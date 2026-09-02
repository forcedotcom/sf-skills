---
name: consumer-goods-tpe-datakit-deploy
description: "Deploy the TPM Accruals Data Kit components specifically required for Trade Promotion Effectiveness (TPE) dashboards. Use when a customer or admin wants to install or deploy the TPM data kit for TPE dashboards, or as a delegated step from consumer-goods-tpe-dashboard-configure. Do not use this skill if the customer wants to deploy the TPM Accruals Data Kit for the Accruals feature."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Consumer Goods"]
  relatedSkills:
    - "consumer-goods-tpe-dashboard-configure"
  cliTools:
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# TPE Data Kit Deploy

Deploys the TPM Accruals Data Kit and its DMO mappings into a Salesforce org. Standalone and self-contained — runs on its own, or as a delegated step invoked by `consumer-goods-tpe-dashboard-configure` (Step 7), which passes through its own already-collected username and dry-run flag rather than this skill re-deriving them.

## Inputs to collect first

Ask before starting, unless already supplied by a calling skill. Do not guess.

1. **TPM System Admin username** — already authenticated via `sf` CLI. Verify via the sibling
   script, never `sf org display --json` directly — that command's raw output includes
   `accessToken` (a live credential), which this script strips before printing:
   ```bash
   node ./scripts/sf-rest.js org-status --target-org <username>
   ```
   Prints `{"username","alias","connectedStatus","orgId"}`. Non-zero exit or
   `connectedStatus != "Connected"` ⇒ stop, ask the user to log in themselves.
2. **Dry-run?** — offer by default. In dry-run, Phase 1 (preflight) and Phase 2's read/diff steps still run; Phase 2's `FieldPermissions` writes and Phases 3-5 (deploy) are skipped and recorded as `pending — not run (dry-run)`.
3. **TPM Data Connector installed and active** — cannot be verified programmatically. Ask the user, spelling out the exact navigation steps rather than just naming the setting: *"Can you confirm the TPM Data Connector is Active? 1) Go to Setup → Data Cloud Setup. 2) In the left nav, under EXTERNAL INTEGRATIONS, click Other Connectors. 3) Find 'TPM Data Connector' in the list and check its status."* Wait for an explicit yes. If missing or inactive, **stop** — tell the user we cannot proceed without the TPM Data Connector being active, and explain the two different paths depending on org type:
   - **Production orgs** — it's typically auto-installed within ~24h of Processing Service pairing, provided the org has a Data Cloud license. If both prerequisites are met, ask the user to wait and retry; if either isn't met (no pairing yet, or no Data Cloud license), that's the real blocker to resolve first.
   - **Sandbox orgs** — auto-install commonly does not happen; it typically needs to be activated manually under EXTERNAL INTEGRATIONS → Other Connectors. Tell the user this is expected in sandboxes and ask them to activate it there, then confirm before continuing.
   Re-run this check once the user confirms it's Active.
4. **Salesforce CRM Home org connection** — cannot be verified programmatically. Ask the user, spelling out the exact navigation steps: *"Can you confirm the Salesforce CRM Home org connection is Active? 1) Go to Setup → Data Cloud Setup. 2) In the left nav, under SALESFORCE INTEGRATIONS, click Salesforce CRM. 3) Check that the Home org connection status is Active."* Wait for an explicit yes. If missing/inactive, **stop** — tell the user we cannot proceed without this connection being active (Phase 2's field-permission grants require the `Data Cloud Salesforce Connector` permission set, which won't exist until this connection is configured) — ask them to activate/configure it first, then re-run this check.
5. **Permission set(s) for the TPM Admin persona + GenieAdmin permission set confirmed assigned** — when invoked as a delegated step from `consumer-goods-tpe-dashboard-configure`, it passes through both results already confirmed in its own earlier phases; reuse them, don't re-ask or re-query. When invoked standalone, confirm each directly:
   - **Permission set(s) for the TPM Admin persona** — "TPM Admin persona" is a role, not an actual permission set name; the org-specific permission set backing that persona (name/assignment) cannot be verified programmatically. Ask the user to confirm: *"Is the permission set(s) required for the TPM Admin persona assigned to &lt;username&gt;?"* Wait for an explicit yes.
   - **GenieAdmin** — resolve its Label first (never show the API `Name` to the user), then check the assignment:
     ```bash
     sf data query --target-org <username> --query "SELECT Label FROM PermissionSet WHERE Name = 'GenieAdmin'"
     sf data query --target-org <username> \
       --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '<username>' AND PermissionSet.Name = 'GenieAdmin'"
     ```
     Missing ⇒ tell the user the Label from the first query (e.g. *"User &lt;username&gt; is missing the &lt;Label&gt; permission set. Assign it now?"*) and ask permission to assign before continuing:
     ```bash
     sf data create record --sobject PermissionSetAssignment \
       --values "AssigneeId=<userId> PermissionSetId=<psId>" --target-org <username>
     ```
     If declined, skip and note it in the report.
6. **Namespace (`NS`)** — when invoked as a delegated step, `consumer-goods-tpe-dashboard-configure` passes through its already-detected `NS` (raw namespace string); reuse it, don't re-detect. When invoked standalone, detect it once yourself, before Phase 1, with the sibling script:
   ```bash
   node ./scripts/detect-namespace.js --target-org <username>
   ```
   Prints `{"NS","NS_SEGMENT","NS_APEX","NS_FIELD"}` as one line of JSON. Store all four and reuse everywhere below.


## Phase 1 — Preflight

2. **Baseline for later verification** — capture the latest `DataKitDeploymentLog` Id now, before any deploy work, to avoid a `CreatedDate` clock-skew false-negative in Phase 5:
   ```bash
   sf data query --target-org <username> \
     --query "SELECT Id FROM DataKitDeploymentLog ORDER BY CreatedDate DESC LIMIT 1" --json
   ```
   Store as `LAST_ID_BEFORE_DEPLOY` (empty if zero rows).
3. **Download & unzip `CGCloudAddons`** — this skill fetches it itself rather than asking the user to do it manually.
   ```bash
   node ./scripts/download-static-resource.js \
     --target-org <username> --name CGCloudAddons
   ```
   Capture `STATIC_RESOURCE_PATH=<dir>` from stdout as `<addons_root>` — every path below is relative to it (e.g. `<addons_root>/TPM/Accruals/TPM Accruals Data Kit`). Zero `StaticResource` rows ⇒ **block**: the package version installed in this org doesn't ship `CGCloudAddons`. Any other script failure ⇒ block and relay its stderr verbatim.

## Phase 2 — Field permissions for CRM streams (derived from the downloaded package)

Two sibling scripts drive this phase — never hand-roll the parsing or the grant calls; see each script's own docstring for exactly what it does and why:

1. **Extract** the `{sobject, fields[]}` list from the downloaded package (read-only, always safe to run):
   ```bash
   node ./scripts/extract-crm-field-permissions.js \
     --dir "<addons_root>/TPM/Accruals/TPM Accruals Data Kit/force-app/main/default/dataSourceObjects" \
     > /tmp/crm-field-permissions.json
   ```
   Zero entries in the output ⇒ block and report — shouldn't happen if Phase 1 succeeded.
2. **Get the diff to update, silently** (the script's own `--dry-run` — read-only: permission set, `sobject/describe`, existing `FieldPermissions`/`ObjectPermissions` rows) — don't show the user anything yet, this is just to find out whether there's anything to do:
   ```bash
   node ./scripts/update-field-permissions.js \
     --target-org <username> --input /tmp/crm-field-permissions.json --dry-run
   ```
   `{"error":"permission_set_not_found",...}` ⇒ stop this phase, mark it blocked, and tell the user: *"Could not find the 'Data Cloud Salesforce Connector' permission set — a likely explanation is that Salesforce CRM hasn't been configured yet (Setup → Data Cloud → Salesforce CRM). Please configure that first, then re-run this phase."*
3. **Only if `wouldGrant` or `objectWouldGrant` is non-empty**, show the user exactly that diff (not the full extracted list) and get an explicit go-ahead before writing anything. If both are empty, everything's already granted — skip straight to step 5, no confirmation needed.
4. **On confirmation, run it for real** — add-only at both field and object level (see script docstring for exact semantics):
   ```bash
   node ./scripts/update-field-permissions.js \
     --target-org <username> --input /tmp/crm-field-permissions.json
   ```
   Exit code `3` (or a non-empty `failed[]`/`objectFailed[]`) ⇒ don't guess a workaround — prompt the user to do it manually via Setup → Permission Sets → Data Cloud Salesforce Connector → Object Settings, using exactly the `failed[]`/`objectFailed[]` list, and note each in the report.
5. Record pass/blocked/pending, and the touched-field/object outcome (`granted`/`alreadyGranted`/`notFlsEligible`/`failed`, `objectGranted`/`objectAlreadyGranted`/`objectFailed`), for the final report. Dry-run mode (never proceed to step 4 when in dry run mode as it updates permissions, step1 and step2 can be run as they are read only)
6. `objectGranted`/`objectAlreadyGranted` entries with `permissionsViewAllRecords: false` are expected for a small, fixed set of sobjects (currently just Product2) whose license blocks that flag — this is a known platform restriction the script applies silently; don't flag it to the user or treat it as something needing manual Setup action.

## Phase 3 — Prepare and deploy data kit metadata

1. In `<addons_root>/TPM/Accruals/TPM Accruals Data Kit`, find-and-replace every instance of the placeholder `__SF_ORG_ID__` with the org's 15-digit Id. Get the org Id via the following sibling script
   ```bash
   node ./scripts/sf-rest.js org-status --target-org <username>
   ```
   Take the `orgId` field from the printed JSON and truncate it to 15 chars (this call is cheap and idempotent — always re-run it here rather than relying on the Inputs step 1 result still being in context).
2. Deploy from that folder:
   ```bash
   sf project deploy start --target-org <username>
   ```

## Phase 4 — Deploy DMO mappings and run the deployment script

1. **DMO mappings** — maps the data kit's DLOs to Data 360 DMOs. From `<addons_root>/TPM/Accruals/DmoMappings`:
   ```bash
   sf project deploy start --target-org <username>
   ```
2. **Deployment script** — from `<addons_root>/TPM/Accruals/Accruals Data Kit Deployment Scripts`:
   ```bash
   SF_ORG_ALIAS=<username> node deploy-tpm-tpe.js
   ```
   This script POSTs to `/services/data/v67.0/actions/custom/flow/sfdatakit__DeployDataKitComponents` and returns an async Flow interview guid immediately; that response alone doesn't mean success — always confirm via the `DataKitDeploymentLog` check in Phase 5. This script runs from inside the downloaded/unzipped static resource.

## Phase 5 — Verify

```bash
sf data query --target-org <username> \
  --query "SELECT Id, DeploymentStatus, ComponentName, DeploymentError, CreatedDate FROM DataKitDeploymentLog WHERE Id > '<LAST_ID_BEFORE_DEPLOY>' ORDER BY CreatedDate DESC"
```

Every row for this run must have `DeploymentStatus = 'Successful'` and a blank `DeploymentError`. **Never claim success while any row is `Failure` or has a non-empty error.**

Alternative UI check: Data Cloud Setup → Data Kits → TPM Accruals → Local Deployment History → status `Successful`.

## Known gotchas

- `FlowDefinition` is **not** SOQL-queryable — don't probe it for readiness.
- An `sfdatakit__DeployDataKitComponents` ApexClass probe can return 0 rows even when the framework is live — prefer probing `DataKitDeploymentLog` directly (Phase 5), never the Apex class.

## Rules

- Never claim success while any `DataKitDeploymentLog` row for this run is `Failure` or has a non-empty `DeploymentError`.
- Only ever read the `CGCloudAddons` `StaticResource` (via `download-static-resource.js`) — never deploy or modify it; the org's own `sf`-authenticated access token drives the download, never a hardcoded credential.
- Never probe `FlowDefinition` or the `sfdatakit__DeployDataKitComponents` Apex class for readiness — probe `DataKitDeploymentLog` instead.
- Never consult the org-shipped `README.md` (or any other in-package documentation bundled inside `CGCloudAddons`) for deployment guidance — follow this skill's phases exactly as written. If a script name or path documented here doesn't match what's actually in the downloaded package, that's a bug in this skill to fix (update the skill itself), not a cue to switch to package docs at runtime.
- If a script or folder is missing from the downloaded folder, do not guess or change the scripts. e.g.: never change the script `deploy-tpm-tpe.js`.
- Never run `update-field-permissions.js` without `--dry-run` first. If its `wouldGrant`/`objectWouldGrant` come back non-empty, never run for real without showing the user that exact diff and getting an explicit go-ahead — same as any other write in this skill. If both are empty, no confirmation is needed; proceed straight to reporting.
- `update-field-permissions.js` only ever adds — a new `FieldPermissions`/`ObjectPermissions` row where none existed, or flipping an existing row's off flag (`PermissionsRead`, or `PermissionsViewAllRecords` at the object level) to `true`. Never call it in a way that deletes a row, weakens an existing grant, or touches `PermissionsCreate`/`Edit`/`Delete`/`ModifyAllRecords`.
- Never guess a workaround when the `sfdc_a360_sfcrm_data_extract` ("Data Cloud Salesforce Connector") permission set is missing or a field/object ends up in `update-field-permissions.js`'s `failed[]`/`objectFailed[]` — stop and prompt the user to grant field-level or object-level security manually via Setup (see Phase 2).

## Report

Produce a final report (pass/blocked/pending) covering: CRM stream field permissions (per-object field list from `extract-crm-field-permissions.js`, and each field's `granted`/`alreadyGranted`/`notFlsEligible`/`failed` outcome from `update-field-permissions.js` — flag any `notFlsEligible` entry with `onObject: false` separately, since that's a package/org data mismatch, not a normal skip), CRM stream object-level permissions (each sobject's `objectGranted`/`objectAlreadyGranted`/`objectFailed` outcome from the same script — a `permissionsViewAllRecords: false` on Product2 specifically is expected and not worth calling out), preflight (connector status), metadata deploy, DMO mapping deploy, deployment script run, and the `DataKitDeploymentLog` verification result (row count, any failures). This is exactly what `consumer-goods-tpe-dashboard-configure` Step 7 relays as its own result when this skill is invoked via delegation.

**When invoked via delegation** (the calling skill used the `Skill` tool to reach this file, rather than the user directly): this report is an intermediate result, not the end of the task. Return it to the calling skill and let it continue with its own next phase — do not present this report to the user as the final answer and stop. Only surface this report directly to the user when this skill was invoked standalone.
