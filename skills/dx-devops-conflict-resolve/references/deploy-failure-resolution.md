# DevOps Center Deploy-Failure Resolution Reference

DevOps Center promotes a work item by **deploying its feature branch** into the target stage branch. That deploy can fail, and the fix depends on *why*. This reference covers the decision tree the `scripts/diagnose-deploy-failure.sh` script implements, the error patterns it recognizes, and the reasoning behind recommending a **full promotion**.

## The two failure classes

| Class | Symptom | Can a re-promote / full promotion fix it? |
|-------|---------|-------------------------------------------|
| **Merge conflict** | Error mentions `MERGE_CONFLICT` or `CONFLICTS:` | **No.** The branches conflict — resolve the conflict first (see `git-conflict-resolution.md`), then re-promote. |
| **Deploy error** | The deploy runs but errors (missing dependency, invalid metadata, test failure, …) | **Sometimes.** A *full* promotion helps only when the deploy failed on a **missing dependency that already exists on the feature branch** but was left out of a partial deployed set. |

## Why a "full promotion" is the lever

DevOps Center can promote a **subset** of a work item's changes. When the deployed subset references a component it did not include (e.g. an Apex class that calls another class not in the set), the deploy fails with a *missing dependency* error. If that referenced component is **already committed on the feature branch**, promoting **everything** (a full promotion) includes it and the deploy succeeds. If the component is **not** on the branch, no promotion can supply it — it must be authored/committed first (or the work item that owns it must be included).

## The decision tree

```text
deploy error
├─ matches MERGE_CONFLICT / CONFLICTS:      → merge conflict; resolve, don't re-promote   (exit 2)
└─ otherwise, parse a missing dependency
   ├─ none parsed                            → generic fix; full promotion won't help      (exit 4)
   └─ dependency <Type> <Name> parsed
      ├─ present on feature branch           → FULL PROMOTION can fix; confirm & promote    (exit 0)
      └─ absent from feature branch          → add/commit the component first, then promote (exit 3)
```

## Recognized error patterns

The parser (mirrors the DevOps Center provider) extracts a metadata **type** and **component name** from these shapes:

| Error shape | Parsed as |
|-------------|-----------|
| `Variable does not exist: Foo` (or `Problem: Variable does not exist: Foo`) | `ApexClass` `Foo` |
| `no ApexClass named Foo found` (also `ApexTrigger`/`ApexPage`/`CustomObject`/`Flow`) | that type + `Foo` |
| `In field: apexClass - no ApexClass named Foo found (profiles/…)` | `ApexClass` `Foo` |
| `... Component: Foo, Type: ApexClass ...` (when not a "Variable does not exist"/"Problem:" line) | that type + `Foo` |

Anything else parses to *no dependency* → generic guidance.

## Branch-presence check

For a parsed `<Type> <Name>`, the script builds candidate source paths for the standard SFDX layout and asks git whether any exist on the branch:

```bash
git show <feature-branch>:force-app/main/default/classes/<Name>.cls        # local ref
git show origin/<feature-branch>:force-app/main/default/classes/<Name>.cls # remote ref fallback
```

Path templates by type:

| Type | Candidate paths (first match wins) |
|------|------------------------------------|
| `ApexClass` | `…/classes/<Name>.cls` (under `force-app/main/default/`, `main/default/`, or `classes/`) |
| `ApexTrigger` | `…/triggers/<Name>.trigger` |
| `ApexPage` | `…/pages/<Name>.page` |
| `Profile` | `…/profiles/<Name>.profile-meta.xml` |
| `CustomObject` | `…/objects/<Name>/<Name>.object-meta.xml` |
| `Flow` | `…/flows/<Name>.flow-meta.xml` |

If a project uses a non-standard package directory (custom `packageDirectories` in `sfdx-project.json`), the standard templates may miss the file and the script reports `dependency_not_in_feature_branch` conservatively — verify manually with `git show <branch>:<actual-path>` before concluding.

## Running the script

```bash
# From the repo clone. Pass an error file, or pipe the deploy output with '-'.
scripts/diagnose-deploy-failure.sh deploy-error.txt feature/WI-101 uat origin
sf project deploy start ... 2>&1 | scripts/diagnose-deploy-failure.sh - feature/WI-101 uat
```

It prints `REASON`, `CAN_FULL_PROMOTION_FIX`, `RECOMMENDATION`, and (when parsed) `MISSING_DEPENDENCY_TYPE` / `MISSING_DEPENDENCY_NAME` / `IN_FEATURE_BRANCH` (+ `IN_TARGET_BRANCH` when a target branch is given). Exit codes: `0` full promotion can fix, `2` merge conflict, `3` dependency absent, `4` unparsed, `1` usage/env error.

## Handing off

This skill diagnoses; it does not promote. When the diagnosis is `dependency_in_feature_branch`, confirm with the user and hand the **full promotion** to `dx-devops-promote`. When a component must be added, author it with the relevant domain skill, commit it to the feature branch, then re-promote. When the diagnosis is a merge conflict, switch to the conflict-resolution track in `git-conflict-resolution.md`.
