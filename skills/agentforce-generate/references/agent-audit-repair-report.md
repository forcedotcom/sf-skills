# AgentScript Audit Repair and Report

Continue here after the scope and reachable-path review is complete.

## Contents

- [Select the Intervention Level](#4-select-the-intervention-level)
- [Capture the Baseline](#5-capture-the-baseline)
- [Apply the Selected Repairs](#6-apply-the-selected-repairs)
- [Evaluate and Iterate](#7-evaluate-and-iterate)
- [Report the Result](#8-report-the-result)

## Workflow (continued)

### 4. Select the Intervention Level

Assess Surface, Structural, and Rewrite against the ranked findings using the
criteria in the Diagnostic Catalog. For each level, state whether it is
warranted, what it would change, which findings it would leave unresolved, and
its regression and evaluation cost.

Recommend the smallest level that can resolve the accepted findings. Record an
explicit user choice before Structural or Rewrite changes. A general request
to fix the agent authorizes Surface repairs only; stop and ask before crossing
that boundary. If a selected level proves insufficient, report why and request
a new choice instead of expanding the scope silently.

"Smallest sufficient" means the smallest level that resolves every accepted
finding affecting an intended use case, including a shared root cause. Do not
recommend Surface as the final repair when it only makes a path reachable but
leaves overlapping state that still assembles competing duties on that path.
In that situation, recommend Structural; Surface may be offered only as an
explicitly incomplete stabilization option.

Do not classify a repair from the number of edited lines alone. If reliable
sequencing requires coordinated changes across several phase variables,
producers, consumers, and reset paths, treat the coupled state ownership as a
Structural problem even when each individual edit looks small. Keep Surface
for isolated wiring defects whose surrounding lifecycle remains coherent.

When the proposed Structural change reorganizes a cross-turn lifecycle, name
the regression cases that prove the new ownership works: normal continuation,
correction before commitment, cancellation or intent change, and reset or a
second independent request. Include only boundaries material to the flow; do
not add state or ceremony solely to satisfy this list.

### 5. Capture the Baseline

- Run available project checks and Salesforce CLI validation before editing.
- Run the use-case matrix against the unchanged agent when a safe execution
  surface is available.
- Use a fresh session for each independent case. Keep one session only for the
  turns of a deliberate multi-turn case.
- Use simulated actions only for routing, instruction, and action-selection
  checks. Do not use simulation to claim output-dependent branches or external
  effects work.
- Run live actions only with explicit user approval, a confirmed
  non-production environment, and safe test data.
- If runtime testing is unavailable, record a static baseline and state the
  limitation. Do not invent a score.

Preserve baseline results separately from candidate results.

### 6. Apply the Selected Repairs

Fix one coherent cause group at a time:

1. syntax, structural, and unsupported-language failures;
2. authorization, safety, and duplicate-side-effect failures;
3. dead, overlapping, or incorrectly gated paths;
4. output, state, lifecycle, and continuation failures;
5. unnecessary complexity with a demonstrated failure mode.

For each group:

- remain within the selected intervention level;
- change the narrowest runtime construct that owns the problem;
- preserve valid optional metadata and unrelated bytes in bounded repairs;
- do not normalize equivalent control flow merely because another form is
  preferred for newly authored code;
- use `available when`, typed outputs, deterministic assignments, an explicit
  reasoning boundary, or a purpose-built implementation that owns the complete
  sequence when prose cannot enforce the invariant;
- keep semantic intent tests in model instructions, and move exact comparisons
  over trusted runtime values into AgentScript control when their consequences
  require stable enforcement;
- interpolate a runtime value only when the model must read that value; do not
  rewrite literal parameter names or author documentation mechanically;
- remove state with no named runtime or later exact-output consumer and no
  evidence-preservation need beyond the usable history window;
- set completion only from the strongest result the runtime can prove;
- keep logic changes separate from broad formatting cleanup;
- for Structural or Rewrite work, record where each removed subagent,
  route, experience-specific branch, action, default, and user-visible
  response went—or identify the accepted behavior change;
- preserve unrelated behavior and wording.

If the user requested diagnosis only, stop before editing and provide the
repair and evaluation plan.

### 7. Evaluate and Iterate

After each coherent repair group:

1. rerun project checks and Salesforce CLI validation;
2. replay the same baseline use cases with the same evaluator;
3. run the new regression case that exposes the repaired defect;
4. inspect effective instructions, action availability, invocation, outputs,
   state changes, transitions, and effects—not only final response text;
5. compare baseline and candidate for the selected unaffected canary cases;
6. verify every material removal in Structural or Rewrite work is preserved
   elsewhere or recorded as an accepted behavior change;
7. keep the change only when the target case improves and unrelated cases are
   no worse.

If a candidate regresses, narrow or revert that repair and repeat. Do not
change the evaluator to make the candidate pass.

### 8. Report the Result

Update the report throughout the audit rather than creating it only at the end.
Return the final checkpoint with the most consequential supported information
first:

1. **Health summary:** what is broken, risky, or sound.
2. **Use-case matrix:** explicit versus inferred cases and expected outcomes.
3. **Findings:** severity, location, evidence, affected cases, and disposition.
4. **Intervention:** assessment of all three levels, recommendation, user
   choice, and selected scope.
5. **Changes:** the minimal repair made for each accepted finding.
6. **Baseline versus candidate:** same cases, same evaluator, exact results.
7. **Validation:** local compiler provider and version or source commit—or
   **compiler not used** with cause—plus target-org CLI, preview/test mode,
   action mode, and limits.
8. **Remaining risks:** only evidence-backed unresolved items.

If work stops early because of missing evidence, access, approval, or an
unresolved safety-critical contract, still return the current ranked ledger,
completed checks, completed changes if any, and the exact next decision needed.
Never substitute continued research for a deliverable blocker report.

State “no actionable finding” when that is the evidence. An audit is not
required to prescribe a change.
