#!/usr/bin/env python3
"""Focused behavior proofs for additive journey v2 JSON and read-only inspect."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
sfx = load_module(SCRIPTS / "sf_context.py", "sf_context_journey_inspect")


class JourneyV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        (self.root / "sfdx-project.json").write_text("{}", encoding="utf-8")
        self.config = mock.patch.object(sfx, "_configured_target_alias", return_value="fixture")
        self.config.start()

    def tearDown(self):
        self.config.stop()
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    def derive(self):
        return sfx._derive_journey_state(
            self.root, has_project=True, target="fixture", target_error=None,
            org_display={"alias": "fixture"})

    def write_history(self, records):
        history = self.root / ".sf" / "phase-history.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    def test_v2_is_additive_and_preserves_existing_status_contract(self):
        state = self.derive()
        # Compatibility snapshot of all pre-v2 top-level values except the long,
        # already-goldened boundary prose; v2 fields are strictly additive.
        self.assertEqual(state["mode"], "journey")
        self.assertEqual(state["currentStage"], "Build")
        self.assertEqual(state["reason"],
                         "Project and reachable org are available; the journey cursor rests at Build.")
        self.assertEqual([s["status"] for s in state["stages"]],
                         ["complete", "complete", "current", "future", "future", "future"])
        self.assertEqual(state["context"], {
            "project": self.root.name, "orgAlias": "fixture", "orgStatus": "reachable",
            "sourceTracking": "unknown",
        })
        self.assertTrue(state["inferenceBounded"])
        self.assertEqual(state["schemaVersion"], 2)
        self.assertEqual(state["cursor"], state["currentStage"])
        self.assertEqual(state["reached"], ["Connect", "Project"])
        self.assertFalse(state["allReached"])
        self.assertTrue(all(s["evidence"] == [] for s in state["stages"]))

    def test_fully_reached_observe_is_current_reached_and_iterating(self):
        classes = self.root / "force-app/main/default/classes"
        classes.mkdir(parents=True)
        (classes / "Example.cls").write_text("class Example {}", encoding="utf-8")
        (classes / "ExampleTest.cls").write_text("@isTest class ExampleTest {}", encoding="utf-8")
        records = [
            {"type": "test-run", "stage": "Test", "outcome": "passed"},
            {"type": "deploy", "stage": "Deploy", "outcome": "passed"},
            {"type": "observe", "stage": "Observe", "outcome": "passed"},
        ]
        self.write_history(records)
        state = self.derive()
        self.assertTrue(state["allReached"])
        self.assertEqual(state["cursor"], "Observe")
        self.assertEqual(state["stages"][-1]["status"], "current")
        self.assertEqual(state["reached"], list(sfx.JOURNEY_STAGES))
        facts = sfx._journey_micro_facts(state, history=records)
        self.assertEqual(facts["substate"], "iterating")
        self.assertTrue(facts["reached"])
        self.assertEqual(facts["events"][0]["outcome"], "passed")


class JourneyInspectTests(unittest.TestCase):
    def capture(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sfx.cmd_journey(args)
        return code, out.getvalue(), err.getvalue()

    def test_missing_and_corrupt_history_are_honest(self):
        empty = sfx.PhaseHistoryResult(0, 0, False, [])
        with mock.patch.object(sfx, "_phase_history_present", return_value=False), \
                mock.patch.object(sfx, "_load_phase_history_result", return_value=empty):
            self.assertEqual(sfx._journey_inspection()["status"], "missing")
        corrupt = sfx.PhaseHistoryResult(0, 3, False, [])
        with mock.patch.object(sfx, "_phase_history_present", return_value=True), \
                mock.patch.object(sfx, "_load_phase_history_result", return_value=corrupt):
            inspected = sfx._journey_inspection()
        self.assertEqual(inspected["status"], "corrupt")
        self.assertEqual(inspected["counts"], {"accepted": 0, "rejected": 3, "truncated": False})

    def test_partial_truncated_counts_and_evidence_are_bounded_and_redacted(self):
        current = {"schemaVersion": 1, "type": "deploy", "stage": "Deploy",
                   "outcome": "passed", "source": "cmd_post_deploy",
                   "ts": "2026-08-02T10:00:00+00:00", "orgHash": "a" * 64}
        other = {**current, "orgHash": "b" * 64}
        legacy = {key: value for key, value in current.items() if key != "orgHash"}
        records = [current, other, legacy] + [current] * 17
        result = sfx.PhaseHistoryResult(20, 2, True, records)
        with mock.patch.object(sfx, "_phase_history_present", return_value=True), \
                mock.patch.object(sfx, "_load_phase_history_result", return_value=result), \
                mock.patch.object(sfx, "_current_phase_org_hash", return_value="a" * 64):
            inspected = sfx._journey_inspection()
        self.assertEqual(inspected["status"], "partially-valid")
        self.assertEqual(inspected["counts"], {"accepted": 20, "rejected": 2, "truncated": True})
        deploy = next(g for g in inspected["stages"] if g["stage"] == "Deploy")
        self.assertEqual(len(deploy["evidence"]), sfx._JOURNEY_EVIDENCE_CAP)
        self.assertEqual(set(deploy["evidence"][0]),
                         {"stage", "type", "outcome", "source", "ts", "scope"})
        scopes = [item["scope"] for item in deploy["evidence"]]
        self.assertIn("current-org", scopes)
        # The per-stage cap keeps the newest records, so the early other/legacy
        # fixtures are checked separately below rather than assumed present here.
        self.assertEqual(sfx._public_phase_evidence(other, "a" * 64)["scope"], "other-org")
        self.assertEqual(sfx._public_phase_evidence(legacy, "a" * 64)["scope"], "unattributed")
        self.assertEqual(sfx._public_phase_evidence(current, None)["scope"], "unattributed")
        self.assertNotIn("orgHash", json.dumps(inspected))
        self.assertNotIn("/", json.dumps(inspected["stages"]))

    def test_human_is_cell_bounded_and_json_mentions_separate_live_derivation(self):
        record = {"type": "deploy", "stage": "Deploy", "outcome": "passed",
                  "source": "s" * 64, "ts": "2026-08-02T10:00:00+00:00"}
        result = sfx.PhaseHistoryResult(1, 0, False, [record])
        with mock.patch.object(sfx, "_phase_history_present", return_value=True), \
                mock.patch.object(sfx, "_load_phase_history_result", return_value=result):
            code, human, _ = self.capture(["inspect"])
            code_json, raw, _ = self.capture(["inspect", "--json"])
        self.assertEqual((code, code_json), (0, 0))
        self.assertTrue(all(sfx._terminal_cell_width(line) <= 80 for line in human.splitlines()))
        payload = json.loads(raw)
        self.assertIn("Live target, project, source, and test facts", payload["derivationNote"])

    def test_where_alias_and_invalid_arguments(self):
        with mock.patch.object(sfx, "cmd_journey", return_value=0) as journey:
            self.assertEqual(sfx.cmd_discovery(["where", "inspect", "--json"]), 0)
        journey.assert_called_once_with(["inspect", "--json"])
        code, _, err = self.capture(["inspect", "--bogus"])
        self.assertEqual(code, 2)
        self.assertIn("Usage:", err)


if __name__ == "__main__":
    unittest.main()
