-- GenAI content category (per-detector rows) — reusable WHERE.
-- DMO: GenAIContentCategory__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Two shapes of parent FK:
--   - Direct on a generation: non-TOXICITY detectors (InstructionAdherence,
--     TaskResolution, PII, PROMPT_DEFENSE) — parent__c = generationId__c
--   - Via a quality row: TOXICITY sub-categories —
--     parent__c = GenAIContentQuality.id__c
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    id__c,
    parent__c,
    detectorType__c,
    category__c,
    value__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIContentCategory__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Non-TOXICITY detectors for a set of generations (direct join)
-- WHERE    → parent__c IN ('<gen_id1>','<gen_id2>')
--            AND detectorType__c != 'TOXICITY'

-- TOXICITY sub-categories for a set of quality rows
-- WHERE    → parent__c IN ('<quality_id1>','<quality_id2>')
--            AND detectorType__c = 'TOXICITY'

-- InstructionAdherence scores only
-- WHERE    → parent__c IN ('<gen_id1>','<gen_id2>')
--            AND detectorType__c = 'InstructionAdherence'
