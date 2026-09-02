---
name: consumer-goods-rtr-datacloud-export-configure
description: "Configure a Trade Promotion Management (TPM) org's RTR (Real Time Reporting) export pipeline to push promotion measures into Data Cloud (Data 360) for Trade Promotion Effectiveness (TPE) dashboards. Use when a customer or admin wants to set up the RTR export for Data Cloud measures, configure the RTR report for TPE, or as a delegated step from consumer-goods-tpe-dashboard-configure."
metadata:
  version: "1.0"
  domains: ["Consumer Goods"]
  relatedSkills:
    - "consumer-goods-tpe-dashboard-configure"
  cliTools:
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Setup RTR Data Cloud Export

Configures the Data-Cloud-targeted RTR exports: the `Data_Cloud_Enabled` system setting, a scoped SF Data Sync, an `RTR_Report_Configuration__c` record (with its `KPI_Set__c`) for Data Cloud export, and the export trigger/status/abort REST calls. Standalone and self-contained — runs on its own, or as a delegated step invoked by `consumer-goods-tpe-dashboard-configure`, which passes through its own already-collected username, dry-run flag, and GenieAdmin confirmation result.

**Distinct from a sibling CSV-export RTR skill** (if present in this org's checkout): that skill targets `Usage__c IN ('integrationmeta','reportmeta')` for CSV export to the CGCloud Processing Services host. This skill targets Data Cloud export. Same underlying `RTR_Report_Configuration__c` object and `KPI_Set__c` Apex patterns, different `Usage__c` values and `JSON__c` shape — this skill does not invoke or depend on that sibling.

**For now, this skill only supports `Usage__c = 'datacloudpromotionmeasuresmeta'`** (`JSON__c.object = "promotionmeasures"`) — it is hardcoded, never asked as an input. `datacloudaccountplanmeasuresmeta` (account-plan measures) is not yet wired up.

## Inputs and namespace detection

Read `references/inputs-and-namespace.md` before starting. It covers:
- The username/dry-run/GenieAdmin/TPM-Admin/namespace inputs that must be collected (or passed through by a calling skill) before Phase 1.
- The Sales Org / KPI Set / measure-codes / date-from inputs that Phase 6 collects lazily, per Sales Org, only once its existing-config check comes back empty.
- The namespace-detection procedure (`scripts/detect-namespace.js`) and the four `NS`/`NS_SEGMENT`/`NS_APEX`/`NS_FIELD` derivations used throughout every phase below.
- `scripts/render-apex.js` (Apex template rendering) and `scripts/resolve-id-by-name.js` (name-to-id lookups) both load `scripts/soql-escape.js` to escape substituted/queried literals for safe SOQL/Apex interpolation.

## Phases

Full step-by-step commands, queries, and Apex templates for every phase are in `references/procedure.md`. Run phases in order.

| Phase | Summary |
|-------|---------|
| 1 | Verify/assign `GenieAdmin` permission set; confirm `TPM Admin` persona assignment. |
| 2 | Upsert the `Data_Cloud_Enabled` system setting via anonymous Apex; confirm the write. |
| 3 | Trigger a scoped SF Data Sync against `System_Setting__c`, after capturing a baseline `Batch_Run_Status__c` Id. |
| 4 | Poll/verify that sync completed (`Done`/`Error`/`Fatal`/`Running`). |
| 5 | Verify the `datacloudpromotionmeasuresmeta` picklist value exists on `Usage__c` — if missing, stop and send the user to Setup (no programmatic fix exists). |
| 6 | Loop, one Sales Org at a time: resolve Sales Org Name → Id, reuse an existing `RTR_Report_Configuration__c` or collect KPI Set/measure-codes/date-from and create one, sync if changed, then ask whether to add another Sales Org. |
| 7 | Once Phase 6's loop is fully done, trigger the export once per configured Sales Org via `scripts/sf-rest.js` (never `sf api request rest`); capture `requestId` as the export guid. |
| 8 | Poll each Sales Org's export status (`Ready`/`Error`/`Aborted`/`Queued`/`InProgress`) via `scripts/sf-rest.js`. |
| 9 | Once every Sales Org has finished polling, ask the user to sync the `promotionmeasures` Data Cloud Data Stream themselves and get explicit confirmation it finished — this skill never triggers that sync. |
| 10 | Abort an in-flight export via `scripts/sf-rest.js` — only if the user explicitly asks. |
| 11 | Report pass/blocked/pending per phase. |

## Rules

- Never assign a permission set, write a record, or trigger a sync/export without an explicit user go-ahead first.
- Never guess or hardcode `Batch_Name__c` — identify the sync's `Batch_Run_Status__c` row by recency against the captured baseline Id, and log the full row set.
- Never attempt to programmatically add a missing `Usage__c` picklist value — the user must add it manually via Setup (link in Phase 5, `references/procedure.md`).
- Never ask for a Usage type — this skill is hardcoded to `Usage__c = 'datacloudpromotionmeasuresmeta'` / `JSON__c.object = "promotionmeasures"` for now.
- When the requested export type is anything other than promotion measures (e.g. `datacloudaccountplanmeasuresmeta`/account-plan measures): state the limitation, then stop or ask if the user wants the promotion-measures export instead for that Sales Org. Do not provide field-by-field manual configuration instructions for the unsupported path — no suggested `Usage__c`/`JSON__c` values, no picklist-add walkthrough. Offering a workaround recipe for the exact path this skill refuses is scope creep, not help. Report the run as blocked, not partially-passed.
- Never skip Phase 6's existence check (keyed on `Usage__c` + `Sales_Organization__c`) — and never overwrite an existing `RTR_Report_Configuration__c` found by that check without a separate, explicit user go-ahead.
- Never trigger Phase 7's export before Phase 6's per-Sales-Org loop is fully done — always ask whether to add another Sales Org before moving from Phase 6 to Phase 7.
- Always give the user a chance to supply a custom `Internal_Name__c` (Phase 6 step 4) — default to `"Data 360 Promotion Measures Export <Sales Org Name>"` (no hyphen) only if they decline. This value is also `metaname` in Phase 7's export — never invent a different one for that call.
- Phase 7 exports **once per Sales Org**, never once for the whole run.
- Both the Sales Org and the KPI Set are given as **Names** by the user, resolved to Ids by query — this skill never creates a `Sales_Organization__c`, a `KPI_Set__c`, or KPI Set junction rows.
- Never sync a Sales Org's config in Phase 6 unless this run actually created it — reusing an existing config as-is is a no-op, no sync call.
- Never call the abort endpoint unless the user explicitly asks to abort.
- Never claim Phase 9 is done on Phase 8's `Ready` status alone — always get the user's explicit confirmation that the `promotionmeasures` Data Stream was synced, once for the whole batch, before moving to Phase 10.
- Never hardcode the namespace in a REST path, Apex snippet, or SOQL query — always use the caller-passed or self-detected `NS`/`NS_SEGMENT`/`NS_APEX`/`NS_FIELD`.
- This skill only calls `global` Apex classes, REST endpoints, or the anonymous-Apex templates in its own `scripts/` directory — never a `public`/`private` method directly, and never a script or template from outside this skill's own directory.

## Report

At the end of a run, give the user a structured status per phase (1-10): pass / blocked / pending, with the specific blocking reason and remediation click-path where applicable (e.g. the Setup path for a missing picklist value). Call out anything skipped due to dry-run or a declined confirmation.

**When invoked via delegation** (the calling skill used the `Skill` tool to reach this file, rather than the user directly): this report is an intermediate result, not the end of the task. Return it to the calling skill and let it continue with its own next phase — do not present this report to the user as the final answer and stop. Only surface this report directly to the user when this skill was invoked standalone.
