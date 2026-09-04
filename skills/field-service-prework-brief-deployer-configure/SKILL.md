---
name: field-service-prework-brief-deployer-configure
description: "Deploy the deterministic half of Einstein Pre-Work Brief on Field Service Mobile to a target org — prompt template, Lightning Data Service, licenses and permission sets, the Work Order layout field, and a scheduled test Work Order. Use this skill when a user asks to deploy, set up, enable, or configure Einstein Pre-Work Brief on Field Service Mobile."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Field Service Pre-Work Brief Deployer

**Deploy the deterministic half of Einstein Pre-Work Brief on Field Service Mobile via `execute_api`.**

This skill takes an org whose Einstein for Field Service add-on is already provisioned and performs every automatable step to stand up Pre-Work Brief: it deploys three metadata artifacts, assigns licenses and permission sets, exposes the Work Order field on the technician's layout, wires a test Work Order scheduled in today's window, and **activates the prompt template via the Connect API**. The workflow is fully automatable end-to-end — there are no irreducibly manual steps. On-device rendering verification (confirming grounding produces job-specific content) is owned by the coordinating Pre-Work Brief skill, not this deploy primitive.

This skill is the **judgment-free deploy primitive.** Org diagnosis / routing (STOP if unprovisioned), technician selection, and the fresh-vs-existing test-data decision are resolved by the coordinating skill and passed in as inputs / a choice point.

## What it does

- **Prompt template** — deploys the `einstein_gpt__fieldServicePreWorkBrief` GenAiPromptTemplate (`Pre_Work_Brief`) as Published.
- **Lightning Data Service** — enables Lightning Data Service on the Field Service settings (the `lsdkForFieldServiceMobilePref` org preference; without LDS the brief renders blank on mobile).
- **Licenses + permission sets** — assigns the Einstein for Field Service PSL + permission sets to an admin and a pilot technician.
- **Field-level access** — deploys `PreWorkBrief_Field_Access` and exposes `WorkOrder.PreWorkBriefPromptTemplate` on the technician's layout with FLS.
- **Test data** — creates a test Work Order + Service Appointment + Assigned Resource scheduled in today's window, pointed at the deployed template (or points an existing Work Order at it).

## Inputs

- **Target org** — an org whose Einstein for Field Service add-on is provisioned. If the add-on is absent the org is unprovisioned — **STOP**; the coordinating skill owns this routing.
- **Pilot technician** — username + user Id, selected by the coordinating skill, with an active `ServiceResource`.
- **Test-data mode** — `fresh` (create a clean test Work Order chain) or `existing` (point a supplied real Work Order at the template and move its Service Appointment into today's window). Default `fresh`.

## Preconditions

- The Einstein for Field Service add-on is provisioned (the Einstein for Field Service permission-set license is present).
- The admin holds Customize Application + Manage Profiles and Permission Sets.
- Einstein generative AI base setup (including Data 360 grounding) is complete on the org.
- A pilot technician has been selected and has an active `ServiceResource`.

## Happy path (fresh test data)

Verify provisioning → assign licenses and permission sets → verify permset assignments → detect existing template → deploy prompt template → verify template deployed → read Field Service settings → deploy LDS setting → verify LDS enabled → deploy field-access permset → read Work Order layout → add field to layout → verify field on layout → create test Work Order → create Service Appointment → assign resource → verify test Work Order scheduled → **resolve template version → activate prompt template (Connect API) → verify activation**.

**Existing-test-WO branch** — when test-data-mode is `existing`, skip create-test-workorder / create-service-appointment / assign-resource and run point-existing-workorder instead: update a real Work Order's `PreWorkBriefPromptTemplate` and move its Service Appointment into today's window.

Every step is idempotent — it checks org state before it writes, so re-running applies zero changes.

## Ordering is load-bearing

- **Assign the admin permission sets (including `EinsteinGPTPromptTemplateManager`) BEFORE deploying the prompt template.** If the admin lacks it, the Pre-Work Brief template type silently vanishes from Prompt Builder and the deploy fails with no error message — just a missing dropdown option.
- **Enable LDS (`lsdkForFieldServiceMobilePref`) before on-device use** or the brief renders blank on mobile.

## Gotchas

- **`GenAiPromptTemplate` is NOT SOQL/REST queryable.** Detect it and resolve its `0hf`-prefixed Id via the Metadata deep-read by name (`type=GenAiPromptTemplate`, `fullName=Pre_Work_Brief`), not a query.
- **Send the template deploy bodies as JSON objects, not serialized strings.**
- **Whole-record write footguns — two different mechanisms, neither a raw MDAPI deploy.** `deploy-lds-setting` and `add-field-to-layout` both write existing whole records, but differently. **LDS** goes through the Field Service settings controller (`saveFieldServiceSettingsConfig`): a per-field `isChanged<Field>` partial-patch whose body **must be wrapped under a top-level `userSettings` key** — `{"userSettings": {"lsdkForFieldServiceMobilePref": true, "isChangedLsdkForFieldServiceMobilePref": true}}`. A flat body (fields at the top level) returns **500 `CONTROLLER_ERROR` NullPointerException (`userSettings is null`)**. **The Work Order layout** is a **Tooling API `Layout.Metadata` round-trip** that IS full-replace: read the current Metadata first (a Tooling `Layout` GET — `read-workorder-layout`'s `describe/layouts` is only for checking placement), add only the new field, and PATCH the whole object back (omitted keys reset to default). On the write, null out `feedLayout` and drop the `ServiceReportRelatedList` related list or the PATCH 400s (see the layout step's notes). This is NOT SOAP MDAPI and NOT `/headless/metadata` (unrouted) — it's Tooling REST over dispatch passthrough.

## Activate the prompt template (Connect API)

The template deploys **Published, not Active** — until it is activated it does not appear in the runtime catalog and the mobile app fails with *"We hit a snag."* Activation IS programmatic via the Connect API (available since v65.0 / API 258):

```http
PUT /services/data/v67.0/einstein/prompt-templates/{devName}/versions/{versionId}/status?action=activate&ignoreWarnings=false
Body: {}
```

- **Resolve the `versionId` first.** GET `/services/data/v67.0/einstein/prompt-templates/{devName}` and read `childRelationships.GenAiPromptTemplateVersions[].fields.Id.value` (the `3vN`-prefixed version Id). This GET works even while the template is inactive/absent from the catalog.
- On success the response is `isSuccessful:true`, `statusCode:"200"`, with an `additionalData.wrappedMap.summary.overallSeverity` of `SAFE`. The template-level `IsActive` flips to `true` and `ActiveVersionId` is populated (the version's own `Status` stays `Published` — "Published" at the version level *is* "Active" at the template level).
- **Not callable from Apex.** The endpoint is `@ConnectHidden(from=Apex)`; call it through `execute_api` (or `sf api request rest --method PUT`), not `ConnectApi`. This is why the earlier Apex `ConnectApi.EinsteinLLM` and Tooling/metadata attempts failed — along with a wrong URL shape (`/activate` rather than `/versions/{id}/status?action=activate`) and too-early API versions (v62–v66).
- `verify-activation` — a runtime prompt-template-catalog read (`GET /einstein/prompt-templates?pageSize=200`, confirm `Pre_Work_Brief` now appears) — is chained immediately after to confirm activation landed.

*Live-verified against a non-prod org 2026-07-22: `IsActive` `False`→`True`, `ActiveVersionId` null→populated, and the template appeared in the runtime catalog on the same call.*

## Scope boundary — on-device rendering

On-device verification (the technician opening the Field Service mobile app and confirming the brief renders job-specific content in the Overview tab) is **out of scope for this deploy primitive** and owned by the coordinating Pre-Work Brief skill. Note that `verify-activation` confirms the template is Active, but only on-device rendering confirms Data 360 grounding is actually producing job-specific content — a distinct check the coordinating skill is responsible for. There is no headless surface that returns what the technician sees on the device.

## Source

Authored from the sf-skills-internal coordinating skill `field-service-prework-brief-configure` (+ its `references/` files) and Salesforce Help for Einstein Pre-Work Brief. Live-validated against a dispatcher org. The harness derives the ordered, typed SOR from this skill on each run.
