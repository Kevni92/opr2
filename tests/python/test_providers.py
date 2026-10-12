import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from providers import build_command, run_provider, validate_result


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schema = self.root / "schema.json"
        self.schema.write_text('{"type":"object"}', encoding="utf-8")
        self.result = {"status": "completed", "summary": "Synthetic task", "tests": [], "risks": []}

    def test_codex_roles_have_distinct_sandbox_and_no_model_hardcoding(self):
        for role, sandbox in [("worker", "workspace-write"), ("reviewer", "read-only")]:
            args = build_command({"kind": "codex", "command": ["codex"]}, "chosen-model", role,
                                 self.root, self.schema, self.root / "result.json")
            self.assertEqual(args[args.index("--model") + 1], "chosen-model")
            self.assertEqual(args[args.index("--sandbox") + 1], sandbox)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", args)

    def test_claude_reviewer_has_no_write_or_shell_tools(self):
        args = build_command({"kind": "claude", "command": ["claude"]}, "chosen-model", "reviewer",
                             self.root, self.schema, self.root / "result.json")
        self.assertEqual(args[args.index("--tools") + 1], "Read,Glob,Grep")
        self.assertNotIn("--dangerously-skip-permissions", args)

    def test_only_worker_receives_private_analysis_write_directory(self):
        for kind in ["codex", "claude"]:
            for role in ["worker", "reviewer"]:
                args = build_command({"kind": kind, "command": [kind]}, "chosen-model", role,
                                     self.root, self.schema, self.root / "result.json", self.root / "private")
                self.assertEqual("--add-dir" in args, role == "worker")

    def test_rea_mcp_is_explicit_for_both_clients_and_static_tools_only(self):
        context = {"server": {"command": "rea", "args": ["mcp"], "env": {"JAVA_HOME": "C:\\Java"}},
                   "tools": ["open_binary", "analyze_function", "export_evidence_bundle"]}
        codex = build_command({"kind": "codex", "command": ["codex"]}, "chosen", "worker",
                              self.root, self.schema, self.root / "result.json", rea=context)
        override = next(arg for arg in codex if arg.startswith("mcp_servers.rea="))
        config = tomllib.loads(override)["mcp_servers"]["rea"]
        self.assertEqual(config["env"]["JAVA_HOME"], "C:\\Java")
        self.assertEqual(config["enabled_tools"], context["tools"])
        self.assertIn("--ignore-user-config", codex)
        claude = build_command({"kind": "claude", "command": ["claude"]}, "chosen", "reviewer",
                               self.root, self.schema, self.root / "result.json", rea=context)
        self.assertEqual(json.loads(claude[claude.index("--mcp-config") + 1])["mcpServers"]["rea"], context["server"])
        allowed = claude[claude.index("--allowedTools") + 1]
        self.assertIn("mcp__rea__analyze_function", allowed)
        self.assertNotIn("export_evidence_bundle", allowed)
        self.assertNotIn("observe_native_calls", allowed)

    def test_custom_adapter_receives_stdin_and_safe_literal_model(self):
        script = self.root / "fake.py"
        script.write_text("import json,sys,pathlib\n"
                          "prompt=sys.stdin.read()\n"
                          "assert prompt == 'A synthetic task'\n"
                          "assert sys.argv[2] == 'model; never a shell'\n"
                          "pathlib.Path(sys.argv[1]).write_text(" + repr(json.dumps(self.result)) + ",encoding='utf-8')\n",
                          encoding="utf-8")
        settings = {"kind": "command", "command": [sys.executable, str(script), "{output}", "{model}"]}
        result = run_provider(settings, "model; never a shell", "worker", self.root, self.schema,
                              self.root / "run", "A synthetic task", 10)
        self.assertEqual(result, self.result)

    def test_claude_envelope_normalization_and_error(self):
        def simulate(args, **kwargs):
            kwargs["stdout"].write(json.dumps({"is_error": False, "structured_output": self.result}))
            return subprocess.CompletedProcess(args, 0)
        with patch("providers.shutil.which", return_value="claude"), patch("providers.subprocess.run", side_effect=simulate):
            result = run_provider({"kind": "claude", "command": ["claude"]}, "any-model", "worker",
                                  self.root, self.schema, self.root / "claude-run", "task", 10)
        self.assertEqual(result, self.result)

    def test_invalid_result_fails_closed(self):
        for result in [None, {}, {**self.result, "status": "trust-me"}, {**self.result, "summary": ""},
                       {**self.result, "tests": "not a list"}]:
            with self.subTest(result=result), self.assertRaises(ValueError):
                validate_result(result, "worker")

    def test_missing_provider_does_not_fallback(self):
        with patch("providers.shutil.which", return_value=None), self.assertRaises(RuntimeError):
            run_provider({"kind": "codex", "command": ["absent-cli"]}, "any-model", "worker",
                         self.root, self.schema, self.root / "missing", "task", 10)


if __name__ == "__main__":
    unittest.main()
