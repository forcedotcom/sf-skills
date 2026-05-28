-- Tag definition ↔ agent association — which tags are available for an agent.
-- DMO: ssot__AiAgentTagDefinitionAssociation__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Agent Optimization add-on DMO. Binds a TagDefinition to a specific agent
-- (by API name) and prompt template. This is what `AiAgentTagAssociation`
-- actually points at via `ssot__AiAgentTagDefinitionAssociationId__c`.

SELECT
    ssot__Id__c,
    ssot__AiAgentTagDefinitionId__c,
    ssot__AiAgentApiName__c,
    ssot__AiPromptTemplateId__c,
    ssot__IsActive__c,
    ssot__CreatedDate__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentTagDefinitionAssociation__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Active associations for a specific agent
-- WHERE    → ssot__AiAgentApiName__c = '<agent_api_name>'
--            AND ssot__IsActive__c = true

-- Associations pointing at a set of tag definitions
-- WHERE    → ssot__AiAgentTagDefinitionId__c IN ('<def_id1>','<def_id2>',...)

-- Resolve by association id (from AiAgentTagAssociation)
-- WHERE    → ssot__Id__c IN ('<assoc_id1>','<assoc_id2>',...)
