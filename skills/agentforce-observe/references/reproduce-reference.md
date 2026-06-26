# Phase 2: Reproduce -- Live Preview (Full Reference)

Use `sf agent preview` to simulate conversations in an isolated session (no production data affected).

---

## Build Test Scenarios from Phase 1 Findings

Before opening a preview session, define one test scenario per confirmed issue:

| Issue type (Phase 1) | Test message to send | Expected behavior | Failure indicator |
|---|---|---|---|
| Dead subagent -- never entered | Utterance that *should* route to that subagent | `subagent` in response = `<dead_subagent>` | Subagent stays `entry` |
| Action not called | Ask directly for the action's task | Action fires in the response | Conversational reply with no action invoked |
| Handoff subagent -- no post-collection routing | Enter the handoff subagent, then send a follow-up | Session continues in specialized subagent | Falls back to `entry` after 1 turn |
| LOW adherence | Exact utterance from the flagged `TRUST_GUARDRAILS_STEP` | Response follows subagent instruction | Generic/off-instruction answer |
| Knowledge miss | Question requiring a specific knowledge article | Agent cites correct information | Hallucinated or generic answer |
| Subagent misroute | Utterance that belongs to subagent A | `subagent` = A in response | `subagent` = B or `entry` |

---

## Run a Preview Session

Use `--authoring-bundle` to compile from the local `.agent` file and generate local trace files:

| Flag | Compiles from | Local traces? | Use when |
|------|---------------|---------------|----------|
| `--authoring-bundle <BundleName>` | Local `.agent` file | YES | Development iteration (recommended) |
| `--api-name <name>` | Last published version | NO | Testing activated agent |

> **Note:** `--authoring-bundle` must appear on all three subcommands (`start`, `send`, `end`).

```bash
# Start a preview session (--authoring-bundle enables local traces)
sf agent preview start --json \
  --authoring-bundle <AgentApiName> \
  -o <org> | tee /tmp/preview_start.json

# Extract the session ID
SESSION_ID=$(python3 -c "import json,sys; print(json.load(open('/tmp/preview_start.json'))['result']['sessionId'])")
echo "Session ID: $SESSION_ID"

# Send the test utterance (flag is --utterance, not --message)
sf agent preview send --json \
  --session-id "$SESSION_ID" \
  --utterance "your test utterance here" \
  --authoring-bundle <AgentApiName> \
  -o <org> | tee /tmp/preview_response.json

# Extract the agent's response text
# The message type is "Inform" in current API versions -- print all messages regardless of type
python3 -c "
import json
data = json.load(open('/tmp/preview_response.json'))
result = data.get('result', data)
# Response field varies by API version -- try common shapes
for key in ['messages', 'message', 'response']:
    if key in result:
        msgs = result[key] if isinstance(result[key], list) else [result[key]]
        for m in msgs:
            if isinstance(m, dict):
                msg_type = m.get('type', '?')
                msg_text = m.get('message', m.get('text', m))
                print(f'Agent [{msg_type}]: {msg_text}')
        break
else:
    print(json.dumps(result, indent=2))  # fallback: print full result
"

# End the session when done (--authoring-bundle required on end too)
sf agent preview end --json \
  --session-id "$SESSION_ID" \
  --authoring-bundle <AgentApiName> \
  -o <org>
```

**Trace file location:**
```
.sfdx/agents/{AgentApiName}/sessions/{sessionId}/traces/{planId}.json
```

For multi-turn scenarios (e.g. handoff routing), repeat the `send` step for each follow-up utterance before ending the session.

---

## Local Trace Diagnosis

For each Phase 1 issue type, diagnose from the local trace:

| Phase 1 Issue | Local Trace Command |
|---|---|
| Subagent misroute | `jq -r '.topic' "$TRACE"` + `jq -r '.plan[] \| select(.type=="NodeEntryStateStep") \| .data.agent_name' "$TRACE"` |
| Action not called | `jq -r '.plan[] \| select(.type=="EnabledToolsStep") \| .data.enabled_tools[]' "$TRACE"` |
| LOW adherence | `jq -r '.plan[] \| select(.type=="ReasoningStep") \| {category, reason}' "$TRACE"` |
| Variable capture fail | `jq -r '.plan[] \| select(.type=="VariableUpdateStep") \| .data.variable_updates[] \| "\(.variable_name): \(.variable_past_value) -> \(.variable_new_value) (\(.variable_change_reason))"' "$TRACE"` |
| Vague/wrong instructions | `jq -r '.plan[] \| select(.type=="LLMStep") \| .data.messages_sent[0].content' "$TRACE"` |

**UNGROUNDED retry detection:** When grounding returns UNGROUNDED, you'll see the retry pattern: UNGROUNDED -> error injection -> second LLMStep -> second ReasoningStep. Count `ReasoningStep` entries (>1 = retry happened):
```bash
jq '[.plan[] | select(.type == "ReasoningStep")] | length' "$TRACE"
```

---

## Classify Each Scenario

Run each test scenario **3 times** (start a new session each run) and classify:

| Verdict | Criteria |
|---|---|
| `[CONFIRMED]` | Same failure in 3/3 runs |
| `[INTERMITTENT]` | Failure in 1-2 of 3 runs |
| `[NOT REPRODUCED]` | Passes in 3/3 runs -- re-examine Phase 1 evidence |

---

## Record Results

For each scenario, record before proceeding to Phase 3:

```
Scenario: <issue type from Phase 1>
Test message: "<exact utterance sent>"
Expected: <subagent name / action name / response behavior>
Actual:   <observed subagent / action / verbatim response>
Verdict:  [CONFIRMED] / [INTERMITTENT] / [NOT REPRODUCED]
```

Only `[CONFIRMED]` and `[INTERMITTENT]` issues proceed to Phase 3.

For `[NOT REPRODUCED]` issues: re-examine the Phase 1 STDM evidence. The session data may be stale (issue was already fixed), the utterance may not match the original user input closely enough, or the issue may be environment-dependent. Report these to the user as "not reproducible" and move on -- do not attempt fixes for issues that cannot be confirmed.
