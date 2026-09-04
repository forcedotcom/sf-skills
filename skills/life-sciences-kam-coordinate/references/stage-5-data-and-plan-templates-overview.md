# Stage 5 — KAM Data & Plan Templates

This single stage creates all the KAM master data **and** the plan templates that back the account plan, all as the **admin** (`--target-org <admin>`). This is Stage 5 of `life-sciences-kam-coordinate`; the coordinator invokes it after the participant role and sprint (Stage 4) exist and the territories (Stage 3) are active.

The stage runs in two parts, in order:

- **Part A — KAM Data Creation**: the account, provider, address, territory-association, and product master data (from the starter-config CSVs + an explicit HCO account bundle).
- **Part B — Goals, Tasks, Measures & Action Plan Template**: the goal definitions, goal-product link, and the published, assigned action-plan template.

Part B links to the `LifeSciMarketableProduct` created in Part A, so run Part A first and capture its Ids.

## Stage Scope

- **In scope**: Part A objects (Account, HealthcareProvider, ContactPointAddress, ObjectTerritory2Association, ProviderAcctTerritoryInfo, Product2, LifeSciMarketableProduct, ProductTerritoryAvailability — **plus an HCO account bundle**) and Part B records (2 `GoalDefinition`, 1 `GoalDefinitionProduct`, 1 `ActionPlanTemplate` + auto `ActionPlanTemplateVersion`, 3 `ActionPlanTemplateItem`, 6 `ActionPlanTemplateItemValue`, publishing the version → Final, 1 `ActionPlanTemplateAssignment`, and the leaf-territory shares — 2 `GoalDefinitionShare` + 1 `ActionPlanTemplateShare` + 2 `ProviderAcctTerritoryInfoShare`)
- **Out of scope**: the Visit chain (not created in the KAM workflow), user provisioning + mobile metadata cache (Stage 6)

## Everything runs as the ADMIN

Unlike the field-sales-rep workflow, the KAM workflow creates **all** data as the **admin** (`--target-org <admin>`). The end user is not provisioned until Stage 6, so there is no rep to log in as and no rep/admin split. There is also **no manual iPad validation step** here — mobile metadata generation belongs to Stage 6.

## Required Inputs

- **Target org / admin**: the admin alias or username
- **Stage-3 level-3 territory Id**: captured by the coordinator in `OrchestrationState.territoryId` — used for `ObjectTerritory2Association`, `ProviderAcctTerritoryInfo`, and `ProductTerritoryAvailability`. This MUST be the same territory later assigned to the KAM user in Stage 6.

## Source folder

All Part A CSVs come from `.lsc-starter-config/LSStarterConfig/Data/`. This stage is a pure consumer of the shared folder — it MUST NOT download or delete it (the coordinator owns the single download and delete). If the folder is absent, stop and report it must be provisioned by the coordinator.

---

# Part A — KAM Data Creation

## Workflow

1. **Read the live CSV for each object** — never hardcode values from the reference table. Full field-by-field mapping: `references/stage-5-data-creation-data.md`.
2. **Create the records in dependency order**, capturing each returned Id for downstream foreign keys:

   ```text
   HCP Account → HealthcareProvider → ContactPointAddress
               → ObjectTerritory2Association → ProviderAcctTerritoryInfo
   HCO Account (Partners Healthcare) → HealthcareProvider → ContactPointAddress
               → ObjectTerritory2Association → ProviderAcctTerritoryInfo
   Product2 → LifeSciMarketableProduct → ProductTerritoryAvailability
   ```

   > The **HCO account bundle** (`Partners Healthcare` Account, its HealthcareProvider, ContactPointAddress, ObjectTerritory2Association, and ProviderAcctTerritoryInfo) uses explicit values, not the CSVs — both the Account and the HealthcareProvider use the `Health_Care_Organization` record type (query the RecordType Id by `DeveloperName`+`SobjectType` first). The HCO ContactPointAddress reuses the CSV address values with `ParentId` = the HCO Account, and the HCO OT2A/PATI reuse the CSV field values against the HCO Account and the **same Stage-3 level-3 territory**. See `references/stage-5-data-creation-data.md`.

   Use `sf data create record --sobject <Object> --target-org <admin> --values "..." --json` for each, or a small tree/import if you prefer. Substitute the captured FK Ids and the Stage-3 `territoryId` where the reference marks a foreign key.
3. **Capture the `LifeSciMarketableProduct` Id and the `Account` Id** in `OrchestrationState` — Part B links `GoalDefinitionProduct.ProductId` to the LifeSciMarketableProduct.

## Part A Verification Gate

```bash
sf data query --query "SELECT Id FROM Account ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
sf data query --query "SELECT Id FROM LifeSciMarketableProduct ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
sf data query --query "SELECT Id, ProductId, TerritoryId FROM ProductTerritoryAvailability ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
```

All three must return a record, and the `ProductTerritoryAvailability.TerritoryId` must equal the Stage-3 `territoryId`.

## Part A Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Create everything as the admin | No end user exists until Stage 6 |
| Do NOT create the Visit chain | KAM workflow has no visit data |
| Read the live CSV; never hardcode | CSV values may change between runs |
| Use the Stage-3 level-3 territory for all three territory FKs | The KAM user (Stage 6) is assigned this same territory; a mismatch hides all data |
| Do NOT download or delete `.lsc-starter-config/` | Owned by the coordinator |

## Part A Gotchas

| Issue | Resolution |
|-------|------------|
| `ProductTerritoryAvailability` created against the wrong territory | Re-create with `TerritoryId` = the Stage-3 `territoryId` (the one Stage 6 assigns to the user) |
| Product2 create fails on `RecordTypeId` | Do NOT set `RecordTypeId` on Product2 — it takes no record type |
| A create fails on an FLS-gated field | As admin this is rare; omit the offending non-required field and continue (see the per-object notes in the data reference) |
| `INVALID_CROSS_REFERENCE_KEY` on an FK | The parent record Id wasn't captured — re-query the parent and retry |

---

# Part B — Goals, Tasks, Measures & Action Plan Template

Creates the goal definitions, the goal-product link, and the action-plan template (with its items) that back the KAM account plan, then publishes it (by setting its version to `Final`) and assigns it. Run entirely as the **admin** (`--target-org <admin>`), immediately after Part A — Part B links to the Part A `LifeSciMarketableProduct`.

Only the record **names** are confirmed with the admin. All other fields are auto-derived from this reference and shown for confirmation.

## Step 1 — Two GoalDefinition records

Both are active. On `GoalDefinition` the active flag is **`Status`** (values `Active`/`Inactive`) — **not** `IsActive` (that field does not exist on this object). Set `Status=Active`. The goal-type field distinguishes them (`Strategic` vs `Individual`).

| # | Name | Goal type | Status | Confirmed? |
|---|------|-----------|--------|-----------|
| 1 | `Immunexis: Secure Q3 Formulary Position` | Strategic | Active | Name only |
| 2 | `Immunexis: Prepare Pharmacy & Therapeutics (P&T) Strategy` | Individual | Active | Name only |

```bash
sf data create record --sobject GoalDefinition --target-org <admin> \
  --values "Name='Immunexis: Secure Q3 Formulary Position' Type=Strategic Status=Active" --json
sf data create record --sobject GoalDefinition --target-org <admin> \
  --values "Name='Immunexis: Prepare Pharmacy & Therapeutics (P&T) Strategy' Type=Individual Status=Active" --json
```

> The goal-type field is the picklist that carries `Strategic`/`Individual`. If `Type` is rejected, describe the object (`sf sobject describe --sobject GoalDefinition`) and use the actual field name (e.g. `GoalType`); the values `Strategic`/`Individual` are unchanged. Capture **both** Ids — the **Strategic** goal (#1) is referenced by both `GoalDefinitionProduct` and `ActionPlanTemplateAssignment`.

---

## Step 2 — GoalDefinitionProduct

Links the **Strategic** goal to the Part A product.

| Field | Value |
|-------|-------|
| `GoalDefinitionId` | Id of goal #1 (`Immunexis: Secure Q3 Formulary Position`) |
| `ProductId` | the Part A `LifeSciMarketableProduct` Id (Immunexis 5mg) — from `OrchestrationState` |

```bash
sf data create record --sobject GoalDefinitionProduct --target-org <admin> \
  --values "GoalDefinitionId=<strategicGoalId> ProductId=<lifeSciMarketableProductId>" --json
```

> `ProductId` is the **LifeSciMarketableProduct** Id from Part A, not the Product2 Id.

---

## Step 3 — ActionPlanTemplate

| Field | Value | Confirmed? |
|-------|-------|-----------|
| `Name` | `Immunexis: Formulary Submission & Review Prep` | Name only |
| `ActionPlanType` | `KAM` | Auto |
| `TargetEntityType` | `AccountPlanObjective` | Auto |
| `IsAdHocItemCreationEnabled` | `true` | Auto |

> **Do NOT set `Status` on create** — `ActionPlanTemplate.Status` is **read-only** (not writable on create or update). It defaults to `Draft`, and it is later driven to `Final` by publishing the version (Step 5), which propagates back to the template. Including `Status=Draft` here is rejected.

```bash
sf data create record --sobject ActionPlanTemplate --target-org <admin> \
  --values "Name='Immunexis: Formulary Submission & Review Prep' ActionPlanType=KAM TargetEntityType=AccountPlanObjective IsAdHocItemCreationEnabled=true" --json
```

Creating the template **auto-creates** an `ActionPlanTemplateVersion` (draft) — no `Status` flag is needed to trigger it. Query for it — the template items and the publish step operate on the version:

```bash
sf data query --query "SELECT Id, ActionPlanTemplateId, Version, Status FROM ActionPlanTemplateVersion WHERE ActionPlanTemplateId = '<templateId>' ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
```

Capture the version Id.

> The version fields are **`Version`** (int) and **`Status`** (picklist) — the same `Status` the publish step (Step 5) updates to `Final`. Do **not** use `VersionNumber`/`VersionStatus`; those columns do not exist and the query silently returns null for them. If a query is rejected, `sf sobject describe --sobject ActionPlanTemplateVersion` and use the reported names.

---

## Step 4 — Three ActionPlanTemplateItem records

All three: `ItemEntityType=AssessmentTask`, `IsActive=true`, linked to the template version.

| # | Name / Subject |
|---|----------------|
| 1 | `Identify key P&T committee members and influencers` |
| 2 | `Gather HEOR data supporting our value proposition` |
| 3 | `Compile the competitive landscape and formulary access gaps` |

```bash
sf data create record --sobject ActionPlanTemplateItem --target-org <admin> \
  --values "ActionPlanTemplateVersionId=<versionId> Name='Identify key P&T committee members and influencers' ItemEntityType=AssessmentTask IsActive=true" --json
# …repeat for items 2 and 3
```

**Capture each item's Id** — the `ActionPlanTemplateItemValue` records below reference it (`<item1Id>`, `<item2Id>`, `<item3Id>`).

> The item-name field may be `Name` or `Subject` depending on the org — describe `ActionPlanTemplateItem` if `Name` is rejected and use the reported field; the three strings are unchanged. The link field to the version may be `ActionPlanTemplateVersionId` (confirm via describe).

### Step 4b — Two ActionPlanTemplateItemValue per item

For **each** `ActionPlanTemplateItem`, create **two** `ActionPlanTemplateItemValue` records — one for the task **Name**, one for the task **Category**. All six share `IsActive=true` and are linked to their item via `ActionPlanTemplateItemId`. Do **not** set `ItemEntityType` on `ActionPlanTemplateItemValue` — it is read-only (derived from the parent item) and setting it fails with "Unable to create/update fields: ItemEntityType". The `Category` values (`Survey`/`Claim`) come from the `AssessmentTaskCategory` StandardValueSet confirmed in Stage 2.

| Item | `ActionPlanTemplateItemId` | `ItemEntityFieldName` | `Name` | `ValueLiteral` |
|------|---------------------------|-----------------------|--------|----------------|
| 1 — Identify key P&T committee members and influencers | `<item1Id>` | `AssessmentTask.Name` | `Name` | `Identify key P&T committee members and influencers` |
| 1 — Identify key P&T committee members and influencers | `<item1Id>` | `AssessmentTask.Category` | `Category` | `Survey` |
| 2 — Gather HEOR data supporting our value proposition | `<item2Id>` | `AssessmentTask.Name` | `Name` | `Gather HEOR data supporting our value proposition` |
| 2 — Gather HEOR data supporting our value proposition | `<item2Id>` | `AssessmentTask.Category` | `Category` | `Claim` |
| 3 — Compile the competitive landscape and formulary access gaps | `<item3Id>` | `AssessmentTask.Name` | `Name` | `Compile the competitive landscape and formulary access gaps` |
| 3 — Compile the competitive landscape and formulary access gaps | `<item3Id>` | `AssessmentTask.Category` | `Category` | `Survey` |

```bash
# Item 1 — <item1Id>
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item1Id> ItemEntityFieldName=AssessmentTask.Name Name=Name ValueLiteral='Identify key P&T committee members and influencers' IsActive=true" --json
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item1Id> ItemEntityFieldName=AssessmentTask.Category Name=Category ValueLiteral='Survey' IsActive=true" --json

# Item 2 — <item2Id>
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item2Id> ItemEntityFieldName=AssessmentTask.Name Name=Name ValueLiteral='Gather HEOR data supporting our value proposition' IsActive=true" --json
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item2Id> ItemEntityFieldName=AssessmentTask.Category Name=Category ValueLiteral='Claim' IsActive=true" --json

# Item 3 — <item3Id>
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item3Id> ItemEntityFieldName=AssessmentTask.Name Name=Name ValueLiteral='Compile the competitive landscape and formulary access gaps' IsActive=true" --json
sf data create record --sobject ActionPlanTemplateItemValue --target-org <admin> \
  --values "ActionPlanTemplateItemId=<item3Id> ItemEntityFieldName=AssessmentTask.Category Name=Category ValueLiteral='Survey' IsActive=true" --json
```

> Wrap each `ValueLiteral` in single quotes so the shell preserves spaces. Create all six values **before** publishing (Step 5) — a published template is immutable.

---

## Step 5 — Publish via the version (→ Final)

**Publishing is driven through the version, not the template.** `ActionPlanTemplate.Status` is read-only and cannot be updated directly; `ActionPlanTemplateVersion.Status` **is** updateable, and setting it to `Final` propagates the published state back to the parent template. Do this only after all three items and their six item values exist — a published version is immutable. Update the `ActionPlanTemplateVersion` record using the `<versionId>` captured in Step 3, **not** the `<templateId>`:

```bash
sf data update record --sobject ActionPlanTemplateVersion --record-id <versionId> \
  --values "Status=Final" --target-org <admin> --json
```

> Do **not** attempt `sf data update record --sobject ActionPlanTemplate ... Status=Final` — the template's `Status` is read-only and the update is rejected. The version is the only writable path.

Verify — the version reads `Final`, and the template's `Status` has propagated to `Final`:

```bash
sf data query --query "SELECT Id, Status FROM ActionPlanTemplateVersion WHERE Id = '<versionId>'" --target-org <admin> --json
sf data query --query "SELECT Id, Status FROM ActionPlanTemplate WHERE Id = '<templateId>'" --target-org <admin> --json
```

Both must return `Status='Final'`.

---

## Step 6 — ActionPlanTemplateAssignment

Assigns the published version to the **Strategic** goal. `ActionPlanTemplateAssignment` has **no `ActionPlanTemplateId` field** — it links to the template **through the version** via `ActionPlanTemplateVersionId` (required).

| Field | Value |
|-------|-------|
| `AssociatedObjectId` | Id of goal #1 (`Immunexis: Secure Q3 Formulary Position`) — the Strategic `GoalDefinition` |
| `ActionPlanTemplateVersionId` | the `<versionId>` captured in Step 3 (required) |

```bash
sf data create record --sobject ActionPlanTemplateAssignment --target-org <admin> \
  --values "AssociatedObjectId=<strategicGoalId> ActionPlanTemplateVersionId=<versionId>" --json
```

> `AssociatedObjectId` points at the **Strategic** GoalDefinition; `ActionPlanTemplateVersionId` is the published version from Step 3. There is no `ActionPlanTemplateId` field on this object — `No such column 'ActionPlanTemplateId'` means you passed the template Id; use the version Id instead.

---

## Step 7 — Share GoalDefinition, ActionPlanTemplate & ProviderAcctTerritoryInfo to the leaf territory

The two `GoalDefinition` records, the `ActionPlanTemplate`, and the two `ProviderAcctTerritoryInfo` records (HCP + HCO, from Part A) are owned by the **admin**. For the KAM user — assigned to the Stage-3 level-3 (leaf) territory in Stage 6 — to see them, grant the **territory** access via manual share records: one `GoalDefinitionShare` per goal, one `ActionPlanTemplateShare` for the template, and one `ProviderAcctTerritoryInfoShare` per PATI record.

Sharing to a territory means sharing to the territory's **Group**, not to the `Territory2` record. First resolve the group for the Stage-3 `territoryId`:

```bash
sf data query --query "SELECT Id, Type, RelatedId FROM Group WHERE RelatedId = '<territoryId>' AND Type IN ('Territory','TerritoryAndSubordinates')" --target-org <admin> --json
```

Two groups come back — `Territory` (users of exactly this territory) and `TerritoryAndSubordinates`. For a leaf territory they resolve to the same users; use the **`Territory`** group Id (`<territoryGroupId>`).

Then create the share records — `AccessLevel=Edit`, `RowCause=Manual`:

```bash
# GoalDefinitionShare — one per GoalDefinition (Strategic + Individual)
sf data create record --sobject GoalDefinitionShare --target-org <admin> \
  --values "ParentId=<strategicGoalId> UserOrGroupId=<territoryGroupId> AccessLevel=Edit RowCause=Manual" --json
sf data create record --sobject GoalDefinitionShare --target-org <admin> \
  --values "ParentId=<individualGoalId> UserOrGroupId=<territoryGroupId> AccessLevel=Edit RowCause=Manual" --json

# ActionPlanTemplateShare — the template
sf data create record --sobject ActionPlanTemplateShare --target-org <admin> \
  --values "ParentId=<templateId> UserOrGroupId=<territoryGroupId> AccessLevel=Edit RowCause=Manual" --json
```

Then share the `ProviderAcctTerritoryInfo` records. Both PATI records (HCP + HCO) were created in Part A against the Stage-3 `<territoryId>`; query them and create one `ProviderAcctTerritoryInfoShare` per record:

```bash
# Fetch both PATI records for the Stage-3 territory (HCP + HCO)
sf data query --query "SELECT Id FROM ProviderAcctTerritoryInfo WHERE Territory2Id = '<territoryId>'" --target-org <admin> --json

# ProviderAcctTerritoryInfoShare — one per PATI Id returned above
sf data create record --sobject ProviderAcctTerritoryInfoShare --target-org <admin> \
  --values "ParentId=<patiId> UserOrGroupId=<territoryGroupId> AccessLevel=Edit RowCause=Manual" --json
```

> The parent lookup on `GoalDefinitionShare`, `ActionPlanTemplateShare`, and `ProviderAcctTerritoryInfoShare` is **`ParentId`** (confirmed) — the record being shared. `AccessLevel` accepts `Read` or `Edit` for a manual share (`All` is reserved for the record owner). Share to the **Group** Id, never the `Territory2` Id directly — a `Territory2` Id in `UserOrGroupId` fails with `INVALID_CROSS_REFERENCE_KEY`. If the share fails with `insufficient access` on `RowCause`, drop `RowCause` (it defaults to `Manual`).

---

## Part B Verification Gate

```bash
sf data query --query "SELECT Id, Status FROM ActionPlanTemplateVersion WHERE Status = 'Final' ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
sf data query --query "SELECT Id, AssociatedObjectId, ActionPlanTemplateVersionId FROM ActionPlanTemplateAssignment ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM GoalDefinitionShare WHERE RowCause = 'Manual' ORDER BY CreatedDate DESC LIMIT 2" --target-org <admin> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM ActionPlanTemplateShare WHERE ParentId = '<templateId>' AND RowCause = 'Manual'" --target-org <admin> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM ProviderAcctTerritoryInfoShare WHERE RowCause = 'Manual' ORDER BY LastModifiedDate DESC LIMIT 2" --target-org <admin> --json
```

Expect a version with `Status='Final'` (the parent template's `Status` propagates to `Final`), an assignment whose `AssociatedObjectId` is the Strategic goal and whose `ActionPlanTemplateVersionId` is that published version, and the five share records (2 `GoalDefinitionShare` + 1 `ActionPlanTemplateShare` + 2 `ProviderAcctTerritoryInfoShare`) whose `UserOrGroupId` equals the leaf-territory `<territoryGroupId>`.

---

## Part B Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Run everything as admin | Setup-level configuration |
| Confirm only the record names; auto-derive the rest | Per spec, names are the only user-supplied values |
| Create all 3 items AND their 6 item values BEFORE publishing | A published (`Status=Final`) version is immutable — items/values can't be added after |
| Publish by updating the **version** to `Status=Final`, never the template | `ActionPlanTemplate.Status` is read-only; the version's `Status` is the only writable path and propagates to the template |
| `GoalDefinitionProduct.ProductId` = Part A LifeSciMarketableProduct | Not the Product2 Id |
| `GoalDefinitionProduct` + `ActionPlanTemplateAssignment` reference the **Strategic** goal | Per spec |
| Share both `GoalDefinition` records + the `ActionPlanTemplate` + both `ProviderAcctTerritoryInfo` records to the leaf-territory **Group** | Admin owns the records; the KAM user reaches them only through the territory share |

## Part B Gotchas

| Issue | Resolution |
|-------|------------|
| Field name rejected (`Type`, `Name`, version-link) | Describe the sObject and use the reported API name; the values/strings are unchanged |
| Can't add items after publish | Publish is one-way — create a new version/template if items were missed |
| `ActionPlanTemplate` create/update rejects `Status` | `Status` is read-only on this object — omit it on create (defaults to `Draft`); publish by updating the **version** to `Final`, which propagates to the template |
| `No such column 'ActionPlanTemplateId' on ... ActionPlanTemplateAssignment` | This object has no `ActionPlanTemplateId` field — link via `ActionPlanTemplateVersionId=<versionId>` (the published version), not the template Id |
| `GoalDefinitionProduct` create fails on ProductId | Use the LifeSciMarketableProduct Id from Part A, not Product2 |
| `GoalDefinition` create fails on `IsActive` (`No such column`) | `GoalDefinition` has no `IsActive` field — its active flag is `Status` (`Active`/`Inactive`). Use `Status=Active` |
| `Share` create fails with `INVALID_CROSS_REFERENCE_KEY` on `UserOrGroupId` | You passed the `Territory2` Id — pass the territory **Group** Id from the `Group WHERE RelatedId=<territoryId>` query instead |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-5-data-creation-data.md` | Part A — object→CSV mapping, per-object field values, dependency chain |
