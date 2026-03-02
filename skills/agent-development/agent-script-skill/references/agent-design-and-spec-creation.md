# Agent Design and Spec Creation

## Table of Contents

1. Agent Spec Overview
2. Topic Architecture
3. Backing Logic and Type Mapping
4. Flow Control and Gating
5. Action Loop Prevention

---

## 1. Agent Spec Overview

An **Agent Spec** is a structured design document describing agent purpose, topics, actions, state, control flow, and behavioral intent. Produce before writing Agent Script (creation) or reverse-engineer from `.agent` file (comprehension/diagnosis).

### Contents

- **Purpose & Scope** — what agent does, plain language
- **Behavioral Intent** — what agent should achieve (requirements/constraints), not just what code does
- **Topic Map** — Mermaid flowchart: topics, transitions (labeled: handoff or delegation), when transitions occur
- **Actions & Backing Logic** — name, backing implementation (Apex/Flow/Prompt Template), inputs/outputs, EXISTS or NEEDS STUB
- **Variables** — declarations, types, defaults, which topics set/read, what gates they control
- **Gating Logic** — conditions governing action visibility or instruction evaluation, with rationale. If no gating, state "No gating required"

### Lifecycle

- **Creation (sparse)**: Purpose, topic names, rough descriptions, directional notes ("needs Apex class accepting X, returning Y"). No flowchart.
- **Build (filled)**: Flowchart with transition types. Backing logic mapped (existing = filenames, missing = protocols/I/O specs). Variables documented. Gating explained.
- **Comprehension (reverse-engineered)**: Parse `.agent` file → complete Agent Spec
- **Diagnosis (reference)**: Compare runtime behavior against Agent Spec to find divergence

**Template**: `assets/agent-spec-template.md`

---

## 2. Topic Architecture

Topics are FSM states. Plan structure before coding.

### Topic Roles

- **Domain** — core work areas (orders, billing, weather, events). Most agents have 1-5 domain topics.
- **Guardrail** — enforce boundaries. Standard template includes `off_topic` (redirect to scope) and `ambiguous_question` (ask for clarification). Preserve these.
- **Escalation** — hand off to human via `@utils.escalate`. Permanent exit, agent session ends.

### Patterns

**Hub-and-Spoke**: Central router (`start_agent`) transitions to specialized domain topics. Use when agent handles multiple distinct domains.

```agentscript
start_agent topic_selector:
    reasoning:
        actions:
            go_weather: @utils.transition to @topic.local_weather
            go_events: @utils.transition to @topic.local_events
```

**Linear Flow**: Topics form pipeline (start → step1 → step2 → end). Use for multi-step workflows with mandatory ordering.

**Escalation Chain**: Tiered support (level1 → level2 → human). First level uses basic actions, higher levels have more power.

**Verification Gate**: Security/permission check before protected topics. Gate validates, then transitions to protected topic or denies.

```agentscript
start_agent security_gate:
    reasoning:
        actions:
            go_admin: @utils.transition to @topic.admin_panel
                available when @variables.user_role == "admin"
            go_denied: @utils.transition to @topic.access_denied
                available when @variables.user_role != "admin"
```

**Single-Topic**: No transitions. Use for focused QA agents where all interactions stay in same domain.

Real agents often combine patterns. Each topic serves exactly one role (domain, guardrail, escalation) — architecture determines how they connect.

---

## 3. Backing Logic and Type Mapping

Every action needs backing logic. Identify existing implementations or stub missing ones.

### Valid Types

**Apex**: Only **invocable** classes. Regular classes don't work.

```apex
// RIGHT — invocable with annotations
public class WeatherFetcher {
    public class Request {
        @InvocableVariable(label='Date' description='Date to check' required=true)
        public Date dateToCheck;
    }
    public class Result {
        @InvocableVariable(label='Max Temp')
        public Decimal maxTemp;
    }
    @InvocableMethod(label='Fetch Weather')
    public static List<Result> getWeather(List<Request> requests) { ... }
}
```

Wire: `target: "apex://ClassName"`

**Flows**: Only **autolaunched** Flows. Screen/trigger/schedule Flows don't work.

Wire: `target: "flow://FlowApiName"`

**Prompt Templates**: Salesforce Prompt Templates.

Wire: `target: "prompt://TemplateName"`

### Finding Existing Logic

Read `sfdx-project.json` → `packageDirectories` → `path` (typically `force-app/main/default/`).

- **Invocable Apex**: Search `classes/` for `@InvocableMethod`. Read `@InvocableVariable` annotations for I/O contract.
- **Autolaunched Flows**: Search `flows/` for `.flow-meta.xml` with `<processType>AutoLaunchedFlow</processType>`. Check variables for inputs (`isInput=true`) and outputs (`isOutput=true`).
- **Prompt Templates**: Search `promptTemplates/` for template metadata.

### Critical Naming Constraint

**Input/output names MUST exactly match Apex `@InvocableVariable` field names, character-for-character.** Mismatches cause publish failures.

```agentscript
# WRONG — snake_case doesn't match Apex field names
actions:
    check_order:
        inputs:
            order_id: string     # Apex field is orderId

# CORRECT — matches Apex exactly
actions:
    check_order:
        inputs:
            orderId: string      # matches Request.orderId
```

### Type Mapping (Apex → Agent Script)

Some Apex types require `object` + `complex_data_type_name` to pass publish validation. Local compilation doesn't check these — mismatches surface at publish.

| Apex Type  | Agent Script type | complex_data_type_name        |
|------------|-------------------|-------------------------------|
| String     | string            | (omit)                        |
| Boolean    | boolean           | (omit)                        |
| Decimal    | number            | (omit)                        |
| Integer    | object            | lightning__integerType         |
| Long       | object            | lightning__longType            |
| Date       | object            | lightning__dateType            |
| Datetime   | object            | lightning__dateTimeType        |

Example:
```agentscript
inputs:
    attendeeCount: object
        complex_data_type_name: "lightning__integerType"
    eventDate: object
        complex_data_type_name: "lightning__dateType"
```

### Stubbing Missing Logic

Always stub as invocable Apex:

1. Record in Agent Spec:
```
fetch_invoice action:
  Backing: (needs creation)
  Target: apex://InvoiceFetcher
  Inputs: invoiceId (string, required)
  Outputs: invoiceAmount (number), dueDate (object, lightning__dateType)
```

2. Find default package directory from `sfdx-project.json` (`"default": true` entry's `path`)

3. Generate: `sf generate apex class --name InvoiceFetcher --output-dir <PACKAGE_DIR>/main/default/classes`

4. Replace body with invocable structure (see Apex example above)

5. Deploy: `sf project deploy start --json --metadata ApexClass:InvoiceFetcher`

---

## 4. Flow Control and Gating

### Transition Types

**Handoff (one-way)**: Use `@utils.transition to` in `reasoning.actions`. Control never returns. Use for mode switches, entry routing, linear workflows.

```agentscript
reasoning:
    actions:
        go_checkout: @utils.transition to @topic.checkout
```

**Delegation (with return intent)**: Use `@topic.X` in `reasoning.actions`. **Critical: Return does NOT happen automatically.** Delegated topic must explicitly transition back to caller.

```agentscript
# Caller
topic main:
    reasoning:
        actions:
            consult: @topic.specialist

# Delegated topic MUST transition back
topic specialist:
    reasoning:
        actions:
            return_to_main: @utils.transition to @topic.main
```

### Deterministic vs. Subjective

**Deterministic** (runtime-enforced) — use when requirement is non-negotiable:
- Security: "only admin users"
- Financial: "never approve >$10K without human"
- State: "don't show payment until address provided"

**Subjective** (LLM decides) — use when flexibility acceptable:
- Conversational tone
- Natural language generation
- User preferences

**Test**: What happens if LLM gets it wrong? Security breach/financial error → deterministic. Awkward response/suboptimal tone → subjective.

### Gating Mechanisms

**`available when`** — Action visibility gate (strongest). Runtime hides action when condition false. LLM cannot call unavailable actions.

```agentscript
reasoning:
    actions:
        confirm: @actions.confirm_booking
            available when @variables.booking_pending == True
```

**Conditional Instructions** — Prompt text gate. Changes what LLM is told, doesn't hide actions.

```agentscript
reasoning:
    instructions: ->
        | You're helping a customer.
        if @variables.is_vip:
            | This is a VIP. Prioritize their request.
```

**`before_reasoning` Guards** — Early exit. Runs before LLM invoked. LLM never sees it, cannot override, cannot skip.

```agentscript
topic admin_panel:
    before_reasoning:
        if @variables.user_role != "admin":
            transition to @topic.access_denied

    reasoning:
        instructions: | You are in admin panel.
```

**Multi-Condition Gating** — Combine mechanisms:

```agentscript
topic checkout:
    before_reasoning:
        if @variables.is_demo_mode:
            transition to @topic.demo_complete

    reasoning:
        instructions: ->
            if @variables.items_in_cart == 0:
                | Your cart is empty.

        actions:
            pay: @actions.process_payment
                available when @variables.authenticated == True
                    and @variables.items_in_cart > 0
```

**Sequential Gate Pattern** — Track progress through validation stages:

```agentscript
variables:
    step1_verified: mutable boolean = False
    step2_verified: mutable boolean = False

topic verification:
    reasoning:
        actions:
            verify_step1: @actions.run_check_1
            verify_step2: @actions.run_check_2
                available when @variables.step1_verified == True
            proceed: @utils.transition to @topic.confirmed
                available when @variables.step2_verified == True
```

### Same-Turn Behavior After Gates

When gate topic transitions via `after_reasoning` to router, both process in **same user turn**. Router receives original message (that satisfied gate), not fresh utterance.

**Mitigation**: Write router instructions defensively. Tell LLM if user just arrived from gate, greet and ask how to help instead of routing the triggering message.

### Writing Effective Instructions

**Instruction Ordering**: Runtime resolves top-to-bottom before LLM sees result. Put post-action checks first, data references next, dynamic conditional text last.

**Grounding**: Platform validates response matches action output data. Use specific values (`"Event is on {!@variables.event_date}"`), don't transform (`"next week"` may fail). Avoid embellishment instructions (`"respond like pirate"`). Test with **live mode** (`--use-live-actions`) — simulated mode has no real data.

**Post-Action Behavior**: When action completes without transition, topic stays active. Runtime re-evaluates entire topic with updated variables, passes new prompt to LLM. LLM may call same action again (see Section 5).

---

## 5. Action Loop Prevention

An action loop occurs when LLM calls same action repeatedly without new user input. Three causes:

- **No `available when` gate**: Action appears every reasoning cycle, nothing automatically hides it
- **Variable-bound input**: Action "ready to go" (`with param = @variables.x`), no friction
- **No post-action instructions**: LLM doesn't know to stop

**WRONG: All three present**
```agentscript
topic events:
    reasoning:
        instructions: ->
            | Use {!@actions.check_events} to find events.

        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest  # Variable-bound
```

### Three Mitigations

**1. Explicit Post-Action Instructions (most common)**

```agentscript
topic events:
    reasoning:
        instructions: ->
            | Use {!@actions.check_events} to find events.
              After receiving results, present them to guest.
              Do NOT call action again — you have the information.

        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest
```

**2. Post-Action Transitions (state-based)**

```agentscript
topic events:
    reasoning:
        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest

    after_reasoning:
        if @outputs.events_found:
            transition to @topic.results_displayed
```

**3. LLM Slot-Filling Over Variable Binding (friction-based)**

```agentscript
topic search:
    reasoning:
        instructions: ->
            | Ask what they're looking for, then use {!@actions.search}.

        actions:
            search: @actions.search
                with query = ...  # LLM must extract each time
```

**Combine for reinforcement:**

```agentscript
topic lookup:
    reasoning:
        instructions: ->
            | Once you have result, present it. Do NOT call again.

        actions:
            lookup: @actions.find_data
                with key = ...  # Requires extraction

    after_reasoning:
        if @outputs.data_found:
            transition to @topic.done  # Exit topic
```
