# STDM Schema Reference

Data Model Object (DMO) schemas, field mappings, query patterns, and data quality notes for the Session Trace Data Model.

---

## Data Hierarchy

```
AiAgentSession (1)
+-- AiAgentSessionParticipant (N)       -- agent planner IDs and user IDs linked to this session
+-- AiAgentInteraction (N)              -- one per conversational turn
|   +-- AiAgentInteractionMessage (N)   -- user and agent messages
|   +-- AiAgentInteractionStep (N)      -- internal steps (LLM, actions)
+-- AiAgentMoment (N)                   -- one per intent/moment in the session
|   +-- AiAgentMomentInteraction (N)    -- junction: links moments to interactions
|   +-- AiAgentTagAssociation (N)       -- junction: links moments to tags (quality scores)
|       +-- AiAgentTag (1)              -- score value (1-5)
|           +-- AiAgentTagDefinition (1)-- tag type definition
AiRetrieverQualityMetric (N)            -- RAG quality scores, linked via gateway request ID
```

**Quality score join chain:** `AiAgentTagAssociation` (FK `AiAgentMomentId` + FK `AiAgentTagId`) -> `AiAgentTag.Value` (1-5 integer). The `AssociationReasonText` field contains the LLM-generated reasoning for the score.

---

## Key Fields

### AiAgentSession (`ssot__AiAgentSession__dlm`)
- `ssot__Id__c` -- Session ID
- `ssot__StartTimestamp__c` / `ssot__EndTimestamp__c` -- Session timing -> `session.duration_ms`
- `ssot__AiAgentChannelType__c` -- Channel -> `session.channel`
- `ssot__AiAgentSessionEndType__c` -- How the session ended: `USER_ENDED`, `AGENT_ENDED`, or null -> `session.end_type`
- `ssot__VariableText__c` -- Final variable snapshot for the session -> `session.session_variables`

### AiAgentSessionParticipant (`ssot__AiAgentSessionParticipant__dlm`)
- `ssot__AiAgentSessionId__c` -- Session this participant belongs to
- `ssot__AiAgentApiName__c` -- API name of the agent (primary filter field -- no SOQL needed)
- `ssot__ParticipantId__c` -- GenAiPlannerDefinition ID (key prefix `16j`) for agents, `005...` for users. May be 15-char or 18-char.

### AiAgentInteraction (`ssot__AiAgentInteraction__dlm`)
- `ssot__TopicApiName__c` -- Topic/skill that handled this turn -> `turn.topic`
- `ssot__StartTimestamp__c` / `ssot__EndTimestamp__c` -- Turn timing -> `turn.duration_ms`
- `ssot__TelemetryTraceId__c` -- Distributed tracing ID -> `turn.telemetry_trace_id`

### AiAgentInteractionMessage (`ssot__AiAgentInteractionMessage__dlm`)
- `ssot__AiAgentInteractionMessageType__c` -- `Input` (user) or `Output` (agent) -> `message.message_type`
- `ssot__ContentText__c` -- Message text -> `message.text`

### AiAgentInteractionStep (`ssot__AiAgentInteractionStep__dlm`)
- `ssot__AiAgentInteractionStepType__c` -- `TOPIC_STEP`, `LLM_STEP`, `ACTION_STEP`, `SESSION_END`, `TRUST_GUARDRAILS_STEP` -> `step.step_type`
- `ssot__Name__c` -- Step or action name -> `step.name`
- `ssot__ErrorMessageText__c` -- Error text (null if none) -> `step.error`
- `ssot__InputValueText__c` / `ssot__OutputValueText__c` -- Input/output data -> `step.input` / `step.output`
- `ssot__PreStepVariableText__c` / `ssot__PostStepVariableText__c` -- Variable snapshots -> `step.pre_vars` / `step.post_vars`
- `ssot__GenerationId__c` -- Links to `GenAIGeneration__dlm` -> `step.generation_id` (non-null on LLM_STEP)
- `ssot__GenAiGatewayRequestId__c` -- Links to `GenAIGatewayRequest__dlm` -> `step.gateway_request_id` (non-null on LLM_STEP)

### Einstein Audit & Feedback DMOs (joined via `getLlmStepDetails()`)

**`GenAIGeneration__dlm`** -- LLM generation records:
- `generationId__c` -- Join key to `ssot__GenerationId__c` on the step DMO
- `responseText__c` -- The full LLM response text -> `LlmStepDetail.llm_response`

**`GenAIGatewayRequest__dlm`** -- Raw gateway requests sent to the LLM:
- `gatewayRequestId__c` -- Join key to `ssot__GenAiGatewayRequestId__c` on the step DMO
- `prompt__c` -- Full prompt text including system instructions -> `LlmStepDetail.prompt`

These two DMOs are only populated when Einstein Audit & Feedback is enabled in the org's Data Cloud setup.

### AiAgentMoment (`ssot__AiAgentMoment__dlm`)

Each moment represents a distinct user intent within a session. One session may have multiple moments.
- `ssot__Id__c` -- Moment ID
- `ssot__AiAgentSessionId__c` -- FK to AiAgentSession
- `ssot__StartTimestamp__c` / `ssot__EndTimestamp__c` -- Moment timing -> `MomentData.duration_ms`
- `ssot__RequestSummaryText__c` -- LLM-generated summary of user intent -> `MomentData.request_summary`
- `ssot__ResponseSummaryText__c` -- LLM-generated summary of agent response -> `MomentData.response_summary`
- `ssot__AiAgentApiName__c` -- Agent API name that handled this moment
- `ssot__AiAgentVersionApiName__c` -- Agent version API name

### AiAgentMomentInteraction (`ssot__AiAgentMomentInteraction__dlm`)

Links moments to the interactions (turns) they span. One moment may cover multiple turns.
- `ssot__Id__c` -- Junction record ID
- `ssot__AiAgentMomentId__c` -- FK to AiAgentMoment
- `ssot__AiAgentInteractionId__c` -- FK to AiAgentInteraction
- `ssot__StartTimestamp__c` -- When this moment-interaction link was created

### AiAgentTagAssociation (`ssot__AiAgentTagAssociation__dlm`)

The key junction table for quality scores. Links a moment to a tag (score 1-5) with LLM reasoning.
- `ssot__Id__c` -- Association ID
- `ssot__AiAgentMomentId__c` -- FK to AiAgentMoment
- `ssot__AiAgentTagId__c` -- FK to AiAgentTag (join to get the score value)
- `ssot__AiAgentSessionId__c` -- FK to AiAgentSession (denormalized for efficient filtering)
- `ssot__AiAgentInteractionId__c` -- FK to AiAgentInteraction
- `ssot__AiAgentTagDefinitionAssociationId__c` -- FK to TagDefinitionAssociation
- `ssot__AssociationReasonText__c` -- LLM-generated reasoning for the quality score -> `MomentData.quality_reasoning`
- `ssot__IsPassed__c` -- Whether the moment passed quality threshold

Quality score query: `TagAssociation JOIN Tag ON TagId -> Tag.Value` gives the 1-5 integer score per moment.

### AiAgentTag (`ssot__AiAgentTag__dlm`)

Contains the 5 quality score levels (1-5). Each tag has a numeric value.
- `ssot__Id__c` -- Tag ID
- `ssot__AiAgentTagDefinitionId__c` -- FK to tag definition
- `ssot__Value__c` -- Score value (e.g. "1", "2", "3", "4", "5") -> `MomentData.quality_score`
- `ssot__Description__c` -- Score description (null in current orgs)
- `ssot__IsActive__c` -- Whether this tag is active

### AiAgentTagDefinition (`ssot__AiAgentTagDefinition__dlm`)

Defines tag categories per agent. Each agent gets its own tag definition.
- `ssot__Id__c` -- Tag Definition ID
- `ssot__Name__c` -- Display name (e.g. "Optimization Request Category")
- `ssot__DeveloperName__c` -- API name (e.g. "AIE_Request_Category_MyServiceAgent")
- `ssot__DataType__c` -- Data type (e.g. "Text")
- `ssot__EngineType__c` -- Engine that generates the tags
- `ssot__Status__c` -- Definition status

### AiRetrieverQualityMetric (`ssot__AiRetrieverQualityMetric__dlm`)

Per-retrieval quality metrics for agents using knowledge retrieval. Links to sessions via gateway request ID.
- `ssot__Id__c` -- Metric ID
- `ssot__AiGatewayRequestId__c` -- FK to GenAIGatewayRequest
- `ssot__AiRetrieverRequestId__c` -- Retriever request ID
- `ssot__RetrieverApiName__c` -- API name of the retriever
- `ssot__UserUtteranceText__c` -- User utterance that triggered retrieval
- `ssot__AgentGeneratedResponseText__c` -- Agent response text
- `ssot__FaithfulnessRelevancyScoreNumber__c` -- Faithfulness score (0-1)
- `ssot__AnswerRelevancyScoreNumber__c` -- Answer relevance score (0-1)
- `ssot__ContextPrecisionScoreNumber__c` -- Context precision score (0-1)

Only populated when the agent uses knowledge retrieval actions. May have 0 rows if the agent has no RAG actions.

---

## TRUST_GUARDRAILS_STEP

A safety/compliance step that measures whether the agent's response followed its instructions:
- `step.name` is typically `InstructionAdherence`
- `step.output` is a Python-style dict string (not JSON). Actual format:
  ```
  {'name': 'InstructionAdherence', 'value': 'HIGH', 'explanation': 'This response adheres to the assigned instructions.'}
  ```
  Check for adherence by searching for `'value': 'LOW'` in the output string.
- `step.input` contains the raw `input_text` and `output_text` that were evaluated
- `step.error` may contain the literal string `"None"` (not a real error)
- Does **not** count toward `action_error_count`

---

## Data Quality Notes

**`NOT_SET` sentinel.** Data Cloud uses `"NOT_SET"` for null/absent values. `AgentforceOptimizeService` strips this sentinel -- any field returning `null` in the JSON should be treated as absent.

**`TRUST_GUARDRAILS_STEP` error field.** May have the Python string `"None"` in the error field. This is **not** a real error -- treat it as absent. `action_error_count` is only incremented for `ACTION_STEP` errors.

**Null `end_time` / `duration_ms`.** Sessions and turns may have `null` for `end_time` when no session-end event was recorded. This is common and does not indicate a problem.

**`LLM_STEP` input/output format.** The `input` and `output` fields on `LLM_STEP` contain raw Python dict strings (the internal LlamaIndex representation), not valid JSON. Do not attempt to `JSON.parse()` these values. Only `ACTION_STEP` input/output is structured JSON.

**Participant ID format inconsistency.** The `ssot__AiAgentSessionParticipant__dlm` DMO stores `ssot__ParticipantId__c` as either 15-char or 18-char Salesforce IDs, inconsistently. `AgentforceOptimizeService.resolvePlannerIds()` automatically handles both formats.

---

## Data Space Name

Always run Phase 0 first to discover the correct Data Space `name` for the org. Use `sf api request rest "/services/data/v63.0/ssot/data-spaces" -o <org>` (no `--json` flag -- unsupported on this beta command). Never assume `'default'` without checking -- it is only a fallback if the API call fails.

---

## Agent Name Resolution Reference

The only Salesforce metadata object that should be queried directly is `GenAiPlannerDefinition` -- used exclusively for agent name resolution in the Routing step.

| Object | Purpose | When to query |
|---|---|---|
| `GenAiPlannerDefinition` | The agent definition | Routing step only -- to resolve `MasterLabel`, `DeveloperName`, and `Id` |
| `DataKnowledgeSpace` | Knowledge base container | Phase 1.5b Step 5 only -- if knowledge gaps are detected |

**Do NOT query these objects directly** -- use the `.agent` file instead:
- `GenAiPluginDefinition` (topics) -- read from `.agent` file `topic:` blocks
- `GenAiPluginInstructionDef` (instructions) -- read from `.agent` file `reasoning: instructions:` blocks
- `GenAiFunction` (actions) -- read from `.agent` file `reasoning: actions:` blocks

The `.agent` file is the single source of truth. All fixes should be applied to it and deployed via the Phase 3 deployment chain.
