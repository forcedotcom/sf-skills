# AgentScript Audit and Repair Evaluation Loop

Use this loop to compare an unchanged AgentScript agent with a minimally
repaired candidate. The goal is not to maximize a generic score. The goal is to
improve the affected use cases without weakening the rest.

## Contents

- [Delivery guard](#delivery-guard)
- [Freeze the comparison](#1-freeze-the-comparison)
- [Build the use-case matrix](#2-build-the-use-case-matrix)
- [Capture the baseline](#3-capture-the-baseline)
- [Apply one coherent repair](#4-apply-one-coherent-repair)
- [Continue candidate verification](#continue-candidate-verification)

## Delivery guard

Treat the comparison record as a durable artifact, not an end-of-task summary.
Write the baseline identity and initial use cases as soon as they are known,
then update the same record after each repair batch. Evaluate Critical and High
findings before lower-priority hypotheses. Missing runtime access or unresolved
non-blocking semantics becomes a stated limitation; it does not justify an
open-ended research loop.

## 1. Freeze the comparison

Record:

- baseline and candidate identity. Prefer a revision or digest when two
  different artifacts are compared. For an unchanged local audit, an explicit
  statement that baseline and candidate are the same byte-identical file is
  sufficient; do not manufacture hashes for ceremony;
- target org alias and API name, if used;
- Salesforce CLI version;
- local compiler provider, exact package version or source commit, and entry
  path—or **compiler not used** with the recorded cause;
- model and runtime surface;
- action mode: simulated or live;
- evaluator and expected outcomes;
- use-case IDs and which are explicit versus inferred;
- selected intervention level and the user's choice when Structural or Rewrite
  is selected.

Do not change these after seeing candidate results.

Use labels that make the comparison unambiguous:

```text
baseline = unchanged agent at <revision-or-digest-or-path>
candidate = repaired agent at <revision-or-digest-or-path>
```

When no change is made, write `candidate = baseline; file unchanged` instead of
requiring a digest. “Parent” and “candidate” are meaningful only when the
artifacts being compared are identified clearly enough to reproduce the result.

## 2. Build the use-case matrix

For each case, record:

| Field | Meaning |
|---|---|
| ID | Stable case identifier |
| Source | User requirement, Agent Spec, existing test, or inferred behavior |
| Turns | Full multi-turn sequence |
| Expected owner | Start agent or subagent |
| Expected action | Required invocation, or `none` |
| Forbidden actions | Actions that must not be available or invoked |
| Expected state | Material state changes |
| Expected effect | Observable external result, if any |
| Evaluation mode | Static, simulated, preview live-action, or test suite |

Include positive, negative, retry, continuation, and repeated-request cases only
when material to the supported use cases.

## 3. Capture the baseline

### Structural validation

Run the bundled local compiler first. Then, when a complete bundle and
authenticated target org are available:

```bash
sf config get target-org --json
sf agent validate authoring-bundle --json --api-name <BundleName>
```

Record exact diagnostics. Do not edit first and reconstruct the baseline later.
Treat diagnostics as evidence, not an optimization score. Do not silence a
warning by violating documented syntax, removing intentional initialization,
or changing behavior. When compiler output conflicts with canonical guidance,
preserve the documented behavior and report the discrepancy.

When org validation is unavailable:

- run documented repository checks that already exist;
- record the static limitation;
- do not claim compiler validity.

Do not substitute regex or a home-grown parser for AgentScript validation.

### Behavioral validation

Use preview when safe:

```bash
sf agent preview start --json \
  --authoring-bundle <BundleName> \
  --simulate-actions \
  -o <org-alias>

sf agent preview send --json \
  --session-id <session-id> \
  --utterance "<case turn>" \
  --authoring-bundle <BundleName> \
  -o <org-alias>

sf agent preview end --json \
  --session-id <session-id> \
  --authoring-bundle <BundleName> \
  -o <org-alias>
```

Use `--simulate-actions` to test:

- routing;
- effective instructions;
- action availability;
- model selection;
- response posture.

Simulation does not prove:

- output-dependent branches;
- Apex or Flow behavior;
- external writes;
- transfer, message, charge, or record effects.

Use `--use-live-actions` only with explicit approval, a verified non-production
org, and safe data.

### Preserve evidence

For each case, retain:

```text
input turns
effective instructions
available actions
invoked actions
action outputs
state changes
transitions
final response
external effect verification
```

If the environment cannot provide one layer, mark it unavailable.

## 4. Apply one coherent repair

Repair one coherent cause group at a time, such as:

- one malformed indentation family;
- one premature completion/result-parsing family;
- one action-availability and duplicate-effect family.

Do not mix broad reformatting with behavioral changes.
Do not exceed the selected intervention level. If the evidence shows the
selected level cannot resolve the finding, stop and request a broader choice
before editing further.

Record for each change:

- finding ID;
- exact source location;
- use case repaired;
- invariant enforced;
- expected observable difference.

For Structural or Rewrite candidates, also record every material removed
subagent, route, experience-specific branch, action, default, and user-visible
response. Identify where each capability is preserved or name the accepted
behavior change. Static “unused” analysis alone does not establish that a
reachable capability is safe to remove.

## Continue candidate verification

After applying the coherent repair, continue with
[Audit Candidate Verification](agent-audit-candidate-verification.md) to inspect
the candidate, decide whether to keep it, handle regressions, and report limits.
