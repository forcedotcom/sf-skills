#!/usr/bin/env python3
"""Contract tests for service-omni-skills-based-routing-configure/scripts/configure-and-report.sh."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import (  # noqa: E402
    FakeSf,
    _FAKE_SF_PROD,
    _FAKE_SF_SANDBOX,
    run,
)


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


class InputContractTests(unittest.TestCase):
    def test_missing_args_rejected(self):
        rc, out = run(["myorg"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_shaped_skill_name_rejected(self):
        rc, out = run(["myorg", "Bad Skill; DROP", "a@b.com"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid skill_developer_name", out)

    def test_missing_agents_rejected(self):
        rc, out = run(["myorg", "Omni_Demo_Voice"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("No agents supplied", out)


class ProductionGuardTests(unittest.TestCase):
    def test_refuses_production_org(self):
        with FakeSf(_FAKE_SF_PROD) as p:
            rc, out = run(["prodorg", "Omni_Demo_Voice", "agent1@example.com"], path_prefix=p)
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("production", v["blocking_issue"].lower())


class ConfigureTests(unittest.TestCase):
    def test_full_create_deploys_skill_and_binds(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Omni_Demo_Voice", "agent1@example.com,agent2@example.com"],
                          path_prefix=p, extra_env={"FAKE_SKILL_PRESENT": "0", "FAKE_BIND_PRESENT": "0"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "configured", out)
        self.assertEqual(v["skill_configured"]["state"], "created", out)
        self.assertEqual(v["created_counts"]["skill_bindings"], 2, out)
        self.assertNotIn("service_resources", v["created_counts"], out)
        self.assertTrue(all("skill_binding_id" in agent for agent in v["agents"]), out)

    def test_reused_when_all_present_no_writes(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Omni_Demo_Voice", "agent1@example.com,agent2@example.com"],
                          path_prefix=p, extra_env={"FAKE_SKILL_PRESENT": "1", "FAKE_BIND_PRESENT": "1",
                                                     "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "reused", out)
        self.assertNotIn("project deploy", log, "reused must not deploy the skill")
        self.assertNotIn("--method POST", log, "reused must not create bindings")

    def test_partial_when_one_binding_post_fails(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Omni_Demo_Voice", "agent1@example.com,agent2@example.com"],
                          path_prefix=p, extra_env={"FAKE_SKILL_PRESENT": "1", "FAKE_BIND_PRESENT": "0",
                                                     "FAKE_BIND_POST_FAIL": "1"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "partial", out)
        self.assertIn("skill binding failed", v["blocking_issue"])
        self.assertEqual(v["created_counts"]["skill_bindings"], 1, out)

    def test_duplicate_value_is_treated_as_reused(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Omni_Demo_Voice", "agent1@example.com,agent2@example.com"],
                          path_prefix=p, extra_env={"FAKE_SKILL_PRESENT": "1", "FAKE_BIND_PRESENT": "0",
                                                     "FAKE_BIND_DUPLICATE": "1"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertIsNone(v["blocking_issue"], out)
        self.assertNotEqual(v["status"], "partial", out)
        self.assertEqual(v["created_counts"]["skill_bindings"], 0, out)
        self.assertEqual(v["reused_counts"]["skill_bindings"], 2, out)

    def test_plan_only_reports_without_writing(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Omni_Demo_Voice", "agent1@example.com"],
                          path_prefix=p, extra_env={"FAKE_SKILL_PRESENT": "0", "PLAN_ONLY": "1",
                                                     "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertTrue(v.get("plan_mode"), out)
        self.assertEqual(v["status"], "action_needed", out)
        self.assertNotIn("project deploy", log, "plan mode must not deploy")
        self.assertNotIn("--method POST", log, "plan mode must not POST")


if __name__ == "__main__":
    unittest.main(verbosity=2)
