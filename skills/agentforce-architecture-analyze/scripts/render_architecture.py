"""Render architecture.md from metadata_tree.json.

Phase 2 Batch 2.2: 8-section architecture document with up to 3 Mermaid
diagrams (2 core + 1 conditional dependency graph). Generation-aware:
classic/ReAct, classic/SequentialPlannerIntentClassifier, NGA/
ConcurrentMultiAgentOrchestration, search/BYOP all produce distinct
structural output on the same fixture schema.

Consumers
---------
- `main.py` phase 10 — called with the finalized tree_path + a target
  out_path under the agent data_dir.
- Tests — `scripts/tests/test_render_architecture.py` exercises every
  per-generation branch and the cap/partial/cycle edge cases.

Template loader
---------------
`load_mermaid(name, **params)` mirrors `soql_loader.load_soql`'s
substitution shape (single-pass `str.replace` on `{{KEY}}` tokens) but
deliberately does NOT run `fs_guard.validate_api_name` on the values.
Mermaid strings are not SQL, not a filesystem path, and not a shell
argument — there is no injection surface downstream. We only guard
against a *substituted* value itself containing `{{` / `}}`, which would
confuse readers of the rendered diff if it silently chained into a
second substitution pass; the loader logs a warning and proceeds.
Template filenames are validated — they flow into a `Path.is_file()`
check on disk, same traversal surface as `load_soql`.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import MERMAID_DIR, SKILL_ROOT, fs_guard  # fs_guard re-exported by config.py from _shared/

logger = logging.getLogger(__name__)

# P2.2-1: per-diagram-type node caps. Above cap -> summary placeholder.
DEFAULT_MAX_MERMAID_NODES: Dict[str, int] = {
    "flowchart": 200,
    "stateDiagram": 40,
    "sequenceDiagram": 60,
    "graph": 100,
}


def _display_name(node: Dict[str, Any]) -> str:
    """Return the node's rendered label.

    For STANDARD_ACTION nodes, append the invocation-type qualifier
    (e.g. `streamKnowledgeSearch (standardinvocableaction)`) so the
    rendered tree distinguishes a real Salesforce-owned builtin from
    a flow-element STANDARD_ACTION whose action-name equals its
    invocation-target. Canonical key is `invocation_type` (schema
    3.1); legacy `raw_invocation_type` / `raw_action_type` fall
    back for caches built by an older parse_wave.
    """
    name = node.get("api_name") or node.get("element_name") or "?"
    if node.get("kind") == "STANDARD_ACTION":
        inv = (
            node.get("invocation_type")
            or node.get("raw_invocation_type")
            or node.get("raw_action_type")
        )
        if inv:
            return f"{name} ({inv})"
    return name


# ---------------------------------------------------------------------------
# Template loader
# ---------------------------------------------------------------------------


def load_mermaid(name: str, **params: str) -> str:
    """Read assets/mermaid/<name>.mmd and substitute {{PARAM}} values.

    P2.2-1: template name is regex-validated BEFORE any filesystem access.
    Traversal via `../../etc/...` is blocked by `fs_guard.validate_api_name`.
    Param *values* are NOT validated — mermaid strings don't flow into
    SOQL, REST, or filesystem paths and carry no injection surface.
    We DO check for nested `{{`/`}}` in substituted values and log a
    warning (the first-pass substitute call won't re-trigger, but a
    stray `{{OTHER}}` inside a value makes the rendered markdown
    confusing to diff). Raises `FileNotFoundError` with the template
    name (no absolute-path leak) when the template file is missing.
    """
    try:
        fs_guard.validate_api_name(name, label="mermaid_template_name")
    except fs_guard.ValidationError as e:
        # Template name is attacker-controlled in theory (a caller could
        # source it from a config file). Don't leak the full SKILL_ROOT
        # via the default FileNotFoundError message.
        raise FileNotFoundError(
            f"Mermaid template name rejected: {e.reason}"
        ) from None

    path = MERMAID_DIR / f"{name}.mmd"
    if not path.is_file():
        # Match soql_loader's SoqlTemplateNotFound hygiene — carry only
        # the template *name*, not the absolute MERMAID_DIR path, so
        # error text surfacing in logs doesn't disclose filesystem layout.
        raise FileNotFoundError(f"Mermaid template not found: {name}")

    template = path.read_text()
    # the `%%` header-comment block in each template is kept
    # verbatim in the rendered output. Mermaid treats `%%` lines as
    # comments and ignores them at render time, and keeping them aids
    # debuggability (rendered diff still carries the author's contract
    # notes). Templates MUST document placeholder names as bare tokens
    # (e.g. `NODES placeholder:`) rather than `{{NODES}}` — otherwise
    # the single-pass `str.replace` below would substitute the comment's
    # placeholder reference and corrupt the header.

    for key, value in params.items():
        if not isinstance(value, str):
            # Fail loud rather than produce a literal 'None' or '[<Node>...]'
            # in the rendered markdown.
            raise TypeError(
                f"Mermaid param {key!r} must be str, got {type(value).__name__}"
            )
        if "{{" in value or "}}" in value:
            # Defensive log; single-pass `str.replace` still renders safely.
            logger.warning(
                "load_mermaid(%s): param %r contains nested placeholder tokens; "
                "rendered output may be confusing",
                name, key,
            )
        template = template.replace(f"{{{{{key}}}}}", value)
    return template.strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render(
    tree_path: Path,
    out_path: Path,
    *,
    max_mermaid_nodes: Optional[Dict[str, int]] = None,
) -> None:
    """Read metadata_tree.json and write architecture.md to out_path.

    The renderer walks the tree once to collect catalog data (topics,
    actions, flows, apex, prompts, unresolved refs, cycles) then emits
    8 sections in document order. Generation-aware branches live at the
    section-level helpers below.

    Note: `_render_invocation_sequence` and `_render_planner_state`
    remain defined and tested but are no longer part of the default
    pipeline (heuristics distrusted by reviewers as of 2026-05).
    Uncomment the relevant `parts.append` calls below to re-enable.
    """
    caps = dict(DEFAULT_MAX_MERMAID_NODES)
    if max_mermaid_nodes:
        caps.update(max_mermaid_nodes)

    tree = json.loads(Path(tree_path).read_text())
    agent = tree.get("agent") or {}
    generation = (agent.get("generation") or "classic").lower()

    walker = _TreeWalker(tree)
    walker.walk()

    parts: List[str] = []
    parts.append(_render_header(tree, agent))
    parts.append(_render_anatomy_summary(tree, walker))
    # parts.append(_render_invocation_sequence(tree, agent, walker, caps))
    # ^ Disabled 2026-05: heuristic over-simplified real orchestration
    # paths. Function + template retained; re-enable by uncommenting.
    parts.append(_render_action_tree(tree, walker, caps))
    parts.append(_render_topic_anatomy(walker))
    parts.append(_render_action_catalog(walker))
    # parts.append(_render_planner_state(agent, generation, caps))
    # ^ Disabled 2026-05: generation-specific state diagram added more
    # noise than signal in review. Function + template retained; re-enable
    # by uncommenting.
    parts.append(_render_data_flow(tree, walker, caps))
    parts.append(_render_artifact_catalogs(walker))
    parts.append(_render_unresolved(tree, walker))

    # Conditional dependency-graph section — emitted only if there are
    # unresolved refs or cycles detected. Not counted as one of the 9.
    if tree.get("_unresolved") or walker.cycles:
        parts.append(_render_dependency_graph(tree, walker, caps))

    Path(out_path).write_text("\n\n".join(parts).rstrip() + "\n")


# ---------------------------------------------------------------------------
# Tree walker — single pass over the tree to collect catalog data
# ---------------------------------------------------------------------------


class _TreeWalker:
    """Collects nodes, edges, topics, cycles in a single depth-first pass.

    P2.2-1: BFS-equivalent visit budget already enforced by parse_wave
    (MAX_BFS_DEPTH=5), so we don't need a depth cap here — the tree is
    already bounded. We DO guard against a malformed tree with a
    self-referential `children` ring by tracking id()'s.
    """

    def __init__(self, tree: Dict[str, Any]) -> None:
        self.tree = tree
        self.topics: List[Dict[str, Any]] = []
        # actions = top-level children of each topic plus planner-level actions
        self.actions: List[Dict[str, Any]] = []
        self.flows: Dict[str, Dict[str, Any]] = {}
        self.apex: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.standard_actions: Dict[str, Dict[str, Any]] = {}
        # tree edges: parent api_name -> list of child api_name
        self.edges: List[Tuple[str, str, str]] = []  # (parent, child, kind)
        # fan-out map for summary-placeholder top-5
        self.fanout: Dict[str, int] = {}
        # cycle-back annotations: list of (node_label, cycle_back_to)
        self.cycles: List[Tuple[str, str]] = []
        # depth-cap truncations (subset of self.cycles surfaced by
        # the unified _truncated annotation with reason="max-depth").
        # Kept separate so downstream renderers can distinguish the two
        # truncation classes without re-walking the tree.
        self.depth_capped: List[Tuple[str, str]] = []
        self._seen_py_ids: set[int] = set()

    def walk(self) -> None:
        root = self.tree.get("root") or {}
        for child in root.get("children") or []:
            self._visit(child, parent_label=root.get("api_name") or "ROOT",
                        topic=None)

    def _visit(
        self,
        node: Dict[str, Any],
        *,
        parent_label: str,
        topic: Optional[Dict[str, Any]],
    ) -> None:
        if not isinstance(node, dict):
            return
        nid = id(node)
        if nid in self._seen_py_ids:
            return
        self._seen_py_ids.add(nid)

        kind = node.get("kind") or "UNKNOWN"
        api_name = node.get("api_name") or node.get("element_name") or ""

        # Top-level children of a BOT_DEFINITION with kind TOPIC feed the
        # topic list. Non-topic top-level children (planner-level actions)
        # attach to a synthetic `_plannerActions` bucket.
        if kind == "TOPIC" and topic is None:
            topic_rec = {
                "api_name": api_name,
                "label": node.get("master_label") or api_name,
                "actions": [],
                "raw": node,
            }
            self.topics.append(topic_rec)
            topic = topic_rec
        elif topic is None and kind == "GEN_AI_FUNCTION":
            # plannerAction (classic Sequential / NGA) — no parent topic.
            self.actions.append({
                "kind": kind,
                "api_name": api_name,
                "topic": None,
                "raw": node,
            })
        elif topic is not None and kind == "GEN_AI_FUNCTION":
            action_rec = {
                "kind": kind,
                "api_name": api_name,
                "topic": topic["api_name"],
                "raw": node,
            }
            topic["actions"].append(action_rec)
            self.actions.append(action_rec)

        # Per-kind catalog buckets. We key on api_name; dupes collapse.
        if kind == "FLOW" and api_name:
            self.flows.setdefault(api_name, node)
        elif kind == "APEX" and api_name:
            self.apex.setdefault(api_name, node)
        elif kind == "PROMPT_TEMPLATE" and api_name:
            self.prompts.setdefault(api_name, node)
        elif kind == "STANDARD_ACTION" and api_name:
            self.standard_actions.setdefault(api_name, node)

        # per-node truncation annotation (cycle OR depth-cap).
        # Prefer the unified `_truncated` sub-object; fall back to the
        # deprecated `_cycle_back_to` string for trees produced by
        # older parse_wave versions.
        trunc = node.get("_truncated") or {}
        cycle_to = trunc.get("target") or node.get("_cycle_back_to")
        reason = trunc.get("reason") or ("cycle" if cycle_to else None)
        if cycle_to:
            self.cycles.append((api_name or parent_label, str(cycle_to)))
            # Optional: downstream renderers may want to distinguish
            # the two truncation classes. We keep that open by stashing
            # `reason` when present.
            if reason and reason != "cycle":
                self.depth_capped.append((api_name or parent_label, str(cycle_to)))

        # Edge + fanout bookkeeping
        children = node.get("children") or []
        if api_name and parent_label and parent_label != api_name:
            self.edges.append((parent_label, api_name, kind))
            self.fanout[parent_label] = self.fanout.get(parent_label, 0) + 1

        for child in children:
            self._visit(child, parent_label=api_name or parent_label,
                        topic=topic)

    # ---- helpers -----------------------------------------------------

    def total_nodes(self) -> int:
        counts = self.tree.get("_kind_counts") or {}
        return sum(counts.values()) or self.tree.get("node_count", 0)

    def top_fanout(self, n: int = 5) -> List[Tuple[str, int]]:
        return sorted(self.fanout.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _md_escape(value: Any) -> str:
    if value is None:
        return "-"
    s = str(value)
    # Escape the two characters that break markdown tables.
    return s.replace("|", r"\|").replace("\n", " ")


def _render_header(tree: Dict[str, Any], agent: Dict[str, Any]) -> str:
    # P2.2-1: section 1 — kv table. No input is trusted (agent fields
    # come from SOQL + metadata retrieve), but we escape pipes anyway.
    lines = ["# Architecture — `{}` `{}`".format(
        _md_escape(agent.get("api_name") or "?"),
        _md_escape(agent.get("version") or "?"),
    )]
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    rows = [
        ("Master label", agent.get("master_label")),
        ("Description", agent.get("description")),
        ("Agent type", agent.get("agent_type")),
        ("Type", agent.get("type")),
        ("Template", agent.get("agent_template")),
        ("Bot source", agent.get("bot_source")),
        ("Generation", agent.get("generation")),
        ("Planner name", agent.get("planner_name")),
        ("Planner type", agent.get("planner_type")),
        ("Bot id", agent.get("bot_id")),
        ("Schema version", tree.get("_schema_version")),
    ]
    for label, value in rows:
        lines.append(f"| {label} | {_md_escape(value)} |")
    return "\n".join(lines)


def _render_anatomy_summary(tree: Dict[str, Any], walker: _TreeWalker) -> str:
    # P2.2-1: section 2 renders health callout when _partial=true.
    kc = tree.get("_kind_counts") or {}
    lines = ["## 2. Anatomy summary", ""]
    topic_count = kc.get("TOPIC", len(walker.topics))
    action_count = kc.get("GEN_AI_FUNCTION", len(walker.actions))
    flow_count = kc.get("FLOW", len(walker.flows))
    apex_count = kc.get("APEX", len(walker.apex))
    prompt_count = kc.get("PROMPT_TEMPLATE", len(walker.prompts))
    stdaction_count = kc.get("STANDARD_ACTION", len(walker.standard_actions))

    lines.append(
        "Agent exposes **{} topics** and **{} declared actions** "
        "spanning **{} flows**, **{} apex classes**, **{} prompt templates**, "
        "and **{} standard actions**. Tree depth is {} across {} total nodes.".format(
            topic_count, action_count, flow_count, apex_count,
            prompt_count, stdaction_count,
            tree.get("depth", "?"), walker.total_nodes(),
        )
    )

    if tree.get("_partial"):
        pending = tree.get("_pending_fetches") or {}
        pending_count = sum(len(v) for v in pending.values())
        reason = tree.get("_partial_reason") or "unspecified"
        lines.append("")
        lines.append("> **Health: PARTIAL.** The tree did not fully converge.")
        lines.append(f"> - Reason: `{_md_escape(reason)}`")
        lines.append(f"> - Pending fetches: {pending_count}")
        if pending:
            for key, items in pending.items():
                if items:
                    lines.append(
                        f">   - `{_md_escape(key)}`: {len(items)} outstanding"
                    )

    # P2.2-1: health callout when planner_name is missing.
    agent = tree.get("agent") or {}
    if not agent.get("planner_name"):
        lines.append("")
        lines.append(
            "> **Health: WARN.** `planner_name` missing from agent metadata — "
            "downstream sections render best-effort from tree shape alone."
        )

    if tree.get("_unresolved"):
        lines.append("")
        lines.append(
            "> **Health: WARN.** {} unresolved references — see section 8.".format(
                len(tree["_unresolved"])
            )
        )

    return "\n".join(lines)


def _render_invocation_sequence(
    tree: Dict[str, Any],
    agent: Dict[str, Any],
    walker: _TreeWalker,
    caps: Dict[str, int],
) -> str:
    # P2.2-1: section 3 — sequenceDiagram with cap check.
    lines = ["## 3. Invocation sequence", ""]
    generation = (agent.get("generation") or "classic").lower()

    participants = ["participant User", "    participant Planner"]
    if generation == "nga":
        participants.append("    participant Orchestrator")
        participants.append("    participant SubAgent")
    else:
        participants.append("    participant TopicClassifier")
    participants.append("    participant ActionExecutor")

    messages: List[str] = []
    messages.append("    User->>+Planner: utterance")
    if generation == "nga":
        messages.append("    Planner->>+Orchestrator: plan")
        messages.append("    Orchestrator->>+SubAgent: dispatch (par/and)")
        messages.append("    SubAgent->>+ActionExecutor: invoke action")
        messages.append("    ActionExecutor-->>-SubAgent: result")
        messages.append("    SubAgent-->>-Orchestrator: subresult")
        messages.append("    Orchestrator-->>-Planner: aggregated")
    elif (agent.get("planner_type") or "").endswith("SequentialPlannerIntentClassifier"):
        messages.append("    Planner->>+ActionExecutor: direct intent->action")
        messages.append("    ActionExecutor-->>-Planner: result")
    else:
        # Classic ReAct — one round-trip per topic (sampled at :5 for
        # readability). The cap check below counts the ACTUAL rendered
        # messages, so a 30-topic bot whose ReAct branch only emits 12
        # lines is correctly NOT truncated.
        for topic in walker.topics[:5]:  # sample for readability
            label = _md_escape(topic["api_name"])
            messages.append(f"    Planner->>+TopicClassifier: classify → {label}")
            messages.append(f"    TopicClassifier-->>-Planner: topic={label}")
        messages.append("    Planner->>+ActionExecutor: invoke action")
        messages.append("    ActionExecutor-->>-Planner: result")

    messages.append("    Planner-->>-User: response")

    # cap against ACTUAL rendered message count, not a
    # potential / over-estimated figure. The prior implementation used
    # `2 * len(walker.topics) + len(walker.actions) + 2`, which false-
    # tripped on large bots because the ReAct branch only emits
    # `2 * min(len(walker.topics), 5) + 2` lines (topics[:5] sampling).
    # The rendered-list length is the single source of truth.
    msg_count = len(messages)
    if msg_count > caps.get("sequenceDiagram", 60):
        lines.append(_truncation_placeholder(
            kind="sequenceDiagram", total=msg_count,
            cap=caps["sequenceDiagram"],
            top_fanout=walker.top_fanout(5),
            catalog_pointer="section 5 (action catalog)",
        ))
        return "\n".join(lines)

    rendered = load_mermaid(
        "invocation_sequence",
        PARTICIPANTS="\n".join(participants).lstrip(),
        MESSAGES="\n".join(messages).lstrip(),
    )
    lines.append("```mermaid")
    lines.append(rendered)
    lines.append("```")
    return "\n".join(lines)


def _render_action_tree(
    tree: Dict[str, Any],
    walker: _TreeWalker,
    caps: Dict[str, int],
) -> str:
    # P2.2-1: section 3 — flowchart + subgraphs per topic; cycle back-edges.
    lines = ["## 3. Action tree", ""]
    total_nodes = walker.total_nodes()
    if total_nodes > caps.get("flowchart", 200):
        lines.append(_truncation_placeholder(
            kind="flowchart", total=total_nodes,
            cap=caps["flowchart"],
            top_fanout=walker.top_fanout(5),
            catalog_pointer="section 5 (action catalog) and section 7 (artifact catalogs)",
        ))
        lines.append("")
        lines.append(_render_action_tree_ascii(walker))
        return "\n".join(lines)

    # Build subgraphs and edges
    subgraphs: List[str] = []
    for topic in walker.topics:
        sg_id = _safe_id(topic["api_name"])
        sg_lines = [f"    subgraph {sg_id}[\"{_md_escape(topic['label'])}\"]"]
        for action in topic["actions"]:
            node_id = _safe_id(action["api_name"])
            label = _display_name(action.get("raw") or action)
            sg_lines.append(f"        {node_id}[\"{_md_escape(label)}\"]")
        sg_lines.append("    end")
        subgraphs.append("\n".join(sg_lines))

    # Planner-level actions (no topic)
    planner_actions = [a for a in walker.actions if a.get("topic") is None]
    if planner_actions:
        sg_lines = ["    subgraph _plannerActions[\"(plannerActions)\"]"]
        for action in planner_actions:
            node_id = _safe_id(action["api_name"])
            label = _display_name(action.get("raw") or action)
            sg_lines.append(f"        {node_id}[\"{_md_escape(label)}\"]")
        sg_lines.append("    end")
        subgraphs.append("\n".join(sg_lines))

    edges: List[str] = []
    for parent, child, kind in walker.edges:
        pid = _safe_id(parent)
        cid = _safe_id(child)
        edges.append(f"    {pid} --> {cid}")

    # Cycle back-edges (dotted)
    for node_label, cycle_to in walker.cycles:
        nid = _safe_id(node_label)
        tid = _safe_id(cycle_to)
        edges.append(f"    {nid} -.->|cycle_back_to: {_md_escape(cycle_to)}| {tid}")

    rendered = load_mermaid(
        "action_tree",
        SUBGRAPHS="\n\n".join(subgraphs).lstrip() if subgraphs else "%% no topics",
        EDGES="\n".join(edges).lstrip() if edges else "%% no edges",
    )
    lines.append("```mermaid")
    lines.append(rendered)
    lines.append("```")
    lines.append("")
    lines.append("**ASCII appendix**")
    lines.append("")
    lines.append("```")
    lines.append(_render_action_tree_ascii(walker))
    lines.append("```")
    return "\n".join(lines)


def _render_action_tree_ascii(walker: _TreeWalker) -> str:
    out: List[str] = []
    root = walker.tree.get("root") or {}
    out.append(f"{root.get('api_name', 'ROOT')} ({root.get('kind', 'BOT_DEFINITION')})")
    _ascii_recurse(root.get("children") or [], out, depth=1, seen=set())
    return "\n".join(out)


def _ascii_recurse(
    children: List[Dict[str, Any]],
    out: List[str],
    depth: int,
    seen: set[int],
) -> None:
    for child in children:
        if not isinstance(child, dict):
            continue
        nid = id(child)
        if nid in seen:
            continue
        seen.add(nid)
        name = _display_name(child)
        kind = child.get("kind") or "?"
        # surface BOTH cycle AND max-depth truncation in the ASCII
        # tree view. Prefer `_truncated["reason"]`; fall back to the
        # legacy `_cycle_back_to` string (older parse_wave output).
        trunc = child.get("_truncated") or {}
        if trunc.get("reason") == "max-depth":
            marker = " [depth-capped]"
        elif trunc.get("reason") == "cycle" or child.get("_cycle_back_to"):
            marker = " [cycle]"
        else:
            marker = ""
        out.append(f"{'  ' * depth}├── [{kind}] {name}{marker}")
        grand = child.get("children") or []
        if grand:
            _ascii_recurse(grand, out, depth + 1, seen)


def _render_topic_anatomy(walker: _TreeWalker) -> str:
    # P2.2-1: section 4 — H3 per topic + kv list. Empty-case: 0 topics is
    # valid for SequentialPlannerIntentClassifier.
    lines = ["## 4. Topic anatomy", ""]
    if not walker.topics:
        lines.append("_No topics defined (planner exposes actions directly)._")
        return "\n".join(lines)
    for topic in walker.topics:
        lines.append(f"### `{_md_escape(topic['api_name'])}`")
        lines.append("")
        lines.append(f"- Label: {_md_escape(topic['label'])}")
        lines.append(f"- Action count: {len(topic['actions'])}")
        if topic["actions"]:
            lines.append("- Actions:")
            for action in topic["actions"]:
                label = _display_name(action.get("raw") or action)
                lines.append(f"  - `{_md_escape(label)}`")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_action_catalog(walker: _TreeWalker) -> str:
    # P2.2-1: section 5 — markdown table of actions.
    lines = ["## 5. Action catalog", ""]
    if not walker.actions:
        lines.append("_No actions declared._")
        return "\n".join(lines)
    lines.append("| Action | Topic | Unwraps to |")
    lines.append("|---|---|---|")
    for action in walker.actions:
        raw = action.get("raw") or {}
        unwrap = raw.get("unwraps_to") or {}
        unwrap_str = "-"
        if unwrap:
            unwrap_str = "{} `{}`".format(
                unwrap.get("kind", "?"),
                _display_name(unwrap),
            )
        lines.append("| `{}` | {} | {} |".format(
            _md_escape(action["api_name"]),
            _md_escape(action.get("topic") or "(plannerAction)"),
            _md_escape(unwrap_str),
        ))
    return "\n".join(lines)


def _planner_state_for_generation(
    agent: Dict[str, Any], generation: str,
) -> Tuple[List[str], List[str]]:
    """Return (states, transitions) for the planner state machine."""
    planner_type = (agent.get("planner_type") or "").lower()
    if generation == "nga":
        states = [
            "[*] --> Planning",
            "    state Planning",
            "    state Orchestration {",
            "        direction LR",
            "        [*] --> Dispatch",
            "        Dispatch --> SubAgentA",
            "        Dispatch --> SubAgentB",
            "        --",
            "        SubAgentA --> Aggregate",
            "        SubAgentB --> Aggregate",
            "    }",
            "    state Respond",
        ]
        transitions = [
            "    Planning --> Orchestration: par/and dispatch",
            "    Orchestration --> Respond: aggregated",
            "    Respond --> [*]",
        ]
        return states, transitions
    if planner_type.endswith("sequentialplannerintentclassifier"):
        states = [
            "[*] --> Classify",
            "    state Classify",
            "    state Execute",
            "    state Respond",
        ]
        transitions = [
            "    Classify --> Execute: intent",
            "    Execute --> Respond: result",
            "    Respond --> [*]",
        ]
        return states, transitions
    # Default: classic ReAct
    states = [
        "[*] --> Thought",
        "    state Thought",
        "    state Action",
        "    state Observation",
        "    state Respond",
    ]
    transitions = [
        "    Thought --> Action: pick tool",
        "    Action --> Observation: tool result",
        "    Observation --> Thought: more reasoning",
        "    Observation --> Respond: done",
        "    Respond --> [*]",
    ]
    return states, transitions


def _render_planner_state(
    agent: Dict[str, Any],
    generation: str,
    caps: Dict[str, int],
) -> str:
    # P2.2-1: section 6 — stateDiagram-v2 with generation-aware branches.
    lines = ["## 6. Planner state machine", ""]

    if generation in ("search", "byop"):
        lines.append(
            "_Custom planner — structure depends on the planner's Apex class_ "
            f"(`{_md_escape(agent.get('planner_type') or '?')}`). State "
            "diagram skipped; see section 7 for the backing Apex class body."
        )
        return "\n".join(lines)

    states, transitions = _planner_state_for_generation(agent, generation)
    total = len(states) + len(transitions)
    if total > caps.get("stateDiagram", 40):
        lines.append(_truncation_placeholder(
            kind="stateDiagram", total=total,
            cap=caps["stateDiagram"],
            top_fanout=[],
            catalog_pointer="section 7 (artifact catalogs)",
        ))
        return "\n".join(lines)

    rendered = load_mermaid(
        "planner_state",
        STATES="\n".join(states).lstrip(),
        TRANSITIONS="\n".join(transitions).lstrip(),
    )
    lines.append("```mermaid")
    lines.append(rendered)
    lines.append("```")
    return "\n".join(lines)


def _render_data_flow(
    tree: Dict[str, Any],
    walker: _TreeWalker,
    caps: Dict[str, int],
) -> str:
    # P2.2-1: section 6 — flowchart LR with labeled param edges.
    lines = ["## 6. Data flow / context propagation", ""]

    # Build node list — User, Planner, each topic, each action.
    nodes: List[str] = ["    User([User utterance])", "    Planner[Planner]"]
    for topic in walker.topics:
        nodes.append(f"    {_safe_id(topic['api_name'])}[Topic: {_md_escape(topic['api_name'])}]")

    edges: List[str] = ["    User --> Planner"]
    for topic in walker.topics:
        edges.append(f"    Planner --> {_safe_id(topic['api_name'])}")
        for action in topic["actions"]:
            label = _display_name(action.get("raw") or action)
            nodes.append(
                f"    {_safe_id(action['api_name'])}[[Action: {_md_escape(label)}]]"
            )
            # Labeled edge when the planner attr metadata declares a
            # parameter hand-off; fall back to a bare edge otherwise.
            attr = (action.get("raw") or {}).get("planner_attr") or {}
            var_name = attr.get("variable_name") or attr.get("name")
            var_type = attr.get("data_type") or attr.get("type")
            if var_name:
                label = _md_escape(var_name)
                if var_type:
                    label = f"{label}: {_md_escape(var_type)}"
                edges.append(
                    f"    {_safe_id(topic['api_name'])} -->|{label}| "
                    f"{_safe_id(action['api_name'])}"
                )
            else:
                edges.append(
                    f"    {_safe_id(topic['api_name'])} --> "
                    f"{_safe_id(action['api_name'])}"
                )

    total = len(nodes) + len(edges)
    if total > caps.get("flowchart", 200):
        lines.append(_truncation_placeholder(
            kind="flowchart", total=total,
            cap=caps["flowchart"],
            top_fanout=walker.top_fanout(5),
            catalog_pointer="section 7 (artifact catalogs)",
        ))
        return "\n".join(lines)

    rendered = load_mermaid(
        "data_flow",
        NODES="\n".join(nodes).lstrip(),
        EDGES="\n".join(edges).lstrip(),
    )
    lines.append("```mermaid")
    lines.append(rendered)
    lines.append("```")
    return "\n".join(lines)


def _render_artifact_catalogs(walker: _TreeWalker) -> str:
    # P2.2-1: section 7 — H3 per flow / apex / prompt + signature.
    lines = ["## 7. Flow / Apex / Prompt catalogs", ""]

    if walker.flows:
        lines.append("### Flows")
        lines.append("")
        for name in sorted(walker.flows):
            node = walker.flows[name]
            sig = node.get("signature") or node.get("_signature")
            # Gap 2 fix (2026-05-05): main._stamp_signatures stamps
            # `_signature_reason` on flows whose body we can't retrieve
            # (managed package, no active version, metadata fetch miss).
            # Surface the reason so the rendered markdown distinguishes
            # a known limitation from a silent hole.
            reason = node.get("_signature_reason")
            lines.append(f"#### `{_md_escape(name)}`")
            lines.append("")
            if sig:
                lines.append("```")
                lines.append(str(sig))
                lines.append("```")
            elif reason:
                lines.append(f"_Signature not captured — {_md_escape(reason)}._")
            else:
                lines.append("_Signature not captured._")
            lines.append("")

    if walker.apex:
        lines.append("### Apex classes")
        lines.append("")
        for name in sorted(walker.apex):
            node = walker.apex[name]
            sig = node.get("signature") or node.get("_signature")
            lines.append(f"#### `{_md_escape(name)}`")
            lines.append("")
            if sig:
                lines.append("```")
                lines.append(str(sig))
                lines.append("```")
            else:
                lines.append("_Signature not captured._")
            lines.append("")

    if walker.prompts:
        lines.append("### Prompt templates")
        lines.append("")
        for name in sorted(walker.prompts):
            node = walker.prompts[name]
            sig = node.get("signature") or node.get("_signature")
            prompt_type = node.get("prompt_type")
            # Gap C (2026-05-05): retrieve_prompt_templates stamps
            # master_label / content / inputs / _body_available onto
            # each PROMPT_TEMPLATE leaf. Emit the real body when
            # available; fall back to the stub only when `_body_available`
            # is explicitly False (retrieve failed / not requested) AND
            # there's no signature/type to show.
            master_label = node.get("master_label")
            content = node.get("content")
            inputs = node.get("inputs") or []
            body_available = node.get("_body_available")
            lines.append(f"#### `{_md_escape(name)}`")
            lines.append("")
            if master_label:
                lines.append(f"_Label: {_md_escape(master_label)}_")
                lines.append("")
            if prompt_type:
                lines.append(f"- Type: `{_md_escape(prompt_type)}`")
            if inputs:
                lines.append("**Inputs**:")
                for inp in inputs:
                    if not isinstance(inp, dict):
                        continue
                    iname = inp.get("name") or "?"
                    itype = inp.get("dataType")
                    if itype:
                        lines.append(
                            f"- `{_md_escape(iname)}`: "
                            f"`{_md_escape(itype)}`"
                        )
                    else:
                        lines.append(f"- `{_md_escape(iname)}`")
                lines.append("")
            if content:
                lines.append("```text")
                lines.append(str(content))
                lines.append("```")
            elif sig:
                lines.append("```")
                lines.append(str(sig))
                lines.append("```")
            if (
                not content and not sig and not prompt_type
                and not master_label and not inputs
            ):
                if body_available is False:
                    lines.append("_Body not retrieved._")
                else:
                    lines.append("_Details not captured._")
            lines.append("")

    if not (walker.flows or walker.apex or walker.prompts):
        lines.append("_No backing artifacts in tree._")

    return "\n".join(lines).rstrip()


def _render_unresolved(tree: Dict[str, Any], walker: _TreeWalker) -> str:
    # P2.2-1: section 8 — unresolved refs + artifact pointers.
    lines = ["## 8. Unresolved refs + artifact pointers", ""]
    unresolved = tree.get("_unresolved") or []
    if unresolved:
        lines.append("> **{} unresolved refs.**".format(len(unresolved)))
        lines.append("")
        lines.append("| Kind | Api name | Reason |")
        lines.append("|---|---|---|")
        for ref in unresolved:
            lines.append("| {} | `{}` | {} |".format(
                _md_escape(ref.get("kind") or "?"),
                _md_escape(ref.get("api_name") or "?"),
                _md_escape(ref.get("reason") or "?"),
            ))
    else:
        lines.append("_No unresolved references._")
    lines.append("")
    lines.append("### Artifact pointers")
    lines.append("")
    lines.append(
        "- Full tree JSON: same directory as this file (`metadata_tree.json`)"
    )
    lines.append("- Build manifest: cache dir / `manifest.json`")
    return "\n".join(lines)


def _render_dependency_graph(
    tree: Dict[str, Any],
    walker: _TreeWalker,
    caps: Dict[str, int],
) -> str:
    # P2.2-1: conditional — render only on unresolved or cycles.
    lines = ["## Dependency graph (conditional)", ""]
    unresolved = tree.get("_unresolved") or []

    nodes: List[str] = []
    edges: List[str] = []
    seen: set[str] = set()

    def add_node(label: str, unresolved_flag: bool) -> None:
        nid = _safe_id(label)
        if nid in seen:
            return
        seen.add(nid)
        suffix = ":::unresolved" if unresolved_flag else ""
        nodes.append(f"    {nid}[{_md_escape(label)}]{suffix}")

    for parent, child, _ in walker.edges:
        add_node(parent, False)
        add_node(child, False)
        edges.append(f"    {_safe_id(parent)} --> {_safe_id(child)}")

    for ref in unresolved:
        name = ref.get("api_name") or "?"
        add_node(name, True)

    for node_label, cycle_to in walker.cycles:
        add_node(node_label, False)
        add_node(cycle_to, False)
        edges.append(
            f"    {_safe_id(node_label)} -.->|cycle| {_safe_id(cycle_to)}"
        )

    total = len(nodes)
    if total > caps.get("graph", 100):
        lines.append(_truncation_placeholder(
            kind="graph", total=total,
            cap=caps["graph"],
            top_fanout=walker.top_fanout(5),
            catalog_pointer="section 8 (unresolved refs)",
        ))
        return "\n".join(lines)

    rendered = load_mermaid(
        "dependency_graph",
        NODES="\n".join(nodes).lstrip() if nodes else "%% no nodes",
        EDGES="\n".join(edges).lstrip() if edges else "%% no edges",
    )
    lines.append("```mermaid")
    lines.append(rendered)
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncation_placeholder(
    *,
    kind: str,
    total: int,
    cap: int,
    top_fanout: List[Tuple[str, int]],
    catalog_pointer: str,
) -> str:
    # P2.2-1: explicit visual placeholder. Mentions the diagram kind, the
    # over-cap count, and points at the catalog section.
    lines = [
        f"> **[diagram truncated: {kind} — {total} elements exceed cap of {cap}]**",
    ]
    if top_fanout:
        lines.append(">")
        lines.append("> Top 5 nodes by fan-out:")
        for name, count in top_fanout:
            lines.append(f"> - `{_md_escape(name)}` ({count})")
    lines.append(">")
    lines.append(f"> See {catalog_pointer} for the full listing.")
    return "\n".join(lines)


def _safe_id(value: str) -> str:
    """Return a mermaid-safe identifier. Mermaid node ids must be
    alphanumeric + underscore; anything else breaks the parser."""
    if not value:
        return "n_empty"
    out = []
    for ch in str(value):
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    # Prefix digit-leading ids so they don't collide with mermaid syntax.
    result = "".join(out)
    if result and result[0].isdigit():
        result = f"n_{result}"
    return result or "n_empty"
