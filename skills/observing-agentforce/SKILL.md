---
name: observing-agentforce
description: "Analyze production Agentforce agent behavior using session traces and Data Cloud. TRIGGER when: user queries STDM session data or Data Cloud trace records; investigates production agent failures, regressions, or performance issues; asks about session traces, conversation logs, or agent metrics; wants to reproduce a reported production issue in preview; runs findSessions or trace analysis queries. DO NOT TRIGGER when: user creates, modifies, or debugs .agent files during development (use developing-agentforce); writes or runs test specs (use testing-agentforce); uses sf agent preview for local development iteration; deploys or publishes agents."
allowed-tools: Bash Read Write Edit Glob Grep
license: Apache-2.0
metadata:
  version: "0.5.1"
  last_updated: "2026-04-08"
  argument-hint: "<org-alias> [--agent-file <path>] [--session-id <id>] [--days <n>]"
  compatibility: claude-code
---


# Agentforce Observability

Improve Agentforce agents using session trace data and live preview testing.

**Three-phase workflow:**
- **Observe** -- Query STDM sessions from Data Cloud (if available), OR run test suites + preview with local traces as fallback
- **Reproduce** -- Use `sf agent preview` to simulate problematic conversations live
- **Improve** -- Edit the `.agent` file directly, validate, publish, verify

---

## Platform Notes

- Shell examples below use bash syntax. On Windows, use PowerShell equivalents or Git Bash.
- Replace `python3` with `python` on Windows.
- Replace `/tmp/` with `$env:TEMP\` (PowerShell) or `%TEMP%\` (cmd).
- Replace `jq` with `python -c "import json,sys; ..."` if jq is not installed.

---

## Routing

Gather these inputs before starting:

- **Org alias** (required)
- **Agent API name** (required for preview and deploy; ask if not provided)
- **Agent file path** (optional) -- path to the `.agent` file, typically `force-app/main/default/aiAuthoringBundles/<AgentName>/<AgentName>.agent`. Auto-detect if not provided.
- **Session IDs** (optional) -- analyze specific sessions; if absent, query last 7 days
- **Days to look back** (optional, default 7)

Determine intent from user input:

- **No specific action** -> run all three phases: Observe -> surface issues -> ask if user wants to Reproduce and/or Improve
- **"analyze" / "sessions" / "what's wrong"** -> Phase 1 only, then suggest next steps
- **"reproduce" / "test" / "preview"** -> Phase 2 (run Phase 1 first if no issues in hand)
- **"fix" / "improve" / "update"** -> Phase 3 (run Phase 1 first if no issues in hand)

### Resolve agent name

Before any STDM query, resolve the user-provided agent name against the org to get the exact `MasterLabel` and `DeveloperName`:

```bash
sf data query --json \
  --query "SELECT Id, MasterLabel, DeveloperName FROM GenAiPlannerDefinition WHERE MasterLabel LIKE '%<user-provided-name>%' OR DeveloperName LIKE '%<user-provided-name>%'" \
  -o <org>
```

- `MasterLabel` = display name used by STDM `findSessions` and Agent Builder UI (e.g. "Order Service")
- `DeveloperName` = API name with version suffix used in metadata (e.g. "OrderService_v9")
- The `--api-name` flag for `sf agent preview/activate/publish` uses `DeveloperName` **without** the `_vN` suffix (e.g. "OrderService")

Store these values:
- `AGENT_MASTER_LABEL` -- for `findSessions()` agent filter
- `AGENT_API_NAME` -- `DeveloperName` without `_vN` suffix, for `sf agent` CLI commands
- `PLANNER_ID` -- the Salesforce record ID for this agent

### Locate the .agent file

**Step 1 -- Search locally:**

```bash
find <project-root>/force-app/main/default/aiAuthoringBundles -name "*.agent" 2>/dev/null
```

If the user provided an agent file path, use that directly. Otherwise, search for files matching `AGENT_API_NAME`.

**Step 2 -- If not found locally, retrieve from the org:**

```bash
sf project retrieve start --json --metadata "AiAuthoringBundle:<AGENT_API_NAME>" -o <org>
```

> **Known bug:** `sf project retrieve start` creates a double-nested path: `force-app/main/default/main/default/aiAuthoringBundles/...`. Fix it immediately after retrieve:

```bash
if [ -d "force-app/main/default/main/default/aiAuthoringBundles" ]; then
  mkdir -p force-app/main/default/aiAuthoringBundles
  cp -r force-app/main/default/main/default/aiAuthoringBundles/* \
    force-app/main/default/aiAuthoringBundles/
  rm -rf force-app/main/default/main
fi
```

**Step 3 -- Validate the retrieved file:**

Read the `.agent` file and verify it has proper Agent Script structure:
- `system:` block with `instructions:`
- `config:` block with `developer_name:`
- `start_agent` or `subagent` blocks with `reasoning: instructions:`
- Each subagent should have distinct `instructions:` content (not identical across subagents)

Store the resolved path as `AGENT_FILE` for Phase 3.

---

## Phase 0: Discover Data Space

Before running any STDM query, determine the correct Data Cloud Data Space API name.

```bash
sf api request rest "/services/data/v63.0/ssot/data-spaces" -o <org>
```

Note: `sf api request rest` is a beta command -- do not add `--json` (that flag is unsupported and causes an error).

The response shape is:
```json
{
  "dataSpaces": [
    {
      "id": "0vhKh000000g3DjIAI",
      "label": "default",
      "name": "default",
      "status": "Active",
      "description": "Your org's default data space."
    }
  ],
  "totalSize": 1
}
```

The `name` field is the API name to pass to `AgentforceOptimizeService`.

**Decision logic:**
- If the command fails (e.g. 404 or permission error), fall back to `'default'` and note it as an assumption.
- Filter to only `status: "Active"` entries.
- If exactly one active Data Space exists, use it automatically and confirm to the user: "Using Data Space: `<name>`".
- If multiple active Data Spaces exist, show the list (label + name) and ask the user which to use.

Store the selected `name` value as `DATA_SPACE` for all subsequent steps.

### Prerequisite check: STDM DMOs

After deploying the helper class (step 1.0), run a quick probe to verify the STDM Data Model Objects exist in Data Cloud:

```bash
sf apex run -o <org> -f /dev/stdin << 'APEX'
ConnectApi.CdpQueryInput qi = new ConnectApi.CdpQueryInput();
qi.sql = 'SELECT ssot__Id__c FROM "ssot__AiAgentSession__dlm" LIMIT 1';
try {
    ConnectApi.CdpQueryOutputV2 out = ConnectApi.CdpQuery.queryAnsiSqlV2(qi, '<DATA_SPACE>');
    System.debug('STDM_CHECK:OK rows=' + (out.data != null ? out.data.size() : 0));
} catch (Exception e) {
    System.debug('STDM_CHECK:FAIL ' + e.getMessage());
}
APEX
```

**If `STDM_CHECK:FAIL`:** STDM is not activated. Inform the user and switch to **Phase 1-ALT**:

> STDM (Session Trace Data Model) is not available in this org. To enable: Setup -> Data Cloud -> Data Streams and verify "Agentforce Activity" is active. **Proceeding with fallback: test suites + local traces.**

**If `STDM_CHECK:OK`**, proceed to Phase 1 (STDM path).

---

## Phase 1-ALT: Observe Without STDM (Fallback Path)

When STDM is not available, use test suites and `sf agent preview --authoring-bundle` with local trace analysis.

| Data source | When to use | Pros | Cons |
|---|---|---|---|
| STDM (Phase 1) | Historical production analysis | Real user data, volume | Requires Data Cloud, 15-min lag |
| Test suites + local traces (Phase 1-ALT) | Dev iteration, orgs without STDM | Instant, full LLM prompt, variable state | Preview only, no real user data |

### 1-ALT.1 Run existing test suite (if available)

```bash
sf agent test list --json -o <org>
sf agent test run --json --api-name <TestSuiteName> --wait 10 --result-format json -o <org> | tee /tmp/test_run.json
JOB_ID=$(python3 -c "import json; print(json.load(open('/tmp/test_run.json'))['result']['runId'])")
sf agent test results --json --job-id "$JOB_ID" --result-format json -o <org>
```

### 1-ALT.2 Derive test utterances from .agent file (if no test suite)

If no test suite exists, derive utterances: one per non-entry subagent (from `description:` keywords), one per key action, one guardrail test, one multi-turn test.

### 1-ALT.3 Preview with `--authoring-bundle` (local traces)

Run each test utterance through preview to generate local trace files:

```bash
sf agent preview start --json --authoring-bundle <BundleName> -o <org> | tee /tmp/preview_start.json
SESSION_ID=$(python3 -c "import json; print(json.load(open('/tmp/preview_start.json'))['result']['sessionId'])")

sf agent preview send --json --session-id "$SESSION_ID" --authoring-bundle <BundleName> \
  --utterance "$UTT" -o <org> | tee /tmp/preview_response.json

sf agent preview end --json --session-id "$SESSION_ID" --authoring-bundle <BundleName> -o <org>
```

**Trace file location:** `.sfdx/agents/{BundleName}/sessions/{sessionId}/traces/{planId}.json`

### 1-ALT.4 Local trace diagnosis

| Issue type | Trace command |
|---|---|
| Subagent misroute | `jq -r '.plan[] \| select(.type=="NodeEntryStateStep") \| .data.agent_name' "$TRACE"` |
| Action not called | `jq -r '.plan[] \| select(.type=="EnabledToolsStep") \| .data.enabled_tools[]' "$TRACE"` |
| LOW adherence | `jq -r '.plan[] \| select(.type=="ReasoningStep") \| {category, reason}' "$TRACE"` |
| Variable capture fail | `jq -r '.plan[] \| select(.type=="VariableUpdateStep") \| .data.variable_updates[]' "$TRACE"` |
| Vague instructions | `jq -r '.plan[] \| select(.type=="LLMStep") \| .data.messages_sent[0].content' "$TRACE"` |

**DefaultTopic trace quirk:** With `--authoring-bundle`, the root `.topic` field often shows `"DefaultTopic"` even when routing works. Always use `NodeEntryStateStep.data.agent_name` for the real subagent chain.

**Entry answering directly (SMALL_TALK pattern):** If `start_agent` trace shows `SMALL_TALK` grounding and transition tools visible but none invoked, add "You are a router only. Do NOT answer questions directly." to `start_agent` instructions.

### 1-ALT.5 Classify and present

Classify issues using the categories in `references/issue-classification.md`. After presenting findings, automatically proceed to agent config evidence analysis.

---

## Phase 1: Observe -- Query STDM

> Full STDM query details, Apex service deployment, and response parsing: see `references/stdm-queries.md`

### 1.0 Deploy helper class (once per org)

Deploy `AgentforceOptimizeService` Apex class to the org. Check if already deployed first:

```bash
sf data query --json --query "SELECT Id, Name FROM ApexClass WHERE Name = 'AgentforceOptimizeService'" -o <org>
```

If not deployed, copy from skill directory and deploy. See `references/stdm-queries.md` for full steps.

### 1.1 Find sessions

Query recent sessions using `findSessions()`. Parse `DEBUG|STDM_RESULT:` from the Apex debug log. If `findSessions` returns empty, switch to Phase 1-ALT.

### 1.2 Get conversation details

Use `getMultipleConversationDetails()` for up to 5 sessions (most recent first). Returns turn-by-turn data with messages, steps, topics, and action results.

### 1.2b Get LLM prompt/response (optional)

When LOW adherence detected, use `getLlmStepDetails()` to get the actual LLM prompt and response.

### 1.2c Get aggregated metrics (recommended first step)

Use `getAggregatedMetrics()` for high-level health dashboard: session rates, top intents, quality distribution, RAG averages.

### 1.2d Get moment insights (per-session detail)

Use `getMomentInsights()` for intent summaries, quality scores (1-5), and retriever metrics per session.

### 1.2e Run observability queries (RAG deep-dive)

Use `runObservabilityQuery()` for targeted RAG analysis: KnowledgeGap, Hallucination, RetrievalQuality, AnswerRelevancy, Leaderboard.

### 1.3 Reconstruct conversations

Render turn-by-turn timeline from `ConversationData` JSON for each session.

### 1.4 Identify issues

> Full issue pattern table and classification categories: see `references/issue-classification.md`

Check each session for: action errors, subagent misroutes, missing actions, wrong inputs, variable capture failures, no transitions, slow actions, LOW adherence, abandoned sessions, dead subagents, publish drift, dead hub anti-pattern, entry answering directly, and safety issues.

Priority: P1 = action errors, misroutes, LOW adherence; P2 = missing actions, variable bugs, knowledge gaps; P3 = performance, abandoned sessions.

### 1.5 Present findings and agent config evidence

Present sessions analyzed, issues grouped by root cause category, and uplift estimate. Then automatically proceed to analyze the `.agent` file to confirm root causes.

> Full structural analysis checks, cross-reference procedures, and publish drift detection: see `references/issue-classification.md`

Retrieve the `.agent` file from the org, run automated checks (subagent count vs action blocks, dead hub detection, orphan actions, cross-subagent variable dependencies), and cross-reference STDM symptoms against the file structure.

---

## Phase 2: Reproduce -- Live Preview

> Full preview procedures, trace diagnosis commands, and classification criteria: see `references/reproduce-reference.md`

Build one test scenario per confirmed issue from Phase 1. Run each through `sf agent preview` with `--authoring-bundle` (generates local traces). Run each scenario **3 times** and classify:

| Verdict | Criteria |
|---|---|
| `[CONFIRMED]` | Same failure in 3/3 runs |
| `[INTERMITTENT]` | Failure in 1-2 of 3 runs |
| `[NOT REPRODUCED]` | Passes in 3/3 runs |

Only `[CONFIRMED]` and `[INTERMITTENT]` issues proceed to Phase 3.

**Key commands:**

```bash
sf agent preview start --json --authoring-bundle <Name> -o <org>
sf agent preview send --json --session-id "$SID" --utterance "<text>" --authoring-bundle <Name> -o <org>
sf agent preview end --json --session-id "$SID" --authoring-bundle <Name> -o <org>
```

**Trace location:** `.sfdx/agents/{Name}/sessions/{sessionId}/traces/{planId}.json`

---

## Phase 3: Improve -- Edit .agent File Directly

> Full procedures for pre-flight checks, fix mapping, instruction principles, regression prevention, deployment chain, verification, safety re-verification, and test case creation: see `references/improve-reference.md`

### 3.0 Pre-flight

Verify all action targets exist and are registered in the org before editing. If targets are missing, present options: deploy stubs, remove actions, register via UI, or proceed with routing-only fixes.

### 3.1-3.3 Map issue, edit, and follow instruction principles

Map each confirmed issue to a fix location in the `.agent` file (description, instructions, actions, bindings, transitions). Use the Edit tool for targeted changes. Follow instruction principles: name actions explicitly, state pre-conditions, scope tightly, keep persona in `system:` only.

### 3.4 Regression prevention

Establish baseline before editing. Make minimal edits. Test immediately after each edit. One fix per publish cycle. Check cross-subagent dependencies. Test adjacent subagents.

### 3.5 Apply fixes

Read the `.agent` file, edit with the Edit tool (tabs for indentation), show the diff.

### 3.6 Validate, deploy, publish, activate

```bash
# Validate (dry run)
sf agent validate authoring-bundle --json --api-name <AGENT_API_NAME> -o <org>

# Publish (compile + deploy + activate)
sf agent publish authoring-bundle --json --api-name <AGENT_API_NAME> -o <org>
```

If publish fails, use deploy + activate fallback (note: incomplete -- does not propagate `reasoning: actions:` to live metadata).

### 3.7 Verify

Run Phase 2 scenarios post-fix. Check trace for correct routing, grounding, tools, and variables. After 24-48 hours, re-run Phase 1 to compare against baseline.

### 3.7b Safety re-verification (required)

Re-run safety review (`Section 15 of /developing-agentforce`) on the modified `.agent` file. Revert any changes that introduce BLOCK findings.

### 3.8 Update Testing Center test cases

Create regression test cases from confirmed issues in Testing Center YAML format. Deploy with `sf agent test create` and verify all previously-broken scenarios pass.

---

## Reference Files

| Reference | Contents |
|---|---|
| `references/stdm-queries.md` | STDM query procedures, Apex service deployment, response parsing |
| `references/issue-classification.md` | Issue pattern table, root cause categories, structural analysis checks |
| `references/reproduce-reference.md` | Phase 2 preview procedures, trace diagnosis, classification criteria |
| `references/improve-reference.md` | Phase 3 editing, deployment chain, verification, safety, test cases |
| `references/stdm-schema.md` | DMO field schemas, data hierarchy, quality notes, agent name resolution |
