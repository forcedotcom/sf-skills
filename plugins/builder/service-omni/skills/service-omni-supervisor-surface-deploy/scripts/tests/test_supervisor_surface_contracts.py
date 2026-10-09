#!/usr/bin/env python3
"""Contract tests for service-omni-supervisor-surface-deploy/scripts/deploy-and-report.sh."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import FakeSf, _FAKE_SF, run  # noqa: E402


def _last_json(out: str) -> dict:
    dec = json.JSONDecoder()
    obj, i, n = None, 0, len(out)
    while i < n:
        if out[i] in "{[":
            try:
                cand, end = dec.raw_decode(out, i)
                if isinstance(cand, dict):
                    obj = cand
                i = end
                continue
            except json.JSONDecodeError:
                pass
        i += 1
    assert obj is not None, f"no JSON object found in output:\n{out}"
    return obj


def _detect(env=None, args=("org",)):
    with FakeSf(_FAKE_SF) as p:
        return run(list(args), path_prefix=p, extra_env=env or {})


class InputContractTests(unittest.TestCase):
    def test_missing_args_rejected(self):
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_bad_config_name_rejected(self):
        rc, out = run(["org", "1badname"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid config_developer_name", out)

    def test_reference_required_action_blocked(self):
        rc, out = _detect({"SUPERVISOR_ACTIONS": "AllAgents.CustomAction"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("external reference", v["blocking_issue"], out)

    def test_reference_required_tab_blocked(self):
        rc, out = _detect({"SUPERVISOR_TABS": "FlexipageType"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)

    def test_unsupported_type_blocked(self):
        rc, out = _detect({"SUPERVISOR_TABS": "NotARealTab"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("Unsupported tab type", v["blocking_issue"], out)


class SafetyAndResolutionTests(unittest.TestCase):
    def test_production_org_blocked(self):
        rc, out = _detect({"FAKE_SANDBOX": "false"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("production", v["blocking_issue"], out)

    def test_no_config_blocks_with_pointer(self):
        rc, out = _detect({"FAKE_CFG_COUNT": "0"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertTrue(any(a.get("target_skill") == "service-omni-supervisor-config-deploy"
                            for a in v["manual_actions"]), out)

    def test_multiple_configs_without_name_blocks(self):
        rc, out = _detect({"FAKE_CFG_COUNT": "2"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("Multiple", v["blocking_issue"], out)


class StateModelTests(unittest.TestCase):
    def test_created_on_empty_surface(self):
        rc, out = _detect({"FAKE_EXIST_ACTIONS": "[]", "FAKE_EXIST_TABS": "[]"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "created", out)
        self.assertEqual(len(v["actions"]["created"]), 5, out)
        self.assertEqual(len(v["tabs"]["created"]), 5, out)
        self.assertEqual(v["actions"]["reused"], [], out)

    def test_reused_when_all_present(self):
        acts = json.dumps(["AllAgents.ChangeQueues", "AllAgents.ChangeSkills",
                           "AllAgents.ChangeGroups", "AllAgents.AssignLearning",
                           "QueuesBacklog.ManageQueues"])
        tabs = json.dumps(["Wallboard", "Agents", "QueuesBacklog", "AssignedWork", "SkillsBacklog"])
        rc, out = _detect({"FAKE_EXIST_ACTIONS": acts, "FAKE_EXIST_TABS": tabs})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "reused", out)
        self.assertEqual(v["actions"]["created"], [], out)
        self.assertEqual(v["tabs"]["created"], [], out)

    def test_partial_diff_inserts_only_missing(self):
        rc, out = _detect({
            "FAKE_EXIST_ACTIONS": json.dumps(["AllAgents.ChangeQueues"]),
            "FAKE_EXIST_TABS": json.dumps(["Wallboard"]),
        })
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "created", out)
        self.assertIn("AllAgents.ChangeQueues", v["actions"]["reused"], out)
        self.assertNotIn("AllAgents.ChangeQueues", v["actions"]["created"], out)
        self.assertEqual(len(v["actions"]["created"]), 4, out)
        self.assertEqual(len(v["tabs"]["created"]), 4, out)

    def test_plan_only_makes_no_writes(self):
        rc, out = _detect({"PLAN_ONLY": "1"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "action_needed", out)
        self.assertTrue(v["plan_mode"], out)
        self.assertEqual(v["actions"]["created"], [], out)

    def test_insert_failure_blocks(self):
        rc, out = _detect({"FAKE_CREATE_OK": "false"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("Failed to insert", v["blocking_issue"], out)

    def test_custom_tab_set_honored(self):
        rc, out = _detect({"SUPERVISOR_TABS": "Wallboard,Reports,Alerts",
                           "SUPERVISOR_ACTIONS": "AllAgents.ChangeQueues"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "created", out)
        self.assertEqual(sorted(v["tabs"]["created"]), ["Alerts", "Reports", "Wallboard"], out)
        self.assertEqual(v["actions"]["created"], ["AllAgents.ChangeQueues"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
