# Procedure

Before starting, read `references/inputs-and-namespace.md` for the required inputs and the namespace-detection procedure.

## Phase 1 — Permission sets

1. **GenieAdmin** — if a value was passed in from the caller, use it. If standalone, resolve its Label first (never show the API `Name` to the user), then check the assignment:
   ```bash
   sf data query --target-org <username> --query "SELECT Label FROM PermissionSet WHERE Name = 'GenieAdmin'"
   sf data query --target-org <username> \
     --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '<username>' AND PermissionSet.Name = 'GenieAdmin'"
   ```
   Missing ⇒ tell the user the Label from the first query (e.g. *"User <username> is missing the &lt;Label&gt; permission set. Assign it now?"*) and ask permission to assign before continuing (same pattern as `consumer-goods-tpe-dashboard-configure` Phase 3).
2. **TPM Admin** — never re-derive or guess. Use the passed-in confirmation, or ask directly if standalone: *"Confirm the permission set(s) required for the org's TPM Admin persona are assigned to the username."* Wait for an explicit yes.

## Phase 2 — `Data_Cloud_Enabled` system setting

**Inform the user first — this is a global setting other parts of the org may read.** Tell them plainly: *"This will create/update the System_Setting__c record named 'Data_Cloud_Enabled' with Value__c = 'true'."* Wait for a go-ahead. `Value__c` is a text field (not Boolean) — the literal string `'true'` is written, not the Boolean `true`. There is no single-record `sf data upsert record` command in the current `sf` CLI (`sf data upsert` only has `bulk`/`resume` CSV subcommands), so this uses an idempotent anonymous-Apex upsert instead — query-then-insert-or-update inside one transaction, avoiding the query/create/update round-trip race the CLI approach would have. `%NS%` takes the `NS_FIELD` form:
```bash
node ./scripts/render-apex.js scripts/upsert-system-setting.apex --var NS=<NS_FIELD>
sf apex run --target-org <username> -f <rendered-path> --json
```
Read the record Id back from the debug log line `RTR_DATACLOUD_SETTING_ID=<id>`. Then query to confirm the write landed, `NS_FIELD` on the custom object/field (`Name` is standard, no prefix):
```bash
sf data query --target-org <username> \
  --query "SELECT Id, Name, <NS_FIELD>Value__c FROM <NS_FIELD>System_Setting__c WHERE Name = 'Data_Cloud_Enabled'"
```
Confirm exactly one row with `Value__c = 'true'`. Dry-run ⇒ skip both the execute and the confirmation query, record `pending — not run (dry-run)`.

## Phase 3 — Trigger SF Data Sync (scoped)

Capture a baseline `Batch_Run_Status__c` Id first, so Phase 4's poll can't match a stale prior sync run (`NS_FIELD` on the custom object; `Id`/standard fields unprefixed):
```bash
sf data query --target-org <username> \
  --query "SELECT Id FROM <NS_FIELD>Batch_Run_Status__c ORDER BY <NS_FIELD>Start_Date__c DESC LIMIT 1" --json
```
Store as `LAST_BRS_ID` (empty if zero rows). Then run, scoped to `System_Setting__c` (the object Phase 2 wrote) rather than a full-org sync. `OffPlatformCallout` takes `NS_APEX`; the tracked object name inside the JSON string is a field API name and takes `NS_FIELD`; the transaction id comes from the confirmed-`global` `TransactionHandler.getTransactionIdentifier()` (also `NS_APEX`-prefixed), not `TPM_App.getTxId()` — `TPM_App` is only `public`, unreachable from anonymous Apex against a namespaced managed-package install:
```apex
<NS_APEX>OffPlatformCallout callout = new <NS_APEX>OffPlatformCallout('SCHEDULE_SFDATA_SYNC', null);
<NS_APEX>OffPlatformCalloutResponse resp = callout.execute(
  <NS_APEX>TransactionHandler.getTransactionIdentifier(), null,
  '{"command":"SYNC","trackedObjectApiNames":["<NS_FIELD>System_Setting__c"]}'
);
System.debug(resp);
```
via `sf apex run`. Use `'RE_SYNC'` instead of `'SYNC'` only if resyncing the same scoped object list. Only omit `trackedObjectApiNames` entirely (plain `{"command":"SYNC"}`) if the user explicitly asks for a full-org sync instead. Dry-run ⇒ skip, record `pending — not run (dry-run)`.

## Phase 4 — Verify the sync completed

```bash
sf data query --target-org <username> \
  --query "SELECT Id, <NS_FIELD>Batch_Name__c, <NS_FIELD>Batch_State__c, <NS_FIELD>Start_Date__c, <NS_FIELD>End_Date__c FROM <NS_FIELD>Batch_Run_Status__c WHERE Id > '<LAST_BRS_ID>' ORDER BY <NS_FIELD>Start_Date__c DESC"
```
Log every returned row — the exact `Batch_Name__c` is `SFDataSyncWorker`. Terminal: `Done` = success, `Error`/`Fatal` = failure, `Running` = poll again after a short wait.

## Phase 5 — Verify the `Usage__c` picklist value exists

```bash
sf sobject describe --sobject <NS_FIELD>RTR_Report_Configuration__c --target-org <username> --json
```
Confirm `datacloudpromotionmeasuresmeta` appears in the `Usage__c` field's `picklistValues[]`.

**If missing, do not try to patch it programmatically.** Picklist values are not carried by a metadata deploy or package upgrade into a subscriber org (confirmed Salesforce platform behavior) — this skill has no way to append a picklist value without a full read-modify-write of the field, which is more fragile than the manual step. Tell the user to add it manually: Setup → Object Manager → RTR Report Configuration → Fields & Relationships → Usage → New → add `datacloudpromotionmeasuresmeta` ("Data 360 Promotion Measures Export"). Reference: https://help.salesforce.com/s/articleView?id=ind.tpm_add_report_metadata.htm&type=5. Then re-run this check before continuing to Phase 6.

## Phase 6 — Reuse or create the RTR Report Configuration (one Sales Org at a time)

`RTR_Report_Configuration__c` is unique per (`Usage__c`, `Sales_Organization__c`) pair. This skill always uses `Usage__c = 'datacloudpromotionmeasuresmeta'` — hardcoded, never asked. Customers can configure more than one Sales Org under it — process them **one at a time**: run steps 1-6 below for the current Sales Org, then ask *"Add another Sales Org to configure?"* before moving on. The Sales Org Name itself is **not** collected up front — step 1 below asks for it fresh on each loop iteration. Check for an existing config **before** asking for anything else — do not ask for KPI Set/measure codes/date-from until the check comes back empty for this Sales Org. Keep a running `CONFIGURED_SALES_ORGS` list of `{salesOrgId, salesOrgName, internalName}` for every Sales Org this loop finishes (both the reused-as-is and the newly-created case) — Phase 7 exports **once per Sales Org in that list**, using each one's `internalName` as `metaname`, only after this loop is fully done.

The remaining Apex template's `%NS%` placeholder expects the `NS_FIELD` form (double-underscore, e.g. `cgcloud__`, or empty) — pass the already-detected `NS_FIELD` value as `--var NS=<NS_FIELD>` in every `render-apex.js` call below (never re-detect; use the value from "Namespace detection" / the caller's passed-through `NS`).

This skill never creates a `KPI_Set__c` or its `KPI_Set_KPI_Definition__c` junction rows — customers set those up independently. Both the Sales Org and the KPI Set are given as **Names** by the user; the skill resolves each to an Id by query (steps 1 and 3) before step 4 runs.

1. **Ask for this iteration's Sales Org Name**, then resolve it to an Id, `NS_FIELD` on the custom object (`Id`/`Name` are standard, unprefixed):
   ```bash
   node ./scripts/resolve-id-by-name.js --target-org <username> --object <NS_FIELD>Sales_Organization__c --name "<salesOrgName>"
   ```
   Zero rows ⇒ stop and tell the user no `Sales_Organization__c` with that Name exists; ask for a different Name. More than one row ⇒ show the matches and ask the user to disambiguate. Exactly one ⇒ use its Id as `<salesOrgId>`.
2. **Check for an existing config, per Sales Org Id**, `NS_FIELD` on the custom object/fields:
   ```bash
   sf data query --target-org <username> \
     --query "SELECT Id, Name, <NS_FIELD>Internal_Name__c, <NS_FIELD>Reporting_KPI_Set__c, <NS_FIELD>JSON__c FROM <NS_FIELD>RTR_Report_Configuration__c WHERE <NS_FIELD>Usage__c = 'datacloudpromotionmeasuresmeta' AND <NS_FIELD>Sales_Organization__c = '<salesOrgId>'"
   ```
   - **Found** ⇒ show the user the existing config's Name/Id and current `Internal_Name__c`/`Reporting_KPI_Set__c`/`JSON__c`, and ask them to confirm proceeding with it as-is. Confirmed ⇒ record its Id as `<configId>` and its `Internal_Name__c` as `<internalName>` for this Sales Org, mark it **unchanged**, and skip straight to step 6 (loop control) — no sync call for this Sales Org, since nothing was modified. Never ask for KPI Set/measure codes/date-from for this Sales Org, and never overwrite it here. Declined ⇒ skip this Sales Org for this run and note it in the report; don't fall through to rebuilding it without a separate, explicit ask.
   - **Not found** ⇒ now ask for this Sales Org's remaining build inputs (KPI Set Name, measure codes, date-from — see `references/inputs-and-namespace.md`) and continue with steps 3-6 below for this Sales Org.
3. **Resolve the KPI Set Name to an Id**, `NS_FIELD` on the custom object (`Id`/`Name` are standard, unprefixed):
   ```bash
   node ./scripts/resolve-id-by-name.js --target-org <username> --object <NS_FIELD>KPI_Set__c --name "<kpiSetName>"
   ```
   Zero rows ⇒ stop and tell the user no `KPI_Set__c` with that Name exists; ask them to create it (with its measure-code junction rows) first, or give a different Name. More than one row ⇒ show the matches and ask the user to disambiguate. Exactly one ⇒ use its Id as `<kpiSetId>`.
4. **Determine the Internal Name, then create the RTR Report Configuration** — this Sales Org has no existing row (step 2 confirmed it), so this always inserts; the template's own existence check is just an idempotency safety net if this phase is re-run. **Ask the user** whether they want to supply a custom `Internal_Name__c` for this Sales Org's config, or use the default: `"Data 360 Promotion Measures Export <Sales Org Name>"` (no hyphen — whether one would trip a validation rule on this field is unconfirmed, so it's avoided), where `<Sales Org Name>` is the `Name` resolved in step 1 — e.g. `"Data 360 Promotion Measures Export US01"`. (A bare label with no Sales Org suffix is only correct when there's exactly one Sales Org configured; once a second one is added, its row needs its own distinguishable label — flag this to the user if they supply a custom name that doesn't vary per Sales Org.) Record whichever value is used as `<internalName>` for this Sales Org — Phase 7 passes it as `metaname` when triggering that Sales Org's export. Assemble `JSON__c` next:
   ```json
   {"measurecodes":["<code1>","<code2>"],"datefrom":"<YYYY-MM-DD>","object":"promotionmeasures"}
   ```
   Then render and run (pass the JSON raw — `render-apex.js` escapes every `--var` value for you; pre-escaping it here would double-escape):
   ```bash
   node ./scripts/render-apex.js scripts/upsert-report-config.apex \
     --var NS=<NS_FIELD> --var USAGE=datacloudpromotionmeasuresmeta --var INTERNAL_NAME="<internalName>" \
     --var SALES_ORG_ID=<salesOrgId> --var KPI_SET_ID=<kpiSetId> --var JSON_LITERAL="<json>"
   sf apex run --target-org <username> -f <rendered-path> --json
   ```
   Read the record Id back from `RTR_DATACLOUD_CONFIG_ID=<id>`. Mark this Sales Org **changed**.
5. **Sync it — only if changed.** If step 2 found an existing config and the user confirmed reuse as-is, there is nothing to sync — skip this step entirely for that Sales Org. Only run this after step 4 actually created a new config:
   ```apex
   <NS_APEX>RTRSyncReportConfigInvocable.syncReportConfig(
     new List<<NS_FIELD>RTR_Report_Configuration__c>{ [SELECT Id FROM <NS_FIELD>RTR_Report_Configuration__c WHERE Id = '<configId>'] }
   );
   ```
   via `sf apex run`. `RTRSyncReportConfigInvocable` (an Apex class) takes `NS_APEX`; `RTR_Report_Configuration__c` (the sObject) takes `NS_FIELD`. Sync happens here, immediately after this Sales Org's config is created — never deferred to a later batch step.
6. Add `{salesOrgId, salesOrgName, internalName}` for this Sales Org to `CONFIGURED_SALES_ORGS`, then ask: *"Add another Sales Org to configure?"* Yes ⇒ go back to step 1 with the next Sales Org Name. No ⇒ move to Phase 7. Dry-run ⇒ skip Phase 6 entirely (for every Sales Org), record `pending — not run (dry-run)`.

## Phase 7 — Trigger the export (once per Sales Org, only after Phase 6's loop is done)

**Never trigger this until Phase 6's loop has finished for every Sales Org the user wants configured this run** — exporting mid-loop would run against an incomplete `CONFIGURED_SALES_ORGS` list. Once done, run once per `{salesOrgName, internalName}` entry in that list — every Sales Org gets its own export call, never a single shared one. `metaname` is that entry's `internalName` (the same value written to `Internal_Name__c` for that Sales Org's config in Phase 6) — this ties the export run back to the specific `RTR_Report_Configuration__c` it was scheduled for. Never use `sf api request rest` — it's a beta command with no `--json` flag at all (confirmed live, it errors `Nonexistent flag: --json`) that can change or be pulled without notice; use the sibling `scripts/sf-rest.js` instead, which fetches the org's instanceUrl/access token itself and makes the callout directly with Node's built-in fetch:
```bash
node ./scripts/sf-rest.js \
  --target-org <username> --method POST \
  --path "/services/apexrest/<NS_SEGMENT>measures/export/schedule" \
  --body '{"metaname":"<internalName>","salesorg":"<salesOrgName>","object":"promotionmeasures"}'
```
Capture `csvGuid` per Sales Org from the response — the schedule endpoint's response body field is actually named `requestId` (confirmed live), not `csvGuid`; use `requestId`'s value as the guid for Phase 8 and Phase 10 below. Dry-run ⇒ skip, record `pending — not run (dry-run)`.

## Phase 8 — Poll export status (once per Sales Org from Phase 7)

Small dedicated loop (the response shape — a flat `Status` field, not `applicationStatus`/`apps[]` — doesn't match a generic app-install poller, so this doesn't reuse `consumer-goods-tpe-dashboard-configure`'s `poll-status.js`). Run once per `(csvGuid, salesOrgName)` pair captured in Phase 7. Via the sibling `scripts/sf-rest.js`, not `sf api request rest`:
```bash
while true; do
  status=$(node ./scripts/sf-rest.js \
    --target-org <username> \
    --path "/services/apexrest/<NS_SEGMENT>measures/export/<csvGuid>/status?salesorg=<salesOrgName>" \
    | node -e "process.stdin.on('data',d=>console.log(JSON.parse(d).Status))")
  echo "export status: $status"
  case "$status" in
    Ready) echo "export ready"; break ;;
    Error|Aborted) echo "export failed: $status"; exit 1 ;;
    Queued|InProgress) sleep 30 ;;
  esac
done
```
`Ready` = terminal success, `Error`/`Aborted` = terminal failure, `Queued`/`InProgress` = keep polling.

## Phase 9 — Sync the `promotionmeasures` Data Stream

Phase 8's `Ready` status only confirms the export landed on the Processing services — the `promotionmeasures` Data Stream in Data Cloud still needs to ingest it before the exported measures show up downstream (KPI Sets, dashboards). This skill never triggers that sync itself — Data Stream sync/refresh isn't something this skill drives via `sf`/REST, and it's an action better left to the user to run interactively in Data Cloud setup.

**Run this once for the whole batch, not once per Sales Org** — the `promotionmeasures` Data Stream isn't scoped per Sales Org, so there's nothing to gain from asking after each one. Only ask once every Sales Org in `CONFIGURED_SALES_ORGS` has finished Phase 8's poll (whether `Ready` or otherwise recorded). This is a hard blocking gate, not a status update — pose it as an explicit yes/no confirmation question (the same way as the Phase 2 system-setting go-ahead and Phase 3 sync-trigger go-ahead), not as a plain narrated sentence that moves straight on to Phase 10: *"All exports have completed. Please go to Data Cloud → Data Streams → `promotionmeasures`, sync it, and wait until the sync is done (or wait until the scheduled sync completes). Has the sync finished?"* Do not proceed to Phase 10 on a generic "continue"/"next step" from the user — that answers a different question (moving the overall flow along), not this specific one (whether the Data Stream sync is actually done). Wait for an explicit confirmation before moving to Phase 10. Dry-run ⇒ skip, record `pending — not run (dry-run)`.

## Phase 10 — Abort (only if the user asks to)

```bash
node ./scripts/sf-rest.js \
  --target-org <username> --method POST \
  --path "/services/apexrest/<NS_SEGMENT>measures/export/abort/<csvGuid>?salesorg=<salesOrgName>&metaname=<internalName>"
```
Never call this unless the user explicitly requests an abort.

## Phase 11 — Report

Record pass/blocked/pending per phase (1-10 above) for the final report — this is exactly what `consumer-goods-tpe-dashboard-configure`'s corresponding step relays as its own result when this skill is invoked via delegation.
