-- GenAI content quality (per-generation quality rows) — reusable WHERE.
-- DMO: GenAIContentQuality__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Joined to a generation via `parent__c = generationId__c`. One row per
-- INPUT/OUTPUT side. `isToxicityDetected__c` is populated only on OUTPUT rows.
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    id__c,
    parent__c,
    isToxicityDetected__c,
    contentType__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIContentQuality__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Quality rows for a set of generations
-- WHERE    → parent__c IN ('<gen_id1>','<gen_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Only rows where toxicity was detected (OUTPUT rows)
-- WHERE    → parent__c IN ('<gen_id1>','<gen_id2>')
--            AND isToxicityDetected__c = 'true'

-- Only OUTPUT-side rows
-- WHERE    → parent__c IN ('<gen_id1>','<gen_id2>')
--            AND contentType__c = 'OUTPUT'
