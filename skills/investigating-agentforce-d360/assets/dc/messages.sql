-- User/agent messages — reusable for any WHERE filter.
-- DMO: ssot__AiAgentInteractionMessage__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- One row per user/agent message. Type enum: Input | Output.
--
-- This DMO has a direct session FK (`ssot__AiAgentSessionId__c`) — verified
-- live against Data Cloud v66.0. Scope by session directly; no need to join through
-- interactions. It also has a participant FK and a parent-message FK for
-- threading, plus `MessageStartTimestamp__c` / `MessageEndTimestamp__c` for
-- voice-modality durations (richer than the single `MessageSentTimestamp__c`).

SELECT
    ssot__Id__c,
    ssot__AiAgentSessionId__c,
    ssot__AiAgentInteractionId__c,
    ssot__AiAgentSessionParticipantId__c,
    ssot__ParentMessageId__c,
    ssot__ContentText__c,
    ssot__AiAgentInteractionMessageType__c,
    ssot__AiAgentInteractionMsgContentType__c,
    Modality__c,
    ssot__MessageSentTimestamp__c,
    MessageStartTimestamp__c,
    MessageEndTimestamp__c,
    ssot__InternalOrganizationId__c
FROM ssot__AiAgentInteractionMessage__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Messages for one session (direct FK — preferred)
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
-- ORDER BY → ORDER BY ssot__MessageSentTimestamp__c

-- Messages for a specific interaction
-- WHERE    → ssot__AiAgentInteractionId__c = '<interaction_id>'
-- ORDER BY → ORDER BY ssot__MessageSentTimestamp__c

-- Only user inputs for a session
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
--            AND ssot__AiAgentInteractionMessageType__c = 'Input'

-- Voice-modality messages (use start/end timestamps for duration)
-- WHERE    → ssot__AiAgentSessionId__c = '<session_id>'
--            AND Modality__c = 'Voice'
