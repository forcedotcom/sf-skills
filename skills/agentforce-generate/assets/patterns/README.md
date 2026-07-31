# Agent Script Patterns

This folder contains reusable patterns for common Agentforce scenarios.

Use `references/patterns-by-requirement.md` first to choose which pattern to apply
for a given requirement. Then use this folder for concrete snippets.

## Pattern Decision Tree

```text
What do you need?
│
├─► Deterministic processing after a normal action result?
│   └─► Use: action-callbacks.agent
│       (run keyword for deterministic callbacks)
│
├─► Setup/cleanup for every reasoning turn?
│   └─► Use: lifecycle-events.agent
│       (before_reasoning / after_reasoning blocks)
│
├─► Navigate to specialist subagent and return with results?
│   └─► Use: bidirectional-routing.agent
│       (store return address, specialist subagent transitions back)
│
├─► Complex parameter passing to actions?
│   └─► Use: advanced-input-bindings.agent
│       (slot filling, variable binding, output chaining)
│
├─► Dynamic behavior based on user context?
│   └─► Use: system-instruction-overrides.agent
│       (tier-based, time-based, feature flag instructions)
│
├─► Several protected handlers share one authentication gate?
│   └─► Use: open-gate-routing.agent
│       (verified proof plus a temporary return address; no focus latch)
│
├─► Later external actions must wait for earlier successful results?
│   └─► Use: multi-step-workflow.agent
│       (action-result gates; no conversational step counter)
│
└─► None of the above?
    └─► Start with: ../agents/hello-world.agent
```

## Patterns Overview

### 1. [action-callbacks.agent](action-callbacks.agent)

**Purpose**: Process a normal parent-action result deterministically with
`run`.

**Use when**:
- A declared follow-up action must run after the parent returns normally
- The callback consumes exact parent outputs
- A returned negative result must be normalized without being presented as
  success

Do not use a callback as evidence that a parent action recovered from an
execution failure. If the parent does not return normally, this pattern does
not establish downstream completion.

**Key syntax**:
```agentscript
track_shipment: @actions.get_shipment_status
    with tracking_number=...
    run @actions.normalize_shipment_result
        with found=@outputs.found
        with status=@outputs.status
```

---

### 2. [lifecycle-events.agent](lifecycle-events.agent)

**Purpose**: Run code once before/after the reasoning loop on each turn.

**Use when**:
- Refresh external context before each response
- Log analytics after each turn
- Apply setup or cleanup that genuinely must run on every reasoning turn

**Key syntax**:
```agentscript
subagent conversation:
   before_reasoning:
      run @actions.refresh_context

   reasoning:
      instructions: ->
         | Answer using the refreshed external context and surviving history.

   after_reasoning:
      run @actions.log_analytics
```

---

### 3. [bidirectional-routing.agent](bidirectional-routing.agent)

**Purpose**: Navigate to a specialist request handler and return with results.

**Use when**:
- Complex workflows spanning multiple subagents
- "Consult an expert" pattern
- A shared specialist must return to one of several possible callers
- Want separation of concerns

**Key syntax**:
```agentscript
# When the return target is fixed, use direct transitions and no state.
consult_pricing: @utils.transition to @subagent.pricing_specialist
return_with_results: @utils.transition to @subagent.main_hub
```

Persist a return address only when the same specialist has multiple possible
callers and runtime logic must choose the correct one.

---

### 4. [advanced-input-bindings.agent](advanced-input-bindings.agent)

**Purpose**: Master all parameter binding techniques for actions.

**Use when**:
- Learning different ways to pass values to actions
- Complex multi-input action scenarios
- Chaining outputs between multiple actions
- Mixing LLM slot filling with stored state

**Key syntax**:
```agentscript
reasoning:
   actions:
      # Slot filling: LLM extracts from conversation
      lookup: @actions.get_order
         with order_id=...

      # Variable binding: Use stored state
      bound: @actions.get_order
         with order_id=@variables.current_order_id

      # Output chaining: Use previous action's result
      process: @actions.create_order
         with items=...
         set @variables.order_id = @outputs.order_id
         run @actions.send_notification
            with order_id=@outputs.order_id    # Chained output
```

**Binding Pattern Quick Reference**:
| Pattern | Syntax | When to Use |
|---------|--------|-------------|
| Slot Filling | `with x=...` | LLM extracts from conversation |
| Fixed Value | `with x="value"` | Always use a constant |
| Variable | `with x=@variables.y` | Use stored state |
| Output | `with x=@outputs.y` | Chain from previous action |

---

### 5. [system-instruction-overrides.agent](system-instruction-overrides.agent)

**Purpose**: Dynamic agent behavior based on context (user tier, time, features).

**Use when**:
- Different behavior for different user segments (VIP vs standard)
- Time-based changes (business hours vs after hours)
- Feature flags controlling agent personality
- A/B testing different conversation styles

**Key syntax**:
```agentscript
# System block: Static base instructions
system:
   instructions: "You are a professional agent. Be helpful and courteous."

# Subagent reasoning: Dynamic overrides
reasoning:
   instructions: ->
      if @variables.customer_tier == "vip":
         | PRIORITY CUSTOMER - Provide white-glove service.
         | You have authority to offer 20% discounts.

      if @variables.business_hours == False:
         | We are outside business hours.
         | Complex issues should be logged for follow-up.

      | Respond to the customer's inquiry.
```

**Override Strategy**:
| Layer | Type | Best For |
|-------|------|----------|
| `system:` | Static | Guardrails, base personality |
| `reasoning:` | Dynamic | Personalization, context-aware behavior |

---

### 6. [open-gate-routing.agent](open-gate-routing.agent)

**Purpose**: Return a verified user to the correct protected request handler
without locking conversational focus.

**Use when**:
- Multiple protected subagents require authentication before access
- Users should be redirected to auth, then automatically returned to their intended subagent
- Verification proof must deterministically guard protected actions
- Cancellation and changed intent must take effect on the next turn

**Key syntax**:
```agentscript
# Protected request handler records only its temporary return address.
if @variables.authenticated == False:
   set @variables.pending_destination = "protected_orders"
   transition to @subagent.authentication

# Successful verification returns deterministically and clears the address.
if @variables.authenticated == True and @variables.pending_destination == "protected_orders":
   set @variables.pending_destination = ""
   transition to @subagent.protected_orders
```

**Credit**: The original open-gate pattern was contributed by Hua Xu
(Salesforce APAC FDE team) from the Kogan agent deployment. This version
preserves the shared verification gate while replacing the conversation focus
lock with fresh-intent routing and an expiring return address.

Do not add an `open_gate`, `active_workflow`, or similar focus latch merely to
bypass reasoning. If only one protected handler exists, use a fixed transition
and omit `pending_destination` too.

---

### 7. [multi-step-workflow.agent](multi-step-workflow.agent)

**Purpose**: Enforce ordering between external actions using their successful
results as the source of truth.

**Use when**:
- A later action would be invalid or unsafe before an earlier external action
- A canonical ID returned by one action is required by later action bindings
- Failure must leave later actions unavailable

**Do not use when**:
- The "steps" are only questions in a conversation
- A `current_step` counter would duplicate per-action completion results
- The goal is to keep a request handler focused despite a changed user intent

**Key syntax**:
```agentscript
save_profile: @actions.update_profile
   with customer_id=@variables.created_customer_id
   with phone=...
   set @variables.profile_saved = @outputs.success

save_preferences: @actions.set_preferences
   with customer_id=@variables.created_customer_id
   with notification_method=...
   available when @variables.profile_saved == True
```

---

## Pattern Combinations

These patterns can be combined:

```text
lifecycle-events + action-callbacks
├── before_reasoning: Initialize context
├── reasoning: Process with callbacks
│   └── action with run callbacks
└── after_reasoning: Log results

authentication-return + lifecycle-events
├── before_reasoning: Verify proof or refresh external context
├── reasoning: Protected actions only when proof is valid
└── after_reasoning: Clear a consumed return address and log the result
```

## Validation and Review Guidance

Patterns are not scored by quantity. More patterns do **not** mean a better agent.

Use a pattern only when a requirement justifies it. Review quality should focus on:

- Requirement fit (pattern solves a real need)
- Correct implementation syntax
- Behavioral reliability in preview traces
- Maintainability (no unnecessary complexity)

| Pattern | What reviewers should verify |
|---------|------------------------------|
| Action Callbacks | `run` chains are needed and not nested incorrectly |
| Lifecycle Events | `before_reasoning`/`after_reasoning` are used intentionally, not as default noise |
| Bidirectional | Return path is explicit only when workflow requires return |
| Input Bindings | Pinning vs `...` matches posture and data trust requirements |
| System Overrides | Dynamic instructions are requirement-driven and not contradictory |
| Authentication Return | Proof comes from verification; return address is cleared; cancel and sign-out work |
| Multi-Step Workflow | Each flag is a trusted action result; failure cannot unlock the next action |

## Anti-Patterns to Avoid

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| Nested `run` inside `run` | Sequential `run` at same level |
| Lifecycle in wrong order | before_reasoning, reasoning, after_reasoning |
| Store a fixed return target | Use direct transitions in both directions |
| Use lifecycle for one-time setup | Initialize outside the per-turn lifecycle |
| Add `current_step` plus completion flags | Derive availability from successful external results |
| Store user input already present in history | Bind safe user inputs with `...` |
| Add a focus latch for cheaper routing | Route the latest intent; reproduce a failure before adding deterministic control |
| Leave authentication without an exit | Clear pending return state on cancel and proof state on sign-out |
