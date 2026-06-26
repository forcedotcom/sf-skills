-- Additional per-request metadata — reusable for any WHERE filter.
-- DMO: GenAIGtwyRequestMetadata__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Child of GenAIGatewayRequest__dlm. Holds typed metadata rows for a
-- request — observed values include `metadataType__c = 'ToolCall'` and
-- `feature__c = 'plannerservice'`, so this is where planner/tool-call
-- metadata on a gateway request lives.
--
-- No `ssot__` prefix — fields end in `__c` directly.
--
-- Joined via `parent__c = GatewayRequest.gatewayRequestId__c`.
-- Join direction verified live: sampled row's parent__c matched exactly
-- one row in GenAIGatewayRequest__dlm. The table is usually heavily
-- populated on orgs with Trust Layer gateway logging enabled.

SELECT
    id__c,
    parent__c,
    metadataType__c,
    metadata__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGtwyRequestMetadata__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All metadata rows for a set of gateway request ids
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Only ToolCall-type metadata
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>')
--            AND metadataType__c = 'ToolCall'
