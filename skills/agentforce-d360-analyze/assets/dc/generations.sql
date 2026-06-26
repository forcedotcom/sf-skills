-- GenAI gateway generations — reusable for any WHERE filter.
-- DMO: GenAIGeneration__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- One row per LLM call at the gateway (Trust Layer).
--
-- NOTE: No `ssot__` prefix on this DMO — fields end in `__c` directly.
--
-- Forward join to a session: this DMO has NO session/trace/turn column.
-- The only supported path is Step.ssot__GenerationId__c → generationId__c,
-- driven forward from the session:
--   Session → Interaction (ssot__AiAgentSessionId__c)
--           → Step        (ssot__AiAgentInteractionId__c)
--           → Generation  (step.ssot__GenerationId__c IN {generationId__c})
-- Pull step rows for the session's interactions first, collect non-empty
-- `ssot__GenerationId__c` values (LLM_STEP rows populate it; others are
-- NOT_SET), then query here with `generationId__c IN (...)`.

SELECT
    generationId__c,
    generationResponseId__c,
    responseText__c,
    maskedResponseText__c,
    responseParameters__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGeneration__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Generations for a set of step generation ids
-- WHERE    → generationId__c IN ('<gen_id1>','<gen_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Generations in a time window for one org
-- WHERE    → orgId__c = '<org_id_18>'
--            AND timestamp__c >= '<iso_window_start>'
--            AND timestamp__c <  '<iso_window_end>'
-- ORDER BY → ORDER BY timestamp__c

-- Filter by feature (e.g. Copilot vs guardrails)
-- WHERE    → feature__c = 'CopilotForDigitalChannels'
