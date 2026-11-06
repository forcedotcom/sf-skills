# Mapping Rules

## Objective

Convert extracted Einstein Bot behavior into a high-quality Agent Spec that `/agentforce-generate` can execute.

## Canonical Mappings

- **Dialog clusters** -> **Subagents/Topics**
- **Intent catalog** -> **Router instructions + transition actions**
- **Entity/slot collection** -> **Variables + eligibility/guard conditions**
- **Action inventory** -> **Action inventory in spec** (`NEEDS_STUB` when implementation unknown)
- **Fallback dialogs** -> **Boundary handling and recovery behavior**
- **Transfer/system handoff** -> **Built-in `@utils.escalate`** (escalation policy; never a new/standalone action)
- **End chat** -> **Built-in `@utils.end_session`** (conversation close; never a new/standalone action)

## Escalation Mapping Rule

Escalation/transfer behavior (Einstein Bot `SystemMessage` `Transfer`, or any "hand off to a live agent/human" handoff) MUST be mapped implicitly to the built-in `@utils.escalate` utility. Do NOT:

- create a new action for it in the action inventory (no `Transfer_To_Agent`-style action, no `NEEDS_STUB`/`NEEDS_CREATION` entry for the transfer),
- model it as a flow/apex/standard-invocable action, or
- represent it as generic "hand off to a human" prose without the explicit `@utils.escalate` control.

Instead:

- Express the escalation as an explicit `@utils.escalate` invocation in the relevant subagent's instructions (typically a terminal step of an escalation subagent).
- Exclude the transfer from the action inventory entirely (it is not an authored action).

## End Chat Mapping Rule

End-chat behavior (Einstein Bot `SystemMessage` `EndChat`, or any step that closes the conversation) MUST be mapped implicitly to the built-in `@utils.end_session` utility. Do NOT:

- create a new action for it in the action inventory (no `End_Chat`/`End_Session`-style action, no `NEEDS_STUB`/`NEEDS_CREATION` entry for the end chat),
- model it as a flow/apex/standard-invocable action, or
- represent it as generic "end the conversation" prose without the explicit `@utils.end_session` control.

Instead:

- Express the end chat as an explicit `@utils.end_session` invocation in the relevant subagent's instructions, at the point in the flow where the bot ended the chat (typically the terminal step of that path).
- Exclude the end chat from the action inventory entirely (it is not an authored action).

## Dialog Functionality Extraction Rules

Capture the functional behavior of each bot dialog before action optimization.

### Processing steps

1. Process each bot dialog independently.
2. Parse the dialog's bot steps strictly in configured order.
3. For each bot step, generate one or more meaningful functional sentences that describe what the bot does at that step.
4. Build an ordered list per dialog (`step_functionality`) that preserves original step sequence.

### What each step description must capture

For each step, include applicable details:

- step intent/purpose (message, collect, invoke, transition, system behavior)
- conditions/guards (for example variable comparisons and branching criteria)
- action invocations (action name and type, when invoked)
- variable updates (set/unset/collect, including affected variable names)
- transition behavior (target dialog and transition type when present)

### Exhaustive bot-step handling

When generating `step_functionality`, handle all supported Einstein Bot step families using the rules below.

1. **Message**
   - Describe user-facing message intent and any branch context.
2. **VariableOperation**
   - **Set**: capture source -> target variable assignment.
   - **Unset**: capture variable clear/reset behavior.
   - **Collect**: capture which variable is collected, requiredness, and option source (static/dynamic).
   - **SetConversationLanguage** and **CollectAttachment** are not supported: do not convert them, and record each skipped step (dialog + step) in open questions so it appears in the run report.
3. **Invocation**
   - Capture invocation target, invocation type (`apex`, `flow`, `standardInvocableAction`, `externalService`, `quickAction`, `api`), input mappings, output mappings, and resulting variable writes.
4. **Navigation**
   - Capture transition type (`Redirect` / `Call`), target dialog, and trigger condition.
5. **Wait**
   - Capture as intent-routing pause point where control waits for user input and may route to intent-enabled dialogs.
6. **Group**
   - Process nested steps recursively in order, preserving parent conditions and emitting child step sentences in sequence.
7. **SystemMessage**
   - **Transfer**: capture escalation behavior and resolved target type/value (resolved per [Extraction Blueprint](extraction-blueprint.md) step 4: from `systemMessageMappings` variable `SObjectType` + assignments when present, otherwise from the bot's `defaultOutboundFlow`), and map it implicitly to the built-in `@utils.escalate` (see Escalation Mapping Rule) — do not emit it as a new action.
   - **EndChat**: capture terminal behavior and conversation close, and map it implicitly to the built-in `@utils.end_session` (see End Chat Mapping Rule) — do not emit it as a new action.
8. **RecordLookup**
   - Capture queried object/entity, filter criteria, and output variable/list assignment.
9. **RichMessage**
   - Not supported: do not convert it, and record each skipped step (dialog + step) in open questions so it appears in the run report.
10. **GoalStep**
    - Not supported and not needed in the agent: do not convert it, and record each skipped step (dialog + step) in open questions so it appears in the run report.

### Step rendering rules

1. Preserve original step order exactly.
2. Emit one or more concise functional sentences per step.
3. Include conditional prefix when step is gated (for example `If <condition> ...`).
4. Preserve variable names and action names verbatim in step descriptions.
5. Do not skip nested steps inside `Group`.

### Output requirement

For every dialog, produce:

1. `dialog_functionality_summary` (short high-level summary)
2. `step_functionality` (ordered list of functional sentences derived step-by-step)

This output is the baseline for downstream subagent grouping and mapping decisions.

## Risk and Safety Rules

- Explicitly capture:
  - identity verification points
  - sensitive action boundaries
  - escalation to human support
  - refusal boundaries for unsupported asks

## Persistence Requirement

At the end of mapping, update `extraction-summary.json` with bot dialog functionality details for every dialog, including `dialog_functionality_summary` and ordered `step_functionality`.

When updating `extraction-summary.json` during mapping:

1. Preserve the canonical schema defined in [Extraction Blueprint](extraction-blueprint.md) (do not add/remove/rename top-level keys).
2. Update existing sections in place (`dialog_graph`, `intent_catalog`, `variables`, `action_inventory`, `dialog_clusters`, `unmapped_items`) instead of reshaping them.
3. Keep enum/status normalization stable (`redirect/call/intent_redirect`; `EXISTS/NEEDS_STUB/NEEDS_CREATION/CANDIDATE_FOR_REMOVAL`).
