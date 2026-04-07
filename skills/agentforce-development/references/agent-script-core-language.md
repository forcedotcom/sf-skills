# Agent Script: Core Language Reference

## Table of Contents

1. How Agent Script Executes
2. File Structure and Block Ordering
3. Naming and Formatting Rules
4. Expressions and Operators
5. System and Config Blocks
6. Variables
7. Topics
8. Reasoning Instructions
9. Flow Control
10. Actions
11. Utility Functions
12. Anti-Patterns

---

## 1. How Agent Script Executes

Agent Script operates in two phases: deterministic resolution, then LLM reasoning.

**Phase 1: Deterministic Resolution.** The runtime executes a topic's reasoning instructions top to bottom — evaluating `if`/`else` conditions, running actions via `run`, and setting variables via `set`. The LLM is NOT involved yet. The runtime builds a prompt string by accumulating `|` pipe text and resolving conditional logic. If a `transition` command occurs, the runtime discards the current prompt and starts fresh with the target topic.

**Phase 2: LLM Reasoning.** The runtime passes the resolved prompt to the LLM along with any reasoning actions (tools) the topic exposes. The LLM decides what to do — it can call available actions but cannot modify the prompt text. It only reasons against what Phase 1 resolved.

**Worked Example.** Consider this topic:

```agentscript
topic check_order:
    reasoning:
        instructions: ->
            if @variables.order_id != "":
                run @actions.fetch_order
                    with id = @variables.order_id
                    set @variables.status = @outputs.status

            | Your order status is {!@variables.status}.
              You can modify it using the {!@actions.update_order} action.

        actions:
            update: @actions.update_order
                with order_id = @variables.order_id
```

If `@variables.order_id` is `"1001"` and the `fetch_order` action returns `status = "shipped"`, the runtime resolves to this prompt:

```
Your order status is shipped.
You can modify it using the update_order action.
```

The LLM then receives this prompt plus the `update` tool and decides whether to call it based on what the user asks.

This split is critical: **deterministic logic controls WHAT the agent knows (via resolved prompt), and the LLM controls WHETHER and HOW to act on that knowledge**.

---

## 2. File Structure and Block Ordering

An Agent Script file (`.agent` extension) contains eight top-level blocks in this mandatory order:

```agentscript
system:
    ...

config:
    ...

variables:
    ...

connection:
    ...

knowledge:
    ...

language:
    ...

start_agent topic_selector:
    ...

topic my_topic:
    ...
```

**Required blocks:** `system`, `config`, `start_agent`, and at least one `topic`.

**Optional blocks:** `variables`, `connections`, `knowledge`, `language`. Omit them if not needed.

**Within `start_agent` and `topic` blocks**, the internal ordering is:

1. `description` (required)
2. `system` (optional — topic-level override of global system instructions)
3. `before_reasoning` (optional — runs before reasoning phase)
4. `reasoning` (required)
5. `after_reasoning` (optional — runs after reasoning phase)
6. `actions` (optional — action definitions)

---

## 3. Naming and Formatting Rules

**Naming constraints for all identifiers** (developer_name, topic names, variable names, action names, connection names):

- Contain only letters, numbers, and underscores
- Begin with a letter (never underscore)
- Cannot end with an underscore
- Cannot contain two consecutive underscores (`__`)
- Maximum 80 characters
- `snake_case` is strongly recommended

Example: `check_order_status` is valid. `check_order__status` is invalid (consecutive underscores).

**Indentation:** Use 4 spaces per indent level. NEVER use tabs. Mixing spaces and tabs breaks the parser. All lines at the same nesting level must use the same indentation.

Each nesting level adds 4 spaces. The hierarchy follows the block structure — topic → reasoning → instructions → logic/prompt:

```agentscript
topic process_order:
    description: "Handle order processing"
    reasoning:
        instructions: ->
            | Welcome
```

**Comments:** Use `#` for single-line comments. The parser ignores everything after `#` on that line.

Comments can appear on their own line or inline after code. Both forms are valid:

```agentscript
# This is a standalone comment
variables:
    order_id: mutable string = ""  # This is an inline comment
```

---

## 4. Expressions and Operators

**Comparison operators**:

- `==` (equal): `@variables.status == "complete"`
- `!=` (not equal): `@variables.count != 0`
- `<` (less than): `@variables.price < 100`
- `<=` (less than or equal): `@variables.age <= 18`
- `>` (greater than): `@variables.amount > 50`
- `>=` (greater than or equal): `@variables.balance >= 0`
- `is` (identity check — use for None): `@variables.value is None`
- `is not` (negated identity check): `@variables.data is not None`

**Logical operators**:

- `and`: Both conditions must be true. `@variables.verified == True and @variables.age >= 18`
- `or`: Either condition can be true. `@variables.status == "pending" or @variables.status == "review"`
- `not`: Negates a condition. `not @variables.is_guest == True` (though `@variables.is_guest == False` is more readable)

**Arithmetic operators** (limited support):

- `+` (addition): `@variables.count + 1`
- `-` (subtraction): `@variables.total - @variables.discount`

Do NOT use `*`, `/`, `%` — they are not supported.

**Access operators**:

- `.` (property access): `@object.property`
- `[]` (index access): `@variables.items[0]`

**Conditional expressions**:

- `x if condition else y`: `"premium" if @variables.is_premium == True else "standard"`

**Template injection in strings** (within `|` multiline text):

Use `{!expression}` to inject variable values or expressions into prompt text:

```agentscript
instructions: |
    Your total is {!@variables.total}.
    Your status: {!@variables.status if @variables.status else "pending"}.
```

The expression inside `{! ... }` is evaluated by the runtime during deterministic resolution and the result replaces the entire `{! ... }` block in the prompt.

**Resource references**:

- `@actions.<name>` — reference an action defined in the topic's `actions` block
- `@topic.<name>` — reference a topic by name
- `@variables.<name>` — reference a variable (use in logic)
- `{!@variables.<name>}` — reference a variable in prompt text (template injection)
- `@outputs.<name>` — action output (only in `set`/`if` immediately after the action — unavailable elsewhere)
- `@inputs.<name>` — action input (only in `with` during invocation — NOT in `set` or post-execution)
- `@utils.<function>` — reference a utility (escalate, transition to, setVariables)

**Do NOT use `<>` as inequality operator.** Use `!=` instead.

```agentscript
# WRONG
if @variables.status <> "pending":

# CORRECT
if @variables.status != "pending":
```

---

## 5. System and Config Blocks

**System block** provides global instructions and messages:

```agentscript
system:
    instructions: "You are a helpful assistant. Be professional and concise."
    messages:
        welcome: "Hello! How can I help?"
        error: "Sorry, something went wrong. Please try again."
```

The `instructions` field is required and contains text directives sent to the LLM in every reasoning phase. Topic-level system blocks can override this.

Both `welcome` and `error` messages are required.

**Config block** contains agent metadata:

```agentscript
config:
    developer_name: "Customer_Service_Agent"
    agent_label: "Customer Service"
    description: "Handles customer inquiries"
    agent_type: "AgentforceServiceAgent"
    default_agent_user: "agent@example.com"
```

**Required fields:**
- `developer_name` (NOT `agent_name`) — unique identifier following naming rules. Must exactly match the AiAuthoringBundle directory name (e.g., if the directory is `aiAuthoringBundles/Travel_Advisor/`, then `developer_name` must be `"Travel_Advisor"`). A mismatch causes deploy failures.
- `agent_type` — `"AgentforceServiceAgent"` or `"AgentforceEmployeeAgent"`. Determines deployment context and whether `default_agent_user` is required:
  - `"AgentforceServiceAgent"` — customer-facing, deployed via messaging channels. **Requires `default_agent_user`** with Einstein Agent license.
  - `"AgentforceEmployeeAgent"` — internal employee-facing. Agent Script files with this agent type MUST NOT include:
    - `default_agent_user`
    - MessagingSession linked variables (`EndUserId`, `RoutableId`, `ContactId`, `EndUserLanguage`)
    - Escalation topic with `@utils.escalate`
    - `connection messaging:` block

  **Common mistake — service-agent constructs on employee agent:**

  ```agentscript
  # WRONG — employee agent with service-agent constructs
  config:
      agent_type: "AgentforceEmployeeAgent"
      default_agent_user: "agent@org.ext"    # PROHIBITED — causes "Internal Error"
  variables:
      EndUserId: linked string               # SERVICE ONLY — no messaging session
          source: @MessagingSession.MessagingEndUserId
  connection messaging:                       # SERVICE ONLY — no messaging channel
      escalation_message: "Transferring..."

  # RIGHT — clean employee agent config
  config:
      agent_type: "AgentforceEmployeeAgent"
      # No default_agent_user, no MessagingSession vars, no connection block
  ```

**Conditionally required fields:**
- `default_agent_user` — **required for `AgentforceServiceAgent`, prohibited for `AgentforceEmployeeAgent`**. This is the Salesforce username of the Einstein Agent User that runs agent actions on behalf of the customer. The user must exist in the target org, be active, and have the Einstein Agent license assigned.

  **⚠️ CRITICAL: Setting `default_agent_user` on an `AgentforceEmployeeAgent` causes publish and preview to fail with an unhelpful "unknown error" or "Internal Error, try again later" message.** The error gives no indication that `default_agent_user` is the cause. If you encounter this error on an employee agent, check whether `default_agent_user` is set and remove it.

  To find a valid Einstein Agent User in the org:
  ```bash
  sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
  ```

  If no results are returned, the org does not have an Einstein Agent User configured. Read `references/salesforce-cli-for-agents.md` for steps to create one.

  This field can be changed after publish, but only while no published version is activated. Deactivate the agent before changing `default_agent_user`.

**Optional fields:**
- `agent_label` — human-readable display name. Defaults to normalized `developer_name` if omitted
- `description` — what the agent does

---

## 6. Variables

**Two types of variables**:

**Mutable variables** — the agent can read AND write. MUST have a default value:

```agentscript
variables:
    customer_name: mutable string = ""
        description: "The customer's full name"
    order_count: mutable number = 0
    is_premium: mutable boolean = False
    preferences: mutable object = {}
    items: mutable list[string] = []
```

The `description` field is optional. Include it when the LLM needs context for slot-filling via `@utils.setVariables`.

**Linked variables** — read-only from external context. MUST have a `source`, MUST NOT have a default value:

```agentscript
variables:
    session_id: linked string
        description: "The current session ID"
        source: @session.sessionID
    user_id: linked string
        source: @MessagingSession.MessagingEndUserId
```

The `source` field points to the external context. At runtime, the platform provides the value.

**Type constraints by context**:

- Mutable variable types: `string`, `number`, `boolean`, `object`, `date`, `id`, `list[T]`
- Linked variable types: `string`, `number`, `boolean`, `date`, `id` (no `list`)
- Action parameter types: `string`, `number`, `boolean`, `object`, `date`, `timestamp`, `currency`, `id`, `list[T]`, `datetime`, `time`, `integer`, `long`

> ⚠️ `timestamp` and `currency` compile as variable types but are absent from official GA documentation and should NOT be used. Prefer `date` for date/time variables and `number` for currency values.

**Some types are ONLY valid for action parameters**:
`integer`, `long`, `datetime`, and `time` are action-parameter-only types. They are NOT valid for mutable or linked variables:

```agentscript
# WRONG — integer is not valid for mutable variables
low_count: mutable integer = 0

# RIGHT — use number for mutable variables
low_count: mutable number = 0
```

**`complex_data_type_name` for action parameters**: The simple types listed above (`date`, `integer`, `datetime`, `long`) work directly for Apex-backed action parameters — no special mapping needed. The `object` + `complex_data_type_name` pattern is only required for SObject references, Apex inner classes, custom Lightning types, and typed collections. Read `references/agent-design-and-spec-creation.md` for the full Apex ↔ Agent Script type mapping table.

**Boolean capitalization**:

ALWAYS use `True` or `False` (capitalized). NEVER use `true` or `false`:

```agentscript
# WRONG
enabled: mutable boolean = true
verified: linked boolean = false

# CORRECT
enabled: mutable boolean = True
is_verified: mutable boolean = False
```

**Template injection for variables** in prompt text:

Use `{!@variables.X}` to interpolate a variable's value into prompt text:

```agentscript
instructions: |
    Hello, {!@variables.customer_name}!
    Your balance: {!@variables.balance}
```

In prompt text (inside `|` pipe sections), always use `{!@variables.X}` with braces — the braces trigger template evaluation. Bare `@variables.X` without braces is valid in logic contexts (e.g., `if @variables.X == True:`) but will not interpolate in prompt text.

---

## 7. Topics

**Topic structure** — a named scope for reasoning, actions, and flow control:

```agentscript
topic order_lookup:
    description: "Handle customer order inquiries"

    reasoning:
        instructions: ->
            | Help the customer find their order.
        actions:
            search: @actions.find_order
                with order_id = ...

    actions:
        find_order:
            description: "Search for an order by ID"
            target: "flow://SearchOrder"
            inputs:
                order_id: string
            outputs:
                status: string
```

**Description is required** — the LLM uses this to understand when the topic is relevant.

**Topic-level system override** (optional) — override global system instructions for this topic only:

```agentscript
topic product_specialist:
    description: "Answer product questions"
    system:
        instructions: "You are a product expert. Be technical and detailed."
    reasoning:
        instructions: ->
            | Help with product specs.
```

**Internal block ordering within a topic**:

1. `description`
2. `system` (optional override)
3. `before_reasoning` (optional)
4. `reasoning` (required)
5. `after_reasoning` (optional)
6. `actions` (optional definitions)

**Before/after reasoning directive blocks**:

`before_reasoning` and `after_reasoning` contain deterministic logic that runs outside the reasoning phase:

```agentscript
before_reasoning:
    if @variables.session_expired:
        transition to @topic.login

reasoning:
    instructions: ->
        | Main topic logic

after_reasoning:
    if @variables.transaction_complete:
        transition to @topic.confirmation
```

Directive blocks use the arrow syntax (`->`) for logic but no LLM reasoning. They run deterministically.

---

## 8. Reasoning Instructions

Reasoning instructions combine deterministic logic and prompt text. The runtime resolves deterministic parts first, then sends the resulting prompt to the LLM for reasoning.

**Arrow syntax (`->`) for logic blocks**:

```agentscript
reasoning:
    instructions: ->
        if @variables.user_verified:
            run @actions.get_account
                with user_id = @variables.user_id
                set @variables.account_info = @outputs.account

        | Now tell the user their account balance.
```

The `->` prefix indicates "start with logic, then switch to prompt". The runtime evaluates the `if` condition and `run` command, then appends the pipe-delimited text to the prompt.

**Multiline strings with `|`** — two forms:

For static text with no logic, use `|` directly after the property:

```agentscript
instructions: |
    Welcome to our service!
    Please provide details about your request.
    I'll help you with whatever you need.
```

Static `|` instructions can coexist with a sibling `actions:` block under `reasoning:`:

```agentscript
reasoning:
    instructions: |
        Help the customer find a venue.
        After receiving results from {!@actions.search_venues}, present them clearly.
        Do NOT call the action again unless the customer asks for a new search.

    actions:
        find_venue: @actions.search_venues
            description: "Search for available venues"
            with location = ...
            with date = ...
```

For text mixed with logic, use `->` to enter a logic block, then `|` to switch to prompt text:

```agentscript
instructions: ->
    if @variables.needs_help:
        | Ask the user what they need help with.
    else:
        | Suggest self-service options.
```

Within `->` blocks, a line without `|` continues the previous line. A new `|` starts a new line:

```agentscript
instructions: ->
    | This is a long instruction that
      continues on the next physical line.
    | This starts a new logical line.
```

**If/Else (no "else if", no nested if)**:

```agentscript
# ✅ CORRECT — simple if/else
if @variables.status == "pending":
    run @actions.notify_pending
else:
    run @actions.notify_complete

# ❌ WRONG — else if not supported
if @variables.count < 5:
    run @actions.small
else if @variables.count < 10:
    run @actions.medium

# ❌ WRONG — nested if inside else is also invalid
if @variables.status == "pending":
    run @actions.queue_pending
else:
    if @variables.status == "closed":
        run @actions.archive
```

For multi-branch logic, use compound conditions (`if A and B:`) or flatten to sequential `if` statements.

**Inline action invocation (`run @actions.X`)**:

```agentscript
run @actions.check_inventory
    with product_id = @variables.selected_product
    set @variables.stock_level = @outputs.available_quantity
```

The `run` command executes the action deterministically — the runtime runs it before the LLM reasons. Use `with` to pass inputs (bound to variables or literal values). Use `set` to capture outputs into variables.

**Post-action directives** (only for `@actions`, not `@utils`):

```agentscript
run @actions.process_order
    with order_id = @variables.order_id
    set @variables.result = @outputs.status
    if @outputs.success == True:
        transition to @topic.confirmation
    else:
        transition to @topic.error_handling
```

After an action completes, you can check outputs and transition.

**Scope lifecycle — `@inputs` and `@outputs` are ephemeral:**
- `@inputs`: only in `with` directives during invocation. NOT in `set`/`if` after execution.
- `@outputs`: only in `set`/`if` immediately after invocation. NOT in instructions or later actions.
- To reuse an input value post-execution, capture it in `@variables` BEFORE the action call.

```agentscript
# WRONG — silent failure, @inputs out of scope in set
run @actions.get_station_status
    with station_name = ...
    set @variables.station = @inputs.station_name   # FAILS SILENTLY

# RIGHT — use @outputs (if action echoes value) or capture input beforehand
run @actions.get_station_status
    with station_name = ...
    set @variables.station = @outputs.station_name
```

**How pipe sections become the LLM prompt**:

All logic is resolved first; only matching `|` pipe lines are included in the prompt:

```agentscript
instructions: ->
    | Welcome!
    if @variables.is_returning:
        | Nice to see you again.
    else:
        | Let's get started.
    | How can I help?

# If is_returning == False, the prompt becomes:
# "Welcome! Let's get started. How can I help?"
```

---

## 9. Flow Control

Flow control determines how execution moves between topics and responds to conditions.

**Start agent topic** — the mandatory entry point:

Every conversation begins at `start_agent`. The LLM classifies the user's intent and routes to the appropriate topic:

```agentscript
start_agent topic_selector:
    description: "Route to appropriate topic"
    reasoning:
        instructions: ->
            | Welcome. I can help with orders, accounts, or billing.
        actions:
            go_orders: @utils.transition to @topic.order_info
                description: "For order inquiries"
            go_accounts: @utils.transition to @topic.account_help
                description: "For account questions"
```

**LLM-chosen transitions in reasoning actions**:

Expose the transition as a reasoning action when the LLM should judge the right moment:

```agentscript
reasoning:
    actions:
        go_next: @utils.transition to @topic.next_topic
            description: "Move to the next topic"
            available when @variables.ready == True
```

**Deterministic transitions in directive blocks**:

Use bare `transition to` in `before_reasoning` and `after_reasoning` for state-based transitions:

```agentscript
before_reasoning:
    if @variables.not_authenticated:
        transition to @topic.login

after_reasoning:
    if @variables.session_complete:
        transition to @topic.summary
```

The runtime evaluates the condition and transitions immediately. Do NOT use `@utils.transition to` in directive blocks — it causes compilation errors.

**Delegation with return**:

When a topic needs another topic's expertise but still has work to do afterward, use `@topic.X` to delegate. The target topic runs its reasoning, then returns control to the caller:

```agentscript
reasoning:
    actions:
        ask_expert: @topic.expert_consultation
            description: "Consult the expert topic"
```

This is different from `@utils.transition to`, which is one-way — the calling topic does not resume.

**Conditional branching within topics**:

Conditions in reasoning instructions control which prompt text the LLM ultimately receives. The runtime evaluates `if`/`else` branches and includes only the matching `|` pipe sections in the resolved prompt:

```agentscript
reasoning:
    instructions: ->
        if @variables.order_id != "":
            | Show order details for {!@variables.order_id}.
        else:
            | I need an order ID to help you.
```

---

## 10. Actions

Actions invoke Flows, Apex classes, Prompt Templates, or other target types. They can run deterministically (the runtime always executes them) or be exposed as tools for the LLM to choose at reasoning time.

**Action definition** — each action is defined in the topic's `actions` block with required and optional properties:

```agentscript
actions:
    get_customer:
        # Required properties
        target: "flow://GetCustomerInfo"
        description: "Fetches customer information"
        # Optional UI/UX properties
        label: "Get Customer"
        require_user_confirmation: False
        include_in_progress_indicator: True
        progress_indicator_message: "Looking up customer..."
        inputs:
            customer_id: string
                description: "The customer's unique ID"
                label: "Customer ID"
                is_required: True
        outputs:
            name: string
                description: "Customer's name"
                is_displayable: True
            customer_info: object
                complex_data_type_name: "lightning__recordInfoType"
                description: "Full customer record"
                filter_from_agent: True
```

**Action properties**:

- `target` (required) — reference to the executable, in the format `"type://DeveloperName"`
- `description` (optional) — the LLM uses this to decide when to call the action
- `label` (optional) — display name shown to the customer; auto-generated from action name if omitted
- `require_user_confirmation` (optional boolean) — when `True`, the customer must confirm before the action runs
- `include_in_progress_indicator` (optional boolean) — when `True`, shows a progress indicator during execution
- `progress_indicator_message` (optional string) — text shown during execution (e.g., `"Looking up customer..."`)

**Input properties**:

- `description` — metadata about the input parameter
- `label` — display name shown in UI; auto-generated from parameter name if omitted
- `is_required` (boolean) — when `True`, the input must be provided

**Output properties**:

- `description` — metadata about the output parameter
- `label` — display name shown in UI; auto-generated from parameter name if omitted
- `filter_from_agent` (boolean) — when `True`, hides the output from the LLM's context
- `is_displayable` (boolean) — controls whether output is shown to the customer
- `complex_data_type_name` — required for complex data types like SObject references (e.g., `"lightning__recordInfoType"`), Apex inner classes, and custom Lightning types. Not needed for simple types like `date`, `integer`, or `datetime` — use the simple type directly.

**Parameter names must exactly match the backing logic interface — including case.** Read the target class before writing the action definition.

Given this Apex class:

```java
public class CheckVenueAvailability {
    public class Request {
        @InvocableVariable public String venueName;
        @InvocableVariable public Date requestedDate;
    }
}
```

```agentscript
# WRONG — snake_case does not match @InvocableVariable field names
inputs:
    venue_name: string
    requested_date: date

# RIGHT — exact match to @InvocableVariable names
inputs:
    venueName: string
    requestedDate: date
```

Flow targets: match the Flow's input/output variable API names. Prompt Template targets: see "Prompt Template actions" below.

**Target types** — use the format `"type://DeveloperName"`:

Common targets:

- `flow` — Salesforce Flow (e.g., `"flow://GetCustomerInfo"`)
- `apex` — Invocable Apex class (e.g., `"apex://CheckWeather"`)
- `prompt` — Prompt Template (e.g., `"prompt://Get_Event_Info"`; long form: `generatePromptResponse`)

Additional targets:

- `standardInvocableAction` — built-in Salesforce actions
- `externalService` — external APIs registered via External Services
- `quickAction` — Salesforce Quick Actions
- `api` — REST API endpoints
- `apexRest` — Apex REST services
- `serviceCatalog` — Service Catalog items
- `integrationProcedureAction` — OmniStudio Integration Procedures
- `expressionSet` — Business Rules Engine expression sets
- `cdpMlPrediction` — Data Cloud ML predictions
- `externalConnector` — external system connectors
- `slack` — Slack integrations
- `namedQuery` — named SOQL queries
- `auraEnabled` — Aura-enabled Apex methods
- `mcpTool` — Model Context Protocol tools
- `retriever` — knowledge retrieval sources

**Prompt Template actions** differ from Apex and Flow actions:

1. Input names use a quoted `"Input:"` prefix: `"Input:fieldApiName"`.
2. Output is always `promptResponse: string`.
3. Target protocol is `generatePromptResponse://` (long form) or `prompt://` (short form).

```agentscript
# WRONG — bare input names and custom output (Apex/Flow pattern)
actions:
    Generate_Schedule:
        inputs:
            email: string
        outputs:
            schedule_text: string
        target: "prompt://Generate_Personalized_Schedule"

# RIGHT — quoted "Input:" prefix, promptResponse output
actions:
    Generate_Schedule:
        inputs:
            "Input:email": string
                description: "User's email address"
                is_required: True
        outputs:
            promptResponse: string
                description: "Generated schedule"
                is_displayable: True
        target: "generatePromptResponse://Generate_Personalized_Schedule"
```

Invocation — quote the input name:

```agentscript
reasoning:
    actions:
        generate: @actions.Generate_Schedule
            with "Input:email" = @variables.user_email
            set @variables.schedule = @outputs.promptResponse
```

**Deterministic invocation** — when the action must always run, use `run` in the reasoning instructions. The runtime executes it before the LLM reasons:

```agentscript
reasoning:
    instructions: ->
        run @actions.get_customer
            with customer_id = @variables.customer_id
            set @variables.customer_name = @outputs.name
            set @variables.customer_email = @outputs.email
```

**LLM exposure** — when the LLM should decide whether and when to call the action, list it in `reasoning.actions`. The LLM sees the description and chooses based on conversation context:

```agentscript
reasoning:
    actions:
        lookup: @actions.get_customer
            description: "Look up customer information"
            with customer_id = @variables.selected_customer
            set @variables.customer_name = @outputs.name
```

**Input binding** — three patterns for providing values to action inputs:

```agentscript
reasoning:
    actions:
        search: @actions.search_products
            # LLM slot-fills: extracts value from conversation
            with query = ...
            with category = ...

        lookup: @actions.get_customer
            # Variable binding: prefilled from state
            with customer_id = @variables.selected_customer
            # Literal value: fixed at definition time
            with include_archive = False
```

**Gating** — `available when` controls which actions the LLM can see based on current state:

```agentscript
reasoning:
    actions:
        check_status: @actions.order_status
            description: "Check your order status"
            available when @variables.order_id != ""

        place_order: @actions.create_order
            description: "Place a new order"
            available when @variables.cart_total > 0
```

**Output capture** — use `set` to store action outputs in variables:

```agentscript
run @actions.fetch_order
    with id = @variables.order_id
    set @variables.status = @outputs.status
    set @variables.total = @outputs.total
```

---

## 11. Utility Functions

Utility functions control flow and state. They do not call external systems.

**`@utils.transition to`** — permanent one-way handoff to another topic:

```agentscript
reasoning:
    actions:
        go_checkout: @utils.transition to @topic.checkout
            description: "Proceed to checkout"
            available when @variables.cart_has_items == True
```

Transition discards the current topic's prompt and starts fresh with the target topic.

**`@utils.escalate`** — route to a human agent (**service agents only** — requires a `connection messaging:` block, which is only valid for `AgentforceServiceAgent`; do not use in employee agents):

```agentscript
reasoning:
    actions:
        get_help: @utils.escalate
            description: "Connect with a live agent"
            available when @variables.needs_human == True
```

Escalation ends the current conversation and routes to the escalation system defined in the connection block.

**`@utils.setVariables`** — LLM-driven variable capture (slot-filling):

```agentscript
reasoning:
    actions:
        collect_info: @utils.setVariables
            description: "Collect customer preferences"
            with preferred_color = ...
            with budget = ...
```

The LLM extracts values from the conversation and populates the specified variables.

**`@topic.X`** — delegation to another topic with return:

```agentscript
reasoning:
    actions:
        consult_expert: @topic.expert_topic
            description: "Get expert guidance"
            available when @variables.needs_expert_help == True
```

Calling a topic as a tool runs that topic's reasoning, then returns control to the calling topic.

**Post-action directives apply only to `@actions`, not `@utils`**:

```agentscript
# WRONG — utilities don't support set
escalate: @utils.escalate
    set @variables.escalated = True

# CORRECT — only @actions support set
process: @actions.process_order
    set @variables.result = @outputs.status
```

Utilities cannot have output, so `set` is invalid.

---

## 12. Anti-Patterns

**WRONG: Using `transition to` in `reasoning.actions`**

```agentscript
# WRONG — this doesn't compile
reasoning:
    actions:
        go_next: transition to @topic.next
            description: "Go to next"
```

**Why it fails:** `reasoning.actions` expose tools to the LLM at reasoning time. The LLM needs an action reference, not a bare command. The runtime rejects bare `transition to` syntax in this context.

**CORRECT:**

```agentscript
reasoning:
    actions:
        go_next: @utils.transition to @topic.next
            description: "Go to next"
```

The `@utils.transition to` syntax creates a callable tool.

---

**WRONG: Using `@utils.transition to` in directive blocks**

```agentscript
# WRONG — compile error
after_reasoning:
    @utils.transition to @topic.next
```

**Why it fails:** Directive blocks (`before_reasoning`, `after_reasoning`) execute deterministically — the runtime handles them, not the LLM. They use bare `transition to` syntax.

**CORRECT:**

```agentscript
after_reasoning:
    transition to @topic.next
```

Bare `transition to` is deterministic — the runtime executes it directly.

---

**WRONG: Using lowercase booleans**

```agentscript
# WRONG
enabled: mutable boolean = true
verified: mutable boolean = false
is_premium: linked boolean

if @variables.is_premium == false:
    run @actions.show_basic_features
```

**Why it fails:** Agent Script requires `True` and `False` (capitalized first letter). The parser rejects lowercase `true`/`false`.

**CORRECT:**

```agentscript
enabled: mutable boolean = True
verified: mutable boolean = False
is_premium: linked boolean

if @variables.is_premium == False:
    run @actions.show_basic_features
```

Always use capitalized boolean values.

---

**WRONG: Mutable variable without default**

```agentscript
# WRONG — missing default
variables:
    customer_name: mutable string
```

**Why it fails:** During deterministic resolution, the runtime needs an initial value. Mutable variables must have defaults.

**CORRECT:**

```agentscript
variables:
    customer_name: mutable string = ""
```

Provide a default value.

---

**WRONG: Linked variable with default**

```agentscript
# WRONG — linked variables get value from source
variables:
    session_id: linked string = "default_session"
        source: @session.sessionID
```

**Why it fails:** Linked variables are populated by external context at runtime. Providing a default is contradictory.

**CORRECT:**

```agentscript
variables:
    session_id: linked string
        source: @session.sessionID
```

Omit the default.

---

**WRONG: Linked variable without source**

```agentscript
# WRONG — missing source
variables:
    user_role: linked string
```

**Why it fails:** The runtime cannot populate a linked variable without knowing where to get the value.

**CORRECT:**

```agentscript
variables:
    user_role: linked string
        source: @context.userRole
```

Specify a source.

---

**WRONG: Vague post-action instructions that don't name output fields**

```agentscript
# WRONG — generic "present the results" lets platform tools hijack the response
reasoning:
    instructions: ->
        | Use the {!@actions.get_station_status} action to retrieve station information.
          After receiving the results, present the station information to the user
          in a clear, organized way.
    actions:
        get_station_status: @actions.get_station_status
            with stationName = ...
```

**Why it fails:** When instructions say "present the results" without specifying *how*, the LLM often calls `show_command` instead of composing a text response — producing a generic "Here are the results:" wrapper with raw structured data. This can corrupt session state, causing subsequent turns to fail with "unexpected error."

**CORRECT:**

```agentscript
reasoning:
    instructions: ->
        | Use the {!@actions.get_station_status} action to retrieve station information.
          After receiving the results, write the data directly in your text response.
          For each station, include the stationName, projectStatus, crewMembers, and
          shieldStatus values from the action output. Use the exact values returned
          by the action — do NOT paraphrase or round.
          Do NOT use the show_command tool. Always compose your response as direct text.
    actions:
        get_station_status: @actions.get_station_status
            with stationName = ...
```

Three things make this work: (1) naming the specific output fields the LLM must include, (2) directing it to write a text response rather than calling a platform tool, (3) blocking `show_command` by name.

---

**WRONG: Post-action directive on utility**

```agentscript
# WRONG — utilities have no outputs
reasoning:
    actions:
        go_next: @utils.transition to @topic.next
            set @variables.transitioned = True
```

**Why it fails:** Utilities like `@utils.transition to` do not return outputs. The `set` directive only works with `@actions`.

**CORRECT:**

```agentscript
# If you need to record state, set before transitioning
before_reasoning:
    set @variables.last_topic = "current_topic"
    transition to @topic.next
```

---

**WRONG: Action loop (action remains available after execution)**

```agentscript
# WRONG — no gating, no post-action guidance, variable-bound input
reasoning:
    instructions: ->
        | Place an order using the {!@actions.create_order} action.
    actions:
        create_order: @actions.create_order
            with items = @variables.cart_items
```

**Why it fails:** Each reasoning cycle, the LLM sees all available actions and decides which to call. This action has no `available when` gate, so it is always available. The variable-bound input (`with items = @variables.cart_items`) means the action is "ready to go" every cycle with no slot-filling decision required. The instructions don't tell the LLM what to do after the action completes, so the LLM may call it repeatedly.

**CORRECT:**

```agentscript
reasoning:
    instructions: ->
        | Place an order using the {!@actions.create_order} action.
          After the order is created, confirm the order number.
          Do NOT call the action again — you have the result.
    actions:
        create_order: @actions.create_order
            with items = @variables.cart_items
            available when @variables.cart_total > 0
```

Three mitigations applied: (1) explicit post-action instructions telling the LLM to stop, (2) an `available when` gate so the action is only available when relevant, (3) clear instructions about what to do with the result.

---

**WRONG: Expecting LLM to reason without deterministic context**

```agentscript
# WRONG — no instructions prepare the LLM
topic check_status:
    reasoning:
        actions:
            lookup: @actions.fetch_status
```

**Why it fails:** The LLM needs instructions about when and how to use the action. Without prompt text from the reasoning instructions guiding the LLM, it may not call the action even when relevant.

**CORRECT:**

```agentscript
topic check_status:
    reasoning:
        instructions: ->
            | If the customer asks about their order status, use the {!@actions.fetch_status} action.
        actions:
            lookup: @actions.fetch_status
                with order_id = @variables.order_id
```

Always pair actions with guiding instructions in the reasoning block.

---

**WRONG: Gate topic transitions to router via `after_reasoning` without defensive instructions**

```agentscript
# WRONG — the router processes the gate's triggering message in the same turn
topic collect_username:
    reasoning:
        instructions: ->
            | Ask the customer for their username.
    after_reasoning:
        if @variables.username != "":
            transition to @topic.topic_selector

topic topic_selector:
    reasoning:
        instructions: ->
            | Route the customer's message:
              - Events → @topic.event_lookup
              - Venues → @topic.venue_booking
              - Weather → @topic.weather_forecast
              - Anything else → @topic.off_topic
```

**Why it fails:** When `collect_username` captures the username and `after_reasoning` transitions to `topic_selector`, both topics process in the same user turn. The router's reasoning fires against the user's original message (e.g., "My username is vivek.chawla"), not a fresh utterance. Since that message doesn't match any domain topic, the router sends it to `off_topic`.

**CORRECT:**

```agentscript
topic collect_username:
    reasoning:
        instructions: ->
            | Ask the customer for their username.
    after_reasoning:
        if @variables.username != "":
            transition to @topic.topic_selector

topic topic_selector:
    reasoning:
        instructions: ->
            | Route the customer's message to the right topic.
              If the customer just arrived from the username collection
              step, greet them and ask how you can help — do NOT route
              their previous message.
              - Events → @topic.event_lookup
              - Venues → @topic.venue_booking
              - Weather → @topic.weather_forecast
              - Anything else → @topic.off_topic
```

This pattern applies whenever a gate topic transitions into a routing topic via `after_reasoning`.
