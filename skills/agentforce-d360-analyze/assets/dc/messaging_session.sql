-- MessagingSession id → AI-agent session id lookup.
-- DMO: ssot__AIAgentSession__dlm
--
-- Given a Salesforce MessagingSession id (0Mw... prefix, 15 or 18 chars),
-- find every ssot__AIAgentSession__dlm row with matching
-- RelatedMessagingSessionId. Used by scripts/resolve_session.py to map a
-- messaging id to the canonical AI-agent session UUID that every other
-- script keys on.
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   MSG_ID  — the MessagingSession id (pre-validated by the caller:
--             is_messaging_id() enforces the `0Mw` key prefix plus an
--             exact 15 or 18 char length before this template is loaded.
--             A raw-UUID or free-text id can never reach this template.)
--
-- Returned rows:
--   * zero rows  → caller raises SystemExit ("no messaging session found")
--   * one row    → caller returns ssot__Id__c as the UUID
--   * many rows  → caller prints every candidate with timestamps + end_type
--                  + channel and exits non-zero so the user can pick one
--                  and re-invoke with the specific UUID.
--
-- The `RelatedMessagingSessionId__c != 'NOT_SET'` clause is defensive —
-- a real msg_id cannot equal the literal 'NOT_SET', but the guard lets
-- the template be copy-pasted for other filters that might otherwise
-- accidentally match the sentinel.

SELECT
    ssot__Id__c,
    ssot__StartTimestamp__c,
    ssot__EndTimestamp__c,
    ssot__AiAgentSessionEndType__c,
    ssot__AiAgentChannelType__c
FROM ssot__AIAgentSession__dlm
WHERE ssot__RelatedMessagingSessionId__c = '{{MSG_ID}}'
  AND ssot__RelatedMessagingSessionId__c != 'NOT_SET'
ORDER BY ssot__StartTimestamp__c DESC;
