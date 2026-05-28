-- Session discovery — find candidate sessions by time/agent/channel/outcome/grep.
-- Produces a short row-per-session shape for the picker rendered by
-- scripts/discover_sessions.py. NOT used by the trace pipeline — once the user
-- picks a UUID, the full pipeline runs fetch_dc.py against the 24-DMO waterfall.
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   SELECT_LIST  — either `s.ssot__Id__c, s.ssot__StartTimestamp__c, s.ssot__EndTimestamp__c,
--                          s.ssot__AiAgentChannelType__c, s.ssot__AiAgentSessionEndType__c`
--                 OR `DISTINCT <same columns>` when JOINs are present (DC SQL requires
--                 ORDER BY columns to appear in a DISTINCT projection).
--   JOINS        — zero or more JOIN clauses, newline-separated, or empty string:
--                   * `JOIN ssot__AiAgentSessionParticipant__dlm p ON s.ssot__Id__c = p.ssot__AiAgentSessionId__c`
--                     (required when filtering by --agent)
--                   * `JOIN ssot__AiAgentInteraction__dlm i ON s.ssot__Id__c = i.ssot__AiAgentSessionId__c
--                      JOIN ssot__AiAgentInteractionMessage__dlm m ON i.ssot__Id__c = m.ssot__AiAgentInteractionId__c`
--                     (required when filtering by --grep)
--   WHERE_CLAUSE — composed by the caller. No "WHERE" keyword. Always non-empty
--                 (at minimum the time-range predicate). All user-supplied string
--                 literals are single-quote-escaped by doubling quotes (O'Brien → O''Brien).
--   LIMIT        — integer, 1..N. Default in caller is 20.
--
-- Field reference:
--   time range → s.ssot__StartTimestamp__c >= '<startISO>' AND s.ssot__StartTimestamp__c < '<endISO>'
--   outcome    → s.ssot__AiAgentSessionEndType__c = '<USER_ENDED|ESCALATED|TRANSFERRED|TIMEOUT|NOT_SET>'
--   channel    → s.ssot__AiAgentChannelType__c = '<Builder|SCRT2 - EmbeddedMessaging|Voice|...>'
--   agent      → p.ssot__AiAgentApiName__c = '<AgentApiName>'  (requires participant JOIN)
--   grep       → m.ssot__ContentText__c LIKE '%<escaped-pattern>%'  (requires interaction+message JOIN)
--
-- All STDM timestamps are UTC.

SELECT {{SELECT_LIST}}
FROM ssot__AIAgentSession__dlm s
{{JOINS}}
WHERE {{WHERE_CLAUSE}}
ORDER BY s.ssot__StartTimestamp__c DESC
LIMIT {{LIMIT}};
