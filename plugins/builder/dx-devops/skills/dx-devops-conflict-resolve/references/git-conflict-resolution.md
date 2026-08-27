# DevOps Center Git Conflict Resolution Reference

DevOps Center is **Git-backed**. Each work item is a feature branch; each pipeline stage has a target branch. Promotion merges the feature branch into the target stage branch, so overlapping metadata changes across work items surface as **git merge conflicts**. There is no `sf devops conflict` CLI command — detection and resolution use standard `git`. This reference covers the git commands, the work-item-to-branch lookup, and metadata-merge guidance.

## The DevOps Center branching model

- **Feature branch** — one per work item, created off the source stage branch. Holds that work item's metadata changes. DevOps Center promotes *this* branch, so any conflict resolution must be committed here.
- **Target stage branch** — the branch of the pipeline stage the work item promotes into (e.g. `integration`, `uat`, `main`).
- **Conflict** — when the feature branch and the target stage branch both changed the same lines/components, the merge cannot auto-resolve.

Resolution direction: **merge the target stage branch INTO the feature branch**. This reconciles the work item with where it is going and keeps the resolution on the branch DevOps Center promotes. When merging target → feature, `--ours` is the **feature branch** and `--theirs` is the **target stage branch**.

---

## Resolving a work item to its feature branch

If the user supplies a work item ID or subject rather than a branch name, resolve it first. Verify org auth, then look up the work item — the branch field name varies by CLI version, so inspect the record:

```bash
# Verify auth (fix with: sf org login web --set-default --alias <alias>)
sf org display --json

# Inspect a work item record to find its branch/source-branch field.
sf devops work-item list --project-id <project-id> --target-org <alias> --json \
  | jq -r '.result.workItems[] | select(.subject == "<subject>")'
```

Look for a branch-name field (commonly `branch`, `sourceBranch`, `featureBranch`, or similar) in the returned record and use it as `<feature-branch>`. If the field is absent, ask the user for the branch name.

---

## Non-destructive detection

Use `scripts/detect-conflicts.sh` (it fetches, trial-merges the target into the feature branch without committing, lists conflicts, and aborts the trial):

```bash
scripts/detect-conflicts.sh <feature-branch> <target-branch> [remote]
# exit 0 = clean, exit 2 = conflicts (files printed), exit 1 = error
```

Equivalent manual detection (only on a clean tree — always abort afterward):

```bash
git fetch origin
git checkout <feature-branch>
git merge --no-commit --no-ff origin/<target-branch> >/dev/null 2>&1 || true
git diff --name-only --diff-filter=U     # the conflicting files
git merge --abort                        # undo the trial — leaves the tree untouched
```

---

## Live resolution

Once detection confirms conflicts, run the real merge and resolve:

```bash
git checkout <feature-branch>
git merge --no-ff origin/<target-branch>   # conflict markers now in the working tree
git diff --name-only --diff-filter=U       # files still to resolve
```

### Per-file resolution options

| Situation | Command | Meaning |
|-----------|---------|---------|
| Keep the feature branch's version | `git checkout --ours -- <file>` | Discards the target stage branch's change to this file |
| Take the target stage branch's version | `git checkout --theirs -- <file>` | Discards the feature branch's change to this file |
| Both sides needed | Edit the file by hand | Reconcile `<<<<<<<` / `=======` / `>>>>>>>` regions into one correct version |

After resolving each file, stage it:

```bash
git add <file>
```

### Verify before committing

```bash
git diff --check                      # must print nothing (no leftover markers/whitespace errors)
git diff --name-only --diff-filter=U  # must be empty (no unmerged files)
```

If either shows output, keep resolving. **Never commit with conflict markers present** — it corrupts the metadata.

### Complete and push

```bash
git commit --no-edit                  # finalize the merge with the default message
git push origin <feature-branch>      # DevOps Center tracks this branch
```

Push only the work item's **feature branch** — never a stage/integration branch directly.

---

## Merging XML metadata safely

Salesforce source-format metadata is XML (`.object-meta.xml`, `.field-meta.xml`, `.flow-meta.xml`, `.permissionset-meta.xml`, etc.). When manually merging:

- Keep the document **well-formed** — every opening tag needs its close; do not truncate mid-element.
- **Do not duplicate elements** — if both sides added the same `<fields>` or `<listViews>` block, keep one; if they added *different* children under the same parent, keep both children under a single parent.
- Preserve ordering where the platform is order-sensitive (e.g. picklist `<values>` sequence).
- After editing, sanity-check the file parses (e.g. `xmllint --noout <file>` if available, or a quick visual scan for balanced tags) before `git add`.

Prefer a **combine** (via `dx-devops-promote`'s combine step) over a manual merge when two work items legitimately share components and should promote as one unit — it avoids hand-merging the same metadata twice.

---

## Common errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `error: Your local changes ... would be overwritten by merge` | Dirty working tree | Commit or stash first; the detection script refuses to run on a dirty tree |
| `merge: <branch> - not something we can merge` | Branch not fetched / wrong name | `git fetch origin`; verify `origin/<target-branch>` exists |
| `fatal: You have not concluded your merge (MERGE_HEAD exists)` | A prior merge is unfinished | Finish it (`git commit`) or abort it (`git merge --abort`) before retrying |
| Conflict markers committed by mistake | Committed without `git diff --check` | Amend/redo the resolution; markers (`<<<<<<<`) in metadata break deployment |
| Pushed to the wrong branch | Pushed a stage branch | Only push the work item's feature branch; revert any direct stage-branch push |

---

## Authentication and access

Git operations use the repo clone's configured remote credentials (SSH key or token). The `sf devops work-item` lookup requires an authenticated org with DevOps Center enabled and read access to the project. Auth is the caller's responsibility — this skill contains no auth logic. In CI, use a service-account git credential and a JWT-authenticated `sf` alias with least-privilege scopes.
