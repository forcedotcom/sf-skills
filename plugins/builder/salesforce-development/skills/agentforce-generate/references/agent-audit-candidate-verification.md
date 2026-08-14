# AgentScript Audit Candidate Verification

Continue here after freezing the comparison, recording the baseline, and
applying one coherent repair.

## Contents

- [Validate the candidate](#5-validate-the-candidate)
- [Inspect more than the final text](#6-inspect-more-than-the-final-text)
- [Evaluate reasoning boundaries](#7-evaluate-reasoning-boundaries)
- [Decide whether to keep the repair](#8-decide-whether-to-keep-the-repair)
- [Handle regressions](#9-handle-regressions)
- [Report limitations](#10-report-limitations)

## 5. Validate the candidate

Run in this order:

1. repository checks;
2. `sf agent validate authoring-bundle --json`;
3. the new regression case;
4. affected existing cases;
5. representative unaffected canaries;
6. the complete frozen matrix before final acceptance.

Use the same model, runtime, action mode, evaluator, and test data as baseline.

## 6. Inspect more than the final text

A response can look correct while the agent used the wrong mechanism. Evaluate:

```text
configured
-> available
-> invoked
-> executed
-> returned
-> stored
-> transitioned
-> effected
```

Examples:

- “I transferred you” does not prove `@utils.escalate` executed.
- A tool invocation does not prove its external write succeeded.
- A raw JSON result does not prove derived boolean state was stored.
- A `checked=True` flag does not prove every branch input is usable.
- A self-transition can prove a new reasoning iteration began, but not that the
  eventual external action effected its target.

## 7. Evaluate reasoning boundaries

When a repair introduces a reasoning boundary, inspect both sides.

Before the boundary:

- the producer runs once;
- the raw result is stored;
- completion remains false;
- no downstream branch reads default derived fields;
- the transition or stage exit is guarded against repetition.

After the boundary:

- the effective prompt is rebuilt from the stored result;
- only result-processing guidance is active;
- the model-visible raw value is explicitly injected when needed;
- one grouped state-update action requests all related fields and completion;
- success or failure actions are unavailable until the grouped update has
  produced the state required by their gates.

A grouped state-update call expresses one semantic state change. Keep
downstream actions unavailable until their complete required state is present;
the grouping does not make model parsing deterministic.

For a guarded self-transition, add regression cases for:

- successful re-entry;
- failed or malformed result;
- no infinite loop;
- second independent request after reset;
- stale prior result not reused.

Treat the self-transition as an explicit phase boundary, not as evidence that
looping is generally desirable.

## 8. Decide whether to keep the repair

Keep the change only when:

- the target case improves;
- no critical or high-severity case regresses;
- relevant compile diagnostics are no worse;
- unaffected canaries are no worse;
- no new unauthorized action becomes available;
- no simulated result is presented as proof of a live effect;
- the candidate stays within the selected intervention level;
- every material removal in Structural or Rewrite work is preserved elsewhere
  or recorded as an accepted behavior change.

If results vary, run repeated trials with the same setup and report the
distribution. Do not hide variance in an average.

## 9. Handle regressions

When a candidate regresses:

1. identify the smallest repair group responsible;
2. narrow or revert that group;
3. keep the evaluator frozen;
4. rerun structural checks;
5. rerun the affected case and all previously passing regression cases.

Do not:

- weaken an expected outcome after seeing the candidate fail;
- delete a failing case without showing it is outside the contract;
- change from live to simulated actions to obtain a pass;
- combine unrelated cleanup with a behavioral repair;
- declare improvement from aggregate score while a critical case regresses.

Stop and report a blocker when evaluation requires unavailable org access,
missing action implementations, production-only side effects, or a material
product-policy decision.

For a large agent, use bounded repair batches:

```text
indexed first pass
-> ranked ledger checkpoint
-> select highest-impact supported cause group
-> one small, coherent cause group
-> full compiler check
-> affected regression cases
-> unaffected canary cases
-> keep, narrow, or revert
-> update the durable report
-> next ranked group
-> final cross-node check and frozen-matrix regression
```

## 10. Report limitations

State explicitly:

- artifact revisions compared;
- explicit versus inferred cases;
- compiler and Salesforce CLI version;
- simulated versus live cases;
- whether external effects were independently verified;
- branches that could not be executed;
- runtime, model, test-data, or evaluator differences;
- assessed intervention levels, recommendation, user choice, and whether the
  candidate remained within that scope.

Use “not evaluated” instead of “passed” when evidence is unavailable.
Compilation alone supports “compiles” or “candidate for review.” Use “safe,”
“behavior-preserving,” “ready to ship,” or equivalent language only when the
relevant behavior has been evaluated; otherwise state what remains untested.
