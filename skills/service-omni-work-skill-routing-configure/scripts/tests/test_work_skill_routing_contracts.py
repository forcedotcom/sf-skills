#!/usr/bin/env python3
"""Contract tests for service-omni-work-skill-routing-configure/scripts/configure-and-report.sh."""
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
        rc, out = run(["myorg", "Case", "Origin"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_shaped_skill_rejected(self):
        rc, out = run(["myorg", "Case", "Origin", "Bad; DROP", "Phone"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid skill", out)

    def test_xml_injection_value_rejected(self):
        rc, out = run(["myorg", "Case", "Origin", "Voice", "<x>&bad"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid value", out)

    def test_bad_related_entity_rejected(self):
        rc, out = run(["myorg", "Case Origin", "Origin", "Voice", "Phone"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid related_entity", out)

    def test_out_of_range_skill_level_rejected(self):
        rc, out = run(["myorg", "Case", "Origin", "Voice", "Phone"], scrub_sf=True,
                      extra_env={"SKILL_LEVEL": "11"})
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid SKILL_LEVEL", out)


class ProductionGuardTests(unittest.TestCase):
    def test_refuses_production_org(self):
        with FakeSf(_FAKE_SF_PROD) as p:
            rc, out = run(["prodorg", "Case", "Origin", "Voice", "Phone"], path_prefix=p)
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("production", v["blocking_issue"].lower())


class ConfigureTests(unittest.TestCase):
    def test_create_deploys_rule(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Case.Origin", "Voice", "Phone"], path_prefix=p,
                          extra_env={"FAKE_STATE_WSR": "Created"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "created", out)
        self.assertEqual(v["rule"]["related_entity"], "Case", out)
        self.assertEqual(v["attribute"]["skill"], "Voice", out)
        self.assertEqual(v["attribute"]["value"], "Phone", out)

    def test_bare_standard_field_is_entity_qualified(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Priority", "Voice", "High"], path_prefix=p,
                          extra_env={"FAKE_STATE_WSR": "Created"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(_last_json(out)["attribute"]["field"], "Case.Priority", out)

    def test_reused_when_unchanged(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice", "Phone"], path_prefix=p,
                          extra_env={"FAKE_STATE_WSR": "Unchanged"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "reused", out)

    def test_blocks_when_referenced_skill_missing(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice", "Phone"], path_prefix=p,
                          extra_env={"FAKE_SKILL_PRESENT": "0"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertTrue(any(a.get("target_skill") == "service-omni-skills-based-routing-configure"
                            for a in v["manual_actions"]), out)

    def test_graceful_degrade_when_feature_unavailable(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice", "Phone"], path_prefix=p,
                          extra_env={"FAKE_DEPLOY_FAIL": "1"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("not available", v["blocking_issue"].lower())

    def test_plan_only_reports_without_writing(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Case", "Origin", "Voice", "Phone"], path_prefix=p,
                          extra_env={"PLAN_ONLY": "1", "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertTrue(v.get("plan_mode"), out)
        self.assertEqual(v["status"], "action_needed", out)
        self.assertNotIn("project deploy", log, "plan mode must not deploy")


class MergeSafeTests(unittest.TestCase):
    def test_preserves_existing_mapping(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice_Support", "Phone"], path_prefix=p,
                          extra_env={"FAKE_WSR_EXISTING": "1", "FAKE_STATE_WSR": "Changed"})
        self.assertEqual(rc, 0, out)
        merge = _last_json(out)["merge"]
        self.assertEqual(merge["attribute_count"], 2, out)
        self.assertEqual(merge["preserved_count"], 1, out)

    def test_omits_null_optional_values_from_preserved_mapping(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice_Support", "Phone"], path_prefix=p,
                          extra_env={"FAKE_WSR_EXISTING": "1", "FAKE_WSR_NULL_OPTIONALS": "1",
                                     "FAKE_STATE_WSR": "Changed"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(_last_json(out)["merge"]["preserved_count"], 1, out)

    def test_inconclusive_read_blocks_destructive_replace(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Case", "Origin", "Voice_Support", "Phone"], path_prefix=p,
                          extra_env={"FAKE_WSR_INCONCLUSIVE": "1"})
        self.assertEqual(rc, 1, out)
        self.assertIn("WSR_REPLACE", _last_json(out)["blocking_issue"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
