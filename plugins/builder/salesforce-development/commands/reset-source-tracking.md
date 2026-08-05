---
description: Reset source tracking for the target org — tells the CLI to forget all tracked changes so the next push/pull treats the full org as new state. Destructive on shared sandboxes. Requires explicit confirmation before executing.
allowed-tools:
  - Bash
argument-hint: "[--target-org <alias>]"
---

**WARNING — Destructive operation.** Resetting source tracking tells the SF CLI to forget every tracked change between your local project and the org. After reset:
- A subsequent `sf project deploy push` will treat **all** local metadata as new and deploy everything.
- A subsequent `sf project retrieve start` will treat **all** org metadata as new and retrieve everything.
- On a **shared sandbox**, this can trigger unintended mass deploys or retrieves that overwrite other developers' in-progress work.

Only proceed if you are on a personal scratch org or developer sandbox that you own.

## Workflow

1. **Resolve the target org.** Parse `$ARGUMENTS` for `--target-org <alias>`. If not supplied, find the project's default:
   ```bash
   sf config get target-org --json
   ```
   Extract the `value` field. If no default is set, ask the user: "Which org alias should source tracking be reset for?"

2. **Confirm the target.** Display the resolved alias clearly, e.g.:
   > Target org: **`myDevSandbox`**
   > Resetting source tracking is destructive on shared sandboxes. Type **`yes, reset source tracking for myDevSandbox`** to continue, or anything else to cancel.

   Wait for the user's reply. If the response does not match `yes, reset source tracking for <alias>` (case-insensitive), print "Cancelled — no changes made." and stop.

3. **Execute the reset:**
   ```bash
   sf project reset tracking --target-org <alias> --json
   ```
   Parse the JSON result. On success the `status` field is `0` and `result` is an empty object `{}`.

4. **Report outcome.** On success, print:
   > Source tracking reset for **`<alias>`**. The CLI has cleared its local tracking state.

   On failure (non-zero status or an `error` key in the JSON), surface the error message verbatim so the user can diagnose.

5. **Post-reset guidance.** Recommend previewing the full diff before deploying:
   > Run `sf project deploy preview --target-org <alias> --json` to review everything that will be pushed to the org before you deploy.

## Rules
- Always use `--json` on `sf` commands so you can parse outcomes programmatically.
- Do NOT skip the confirmation gate under any circumstances, even if the user says "just do it".
- Do NOT chain the reset into an immediate deploy or retrieve without a separate user confirmation.
- If the command fails with `SourceTrackingError` or a locked-tracking message, suggest `sf project reset tracking --no-prompt --target-org <alias> --json` as a fallback (this bypasses the CLI's own prompt when one exists), but re-confirm with the user first.
