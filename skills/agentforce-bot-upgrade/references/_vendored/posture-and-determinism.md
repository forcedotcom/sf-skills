# Authoring Posture: The Control Spectrum

This guide defines how to choose the right posture for each subagent.

Posture is the dial between model latitude (agentic) and authored control
(deterministic). Choose posture first, then choose subagent organization
(router-first architecture, verification gate, and so on).

## Core Principle

Choose the least control that makes unacceptable failures unlikely or
impossible while preserving the flexibility the use case needs. This is a
tradeoff, not a rule that every exact fact must become a branch or that every
conversation should remain prompt-led.

More deterministic control provides stronger ordering, repeatability,
auditability, and protection around consequential actions. It also creates
more state, more lifecycle cases, more maintenance, and less natural recovery
from corrections, digressions, or changed intent.

More model latitude handles meaning, ambiguity, corrections, and conversational
variation more naturally. It also makes exact ordering, action choice, and
repeatability probabilistic.

Mixed control is often the useful middle: let the model interpret the user's
meaning and collect conversational inputs, while runtime predicates gate only
the consequences that need a guarantee.

| Posture | Main benefit | Main cost | Typical fit |
|---|---|---|---|
| Agentic | flexibility and natural recovery | probabilistic ordering and action choice | advice, discovery, low-risk assistance |
| Mixed | flexible interpretation with protected invariants | two owners must have a clear boundary | most action-oriented assistants |
| Scripted | repeatability, traceability, and strict ordering | rigidity, state lifecycle, and maintenance | regulated or externally ordered workflows |

Pin more behavior when the cost of a wrong or reordered decision justifies that
cost: regulation, authorization, confirmed consequential actions, external
ordering, or a reproduced reliability failure. Do not add control merely
because the runtime could express it.

## Primary Controls

Three primitives control posture:

1. `available when`  
   Primary invariant tool. Hide actions when preconditions are false.
2. `with param = ...` vs `with param = value`  
   Default to `...`. Pin values only when sourced from controlled state
   (for example, verified `customer_id`), needed after action-output scope ends,
   or when a reproduced extraction failure requires it.
3. `if` / `else` in `instructions: ->`  
   Use conditional instructions only when a named controlled value changes the
   prompt the model must receive. More branching means more authored control.

Surviving conversation history is the default source for names, preferences,
answers, corrections, and current intent. Add mutable state only for a named
runtime consumer or a value explicitly required beyond the history window.

## Decision Ownership Test

Do not choose posture from the fact that a sentence contains the word “if.”
Classify the decision:

| Decision | Likely owner | Example |
|---|---|---|
| Exact trusted fact with a required stable consequence | AgentScript | `@variables.account_status == "blocked"` |
| Mandatory eligibility or side-effect gate | AgentScript | hide submit until authorization succeeds |
| Model needs a stored value to explain or summarize | Model, with explicit interpolation | `{!@variables.case_summary}` |
| Semantic intent or ambiguity | Model | user wants a human, is changing topics, or is asking hypothetically |

Ask:

1. Does the runtime already know the exact fact?
2. Must the same fact always produce the same branch?
3. Does the branch protect authorization, ordering, or a consequential effect?
4. What happens if the model gets the decision wrong?
5. What flexibility is lost if the branch is locked?
6. Does the decision require interpreting natural language and context?

Runtime knowledge is a signal, not an automatic ownership rule. Use
deterministic control when stable behavior is worth the rigidity. Use model
reasoning when interpretation and recovery are more valuable than exact
repeatability. For mixed cases, let the model interpret intent, then gate the
available consequence with trusted runtime state.

Do not write an exact comparison as model prose:

```agentscript
| If {!@variables.account_status} == "blocked", route to account recovery.
```

Interpolation only reveals the value. It still asks the model to perform and
obey the comparison. If its consequence must be stable, encode it with `if`.

## Match Reasoning Burden to the Target Model

Record the deployed model and configuration when they are known. For each
reasoning iteration, count the distinct classifications, precedence rules,
tool choices, and exact sequences the model must reconcile.

- A stronger model may handle broader semantic judgment with fewer examples.
- A smaller model generally benefits from a narrower objective, clearer
  boundaries, and fewer simultaneous decisions.
- Treat contradictory instructions, missing values, impossible sequencing, and
  invalid state combinations as authoring defects rather than assuming the
  selected model will repair them.

If the target model is unknown, mark posture fit as unassessed. Do not
over-script preemptively for a hypothetical weak model or declare a dense
prompt safe because a hypothetical stronger model might follow it.

## Failure Mode to Avoid

Do not start with step-by-step **prose** directives like:

- `Step 1: invoke X`
- `Step 2: invoke Y`
- `CRITICAL: always invoke Z`

These ask the LLM to follow a fixed procedure via natural language — brittle
and easily ignored.

Deterministic `if/else` conditionals are resolved before the LLM sees the
prompt, but that does not make every branch desirable. Justify each branch by
the value of stable behavior relative to its flexibility and lifecycle cost.
Common reasons include regulation, authorization, confirmed consequences,
external ordering, and reproduced trace failures. Its variable needs a known
writer and consumer.

**Favor runtime conditions when:**
- The branch consumes verified authorization or eligibility
- The branch consumes exact action output or confirmed consequence data
- The branch enforces required external ordering
- A reproduced trace failure requires deterministic resolution

**Favor prompt-led reasoning when:**
- The LLM needs judgment/flexibility (tone, phrasing, edge-case handling)
- The decision depends on unstructured user input the LLM must interpret
- Surviving conversation history already contains the relevant fact
- A rigid branch would make ordinary correction, digression, or intent change
  harder without protecting a meaningful invariant

## Posture Matrix

| Decision | Scripted | Mixed | Agentic |
|---|---|---|---|
| Action ordering | gates on required external outcomes | gates on real invariants | gates on real invariants |
| Action parameters | mostly pinned | mixed pinned + `...` | mostly `...` |
| Instructions | step-by-step with many branches | guidance with targeted branching | high-level intent, minimal branching |

When requirements do not justify a control, start prompt-led and add control
only where the cost of probabilistic behavior warrants it. When requirements
do justify strict sequencing, do not weaken it merely to appear more agentic.

## Scripted Posture

Use when requirements are regulated, audited, or require strict traceability.

Signals in requirements:

- "regulated"
- "compliance"
- "auditable"
- "must trace every step"

Structural expectations:

- `available when` gates on auditable invariants
- Parameters mostly pinned to authored variables
- Detailed branching only where the regulated procedure requires it

## Mixed Posture

Use when some decisions have machine-checkable invariants while the remaining
decisions depend on unstructured current intent or judgment.

Typical shape:

- Gate real invariants only (identity, entitlement, eligibility)
- Pin controlled values (for example `customer_id`), keep other values as `...`
- Use concise guidance, not full scripts

## Agentic Posture

Use for open-ended assistance where the model can safely carry more reasoning.

Typical shape:

- Minimal gating outside trust/security invariants
- Most parameters use `...`
- High-level intent instructions with minimal branching

## Review Checklist

For each subagent:

1. Which posture is selected?
2. Why that posture (regulation, trust gate, or observed failure)?
3. Which invariants are enforced with `available when`?
4. Which parameters are pinned, and what controlled source justifies each pin?
5. For every variable, what named runtime expression or later action consumes it?
6. Does that consumer need the exact stored value, or would a trusted boolean
   outcome preserve the same invariant with less state?
7. Which reset, expiry, correction, or cancellation paths can affect each
   variable before it stops mattering, and are those paths defined?
8. Which instructions can be simplified without losing required control?
9. Which decisions are exact runtime facts, and which require semantic
   interpretation?
10. Is the reasoning burden supported by the deployed target model and evals?
11. For each added control, what failure does it prevent and what
    conversational flexibility does it remove?
12. For each prompt-led decision, is the cost of a wrong or reordered choice
    acceptable?

If a control cannot cite a cause and consumer, question it. Remove it only
after confirming that doing so preserves the required behavior.
