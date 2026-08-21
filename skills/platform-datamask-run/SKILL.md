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
  accessCheck:
    - type: userPerm
      value: PermissionsManageDataMaskPolicies
    - type: userPerm
      value: PermissionsAccessDataMaskAndSeed
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
If none targets the Contact PII you need, author one with the **two-step** recipe (the
`DataMaskPolicy` Metadata shape is a thin shell; membership is Tooling-inserted):
1. **Metadata-deploy the thin shell** in **mdapi format** (`--metadata-dir` + `package.xml`; a
   source-format `--source-dir` deploy fails "Could not infer a metadata type"). The shell carries
   only `<label>`, `<description>`, `<runOnRefresh>`. This creates the policy *with an active
   revision*, which A2 requires.
2. **Tooling-insert** the `DataMaskPolicyObject` (one per object) then its `DataMaskPolicyField`
   rows. Each field row's treatment is `MaskingCategory` (`library`) + `MaskValue` (a snake_case
   token like `first_name`, `email`, `phone`). There is **no `MaskingRuleType` column**.

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
reach a terminal state or emit detail rows for several minutes after the run starts. This is fixed
overhead, **not** proportional to row count. Plan the run around it — the single biggest failure mode
is treating the job as instant, polling on a tight interval, and either timing out or writing a
"still pending" report.

Run `scripts/poll-job.sh` as a **single command** — do **not** hand-roll a SOQL poll loop:
```bash
bash scripts/poll-job.sh <alias> <jobRunId>        # defaults: cap 600s (10 min), 20s interval
```
It sleeps on a low-frequency interval, short-circuits the instant a ground-truth detail row appears,
prints the terminal signal (`completed`/`failed`/`canceled`) on stdout, and exits `0` (or `1` on
timeout). **Call it once and read its result — do not wrap it in your own retry loop**, and do not
poll on a sub-10s interval (it just burns tool calls against a job that cannot finish sooner).

**Ground truth is the detail rows, not the parent status.** The parent `DataMaskPolicyJobRun.Status`
can **lag** — it may read `pending`/`running` for a while after masking actually finished. Once a
`total_records_masked` (or `completed`) `DataMaskPolicyJobRunDtl` row exists, the masking is done.
`poll-job.sh` already encodes all of this — the bounded interval and timeout, the short-circuit on
the ground-truth detail row, and the terminal-signal exit code — so you do **not** re-implement any
of it inline. Run the poller once, read its exit signal, then update `report.md` (the stub you wrote
before polling) with the terminal status and the masked count from A5.

### A5. Report results from the job DETAIL object
The parent job carries an overall status; **per-object masked counts live on the child**
`DataMaskPolicyJobRunDtl` (linked by `DataMaskPolicyJobRunId`). Report a concrete count, not a
fabricated one:
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, DataMaskPolicyJobRunId, Status FROM DataMaskPolicyJobRunDtl WHERE DataMaskPolicyJobRunId = '<jobRunId>'"
```

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
the user is asking to cancel. **Capture its `DataMaskPolicyId` too** — you need it to start a
replacement run if the abort window is missed (B2 exit 3 / exit 1). If they just started it, use that
id; otherwise query for the active run:
```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Status, DataMaskPolicyId FROM DataMaskPolicyJobRun ORDER BY CreatedDate DESC LIMIT 5"
```
Note the `DataMaskPolicyId` (`8dm` prefix) of the run you pick — that is the `<policyId>` A3 needs.

### B2. Wait for the job to be `running` (the only abortable state)
You can only abort while `DataMaskPolicyJobRun.Status` is `running`. A `pending`/`scheduled` job
`409`s; a terminal one is already done. Poll for the `running` window with the bundled poller in its
**`running` mode** — it exits the instant the status reads `running` (unlike the default mode, which
waits for a terminal state), so it will not block past the abortable window:
```bash
POLL_MODE=running bash scripts/poll-job.sh <alias> <jobRunId> 900 15
```
The cap is **900s (15 min)**, above the ~5–10 min scheduling floor so a slow-to-start job still gets
caught. Handle every exit:
- **Exit `0`** (prints `running`) → go straight to B3.
- **Exit `3`** → the job raced to a terminal state before `running` was caught; the abort window is
  gone. Start a fresh run against the policy you captured in B1 (A3 with that `<policyId>`), then
  return here and poll the **new** `jobRunId`.
- **Exit `1`** (timeout — the cap expired) → re-query the job's status:
  ```bash
  sf data query --target-org <alias> \
    --query "SELECT Id, Status FROM DataMaskPolicyJobRun WHERE Id = '<jobRunId>'"
  ```
  If it is still non-terminal (`pending`/`scheduled`/`running`), re-run the poller **once** more (same
  command) to continue waiting. If it is `running`, go to B3. If it is terminal, treat it like exit 3
  — start a fresh run (A3 with the B1 `<policyId>`) and poll the new job.

Because of the ~5–10 min pool floor the `running` window is usually minutes wide, so there is time to
catch it; do not poll with no delay.

> **If no run is currently in progress** (the job already completed, or you must reproduce a
> run→cancel flow end to end), start one first with A3, then return here — poll it to `running` and
> abort **that** live job. Never substitute an older, already-terminal job to "show" a cancel; the
> abort must target the run that is actually live.

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
| Never use standard SOQL / `sobject describe` on `DataMaskPolicy*` config objects | They return `INVALID_TYPE` / `NOT_FOUND` — use Tooling API or MDAPI |
| Read masked counts from `DataMaskPolicyJobRunDtl`, never invent them | The child detail is the source of truth for per-object results |
| Only `completed` / `completed_with_errors` / `failed` are terminal | Reporting `running`/`scheduled` as final is wrong |
| Abort only via the run-API abort endpoint | DML/delete on the job record is not a real abort and corrupts state |
| Always re-query status after abort and confirm `canceled` | An abort call returning 200 is not proof the job stopped |
| Data Mask runs on sandboxes only | Run/abort endpoints `403` on production |
| Use API version `v67.0` or later, and no `/connect/` segment | The run/abort endpoints are `/services/data/v67.0/platform/data-resilience/data-mask/...` — a `connect` segment or a pre-v67 version returns `NOT_FOUND` |
| Poll via `scripts/poll-job.sh` (one call), never a hand-rolled SOQL loop | The script caps attempts and short-circuits on the ground-truth detail row; a manual loop against the lagging parent status is the #1 cause of a run timing out with no report |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf sobject describe DataMaskPolicy` → `NOT_FOUND` | It's a Tooling/MDAPI entity — query with `--use-tooling-api`, don't retry standard API |
| `SELECT ... FROM DataMaskPolicy` → `INVALID_TYPE` | Same cause — use Tooling API for the policy; standard API only for `DataMaskPolicyJobRun`/`Dtl` |
| Run start returns `409` | A run is already in progress for that policy — poll the existing one or wait for it to finish |
| Abort returns `409` "status=PENDING" | The job is still `pending`/`scheduled`, not yet `running` — keep polling and abort only once it reads `running`; don't give up on the abort |
| Small job finishes before you can abort it | The `running` window is seconds on a small sandbox — start a fresh run and poll tightly; never substitute a previously-aborted job to fake the flow |
| Abort returns `200` but SOQL status still `running` | Cancellation is async — keep polling the SOQL status until `canceled`; don't report success early |
| Run API says `CANCELED` but SOQL says `running` | Case + surface differ: the run API is UPPERCASE, SOQL picklist is lowercase. Trust the SOQL value for terminal state |
| Job "finished" instantly | Re-check: `scheduled` is not terminal. Poll until a terminal value actually appears |
| Run/abort endpoint `NOT_FOUND` | The path must be `/services/data/v67.0/platform/data-resilience/data-mask/...` — no `/connect/` segment, and version `v67.0`+ (Core 262). See `references/api-surface.md` |

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
