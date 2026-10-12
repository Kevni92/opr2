import json
import tempfile
import unittest
from pathlib import Path

from tools.reference_manifest import main, snapshot, verify


class ReferenceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "reference"
        self.source.mkdir()
        (self.source / "nested").mkdir()
        (self.source / "nested" / "sample.bin").write_bytes(b"synthetic fixture\0data")
        (self.source / "readme.txt").write_text("synthetic", encoding="utf-8")

    def test_snapshot_matches_baseline_schema(self):
        result = snapshot(self.source)
        self.assertEqual(set(result), {"version", "files"})
        self.assertEqual(result["version"], 1)
        record = result["files"]["nested/sample.bin"]
        self.assertEqual(record["size"], len(b"synthetic fixture\0data"))
        self.assertEqual(len(record["sha256"]), 64)
        self.assertEqual(verify(self.source, result), [])

    def test_verify_reports_changed_added_and_missing(self):
        baseline = snapshot(self.source)
        (self.source / "readme.txt").write_text("changed", encoding="utf-8")
        (self.source / "new.txt").write_text("new", encoding="utf-8")
        (self.source / "nested" / "sample.bin").unlink()
        self.assertEqual(verify(self.source, baseline), [
            "missing: nested/sample.bin", "added: new.txt", "changed: readme.txt",
        ])

    def test_create_refuses_output_inside_source_before_creating_parents(self):
        output = self.source / "new-parent" / "manifest.json"
        code = main(["create", "--root", str(self.source), "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertFalse(output.parent.exists())

    def test_create_and_verify_cli(self):
        output = self.base / "manifest.json"
        self.assertEqual(main(["create", "--root", str(self.source), "--output", str(output)]), 0)
        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(verify(self.source, manifest), [])
        (self.source / "readme.txt").write_text("changed", encoding="utf-8")
        self.assertEqual(main(["verify", "--root", str(self.source), "--manifest", str(output)]), 1)

    def test_rejects_symlink_in_source_when_supported(self):
        target = self.source / "readme.txt"
        link = self.source / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(ValueError):
            snapshot(self.source)


if __name__ == "__main__":
    unittest.main()
