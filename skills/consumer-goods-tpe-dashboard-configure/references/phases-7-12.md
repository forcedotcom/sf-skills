# Phases 7-12 — Data Kit, Business Period Export, RTR Export, Data Transform, App Install, KPI Customization

## Phase 7 (Step 7) — TPM Accruals Data Kit for TPE (delegated)

Invoke the `consumer-goods-tpe-datakit-deploy` skill via the `Skill` tool, passing through:

- TPM admin username + dry-run flag (Inputs).
- The permission set(s) for the TPM Admin persona (Phase 2) and GenieAdmin (Phase 3) confirmation results, so it doesn't re-ask/re-query either.
- The detected `NS` (raw namespace string) from the Namespace detection step, so it doesn't re-detect.

`consumer-goods-tpe-datakit-deploy` accepts all of these as its own inputs (it also runs standalone, deriving them itself when not supplied). Treat its final report (pass/blocked/pending) as this phase's result and fold it into the overall report. **When `consumer-goods-tpe-datakit-deploy` returns, continue directly to Phase 8 in this same run — its own "Report" section is an intermediate result for this skill, not a signal to stop.**

## Phase 8 (Step 8) — Export TPM Business Period data

**Two distinct `salesorg` values — do not conflate them:** the `OffPlatformCallout` constructor argument is tenant/substrate routing only (must be a real Hyperforce-substrate Sales Org, called exactly once); the JSON body's `"salesorg":"*"` is a business-level "export for every sales org" parameter, not a platform-level wildcard.

This step must stay anonymous Apex, not a direct REST call to `ScheduleRTRExportService` (`/measures/export/schedule`, the same endpoint `consumer-goods-rtr-datacloud-export-configure` Phase 10 calls): that REST resource reads a single `salesorg` field out of its JSON body and uses that same value for **both** tenant/substrate routing (`SalesOrgSubstrate` mode — `SalesOrganizationServiceWOSharing.getTenantSubstrateEnum(salesorg)`) and the forwarded payload. `"*"` doesn't resolve to a real `Sales_Organization__c`, so it can't be used for routing — there's no way to decouple a real routing Sales Org from the payload's wildcard through that REST resource. The template below (run via `sf apex run`) keeps that decoupling: a real Sales Org drives routing via the `OffPlatformCallout` constructor; the JSON body's `salesorg` stays `"*"`.

1. Query for a routing Sales Org (never hardcode one), with `NS_FIELD` prefixed on the custom object and custom field (`Name` is standard, no prefix):
   ```bash
   sf data query --target-org <username> \
     --query "SELECT Name FROM <NS_FIELD>Sales_Organization__c WHERE <NS_FIELD>Tenant_Substrate__c = 'Hyperforce_AWS' LIMIT 1"
   ```
   Zero rows ⇒ **block** — no Hyperforce-substrate Sales Org to route `SCHEDULE_RTR_EXPORT` through. Never fall back to a GCP-substrate org.
2. Render and run the template, passing that `Name` and `NS_APEX` (the sibling `scripts/render-apex.js`, same substitution pattern as `consumer-goods-rtr-datacloud-export-configure`'s templates):
   ```bash
   node ./scripts/render-apex.js scripts/schedule-business-period-export.apex \
     --var NS_APEX=<NS_APEX> --var SALES_ORG=<hyperforceSalesOrgName>
   sf apex run --target-org <username> -f <rendered-path> --json
   ```
   `sf apex run` provisions its own temporary trace flag for the execute-anonymous call automatically — no separate "enable debug logs" step is needed, and none should be asked of the user. Read the response back from the debug log line `SCHEDULE_RTR_EXPORT_RESPONSE=<response>` in the `--json` output's `result.logs`.
3. Inspect the returned response for a 2xx; log it in full. The response body field is `requestId` (confirmed live — not `csvGuid`, despite sharing the schedule endpoint used elsewhere); use its value as `<requestId>` below. Poll its status with the shared poller — its flat `{"Status": "..."}` body shape fits `poll-status.js`'s single-field contract just as well as the app-install responses in Phases 6 and 11 do. **The `salesorg` query param on this status call is tenant/substrate routing, not the business-level wildcard** — pass the same real Hyperforce-substrate Sales Org Name (`<hyperforceSalesOrgName>`) resolved in step 1/2, never the JSON body's `"*"`; passing `"*"` here (confirmed live) fails with `CGCloudException: {"reason":"CONFIGURATION","message":"Sales Org \"*\" not found."}`.
   ```bash
   node ./scripts/poll-status.js --target-org <username> \
     --path "/services/apexrest/<NS_SEGMENT>measures/export/<requestId>/status?salesorg=<hyperforceSalesOrgName>" \
     --status-field Status \
     --success-values Ready \
     --failure-values Error,Aborted \
     --interval-seconds 30 --max-wait-seconds 900
   ```
   `Ready` = terminal success, `Error`/`Aborted` = terminal failure, `Queued`/`InProgress` = keep polling (timeout while non-terminal ⇒ not a failure — a later run can re-poll).
4. Record pass/blocked/pending.
5. **Sync the `tpmbusinessperiod` Data Stream.** Step 3's `Ready` status only confirms the export landed on the Processing Services host — the `tpmbusinessperiod` Data Stream in Data Cloud still needs to ingest it before the exported business-period data shows up downstream. This skill never triggers that sync itself — Data Stream sync/refresh isn't something this skill drives via `sf`/REST, and it's an action better left to the user to run interactively in Data Cloud setup. Only ask once step 3 reached `Ready` (skip if step 3 failed or is still pending). This is a hard blocking gate, not a status update — pose it as an explicit yes/no confirmation question, not a plain narrated sentence that moves straight on to Phase 9: *"The tpmbusinessperiod export has completed. Please go to Data Cloud → Data Streams → `tpmbusinessperiod`, sync it, and wait until the sync finishes (or wait for the scheduled sync). Has the sync finished?"* Do not proceed to Phase 9 on a generic "continue"/"next step" from the user — that answers a different question (moving the overall flow along), not this specific one (whether the Data Stream sync is actually done). Wait for an explicit confirmation before moving to Phase 9. Dry-run ⇒ skip, record `pending — not run (dry-run)`.

## Phase 9 (Step 9) — Data Cloud measures RTR export (delegated)

Invoke the `consumer-goods-rtr-datacloud-export-configure` skill via the `Skill` tool, passing through:

- TPM admin username + dry-run flag (Inputs).
- The detected `NS` (raw namespace string) from the Namespace detection step, so it doesn't re-detect.
- The GenieAdmin confirmation result from Phase 3 (so it isn't re-queried).

Treat its final report as this phase's result and fold it into the overall report. **When it returns, continue directly to Phase 10 in this same run — do not stop here.**

## Phase 10 (Step 10) — TPM_PROMOTION_MEASURE Data Transform

1. **Wait until all CRM Data Streams are synced before running the transform.** The TPM_PROMOTION_MEASURE Data Transform reads from CRM Data Streams — running it before they've finished syncing produces stale or incomplete measures. This cannot be verified programmatically — never check or infer stream status yourself (e.g. via SOQL against `DataStream`/`DataStreamHistory`, Tooling/REST calls, or any other query); the user is the sole source of truth here. Explicitly ask the user for a **yes/no confirmation** (e.g. via the `AskUserQuestion` tool if available, with Yes/No options) — never state it as a plain sentence the user could mistake for informational text: *"Before we run the Data Transform, please make sure all the relevant CRM Data Streams have finished syncing — every one should show Last Run Status = Success. Have all of them reached Success? (You can find the list at Data Cloud → Setup → Data Kits → TPM Accruals → Data Stream Bundles → expand the TPM section.)"* Do not proceed to step 2 on a generic "continue"/"next step" — wait for explicit confirmation.
   - If the user says any stream isn't `Success` yet: `None` — has never run; ask them to manually refresh the stream. `Pending` — a run is already queued; ask them to just refresh the status (not the stream itself — it's already running, refreshing the stream would just requeue it). Then re-ask the same yes/no question.
   Dry-run ⇒ skip, record `pending — not run (dry-run)`.
2. **Ask before running — Data Cloud credit consumption.** Tell the user plainly: *"Running the TPM_PROMOTION_MEASURE Data Transform will consume Data Cloud credits proportional to the volume of promotion-measure data processed. Proceed?"* Never trigger without an explicit yes. In dry-run, skip and record `pending — not run (dry-run)`.
3. On confirmation, hand off to the shared script. This Data Transform's name is never namespaced, regardless of the package namespace detected earlier — pass it as-is:
   ```bash
   node ./scripts/run-data-transform.js --target-org <username> --transform-name TPM_PROMOTION_MEASURE
   ```
4. Record pass/blocked/pending, the final `lastRunStatus`, and (on failure) `lastRunErrorMessage`. A timeout while `lastRunStatus` is still non-terminal after the script's 1-hour default wait is not a failure — a later run can re-poll (pass `--max-wait-seconds` explicitly for a longer window if needed).

## Phase 11 (Step 11) — Install TPE Analytics App

1. **Prerequisite check** — Tableau Next enabled (Phase 5), GenieAdmin (Phase 3), C360 SDM `SuccessStatus` (Phase 6), and data kit deployed (Phase 7) are already independently verified earlier in this run; treat as a fast confirmation, not a re-block, when all four already passed. Otherwise re-check and block on whichever failed.
2. **Install trigger** — the confirmed TPE template id is `sfdc_internal__Trade_Promotion_Effectiveness` (not the MCP tooling's built-in ids). Via `scripts/sf-rest.js`, not `sf api request rest`:
   ```bash
   node ./scripts/sf-rest.js \
     --target-org <username> --method POST \
     --path "/services/data/v67.0/app-framework/apps" \
     --body '{"label":"TPE_Analytics","name":"TPE_Analytics","templateSourceId":"sfdc_internal__Trade_Promotion_Effectiveness","runtimeMethod":"Async"}'
   ```
   Extract `app.id`. Never use `Sync` — this is a 400-500 task pipeline (~15-20 minutes).
3. **Poll** with the same shared poller, a longer window this time:
   ```bash
   node ./scripts/poll-status.js --target-org <username> \
     --path "/services/data/v67.0/app-framework/apps/<appId>" \
     --status-field applicationStatus \
     --success-values SuccessStatus,SuccessWithWarningsStatus \
     --failure-values FailedStatus \
     --interval-seconds 60 --max-wait-seconds 1200
   ```
4. `SuccessStatus` / `SuccessWithWarningsStatus` ⇒ record success (note warnings). Timeout while `InProgressStatus` ⇒ inform the user it's still installing — a later run can re-poll; not a failure.

   `FailedStatus` ⇒ **find the actual reason before stopping.** `applicationStatus: FailedStatus` alone carries no detail — the per-requirement failure message only lives on the install's async execution graph (its Domino runtime), never on the app resource itself. Use the sibling script rather than hand-parsing this (confirmed live: the graph is deeply nested and its own failure-message template is inconsistently formatted):
   ```bash
   node ./scripts/find-failure-reason.js --target-org <username> --app-id <appId>
   ```
   Prints one line of JSON: `{"failedNodes":[{"node","statusMessage"}],"dmoNotAvailable":[<DMO API names>]}`. `failedNodes` is every failed requirement's human-readable message from the most recent install attempt — log it in full; the underlying message is generic ("...enabled or minimum required set of fields mapped in your org. Please make sure required Datakits are installed and data stream is deployed."), so don't assume every failure is DMO-related.

   - **`dmoNotAvailable` is non-empty** ⇒ a "DMO not available" failure. Every DMO name it can surface here is one this org's `consumer-goods-tpe-datakit-deploy` Phase 4 DMO-mapping deploy is responsible for (e.g. `ssot__BusinessPeriod__dlm`, `MeasureDefinition_std__dlm`, `ssot__PromotionOffer__dlm`, `ssot__Promotion__dlm`, `ssot__Account__dlm`, `ssot__PromotionAccount__dlm`, `ssot__PromotionTemplate__dlm`, `ssot__ProductCategory__dlm`, `PromotionProductMeasure_std__dlm`, `PromotionOfferProductMeasure_std__dlm`) — treat any other DMO name it lists the same way. Whether a DMO's mapping is actually active in the org's Data Cloud tenant isn't exposed over any documented REST/SOQL API (confirmed live — `ssot/data-model-objects` lists DMO definitions, not per-org mapping/activation state) — ask the user directly, one question per DMO, via `AskUserQuestion` (Yes/No):
     *"The TPE Analytics App install failed because `<DMO>` isn't available in Data Cloud. Please check Setup → Data Cloud → Data Model → find `<DMO>` → its Mapping tab. Is `<DMO>` mapped to a data source object in this org?"*
     - **No (not mapped)** ⇒ something went wrong with the data kit deployment itself, not with this phase. **Stop the entire `consumer-goods-tpe-dashboard-configure` run here** — don't just record this phase as blocked and continue. Point the user back to Phase 7 (`consumer-goods-tpe-datakit-deploy`), specifically its Phase 5 `DataKitDeploymentLog` verification, to find and fix the actual deployment error. Only re-attempt this phase after that comes back clean.
     - **Yes (mapped)** ⇒ a known Data Cloud quirk: deploying `dataSrcDataModelFieldMap` metadata doesn't always fully activate the mapping in the org's Data Cloud tenant until it's opened and saved once in the UI. Ask the user to open that same Mapping tab and click **Save** (no field changes needed) for `<DMO>`'s mapping, confirm it saved without error, then retry this phase from step 2 — POST a new install rather than re-polling the failed `appId`.
   - **`failedNodes` is non-empty but `dmoNotAvailable` is empty** ⇒ a different requirement failed. Relay the exact `statusMessage`(s) to the user and stop this phase — don't guess a remediation for a failure shape this skill hasn't seen before.
   - **`failedNodes` is empty** ⇒ the graph-level detail wasn't available yet (e.g. activities not populated). Fall back to reporting bare `FailedStatus` and point the user to the install's `installationHistoryUrl` / `appHubUrl` (already captured from the create response in step 2) for a manual look in Setup.
5. Record the app id, name, and final status.

## Phase 12 (Step 12) — Customize TPE dashboard KPIs (delegated, optional)

Implements Salesforce Help's [Customize Trade Promotion Effectiveness Analytics
Dashboards](https://help.salesforce.com/s/articleView?id=ind.tpe_tpm_tab_next_dashboard_customize.htm&type=5) —
specifically **Customization Scenario 1** ("Use Custom KPIs with Standard Dashboards"). Let the user
know this when asking (step 1 below), so they can cross-reference the doc if they want more detail
before deciding.

1. **Ask before proceeding.** Tell the user plainly: *"The base TPE Analytics app is installed with
   its standard KPIs. Would you like to customize the Promotion/Tactic dashboards with your own KPI
   measure codes now? (For more details see scenario 1 in https://help.salesforce.com/s/articleView?id=ind.tpe_tpm_tab_next_dashboard_customize.htm&type=5)"* Never proceed on anything other than an explicit yes. On no/undecided, skip
   this phase entirely and record `skipped — not requested` — note that `consumer-goods-tpe-dashboard-custom-kpi-configure` can
   still be run standalone later. In dry-run, still ask (it's a plan-only decision); record
   `pending — not run (dry-run)` if yes, `skipped — not requested` if no.
2. **Prerequisite check** — Phase 11's TPE Analytics app install must have reported
   `SuccessStatus`/`SuccessWithWarningsStatus`; `consumer-goods-tpe-dashboard-custom-kpi-configure` clones that app's Extended
   TPM Analytics SDM and dashboards, so it cannot run against a missing/failed install. If Phase 11
   didn't succeed, skip this phase and note it's blocked on Phase 11, not independently broken.
3. On a yes, collect `consumer-goods-tpe-dashboard-custom-kpi-configure`'s own inputs now (suffix, per-slot overrides — see
   its `SKILL.md`'s "Inputs to collect first" for the exact shape), then invoke it via the `Skill`
   tool, passing through:
   - TPM admin username + dry-run flag (Inputs).
   - The suffix and per-slot `--overrides` just collected.
4. Treat its final report (pass/blocked/pending per artifact) as this phase's result and fold it
   into the overall report. This is the only phase in this skill that ever mutates the TPE Analytics
   app's semantic model/dashboards after Phase 11 — `consumer-goods-tpe-dashboard-custom-kpi-configure` never touches the base
   artifacts themselves, only adds suffixed clones alongside them (see its own `SKILL.md`). **This is
   the last phase — once it returns (or is skipped per step 1), proceed straight to this skill's own
   overall Report below; don't stop mid-run waiting on anything further from the sub-skill.**

## Shared poller

`scripts/poll-status.js` — generic, reused by Phases 6 and 11 (and any future async-install step): calls `restRequest()` from the sibling `scripts/sf-rest.js` on each tick (a direct authenticated HTTP GET, not `sf api request rest` — that command is beta, has no `--json`, and can change or be pulled without notice), reads `--status-field` off the response (handles both a single-object and a first-array-element shape), stops on a success/failure value or timeout, non-zero exit on failure/timeout. See its own header comment for the full flag list. Do not write a second poll loop — extend this one if a new step needs different response shape handling.

## Diagnosing an app-framework install failure

`scripts/find-failure-reason.js` — used by Phase 11's `FailedStatus` branch (and reusable as-is for Phase 6's, if it ever needs the same depth of detail): `applicationStatus`/`requestStatus` values like `FailedStatus` never carry a reason on the app resource itself. The reason only exists on the install's Domino runtime — walk `GET /app-framework/apps/<appId>/activities` to the latest attempt's `runtimeRequest.id`, then `GET /domino/runtimes/<runtimeRequestId>` to its `definition.nodes`, and collect every node whose `results.validate.taskStatus` starts with `Fail`. Confirmed live against a real failure (an org with a DMO mapping deliberately removed): the readiness-check nodes for each required DMO report `-1` when the DMO can't be queried in Data Cloud, and the paired requirement node's `statusMessage` reads *"Sorry! You don't have [`<dmo>__dlm`] enabled or minimum required set of fields mapped in your org. Please make sure required Datakits are installed and data stream is deployed."* — the script extracts the DMO API name out of that message into `dmoNotAvailable`. Do not hand-parse this graph inline elsewhere; extend this script if a new failure shape needs handling. Note its own failure-message template is inconsistently formatted (confirmed live — one DMO's message is missing its opening `[`) and HTML-entity-encoded; the script normalizes both before matching/printing.

## Rules

- Never authenticate on the user's behalf — if `org-status` shows disconnected, stop and ask the user to log in themselves.
- Never run `sf org display --json` directly and read its output — always go through `scripts/sf-rest.js`'s `org-status` subcommands, which strip `accessToken` before printing.
- Never proceed past the Namespace detection step on a managed-package org below Consumer Goods Cloud version 262.2 — state both the installed and required version numbers and stop.
- Never proceed past Phase 1 until the user has explicitly confirmed (yes/no) that Hyperforce Processing Service pairing is ready. Phase 1 only ever asks about Hyperforce, never GCP.
- Never assign a permission set, write a record, or trigger an install without an explicit user go-ahead first.
- Never attempt to enable or verify Tableau Next via any REST/Tooling/Connect API call, or by querying for the `TableauIncludedAppManager` permission set — there's no reliable programmatic path (the enable APIs are confirmed unavailable live against a test org on `v63.0`, and the permission set isn't a reliable enablement signal); Phase 5 always asks the user directly and defers enablement to the Setup UI.
- Never hardcode a Sales Org code — always query for one with the required `Tenant_Substrate__c`.
- Never hardcode the namespace (`cgcloud_dev`, `cgcloud`, or any other string) in a REST path, Apex snippet, or SOQL query — always use the detected `NS`/`NS_SEGMENT`/`NS_APEX`/`NS_FIELD` from the Namespace detection step.
- Never claim an async install succeeded on anything other than `SuccessStatus`/`SuccessWithWarningsStatus` (apps), a user-confirmed ready `state` (tenant status), or a non-`FAILURE` terminal `lastRunStatus` with a fresh `lastRunDate` (data transform).
- A poll timeout while still in an in-progress state is **not** a failure — report it as still-running and let a later run re-poll.
- This skill never deploys Apex. It only calls `global` Apex classes, REST endpoints already shipped in the target org's installed package, or the anonymous-Apex templates in its own `scripts/` directory — never a `public`/`private` method directly, never a class this skill deploys itself (skills are distributed independently of this repo; see the architecture rule on self-contained skills), and never a script or template from outside this skill's own directory.

## Report

At the end of a run, give the user a structured status per phase (1-12): pass / blocked / pending, with the specific blocking reason and remediation click-path where applicable. Call out anything skipped due to dry-run, a declined confirmation, or (Phase 12) the customer opting out of KPI customization.
