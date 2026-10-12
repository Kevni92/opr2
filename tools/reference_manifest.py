"""Create and verify a read-only file manifest for a local reference tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any


def _is_reparse_or_link(path: Path, info: os.stat_result) -> bool:
    attrs = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attrs & reparse)


def _resolved(path: Path) -> Path:
    # strict=False resolves existing parents too, including Windows junctions.
    return path.expanduser().resolve(strict=False)


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _check_source(root: Path) -> Path:
    root = root.expanduser().absolute()
    info = root.lstat()
    if _is_reparse_or_link(root, info) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"source root must be a real directory, not a link or reparse point: {root}")
    return root.resolve(strict=True)


def _check_output_separate(root: Path, output: Path) -> Path:
    output = output.expanduser().absolute()
    resolved_root = root.resolve(strict=True)
    resolved_output = _resolved(output)
    if _inside(resolved_output, resolved_root):
        raise ValueError(f"output must be outside the source tree: {output}")
    # Also inspect existing ancestors to catch a junction that resolves into root.
    cursor = output
    while not cursor.exists() and not cursor.is_symlink() and cursor != cursor.parent:
        cursor = cursor.parent
    if cursor.exists():
        info = cursor.lstat()
        if _is_reparse_or_link(cursor, info) and _inside(cursor.resolve(strict=False), resolved_root):
            raise ValueError(f"output parent resolves inside the source tree: {cursor}")
    return output


def _safe_file(path: Path, root: Path) -> os.stat_result:
    info = path.lstat()
    if _is_reparse_or_link(path, info):
        raise ValueError(f"source contains a symlink or reparse point: {path.relative_to(root).as_posix()}")
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"source contains a non-regular file: {path.relative_to(root).as_posix()}")
    return info


def snapshot(root: Path) -> dict[str, Any]:
    """Return {version: 1, files: {relative path: {size, sha256}}} for a tree."""
    root = _check_source(Path(root))
    files: dict[str, dict[str, int | str]] = {}
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in dirs:
            child = current_path / name
            info = child.lstat()
            if _is_reparse_or_link(child, info):
                raise ValueError(f"source contains a symlink or reparse point: {child.relative_to(root).as_posix()}")
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"source contains a non-directory entry: {child.relative_to(root).as_posix()}")
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in names:
            path = current_path / name
            info = _safe_file(path, root)
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            rel = path.relative_to(root).as_posix()
            files[rel] = {"size": info.st_size, "sha256": digest.hexdigest()}
    return {"version": 1, "files": dict(sorted(files.items()))}


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or not isinstance(manifest.get("files"), dict):
        raise ValueError("manifest must have version 1 and a files object")
    for name, record in manifest["files"].items():
        posix_name = PurePosixPath(name) if isinstance(name, str) and name else None
        if (posix_name is None or posix_name.is_absolute() or posix_name.as_posix() != name
                or "\\" in name or any(part in {".", ".."} or ":" in part for part in posix_name.parts)
                or not isinstance(record, dict)
                or type(record.get("size")) is not int or record["size"] < 0
                or not isinstance(record.get("sha256"), str)
                or len(record["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in record["sha256"])):
            raise ValueError(f"invalid manifest entry: {name!r}")


def verify(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Return human-readable additions, removals, and content changes."""
    _validate_manifest(manifest)
    current = snapshot(root)["files"]
    expected = manifest["files"]
    errors: list[str] = []
    for name in sorted(expected.keys() - current.keys()):
        errors.append(f"missing: {name}")
    for name in sorted(current.keys() - expected.keys()):
        errors.append(f"added: {name}")
    for name in sorted(current.keys() & expected.keys()):
        if current[name] != expected[name]:
            errors.append(f"changed: {name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create", help="write a baseline manifest")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    check = actions.add_parser("verify", help="compare a tree with a baseline manifest")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "create":
            root = _check_source(args.root)
            output = _check_output_separate(root, args.output)
            result = snapshot(root)
            output.parent.mkdir(parents=True, exist_ok=True)
            # Recheck after directory creation in case a parent was a junction.
            _check_output_separate(root, output)
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(f"manifest written: {output}")
            return 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        errors = verify(args.root, manifest)
        for error in errors:
            print(error, file=sys.stderr)
        if errors:
            return 1
        print("reference tree matches manifest")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"reference manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
