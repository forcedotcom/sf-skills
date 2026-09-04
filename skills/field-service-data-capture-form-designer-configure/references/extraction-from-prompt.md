# Extraction rules — natural-language sources

These are the rules to follow when given a prose description of a form (no PDF or image) and asked to produce the intermediate JSON spec for a Data Capture Flow.

The spec schema is the input contract of the build skill — see [field-types.md](../../fs-data-capture-form-deployer/reference/field-types.md) and [post-screen-automation.md](../../fs-data-capture-form-deployer/reference/post-screen-automation.md). This file covers extraction *behavior*; that file covers what the converter accepts.

## Output schema

```json
{
  "formTitle": "string",
  "formType": "string",
  "screens": {
    "PascalCaseScreenName1": [ /* fields */ ],
    "PascalCaseScreenName2": [ /* fields */ ]
  },
  "postScreen": { /* optional — see post-screen-automation.md */ }
}
```

Each field has these properties (only `fieldName`, `fieldLabel`, and `fieldType` are required):

| Property | Type | Notes |
|----------|------|-------|
| `fieldName` | string | camelCase or PascalCase, English, unique across the form, valid Salesforce API name. |
| `fieldLabel` | string | The label the user gave (or a faithful summary if they didn't give an explicit label). Strip required indicators (`*`, `(required)`). |
| `fieldType` | string | One of the supported types in `field-types.md`. Case-sensitive. |
| `isRequired` | boolean | true if the user said "required", "mandatory", "must enter", etc. |
| `defaultValue` | string \| null | null for input fields; for `DisplayText`, the static body text. |
| `options` | array \| null | Required for `Radio`, `Picklist`, `CheckboxGroup`, `Matrix` (column choices). null otherwise. |
| `repeaterFields` | array | Required for `Repeater`. List of nested field objects with the same shape. |
| `matrixRows` | array | Required for `Matrix`. List of row labels. |
| `min` / `max` / `value` | number | Optional for `Counter` — initial/min/max for the +/- counter. |
| `visibility` | object | Optional. `{ "field": "<fieldName>", "operator": "EqualTo", "value": "<choice display>" }` — show this field only when the referenced choice is selected. |
| `lookupObject` | string | Required for `Lookup`. Salesforce object API name (e.g. `"Asset"`, `"WorkOrder"`). |
| `lookupSearchFields` | string | Optional for `Lookup`. Comma-separated field API names searched by typeahead (e.g. `"Name, SerialNumber"`). |
| `lookupMulti` | boolean | Optional for `Lookup`. true to allow selecting multiple records. |
| `fileName` | string | Required for `FileView`. Static-asset filename without extension. |

## Output requirements

1. Output **only** the JSON object.
2. No markdown, no code fences, no explanation before or after.
3. Use `null` for null, `true`/`false` for booleans, double-quoted strings.
4. Stop immediately after the closing `}`.

## Field-type classification — explicit vocabulary required

For prose input (no visual reference), only choose specialized types (`Signature`, `UploadFile`, `UploadImage`, `FileView`, `Matrix`, `Address`, `Repeater`) when the user **explicitly** describes that control. The user saying "captures the inspector's signature" with no other context isn't enough — that could be a typed name or a real signature pad. Default to the simpler text/number/date type unless the user uses control vocabulary.

Use the **most specific** type the prose evidence supports. Default to `ShortText` when in doubt.

| Type | Prose evidence required |
|---|---|
| `Name` | User says the field captures a person's name (inspector, operator, technician, customer, employee). |
| `Email` | User says "email". |
| `Phone` | User says "phone", "phone number", "mobile", "contact number". |
| `Numeric` | User says "number", "count", or gives a numeric measurement (pressure, temperature, weight). |
| `Counter` | User says "counter", "stepper", "+/- quantity", "quantity field". |
| `Date` | User says "date". |
| `DateTime` | User says "date and time", "timestamp". |
| `Checkbox` | User says "checkbox" (singular). |
| `CheckboxGroup` | User says "select multiple", "all that apply", "checkbox group". |
| `Radio` | User says "radio", "single choice", "pick one", "select one". |
| `Picklist` | User says "dropdown", "picklist", "select from a list". For person-name dropdowns, prefer `Name`. |
| `Toggle` | User says "toggle" or "on/off switch". |
| `UploadFile` | User says "upload a file" / "attach a document" / explicitly describes a file picker. |
| `UploadImage` | User says "upload an image" / "add a photo" / "camera capture" / explicitly describes an image picker. |
| `FileView` | User explicitly asks for a read-only image viewer. |
| `Signature` | User says "signature pad" / "captures a signature" / explicitly describes a sign-here widget. |
| `Matrix` | User explicitly describes a same-question-per-row table (rows share OK/NOK columns). |
| `Repeater` | User says "add multiple rows" / "list of parts" / "repeat for each item" / "repeater". |
| `Address` | User explicitly says "compound address" or lists street/city/state/zip as a single block. |
| `LongText` | User says "notes", "comments", "long text", "description", "remarks". |
| `ShortText` | User just lists a label with no other vocabulary. **This is the default.** |
| `DisplayText` | User explicitly says "show static text" / "instructions". |
| `Lookup` | User says "lookup", "select a record", "pick an existing X". Requires `lookupObject` (the Salesforce object API name). |

### Anti-patterns (do NOT do these)

- ❌ User mentions "signature" → automatically `Signature`. They might mean a typed name. Only emit `Signature` when they say "signature pad", "sign-here widget", or similar control vocabulary.
- ❌ User mentions "photo" / "image" → automatically `UploadImage`. They might mean a description field. Only emit `UploadImage` when they say "upload an image", "add a photo", "camera capture".
- ❌ User mentions "address" → automatically `Address`. Single text line is fine for most addresses. Only emit `Address` for an explicit compound widget.
- ❌ User says "table" → automatically `Repeater` or `Matrix`. Ask for clarification: rows-the-user-adds (Repeater) vs. fixed-rows-with-shared-columns (Matrix).
- ❌ Inventing fields the user didn't mention. If the user says "asset id, condition rating, photos, and remarks", emit four fields. Don't add an "Inspector" or "Date Inspected" field just because forms usually have those.

When the evidence is ambiguous, **fall back to the simplest type** (`ShortText`, `LongText`, `Numeric`) and call it out in the confirmation step so the user can correct it before deploy.

## Conditional fields

If the user describes a field that depends on a previous answer ("if they pick Work Order, then ask for the WO number"), attach a `visibility` block:

```json
{
  "fieldName": "WorkOrderNumber",
  "fieldLabel": "WO Number",
  "fieldType": "ShortText",
  "isRequired": true,
  "visibility": { "field": "To", "operator": "EqualTo", "value": "Work Order" }
}
```

The `value` must match one of the parent field's `options` exactly (display text, not the api-sanitized name).

## Naming rules

- `fieldName`: camelCase or PascalCase, English. No spaces, no special characters (underscore allowed). Unique within the form. ≤ 80 chars.
- Screen keys: `PascalCase` describing the section (`HeaderInformation`, `OperatingParameters`, `VisualInspection`). Never `Screen1`, `Screen2`.
- `formTitle`: human-readable. The Flow's API name is derived from this by the deploy step.
- `formType`: short descriptor (e.g. `Inspection Report`, `Service Log`, `Inventory Transfer`).

## Label rules

- Use the user's words verbatim where possible. If the user gave a label, keep it. If they only described the field ("the inspector's name"), summarize concisely as the label ("Inspector Name").
- **Strip** any `*`, `(required)`, `(mandatory)` from the label and set `isRequired: true` instead.

## Screen grouping

- 8–12 fields per screen, max.
- A small form (≤ 8 fields) can be a single screen — don't fabricate sections.
- If the user described multiple sections ("first ask for header info, then measurements, then the parts list"), respect their grouping.
- If the user just listed fields with no sections, group them into one screen unless there are more than 12 fields. Then split logically.
- Use descriptive PascalCase screen names — never `Screen1`.

## Sections within a screen

A Section is a *visual grouping inside one screen* — distinct from splitting fields across multiple screens. **Default to a flat field list.** Emit sections only when the user explicitly describes named sub-groups within a single screen ("on the inspection screen, group fields under 'Asset Details' and 'Inspection Notes'"). Don't infer sections from a list of field topics — a list of fields is just a list of fields.

When you emit a section, insert a `{ "section": "Header Label" }` item into the screen's field list before the fields belonging to that group:

```json
{
  "screens": {
    "AssetInspection": [
      { "section": "Asset Details" },
      { "fieldName": "AssetName",    "fieldLabel": "Asset Name",    "fieldType": "ShortText" },
      { "fieldName": "Manufacturer", "fieldLabel": "Manufacturer",  "fieldType": "Picklist", "options": ["Demag","Konecranes"] },

      { "section": "Inspection" },
      { "fieldName": "Condition",    "fieldLabel": "Condition",     "fieldType": "Picklist", "options": ["Pass","Fail"] }
    ]
  }
}
```

**When NOT to use sections:**
- The user didn't explicitly name within-screen sub-groups.
- The user described separate steps (those become separate *screens*, not sections).
- You'd be inventing groupings the user didn't describe.

**Single-column only.** Sections render as full-width single-column groups. Don't try to express multi-column layouts.

**One-section screens are usually wrong.** A single section spanning the whole screen is just a screen with a redundant header bar. Either emit no sections, or emit ≥ 2 sections per screen.

## Post-screen automation — determine the desired outcome

A data capture form is rarely just a form. The captured data almost always needs to **do** something in Salesforce: create a record, update a record, look something up.

You **must** determine the desired outcome before finalizing the spec. A form that captures perfect data but never writes anything to Salesforce is a broken flow.

### Outcome-elicitation rules

For every form, ask yourself:

1. **What Salesforce object should be created or updated when the user finishes?** (e.g. ProductTransfer, WorkOrderLineItem, Case, Asset, ServiceAppointment.)
2. **Are any rows in a Repeater supposed to become individual records?** If yes, you need a `loop` over `<Repeater>.AddedItems` and a `recordCreate` per iteration.
3. **Does any captured value need to be resolved to a record Id before writing?** If yes, you need a `recordLookup`.
4. **Is the user picking a branch that determines which lookup or write to do?** If yes, you need a `decision`.
5. **Is there a parent record passed in via `parentRecordId` / `parentObjectType`?** This is the standard Field Service entry-point pattern.

### How to decide whether to emit `postScreen`

| Signal | Action |
|---|---|
| The user explicitly says what to create/update ("create a ProductTransfer for each part") | **Emit `postScreen`** with the named object and field mappings. |
| The user gives a form name or purpose that strongly implies a single object — Inventory Transfer, Work Order Completion, Asset Inspection, Damage Report, Time Entry | **Emit `postScreen`** with your best-guess object/field mapping AND list every `valueRef` / `field` in the confirmation step so the user can correct names. |
| The user describes a Repeater whose rows obviously become rows in Salesforce | **Emit `postScreen`** with a loop + recordCreate. State the assumption explicitly. |
| You truly cannot infer what the data should do, AND the user gave no hint | Surface a question in the confirmation step ("What should happen when this form is submitted?") with concrete options. Don't deploy a screens-only flow without flagging that the data goes nowhere. |

### Common outcome patterns

- **Inventory Transfer** (form has a parts repeater) → loop over `Part.AddedItems` → create one `ProductTransfer` per row, mapping `Product2Id`, `QuantitySent`, `QuantityReceived`, `DestinationLocationId`.
- **Inspection / Checklist** → create one `WorkOrderLineItem` or `Asset__History` record summarizing the inspection.
- **Time Entry** → create a `ResourceAbsence` or custom time-entry record tied to `parentRecordId`.
- **Damage Report** → update the parent Work Order and/or create child Case records.

### Validation for `postScreen`

When you emit a `postScreen` block, every reference must point at a real thing:

- Every `valueRef` is either: a `<fieldName>.value` from a screen field, a `<RepeaterName>.<ChildName>.value` inside a loop, a non-input variable you declared, or a global like `$User.Id`.
- Every `field` in `inputAssignments` and `outputAssignments` is the API name of a field on the named `object`. If you don't know the exact API name, use your best guess and list it in the confirmation step.
- Every `next` connector targets the name of an element you actually defined.
- The decision's branch `when.field` is a screen field, and `when.value` exactly matches one of that field's `options`.

## Validation checklist

Before returning, verify:

- [ ] Every screen key is PascalCase.
- [ ] Every `fieldName` is a valid API name, unique across the form (including inside repeaters).
- [ ] Every `fieldType` is one of the supported types in [field-types.md](../../fs-data-capture-form-deployer/reference/field-types.md) (case-sensitive).
- [ ] `Radio`, `Picklist`, `CheckboxGroup` have non-empty `options` (use 3–5 plausible options if the user didn't list specific ones, and surface that you guessed).
- [ ] `Matrix` has both `options` (columns) and `matrixRows`.
- [ ] `Repeater` has `repeaterFields` (each child has its own valid `fieldType`).
- [ ] Any `visibility.value` exactly matches one of the referenced field's `options`.
- [ ] **No fabricated fields the user didn't mention.** This is the most common prose-extraction bug — don't pad the form with "usual" fields.
- [ ] **Outcome is determined.** Either a `postScreen` block is emitted, or the confirmation step will explicitly ask the user what to do with the data.
- [ ] If `postScreen` is emitted: every `valueRef` resolves, every `field` belongs to the named `object` (or is flagged for user review), every `next` connector targets a defined element.
- [ ] **Specialized types are evidence-backed.** For every `Signature`, `UploadFile`, `UploadImage`, `Images`, `Matrix`, `Address`, `Lookup`, `FileView`, and `Repeater` in the output, name the prose evidence ("user said 'add multiple parts'"). If the user only used the *label* not the *control vocabulary*, downgrade the type per the table above. (These are real components that deploy as functional widgets — emitting them when the user only meant a text field is the most common bug.)
- [ ] **Lookup has `lookupObject`.** Every `Lookup` field has a `lookupObject` (Salesforce object API name). If the user didn't say which object, surface a question in the confirmation step or pick a best-guess and flag it.
- [ ] **FileView has `fileName`.** Every `FileView` field has a `fileName` (static asset filename, no extension). If unknown, surface a question.
- [ ] **Sections only where the user described them.** Every `{ "section": "..." }` item corresponds to a named sub-group the user actually mentioned. No invented sections, and no screens with exactly one section.

---

## Source design docs

This rule sheet is informed by two upstream design docs. Don't paste the full prompts from those docs into the user-facing flow — they're internal source-of-truth references.

- **Form-To-Flow AI HLD** ([doc](https://docs.google.com/document/d/1XlDRQE1gVrux8Iyz5LDupN9xV7i1IKpczLbsvMq5Tc4)) — the Flow Builder team's architecture for prose/PDF-to-DC-Flow generation.
- **Field Service POC HLD** ([doc](https://docs.google.com/document/d/10TO6CC983AcclXY7Ixp3I3hY5R7TagUMWP9VRqXOFoc)) — Field Service team's Apex+Agentforce POC. Source for the intermediate JSON contract and the extraction prompt rules.
