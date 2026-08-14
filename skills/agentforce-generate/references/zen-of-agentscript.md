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
- A branch both escalates and promises that the current agent will continue
  the task.

## Do not let prompt layout impersonate control flow

Inside `|` text, indentation, numbered steps, and words such as `Show`, `Ask`,
`Call`, `Set`, or `STOP` are instructions for the model. They do not create
runtime scope, mutate variables, execute tools, or enforce order.

Actions belong to the reasoning scope. Gate them with `available when` when
they must exist only for a particular machine-known branch. If two operations
must occur in order, use runtime control flow or one purpose-built
implementation that owns the sequence rather than a prose sequence of
model-selected tools.

Pass:

- A failed-validation branch includes self-contained response guidance while
  its success-only action is unavailable.
- A consequential action becomes available only after its typed prerequisite
  output is stored.

Fail:

- “Step 4” assumes the model saw Steps 1–3.
- An action visually indented beneath one prompt branch remains ungated for
  every other branch.
- Prompt text says “set the value, then call the action” as though the setter
  guarantees the next action.

## Declare no mutable variable without a named consumer

Before adding a variable, identify at least one concrete consumer:

```text
if | available when | transition | action input | later-turn exact output
```

Common justified uses include:

- trusted action output;
- authorization, eligibility, or confirmation proof;
- an exact value required by later deterministic logic; or
- a value explicitly required beyond the conversation-history window; or
- a product-owned state value whose producer, consumer, and lifetime are clear.

If no consumer requires stored state, prefer conversation history or a direct
action binding.

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

Every `if`, `available when`, automatic `run`, or forced transition should
protect a named requirement or reproduced failure. Common causes include:

```text
regulation | authorization | product invariant | repeatability requirement |
irreversible consequence | external ordering | observed trace or eval failure
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

A subagent boundary should change at least one of:

```text
objective | instructions | available actions | authority | escalation behavior
```

The difference should be material enough to justify the extra prompt boundary,
tool scope, routing behavior, and lifecycle. A greeting, cancellation
acknowledgment, completion message, ambiguity question, or ordinary dialogue
step normally remains a branch unless separating it improves a measured
behavior or enforces a real boundary.

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
- Separate turn-ending human escalation from a returning specialist
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

## Reveal every runtime value the model must read

The runtime can evaluate `@variables.X` in predicates, assignments, and action
bindings. The model cannot inspect the variable store directly. Inside `|`
text, use `{!@variables.X}` when that prompt must receive the current stored
value. A value may also be visible when separately preserved in conversation
or tool history, but a bare `@variables.X` token does not reveal it.

Do not interpolate a name merely because it resembles a variable. A literal
instruction such as `Set next_destination to "self_service"` supplies a
parameter value; it does not read the current variable.

Pass:

```agentscript
if @variables.case_summary != "":
    | Summarize this case for the customer: {!@variables.case_summary}
```

Fail:

```agentscript
| Read @variables.case_summary and explain it to the customer.
```

## Give exact facts to runtime and meaning to the model

For each condition, decide who can evaluate it correctly.

- Use AgentScript control for an exact trusted fact whose consequence must not
  vary.
- Use model reasoning for intent, ambiguity, meaning, tone, and other
  situation-aware interpretation.
- In mixed cases, let the model interpret intent while runtime state gates any
  consequential action.

A merge field gives the model a value. It does not make the model's comparison
deterministic.

Pass:

```agentscript
if @variables.account_status == "blocked":
    | Help the customer recover access to the blocked account.

| If the user wants to speak with a human, use
  {!@actions.escalate_to_support}.
```

Fail:

```agentscript
| If {!@variables.account_status} == "blocked", follow the blocked-account
  workflow.
```

Do not convert every sentence containing “if” into state and branches. Make
the ownership choice from the nature and consequence of the decision.

## Match reasoning burden to the deployed model

Each reasoning iteration should have one coherent objective and a number of
classifications, precedence rules, and tool choices that the target model has
demonstrated it can handle.

Pass:

- Target-model evals cover the semantic boundaries in the resolved prompt.
- A smaller model receives a narrower task instead of more overlapping rules.

Fail:

- A stronger model is expected to repair contradictory instructions, missing
  values, or impossible sequencing.
- The target model is unknown, but the design is declared appropriately
  agentic or scripted without evidence.

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

- Add a separate `setVariables` call just to copy “jazz” from history before
  calling the search action.
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

The agent should claim an external fact or completed action only when the
observed action result supports that exact claim. If the action result proves
only that work was requested or accepted, use language such as “submitted” or
“initiated,” not “completed.”

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

For each persistent control value, identify the lifecycle fields that can
affect its intended use:

```text
owner | writer | reader | reset | expiry | correction behavior | cancel path
```

Not every short-lived value needs every field. Require reset, expiry,
correction, or cancellation behavior only when that path can occur before the
value stops mattering. Reject a value when a reachable use case leaves its
meaning stale or ambiguous.

Additional checks:

- Keep one source of truth; do not store both `current_step` and equivalent
  completion flags.
- A cache must define when external data is refreshed.
- A focus latch must be justified by a reproduced trace and allow the next user
  turn to cancel or change intent.

Fail:

- `open_gate` bypasses fresh routing and the locked subagent has no exit action.
- `data_loaded=True` suppresses refresh for the rest of the conversation.

## Merge only on conversation behavior, with syntax as a hard precondition

Every candidate should pass the applicable deterministic checks available for
the artifact:

```text
parse | lint | reference resolution | compile | emitted-artifact inspection
```

Then select the parent-versus-candidate scenarios material to the changed
behavior:

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
