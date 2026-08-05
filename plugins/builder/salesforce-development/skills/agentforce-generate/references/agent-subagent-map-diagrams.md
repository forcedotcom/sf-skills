# Agent Subagent Map Diagrams Reference

## Table of Contents

- [Purpose and Context](#purpose-and-context)
- [Fundamental Structure Rules](#fundamental-structure-rules)
- [Node Types and Agent Script Elements](#node-types-and-agent-script-elements)
- [Subagent Map Patterns](#subagent-map-patterns)
- [Complete Example: Local_Info_Agent](#complete-example-local_info_agent)
- [Validation Checklist](#validation-checklist)
- [Anti-patterns](#anti-patterns)

---

## Purpose and Context

A Subagent Map diagram is a Mermaid flowchart that visualizes an agent's
subagent graph structure. Use the smallest graph that represents the design.
For a multi-subagent agent, it displays:

- The `start_agent agent_router` entry point when multiple genuine domains need
  intent classification
- All subagents in the agent
- Subagent transitions and routing logic
- Action calls within subagents (with backing type: Apex, Prompt Template, Flow)
- Gating conditions (`available when` expressions), when required
- Variable state changes that have a trusted writer and named consumer
- Escalation and off-topic handling
- Conditional instructions based on variable values

Subagent Map diagrams are the primary visual deliverable in an Agent Spec (design document) and serve both specification and comprehension purposes.

---

## Fundamental Structure Rules

### Graph Orientation

- ALWAYS use `graph TD` (Top-Down orientation)
- Put the `start_agent` entry point at the top
- For a router-first design, subagents flow downward from the router
- Never use other orientations

### Node Identification

- Use sequential capital letters (A, B, C, ...) for node IDs
- Start with `A` for start_agent
- Increment sequentially through subagents and decisions
- Use descriptive labels within brackets

### Flow Direction

- Primary flow moves top-to-bottom
- Use `-->` for standard transitions
- Label decision branches with `|Label|` syntax
- Separate paths for different subagents

---

## Node Types and Agent Script Elements

### Start Agent Subagent Router Node

Format: `[start_agent<br/>agent_router]`

Represents the entry point where user input is evaluated and routed to appropriate subagents.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>agent_router]
```

### Subagent Nodes

Format: `[subagent_name<br/>Subagent]`

Represents a subagent within the agent.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>agent_router]
    B[order_status<br/>Subagent]
    C[billing<br/>Subagent]
```

### Action Call Nodes

Format: `[Call action_name<br/>backing: Type]`

Backing types: Apex, Prompt Template, Flow

Example: `[Call check_weather<br/>backing: Apex]`

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[local_weather<br/>Subagent] --> B[Call check_weather<br/>backing: Apex]
```

### Decision/Gating Nodes

Use curly braces `{}` for required deterministic conditions. Common formats:

- Authorization or confirmation gates: `{Check: customer_verified == true?}`
- External outcome gates: `{Check: verification_success == true?}`
- Subagent transition logic: `{user_intent matches?}`

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[account_changes<br/>Subagent] --> B{Check: customer_verified<br/>== true?}
    B -->|Yes| C[Call update_account<br/>backing: Flow]
    B -->|No| D[Call verify_customer<br/>backing: Apex]
```

### Variable State Change Nodes

Format: `[Set verified_customer_id<br/>= action output]`

Show a state modification only when a later runtime gate, transition, or action
binding consumes it. Ordinary conversational facts belong in conversation
history and do not need state-change nodes.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[Call verify_customer] --> B[Set verified_customer_id<br/>= action output]
    B --> C{Check: verified_customer_id<br/>!= empty?}
    C -->|Yes| D[Protected action available]
```

### Utility Call Nodes

Format: `[Call @utils.name]`

For escalation and system utilities.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[escalation<br/>Subagent] --> B[Call @utils.escalate]
```

---

## Subagent Map Patterns

### Basic Subagent with Single Action

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>agent_router]
    A -->|route to subagent| B[simple_subagent<br/>Subagent]
    B --> C[Call do_action<br/>backing: Apex]
    C --> D[Continue]
```

### Subagent with Gating Condition

`available when` expressions prevent protected action execution until trusted
preconditions are met.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[account_changes<br/>Subagent]
    A --> B{Check: verified_customer_id<br/>!= empty?}
    B -->|No| C[Call verify_customer<br/>backing: Apex]
    B -->|Yes| D[Protected account action<br/>backing: Flow]
    C --> E[Set verified_customer_id<br/>= action output]
    E --> A
```

### Subagent with Conditional Instructions

Trusted action outputs or named invariants may control which instructions apply.
Do not add a variable solely to create a conditional prompt.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[Call verify_customer<br/>backing: Apex]
    A --> B[Set verification_success<br/>= action output]
    B --> C{Check: verification_success<br/>== true?}
    C -->|Yes| D[Offer protected operations]
    C -->|No| E[Explain verification failure]
```

### Subagent Transitions

When logic determines a new subagent should be active.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[current_subagent<br/>Subagent]
    A --> B{Transition<br/>condition?}
    B -->|Yes| C[Transition to<br/>next_subagent]
    C --> D[next_subagent<br/>Subagent]
    B -->|No| E[Continue in<br/>current_subagent]
```

### Off-Topic and Escalation Routing

How the agent handles out-of-scope requests.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>agent_router]
    A -->|out of scope| B[off_topic<br/>Subagent]
    A -->|needs help| C[escalation<br/>Subagent]
    B --> D[Instruction: redirect user]
    C --> E[Call @utils.escalate]
```

---

## Complete Example: Local_Info_Agent

This example demonstrates a complete Subagent Map for a guest information
agent. It needs no mutable state: surviving conversation history carries
follow-up context, and each action can slot-fill its input from the conversation.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>agent_router]

    A -->|weather query| B[local_weather<br/>Subagent]
    A -->|events query| C[local_events<br/>Subagent]
    A -->|hours query| D[resort_hours<br/>Subagent]
    A -->|unclear intent| E[ambiguous_question<br/>Subagent]
    A -->|out of scope| F[off_topic<br/>Subagent]
    A -->|needs escalation| G[escalation<br/>Subagent]

    B --> B1[Call check_weather<br/>backing: Apex]
    B1 --> B2[Continue]

    C --> C1[Call check_events<br/>backing: Prompt Template]
    C1 --> C2[Continue]

    D --> D1[Call get_resort_hours<br/>backing: Flow]
    D1 --> D2[Continue]

    E --> E1[Instruction: ask for clarification]
    E1 --> E2[Await user input]
    E2 --> A

    F --> F1[Instruction: explain available subagents]
    F1 --> F2[Continue]

    G --> G1[Call @utils.escalate]
    G1 --> G2[Continue]
```

### Subagent Descriptions

**local_weather**: Provides weather information via Apex-backed action. No preconditions.

**local_events**: Uses the Prompt Template-backed action when the user asks for
events. Its conversational input is slot-filled from the current turn and
surviving history.

**resort_hours**: Calls a Flow-backed action and presents its returned hours.

**ambiguous_question**: No actions. Requests clarification and routes back to start_agent.

**off_topic**: No actions. Explains available subagents and continues conversation.

**escalation**: Calls @utils.escalate utility to route to human agent.

**start_agent agent_router**: Routes incoming user input to appropriate subagents based on intent.

---

## Validation Checklist

Before finalizing a Subagent Map diagram:

- [ ] Uses `graph TD` syntax
- [ ] Starts with `%%{init: {'theme':'neutral'}}%%`
- [ ] `start_agent` is node A at top; use `agent_router` only for a
      router-first multi-domain design
- [ ] Nodes use sequential capital letter IDs
- [ ] All subagents labeled with `[subagent_name<br/>Subagent]` format
- [ ] Action calls include backing type (Apex, Prompt Template, Flow)
- [ ] Required gating conditions are shown as decision nodes with `{Check: ...?}` format
- [ ] Every shown variable has a trusted writer and named runtime consumer
- [ ] Variable state changes that affect logic are labeled with `[Set variable = value]`
- [ ] Escalation uses `[Call @utils.escalate]` format
- [ ] All transition branches are labeled
- [ ] Diagram fits in 20-30 nodes
- [ ] Subagent routing from start_agent is clear
- [ ] Off-topic and escalation paths are visible
- [ ] Required conditional instruction logic is shown

---

## Anti-patterns

### Don't

- Use `graph LR` or other orientations instead of `graph TD`
- Place `start_agent` anywhere except top (node A)
- Label actions without backing type information
- Use ambiguous decision node labels (avoid `{Process?}`)
- Hide gating conditions in node descriptions instead of showing as decisions
- Omit variable state changes that affect downstream behavior
- Add variables for facts already available in surviving conversation history
- Show a state node without its trusted writer and named consumer
- Create subagent routing without labels on the decision logic
- Mix subagent nodes with action nodes at same level without clear containment
- Use custom color styling (breaks in dark mode)
- Leave off-topic and escalation paths out of diagram

### Do

- Keep the selected `start_agent` at the top
- Show all subagents reachable from start_agent
- Include backing type for every action call
- Make gating conditions explicit as decision nodes
- Show justified variable updates as separate nodes when they affect logic flow
- Label all transition branches
- Include off-topic and escalation subagents
- Show conditional instructions with decision nodes
- Use `%%{init: {'theme':'neutral'}}%%` for light/dark mode compatibility
- Focus diagram on subagent structure, not detailed action logic
