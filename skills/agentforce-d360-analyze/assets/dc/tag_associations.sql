-- Tag ↔ target association — which tag was applied to a moment/session/interaction.
-- DMO: ssot__AiAgentTagAssociation__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Agent Optimization add-on DMO. THE applied-tag row — one per annotation.
-- Points at a tag value (`ssot__AiAgentTagId__c`) + a target
-- (moment | session | interaction) + the tag-definition-association that
-- authorized it. `ssot__AssociationReasonText__c` carries the LLM's
-- rationale for why it assigned this tag.

SELECT
    ssot__Id__c,
    ssot__AiAgentTagId__c,
    ssot__AiAgentTagDefinitionAssociationId__c,
    ssot__AiAgentMomentId__c,
    ssot__AiAgentSessionId__c,
    ssot__AiAgentInteractionId__c,
    ssot__IsPassed__c,
    ssot__AssociationReasonText__c,
    ssot__CreatedDate__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentTagAssociation__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All tag associations for one session
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
-- ORDER BY → ORDER BY ssot__CreatedDate__c

-- Tags applied to a set of moments
-- WHERE    → ssot__AiAgentMomentId__c IN ('<mom_id1>','<mom_id2>')

-- Only passed evaluations (quality pass/fail)
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
--            AND ssot__IsPassed__c = true

-- Associations by tag id (reverse lookup)
-- WHERE    → ssot__AiAgentTagId__c IN ('<tag_id1>','<tag_id2>')
