# STDM Query Reference

Detailed procedures for querying Session Trace Data Model (STDM) via the `AgentforceOptimizeService` Apex helper class.

---

## Deploy Helper Class (Once Per Org)

`AgentforceOptimizeService` is a bundled Apex class that queries STDM DMOs and returns clean JSON. Deploy it once; subsequent runs reuse the deployed class.

Methods:
- `findSessions(dataSpaceName, startIso, endIso, maxRows, agentName)` -> `List<SessionSummary>`
- `getConversationDetails(dataSpaceName, sessionId)` -> `ConversationData`
- `getMultipleConversationDetails(dataSpaceName, sessionIds)` -> `List<ConversationData>`
- `getLlmStepDetails(dataSpaceName, stepIds)` -> `List<LlmStepDetail>`
- `getMomentInsights(dataSpaceName, sessionIds)` -> `List<SessionInsights>` (moments, turn counts, retriever metrics)
- `getAggregatedMetrics(dataSpaceName, startIso, endIso, maxRows, agentName)` -> `AggregatedMetrics` (session rates, top intents, RAG quality)
- `runObservabilityQuery(List<ObservabilityInput>)` -> `List<ObservabilityOutput>` (@InvocableMethod -- RAG observability queries for Flow/Agentforce actions)

**Step 1 -- copy the class into the project:**

```bash
# Ensure the classes directory exists
mkdir -p <project-root>/force-app/main/default/classes

# Copy from the installed skill location
cp skills/observing-agentforce/apex/AgentforceOptimizeService.cls \
   <project-root>/force-app/main/default/classes/
cp skills/observing-agentforce/apex/AgentforceOptimizeService.cls-meta.xml \
   <project-root>/force-app/main/default/classes/
```

If the skill is installed globally via the installer, use the installed path:
```bash
cp ~/.claude/skills/observing-agentforce/apex/AgentforceOptimizeService.cls \
   <project-root>/force-app/main/default/classes/
cp ~/.claude/skills/observing-agentforce/apex/AgentforceOptimizeService.cls-meta.xml \
   <project-root>/force-app/main/default/classes/
```

**Step 2 -- ensure `sfdx-project.json` exists** (if absent, create a minimal one):

```json
{
  "packageDirectories": [{ "path": "force-app", "default": true }],
  "sourceApiVersion": "63.0"
}
```

**Step 3 -- deploy to the org:**

```bash
sf project deploy start --json \
  --metadata ApexClass:AgentforceOptimizeService \
  -o <org>
```

Confirm the deploy succeeds before proceeding. If it fails with a compile error, check that the org has Data Cloud enabled (the `ConnectApi.CdpQuery` namespace requires Data Cloud).

**Skip this step if `AgentforceOptimizeService` is already deployed** -- check with:
```bash
sf data query --json \
  --query "SELECT Id, Name FROM ApexClass WHERE Name = 'AgentforceOptimizeService'" \
  -o <org>
```

---

## Find Sessions

If the user provided session IDs, skip to conversation details. Otherwise, write `/tmp/stdm_find.apex` and run it (substitute actual ISO 8601 UTC timestamps, DATA_SPACE, and AGENT_API_NAME):

```apex
String result = AgentforceOptimizeService.findSessions(
    'DATA_SPACE',
    'START_ISO',
    'END_ISO',
    20,
    'AGENT_MASTER_LABEL'
);
System.debug('STDM_RESULT:' + result);
```

```bash
sf apex run --json --file /tmp/stdm_find.apex -o <org>
```

Parse: search for `DEBUG|STDM_RESULT:` (not `STDM_RESULT:` -- the first occurrence of that string is in the source echo, not the debug output) and extract the JSON that follows on that line:

```bash
python3 -c "
import json, sys
logs = json.load(sys.stdin)['result']['logs']
idx = logs.find('DEBUG|STDM_RESULT:')
print(logs[idx + len('DEBUG|STDM_RESULT:'):].split('\n')[0].strip())
" < /tmp/apex_result.json
```

The result is a JSON array of `SessionSummary` objects:
```json
[
  {
    "session_id": "...", "start_time": "...", "end_time": "...",
    "channel": "...", "duration_ms": 12345,
    "end_type": "USER_ENDED"
  }
]
```

- `end_time` and `duration_ms` may be `null` when the session has no recorded end event -- this is a normal STDM data quality gap, not an error.
- `end_type` values: `USER_ENDED`, `AGENT_ENDED`, or `null` (in-progress or not recorded). A `null` `end_type` may indicate an abandoned session.

**Session quality filter:** `findSessions` automatically filters to sessions with actual conversation turns by querying `AiAgentInteraction` first. Sessions from `sf agent preview`, `sf agent test`, and Agent Builder that created `AiAgentSession` records but no `AiAgentInteraction` (TURN) records are excluded. If `findSessions` returns an empty list, there are no sessions with actionable data — go directly to Phase 1-ALT (local traces).

**How agent filtering works** -- `findSessions` tries two strategies in order:

1. **Direct** (preferred): `ssot__AiAgentApiName__c = agentApiName` on `ssot__AiAgentSessionParticipant__dlm` -- no SOQL needed, uses a dedicated DMO field. Resolves in a single Data Cloud query.
2. **Planner fallback**: If strategy 1 returns no rows, SOQL: `SELECT Id FROM GenAiPlannerDefinition WHERE MasterLabel = :agentApiName` -> `ssot__ParticipantId__c IN (...)`. Both 15-char and 18-char ID formats are included (the DMO stores them inconsistently). If both strategies return empty, the query falls back to all sessions in the date range.

**If the debug log shows `Agent not found: <name>`**, no `GenAiPlannerDefinition` matched -- verify the agent name with:
```bash
sf data query --json --query "SELECT Id, MasterLabel, DeveloperName FROM GenAiPlannerDefinition" -o <org>
```
Use the exact `MasterLabel` value (not `DeveloperName`). `MasterLabel` matches the agent's display name; `DeveloperName` has a version suffix (e.g. `TeslaSupportAgent_v1`).

**If the debug log shows a warning about no sessions for the agent**, both strategies returned empty -- the agent may have no sessions in this date range, or Data Cloud ingestion may be delayed. The query falls back to all sessions in the date range.

---

## Get Conversation Details

For up to 5 sessions (most recent first), write `/tmp/stdm_details.apex` and run it (substitute session IDs and DATA_SPACE):

```apex
String result = AgentforceOptimizeService.getMultipleConversationDetails(
    'DATA_SPACE',
    new List<String>{ 'SESSION_ID_1', 'SESSION_ID_2' }
);
System.debug('STDM_RESULT:' + result);
```

```bash
sf apex run --json --file /tmp/stdm_details.apex -o <org>
```

Parse using the same `DEBUG|STDM_RESULT:` pattern. Each element is a `ConversationData` object:

```json
{
  "session_id": "...",
  "start_time": "...", "end_time": "...", "channel": "...",
  "duration_ms": 45000,
  "end_type": "USER_ENDED",
  "session_variables": "{...}",
  "turn_count": 3,
  "action_error_count": 1,
  "turns": [
    {
      "interaction_id": "...",
      "topic": "CheckOrderStatus",
      "start_time": "...", "end_time": "...", "duration_ms": 8000,
      "telemetry_trace_id": "...",
      "messages": [
        { "message_type": "Input",  "text": "Where is my order?", "sent_at": "..." },
        { "message_type": "Output", "text": "I found your order...", "sent_at": "..." }
      ],
      "steps": [
        { "step_type": "TOPIC_STEP",  "name": "CheckOrderStatus" },
        { "step_type": "LLM_STEP",    "name": "...", "duration_ms": 3200,
          "generation_id": "abc123", "gateway_request_id": "def456" },
        { "step_type": "ACTION_STEP", "name": "GetOrderDetails",
          "input": "{...}", "output": "{...}", "error": null,
          "pre_vars": "{...}", "post_vars": "{...}", "duration_ms": 1500 }
      ]
    }
  ]
}
```

Key fields:
- `end_type` -- how the session ended (`USER_ENDED`, `AGENT_ENDED`, or null)
- `session_variables` -- final variable snapshot for the session (null when absent)
- `telemetry_trace_id` -- distributed tracing ID for this turn (null when absent)
- `generation_id` / `gateway_request_id` on `LLM_STEP` -- pass these step IDs to `getLlmStepDetails()` to retrieve the actual LLM prompt and response (useful for diagnosing LOW instruction adherence)

Treat any `null` field as absent/unknown. The `"NOT_SET"` sentinel is stripped by the service class before returning.

---

## Get LLM Prompt/Response (Optional, for LOW Adherence)

When a session shows `TRUST_GUARDRAILS_STEP` with `'value': 'LOW'`, use `getLlmStepDetails()` to retrieve the actual LLM prompt and response for the associated `LLM_STEP` records. Pass the `step_id` values from steps where `step_type == "LLM_STEP"` and `generation_id != null`.

```apex
String result = AgentforceOptimizeService.getLlmStepDetails(
    'DATA_SPACE',
    new List<String>{ 'STEP_ID_1', 'STEP_ID_2' }
);
System.debug('STDM_RESULT:' + result);
```

```bash
sf apex run --json --file /tmp/stdm_llm.apex -o <org>
```

Returns a JSON array of `LlmStepDetail` objects:
```json
[
  {
    "step_id": "...",
    "interaction_id": "...",
    "step_name": "...",
    "prompt": "System: You are a Tesla support agent...\nUser: I want to schedule a test drive",
    "llm_response": "I'd be happy to help you schedule a test drive...",
    "generation_id": "...",
    "gateway_request_id": "..."
  }
]
```

- `prompt` -- full prompt from `GenAIGatewayRequest__dlm.prompt__c` (null if Einstein Audit DMO not enabled)
- `llm_response` -- model response from `GenAIGeneration__dlm.responseText__c` (null if not available)

Use these to confirm whether the agent's instructions were included in the prompt and whether the response deviated from them.

---

## Get Aggregated Metrics (Recommended First Step)

Before drilling into individual sessions, get a high-level health dashboard with `getAggregatedMetrics()`. This gives session rates, top intents, and RAG quality averages across the date range.

```apex
String result = AgentforceOptimizeService.getAggregatedMetrics(
    'DATA_SPACE',
    'START_ISO',
    'END_ISO',
    50,
    'AGENT_MASTER_LABEL'
);
System.debug('STDM_RESULT:' + result);
```

Returns an `AggregatedMetrics` object:
```json
{
  "total_sessions": 36,
  "total_moments": 32,
  "total_turns": 101,
  "avg_quality_score": 4.34,
  "avg_session_duration_sec": 45.2,
  "end_type_counts": { "USER_ENDED": 5, "AGENT_ENDED": 10, "UNKNOWN": 21 },
  "quality_distribution": { "5": 20, "4": 6, "3": 4, "2": 1, "1": 1 },
  "abandonment_rate": 0.14,
  "deflection_rate": 0.28,
  "escalation_rate": 0.0,
  "top_intents": { "I want help finding homes in San Jose.": 3, "Check order status": 2 },
  "avg_faithfulness": 0.85,
  "avg_answer_relevance": 0.72,
  "avg_context_precision": 0.91,
  "unavailable_dmos": []
}
```

Key signals:
- `avg_quality_score` < 4.0 -> agent has Medium/Low quality responses, investigate low-scoring moments. Score labels: 5=High, 3-4=Medium, 2=Low, 1=Very Low
- `quality_distribution` skewed toward 1-3 -> systemic agent quality issue; focus on moments with score <= 3
- High `abandonment_rate` (> 0.3) -> users giving up, check for dead-ends or missing actions
- Low `avg_faithfulness` / `avg_answer_relevance` -> RAG retrieval issues, check knowledge base content
- `top_intents` shows what users ask about most -- verify the agent has topics/actions for each
- `unavailable_dmos` lists any DMOs that couldn't be queried (graceful degradation)

---

## Get Moment Insights (Per-Session Detail)

For deeper analysis of specific sessions, use `getMomentInsights()` to get intent summaries, moment durations, and retriever quality metrics per session.

```apex
String result = AgentforceOptimizeService.getMomentInsights(
    'DATA_SPACE',
    new List<String>{ 'SESSION_ID_1', 'SESSION_ID_2' }
);
System.debug('STDM_RESULT:' + result);
```

Returns a JSON array of `SessionInsights` objects:
```json
[
  {
    "session_id": "...",
    "start_time": "...", "end_time": "...", "end_type": null,
    "duration_ms": null, "turn_count": 3, "moment_count": 2,
    "avg_quality_score": 4.5,
    "action_error_count": 0,
    "moments": [
      {
        "moment_id": "...",
        "session_id": "...",
        "start_time": "...", "end_time": "...", "duration_ms": 10000,
        "request_summary": "I want help finding homes in San Jose.",
        "response_summary": "The agent provided details on three homes...",
        "agent_api_name": "MyServiceAgent",
        "agent_version": null,
        "quality_score": 5,
        "quality_reasoning": "The agent provided a detailed and helpful response..."
      }
    ],
    "retriever_metrics": [],
    "debug_message": null
  }
]
```

Key fields:
- `quality_score` (1-5) -- per-moment quality score from `AiAgentTagAssociation -> AiAgentTag.Value`. Maps to UI labels: 5=High, 3-4=Medium, 2=Low, 1=Very Low
- `quality_reasoning` -- LLM-generated explanation for the score (from `AssociationReasonText`)
- `avg_quality_score` -- session-level average across all scored moments
- `request_summary` / `response_summary` -- LLM-generated intent and response summaries per moment
- `moment_count` vs `turn_count` -- if `turn_count` >> `moment_count`, the agent needed many turns per intent (inefficient)
- `retriever_metrics` -- RAG quality scores per retrieval (empty if agent doesn't use knowledge retrieval)
- `debug_message` -- non-null if a DMO was unavailable (e.g. "AiAgentMoment DMO not available in this org")

---

## Run Observability Queries (RAG Deep-Dive)

For targeted RAG/retriever quality analysis, use the `@InvocableMethod` entry point `runObservabilityQuery()`. This can be called from anonymous Apex, Flows, or Agentforce actions. It queries Data Lake objects (`*__dll`) directly without a Data Space parameter.

**Query types:**

| `queryType` | What it returns |
|---|---|
| `KnowledgeGap` | Avg context precision + answer relevancy by subagent/agent (lowest first) |
| `Hallucination` | Subagents with avg faithfulness < 0.8 |
| `RetrievalQuality` | Avg context precision by retriever/subagent/agent |
| `AnswerRelevancy` | Subagents with avg answer relevancy < 0.7 |
| `Leaderboard` | Combined precision, relevancy, and faithfulness by subagent/agent |

**From anonymous Apex:**

```apex
AgentforceOptimizeService.ObservabilityInput inp = new AgentforceOptimizeService.ObservabilityInput();
inp.queryType = 'KnowledgeGap';
inp.agentApiName = 'AGENT_API_NAME';  // optional
inp.topicApiName = 'TOPIC_API_NAME';  // optional
inp.lookbackDays = 90;                // optional, default 90

List<AgentforceOptimizeService.ObservabilityOutput> results =
    AgentforceOptimizeService.runObservabilityQuery(
        new List<AgentforceOptimizeService.ObservabilityInput>{ inp }
    );
System.debug('STDM_RESULT:' + results[0].summaryText);
System.debug('STDM_RESULT:' + results[0].resultJson);
```

```bash
sf apex run --json --file /tmp/observability_query.apex -o <org>
```

**When to use observability queries vs `getAggregatedMetrics()`:**

- Use `getAggregatedMetrics()` for a broad health dashboard (session rates, top intents, overall RAG averages)
- Use `runObservabilityQuery()` for targeted RAG deep-dives when knowledge gaps or hallucination issues are detected -- it provides per-subagent and per-retriever breakdowns

---

## Reconstruct Conversations

For each session, render the turn-by-turn timeline from the `ConversationData` JSON:

```
Session <session_id>  [<channel>]  <duration_ms>ms total  <turn_count> turns
------------------------------------------------------------
Turn 1  [Subagent: <subagent>]  <duration_ms>ms
  User:  <messages[type=Input].text>
  Agent: <messages[type=Output].text>
  Steps:
    TOPIC_STEP:  <name>
    LLM_STEP:    <name>  (<duration_ms>ms)
    ACTION_STEP: <name>  in: <input>  out: <output>  [ERROR: <error>]
```
