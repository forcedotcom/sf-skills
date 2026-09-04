# KAM & Sprint Config-Record Edits (Stage 2, Step 14)

After the LifeSciConfigRecords deploy (Step 7) succeeds and the 10 KAM StandardValueSets are confirmed (Step 1), set the picklist values in the two org-level config records, then re-deploy. Config deploys are **upsert** — re-deploying updates the existing records, it does not duplicate them.

Both files live under `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord/lifeSciConfigRecords/`:
- `KAMSettings_OrgLevel.lifeSciConfigRecord`
- `SprintSettings_OrgLevel.lifeSciConfigRecord`

Each setting is a `<fieldValues>` block. A single-value picklist uses `<dataType>PICKLIST</dataType>` + `<picklistValue>…</picklistValue>`; a multi-select uses `<dataType>MULTIPICKLIST</dataType>` + `<longTextValue>…</longTextValue>` (values `;`-separated). Do **not** invent new elements — only change the value inside the existing `<picklistValue>` / `<longTextValue>` tag.

---

## KAMSettings_OrgLevel — six single-value picklist fields

Each value MUST be exactly **one** value drawn from the noted StandardValueSet (confirmed in Step 1). The starter file ships with sensible defaults; confirm each with the admin and change only if they differ.

| `<fieldName>` | Source StandardValueSet | Cardinality | Default in file | Element to edit |
|---------------|------------------------|-------------|-----------------|-----------------|
| `StatusValueForAP` | `AccountPlanStatus` | ONE | `Completed` | `<picklistValue>` |
| `StatusValueForAPO` | `AccPlanObjectiveStatus` | ONE | `Completed` | `<picklistValue>` |
| `NotStartedStatusValueForAP` | `ActionPlanState` | ONE | `Not Started` | `<picklistValue>` |
| `CompletionStatusValueForAP` | `ActionPlanState` | ONE | `Completed` | `<picklistValue>` |
| `CompletionStatusValueForTBP` | `TerritoryBusinessPlanStatus` | ONE | `Completed` | `<picklistValue>` |
| `CompletionStatusValueForGA` | `GoalAssignmentStatus` | ONE | `Completed` | `<picklistValue>` |

Example block (do not change `dataType`/`fieldName`/`hasBooleanValue`):

```xml
<fieldValues>
    <dataType>PICKLIST</dataType>
    <fieldName>StatusValueForAP</fieldName>
    <hasBooleanValue>false</hasBooleanValue>
    <picklistValue>Completed</picklistValue>
</fieldValues>
```

Leave the trailing `<isActive>`, `<isOrgLevel>`, `<lifeSciConfigCategory>KAMSettings</lifeSciConfigCategory>`, and `<masterLabel>KAMSettings_OrgLevel</masterLabel>` elements as-is.

---

## SprintSettings_OrgLevel — one multi-select field

| `<fieldName>` | Source StandardValueSet | Cardinality | Default in file | Element to edit |
|---------------|------------------------|-------------|-----------------|-----------------|
| `StatusValueForSprint` | `SprintStatus` | ONE OR MORE (`;`-separated) | `Completed` | `<longTextValue>` |

`StatusValueForSprint` is a `MULTIPICKLIST` — its value goes in **`<longTextValue>`**, not `<picklistValue>`. To select more than one status, separate them with a semicolon and no surrounding spaces:

```xml
<fieldValues>
    <dataType>MULTIPICKLIST</dataType>
    <fieldName>StatusValueForSprint</fieldName>
    <hasBooleanValue>false</hasBooleanValue>
    <longTextValue>In Progress;Completed</longTextValue>
</fieldValues>
```

---

## Deploy the edited config records

Re-deploy the whole `lifeSciConfigRecord` directory (upsert-safe) from inside the project root:

```bash
sf project deploy start -d .lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord --target-org <org>
```

Confirm **zero component failures** in the deploy result. Then verify the values landed:

```bash
sf data query --query "SELECT Id, MasterLabel FROM LifeSciConfigRecord WHERE MasterLabel IN ('KAMSettings_OrgLevel','SprintSettings_OrgLevel')" --target-org <org> --json
```

Both records must be present. (The individual field values are stored as child `LifeSciConfigRecordDetail`/field-value rows; the successful upsert deploy with 0 failures is the authoritative confirmation the picklist values were written.)

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Edit didn't take effect | You may have edited the wrong element — single picklists use `<picklistValue>`, the Sprint multi-select uses `<longTextValue>`. Re-edit and re-deploy |
| Multiple Sprint statuses not applying | Separate them with `;` (no spaces) inside a single `<longTextValue>`; do not add extra `<fieldValues>` blocks for the same field |
| Value rejected on deploy | The value must exactly match an entry in the source StandardValueSet (confirmed in Step 1); check spelling/casing |
| Config records fail with `Enter an assignment level and an assignment ID.` | The `LSC Custom Profile` was absent — this should not happen at Step 14 (Step 7 already ran); re-confirm Step 6/7 succeeded |
