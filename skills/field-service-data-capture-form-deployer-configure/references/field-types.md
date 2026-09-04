# Field types reference

Mapping of intermediate-JSON `fieldType` to the runtime component used in the deployed Flow. The `Flow strategy` column is the `fieldType` value in the Flow `Metadata` JSON (see [flow-metadata-json.md](flow-metadata-json.md)). **All names here have been verified against a live Field Service org by retrieving real flows and deploying probe flows** (May 2026).

> **Picking a type:** classify from the actual control on the form, not from the field's label or name. A text line labeled "Signature" is `ShortText`. A textarea labeled "Photo of damage" is `LongText`. Only emit `Signature`, `UploadFile`, `UploadImage`, `FileView`, `Address`, `Matrix`, or `Repeater` when the source shows the corresponding widget (sign-here pad, file/camera picker, compound address, row-shared grid, user-added rows table) — or when the user explicitly describes that widget in prose. See the "control evidence" table in `extraction-prompt.md`.

## Verified types

| `fieldType`     | `extensionName`                                | Flow strategy            |
|-----------------|------------------------------------------------|--------------------------|
| `ShortText`     | `runtime_service_fieldservice:dcTextInput`     | `ComponentInstance`      |
| `LongText`      | `runtime_service_fieldservice:dcLongText`      | `ComponentInstance`      |
| `Name`          | `runtime_service_fieldservice:dcName`          | `ComponentInstance`      |
| `Email`         | `runtime_service_fieldservice:dcEmail`         | `ComponentInstance`      |
| `Phone`         | `runtime_service_fieldservice:dcPhone`         | `ComponentInstance`      |
| `Numeric`       | `runtime_service_fieldservice:dcNumeric`       | `ComponentInstance`      |
| `Counter`       | `runtime_service_fieldservice:dcCounter`       | `ComponentInstance` (supports `min`, `max`, `value` numeric params) |
| `Date`          | `runtime_service_fieldservice:dcDate`          | `ComponentInstance`      |
| `DateTime`      | `runtime_service_fieldservice:dcDateTime`      | `ComponentInstance`      |
| `Checkbox`      | `runtime_service_fieldservice:dcCheckbox`      | `ComponentInstance`      |
| `Toggle`        | `runtime_service_fieldservice:dcToggle`        | `ComponentInstance`      |
| `Picklist`      | `runtime_service_fieldservice:dcPicklist`      | `ComponentChoice`        |
| `Radio`         | `runtime_service_fieldservice:dcRbGroup`       | `ComponentChoice` (verified May 2026 via retrieved Inventory_Transfer flow) |
| `CheckboxGroup` | `runtime_service_fieldservice:dcCbGroup`       | `ComponentMultiChoice`   |
| `Signature`     | `runtime_service_fieldservice:dcSignature`     | `ComponentInstance` (auto-wires `parentRecordId` and `recordId` to the standard input variables) |
| `UploadFile`    | `runtime_service_fieldservice:dcUpFile`        | `ComponentInstance` (auto-wires `recordId` → `parentRecordId`) |
| `UploadImage`   | `runtime_service_fieldservice:dcUpImage`       | `ComponentInstance` (auto-wires `recordId` → `parentRecordId`) |
| `Images`        | `runtime_service_fieldservice:dcImages`        | `ComponentInstance` (gallery viewer, auto-wires `recordId` → `parentRecordId`) |
| `Address`       | `runtime_service_fieldservice:dcAddress`       | `ComponentInstance` (compound street/city/state/zip widget) |
| `Matrix`        | `runtime_service_fieldservice:dcMatrix`        | `ComponentMultiChoice` (column choices via `<choiceReferences>`; row labels via `questions` JSON-array input parameter) |
| `Lookup`        | `runtime_service_fieldservice:dcLookup`        | `ComponentInstance` (requires `lookupObject`; optional `lookupSearchFields`, `lookupMulti`) |
| `FileView`      | `runtime_service_fieldservice:dcFileView`      | `ComponentInstance` (requires `fileName` — static asset filename without extension) |
| `DisplayText`   | (native — no extension)                        | native `DisplayText`     |
| `Repeater`      | (native — no extension; nested `<fields>`)     | native `Repeater` (verified May 2026; supports any `ComponentInstance` child) |

## Falls back to a placeholder

| `fieldType`  | Falls back to                               | Why |
|--------------|---------------------------------------------|-----|
| `Lookup` *with no `lookupObject`* | `dcTextInput` w/ `[Lookup — set objectApiName in Flow Builder]` prefix | `dcLookup` deploys but won't render without an `objectApiName`. Supply `lookupObject` in the spec or the admin must wire it up in Flow Builder. |
| `FileView` *with no `fileName`* | `dcTextInput` w/ `[FileView — set fileName in Flow Builder]` prefix | `dcFileView` needs a static asset `fileName`. |

## Required Flow boilerplate

A Data Capture Flow won't deploy without these keys in `Metadata`:

1. **`environments`** must include `Offline`:
   ```json
   "environments": ["Offline"]
   ```
2. **Three input variables** (Text, Available for Input):
   ```json
   "variables": [
     { "name": "parentObjectType", "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false },
     { "name": "parentRecordId",   "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false },
     { "name": "recordId",         "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false }
   ]
   ```
3. **`processType`** must be `DataCaptureFlow`.

## Choice/MultiChoice fields

For `Picklist`, `Radio` (`dcRbGroup`), and `CheckboxGroup`, options are NOT inline parameters. They are top-level `choices` entries referenced from the field via a `choiceReferences` array:

```json
"choices": [
  { "name": "Good", "choiceText": "Good", "dataType": "String", "value": { "stringValue": "Good" } }
]
```
```json
{
  "name": "overallCondition",
  "choiceReferences": ["Good", "Fair", "Poor"],
  "extensionName": "runtime_service_fieldservice:dcPicklist",
  "fieldText": "Overall Condition",
  "fieldType": "ComponentChoice",
  "inputsOnNextNavToAssocScrn": "UseStoredValues",
  "isRequired": true,
  "storeOutputAutomatically": true
}
```

Dedupe choices across the whole flow — two fields with `["Good","Fair","Poor"]` share the same three `choices` entries.

## Repeater fields

`Repeater` is a native Flow field type — not a component. The JSON shape (children are a nested `fields` array):

```json
{
  "name": "Part",
  "fieldType": "Repeater",
  "fields": [
    { "name": "Quantity",    "extensionName": "runtime_service_fieldservice:dcCounter",   "fieldType": "ComponentInstance" },
    { "name": "Part_Number", "extensionName": "runtime_service_fieldservice:dcTextInput", "fieldType": "ComponentInstance" }
  ],
  "isRequired": false,
  "styleProperties": { "verticalAlignment": { "stringValue": "top" }, "width": { "stringValue": "12" } }
}
```

In the spec, supply children as `repeaterFields`:

```json
{
  "fieldName": "Part",
  "fieldLabel": "Parts",
  "fieldType": "Repeater",
  "isRequired": false,
  "repeaterFields": [
    { "fieldName": "Quantity", "fieldLabel": "Quantity", "fieldType": "Counter", "isRequired": true, "min": 1, "value": 1 },
    { "fieldName": "Part_Number", "fieldLabel": "Part Number", "fieldType": "ShortText", "isRequired": true },
    { "fieldName": "Part_Description", "fieldLabel": "Part Description", "fieldType": "ShortText", "isRequired": true }
  ]
}
```

The runtime exposes the captured rows as the collection `<RepeaterName>.AddedItems`, with each row's child accessible as `<loopVar>.<ChildName>.value` inside a Loop element. See `flow-metadata-json.md` for the loop/createRecord pattern.

## Counter min/max/value

`dcCounter` accepts these optional numeric input parameters: `min`, `max`, `value` (initial value). In the spec:

```json
{
  "fieldName": "Quantity",
  "fieldLabel": "Quantity",
  "fieldType": "Counter",
  "isRequired": true,
  "min": 1,
  "max": 999,
  "value": 1
}
```

## Specialized component spec keys

### Signature / UploadFile / UploadImage / Images

Auto-wired — no extra spec keys needed. Inject:
- `Signature` → `parentRecordId` and `recordId` input parameters, both as `{ "elementReference": ... }` to the flow's standard input variables of the same name.
- `UploadFile` / `UploadImage` / `Images` → `recordId` input parameter as `{ "elementReference": "parentRecordId" }` (the runtime attaches the captured file/image to the parent record passed in via `parentRecordId`).

These standard input variables are present on every flow:

```json
"variables": [
  { "name": "parentObjectType", "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false },
  { "name": "parentRecordId",   "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false },
  { "name": "recordId",         "dataType": "String", "isCollection": false, "isInput": true, "isOutput": false }
]
```

So `Signature` / `UploadFile` / `UploadImage` / `Images` deploy and run end-to-end as long as the flow is launched from a standard Field Service entry point (Mobile App, Work Order, Asset, etc.) that supplies `parentRecordId`.

### Address

No extra spec keys. Renders as `dcAddress` ComponentInstance with the field label.

### Matrix

```json
{
  "fieldName": "PreTripChecklist",
  "fieldLabel": "Pre-trip checklist",
  "fieldType": "Matrix",
  "isRequired": true,
  "options":   ["OK", "NOK", "N/A"],
  "matrixRows": ["Tires", "Lights", "Brakes", "Fluids"]
}
```

- `options` become column choices (`<choiceReferences>`), exactly like Picklist.
- `matrixRows` become per-row prompts, JSON-encoded into the `questions` input parameter as a string array.

### Lookup

```json
{
  "fieldName": "AssetLookup",
  "fieldLabel": "Asset",
  "fieldType": "Lookup",
  "isRequired": true,
  "lookupObject": "Asset",
  "lookupSearchFields": "Name, SerialNumber",
  "lookupMulti": false
}
```

- `lookupObject` (required) — the object API name to look up against.
- `lookupSearchFields` — comma-separated field API names searched by typeahead.
- `lookupMulti` (or `isMultiSelection`) — `true` to allow selecting multiple records.

If `lookupObject` is missing, the field renders as a labeled ShortText placeholder so the flow still deploys.

### FileView

```json
{
  "fieldName": "ManualPreview",
  "fieldLabel": "Manual",
  "fieldType": "FileView",
  "fileName": "service_manual_v3"
}
```

`fileName` is the static-asset filename (without extension). If missing, falls back to a labeled ShortText placeholder.

## Visibility rules

A field can be conditionally shown based on a previously-captured field. The spec shape:

```json
{
  "fieldName": "Work_Order_Number",
  "fieldLabel": "Work Order Number",
  "fieldType": "ShortText",
  "isRequired": true,
  "visibility": {
    "field": "To",
    "operator": "EqualTo",
    "value": "Work Order"
  }
}
```

Look up the matching choice api name (e.g. `Work_Order`) and emit a `visibilityRule` on the field:

```json
"visibilityRule": {
  "conditionLogic": "and",
  "conditions": [
    { "leftValueReference": "Work_Order", "operator": "EqualTo", "rightValue": { "booleanValue": true } }
  ]
}
```

> Note: Field Service's runtime evaluates visibility against the choice's *boolean selection state*, not the parent field's string value. The `leftValueReference` is therefore the **choice api name**, not the field name. If `visibility.value` doesn't match any known choice, warn and skip the rule.

## Field name rules

- `fieldName` must match `^[A-Za-z][A-Za-z0-9_]*$`, ≤ 80 chars, unique per flow.
- Choice api names are derived from the option's display text (sanitized).
- Screen api names are derived as `Screen_<PascalCaseScreenKey>`.

## Sections

A Section is a visual grouping inside a screen, rendered as a Salesforce Flow `RegionContainer` (one full-width Region column) with a header bar showing the section label. Use sections **only when the source explicitly shows them** (visible group headers in an image/PDF, or the user describing named sub-sections in prose). A flat field list is the right default.

To declare sections, mix section-header items into a screen's field list. A section header is an item with a `section` key and **no** `fieldName`:

```json
{
  "screens": {
    "AssetInspection": [
      { "section": "Asset Details" },
      { "fieldName": "AssetName",    "fieldLabel": "Asset Name",    "fieldType": "ShortText" },
      { "fieldName": "Manufacturer", "fieldLabel": "Manufacturer",  "fieldType": "Picklist",  "options": ["Demag","Konecranes"] },

      { "section": "Inspection" },
      { "fieldName": "Condition",    "fieldLabel": "Condition",     "fieldType": "Picklist",  "options": ["Pass","Fail"] },
      { "fieldName": "Notes",        "fieldLabel": "Notes",         "fieldType": "LongText"   }
    ]
  }
}
```

Rules:
- A `section` item starts a new section. All subsequent fields belong to it until the next `section` item or the end of the screen.
- Fields appearing **before** the first `section` item are bucketed into an implicit section labeled `"General"`.
- Specs with no `section` items deploy as a flat field list — fully backward-compatible.
- Sections are **single-column, full-width** by default. Multi-column layouts are not generated; if a source shows two columns, file each field separately and let it stack.
- Section api names are auto-derived from the label (`Sec_<sanitized>`, deduped within the screen).

The emitted JSON matches the verified `SectionWithHeader` pattern from `salesforce-data-capture/examples/Data_Capture_All_Components.flow-meta.xml`:

```json
{
  "name": "Sec_Asset_Details",
  "fieldText": "Asset Details",
  "fieldType": "RegionContainer",
  "fields": [
    {
      "name": "Sec_Asset_Details_Col1",
      "fieldType": "Region",
      "fields": [ /* AssetName, Manufacturer, etc. */ ],
      "inputParameters": [
        { "name": "width", "value": { "stringValue": "12" } }
      ],
      "isRequired": false
    }
  ],
  "isRequired": false,
  "regionContainerType": "SectionWithHeader",
  "styleProperties": {}
}
```
