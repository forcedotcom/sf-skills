# Agent Validation and Debugging Reference

## Table of Contents

1. Validation
2. Error Taxonomy and Prevention
3. Preview
4. Session Traces
5. Diagnostic Patterns
6. Diagnostic Workflow

---

## 1. Validation

The `sf agent validate` command checks Agent Script files for syntax errors, structural issues, and missing declarations before you attempt to preview or deploy an agent.

### Running Validation

After modifying any `.agent` file, always run this command:

```bash
sf agent validate authoring-bundle --api-name <AGENT_NAME> --json
```

Replace `<AGENT_NAME>` with the directory name under `aiAuthoringBundles/` (without the `.agent` extension). Always include `--json` so the output is machine-readable.

Example:

```bash
sf agent validate authoring-bundle --api-name Local_Info_Agent --json
```

### Interpreting Output

When validation succeeds, the JSON output contains `result.success` set to `true`:

```json
{
  "status": 0,
  "result": {
    "success": true
  },
  "warnings": []
}
```

When validation fails, the CLI treats it as an error. The output uses the CLI error format, not a structured validation result. All useful information is in the `message` field. Ignore `stack`, `cause`, `code`, and `commandName` — these are CLI internals, not diagnostic content.

The `message` field contains the compilation errors. These errors may include ANSI terminal color codes (`\u001b[31m`, `\u001b[39m`, etc.) — strip these before interpreting the message. Errors typically include line and column references (e.g., `[Ln 92, Col 13]`) that map to the `.agent` file, but do not assume a fixed error format. Read the `message` content naturally and reason about what it tells you.

Do not attempt to preview or deploy until validation passes.

### Validation Checklist (Pre-Validate Mental Model)

Before running the validation command, mentally check these 14 items. This checklist prevents the most common errors and speeds up the feedback loop:

- Block ordering is correct: `system` → `config` → `variables` → `connections` → `knowledge` → `language` → `start_agent` → `topic` blocks
- `config` block has `developer_name` (required for service agents: also needs `default_agent_user`)
- `system` block has `messages.welcome`, `messages.error`, and `instructions`
- `start_agent` block exists with description and at least one transition action
- Each `topic` has a `description` and `reasoning` block
- All `mutable` variables have default values (required)
- All `linked` variables have `source` specified and NO default value
- Action `target` uses valid format (`flow://`, `apex://`, `prompt://`, etc.)
- Boolean values use `True`/`False` (capitalized, not `true`/`false`)
- `...` is used for LLM slot-filling in reasoning action inputs, not as variable defaults
- Transition syntax is correct: `@utils.transition to` in `reasoning.actions`, bare `transition to` in directive blocks
- Indentation is consistent (4 spaces recommended)
- Names follow naming rules (letters, numbers, underscores only; no spaces; start with letter)
- No duplicate block names or action names within the same scope

---

## 2. Error Taxonomy and Prevention

Validation errors fall into several categories: block ordering, indentation, syntax, missing declarations, type mismatches, and structural violations. The following examples show the most common mistakes and their fixes.

### Common Mistakes with WRONG/RIGHT Pairs

**1. Wrong Transition Syntax**

```agentscript
# WRONG — bare transition in reasoning.actions
go_next: transition to @topic.next

# CORRECT — use @utils.transition to in reasoning.actions
go_next: @utils.transition to @topic.next

# CORRECT — use bare transition in directive blocks
after_reasoning:
    transition to @topic.next
```

In reasoning actions (where the LLM decides what to do), use `@utils.transition to`. In directive blocks (`before_reasoning`, `after_reasoning`), use bare `transition to`. These are two different syntaxes for two different contexts.

**2. Missing Default for Mutable Variable**

```agentscript
# WRONG — mutable variables must have default values
count: mutable number

# CORRECT
count: mutable number = 0
```

Mutable variables are initialized at runtime. They must have a default value so the runtime knows the initial state.

**3. Wrong Boolean Capitalization**

```agentscript
# WRONG — lowercase booleans
enabled: mutable boolean = true

# CORRECT — capitalized booleans
enabled: mutable boolean = True
```

Agent Script requires `True`/`False` (capitalized). This is consistent across all boolean contexts: variable defaults, conditional comparisons, and field values.

**4. Using `...` as Variable Default (It's for Slot-Filling Only)**

```agentscript
# WRONG — `...` is slot-filling syntax, not a default value
my_var: mutable string = ...

# CORRECT
my_var: mutable string = ""
```

`...` tells the LLM "extract this value from the conversation" during reasoning actions. It cannot be a variable default.

**5. List Type for Linked Variables**

```agentscript
# WRONG — linked variables cannot be lists
items: linked list[string]

# CORRECT — mutable can be list
items: mutable list[string] = []
```

Linked variables come from external context (session ID, user record, etc.) which are scalar values. Lists must be mutable.

**6. Default Value on Linked Variable**

```agentscript
# WRONG — linked variables get value from source, no default
session_id: linked string = ""
    source: @session.sessionID

# CORRECT — no default, only source
session_id: linked string
    source: @session.sessionID
```

Linked variables are populated from their `source` at runtime. Do not assign a default value.

**7. Post-Action Directives on Utility Actions**

```agentscript
# WRONG — utilities don't support post-action directives
go_next: @utils.transition to @topic.next
    set @variables.navigated = True

# CORRECT — only @actions support post-action directives
process: @actions.process_order
    set @variables.result = @outputs.result
```

Post-action directives (`set`, `run`, `if`, `transition`) only work after `@actions.*` invocations. Utility actions (`@utils.*`) and topic delegates (`@topic.*`) do not produce outputs, so post-action directives are not applicable.

---

## 3. Preview

Preview lets you test an agent's behavior by sending utterances and observing responses. The preview workflow starts a session, sends one or more utterances, and captures session traces for analysis.

### Programmatic Workflow

ALWAYS use `--json` when calling from a script or AI assistant (not interactive REPL).

#### Step 1: Start a Session

```bash
sf agent preview start --authoring-bundle <BUNDLE_NAME> --json
```

This command returns a session ID. Capture it immediately — you need it for every subsequent command.

Example:

```bash
sf agent preview start --authoring-bundle Local_Info_Agent --json
```

#### Step 2: Send Utterances

```bash
sf agent preview send --authoring-bundle <BUNDLE_NAME> --session-id <SESSION_ID> -u "<MESSAGE>" --json
```

Include the same `--authoring-bundle` name and the session ID from Step 1. You can send multiple utterances in the same session — do not end and restart between turns.

Example:

```bash
sf agent preview send --authoring-bundle Local_Info_Agent --session-id abc123def456 -u "What's the weather?" --json
```

#### Step 3: End a Session (Optional)

```bash
sf agent preview end --authoring-bundle <BUNDLE_NAME> --session-id <SESSION_ID> --json
```

This command returns the path to session trace files. Call it when the conversation is complete. Do not end prematurely — if the user may ask follow-up questions, keep the session open.

### Execution Modes

Agent Script agents in authoring bundles support two preview execution modes: simulated (default) and live.

**Simulated Preview Mode (Default).** The LLM generates fake action outputs. Use simulated preview mode when:
- Backing Apex, Flows, or Prompt Templates don't exist yet (you're experimenting with instructions and flow before building actions)
- No default agent user is configured (live preview mode requires a real, active user; simulated preview mode skips this requirement)

Simulated preview mode speeds up inner-loop development but cannot validate real action outputs, variable-driven branching, or grounding behavior.

**Live Preview Mode.** Real backing code executes and returns real outputs. Pass `--use-live-actions`:

```bash
sf agent preview start --authoring-bundle <BUNDLE_NAME> --use-live-actions --json
```

Use live preview mode when:
- Backing code is deployed and a default agent user is configured
- Your test depends on real action output values (grounding validation, variable-driven branching, output formatting)

Live preview mode is required for reliable grounding testing. The grounding checker runs in both modes, but simulated preview mode generates fake action outputs via LLM, and those outputs can trigger false grounding failures because they don't match real data patterns. If you see grounding failures in simulated preview mode, switch to live preview mode before diagnosing — the failure may be an artifact of simulation, not a real problem.

CRITICAL: `--use-live-actions` is ONLY valid with `--authoring-bundle`. Published agents (`--api-name`) always execute real actions — do NOT pass `--use-live-actions` with `--api-name`.

### Agent Identification

Use exactly one of these mutually exclusive flags:

- `--authoring-bundle <name>` — for a local Agent Script agent. The name is the directory name under `aiAuthoringBundles/` (without the `.agent` extension).
- `--api-name <name>` — for a published agent in the org. The name is the directory name under `Bots/`.

These flags identify which agent to preview.

To use a published agent, switch from `--authoring-bundle` to `--api-name`. No additional setup is required. The agent runs real actions; `--use-live-actions` is not passed.

### Target Org

The CLI automatically uses the project's default target org. Always omit `--target-org` and rely on the project default. Only pass `--target-org` if the user explicitly tells you which org to use. Never guess or invent an org username.

### Common Preview Mistakes with WRONG/RIGHT Pairs

**1. Using the Interactive REPL from Automation**

```bash
# WRONG — requires terminal interaction (ESC to exit)
sf agent preview --authoring-bundle My_Bundle

# CORRECT — programmatic API
sf agent preview start --authoring-bundle My_Bundle --json
```

The bare `sf agent preview` command is an interactive REPL for humans. Automation cannot provide terminal input (ESC), so it hangs. Use `start`/`send`/`end` with `--json`.

**2. Combining `--authoring-bundle` and `--api-name`**

```bash
# WRONG — mutually exclusive flags
sf agent preview start --authoring-bundle My_Bundle --api-name My_Agent --json

# CORRECT — choose one
sf agent preview start --authoring-bundle My_Bundle --json
```

These flags are mutually exclusive. Use the one matching your agent type.

**3. Using `--authoring-bundle` to Verify a Published Agent**

```bash
# WRONG — publishes, then previews from LOCAL agent script (not what's published)
sf agent publish authoring-bundle --json --api-name My_Agent
sf agent preview start --json --authoring-bundle My_Agent

# CORRECT — publishes, then previews the PUBLISHED agent users interact with
sf agent publish authoring-bundle --json --api-name My_Agent
sf agent preview start --json --api-name My_Agent
```

Use `agent preview` commands with `--api-name` to preview published agents. 

**4. Sending Before Starting**

```bash
# WRONG — no session exists
sf agent preview send --authoring-bundle My_Bundle -u "Hello" --json

# CORRECT — start first, capture session ID
sf agent preview start --authoring-bundle My_Bundle --json
sf agent preview send --authoring-bundle My_Bundle --session-id <ID> -u "Hello" --json
```

Each session has a unique ID. You must start before sending.

**5. Forgetting the Agent Identifier on `send` and `end`**

```bash
# WRONG — missing --authoring-bundle
sf agent preview send --session-id <ID> -u "Hello" --json

# CORRECT
sf agent preview send --authoring-bundle My_Bundle --session-id <ID> -u "Hello" --json
```

Every command after `start` must include the same `--authoring-bundle` or `--api-name` flag.

**6. Omitting `--session-id` on `send` or `end`**

```bash
# WRONG — concurrent sessions collide
sf agent preview send --authoring-bundle My_Bundle -u "Hello" --json

# CORRECT — always include session ID
sf agent preview send --authoring-bundle My_Bundle --session-id <ID> -u "Hello" --json
```

If multiple agents have concurrent sessions against the same agent, omitting the session ID causes them to interfere. Always pass the session ID from `start`.

### Context Variable Limitations in Preview

Agent behavior requiring `@context` or `@session` variables for routing or guards CAN NOT be tested via `sf agent preview`. Commands in the `preview` topic DO NOT support context or session variable injection. Flags like `--context`, `--session-var`, or `--variables` DO NOT EXIST.

- `@session.sessionID`, `@context.customerId`, `@context.RoutableId` — do NOT work in preview.
- Mutable variables with default values — work normally in preview.
- `with param=...` (LLM slot-filling) — works normally in preview.

### Utterance Derivation

Utterances provided to `sf agent preview send` must be derived from the `.agent` file using these guidelines:

1. **One per non-start topic** — based on `description:` keywords. Pick the most natural user phrasing.
2. **One that should trigger each key action** — match the action's `description:` to a realistic user request.
3. **One off-topic utterance** — tests guardrails (e.g., "Tell me a joke", "What's the weather?").
4. **One multi-turn pair** — if agent has topic transitions, send two related utterances to test handoff (e.g., "Check my order" → "Actually I want to return it").

---

## 4. Session Traces

After each utterance in a preview session, the runtime writes trace files. Traces show the complete execution path: what topic was selected, what variables were set, what the LLM saw in its prompt, what it decided to do, and whether the response passed grounding.

### Trace File Location

Traces are stored locally at:

```
.sfdx/agents/<AGENT_NAME>/sessions/<SESSION_ID>/
├── metadata.json           # Session metadata
├── transcript.jsonl        # Conversation log (one JSON object per line)
└── traces/
    └── <PLAN_ID>.json      # Detailed execution trace for each turn
```

Replace `<AGENT_NAME>` with your authoring bundle name (e.g., `Local_Info_Agent`). The `<SESSION_ID>` is the value returned by `sf agent preview start`. A separate trace file (identified by `<PLAN_ID>`) is written for each conversation turn.

Traces are available immediately after each `send` — you do NOT need to end the session to read them.

### File Structure

**metadata.json** contains session-level information: `sessionId`, `agentId`, `startTime`, and `mockMode` (either `"Mock"` for simulated or `"Live Test"` for live).

**transcript.jsonl** is a conversation log with one JSON object per line. Each entry includes `timestamp`, `agentId`, `sessionId`, `role` (`"user"` or `"agent"`), and `text`. Agent responses also include a `raw` array with additional metadata — most importantly, the `planId` field that links to the corresponding trace file.

```json
{"timestamp":"...","agentId":"Local_Info_Agent","sessionId":"abc123","role":"user","text":"What's the weather?"}
{"timestamp":"...","agentId":"Local_Info_Agent","sessionId":"abc123","role":"agent","text":"The weather on 2026-02-19...","raw":[{"planId":"def456","isContentSafe":true,...}]}
```

To connect a failed turn to its trace, find the agent response in the transcript and read the `planId` from its `raw` array. That `planId` is the filename under `traces/`.

**traces/<PLAN_ID>.json** is the detailed execution log for a single turn. It contains top-level fields (`type`, `planId`, `sessionId`, `intent`, `topic`) and a `plan` array with execution steps in chronological order.

### Step Types (Reference Table)

Each trace step type reveals specific execution information:

- **`UserInputStep`** — The user's utterance that triggered this turn.
- **`SessionInitialStateStep`** — Variable values and directive context at turn start.
- **`NodeEntryStateStep`** — Which agent/topic is executing and its full state snapshot.
- **`VariableUpdateStep`** — A variable was changed — shows old/new value and reason.
- **`BeforeReasoningIterationStep`** — `before_reasoning` block ran — lists actions executed.
- **`EnabledToolsStep`** — Which tools/actions are available to the LLM for this reasoning cycle.
- **`LLMStep`** — The LLM call — full prompt, response, available tools, latency.
- **`FunctionStep`** — An action executed — shows input, output, and latency.
- **`ReasoningStep`** — Grounding check result — `GROUNDED` or `UNGROUNDED` with reason.
- **`TransitionStep`** — Topic transition — shows from/to topics and transition type.
- **`PlannerResponseStep`** — Final response delivered to user — includes safety scores.


### How to Read a Trace

Read steps in chronological order:

1. Locate `UserInputStep` — the trigger for this turn
2. Check `NodeEntryStateStep` — which topic is running and what is the current variable state?
3. Look for `EnabledToolsStep` — what actions are available to the LLM?
4. Find `LLMStep` — examine `messages_sent` (the full prompt), `tools_sent` (available actions), and `response_messages` (what the LLM chose to do)
5. If an action was called, find the corresponding `FunctionStep` — compare inputs sent and outputs received
6. Check `ReasoningStep` — did the response pass grounding?
7. Look for `TransitionStep` — did the agent move to another topic?
8. Check `PlannerResponseStep` — what did the user receive?

### The LLMStep in Detail

The `LLMStep` is the most diagnostic step type. It contains:

- `agent_name` — which topic or selector is running
- `messages_sent` — the FULL prompt sent to the LLM (system message, conversation history, and injected instructions)
- `tools_sent` — action names available to the LLM
- `response_messages` — the LLM's response (text or tool invocation)
- `execution_latency` — milliseconds for the LLM call

The `messages_sent` array shows you exactly what the LLM saw. This is invaluable for debugging because:
- You can see how Agent Script instructions were compiled into the system prompt
- You can see the full conversation history (including grounding retry injections)
- You can verify that variable interpolation (`{!@variables.x}`) worked correctly
- You can see platform-injected system prompts (tool usage protocol, safety routing, language guidelines) that your Agent Script instructions sit alongside


### When to Use Traces vs. Transcript

Use the **transcript** to quickly identify WHICH turn failed (unexpected response, wrong topic, agent crash).

Use the **trace files** when:
- The agent routes to the wrong topic
- An action isn't firing
- The response is unexpectedly worded
- Grounding is failing
- You need to understand variable values at a specific point in execution
- You need to see what the LLM actually saw in its prompt

The transcript is sufficient for conversation-level understanding. Traces provide execution-level detail needed for diagnosis.

### Trace Diagnostic Checks

Use these `jq` commands against trace files (`traces/<PLAN_ID>.json`) to quickly extract diagnostic information.

#### Check 1: Topic Routing

```bash
jq '[.steps[] | select(.stepType == "TransitionStep") | .data.to]' "$TRACE"
```

**Expected**: Array contains the target topic name (e.g., `["order_mgmt"]`). Empty array means the agent stayed in Topic Selector — topic descriptions are too vague. Wrong topic name means keyword overlap between topics.

#### Check 2: Action Invocation

```bash
jq '[.steps[] | select(.stepType == "FunctionStep") | .data.function]' "$TRACE"
```

**Expected**: Array contains the target action name. If missing: `available when:` guards too restrictive, action `description:` doesn't match user request, or action not listed in `reasoning.actions:` for this topic.

#### Check 3: Wrong Action Selected

Use the same `jq` as Check 2 — compare output against expected action name. If the wrong action fired, two actions have overlapping descriptions. Differentiate with exclusion language and `available when:` guards.

#### Check 4: Grounding Assessment

```bash
jq '[.steps[] | select(.stepType == "ReasoningStep") | .data.groundingAssessment]' "$TRACE"
```

**Expected**: `"GROUNDED"` for all reasoning steps. `"UNGROUNDED"` means the agent fabricated data instead of using action outputs or variable values. Add explicit data references in `instructions: ->` block using `{!@variables.X}` or `{!@outputs.Y}`.

#### Check 5: Safety Score

```bash
jq '.steps[] | select(.stepType == "PlannerResponseStep") | .data.safetyScore' "$TRACE"
```

**Expected**: `.overall >= 0.9`. Low score indicates the agent is revealing internal system details, responding to harmful prompts without guardrails, or missing safety instructions in `system:` block.

#### Check 6: Tool Visibility

```bash
jq '[.steps[] | select(.stepType == "EnabledToolsStep") | .data.enabled_tools]' "$TRACE"
```

**Expected**: Array includes the action names defined in the topic's `reasoning.actions:`. If missing: `available when:` conditions not met, action defined in wrong topic, or action `target:` protocol invalid (flow not deployed, apex class not found).

---

## 5. Diagnostic Patterns

These patterns map symptoms to trace analysis techniques. Each pattern follows the same structure: symptom → which trace steps to examine → root cause → fix (with code example).

### Pattern: Wrong Topic Routing

**Symptom:** The agent enters the wrong topic. For example, asking about weather sends the agent to the events topic instead.

**Trace Analysis:**

1. Find the `LLMStep` where `agent_name` is `topic_selector` (the entry point that routes to topics)
2. Examine `tools_sent` — are the transition actions for all expected topics listed? (e.g., `go_to_local_weather`, `go_to_local_events`, `go_to_resort_hours`)
3. Examine `response_messages` — which action tool did the LLM select?
4. Examine `messages_sent` — does the system prompt (what topic selector instructions were compiled to) give the LLM enough context to route correctly?

**Root Cause:** Topic selector instructions are ambiguous, missing context, or don't map user requests to the correct topics.

**Fix:** A minimal topic selector with well-named actions often routes correctly. When it doesn't, add routing instructions and action descriptions to give the LLM more context:

```agentscript
# BEFORE — relies on action names alone for routing
start_agent topic_selector:
    description: "Route to appropriate topics"
    reasoning:
        actions:
            go_to_weather: @utils.transition to @topic.local_weather
            go_to_events: @utils.transition to @topic.local_events

# AFTER — explicit instructions and descriptions improve routing accuracy
start_agent topic_selector:
    description: "Route to appropriate topics"
    reasoning:
        instructions: ->
            | If the user asks about weather conditions, temperature, or forecasts, go to the weather topic.
              If the user asks about local events, activities, or entertainment, go to the events topic.
              If the user asks about facility hours, reservations, or amenities, go to the hours topic.

        actions:
            go_to_weather: @utils.transition to @topic.local_weather
                description: "Route to weather topic for weather questions"
            go_to_events: @utils.transition to @topic.local_events
                description: "Route to events topic for local event questions"
            go_to_hours: @utils.transition to @topic.resort_hours
                description: "Route to hours topic for facility hours questions"
```


### Pattern: Actions Not Firing

**Symptom:** The agent doesn't call an action you expect it to. For example, the agent should fetch data but responds without calling the action.

**Trace Analysis:**

1. Find the `EnabledToolsStep` for the topic — is the expected action listed?
2. If missing:
   - Check the action definition's `available when` condition (e.g., `available when @variables.guest_interests != ""`)
   - Look at the `NodeEntryStateStep` to see if the gating variable has the expected value
   - If the variable is empty or has the wrong value, the action is hidden
3. If listed but not called:
   - Find the `LLMStep` response — did the LLM choose a different action or respond without using any tool?
   - Compare `messages_sent` — does the instructions tell the LLM when to use this action?

**Root Cause:** Either the action is gated behind a condition that hasn't been satisfied, or the instructions don't tell the LLM to call it.

**Fix Example:**

```agentscript
# WRONG — action is hidden until guest_interests is set, but there's no way to set it
reasoning:
    actions:
        check_events: @actions.check_events
            available when @variables.guest_interests != ""
            with Event_Type = @variables.guest_interests

# CORRECT — first step collects interests, second action uses them
reasoning:
    instructions: ->
        | Ask about the guest's interests if you don't know them yet.
          Once you know what they're interested in, look up matching events.

    actions:
        collect_interests: @utils.setVariables
            description: "Collect the guest's interests"
            with guest_interests = ...

        check_events: @actions.check_events
            description: "Look up local events matching the guest's interests"
            available when @variables.guest_interests != ""
            with Event_Type = @variables.guest_interests
```


### Pattern: Behavioral Loops

**Symptom:** The agent keeps asking the same question or repeating the same response across multiple turns, even though the user already provided the requested information.

**Diagnosis:** Observe the conversation output first — the behavioral symptom is often obvious (e.g., the agent asking the same question repeatedly). A common cause is instructions that collect information and act on it within the same topic — when the topic is re-entered, the collection logic runs again even though the data was already gathered.

**Fix Example:** In this real scenario, the `local_events` topic asks about interests and then looks up events. But each time the topic is re-entered, the agent asks about interests again instead of checking whether it already knows them:

```agentscript
# BEFORE — agent asks about interests every time the topic is entered
reasoning:
    instructions: ->
        | If you do not already know the guest's interests, ask them about their
          interests so you can provide relevant event information.
          Use the {!@actions.check_events} action to get a list of events once
          you know what the guest is interested in.

    actions:
        collect_interests: @utils.setVariables
            description: "Collect the guest's interests when they share them"
            with guest_interests = ...

        check_events: @actions.check_events
            available when @variables.guest_interests != ""
            with Event_Type = @variables.guest_interests

# AFTER — condition on the variable, not on re-asking
reasoning:
    instructions: ->
        | If @variables.guest_interests is empty, ask the guest about their interests.
          If @variables.guest_interests is already set, use {!@actions.check_events}
          to find matching events and present the results.
          Do NOT ask about interests again if you already have them.

    actions:
        collect_interests: @utils.setVariables
            description: "Collect the guest's interests when they share them"
            with guest_interests = ...

        check_events: @actions.check_events
            available when @variables.guest_interests != ""
            with Event_Type = @variables.guest_interests
```

The key difference: the AFTER version explicitly references the variable value to decide whether to ask or act, and includes a stop condition ("Do NOT ask about interests again").

Note: repeated `LLMStep` → `ReasoningStep` pairs in a trace may indicate grounding retry rather than a behavioral loop — see Diagnostic Workflow: Grounding subsection.

### Pattern: "Unexpected Error" Responses

**Symptom:** The agent returns "I apologize, but I encountered an unexpected error" instead of a normal response.

**Trace Analysis:**

1. Find the `PlannerResponseStep` — is the message the system error message?
2. Look backward through the trace for consecutive `ReasoningStep` entries with `category: "UNGROUNDED"` — two consecutive UNGROUNDED results cause this error
3. If no grounding failures, look for `FunctionStep` entries with error outputs (action execution failed)
4. Check if a topic transition failed (the target topic doesn't exist or has a circular reference)

**Root Cause:** Grounding failed twice in a row, OR an action returned an error, OR a topic transition is misconfigured.

**Fix:** See Diagnostic Workflow: Grounding subsection for grounding failures. For action errors, verify the backing Apex/Flow/Prompt Template is deployed and handles edge cases correctly. For transition errors, verify all referenced topics exist and are spelled correctly.

### Pattern: Agent Responds with Generic Message but No Data After Successful Action

**Symptom:** Action returns data (visible in `FunctionStep.function.output`) but the agent's text response is empty or generic (e.g., "Here are the results:").

**Trace Analysis:**

1. Check `EnabledToolsStep` — it lists both your defined actions and platform-injected tools. Any tool you did not define is a platform tool.
2. Find the `LLMStep` after the `FunctionStep`. If `response_messages` contains a `tool_invocation` targeting a platform tool instead of a text response, the LLM chose that tool over composing a reply.

**Fix:** Update reasoning instructions to direct the LLM to write specific field values from the action response in its text reply. Name the fields. Block the observed platform tool by name.

### Fix Strategies Quick Reference

| Failure | Target Block | Edit Strategy | Example |
|---------|-------------|---------------|---------|
| Topic not matched | `topic X: description:` | Add keywords from test utterance | `"Handle orders"` → `"Handle order queries, order status, package tracking, shipping updates"` |
| Action not invoked | `reasoning.actions: X description:` | Make description more trigger-specific | `"Get order"` → `"Look up order status when user asks about their order, package, or delivery"` |
| Action not invoked | `available when:` | Relax guard condition | Remove overly restrictive `@variables.X == True` if variable isn't set yet |
| Wrong action selected | Both competing `description:` fields | Differentiate with exclusion language | Add `"NOT for returns"` to order action, `"ONLY for returns"` to refund action |
| Ungrounded response | `reasoning: instructions: ->` | Add explicit data references | `"Help the customer"` → `"Help the customer using {!@variables.order_data} from Get_Order action"` |
| Low safety score | `system: instructions:` | Add safety guidelines | Add `CRITICAL: Never reveal internal system details or customer PII` |
| Tool not visible | `available when:` | Ensure guard matches test state | Set test variables before action, or remove guards for initial smoke test |

---

## 6. Diagnostic Workflow

Use this systematic 8-step approach when diagnosing any agent behavior issue.

1. **Reproduce** — Use `sf agent preview start/send/end` with `--json` to recreate the issue with the exact user input that triggered it

2. **Locate** — Open `transcript.jsonl` and find the failing agent turn. Read the `planId` from its `raw` array.

3. **Read the Trace** — Open `traces/<PLAN_ID>.json` for the failing turn. Read the plan array in order.

4. **Follow Execution** — As you read each step, note:
   - Which topic was selected? (Look at `NodeEntryStateStep`)
   - What state were variables in? (Look at `SessionInitialStateStep` and `VariableUpdateStep`)
   - What actions were available vs. invoked? (Look at `EnabledToolsStep` and `LLMStep` response)
   - What did the LLM see in its prompt? (Look at `LLMStep.messages_sent`)
   - What did it respond with? (Look at `LLMStep.response_messages`)
   - Did the response pass grounding? (Look at `ReasoningStep.category`)

5. **Identify the Gap** — Compare expected behavior to actual execution at each step. Use the diagnostic patterns (Section 5) to map symptoms to root causes.

6. **Fix** — Update Agent Script instructions, variable logic, or action definitions based on what you found.

7. **Validate** — Run `sf agent validate authoring-bundle --api-name <AGENT_NAME> --json` to ensure the fix doesn't introduce syntax errors.

8. **Re-Test** — Run a new preview session with the same input and compare traces. Verify the fix resolved the issue.


### Grounding

Grounding is a platform service that validates an agent's response against real action output data. When grounding fails, the platform gives the LLM a second chance. Understanding how grounding works, why it fails, and how to fix it is critical for behavioral diagnosis.

#### The Grounding Retry Mechanism

When the platform's grounding checker flags a response as UNGROUNDED:

1. The system injects an error message as a `role: "user"` message:
   ```
   Error: The system determined your original response was ungrounded.
   Reason the response was flagged: [explanation]
   Try again. Make sure to follow all system instructions.
   Original query: [original user message]
   ```
2. The LLM is given another chance to respond
3. If the second attempt is also UNGROUNDED, the agent returns the system error message ("I apologize, but I encountered an unexpected error") and gives up
4. This retry is visible in traces as repeated `LLMStep` → `ReasoningStep` pairs for the same topic
5. When this happens, the actual action output is still in the trace's `FunctionStep.function.output`. The LLM's failed response attempts are in the `LLMStep.response_messages`. Use these to understand what the agent tried to say versus what the action actually returned.


#### Non-Deterministic Behavior

The grounding checker is non-deterministic. The same response may be flagged as UNGROUNDED on one attempt and GROUNDED on the next. When diagnosing intermittent grounding failures, look for responses that require the grounding checker to make inferences (date inference, unit conversions, paraphrased values).

#### Common Grounding Failure Causes

- **Date Inference:** Function returns a specific date (e.g., "2025-02-19"), agent says "today" or "this week". The grounding checker cannot always infer that a relative date equals a specific date.
- **Unit Conversion:** Function returns Celsius, agent responds in Fahrenheit without the grounding checker recognizing the conversion.
- **Embellishment:** Agent adds details not in the function output (e.g., "gentle breeze" when the function only returned temperature data).
- **Loose Paraphrasing:** Agent restates function output in words that don't closely match the original.


#### Diagnosing Grounding Failures

1. Find the `ReasoningStep` with `category: "UNGROUNDED"`
2. Read the `reason` field — it explains exactly what the grounding checker flagged
3. Find the `FunctionStep` output for the action that was called
4. Find the `LLMStep` response — compare it to the function output
5. Identify where the response diverges from the function output (dates, numbers, names, facts)

**Example:** Function returns:
```json
{"date": "2025-02-19", "temperature": "48.5F"}
```

Agent responds: "Today will be around 50 degrees."

Grounding fails because: "today" requires inference (the checker doesn't know if 2025-02-19 is today), and "around 50" doesn't match the specific value "48.5F".

#### Fix Approach

Update Agent Script instructions to tell the agent to use specific values from action output verbatim rather than paraphrasing or inferring.

```agentscript
# WRONG — allows paraphrasing and inference
reasoning:
    instructions: ->
        | Tell the user about the weather.

# CORRECT — explicit instructions to use verbatim values
reasoning:
    instructions: ->
        | After getting weather results, respond using the exact date and temperature
          values returned by the action. Do NOT paraphrase dates (say "2025-02-19",
          not "today"). Do NOT round temperatures (say the exact value from the results).
          Quote action output values verbatim whenever possible.
```

#### Grounding in Simulated Preview Mode

The grounding checker runs in both simulated and live preview modes. However, simulated preview mode generates fake action outputs via LLM, and those outputs can trigger false grounding failures because they don't match real data patterns. If you see grounding failures during simulated preview, switch to live preview mode (`--use-live-actions`) before investing time in diagnosis — the failure may be an artifact of simulation, not a real instruction problem.

### Iterative Debugging Patterns

When fixing errors through repeated preview cycles, track how the error message changes between attempts. A different error after a fix usually means progress, not regression.

**Anti-pattern: reverting a correct fix because a new error appeared.**

```
# WRONG — assumes changed error = bad fix
Preview attempt 1: "Invalid complex_data_type_name format"
→ Fix: change complex_data_type_name to "@apexClassType/c__MyClass$Result"
Preview attempt 2: "Action output type mismatch"
→ Conclusion: "My fix broke something, reverting"

# RIGHT — recognize error evolution as forward progress
Preview attempt 1: "Invalid complex_data_type_name format"
→ Fix: change complex_data_type_name to "@apexClassType/c__MyClass$Result"
Preview attempt 2: "Action output type mismatch"
→ Conclusion: "Format is now valid. New error is a different layer — diagnose the type mismatch separately."
```

**Rule:** Compare the error message text, not just pass/fail. If the error changed, the previous fix likely resolved its target issue. Diagnose the new error as a separate problem. Only revert a fix if the *same* error persists or worsens.

---

