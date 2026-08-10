#!/usr/bin/env python3
"""Behavior proofs for nonce-confirmed, scoped, atomic journey reset."""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
sfx = load_module(SCRIPTS / "sf_context.py", "sf_context_journey_reset")


class JourneyResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_cwd = Path.cwd()
        os.chdir(self.root)
        (self.root / "sfdx-project.json").write_text(
            '{"name":"Reset Project\\nunsafe/path"}', encoding="utf-8"
        )

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    @property
    def history(self):
        return self.root / ".sf" / "phase-history.jsonl"

    def record(self, stage, *, org=None, outcome="passed"):
        kinds = {"Test": "test-run", "Deploy": "deploy", "Observe": "observe"}
        value = {
            "schemaVersion": 1,
            "type": kinds[stage],
            "stage": stage,
            "outcome": outcome,
            "source": "fixture",
            "ts": "2026-08-02T10:00:00+00:00",
        }
        if org:
            value["orgHash"] = org
        return value

    def write(self, records, rejected=b""):
        self.history.parent.mkdir(parents=True, exist_ok=True)
        body = b"".join(
            (json.dumps(record, separators=(",", ":")) + "\n").encode()
            for record in records
        )
        self.history.write_bytes(body + rejected)
        return body + rejected

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sfx.cmd_journey(["reset", *args])
        payload = json.loads(out.getvalue()) if out.getvalue().startswith("{") else None
        return code, payload, out.getvalue(), err.getvalue()

    def dry(self, *args):
        code, payload, _, err = self.invoke([*args, "--json"])
        self.assertEqual((code, err), (0, ""))
        return payload

    def tree_snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (
                path.lstat().st_mode, path.read_bytes() if path.is_file() else None
            )
            for path in sorted(self.root.rglob("*"))
        }

    def test_dry_run_is_full_tree_read_only_exact_and_redacted(self):
        original = self.write([self.record("Test"), self.record("Deploy")])
        before = self.tree_snapshot()
        payload = self.dry("--stage", "Deploy", "--scope", "all")
        self.assertEqual(self.tree_snapshot(), before)
        self.assertFalse((self.history.parent / "phase-history.lock").exists())
        self.assertEqual(self.history.read_bytes(), original)
        self.assertEqual(payload["project"], "Reset Project unsafe path")
        self.assertEqual(payload["filters"], {"stage": "Deploy", "scope": "all"})
        self.assertEqual(payload["selectedAcceptedRecords"], 1)
        self.assertEqual(payload["history"], {"status": "available", "accepted": 2,
                                               "rejected": 0, "truncated": False})
        self.assertTrue(payload["dryRun"])
        self.assertRegex(payload["nonce"], r"^[a-f0-9]{64}$")
        rendered = json.dumps(payload)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn("orgHash", rendered)
        self.assertIn("relight", payload["liveFactsNote"])

    def test_confirm_creates_byte_exact_backup_and_atomically_retains_records(self):
        keep = self.record("Test")
        remove = self.record("Deploy")
        original = self.write([keep, remove])
        nonce = self.dry("--stage", "Deploy")["nonce"]
        code, result, _, err = self.invoke(["--stage", "Deploy", "--confirm", nonce, "--json"])
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(result["reset"])
        self.assertEqual(result["selectedAcceptedRecords"], 1)
        self.assertEqual(result["rejectedRecordsRemoved"], 0)
        self.assertEqual(sfx._load_phase_history_result().records, [keep])
        backups = list(self.history.parent.glob("phase-history.backup-*.jsonl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertNotIn(backups[0].name, json.dumps(result))

    def test_reset_after_retention_binds_and_backs_up_retained_preimage(self):
        self.write([
            self.record("Test"),
            self.record("Deploy", outcome="failed"),
        ])
        with mock.patch.object(sfx, "_PHASE_HISTORY_MAX_RECORDS", 2):
            self.assertTrue(sfx._record_phase_event(
                "Deploy", "passed", source="retained", event_type="deploy"))
        retained_preimage = self.history.read_bytes()
        retained_records = sfx._load_phase_history_result().records
        self.assertEqual([(record["stage"], record["outcome"]) for record in retained_records],
                         [("Test", "passed"), ("Deploy", "passed")])

        nonce = self.dry("--stage", "Deploy")["nonce"]
        code, result, _, err = self.invoke(
            ["--stage", "Deploy", "--confirm", nonce, "--json"])

        self.assertEqual((code, err), (0, ""))
        self.assertTrue(result["reset"])
        self.assertEqual(sfx._load_phase_history_result().records, [retained_records[0]])
        backups = list(self.history.parent.glob("phase-history.backup-*.jsonl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), retained_preimage)

    def test_current_scope_dry_run_does_not_chmod_key_or_create_lock(self):
        self.write([self.record("Deploy", org="a" * 64)])
        key = self.history.parent / "phase-org.key"
        key.write_bytes(b"k" * 32)
        if os.name != "nt":
            key.chmod(0o600)
        before = self.tree_snapshot()
        with mock.patch.object(sfx, "get_target_org_detailed", return_value=("alias", None)), \
                mock.patch.object(sfx, "get_org_display", return_value={"id": "00D000000000001"}):
            payload = self.dry("--scope", "current-org")
        self.assertFalse(payload["blocked"])
        self.assertEqual(self.tree_snapshot(), before)
        self.assertFalse((self.history.parent / "phase-history.lock").exists())

    def test_rejected_history_blocks_dry_run_and_confirm_without_rewriting_selective_data(self):
        keep = self.record("Test")
        remove = self.record("Deploy")
        original = self.write([keep, remove], rejected=b"invalid\n")
        payload = self.dry("--stage", "Deploy")
        self.assertEqual(payload["selectedAcceptedRecords"], 0)
        self.assertIsNone(payload["nonce"])
        self.assertTrue(payload["blocked"])
        self.assertIn("rejected", payload["blockedReason"])
        self.assertEqual(self.history.read_bytes(), original)
        code, _, _, err = self.invoke(
            ["--stage", "Deploy", "--confirm", "0" * 64, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("blocked", err.lower())
        self.assertEqual(self.history.read_bytes(), original)
        self.assertEqual(list(self.history.parent.glob("phase-history.backup-*.jsonl")), [])

    def test_truncated_history_blocks_and_preserves_every_byte(self):
        encoded = (json.dumps(self.record("Deploy"), separators=(",", ":")) + "\n").encode()
        repeats = sfx._PHASE_HISTORY_MAX_FILE_BYTES // len(encoded) + 2
        original = self.write([])
        original = encoded * repeats
        self.history.write_bytes(original)
        directory = sfx._open_phase_directory(False)
        try:
            preimage, _ = sfx._read_phase_preimage(directory)
        finally:
            sfx._close_phase_directory(directory)
        self.assertEqual(len(preimage), sfx._PHASE_HISTORY_MAX_FILE_BYTES + 1)
        payload = self.dry("--stage", "Deploy")
        self.assertTrue(payload["history"]["truncated"])
        self.assertTrue(payload["blocked"])
        self.assertEqual(payload["selectedAcceptedRecords"], 0)
        self.assertIsNone(payload["nonce"])
        code, _, _, _ = self.invoke(
            ["--stage", "Deploy", "--confirm", "0" * 64, "--json"])
        self.assertEqual(code, 3)
        self.assertEqual(self.history.read_bytes(), original)

    def test_nonce_conflict_repeat_and_no_history_noop(self):
        self.write([self.record("Deploy")])
        nonce = self.dry()["nonce"]
        with self.history.open("ab") as stream:
            stream.write((json.dumps(self.record("Test")) + "\n").encode())
        before = self.history.read_bytes()
        code, payload, _, err = self.invoke(["--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIsNone(payload)
        self.assertIn("changed", err.lower())
        self.assertEqual(self.history.read_bytes(), before)

        fresh = self.dry()["nonce"]
        self.assertEqual(self.invoke(["--confirm", fresh, "--json"])[0], 0)
        self.assertNotEqual(self.invoke(["--confirm", fresh, "--json"])[0], 0)

        self.history.unlink()
        no_history = self.dry()
        self.assertTrue(no_history["noHistory"])
        self.assertIsNone(no_history["nonce"])
        code, result, _, _ = self.invoke(["--confirm", "0" * 64, "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(result["dryRun"])
        self.assertFalse(result["reset"])

    def test_all_scope_and_stage_filters(self):
        current, other = "a" * 64, "b" * 64
        records = [self.record("Test", org=current), self.record("Deploy", org=other),
                   self.record("Observe")]
        self.write(records)
        self.assertEqual(self.dry()["selectedAcceptedRecords"], 3)
        self.assertEqual(self.dry("--stage", "Test")["selectedAcceptedRecords"], 1)
        self.assertEqual(self.dry("--stage", "Connect")["selectedAcceptedRecords"], 0)
        front = self.dry("--stage", "Project")
        self.assertIn("re-derive", front["stageNote"])
        self.assertEqual(self.dry("--scope", "unattributed")["selectedAcceptedRecords"], 1)
        with mock.patch.object(sfx, "_current_phase_org_hash", return_value=current):
            self.assertEqual(self.dry("--scope", "current-org")["selectedAcceptedRecords"], 1)
            self.assertEqual(self.dry("--scope", "other-org")["selectedAcceptedRecords"], 1)

    def test_current_scopes_refuse_without_identity_and_bind_resolved_identity(self):
        self.write([self.record("Deploy", org="a" * 64)])
        with mock.patch.object(sfx, "_current_phase_org_hash", return_value=None):
            code, _, _, err = self.invoke(["--scope", "current-org", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("identity", err.lower())
        with mock.patch.object(sfx, "_current_phase_org_hash", return_value="a" * 64):
            nonce = self.dry("--scope", "current-org")["nonce"]
        before = self.history.read_bytes()
        with mock.patch.object(sfx, "_current_phase_org_hash", return_value="b" * 64):
            code, _, _, err = self.invoke(
                ["--scope", "current-org", "--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("changed", err.lower())
        self.assertEqual(self.history.read_bytes(), before)
        code, _, _, err = self.invoke(["--scope", "bogus", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("scope", err.lower())

    def test_backup_directory_sync_failure_keeps_original_and_durable_backup(self):
        original = self.write([self.record("Deploy")])
        nonce = self.dry()["nonce"]
        with mock.patch.object(sfx, "_sync_phase_directory", return_value=False):
            code, _, _, err = self.invoke(["--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("backup", err.lower())
        self.assertEqual(self.history.read_bytes(), original)
        backups = list(self.history.parent.glob("phase-history.backup-*.jsonl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_post_replace_sync_failure_reports_failure_and_restores_original(self):
        original = self.write([self.record("Deploy")])
        nonce = self.dry()["nonce"]
        with mock.patch.object(sfx, "_sync_phase_file", side_effect=[False, True]), \
                mock.patch.object(sfx, "_sync_phase_directory", return_value=True):
            code, _, _, err = self.invoke(["--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("confirmed rollback", err.lower())
        self.assertEqual(self.history.read_bytes(), original)
        backups = list(self.history.parent.glob("phase-history.backup-*.jsonl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def windows_directory(self):
        root_info = self.root.lstat()
        parent_info = self.history.parent.lstat()
        return sfx.PhaseDirectory(
            fd=None, path=self.history.parent, relative=False, root_path=self.root,
            root_identity=sfx._phase_identity(root_info),
            parent_identity=sfx._phase_identity(parent_info),
        )

    def test_windows_directory_sync_uses_backup_semantics_and_safe_sharing(self):
        self.write([self.record("Deploy")])
        directory = self.windows_directory()
        api = mock.Mock()
        api.CreateFileW.return_value = 123
        api.FlushFileBuffers.return_value = True
        api.CloseHandle.return_value = True
        with mock.patch.object(sfx, "_phase_windows", return_value=True), \
                mock.patch.object(sfx, "_windows_kernel32", return_value=api):
            self.assertTrue(sfx._sync_phase_directory(directory))
        args = api.CreateFileW.call_args.args
        self.assertEqual(args[0], str(self.history.parent))
        self.assertEqual(args[2], 0x1 | 0x2 | 0x4)
        self.assertTrue(args[5] & 0x02000000)
        api.FlushFileBuffers.assert_called_once_with(123)
        api.CloseHandle.assert_called_once_with(123)

    def test_windows_backup_flush_failure_blocks_active_replacement(self):
        original = self.write([self.record("Deploy")])
        nonce = self.dry()["nonce"]
        directory = self.windows_directory()
        api = mock.Mock()
        api.CreateFileW.return_value = 123
        api.FlushFileBuffers.return_value = False
        api.CloseHandle.return_value = True
        with mock.patch.object(sfx, "_phase_windows", return_value=True), \
                mock.patch.object(sfx, "_open_phase_directory", return_value=directory), \
                mock.patch.object(sfx, "_acquire_phase_history_lock", return_value=99), \
                mock.patch.object(sfx, "_release_phase_history_lock"), \
                mock.patch.object(sfx, "_windows_kernel32", return_value=api), \
                mock.patch.object(sfx, "_replace_phase_history") as replace:
            code, _, _, err = self.invoke(["--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("backup", err.lower())
        replace.assert_not_called()
        self.assertEqual(self.history.read_bytes(), original)
        backups = list(self.history.parent.glob("phase-history.backup-*.jsonl"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_rollback_replace_failure_is_uncertain(self):
        original = self.write([self.record("Deploy")])
        directory = sfx._open_phase_directory(False)
        observed, identity = sfx._read_phase_preimage(directory)
        real_replace = sfx._replace_phase_entry
        calls = 0

        def fail_rollback(*args):
            nonlocal calls
            calls += 1
            return real_replace(*args) if calls == 1 else False

        with mock.patch.object(sfx, "_replace_phase_entry", side_effect=fail_rollback), \
                mock.patch.object(sfx, "_sync_phase_file", return_value=False):
            outcome = sfx._replace_phase_history(directory, observed, identity, b"")
        sfx._close_phase_directory(directory)
        self.assertEqual(outcome.status, sfx._PHASE_REPLACE_UNCERTAIN)
        self.assertNotEqual(self.history.read_bytes(), original)

    def test_rollback_sync_failure_is_uncertain_and_caller_requires_recovery(self):
        original = self.write([self.record("Deploy")])
        directory = sfx._open_phase_directory(False)
        observed, identity = sfx._read_phase_preimage(directory)
        with mock.patch.object(sfx, "_sync_phase_file", side_effect=[False, False]), \
                mock.patch.object(sfx, "_sync_phase_directory", return_value=True):
            outcome = sfx._replace_phase_history(directory, observed, identity, b"")
        sfx._close_phase_directory(directory)
        self.assertEqual(outcome.status, sfx._PHASE_REPLACE_UNCERTAIN)
        self.assertEqual(self.history.read_bytes(), original)

        nonce = self.dry()["nonce"]
        uncertain = sfx.PhaseReplaceOutcome(sfx._PHASE_REPLACE_UNCERTAIN)
        with mock.patch.object(sfx, "_replace_phase_history", return_value=uncertain):
            code, _, _, err = self.invoke(["--confirm", nonce, "--json"])
        self.assertEqual(code, 3)
        self.assertIn("uncertain", err.lower())
        self.assertIn("durable backup", err.lower())
        self.assertIn("manual", err.lower())
        self.assertNotIn("unchanged", err.lower())

    def test_backup_failure_and_cooperating_append_never_lose_original(self):
        self.write([self.record("Deploy")])
        nonce = self.dry()["nonce"]
        before = self.history.read_bytes()
        with mock.patch.object(sfx, "_create_phase_backup", return_value=False):
            code, _, _, _ = self.invoke(["--confirm", nonce, "--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(self.history.read_bytes(), before)

        # If an append wins the phase lock first it is included in the next dry-run;
        # if reset wins first the stale nonce conflicts. Either outcome loses no append.
        nonce = self.dry()["nonce"]
        started = threading.Event()
        original_acquire = sfx._acquire_phase_history_lock

        def delayed(directory):
            started.set()
            return original_acquire(directory)

        result = []
        with mock.patch.object(sfx, "_acquire_phase_history_lock", side_effect=delayed):
            worker = threading.Thread(target=lambda: result.append(
                sfx._record_phase_event("Test", "passed", source="fixture", event_type="test-run")
            ))
            worker.start()
            started.wait(1)
            code, _, _, _ = self.invoke(["--confirm", nonce, "--json"])
            worker.join(2)
        parsed = sfx._load_phase_history_result().records
        self.assertTrue(result and result[0])
        self.assertTrue(code == 3 or any(r["stage"] == "Test" for r in parsed))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_history_symlink_attack_is_rejected(self):
        self.history.parent.mkdir()
        victim = self.root / "victim"
        victim.write_bytes(b"secret")
        os.symlink(victim, self.history)
        code, _, _, _ = self.invoke(["--json"])
        self.assertNotEqual(code, 0)
        self.assertEqual(victim.read_bytes(), b"secret")

    @unittest.skipUnless(hasattr(os, "link") and hasattr(os, "mkfifo"),
                         "hardlinks/FIFOs unavailable")
    def test_history_hardlink_and_special_file_attacks_are_rejected(self):
        self.history.parent.mkdir()
        victim = self.root / "victim"
        victim.write_bytes(b"secret")
        os.link(victim, self.history)
        self.assertNotEqual(self.invoke(["--json"])[0], 0)
        self.assertEqual(victim.read_bytes(), b"secret")
        self.history.unlink()
        os.mkfifo(self.history)
        # O_NONBLOCK is applied by the safe reader boundary before any read, so a
        # hostile FIFO never hangs the command and is rejected as non-regular.
        with mock.patch.object(sfx, "_open_phase_child", wraps=sfx._open_phase_child):
            self.assertNotEqual(self.invoke(["--json"])[0], 0)

    def test_human_output_is_bounded(self):
        self.write([self.record("Deploy")])
        code, _, output, err = self.invoke([])
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(all(sfx._terminal_cell_width(line) <= 80 for line in output.splitlines()))
        self.assertNotIn(str(self.root), output)


if __name__ == "__main__":
    unittest.main()
