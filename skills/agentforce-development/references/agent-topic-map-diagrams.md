# Agent Topic Map Diagrams Reference

## Table of Contents

- [Purpose and Context](#purpose-and-context)
- [Fundamental Structure Rules](#fundamental-structure-rules)
- [Node Types and Agent Script Elements](#node-types-and-agent-script-elements)
- [Topic Map Patterns](#topic-map-patterns)
- [Complete Example: Local_Info_Agent](#complete-example-local_info_agent)
- [Validation Checklist](#validation-checklist)
- [Anti-patterns](#anti-patterns)

---

## Purpose and Context

A Topic Map diagram is a Mermaid flowchart that visualizes an agent's topic graph structure. It shows the architecture of an agent before implementation, displaying:

- The start_agent topic_selector entry point
- All topics in the agent
- Topic transitions and routing logic
- Action calls within topics (with backing type: Apex, Prompt Template, Flow)
- Gating conditions (available_when expressions)
- Variable state changes
- Escalation and off-topic handling
- Conditional instructions based on variable values

Topic Map diagrams are the primary visual deliverable in an Agent Spec (design document) and serve both specification and comprehension purposes.

---

## Fundamental Structure Rules

### Graph Orientation

- ALWAYS use `graph TD` (Top-Down orientation)
- Start with start_agent topic_selector at the top
- Topics flow downward from the selector
- Never use other orientations

### Node Identification

- Use sequential capital letters (A, B, C, ...) for node IDs
- Start with `A` for start_agent
- Increment sequentially through topics and decisions
- Use descriptive labels within brackets

### Flow Direction

- Primary flow moves top-to-bottom
- Use `-->` for standard transitions
- Label decision branches with `|Label|` syntax
- Separate paths for different topics

---

## Node Types and Agent Script Elements

### Start Agent Topic Selector Node

Format: `[start_agent<br/>topic_selector]`

Represents the entry point where user input is evaluated and routed to appropriate topics.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]
```

### Topic Nodes

Format: `[topic_name<br/>Topic]`

Represents a topic within the agent.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]
    B[order_status<br/>Topic]
    C[billing<br/>Topic]
```

### Action Call Nodes

Format: `[Call action_name<br/>backing: Type]`

Backing types: Apex, Prompt Template, Flow

Example: `[Call check_weather<br/>backing: Apex]`

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[local_weather<br/>Topic] --> B[Call check_weather<br/>backing: Apex]
```

### Decision/Gating Nodes

Use curly braces `{}` for conditions. Common formats:

- Variable availability gates: `{Check: variable_name != empty?}`
- Conditional instructions: `{variable_name == value?}`
- Topic transition logic: `{user_intent matches?}`

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[topic<br/>Topic] --> B{Check: guest_interests<br/>!= empty?}
    B -->|Yes| C[Call collect_events<br/>backing: Prompt Template]
    B -->|No| D[Ask for clarification]
```

### Variable State Change Nodes

Format: `[Set variable_name = value]`

Shows state modifications that affect downstream behavior.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[Call action] --> B[Set reservation_required<br/>= true]
```

### Utility Call Nodes

Format: `[Call @utils.name]`

For escalation and system utilities.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[escalation<br/>Topic] --> B[Call @utils.escalate]
```

---

## Topic Map Patterns

### Basic Topic with Single Action

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]
    A -->|route to topic| B[simple_topic<br/>Topic]
    B --> C[Call do_action<br/>backing: Apex]
    C --> D[Continue]
```

### Topic with Gating Condition

Available_when expressions prevent action execution until conditions are met.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[topic_with_gate<br/>Topic]
    A --> B{Check: required_var<br/>!= empty?}
    B -->|No| C[Instruction: collect info first]
    B -->|Yes| D[Call action<br/>backing: Prompt Template]
    C --> E[Wait for input]
    E --> A
```

### Topic with Conditional Instructions

Variable values control which instructions apply to a topic.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[Call process_request<br/>backing: Flow]
    A --> B[Set status_flag = complete]
    B --> C{Check: status_flag<br/>== complete?}
    C -->|Yes| D[Apply conditional<br/>instructions]
    D --> E[Continue]
```

### Topic Transitions

When logic determines a new topic should be active.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[current_topic<br/>Topic]
    A --> B{Transition<br/>condition?}
    B -->|Yes| C[Transition to<br/>next_topic]
    C --> D[next_topic<br/>Topic]
    B -->|No| E[Continue in<br/>current_topic]
```

### Off-Topic and Escalation Routing

How the agent handles out-of-scope requests.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]
    A -->|out of scope| B[off_topic<br/>Topic]
    A -->|needs help| C[escalation<br/>Topic]
    B --> D[Instruction: redirect user]
    C --> E[Call @utils.escalate]
```

---

## Complete Example: Local_Info_Agent

This example demonstrates a complete Topic Map for a guest information agent with multiple topics, gating conditions, variable state, and escalation handling.

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]

    A -->|weather query| B[local_weather<br/>Topic]
    A -->|events query| C[local_events<br/>Topic]
    A -->|hours query| D[resort_hours<br/>Topic]
    A -->|unclear intent| E[ambiguous_question<br/>Topic]
    A -->|out of scope| F[off_topic<br/>Topic]
    A -->|needs escalation| G[escalation<br/>Topic]

    B --> B1[Call check_weather<br/>backing: Apex]
    B1 --> B2[Continue]

    C --> C1{Check: guest_interests<br/>!= empty?}
    C1 -->|No| C2[Instruction: collect guest interests]
    C1 -->|Yes| C3[Call check_events<br/>backing: Prompt Template]
    C2 --> C4[Pause for input]
    C4 --> C
    C3 --> C5[Continue]

    D --> D1[Call get_resort_hours<br/>backing: Flow]
    D1 --> D2[Set reservation_required<br/>= true]
    D2 --> D3{Check: reservation_required<br/>== true?}
    D3 -->|Yes| D4[Apply booking instructions]
    D3 -->|No| D5[Apply standard instructions]
    D4 --> D6[Continue]
    D5 --> D6

    E --> E1[Instruction: ask for clarification]
    E1 --> E2[Await user input]
    E2 --> A

    F --> F1[Instruction: explain available topics]
    F1 --> F2[Continue]

    G --> G1[Call @utils.escalate]
    G1 --> G2[Continue]
```

### Topic Descriptions

**local_weather**: Provides weather information via Apex-backed action. No preconditions.

**local_events**: Requires guest_interests variable to be populated (gating: `available_when guest_interests != ""`). Calls Prompt Template-backed action only when gate is satisfied.

**resort_hours**: Calls Flow-backed action that sets reservation_required variable. Conditional instructions applied based on variable state: booking-specific guidance when true, standard guidance when false.

**ambiguous_question**: No actions. Requests clarification and routes back to start_agent.

**off_topic**: No actions. Explains available topics and continues conversation.

**escalation**: Calls @utils.escalate utility to route to human agent.

**start_agent topic_selector**: Routes incoming user input to appropriate topics based on intent.

---

## Validation Checklist

Before finalizing a Topic Map diagram:

- [ ] Uses `graph TD` syntax
- [ ] Starts with `%%{init: {'theme':'neutral'}}%%`
- [ ] start_agent topic_selector is node A at top
- [ ] Nodes use sequential capital letter IDs
- [ ] All topics labeled with `[topic_name<br/>Topic]` format
- [ ] Action calls include backing type (Apex, Prompt Template, Flow)
- [ ] Gating conditions shown as decision nodes with `{Check: ...?}` format
- [ ] Variable state changes explicitly labeled with `[Set variable = value]`
- [ ] Escalation uses `[Call @utils.escalate]` format
- [ ] All transition branches are labeled
- [ ] Diagram fits in 20-30 nodes
- [ ] Topic routing from start_agent is clear
- [ ] Off-topic and escalation paths are visible
- [ ] Conditional instruction logic is shown

---

## Anti-patterns

### Don't

- Use `graph LR` or other orientations instead of `graph TD`
- Place start_agent anywhere except top (node A)
- Label actions without backing type information
- Use ambiguous decision node labels (avoid `{Process?}`)
- Hide gating conditions in node descriptions instead of showing as decisions
- Omit variable state changes that affect downstream behavior
- Create topic routing without labels on the decision logic
- Mix topic nodes with action nodes at same level without clear containment
- Use custom color styling (breaks in dark mode)
- Leave off-topic and escalation paths out of diagram

### Do

- Keep start_agent topic_selector at the top
- Show all topics reachable from start_agent
- Include backing type for every action call
- Make gating conditions explicit as decision nodes
- Show variable updates as separate nodes when they affect logic flow
- Label all transition branches
- Include off-topic and escalation topics
- Show conditional instructions with decision nodes
- Use `%%{init: {'theme':'neutral'}}%%` for light/dark mode compatibility
- Focus diagram on topic structure, not detailed action logic
