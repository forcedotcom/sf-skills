#!/usr/bin/env python3
"""
Authoritative FSM Flow <-> Data Capture capability-parity catalog.

This module is the single source of truth for the migration skill's decisions
about which Field Service Mobile (FSM) Flow screen components have a Data
Capture (DC) equivalent, which do not, and which DC components have no FSM
source at all. It is consumed by analyze_flow.py (gap reporting) and is the
data behind references/fsm-dc-capability-catalog.md. WI-7/WI-10 import it too.

KEYED ON THE REAL FSM VOCABULARY
--------------------------------
FSM Flow screen fields use the standard Flow `FlowScreenFieldType` enum
(`InputField`, `DropdownBox`, `RadioButtons`, `MultiSelectCheckboxes`,
`DisplayText`, `LargeTextArea`, `PasswordField`, ...) — NOT Lightning component
names. A `lightning:*` / `forceContent:*` / `c:*` name only ever appears as the
`<extensionName>` INSIDE a `ComponentInstance` field. This catalog therefore
classifies by `fieldType` first and only inspects `extensionName` for
`ComponentInstance`.

VERIFIED AGAINST CORE (core-2206 / 264 release line)
----------------------------------------------------
- FSM vocabulary: `FlowScreenField.FlowScreenFieldType` enum
    core/interaction/submodules/udd/java/src/interaction/definition/mdapi/FlowScreenField.java
- FSM screen fields use a DENYLIST (not an allowlist): hook_isFlowScreenFieldTypeAllowed
  blocks only Component*/Region/RegionContainer/Repeater/ObjectProvided, so the
  full native vocabulary (InputField, DropdownBox, RadioButtons, MultiSelectPicklist,
  MultiSelectCheckboxes, ...) is a valid migration SOURCE:
    .../mdapi/processtype/FieldServiceMobileProcessTypeHandler.java
  Separately, an FSM ComponentInstance may embed exactly one whitelisted extension:
    .../mdapi/validation/FieldServiceMobileFlowValidator.java
      -> supportedLightningComponents = ImmutableSet.of("forceContent:fileUpload")
- DC-allowed screen fields + actions:
    .../mdapi/processtype/DataCaptureFlowProcessTypeHandler.java
      allowedScreenFieldTypes = {DisplayText, ComponentInstance, ComponentChoice,
        ComponentMultiChoice, RegionContainer, Region, Repeater, ObjectProvided}
      allowedActionTypes = {AGX_FLOW}   -> no user-facing action buttons
      hook_isEnvironmentAllowed -> Offline only

TWO CORRECTIONS THIS CATALOG MAKES (see reference doc for the full write-up)
----------------------------------------------------------------------------
1. SIGNATURE is DC-only. Core exposes NO native FSM signature component. The
   earlier decision (WI-3 / W-23364096) that "signature is a supported FSM->DC
   migration target" was WRONG and is reversed here.
2. FILE-UPLOAD is NOT DC-only (the assessment spreadsheet is wrong on this).
   FSM allows exactly one screen extension — `forceContent:fileUpload` — and it
   maps cleanly to `dcUpFile`. The migration keys off that extension name, never
   the `lightning:fileUpload` name the old skill assumed.
"""

from typing import Dict, List, Optional, Tuple

# DC screen-field categories (how the target renders in DataCaptureFlow XML).
COMPONENT_INSTANCE = "ComponentInstance"
COMPONENT_CHOICE = "ComponentChoice"
COMPONENT_MULTI_CHOICE = "ComponentMultiChoice"

DC_NS = "runtime_service_fieldservice:"

# Classification status values.
MAPPED = "mapped"                       # clean FSM -> DC conversion exists
NO_DC_EQUIVALENT = "no-DC-equivalent"   # FSM component with nothing on the DC side
DC_ONLY = "DC-only"                     # DC component with no FSM source (reference)
UNKNOWN = "unknown"                     # not a recognised FSM screen field


# ──────────────────────────────────────────────────────────────────────────
# 1. FSM fieldType (standalone, no extensionName) -> DC target
#    A `dc_target` of None means "no DC equivalent"; the field cannot migrate.
# ──────────────────────────────────────────────────────────────────────────

# (dc_extension, dc_fieldType) for InputField, resolved by the field's dataType.
# Matches transform_flow.py FIELD_TYPE_MAP exactly (catalog <-> transformer must
# agree). NOTE the Boolean discrepancy documented at the bottom of this file.
INPUTFIELD_BY_DATATYPE: Dict[str, Tuple[str, str]] = {
    "Boolean":             ("dcCheckbox",  COMPONENT_INSTANCE),
    "String":              ("dcTextInput", COMPONENT_INSTANCE),
    "Number":              ("dcNumeric",   COMPONENT_INSTANCE),
    "Double":              ("dcNumeric",   COMPONENT_INSTANCE),
    "Currency":            ("dcNumeric",   COMPONENT_INSTANCE),
    "Date":                ("dcDate",      COMPONENT_INSTANCE),
    "DateTime":            ("dcDateTime",  COMPONENT_INSTANCE),
    "Email":               ("dcEmail",     COMPONENT_INSTANCE),
    "Phone":               ("dcPhone",     COMPONENT_INSTANCE),
    "TextArea":            ("dcLongText",  COMPONENT_INSTANCE),
    "LongTextArea":        ("dcLongText",  COMPONENT_INSTANCE),
    "Picklist":            ("dcPicklist",  COMPONENT_CHOICE),
    "MultiselectPicklist": ("dcCbGroup",   COMPONENT_MULTI_CHOICE),
    "Name":                ("dcName",      COMPONENT_INSTANCE),
    "Toggle":              ("dcToggle",    COMPONENT_INSTANCE),
    "Address":             ("dcAddress",   COMPONENT_INSTANCE),
    "Lookup":              ("dcLookup",    COMPONENT_INSTANCE),
    "Counter":             ("dcCounter",   COMPONENT_INSTANCE),
    "Matrix":              ("dcMatrix",    COMPONENT_MULTI_CHOICE),
}
# InputField with an unrecognised/absent dataType falls back to a text input.
INPUTFIELD_DEFAULT = ("dcTextInput", COMPONENT_INSTANCE)

# Standalone FSM screen field types (no extensionName involved).
# value = (status, dc_extension_or_None, dc_fieldType_or_None, note)
FSM_FIELDTYPE_CATALOG: Dict[str, Tuple[str, Optional[str], Optional[str], str]] = {
    # ── Mapped: clean FSM -> DC path ──────────────────────────────────────
    "DisplayText":           (MAPPED, None, "DisplayText",
                              "Only field type valid in BOTH flow types; passes through. "
                              "Complex formulas fail at DC mobile runtime — pre-calculate."),
    "LargeTextArea":         (MAPPED, "dcLongText", COMPONENT_INSTANCE, ""),
    "DropdownBox":           (MAPPED, "dcPicklist", COMPONENT_CHOICE, ""),
    "RadioButtons":          (MAPPED, "dcRbGroup", COMPONENT_CHOICE, ""),
    "MultiSelectCheckboxes": (MAPPED, "dcCbGroup", COMPONENT_MULTI_CHOICE, ""),
    "MultiSelectPicklist":   (MAPPED, "dcCbGroup", COMPONENT_MULTI_CHOICE,
                              "Multi-select choice field. Maps to dcCbGroup "
                              "(ComponentMultiChoice), matching transform_flow.py. "
                              "dcPicklist in multi mode is a closer-UX alternative "
                              "(also ComponentMultiChoice)."),
    "RadioButtonGroup":      (MAPPED, "dcRbGroup", COMPONENT_CHOICE,
                              "Single-select radio (grouped/segmented rendering); "
                              "same DC target as RadioButtons. Note: FSM reports the "
                              "RadioButtonGroup *feature* as unsupported, so it is "
                              "uncommon in genuine FSM sources."),
    # InputField is resolved separately by dataType (see classify()).
    "InputField":            (MAPPED, None, COMPONENT_INSTANCE,
                              "Resolved by dataType to a dc* component."),

    # ── No DC equivalent: FSM-only, cannot migrate automatically ──────────
    "PasswordField":   (NO_DC_EQUIVALENT, None, None,
                        "No DC password component. Rare in field forms; capture as "
                        "dcTextInput only if the value is non-secret, else drop."),
    "DisplayRichText": (NO_DC_EQUIVALENT, None, None,
                        "No DC rich-text display. Downgrade to DisplayText (plain/basic "
                        "HTML) manually; rich formatting is lost."),
    "PlainButtons":    (NO_DC_EQUIVALENT, None, None,
                        "CAPABILITY GAP: Data Capture has no user-facing action buttons "
                        "(only AGX_FLOW actions). No migration path — remove or redesign."),
}

# ──────────────────────────────────────────────────────────────────────────
# 2. ComponentInstance extensionName -> DC target
#    Only `forceContent:fileUpload` is natively allowed in an FSM flow (core
#    whitelist). Everything else is a custom/unsupported component.
# ──────────────────────────────────────────────────────────────────────────

# Extensions with a real FSM -> DC migration path.
EXTENSION_CATALOG: Dict[str, Tuple[str, str, str, str]] = {
    # (status, dc_extension, dc_fieldType, note)
    "forceContent:fileUpload": (MAPPED, "dcUpFile", COMPONENT_INSTANCE,
                                "The ONLY screen extension core allows inside an FSM "
                                "flow. Maps cleanly to dcUpFile."),
    # imageUpload is handled by transform_flow.py; core only whitelists fileUpload
    # for FSM, so a real FSM source rarely contains it, but map it if present.
    "forceContent:imageUpload": (MAPPED, "dcUpImage", COMPONENT_INSTANCE,
                                "Maps to dcUpImage. Note: core's FSM whitelist only "
                                "lists forceContent:fileUpload, so imageUpload is "
                                "uncommon in genuine FSM sources."),
}

# Field-already-DC: an FSM flow that was partially hand-migrated may already
# carry runtime_service_fieldservice:dc* extensions. Treat as already-DC.
DC_EXTENSION_PREFIX = DC_NS + "dc"

# Named unsupported extensions. These are real, standard-shipped Lightning flow
# screen components (fieldType=ComponentInstance) that CAN legitimately appear on
# a Field Service Mobile flow screen when the relevant org feature is enabled,
# but have NO Data Capture equivalent. They would otherwise fall into the generic
# "custom/unsupported component" bucket; naming them lets the gap report explain
# exactly what was found and why it can't migrate, instead of a vague "unknown
# component" line. Keyed by extensionName; value = (status, note).
#
# `runtime_industries_csv_dataimport:advCsv` — palette label "Advanced CSV
# Import"; imports CSV data via Data Processing Engine (DPE) templates. Exposed
# as a lightning__FlowScreen component and surfaced in the FSM flow builder
# palette when Industries CSV Data Import is enabled. Its DPE-backed bulk-import
# model is outside Data Capture's per-record form model, so there is no dc*
# equivalent. `...:impBeg` is the simpler "beginner" variant of the same feature.
# Verified against core (core-2206): the advCsv/impBeg LWCs live in the
# runtime_industries_csv_dataimport module with <target>lightning__FlowScreen</target>.
KNOWN_UNSUPPORTED_EXTENSIONS: Dict[str, Tuple[str, str]] = {
    "runtime_industries_csv_dataimport:advCsv": (
        NO_DC_EQUIVALENT,
        "'Advanced CSV Import' (Industries CSV Data Import / DPE-backed bulk "
        "import). No Data Capture equivalent — DC has no CSV/bulk-import screen "
        "component and its per-record form model is a different paradigm. Rebuild "
        "the data-loading step outside the flow (e.g. Data Processing Engine) or "
        "drop it; it cannot be migrated automatically.",
    ),
    "runtime_industries_csv_dataimport:impBeg": (
        NO_DC_EQUIVALENT,
        "'CSV Import' (beginner variant of Industries CSV Data Import). Same "
        "capability gap as runtime_industries_csv_dataimport:advCsv — no Data "
        "Capture equivalent; cannot be migrated automatically.",
    ),
    # Two more standard extensions that appear in the FSM palette gold file
    # (flowExtensionsForFieldServiceMobile) with no DC equivalent.
    "industries_common:intelligentDocumentUpload": (
        NO_DC_EQUIVALENT,
        "'Intelligent Document Upload' (Industries). Document capture/extraction "
        "component with no Data Capture equivalent. For plain file capture use "
        "dcUpFile; the intelligent-extraction behaviour cannot be migrated.",
    ),
    "healthcloud:censusMembersMgmtWrapper": (
        NO_DC_EQUIVALENT,
        "Health Cloud census-members management component. Domain-specific, with "
        "no Data Capture equivalent; cannot be migrated automatically.",
    ),
}

# ──────────────────────────────────────────────────────────────────────────
# 3. DC-only components (no FSM source maps to them) — reference / for docs.
#    Used to explain "these DC capabilities cannot be produced by migration."
# ──────────────────────────────────────────────────────────────────────────

DC_ONLY_COMPONENTS: Dict[str, str] = {
    "dcSignature": "Signature capture. DC-only — FSM has NO native signature component.",
    "dcEmail":     "Email input. DC-only as a dedicated component (FSM uses InputField/Email).",
    "dcPhone":     "Phone input. DC-only as a dedicated component (FSM uses InputField/Phone).",
    "dcName":      "Structured name input. DC-only.",
    "dcAddress":   "Address input (optional GPS). DC-only.",
    "dcLookup":    "Record lookup. DC-only.",
    "dcMatrix":    "Matrix / grid input. DC-only.",
    "dcCounter":   "Numeric stepper. DC-only.",
    "dcCheckbox":  "Single checkbox. DC-only as a distinct component — see the "
                   "Boolean discrepancy note below.",
    "dcFileView":  "Read-only file/image viewer. DC-only.",
    "dcUpImage":   "Image upload. DC-only as a dedicated component.",
}

# Layout / structural DC constructs FSM does not allow (core FSM handler
# disallows Region/RegionContainer/Repeater/ObjectProvided).
DC_ONLY_LAYOUT: Dict[str, str] = {
    "Region":          "Layout region. DC-only (FSM disallows).",
    "RegionContainer": "Layout region container. DC-only (FSM disallows).",
    "Repeater":        "Native repeating section. DC-only (FSM disallows; FSM used "
                       "Loop + screens instead).",
    "ObjectProvided":  "Object-provided fields. DC-only (FSM disallows).",
}


# ──────────────────────────────────────────────────────────────────────────
# 4. Capability-level gaps (beyond individual components)
# ──────────────────────────────────────────────────────────────────────────

def capability_gaps() -> List[Dict[str, str]]:
    """Capability-level differences that no per-component mapping can preserve.

    Returned as a list of {gap, detail, evidence} dicts so callers (analyze_flow,
    WI-10 summary) can render them uniformly.
    """
    return [
        {
            "gap": "No actions / buttons",
            "detail": "Data Capture has no user-facing action buttons. FSM's "
                      "PlainButtons has no DC equivalent; the only invocable action "
                      "a DC flow permits is AGX_FLOW. Button-driven FSM logic must "
                      "be redesigned.",
            "evidence": "DataCaptureFlowProcessTypeHandler.java: allowedScreenFieldTypes "
                        "omits PlainButtons; allowedActionTypes = {AGX_FLOW}.",
        },
        {
            "gap": "Offline-only environment",
            "detail": "DataCaptureFlow runs only in the Offline environment. Flows "
                      "that relied on online-only behaviour (Apex, real-time callouts) "
                      "cannot be preserved.",
            "evidence": "DataCaptureFlowProcessTypeHandler.hook_isEnvironmentAllowed "
                        "returns true only for FlowEnvironment.Offline.",
        },
        {
            "gap": "No Apex / action calls",
            "detail": "DataCaptureFlow forbids <actionCalls> and Apex data types. "
                      "FSM flows calling Apex must convert that logic to record "
                      "lookups or move it out of the flow.",
            "evidence": "DataCaptureFlowProcessTypeHandler action allowlist "
                        "(AGX_FLOW only); ActionCall / FlowDataType.Apex rejected.",
        },
        {
            "gap": "CUD only at end of flow",
            "detail": "All record create/update/delete must follow the last screen. "
                      "FSM allowed CUD mid-flow. The transformer restructures the "
                      "graph; some patterns (create->lookup cycles) need redesign.",
            "evidence": "DataCaptureFlowValidator CUD-at-end BFS.",
        },
        {
            "gap": "No fault paths",
            "detail": "Fault connectors are unsupported. FSM fault handling is "
                      "stripped and cannot be preserved.",
            "evidence": "navigateToFault() is an empty stub; $Flow.FaultMessage "
                        "global blocked (see references/dc-platform-rules.md).",
        },
        {
            "gap": "Subflows: DC-type only, no CUD",
            "detail": "A DC flow can only call another DataCaptureFlow, and subflows "
                      "cannot contain CUD. FSM AutoLaunched subflows must be inlined "
                      "or converted.",
            "evidence": "DataCaptureFlowProcessTypeHandler subflow-type check.",
        },
    ]


# ──────────────────────────────────────────────────────────────────────────
# 5. Field classification entry point
# ──────────────────────────────────────────────────────────────────────────

def classify(field_type: Optional[str],
             data_type: Optional[str] = None,
             extension_name: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Classify one FSM screen field against the DC catalog.

    Args:
        field_type: the FSM `<fieldType>` (e.g. 'InputField', 'DropdownBox',
            'ComponentInstance', 'DisplayText').
        data_type: the field's `<dataType>` (only meaningful for 'InputField').
        extension_name: the `<extensionName>` (only meaningful for
            'ComponentInstance').

    Returns a dict:
        {
          'status': mapped | no-DC-equivalent | DC-only | unknown,
          'dc_extension': 'runtime_service_fieldservice:dcX' or None,
          'dc_field_type': 'ComponentInstance'|'ComponentChoice'|... or None,
          'note': human-readable guidance,
        }
    """
    ft = (field_type or "").strip()
    dt = (data_type or "").strip() or None
    ext = (extension_name or "").strip() or None

    # ── ComponentInstance: classify by extensionName ──────────────────────
    if ft == COMPONENT_INSTANCE or (ext and not ft):
        # Already a DC component (partially hand-migrated source).
        if ext and ext.startswith(DC_EXTENSION_PREFIX):
            return _result(MAPPED, ext, COMPONENT_INSTANCE,
                           "Already a Data Capture component; passes through.")
        if ext in EXTENSION_CATALOG:
            status, dc_ext, dc_ft, note = EXTENSION_CATALOG[ext]
            return _result(status, DC_NS + dc_ext, dc_ft, note)
        # Known standard extension with no DC equivalent (e.g. Advanced CSV
        # Import) — name it explicitly so the gap report is specific.
        if ext in KNOWN_UNSUPPORTED_EXTENSIONS:
            status, note = KNOWN_UNSUPPORTED_EXTENSIONS[ext]
            return _result(status, None, None, note)
        # Any other extension (lightning:*, c:*, forceChatter:*, ...) is a
        # custom/unsupported component with no DC extension point.
        return _result(
            NO_DC_EQUIVALENT, None, None,
            f"Custom/unsupported component '{ext or 'unknown'}'. Data Capture has "
            f"no custom-component extension point; rebuild with a native dc* "
            f"component or flag as unmigratable.",
        )

    # ── InputField: resolve by dataType ───────────────────────────────────
    if ft == "InputField":
        dc_ext, dc_ft = INPUTFIELD_BY_DATATYPE.get(dt, INPUTFIELD_DEFAULT)
        note = "" if dt in INPUTFIELD_BY_DATATYPE else (
            f"InputField dataType '{dt}' not recognised; defaulted to dcTextInput."
        )
        return _result(MAPPED, DC_NS + dc_ext, dc_ft, note)

    # ── Standalone FSM field types ────────────────────────────────────────
    if ft in FSM_FIELDTYPE_CATALOG:
        status, dc_ext, dc_ft, note = FSM_FIELDTYPE_CATALOG[ft]
        full_ext = (DC_NS + dc_ext) if dc_ext else None
        return _result(status, full_ext, dc_ft, note)

    # ── DC-only layout constructs appearing in a source (unusual) ─────────
    if ft in DC_ONLY_LAYOUT:
        return _result(MAPPED, None, ft,
                       f"{DC_ONLY_LAYOUT[ft]} Passes through unchanged.")

    # ── Unrecognised ──────────────────────────────────────────────────────
    return _result(UNKNOWN, None, None,
                   f"Unrecognised FSM fieldType '{ft}'. Not in the capability "
                   f"catalog; treat as unsupported and flag for manual review.")


def _result(status: str, dc_extension: Optional[str],
            dc_field_type: Optional[str], note: str) -> Dict[str, Optional[str]]:
    return {
        "status": status,
        "dc_extension": dc_extension,
        "dc_field_type": dc_field_type,
        "note": note,
    }


def is_gap(status: str) -> bool:
    """True if this classification represents a functionality gap (won't migrate)."""
    return status in (NO_DC_EQUIVALENT, UNKNOWN)


# ──────────────────────────────────────────────────────────────────────────
# KNOWN DISCREPANCY — Boolean InputField target (dcCheckbox vs dcToggle)
# ──────────────────────────────────────────────────────────────────────────
# The shipping transformer (transform_flow.py) maps `InputField`/`Boolean` to
# `dcCheckbox`, and this catalog matches it so catalog and code stay in sync.
# The assessment spreadsheet instead recommends `dcToggle` for a Boolean
# ("Boolean/Toggle is dcToggle, NOT dcCheckbox; single Checkbox is DC-only").
# Both dcCheckbox and dcToggle bind to Boolean and deploy successfully; the
# difference is UX (checkbox vs. toggle switch). This is an unresolved product
# decision, not a correctness bug. If the mapping should change to dcToggle,
# update INPUTFIELD_BY_DATATYPE here AND transform_flow.py's FIELD_TYPE_MAP
# together. Flagged in W-23364461.
BOOLEAN_TARGET_DISCREPANCY = (
    "InputField/Boolean -> dcCheckbox (matches shipping transform_flow.py). "
    "Assessment spreadsheet recommended dcToggle. Unresolved product decision."
)


if __name__ == "__main__":
    # Tiny self-demo: print the catalog as a table.
    import json
    demo = {
        "capability_gaps": capability_gaps(),
        "boolean_discrepancy": BOOLEAN_TARGET_DISCREPANCY,
    }
    print(json.dumps(demo, indent=2))
