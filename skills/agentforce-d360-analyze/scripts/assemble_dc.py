"""Assemble dc._session_tree.json from fetched DC artifacts.

Given `DATA_ROOT/<sid>/dc.*.json` + `dc._session_manifest.json` (produced by
`scripts/fetch_dc.py`), this module joins the rows in memory and emits:

  - dc._session_tree.json    — session-rooted hierarchical view
                                (Interaction → Step → Generation →
                                GatewayRequest, with audit rows nested)

The human-readable markdown summary is produced by a separate stage,
`scripts/render_dc.py`, which reads only the tree.

Design contract (see references/dc_pipeline_contract.md):

  - No DMO fetches. Pure in-memory compute over already-fetched artifacts.
  - Driven off `manifest["queries"][*]["name"]` — adding a 25th DMO to
    fetch_dc.py doesn't require changes here (it just won't be placed in
    the tree until the logic is extended).
  - Declared binding chain nests GatewayRequest under LLM_STEP via
    `Step.ssot__GenerationId__c → Generation → GatewayResponse → Request`.
  - Chain-orphan GW calls fall through to a timestamp-window rule
    (tier dominates: ACTION → TOPIC → TRUST_GUARDRAILS → any other;
    innermost Step wins within a tier).
  - PK collisions and parse warnings surface in `counts.*`, not stderr-only.

Invocation:
    python3 scripts/assemble_dc.py --session <sid>
"""
from __future__ import annotations

import argparse
import functools
import html
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_ROOT, paths


# ---- sentinels + constants -------------------------------------------------

_NOT_SET = {"", "NOT_SET", None}
_INTERNAL_TRACE_RE = re.compile(r'"internalTraceId":"([a-f0-9]+)"')  # @rule-suppress starter-sec-002 — re.compile, not eval/exec

# Real, non-placeholder agent version. Matches the canonical `^v[0-9]+$`
# shape that paths.session_dir requires AND excludes the `v0` placeholder
# stamped by fetch_dc's MyAgent fallback (fetch_dc.py:570-597).
# Used by `_promote_identity` to decide whether session_identity carries
# a richer agent_version that should win over a manifest placeholder.
_REAL_VERSION_RE = re.compile(r'^v[0-9]+$')  # @rule-suppress starter-sec-002 — re.compile, not eval/exec

# Tier order for timestamp-window fallback. "any other" is an implicit last-resort
# catch-all covering LLM_STEP (without declared binding), SESSION_END, and any
# future step types not explicitly listed.
_TIER_ORDER = ("ACTION_STEP", "TOPIC_STEP", "TRUST_GUARDRAILS_STEP")

# Canonical identity-field name → ordered list of `gateway_request_tags.tag__c`
# values that carry it, tried in order. Agent versions emit different tag
# names: newer Atlas ReAct agents use `agent_developer_name` /
# `agent_version_api_name`; legacy MyAgent builds omit the developer
# name entirely and use the unprefixed `version_api_name`. First non-null
# value wins. A single-element list means "no fallback known."
_TAG_KEY_ALIASES: Dict[str, Tuple[str, ...]] = {
    "agent_api_name": ("agent_developer_name",),
    "agent_version": ("agent_version_api_name", "version_api_name"),
}


# ---- typed namespaces ------------------------------------------------------
#
# Four frozen dataclasses replace the former dict-bags. frozen=True guards
# attribute re-assignment, not mutation of the dict values themselves — the
# producers are responsible for handing in plain dicts (not defaultdicts) so
# downstream helpers don't rely on auto-creation the type doesn't promise.

@dataclass(frozen=True)
class Indexes:
    interactions_by_id: Dict[str, dict]
    participants_by_id: Dict[str, dict]
    generations_by_id: Dict[str, dict]
    gw_req_by_id: Dict[str, dict]
    gw_resp_by_resp_id: Dict[str, dict]
    feedback_by_id: Dict[str, dict]
    gw_resp_by_req_id: Dict[str, List[dict]]
    steps_by_interaction: Dict[str, List[dict]]
    messages_by_interaction: Dict[str, List[dict]]
    gw_tags_by_parent: Dict[str, List[dict]]
    gw_md_by_parent: Dict[str, List[dict]]
    gw_llm_by_parent: Dict[str, List[dict]]
    quality_by_parent: Dict[str, List[dict]]
    quality_by_id: Dict[str, dict]
    feedback_by_gen: Dict[str, List[dict]]
    feedback_details_by_parent: Dict[str, List[dict]]
    participant_role_by_id: Dict[str, Optional[str]]


@dataclass(frozen=True)
class PolymorphicSplits:
    categories_by_generation: Dict[str, List[dict]]
    categories_by_quality: Dict[str, List[dict]]
    gw_records_by_gw_req: Dict[str, List[dict]]
    gw_records_by_feedback: Dict[str, List[dict]]
    tag_assoc_session: List[dict]
    tag_assoc_by_interaction: Dict[str, List[dict]]
    tag_assoc_by_moment: Dict[str, List[dict]]


@dataclass(frozen=True)
class BindingResults:
    declared_gw_ids: Set[str]
    declared_steps_with_gw: frozenset
    step_id_to_gw_id: Dict[str, Optional[str]]
    declared_collisions: int


@dataclass(frozen=True)
class Catalog:
    agents_observed: List[str]
    tag_definitions: List[dict]
    tag_definition_associations: List[dict]
    tags: List[dict]


@dataclass
class BinderCtx:
    """Per-interaction scratch state used only by the timestamp-window pass.

    Kept in a parallel `Dict[iid, BinderCtx]` instead of stashed on the
    interaction view, so binder state can never leak into the emitted tree.
    """
    start_ts: Optional[datetime]
    end_ts: Optional[datetime]
    steps_with_ts: List[Tuple[dict, Optional[datetime], Optional[datetime]]]
    reserved_step_ids: frozenset


# ---- session-dir resolution ----------------------------------------------

def _find_session_dir(sid: str) -> Path:
    """Locate the session dir under the nested layout.

    Given only a session id, we don't know ``(org, agent, version)`` upfront.
    Strategy:

    1. Validate ``sid`` against ``paths.SESSION_ID_RE`` at entry. ``sid`` comes
       in via argv / resolve_session and flows directly into path composition
       (``<org>/_sessions/<sid>.link``) and glob patterns; an unvalidated
       value here would undo the traversal guard added in PR #657 BLOCKER-2.
    2. Breadcrumb lookup: ``DATA_ROOT/<org>/_sessions/<sid>.link`` is a plain-
       text relative-path pointer written by ``storage.save``. Iterate all
       orgs, read each ``.link``, resolve against the breadcrumb's parent,
       and **enforce containment** — a tampered or stale breadcrumb whose
       target escapes ``DATA_ROOT`` is skipped (not raised) so a single
       malicious breadcrumb can't DoS the whole resolver. Falls through to
       the glob fallback on any breadcrumb miss.
    3. Glob fallback: ``DATA_ROOT/*/*/<sid>/`` — ``sid`` is now validated at
       entry so the pattern is fixed-depth and cannot glob outside its
       intended 2-level subtree.
    4. Raise ``SystemExit`` with a clear hint to run fetch_dc.py first.

    Returns the absolute directory path.
    """
    # Validate first — rejects "../etc", "a/b", "", None, and control chars.
    # ``sid`` from here on is safe to use as a path segment and as the tail
    # of a fixed-depth glob.
    paths.validate_session_id(sid)
    root = paths.DATA_ROOT
    if root.is_dir():
        # Resolve DATA_ROOT once so containment checks don't repeat the walk.
        root_resolved = root.resolve()
        for org_dir in root.iterdir():
            if not org_dir.is_dir():
                continue
            link = org_dir / "_sessions" / f"{sid}.link"
            if link.is_file():
                try:
                    rel = link.read_text().strip()
                except OSError:
                    continue
                # Resolve relative to the breadcrumb's parent (_sessions/),
                # then enforce that the resolved path stays inside
                # DATA_ROOT. ``.link`` contents are user-writable — a planted
                # breadcrumb with ``../../../../etc/passwd`` must NOT pivot
                # the assembler outside the plugin's data tree.
                target = (link.parent / rel).resolve()
                if not target.is_relative_to(root_resolved):
                    # Stale or malicious breadcrumb. Skip — fall through to
                    # the glob fallback rather than raising, so one bad
                    # breadcrumb in one org doesn't block discovery in
                    # another.
                    continue
                if target.is_dir():
                    return target
        # Glob fallback. ``sid`` is validated; the pattern is fixed-depth.
        matches = list(root.glob(f"*/*/{sid}"))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Placeholder agent dirs (leading-underscore name like
            # ``<org>/_agent_<botid>__v0/``) mark provisional sessions
            # whose identity wasn't fully resolved at first write. When a
            # real (agent, version) dir also exists for the same session,
            # it's the authoritative home; the placeholder is stale.
            # Prefer the real dir.
            real = [p for p in matches if not p.parent.name.startswith("_")]
            if len(real) == 1:
                return real[0]
            raise SystemExit(
                f"assemble_dc: session {sid} resolves to {len(matches)} dirs "
                f"under {root} — ambiguous. Check for duplicate sessions "
                f"across agents."
            )
    raise SystemExit(
        f"assemble_dc: session dir for {sid} not found under {root}; "
        f"run fetch_dc.py first"
    )


# ---- loaders ---------------------------------------------------------------

def _load(session_dir: Path, name: str, parse_warnings: List[str]) -> List[dict]:
    """Load dc.<name>.json from session_dir. Missing → []. Malformed → [] + warning."""
    p = session_dir / f"dc.{name}.json"
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"assemble_dc: WARN dc.{name}.json unreadable: {str(e).splitlines()[0]}",
              file=sys.stderr)
        parse_warnings.append(name)
        return []


def _load_manifest(session_dir: Path) -> dict:
    p = session_dir / "dc._session_manifest.json"
    if not p.is_file():
        raise SystemExit(
            f"assemble_dc: manifest not found at {p}; run fetch_dc.py first"
        )
    manifest = json.loads(p.read_text())
    if "queries" not in manifest:
        raise SystemExit("assemble_dc: manifest schema changed — no 'queries' key")
    return manifest


def _load_all(sid: str) -> Tuple[dict, Dict[str, List[dict]], List[str], Path]:
    """Return (manifest, rows_by_name, parse_warnings, session_dir).

    Iterates manifest["queries"][*]["name"] rather than a hard-coded list —
    a new DMO added to fetch_dc.py is picked up automatically.
    """
    session_dir = _find_session_dir(sid)
    manifest = _load_manifest(session_dir)
    parse_warnings: List[str] = []
    rows = {
        q["name"]: _load(session_dir, q["name"], parse_warnings)
        for q in manifest["queries"]
    }
    return manifest, rows, parse_warnings, session_dir


# ---- small helpers ---------------------------------------------------------

def _clean(value: Any) -> Any:
    """NOT_SET sentinel → None. Other values pass through."""
    return None if value in _NOT_SET else value


def _harvest_str(value: Any) -> Optional[str]:
    """Harvest-layer string normalizer for the session-identity block.

    Handles three quirks that `_clean` deliberately does not:
    1. **html.unescape** — tag values arrive double-escaped
       (`"&quot;0Xx…&quot;"`).
    2. **Quote-strip** — after unescape most tag values are wrapped in
       literal `"` characters; strip them.
    3. **`UNSET_VALUE` sentinel** — Data Cloud emits this on a small set
       of optional columns (e.g. `gateway_requests.promptTemplateVersionNo__c`,
       certain `tag_first` values on cold-start sessions). Not observed
       on the columns `_build_session_identity` currently reads, but
       included defensively since the sentinel is part of the DC schema
       contract and a harvest-layer reader should collapse it to None.

    The binding / index layer uses `_clean()` / `_NOT_SET` which
    intentionally omits these rules — they would be noise there.
    """
    if value is None:
        return None
    s = html.unescape(str(value)).strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return None if s in ("", "NOT_SET", "UNSET_VALUE") else s


def _promote_identity(
    manifest_value: Any,
    session_identity_value: Any,
    *,
    kind: Literal["api_name", "version"],
) -> Any:
    """Pick the richer of (manifest, session_identity) for a top-level identity slot.

    Background. ``fetch_dc._resolve_identity`` walks AGENT-role participant
    rows for ``(api_name, version)``. On agent shapes like MyAgent the
    AGENT rows can leave both fields NOT_SET, so the resolver falls back
    (fetch_dc.py:570-597) to picking ``api_name`` from any participant row
    and stamping ``version="v0"`` as a placeholder satisfying
    ``paths.session_dir``'s ``^v[0-9]+$`` shape. The placeholder is enough
    to land the session in a directory, but it's wrong: by wave 5 the
    fetch has materialized ``gateway_request_tags`` rows carrying the real
    ``agent_version_api_name`` (e.g. ``v24``), and ``_build_session_identity``
    correctly harvests it onto ``session.identity``. The top-level
    ``identity`` block was previously copied verbatim from the manifest,
    so the placeholder leaked downstream while the right value sat
    visible in the same JSON.

    Policy:

    - ``kind="version"``: if manifest is the ``"v0"`` placeholder AND
      session_identity carries a non-``v0`` value matching ``^v[0-9]+$``,
      promote. Otherwise keep manifest.
    - ``kind="api_name"``: if manifest is NOT_SET-ish (None / "" / "NOT_SET"
      / "NOT SET") AND session_identity has a real value, promote.
      Otherwise keep manifest. (Crucially, when session_identity is None
      and manifest has a value, we keep manifest — the strict AGENT-row
      pick is intentional on healthy sessions.)
    - When manifest and session_identity both carry real-but-disagreeing
      values, the manifest wins. The strict AGENT-row pick is the
      authoritative source on a normal session; we only promote in the
      narrow case where the manifest carries a known placeholder /
      NOT_SET sentinel and the harvest layer has something better.
    """
    if kind == "version":
        if manifest_value != "v0":
            return manifest_value
        if not isinstance(session_identity_value, str):
            return manifest_value
        if session_identity_value == "v0":
            return manifest_value
        if not _REAL_VERSION_RE.match(session_identity_value):
            return manifest_value
        return session_identity_value
    # kind == "api_name"
    if manifest_value not in (None, "", "NOT_SET", "NOT SET"):
        return manifest_value
    if isinstance(session_identity_value, str) and session_identity_value:
        return session_identity_value
    return manifest_value


def _reconcile_top_identity(
    manifest: dict, session_identity: dict, org_id_15: Any,
) -> dict:
    """Build the top-level ``identity`` block, promoting placeholders.

    Centralizes the policy in one place so the happy path
    (`_assemble_session`) and the gateway-direct fallback don't drift
    apart. Emits a stderr note when promotion fires so an investigator
    sees the divergence at run time.
    """
    manifest_api = manifest.get("agent_api_name")
    manifest_ver = manifest.get("agent_version")
    session_api = session_identity.get("agent_api_name")
    session_ver = session_identity.get("agent_version")

    promoted_api = _promote_identity(manifest_api, session_api, kind="api_name")
    promoted_ver = _promote_identity(manifest_ver, session_ver, kind="version")

    if promoted_api != manifest_api:
        print(
            f"assemble_dc: identity promoted: agent_api_name "
            f"{manifest_api!r} -> {promoted_api!r} (from session.identity)",
            file=sys.stderr,
        )
    if promoted_ver != manifest_ver:
        print(
            f"assemble_dc: identity promoted: agent_version "
            f"{manifest_ver} -> {promoted_ver} (from session.identity)",
            file=sys.stderr,
        )

    return {
        "org_id_15": org_id_15,
        "agent_api_name": promoted_api,
        "agent_version": promoted_ver,
    }


def _resolve_end_type(session_row: dict, rows: dict) -> Optional[str]:
    """Resolve the session's terminal outcome with a Session→Step fallback.

    Session DMO's ``ssot__AiAgentSessionEndType__c`` is authoritative when
    populated, but on Messaging-channel and short E&O sessions it stays
    ``NOT_SET`` even after the SESSION_END interaction has materialized.
    The runtime writes the actual outcome (``CLOSED_USER_REQUEST``,
    ``USER_ENDED``, ``ESCALATED``, ``TRANSFERRED``, ``TIMEOUT``) onto the
    SESSION_END step's ``ssot__Name__c`` instead. Fall through to that
    step when Session.EndType is missing, so the rendered summary stops
    saying "session end not yet materialized in STDM" for sessions that
    actually completed cleanly.
    """
    primary = _clean(session_row.get("ssot__AiAgentSessionEndType__c"))
    if primary:
        return primary
    for step in rows.get("steps", []) or ():
        if step.get("ssot__AiAgentInteractionStepType__c") == "SESSION_END":
            name = _clean(step.get("ssot__Name__c"))
            if name:
                return name
    return None


def _ts(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp. NOT_SET / non-string → None (unbounded)."""
    if not isinstance(value, str) or value in _NOT_SET:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _index_unique(rows: Iterable[dict], key: str,
                  collisions: List[dict], dmo_label: str) -> Dict[str, dict]:
    """Build a {key_value: row} dict. On collision: first-write-wins + record."""
    out: Dict[str, dict] = {}
    for r in rows:
        k = r.get(key)
        if k in _NOT_SET:
            continue
        if k in out:
            collisions.append({"dmo": dmo_label, "key": k})
        else:
            out[k] = r
    return out


def _groupby(rows: Iterable[dict], key: str) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        k = r.get(key)
        if k not in _NOT_SET:
            out[k].append(r)
    return dict(out)


def _extract_trace_id(interaction: dict) -> Optional[str]:
    """Prefer the primary column; fall back to AttributeText regex."""
    tid = interaction.get("ssot__TelemetryTraceId__c")
    if tid and tid not in _NOT_SET:
        return tid
    attr = interaction.get("ssot__AttributeText__c") or ""
    if not attr:
        return None
    m = _INTERNAL_TRACE_RE.search(html.unescape(attr))
    return m.group(1) if m else None


# ---- declared binding chain ------------------------------------------------

def _declared_gw_for_step(step: dict,
                          generations_by_id: Dict[str, dict],
                          gw_resp_by_resp_id: Dict[str, dict],
                          gw_req_by_id: Dict[str, dict]) -> Optional[dict]:
    """Step → Generation → Response → Request. Returns the GatewayRequest row or None."""
    gen_id = step.get("ssot__GenerationId__c")
    if gen_id in _NOT_SET:
        return None
    gen = generations_by_id.get(gen_id)
    if not gen:
        return None
    resp_id = gen.get("generationResponseId__c")
    if resp_id in _NOT_SET:
        return None
    resp = gw_resp_by_resp_id.get(resp_id)
    if not resp:
        return None
    req_id = resp.get("generationRequestId__c")
    if req_id in _NOT_SET:
        return None
    return gw_req_by_id.get(req_id)


# ---- timestamp-window fallback --------------------------------------------

def _tier(step_type: str) -> int:
    """Lower is better. 0 = ACTION, 1 = TOPIC, 2 = GUARDRAIL, 3 = any other."""
    try:
        return _TIER_ORDER.index(step_type)
    except ValueError:
        return len(_TIER_ORDER)  # "any other"


def _window_contains(gw_ts: datetime, start: Optional[datetime],
                     end: Optional[datetime]) -> bool:
    """Closed-closed containment. None end_ts → +∞. Missing start → no match."""
    if start is None:
        return False
    if gw_ts < start:
        return False
    if end is None:
        return True  # open-ended upward
    return gw_ts <= end


def _bind_ts_window(gw_req: dict,
                    steps_with_ts: List[Tuple[dict, datetime, Optional[datetime]]],
                    interaction_window: Tuple[Optional[datetime], Optional[datetime]],
                    reserved_step_ids: "frozenset[str]") -> Tuple[str, Optional[str]]:
    """Return (placement, bound_step_id).

    placement ∈ {"step", "interaction", "unbound"}.
    bound_step_id is set only when placement == "step".
    """
    gw_ts_raw = gw_req.get("timestamp__c")
    gw_ts = _ts(gw_ts_raw)
    if gw_ts is None:
        return ("unbound", None)

    # Step candidates: contains gw_ts AND not already declared-bound.
    candidates = [
        (step, start, end)
        for step, start, end in steps_with_ts
        if step["ssot__Id__c"] not in reserved_step_ids
           and _window_contains(gw_ts, start, end)
    ]
    if candidates:
        # Best tier → innermost (shortest window) → latest start_ts.
        def sort_key(c):
            step, start, end = c
            tier = _tier(step.get("ssot__AiAgentInteractionStepType__c", ""))
            # Window size; treat None end_ts as "longest" (so nested closed wins).
            if end is None:
                width = float("inf")
            else:
                width = (end - start).total_seconds()
            # Invert latest-start-wins by negating seconds since epoch.
            return (tier, width, -start.timestamp())
        candidates.sort(key=sort_key)
        winner = candidates[0][0]
        return ("step", winner["ssot__Id__c"])

    # Interaction window.
    i_start, i_end = interaction_window
    if _window_contains(gw_ts, i_start, i_end):
        return ("interaction", None)
    return ("unbound", None)


# ---- gateway-request view builder -----------------------------------------

def _build_gw_view(gw_req: dict, binding_method: str, *,
                   idx: Indexes, dispatch: PolymorphicSplits,
                   bound_step_id: Optional[str] = None) -> dict:
    """Build one GatewayRequest view row.

    `idx` and `dispatch` are kw-only so `functools.partial(_build_gw_view,
    idx=..., dispatch=...)` bindings don't collide with positional args at
    the 3 call sites (declared / timestamp_window / unbound).
    """
    gw_id = gw_req["gatewayRequestId__c"]
    responses = idx.gw_resp_by_req_id.get(gw_id, [])
    view: Dict[str, Any] = {
        "binding_method": binding_method,
        "gateway_request_id": gw_id,
        "feature": _clean(gw_req.get("feature__c")),
        "model": _clean(gw_req.get("model__c")),
        "provider": _clean(gw_req.get("provider__c")),
        "prompt_template_dev_name": _clean(gw_req.get("promptTemplateDevName__c")),
        "prompt_tokens": gw_req.get("promptTokens__c"),
        "completion_tokens": gw_req.get("completionTokens__c"),
        "total_tokens": gw_req.get("totalTokens__c"),
        # Carry the raw input prompt through the hierarchical view so the
        # renderer can surface it in the opt-in "Planner LLM calls" section.
        # The 64 KB display cap lives in render_dc, not here — the tree
        # stores the authoritative payload.
        "prompt_text": gw_req.get("prompt__c"),
        "response": responses[0] if responses else None,
        "tags": idx.gw_tags_by_parent.get(gw_id, []),
        "records": dispatch.gw_records_by_gw_req.get(gw_id, []),
        "metadata": idx.gw_md_by_parent.get(gw_id, []),
        "llm": idx.gw_llm_by_parent.get(gw_id, []),
    }
    if bound_step_id is not None:
        view["bound_to_step_id"] = bound_step_id
    return view


# ---- main assembly ---------------------------------------------------------

def _build_indexes(rows: Dict[str, List[dict]], collisions: List[dict]) -> Indexes:
    """Build all primary-key dicts and groupby tables. Returns a frozen Indexes."""
    return Indexes(
        interactions_by_id=_index_unique(
            rows.get("interactions", []), "ssot__Id__c", collisions, "interactions_by_id"),
        participants_by_id=_index_unique(
            rows.get("participants", []), "ssot__Id__c", collisions, "participants_by_id"),
        generations_by_id=_index_unique(
            rows.get("generations", []), "generationId__c", collisions, "generations_by_id"),
        gw_req_by_id=_index_unique(
            rows.get("gateway_requests", []), "gatewayRequestId__c", collisions, "gw_req_by_id"),
        gw_resp_by_resp_id=_index_unique(
            rows.get("gateway_responses", []), "generationResponseId__c",
            collisions, "gw_resp_by_resp_id"),
        feedback_by_id=_index_unique(
            rows.get("feedback", []), "feedbackId__c", collisions, "feedback_by_id"),
        gw_resp_by_req_id=_groupby(rows.get("gateway_responses", []), "generationRequestId__c"),
        steps_by_interaction=_groupby(rows.get("steps", []), "ssot__AiAgentInteractionId__c"),
        messages_by_interaction=_groupby(rows.get("messages", []), "ssot__AiAgentInteractionId__c"),
        gw_tags_by_parent=_groupby(rows.get("gateway_request_tags", []), "parent__c"),
        gw_md_by_parent=_groupby(rows.get("gateway_request_metadata", []), "parent__c"),
        gw_llm_by_parent=_groupby(rows.get("gateway_request_llm", []), "parent__c"),
        quality_by_parent=_groupby(rows.get("content_quality", []), "parent__c"),
        quality_by_id={q["id__c"]: q for q in rows.get("content_quality", []) if q.get("id__c")},
        feedback_by_gen=_groupby(rows.get("feedback", []), "generationId__c"),
        feedback_details_by_parent=_groupby(rows.get("feedback_details", []), "parent__c"),
        participant_role_by_id={
            p["ssot__Id__c"]: p.get("ssot__AiAgentSessionParticipantRole__c")
            for p in rows.get("participants", []) if p.get("ssot__Id__c")
        },
    )


def _dispatch_polymorphic(rows: Dict[str, List[dict]], idx: Indexes) -> PolymorphicSplits:
    """Split ContentCategory, GtwyObjRecord, and TagAssociation by polymorphic parent.

    Producers accumulate into defaultdicts for ergonomics, but the returned
    dataclass stores plain dicts — frozen `Dict[...]` typing can't promise
    auto-creation, so don't let it leak.
    """
    # ContentCategory: parent is either a generation or a quality row.
    cat_by_gen: Dict[str, List[dict]] = defaultdict(list)
    cat_by_qual: Dict[str, List[dict]] = defaultdict(list)
    for cat in rows.get("content_category", []):
        parent = cat.get("parent__c")
        if parent in _NOT_SET:
            continue
        if parent in idx.generations_by_id:
            cat_by_gen[parent].append(cat)
        elif parent in idx.quality_by_id:
            cat_by_qual[parent].append(cat)

    # GtwyObjRecord: parent is either a gateway_request or a feedback row.
    rec_by_gw: Dict[str, List[dict]] = defaultdict(list)
    rec_by_fb: Dict[str, List[dict]] = defaultdict(list)
    for rec in rows.get("gateway_records", []):
        parent = rec.get("parent__c")
        if parent in _NOT_SET:
            continue
        if parent in idx.gw_req_by_id:
            rec_by_gw[parent].append(rec)
        elif parent in idx.feedback_by_id:
            rec_by_fb[parent].append(rec)

    # TagAssociation: exactly one of session/interaction/moment FK is populated.
    ta_session: List[dict] = []
    ta_by_int: Dict[str, List[dict]] = defaultdict(list)
    ta_by_mom: Dict[str, List[dict]] = defaultdict(list)
    for ta in rows.get("tag_associations", []):
        if ta.get("ssot__AiAgentSessionId__c") not in _NOT_SET:
            ta_session.append(ta)
        elif ta.get("ssot__AiAgentInteractionId__c") not in _NOT_SET:
            ta_by_int[ta["ssot__AiAgentInteractionId__c"]].append(ta)
        elif ta.get("ssot__AiAgentMomentId__c") not in _NOT_SET:
            ta_by_mom[ta["ssot__AiAgentMomentId__c"]].append(ta)

    return PolymorphicSplits(
        categories_by_generation=dict(cat_by_gen),
        categories_by_quality=dict(cat_by_qual),
        gw_records_by_gw_req=dict(rec_by_gw),
        gw_records_by_feedback=dict(rec_by_fb),
        tag_assoc_session=ta_session,
        tag_assoc_by_interaction=dict(ta_by_int),
        tag_assoc_by_moment=dict(ta_by_mom),
    )


def _filter_catalog(rows: Dict[str, List[dict]]) -> Catalog:
    """Filter org-wide tag vocabulary to only what's reachable from session agents."""
    agents = {
        p.get("ssot__AiAgentApiName__c") for p in rows.get("participants", [])
        if p.get("ssot__AiAgentSessionParticipantRole__c") == "AGENT"
           and p.get("ssot__AiAgentApiName__c") not in _NOT_SET
    } | {
        m.get("ssot__AiAgentApiName__c") for m in rows.get("moments", [])
        if m.get("ssot__AiAgentApiName__c") not in _NOT_SET
    }
    # Mirror fetch_dc._resolve_identity's USER-row fallback. On agent shapes
    # like MyAgent, AGENT-role rows leave api_name=NOT_SET while USER
    # rows correctly carry the agent's api_name. Without this fallback, the
    # session lands in a `<api_name>__v0/` directory but `agents_observed`
    # is empty — directory and rendered catalog disagree. Only fires when the
    # primary (AGENT + moments) sources turned up nothing usable; in normal
    # sessions the USER and AGENT rows agree and the union is idempotent.
    if not agents:
        agents = {
            p.get("ssot__AiAgentApiName__c") for p in rows.get("participants", [])
            if p.get("ssot__AiAgentApiName__c") not in _NOT_SET
        }
    agents_observed = sorted(a for a in agents if a)
    relevant_assocs = [
        a for a in rows.get("tag_definition_associations", [])
        if a.get("ssot__AiAgentApiName__c") in agents_observed
    ]
    relevant_def_ids = {
        a["ssot__AiAgentTagDefinitionId__c"] for a in relevant_assocs
        if a.get("ssot__AiAgentTagDefinitionId__c") not in _NOT_SET
    }
    return Catalog(
        agents_observed=agents_observed,
        tag_definitions=[d for d in rows.get("tag_definitions", [])
                         if d.get("ssot__Id__c") in relevant_def_ids],
        tag_definition_associations=relevant_assocs,
        tags=[t for t in rows.get("tags", [])
              if t.get("ssot__AiAgentTagDefinitionId__c") in relevant_def_ids],
    )


def _build_session_identity(rows: Dict[str, List[dict]], manifest: dict) -> dict:
    """Harvest 18 identity fields from 4 DMOs for the `session.identity` block.

    All row iteration is preceded by a deterministic sort so repeated runs
    produce byte-identical output regardless of fetch order. `_harvest_str()` is
    the shared normalizer — html.unescape + quote-strip + NOT_SET /
    UNSET_VALUE / empty coercion. See references/dc_pipeline_contract.md
    §2.9a for the field-to-column mapping.
    """
    # --- gateway_requests: sort by (timestamp__c, gatewayRequestId__c) ---
    gwr_sorted = sorted(
        rows.get("gateway_requests", []),
        key=lambda r: (r.get("timestamp__c") or "",
                       r.get("gatewayRequestId__c") or ""),
    )

    def _first_gwr(key: str) -> Optional[str]:
        for r in gwr_sorted:
            v = _harvest_str(r.get(key))
            if v is not None:
                return v
        return None

    org_id = _first_gwr("orgId__c")
    platform_user_id = _first_gwr("userId__c")
    planner_id = _first_gwr("plannerId__c")
    bot_version_id = _first_gwr("botVersionId__c")
    app_type = _first_gwr("appType__c")

    # --- gateway_request_tags: sort by (parent__c, tag__c, tagValue__c) ---
    tags_sorted = sorted(
        rows.get("gateway_request_tags", []),
        key=lambda r: (r.get("parent__c") or "",
                       r.get("tag__c") or "",
                       r.get("tagValue__c") or ""),
    )
    tag_first: Dict[str, Optional[str]] = {}
    for t in tags_sorted:
        k = t.get("tag__c")
        if not k or k in tag_first:
            continue
        tag_first[k] = _harvest_str(t.get("tagValue__c"))

    # --- sessions[0] — always exactly one row per session on this path ---
    sessions = rows.get("sessions", [])
    session_row = sessions[0] if sessions else {}

    # --- participants: first USER-role row by ssot__Id__c ---
    participants_sorted = sorted(
        rows.get("participants", []),
        key=lambda r: r.get("ssot__Id__c") or "",
    )
    messaging_end_user_id = None
    for p in participants_sorted:
        if p.get("ssot__AiAgentSessionParticipantRole__c") == "USER":
            v = _harvest_str(p.get("ssot__ParticipantId__c"))
            if v is not None:
                messaging_end_user_id = v
                break

    def _aliased(identity_key: str) -> Optional[str]:
        """Resolve an identity field via its tag-name fallback chain.

        Parameter name intentionally avoids shadowing `dataclasses.field`.
        """
        for tag_key in _TAG_KEY_ALIASES[identity_key]:
            v = tag_first.get(tag_key)
            if v is not None:
                return v
        return None

    # Expose VariableText__c bootstrap variables. Production messaging
    # sessions leave this NOT_SET; Builder Previewer populates it with
    # test-harness keys (__resolved_locale__, __supports_result_display__,
    # etc.). Surfacing this is what makes channel-mode visible in the
    # renderer.
    messaging_session_id = _harvest_str(session_row.get("ssot__RelatedMessagingSessionId__c"))
    voice_call_id = _harvest_str(session_row.get("ssot__RelatedVoiceCallId__c"))
    bootstrap_variables = _parse_bootstrap_variables(
        session_row.get("ssot__VariableText__c")
    )

    # Derive a `mode` field. ssot__AiAgentChannelType__c is identical for
    # MIAW production and Builder Previewer (`SCRT2 - EmbeddedMessaging`);
    # we have to look at related-id population and bootstrap_variables to
    # tell them apart.
    mode = _derive_mode(messaging_session_id, voice_call_id, bootstrap_variables)

    # `voice_call_id` + `individual_id` are null on EmbeddedMessaging sessions.
    # They populate on authenticated channels (voice, Experience Cloud with
    # linked Individual). Kept for schema parallelism with messaging_session_id.
    return {
        "org_id": org_id,
        "platform_user_id": platform_user_id,
        "planner_id": planner_id,
        "bot_version_id": bot_version_id,
        "app_type": app_type,
        "bot_id": tag_first.get("bot_id"),
        "bot_name": tag_first.get("bot_name"),
        "agent_api_name": _aliased("agent_api_name"),
        "agent_label": tag_first.get("agent_label"),
        "agent_version": _aliased("agent_version"),
        "agent_type": tag_first.get("agent_type"),
        "planner_name": tag_first.get("planner_name"),
        "planner_type": tag_first.get("planner_type"),
        "configured_model": tag_first.get("configured_model_name"),
        "messaging_session_id": messaging_session_id,
        "messaging_end_user_id": messaging_end_user_id,
        "voice_call_id": voice_call_id,
        "individual_id": _harvest_str(session_row.get("ssot__IndividualId__c")),
        "bootstrap_variables": bootstrap_variables,
        "mode": mode,
    }


# Test-harness bootstrap keys that are observed in Builder Previewer sessions
# but NOT in MIAW production. The presence of any of these in
# `ssot__VariableText__c` is the strongest at-rest signal that a session was
# run through the Previewer rather than against a real customer messaging
# session. Listed here as a frozenset so it's read-only at module level.
# Builder Previewer adds these keys to ssot__VariableText__c at session
# bootstrap; MIAW production sessions don't seed them. Used by _derive_mode
# to distinguish previewer runs from real customer messaging sessions.
_BUILDER_PREVIEWER_INDICATOR_KEYS: frozenset[str] = frozenset({
    "__resolved_locale__",
    "__locale_instruction__",
    "__supports_result_display__",
    "__show_tool_results_invoked__",
})


def _parse_bootstrap_variables(raw: Any) -> Optional[dict]:
    """Parse `ssot__VariableText__c` defensively.

    On real sessions this field can be:
      - missing / None / NOT_SET / UNSET_VALUE         → returns None
      - well-formed JSON (Builder Previewer)            → returns the dict
      - HTML-entity-encoded JSON (some surfaces emit
        the `&quot;`-escaped form)                      → unescaped, returns the dict
      - truncated or malformed JSON                     → returns
        `{"_parse_error": True, "_raw": <first 200 chars>}` so the renderer
        can still flag that a bootstrap exists, just not parseable.

    Returns None for the empty cases so the caller can treat None as
    "no bootstrap" without distinguishing missing from sentinel.
    """
    if raw is None:
        return None
    s = html.unescape(str(raw)).strip()
    if not s or s in _NOT_SET or s in ("NOT_SET", "UNSET_VALUE"):
        return None
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return {"_parse_error": True, "_raw": s[:200]}
    # Defensive: VariableText__c is documented as a JSON object; if a future
    # version emits a JSON array or scalar, surface it under `_raw` rather
    # than letting downstream code crash on `.get()`.
    if not isinstance(parsed, dict):
        return {"_parse_error": True, "_raw": s[:200]}
    return parsed


def _derive_mode(
    messaging_session_id: Optional[str],
    voice_call_id: Optional[str],
    bootstrap_variables: Optional[dict],
) -> str:
    """Distinguish MIAW production from Builder Previewer from voice.

    `ssot__AiAgentChannelType__c` is identical (`SCRT2 - EmbeddedMessaging`)
    for MIAW and Builder Previewer — useless for distinguishing them. The
    real signals, in priority order:

    1. `ssot__RelatedVoiceCallId__c` set ↔ voice channel.
    2. `ssot__RelatedMessagingSessionId__c` set ↔ MIAW production
       (a real MessagingSession record exists).
    3. `RelatedMessagingSessionId__c` NOT_SET AND bootstrap_variables
       contains test-harness keys ↔ Builder Previewer.
    4. None of the above ↔ unknown (e.g. headless API runs, agent script
       previewer cases that don't seed VariableText__c).

    Return a stable enum string the renderer can match on.
    """
    if voice_call_id:
        return "voice"
    if messaging_session_id:
        return "production_messaging"
    if isinstance(bootstrap_variables, dict):
        if set(bootstrap_variables) & _BUILDER_PREVIEWER_INDICATOR_KEYS:
            return "builder_previewer"
    return "unknown"


def _declared_binding_pass(rows: Dict[str, List[dict]], idx: Indexes) -> BindingResults:
    """Walk every step; claim GWs reachable via the declared chain.

    Returns BindingResults(declared_gw_ids, declared_steps_with_gw,
    step_id_to_gw_id, declared_collisions). `declared_steps_with_gw` is a
    frozenset so downstream consumers can't accidentally mutate it.
    `step_id_to_gw_id[step_id]` is the GW id when declared, or None when this
    step's declared GW was already claimed by an earlier step (collision sentinel).
    `declared_collisions` is the aggregate count of collision-sentinel entries.
    """
    declared_gw_ids: set = set()
    declared_steps_with_gw: set = set()
    step_id_to_gw_id: Dict[str, Optional[str]] = {}
    for step in rows.get("steps", []):
        gw_req = _declared_gw_for_step(
            step, idx.generations_by_id, idx.gw_resp_by_resp_id, idx.gw_req_by_id)
        if gw_req is None:
            continue
        gw_id = gw_req["gatewayRequestId__c"]
        if gw_id in declared_gw_ids:
            # Collision: second+ step reaches a GW already claimed.
            step_id_to_gw_id[step["ssot__Id__c"]] = None
            continue
        declared_gw_ids.add(gw_id)
        declared_steps_with_gw.add(step["ssot__Id__c"])
        step_id_to_gw_id[step["ssot__Id__c"]] = gw_id
    return BindingResults(
        declared_gw_ids=declared_gw_ids,
        declared_steps_with_gw=frozenset(declared_steps_with_gw),
        step_id_to_gw_id=step_id_to_gw_id,
        declared_collisions=sum(1 for v in step_id_to_gw_id.values() if v is None),
    )


def _build_step_view(step: dict, idx: Indexes, dispatch: PolymorphicSplits,
                     step_id_to_gw_id: Dict[str, Optional[str]],
                     build_gw) -> dict:
    """Emit one Step view, including its Generation and (if declared) GatewayRequest.

    `build_gw` is a `functools.partial` pre-bound with `idx`/`dispatch`
    (see `assemble()`); call sites only supply `gw_req`, `binding_method`,
    and optionally `bound_step_id`.
    """
    sid_step = step["ssot__Id__c"]
    gen_id = step.get("ssot__GenerationId__c")
    gen = idx.generations_by_id.get(gen_id) if gen_id not in _NOT_SET else None
    generation_view = _build_generation_view(
        gen, idx.quality_by_parent, dispatch.categories_by_generation,
        dispatch.categories_by_quality, idx.feedback_by_gen,
        idx.feedback_details_by_parent, dispatch.gw_records_by_feedback,
    ) if gen is not None else None

    gw_id = step_id_to_gw_id.get(sid_step)
    gw_view = None
    collision_flag = gw_id is None and sid_step in step_id_to_gw_id
    if gw_id is not None:
        gw_view = build_gw(idx.gw_req_by_id[gw_id], "declared")

    # Mirror the bound gateway_request's model identifier onto the step
    # itself so renderers can show "LLM_STEP <name> · <model>" without
    # dereferencing the nested gateway view. The mirror is None when no
    # gateway_request is bound (declared chain didn't reach, or the STDM
    # exporter dropped writes — see the `gateway_requests_dropped_by_stdm`
    # session_shape).
    step_model_name = gw_view.get("model") if gw_view else None

    step_view: Dict[str, Any] = {
        "id": sid_step,
        "type": step.get("ssot__AiAgentInteractionStepType__c"),
        "name": step.get("ssot__Name__c"),
        "start_ts": step.get("ssot__StartTimestamp__c"),
        "end_ts": step.get("ssot__EndTimestamp__c"),
        "error_text": _clean(step.get("ssot__ErrorMessageText__c")),
        "model_name": step_model_name,
        "generation": generation_view,
        "gateway_request": gw_view,
    }
    if collision_flag:
        step_view["gateway_request_collision"] = True
    return step_view


def _build_message_view(m: dict, participant_role_by_id: Dict[str, str]) -> dict:
    mtype = m.get("ssot__AiAgentInteractionMessageType__c")
    pid = m.get("ssot__AiAgentSessionParticipantId__c")
    role = participant_role_by_id.get(pid)
    if role is None:
        role = "USER" if mtype == "Input" else "AGENT" if mtype == "Output" else None
    return {
        "message_id": m.get("ssot__Id__c"),
        "type": mtype,
        "role": role,
        "participant_id": pid,
        "text": m.get("ssot__ContentText__c"),
        "content_type": m.get("ssot__AiAgentInteractionMsgContentType__c"),
        "modality": m.get("Modality__c"),
        "ts": m.get("ssot__MessageSentTimestamp__c"),
    }


def _build_interaction_view(interaction: dict, rows: Dict[str, List[dict]],
                            idx: Indexes, dispatch: PolymorphicSplits,
                            binding: BindingResults,
                            build_gw) -> Tuple[dict, BinderCtx]:
    """Emit one Interaction view plus its BinderCtx.

    Returns (view, binder_ctx). Binder scratch state lives in the `BinderCtx`
    and is keyed externally by `iid`; it never touches the emitted view, so
    it can't leak into `dc._session_tree.json`. `build_gw` is the
    `functools.partial` from `assemble()`.
    """
    iid = interaction["ssot__Id__c"]
    trace_id = _extract_trace_id(interaction)

    steps_sorted = sorted(
        idx.steps_by_interaction.get(iid, []),
        key=lambda s: (s.get("ssot__StartTimestamp__c") or "", s.get("ssot__Id__c") or ""))
    step_views = [_build_step_view(s, idx, dispatch, binding.step_id_to_gw_id, build_gw)
                  for s in steps_sorted]

    # Step windows consumed only by _ts_window_pass via the parallel BinderCtx.
    steps_with_ts: List[Tuple[dict, Optional[datetime], Optional[datetime]]] = [
        (s, _ts(s.get("ssot__StartTimestamp__c")), _ts(s.get("ssot__EndTimestamp__c")))
        for s in steps_sorted if _ts(s.get("ssot__StartTimestamp__c")) is not None
    ]

    messages_sorted = sorted(
        idx.messages_by_interaction.get(iid, []),
        key=lambda r: (r.get("ssot__MessageSentTimestamp__c") or "",
                       r.get("ssot__Id__c") or ""))
    msg_views = [_build_message_view(m, idx.participant_role_by_id)
                 for m in messages_sorted]

    view = {
        "id": iid,
        "type": interaction.get("ssot__AiAgentInteractionType__c"),
        "topic": _clean(interaction.get("ssot__TopicApiName__c")),
        "trace_id": trace_id,
        "start_ts": interaction.get("ssot__StartTimestamp__c"),
        "end_ts": interaction.get("ssot__EndTimestamp__c"),
        "messages": msg_views,
        "telemetry_spans": [s for s in rows.get("telemetry_spans", [])
                            if s.get("ssot__TelemetryTrace__c") == trace_id],
        "steps": step_views,
        "timestamp_bound_gateway_calls": [],  # appended by _ts_window_pass
        "tag_associations": dispatch.tag_assoc_by_interaction.get(iid, []),
    }
    binder_ctx = BinderCtx(
        start_ts=_ts(interaction.get("ssot__StartTimestamp__c")),
        end_ts=_ts(interaction.get("ssot__EndTimestamp__c")),
        steps_with_ts=steps_with_ts,
        reserved_step_ids=binding.declared_steps_with_gw,
    )
    return view, binder_ctx


def _ts_window_pass(interactions_view: List[dict],
                    binders: Dict[str, BinderCtx],
                    idx: Indexes,
                    binding: BindingResults,
                    build_gw) -> Tuple[List[dict], dict]:
    """Place every chain-orphan GW via timestamp-window, or into unbound[].

    Reads per-interaction binder state from the parallel `binders` dict keyed
    by `iv["id"]` — never from the view itself. Mutates `interactions_view`
    in place only to append to `timestamp_bound_gateway_calls[]` (an emission
    field, pre-initialized to `[]` in `_build_interaction_view`).

    Returns (unbound_gw_calls, gw_binding_counts).
    """
    unbound: List[dict] = []
    counts = {
        "declared": len(binding.declared_gw_ids),
        "timestamp_window": 0,
        "unbound": 0,
        "declared_collisions": binding.declared_collisions,
    }
    for gw_id, gw_req in idx.gw_req_by_id.items():
        if gw_id in binding.declared_gw_ids:
            continue
        placed = False
        for iv in interactions_view:
            bctx = binders[iv["id"]]
            placement, bound_step_id = _bind_ts_window(
                gw_req,
                bctx.steps_with_ts,
                (bctx.start_ts, bctx.end_ts),
                bctx.reserved_step_ids,
            )
            if placement in ("step", "interaction"):
                iv["timestamp_bound_gateway_calls"].append(
                    build_gw(gw_req, "timestamp_window", bound_step_id=bound_step_id))
                counts["timestamp_window"] += 1
                placed = True
                break
        if not placed:
            unbound.append(build_gw(gw_req, "unbound"))
            counts["unbound"] += 1

    # Defense in depth: if anyone reintroduces the binder-cache-on-view
    # pattern in a future edit, this catches it before the tree ever writes.
    assert not any(k.startswith("_") for iv in interactions_view for k in iv), \
        "binder scratch state leaked into interaction view — do not stash on the view dict"

    return unbound, counts


def _build_moments_view(rows: Dict[str, List[dict]], dispatch: PolymorphicSplits) -> List[dict]:
    """session.moments[] with interaction_ids[] back-refs derived from MomentInteraction."""
    by_moment: Dict[str, List[str]] = defaultdict(list)
    for mi in rows.get("moment_interactions", []):
        mid = mi.get("ssot__AiAgentMomentId__c")
        iid = mi.get("ssot__AiAgentInteractionId__c")
        if mid not in _NOT_SET and iid not in _NOT_SET:
            by_moment[mid].append(iid)

    moments_sorted = sorted(
        rows.get("moments", []),
        key=lambda r: (r.get("ssot__StartTimestamp__c") or "", r.get("ssot__Id__c") or ""))
    return [
        {
            "moment_id": m.get("ssot__Id__c"),
            "agent_api_name": _clean(m.get("ssot__AiAgentApiName__c")),
            "agent_version": _clean(m.get("ssot__AiAgentVersionApiName__c")),
            "request_summary_text": _clean(m.get("ssot__RequestSummaryText__c")),
            "response_summary_text": _clean(m.get("ssot__ResponseSummaryText__c")),
            "interaction_ids": sorted(by_moment.get(m.get("ssot__Id__c"), [])),
            "start_ts": m.get("ssot__StartTimestamp__c"),
            "end_ts": m.get("ssot__EndTimestamp__c"),
            "tag_associations": dispatch.tag_assoc_by_moment.get(m.get("ssot__Id__c"), []),
        }
        for m in moments_sorted
    ]


def _build_participants_view(rows: Dict[str, List[dict]]) -> List[dict]:
    return [
        {
            "participant_id": p.get("ssot__Id__c"),
            "role": p.get("ssot__AiAgentSessionParticipantRole__c"),
            "agent_api_name": _clean(p.get("ssot__AiAgentApiName__c")),
            "agent_version": _clean(p.get("ssot__AiAgentVersionApiName__c")),
            "agent_type": _clean(p.get("ssot__AiAgentType__c")),
        }
        for p in sorted(
            rows.get("participants", []),
            key=lambda r: (r.get("ssot__StartTimestamp__c") or "", r.get("ssot__Id__c") or ""))
    ]


def _build_counts(rows: Dict[str, List[dict]], dispatch: PolymorphicSplits,
                  binding_counts: dict,
                  manifest: dict, collisions: List[dict],
                  parse_warnings: List[str]) -> dict:
    int_by_type: Dict[str, int] = defaultdict(int)
    step_by_type: Dict[str, int] = defaultdict(int)
    for i in rows.get("interactions", []):
        int_by_type[i.get("ssot__AiAgentInteractionType__c")] += 1
    for s in rows.get("steps", []):
        step_by_type[s.get("ssot__AiAgentInteractionStepType__c")] += 1

    return {
        "interactions_total": len(rows.get("interactions", [])),
        "interactions_turn": int_by_type.get("TURN", 0),
        "interactions_session_end": int_by_type.get("SESSION_END", 0),
        "steps_total": len(rows.get("steps", [])),
        "steps_by_type": {
            k: step_by_type.get(k, 0) for k in
            ("LLM_STEP", "ACTION_STEP", "TOPIC_STEP", "TRUST_GUARDRAILS_STEP", "SESSION_END")
        },
        "generations": len(rows.get("generations", [])),
        "gateway_requests": len(rows.get("gateway_requests", [])),
        "gateway_responses": len(rows.get("gateway_responses", [])),
        "gateway_metadata": len(rows.get("gateway_request_metadata", [])),
        "gateway_llm": len(rows.get("gateway_request_llm", [])),
        "gateway_records_grounded": sum(len(v) for v in dispatch.gw_records_by_gw_req.values()),
        "gateway_records_feedback": sum(len(v) for v in dispatch.gw_records_by_feedback.values()),
        "feedback": len(rows.get("feedback", [])),
        "audit_chain_1to1_ok": (
            len(rows.get("gateway_requests", [])) == len(rows.get("gateway_responses", []))
        ),
        "gw_binding": binding_counts,
        "session_shape": manifest.get("session_shape", "unknown"),
        "pk_collisions": collisions,
        "parse_warnings": parse_warnings,
    }


def assemble(sid: str) -> Tuple[dict, Path]:
    """Orchestrate: load → index → dispatch → bind → build views → counts → tree.

    Returns (tree, session_dir). The session_dir is resolved by
    ``_find_session_dir`` (via breadcrumb or glob) and passed back so
    the caller can write ``dc._session_tree.json`` next to the inputs
    without re-scanning the disk.
    """
    manifest, rows, parse_warnings, session_dir = _load_all(sid)

    # Short-circuit: session row not found.
    sessions = rows.get("sessions", [])
    if not sessions:
        return _minimal_tree_session_not_found(sid, manifest, parse_warnings), session_dir

    # Short-circuit: STDM Interaction/Step/Message DMOs haven't materialized yet
    # (gateway_requests present, interactions/steps empty). Render the gateway
    # chain directly instead of silently emitting an empty tree.
    if manifest.get("session_shape") == "interactions_not_materialized_yet":
        return _assemble_gateway_direct(sid, rows, manifest, parse_warnings), session_dir

    collisions: List[dict] = []
    # Phase 1: independent bags.
    idx = _build_indexes(rows, collisions)
    dispatch = _dispatch_polymorphic(rows, idx)
    catalog = _filter_catalog(rows)
    # Phase 2: derived bag that depends on idx.
    binding = _declared_binding_pass(rows, idx)

    # Bind the invariant gw-view args once; call sites supply only the varying ones.
    build_gw = functools.partial(_build_gw_view, idx=idx, dispatch=dispatch)

    # Build per-Interaction views + parallel binder state (sorted by start_ts).
    interactions_view: List[dict] = []
    binders: Dict[str, BinderCtx] = {}
    for interaction in sorted(
            rows.get("interactions", []),
            key=lambda r: (r.get("ssot__StartTimestamp__c") or "",
                           r.get("ssot__Id__c") or "")):
        view, bctx = _build_interaction_view(interaction, rows, idx, dispatch, binding, build_gw)
        interactions_view.append(view)
        binders[view["id"]] = bctx

    # Timestamp-window fallback; mutates interactions_view only via
    # timestamp_bound_gateway_calls[].append.
    unbound_gw_calls, gw_binding_counts = _ts_window_pass(
        interactions_view, binders, idx, binding, build_gw)

    session_row = sessions[0]
    session_identity = _build_session_identity(rows, manifest)
    # `org_id_15` is the canonical 15-char slice used by path helpers.
    # Prefer the manifest-stamped value (resolved in wave 1a of fetch_dc
    # from sessions[0].ssot__InternalOrganizationId__c); fall back to
    # slicing session_identity.org_id (the 18-char form from
    # gateway_requests) when the manifest is missing the field (older
    # artifacts predate the manifest stamp).
    org_id_15 = manifest.get("org_id_15")
    if not org_id_15 and session_identity.get("org_id"):
        org_id_15 = session_identity["org_id"][:15]
    session_identity["org_id_15"] = org_id_15

    # Top-level identity block — canonical location for the 3 segments
    # needed to name the session dir. Richer identity fields live under
    # `session.identity` as before.
    # Promote richer values from `session_identity` when the manifest carries
    # placeholders (notably ``agent_version="v0"`` from the MyAgent
    # fallback in fetch_dc.py:570-597) — without this, the top-level block
    # diverges from `session.identity` in the same JSON file.
    top_identity = _reconcile_top_identity(manifest, session_identity, org_id_15)

    return {
        "identity": top_identity,
        "session": {
            "id": sid,
            "_schema_version": 1,
            "org": {
                "alias": manifest.get("org_alias"),
                "instance_url": manifest.get("instance_url"),
            },
            "identity": session_identity,
            "start_ts": session_row.get("ssot__StartTimestamp__c"),
            "end_ts": session_row.get("ssot__EndTimestamp__c"),
            "end_type": _resolve_end_type(session_row, rows),
            "channel": _harvest_str(session_row.get("ssot__AiAgentChannelType__c")),
            "participants": _build_participants_view(rows),
            "moments": _build_moments_view(rows, dispatch),
            "interactions": interactions_view,
            "session_tag_associations": dispatch.tag_assoc_session,
            "unbound_gateway_calls": unbound_gw_calls,
            "counts": _build_counts(rows, dispatch, gw_binding_counts,
                                    manifest, collisions, parse_warnings),
        },
        "catalog": {
            "agents_observed": catalog.agents_observed,
            "tag_definitions": catalog.tag_definitions,
            "tag_definition_associations": catalog.tag_definition_associations,
            "tags": catalog.tags,
        },
        "_doc": (
            "Assembled from "
            "DATA_ROOT/<org>/<agent>__<ver>/<sid>/dc.*.json. "
            "See dc._session_manifest.json for per-query counts and empty reasons. "
            "Contract: references/dc_pipeline_contract.md."
        ),
    }, session_dir


def _build_generation_view(gen: dict,
                           quality_by_parent: Dict[str, List[dict]],
                           categories_by_generation: Dict[str, List[dict]],
                           categories_by_quality: Dict[str, List[dict]],
                           feedback_by_gen: Dict[str, List[dict]],
                           feedback_details_by_parent: Dict[str, List[dict]],
                           gw_records_by_feedback: Dict[str, List[dict]]) -> dict:
    gen_id = gen["generationId__c"]
    # Quality rows with their TOXICITY sub-categories nested.
    quality_rows = []
    for q in quality_by_parent.get(gen_id, []):
        q_view = dict(q)
        q_view["_toxicity_subcategories"] = categories_by_quality.get(q.get("id__c"), [])
        quality_rows.append(q_view)

    # Feedback rows with details + feedback-attachment records nested.
    feedback_rows = []
    for fb in feedback_by_gen.get(gen_id, []):
        fid = fb.get("feedbackId__c")
        feedback_rows.append({
            "feedback_id": fid,
            "feedback": fb.get("feedback__c"),
            "action": fb.get("action__c"),
            "details": feedback_details_by_parent.get(fid, []),
            "records": gw_records_by_feedback.get(fid, []),
        })

    return {
        "generation_id": gen_id,
        "response_id": _clean(gen.get("generationResponseId__c")),
        "response_text": gen.get("responseText__c"),
        "masked_response_text": gen.get("maskedResponseText__c"),
        "response_parameters": gen.get("responseParameters__c"),
        "feature": _clean(gen.get("feature__c")),
        "quality": quality_rows,
        "categories": categories_by_generation.get(gen_id, []),
        "feedback": feedback_rows,
    }


_STDM_LAG_NOTE = (
    "Interaction/Step/Message DMOs materialize on a separate cadence from "
    "Gateway DMOs. For fresh sessions this view reflects the gateway chain "
    "directly. Re-run in 24–72 hours for the full hierarchical trace."
)


def _assemble_gateway_direct(sid: str, rows: Dict[str, List[dict]],
                              manifest: dict,
                              parse_warnings: List[str]) -> dict:
    """Build a gateway-chain-only tree for sessions whose STDM hierarchy hasn't materialized.

    Mirrors ``_minimal_tree_session_not_found`` in shape, but populates a
    ``session.gateway_chain[]`` harvested directly from ``gateway_requests``
    joined to ``gateway_request_tags`` / ``gateway_request_metadata`` /
    ``gateway_responses``. ``session.interactions`` is an explicit empty list
    so consumers that walk it simply no-op.

    The sentinel ``_source = "gateway_direct"`` is consumed by
    ``render_dc._render_gateway_direct``.
    """
    sessions = rows.get("sessions", [])
    session_row = sessions[0] if sessions else {}

    # Reuse the canonical identity harvester — same tag-alias fallbacks,
    # same normalization — and apply the same org_id_15 fallback as the
    # happy path so the top-level identity block is consistent across shapes.
    session_identity = _build_session_identity(rows, manifest)
    org_id_15 = manifest.get("org_id_15")
    if not org_id_15 and session_identity.get("org_id"):
        org_id_15 = session_identity["org_id"][:15]
    session_identity["org_id_15"] = org_id_15

    # Same placeholder-promotion policy as the happy path — see
    # `_reconcile_top_identity` for why we don't trust the manifest blindly.
    top_identity = _reconcile_top_identity(manifest, session_identity, org_id_15)

    # Group the child DMOs by parent once so the per-request loop stays O(n).
    tags_by_req: Dict[str, List[dict]] = _groupby(
        rows.get("gateway_request_tags", []), "parent__c")
    md_by_req: Dict[str, List[dict]] = _groupby(
        rows.get("gateway_request_metadata", []), "parent__c")
    resp_by_req: Dict[str, List[dict]] = _groupby(
        rows.get("gateway_responses", []), "generationRequestId__c")

    # Deterministic order: sort by (timestamp__c, gatewayRequestId__c) so
    # repeat runs on the same inputs produce byte-identical output.
    gw_sorted = sorted(
        rows.get("gateway_requests", []),
        key=lambda r: (r.get("timestamp__c") or "",
                       r.get("gatewayRequestId__c") or ""),
    )

    gateway_chain: List[dict] = []
    for gw in gw_sorted:
        gw_id = gw.get("gatewayRequestId__c")
        # sf__Id (platform row id) isn't harvested by fetch_dc; the logical
        # PK is gatewayRequestId__c. Keep both keys on the view so readers
        # can lift either without re-joining.
        sf_id = gw.get("sf__Id")

        # timestamp: prefer the columns named in the change-request
        # (requestTimeStamp__c, createdAt__c), then fall back to the
        # documented column (timestamp__c in references/dc_dmo_fields.md).
        timestamp = (
            _clean(gw.get("requestTimeStamp__c"))
            or _clean(gw.get("createdAt__c"))
            or _clean(gw.get("timestamp__c"))
        )

        # Tag-driven fields. Use _harvest_str for html-unescape + quote-strip —
        # same normalizer _build_session_identity uses on tag values.
        tag_first: Dict[str, Optional[str]] = {}
        for t in sorted(
                tags_by_req.get(gw_id, []),
                key=lambda r: (r.get("tag__c") or "",
                               r.get("tagValue__c") or "")):
            k = t.get("tag__c")
            if not k or k in tag_first:
                continue
            tag_first[k] = _harvest_str(t.get("tagValue__c"))

        # Prompt-template name: prefer the direct column on the request;
        # fall back to the tag alias used by older agent builds.
        prompt_template_dev_name = (
            _clean(gw.get("promptTemplateDevName__c"))
            or tag_first.get("prompt_template_dev_name")
        )
        # `feature` likewise prefers the typed column, falls back to tag.
        feature = _clean(gw.get("feature__c")) or tag_first.get("feature")

        # Response side — take the first by response timestamp. 1:1 invariant
        # holds on every live session we've observed, but defend against the
        # in-flight-call edge case by sorting deterministically.
        responses_sorted = sorted(
            resp_by_req.get(gw_id, []),
            key=lambda r: (r.get("timestamp__c") or "",
                           r.get("generationResponseId__c") or ""),
        )
        response_view: Optional[dict] = None
        if responses_sorted:
            resp = responses_sorted[0]
            response_view = {
                "timestamp": _clean(resp.get("timestamp__c")),
                "finish_reason": _parse_finish_reason_params(resp.get("parameters__c")),
            }

        gateway_chain.append({
            "gateway_request_id": gw_id,
            "sf_id": sf_id,
            "timestamp": timestamp,
            "model": _clean(gw.get("model__c")),
            "provider": _clean(gw.get("provider__c")),
            "prompt_template_dev_name": prompt_template_dev_name,
            "feature": feature,
            "prompt_tokens": gw.get("promptTokens__c"),
            "completion_tokens": gw.get("completionTokens__c"),
            "total_tokens": gw.get("totalTokens__c"),
            # Raw prompt is authoritative on disk (dc.gateway_requests.json);
            # the 64 KB display cap lives in the render layer, not here.
            "prompt_text": gw.get("prompt__c"),
            "metadata": md_by_req.get(gw_id, []),
            "tags": tags_by_req.get(gw_id, []),
            "response": response_view,
        })

    return {
        "identity": top_identity,
        "_source": "gateway_direct",
        "session": {
            "id": sid,
            "_schema_version": 1,
            "org": {
                "alias": manifest.get("org_alias"),
                "instance_url": manifest.get("instance_url"),
            },
            "identity": session_identity,
            "start_ts": session_row.get("ssot__StartTimestamp__c"),
            "end_ts": session_row.get("ssot__EndTimestamp__c"),
            "end_type": _resolve_end_type(session_row, rows),
            "channel": _harvest_str(session_row.get("ssot__AiAgentChannelType__c")),
            "participants": _build_participants_view(rows),
            # Explicit empty list — downstream consumers walk this and must
            # no-op safely when STDM hasn't materialized yet.
            "interactions": [],
            "gateway_chain": gateway_chain,
            "_stdm_lag_note": _STDM_LAG_NOTE,
            "counts": {
                "session_shape": manifest.get("session_shape",
                                              "interactions_not_materialized_yet"),
                "gateway_requests": len(rows.get("gateway_requests", [])),
                "gateway_responses": len(rows.get("gateway_responses", [])),
                "gateway_metadata": len(rows.get("gateway_request_metadata", [])),
                "gateway_tags": len(rows.get("gateway_request_tags", [])),
                "interactions_total": 0,
                "steps_total": 0,
                "parse_warnings": parse_warnings,
            },
        },
        "_doc": (
            f"Session {sid}: STDM Interaction/Step/Message DMOs have not "
            "materialized yet (they lag Gateway DMOs by hours to days). "
            "Tree carries the gateway chain harvested directly from "
            "GenAIGatewayRequest + related audit DMOs. Re-run fetch_dc.py "
            "in 24–72h once the STDM hierarchy has caught up for the full "
            "hierarchical trace."
        ),
    }


def _parse_finish_reason_params(parameters: Optional[str]) -> Optional[str]:
    """Lift finish_reason out of GatewayResponse.parameters__c.

    The field arrives HTML-escaped and the finish_reason value itself is
    often wrapped in escaped quotes (e.g. `\\"stop\\"`). Mirrors
    ``render_dc._parse_finish_reason`` but against the gateway-response
    parameters column rather than Generation.responseParameters__c.
    """
    if not parameters:
        return None
    try:
        decoded = html.unescape(parameters)
        parsed = json.loads(decoded)
    except (ValueError, TypeError):
        return None
    raw = parsed.get("finish_reason") if isinstance(parsed, dict) else None
    if not isinstance(raw, str):
        return None
    return raw.replace("\\", "").strip('"').strip() or None


def _minimal_tree_session_not_found(sid: str, manifest: dict,
                                     parse_warnings: List[str]) -> dict:
    # Note: deliberately does NOT include `session.identity` — harvest
    # sources (gateway_requests, gateway_request_tags, sessions[0],
    # participants) are all empty on this path. Renderer's minimal-tree
    # branch must handle absent identity. DOES include _schema_version so
    # the renderer's version check doesn't warn on every not-found session.
    #
    # Top-level `identity` still carries the manifest-stamped (org, agent,
    # version) when available — the session dir already exists under that
    # identity or the manifest couldn't have been read. Breadcrumb readers
    # depend on this block being present on EVERY tree, not just
    # full-populated ones.
    return {
        "identity": {
            "org_id_15": manifest.get("org_id_15"),
            "agent_api_name": manifest.get("agent_api_name"),
            "agent_version": manifest.get("agent_version"),
        },
        "session": {
            "id": sid,
            "_schema_version": 1,
            "org": {
                "alias": manifest.get("org_alias"),
                "instance_url": manifest.get("instance_url"),
            },
            "counts": {
                "session_shape": manifest.get("session_shape", "session_not_found"),
                "parse_warnings": parse_warnings,
            },
        },
        "_doc": (
            f"Session {sid} did not resolve in Data Cloud "
            "(sessions.json returned 0 rows). Check the session id, or wait for "
            "STDM materialization. No interactions, catalog, or audit rows available."
        ),
    }


# ---- public entry points --------------------------------------------------

def main_for_session(sid: str) -> int:
    """Called by fetch_dc.py's auto-run hook and by `--session` CLI.

    Writes ``dc._session_tree.json`` into the session dir located by
    ``_find_session_dir`` (via breadcrumb / glob) — the caller does not
    need to know ``(org, agent, version)`` to invoke the assembler.
    """
    tree, session_dir = assemble(sid)
    tree_path = session_dir / "dc._session_tree.json"
    tree_path.write_text(json.dumps(tree, indent=2, sort_keys=True, default=str) + "\n")
    print(f"assemble_dc: wrote {tree_path}", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="assemble_dc.py",
        description="Assemble dc._session_tree.json for one session.",
    )
    ap.add_argument("--session", required=True,
                    help="AI-agent session UUID or MessagingSession id (0Mw...). "
                         "Messaging ids are resolved from disk "
                         "(DATA_ROOT/*/dc.sessions.json); run fetch_dc.py first "
                         "if the session hasn't been fetched yet.")
    # Runtime-agnostic path overrides; default to ~/.vibe/...
    from _shared.cli_override import add_cli_flags, apply_overrides
    add_cli_flags(ap)
    args = ap.parse_args()
    apply_overrides(args, caller_globals=globals())
    from resolve_session import resolve_disk_or_live
    sid = resolve_disk_or_live(args.session)
    return main_for_session(sid)


if __name__ == "__main__":
    sys.exit(main())
