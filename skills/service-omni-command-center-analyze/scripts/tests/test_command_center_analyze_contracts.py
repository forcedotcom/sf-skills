#!/usr/bin/env python3
"""Contract tests for service-omni-command-center-analyze/scripts/analyze.sh (read-only state model)."""
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


class InputContractTests(unittest.TestCase):
    def test_missing_args_rejected(self):
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_bad_supervisor_token_rejected(self):
        with FakeSf(_FAKE_SF) as p:
            rc, out = run(["org", "not-a-user-or-id"], path_prefix=p, extra_env={"FAKE_CAP": "true"})
        self.assertEqual(rc, 1, out)
        self.assertIn("neither a Username", out)


class StateModelTests(unittest.TestCase):
    def _detect(self, env, args=("org",)):
        with FakeSf(_FAKE_SF) as p:
            return run(list(args), path_prefix=p, extra_env=env)

    def test_legacy_when_capability_absent(self):
        rc, out = self._detect({"FAKE_CAP": "false"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "legacy_selected", out)
        self.assertEqual(v["recommended_skill"], "service-omni-supervisor-config-deploy", out)
        self.assertEqual(v["signals"]["v2_capability"], "false", out)

    def test_ambiguous_when_capability_unknown_blocks(self):
        rc, out = self._detect({"FAKE_CAP": "unknown"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "ambiguous", out)
        self.assertEqual(v["status"], "blocked", out)

    def test_ambiguous_when_seed_unreadable_blocks(self):
        rc, out = self._detect({"FAKE_CAP": "true", "FAKE_SEED": "unknown"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "ambiguous", out)

    def test_available_not_enabled_when_no_seed(self):
        rc, out = self._detect({"FAKE_CAP": "true", "FAKE_SEED": "false", "FAKE_TAB": "false"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_available_not_enabled", out)
        self.assertTrue(any(a["id"] == "ENABLE_V2_PREF" for a in v["manual_actions"]), out)

    def test_ready_org_level_without_supervisor(self):
        rc, out = self._detect({"FAKE_CAP": "true", "FAKE_SEED": "true", "FAKE_TAB": "true"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_ready", out)
        self.assertFalse(v["signals"]["supervisor"]["checked"], out)

    def test_ready_with_supervisor_having_permission(self):
        rc, out = self._detect(
            {"FAKE_CAP": "true", "FAKE_SEED": "true", "FAKE_TAB": "true", "FAKE_SUP_PERM": "true"},
            args=("org", "sup@example.com"))
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_ready", out)
        self.assertTrue(v["signals"]["supervisor"]["checked"], out)
        self.assertTrue(v["signals"]["supervisor"]["has_command_center_permission"], out)

    def test_permission_missing_when_supervisor_lacks_perm(self):
        rc, out = self._detect(
            {"FAKE_CAP": "true", "FAKE_SEED": "true", "FAKE_TAB": "true", "FAKE_SUP_PERM": "false"},
            args=("org", "005000000000002AAA"))
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_permission_missing", out)
        self.assertIsNone(v["recommended_skill"], out)
        self.assertTrue(any(a["id"] == "ASSIGN_V2_PERM" for a in v["manual_actions"]), out)
        self.assertFalse(v["signals"]["supervisor"]["has_command_center_permission"], out)

    def test_missing_supplied_supervisor_blocks(self):
        rc, out = self._detect(
            {
                "FAKE_CAP": "true",
                "FAKE_SEED": "true",
                "FAKE_TAB": "true",
                "FAKE_SUP_LOOKUP": "missing",
            },
            args=("org", "sup@example.com"))
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "ambiguous", out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("was not found", v["blocking_issue"], out)
        self.assertFalse(v["signals"]["supervisor"]["checked"], out)

    def test_unreadable_supplied_supervisor_blocks(self):
        rc, out = self._detect(
            {
                "FAKE_CAP": "true",
                "FAKE_SEED": "true",
                "FAKE_TAB": "true",
                "FAKE_SUP_LOOKUP": "unknown",
            },
            args=("org", "005000000000002AAA"))
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "ambiguous", out)
        self.assertIn("could not be read", v["blocking_issue"], out)

    def test_unreadable_supervisor_permission_blocks(self):
        rc, out = self._detect(
            {
                "FAKE_CAP": "true",
                "FAKE_SEED": "true",
                "FAKE_TAB": "true",
                "FAKE_SUP_PERM": "unknown",
            },
            args=("org", "sup@example.com"))
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "ambiguous", out)
        self.assertIn("permission could not be read", v["blocking_issue"], out)

    def test_seed_incomplete_when_seed_without_tab(self):
        rc, out = self._detect({"FAKE_CAP": "true", "FAKE_SEED": "true", "FAKE_TAB": "false"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_seed_incomplete", out)

    def test_ready_when_tab_unknown(self):
        rc, out = self._detect({"FAKE_CAP": "true", "FAKE_SEED": "true", "FAKE_TAB": "unknown"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["state"], "v2_ready", out)
        self.assertEqual(v["signals"]["v2_tab_present"], "unknown", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
