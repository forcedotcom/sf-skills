# Component Mapping Reference

Mapping from legacy Field Service Mobile (`FieldServiceMobile` process type) flow
components to Data Capture Flow (`DataCaptureFlow` process type) equivalents.

> **Source of truth.** The authoritative supported/unsupported decisions live in
> [`fsm-dc-capability-catalog.md`](./fsm-dc-capability-catalog.md) and its
> executable twin `scripts/fsm_dc_catalog.py`. This file is a human-readable
> companion; where the two ever disagree, the catalog wins.

## Keyed on the real FSM vocabulary — not Lightning names

FSM Flow screen fields use the standard Flow `FlowScreenFieldType` enum:
`InputField`, `DropdownBox`, `RadioButtons`, `MultiSelectCheckboxes`,
`DisplayText`, `LargeTextArea`, `PasswordField`, `ComponentInstance`, …

A `lightning:*` / `forceContent:*` / `c:*` name is **not** a field type — it only
ever appears as the `<extensionName>` *inside* a `ComponentInstance` field. So
classification is always **`fieldType` first, `extensionName` second**. An earlier
version of this skill keyed its decisions off `lightning:input` /
`lightning:fileUpload` names; that was wrong and produced the two errors corrected
in the catalog (signature, file-upload). See W-23364461.

## Class 1 — Direct mappings (clean FSM → DC path)

Keyed by the FSM `<fieldType>`; `InputField` is further resolved by its
`<dataType>`, and `ComponentInstance` by its `<extensionName>`.

| FSM `<fieldType>` | Discriminator | Data Capture | DC extension |
|---|---|---|---|
| `InputField` | dataType `String` | ShortText | `dcTextInput` |
| `InputField` | dataType `TextArea`/`LongTextArea` | LongText | `dcLongText` |
| `InputField` | dataType `Email` | Email | `dcEmail` |
| `InputField` | dataType `Phone` | Phone | `dcPhone` |
| `InputField` | dataType `Number`/`Double`/`Currency` | Numeric | `dcNumeric` |
| `InputField` | dataType `Date` | Date | `dcDate` |
| `InputField` | dataType `DateTime` | DateTime | `dcDateTime` |
| `InputField` | dataType `Boolean` | Checkbox | `dcCheckbox` — *(see discrepancy in catalog)* |
| `InputField` | dataType `Picklist` | Picklist | `dcPicklist` |
| `InputField` | dataType `MultiselectPicklist` | CheckboxGroup | `dcCbGroup` |
| `LargeTextArea` | — | LongText | `dcLongText` |
| `DropdownBox` | — | Picklist | `dcPicklist` |
| `RadioButtons` | — | Radio | `dcRbGroup` |
| `RadioButtonGroup` | — | Radio | `dcRbGroup` |
| `MultiSelectCheckboxes` | — | CheckboxGroup | `dcCbGroup` |
| `MultiSelectPicklist` | — | CheckboxGroup | `dcCbGroup` *(or `dcPicklist` multi-mode)* |
| `DisplayText` | — | DisplayText | *(pass-through; review formulas)* |
| `ComponentInstance` | ext `forceContent:fileUpload` | UploadFile | `dcUpFile` |
| `ComponentInstance` | ext `forceContent:imageUpload` | UploadImage | `dcUpImage` |
| `ComponentInstance` | ext already `runtime_service_fieldservice:dc*` | *(pass-through, cleaned)* | — |

`DisplayText` is the only field type valid in **both** flow types.
`forceContent:fileUpload` is the **only** screen extension core allows inside an
FSM flow (per `FieldServiceMobileFlowValidator`).

## Class 2 — No DC equivalent (flag, never silently drop)

These FSM field types have nothing on the DC side and cannot auto-migrate. The
analyzer flags each in its Data Capture Gap Report.

| FSM `<fieldType>` | Reason | Recommended approach |
|---|---|---|
| `PasswordField` | No DC password component | Capture as `dcTextInput` only if non-secret, else drop |
| `DisplayRichText` | No DC rich-text display | Downgrade to `DisplayText`; rich formatting lost |
| `PlainButtons` | **Capability gap** — DC has no action buttons | Remove or redesign; no migration path |
| `ComponentInstance` w/ any custom ext (`c:*`, or `lightning:*` other than the whitelisted `forceContent:fileUpload`) | DC has no custom-component extension point | Rebuild with a native `dc*` component or flag as unmigratable |

Multi-select choice types (`MultiSelectPicklist`, `MultiSelectCheckboxes`) and
`RadioButtonGroup` are **not** gaps — they map to DC via `ComponentMultiChoice` /
`ComponentChoice` (see Class 1). DC has no *single* component covering both single-
and multi-select, but `dcPicklist` covers both modes and `dcCbGroup` covers multi.

## Class 3 — DC-only components (no FSM source produces them)

These exist only in Data Capture; **nothing in a source FSM flow migrates into
them**, so the converter never emits them from a migration.

| DC component | Notes |
|---|---|
| `dcSignature` | Signature capture — **FSM has no signature component** (see correction below) |
| `dcEmail` / `dcPhone` / `dcName` | Dedicated inputs (FSM approximates via `InputField`) |
| `dcAddress` | Address input (optional GPS) |
| `dcLookup` | Record lookup |
| `dcMatrix` | Matrix / grid input |
| `dcCounter` | Numeric stepper |
| `dcCheckbox` | Single checkbox — distinct from Boolean/Toggle (see discrepancy in catalog) |
| `dcFileView` | Read-only file/image viewer (requires `fileName`) |
| `dcUpImage` | Image upload (dedicated component) |
| `Region` / `RegionContainer` / `Repeater` / `ObjectProvided` | Layout/structural — FSM disallows |

> **`dcImages` does not exist.** Image upload is `dcUpImage`; the read-only
> file/image viewer is `dcFileView`.

### Correction: Signature is DC-only (WI-3 reversal)

An earlier decision (WI-3 / W-23364096) recorded that file-upload **and
signature** were supported FSM → DC migration targets. Core disproves the
signature half: `FieldServiceMobileFlowValidator` whitelists exactly one screen
extension — `forceContent:fileUpload` — and there is **no** native FSM signature
component anywhere in the FSM path. `dcSignature` is DataCaptureFlow-only. There
is no FSM signature source to migrate *from*, so the skill emits no `dcSignature`
and the downstream signature-emission task (WI-7 / W-23364093) is reverted. The
file-upload half of WI-3 stands, but keyed on `forceContent:fileUpload → dcUpFile`,
never `lightning:fileUpload`.

## Automation element mapping

| Legacy element | Data Capture | Notes |
|---|---|---|
| Record Lookup | `<recordLookups>` | Direct map; verify offline behavior |
| Record Create | `<recordCreates>` | Must follow the last screen (CUD-at-end) |
| Record Update | `<recordUpdates>` | Must follow the last screen (CUD-at-end) |
| Record Delete | `<recordDeletes>` | Must follow the last screen (CUD-at-end) |
| Decision | `<decisions>` | Direct map; review cross-screen routing |
| Loop | `<loops>` | Direct map |
| Assignment | `<assignments>` | Direct map |
| Action Call (Apex) | **BLOCKER** | DC forbids `<actionCalls>`/Apex; only `AGX_FLOW` actions. Convert to record lookups |
| Subflow Call | **BLOCKER** | DC can only call other DC flows and subflows cannot contain CUD; inline or convert |
| Formula | `<assignments>` or Decision | Limited DisplayText formula support at DC runtime; pre-calculate |
| Fault path | **Not supported** | Fault connectors stripped; `$Flow.FaultMessage` blocked |

These are the capability-level gaps returned by
`fsm_dc_catalog.capability_gaps()` and surfaced per-flow by `analyze_flow.py`.

## Visibility rules

| Legacy pattern | Data Capture | Migration notes |
|---|---|---|
| Simple field visibility | `<visibilityRule>` | Direct map; same XML structure |
| Complex formula visibility | `<visibilityRule>` | Review formula; DC runtime support is limited |
| Cross-screen visibility | Not directly supported | Redesign with decision-based routing |

## Choice set patterns

### Legacy: picklist with static choices

```xml
<choices>
    <name>choice_Yes</name>
    <choiceText>Yes</choiceText>
    <dataType>String</dataType>
    <value><stringValue>Yes</stringValue></value>
</choices>
```

### Data Capture equivalent

In spec JSON:
```json
{
  "fieldType": "Picklist",
  "choices": ["Yes", "No", "Maybe"]
}
```

Converter auto-generates `<choices>` blocks with deduplication.

### Legacy: dynamic choice set (record-backed)

```xml
<dynamicChoiceSets>
    <name>AssetChoices</name>
    <object>Asset</object>
    <displayField>Name</displayField>
    <valueField>Id</valueField>
</dynamicChoiceSets>
```

Data Capture supports `dynamicChoiceSets` with the same structure. Converter
preserves these but flags for offline-priming verification.

## Input parameter mapping

| Legacy parameter | DC parameter | Notes |
|---|---|---|
| `label` | `label` | Direct map for ComponentInstance fields |
| `required` | Field-level `<isRequired>` **and** a `required` inputParameter | `ComponentInstance` fields read required-ness from the inputParameter at DC runtime, not `<isRequired>` alone — transformer emits both. Exception: `dcCheckbox`/`dcToggle` don't expose a `required` input attribute; only `<isRequired>` is set for those. |
| `placeholder` | *(not supported)* | Bake into label text |
| `disabled` / `readOnly` | `isDisabled` / `isReadonly` | Available on some DC components |
| `helpText` | *(not supported)* | Bake into label or use DisplayText |
| `min` / `max` (Counter) | `min` / `max` | Direct map for `dcCounter` |
| `minDate` / `maxDate` | `minDate` / `maxDate` | Direct map for `dcDate` / `dcDateTime` |

## Common migration pitfalls

### 1. Apex dependency

**Legacy:** Flow calls Apex to compute pricing, validate inventory, etc.
**Migration:** DC flows are offline-first and cannot call Apex at runtime.
**Fix:** Convert Apex logic to record lookups, or gate the flow behind an online detector and degrade gracefully.

### 2. AutoLaunched subflows

**Legacy:** Flow calls an AutoLaunched subflow for reusable logic.
**Migration:** DC can only call other DC flows (`processType=DataCaptureFlow`), and subflows cannot contain CUD.
**Fix:** Inline the subflow logic or convert the subflow to DC format.

### 3. Cross-screen formula references

**Legacy:** Screen 3's DisplayText references fields from Screen 1 via formula.
**Migration:** DC has limited formula support in DisplayText.
**Fix:** Use `<assignments>` between screens to pre-calculate values into variables.

### 4. Custom components (`ComponentInstance`)

**Legacy:** Custom LWC (`c:*`) or non-whitelisted `lightning:*` component embedded in a `ComponentInstance` field.
**Migration:** No custom component extension points in DC.
**Fix:** Rebuild with native DC components or flag as incompatible.

### 5. Action buttons (`PlainButtons`)

**Legacy:** `PlainButtons` field drives in-screen navigation or actions.
**Migration:** DC has no user-facing action buttons (only `AGX_FLOW`).
**Fix:** Redesign the interaction; there is no direct migration path.

## Validation checklist

After migration, verify:

- [ ] All screens render
- [ ] All field types display correctly
- [ ] Required validation fires
- [ ] Conditional visibility works
- [ ] Choices populate (picklists, radios, checkboxes)
- [ ] Lookups search the correct object
- [ ] File-upload components accept input
- [ ] Record creates/updates succeed
- [ ] Loops iterate correctly
- [ ] Decisions route to correct next steps
- [ ] Offline behavior: drafts queue when airplane mode on
- [ ] Form appears in FSL Mobile "Forms" tab

## Conversion confidence levels

### GREEN (high confidence, automated)

- Simple data-entry forms
- Standard `InputField` types (text, number, date, boolean)
- Static picklists (`DropdownBox`) and radio groups (`RadioButtons`)
- File upload via `forceContent:fileUpload`
- Single record create at end
- No Apex, no custom components

### YELLOW (medium confidence, requires review)

- Visibility rules with formulas
- Decision-based routing
- Dynamic choice sets (requires offline-priming verification)
- Record updates with conditional logic
- `MultiSelectPicklist` / `RadioButtonGroup` rebuilt as `dcCbGroup` / `dcRbGroup`

### RED (low confidence, manual redesign)

- Custom `ComponentInstance` components (`c:*`, non-whitelisted `lightning:*`)
- `PlainButtons` action buttons
- Apex callouts
- AutoLaunched subflows
- Complex nested decisions
- Cross-screen formula dependencies in DisplayText
- `DisplayRichText`

## Testing strategy

1. **Desktop first:** Open migrated flow via `<instanceUrl>/flow/<FlowApiName>_v2`, complete the form end-to-end
2. **Offline priming:** Verify Briefcase includes all objects/fields the flow touches
3. **Mobile render:** Attach to a test record, open on FSL Mobile device
4. **Offline mode:** Airplane mode + complete form + verify draft queues
5. **Data integrity:** Compare output records from legacy vs. migrated flow
6. **Edge cases:** Test all branches, visibility conditions, validation rules

## Rollback procedure

If migrated flow has issues:

1. Keep legacy flow active (don't deactivate)
2. Remove `DynamicDataCapture` attachment for migrated flow
3. Iterate on spec, rebuild, redeploy as `_v3`, `_v4`, etc.
4. Once validated, deactivate legacy flow and clean up test versions
