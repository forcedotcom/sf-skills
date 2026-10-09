#!/usr/bin/env python3
"""Contract tests for service-omni-presence-user-config-deploy/scripts/deploy-and-report.sh."""
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
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_shaped_config_name_rejected(self):
        rc, out = run(["org", "Bad Name; DROP"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid config_developer_name", out)

    def test_capacity_out_of_range_rejected(self):
        rc, out = run(["org", "Omni_Demo_Presence_Config"], scrub_sf=True,
                      extra_env={"CAPACITY": "0"})
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid CAPACITY", out)

    def test_acw_out_of_range_rejected(self):
        rc, out = run(["org", "Omni_Demo_Presence_Config"], scrub_sf=True,
                      extra_env={"ACW_SECONDS": "5"})
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid ACW_SECONDS", out)


class ProductionGuardTests(unittest.TestCase):
    def test_refuses_production_org(self):
        with FakeSf(_FAKE_SF_PROD) as p:
            rc, out = run(["prodorg"], path_prefix=p)
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("production", v["blocking_issue"].lower())


class DeployTests(unittest.TestCase):
    def test_created_reports_states_and_assignments(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Omni_Demo_Presence_Config", "agent1@example.com,agent2@example.com"],
                          path_prefix=p, extra_env={"FAKE_STATE_DR": "Created", "FAKE_STATE_PUC": "Created"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "created", out)
        self.assertEqual(v["config"]["state"], "Created", out)
        self.assertEqual(v["decline_reason"]["state"], "Created", out)
        self.assertEqual(v["config"]["acw_seconds"], 60, out)
        self.assertIn("agent1@example.com", v["assigned_usernames"], out)
        self.assertIn("agent2@example.com", v["assigned_usernames"], out)

    def test_reused_when_both_unchanged(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p,
                          extra_env={"FAKE_STATE_DR": "Unchanged", "FAKE_STATE_PUC": "Unchanged"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "reused", out)

    def test_updated_when_config_changed(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p,
                          extra_env={"FAKE_STATE_DR": "Unchanged", "FAKE_STATE_PUC": "Changed"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "updated", out)

    def test_deploy_failure_points_at_base_settings(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p, extra_env={"FAKE_DEPLOY_FAIL": "1"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertTrue(any(a.get("target_skill") == "service-omni-base-settings-configure"
                            for a in v["manual_actions"]), out)

    def test_empty_status_on_decline_does_not_swallow_unrelated_failure(self):
        # Regression (blocker 3): with PRESENCE_STATUS_ON_DECLINE="" the presence-status case arm was
        # effectively `*""*`, matching EVERY failure and misreporting an unrelated deploy error as a
        # missing presence status. An unrelated failure must now surface as the generic message.
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p, extra_env={
                "FAKE_DEPLOY_FAIL": "1",
                "FAKE_DEPLOY_PROBLEM": "FIELD_CUSTOM_VALIDATION_EXCEPTION: unrelated failure",
                "PRESENCE_STATUS_ON_DECLINE": "",
            })
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("FIELD_CUSTOM_VALIDATION_EXCEPTION", v["blocking_issue"], out)
        self.assertNotIn("presenceStatusOnDecline", v["blocking_issue"], out)
        self.assertFalse(any(a.get("target_skill") == "service-omni-presence-status-deploy"
                             for a in v.get("manual_actions", [])), out)

    def test_plan_only_reports_without_deploying(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Omni_Demo_Presence_Config", "agent1@example.com"],
                          path_prefix=p, extra_env={"PLAN_ONLY": "1", "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertTrue(v.get("plan_mode"), out)
        self.assertEqual(v["status"], "action_needed", out)
        self.assertNotIn("project deploy", log, "plan mode must not deploy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
