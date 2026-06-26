#!/usr/bin/env python3
"""Idempotent wave parser — builds `$WORK_DIR/declared_action_tree.json`.

Replaces old agent Phase 4 (wave-2 init) + Phase 5/6 re-parse + MAX_WAVE cap.
One script, one code path. The "init vs re-parse" distinction is keyed on the
presence of `declared_action_tree.json` at call time.

Flow:
  1. Load bundle JSON, bot_definition JSON, existing tree (if any).
  2. Walk every $WORK_DIR/sf_meta/*/unpackaged/ dir:
     - flows/*.flow: parse actionCalls → APEX/PROMPT_TEMPLATE/STANDARD_ACTION/
       UNKNOWN children; subflows → FLOW children. Record flow_children[flow_name].
       Mark ("FLOW", flow_name) visited.
     - classes/*.cls-meta.xml: mark ("APEX", name) visited.
     - genAiPromptTemplates/*.genAiPromptTemplate: mark ("PROMPT_TEMPLATE", name).
  3. Build tree if missing (Phase-4 init):
     - agent metadata from bot_definition + bundle
     - root BOT_DEFINITION node with children = topics[] only
       (plannerActions[] retained in the bundle shape for back-compat but
       always empty — a planner never has direct functions, 2026-05-05)
     - each topic → TOPIC node with GEN_AI_FUNCTION children (from inline actions)
     - each GEN_AI_FUNCTION → unwraps_to + leaf child (Flow/Apex/Prompt/Std/Unk)
  4. Inflate every FLOW leaf recursively (depth ≤ 6) with flow_children data.
  5. Recompute `_pending_fetches` (names not yet in visited set).
  6. Walk tree for `node_count`, `depth`, `_kind_counts`.
  7. Atomic write.

With --finalize-cap: after loading tree, move all remaining _pending_fetches
items to _unresolved[] with reason "max-wave-depth exceeded".

Usage:
    python3 parse_wave.py                  # init or re-parse
    python3 parse_wave.py --finalize-cap   # drain _pending_fetches → _unresolved

Inputs (env):
    WORK_DIR, AGENT_API_NAME, AGENT_VERSION, BOT_ID, BOT_MASTER_LABEL,
    VERSION_AUTO_PICKED

Outputs:
    $WORK_DIR/declared_action_tree.json (atomic write)
    stderr: log lines (node counts, pending counts, etc.)
    exit 0 on success, 1 on write failure
"""
import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET
from collections import Counter


NS = {"sf": "http://soap.sforce.com/2006/04/metadata"}


def _t(el, p):
    if el is None:
        return None
    x = el.find(p, NS)
    return x.text if x is not None else None


def classify_bundle_action(action: dict) -> dict:
    """Bundle-action classifier — duplicated in plan_wave.py per 'no
    intra-skill imports' convention. Matches old agent's Phase 3/4 logic.

    Returns (unwraps_dict, leaf_dict) as in the old agent Phase 4's
    action_node(). leaf_dict is the child appended under the GEN_AI_FUNCTION
    node; unwraps_dict is the compact form stored on the function itself.
    """
    tgt = action.get("invocationTarget")
    ttype = (action.get("invocationTargetType") or "").lower()
    if not tgt:
        return None, None
    if ttype == "flow":
        return ({"kind": "FLOW", "api_name": tgt},
                {"kind": "FLOW", "api_name": tgt, "children": []})
    if ttype == "apex":
        return ({"kind": "APEX", "api_name": tgt},
                {"kind": "APEX", "api_name": tgt})
    if ttype == "generatepromptresponse" or ttype.startswith("prompt") or ttype.startswith("genai"):
        return ({"kind": "PROMPT_TEMPLATE", "api_name": tgt},
                {"kind": "PROMPT_TEMPLATE", "api_name": tgt})
    # Canonical field name is `invocation_type` (schema 3.1). Prior
    # versions wrote `raw_invocation_type` on bundle-sourced nodes and
    # `raw_action_type` on flow-actionCall-sourced nodes — downstream
    # readers (render_architecture._display_name, summarize_tree) fall
    # back to both legacy keys for one release.
    if ttype == "standardinvocableaction":
        return ({"kind": "STANDARD_ACTION", "api_name": tgt, "invocation_type": ttype},
                {"kind": "STANDARD_ACTION", "api_name": tgt, "invocation_type": ttype})
    return ({"kind": "UNKNOWN", "api_name": tgt, "invocation_type": ttype},
            {"kind": "UNKNOWN", "api_name": tgt, "invocation_type": ttype})


def classify_action_call(at: str, an: str, element_name: str) -> dict:
    """Flow actionCall classifier (old Phase 4 logic).

    Canonical field name is `invocation_type` (schema 3.1). Legacy readers
    still fall back to `raw_action_type` for one release.
    """
    at = at or ""
    if at == "apex" and an:
        return {"kind": "APEX", "element_name": element_name, "api_name": an}
    if at == "generatePromptResponse" and an:
        return {"kind": "PROMPT_TEMPLATE", "element_name": element_name, "api_name": an}
    if at:
        # Any other non-empty actionType → STANDARD_ACTION; preserve raw.
        return {"kind": "STANDARD_ACTION", "element_name": element_name,
                "api_name": an or at, "invocation_type": at}
    return {"kind": "UNKNOWN", "element_name": element_name,
            "api_name": an or "?", "invocation_type": at or ""}


# ---------------------------------------------------------------------------
# pure BFS step helper. Visited sets are tuple-keyed on
# (kind, canonical_name). Pending is a dict-by-kind so cross-kind collisions
# (Flow Foo vs Apex Foo) stay distinct.
#
# this is the single source of truth for wave-level BFS. Both
# `harvest_waves` and `main()` route through here so the tuple-keyed
# semantics are active on the production path — not just under unit tests.
#
# kind tokens match the runtime tree's `kind` field
# (FLOW/APEX/PROMPT_TEMPLATE/STANDARD_ACTION). The persisted
# `_pending_fetches` dict uses the SAME tokens so internal + on-disk
# conventions don't diverge.
#
# promoted from `_BFS_KINDS` → `BFS_KINDS` so
# cross-module callers (main.py's in-process orchestrator) import a stable
# public symbol instead of reaching across a leading-underscore boundary.
# Same pattern as rest_client.redact_text's promotion. The underscore
# alias below is retained for backwards compatibility and will be removed
# in the next minor version; new code MUST use `BFS_KINDS`.
# unified node-truncation annotation. When a node is not fully
# expanded (either because of a cycle back to an ancestor, or because the
# MAX_BFS_DEPTH cap tripped), we annotate it with a `_truncated` sub-
# object of shape `{"reason": <str>, "target": <str>}`. `reason` is one
# of the values below; `target` is a `"KIND:name"` path pointing at the
# first encounter (cycle) or the unreached leaf (depth-cap). Downstream
# consumers check `_truncated["reason"]` once; no per-reason pattern
# matching.
#
# Backcompat: `_cycle_back_to` is emitted alongside `_truncated` for any
# consumer that hasn't migrated (render_architecture, summarize_tree,
# third-party tooling). Will be removed in the next minor version.
TRUNCATION_CYCLE = "cycle"
TRUNCATION_MAX_DEPTH = "max-depth"
TRUNCATION_REASONS = frozenset({TRUNCATION_CYCLE, TRUNCATION_MAX_DEPTH})


BFS_KINDS = ("FLOW", "APEX", "PROMPT_TEMPLATE", "STANDARD_ACTION")

# STANDARD_ACTION is a Salesforce-owned builtin (e.g.
# `streamKnowledgeSearch`, `createRecord`, `sendEmail`). These are never
# fetched — they're declared-only leaves, with the action name carrying
# all the identity. Keeping STANDARD_ACTION in BFS_KINDS lets the tree's
# _kind_counts tally include them and visited-bookkeeping dedup against
# them, but they must never accumulate into `_pending_fetches`. A name
# like `streamKnowledgeSearch` landing in _pending_fetches.STANDARD_ACTION
# is pollution — the pipeline isn't "missing" anything; the action is
# simply declared and never materialized.
#
# Callers: when collecting refs into `new_refs`, gate on FETCHABLE_KINDS
# rather than BFS_KINDS to avoid polluting pending buckets with leaves.
FETCHABLE_KINDS = ("FLOW", "APEX", "PROMPT_TEMPLATE")

# deprecated alias. Retained so existing tests and any lingering
# `from parse_wave import _BFS_KINDS` imports keep working. New code MUST
# use `BFS_KINDS` (public). Planned removal in the next minor version.
_BFS_KINDS = BFS_KINDS


def bfs_step(
    pending_by_kind: dict[str, set[str]],
    visited_by_kind: dict[str, set[str]],
    new_refs_by_kind: dict[str, set[str]],
) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    """Advance one BFS wave. Returns (new_pending_by_kind, cycles).

    `cycles` is a list of (kind, name) tuples for refs that were already
    visited on this wave — callers use these to annotate `_cycle_back_to`.

    Self-cycles (a ref pointing at something already visited) are filtered
    out of pending. Cross-type tuples (Flow Foo + Apex Foo) are distinct —
    both land in their respective pending buckets.

    unknown kinds RAISE — this is an internal API; a typo in a caller
    is a programming error, not a recoverable runtime condition. Silent drop
    produced false confidence (the dropped ref never got fetched and no log
    ever mentioned it). Callers must filter to `BFS_KINDS` upstream.
    """
    new_pending: dict[str, set[str]] = {k: set() for k in BFS_KINDS}
    cycles: list[tuple[str, str]] = []
    for kind, refs in new_refs_by_kind.items():
        if kind not in BFS_KINDS:
            raise ValueError(
                f"unknown BFS kind {kind!r}; must be one of {sorted(BFS_KINDS)}"
            )
        visited = visited_by_kind.get(kind, set())
        for name in refs:
            if name in visited:
                cycles.append((kind, name))
                continue
            # Not yet visited AND not already pending on a prior wave:
            # OR-in unconditionally — `pending |= (new - visited)` semantics.
            new_pending[kind].add(name)
    # Merge with the caller's existing pending. Caller passes the authoritative
    # pending buckets; we return the delta merged in so they can just replace.
    merged: dict[str, set[str]] = {k: set(pending_by_kind.get(k, set())) for k in BFS_KINDS}
    for kind, names in new_pending.items():
        merged[kind] |= names
    return merged, cycles


def empty_kind_sets() -> dict[str, set[str]]:
    """Build a fresh {kind: set()} dict covering every BFS_KINDS entry.

    callers use this to seed per-kind visited / pending
    buckets. Keeping it centralized means new kinds added to BFS_KINDS
    automatically flow through harvest_waves, bfs_step, and main().

    promoted from `_empty_kind_sets` → public so
    cross-module callers (main.py) can import a stable name instead of
    reaching into a private symbol. The underscore alias below is kept
    for backwards compatibility; it will be removed in the next minor
    version.
    """
    return {k: set() for k in BFS_KINDS}


# deprecated alias. Retained for backwards compatibility with any
# lingering `from parse_wave import _empty_kind_sets` imports; new code
# MUST use `empty_kind_sets` (public). Planned removal in the next minor
# version.
_empty_kind_sets = empty_kind_sets


def harvest_waves(
    work_dir: pathlib.Path,
) -> tuple[dict[str, list[dict]], dict[str, set[str]], dict[str, set[str]], list[tuple[str, str]]]:
    """Walk sf_meta/*/unpackaged/ dirs.

    Returns (flow_children, visited_by_kind, pending_by_kind, cycles).

    every ref collected from Flow XML (actionCalls + subflows)
    is routed through `bfs_step` per-flow. The tuple-keyed visited set is
    the authoritative record; flat per-name sets have been removed.

    the two dicts are keyed by `BFS_KINDS` tokens
    (FLOW/APEX/PROMPT_TEMPLATE/STANDARD_ACTION) — matching the runtime
    tree's `kind` field and the on-disk `_pending_fetches` layout.
    """
    flow_children: dict[str, list[dict]] = {}
    visited_by_kind: dict[str, set[str]] = empty_kind_sets()
    pending_by_kind: dict[str, set[str]] = empty_kind_sets()
    cycles: list[tuple[str, str]] = []

    sf_meta = work_dir / "sf_meta"
    if not sf_meta.exists():
        return flow_children, visited_by_kind, pending_by_kind, cycles

    all_wave_dirs = sorted(
        p / "unpackaged" for p in sf_meta.iterdir()
        if p.is_dir() and (p / "unpackaged").exists()
    )

    # Pass 1: flows (+ route per-flow refs through bfs_step).
    for wave_dir in all_wave_dirs:
        flows_dir = wave_dir / "flows"
        if not flows_dir.exists():
            continue
        for f in sorted(flows_dir.glob("*.flow")):
            flow_name = f.stem
            if flow_name in flow_children:
                continue  # already harvested this wave dir (earlier iter)
            visited_by_kind["FLOW"].add(flow_name)
            try:
                root = ET.parse(f).getroot()
            except ET.ParseError:
                flow_children[flow_name] = []
                continue
            children: list[dict] = []
            # Collect per-flow refs into kind-bucketed sets for one bfs_step.
            new_refs: dict[str, set[str]] = empty_kind_sets()
            for ac in root.findall("sf:actionCalls", NS):
                n = _t(ac, "sf:name")
                at = _t(ac, "sf:actionType") or ""
                an = _t(ac, "sf:actionName")
                item = classify_action_call(at, an, n)
                children.append(item)
                k = item["kind"]
                api = item["api_name"]
                # Only route FETCHABLE kinds into `new_refs` — STANDARD_ACTION
                # items stay as leaf children with no further fetching implied
                # . UNKNOWN items are similarly skipped.
                if k in FETCHABLE_KINDS and api:
                    new_refs[k].add(api)
            for sub in root.findall("sf:subflows", NS):
                n = _t(sub, "sf:name")
                fn = _t(sub, "sf:flowName")
                if fn:
                    children.append({"kind": "FLOW", "element_name": n, "api_name": fn})
                    new_refs["FLOW"].add(fn)
            flow_children[flow_name] = children
            # bfs_step is the canonical merge point.
            pending_by_kind, step_cycles = bfs_step(
                pending_by_kind, visited_by_kind, new_refs
            )
            cycles.extend(step_cycles)

    # Pass 2: APEX classes (mark visited).
    for wave_dir in all_wave_dirs:
        apex_dir = wave_dir / "classes"
        if apex_dir.exists():
            for f in sorted(apex_dir.glob("*.cls-meta.xml")):
                visited_by_kind["APEX"].add(f.name.replace(".cls-meta.xml", ""))

    # Pass 3: Prompt templates (mark visited).
    for wave_dir in all_wave_dirs:
        prompt_dir = wave_dir / "genAiPromptTemplates"
        if prompt_dir.exists():
            for f in sorted(prompt_dir.glob("*.genAiPromptTemplate")):
                visited_by_kind["PROMPT_TEMPLATE"].add(f.stem)

    # Passes 2/3 may have added visited entries AFTER pass-1 pending routing;
    # prune anything that's now visited. This preserves the invariant that
    # `pending ∩ visited = ∅` without needing a second bfs_step.
    for kind in BFS_KINDS:
        pending_by_kind[kind] -= visited_by_kind[kind]

    return flow_children, visited_by_kind, pending_by_kind, cycles


def init_tree(work_dir: pathlib.Path, bundle: dict) -> dict:
    bd_rec = {}
    bd_file = work_dir / "_bot_definition.json"
    if bd_file.exists():
        try:
            recs = (json.loads(bd_file.read_text()).get("result") or {}).get("records") or []
            if recs:
                bd_rec = recs[0]
        except (OSError, json.JSONDecodeError):
            pass

    tree = {
        # 3.0 bumps the _pending_fetches key convention from
        # Metadata-API tokens (Flow/ApexClass/GenAiPromptTemplate) to the
        # runtime-tree `kind` tokens (FLOW/APEX/PROMPT_TEMPLATE/
        # STANDARD_ACTION). `cache_check.py`'s schema-version gate busts any
        # pre-3.0 cache on first run.
        #
        # 3.1 (2026-05-05) canonicalizes `invocation_type` on STANDARD_ACTION
        # nodes (formerly split across `raw_invocation_type` on bundle-
        # sourced nodes and `raw_action_type` on flow-actionCall-sourced
        # nodes). Readers fall back to the two legacy keys for one release.
        "_schema_version": "3.1",
        "agent": {
            "api_name": os.environ["AGENT_API_NAME"],
            "version": os.environ["AGENT_VERSION"],
            "bot_id": os.environ.get("BOT_ID", ""),
            "master_label": bd_rec.get("MasterLabel") or os.environ.get("BOT_MASTER_LABEL", ""),
            "description": bd_rec.get("Description"),
            "agent_type": bd_rec.get("AgentType"),
            "type": bd_rec.get("Type"),
            "agent_template": bd_rec.get("AgentTemplate"),
            "bot_source": bd_rec.get("BotSource"),
            "generation": bundle.get("generation", "unknown"),
            "planner_name": bundle.get("plannerName"),
            "planner_type": bundle.get("plannerType"),
            "_version_auto_picked": (os.environ.get("VERSION_AUTO_PICKED", "") == "true"),
        },
        "root": {
            "kind": "BOT_DEFINITION",
            "api_name": os.environ["AGENT_API_NAME"],
            "children": [],
        },
        "node_count": 0,
        "depth": 0,
        # `_partial` + `_partial_reason` propagate from parse_wave's
        # depth-cap detection through to emit_result's PARTIAL_OK status.
        # `_partial_reason` values: "max-depth-cap" | "pending-refs" | null.
        "_partial": True,
        "_partial_reason": None,
        "_pending_fetches": {k: [] for k in BFS_KINDS},
        "_unresolved": [],
        "_visited": [],
    }
    return tree


def build_root_children(
    bundle: dict,
    visited_by_kind: dict[str, set[str]],
    aux_visited: set[tuple[str, str]],
) -> tuple[list[dict], dict[str, set[str]]]:
    """Build the root's topic / plannerAction children.

    bundle-scoped FLOW/APEX/PROMPT_TEMPLATE refs are collected
    into a kind-keyed `new_refs` dict and returned to the caller, which runs
    them through `bfs_step` for uniform pending-merge + cycle tracking.
    This used to directly mutate three flat sets — split out so the tuple-
    keyed semantics apply to bundle-derived refs too, not just wave-derived
    ones.

    `aux_visited` tracks non-BFS node identity (GEN_AI_FUNCTION / TOPIC) so
    the persisted `_visited` list still represents every node the walker
    has laid hands on. It is NOT consulted by bfs_step.
    """
    children: list[dict] = []
    new_refs: dict[str, set[str]] = empty_kind_sets()

    def action_node(action: dict) -> dict:
        unwraps, leaf = classify_bundle_action(action)
        aux_visited.add(("GEN_AI_FUNCTION", action["name"]))
        node = {
            "kind": "GEN_AI_FUNCTION",
            "api_name": action["name"],
            "unwraps_to": unwraps,
            "children": [leaf] if leaf else [],
        }
        if unwraps:
            tgt = unwraps.get("api_name")
            kind = unwraps.get("kind")
            # STANDARD_ACTION is declared-only, never
            # fetched; routing it into `new_refs` would pollute
            # `_pending_fetches.STANDARD_ACTION`. Gate on FETCHABLE_KINDS.
            if kind in FETCHABLE_KINDS and tgt and tgt not in visited_by_kind[kind]:
                new_refs[kind].add(tgt)
        return node

    for topic in bundle.get("topics", []) or []:
        aux_visited.add(("TOPIC", topic["name"]))
        children.append({
            "kind": "TOPIC",
            "api_name": topic["name"],
            "children": [action_node(a) for a in topic.get("actions", []) or []],
        })

    # bundle["plannerActions"] is always [] now (a planner never has
    # direct functions — 2026-05-05). The key stays in the bundle dict
    # for back-compat with consumers that still call `.get("plannerActions")`.

    return children, new_refs


# ---------------------------------------------------------------------------
# cycle-safe inflate with (kind, canonical_name) tuple-keyed tracking.
#
# Visited tracking uses tuple keys so a Flow `Foo` and an Apex `Foo` are
# distinct nodes — a flat name-only set would silently drop the second one.
# Flow→subflow cycles (direct or cross-type A→B→A) are annotated with
# `_cycle_back_to` on the repeat node and recursion terminates immediately.
#
# , revised 2026-05-03: `MAX_BFS_DEPTH` is a DEFENSIVE termination
# guard, not a functional constraint on chain depth. Must stay in sync
# with `scripts/config.py::MAX_BFS_DEPTH` — duplicated (rather than
# imported) because this module runs as a standalone subprocess under
# `python3 parse_wave.py` (see `main()`) and the module has a long-standing
# "no intra-skill imports" convention (search `no intra-skill imports'
# convention`).
#
# Real cycle detection is per-branch via `visited_in_path`: a flow that
# appears on sibling branches is NOT a cycle (e.g. `handleFlowFault`,
# invoked from many parents), but the same flow recurring along its own
# ancestor chain IS. Textbook DFS cycle detection.
#
# Before the revision this was `5` and the cap itself tripped on shared
# utility flows (`handleFlowFault`, logging subflows) — those landed in
# `_pending_fetches["FLOW"]` and the user saw `PARTIAL_REASON=max-depth-cap`
# on trees that were in fact fully knowable. Bumping to 20 keeps a safety
# net for pathological graphs while letting per-branch cycle detection do
# the real work. On every real bot tree observed to date, the per-branch
# check terminates well below depth 20.
#
# When this cap *does* trip (truly exceptional), the unreached FLOW lands
# in `pending_out["FLOW"]` and the leaf is annotated `_truncated =
# {reason: "max-depth", target: "FLOW:<name>"}`, exactly as before.
MAX_BFS_DEPTH = 20

# Retained alias so the `MAX_INFLATE_DEPTH` symbol (referenced in older
# agent notes / docs) still resolves. Tracks `MAX_BFS_DEPTH` exactly; the
# 2026-05-03 revision reinterpreted this as a defensive guard rather than
# a functional cap, but the alias semantics are unchanged.
MAX_INFLATE_DEPTH = MAX_BFS_DEPTH
_FLOW_CYCLE_KINDS = frozenset({"FLOW"})  # the only kind that recurses here


def _cycle_key(node: dict) -> tuple[str, str]:
    """Tuple key for visited / cycle detection. Flows use canonical api_name.

    keying on `(kind, api_name)` — NOT just name — so cross-kind
    collisions (Flow Foo + Apex Foo) stay distinct.
    """
    return (node.get("kind") or "", node.get("api_name") or "")


def inflate_flow_leaf(
    leaf: dict,
    flow_children: dict,
    depth: int = 0,
    visited_in_path: frozenset[tuple[str, str]] | None = None,
    pending_out: dict[str, set[str]] | None = None,
) -> None:
    """Recursively expand a FLOW leaf's subflow tree.

    `visited_in_path` is threaded through the recursion as an
    IMMUTABLE frozenset — siblings at the same depth must NOT observe
    each other's descent. Mutating a shared set would cause the second
    sibling to be pruned as a false cycle.

    `pending_out` is an OPTIONAL mutable accumulator keyed by
    `BFS_KINDS` tokens. When the depth cap trips (`depth >= MAX_BFS_DEPTH`)
    and the current leaf still has subflow children we'd normally expand,
    those unreached targets are added to `pending_out[kind]` so a caller
    can surface them as `_pending_fetches` on the tree with
    `_partial=True` + `_partial_reason="max-depth-cap"`. When `pending_out`
    is None (legacy callers), the cap behaves as before — silently skip.
    """
    # depth-cap check. We use `>=` (not `>`) so the cap matches
    # `MAX_BFS_DEPTH` exactly — at depth 5 we do NOT expand the current
    # leaf, and the leaf's own (kind, api_name) is recorded in
    # `pending_out` as "unreached". Rationale: this node was supposed
    # to be fully explored but we hit the cap on the way in. Naming
    # the leaf itself (not its kids) is what downstream callers need
    # to surface as `_pending_fetches["FLOW"] = [<unreached>]`.
    if depth >= MAX_BFS_DEPTH:
        if leaf.get("kind") == "FLOW":
            flow_name = leaf.get("api_name")
            if flow_name:
                if pending_out is not None:
                    pending_out.setdefault("FLOW", set()).add(flow_name)
                # annotate the truncated leaf with the unified
                # `_truncated` sub-object so rendered tree views can
                # mark depth-capped nodes alongside cycle nodes using
                # one predicate. The target points at the leaf itself
                # (it was supposed to be fully explored but the cap
                # tripped on the way in).
                leaf["_truncated"] = {
                    "reason": TRUNCATION_MAX_DEPTH,
                    "target": f"FLOW:{flow_name}",
                }
        return
    if leaf.get("kind") != "FLOW":
        return
    flow_name = leaf.get("api_name")
    if not flow_name:
        return
    kids = flow_children.get(flow_name)
    if not kids:
        return  # no data this wave; preserve any existing children

    # Extend the path-visited set with this node. Frozenset keeps sibling
    # branches independent — mutation would cross-contaminate.
    leaf_key = _cycle_key(leaf)
    path_set = (visited_in_path or frozenset()) | {leaf_key}

    new_children: list[dict] = []
    for k in kids:
        item = {"kind": k["kind"], "element_name": k.get("element_name"), "api_name": k["api_name"]}
        # Carry the STANDARD_ACTION / UNKNOWN invocation-type qualifier
        # through to the expanded child. Canonical key is `invocation_type`
        # (schema 3.1); legacy `raw_action_type` kept for one release so
        # caches built by an older parse_wave still render cleanly.
        if "invocation_type" in k:
            item["invocation_type"] = k["invocation_type"]
        if "raw_action_type" in k:
            item["raw_action_type"] = k["raw_action_type"]
        if k["kind"] == "FLOW":
            item["children"] = []
            child_key = _cycle_key(item)
            if child_key in path_set:
                # cycle detected — annotate and do NOT recurse.
                # Path format: "<KIND>:<name>" of the first encounter.
                # unified `_truncated` sub-object + legacy
                # `_cycle_back_to` for backcompat.
                target_path = f"{child_key[0]}:{child_key[1]}"
                item["_truncated"] = {
                    "reason": TRUNCATION_CYCLE,
                    "target": target_path,
                }
                item["_cycle_back_to"] = target_path  # deprecated alias
                new_children.append(item)
                continue
            new_children.append(item)
            inflate_flow_leaf(item, flow_children, depth + 1, path_set, pending_out)
        else:
            new_children.append(item)
    leaf["children"] = new_children


def walk_and_inflate(
    node: dict,
    flow_children: dict,
    depth: int = 0,
    pending_out: dict[str, set[str]] | None = None,
) -> None:
    """Walk the tree and inflate every FLOW leaf we encounter.

    Each inflate call starts with an empty path-visited set — tree-walk
    descent is not itself a Flow recursion, so ancestor GEN_AI_FUNCTION
    or TOPIC nodes don't count toward cycle detection.

    `pending_out` (optional) is threaded into every `inflate_flow_leaf`
    call so depth-cap truncations accumulate into a single shared dict,
    which `main()` merges into `tree["_pending_fetches"]` + flips
    `tree["_partial"]` with reason `max-depth-cap`.
    """
    if node.get("kind") == "GEN_AI_FUNCTION":
        for child in node.get("children", []) or []:
            if child.get("kind") == "FLOW":
                inflate_flow_leaf(child, flow_children, depth, pending_out=pending_out)
    elif node.get("kind") == "FLOW":
        inflate_flow_leaf(node, flow_children, depth, pending_out=pending_out)
    for c in node.get("children", []) or []:
        walk_and_inflate(c, flow_children, depth + 1, pending_out)


def compute_stats(root: dict) -> tuple[int, int, dict]:
    counts: Counter = Counter()

    def walk(node: dict, d: int = 0) -> int:
        k = node.get("kind")
        if k:
            counts[k] += 1
        max_d = d
        for c in node.get("children", []) or []:
            max_d = max(max_d, walk(c, d + 1))
        return max_d

    depth = walk(root)
    return sum(counts.values()), depth, dict(counts)


def atomic_write_json(path: pathlib.Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def finalize_cap(tree: dict) -> dict:
    """Move remaining _pending_fetches items to _unresolved[].

    pending and unresolved both use the same kind tokens now
    (FLOW/APEX/PROMPT_TEMPLATE/STANDARD_ACTION) — matching the runtime
    tree's `kind` field.

    depth-cap truncation writes `_partial=True` +
    `_partial_reason="max-depth-cap"` earlier in the pipeline. Finalize
    preserves those signals when it drains pending → unresolved so the
    downstream emit_result.py can still surface PARTIAL_OK with the
    correct reason. If BOTH the depth cap AND finalize-cap fire on the
    same run, depth-cap wins priority (set first, not overwritten).
    """
    pending = tree.get("_pending_fetches") or {}
    unresolved = tree.setdefault("_unresolved", [])
    drained_any = False
    for kind, items in pending.items():
        for n in items:
            drained_any = True
            unresolved.append({
                "kind": kind,
                "api_name": n,
                "reason": "max-wave-depth exceeded",
            })
    tree["_pending_fetches"] = {k: [] for k in BFS_KINDS}

    # if pending was drained but no `_partial_reason` is set yet,
    # mark it as wave-depth exhaustion. DO NOT overwrite an existing
    # `max-depth-cap` reason — the depth-cap trigger is strictly earlier
    # and more specific.
    if drained_any:
        tree["_partial"] = True
        if not tree.get("_partial_reason"):
            tree["_partial_reason"] = "max-wave-depth"
    return tree


def main() -> int:
    finalize_cap_mode = "--finalize-cap" in sys.argv

    try:
        work_dir = pathlib.Path(os.environ["WORK_DIR"])
    except KeyError as e:
        sys.stderr.write(f"parse_wave.py: missing env {e}\n")
        return 1

    tree_path = work_dir / "declared_action_tree.json"

    # --finalize-cap: trivial; just drain pending → unresolved on existing tree
    if finalize_cap_mode:
        if not tree_path.is_file():
            sys.stderr.write("parse_wave.py: --finalize-cap with no tree file; noop\n")
            return 0
        try:
            tree = json.loads(tree_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            sys.stderr.write(f"parse_wave.py: cannot read tree: {e}\n")
            return 1
        tree = finalize_cap(tree)
        try:
            atomic_write_json(tree_path, tree)
        except OSError as e:
            sys.stderr.write(f"parse_wave.py: write failed: {e}\n")
            return 1
        sys.stderr.write(
            f"[parse_wave] finalize-cap: {len(tree.get('_unresolved', []))} nodes unresolved\n"
        )
        return 0

    # Standard init-or-reparse path
    bundle_path = work_dir / "_bundle_parsed.json"
    if not bundle_path.is_file():
        sys.stderr.write(f"parse_wave.py: missing {bundle_path}\n")
        return 1
    try:
        bundle = json.loads(bundle_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"parse_wave.py: bundle parse error: {e}\n")
        return 1

    # Harvest wave dirs. Returns kind-keyed visited + pending dicts plus
    # the list of (kind, name) cycles detected during per-flow BFS merges.
    flow_children, wave_visited_by_kind, pending_by_kind, _wave_cycles = harvest_waves(work_dir)

    # Load-or-init tree
    if tree_path.is_file():
        try:
            tree = json.loads(tree_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            sys.stderr.write(f"parse_wave.py: cannot re-parse; reinitializing ({e})\n")
            tree = init_tree(work_dir, bundle)
    else:
        tree = init_tree(work_dir, bundle)

    # Rehydrate tuple-keyed visited from the persisted _visited list and
    # union with wave-derived visited. Non-BFS kinds (TOPIC/GEN_AI_FUNCTION)
    # live in `aux_visited` — they're persisted in _visited but do NOT
    # participate in BFS routing.
    visited_by_kind: dict[str, set[str]] = empty_kind_sets()
    for kind, names in wave_visited_by_kind.items():
        visited_by_kind[kind] |= names
    aux_visited: set[tuple[str, str]] = set()
    for pair in (tree.get("_visited") or []):
        if not pair or len(pair) != 2:
            continue
        k, n = pair[0], pair[1]
        if k in BFS_KINDS:
            visited_by_kind[k].add(n)
        else:
            aux_visited.add((k, n))

    # If the tree was just initialized, populate root children (only once).
    # bundle-derived refs now flow through bfs_step via
    # build_root_children's new_refs return value — same code path as
    # wave-derived refs.
    is_fresh = not (tree.get("root", {}).get("children"))
    if is_fresh:
        children, bundle_new_refs = build_root_children(
            bundle, visited_by_kind, aux_visited
        )
        tree["root"]["children"] = children
        pending_by_kind, _bundle_cycles = bfs_step(
            pending_by_kind, visited_by_kind, bundle_new_refs
        )

    # Inflate Flow leaves wherever possible.
    # `depth_cap_pending` captures subflow refs we skipped because
    # the depth cap tripped — these get merged into `_pending_fetches`
    # below so downstream emit_result.py can surface `PARTIAL_OK`.
    depth_cap_pending: dict[str, set[str]] = empty_kind_sets()
    walk_and_inflate(tree["root"], flow_children, pending_out=depth_cap_pending)

    # Merge depth-cap-suppressed refs back into pending_by_kind so they
    # land in `_pending_fetches`. Preserve any existing (already-visited)
    # exclusion semantics — refs already fetched this run MUST NOT be
    # re-reported as pending.
    for kind in BFS_KINDS:
        pending_by_kind[kind] |= depth_cap_pending.get(kind, set())

    depth_cap_tripped = any(depth_cap_pending[k] for k in BFS_KINDS)

    # Recompute pending (exclude anything now visited). the
    # persisted dict uses the same `BFS_KINDS` tokens as the runtime tree
    # and the in-memory buckets — no more Metadata-API-style aliasing.
    tree["_pending_fetches"] = {
        k: sorted(pending_by_kind.get(k, set()) - visited_by_kind.get(k, set()))
        for k in BFS_KINDS
    }

    # surface a `_partial` signal when:
    # (a) depth-cap-pending refs exist (we suppressed deep subflows), OR
    # (b) any `_pending_fetches` bucket is non-empty at write time.
    # `_partial_reason` identifies which of the two tripped — `max-depth-cap`
    # takes priority when depth_cap_pending is non-empty, since the cap is
    # the reason pending refs weren't drained to `_unresolved` yet.
    any_pending = any(tree["_pending_fetches"][k] for k in BFS_KINDS)
    if depth_cap_tripped:
        tree["_partial"] = True
        tree["_partial_reason"] = "max-depth-cap"
    elif any_pending:
        # Still incomplete but NOT because of the depth cap. Leave any
        # existing reason intact if prior run set it; default to a neutral
        # marker so emit_result.py can still flip to PARTIAL_OK.
        tree["_partial"] = True
        if not tree.get("_partial_reason"):
            tree["_partial_reason"] = "pending-refs"
    else:
        tree["_partial"] = False
        tree["_partial_reason"] = None

    # Recompute node_count + depth + kind_counts
    node_count, depth, kind_counts = compute_stats(tree["root"])
    tree["node_count"] = node_count
    tree["depth"] = depth
    tree["_kind_counts"] = kind_counts

    # Persist visited as sorted list of [kind, name] pairs. Includes aux
    # kinds (TOPIC/GEN_AI_FUNCTION) so the replay surface is complete.
    all_visited: set[tuple[str, str]] = set(aux_visited)
    for kind, names in visited_by_kind.items():
        for n in names:
            all_visited.add((kind, n))
    tree["_visited"] = [list(v) for v in sorted(all_visited)]

    try:
        atomic_write_json(tree_path, tree)
    except OSError as e:
        sys.stderr.write(f"parse_wave.py: write failed: {e}\n")
        return 1

    # log line mirrors the persisted dict's kind tokens.
    pending_total = sum(len(v) for v in tree["_pending_fetches"].values())
    sys.stderr.write(
        f"[parse_wave] parsed: {node_count} nodes, depth {depth}, counts={kind_counts}, "
        f"pending={pending_total} "
        f"(flow={len(tree['_pending_fetches']['FLOW'])} "
        f"apex={len(tree['_pending_fetches']['APEX'])} "
        f"prompt_template={len(tree['_pending_fetches']['PROMPT_TEMPLATE'])} "
        f"standard_action={len(tree['_pending_fetches']['STANDARD_ACTION'])})\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
