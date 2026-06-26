-- Sessions from Data Cloud — reusable for any WHERE filter.
-- DMO: ssot__AIAgentSession__dlm
--
-- Placeholders (substituted by scripts/dc.py._load):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- See EXAMPLE QUERIES below for common WHERE patterns.
--
-- This query extracts session-level data including:
--   - Session ID and timestamps
--   - Channel type (how user connected)
--   - How the session ended (Completed, Abandoned, Escalated, etc.)
--   - Related messaging session (if applicable)
--
-- NOTE: Agent name is NOT on Session table. Join with Moment to get agent info.

SELECT
    ssot__Id__c,
    ssot__AiAgentChannelType__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__AiAgentSessionEndType__c,
    ssot__RelatedMessagingSessionId__c,
    ssot__RelatedVoiceCallId__c,
    ssot__InternalOrganizationId__c,
    ssot__SessionOwnerId__c,
    ssot__SessionOwnerObject__c,
    ssot__IndividualId__c,
    ssot__PreviousSessionId__c,
    ssot__VariableText__c
FROM ssot__AIAgentSession__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE QUERIES (pass to sessions_sql via where_clause= / order_by=)
-- ============================================================================

-- One session by id (this skill's primary use case)
-- WHERE    → ssot__Id__c = '<session_uuid>'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Last 7 days of sessions
-- WHERE    → ssot__StartTimestamp__c >= '<iso_cutoff_7d_ago>'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Date range
-- WHERE    → ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
--            AND ssot__StartTimestamp__c < '2026-02-01T00:00:00.000Z'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Failed / escalated sessions only
-- WHERE    → ssot__AiAgentSessionEndType__c IN ('Escalated', 'Abandoned', 'Failed')
--            AND ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Sessions by channel (e.g. embedded messaging only)
-- WHERE    → ssot__AiAgentChannelType__c = 'SCRT2 - EmbeddedMessaging'
--            AND ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
-- ORDER BY → ORDER BY ssot__StartTimestamp__c

-- Session count by end type (aggregate — SELECT list changes too; separate template)
-- SELECT
--     ssot__AiAgentSessionEndType__c,
--     COUNT(*) as session_count
-- FROM ssot__AIAgentSession__dlm
-- WHERE ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z'
-- GROUP BY ssot__AiAgentSessionEndType__c;

-- Sessions by agent (requires Moment join — separate query shape, not this template)
-- SELECT DISTINCT s.*
-- FROM ssot__AIAgentSession__dlm s
-- JOIN ssot__AiAgentMoment__dlm m
--     ON m.ssot__AiAgentSessionId__c = s.ssot__Id__c
-- WHERE m.ssot__AiAgentApiName__c = 'MyAgent'
--   AND s.ssot__StartTimestamp__c >= '2026-01-01T00:00:00.000Z';
