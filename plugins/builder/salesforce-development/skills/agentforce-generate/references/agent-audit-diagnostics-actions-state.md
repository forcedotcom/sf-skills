# AgentScript Action and State Diagnostics

Use these categories only after the audit identifies a relevant action,
contract, state, sequencing, transition, or authority concern.

## Contents

- [Action surface and contracts](#action-surface-and-contracts)
- [Outputs and trusted decisions](#outputs-and-trusted-decisions)
- [State and lifecycle](#state-and-lifecycle)
- [Turn sequencing](#turn-sequencing)
- [Transitions and message continuity](#transitions-and-message-continuity)
- [Authority and side effects](#authority-and-side-effects)

## Action surface and contracts

Check:

- an action is referenced but undefined, or defined but unreachable;
- availability is broader than the use case;
- an action remains available after success and can repeat;
- descriptions overpromise capability or conflict with eligibility;
- required inputs have no conversation, variable, or literal producer;
- outputs are declared but not captured, or captured but never consumed;
- implementation inputs and outputs disagree with the `.agent` contract;
- a utility action is treated as though it returned action outputs.

Fix:

- Gate availability with trusted state.
- Return typed outputs and bind them to named consumers.
- Align the contract with the real implementation.
- Remove dead actions only after proving they serve no intended use case.

Evaluate availability, invocation, execution, output, and effect separately.
Include negative cases where the action must be absent.

## Outputs and trusted decisions

Check:

- raw JSON or display text controls authorization, eligibility, routing, or
  success;
- the model is asked to parse a value that should be typed;
- a “checked” flag becomes true before every downstream value is stored;
- stale structured values survive a new raw result;
- the prompt assumes stored state is visible without explicit injection;
- a `|` block is assumed to pause deterministic resolution so the model can act
  before the next `set` or condition resolves.

Fix:

- Prefer typed outputs.
- Normalize raw output deterministically before setting completion.
- Request related result fields as one grouped semantic state update when
  possible.
- If model-driven normalization is unavoidable, create an explicit reasoning
  boundary: first produce and store the raw result, then rebuild reasoning from
  that state and store all derived fields plus completion together.
- Treat a guarded self-transition as a last-resort phase boundary when a
  deterministic producer resolves before a required model-selected
  normalization call can occur, and no clearer supported stage or typed result
  is available. Document its entry and exit guards.

Apply this two-phase rule:

```text
1. Resolve deterministic run, set, and if statements and assemble all | text.
2. Send the completed prompt to the model, which may call a tool or respond.
```

Evaluate:

- Test true, false, malformed, missing, and stale-result cases.
- Confirm the branch reads the current result, not a default.
- Inspect the effective prompt before and after the reasoning boundary.

## State and lifecycle

Check:

- state merely remembers dialogue that remains available in conversation
  history and has no runtime consumer;
- `current_step`, `question_asked`, or similar variables imitate a workflow
  engine without deterministic consumers;
- several booleans and a phase variable encode the same workflow position;
- reachable combinations of state have no coherent meaning;
- completion means attempted or initiated rather than effected;
- request-scoped state leaks into a later request;
- reset, retry, correction, cancellation, logout, or expiry semantics are
  missing;
- `before_reasoning` unconditionally erases a legitimate prior-turn value;
- `after_reasoning` overwrites or advances state despite failure.

Fix:

- Remove state only when its control benefit does not justify its flexibility
  and lifecycle cost.
- Prefer one explicit phase value over several overlapping asking/answered
  latches when deterministic sequencing is truly required.
- Name state after the evidence it represents.
- Give every mutable variable a producer, consumer, and lifecycle
  proportionate to how long it lives and what it controls.

Select the second-request, retry, cancellation, correction, and expiry paths
that can affect the changed state before it stops mattering. Assert state
transitions, not just response wording.

## Turn sequencing

Check:

- prompt text asks the model to call an action, while later deterministic
  conditions assume that action has already run;
- one prompt asks a question and consumes the future answer immediately;
- several model-selected tools are required in an exact order;
- the model can return text instead of invoking a required action;
- post-action and first-entry instructions can resolve together because their
  predicates are not mutually exclusive and no control boundary separates
  them.

Fix:

- Give each branch one next outcome.
- Bind current-turn inputs directly to the real action when persistence is not
  required.
- Use deterministic chaining, an explicit reasoning boundary, or one
  purpose-built action that owns the sequence when order protects correctness.
- Do not describe `@utils.setVariables` as turn-ending or as guaranteeing
  another reasoning iteration. It is a model-selected state-update tool whose
  call updates state but does not itself define a turn boundary. The risk is
  assuming that prompt text has already caused the call before the prompt is
  sent.

Evaluate the actual multi-turn sequence and inspect each reasoning iteration.

## Transitions and message continuity

Check:

- the target subagent reprocesses the message that completed the source flow;
- transition state is incomplete for the target's arrival path;
- both source and target respond or perform the same work;
- a flow cannot return or exit when supported use cases require it;
- a generic “stay” rule traps genuine topic switches.

Fix:

- Define one owner for the arrival turn.
- Pass explicit state only when the target needs it.
- Make continuation and exit predicates reflect real use cases, not exhaustive
  phrase lists.

Evaluate the entry, continuation, cancellation, pivot, and return cases that
the supported use cases can reach.

## Authority and side effects

Check:

- a consequential action is gated by model-inferred or user-claimed authority;
- confirmation exists only in prose;
- two actions both appear to perform the same external effect;
- idempotency is absent for repeatable writes, transfers, messages, or charges;
- completion is set before a typed success result;
- simulated execution is treated as proof of a live effect.

Fix:

- Gate on trusted authorization and confirmation evidence.
- Choose one side-effect owner.
- Use idempotency keys or returned identifiers where supported.
- Claim only the strongest effect the runtime can verify.

Evaluate unauthorized, unconfirmed, duplicate, failure, timeout, and retry
cases. Verify the external record only when live execution is authorized.
