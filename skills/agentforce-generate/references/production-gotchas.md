# Production Gotchas: Billing, Determinism & Performance
Credit consumption, lifecycle hooks, determinism patterns, and performance guardrails in Agentforce.
---

## Credit Consumption Table

| Operation | Credits | Notes |
|-----------|---------|-------|
| `@utils.transition` | FREE | Framework navigation |
| `@utils.setVariables` | FREE | Framework state management |
| `@utils.escalate` | FREE | Framework escalation |
| `if`/`else` control flow | FREE | Deterministic resolution |
| `before_reasoning` | FREE | Deterministic pre-processing (see note below) |
| `after_reasoning` | FREE | Deterministic post-processing (see note below) |
| `reasoning` (LLM turn) | FREE | LLM reasoning itself is not billed |
| Prompt Templates | 2-16 | Per invocation (varies by complexity) |
| Flow actions | 20 | Per action execution |
| Apex actions | 20 | Per action execution |
| Any other action | 20 | Per action execution |

The `before_reasoning:` and `after_reasoning:` lifecycle hooks are validated. Content goes **directly** under the block (no `instructions:` wrapper). See "Lifecycle Hooks" section below for correct syntax.

### Cost Optimization Pattern

Fetch data once in `before_reasoning:`, cache in variables, reuse across subagents.

## Lifecycle Hooks

```yaml
subagent main:
   description: "Subagent with lifecycle hooks"

   # BEFORE: Runs deterministically BEFORE LLM sees instructions
   before_reasoning:
      # Content goes DIRECTLY here (NO instructions: wrapper!)
      set @variables.pre_processed = True
      set @variables.customer_tier = "gold"

   # LLM reasoning phase
   reasoning:
      instructions: ->
         | Customer tier: {!@variables.customer_tier}
         | How can I help you today?

   # AFTER: Runs deterministically AFTER LLM finishes reasoning
   after_reasoning:
      # Content goes DIRECTLY here (NO instructions: wrapper!)
      set @variables.interaction_logged = True
      if @variables.needs_audit == True:
         set @variables.audit_flag = True
```

**Key Points:**
- Content goes **directly** under `before_reasoning:` / `after_reasoning:` (NO `instructions:` wrapper)
- Reliable primitives: `set`, `if`/`else`, `transition to`. `run` has inconsistent runtime behavior across bundle types — use it in `reasoning.actions:` or `instructions: ->` instead
- `before_reasoning:` is FREE (no credit cost) - use for data prep
- `after_reasoning:` is FREE (no credit cost) - use for logging, cleanup
- `transition to` works in `after_reasoning:` — but if a subagent transitions mid-reasoning, the original subagent's `after_reasoning:` does NOT run

**❌ WRONG Syntax (causes compile error):**
```yaml
before_reasoning:
   instructions: ->      # ❌ NO! Don't wrap with instructions:
      set @variables.x = True
```

**✅ CORRECT Syntax:**
```yaml
before_reasoning:
   set @variables.x = True   # ✅ Direct content under the block
```

## Supervision vs Handoff

| Term | Syntax | Behavior | Use When |
|------|--------|----------|----------|
| **Handoff** | `@utils.transition to @subagent.X` | Control transfers completely, child generates final response | Checkout, escalation, terminal states |
| **Supervision** | `@subagent.X` (as action reference) | Parent orchestrates, child returns, parent synthesizes | Expert consultation, sub-tasks |

```yaml
# HANDOFF - child subagent takes over completely:
checkout: @utils.transition to @subagent.order_checkout
   description: "Proceed to checkout"
# → @subagent.order_checkout generates the user-facing response

# SUPERVISION - parent remains in control:
get_advice: @subagent.product_expert
   description: "Consult product expert"
# → @subagent.product_expert returns, parent subagent synthesizes final response
```

**KNOWN BUG**: Adding ANY new action in Canvas view may inadvertently change Supervision references to Handoff transitions.

## Action Output Flags for Zero-Hallucination Routing

Control what the LLM can see and say.

When defining actions in Agentforce Assets, use these output flags:

| Flag | Effect | Use When |
|------|--------|----------|
| `filter_from_agent: True` | LLM **cannot** show this value to user | Preventing hallucinated responses (GA standard) |
| `is_used_by_planner: True` | LLM **can** reason about this value | Decision-making, routing |

**Zero-Hallucination Intent Classification Pattern:**
```yaml
# In Agentforce Assets - Action Definition outputs:
outputs:
   intent_classification: string
      filter_from_agent: True     # LLM cannot show this to user (GA standard)
      is_used_by_planner: True    # LLM can use for routing decisions

# In Agent Script - LLM routes but cannot hallucinate:
subagent intent_router:
   reasoning:
      instructions: ->
         run @actions.classify_intent
         set @variables.intent = @outputs.intent_classification

         if @variables.intent == "refund":
            transition to @subagent.refunds
         if @variables.intent == "order_status":
            transition to @subagent.orders
```

## Action I/O Metadata Properties

Complete reference for all metadata properties available on action definitions, inputs, and outputs.

**Action-Level Properties:**

| Property | Type | Effect |
|----------|------|--------|
| `label` | String | Display name in UI |
| `description` | String | LLM reads this for decision-making |
| `require_user_confirmation` | Boolean | Request user confirmation before execution (compiles; runtime no-op per Issue 6) |
| `include_in_progress_indicator` | Boolean | Show spinner during execution |
| `progress_indicator_message` | String | Custom spinner text |

**Input Properties:**

| Property | Type | Effect |
|----------|------|--------|
| `description` | String | Explains parameter to LLM |
| `label` | String | Display name in UI |
| `is_required` | Boolean | Marks input as mandatory for LLM |
| `is_user_input` | Boolean | LLM extracts value from conversation |
| `complex_data_type_name` | String | Lightning type mapping |

**Output Properties:**

| Property | Type | Effect |
|----------|------|--------|
| `description` | String | Explains output to LLM |
| `label` | String | Display name in UI |
| `filter_from_agent` | Boolean | `True` = hide from user display (GA standard) |
| `is_displayable` | Boolean | `False` = hide from user (compile-valid alias) |
| `is_used_by_planner` | Boolean | `True` = LLM can reason about value |
| `developer_name` | String | Overrides the parameter's developer name |
| `complex_data_type_name` | String | Lightning type mapping |

`filter_from_agent: True` is the GA standard name. `is_displayable: False` is a compile-valid alias.

### User Input Pattern

With `is_user_input: True`:
```yaml
inputs:
   customer_name: string
      description: "Customer's full name"
      is_user_input: True    # LLM pulls from what user already said
      is_required: True      # Must have a value before action executes
```

## Action Chaining with `run` Keyword

Parent action may complain about inputs needed by chained action - this is expected.

```yaml
process_order: @actions.create_order
   with customer_id = @variables.customer_id
   run @actions.send_confirmation        # Chains after create_order completes
   set @variables.order_id = @outputs.id
```

KNOWN BUG: Chained actions with Prompt Templates don't properly map inputs using `Input:Query` format.

For prompt template action definitions, input binding syntax, and grounded data patterns, see [Action Prompt Templates](action-prompt-templates.md).

## Latch Variable Pattern for Subagent Re-entry

Subagent router doesn't properly re-evaluate after user provides missing input. Use a "latch" variable to force re-entry:

```yaml
variables:
   verification_in_progress: mutable boolean = False

start_agent agent_router:
   reasoning:
      instructions: ->
         if @variables.verification_in_progress == True:
            transition to @subagent.verification
         | How can I help you today?
      actions:
         start_verify: @subagent.verification
            description: "Start identity verification"
            set @variables.verification_in_progress = True

subagent verification:
   reasoning:
      instructions: ->
         | Please provide your email to verify your identity.
      actions:
         verify: @actions.verify_identity
            with email = ...
            set @variables.verified = @outputs.success
            set @variables.verification_in_progress = False
```

## Loop Protection Guardrail

Agent Scripts have a built-in guardrail that limits iterations to approximately **3-4 loops** before breaking out and returning to the Subagent Router.

**Best Practice**: Map out your execution paths and test for unintended circular references between subagents.

## Token & Size Limits

| Limit Type | Value | Notes |
|------------|-------|-------|
| Max response size | 1,048,576 bytes (1MB) | Per agent response |
| Plan trace limit (Frontend) | 1M characters | For debugging UI |
| Transformed plan trace (Backend) | 32k tokens | Internal processing |
| Active/Committed Agents per org | 100 max | Org limit |

## Progress Indicators

```yaml
actions:
   fetch_data: @actions.get_customer_data
      description: "Fetch customer information"
      include_in_progress_indicator: True
      progress_indicator_message: "Fetching your account details..."
```

## VS Code Pull/Push NOT Supported

```bash
# ❌ ERROR when using source tracking:
Failed to retrieve components using source tracking:
[SfError [UnsupportedBundleTypeError]: Unsupported Bundle Type: AiAuthoringBundle

# ✅ WORKAROUND - Use CLI directly:
sf project retrieve start --json -m AiAuthoringBundle:MyAgent
sf agent publish authoring-bundle --json --api-name MyAgent -o TARGET_ORG
```

## `@inputs` Scope Lifecycle (Silent Failure)

`@inputs` is only available in `with` directives during action invocation. Using `@inputs` in a post-action `set` causes **silent runtime failure** — the action executes but the `set` silently drops, leaving the variable unchanged. No trace error; the FunctionStep shows no output capture.

```agentscript
# WRONG — silent failure, @inputs out of scope after action executes
run @actions.get_station_status
    with station_name = ...
    set @variables.station = @inputs.station_name   # FAILS SILENTLY

# RIGHT — use @outputs (if action echoes the value) or capture input before the call
set @variables.station = @variables.selected_station  # capture before
run @actions.get_station_status
    with station_name = @variables.station
    set @variables.status = @outputs.status           # @outputs is valid here
```

**Diagnosis:** A FunctionStep that completes with no output capture (set directives dropped) indicates an `@inputs` scope violation. The action succeeds — only the assignment fails.

Similarly, `@outputs` is only available in `set` and `if` directives immediately following the action invocation — not in instructions, pipe lines, or later actions.

## Reserved `@InvocableVariable` Keywords

Certain common words cannot be used as `@InvocableVariable` names in Apex classes called by Agent Script. Using them causes "SyntaxError: Unexpected '{keyword}'" during agent script compilation. (Validated March 2026)

**Reserved names (cannot use as `@InvocableVariable`):**

| Reserved Name | Workaround | Example |
|---------------|------------|---------|
| `model` | `vehicle_model`, `data_model`, `model_name` | `@InvocableVariable public String vehicle_model;` |
| `description` | `issue_description`, `desc_text`, `description_field` | `@InvocableVariable public String issue_description;` |
| `label` | `label_text`, `display_label`, `label_field` | `@InvocableVariable public String label_text;` |

**How it manifests:**
- Apex compiles and deploys successfully (these are valid Apex identifiers)
- Error only appears when the Agent Script compiler processes the action's I/O schema
- Error message: `SyntaxError: Unexpected 'model'` (or `description`, `label`)
- Fix: Rename the `@InvocableVariable` in Apex, redeploy, then republish the agent

## Language Block Quirks

- Hebrew and Indonesian appear **twice** in the language dropdown
- Selecting from the second set causes save errors
- Use `adaptive_response_allowed: True` for automatic language adaptation
