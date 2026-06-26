# Artifacts reference

Every successful trace lands artifacts under
`~/.vibe/data/agentforce-d360-analyze/<org_id15>/<agent>__<ver>/<sid>/`.
Re-running the same `(org, sid)` overwrites in place. Listed below in
the order they're produced.

```
~/.vibe/data/agentforce-d360-analyze/<org_id15>/<agent>__<ver>/<sid>/
├── dc._session_manifest.json ← per-query counts + session_shape + empties
├── dc._session_tree.json ← hierarchical join (primary artifact)
├── dc._session_summary.md ← human-readable summary, up to 11 sections (varies with session_shape + identity bootstrap + --show-prompts opt-in)
├── dc.sessions.json ← 1 row (STDM session)
├── dc.interactions.json ← N rows (TURN + SESSION_END)
├── dc.messages.json ← USER + AGENT messages
├── dc.steps.json ← LLM_STEP / ACTION_STEP / TOPIC_STEP / TRUST_GUARDRAILS_STEP / SESSION_END
├── dc.participants.json ← USER + AGENT participants
├── dc.generations.json ← LLM generations
├── dc.gateway_requests.json ← gateway-logged LLM calls
├── dc.gateway_responses.json ← 1:1 with gateway_requests
├── dc.gateway_request_tags.json ← tag rows (bot_id, agent_version_api_name, etc.)
├── dc.gateway_request_metadata.json ← per-call metadata
├── dc.content_quality.json ← Trust Layer quality scores
├── dc.content_category.json ← toxicity + other category rows
├── dc.feedback.json ← user thumbs-up/down (often empty)
├── dc.feedback_details.json ← feedback text (often empty)
├── dc.moments.json ← optional Agent Optimization rollup (often empty)
├── dc.moment_interactions.json ← moment→interaction junction (often empty)
├── dc.tag_*.json ← org-wide agent tag catalog (often empty)
├── dc.telemetry_spans.json ← usually empty (Agent Platform Tracing off)
├── dc.app_generation.json ← reserved, always empty today
├── dc.gateway_records.json ← grounded attachments (rare)
├── dc.gateway_request_llm.json ← writer inactive on observed orgs
└── dc.tag_associations.json ← agent↔tag links (often empty)
```

## Read order

1. **`dc._session_summary.md`** — human-readable, top-to-bottom answers
 "what happened in this session?"
2. **`dc._session_tree.json`** — single source of truth, the
 hierarchical join the summary was rendered from. Open this when the
 summary is missing a detail you need.
3. **`dc._session_manifest.json`** — per-DMO row counts, classified
 `session_shape`, and empty-by-design reasons for any DMO that
 returned zero rows. Open this when something looks missing in the
 tree.
4. **`dc.<name>.json`** — raw per-DMO rows. Only needed when the
 manifest reports an unexpected count or the assembler logs a parse
 warning.
