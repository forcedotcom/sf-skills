# Converter → Builder integration contract

This is the authoritative contract between the two scripts that form the
migration pipeline:

```text
legacy Digital Forms XML
   └─▶ scripts/convert_to_dc_spec.py   (producer)
          └─▶ spec JSON
                 └─▶ scripts/vendor/build_flow.py   (consumer)
                        └─▶ .flow-meta.xml (DataCaptureFlow)
```

Before `collapse_gating_decisions`, the converter runs `normalize_inverted_gates`,
which rewrites inverted-shape gates (default branch shows the gated field) into
equivalent positive gates by negating the rule condition and swapping connectors.
Collapse then handles them unchanged (field or section). Inverted gates whose
condition uses a non-invertible operator or custom logic are left flagged (see the
capability catalog).

`build_flow.py` (`parse_spec`) is the source of truth for the JSON shape.
`convert_to_dc_spec.py` MUST emit exactly this shape.

> **History:** an earlier converter emitted `screens` as a *list* of
> `{title, fields:[{name, label, fieldType, required, choices}]}`, while the
> builder consumes `screens` as a *dict* of `{ScreenName: [{fieldName,
> fieldLabel, isRequired, options, visibility}]}`. Piping one into the other
> raised `ValueError: spec must have a non-empty 'screens' object` and produced
> no output. This doc + the smoke test exist to prevent that regression.

## Top-level spec object

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `formTitle` | string | yes | Flow label / interview label. |
| `formType` | string | no | Free text; converter sets `"DataCaptureFlow"`. |
| `screens` | **object (dict)** | yes | Keyed by screen name → list of field objects. Must be non-empty. |
| `decisions` | list | no | Pre-CUD screen-routing decisions. Each: `{name, label, defaultConnector, defaultLabel, rules:[{name, label, conditionLogic, conditions:[{leftValueReference, operator, rightValue}], connectsTo}]}`. Emitted by the converter (WI-6a) **only when the decision passes the deployability gate** — every target resolves to an element 6a actually builds (another surviving decision) AND the decision is reachable from a screen connector. Decisions that fail either bar are routed to `_decisionFlags`, never emitted, so no `<decisions>` element ever carries a dangling `<targetReference>`. |
| `_screenConnectors` | object | no | `{screen_key: target_api_name}` — a source screen's outgoing connector, **filtered to targets that are emitted decisions**. Connectors whose target is not an emitted decision are dropped so the screen falls through sequentially rather than dangling. Full connector-graph wiring to renamed `Screen_` api-names and to assignments/lookups is deferred to WI-6b/6c. |
| `_decisionFlags` | list | no | `{name, reason}` for **decisions** the routing gate did not emit. Two reason families: (1) **Decision→CUD** — routes directly to a CUD element (forbidden by the CUD-at-end rule); (2) **target not yet wired** — routes to screens/assignments/lookups 6a does not build, or is unreachable — deferred to WI-6b/6c. Decision-routing only; structural ceilings live in `_ceilingFlags`. Migration annotation only. |
| `_ceilingFlags` | list | no | `{name, reason}` for **structural** DC deploy-time ceilings the converter cannot translate (WI-7), in document order: (1) any element reachable only after a CUD node (CUD-at-end rule); (2) any element carrying a `<faultConnector>`; (3) any `<loops>`. Kept SEPARATE from `_decisionFlags` because the same element name can legitimately appear in both surfaces (a decision that is both unwired and post-CUD), so a single name-keyed list would collide. Migration annotation only. |
| `_cudAnalysis` | object | no | WI-8 ordinal CUD-placement analysis. `{consolidated:[{node,op,from,to}], manualRestructure:[{node,op,position,reason,blockers}], hasMidFlowCud:bool}`. Present only when the flow has ≥1 CUD element. `consolidated` lists safe record-creates the converter moved to `postScreen`; `manualRestructure` lists CUD needing hand-restructuring (unsafe, or safe update/delete with no `postScreen` emission path). Migration annotation only. |
| `_collapsedDecisions` | list | no | `{decision, field?, section?, fields?, clearedRequired?}` for gates the converter collapsed into visibility. Field-level collapses (WI-6b) populate `field`; section-level collapses (WI-6c) populate `section` and `fields` (the list of field api-names the section contained) and `clearedRequired` (field names whose required flag was unset because they became conditionally visible). Migration annotation only. |
| `_incompleteMigration` | list | no | Unsupported elements from the source flow that have no Data Capture equivalent. Each: `{type, name, reason}` where `type ∈ {apex, subflow, faultPath, customComponent, unknownField}`. Present **only when** the source flow has ≥1 unsupported element; the key is omitted entirely (not emitted as an empty list) for clean flows. Ordering: flow-level (`apex`, `subflow`, `faultPath`) in document order, then field-level (`customComponent`, `unknownField`) in screen/field document order — deterministic. See "Incomplete Migration Marker" section below. |
| `postScreen` | object | no | End-of-flow automation (decisions/lookups/loop/creates). As of WI-8, `_automationNote` fires only when mid-flow CUD is detected and its body is ordering-based (points at `_cudAnalysis`); the former count-based note is removed. Safe record-creates are emitted into `postScreen.recordCreates`. |
| `_migrationSummary` | list of strings | no | Human-readable rollup, one line per migration action: section/field collapses, cleared-required fields (WI-6c), and WI-7 ceiling flags (post-CUD / fault / loop). The human-facing mirror of the machine keys `_collapsedDecisions` and `_ceilingFlags`. Only present when at least one action occurred. Migration annotation only. |

Any key beginning with `_` (e.g. `_automationNote`, `_migrationNote`, `_incompleteMigration`, `_screenConnectors`, `_decisionFlags`) is a
migration annotation. As of WI-8, `_automationNote` fires only when mid-flow CUD is detected and its body is ordering-based (points at `_cudAnalysis`); the former count-based note is removed. Safe record-creates are emitted into `postScreen.recordCreates`. The builder ignores unknown keys, so annotations pass
through harmlessly.

## `screens` — dict, not list

- **Key**: the screen name/label as a string (e.g. `"Asset Details"`). It does
  not need to be pre-sanitized — the builder derives the display label via
  `humanize_screen_key` and produces the screen api-name by running the key
  through `coerce_api_name` with a `Screen_` prefix (so `"Asset Details"` →
  api-name `Screen_Asset_Details`, label "Asset Details"). Keys must be unique
  within the `screens` dict.
- **Value**: a **non-empty** list of field objects or **section-sentinel dicts**. The builder raises if any
  screen maps to an empty list, so the converter drops screens that yield no
  convertible fields rather than emit an empty one. Section-sentinels (WI-6c) are expressed as `{"section": label, "visibility"?: {...}, "fields": [...]}` for self-contained / nestable sections, or `{"section": label}` (no `fields` key) for legacy inline openers.

## Field object

| Key | Type | Required | Emitted by converter | Notes |
|-----|------|----------|----------------------|-------|
| `fieldName` | string | yes | yes | Source field api-name. Builder re-sanitizes and uniquifies it. |
| `fieldLabel` | string | yes | yes | Display label. |
| `fieldType` | string | yes | yes | One of the builder's `TYPE_MAP` keys (see below). Unknown types fall back to `ShortText` with a `[Unknown type: X]` label prefix. |
| `isRequired` | bool | yes | yes | Coerced with `bool()` by the builder. |
| `options` | list[string] | for choice types | when choices present | Choice display values for `Picklist` / `Radio` / `CheckboxGroup` / `Matrix`. |
| `visibility` | object | no | yes (6b/6c) | `{ field, operator, value }`; `field` must reference a choice field, `value` one of its options. Field-level visibility collapse delivered in WI-6b. A `visibility` key on a **section sentinel** (WI-6c) gates the entire section (builder emits a `<visibilityRule>` on the `RegionContainer` field). Note: legacy FSM has no component-level visibility — all conditionality arrives via the top-level `decisions` list (decision routing delivered in WI-6a). |
| `defaultValue` | string/number/bool | no | not yet | Pre-fill / DisplayText body. |
| `_migrationNote` | string | no | yes (when needed) | Migration annotation; ignored by builder. |

Repeater/Matrix/Counter/Lookup/FileView carry extra keys (`repeaterFields`,
`matrixRows`, `min`/`max`/`value`, `lookupObject`, `fileName`) — see
`field-types.md` in the Data Capture form deployer skill. The converter does not emit
these yet.

### Sections & nesting

Sections (WI-6c) are expressed as **section-sentinel dicts** within a screen's field list. Two forms exist:

- **Self-contained / nestable**: `{"section": label, "visibility"?: {...}, "fields": [...]}` — the `fields` array contains the section's child fields (and may itself contain nested section sentinels, up to `MAX_SECTION_DEPTH = 5`). The builder emits a `RegionContainer` field wrapping the children. If `visibility` is present, the builder emits a `<visibilityRule>` on the `RegionContainer`.
- **Legacy inline opener**: `{"section": label}` (no `fields` key) — the legacy converter emitted this form; it opens a section that extends to the next section sentinel or end-of-screen. Not nested. The current converter (WI-6c) emits only the self-contained form.

**Cascade rule**: each section carries only its own `visibility` conditions. The Data Capture runtime auto-hides children when a parent section is hidden, so the converter does not need to propagate parent conditions downward into child field visibility rules.

## Decision conditions

Each decision in the top-level `decisions` list contains `rules`, and each rule contains `conditions`. Condition structure:

| Key | Type | Notes |
|-----|------|-------|
| `leftValueReference` | string | Field api-name or merge-field reference. |
| `operator` | string | Flow operator (e.g. `EqualTo`, `NotEqualTo`, `IsNull`, `GreaterThan`). Defaults to `EqualTo` if omitted. |
| `rightValue` | object | Typed single-key dict: one of `{booleanValue: bool}`, `{numberValue: float}`, `{stringValue: string}`, or `{elementReference: string}`. May be omitted for null-check operators. |

The `conditionLogic` field (string) is copied verbatim from the source Flow decision, including custom logic strings like `3 and (1 OR 2) and 4`. Defaults to `"and"` if omitted.

## Field-type vocabulary

`fieldType` values MUST be keys in `build_flow.py`'s `TYPE_MAP`. As of this
writing:

```text
ShortText, LongText, Name, Email, Phone, Numeric, Counter, Date, DateTime,
Checkbox, Toggle, Picklist, Radio, CheckboxGroup, DisplayText, Repeater,
Signature, UploadFile, UploadImage, Address, Matrix, Images, Lookup, FileView
```

The converter maps legacy `extensionName`s to a subset of these (see
[component-mapping.md](component-mapping.md)). Any legacy component with no mapping is
emitted as `ShortText` with a `_migrationNote`.

## Renamed keys (legacy converter → current contract)

If you are updating older code or docs, these are the renames that closed the
contract gap:

| Old converter key | Current contract key |
|-------------------|----------------------|
| `screens` (list) | `screens` (dict, keyed by screen name) |
| screen `title` | (dropped — label derived from the dict key) |
| screen `fields` | (dropped — the dict value *is* the field list) |
| `name` | `fieldName` |
| `label` | `fieldLabel` |
| `required` | `isRequired` |
| `choices` | `options` |

## Incomplete Migration Marker

When the converter encounters source flow elements that have no Data Capture equivalent, it emits `_incompleteMigration`: a top-level list of `{type, name, reason}` dictionaries. This key is present **only when** the source flow has ≥1 unsupported element; it is omitted entirely (not emitted as an empty list) for clean flows.

### Type vocabulary

`type` is a closed set with exactly five values:

| Type | Meaning | Example |
|------|---------|---------|
| `apex` | Apex action call or invocable action | EmailAlert, Apex class invocation |
| `subflow` | Subflow invocation | DataCaptureFlow can call other DC subflows, but this flags manual review |
| `faultPath` | Fault connector (error path) | DC has no fault paths; error handling is stripped |
| `customComponent` | Custom Lightning component in a field slot | Non-runtime_service_fieldservice component |
| `unknownField` | Field with no recognized type mapping | Unrecognized extensionName or fieldType |

### Ordering

The list is deterministic:
1. **Flow-level** (`apex`, `subflow`, `faultPath`) in source-document order (from `detect_unsupported_elements`)
2. **Field-level** (`customComponent`, `unknownField`) in screen/field document order (collected during the screen loop)

### Builder behavior

`build_flow.py` reads `_incompleteMigration` via `parse_spec` into `FormSpec.incomplete_migration` (a list). When present and non-empty, `build_xml` renders ONE `<!-- INCOMPLETE MIGRATION ... -->` comment block between the `<?xml version="1.0"?>` declaration and the `<Flow>` opening tag. Each entry is formatted as:

```text
  - [type] name: reason
```

If the key is absent, no comment is emitted. (In practice the converter omits the key rather than emitting an empty list, but the builder tolerates an empty list too.)

### Coexistence with other annotations

`_incompleteMigration` coexists with `_subflowNote`, `_automationNote`, and per-field `_migrationNote`. These annotations were **not consolidated** — each serves a distinct purpose:
- `_incompleteMigration`: top-level spec key listing all unsupported elements → XML comment block
- `_subflowNote` / `_automationNote`: converter stdout warnings about CUD/subflow review needs
- `_migrationNote`: per-field note embedded in the spec field dict (not promoted to `_incompleteMigration` unless the field is also unsupported)

A subflow is intentionally surfaced by **both** mechanisms: it is flagged in `_incompleteMigration` (type `subflow`) **and** may still trigger a `_subflowNote` stdout warning. The two are independent and were deliberately left un-deduplicated (consolidation is out of scope for WI-7).

### Unsupported field placeholder behavior

Unsupported field slots (those with `meta['unsupported'] = True`) are emitted as **read-only `DisplayText` placeholders** with the `fieldLabel` set to `[UNSUPPORTED: <fieldName> — <reason>]` (em-dash U+2014 separator). They are NOT emitted as silent `ShortText` inputs (the WI-7 silent-downgrade behavior was removed). The placeholder ensures the unsupported field is visible in the built XML and flagged for manual attention.

## Verifying the contract

Run `scripts/convert_to_dc_spec.py` against `assets/sample-legacy-flow.flow-meta.xml`, then
`scripts/vendor/build_flow.py` against the resulting spec, and confirm the output XML has a
non-empty `screens` section. If it fails, the converter output and builder input have drifted —
reconcile against `build_flow.parse_spec`, which remains the source of truth.
