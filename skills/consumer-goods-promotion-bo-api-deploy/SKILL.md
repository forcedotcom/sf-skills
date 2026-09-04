---
name: consumer-goods-promotion-bo-api-deploy
description: "Use to enable the Consumer Goods Cloud TPM Promotion Business Object (BO) API framework in a Salesforce org, interview the user for the custom Workflow Step they want to add, generate and deploy that Apex class, wire it into the create/update/copy workflows, and prove it end-to-end via headless REST ingest. Ships a worked reference example (SetCommentValue) but the customization is user-supplied per org. Triggers on \"deploy the promotion BO API\", \"set up promotion BO API\", \"headless promotion create\", \"add a BO API workflow step\"."
metadata:
  version: "1.0"
  domains: ["Consumer Goods"]
  minApiVersion: "60.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["node"]
      semver: ">=20.17.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: license
      value: "CGCRetailAndTPMMgmtPsl"
---

# Deploy the Promotion BO API

## What this does

Turns on the Consumer Goods Cloud TPM Promotion Business Object (BO) API in a
Salesforce org, interviews the user for **one custom Workflow Step** to add to
the promotion pipeline, generates and deploys that Apex class, registers it
against a BO API entity, wires it into the customer's chosen subset of
`{create, update, copy}` workflows, then proves the whole path end-to-end via
three REST endpoints:

- `POST /services/apexrest/<prefix>/promotions/initialize`
- `POST /services/apexrest/<prefix>/promotions/ingest`
- `GET  /services/apexrest/<prefix>/promotions/status?importId=...`

It is meant for **headless delivery**: point it at an org, answer the interview,
and the skill installs the step and verifies it. The Promotion BO API ships in
the CGCloud **managed package** (namespace `cgcloud` released, `cgcloud_dev`
dev/beta). Every Apex identifier, object/field API name, and REST URL is derived
from the detected package prefix at runtime — this skill never hard-codes it.

`derive` is out of scope here (a follow-up skill covers it). Detailed runbooks
for the write and smoke phases live under `references/`:

- `references/conventions-and-payload-rules.md` — sales-org partitioning, schema-first contract derivation, and the eight cross-workflow payload rules R1–R8.
- `references/generate-and-wire.md` — Phase 5a (generate + deploy the class) and Phase 5b (register + wire the step), with the full `register-step.apex`.
- `references/smoke-and-verify.md` — Phase 6 (contract derivation, payload materialization, create/update/copy legs + verification).
- `references/reference-example-set-comment-value.md` — the shipped `SetCommentValue` preset (assets at `assets/set-comment-value/`).

## Inputs to collect first

Ask before starting; do not guess.

1. **Org alias** — the `sf` alias of the target org. Required.
2. **Sales org** — required pre-parameter, default `0001`. Must be 4 chars, uppercase (mirrors `TPMSetupData.validateSalesOrg`). **Every** downstream lookup (promotion template, tactic template, anchor account, product filter criteria, SKUs) is scoped to this sales org — see `references/conventions-and-payload-rules.md` ("Sales-org partitioning").
3. **Yes to seeding?** — Phase 3a fetches the packaged BO API seed and asks for confirmation before inserting ~232 rows across 8 objects. Offer `--yes` for CI callers.
4. **Dry run?** — `--dry-run` runs Phases 1, 2, 3a-preview, the Phase 5 interview, and a validate-only deploy. Writes nothing.

What the customization *is* gets collected in Phase 5's interview, once the
framework state is known.

## Find the namespace first

The prefix depends on the installed build — detect it, do not guess. Released
package → `cgcloud`; dev/beta → `cgcloud_dev`; source-deployed → no prefix.

```bash
sf data query --target-org <alias> \
  --query "SELECT NamespacePrefix FROM ApexClass WHERE Name = 'TPMSetupData'" --json
```

Read `records[0].NamespacePrefix` and bind three variables used everywhere below:

- `PREFIX_DOT` — Apex references: `cgcloud.` / `cgcloud_dev.` / empty.
- `PREFIX_UNDER` — object/field API names: `cgcloud__` / `cgcloud_dev__` / empty.
- `URL_NS` — REST paths: `/cgcloud` / `/cgcloud_dev` / empty.

Every Apex call is `${PREFIX_DOT}ClassName.method(...)`; every SOQL object/field is
`${PREFIX_UNDER}Object__c`; every REST URL is
`/services/apexrest${URL_NS}/promotions/<endpoint>`. Substitute at run time.

## Phase 1 — Preflight

Run these and stop on the first failure.

1. `sf --version`; `node --version` (only if running shipped scripts).
2. `sf org display --target-org <alias> --json` — confirm reachable, capture `instanceUrl` + org id (for display/logging only). Every REST call in later phases goes through `sf api request rest`, which uses the CLI's stored session — this skill never extracts the access token.
3. Validate the sales org locally: length 4, uppercase, non-blank (mirrors `TPMSetupData.validateSalesOrg`). Fail fast instead of surfacing an Apex stack trace.
4. **TPM entitlement (Permission Set License)** — the TPM app is licensed through the **`CGCRetailAndTPMMgmtPsl`** Permission Set License ("CGC Retail and Trade Promotion Management"); there is **no** `TPM App` UserLicense. Check the running user's PSL assignment:
   ```sql
   SELECT Id FROM PermissionSetLicenseAssign
    WHERE Assignee.Username = '<running-user-name>'
      AND PermissionSetLicense.DeveloperName = 'CGCRetailAndTPMMgmtPsl'
   ```
   On scratch/dev-hub the PSL may be legitimately unassigned; detect env with `SELECT OrganizationType, IsSandbox FROM Organization`:
   - `OrganizationType = 'Developer Edition'` OR `IsSandbox = true` and empty → **warn** ("permset gate below is the real check"), continue.
   - Any other org shape and empty → **stop** ("TPM Permission Set License `CGCRetailAndTPMMgmtPsl` not assigned to the running user").
5. **Running-user permission set (TPM Admin persona)** — the setup needs a permission set granting the *TPM Master Data Admin* persona. The shipped permset is `TPM_Master_Data_Admin` (packaged; `PermissionSet.Name` is the bare name regardless of namespace), but **customers frequently clone it** under their own name — so treat a miss as "ask", not "fail". Take `<running-user-name>` from `sf org display ... .result.username`:
   ```sql
   SELECT PermissionSet.Name, PermissionSet.Label FROM PermissionSetAssignment
    WHERE Assignee.Username = '<running-user-name>'
      AND (PermissionSet.Name = 'TPM_Master_Data_Admin'
           OR PermissionSet.Label LIKE '%TPM%Master Data Admin%')
   ```
   Match → proceed. No match → **do not hard-fail on the name**: show `sf org assign permset --name TPM_Master_Data_Admin --target-org <alias>` as the default option, but also ask the user to confirm whether they already hold an equivalent (possibly cloned/renamed) permission set for the TPM admin persona. Pause, wait for a cloned-permset confirmation or the assignment, then re-query. Proceed only once admin access is confirmed.
6. Namespace discovery (above).

## Phase 2 — Verify BO API framework state

Read-only; tells you whether Phase 3 needs to run. All three counts MUST be
scoped to `<salesOrg>` — the framework rows are sales-org-partitioned.

```bash
# 1. Workflow rows for this sales org (expect 4: create/update/copy/derive)
sf data query --target-org <alias> --json --query "
  SELECT Name FROM ${PREFIX_UNDER}BO_API_Workflow__c
   WHERE ${PREFIX_UNDER}BO_API__r.Name = 'Promotion'
     AND ${PREFIX_UNDER}BO_API__r.${PREFIX_UNDER}Sales_Org__c = '<salesOrg>'"

# 2. Step rows for this sales org
sf data query --target-org <alias> --json --query "
  SELECT COUNT(Id) FROM ${PREFIX_UNDER}BO_API_Workflow_Step__c
   WHERE ${PREFIX_UNDER}Sales_Org__c = '<salesOrg>'"

# 3. Junction rows whose parent workflow belongs to a Promotion BO API for this sales org
sf data query --target-org <alias> --json --query "
  SELECT COUNT(Id) FROM ${PREFIX_UNDER}BO_API_Workflow_Workflow_Step__c
   WHERE ${PREFIX_UNDER}BO_API_Workflow__r.${PREFIX_UNDER}BO_API__r.Name = 'Promotion'
     AND ${PREFIX_UNDER}BO_API_Workflow__r.${PREFIX_UNDER}BO_API__r.${PREFIX_UNDER}Sales_Org__c = '<salesOrg>'"
```

- Zero workflow rows → fresh for this sales org, Phase 3 will seed.
- Full state (4 workflow rows `create/update/copy/derive`; >0 step + junction rows) → Phase 3 is a no-op for this sales org (still run for idempotency; 3a shows zero net-new).
- Partial state → **error**; stop, report which rows are missing. A human inspects first.

## Phase 3a — Preview the default BO API seed (fetch + confirm)

The workflows/steps/junctions/entities/input-structures ship as CSVs inside the
packaged `TPMSetupData` static resource; `TPMSetupData.setupBOApi` reads and
upserts them. Before running it, show the user what will land.

1. Locate the resource:
   ```bash
   sf data query --target-org <alias> --json --query "
     SELECT Id, Name, NamespacePrefix, SystemModStamp, BodyLength
       FROM StaticResource WHERE Name = 'TPMSetupData'"
   ```
   Zero rows → stop ("TPMSetupData static resource not found — is the CGCloud package installed?"). Multiple rows → prefer the one whose `NamespacePrefix` matches Phase 1; if prefixes disagree, stop and ask.
2. **Retrieve + expand the resource cross-platform via SFDX** — use `sf project retrieve`, which unpacks a zip StaticResource into a folder on every OS (no `curl`, no `unzip` — `unzip` isn't present on Windows by default). Retrieve into a **dedicated `setup-data/` subproject** so the read-only managed resource never mixes into the Phase-5a deploy tree (`./.promotion-bo-api-deploy/force-app`, which is what gets deployed back):
   ```bash
   mkdir -p ./.promotion-bo-api-deploy/setup-data/force-app/main/default
   printf '{ "packageDirectories": [{ "path": "force-app", "default": true }], "sourceApiVersion": "60.0" }' \
     > ./.promotion-bo-api-deploy/setup-data/sfdx-project.json
   ( cd ./.promotion-bo-api-deploy/setup-data && sf project retrieve start \
       --metadata "StaticResource:${PREFIX_UNDER}TPMSetupData" --target-org <alias> --json )
   ```
   Non-success → stop, print `result` errors.
3. SFDX expands the zip to `./.promotion-bo-api-deploy/setup-data/force-app/main/default/staticresources/${PREFIX_UNDER}TPMSetupData/BOApi/`. `ls` it. Expected: `0_BO_API__c.csv`, `0_BO_API_Entity__c.csv`, `0_BO_API_Output_Entity__c.csv`, `0_BO_API_Workflow__c.csv`, `0_BO_API_Workflow_Entity__c.csv`, `0_BO_API_Workflow_Step__c.csv`, `0_BO_API_Workflow_Workflow_Step__c.csv`, `0_BO_API_Step_Input_Structure__c.csv`, `import.json`. Any missing → stop, print the delta.
4. Confirm each target sObject exists: `sf sobject describe --sobject '${PREFIX_UNDER}BO_API_Workflow__c' --target-org <alias> > /dev/null` (etc.). Any describe failure → stop (package partially installed).
5. Show a summary (row counts per object; total ~232 rows across 8 objects; "upsert on Unique_Key__c — re-running is idempotent"), plus the first 3 rows of `0_BO_API_Workflow__c.csv` and `0_BO_API_Workflow_Step__c.csv` with `{{NS}}`/`{{SALES_ORG}}` substituted.
6. Wait for confirmation unless `--yes`. "no"/blank → abort clean, point at `./.promotion-bo-api-deploy/setup-data/force-app/main/default/staticresources/${PREFIX_UNDER}TPMSetupData/BOApi/`.
7. On `--dry-run` → stop here; do not run 3b.

## Phase 3b — Apply the default seed

Only after 3a confirmation.

1. `PHASE3_START=$(date -u +%FT%TZ)`.
2. Run metadata-wizard setup via anon Apex: `${PREFIX_DOT}TPMSetupData.setupMetadataWizard('<salesOrg>');` → `sf apex run --target-org <alias> --file ./.promotion-bo-api-deploy/setup-metadata-wizard.apex`.
3. Wait for the whole batch chain. `GenericDemoSetupDataBatch` self-chains via `finish()`; polling a single job id misses children. Poll by class:
   ```bash
   sf data query --target-org <alias> --json --query "
     SELECT COUNT() FROM AsyncApexJob
      WHERE ApexClass.Name = 'GenericDemoSetupDataBatch'
        AND CreatedDate >= ${PHASE3_START}
        AND Status NOT IN ('Completed','Failed','Aborted')"
   ```
   Sleep 5s between polls; break when count is zero for **two consecutive** polls (covers the gap between a parent's `finish()` and the child's `AsyncApexJob` row appearing).
4. Final check — every child succeeded (`SELECT Id, Status, NumberOfErrors, ExtendedStatus FROM AsyncApexJob WHERE ApexClass.Name = 'GenericDemoSetupDataBatch' AND CreatedDate >= ${PHASE3_START}`). Any `Failed`/`Aborted`/`NumberOfErrors > 0` → stop, print `ExtendedStatus`.
5. Repeat 2–4 for `${PREFIX_DOT}TPMSetupData.setupBOApi('<salesOrg>');`.

## Phase 4 — Verify the BO API framework is on

Re-run the Phase 2 queries. Expect 4 `BO_API_Workflow__c` rows
(`create`/`update`/`copy`/`derive`, uniqueness on `Unique_Key__c`), ≥46
`BO_API_Workflow_Step__c` rows, ≥54 `BO_API_Workflow_Workflow_Step__c` junction
rows. Anything short → stop, print what's missing. Never claim success while a
component failed.

## Phase 5 — Interview: what does the user want to customize?

The framework is now on. The customization is **user-supplied** — do not skip
the interview; do not invent an answer. Print:

```text
The Promotion BO API framework is installed. To add a custom step, tell me:
  - Which BO API entity does it target? (e.g. Promotion or Tactic — I'll list the exact entities registered in your org)
  - Which workflows should it fire in? (create, update, copy)
  - What does it read from the ingest input?
  - What does it write on the SObject or elsewhere?
  - Any preconditions or side effects I should know about?
If you want a worked example, say "use the SetCommentValue reference" —
it copies the tactic input Comment onto Tactic.Comment__c.
```

### 5.1 — Answers to collect

| Field | Required | Notes |
|---|---|---|
| `stepName` | yes | PascalCase Apex class name + BO API Workflow Step `Name`. Unique across `ApexClass`. |
| `entity` | yes | BO API entity `Name` — MUST match a row queried live from `${PREFIX_UNDER}BO_API_Entity__c` (shared, not sales-org-partitioned); do not assume a fixed list. In a current org these include `Promotion`, `Tactic`, `ProductFilter`, `ManualInputs`, `CustomState` (plus the `TPM_Promotion.*` structures). Query the org and offer the actual rows. |
| `workflows` | yes | Non-empty subset of `{create, update, copy}`. `derive` is out of scope. |
| `actionName` | yes | Symbolic action string the class receives in `call(String action, ...)`. Convention: lowerCamelCase of `stepName`. |
| `inputPaths` | yes (≥1) | JSON paths to read from `currentInput`, e.g. `["Comment"]`. |
| `inputPathType` | yes | JSON type of the input paths — `String`, `Array`, `Boolean`, `Number`, `Object`. Drives the `RecordType` on each SIS row; a wrong value causes `TransformationError: Expected <Type>` at ingest. Different types → run Phase 5b once per type group. |
| `outputWrites` | yes (≥1) | `{field, source}` pairs; `field` is the target API name **without** the namespace prefix (skill adds `${PREFIX_UNDER}`), `source` references an `inputPaths` value / literal / computed expression. |
| `description` | yes | One-sentence step description → `${PREFIX_UNDER}Description__c` + class docstring. |
| `preconditions` | optional | Free-text guards before writing. |
| `sortAfter` | optional | Named packaged step to sort after; default `max(Sort__c) + 10`. |

### 5.2 — Interview flow

1. **Preset shortcut.** If `--preset set-comment-value` or the user says "use the SetCommentValue reference", load the answers from `references/reference-example-set-comment-value.md` (`assets/set-comment-value/interview-answers.json`) and skip the interactive interview. `--interview-file <path>` loads answers from a JSON file mirroring the 5.1 table (wins over `--preset`).
2. **Ask the questions** one at a time (or as a block); do not proceed until every required field has a concrete value.
3. **Show the entity's writeable fields** after the user names the entity:
   ```bash
   sf sobject describe --target-org <alias> --sobject '${PREFIX_UNDER}<Entity>__c' --json \
     | jq -r '.fields[] | select(.updateable == true and .createable == true) | .name'
   ```
   Any `outputWrites` field must appear here; otherwise stop and ask for a different one (FLS is caller-scoped).
4. **Confirm the plan** (recap Class/Entity/Workflows/Reads/Writes/Sort/Description → "Deploy + wire? [y/N]"). `n`/blank → save answers to `./.promotion-bo-api-deploy/interview.json` and exit. `y` → Phase 5a.

## Phases 5a / 5b — Generate + deploy, register + wire

Runbook in `references/generate-and-wire.md`. In short: guard the class name for
idempotency; confirm target-field writeability; generate a namespace-agnostic
`Callable` from the interview (reads `currentInput`/`currentOutput`, derives the
prefix from `getSObjectType()` at runtime); show + confirm; `sf project deploy
start`. Then, in one anon-Apex transaction, upsert one `BO_API_Workflow_Step__c`
(bare class name in `Classname__c`), one `BO_API_Workflow_Workflow_Step__c`
junction per chosen workflow (never assume all three; `derive` dropped), and the
`BO_API_Step_Input_Structure__c` rows (RecordType per `inputPathType`). Both
upserts key on `Unique_Key__c` (idempotent).

## Phase 6 — Smoke test through the REST endpoints

Runbook in `references/smoke-and-verify.md`. Derive the payload contract per
invoked workflow from `BO_API_Step_Input_Structure__c` (schema-first), apply
rules R1–R8 from `references/conventions-and-payload-rules.md`, resolve every
reference in-sales-org, materialize `./out/smoke/{create,update,copy}.json`, then
run `initialize → ingest → poll status` for each chosen workflow. Verify via a
direct `BO_API_Transaction_Log__c` query (any row `!= 'Calculated'` → fail) plus
an `outputWrites` field assertion against `./out/smoke/expected.json`. Update and
copy legs run only if the interview included them.

## Phase 7 — Report

Short status: org, sales org, dry-run flag; namespace prefix; BO API seed rows
before/after (Phases 2 & 4); interview (preset name or resolved `stepName`,
`entity`, `workflows`, `inputPaths`, `outputWrites`); class deploy result +
workflow-step id + junction ids (1–3); smoke import ids per invoked workflow, all
`Calculated` with matching write assertions — or exactly which failed (SOQL,
expected, actual); manual follow-ups (`none` if clean).

## Rules

- Never claim success while any `BO_API_Transaction_Log__c` row for the smoke import ids has `Status__c != 'Calculated'`. `Calculated` is the terminal success state (R2); `Processed` does NOT exist in the picklist.
- Never claim success while any `outputWrites` assertion fails, or while any `GenericDemoSetupDataBatch` `AsyncApexJob` since the phase start is still running or failed.
- Stop on the first failed preflight or verify check; report the exact failure.
- Never hard-code the namespace prefix — compose every Apex/SOQL/REST reference from the Phase-1 detection.
- Never invent Apex method signatures — use what the packaged `TPMSetupData` / `BO_API_*` objects and the shipping REST endpoints declare.
- The seeded BO API metadata is packaged content — preview it and get user confirmation before invoking `TPMSetupData.setupBOApi`.
- Never invent an interview answer. Absent a user and any `--preset`/`--interview-file`, stop and print the questions.
- Never wire a workflow the interview did not include. `create`/`update`/`copy` are individually opt-in; `derive` is always excluded.
- Never compose a smoke payload from a hard-coded template — derive accepted paths per workflow from `BO_API_Step_Input_Structure__c` and validate user input against that contract first.
- Never resolve a reference value without the sales-org filter. A record under a different sales org is not valid for this invocation.
