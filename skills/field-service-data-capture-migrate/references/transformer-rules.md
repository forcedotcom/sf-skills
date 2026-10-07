# What the transformer does automatically

`transform_flow.py` is a direct XML-to-XML transformer — no spec generation, no intermediate files. It makes one pass through the flow and applies all transformations below.

## Field type conversion (complete mapping)

| Legacy fieldType | Legacy dataType / extensionName | → DC fieldType | → extensionName |
|---|---|---|---|
| `InputField` | `Boolean` | `ComponentInstance` | `dcCheckbox` |
| `InputField` | `String` | `ComponentInstance` | `dcTextInput` |
| `InputField` | `Number` / `Double` / `Currency` | `ComponentInstance` | `dcNumeric` |
| `InputField` | `Date` | `ComponentInstance` | `dcDate` |
| `InputField` | `DateTime` | `ComponentInstance` | `dcDateTime` |
| `InputField` | `Email` | `ComponentInstance` | `dcEmail` |
| `InputField` | `Phone` | `ComponentInstance` | `dcPhone` |
| `InputField` | `TextArea` / `LongTextArea` | `ComponentInstance` | `dcLongText` |
| `InputField` | `Picklist` | `ComponentChoice` | `dcPicklist` (supports single OR multiple selection via configuration) |
| `InputField` | `MultiselectPicklist` | `ComponentMultiChoice` | `dcCbGroup` |
| `InputField` | `Name` | `ComponentInstance` | `dcName` |
| `InputField` | `Toggle` | `ComponentInstance` | `dcToggle` |
| `InputField` | `Address` | `ComponentInstance` | `dcAddress` |
| `InputField` | `Lookup` | `ComponentInstance` | `dcLookup` |
| `InputField` | `Counter` | `ComponentInstance` | `dcCounter` |
| `InputField` | `Matrix` | `ComponentMultiChoice` | `dcMatrix` |
| `DropdownBox` | — | `ComponentChoice` | `dcPicklist` |
| `RadioButtons` | — | `ComponentChoice` | `dcRbGroup` |
| `RadioButtonGroup` | — | `ComponentChoice` | `dcRbGroup` |
| `MultiSelectCheckboxes` | — | `ComponentMultiChoice` | `dcCbGroup` |
| `MultiSelectPicklist` | — | `ComponentMultiChoice` | `dcCbGroup` |
| `LargeTextArea` | — | `ComponentInstance` | `dcLongText` |
| `forceContent:fileView` | — | `ComponentInstance` | `dcFileView` |
| `forceContent:fileUpload` | — | `ComponentInstance` | `dcUpFile` |
| `forceContent:imageUpload` | — | `ComponentInstance` | `dcUpImage` |
| `Range` (slider) | — | **SKIPPED — not valid in DC** | Flag for manual replacement with `dcNumeric` or `dcCounter` |
| `DisplayText` | — | `DisplayText` | *(pass-through)* |
| `Repeater` | — | `Repeater` | *(pass-through)* |
| Already `runtime_service_fieldservice:dc*` | — | *(pass-through, cleaned)* | — |

## Required XML injected on every converted ComponentInstance field

Every `dc*` `ComponentInstance` field gets these elements injected by the transformer:

```xml
<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>
<storeOutputAutomatically>true</storeOutputAutomatically>
<styleProperties>
    <verticalAlignment><stringValue>top</stringValue></verticalAlignment>
    <width><stringValue>12</stringValue></width>
</styleProperties>
```

**Exception:** `<fieldType>Repeater</fieldType>` must NOT get `storeOutputAutomatically` — the Repeater always outputs via `.AllItems` and the element causes a deploy error if present on the Repeater itself (nested fields inside the Repeater still get it).

## Label placement rules by fieldType

| fieldType | Label location | Note |
|---|---|---|
| `ComponentInstance` (`dc*`) | `<inputParameters><name>label</name>...` | `<fieldText>` is stripped if present; missing `label` inputParameter causes deploy error |
| `ComponentChoice` / `ComponentMultiChoice` | `<fieldText>` | Direct content |
| `DisplayText` | `<fieldText>` | HTML content |
| `RegionContainer` / `Region` (section) | `<fieldText>` | Section header |

## CUD-at-end graph restructuring

DataCaptureFlow requires all record creates/updates/deletes after the last screen. The transformer detects violations by walking the execution graph and fixes them with 4 patterns (up to 50 convergence iterations):

**Analysis/converter path (WI-8):** `convert_to_dc_spec.py` and `analyze_flow.py` perform
ordinal CUD-placement analysis (`scripts/cud_analysis.py`): each create/update/delete is
classified by execution position as `compliant`, `safe_consolidate`, or `unsafe_manual`.
Safe record-creates are auto-consolidated into `postScreen.recordCreates` (rendered after
the last screen); unsafe CUD and safe updates/deletes (no auto-move path) get precise
manual-restructure guidance in `_cudAnalysis` / `_migrationSummary`. This is distinct from
the `transform_flow.py` restructurer, which rewrites the flow XML connectors in place.

- **Pattern A — CUD → Screen**: Moves the screen to before the CUD chain (converts "confirmation after save" to "confirm before save")
- **Pattern B — CUD → Lookup**: Hoists the lookup to before the first screen (pre-loads data before user sees the form)
- **Pattern C — CUD → Assignment**: Same as Pattern B
- **Pattern D — CUD → Decision**: Hoists the decision to before the first screen

**Functional impact of CUD restructuring:** In most flows, lookups that were originally after a screen are pre-screen in the original design anyway (they load context). Hoisting them doesn't change their results. **Check the warnings output** — if a warning says a hoisted lookup filters on a screen field value, that lookup will run with an empty value before the user fills in the screen. That flow needs manual redesign.

## Other automatic fixes

- `processType` → `DataCaptureFlow`
- `status` → `Draft` (always — the source's status, often `Active`, never leaks through; `deploy_flow.sh` also force-rewrites `<status>` to `Draft` at the deploy boundary, so this holds even for a hand-edited file. Activation is a manual admin action in the org UI after a clean dry-run and device testing — SKILL.md Step 8 — never scripted)
- `environments` → `Offline` (replaces `Default` or adds if missing)
- Sets `areMetricsLoggedToDataCloud` to `false` (required DC header; adds if missing, updates if present)
- Removes `<apiVersion>` (not valid in DC — causes deploy error if present)
- Removes `<constants>` (not allowed in DC)
- Removes `<actionCalls>` elements (not allowed in DC — use DisplayText for notifications)
- Strips fault connectors from all elements (not supported in DataCaptureFlow)
- Removes platform event `<recordCreates>` nodes (DC can't create non-UI entities like `AsgnResourceLocUpdateEvent`) — **side effect: those events will no longer fire**
- Removes `<outputAssignments>` from screen fields → replaced with `storeOutputAutomatically=true` + an injected `<assignments>` node to preserve variable bindings
- Strips invalid incoming `<inputParameters>`: `required`, `disabled`, `multiple`, `accept`, `helpText`, `placeholder` (not carried over as-is from the legacy field). `disabled`/`helpText`/`placeholder`/`multiple`/`accept` stay stripped (bake content into label text instead). `required` is different: it's re-added as a computed inputParameter (from `<isRequired>`) on most `ComponentInstance` fields, since the DC runtime reads required-ness from the inputParameter, not `<isRequired>`, for those — except `dcCheckbox`/`dcToggle`, which don't expose a `required` input attribute at all and get only `<isRequired>`
- Replaces `minimumDate`/`maximumDate` with `minDate`/`maxDate` on date fields
- Replaces `multiSelection` with `isMultiSelection` on Lookup fields
- Replaces `disabled`/`readOnly` with `isDisabled`/`isReadonly` (note lowercase `o`) on Lookup fields
- Replaces `recordIds` inputParameter with `recordIdCollection` on Lookup fields
- Removes `extensionName` from Repeater elements (only valid on nested fields inside a Repeater)
- Removes `min`/`max` inputParameters from `dcNumeric` fields (only valid on `dcCounter`)
- Fixes screen field references in downstream automation to use `{fieldName}.value` (DC accessor pattern)
- Removes `<defaultValue>` from `ComponentInstance` fields (DC uses `value` inputParameter instead)
- Removes `<dataType>` from `ComponentChoice` fields
- Removes dangling empty connectors left by restructuring
- Case-insensitive deduplication of `<variables>` — updates `isInput=true` on existing vars rather than adding duplicates
- Ensures required DC input variables: `recordId`, `parentRecordId`, `parentObjectType` (all String, `isInput=true`)
- Ensures required screen attributes: `allowFinish`, `showFooter`, `nextOrFinishButtonLabel`
- Reorders field child elements so all `<inputParameters>` are contiguous (fixes "Element inputParameters is duplicated" deploy error)
- Updates subflow `<flowName>` references to DC versions (appends `_DC` suffix; explicit overrides for known name mismatches)
- **Detects and warns** (does NOT auto-fix): Screen inside a loop — DC doesn't support screens in loops; requires Repeater redesign
- **Detects and warns** (does NOT auto-fix): `Range` slider fields — not valid in DataCaptureFlow; replace manually with `dcNumeric` or `dcCounter`
- **Detects and warns** (does NOT auto-fix): `isRequired=true` on fields behind a `visibilityRule` — required check fires even when field is hidden; mobile worker cannot proceed
- **Detects and warns** (does NOT auto-fix): complex formulas in `DisplayText` fields (`IF`, `CASE`, date math) — deploys fine but fails at mobile runtime

---

# Functional equivalence after migration

**What is preserved exactly:**
- All record lookups, creates, updates, deletes (just reordered to comply with DC constraint)
- All decisions, loops, assignments
- All screen fields and their labels
- All choice sets (picklists, radio groups, checkboxes)
- All visibility rules
- All variable definitions (deduplicated)
- All subflow calls (references updated to DC names)

**What changes behaviorally:**
- **Lookup execution order**: Lookups hoisted before the first screen now run before the user sees the form. Most lookups load context data (Work Order details, parent records) and are unaffected. Lookups that filter on screen input values will run with empty inputs — transformer flags these in warnings.
- **Platform events removed**: Any `recordCreates` targeting event objects (e.g. `AsgnResourceLocUpdateEvent`) are removed. Real-time dispatcher/Gantt events that were fired mid-flow will no longer fire. If this matters, replace with an Apex trigger or a separate AutoLaunched flow triggered by the record update.
- **Confirmation screens**: If the original flow showed a confirmation screen *after* saving a record (Pattern A), the DC version shows it *before*. The data is still saved — the order of user experience changes.
- **Constants replaced**: Flow constants are removed (DC doesn't support them). Downstream references to constants may need to be replaced with hardcoded values or variables.
