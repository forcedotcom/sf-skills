"""Additional ``render_dc`` tests targeting branches not covered by
``test_render_dc_integration.py``:

- ``main_for_session``     reads tree + manifest from disk; emits markdown
- ``main``                  argparse → main_for_session
- ``_parse_finish_reason``  HTML-escaped JSON parsing
- ``_decoded_line``         tool-call JSON detection
- mermaid sequence diagram  (requires ≥2 ACTION_STEPs OR an error_text)
- mermaid topic flowchart   (requires repeating topics across turns)
- schema-version refusal    on unsupported _schema_version
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore
import render_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import IDS, write_to_disk  # type: ignore


# -----------------------------------------------------------------------------
# main_for_session — disk-backed entry point
# -----------------------------------------------------------------------------


class MainForSessionTests(unittest.TestCase):

    def test_reads_tree_writes_summary_md(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            sdir = write_to_disk(tmp)
            with mock.patch.object(paths, "DATA_ROOT", tmp):
                tree, _ = assemble_dc.assemble(IDS.SID)
                (sdir / "dc._session_tree.json").write_text(
                    json.dumps(tree, default=str)
                )
                rc = render_dc.main_for_session(IDS.SID)
                self.assertEqual(rc, 0)
                summary_path = sdir / "dc._session_summary.md"
                self.assertTrue(summary_path.is_file())
                self.assertGreater(len(summary_path.read_text()), 1000)

    def test_raises_when_tree_missing(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            write_to_disk(tmp)  # creates session dir but not tree
            with mock.patch.object(paths, "DATA_ROOT", tmp):
                with self.assertRaises(SystemExit) as ctx:
                    render_dc.main_for_session(IDS.SID)
        self.assertIn("tree not found", str(ctx.exception))

    def test_tolerates_missing_manifest_with_warning(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            sdir = write_to_disk(tmp)
            with mock.patch.object(paths, "DATA_ROOT", tmp):
                tree, _ = assemble_dc.assemble(IDS.SID)
                (sdir / "dc._session_tree.json").write_text(
                    json.dumps(tree, default=str)
                )
                # Wipe the manifest. main_for_session should still succeed
                # (manifest is optional; missing → no manifest-driven sections).
                (sdir / "dc._session_manifest.json").unlink()
                rc = render_dc.main_for_session(IDS.SID)
                self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# main — argparse + resolve
# -----------------------------------------------------------------------------


class MainTests(unittest.TestCase):

    def test_main_invokes_main_for_session_with_resolved_sid(self):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            sdir = write_to_disk(tmp)
            with mock.patch.object(paths, "DATA_ROOT", tmp):
                tree, _ = assemble_dc.assemble(IDS.SID)
                (sdir / "dc._session_tree.json").write_text(
                    json.dumps(tree, default=str)
                )
                with mock.patch.object(
                    render_dc.sys, "argv",
                    ["render_dc.py", "--session", IDS.SID],
                ):
                    rc = render_dc.main()
        self.assertEqual(rc, 0)


# -----------------------------------------------------------------------------
# _parse_finish_reason — HTML-escaped JSON
# -----------------------------------------------------------------------------


class ParseFinishReasonTests(unittest.TestCase):

    def test_extracts_stop_from_double_escaped_json(self):
        # Real wire format: `{&quot;finish_reason&quot;:&quot;\"stop\"&quot;}`
        params = '{&quot;finish_reason&quot;:&quot;\\"stop\\"&quot;}'
        self.assertEqual(render_dc._parse_finish_reason(params), "stop")

    def test_returns_none_for_empty(self):
        self.assertIsNone(render_dc._parse_finish_reason(None))
        self.assertIsNone(render_dc._parse_finish_reason(""))

    def test_returns_none_for_unparseable_json(self):
        self.assertIsNone(render_dc._parse_finish_reason("<<<not json>>>"))

    def test_returns_none_when_finish_reason_not_string(self):
        params = '{&quot;finish_reason&quot;: 42}'
        self.assertIsNone(render_dc._parse_finish_reason(params))


# -----------------------------------------------------------------------------
# _decoded_line — tool-call JSON detection
# -----------------------------------------------------------------------------


class DecodedLineTests(unittest.TestCase):

    def test_returns_dash_for_empty(self):
        self.assertEqual(render_dc._decoded_line(None), "—")
        self.assertEqual(render_dc._decoded_line(""), "—")

    def test_renders_quoted_truncated_text_for_plain_string(self):
        out = render_dc._decoded_line("Hello world")
        self.assertEqual(out, '"Hello world"')

    def test_summarizes_tool_call_json(self):
        # Real wire shape: HTML-escaped JSON with toolInvocations array.
        body = (
            '{"toolInvocations":[{'
            '"function":{"name":"search_orders",'
            '"arguments":"{\\"query\\":\\"refund\\"}"}}],'
            '"content":"I will search for orders."}'
        )
        out = render_dc._decoded_line(body)
        self.assertIn("1 tool call", out)
        self.assertIn("search_orders", out)
        self.assertIn("query=", out)


# -----------------------------------------------------------------------------
# Multi-turn fixture for mermaid branches
# -----------------------------------------------------------------------------


def _add_extra_turn_to_tree(tree: dict) -> None:
    """Mutate the assembled tree to have a 2nd TURN with a topic that
    repeats — triggers both the sequence diagram and the topic flowchart.
    """
    # Tag the existing turn with a topic
    sess = tree["session"]
    for iv in sess["interactions"]:
        if iv["type"] == "TURN":
            iv["topic"] = "Refunds"
            # Inject a 2nd action step so sequence diagram passes its
            # has_error/len(actions)>=2 gate.
            iv["steps"].append({
                "id": "step-extra-action",
                "type": "ACTION_STEP",
                "name": "ExtraAction",
                "start_ts": "2026-04-22T10:00:42.000Z",
                "end_ts":   "2026-04-22T10:00:48.000Z",
                "error_text": None,
                "generation": None,
                "gateway_request": None,
            })
            break
    # Append a 2nd TURN that uses the same topic — triggers flowchart edges.
    sess["interactions"].append({
        "id": "ixn-turn-002b",
        "type": "TURN",
        "topic": "Refunds",
        "trace_id": "trace-2nd",
        "start_ts": "2026-04-22T10:01:05.000Z",
        "end_ts":   "2026-04-22T10:01:25.000Z",
        "steps": [
            {"id": "step-2a", "type": "ACTION_STEP",
             "name": "ActionA",
             "start_ts": "2026-04-22T10:01:08.000Z",
             "end_ts":   "2026-04-22T10:01:12.000Z",
             "error_text": None,
             "generation": None,
             "gateway_request": None},
            {"id": "step-2b", "type": "ACTION_STEP",
             "name": "ActionB",
             "start_ts": "2026-04-22T10:01:13.000Z",
             "end_ts":   "2026-04-22T10:01:18.000Z",
             "error_text": "Action B failed: timeout",
             "generation": None,
             "gateway_request": None},
        ],
        "messages": [
            {"role": "USER", "text": "I want to escalate.", "ts": None},
            {"role": "AGENT", "text": "Connecting you to a human.", "ts": None},
        ],
        "tag_associations": [], "telemetry_spans": [],
        "timestamp_bound_gateway_calls": [],
    })


class MultiTurnRenderTests(unittest.TestCase):

    def _assemble_and_render(self, tree_mutator):
        with TemporaryDirectory() as t:
            tmp = Path(t)
            sdir = write_to_disk(tmp)
            with mock.patch.object(paths, "DATA_ROOT", tmp):
                tree, _ = assemble_dc.assemble(IDS.SID)
                tree_mutator(tree)
                manifest = json.loads(
                    (sdir / "dc._session_manifest.json").read_text()
                )
                return render_dc.render(tree, manifest=manifest, session_dir=sdir)

    def test_sequence_diagram_emitted_when_turn_has_two_actions(self):
        md = self._assemble_and_render(_add_extra_turn_to_tree)
        self.assertIn("sequenceDiagram", md)
        self.assertIn("participant U as USER", md)
        self.assertIn("participant P as Planner", md)

    def test_topic_flowchart_emitted_when_topics_repeat(self):
        md = self._assemble_and_render(_add_extra_turn_to_tree)
        self.assertIn("flowchart LR", md)
        self.assertIn("Refunds", md)


# -----------------------------------------------------------------------------
# Schema-version guard
# -----------------------------------------------------------------------------


class SchemaVersionGuardTests(unittest.TestCase):

    def test_render_refuses_unsupported_schema_version(self):
        # _assert_schema_version reads session._schema_version (per impl).
        bad_tree = {
            "session": {"id": IDS.SID, "interactions": [], "_schema_version": 999},
        }
        with self.assertRaises(SystemExit) as ctx:
            render_dc.render(bad_tree)
        self.assertIn("unsupported tree _schema_version", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
