-- Session-level agent moment rollup — reusable for any WHERE filter.
-- DMO: ssot__AiAgentMoment__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- When present, carries agent identity + a request/response summary for
-- the session. This is the only STDM DMO outside Participant that exposes
-- AiAgentApiName__c. Moments are absent on orgs without Agent Optimization
-- enabled; the assembler falls back to Participant (AGENT role) for agent
-- identity in that case.

SELECT
    ssot__Id__c,
    ssot__AiAgentSessionId__c,
    ssot__AiAgentApiName__c,
    ssot__AiAgentVersionApiName__c,
    ssot__RequestSummaryText__c,
    ssot__ResponseSummaryText__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentMoment__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Moment(s) for one session — usually 0 or 1 row
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'

-- All sessions handled by a specific agent API name in a date range
-- WHERE    → ssot__AiAgentApiName__c = 'MyAgent'
--            AND ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c
