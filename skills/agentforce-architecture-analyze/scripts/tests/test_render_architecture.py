"""Tests for render_architecture.render + load_mermaid.

P2.2-1: exercise every per-generation branch (classic ReAct, classic
Sequential, NGA ConcurrentMultiAgent, search/BYOP placeholder), the
_partial / _unresolved / cycle surfaces, and the node-cap behaviour.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401 — sys.path setup

import render_architecture  # type: ignore

# SKILL_ROOT is now file-relative (config.py uses
# Path(__file__).resolve().parent.parent), so config.MERMAID_DIR auto-
# resolves to the repo's assets/mermaid/ under test. We still construct
# _REPO_MERMAID_DIR explicitly for tests that compare paths or pass them
# as args; render_architecture's own MERMAID_DIR captures the right path
# at module import time.
_REPO_MERMAID_DIR = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "mermaid"
)


def _classic_react_tree() -> dict:
    """MyAgent v5 shape — classic ReAct, 2 topics, a handful of
    children to keep the fixture inline-readable."""
    return {
        "_schema_version": "3.0",
        "agent": {
            "api_name": "MyAgent",
            "version": "v5",
            "master_label": "Xero support AI",
            "description": "External-facing service agent.",
            "agent_type": "EinsteinAgentKind",
            "type": "ExternalCopilot",
            "agent_template": "SvcCopilotTmpl__EinsteinAgentKind",
            "bot_source": "None",
            "generation": "classic",
            "planner_name": "MyAgent_v2_v3_v4_v5",
            "planner_type": "AiCopilot__ReAct",
            "bot_id": "0XxXx00000000FdKAI",
        },
        "root": {
            "kind": "BOT_DEFINITION",
            "api_name": "MyAgent",
            "children": [
                {
                    "kind": "TOPIC",
                    "api_name": "Customer_Q_A",
                    "children": [
                        {
                            "kind": "GEN_AI_FUNCTION",
                            "api_name": "Find_Articles",
                            "unwraps_to": {"kind": "FLOW",
                                           "api_name": "Find_Public_Articles"},
                            "children": [
                                {
                                    "kind": "FLOW",
                                    "api_name": "Find_Public_Articles",
                                    "children": [
                                        {"kind": "APEX",
                                         "api_name": "KnowledgeRetriever"},
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "kind": "TOPIC",
                    "api_name": "Escalation",
                    "children": [
                        {
                            "kind": "GEN_AI_FUNCTION",
                            "api_name": "Escalate",
                            "unwraps_to": {"kind": "APEX",
                                           "api_name": "EscalateAction"},
                            "children": [
                                {"kind": "APEX", "api_name": "EscalateAction"},
                            ],
                        },
                    ],
                },
            ],
        },
        "node_count": 8,
        "depth": 4,
        "_partial": False,
        "_pending_fetches": {"Flow": [], "ApexClass": [], "GenAiPromptTemplate": []},
        "_unresolved": [],
        "_kind_counts": {
            "BOT_DEFINITION": 1,
            "TOPIC": 2,
            "GEN_AI_FUNCTION": 2,
            "FLOW": 1,
            "APEX": 2,
        },
    }


def _nga_tree() -> dict:
    t = _classic_react_tree()
    t["agent"]["generation"] = "nga"
    t["agent"]["planner_name"] = "Atlas__ConcurrentMultiAgentOrchestration"
    t["agent"]["planner_type"] = "Atlas__ConcurrentMultiAgentOrchestration"
    return t


def _sequential_tree() -> dict:
    """Zero-topic Sequential planner (classic)."""
    return {
        "_schema_version": "3.0",
        "agent": {
            "api_name": "KAMAgent",
            "version": "v5",
            "generation": "classic",
            "planner_name": "KAM_Planner",
            "planner_type": "AiCopilot__SequentialPlannerIntentClassifier",
        },
        "root": {
            "kind": "BOT_DEFINITION",
            "api_name": "KAMAgent",
            "children": [
                {
                    "kind": "GEN_AI_FUNCTION",
                    "api_name": "SalesPlay",
                    "children": [],
                },
            ],
        },
        "node_count": 2,
        "depth": 1,
        "_partial": False,
        "_pending_fetches": {},
        "_unresolved": [],
        "_kind_counts": {"BOT_DEFINITION": 1, "GEN_AI_FUNCTION": 1},
    }


def _write_tree(tmp: Path, tree: dict) -> Path:
    p = tmp / "metadata_tree.json"
    p.write_text(json.dumps(tree))
    return p


class _RenderTestBase(unittest.TestCase):
    """Shared setup: patch MERMAID_DIR at the renderer binding + tmp dir.

    Every test that invokes `render_architecture.render` or
    `render_architecture.load_mermaid` patches MERMAID_DIR to point at the
    repo's `assets/mermaid/`. With file-relative SKILL_ROOT this is now
    coincident with the natural resolution, but the explicit patch keeps
    each TestCase deterministic and isolated from any sys.path drift.
    """

    def setUp(self) -> None:
        self._patch = mock.patch.object(
            render_architecture, "MERMAID_DIR", _REPO_MERMAID_DIR,
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)


class RenderClassicReActTests(_RenderTestBase):
    def test_all_eight_sections_present(self):
        tree_path = _write_tree(self.tmp, _classic_react_tree())
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        # Section headers 2..8 all present; H1 covers section 1.
        # Invocation sequence (formerly section 3) was removed from the
        # default pipeline in 2026-05 — the heuristic was not trusted.
        # Planner state machine (formerly section 6) was also removed in
        # 2026-05. Both `_render_invocation_sequence` and
        # `_render_planner_state` stay callable for a future re-enable;
        # see `test_nga_invocation_sequence_has_orchestrator_lane` and
        # `test_nga_state_diagram_has_par_and_block`.
        self.assertIn("# Architecture", text)
        for heading in (
            "## 2. Anatomy summary",
            "## 3. Action tree",
            "## 4. Topic anatomy",
            "## 5. Action catalog",
            "## 6. Data flow / context propagation",
            "## 7. Flow / Apex / Prompt catalogs",
            "## 8. Unresolved refs + artifact pointers",
        ):
            self.assertIn(heading, text)
        # Explicit regression guard: the retired sections must NOT appear.
        self.assertNotIn("## 3. Invocation sequence", text)
        self.assertNotIn("Invocation sequence", text)
        self.assertNotIn("Planner state machine", text)

    def test_two_mermaid_diagrams_rendered(self):
        tree_path = _write_tree(self.tmp, _classic_react_tree())
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        # each diagram-kind keyword must appear as a bare
        # non-comment line inside exactly one fenced block. Keywords in
        # prose inside `%%` comments are now harmless (Mermaid parses
        # them as comments at render time), so we don't policework the
        # comment contents — we only require a real keyword line.
        # sequenceDiagram was removed from the default pipeline in 2026-05
        # along with the Invocation sequence section; stateDiagram-v2
        # was removed the same cycle along with Planner state machine.
        import re
        blocks = re.findall(r"```mermaid\n(.*?)\n```", text, re.DOTALL)
        keywords = {"flowchart TB", "flowchart LR"}
        seen_keywords: set[str] = set()
        for b in blocks:
            for ln in b.splitlines():
                stripped = ln.strip()
                if stripped.startswith("%%"):
                    continue
                if stripped in keywords:
                    seen_keywords.add(stripped)
        self.assertEqual(seen_keywords, keywords)
        # Regression: sequenceDiagram and stateDiagram-v2 must NOT appear
        # in the default render.
        for b in blocks:
            for ln in b.splitlines():
                stripped = ln.strip()
                if stripped.startswith("%%"):
                    continue
                self.assertNotEqual(stripped, "sequenceDiagram")
                self.assertNotEqual(stripped, "stateDiagram-v2")
        # Every block must be fully substituted — no stray `{{PARAM}}`
        # tokens left behind. removed the `{{...}}` from
        # comment headers precisely to make this invariant hold.
        for b in blocks:
            self.assertNotIn("{{", b)
            self.assertNotIn("}}", b)
        # No dependency graph when _unresolved is empty.
        self.assertNotIn("## Dependency graph", text)

    def test_react_state_machine_not_in_default_render(self):
        # Planner state machine was retired from the default pipeline in
        # 2026-05. Thought/Action/Observation states are emitted by
        # `_render_planner_state` which is still tested directly but not
        # wired into `render`.
        tree_path = _write_tree(self.tmp, _classic_react_tree())
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertNotIn("Thought", text)
        self.assertNotIn("Action --> Observation", text)


class RenderNgaTests(_RenderTestBase):
    def test_nga_state_diagram_has_par_and_block(self):
        # `_render_planner_state` was removed from the default render
        # pipeline in 2026-05, but the function + mermaid template are
        # retained so the feature can be re-enabled by uncommenting one
        # line in `render`. This test exercises the function directly to
        # keep the NGA par/and-block behaviour covered.
        tree = _nga_tree()
        rendered = render_architecture._render_planner_state(
            tree["agent"], "nga",
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        # par/and block marker is the `--` separator inside an `Orchestration`
        # state nest. Also confirm the lanes differ from ReAct.
        self.assertIn("state Orchestration", rendered)
        self.assertIn("--", rendered)
        self.assertIn("SubAgentA", rendered)
        self.assertIn("SubAgentB", rendered)
        # ReAct-specific states must NOT appear.
        self.assertNotIn("Thought", rendered)

    def test_nga_invocation_sequence_has_orchestrator_lane(self):
        # `_render_invocation_sequence` was removed from the default
        # render pipeline in 2026-05 (heuristic distrusted), but the
        # function + mermaid template are retained so the feature can
        # be re-enabled by uncommenting one line in `render`. This test
        # exercises the function directly to keep the behaviour covered.
        tree = _nga_tree()
        walker = render_architecture._TreeWalker(tree)
        walker.walk()
        rendered = render_architecture._render_invocation_sequence(
            tree, tree["agent"], walker,
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        self.assertIn("participant Orchestrator", rendered)
        self.assertIn("participant SubAgent", rendered)


class RenderSequentialTests(_RenderTestBase):
    def test_sequential_zero_topic_produces_empty_topic_section(self):
        tree_path = _write_tree(self.tmp, _sequential_tree())
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("_No topics defined", text)
        # Sequential state machine uses Classify -> Execute, but the
        # Planner state machine section was retired from the default
        # pipeline in 2026-05 — exercise the helper directly instead.
        rendered = render_architecture._render_planner_state(
            _sequential_tree()["agent"], "classic",
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        self.assertIn("Classify --> Execute", rendered)

    def test_sequential_does_not_emit_react_states(self):
        tree_path = _write_tree(self.tmp, _sequential_tree())
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertNotIn("Thought", text)
        self.assertNotIn("Orchestration", text)


class RenderPartialTreeTests(_RenderTestBase):
    def test_partial_true_emits_health_callout(self):
        tree = _classic_react_tree()
        tree["_partial"] = True
        tree["_partial_reason"] = "flow-metadata-timeout"
        tree["_pending_fetches"] = {"FLOW": ["Foo", "Bar"], "APEX": []}
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("**Health: PARTIAL.**", text)
        self.assertIn("flow-metadata-timeout", text)
        self.assertIn("Pending fetches: 2", text)

    def test_missing_planner_name_emits_warn(self):
        tree = _classic_react_tree()
        tree["agent"]["planner_name"] = None
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("`planner_name` missing", text)


class RenderUnresolvedAndCyclesTests(_RenderTestBase):
    def test_unresolved_renders_dependency_graph(self):
        tree = _classic_react_tree()
        tree["_unresolved"] = [
            {"kind": "FLOW", "api_name": "Missing_Flow",
             "reason": "not-in-org"},
        ]
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("## Dependency graph", text)
        self.assertIn("Missing_Flow", text)
        # Section 8 renders the unresolved row in its table.
        self.assertIn("not-in-org", text)

    def test_cycle_annotation_renders_dotted_back_edge(self):
        tree = _classic_react_tree()
        # Inject a _cycle_back_to annotation on the Find_Public_Articles flow.
        tree["root"]["children"][0]["children"][0]["children"][0][
            "_cycle_back_to"] = "Find_Public_Articles"
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        # Dotted back-edge syntax `-.->` plus the `cycle_back_to:` label.
        self.assertIn("-.->", text)
        self.assertIn("cycle_back_to", text)


class RenderNodeCapTests(_RenderTestBase):
    def _large_tree(self, n_actions: int) -> dict:
        tree = _classic_react_tree()
        # Overwrite the second topic with a fan-out of n_actions children.
        big_topic = {
            "kind": "TOPIC",
            "api_name": "Mega_Topic",
            "children": [
                {
                    "kind": "GEN_AI_FUNCTION",
                    "api_name": f"Action_{i:03d}",
                    "children": [
                        {"kind": "APEX", "api_name": f"ApexClass_{i:03d}"},
                    ],
                }
                for i in range(n_actions)
            ],
        }
        tree["root"]["children"] = [big_topic]
        tree["_kind_counts"] = {
            "BOT_DEFINITION": 1,
            "TOPIC": 1,
            "GEN_AI_FUNCTION": n_actions,
            "APEX": n_actions,
        }
        return tree

    def test_flowchart_cap_exceeded_emits_placeholder(self):
        # 250 actions + 250 apex + 1 topic + 1 bot = 502 nodes > 200 cap.
        tree = self._large_tree(250)
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("[diagram truncated: flowchart", text)
        self.assertIn("exceed cap of 200", text)
        # Top-5 fan-out line present.
        self.assertIn("Top 5 nodes by fan-out", text)
        # Mega_Topic shows up as a top fan-out node.
        self.assertIn("Mega_Topic", text)

    def test_react_30_topics_does_not_false_trip_sequence_cap(self):
        # pre-fix, msg_count was computed as
        # `2 * len(topics) + len(actions) + 2`, which for 30 topics
        # yields 62+ > cap=60. But ReAct only samples topics[:5], so
        # the rendered sequence has ~14 messages — nowhere near the
        # cap. Assert the diagram renders, no truncation placeholder.
        # 2026-05: `_render_invocation_sequence` is no longer wired
        # into `render`; invoke it directly so the cap math stays
        # covered.
        tree = _classic_react_tree()
        topics = [
            {
                "kind": "TOPIC",
                "api_name": f"Topic_{i:02d}",
                "children": [
                    {"kind": "GEN_AI_FUNCTION",
                     "api_name": f"Action_{i:02d}"},
                ],
            }
            for i in range(30)
        ]
        tree["root"]["children"] = topics
        tree["_kind_counts"] = {
            "BOT_DEFINITION": 1, "TOPIC": 30, "GEN_AI_FUNCTION": 30,
        }
        walker = render_architecture._TreeWalker(tree)
        walker.walk()
        rendered = render_architecture._render_invocation_sequence(
            tree, tree["agent"], walker,
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        self.assertNotIn("[diagram truncated: sequenceDiagram", rendered)
        self.assertIn("sequenceDiagram", rendered)
        # Sampling at :5 means exactly 5 topics show up in the messages.
        # Topic_00..Topic_04 must appear; Topic_05 must not.
        self.assertIn("Topic_04", rendered)
        self.assertNotIn("Topic_05", rendered)

    def test_sequence_cap_trips_on_actually_rendered_overflow(self):
        # construct a scenario where the rendered message
        # list truly exceeds the cap. We use a tiny cap (5) rather than
        # fabricating 60+ NGA messages — the test's intent is "cap math
        # is evaluated against the rendered list", not "cap=60 is
        # specifically correct".
        # 2026-05: invoke `_render_invocation_sequence` directly since
        # the section was retired from the default pipeline.
        tree = _classic_react_tree()
        walker = render_architecture._TreeWalker(tree)
        walker.walk()
        caps = dict(render_architecture.DEFAULT_MAX_MERMAID_NODES)
        caps["sequenceDiagram"] = 3
        rendered = render_architecture._render_invocation_sequence(
            tree, tree["agent"], walker, caps,
        )
        self.assertIn("[diagram truncated: sequenceDiagram", rendered)
        self.assertIn("exceed cap of 3", rendered)


class RenderLoadMermaidTests(_RenderTestBase):
    def test_nested_placeholder_in_value_logs_warning(self):
        with self.assertLogs(render_architecture.logger, level="WARNING") as cm:
            out = render_architecture.load_mermaid(
                "invocation_sequence",
                PARTICIPANTS="participant {{NESTED}}",
                MESSAGES="User->>+Planner: x",
            )
        self.assertTrue(any("nested placeholder" in m for m in cm.output))
        # Still renders — the nested token is left as-is (no second pass).
        self.assertIn("{{NESTED}}", out)

    def test_missing_template_raises_filenotfounderror_without_path(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            render_architecture.load_mermaid("nonexistent_template_zzz")
        msg = str(ctx.exception)
        self.assertIn("nonexistent_template_zzz", msg)
        # Hygiene: absolute SKILL_ROOT path must not bleed through.
        self.assertNotIn("/assets/mermaid", msg)

    def test_traversal_name_rejected_without_absolute_path_leak(self):
        # The hygiene contract is that the absolute MERMAID_DIR path
        # must not appear in the error text — echoing the caller's
        # own input back (which here happens to contain `/etc/passwd`)
        # is fine; that's information the caller already had.
        with self.assertRaises(FileNotFoundError) as ctx:
            render_architecture.load_mermaid("../../../etc/passwd")
        msg = str(ctx.exception)
        self.assertNotIn(str(_REPO_MERMAID_DIR), msg)
        # Also must not leak the absolute install path. Asserting the user's
        # home directory doesn't appear is a stricter, runtime-agnostic check
        # than naming any specific install root (.claude / .vibe /
        # plugin-specific layouts).
        self.assertNotIn(str(Path.home()), msg)

    def test_non_string_param_raises_typeerror(self):
        with self.assertRaises(TypeError):
            render_architecture.load_mermaid(
                "invocation_sequence",
                PARTICIPANTS=None,  # type: ignore[arg-type]
                MESSAGES="x",
            )

    def test_leading_comment_block_preserved_but_not_substituted(self):
        # the `%%` header comments in the shipped templates
        # are kept in rendered output (Mermaid ignores `%%` lines at
        # render time). The prior _strip_leading_comment_block workaround
        # was a misdiagnosis — the real bug was templates documenting
        # placeholders as `{{NAME}}` inside `%%` comments, causing
        # load_mermaid's str.replace to substitute them.
        out = render_architecture.load_mermaid(
            "action_tree", SUBGRAPHS="SG_INJECTED", EDGES="EDGES_INJECTED",
        )
        # Header comments survive.
        self.assertTrue(out.startswith("%%"))
        # `%%` lines must not have been corrupted by substitution.
        for ln in out.splitlines():
            if ln.startswith("%%"):
                self.assertNotIn("SG_INJECTED", ln)
                self.assertNotIn("EDGES_INJECTED", ln)
        # Diagram-kind keyword still present on its own bare line.
        self.assertIn("\nflowchart TB", "\n" + out)
        # Placeholders in the body were substituted exactly once.
        self.assertIn("SG_INJECTED", out)
        self.assertIn("EDGES_INJECTED", out)


class RenderEmptyAndSearchTests(_RenderTestBase):
    def test_empty_bot_definition_renders_without_crash(self):
        tree = {
            "_schema_version": "3.0",
            "agent": {
                "api_name": "Empty",
                "version": "v1",
                "generation": "classic",
                "planner_type": "AiCopilot__ReAct",
                "planner_name": "Empty_Planner",
            },
            "root": {"kind": "BOT_DEFINITION", "api_name": "Empty",
                     "children": []},
            "node_count": 1,
            "depth": 0,
            "_partial": False,
            "_unresolved": [],
            "_kind_counts": {"BOT_DEFINITION": 1},
        }
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()
        self.assertIn("_No topics defined", text)
        self.assertIn("_No actions declared._", text)
        self.assertIn("_No backing artifacts in tree._", text)

    def test_search_generation_skips_state_diagram(self):
        # Planner state machine was retired from the default render in
        # 2026-05. Exercise `_render_planner_state` directly to keep the
        # search-generation prose-placeholder branch covered.
        tree = _classic_react_tree()
        tree["agent"]["generation"] = "search"
        tree["agent"]["planner_type"] = "custom_search_Apex"
        rendered = render_architecture._render_planner_state(
            tree["agent"], "search",
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        self.assertIn("Custom planner", rendered)
        self.assertNotIn("stateDiagram-v2", rendered)

    def test_byop_generation_skips_state_diagram(self):
        # Same 2026-05 retirement — exercise the helper directly.
        tree = _classic_react_tree()
        tree["agent"]["generation"] = "byop"
        rendered = render_architecture._render_planner_state(
            tree["agent"], "byop",
            dict(render_architecture.DEFAULT_MAX_MERMAID_NODES),
        )
        self.assertIn("Custom planner", rendered)


class RenderPromptCatalogTests(_RenderTestBase):
    """Section-7 'Prompt templates' sub-section shape.

    Flows and Apex classes each get an H4 per entry with a fenced
    signature block. Prompts were historically rendered as a bare bullet
    list (just names) which left the reader with no indication of what
    each prompt does. We now mirror the flow/apex shape: H4 heading,
    optional `Type:` line, optional signature fence, `_Details not
    captured._` fallback when the walker has no metadata on the node.
    Wave B doesn't yet stamp prompt signatures — the renderer just has
    to be ready for when it does."""

    def _tree_with_prompts(self, prompt_nodes: list[dict]) -> dict:
        """Wrap two prompt nodes under a TOPIC -> GEN_AI_FUNCTION so the
        walker indexes them into `walker.prompts`."""
        tree = _classic_react_tree()
        tree["root"]["children"].append({
            "kind": "TOPIC",
            "api_name": "PromptTopic",
            "children": [
                {
                    "kind": "GEN_AI_FUNCTION",
                    "api_name": "UsePrompts",
                    "children": prompt_nodes,
                },
            ],
        })
        return tree

    def test_prompt_h4_per_entry_with_type_and_fallback(self):
        r"""Two prompts: one with `prompt_type` set, one without. Both
        get H4 headings. The typed one shows ``Type: `flex```; the
        bare one shows `_Details not captured._`."""
        tree = self._tree_with_prompts([
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "DraftReply",
                "prompt_type": "flex",
                "children": [],
            },
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "SummarizeThread",
                "children": [],
            },
        ])
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()

        self.assertIn("### Prompt templates", text)
        # Both prompts render as H4, not as bare bullets.
        self.assertIn("#### `DraftReply`", text)
        self.assertIn("#### `SummarizeThread`", text)
        self.assertNotIn("- `DraftReply`", text)
        self.assertNotIn("- `SummarizeThread`", text)
        # Typed prompt surfaces its Type line.
        self.assertIn("- Type: `flex`", text)
        # Untyped prompt (no signature either) falls back honestly.
        # Locate the SummarizeThread block and confirm its body.
        import re
        m = re.search(
            r"#### `SummarizeThread`\n\n(.*?)(?:\n#### |\n### |\n## |\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m, "SummarizeThread prompt block not found")
        self.assertIn("_Details not captured._", m.group(1))

    def test_prompt_with_signature_renders_fenced_block(self):
        """When a prompt node carries a `signature` (future Wave B
        stamp), the renderer emits it inside a fenced code block, same
        shape used for flows/apex."""
        tree = self._tree_with_prompts([
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "ClassifyIntent",
                "prompt_type": "genAiPromptTemplate",
                "signature": "in: userUtterance: String | out: intent: String",
                "children": [],
            },
        ])
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()

        self.assertIn("#### `ClassifyIntent`", text)
        self.assertIn("- Type: `genAiPromptTemplate`", text)
        # Fenced signature block present.
        self.assertIn(
            "```\nin: userUtterance: String | out: intent: String\n```",
            text,
        )
        # No fallback when we have either type or sig.
        import re
        m = re.search(
            r"#### `ClassifyIntent`\n\n(.*?)(?:\n#### |\n### |\n## |\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m)
        self.assertNotIn("_Details not captured._", m.group(1))


class RenderPromptTemplateBodyTests(_RenderTestBase):
    """Gap C (2026-05-05): prompt template bodies retrieved via
    `retrieve_prompt_templates` are stamped onto PROMPT_TEMPLATE leaves
    as `master_label`, `content`, `inputs`, `_body_available`. The
    renderer emits:
      - `_Label: <master_label>_` blurb
      - `**Inputs**:` bulleted list
      - fenced `text` code block for the content
      - `_Body not retrieved._` when `_body_available` is False and no
        other details are available
    """

    def _tree_with_prompts(self, prompt_nodes: list[dict]) -> dict:
        tree = _classic_react_tree()
        tree["root"]["children"].append({
            "kind": "TOPIC",
            "api_name": "PromptTopic",
            "children": [
                {
                    "kind": "GEN_AI_FUNCTION",
                    "api_name": "UsePrompts",
                    "children": prompt_nodes,
                },
            ],
        })
        return tree

    def test_body_rendered_with_label_inputs_and_fenced_content(self):
        tree = self._tree_with_prompts([
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "AGNT_US_Q_A_with_Site_Scraping",
                "master_label": "AGNT - US Q&A with Site Scraping",
                "content": "# ROLE & OBJECTIVE\nAnswer the customer question.",
                "inputs": [
                    {"name": "Query", "dataType": "String"},
                    {"name": "Site", "dataType": "String"},
                ],
                "_body_available": True,
                "children": [],
            },
        ])
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()

        self.assertIn(
            "#### `AGNT_US_Q_A_with_Site_Scraping`", text,
        )
        self.assertIn("_Label: AGNT - US Q&A with Site Scraping_", text)
        self.assertIn("**Inputs**:", text)
        self.assertIn("- `Query`: `String`", text)
        self.assertIn("- `Site`: `String`", text)
        # Fenced content block uses `text` language hint.
        self.assertIn(
            "```text\n# ROLE & OBJECTIVE\nAnswer the customer question.\n```",
            text,
        )
        self.assertNotIn("_Details not captured._", text)
        self.assertNotIn("_Body not retrieved._", text)

    def test_body_unavailable_falls_back_honestly(self):
        tree = self._tree_with_prompts([
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "MissingTpl",
                "_body_available": False,
                "children": [],
            },
        ])
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()

        self.assertIn("#### `MissingTpl`", text)
        import re
        m = re.search(
            r"#### `MissingTpl`\n\n(.*?)(?:\n#### |\n### |\n## |\Z)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m)
        block = m.group(1)
        self.assertIn("_Body not retrieved._", block)
        # No content fence; no Inputs block.
        self.assertNotIn("```text", block)
        self.assertNotIn("**Inputs**:", block)

    def test_inputs_without_datatype_still_render(self):
        """Older templates may omit <dataType> on <inputs>. Render the
        name alone rather than crashing or dropping the input."""
        tree = self._tree_with_prompts([
            {
                "kind": "PROMPT_TEMPLATE",
                "api_name": "LegacyTpl",
                "content": "body",
                "inputs": [{"name": "Query"}],
                "_body_available": True,
                "children": [],
            },
        ])
        tree_path = _write_tree(self.tmp, tree)
        out = self.tmp / "architecture.md"
        render_architecture.render(tree_path, out)
        text = out.read_text()

        self.assertIn("**Inputs**:", text)
        self.assertIn("- `Query`", text)


if __name__ == "__main__":
    unittest.main()
