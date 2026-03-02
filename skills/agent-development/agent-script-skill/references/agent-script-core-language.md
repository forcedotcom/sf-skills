# Agent Script: Core Language Reference

## Table of Contents

1. Execution Model
2. Syntax Basics
3. Configuration and Variables
4. Topics and Flow Control
5. Actions and Utilities
6. Anti-Patterns

---

## 1. Execution Model

Agent Script operates in two phases:

**Phase 1: Deterministic Resolution** — Runtime executes reasoning instructions top-down: evaluates `if`/`else`, runs actions via `run`, sets variables via `set`. Builds prompt string by accumulating `|` pipe text and resolving conditionals. If `transition` occurs, discards current prompt and starts with target topic. **LLM not involved yet.**

**Phase 2: LLM Reasoning** — Runtime passes resolved prompt + reasoning actions (tools) to LLM. LLM decides what to do — can call available actions but cannot modify prompt text.

**Example:**

```agentscript
topic check_order:
    reasoning:
        instructions: ->
            if @variables.order_id != "":
                run @actions.fetch_order
                    with id = @variables.order_id
                    set @variables.status = @outputs.status

            | Your order status is {!@variables.status}.
              You can modify it using {!@actions.update_order}.

        actions:
            update: @actions.update_order
                with order_id = @variables.order_id
```

If `order_id = "1001"` and `fetch_order` returns `status = "shipped"`, runtime resolves to:

```
Your order status is shipped.
You can modify it using update_order.
```

LLM receives this prompt + `update` tool and decides whether to call based on user's next message.

**Key insight**: Deterministic logic controls WHAT the agent knows (resolved prompt). LLM controls WHETHER/HOW to act.

---

## 2. Syntax Basics

### File Structure

Mandatory order (system, config, start_agent, topic required; others optional):

```agentscript
system:
    instructions: "Global LLM directives"
    messages:
        welcome: "..."
        error: "..."

config:
    developer_name: "Name"
    agent_type: "AgentforceServiceAgent"  # or AgentforceEmployeeAgent
    default_agent_user: "user@example.com"  # For ServiceAgent only

variables:
    my_var: mutable string = ""
    session_id: linked string
        source: @session.sessionID

start_agent topic_selector:
    description: "..."
    reasoning:
        instructions: -> ...
        actions: ...

topic my_topic:
    description: "..."
    actions: ...              # Optional: action definitions
    before_reasoning: ...     # Optional: pre-reasoning logic
    reasoning:
        instructions: -> ...  # Required
        actions: ...          # Optional: tools for LLM
    after_reasoning: ...      # Optional: post-reasoning logic
```

### Naming Rules

All names (developer_name, topics, variables, actions): letters, numbers, underscores. Start with letter. No consecutive underscores. No trailing underscore. Max 80 chars. `snake_case` recommended.

**Indentation**: 4 spaces per level. Never tabs. **Comments**: `#`

### Operators

- **Comparison**: `==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `is not`
- **Logical**: `and`, `or`, `not`
- **Arithmetic**: `+`, `-` (no `*`, `/`, `%`)
- **Access**: `.` (property), `[]` (index)
- **Conditional**: `x if condition else y`
- **Template injection**: `{!expression}` in `|` pipe text

**Resource references**: `@actions.X`, `@topic.X`, `@variables.X`, `@outputs.X`, `@utils.X`

**Do NOT use `<>` for inequality** — use `!=`:

```agentscript
# WRONG
if @variables.status <> "pending":

# CORRECT
if @variables.status != "pending":
```

---

## 3. Configuration and Variables

### System Block

Required. Global instructions + messages:

```agentscript
system:
    instructions: "You are a helpful assistant. Be professional."
    messages:
        welcome: "Hello! How can I help?"
        error: "Sorry, something went wrong."
```

### Config Block

Required fields:
- `developer_name` — MUST match `AiAuthoringBundle` directory name exactly (e.g., directory `Travel_Advisor/` requires `developer_name: "Travel_Advisor"`)
- `default_agent_user` (for `AgentforceServiceAgent` only) — Salesforce username with Einstein Agent license. Invalid user causes misleading "Internal Error, try again later" at publish. Query valid users: `sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"`. **Immutable after first publish.**

Optional fields:
- `agent_label` — display name
- `description` — what agent does
- `agent_type` — `"AgentforceServiceAgent"` (customer-facing, requires `default_agent_user`) or `"AgentforceEmployeeAgent"` (internal, no `default_agent_user`)

Generated boilerplate defaults to Service Agent (includes MessagingSession linked variables, escalation topic). For Employee Agent, remove `default_agent_user`, MessagingSession variables, and escalation topics.

### Variables

**Mutable** (read/write, MUST have default):

```agentscript
variables:
    name: mutable string = ""
        description: "Customer name"  # Optional, for LLM slot-filling context
    count: mutable number = 0
    active: mutable boolean = True    # MUST be capitalized!
    data: mutable object = {}
    items: mutable list[string] = []
```

**Linked** (read-only from external context, MUST have source, NO default):

```agentscript
variables:
    session_id: linked string
        source: @session.sessionID
    user_id: linked string
        source: @MessagingSession.MessagingEndUserId
```

**Types**:
- **Mutable**: `string`, `number`, `boolean`, `object`, `date`, `timestamp`, `currency`, `id`, `list[T]`
- **Linked**: same except NO `list`
- **Action params**: mutable types plus `datetime`, `time`, `integer`, `long`

**Boolean capitalization**: Always `True`/`False`, never `true`/`false`

**Publish-time Apex type restriction**: For Apex `Integer`, `Date`, `Datetime` fields, use `object` + `complex_data_type_name`. See type mapping table in `agent-design-and-spec-creation.md` Section 4.

**Template injection**: Use `{!@variables.X}` in prompt text (inside `|` sections):

```agentscript
instructions: |
    Hello, {!@variables.name}! Balance: {!@variables.balance}
```

Bare `@variables.X` (without braces) is valid in logic contexts (`if @variables.X == True:`) but won't interpolate in prompts.

---

## 4. Topics and Flow Control

### Topic Structure

```agentscript
topic order_lookup:
    description: "Handle order inquiries"  # Required - LLM uses for relevance

    system:  # Optional - override global system instructions for this topic
        instructions: "Be detailed about order status."

    actions:  # Optional - define callable actions
        find_order:
            target: "flow://SearchOrder"
            description: "Search by order ID"
            inputs:
                order_id: string
            outputs:
                status: string

    before_reasoning:  # Optional - runs before LLM reasoning
        if @variables.session_expired:
            transition to @topic.login

    reasoning:  # Required
        instructions: ->
            | Help customer find order.
        actions:
            search: @actions.find_order
                with order_id = ...

    after_reasoning:  # Optional - runs after LLM reasoning
        if @variables.order_complete:
            transition to @topic.confirmation
```

### Reasoning Instructions

**Arrow syntax (`->`)** for logic + prompt:

```agentscript
reasoning:
    instructions: ->
        if @variables.verified:
            run @actions.get_account
                with user_id = @variables.user_id
                set @variables.account_info = @outputs.account

        | Tell the user their account balance.
```

**Static `|` pipe** for prompt-only (no logic):

```agentscript
reasoning:
    instructions: |
        Help customer find venue.
        After receiving results from {!@actions.search_venues}, present them.
        Do NOT call action again unless customer asks.

    actions:
        find_venue: @actions.search_venues
            with location = ...
```

**The `|` pipe operator works alongside `reasoning.actions`** — both are valid in same reasoning block. Pipe builds prompt text, actions define LLM tools.

**If/Else** (no `else if`):

```agentscript
if @variables.status == "pending":
    run @actions.notify_pending
else:
    run @actions.notify_complete
```

Nest conditions with separate `if` blocks:

```agentscript
if @variables.status == "pending":
    if @variables.priority == "high":
        run @actions.escalate
```

### Flow Control

**Start agent** (mandatory entry point):

```agentscript
start_agent topic_selector:
    description: "Route to appropriate topic"
    reasoning:
        actions:
            go_orders: @utils.transition to @topic.order_info
                description: "For order inquiries"
```

**LLM-chosen transitions** (in `reasoning.actions` with `@utils.transition to`):

```agentscript
reasoning:
    actions:
        go_next: @utils.transition to @topic.next_topic
            description: "Move to next topic"
            available when @variables.ready == True
```

**Deterministic transitions** (in directive blocks, bare `transition to`):

```agentscript
before_reasoning:
    if @variables.not_authenticated:
        transition to @topic.login

after_reasoning:
    if @variables.complete:
        transition to @topic.summary
```

Do NOT use `@utils.transition to` in directive blocks — causes compilation errors.

**Delegation with return** (use `@topic.X`):

```agentscript
reasoning:
    actions:
        ask_expert: @topic.expert_consultation
            description: "Consult expert"
```

Target topic runs reasoning, then returns control. Different from `@utils.transition to` (one-way, no return).

---

## 5. Actions and Utilities

### Action Definition

```agentscript
actions:
    get_customer:
        target: "flow://GetCustomerInfo"  # Required
        description: "Fetches customer info"
        label: "Get Customer"  # Optional display name
        require_user_confirmation: False
        include_in_progress_indicator: True
        progress_indicator_message: "Looking up..."
        inputs:
            customer_id: string
                description: "Customer's ID"
                is_required: True
        outputs:
            name: string
                is_displayable: True
```

**Target formats** — `"type://Name"`:
- Common: `flow`, `apex`, `prompt`, `standardInvocableAction`, `externalService`, `api`
- Others: `quickAction`, `apexRest`, `serviceCatalog`, `integrationProcedureAction`, `expressionSet`, `cdpMlPrediction`, `externalConnector`, `slack`, `namedQuery`, `auraEnabled`, `mcpTool`, `retriever`

**Deterministic invocation** (always runs):

```agentscript
reasoning:
    instructions: ->
        run @actions.get_customer
            with customer_id = @variables.customer_id
            set @variables.name = @outputs.name
```

**LLM exposure** (LLM decides):

```agentscript
reasoning:
    actions:
        lookup: @actions.get_customer
            description: "Look up customer"
            with customer_id = @variables.selected_customer
            set @variables.name = @outputs.name
```

**Input binding patterns**:

```agentscript
reasoning:
    actions:
        search: @actions.search_products
            with query = ...             # LLM slot-fills
            with category = ...          # LLM slot-fills
            with customer_id = @variables.user_id  # Variable binding
            with limit = 10              # Literal value
```

**Gating** — control action visibility:

```agentscript
reasoning:
    actions:
        check_status: @actions.order_status
            description: "Check order status"
            available when @variables.order_id != ""
```

**Post-action directives** (only for `@actions`, NOT `@utils`):

```agentscript
run @actions.process_order
    with order_id = @variables.order_id
    set @variables.result = @outputs.status
    if @outputs.success == True:
        transition to @topic.confirmation
```

### Utility Functions

**`@utils.transition to`** — one-way handoff:

```agentscript
reasoning:
    actions:
        go_checkout: @utils.transition to @topic.checkout
            description: "Proceed to checkout"
```

**`@utils.escalate`** — route to human:

```agentscript
reasoning:
    actions:
        get_help: @utils.escalate
            description: "Connect with live agent"
```

**`@utils.setVariables`** — LLM slot-filling:

```agentscript
reasoning:
    actions:
        collect: @utils.setVariables
            description: "Collect preferences"
            with preferred_color = ...
            with budget = ...
```

Variables must be predefined in `variables:` block.

**`@topic.X`** — delegation with return:

```agentscript
reasoning:
    actions:
        consult: @topic.expert_topic
            description: "Get expert guidance"
```

**Post-action directives only work with `@actions`, not `@utils` or `@topic`**. Utilities have no outputs, so `set` is invalid.

---

## 6. Anti-Patterns

Each shows WRONG then CORRECT with semantic explanation.

### 1. Using `transition to` in `reasoning.actions`

```agentscript
# WRONG — doesn't compile
reasoning:
    actions:
        go_next: transition to @topic.next

# CORRECT
reasoning:
    actions:
        go_next: @utils.transition to @topic.next
```

**Why**: `reasoning.actions` expose LLM tools. LLM needs action reference (`@utils.transition to`), not bare command.

---

### 2. Using `@utils.transition to` in directive blocks

```agentscript
# WRONG — compile error
after_reasoning:
    @utils.transition to @topic.next

# CORRECT
after_reasoning:
    transition to @topic.next
```

**Why**: Directive blocks execute deterministically. Use bare `transition to` syntax.

---

### 3. Lowercase booleans

```agentscript
# WRONG
enabled: mutable boolean = true
if @variables.is_premium == false:

# CORRECT
enabled: mutable boolean = True
if @variables.is_premium == False:
```

**Why**: Agent Script requires capitalized `True`/`False`. Parser rejects lowercase.

---

### 4. Mutable variable without default

```agentscript
# WRONG
variables:
    customer_name: mutable string

# CORRECT
variables:
    customer_name: mutable string = ""
```

**Why**: Runtime needs initial value during deterministic resolution. Mutable variables must have defaults.

---

### 5. Linked variable with default

```agentscript
# WRONG
session_id: linked string = ""
    source: @session.sessionID

# CORRECT
session_id: linked string
    source: @session.sessionID
```

**Why**: Linked variables get values from external context via `source`. Default is invalid.

---

### 6. Linked variable with `list` type

```agentscript
# WRONG
items: linked list[string]
    source: @session.items

# CORRECT
items: mutable list[string] = []
```

**Why**: Linked variables cannot be `list` type. Use mutable instead.

---

### 7. Using `...` as variable default

```agentscript
# WRONG
variables:
    name: mutable string = ...

# CORRECT
variables:
    name: mutable string = ""
```

**Why**: `...` is slot-filling syntax for action inputs, not variable defaults. Mutable variables need concrete defaults.

---

### 8. Post-action directives on utilities

```agentscript
# WRONG — utilities don't support set
escalate: @utils.escalate
    set @variables.escalated = True

# CORRECT — only @actions support set
process: @actions.process_order
    set @variables.result = @outputs.status
```

**Why**: Utilities have no outputs. `set` requires `@outputs`, which only `@actions` produce.

---

### 9. Variable binding without brackets in prompts

```agentscript
# WRONG — won't interpolate
instructions: |
    Your balance: @variables.balance

# CORRECT
instructions: |
    Your balance: {!@variables.balance}
```

**Why**: Bare `@variables.X` is valid in logic contexts (`if` conditions) but won't interpolate in prompt text. Use `{!@variables.X}` for template injection.

---

### 10. developer_name mismatch

```agentscript
# WRONG — directory is Travel_Advisor/, config says Travel_Agent
config:
    developer_name: "Travel_Agent"

# CORRECT — must match directory name exactly
config:
    developer_name: "Travel_Advisor"
```

**Why**: `developer_name` must exactly match the `AiAuthoringBundle` directory name. Mismatch causes deploy failures.
