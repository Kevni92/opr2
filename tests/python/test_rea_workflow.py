import hashlib
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from rea_workflow import REA_TOOLS, prepare_rea


class ReaWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "workspace"
        (self.root / "pr2").mkdir(parents=True)
        self.exe_bytes = b"synthetic PR2 executable fixture\x00not original data"
        (self.root / "pr2" / "PR2.exe").write_bytes(self.exe_bytes)
        self.baseline = {"version": 1, "files": {"PR2.exe": {
            "size": len(self.exe_bytes), "sha256": hashlib.sha256(self.exe_bytes).hexdigest()}}}
        self.run_dir = self.root / "analysis" / "runs" / "issue-1"
        self.config_dir = self.root / "local"
        self.config_dir.mkdir()
        self.fake_server = self.base / "fake_mcp_server.py"
        self.fake_server.write_text(
            "import json, os\n"
            "print(json.dumps({'transport':'stdio','test_env':os.environ.get('REA_FAKE_ENV')}))\n",
            encoding="utf-8",
        )
        self.server_spec = {"command": sys.executable, "args": [str(self.fake_server)],
                            "env": {"REA_FAKE_ENV": "synthetic"}}
        self.write_config({"mcpServers": {"rea": self.server_spec}})

    def write_config(self, document):
        (self.config_dir / "rea.mcp.json").write_text(json.dumps(document), encoding="utf-8")

    def test_prepares_verified_static_context_and_private_evidence(self):
        context = prepare_rea(self.root, {}, self.run_dir, self.baseline)
        self.assertEqual(context["server"], self.server_spec)
        self.assertEqual(context["tools"], REA_TOOLS)
        self.assertTrue(context["target"]["baseline_verified"])
        self.assertEqual(context["target"]["relative_path"], "PR2.exe")
        self.assertIn("observation", context["prompt"])
        self.assertIn("AppControl", context["prompt"])
        evidence = Path(context["evidence_path"])
        self.assertEqual(evidence, self.run_dir / "analysis" / "rea-context.json")
        self.assertEqual(list(evidence.parent.iterdir()), [evidence])
        self.assertNotIn(self.exe_bytes.decode("latin-1"), evidence.read_text(encoding="utf-8"))
        self.assertEqual(context["target"]["sha256"], self.baseline["files"]["PR2.exe"]["sha256"])
        self.assertIn(context["target"]["path"], context["prompt"].replace("\\\\", "\\"))

    def test_returned_stdio_spec_can_launch_a_synthetic_fake_server(self):
        context = prepare_rea(self.root, {}, self.run_dir, self.baseline)
        server = context["server"]
        result = subprocess.run([server["command"], *server["args"]], check=True, text=True,
                                stdout=subprocess.PIPE, env={**os.environ, **server["env"]})
        self.assertEqual(json.loads(result.stdout), {"transport": "stdio", "test_env": "synthetic"})

    @unittest.skipUnless(os.name == "nt", "Windows short-name alias regression")
    def test_windows_short_alias_accepts_local_rea_config_and_output_path(self):
        short_root = self.windows_short_alias(self.root)
        if short_root is None:
            self.skipTest("8.3 short path alias is unavailable")
        config_path = short_root / "local" / "rea.mcp.json"
        run_dir = short_root / "analysis" / "runs" / "short-alias"
        context = prepare_rea(
            self.root, {"rea_mcp_config": str(config_path)}, run_dir, self.baseline
        )
        self.assertEqual(Path(context["evidence_path"]).resolve(strict=False),
                         (self.root / "analysis" / "runs" / "short-alias" / "analysis" / "rea-context.json"))

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

    def test_missing_or_remote_configuration_is_blocked(self):
        (self.config_dir / "rea.mcp.json").unlink()
        with self.assertRaisesRegex(ValueError, "config is missing"):
            prepare_rea(self.root, {}, self.run_dir, self.baseline)
        self.write_config({"mcpServers": {"rea": {"command": "https://example.invalid/mcp"}}})
        with self.assertRaisesRegex(ValueError, "not a URL"):
            prepare_rea(self.root, {}, self.run_dir, self.baseline)

    def test_other_servers_and_invalid_fields_are_blocked(self):
        self.write_config({"mcpServers": {"rea": self.server_spec, "other": self.server_spec}})
        with self.assertRaisesRegex(ValueError, "exactly one"):
            prepare_rea(self.root, {}, self.run_dir, self.baseline)
        self.write_config({"mcpServers": {"rea": {**self.server_spec, "url": "stdio://unexpected"}}})
        with self.assertRaisesRegex(ValueError, "only command, args, and env"):
            prepare_rea(self.root, {}, self.run_dir, self.baseline)

    def test_wrong_or_missing_baseline_hash_blocks(self):
        wrong = json.loads(json.dumps(self.baseline))
        wrong["files"]["PR2.exe"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match the baseline"):
            prepare_rea(self.root, {}, self.run_dir, wrong)
        missing = {"version": 1, "files": {}}
        with self.assertRaisesRegex(ValueError, "no valid PR2.exe hash"):
            prepare_rea(self.root, {}, self.run_dir, missing)


if __name__ == "__main__":
    unittest.main()
