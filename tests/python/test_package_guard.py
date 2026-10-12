import tempfile
import unittest
from pathlib import Path

from tools.package_guard import check_package


class PackageGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name) / "package"
        self.package.mkdir()
        (self.package / "opr2").write_bytes(b"\x7fELF" + b"synthetic executable")
        (self.package / "README.txt").write_text("User supplies original game data.\n", encoding="utf-8")

    def test_minimal_linux_package_passes(self):
        self.assertEqual(check_package(self.package), [])

    def test_minimal_windows_package_passes(self):
        (self.package / "opr2").unlink()
        (self.package / "opr2.exe").write_bytes(b"MZ" + b"synthetic executable")
        self.assertEqual(check_package(self.package), [])

    def test_unexpected_file_is_rejected(self):
        (self.package / "asset.dll").write_bytes(b"synthetic bytes")
        errors = check_package(self.package)
        self.assertTrue(any("unexpected package file: asset.dll" in error for error in errors))

    def test_nested_directory_is_rejected(self):
        (self.package / "assets").mkdir()
        errors = check_package(self.package)
        self.assertTrue(any("unexpected directory or special entry" in error for error in errors))

    def test_readme_must_be_text(self):
        (self.package / "README.txt").write_bytes(b"PK\x03\x04synthetic")
        errors = check_package(self.package)
        self.assertTrue(any("forbidden asset/archive/executable signature" in error for error in errors))

    def test_original_style_binary_renamed_readme_is_rejected(self):
        (self.package / "README.txt").write_bytes(b"MZsynthetic executable")
        errors = check_package(self.package)
        self.assertTrue(any("forbidden asset/archive/executable signature" in error for error in errors))

    def test_platform_executable_header_is_checked(self):
        (self.package / "opr2").write_bytes(b"synthetic executable")
        errors = check_package(self.package)
        self.assertTrue(any("Linux ELF header" in error for error in errors))

    def test_build_and_readme_provenance_must_match(self):
        built = Path(self.temp.name) / "build-opr2"
        readme_source = Path(self.temp.name) / "README-source.txt"
        built.write_bytes(b"\x7fELF" + b"different synthetic executable")
        readme_source.write_text("Different synthetic instructions.\n", encoding="utf-8")
        errors = check_package(
            self.package,
            expected_executable=built,
            expected_readme=readme_source,
        )
        self.assertTrue(any("does not match the expected build executable" in error for error in errors))
        self.assertTrue(any("does not match the expected README source" in error for error in errors))

    def test_matching_build_and_readme_provenance_passes(self):
        built = Path(self.temp.name) / "build-opr2"
        readme_source = Path(self.temp.name) / "README-source.txt"
        built.write_bytes((self.package / "opr2").read_bytes())
        readme_source.write_bytes((self.package / "README.txt").read_bytes())
        self.assertEqual(
            check_package(self.package, expected_executable=built, expected_readme=readme_source),
            [],
        )

    def test_package_root_symlink_is_rejected_when_supported(self):
        alias = Path(self.temp.name) / "package-link"
        try:
            alias.symlink_to(self.package, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        self.assertTrue(any("package directory cannot be a symlink" in error for error in check_package(alias)))

    def test_missing_readme_and_executable_are_rejected(self):
        (self.package / "opr2").unlink()
        (self.package / "README.txt").unlink()
        errors = check_package(self.package)
        self.assertTrue(any("must contain opr2" in error for error in errors))
        self.assertTrue(any("missing README.txt" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
