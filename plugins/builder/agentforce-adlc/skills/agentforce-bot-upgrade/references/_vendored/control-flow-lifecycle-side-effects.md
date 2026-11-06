# AgentScript Lifecycle and Side-Effect Pitfalls

Use this reference when per-turn lifecycle code, transitions, repeated
reasoning, or competing side-effect owners may explain a behavior defect.

## Lifecycle code that overwrites later work

### Pitfall: `before_reasoning` resets a value every turn

`before_reasoning` runs once when that subagent execution begins. A transition,
including a self-transition, can start another subagent execution in the same
user turn. An unconditional assignment there can erase a value captured or
inferred earlier.

Review every lifecycle assignment by asking:

- Is this an initialization or an unconditional reset?
- Can a later branch legitimately change it?
- When and where is it cleared?

Initialize only when the value is unset, or let the destination subagent own its
own intent.

### Pitfall: a transition reprocesses the same customer message

A transition can start the target subagent during the same customer turn. The
target may receive the message that completed the prior gate, not a fresh
request. Make the target coherent for that arrival path or transition only when
the target has enough explicit state to act safely.

### Pitfall: same-iteration instructions assume a deterministic pause

Deterministic lifecycle statements continue resolving after a `run` stores its
output. A nearby `|` block adds text to the model's next prompt; it does not
pause runtime execution so the model can act before the following `set` or
condition.

Remember the execution order:

```text
1. Resolve deterministic run, set, and if statements and assemble all | text.
2. Send the completed prompt to the model, which may call a tool or respond.
```

For example, this is unsafe when the parsed fields still hold defaults:

```agentscript
run @actions.validate
    set @variables.raw_result = @outputs.output
| Parse the raw result and store the derived flags.
set @variables.validation_checked = True
```

Use typed outputs, deterministic normalization, a purpose-built action that
owns the operation, or an explicit reasoning boundary. A guarded
self-transition can serve as a boundary
when the runtime offers no smaller supported stage: the first pass stores the
raw result and exits; re-entry builds a fresh prompt from that result; the next
model action stores all derived fields and the completion flag together.
Document that pattern as a phase boundary, not as a generic loop.

## Competing owners for one side effect

### Pitfall: two mechanisms both appear to perform the same operation

Examples:

- one action is named “validate and submit,” followed by another submit action;
- an external action performs transfer, followed by a utility escalation;
- a transition and a delegated subagent both own completion.

Choose one owner for each external side effect. Document whether other actions
prepare, validate, invoke, or verify it.

### Pitfall: model text is treated as proof

A promise, confirmation, or tool name in the model response is not evidence
that an external action occurred. An instruction such as `Call
escalate_to_live_engineer` only asks the model to select that tool. The model
may instead answer “I'm transferring you,” and a text-only response is a valid
reasoning result. Verify separately:

```text
configured -> available -> invoked -> executed -> effected
```

Advance consequential state only at the strongest layer the runtime can prove.
