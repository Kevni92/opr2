import json
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
import validate as validation
from reference_manifest import snapshot


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "workspace"
        self.root.mkdir()

    def make_reference(self):
        original = self.root / "pr2"
        original.mkdir(exist_ok=True)
        (original / "synthetic.ini").write_text("[synthetic]\nvalue=fixture\n", encoding="utf-8")
        manifest = self.base / "reference-manifest.json"
        manifest.write_text(json.dumps(snapshot(original)), encoding="utf-8")
        return original, manifest, json.loads(manifest.read_text(encoding="utf-8"))

    def test_unsafe_build_paths_are_rejected_before_any_command_or_repository_scan(self):
        original, _manifest, _baseline = self.make_reference()
        outside = self.base / "outside-build"
        with mock.patch.object(validation, "run") as run, \
                mock.patch.object(validation, "check_repository") as guard:
            with self.assertRaises(ValueError):
                validation.validate(self.root, outside)
            with self.assertRaises(ValueError):
                validation.validate(self.root, Path("pr2") / "build")
            with self.assertRaises(ValueError):
                validation.validate(self.root, original / "build", original=original)
        run.assert_not_called()
        guard.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows short-name alias regression")
    def test_windows_short_alias_accepts_workspace_build_but_still_blocks_pr2(self):
        short_root = self.windows_short_alias(self.root)
        if short_root is None:
            self.skipTest("8.3 short path alias is unavailable")
        normal = self.root / "build" / "validation"
        self.assertEqual(validation._check_build_path(short_root, short_root / "build" / "validation"), normal)
        with self.assertRaises(ValueError):
            validation._check_build_path(short_root, short_root / "pr2" / "validation")

    @staticmethod
    def windows_short_alias(path):
        buffer = ctypes.create_unicode_buffer(32768)
        get_short = ctypes.windll.kernel32.GetShortPathNameW
        get_short.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        get_short.restype = ctypes.c_uint
        length = get_short(str(path), buffer, len(buffer))
        if not length or "~" not in buffer.value:
            return None
        short = Path(buffer.value)
        return short if short.resolve(strict=False) == path.resolve(strict=False) else None

    def test_normal_orchestration_uses_reference_copy_and_manifest_hashes(self):
        original, manifest, baseline = self.make_reference()
        build = self.root / "build" / "validation"
        analysis = self.base / "shared-analysis" / "runs" / "issue-3"
        readme = self.root / "docs" / "runtime-package.txt"
        readme.parent.mkdir()
        readme.write_text("Synthetic runtime instructions.\n", encoding="utf-8")
        expected_hashes = {record["sha256"] for record in baseline["files"].values()}
        commands = []

        def fake_run(command, cwd):
            commands.append(command)
            if command[:2] == ["cmake", "--build"]:
                build.mkdir(parents=True, exist_ok=True)
                (build / "opr2").write_bytes(b"\x7fELFsynthetic-built-executable")
            elif command[:2] == ["cmake", "--install"]:
                package = build / "package"
                package.mkdir(parents=True)
                shutil.copy2(build / "opr2", package / "opr2")
                shutil.copy2(readme, package / "README.txt")
            elif command and command[0].endswith("opr2"):
                data_dir = Path(command[command.index("--data-dir") + 1])
                self.assertNotEqual(data_dir, original)
                self.assertTrue(data_dir.is_relative_to(analysis))
                self.assertEqual(validation.verify(data_dir, baseline), [])

        with mock.patch.object(validation, "run", side_effect=fake_run), \
                mock.patch.object(validation, "check_repository", return_value=[]) as guard:
            validation.validate(self.root, build, original=original, manifest=manifest, analysis_dir=analysis)

        guard.assert_called_once_with(self.root.resolve(), history=True, reference_hashes=expected_hashes)
        self.assertEqual([command[:2] for command in commands], [
            [sys.executable, "-m"], ["cmake", "-S"], ["cmake", "--build"],
            ["ctest", "--test-dir"], [str(build / "opr2"), "--check-data"],
            ["cmake", "--install"],
        ])
        self.assertEqual(validation.verify(original, baseline), [])
        self.assertTrue((analysis / "validation-reference").is_dir())

    def test_manifest_hashes_are_passed_to_guard_without_original_even_on_failure(self):
        _original, manifest, baseline = self.make_reference()
        expected_hashes = {record["sha256"] for record in baseline["files"].values()}
        with mock.patch.object(validation, "check_repository", return_value=[]) as guard, \
                mock.patch.object(validation, "run", side_effect=subprocess.CalledProcessError(1, "synthetic")):
            with self.assertRaises(subprocess.CalledProcessError):
                validation.validate(self.root, Path("build/validation"), manifest=manifest)
        guard.assert_called_once_with(self.root.resolve(), history=True, reference_hashes=expected_hashes)

    def test_original_manifest_is_rechecked_after_subprocess_failure(self):
        original, manifest, baseline = self.make_reference()
        real_verify = validation.verify
        with mock.patch.object(validation, "check_repository", return_value=[]), \
                mock.patch.object(validation, "run", side_effect=[None, None, subprocess.CalledProcessError(1, "cmake --build")]), \
                mock.patch.object(validation, "verify", wraps=real_verify) as verify:
            with self.assertRaises(subprocess.CalledProcessError):
                validation.validate(self.root, Path("build/validation"), original=original, manifest=manifest)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(real_verify(original, baseline), [])

    def test_nested_package_reparse_entry_is_rejected_before_install(self):
        self.make_reference()
        build = self.root / "build" / "validation"
        package = build / "package"
        junction = package / "synthetic-junction-entry"
        commands = []
        reparse_identity = set()
        real_is_reparse = validation._is_reparse

        def fake_run(command, _cwd):
            commands.append(command)
            if command[:2] == ["cmake", "--build"]:
                build.mkdir(parents=True, exist_ok=True)
                (build / "opr2").write_bytes(b"\x7fELFsynthetic-built-executable")
            if command[:2] == ["ctest", "--test-dir"]:
                package.mkdir(parents=True)
                junction.mkdir()
                entry_info = junction.lstat()
                reparse_identity.add((entry_info.st_dev, entry_info.st_ino))

        with mock.patch.object(validation, "check_repository", return_value=[]), \
                mock.patch.object(validation, "run", side_effect=fake_run), \
                mock.patch.object(validation, "_is_reparse", side_effect=lambda info:
                                  real_is_reparse(info) or (info.st_dev, info.st_ino) in reparse_identity):
            with self.assertRaisesRegex(ValueError, "symlink or reparse point"):
                validation.validate(self.root, build)
        self.assertFalse(any(command[:2] == ["cmake", "--install"] for command in commands))

    def test_analysis_copy_target_cannot_be_original_or_build(self):
        original, _manifest, _baseline = self.make_reference()
        build = self.root / "build" / "validation"
        with self.assertRaises(ValueError):
            validation._check_reference_copy_target(self.root, build / "copy", build, original)
        with self.assertRaises(ValueError):
            validation._check_reference_copy_target(self.root, original / "copy", build, original)


if __name__ == "__main__":
    unittest.main()
