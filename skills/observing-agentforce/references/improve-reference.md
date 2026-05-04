# Phase 3: Improve -- Edit .agent File (Full Reference)

Phase 3 edits the `.agent` file directly using the Edit tool. No intermediate markdown conversion step. After editing, validate and publish the authoring bundle.

---

## Pre-Flight: Verify Action Target Availability

Before making any `.agent` file edits, verify that all action targets actually exist and are registered in the org.

**Step 1 -- Extract all action targets from the `.agent` file:**

```bash
AGENT_FILE="<path_to_agent_file>"
grep -oP 'target:\s*"\K[^"]+' "$AGENT_FILE" | sort -u
```

**Step 2 -- Query GenAiFunction records in the org:**

```bash
sf data query --json -q "SELECT DeveloperName, MasterLabel, InvocableActionDeveloperName FROM GenAiFunction WHERE IsActive = true" -o <ORG_ALIAS>
```

**Step 3 -- Compare and flag missing targets:**

```bash
# For flow:// targets
sf flow list -o <ORG_ALIAS> --json | python3 -c "import json,sys; flows=[f['ApiName'] for f in json.load(sys.stdin)['result']]; print('\n'.join(flows))"

# For apex:// targets
sf data query --json -q "SELECT Name FROM ApexClass WHERE Name IN ('ClassName1','ClassName2')" -o <ORG_ALIAS>
```

**Step 4 -- Present options to user if targets are missing:**

1. **Deploy missing targets first** -- Use `Section 17 of /developing-agentforce` to generate stubs, then `Section 18 of /developing-agentforce` to deploy
2. **Remove unresolvable actions** -- Delete from `.agent` file and focus on routing/instruction improvements
3. **Register via Agent Builder UI** -- For targets that exist but aren't registered as `GenAiFunction`
4. **Proceed anyway** -- If the planned fix only touches routing logic or instructions

**Guideline:** If 50%+ of action targets are missing or unregistered, pivoting to routing and instruction fixes is usually the most pragmatic path.

**WARNING:** Do NOT use `flow://` syntax directly in `.agent` file action `target:` URIs as a workaround -- the Agent Script lexer does not support URI prefixes in target fields.

---

## .agent File Structure

The `.agent` file uses Agent Script -- a tab-indented DSL that compiles to Agentforce metadata:

```
system:
    instructions: "Agent-level system prompt (persona, guardrails)"
    messages:
        welcome: "Welcome message"
        error: "Error fallback message"

config:
    agent_name: "AgentApiName"
    agent_label: "Agent Display Name"
    description: "Agent description"
    default_agent_user: "user@org.com"

variables:
    myVar: mutable string
        description: "Variable description"
        default: ""

start_agent: entry_topic

subagent entry_topic:
    label: "Entry Subagent"
    description: "Routes users to specialized subagents"

    reasoning:
        instructions: ->
            | Welcome the user warmly.
            | Ask how you can help today.
        actions:
            go_to_orders: @utils.transition to @subagent.orders
                description: "Route to orders subagent"
            check_order: @actions.get_order_status
                description: "Look up order details"
                with order_id = @variables.order_id
                set @variables.order_status = @outputs.status
```

**Critical mapping to Salesforce metadata:**
- `subagent.description` -> `GenAiPluginDefinition.Description` (subagent routing signal)
- `subagent.reasoning.instructions` -> `GenAiPluginInstructionDef.Instruction` (verbatim LLM prompt text)
- `system.instructions` -> `GenAiPlannerDefinition.Description` (agent-level system prompt)
- `reasoning.actions` with `@utils.transition` -> subagent transitions
- `reasoning.actions` with `@actions.*` -> action invocations with `with` (input) and `set` (output) bindings

---

## Map Issue to Fix Location

| Root cause category | STDM signal | Fix target in .agent file | What to change |
|---|---|---|---|
| `Agent Configuration Gap` | Subagent misroute | `subagent <name>: description:` | Tighten description to exclude overlapping intents |
| `Agent Configuration Gap` | Action not called | `subagent <name>: reasoning: actions:` and `reasoning: instructions:` | Add action definition under `actions:` and mention it in `instructions:` |
| `Agent Configuration Gap` | Wrong action input / error | `reasoning: actions: <action>: with` | Correct `with` bindings or action `target:` URI |
| `Agent Configuration Gap` | Variable not captured | `reasoning: actions: <action>: set` | Add `set @variables.myVar = @outputs.field` binding |
| `Agent Configuration Gap` | No post-action transition | `reasoning: actions:` | Add `@utils.transition to @subagent.<next_subagent>` action |
| `Agent Configuration Gap` | LOW adherence / vague instructions | `subagent <name>: reasoning: instructions:` | Rewrite using instruction principles below |
| `Agent Configuration Gap` | Identical instructions across subagents | All `subagent: reasoning: instructions:` blocks | Give each subagent distinct, actionable instructions |
| `Knowledge Gap -- Infrastructure` | Knowledge question answered generically | Add knowledge action definition to the relevant subagent | Define action with `retriever://` target |
| `Knowledge Gap -- Content` | Knowledge question -- wrong/missing answer | N/A (org data issue) | Add missing articles to knowledge space |
| `Platform / Runtime Issue` | Action timeout / latency > 10s | Flow or Apex class (not .agent) | Optimize query/processing logic |
| `Agent Configuration Gap` | Dead hub anti-pattern | Entire intermediate subagent block | Move transitions to `start_agent > reasoning > actions:`, delete dead hub subagent |

**Target resolution checklist:**

| Target exists? | Registered as GenAiFunction? | Action |
|---|---|---|
| Yes | Yes | Issue is elsewhere (check action bindings, instructions) |
| Yes | No | Deploy/register: use `Section 18 of /developing-agentforce` or register via Agent Builder UI |
| No | N/A | Scaffold first: use `Section 17 of /developing-agentforce` to generate stub, then deploy |
| Can't deploy now | N/A | Pivot to routing fixes: remove action from `.agent`, focus on instructions and transitions |

---

## Principles for Effective Subagent Instructions

Good instructions are specific, imperative, and action-named. Poor instructions are persona descriptions or generic guidance reused across subagents.

1. **Name the action explicitly** -- "Use `@actions.schedule_test_drive` to book the appointment" not "help the user book"
2. **State the pre-condition** -- "Only handle scheduling after the customer's name and email have been collected"
3. **State what to do after** -- "After scheduling completes, confirm the date/time and transition to follow_up"
4. **Scope tightly** -- "This subagent handles test drive scheduling only. For vehicle specs or pricing, do not answer -- the user should be routed to general_support"
5. **Keep persona out of instructions** -- persona belongs in `system: instructions:` (agent-level), not per-subagent reasoning instructions
6. **One responsibility per subagent** -- if the instruction covers 3 distinct tasks, split into 3 subagents

**Before / after example** (identical instructions -> distinct instructions):

*Before (generic persona text, same across all subagents):*
```
reasoning:
    instructions: |
        You are Nova, a friendly Tesla support assistant. Greet customers warmly,
        help them with their needs, and guide them toward scheduling a test drive.
```

*After (for `identity_collection` subagent specifically):*
```
reasoning:
    instructions: ->
        | Collect the customer's name, email address, and phone number using @actions.collect_customer_info.
        | Do not proceed until all three fields are provided.
        | After collection, confirm the details back to the customer.
    actions:
        collect_info: @actions.collect_customer_info
            description: "Capture customer contact details"
            set @variables.customer_name = @outputs.name
            set @variables.customer_email = @outputs.email
        proceed: @utils.transition to @subagent.schedule_test_drive
            description: "Move to test drive scheduling after info collected"
            available when @variables.customer_name != ""
```

---

## Regression Prevention

When editing subagent instructions, follow these principles:

1. **Establish a baseline BEFORE editing** -- Run the test utterance 3 times before making changes. Record the pass rate.

2. **Make minimal, targeted edits** -- Change only the specific instruction line that addresses the identified issue. Do NOT expand terse instructions into verbose ones unless the terse version was causing a specific documented failure.

3. **Avoid instruction expansion** -- Adding more text to instructions does NOT always help. Prefer:
   - Adding a single action reference: "Use `@actions.X` to look up..."
   - Adding a single constraint: "Do not proceed until the customer provides..."
   - Adding a single routing directive: "After completing, transition to @subagent.Y"

4. **Test immediately after each edit** -- Run the same test utterances. If pass rate drops, revert the change immediately.

5. **One fix per publish cycle** -- Do not batch multiple instruction changes into a single publish.

6. **Check cross-subagent dependencies before editing** -- Before changing Subagent A, identify variable dependencies, transition chains, and shared variable mutations:
   ```bash
   grep -n 'set @variables\.' "$AGENT_FILE"
   grep -n 'with .* = @variables\.' "$AGENT_FILE"
   grep -n '@utils.transition to @subagent\.' "$AGENT_FILE"
   ```

7. **Test adjacent subagents after each fix** -- Include at least one cross-subagent test to confirm the fix didn't cause spillover routing.

8. **Verify start_agent routing after subagent removal** -- If removing a dead hub or merging subagents, verify `start_agent > reasoning > actions:` still has transition actions to all remaining subagents.

---

## Apply Fixes

**Step 1 -- Read the current .agent file** using the Read tool. Locate the specific `subagent` block that needs changes.

**Step 2 -- Edit the .agent file directly** using the Edit tool. Edit only the specific lines that need to change. Common edit patterns:

- **Subagent description** (for misroute fixes): Change `description:` text
- **Subagent instructions** (for LOW adherence): Replace `reasoning: instructions:` block
- **Adding an action**: Add definition under `reasoning: actions:`
- **Adding a transition**: Add `@utils.transition to @subagent.<name>` action
- **Adding an `available when` guard**: Add guard condition to action definition

IMPORTANT: Agent Script uses **tabs** for indentation, not spaces.

**Step 3 -- Show the diff:**
```bash
cd <project-root> && git diff <AGENT_FILE>
```

---

## Validate, Deploy, Publish, and Activate

After editing the `.agent` file, use this deployment chain. **Never update `GenAiPluginInstructionDef` or other agent metadata directly** -- always edit the `.agent` file and re-deploy.

```bash
# Step 1: Validate (dry run)
sf agent validate authoring-bundle --json --api-name <AGENT_API_NAME> -o <org>
```

If validation fails: fix syntax errors, deploy missing targets, or resolve duplicate names.

```bash
# Step 2: Publish (compiles, deploys metadata, and activates)
sf agent publish authoring-bundle --json --api-name <AGENT_API_NAME> -o <org>
```

**If publish fails**, use the deploy + activate fallback:

```bash
# Step 3a: Deploy the bundle
sf project deploy start --json --metadata "AiAuthoringBundle:<AGENT_API_NAME>" -o <org>

# Step 3b: Activate
sf agent activate --json --api-name <AGENT_API_NAME> -o <org>
```

> **Warning: deploy + activate is an incomplete fallback.** `sf project deploy start` stores the bundle metadata but does **NOT** propagate subagent-level `reasoning: actions:` blocks to live `GenAiPluginDefinition` records. Always verify with `--authoring-bundle` preview.

**Never use the Tooling API to patch `GenAiPluginInstructionDef` or other BPO objects directly.**

---

## Verify

**Immediate** -- run the Phase 2 scenarios that returned `[CONFIRMED]` before the fix. All should now return `[NOT REPRODUCED]`. Use `--authoring-bundle` to get trace-level verification:

```bash
sf agent preview start --json --authoring-bundle <BundleName> -o <org> | tee /tmp/verify_start.json
SESSION_ID=$(python3 -c "import json; print(json.load(open('/tmp/verify_start.json'))['result']['sessionId'])")

sf agent preview send --json \
  --session-id "$SESSION_ID" \
  --utterance "<test utterance from Phase 2 scenario>" \
  --authoring-bundle <BundleName> \
  -o <org> | tee /tmp/verify_response.json

PLAN_ID=$(python3 -c "import json; d=json.load(open('/tmp/verify_response.json')); print(d['result']['messages'][-1]['planId'])")
TRACE=".sfdx/agents/<BundleName>/sessions/$SESSION_ID/traces/$PLAN_ID.json"

sf agent preview end --json --session-id "$SESSION_ID" --authoring-bundle <BundleName> -o <org>
```

**Trace-based verification checklist:**
```bash
# 1. Correct subagent routing
jq -r '.topic' "$TRACE"
# 2. Grounding passed (no UNGROUNDED)
jq -r '.plan[] | select(.type == "ReasoningStep") | .category' "$TRACE"
# 3. No UNGROUNDED retries (count should be 1)
jq '[.plan[] | select(.type == "ReasoningStep")] | length' "$TRACE"
# 4. Correct tools visible
jq -r '.plan[] | select(.type == "EnabledToolsStep") | .data.enabled_tools[]' "$TRACE"
# 5. Variable state updated correctly
jq -r '.plan[] | select(.type == "VariableUpdateStep") | .data.variable_updates[] | "\(.variable_name): \(.variable_new_value)"' "$TRACE"
```

**At scale** -- after 24-48 hours of new live sessions, re-run Phase 1 and compare against the pre-fix baseline:

| Metric | What to look for after fix |
|---|---|
| Subagents seen in STDM | Dead subagents should now appear in session data |
| `TRUST_GUARDRAILS_STEP` value | `LOW` occurrences should drop or disappear |
| Action invocation per turn | Actions should now fire for the intents they cover |
| `action_error_count` | Should not increase (regression check) |
| Avg session duration / turn count | Shorter = less confusion, faster resolution |

---

## Safety Re-Verification (Required)

After applying fixes, re-run safety review on the modified `.agent` file. Optimization fixes can inadvertently introduce safety regressions:

- Relaxing `available when` guards may expose actions that should be gated
- Expanding subagent descriptions may cause the agent to handle out-of-scope requests
- Changing instructions to be more permissive may weaken guardrails
- Adding literal instructions with tool names may bypass safety boundaries

**Run the safety review** from `Section 15 of /developing-agentforce` (Identity, User Safety, Data Handling, Content Safety, Fairness, Deception, Scope). Focus especially on:

1. **Scope boundaries** -- Did the fix widen the agent's scope beyond what's appropriate?
2. **Guard conditions** -- Did relaxing `available when` expose sensitive actions?
3. **Instruction safety** -- Do new/modified instructions maintain appropriate guardrails?
4. **Escalation paths** -- Are escalation paths still intact after subagent restructuring?

**If any new BLOCK finding is introduced by the fix:** revert and find an alternative fix. Do NOT deploy an agent with new safety violations.

---

## Update Testing Center Test Cases

After fixing issues, create or update test cases in Testing Center format:

```yaml
# tests/<AgentApiName>-regression.yaml
name: "<AgentApiName> Regression Tests"
subjectType: AGENT
subjectName: <AgentApiName>

testCases:
  - utterance: "<exact utterance from Phase 2 scenario>"
    expectedTopic: <subagent_that_should_handle_this>
    expectedActions:
      - <action_that_should_fire>

  - utterance: "<another failing utterance>"
    expectedTopic: <expected_subagent>
    expectedOutcome: "Agent should <expected behavior description>"
```

**Key format rules:**
- `expectedActions` is a **flat string list**: `["action_a"]`, NOT objects
- `subjectName` is the agent's `DeveloperName` (API name without `_vN` suffix)
- `expectedOutcome` uses LLM-as-judge evaluation

**Deploy and run:**

```bash
sf agent test create --json \
  --spec tests/<AgentApiName>-regression.yaml \
  --api-name <AgentApiName>_Regression \
  --force-overwrite \
  -o <org>

sf agent test run --json \
  --api-name <AgentApiName>_Regression \
  --wait 10 \
  --result-format json \
  -o <org> | tee /tmp/regression_run.json

# ALWAYS use --job-id, NOT --use-most-recent which is broken
JOB_ID=$(python3 -c "import json; print(json.load(open('/tmp/regression_run.json'))['result']['runId'])")
sf agent test results --json --job-id "$JOB_ID" --result-format json -o <org>
```

All test cases derived from Phase 2 `[CONFIRMED]` issues should pass after the Phase 3 fix.
