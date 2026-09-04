# Extraction rules — visual sources (PDF / image)

These are the rules to follow when given a `.pdf`, `.png`, `.jpg`, or `.jpeg` and asked to produce the intermediate JSON spec for a Data Capture Flow.

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
| `fieldLabel` | string | Exact label from the source. Preserve original language, units, special characters. Strip required indicators (`*`, `(required)`). |
| `fieldType` | string | One of the supported types in `field-types.md`. Case-sensitive. |
| `isRequired` | boolean | true if the source had `*`, "required", "mandatory", "Pflichtfeld", "obligatoire", etc. |
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

## Field-type classification — control evidence over labels

Pick a field type from what the *control* does, not from what the *label* says. A field labeled "Signature" that's just a text line is `ShortText`, not `Signature`. A field labeled "Photo of damage" that's a description box is `LongText`, not `UploadImage`. The label is a hint; the rendered UI control is the answer.

Use the **most specific** type the visual evidence supports. Default to `ShortText` when in doubt.

| Type | Control evidence required (PDF/image) |
|---|---|
| `Name` | A text input whose label is an unambiguous person role: Inspector, Operator, Technician, Employee, Customer Name, Reported By. Plain "Name" alone is fine. **A dropdown control with a person-role label (e.g. "--Select Inspector--", "Choose Operator ▼") is still `Name`, not `Picklist`** — the data captured is a person, and the runtime treatment of person fields is what matters. |
| `Email` | Text input with `@` placeholder, label "Email", or input attribute hints. |
| `Phone` | Text input with phone formatting, label "Phone", "Tel", "Mobile". |
| `Numeric` | Numeric input, often with units (°C, mm, kg, bar, %). |
| `Counter` | A `+` / `-` stepper widget *or* explicit "Quantity" with stepper UI. Default `min: 1, value: 1`. |
| `Date` | A date picker (calendar icon, `MM/DD/YYYY` placeholder). |
| `DateTime` | A date+time picker. |
| `Checkbox` | A single standalone checkbox with one label. |
| `CheckboxGroup` | Multiple checkboxes under one heading or "select all that apply". |
| `Radio` | Radio buttons / "(circle one)" / mutually exclusive options visible on the form. |
| `Picklist` | A combo box / dropdown indicator (▼ ▾ ⌄, "Select…"). For person-name dropdowns, prefer `Name`. Supply 3–5 sample options. |
| `Toggle` | An on/off switch UI element (rounded slider). |
| `UploadFile` | A file-picker control: "Choose file", paperclip icon, drag-drop zone, attachment slot. **Not** a label that mentions a file. |
| `UploadImage` | An image-upload control: camera icon, "Add photo" button, image drop zone. **Not** a label like "Photo" on a text line. |
| `FileView` | A read-only image preview / pre-attached image. |
| `Signature` | A signature pad (a labeled empty box sized for handwriting, with "Sign here" / "Signature" inside the box, often with an X-line). **Not** a one-line text field labeled "Signature". |
| `Matrix` | A grid where each row asks the same question with shared answer columns (e.g. row=item, columns=OK/NOK/N/A). ONE field with `matrixRows` + `options`. |
| `Repeater` | A table with input columns where the user adds N rows (e.g. Part Number / Quantity / Description). ONE field with `repeaterFields`. |
| `Address` | A compound address widget with separate sub-inputs (street + city + state + zip + country). |
| `LongText` | A multi-line text box (textarea, ≥3 lines tall, "Notes" / "Comments" / "Remarks"). |
| `ShortText` | A single-line text input. **This is the default** when no other evidence applies. |
| `DisplayText` | Static instructional text with no input control. Set `defaultValue` to the body. |
| `Lookup` | A typeahead/record-search input bound to a Salesforce object (search-as-you-type that resolves to a record). Requires `lookupObject` (the Salesforce object API name) supplied via the spec. |

**Multi-part fields** (e.g. "D0: ___ Ref.-Dim.: ___") → extract each part as its own field with its own classification.

### Repeater extraction rules

A `Repeater` is for tables where each row is a **user-added item** with **input columns** (the user types/picks per cell). Distinct from `Matrix`, which is a fixed set of rows that share **selection columns** (OK / NOK / N/A — pick one).

| Pattern | Type |
|---|---|
| Table: `Parameter \| Old Value \| New Value` (user types in each cell) | `Repeater` |
| Table: `Component \| OK \| NOK \| N/A \| Repair` (user picks one per row) | `Matrix` |

When emitting a `Repeater`, populate `repeaterFields` with one nested field per **input column**, classified using the same evidence rules above. Skip any selection-only "OK/NOK" columns — those mean it's a `Matrix`.

**Merge side-by-side / stacked repeaters with the same columns.** If the source visually splits one logical table into two blocks (top half / bottom half, left / right) because of page-space constraints, but both blocks have the same column structure — emit **one** Repeater. Two Repeater fields with identical `repeaterFields` is almost always a mistake.

**Dedupe columns with the same label.** If a table has the same column label appearing twice and the data captured is the same kind of thing, include the column **once** in `repeaterFields`.

**Skip symbol-only columns.** Single-character or symbol headers (`Δ`, `Σ`, `→`, blank) are typically separators or change indicators, not data inputs.

### Anti-patterns (do NOT do these)

- ❌ Label contains "signature" → automatically `Signature`. The control might be a single-line text field where the inspector types their name. Only emit `Signature` if you can see a sign-here pad.
- ❌ Label contains "photo" / "image" / "picture" → automatically `UploadImage`. The control might be a description text box. Only emit `UploadImage` when you see a camera/upload widget.
- ❌ Label contains "attach" / "file" / "document" → automatically `UploadFile`. Same rule — needs an actual file picker.
- ❌ Label contains "address" → automatically `Address`. A single text line for address is `ShortText` or `LongText`. Only emit `Address` for a compound widget with separate sub-inputs.
- ❌ Any table → `Repeater`. A table where each row is a fixed inspection point (with shared OK/NOK columns) is `Matrix`, not `Repeater`.
- ❌ Any list of options → `Picklist`. If the source explicitly shows radio buttons or "circle one", use `Radio`.

When the evidence is ambiguous, **fall back to the simplest type** (`ShortText`, `LongText`, `Numeric`) and call it out in the confirmation step so the user can correct it before deploy.

## Conditional fields

If a field on the form is preceded by something like "If Work Order, also fill: WO#" or only makes sense given a previous answer, attach a `visibility` block:

```json
{
  "fieldName": "WorkOrderNumber",
  "fieldLabel": "WO#",
  "fieldType": "ShortText",
  "isRequired": true,
  "visibility": { "field": "To", "operator": "EqualTo", "value": "Work Order" }
}
```

The `value` must match one of the parent field's `options` exactly (display text, not the api-sanitized name).

## Naming rules

- `fieldName`: camelCase or PascalCase, English even if the label is in another language. No spaces, no special characters (underscore allowed). Unique within the form. ≤ 80 chars.
- Screen keys: `PascalCase` describing the section (`HeaderInformation`, `OperatingParameters`, `VisualInspection`). Never `Screen1`, `Screen2`.
- `formTitle`: human-readable, original language allowed. The Flow's API name is derived from this by the deploy step.
- `formType`: short descriptor (e.g. `Inspection Report`, `Service Log`, `Inventory Transfer`).

## Label rules

- **Preserve** original language, umlauts/accents, units, bilingual text exactly as shown (`"Kennwort: / Job name:"`).
- **Strip** leading `*`, `(required)`, `(mandatory)`, `Pflichtfeld` from the label and set `isRequired: true` instead.
- **Do not** translate or rephrase.

## Screen grouping

- 8–12 fields per screen, max.
- A form with a single section and a repeater can be a single screen — don't fabricate sections.
- Group by logical sections in the source (header info, measurements, inspection, attachments, signatures…).
- Use the source's section breaks where they exist.
- Use descriptive PascalCase screen names — never `Screen1`.

## Sections within a screen

A Section is a *visual grouping inside one screen* — distinct from splitting fields across multiple screens. Emit a section **only when the source visibly shows a labeled group header** (a banner/heading like "Asset Details", "Inspection Notes", a colored separator with a title, or a visibly bordered group).

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
- The source has no visible group headers — emit a flat field list.
- The source uses one heading per screen (these are *screen names*, not within-screen sections).
- You'd be inventing groupings the source doesn't show.

**One-section screens are usually wrong.** A single section spanning the whole screen is just a screen with a redundant header bar. Either emit no sections, or emit ≥ 2 sections per screen.

## Post-screen automation — determine the desired outcome

A data capture form is rarely just a form. The captured data almost always needs to **do** something in Salesforce: create a record, update a record, look something up. That "do something" is the desired outcome.

You **must** determine the desired outcome before finalizing the spec. A form that captures perfect data but never writes anything to Salesforce is a broken flow.

### Outcome-elicitation rules

For every form, ask yourself:

1. **What Salesforce object should be created or updated when the user finishes the form?** (e.g. ProductTransfer, WorkOrderLineItem, Case, Asset, ServiceAppointment.)
2. **Are any rows in a Repeater supposed to become individual records?** If yes, you need a `loop` over `<Repeater>.AddedItems` and a `recordCreate` per iteration.
3. **Does any captured value need to be resolved to a record Id before writing?** If yes, you need a `recordLookup`.
4. **Is the user picking a branch that determines which lookup or write to do?** If yes, you need a `decision`.
5. **Is there a parent record passed in via `parentRecordId` / `parentObjectType` that should be referenced or updated?** This is the standard Field Service entry-point pattern.

### How to decide whether to emit `postScreen`

| Signal | Action |
|---|---|
| The form's name or purpose strongly implies a single object — Inventory Transfer, Work Order Completion, Asset Inspection, Damage Report, Time Entry | **Emit `postScreen`** with your best-guess object/field mapping AND list every `valueRef` / `field` in the confirmation step so the user can correct names. |
| The form has a Repeater whose rows obviously become rows in Salesforce (parts, line items, time entries, photos with metadata) | **Emit `postScreen`** with a loop + recordCreate. State the assumption explicitly. |
| You're refining an existing flow the user pointed you at | **Mirror the existing flow's `postScreen`** (same object, same field shape). |
| You truly cannot infer what the data should do | Surface a question to the user in the confirmation step ("What should happen when this form is submitted?") and emit no `postScreen` until they answer. |

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
- [ ] `Radio`, `Picklist`, `CheckboxGroup` have non-empty `options`.
- [ ] `Matrix` has both `options` (columns) and `matrixRows`.
- [ ] `Repeater` has `repeaterFields` (each child has its own valid `fieldType`).
- [ ] Any `visibility.value` exactly matches one of the referenced field's `options`.
- [ ] No required indicators (`*`, "(required)") left in any label.
- [ ] No translations of original labels.
- [ ] No fabricated fields the source doesn't have.
- [ ] **Outcome is determined.** Either a `postScreen` block is emitted, or the confirmation step will explicitly ask the user what to do with the data.
- [ ] If `postScreen` is emitted: every `valueRef` resolves, every `field` belongs to the named `object` (or is flagged for user review), every `next` connector targets a defined element, and decision branch `value`s match a parent field's `options`.
- [ ] **Specialized types are evidence-backed.** For every `Signature`, `UploadFile`, `UploadImage`, `Images`, `FileView`, `Address`, `Matrix`, `Lookup`, and `Repeater` in the output, name the visual evidence (camera-icon button, sign-here pad, +/- stepper, table with row-add button, typeahead picker). If you can only point to the field's *label*, downgrade the type per the table above. (These deploy as **real functional components** — `dcSignature`, `dcUpImage`, `dcMatrix`, etc. — so emitting them when the source only shows a text line is the most common extraction bug.)
- [ ] **Lookup has `lookupObject`.** Every `Lookup` field has a `lookupObject` (Salesforce object API name). If the source doesn't make it explicit, pick a best-guess and flag it in the confirmation step.
- [ ] **FileView has `fileName`.** Every `FileView` field has a `fileName` (static asset filename, no extension). If unknown, surface a question.
- [ ] **Repeaters are not duplicated.** No two `Repeater` fields have identical `repeaterFields` (merge side-by-side or stacked tables that share columns). No `repeaterFields` entries for symbol-only headers (`Δ`, `Σ`).
- [ ] **Sections only where the source shows them.** Every `{ "section": "..." }` item corresponds to a visible group header in the source. No invented sections, and no screens with exactly one section.

---

## Source design docs

This rule sheet is informed by two upstream design docs. Don't paste the full prompts from those docs into the user-facing flow — they're internal source-of-truth references.

- **Form-To-Flow AI HLD** ([doc](https://docs.google.com/document/d/1XlDRQE1gVrux8Iyz5LDupN9xV7i1IKpczLbsvMq5Tc4)) — the Flow Builder team's architecture for PDF-to-DC-Flow generation.
- **Field Service POC HLD** ([doc](https://docs.google.com/document/d/10TO6CC983AcclXY7Ixp3I3hY5R7TagUMWP9VRqXOFoc)) — Field Service team's Apex+Agentforce POC. Source for the intermediate JSON contract and the extraction prompt rules.
