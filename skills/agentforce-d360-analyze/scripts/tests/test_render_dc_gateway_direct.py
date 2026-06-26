"""Tests for ``render_dc._render_gateway_direct``.

Feeds a gateway-direct tree (built by ``_assemble_gateway_direct``)
through the public ``render()`` entry point and asserts on the emitted
markdown. The intent is to pin the section contract without coupling to
exact whitespace:

  - lag banner appears
  - gateway chain table has the expected header
  - one H4 per gateway_request_id in per-call detail
  - per-call detail includes a fenced code block for the prompt
  - Interaction-dependent sections are ABSENT (Hierarchical trace,
    Per-turn summary, Transcript, Session counts)
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

from assemble_dc import _assemble_gateway_direct  # type: ignore
from render_dc import render  # type: ignore

from .test_assemble_dc_gateway_direct import (
    _SID,
    _make_manifest,
    _make_rows,
)


class RenderGatewayDirectTests(unittest.TestCase):

    def setUp(self):
        rows = _make_rows()
        manifest = _make_manifest()
        self.tree = _assemble_gateway_direct(_SID, rows, manifest, parse_warnings=[])
        # Opt into prompt rendering — these tests exercise the *content* of
        # the per-call detail block, not the default-gating contract. The
        # default-gating tests live in test_render_dc_show_prompts_gating.py.
        self.md = render(self.tree, manifest, show_prompts=True)

    def test_starts_with_session_heading(self):
        self.assertTrue(self.md.startswith(f"# Session {_SID}"))

    def test_lag_banner_present(self):
        self.assertIn("STDM Interaction/Step/Message DMOs have not yet "
                      "materialized", self.md)
        self.assertIn("Re-run in 24–72h", self.md)

    def test_gateway_chain_table_header(self):
        self.assertIn("| Model | Provider", self.md)
        self.assertIn("Prompt tok", self.md)
        self.assertIn("Response ts", self.md)

    def test_h4_per_gateway_call(self):
        """3 fixture gateway_requests → 3 `#### LLM call N` headings."""
        h4_count = self.md.count("#### LLM call ")
        self.assertGreaterEqual(h4_count, 3)

    def test_prompt_fenced_code_block(self):
        """Per-call detail wraps the prompt in a fenced code block."""
        self.assertIn("```", self.md)
        self.assertIn("This is the prompt body for gw-1.", self.md)

    def test_no_hierarchical_trace_section(self):
        self.assertNotIn("Hierarchical trace", self.md)
        self.assertNotIn("Complete hierarchical trace", self.md)

    def test_no_per_turn_summary_section(self):
        self.assertNotIn("Per-turn summary", self.md)

    def test_no_transcript_section(self):
        self.assertNotIn("## Transcript", self.md)

    def test_session_identity_section_present(self):
        self.assertIn("## Session identity", self.md)

    def test_prompt_with_triple_backticks_uses_longer_fence(self):
        """Prompts containing ``` must get a 4+-backtick fence.

        LLM prompt templates commonly embed triple-backtick tool-use
        examples. A hardcoded ``` fence would close early and corrupt
        every section after the first such prompt.
        """
        rows = _make_rows()
        rows["gateway_requests"][0]["prompt__c"] = (
            "See this example:\n"
            "```python\n"
            "print('hi')\n"
            "```\n"
            "End of example."
        )
        manifest = _make_manifest()
        tree = _assemble_gateway_direct(_SID, rows, manifest, parse_warnings=[])
        md = render(tree, manifest, show_prompts=True)
        self.assertIn("````", md)  # 4-backtick fence
        self.assertIn("print('hi')", md)
        # The inner triple-backticks survive intact.
        self.assertIn("```python", md)

    def test_prompt_with_four_backticks_uses_five_backtick_fence(self):
        """Fence length scales with the longest inner run of backticks."""
        rows = _make_rows()
        rows["gateway_requests"][0]["prompt__c"] = (
            "Edge case:\n````\nnested\n````\nDone."
        )
        manifest = _make_manifest()
        tree = _assemble_gateway_direct(_SID, rows, manifest, parse_warnings=[])
        md = render(tree, manifest, show_prompts=True)
        self.assertIn("`````", md)  # 5-backtick fence

    def test_prompt_truncation_marker_for_oversized_prompt(self):
        """Display-only 64 KB cap: prompts over the limit carry a truncation marker.

        Raw JSON on disk is untouched — the cap only applies to markdown.
        """
        rows = _make_rows()
        # Inflate the first prompt to 80 KB of ASCII.
        rows["gateway_requests"][0]["prompt__c"] = "x" * 80_000
        manifest = _make_manifest()
        tree = _assemble_gateway_direct(_SID, rows, manifest, parse_warnings=[])
        md = render(tree, manifest, show_prompts=True)
        self.assertIn("[truncated; full prompt in dc.gateway_requests.json]", md)
        # The on-tree prompt_text is still the full 80 KB — the cap is render-only.
        self.assertEqual(len(tree["session"]["gateway_chain"][0]["prompt_text"]),
                         80_000)


if __name__ == "__main__":
    unittest.main()
