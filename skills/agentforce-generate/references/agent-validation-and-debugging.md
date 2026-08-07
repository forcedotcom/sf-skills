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
sf agent validate authoring-bundle --json --api-name <AGENT_NAME>
```

Replace `<AGENT_NAME>` with the directory name under `aiAuthoringBundles/` (without the `.agent` extension). Always include `--json` so the output is machine-readable.

Example:

```bash
sf agent validate authoring-bundle --json --api-name Local_Info_Agent
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

- Block ordering is correct: `system` → `access` → `config` → `variables` → `connections` → `knowledge` → `language` → `start_agent` → `subagent` blocks
- `config` has `developer_name`; service agents also need `access.default_agent_user`
- `system` block has `messages.welcome`, `messages.error`, and `instructions`
- `start_agent` block exists with description and at least one transition action
- Each `subagent` has a `description` and `reasoning` block
- All `mutable` variables have default values (required)
- All `linked` variables have `source` specified and NO default value
- Action `target` uses valid format (`flow://`, `apex://`, `prompt://`, etc.)
- Boolean values use `True`/`False` (capitalized, not `true`/`false`)
- `...` is used for LLM slot-filling in reasoning action inputs, not as variable defaults
- Transition syntax is correct: `@utils.transition to` in `reasoning.actions`, bare `transition to` in directive blocks
- New files use 4-space structural indentation; edited files do not mix styles
- Names follow naming rules (letters, numbers, underscores only; no spaces; start with letter)
- No duplicate block names or action names within the same scope
- Conditional chains use `if / else if / else`, never legacy `elif`; true
  nested conditionals are avoided

---

## 2. Error Taxonomy and Prevention

Validation errors fall into several categories: block ordering, indentation, syntax, missing declarations, type mismatches, and structural violations. The following examples show the most common mistakes and their fixes.

### Common Mistakes with WRONG/RIGHT Pairs

**1. Wrong Transition Syntax**

```agentscript
# WRONG — bare transition in reasoning.actions
go_next: transition to @subagent.next

# CORRECT — use @utils.transition to in reasoning.actions
go_next: @utils.transition to @subagent.next

# CORRECT — use bare transition in directive blocks
after_reasoning:
    transition to @subagent.next
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
go_next: @utils.transition to @subagent.next
    set @variables.navigated = True

# CORRECT — only @actions support post-action directives
process: @actions.process_order
    set @variables.result = @outputs.result
```

Post-action directives (`set`, `run`, `if`, `transition`) only work after `@actions.*` invocations. Utility actions (`@utils.*`) and subagent delegates (`@subagent.*`) do not produce outputs, so post-action directives are not applicable.

**8. Conditional Syntax**

Use `if / else if / else`; `elif` produces a syntax error. Agentforce lint
rejects true nested conditionals with `unsupported-nested-if`; the compiler
also warns about the narrower nested `if/else` condition-slot limitation. For
examples, post-action behavior, and flattening alternatives, use the canonical
[Conditional Control Flow Syntax](agent-script-core-language.md#conditional-control-flow-syntax)
section rather than maintaining a second syntax guide here.

---

## 3. Preview

Preview lets you test an agent's behavior by sending utterances and observing responses. The preview workflow starts a session, sends one or more utterances, and captures session traces for analysis.

### Programmatic Workflow

ALWAYS use `--json` when calling from a script or AI assistant (not interactive REPL).

#### Step 1: Start a Session

```bash
sf agent preview start --json --authoring-bundle <BUNDLE_NAME> --use-live-actions
```

This command returns a session ID. Capture it immediately — you need it for every subsequent command. Use `--use-live-actions` to execute real action implementations (recommended). Omit it only when implementations don't exist yet and you want simulated preview.

Example:

```bash
sf agent preview start --json --authoring-bundle Local_Info_Agent --use-live-actions
```

#### Step 2: Send Utterances

```bash
sf agent preview send --json --authoring-bundle <BUNDLE_NAME> --session-id <SESSION_ID> -u "<MESSAGE>"
```

Include the same `--authoring-bundle` name and the session ID from Step 1. You can send multiple utterances in the same session — do not end and restart between turns.

Example:

```bash
sf agent preview send --json --authoring-bundle Local_Info_Agent --session-id abc123def456 -u "What's the weather?"
```

#### Step 3: End a Session (Optional)

```bash
sf agent preview end --json --authoring-bundle <BUNDLE_NAME> --session-id <SESSION_ID>
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
sf agent preview start --json --authoring-bundle <BUNDLE_NAME> --use-live-actions
```

Use live preview mode when:
- Backing code is deployed and a default agent user is configured
- Your test depends on real action output values (grounding validation, variable-driven branching, output formatting)

Live preview mode is required for reliable grounding testing. The grounding checker runs in both modes, but simulated preview mode generates fake action outputs via LLM, and those outputs can trigger false grounding failures because they don't match real data patterns. If you see grounding failures in simulated preview mode, switch to live preview mode before diagnosing — the failure may be an artifact of simulation, not a real problem.

CRITICAL: `--use-live-actions` is ONLY valid with `--authoring-bundle`. Published agents (`--api-name`) always execute real actions — do NOT pass `--use-live-actions` with `--api-name`.

CRITICAL: `--use-live-actions` is a flag on `preview start` ONLY. Do NOT pass it to `preview send` or `preview end` — those commands do not accept it and will error.

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
sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions
```

The bare `sf agent preview` command is an interactive REPL for humans. Automation cannot provide terminal input (ESC), so it hangs. Use `start`/`send`/`end` with `--json`.

**2. Combining `--authoring-bundle` and `--api-name`**

```bash
# WRONG — mutually exclusive flags
sf agent preview start --json --authoring-bundle My_Bundle --api-name My_Agent

# CORRECT — choose one
sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions
```

These flags are mutually exclusive. Use the one matching your agent type.

**3. Using `--authoring-bundle` to Verify a Published Agent**

```bash
# WRONG — publishes, then previews from LOCAL agent script (not what's published)
sf agent publish authoring-bundle --json --api-name My_Agent
sf agent preview start --json --authoring-bundle My_Agent --simulate-actions

# CORRECT — publishes, then previews the PUBLISHED agent users interact with
sf agent publish authoring-bundle --json --api-name My_Agent
sf agent preview start --json --api-name My_Agent
```

Use `agent preview` commands with `--api-name` to preview published agents. 

**4. Sending Before Starting**

```bash
# WRONG — no session exists
sf agent preview send --json --authoring-bundle My_Bundle -u "Hello"

# CORRECT — start first, capture session ID
sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions
sf agent preview send --json --authoring-bundle My_Bundle --session-id <ID> -u "Hello"
```

Each session has a unique ID. You must start before sending.

**5. Forgetting the Agent Identifier on `send` and `end`**

```bash
# WRONG — missing --authoring-bundle
sf agent preview send --json --session-id <ID> -u "Hello"

# CORRECT
sf agent preview send --json --authoring-bundle My_Bundle --session-id <ID> -u "Hello"
```

Every command after `start` must include the same `--authoring-bundle` or `--api-name` flag.

**6. Omitting `--session-id` on `send` or `end`**

```bash
# WRONG — concurrent sessions collide
sf agent preview send --json --authoring-bundle My_Bundle -u "Hello"

# CORRECT — always include session ID
sf agent preview send --json --authoring-bundle My_Bundle --session-id <ID> -u "Hello"
```

If multiple agents have concurrent sessions against the same agent, omitting the session ID causes them to interfere. Always pass the session ID from `start`.

**7. Omitting the action mode on `start`, or passing it to `send`/`end`**

```bash
# WRONG — MissingModeFlag: --authoring-bundle requires an action mode
sf agent preview start --json --authoring-bundle My_Bundle

# WRONG — Nonexistent flag: the mode is set once, on start
sf agent preview send --json --authoring-bundle My_Bundle --session-id <ID> --simulate-actions -u "Hello"

# CORRECT — mode on start only
sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions
sf agent preview send --json --authoring-bundle My_Bundle --session-id <ID> -u "Hello"
```

`--simulate-actions` has the platform generate plausible action results without touching the org; `--use-live-actions` executes real Apex, Flows, and Prompt Templates. Pick one on `start` — the choice applies to the whole session.

**8. Running outside a Salesforce project**

```bash
# WRONG — RequiresProjectError
cd /tmp && sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions

# CORRECT — run from the project root (where sfdx-project.json lives)
cd ~/projects/my-sfdx-project && sf agent preview start --json --authoring-bundle My_Bundle --simulate-actions
```

Every `sf agent preview` subcommand requires `sfdx-project.json` in the working directory.

### Context Variable Limitations in Preview

Agent behavior requiring `@context` or `@session` variables for routing or guards CAN NOT be tested via `sf agent preview`. Commands in the `preview` command DO NOT support context or session variable injection. Flags like `--context`, `--session-var`, or `--variables` DO NOT EXIST.

- `@session.sessionID`, `@context.customerId`, `@context.RoutableId` — do NOT work in preview.
- Mutable variables with default values — work normally in preview.
- `with param=...` (LLM slot-filling) — works normally in preview.

### Utterance Derivation

Utterances must sound like what a real human would type in a chat. Avoid keyword-style inputs — a user would never type just "upgrade" to upgrade their account. They'd say "Hey I'd like to upgrade my plan" or "Can I switch to the premium tier?" Write utterances that reflect natural conversational patterns.

#### Coverage Requirements

Smoke testing is not a single pass. Test broadly:

1. **Every routing branch** — If the agent has branching logic (multiple subagents, conditional transitions), test ALL branches, not just the happy path.
2. **Multiple variations per branch** — Test at least 2-3 different phrasings that should trigger the same subagent/action. Real users express the same intent differently ("I want to cancel", "How do I end my subscription?", "I don't want this anymore").
3. **Every key action** — Send utterances that should trigger each action. Verify via trace that the action actually fired (see "Trace Evaluation" below).
4. **Edge cases** — Ambiguous inputs, partial information, multi-intent messages, typos or informal language.
5. **Off-topic utterance** — Tests guardrails (e.g., "What's the meaning of life?", "Can you help me write a poem?").
6. **Multi-turn sequences** — Test subagent transitions and context carry-over across turns (e.g., "Check my order status" → "Actually I want to return it" → "Never mind, keep it").

#### Realistic Phrasing

Derive utterances from subagent/action `description:` keywords, but rewrite them as natural conversation:

| BAD (keyword-style) | GOOD (natural) |
|---|---|
| "upgrade" | "Hey, I'd like to upgrade my account to premium" |
| "check order" | "Can you look up order #12345 for me?" |
| "weather" | "What's the weather going to be like tomorrow?" |
| "cancel subscription" | "I'm thinking about canceling — what happens to my data?" |

### Trace Evaluation

After EVERY preview utterance, read the trace — not just the agent's text response. The agent's response alone is insufficient for validation because agents can claim to have performed actions without actually calling them.

Never trust the chat transcript as evidence that an action ran. The LLM will confidently paraphrase action success even when no invocation occurred.

For each turn, verify in the trace:

1. **Action execution** — Check for `FunctionStep` entries. If the agent said it performed an action (e.g., "I've upgraded your account"), confirm the corresponding action actually fired in the trace. An agent saying it did something without a `FunctionStep` is a critical bug.
2. **Correct subagent routing** — Check `TransitionStep` and `NodeEntryStateStep` to confirm the utterance routed to the expected subagent.
3. **Action inputs** — In `FunctionStep`, verify the inputs sent to the action match what the user provided (no hallucinated parameters).
4. **Action outputs used correctly** — Compare `FunctionStep` outputs to the agent's final response. The agent should be using real data from the action, not inventing values.
5. **Persisted state (live preview)** — For actions that write data (create records, update fields), query the backing SObject directly to confirm the write happened. This is ground truth. If no record exists, the action was not invoked regardless of what the trace or chat says — investigate the router first.

> **Traces are only written on the authoring-bundle preview path.** A preview started with
> `--api-name` (the published/activated agent) writes trace files containing exactly `{}` — no
> `plan` array, no `FunctionStep`. Verified on API v67.0 with `sf` CLI 2.145.6. Only
> `sf agent preview start --authoring-bundle <Name>` produces readable traces.
>
> This matters because the two are not always interchangeable: a **service** agent cannot always be
> previewed via `--authoring-bundle` (that path can be unreachable on restricted networks), which
> leaves `--api-name` as the only option — and it yields no trace. In that situation the
> "read the trace after every utterance" rule above cannot be satisfied, so substitute
> **discriminating-value testing**:
>
> - Query ground truth first, then ask the agent about records whose values an LLM could not guess.
>   A response matching an arbitrary figure like `$48,077.20` exactly is strong evidence the action
>   ran.
> - Better still, target a record that exercises a **distinctive code path** in the action
>   implementation. Example: an invocable that falls back to `Date.today().year()` when a record has
>   no transactions — if the agent reports that fallback year for such a record, the Apex
>   demonstrably executed.
> - Cross-check writes by querying the SObject directly, per item 5 above.
>
> Record which method you used. "Verified by trace" and "verified by discriminating value" are
> different strengths of evidence and should not be reported interchangeably.

### Behavioral Evaluation

Evaluate the agent's behavior like a human would — does this feel like a natural, competent conversation?

- **Spec-defined behavior** — If the spec or user explicitly defines a behavior (e.g., "collect all required inputs before calling the action"), verify the agent follows it exactly.
- **Natural conversation flow** — For everything NOT explicitly specified, the agent should behave naturally. Asking for confirmation multiple times, repeating information the user already provided, or over-explaining simple actions are all bugs even if the spec doesn't explicitly forbid them.
- **Response quality** — Is the response helpful, clear, and appropriately concise? Does it match the tone/persona defined in the spec?

When behavioral issues are found, identify whether the root cause is in instructions, routing, action wiring, or variable handling, and fix the `.agent` file accordingly. Then re-preview to confirm the fix.

---

## 4. Session Traces

After each utterance in a preview session, the runtime writes trace files. Traces show the complete execution path: what subagent was selected, what variables were set, what the LLM saw in its prompt, what it decided to do, and whether the response passed grounding.

### Trace File Location

Traces are stored locally at:

```text
.sfdx/agents/<AGENT_NAME>/sessions/<SESSION_ID>/
├── metadata.json           # Session metadata
├── transcript.jsonl        # Conversation log (one JSON object per line)
└── traces/
    └── <PLAN_ID>.json      # Detailed execution trace for each turn
```

Replace `<AGENT_NAME>` with your authoring bundle name (e.g., `Local_Info_Agent`). The `<SESSION_ID>` is the value returned by `sf agent preview start`. A separate trace file (identified by `<PLAN_ID>`) is written for each conversation turn.

Traces are available immediately after each `send` — you do NOT need to end the session to read them.

The **published-agent** preview path (`--api-name`) uses a different layout, keyed by **Bot ID**
rather than agent name, and its `traces/*.json` files are empty (`{}`):

```text
.sfdx/agents/<BOT_ID>/sessions/<SESSION_ID>/
├── metadata.json
├── session-meta.json
├── transcript.jsonl        # populated — the conversation is still readable
├── turn-index.json
└── traces/
    └── <PLAN_ID>.json      # written, but contains only {}
```

`transcript.jsonl` is still usable there, so you can review the conversation — you just cannot
confirm `FunctionStep` execution. Use the discriminating-value technique described under
[Trace Evaluation](#trace-evaluation) instead.

### File Structure

**metadata.json** contains session-level information: `sessionId`, `agentId`, `startTime`, and `mockMode` (either `"Mock"` for simulated or `"Live Test"` for live).

**transcript.jsonl** is a conversation log with one JSON object per line. Each entry includes `timestamp`, `agentId`, `sessionId`, `role` (`"user"` or `"agent"`), and `text`. Agent responses also include a `raw` array with additional metadata — most importantly, the `planId` field that links to the corresponding trace file.

```json
{"timestamp":"...","agentId":"Local_Info_Agent","sessionId":"abc123","role":"user","text":"What's the weather?"}
{"timestamp":"...","agentId":"Local_Info_Agent","sessionId":"abc123","role":"agent","text":"The weather on 2026-02-19...","raw":[{"planId":"def456","isContentSafe":true,...}]}
```

To connect a failed turn to its trace, find the agent response in the transcript and read the `planId` from its `raw` array. That `planId` is the filename under `traces/`.

**traces/<PLAN_ID>.json** is the detailed execution log for a single turn. It contains top-level fields (`type`, `planId`, `sessionId`, `intent`, `subagent`) and a `plan` array with execution steps in chronological order.

### Step Types (Reference Table)

Each trace step type reveals specific execution information:

- **`UserInputStep`** — The user's utterance that triggered this turn.
- **`SessionInitialStateStep`** — Variable values and directive context at turn start.
- **`NodeEntryStateStep`** — Which agent/subagent is executing and its full state snapshot.
- **`VariableUpdateStep`** — A variable was changed — shows old/new value and reason.
- **`BeforeReasoningIterationStep`** — `before_reasoning` block ran — lists actions executed.
- **`EnabledToolsStep`** — Which tools/actions are available to the LLM for this reasoning cycle.
- **`LLMStep`** — The LLM call — full prompt, response, available tools, latency.
- **`FunctionStep`** — An action executed — shows input, output, and latency.
- **`ReasoningStep`** — Grounding check result — `GROUNDED` or `UNGROUNDED` with reason.
- **`TransitionStep`** — Subagent transition — shows from/to subagents and transition type.
- **`PlannerResponseStep`** — Final response delivered to user — includes safety scores.


### How to Read a Trace

Read steps in chronological order:

1. Locate `UserInputStep` — the trigger for this turn
2. Check `NodeEntryStateStep` — which subagent is running and what is the current variable state?
3. Look for `EnabledToolsStep` — what actions are available to the LLM?
4. Find `LLMStep` — examine `messages_sent` (the full prompt), `tools_sent` (available actions), and `response_messages` (what the LLM chose to do)
5. If an action was called, find the corresponding `FunctionStep` — compare inputs sent and outputs received
6. Check `ReasoningStep` — did the response pass grounding?
7. Look for `TransitionStep` — did the agent move to another subagent?
8. Check `PlannerResponseStep` — what did the user receive?

### The LLMStep in Detail

The `LLMStep` is the most diagnostic step type. It contains:

- `agent_name` — which subagent or router is running
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

Use the **transcript** to quickly identify WHICH turn failed (unexpected response, wrong subagent, agent crash).

Use the **trace files** when:
- The agent routes to the wrong subagent
- An action isn't firing
- The response is unexpectedly worded
- Grounding is failing
- You need to understand variable values at a specific point in execution
- You need to see what the LLM actually saw in its prompt

The transcript is sufficient for conversation-level understanding. Traces provide execution-level detail needed for diagnosis.

### Trace Diagnostic Checks

Use these `jq` commands against trace files (`traces/<PLAN_ID>.json`) to quickly extract diagnostic information.

#### Check 1: Subagent Routing

```bash
jq '[.steps[] | select(.stepType == "TransitionStep") | .data.to]' "$TRACE"
```

**Expected**: Array contains the target subagent name (e.g., `["order_mgmt"]`). Empty array means the agent stayed in Subagent Router — subagent descriptions are too vague. Wrong subagent name means keyword overlap between subagents.

#### Check 2: Action Invocation

```bash
jq '[.steps[] | select(.stepType == "FunctionStep") | .data.function]' "$TRACE"
```

**Expected**: Array contains the target action name. If missing: `available when:` guards too restrictive, action `description:` doesn't match user request, or action not listed in `reasoning.actions:` for this subagent.

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

**Expected**: Array includes the action names defined in the subagent's `reasoning.actions:`. If missing: `available when:` conditions not met, action defined in wrong subagent, or action `target:` protocol invalid (flow not deployed, apex class not found).

---

## 5. Diagnostic Patterns

These patterns map symptoms to trace analysis techniques. Each pattern follows the same structure: symptom → which trace steps to examine → root cause → fix (with code example).

### Pattern: Wrong Subagent Routing

**Symptom:** The agent enters the wrong subagent. For example, asking about weather sends the agent to the events subagent instead.

**Trace Analysis:**

1. Find the `LLMStep` where `agent_name` is `agent_router` (the entry point that routes to subagents)
2. Examine `tools_sent` — are the transition actions for all expected subagents listed? (e.g., `go_to_local_weather`, `go_to_local_events`, `go_to_resort_hours`)
3. Examine `response_messages` — which action tool did the LLM select?
4. Examine `messages_sent` — does the system prompt (what subagent router instructions were compiled to) give the LLM enough context to route correctly?

**Root Cause:** Subagent router instructions are ambiguous, missing context, or don't map user requests to the correct subagents.

**Fix:** A minimal subagent router with well-named actions often routes correctly. When it doesn't, add routing instructions and action descriptions to give the LLM more context:

```agentscript
# BEFORE — relies on action names alone for routing
start_agent agent_router:
    description: "Route to appropriate subagents"
    reasoning:
        actions:
            go_to_weather: @utils.transition to @subagent.local_weather
            go_to_events: @utils.transition to @subagent.local_events

# AFTER — explicit instructions and descriptions improve routing accuracy
start_agent agent_router:
    description: "Route to appropriate subagents"
    reasoning:
        instructions: ->
            | If the user asks about weather conditions, temperature, or forecasts, go to the weather subagent.
              If the user asks about local events, activities, or entertainment, go to the events subagent.
              If the user asks about facility hours, reservations, or amenities, go to the hours subagent.

        actions:
            go_to_weather: @utils.transition to @subagent.local_weather
                description: "Route to weather subagent for weather questions"
            go_to_events: @utils.transition to @subagent.local_events
                description: "Route to events subagent for local event questions"
            go_to_hours: @utils.transition to @subagent.resort_hours
                description: "Route to hours subagent for facility hours questions"
```


### Pattern: Actions Not Firing

**Symptom:** The agent doesn't call an action you expect it to. For example, the agent should fetch data but responds without calling the action.

**Trace Analysis:**

1. Find the `EnabledToolsStep` for the subagent — is the expected action listed?
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

# CORRECT — let the action slot-fill from the current turn and history
reasoning:
    instructions: ->
        | If the guest has not shared an interest, ask one concise question.
          Otherwise use the latest interest in the conversation to look up
          matching events in this turn.

    actions:
        check_events: @actions.check_events
            description: "Look up local events matching the guest's interests"
            with Event_Type = ...
```


### Pattern: Behavioral Loops

**Symptom:** The agent keeps asking the same question or repeating the same response across multiple turns, even though the user already provided the requested information.

**Diagnosis:** Observe the conversation output first — the behavioral symptom
is often obvious (e.g., the agent asking the same question repeatedly). Check
the exact messages sent to the model. A common cause is an instruction that
always asks rather than first using surviving conversation history. Another is
stale mutable state overriding a later correction.

**Fix Example:** In this real scenario, the `local_events` subagent asks about interests and then looks up events. But each time the subagent is re-entered, the agent asks about interests again instead of checking whether it already knows them:

```agentscript
# BEFORE — agent asks about interests every time the subagent is entered
reasoning:
    instructions: ->
        | If you do not already know the guest's interests, ask them about their
          interests so you can provide relevant event information.
          Use the {!@actions.check_events} action to get a list of events once
          you know what the guest is interested in.

    actions:
        check_events: @actions.check_events
            with Event_Type = ...

# AFTER — use history directly and slot-fill the latest value
reasoning:
    instructions: ->
        | Use the guest's latest stated interest from the conversation to call
          {!@actions.check_events} and present matching events. Ask one concise
          question only when no interest appears in the surviving history. If
          the guest corrects an earlier interest, use the correction.

    actions:
        check_events: @actions.check_events
            description: "Find events for the guest's latest stated interest"
            with Event_Type = ...
```

The key difference: the AFTER version treats surviving history as conversational
memory and lets the action slot-fill the latest value. Add mutable state only
if a later deterministic consumer needs a canonicalized interest after the
history window; do not duplicate the conversation merely to prevent re-asking.

Note: repeated `LLMStep` → `ReasoningStep` pairs in a trace may indicate grounding retry rather than a behavioral loop — see Diagnostic Workflow: Grounding subsection.

### Pattern: "Unexpected Error" Responses

**Symptom:** The agent returns "I apologize, but I encountered an unexpected error" instead of a normal response.

**Trace Analysis:**

1. Find the `PlannerResponseStep` — is the message the system error message?
2. Look backward through the trace for consecutive `ReasoningStep` entries with `category: "UNGROUNDED"` — two consecutive UNGROUNDED results cause this error
3. If no grounding failures, look for `FunctionStep` entries with error outputs (action execution failed)
4. Check if a subagent transition failed (the target subagent doesn't exist or has a circular reference)

**Root Cause:** Grounding failed twice in a row, OR an action returned an error, OR a subagent transition is misconfigured.

**Fix:** See Diagnostic Workflow: Grounding subsection for grounding failures. For action errors, verify the backing Apex/Flow/Prompt Template is deployed and handles edge cases correctly. For transition errors, verify all referenced subagents exist and are spelled correctly.

### Pattern: Agent Responds with Generic Message but No Data After Successful Action

**Symptom:** Action returns data (visible in `FunctionStep.function.output`) but the agent's text response is empty or generic (e.g., "Here are the results:").

**Trace Analysis:**

1. Check `EnabledToolsStep` — it lists both your defined actions and platform-injected tools. Any tool you did not define is a platform tool.
2. Find the `LLMStep` after the `FunctionStep`. If `response_messages` contains a `tool_invocation` targeting a platform tool instead of a text response, the LLM chose that tool over composing a reply.

**Fix:** Update reasoning instructions to direct the LLM to write specific field values from the action response in its text reply. Name the fields. Block the observed platform tool by name.

### Fix Strategies Quick Reference

| Failure | Target Block | Edit Strategy | Example |
|---------|-------------|---------------|---------|
| Subagent not matched | `subagent X: description:` | Add keywords from test utterance | `"Handle orders"` → `"Handle order queries, order status, package tracking, shipping updates"` |
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
   - Which subagent was selected? (Look at `NodeEntryStateStep`)
   - What state were variables in? (Look at `SessionInitialStateStep` and `VariableUpdateStep`)
   - What actions were available vs. invoked? (Look at `EnabledToolsStep` and `LLMStep` response)
   - What did the LLM see in its prompt? (Look at `LLMStep.messages_sent`)
   - What did it respond with? (Look at `LLMStep.response_messages`)
   - Did the response pass grounding? (Look at `ReasoningStep.category`)

5. **Identify the Gap** — Compare expected behavior to actual execution at each step. Use the diagnostic patterns (Section 5) to map symptoms to root causes.

6. **Fix** — Update Agent Script instructions, variable logic, or action definitions based on what you found.

7. **Validate** — Run `sf agent validate authoring-bundle --json --api-name <AGENT_NAME>` to ensure the fix doesn't introduce syntax errors.

8. **Re-Test** — Run a new preview session with the same input and compare traces. Verify the fix resolved the issue.


### Grounding

Grounding is a platform service that validates an agent's response against real action output data. When grounding fails, the platform gives the LLM a second chance. Understanding how grounding works, why it fails, and how to fix it is critical for behavioral diagnosis.

#### The Grounding Retry Mechanism

When the platform's grounding checker flags a response as UNGROUNDED:

1. The system injects an error message as a `role: "user"` message:
   ```text
   Error: The system determined your original response was ungrounded.
   Reason the response was flagged: [explanation]
   Try again. Make sure to follow all system instructions.
   Original query: [original user message]
   ```
2. The LLM is given another chance to respond
3. If the second attempt is also UNGROUNDED, the agent returns the system error message ("I apologize, but I encountered an unexpected error") and gives up
4. This retry is visible in traces as repeated `LLMStep` → `ReasoningStep` pairs for the same subagent
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

```text
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
