"""Scan Git's index, tracked working files, and optionally reachable history."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MAX_BLOB_SIZE = 2 * 1024 * 1024
FORBIDDEN_DIRS = {"pr2", "analysis", "build", "dist", ".worktrees", "local"}
FORBIDDEN_EXTENSIONS = {
    ".cpr", ".aim", ".3do", ".screen", ".anim", ".cla", ".tow", ".lcr",
    ".coa", ".let", ".res", ".ttf", ".otf", ".mp3", ".wav", ".ogg",
    ".wmv", ".avi", ".mp4", ".pdf", ".exe", ".dll", ".so", ".asi",
    ".emp", ".bin", ".dat", ".zip", ".7z", ".rar", ".cab", ".pak",
    ".arc", ".bmp", ".png", ".jpg", ".jpeg", ".gif", ".tga", ".dds",
    ".ico", ".cur", ".mid", ".midi", ".wav", ".flac", ".ogg", ".mod",
    ".db", ".sqlite", ".sav", ".save", ".patch", ".iso", ".img", ".msi",
}
ALLOWED_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".ixx",
    ".py", ".ps1", ".sh", ".bat", ".cmd", ".md", ".txt", ".rst", ".adoc",
    ".json", ".toml", ".yaml", ".yml", ".xml", ".ini", ".cfg", ".conf",
    ".cmake", ".html", ".css", ".js", ".ts", ".gitignore", ".gitattributes",
    ".gitmodules", ".editorconfig", ".clang-format", ".clang-tidy", ".def",
}
ALLOWED_BASENAMES = {
    "CMakeLists.txt", "Makefile", "Dockerfile", "Containerfile", "README",
    "LICENSE", "NOTICE", "COPYING", ".gitignore", ".gitattributes",
    ".gitmodules", ".editorconfig", ".clang-format", ".clang-tidy",
    "pre-commit", "pre-push",
}
MAGIC = (
    (b"MZ", "PE executable"), (b"\x7fELF", "ELF executable"),
    (b"PK\x03\x04", "ZIP archive"), (b"Rar!", "RAR archive"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"), (b"\x1f\x8b", "gzip archive"),
    (b"RIFF", "RIFF media/container"), (b"OggS", "Ogg media"),
    (b"\x89PNG\r\n\x1a\n", "PNG image"), (b"\xff\xd8\xff", "JPEG image"),
    (b"BM", "bitmap image"), (b"DDS ", "DDS image"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "OLE document/container"),
)
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"
_LFS_OID = re.compile(rb"^oid sha256:[0-9a-f]{64}$", re.MULTILINE)


def _git(root: Path, *args: str, binary: bool = True) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout if binary else result.stdout.decode("utf-8", errors="replace")


def _path_reason(raw_path: str) -> str | None:
    path = PurePosixPath(raw_path.replace("\\", "/"))
    parts = [part.casefold() for part in path.parts]
    if any(part in FORBIDDEN_DIRS for part in parts):
        return "forbidden repository path"
    if path.suffix.casefold() in FORBIDDEN_EXTENSIONS:
        return "forbidden asset or executable extension"
    if path.name not in ALLOWED_BASENAMES and path.suffix.casefold() not in ALLOWED_EXTENSIONS:
        return "unapproved file type"
    return None


def _content_reason(data: bytes, reference_hashes: set[str] | None = None) -> str | None:
    if len(data) > MAX_BLOB_SIZE:
        return f"blob exceeds {MAX_BLOB_SIZE} byte limit"
    if b"\0" in data:
        return "binary or NUL-containing data"
    head = data[:32]
    for signature, description in MAGIC:
        if head.startswith(signature):
            return description
    if data.startswith(LFS_HEADER) and _LFS_OID.search(data[:4096]):
        return "Git LFS pointer"
    if reference_hashes and hashlib.sha256(data).hexdigest() in reference_hashes:
        return "content matches a local reference file"
    return None


def _split_nul(data: bytes) -> list[bytes]:
    return [part for part in data.split(b"\0") if part]


def _safe_working_blob(root: Path, rel: str, errors: set[str]) -> bytes | None:
    parts = PurePosixPath(rel).parts
    path = root
    try:
        for part in parts[:-1]:
            path = path / part
            parent_info = path.lstat()
            if path.is_symlink() or getattr(parent_info, "st_file_attributes", 0) & 0x400:
                errors.add(f"{rel}: symlink/reparse point in tracked path")
                return None
            if not path.is_dir():
                return None
        path = path / parts[-1]
        info = path.lstat()
        if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            errors.add(f"{rel}: symlink/reparse point")
            return None
        if not path.is_file():
            return None
        if info.st_size > MAX_BLOB_SIZE:
            return b" " * (MAX_BLOB_SIZE + 1)
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        errors.add(f"{rel}: cannot read tracked working file ({exc})")
        return None


def check_repository(
    root: Path,
    history: bool = False,
    reference_hashes: set[str] | None = None,
) -> list[str]:
    """Return policy violations found in index, tracked files, or reachable history."""
    root = Path(root).expanduser().resolve(strict=True)
    top = Path(str(_git(root, "rev-parse", "--show-toplevel", binary=False)).strip()).resolve(strict=True)
    if top != root:
        root = top
    errors: set[str] = set()
    index_entries = _split_nul(_git(root, "ls-files", "--stage", "-z"))
    seen_working: set[str] = set()
    seen_index_blobs: set[str] = set()
    for entry in index_entries:
        try:
            meta, path_bytes = entry.split(b"\t", 1)
            mode, oid, _stage = meta.decode("ascii").split()
            rel = path_bytes.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        except (ValueError, UnicodeDecodeError):
            errors.add("index contains an unparsable entry")
            continue
        reason = _path_reason(rel)
        if reason:
            errors.add(f"{rel}: {reason} (index)")
        if mode == "120000":
            errors.add(f"{rel}: symlink Git entry")
        if oid not in seen_index_blobs:
            seen_index_blobs.add(oid)
            size_text = str(_git(root, "cat-file", "-s", oid, binary=False)).strip()
            if not size_text.isdigit() or int(size_text) > MAX_BLOB_SIZE:
                content_reason = f"blob exceeds {MAX_BLOB_SIZE} byte limit"
            else:
                content_reason = _content_reason(_git(root, "cat-file", "blob", oid), reference_hashes)
            if content_reason:
                errors.add(f"{rel}: {content_reason} (index blob)")
        if rel not in seen_working:
            seen_working.add(rel)
            working = _safe_working_blob(root, rel, errors)
            if working is not None:
                content_reason = _content_reason(working, reference_hashes)
                if content_reason:
                    errors.add(f"{rel}: {content_reason} (working file)")

    if history:
        # `rev-list --objects` deduplicates blobs and can associate one blob with
        # only one path. Walk changed names too so reused content under a later
        # forbidden name cannot disappear from the path check.
        history_paths = _split_nul(_git(root, "log", "--all", "--format=", "--name-only", "-z"))
        for raw_path in history_paths:
            rel = raw_path.decode("utf-8", errors="surrogateescape").replace("\\", "/")
            reason = _path_reason(rel)
            if reason:
                errors.add(f"{rel}: {reason} (reachable history)")
        objects = str(_git(root, "rev-list", "--objects", "--all", binary=False)).splitlines()
        seen: set[str] = set()
        for line in objects:
            fields = line.split(" ", 1)
            oid = fields[0]
            if not re.fullmatch(r"[0-9a-f]{40,64}", oid) or oid in seen:
                continue
            seen.add(oid)
            type_name = str(_git(root, "cat-file", "-t", oid, binary=False)).strip()
            if type_name != "blob":
                continue
            rel = fields[1] if len(fields) > 1 else f"<blob {oid}>"
            reason = _path_reason(rel) if len(fields) > 1 else None
            if reason:
                errors.add(f"{rel}: {reason} (reachable history)")
            size_text = str(_git(root, "cat-file", "-s", oid, binary=False)).strip()
            if not size_text.isdigit() or int(size_text) > MAX_BLOB_SIZE:
                errors.add(f"{rel}: blob exceeds {MAX_BLOB_SIZE} byte limit (reachable history)")
                continue
            reason = _content_reason(_git(root, "cat-file", "blob", oid), reference_hashes)
            if reason:
                errors.add(f"{rel}: {reason} (reachable history)")
    return sorted(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--history", action="store_true", help="also scan all reachable Git history")
    parser.add_argument("--manifest", type=Path, help="local reference manifest; defaults to analysis/reference-manifest.json when present")
    args = parser.parse_args(argv)
    try:
        manifest_path = args.manifest
        if manifest_path is None:
            candidate = args.repo / "analysis" / "reference-manifest.json"
            if candidate.is_file():
                manifest_path = candidate
        hashes: set[str] | None = None
        if manifest_path is not None:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
                raise ValueError("reference manifest must contain a files object")
            hashes = set()
            for rel, metadata in manifest["files"].items():
                digest = metadata.get("sha256") if isinstance(metadata, dict) else None
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError(f"invalid SHA-256 entry in reference manifest: {rel!r}")
                hashes.add(digest)
        violations = check_repository(args.repo, args.history, hashes)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"asset guard error: {exc}", file=sys.stderr)
        return 2
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        return 1
    print("asset guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
