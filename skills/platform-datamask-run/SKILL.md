---
name: platform-datamask-run
description: "Data Mask end-to-end operation on a sandbox: configure a masking policy over PII, run the masking job, poll it to completion, report masked-record results, and abort an in-progress run. Use when the user needs to run, monitor, or cancel a Salesforce Data Mask job, mask PII/sandbox data, or work with DataMaskPolicy / DataMaskPolicyJobRun. TRIGGER when: user runs a data mask job, masks sandbox PII, polls masking status, reports masked records, or aborts a running mask. DO NOT TRIGGER when: writing anonymization Apex by hand (use platform-apex-generate), generating test data (use platform-data-manage), or deploying unrelated metadata (use platform-metadata-deploy)."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "67.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-data-manage"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck: "(UserPermissions.PermissionsManageDataMaskPolicies) && (UserPermissions.PermissionsAccessDataMaskAndSeed)"
---

# platform-datamask-run: Salesforce Data Mask End-to-End Operation

Use this skill to **operate** the Salesforce Data Mask feature on a **sandbox**: configure a
masking policy over PII fields, start a masking job, poll it to a terminal state, report which
records were masked, and abort a run that is still in progress.

Data Mask is **sandbox-only** — the run/abort REST endpoints return `403` on production (a runtime
sandbox guard). Confirm the target org is a sandbox before starting.

## When This Skill Owns the Task

- Running a Data Mask job against a configured policy
- Polling masking-job status to completion
- Reporting masked-record counts / per-object results
- Aborting (canceling) an in-progress masking run
- Creating or identifying the policy the job runs against

Delegate elsewhere when the user is:
- hand-writing anonymization Apex → `platform-apex-generate`
- seeding or generating test data → `platform-data-manage`
- deploying unrelated metadata → `platform-metadata-deploy`

---

## The One Thing to Get Right First: the API surface map

The single biggest failure mode is assuming Data Mask entities are ordinary data-API objects.
**They are not, and the surface differs per entity.** Memorize this table before running anything —
guessing here is what turns a 3-second job into a 30-minute dead end.

| Entity | What it is | How you reach it |
|--------|-----------|------------------|
| `DataMaskPolicy` | The masking policy shell (config) | **Tooling API** or **Metadata API** (thin shell: `<label>`/`<description>`/`<runOnRefresh>` only) — NOT standard SOQL/`sobject describe` |
| `DataMaskPolicyObject` | An object targeted by a policy (holds the optional row filter) | **Tooling API only** — query AND insert; row-subset "sample" runs set `FilterEnabled`+`WhereCriteria` here (no `sampleSize` on the policy) |
| `DataMaskPolicyField` | A field + its masking treatment | **Tooling API only** — query AND insert; treatment cols are `MaskingCategory` + `MaskValue` |
| `DataMaskPolicyJobRun` | The **job** (one masking run) | **Standard SOQL** — `sf data query` works |
| `DataMaskPolicyJobRunDtl` | Per-object **job detail** (child, FK `DataMaskPolicyJobRunId`) | **Standard SOQL** |
| Start a run | — | **REST run API** `POST /services/data/v67.0/platform/data-resilience/data-mask/policies/{policyId}/run` |
| Abort a run | — | **REST run API** `POST /services/data/v67.0/platform/data-resilience/data-mask/jobs/{jobRunId}/abort` |

Concretely:
- `sf sobject describe --sobject DataMaskPolicy` → **`NOT_FOUND`** (don't retry it against standard API)
- `SELECT ... FROM DataMaskPolicy` via `sf data query` → **`INVALID_TYPE`**
- Query the **policy** via Tooling: `sf data query --use-tooling-api --query "SELECT Id, MasterLabel FROM DataMaskPolicy"`
- Query the **job / job-detail** via standard API: `sf data query --query "SELECT Id, Status FROM DataMaskPolicyJobRun"`

Full command reference: `references/api-surface.md`.

---

## Pick the workflow that matches the request

This skill has **two distinct workflows**. Select ONE up front from what the user asked for, then
run **every** step of that workflow — neither has optional steps:

| The user wants to… | Run | Ends when |
|--------------------|-----|-----------|
| Configure/edit a policy and **mask** records; report how many were masked | **Workflow A — Mask & report** (below) | The masked count is reported from the detail rows |
| **Cancel / abort** a masking run | **Workflow B — Cancel a run** (further below) | The job's status is confirmed `canceled` |

Choose by the verb in the request. "Create/edit a policy and run it", "mask the PII", "how many
records were masked" → **Workflow A only**. "Abort", "cancel", "stop the run" → **Workflow B**. A
mask-and-report request does **not** include an abort: do not start a second job to "demonstrate"
cancelling — an unrequested run wastes a full ~5–10 min job (see the pool floor in A4) and is the top
cause of this task running out of turn before it finishes the masked count it *was* asked for.

---

## Workflow A — Mask & report

### A1. Confirm sandbox + capture org context
Verify the org is a sandbox and grab the instance URL + a session token for the run-API calls:
```bash
sf org display --target-org <alias> --json
```

### A2. Identify or create the policy
Prefer reusing an existing policy (fastest, no deploy):
```bash
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, DeveloperName, MasterLabel FROM DataMaskPolicy"
```
If none targets the object and fields you need, choose the fields first (below), then author one.

**Choose the fields from Core's classification, not from field names alone.** Before inserting any
`DataMaskPolicyField` row, call the field-classification operation once per target object and map each
`recommendedPiiType` to a treatment. The steps are in `references/policy-authoring.md` ("Choosing the
fields from Core's classification"). Any recommendation with no verified `MaskValue` token is reported
as unmapped; never guess a `MaskValue`. Use the static table only if the call fails, and say so in the
report.

Then author one with the **two-step** recipe (the
`DataMaskPolicy` Metadata shape is a thin shell; membership is Tooling-inserted):
1. **Metadata-deploy the thin shell** in **mdapi format** (`--metadata-dir` + `package.xml`; a
   source-format `--source-dir` deploy fails "Could not infer a metadata type"). The shell carries
   only `<label>`, `<description>`, `<runOnRefresh>`. This creates the policy *with an active
   revision*, which the Tooling inserts in the next step require.
2. **Tooling-insert** the `DataMaskPolicyObject` (one per object) then its `DataMaskPolicyField`
   rows. Each field row's treatment is `MaskingCategory` + `MaskValue`. For `library`, `MaskValue` is a
   snake_case token like `first_name`, `email`, `phone`. For `characters` and `replaceRandom`, `MaskValue`
   is the field's type group (`Text`, `Date`; Long Text Area is `Text`). There is **no `MaskingRuleType` column**.

> Insert order matters: a Tooling-created parent (no active revision) makes the child insert fail
> `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`. Metadata-deploy the shell first.

See `references/policy-authoring.md` for the full recipe and the `MaskValue` token table. Choose a
`MaskValue` appropriate to each field; do **not** blanket-replace.

### A3. Start the masking run (REST run API)
```bash
printf '{}' > ./empty-body.json
sf api request rest \
  "/services/data/v67.0/platform/data-resilience/data-mask/policies/{policyId}/run" \
  --method POST --body @./empty-body.json --target-org <alias>
```
The endpoint needs an **empty JSON body** (`{}`) — `sf api request rest` requires `--body` on a POST
even when the API takes no payload. **Pass the file with an `@` prefix** (`--body @./empty-body.json`);
without it the literal path is sent as the body and the API returns `JSON_PARSER_ERROR`. A `200` returns `jobRunId`, `policyId`, `status` (the run-API
status is UPPERCASE, e.g. `RUNNING`) and `message: "Job started successfully"`. A `409`/`CONFLICT`
means a run is already in progress for that policy.

> **Write `report.md` NOW, before you poll — do not wait until the end.** The masking job takes
> several minutes (see below), and the single most common way this task scores zero is the turn
> ending during the poll with **no output file written at all**. The instant you have the `jobRunId`,
> write `report.md` with everything known so far (policy Id/label, the run command, the `jobRunId`,
> status `RUNNING`, and a "polling for completion…" placeholder for the masked count). Then **update
> that same file** once the job finishes. A report that exists and says "still running" beats no file;
> a fabricated count is worse than either — only fill the count from the detail rows (A5).

### A4. Poll to a terminal state (standard SOQL)
Poll `DataMaskPolicyJobRun.Status` until it reaches a **terminal** value. Do **not** report a
mid-run status as final.
- Mid-run (pre-work): `pending`, `scheduled` — the job is queued but **not yet abortable**
- Mid-run (working): `running` — this is the **only** state in which abort succeeds
- Terminal: `completed`, `completed_with_errors`, `failed`
- Abort target: `canceled` (single "l")

**`pending` is not `running`.** Abort on a `pending`/`scheduled` job returns `409 CONFLICT`
("Job is not in a running state ... status=PENDING"). You must poll until the status is literally
`running` before you can abort — see Workflow B.

**Jobs are slow — expect several minutes, and poll with the bundled script.** Data Mask runs on a
backend pool/scheduler with a **~5–10 minute floor**: even a tiny (20-row) job usually does **not**
reach a terminal state or emit detail rows for several minutes. This is fixed overhead, **not**
proportional to row count. The biggest failure mode is treating the job as instant, polling tightly,
and either timing out or writing a "still pending" report.

Run `scripts/poll-job.sh` as a **single command** — do **not** hand-roll a SOQL poll loop:
```bash
bash scripts/poll-job.sh <alias> <jobRunId>        # defaults: cap 600s (10 min), 20s interval
```
It sleeps on a low-frequency interval, prints the terminal status (`completed` /
`completed_with_errors` / `failed` / `canceled`) on stdout, and exits `0` (or `1` on timeout).
**Call it once and read its result — do not wrap it in your own retry loop**, and do not poll on a
sub-10s interval (it just burns tool calls against a job that cannot finish sooner).

**The job is done only when the parent `DataMaskPolicyJobRun.Status` is terminal.** A
`DataMaskPolicyJobRunDtl` row is not a completion signal: a `total_records_masked` row can already
exist, reading `0`, while the parent is still `running`, so a count read mid-run is wrong. Wait for
the poller to exit `0`, then read the detail rows (A5) and update the `report.md` stub with the
terminal status and the masked count.

### A5. Report results from the job DETAIL object
The parent job carries an overall status; **per-object masked counts live on the child**
`DataMaskPolicyJobRunDtl` (linked by `DataMaskPolicyJobRunId`). `DataMaskPolicyJobRunDtl` has **no
`Status` column** — the status lives in `Type`/`Subtype`, with the count itself in `Value` (a
string). Report a concrete count, not a fabricated one:
```bash
sf data query --target-org <alias> \
  --query "SELECT ObjectReference, Type, Subtype, Value FROM DataMaskPolicyJobRunDtl WHERE DataMaskPolicyJobRunId = '<jobRunId>' ORDER BY Timestamp"
```
Expect one `status_update` row per `Subtype` (`loaded`, `completed`, `total_records_masked`) for
each target object; `total_records_masked`'s `Value` is the masked count.

**Report only what the rows literally show — do not overstate granularity.** The detail rows are
**object-level** status_update entries (`loaded`, `completed`, `total_records_masked` for the object,
e.g. Contact). They are **not** per-field rows. So state per-object success as an observed fact
("Contact: 27/27 records masked, 0 error rows"), but frame field-level success as an **inference**,
not a direct observation — say "no field-level error rows were returned, so no field is reported as
failed", **not** "all 5 fields succeeded" (the data does not carry a per-field success row to back
that claim). Overstating an inference as an observation is the most common factuality miss here.

---

## Workflow B — Cancel a run

Use this workflow when the request is to **abort/cancel** a masking run. It targets the run that is
**currently in progress** — aborting is an on-demand action against a live job; nobody starts a job
just to cancel it. Steps B1–B4 are all required.

### B1. Confirm sandbox + identify the run to cancel
Confirm the org is a sandbox (`sf org display`) and get the `jobRunId` of the run to abort — the one
the user is asking to cancel. **Capture its policy Id too** — you need it to start a replacement run
if the abort window is missed (B2 exit 3 / exit 1). If they just started it, use that policy id
directly; otherwise query for the active run:
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Status, PolicyName FROM DataMaskPolicyJobRun ORDER BY CreatedDate DESC LIMIT 5"
```
`DataMaskPolicyJobRun` has **no `DataMaskPolicyId` lookup field** — the only link back to the policy
is the human-readable `PolicyName` (`MasterLabel`). Resolve the Id from it via the Tooling API:
```bash
sf data query --use-tooling-api --target-org <alias> \
  --query "SELECT Id, DeveloperName FROM DataMaskPolicy WHERE MasterLabel = '<PolicyName>'"
```
That `Id` (`8dm` prefix) is the `<policyId>` A3 needs.

### B2. Wait for the job to be `running` (the only abortable state)
Poll with `POLL_MODE=running` (cap 900s, 15s interval). Full command, exit-code handling (0 / 3 / 1),
and the re-query-on-timeout steps are in `references/run-and-abort.md` section 5. A `pending` or
`scheduled` job `409`s on abort, so do not abort until the poller exits `0`.

If no run is in progress, start one with A3 and abort **that** live job. Never substitute an older,
already-terminal job to "show" a cancel.

### B3. Abort via the run API
Abort via the run API — **not** by DML/delete on the job record:
```bash
sf api request rest \
  "/services/data/v67.0/platform/data-resilience/data-mask/jobs/{jobRunId}/abort" \
  --method POST --body @./empty-body.json --target-org <alias>
```
Empty JSON body (`{}`) via the `@`-prefixed file, as above. A `200` returns `status: "CANCELED"`
(uppercase, from the run API) and `message: "Job abort requested"`. A `409` means the job was not in
a `running` state (usually still `pending`/`scheduled`) — return to B2 and resume polling.

### B4. Confirm and report the cancellation
Cancellation is asynchronous. **Re-query** `DataMaskPolicyJobRun` and confirm `Status = canceled`
(lowercase, from SOQL) before reporting the abort succeeded. Verify:
- [ ] Confirmed the abort targeted the live job while its queried status was `running`.
- [ ] Re-queried `DataMaskPolicyJobRun` after the abort and saw `Status = canceled`.

---

## High-Signal Rules

| Rule | Rationale |
|------|-----------|
| Run each `sf` command **bare** — never add a pipe or redirect of any kind (`\|`, `\| python3`, `\| grep`, `2>&1`, `2>/dev/null`, `> file`) | `sf ... --json` already prints clean JSON on stdout; read it directly. A redirect/pipe trips an unbypassable shell-safety guard that silently stalls the whole run to timeout. Never post-process with `python3`/`grep`/`jq`, and never suppress stderr — even if a command prints a warning, the `--json` payload on stdout is still valid; just parse it as-is |
| Abort only via the run-API abort endpoint | DML/delete on the job record is not a real abort and corrupts state |
| Use API version `v67.0` or later, and no `/connect/` segment | The run/abort endpoints are `/services/data/v67.0/platform/data-resilience/data-mask/...` — a `connect` segment or a pre-v67 version returns `NOT_FOUND` |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Small job finishes before you can abort it | The `running` window is seconds on a small sandbox — start a fresh run and poll tightly; never substitute a previously-aborted job to fake the flow |
| Run API says `CANCELED` but SOQL says `running` | Case + surface differ (run API UPPERCASE, SOQL lowercase). Trust the SOQL value for terminal state |
| Run start returns `409` or abort `409` | Run start: a run is already active for that policy. Abort: the job is not `running` yet. Details in `references/run-and-abort.md` failure table |

---

## Output Format

Report the sections for **the workflow you ran** — do not add sections for the other one. **Keep it
tight — show each command once, at the step it belongs to; do not append a second "full command log"
that repeats calls already shown.** Prefer a compact table over prose; a reader should reach the key
result in the first screenful.

**Workflow A (mask & report):**
1. **Policy used** (Id + label, and whether reused or created)
2. **Run** — job Id, final terminal status, masked-record count (from the detail object). Collapse
   the poll loop to one line (e.g. "polled 5×, `running`→`completed`"); do not print a row per poll.
3. **Per-object results** — from `DataMaskPolicyJobRunDtl`. Report the object-level counts the rows
   actually carry; if there are no field-level error rows, say so as an inference ("no field-level
   errors reported"), not as a claimed per-field success. See A5 for the exact phrasing.
4. **Commands run** — already shown inline above; here just list any not yet shown. Do **not**
   re-paste the full sequence a second time.

**Workflow B (cancel a run):**
1. **Job cancelled** — the job Id, that it was `running` when aborted, that the abort was issued via
   the run-API abort endpoint, and the re-queried `canceled` status.
2. **Commands run** — as above, no re-pasting.

**Accuracy notes that keep factuality high:**
- The run/abort REST response returns a **15-character** `jobRunId` (e.g. `1aGXK0000000uob`); SOQL
  returns the **18-character** form of the same record (e.g. `1aGXK0000000uob2AA`). They are the
  **same job** — when both appear, note that rather than presenting them as two IDs.
- Do not assert a masked count, a per-field outcome, or a terminal status you did not actually query.
  Every number in the report must trace to a query result shown in the command log.

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|------|-------------|--------|
| Seed realistic PII records to mask | [platform-data-manage](../platform-data-manage/SKILL.md) | Test-data creation |
| Author custom anonymization Apex | [platform-apex-generate](../platform-apex-generate/SKILL.md) | Apex authoring |
| Deploy the policy metadata to the org | [platform-metadata-deploy](../platform-metadata-deploy/SKILL.md) | Metadata deployment |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/api-surface.md` | Exact per-entity API surface, all CLI commands, run/abort REST endpoints, and status picklist values |
| `references/policy-authoring.md` | Two-step authoring recipe (MDAPI thin shell → Tooling object/field inserts) and the `MaskingCategory`/`MaskValue` treatment table |
| `references/run-and-abort.md` | The run → poll → report → re-run → abort sequence in full, with sample responses |
| `scripts/poll-job.sh` | Bounded poller: waits for a terminal status (default) or, with `POLL_MODE=running`, for the abortable `running` window |
