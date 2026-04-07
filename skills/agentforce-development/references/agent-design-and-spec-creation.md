# Agent Design and Spec Creation

## Table of Contents

1. Agent Spec: Structure and Lifecycle
2. Discovery Questions
3. Environment Prerequisites
4. Topic Architecture
5. Mapping Logic to Actions
6. Transition Patterns
7. Deterministic vs. Subjective Flow Control
8. Gating Patterns
9. Action Loop Prevention

---

## 1. Agent Spec: Structure and Lifecycle

An **Agent Spec** is a structured design document describing an agent's purpose, topics, actions, state, control flow, and behavioral intent. When creating a new agent, produce the Agent Spec before writing Agent Script code. When comprehending or diagnosing an existing agent, reverse-engineer an Agent Spec from the `.agent` file to make the agent's design explicit.

### What an Agent Spec Contains

- **Purpose & Scope** — what the agent does, in plain language
- **Behavioral Intent** — what the agent is supposed to achieve (requirements and constraints), not just what the code does
- **Topic Map** — a Mermaid flowchart showing all topics, transitions (with type labels: handoff or delegation), and when transitions occur
- **Actions & Backing Logic** — each action's name, its backing implementation (Apex class, Flow, Prompt Template), inputs/outputs with visibility decisions, and whether the backing logic exists or needs creation
- **Variables** — declarations, types, default values, which topics set/read them, and what gates they control
- **Gating Logic** — conditions that govern action visibility or instruction evaluation, with rationale for each. Always include this section; if no gating applies, state "No gating required" so reviewers know it was considered, not overlooked.

### Directional vs. Observational Entries

Agent Spec entries can be directional or observational — both are valid:

- **Directional:** "The `confirm_booking` action needs an Apex class `BookingConfirmer` that accepts reservation_id (string), guest_name (string), and returns confirmation_number (string), booking_date (date)." This is a gap you're creating acceptance criteria for.

- **Observational:** "The `fetch_weather` action is backed by Apex class `WeatherService`, invoked via `apex://WeatherService`. Accepts dateToCheck (date), returns maxTemp/minTemp (number)." This documents existing backing logic.

Both go in the same Agent Spec section.

### Lifecycle Stages

The Agent Spec evolves across the agent's lifecycle:

**Creation (sparse).** Purpose, topic names, rough descriptions, directional notes about backing logic ("this action needs an Apex class that accepts X, returns Y"). No flowchart yet. Entries are mostly placeholders.

**Build (filled).** Flowchart added with transition types labeled. Backing logic mapped (existing implementations identified with filenames, missing implementations stubbed with protocols and I/O specs). Variables documented with their usage and gating impact. Gating rationale explained.

**Comprehension (reverse-engineered).** Starting from an existing `.agent` file, produce a complete Agent Spec by parsing topics, tracing transitions, analyzing actions, and documenting state. This is the "what does this agent do?" output.

**Diagnosis (reference).** Compare actual runtime behavior against the Agent Spec to find where intent and implementation diverge.

### Agent Spec Template

Use the starter spec template at `assets/agent-spec-template.md` for new agents.

---

## 2. Discovery Questions

These five question categories drive the content of your Agent Spec. When creating a new agent, use them to elicit requirements from the human. When comprehending or diagnosing an existing agent, extract the answers from the `.agent` file and project files.

**Resolve as many questions as possible from available context before asking the human.** Scan existing code, project metadata, prior conversation, and any provided requirements. Only surface questions the human must answer — never forward this list verbatim.

### Agent Identity & Purpose *(feeds Purpose & Scope)*

- What is the agent's name? (no spaces, letters/numbers/underscores only)
- What is the agent's primary purpose in one sentence?
- What should the welcome message say?
- What personality should the agent have? (professional, friendly, formal, casual)
- What error message should the agent show if something breaks?

### Topics & Conversation Flow *(feeds Topic Map)*

- What distinct conversation areas (topics) does the agent need?
- Which topic is the entry point? (where conversations start)
- What are the possible transitions between topics?
- Are there topics that delegate to others and need to return?
- Are there guardrail topics (off-topic redirection, ambiguity handling, security gates)?

### Reasoning & Instructions *(feeds Behavioral Intent)*

- What should the agent do in each topic?
- What conditions change the instructions? (if guest is premium, if step 1 is complete)
- Should the agent do anything before or after reasoning in a given topic? (e.g., security checks, data fetches, automatic transitions)
- What data transformations (if any) does the LLM need to do?

### Actions & External Systems *(feeds Actions & Backing Logic)*

- What external systems does the agent call?
  - Salesforce Flows (autolaunched only)
  - Apex classes (invocable only)
  - Prompt Templates
  - External APIs (not directly; must be wrapped in Apex or Flow)
- For each action: What inputs? What outputs? When should it be available?
- What custom objects exist in the project? Scan `objects/` for `.object-meta.xml` files. Check relationships (lookup, master-detail) between objects — related objects often contain data the agent should expose even when not explicitly mentioned in the prompt.

### State Management *(feeds Variables, Gating Logic)*

- What information must persist across the conversation? (customer name, preferences, process state)
- What external context is needed? (session ID, user record, linked fields)
- What conditions should trigger different behavior in the same topic? (is_premium, role, completed_steps)

---

## 3. Environment Prerequisites

**⚠️ MANDATORY: Run these checks immediately after determining the agent type during discovery.** Do not proceed to topic architecture or code generation until the environment is validated.

### `AgentforceEmployeeAgent`

1. Confirm the config block does NOT include `default_agent_user`. If the generated boilerplate includes it, remove it along with any MessagingSession linked variables and escalation topic.

**⚠️ Setting `default_agent_user` on an employee agent causes publish and preview to fail with an unhelpful "unknown error."**

### `AgentforceServiceAgent`

REQUIRES `default_agent_user`. Query the org to find an active Einstein Agent User:

```bash
sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
```

**If results are returned:** Ask which username to use. Record choice in the Agent Spec Configuration section. Verify permissions per [Agent User Setup & Permissions](agent-user-setup.md).

**If no results are returned:** STOP. Do NOT invent a username. Ask if you should create a new user, then read [Agent User Setup & Permissions](agent-user-setup.md) for user creation instructions.

**WRONG:** Fabricating a username when query returns nothing
```
default_agent_user: "myagent@example.com"   # made up, will fail at publish
```

**RIGHT:** Stopping and asking to create a new user
```
"No Einstein Agent User found in this org. Would you like me to create one for you?"
```

### Recording Prerequisites in the Agent Spec

Add a "Configuration" section to the Agent Spec:

- **Agent type**: `AgentforceServiceAgent` or `AgentforceEmployeeAgent`
- **Default agent user**: confirmed username (service agents), or "N/A — employee agent"
- **Permissions verified**: yes/no — see [Agent User Setup & Permissions](agent-user-setup.md)

---

## 4. Topic Architecture

Topics are states in a finite state machine. When designing a new agent, plan your topic structure before writing code. When comprehending an existing agent, identify which topic strategies and architecture pattern it uses.

### Topic Strategies

Every topic in an agent serves one of three roles: domain, guardrail, or escalation.

**Domain Topics.** The core conversation areas where the agent does its work. Each domain topic handles a specific area (orders, billing, weather, events) with its own instructions, actions, and state. Most agents have 1-5 domain topics.

**Guardrail Topics.** Specialized topics that enforce agent boundaries. The standard Agentforce template includes two guardrail topics by default: `off_topic` (redirects users back to the agent's scope) and `ambiguous_question` (asks for clarification instead of guessing). Preserve these when modifying existing agents.

```agentscript
topic off_topic:
    description: "Handle off-topic requests"
    reasoning:
        instructions: ->
            | You asked about something outside my scope.
              I can only help with [list your capabilities].
              What can I help you with today?

topic ambiguous_question:
    description: "Ask for clarification"
    reasoning:
        instructions: ->
            | I didn't quite understand your request.
              Can you provide more details about what you need?
```

**Escalation Topics.** Hand off to a human via `@utils.escalate`. This is a permanent exit — the user leaves the agent for a support channel (phone, email, chat with a human). Once triggered, the agent session ends. The escalation action does NOT return.

```agentscript
topic escalation:
    reasoning:
        actions:
            escalate: @utils.escalate
                description: "Connect with a human agent"
```

### Single-Topic vs. Multi-Topic

Decide this before choosing an architecture pattern.

Use **single-topic** if:
- The agent handles one domain only (FAQ, weather checker, status lookup)
- All interactions naturally stay in the same context
- No complex state transitions needed

Use **multi-topic** if:
- The agent handles multiple distinct domains (customer service: orders + billing + account)
- Different topics have different instructions or action sets
- Users may need to switch contexts mid-conversation
- You need different entry points or security gates

### Architecture Patterns

**Hub-and-Spoke.** One central topic (the router) transitions to specialized domain topics. The router is typically the `start_agent` topic. Each spoke handles a specific domain and may transition back to the router or to other spokes. Use when the agent handles multiple distinct domains that don't naturally flow together.

Example: The Local Info Agent. The `topic_selector` topic (hub) routes to domain and guardrail topics (spokes).

```agentscript
start_agent topic_selector:
    reasoning:
        actions:
            go_to_weather: @utils.transition to @topic.local_weather
            go_to_events: @utils.transition to @topic.local_events
            go_to_hours: @utils.transition to @topic.resort_hours
            go_to_off_topic: @utils.transition to @topic.off_topic
            go_to_ambiguous_question: @utils.transition to @topic.ambiguous_question

# Domain topics — each has its own instructions and actions
topic local_weather:
    reasoning:
        instructions: | Handle weather questions.

topic local_events:
    reasoning:
        instructions: | Handle event questions.

# resort_hours, off_topic, ambiguous_question defined further down the file
```

**Linear Flow.** Topics form a pipeline: start → step 1 → step 2 → step 3 → end. Users progress through stages without backtracking. Use for multi-step workflows with mandatory ordering (application forms, onboarding, troubleshooting trees).

```agentscript
start_agent intake:
    reasoning:
        actions:
            go_next: @utils.transition to @topic.verification

topic verification:
    reasoning:
        actions:
            go_next: @utils.transition to @topic.details_gathering

topic details_gathering:
    reasoning:
        actions:
            go_next: @utils.transition to @topic.confirmation
```

**Escalation Chain.** Tiered support where each level has increasing capabilities. First-level resolves common issues with basic actions; second-level has access to more powerful actions or broader authority; final level escalates to a human. Use when support difficulty varies and you want to resolve simple issues quickly without involving higher tiers.

```agentscript
topic level_1_support:
    reasoning:
        instructions: | Try to resolve the issue using the FAQ and basic troubleshooting.
        actions:
            check_faq: @actions.search_faq
            escalate: @utils.transition to @topic.level_2_support

topic level_2_support:
    reasoning:
        instructions: | You have access to account tools. Try to resolve before escalating.
        actions:
            lookup_account: @actions.get_account_details
            modify_account: @actions.update_account
            escalate_to_human: @utils.escalate
```

**Verification Gate.** A security or permission check before allowing access to protected topics. The gate validates the user, then transitions to the protected topic or denies access.

```agentscript
start_agent security_gate:
    reasoning:
        actions:
            go_admin: @utils.transition to @topic.admin_panel
                available when @variables.user_role == "admin"
            go_denied: @utils.transition to @topic.access_denied
                available when @variables.user_role != "admin"

topic access_denied:
    reasoning:
        instructions: | You don't have permission to access this.
```

**Single-Topic.** The entire agent is one topic — no transitions. Use for focused QA agents where all interactions stay in the same domain.

```agentscript
start_agent faq:
    description: "Answer questions about pricing"
    reasoning:
        instructions: | Answer questions about our pricing plans.
        actions:
            lookup_plan: @actions.get_plan_details
```

### Composing Patterns

Real agents often combine patterns. A hub-and-spoke agent may use a verification gate before protected spokes. A linear flow may include escalation exits at each stage. When composing, each topic still serves exactly one role (domain, guardrail, or escalation) — the architecture pattern determines how they connect.

---

## 5. Mapping Logic to Actions

Every action in Agent Script needs backing logic — a Salesforce implementation that does the work. When creating a new agent, identify existing backing logic and stub what's missing. When comprehending an existing agent, trace each action to its backing implementation to understand what it does.

### Valid Backing Logic Types

The most common backing logic types are Apex, Flows, and Prompt Templates.

**Apex**: Only **invocable Apex classes** work. A regular Apex class, even if it has public methods, will not work. Invocable classes use two key annotations:

`@InvocableMethod` marks the entry point. Its attributes: `label` (human-readable name), `description` (what the method does). Read these when comprehending existing backing logic.

> ⚠️ **An Apex class can only have ONE `@InvocableMethod`.** If you need multiple actions, create separate classes — one per action.

`@InvocableVariable` marks each input and output field on the inner Request/Result classes. Its attributes: `label` (human-readable field name), `description` (what the field represents), `required` (whether the field must be provided). Use these to build action input/output definitions.

```apex
// WRONG — regular class, not invocable
public class WeatherFetcher {
    public static String getWeather(String date) { ... }
}

// RIGHT — invocable class with annotated I/O (multiline annotations)
public class WeatherFetcher {
    public class Request {
        @InvocableVariable(
            label='Date'
            description='Date to check weather for'
            required=true
        )
        public Date dateToCheck;
    }
    public class Result {
        @InvocableVariable(
            label='Max Temp'
            description='Maximum temperature in Fahrenheit'
        )
        public Decimal maxTemp;
        @InvocableVariable(
            label='Min Temp'
            description='Minimum temperature in Fahrenheit'
        )
        public Decimal minTemp;
    }
    @InvocableMethod(
        label='Fetch Weather'
        description='Gets weather forecast for a given date'
    )
    public static List<Result> getWeather(List<Request> requests) { ... }
}
```

Wire with: `target: "apex://ClassName"`

**Flows**: Only **autolaunched Flows** work. Screen Flows, record-triggered Flows, and schedule-triggered Flows will not work. The Flow must start only when explicitly invoked.

Wire with: `target: "flow://FlowApiName"`

**Prompt Templates**: Salesforce Prompt Templates (custom or industry-specific).

Wire with: `target: "prompt://TemplateName"` (short form). The long form `generatePromptResponse://TemplateName` also works but prefer the short form.

### How to Identify Existing Backing Logic

Read `sfdx-project.json` and look at the `packageDirectories` array — each entry's `path` field tells you where source files live (typically `force-app/main/default/`).

Then scan for each type within those directories:

**Finding invocable Apex:** Search `classes/` for files containing `@InvocableMethod`. For each match, read the class to extract the `@InvocableVariable` annotations on its inner `Request` and `Result` classes — these define the action's input and output contract. Pay attention to the `@InvocableVariable` types: they map to Agent Script types (`String` → `string`, `Boolean` → `boolean`, `Decimal` → `number`, `Integer` → `integer`, `Date` → `date`, `Datetime` → `datetime`). See the full type mapping table in "Connecting Backing Logic to Action Definitions" below.

**Finding autolaunched Flows:** Search `flows/` for `.flow-meta.xml` files. Read each file and check the `<processType>` element. Only `AutoLaunchedFlow` is valid for actions. Examine the `<variables>` elements to identify inputs (`isInput=true`) and outputs (`isOutput=true`) with their data types.

**Finding Prompt Templates:** Search `promptTemplates/` for template metadata files. Review the template's input variables and output format.

### How to Map Existing Implementations

For each candidate implementation, verify it matches what the action needs:

- **Input contract** — does the implementation accept the parameters the action will send?
- **Output contract** — does the implementation return data the agent needs?
- **Target format** — use the correct protocol (`apex://`, `flow://`, `prompt://`)

Example — existing Apex class `OrderLookup`:

```apex
public class OrderLookup {
    public class Request {
        @InvocableVariable(required=true)
        public String orderId;
    }
    public class Result {
        @InvocableVariable public String status;
        @InvocableVariable public Decimal amount;
        @InvocableVariable public Date orderDate;
    }
    @InvocableMethod(label='Fetch Order')
    public static List<Result> getOrderStatus(List<Request> requests) { ... }
}
```

In the Agent Spec, record:
```
check_order action:
  Backing: Apex class OrderLookup (invocable)
  Target: apex://OrderLookup
  Inputs: orderId (string, required)
  Outputs: status (string), amount (number), orderDate (date)
  Status: IMPLEMENTED
```

### Connecting Backing Logic to Action Definitions

Each `@InvocableVariable` on the request class becomes an action input; each on the result class becomes an output. The `target` field points to the implementation.

**Critical: Input and output names must exactly match the Apex `@InvocableVariable` field names, character-for-character.** If the Apex field is `dateToCheck`, the Agent Script input must be `dateToCheck` — not `date_to_check`, not `DateToCheck`. The platform validates these names at publish time; mismatches cause publish failures.

```agentscript
# WRONG — snake_case doesn't match the Apex field names
topic orders:
    actions:
        check_order: @actions.check_order
            target: "apex://OrderLookup"
            inputs:
                order_id: string     # Apex field is orderId, NOT order_id
            outputs:
                order_date: date     # Apex field is orderDate, NOT order_date

# RIGHT — names match Apex @InvocableVariable field names exactly
topic orders:
    actions:
        check_order: @actions.check_order
            target: "apex://OrderLookup"
            description: "Look up order status"
            inputs:
                orderId: string      # matches Request.orderId
            outputs:
                status: string       # matches Result.status
                    filter_from_agent: False
                amount: number       # matches Result.amount (Decimal → number)
                    filter_from_agent: False
                orderDate: date      # matches Result.orderDate (Date → date)
                    filter_from_agent: False
```

#### Primitive Agent Script Type Mapping

Primitive types (individual and arrays) require only an Agent Script type.

| Agent Script Type | Apex | Flow | Prompt Template |
|---|---|---|---|
| `string` | String | Text | UNGROUNDED |
| `boolean` | Boolean | Boolean | UNGROUNDED |
| `number` | Decimal | UNGROUNDED | UNGROUNDED |
| `integer` | Integer | UNGROUNDED | UNGROUNDED |
| `long` | Long | UNGROUNDED | UNGROUNDED |
| `date` | Date | Date | UNGROUNDED |
| `datetime` | Datetime | UNGROUNDED | UNGROUNDED |
| `list[T]` | `List<T>` | UNGROUNDED | UNGROUNDED |

`integer`, `long`, and `datetime` are valid in action I/O only — not valid for agent variables.

#### Complex Agent Script Type Mapping

Complex types (Apex classes, SObject records) require both `object` or `list[object]` AND `complex_data_type_name`. **Correct value depends on action `target`, not data shape.**

| Target | Backing Logic Type | Agent Script Type | `complex_data_type_name` Format | Example |
|---|---|---|---|---|
| `apex://` | `List<InnerClass>` | `list[object]` | `@apexClassType/c__Class$InnerClass` | `@apexClassType/c__StationSupplyChecker$SupplyInfo` |
| `apex://` | `InnerClass` (single) | `object` | `@apexClassType/c__Class$InnerClass` | `@apexClassType/c__StationSupplyChecker$SupplyInfo` |
| `flow://` | SObject collection | `list[object]` | `lightning__recordInfoType` | `lightning__recordInfoType` |
| `flow://` | Single SObject | `object` | `lightning__recordInfoType` | `lightning__recordInfoType` |
| `prompt://` | UNGROUNDED | UNGROUNDED | UNGROUNDED | UNGROUNDED |

Format: `@apexClassType/c__<OuterClass>$<InnerClass>`. The `c__` prefix is the default namespace. The `$` separates outer from inner class.

NEVER use `lightning__recordInfoType` for `apex://` targets. ONLY use for Flow SObject returns. 

```agentscript
# WRONG — lightning__recordInfoType with apex:// target
    get_properties:
        target: "apex://PropertyQueryService"
        outputs:
            properties: list[object]
                complex_data_type_name: "lightning__recordInfoType"

# WRONG — outer class name only, missing $InnerClass
    get_properties:
        target: "apex://PropertyQueryService"
        outputs:
            properties: list[object]
                complex_data_type_name: "@apexClassType/c__PropertyQueryService"

# RIGHT — full inner class path, matches apex:// target
    get_properties:
        target: "apex://PropertyQueryService"
        outputs:
            properties: list[object]
                complex_data_type_name: "@apexClassType/c__PropertyQueryService$PropertyInfo"
```

Example — `flow://` target returning records:
```agentscript
    get_customer:
        target: "flow://GetCustomerInfo"
        outputs:
            customer_info: object
                complex_data_type_name: "lightning__recordInfoType"
```

Example — `apex://` target returning structured data:
```agentscript
    check_supplies:
        target: "apex://StationSupplyChecker"
        outputs:
            supplies: list[object]
                complex_data_type_name: "@apexClassType/c__StationSupplyChecker$SupplyInfo"
```

#### Output Visibility (`filter_from_agent`)

Each output requires a visibility decision: Should the agent display this value to the user, or keep it internal for routing and logic?

The `filter_from_agent` property controls this. The name is inverted — `True` means the output is **filtered out** (hidden from the user), `False` means it is **visible**.

Capture this decision during spec creation using the **Visible to User?** column in the Agent Spec template. Wrong choice causes agent to retrieve data but never display it.

| `filter_from_agent` | User sees the value? |
|---|---|
| `False` | Yes — displayed in the agent's response |
| `True` | No — available to the LLM for reasoning but not shown |

**Show** outputs the user asked for: records, summaries, computed results, status messages.

**Hide** outputs that are internal plumbing: success flags (`isSuccess`, `hasData`), IDs consumed by downstream actions, routing signals used in `available when` gates.

```agentscript
    get_properties:
        target: "apex://PropertyQueryService"
        outputs:
            properties: list[object]
                filter_from_agent: False   # Desired info. Show to user
                complex_data_type_name: "@apexClassType/c__PropertyQueryService$PropertyInfo"
            hasData: boolean
                filter_from_agent: True    # Internal flag. Hide from user
```

**⚠️ Invalid backing logic (non-autolaunched Flow, non-invocable Apex) may pass validation and simulation-mode preview. The failure surfaces at deploy or as cryptic runtime errors in live mode.** Always verify the backing logic type before wiring.

### How to Stub Missing Logic

When no backing logic exists for an action, stub it as an invocable Apex class. Always use Apex for stubs — do not attempt to hand-craft Flow XML or Prompt Template metadata.

First, record the stub in the Agent Spec:
```
fetch_invoice action:
  Backing: (needs creation)
  Target: apex://InvoiceFetcher (proposed)
  Inputs: invoiceId (string, required)
  Outputs: invoiceAmount (number), dueDate (date), status (string)
  Requirements: Invocable Apex class that accepts invoiceId,
                queries Invoice records, returns amount/dueDate/status
```

Second, find the default package directory by reading `sfdx-project.json` at the project root and locating the `packageDirectories` entry where `"default": true`. The `path` value in that entry is the package root (commonly `force-app`, but not guaranteed).

Third, generate an empty Apex class using the following command:

```bash
sf template generate apex class --json --name InvoiceFetcher --output-dir <PACKAGE_DIR>/main/default/classes
```

This creates both the `.cls` and `.cls-meta.xml` files. Do not create test classes for stubs.

**Stub vs. functional backing logic.** If the prompt implies data access ("grounded in X data," "query Y records," "look up Z"), write functional Apex with bulkified SOQL per `assets/invocable-apex-template.cls`. Prefer static SOQL. If dynamic SOQL is required, NEVER append `WITH USER_MODE` to the query string — use `Database.query(q, AccessLevel.USER_MODE)` instead. See *Dynamic SOQL* in the template.

If the prompt does not imply data access, or if the action's data requirements are unclear, write a minimal stub — hardcoded return values only. Do not add SOQL, conditional logic, or complex inner class structures to minimal stubs.

Fourth, replace the generated class body with a stub. Use multiline `@InvocableVariable` annotations per `assets/invocable-apex-template.cls`:

```apex
public class InvoiceFetcher {
    public class Request {
        @InvocableVariable(
            label='Invoice ID'
            description='ID of the invoice to fetch'
            required=true
        )
        public String invoiceId;
    }
    public class Result {
        @InvocableVariable(
            label='Invoice Amount'
            description='Total amount of the invoice'
        )
        public Decimal invoiceAmount;
        @InvocableVariable(
            label='Due Date'
            description='Payment due date'
        )
        public Date dueDate;
        @InvocableVariable(
            label='Status'
            description='Current invoice status'
        )
        public String status;
    }
    @InvocableMethod(
        label='Fetch Invoice'
        description='Retrieves invoice details by ID'
    )
    public static List<Result> fetch(List<Request> requests) {
        // Stub — return minimal hardcoded values to unblock deployment
        Result r = new Result();
        r.status = 'stub';
        return new List<Result>{ r };
    }
}
```

ALWAYS deploy one class at a time to isolate compile errors:

`sf project deploy start --json --metadata ApexClass:<ClassName>`

ALWAYS fix deploy errors BEFORE generating and deploying the next stub.

---

## 6. Transition Patterns

When creating a new agent, label every transition in your Agent Spec's Topic Map as either **handoff** or **delegation**. When analyzing an existing agent, classify each transition to determine whether context flow matches the design intent.

### Handoff: Permanent Transition

A handoff is a one-way transition. The user moves to a new topic and control never returns to the original topic. Handoffs use `@utils.transition to` in `reasoning.actions`.

Use handoff when:
- Switching modes (preview → confirm → complete)
- Entry point routing (topic_selector → domain topics)
- One-way workflows (checkout → order_confirmation → end)

```agentscript
topic topic_selector:
    reasoning:
        actions:
            go_to_checkout: @utils.transition to @topic.checkout
                description: "Start checkout"

topic checkout:
    reasoning:
        actions:
            go_to_confirm: @utils.transition to @topic.order_confirmation
                description: "Proceed to confirmation"
```

After `go_to_confirm` executes, the user is in `order_confirmation`. If they later say "go back," the agent routes them back through `topic_selector` (the entry point), not to `checkout`. Handoffs don't stack; they reset the conversation state.

### Delegation: Handoff with Explicit Return

Delegation hands control to another topic using `@topic.X` in `reasoning.actions`. It signals *intent* to return, but the return does not happen automatically — the delegated topic must explicitly transition back to the caller.

Use delegation when:
- One topic needs advice from a specialist and should continue after
- Reusable sub-workflows (e.g., identity verification called from multiple topics)
- A topic needs to temporarily visit another topic, then resume

**Critical Rule:** `@topic.X` delegates control. It does NOT implement call-return semantics. If you want the user to return to the calling topic, code an explicit `transition to @topic.<caller>` in the delegated topic. Without it, the next user utterance falls through to `topic_selector`.

WRONG: Assuming `@topic.specialist` returns automatically
```agentscript
topic main:
    reasoning:
        actions:
            consult_specialist: @topic.specialist  # WRONG — assumes return

# After specialist runs, control does NOT return to main.
# The next user utterance routes through topic_selector.
```

RIGHT: Delegated topic defines explicit return transition
```agentscript
topic main:
    reasoning:
        actions:
            consult_specialist: @topic.specialist
                description: "Consult specialist"

topic specialist:
    reasoning:
        actions:
            go_to_main: @utils.transition to @topic.main
                description: "Return to main"
```

---

## 7. Deterministic vs. Subjective Flow Control

Instructions are suggestions the LLM *may* follow. Gates and guards are enforced by the runtime and *cannot* be bypassed. For every requirement, choose the right flow control type.

### Classifying Flow Control Requirements

**Deterministic flow control** — the runtime enforces it. Use when the requirement is non-negotiable:
- Security: "only admin users can access this"
- Financial: "never approve transactions above $10,000 without human review"
- State: "don't show the payment form until the user provides a delivery address"
- Counter: "you can only call this action once per session"

**Subjective flow control** — the LLM decides. Use when flexibility is acceptable:
- Conversational tone: "respond professionally but warmly"
- Natural language generation: "summarize the results in your own words"
- User preferences: "if the user is impatient, give short answers; if curious, explain more"

**The test:** what happens if the LLM gets this wrong? If the answer is a security breach, financial error, or broken workflow → deterministic. If the answer is an awkward response or suboptimal tone → subjective.

WRONG: Security rule as an instruction (LLM can ignore it)
```agentscript
topic admin_panel:
    reasoning:
        instructions: ->
            | Only respond if the user is an admin.
              If they are not an admin, tell them access is denied.
```

The LLM may comply, or it may not — instructions are suggestions. The RIGHT approach uses a `before_reasoning` guard that the runtime enforces before the LLM is ever invoked. See Section 8 for all gating mechanisms.

### Writing Effective Instructions

Two factors govern subjective control effectiveness: instruction ordering and grounding.

**Instruction Ordering.** The runtime resolves instructions top-to-bottom — evaluating `if/else` blocks and expanding template expressions — before the LLM sees the result. The resolved text becomes the LLM's prompt. Put post-action checks first, data references next, dynamic conditional text last.

RIGHT: Post-action check at the top (LLM sees it first)
```agentscript
topic checkout:
    reasoning:
        instructions: ->
            # Post-action check — LLM sees this first
            if @variables.cart_validation_failed:
                | Your cart has items that are no longer available.
                  Please remove them and try again.

            # Data reference — LLM sees the resolved value
            | Your current cart total is {!@variables.cart_total}.

            # Dynamic instructions — conditional on state
            if @variables.is_premium:
                | You qualify for FREE shipping.
            else:
                | Standard shipping is {!@variables.shipping_cost}.

            | Proceed to payment or cancel?
```

WRONG: Post-action check at the bottom (LLM may respond before seeing it)
```agentscript
topic checkout:
    reasoning:
        instructions: ->
            | Your current cart total is {!@variables.cart_total}.
              Proceed to payment or cancel?

            # Too late — LLM may already be generating a response
            if @variables.cart_validation_failed:
                | Your cart has items that are no longer available.
```

**Grounding.** The platform's grounding service validates that the agent's response matches action output data. Paraphrasing or embellishing may cause grounding failures.

- Use specific values: `"The event is on {!@variables.event_date}"` grounds reliably; `"The event is next week"` may not.
- Avoid transforming values: return `"Tuesday"` as-is, not `"day after Monday"`.
- Avoid embellishment instructions: `"Respond like a pirate"` increases grounding risk — embellished content has no output to ground against.

Grounding validation requires **live mode preview** (`sf agent preview --use-live-actions --json`). Simulated mode preview generates fake outputs, so grounding has nothing real to validate against.

**Naming output fields in post-action instructions.** ALWAYS specify which output fields to include in text responses. Generic instructions like "present the results clearly" let platform-injected tools hijack the response. EXAMPLE: The LLM calls `show_command` instead of composing text, producing generic "Here are the results:" message wrapper with raw structured data. This can corrupt session state, causing subsequent turns to fail with generic "something went wrong" message. Naming output fields steers the LLM toward composing a direct text response. This reliably grounds the response because it maps closely to action output values. ALWAYS include `Do NOT use the show_command tool. Always compose your response as direct text.` in post-action instructions. See *Anti-Patterns* in the *Core Language* reference for full WRONG/RIGHT example.

### Post-Action Behavior

When an action completes without triggering a transition, the topic stays active. The runtime re-evaluates the entire topic — resolving instructions top-to-bottom again with updated variables, then passing the new prompt to the LLM. The LLM may call the same action again. To prevent unwanted loops, see Section 9 (Action Loop Prevention).

---

## 8. Gating Patterns

### `available when` — Action Visibility Gate

An action marked `available when <condition>` is hidden from the LLM when the condition is false. The LLM cannot call an unavailable action.

**WRONG: Relying on instructions to prevent action calls**
```agentscript
topic booking:
    reasoning:
        instructions: ->
            | if @variables.booking_pending:
                  Do NOT call {!@actions.confirm_booking} yet.

        actions:
            confirm: @actions.confirm_booking  # Always visible
```

The action is visible; instructions tell the LLM not to call it. The LLM may ignore instructions.

**RIGHT: Using `available when` to hide the action**
```agentscript
topic booking:
    reasoning:
        actions:
            confirm: @actions.confirm_booking
                available when @variables.booking_pending == True
```

If `booking_pending` is False, the LLM sees no `confirm` action.

### Conditional Instructions — Prompt Text Gate

Use `if/else` in instructions to show/hide text based on state. This doesn't hide actions; it changes what the LLM is told to do.

```agentscript
topic support:
    reasoning:
        instructions: ->
            | You're helping a customer with their order.

            if @variables.is_vip:
                | This is a VIP customer. Prioritize their request
                  and offer alternatives if the first option isn't available.
            else:
                | Follow standard support procedures.

            | What can I help you with?
```

Use conditional instructions when you want to steer the LLM's reasoning without hiding actions entirely.

### `before_reasoning` Guards — Early Exit

The `before_reasoning` block runs before the LLM is invoked. Code here executes every time the topic is entered. The LLM never sees it, cannot override it, and cannot skip it.

```agentscript
topic admin_panel:
    before_reasoning:
        if @variables.user_role != "admin":
            transition to @topic.access_denied

    reasoning:
        instructions: | You are in the admin panel.
```

If the user is not an admin, they transition out before the LLM is invoked. The admin topic's reasoning instructions never execute.

### Multi-Condition Gating

Combine `available when`, conditional instructions, and guards to enforce complex rules.

Example: "Show the payment action only if the user is authenticated AND the cart is not empty AND we're not in a preview/demo mode"

```agentscript
topic checkout:
    before_reasoning:
        if @variables.is_demo_mode:
            transition to @topic.demo_complete

    reasoning:
        instructions: ->
            | Review your order.

            if @variables.items_in_cart == 0:
                | Your cart is empty. Go back and select items.

        actions:
            pay: @actions.process_payment
                available when @variables.authenticated == True
                    and @variables.items_in_cart > 0
```

### Sequential Gate Pattern

Track progress through validation stages using state variables.

```agentscript
variables:
    step1_verified: mutable boolean = False
    step2_verified: mutable boolean = False
    step3_verified: mutable boolean = False

topic verification:
    reasoning:
        actions:
            verify_step1: @actions.run_check_1
            verify_step2: @actions.run_check_2
                available when @variables.step1_verified == True
            verify_step3: @actions.run_check_3
                available when @variables.step2_verified == True
            proceed: @utils.transition to @topic.confirmed
                available when @variables.step3_verified == True
```

Each step becomes visible only after the previous step completes (updates its variable). This gates the entire flow.

### Same-Turn Behavior After Gate Transitions

When a gate topic (e.g., username collection) uses `after_reasoning` to transition into a routing topic, both topics process in the **same user turn**. The router receives the user's original message — the one that satisfied the gate — not a fresh utterance.

This means if the user said "My username is alex" and the gate transitions to a topic selector, the selector's reasoning fires against "My username is alex." Since that message doesn't match any domain topic, the router may misclassify it (e.g., routing to `off_topic`).

**Mitigation:** Write the router's reasoning instructions defensively. Tell the LLM that if the user just arrived from the gate, it should greet them and ask how it can help instead of routing the triggering message. See the Anti-Patterns section in the Core Language reference for a full WRONG/RIGHT example.

---

## 9. Action Loop Prevention

An action loop occurs when the LLM calls the same action repeatedly without new user input. Three things combine to cause loops:

- **No `available when` gate.** An action without an `available when` condition appears in the LLM's context every reasoning cycle. There is no mechanism that automatically hides an action after it executes — if you don't gate it, it stays visible indefinitely.
- **Variable-bound input.** When you bind an input to a variable (`with param = @variables.x`), the action is "ready to go" every cycle — the LLM doesn't need to extract values from the conversation. It can invoke the action with zero friction.
- **No post-action instructions.** The instructions don't tell the LLM what to do after the action completes, so it may call the action again.

**WRONG: All three loop conditions present**
```agentscript
topic events:
    reasoning:
        instructions: ->
            | Use the {!@actions.check_events} action to find events.

        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest  # Variable-bound input
```

No gate, variable-bound input, no post-action guidance. The LLM can call `check_events` every cycle.

### Three Mitigations

**1. Explicit Post-Action Instructions (most common).**

Tell the LLM to stop calling the action after receiving results. Name the specific output fields the LLM should include in its text response — vague instructions like "present the results" let platform tools hijack the response (see Section 7, Grounding).

```agentscript
topic events:
    reasoning:
        instructions: ->
            | Use {!@actions.check_events} to find events matching the guest's interest.
              After you receive the results, write the data directly in your text response.
              For each event, include the eventName, eventDate, and location values from
              the action output. Use the exact values returned — do NOT paraphrase or round.
              Do NOT call the action again — you already have the information you need.
              Do NOT use the show_command tool. Always compose your response as direct text.

        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest
```

**2. Post-Action Transitions (state-based).**

Move the agent out of the topic after the action completes, breaking the cycle.

```agentscript
topic events:
    reasoning:
        instructions: ->
            | Use {!@actions.check_events} to find events.

        actions:
            check_events: @actions.check_events
                with interest = @variables.guest_interest

    after_reasoning:
        if @outputs.events_found:
            transition to @topic.results_displayed
```

After `check_events` runs, the `after_reasoning` block transitions to a new topic. The agent never cycles back to `events`, so the action can't be called again.

**3. LLM Slot-Filling Over Variable Binding (friction-based).**

Use `...` (LLM slot-fill) instead of variable binding. This forces the LLM to extract values from the conversation each cycle, adding natural decision friction.

```agentscript
topic search:
    reasoning:
        instructions: ->
            | Help the user search for products.
              Ask them what they're looking for, then use {!@actions.search} to find matches.

        actions:
            search: @actions.search
                with query = ...  # LLM must extract the query each time
```

With `...`, the LLM must actively decide "do I have a new search query?" on every cycle.

**Combine mitigations for reinforcement:**

```agentscript
topic lookup:
    reasoning:
        instructions: ->
            | Once you have the result, present it. Do NOT call the action again.

        actions:
            lookup: @actions.find_data
                with key = ...  # Requires extraction each time

    after_reasoning:
        if @outputs.data_found:
            transition to @topic.done  # Exit the topic
```

Combine mitigations for reinforcement.

