-- Gateway object records — structured attachments on requests/feedback.
-- DMO: GenAIGtwyObjRecord__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Polymorphic attachment table. `parent__c` points at different parents
-- depending on `type__c`:
--   - `parent__c = GenAIGatewayRequest.gatewayRequestId__c` (grounded-record
--     attachments) — the forward-only path used by this skill's waterfall.
--   - `parent__c = GenAIFeedback.feedbackId__c` (feedback attachments) —
--     present only when the session has feedback rows.
-- The waterfall queries the gateway-request case (wave 3); feedback attachments
-- appear through the session only when feedback is present.
--
-- NOTE: No `ssot__` prefix — fields end in `__c` directly.

SELECT
    id__c,
    parent__c,
    recordId__c,
    type__c,
    name__c,
    value__c,
    metadata__c,
    feature__c,
    timestamp__c,
    orgId__c,
    cloud__c
FROM GenAIGtwyObjRecord__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- Records attached to a set of feedback rows
-- WHERE    → parent__c IN ('<feedback_id1>','<feedback_id2>',...)
-- ORDER BY → ORDER BY timestamp__c

-- Records attached to a set of gateway request ids
-- WHERE    → parent__c IN ('<req_id1>','<req_id2>')
