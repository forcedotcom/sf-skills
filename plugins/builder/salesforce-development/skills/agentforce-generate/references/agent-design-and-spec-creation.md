# Agent Design and Spec Creation

## Table of Contents

1. Agent Spec: Purpose and Lifecycle
2. Discovery Questions (Outcome First)
3. Environment Prerequisites
4. Subagent Architecture
5. Mapping Action Implementations
6. Transition Patterns
7. Deterministic vs. Subjective Flow Control
8. Gating Patterns
9. Action Loop Prevention

---

## 1. Agent Spec: Purpose and Lifecycle

An **Agent Spec** is a structured design document describing business outcomes,
use cases, actions, subagents, and control flow. It documents mutable state only
when the runtime needs it. Build the spec before writing Agent Script. For
existing agents, reverse-engineer the spec from the `.agent` file so intent is
explicit before changes.

If the user supplies a sufficiently detailed design or Agent Spec and explicitly
says it is already approved, use it as the current build contract. Do not
recreate or reapprove it unless requirements are missing or materially change.

### What an Agent Spec Contains

- **Purpose & Scope** — what business outcome the agent should drive
- **Behavioral Intent** — what the agent is supposed to achieve (requirements and constraints), not just what code exists
- **Subagent Map** — a Mermaid flowchart showing all subagents, transitions (with type labels: handoff or delegation), and when transitions occur
- **Actions & Implementations** — each action's name, implementation type (Apex class, Flow, Prompt Template), inputs/outputs, and whether implementation exists or needs creation
- **Variables (when needed)** — declarations, trusted writers, named
  deterministic consumers, causes, and lifecycle behavior
- **Deterministic Controls (when needed)** — only include gating/invariants that are required by trust, policy, regulation, or observed failures
- **Interaction Style** — brand voice, personality, escalation tone, and response style constraints
- **Subagent Posture** — scripted, mixed, or agentic posture per subagent with a short justification

### Planned vs. Existing Entries

Agent Spec entries can be planned or existing — both are valid:

- **Planned (placeholder):** "The `confirm_booking` action needs an Apex class `BookingConfirmer` that accepts reservation_id (string), guest_name (string), and returns confirmation_number (string), booking_date (date)." This is a not-yet-implemented requirement.

- **Existing (implemented):** "The `fetch_weather` action uses Apex class `WeatherService`, invoked via `apex://WeatherService`. Accepts dateToCheck (date), returns maxTemp/minTemp (number)." This documents current implementation.

Both go in the same Agent Spec section.

### Lifecycle Stages

The Agent Spec evolves across the agent's lifecycle:

**Creation (sparse).** Purpose, outcomes, use cases, and planned notes about action implementations ("this action needs an Apex class that accepts X, returns Y"). No full flowchart yet.

**Build (filled).** Flowchart added with transition types labeled. Action implementations mapped (existing implementations identified with filenames, missing implementations stubbed with protocols and I/O specs). Add variables and deterministic controls only where required and justified.

**Comprehension (reverse-engineered).** Starting from an existing `.agent` file, produce a complete Agent Spec by parsing subagents, tracing transitions, analyzing actions, and documenting state. This is the "what does this agent do?" output.

**Diagnosis (reference).** Compare actual runtime behavior against the Agent Spec to find where intent and implementation diverge.

### Agent Spec Template

Use the starter spec template at `assets/agent-spec-template.md` for new agents.

---

## 2. Discovery Questions (Outcome First)

These discovery categories drive the Agent Spec. Start from outcomes and business
process first, then map to actions/subagents. When comprehending an existing
agent, extract the same answers from `.agent` and project files.

**Resolve as many questions as possible from available context before asking the human.** Scan existing code, project metadata, prior conversation, and any provided requirements. Only surface questions the human must answer — never forward this list verbatim.

Default new actions to placeholders (`NEEDS STUB`) during planning. Reuse/generate
implementation work is an explicit user choice. Follow the execution policy in
`SKILL.md` for when to scan existing implementations or generate new ones.

### Agent Identity & Purpose *(feeds Purpose & Scope)*

- What is the agent's name? (no spaces, letters/numbers/underscores only)
- What is the agent's primary purpose in one sentence?
- What should the welcome message say?
- What personality should the agent have? (professional, friendly, formal, casual)
- What error message should the agent show if something breaks?

### Outcomes, Process, and Requirements *(feeds Behavioral Intent and Deterministic Controls)*

- What outcome should the agent produce for the business and user?
- What process or policy should the agent follow (for example, verification, time-window checks, escalation rules)?
- Which steps are strict invariants versus flexible conversational guidance?
- Which requirements are regulated, audited, trust-sensitive, or otherwise must be deterministic?

### Subagents & Conversation Flow *(feeds Subagent Map)*

- What distinct conversation areas (subagents) does the agent need?
- Default to one execution block: put the focused domain directly in
  `start_agent <domain>:` and create zero `subagent` blocks. Add another block
  only when objective, instructions, actions, authority, or escalation
  behavior changes and cannot remain coherent in the current scope.
- Treat greetings, cancellation acknowledgments, completion messages,
  ambiguity questions, and ordinary dialogue steps as branches unless they
  genuinely require a separate scope.
- If multiple genuine domains need current-intent classification, use
  `start_agent agent_router`.
- What are the possible transitions between subagents?
- Are there subagents that delegate to others and need to return?
- Are there guardrail subagents (off-topic redirection, ambiguity handling, security gates)?
- Are there any workflow-local linear steps within a subagent (instead of treating the whole agent as linear)?

### Reasoning & Instructions *(feeds Behavioral Intent)*

- What should the agent do in each subagent?
- What trusted output or invariant changes the instructions, if any?
- Should the agent do anything before or after reasoning in a given subagent? (e.g., security checks, data fetches, automatic transitions)
- What data transformations (if any) does the LLM need to do?

### Subagent Posture *(feeds posture-and-determinism.md)*

- For each subagent, should posture be scripted, mixed, or agentic?
- If deterministic controls are added, what is the explicit cause (regulation/trust/observed failure)?
- Which controls are true invariants (`available when`) vs guidance?

### Actions & External Systems *(feeds Actions & Implementations)*

- What external systems does the agent call?
  - Salesforce Flows (autolaunched only)
  - Apex classes (invocable only)
  - Prompt Templates
  - External APIs (not directly; must be wrapped in Apex or Flow)
- For each action: what inputs, outputs, and availability conditions are required?
- Should any action be a placeholder stub first so the team can iterate on behavior before full implementation?
- What custom objects exist in the project? Scan `objects/` for `.object-meta.xml` files. Check relationships (lookup, master-detail) between objects — related objects often contain data the agent should expose even when not explicitly mentioned in the prompt.

### Runtime State *(optional; feeds Variables and Deterministic Controls)*

Surviving conversation history already carries ordinary conversational facts.
Do not mirror names, preferences, questions asked, or dialogue stages into
variables.

For each proposed variable:

- Which named `if`, `available when`, transition, action input, or later-turn
  exact output consumes it?
- Does that consumer need the exact external identifier, or only a trusted
  complete/incomplete outcome? Keep a display-only final identifier in the
  action result and surviving history when a boolean is sufficient for control.
- Does it record trusted action output, prove authorization/eligibility/
  confirmation, preserve exact action data flow, enforce external ordering, or
  outlive the configured history window?
- Who writes it, and what are its reset, expiry, correction, and cancellation
  semantics?

If these questions have no concrete answer, omit the variable.

---

## 3. Environment Prerequisites

**⚠️ MANDATORY: Run these checks immediately after determining the agent type during discovery.** Do not proceed to subagent architecture or code generation until the environment is validated.

Posture guidance is separate from architecture. Read [Posture and Determinism](posture-and-determinism.md) to choose subagent posture (scripted, mixed, agentic) based on requirements and observed failures.

### `AgentforceEmployeeAgent`

1. Confirm the file normally omits `access.default_agent_user`. If the generated boilerplate includes an `access` block, remove it along with any MessagingSession linked variables and escalation subagent.

**⚠️ Setting `default_agent_user` on an employee agent causes publish and preview to fail with an unhelpful "unknown error."**

### `AgentforceServiceAgent`

REQUIRES `access.default_agent_user`. Query the org to find an active Einstein Agent User:

```bash
sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
```

**If results are returned:** Ask which username to use. Record choice in the Agent Spec Configuration section. Verify permissions per [Agent User Setup & Permissions](agent-user-setup.md).

**If no results are returned:** STOP. Do NOT invent a username. Ask if you should create a new user, then read [Agent User Setup & Permissions](agent-user-setup.md) for user creation instructions.

**WRONG:** Fabricating a username when query returns nothing
```text
default_agent_user: "myagent@example.com"   # made up, will fail at publish
```

**RIGHT:** Stopping and asking to create a new user
```text
"No Einstein Agent User found in this org. Would you like me to create one for you?"
```

### Recording Prerequisites in the Agent Spec

Add a "Configuration" section to the Agent Spec:

- **Agent type**: `AgentforceServiceAgent` or `AgentforceEmployeeAgent`
- **Default agent user**: confirmed username (service agents), or "N/A — employee agent"
- **Permissions verified**: yes/no — see [Agent User Setup & Permissions](agent-user-setup.md)

---

## 4. Subagent Architecture

Subagents are responsibility and capability scopes, not conversation-state
markers. Create a subagent only when the boundary changes its objective,
instructions, available actions, authority, or escalation behavior and the
result cannot remain coherent in one scope. When designing a new agent, plan
those boundaries before writing code. When comprehending an existing agent,
identify what behavior each boundary changes.

### Subagent Strategies

Every subagent in an agent serves one of three roles: domain, guardrail, or escalation.

**Domain Subagents.** The core conversation areas where the agent does its work.
Each domain subagent handles a specific area (orders, billing, weather, events)
with distinct instructions, actions, authority, or escalation behavior. Most
focused agents need only the `start_agent`; add domain subagents only for
genuine additional domains.

**Guardrail Subagents.** Specialized scopes for boundaries that need their own
instructions, actions, authority, or escalation behavior. Off-topic redirection
and ambiguity clarification are ordinary branches by default. Create
`off_topic` or `ambiguous_question` subagents only when their distinct policy
cannot remain coherent in the current scope. When modifying an existing agent,
do not delete such scopes without testing their behavior, but do not copy them
into every new design.

```agentscript
subagent off_topic:
    description: "Handle off-topic requests"
    reasoning:
        instructions: ->
            | Explain that the request is outside scope, state the supported
              capabilities, and ask which supported task the user wants help
              with.

subagent ambiguous_question:
    description: "Ask for clarification"
    reasoning:
        instructions: ->
            | Explain briefly that the request is unclear and ask one focused
              question for the missing detail needed to proceed.
```

**Escalation Subagents.** Hand off via `@utils.escalate`. It ends the current
agent turn and transfers control to the configured escalation path; the source
subagent does not resume automatically. Do not assume the broader messaging
session ends unless that channel's escalation contract says so.

```agentscript
subagent escalation:
    reasoning:
        actions:
            escalate: @utils.escalate
                description: "Connect with a human agent"
```

### Single-Subagent vs. Multi-Subagent

Decide this before choosing an architecture pattern.

Use **single-subagent** if:
- The agent handles one domain only (FAQ, weather checker, status lookup)
- All interactions naturally stay in the same context
- No boundary needs a different action set, authority, or escalation behavior

Use **multi-subagent** if:
- The agent handles multiple distinct domains (customer service: orders + billing + account)
- Different subagents have different instructions or action sets
- Users may need to switch contexts mid-conversation
- You need security gates or clearly distinct action sets

### Architecture Patterns

Default to the smallest architecture: one `start_agent <domain>:` execution
block and zero `subagent` blocks. Do not create an `agent_router` that merely
transitions to one domain. Add a boundary only when objective, instructions,
actions, authority, or escalation behavior changes and cannot remain coherent
in the current scope. Use
router-first (`start_agent agent_router`) when multiple genuine domains require
current-intent classification. Treat linear flow as workflow-local external
ordering, not as the default shape for a conversation.

Use [Patterns by Requirement](patterns-by-requirement.md) to choose the right
pattern for the scenario. Use [Architecture Patterns](architecture-patterns.md)
for detailed mechanics and migration guidance.

**Router-First Architecture.** One central router (`start_agent agent_router`) transitions to specialized domain subagents. Subagents may transition directly to other subagents when the workflow calls for it, or return to router when reclassification is needed. Use when the agent handles multiple distinct domains that don't naturally flow together.

Example: The Local Info Agent. The `agent_router` router transitions to domain and guardrail subagents.

```agentscript
start_agent agent_router:
    reasoning:
        actions:
            go_to_weather: @utils.transition to @subagent.local_weather
            go_to_events: @utils.transition to @subagent.local_events
            go_to_hours: @utils.transition to @subagent.resort_hours
            go_to_off_topic: @utils.transition to @subagent.off_topic
            go_to_ambiguous_question: @utils.transition to @subagent.ambiguous_question

# Domain subagents — each has its own instructions and actions
subagent local_weather:
    reasoning:
        instructions: | Handle weather questions.

subagent local_events:
    reasoning:
        instructions: | Handle event questions.

# resort_hours, off_topic, ambiguous_question defined further down the file
```

**Staged Flow.** Subagents may form a pipeline when the benefit of strict
ordering outweighs the loss of conversational flexibility—for example, when
an external protocol requires successful verification before a protected
commit. A staged flow improves repeatability and auditability, but adds state,
maintenance, and friction around corrections or changed intent. A prompt-led
multi-question conversation is usually more flexible but cannot guarantee the
same order.

Choose deliberately. For stages that persist across turns, define the
correction, cancellation, retry, or intent-change behavior that the actual use
cases need. A short-lived deterministic guard does not need ceremonial state
or every possible exit path.

```agentscript
start_agent intake:
    reasoning:
        actions:
            go_next: @utils.transition to @subagent.verification

subagent verification:
    reasoning:
        actions:
            go_next: @utils.transition to @subagent.details_gathering

subagent details_gathering:
    reasoning:
        actions:
            go_next: @utils.transition to @subagent.confirmation
```

**Escalation Chain.** Tiered support where each level has increasing capabilities. First-level resolves common issues with basic actions; second-level has access to more powerful actions or broader authority; final level escalates to a human. Use when support difficulty varies and you want to resolve simple issues quickly without involving higher tiers.

```agentscript
subagent level_1_support:
    reasoning:
        instructions: | Try to resolve the issue using the FAQ and basic troubleshooting.
        actions:
            check_faq: @actions.search_faq
            escalate: @utils.transition to @subagent.level_2_support

subagent level_2_support:
    reasoning:
        instructions: | You have access to account tools. Try to resolve before escalating.
        actions:
            lookup_account: @actions.get_account_details
            modify_account: @actions.update_account
            escalate_to_human: @utils.escalate
```

**Verification Gate.** A security or permission check before allowing access to protected subagents. The gate validates the user, then transitions to the protected subagent or denies access.

In this example, `user_role` must be trusted output from an authorization
action. The two transitions are its named consumers; the cause is authorization.

```agentscript
start_agent security_gate:
    reasoning:
        actions:
            go_admin: @utils.transition to @subagent.admin_panel
                available when @variables.user_role == "admin"
            go_denied: @utils.transition to @subagent.access_denied
                available when @variables.user_role != "admin"

subagent access_denied:
    reasoning:
        instructions: | You don't have permission to access this.
```

**Single-Subagent.** The entire agent is one subagent — no transitions. Use for focused QA agents where all interactions stay in the same domain.

```agentscript
start_agent faq:
    description: "Answer questions about pricing"
    reasoning:
        instructions: | Answer questions about our pricing plans.
        actions:
            lookup_plan: @actions.get_plan_details
```

### Composing Patterns

Real agents often combine patterns. A router-first agent may use a verification gate before protected subagents. A linear flow may include escalation exits at each stage. When composing, each subagent still serves exactly one role (domain, guardrail, or escalation) — the architecture pattern determines how they connect.

---

## 5. Mapping Action Implementations

Every action in Agent Script needs an implementation in Salesforce. When creating
an agent, identify existing implementations and stub what's missing. When
comprehending an existing agent, trace each action to its implementation.

### Valid Action Implementation Types

The most common implementation types are Apex, Flows, and Prompt Templates.

**Apex**: Only **invocable Apex classes** work. A regular Apex class, even if it has public methods, will not work. Invocable classes use two key annotations:

`@InvocableMethod` marks the entry point. Its attributes: `label` (human-readable name), `description` (what the method does). Read these when comprehending existing action implementations.

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

Wire with the exact registered target identifier, commonly
`target: "apex://ClassName"`.

> **One `@InvocableMethod` per Apex class.** This verified Apex constraint
> governs implementation structure; it does not justify rewriting an action
> target supplied by the user, project, org metadata, or an approved contract.
> Preserve the exact target. If its implementation mapping is uncertain, flag
> that uncertainty and verify it from the implementation or target org before
> proposing a contract change. Do not infer from a dotted target that several
> `@InvocableMethod`s share one class.

**Flows**: Only **autolaunched Flows** work. Screen Flows, record-triggered Flows, and schedule-triggered Flows will not work. The Flow must start only when explicitly invoked.

Wire with: `target: "flow://FlowApiName"`

**Prompt Templates**: Salesforce Prompt Templates (custom or industry-specific).

Wire with: `target: "prompt://TemplateName"` (short form). The long form `generatePromptResponse://TemplateName` also works but prefer the short form.

### How to Identify Existing Actions

Read `sfdx-project.json` and look at the `packageDirectories` array — each entry's `path` field tells you where source files live (typically `force-app/main/default/`).

Then scan for each type within those directories:

**Finding invocable Apex:** Search `classes/` for files containing `@InvocableMethod`. For each match, read the class to extract the `@InvocableVariable` annotations on its inner `Request` and `Result` classes — these define the action's input and output contract. Pay attention to the `@InvocableVariable` types: they map to Agent Script types (`String` → `string`, `Boolean` → `boolean`, `Decimal` → `number`, `Integer` → `integer`, `Date` → `date`, `Datetime` → `datetime`). See the full type mapping table in "Connecting Existing Actions to Action Definitions" below.

**Finding autolaunched Flows:** Search `flows/` for `.flow-meta.xml` files. Read each file and check the `<processType>` element. Only `AutoLaunchedFlow` is valid for actions. Examine the `<variables>` elements to identify inputs (`isInput=true`) and outputs (`isOutput=true`) with their data types.

**Finding Prompt Templates:** Search `promptTemplates/` for template metadata files. Review the template's input variables and output format.

**Finding External Services:** Search `externalServiceRegistrations/` for `.externalServiceRegistration-meta.xml` files. These represent registered external APIs (REST endpoints). Check the schema for available operations, inputs, and outputs. Wire with `target: "externalService://ServiceName"`.

**Finding Standard Invocable Actions:** These are platform-provided actions (e.g., `sendEmail`, `chatterPost`). Query the org: `sf api request rest --json "/services/data/v63.0/actions/standard" -o <org-alias>` to list all available standard actions. Wire with `target: "standardInvocableAction://actionName"`.

### How to Map Existing Actions

For each candidate action, verify it matches what the agent needs:

- **Input contract** — does the action accept the parameters the agent will send?
- **Output contract** — does the action return data the agent needs?
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
```text
check_order action:
  Existing Action: Apex class OrderLookup (invocable)
  Target: apex://OrderLookup
  Inputs: orderId (string, required)
  Outputs: status (string), amount (number), orderDate (date)
  Status: IMPLEMENTED
```

### Connecting Existing Actions to Action Definitions

Each `@InvocableVariable` on the request class becomes an action input; each on the result class becomes an output. The `target` field points to the existing action.

**Critical: Input and output names must exactly match the Apex `@InvocableVariable` field names, character-for-character.** If the Apex field is `dateToCheck`, the Agent Script input must be `dateToCheck` — not `date_to_check`, not `DateToCheck`. The platform validates these names at publish time; mismatches cause publish failures.

```agentscript
# WRONG — snake_case doesn't match the Apex field names
subagent orders:
    actions:
        check_order: @actions.check_order
            target: "apex://OrderLookup"
            inputs:
                order_id: string     # Apex field is orderId, NOT order_id
            outputs:
                order_date: date     # Apex field is orderDate, NOT order_date

# RIGHT — names match Apex @InvocableVariable field names exactly
subagent orders:
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

| Target | Action Type | Agent Script Type | `complex_data_type_name` Format | Example |
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

**⚠️ Invalid action implementations (non-autolaunched Flow, non-invocable Apex) may pass validation and simulation-mode preview. The failure surfaces at deploy or as cryptic runtime errors in live mode.** Always verify implementation type before wiring.

### How to Stub Missing Logic

When no implementation exists for an action, stub it as an invocable Apex class. Always use Apex for stubs — do not attempt to hand-craft Flow XML or Prompt Template metadata.

First, record the stub in the Agent Spec:
```text
fetch_invoice action:
  Existing Action: (none — needs creation)
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

**Stub vs. functional implementation.** If the prompt implies data access ("grounded in X data," "query Y records," "look up Z"), write functional Apex with bulkified SOQL per `assets/invocable-apex-template.cls`. Prefer static SOQL. If dynamic SOQL is required, NEVER append `WITH USER_MODE` to the query string — use `Database.query(q, AccessLevel.USER_MODE)` instead. See *Dynamic SOQL* in the template.

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

When creating a new agent, label every transition in your Agent Spec's Subagent Map as either **handoff** or **delegation**. When analyzing an existing agent, classify each transition to determine whether context flow matches the design intent.

### Handoff: Non-Returning Transition

A handoff is a one-way transition. The user moves to a new subagent and control never returns to the original subagent. Handoffs use `@utils.transition to` in `reasoning.actions`.

Use handoff when:
- Switching modes (preview → confirm → complete)
- Entry point routing (agent_router → domain subagents)
- One-way workflows (checkout → order_confirmation → end)

```agentscript
subagent agent_router:
    reasoning:
        actions:
            go_to_checkout: @utils.transition to @subagent.checkout
                description: "Start checkout"

subagent checkout:
    reasoning:
        actions:
            go_to_confirm: @utils.transition to @subagent.order_confirmation
                description: "Proceed to confirmation"
```

After `go_to_confirm` executes, the active execution target is
`order_confirmation`. If the user later says "go back," the agent routes them
through `agent_router` (the entry point), not automatically to `checkout`.
Handoffs do not maintain a return stack. This does not mean surviving user and
assistant messages disappear from model-visible conversation history.

### Delegation: Handoff with Explicit Return

Delegation hands control to another subagent using `@subagent.X` in `reasoning.actions`. It signals *intent* to return, but the return does not happen automatically — the delegated subagent must explicitly transition back to the caller.

Use delegation when:
- One subagent needs advice from a specialist and should continue after
- Reusable sub-workflows (e.g., identity verification called from multiple subagents)
- A subagent needs to temporarily visit another subagent, then resume

**Critical Rule:** `@subagent.X` delegates control. It does NOT implement call-return semantics. If you want the user to return to the calling subagent, code an explicit `transition to @subagent.<caller>` in the delegated subagent. Without it, the next user utterance falls through to `agent_router`.

WRONG: Assuming `@subagent.specialist` returns automatically
```agentscript
subagent main:
    reasoning:
        actions:
            consult_specialist: @subagent.specialist  # WRONG — assumes return

# After specialist runs, control does NOT return to main.
# The next user utterance routes through agent_router.
```

RIGHT: Delegated subagent defines explicit return transition
```agentscript
subagent main:
    reasoning:
        actions:
            consult_specialist: @subagent.specialist
                description: "Consult specialist"

subagent specialist:
    reasoning:
        actions:
            go_to_main: @utils.transition to @subagent.main
                description: "Return to main"
```

---

## 7. Deterministic vs. Subjective Flow Control

Instructions are suggestions the LLM *may* follow. Gates and guards are enforced by the runtime and *cannot* be bypassed. For every requirement, choose the right flow control type.

### Classifying Flow Control Requirements

**Deterministic flow control** — the runtime enforces it. Use when the requirement is non-negotiable:
- Security: "only admin users can access this"
- Financial: "never approve transactions above $10,000 without human review"
- Confirmed consequence: "do not submit until the exact target and explicit confirmation are recorded"
- External ordering: "step 2 is unavailable until step 1 returns success"
- Observed failure: a reproduced trace proves model reasoning cannot reliably enforce the requirement

**Subjective flow control** — the LLM decides. Use when flexibility is acceptable:
- Conversational tone: "respond professionally but warmly"
- Natural language generation: "summarize the results in your own words"
- User preferences: "if the user is impatient, give short answers; if curious, explain more"

**The test:** name the regulation, authorization boundary, irreversible
consequence, external ordering constraint, or reproduced trace failure. If none
exists, leave the decision to model reasoning. Awkward phrasing or the mere
presence of multiple conversational questions is not a deterministic cause.

WRONG: Security rule as an instruction (LLM can ignore it)
```agentscript
subagent admin_panel:
    reasoning:
        instructions: ->
            | Only respond if the user is an admin.
              If they are not an admin, tell them access is denied.
```

Model instructions influence behavior but do not provide the same enforcement
as a runtime gate over a trusted authorization value. For this protected
boundary, use a `before_reasoning` guard that resolves before the planner. See
Section 8 for the available gating mechanisms.

### Writing Effective Instructions

Three useful factors for subjective control effectiveness are clear response
duties, instruction ordering, and grounding.

**Describe the duty, not a draft reply.** By default, tell the model what the
response must accomplish: the facts to use, claims to avoid, action to take,
and next conversational objective. Do not write ordinary prompt fragments as
finished user-facing copy. Copy-first instructions can hide the intended
behavior, adapt poorly to conversation context, and make conflicting duties
harder to notice.

Use exact response copy only when the wording itself is a requirement, such as
an approved legal or compliance notice. State that contract explicitly with
language such as `Respond with exactly this text, with no additions:`. Label
optional wording as an example and state which tone or content properties the
model should preserve.

**Instruction Ordering.** The runtime resolves instructions top-to-bottom —
evaluating conditions and expanding template expressions — before the LLM sees
the assembled result. Ordering controls the order of prompt fragments, not
whether the model can respond before a later deterministic condition resolves.
Put the current objective and highest-consequence guidance where it is easy to
notice, and use exclusive predicates or a transition when two duties must not
coexist.

The checkout examples assume `cart_validation_failed`, `cart_total`,
`free_shipping_eligible`, and `shipping_cost` are exact outputs from cart and
entitlement actions. Each is consumed by the shown prompt branch or output
reference; none mirrors a conversational fact.

RIGHT: Completed and first-entry duties are mutually exclusive
```agentscript
subagent checkout:
    reasoning:
        instructions: ->
            if @variables.cart_validation_failed:
                | Explain that one or more cart items are unavailable. Do not
                  offer payment. Ask the user to review or remove those items.

            if @variables.cart_validation_failed == False:
                | Tell the user the current cart total is
                  {!@variables.cart_total}. Ask whether they want to proceed to
                  payment or cancel.

            if @variables.cart_validation_failed == False and @variables.free_shipping_eligible:
                | Tell the user shipping is free.

            if @variables.cart_validation_failed == False and @variables.free_shipping_eligible == False:
                | Tell the user standard shipping costs
                  {!@variables.shipping_cost}.
```

WRONG: Conflicting fragments can be assembled together
```agentscript
subagent checkout:
    reasoning:
        instructions: ->
            | Tell the user the current cart total is
              {!@variables.cart_total}. Ask whether they want to proceed to
              payment or cancel.

            if @variables.cart_validation_failed:
                | Explain that one or more cart items are unavailable and ask
                  the user to review or remove them.
```

The problem is not that the model responds before the bottom condition is
evaluated; deterministic resolution finishes first. The problem is that both
the payment duty and failure duty can reach the same assembled prompt.

**Grounding.** The platform's grounding service validates that the agent's response matches action output data. Paraphrasing or embellishing may cause grounding failures. In the example below, `event_date` is exact action output consumed by the response.

- Use specific values: `"The event is on {!@variables.event_date}"` grounds reliably; `"The event is next week"` may not.
- Avoid transforming values: return `"Tuesday"` as-is, not `"day after Monday"`.
- Avoid embellishment instructions: `"Respond like a pirate"` increases grounding risk — embellished content has no output to ground against.

Grounding validation requires **live mode preview** (`sf agent preview --use-live-actions --json`). Simulated mode preview generates fake outputs, so grounding has nothing real to validate against.

**Naming output fields in post-action instructions.** Name the fields needed in
the response when generic result-presentation guidance produces the wrong
format or tool choice in the target runtime. Observed configurations may expose
platform presentation tools such as `show_command`; if traces show the model
selecting one when direct text is required, add a scoped instruction to compose
text and test it with that configuration. Do not add a universal
`show_command` prohibition to agents where the tool is absent or desired.

### Post-Action Behavior

When a model-selected action batch completes without a handoff, pause,
cancellation, or limit, the runtime begins another reasoning iteration with
updated state. The LLM may call the same still-available action again. To
prevent unwanted loops, see Section 9 (Action Loop Prevention).

---

## 8. Gating Patterns

### `available when` — Action Visibility Gate

An action marked `available when <condition>` is hidden from the LLM when the condition is false. The LLM cannot call an unavailable action.

The examples below assume `refund_confirmed` is written only by the explicit
confirmation path. Its named consumer is the consequential refund-action gate.

**WRONG: Relying on instructions to prevent action calls**
```agentscript
subagent refunds:
    reasoning:
        instructions: ->
            | If the refund is not confirmed, do not call
              {!@actions.issue_refund}.

        actions:
            issue: @actions.issue_refund  # Always visible
```

The action is visible; instructions tell the LLM not to call it. The LLM may ignore instructions.

**RIGHT: Using `available when` to hide the action**
```agentscript
subagent refunds:
    reasoning:
        actions:
            issue: @actions.issue_refund
                available when @variables.refund_confirmed == True
```

If `refund_confirmed` is False, the LLM sees no `issue` action. Reset the value
when the user cancels or changes any material refund parameter.

### Conditional Instructions — Prompt Text Gate

Use `if/else` in instructions only when a named controlled value changes the
text the model must receive. This does not hide actions; it changes what the LLM
is told to do. Do not add a variable merely to create a conditional prompt.

```agentscript
subagent refunds:
    reasoning:
        instructions: ->
            | Explain the refund review result.

            if @variables.refund_authorized:
                | The refund is authorized. Explain the approved amount.
            else:
                | The refund is not authorized. Explain the available review
                  or escalation options.
```

Use conditional instructions when the branch has a named cause and the variable
has a trusted writer. Let surviving history and model judgment handle ordinary
preferences and current intent.

In this example, `refund_authorized` must be trusted output from the refund
review action. The prompt branch consumes that authorization result.

### `before_reasoning` Guards — Early Exit

The `before_reasoning` block runs before the LLM is invoked. Code here executes every time the subagent is entered. The LLM never sees it, cannot override it, and cannot skip it.

Here `user_role` is trusted authorization output, the guard is its named
consumer, and the cause is restricted admin authority.

```agentscript
subagent admin_panel:
    before_reasoning:
        if @variables.user_role != "admin":
            transition to @subagent.access_denied

    reasoning:
        instructions: | You are in the admin panel.
```

If the user is not an admin, they transition out before the LLM is invoked. The admin subagent's reasoning instructions never execute.

### Multi-Condition Gating

Combine `available when`, conditional instructions, and guards to enforce complex rules.

Example: "Show the payment action only if the user is authenticated AND the cart is not empty AND we're not in a preview/demo mode"

Assume `is_demo_mode` comes from deployment configuration,
`authenticated` from verification output, and `items_in_cart` from the cart
service. The consumers enforce environment safety, authorization, and the
preconditions of a consequential payment.

```agentscript
subagent checkout:
    before_reasoning:
        if @variables.is_demo_mode:
            transition to @subagent.demo_complete

    reasoning:
        instructions: ->
            if @variables.items_in_cart == 0:
                | Explain that the cart is empty and ask the user to select an
                  item before checkout.

            if @variables.items_in_cart > 0:
                | Summarize the current order and help the user review it before
                  payment.

        actions:
            pay: @actions.process_payment
                available when @variables.authenticated == True
                    and @variables.items_in_cart > 0
```

### External-Outcome Sequential Gate

Use state for ordered stages only when each value records a successful external
outcome consumed by the next runtime gate. Do not also store a `current_step`
counter.

```agentscript
variables:
    step1_verified: mutable boolean = False
    step2_verified: mutable boolean = False
    step3_verified: mutable boolean = False

subagent verification:
    reasoning:
        actions:
            verify_step1: @actions.run_check_1
                set @variables.step1_verified = @outputs.success
            verify_step2: @actions.run_check_2
                available when @variables.step1_verified == True
                set @variables.step2_verified = @outputs.success
            verify_step3: @actions.run_check_3
                available when @variables.step2_verified == True
                set @variables.step3_verified = @outputs.success
            proceed: @utils.transition to @subagent.confirmed
                available when @variables.step3_verified == True
```

Each flag has one trusted writer and a named next-step consumer. Failed actions
must leave the next action unavailable. Define only the correction,
cancellation, reset, and expiry semantics relevant to the real workflow and
the lifetime of that state.

### Same-Turn Behavior After Gate Transitions

When a gate subagent (e.g., username collection) uses `after_reasoning` to transition into a routing subagent, both subagents process in the **same user turn**. The router receives the user's original message — the one that satisfied the gate — not a fresh utterance.

This means if the user said "My username is alex" and the gate transitions to a subagent router, the router's reasoning fires against "My username is alex." Since that message doesn't match any domain subagent, the router may misclassify it (e.g., routing to `off_topic`).

**Mitigation:** Avoid a same-turn gate-to-router transition when the triggering
utterance is not itself routable. Transition directly to the known destination,
or let the gate produce its outcome and route the next user turn normally.
Do not introduce an “arrived from gate” latch unless a reproduced trace requires
it and the latch has reset, cancellation, and intent-change behavior.

---

## 9. Action Loop Prevention

An action loop occurs when the LLM calls the same action repeatedly without new user input. Three things combine to cause loops:

- **No `available when` gate.** An action without an `available when` condition appears in the LLM's context every reasoning cycle. There is no mechanism that automatically hides an action after it executes — if you don't gate it, it stays visible indefinitely.
- **Variable-bound input.** When you bind an input to a variable (`with param = @variables.x`), the action is "ready to go" every cycle — the LLM doesn't need to extract values from the conversation. It can invoke the action with zero friction.
- **No post-action instructions.** The instructions don't tell the LLM what to do after the action completes, so it may call the action again.

**WRONG: All three loop conditions present**
```agentscript
subagent events:
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
subagent events:
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
                with interest = ...
```

**2. Slot-Filling Instead of Conversational State.**

Use `...` so the model extracts the latest value from the current turn and
surviving history. Do not copy the query into a variable merely to reuse it.

```agentscript
subagent search:
    reasoning:
        instructions: ->
            | Help the user search for products. Ask what they want, then use
              {!@actions.search}.

        actions:
            search: @actions.search
                with query = ...
```

The model must decide whether the latest conversation contains a new search
request instead of receiving a permanently ready variable-bound action.

**3. Machine Guard for Consequential Repeats.**

When repeat execution could change external state twice, use an explicit
confirmation value and successful action identifier as machine-checkable
consumers. This is safety state, not conversation-flow state.

```agentscript
variables:
    operation_confirmed: mutable boolean = False
    operation_id: mutable string = ""

subagent commit:
    reasoning:
        actions:
            execute: @actions.commit_operation
                with target = ...
                available when @variables.operation_confirmed == True
                    and @variables.operation_id == ""
                set @variables.operation_id = @outputs.id
```

Write `operation_confirmed` only from the explicit confirmation path; reset it
on cancel or any material correction. Preserve `operation_id` as the successful
external result and idempotency evidence.

**Combine mitigations for reinforcement:**

```agentscript
subagent lookup:
    reasoning:
        instructions: ->
            | Once you have the result, present it. Do NOT call the action again.

        actions:
            lookup: @actions.find_data
                with key = ...  # Requires extraction each time
```

Use state in the combined design only if the action is consequential enough to
require the machine guard above.
