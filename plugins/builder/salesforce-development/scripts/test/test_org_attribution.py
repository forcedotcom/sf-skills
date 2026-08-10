#!/usr/bin/env python3
"""Behavior proofs for private org attribution and same-org soft Observe."""
from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
sfx = load_module(SCRIPTS / "sf_context.py", "sf_context_org_attribution")

ORG_A_15 = "00D000000000001"
ORG_B_15 = "00D000000000002"


class OrgAttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        (self.root / "sfdx-project.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    @staticmethod
    def payload(command):
        return {"tool_input": {"command": command}}

    def capture(self, handler, command):
        out = io.StringIO()
        with redirect_stdout(out):
            code = handler(self.payload(command))
        return code, out.getvalue()

    def records(self):
        return sfx._load_phase_history_result().records

    def test_effective_target_explicit_never_falls_back_and_last_flag_wins(self):
        default = mock.Mock(return_value="default-b")
        cases = (
            (["sf", "project", "deploy", "start", "--target-org", "explicit-a"], "explicit-a"),
            (["sf", "project", "deploy", "start", "--target-org=first", "-o", "last"], "last"),
            (["sf", "data", "query", "-o", "first", "--target-org=last"], "last"),
            (["sf", "apex", "run", "test", "--synchronous"], "default-b"),
        )
        for argv, expected in cases:
            with self.subTest(argv=argv), mock.patch.object(
                    sfx, "_configured_target_alias", default):
                self.assertEqual(sfx._effective_phase_target(argv), expected)
        self.assertEqual(default.call_count, 1)
        with mock.patch.object(sfx, "_configured_target_alias", return_value="default-b") as configured:
            self.assertIsNone(sfx._effective_phase_target(
                ["sf", "project", "deploy", "start", "--target-org"]))
            self.assertIsNone(sfx._effective_phase_target(
                ["sf", "project", "deploy", "start", "-o", "--json"]))
        configured.assert_not_called()

    def test_salesforce_15_and_18_ids_normalize_identically(self):
        canonical = sfx._normalize_salesforce_org_id(ORG_A_15)
        self.assertEqual(len(canonical), 18)
        self.assertEqual(sfx._normalize_salesforce_org_id(canonical), canonical)
        self.assertIsNone(sfx._normalize_salesforce_org_id("001000000000001"))
        self.assertIsNone(sfx._normalize_salesforce_org_id(canonical[:-1] + "Z"))

    def test_alias_rename_two_aliases_and_repoint_follow_canonical_id(self):
        displays = {
            "old-name": {"id": ORG_A_15, "alias": "old-name"},
            "new-name": {"id": sfx._normalize_salesforce_org_id(ORG_A_15), "alias": "new-name"},
            "repointed": {"id": ORG_B_15, "alias": "old-name"},
        }
        with mock.patch.object(sfx, "get_org_display", side_effect=lambda target: displays[target]):
            first = sfx._resolve_phase_org_id(["sf", "data", "query", "-o", "old-name"])
            renamed = sfx._resolve_phase_org_id(["sf", "data", "query", "-o", "new-name"])
            repointed = sfx._resolve_phase_org_id(["sf", "data", "query", "-o", "repointed"])
        self.assertEqual(first, renamed)
        self.assertNotEqual(first, repointed)

    def test_matching_command_resolves_once_and_failure_stays_unattributed(self):
        secrets = {"alias": "private-alias", "username": "private@example.com",
                   "instanceUrl": "https://private.example", "accessToken": "private-token"}
        with mock.patch.object(
                sfx, "get_org_display", return_value={"id": ORG_A_15, **secrets}) as display:
            _, output = self.capture(
                sfx.cmd_post_deploy,
                "sf project deploy start --target-org explicit-a --source-dir force-app")
        display.assert_called_once_with("explicit-a")
        self.assertIn("orgHash", self.records()[0])
        persisted_and_emitted = (self.root / ".sf/phase-history.jsonl").read_text() + output
        for secret in (ORG_A_15, *secrets.values()):
            self.assertNotIn(secret, persisted_and_emitted)

        history = self.root / ".sf" / "phase-history.jsonl"
        history.unlink()
        with mock.patch.object(sfx, "get_org_display", return_value={}) as display:
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o missing")
        display.assert_called_once_with("missing")
        self.assertNotIn("orgHash", self.records()[0])

    def test_proven_deploy_test_and_standalone_test_events_are_attributed(self):
        with mock.patch.object(sfx, "get_org_display", return_value={"id": ORG_A_15}):
            self.capture(
                sfx.cmd_post_deploy,
                "sf project deploy start -o a --test-level RunLocalTests")
            self.capture(
                sfx.cmd_post_test_run,
                "sf apex run test --synchronous --target-org=a")
        records = self.records()
        self.assertEqual([record["stage"] for record in records], ["Deploy", "Test", "Test"])
        self.assertEqual(len({record.get("orgHash") for record in records}), 1)
        self.assertTrue(all("orgHash" in record for record in records))

    def test_chained_ambiguous_and_unrelated_commands_never_resolve(self):
        commands = (
            "sf project deploy start -o a && sf org display -o b",
            "sf data query -q 'select Id from Account' | cat",
            "sf project deploy start --target-org",
            "git status --short",
        )
        with mock.patch.object(sfx, "get_org_display") as display:
            for command in commands:
                self.capture(sfx.cmd_post_deploy, command)
        display.assert_not_called()

    def test_same_org_soft_observe_records_and_cross_org_does_not(self):
        displays = {"a": {"id": ORG_A_15}, "also-a": {"id": sfx._normalize_salesforce_org_id(ORG_A_15)},
                    "b": {"id": ORG_B_15}}
        with mock.patch.object(sfx, "get_org_display", side_effect=lambda target: displays[target]):
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o a")
            self.capture(sfx.cmd_post_observe, "sf org open -o b")
            self.capture(sfx.cmd_post_observe, "sf data query -o also-a -q 'select Id from Account'")
        observes = [record for record in self.records() if record["stage"] == "Observe"]
        self.assertEqual(len(observes), 1)
        self.assertIn("orgHash", observes[0])

    def test_strong_observe_may_remain_unattributed(self):
        with mock.patch.object(sfx, "get_org_display", return_value={}) as display:
            self.capture(sfx.cmd_post_observe, "sf apex tail log -o unknown")
        display.assert_called_once_with("unknown")
        observe = self.records()[0]
        self.assertEqual(observe["stage"], "Observe")
        self.assertNotIn("orgHash", observe)

    def test_journey_scope_uses_already_resolved_identity_without_cli_or_hash_output(self):
        with mock.patch.object(sfx, "get_org_display", return_value={"id": ORG_A_15}):
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o a")
        digest = self.records()[0]["orgHash"]
        legacy = {"type": "deploy", "stage": "Deploy", "outcome": "passed"}
        other = dict(self.records()[0], orgHash="f" * 64)
        with mock.patch.object(sfx, "_load_phase_history_result", return_value=sfx.PhaseHistoryResult(
                3, 0, False, [self.records()[0], other, legacy])), \
                mock.patch.object(sfx, "run_result", side_effect=AssertionError("passive CLI call")):
            state = sfx._derive_journey_state(
                self.root, has_project=True, target="alias", target_error=None,
                org_display={"id": ORG_A_15, "alias": "renamed"})
        evidence = next(stage for stage in state["stages"] if stage["name"] == "Deploy")["evidence"]
        self.assertEqual([item["scope"] for item in evidence],
                         ["current-org", "other-org", "unattributed"])
        rendered = json.dumps(state)
        self.assertNotIn(digest, rendered)
        self.assertNotIn("orgHash", rendered)
        self.assertNotIn(ORG_A_15, rendered)

    def test_passive_unknown_identity_leaves_all_scope_unattributed(self):
        record = {"type": "deploy", "stage": "Deploy", "outcome": "passed", "orgHash": "a" * 64}
        with mock.patch.object(sfx, "_load_phase_history_result", return_value=sfx.PhaseHistoryResult(
                1, 0, False, [record])), mock.patch.object(
                sfx, "get_org_display", side_effect=AssertionError("must not resolve")):
            state = sfx._derive_journey_state(
                self.root, has_project=True, target="configured", target_error="unprobed",
                org_display=None)
        deploy = next(stage for stage in state["stages"] if stage["name"] == "Deploy")
        self.assertEqual(deploy["evidence"][0]["scope"], "unattributed")

    @unittest.skipUnless(
        hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "POSIX FIFOs unavailable"
    )
    def test_existing_key_fifo_returns_promptly_without_reading(self):
        sf_dir = self.root / ".sf"
        sf_dir.mkdir()
        fifo = sf_dir / "phase-org.key"
        os.mkfifo(fifo)
        directory = sfx._open_phase_directory(False)
        self.assertIsNotNone(directory)
        results = []
        errors = []

        def read_key():
            try:
                results.append(sfx._phase_key_bytes(directory, create=False))
            except BaseException as exc:  # Surface worker failures in the main test thread.
                errors.append(exc)

        worker = threading.Thread(target=read_key, daemon=True)
        worker.start()
        worker.join(0.5)
        blocked = worker.is_alive()
        if blocked:
            # Unblock the pre-fix FIFO reader so a red test does not leak a live worker.
            writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
            os.close(writer)
            worker.join(0.5)
        sfx._close_phase_directory(directory)

        self.assertFalse(blocked, "phase key read blocked on a FIFO")
        self.assertEqual(errors, [])
        self.assertEqual(results, [None])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_key_symlink_is_rejected_without_touching_target(self):
        sf_dir = self.root / ".sf"
        sf_dir.mkdir()
        victim = self.root / "victim"
        victim.write_bytes(b"v" * 32)
        os.symlink(victim, sf_dir / "phase-org.key")
        with mock.patch.object(sfx, "get_org_display", return_value={"id": ORG_A_15}):
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o a")
        self.assertEqual(victim.read_bytes(), b"v" * 32)
        self.assertNotIn("orgHash", self.records()[0])

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_key_hardlink_is_rejected_and_new_key_is_private(self):
        sf_dir = self.root / ".sf"
        sf_dir.mkdir()
        victim = self.root / "victim"
        victim.write_bytes(b"v" * 32)
        os.link(victim, sf_dir / "phase-org.key")
        with mock.patch.object(sfx, "get_org_display", return_value={"id": ORG_A_15}):
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o a")
        self.assertNotIn("orgHash", self.records()[0])

        (sf_dir / "phase-org.key").unlink()
        with mock.patch.object(sfx, "get_org_display", return_value={"id": ORG_A_15}):
            self.capture(sfx.cmd_post_deploy, "sf project deploy start -o a")
        key = sf_dir / "phase-org.key"
        self.assertEqual(len(key.read_bytes()), 32)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
