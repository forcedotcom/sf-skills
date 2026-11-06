# AgentScript Action and Sequencing Pitfalls

Use this reference when action availability, ordered tool use, state timing, or
result handling may explain a behavior defect.

## Contents

- [Actions that escape their intended branch](#actions-that-escape-their-intended-branch)
- [Impossible same-turn sequences](#impossible-same-turn-sequences)
- [State written too early](#state-written-too-early)
- [Stale, raw, or missing action results](#stale-raw-or-missing-action-results)

## Actions that escape their intended branch

### Pitfall: mentioning an action under one branch is assumed to scope it

Actions are defined for the reasoning scope, not nested under the visual prompt
paragraph that mentions them. Unless gated, an action remains available while
other branches are active.

```agentscript
reasoning:
    instructions: ->
        if @variables.validation_succeeded == True:
            | Use the {!@actions.submit} action.
    actions:
        submit: @actions.submit_request
```

The `submit` action is still available when `validation_succeeded` is false.

Fix:

```agentscript
submit: @actions.submit_request
    available when @variables.validation_succeeded == True
```

### Pitfall: an action remains available after it succeeds

If repeating an action would duplicate a write, charge, message, or external
commitment, gate it on a result or idempotency value.

```agentscript
submit: @actions.submit_request
    available when @variables.validation_succeeded == True
    available when @variables.submission_id == ""
    set @variables.submission_id = @outputs.submission_id
```

Do not depend only on prose such as “do not call this again.”

## Impossible same-turn sequences

### Pitfall: model-selected actions are written as imperative steps

`@utils.setVariables` is a normal model-selected state-update tool. If the
model calls it successfully, the runtime stores the values. The action does
not itself define a turn boundary or guarantee another reasoning iteration.
Prompt text does not execute the tool:

```text
Call the state-setting action.
Then call the submission action.
```

The model may call either action, call both in one batch, or return text without
calling either. The second action does not automatically follow merely because
the prompt lists it second.

Fix with the smallest suitable option:

- bind current-turn values directly to the real action with `...`;
- set trusted values deterministically before reasoning;
- pass fixed values through a purpose-built transition or action;
- return the required values from the first real action; or
- combine inseparable writes into one implementation that owns the complete
  update.

### Pitfall: ask now and capture the future answer now

```text
Ask for the issue description.
Call the capture action with the issue description.
```

The answer does not exist when the question is asked. Give that branch one
outcome: ask. On the later turn, capture or use the answer.

### Pitfall: one branch requires several model-selected tools in order

The model may choose one tool, choose them in a different order, or produce a
response before the expected sequence is complete. If the order protects
authorization, correctness, or an external side effect, do not encode it only
as a tool list in prompt text.

Use deterministic post-action logic, gated actions with explicit intermediate
results, or one purpose-built action that owns the sequence.

## State written too early

### Pitfall: “complete” means “started”

Do not set:

```agentscript
set @variables.operation_completed = True
```

before the consequential action has returned a successful result.

Prefer state names that match the evidence:

```text
validation_completed
operation_requested
operation_succeeded
```

If the runtime cannot observe the final external side effect, use a weaker name
such as `operation_initiated` instead of claiming completion.

### Pitfall: workflow state advances on failure

Do not advance a stage, close a gate, or hide retry behavior merely because an
action was attempted. Branch on the trusted action result and preserve a safe
retry or failure path.

### Pitfall: state exists only to imitate dialogue stages

Avoid `current_step`, `question_asked`, or `has_greeted` when the available
conversation history already supplies the required continuity. Add state for a
named runtime consumer or when a value must outlive the usable history window;
give it the reset, correction, and failure behavior relevant to its use cases.

### Pitfall: one phase is represented several ways

Pairs such as `q1_asking`/`q1_answered`, plus `current_step` and completion
flags, can describe contradictory workflow positions. When deterministic
sequencing is truly required, prefer one explicit phase value and keep separate
state only for durable facts or trusted action inputs.

Before adding state, list its producer, consumer, reset, failure behavior, and
valid combinations with neighboring variables.

## Stale, raw, or missing action results

### Pitfall: “checked” is set before the result is usable

Do not mark validation complete while its result still needs model-driven
parsing:

```agentscript
set @variables.validation_output = @outputs.raw_json
set @variables.validation_checked = True
```

Later conditions can read old or default structured values and choose the wrong
branch. The raw output has resolved, but its derived fields have not.

Fix:

- Prefer typed action outputs.
- Otherwise normalize the raw result deterministically.
- Mark the check complete only after all branch inputs are stored.
- If normalization must be model-driven, use an explicit reasoning boundary so
  producing the raw result and consuming its parsed fields cannot occur in one
  half-populated state.

### Pitfall: raw JSON controls important branches

Do not ask the model to extract authorization, eligibility, confirmation, or
success flags from display-oriented text when those flags determine tool
availability or a consequential transition. Return typed, machine-checkable
outputs.

### Pitfall: the script branches on a value no producer returns

For every condition and `available when`, trace the value backward:

```text
consumer -> stored variable -> action output or deterministic assignment
```

If no reachable producer exists, the branch is dead or depends on an accidental
default.

### Pitfall: independent conditions overlap

Sequential top-level condition blocks are evaluated independently. This is a
pitfall only when predicates can overlap, leave an unintended gap, or require
first-match priority. Complementary predicates such as `X == value` and
`X != value` are mutually exclusive and do not overlap. When authoring new
first-match alternatives, prefer `if / else if / else`; use independent blocks
when multiple branches may run or mutual exclusion is explicit. Do not rewrite
equivalent control flow in a bounded repair solely for style. Spell the clause
`else if`; Python-style `elif` is invalid. Verify the effective prompt for each
reachable state.
