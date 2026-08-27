---
name: dx-devops-conflict-resolve
description: "Use this skill to diagnose and resolve what blocks a DevOps Center promotion of a work item's feature branch: Git merge conflicts and deployment failures. DevOps Center is Git-backed, so overlapping metadata changes surface as merge conflicts against the target stage branch, resolved with git (detect, resolve markers, commit, push). Deploy failures often cite a missing dependency a full promotion can fix when the component already exists on the branch. TRIGGER when the user wants to check a work item for conflicts before promoting, resolve merge conflicts or leftover conflict markers in metadata files (.xml, .object-meta.xml, .cls), reconcile a feature branch with its target stage branch, or diagnose why a DevOps Center promotion or deployment failed and whether a full promotion or a missing-dependency fix will resolve it. DO NOT TRIGGER for running the promotion itself (use dx-devops-promote), creating or updating work items (use dx-devops-work-item-manage), or deploying metadata directly to an org."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "58.0"
  relatedSkills:
    - "dx-devops-promote"
    - "dx-devops-work-item-manage"
  cliTools:
    - tool: ["git"]
      semver: ">=2.23"
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "orgPref"
      value: "ALMDevopsCorePref"
    - type: "userPerm"
      value: "UserHasDevOpsCore"
---

# DevOps Center Conflict & Deploy-Failure Resolution

Diagnoses and resolves what blocks a DevOps Center promotion of a work item's feature branch. DevOps Center is Git-backed: each work item is a feature branch and each pipeline stage has a target branch. A promotion can fail two ways — a **Git merge conflict** (two work items changed the same metadata) or a **deployment failure** (the deploy itself errors, often on a **missing dependency**). There is no `sf devops conflict` CLI command; both cases are diagnosed and resolved with standard **git** against the connected repository. This skill runs in a local clone of that repo.

## Scope

- **In scope**: (a) Detect merge conflicts between a work item's feature branch and the target stage branch (non-destructively), resolve conflicted files (choose a side or manually merge conflict markers), commit, and push the feature branch DevOps Center tracks; (b) Diagnose a promotion **deploy failure** — classify it as a merge conflict vs. a deploy error, parse a missing dependency, and determine whether a **full promotion** can fix it (the component exists on the feature branch) or the component must be added first
- **Out of scope**: Running the promotion, full promotion, or combine (use `dx-devops-promote`), creating/updating work items or their status (use `dx-devops-work-item-manage`), deploying metadata directly to an org, pipeline or project setup (separate skills)

---

## Required Inputs

Gather or infer before proceeding:

- **Local clone** of the DevOps Center connected Git repository (the agent runs git commands here). Confirm the working tree is clean before starting.
- **Feature branch name** — the branch backing the work item. If the user gives a work item ID/subject instead, resolve it to its branch (see the Reference File Index for the `sf devops work-item` lookup).
- **Target stage branch name** — the branch of the pipeline stage the work item promotes into (e.g. the integration/UAT branch).
- **Remote name** — defaults to `origin`.
- **Deploy error text** (deploy-failure track only) — the promotion's error output/summary. Needed to classify the failure and parse a missing dependency. Capture it to a file or pipe it into the diagnosis script.

Defaults unless specified:
- Remote: `origin`
- Merge direction: merge the **target stage branch into the feature branch** (reconcile the work item with where it is going)

If the user names both branches ("resolve conflicts on `feature/WI-101` against `uat`"), proceed. If they give a work item, resolve its branch first.

---

## Workflow

DevOps Center promotion blockers are Git-level. Detection and diagnosis are deterministic (scripts); resolving each conflicted file requires judgment (prose). Never resolve without first detecting on a clean tree.

**Route first.** Pick the track from the user's situation:

- **Merge conflict track** — the user wants a pre-promotion conflict check, or a promotion failed and the cause is (or is suspected to be) a merge conflict → Phases 1–4 below.
- **Deploy-failure track** — a promotion's *deploy* failed with an error message and the user wants to know why and how to fix it → Phase D below. If Phase D classifies the failure as a merge conflict, fall through to the merge-conflict track.

### Phase 1 — Authenticate and orient

1. **Confirm the local repo and clean tree.** Run in the repo clone:
   ```bash
   git rev-parse --is-inside-work-tree && git status --porcelain
   ```
   - If `git status --porcelain` prints anything, the tree is dirty — instruct the user to commit or stash first. A trial merge on a dirty tree is unsafe.
2. **Resolve a work item to its branch (only if the user gave a work item, not a branch).** Verify org auth with `sf org display --json`; if it fails, tell the user to run `sf org login web --set-default --alias <alias>`. Then look up the branch — see `references/git-conflict-resolution.md`.

### Phase 2 — Detect (non-destructive)

3. **Run the detection script.** It fetches, trial-merges the target branch into the feature branch without committing, lists conflicted files, and aborts the trial so the tree is left untouched:
   ```bash
   scripts/detect-conflicts.sh <feature-branch> <target-branch> [remote]
   ```
   - Exit `0` = clean merge (no conflicts) → report "safe to promote" and STOP.
   - Exit `2` = conflicts found → the script prints the conflicting file list; proceed to Phase 3.
   - Exit `1` = error (dirty tree, unknown branch, fetch failure) → report the error and STOP; do not treat an error as "no conflicts".

### Phase 3 — Resolve

4. **Start the real merge** to bring conflict markers into the working tree:
   ```bash
   git checkout <feature-branch>
   git merge --no-ff <remote>/<target-branch>
   ```
   List the conflicted files deterministically:
   ```bash
   git diff --name-only --diff-filter=U
   ```
5. **Resolve each conflicted file** — this is the judgment step:
   - When one side is unambiguously correct, take it: `git checkout --ours -- <file>` (keep the feature branch's version) or `git checkout --theirs -- <file>` (take the target branch's version). For DevOps Center, "ours" is the feature branch, "theirs" is the target stage branch.
   - When both sides contain needed changes (divergent edits to the same component), open the file and manually merge — reconcile the `<<<<<<<` / `=======` / `>>>>>>>` regions into a single correct version, preserving both intents. Be especially careful with XML metadata (`.xml`, `.object-meta.xml`, `.field-meta.xml`): keep the file well-formed and do not duplicate elements.
   - Stage each resolved file: `git add <file>`.
6. **Confirm no markers remain** before committing:
   ```bash
   git diff --check
   git diff --name-only --diff-filter=U
   ```
   - `git diff --check` must report nothing, and the unmerged-file list must be empty. If either shows leftovers, keep resolving — do not commit.

### Phase 4 — Finalize and report

7. **Commit and push the resolution** to the tracked feature branch so DevOps Center picks it up:
   ```bash
   git commit --no-edit          # completes the merge with the default merge message
   git push <remote> <feature-branch>
   ```
8. **Report the outcome**:
   - No conflicts: "No merge conflicts between `<feature>` and `<target>`. Safe to promote."
   - Resolved: list the files resolved and how (took a side vs. manual merge), and state that the feature branch was pushed. Then hand off: "Re-validate and promote via `dx-devops-promote`."

### Phase D — Diagnose a deployment failure

Use this track when a promotion's **deploy** failed with an error and the user wants to know why and how to fix it. Diagnosis is deterministic (a script); do not eyeball the error.

D1. **Capture the deploy error text** to a file, or pipe it directly into the diagnosis script.

D2. **Run the diagnosis script** from the repo clone. It classifies the failure, parses any missing dependency, and checks whether that component exists on the feature branch (via `git show`):
   ```bash
   scripts/diagnose-deploy-failure.sh <error-file|-> <feature-branch> [target-branch] [remote]
   # or:  <deploy command> 2>&1 | scripts/diagnose-deploy-failure.sh - <feature-branch> <target-branch>
   ```
   Act on the exit code and the printed `REASON` / `RECOMMENDATION`:
   - Exit `0` (`dependency_in_feature_branch`) → the missing component **exists on the feature branch** but was left out of the deployed set. A **full promotion** should fix it. Report this, confirm with the user, and hand off to `dx-devops-promote` to run a full promotion. This skill does not promote.
   - Exit `2` (`merge_conflict`) → the failure is a merge conflict, not a deploy error. Fall through to the **merge-conflict track** (Phase 1 onward).
   - Exit `3` (`dependency_not_in_feature_branch`) → the missing component is **not** on the feature branch, so promoting cannot supply it. Report that the component must be added and committed to the feature branch (or the owning work item included) before promoting.
   - Exit `4` (`no_dependency_parsed`) → the error is not a recognizable missing dependency. Report the raw error and advise fixing the underlying issue (e.g. test coverage, invalid metadata); a full promotion will not help.
   - Exit `1` → environment/usage error (not in a git repo, unreadable error file) → report and stop.

D3. **Report the diagnosis** with the `REASON`, whether a full promotion can fix it, the missing component (if any) and where it lives, and the concrete next step. Never re-promote blindly — only recommend a full promotion when the diagnosis is `dependency_in_feature_branch`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Never trial-merge or merge on a dirty working tree | An in-progress merge on uncommitted changes can clobber the user's work irrecoverably |
| Always detect (Phase 2) before resolving (Phase 3) | Detection is non-destructive; jumping to a live merge without knowing the conflict set risks a messy half-merge |
| Detect conflicts with the script, not by eyeballing | `scripts/detect-conflicts.sh` produces a deterministic, reproducible conflict list and always cleans up its trial merge |
| A non-zero detection error is NOT "no conflicts" | Only exit `0` (clean) means safe to promote; exit `1` means the check failed and must be reported |
| Merge the target stage branch INTO the feature branch | Reconciles the work item with its destination; DevOps Center promotes the feature branch, so the resolution must live there |
| Verify no conflict markers remain (`git diff --check`) before committing | Committing unresolved markers corrupts the metadata and the promotion |
| Preserve XML well-formedness when manually merging metadata | Malformed `-meta.xml` breaks deployment; never leave duplicated or truncated elements |
| Push only the work item's feature branch | The resolution belongs to the work item's branch; never push to a stage/integration branch directly |
| This skill does not promote or deploy | Resolution ends at a pushed, conflict-free branch or a diagnosis; promotion (including full promotion) is `dx-devops-promote` |
| Diagnose deploy failures with the script, not by eyeballing | `scripts/diagnose-deploy-failure.sh` deterministically classifies the failure and verifies branch presence with `git show` |
| Recommend a full promotion ONLY when the missing component is on the feature branch | If the component is absent, promoting the branch cannot supply it — a re-promote just fails again |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **No `sf devops conflict` CLI command exists** | DevOps Center conflicts are Git conflicts — resolve them with `git`, not a `sf devops` subcommand. This skill is git-based by design |
| **Dirty working tree** | `git status --porcelain` must be empty; instruct the user to commit or stash before detecting/resolving |
| **User gave a work item, not a branch** | Resolve the work item to its feature branch first via `sf devops work-item` — see `references/git-conflict-resolution.md` |
| **Non-zero script exit treated as clean** | Exit `2` = conflicts, exit `1` = error. Only exit `0` is "safe to promote" |
| **Committing with markers still present** | Run `git diff --check` and confirm the `--diff-filter=U` list is empty before `git commit`; leftover `<<<<<<<`/`>>>>>>>` markers corrupt metadata |
| **`--ours` / `--theirs` reversed** | When merging the target INTO the feature branch, `--ours` = feature branch, `--theirs` = target stage branch |
| **Manually merged XML is malformed** | Keep `-meta.xml` well-formed; do not duplicate elements. Re-check the file parses before staging |
| **Detached HEAD / stale branch** | `git fetch` first; check out the feature branch as a tracking branch before merging (the script fetches for you) |
| **Conflict reappears after promotion still fails** | The target branch moved; re-run detection against the current target branch and resolve again |
| **Re-promoting a deploy failure without diagnosing** | Run `scripts/diagnose-deploy-failure.sh` first: exit `0` = component on the branch, a full promotion fixes it; exit `2` = it's a merge conflict (switch tracks); exit `3` = component absent, add and commit it (or include the owning work item) before promoting — promotion alone cannot supply it |

---

## Output Expectations

This skill produces a **conflict-free feature branch** or a **deploy-failure diagnosis**, not org changes:

- **No conflicts**: confirmation that the feature branch merges cleanly into the target stage branch — safe to promote
- **Conflicts resolved**: a merge commit on the work item's feature branch reconciling it with the target stage branch, pushed to the remote, plus a report of which files were resolved and how (took a side vs. manual merge)
- **Deploy-failure diagnosis**: a report stating the failure reason (merge conflict / missing dependency in-branch / missing dependency not-in-branch / unrecognized), whether a full promotion can fix it, the missing component and where it lives, and the concrete next step

No metadata is deployed and no org state is mutated. The deliverable is the pushed, conflict-free branch or the diagnosis and recommended next step.

---

## Cross-Skill Integration

| When | Action |
|------|--------|
| The branch is conflict-free (or resolved and pushed) and ready to advance | Delegate to `dx-devops-promote` to validate and promote |
| A work item name/ID must be resolved to its feature branch, or candidate work items listed | Use `dx-devops-work-item-manage` |
| Work items share metadata and could promote as one unit instead of resolving separately | Consider combining via `dx-devops-promote`'s combine step rather than a manual merge |
| A promote deploy already failed on a conflict | Re-detect against the current target branch, resolve, push, then re-promote via `dx-devops-promote` |
| Diagnosis says a full promotion can fix the failure (`dependency_in_feature_branch`) | Hand off to `dx-devops-promote` to run the full promotion — this skill does not promote |
| Missing component must be added to the feature branch before promoting | Author/commit the component (or include the owning work item) — for metadata generation use the relevant domain skill, then re-promote via `dx-devops-promote` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `scripts/detect-conflicts.sh` | Phase 2 — run it to non-destructively detect merge conflicts between the feature branch and the target stage branch |
| `scripts/diagnose-deploy-failure.sh` | Phase D — run it to classify a promotion deploy failure and decide whether a full promotion (or a missing-dependency fix) resolves it |
| `references/git-conflict-resolution.md` | When you need the full git command reference, the `sf devops work-item`-to-branch lookup, or `--ours`/`--theirs` and XML-merge guidance |
| `references/deploy-failure-resolution.md` | Phase D — when you need the deploy-failure decision tree, the error-parsing patterns, or the full-promotion reasoning behind the diagnosis script |
| `examples/conflict-workflows.md` | When the user's request matches a common pattern (pre-promotion conflict check, take-a-side resolution, manual XML merge, troubleshooting a failed promotion, or diagnosing a deploy failure) |
