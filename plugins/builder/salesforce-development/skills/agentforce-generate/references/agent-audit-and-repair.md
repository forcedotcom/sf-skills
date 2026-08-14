# Audit and Repair Existing Agents

Repair an existing AgentScript agent without replacing its intended behavior
with generic preferences.

Org-backed validation requires an Agentforce-enabled org and Salesforce CLI.
A bounded static review can proceed without org access, but must not be
reported as compiler or runtime validation.

## Contents

- [Operating Contract](#operating-contract)
- [Surface Preservation Gate](#surface-preservation-gate)
- [Related Skill Boundaries](#related-skill-boundaries)
- [Workflow references](#workflow-references)

## Operating Contract

1. **Use cases define correctness.** A checklist can reveal risk; it cannot
   decide what the agent should do. Reconstruct the agent's intended use cases
   before recommending or making behavioral changes.
2. **Diagnose before editing.** Record the baseline, exact evidence, affected
   use cases, and smallest credible fix first.
3. **Make findings actionable.** Every finding must include a source location,
   runtime consequence, affected use case, proposed change, and verification
   method. Omit unsupported style opinions.
4. **Prefer the smallest repair.** Do not redesign the agent, add subagents,
   add persistent state, or add universal ambiguity, off-topic, or human-help
   behavior unless the use cases require it.
5. **Evaluate the control tradeoff.** Do not mechanically make every condition
   deterministic or leave every condition to the model. More control improves
   ordering and repeatability but costs flexibility, state, and maintenance.
   More model latitude improves interpretation and recovery but makes behavior
   probabilistic. Protect requirements whose failure cost warrants runtime
   control; preserve model judgment where flexibility is valuable. When the
   model needs a runtime value, inject it explicitly.
6. **Choose the intervention level.** After diagnosis, assess Surface,
   Structural, and Rewrite; recommend the smallest sufficient level, explain
   the alternatives and tradeoffs, and obtain user choice before Structural or
   Rewrite work. Never broaden the repair silently.
7. **Compile locally, then validate against the target org.** Run the bundled
   local compiler first. When an authenticated org is available, also use
   `sf agent validate authoring-bundle --json` for target-org language
   validation. Never claim language validity from a regex, a home-grown parser,
   or prompt inspection. Treat diagnostics as evidence, not an optimization
   score. Do not silence a diagnostic by violating documented AgentScript
   syntax, removing intentional initialization, or changing behavior. Treat
   reference lists and examples as guidance rather than exhaustive schemas.
   When references, examples, the selected compiler, and the target validator
   disagree, preserve an accepted existing construct, report the discrepancy,
   and validate against the intended deployment target instead of deleting the
   construct by inference.
8. **Compare like with like.** Run the same use cases and evaluators against
   the unchanged baseline and candidate. Label them explicitly. For Structural
   or Rewrite candidates, account for every material removal of a subagent,
   route, experience-specific branch, action, default, or user-visible
   response before claiming capabilities were preserved.
9. **Distinguish availability, invocation, execution, and effect.** A good
   response or tool name does not prove that an external side effect occurred.
10. **Calibrate every claim.** Distinguish language/compiler contracts,
    runtime-source behavior, observed trace behavior, empirical heuristics, and
    authoring recommendations. Do not turn a single trace, runtime version, or
    preferred design into a universal rule. Use causal or categorical wording
    only when the evidence supports it. Compilation alone supports “compiles”
    or “candidate for review.” Use “safe,” “behavior-preserving,” “ready to
    ship,” or equivalent language only when relevant behavior has also been
    evaluated; otherwise state what remains untested.
11. **Do not release.** This workflow authorizes local edits and proportionate
    validation, not deployment, publication, activation, production execution,
    or live consequential actions.
12. **Deliver useful work before exhaustive work.** Create a durable audit
    ledger or report shell after the initial scan, rank supported findings by
    observable harm, and update the artifact as evidence or repairs land. Do
    not make a complete runtime theory, complete reference review, or complete
    rewrite a prerequisite for the first useful deliverable.
13. **Bound investigation by decisions.** Follow a reference, source path, or
    trace only when it can change a named finding, repair, or verification
    decision. If a primary source and one relevant corroborating source do not
    resolve a non-safety-critical semantic question, record the uncertainty
    and proceed. If the uncertainty blocks a safe repair, deliver the ranked
    findings and blocker instead of continuing an open-ended investigation.
14. **Carry the contract into delegated work.** Give each delegated pass a
    bounded artifact or cause group, priority order, lookup-only references,
    and explicit output path. Require the first checkpoint after its initial
    scan and a useful partial report when blocked. Do not hand a delegate a
    broad mandatory reading list or an all-or-nothing final deliverable.

## Surface Preservation Gate

For a Surface-only request, use the original artifact as the byte-preserving
baseline:

1. List accepted findings before editing. Each must identify the original
   source text, evidence, concrete consequence, and exact intended edit.
2. Do not treat a draft as a generation task. Missing recommended fields,
   optional messages, preferred formatting, or equivalent control-flow forms
   are not repair findings by themselves.
3. Edit the existing bundle in place. Preserve its directory, API name,
   filenames, metadata, and equivalent control-flow form unless an accepted
   finding specifically requires changing one of them. Do not emit a renamed
   candidate bundle for an ordinary repair.
4. Apply only edits on the accepted list. Do not improve tone, complete a
   schema, reorder blocks, or normalize style opportunistically.
5. Diff the candidate against the baseline. Revert every hunk that cannot be
   mapped one-to-one to an accepted finding. If a hunk contains both required
   and unrelated cleanup, narrow it before delivery.
6. Validation is evidence, not permission to widen the repair. Do not change
   block-scalar style, normalize equivalent control flow, or migrate otherwise
   preserved metadata merely so an org validator can run; record the
   validation limit and keep the unrelated bytes unchanged.

This gate does not prevent evidence-backed Surface fixes. It prevents an
authoring preference from silently expanding a bounded repair.

Use [Diagnostic Catalog](agent-audit-diagnostic-catalog.md) as a lookup after
the initial scan; do not preload it. Consult the relevant section of
[Evaluation Loop](agent-audit-evaluation-loop.md) before recording a baseline,
applying a repair, or accepting a candidate; do not preload sections for later
steps.

## Related Skill Boundaries

- Use the parent skill's create or modify task domain for a new agent or one
  already-specified edit.
- Use `agentforce-observe` when production session or trace evidence is the
  primary input.
- Use `agentforce-test` when the task is only to author or run a predefined
  functional or security test suite.

## Workflow references

Read both workflow references in order for a full audit or repair:

1. [Audit Scope and Path Review](agent-audit-scope-path-review.md) — establish scope, scale large audits, reconstruct use cases, and inspect reachable paths.
2. [Audit Repair and Report](agent-audit-repair-report.md) — select the intervention level, preserve a baseline, repair, evaluate, and report.
