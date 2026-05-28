-- Session interactions (turns + session-end event) — reusable for any WHERE.
-- DMO: ssot__AIAgentInteraction__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- One row per turn plus one SESSION_END row per session.
-- Type enum: TURN | SESSION_END.
--
-- Casing gotcha: DMO name uses `AIAgent` (uppercase AI). Field names use
-- `AiAgent` (lowercase i). See references/dc_dmo_fields.md.
--
-- trace_id gotcha: `ssot__TelemetryTraceId__c` is often empty on real orgs
-- (verified live). The runtime trace_id lives inside
-- `ssot__AttributeText__c` as HTML-escaped JSON, key `internalTraceId`.
-- Consumers must `html.unescape()` + regex-extract. Used to join with
-- GenAIGeneration (generationId via Step) and TelemetryTraceSpan.

SELECT
    ssot__Id__c,
    ssot__AiAgentSessionId__c,
    ssot__AiAgentInteractionType__c,
    ssot__TopicApiName__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__PrevInteractionId__c,
    ssot__SessionOwnerId__c,
    ssot__IndividualId__c,
    ssot__InternalOrganizationId__c,
    ssot__TelemetryTraceId__c,
    ssot__TelemetryTraceSpanId__c,
    ssot__AttributeText__c
FROM ssot__AIAgentInteraction__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All interactions for one session
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- TURN rows only (exclude SESSION_END)
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
--            AND ssot__AiAgentInteractionType__c = 'TURN'

-- Interactions handled by a specific topic across sessions
-- WHERE    → ssot__TopicApiName__c = 'Order_Management'
--            AND ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
