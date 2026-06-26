"""Default-gating contract for the ``--show-prompts`` flag in render_dc.

Both render branches — gateway-direct (STDM lag) and full-tree (post-STDM
materialization) — must suppress the full prompt block by default and only
emit it when the caller opts in via ``show_prompts=True`` (CLI:
``--show-prompts``).

This pins the doc contract from ``SKILL.md``:

    The default ``dc._session_summary.md`` does NOT include the input
    prompt or the model's full response — only a one-line ``decoded:``
    summary on each generation. When the user asks for the actual prompt
    sent to the model … re-render with the ``--show-prompts`` flag.

A regression on the gateway-direct branch (renderer dropped the
parameter on the ``--show-prompts`` plumbing path) leaked the full prompt
on every fresh-session render. These tests guard both branches and the
``_render_call_detail_block`` helper directly so the two flags
(``show_prompts`` / ``show_response_text``) gate independently.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

import render_dc  # type: ignore


# Distinct sentinel strings so test failures point at the exact branch
# that leaked. ``role: user`` is included because the live render uses
# that exact substring on real prompts and `grep` searches in the
# investigation runbook key off it.
_GATEWAY_DIRECT_PROMPT_MARKER = "ROLE-USER-GATEWAY-DIRECT-MARKER"
_FULL_TREE_PROMPT_MARKER = "ROLE-USER-FULL-TREE-MARKER"
_FULL_TREE_RESPONSE_MARKER = "ROLE-ASSISTANT-FULL-TREE-MARKER"


def _gateway_direct_tree_with_marker() -> dict:
    """Synthetic gateway-direct tree carrying a unique prompt marker."""
    return {
        "_source": "gateway_direct",
        "session": {
            "_schema_version": 1,
            "id": "fixture-gd-session-0000",
            "start_ts": "2026-05-26T10:00:00.000Z",
            "end_ts": "2026-05-26T10:00:30.000Z",
            "identity": {},
            "gateway_chain": [{
                "gateway_request_id": "gw-gd-0",
                "model": "gpt-4.1",
                "provider": "salesforce",
                "prompt_template_dev_name": "Atlas__X",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "prompt_text": _GATEWAY_DIRECT_PROMPT_MARKER,
                "response": {"finish_reason": "stop"},
            }],
        },
    }


def _full_tree_with_marker() -> dict:
    """Synthetic full-tree session with one LLM call, unique markers."""
    return {
        "session": {
            "_schema_version": 1,
            "id": "fixture-ft-session-0000",
            "start_ts": "2026-05-26T10:00:00.000Z",
            "end_ts": "2026-05-26T10:00:30.000Z",
            "identity": {},
            "interactions": [{
                "id": "interaction-0000",
                "type": "TURN",
                "steps": [{
                    "id": "step-0",
                    "type": "LLM_STEP",
                    "gateway_request": {
                        "gateway_request_id": "gw-ft-0",
                        "model": "gpt-4.1",
                        "provider": "salesforce",
                        "prompt_template_dev_name": "Atlas__X",
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                        "prompt_text": _FULL_TREE_PROMPT_MARKER,
                        "response": {"finish_reason": "stop"},
                    },
                    "generation": {
                        "generation_id": "gen-0",
                        "response_text": _FULL_TREE_RESPONSE_MARKER,
                    },
                }],
            }],
        },
    }


# ---------------------------------------------------------------------------
# Gateway-direct branch (the leaky branch this fix targets)
# ---------------------------------------------------------------------------


class GatewayDirectBranchGatingTests(unittest.TestCase):

    def test_gateway_direct_no_prompt_block_by_default(self):
        """Default render: no **Prompt** heading, no prompt body bytes."""
        md = render_dc.render(_gateway_direct_tree_with_marker())
        self.assertNotIn(_GATEWAY_DIRECT_PROMPT_MARKER, md)
        self.assertNotIn("**Prompt**", md)
        # The Per-call detail section header itself stays — only the
        # body is gated.
        self.assertIn("## Per-call detail", md)

    def test_gateway_direct_emits_prompt_block_when_show_prompts_true(self):
        """Opt-in render: prompt body + heading both surface."""
        md = render_dc.render(_gateway_direct_tree_with_marker(),
                              show_prompts=True)
        self.assertIn(_GATEWAY_DIRECT_PROMPT_MARKER, md)
        self.assertIn("**Prompt**", md)


# ---------------------------------------------------------------------------
# Full-tree branch (regression guard — already correctly gated, lock it in)
# ---------------------------------------------------------------------------


class FullTreeBranchGatingTests(unittest.TestCase):

    def test_full_tree_no_prompt_block_by_default_regression(self):
        """Full-tree default: no Planner LLM calls section, no prompt body."""
        md = render_dc.render(_full_tree_with_marker())
        self.assertNotIn(_FULL_TREE_PROMPT_MARKER, md)
        self.assertNotIn("**Prompt**", md)
        self.assertNotIn("## Planner LLM calls", md)

    def test_full_tree_emits_prompt_block_when_show_prompts_true_regression(self):
        """Full-tree opt-in: section header + prompt + response all surface."""
        md = render_dc.render(_full_tree_with_marker(), show_prompts=True)
        self.assertIn("## Planner LLM calls", md)
        self.assertIn("**Prompt**", md)
        self.assertIn(_FULL_TREE_PROMPT_MARKER, md)
        self.assertIn("**Response**", md)
        self.assertIn(_FULL_TREE_RESPONSE_MARKER, md)


# ---------------------------------------------------------------------------
# Helper: independent gating of prompt vs response block
# ---------------------------------------------------------------------------


class RenderCallDetailBlockHelperTests(unittest.TestCase):
    """``_render_call_detail_block`` must gate prompt and response
    independently. The gateway-direct path uses
    ``show_prompts=False, show_response_text=False`` by default, while
    the full-tree path post-fix uses
    ``show_prompts=True, show_response_text=True`` once the section
    guard has cleared. Mixed combinations must work too."""

    def _call(self):
        return {
            "gateway_request_id": "gw-helper-0",
            "model": "gpt-4.1",
            "provider": "salesforce",
            "prompt_template_dev_name": "Atlas__X",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "prompt_text": "PROMPT-MARKER",
            "response": {"finish_reason": "stop"},
            "response_text": "RESPONSE-MARKER",
        }

    def test_response_only(self):
        """show_prompts=False + show_response_text=True → response only."""
        block = "\n".join(render_dc._render_call_detail_block(
            self._call(), 1, show_prompts=False, show_response_text=True))
        self.assertNotIn("**Prompt**", block)
        self.assertNotIn("PROMPT-MARKER", block)
        self.assertIn("**Response**", block)
        self.assertIn("RESPONSE-MARKER", block)

    def test_prompt_only(self):
        """show_prompts=True + show_response_text=False → prompt only."""
        block = "\n".join(render_dc._render_call_detail_block(
            self._call(), 1, show_prompts=True, show_response_text=False))
        self.assertIn("**Prompt**", block)
        self.assertIn("PROMPT-MARKER", block)
        self.assertNotIn("**Response**", block)
        self.assertNotIn("RESPONSE-MARKER", block)

    def test_neither(self):
        """Both flags off → summary line only, no fenced blocks."""
        block = "\n".join(render_dc._render_call_detail_block(
            self._call(), 1))
        self.assertNotIn("**Prompt**", block)
        self.assertNotIn("**Response**", block)
        self.assertNotIn("PROMPT-MARKER", block)
        self.assertNotIn("RESPONSE-MARKER", block)
        # Summary line still emits.
        self.assertIn("model=gpt-4.1", block)

    def test_both(self):
        """Both flags on → both blocks present."""
        block = "\n".join(render_dc._render_call_detail_block(
            self._call(), 1, show_prompts=True, show_response_text=True))
        self.assertIn("**Prompt**", block)
        self.assertIn("PROMPT-MARKER", block)
        self.assertIn("**Response**", block)
        self.assertIn("RESPONSE-MARKER", block)


if __name__ == "__main__":
    unittest.main()
