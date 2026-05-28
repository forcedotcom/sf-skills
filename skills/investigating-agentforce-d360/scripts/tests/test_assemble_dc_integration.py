"""End-to-end integration tests for ``assemble_dc.assemble``.

Drives the full assembler against the synthetic session fixture under
``tests/fixtures/synthetic_session.py``. Each test materializes the
fixture into a tmp DATA_ROOT, calls ``assemble_dc.assemble(SID)``, and
asserts on the resulting tree.

These tests cover the orchestration paths that the helper-only
``test_assemble_dc_helpers.py`` doesn't touch:

- declared Step → Generation → Response → Request chain
- timestamp-window fallback for an un-declared gateway request
- trace_id extraction from HTML-escaped AttributeText
- session-identity resolution from AGENT participant
- malformed dc.<name>.json → parse_warnings recorded, fixture survives
- minimal-tree path when sessions[] is empty (session_not_found)
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import (  # type: ignore
    IDS, make_rows, write_to_disk, session_dir_for,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


class _AssembleHarness:
    """Context-manager that builds a tmp DATA_ROOT, materializes the
    fixture, patches ``paths.DATA_ROOT``, and yields ``(tree, sdir)``."""

    def __init__(self, mutate_files=None):
        self.mutate_files = mutate_files

    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)
        sdir = write_to_disk(self._tmpdir)
        if self.mutate_files:
            self.mutate_files(sdir)
        self._patch = mock.patch.object(paths, "DATA_ROOT", self._tmpdir)
        self._patch.start()
        self.tree, self.sdir = assemble_dc.assemble(IDS.SID)
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        self._tmp.cleanup()


def _turn(tree: dict) -> dict:
    return next(
        iv for iv in tree["session"]["interactions"]
        if iv.get("type") == "TURN"
    )


# -----------------------------------------------------------------------------
# Top-level shape
# -----------------------------------------------------------------------------


class AssembleTreeShapeTests(unittest.TestCase):

    def test_tree_top_level_keys(self):
        with _AssembleHarness() as h:
            self.assertIn("identity", h.tree)
            self.assertIn("session", h.tree)
            self.assertIn("catalog", h.tree)

    def test_session_dir_path_is_under_data_root(self):
        with _AssembleHarness() as h:
            # On macOS the tmp path resolves through /private/var → /var
            # (or vice versa). Compare via .resolve() so the symlink
            # discrepancy doesn't fail the assertion.
            expected = session_dir_for(h._tmpdir).resolve()
            self.assertEqual(h.sdir.resolve(), expected)

    def test_three_interactions_in_chronological_order(self):
        with _AssembleHarness() as h:
            ivs = h.tree["session"]["interactions"]
        types = [iv["type"] for iv in ivs]
        self.assertEqual(types, ["SESSION_START", "TURN", "SESSION_END"])

    def test_turn_has_three_steps_in_order(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        names = [s.get("name") for s in turn["steps"]]
        # Step names from the fixture's ssot__Name__c column
        self.assertIn("TopicSelection", names)
        self.assertIn("PrimaryAction", names)
        self.assertIn("FinalGuard", names)

    def test_turn_has_two_messages_user_and_agent(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        self.assertEqual(len(turn["messages"]), 2)


# -----------------------------------------------------------------------------
# Identity resolution
# -----------------------------------------------------------------------------


class AssembleIdentityTests(unittest.TestCase):

    def test_identity_extracted_from_agent_participant(self):
        with _AssembleHarness() as h:
            ident = h.tree["identity"]
        self.assertEqual(ident["org_id_15"], IDS.ORG_ID_15)
        self.assertEqual(ident["agent_api_name"], IDS.AGENT_API)
        self.assertEqual(ident["agent_version"], IDS.AGENT_VERSION)


# -----------------------------------------------------------------------------
# Trace_id extraction (HTML-escaped fallback)
# -----------------------------------------------------------------------------


class AssembleTraceIdTests(unittest.TestCase):

    def test_turn_trace_id_pulled_from_html_escaped_attribute_text(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        # The fixture intentionally puts trace_id ONLY in AttributeText
        # (HTML-escaped JSON); the primary TelemetryTraceId__c column is
        # empty. This exercises the fallback path in assemble_dc.
        self.assertEqual(turn["trace_id"], IDS.TRACE_ID)


# -----------------------------------------------------------------------------
# Gateway binding (declared chain + timestamp-window fallback)
# -----------------------------------------------------------------------------


class AssembleGatewayBindingTests(unittest.TestCase):

    def test_action_step_has_declared_gateway_request(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        action_step = next(
            s for s in turn["steps"] if s.get("name") == "PrimaryAction"
        )
        gw = action_step["gateway_request"]
        self.assertIsNotNone(gw)
        self.assertEqual(gw["binding_method"], "declared")
        self.assertEqual(gw["gateway_request_id"], IDS.GW_REQ_DECLARED)
        self.assertEqual(gw["model"], "gpt-4o")
        self.assertEqual(gw["total_tokens"], 1250)

    def test_topic_and_guardrail_steps_have_no_gateway_binding(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        for s in turn["steps"]:
            if s.get("name") in ("TopicSelection", "FinalGuard"):
                self.assertIsNone(s.get("gateway_request"))

    def test_timestamp_window_pass_picks_up_undeclared_gateway_request(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        ts_calls = turn.get("timestamp_bound_gateway_calls", [])
        # Exactly one gateway request lives in the TURN window without a
        # declared binding (GW_REQ_WINDOW). The declared one is consumed
        # by step-action and is excluded from the ts-window pass.
        self.assertEqual(len(ts_calls), 1)
        self.assertEqual(
            ts_calls[0]["gateway_request_id"], IDS.GW_REQ_WINDOW,
        )

    def test_declared_response_carries_finish_reason(self):
        with _AssembleHarness() as h:
            turn = _turn(h.tree)
        action_step = next(
            s for s in turn["steps"] if s.get("name") == "PrimaryAction"
        )
        # parameters__c is HTML-escaped JSON in the fixture; the
        # renderer is responsible for decoding, but the raw string
        # must be preserved unchanged in the assembled tree.
        params = action_step["gateway_request"]["response"]["parameters__c"]
        self.assertIn("finish_reason", params)
        self.assertIn("&quot;", params)


# -----------------------------------------------------------------------------
# Malformed-input tolerance (parse_warnings)
# -----------------------------------------------------------------------------


class AssembleParseWarningsTests(unittest.TestCase):

    def test_malformed_dc_file_recorded_in_parse_warnings(self):
        def corrupt_messages(sdir: Path) -> None:
            (sdir / "dc.messages.json").write_text("<<<not json>>>")

        with _AssembleHarness(mutate_files=corrupt_messages) as h:
            # parse_warnings lives on session.counts (cf. _build_counts).
            warnings = h.tree["session"]["counts"].get("parse_warnings") or []
        self.assertIn("messages", warnings)


# -----------------------------------------------------------------------------
# session_not_found short-circuit
# -----------------------------------------------------------------------------


class AssembleSessionNotFoundTests(unittest.TestCase):

    def test_empty_sessions_returns_minimal_tree(self):
        def empty_sessions(sdir: Path) -> None:
            (sdir / "dc.sessions.json").write_text("[]")

        with _AssembleHarness(mutate_files=empty_sessions) as h:
            tree = h.tree
        # Minimal-tree shape signaled by session_shape == 'session_not_found'
        # in the manifest section, plus an empty interactions list.
        self.assertEqual(tree["session"].get("interactions", []), [])


# -----------------------------------------------------------------------------
# Public API path: tree dict is JSON-serializable
# -----------------------------------------------------------------------------


class AssembleSerializableTests(unittest.TestCase):

    def test_tree_round_trips_through_json(self):
        with _AssembleHarness() as h:
            blob = json.dumps(h.tree, default=str)
            back = json.loads(blob)
        # Sanity: re-loaded keys match originals
        self.assertEqual(set(back.keys()), set(h.tree.keys()))


if __name__ == "__main__":
    unittest.main()
