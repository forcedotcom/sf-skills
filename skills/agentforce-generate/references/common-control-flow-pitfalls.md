# Common AgentScript Control-Flow Pitfalls

Use this checklist when authoring, reviewing, debugging, or optimizing an
AgentScript workflow. It focuses on mistakes that look reasonable in the source
but do not mean what their formatting suggests.

For an audit, use the contents below as a lookup after the initial artifact
scan. Read the sections that match a named observation; do not delay a ranked
finding or repair by reviewing every pitfall first.

## Contents

- [The simple mental model](#the-simple-mental-model)
- [Variable visibility and condition ownership](#variable-visibility-and-condition-ownership)
- [Prompt text that looks like code](#prompt-text-that-looks-like-code)
- [Repeated prompt markers](#repeated-prompt-markers)
- [Step labels without runtime state](#step-labels-without-runtime-state)
- [Focused continuation references](#focused-continuation-references)
- [Review checklist](#review-checklist)

## The simple mental model

AgentScript has three different execution surfaces:

1. Deterministic constructs such as `if`, `run`, `set`, `transition to`, and
   lifecycle hooks execute in the runtime.
2. Text introduced by `|` becomes instructions for the model.
3. Actions under `reasoning.actions` become tools the model may choose.

Do not rely on indentation, numbering, or imperative words inside prompt text
to behave like runtime control flow.

## Variable visibility and condition ownership

### Pitfall: the model is expected to read stored state

The runtime can evaluate and bind `@variables.X`. The model cannot inspect the
variable store directly. Inside `|` text, a bare variable reference contributes
only its literal name; it does not inject the stored value. The same value could
still be visible if it was separately interpolated or preserved in conversation
or tool history:

```agentscript
# Model sees the characters "@variables.case_summary", not the summary value.
| Explain @variables.case_summary to the customer.

# Model receives the current value.
| Explain this case summary: {!@variables.case_summary}
```

Do not add interpolation when the text merely names a parameter:

```agentscript
| Set next_destination to "self_service".
```

That instruction asks the model to supply a value; it does not ask the model to
read the current value.

### Pitfall: interpolation is mistaken for deterministic control

```agentscript
# BAD when this must be an exact branch
| If {!@variables.account_status} == "blocked":
    do the blocked-account steps.
```

The merge field reveals the value, but the model still performs the comparison
and decides whether to comply. If the runtime fact must always select the same
branch, use AgentScript control:

```agentscript
if @variables.account_status == "blocked":
    | Help the customer recover access to the blocked account.
```

Keep situation-aware judgment with the model:

```agentscript
| If the user wants to speak with a human, use
  {!@actions.escalate_to_support}.
```

Do not convert conditions mechanically. Ask whether the decision is an exact
trusted fact with a mandatory consequence or an interpretation of natural
language and context.

## Prompt text that looks like code

### Pitfall: indented prompt text appears scoped

```agentscript
if @variables.lookup_failed == True:
    | Failure path:
        Call {!@actions.create_ticket}.
```

The indentation after `|` formats model-visible prose. It does not place
`create_ticket` inside the deterministic `if`.

Fix:

- Use the `if` to select the prompt text.
- Use `available when` to select the action schema.

```agentscript
reasoning:
    instructions: ->
        if @variables.lookup_failed == True:
            | Explain that the lookup failed. If the customer asks to create a
              ticket, use the ticket action.
    actions:
        create_ticket: @actions.create_ticket
            available when @variables.lookup_failed == True
```

### Pitfall: prompt verbs are mistaken for commands

Inside a pipe block, these are ordinary words:

```text
Show | Ask | Call | Set | Stop | Continue | Go to
```

They may guide the model, but they do not:

- send a response deterministically;
- mutate a variable;
- execute an action;
- stop runtime resolution; or
- transition to another subagent.

Use runtime `set` and `transition to` for deterministic state-based behavior.
Expose an action when the model should judge whether to act.

### Pitfall: stronger wording is used as enforcement

Repeating `MANDATORY`, `DO NOT SKIP`, or `IMMEDIATELY` does not create a runtime
guarantee. If ordering or eligibility matters, represent it with machine-known
state, action inputs, `available when`, deterministic action chaining, or one
purpose-built implementation that owns the sequence.

## Repeated prompt markers

### Pitfall: every sentence starts a new `|` fragment

Inside one contiguous prompt block, use one `|` marker and continue subsequent
lines beneath its content:

```agentscript
reasoning:
    instructions: ->
        | Explain the available options.
          Ask which option the user prefers.
          Keep the answer concise.
```

A same-scope run of `|`-prefixed sentences is valid syntax, but each marker
starts another prompt fragment. It does not create a stage, pause, priority, or
control boundary. Repeating the marker adds visual noise and can make the
resolved prompt harder to review.

Start another `|` after a runtime statement or branch when a new prompt
fragment is structurally required. Preserve existing structural indentation,
and compile after cleanup. Treat this as a Surface readability repair unless
prompt inspection or evaluation shows a behavioral consequence.

## Step labels without runtime state

### Pitfall: step numbers are treated as a workflow engine

```agentscript
if @variables.ready == True:
    | Step 4 — Submit the request.
```

The model may see “Step 4” without Steps 1–3. AgentScript includes only the
prompt branches that resolve true during the current reasoning iteration.
Numbering does not prove that earlier work happened.

Fix:

- Remove step numbers when they are only explanatory labels.
- If earlier work is a real prerequisite, gate the later action on trusted
  output from that work.

```agentscript
submit: @actions.submit_request
    available when @variables.validation_succeeded == True
```

### Pitfall: a prompt depends on missing context

Each resolved prompt fragment should make sense with the other fragments that
can accompany it in the same reachable state. Avoid instructions
such as “continue to the next step,” “use the result above,” or “as described
earlier” when the referenced fragment may not survive conditional resolution.

Name the actual objective and relevant state in the branch:

```agentscript
if @variables.validation_succeeded == True:
    | Validation succeeded. Submit the verified request.
```

### Pitfall: stored state is assumed to be model-visible

Storing an action output in `@variables` makes it available to runtime
conditions and later bindings. It does not automatically insert the value into
model-facing instructions. When the model must read a stored value, inject it
explicitly:

```agentscript
if @variables.lookup_result != "":
    | Use this lookup result: {!@variables.lookup_result}
```

Prefer typed outputs and deterministic conditions when the value controls
authorization, eligibility, routing, or another consequential decision.

## Focused continuation references

- [Action and Sequencing Pitfalls](control-flow-actions-sequencing.md) — action availability, same-turn sequences, state timing, stale results, missing producers, and overlapping conditions.
- [Lifecycle and Side-Effect Pitfalls](control-flow-lifecycle-side-effects.md) — per-turn resets, self-transitions, same-iteration assumptions, competing owners, and response text mistaken for proof.

## Review checklist

For every reasoning branch:

- [ ] Does the resolved prompt make sense without hidden earlier “steps”?
- [ ] Is every stored value the model must read explicitly injected?
- [ ] Is every exact trusted comparison owned by runtime control when its
      consequence must not vary?
- [ ] Are semantic intent and ambiguity left to model judgment?
- [ ] Does the branch have one next outcome?
- [ ] Are `Show`, `Ask`, `Call`, `Set`, and `STOP` being used only as prose?
- [ ] Are material actions gated independently of the prompt paragraph?
- [ ] Can any action remain available after success and repeat?
- [ ] Does prompt text request a tool call while later deterministic logic
      assumes that call has already happened?
- [ ] Does the branch ask for and consume the same future answer?
- [ ] Are ordered tool calls enforced by the runtime when order matters?
- [ ] Is every completion flag backed by a complete, usable result?
- [ ] Is every condition value produced on every reachable path?
- [ ] Are typed outputs used for machine-controlled decisions?
- [ ] Are independent conditions intentionally cumulative or provably mutually
      exclusive, and is first-match priority expressed with an
      `if / else if / else` chain when it matters?
- [ ] Can lifecycle logic overwrite a legitimate later value?
- [ ] Does state encode durable evidence rather than duplicating history or
      representing one phase with overlapping latches?
- [ ] Is the reasoning burden appropriate for the deployed target model?
- [ ] Does exactly one mechanism own each external side effect?
- [ ] Do tests inspect action availability and external results, not only final
      model text?
