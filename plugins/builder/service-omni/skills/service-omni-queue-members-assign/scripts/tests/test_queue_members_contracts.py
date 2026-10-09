#!/usr/bin/env python3
"""Contract tests for service-omni-queue-members-assign/scripts/verify-and-bind.sh."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _bootstrap import (  # noqa: E402
    SCRIPT,
    SKILLS_ROOT,
    FakeSf,
    _FAKE_SF_ORG_QUERY_FAILS,
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


class SyntaxTests(unittest.TestCase):
    def test_bash_syntax_valid(self):
        proc = subprocess.run(["bash", "-n", str(SKILLS_ROOT / SCRIPT)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class InputContractTests(unittest.TestCase):
    def test_missing_args_rejected(self):
        rc, out = run([], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Usage", out)

    def test_injection_shaped_queue_name_rejected(self):
        rc, out = run(["org", "Bad Name; DROP"], scrub_sf=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("Invalid queue_developer_name", out)


class OrgQueryFailClosedTests(unittest.TestCase):
    def test_org_query_failure_emits_blocked_json_on_stdout(self):
        # Regression (blocker 2): a failing Organization safe_to_write query used to make the command
        # substitution non-zero and `set -e` killed the script before any JSON. It must now fail closed
        # with a structured blocked result on stdout.
        with FakeSf(_FAKE_SF_ORG_QUERY_FAILS) as p:
            rc, out = run(["sandbox", "CaseQueue"], path_prefix=p)
        self.assertEqual(rc, 1, out)
        self.assertTrue(out.strip(), "expected structured JSON, got empty output")
        v = _last_json(out)
        self.assertEqual(v["status"], "blocked", out)
        self.assertIn("Organization", v["blocking_issue"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
