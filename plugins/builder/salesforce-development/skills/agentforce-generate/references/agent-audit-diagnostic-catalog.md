# AgentScript Diagnostic Catalog

Use this catalog after reconstructing the agent's use cases. A pattern is a
finding only when it has a source location, reachable consequence, affected
use case, minimal fix, and verification method.

This catalog is a lookup index, not a required cover-to-cover review. Start
with the artifact and its use cases, consult only categories that can confirm
or reject a named observation, and return to the audit ledger after each
relevant section.

## Contents

- [Post-diagnosis intervention levels](#post-diagnosis-intervention-levels)
- [Control posture and tradeoffs](#control-posture-and-tradeoffs)
- [Claim calibration](#claim-calibration)
- [Focused diagnostic references](#focused-diagnostic-references)

## Post-diagnosis intervention levels

Assess all three levels after ranking findings. Mark each level **warranted** or
**not warranted** from evidence, then recommend the smallest level that can
resolve the accepted findings.

### Surface

Use for local bugs, typos with runtime impact, simple best-practice violations,
and one-line or similarly bounded fixes. It may correct a predicate, action
description, variable reference, indentation error, reset, or isolated prompt
instruction without reorganizing the flow or changing its architecture.

Choose Surface when the intended structure and contracts remain sound. State
which deeper problems, if any, it intentionally leaves unresolved.

Surface is not schema completion or style normalization. Preserve valid
optional metadata and semantically equivalent control-flow shapes. Absence
from an abbreviated reference list or example does not establish that an
existing field is unsupported; use the selected compiler, target validator,
or concrete runtime evidence. Likewise, do not add a missing field without a
diagnostic and evidence for the correct value; a guessed value can change
deployment semantics even when it compiles.

### Structural

Use for limited reorganization or basic structure changes when local edits
cannot make sequencing, ownership, routing, or lifecycle behavior reliable. It
may reorder or regroup existing logic, clarify a phase boundary, consolidate
duplicated rules, or make a bounded state lifecycle explicit.

Classify by behavioral coupling, not line count. Several individually small
edits are Structural when they must change multiple producers, consumers, and
reset paths that jointly encode one phase. In particular, when overlapping
flags and a stage value describe the same lifecycle, local patches that leave
contradictory combinations or unclear ownership do not make the design
reliable. Consolidating that lifecycle is a Structural change. A single
missing producer, gate, or reset can still be Surface when the surrounding
state model remains coherent.

Do not choose Surface merely because it fixes the highest-severity symptoms.
If an accepted shared root cause still creates competing duties on the repaired
happy path, Surface is an incomplete stabilization, not the smallest sufficient
final repair. Recommend Structural and present Surface only as that bounded
stopgap.

Structural work preserves the agent's objectives and overall architecture. It
costs more regression testing because several paths or prompt-resolution
boundaries may change.

For a cross-turn lifecycle reorganization, verify normal continuation,
correction before commitment, cancellation or intent change, and reset or a
second independent request. These cases test the state ownership; they do not
justify adding persistent state when the flow does not otherwise need it.

### Rewrite

Use for a total redesign only when evidence shows the existing architecture
cannot safely or maintainably satisfy the intended use cases. It may replace
routing, state, subagent boundaries, or action contracts and therefore requires
a complete frozen-matrix regression and contract review.

Do not recommend Rewrite merely because the file is large or unfamiliar.
Explain why Surface and Structural changes are insufficient and identify the
behavioral and migration risks.

### Choice and scope control

For each level, report:

- findings and use cases it resolves;
- findings it leaves unresolved;
- expected diff and architecture scope;
- regression risk and evaluation burden;
- compatibility or migration tradeoffs.

Recommend one level, but let the user choose. A general request to fix findings
defaults to Surface. Obtain explicit user choice before Structural or Rewrite,
unless the user already selected that level in the request. Do not mix levels
silently; if the chosen level is insufficient, stop and request a broader
choice.

## Control posture and tradeoffs

Judge each flow on a spectrum from prompt-led to mixed to scripted. Do not
award determinism merely for being deterministic, and do not flag a staged
flow merely for having stages.

More runtime control improves ordering, repeatability, auditability, and
protection of consequential effects. It also adds state, lifecycle cases,
maintenance, and rigidity when the user corrects themselves, digresses, or
changes intent. More model latitude provides natural interpretation and
recovery, but exact action choice and ordering remain probabilistic.

For each disputed decision, record:

- the observable cost if the model makes the wrong or reordered choice;
- the conversational flexibility lost by locking the choice;
- whether a mixed design can let the model interpret intent while runtime
  gates only the consequence;
- evidence from requirements, evaluations, or traces that justifies changing
  the current posture.

Recommend more control only when its reliability benefit exceeds its
flexibility and lifecycle cost. Recommend less control only when doing so
preserves the required invariants. A stage that spans turns needs the recovery
paths relevant to its use cases; a short-lived guard does not automatically
need correction, cancellation, retry, and expiry machinery.

## Claim calibration

Classify the basis of each finding before choosing its wording:

| Basis | What it supports |
|---|---|
| Compiler or language contract | A statement scoped to the validated language/version |
| Runtime source and tests | A statement scoped to the inspected runtime/version |
| Repeated trace or evaluation evidence | An empirical reliability claim for the tested configuration |
| Single trace | What happened in that session, not a universal causal rule |
| Design analysis | A recommendation with explicit tradeoffs |
| No direct evidence | A hypothesis to verify, not a finding |

Search categorical terms such as `always`, `never`, `every`, `cannot`,
`guarantees`, `ends the turn`, and `must` in the draft report and proposed
guidance. Keep them only when the cited contract or invariant is equally
categorical. State uncertainty and version scope where relevant.

Do not infer causation from sequence alone. For example, a response after a
state update does not prove the state update ended the turn, and a workaround
that improved one trace does not prove why it worked.

## Focused diagnostic references

Load only the category needed for a supported finding:

- [Instruction and Routing Diagnostics](agent-audit-diagnostics-instructions-routing.md) — language validity, instruction resolution, variable visibility, prompt pseudo-code, user-facing behavior, routing, and HyperClassifier fit.
- [Action and State Diagnostics](agent-audit-diagnostics-actions-state.md) — action surfaces, output contracts, state lifecycle, turn sequencing, transitions, authority, and side effects.
- [Architecture and Evaluation Diagnostics](agent-audit-diagnostics-architecture-evaluation.md) — architecture density, evaluation integrity, and non-findings that should not trigger edits.
