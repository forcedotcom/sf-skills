-- App-layer generation records — reusable for any WHERE filter.
-- DMO: GenAIAppGeneration__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Sibling of GenAIGeneration__dlm: where GenAIGeneration is the raw
-- gateway response, GenAIAppGeneration appears to be the app/feature-
-- layer view of the same generation (separate `id__c` from `generationId__c`).
--
-- No `ssot__` prefix — fields end in `__c` directly.
--
-- Join to a session: the same Step → Generation bridge used for
-- GenAIGeneration also works here. Pull session steps, collect
-- non-empty `ssot__GenerationId__c` values, then query here with
-- `generationId__c IN (...)`. The App-Generation row points at the
-- same underlying gateway generation.
--
-- The DMO is provisioned by default on orgs with generative AI audit
-- enabled, but row population depends on whether the org uses app-layer
-- regeneration / update flows. Verify presence with `sf ssot/metadata`
-- before relying on it.

SELECT
    id__c,
    generationId__c,
    generationUpdate__c,
    generationUpdateId__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIAppGeneration__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- App-generations for a set of step generation ids
-- WHERE    → generationId__c IN ('<gen_id1>','<gen_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- App-generations in a time window for one org
-- WHERE    → orgId__c = '<org_id_18>'
--            AND timestamp__c >= '<iso_window_start>'
--            AND timestamp__c <  '<iso_window_end>'
-- ORDER BY → ORDER BY timestamp__c
