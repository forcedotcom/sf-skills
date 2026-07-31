<!-- Parent: adlc-author/SKILL.md -->
# Instruction Resolution

> How Agent Script instructions are processed at runtime: from static text to dynamic LLM prompts.

---

## 1. Runtime Lifecycle

AgentScript defines deterministic lifecycle hooks around an iterative LLM
reasoning loop:

```text
before_reasoning (once per turn)
    -> resolve reasoning.instructions (every reasoning iteration)
    -> LLM calls a tool or produces a user response
       -> tool call: execute it, then resolve reasoning.instructions again
       -> response: end the loop
    -> after_reasoning (once, if execution reaches the hook)
```

Do not confuse a new reasoning iteration after a tool call with
`after_reasoning`. The latter does not run after each tool.

---

## 2. Instruction Surfaces

| Surface | Runtime meaning | Authoring use |
|---|---|---|
| Global `system.instructions` | Default system prompt for every execution block | Durable identity, safety, scope, and response invariants |
| Subagent `system.instructions` | Replaces the global system prompt for that subagent; it does not merge | Rare specialist override that restates every invariant still required |
| `reasoning.instructions` | Runtime-resolved instructions rebuilt on every reasoning iteration | Current objective, relevant state, action guidance, and stop conditions |
| `before_reasoning` | Deterministic procedure that runs once before the reasoning loop | Preconditions, data preparation, and early transitions |
| `after_reasoning` | Deterministic procedure that runs if execution reaches the hook after the reasoning loop | Final state updates and post-response transitions |

Omit a subagent system override when the global instructions already apply. If
an override is necessary, copy the durable invariants that subagent must retain;
the compiler selects the subagent value instead of the global value.

Treat effective system and reasoning instructions as cumulative. Do not depend
on a model provider separating or prioritizing the AgentScript surfaces
differently unless the target runtime's public, versioned contract guarantees
that behavior. Their combined meaning must contain no contradiction, duplicate
policy, or reliance on one layer overriding the other.

### Separate AgentScript Control from Model Instructions

Subagents and variables are AgentScript runtime concepts, not model knowledge.
The compiler and runtime select the current execution block, evaluate
conditions, run deterministic actions, update state, interpolate values, and
expose the currently available tools. Portable model instructions must not
depend on a provider exposing structured execution-block identity or direct
variable-store access unless the target runtime's public contract guarantees
it.

Developer documentation may explain subagents and variables because authors
need that mental model. Text sent to the model must instead state the concrete
task and response duty. Do not tell the model to inspect the active subagent or
read `@variables`.

### Scope Response Duties by Branch

Do not put an unconditional response duty in the global layer when any branch
must route, verify, clarify, refuse, close, or escalate without answering. This
conflict is especially common in router-first agents:

```agentscript
# WRONG: the effective prompt says both answer and do not answer.
system:
    instructions: "Answer the user's questions helpfully."
start_agent agent_router:
    reasoning:
        instructions: ->
            | Do not answer. Route the request.

# RIGHT: the global rule allows the current operating task to set posture.
system:
    instructions: |
        Perform only the current operating task described below. Answer the
        underlying request only when that task calls for an answer. Otherwise
        route, verify, clarify, refuse, or escalate as directed.
```

Review the effective pair for every execution branch: global or replacement
system instructions plus the branch's resolved reasoning instructions. A scope
narrowing is compatible only when the global layer already permits that
narrowing. For every reachable LLM call, that effective pair must prescribe one
unambiguous response posture. A subagent system replacement must restate every
durable invariant it retains.

### Deterministic Resolution Before Each LLM Call

Before every reasoning iteration, the runtime evaluates deterministic
constructs in `reasoning.instructions: ->`. This happens before the LLM sees
the resolved reasoning instructions.

### What Happens During Resolution

1. **`if`/`else` evaluation**: Conditions are evaluated against current variable values. Only the matching branch is included in the prompt.
2. **Variable injection**: `{!@variables.X}` tokens are replaced with current values.
3. **`run` execution**: Deterministic `run @actions.X` calls execute and their outputs are captured.
4. **`set` execution**: Variable assignments execute immediately.
5. **`transition to`**: If reached, the subagent switch happens immediately (LLM is never called).

### Resolution Example

Given this instruction block:

```agentscript
reasoning:
   instructions: ->
      # Completed-state check from a previous tool call
      if @variables.order_status != "":
         | Report order status {!@variables.order_status}, then stop.
         transition to @subagent.confirmation

      | Collect the order number, then use {!@actions.lookup_order} once.
```

Before lookup, the LLM sees only:
```text
Collect the order number, then use lookup_order once.
```

After the tool stores `order_status`, the instructions are rebuilt. The
completed-state branch resolves and transitions without asking the LLM to call
the tool again.

---

## 3. LLM Processing

AgentScript guarantees the authored semantics, not an exact provider message
count. Reasoning receives:

- One authored node-instruction value: the subagent system override when
  present, otherwise the global `system.instructions`. Runtime base prompts and
  metadata may add other system content outside AgentScript.
- Conversation history.
- The resolved `reasoning.instructions`, when non-empty.
- The currently available tools and their schemas.

Do not document or test an exact four-message structure. Tool schemas are not
necessarily encoded as a chat message, and message transport is not the
AgentScript authoring contract.

### What the LLM Decides

Based on the assembled prompt, the LLM:

1. **Selects an action** (if applicable) from the available actions list
2. **Fills slot parameters** (`...` values) from conversation context
3. **Generates a text response** to send to the user
4. **Decides whether to transition** (if a transition action is available and appropriate)

### What the LLM Does NOT See

- Raw `if`/`else` blocks (already resolved before the iteration)
- Structured AgentScript execution-block identity or direct variable-store
  access unless the target runtime explicitly provides it
- `run` statements (already executed before the iteration)
- `set` statements (already executed)
- `available when` conditions (already evaluated -- hidden actions are simply absent)
- `after_reasoning` blocks (run after the LLM, not shown to it)

---

## 4. Tool Loop and Re-Resolution

After the LLM selects and executes a tool, the runtime begins another reasoning
iteration and rebuilds `reasoning.instructions` from current state.

### Loop Sequence

```text
1. Resolve reasoning instructions
2. LLM reasons and selects a tool
3. Action executes -> outputs captured in variables
4. Re-resolve reasoning instructions with updated variables
   - Post-action checks at TOP of instructions fire
   - New data is injected into the prompt
5. LLM reasons again with updated context
6. Repeat until a transition occurs or the LLM produces a user response
```

Only after the LLM produces a user response does the reasoning loop end and
`after_reasoning` run.

### Why Post-Action Checks Go at the TOP

Place post-action checks at the TOP of `instructions: ->` so they fire immediately on re-resolution:

```agentscript
reasoning:
   instructions: ->
      # POST-ACTION CHECK (at TOP -- fires on re-resolution)
      if @variables.order_cancelled == True:
         | Your order has been cancelled successfully.
         transition to @subagent.confirmation

      # These instructions are for the FIRST entry (before action runs)
      | I can help you cancel your order.
      | What is your order number?
```

If the check were at the BOTTOM, the LLM would see the "ask for order number" instructions again even after the cancellation succeeded, causing confusion.

---

## 5. Concise Reasoning Instructions

Keep `reasoning.instructions` task-local. Include only information that can
change the current tool choice or response:

1. Checks backed by trusted outcomes or material invariants.
2. Deterministic data loading required for this iteration.
3. The current objective and only the resolved state it consumes.
4. Action guidance, exclusions, and a stop condition.

Do not add a variable or branch merely to remind the model what happened in
surviving conversation history.

Keep persona, tone, disclosure, safety, and broad scope rules in the effective
system layer. Put tool-specific trigger details in action descriptions instead
of repeating them in the reasoning instructions.

```agentscript
reasoning:
   instructions: ->
      # Trusted verification output controls the protected capability.
      if @variables.is_verified == True:
         | Complete the requested account task using the available action once.

      if @variables.is_verified == False:
         | Ask for the minimum information needed to verify identity. Do not use account-changing actions.
```

---

## 6. Common Instruction Patterns

### Pattern 1: Security Gate

Prevent access to sensitive actions until identity is verified:

```agentscript
reasoning:
   instructions: ->
      if @variables.is_verified == False:
         | You must verify your identity before I can help with account changes.
         | Please provide your email address.

      if @variables.is_verified == True:
         | Identity verified. I can now help with account changes.
         | What would you like to do?

   actions:
      update_account: @actions.update_account_info
         description: "Update account information"
         available when @variables.is_verified == True
         with field = ...
         with value = ...
```

The `available when` guard hides the action from the LLM until verification passes. The conditional instructions tell the user what to do.

### Pattern 2: Data-Dependent Instructions

Load data first, then tailor instructions based on the result:

```agentscript
reasoning:
   instructions: ->
      run @actions.get_account_status
         with account_id = @variables.account_id
         set @variables.account_status = @outputs.status
         set @variables.balance = @outputs.balance

      | Account status: {!@variables.account_status}
      | Current balance: {!@variables.balance}

      if @variables.account_status == "delinquent":
         | IMPORTANT: This account is delinquent.
         | Collect payment before processing any other requests.
         | Offer payment plan options if customer cannot pay in full.

      if @variables.account_status == "active":
         | This account is in good standing.
         | Process requests normally.
```

### Pattern 3: Action Chaining

Execute one action, then use its output to drive the next:

```agentscript
reasoning:
   instructions: ->
      # Post-action check: case was created in previous loop
      if @variables.case_id != "":
         | Case {!@variables.case_id} has been created.
         run @actions.assign_case
            with case_id = @variables.case_id
            with priority = @variables.priority
         transition to @subagent.case_confirmation

      | I need to collect some information to create a support case.
      | What is the issue you're experiencing?
```

### Pattern 4: Machine-Known Gate

Use compound conditions when trusted machine state controls a material
capability. Do not persist the user's current intent merely to route it; let the
router infer current intent from the latest turn and conversation history.

```agentscript
reasoning:
   instructions: ->
      if @variables.is_verified == True and @variables.account_locked == False:
         | Complete the requested account task using the available action.

      if @variables.is_verified == False:
         | Ask for the minimum information needed to verify identity.

      if @variables.account_locked == True:
         | Do not use account-changing actions. Explain how to unlock the
           account or escalate.
```

---

## 7. Anti-Patterns to Avoid

### Anti-Pattern 1: Re-Explaining Language Syntax

Keep this reference focused on instruction resolution. For supported
`if / else if / else`, invalid `elif`, nested-condition limitations, and
post-action conditionals, use the canonical
[Conditional Control Flow Syntax](agent-script-core-language.md#conditional-control-flow-syntax)
section.

### Anti-Pattern 2: Post-Action Check at Bottom

```agentscript
# WRONG -- Check at bottom; LLM sees stale instructions on re-resolution
reasoning:
   instructions: ->
      | What is your order number?

      if @variables.order_status != "":
         transition to @subagent.show_status

# CORRECT -- Check at TOP
reasoning:
   instructions: ->
      if @variables.order_status != "":
         transition to @subagent.show_status

      | What is your order number?
```

### Anti-Pattern 3: Persona in Subagent Instructions

```text
# WRONG -- Persona text duplicated in every subagent
reasoning:
   instructions: |
      You are a friendly, professional customer service agent.
      Help the customer with their order.

# CORRECT -- Persona in system instructions, subagent has operational instructions only
system:
   instructions: |
      You are a friendly, professional customer service agent.

subagent order_support:
   reasoning:
      instructions: ->
         | Help the customer check their order status.
         | Ask for the order number if not provided.
```

### Anti-Pattern 4: Using `|` When `->` Is Needed

```agentscript
# WRONG -- Using literal mode when conditionals are needed
reasoning:
   instructions: |
      if @variables.is_verified == True:
         Show account details.

# The above sends the literal text "if @variables.is_verified == True:" to the LLM!

# CORRECT -- Use procedural mode for conditionals
reasoning:
   instructions: ->
      if @variables.is_verified == True:
         | Show account details.
```

### Anti-Pattern 5: Missing Variable Injection Syntax

```agentscript
# WRONG -- Variable name as literal text
reasoning:
   instructions: ->
      | Your order ID is @variables.order_id

# CORRECT -- Use injection syntax
reasoning:
   instructions: ->
      | Your order ID is {!@variables.order_id}
```

### Pattern: `after_reasoning` Lifecycle Actions

`run` is supported in `after_reasoning` through the common action mechanism.
The block runs after the reasoning loop ends, including a turn where the model
produced a response without calling a tool. Use it only when the follow-up must
run after every completed reasoning pass.

Do not use this lifecycle hook for an irreversible action merely because it is
deterministic; consequential-action preconditions still need explicit guards.

```agentscript
# Log every completed reasoning turn.
after_reasoning:
   run @actions.log_event
      with event = "turn_completed"
```

### Anti-Pattern 7: Prose-Based Conditional Logic

```agentscript
# WRONG -- Conditional behavior described in prose; the LLM must interpret
# these directives and may ignore, reorder, or misapply them
reasoning:
   instructions: ->
      | If the user is a VIP, offer priority support.
      | If they haven't been verified, ask for verification first.
      | If the refund has been approved, confirm it and end the conversation.
      | Check availability before booking.

# CORRECT when the conditions are trusted machine facts protecting material
# invariants. The LLM sees only the matching operating instructions.
reasoning:
   instructions: ->
      if @variables.refund_approved == True:
         | Your refund has been confirmed. Reference: {!@variables.refund_id}
         transition to @subagent.confirmation

      if @variables.customer_verified == False:
         | I need to verify your identity before proceeding.
         | Please provide your email address.

      if @variables.customer_tier == "vip":
         | As a VIP customer, you have access to priority support.

      | How can I help you today?
```

Why this matters: machine-known authorization, confirmation, action-result, and
external-ordering conditions must not depend on model discretion. AgentScript
resolves those branches before the model sees the prompt.

Do not manufacture state merely so conversational judgment can become an
`if/else`. Use a deterministic branch only when a named runtime consumer and
material cause justify it. Reserve prose for current intent, tone, phrasing,
and other decisions the model should interpret from the conversation.

---

## 8. Syntax Patterns Reference

### Literal Mode (`|`)

Static text passed directly to the LLM. No evaluation occurs:

```agentscript
instructions: |
   Help the customer with their order.
   Be professional and concise.
```

Or with the `|` prefix on each line (inside procedural mode):

```agentscript
instructions: ->
   | Help the customer with their order.
   | Be professional and concise.
```

### Procedural Mode (`->`)

Enables conditionals, variable injection, and deterministic actions:

```agentscript
instructions: ->
   if @variables.condition == True:
      | Text shown when condition is true.
   else:
      | Text shown when condition is false.
```

### Variable Injection

```agentscript
| Your order {!@variables.order_id} is {!@variables.status}.
```

### Deterministic Run

```agentscript
run @actions.load_data
   with param = @variables.value
   set @variables.result = @outputs.field
```

### Deterministic Set

```agentscript
set @variables.counter = @variables.counter + 1
```

### Deterministic Transition

```agentscript
transition to @subagent.next_subagent
```

### Conditional Transition

```agentscript
if @variables.all_collected == True:
   transition to @subagent.confirmation
```

---

## 9. Programmatic Trace Access

To verify how instructions were resolved at runtime, use the trace files generated by `sf agent preview`.

### Trace File Location

```text
.sfdx/agents/{BundleName}/sessions/{sessionId}/traces/{planId}.json
```

### Reading Instruction Resolution from Traces

```bash
# Extract the resolved instructions that the LLM received
jq -r '.planTrace.steps[] | select(.type == "LLM_STEP") | .input' \
  ~/.sf/sfdx/agents/MyAgent/sessions/*/traces/*.json

# Extract the LLM's response
jq -r '.planTrace.steps[] | select(.type == "LLM_STEP") | .output' \
  ~/.sf/sfdx/agents/MyAgent/sessions/*/traces/*.json

# Check which variables were set during resolution
jq -r '.planTrace.steps[] | select(.type == "ACTION_STEP") | {name: .name, pre: .preVars, post: .postVars}' \
  ~/.sf/sfdx/agents/MyAgent/sessions/*/traces/*.json
```

### Verifying Per-Iteration Resolution

To confirm that `if`/`else` blocks resolved correctly, compare the trace's `LLM_STEP` input against your `instructions: ->` block. The LLM input should contain only the branches that matched, with all `{!@variables.X}` tokens replaced with actual values.

If the trace shows unexpected instruction text:
1. Check that you used `->` mode (not `|` mode) when conditionals are present
2. Verify variable values at the time of resolution (check `preVars` on preceding `ACTION_STEP`)
3. Confirm that `if` conditions use the correct comparison operators

### Using STDM for Production Trace Analysis

For production agents, use the Session Trace Data Model (STDM) in Data Cloud to access trace data programmatically. The STDM captures `LLM_STEP` records with `input` and `output` fields that contain the resolved prompt and LLM response. This is useful for auditing instruction resolution at scale across hundreds of live sessions.

---

## 10. Resolution Across Subagent Transitions

When a subagent transition occurs (via `@utils.transition to @subagent.X` or `transition to @subagent.X`), instruction resolution starts fresh in the new subagent:

1. The current subagent's remaining instructions are NOT processed
2. The new subagent's `before_reasoning:` runs (if present)
3. The new subagent's `reasoning: instructions:` resolves for its first iteration
4. The LLM receives the new subagent's assembled prompt

**Important**: Variables persist across transitions. A variable set in Subagent A is available in Subagent B. This is how you pass data between subagents:

```agentscript
# Subagent A: Collect data
subagent collect_info:
   reasoning:
      instructions: ->
         | Please provide your order number.
      actions:
         capture_order: @actions.get_order_id
            with input = ...
            set @variables.order_id = @outputs.order_id

   after_reasoning:
      if @variables.order_id != "":
         transition to @subagent.process_order

# Subagent B: Use the data
subagent process_order:
   reasoning:
      instructions: ->
         # order_id is available from Subagent A
         | Processing order {!@variables.order_id}...
         run @actions.get_order_details
            with order_id = @variables.order_id
            set @variables.order_status = @outputs.status
```
