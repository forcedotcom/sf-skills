# AgentScript Instruction and Routing Diagnostics

Use these categories only after the audit identifies a relevant instruction,
visibility, response, or routing concern.

## Contents

- [Language and structural validity](#language-and-structural-validity)
- [Instruction resolution](#instruction-resolution)
- [Prompt text that impersonates code](#prompt-text-that-impersonates-code)
- [Behavioral duties versus response copy](#behavioral-duties-versus-response-copy)
- [Routing and reachability](#routing-and-reachability)
- [HyperClassifier router fit](#hyperclassifier-router-fit)

## Language and structural validity

Check:

- unsupported blocks, hooks, utilities, conditional forms, or directives;
- malformed structural indentation or mixed indentation;
- missing required declarations in a complete bundle;
- references to undeclared variables, actions, subagents, or outputs;
- action targets or input/output schemas that disagree with implementations;
- syntax copied from a newer or different AgentScript dialect.

Evidence and fix:

- Prefer `sf agent validate authoring-bundle --json` against the intended
  target org.
- Distinguish a complete bundle from an extracted fragment.
- Use the smallest supported construct.
- Do not patch around a compiler failure with prompt wording.

Evaluate:

- Require zero relevant compile errors.
- Re-run contract discovery when action definitions change.

## Instruction resolution

Check:

- a subagent `system.instructions` value unintentionally replaces global
  identity, safety, or scope instructions;
- a `system.instructions` value attempts to use `instructions: ->` or runtime
  procedure statements instead of declarative prompt text;
- a system merge field is treated as deterministic enforcement rather than a
  current value rendered for the model;
- global and local instructions demand incompatible outcomes;
- model-facing instructions mention runtime-only concepts the model cannot see;
- model-facing instructions name `@variables.X` without interpolating a value
  the model must actually read;
- model-facing instructions compare an interpolated value even though the
  runtime already knows the exact fact and a stable consequence may be clearer
  or safer as a runtime branch;
- a conditional fragment assumes another fragment is present;
- repeated instructions conflict, dilute precedence, or exceed useful context.

Fix:

- Put durable invariants in the effective system instruction for every block
  that needs them.
- Keep system instructions declarative. Move `run`, `set`, runtime `if`, and
  transitions to supported lifecycle or reasoning procedure blocks.
- Remove duplicate or contradictory prose.
- Inject only the concrete values the model must read.

Evaluate:

- Inspect the effective prompt for each affected use case, not only the source.
- Inspect system merge fields on the first iteration and after relevant state
  changes.
- Test one case per instruction-override boundary.

### Variable visibility and decision ownership

Classify each variable-like reference before changing it:

| Source form | Meaning | Correct use |
|---|---|---|
| `if @variables.X == ...` | Runtime expression | Exact machine-known branch |
| `with input = @variables.X` | Runtime binding | Pass a trusted value |
| `| Current value: {!@variables.X}` | Prompt interpolation | Model must read the value |
| `| Set next_destination to "self_service"` | Literal instruction | Model supplies a named parameter; no current value is needed |

A bare `@variables.X` inside `|` text contributes only literal text; that token
does not provide the stored value. The same value may be separately present in
conversation or tool history. Interpolate when the current stored value is the
one the prompt must reliably receive.

Interpolation does not make a branch deterministic. This still delegates an
exact comparison to the model:

```agentscript
| If {!@variables.account_status} == "blocked", do the blocked-account flow.
```

If stable behavior truly depends on that exact trusted value, use a runtime
predicate and give the matching branch one concrete objective. If the
condition depends on semantic intent—such as whether the user is asking for a
human—or the use case benefits more from flexibility than strict
repeatability, leave that judgment in model instructions.

Do not auto-fix every compiler interpolation hint. First decide whether the
text needs the value, merely names a parameter, or should not ask the model to
evaluate the condition at all.

## Prompt text that impersonates code

Check:

- indentation beneath `|` is treated as executable nesting;
- `if {!@variables.X} == ...` inside prompt text is treated as a runtime
  predicate;
- Python-style `elif` is used instead of AgentScript `else if`, or a separate
  `if` is nested inside a conditional body;
- `Show`, `Ask`, `Call`, `Set`, `STOP`, or `Continue` is treated as a runtime
  directive;
- “Step 3” or “continue above” assumes prior prompt fragments survived;
- `MANDATORY` or `DO NOT SKIP` substitutes for gating or sequencing;
- adjacent same-scope prompt lines repeat `|` as though each marker creates a
  step or boundary;
- an action visually placed under one prompt branch remains globally available.

Fix:

- Use runtime constructs for machine-known behavior.
- Use model instructions for intent, ambiguity, meaning, and other
  situation-aware judgments.
- Use explicit predicates or a supported mutually exclusive conditional
  structure for exclusive branches.
- When authoring new alternatives or when first-match priority matters, prefer
  `if / else if / else`. Independent top-level `if` statements are valid when
  multiple branches may run or their predicates are provably mutually
  exclusive. Do not rewrite an equivalent form during a Surface repair without
  a diagnostic or concrete overlap, gap, priority, or use-case consequence.
  Spell the clause `else if`; `elif` is invalid.
- Collapse adjacent same-scope prompt fragments into one `|` block with
  aligned continuation lines. Start a new marker after a runtime statement or
  branch when the structure requires a new fragment.
- Preserve a valid `instructions: ->` block that contains only `|` prompt text
  during a bounded repair. The absence of runtime statements does not make the
  block defective. Changing it to `instructions: |` is cosmetic unless the
  user explicitly requests scalar-style cleanup or runtime evidence shows a
  behavior difference.
- Make each resolved prompt fragment understandable with the other fragments
  that can accompany it in the same reachable state.

Evaluate:

- Inspect both effective instructions and available actions for true and false
  versions of each branch condition.
- For a marker-only cleanup, compile the file and compare the resolved prompt
  text before and after; do not claim a behavioral repair from formatting
  alone.

## Behavioral duties versus response copy

Check:

- ordinary instructions are written as finished dialogue instead of telling
  the model what outcome, content, and constraints the response needs;
- draft copy hides whether a line is a required fact, an example, a tone cue,
  or the complete response duty;
- two candidate replies can resolve into the same prompt even though their
  underlying duties are mutually exclusive;
- exact wording is implied by quotation or prose style but never stated as a
  requirement;
- rigid canned text discards relevant conversation context without a legal,
  compliance, safety, brand, or grounding reason.

Default to behavioral instructions:

```agentscript
if @variables.cart_validation_failed:
    | Explain that one or more cart items are unavailable. Do not offer
      payment. Ask the user to review or remove those items.
else:
    | Tell the user the current cart total is {!@variables.cart_total}. Ask
      whether they want to proceed to payment or cancel.
```

This states what the model must accomplish while leaving ordinary wording
responsive to the conversation. It also exposes the real branch duties for
review.

Use response copy only when the wording itself is part of the requirement. In
that case, make the contract explicit rather than hoping the model infers it:

```agentscript
| Respond with exactly this approved notice, with no additions:
  "This call may be recorded for quality and training purposes."
```

Examples and tone samples are not exact-copy requirements. Label them as
examples and state which properties should carry over.

Fix:

- replace ordinary candidate dialogue with the intended response duty,
  required facts, prohibited claims, and next conversational objective;
- preserve merge fields for exact values the model must receive;
- make mutually exclusive duties exclusive with runtime predicates when they
  depend on trusted machine state;
- retain exact copy only when the use case actually requires it, and say
  `Respond exactly` or equivalent;
- keep useful sample wording as a labeled example rather than an unlabeled
  command.

Evaluate:

- inspect every reachable assembled prompt and name its single current
  response duty;
- vary the preceding conversation and confirm ordinary responses adapt while
  preserving required facts and exclusions;
- for exact-copy cases, assert the literal output and absence of additions;
- do not report stylistic preference alone as a defect: identify the ambiguity,
  conflict, lost context, or unsupported exact-copy requirement it causes.

## Routing and reachability

Check:

- independent conditions can resolve simultaneously;
- no condition handles a reachable state;
- precedence is stated in prose but not represented by predicates;
- a branch depends on an accidental default or a value with no producer;
- a route is unreachable because an earlier transition or reset always wins;
- a broad fallback steals a specific use case;
- routing descriptions disagree with reasoning instructions.

Fix:

- Use mutually exclusive predicates or another supported mutually exclusive
  structure.
- Encode only machine-known precedence deterministically.
- Add a fallback only when intended use cases require one.

Evaluate:

- Test each route positively and negatively.
- Test ambiguous boundary utterances against neighboring routes.

## HyperClassifier router fit

Check:

- `model://sfdc_ai__DefaultEinsteinHyperClassifier` is used on a node that must
  answer, clarify, inspect images, set state, run domain actions, escalate,
  delegate to a connected agent, or use `before_reasoning` or
  `after_reasoning`;
- a HyperClassifier reasoning action is anything other than
  `@utils.transition`;
- route descriptions overlap, omit important exclusions, or disagree with the
  target subagents;
- trusted state should remove an ineligible route but no `available when` guard
  does so;
- the design expects the router itself to respond when classification is
  ambiguous instead of routing to an intended clarification or fallback
  subagent;
- an ordinary-model router is reported as defective merely because it does not
  use HyperClassifier.

Fix:

- Add HyperClassifier only when the node can remain a pure transition selector
  and routing latency is a requirement.
- Move conversation and domain work to the target subagent, or keep an ordinary
  model when those duties belong in the entry node.
- Use `available when` for machine-known eligibility and distinct action
  descriptions for semantic intent.
- Do not create a router or additional subagents solely to use HyperClassifier.

Evaluate:

- Run `sf agent validate authoring-bundle --json` and confirm the router has no
  unsupported actions or lifecycle hooks.
- Preview positive and negative examples for every route, ambiguous boundaries,
  follow-up turns, unavailable-route states, and the intended fallback.
- Inspect traces for the selected transition. Do not infer correct routing from
  plausible response text.
- Treat a compatible ordinary-model router as an optimization opportunity only
  when latency or observed transition reliability justifies the change.
