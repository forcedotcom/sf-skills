#!/usr/bin/env python3
"""Convert intermediate Data Capture Flow JSON into Salesforce Flow XML.

Schema is derived from real DataCaptureFlows retrieved from a Field Service
demo org (Data_Capture_Asset_Inspection, Inventory_Transfer). Notes on what
is verified vs guessed live in TYPE_MAP below.

Input JSON shape:
    {
      "formTitle": "...",
      "formType": "...",
      "screens": {
        "PascalCaseName": [ { fieldName, fieldLabel, fieldType, isRequired,
                              defaultValue, options,
                              [repeaterFields], [matrixRows],
                              [min, max, value],
                              [visibility: { field, operator, value }] }, ... ],
        ...
      },
      "postScreen": {                           # optional
        "variables":     [ { name, type } ],
        "decision":      { name, label, defaultLabel, branches: [...] },
        "recordLookups": [ { name, label, object, filters, outputAssignments, next } ],
        "loop":          { name, label, collection, next },
        "recordCreates": [ { name, label, object, inputAssignments, next } ]
      }
    }

Usage:
    build_flow.py <input.json> <FlowApiName> <output.flow-meta.xml>
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

API_VERSION = "65.0"
NS = "http://soap.sforce.com/2006/04/metadata"

# ---- Field-type mapping --------------------------------------------------
#
# Each entry: extension_name, render_strategy, [optional] fallback_label_prefix
#
# render_strategy values:
#   "instance"      -> <fieldType>ComponentInstance</fieldType>, label via inputParameters
#   "choice"        -> <fieldType>ComponentChoice</fieldType>, single-select choices
#   "multichoice"   -> <fieldType>ComponentMultiChoice</fieldType>, multi-select choices
#   "displaytext"   -> native <fieldType>DisplayText</fieldType>, no extension
#   "repeater"      -> native <fieldType>Repeater</fieldType>, nested <fields>
#
# All entries below have been verified against retrieved flows from the
# fs-demo org (May 2026) unless tagged PROBE.

VERIFIED = "verified"
PROBE = "probe"

# Each entry: (extension_name, render_strategy, fallback_prefix, status, extra_inputs)
# extra_inputs is a list of (param_name, kind, value) auto-injected on every instance.
#   kind="ref"   -> <value><elementReference>VALUE</elementReference></value>
#   kind="bool"  -> <value><booleanValue>VALUE</booleanValue></value>
#   kind="str"   -> <value><stringValue>VALUE</stringValue></value>
#
# All component names verified against the published Field Service data capture
# component reference (https://help.salesforce.com/s/articleView?id=service.mfs_data_capture_components.htm)
# and a retrieved Data_Capture_All_Components flow from a live FS org (May 2026).

TYPE_MAP: dict[str, tuple[str, str, str | None, str, list[tuple[str, str, str]]]] = {
    # type           extension                                           strategy        fallback_prefix     status     extra_inputs
    "ShortText":    ("runtime_service_fieldservice:dcTextInput",         "instance",     None,               VERIFIED,  []),
    "LongText":     ("runtime_service_fieldservice:dcLongText",          "instance",     None,               VERIFIED,  []),
    "Name":         ("runtime_service_fieldservice:dcName",              "instance",     None,               VERIFIED,  []),
    "Email":        ("runtime_service_fieldservice:dcEmail",             "instance",     None,               PROBE,     []),
    "Phone":        ("runtime_service_fieldservice:dcPhone",             "instance",     None,               PROBE,     []),
    "Numeric":      ("runtime_service_fieldservice:dcNumeric",           "instance",     None,               PROBE,     []),
    "Counter":      ("runtime_service_fieldservice:dcCounter",           "instance",     None,               VERIFIED,  []),
    "Date":         ("runtime_service_fieldservice:dcDate",              "instance",     None,               PROBE,     []),
    "DateTime":     ("runtime_service_fieldservice:dcDateTime",          "instance",     None,               PROBE,     []),
    "Checkbox":     ("runtime_service_fieldservice:dcCheckbox",          "instance",     None,               PROBE,     []),
    "Toggle":       ("runtime_service_fieldservice:dcToggle",            "instance",     None,               VERIFIED,  []),
    "Picklist":     ("runtime_service_fieldservice:dcPicklist",          "choice",       None,               VERIFIED,  []),
    # Radio uses dcRbGroup (verified May 2026 via Inventory_Transfer flow).
    "Radio":        ("runtime_service_fieldservice:dcRbGroup",           "choice",       None,               VERIFIED,  []),
    "CheckboxGroup":("runtime_service_fieldservice:dcCbGroup",           "multichoice",  None,               VERIFIED,  []),
    "DisplayText":  ("",                                                 "displaytext",  None,               VERIFIED,  []),
    "Repeater":     ("",                                                 "repeater",     None,               VERIFIED,  []),
    # Real Field Service data capture components. Their `recordId` / `parentRecordId`
    # input parameters are auto-wired to the standard Data Capture input variables
    # `parentRecordId` and `recordId` (declared at the bottom of every flow).
    "Signature":    ("runtime_service_fieldservice:dcSignature",         "instance",     None,               VERIFIED,  [("parentRecordId", "ref", "parentRecordId"), ("recordId", "ref", "recordId")]),
    "UploadFile":   ("runtime_service_fieldservice:dcUpFile",            "instance",     None,               VERIFIED,  [("recordId", "ref", "parentRecordId")]),
    "UploadImage":  ("runtime_service_fieldservice:dcUpImage",           "instance",     None,               VERIFIED,  [("recordId", "ref", "parentRecordId")]),
    "Address":      ("runtime_service_fieldservice:dcAddress",           "instance",     None,               VERIFIED,  []),
    "Matrix":       ("runtime_service_fieldservice:dcMatrix",            "matrix",       None,               VERIFIED,  []),
    "Images":       ("runtime_service_fieldservice:dcImages",            "instance",     None,               VERIFIED,  [("recordId", "ref", "parentRecordId")]),
    # Lookup is a real component but needs `objectApiName` (and optionally `searchedFields`)
    # supplied via the spec's `lookupObject` / `lookupSearchFields` keys. If `lookupObject`
    # is missing, render_field falls back to a labeled ShortText so the flow still deploys.
    "Lookup":       ("runtime_service_fieldservice:dcLookup",            "instance",     None,               VERIFIED,  []),
    # FileView is a read-only static-image viewer; it needs `fileName` (the asset
    # filename without extension) supplied via the spec's `fileName` key.
    "FileView":     ("runtime_service_fieldservice:dcFileView",          "instance",     None,               VERIFIED,  []),
}

API_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
MAX_SECTION_DEPTH = 5


@dataclass
class Field:
    name: str
    label: str
    field_type: str
    is_required: bool
    default_value: Any = None
    options: list[str] | None = None
    matrix_rows: list[str] | None = None
    matrix_questions: list[str] | None = None  # Matrix component's row labels (input parameter "questions")
    repeater_fields: list["Field"] | None = None
    counter_min: float | None = None
    counter_max: float | None = None
    counter_value: float | None = None
    visibility: dict | None = None  # { "field": str, "operator": str, "value": str }
    # Lookup-specific:
    lookup_object: str | None = None         # objectApiName (e.g. "Asset")
    lookup_search_fields: str | None = None  # comma-sep field names (e.g. "Name, SerialNumber")
    lookup_multi: bool = False               # isMultiSelection
    # FileView-specific:
    file_name: str | None = None             # static asset filename without extension


@dataclass
class Section:
    """Visual grouping rendered as a Salesforce Section component
    (RegionContainer with a single full-width Region child).

    Sections are emitted only when the source explicitly shows them. Specs
    without sections deploy as a flat list of fields exactly as before.
    """
    name: str
    label: str
    fields: list[Field]
    visibility: dict | None = None  # shape (b): {conditionLogic, conditions:[...]}


@dataclass
class Screen:
    name: str
    label: str
    # Either a flat list of Field, or a list of Section. Mixed is not allowed:
    # if any item in a screen carries `section`, all fields after the first
    # sentinel get bucketed into Sections; fields before the first sentinel go
    # into an implicit lead-in Section labeled "General".
    fields: list[Field]
    sections: list[Section] | None = None


@dataclass
class FormSpec:
    title: str
    form_type: str
    screens: list[Screen]
    # All choices used across the flow, deduped: maps choice api_name -> display_text
    choices: dict[str, str] = dc_field(default_factory=dict)
    # Field name (api) -> field type, used by visibility resolution
    fields_by_name: dict[str, Field] = dc_field(default_factory=dict)
    # Raw post-screen automation block (passes through as-is; emitted in build_xml)
    post_screen: dict | None = None
    decisions: list = dc_field(default_factory=list)
    screen_connectors: dict = dc_field(default_factory=dict)
    warnings: list[str] = dc_field(default_factory=list)
    # WI-7: {type, name, reason} entries the converter could not fully migrate.
    incomplete_migration: list = dc_field(default_factory=list)


def coerce_api_name(raw: str, *, fallback_prefix: str = "f_") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw or "")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "field"
    if not cleaned[0].isalpha():
        cleaned = fallback_prefix + cleaned
    return cleaned[:80]


def _xml_comment_safe(text: str) -> str:
    """Make text safe inside an XML comment: no '--' run, no comment-closing '>'."""
    s = (text or "").replace("\r", " ").replace("\n", " ")
    # Collapse any run of dashes to an em-dash so '--' / '-->' can't appear.
    s = re.sub(r"-{2,}", "—", s)
    # The '--' collapse above already prevents a premature '-->'. Escaping any
    # remaining '>' is defensive only — a lone '>' is legal in a comment, but
    # this keeps the body free of angle brackets.
    s = s.replace(">", "&gt;")
    return " ".join(s.split())


def humanize_screen_key(key: str) -> str:
    s = key.replace("_", " ")
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_field(raw: dict, used_names: set[str], warnings: list[str] | None = None) -> Field:
    name = (raw.get("fieldName") or "").strip()
    if not name:
        raise ValueError(f"field missing fieldName: {raw}")
    api_name = uniquify(coerce_api_name(name), used_names)

    original_field_type = (raw.get("fieldType") or "ShortText").strip()
    field_type = original_field_type
    if field_type not in TYPE_MAP:
        field_type = "ShortText"
        existing = (raw.get("fieldLabel") or "").strip()
        raw["fieldLabel"] = f"[Unknown type: {original_field_type}] {existing}".strip()
        # FIX I2: surface unknown fieldType as a warning so it appears in output.
        if warnings is not None:
            warnings.append(f"field '{api_name}': unknown fieldType '{original_field_type}', downgraded to ShortText")

    label = (raw.get("fieldLabel") or api_name).strip()
    is_required = bool(raw.get("isRequired"))
    default_value = raw.get("defaultValue")
    options_raw = raw.get("options")
    options = [str(o) for o in options_raw] if isinstance(options_raw, list) else None
    matrix_rows_raw = raw.get("matrixRows")
    matrix_rows = [str(r) for r in matrix_rows_raw] if isinstance(matrix_rows_raw, list) else None

    repeater_children: list[Field] | None = None
    if field_type == "Repeater":
        children_raw = raw.get("repeaterFields") or []
        if not children_raw:
            raise ValueError(f"Repeater '{api_name}' has no repeaterFields")
        repeater_children = [parse_field(c, used_names, warnings) for c in children_raw]

    counter_min = _to_number(raw.get("min"))
    counter_max = _to_number(raw.get("max"))
    counter_value = _to_number(raw.get("value"))

    visibility = raw.get("visibility")
    if visibility is not None and not isinstance(visibility, dict):
        visibility = None

    # Component-specific config
    lookup_object = raw.get("lookupObject")
    lookup_object = str(lookup_object).strip() if lookup_object else None
    lookup_search_fields = raw.get("lookupSearchFields")
    lookup_search_fields = str(lookup_search_fields).strip() if lookup_search_fields else None
    lookup_multi = bool(raw.get("lookupMulti")) or bool(raw.get("isMultiSelection"))
    file_name = raw.get("fileName")
    file_name = str(file_name).strip() if file_name else None

    # Matrix uses "matrixRows" as per-row prompt text. The dcMatrix component
    # exposes those as the "questions" input parameter. options become the
    # column choices (choiceReferences).
    matrix_questions: list[str] | None = None
    if field_type == "Matrix":
        matrix_questions = matrix_rows

    return Field(
        name=api_name,
        label=label,
        field_type=field_type,
        is_required=is_required,
        default_value=default_value,
        options=options,
        matrix_rows=matrix_rows,
        matrix_questions=matrix_questions,
        repeater_fields=repeater_children,
        counter_min=counter_min,
        counter_max=counter_max,
        counter_value=counter_value,
        visibility=visibility,
        lookup_object=lookup_object,
        lookup_search_fields=lookup_search_fields,
        lookup_multi=lookup_multi,
        file_name=file_name,
    )


def _to_number(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def uniquify(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    i = 2
    while f"{name}_{i}" in used:
        i += 1
    final = f"{name}_{i}"
    used.add(final)
    return final


def parse_spec(data: dict) -> FormSpec:
    title = (data.get("formTitle") or "Data Capture Form").strip()
    form_type = (data.get("formType") or "").strip()
    screens_raw = data.get("screens")
    if not isinstance(screens_raw, dict) or not screens_raw:
        raise ValueError("spec must have a non-empty 'screens' object")

    used_names: set[str] = set()
    spec = FormSpec(title=title, form_type=form_type, screens=[])
    for screen_key, fields_raw in screens_raw.items():
        if not isinstance(fields_raw, list) or not fields_raw:
            raise ValueError(f"screen '{screen_key}' must have a non-empty list of fields")
        screen_api = uniquify(coerce_api_name(f"Screen_{screen_key}"), used_names)
        screen_label = humanize_screen_key(screen_key)

        # Split items into (Section header dict | field) sequence. A header is
        # any dict with a "section" key and no "fieldName".
        sections: list[Section] = []
        flat_fields: list[Field] = []
        current_section_label: str | None = None
        current_section_fields: list[Field] = []
        # FIX I1: section_names_used now seeds from used_names to prevent
        # flow-global collisions (e.g. Sec_General on multiple screens).
        section_names_used: set[str] = used_names.copy()

        def flush_section():
            if current_section_label is None:
                return
            api = uniquify(
                coerce_api_name(f"Sec_{current_section_label}"),
                section_names_used,
            )
            # FIX I1: register section name in global used_names to prevent
            # cross-screen collisions (e.g. multiple "Sec_General" sections).
            used_names.add(api)
            sections.append(Section(
                name=api,
                label=current_section_label,
                fields=current_section_fields[:],
            ))

        def build_nested_section(item: dict, used: set[str],
                                 sec_names: set[str], depth: int) -> Section:
            label = str(item.get("section") or "Section").strip() or "Section"
            api = uniquify(coerce_api_name(f"Sec_{label}"), sec_names)
            # FIX I1: register nested section name in global used_names.
            used.add(api)
            children: list = []
            for child in item.get("fields") or []:
                if isinstance(child, dict) and "section" in child and "fields" in child:
                    if depth + 1 >= MAX_SECTION_DEPTH:
                        # Over-cap: nesting stops at MAX_SECTION_DEPTH. Flatten ALL
                        # descendant leaf fields of this over-cap subtree into the
                        # current section (no field is dropped). NOTE: the over-cap
                        # section's own visibilityRule is intentionally not preserved
                        # here — the converter's depth-cap flagging (WI-7) surfaces
                        # over-cap chains to the user, honoring "flag, never silently
                        # drop".
                        def _flatten_leaves(node_fields):
                            for leaf in node_fields:
                                if isinstance(leaf, dict) and "fieldName" in leaf:
                                    yield parse_field(leaf, used, spec.warnings)
                                elif isinstance(leaf, dict) and "fields" in leaf:
                                    yield from _flatten_leaves(leaf.get("fields") or [])
                        children.extend(_flatten_leaves(child.get("fields") or []))
                        continue
                    children.append(build_nested_section(child, used, sec_names, depth + 1))
                elif isinstance(child, dict) and "fieldName" in child:
                    children.append(parse_field(child, used, spec.warnings))
            sec = Section(name=api, label=label, fields=children)
            vis = item.get("visibility")
            sec.visibility = vis if isinstance(vis, dict) else None
            return sec

        has_sections = any(
            isinstance(item, dict) and "section" in item and "fieldName" not in item
            for item in fields_raw
        )

        for item in fields_raw:
            if has_sections and isinstance(item, dict) and "section" in item and "fieldName" not in item:
                if "fields" in item:
                    # Self-contained (possibly nested) section.
                    flush_section()
                    current_section_label = None
                    sections.append(build_nested_section(
                        item, used_names, section_names_used, depth=0))
                    continue
                # Legacy inline opener (unchanged).
                flush_section()
                current_section_label = str(item["section"]).strip() or "Section"
                current_section_fields = []
                continue
            f = parse_field(item, used_names, spec.warnings)
            if has_sections:
                if current_section_label is None:
                    # Fields before the first sentinel: bucket into implicit "General".
                    current_section_label = "General"
                    current_section_fields = []
                current_section_fields.append(f)
            else:
                flat_fields.append(f)

        if has_sections:
            flush_section()
            spec.screens.append(Screen(
                name=screen_api,
                label=screen_label,
                fields=list(_walk_fields([ff for s in sections for ff in s.fields])),
                sections=sections,
            ))
        else:
            spec.screens.append(Screen(name=screen_api, label=screen_label, fields=flat_fields))

        # Hoist choices for choice/multichoice/matrix strategies (top-level + repeater children).
        # Matrix uses choiceReferences for its column options exactly like Picklist.
        screen_obj = spec.screens[-1]
        for f in _walk_fields(screen_obj.fields):
            strategy = TYPE_MAP[f.field_type][1]
            if strategy in ("choice", "multichoice", "matrix") and f.options:
                for opt in f.options:
                    cname = uniquify_choice(opt, spec.choices)
                    spec.choices.setdefault(cname, opt)
            spec.fields_by_name[f.name] = f

    spec.post_screen = data.get("postScreen") if isinstance(data.get("postScreen"), dict) else None
    raw_decisions = data.get("decisions")
    spec.decisions = raw_decisions if isinstance(raw_decisions, list) else []
    raw_conns = data.get("_screenConnectors")
    spec.screen_connectors = raw_conns if isinstance(raw_conns, dict) else {}
    inc = data.get("_incompleteMigration")
    if isinstance(inc, list):
        spec.incomplete_migration = inc
    return spec


def _walk_fields(fields: list):
    for f in fields:
        if isinstance(f, Section):
            yield from _walk_fields(f.fields)
            continue
        yield f
        if f.repeater_fields:
            yield from _walk_fields(f.repeater_fields)


def uniquify_choice(display: str, existing: dict[str, str]) -> str:
    """Choice api_name = sanitized display, but if same display already mapped, reuse it."""
    for k, v in existing.items():
        if v == display:
            return k
    base = coerce_api_name(display)
    if base in existing:
        i = 2
        while f"{base}_{i}" in existing:
            i += 1
        return f"{base}_{i}"
    return base


# ---- XML emission --------------------------------------------------------


def x(text: str) -> str:
    return xml_escape(text or "", {'"': "&quot;", "'": "&apos;"})


def render_input_param(name: str, value: str | None = None, *,
                       boolean_value: bool | None = None,
                       number_value: float | None = None,
                       ref_value: str | None = None,
                       indent: str = "                ") -> str:
    parts = [f"{indent}<inputParameters>\n",
             f"{indent}    <name>{x(name)}</name>\n",
             f"{indent}    <value>\n"]
    if ref_value is not None:
        parts.append(f"{indent}        <elementReference>{x(ref_value)}</elementReference>\n")
    elif value is not None:
        parts.append(f"{indent}        <stringValue>{x(value)}</stringValue>\n")
    elif boolean_value is not None:
        parts.append(f"{indent}        <booleanValue>{'true' if boolean_value else 'false'}</booleanValue>\n")
    elif number_value is not None:
        parts.append(f"{indent}        <numberValue>{_fmt_num(number_value)}</numberValue>\n")
    parts.extend([f"{indent}    </value>\n", f"{indent}</inputParameters>\n"])
    return "".join(parts)


def _fmt_num(n: float) -> str:
    # FIX I5: Use fixed/decimal formatting to avoid scientific notation (repr(1e-5)=='1e-05').
    # Salesforce expects e.g. "1.0" not "1" for integers.
    if n == int(n):
        return f"{n:.1f}"
    # Use .15g for compact representation, then convert any scientific notation to fixed.
    # This balances precision (avoiding floating-point artifacts like 123.456000000000003)
    # with readability (avoiding 1e-05).
    formatted = f"{n:.15g}"
    # If .15g produced scientific notation, convert to fixed-point.
    if 'e' in formatted or 'E' in formatted:
        # Use sufficient decimal places to represent the number accurately.
        formatted = f"{n:.15f}".rstrip('0').rstrip('.')
    # Ensure there's a decimal point for Salesforce (e.g. "5" -> "5.0").
    if '.' not in formatted:
        formatted += ".0"
    return formatted


def render_style_properties(indent: str) -> str:
    return (
        f"{indent}<styleProperties>\n"
        f"{indent}    <verticalAlignment>\n"
        f"{indent}        <stringValue>top</stringValue>\n"
        f"{indent}    </verticalAlignment>\n"
        f"{indent}    <width>\n"
        f"{indent}        <stringValue>12</stringValue>\n"
        f"{indent}    </width>\n"
        f"{indent}</styleProperties>\n"
    )


def find_choice_name(spec: FormSpec, display: str) -> str | None:
    for k, v in spec.choices.items():
        if v == display:
            return k
    return None


def render_visibility_rule(field: Field, spec: FormSpec, indent: str) -> str:
    """Emit a <visibilityRule> for the field's visibility spec.

    Two accepted shapes, discriminated by the "conditions" key:
      (a) legacy  {field, operator, value}  — resolves value to a choice
          api-name, rightValue booleanValue=true, conditionLogic=and.
      (b) multi   {conditionLogic, conditions:[{leftValueReference, operator,
          rightValue:{<type>:v}}]} — leftValueReference used verbatim; rendered
          via render_conditions (18 operators, all typed rightValues).
    """
    v = field.visibility or {}

    # Shape (b): multi-condition. leftValueReference is already a resolved
    # element/field name from the converter — used verbatim.
    if "conditions" in v:
        conditions = v.get("conditions") or []
        if not conditions:
            spec.warnings.append(
                f"visibility on {field.name}: empty conditions, skipped")
            return ""
        for cond in conditions:
            left = (cond.get("leftValueReference") or "").split(".")[0]
            if not left or left not in spec.fields_by_name:
                spec.warnings.append(
                    f"visibility on {field.name}: leftValueReference "
                    f"'{cond.get('leftValueReference')}' not found, skipped")
                return ""
        inner = indent + "    "
        return (f"{indent}<visibilityRule>\n"
                + render_conditions(conditions, v.get("conditionLogic") or "and", inner)
                + f"{indent}</visibilityRule>\n")

    # Shape (a): legacy choice-boolean rule (unchanged).
    target_field = (v.get("field") or "").strip()
    target_value = (v.get("value") or "").strip()
    operator = (v.get("operator") or "EqualTo").strip()
    if not target_field or not target_value:
        spec.warnings.append(
            f"visibility on {field.name}: missing field/value, skipped")
        return ""
    parent = spec.fields_by_name.get(target_field)
    if parent is None:
        spec.warnings.append(
            f"visibility on {field.name}: field '{target_field}' not found, skipped")
        return ""
    if parent.field_type not in ("Picklist", "Radio", "CheckboxGroup"):
        spec.warnings.append(
            f"visibility on {field.name}: field '{target_field}' is not a choice field, skipped")
        return ""
    choice_name = find_choice_name(spec, target_value)
    if choice_name is None:
        spec.warnings.append(
            f"visibility on {field.name}: value '{target_value}' is not one of "
            f"'{target_field}'s options, skipped")
        return ""

    # FIX I6: legacy shape (a) always emits rightValue booleanValue=true, so warn
    # if the operator is not EqualTo (e.g. "NotEqualTo ... true" is likely unintended).
    if operator != "EqualTo":
        spec.warnings.append(
            f"visibility on {field.name}: legacy shape (a) always emits 'rightValue booleanValue=true'; "
            f"operator '{operator}' may produce unexpected results (consider shape (b) for complex logic)")

    inner = indent + "    "
    cinner = inner + "    "
    rinner = cinner + "    "
    parts = [
        f"{indent}<visibilityRule>\n",
        f"{inner}<conditionLogic>and</conditionLogic>\n",
        f"{inner}<conditions>\n",
        f"{cinner}<leftValueReference>{x(choice_name)}</leftValueReference>\n",
        f"{cinner}<operator>{x(operator)}</operator>\n",
        f"{cinner}<rightValue>\n",
        f"{rinner}<booleanValue>true</booleanValue>\n",
        f"{cinner}</rightValue>\n",
        f"{inner}</conditions>\n",
        f"{indent}</visibilityRule>\n",
    ]
    return "".join(parts)


def render_field(field: Field, spec: FormSpec, indent: str = "        ") -> str:
    extension_name, strategy, fallback_prefix, _status, extra_inputs = TYPE_MAP[field.field_type]

    # Lookup needs `objectApiName`; without it, fall back to a labeled ShortText
    # so the flow still deploys and the admin can wire it up.
    if field.field_type == "Lookup" and not field.lookup_object:
        spec.warnings.append(
            f"Lookup '{field.name}': no `lookupObject` provided; rendering as ShortText placeholder."
        )
        extension_name = "runtime_service_fieldservice:dcTextInput"
        strategy = "instance"
        fallback_prefix = "[Lookup — set objectApiName in Flow Builder] "
        extra_inputs = []

    # FileView needs `fileName`; without it, fall back to a labeled ShortText placeholder.
    if field.field_type == "FileView" and not field.file_name:
        spec.warnings.append(
            f"FileView '{field.name}': no `fileName` provided; rendering as ShortText placeholder."
        )
        extension_name = "runtime_service_fieldservice:dcTextInput"
        strategy = "instance"
        fallback_prefix = "[FileView — set fileName in Flow Builder] "
        extra_inputs = []

    label = field.label
    if fallback_prefix:
        label = f"{fallback_prefix}{label}"

    parts: list[str] = []
    parts.append(f"{indent}<fields>\n")
    parts.append(f"{indent}    <name>{x(field.name)}</name>\n")

    inner = indent + "    "

    if strategy == "displaytext":
        body = field.default_value if isinstance(field.default_value, str) and field.default_value else label
        parts.append(f"{indent}    <fieldText>{x('<p>' + body + '</p>')}</fieldText>\n")
        parts.append(f"{indent}    <fieldType>DisplayText</fieldType>\n")
        parts.append(render_style_properties(inner))
        parts.append(f"{indent}</fields>\n")
        return "".join(parts)

    if strategy == "repeater":
        parts.append(f"{indent}    <fieldType>Repeater</fieldType>\n")
        for child in field.repeater_fields or []:
            parts.append(render_field(child, spec, indent + "    "))
        parts.append(f"{indent}    <isRequired>{'true' if field.is_required else 'false'}</isRequired>\n")
        parts.append(render_style_properties(inner))
        if field.visibility:
            parts.append(render_visibility_rule(field, spec, inner))
        parts.append(f"{indent}</fields>\n")
        return "".join(parts)

    if strategy in ("choice", "multichoice"):
        for opt in field.options or []:
            cname = find_choice_name(spec, opt)
            if cname:
                parts.append(f"{indent}    <choiceReferences>{x(cname)}</choiceReferences>\n")
        if field.default_value and isinstance(field.default_value, str):
            cname = find_choice_name(spec, field.default_value)
            if cname:
                parts.append(f"{indent}    <defaultValue>\n")
                parts.append(f"{indent}        <elementReference>{x(cname)}</elementReference>\n")
                parts.append(f"{indent}    </defaultValue>\n")
        parts.append(f"{indent}    <extensionName>{x(extension_name)}</extensionName>\n")
        parts.append(f"{indent}    <fieldText>{x(label)}</fieldText>\n")
        parts.append(f"{indent}    <fieldType>{'ComponentChoice' if strategy == 'choice' else 'ComponentMultiChoice'}</fieldType>\n")
        parts.append(f"{indent}    <inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>\n")
        parts.append(f"{indent}    <isRequired>{'true' if field.is_required else 'false'}</isRequired>\n")
        parts.append(f"{indent}    <storeOutputAutomatically>true</storeOutputAutomatically>\n")
        parts.append(render_style_properties(inner))
        if field.visibility:
            parts.append(render_visibility_rule(field, spec, inner))
        parts.append(f"{indent}</fields>\n")
        return "".join(parts)

    if strategy == "matrix":
        # dcMatrix is a ComponentMultiChoice that takes column options via
        # <choiceReferences> and row labels via the "questions" input parameter
        # (a JSON-encoded array of strings). Verified May 2026 from
        # Data_Capture_All_Components.flow-meta.xml.
        for opt in field.options or []:
            cname = find_choice_name(spec, opt)
            if cname:
                parts.append(f"{indent}    <choiceReferences>{x(cname)}</choiceReferences>\n")
        if field.default_value and isinstance(field.default_value, str):
            cname = find_choice_name(spec, field.default_value)
            if cname:
                parts.append(f"{indent}    <defaultValue>\n")
                parts.append(f"{indent}        <elementReference>{x(cname)}</elementReference>\n")
                parts.append(f"{indent}    </defaultValue>\n")
        parts.append(f"{indent}    <extensionName>{x(extension_name)}</extensionName>\n")
        parts.append(f"{indent}    <fieldText>{x(label)}</fieldText>\n")
        parts.append(f"{indent}    <fieldType>ComponentMultiChoice</fieldType>\n")
        if field.matrix_questions:
            questions_json = json.dumps(field.matrix_questions, ensure_ascii=False)
            parts.append(render_input_param("questions", questions_json, indent=inner))
        parts.append(f"{indent}    <inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>\n")
        parts.append(f"{indent}    <isRequired>{'true' if field.is_required else 'false'}</isRequired>\n")
        parts.append(f"{indent}    <storeOutputAutomatically>true</storeOutputAutomatically>\n")
        parts.append(render_style_properties(inner))
        if field.visibility:
            parts.append(render_visibility_rule(field, spec, inner))
        parts.append(f"{indent}</fields>\n")
        return "".join(parts)

    # strategy == "instance"
    parts.append(f"{indent}    <extensionName>{x(extension_name)}</extensionName>\n")
    parts.append(f"{indent}    <fieldType>ComponentInstance</fieldType>\n")
    parts.append(render_input_param("label", label, indent=inner))
    # dcCheckbox/dcToggle don't expose a `required` input attribute — an
    # unchecked/off boolean is itself a valid answer, so deploying `required`
    # on these fails with "We can't find this input attribute: 'required'".
    if field.is_required and field.field_type not in ("Checkbox", "Toggle"):
        parts.append(render_input_param("required", boolean_value=True, indent=inner))
    if field.field_type == "Counter":
        if field.counter_min is not None:
            parts.append(render_input_param("min", number_value=field.counter_min, indent=inner))
        if field.counter_max is not None:
            parts.append(render_input_param("max", number_value=field.counter_max, indent=inner))
        if field.counter_value is not None:
            parts.append(render_input_param("value", number_value=field.counter_value, indent=inner))
    # Component-specific input parameters
    if field.field_type == "Lookup" and field.lookup_object:
        parts.append(render_input_param("objectApiName", field.lookup_object, indent=inner))
        if field.lookup_search_fields:
            parts.append(render_input_param("searchedFields", field.lookup_search_fields, indent=inner))
        if field.lookup_multi:
            parts.append(render_input_param("isMultiSelection", boolean_value=True, indent=inner))
    if field.field_type == "FileView" and field.file_name:
        parts.append(render_input_param("fileName", field.file_name, indent=inner))
    # Auto-injected component plumbing (e.g. UploadImage's recordId, Signature's
    # parentRecordId). These reference the standard DataCaptureFlow input vars.
    for param_name, kind, value in extra_inputs:
        if kind == "ref":
            parts.append(render_input_param(param_name, ref_value=value, indent=inner))
        elif kind == "bool":
            parts.append(render_input_param(param_name, boolean_value=(value == "true"), indent=inner))
        else:
            parts.append(render_input_param(param_name, value, indent=inner))
    if field.default_value is not None and isinstance(field.default_value, (str, int, float, bool)) \
            and field.field_type != "Counter":
        if isinstance(field.default_value, bool):
            parts.append(render_input_param("defaultValue", boolean_value=field.default_value, indent=inner))
        elif isinstance(field.default_value, (int, float)):
            parts.append(render_input_param("defaultValue", number_value=float(field.default_value), indent=inner))
        else:
            parts.append(render_input_param("defaultValue", str(field.default_value), indent=inner))
    parts.append(f"{indent}    <inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>\n")
    parts.append(f"{indent}    <isRequired>{'true' if field.is_required else 'false'}</isRequired>\n")
    parts.append(f"{indent}    <storeOutputAutomatically>true</storeOutputAutomatically>\n")
    parts.append(render_style_properties(inner))
    if field.visibility:
        parts.append(render_visibility_rule(field, spec, inner))
    parts.append(f"{indent}</fields>\n")
    return "".join(parts)


def render_section(section: Section, spec: FormSpec, indent: str = "        ") -> str:
    """Render a Salesforce Flow Section component.

    Encoded as a single <fields> block of fieldType=RegionContainer with one
    inner <fields> block of fieldType=Region (single column, full width 12).
    Mirrors the verified pattern in
    .claude/skills/salesforce-data-capture/examples/Data_Capture_All_Components.flow-meta.xml.
    """
    inner = indent + "    "
    region_inner = inner + "    "
    parts: list[str] = []
    parts.append(f"{indent}<fields>\n")
    parts.append(f"{inner}<name>{x(section.name)}</name>\n")
    parts.append(f"{inner}<fieldText>{x(section.label)}</fieldText>\n")
    parts.append(f"{inner}<fieldType>RegionContainer</fieldType>\n")
    # Single Region child (one column, width 12).
    parts.append(f"{inner}<fields>\n")
    parts.append(f"{region_inner}<name>{x(section.name)}_Col1</name>\n")
    parts.append(f"{region_inner}<fieldType>Region</fieldType>\n")
    for field in section.fields:
        if isinstance(field, Section):
            parts.append(render_section(field, spec, indent=region_inner))
        else:
            parts.append(render_field(field, spec, indent=region_inner))
    parts.append(f"{region_inner}<inputParameters>\n")
    parts.append(f"{region_inner}    <name>width</name>\n")
    parts.append(f"{region_inner}    <value>\n")
    parts.append(f"{region_inner}        <stringValue>12</stringValue>\n")
    parts.append(f"{region_inner}    </value>\n")
    parts.append(f"{region_inner}</inputParameters>\n")
    parts.append(f"{region_inner}<isRequired>false</isRequired>\n")
    parts.append(f"{inner}</fields>\n")
    parts.append(f"{inner}<isRequired>false</isRequired>\n")
    parts.append(f"{inner}<regionContainerType>SectionWithHeader</regionContainerType>\n")
    parts.append(render_style_properties(inner))
    if section.visibility and section.visibility.get("conditions"):
        parts.append(
            f"{inner}<visibilityRule>\n"
            + render_conditions(section.visibility["conditions"],
                                section.visibility.get("conditionLogic") or "and",
                                inner + "    ")
            + f"{inner}</visibilityRule>\n"
        )
    parts.append(f"{indent}</fields>\n")
    return "".join(parts)


def render_screen(screen: Screen, spec: FormSpec, *, next_target: str | None) -> str:
    parts: list[str] = []
    parts.append("    <screens>\n")
    parts.append(f"        <name>{x(screen.name)}</name>\n")
    parts.append(f"        <label>{x(screen.label)}</label>\n")
    parts.append("        <locationX>0</locationX>\n")
    parts.append("        <locationY>0</locationY>\n")
    parts.append("        <allowBack>true</allowBack>\n")
    parts.append("        <allowFinish>true</allowFinish>\n")
    parts.append("        <allowPause>true</allowPause>\n")
    if next_target:
        parts.append("        <connector>\n")
        parts.append(f"            <targetReference>{x(next_target)}</targetReference>\n")
        parts.append("        </connector>\n")
    if screen.sections:
        for section in screen.sections:
            parts.append(render_section(section, spec))
    else:
        for field in screen.fields:
            parts.append(render_field(field, spec))
    parts.append("        <showFooter>true</showFooter>\n")
    parts.append("        <showHeader>true</showHeader>\n")
    parts.append("    </screens>\n")
    return "".join(parts)


def render_choice(name: str, display: str) -> str:
    return (
        "    <choices>\n"
        f"        <name>{x(name)}</name>\n"
        f"        <choiceText>{x(display)}</choiceText>\n"
        "        <dataType>String</dataType>\n"
        "        <value>\n"
        f"            <stringValue>{x(display)}</stringValue>\n"
        "        </value>\n"
        "    </choices>\n"
    )


# ---- post-screen automation ----------------------------------------------


def _render_value(spec: FormSpec, raw: dict | None,
                  *, value_key: str = "value", ref_key: str = "valueRef",
                  bool_key: str = "boolean", num_key: str = "number",
                  indent: str = "        ") -> str:
    """Render a <value>...</value> block from a raw spec dict.

    Recognised keys: valueRef (elementReference), value (stringValue),
    boolean (booleanValue), number (numberValue).
    """
    raw = raw or {}
    parts = [f"{indent}<value>\n"]
    inner = indent + "    "
    if ref_key in raw and raw[ref_key] is not None:
        parts.append(f"{inner}<elementReference>{x(str(raw[ref_key]))}</elementReference>\n")
    elif bool_key in raw and raw[bool_key] is not None:
        parts.append(f"{inner}<booleanValue>{'true' if raw[bool_key] else 'false'}</booleanValue>\n")
    elif num_key in raw and raw[num_key] is not None:
        parts.append(f"{inner}<numberValue>{_fmt_num(float(raw[num_key]))}</numberValue>\n")
    elif value_key in raw and raw[value_key] is not None:
        parts.append(f"{inner}<stringValue>{x(str(raw[value_key]))}</stringValue>\n")
    parts.append(f"{indent}</value>\n")
    return "".join(parts)


def render_conditions(conditions: list[dict], condition_logic: str, indent: str) -> str:
    """Render a <conditionLogic> line + one <conditions> block per condition.

    `indent` is the indent of the <conditionLogic>/<conditions> tags; condition
    children (leftValueReference/operator/rightValue) sit at indent + 4 spaces.
    rightValue typing is delegated to _render_decision_right_value, so all 18
    operators and every typed value render through a single code path.
    """
    child = indent + "    "
    out: list[str] = [f"{indent}<conditionLogic>{x(condition_logic or 'and')}</conditionLogic>\n"]
    for cond in conditions or []:
        out.append(f"{indent}<conditions>\n")
        out.append(f"{child}<leftValueReference>{x(cond.get('leftValueReference') or '')}</leftValueReference>\n")
        out.append(f"{child}<operator>{x(cond.get('operator') or 'EqualTo')}</operator>\n")
        out.append(_render_decision_right_value(cond.get("rightValue"), indent=child))
        out.append(f"{indent}</conditions>\n")
    return "".join(out)


def render_decisions(decisions: list[dict]) -> str:
    """Render N <decisions> elements from the spec-level decisions list.

    Each decision: {name, label, defaultConnector, defaultLabel, rules:[...]}.
    Each rule: {name, label, conditionLogic, conditions:[...], connectsTo}.
    Each condition: {leftValueReference, operator, rightValue: {<type>: v}}.
    """
    if not decisions:
        return ""
    out: list[str] = []
    for dec in decisions:
        out.append("    <decisions>\n")
        out.append(f"        <name>{x(dec.get('name', 'Decision'))}</name>\n")
        out.append(f"        <label>{x(dec.get('label') or dec.get('name', 'Decision'))}</label>\n")
        out.append("        <locationX>0</locationX>\n")
        out.append("        <locationY>0</locationY>\n")
        if dec.get("defaultConnector"):
            out.append("        <defaultConnector>\n")
            out.append(f"            <targetReference>{x(dec['defaultConnector'])}</targetReference>\n")
            out.append("        </defaultConnector>\n")
        if dec.get("defaultLabel"):
            out.append(f"        <defaultConnectorLabel>{x(dec['defaultLabel'])}</defaultConnectorLabel>\n")
        for rule in dec.get("rules") or []:
            out.append("        <rules>\n")
            out.append(f"            <name>{x(rule.get('name', 'Rule'))}</name>\n")
            out.append(render_conditions(
                rule.get("conditions") or [],
                rule.get("conditionLogic") or "and",
                indent="            ",
            ))
            if rule.get("connectsTo"):
                out.append("            <connector>\n")
                out.append(f"                <targetReference>{x(rule['connectsTo'])}</targetReference>\n")
                out.append("            </connector>\n")
            out.append(f"            <label>{x(rule.get('label') or rule.get('name', 'Rule'))}</label>\n")
            out.append("        </rules>\n")
        out.append("    </decisions>\n")
    return "".join(out)


def _render_decision_right_value(rv: dict | None, *, indent: str) -> str:
    """Render <rightValue> from a single-key typed dict."""
    inner = indent + "    "
    parts = [f"{indent}<rightValue>\n"]
    rv = rv or {}
    if "elementReference" in rv:
        parts.append(f"{inner}<elementReference>{x(str(rv['elementReference']))}</elementReference>\n")
    elif "booleanValue" in rv:
        parts.append(f"{inner}<booleanValue>{'true' if rv['booleanValue'] else 'false'}</booleanValue>\n")
    elif "numberValue" in rv:
        parts.append(f"{inner}<numberValue>{_fmt_num(float(rv['numberValue']))}</numberValue>\n")
    elif "stringValue" in rv:
        parts.append(f"{inner}<stringValue>{x(str(rv['stringValue']))}</stringValue>\n")
    parts.append(f"{indent}</rightValue>\n")
    return "".join(parts)


def render_post_screen(spec: FormSpec) -> tuple[str, list[str]]:
    """Returns (xml_chunk, extra_variables_xml_list).

    extra_variables come from postScreen.variables; the caller appends them
    to the global <variables> block.
    """
    if not spec.post_screen:
        return "", []

    out: list[str] = []
    extra_vars_xml: list[str] = []

    decision = spec.post_screen.get("decision")
    lookups = spec.post_screen.get("recordLookups") or []
    loop = spec.post_screen.get("loop")
    creates = spec.post_screen.get("recordCreates") or []
    variables = spec.post_screen.get("variables") or []

    # decisions
    if decision and isinstance(decision, dict):
        out.append("    <decisions>\n")
        out.append(f"        <name>{x(decision.get('name', 'Decision'))}</name>\n")
        out.append(f"        <label>{x(decision.get('label') or decision.get('name', 'Decision'))}</label>\n")
        out.append("        <locationX>0</locationX>\n")
        out.append("        <locationY>0</locationY>\n")
        if decision.get("defaultLabel"):
            out.append(f"        <defaultConnectorLabel>{x(decision['defaultLabel'])}</defaultConnectorLabel>\n")
        for branch in decision.get("branches") or []:
            out.append("        <rules>\n")
            out.append(f"            <name>{x(branch.get('name', 'Rule'))}</name>\n")
            out.append("            <conditionLogic>and</conditionLogic>\n")
            cond = branch.get("when") or {}
            out.append("            <conditions>\n")
            # When the parent is a choice field, the runtime expects
            # `<fieldName>.selectedChoiceValues` and an elementReference to the choice api-name.
            left_field = cond.get("field", "")
            target_value = cond.get("value", "")
            choice_name = find_choice_name(spec, target_value)
            parent = spec.fields_by_name.get(left_field)
            is_choice = parent is not None and parent.field_type in ("Picklist", "Radio", "CheckboxGroup")
            if is_choice and choice_name:
                out.append(f"                <leftValueReference>{x(left_field)}.selectedChoiceValues</leftValueReference>\n")
                out.append(f"                <operator>{x(cond.get('operator', 'EqualTo'))}</operator>\n")
                out.append("                <rightValue>\n")
                out.append(f"                    <elementReference>{x(choice_name)}</elementReference>\n")
                out.append("                </rightValue>\n")
            else:
                out.append(f"                <leftValueReference>{x(left_field)}</leftValueReference>\n")
                out.append(f"                <operator>{x(cond.get('operator', 'EqualTo'))}</operator>\n")
                out.append(_render_value(spec, cond, indent="                "))
            out.append("            </conditions>\n")
            if branch.get("then"):
                out.append("            <connector>\n")
                out.append(f"                <targetReference>{x(branch['then'])}</targetReference>\n")
                out.append("            </connector>\n")
            out.append(f"            <label>{x(branch.get('label') or branch.get('name', 'Rule'))}</label>\n")
            out.append("        </rules>\n")
        out.append("    </decisions>\n")

    # loops (one)
    if loop and isinstance(loop, dict):
        out.append("    <loops>\n")
        if loop.get("description"):
            out.append(f"        <description>{x(loop['description'])}</description>\n")
        out.append(f"        <name>{x(loop.get('name', 'Loop'))}</name>\n")
        out.append(f"        <label>{x(loop.get('label') or loop.get('name', 'Loop'))}</label>\n")
        out.append("        <locationX>0</locationX>\n")
        out.append("        <locationY>0</locationY>\n")
        out.append(f"        <collectionReference>{x(loop.get('collection', ''))}</collectionReference>\n")
        out.append("        <iterationOrder>Asc</iterationOrder>\n")
        if loop.get("next"):
            out.append("        <nextValueConnector>\n")
            out.append(f"            <targetReference>{x(loop['next'])}</targetReference>\n")
            out.append("        </nextValueConnector>\n")
        out.append("    </loops>\n")

    # recordCreates
    for rc in creates:
        out.append("    <recordCreates>\n")
        out.append(f"        <name>{x(rc.get('name', 'Create'))}</name>\n")
        out.append(f"        <label>{x(rc.get('label') or rc.get('name', 'Create'))}</label>\n")
        out.append("        <locationX>0</locationX>\n")
        out.append("        <locationY>0</locationY>\n")
        if rc.get("next"):
            out.append("        <connector>\n")
            out.append(f"            <targetReference>{x(rc['next'])}</targetReference>\n")
            out.append("        </connector>\n")
        for ia in rc.get("inputAssignments") or []:
            out.append("        <inputAssignments>\n")
            out.append(f"            <field>{x(ia.get('field', ''))}</field>\n")
            out.append(_render_value(spec, ia, indent="            "))
            out.append("        </inputAssignments>\n")
        out.append(f"        <object>{x(rc.get('object', ''))}</object>\n")
        out.append("        <storeOutputAutomatically>true</storeOutputAutomatically>\n")
        out.append("    </recordCreates>\n")

    # recordLookups
    for rl in lookups:
        out.append("    <recordLookups>\n")
        out.append(f"        <name>{x(rl.get('name', 'Lookup'))}</name>\n")
        out.append(f"        <label>{x(rl.get('label') or rl.get('name', 'Lookup'))}</label>\n")
        out.append("        <locationX>0</locationX>\n")
        out.append("        <locationY>0</locationY>\n")
        out.append("        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>\n")
        if rl.get("next"):
            out.append("        <connector>\n")
            out.append(f"            <targetReference>{x(rl['next'])}</targetReference>\n")
            out.append("        </connector>\n")
        out.append("        <filterLogic>and</filterLogic>\n")
        for filt in rl.get("filters") or []:
            out.append("        <filters>\n")
            out.append(f"            <field>{x(filt.get('field', ''))}</field>\n")
            out.append(f"            <operator>{x(filt.get('operator', 'EqualTo'))}</operator>\n")
            out.append(_render_value(spec, filt, indent="            "))
            out.append("        </filters>\n")
        out.append(f"        <object>{x(rl.get('object', ''))}</object>\n")
        for oa in rl.get("outputAssignments") or []:
            out.append("        <outputAssignments>\n")
            out.append(f"            <assignToReference>{x(oa.get('assignTo', ''))}</assignToReference>\n")
            out.append(f"            <field>{x(oa.get('field', ''))}</field>\n")
            out.append("        </outputAssignments>\n")
        out.append("    </recordLookups>\n")

    # extra non-input variables
    for v in variables:
        if not isinstance(v, dict):
            continue
        name = v.get("name")
        if not name:
            continue
        var_type = v.get("type", "String")
        extra_vars_xml.append(
            "    <variables>\n"
            f"        <name>{x(name)}</name>\n"
            f"        <dataType>{x(var_type)}</dataType>\n"
            "        <isCollection>false</isCollection>\n"
            "        <isInput>false</isInput>\n"
            "        <isOutput>false</isOutput>\n"
            "    </variables>\n"
        )

    return "".join(out), extra_vars_xml


def post_screen_entry_point(spec: FormSpec) -> str | None:
    """The element name the last screen connects to, if postScreen is set."""
    if not spec.post_screen:
        return None
    decision = spec.post_screen.get("decision")
    if decision and decision.get("name"):
        return decision["name"]
    lookups = spec.post_screen.get("recordLookups") or []
    if lookups and lookups[0].get("name"):
        return lookups[0]["name"]
    loop = spec.post_screen.get("loop")
    if loop and loop.get("name"):
        return loop["name"]
    creates = spec.post_screen.get("recordCreates") or []
    if creates and creates[0].get("name"):
        return creates[0]["name"]
    return None


# ---- top-level XML --------------------------------------------------------


def build_xml(spec: FormSpec, flow_api_name: str) -> str:
    if not API_NAME_RE.match(flow_api_name):
        raise ValueError(
            f"FlowApiName '{flow_api_name}' is not a valid Salesforce API name "
            "(must match ^[A-Z][A-Za-z0-9_]*$)"
        )

    description = f"Generated from spec: {spec.title}"
    if spec.form_type:
        description += f" ({spec.form_type})"

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    if spec.incomplete_migration:
        out.append("<!-- ============================================================\n")
        out.append("     INCOMPLETE MIGRATION — this DataCaptureFlow was auto-migrated from a\n")
        out.append("     Field Service Mobile flow. The following source elements have NO Data\n")
        out.append("     Capture equivalent and were NOT fully migrated. Review and rebuild each\n")
        out.append("     in Flow Builder before relying on this form.\n")
        for e in spec.incomplete_migration:
            etype = _xml_comment_safe(str(e.get("type", "")))
            name = _xml_comment_safe(str(e.get("name", "")))
            reason = _xml_comment_safe(str(e.get("reason", "")))
            out.append(f"       - [{etype}] {name}: {reason}\n")
        out.append("     ============================================================ -->\n")
    out.append(f'<Flow xmlns="{NS}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')
    out.append("    <areMetricsLoggedToDataCloud>false</areMetricsLoggedToDataCloud>\n")

    # Choices block (sorted by name for stable output)
    for cname in sorted(spec.choices.keys()):
        out.append(render_choice(cname, spec.choices[cname]))

    # post-screen chunk + extra variables
    post_xml, extra_vars_xml = render_post_screen(spec)

    out.append(f"    <description>{x(description)}</description>\n")
    out.append("    <environments>Offline</environments>\n")
    out.append(f"    <interviewLabel>{x(spec.title)} {{!$Flow.CurrentDateTime}}</interviewLabel>\n")
    out.append(f"    <label>{x(spec.title)}</label>\n")
    out.append("    <processMetadataValues>\n")
    out.append("        <name>BuilderType</name>\n")
    out.append("        <value>\n")
    out.append("            <stringValue>LightningFlowBuilder</stringValue>\n")
    out.append("        </value>\n")
    out.append("    </processMetadataValues>\n")
    out.append("    <processMetadataValues>\n")
    out.append("        <name>CanvasMode</name>\n")
    out.append("        <value>\n")
    out.append("            <stringValue>AUTO_LAYOUT_CANVAS</stringValue>\n")
    out.append("        </value>\n")
    out.append("    </processMetadataValues>\n")
    out.append("    <processType>DataCaptureFlow</processType>\n")

    # post-screen elements (decisions / loops / lookups / creates) appear before screens
    out.append(post_xml)
    out.append(render_decisions(spec.decisions))

    # Screens
    post_entry = post_screen_entry_point(spec)
    for i, screen in enumerate(spec.screens):
        is_last = i == len(spec.screens) - 1
        # A source screen connector (to a decision or another screen) overrides fall-through.
        override = spec.screen_connectors.get(screen.label) or spec.screen_connectors.get(screen.name)
        if override:
            next_target = override
        elif is_last:
            next_target = post_entry
        else:
            next_target = spec.screens[i + 1].name
        out.append(render_screen(screen, spec, next_target=next_target))

    # Start
    first_screen = spec.screens[0]
    out.append("    <start>\n")
    out.append("        <locationX>0</locationX>\n")
    out.append("        <locationY>0</locationY>\n")
    out.append("        <connector>\n")
    out.append(f"            <targetReference>{x(first_screen.name)}</targetReference>\n")
    out.append("        </connector>\n")
    out.append("    </start>\n")

    out.append("    <status>Draft</status>\n")
    # Required input variables for any DataCaptureFlow
    for var_name in ("parentObjectType", "parentRecordId", "recordId"):
        out.append("    <variables>\n")
        out.append(f"        <name>{var_name}</name>\n")
        out.append("        <dataType>String</dataType>\n")
        out.append("        <isCollection>false</isCollection>\n")
        out.append("        <isInput>true</isInput>\n")
        out.append("        <isOutput>false</isOutput>\n")
        out.append("    </variables>\n")
    for v in extra_vars_xml:
        out.append(v)
    out.append("</Flow>\n")
    return "".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    in_path = Path(argv[1])
    flow_api_name = argv[2]
    out_path = Path(argv[3])

    data = json.loads(in_path.read_text(encoding="utf-8"))
    spec = parse_spec(data)
    xml = build_xml(spec, flow_api_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")

    total_fields = sum(1 for _ in _walk_fields([f for s in spec.screens for f in s.fields]))
    section_count = sum(len(s.sections or []) for s in spec.screens)
    print(f"Wrote {out_path}")
    print(f"  Flow: {flow_api_name}")
    print(f"  Title: {spec.title}")
    print(f"  Screens: {len(spec.screens)}")
    if section_count:
        print(f"  Sections: {section_count}")
    print(f"  Fields total (incl. repeater children): {total_fields}")
    print(f"  Choices: {len(spec.choices)}")
    if spec.post_screen:
        ps = spec.post_screen
        print(f"  postScreen: decision={'yes' if ps.get('decision') else 'no'}, "
              f"lookups={len(ps.get('recordLookups') or [])}, "
              f"loop={'yes' if ps.get('loop') else 'no'}, "
              f"creates={len(ps.get('recordCreates') or [])}, "
              f"vars={len(ps.get('variables') or [])}")
    if spec.warnings:
        print("  Warnings:")
        for w in spec.warnings:
            print(f"    - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
