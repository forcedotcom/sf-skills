-- Gateway responses — one row per LLM call response at the GenAI Gateway.
-- DMO: GenAIGatewayResponse__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- FK shape (small table; documented for reference only):
--   generationRequestId__c   = GatewayRequest.gatewayRequestId__c
--   generationResponseId__c  = Step.ssot__GenAiGatewayResponseId__c
--                            = Generation.generationResponseId__c
--
-- Forward join path from a session:
--   Session → GatewayRequest (sessionId__c LIKE)
--           → GatewayResponse (generationRequestId__c IN {gw_req_ids})
-- This is the canonical and only supported direction. 1:1 invariant holds
-- in live data — every GatewayRequest for a session produces one Response
-- row (modulo in-flight calls at fetch time).
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    generationResponseId__c,
    generationRequestId__c,
    parameters__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGatewayResponse__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Forward: Responses for the session's gateway requests (primary use case)
-- WHERE    → generationRequestId__c IN ('<req_id1>','<req_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Ad-hoc lookup by specific response ids (not used by the waterfall)
-- WHERE    → generationResponseId__c IN ('<resp_id1>','<resp_id2>',...)
