# The Zen of AgentScript

These are enforceable, unordered authoring rules shipped with the skill. Each rule includes a test
that can fail. No rule takes precedence over another; a valid design satisfies
all applicable rules at the same time.

## Give each reachable branch one next outcome

For every branch, choose exactly one primary outcome:

```text
answer | ask | invoke an action | transition | refuse | escalate
```

The model may explain an outcome, but it must not receive two incompatible
duties.

Pass:

- A router transitions without answering the underlying request.
- A request handler answers or invokes its domain action.
- A verification gate asks for missing proof or transitions after proof.

Fail:

- Global instructions say “always answer,” while a router branch says “do not
  answer; transition.”
- A branch both escalates permanently and promises to continue the task.

## Declare no mutable variable without a named consumer

Before adding a variable, identify at least one concrete consumer:

```text
if | available when | transition | action input | later-turn exact output
```

The variable must also represent one of:

- trusted action output;
- authorization, eligibility, or confirmation proof;
- an exact value required by later deterministic logic; or
- a value explicitly required beyond the conversation-history window.

Otherwise, leave the information in conversation history.

Pass:

```agentscript
authenticated: mutable boolean = False

lookup_profile: @actions.get_profile
    available when @variables.authenticated == True
```

Fail:

```agentscript
has_greeted: mutable boolean = False
question_asked: mutable boolean = False
conversation_stage: mutable string = "collecting"
```

## Add deterministic control only for a named cause

Every `if`, `available when`, automatic `run`, or forced transition must cite
one cause in the design:

```text
regulation | authorization | irreversible consequence |
external ordering | observed trace failure
```

If the decision depends on unstructured current intent and none of those causes
applies, leave the decision to model reasoning.

Pass:

- Hide a refund action until the exact amount and explicit confirmation are
  recorded.
- Prevent step 2 until step 1’s external action returns `success=True`.

Fail:

- Add a `current_step` counter because a conversation happens to have several
  questions.
- Force every follow-up back into an old subagent without a reproduced routing
  defect.

## Create a subagent only when the boundary changes behavior

A subagent boundary must change at least one of:

```text
objective | instructions | available actions | authority | escalation behavior
```

The difference must also be large enough that the two behaviors cannot remain
coherent in one scope. A greeting, cancellation acknowledgment, completion
message, ambiguity question, or ordinary dialogue step is a branch by default,
not a separate subagent.

For a focused single-domain agent, the concrete default is:

```agentscript
start_agent event_search:
    reasoning:
        actions:
            search: @actions.search_events
```

That means one execution block and zero `subagent` blocks—not an
`agent_router` that only transitions to `event_search`.

Pass:

- Separate public FAQ actions from authenticated account actions.
- Separate permanent human escalation from a returning specialist
  consultation.

Fail:

- Create `greeting`, `collect_name`, `collect_email`, and `present_results`
  subagents solely to represent dialogue stages.
- Wrap one read-only event search in a router and a cancellation subagent when
  the single search scope can cancel without invoking its action.

## Make model-visible instructions concrete and self-contained

Write what the model must do now. Do not tell it to inspect AgentScript
constructs such as the active subagent, `@variables`, lifecycle hooks, or “the
reasoning instructions.”

For every branch, concatenate the effective system text and resolved reasoning
text. The result must still prescribe one compatible outcome from the
branch-outcome rule.

Pass:

```text
Ask for the minimum information needed to verify identity. Do not use
account-changing actions.
```

Fail:

```text
Inspect the current subagent and variables, then follow the response duty in
the reasoning instructions.
```

## Use slot filling unless the value is controlled

Bind an action input with `...` when the model can safely extract it from the
current turn and surviving history.

Use `@variables.x` only when the value is trusted, canonicalized, needed by
deterministic logic, or must be reused after its action-output scope ends. Use a
literal only for an actual constant.

Action descriptions need:

1. the action’s outcome;
2. when to choose it over its closest alternative; and
3. any material consequence.

They do not need to script the surrounding conversation.

Pass:

```agentscript
find_events: @actions.search_events
    with interest=...
```

Fail:

- End one turn with `setVariables` just to copy “jazz” from history, then call
  the search action on the next turn.
- Pin a user-correctable value from stale state when `...` would use the latest
  turn.

## Bind consequential actions to machine-checkable preconditions

For an action that changes money, access, records, commitments, or external
state:

1. bind the exact target and material parameters;
2. make required authorization and confirmation machine-checkable;
3. keep the action unavailable until those checks pass;
4. record the action result or idempotency key when repeat execution would
   cause harm; and
5. do not advance workflow state when the action fails.

Pass:

```agentscript
issue_refund: @actions.refund
    with order_id=@variables.verified_order_id
    with amount=@variables.confirmed_amount
    available when @variables.customer_verified == True
    available when @variables.refund_confirmed == True
    available when @variables.refund_id == ""
    set @variables.refund_id = @outputs.refund_id
```

Fail:

- A prose instruction says “only refund after confirmation,” but the action is
  always available.
- `current_step` advances after `@outputs.success == False`.

## Treat action execution—not model text—as evidence

The agent may claim an external fact or completed action only when the trace
contains the corresponding successful action result.

Use direct `@outputs` chaining inside the same action scope. Persist only the
fields a later deterministic consumer needs. If later logic needs only
complete-versus-incomplete, persist a trusted boolean outcome rather than a
display-only external identifier. Persist the identifier itself only when an
exact-ID consumer exists, such as a later action input, idempotency guard, or
required later-turn evidence check.

Pass:

- The response names the returned status from the order lookup.
- A later action receives the canonical ID returned by verification.
- A final verification writes `verified=True` for repeat gating while its
  display-only receipt remains in the action result and conversation history.

Fail:

- The model says “your refund was issued” because the action was visible or it
  intended to call it.
- An empty or failed action result is presented as success.
- A final receipt ID is copied into mutable state even though later logic tests
  only whether completion occurred.

## Give every flag, cache, and latch a complete lifecycle

For each persistent control value, document:

```text
owner | writer | reader | reset | expiry | correction behavior | cancel path
```

Reject the value if any field is missing.

Additional hard rules:

- Keep one source of truth; do not store both `current_step` and equivalent
  completion flags.
- A cache must define when external data is refreshed.
- A focus latch must be justified by a reproduced trace and allow the next user
  turn to cancel or change intent.

Fail:

- `open_gate` bypasses fresh routing and the locked subagent has no exit action.
- `data_loaded=True` suppresses refresh for the rest of the conversation.

## Merge only on conversation behavior, with syntax as a hard precondition

Every candidate must first pass:

```text
parse | lint | reference resolution | compile | emitted-artifact inspection
```

Then compare parent and candidate on multi-turn scenarios:

- natural follow-up;
- correction of an earlier value;
- intent change during a workflow;
- cancellation during verification or confirmation;
- action success, empty result, and failure;
- trusted authorization;
- consequential confirmation;
- exact later-turn action data flow; and
- completion without repeated actions.

Merge only when:

1. the candidate has no new deterministic validation failure;
2. safety, authorization, confirmation, and release boundaries do not regress;
3. protected parent behaviors remain correct; and
4. the candidate improves or ties conversation outcomes without adding
   unjustified state, turns, or tool calls.

Parser success alone is not evidence that the agent behaves well.
