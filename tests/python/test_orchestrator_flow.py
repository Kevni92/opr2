import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import orchestrator


class OrchestratorFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.events_file = self.base / "events.txt"
        self.fake_provider = self.base / "fake_provider.py"
        self.fake_provider.write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "role, workspace, output = sys.argv[1:4]\n"
            "Path(os.environ['FLOW_EVENTS']).open('a').write(role + '\\n')\n"
            "sys.stdin.read()\n"
            "if role == 'worker':\n"
            " Path(workspace, 'src/example.cpp').write_text('int answer() { return 42; }\\n', encoding='utf-8')\n"
            " result = {'status':'completed','summary':'synthetic change','tests':[],'risks':[]}\n"
            "else:\n"
            " verdict = os.environ.get('FAKE_REVIEW', 'approve')\n"
            " result = {'verdict':verdict,'summary':'synthetic review','findings':([] if verdict == 'approve' else ['synthetic finding'])}\n"
            "Path(output).write_text(json.dumps(result), encoding='utf-8')\n",
            encoding="utf-8",
        )
        self._write("AGENTS.md", "Follow the synthetic test policy.\n")
        self._write(".gitignore", "analysis/\n.worktrees/\nbuild/\n")
        self._write("automation/worker-result.schema.json", "{}\n")
        self._write("automation/review-result.schema.json", "{}\n")
        self._write("tools/validate.py", "# intercepted by the synthetic integration test\n")
        self._write("src/example.cpp", "int answer() { return 0; }\n")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Synthetic Test")
        self.git("add", ".")
        self.git("commit", "-qm", "initial synthetic tree")
        self.base_oid = self.git("rev-parse", "HEAD").strip()
        self.remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", "-q", str(self.remote)], check=True)
        subprocess.run(["git", "--git-dir", str(self.remote), "fetch", "-q", str(self.root),
                        "main:refs/heads/main"], check=True)
        self.git("remote", "add", "origin", str(self.remote))
        self.plan = {
            "issue": {"number": 7, "title": "Synthetic issue", "body": "Bounded fixture",
                      "state": "OPEN", "labels": [{"name": "agent:ready"}]},
            "task": {"version": 1, "complexity": "small", "allowed_paths": ["src/"],
                     "dependencies": [], "requires_original_data": False,
                     "acceptance": ["Change the synthetic example"]},
            "worker_provider": "fake", "review_provider": "fake",
            "worker_model": "synthetic", "review_model": "synthetic",
        }
        self.config = {
            "repository": "synthetic/project", "base_branch": "main",
            "required_check": "validation-required", "ci_timeout_seconds": 1,
            "provider_timeout_seconds": 10,
            "providers": {"fake": {"kind": "command", "command": [
                sys.executable, str(self.fake_provider), "{role}", "{workspace}", "{output}"]}},
        }

    def tearDown(self):
        for worktree in (self.root / ".worktrees").glob("*"):
            subprocess.run(["git", "-C", str(self.root), "worktree", "remove", "--force", str(worktree)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def process(self, *, review="approve", validation_fails=False, stale_base=False):
        events = []
        state = {"head": None}
        real_command = orchestrator.command
        protection = {"required_status_checks": {"strict": True,
                      "contexts": ["validation-required"], "checks": []}}

        def record(event):
            events.append(event)
            with self.events_file.open("a", encoding="utf-8") as stream:
                stream.write(event + "\n")

        def fake_command(argv, cwd, *, capture=True):
            if argv[0] == "gh":
                if argv[1:2] == ["api"]:
                    record("protection")
                    return json.dumps(protection)
                if argv[1:3] == ["pr", "create"]:
                    record("pr-create")
                    return "https://example.invalid/pull/7"
                if argv[1:3] == ["pr", "view"]:
                    record("pr-view")
                    pr = {"number": 7, "state": "OPEN", "isDraft": False, "baseRefName": "main",
                          "baseRefOid": "f" * 40 if stale_base else self.base_oid,
                          "headRefOid": state["head"], "mergeStateStatus": "CLEAN",
                          "statusCheckRollup": [{"name": "validation-required", "conclusion": "SUCCESS"}]}
                    return json.dumps(pr)
                if argv[1:3] == ["pr", "merge"]:
                    record("merge")
                    return ""
                if argv[1:3] == ["issue", "edit"]:
                    record("label")
                    return ""
                raise AssertionError(f"unexpected GitHub command: {argv}")
            if argv[0] == sys.executable and any(
                    Path(str(arg)).name == "validate.py" and Path(str(arg)).parent.name == "tools"
                    for arg in argv[1:]):
                record("validation")
                if validation_fails:
                    raise subprocess.CalledProcessError(1, argv)
                return ""
            if argv[:2] == ["git", "push"]:
                record("push")
                state["head"] = real_command(["git", "rev-parse", "HEAD"], cwd)
                return ""
            return real_command(argv, cwd, capture=capture)

        args = Namespace(issue=7, no_merge=False)
        env = {"FLOW_EVENTS": str(self.events_file), "FAKE_REVIEW": review}
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(orchestrator, "command", side_effect=fake_command):
            orchestrator.process(self.root, args, self.config, self.plan)
        return self.events_file.read_text(encoding="utf-8").splitlines()

    def test_happy_flow_reviews_before_validation_and_merges(self):
        events = self.process()
        self.assertLess(events.index("reviewer"), events.index("validation"))
        self.assertLess(events.index("validation"), events.index("push"))
        self.assertLess(events.index("push"), events.index("merge"))

    def test_review_rejection_stops_validation_push_and_merge(self):
        with self.assertRaisesRegex(ValueError, "independent review requested changes"):
            self.process(review="request_changes")
        events = self.events_file.read_text(encoding="utf-8")
        self.assertIn("reviewer", events)
        self.assertNotIn("validation", events)
        self.assertNotIn("push", events)
        self.assertNotIn("merge", events)

    def test_validation_failure_stops_push_and_merge(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.process(validation_fails=True)
        events = self.events_file.read_text(encoding="utf-8")
        self.assertLess(events.index("reviewer"), events.index("validation"))
        self.assertNotIn("push", events)
        self.assertNotIn("merge", events)

    def test_stale_base_blocks_merge(self):
        with self.assertRaisesRegex(ValueError, "base branch changed"):
            self.process(stale_base=True)
        events = self.events_file.read_text(encoding="utf-8").splitlines()
        self.assertIn("push", events)
        self.assertIn("pr-view", events)
        self.assertNotIn("merge", events)


if __name__ == "__main__":
    unittest.main()
