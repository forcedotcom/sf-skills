-- Gateway request tags — k/v metadata attached to a gateway request.
-- DMO: GenAIGatewayRequestTag__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Many rows per request. Common tags include:
--   - `prompt_template_dev_name` → which prompt template was used
--   - `user_utterance`           → raw user input that triggered this request
--
-- Joined via `parent__c = GatewayRequest.gatewayRequestId__c`.
-- No `ssot__` prefix — fields end in `__c` directly.

SELECT
    id__c,
    parent__c,
    tag__c,
    tagValue__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGatewayRequestTag__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All tags for a set of request ids
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Only `prompt_template_dev_name` tags
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>')
--            AND tag__c = 'prompt_template_dev_name'

-- Find requests where the user utterance matched a pattern
-- WHERE    → tag__c = 'user_utterance'
--            AND tagValue__c LIKE '%refund%'
