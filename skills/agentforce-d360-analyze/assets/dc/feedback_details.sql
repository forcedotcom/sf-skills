-- Free-text / structured detail attached to a feedback event.
-- DMO: GenAIFeedbackDetail__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Zero or more rows per feedback. `feedbackText__c` is what the user typed;
-- `appFeedback__c` is an app-layer tag (e.g. the reason bucket).
-- Joined via `parent__c = GenAIFeedback.feedbackId__c`.
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    feedbackDetailId__c,
    parent__c,
    feedbackText__c,
    appFeedback__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIFeedbackDetail__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Details for a set of feedback rows
-- WHERE    → parent__c IN ('<feedback_id1>','<feedback_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Free-text feedback only (DC Query returns "" for unset text, not NULL)
-- WHERE    → parent__c IN ('<feedback_id1>','<feedback_id2>')
--            AND feedbackText__c IS NOT NULL AND feedbackText__c != ''
