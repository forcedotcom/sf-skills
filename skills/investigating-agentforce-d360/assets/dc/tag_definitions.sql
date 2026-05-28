-- Tag definitions — the schema/vocabulary for tags applied to moments or sessions.
-- DMO: ssot__AiAgentTagDefinition__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Agent Optimization add-on DMO. Defines a tag type (name, data type,
-- input scope, engine type, source) that can then be applied via
-- AiAgentTag + AiAgentTagAssociation.

SELECT
    ssot__Id__c,
    ssot__DeveloperName__c,
    ssot__Name__c,
    ssot__Description__c,
    ssot__TagIdentifier__c,
    ssot__DataType__c,
    ssot__Status__c,
    ssot__VersionNumber__c,
    ssot__EngineType__c,
    ssot__SourceType__c,
    ssot__SourceTagReferenceName__c,
    ssot__InputScope__c,
    ssot__CreatedDate__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentTagDefinition__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All active tag definitions
--   Live orgs use 'Available' (not 'Active') — verified via live
--   describe. Group by ssot__Status__c to confirm per-org.
--   If 'Available' returns 0 rows, the waterfall retries unfiltered
--   (`ssot__Id__c IS NOT NULL`). Callers replicating this template
--   outside fetch_dc.py should apply the same fallback or expect
--   empty catalogs on orgs where Status uses a different enum.
-- WHERE    → ssot__Status__c = 'Available'
-- ORDER BY → ORDER BY ssot__Name__c

-- By developer name
-- WHERE    → ssot__DeveloperName__c = 'IntentCategory'

-- Definitions for a set of ids (resolves foreign keys from AiAgentTag)
-- WHERE    → ssot__Id__c IN ('<def_id1>','<def_id2>',...)
