# Run / Poll / Report — and Cancel

The operational commands for a Data Mask run. Assumes a policy already exists (see
`policy-authoring.md` to create one) and the target org is a **sandbox**.

These map to the two workflows in `SKILL.md`: **Workflow A (mask & report)** uses steps 0–4;
**Workflow B (cancel a run)** uses steps 5–7 and is run only when the request is to abort/cancel.
Pick one by the request — a mask-and-report task does not include a cancel.

Throughout, `<alias>` is the target org, `<policyId>` the `DataMaskPolicy.Id`, `<jobRunId>` the id
returned by the run-start call.

## 0. Confirm sandbox + context
```bash
sf org display --target-org <alias> --json
```
Check `result.isSandbox === true`. Note `result.instanceUrl`. Data Mask run endpoints return `403`
on production.

## 1. Identify the policy
```bash
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, DeveloperName, MasterLabel FROM DataMaskPolicy"
```
Pick the policy that targets the PII you intend to mask (or create one — see `policy-authoring.md`).

## 2. Start the run (REST run API)
```bash
printf '{}' > ./empty-body.json
sf api request rest \
  "/services/data/v67.0/platform/data-resilience/data-mask/policies/<policyId>/run" \
  --method POST --body @./empty-body.json --target-org <alias>
```
`--body` must point at a file containing `{}` **with an `@` prefix** (`--body @./empty-body.json`) —
`sf api request rest` requires a body on POST even though this endpoint takes no payload, and without
the `@` the literal path string is sent as the body (→ `JSON_PARSER_ERROR`). Version must be **`v67.0`+** and there is **no `/connect/`
segment** (either mistake returns `NOT_FOUND`). Sample response (HTTP **200**):
```json
{ "jobRunId": "1aG...", "policyId": "8dm...", "status": "RUNNING", "message": "Job started successfully" }
```
Capture `jobRunId`. A `409`/`CONFLICT` means a run is already active for this policy.

> **Status case differs by surface.** The run API returns **UPPERCASE** status strings
> (`RUNNING`, `CANCELED`), while the `DataMaskPolicyJobRun.Status` SOQL picklist is **lowercase**
> (`running`, `canceled`). Poll for terminal state against the **SOQL** value (lowercase) — that is
> what `scripts/poll-job.sh` checks. `DataMaskPolicy` Ids carry the `8dm` prefix.

## 3. Poll to terminal
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Status, Type, TotalRecords FROM DataMaskPolicyJobRun WHERE Id = '<jobRunId>'"
```
Repeat on a bounded interval until `Status` is one of `completed`, `completed_with_errors`,
`failed`. `scheduled`/`running` are NOT terminal. `scripts/poll-job.sh` automates this with a
timeout.

## 4. Report from the detail object
Per-object masked results live on the child, not the parent:
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DataMaskPolicyJobRunId, Status FROM DataMaskPolicyJobRunDtl WHERE DataMaskPolicyJobRunId = '<jobRunId>'"
```
Report the concrete masked-record count and per-object success/failure from these rows. Do not
report a number you did not read from here.

## 5. Abort the currently-running job — ONLY when the user asked to cancel
Steps 5–7 are the **abort** flow. Run them **only when the prompt explicitly asks to cancel/abort**
a run — a "create and run" or "edit and run" task is complete after step 4.

Aborting is an **on-demand action against a job that is already in progress**: take that job's
`jobRunId` (and note its `DataMaskPolicyId` — you need it to start a replacement run if the window is
missed), wait for `DataMaskPolicyJobRun.Status = running`, and go straight to the abort (step 6).
You can only abort a running job. Do **not** use the terminal poll from step 3 here — it waits until
the job is *done*. Use the poller's `running` mode, which returns the instant the job is abortable:
```bash
POLL_MODE=running bash scripts/poll-job.sh <alias> <jobRunId> 900 15
```
- Exit `0` (prints `running`) → abort now (step 6).
- Exit `3` → the job reached a terminal state before `running` was caught; the window is gone. Start
  a fresh run (step 2, using the policy Id you noted) and poll the new `jobRunId`.
- Exit `1` (timeout) → re-query the job. If still non-terminal, re-run the poller once more; if
  `running`, abort; if terminal, treat as exit 3 (fresh run + poll).

**Only if no job is currently running** (the one you were watching already finished, or you're
reproducing the run→abort flow end-to-end) start a fresh run (repeat step 2) to have a live job to
cancel, poll (`POLL_MODE=running`) until `Status = running`, then abort — targeting that live run,
never an older already-terminal one.

## 6. Abort (REST run API)
```bash
sf api request rest \
  "/services/data/v67.0/platform/data-resilience/data-mask/jobs/<jobRunId>/abort" \
  --method POST --body @./empty-body.json --target-org <alias>
```
- `200` → accepted (response `status: "CANCELED"`, `message: "Job abort requested"`). `409` → not in `running` state.
- Do **not** abort by deleting/updating the `DataMaskPolicyJobRun` row via DML — that is not a real
  cancellation.

## 7. Confirm the abort
Cancellation is asynchronous. Re-query until the status settles:
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Status FROM DataMaskPolicyJobRun WHERE Id = '<jobRunId>'"
```
Only report the abort as successful once `Status = canceled`.

## Failure decision table

| Symptom | Meaning | Action |
|---------|---------|--------|
| run-start `403` | Production org | Data Mask is sandbox-only; switch to a sandbox |
| run-start `409` | Run already active | Poll the existing run or wait |
| abort `409` | Job not `running` | Re-check status; may already be terminal or still `scheduled` |
| abort `200`, SOQL status still `running` | Async cancel in flight | Keep polling until `canceled` |
| run/abort `NOT_FOUND` | Wrong path — `/connect/` segment present or version < v67 | Use `/services/data/v67.0/platform/data-resilience/data-mask/...` (no `connect`) |
| status stuck `scheduled` | Job hasn't picked up yet | Keep polling within the cap; not an error yet |
