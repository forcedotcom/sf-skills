# Authoring Posture: Agentic vs Deterministic

This guide defines how to choose the right posture for each subagent.

Posture is the dial between model latitude (agentic) and authored control
(deterministic). Choose posture first, then choose subagent organization
(router-first architecture, verification gate, and so on).

## Core Principle

Default to the most agentic posture that still meets the requirement.

Pin determinism only with cause:

- Regulated, audited, or legally constrained steps
- Identity, trust, or authorization gates
- Confirmed irreversible or consequential actions
- External ordering backed by successful action outcomes
- A failure mode observed in preview or production traces

Avoid defaulting to scripted instructions because they feel safer. Over-scripted
flows are brittle and expensive to maintain.

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

## Failure Mode to Avoid

Do not start with step-by-step **prose** directives like:

- `Step 1: invoke X`
- `Step 2: invoke Y`
- `CRITICAL: always invoke Z`

These ask the LLM to follow a fixed procedure via natural language — brittle
and easily ignored.

Deterministic `if/else` conditionals are resolved before the LLM sees the
prompt, but that does not make every branch desirable. Each branch must cite a
regulation, authorization boundary, confirmed consequence, external ordering
constraint, or reproduced trace failure. Its variable must have a trusted
writer and a named consumer.

**Use `if/else` when:**
- The branch consumes verified authorization or eligibility
- The branch consumes exact action output or confirmed consequence data
- The branch enforces required external ordering
- A reproduced trace failure requires deterministic resolution

**Use prose instructions when:**
- The LLM needs judgment/flexibility (tone, phrasing, edge-case handling)
- The decision depends on unstructured user input the LLM must interpret
- Surviving conversation history already contains the relevant fact

## Posture Matrix

| Decision | Scripted | Mixed | Agentic |
|---|---|---|---|
| Action ordering | gates on required external outcomes | gates on real invariants | gates on real invariants |
| Action parameters | mostly pinned | mixed pinned + `...` | mostly `...` |
| Instructions | step-by-step with many branches | guidance with targeted branching | high-level intent, minimal branching |

When requirements do not name a deterministic cause, start agentic. Add each
mixed or scripted control only when a specific decision needs one of the causes
listed above.

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
7. What are each variable's reset, expiry, correction, and cancellation semantics?
8. Which instructions can be simplified without losing required control?

If an answer cannot cite a cause and consumer, remove the control or variable.
