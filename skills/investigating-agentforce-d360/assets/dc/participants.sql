-- Session participants from Data Cloud — reusable for any WHERE filter.
-- DMO: ssot__AiAgentSessionParticipant__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- One row per participant per session. Roles: USER, AGENT.
-- AiAgentApiName__c is populated on AGENT rows only.
--
-- Casing gotcha: DMO name uses `AiAgent` (lowercase i), unlike the Session
-- DMO which uses `AIAgent` (uppercase AI). See references/dc_dmo_fields.md.

SELECT
    ssot__Id__c,
    ssot__AiAgentSessionId__c,
    ssot__ParticipantId__c,
    ssot__AiAgentApiName__c,
    ssot__AiAgentType__c,
    ssot__AiAgentTemplateApiName__c,
    ssot__AiAgentVersionApiName__c,
    ssot__AiAgentSessionParticipantRole__c,
    ssot__ParticipantObject__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__IndividualId__c,
    ssot__InternalOrganizationId__c,
    ssot__ParticipantAttributeText__c
FROM ssot__AiAgentSessionParticipant__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Participants for one session
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Only AGENT rows (carry agent identity)
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
--            AND ssot__AiAgentSessionParticipantRole__c = 'AGENT'

-- All sessions handled by a specific agent
-- WHERE    → ssot__AiAgentApiName__c = 'MyAgent'
--            AND ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
