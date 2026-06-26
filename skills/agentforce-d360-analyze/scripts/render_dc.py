"""Render dc._session_summary.md from dc._session_tree.json + dc._session_manifest.json.

Given `DATA_ROOT/<sid>/dc._session_tree.json` (produced by `scripts/assemble_dc.py`)
this module emits a human-readable `dc._session_summary.md`. Pure tree reader —
no raw DMO fetches, no joins. The `session.identity` sub-object on the tree
(added by the assembler) supplies all identity fields; everything else
(counts, trees, catalog) comes from the tree itself.

Output has 8 `##` sections:

  1. Session identity      — org/agent/bot/planner/session-start/end/duration
  2. ID reference          — full UUIDs for every ellipsized id in the tree
  3. Transcript            — narrative USER/AGENT text per TURN
  4. Complete hierarchical trace — tree with `+start + dur = +end` math
  5. Per-turn summary      — one row per interaction
  6. Session counts        — engineer-facing totals
  7. Empties diagnostics   — DMOs that returned 0 rows + reason
  8. Catalog (session-filtered)

Contract:
  - Pure in-memory compute over already-produced artifacts.
  - Reads DATA_ROOT/<sid>/dc._session_tree.json and dc._session_manifest.json.
  - UUIDs in the tree are truncated to first 8 chars + `…`; full forms
    live in the ID reference block.
  - Session-not-found trees render only Session identity + a note.
  - Tree schema version check: refuses incompatible versions, warns on
    missing version (backward compat).

Invocation:
    python3 scripts/render_dc.py --session <sid>
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_ROOT, paths


# ---- schema ---------------------------------------------------------------

_SUPPORTED_SCHEMA_VERSION = 1


# ---- timestamp / string helpers -------------------------------------------

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _fmt_offset(ts_iso: Optional[str], start_dt: Optional[datetime]) -> str:
    """Return '+12.345s' or '—' if timestamp is missing."""
    ts = _parse_iso(ts_iso)
    if ts is None or start_dt is None:
        return "—"
    return f"+{(ts - start_dt).total_seconds():.3f}s"


def _fmt_duration_ms(start_iso: Optional[str], end_iso: Optional[str]) -> str:
    s = _parse_iso(start_iso)
    e = _parse_iso(end_iso)
    if s is None or e is None:
        return "—"
    return f"{int((e - s).total_seconds() * 1000)}ms"


def _decode(s: Optional[str]) -> str:
    if not s:
        return ""
    return html.unescape(s).replace("\n", " ").strip()


def _truncate(s: Optional[str], n: int = 80) -> str:
    if not s:
        return "—"
    s = _decode(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _short(uid: Optional[str], keep: int = 8) -> str:
    """Truncate a UUID to `keep` chars + ellipsis. Full form lives in ID reference."""
    if not uid:
        return "—"
    return uid[:keep] + "…" if len(uid) > keep else uid


def _fmt_total_duration(start_iso: Optional[str], end_iso: Optional[str]) -> Optional[str]:
    s = _parse_iso(start_iso)
    e = _parse_iso(end_iso)
    if s is None or e is None:
        return None
    total_secs = (e - s).total_seconds()
    if total_secs >= 3600:
        h = int(total_secs // 3600)
        m = int((total_secs % 3600) // 60)
        return f"{h}h {m}m {total_secs % 60:.3f}s"
    if total_secs >= 60:
        m = int(total_secs // 60)
        return f"{m}m {total_secs % 60:.3f}s"
    return f"{total_secs:.3f}s"


# ---- session-end derivation ----------------------------------------------

def _derive_session_end(sess: dict) -> tuple[Optional[str], Optional[str]]:
    """Return (effective_end_iso, source_label).

    Contract §3.5 derivation:
      1. If `session.end_ts` is non-null → return it as-is (caller adds
         "✓ materialized" suffix).
      2. Else prefer a SESSION_END interaction's `start_ts`
         (label: "from SESSION_END interaction").
      3. Else fall back to the last TURN interaction's `end_ts`
         (or `start_ts` if end is null) (label: "session still open (last TURN)").
      4. Else `(None, None)`.
    """
    end_iso = sess.get("end_ts")
    if end_iso:
        return end_iso, None  # no derivation needed
    interactions = sess.get("interactions") or []
    # Prefer SESSION_END start_ts.
    for iv in interactions:
        if iv.get("type") == "SESSION_END" and iv.get("start_ts"):
            return iv["start_ts"], "from SESSION_END interaction"
    # Fall back to the last TURN (by interaction order; tree is already sorted).
    last_turn = None
    for iv in interactions:
        if iv.get("type") == "TURN":
            last_turn = iv
    if last_turn is not None:
        fallback = last_turn.get("end_ts") or last_turn.get("start_ts")
        if fallback:
            return fallback, "session still open (last TURN)"
    return None, None


# ---- section builders -----------------------------------------------------

# Channel-mode value → human cell. Annotated so the reader can tell at
# a glance why we believe the mode is
# what it is — `ssot__AiAgentChannelType__c` is identical for MIAW
# production and Builder Previewer, which makes it useless without the
# annotation.
_MODE_HINTS: dict[str, str] = {
    "production_messaging": "production_messaging  ←  inferred from RelatedMessagingSessionId",
    "builder_previewer":    "builder_previewer  ←  inferred from VariableText__c bootstrap keys",
    "voice":                "voice  ←  inferred from RelatedVoiceCallId",
    "unknown":              "unknown  ←  no signals (headless API, etc.)",
}


def _fmt_mode_cell(mode_value: str) -> str:
    """Format the `mode` field with a short why-this-value annotation."""
    return _MODE_HINTS.get(mode_value, mode_value)


# Channel values that flag a production messaging session. `VariableText__c`
# is expected to be NOT_SET on these — the bootstrap variables ride the
# messaging session record, not the AI session. Any other channel
# (E & O headless API, Builder Previewer, voice, unknown/integration)
# can also legitimately produce NOT_SET, but for a different reason
# (no bootstrap variables were attached at session start) — and we
# must not mislabel those as "production messaging path".
_MESSAGING_CHANNELS = frozenset({
    "SCRT2 - EmbeddedMessaging",
    "Messaging",
})


def _section_session_bootstrap(identity: dict, channel: Optional[str] = None) -> List[str]:
    """Render the `bootstrap_variables` block parsed from VariableText__c.

    Three states (all rendered as a small subtable so they don't clutter
    the main identity table):
      - None / NOT_SET → "no bootstrap variables for this session"
                         (with a messaging-path addendum only when the
                         session's `channel` is actually a messaging
                         channel — see `_MESSAGING_CHANNELS`).
      - parse error    → "_parse_error" with the raw prefix
      - populated      → key/value pairs sorted, plus a "Builder Previewer
                         indicators" tally derived from the same key set
                         used in `_derive_mode`.

    Empty section returned when bootstrap_variables is missing entirely
    (older artifacts predate the bootstrap-variables harvest).
    """
    if "bootstrap_variables" not in identity:
        return []  # older artifact: no bootstrap_variables harvested

    bootstrap = identity.get("bootstrap_variables")
    lines: List[str] = ["## Session bootstrap", ""]

    if bootstrap is None:
        if channel in _MESSAGING_CHANNELS:
            lines.append(
                "`ssot__VariableText__c` is `NOT_SET` — no bootstrap variables "
                "(production messaging path; messaging sessions don't carry VariableText)."
            )
        else:
            lines.append(
                "`ssot__VariableText__c` is `NOT_SET` — no bootstrap variables for this session."
            )
        lines.append("")
        return lines

    if isinstance(bootstrap, dict) and bootstrap.get("_parse_error"):
        raw = bootstrap.get("_raw") or ""
        lines.append("`ssot__VariableText__c` failed to parse as JSON:")
        lines.append("")
        lines.append("```")
        lines.append(raw)
        lines.append("```")
        lines.append("")
        return lines

    # Populated case.
    indicator_keys = {
        "__resolved_locale__",
        "__locale_instruction__",
        "__supports_result_display__",
        "__show_tool_results_invoked__",
    }
    present_indicators = sorted(set(bootstrap) & indicator_keys)
    indicator_cell = (
        "yes  ·  " + ", ".join(present_indicators)
        if present_indicators else "no"
    )

    lines.append("| Key | Value |")
    lines.append("|---|---|")
    for key in sorted(bootstrap):
        value = bootstrap[key]
        # Render lists / dicts compactly; keep strings/numbers/bools as-is.
        if isinstance(value, (list, dict)):
            value_repr = json.dumps(value)
        else:
            value_repr = str(value)
        # Pipe character would break the markdown table — escape.
        value_repr = value_repr.replace("|", "\\|")
        lines.append(f"| {key} | {value_repr} |")
    lines.append(f"| **Builder Previewer indicators** | {indicator_cell} |")
    lines.append("")
    return lines


def _compose_agent_cell(identity: dict) -> Optional[str]:
    """Build the human Agent cell from identity fields; drop None components."""
    parts: List[str] = []
    api_name = identity.get("agent_api_name")
    version = identity.get("agent_version")
    if api_name and version:
        parts.append(f"{api_name} {version}")
    elif api_name:
        parts.append(api_name)
    elif version:
        parts.append(version)
    label = identity.get("agent_label")
    if label:
        parts.append(f"— {label}" if parts else label)
    atype = identity.get("agent_type")
    if atype:
        parts.append(f"({atype})")
    return " ".join(parts) if parts else None


def _fmt_session_end_cell(effective_end_iso: Optional[str],
                          end_source: Optional[str],
                          raw_end_iso: Optional[str]) -> Optional[str]:
    """Compose the identity-table value for `Session end`.

    - Materialized end (`raw_end_iso` truthy)           → "<iso> ✓ materialized"
    - Derived end   (end_source truthy)                 → "<iso> (<source label>)"
    - Neither                                           → None (row is dropped)
    """
    if effective_end_iso is None:
        return None
    if raw_end_iso:
        return f"{effective_end_iso} ✓ materialized"
    if end_source:
        return f"{effective_end_iso} ({end_source})"
    return effective_end_iso


def _section_session_identity(sess: dict, effective_end_iso: Optional[str],
                              end_source: Optional[str]) -> List[str]:
    identity = sess.get("identity") or {}
    org = sess.get("org") or {}

    # `mode` is "production_messaging" / "builder_previewer" / "voice" /
    # "unknown" — derived in assemble_dc from RelatedMessagingSessionId +
    # RelatedVoiceCallId + bootstrap_variables because
    # ssot__AiAgentChannelType__c is identical for MIAW production and
    # Builder Previewer.
    mode_value = identity.get("mode")
    mode_cell = _fmt_mode_cell(mode_value) if mode_value else None

    rows_out = [
        ("Session id", sess.get("id")),
        ("Org id", identity.get("org_id")),
        ("Org alias", org.get("alias")),
        ("Instance URL", org.get("instance_url")),
        ("Channel", sess.get("channel")),
        ("Mode", mode_cell),
        ("App type", identity.get("app_type")),
        ("Agent", _compose_agent_cell(identity)),
        ("Bot id", identity.get("bot_id")),
        ("Bot name", identity.get("bot_name")),
        ("Bot version id", identity.get("bot_version_id")),
        ("Planner id", identity.get("planner_id")),
        ("Planner name", identity.get("planner_name")),
        ("Planner type", identity.get("planner_type")),
        ("Configured model", identity.get("configured_model")),
        ("Platform user id", identity.get("platform_user_id")),
        ("Messaging session id", identity.get("messaging_session_id")),
        ("Messaging end-user id", identity.get("messaging_end_user_id")),
        ("Voice call id", identity.get("voice_call_id")),
        ("Individual id", identity.get("individual_id")),
        ("Session start", sess.get("start_ts")),
        (
            "Session end",
            _fmt_session_end_cell(effective_end_iso, end_source, sess.get("end_ts")),
        ),
        ("End type", sess.get("end_type")),
        ("Total duration", _fmt_total_duration(sess.get("start_ts"), effective_end_iso)),
    ]
    lines: List[str] = ["## Session identity", "", "| Field | Value |", "|---|---|"]
    for label, value in rows_out:
        if value is None or value == "" or value == "—":
            continue
        lines.append(f"| {label} | {value} |")
    lines.append("")
    return lines


def _section_id_reference(sess: dict) -> List[str]:
    """Full-UUID lookup for every id the tree truncates."""
    lines: List[str] = [
        "## ID reference",
        "",
        "The tree truncates UUIDs to the first 8 chars + `…`. Look up the full "
        "form here. Ordered by type → first occurrence.",
        "",
        "```",
        f"session        = {sess.get('id')}",
        "",
    ]
    # Interactions
    lines.append("interactions:")
    for iv in sess.get("interactions", []):
        lines.append(
            f"  {iv.get('id')}   type={iv.get('type') or '?'}   "
            f"trace={iv.get('trace_id') or '—'}"
        )
    lines.append("")
    # Participants
    lines.append("participants:")
    for p in sess.get("participants", []):
        lines.append(
            f"  {p.get('participant_id') or '—'}   role={p.get('role') or '—'}   "
            f"agent={p.get('agent_api_name') or '—'}   version={p.get('agent_version') or '—'}   "
            f"type={p.get('agent_type') or '—'}"
        )
    lines.append("")

    # Steps, generations, gateway_requests, messages harvested from the tree.
    all_steps: List[tuple] = []
    all_gens: List[tuple] = []
    all_gws: List[tuple] = []
    all_msgs: List[tuple] = []
    for iv in sess.get("interactions", []):
        for m in iv.get("messages", []):
            if m.get("message_id"):
                all_msgs.append((m["message_id"], m.get("role") or m.get("type") or "?"))
        for st in iv.get("steps", []):
            if st.get("id"):
                all_steps.append((st["id"], st.get("type") or "?", st.get("name") or "—"))
            gen = st.get("generation")
            if gen and gen.get("generation_id"):
                all_gens.append((
                    gen["generation_id"],
                    gen.get("response_id") or "—",
                    gen.get("feature") or "—",
                ))
            gw = st.get("gateway_request")
            if gw and gw.get("gateway_request_id"):
                all_gws.append((
                    gw["gateway_request_id"], "declared",
                    gw.get("feature") or "—", gw.get("model") or "—",
                ))
        for tb in iv.get("timestamp_bound_gateway_calls", []):
            if tb.get("gateway_request_id"):
                all_gws.append((
                    tb["gateway_request_id"], "timestamp_window",
                    tb.get("feature") or "—", tb.get("model") or "—",
                ))
    for g in sess.get("unbound_gateway_calls", []):
        if g.get("gateway_request_id"):
            all_gws.append((
                g["gateway_request_id"], "unbound",
                g.get("feature") or "—", g.get("model") or "—",
            ))

    if all_steps:
        lines.append("steps:")
        for sid_, stype, sname in all_steps:
            lines.append(f"  {sid_}   type={stype}   name={sname}")
        lines.append("")
    if all_gens:
        lines.append("generations:")
        for gid, rid, feat in all_gens:
            lines.append(f"  {gid}   response_id={rid}   feature={feat}")
        lines.append("")
    if all_gws:
        lines.append("gateway_requests:")
        for gwid, bm, feat, model in all_gws:
            lines.append(f"  {gwid}   binding={bm}   feature={feat}   model={model}")
        lines.append("")
    if all_msgs:
        lines.append("messages:")
        for mid, role in all_msgs:
            lines.append(f"  {mid}   role={role}")
    lines.append("```")
    lines.append("")
    return lines


def _section_transcript(sess: dict, start_dt: Optional[datetime]) -> List[str]:
    turns = [iv for iv in sess.get("interactions", []) if iv.get("type") == "TURN"]
    if not turns:
        return []
    lines: List[str] = ["## Transcript", ""]
    for iv in turns:
        start_off = _fmt_offset(iv.get("start_ts"), start_dt)
        dur = _fmt_duration_ms(iv.get("start_ts"), iv.get("end_ts"))
        lines.append(f"**Interaction {_short(iv.get('id'))}** · {start_off} · {dur}")
        for m in iv.get("messages", []):
            role = m.get("role") or m.get("type") or "?"
            lines.append(f"> **{role}:** {_decode(m.get('text') or '')}")
        lines.append("")
    return lines


def _section_hierarchical_trace(sess: dict, start_dt: Optional[datetime],
                                effective_end_iso: Optional[str],
                                end_source: Optional[str]) -> List[str]:
    lines: List[str] = [
        "## Complete hierarchical trace",
        "",
        "Notation: `+Xs` = offset in seconds from session start. "
        "UUIDs are truncated to 8 chars + `…` for readability; "
        "full forms are in the **ID reference** block above.",
        "",
        "```",
    ]

    # Session header
    lines.append(f"SESSION {_short(sess.get('id'))}")
    start_iso = sess.get("start_ts")
    if start_iso:
        lines.append(f"│   Start +0.000s ({start_iso})")

    end_iso_raw = sess.get("end_ts")
    end_type = sess.get("end_type") or None
    outcome_s = end_type or "—"
    if not end_type and not end_iso_raw:
        outcome_s = "—  (session end not yet materialized in STDM)"
    display_end = end_iso_raw or effective_end_iso
    if display_end:
        label_suffix = f"  [{end_source}]" if end_source else ""
        lines.append(
            f"│   End   {_fmt_offset(display_end, start_dt)} ({display_end}){label_suffix}  "
            f"outcome={outcome_s}"
        )
    else:
        lines.append(f"│   End   — (session still open)  outcome={outcome_s}")
    lines.append("│")

    interactions = sess.get("interactions", [])
    for iv_idx, iv in enumerate(interactions):
        is_last_iv = iv_idx == len(interactions) - 1
        iv_branch = "└──" if is_last_iv else "├──"
        iv_cont = "    " if is_last_iv else "│   "

        iv_start_off = _fmt_offset(iv.get("start_ts"), start_dt)
        iv_end_off = _fmt_offset(iv.get("end_ts"), start_dt)
        iv_dur = _fmt_duration_ms(iv.get("start_ts"), iv.get("end_ts"))
        iv_type = iv.get("type") or "?"
        lines.append(
            f"{iv_branch} {iv_type}  {_short(iv.get('id'))}  "
            f"{iv_start_off} + {iv_dur} = {iv_end_off}"
        )

        topic = iv.get("topic")
        if topic:
            lines.append(f"{iv_cont}├── TOPIC: {topic}")

        for m in iv.get("messages", []):
            role = m.get("role") or m.get("type") or "?"
            m_off = _fmt_offset(m.get("ts"), start_dt) if m.get("ts") else "—"
            lines.append(f"{iv_cont}├── {role} message  {_short(m.get('message_id'))}  ts={m_off}")
            lines.append(f"{iv_cont}│   └── text: \"{_truncate(m.get('text'), 100)}\"")

        steps = iv.get("steps", [])
        tsbound = iv.get("timestamp_bound_gateway_calls", [])
        tsb_by_step: Dict[str, List[dict]] = {}
        tsb_interaction_level: List[dict] = []
        for tb in tsbound:
            bsid = tb.get("bound_to_step_id")
            if bsid:
                tsb_by_step.setdefault(bsid, []).append(tb)
            else:
                tsb_interaction_level.append(tb)

        remaining_groups: List[str] = []
        if steps:
            remaining_groups.append("steps")
        if tsb_interaction_level:
            remaining_groups.append("ts_il")

        for grp_idx, grp in enumerate(remaining_groups):
            grp_is_last = grp_idx == len(remaining_groups) - 1
            grp_branch = "└──" if grp_is_last else "├──"
            grp_cont = "    " if grp_is_last else "│   "
            if grp == "steps":
                lines.append(f"{iv_cont}{grp_branch} STEPS:")
                for st_idx, st in enumerate(steps):
                    lines.extend(_render_step(
                        st, st_idx, len(steps), iv_cont, grp_cont,
                        start_dt, tsb_by_step,
                    ))
            else:  # grp == "ts_il"
                lines.append(f"{iv_cont}{grp_branch} INTERACTION-LEVEL TIMESTAMP-BOUND GATEWAY CALLS:")
                for tb_idx, tb in enumerate(tsb_interaction_level):
                    tb_is_last = tb_idx == len(tsb_interaction_level) - 1
                    tb_branch = "└──" if tb_is_last else "├──"
                    lines.append(
                        f"{iv_cont}{grp_cont}{tb_branch} "
                        f"gateway_request [timestamp_window, interaction-level]  "
                        f"{_short(tb.get('gateway_request_id'))}  "
                        f"feature={tb.get('feature') or '—'}  "
                        f"model={tb.get('model') or '—'}"
                    )

        if not is_last_iv:
            lines.append("│")

    # Unbound gateway calls (session root level)
    ub = sess.get("unbound_gateway_calls", [])
    if ub:
        lines.append("")
        lines.append(
            f"UNBOUND GATEWAY CALLS ({len(ub)}) — neither declared chain "
            "nor timestamp window matched"
        )
        for i, g in enumerate(ub):
            branch = "└──" if i == len(ub) - 1 else "├──"
            lines.append(
                f"{branch} {_short(g.get('gateway_request_id'))}  "
                f"feature={g.get('feature') or '—'}  model={g.get('model') or '—'}"
            )

    lines.append("```")
    lines.append("")
    return lines


def _render_step(st: dict, st_idx: int, n_steps: int,
                 iv_cont: str, grp_cont: str,
                 start_dt: Optional[datetime],
                 tsb_by_step: Dict[str, List[dict]]) -> List[str]:
    """Render one step + its nested generation / gateway_request / ts-bound GWs."""
    st_is_last = st_idx == n_steps - 1
    st_branch = "└──" if st_is_last else "├──"
    st_cont = "    " if st_is_last else "│   "
    st_start_off = _fmt_offset(st.get("start_ts"), start_dt)
    st_end_off = _fmt_offset(st.get("end_ts"), start_dt)
    st_dur = _fmt_duration_ms(st.get("start_ts"), st.get("end_ts"))

    # Show the bound LLM model alongside the step name when known.
    # `model_name` is mirrored from the bound gateway_request by
    # assemble_dc; None when the declared chain didn't reach or when STDM
    # dropped writes (the `gateway_requests_dropped_by_stdm` shape).
    name_cell = st.get("name") or "—"
    model_name = st.get("model_name")
    if model_name:
        name_cell = f"{name_cell} · {model_name}"

    lines = [
        f"{iv_cont}{grp_cont}{st_branch} {st.get('type') or '?'}  {_short(st.get('id'))}  "
        f"name={name_cell}  {st_start_off} + {st_dur} = {st_end_off}"
    ]

    # Step children: error, generation (+ trust signals), gateway_request, collision, bound GWs.
    step_kids: List[tuple] = []
    if st.get("error_text"):
        step_kids.append(("error", None))
    gen = st.get("generation")
    if gen:
        step_kids.append(("gen", gen))
    gw = st.get("gateway_request")
    if gw:
        step_kids.append(("gw", gw))
    if st.get("gateway_request_collision"):
        step_kids.append(("collision", None))
    for tb in tsb_by_step.get(st.get("id", ""), []):
        step_kids.append(("tsb", tb))

    prefix = f"{iv_cont}{grp_cont}{st_cont}"
    for k_idx, (ktype, kval) in enumerate(step_kids):
        k_is_last = k_idx == len(step_kids) - 1
        k_branch = "└──" if k_is_last else "├──"
        k_cont = "    " if k_is_last else "│   "

        if ktype == "error":
            lines.append(f"{prefix}{k_branch} ERROR: {st['error_text']}")
        elif ktype == "collision":
            lines.append(
                f"{prefix}{k_branch} ⚠ gateway_request_collision: "
                "earlier step claimed the declared GW"
            )
        elif ktype == "gen":
            lines.extend(_render_generation(kval, prefix, k_branch, k_cont,
                                           step_name=st.get("name")))
        elif ktype == "gw":
            lines.extend(_render_gw_declared(kval, prefix, k_branch, k_cont))
        elif ktype == "tsb":
            tb = kval
            lines.append(
                f"{prefix}{k_branch} gateway_request [timestamp_window]  "
                f"{_short(tb.get('gateway_request_id'))}  "
                f"feature={tb.get('feature') or '—'}  "
                f"model={tb.get('model') or '—'}"
            )
    return lines


_ROLE_LABELS = {
    "ReactTopicPrompt":                 "topic-classification output",
    "ReactInitialPrompt":               "ReAct planner step",
    "ReactValidationPrompt":            "ReAct validator",
    "ReactFormatSurfaceResponsePrompt": "response formatter",
}


def _role_label_for(step_name: Optional[str]) -> Optional[str]:
    if not step_name:
        return None
    for key, label in _ROLE_LABELS.items():
        if key in step_name:
            return label
    return None


def _parse_finish_reason(response_parameters: Optional[str]) -> Optional[str]:
    """Pull finish_reason out of the HTML-escaped JSON in responseParameters__c.
    Shape: `{&quot;finish_reason&quot;:&quot;&#92;&quot;stop&#92;&quot;&quot;,...}`."""
    if not response_parameters:
        return None
    try:
        decoded = html.unescape(response_parameters)
        parsed = json.loads(decoded)
    except (ValueError, TypeError):
        return None
    raw = parsed.get("finish_reason") if isinstance(parsed, dict) else None
    if not isinstance(raw, str):
        return None
    # value often comes wrapped in escaped quotes: `\"stop\"` → `stop`
    return raw.replace("\\", "").strip('"').strip()


def _decoded_line(response_text: Optional[str]) -> str:
    """Render `decoded:` content. Detect tool-call JSON and summarize.
    responseText__c is HTML-escaped (&quot; etc.) in the wire format — unescape
    before trying to parse as JSON."""
    if not response_text:
        return "—"
    candidate = html.unescape(response_text).strip()
    if candidate.startswith("{") and '"toolInvocations"' in candidate:
        try:
            obj = json.loads(candidate)
            tools = obj.get("toolInvocations") or []
            content = (obj.get("content") or "").strip()
            if tools:
                first = tools[0].get("function") or {}
                name = first.get("name") or "?"
                args_raw = first.get("arguments") or ""
                arg_summary = ""
                try:
                    args_obj = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    if isinstance(args_obj, dict) and args_obj:
                        k, v = next(iter(args_obj.items()))
                        v_str = str(v)
                        if len(v_str) > 60:
                            v_str = v_str[:57] + "…"
                        arg_summary = f'{k}="{v_str}"'
                except (ValueError, TypeError):
                    pass
                prefix = "no user text" if not content else f'"{_truncate(content, 60)}"'
                n = len(tools)
                call_word = "tool call" if n == 1 else "tool calls"
                return f"{prefix}; {n} {call_word} → {name}({arg_summary})"
        except (ValueError, TypeError):
            pass
    return f'"{_truncate(response_text, 140)}"'


def _float_or_none(v) -> Optional[float]:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _trust_line(g: dict) -> str:
    """Summarize trust signals. TOXICITY sub-categories (parented on the
    quality row) carry a dedicated `safety_score` category in the 0-1 range
    (1.0 = clean). Non-`safety_score` sub-categories are the 8 hazard axes
    (profanity, hate, violence, …); report the max of those when a detection
    fires so the reader sees which axis tripped.
    Non-TOXICITY detectors (InstructionAdherence, etc.) are parented directly
    on the generation and render as textual verdicts."""
    quality = g.get("quality") or []
    cats = g.get("categories") or []
    if not quality and not cats:
        return "—  (no quality/category rows)"
    parts: List[str] = []
    for q in quality:
        subs = q.get("_toxicity_subcategories") or []
        detected = str(q.get("isToxicityDetected__c", "")).lower() == "true"
        safety: Optional[float] = None
        hazard_subs: List[tuple] = []
        for s in subs:
            if (s.get("detectorType__c") or "").upper() != "TOXICITY":
                continue
            name = s.get("category__c") or ""
            val = _float_or_none(s.get("value__c"))
            if val is None:
                continue
            if name == "safety_score":
                safety = val
            else:
                hazard_subs.append((name, val))
        status = "detected" if detected else "clean"
        safety_str = f"{safety:.2f}" if safety is not None else "—"
        if not detected and hazard_subs and all(v == 0 for _, v in hazard_subs):
            detail = f" — all {len(hazard_subs)} sub-categories 0.00"
        elif hazard_subs:
            top_name, top_val = max(hazard_subs, key=lambda kv: kv[1])
            detail = f" — max {top_name}={top_val:.2f}"
        else:
            detail = ""
        parts.append(f"TOXICITY safety_score={safety_str} ({status}{detail})")
    # Non-TOXICITY detectors (generation-direct).
    for c in cats:
        dtype = (c.get("detectorType__c") or "?").strip()
        if dtype.upper() == "TOXICITY":
            continue
        val = c.get("value__c")
        parts.append(f"{dtype}: {_truncate(val, 80)}")
    return "; ".join(parts) if parts else "—"


def _render_generation(g: dict, prefix: str, k_branch: str, k_cont: str,
                       *, step_name: Optional[str] = None) -> List[str]:
    """Generation node: 3 fixed children (decoded / finish_reason+masked / trust).
    Header is naked (id only); `response_id` and `feature` live in the ID reference
    block / on the sibling gateway_request line."""
    lines = [
        f"{prefix}{k_branch} generation  {_short(g.get('generation_id'))}"
    ]
    role = _role_label_for(step_name)
    decoded = _decoded_line(g.get("response_text"))
    if role:
        decoded_line = f"decoded: {decoded}  ({role})"
    else:
        decoded_line = f"decoded: {decoded}"
    masked = g.get("masked_response_text")
    masked_disp = _truncate(masked, 60) if masked else "—"
    finish_reason = _parse_finish_reason(g.get("response_parameters")) or "—"
    gprefix = f"{prefix}{k_cont}"
    lines.append(f"{gprefix}├── {decoded_line}")
    lines.append(f"{gprefix}├── finish_reason={finish_reason}  masked={masked_disp}")
    lines.append(f"{gprefix}└── trust: {_trust_line(g)}")
    return lines


def _render_gw_declared(g: dict, prefix: str, k_branch: str, k_cont: str) -> List[str]:
    tokens = (
        f"prompt={int(g.get('prompt_tokens') or 0)}  "
        f"completion={int(g.get('completion_tokens') or 0)}  "
        f"total={int(g.get('total_tokens') or 0)}"
    )
    tags = g.get("tags") or []
    md = g.get("metadata") or []
    recs = g.get("records") or []
    llm = g.get("llm") or []
    audit_line = (
        f"audit: tags={len(tags)}  metadata={len(md)}  records={len(recs)}  llm={len(llm)}"
        if (tags or md or recs or llm)
        else "audit: (none)"
    )
    return [
        f"{prefix}{k_branch} gateway_request [declared]  "
        f"{_short(g.get('gateway_request_id'))}  "
        f"feature={g.get('feature') or '—'}  "
        f"model={g.get('model') or '—'}  "
        f"provider={g.get('provider') or '—'}",
        f"{prefix}{k_cont}├── tokens: {tokens}",
        f"{prefix}{k_cont}└── {audit_line}",
    ]


def _section_per_turn_summary(sess: dict, start_dt: Optional[datetime]) -> List[str]:
    lines: List[str] = [
        "## Per-turn summary",
        "",
        "| Interaction | Type | Start offset | Duration | Steps | "
        "GW declared | GW ts_window | USER → AGENT |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for iv in sess.get("interactions", []):
        iv_type = iv.get("type") or "?"
        start_off = _fmt_offset(iv.get("start_ts"), start_dt)
        dur = _fmt_duration_ms(iv.get("start_ts"), iv.get("end_ts"))
        step_count = len(iv.get("steps", []))
        declared_gws = sum(
            1 for st in iv.get("steps", [])
            if st.get("gateway_request")
            and st["gateway_request"].get("binding_method") == "declared"
        )
        tsw_gws = len(iv.get("timestamp_bound_gateway_calls", []))
        user_msg = next((m for m in iv.get("messages", []) if m.get("role") == "USER"), None)
        agent_msg = next((m for m in iv.get("messages", []) if m.get("role") == "AGENT"), None)
        ut = _truncate(user_msg.get("text") if user_msg else None, 40)
        at = _truncate(agent_msg.get("text") if agent_msg else None, 40)
        lines.append(
            f"| `{_short(iv.get('id'))}` | {iv_type} | {start_off} | {dur} | "
            f"{step_count} | {declared_gws} | {tsw_gws} | {ut} → {at} |"
        )
    lines.append("")
    return lines


# ---- visual analysis (mermaid) -------------------------------------------

# Chars that break mermaid label parsing when bare; quote-wrap the string
# when any of these show up. Underscore+digit tokens in topic strings are
# legal inside mermaid node labels — only syntax-significant chars need
# escaping here.
_MERMAID_LABEL_SPECIALS = set(',()<>:"#')


def _escape_mermaid_label(s: str) -> str:
    if not s:
        return '""'
    if any(ch in _MERMAID_LABEL_SPECIALS for ch in s):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _sequence_msg(s: str) -> str:
    """Sanitize free-form text for the right-hand side of a sequenceDiagram
    arrow. Mermaid parses `A->>B: <text>` up to newline — the text itself is
    unquoted, so wrapping in `"..."` (as node-label escape does) renders the
    quotes literally. We just strip newlines and escape the one char that
    ends the message field (semicolon is the statement terminator)."""
    if not s:
        return "—"
    return s.replace("\n", " ").replace(";", ",").strip()


def _flowchart_edge_label(s: str) -> str:
    """Sanitize free-form text for a flowchart edge label `A -->|label| B`.
    The delimiter is the pipe itself, so a literal `|` in the label shatters
    the parser. Square brackets also clash with node-shape syntax. Strip/
    substitute these; other specials (commas, colons, parens) are fine
    inside quoted labels, which `_escape_mermaid_label` handles."""
    if not s:
        return ""
    cleaned = s.replace("|", "/").replace("[", "(").replace("]", ")")
    return _escape_mermaid_label(cleaned)


def _step_display_name(st: dict) -> str:
    """Short, mermaid-safe row label for a step.

    - Strip `AiCopilot__` prefix on LLM prompts.
    - For ACTION_STEP names shaped `Topic_xxx.AGNT_Action_yyy`, keep the
      action-name portion after the last `.` so the row reads as the
      invoked action, not the topic.
    """
    name = st.get("name") or st.get("type") or "?"
    if name.startswith("AiCopilot__"):
        name = name[len("AiCopilot__"):]
    if st.get("type") == "ACTION_STEP" and "." in name:
        name = name.rsplit(".", 1)[-1]
    # Gantt task names cannot contain colons (task syntax is `label : id, start, dur`).
    return name.replace(":", "·")


def _iter_turns(sess: dict) -> List[dict]:
    return [iv for iv in sess.get("interactions", []) if iv.get("type") == "TURN"]


def _mermaid_gantt(
    sess: dict,
    start_dt: Optional[datetime],
    llm_calls: Optional[List[dict]] = None,
) -> List[str]:
    """Gantt chart — wall-clock timeline.

    Rows per turn (ACTION steps tagged :crit). When `llm_calls` is
    non-empty, a trailing "LLM calls" section renders per-call rows
    tagged by region-class (:active = cross_region, :done = same-
    region, plain = unknown). Mermaid's built-in 3-class palette is
    enough signal for v1; full per-region color would need a classDef
    block (deferred — see plan OOS-2.A).

    Kill-criterion: <3 total rows after dropping zero-duration steps
    AND no LLM-call rows → return []. If the step set is thin but the
    call set is non-empty, we still render (the call rows are the
    whole point of the overlay).
    """
    if start_dt is None:
        return []
    rows: List[tuple] = []  # (section_label, row_label, start_ms, end_ms, is_action)
    turns = _iter_turns(sess)
    for iv in sess.get("interactions", []):
        if iv.get("type") != "TURN":
            continue
        topic = iv.get("topic") or "(no topic)"
        section = f"Turn {turns.index(iv) + 1} ({topic})"
        for st in iv.get("steps", []):
            if st.get("type") == "SESSION_END":
                continue
            s_dt = _parse_iso(st.get("start_ts"))
            e_dt = _parse_iso(st.get("end_ts"))
            if s_dt is None or e_dt is None:
                continue
            s_ms = int((s_dt - start_dt).total_seconds() * 1000)
            e_ms = int((e_dt - start_dt).total_seconds() * 1000)
            if e_ms <= s_ms:
                continue  # skip zero-duration (e.g. TOPIC_STEP markers)
            rows.append((section, _step_display_name(st), s_ms, e_ms,
                         st.get("type") == "ACTION_STEP"))

    # LLM-call rows — one per gateway call, derived from _llm_calls.json.
    # Rendered in a trailing section so they don't interleave with step
    # rows (mermaid sections don't sort across boundaries).
    call_rows: List[tuple] = []  # (row_label, start_ms, end_ms, class_tag)
    for call in (llm_calls or []):
        t_iso = call.get("_time")
        dur_ms = call.get("duration_ms")
        if not t_iso or dur_ms is None:
            continue
        t_dt = _parse_iso(t_iso)
        if t_dt is None:
            continue
        s_ms = int((t_dt - start_dt).total_seconds() * 1000)
        e_ms = s_ms + int(dur_ms)
        if e_ms <= s_ms:
            continue
        # class_tag: cross_region=True → :active (mermaid's yellow),
        # cross_region=False → :done (grey), unknown/None → no tag
        # (default blue). Operators can scan for the yellow bars as
        # the cross-region outliers.
        cr = call.get("cross_region")
        if cr is True:
            class_tag = ":active, "
        elif cr is False:
            class_tag = ":done, "
        else:
            class_tag = ":"
        model = call.get("model_name") or "call"
        region = call.get("routing_decision") or "—"
        label = _escape_mermaid_label(f"{model} [{region}]")
        call_rows.append((label, s_ms, e_ms, class_tag))

    if len(rows) < 3 and not call_rows:
        return []

    # axisFormat: `%M:%S` renders as minutes:seconds via d3. Our offsets
    # are ms-from-start passed through `dateFormat x` (unix epoch); d3
    # treats them as Jan 1 1970 timestamps, so for any session under
    # 1 hour this reads cleanly as m:ss elapsed. `%L` (ms-of-second)
    # always rendered 000 because ticks land at second boundaries.
    # The leading `section anchor` + 1ms milestone forces the x-axis to
    # start at 00:00 — mermaid derives axis min from the smallest task
    # timestamp, and without the anchor that's the first step's offset
    # (~5s into a typical session), making the axis misleadingly slide.
    lines = [
        "```mermaid",
        "gantt",
        "    title Session timeline (m:ss from start)",
        "    dateFormat x",
        "    axisFormat %M:%S",
        "    section Session start",
        "    t0 :milestone, 0, 0",
    ]
    current_section: Optional[str] = None
    for section, label, s_ms, e_ms, is_action in rows:
        if section != current_section:
            lines.append(f"    section {section}")
            current_section = section
        # Mermaid gantt task: `<name> :[tag,] <start>, <end>` — single colon,
        # tag is the first comma-separated field after it. Two colons (the
        # `:crit:` shape) is a parse error.
        prefix = ":crit, " if is_action else ":"
        lines.append(f"    {label} {prefix}{s_ms}, {e_ms}")
    if call_rows:
        lines.append("    section LLM calls")
        for label, s_ms, e_ms, class_tag in call_rows:
            lines.append(f"    {label} {class_tag}{s_ms}, {e_ms}")
    lines.append("```")
    lines.append("")
    return lines


def _action_short_name(st: dict) -> str:
    name = st.get("name") or ""
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    return name or "action"


def _mermaid_sequence_per_turn(iv: dict, start_dt: Optional[datetime],
                               turn_no: int) -> List[str]:
    steps = iv.get("steps", [])
    has_error = any(st.get("error_text") for st in steps)
    action_steps = [st for st in steps if st.get("type") == "ACTION_STEP"]
    if not has_error and len(action_steps) < 2:
        return []

    topic = iv.get("topic") or "(no topic)"
    heading = f"### Turn {turn_no} ({topic}) — control flow"
    lines: List[str] = [heading, "", "```mermaid", "sequenceDiagram"]

    # Participants: U, P, L are always present; actions get A1, A2, …
    lines.append("    participant U as USER")
    lines.append("    participant P as Planner")
    lines.append("    participant L as LLM Gateway")
    action_alias: Dict[str, str] = {}  # step id → alias
    for i, st in enumerate(action_steps, start=1):
        alias = f"A{i}"
        action_alias[st.get("id") or f"_a{i}"] = alias
        label = _escape_mermaid_label(_action_short_name(st))
        lines.append(f"    participant {alias} as {label}")

    # User → Planner (utterance).
    user_msg = next((m for m in iv.get("messages", []) if m.get("role") == "USER"), None)
    user_text = _truncate(user_msg.get("text") if user_msg else None, 40)
    if user_msg:
        lines.append(f"    U->>P: {_sequence_msg(user_text)}")

    # Walk steps in order. LLM → L, ACTION → A<n>, errors → Note over.
    for st in steps:
        stype = st.get("type")
        if stype == "LLM_STEP":
            label = _step_display_name(st)
            gw = st.get("gateway_request") or {}
            model = gw.get("model")
            suffix = f" ({model})" if model else ""
            lines.append(f"    P->>L: {_sequence_msg(label + suffix)}")
            dur = _fmt_duration_ms(st.get("start_ts"), st.get("end_ts"))
            if st.get("error_text"):
                lines.append(f"    Note over L: ERROR in {dur}")
            else:
                lines.append(f"    L-->>P: ok ({dur})")
        elif stype == "ACTION_STEP":
            alias = action_alias.get(st.get("id") or "", "A?")
            dur = _fmt_duration_ms(st.get("start_ts"), st.get("end_ts"))
            lines.append(f"    P->>{alias}: invoke")
            lines.append(f"    {alias}-->>P: result ({dur})")

    # Agent reply (if any).
    agent_msg = next((m for m in iv.get("messages", []) if m.get("role") == "AGENT"), None)
    if agent_msg:
        agent_text = _truncate(agent_msg.get("text"), 40)
        lines.append(f"    P-->>U: {_sequence_msg(agent_text)}")

    lines.append("```")
    lines.append("")
    return lines


def _mermaid_topic_flowchart(sess: dict) -> List[str]:
    turns = _iter_turns(sess)
    if not turns:
        return []
    # Order-preserving unique topics.
    topic_ids: Dict[str, str] = {}
    for iv in turns:
        t = iv.get("topic") or "(no topic)"
        if t not in topic_ids:
            topic_ids[t] = f"T{len(topic_ids) + 1}"
    if len(topic_ids) == len(turns):
        return []  # linear — no repeats, skip

    lines: List[str] = ["```mermaid", "flowchart LR"]
    # Node declarations.
    for topic, node_id in topic_ids.items():
        lines.append(f"    {node_id}[{_escape_mermaid_label(topic)}]")

    # Edges: one per turn transition, labelled by the user utterance that
    # drove into that turn. The first turn has no predecessor so we just
    # declare the node; edges start from turn 2.
    prev_topic = turns[0].get("topic") or "(no topic)"
    for iv in turns[1:]:
        cur_topic = iv.get("topic") or "(no topic)"
        user_msg = next((m for m in iv.get("messages", []) if m.get("role") == "USER"), None)
        utter = _truncate(user_msg.get("text") if user_msg else None, 30)
        src = topic_ids[prev_topic]
        dst = topic_ids[cur_topic]
        label = _flowchart_edge_label(utter) if utter and utter != "—" else ""
        arrow = f"    {src} -->|{label}| {dst}" if label else f"    {src} --> {dst}"
        lines.append(arrow)
        prev_topic = cur_topic

    # Error class for topics whose turn ended with an error_text.
    errored_topic_ids: List[str] = []
    for iv in turns:
        if any(st.get("error_text") for st in iv.get("steps", [])):
            tid = topic_ids[iv.get("topic") or "(no topic)"]
            if tid not in errored_topic_ids:
                errored_topic_ids.append(tid)
    if errored_topic_ids:
        lines.append(f"    classDef err fill:#fee,stroke:#c00")
        for tid in errored_topic_ids:
            lines.append(f"    class {tid} err")

    lines.append("```")
    lines.append("")
    return lines


def _mermaid_token_pie(sess: dict) -> List[str]:
    buckets: Dict[str, int] = {}
    total = 0
    for iv in sess.get("interactions", []):
        for st in iv.get("steps", []):
            gw = st.get("gateway_request") or {}
            p = int(gw.get("prompt_tokens") or 0)
            c = int(gw.get("completion_tokens") or 0)
            tok = p + c
            if tok <= 0:
                continue
            role = _role_label_for(st.get("name")) or "other"
            buckets[role] = buckets.get(role, 0) + tok
            total += tok
    if total < 1000 or not buckets:
        return []

    lines = [
        "```mermaid",
        "pie showData",
        f"    title Prompt-role token attribution (total = {total:,})",
    ]
    # Largest slice first reads better in most renderers.
    for role, n in sorted(buckets.items(), key=lambda kv: -kv[1]):
        lines.append(f'    "{role}" : {n}')
    lines.append("```")
    lines.append("")
    return lines


def _section_visual_analysis(
    sess: dict,
    start_dt: Optional[datetime],
    llm_calls: Optional[List[dict]] = None,
) -> List[str]:
    blocks: List[List[str]] = []
    gantt = _mermaid_gantt(sess, start_dt, llm_calls=llm_calls)
    if gantt:
        blocks.append(gantt)
    # Per-turn sequence diagrams (at most one per turn; most turns skip).
    turns = _iter_turns(sess)
    for idx, iv in enumerate(turns, start=1):
        seq = _mermaid_sequence_per_turn(iv, start_dt, idx)
        if seq:
            blocks.append(seq)
    flow = _mermaid_topic_flowchart(sess)
    if flow:
        blocks.append(flow)
    pie = _mermaid_token_pie(sess)
    if pie:
        blocks.append(pie)

    if not blocks:
        return []
    lines: List[str] = ["## Visual analysis", ""]
    for b in blocks:
        lines.extend(b)
    return lines


def _section_session_counts(sess: dict) -> List[str]:
    c = sess.get("counts", {})
    st_by_type = c.get("steps_by_type", {})
    gwb = c.get("gw_binding", {})
    lines: List[str] = [
        "## Session counts",
        "",
        "| metric | value |",
        "|---|---|",
        f"| interactions | {c.get('interactions_total', 0)} |",
        f"| steps | {c.get('steps_total', 0)} |",
        f"| llm_steps | {st_by_type.get('LLM_STEP', 0)} |",
        f"| action_steps | {st_by_type.get('ACTION_STEP', 0)} |",
        f"| gateway_requests | {c.get('gateway_requests', 0)} |",
        f"| gateway_responses | {c.get('gateway_responses', 0)} |",
        f"| 1:1 invariant | {'✓' if c.get('audit_chain_1to1_ok') else '✗'} |",
        f"| gw declared | {gwb.get('declared', 0)} |",
        f"| gw timestamp_window | {gwb.get('timestamp_window', 0)} |",
        f"| gw unbound | {gwb.get('unbound', 0)} |",
    ]
    if gwb.get("declared_collisions"):
        lines.append(f"| ⚠ declared_collisions | {gwb['declared_collisions']} |")
    lines.append("")
    return lines


def _section_empties_diagnostics(manifest: dict) -> List[str]:
    """Operator-actionable: lift `_unavailable_reason` verbatim from the manifest."""
    queries = manifest.get("queries", []) if manifest else []
    empties = [
        q for q in queries
        if q.get("rows") == 0 and q.get("_unavailable_reason")
    ]
    if not empties:
        return []
    lines: List[str] = [
        "## Empties diagnostics",
        "",
        "DMOs that returned zero rows, with the reason lifted verbatim from the manifest:",
        "",
        "| DMO | Reason |",
        "|---|---|",
    ]
    for q in empties:
        name = q.get("name") or "?"
        # Pipe characters in reason text would break markdown tables.
        reason = str(q.get("_unavailable_reason") or "").replace("|", "\\|")
        lines.append(f"| {name} | {reason} |")
    lines.append("")
    return lines


def _section_catalog(tree: dict) -> List[str]:
    catalog = tree.get("catalog", {}) or {}
    agents = ", ".join(catalog.get("agents_observed", []) or []) or "—"
    return [
        "## Catalog (session-filtered)",
        "",
        f"- TagDefinitions: {len(catalog.get('tag_definitions', []) or [])}",
        f"- TagDefinitionAssociations: "
        f"{len(catalog.get('tag_definition_associations', []) or [])} (agents: {agents})",
        f"- Tags: {len(catalog.get('tags', []) or [])}",
        "",
    ]


# ---- top-level render + entry points -------------------------------------

def render(
    tree: dict,
    manifest: Optional[dict] = None,
    session_dir: Optional[Path] = None,
    *,
    show_prompts: bool = False,
) -> str:
    """Produce the summary markdown for a single session.

    Branches on tree shape:
    - gateway-direct tree (``_source == "gateway_direct"``) → identity +
      lag banner + gateway-chain table + per-call detail; skips the
      Interaction-dependent sections.
    - minimal tree (session-not-found) → short markdown with just identity.
    - full tree → multi-section summary (see SKILL.md for the full list).

    ``session_dir`` is reserved for callers that want the renderer to look
    up artifacts beside the tree on disk. The standalone d360 skill produces
    no runtime-telemetry rollups — DC alone doesn't expose per-turn LLM
    latency in a useful form — so when ``None`` (the test-friendly default),
    the gantt simply draws without the LLM-call overlay.

    ``show_prompts`` (opt-in): when True, the full-tree branch appends
    a "Planner LLM calls" section with full prompt + response text per
    LLM call. Default False — the section can add hundreds of KB to the
    summary on multi-turn sessions.

    Refuses incompatible tree schema versions (see `_assert_schema_version`).
    """
    _assert_schema_version(tree)

    # Gateway-direct branch — session resolved but STDM hierarchy hasn't
    # materialized yet. Handled before the has_interactions check because
    # the gateway-direct tree does set `session.interactions = []`.
    if tree.get("_source") == "gateway_direct":
        return _render_gateway_direct(tree, manifest, show_prompts=show_prompts)

    sess = tree.get("session") or {}
    sid = sess.get("id") or "<unknown>"
    has_interactions = "interactions" in sess

    # Minimal-tree early return.
    if not has_interactions:
        return _render_minimal(sid, sess)

    start_iso = sess.get("start_ts")
    start_dt = _parse_iso(start_iso)
    effective_end_iso, end_source = _derive_session_end(sess)

    # The d360 skill produces no runtime-telemetry rollups — DC alone
    # doesn't expose per-turn LLM latency in a useful form. Visual
    # analysis falls back to its pre-rollup output.
    llm_calls: List[dict] = []

    lines: List[str] = [f"# Session {sid}", ""]
    lines.extend(_section_session_identity(sess, effective_end_iso, end_source))
    # VariableText__c bootstrap (channel-mode diagnostic).
    lines.extend(_section_session_bootstrap(
        sess.get("identity") or {}, channel=sess.get("channel"),
    ))
    lines.extend(_section_id_reference(sess))
    lines.extend(_section_transcript(sess, start_dt))
    lines.extend(_section_hierarchical_trace(sess, start_dt, effective_end_iso, end_source))
    lines.extend(_section_per_turn_summary(sess, start_dt))
    # Opt-in full prompt + response per LLM call. Off by
    # default — multi-turn sessions can produce hundreds of KB here.
    lines.extend(_section_planner_llm_calls(sess, show_prompts=show_prompts))
    lines.extend(_section_visual_analysis(sess, start_dt, llm_calls=llm_calls))
    lines.extend(_section_session_counts(sess))
    lines.extend(_section_empties_diagnostics(manifest or {}))
    lines.extend(_section_catalog(tree))
    return "\n".join(lines) + "\n"


def _render_minimal(sid: str, sess: dict) -> str:
    """Short markdown for session-not-found minimal trees."""
    shape = (sess.get("counts") or {}).get("session_shape", "session_not_found")
    lines = [
        f"# Session {sid}",
        "",
        "## Session identity",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Session id | {sid} |",
        f"| Session shape | {shape} |",
        "",
        "_No interactions resolved in Data Cloud. Check the session id, or wait for "
        "STDM materialization._",
        "",
    ]
    return "\n".join(lines) + "\n"


# Display-only cap on `prompt_text` inside per-call detail. The raw JSON on
# disk (dc.gateway_requests.json) is authoritative and never truncated — the
# assembler stores the full prompt, and this slice only applies to markdown.
_PROMPT_DISPLAY_CAP_BYTES = 65536


def _fmt_token_count(value) -> str:
    """Tolerate ints, stringified ints, and None/''/NOT_SET."""
    if value in (None, "", "NOT_SET"):
        return "—"
    return str(value)


def _render_gateway_direct(tree: dict, manifest: Optional[dict],
                           *, show_prompts: bool = False) -> str:
    """Render the STDM-hasn't-materialized-yet view.

    Sections:
      1. Session identity          (reused)
      2. ID reference              (reused; gracefully handles the empty
                                    interactions/participants on this path)
      3. STDM lag banner           (gateway-direct specific)
      4. Gateway chain table       (gateway-direct specific)
      5. Per-call detail           (gateway-direct specific)
      6. Empties diagnostics       (reused; reads manifest, not tree)
      7. Catalog                   (reused; catalog may be empty on a
                                    fresh-session gateway-direct tree)

    Skipped: Transcript, Hierarchical trace, Per-turn summary, Session
    counts — all require Interaction rows that don't exist yet.

    ``show_prompts`` (default False): forwarded to per-call detail so the
    full prompt block only renders under ``--show-prompts``. The prior
    behavior unconditionally leaked prompts on this branch, contradicting
    the documented contract for ``dc._session_summary.md``.
    """
    sess = tree.get("session") or {}
    sid = sess.get("id") or "<unknown>"
    start_iso = sess.get("start_ts")
    start_dt = _parse_iso(start_iso)
    # No derivation needed — sessions.end_ts is the only source on this path.
    effective_end_iso = sess.get("end_ts")

    lines: List[str] = [f"# Session {sid}", ""]
    lines.extend(_section_session_identity(sess, effective_end_iso, None))
    # VariableText__c bootstrap (channel-mode diagnostic).
    lines.extend(_section_session_bootstrap(
        sess.get("identity") or {}, channel=sess.get("channel"),
    ))
    lines.extend(_section_id_reference(sess))
    lines.extend(_section_stdm_lag_banner())
    lines.extend(_section_gateway_chain_table(sess, start_dt))
    lines.extend(_section_gateway_per_call_detail(sess, show_prompts=show_prompts))
    lines.extend(_section_empties_diagnostics(manifest or {}))
    lines.extend(_section_catalog(tree))
    return "\n".join(lines) + "\n"


def _section_stdm_lag_banner() -> List[str]:
    return [
        "## STDM materialization lag",
        "",
        "> **Note** STDM Interaction/Step/Message DMOs have not yet "
        "materialized for this session. The view below is the gateway chain "
        "harvested directly from Gateway DMOs (materialize in minutes). "
        "Re-run in 24–72h for the full hierarchical trace.",
        "",
    ]


def _section_gateway_chain_table(sess: dict,
                                 start_dt: Optional[datetime]) -> List[str]:
    chain = sess.get("gateway_chain") or []
    lines: List[str] = [
        "## Gateway chain",
        "",
        "| # | Request ts | Model | Provider | Prompt template | "
        "Prompt tok | Completion tok | Total tok | Response ts |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, call in enumerate(chain, start=1):
        req_offset = _fmt_offset(call.get("timestamp"), start_dt)
        resp_offset = _fmt_offset(
            (call.get("response") or {}).get("timestamp"), start_dt)
        model = call.get("model") or "—"
        provider = call.get("provider") or "—"
        template = call.get("prompt_template_dev_name") or "—"
        prompt_tok = _fmt_token_count(call.get("prompt_tokens"))
        completion_tok = _fmt_token_count(call.get("completion_tokens"))
        total_tok = _fmt_token_count(call.get("total_tokens"))
        lines.append(
            f"| {i} | {req_offset} | {model} | {provider} | {template} | "
            f"{prompt_tok} | {completion_tok} | {total_tok} | {resp_offset} |"
        )
    lines.append("")
    return lines


def _pick_fence(text: str) -> str:
    """Pick a backtick fence long enough to wrap `text` safely.

    CommonMark lets a fenced code block use any run of 3+ backticks; the
    closing fence must be at least as long as the opening. LLM prompts
    routinely contain triple-backticks inside tool-use examples, so a
    hardcoded ``` fence closes early and corrupts the rest of the doc.
    """
    if not isinstance(text, str) or not text:
        return "```"
    longest = 0
    run = 0
    for ch in text:
        if ch == "`":
            run += 1
            if run > longest:
                longest = run
        else:
            run = 0
    return "`" * max(3, longest + 1)


def _capped_payload(text: Optional[str], note_source: str) -> tuple[str, bool, str]:
    """Cap a payload string at `_PROMPT_DISPLAY_CAP_BYTES` for display.

    Returns ``(body, truncated, source_note)``. Byte-length check so
    multi-byte chars don't blow through the limit when the renderer emits
    UTF-8 text. Slicing happens on the encoded form, then decodes with
    ``errors="ignore"`` so we never split a multi-byte char mid-sequence.
    `source_note` names the on-disk file with the authoritative full text.
    """
    if not isinstance(text, str) or not text:
        return ("(empty)", False, note_source)
    encoded = text.encode("utf-8")
    if len(encoded) <= _PROMPT_DISPLAY_CAP_BYTES:
        return (text, False, note_source)
    body = encoded[:_PROMPT_DISPLAY_CAP_BYTES].decode("utf-8", errors="ignore")
    return (body, True, note_source)


def _render_call_detail_block(call: dict, idx: int, *,
                              show_prompts: bool = False,
                              show_response_text: bool = False) -> List[str]:
    """Render one ``#### LLM call N — <short-id>`` block.

    Used by both:
      - the gateway-direct branch (``_section_gateway_per_call_detail``)
      - the full-tree opt-in section (``_section_planner_llm_calls``)

    ``call`` shape (subset of fields used here):
      gateway_request_id, model, provider, prompt_template_dev_name,
      prompt_tokens, completion_tokens, total_tokens, prompt_text,
      response (-> finish_reason), response_text (only on full-tree path).

    The prompt and response blocks are independently gated:
      - ``show_prompts`` controls the **Prompt** block.
      - ``show_response_text`` controls the **Response** block (full-tree
        only — gateway-direct chain entries don't carry response_text).
    Both default off so callers must opt in explicitly. The summary line
    (model/provider/template/tokens/finish_reason) always renders.
    """
    gw_id = call.get("gateway_request_id") or "—"
    short_id = _short(gw_id)
    lines = [f"#### LLM call {idx} — {short_id}", ""]
    finish_reason = (call.get("response") or {}).get("finish_reason") or "—"
    summary = (
        f"- model={call.get('model') or '—'}"
        f"  provider={call.get('provider') or '—'}"
        f"  template={call.get('prompt_template_dev_name') or '—'}"
        f"  prompt_tok={_fmt_token_count(call.get('prompt_tokens'))}"
        f"  completion_tok={_fmt_token_count(call.get('completion_tokens'))}"
        f"  total_tok={_fmt_token_count(call.get('total_tokens'))}"
        f"  finish_reason={finish_reason}"
    )
    lines.append(summary)
    lines.append("")

    # Prompt block — gated by show_prompts. Default-off everywhere; the
    # summary file should never leak full prompt text without an explicit
    # --show-prompts opt-in (matches the doc contract in SKILL.md).
    if show_prompts:
        body, truncated, src = _capped_payload(
            call.get("prompt_text"), "dc.gateway_requests.json")
        fence = _pick_fence(body)
        lines.append("**Prompt** (full input sent to the model):")
        lines.append(fence)
        lines.append(body)
        if truncated:
            lines.append(f"…[truncated; full prompt in {src}]")
        lines.append(fence)
        lines.append("")

    # Response block — only the full-tree path carries response_text;
    # gateway-direct rows get finish_reason in the header line above and
    # nothing else (the response DMO doesn't carry text on that path).
    if show_response_text:
        body, truncated, src = _capped_payload(
            call.get("response_text"), "dc.generations.json")
        # html.unescape so the rendered block reads as plain JSON instead of
        # &quot;-laden text — matches the existing _decoded_line treatment.
        if body and body != "(empty)":
            body = html.unescape(body)
        fence = _pick_fence(body)
        lines.append("**Response** (model output, including tool invocations):")
        lines.append(fence)
        lines.append(body)
        if truncated:
            lines.append(f"…[truncated; full response in {src}]")
        lines.append(fence)
        lines.append("")

    return lines


def _section_gateway_per_call_detail(sess: dict, *,
                                     show_prompts: bool = False) -> List[str]:
    """Per-call detail for the gateway-direct branch.

    ``gateway_chain`` does NOT carry `response_text` (the responses DMO
    doesn't include it on that path), so the response block is always
    suppressed. The prompt block is gated by ``show_prompts`` so the
    default summary doesn't leak full prompt text — matches the
    documented contract for ``dc._session_summary.md``.
    """
    chain = sess.get("gateway_chain") or []
    lines: List[str] = ["## Per-call detail", ""]
    for i, call in enumerate(chain, start=1):
        lines.extend(_render_call_detail_block(
            call, i, show_prompts=show_prompts, show_response_text=False))
    return lines


def _collect_planner_llm_calls(sess: dict) -> List[dict]:
    """Walk ``interactions[].steps[]`` and collect call-view dicts.

    Each step that has a ``gateway_request`` (regardless of binding method)
    contributes one call view. ``response_text`` is sourced from the step's
    sibling ``generation.response_text`` when present; otherwise the call is
    still emitted with the prompt + token summary.

    Returned dicts use the same field names as ``gateway_chain`` entries so
    ``_render_call_detail_block`` can consume both shapes uniformly.
    """
    calls: List[dict] = []
    for iv in sess.get("interactions") or []:
        for st in iv.get("steps") or []:
            gw = st.get("gateway_request")
            if not gw:
                continue
            gen = st.get("generation") or {}
            calls.append({
                "gateway_request_id": gw.get("gateway_request_id"),
                "model": gw.get("model"),
                "provider": gw.get("provider"),
                "prompt_template_dev_name": gw.get("prompt_template_dev_name"),
                "prompt_tokens": gw.get("prompt_tokens"),
                "completion_tokens": gw.get("completion_tokens"),
                "total_tokens": gw.get("total_tokens"),
                "prompt_text": gw.get("prompt_text"),
                "response": gw.get("response"),
                "response_text": gen.get("response_text"),
            })
    return calls


def _section_planner_llm_calls(sess: dict, *, show_prompts: bool) -> List[str]:
    """Opt-in full-tree section showing the input prompt + response
    for every LLM call in the session's hierarchical trace.

    Off by default — prompts can be 30 KB+ each on multi-turn sessions
    and would otherwise dominate the summary. Enable with
    ``render_dc.py --show-prompts``.
    """
    if not show_prompts:
        return []
    calls = _collect_planner_llm_calls(sess)
    if not calls:
        return []
    lines: List[str] = [
        "## Planner LLM calls (full prompts + responses)",
        "",
        f"_Found {len(calls)} LLM call(s) across the session's hierarchical "
        f"trace. Prompts are capped at "
        f"{_PROMPT_DISPLAY_CAP_BYTES // 1024} KB for display; full payloads "
        f"are on disk in `dc.gateway_requests.json` and "
        f"`dc.generations.json`._",
        "",
    ]
    for i, call in enumerate(calls, start=1):
        # show_prompts is True here by section-guard above (early return when
        # show_prompts is False); pass through explicitly so the helper's new
        # prompt-gate stays aligned with the section's intent.
        lines.extend(_render_call_detail_block(
            call, i, show_prompts=True, show_response_text=True))
    return lines


def _assert_schema_version(tree: dict) -> None:
    """Refuse unsupported versions; warn on missing version (older assembler)."""
    version = (tree.get("session") or {}).get("_schema_version")
    if version is None:
        print(
            "render_dc: WARN tree has no _schema_version "
            "(produced by an older assembler?); rendering anyway",
            file=sys.stderr,
        )
        return
    if version != _SUPPORTED_SCHEMA_VERSION:
        raise SystemExit(
            f"render_dc: unsupported tree _schema_version={version}; "
            f"expected {_SUPPORTED_SCHEMA_VERSION}"
        )


def main_for_session(sid: str, *, show_prompts: bool = False) -> int:
    """Read session tree + manifest from the nested session dir; emit summary.md.

    Uses ``assemble_dc._find_session_dir`` to locate the session under
    ``DATA_ROOT/<org>/<agent>__<ver>/<sid>/`` — follows the ``_sessions/*.link``
    breadcrumb when present, globs otherwise. No callers need to know the
    full identity triple upfront.

    ``show_prompts``: pass through to ``render`` to include the
    opt-in "Planner LLM calls" section.
    """
    from assemble_dc import _find_session_dir
    session_dir = _find_session_dir(sid)
    tree_path = session_dir / "dc._session_tree.json"
    if not tree_path.is_file():
        raise SystemExit(
            f"render_dc: tree not found at {tree_path}; "
            f"run `python3 scripts/assemble_dc.py --session {sid}` first"
        )
    manifest_path = session_dir / "dc._session_manifest.json"
    manifest: Optional[dict] = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"render_dc: WARN could not read manifest: {str(e).splitlines()[0]}",
                file=sys.stderr,
            )

    tree = json.loads(tree_path.read_text())
    _assert_schema_version(tree)

    md_path = session_dir / "dc._session_summary.md"
    md_path.write_text(render(tree, manifest, session_dir=session_dir,
                              show_prompts=show_prompts))
    print(f"render_dc: wrote {md_path}", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="render_dc.py",
        description="Render dc._session_summary.md from dc._session_tree.json for one session.",
    )
    ap.add_argument("--session", required=True,
                    help="AI-agent session UUID or MessagingSession id (0Mw...). "
                         "Messaging ids are resolved from disk "
                         "(DATA_ROOT/*/dc.sessions.json); run fetch_dc.py first "
                         "if the session hasn't been fetched yet.")
    ap.add_argument("--show-prompts", action="store_true",
                    help="Include the opt-in 'Planner LLM calls' section "
                         "with the full input prompt + response per LLM call. "
                         "Off by default — multi-turn sessions can produce "
                         "hundreds of KB here. Per-prompt display is capped "
                         "at 64 KB; full payloads remain on disk in "
                         "dc.gateway_requests.json + dc.generations.json.")
    # Runtime-agnostic path overrides; default to ~/.vibe/...
    from _shared.cli_override import add_cli_flags, apply_overrides
    add_cli_flags(ap)
    args = ap.parse_args()
    apply_overrides(args, caller_globals=globals())
    from resolve_session import resolve_disk_or_live
    sid = resolve_disk_or_live(args.session)
    return main_for_session(sid, show_prompts=args.show_prompts)


if __name__ == "__main__":
    sys.exit(main())
