# Patterns by Requirement

Use this guide to choose patterns based on product requirements, not topology labels.

Default shape:

- One `start_agent <domain>:` execution block and zero `subagent` blocks unless
  a boundary changes objective, instructions, actions, authority, or escalation
  behavior and cannot remain coherent in the current scope
- Router-first architecture only when multiple genuine domains require
  current-intent classification
- Subagent-specific posture (scripted, mixed, agentic)
- Deterministic controls only where justified

Read this file first when deciding architecture and flow patterns. Then use:

- `references/architecture-patterns.md` for architecture mechanics and migration guidance
- `assets/patterns/` for concrete pattern snippets

## Quick Selection Table

| Requirement / Scenario | Recommended Pattern | Why | Reference Assets |
|---|---|---|---|
| Multiple genuine domains need different instructions, actions, authority, or escalation | Router-first architecture | Separates incompatible domain scopes and classifies current intent | `references/architecture-patterns.md`, `assets/agents/router-first.agent`, `assets/agents/template-multi-subagent.agent` |
| Identity/trust gate before protected operations | Verification gate | Enforces trusted action output before sensitive actions; does not require a generic focus lock | `references/architecture-patterns.md` |
| Need deterministic follow-up after action | Action callbacks (`run`) | Guarantees ordered post-action execution | `assets/patterns/action-callbacks.agent` |
| Need deterministic setup/cleanup around a turn | Lifecycle events | Runs once before and once after the turn's reasoning loop | `assets/patterns/lifecycle-events.agent` |
| Need specialist consultation and return | Bidirectional routing/delegation | Keeps workflow continuity across subagents | `assets/patterns/bidirectional-routing.agent`, `assets/patterns/delegation-routing.agent` |
| Complex action input strategy required | Advanced input bindings | Mixes slot filling, variable binding, output chaining | `assets/patterns/advanced-input-bindings.agent`, `assets/patterns/critical-input-collection.agent` |
| Controlled output changes the prompt | Context-aware instruction layering | Resolves a branch from trusted action output or a named invariant | `assets/patterns/system-instruction-overrides.agent`, `assets/patterns/procedural-instructions.agent` |
| External process requires ordered successful actions | Outcome-driven gates | Makes the next action available only after the prior external action succeeds | `references/architecture-patterns.md`, `assets/patterns/multi-step-workflow.agent` |
| Prefer LLM-led flexibility with minimal pinning | LLM-controlled actions | Keeps implementation agentic by default | `assets/patterns/llm-controlled-actions.agent` |
| Prompt-template-backed action usage | Prompt template action pattern | Standardized prompt action wiring | `assets/patterns/prompt-template-action.agent` |

## Decision Rules

1. **Choose posture first (per subagent).**
   - Start agentic.
   - Move scripted only when required by regulation, authorization, confirmed
     consequence, external ordering, or observed failure.
   - See `references/posture-and-determinism.md`.

2. **Choose architecture second.**
   - Start with one domain `start_agent` and zero `subagent` blocks.
   - Never add a router that only transitions to that one domain.
   - Add a router only for multiple genuine domains.
   - Add verification gates for protected operations.
   - Add workflow-local sequencing only for externally ordered outcomes.

3. **Choose implementation patterns third.**
   - Add lifecycle/callback/input-binding patterns to solve concrete behavior gaps.
   - Prefer the smallest pattern that satisfies the requirement.

## Common Compositions

### Multi-Domain Protected Service

- Router-first architecture
- Verification gate for protected actions
- Input pinning only for trusted values consumed by protected actions

### Regulated Flow

- One subagent unless the regulated work contains genuine additional domains
- Verification gate
- Scripted controls only for regulated decisions
- Action callbacks for deterministic post-action chain

### Open-Ended Assistant

- One agentic subagent unless genuine domain boundaries require more
- Minimal deterministic controls
- LLM-controlled actions and selective input pinning

## Anti-Patterns

- Modeling the entire agent as linear when only one workflow needs sequencing
- Creating a separate router subagent instead of using `start_agent agent_router`
- Creating greeting, cancellation, completion, off-topic, or ambiguity
  subagents when one existing scope can handle those branches coherently
- Routing every turn back to router by default instead of using direct subagent transitions when workflow intent is clear
- Overusing deterministic controls without requirement or observed failure
- Pinning all action inputs by default instead of using `...` where safe
- Persisting names, preferences, questions asked, or dialogue stages that
  surviving conversation history already contains
- Adding a variable without a trusted writer, named consumer, and lifecycle
