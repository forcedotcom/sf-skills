-- Gateway requests — one row per LLM request at the GenAI Gateway.
-- DMO: GenAIGatewayRequest__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Richer than GenAIGeneration — carries the actual prompt text, token counts,
-- model params (temperature/penalties), session/user IDs, bot version, and
-- the masked-prompt variant.
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.
--
-- sessionId__c storage format (verified live): the value is stored as a
-- literal 40-char string INCLUDING surrounding double-quotes, e.g.
--   sessionId__c = "<session_uuid>"
-- Non-session features (prompt-builder previews, eval harnesses, etc.) store
-- the literal sentinel "no_session". Exact-match queries MUST include the
-- double-quotes:
--   WHERE sessionId__c = '"<session_uuid>"'
-- Or use LIKE with wildcards (robust against format variants):
--   WHERE sessionId__c LIKE '%<session_uuid>%'
-- Raw-UUID exact match returns 0 rows — the quotes are part of the stored value.
--
-- Forward join path from a session:
--   Session.ssot__Id__c  →  GatewayRequest.sessionId__c (LIKE or quoted match)
-- This is the authoritative and only supported entry point. GatewayRequest is
-- then the parent for all downstream audit-chain children — Response (via
-- generationRequestId__c), Tag/ObjRecord/Metadata/LLM (via parent__c).
-- See `scripts/fetch_dc.py` wave 3 and `references/dc_dmo_fields.md` "Cross-DMO
-- join map" for the full forward tree.

SELECT
    gatewayRequestId__c,
    generationGroupId__c,
    sessionId__c,
    userId__c,
    botVersionId__c,
    plannerId__c,
    feature__c,
    appType__c,
    model__c,
    provider__c,
    promptTemplateDevName__c,
    promptTemplateVersionNo__c,
    prompt__c,
    maskedPrompt__c,
    parameters__c,
    temperature__c,
    frequencyPenalty__c,
    presencePenalty__c,
    stopSequences__c,
    numGenerations__c,
    promptTokens__c,
    completionTokens__c,
    totalTokens__c,
    enableInputSafetyScoring__c,
    enableOutputSafetyScoring__c,
    enablePiiMasking__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGatewayRequest__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Requests for one session (direct FK; note the mandatory double-quoted form).
-- Two equivalent WHERE forms — both verified live, both return the same rows:
-- WHERE    → sessionId__c = '"<session_id>"'            (exact match on quoted string)
-- WHERE    → sessionId__c LIKE '%<session_id>%'          (format-tolerant)
-- ORDER BY → ORDER BY timestamp__c

-- Requests for a specific set of gatewayRequestIds (e.g. narrowing after a
-- session fetch, or lookup by ids harvested from another query)
-- WHERE    → gatewayRequestId__c IN ('<req_id1>','<req_id2>',...)

-- All requests for a bot version in a time window
-- WHERE    → botVersionId__c = '<version_id>'
--            AND timestamp__c >= '<iso_cutoff>'
-- ORDER BY → ORDER BY timestamp__c DESC

-- Requests using a specific prompt template
-- WHERE    → promptTemplateDevName__c = '<template_dev_name>'
--            AND timestamp__c >= '<iso_cutoff>'
