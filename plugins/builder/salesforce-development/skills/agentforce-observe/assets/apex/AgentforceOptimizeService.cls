/**
 * @description STDM query service for the agentforce-optimize Claude Code skill.
 *              Queries the Session Trace Data Model (STDM) in Data Cloud to retrieve
 *              session traces, conversation turns, messages, and steps for issue analysis.
 *
 *              Deployed once per org by the agentforce-optimize skill (Phase 1 setup).
 *              All public methods accept dataSpaceName so no Data Space is hardcoded.
 *
 * Methods:
 *   findSessions(dataSpaceName, startIso, endIso, maxRows)            → JSON List<SessionSummary>
 *   findSessions(dataSpaceName, startIso, endIso, maxRows, agentName) → JSON List<SessionSummary>
 *   getConversationDetails(dataSpaceName, sessionId)                  → JSON ConversationData
 *   getMultipleConversationDetails(dataSpaceName, sessionIds)         → JSON List<ConversationData>
 *   getLlmStepDetails(dataSpaceName, stepIds)                         → JSON List<LlmStepDetail>
 *   getMomentInsights(dataSpaceName, sessionIds)                      → JSON List<SessionInsights>
 *   getAggregatedMetrics(dataSpaceName, startIso, endIso, maxRows, agentName) → JSON AggregatedMetrics
 *   runObservabilityQuery(List<ObservabilityInput>)                         → List<ObservabilityOutput> (@InvocableMethod)
 */
public with sharing class AgentforceOptimizeService {

    // =========================================================================
    // Output wrappers
    // =========================================================================

    /** Lightweight session record returned by findSessions(). */
    public class SessionSummary {
        public String  session_id;
        public String  start_time;
        public String  end_time;
        public String  channel;
        public Long    duration_ms;
        /** How the session ended: e.g. USER_ENDED, AGENT_ENDED (null = in progress or not recorded) */
        public String  end_type;
    }

    /** A single user/agent message within a turn. */
    public class MessageData {
        public String message_id;
        /** 'Input' (user) or 'Output' (agent) — raw STDM value */
        public String message_type;
        public String text;
        public String sent_at;
    }

    /**
     * A single internal step within a turn.
     * All issue-detection fields are included:
     *   - error          → non-null means ACTION_STEP failure (P1)
     *   - pre_vars / post_vars → null delta means variable not captured (P2)
     *   - duration_ms > 10 000 → slow action (P3)
     *   - generation_id  → non-null on LLM_STEP; use getLlmStepDetails() to get the prompt
     */
    public class StepData {
        public String step_id;
        /** TOPIC_STEP | LLM_STEP | ACTION_STEP | SESSION_END | TRUST_GUARDRAILS_STEP */
        public String step_type;
        public String name;
        public String start_time;
        public String end_time;
        public Long   duration_ms;
        /** Raw input to the step (JSON for ACTION_STEP; Python dict string for LLM_STEP) */
        public String input;
        /** Raw output from the step (JSON for ACTION_STEP; Python dict string for LLM_STEP) */
        public String output;
        /** Non-null indicates the step threw an error (only ACTION_STEP counts toward action_error_count) */
        public String error;
        /** Variable snapshot before this step (null when NOT_SET) */
        public String pre_vars;
        /** Variable snapshot after this step (null when NOT_SET) */
        public String post_vars;
        /** GenAiGeneration ID — non-null on LLM_STEP; pass to getLlmStepDetails() for full prompt/response */
        public String generation_id;
        /** GenAiGatewayRequest ID — non-null on LLM_STEP; links to raw gateway request */
        public String gateway_request_id;
    }

    /**
     * One conversational turn (AiAgentInteraction of type TURN).
     * Contains all messages and steps for that turn.
     */
    public class TurnData {
        public String interaction_id;
        /** Subagent API name (stored as `topic` in STDM) — null/mismatch signals a misroute (P1) */
        public String topic;
        public String start_time;
        public String end_time;
        public Long   duration_ms;
        /** Telemetry trace ID for distributed tracing correlation */
        public String telemetry_trace_id;
        public List<MessageData> messages;
        public List<StepData>    steps;

        public TurnData() {
            messages = new List<MessageData>();
            steps    = new List<StepData>();
        }
    }

    /**
     * Full conversation for one session: session header + ordered turns.
     * turn_count and action_error_count are pre-computed for quick triage.
     */
    public class ConversationData {
        public String  session_id;
        public String  start_time;
        public String  end_time;
        public String  channel;
        public Long    duration_ms;
        /** How the session ended (null = in progress or not recorded by Data Cloud) */
        public String  end_type;
        /** Session-level variable snapshot from ssot__VariableText__c (null when absent) */
        public String  session_variables;
        public Integer turn_count        = 0;
        public Integer action_error_count = 0;
        public List<TurnData> turns;

        public ConversationData() {
            turns = new List<TurnData>();
        }
    }

    /**
     * LLM step detail retrieved from Einstein Audit & Feedback DMOs.
     * Obtained by joining AiAgentInteractionStep with GenAIGeneration and GenAIGatewayRequest.
     */
    public class LlmStepDetail {
        public String step_id;
        public String interaction_id;
        public String step_name;
        /** Full prompt text from GenAIGatewayRequest__dlm.prompt__c */
        public String prompt;
        /** LLM response text from GenAIGeneration__dlm.responseText__c */
        public String llm_response;
        public String generation_id;
        public String gateway_request_id;
    }

    /** A single intent moment within a session (from AiAgentMoment DMO). */
    public class MomentData {
        public String  moment_id;
        public String  session_id;
        public String  start_time;
        public String  end_time;
        public Long    duration_ms;
        public String  request_summary;
        public String  response_summary;
        public String  agent_api_name;
        public String  agent_version;
        /** Quality score 1-5 from AiAgentTagAssociation → AiAgentTag.Value */
        public Integer quality_score;
        /** LLM-generated reasoning for the quality score */
        public String  quality_reasoning;
        public MomentData() {}
    }

    /** RAG quality metrics from the AiRetrieverQualityMetric DMO. */
    public class RetrieverMetricData {
        public String  metric_id;
        public String  gateway_request_id;
        public String  retriever_request_id;
        public String  retriever_api_name;
        public String  user_utterance;
        public Decimal faithfulness;
        public Decimal answer_relevance;
        public Decimal context_precision;
    }

    /** Per-session insights rollup (moments + retriever metrics). */
    public class SessionInsights {
        public String  session_id;
        public String  start_time;
        public String  end_time;
        public String  end_type;
        public Long    duration_ms;
        public Integer turn_count;
        public Integer moment_count;
        public Decimal avg_quality_score;
        public Integer action_error_count;
        public List<MomentData> moments;
        public List<RetrieverMetricData> retriever_metrics;
        public String  debug_message;
        public SessionInsights() {
            moments = new List<MomentData>();
            retriever_metrics = new List<RetrieverMetricData>();
        }
    }

    /** Aggregated metrics across multiple sessions. */
    public class AggregatedMetrics {
        public Integer total_sessions;
        public Integer total_moments;
        public Integer total_turns;
        public Decimal avg_quality_score;
        public Decimal avg_session_duration_sec;
        public Map<String, Integer> end_type_counts;
        public Map<String, Integer> top_intents;
        public Map<String, Integer> quality_distribution;
        public Decimal abandonment_rate;
        public Decimal escalation_rate;
        public Decimal deflection_rate;
        public Decimal avg_faithfulness;
        public Decimal avg_answer_relevance;
        public Decimal avg_context_precision;
        public List<String> unavailable_dmos;
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Find recent sessions within a date range, optionally filtered to a specific agent.
     *
     * Agent filtering tries two strategies in order:
     *   1. Direct: ssot__AiAgentApiName__c = agentApiName on the participant DMO (no SOQL needed)
     *   2. Fallback: GenAiPlannerDefinition (SOQL) → ssot__ParticipantId__c IN plannerIds
     *      Both 15-char and 18-char ID formats are included to handle DMO inconsistency.
     *
     * If both strategies return empty, the query falls back to all sessions.
     *
     * @param dataSpaceName  Data Cloud Data Space API name (discovered in Phase 0)
     * @param startIso       ISO 8601 UTC start, e.g. '2025-03-01T00:00:00.000Z'
     * @param endIso         ISO 8601 UTC end
     * @param maxRows        Maximum sessions to return (e.g. 20)
     * @param agentApiName   Agent display name / MasterLabel to filter by (null = all agents)
     * @return JSON-serialized List<SessionSummary>
     */
    public static String findSessions(String dataSpaceName, String startIso, String endIso, Integer maxRows, String agentApiName) {
        // Step 1: Find sessions that have actual TURN interactions (skip empty preview sessions).
        // Empty sessions (sf agent preview, builder pings) create AiAgentSession + SESSION_END
        // interaction records but never TURN records. Querying for TURN directly ensures we only
        // return sessions with real conversation data.
        String turnSessionSql =
              'SELECT DISTINCT ssot__AiAgentSessionId__c '
            + 'FROM "ssot__AiAgentInteraction__dlm" '
            + 'WHERE ssot__AiAgentInteractionType__c = \'TURN\' '
            + '  AND ssot__StartTimestamp__c >= \'' + startIso + '\' '
            + '  AND ssot__StartTimestamp__c <= \'' + endIso   + '\'';

        ConnectApi.CdpQueryOutputV2 turnResult = runQuery(turnSessionSql, dataSpaceName);
        Set<String> sessionsWithTurns = new Set<String>();
        if (turnResult != null && turnResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : turnResult.data) {
                String sid = col(row.rowData, 0);
                if (sid != null) sessionsWithTurns.add(sid);
            }
        }
        System.debug(LoggingLevel.DEBUG, 'Sessions with turns in date range: ' + sessionsWithTurns.size());

        // Step 2: Build agent filter (optional)
        String sessionFilter = '';
        if (String.isNotBlank(agentApiName)) {
            // Strategy 1: filter directly by ssot__AiAgentApiName__c (simplest, no SOQL)
            String partSqlByName =
                  'SELECT ssot__AiAgentSessionId__c '
                + 'FROM "ssot__AiAgentSessionParticipant__dlm" '
                + 'WHERE ssot__AiAgentApiName__c = \'' + String.escapeSingleQuotes(agentApiName) + '\'';
            ConnectApi.CdpQueryOutputV2 nameResult = runQuery(partSqlByName, dataSpaceName);
            List<String> sessionIds = extractSessionIds(nameResult);

            if (!sessionIds.isEmpty()) {
                sessionFilter = '  AND ssot__Id__c IN (\'' + String.join(sessionIds, '\',\'') + '\') ';
                System.debug(LoggingLevel.DEBUG, 'Agent filter (AiAgentApiName): '
                    + sessionIds.size() + ' session(s) for agent: ' + agentApiName);
            } else {
                // Strategy 2: GenAiPlannerDefinition SOQL → ssot__ParticipantId__c
                System.debug(LoggingLevel.DEBUG,
                    'AiAgentApiName filter returned no sessions; trying GenAiPlannerDefinition fallback');
                List<String> plannerIds = resolvePlannerIds(agentApiName);
                if (!plannerIds.isEmpty()) {
                    String pInClause = '(\'' + String.join(plannerIds, '\',\'') + '\')';
                    String partSqlById =
                          'SELECT ssot__AiAgentSessionId__c '
                        + 'FROM "ssot__AiAgentSessionParticipant__dlm" '
                        + 'WHERE ssot__ParticipantId__c IN ' + pInClause;
                    ConnectApi.CdpQueryOutputV2 idResult = runQuery(partSqlById, dataSpaceName);
                    List<String> sessionIds2 = extractSessionIds(idResult);
                    if (!sessionIds2.isEmpty()) {
                        sessionFilter = '  AND ssot__Id__c IN (\'' + String.join(sessionIds2, '\',\'') + '\') ';
                        System.debug(LoggingLevel.DEBUG, 'Agent filter (PlannerIds): '
                            + plannerIds.size() + ' planner(s), ' + sessionIds2.size() + ' session(s)');
                    } else {
                        System.debug(LoggingLevel.WARN,
                            'No sessions found for agent: ' + agentApiName + ' — returning all sessions');
                    }
                } else {
                    System.debug(LoggingLevel.WARN,
                        'Agent not found: ' + agentApiName + ' — returning sessions for all agents');
                }
            }
        }

        // Step 3: Query sessions, preferring those with actual turns
        String turnFilter = '';
        if (!sessionsWithTurns.isEmpty()) {
            List<String> turnList = new List<String>(sessionsWithTurns);
            turnFilter = '  AND ssot__Id__c IN (\'' + String.join(turnList, '\',\'') + '\') ';
        }

        String sql =
              'SELECT ssot__Id__c, ssot__StartTimestamp__c, ssot__EndTimestamp__c, '
            + '       ssot__AiAgentChannelType__c, ssot__AiAgentSessionEndType__c '
            + 'FROM "ssot__AiAgentSession__dlm" '
            + 'WHERE ssot__StartTimestamp__c >= \'' + startIso + '\' '
            + '  AND ssot__StartTimestamp__c <= \'' + endIso   + '\' '
            + sessionFilter
            + turnFilter
            + 'ORDER BY ssot__StartTimestamp__c DESC '
            + 'LIMIT ' + maxRows;

        ConnectApi.CdpQueryOutputV2 result = runQuery(sql, dataSpaceName);
        List<SessionSummary> sessions = new List<SessionSummary>();

        if (result != null && result.data != null) {
            for (ConnectApi.CdpQueryV2Row row : result.data) {
                SessionSummary s = new SessionSummary();
                s.session_id  = col(row.rowData, 0);
                s.start_time  = col(row.rowData, 1);
                s.end_time    = col(row.rowData, 2);
                s.channel     = col(row.rowData, 3);
                s.end_type    = notSet(col(row.rowData, 4));
                s.duration_ms = durationMs(s.start_time, s.end_time);
                sessions.add(s);
            }
        }
        return JSON.serialize(sessions);
    }

    /**
     * Overload that queries sessions for all agents (no agent filter).
     * Kept for backwards compatibility; prefer the 5-argument version.
     */
    public static String findSessions(String dataSpaceName, String startIso, String endIso, Integer maxRows) {
        return findSessions(dataSpaceName, startIso, endIso, maxRows, null);
    }

    /**
     * Retrieve full conversation details for a single session.
     * Fetches interactions, messages, and steps (with error/variable/generation fields).
     *
     * @param dataSpaceName  Data Cloud Data Space API name
     * @param sessionId      ssot__Id__c of the AiAgentSession
     * @return JSON-serialized ConversationData
     */
    public static String getConversationDetails(String dataSpaceName, String sessionId) {
        if (String.isBlank(sessionId)) return null;

        ConversationData convo = new ConversationData();
        convo.session_id = sessionId;

        // --- Session header ---
        String sessionSql =
              'SELECT ssot__StartTimestamp__c, ssot__EndTimestamp__c, ssot__AiAgentChannelType__c, '
            + '       ssot__AiAgentSessionEndType__c, ssot__VariableText__c '
            + 'FROM "ssot__AiAgentSession__dlm" '
            + 'WHERE ssot__Id__c = \'' + String.escapeSingleQuotes(sessionId) + '\'';

        ConnectApi.CdpQueryOutputV2 sessionResult = runQuery(sessionSql, dataSpaceName);
        if (sessionResult != null && sessionResult.data != null && !sessionResult.data.isEmpty()) {
            List<Object> r = sessionResult.data[0].rowData;
            convo.start_time        = col(r, 0);
            convo.end_time          = col(r, 1);
            convo.channel           = col(r, 2);
            convo.end_type          = notSet(col(r, 3));
            convo.session_variables = notSet(col(r, 4));
            convo.duration_ms       = durationMs(convo.start_time, convo.end_time);
        }

        // --- Interactions (turns) ---
        // ssot__TopicApiName__c included for misroute detection
        // ssot__TelemetryTraceId__c included for distributed tracing
        String interSql =
              'SELECT ssot__Id__c, ssot__TopicApiName__c, ssot__AiAgentInteractionType__c, '
            + '       ssot__StartTimestamp__c, ssot__EndTimestamp__c, ssot__TelemetryTraceId__c '
            + 'FROM "ssot__AiAgentInteraction__dlm" '
            + 'WHERE ssot__AiAgentSessionId__c = \'' + String.escapeSingleQuotes(sessionId) + '\' '
            + 'ORDER BY ssot__StartTimestamp__c';

        ConnectApi.CdpQueryOutputV2 interResult = runQuery(interSql, dataSpaceName);
        if (interResult == null || interResult.data == null || interResult.data.isEmpty()) {
            return JSON.serialize(convo);
        }

        Map<String, TurnData> turnById = new Map<String, TurnData>();
        List<String> turnIds = new List<String>();

        for (ConnectApi.CdpQueryV2Row row : interResult.data) {
            String interType = col(row.rowData, 2);
            // SESSION_END is a meta interaction, not a user turn
            if ('SESSION_END'.equalsIgnoreCase(interType)) continue;

            TurnData t            = new TurnData();
            t.interaction_id      = col(row.rowData, 0);
            t.topic               = col(row.rowData, 1);
            t.start_time          = col(row.rowData, 3);
            t.end_time            = col(row.rowData, 4);
            t.duration_ms         = durationMs(t.start_time, t.end_time);
            t.telemetry_trace_id  = notSet(col(row.rowData, 5));
            turnById.put(t.interaction_id, t);
            turnIds.add(t.interaction_id);
            convo.turns.add(t);
        }
        convo.turn_count = convo.turns.size();

        if (turnIds.isEmpty()) return JSON.serialize(convo);

        String inClause = '(\'' + String.join(turnIds, '\',\'') + '\')';

        // --- Messages ---
        String msgSql =
              'SELECT ssot__Id__c, ssot__AiAgentInteractionId__c, '
            + '       ssot__AiAgentInteractionMessageType__c, ssot__ContentText__c, '
            + '       ssot__MessageSentTimestamp__c '
            + 'FROM "ssot__AiAgentInteractionMessage__dlm" '
            + 'WHERE ssot__AiAgentInteractionId__c IN ' + inClause + ' '
            + 'ORDER BY ssot__MessageSentTimestamp__c';

        ConnectApi.CdpQueryOutputV2 msgResult = runQuery(msgSql, dataSpaceName);
        if (msgResult != null && msgResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : msgResult.data) {
                TurnData t = turnById.get(col(row.rowData, 1));
                if (t == null) continue;

                MessageData m  = new MessageData();
                m.message_id   = col(row.rowData, 0);
                m.message_type = col(row.rowData, 2); // 'Input' or 'Output'
                m.text         = col(row.rowData, 3);
                m.sent_at      = col(row.rowData, 4);
                t.messages.add(m);
            }
        }

        // Infer message types when ssot__AiAgentInteractionMessageType__c is null.
        // In STDM, messages within a turn alternate: user Input first, then agent Output.
        // If ALL messages in a turn have null type, assign by position (odd=Input, even=Output).
        for (TurnData t : convo.turns) {
            Boolean anyNull = false;
            Boolean allNull = true;
            for (MessageData m : t.messages) {
                if (m.message_type == null) { anyNull = true; }
                else { allNull = false; }
            }
            if (anyNull && allNull) {
                // All null — infer from position: 1st=Input, 2nd=Output, 3rd=Input, ...
                for (Integer i = 0; i < t.messages.size(); i++) {
                    t.messages[i].message_type = (Math.mod(i, 2) == 0) ? 'Input' : 'Output';
                }
            } else if (anyNull) {
                // Mixed — fill gaps by inferring the opposite of the nearest known neighbor
                for (Integer i = 0; i < t.messages.size(); i++) {
                    if (t.messages[i].message_type == null) {
                        // Look at previous message for context
                        if (i > 0 && t.messages[i - 1].message_type != null) {
                            t.messages[i].message_type = 'Input'.equals(t.messages[i - 1].message_type)
                                ? 'Output' : 'Input';
                        } else if (i == 0) {
                            t.messages[i].message_type = 'Input'; // first message is always user
                        }
                    }
                }
            }
        }

        // --- Steps ---
        // All issue-detection fields are selected:
        //   ssot__ErrorMessageText__c        → Action error (P1)
        //   ssot__InputValueText__c          → Wrong action input (P2)
        //   ssot__OutputValueText__c         → Action output / TRUST_GUARDRAILS adherence dict
        //   ssot__PreStepVariableText__c     → Pre-step variable snapshot (P2)
        //   ssot__PostStepVariableText__c    → Post-step variable snapshot (P2)
        //   ssot__EndTimestamp__c            → Step duration for slow action (P3)
        //   ssot__GenerationId__c            → Links to GenAIGeneration__dlm (LLM audit)
        //   ssot__GenAiGatewayRequestId__c   → Links to GenAIGatewayRequest__dlm (prompt text)
        String stepSql =
              'SELECT ssot__Id__c, ssot__AiAgentInteractionId__c, '
            + '       ssot__AiAgentInteractionStepType__c, ssot__Name__c, '
            + '       ssot__StartTimestamp__c, ssot__EndTimestamp__c, '
            + '       ssot__InputValueText__c, ssot__OutputValueText__c, '
            + '       ssot__ErrorMessageText__c, '
            + '       ssot__PreStepVariableText__c, ssot__PostStepVariableText__c, '
            + '       ssot__GenerationId__c, ssot__GenAiGatewayRequestId__c '
            + 'FROM "ssot__AiAgentInteractionStep__dlm" '
            + 'WHERE ssot__AiAgentInteractionId__c IN ' + inClause + ' '
            + 'ORDER BY ssot__StartTimestamp__c';

        ConnectApi.CdpQueryOutputV2 stepResult = runQuery(stepSql, dataSpaceName);
        if (stepResult != null && stepResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : stepResult.data) {
                TurnData t = turnById.get(col(row.rowData, 1));
                if (t == null) continue;

                StepData s        = new StepData();
                s.step_id         = col(row.rowData, 0);
                s.step_type       = col(row.rowData, 2);
                s.name            = col(row.rowData, 3);
                s.start_time      = col(row.rowData, 4);
                s.end_time        = col(row.rowData, 5);
                s.duration_ms     = durationMs(s.start_time, s.end_time);
                s.input           = notSet(col(row.rowData, 6));
                s.output          = notSet(col(row.rowData, 7));
                s.error           = notSet(col(row.rowData, 8));
                s.pre_vars        = notSet(col(row.rowData, 9));
                s.post_vars       = notSet(col(row.rowData, 10));
                s.generation_id   = notSet(col(row.rowData, 11));
                s.gateway_request_id = notSet(col(row.rowData, 12));

                if (s.error != null && 'ACTION_STEP'.equalsIgnoreCase(s.step_type)) convo.action_error_count++;
                t.steps.add(s);
            }
        }

        return JSON.serialize(convo);
    }

    /**
     * Retrieve full conversation details for multiple sessions.
     *
     * @param dataSpaceName  Data Cloud Data Space API name
     * @param sessionIds     List of ssot__Id__c values (keep under 20 to avoid CPU limits)
     * @return JSON-serialized List<ConversationData>
     */
    public static String getMultipleConversationDetails(String dataSpaceName, List<String> sessionIds) {
        List<ConversationData> results = new List<ConversationData>();
        if (sessionIds == null || sessionIds.isEmpty()) return JSON.serialize(results);

        for (String sid : sessionIds) {
            String detail = getConversationDetails(dataSpaceName, sid);
            if (String.isNotBlank(detail)) {
                ConversationData convo = (ConversationData) JSON.deserialize(detail, ConversationData.class);
                results.add(convo);
            }
        }
        return JSON.serialize(results);
    }

    /**
     * Retrieve LLM prompt and response for a set of LLM_STEP records by joining the
     * Einstein Audit & Feedback DMOs (GenAIGatewayRequest and GenAIGeneration).
     *
     * Typical use: after finding LLM_STEP records with non-null generation_id in a
     * ConversationData, pass those step IDs here to see what prompt was sent and what
     * the model actually returned — useful for diagnosing LOW instruction adherence.
     *
     * @param dataSpaceName  Data Cloud Data Space API name
     * @param stepIds        List of ssot__Id__c values from LLM_STEP StepData records
     * @return JSON-serialized List<LlmStepDetail>
     */
    public static String getLlmStepDetails(String dataSpaceName, List<String> stepIds) {
        if (stepIds == null || stepIds.isEmpty()) return JSON.serialize(new List<LlmStepDetail>());

        String inClause = '(\'' + String.join(stepIds, '\',\'') + '\')';
        String sql =
              'SELECT s.ssot__Id__c, s.ssot__AiAgentInteractionId__c, s.ssot__Name__c, '
            + '       r.prompt__c, g.responseText__c, '
            + '       s.ssot__GenerationId__c, s.ssot__GenAiGatewayRequestId__c '
            + 'FROM "ssot__AiAgentInteractionStep__dlm" s '
            + 'LEFT JOIN "GenAIGeneration__dlm" g '
            + '  ON s.ssot__GenerationId__c = g.generationId__c '
            + 'LEFT JOIN "GenAIGatewayRequest__dlm" r '
            + '  ON s.ssot__GenAiGatewayRequestId__c = r.gatewayRequestId__c '
            + 'WHERE s.ssot__Id__c IN ' + inClause;

        ConnectApi.CdpQueryOutputV2 result = runQuery(sql, dataSpaceName);
        List<LlmStepDetail> details = new List<LlmStepDetail>();

        if (result != null && result.data != null) {
            for (ConnectApi.CdpQueryV2Row row : result.data) {
                LlmStepDetail d      = new LlmStepDetail();
                d.step_id            = col(row.rowData, 0);
                d.interaction_id     = col(row.rowData, 1);
                d.step_name          = col(row.rowData, 2);
                d.prompt             = notSet(col(row.rowData, 3));
                d.llm_response       = notSet(col(row.rowData, 4));
                d.generation_id      = notSet(col(row.rowData, 5));
                d.gateway_request_id = notSet(col(row.rowData, 6));
                details.add(d);
            }
        }
        return JSON.serialize(details);
    }

    /**
     * Retrieve moment insights (intent summaries, durations) and retriever quality metrics
     * for a set of sessions. Gracefully degrades if DMOs are unavailable.
     *
     * @param dataSpaceName  Data Cloud Data Space API name
     * @param sessionIds     List of ssot__Id__c values from AiAgentSession
     * @return JSON-serialized List<SessionInsights>
     */
    public static String getMomentInsights(String dataSpaceName, List<String> sessionIds) {
        List<SessionInsights> results = new List<SessionInsights>();
        if (sessionIds == null || sessionIds.isEmpty()) return JSON.serialize(results);

        String inClause = '(\'' + String.join(sessionIds, '\',\'') + '\')';

        // --- Session headers ---
        String sessionSql =
              'SELECT ssot__Id__c, ssot__StartTimestamp__c, ssot__EndTimestamp__c, '
            + '       ssot__AiAgentSessionEndType__c '
            + 'FROM "ssot__AiAgentSession__dlm" '
            + 'WHERE ssot__Id__c IN ' + inClause;

        ConnectApi.CdpQueryOutputV2 sessionResult = runQuery(sessionSql, dataSpaceName);
        Map<String, SessionInsights> insightsById = new Map<String, SessionInsights>();

        if (sessionResult != null && sessionResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : sessionResult.data) {
                SessionInsights si = new SessionInsights();
                si.session_id   = col(row.rowData, 0);
                si.start_time   = col(row.rowData, 1);
                si.end_time     = col(row.rowData, 2);
                si.end_type     = notSet(col(row.rowData, 3));
                si.duration_ms  = durationMs(si.start_time, si.end_time);
                insightsById.put(si.session_id, si);
                results.add(si);
            }
        }

        // --- Turn counts ---
        String turnSql =
              'SELECT ssot__AiAgentSessionId__c, COUNT(*) '
            + 'FROM "ssot__AiAgentInteraction__dlm" '
            + 'WHERE ssot__AiAgentSessionId__c IN ' + inClause + ' '
            + '  AND ssot__AiAgentInteractionType__c = \'TURN\' '
            + 'GROUP BY ssot__AiAgentSessionId__c';

        ConnectApi.CdpQueryOutputV2 turnResult = runQuery(turnSql, dataSpaceName);
        if (turnResult != null && turnResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : turnResult.data) {
                SessionInsights si = insightsById.get(col(row.rowData, 0));
                if (si != null) {
                    si.turn_count = Integer.valueOf(col(row.rowData, 1));
                }
            }
        }

        // --- Action error counts ---
        String errSql =
              'SELECT ssot__AiAgentInteraction__dlm.ssot__AiAgentSessionId__c, COUNT(*) '
            + 'FROM "ssot__AiAgentInteractionStep__dlm" '
            + 'JOIN "ssot__AiAgentInteraction__dlm" '
            + '  ON ssot__AiAgentInteractionStep__dlm.ssot__AiAgentInteractionId__c = ssot__AiAgentInteraction__dlm.ssot__Id__c '
            + 'WHERE ssot__AiAgentInteraction__dlm.ssot__AiAgentSessionId__c IN ' + inClause + ' '
            + '  AND ssot__AiAgentInteractionStep__dlm.ssot__AiAgentInteractionStepType__c = \'ACTION_STEP\' '
            + '  AND ssot__AiAgentInteractionStep__dlm.ssot__ErrorMessageText__c IS NOT NULL '
            + '  AND ssot__AiAgentInteractionStep__dlm.ssot__ErrorMessageText__c != \'NOT_SET\' '
            + 'GROUP BY ssot__AiAgentInteraction__dlm.ssot__AiAgentSessionId__c';

        ConnectApi.CdpQueryOutputV2 errResult = runQuery(errSql, dataSpaceName);
        if (errResult != null && errResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : errResult.data) {
                SessionInsights si = insightsById.get(col(row.rowData, 0));
                if (si != null) {
                    si.action_error_count = Integer.valueOf(col(row.rowData, 1));
                }
            }
        }

        // --- Moments (graceful degradation) ---
        Boolean momentAvailable = isDmoAvailable('ssot__AiAgentMoment__dlm', dataSpaceName);
        if (momentAvailable) {
            String momentSql =
                  'SELECT ssot__Id__c, ssot__AiAgentSessionId__c, '
                + '       ssot__StartTimestamp__c, ssot__EndTimestamp__c, '
                + '       ssot__RequestSummaryText__c, ssot__ResponseSummaryText__c, '
                + '       ssot__AiAgentApiName__c, ssot__AiAgentVersionApiName__c '
                + 'FROM "ssot__AiAgentMoment__dlm" '
                + 'WHERE ssot__AiAgentSessionId__c IN ' + inClause + ' '
                + 'ORDER BY ssot__StartTimestamp__c';

            ConnectApi.CdpQueryOutputV2 momentResult = runQuery(momentSql, dataSpaceName);
            if (momentResult != null && momentResult.data != null) {
                for (ConnectApi.CdpQueryV2Row row : momentResult.data) {
                    MomentData m       = new MomentData();
                    m.moment_id        = col(row.rowData, 0);
                    m.session_id       = col(row.rowData, 1);
                    m.start_time       = col(row.rowData, 2);
                    m.end_time         = col(row.rowData, 3);
                    m.duration_ms      = durationMs(m.start_time, m.end_time);
                    m.request_summary  = notSet(col(row.rowData, 4));
                    m.response_summary = notSet(col(row.rowData, 5));
                    m.agent_api_name   = notSet(col(row.rowData, 6));
                    m.agent_version    = notSet(col(row.rowData, 7));

                    SessionInsights si = insightsById.get(m.session_id);
                    if (si != null) si.moments.add(m);
                }
            }
            // --- Quality scores via AiAgentTagAssociation → AiAgentTag ---
            if (isDmoAvailable('ssot__AiAgentTagAssociation__dlm', dataSpaceName)) {
                // Collect all moment IDs for the quality score query
                List<String> momentIds = new List<String>();
                Map<String, MomentData> momentById = new Map<String, MomentData>();
                for (SessionInsights si : results) {
                    for (MomentData m : si.moments) {
                        momentIds.add(m.moment_id);
                        momentById.put(m.moment_id, m);
                    }
                }

                if (!momentIds.isEmpty()) {
                    String momentInClause = '(\'' + String.join(momentIds, '\',\'') + '\')';
                    String qualitySql =
                          'SELECT ta.ssot__AiAgentMomentId__c, t.ssot__Value__c, '
                        + '       ta.ssot__AssociationReasonText__c '
                        + 'FROM "ssot__AiAgentTagAssociation__dlm" ta '
                        + 'JOIN "ssot__AiAgentTag__dlm" t '
                        + '  ON ta.ssot__AiAgentTagId__c = t.ssot__Id__c '
                        + 'WHERE ta.ssot__AiAgentMomentId__c IN ' + momentInClause;

                    ConnectApi.CdpQueryOutputV2 qualityResult = runQuery(qualitySql, dataSpaceName);
                    if (qualityResult != null && qualityResult.data != null) {
                        for (ConnectApi.CdpQueryV2Row row : qualityResult.data) {
                            String momentId = col(row.rowData, 0);
                            MomentData m = momentById.get(momentId);
                            if (m != null) {
                                m.quality_score     = toInteger(col(row.rowData, 1));
                                m.quality_reasoning = notSet(col(row.rowData, 2));
                            }
                        }
                    }
                }
            }
        } else {
            for (SessionInsights si : results) {
                si.debug_message = 'AiAgentMoment DMO not available in this org';
            }
        }

        // Set moment_count and avg_quality_score per session
        for (SessionInsights si : results) {
            si.moment_count = si.moments.size();
            Integer scoreSum = 0;
            Integer scoreCount = 0;
            for (MomentData m : si.moments) {
                if (m.quality_score != null) {
                    scoreSum += m.quality_score;
                    scoreCount++;
                }
            }
            if (scoreCount > 0) {
                si.avg_quality_score = Decimal.valueOf(scoreSum) / scoreCount;
            }
        }

        // --- Retriever quality metrics (graceful degradation) ---
        Boolean retrieverAvailable = isDmoAvailable('ssot__AiRetrieverQualityMetric__dlm', dataSpaceName);
        if (retrieverAvailable) {
            // Retriever metrics link to sessions via gateway request IDs on LLM steps.
            // Query all retriever metrics for gateway requests that belong to these sessions.
            String retrieverSql =
                  'SELECT r.ssot__Id__c, r.ssot__AiGatewayRequestId__c, '
                + '       r.ssot__AiRetrieverRequestId__c, r.ssot__RetrieverApiName__c, '
                + '       r.ssot__UserUtteranceText__c, '
                + '       r.ssot__FaithfulnessRelevancyScoreNumber__c, '
                + '       r.ssot__AnswerRelevancyScoreNumber__c, '
                + '       r.ssot__ContextPrecisionScoreNumber__c, '
                + '       i.ssot__AiAgentSessionId__c '
                + 'FROM "ssot__AiRetrieverQualityMetric__dlm" r '
                + 'JOIN "ssot__AiAgentInteractionStep__dlm" s '
                + '  ON r.ssot__AiGatewayRequestId__c = s.ssot__GenAiGatewayRequestId__c '
                + 'JOIN "ssot__AiAgentInteraction__dlm" i '
                + '  ON s.ssot__AiAgentInteractionId__c = i.ssot__Id__c '
                + 'WHERE i.ssot__AiAgentSessionId__c IN ' + inClause;

            ConnectApi.CdpQueryOutputV2 retResult = runQuery(retrieverSql, dataSpaceName);
            if (retResult != null && retResult.data != null) {
                for (ConnectApi.CdpQueryV2Row row : retResult.data) {
                    RetrieverMetricData rm  = new RetrieverMetricData();
                    rm.metric_id            = col(row.rowData, 0);
                    rm.gateway_request_id   = col(row.rowData, 1);
                    rm.retriever_request_id = col(row.rowData, 2);
                    rm.retriever_api_name   = notSet(col(row.rowData, 3));
                    rm.user_utterance       = notSet(col(row.rowData, 4));
                    rm.faithfulness         = toDecimal(col(row.rowData, 5));
                    rm.answer_relevance     = toDecimal(col(row.rowData, 6));
                    rm.context_precision    = toDecimal(col(row.rowData, 7));

                    String sessionId = col(row.rowData, 8);
                    SessionInsights si = insightsById.get(sessionId);
                    if (si != null) si.retriever_metrics.add(rm);
                }
            }
        }

        return JSON.serialize(results);
    }

    /**
     * Compute aggregated metrics across sessions in a date range.
     * Includes session rates (abandonment, escalation, deflection), top intents from moments,
     * and average RAG quality scores. Gracefully degrades when DMOs are unavailable.
     *
     * @param dataSpaceName  Data Cloud Data Space API name
     * @param startIso       ISO 8601 UTC start timestamp
     * @param endIso         ISO 8601 UTC end timestamp
     * @param maxRows        Maximum sessions to aggregate over
     * @param agentApiName   Agent MasterLabel to filter by (null = all agents)
     * @return JSON-serialized AggregatedMetrics
     */
    public static String getAggregatedMetrics(String dataSpaceName, String startIso, String endIso, Integer maxRows, String agentApiName) {
        AggregatedMetrics metrics = new AggregatedMetrics();
        metrics.end_type_counts  = new Map<String, Integer>();
        metrics.top_intents      = new Map<String, Integer>();
        metrics.unavailable_dmos = new List<String>();

        // Step 1: Find sessions (reuse existing method)
        String sessionsJson = findSessions(dataSpaceName, startIso, endIso, maxRows, agentApiName);
        List<SessionSummary> sessions = (List<SessionSummary>) JSON.deserialize(sessionsJson, List<SessionSummary>.class);
        metrics.total_sessions = sessions.size();

        if (sessions.isEmpty()) return JSON.serialize(metrics);

        // Compute session-level aggregates
        Decimal totalDurationSec = 0;
        Integer durationCount = 0;
        for (SessionSummary s : sessions) {
            // End type distribution
            String endType = s.end_type != null ? s.end_type : 'UNKNOWN';
            Integer cnt = metrics.end_type_counts.get(endType);
            metrics.end_type_counts.put(endType, cnt != null ? cnt + 1 : 1);

            // Duration
            if (s.duration_ms != null) {
                totalDurationSec += Decimal.valueOf(s.duration_ms) / 1000;
                durationCount++;
            }
        }

        if (durationCount > 0) {
            metrics.avg_session_duration_sec = totalDurationSec / durationCount;
        }

        // Session rates
        Integer userEnded = metrics.end_type_counts.get('USER_ENDED');
        Integer agentEnded = metrics.end_type_counts.get('AGENT_ENDED');
        Integer escalated = metrics.end_type_counts.get('ESCALATED');
        Integer total = metrics.total_sessions;

        metrics.abandonment_rate = Decimal.valueOf(userEnded != null ? userEnded : 0) / total;
        metrics.deflection_rate  = Decimal.valueOf(agentEnded != null ? agentEnded : 0) / total;
        metrics.escalation_rate  = Decimal.valueOf(escalated != null ? escalated : 0) / total;

        // Collect session IDs for sub-queries
        List<String> sessionIds = new List<String>();
        for (SessionSummary s : sessions) {
            sessionIds.add(s.session_id);
        }
        String inClause = '(\'' + String.join(sessionIds, '\',\'') + '\')';

        // Step 2: Total turns
        String turnSql =
              'SELECT COUNT(*) '
            + 'FROM "ssot__AiAgentInteraction__dlm" '
            + 'WHERE ssot__AiAgentSessionId__c IN ' + inClause + ' '
            + '  AND ssot__AiAgentInteractionType__c = \'TURN\'';

        ConnectApi.CdpQueryOutputV2 turnResult = runQuery(turnSql, dataSpaceName);
        if (turnResult != null && turnResult.data != null && !turnResult.data.isEmpty()) {
            metrics.total_turns = Integer.valueOf(col(turnResult.data[0].rowData, 0));
        }

        // Step 3: Moments — count + top intents
        if (isDmoAvailable('ssot__AiAgentMoment__dlm', dataSpaceName)) {
            // Total moment count
            String momentCountSql =
                  'SELECT COUNT(*) '
                + 'FROM "ssot__AiAgentMoment__dlm" '
                + 'WHERE ssot__AiAgentSessionId__c IN ' + inClause;

            ConnectApi.CdpQueryOutputV2 mcResult = runQuery(momentCountSql, dataSpaceName);
            if (mcResult != null && mcResult.data != null && !mcResult.data.isEmpty()) {
                metrics.total_moments = Integer.valueOf(col(mcResult.data[0].rowData, 0));
            }

            // Top intents by request summary (GROUP BY truncated summary)
            String intentSql =
                  'SELECT ssot__RequestSummaryText__c, COUNT(*) AS cnt '
                + 'FROM "ssot__AiAgentMoment__dlm" '
                + 'WHERE ssot__AiAgentSessionId__c IN ' + inClause + ' '
                + '  AND ssot__RequestSummaryText__c IS NOT NULL '
                + '  AND ssot__RequestSummaryText__c != \'NOT_SET\' '
                + 'GROUP BY ssot__RequestSummaryText__c '
                + 'ORDER BY cnt DESC '
                + 'LIMIT 20';

            ConnectApi.CdpQueryOutputV2 intentResult = runQuery(intentSql, dataSpaceName);
            if (intentResult != null && intentResult.data != null) {
                for (ConnectApi.CdpQueryV2Row row : intentResult.data) {
                    String intent = col(row.rowData, 0);
                    Integer intentCnt = Integer.valueOf(col(row.rowData, 1));
                    if (intent != null) {
                        // Truncate long summaries for the top_intents map key
                        if (intent.length() > 100) intent = intent.substring(0, 100) + '...';
                        metrics.top_intents.put(intent, intentCnt);
                    }
                }
            }
        } else {
            metrics.unavailable_dmos.add('ssot__AiAgentMoment__dlm');
        }

        // Step 3b: Quality scores via AiAgentTagAssociation → AiAgentTag
        metrics.quality_distribution = new Map<String, Integer>();
        if (isDmoAvailable('ssot__AiAgentTagAssociation__dlm', dataSpaceName)) {
            // AVG quality score and distribution across all moments in these sessions
            String qualityAvgSql =
                  'SELECT t.ssot__Value__c, COUNT(*) AS cnt '
                + 'FROM "ssot__AiAgentTagAssociation__dlm" ta '
                + 'JOIN "ssot__AiAgentTag__dlm" t '
                + '  ON ta.ssot__AiAgentTagId__c = t.ssot__Id__c '
                + 'WHERE ta.ssot__AiAgentSessionId__c IN ' + inClause + ' '
                + 'GROUP BY t.ssot__Value__c '
                + 'ORDER BY t.ssot__Value__c';

            ConnectApi.CdpQueryOutputV2 qualityResult = runQuery(qualityAvgSql, dataSpaceName);
            if (qualityResult != null && qualityResult.data != null) {
                Integer totalScore = 0;
                Integer totalCount = 0;
                for (ConnectApi.CdpQueryV2Row row : qualityResult.data) {
                    String scoreStr = col(row.rowData, 0);
                    Integer cnt = Integer.valueOf(col(row.rowData, 1));
                    if (scoreStr != null && cnt != null) {
                        Integer score = toInteger(scoreStr);
                        metrics.quality_distribution.put(String.valueOf(score), cnt);
                        if (score != null) {
                            totalScore += score * cnt;
                            totalCount += cnt;
                        }
                    }
                }
                if (totalCount > 0) {
                    metrics.avg_quality_score = Decimal.valueOf(totalScore) / totalCount;
                }
            }
        } else {
            metrics.unavailable_dmos.add('ssot__AiAgentTagAssociation__dlm');
        }

        // Step 4: Retriever quality averages
        if (isDmoAvailable('ssot__AiRetrieverQualityMetric__dlm', dataSpaceName)) {
            String retSql =
                  'SELECT AVG(r.ssot__FaithfulnessRelevancyScoreNumber__c), '
                + '       AVG(r.ssot__AnswerRelevancyScoreNumber__c), '
                + '       AVG(r.ssot__ContextPrecisionScoreNumber__c) '
                + 'FROM "ssot__AiRetrieverQualityMetric__dlm" r '
                + 'JOIN "ssot__AiAgentInteractionStep__dlm" s '
                + '  ON r.ssot__AiGatewayRequestId__c = s.ssot__GenAiGatewayRequestId__c '
                + 'JOIN "ssot__AiAgentInteraction__dlm" i '
                + '  ON s.ssot__AiAgentInteractionId__c = i.ssot__Id__c '
                + 'WHERE i.ssot__AiAgentSessionId__c IN ' + inClause;

            ConnectApi.CdpQueryOutputV2 retResult = runQuery(retSql, dataSpaceName);
            if (retResult != null && retResult.data != null && !retResult.data.isEmpty()) {
                metrics.avg_faithfulness      = toDecimal(col(retResult.data[0].rowData, 0));
                metrics.avg_answer_relevance  = toDecimal(col(retResult.data[0].rowData, 1));
                metrics.avg_context_precision = toDecimal(col(retResult.data[0].rowData, 2));
            }
        } else {
            metrics.unavailable_dmos.add('ssot__AiRetrieverQualityMetric__dlm');
        }

        return JSON.serialize(metrics);
    }

    // =========================================================================
    // Private helpers
    // =========================================================================

    /** Cache for DMO availability probes to avoid repeated queries. */
    private static Map<String, Boolean> dmoAvailabilityCache = new Map<String, Boolean>();

    /**
     * Probe whether a DMO exists and is queryable in this org's Data Cloud.
     * Results are cached for the transaction to avoid repeated probes.
     */
    private static Boolean isDmoAvailable(String dmoName, String dataSpaceName) {
        if (dmoAvailabilityCache.containsKey(dmoName)) return dmoAvailabilityCache.get(dmoName);
        ConnectApi.CdpQueryInput inp = new ConnectApi.CdpQueryInput();
        inp.sql = 'SELECT COUNT(*) FROM "' + dmoName + '"';
        try {
            ConnectApi.CdpQueryOutputV2 result = ConnectApi.CdpQuery.queryAnsiSqlV2(inp, dataSpaceName);
            dmoAvailabilityCache.put(dmoName, true);
            return true;
        } catch (Exception e) {
            System.debug(LoggingLevel.WARN, 'DMO not available: ' + dmoName + ' — ' + e.getMessage());
            dmoAvailabilityCache.put(dmoName, false);
            return false;
        }
    }

    /** Safely parse a string to Decimal; returns null on failure. */
    private static Decimal toDecimal(String val) {
        if (String.isBlank(val) || val == 'NOT_SET') return null;
        try {
            return Decimal.valueOf(val);
        } catch (Exception e) {
            return null;
        }
    }

    /** Safely parse a string to Integer (truncating decimals); returns null on failure. */
    private static Integer toInteger(String val) {
        if (String.isBlank(val) || val == 'NOT_SET') return null;
        try {
            return Decimal.valueOf(val).intValue();
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Resolve an Agentforce agent name to its GenAiPlannerDefinition IDs.
     *
     * Each deployed agent version creates a GenAiPlannerDefinition whose MasterLabel
     * matches the agent's display name (e.g. 'TeslaSupportAgent'). Returning all
     * matching versions ensures historical sessions from older deployments are included.
     *
     * Also adds the 15-char version of each ID to handle STDM DMO inconsistency:
     * the participant DMO stores ssot__ParticipantId__c as either 15-char or 18-char.
     *
     * @param agentApiName  MasterLabel of the agent (same as the agent's display name)
     * @return List of GenAiPlannerDefinition Ids in both 15-char and 18-char formats; empty if not found
     */
    private static List<String> resolvePlannerIds(String agentApiName) {
        List<String> ids = new List<String>();
        try {
            // Search by MasterLabel (exact match) OR DeveloperName pattern.
            // Agent Script agents create GenAiPlannerDefinition with DeveloperName
            // like 'OrderService_v1' and MasterLabel like 'Order Service'.
            // Accept the API name (no spaces) and match both patterns.
            String devNamePattern = agentApiName + '_%';
            List<GenAiPlannerDefinition> planners = [
                SELECT Id FROM GenAiPlannerDefinition
                WHERE MasterLabel = :agentApiName
                   OR DeveloperName = :agentApiName
                   OR DeveloperName LIKE :devNamePattern
            ];
            for (GenAiPlannerDefinition p : planners) {
                String id18 = String.valueOf(p.Id);
                ids.add(id18);
                // STDM DMO stores IDs inconsistently (15-char or 18-char) — include both
                if (id18.length() == 18) ids.add(id18.substring(0, 15));
            }
            if (ids.isEmpty()) {
                System.debug(LoggingLevel.WARN, 'No GenAiPlannerDefinition found for: ' + agentApiName);
            } else {
                System.debug(LoggingLevel.DEBUG, 'Resolved ' + planners.size() + ' planner version(s) for agent "'
                    + agentApiName + '": ' + ids);
            }
        } catch (Exception e) {
            System.debug(LoggingLevel.WARN, 'resolvePlannerIds failed for "' + agentApiName + '": ' + e.getMessage());
        }
        return ids;
    }

    /** Extract ssot__AiAgentSessionId__c values (col 0) from a participant DMO query result. */
    private static List<String> extractSessionIds(ConnectApi.CdpQueryOutputV2 partResult) {
        List<String> sessionIds = new List<String>();
        if (partResult != null && partResult.data != null) {
            for (ConnectApi.CdpQueryV2Row row : partResult.data) {
                String sid = col(row.rowData, 0);
                if (sid != null) sessionIds.add(sid);
            }
        }
        return sessionIds;
    }

    private static ConnectApi.CdpQueryOutputV2 runQuery(String sql, String dataSpaceName) {
        System.debug(LoggingLevel.DEBUG, 'AgentforceOptimize CDP query (' + dataSpaceName + '): ' + sql);
        ConnectApi.CdpQueryInput inp = new ConnectApi.CdpQueryInput();
        inp.sql = sql;
        try {
            ConnectApi.CdpQueryOutputV2 result = ConnectApi.CdpQuery.queryAnsiSqlV2(inp, dataSpaceName);
            Integer rowCount = (result != null && result.data != null) ? result.data.size() : 0;
            System.debug(LoggingLevel.DEBUG, 'Rows returned: ' + rowCount);
            return result;
        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR,
                'CDP query failed [' + dataSpaceName + ']: ' + e.getMessage() + ' | SQL: ' + sql);
            return null;
        }
    }

    /** Safely extract a column value as String; returns null for empty/null cells. */
    private static String col(List<Object> row, Integer i) {
        if (row == null || i >= row.size() || row[i] == null) return null;
        return String.valueOf(row[i]);
    }

    /** Return null when the value is the STDM "NOT_SET" sentinel or blank. */
    private static String notSet(String val) {
        if (String.isBlank(val) || val == 'NOT_SET') return null;
        return val;
    }

    /** Compute millisecond duration between two ISO timestamp strings; null on any failure. */
    private static Long durationMs(String startTs, String endTs) {
        if (String.isBlank(startTs) || String.isBlank(endTs)) return null;
        try {
            Datetime startDt = parseTs(startTs);
            Datetime endDt   = parseTs(endTs);
            if (startDt == null || endDt == null) return null;
            return endDt.getTime() - startDt.getTime();
        } catch (Exception e) {
            return null;
        }
    }

    /** Parse an ISO 8601 timestamp string into a Datetime, with fallback strategies. */
    private static Datetime parseTs(String ts) {
        if (String.isBlank(ts)) return null;
        // Strategy 1: ISO 8601 via JSON deserialise
        try {
            return (Datetime) JSON.deserialize('"' + ts + '"', Datetime.class);
        } catch (Exception e1) {
            System.debug(LoggingLevel.FINE, 'parseTs strategy 1 failed for "' + ts + '": ' + e1.getMessage());
        }
        // Strategy 2: Datetime.valueOf (handles 'yyyy-MM-dd HH:mm:ss' format)
        try {
            return Datetime.valueOf(ts);
        } catch (Exception e2) {
            System.debug(LoggingLevel.FINE, 'parseTs strategy 2 failed for "' + ts + '": ' + e2.getMessage());
        }
        // Strategy 3: epoch milliseconds
        try {
            return Datetime.newInstance(Long.valueOf(ts));
        } catch (Exception e3) {
            System.debug(LoggingLevel.FINE, 'parseTs strategy 3 failed for "' + ts + '": ' + e3.getMessage());
        }
        return null;
    }

    // =========================================================================
    // Observability Query (@InvocableMethod for Flow / Agentforce actions)
    // =========================================================================

    public class ObservabilityInput {
        @InvocableVariable(label='Query Type' required=true)
        public String queryType;

        @InvocableVariable(label='Agent API Name' required=false)
        public String agentApiName;

        @InvocableVariable(label='Subagent API Name' required=false)
        public String topicApiName;

        @InvocableVariable(label='Lookback Days' required=false)
        public Integer lookbackDays;
    }

    public class ObservabilityOutput {
        @InvocableVariable(label='Query Result JSON')
        public String resultJson;

        @InvocableVariable(label='Summary Text')
        public String summaryText;
    }

    @InvocableMethod(label='Run Observability Query' description='Executes a Data Cloud observability query based on query type and optional filters.')
    public static List<ObservabilityOutput> runObservabilityQuery(List<ObservabilityInput> inputs) {
        List<ObservabilityOutput> results = new List<ObservabilityOutput>();
        for (ObservabilityInput input : inputs) {
            ObservabilityOutput out = new ObservabilityOutput();
            try {
                String query = buildObservabilityQuery(input);
                ConnectApi.CdpQueryInput cdpInput = new ConnectApi.CdpQueryInput();
                cdpInput.sql = query;
                ConnectApi.CdpQueryOutputV2 cdpOutput = ConnectApi.CdpQuery.queryAnsiSqlV2(cdpInput);

                out.resultJson = JSON.serialize(cdpOutput);
                Integer rowCount = cdpOutput.rowCount != null ? cdpOutput.rowCount : 0;

                if (rowCount == 0) {
                    out.summaryText = 'Query executed for ' + input.queryType + '. No results found for the given filters and time range. SQL: ' + query;
                } else {
                    out.summaryText = 'Query executed for ' + input.queryType + '. Found ' + rowCount + ' result(s). Use the metadata to map column positions to names in the data arrays.';
                }
            } catch (Exception e) {
                out.summaryText = 'Error executing ' + input.queryType + ' query: ' + e.getMessage();
                out.resultJson = '{"error":"' + e.getMessage().replace('"', '\\"') + '"}';
            }
            results.add(out);
        }
        return results;
    }

    private static String buildObservabilityQuery(ObservabilityInput p) {
        Integer days = p.lookbackDays != null ? p.lookbackDays : 90;
        String cutoff = Datetime.now().addDays(-days).formatGmt('yyyy-MM-dd HH:mm:ss.SSS');

        String agentFilter = String.isNotBlank(p.agentApiName)
            ? ' AND sp.aiAgentApiName__c = \'' + String.escapeSingleQuotes(p.agentApiName) + '\'' : '';
        String topicFilter = String.isNotBlank(p.topicApiName)
            ? ' AND i.topicApiName__c = \'' + String.escapeSingleQuotes(p.topicApiName) + '\'' : '';

        if (p.queryType == 'KnowledgeGap') {
            return 'SELECT i.topicApiName__c, sp.aiAgentApiName__c, ' +
                   'AVG(q.ContextPrecisionScoreNumber__c) AS avg_precision, ' +
                   'AVG(q.AnswerRelevancyScoreNumber__c) AS avg_relevancy, ' +
                   'COUNT(*) AS total_interactions ' +
                   'FROM AIRetrieverQualityMetric__dll q ' +
                   'JOIN AIAgentInteraction__dll i ON q.RetrieverTraceId__c = i.telemetryTraceId__c ' +
                   'JOIN AIAgentSessionParticipant__dll sp ON sp.aiAgentSessionId__c = i.aiAgentSessionId__c ' +
                   'WHERE i.startTimestamp__c > \'' + cutoff + '\'' +
                   agentFilter + topicFilter +
                   ' GROUP BY i.topicApiName__c, sp.aiAgentApiName__c ' +
                   'ORDER BY avg_precision ASC LIMIT 25';

        } else if (p.queryType == 'Hallucination') {
            return 'SELECT sp.aiAgentApiName__c, i.topicApiName__c, ' +
                   'AVG(q.FaithfulnessRelevancyScoreNumber__c) AS avg_faithfulness, ' +
                   'COUNT(*) AS total_interactions ' +
                   'FROM AIRetrieverQualityMetric__dll q ' +
                   'JOIN AIAgentInteraction__dll i ON q.RetrieverTraceId__c = i.telemetryTraceId__c ' +
                   'JOIN AIAgentSessionParticipant__dll sp ON sp.aiAgentSessionId__c = i.aiAgentSessionId__c ' +
                   'WHERE i.startTimestamp__c > \'' + cutoff + '\'' +
                   ' AND q.FaithfulnessRelevancyScoreNumber__c < 0.8' +
                   agentFilter + topicFilter +
                   ' GROUP BY sp.aiAgentApiName__c, i.topicApiName__c ' +
                   'ORDER BY avg_faithfulness ASC LIMIT 25';

        } else if (p.queryType == 'RetrievalQuality') {
            return 'SELECT q.RetrieverApiName__c, i.topicApiName__c, sp.aiAgentApiName__c, ' +
                   'AVG(q.ContextPrecisionScoreNumber__c) AS avg_precision, COUNT(*) AS total ' +
                   'FROM AIRetrieverQualityMetric__dll q ' +
                   'JOIN AIAgentInteraction__dll i ON q.RetrieverTraceId__c = i.telemetryTraceId__c ' +
                   'JOIN AIAgentSessionParticipant__dll sp ON sp.aiAgentSessionId__c = i.aiAgentSessionId__c ' +
                   'WHERE i.startTimestamp__c > \'' + cutoff + '\'' +
                   agentFilter + topicFilter +
                   ' GROUP BY q.RetrieverApiName__c, i.topicApiName__c, sp.aiAgentApiName__c ' +
                   'ORDER BY avg_precision ASC LIMIT 25';

        } else if (p.queryType == 'AnswerRelevancy') {
            return 'SELECT sp.aiAgentApiName__c, i.topicApiName__c, ' +
                   'AVG(q.AnswerRelevancyScoreNumber__c) AS avg_relevancy, COUNT(*) AS total ' +
                   'FROM AIRetrieverQualityMetric__dll q ' +
                   'JOIN AIAgentInteraction__dll i ON q.RetrieverTraceId__c = i.telemetryTraceId__c ' +
                   'JOIN AIAgentSessionParticipant__dll sp ON sp.aiAgentSessionId__c = i.aiAgentSessionId__c ' +
                   'WHERE i.startTimestamp__c > \'' + cutoff + '\'' +
                   ' AND q.AnswerRelevancyScoreNumber__c < 0.7' +
                   agentFilter + topicFilter +
                   ' GROUP BY sp.aiAgentApiName__c, i.topicApiName__c ' +
                   'ORDER BY avg_relevancy ASC LIMIT 25';

        } else if (p.queryType == 'Leaderboard') {
            return 'SELECT sp.aiAgentApiName__c, i.topicApiName__c, ' +
                   'AVG(q.ContextPrecisionScoreNumber__c) AS avg_precision, ' +
                   'AVG(q.AnswerRelevancyScoreNumber__c) AS avg_relevancy, ' +
                   'AVG(q.FaithfulnessRelevancyScoreNumber__c) AS avg_faithfulness, ' +
                   'COUNT(*) AS total_interactions ' +
                   'FROM AIRetrieverQualityMetric__dll q ' +
                   'JOIN AIAgentInteraction__dll i ON q.RetrieverTraceId__c = i.telemetryTraceId__c ' +
                   'JOIN AIAgentSessionParticipant__dll sp ON sp.aiAgentSessionId__c = i.aiAgentSessionId__c ' +
                   'WHERE i.startTimestamp__c > \'' + cutoff + '\'' +
                   agentFilter + topicFilter +
                   ' GROUP BY sp.aiAgentApiName__c, i.topicApiName__c ' +
                   'ORDER BY avg_precision ASC LIMIT 25';
        }
        return 'SELECT COUNT(*) AS cnt FROM AIAgentSession__dll';
    }
}
