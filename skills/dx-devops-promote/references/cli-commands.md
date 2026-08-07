# DevOps Center Promotion CLI Commands Reference

Complete reference for the `sf devops` promotion commands with JSON output schemas and error handling. All commands support `--json` and `--target-org <alias>`. Every command is keyed on **record IDs**, not work item names.

## Command Summary

| Command | Purpose | Required Flags | Async? |
|---------|---------|---------------|--------|
| `sf devops promotion validate` | Validate work item promotion to a target stage | `--work-item-id`, `--target-stage-id` | No |
| `sf devops work-item prepare` | Prepare one work item for promotion | `--work-item-id`, `--target-stage-id` | No |
| `sf devops work-item combine` | Combine child work items into a parent | `--parent-work-item-id`, `--child-work-item-id`, `--target-stage-id` | No |
| `sf devops promote` | Promote work item(s) or a stage to a target stage | (`--work-item-id` XOR `--stage-id`), `--target-stage-id`; add `--skip-validation` only if Phase 1 validate passed this session | Yes |
| `sf devops promotion complete` | Finalize the promotion in the target stage | `--target-stage-id` | No |

**Org authentication** — verify before any command:
```bash
sf org display --json
```

---

## Validate (Mandatory First Step)

Validates whether the specified work item(s) can be promoted to the target stage — checks for VCS and object-permission errors before a promotion is attempted. Requires `--target-stage-id`; repeat `--work-item-id` to validate multiple work items in one call.

```bash
sf devops promotion validate \
  --work-item-id 1fkxx0000000001AAA \
  --target-stage-id 1QVxx0000000001AAA \
  --target-org myorg \
  --json
```

### Key Flags

| Flag | Description |
|------|-------------|
| `-i, --work-item-id` | Work item to validate for promotion (required, repeatable) |
| `-t, --target-stage-id` | Target pipeline stage to validate promotion to (required) |
| `-o, --target-org` | Target org alias |

### JSON Output Schema (success)

```json
{
  "status": 0,
  "result": {
    "success": true,
    "errorType": null,
    "errorDetails": null,
    "combineDetails": null,
    "suggestions": []
  },
  "warnings": []
}
```

### JSON Output Schema (success, work items share components)

When multiple work items share metadata, validation still succeeds (`success: true`) but returns `combineDetails` and `suggestions` describing whether to combine before promoting:

```json
{
  "status": 0,
  "result": {
    "success": true,
    "errorType": null,
    "errorDetails": null,
    "combineDetails": {
      "parentWorkitemId": "1fk000000000001",
      "childWorkitemsId": ["1fk000000000002"],
      "sharedComponentsList": {
        "1fk000000000001": ["MyApexClass", "MyTrigger"],
        "1fk000000000002": ["MyApexClass"]
      }
    },
    "suggestions": [
      "The selected work items share one or more components. Choose one of these approaches:",
      "Option 1 - Combine the work items and promote them as a single unit: ...",
      "Option 2 - Promote the work items as they are, without combining: ..."
    ]
  },
  "warnings": []
}
```

### Interpreting the result

- **Success:** `status == 0` and `.result.success == true`. Proceed.
- **Shared components:** if `.result.combineDetails` is non-null, the work items share metadata. Use `.result.combineDetails.parentWorkitemId` / `.childWorkitemsId` to drive the combine decision in Phase 2 (see Combine), then promote the parent. This is the authoritative signal for whether to combine — don't guess.
- **Failure:** a non-zero exit code. The command surfaces an error such as `Validation failed (VCS_ERROR): No pull request exists for the work item on the source branch.`, with `.result.errorType` / `.result.errorDetails` populated in `--json`. STOP — do not prepare/combine/promote. The `VCS_ERROR` case confirms the associated-PR requirement is enforced here.

---

## Prepare

`--target-stage-id` is required (the pipeline stage the work item is being prepared to promote to).

```bash
sf devops work-item prepare --work-item-id 1fkxx0000000001AAA --target-stage-id 1QVxx0000000001AAA --target-org myorg --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "workItemId": "1fkxx0000000001AAA",
    "prepared": true
  }
}
```

Idempotent — re-running a prepared work item is a safe no-op.

---

## Combine

Combine one or more child work items into a parent work item so they promote as a single unit. Repeat `--child-work-item-id` once per child.

```bash
sf devops work-item combine \
  --parent-work-item-id 1fkxx0000000001AAA \
  --child-work-item-id 1fkxx0000000002AAA \
  --child-work-item-id 1fkxx0000000003AAA \
  --target-stage-id 1QVxx0000000001AAA \
  --target-org myorg \
  --json
```

### Key Flags

| Flag | Description |
|------|-------------|
| `--parent-work-item-id` | The primary work item that continues through the pipeline |
| `--child-work-item-id` | A work item to merge into the parent (repeatable) |
| `--target-stage-id` | The pipeline stage to promote the combined unit to (required) |
| `-o, --target-org` | Target org alias |

After combining, promote the **parent** work item ID via `sf devops promote`.

---

## Promote (Async)

Exactly one of `--work-item-id` or `--stage-id` must be provided; they are mutually exclusive. `--target-stage-id` is always required. **Pass `--skip-validation` ONLY when the Phase 1 validate step completed successfully this session for every work item being promoted** — `promote`'s built-in pre-promote validation runs the *same* checks (including the associated-PR requirement) as `sf devops promotion validate`. When that validation already ran this session, skipping avoids a redundant re-run; but if the agent resumed mid-workflow or promotion was invoked without a preceding validate, OMIT the flag so the CLI validates.

### Promote one or more work items

```bash
sf devops promote \
  --work-item-id 1fkxx0000000001AAA \
  --target-stage-id 1QVxx0000000001AAA \
  --skip-validation \
  --target-org myorg \
  --json
```

Repeat `--work-item-id` per item. For a combined promotion, pass the **parent** work item ID.

### Promote an entire source stage

```bash
sf devops promote \
  --stage-id 1QVxx0000000000AAA \
  --target-stage-id 1QVxx0000000001AAA \
  --skip-validation \
  --target-org myorg \
  --json
```

### Key Flags

| Flag | Description |
|------|-------------|
| `-i, --work-item-id` | Work item to promote (repeatable, mutually exclusive with `--stage-id`) |
| `-s, --stage-id` | Source stage whose approved work items are promoted (mutually exclusive with `--work-item-id`) |
| `-t, --target-stage-id` | Destination pipeline stage (required) |
| `-a, --deploy-all` | Deploy all metadata in the branch, not just changes not yet in the target stage |
| `-l, --test-level` | Apex test level: `NoTestRun`, `RunSpecifiedTests`, `RunLocalTests`, `RunAllTestsInOrg` |
| `--tests` | Specific tests to run when `--test-level RunSpecifiedTests` |
| `--skip-validation` | Skip `promote`'s built-in pre-promote validation. It runs the same checks (including the associated-PR requirement) as `promotion validate`. Pass this ONLY when Phase 1 validate already ran successfully this session; omit it if promotion was invoked without a preceding validate (e.g. mid-workflow resume) so the CLI validates |
| `-o, --target-org` | Target org alias |

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "promotionId": "0Af000000000001AAA",
    "sourceStageId": "1QVxx0000000000AAA",
    "targetStageId": "1QVxx0000000001AAA",
    "status": "InProgress"
  }
}
```

- Async operation. Capture `.result.promotionId` (some CLI versions use `.result.asyncOperationId`).
- Poll the returned identifier separately to confirm completion — do NOT busy-wait here.
- After the deploy completes, run `sf devops promotion complete` to finalize.

---

## Promotion Complete

Finalize the promotion — advances the promoted work items in the target stage. Run after the promote deploy succeeds. `--target-stage-id` is required (the same target stage the work items were promoted to).

```bash
sf devops promotion complete --target-stage-id 1QVxx0000000001AAA --target-org myorg --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "completed": true,
    "targetStageId": "1QVxx0000000001AAA"
  }
}
```

---

## Error Handling

**Work item not found:**
```json
{ "status": 1, "name": "NOT_FOUND", "message": "Work item does not exist or is not accessible", "exitCode": 1 }
```

**Not prepared before promote:**
```json
{ "status": 1, "name": "NOT_PREPARED", "message": "Work item has not been prepared for promotion", "exitCode": 1 }
```

**Missing target stage:**
```json
{ "status": 1, "name": "MissingRequiredFlag", "message": "Missing required flag --target-stage-id", "exitCode": 1 }
```

**Conflict on deploy:**
```json
{ "status": 1, "name": "DEPLOY_CONFLICT", "message": "Metadata conflict detected during deployment", "exitCode": 1 }
```

**Authentication failure:**
```json
{ "status": 1, "name": "NoOrgFound", "message": "No org configuration found for target-org. Run 'sf org login web' to authenticate.", "exitCode": 1 }
```

---

## Parsing Async Promotion IDs

```bash
# Promote and capture the promotion ID for status polling.
# --skip-validation is shown here because this snippet assumes Phase 1 validate
# already passed this session; OMIT it if promotion is invoked without a
# preceding validate (e.g. a mid-workflow resume).
PROMOTION_ID=$(sf devops promote \
  --work-item-id 1fkxx0000000001AAA \
  --target-stage-id 1QVxx0000000001AAA \
  --skip-validation \
  --target-org myorg \
  --json | jq -r '.result.promotionId // .result.asyncOperationId')

echo "Promotion initiated. Promotion ID: $PROMOTION_ID"
# Poll this ID separately, then run: sf devops promotion complete --target-stage-id 1QVxx0000000001AAA --target-org myorg --json
```

---

## Resolving Names to IDs

Promotion commands need record IDs. Resolve a project name and work item subject/name to IDs first:

```bash
# List projects to resolve a project name to an ID
# (project list returns .result.projects[] with capitalized .Id / .Name)
sf devops project list --json | jq -r '.result.projects[] | "\(.Id): \(.Name)"'

# Resolve a work item subject to its ID
# (work-item list returns .result.workItems[] with .id / .subject)
sf devops work-item list --project-id <project-id> --json | \
  jq -r '.result.workItems[] | select(.subject == "<subject>") | .id'
```

---

## Authentication Requirements

All promotion commands require:

1. **Authenticated org**: `sf org login web` or JWT auth (for CI)
2. **DevOps Center enabled**: org must have DOCe provisioned
3. **Promotion permissions**: user/service account must be able to promote in the target pipeline

Auth is the caller's responsibility — these skills contain no auth logic. In CI, use a JWT-authenticated service-account alias with least-privilege scopes.
