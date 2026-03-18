# Agent Spec: Agent_API_Name

## Purpose & Scope

Describe the agent's purpose in 1-2 sentences. What does it help users do?
What domain does it operate in?

## Behavioral Intent

Describe the key behavioral rules that govern the agent:
- What must the agent know before taking action?
- What backing logic types are used (Apex, Flow, Prompt Template)?
- What guardrails apply (off-topic handling, escalation)?
- What information persists across topic switches?

## Topic Map

```mermaid
%%{init: {'theme':'neutral'}}%%
graph TD
    A[start_agent<br/>topic_selector]

    A -->|description of routing condition| B[topic_name<br/>Topic]
    A -->|unclear intent| C[ambiguous_question<br/>Topic]
    A -->|out of scope| D[off_topic<br/>Topic]
    A -->|needs escalation| E[escalation<br/>Topic]
```

Expand the diagram to show actions, gating logic, and variable state changes
within each topic. See the Topic Map Diagrams reference for conventions.

## Variables

- `variable_name` (mutable type = default) — What this variable tracks.
  Set by: which action or utility. Read by: which topics for gating or
  conditional instructions.

## Actions & Backing Logic

### action_name (topic_name topic)

- **Target:** `apex://ClassName` or `flow://FlowName` or `prompt://PromptTemplateName`
- **Backing Status:** EXISTS / NEEDS STUB / NEEDS IMPLEMENTATION

#### Inputs

| Name | Type | Required | Source |
|------|------|----------|--------|
| property_id | string | Yes | User input |
| max_results | integer | No | Defaults to 10 |

#### Outputs

| Name | Type | Visible to User? | Source | Notes |
|------|------|-------------------|--------|-------|
| property | object | Yes | `Property__c` | Complete property details |
| related_applications | list[object] | Yes | `Application__c` | Records for this property |
| active_listing | boolean | Yes | `Listing__c` | Listing status |
| hasData | boolean | No | Computed | Internal empty-result flag |

> **"Visible to User?"** maps to `filter_from_agent` in the `.agent` file: Yes → `filter_from_agent: False`, No → `filter_from_agent: True`.

#### Stubbing Requirement

If NEEDS STUB:

- Apex class name and inner class wrappers needed
- `complex_data_type_name` for each `object`/`list[object]` output
- Key queries or computation logic the stub must implement

Repeat for each action.

## Gating Logic

- `action_name` visibility: `available when @variables.variable_name != ""`
  — Rationale for why this gate exists.

List all gating conditions with their rationale.

## Architecture Pattern

State the architecture pattern: hub-and-spoke, chain, hybrid, etc.
Describe the routing strategy and how topics relate to each other.

## Agent Configuration

- **developer_name:** `Agent_API_Name`
- **agent_label:** `Agent Display Name`
- **agent_type:** `AgentforceEmployeeAgent` or `AgentforceServiceAgent` — state the reasoning based on prompt signals (e.g., "accessible by employees" → Employee, "customer-facing channel" → Service)
- **default_agent_user:** Required for `AgentforceServiceAgent`. Forbidden for `AgentforceEmployeeAgent`. If specified, MUST be **user name**. MUST NEVER be **user ID**. User MUST have `Einstein Agent` license.
