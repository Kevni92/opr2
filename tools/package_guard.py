"""Validate that a runtime package contains only the project executable and README."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

MAX_README_SIZE = 2 * 1024 * 1024
EXECUTABLE_NAMES = {"opr2", "opr2.exe"}
README_NAME = "README.txt"
README_FORBIDDEN_MAGIC = (
    b"MZ", b"\x7fELF", b"PK\x03\x04", b"Rar!", b"7z\xbc\xaf\x27\x1c",
    b"\x1f\x8b", b"RIFF", b"OggS", b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff",
    b"BM", b"DDS ", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_reference(path: Path, label: str, errors: list[str]) -> Path | None:
    path = Path(path).expanduser().absolute()
    try:
        info = path.lstat()
    except OSError as exc:
        errors.append(f"{label} is unavailable: {exc}")
        return None
    if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400 or not path.is_file():
        errors.append(f"{label} must be a regular non-symlink file")
        return None
    return path


def check_package(
    directory: Path,
    *,
    expected_executable: Path | None = None,
    expected_readme: Path | None = None,
) -> list[str]:
    """Return violations for the strict, dependency-free runtime package layout."""
    directory = Path(directory).expanduser().absolute()
    root_info = directory.lstat()
    if directory.is_symlink() or getattr(root_info, "st_file_attributes", 0) & 0x400:
        return ["package directory cannot be a symlink or reparse point"]
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        return [f"package path is not a directory: {directory}"]
    errors: list[str] = []
    found: set[str] = set()
    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        return [f"cannot list package directory: {exc}"]
    for entry in entries:
        try:
            info = entry.lstat()
        except OSError as exc:
            errors.append(f"cannot inspect {entry.name}: {exc}")
            continue
        if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            errors.append(f"symlink/reparse point is forbidden: {entry.name}")
            continue
        if not entry.is_file():
            errors.append(f"unexpected directory or special entry: {entry.name}")
            continue
        found.add(entry.name)
        if entry.name in EXECUTABLE_NAMES:
            try:
                if info.st_size == 0:
                    errors.append(f"executable is empty: {entry.name}")
                else:
                    with entry.open("rb") as stream:
                        head = stream.read(4)
                    if entry.name == "opr2.exe" and not head.startswith(b"MZ"):
                        errors.append("opr2.exe does not have a Windows PE header")
                    if entry.name == "opr2" and not head.startswith(b"\x7fELF"):
                        errors.append("opr2 does not have a Linux ELF header")
            except OSError as exc:
                errors.append(f"cannot read {entry.name}: {exc}")
        elif entry.name == README_NAME:
            if info.st_size > MAX_README_SIZE:
                errors.append(f"README exceeds {MAX_README_SIZE} byte limit")
                continue
            try:
                data = entry.read_bytes()
                if b"\0" in data:
                    errors.append("README contains binary/NUL data")
                elif any(data.startswith(signature) for signature in README_FORBIDDEN_MAGIC):
                    errors.append("README starts with a forbidden asset/archive/executable signature")
                else:
                    data.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"README is not readable UTF-8 text: {exc}")
    executables = EXECUTABLE_NAMES & found
    if not executables:
        errors.append("package must contain opr2 (Linux) or opr2.exe (Windows)")
    if len(executables) > 1:
        errors.append("package must contain only one platform executable")
    if README_NAME not in found:
        errors.append(f"package is missing {README_NAME}")
    for name in sorted(found - EXECUTABLE_NAMES - {README_NAME}):
        errors.append(f"unexpected package file: {name}")
    packaged_executables = [directory / name for name in sorted(executables)]
    if expected_executable is not None:
        reference = _regular_reference(expected_executable, "expected build executable", errors)
        if reference is not None and len(packaged_executables) == 1:
            try:
                if _sha256(packaged_executables[0]) != _sha256(reference):
                    errors.append("packaged executable does not match the expected build executable")
            except OSError as exc:
                errors.append(f"cannot compare packaged executable with build output: {exc}")
    if expected_readme is not None:
        reference = _regular_reference(expected_readme, "expected README source", errors)
        packaged_readme = directory / README_NAME
        if reference is not None and README_NAME in found:
            try:
                if _sha256(packaged_readme) != _sha256(reference):
                    errors.append("packaged README does not match the expected README source")
            except OSError as exc:
                errors.append(f"cannot compare packaged README with source: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--built-executable", type=Path, help="expected executable produced by the build")
    parser.add_argument("--readme-source", type=Path, help="expected README source file")
    args = parser.parse_args(argv)
    try:
        violations = check_package(
            args.directory,
            expected_executable=args.built_executable,
            expected_readme=args.readme_source,
        )
    except (OSError, ValueError) as exc:
        print(f"package guard error: {exc}", file=sys.stderr)
        return 2
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        return 1
    print("package guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
