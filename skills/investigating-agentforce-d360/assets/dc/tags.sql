-- Tag instances — a specific tag value under a tag definition.
-- DMO: ssot__AiAgentTag__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Agent Optimization add-on DMO. A `AiAgentTag` belongs to a definition
-- (e.g. definition "IntentCategory" with tag value "Refund Request").
-- The tag is applied to a moment/session/interaction via AiAgentTagAssociation.

SELECT
    ssot__Id__c,
    ssot__AiAgentTagDefinitionId__c,
    ssot__Value__c,
    ssot__Description__c,
    ssot__OrderNumber__c,
    ssot__IsActive__c,
    ssot__IsFallback__c,
    ssot__CreatedDate__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentTag__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Tags for a specific definition (all allowed values)
-- WHERE    → ssot__AiAgentTagDefinitionId__c = '<def_id>'
--            AND ssot__IsActive__c = true
-- ORDER BY → ORDER BY ssot__OrderNumber__c

-- Resolve tags by id (from AiAgentTagAssociation.ssot__AiAgentTagId__c)
-- WHERE    → ssot__Id__c IN ('<tag_id1>','<tag_id2>',...)
