#!/usr/bin/env python3
"""Contract tests for service-omni-sidebar-configure/scripts/enable-and-report.sh.

Run standalone: ``python3 test_sidebar_contracts.py`` (or under pytest / unittest discovery).
"""
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
    """Parse the last JSON object printed to stdout+stderr."""
    dec = json.JSONDecoder()
    obj, i, n = None, 0, len(out)
    while i < n:
        ch = out[i]
        if ch in "{[":
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
    """Argument guarantees must hold before any `sf` call (PATH has no sf)."""

    def test_missing_org_rejected(self):
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_shaped_app_name_rejected(self):
        rc, out = run(["myorg", "Bad Name; DROP"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid app_developer_name", out)


class ProductionGuardTests(unittest.TestCase):
    def test_refuses_production_org(self):
        with FakeSf(_FAKE_SF_PROD) as p:
            rc, out = run(["prodorg", "Demo_Console"], path_prefix=p)
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("production", v["blocking_issue"].lower())


class AutoDetectTests(unittest.TestCase):
    def test_blocks_when_no_console_app(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p, extra_env={"FAKE_CONSOLE_APPS": "0"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("No deployable custom Lightning console app", v["blocking_issue"])

    def test_blocks_when_multiple_console_apps(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p, extra_env={"FAKE_CONSOLE_APPS": "2"})
        self.assertEqual(rc, 1, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("explicit app_developer_name", v["blocking_issue"])

    def test_adopts_single_console_app(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox"], path_prefix=p, extra_env={"FAKE_CONSOLE_APPS": "1"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["app_developer_name"], "Demo_Console", out)

    def test_autodetect_uses_deployable_custom_application_metadata(self):
        src = (Path(__file__).resolve().parents[1] / "enable-and-report.sh").read_text()
        start = src.index("APP_METADATA_JSON=$(sf org list metadata")
        block = src[start:src.index("APP_COUNT=", start)]
        self.assertIn("--metadata-type CustomApplication", block)
        self.assertIn('startswith("standard__") | not', block)
        self.assertIn("<navType>Console</navType>", block)


class EnableAndReuseTests(unittest.TestCase):
    def test_enables_when_absent_and_verifies_roundtrip(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            rc, out = run(["sandbox", "Demo_Console"], path_prefix=p,
                          extra_env={"FAKE_APP_PINNED": "0"})
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "enabled", out)
        self.assertFalse(v["before"], out)
        self.assertTrue(v["after"], out)
        self.assertIsNotNone(v["deploy_id"], out)

    def test_reused_when_already_pinned_without_deploy(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Demo_Console"], path_prefix=p,
                          extra_env={"FAKE_APP_PINNED": "1", "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertEqual(v["status"], "reused", out)
        self.assertTrue(v["before"], out)
        self.assertTrue(v["after"], out)
        self.assertNotIn("project deploy", log, "reused path must not deploy")

    def test_plan_only_reports_action_without_writing(self):
        with FakeSf(_FAKE_SF_SANDBOX) as p:
            calllog = str(Path(p) / "calls.log")
            rc, out = run(["sandbox", "Demo_Console"], path_prefix=p,
                          extra_env={"FAKE_APP_PINNED": "0", "PLAN_ONLY": "1",
                                     "FAKE_SF_CALLLOG": calllog})
            log = Path(calllog).read_text() if Path(calllog).exists() else ""
        self.assertEqual(rc, 0, out)
        v = _last_json(out)
        self.assertTrue(v.get("plan_mode"), out)
        self.assertEqual(v["status"], "action_needed", out)
        self.assertNotIn("project deploy", log, "plan mode must not deploy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
