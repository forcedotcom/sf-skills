-- Per-request LLM call diagnostics — reusable for any WHERE filter.
-- DMO: GenAIGtwyRequestLLM__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Child of GenAIGatewayRequest__dlm. Captures LLM invocation
-- diagnostics (latency, status, endpoint, region, model). Populated
-- only when Trust Layer gateway LLM telemetry is on.
--
-- The DMO is provisioned by default but rows only appear when the
-- gateway LLM telemetry is emitted. Join column pattern mirrors
-- GenAIGtwyRequestMetadata__dlm (same parent__c shape).
--
-- No `ssot__` prefix — fields end in `__c` directly. Note that org id
-- is `salesforceOrgId__c` on this DMO, not the usual `orgId__c`.
--
-- Joined via `parent__c = GatewayRequest.gatewayRequestId__c`.

SELECT
    id__c,
    parent__c,
    endpoint__c,
    region__c,
    genAILLM__c,
    llmCallStatus__c,
    llmCallLatency__c,
    llmErrorTrace__c,
    metadata__c,
    feature__c,
    salesforceOrgId__c,
    timestamp__c,
    cloud__c
FROM GenAIGtwyRequestLLM__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All LLM diagnostic rows for a set of gateway request ids
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Only failed LLM calls
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>')
--            AND llmCallStatus__c != 'success'
