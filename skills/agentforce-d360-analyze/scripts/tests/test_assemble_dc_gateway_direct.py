"""Tests for ``assemble_dc._assemble_gateway_direct``.

Exercises the ``interactions_not_materialized_yet`` path: session row
resolved, gateway_requests populated, interactions/steps empty. Builds a
minimal rows-dict fixture and calls the private assembler directly — the
function is pure over (sid, rows, manifest, parse_warnings), so no disk
fixtures are needed.

Scope:
  - ``_source == "gateway_direct"`` sentinel
  - ``session.interactions == []`` (downstream consumers no-op)
  - ``session.gateway_chain`` length == fixture's gateway_requests
  - each gateway_chain entry has a populated ``response.timestamp``
  - finish_reason is lifted out of the HTML-escaped parameters JSON
  - model / provider / prompt_template_dev_name / token counts populated
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

from assemble_dc import _assemble_gateway_direct  # type: ignore


_SID = "01912345-0000-7000-8000-000000000001"


def _gw_request(req_id: str, ts: str, model: str, tokens: tuple) -> dict:
    """Shape mirrors GenAIGatewayRequest__dlm rows as fetched."""
    prompt_tok, completion_tok, total_tok = tokens
    return {
        "gatewayRequestId__c": req_id,
        "sf__Id": f"sf-{req_id}",
        "sessionId__c": f'"{_SID}"',
        "timestamp__c": ts,
        "model__c": model,
        "provider__c": "openai",
        "promptTemplateDevName__c": "AiCopilot__ReactTopicPrompt",
        "feature__c": "plannerservice",
        "promptTokens__c": prompt_tok,
        "completionTokens__c": completion_tok,
        "totalTokens__c": total_tok,
        "prompt__c": f"This is the prompt body for {req_id}.",
    }


def _gw_response(req_id: str, resp_id: str, ts: str, finish: str) -> dict:
    """Shape mirrors GenAIGatewayResponse__dlm rows as fetched.

    parameters__c is HTML-escaped JSON with the finish_reason value
    wrapped in escaped quotes — the exact on-wire shape the live fetcher
    produces. Mirrors the fixture used elsewhere in the test suite.
    """
    # Build the raw JSON first, then HTML-escape the quotes the same way
    # the gateway serializer does.
    raw = '{"finish_reason":"\\"' + finish + '\\""}'
    escaped = raw.replace('"', "&quot;")
    return {
        "generationResponseId__c": resp_id,
        "generationRequestId__c": req_id,
        "parameters__c": escaped,
        "timestamp__c": ts,
    }


def _tag(req_id: str, key: str, value: str) -> dict:
    return {
        "id__c": f"tag-{req_id}-{key}",
        "parent__c": req_id,
        "tag__c": key,
        "tagValue__c": value,
    }


def _md(req_id: str, mtype: str, payload: str) -> dict:
    return {
        "id__c": f"md-{req_id}",
        "parent__c": req_id,
        "metadataType__c": mtype,
        "metadata__c": payload,
    }


def _make_rows() -> dict:
    session_row = {
        "ssot__Id__c": _SID,
        "ssot__StartTimestamp__c": "2026-05-03T10:00:00.000Z",
        "ssot__EndTimestamp__c": None,
        "ssot__AiAgentChannelType__c": "EmbeddedMessaging",
        "ssot__AiAgentSessionEndType__c": None,
    }
    return {
        "sessions": [session_row],
        "participants": [],
        "messages": [],
        "moments": [],
        "interactions": [],
        "steps": [],
        "generations": [],
        "gateway_requests": [
            _gw_request("gw-1", "2026-05-03T10:00:01.000Z", "gpt-4o", (100, 50, 150)),
            _gw_request("gw-2", "2026-05-03T10:00:05.000Z", "gpt-4o", (200, 80, 280)),
            _gw_request("gw-3", "2026-05-03T10:00:10.000Z", "gpt-4o-mini", (50, 30, 80)),
        ],
        "gateway_responses": [
            _gw_response("gw-1", "resp-1", "2026-05-03T10:00:02.500Z", "stop"),
            _gw_response("gw-2", "resp-2", "2026-05-03T10:00:06.000Z", "tool_calls"),
            _gw_response("gw-3", "resp-3", "2026-05-03T10:00:11.000Z", "stop"),
        ],
        "gateway_request_tags": [
            _tag("gw-1", "bot_id", "0Xx000000000001"),
            _tag("gw-2", "feature", "plannerservice"),
        ],
        "gateway_request_metadata": [
            _md("gw-2", "ToolCall", '{"tool":"apex"}'),
        ],
        "gateway_request_llm": [],
        "content_quality": [],
        "content_category": [],
        "feedback": [],
        "feedback_details": [],
        "gateway_records": [],
        "tag_associations": [],
        "tag_definitions": [],
        "tag_definition_associations": [],
        "tags": [],
        "app_generation": [],
        "telemetry_spans": [],
        "moment_interactions": [],
    }


def _make_manifest() -> dict:
    return {
        "session_id": _SID,
        "org_alias": "test-org",
        "instance_url": "https://example.my.salesforce.com",
        "org_id_15": "00DXX0000000001",
        "agent_api_name": "My_Agent",
        "agent_version": "v1",
        "session_shape": "interactions_not_materialized_yet",
        "queries": [],
    }


class AssembleGatewayDirectTests(unittest.TestCase):

    def setUp(self):
        self.rows = _make_rows()
        self.manifest = _make_manifest()
        self.tree = _assemble_gateway_direct(
            _SID, self.rows, self.manifest, parse_warnings=[])

    def test_source_sentinel(self):
        """The render layer keys off this exact string."""
        self.assertEqual(self.tree["_source"], "gateway_direct")

    def test_interactions_is_explicit_empty_list(self):
        """Downstream consumers walk session.interactions — must exist + be empty."""
        self.assertEqual(self.tree["session"]["interactions"], [])

    def test_gateway_chain_length_matches_input(self):
        self.assertEqual(len(self.tree["session"]["gateway_chain"]), 3)

    def test_each_chain_entry_has_response_timestamp(self):
        """Join via generationRequestId__c must populate response.timestamp on each."""
        for call in self.tree["session"]["gateway_chain"]:
            with self.subTest(req_id=call.get("gateway_request_id")):
                self.assertIsNotNone(call.get("response"))
                self.assertIsNotNone(call["response"].get("timestamp"))

    def test_finish_reason_parsed(self):
        """HTML-escaped, quote-wrapped finish_reason must decode to bare string."""
        reasons = [c["response"]["finish_reason"]
                   for c in self.tree["session"]["gateway_chain"]]
        self.assertEqual(reasons, ["stop", "tool_calls", "stop"])

    def test_chain_sorted_by_timestamp(self):
        """Deterministic ordering — required for byte-identical output across runs."""
        timestamps = [c["timestamp"] for c in self.tree["session"]["gateway_chain"]]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_model_and_tokens_harvested(self):
        first = self.tree["session"]["gateway_chain"][0]
        self.assertEqual(first["model"], "gpt-4o")
        self.assertEqual(first["provider"], "openai")
        self.assertEqual(first["prompt_template_dev_name"],
                         "AiCopilot__ReactTopicPrompt")
        self.assertEqual(first["prompt_tokens"], 100)
        self.assertEqual(first["total_tokens"], 150)

    def test_prompt_text_untruncated_on_disk(self):
        """Assembler stores the full prompt — the 64 KB cap is render-only."""
        for call in self.tree["session"]["gateway_chain"]:
            self.assertIn("This is the prompt body for",
                          call.get("prompt_text") or "")

    def test_identity_block_present(self):
        """Top-level identity must carry (org_id_15, agent_api_name, agent_version)."""
        self.assertEqual(self.tree["identity"]["org_id_15"], "00DXX0000000001")
        self.assertEqual(self.tree["identity"]["agent_api_name"], "My_Agent")
        self.assertEqual(self.tree["identity"]["agent_version"], "v1")

    def test_stdm_lag_note_on_session(self):
        note = self.tree["session"].get("_stdm_lag_note") or ""
        self.assertIn("materialize on a separate cadence", note)

    def test_counts_reflect_input_rows(self):
        counts = self.tree["session"]["counts"]
        self.assertEqual(counts["gateway_requests"], 3)
        self.assertEqual(counts["gateway_responses"], 3)
        self.assertEqual(counts["interactions_total"], 0)
        self.assertEqual(counts["steps_total"], 0)
        self.assertEqual(counts["session_shape"],
                         "interactions_not_materialized_yet")


if __name__ == "__main__":
    unittest.main()
