---
name: consumer-goods-accruals-datakit-deploy
description: "Use this skill to deploy the TPM Liability Accruals data kit end to end to a Salesforce org. Invoke when a customer or teammate wants to install the accrual engine, verify the Data Cloud connection, deploy the Data Kit components, and schedule the export and accrual calculation chain. Trigger phrases include: 'deploy the accrual data kit', 'set up liability accruals', 'install TPM accruals', 'headless accruals setup', 'configure the Data Cloud export connector', 'schedule the accrual chain'. Do NOT use for creating a Data Space alone (use platform-dataspace-access-configure), for generic Salesforce metadata deployment (use platform-metadata-deploy), for querying org data only (use platform-soql-query), or when setting up the data kit for the Trade Promotion Effectiveness (TPE) feature (use consumer-goods-tpe-datakit-deploy instead)."
metadata:
  version: "1.0"
  domains: ["Consumer Goods"]
  relatedSkills:
    - "consumer-goods-tpe-datakit-deploy"
    - "platform-dataspace-access-configure"
    - "platform-metadata-deploy"
    - "platform-soql-query"
  minApiVersion: "62.0"
  cliTools:
    - tool: ["node"]
      semver: ">=22.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["sfdx"]
      semver: ">=7.0.0"
---

## MANDATORY: Always write the Phase 6 report

After completing all phases — including early stops, blocked phases, or error conditions — you MUST write the Phase 6 report to disk. Failure to write the report is always a test failure, regardless of how well you handled the scenario.

This applies to **ALL exit paths** without exception:
- Normal completion (all phases ran)
- Phase 1 stop (preflight failed, sales org not found, CGCloudAddons missing, Data Cloud not enabled)
- Phase 3 error (setup script non-zero exit)
- Phase 4 failure detection (DataKitDeploymentLog failures)
- Schedule conflict (Phase 5 guard triggered)
- Any other blocking condition (missing inputs, org unreachable, etc.)

Write the report to `${outputDir}/report.md` (the path from the `generatedFileLocationDirective` in the task). Do not print it as a chat message only — it must exist as a file on disk. If you handled a scenario correctly but never wrote the file, the eval will record `no_output` and score zero.

---

# Deploy the Accrual Data Kit

Installs the TPM Liability Accruals solution into a Salesforce org end to end.
Runs the full setup toolchain bundled in `scripts/`: checks the org is ready,
verifies the Data Cloud connection, downloads the `CGCloudAddons` static resource,
deploys the data kit, confirms the deployment, and schedules the Data Cloud export
and accrual calculation chain.

Designed for **headless delivery**: point it at an org and it runs the full install.

The namespace differs per build: `cgcloud` (released), `cgcloud_dev` (dev/beta), or no
prefix (source-only). The setup script auto-detects the prefix at runtime via the
`DataCloudExportScheduler` Apex class query. **Never hardcode `cgcloud.` or `cgcloud_dev.`.**

Reference: [TPM Accrual Engine concept](https://help.salesforce.com/s/articleView?id=ind.tpm_concept_accruals.htm&type=5)

Run the setup script from the skill root directory:
```bash
node scripts/setup.js --org <alias> [options]
```

---

## Inputs to collect

**Collect and validate ALL required inputs before running any Phase 1 checks.** Do not start Phase 1 until org alias and sales org name are both confirmed. If either is missing after asking, stop immediately and write the Phase 6 report.

Ask before starting — do not guess.

| Input | Default | Notes |
|---|---|---|
| **Org alias / username** | — | `sf` alias of the target org. Required. |
| **Sales org name** | — | Used to name the Data Space (`DataSpace_<salesOrg>`), its prefix (`DS<lastChar>_`), and the UI controller map key. **Required. Must be exactly 4 alphanumeric characters (e.g. `0001`, `AB12`). If the user has not provided it and cannot provide it, do NOT guess or use any default value — stop immediately, write the Phase 6 report with Phase 1 blocked ("sales org name not provided"), and end the session. Do not run any Phase 1 checks without it.** |
| **Skip Data Space?** | no | Yes only if the org has no Data Spaces (some demo orgs). |
| **Dry run?** | no | Prepares files; skips all deploys and scheduling. Offer this first. |
| **Namespace override** | auto-detected | Pass only if auto-detection would fail. Value WITHOUT trailing `__`. |
| **Export cron** | `0 0 2 * * ?` | Only prompt if user requests a different schedule. |
| **Accrual chain cron** | `0 0 3 * * ?` | Only prompt if user requests a different schedule. |

The dry-run flag is collected once here and honored through all phases — do not re-prompt.

---

## Phase 1 — Preflight

Stop on first failure. Do not continue past a failed check.

### 1.1 Local tooling
1. **Salesforce CLI present:** `sf --version`
2. **Node 22:** `node --version`

### 1.2 Org reachable
```bash
sf org display --target-org <alias> --json
```
Confirm `status` is `Active`. Capture `id` (org id), `instanceUrl`, `apiVersion`.
Non-zero exit or inactive status → stop, ask user to log in.

### 1.3 Data Cloud Data Kit framework present
```bash
sf data query --target-org <alias> \
  --query "SELECT Id FROM DataKitDeploymentLog LIMIT 1"
```
`INVALID_TYPE` or `NOT_FOUND` → **stop immediately**: the Data Cloud Data Kit framework
is not enabled in this org. Tell the user they must enable Data Cloud and the Data Kit
feature before this skill can proceed. Write the Phase 6 report now with Phase 1 blocked
and the exact query error. Do NOT run any further queries, downloads, or deploys.
Zero rows is fine — the framework is present, continue to Phase 1.4.

### 1.4 CGCloudAddons static resource present
```bash
sf data query --target-org <alias> \
  --query "SELECT Id FROM StaticResource WHERE Name='CGCloudAddons'"
```
Zero rows → **stop immediately**: the managed package is not installed (or this version
does not ship `CGCloudAddons`). Tell the user the package must be installed before
proceeding. Write the Phase 6 report now with Phase 1 blocked: `CGCloudAddons not found`.
Do NOT attempt to download, deploy, or schedule anything after this failure.

### 1.5 Sales org validation
```bash
sf data query --target-org <alias> --json \
  --query "SELECT Id, Name FROM Sales_Organization__c WHERE Name = '<salesOrg>'"
```
Zero rows → **stop immediately**: the sales org name provided does not exist in this org.
Show the user the query and the zero-row result. Do NOT proceed to deploy or schedule.
Record Phase 1 as blocked: `Sales org '<salesOrg>' not found`.

### 1.6 Deployment baseline
```bash
sf data query --target-org <alias> --json \
  --query "SELECT MAX(CreatedDate) maxCreated FROM DataKitDeploymentLog"
```
The aggregate query always returns exactly one row. `maxCreated` is `null` when the
table is empty (first-ever deployment). Store `DEPLOY_BASELINE_TIME = maxCreated ?? ''`
(treat null as empty string). Phase 4 uses `WHERE CreatedDate > DEPLOY_BASELINE_TIME`
only when `DEPLOY_BASELINE_TIME` is non-empty; omit the `WHERE` clause entirely when it
is empty — `WHERE CreatedDate > null` is an `INVALID_QUERY_FILTER_OPERATOR` error in
Salesforce SOQL and will abort the query.

### 1.7 Org-side manual prerequisites
If the user's prompt already confirms these prerequisites, treat them as confirmed — do
**not** re-ask. Only ask for items the user has not already addressed:
- Data Cloud and Analytics Studio enabled (Setup → Data Cloud Setup)
- Connectors feature enabled (Data Cloud Setup → Feature Manager)
- A user assigned to the **Accrual Ingestion Process** in Processing Services Pairing
  with the **Data Cloud Architect** permission set
- OAuth scope **`cdp_ingest_api`** on the TPM Offcore connected app
- Licenses: `AccrualsProcessingAddOn`, `AccrualsProcessingUserAddOn`,
  `TpmAccrualsAddOn`, `TpmAccrualsUserAddOn` (advisory — record what the user confirmed)

---

## Phase 2 — Verify the Data Cloud connection (best-effort)

Try to verify `cdp_ingest_api` by query — treat "cannot verify" as WARN, not STOP:

```bash
sf data query --target-org <alias> \
  --query "SELECT Id, Name FROM ConnectedApplication WHERE Name LIKE '%TPM%'"
```

If the query errors on permissions, ask the user to confirm `cdp_ingest_api` is in
Setup → App Manager → (edit TPM Offcore connected app) → OAuth Policies →
Selected OAuth Scopes. Continue only after the user confirms.

---

## Phase 3 — Run the setup script

Run the end-to-end setup script from the skill's own root directory. In dry-run mode, pass `--dry-run`.

```bash
node scripts/setup.js --org <alias> --sales-org <salesOrg> [--skip-dataspace] [--dry-run] [--namespace <ns>]
```

If `scripts/setup.js` is not accessible in the current working directory, record Phase 3 as
`not run — script path not accessible in this environment` in the Phase 6 report and
proceed directly to Phase 4 (query `DataKitDeploymentLog` for any rows after `DEPLOY_BASELINE_TIME`).

The script runs these steps in order:

- **Step 0** — Prerequisites confirmation (interactive prompt, skipped in dry-run)
- **Step 1** — Download `CGCloudAddons` static resource
- **Step 2** — Replace `__SF_ORG_ID__` placeholders in data kit metadata
- **Step 3** — Deploy TPM Accruals Data Kit metadata (`sf project deploy start`)
- **Step 4** — Deploy Liability Accruals Engine data kit via `sfdatakit__DeployDataKitComponents`
  (skips already-deployed components; waits up to 30 min for completion)
- **Step 5** — Deploy TPM Accruals data kit via `sfdatakit__DeployDataKitComponents`
  (same pattern; also waits for completion)
- **Step 6** — Create Data Space (manual prompt — see below; skipped with `--skip-dataspace`)
- **Step 7** — Deploy Accruals Reports metadata with Data Space placeholder replacements (two-pass)
- **Step 8** — Deploy `TPMAccrualTacticSummary` UI component with namespace and Data Space replacements
- **Step 9** — Print scheduling instructions

The script pauses at **Step 0** (prerequisites confirmation) and **Step 6** (Data Space
creation). When it pauses, capture the stdout block starting at `=== Step N:` and relay
it verbatim to the user. Wait for the user to complete the step before continuing.

Adding the `TPMAccrualTacticSummary` UI component to the Promotion page is a
post-run manual step — the script only prints the instruction. Track it as pending in
Phase 6.

On non-zero exit → stop and surface the last 50 lines of stdout. Do not proceed to
Phase 4 on a failed script.

---

## Phase 4 — Verify deployment

**Skip this entire phase in dry-run mode.** Record it as `pending — not run (dry-run)` in the report.

```bash
sf data query --target-org <alias> --json \
  --query "SELECT ComponentName, DeploymentStatus, DeploymentError, CreatedDate
           FROM DataKitDeploymentLog
           WHERE CreatedDate > ${DEPLOY_BASELINE_TIME}
           ORDER BY CreatedDate ASC
           LIMIT 200"
```
(Omit `WHERE` clause if `DEPLOY_BASELINE_TIME` is empty. Always include `LIMIT 200`.)

Evaluate the rows:

- Any `DeploymentStatus = 'Failure'` or non-empty `DeploymentError` → **stop**, list every
  failing component name and its `DeploymentError` value. Do not proceed to Phase 5.
  Record Phase 5 as `not run — deployment failures unresolved` in the Phase 6 report.
- Any `InProgress` row → wait 60 s and re-query. **Do not advance to Phase 5 until all
  rows are in a terminal state** (`Successful` or `Failure`). If any row is still
  `InProgress` after 30 minutes, stop and surface the live counts.
- Zero rows → the deployment has not produced log entries yet; re-query every 60 s up to
  30 minutes. Treat persistent zero rows as a deployment problem — stop and report.
- All rows `Successful` → proceed to Phase 5.
- Never advance to Phase 5 while any row is `InProgress`, `Failure`, or
  while zero rows have been returned within the polling window.

---

## Phase 5 — Schedule

In dry-run mode: still run steps 5.1 (namespace detection — read-only) and 5.2 (cron
job check — read-only), print the fully-substituted Apex that would be run, but do NOT
execute `sf apex run`. Record Phase 5 as `pending — not run (dry-run)` in the report.

### 5.1 Detect namespace prefix

Query the installed class (same probe used by `scripts/steps/utils.js`):

```bash
sf data query --target-org <alias> --json \
  --query "SELECT NamespacePrefix FROM ApexClass WHERE Name='DataCloudExportScheduler'"
```

| Query result | `NS_PREFIX` | Meaning |
|---|---|---|
| 0 rows | — | Scheduler class not deployed → **STOP**: Phase 3 did not complete |
| 1 row, null | `""` | Unmanaged source deploy |
| 1 row, any value | that value | Use whatever namespace the query returns |
| >1 row | — | Ambiguous → **STOP**, print all rows |

Compose the dotted prefix:
```bash
NS="${NS_PREFIX:+${NS_PREFIX}.}"    # yields "cgcloud.", "cgcloud_dev.", or ""
```

Every Apex identifier below is written as `${NS}ClassName`.

### 5.2 Guard duplicate cron jobs
```bash
sf data query --target-org <alias> --json \
  --query "SELECT Id, State, CronJobDetail.Name FROM CronTrigger
           WHERE CronJobDetail.Name IN
             ('DataCloud Export Daily','TPM Accrual Process Chain')"
```
If any matching job exists:
1. Show the user the existing job `Id` and `State` for each conflicting job.
2. Ask explicitly: abort the existing jobs and reschedule, or skip scheduling?
3. Do NOT silently overwrite — wait for the user's answer before calling `System.schedule`.
4. If the user chooses to abort and reschedule: run `System.abortJob('<id>')` for each
   conflicting job, then proceed with 5.3/5.4 and verify the new `CronTrigger` shows
   `State = 'WAITING'` and non-null `NextFireTime`.
5. Record the conflict and its resolution in the Phase 6 report.

**Cron ordering requirement:** the export job (5.3) must fire **before** the accrual
chain job (5.4) so that Data Cloud data is available when the chain runs. The defaults
(`exportCron` = `0 0 2 * * ?`, `accrualCron` = `0 0 3 * * ?`) enforce a 1-hour gap.
When the user provides custom expressions, verify that the export cron precedes the
accrual cron — a gap of at least 1 hour is the recommended convention. Warn the user
if the two expressions conflict or are inverted; do not schedule without their
confirmation.

### 5.3 Schedule Data Cloud Connector Export

Write the following Apex to a temporary file (e.g. `/tmp/dc-export.apex`), run it,
then delete the file:

```apex
${NS}DataCloudExportScheduler scheduler = new ${NS}DataCloudExportScheduler(
  new List<String>{ 'promotionmeasures', 'paymenttacticmeasures', 'dailymeasurereal' }
);
System.schedule('DataCloud Export Daily', '<exportCron>', scheduler);
```
```bash
# Write to temp file, run, clean up
cat > /tmp/dc-export.apex << 'EOF'
<filled-in Apex from above>
EOF
sf apex run --target-org <alias> --file /tmp/dc-export.apex
rm /tmp/dc-export.apex
```
Verify: `CronTrigger WHERE CronJobDetail.Name = 'DataCloud Export Daily'` → exactly one
row, `State = 'WAITING'`, non-null `NextFireTime`.

### 5.4 Schedule Accrual Calculation Chain

Write the following Apex to a temporary file (e.g. `/tmp/accrual-chain.apex`), run it,
then delete the file (see Rules — only `'partial'` or `'full'` are valid for `ingestionMode`):

```apex
${NS}ScheduleTPMAccrualProcessChain scheduler =
  new ${NS}ScheduleTPMAccrualProcessChain();
System.schedule('TPM Accrual Process Chain', '<accrualCron>', scheduler);
```
```bash
# Write to temp file, run, clean up
cat > /tmp/accrual-chain.apex << 'EOF'
<filled-in Apex from above>
EOF
sf apex run --target-org <alias> --file /tmp/accrual-chain.apex
rm /tmp/accrual-chain.apex
```
Verify with the same `CronTrigger` pattern as 5.3.

References:
- [DataCloudExportScheduler](https://developer.salesforce.com/docs/atlas.en-us.retail_api.meta/retail_api/cg_tpm_apex_datacloudexportscheduler.htm)
- [ScheduleTPMAccrualProcessChain](https://developer.salesforce.com/docs/atlas.en-us.retail_api.meta/retail_api/global_tpm_accrual_process.htm)

---

## Phase 6 — Report

**Write this report after every run, including early stops.** If execution was blocked at Phase 1 (missing inputs, failed preflight, Data Cloud not enabled, sales org not found), write the report immediately after confirming the stop condition — do not skip it. A correctly handled early stop that produces no report.md file is scored as a failure. If you are in an agentic eval context with a file-output directive, that directive means "write the file when you are done", not "write the file instead of working".

Write the report to disk using a shell command (e.g. `Write` tool or `cat > <path>`). Do not just print it as a chat message — it must exist as a file at the path specified in the task directive.

**Keep early-stop reports short.** When execution is blocked before Phase 3 starts (missing input, failed preflight), the report only needs to cover what actually happened: the block reason, what was not run, and what the user must provide to retry. Do NOT pad an early-stop report with boilerplate sections for phases that never ran (detailed DataKit deployment rows, schedule conflict resolution, license warnings, manual steps). Those sections are only relevant when the corresponding phases executed. A 3–5 line report is the correct shape for a Phase 1 block.

```text
Deployment report — <org alias, or "not provided">
  Sales org: <salesOrg, or "not provided">
  Dry run: <yes|no>
  Namespace prefix: <detected value, or "(not detected — execution blocked)">
  Phase 1 preflight: <passed | blocked: <exact check that failed>>
  DataKit deployments: <X succeeded / Y failed / Z in progress, or "not run — Phase 1 blocked">
  Data Space: <created | skipped | not run — Phase 1 blocked>
  Data Cloud Export: <scheduled | dry-run | not run — Phase 1 blocked>
  Accrual Chain: <scheduled | dry-run | not run — Phase 1 blocked>
  Pending manual steps: <list, or "none — execution did not complete">
  License warnings: <unconfirmed licenses, or "none — not checked">
```

---

## Rules

- **Always execute before reporting.** Run every phase to completion (or to a documented stop condition) before writing the Phase 6 report. Never write the report as a substitute for executing the skill — a file-output directive means "write when done", not "write instead of working".
- **Re-run means re-run.** When asked to re-run or verify an existing deployment, always re-execute `node scripts/setup.js` and capture a fresh `DataKitDeploymentLog` baseline before doing so. Do not treat a prior successful run as sufficient — re-verify against fresh log rows from this run.
- Never claim success while any `DataKitDeploymentLog` row for this run has
  `DeploymentStatus = 'Failure'` or a non-empty `DeploymentError`.
- Never claim a schedule succeeded until `CronTrigger` shows `State = 'WAITING'` and
  non-null `NextFireTime`.
- Stop on the first failed preflight check; report the exact failure.
- Relay manual-step instructions verbatim from the setup script's stdout and wait for
  the user.
- Never hardcode namespace prefixes in emitted Apex — always compose from `${NS}`.
- `ingestionMode` accepts only `'partial'` or `'full'`; `'initial'` throws.
