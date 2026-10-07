# FSM Flow ↔ Data Capture Capability-Parity Catalog

**Authoritative** capability-parity / functionality-gap catalog between Field
Service Mobile (FSM) Flow and Data Capture (DC) Flow. This document and its
executable twin — `scripts/fsm_dc_catalog.py` — are the single source of truth
for the migration skill's supported / unsupported decisions.

It is keyed on the **real FSM Flow component vocabulary** — the standard Flow
`FlowScreenFieldType` enum (`InputField`, `DropdownBox`, `RadioButtons`,
`MultiSelectCheckboxes`, `DisplayText`, …) — **not** Lightning component names.
A `lightning:*` / `forceContent:*` / `c:*` name only ever appears as the
`<extensionName>` inside a `ComponentInstance` field.

> **Why this rewrite exists (W-23364461):** the skill's earlier
> supported/unsupported decisions were made against Lightning component names
> (`lightning:input`, `lightning:fileUpload`, …) rather than the FSM Flow
> vocabulary the platform actually uses. That produced two concrete errors,
> corrected below.

---

## Source of truth & verification

Two inputs were reconciled:

1. The **assessment spreadsheet** — *FSM Flow vs Data Capture Flow component
   assessment*.
2. **Salesforce core code** (core-2206, 264 release line), which is
   authoritative where the two disagree.

Core evidence:

| Fact | Core location |
|---|---|
| FSM/DC screen-field vocabulary (`FlowScreenFieldType` enum) | `interaction/.../mdapi/FlowScreenField.java` |
| FSM's single allowed `ComponentInstance` extension = `forceContent:fileUpload` | `interaction/.../mdapi/validation/FieldServiceMobileFlowValidator.java` (`supportedLightningComponents`) |
| FSM field types are a **denylist** (blocks only `Component*`/`Region`/`RegionContainer`/`Repeater`/`ObjectProvided`; all native types allowed) | `FieldServiceMobileProcessTypeHandler.hook_isFlowScreenFieldTypeAllowed` |
| DC field types are an **allowlist** (`DisplayText`, `ComponentInstance`, `ComponentChoice`, `ComponentMultiChoice`, `RegionContainer`, `Region`, `Repeater`, `ObjectProvided`); `AGX_FLOW`-only actions; Offline-only | `interaction/.../mdapi/processtype/DataCaptureFlowProcessTypeHandler.java` |

> **Two different gates — don't conflate them.** FSM screen *field types* are
> governed by a denylist, so the full native vocabulary (`InputField`,
> `DropdownBox`, `RadioButtons`, `MultiSelectPicklist`, …) is a valid migration
> **source**. Separately, an FSM `ComponentInstance` field may embed exactly one
> whitelisted extension — `forceContent:fileUpload`. DC is the mirror image: it
> *allows only* the `Component*` field types and blocks the native ones. That
> asymmetry is why migration is a type **conversion** (`DropdownBox` →
> `ComponentChoice`+`dcPicklist`), not a pass-through.
| DC deploy-time ceilings (CUD-at-end, blocked globals, fault stub) | `reference/dc-conditional-logic-sources.md` (spike W-23363833) |

---

## Corrections vs. the assessment spreadsheet

The spreadsheet is correct on almost everything, but core code contradicts it on
two points that matter for migration decisions:

### 1. Signature is DC-only — FSM has **no** signature component (spreadsheet correct, earlier skill decision wrong)

Core exposes **no native FSM signature component**. `FieldServiceMobileFlowValidator`
hardcodes the only allowed screen extension as `forceContent:fileUpload` — there
is no signature entry anywhere in the FSM path. `dcSignature` is DataCaptureFlow-only.

**Consequence:** the earlier decision recorded in **WI-3 (W-23364096)** —
"file-upload **and signature** ARE supported Phase-1 migration targets" — is
**wrong on the signature half** and is reversed here. There is no FSM signature
source to migrate *from*, so there is nothing to emit as `dcSignature`. Any
downstream task to "implement signature emission" (WI-7 / W-23364093) should be
**reverted**.

### 2. File-upload is **NOT** DC-only — the spreadsheet is wrong here, and the earlier skill was wrong too

The spreadsheet lists File Upload as "DC only – file attachment" (no FSM
equivalent). Core disproves this: `FieldServiceMobileFlowValidator` explicitly
**allows** `forceContent:fileUpload` inside an FSM flow. So:

- FSM Flow **can** contain file upload — via the extension `forceContent:fileUpload`.
- That maps cleanly to DC's `dcUpFile`.
- The earlier skill was *also* wrong, for a different reason: it keyed this off
  `lightning:fileUpload`, which is not the extension FSM actually allows.

**Consequence:** file-upload **is** a supported migration target — the WI-3
"file-upload supported" conclusion stands — but the mapping must key off
`forceContent:fileUpload → dcUpFile`, never `lightning:fileUpload`.

---

## Class 1 — FSM components with a clean FSM → DC mapping

Keyed by the FSM `<fieldType>` (and, for `InputField`, the field's `<dataType>`;
for `ComponentInstance`, the `<extensionName>`).

| FSM fieldType | Discriminator | → DC fieldType | → extensionName |
|---|---|---|---|
| `InputField` | dataType `Boolean` | `ComponentInstance` | `dcCheckbox` — *(see discrepancy)* |
| `InputField` | dataType `String` | `ComponentInstance` | `dcTextInput` |
| `InputField` | dataType `Number`/`Double`/`Currency` | `ComponentInstance` | `dcNumeric` |
| `InputField` | dataType `Date` | `ComponentInstance` | `dcDate` |
| `InputField` | dataType `DateTime` | `ComponentInstance` | `dcDateTime` |
| `InputField` | dataType `Email` | `ComponentInstance` | `dcEmail` |
| `InputField` | dataType `Phone` | `ComponentInstance` | `dcPhone` |
| `InputField` | dataType `TextArea`/`LongTextArea` | `ComponentInstance` | `dcLongText` |
| `InputField` | dataType `Picklist` | `ComponentChoice` | `dcPicklist` |
| `InputField` | dataType `MultiselectPicklist` | `ComponentMultiChoice` | `dcCbGroup` |
| `DropdownBox` | — | `ComponentChoice` | `dcPicklist` |
| `RadioButtons` | — | `ComponentChoice` | `dcRbGroup` |
| `RadioButtonGroup` | — | `ComponentChoice` | `dcRbGroup` |
| `MultiSelectCheckboxes` | — | `ComponentMultiChoice` | `dcCbGroup` |
| `MultiSelectPicklist` | — | `ComponentMultiChoice` | `dcCbGroup` *(or `dcPicklist` multi-mode)* |
| `LargeTextArea` | — | `ComponentInstance` | `dcLongText` |
| `DisplayText` | — | `DisplayText` | *(pass-through)* |
| `ComponentInstance` | ext `forceContent:fileUpload` | `ComponentInstance` | `dcUpFile` |
| `ComponentInstance` | ext `forceContent:imageUpload` | `ComponentInstance` | `dcUpImage` |
| `ComponentInstance` | ext already `runtime_service_fieldservice:dc*` | *(pass-through, cleaned)* | — |

`DisplayText` is the only field type valid in **both** flow types.

## Class 2 — FSM components with **NO DC equivalent** (cannot auto-migrate)

The migration must **flag, never silently drop or downgrade** these.

| FSM fieldType | Why no DC path | Manual option |
|---|---|---|
| `PasswordField` | No DC password component | Capture as `dcTextInput` only if non-secret, else drop |
| `DisplayRichText` | No DC rich-text display | Downgrade to `DisplayText`; rich formatting lost |
| `PlainButtons` | **DC has no action buttons** (capability gap) | Remove or redesign — no migration path |
| `ComponentInstance` ext `runtime_industries_csv_dataimport:advCsv` ("**Advanced CSV Import**"), or `:impBeg` (beginner variant) | Industries CSV Data Import / DPE-backed bulk import; DC has no CSV/bulk-import screen component and uses a per-record form model | Rebuild the data-loading step outside the flow (Data Processing Engine) or drop it |
| `ComponentInstance` w/ any custom ext (`c:*`, `lightning:*` other than the whitelisted `forceContent:fileUpload`) | DC has no custom-component extension point | Rebuild with a native `dc*` component or flag as unmigratable |

> **"Advanced CSV Import" is real — and a gap.** It is a standard-shipped
> Lightning flow screen component (`runtime_industries_csv_dataimport:advCsv`,
> `<target>lightning__FlowScreen</target>`) that appears in the FSM flow builder
> palette when Industries CSV Data Import is enabled, so it can legitimately show
> up in an FSM source flow. It has no DC equivalent. The catalog names it
> explicitly (`KNOWN_UNSUPPORTED_EXTENSIONS` in `fsm_dc_catalog.py`) so the gap
> report says *what* it is rather than a generic "unknown component" (W-23364461).

> **Choice types are NOT gaps.** `MultiSelectPicklist`, `RadioButtonGroup`,
> `RadioButtons`, `DropdownBox`, and `MultiSelectCheckboxes` all have genuine DC
> equivalents (Class 1). DC expresses multi-select through the
> `ComponentMultiChoice` field type — `dcCbGroup`, or `dcPicklist` in multi mode
> (its meta declares both `allowSingleChoice` and `allowMultipleChoices`). An
> earlier version of this catalog wrongly listed `MultiSelectPicklist` and
> `RadioButtonGroup` as no-DC-equivalent; that was a false gap and is corrected
> here (W-23364461).

## Class 3 — DC-only components (no FSM source maps to them)

These exist only in Data Capture; nothing in a source FSM flow produces them.
Listed for completeness so the skill can explain what a migration *cannot*
generate.

| DC component | Notes |
|---|---|
| `dcSignature` | Signature capture — **FSM has no signature component** |
| `dcEmail` / `dcPhone` / `dcName` | Dedicated inputs (FSM approximates via `InputField`) |
| `dcAddress` | Address input (optional GPS) |
| `dcLookup` | Record lookup |
| `dcMatrix` | Matrix / grid input |
| `dcCounter` | Numeric stepper |
| `dcCheckbox` | Single checkbox — distinct from Boolean/Toggle (see discrepancy) |
| `dcFileView` | Read-only file/image viewer |
| `dcUpImage` | Image upload (dedicated component) |
| `Region` / `RegionContainer` | Layout regions — FSM disallows |
| `Repeater` | Native repeating section — FSM used Loop + screens |
| `ObjectProvided` | Object-provided fields — FSM disallows |

> **`dcImages` does not exist.** Image upload is `dcUpImage`; the read-only
> file/image viewer is `dcFileView`. (Correction to an earlier assumption.)

---

## Capability-level gaps (beyond individual components)

These are differences no per-component mapping can preserve. They are returned
by `fsm_dc_catalog.capability_gaps()` and surfaced per-flow by `analyze_flow.py`.

| Capability gap | Detail | Core evidence |
|---|---|---|
| **No actions / buttons** | DC has no user-facing action buttons. FSM's `PlainButtons` has no DC equivalent; the only invocable action DC permits is `AGX_FLOW`. | `DataCaptureFlowProcessTypeHandler`: `allowedScreenFieldTypes` omits `PlainButtons`; `allowedActionTypes = {AGX_FLOW}` |
| **Offline-only** | DC runs only in the Offline environment. Online-only behaviour cannot be preserved. | `hook_isEnvironmentAllowed` → Offline only |
| **No Apex / action calls** | DC forbids `<actionCalls>` and Apex data types. | action allowlist = `AGX_FLOW` only |
| **CUD only at end of flow** | All create/update/delete must follow the last screen. FSM allowed CUD mid-flow. | `DataCaptureFlowValidator` CUD-at-end BFS |
| **No fault paths** | Fault connectors unsupported; FSM fault handling is stripped. | empty `navigateToFault()` stub; blocked `$Flow.FaultMessage` |
| **Subflows: DC-type only, no CUD** | A DC flow can only call another DC flow, and subflows cannot contain CUD. | subflow-type check |
| **Inverted gate w/ non-invertible condition** | An inverted-shape gate (default branch shows the field, rule branch skips it) collapses by *negating* the rule condition. When the rule uses a non-invertible operator (`Contains`, `StartsWith`, `EndsWith` — no negated Flow operator) or a custom `conditionLogic` formula, it cannot collapse and stays a flagged decision. Expressing it would need formula-typed visibility. | Flow operator enum has no `DoesNotContain`/`NotStartsWith`/`NotEndsWith`; DC visibility is show-when-only with no per-condition `NOT`. |

---

## Known discrepancy — Boolean `InputField` target (`dcCheckbox` vs `dcToggle`)

The shipping transformer (`transform_flow.py`) maps `InputField`/`Boolean` →
`dcCheckbox`, and this catalog matches it so **catalog and code stay in sync**
(AC#5). The assessment spreadsheet instead recommends `dcToggle` for a Boolean
("Boolean/Toggle is `dcToggle`, **NOT** `dcCheckbox`; single Checkbox is a
distinct DC-only component").

Both `dcCheckbox` and `dcToggle` bind to a Boolean and deploy successfully — the
difference is UX (checkbox vs. toggle switch), not correctness. This is an
**unresolved product decision**, not a bug. If the mapping should change to
`dcToggle`, update `INPUTFIELD_BY_DATATYPE` in `fsm_dc_catalog.py` **and**
`FIELD_TYPE_MAP` in `transform_flow.py` together.

---

## How the catalog is consumed

- **`scripts/fsm_dc_catalog.py`** — `classify(field_type, data_type, extension_name)`
  returns `{status, dc_extension, dc_field_type, note}`; `capability_gaps()`
  returns the table above; `is_gap(status)` is the gap predicate.
- **`scripts/analyze_flow.py`** — classifies every screen field via the catalog
  and emits a **Data Capture Gap Report** per flow (feeds WI-7 / WI-10).
- **`scripts/transform_flow.py`** — the shipping transformer; its `FIELD_TYPE_MAP`
  is the same vocabulary and must stay in sync with this catalog.
- **`reference/component-mapping.md`** — points here as the source of truth.
