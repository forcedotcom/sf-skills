# STDM + GenAI DMO field reference

> **Convention.** Executable SQL literals live under `assets/dc/*.sql`
> and are loaded by scripts via `dc.load_sql`. Reference docs (including
> this one) describe query shape, column meaning, and join topology in
> prose — they do **not** contain the literal the engine would execute.
> Rationale: loaders parse, comment-strip, and placeholder-substitute
> the asset files; `.md` code fences are inert. A query literal in
> `.md` is orphan code with no linter coverage and no guarantee it
> matches the live schema.

Field reference for the DMOs this skill touches. **24 queried** by the
`scripts/fetch_dc.py` waterfall (one `.sql` template each under
`assets/dc/`). All field lists are copy-pasteable into `assets/dc/*.sql`
SELECT lists. Schemas verified against live Data Cloud v66.0 via
`sf ssot/metadata` describes; join paths verified by running the
waterfall end-to-end on live sessions.

**Source of truth: the live org** (`sf ssot/metadata?entityName=<dmo>`).
Official Salesforce Help pages list *logical* API names and aspirational
enum values that frequently diverge from the physical names and runtime
values the Data Cloud API actually exposes. When a Help page disagrees
with a live describe, trust the live describe — the names and enums in
this reference are what you query.

Official doc pointers (for context, not authority — Session Tracing doc
uses logical API names and aspirational enum values that diverge from
what the live `sf ssot/metadata` describe returns; trust the live describe):
- Session Tracing DMOs: https://help.salesforce.com/s/articleView?id=ai.generative_ai_session_trace_data_model.htm&type=5
- Generative AI Audit and Feedback DMOs: https://help.salesforce.com/s/articleView?id=ai.generative_ai_feedback_data_model.htm&type=5
- Agent Optimization DMOs: https://help.salesforce.com/s/articleView?id=ai.generative_ai_optimize_data_model.htm&type=5
- Agent Platform Tracing (`ssot__TelemetryTraceSpan__dlm`): https://help.salesforce.com/s/articleView?id=ai.generative_ai_platform_trace.htm&type=5

**Casing gotchas (important):**
- DMO table casing is **mixed** — don't assume a single rule. Three STDM DMOs use uppercase `AIAgent` (`ssot__AIAgentSession__dlm`, `ssot__AIAgentInteraction__dlm`, `ssot__AIAgentInteractionStep__dlm`); all other `ssot__*AiAgent*__dlm` tables use lowercase `AiAgent`. Trust the exact name in each section header or the live `describe`.
- Field names consistently use **`AiAgent`** (lowercase `i`), e.g. `ssot__AiAgentSessionId__c`, across every DMO.
- Generative AI Audit and Feedback DMOs (`GenAIGeneration`, `GenAIContentQuality`, `GenAIContentCategory`, and the 9 other DMOs in that family — see below) do **not** use the `ssot__` prefix. Their fields end in `__c`, not `ssot__*__c`.

---

## Cross-DMO join map

Every edge is strictly **forward** from Session. `scripts/fetch_dc.py` runs
the tree as a 5-wave waterfall; each child query keys off ids harvested
from parents in earlier waves. No backward lookups, no cross-validation
paths — if a DMO can't be reached by a forward FK from Session, it's not
fetched.

The audit/cost chain (GatewayRequest and its children) enters the tree
forward through `GenAIGatewayRequest.sessionId__c`. Storage gotcha: the
value is stored as a literal 40-char string INCLUDING surrounding
double-quotes, e.g. `"<session_uuid>"`. Non-session features store the
sentinel `"no_session"`. A raw-UUID exact match returns 0 rows; use
`sessionId__c LIKE '%<sid>%'` or `sessionId__c = '"<sid>"'`.

Per-run row counts, empty reasons, and join paths are recorded in
`dc._session_manifest.json`.

Legend: ★ = session-FK direct (one hop) ▸ = polymorphic `parent__c`
 ⚠ = requires feature provisioning

```
Session (ssot__AIAgentSession__dlm, PK ssot__Id__c)
 │
 ├── ★ Participant (ssot__AiAgentSessionId__c)
 │
 ├── ★ Message (ssot__AiAgentSessionId__c)
 │ └── Message.participant (ssot__AiAgentSessionParticipantId__c → Participant.ssot__Id__c)
 │
 ├── ★ Moment (ssot__AiAgentSessionId__c)
 │ └── MomentInteraction (ssot__AiAgentMomentId__c, ssot__AiAgentInteractionId__c)
 │
 ├── ★ TagAssociation ▸ (ssot__AiAgentSessionId__c when target is session;
 │ ssot__AiAgentInteractionId__c when target is turn;
 │ ssot__AiAgentMomentId__c when target is moment —
 │ exactly one of the three is populated per row)
 │ ├── → AiAgentTag (ssot__AiAgentTagId__c = Tag.ssot__Id__c)
 │ │ └── TagDefinition (Tag.ssot__AiAgentTagDefinitionId__c =
 │ │ TagDefinition.ssot__Id__c)
 │ │ — catalog, not session-keyed; query with
 │ │ ssot__Status__c = 'Available' (verified live;
 │ │ Help docs' 'Active' value does not match live data)
 │ └── → TagDefinitionAssociation
 │ (ssot__AiAgentTagDefinitionAssociationId__c = TagDefAssoc.ssot__Id__c)
 │ — catalog, not session-keyed; query by ssot__AiAgentApiName__c IN
 │ {agent_api_names from Participant(role='AGENT') ∪ Moment}
 │ (Participant is the primary source — Moment rows may be absent on
 │ orgs without Agent Optimization enabled)
 │
 ├── ★ Interaction (ssot__AiAgentSessionId__c)
 │ ├── Step (ssot__AiAgentInteractionId__c)
 │ │ └── GenAIGeneration (step.ssot__GenerationId__c IN {generationId__c})
 │ │ │ (assembly bridge → references/dc_pipeline_contract.md:
 │ │ │ Generation.generationResponseId__c =
 │ │ │ GatewayResponse.generationResponseId__c)
 │ │ ├── GenAIContentQuality (parent__c = generationId__c)
 │ │ │ └── GenAIContentCategory ▸ (parent__c = Quality.id__c;
 │ │ │ toxicity sub-category rows)
 │ │ ├── GenAIContentCategory ▸ (parent__c = generationId__c;
 │ │ │ non-toxicity detector rows)
 │ │ ├── GenAIAppGeneration (generationId__c = Gen.generationId__c;
 │ │ │ sibling record, often empty on observed orgs)
 │ │ └── GenAIFeedback (generationId__c)
 │ │ ├── GenAIFeedbackDetail (parent__c = feedback.feedbackId__c)
 │ │ └── GenAIGtwyObjRecord ▸ (parent__c = feedback.feedbackId__c
 │ │ when type__c is a feedback attachment)
 │ └── ⚠ TelemetryTraceSpan (ssot__TelemetryTrace__c IN {trace_ids};
 │ trace_ids extracted from Interaction.ssot__AttributeText__c via
 │ html.unescape() + regex "internalTraceId":"([a-f0-9]+)" —
 │ Interaction.ssot__TelemetryTraceId__c column is usually empty.
 │ Requires Agent Platform Tracing enabled on the org.)
 │
 └── ★ GenAIGatewayRequest (sessionId__c LIKE '%<sid>%')
 │ — one row per LLM call owned by the session,
 │ across all features (plannerservice,
 │ PromptTemplateGenerationsInvocable, etc.)
 │
 ├── GenAIGatewayResponse (generationRequestId__c = gatewayRequestId__c)
 ├── GenAIGatewayRequestTag (parent__c = gatewayRequestId__c)
 ├── GenAIGtwyObjRecord ▸ (parent__c = gatewayRequestId__c
 │ when type__c = grounded record attachment;
 │ populated only for grounding features —
 │ planner-only sessions produce 0 rows)
 ├── GenAIGtwyRequestMetadata (parent__c = gatewayRequestId__c;
 │ typed metadata rows, e.g. ToolCall payloads)
 └── ⚠ GenAIGtwyRequestLLM (parent__c = gatewayRequestId__c;
 per-call LLM diagnostics; schema provisioned
 but writer inactive on every sandbox observed
 — treat as aspirational)
```

### How to "join all 24" from one session id

All 24 entries below are in the `scripts/fetch_dc.py` waterfall — the
join expressions are exactly what the script runs, and each one has a
`.sql` template under `assets/dc/`.

```
 1. sessions WHERE ssot__Id__c = {sid}
 2. interactions WHERE ssot__AiAgentSessionId__c = {sid}
 3. messages WHERE ssot__AiAgentSessionId__c = {sid}
 4. moments WHERE ssot__AiAgentSessionId__c = {sid}
 5. participants WHERE ssot__AiAgentSessionId__c = {sid}
 6. tag_associations WHERE ssot__AiAgentSessionId__c = {sid}
 7. gateway_requests WHERE sessionId__c LIKE '%{sid}%'
 — sessionId__c is stored quoted (e.g. '"<sid>"');
 raw-UUID exact match returns 0. Equivalent
 exact form: sessionId__c = '"{sid}"'
 8. steps WHERE ssot__AiAgentInteractionId__c IN {interaction_ids}
 9. moment_interactions WHERE ssot__AiAgentInteractionId__c IN {interaction_ids}
10. telemetry_spans WHERE ssot__TelemetryTrace__c IN {trace_ids_from_AttributeText}
11. generations WHERE generationId__c IN {step.ssot__GenerationId__c values}
12. gateway_request_tags WHERE parent__c IN {gateway_request_ids}
13. gateway_responses WHERE generationRequestId__c IN {gateway_request_ids}
14. gateway_records (→ GenAIGtwyObjRecord__dlm) WHERE parent__c IN {gateway_request_ids}
15. feedback WHERE generationId__c IN {generation_ids}
16. content_quality WHERE parent__c IN {generation_ids}
17. content_category WHERE parent__c IN ({generation_ids} ∪ {content_quality.id__c})
18. feedback_details WHERE parent__c IN {feedback.feedbackId__c}
19. tag_definitions WHERE ssot__Status__c = 'Available'
 — not keyed by session (tag vocabulary)
20. tag_definition_associations WHERE ssot__AiAgentApiName__c IN
 {agent_api_names from Participant(role='AGENT') ∪ Moment}
 — keyed by agent, not session. Participant is primary
 (Moment rows may be absent without Agent Optimization)
21. tags WHERE ssot__AiAgentTagDefinitionId__c IN
 {tag_definition.ssot__Id__c}
 — tag VALUES; session reaches them via TagAssociation

22. app_generation WHERE generationId__c IN {step.ssot__GenerationId__c values}
 — app-layer twin of GenAIGeneration
23. gateway_request_metadata WHERE parent__c IN {gateway_request_ids}
 — verified live: parent__c → GatewayRequest.gatewayRequestId__c
24. gateway_request_llm WHERE parent__c IN {gateway_request_ids}
 — same parent pattern as Metadata; writer inactive on
 observed sandboxes (0 rows expected until enabled)
```

---

### DMO materialization timing

Data Cloud DMOs don't all appear at the same time. Gateway DMOs
materialize within minutes; STDM Interaction/Step/Message DMOs can
take hours to days.

| DMO | Table | Materializes | Notes |
|---|---|---|---|
| Session | `ssot__AIAgentSession__dlm` | Minutes | Always query first |
| Participant | `ssot__AiAgentSessionParticipant__dlm` | Minutes | Fast |
| GatewayRequest | `GenAIGatewayRequest__dlm` | Minutes | Direct FK via `sessionId__c LIKE` |
| GatewayResponse | `GenAIGatewayResponse__dlm` | Minutes | Joins via `generationRequestId__c` |
| GatewayRequestTag | `GenAIGatewayRequestTag__dlm` | Minutes | `parent__c = gatewayRequestId__c` |
| GtwyRequestMetadata | `GenAIGtwyRequestMetadata__dlm` | Minutes | `parent__c = gatewayRequestId__c` |
| Moment | `ssot__AiAgentMoment__dlm` | Hours–days | Often empty on same-day |
| Interaction | `ssot__AIAgentInteraction__dlm` | **Hours–days** | Do NOT use as query anchor for fresh sessions — `fetch_dc.py` classifies this as `session_shape=interactions_not_materialized_yet` and renders the gateway-direct view |
| Message | `ssot__AiAgentSessionMessage__dlm` | Hours–days | Downstream of Interaction |
| Step | `ssot__AIAgentInteractionStep__dlm` | Hours–days | Downstream of Interaction |
| Generation | `GenAIGeneration__dlm` | Hours–days | Downstream of Step |
| GtwyRequestLLM | `GenAIGtwyRequestLLM__dlm` | N/A | Writer inactive on sandboxes |

---

## Session Tracing DMOs (5)

### `ssot__AIAgentSession__dlm` — one row per session

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | Session UUID (what users pass in) |
| `ssot__StartTimestamp__c` | string (ISO UTC) | |
| `ssot__EndTimestamp__c` | string (ISO UTC) | null while active |
| `ssot__AiAgentSessionEndType__c` | string | Completed / Abandoned / Escalated / etc. |
| `ssot__AiAgentChannelType__c` | string | e.g. "SCRT2 - EmbeddedMessaging", "Voice" |
| `ssot__RelatedMessagingSessionId__c` | string | |
| `ssot__RelatedVoiceCallId__c` | string | |
| `ssot__InternalOrganizationId__c` | string | 18-char org id |
| `ssot__SessionOwnerId__c` | string | |
| `ssot__SessionOwnerObject__c` | string | Owner type, e.g. "User" |
| `ssot__IndividualId__c` | string | Data 360 individual id |
| `ssot__PreviousSessionId__c` | string | Conversation-chain link to prior session |
| `ssot__VariableText__c` | string | Session-level variables, JSON. Channel-specific bootstrap dict (e.g. `__resolved_locale__`, `__supports_result_display__`, `__user_dst_offset_ms__`). Parsed at assemble time into `session.identity.bootstrap_variables`. The presence of Builder-Previewer-only keys (`__supports_result_display__` etc.) is one input to the derived `session.identity.mode` field — see dc_pipeline_contract.md §2.9a. |

Note: **agent API name is NOT on Session**. Join with Moment to get agent info.

### `ssot__AiAgentSessionParticipant__dlm` — one row per participant per session

Roles: `USER`, `AGENT`.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentSessionId__c` | string (FK) | → Session.Id |
| `ssot__ParticipantId__c` | string | MessagingEndUser id (USER) or GenAiPlannerDefinition id (AGENT) |
| `ssot__AiAgentApiName__c` | string | Bot identity — omit on USER rows |
| `ssot__AiAgentType__c` | string | e.g. "DemoAgentType" |
| `ssot__AiAgentTemplateApiName__c` | string | |
| `ssot__AiAgentVersionApiName__c` | string | e.g. "v5" |
| `ssot__AiAgentSessionParticipantRole__c` | string | USER \| AGENT |
| `ssot__ParticipantObject__c` | string | e.g. "MessagingEndUser", "GenAiPlannerDefinition" |
| `ssot__StartTimestamp__c` | string | |
| `ssot__EndTimestamp__c` | string | |
| `ssot__IndividualId__c` | string | Data 360 individual id |
| `ssot__InternalOrganizationId__c` | string | 18-char org id |
| `ssot__ParticipantAttributeText__c` | string | JSON — per-participant metadata |

### `ssot__AIAgentInteraction__dlm` — one row per turn (and session-end event)

Types: `TURN`, `SESSION_END`.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | Turn/interaction UUID |
| `ssot__AiAgentSessionId__c` | string (FK) | → Session.Id |
| `ssot__AiAgentInteractionType__c` | string | TURN \| SESSION_END |
| `ssot__TopicApiName__c` | string | Which topic handled this turn |
| `ssot__StartTimestamp__c` | string | |
| `ssot__EndTimestamp__c` | string | |
| `ssot__PrevInteractionId__c` | string | |
| `ssot__SessionOwnerId__c` | string | |
| `ssot__IndividualId__c` | string | |
| `ssot__InternalOrganizationId__c` | string | |
| `ssot__TelemetryTraceId__c` | string | Often empty on real orgs (verified live). See note below. |
| `ssot__TelemetryTraceSpanId__c` | string | Often empty — same caveat as above. |
| `ssot__AttributeText__c` | string | HTML-escaped JSON. Holds `internalTraceId` + `internalSpanId` — the real runtime trace_id when `TelemetryTraceId__c` is empty. Consumers: `html.unescape()` + regex `"internalTraceId":"([a-f0-9]+)"`. |

### `ssot__AiAgentInteractionMessage__dlm` — one row per user/agent message

Types: `Input`, `Output`.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentSessionId__c` | string (FK) | → Session.Id — direct session FK (verified v66.0) |
| `ssot__AiAgentInteractionId__c` | string (FK) | → Interaction.Id |
| `ssot__AiAgentSessionParticipantId__c` | string (FK) | → Participant.Id — who sent/received the message |
| `ssot__ParentMessageId__c` | string | Threading — prior message in a nested conversation |
| `ssot__ContentText__c` | string | The actual message text |
| `ssot__AiAgentInteractionMessageType__c` | string | Input \| Output |
| `ssot__AiAgentInteractionMsgContentType__c` | string | Content MIME/type (text/audio/etc.) |
| `Modality__c` | string | e.g. Text, Voice — no `ssot__` prefix |
| `ssot__MessageSentTimestamp__c` | string | Single-point timestamp (text channels) |
| `MessageStartTimestamp__c` | datetime | Start of message (voice/streaming) — no `ssot__` prefix |
| `MessageEndTimestamp__c` | datetime | End of message (voice/streaming) — no `ssot__` prefix |
| `ssot__InternalOrganizationId__c` | string | 18-char org id |

**Messages have a direct session FK** (`ssot__AiAgentSessionId__c`) — scope by session directly; earlier docs claiming otherwise were wrong. The interaction FK is still useful for per-turn joins.

### `ssot__AIAgentInteractionStep__dlm` — one row per planner step

Types observed in live data:
`LLM_STEP`, `ACTION_STEP`, `TOPIC_STEP`, `TRUST_GUARDRAILS_STEP`, `SESSION_END`.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentInteractionId__c` | string (FK) | → Interaction.Id |
| `ssot__AiAgentInteractionStepType__c` | string | LLM_STEP \| ACTION_STEP \| TOPIC_STEP \| TRUST_GUARDRAILS_STEP \| SESSION_END |
| `ssot__Name__c` | string | step/action name (e.g. "AiCopilot__ReactTopicPrompt") |
| `ssot__InputValueText__c` | string | HTML-escaped JSON; parse after `html.unescape` |
| `ssot__OutputValueText__c` | string | HTML-escaped JSON; parse after `html.unescape` |
| `ssot__PreStepVariableText__c` | string | |
| `ssot__PostStepVariableText__c` | string | |
| `ssot__GenerationId__c` | string | → `GenAIGeneration.generationId__c`. Populated only on `LLM_STEP` rows (in live samples, most LLM_STEP rows populate it); `NOT_SET` on every other step type. This is the only Step→Generation join key used by the waterfall. |
| `ssot__ErrorMessageText__c` | string | Sentinel `NOT_SET` when no error (never NULL). Filter errors with `!= 'NOT_SET'`, not `IS NOT NULL`. |
| `ssot__StartTimestamp__c` | string | |
| `ssot__EndTimestamp__c` | string | |
| `ssot__PrevStepId__c` | string | |
| `ssot__InternalOrganizationId__c` | string | |
| `ssot__TelemetryTraceSpanId__c` | string | |
| `ssot__AttributeText__c` | string | |
| `ssot__GenAiGatewayRequestId__c` | string | Schema-only FK. Live data shows this is frequently `NOT_SET` even on `LLM_STEP` rows. **Not used by the waterfall** — GatewayRequest is fetched forward from Session via `sessionId__c`, which is the authoritative set and covers requests this FK doesn't reach. |
| `ssot__GenAiGatewayResponseId__c` | string | Schema-only FK. Same as above — documented for schema completeness, not used as a join key. Following it back to GatewayResponse is a backward-reasoning pattern and rejected by the skill design. |

Join: steps lack a direct session FK — go through Interaction.

**Step Gateway FKs are not join keys.** The three Gateway-related FK
columns (`ssot__GenAiGatewayRequestId__c`, `ssot__GenAiGatewayResponseId__c`)
are included in the SELECT for schema completeness but are not used to
reach any downstream DMO. GatewayRequest is entered forward from Session
via `GatewayRequest.sessionId__c` (see gateway_requests section); its
children flow forward from there. Only `ssot__GenerationId__c` is used
as a forward Step → Generation key.

---

## Generative AI Audit and Feedback DMOs (12 of 13 documented)

Canonical umbrella per the Salesforce Help article
[Data Model for Generative AI Audit and Feedback](https://help.salesforce.com/s/articleView?id=ai.generative_ai_feedback_data_model.htm&type=5).
Spans the full Einstein generative AI audit chain: LLM requests and responses
at the gateway, trust-layer safety scoring, and user-side feedback on
generations.

**No `ssot__` prefix.** Fields end in `__c` directly.

Data 360 Data Lake Objects (DLOs) that contain generative AI audit and
feedback data map to custom DMOs (legacy) and standard DMOs. The 13 DMOs
in this family per the Help article:

| DLO | Custom DMO (legacy) | Standard DMO | Queried by `fetch_dc.py`? |
|---|---|---|---|
| GenAIAppGeneration | `GenAIAppGeneration__dlm` | Ai Response App Generation | ✓ |
| GenAIContentCategory | `GenAIContentCategory__dlm` | Ai Content Quality Category | ✓ |
| GenAIContentQuality | `GenAIContentQuality__dlm` | Ai Content Quality | ✓ |
| GenAIFeedback | `GenAIFeedback__dlm` | Ai Feedback | ✓ |
| GenAIFeedbackDetail | `GenAIFeedbackDetail__dlm` | Ai Feedback Additional Info | ✓ |
| GenAIGatewayRequest | `GenAIGatewayRequest__dlm` | Ai Gateway Request | ✓ |
| GenAIGatewayRequestTag | `GenAIGatewayRequestTag__dlm` | Ai Gateway Request Tag | ✓ |
| GenAIGatewayResponse | `GenAIGatewayResponse__dlm` | Ai Gateway Response | ✓ |
| GenAIGeneration | `GenAIGeneration__dlm` | Ai Response Generation | ✓ |
| GenAIGtwyRequestMetadata | `GenAIGtwyRequestMetadata__dlm` | Ai Gateway Req Additional Info | ✓ |
| GenAIGtwyRequestLLM | `GenAIGtwyRequestLLM__dlm` | Ai Gateway Request Model Diagnostic | ✓ |
| GenAIGtwyObjRecord | `GenAIGtwyObjRecord__dlm` | Ai Gateway Request Object Record | ✓ |

The Help article lists one additional DMO in this family —
`GenAIGtwyObjRecCitation__dlm` (standard DMO: **Ai Gateway Req Object
Record Citation**). It is not documented here: live `describe` returns
"DMO with developerName 'GenAIGtwyObjRecCitation' not found" on the
tested org, so we have no verified schema or join column. Bring it in
once it's provisioned on a test org.

All 12 DMOs marked ✓ above are queried by the 24-query `fetch_dc.py`
waterfall. Their `.sql` templates are under `assets/dc/` and their full
schemas are documented in the per-DMO sections below.

### `GenAIGeneration__dlm` — one row per LLM call at the gateway

**Joining to a session:** this DMO has NO `sessionId__c`, `traceId__c`, or
`turnId__c` column (verified via live `describe`; 11 fields total,
none reference session/trace/turn). The canonical join path is:

```
Session → Interaction → Step (.ssot__GenerationId__c) → Generation (.generationId__c)
```

Pull session steps, collect non-empty `ssot__GenerationId__c` values
(many steps have `NOT_SET`), then filter by `generationId__c IN (...)`.

There is no backward chain to this DMO from GatewayRequest/Response.
The waterfall only reaches `GenAIGeneration__dlm` via the forward
Step→Generation path above; Generation rows for LLM calls that aren't
owned by an LLM_STEP are not fetched by this skill.

| Field | Type | Notes |
|---|---|---|
| `generationId__c` | string (PK) | Forward join key from `Step.ssot__GenerationId__c`. |
| `generationResponseId__c` | string | Provider-issued response id (OpenAI-style `chatcmpl-*`, Gemini/Anthropic use their own prefixes). Not used as a join key. |
| `responseText__c` | string | HTML-escaped JSON for tool-calling outputs; `html.unescape()` before parsing. |
| `maskedResponseText__c` | string | PII-masked version |
| `responseParameters__c` | string | JSON |
| `feature__c` | string | e.g. "plannerservice", "Guardrails and Citations" |
| `timestamp__c` | string | |
| `orgId__c` | string | |
| `cloud__c` | string | e.g. "Platform" |

### `GenAIContentQuality__dlm` — per-generation quality row

Joined to a generation via `parent__c = generationId__c`.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GenAIGeneration.generationId__c` |
| `isToxicityDetected__c` | string | "true" / "false" — populated only on OUTPUT rows |
| `contentType__c` | string | INPUT \| OUTPUT |
| `feature__c` | string | |
| `timestamp__c` | string | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIContentCategory__dlm` — per-category detector row

Joined either to a generation (direct, non-TOXICITY detectors like
`InstructionAdherence`) or to a quality row (TOXICITY sub-categories).
The `parent__c` FK points to whichever parent emitted it.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GenAIGeneration.generationId__c` OR `GenAIContentQuality.id__c` |
| `detectorType__c` | string | TOXICITY \| PII \| PROMPT_DEFENSE \| InstructionAdherence \| TaskResolution |
| `category__c` | string | e.g. "violence", "safety_score", "Low" / "Medium" / "High" |
| `value__c` | string | "0.0" – "1.0" as string; convert to float in analysis |
| `timestamp__c` | string | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGatewayRequest__dlm` — one row per LLM request at the gateway

Richer than `GenAIGeneration` — carries prompt text, tokens, model, and
session/user/bot identifiers. **Forward entry point for the entire audit
chain**, reached from Session via `sessionId__c`:

```
Session.ssot__Id__c → GatewayRequest.sessionId__c LIKE '%<sid>%'
```

`sessionId__c` is stored as a literal quoted string (e.g. `"<uuid>"`), so a
raw-UUID exact match returns 0 rows; use LIKE or `sessionId__c = '"<sid>"'`.
See `assets/dc/gateway_requests.sql` for details.

GatewayRequest is the parent for all downstream audit DMOs — Response,
RequestTag, GtwyObjRecord, RequestMetadata, RequestLLM — each keyed by
`generationRequestId__c` or `parent__c = gatewayRequestId__c`.

| Field | Type | Notes |
|---|---|---|
| `gatewayRequestId__c` | string (PK) | |
| `generationGroupId__c` | string | Groups multiple generations for one user-visible turn |
| `sessionId__c` | string | Session FK — the forward entry point. Stored as a quoted string (e.g. `"<uuid>"`) or sentinel `"no_session"`. Query with `sessionId__c LIKE '%<sid>%'` or exact `sessionId__c = '"<sid>"'`; raw-UUID match returns 0 rows. |
| `userId__c` | string | End-user id |
| `botVersionId__c` | string | Agent version id |
| `plannerId__c` | string | Planner id (ReAct etc.) |
| `feature__c` | string | e.g. `CopilotForDigitalChannels` |
| `appType__c` | string | |
| `model__c` | string | e.g. `gpt-4o-2024-11-20` |
| `provider__c` | string | e.g. `openai`, `azureOpenAI`, `salesforce` |
| `promptTemplateDevName__c` | string | e.g. `AiCopilot__ReactTopicPrompt`, `Atlas__AgentGraphReasoningPrompt`. Surfaced through the hierarchical view as `gateway_request.prompt_template_dev_name`. |
| `promptTemplateVersionNo__c` | string | |
| `prompt__c` | string | **Full input prompt sent to the model** — `role: system` / `role: user` / `role: assistant` segments, tool definitions, conversation history. Up to 30 KB+ on observed sessions. Carried through the hierarchical view as `gateway_request.prompt_text`; surfaced verbatim by `render_dc.py --show-prompts` (off by default; per-prompt display capped at 64 KB). HTML-escaped on the wire (`&quot;` etc.) — renderer unescapes before display. |
| `maskedPrompt__c` | string | PII-masked variant of `prompt__c`. Empty when `enablePiiMasking__c = "false"`; populated when masking is enabled. |
| `parameters__c` | string | JSON — extra invocation params |
| `temperature__c` | number | |
| `frequencyPenalty__c` | number | |
| `presencePenalty__c` | number | |
| `stopSequences__c` | string | |
| `numGenerations__c` | number | |
| `promptTokens__c` | number | |
| `completionTokens__c` | number | |
| `totalTokens__c` | number | |
| `enableInputSafetyScoring__c` | string | "true" / "false" |
| `enableOutputSafetyScoring__c` | string | "true" / "false" |
| `enablePiiMasking__c` | string | "true" / "false" |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGatewayResponse__dlm` — one row per LLM call response

Forward join: from GatewayRequest via `generationRequestId__c IN {gw_req_ids}`.
Every GatewayRequest has one Response (modulo in-flight calls at fetch time) —
1:1 invariant verified live.

| Field | Type | Notes |
|---|---|---|
| `generationResponseId__c` | string (PK) | Provider-issued response id (e.g. OpenAI `chatcmpl-*`). Same value also appears on `Step.ssot__GenAiGatewayResponseId__c` and `Generation.generationResponseId__c`, but those are not used as join keys. |
| `generationRequestId__c` | string (FK) | → `GatewayRequest.gatewayRequestId__c`. The forward join key. |
| `parameters__c` | string | JSON |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGatewayRequestTag__dlm` — k/v tags per request

Joined via `parent__c = GatewayRequest.gatewayRequestId__c`. Multiple rows per request.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GatewayRequest.gatewayRequestId__c` |
| `tag__c` | string | e.g. `prompt_template_dev_name`, `user_utterance` |
| `tagValue__c` | string | |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIFeedback__dlm` — user thumbs up/down on a generation

Joined via `generationId__c = Generation.generationId__c`. PK `feedbackId__c`
is the parent for `GenAIFeedbackDetail` rows.

| Field | Type | Notes |
|---|---|---|
| `feedbackId__c` | string (PK) | |
| `generationId__c` | string (FK) | → `Generation.generationId__c` |
| `generationUpdateId__c` | string | |
| `generationGroupId__c` | string | |
| `userId__c` | string | |
| `feedback__c` | string | e.g. `UP`, `DOWN` |
| `action__c` | string | Richer action, e.g. `REGENERATE`, `COPY` |
| `source__c` | string | Channel/app that captured the feedback |
| `feature__c` | string | |
| `appType__c` | string | |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIFeedbackDetail__dlm` — free-text / structured detail per feedback

Joined via `parent__c = Feedback.feedbackId__c`. Zero or more rows per feedback.

| Field | Type | Notes |
|---|---|---|
| `feedbackDetailId__c` | string (PK) | |
| `parent__c` | string (FK) | → `Feedback.feedbackId__c` |
| `feedbackText__c` | string | Free-text user input |
| `appFeedback__c` | string | App-layer reason bucket |
| `feature__c` | string | |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGtwyObjRecord__dlm` — grounded record attachments on gateway requests

Polymorphic. `parent__c` is the id of whatever owns this record (GatewayRequest
for grounded-content attachments, GenAIFeedback for feedback attachments, etc.)
and `type__c` names the DMO the attached record lives in
(e.g. `ssot__KnowledgeArticleVersion__dlm`).

**Populated only on planners that perform grounded retrieval.** Join path is
clean and forward (`Session → GatewayRequest → GtwyObjRecord`), but the child
table is planner-dependent — a planner that doesn't attach grounded records
produces zero rows even when the session is fully traced. Verified live:

- Tool-calling / planner-style Agentforce sessions (request `feature__c =
 'plannerservice'` only): 0 rows across all observed sessions. The planner
 doesn't emit grounded-record attachments.
- Sessions whose requests include `PromptTemplateGenerationsInvocable` or
 `PromptBuilderPreview` features *do* produce rows — e.g. one live turn
 produced a `type__c = ssot__KnowledgeArticleVersion__dlm` attachment via
 the forward chain.

If fetch returns 0 for an Agentforce agent session, first check the
GatewayRequest rows' `plannerId__c` and `feature__c` — a planner that only
shows `plannerservice` feature will not produce child records. This DMO is
also org-gated: across a set of observed sandboxes with ~400K total
GatewayRequest rows, only a minority had any GtwyObjRecord rows at all.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GatewayRequest.gatewayRequestId__c` (forward from session) or `GenAIFeedback.feedbackId__c` (feedback attachment) |
| `recordId__c` | string | Attached record's id in its home DMO |
| `type__c` | string | DMO the record lives in, e.g. `ssot__KnowledgeArticleVersion__dlm` |
| `name__c` | string | |
| `value__c` | string | Often a deep-link URL to the record in the org |
| `metadata__c` | string | JSON |
| `feature__c` | string | |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

The 3 DMOs below are wired into the `fetch_dc.py` waterfall as entries
22–24 with matching `.sql` templates under `assets/dc/` (`app_generation`,
`gateway_request_metadata`, `gateway_request_llm`). Field schemas below are
from live `describe`. Population varies by DMO:
- `GenAIAppGeneration__dlm` — provisioned but not populated on observed orgs.
- `GenAIGtwyRequestMetadata__dlm` — populated whenever the session's
 GatewayRequest rows are populated; one row per request on Agentforce
 sessions (e.g. `ToolCall` payloads for `plannerservice`).
- `GenAIGtwyRequestLLM__dlm` — **0 rows on every sandbox observed**
 (multiple orgs checked; total GatewayRequest rows ~400K, total
 GtwyRequestLLM rows 0). Schema exists, writer appears inactive.

### `GenAIAppGeneration__dlm` — app-layer generation record

Standard DMO: **Ai Response App Generation**. Sibling of
`GenAIGeneration__dlm`: where `GenAIGeneration` is the raw gateway
response, `GenAIAppGeneration` appears to be the app/feature-layer view
of the same generation (separate `id__c` from `generationId__c`).

**Executable query:** `assets/dc/app_generation.sql`.

**Join path:** `generationId__c → GenAIGeneration.generationId__c → AiAgentInteractionStep.ssot__GenerationId__c → Interaction → Session`. Same Step → Generation bridge used for `GenAIGeneration__dlm`.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | App-generation row id — distinct from `generationId__c` |
| `generationId__c` | string (FK) | → `GenAIGeneration.generationId__c` (session join path) |
| `generationUpdate__c` | string | Likely a later revision of the generation |
| `generationUpdateId__c` | string | id of the update row |
| `feature__c` | string | |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGtwyRequestMetadata__dlm` — additional per-request metadata

Standard DMO: **Ai Gateway Req Additional Info**. Child of
`GenAIGatewayRequest__dlm`: holds typed metadata rows for a request.
On live data a sampled row showed `metadataType__c = "ToolCall"` and
`feature__c = "plannerservice"`, so it's where tool-call/planner-side
per-request metadata lives.

**Executable query:** `assets/dc/gateway_request_metadata.sql`.

**Join verified live:** `parent__c → GatewayRequest.gatewayRequestId__c`. A sampled `parent__c` value matched exactly one row in `GenAIGatewayRequest__dlm WHERE gatewayRequestId__c = …`.

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GatewayRequest.gatewayRequestId__c` (verified live) |
| `metadataType__c` | string | Observed: `ToolCall`; other values likely |
| `metadata__c` | string | JSON — the actual metadata payload |
| `feature__c` | string | Observed: `plannerservice` |
| `timestamp__c` | datetime | |
| `orgId__c` | string | |
| `cloud__c` | string | |

### `GenAIGtwyRequestLLM__dlm` — per-request LLM call diagnostics

Standard DMO: **Ai Gateway Request Model Diagnostic**. Child of
`GenAIGatewayRequest__dlm`: captures LLM invocation diagnostics (latency,
status, endpoint, region).

**Cross-org reality check: 0 rows on every sandbox observed.** Checked
multiple sandboxes with a combined ~400K GatewayRequest rows — every one
returned 0 GtwyRequestLLM rows. The schema is provisioned everywhere, but
the writer appears inactive. Treat as aspirational until the feature is
enabled and populated somewhere we can verify. The join path is declared
(by analogy with `GenAIGtwyRequestMetadata`) but not live-verified.

**Executable query:** `assets/dc/gateway_request_llm.sql`.

**Join:** `parent__c → GatewayRequest.gatewayRequestId__c` (inferred from schema symmetry with `GenAIGtwyRequestMetadata`; not verifiable until an org populates the table).

| Field | Type | Notes |
|---|---|---|
| `id__c` | string (PK) | |
| `parent__c` | string (FK) | → `GatewayRequest.gatewayRequestId__c` (by analogy) |
| `endpoint__c` | string | LLM endpoint URL / name |
| `region__c` | string | Cloud region the call ran in |
| `genAILLM__c` | string | Model/LLM identifier |
| `llmCallStatus__c` | string | e.g. success / error |
| `llmCallLatency__c` | number | Latency of the LLM call |
| `llmErrorTrace__c` | string | Error trace when the call failed |
| `metadata__c` | string | JSON — extra diagnostic info |
| `feature__c` | string | |
| `salesforceOrgId__c` | string | Note: `salesforceOrgId__c`, not `orgId__c` |
| `timestamp__c` | datetime | |
| `cloud__c` | string | |

---

## Agent Optimization DMOs (6)

Provisioned only when **Agent Optimization** is enabled (Enterprise/Performance/
Unlimited + an Einstein add-on). Extends STDM with moment clustering and LLM-driven
tag annotations. See: https://help.salesforce.com/s/articleView?id=ai.generative_ai_optimize_data_model.htm&type=5

### `ssot__AiAgentMoment__dlm` — session-level rollup

Carries agent identity.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentSessionId__c` | string (FK) | → Session.Id |
| `ssot__AiAgentApiName__c` | string | e.g. "MyAgent" |
| `ssot__AiAgentVersionApiName__c` | string | e.g. "v5" — observed `NOT_SET` in some live samples |
| `ssot__RequestSummaryText__c` | string | |
| `ssot__ResponseSummaryText__c` | string | |
| `ssot__StartTimestamp__c` | string | |
| `ssot__EndTimestamp__c` | string | |
| `ssot__InternalOrganizationId__c` | string | |

### `ssot__AiAgentMomentInteraction__dlm` — junction: moment ↔ interactions

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentMomentId__c` | string (FK) | → `Moment.Id` |
| `ssot__AiAgentInteractionId__c` | string (FK) | → `Interaction.Id` |
| `ssot__StartTimestamp__c` | datetime | |
| `ssot__InternalOrganizationId__c` | string | |

### `ssot__AiAgentTagDefinition__dlm` — tag schema / vocabulary

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__DeveloperName__c` | string | |
| `ssot__Name__c` | string | |
| `ssot__Description__c` | string | |
| `ssot__TagIdentifier__c` | string | |
| `ssot__DataType__c` | string | |
| `ssot__Status__c` | string | Live enum observed: `Available` (verified via live describe; all sampled rows used this value). Help docs say `Active/Inactive` but no `'Active'` rows exist on tested orgs — query by `'Available'` or omit filter. |
| `ssot__VersionNumber__c` | number | |
| `ssot__EngineType__c` | string | LLM engine that applies the tag |
| `ssot__SourceType__c` | string | |
| `ssot__SourceTagReferenceName__c` | string | |
| `ssot__InputScope__c` | string | |
| `ssot__CreatedDate__c` | datetime | |
| `ssot__InternalOrganizationId__c` | string | |

### `ssot__AiAgentTagDefinitionAssociation__dlm` — definition ↔ agent binding

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentTagDefinitionId__c` | string (FK) | → `TagDefinition.Id` |
| `ssot__AiAgentApiName__c` | string | Agent API name this definition binds to |
| `ssot__AiPromptTemplateId__c` | string | |
| `ssot__IsActive__c` | boolean | |
| `ssot__CreatedDate__c` | datetime | |
| `ssot__InternalOrganizationId__c` | string | |

### `ssot__AiAgentTag__dlm` — tag instance (a specific value under a definition)

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentTagDefinitionId__c` | string (FK) | → `TagDefinition.Id` |
| `ssot__Value__c` | string | Tag value text |
| `ssot__Description__c` | string | |
| `ssot__OrderNumber__c` | number | Display order |
| `ssot__IsActive__c` | boolean | |
| `ssot__IsFallback__c` | boolean | True when this tag is the fallback for the definition |
| `ssot__CreatedDate__c` | datetime | |
| `ssot__InternalOrganizationId__c` | string | |

### `ssot__AiAgentTagAssociation__dlm` — applied annotation

One row per tag applied to a target. Target is a moment, session, or interaction —
only one of those FKs is populated per row.

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | |
| `ssot__AiAgentTagId__c` | string (FK) | → `AiAgentTag.Id` — the tag value |
| `ssot__AiAgentTagDefinitionAssociationId__c` | string (FK) | → `TagDefinitionAssociation.Id` |
| `ssot__AiAgentMomentId__c` | string (FK) | → `Moment.Id` — populated when target is a moment |
| `ssot__AiAgentSessionId__c` | string (FK) | → `Session.Id` — populated when target is a session |
| `ssot__AiAgentInteractionId__c` | string (FK) | → `Interaction.Id` — populated when target is a turn |
| `ssot__IsPassed__c` | boolean | Pass/fail for evaluation-style tags |
| `ssot__AssociationReasonText__c` | string | LLM rationale for applying this tag |
| `ssot__CreatedDate__c` | datetime | |
| `ssot__InternalOrganizationId__c` | string | |

---

## Agent Platform Tracing DMO (1)

Provisioned only when **Agent Platform Tracing** is enabled (Setup → Einstein
Audit, Analytics, and Monitoring Setup → Agent Platform Tracing toggle; requires
Agentforce Session Tracing already on). Captures OpenTelemetry-style spans from
Apex, Flows, Prompt Builder, Invocable Actions, Planner, AI Gateway, LLM Gateway,
and DC Query Federator. Data collection runs every 5 minutes.

Joined to STDM via `ssot__TelemetryTrace__c = Interaction.ssot__TelemetryTraceId__c`.

### `ssot__TelemetryTraceSpan__dlm` — one row per span

| Field | Type | Notes |
|---|---|---|
| `ssot__Id__c` | string (PK) | Span id |
| `ssot__TelemetryTrace__c` | string (FK) | → `Interaction.ssot__TelemetryTraceId__c` |
| `ssot__TelemetryParentSpanId__c` | string | Parent span id (within the same trace); null on root |
| `ssot__OperationName__c` | string | e.g. `run.interaction`, `run.llmstep`, `run.action.<name>`, `run.invokeActions.<name>`, `run.hybridsearch.<index>` |
| `ssot__ServiceName__c` | string | e.g. `Atlas Reasoning Engine`, `InvocableAction`, `PromptTemplate`, `Einstein AI Gateway`, `Data Cloud` |
| `ssot__SpanKind__c` | string | OpenTelemetry span kind |
| `ssot__StatusCode__c` | string | Execution result |
| `ssot__StartDateTime__c` | datetime | Span start |
| `ssot__EndDateTime__c` | datetime | Span end |
| `ssot__DurationNumber__c` | number | Duration in nanoseconds |
| `ssot__TelemetrySpanAttributeText__c` | string | JSON key/value span attributes (e.g. `prompt_template.api.name`, `retriever.retrievername`) |
| `ssot__InternalOrganizationId__c` | string | |

---

## Known enum values (live-API verified)

| DMO | Field | Values |
|---|---|---|
| Session | `AiAgentChannelType__c` | `E & O`, `Builder`, `SCRT2 - EmbeddedMessaging`, `Voice`, `NGC` |
| Participant | `AiAgentType__c` | `DemoAgentType`, `AgentforceEmployeeAgent`, `AgentforceMyAgent` |
| Participant | `AiAgentSessionParticipantRole__c` | `USER`, `AGENT` |
| Interaction | `AiAgentInteractionType__c` | `TURN`, `SESSION_END` |
| Message | `AiAgentInteractionMessageType__c` | `Input`, `Output` |
| Step | `AiAgentInteractionStepType__c` | `LLM_STEP`, `ACTION_STEP`, `TOPIC_STEP`, `TRUST_GUARDRAILS_STEP`, `SESSION_END` (verified live) |
| ContentCategory | `detectorType__c` | `TOXICITY`, `PII`, `PROMPT_DEFENSE`, `InstructionAdherence`, `TaskResolution` |

---

## Tooling

DMO queries are executable; one CLI wrapper ships with the skill for
common operator needs:

| Script | Use case | Args |
|---|---|---|
| `scripts/discover_sessions.py` | Find sessions by time / agent / channel / outcome / grep; newest-first picker. | `--org`, optional `--since / --agent / --channel / --outcome / --grep / --tz / --limit` |
