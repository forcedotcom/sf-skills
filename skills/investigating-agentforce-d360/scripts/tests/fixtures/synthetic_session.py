"""Synthetic session fixture for d360 integration tests.

Provides:

- ``IDS``           a flat namespace of all UUIDs/keys used so tests
                    can assert against specific values.
- ``make_rows()``   returns ``{dmo_name: [row, ...]}`` for the 24 DMOs
                    `assemble_dc` reads. Self-consistent: every
                    Step.GenerationId references a Generation row, etc.
- ``make_manifest`` returns the dc._session_manifest.json shape.
- ``write_to_disk`` materializes the whole fixture under a session dir
                    so tests that drive the public ``assemble_dc.assemble``
                    can use ``tmp_path`` + DATA_ROOT redirect without
                    duplicating layout knowledge.

Shape rules:
  - Timestamps anchored on 2026-04-22T10:00:00Z; offsets in seconds.
  - All ssot__Id__c values are 18-char-stable strings (not real Salesforce
    IDs) — assemble_dc only key-equality-checks them.
  - HTML escaping applied to AttributeText__c so the trace_id fallback
    path exercises real code.
  - parameters__c on gateway_responses uses the &quot;-escaped JSON shape
    real DC emits.
"""
from __future__ import annotations

import html
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


# -----------------------------------------------------------------------------
# IDs — exposed flat for cross-test assertions
# -----------------------------------------------------------------------------


class _IDs:
    SID = "019dface-0000-7000-8000-000000000001"
    """Agent session UUID. Valid UUIDv7 so window decode works."""

    ORG_ID_15 = "00D000000000ABC"
    ORG_ID_18 = "00D000000000ABCDEF"
    AGENT_API = "DemoAgent"
    AGENT_VERSION = "v5"
    BOT_ID = "0Xx000000000DemoBot"

    # Interactions
    IXN_START = "ixn-start-001"
    IXN_TURN = "ixn-turn-002"
    IXN_END = "ixn-end-003"

    # Steps within the TURN
    STEP_TOPIC = "step-topic-001"
    STEP_ACTION = "step-action-002"
    STEP_GUARDRAIL = "step-guardrail-003"

    # Gateway audit chain — one declared, one timestamp-window-only
    GW_REQ_DECLARED = "gw-req-declared-001"
    GW_REQ_WINDOW = "gw-req-window-002"
    GW_RESP_DECLARED = "gw-resp-declared-001"

    # Generation chain (declared)
    GEN_DECLARED = "gen-declared-001"

    # Participants
    PART_AGENT = "part-agent-001"
    PART_USER = "part-user-002"

    # Trace + window
    TRACE_ID = "8b820e85aaaaaaaabbbbbbbbcccccccc"
    SESSION_START = "2026-04-22T10:00:00.000Z"
    SESSION_END = "2026-04-22T10:01:30.000Z"
    TURN_START = "2026-04-22T10:00:05.000Z"
    TURN_END = "2026-04-22T10:01:00.000Z"
    GW_DECLARED_TS = "2026-04-22T10:00:30.000Z"  # inside step-action window
    GW_WINDOW_TS = "2026-04-22T10:00:45.000Z"   # inside the TURN window only


IDS = _IDs


# -----------------------------------------------------------------------------
# Per-DMO row builders
# -----------------------------------------------------------------------------


def _sessions() -> List[dict]:
    return [{
        "ssot__Id__c": IDS.SID,
        "ssot__InternalOrganizationId__c": IDS.ORG_ID_18,
        "ssot__StartTimestamp__c": IDS.SESSION_START,
        "ssot__EndTimestamp__c": IDS.SESSION_END,
        "ssot__AiAgentChannelType__c": "SCRT2 - EmbeddedMessaging",
        "ssot__AiAgentSessionEndType__c": "USER_ENDED",
        "ssot__RelatedMessagingSessionId__c": "0MwTESTMSG12345AAA",
    }]


def _interactions() -> List[dict]:
    """Three interactions: SESSION_START, TURN, SESSION_END.

    `AttributeText__c` carries the real internalTraceId in HTML-escaped
    JSON form on the TURN row (matches live DC shape).
    """
    # No spaces in separators — production logger emits compact JSON, and
    # the trace_id regex (`"internalTraceId":"([a-f0-9]+)"`) requires no
    # whitespace around the colon.
    raw_attr_text = json.dumps(
        {"internalTraceId": IDS.TRACE_ID, "label": "react-loop"},
        separators=(",", ":"),
    )
    return [
        {
            "ssot__Id__c": IDS.IXN_START,
            "ssot__AiAgentSessionId__c": IDS.SID,
            "ssot__AiAgentInteractionType__c": "SESSION_START",
            "ssot__StartTimestamp__c": IDS.SESSION_START,
            "ssot__EndTimestamp__c": IDS.SESSION_START,
            "ssot__TelemetryTraceId__c": "",
            "ssot__AttributeText__c": "",
        },
        {
            "ssot__Id__c": IDS.IXN_TURN,
            "ssot__AiAgentSessionId__c": IDS.SID,
            "ssot__AiAgentInteractionType__c": "TURN",
            "ssot__StartTimestamp__c": IDS.TURN_START,
            "ssot__EndTimestamp__c": IDS.TURN_END,
            "ssot__TelemetryTraceId__c": "",
            # HTML-escaped JSON triggers the AttributeText fallback path.
            "ssot__AttributeText__c": html.escape(raw_attr_text, quote=True),
        },
        {
            "ssot__Id__c": IDS.IXN_END,
            "ssot__AiAgentSessionId__c": IDS.SID,
            "ssot__AiAgentInteractionType__c": "SESSION_END",
            "ssot__StartTimestamp__c": IDS.SESSION_END,
            "ssot__EndTimestamp__c": IDS.SESSION_END,
            "ssot__TelemetryTraceId__c": "NOT_SET",
            "ssot__AttributeText__c": "",
        },
    ]


def _steps() -> List[dict]:
    """Three steps inside the TURN. Step times nest inside the turn window
    so the timestamp-window pass binds gateway_requests by containment."""
    return [
        {
            "ssot__Id__c": IDS.STEP_TOPIC,
            "ssot__AiAgentInteractionId__c": IDS.IXN_TURN,
            "ssot__AiAgentInteractionStepType__c": "TOPIC_STEP",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:10.000Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:00:20.000Z",
            "ssot__GenerationId__c": "NOT_SET",
            "ssot__Name__c": "TopicSelection",
        },
        {
            "ssot__Id__c": IDS.STEP_ACTION,
            "ssot__AiAgentInteractionId__c": IDS.IXN_TURN,
            "ssot__AiAgentInteractionStepType__c": "ACTION_STEP",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:25.000Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:00:40.000Z",
            "ssot__GenerationId__c": IDS.GEN_DECLARED,
            "ssot__Name__c": "PrimaryAction",
        },
        {
            "ssot__Id__c": IDS.STEP_GUARDRAIL,
            "ssot__AiAgentInteractionId__c": IDS.IXN_TURN,
            "ssot__AiAgentInteractionStepType__c": "TRUST_GUARDRAILS_STEP",
            "ssot__StartTimestamp__c": "2026-04-22T10:00:55.000Z",
            "ssot__EndTimestamp__c": "2026-04-22T10:01:00.000Z",
            "ssot__GenerationId__c": "NOT_SET",
            "ssot__Name__c": "FinalGuard",
        },
    ]


def _messages() -> List[dict]:
    return [
        {
            "ssot__Id__c": "msg-001",
            "ssot__AiAgentInteractionId__c": IDS.IXN_TURN,
            "ssot__AiAgentInteractionMessageType__c": "USER",
            "ssot__ContentText__c": "How do I refund my order?",
            "ssot__StartTimestamp__c": IDS.TURN_START,
        },
        {
            "ssot__Id__c": "msg-002",
            "ssot__AiAgentInteractionId__c": IDS.IXN_TURN,
            "ssot__AiAgentInteractionMessageType__c": "AGENT",
            "ssot__ContentText__c": "I'll help you with the refund process.",
            "ssot__StartTimestamp__c": IDS.TURN_END,
        },
    ]


def _participants() -> List[dict]:
    return [
        {
            "ssot__Id__c": IDS.PART_AGENT,
            "ssot__AiAgentSessionId__c": IDS.SID,
            "ssot__AiAgentSessionParticipantRole__c": "AGENT",
            "ssot__AiAgentApiName__c": IDS.AGENT_API,
            "ssot__AiAgentVersionApiName__c": IDS.AGENT_VERSION,
        },
        {
            "ssot__Id__c": IDS.PART_USER,
            "ssot__AiAgentSessionId__c": IDS.SID,
            "ssot__AiAgentSessionParticipantRole__c": "USER",
            "ssot__AiAgentApiName__c": "",
            "ssot__AiAgentVersionApiName__c": "",
        },
    ]


def _gateway_requests() -> List[dict]:
    """Two gateway requests:

    - GW_REQ_DECLARED: chained from Step → Generation → Response → Request.
      Timestamp also falls within step-action window so either binding
      method can resolve it. Declared chain wins.

    - GW_REQ_WINDOW: NOT in the declared chain. Timestamp falls inside
      the TURN window → exercise timestamp-window fallback.
    """
    return [
        {
            "gatewayRequestId__c": IDS.GW_REQ_DECLARED,
            "sf__Id": "sf-" + IDS.GW_REQ_DECLARED,
            "sessionId__c": f'"{IDS.SID}"',
            "timestamp__c": IDS.GW_DECLARED_TS,
            "model__c": "gpt-4o",
            "provider__c": "openai",
            "promptTemplateDevName__c": "AiCopilot__ReactInitialPrompt",
            "feature__c": "plannerservice",
            "promptTokens__c": 1200,
            "completionTokens__c": 50,
            "totalTokens__c": 1250,
            "prompt__c": "Declared-bound prompt body.",
        },
        {
            "gatewayRequestId__c": IDS.GW_REQ_WINDOW,
            "sf__Id": "sf-" + IDS.GW_REQ_WINDOW,
            "sessionId__c": f'"{IDS.SID}"',
            "timestamp__c": IDS.GW_WINDOW_TS,
            "model__c": "gpt-4o-mini",
            "provider__c": "openai",
            "promptTemplateDevName__c": "AiCopilot__PromptTemplateGenerationsInvocable",
            "feature__c": "plannerservice",
            "promptTokens__c": 200,
            "completionTokens__c": 20,
            "totalTokens__c": 220,
            "prompt__c": "Window-bound prompt body.",
        },
    ]


def _gateway_responses() -> List[dict]:
    raw = '{"finish_reason":"\\"stop\\""}'
    escaped = raw.replace('"', "&quot;")
    return [{
        "generationResponseId__c": IDS.GW_RESP_DECLARED,
        "generationRequestId__c": IDS.GW_REQ_DECLARED,
        "parameters__c": escaped,
        "timestamp__c": IDS.GW_DECLARED_TS,
    }]


def _generations() -> List[dict]:
    return [{
        "generationId__c": IDS.GEN_DECLARED,
        "generationResponseId__c": IDS.GW_RESP_DECLARED,
        "responseText__c": "I'll help you with the refund process.",
        "timestamp__c": IDS.GW_DECLARED_TS,
    }]


def _content_quality() -> List[dict]:
    return [{
        "generationId__c": IDS.GEN_DECLARED,
        "trustScore__c": 0.92,
        "qualityType__c": "NORMAL",
    }]


def _gateway_records() -> List[dict]:
    return [{
        "id__c": "gw-rec-001",
        "parent__c": IDS.GW_REQ_DECLARED,
        "sessionId__c": IDS.SID,
        "recordType__c": "RAG",
    }]


def _gateway_request_tags() -> List[dict]:
    return [
        {"id__c": "tag-001", "parent__c": IDS.GW_REQ_DECLARED,
         "tag__c": "promptTemplateDevName", "tagValue__c": "AiCopilot__ReactInitialPrompt"},
        {"id__c": "tag-002", "parent__c": IDS.GW_REQ_DECLARED,
         "tag__c": "feature", "tagValue__c": "plannerservice"},
    ]


# -----------------------------------------------------------------------------
# Public: rows + manifest
# -----------------------------------------------------------------------------


_ALL_TEMPLATES = (
    "sessions", "interactions", "messages", "moments", "participants",
    "tag_associations", "gateway_requests",
    "steps", "moment_interactions",
    "telemetry_spans", "generations", "app_generation",
    "gateway_request_tags", "gateway_responses", "gateway_records",
    "gateway_request_metadata", "gateway_request_llm",
    "feedback",
    "content_quality", "content_category", "feedback_details",
    "tag_definitions", "tag_definition_associations", "tags",
)


def make_rows() -> Dict[str, List[dict]]:
    """Return ``{dmo_name: [row, ...]}`` for all 24 DMOs.

    Empty lists for DMOs the synthetic session doesn't exercise — the
    code under test reads them by ``.get(name, [])`` and tolerates
    missing entries.
    """
    populated = {
        "sessions": _sessions(),
        "interactions": _interactions(),
        "steps": _steps(),
        "messages": _messages(),
        "participants": _participants(),
        "gateway_requests": _gateway_requests(),
        "gateway_responses": _gateway_responses(),
        "generations": _generations(),
        "content_quality": _content_quality(),
        "gateway_records": _gateway_records(),
        "gateway_request_tags": _gateway_request_tags(),
    }
    rows: Dict[str, List[dict]] = {name: [] for name in _ALL_TEMPLATES}
    rows.update(populated)
    return deepcopy(rows)


def make_manifest() -> dict:
    """Manifest shape matching what `fetch_dc.py` writes."""
    rows = make_rows()
    queries = [
        {
            "name": name,
            "row_count": len(rows[name]),
            "elapsed_ms": 50,
            "where_clause": f"ssot__AiAgentSessionId__c = '{IDS.SID}'",
        }
        for name in _ALL_TEMPLATES
    ]
    return {
        "_doc": "Per-query summary of this DC fetch run.",
        "session_id": IDS.SID,
        "org_alias": "my-org",
        "instance_url": "https://example.my.salesforce.com",
        "org_id_15": IDS.ORG_ID_15,
        "agent_api_name": IDS.AGENT_API,
        "agent_version": IDS.AGENT_VERSION,
        "session_shape": "ok",
        "started_at_utc": "2026-04-22T10:01:30.000Z",
        "finished_at_utc": "2026-04-22T10:01:32.000Z",
        "elapsed_ms": 2000,
        "queries": queries,
        "harvested_ids": {
            "interactions": [IDS.IXN_START, IDS.IXN_TURN, IDS.IXN_END],
        },
    }


# -----------------------------------------------------------------------------
# Disk materialization
# -----------------------------------------------------------------------------


def session_dir_for(data_root: Path) -> Path:
    """Compute the canonical session dir under a tmp DATA_ROOT."""
    return (
        data_root
        / IDS.ORG_ID_15
        / f"{IDS.AGENT_API}__{IDS.AGENT_VERSION}"
        / IDS.SID
    )


def write_to_disk(data_root: Path) -> Path:
    """Materialize the synthetic session under ``<data_root>/<org>/<agent>__<ver>/<sid>/``.

    Writes:
      - dc._session_manifest.json
      - dc.<name>.json for every populated DMO
      - The per-org breadcrumb at <org>/_sessions/<sid>.link

    Returns the session dir absolute path.
    """
    sdir = session_dir_for(data_root)
    sdir.mkdir(parents=True, exist_ok=True)

    # DC manifest + rows
    (sdir / "dc._session_manifest.json").write_text(
        json.dumps(make_manifest(), indent=2) + "\n"
    )
    rows = make_rows()
    for name, rs in rows.items():
        if rs:
            (sdir / f"dc.{name}.json").write_text(json.dumps(rs, indent=2) + "\n")

    # Breadcrumb so _find_session_dir's primary path resolves
    link_dir = data_root / IDS.ORG_ID_15 / "_sessions"
    link_dir.mkdir(parents=True, exist_ok=True)
    (link_dir / f"{IDS.SID}.link").write_text(
        f"../{IDS.AGENT_API}__{IDS.AGENT_VERSION}/{IDS.SID}\n"
    )

    return sdir
