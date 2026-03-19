# Agent Script Patterns

This folder contains reusable patterns for common Agentforce scenarios.

## Pattern Decision Tree

```
What do you need?
│
├─► Guaranteed post-action processing?
│   └─► Use: action-callbacks.agent
│       (run keyword for deterministic callbacks)
│
├─► Setup/cleanup for every reasoning turn?
│   └─► Use: lifecycle-events.agent
│       (before_reasoning / after_reasoning blocks)
│
├─► Navigate to specialist and return with results?
│   └─► Use: bidirectional-routing.agent
│       (store return address, specialist transitions back)
│
├─► Complex parameter passing to actions?
│   └─► Use: advanced-input-bindings.agent
│       (slot filling, variable binding, output chaining)
│
├─► Dynamic behavior based on user context?
│   └─► Use: system-instruction-overrides.agent
│       (tier-based, time-based, feature flag instructions)
│
├─► Authentication gate with deferred routing?
│   └─► Use: open-gate-routing.agent
│       (3-variable state machine with LLM bypass)
│
└─► None of the above?
    └─► Start with: ../getting-started/hello-world.agent
```

## Patterns Overview

### 1. [action-callbacks.agent](action-callbacks.agent)

**Purpose**: Chain actions with guaranteed execution using `run` keyword.

**Use when**:
- Follow-up actions MUST happen after parent action
- Audit logging required for compliance
- Order matters (send email AFTER order created)

**Key syntax**:
```agentscript
process_order: @actions.create_order
   with customer_id=...
   set @variables.order_id = @outputs.order_id
   run @actions.send_confirmation        # Always runs after create_order
      with order_id=@variables.order_id
   run @actions.log_activity             # Always runs after confirmation
      with event_type="ORDER_CREATED"
```

---

### 2. [lifecycle-events.agent](lifecycle-events.agent)

**Purpose**: Run code before/after every reasoning step automatically.

**Use when**:
- Track conversation metrics (turn count, duration)
- Refresh context before each response
- Log analytics after each turn
- Initialize state on first turn

**Key syntax**:
```agentscript
topic conversation:
   before_reasoning:
      set @variables.turn_count = @variables.turn_count + 1
      run @actions.refresh_context

   reasoning:
      instructions: ->
         | This is turn {!@variables.turn_count}

   after_reasoning:
      run @actions.log_analytics
```

---

### 3. [bidirectional-routing.agent](bidirectional-routing.agent)

**Purpose**: Navigate to specialist topic and return with results.

**Use when**:
- Complex workflows spanning multiple topics
- "Consult an expert" pattern
- Need to bring results back to coordinator
- Want separation of concerns

**Key syntax**:
```agentscript
# In main topic
consult_pricing: @utils.transition to @topic.pricing_specialist

# In specialist topic
before_reasoning:
   set @variables.return_topic = "main_hub"

# ... do specialist work ...

return_with_results: @utils.transition to @topic.main_hub
```

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

# Topic reasoning: Dynamic overrides
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

**Purpose**: Auth-gated topic routing with LLM bypass using a 3-variable state machine.

**Use when**:
- Multiple protected topics require authentication before access
- You want zero-credit LLM bypass while a gate topic holds focus
- Users should be redirected to auth, then automatically returned to their intended topic
- You need an EXIT_PROTOCOL to release gate state when users change intent

**Key syntax**:
```agentscript
# topic_selector bypasses LLM when open_gate is set
before_reasoning:
   if @variables.open_gate == "protected_workflow":
      transition to @topic.protected_workflow
   if @variables.open_gate == "authentication_gate":
      transition to @topic.authentication_gate
```

**Credit**: Hua Xu (Salesforce APAC FDE team) — production pattern from Kogan agent deployment.

---

## Pattern Combinations

These patterns can be combined:

```
lifecycle-events + action-callbacks
├── before_reasoning: Initialize context
├── reasoning: Process with callbacks
│   └── action with run callbacks
└── after_reasoning: Log results

open-gate-routing + lifecycle-events
├── before_reasoning: Gate check + context refresh
├── reasoning: Protected actions (if authenticated)
└── after_reasoning: Post-auth routing + analytics
```

## Validation Scoring Impact

| Pattern | Scoring Boost | Key Requirements |
|---------|--------------|------------------|
| Action Callbacks | +5 pts | No nested run |
| Lifecycle Events | +5 pts | Proper block placement |
| Bidirectional | +5 pts | Return transitions |
| Input Bindings | +5 pts | Proper binding patterns |
| System Overrides | +5 pts | Static system, dynamic topics |
| Open Gate | +5 pts | 3-variable coordination |

## Anti-Patterns to Avoid

| ❌ Don't | ✅ Do Instead |
|----------|---------------|
| Nested `run` inside `run` | Sequential `run` at same level |
| Lifecycle in wrong order | before_reasoning, reasoning, after_reasoning |
| Forget return transition | Always include return action in specialists |
| Use lifecycle for one-time setup | Use if @variables.turn_count == 1 |
| Missing EXIT_PROTOCOL in gate pattern | Always include gate reset topic |
| Hardcoding gate topic name in open_gate | Use variable-driven routing |
