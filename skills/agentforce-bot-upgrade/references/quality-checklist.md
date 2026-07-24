# Quality Checklist

Run this checklist before handing off to `/agentforce-generate`.

## Completeness

- Input mode is explicitly recorded for the run (Mode A org-backed or Mode B offline).
- Agent Spec uses the exact section names/order from `assets/agent-spec-template.md` in `agentforce-generate`.
- Every major bot capability is represented in the Agent Spec.
- Every critical dialog/intent/action is either mapped or listed in `unmapped_items`.
- Fallback and escalation behavior is explicit.

## Fidelity

- Action purpose and I/O are preserved from source metadata where available.
- For Mode B (offline), action signatures are inferred from bot metadata mappings and unresolved signature details are tracked in `open_questions` (non-blocking).
- Dialog-to-subagent and intent-to-subagent mappings are consistent.
- High-risk flows contain clear deterministic guidance.

## Handoff Readiness

- Agent Spec markdown is coherent and structured for implementation.
- Handoff JSON is machine-readable and aligned with markdown.
- Open questions are specific, non-duplicative, and decision-ready.
- Open questions are resolved — one-by-one with the user in interactive mode, or auto-applied from recommended defaults when `--interactive=false` — and each resolution is reflected in both Agent Spec and `extraction-summary.json`.
- Migration appendix is present and includes confidence, gaps, and approval gates.

## Failure Conditions (must fix before handoff)

- Missing action inventory for flows that clearly invoke actions
- Claimed parity while unresolved items are not documented
- Ambiguous routing with no fallback
- Unresolved or ambiguous open questions remain before automatic handoff to `/agentforce-generate`
