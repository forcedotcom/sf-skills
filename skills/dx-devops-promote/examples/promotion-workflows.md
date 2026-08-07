# Promotion Workflow Examples

Common end-to-end promotion patterns. Every pattern begins with the mandatory validate step. All commands are keyed on record IDs — resolve names/subjects to IDs first. The promote step is async and returns a promotion ID that is polled separately before running `promotion complete`.

---

## Example 1 — Promote a single work item

**User prompt:** "Promote work item 1fkxx0000000123AAA to the QA stage."

```bash
# 1. Verify auth
sf org display --json

# 2. Mandatory validate (requires the target stage)
sf devops promotion validate \
  --work-item-id 1fkxx0000000123AAA \
  --target-stage-id 1QVxx0000000QA0AAA \
  --target-org myorg --json
# → status 0 and .result.success == true, proceed. On non-zero exit, STOP.

# 3. Prepare (target stage is required)
sf devops work-item prepare --work-item-id 1fkxx0000000123AAA --target-stage-id 1QVxx0000000QA0AAA --target-org myorg --json

# 4. Promote (async). --skip-validation: this skill already validated (step 2)
#    and prepared (step 3), so the CLI's built-in pre-promote check is redundant.
PROMOTION_ID=$(sf devops promote \
  --work-item-id 1fkxx0000000123AAA \
  --target-stage-id 1QVxx0000000QA0AAA \
  --skip-validation \
  --target-org myorg \
  --json | jq -r '.result.promotionId // .result.asyncOperationId')

echo "Promotion initiated. Promotion ID: $PROMOTION_ID"

# 5. Hand off the promotion ID for status polling (a separate concern —
#    do NOT busy-wait here). Only once the async deploy has CONFIRMED
#    completion should the promotion be finalized:
#      sf devops promotion complete --target-stage-id 1QVxx0000000QA0AAA --target-org myorg --json
```

**Report:** "Work item promotion initiated (→ QA stage). Promotion ID: `<id>`. Poll this ID to confirm the deploy completed; run `sf devops promotion complete` only after it reports success."

---

## Example 2 — Combine and promote multiple work items

**User prompt:** "Combine work items 1fkxx…101 and 1fkxx…102 into 1fkxx…100 and promote them to UAT."

```bash
# 1. Validate ALL work items against the target stage in one call — if it fails
#    (non-zero exit), STOP. On success, a non-null .result.combineDetails
#    confirms the work items share components and returns the parent/child
#    grouping to use in step 2.
sf devops promotion validate \
  --work-item-id 1fkxx0000000100AAA \
  --work-item-id 1fkxx0000000101AAA \
  --work-item-id 1fkxx0000000102AAA \
  --target-stage-id 1QVxx000000UAT0AAA \
  --target-org myorg --json

# 2. Combine children into the parent (from .result.combineDetails), targeting the destination stage
sf devops work-item combine \
  --parent-work-item-id 1fkxx0000000100AAA \
  --child-work-item-id 1fkxx0000000101AAA \
  --child-work-item-id 1fkxx0000000102AAA \
  --target-stage-id 1QVxx000000UAT0AAA \
  --target-org myorg \
  --json

# 3. Promote the PARENT work item (async). --skip-validation: all work items
#    were validated in step 1 and combining prepared the unit.
PROMOTION_ID=$(sf devops promote \
  --work-item-id 1fkxx0000000100AAA \
  --target-stage-id 1QVxx000000UAT0AAA \
  --skip-validation \
  --target-org myorg \
  --json | jq -r '.result.promotionId // .result.asyncOperationId')

echo "Combined promotion initiated. Promotion ID: $PROMOTION_ID"

# 4. Hand off the promotion ID for status polling. Finalize with
#    `sf devops promotion complete --target-stage-id 1QVxx000000UAT0AAA --target-org myorg --json`
#    ONLY after the async deploy has confirmed completion — do not run it here.
```

**Report:** "Work items combined into parent 1fkxx…100 and promotion initiated (→ UAT). Promotion ID: `<id>`. Poll this ID; run `sf devops promotion complete` only after the deploy reports success."

---

## Example 3 — Promote an entire stage

**User prompt:** "Promote everything in the QA stage to Production."

```bash
# 1. The validate-first gate still applies. `sf devops work-item list` takes
#    --project-id (not a stage flag), so list the project's work items and
#    filter to the approved ones in the QA stage with jq. Validate them against
#    the target stage before promoting — if validation fails, STOP; do not promote.
#
#    IMPORTANT: capture the list command into a variable with fail-fast checks
#    BEFORE filtering. Do not put `sf devops work-item list | jq` directly in a
#    `for` loop — command substitution in the loop header hides non-zero exits
#    (and an unset/invalid project ID) as an empty iteration, which would skip
#    validation entirely and fall through to `sf devops promote`.
set -euo pipefail
PROJECT_ID=1Qg0000000000001
QA_STAGE_ID=1QVxx0000000QA0AAA
PROD_STAGE_ID=1QVxx00000PROD0AAA   # the target stage promotion validates against

if ! WI_LIST_JSON=$(sf devops work-item list --project-id "$PROJECT_ID" --target-org myorg --json); then
  echo "Failed to list work items for project $PROJECT_ID — STOP. Do not promote." >&2
  exit 1
fi

# `sf devops work-item list` returns .result.workItems[]. Filter to the approved
# work items in the QA stage.
WI_IDS=$(printf '%s' "$WI_LIST_JSON" \
  | jq -r --arg s "$QA_STAGE_ID" '.result.workItems[] | select(.stageId == $s and .status == "Approved") | .id')

if [ -z "$WI_IDS" ]; then
  echo "No approved work items in QA stage $QA_STAGE_ID — STOP. Do not promote." >&2
  exit 1
fi

# Validate all approved work items against the TARGET stage in one call (repeat
# --work-item-id per item). A non-zero exit means validation failed — STOP.
VALIDATE_ARGS=()
for WI_ID in $WI_IDS; do VALIDATE_ARGS+=(--work-item-id "$WI_ID"); done
if ! sf devops promotion validate "${VALIDATE_ARGS[@]}" \
     --target-stage-id "$PROD_STAGE_ID" --target-org myorg --json; then
  echo "Promotion validation failed — STOP. Do not promote the stage." >&2
  exit 1
fi

# 2. All QA work items validated — promote the whole source stage to the
#    target stage (async). Production deploys with Apex should run tests.
PROMOTION_ID=$(sf devops promote \
  --stage-id "$QA_STAGE_ID" \
  --target-stage-id "$PROD_STAGE_ID" \
  --test-level RunLocalTests \
  --skip-validation \
  --target-org myorg \
  --json | jq -r '.result.promotionId // .result.asyncOperationId')

echo "Stage promotion initiated. Promotion ID: $PROMOTION_ID"

# 3. Hand off the promotion ID for status polling. Finalize with
#    `sf devops promotion complete --target-stage-id "$PROD_STAGE_ID" --target-org myorg --json`
#    ONLY after the async deploy has confirmed completion — do not run it here.
```

**Report:** "QA → Production stage promotion initiated after validating all approved QA work items. Promotion ID: `<id>`. Poll this ID; run `sf devops promotion complete` only after the deploy reports success."

---

## Example 4 — Validate-first gate blocks promotion

**User prompt:** "Promote work item 1fkxx0000000200AAA."

```bash
sf devops promotion validate \
  --work-item-id 1fkxx0000000200AAA \
  --target-stage-id 1QVxx0000000QA0AAA \
  --target-org myorg --json
```

Response (non-zero exit indicates the work item cannot be promoted):
```json
{
  "status": 1,
  "result": {
    "success": false,
    "errorType": "VCS_ERROR",
    "errorDetails": "No pull request exists for the work item on the source branch."
  },
  "warnings": []
}
```

**Action:** STOP. Do NOT prepare/combine/promote/complete. Report the exact blocking issue from `.result.errorType` / `.result.errorDetails` — here a `VCS_ERROR`: no pull request exists for the work item on the source branch. Remediate the reported cause (create/associate the pull request for the work item), then re-validate only after it is resolved.

**Report:** "Promotion blocked — validation failed (`VCS_ERROR`): no pull request exists for the work item on the source branch. Create/associate the PR, then re-validate and retry."

---

## Example 5 — Idempotent retry in CI

**Scenario:** A CI job re-runs after a transient network failure mid-promotion.

```bash
# Re-running validate + prepare is safe — prepare is a no-op if already prepared
sf devops promotion validate \
  --work-item-id 1fkxx0000000300AAA \
  --target-stage-id 1QVxx0000000QA0AAA \
  --target-org myorg --json
sf devops work-item prepare --work-item-id 1fkxx0000000300AAA --target-stage-id 1QVxx0000000QA0AAA --target-org myorg --json
# → treat an already-prepared work item as success

# Promote again — capture the promotion ID (--skip-validation: validated and
# prepared above)
PROMOTION_ID=$(sf devops promote \
  --work-item-id 1fkxx0000000300AAA \
  --target-stage-id 1QVxx0000000QA0AAA \
  --skip-validation \
  --target-org myorg \
  --json | jq -r '.result.promotionId // .result.asyncOperationId')

echo "Promotion ID: $PROMOTION_ID"
```

**Key point:** validate and prepare are idempotent — retries do not create duplicate state or double-prepare.
