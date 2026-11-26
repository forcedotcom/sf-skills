"""Regression tests for scripts/observe_workers.py — the four gate holes.

The gate's whole job is to be un-foolable: it must stay CLOSED until every
planned unit is terminal WITH EVIDENCE. The four holes each let a non-migrated
project slip into Phase 5:

  1. Stall detection was a no-op without --now, so a silent worker looked
     "running" forever and the gate never noticed. `now` now defaults to the
     ledger's max ts.
  2. A bare "done" (no filesTouched/flagged) was trusted — exactly how a silent
     failure masquerades as success. "done" now requires evidence.
  3. A bare "blocked" (no flagged reason) opened the gate for an all-gave-up run.
     "blocked" now requires a flagged list, and blockedCount is surfaced.
  4. A demoted (restart-exhausted) unit had no terminal event, so it jammed the
     gate closed forever. "demoted" is now a terminal event/status.

These drive the real summarize()/build_todo() so they can't drift from the code.
"""
import unittest

import _bootstrap  # noqa: F401
import observe_workers as ow


def _summarize(units, events, now=None, stall_threshold=30, max_restarts=2):
    return ow.summarize(units, events, now, stall_threshold, max_restarts)


def _status(state, unit):
    return state[unit]["status"]


class TestStallWithoutExplicitNow(unittest.TestCase):
    """Hole 1: staleness must be detectable on a plain re-run (now defaults to
    the ledger's highest ts)."""

    def test_now_defaults_to_ledger_max(self):
        events = [
            {"unit": "u1", "event": "done", "ts": 100, "filesTouched": ["A.kt"]},
            {"unit": "u2", "event": "start", "ts": 5},   # 95 ticks behind → stalled
        ]
        now = max(ev["ts"] for ev in events)  # what main() computes as the default
        state, _, _ = _summarize(["u1", "u2"], events, now=now, stall_threshold=30)
        self.assertEqual(_status(state, "u2"), "stalled")

    def test_within_threshold_is_running_not_stalled(self):
        events = [
            {"unit": "u1", "event": "heartbeat", "ts": 100},
            {"unit": "u2", "event": "heartbeat", "ts": 90},  # only 10 behind
        ]
        now = 100
        state, _, _ = _summarize(["u1", "u2"], events, now=now, stall_threshold=30)
        self.assertEqual(_status(state, "u2"), "running")

    def test_no_now_and_no_events_cannot_false_open(self):
        # Empty ledger, planned units → everything MISSING, gate must be closed.
        state, _, _ = _summarize(["u1"], [], now=None)
        self.assertEqual(_status(state, "u1"), "missing")


class TestDoneNeedsEvidence(unittest.TestCase):
    """Hole 2: a 'done' with no diff is not trusted."""

    def test_bare_done_is_unverified(self):
        events = [{"unit": "u1", "event": "done", "ts": 10}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "done-unverified")
        self.assertNotIn("done-unverified", ow.TERMINAL_STATUSES)

    def test_done_with_files_is_terminal(self):
        events = [{"unit": "u1", "event": "done", "ts": 10, "filesTouched": ["App.kt"]}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "done")

    def test_evidence_may_arrive_on_an_earlier_heartbeat(self):
        # The worker reported files on a heartbeat, then a bare done. Accumulated
        # evidence still counts — the done need not repeat the file list.
        events = [
            {"unit": "u1", "event": "heartbeat", "ts": 5, "filesTouched": ["App.kt"]},
            {"unit": "u1", "event": "done", "ts": 10},
        ]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "done")

    def test_done_with_only_flagged_is_terminal(self):
        # A "reviewed, no change needed" disposition is valid evidence.
        events = [{"unit": "u1", "event": "done", "ts": 10,
                   "flagged": [{"file": "X.kt", "line": 1, "why": "no change needed"}]}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "done")

    def test_unverified_done_is_re_dispatched(self):
        events = [{"unit": "u1", "event": "done", "ts": 10}]
        state, _, _ = _summarize(["u1"], events)
        todo = ow.build_todo(state, max_restarts=2)
        self.assertIn("u1", todo["verify"])

    def test_unverified_done_with_exhausted_restarts_is_demoted(self):
        events = [{"unit": "u1", "event": "done", "ts": 10, "restart": 2}]
        state, _, _ = _summarize(["u1"], events, max_restarts=2)
        todo = ow.build_todo(state, max_restarts=2)
        self.assertIn("u1", todo["demote"])
        self.assertNotIn("u1", todo["verify"])


class TestBlockedNeedsReason(unittest.TestCase):
    """Hole 3: a 'blocked' with no flagged items is an empty claim."""

    def test_bare_blocked_is_unverified(self):
        events = [{"unit": "u1", "event": "blocked", "ts": 10}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "blocked-unverified")

    def test_blocked_with_flagged_is_terminal(self):
        events = [{"unit": "u1", "event": "blocked", "ts": 10,
                   "flagged": [{"file": "X.kt", "line": 3, "why": "manual"}]}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "blocked")
        self.assertIn("blocked", ow.TERMINAL_STATUSES)


class TestDemotedIsTerminal(unittest.TestCase):
    """Hole 4: an exhausted unit needs a terminal disposition or it jams the gate."""

    def test_demoted_is_terminal_status(self):
        events = [{"unit": "u1", "event": "demoted", "ts": 11, "detail": "budget exhausted"}]
        state, _, _ = _summarize(["u1"], events)
        self.assertEqual(_status(state, "u1"), "demoted")
        self.assertIn("demoted", ow.TERMINAL_STATUSES)
        self.assertIn("demoted", ow.TERMINAL)

    def test_demoted_does_not_count_as_heartbeat(self):
        # A demoted event must not reset staleness for some other reasoning path.
        events = [{"unit": "u1", "event": "start", "ts": 1},
                  {"unit": "u1", "event": "demoted", "ts": 50}]
        state, _, _ = _summarize(["u1"], events, now=50, stall_threshold=30)
        # It's terminal regardless, but the last heartbeat should still be the start.
        self.assertEqual(_status(state, "u1"), "demoted")
        self.assertEqual(state["u1"]["lastHeartbeatTs"], 1)


class TestGateEndToEnd(unittest.TestCase):
    """The four fixes combined: only verified-terminal units open the gate."""

    def _gate(self, units, events, now=None):
        # Mirror main()'s now-default + gate computation.
        ledger_max = max((ev["ts"] for ev in events if isinstance(ev.get("ts"), int)),
                         default=None)
        resolved_now = now if now is not None else ledger_max
        state, _, _ = _summarize(units, events, resolved_now)
        have_plan = bool(units)
        return have_plan and all(s["status"] in ow.TERMINAL_STATUSES for s in state.values())

    def test_all_verified_terminal_opens(self):
        events = [
            {"unit": "u1", "event": "done", "ts": 10, "filesTouched": ["A.kt"]},
            {"unit": "u2", "event": "blocked", "ts": 11, "flagged": [{"why": "manual"}]},
            {"unit": "u3", "event": "demoted", "ts": 12},
        ]
        self.assertTrue(self._gate(["u1", "u2", "u3"], events))

    def test_one_unverified_keeps_closed(self):
        events = [
            {"unit": "u1", "event": "done", "ts": 10, "filesTouched": ["A.kt"]},
            {"unit": "u2", "event": "done", "ts": 11},  # no evidence
        ]
        self.assertFalse(self._gate(["u1", "u2"], events))

    def test_stalled_unit_keeps_closed_without_explicit_now(self):
        events = [
            {"unit": "u1", "event": "done", "ts": 100, "filesTouched": ["A.kt"]},
            {"unit": "u2", "event": "start", "ts": 1},
        ]
        self.assertFalse(self._gate(["u1", "u2"], events))

    def test_no_plan_never_opens(self):
        events = [{"unit": "u1", "event": "done", "ts": 10, "filesTouched": ["A.kt"]}]
        self.assertFalse(self._gate([], events))


if __name__ == "__main__":
    unittest.main()
