# Quality Checklist

Run this checklist before handing off to `/agentforce-generate`.

## Completeness

- Input mode is explicitly recorded for the run (Online org-backed or Offline local metadata).
- Agent Spec uses the exact section names/order from [agent-spec-template.md](../assets/_vendored/agent-spec-template.md) (from the `agentforce-generate` skill).
- Every major bot capability is represented in the Agent Spec.
- Every critical dialog/intent/action is either mapped or listed in `unmapped_items`.
- Fallback and escalation behavior is explicit.
- The Agent Spec includes the default `ambiguous` (unclear requests) and `off_topic` (out-of-scope requests) subagents, each with its own router transition.

## Fidelity

- Action purpose and I/O are preserved from source metadata where available.
- For Offline mode, action signatures come from local Apex/Flow/referenced files when present, falling back to bot metadata mappings when they are not; unresolved signature details are tracked in `open_questions` (non-blocking).
- Dialog-to-subagent and intent-to-subagent mappings are consistent.
- High-risk flows contain clear deterministic guidance.

## Handoff Readiness

- Agent Spec markdown is coherent and structured for implementation.
- Handoff JSON is machine-readable and aligned with markdown.
- Open questions are specific, non-duplicative, and decision-ready.
- Open questions are resolved — one-by-one with the user in interactive mode, or auto-applied from recommended defaults when `--interactive=false` — and each resolution is reflected in both Agent Spec and `extraction-summary.json`.

## Failure Conditions (must fix before handoff)

- Missing action inventory for flows that clearly invoke actions
- Claimed parity while unresolved items are not documented
- Ambiguous routing with no fallback
- Unresolved or ambiguous open questions remain before automatic handoff to `/agentforce-generate`
