-- Planner steps — reusable for any WHERE filter.
-- DMO: ssot__AIAgentInteractionStep__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- One row per planner step within an interaction. Type enum (verified live):
-- LLM_STEP | ACTION_STEP | TOPIC_STEP | TRUST_GUARDRAILS_STEP | SESSION_END.
--
-- NOTE: InputValueText__c / OutputValueText__c are HTML-escaped JSON.
-- Callers should `html.unescape()` then `json.loads()` after fetch.
-- No direct session FK — scope forward via ssot__AiAgentInteractionId__c
-- (harvested from the session's Interaction rows).
--
-- ssot__GenAiGatewayRequestId__c / ssot__GenAiGatewayResponseId__c are
-- included in the SELECT for completeness but are NOT used as join keys
-- anywhere in the waterfall. Gateway audit rows are fetched forward from
-- Session → GatewayRequest (via sessionId__c) — see gateway_requests.sql.
-- ssot__ErrorMessageText__c uses the sentinel 'NOT_SET' (never NULL) to
-- mean "no error"; filter with `!= 'NOT_SET'`, not `IS NOT NULL`.

SELECT
    ssot__Id__c,
    ssot__AiAgentInteractionId__c,
    ssot__AiAgentInteractionStepType__c,
    ssot__Name__c,
    ssot__InputValueText__c,
    ssot__OutputValueText__c,
    ssot__PreStepVariableText__c,
    ssot__PostStepVariableText__c,
    ssot__GenerationId__c,
    ssot__ErrorMessageText__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__PrevStepId__c,
    ssot__InternalOrganizationId__c,
    ssot__TelemetryTraceSpanId__c,
    ssot__AttributeText__c,
    ssot__GenAiGatewayRequestId__c,
    ssot__GenAiGatewayResponseId__c
FROM ssot__AIAgentInteractionStep__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Steps for a specific interaction
-- WHERE    → ssot__AiAgentInteractionId__c = '<interaction_id>'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Steps for a session (via interaction id IN list)
-- WHERE    → ssot__AiAgentInteractionId__c IN ('<id1>','<id2>',...)

-- Only action steps (exclude LLM + topic planning)
-- WHERE    → ssot__AiAgentInteractionId__c IN ('<id1>','<id2>')
--            AND ssot__AiAgentInteractionStepType__c = 'ACTION_STEP'

-- Steps with errors (sentinel value; NOT null)
-- WHERE    → ssot__AiAgentInteractionId__c IN ('<id1>','<id2>')
--            AND ssot__ErrorMessageText__c != 'NOT_SET'
