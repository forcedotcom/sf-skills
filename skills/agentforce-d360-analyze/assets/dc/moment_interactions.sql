-- Moment ↔ Interaction junction — which turns belong to a moment.
-- DMO: ssot__AiAgentMomentInteraction__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Agent Optimization add-on DMO. Provisioned only when Agent Optimization
-- is enabled. Junction between AiAgentMoment and AIAgentInteraction.
-- Observed live: one Moment per Interaction (N:1 direction). The junction
-- schema supports true many-to-many; the assembler emits Moment.interaction_ids[]
-- back-refs to preserve the schema-correct shape even when live data is 1:N.

SELECT
    ssot__Id__c,
    ssot__AiAgentMomentId__c,
    ssot__AiAgentInteractionId__c,
    ssot__StartTimestamp__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentMomentInteraction__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Junction rows for a set of moments
-- WHERE    → ssot__AiAgentMomentId__c IN ('<mom_id1>','<mom_id2>',...)
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Junction rows for a set of interactions (reverse lookup)
-- WHERE    → ssot__AiAgentInteractionId__c IN ('<int_id1>','<int_id2>')
