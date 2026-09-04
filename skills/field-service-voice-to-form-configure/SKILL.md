---
name: field-service-voice-to-form-configure
description: "Set up Voice to Form on Field Service Mobile end-to-end against a Salesforce org, covering both variants: Voice to Record Edit (voice-fills any record-edit screen) and Voice to Form Data Capture (voice-fills Discovery Framework / Data Capture forms). Discovers existing DC forms and asks which to enable, hands off to fs-data-capture-form-deployer to create them if none exist, assigns every permission a mobile user needs, and walks the admin through the Einstein generative AI base setup. TRIGGER when the user asks to enable, configure, install, or set up Voice to Form, V2F, Voice to Record Edit, V2RE, the microphone on the mobile app, or voice-fill on Field Service Mobile. DO NOT TRIGGER when the user wants Pre-Work Brief, wants to author a brand-new Data Capture form, or wants to build a generic Agentforce agent."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Setting up Voice to Form

Configure Voice to Form on Field Service Mobile from a fresh Field Service org. Voice to Form lets a mobile worker tap the microphone on a form or a record edit screen and dictate the contents. Einstein generative AI parses the speech and fills the matching fields.

There are two variants. They share a permission backbone but enable through different switches:

| Variant | What it does | Where it shows up | Underlying switch |
|---|---|---|---|
| **Voice to Record Edit (V2RE)** | Voice-fills the standard record edit screen on objects mobile workers can edit (Work Order, Service Appointment, Asset, Contact, Account, custom objects, etc.) | Mic icon on the Record Edit screen | `FieldServiceMobileSettings.IsShowEditFullRecord = true` (org-level row) + `FieldServiceVoiceToRecordEdit` system permission |
| **Voice to Form Data Capture (V2F, Beta)** | Voice-fills Discovery Framework / Data Capture flows the admin built in Flow Builder | Mic icon on a Data Capture form | `FieldServiceVoiceToForm` system permission + per-form **LLM Targetable** flag (UI toggle only) |

This skill walks the complete setup for both, in the order Salesforce documents them at:

- `help.salesforce.com/s/articleView?id=service.mfs_voice_to_form_setup.htm` (V2F Data Capture)
- `help.salesforce.com/s/articleView?id=service.mfs_voice_to_record_edit_setup.htm` (V2 Record Edit)

The skill is idempotent. Re-running on an already-configured org applies zero changes.

> **Runtime contract:** every org interaction in this skill is a REST call
> dispatched through the Codey runtime (`execute_api` locally / the hosted
> Headless 360 MCP in shared surfaces). This skill has **no dependency on the
> execution environment** — no `sf` CLI, no shell scripts, no local Python, no
> `jq`, no temp files, no metadata deploy, no Apex. Detection is a set of REST
> GETs; the LDS toggle is a Tooling `FieldServiceSettings.Metadata` PATCH; the
> V2RE org switch is an sObject PATCH; the voice permset is a single sObject
> POST; entitlement grants are association-object POSTs. The one step with no
> callable API — the per-form **LLM Targetable** flag — is driven by the
> agent-native browser MCP or handed to the admin as a Setup deeplink (a
> click-through, not a shell step). Do not shell out.

---

## Platform Notes

- All API paths use `vXX.0` — pin to the org's **current** API version (query `GET /services/data` and use the highest `version`), NOT a fixed floor. This matters for the Step 3 feature test specifically: the `PermissionsFieldServiceVoiceTo*` describe columns only surface at a recent API version. On a live org the columns were **absent** from the `PermissionSet` describe at v62.0/v64.0 but **present** at v68.0 — pinning to an old version produces a false "feature not licensed → Stop" negative. Use the org's latest version so the describe reflects the beta perms. v62.0 is a hard floor only (the V2F Beta assumes a recent release); it is not a safe version for the describe test.
- Endpoints marked **Tooling** dispatch to `/services/data/vXX.0/tooling/...`; the rest are the core Data API (`/services/data/vXX.0/...`).
- The Codey runtime resolves and refreshes the connected org and mints tokens on demand — this skill never manages org aliases, instance URLs, or access tokens.
- A few setup steps are genuinely clicks-only in **Setup** (the Einstein base-setup wizard org pref, the per-form LLM Targetable flag). For those the skill surfaces the exact Setup deeplink for the admin to click; it never tries to script them.
- Every SOQL below is dispatched as `GET /services/data/vXX.0/query?q=<soql>` (Data API) or `GET /services/data/vXX.0/tooling/query?q=<soql>` (Tooling). Reads that return records are handled inline by the agent — there is no shell parsing.

---

## Editions and licensing

- **Edition.** Field Service core features, managed package, and the mobile app are available in **Enterprise**, **Unlimited**, and **Developer** editions in Lightning Experience.
- **Mobile entitlement.** Every mobile worker needs the **Field Service Mobile** PSL (`FieldServiceMobilePsl`) to log into the app. In modern Field Service orgs this is a permission-set license layered on top of any standard user license — there is NOT a separate "Field Service Mobile" user license SKU. (Earlier docs said otherwise; trust the live `PermissionSetLicense` query in Step 0.)
- **V2RE entitlement.** Mobile workers who use Voice to Record Edit need the **Einstein for Field Service** PSL (`EinsteinFieldServicePsl`).
- **V2F (Beta) entitlement.** Mobile workers who use Voice to Form on Data Capture need the **Agentforce for Field Service** PSL. The Voice to Form Beta also requires the V2F and V2RE system permissions on a custom permset (see Step 4 — a thin custom permset, NOT a clone). Confirm license entitlement with your account exec before assigning, to avoid unanticipated fees.
- **App version.** V2RE requires Summer '25 or later of the Field Service Mobile App. V2F requires the latest version.

---

## Prerequisites

Before running the setup sequence, confirm all of the following:

1. **Edition + add-on.** The org has Einstein for Field Service (V2RE) and/or Agentforce for Field Service (V2F).
2. **Einstein generative AI is fully ON, not just provisioned.** The Step 1.5 probe flags this. The `EinsteinLlm` runtime entitlement must be active (live LLM call returns 200, not `FUNCTIONALITY_NOT_ENABLED`). Trial and SDO orgs commonly have the PSLs assigned but the runtime never turned on — this is the single most common cause of "We couldn't recommend any updates" on the mobile app.
3. **Data Cloud is provisioned and enabled** if you also use Prompt Builder against grounded data. Required by the V2F help article. V2RE works without Data Cloud activation in practice.
4. **For V2F only:** Data Capture is set up per `help.salesforce.com/s/articleView?id=service.mfs_data_capture_setup.htm`. The skill detects DC forms in Step 5 and, if none exist, hands off to the `fs-data-capture-form-deployer` skill in this repo to create them.
5. **Admin user has the right permissions:** `Customize Application`, `Manage Profiles and Permission Sets`, and `Manage Flows`.

---

## Setup Sequence

Run steps in order. Each step reads the org state before it writes; if a precondition fails, the step surfaces the failure and stops without mutating the org. Every read and write below is a single `execute_api` call.

### Step 0: Detect provisioning state and route

Run six detection reads to classify the org. Several queries that look intuitive (`FlowDefinitionView`, Tooling `FieldServiceMobileSettings`, `Flow.DeveloperName`) DO NOT WORK — the field names and surfaces below are the verified ones.

**1. Einstein / Agentforce / Mobile Field Service PSLs** — `GET /services/data/vXX.0/query`:

```sql
SELECT DeveloperName, MasterLabel, TotalLicenses, UsedLicenses
FROM PermissionSetLicense
WHERE DeveloperName IN ('EinsteinFieldServicePsl','FieldServiceMobilePsl','AgentforceForFieldServicePsl')
```

`EinsteinFieldServicePsl` + `FieldServiceMobilePsl` are required for a V2F demo; `AgentforceForFieldServicePsl` is optional. Only assign in Step 7 the PSLs that come back here.

**2. Shipped `EinsteinFieldServiceUser` permset (read-only clone source reference)** — `GET /services/data/vXX.0/query`:

```sql
SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'EinsteinFieldServiceUser'
```

Present → the FSL package is installed at a V2F-capable version. This permset is shipped read-only; the skill never edits it (and does NOT clone it — see Step 4).

**3. Lightning Data Service mode (LDS)** — Tooling `GET /services/data/vXX.0/tooling/query`:

```sql
SELECT FullName, Metadata FROM FieldServiceSettings
```

Read `Metadata.enableLsdkMode`. `true` → LDS on, proceed. `false` → Step 1 flips it. LDS is needed for V2F-DC, optional for V2RE.

**4. V2RE org switch** — regular sObject `GET /services/data/vXX.0/query` (NOT Tooling):

```sql
SELECT Id, MasterLabel, IsDefault, IsShowEditFullRecord FROM FieldServiceMobileSettings
```

Capture the Id of the `IsDefault = true` row (or the sole row) — Step 2's PATCH targets it.

**5. Active Data Capture forms** — Tooling `GET /services/data/vXX.0/tooling/query` (NOT `FlowDefinitionView`):

```sql
SELECT Id, MasterLabel, ProcessType, Status, DefinitionId
FROM Flow
WHERE ProcessType IN ('DataCaptureFlow','DiscoveryFrameworkDataCaptureFlow') AND Status = 'Active'
```

Use `MasterLabel` for display — `Flow` has no `DeveloperName` column (querying it 400s `INVALID_FIELD`); follow `Definition.DeveloperName` for the API name. Zero rows → Step 5 hands off to `fs-data-capture-form-deployer`.

**6. Existing V2F custom permset** — `GET /services/data/vXX.0/query`:

```sql
SELECT Id, Name, Label FROM PermissionSet WHERE IsCustom = true AND Name LIKE '%V2F%'
```

One row → a prior run created it; skip Step 4 and reuse its Id. Zero rows → Step 4 creates it.

Interpret the results to classify the org:

| Diagnostic 1 (PSL) | Diagnostic 2 (permset) | Diagnostic 5 (forms) | Action |
|---|---|---|---|
| MISSING | any | any | **Stop.** Contact Salesforce AE to purchase Einstein/Agentforce for Field Service. The skill cannot continue. |
| PRESENT | MISSING | any | **Continue to Step 1.5.** Einstein base setup is incomplete; run the wizard before anything else. |
| PRESENT | PRESENT | MISSING | **Continue.** V2RE will set up cleanly. V2F-DC will hand off to the DC skill in Step 5. |
| PRESENT | PRESENT | PRESENT | **Continue.** Both variants will set up cleanly. |

### Step 0.5: Choose the target technician user

Voice to Form is a per-user feature: each technician needs the Field Service Mobile PSL, the Einstein for Field Service PSL, the V2F/V2RE permset, and an active `ServiceResource` row. The skill targets one technician at a time so the admin can pilot before broad rollout.

Ask the admin: **"Do you have a specific technician user you want to enable Voice to Form for?"**

**If yes:** the admin supplies a username or User Id. Validate that the user is active and has a `ServiceResource` record — two `GET /services/data/vXX.0/query` reads (substitute the supplied value into the bound `WHERE`):

```sql
SELECT Id, Name, Username, IsActive, Profile.Name FROM User
WHERE (Username = :tech OR Id = :tech) AND IsActive = true
```

```sql
SELECT Id, Name, ResourceType FROM ServiceResource
WHERE RelatedRecordId IN (SELECT Id FROM User WHERE Username = :tech OR Id = :tech)
  AND IsActive = true
```

**If no:** auto-pick a candidate — the first active `ResourceType='T'` technician on a non-administrator profile — and surface the choice for confirmation, `GET /services/data/vXX.0/query`:

```sql
SELECT Id, Name, RelatedRecord.Id, RelatedRecord.Username, RelatedRecord.Name, RelatedRecord.Profile.Name
FROM ServiceResource
WHERE IsActive = true AND ResourceType = 'T'
  AND RelatedRecordId != null AND RelatedRecord.IsActive = true
  AND RelatedRecord.Profile.Name NOT IN ('System Administrator')
  AND (NOT RelatedRecord.Profile.Name LIKE '%Customer Community%')
  AND (NOT RelatedRecord.Profile.Name LIKE '%Partner Community%')
ORDER BY Name LIMIT 1
```

Capture the technician's `User.Id` (call it TECH_USER_ID) and `Username` for the assignment steps. The running admin's User Id is resolved the same way when needed (`SELECT Id, Username FROM User WHERE ...`) — the Codey runtime already knows the connected identity, so no `org display` call is required.

### Step 1: Enable Lightning Data Service for the Field Service Mobile app

Voice to Form on Discovery Framework forms (V2F-DC) renders inside the LDS-aware mobile container. V2RE works without LDS, but enabling it is harmless and required for V2F-DC, so do it once up front.

LDS is enabled by default for new orgs from Winter '25; all orgs auto-migrate by Spring '26.

`FieldServiceSettings` is a **Tooling sObject** whose config lives in a JSON `Metadata` field — the same shape Step 0 diagnostic 3 reads back. So enabling LDS is a Tooling **read-modify-write PATCH**, not a metadata-file deploy. There is no `.settings-meta.xml`, no SFDX project, and no `sf project deploy start` — that path was never necessary; the Tooling `Metadata` surface is the real REST path (same pattern the sibling `fs-data-capture-form-deployer` skill uses for the FieldServiceSettings sharing prefs).

**1a. Read the settings singleton** (already done in Step 0 diagnostic 3, but re-read to get the full `Metadata` object and its row Id) — Tooling `GET /services/data/vXX.0/tooling/query`:

```sql
SELECT Id, FullName, Metadata FROM FieldServiceSettings
```

If `Metadata.enableLsdkMode` is already `true`, LDS is on — skip to Step 1.5. Otherwise capture the row `Id` (a base64-encoded singleton Tooling id) and the full `Metadata` object.

**1b. PATCH the full `Metadata` back with `enableLsdkMode: true`** — `PATCH /services/data/vXX.0/tooling/sobjects/FieldServiceSettings/{Id}`:

```json
{ "FullName": "FieldService", "Metadata": { "...all sibling keys from the GET...", "enableLsdkMode": true } }
```

`FullName` is **required** on a Tooling `Metadata` PATCH — omitting it 400s with `FIELD_INTEGRITY_EXCEPTION` "Full name must be specified to update metadata" (verified against a live org). For the `FieldServiceSettings` singleton `FullName` is the literal `"FieldService"`; echo back the `FullName` returned by the 1a read. Send the **entire** `Metadata` object read in 1a with only `enableLsdkMode` flipped — a partial body nulls the omitted org prefs (`fieldServiceOrgPref`, `enableWorkOrders`, the search-field arrays, etc.). A 204 is success.

**1c. Verify it actually flipped** — re-run the 1a Tooling read and confirm `Metadata.enableLsdkMode == true`. This guards the rare SDO/trial-org case where a write reports success but the flag stays false. If it did not flip, surface the Setup deeplink for the admin to toggle it by hand:

```text
LDS Setup UI (fallback — only if the PATCH did not persist):
  <instanceUrl>/lightning/setup/FieldServiceSettings/home
  Enable 'Lightning SDK for Field Service Mobile' under the Lightning SDK section.
```

(The Codey runtime knows the instance URL; the skill just names the relative Setup path for the admin.)

### Step 1.5: Confirm the Einstein generative AI runtime is ON

This is the step that most often goes missed. Without it the mic icon WILL render on-device, transcription WILL work, but every voice attempt fails with **"We couldn't recommend any updates. Try again."** — the LLM runtime returning `FUNCTIONALITY_NOT_ENABLED: [EinsteinLlm]` because the `enableEinsteinGPT` org pref was never flipped.

**1.5a. Probe the runtime live.** This is the only honest test — Tooling queries on Einstein settings are unreliable across releases. Dispatch `GET /services/data/vXX.0/einstein/prompt-templates?pageSize=5`:

- **200** with a `promptRecords` array (at least one row, e.g. Salesforce-managed defaults like `einstein_gpt__summarizeContact`) → the LLM runtime is ON. Continue to Step 2.
- **400** `FUNCTIONALITY_NOT_ENABLED: [EinsteinLlm]` → the runtime is OFF. Walk 1.5b.

**1.5b. If the probe failed, surface the wizard deeplinks for the admin.** The wizard is genuinely UI-only — the skill cannot click through it and does not try. Name the relative Setup paths (the runtime resolves the instance URL):

```text
Einstein LLM runtime is OFF. Walk the wizard end-to-end.

PRIMARY (start here):
  /lightning/setup/EinsteinSetup/home

Wizard sub-pages:
  Generative AI:    /lightning/setup/EinsteinGPTSetupHome/home
  Trust Layer:      /lightning/setup/EinsteinTrustSetup/home
  Data Cloud:       /lightning/setup/DataCloudSetup/home
  Prompt Builder:   /lightning/setup/EinsteinPromptStudio/home
  Models config:    /lightning/setup/EinsteinModelsConfiguration/home

In order:
  1. Open the PRIMARY link. Toggle 'Turn On Einstein' -> accept terms.
  2. Open the Generative AI sub-page. Step through each numbered stage
     (enable the org pref, set up Trust Layer, acknowledge data usage,
      enable Prompt Builder).
  3. If the wizard prompts for Data Cloud, open Data Cloud Setup and activate.
     If it's not visible, refresh or re-login; if still missing, the org needs
     a Data Cloud SKU (a CRT to Salesforce Support).
  4. Re-run the 1.5a probe. If it now returns promptRecords, continue to Step 2.

Most common SDO/trial-org symptom: PSLs all assigned, EinsteinSetup page exists,
but the runtime entitlement was never turned on. 'Turn On Einstein' flips it.
```

**1.5c. Re-probe after the admin completes the wizard.** Re-run the 1.5a `execute_api` call. Do not move on until it returns `promptRecords`.

### Step 2: Enable the Voice to Record Edit org switch

V2RE's org-level switch lives on `FieldServiceMobileSettings`, a **regular sObject** (not a Tooling Settings type — earlier docs were wrong about this). The relevant field is **`IsShowEditFullRecord`** (label "Enable full edit on records"). The settings record is named ("Field Service Mobile Settings" by default) and has an `IsDefault` flag controlling which profiles inherit it.

**2a. Find the default settings row (from Step 0 diagnostic 4), or create one** — if diagnostic 4 returned no row, create the default with `POST /services/data/vXX.0/sobjects/FieldServiceMobileSettings`:

```json
{
  "MasterLabel": "Field Service Mobile Settings",
  "DeveloperName": "Field_Service_Mobile_Settings",
  "IsDefault": true,
  "IsShowEditFullRecord": true
}
```

A 201 returns the new row Id (which already satisfies Step 2b — skip the PATCH).

**2b. Flip `IsShowEditFullRecord` to true** on the existing row — `PATCH /services/data/vXX.0/sobjects/FieldServiceMobileSettings/{Id}`:

```json
{ "IsShowEditFullRecord": true }
```

A 204 is success. **Do NOT include `IsDefault` in the PATCH body** — `IsDefault` is a create-only field and is *not updateable* on an existing row; sending it 400s with `INVALID_FIELD_FOR_INSERT_UPDATE` on `IsDefault` (verified against a live org). Set `IsDefault` only at create time via the 2a POST. If the existing row you're patching is not already the default (`IsDefault = false`) and you need it to be, you cannot flip it in place — the toggle then takes effect only on profiles explicitly mapped to this settings row via `MobileSettingsAssignment`; the simplest path for a pilot is to create the default row via 2a instead. Re-read the row (Step 0 diagnostic 4) to confirm `IsShowEditFullRecord` is `true`. The PATCH is idempotent: re-sending the same value returns 204 and changes nothing.

> **What the user sees on-device.** Per Salesforce help (`mfs_actions_order.xml`): once `IsShowEditFullRecord = true` and the user has Edit access to the object, **Edit Work Order**, **Edit Work Order Line Item**, and **Edit Service Appointment** appear in the Actions launcher on the Work Order Overview screen, after Quick Actions. The mobile app caches the settings — the technician must log out and back in for the new actions to appear.

### Step 3: Confirm the V2F + V2RE system-permission columns exist

Salesforce ships two distinct system perms — one per variant. They are enabled on a custom permset (Step 4). Their `PermissionSet` describe columns are:

- **V2F (Beta):** `FieldServiceVoiceToForm` — column `PermissionsFieldServiceVoiceToForm`
- **V2RE:** `FieldServiceVoiceToRecordEdit` — column `PermissionsFieldServiceVoiceToRecordEdit`

Column presence in the describe IS the org-level feature-flag test. Dispatch `GET /services/data/vXX.0/sobjects/PermissionSet/describe` and filter `fields[].name` for `PermissionsFieldServiceVoiceTo*`:

- Both columns present → V2F Beta and V2RE are both licensed on the org.
- Only `PermissionsFieldServiceVoiceToRecordEdit` → V2F Beta isn't enabled for this org. Per the help article: *"Your Customer Org ID needs to be identified, and the feature flag must be turned on for your respective sandbox or production organization."* File a CRT with Salesforce Support quoting the org ID, then continue with V2RE-only setup.
- Neither present → the feature is not licensed. Stop.

The describe also confirms both columns are `createable = true` and `updateable = true` — which is why Step 4 can be a single POST (see below).

### Step 4: Create the V2F/V2RE permset with both system perms

Create a **thin custom permset** that enables the voice system perms via a single sObject POST. `PermissionSet` is a REST-createable sObject and every `Permissions*` system-perm column is writable at create time (confirmed by the Step 3 describe: all 474 `Permissions*` columns are createable+updateable), so the permset is born with the voice perms already on — no XML, no SFDX project, no `sf project deploy start`.

> **Do NOT "clone" `EinsteinFieldServiceUser`.** The shipped permset grants **zero** object permissions and only two unrelated system perms (`ShowPreWorkBriefGA`, `FieldServiceCopilotActions`); its only real payload is the Einstein license link, which Step 7 already delivers via the `EinsteinFieldServicePsl` PSL. A thin custom permset carrying just the voice system-perm booleans is correct and sufficient — replicating the shipped permset would add nothing.

Dispatch `POST /services/data/vXX.0/sobjects/PermissionSet`. Gate the body on the Step 3 describe — set `PermissionsFieldServiceVoiceToForm: true` **only** when that column is present (sending an unknown perm column 400s):

```json
{
  "Name": "EinsteinFieldServiceUser_V2F",
  "Label": "Einstein for Field Service User (V2F)",
  "Description": "Adds Field Service Voice to Form / Voice to Record Edit system perms. Assign to admins and mobile workers who use voice on the FSL mobile app.",
  "PermissionsFieldServiceVoiceToRecordEdit": true,
  "PermissionsFieldServiceVoiceToForm": true
}
```

- `Name` must match `^[A-Za-z][A-Za-z0-9_]*$`; custom permsets are `IsCustom = true` automatically.
- If only the V2RE column exists (V2F Beta off), omit `PermissionsFieldServiceVoiceToForm` and create a V2RE-only permset.
- A 201 returns the new PermissionSet Id.
- Re-running with the same `Name` returns 400 `DUPLICATE_DEVELOPER_NAME` — the Step 0 diagnostic 6 check guards this by skipping create when a V2F permset already exists (reuse its Id).

**Verify the perms actually landed** (a create can report success while a downstream trigger clears a perm) — `GET /services/data/vXX.0/query`:

```sql
SELECT Id, Name, PermissionsFieldServiceVoiceToRecordEdit FROM PermissionSet
WHERE IsCustom = true AND Name = 'EinsteinFieldServiceUser_V2F'
```

Add `PermissionsFieldServiceVoiceToForm` to the SELECT only when that column exists on the org. The perm columns should read back `true`. Capture the Id for Step 7.

### Step 5: Discover Data Capture forms and decide which to enable for V2F

This step is interactive ONLY for V2F-DC. V2RE is fully enabled by Step 2 + Step 4 + Step 7 (no per-form toggling).

**5a. List active DC forms** — Tooling `GET /services/data/vXX.0/tooling/query` (NOT `FlowDefinitionView`, which is not Tooling-queryable on most orgs):

```sql
SELECT Id, MasterLabel, ProcessType, Status, DefinitionId, Definition.DeveloperName
FROM Flow
WHERE ProcessType IN ('DataCaptureFlow','DiscoveryFrameworkDataCaptureFlow') AND Status = 'Active'
ORDER BY MasterLabel
```

Present the form count and, if greater than zero, list each form (`Definition.DeveloperName` — MasterLabel).

**5b. If zero forms:** hand off to the `fs-data-capture-form-deployer` skill and stop V2F-DC enablement. V2RE is unaffected. (This handoff is a machine-readable `delegates_to` edge in the SOR, gated on `FORM_COUNT == 0`.)

```text
No Data Capture forms found.

Voice to Form fills DC forms; without at least one DC form, there is nothing to enable.
To create one, invoke the fs-data-capture-form-deployer skill in this repo
(../fs-data-capture-form-deployer/SKILL.md), or use fs-data-capture-form-designer
(prose or image/PDF input) for end-to-end form generation.

Re-run this skill from Step 5 after at least one DC form exists. Steps 0-4 are
idempotent; re-running is safe.

V2RE — Voice to Record Edit — does NOT depend on DC forms. If you only want V2RE,
Steps 1, 1.5, 2, 4, 7 are sufficient.
```

**5c. If one or more forms:** ask the admin which forms. Default offer is **all**:

```text
Which forms do you want to enable Voice to Form on?
  [a] All <FORM_COUNT> forms above (recommended for a fresh setup)
  [s] Some — pick a subset by row number or DeveloperName
  [n] None for now — re-run later
```

### Step 6: Enable LLM Targetable per selected form

> **Verified GAP (no callable API as of Summer '26).** The **LLM Targetable** flag has NO metadata API representation. Seven candidate field names (`isLLMTargetable`, `isAIPromptable`, `isAvailableForLlm`, `voiceCaptureEnabled`, `supportsVoiceCapture`, `voiceToFormEnabled`, `isAITargetable`) were all rejected by the Flow XSD parser as `Element ... invalid at this location in type Flow`. The Tooling REST `Flow.Metadata` JSON contains no LLM/voice/targetable keys, and `FlowDefinition.Metadata` is barren. The flag exists ONLY in Flow Builder's "Save as" dialog under "Show Advanced". This is the one irreducible non-REST step in the skill — and it is handled **agent-natively via the browser MCP**, not via any execution-environment dependency.

There are two ways to flip it. Pick based on what's available in the runtime.

**Path A (preferred — agent-native browser MCP drive).** Verified working end-to-end: V2F triggered correctly on the mobile app after this path enabled the flag on real forms. The browser MCP is part of the agent runtime (like `execute_api`), not a shell or an external tool the skill depends on.

The sequence per form is exactly these clicks:
1. Open Flow Builder on the form. Resolve the Flow Id for each selected form from the Step 5a list, then navigate the browser MCP to `<instanceUrl>/builder_platform_interaction/flowBuilder.app?flowId=<FLOW_ID>`. (The runtime supplies the authenticated session; the skill does not build `frontdoor.jsp` URLs or handle tokens.)
2. Click toolbar **Save As New Version** (opens the "Save as" dialog).
3. Click **Show Advanced** in the dialog.
4. Click the **LLM Targetable** label (toggles the checkbox).
5. Click the dialog's **Save** button → Flow Builder creates V(n+1) as a Draft.
6. Click toolbar **Activate** → the Draft becomes Active, the prior version becomes Obsolete.

Browser-MCP click sequence per form (node IDs change per page-load and must be re-fetched via `browser_a11y_tree`):

```text
browser_navigate(<instanceUrl>/builder_platform_interaction/flowBuilder.app?flowId=<FLOW_ID>)
# Wait until the toolbar renders. The "Last saved on..." banner is reliable.
browser_a11y_tree(query="Save As New Version") -> click that node
browser_a11y_tree(query="Show Advanced")       -> click that node
browser_click("LLM Targetable")                 # aria-label resolution works for the label
browser_a11y_tree(query="dialog") -> drill into the dialog root, click "Save"
browser_a11y_tree(query="Activate") -> click that node
```

**Verify per form** — a new Active version with a higher `VersionNumber` confirms the save committed. Tooling `GET /services/data/vXX.0/tooling/query`:

```sql
SELECT Definition.DeveloperName, VersionNumber, Status, LastModifiedDate FROM Flow
WHERE Definition.DeveloperName = :formApiName ORDER BY VersionNumber DESC LIMIT 3
```

The newest row should be Active with a `LastModifiedDate` near the run time.

**Path B (fallback when no browser MCP is available) — hand the admin deeplinks.** Surface one Flow Builder URL per selected form and the click steps. The admin opens each, clicks Save As New Version → Show Advanced → ticks LLM Targetable → Save → Activate:

```text
Open each link. Click Save As New Version. Click Show Advanced.
Tick 'LLM Targetable'. Click Save. Click Activate.

  <form MasterLabel>
    <instanceUrl>/builder_platform_interaction/flowBuilder.app?flowId=<FLOW_ID>
```

> **Gotcha:** clicking **Save** alone (without Save As New Version) on an Active flow leaves the Save button greyed out — Flow Builder won't mutate an active flow in place. The version-properties dialog accepts the LLM Targetable click but a plain Save won't persist it. Save As New Version creates a Draft V(n+1); Activate then flips that Draft to Active.

After the form is saved + activated, the technician confirms on-device by opening the form and looking for the mic icon (Step 7's permset is a prerequisite, not the trigger).

### Step 7: Assign permission set licenses and the voice permset

Assign the PSLs that came back from Step 0 diagnostic 1, plus the Step 4 permset, to BOTH the admin (so they can validate end-to-end) and the technician (so the mic renders on-device and the LLM call goes through). Every grant is an association-object POST — one row per (user, entitlement) pair. An already-existing assignment returns 400 `DUPLICATE_VALUE`, which the caller treats as no-op success.

**7a. Assign each detected PSL** — one `POST /services/data/vXX.0/sobjects/PermissionSetLicenseAssign` per PSL per user. Resolve `PermissionSetLicenseId` from the Step 0 diagnostic 1 result:

```json
{ "AssigneeId": "<userId>", "PermissionSetLicenseId": "<pslId>" }
```

Fan out over {admin User Id, technician User Id} × {each PSL from diagnostic 1 — at minimum `EinsteinFieldServicePsl` and `FieldServiceMobilePsl`}.

**7b. Assign the Step 4 permset** — one `POST /services/data/vXX.0/sobjects/PermissionSetAssignment` per user:

```json
{ "AssigneeId": "<userId>", "PermissionSetId": "<v2fPermsetId>" }
```

**7c. Verify the technician's full mobile-user permission stack.** Run these four `GET /services/data/vXX.0/query` reads for TECH_USER_ID and confirm each returns the expected rows. A missing row here is a certain on-device failure with no error message.

1. Field Service Mobile PSL assigned:
   ```sql
   SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign
   WHERE AssigneeId = :techId AND PermissionSetLicense.DeveloperName = 'FieldServiceMobilePsl'
   ```
2. Einstein for Field Service PSL assigned:
   ```sql
   SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign
   WHERE AssigneeId = :techId AND PermissionSetLicense.DeveloperName = 'EinsteinFieldServicePsl'
   ```
3. Voice permset assigned with both system perms:
   ```sql
   SELECT PermissionSet.PermissionsFieldServiceVoiceToForm, PermissionSet.PermissionsFieldServiceVoiceToRecordEdit
   FROM PermissionSetAssignment
   WHERE AssigneeId = :techId AND PermissionSet.Name = 'EinsteinFieldServiceUser_V2F'
   ```
4. Active ServiceResource + Edit access on the parent objects:
   ```sql
   SELECT Id, IsActive FROM ServiceResource WHERE RelatedRecordId = :techId AND IsActive = true
   ```
   ```sql
   SELECT SObjectType, PermissionsRead, PermissionsEdit FROM ObjectPermissions
   WHERE ParentId IN (SELECT PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId = :techId)
     AND SObjectType IN ('WorkOrder','ServiceAppointment')
   ```

Common gaps:
- **PSL missing:** the user's profile lacks the FSL Mobile PSL — assign explicitly (7a).
- **Edit access missing/partial:** the Standard User profile does not grant Edit on FSL objects by default. Move the user to a Field Service Mobile profile, or grant Read+Edit via a permset.

Once all four pass, the technician's permission stack is complete. On-device verification (below) is a manual admin task, outside the REST workflow.

### Step 8: On-device verification (manual)

The technician logs into the Field Service Mobile app on a device and confirms voice-fill works. This is a human step — the skill has finished configuring the org.

Three things to check, in order:

**8a. V2RE — Edit Work Order action appears:**
1. Open a Work Order on today's schedule.
2. Tap **Actions** (top-right of the Overview screen).
3. **Edit Work Order**, **Edit Work Order Line Item**, and **Edit Service Appointment** appear after Quick Actions.

If they don't appear, log out and back in (settings cache).

**8b. V2RE mic — voice fills fields:**
1. Tap **Edit Work Order**.
2. Look for the mic icon next to the keyboard.
3. Tap mic, dictate e.g. *"Set priority to High and add a description that the customer reported a leak in the kitchen."*
4. Confirm Priority and Description populate.

If the mic appears but voice fails with **"We couldn't recommend any updates. Try again."** — return to Step 1.5 and re-run the live LLM probe. The Einstein wizard wasn't fully completed.

**8c. V2F-DC mic — voice fills DC form:**
1. Open a Work Order's Forms tab (or related list).
2. Open one of the LLM Targetable-enabled DC forms from Step 6.
3. Tap mic, dictate.
4. Confirm fields populate.

If the mic doesn't appear on the form, the LLM Targetable click didn't save — re-open in Flow Builder (Step 6), verify the checkbox, save again.

---

## What if the org has zero Data Capture forms

Step 5 short-circuits. The skill hands off to the `fs-data-capture-form-deployer` skill (sibling skill in this repo) and stops V2F-DC enablement. V2RE is unaffected — Steps 1, 1.5, 2, 4, 7 are sufficient for V2RE alone.

To resume V2F-DC enablement after the DC skill creates at least one form, re-run from Step 5. Steps 0-4 are idempotent.

---

## Configuration Reference

| Concern | Where it lives | How to change |
|---|---|---|
| Whether mobile workers see the mic at all | `EinsteinFieldServiceUser_V2F` permset assigned + `EinsteinFieldServicePsl` PSL assigned + `FieldServiceMobilePsl` PSL assigned | Step 7 (association-object POSTs) |
| Whether the Einstein LLM runtime is on | `enableEinsteinGPT` org pref | Setup → Einstein → Get Started wizard (Step 1.5, UI-only) |
| Whether Edit Work Order / Edit SA actions appear | `FieldServiceMobileSettings.IsShowEditFullRecord` + the FSM Settings row's `IsDefault = true` (or explicit profile assignment) | Step 2 (sObject PATCH) |
| Whether LDS is on for the mobile app | `FieldServiceSettings.Metadata.enableLsdkMode` | Step 1 (Tooling `Metadata` PATCH) |
| Whether V2RE works for a user | `FieldServiceVoiceToRecordEdit` system perm via the custom permset | Step 4, Step 7 |
| Whether V2F (Beta) works at all in the org | `FieldServiceVoiceToForm` system perm exists in describe + Customer Org ID feature flag enabled by Salesforce Support | Step 3 describe; CRT to Support if missing |
| Whether V2F is on for a specific DC form | LLM Targetable checkbox in Flow Builder Save dialog (no metadata API path) | Step 6 (browser MCP or deeplink) |
| Which LLM runs the voice-to-text and field mapping | Salesforce-managed | Not customer-configurable |

---

## Common Issues

**Mic doesn't appear on the record edit screen (V2RE).**

Walk in this order:
1. `FieldServiceMobileSettings.IsShowEditFullRecord = true` AND that row has `IsDefault = true` (Step 2 verify).
2. The user has the custom permset with `PermissionsFieldServiceVoiceToRecordEdit = true` (Step 7c, item 3).
3. The user has the `FieldServiceMobilePsl` PSL (Step 7c, item 1).
4. The user logged out and back in after Step 2.
5. The user is on Summer '25 or later of the Field Service Mobile App.

**Mic doesn't appear on a Data Capture form (V2F).**

Walk in this order:
1. The form has LLM Targetable = true (Step 6 verify).
2. The user has the V2F system perm via the custom permset (Step 7c, item 3 → V2F=true).
3. The user has the FSL Mobile PSL (Step 7c, item 1).
4. The Customer Org ID feature flag is on. If still missing after items 1-3, file a CRT quoting the org ID (Step 3 describe).
5. The form doesn't contain ONLY Upload Image, Upload File, Image Preview, Matrix, Lookup, or Signature components — these don't support V2F.

**Mic appears but voice fails with "We couldn't recommend any updates. Try again."**

This is the most common failure mode. The LLM runtime is off. Walk in this order:
1. Run the Step 1.5a probe. If it returns `FUNCTIONALITY_NOT_ENABLED: [EinsteinLlm]`, the runtime is off.
2. Run the Einstein Setup wizard (Step 1.5b). Toggle 'Turn On Einstein'. Walk every numbered step including Trust Layer.
3. Re-run the probe. If it now returns `promptRecords` with at least one row, the runtime is on.
4. Have the technician retry on-device.

If the probe still fails after the wizard, file a CRT with Salesforce Support quoting the org ID and the `FUNCTIONALITY_NOT_ENABLED: [EinsteinLlm]` error code. SDO and trial orgs occasionally need Salesforce-side enablement even after the wizard completes.

**Mic appears, voice transcribes, but fills wrong fields.**

The LLM is mapping speech to the wrong field. Two patterns:
1. **Field labels collide.** Two fields with similar labels ("Notes" and "Technician Notes") confuse the mapping. Rename for clarity.
2. **Form is too long.** Long single-screen forms degrade mapping accuracy. Break into multiple screens.

**Edit Work Order action doesn't appear in the mobile Actions list.**

Per `mfs_actions_order.xml`: the Edit actions appear AFTER Quick Actions, only when `IsShowEditFullRecord = true` AND the user has Edit access to the object. Walk:
1. Step 2 verify — `IsShowEditFullRecord = true` AND `IsDefault = true`.
2. Step 7c, item 4 — Edit on WorkOrder and ServiceAppointment.
3. Log out and back in on the mobile app — actions list is cached.

---

## Verification Checklist

Run before declaring Voice to Form enabled in production:

- [ ] The auth probe (`SELECT Id FROM Organization LIMIT 1`) returns the expected org.
- [ ] At least one Einstein/Agentforce for Field Service PSL is present with `TotalLicenses > 0` and `UsedLicenses < TotalLicenses`.
- [ ] LDS for Field Service Mobile is enabled (verified via the actual `Metadata.enableLsdkMode` value read back after the PATCH, not just the 204).
- [ ] **Step 1.5 probe returns 200 with `promptRecords`.** The live LLM call to `/einstein/prompt-templates` returns at least one row, not `FUNCTIONALITY_NOT_ENABLED`.
- [ ] `FieldServiceMobileSettings.IsShowEditFullRecord = true` AND the same row has `IsDefault = true` (or is explicitly assigned to the technician's profile).
- [ ] Custom permset `EinsteinFieldServiceUser_V2F` exists with `PermissionsFieldServiceVoiceToRecordEdit = true` (and `PermissionsFieldServiceVoiceToForm = true` when V2F Beta is on).
- [ ] The permset is assigned to both the admin and the chosen technician.
- [ ] Tech has `FieldServiceMobilePsl` AND `EinsteinFieldServicePsl` assigned, plus an active `ServiceResource` row.
- [ ] (V2F-DC only) At least one DC form has LLM Targetable checked and a new Active version (Step 6 verify).
- [ ] On-device: technician logs out, back in, opens a Work Order, taps Edit (V2RE) or opens a DC form (V2F), mic appears, dictation fills the right fields.

---

## Conventions

- **REST-native, no execution-environment dependency.** Every org read and write is a single `execute_api` REST call dispatched through the Codey runtime. The skill uses no `sf` CLI, no shell, no local Python or `jq`, no temp files, no metadata deploy, and no Apex. The one non-REST step (LLM Targetable) uses the agent-native browser MCP or a Setup deeplink — never a shell.
- **Idempotent.** Re-running on an already-configured org applies zero changes. LDS/permset/PSL writes are safe to re-run (204/no-op or `DUPLICATE_VALUE` treated as success).
- **Read API names back from the org.** PSL DeveloperName, the permset Id, the form API-name list, and the FSM Settings row Id are all read live, never hard-coded.
- **Trust the runtime probe over Tooling settings probes.** `Ai4mSettings.enableEinsteinGPT` returns `<missing>` even on fully-enabled orgs. The only honest check is the live LLM call in Step 1.5a.
- **Full-object writes on JSON `Metadata` fields.** The LDS PATCH sends the entire `FieldServiceSettings.Metadata` object with one key flipped — a partial body nulls omitted org prefs.
- **Single source of truth.** Where Salesforce Help documents a setup step, this skill cites the article rather than reproducing or contradicting it.

---

## Manual steps the admin must do (clicks-only)

The skill cannot perform these via API. Each returns a Setup deeplink for the admin to click:

| When | What | Why |
|---|---|---|
| Step 1.5b | Open `/lightning/setup/EinsteinSetup/home`, click 'Turn On Einstein', walk every numbered step in the Generative AI sub-page | Flips `enableEinsteinGPT` org pref. The single most important step. Without it, voice fails with "We couldn't recommend any updates" even though everything else is correct. |
| Step 1 (fallback only) | Open `/lightning/setup/FieldServiceSettings/home`, enable 'Lightning SDK for Field Service Mobile' | Only if the Tooling `Metadata` PATCH did not persist on a stubborn SDO/trial template. The PATCH is the primary path. |
| Step 6 (Path B fallback only) | Open each Flow Builder URL, Save As New Version → Show Advanced → tick LLM Targetable → Save → Activate | No metadata API path exists. Path A automates this via the browser MCP; this fallback applies when no browser MCP is in the runtime. |
| Step 8 | On-device: log out and back in to the Field Service Mobile app | Settings + permset cache; the app picks up changes only on a fresh session. |

---

## Related skills

All sibling skills in this repo:

- **`fs-data-capture-form-deployer`** — creates a Data Capture form from a Flow Builder spec. Step 5 hands off here when the org has zero forms.
- **`fs-data-capture-form-designer`** — generates a DC form from a natural-language prompt OR a photographed/PDF paper form, then deploys via fs-data-capture-form-deployer.
- **`fs-data-capture-form-editor`** — modifies an existing DC form.
- **`configure-field-service-mobile`** — sets up FSL Mobile org-level settings (LDS, Forms tab visibility, branding); composes with this skill on Step 1 (LDS) and the Forms-tab association needed for V2F-DC to render on mobile.
- **`fs-mobile-branding`** — applies brand colors to the Field Service Mobile app.
- **`setting-up-pre-work-brief`** + **`customizing-pre-work-brief`** — sister skills in the same Frontline AI family. PWB renders an AI brief in the Work Order Overview tab; V2F lets the technician dictate into that Work Order's forms or record edit screens. The two compose cleanly: PWB before the visit, V2F during.
- **`fs-data-capture-reference`** — primer on Data Capture concepts; useful background reading.
- **`salesforce-agx-*`** — AGX Flow Builder family (background-flow, screen-flow, data-retrieval-flow, orchestration-flow); useful when authoring a custom DC flow rather than Voice-enabling an existing one.

---

## References

External (Salesforce Help):

- Voice to Form (Data Capture) setup: `https://help.salesforce.com/s/articleView?id=service.mfs_voice_to_form_setup.htm`
- Voice to Record Edit setup: `https://help.salesforce.com/s/articleView?id=service.mfs_voice_to_record_edit_setup.htm`
- Field Service Mobile Settings details: `https://help.salesforce.com/s/articleView?id=service.mfs_settings_details.htm`
- Which Actions Appear in the Field Service Mobile App: `https://help.salesforce.com/s/articleView?id=service.mfs_actions_order.htm`
- Set Up Data Capture: `https://help.salesforce.com/s/articleView?id=service.mfs_data_capture_setup.htm`
- Build a Data Capture Flow: `https://help.salesforce.com/s/articleView?id=service.mfs_data_capture_buildflow.htm`
- Data Capture Limitations and Guidelines: `https://help.salesforce.com/s/articleView?id=service.mfs_data_capture_limitations.htm`
- Set Up Einstein Generative AI: `https://help.salesforce.com/s/articleView?id=ai.generative_ai_enable.htm`
- Lightning Data Service for Field Service Mobile: `https://help.salesforce.com/s/articleView?id=service.mfs_lightning_data_service.htm`

---

## Known Limitations

- **Voice to Form is Beta.** Salesforce reserves the right to change behavior, permission names, or feature flags between releases. The skill targets Spring '26 / Summer '26.
- **LLM Targetable has no metadata API path.** Verified empirically: the Flow XSD parser rejects every candidate field name, and the Tooling REST `Flow.Metadata` JSON contains no LLM-related keys. Per-form enablement requires Flow Builder UI. Step 6 Path A drives this agent-natively via the browser MCP (verified end-to-end); Path B falls back to deeplinks for an admin to click. This is the ONLY non-REST step in the skill.
- **Customer Org ID feature flag.** V2F-DC requires Salesforce-side enablement of a feature flag on the specific org. The skill detects via the `PermissionSet.PermissionsFieldServiceVoiceToForm` describe column, but cannot toggle it. If missing, file a CRT with Salesforce Support.
- **Einstein LLM runtime entitlement.** Trial / SDO orgs commonly have all PSLs assigned but the runtime never turned on. Step 1.5 detects and surfaces this; resolution is a UI wizard click-through. SDO orgs occasionally need Salesforce-side enablement even after the wizard.
- **LDS on stubborn templates.** On rare SDO/trial templates the `enableLsdkMode` write reports success but doesn't flip; Step 1c re-reads to catch this and falls back to the Setup deeplink.
- **Component-type coverage.** V2F doesn't support Upload Image, Upload File, Image Preview, Matrix, Lookup, or Signature components in DC forms. A form composed entirely of these shows no mic icon.
