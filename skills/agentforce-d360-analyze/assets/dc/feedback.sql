-- User feedback on generations — one row per feedback event.
-- DMO: GenAIFeedback__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Captures thumbs-up/thumbs-down (and richer `action__c`) that a user gave
-- a specific generation. Joined via `generationId__c = Generation.generationId__c`.
-- `feedbackId__c` is the PK that GenAIFeedbackDetail rows point at.
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    feedbackId__c,
    generationId__c,
    generationUpdateId__c,
    generationGroupId__c,
    userId__c,
    feedback__c,
    action__c,
    source__c,
    feature__c,
    appType__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIFeedback__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Feedback for a set of generations (typical session trace path)
-- WHERE    → generationId__c IN ('<gen_id1>','<gen_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Feedback by a specific user in a time window
-- WHERE    → userId__c = '<user_id>'
--            AND timestamp__c >= '<iso_cutoff>'

-- Only thumbs-down
-- WHERE    → generationId__c IN ('<gen_id1>','<gen_id2>')
--            AND feedback__c = 'DOWN'
