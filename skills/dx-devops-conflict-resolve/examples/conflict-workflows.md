# DevOps Center Conflict Resolution Examples

Common end-to-end patterns. Every pattern runs in a local clone of the DevOps Center connected Git repo, starts from a **clean working tree**, and **detects before resolving**. Detection is non-destructive; resolution ends with a commit pushed to the work item's feature branch. Promotion itself is `dx-devops-promote`, not this skill.

---

## Example 1 — Pre-promotion conflict check (no conflicts)

**User prompt:** "Before I promote `feature/WI-101` to UAT, is there anything that will conflict?"

```bash
# 1. Confirm a clean tree
git status --porcelain    # must be empty

# 2. Detect (non-destructive) — target stage branch is uat
scripts/detect-conflicts.sh feature/WI-101 uat origin
# → CLEAN: no merge conflicts between feature/WI-101 and origin/uat   (exit 0)
```

**Report:** "No merge conflicts between `feature/WI-101` and `uat`. Safe to promote — hand off to `dx-devops-promote`."

---

## Example 2 — Resolve by taking one side

**User prompt:** "`feature/WI-101` conflicts with `uat` on the README — keep my branch's version."

```bash
# 1. Detect
scripts/detect-conflicts.sh feature/WI-101 uat origin
# → CONFLICTS: merging origin/uat into feature/WI-101 conflicts on these files:
#   docs/README.md                                                   (exit 2)

# 2. Real merge to bring in the markers
git checkout feature/WI-101
git merge --no-ff origin/uat

# 3. Keep the feature branch's version (ours = feature branch when merging target → feature)
git checkout --ours -- docs/README.md
git add docs/README.md

# 4. Verify nothing left, then finalize
git diff --check
git diff --name-only --diff-filter=U    # empty
git commit --no-edit
git push origin feature/WI-101
```

**Report:** "Resolved `docs/README.md` by keeping the feature branch's version; merged `uat` into `feature/WI-101` and pushed. Re-validate and promote via `dx-devops-promote`."

---

## Example 3 — Manual merge of conflicting XML metadata

**User prompt:** "Two work items both edited the `Account` object — resolve the conflict on `feature/WI-205` against `integration`, keeping both sets of fields."

```bash
# 1. Detect
scripts/detect-conflicts.sh feature/WI-205 integration origin
# → CONFLICTS: ... force-app/main/default/objects/Account/Account.object-meta.xml   (exit 2)

# 2. Real merge
git checkout feature/WI-205
git merge --no-ff origin/integration

# 3. Hand-merge the XML: open the file, reconcile the
#    <<<<<<< / ======= / >>>>>>> regions so BOTH work items' <fields> blocks
#    are present exactly once, keep the document well-formed, no duplicated elements.
#    (Edit Account.object-meta.xml here.)

# 4. Sanity-check it still parses, then stage
xmllint --noout force-app/main/default/objects/Account/Account.object-meta.xml   # if available
git add force-app/main/default/objects/Account/Account.object-meta.xml

# 5. Verify + finalize
git diff --check
git diff --name-only --diff-filter=U    # empty
git commit --no-edit
git push origin feature/WI-205
```

**Report:** "Manually merged `Account.object-meta.xml`, preserving both work items' field additions; XML validated, merged `integration` into `feature/WI-205`, and pushed. Consider combining these work items via `dx-devops-promote` if they should promote as one unit."

---

## Example 4 — Prefer combine over manual merge

**User prompt:** "WI-301 and WI-302 keep conflicting on the same Apex class every promotion."

When two work items legitimately share components, resolving the same metadata by hand on every promotion is wasted effort. Detect to confirm the overlap, then recommend combining rather than merging:

```bash
scripts/detect-conflicts.sh feature/WI-301 uat origin
# → CONFLICTS: ... force-app/main/default/classes/AccountService.cls   (exit 2)
```

**Report:** "WI-301 and WI-302 both modify `AccountService.cls`. Rather than hand-merging on each promotion, combine them into one promotion unit via `dx-devops-promote`'s combine step so they deploy together. If you must keep them separate, resolve now: merge `uat` into `feature/WI-301`, reconcile the class, commit, and push."

---

## Example 5 — Troubleshoot a promotion that failed on a conflict

**User prompt:** "My promote just failed with a deploy conflict — fix it."

```bash
# 1. The target branch may have moved since the last check. Re-detect against
#    the CURRENT target stage branch on a clean tree.
git status --porcelain      # must be empty
scripts/detect-conflicts.sh feature/WI-410 main origin

# 2a. If exit 0 (CLEAN): the conflict was transient/stale — re-run dx-devops-promote.
# 2b. If exit 2 (CONFLICTS): resolve as in Examples 2/3, then push:
git checkout feature/WI-410
git merge --no-ff origin/main
# ...resolve each file, git add...
git diff --check
git commit --no-edit
git push origin feature/WI-410
```

**Report:** "Re-detected against the current `main`; resolved `<files>` and pushed `feature/WI-410`. Re-run the promotion via `dx-devops-promote`."

---

## Example 6 — Diagnose a deployment failure (full promotion can fix)

**User prompt:** "My promotion of WI-101 to UAT failed with `Variable does not exist: BillingService`. What do I do?"

```bash
# 1. Diagnose deterministically from the repo clone. The class BillingService is
#    referenced but was left out of a partial deployed set.
echo "Problem: Variable does not exist: BillingService" \
  | scripts/diagnose-deploy-failure.sh - feature/WI-101 uat origin
# → MISSING_DEPENDENCY_TYPE=ApexClass
#   MISSING_DEPENDENCY_NAME=BillingService
#   IN_FEATURE_BRANCH=true
#   REASON=dependency_in_feature_branch
#   CAN_FULL_PROMOTION_FIX=true                                        (exit 0)
```

**Report:** "`BillingService` (ApexClass) exists on `feature/WI-101` but wasn't in the deployed set, so the deploy failed on a missing dependency. A **full promotion** will include it and should fix the failure. Confirm, then run the full promotion via `dx-devops-promote`."

---

## Example 7 — Diagnose a deployment failure (component missing from the branch)

**User prompt:** "Promotion failed: `no ApexClass named TaxHelper found`. Just re-run it as a full promotion?"

```bash
sf project deploy start ... 2>&1 \
  | scripts/diagnose-deploy-failure.sh - feature/WI-210 integration origin
# → MISSING_DEPENDENCY_TYPE=ApexClass
#   MISSING_DEPENDENCY_NAME=TaxHelper
#   IN_FEATURE_BRANCH=false
#   REASON=dependency_not_in_feature_branch
#   CAN_FULL_PROMOTION_FIX=false                                       (exit 3)
```

**Report:** "No — `TaxHelper` is **not** on `feature/WI-210`, so promoting the branch (full or partial) cannot supply it. Add and commit `TaxHelper` to the feature branch (or include the work item that owns it), then re-promote via `dx-devops-promote`." (If exit `4`/`no_dependency_parsed`, report the raw error and advise fixing the underlying issue — e.g. test coverage — since a full promotion won't help. If exit `2`/`merge_conflict`, switch to the conflict-resolution track above.)

---

## Idempotency note

Detection is always safe to re-run — it aborts its trial merge and restores the checkout. If a live merge is interrupted (`MERGE_HEAD exists`), either finish it (`git commit`) or abort it (`git merge --abort`) before re-detecting; never start a second merge on top of an unfinished one.
