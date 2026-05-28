"""End-to-end integration tests for ``render_dc.render``.

Drives the full renderer against the synthetic session fixture (assembled
through ``assemble_dc.assemble`` first). Asserts on section presence,
substring content of identity / transcript / hierarchical-trace / id-ref
sections, and graceful degradation paths (no session_dir, gateway-direct
shape, minimal tree).
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
from .fixtures.synthetic_session import (  # type: ignore
    IDS, write_to_disk,
)


class _RenderHarness:
    """Materialize fixture, assemble, render."""

    def __init__(self, *, with_session_dir: bool = True,
                 mutate_files=None):
        self.with_session_dir = with_session_dir
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
        self.manifest = json.loads(
            (self.sdir / "dc._session_manifest.json").read_text()
        )
        self.md = render_dc.render(
            self.tree,
            manifest=self.manifest,
            session_dir=self.sdir if self.with_session_dir else None,
        )
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        self._tmp.cleanup()


# -----------------------------------------------------------------------------
# Top-level shape — sections present
# -----------------------------------------------------------------------------


class RenderSectionsPresentTests(unittest.TestCase):

    def test_renders_session_identity_section(self):
        with _RenderHarness() as h:
            self.assertIn("## Session identity", h.md)

    def test_renders_id_reference_section(self):
        with _RenderHarness() as h:
            self.assertIn("## ID reference", h.md)

    def test_renders_hierarchical_trace_section(self):
        with _RenderHarness() as h:
            self.assertIn("## Complete hierarchical trace", h.md)

    def test_renders_per_turn_summary_section(self):
        with _RenderHarness() as h:
            self.assertIn("## Per-turn summary", h.md)

    def test_renders_transcript_section(self):
        with _RenderHarness() as h:
            self.assertIn("## Transcript", h.md)


# -----------------------------------------------------------------------------
# Identity content
# -----------------------------------------------------------------------------


class RenderIdentityTests(unittest.TestCase):

    def test_identity_shows_session_id(self):
        with _RenderHarness() as h:
            self.assertIn(IDS.SID, h.md)

    def test_identity_shows_messaging_session_id(self):
        with _RenderHarness() as h:
            self.assertIn("0MwTESTMSG12345AAA", h.md)

    def test_identity_shows_total_duration_in_human_form(self):
        with _RenderHarness() as h:
            # Session is 90 seconds → "1m 30.000s"
            self.assertIn("1m 30.000s", h.md)

    def test_identity_shows_channel_and_end_type(self):
        with _RenderHarness() as h:
            self.assertIn("SCRT2 - EmbeddedMessaging", h.md)
            self.assertIn("USER_ENDED", h.md)

    def test_identity_marks_session_end_as_materialized(self):
        with _RenderHarness() as h:
            self.assertIn("✓ materialized", h.md)


# -----------------------------------------------------------------------------
# ID reference
# -----------------------------------------------------------------------------


class RenderIdReferenceTests(unittest.TestCase):

    def test_id_ref_lists_all_three_interactions(self):
        with _RenderHarness() as h:
            self.assertIn(IDS.IXN_START, h.md)
            self.assertIn(IDS.IXN_TURN, h.md)
            self.assertIn(IDS.IXN_END, h.md)

    def test_id_ref_lists_both_participants_with_roles(self):
        with _RenderHarness() as h:
            self.assertIn(IDS.PART_AGENT, h.md)
            self.assertIn(IDS.PART_USER, h.md)
            self.assertIn("role=AGENT", h.md)
            self.assertIn("role=USER", h.md)

    def test_id_ref_lists_all_three_steps(self):
        with _RenderHarness() as h:
            self.assertIn("TopicSelection", h.md)
            self.assertIn("PrimaryAction", h.md)
            self.assertIn("FinalGuard", h.md)

    def test_id_ref_lists_both_gateway_requests_with_binding_method(self):
        with _RenderHarness() as h:
            self.assertIn(IDS.GW_REQ_DECLARED, h.md)
            self.assertIn(IDS.GW_REQ_WINDOW, h.md)
            self.assertIn("binding=declared", h.md)
            self.assertIn("binding=timestamp_window", h.md)

    def test_id_ref_includes_extracted_trace_id(self):
        with _RenderHarness() as h:
            # Trace_id was pulled from HTML-escaped AttributeText; once
            # decoded it must appear verbatim in the id-ref section.
            self.assertIn(IDS.TRACE_ID, h.md)


# -----------------------------------------------------------------------------
# Transcript
# -----------------------------------------------------------------------------


class RenderTranscriptTests(unittest.TestCase):

    def test_transcript_includes_user_message(self):
        with _RenderHarness() as h:
            self.assertIn("How do I refund my order?", h.md)

    def test_transcript_includes_agent_message(self):
        with _RenderHarness() as h:
            self.assertIn("I'll help you with the refund process.", h.md)


# -----------------------------------------------------------------------------
# Graceful degradation paths
# -----------------------------------------------------------------------------


class RenderDegradationTests(unittest.TestCase):

    def test_renders_without_session_dir(self):
        # No session_dir → no latency-rollup section, but the rest of
        # the render should succeed and contain the standard sections.
        with _RenderHarness(with_session_dir=False) as h:
            self.assertIn("## Session identity", h.md)
            self.assertIn("## Complete hierarchical trace", h.md)

    def test_minimal_tree_short_circuits_to_short_markdown(self):
        def empty_sessions(sdir: Path) -> None:
            (sdir / "dc.sessions.json").write_text("[]")

        with _RenderHarness(mutate_files=empty_sessions) as h:
            # session_not_found minimal tree still produces something
            # readable that contains the SID.
            self.assertIn(IDS.SID, h.md)
            # Doesn't produce the full 9-section layout — verify by
            # absence of a section that requires interactions.
            self.assertNotIn("## Complete hierarchical trace", h.md)


# -----------------------------------------------------------------------------
# Output is non-empty markdown
# -----------------------------------------------------------------------------


class RenderOutputBasicsTests(unittest.TestCase):

    def test_output_starts_with_h1_header(self):
        with _RenderHarness() as h:
            first_line = h.md.splitlines()[0]
            self.assertTrue(first_line.startswith("# Session "))

    def test_output_is_substantial(self):
        # A real session produces several KB; a hand-built fixture with
        # 1 turn + 3 steps + 2 gateway calls should produce ≥ 2 KB.
        with _RenderHarness() as h:
            self.assertGreater(len(h.md), 2000)


if __name__ == "__main__":
    unittest.main()
