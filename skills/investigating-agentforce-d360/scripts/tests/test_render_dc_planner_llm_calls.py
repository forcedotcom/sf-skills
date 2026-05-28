"""Tests for the opt-in Planner LLM calls section in render_dc.

The full-tree branch of `render_dc.render()` by default surfaces only a
one-line `decoded:` summary on each generation. The `--show-prompts` flag
(CLI) / `show_prompts=True` (programmatic) opts in to a section that
emits the full prompt + response per LLM call.

Coverage:
  - assemble_dc: hierarchical-tree gw view carries `prompt_text` + `prompt_template_dev_name`
  - render_dc: section omitted by default
  - render_dc: section emitted with show_prompts=True
  - render_dc: section walks all interactions[].steps[] and renders one block per gateway_request
  - render_dc: 64 KB byte-cap on prompt display still applies (regression guard)
  - render_dc: empty/missing prompt → renders `(empty)` not crash
  - render_dc: response_text is HTML-unescaped before display
  - render_dc: gateway-direct branch unchanged (still emits Per-call detail)

Test isolation: synthesizes a session tree in memory (no on-disk DC fetch),
calls `render(...)` directly, and asserts on the produced markdown.
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore
import render_dc  # type: ignore


# ---------------------------------------------------------------------------
# Test fixtures: minimal full-tree shape that render() will accept
# ---------------------------------------------------------------------------

def _full_tree(*, with_prompt_text: bool = True,
               with_response_text: bool = True,
               num_calls: int = 2) -> dict:
    """Build a synthetic full-tree dict with `num_calls` gateway requests."""
    steps = []
    for i in range(num_calls):
        gw = {
            "gateway_request_id": f"gw-id-{i}",
            "model": "gpt-4.1-2025-04-14",
            "provider": "salesforce",
            "prompt_template_dev_name": "Atlas__AgentGraphReasoningPrompt",
            "prompt_tokens": 100 + i,
            "completion_tokens": 50,
            "total_tokens": 150 + i,
            "prompt_text": (
                f"role: user\nMessage {i}\nrole: assistant\nResponse {i}"
                if with_prompt_text else None
            ),
            "response": {"finish_reason": "stop"},
        }
        gen = {
            "generation_id": f"gen-{i}",
            "response_text": (
                f'{{"content":"","toolInvocations":[{{"id":"call_{i}",'
                f'"function":{{"name":"some_tool","arguments":"{{}}"}}}}]}}'
                if with_response_text else None
            ),
        }
        steps.append({
            "id": f"step-{i}",
            "type": "LLM_STEP",
            "gateway_request": gw,
            "generation": gen,
        })
    return {
        "session": {
            "_schema_version": 1,
            "id": "fixture-session-uuid-0000",
            "start_ts": "2026-05-14T10:00:00.000Z",
            "end_ts": "2026-05-14T10:00:30.000Z",
            "identity": {},
            "interactions": [{
                "id": "interaction-0000",
                "type": "TURN",
                "steps": steps,
            }],
        },
    }


# ---------------------------------------------------------------------------
# Assembler: _build_gw_view now carries prompt_text + prompt_template_dev_name
# ---------------------------------------------------------------------------

class BuildGwViewCarriesPromptTests(unittest.TestCase):
    """Hierarchical view propagates prompt__c so renderer can use it."""

    def _idx_dispatch(self):
        from assemble_dc import Indexes, PolymorphicSplits
        idx = Indexes(
            interactions_by_id={}, participants_by_id={},
            generations_by_id={}, gw_req_by_id={},
            gw_resp_by_resp_id={}, feedback_by_id={},
            gw_resp_by_req_id={}, steps_by_interaction={},
            messages_by_interaction={}, gw_tags_by_parent={},
            gw_md_by_parent={}, gw_llm_by_parent={},
            quality_by_parent={}, quality_by_id={},
            feedback_by_gen={}, feedback_details_by_parent={},
            participant_role_by_id={},
        )
        dispatch = PolymorphicSplits(
            categories_by_generation={}, categories_by_quality={},
            gw_records_by_gw_req={}, gw_records_by_feedback={},
            tag_assoc_session=[], tag_assoc_by_interaction={},
            tag_assoc_by_moment={},
        )
        return idx, dispatch

    def test_prompt_text_propagated(self):
        idx, dispatch = self._idx_dispatch()
        gw_req = {
            "gatewayRequestId__c": "gw-fixture-0000",
            "feature__c": "plannerservice",
            "model__c": "gpt-4.1",
            "provider__c": "salesforce",
            "promptTemplateDevName__c": "Atlas__AgentGraphReasoningPrompt",
            "promptTokens__c": 874.0,
            "completionTokens__c": 1.0,
            "totalTokens__c": 875.0,
            "prompt__c": "role: user\nHello\nrole: assistant\nHi",
        }
        view = assemble_dc._build_gw_view(
            gw_req, "declared", idx=idx, dispatch=dispatch,
        )
        self.assertEqual(view["prompt_text"],
                         "role: user\nHello\nrole: assistant\nHi")
        self.assertEqual(view["prompt_template_dev_name"],
                         "Atlas__AgentGraphReasoningPrompt")

    def test_missing_prompt_propagates_as_none(self):
        """No prompt__c on the source row → view.prompt_text is None, no crash."""
        idx, dispatch = self._idx_dispatch()
        gw_req = {"gatewayRequestId__c": "gw-no-prompt"}
        view = assemble_dc._build_gw_view(
            gw_req, "declared", idx=idx, dispatch=dispatch,
        )
        self.assertIsNone(view["prompt_text"])


# ---------------------------------------------------------------------------
# Renderer: opt-in section
# ---------------------------------------------------------------------------

class RenderShowPromptsOffByDefaultTests(unittest.TestCase):

    def test_section_absent_by_default(self):
        tree = _full_tree()
        md = render_dc.render(tree)
        self.assertNotIn("Planner LLM calls", md)
        self.assertNotIn("**Prompt** (full input sent to the model)", md)

    def test_section_present_with_flag(self):
        tree = _full_tree()
        md = render_dc.render(tree, show_prompts=True)
        self.assertIn("## Planner LLM calls", md)
        self.assertIn("**Prompt**", md)


class RenderShowPromptsContentsTests(unittest.TestCase):

    def test_section_renders_one_block_per_call(self):
        tree = _full_tree(num_calls=3)
        md = render_dc.render(tree, show_prompts=True)
        # Three "#### LLM call N" headers — one per gateway_request.
        self.assertEqual(md.count("#### LLM call 1 — "), 1)
        self.assertEqual(md.count("#### LLM call 2 — "), 1)
        self.assertEqual(md.count("#### LLM call 3 — "), 1)
        # Both blocks (prompt + response) per call → 3 of each.
        self.assertEqual(md.count("**Prompt**"), 3)
        self.assertEqual(md.count("**Response**"), 3)

    def test_prompt_text_appears_verbatim(self):
        tree = _full_tree(num_calls=1)
        md = render_dc.render(tree, show_prompts=True)
        self.assertIn("role: user\nMessage 0\nrole: assistant\nResponse 0", md)

    def test_response_text_html_unescaped(self):
        """Generation.response_text may have &quot; from the wire format —
        renderer must HTML-unescape before fenced-block insertion."""
        tree = _full_tree(num_calls=1)
        # Replace the response with HTML-escaped content.
        tree["session"]["interactions"][0]["steps"][0]["generation"]["response_text"] = (
            '{&quot;content&quot;:&quot;Hello&quot;}'
        )
        md = render_dc.render(tree, show_prompts=True)
        self.assertIn('{"content":"Hello"}', md)
        self.assertNotIn("&quot;", md)

    def test_empty_prompt_renders_empty_marker_not_crash(self):
        """Missing prompt + response → block emits `(empty)` cleanly."""
        tree = _full_tree(with_prompt_text=False, with_response_text=False,
                          num_calls=1)
        md = render_dc.render(tree, show_prompts=True)
        # Both blocks present, but the body is `(empty)`.
        self.assertIn("**Prompt**", md)
        self.assertIn("(empty)", md)

    def test_section_empty_when_no_steps_have_gateway_request(self):
        """Steps without gateway_request → no section emitted at all."""
        tree = _full_tree(num_calls=1)
        # Strip the gateway_request off the only step.
        tree["session"]["interactions"][0]["steps"][0].pop("gateway_request")
        md = render_dc.render(tree, show_prompts=True)
        self.assertNotIn("## Planner LLM calls", md)


class RenderPromptDisplayCapTests(unittest.TestCase):
    """Regression guard: the 64 KB byte-cap from the gateway-direct path
    still applies on the new full-tree path."""

    def test_oversize_prompt_truncated(self):
        tree = _full_tree(num_calls=1)
        # 100 KB of ASCII — well over the 64 KB cap.
        oversize = "x" * (100 * 1024)
        tree["session"]["interactions"][0]["steps"][0][
            "gateway_request"]["prompt_text"] = oversize
        md = render_dc.render(tree, show_prompts=True)
        # Truncation marker present.
        self.assertIn("…[truncated; full prompt in dc.gateway_requests.json]",
                      md)
        # Body capped — not the full 100 KB.
        self.assertLess(md.count("x"), 100 * 1024)


class RenderGatewayDirectUnchangedTests(unittest.TestCase):
    """The gateway-direct branch (STDM-not-yet-materialized) keeps emitting
    its Per-call detail section header + per-call summary line by default.
    The full prompt body is gated behind ``show_prompts=True`` to match the
    documented contract for ``dc._session_summary.md`` (default summary
    omits prompts; ``--show-prompts`` opts in).
    """

    def _gateway_direct_tree(self):
        return {
            "_source": "gateway_direct",
            "session": {
                "_schema_version": 1,
                "id": "fixture-session-uuid-0000",
                "start_ts": "2026-05-14T10:00:00.000Z",
                "end_ts": "2026-05-14T10:00:30.000Z",
                "identity": {},
                "gateway_chain": [{
                    "gateway_request_id": "gw-direct-0",
                    "model": "gpt-4.1",
                    "provider": "salesforce",
                    "prompt_template_dev_name": "Atlas__X",
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "prompt_text": "Some prompt",
                    "response": {"finish_reason": "stop"},
                }],
            },
        }

    def test_gateway_direct_per_call_section_header_still_emitted(self):
        """Default render keeps the Per-call detail header + summary line."""
        md = render_dc.render(self._gateway_direct_tree())
        # gateway-direct path's own header is "## Per-call detail".
        self.assertIn("## Per-call detail", md)
        # Per-call summary line (model/provider/tokens) still emits.
        self.assertIn("model=gpt-4.1", md)
        # Prompt body suppressed by default (matches doc contract).
        self.assertNotIn("Some prompt", md)
        self.assertNotIn("**Prompt**", md)
        # gateway-direct never has response_text → no Response block.
        self.assertNotIn("**Response**", md)

    def test_gateway_direct_per_call_detail_with_show_prompts(self):
        """Opt-in render exposes the full prompt body in the per-call block."""
        md = render_dc.render(self._gateway_direct_tree(), show_prompts=True)
        self.assertIn("## Per-call detail", md)
        self.assertIn("**Prompt**", md)
        self.assertIn("Some prompt", md)
        # Response block still suppressed — gateway-direct never carries it.
        self.assertNotIn("**Response**", md)


if __name__ == "__main__":
    unittest.main()
