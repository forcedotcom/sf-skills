-- Agent Platform Tracing spans — OpenTelemetry span tree per trace.
-- DMO: ssot__TelemetryTraceSpan__dlm
--
-- Placeholders (substituted by scripts/dc.py.load_sql):
--   WHERE_CLAUSE  — the filter expression, no "WHERE" keyword
--   ORDER_BY      — full "ORDER BY <col>" or empty string
--
-- Provisioned only when **Agent Platform Tracing** is enabled (Setup →
-- Einstein Audit, Analytics, and Monitoring Setup). Captures spans from
-- Apex, Flows, Prompt Builder, Invocable Actions, Planner, AI Gateway,
-- LLM Gateway, DC Query Federator.
--
-- Join to STDM: `ssot__TelemetryTrace__c = Interaction.ssot__TelemetryTraceId__c`.
-- Parent/child within a trace: `ssot__TelemetryParentSpanId__c = <another span>.ssot__Id__c`.

SELECT
    ssot__Id__c,
    ssot__TelemetryTrace__c,
    ssot__TelemetryParentSpanId__c,
    ssot__OperationName__c,
    ssot__ServiceName__c,
    ssot__SpanKind__c,
    ssot__StatusCode__c,
    ssot__StartDateTime__c,
    ssot__EndDateTime__c,
    ssot__DurationNumber__c,
    ssot__TelemetrySpanAttributeText__c,
    ssot__InternalOrganizationId__c
FROM ssot__TelemetryTraceSpan__dlm
WHERE {{WHERE_CLAUSE}}
{{ORDER_BY}};


-- ============================================================================
-- EXAMPLE WHERE clauses (pass via where_clause=)
-- ============================================================================

-- All spans for one trace (joins to Interaction.ssot__TelemetryTraceId__c)
-- WHERE    → ssot__TelemetryTrace__c = '<trace_id>'
-- ORDER BY → ORDER BY ssot__StartDateTime__c

-- All spans for a set of traces (whole session)
-- WHERE    → ssot__TelemetryTrace__c IN ('<trace_id1>','<trace_id2>',...)

-- Only root spans (no parent)
-- WHERE    → ssot__TelemetryTrace__c = '<trace_id>'
--            AND ssot__TelemetryParentSpanId__c = null

-- Only spans from a specific service
-- WHERE    → ssot__TelemetryTrace__c = '<trace_id>'
--            AND ssot__ServiceName__c = 'Atlas Reasoning Engine'

-- Slow spans — duration > 1s (nanoseconds in DurationNumber)
-- WHERE    → ssot__TelemetryTrace__c = '<trace_id>'
--            AND ssot__DurationNumber__c > 1000000000
