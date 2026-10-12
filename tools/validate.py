"""Run the same asset-free validation locally and in CI; original data is opt-in."""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import uuid
import shutil
from pathlib import Path

from asset_guard import check_repository
from package_guard import check_package
from reference_manifest import verify


def _is_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _reject_reparse_components(path: Path, label: str) -> Path:
    """Inspect raw components before canonicalizing aliases or links."""
    raw = Path(os.path.abspath(path))
    cursor = Path(raw.anchor)
    for part in raw.parts[1:]:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            break
        if _is_reparse(cursor.lstat()):
            raise ValueError(f"{label} contains a symlink or reparse point: {cursor}")
    return raw


def _reference_hashes(manifest: dict) -> set[str]:
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, dict):
        raise ValueError("reference manifest must contain a files object")
    hashes: set[str] = set()
    for name, record in files.items():
        digest = record.get("sha256") if isinstance(record, dict) else None
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError(f"invalid SHA-256 entry in reference manifest: {name!r}")
        hashes.add(digest)
    return hashes


def _check_build_path(root: Path, build: Path, original: Path | None = None) -> Path:
    """Check path containment and links; this is not a process sandbox."""
    root_real = Path(root).resolve(strict=True)
    build_input = build if build.is_absolute() else root_real / build
    build_raw = _reject_reparse_components(build_input, "build path")
    build_real = build_raw.resolve(strict=False)
    pr2_real = (root_real / "pr2").resolve(strict=False)
    if (build_real == root_real or not _within(build_real, root_real)
            or _within(build_real, pr2_real)):
        raise ValueError("build directory must be inside the workspace and outside pr2")
    if original is not None:
        original_input = original if original.is_absolute() else root_real / original
        original_real = Path(original_input).resolve(strict=True)
        if _within(build_real, original_real):
            raise ValueError("build directory must not be inside original data")

    # Inspect each path component and the existing tree without following links.
    relative = build_real.relative_to(root_real)
    cursor = root_real
    for part in relative.parts:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            break
        info = cursor.lstat()
        if _is_reparse(info):
            raise ValueError(f"build path contains a symlink or reparse point: {cursor}")
        if cursor != build_real and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"build path component is not a directory: {cursor}")
    if build_real.exists():
        info = build_real.lstat()
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("build path must be a real directory")
        for current, dirs, files in os.walk(build_real, topdown=True, followlinks=False):
            current_path = Path(current)
            for name in list(dirs):
                entry = current_path / name
                entry_info = entry.lstat()
                if _is_reparse(entry_info):
                    raise ValueError(f"build tree contains a symlink or reparse point: {entry}")
                if not stat.S_ISDIR(entry_info.st_mode):
                    raise ValueError(f"build tree contains a non-directory entry: {entry}")
            for name in files:
                entry = current_path / name
                entry_info = entry.lstat()
                if _is_reparse(entry_info):
                    raise ValueError(f"build tree contains a symlink or reparse point: {entry}")
    return build_real


def _check_reference_copy_target(root: Path, target: Path, build: Path,
                                 original: Path | None) -> Path:
    root_real = root.resolve(strict=True)
    target_input = target if target.is_absolute() else root_real / target
    target_raw = _reject_reparse_components(target_input, "analysis output path")
    target_real = target_raw.resolve(strict=False)
    build_real = build.resolve(strict=False)
    pr2_real = (root_real / "pr2").resolve(strict=False)
    blocked = [build_real, pr2_real]
    if original is not None:
        blocked.append(original.resolve(strict=True))
    for path in blocked:
        path_real = path.resolve(strict=False)
        if _within(target_real, path_real) or target_real == path_real:
            raise ValueError("original-data copy must be outside build and original-data trees")
    if target_real == root_real:
        raise ValueError("original-data copy target must be a dedicated analysis directory")
    analysis_real = (root_real / "analysis").resolve(strict=False)
    if _within(target_real, root_real) and not _within(target_real, analysis_real):
        raise ValueError("in-workspace original-data copies must stay under analysis/")

    if target_real.exists():
        info = target_real.lstat()
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("original-data copy target must be a real directory")
    return target_real


def run(command: list[str], root: Path) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


def validate(root: Path, build: Path, sanitizers: bool = False,
             original: Path | None = None, manifest: Path | None = None,
             analysis_dir: Path | None = None) -> None:
    root = root.resolve(strict=True)
    analysis_dir = analysis_dir or (root / "analysis")
    # Path validation happens before tests, manifest verification, or any command
    # that can write into the requested build tree.
    build = _check_build_path(root, build, original)
    baseline = None
    selected_manifest = manifest
    if original is not None:
        original = original.resolve(strict=True)
        if manifest is None:
            raise ValueError("original-data validation requires an existing --manifest")
    if selected_manifest is None:
        candidate = root / "analysis" / "reference-manifest.json"
        if candidate.is_file():
            selected_manifest = candidate
    reference_hashes = None
    if selected_manifest is not None:
        baseline = json.loads(selected_manifest.read_text(encoding="utf-8"))
        reference_hashes = _reference_hashes(baseline)
    if original is not None:
        violations = verify(original, baseline)
        if violations:
            raise ValueError("reference mismatch before validation: " + "; ".join(violations))
    try:
        violations = check_repository(root, history=True, reference_hashes=reference_hashes)
        if violations:
            raise ValueError("repository asset policy: " + "; ".join(violations))
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests/python", "-v"], root)
        build = _check_build_path(root, build, original)
        run(["cmake", "-S", str(root), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
             "-DBUILD_TESTING=ON", "-DOPR2_ENABLE_SANITIZERS=" + ("ON" if sanitizers else "OFF")], root)
        build = _check_build_path(root, build, original)
        run(["cmake", "--build", str(build), "--config", "Release", "--parallel", "2"], root)
        build = _check_build_path(root, build, original)
        run(["ctest", "--test-dir", str(build), "-C", "Release", "--output-on-failure"], root)
        executable = next((p for p in [build / "Release/opr2.exe", build / "opr2.exe", build / "opr2"]
                           if p.is_file()), None)
        if executable is None:
            raise ValueError("project-built executable was not found")
        if original is not None:
            copy_target = _check_reference_copy_target(
                root, analysis_dir / "validation-reference" / uuid.uuid4().hex, build, original
            )
            copy_target.parent.mkdir(parents=True, exist_ok=True)
            # Recheck after creating parent directories in case an ancestor changed.
            copy_target = _check_reference_copy_target(root, copy_target, build, original)
            shutil.copytree(original, copy_target, symlinks=True)
            copy_violations = verify(copy_target, baseline)
            if copy_violations:
                raise ValueError("reference copy mismatch before validation: " + "; ".join(copy_violations))
            run([str(executable), "--check-data", "--data-dir", str(copy_target)], root)
        package = build / "package"
        # Validate the install destination separately immediately before CMake
        # writes there; this also catches an existing nested package junction.
        _check_build_path(root, package, original)
        run(["cmake", "--install", str(build), "--config", "Release", "--prefix", str(package)], root)
        violations = check_package(package, expected_executable=executable,
                                   expected_readme=root / "docs/runtime-package.txt")
        if violations:
            raise ValueError("runtime package policy: " + "; ".join(violations))
        print("Validation passed (synthetic tests; not a gameplay parity certificate).", flush=True)
    finally:
        if original is not None and baseline is not None:
            violations = verify(original, baseline)
            if violations:
                raise ValueError("reference mismatch after validation: " + "; ".join(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=Path("build/validation"))
    parser.add_argument("--sanitizers", action="store_true")
    parser.add_argument("--original-data", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--analysis-dir", type=Path, help="local analysis directory for validation copies")
    args = parser.parse_args()
    try:
        validate(Path.cwd(), args.build_dir, args.sanitizers, args.original_data,
                 args.manifest, args.analysis_dir)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
