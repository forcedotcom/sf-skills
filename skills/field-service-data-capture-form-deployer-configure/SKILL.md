---
name: field-service-data-capture-form-deployer-configure
description: "Assemble a Data Capture Flow from a JSON spec and deploy it to a connected Field Service org via the Tooling Flow sObject (JSON Metadata, no XML). Use when given a data-capture spec JSON and asked to build or deploy a DataCaptureFlow."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Build a Data Capture Form (Field Service Mobile)

This skill takes an intermediate JSON spec and produces a deployed Salesforce Flow with `processType=DataCaptureFlow`. It assumes the spec is already correct and approved — confirmation with the user happens upstream in the design skills.

> **Runtime contract:** every org interaction in this skill is a REST call
> dispatched through the Codey runtime (`execute_api` locally / the hosted
> Headless 360 MCP in shared surfaces). This skill has **no dependency on the
> execution environment** — no `sf` CLI, no shell scripts, no local Python, no
> temp files. Auth probes, record reads, and record writes are single REST
> calls; the Flow XML is authored by the agent inline from the reference docs.
> Do not shell out.

## Input contract

A JSON file matching the schema in [reference/field-types.md](reference/field-types.md) and (optionally) [reference/post-screen-automation.md](reference/post-screen-automation.md). Canonical examples:

- [examples/sample-spec.json](examples/sample-spec.json) — minimal screens-only flow.
- [examples/inventory-transfer-spec.json](examples/inventory-transfer-spec.json) — full example with Repeater, Radio, visibility, decision, lookups, loop, and record-create.

Required top-level keys: `formTitle`, `formType`, `screens`. Optional: `postScreen`.

## Output

A Data Capture Flow created in the org via a single Tooling API call — `POST /services/data/vXX.0/tooling/sobjects/Flow` with a JSON `Metadata` body (no `.flow-meta.xml`, no zip, no SFDX project). The flow is created in `Draft` status and the user activates it themselves in Flow Builder.

## Workflow

### 1. Verify org auth

Confirm the connected org is reachable with a cheap auth probe — dispatch `SELECT Id FROM Organization LIMIT 1` (`GET /services/data/vXX.0/query`):

- 2xx with `totalSize=1` → the session token is live; continue.
- 401/403 → the org needs re-authentication. Surface that to the user and **stop**; do not deploy. (The Codey runtime resolves and refreshes the connected org — this skill does not manage org aliases.)

### 2. Pick a Flow API name

If the design skill already supplied `<FlowApiName>`, use it. Otherwise derive from `formTitle`: PascalCase, no spaces, must match `^[A-Z][A-Za-z0-9_]*$`. If the title can't be coerced, ask the user.

### 3. Build the Flow Metadata JSON

Assemble the flow's `Metadata` object **inline** from the spec — the Tooling `Flow` sObject takes a JSON `Metadata` blob, so there is no XML to compile and no converter to run. Follow the JSON shape and field mappings in [reference/flow-metadata-json.md](reference/flow-metadata-json.md) and [reference/field-types.md](reference/field-types.md).

Notes:
- The JSON `Metadata` is the exact same shape the Tooling `Flow` GET returns (`GET /tooling/sobjects/Flow/{id}` → `Metadata`), so you can retrieve a known-good sibling flow as a live reference before composing.
- **Dedupe choices** across the entire flow — two fields with `["Good","Fair","Poor"]` share the same three entries in the top-level `choices` array.
- Repeater children are nested as `fields` entries inside the parent Repeater field.
- `Signature`, `UploadFile`, `UploadImage`, and `Images` auto-wire `parentRecordId` / `recordId` to the standard DataCaptureFlow input variables. They deploy as functional components, no Flow Builder cleanup required.
- `Lookup` requires a `lookupObject` spec key; without it, emit the labeled `dcTextInput` placeholder. `FileView` requires a `fileName`; same fallback. Collect any such fallbacks and surface them in step 5.
- Self-check before deploying: `processType` is `DataCaptureFlow`, `environments` includes `Offline`, and the three input variables (`parentObjectType`, `parentRecordId`, `recordId`) are present.

### 4. Deploy to org

Create the flow with a single Tooling API call — dispatch `POST /services/data/vXX.0/tooling/sobjects/Flow` with body:

```json
{
  "FullName": "<FlowApiName>",
  "Metadata": { "processType": "DataCaptureFlow", "environments": ["Offline"], "label": "...", "screens": [ ... ], "choices": [ ... ], "variables": [ ... ], "status": "Draft" }
}
```

- `FullName` is the Flow API name; `Metadata` is the object you assembled in step 3.
- A 201 with `success: true` returns the new Flow version id. `Status` stays `Draft` (set `Metadata.status: "Active"` only if the user asked to activate on create — the default is Draft so the user reviews in Flow Builder first).
- On a 400, the response body's `message` carries the Flow validation error — diagnose against step 5's failure table.

### 5. Report back

On success:
- Look up the FlowDefinition Id with a Tooling API query — dispatch `GET /services/data/vXX.0/tooling/query` with `SELECT Id, ActiveVersionId FROM FlowDefinition WHERE DeveloperName = '<FlowApiName>'`.
- Print a clickable Flow Builder URL: `<instanceUrl>/builder_platform_interaction/flowBuilder.app?flowId=<id>`.
- List screens, total field count, and any fallback fields (Lookup with no `lookupObject`, FileView with no `fileName`) the user needs to wire up in Flow Builder.
- Print the direct flow-launch URL: `<instanceUrl>/flow/<FlowApiName>` — the fastest validation path that bypasses QuickActions, layouts, and the Forms tab.

On failure (the `POST` returned a 400 — read the error from the response body's `message`):
- If `Cannot find component 'runtime_service_fieldservice:dcXxx'` → org doesn't have Field Service enabled (or the component name is wrong). Surface the exact error and stop.
- For Flow validation errors, the cause is usually a pattern listed in the prohibited-patterns table at [fs-data-capture-reference/SKILL.md](../fs-data-capture-reference/SKILL.md). Read that file before retrying. Common diagnoses: schema-grouping violations, `.AllItems` vs `.AddedItems` accessor mismatch, CUD ordering, missing `nextOrFinishButtonLabel`, `IsLlmTargetable` boolean-vs-string.
- Don't loop more than twice without showing the user.
- Common gotcha: if you emit an implicit `Sec_General` section for any screen whose first field appears before an explicit `{ "section": "..." }` header, two such screens collide with `Duplicate developer name: Sec_General`. Give each such screen an explicit leading section in the JSON, then re-assemble and re-POST.

### 6. Make the form visible (optional but usually wanted)

Deploying the flow does NOT make it appear in the "Forms" related list on a Service Appointment, Work Order, or other parent. To make a deployed flow show up as a pending form a tech can pick up:

1. **Attach a `DynamicDataCapture` record to the parent.** This is the SDO's canonical "pending form" pattern — see how shipped SDO forms (Job Safety, Vehicle Inspection, Job Completion) are wired. Create the record with a single sObject insert — dispatch `POST /services/data/vXX.0/sobjects/DynamicDataCapture` with this body:

   ```json
   {
     "Name": "<Display Name>",
     "ParentRecordId": "<ParentRecordId>",
     "ActionDefinition": "<FlowApiName>",
     "ActionType": "Flow",
     "ProcessType": "DataCaptureFlow",
     "StatusCategory": "New",
     "IsRequired": true,
     "ExecutionOrder": 1
   }
   ```

   `Name` defaults to `<FlowApiName>` with underscores → spaces if the caller gives no display name; `IsRequired` is a real boolean (`true`/`false`), not a string. A 201 with `success: true` returns the new DDC id. `ParentRecordId` is polymorphic — accepted parent types are `ServiceAppointment`, `ServiceResource`, `TimeSheet`, `Visit`, `WorkOrder`, `WorkOrderLineItem`.

2. **For FSL Mobile / Service Appointment context, attach to the parent Work Order, not the SA itself.** FSL Mobile's Forms tab on a Service Appointment typically aggregates `DynamicDataCapture` records from the SA's parent Work Order (via `ServiceAppointment.ParentRecordId`). Attaching directly to the SA may not surface in mobile.

   Resolve the SA's parent Work Order Id first — dispatch `GET /services/data/vXX.0/query` with `SELECT ParentRecordId FROM ServiceAppointment WHERE Id = '<SA_Id>'`, then attach (sub-step 1) to that Work Order Id.

3. **Verify the parent's page layout has the Forms (DynamicDataCapture) related list.** Different SDOs use different layouts per profile. Query with the Tooling API — dispatch `GET /services/data/vXX.0/tooling/query` with `SELECT Layout.Name, Profile.Name FROM ProfileLayout WHERE TableEnumOrId = 'WorkOrder'`.

   `Layout` is itself a Tooling sObject with a JSON `Metadata` field, so the splice is a REST read-modify-write — no XML file, no deploy. Read the layout with `GET /services/data/vXX.0/tooling/sobjects/Layout/{layoutId}` (resolve `{layoutId}` from the `ProfileLayout.LayoutId` in the query above), check `Metadata.relatedLists` for a `DynamicDataCapture` entry, and if absent append this entry and `PATCH /services/data/vXX.0/tooling/sobjects/Layout/{layoutId}` with the updated `Metadata`:

   ```json
   {
     "relatedList": "DynamicDataCapture",
     "fields": ["Name", "StatusCategory", "IsRequired"]
   }
   ```

4. **Caveats:**
   - Attached form must have `StatusCategory='New'` to appear as pending. `Completed` records show as historical.
   - `ActionDefinition` must exactly match the deployed flow's API name (case-sensitive).
   - `ProcessType='DataCaptureFlow'` is required — the SDO sometimes also uses `DiscoveryFrameworkFlow`.
   - If the parent profile's layout lacks the Forms list, attaching the DDC succeeds at the data layer but the form is invisible in the UI.

5. **Each profile has its own page layout.** Real SDOs commonly route different profiles to different Work Order layouts (e.g. `System Administrator` → `SDO SFS Work Order Layout`, `Standard User` → `Work Order Layout`, `SDO-Service` → `FSL Work Order Layout`). Patching one layout doesn't help users on the others. Run the ProfileLayout query above for every profile that needs to see the form, then patch the union of layouts.

6. **DDC + WorkPlan OWD must be Public Read/Write for FSL Mobile.** The Forms tab on FSL Mobile uses the UI API (`/ui-api/related-list-records/<woId>/DynamicDataCaptures`), which enforces sharing. If `DynamicDataCapture` or `WorkPlan` OWD is **Private** (the platform default), the technician got the WO via AssignedResource sharing and has zero row access to the DDCs themselves — UI API returns `INSUFFICIENT_ACCESS` and the Forms tab silently shows "No forms available. We couldn't find any forms to display." with a "Try Again" button. Desktop SOQL as admin doesn't catch this because admins bypass sharing.

   **Fix:**
   - Set the org-wide default for `DynamicDataCapture` and `WorkPlan` to **Public Read/Write**. Org-wide sharing defaults are a Setup-only surface — surface the deeplink `<instanceUrl>/lightning/setup/SecuritySharing/home` and have the admin set both objects' Default Internal Access to Public Read/Write. (This is a click-through, not a shell step.)
   - Set `doesShareSaParentWoWithAr` and `doesShareSaWithAr` to `true` on `FieldServiceSettings` via a Tooling PATCH — `GET /services/data/vXX.0/tooling/query` `SELECT Id, Metadata FROM FieldServiceSettings` to read the singleton, then `PATCH /services/data/vXX.0/tooling/sobjects/FieldServiceSettings/{id}` with `{"Metadata": {"doesShareSaParentWoWithAr": true, "doesShareSaWithAr": true}}` (merge — include the existing Metadata keys).
   - Re-save existing `AssignedResource` records to trigger sharing recalc — a no-op `PATCH /services/data/vXX.0/sobjects/AssignedResource/{id}` per record re-fires the sharing rules.
   - User must **sign out + back in to FSL Mobile** — the sharing snapshot is cached at login.

   Verify with a Tooling API query — dispatch `GET /services/data/vXX.0/tooling/query` with `SELECT QualifiedApiName, InternalSharingModel FROM EntityDefinition WHERE QualifiedApiName IN ('DynamicDataCapture','WorkPlan')`. Both should return `ReadWrite`. If either returns `Private`, the Forms tab will fail for the tech even though the DDC row exists.

7. **After attaching, mobile may need a refresh.** Even with OWD correct, the FSL Mobile Forms tab caches the related list. To pick up a newly-attached DDC: **pull-to-refresh on the Forms tab** on the Work Order. Force-quit + reopen the app if pull-to-refresh doesn't surface it. Sign out + back in is only needed when sharing changes (#6).

8. **UI API version note (testing only).** UI API v60 returns `INSUFFICIENT_ACCESS` even after sharing is correct; v62+ works. The iOS FSL Mobile app hardcodes v67, so this isn't a production issue — but it matters when reproducing the call via curl.

## Scope

**Generated automatically:**
- Field labels, types, and required state from the spec.
- Native types: `ShortText`, `LongText`, `Name`, `Email`, `Phone`, `Numeric`, `Counter` (with `min`/`max`/`value`), `Date`, `DateTime`, `Checkbox`, `Toggle`, `Picklist`, `Radio` (`dcRbGroup`), `CheckboxGroup`, `DisplayText`, `Repeater`.
- Specialized Field Service components: `Signature` (auto-wires `parentRecordId` + `recordId`), `UploadFile`, `UploadImage`, `Images` (auto-wire `recordId` → `parentRecordId`), `Address` (compound), `Matrix` (column choices + `questions` row labels), `Lookup` (with `lookupObject`/`lookupSearchFields`/`lookupMulti` spec keys), `FileView` (with `fileName` spec key).
- Conditional visibility on individual fields.
- Optional `postScreen` automation: a decision, multiple `recordLookups`, one `loop`, multiple `recordCreates`, and extra non-input variables.

**Falls back to deploy-safe placeholders** (admin replaces in Flow Builder):
- `Lookup` *with no `lookupObject`* → `dcTextInput` with `[Lookup — set objectApiName in Flow Builder]` prefix.
- `FileView` *with no `fileName`* → `dcTextInput` with `[FileView — set fileName in Flow Builder]` prefix.

See [reference/field-types.md](reference/field-types.md) for the full mapping.

**Out of scope:**
- Multiple decisions / multiple loops / nested loops in `postScreen`.
- Subflows, formulas, text templates, assignments.
- Visual polish HTML (banners, progress bars, callouts) — those are hand-authored. See `fs-data-capture-reference` skill for patterns.

## Files in this skill

This skill has **no executable scripts**. Auth checks, record reads, the `DynamicDataCapture` attach, and the flow create/deploy are all single REST calls dispatched through the Codey runtime (steps 1, 4, 5, 6). The Flow Metadata JSON is assembled by the agent inline (step 3) from the reference docs below.

- `reference/flow-metadata-json.md` — the Tooling `Flow.Metadata` JSON shape (screens, choices, decisions, variables, post-screen chain) and the deploy/activate calls. Read this when composing the flow.
- `reference/field-types.md` — input contract: spec `fieldType` → runtime component + JSON attributes.
- `reference/post-screen-automation.md` — input contract for the optional `postScreen` block.
- `examples/sample-spec.json`, `examples/inventory-transfer-spec.json` — canonical specs.

## Related skills

- **`fs-data-capture-reference`** (sibling library skill) — reference manual for hand-authoring patterns, prohibited patterns + exact deploy errors, visual polish HTML, supporting CustomObject/PermissionSet/CustomTab deploy. Read this when diagnosing a deploy error or extending the JSON field mappings.
- **`fs-data-capture-form-designer`** — produces the spec this skill consumes (from prose or an image/PDF).
- **`fs-data-capture-form-editor`** — patches an already-deployed flow in the org. Uses the same Tooling `Flow` JSON round-trip (GET Metadata → edit → PATCH) this skill uses to create.
