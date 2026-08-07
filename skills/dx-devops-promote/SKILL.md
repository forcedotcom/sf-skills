---
name: dx-devops-promote
description: "Use this skill to drive the full DevOps Center promotion workflow for work items and pipeline stages — validate preconditions, prepare work items, optionally combine work items that share metadata, promote one or more work items or an entire stage to a target pipeline stage, and complete the promotion to finalize the deployment. TRIGGER when the user wants to promote a work item, advance changes to the next environment or stage, combine work items for a single promotion, or move metadata through the release pipeline. The mandatory validate step runs automatically at the start. DO NOT TRIGGER for work item creation or status updates (use dx-devops-work-item-manage), for conflict detection, or for polling an existing promotion's status."
metadata:
  version: "1.0"
  minApiVersion: "58.0"
  relatedSkills:
    - "dx-devops-work-item-manage"
  cliTools:
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

# DevOps Center Promotion

Drives the full promotion workflow in DevOps Center — validate, prepare, optionally combine, promote, and complete — moving work items through the release pipeline. Provides headless, `--json`-driven, idempotent operations for autonomous release workflows in CI. Every promotion begins with a mandatory validate step.

## Scope

- **In scope**: Validate promotion preconditions, prepare a work item, combine work items that share metadata into one promotion, promote one or more work items or an entire source stage to a target stage, and complete the promotion
- **Out of scope**: Work item creation/status updates (use `dx-devops-work-item-manage`), conflict detection, polling an existing promotion's status, pipeline or project setup (separate skills)

---

## Required Inputs

Gather or infer before proceeding:

- **Promotion target**: one or more specific work items, or all approved work items in a source stage
- **Target stage ID** (required for every promotion command — validate, prepare, combine, promote, and complete): `--target-stage-id` — the pipeline stage to promote to
- **Work item ID(s)** or **source stage ID** — depending on the promotion target. `sf devops promote` takes `--work-item-id` (repeatable) XOR `--stage-id`
- **For combined promotion**: a parent work item ID and one or more child work item IDs that share metadata
- **Target org**: `--target-org <alias>` (required unless the `target-org` config variable is set)

Defaults unless specified:
- Output format: `--json` for headless consumption
- Test level: omit `--test-level` for development-stage deploys (defaults to `NoTestRun`); use `RunLocalTests` for production-stage deploys with Apex

If the user gives a clear request ("promote work item 1fkxx… to stage 1QVxx…", "promote the QA stage to UAT", "combine these work items and promote"), proceed once you have the required IDs.

---

## Workflow

All operations use `sf devops` CLI commands with `--json` output. Validate ALWAYS runs first. All promotion commands are keyed on **record IDs**, not work item names — resolve names to IDs first if needed.

### Phase 1 — Authenticate and Validate

1. **Verify org authentication** before any operation:
   ```bash
   sf org display --json
   ```
   - If it fails, instruct the user to run `sf org login web --set-default --alias <alias>`
   - Pass `--target-org <alias>` on every subsequent command (required unless the `target-org` config variable is set)

2. **Run the mandatory validate step** — this is non-negotiable and always runs before prepare/combine/promote. `sf devops promotion validate` requires the target stage (`-t/--target-stage-id`) and one or more `-i/--work-item-id`:
   ```bash
   # Capture the output — Phase 2 derives the combine decision from it deterministically.
   VALIDATE_JSON=$(sf devops promotion validate --work-item-id <id> --target-stage-id <target-stage-id> --target-org <alias> --json)
   ```
   - Validates whether the work item(s) can be promoted to the target stage — checks for VCS and object-permission errors (including the associated-PR requirement) before a promotion is attempted
   - Repeat `--work-item-id` to validate multiple work items in one call
   - **Success:** `status == 0` and `.result.success == true` — proceed
   - **If validation fails** (non-zero exit; e.g. `VCS_ERROR: No pull request exists…`, with `.result.errorType`/`.result.errorDetails` set), STOP. Report the error and do not proceed. If it references metadata overlap, resolve the conflict before retrying
   - **Shared components:** when `.result.combineDetails` is non-null, the work items share metadata — validate returns the parent/child grouping and `suggestions`. This is the authoritative signal for the Phase 2 combine decision (see step 4); do not guess whether to combine — the Phase 2 script reads `.result.combineDetails` from `VALIDATE_JSON`

### Phase 2 — Prepare (and optionally Combine)

3. **Prepare the work item** for promotion:
   ```bash
   sf devops work-item prepare --work-item-id <id> --target-stage-id <target-stage-id> --target-org <alias> --json
   ```
   - `--target-stage-id` is required — the same target stage the work item will be promoted to
   - Idempotent: re-running a prepared work item is safe — treat as success

4. **Combine work items** — ONLY when the Phase 1 validate step reported shared components (`.result.combineDetails` non-null) or the work items otherwise have dependencies and must promote as one unit. Do not eyeball the JSON — derive the decision and the parent/child IDs deterministically from the saved validate output (`VALIDATE_JSON`):
   ```bash
   # COMBINE == "true" only when validate returned a combineDetails block.
   COMBINE=$(printf '%s' "$VALIDATE_JSON" | jq -r '(.result.combineDetails != null)')
   if [ "$COMBINE" = "true" ]; then
     PARENT_ID=$(printf '%s' "$VALIDATE_JSON" | jq -r '.result.combineDetails.parentWorkitemId')
     # one --child-work-item-id arg per child, safe for use as a flag array
     CHILD_ARGS=()
     while IFS= read -r cid; do CHILD_ARGS+=(--child-work-item-id "$cid"); done < <(
       printf '%s' "$VALIDATE_JSON" | jq -r '.result.combineDetails.childWorkitemsId[]')
   fi
   ```
   Then combine using those derived values (skip this command entirely when `COMBINE` is not `"true"`):
   ```bash
   sf devops work-item combine \
     --parent-work-item-id "$PARENT_ID" \
     "${CHILD_ARGS[@]}" \
     --target-stage-id <stage-id> \
     --target-org <alias> \
     --json
   ```
   - `CHILD_ARGS` expands to one `--child-work-item-id <id>` pair per child work item
   - The **parent** work item is the primary item that continues through the pipeline; child changes merge into the parent's branch during promotion
   - After combining, promote the **parent** work item ID in step 5

### Phase 3 — Promote

5. **Promote to the target stage** — exactly one of `--work-item-id` or `--stage-id` must be provided; `--target-stage-id` is always required. **Pass `--skip-validation` ONLY when the Phase 1 validate step completed successfully in the current session for every work item being promoted.** Otherwise, OMIT the flag and let the CLI run its built-in validation:
   - Promote one or more specific work items (repeat `--work-item-id` per item; use the parent's ID for a combined promotion). Include the `--skip-validation` line ONLY if Phase 1 validate passed this session; otherwise drop that line:
     ```bash
     sf devops promote \
       --work-item-id <id> \
       --target-stage-id <target-stage-id> \
       --skip-validation \
       --target-org <alias> \
       --json
     ```
   - Or promote all approved work items from a source stage (again, include the `--skip-validation` line only if Phase 1 validate passed this session):
     ```bash
     sf devops promote \
       --stage-id <source-stage-id> \
       --target-stage-id <target-stage-id> \
       --skip-validation \
       --target-org <alias> \
       --json
     ```
   - **Why conditional:** `sf devops promote`'s built-in pre-promote validation runs the *same* checks as the Phase 1 `sf devops promotion validate` step (including the associated-PR requirement). When the full workflow ran sequentially this session, that validation already passed, so `--skip-validation` only eliminates a redundant re-run. But if the agent resumed mid-workflow, promotion was invoked without a preceding Phase 1 validate, or Phase 1 was not run for every work item being promoted, DO NOT pass `--skip-validation` — bypassing it there would skip validation entirely with no prior guard
   - Add `--deploy-all` to deploy all metadata in the branch rather than only changes not yet in the target stage
   - Add `--test-level RunLocalTests` (or `RunSpecifiedTests --tests <names>`) for production-stage deploys that include Apex
   - The deploy runs asynchronously — capture the returned promotion/deploy identifier from the JSON `.result`

### Phase 4 — Complete and Report

6. **Complete the promotion** to finalize — advances the work items in the target stage:
   ```bash
   sf devops promotion complete --target-stage-id <target-stage-id> --target-org <alias> --json
   ```
   - Run after the promote deploy succeeds to mark the promotion done in the target stage
   - `--target-stage-id` is required (same target stage the work items were promoted to)

7. **Report the outcome**:
   - Confirm the CLI returned status 0 for each step
   - Report the promotion/deploy identifier and note that async deploy completion is tracked separately
   - Do NOT block or busy-wait inside this skill — surface the identifier and return
   - State the promotion clearly: e.g., "Work item promotion initiated (source stage → target stage). Deploy ID: <id>. Poll this ID to confirm deploy completion, then run promotion complete."

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Validate ALWAYS runs first | Guarantees preconditions are met before any mutation; skipping it can corrupt pipeline state |
| All `sf devops` commands must use `--json` | Structured output is required for headless consumption; human-readable output is unreliable to parse |
| Commands are keyed on record IDs, not names | `--work-item-id`, `--stage-id`, `--target-stage-id`, `--parent/--child-work-item-id` all take IDs; resolve names to IDs first |
| `--target-stage-id` required for every promotion command (validate, prepare, combine, promote, complete) | The target stage is mandatory; the promotion has no destination without it |
| Exactly one of `--work-item-id` or `--stage-id` on promote | These flags are mutually exclusive; promote either specific items or a whole source stage |
| Pass `--skip-validation` on promote ONLY if Phase 1 validate passed this session | The CLI's built-in pre-promote validation runs the same checks (including the associated-PR requirement) as the Phase 1 `promotion validate` step. Skipping is safe only when that validation already ran successfully this session; if the agent resumed mid-workflow or promotion was invoked without a preceding validate, OMIT the flag so the CLI validates |
| Deploy runs async — capture and report the identifier | The promote deploy does not complete synchronously; completion is tracked separately |
| Do NOT busy-wait for deploy completion in this skill | Polling is a separate concern; blocking here wastes turns and risks timeouts |
| Combine only when work items share metadata/dependencies | Combining is for conflict-prone or dependent items, not a default for every multi-item promotion |
| Prepare is idempotent | Retry-safe for CI; re-running a completed prepare is a no-op |
| Never use interactive prompts | Skills run headless; all inputs must be CLI flags |
| Pass IDs as CLI flags, never interpolate into shell strings | Prevents prompt/command injection via crafted identifiers |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **Validation fails** | STOP — do not prepare/combine/promote. Report the non-zero status / error message; if metadata overlap, resolve the conflict before retrying |
| **No default org set** | Run `sf org display --json`; if it fails, instruct user to run `sf org login web --set-default` |
| **Passing a work item name instead of an ID** | Promotion commands need record IDs; resolve names via `sf devops work-item list --project-id <id> --json \| jq -r '.result.workItems[] \| select(.subject == "<WI-subject>") \| .id'` |
| **Both `--work-item-id` and `--stage-id` supplied** | They are mutually exclusive; pick specific work items OR a source stage, not both |
| **Missing `--target-stage-id`** | Required on every promotion command (validate, prepare, combine, promote, complete); obtain the target stage ID from the pipeline configuration |
| **Combined promotion promotes the wrong item** | After `work-item combine`, promote the **parent** work item ID — children merge into the parent's branch |
| **Treating the deploy as synchronous** | The promote deploy is async; capture the identifier and confirm completion before running `promotion complete` |
| **Production deploy fails on Apex coverage** | Set `--test-level RunLocalTests` (or `RunSpecifiedTests --tests <names>`) for production-stage promotions with Apex |
| **Deploy fails with conflict** | A conflict slipped past validate; resolve the metadata conflict, then re-validate and retry |

---

## Output Expectations

Deliverables vary by operation:

- **Validate**: `.result.success` plus, when work items share metadata, `.result.combineDetails` / `.result.suggestions`. A non-zero exit (with `.result.errorType`/`.result.errorDetails`) means the work item cannot be promoted to the target stage
- **Prepare / combine**: confirmation that the work item(s) are staged (combine returns the parent/child grouping)
- **Promote**: an async deploy identifier and confirmation that the promotion deploy was initiated
- **Promotion complete**: confirmation the work items advanced in the target stage

Outputs are derived from `sf devops work-item`, `sf devops promote`, and `sf devops promotion complete` CLI commands. Async deploy completion is NOT produced by the promote call — poll the returned identifier separately before completing.

---

## Cross-Skill Integration

| When | Action |
|------|--------|
| Work item must be created or moved to a promotable status first | Delegate to `dx-devops-work-item-manage` |
| Validation reports metadata overlap / conflict | Resolve the metadata conflict before retrying |
| The promote deploy identifier must be polled to confirm completion | Poll the returned identifier separately, then run `sf devops promotion complete` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cli-commands.md` | When you need detailed CLI flag documentation, JSON output schemas, or error-handling patterns for validate/prepare/combine/promote/complete |
| `examples/promotion-workflows.md` | When the user's request matches a common pattern (single work item promotion, combined promotion, whole-stage promotion, validate-first gate) |
