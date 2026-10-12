import os
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.asset_guard import check_repository


class AssetGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Synthetic Test")
        (self.repo / "CMakeLists.txt").write_text("project(synthetic)\n", encoding="utf-8")
        (self.repo / "README.md").write_text("Synthetic test repository.\n", encoding="utf-8")
        self.git("add", ".")

    def git(self, *args, input_bytes=None):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, input=input_bytes,
        ).stdout

    def test_clean_synthetic_repository_passes(self):
        self.assertEqual(check_repository(self.repo), [])

    def test_forbidden_path_is_detected_in_index(self):
        (self.repo / "fixture.dat").write_bytes(b"synthetic bytes")
        self.git("add", "fixture.dat")
        errors = check_repository(self.repo)
        self.assertTrue(any("forbidden asset or executable extension" in error for error in errors))

    def test_working_copy_content_is_scanned(self):
        path = self.repo / "README.md"
        path.write_bytes(b"MZsynthetic executable bytes")
        errors = check_repository(self.repo)
        self.assertTrue(any("PE executable (working file)" in error for error in errors))

    def test_renamed_archive_is_detected_by_content(self):
        (self.repo / "payload.txt").write_bytes(b"PK\x03\x04synthetic archive marker")
        self.git("add", "payload.txt")
        errors = check_repository(self.repo)
        self.assertTrue(any("ZIP archive" in error for error in errors))

    def test_lfs_pointer_is_detected(self):
        pointer = (
            b"version https://git-lfs.github.com/spec/v1\n"
            + b"oid sha256:" + b"a" * 64 + b"\nsize 42\n"
        )
        (self.repo / "fixture.txt").write_bytes(pointer)
        self.git("add", "fixture.txt")
        errors = check_repository(self.repo)
        self.assertTrue(any("Git LFS pointer" in error for error in errors))

    def test_deleted_historical_asset_is_detected_only_with_history_scan(self):
        (self.repo / "gone.dat").write_bytes(b"synthetic historical fixture")
        self.git("add", "gone.dat")
        self.git("commit", "-qm", "add synthetic fixture")
        (self.repo / "gone.dat").unlink()
        self.git("add", "-u")
        self.git("commit", "-qm", "remove synthetic fixture")
        self.assertEqual(check_repository(self.repo, history=False), [])
        errors = check_repository(self.repo, history=True)
        self.assertTrue(any("gone.dat" in error and "reachable history" in error for error in errors))

    def test_historical_forbidden_path_is_found_when_blob_is_shared(self):
        # Git reuses this blob ID for both paths; path checks must inspect the
        # commit names, not only the single path rev-list associates with it.
        payload = b"synthetic textual fixture with a shared object id\n"
        (self.repo / "allowed.txt").write_bytes(payload)
        self.git("add", "allowed.txt")
        self.git("commit", "-qm", "add allowed synthetic file")
        forbidden_dir = self.repo / "pr2"
        forbidden_dir.mkdir()
        (self.repo / "allowed.txt").rename(forbidden_dir / "alias.txt")
        self.git("add", "-A")
        self.git("commit", "-qm", "rename into forbidden path")
        (forbidden_dir / "alias.txt").unlink()
        forbidden_dir.rmdir()
        self.git("add", "-A")
        self.git("commit", "-qm", "delete synthetic file")
        errors = check_repository(self.repo, history=True)
        self.assertTrue(any("pr2/alias.txt" in error and "reachable history" in error for error in errors))

    def test_local_reference_hash_catches_allowed_text_path_in_index_and_working_tree(self):
        payload = b"[synthetic]\nname=original-reference-text\n"
        digest = hashlib.sha256(payload).hexdigest()
        (self.repo / "safe.txt").write_bytes(payload)
        self.git("add", "safe.txt")
        errors = check_repository(self.repo, reference_hashes={digest})
        self.assertTrue(any("safe.txt" in error and "index blob" in error for error in errors))
        self.assertTrue(any("safe.txt" in error and "working file" in error for error in errors))
        self.assertFalse(any(digest in error for error in errors))

    def test_local_reference_hash_catches_deleted_historical_text(self):
        payload = b"[synthetic]\nname=original-reference-text\n"
        digest = hashlib.sha256(payload).hexdigest()
        (self.repo / "safe.txt").write_bytes(payload)
        self.git("add", "safe.txt")
        self.git("commit", "-qm", "add synthetic reference-like text")
        (self.repo / "safe.txt").unlink()
        self.git("add", "-u")
        self.git("commit", "-qm", "remove synthetic reference-like text")
        errors = check_repository(self.repo, history=True, reference_hashes={digest})
        self.assertTrue(any("safe.txt" in error and "reachable history" in error for error in errors))
        self.assertFalse(any(digest in error for error in errors))

    def test_cli_automatically_uses_local_reference_manifest_when_present(self):
        payload = b"[synthetic]\nname=original-reference-text\n"
        digest = hashlib.sha256(payload).hexdigest()
        (self.repo / "safe.txt").write_bytes(payload)
        self.git("add", "safe.txt")
        analysis = self.repo / "analysis"
        analysis.mkdir()
        (analysis / "reference-manifest.json").write_text(json.dumps({
            "version": 1,
            "files": {"original.ini": {"size": len(payload), "sha256": digest}},
        }), encoding="utf-8")
        from tools.asset_guard import main
        self.assertEqual(main(["--repo", str(self.repo)]), 1)

    def test_symlink_index_entry_is_detected(self):
        try:
            os.symlink("missing-target", self.repo / "link.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        self.git("add", "link.txt")
        errors = check_repository(self.repo)
        self.assertTrue(any("symlink Git entry" in error for error in errors))

    def test_forbidden_root_tree_does_not_need_to_be_traversed(self):
        # The guard examines Git metadata only; an untracked original tree is ignored.
        original = self.repo / "pr2"
        original.mkdir()
        (original / "untouched.dat").write_bytes(b"not scanned as an untracked tree")
        self.assertEqual(check_repository(self.repo), [])


if __name__ == "__main__":
    unittest.main()
