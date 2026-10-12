import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from orchestrator import merge_gate, parse_contract, protection_gate, scope_violations


class TaskContractTests(unittest.TestCase):
    def setUp(self):
        self.task = {"version": 1, "complexity": "small", "allowed_paths": ["src/", "tests/cpp/"],
                     "dependencies": [2], "requires_original_data": False, "acceptance": ["A real behavior"]}

    def parse(self, task):
        return parse_contract("## Task contract\n```json\n" + json.dumps(task) + "\n```\n")

    def test_roundtrip_and_literal_scope(self):
        self.assertEqual(self.parse(self.task), self.task)
        self.assertEqual(scope_violations(["src/main.cpp", "tests/cpp/test.cpp", "README.md"],
                                         self.task["allowed_paths"]), ["README.md"])
        self.assertEqual(scope_violations(["src-other/a.cpp"], ["src/"]), ["src-other/a.cpp"])

    def test_private_and_policy_paths_rejected(self):
        for path in ["pr2/", "PR2/", "analysis/", "tools/", ".github/", "AGENTS.md", "automation/"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.parse({**self.task, "allowed_paths": [path]})

    def test_unsafe_scopes_rejected(self):
        for path in ["../pr2/", "/src/", "C:/src/", "src/../pr2", "src/**", "src\\", ".", "", "src/.", "src//a"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.parse({**self.task, "allowed_paths": [path]})

    def test_large_ambiguous_or_missing_contract_rejected(self):
        with self.assertRaises(ValueError):
            self.parse({**self.task, "complexity": "large"})
        with self.assertRaises(ValueError):
            self.parse({**self.task, "acceptance": []})
        with self.assertRaises(ValueError):
            parse_contract("please just implement anything")
        body = "```json\n" + json.dumps(self.task) + "\n```\n"
        with self.assertRaises(ValueError):
            parse_contract(body + body)

    def test_rea_capability_requires_explicit_original_data_contract(self):
        valid = {**self.task, "capabilities": ["rea"], "requires_original_data": True}
        self.assertEqual(self.parse(valid), valid)
        for fields in [{"capabilities": ["rea"]}, {"capabilities": ["runtime"]},
                       {"capabilities": "rea"}, {"version": True}]:
            with self.assertRaises(ValueError):
                self.parse({**self.task, **fields})


class MergeGateTests(unittest.TestCase):
    def setUp(self):
        self.head = "a" * 40
        self.base = "b" * 40
        self.pr = {"state": "OPEN", "isDraft": False, "baseRefName": "main", "headRefOid": self.head,
                   "baseRefOid": self.base,
                   "mergeStateStatus": "CLEAN", "statusCheckRollup": [
                       {"name": "validation-required", "conclusion": "SUCCESS"},
                       {"name": "validation (windows-msvc)", "conclusion": "SUCCESS"}]}
        self.review = {"head": self.head, "verdict": "approve", "findings": []}

    def test_changed_base_and_non_strict_server_protection_rejected(self):
        self.assertTrue(merge_gate({**self.pr, "baseRefOid": "c" * 40}, self.head, self.review,
                                  "validation-required", self.base))
        protection_gate({"required_status_checks": {"strict": True, "contexts": ["validation-required"]}},
                        "validation-required")
        for protection in [{}, {"required_status_checks": {"strict": False, "contexts": ["validation-required"]}},
                           {"required_status_checks": {"strict": True, "contexts": []}}]:
            with self.assertRaises(ValueError):
                protection_gate(protection, "validation-required")

    def test_current_green_review_allows_merge(self):
        self.assertEqual(merge_gate(self.pr, self.head, self.review, "validation-required", self.base), [])

    def test_stale_review_or_pr_head_rejected(self):
        self.assertTrue(merge_gate(self.pr, self.head, {**self.review, "head": "b" * 40}, "validation-required", self.base))
        self.assertTrue(merge_gate({**self.pr, "headRefOid": "b" * 40}, self.head, self.review, "validation-required", self.base))

    def test_missing_failed_pending_duplicate_checks_rejected(self):
        for checks in [[], [{"name": "validation-required", "conclusion": None}],
                       [{"name": "validation-required", "conclusion": "FAILURE"}],
                       self.pr["statusCheckRollup"] + [self.pr["statusCheckRollup"][0]],
                       self.pr["statusCheckRollup"] + [{"name": "other", "conclusion": "FAILURE"}],
                       self.pr["statusCheckRollup"] + [{"name": "other", "conclusion": "SKIPPED"}]]:
            with self.subTest(checks=checks):
                self.assertTrue(merge_gate({**self.pr, "statusCheckRollup": checks}, self.head,
                                          self.review, "validation-required", self.base))

    def test_review_findings_draft_wrong_base_or_conflict_rejected(self):
        self.assertTrue(merge_gate(self.pr, self.head, {**self.review, "findings": ["bug"]}, "validation-required", self.base))
        for updates in [{"isDraft": True}, {"baseRefName": "other"}, {"state": "CLOSED"},
                        {"mergeStateStatus": "DIRTY"}, {"mergeStateStatus": "BEHIND"}]:
            self.assertTrue(merge_gate({**self.pr, **updates}, self.head, self.review, "validation-required", self.base))


if __name__ == "__main__":
    unittest.main()
