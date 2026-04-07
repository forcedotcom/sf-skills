<!-- Parent: adlc-author/SKILL.md -->
# Instruction Resolution

> How Agent Script instructions are processed at runtime: from static text to dynamic LLM prompts.

---

## 1. Three Phases of Instruction Resolution

Agent Script instructions go through three distinct phases at runtime. Understanding these phases is critical for writing effective instructions and debugging unexpected behavior.

```
Phase 1: Pre-LLM Setup
   (deterministic -- runs before the LLM sees anything)
       |
       v
Phase 2: LLM Reasoning
   (non-deterministic -- LLM processes the assembled prompt)
       |
       v
Phase 3: Post-Action Loop
   (deterministic -- runs after an action completes, then loops back to Phase 1)
```

---

## 2. Phase 1: Pre-LLM Resolution

During Phase 1, the Agent Script runtime evaluates deterministic constructs in `instructions: ->` blocks. This happens BEFORE the LLM sees any text.

### What Happens in Phase 1

1. **`if`/`else` evaluation**: Conditions are evaluated against current variable values. Only the matching branch is included in the prompt.
2. **Variable injection**: `{!@variables.X}` tokens are replaced with current values.
3. **`run` execution**: Deterministic `run @actions.X` calls execute and their outputs are captured.
4. **`set` execution**: Variable assignments execute immediately.
5. **`transition to`**: If reached, the topic switch happens immediately (LLM is never called).

### Phase 1 Example

Given this instruction block:

```
reasoning:
   instructions: ->
      # 1. Post-action check (from previous loop)
      if @variables.refund_approved == True:
         | Your refund has been processed. Reference: {!@variables.refund_id}
         transition to @topic.confirmation

      # 2. Pre-LLM data loading
      if @variables.data_loaded == False:
         run @actions.load_customer_profile
            with customer_id = @variables.customer_id
            set @variables.risk_score = @outputs.risk_score
            set @variables.tier = @outputs.tier
         set @variables.data_loaded = True

      # 3. Dynamic instructions
      | Customer tier: {!@variables.tier}, Risk score: {!@variables.risk_score}

      if @variables.risk_score >= 80:
         | HIGH RISK -- Offer full cash refund to retain this customer.
         | Do NOT offer store credit. Prioritize retention.

      if @variables.risk_score < 80:
         | STANDARD -- Offer $10 store credit as goodwill.
         | Only escalate to cash refund if customer insists.
```

**First turn resolution** (variables at defaults):

- `refund_approved == True` -> False. Skip this block.
- `data_loaded == False` -> True. Execute `run @actions.load_customer_profile`. Variables now set.
- Set `data_loaded = True`.
- Inject `{!@variables.tier}` -> `"gold"`, `{!@variables.risk_score}` -> `85`.
- `risk_score >= 80` -> True. Include high-risk instructions.
- `risk_score < 80` -> False. Skip standard instructions.

**What the LLM actually sees**:
```
Customer tier: gold, Risk score: 85
HIGH RISK -- Offer full cash refund to retain this customer.
Do NOT offer store credit. Prioritize retention.
```

---

## 3. Phase 2: LLM Processing

In Phase 2, the LLM receives the assembled prompt and produces a response. The LLM sees:

### The 4-Message Prompt Structure

The Agent Script runtime assembles a 4-message prompt for the LLM:

| # | Message Role | Content Source | Purpose |
|---|---|---|---|
| 1 | **System** | `system: instructions:` + agent metadata | Global persona, safety rules, capabilities |
| 2 | **System** | `topic: reasoning: instructions:` (resolved from Phase 1) | Topic-specific operating instructions |
| 3 | **User/Assistant** | Conversation history (all turns) | Context for the current request |
| 4 | **System** | Available actions + their descriptions | Tool palette the LLM can choose from |

### What the LLM Decides

Based on the assembled prompt, the LLM:

1. **Selects an action** (if applicable) from the available actions list
2. **Fills slot parameters** (`...` values) from conversation context
3. **Generates a text response** to send to the user
4. **Decides whether to transition** (if a transition action is available and appropriate)

### What the LLM Does NOT See

- Raw `if`/`else` blocks (already resolved in Phase 1)
- `run` statements (already executed in Phase 1)
- `set` statements (already executed)
- `available when` conditions (already evaluated -- hidden actions are simply absent)
- `after_reasoning` blocks (run after the LLM, not shown to it)

---

## 4. Phase 3: Post-Action Loop

After the LLM selects and executes an action, the system loops back to Phase 1 for **re-resolution**. This is the post-action loop pattern described in the SKILL.md architecture section.

### Loop Sequence

```
1. Phase 1 resolves instructions (first time)
2. Phase 2: LLM reasons and selects an action
3. Action executes -> outputs captured in variables
4. Phase 1 re-resolves instructions (with updated variables)
   - Post-action checks at TOP of instructions fire
   - New data is injected into the prompt
5. Phase 2: LLM reasons again with updated context
6. Repeat until: transition, escalation, or no action selected
```

### Why Post-Action Checks Go at the TOP

Place post-action checks at the TOP of `instructions: ->` so they fire immediately on re-resolution:

```
reasoning:
   instructions: ->
      # POST-ACTION CHECK (at TOP -- fires on re-resolution)
      if @variables.order_cancelled == True:
         | Your order has been cancelled successfully.
         transition to @topic.confirmation

      # These instructions are for the FIRST entry (before action runs)
      | I can help you cancel your order.
      | What is your order number?
```

If the check were at the BOTTOM, the LLM would see the "ask for order number" instructions again even after the cancellation succeeded, causing confusion.

---

## 5. Recommended Instruction Order

Within a `instructions: ->` block, follow this order for maximum clarity:

```
reasoning:
   instructions: ->
      # 1. POST-ACTION CHECKS (deterministic transitions)
      if @variables.action_completed == True:
         transition to @topic.next_step

      # 2. PRE-LLM DATA LOADING (deterministic actions)
      if @variables.data_needed == True:
         run @actions.load_data
            with id = @variables.record_id
            set @variables.loaded_data = @outputs.result

      # 3. CONDITIONAL INSTRUCTIONS (based on state)
      if @variables.is_verified == True:
         | Full access granted. You can:
         | - View account details
         | - Make changes
         | - Request refunds

      if @variables.is_verified == False:
         | Please verify your identity first.
         | I need your email address and order number.

      # 4. STATIC INSTRUCTIONS (always included)
      | Be concise and professional.
      | Always confirm before making changes.
```

---

## 6. Common Instruction Patterns

### Pattern 1: Security Gate

Prevent access to sensitive actions until identity is verified:

```
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

```
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

```
reasoning:
   instructions: ->
      # Post-action check: case was created in previous loop
      if @variables.case_id != "":
         | Case {!@variables.case_id} has been created.
         run @actions.assign_case
            with case_id = @variables.case_id
            with priority = @variables.priority
         transition to @topic.case_confirmation

      | I need to collect some information to create a support case.
      | What is the issue you're experiencing?
```

### Pattern 4: Multi-Condition Routing

Route based on multiple variable values:

```
reasoning:
   instructions: ->
      if @variables.intent == "billing" and @variables.is_verified == True:
         | I can help with your billing question.
         transition to @topic.billing_support

      if @variables.intent == "billing" and @variables.is_verified == False:
         | For billing questions, I need to verify your identity first.
         transition to @topic.identity_verification

      if @variables.intent == "general":
         | How can I help you today?
```

---

## 7. Anti-Patterns to Avoid

### Anti-Pattern 1: Nested If Blocks

```
# WRONG -- Agent Script does not support nested if or else if
if @variables.tier == "gold":
   if @variables.is_verified == True:
      | VIP treatment
   else:
      | Verify first

# CORRECT -- Use compound conditions
if @variables.tier == "gold" and @variables.is_verified == True:
   | VIP treatment

if @variables.tier == "gold" and @variables.is_verified == False:
   | Verify first
```

### Anti-Pattern 2: Post-Action Check at Bottom

```
# WRONG -- Check at bottom; LLM sees stale instructions on re-resolution
reasoning:
   instructions: ->
      | What is your order number?

      if @variables.order_status != "":
         transition to @topic.show_status

# CORRECT -- Check at TOP
reasoning:
   instructions: ->
      if @variables.order_status != "":
         transition to @topic.show_status

      | What is your order number?
```

### Anti-Pattern 3: Persona in Topic Instructions

```
# WRONG -- Persona text duplicated in every topic
reasoning:
   instructions: |
      You are a friendly, professional customer service agent.
      Help the customer with their order.

# CORRECT -- Persona in system instructions, topic has operational instructions only
system:
   instructions: |
      You are a friendly, professional customer service agent.

topic order_support:
   reasoning:
      instructions: ->
         | Help the customer check their order status.
         | Ask for the order number if not provided.
```

### Anti-Pattern 4: Using `|` When `->` Is Needed

```
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

```
# WRONG -- Variable name as literal text
reasoning:
   instructions: ->
      | Your order ID is @variables.order_id

# CORRECT -- Use injection syntax
reasoning:
   instructions: ->
      | Your order ID is {!@variables.order_id}
```

### Anti-Pattern 6: `run` Inside `after_reasoning`

While `run` compiles inside `after_reasoning:`, its runtime behavior is inconsistent across bundle types. Prefer using `run` in `reasoning: instructions: ->` or `reasoning: actions:` instead.

```
# RISKY -- run in after_reasoning has inconsistent behavior
after_reasoning:
   run @actions.log_event
      with event = "turn_completed"

# SAFER -- Use instructions: -> for deterministic runs
reasoning:
   instructions: ->
      # Post-action logging
      if @variables.last_action != "":
         run @actions.log_event
            with event = @variables.last_action
```

---

## 8. Syntax Patterns Reference

### Literal Mode (`|`)

Static text passed directly to the LLM. No evaluation occurs:

```
instructions: |
   Help the customer with their order.
   Be professional and concise.
```

Or with the `|` prefix on each line (inside procedural mode):

```
instructions: ->
   | Help the customer with their order.
   | Be professional and concise.
```

### Procedural Mode (`->`)

Enables conditionals, variable injection, and deterministic actions:

```
instructions: ->
   if @variables.condition == True:
      | Text shown when condition is true.
   else:
      | Text shown when condition is false.
```

### Variable Injection

```
| Your order {!@variables.order_id} is {!@variables.status}.
```

### Deterministic Run

```
run @actions.load_data
   with param = @variables.value
   set @variables.result = @outputs.field
```

### Deterministic Set

```
set @variables.counter = @variables.counter + 1
```

### Deterministic Transition

```
transition to @topic.next_topic
```

### Conditional Transition

```
if @variables.all_collected == True:
   transition to @topic.confirmation
```

---

## 9. Programmatic Trace Access

To verify how instructions were resolved at runtime, use the trace files generated by `sf agent preview`.

### Trace File Location

```
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

### Verifying Phase 1 Resolution

To confirm that `if`/`else` blocks resolved correctly, compare the trace's `LLM_STEP` input against your `instructions: ->` block. The LLM input should contain only the branches that matched, with all `{!@variables.X}` tokens replaced with actual values.

If the trace shows unexpected instruction text:
1. Check that you used `->` mode (not `|` mode) when conditionals are present
2. Verify variable values at the time of resolution (check `preVars` on preceding `ACTION_STEP`)
3. Confirm that `if` conditions use the correct comparison operators

### Using STDM for Production Trace Analysis

For production agents, use the Session Trace Data Model (STDM) in Data Cloud to access trace data programmatically. The STDM captures `LLM_STEP` records with `input` and `output` fields that contain the resolved prompt and LLM response. This is useful for auditing instruction resolution at scale across hundreds of live sessions.

---

## 10. Resolution Across Topic Transitions

When a topic transition occurs (via `@utils.transition to @topic.X` or `transition to @topic.X`), instruction resolution starts fresh in the new topic:

1. The current topic's remaining instructions are NOT processed
2. The new topic's `before_reasoning:` runs (if present)
3. The new topic's `reasoning: instructions:` resolves from Phase 1
4. The LLM receives the new topic's assembled prompt

**Important**: Variables persist across transitions. A variable set in Topic A is available in Topic B. This is how you pass data between topics:

```
# Topic A: Collect data
topic collect_info:
   reasoning:
      instructions: ->
         | Please provide your order number.
      actions:
         capture_order: @actions.get_order_id
            with input = ...
            set @variables.order_id = @outputs.order_id

   after_reasoning:
      if @variables.order_id != "":
         transition to @topic.process_order

# Topic B: Use the data
topic process_order:
   reasoning:
      instructions: ->
         # order_id is available from Topic A
         | Processing order {!@variables.order_id}...
         run @actions.get_order_details
            with order_id = @variables.order_id
            set @variables.order_status = @outputs.status
```
