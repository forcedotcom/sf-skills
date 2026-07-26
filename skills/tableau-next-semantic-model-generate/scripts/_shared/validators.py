"""Pre-POST validation engine for Tableau Next visualization JSON.

Runs 16 checks derived from:
- Common API error messages documented in SKILL.md
- The _ensure_encoding_field_styles / _clean_palette_schema logic in
  tabnext-tools-main/backend/lib/api_versions/v66_8.py
"""

import sys
from typing import Any, Dict, List, Optional, Tuple

VALID_MARK_TYPES = {"Bar", "Line", "Donut", "Circle", "Text", "Square"}

REQUIRED_FONT_KEYS = {
    "actionableHeaders",
    "axisTickLabels",
    "fieldLabels",
    "headers",
    "legendLabels",
    "markLabels",
    "marks",
}

REQUIRED_LINE_KEYS = {"axisLine", "fieldLabelDividerLine", "separatorLine", "zeroLine"}


class ValidationResult:
    __slots__ = ("ok", "rule", "message", "fix")

    def __init__(self, ok: bool, rule: str, message: str = "", fix: str = ""):
        self.ok = ok
        self.rule = rule
        self.message = message
        self.fix = fix

    def __repr__(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        return f"[{status}] {self.rule}: {self.message}"


def _walk_collect_encoding_field_keys(obj: Any, out: set) -> None:
    """Collect fieldKey values from every encodings[] list under a marks/visual subtree."""
    if isinstance(obj, dict):
        enc = obj.get("encodings")
        if isinstance(enc, list):
            for e in enc:
                if isinstance(e, dict):
                    fk = e.get("fieldKey")
                    if fk:
                        out.add(fk)
        for v in obj.values():
            _walk_collect_encoding_field_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_collect_encoding_field_keys(item, out)


def _check_encoding_field_refs(p: dict) -> List[ValidationResult]:
    """Optional strict check: every encoding fieldKey exists in root fields (generated payloads)."""
    fields = p.get("fields", {})
    if not isinstance(fields, dict):
        return [ValidationResult(True, "encoding_field_refs", "Skipped (fields not a dict).")]
    keys: set = set()
    _walk_collect_encoding_field_keys(p.get("visualSpecification", {}).get("marks"), keys)
    missing = sorted(k for k in keys if k not in fields)
    if missing:
        return [ValidationResult(
            False,
            "encoding_field_refs",
            f"encoding fieldKey(s) missing from fields: {', '.join(missing)}",
            "Define each encoded field under root fields or remove orphan encodings.",
        )]
    return [ValidationResult(True, "encoding_field_refs", "All encoding fieldKeys exist in fields.")]


def validate(payload: dict, *, strict_encoding_field_refs: bool = False) -> List[ValidationResult]:
    """Run all validation rules and return a list of results.

    If strict_encoding_field_refs is True, also require every marks encoding fieldKey
    to appear in root fields (useful for generated JSON; vendor exports may omit keys).
    """
    results: List[ValidationResult] = []
    results.extend(_check_root_fields(payload))
    results.extend(_check_view(payload))
    results.extend(_check_visual_spec_fields(payload))
    results.extend(_check_marks_structure(payload))
    results.extend(_check_style(payload))
    results.extend(_check_encoding_fields(payload))
    results.extend(_check_palette_schema(payload))
    results.extend(_check_size_encoding_support(payload))
    if strict_encoding_field_refs:
        results.extend(_check_encoding_field_refs(payload))
    return results


def is_valid(payload: dict, *, strict_encoding_field_refs: bool = False) -> Tuple[bool, List[ValidationResult]]:
    """Convenience: returns (all_passed, results)."""
    results = validate(payload, strict_encoding_field_refs=strict_encoding_field_refs)
    ok = all(r.ok for r in results)
    return ok, results


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def _check_root_fields(p: dict) -> List[ValidationResult]:
    """Rule 1: Required root fields."""
    required = ["name", "label", "dataSource", "workspace", "fields", "visualSpecification", "interactions", "view"]
    missing = [k for k in required if k not in p]
    if missing:
        return [ValidationResult(
            False, "root_fields",
            f"Missing required root field(s): {', '.join(missing)}",
            "Add the missing keys to the top level of the payload.",
        )]
    return [ValidationResult(True, "root_fields", "All required root fields present.")]


def _check_view(p: dict) -> List[ValidationResult]:
    """Rule 2: view structure."""
    view = p.get("view")
    if not isinstance(view, dict):
        return [ValidationResult(False, "view", "Missing or invalid 'view' object.", "Add view: {label, name, viewSpecification}.")]
    missing = []
    for k in ("label", "name", "viewSpecification"):
        if k not in view:
            missing.append(k)
    vs = view.get("viewSpecification")
    if not isinstance(vs, dict):
        return [ValidationResult(
            False, "view",
            "viewSpecification is missing or not an object.",
            "Add viewSpecification as an object with at least sortOrders.",
        )]
    if "sortOrders" not in vs:
        missing.append("viewSpecification.sortOrders")
    # API v66.12: legacy top-level viewSpecification.filters (array) is rejected for all layouts.
    if "filters" in vs:
        return [ValidationResult(
            False, "view",
            "viewSpecification must not use legacy top-level 'filters' (disallowed at API v66.12).",
            "Use viewSpecification.filter with nested filters array instead, or omit when empty (Flow).",
        )]
    if missing:
        return [ValidationResult(
            False, "view",
            f"view missing: {', '.join(missing)}",
            "Ensure view has label, name, and viewSpecification with sortOrders.",
        )]
    return [ValidationResult(True, "view", "view structure is valid.")]


def _check_visual_spec_fields(p: dict) -> List[ValidationResult]:
    """Rule 3: visualSpecification required keys."""
    vs = p.get("visualSpecification", {})
    if not isinstance(vs, dict):
        return [ValidationResult(False, "vis_spec", "visualSpecification is missing or not an object.")]
    layout = vs.get("layout", "Vizql")
    if layout == "Table":
        required = ["marks", "style", "rows", "layout"]
    elif layout == "Map":
        required = ["marks", "style", "layout", "locations"]
    elif layout == "Flow":
        required = ["marks", "style", "layout", "levels", "link"]
    elif layout == "Radial":
        # Radial vizzes (262.10 / v67.0): rings + slices replace columns/rows.
        # At least one must be present (caller content checked elsewhere).
        required = ["marks", "style", "layout", "rings", "slices"]
    else:
        required = ["marks", "style", "measureValues", "referenceLines", "forecasts", "layout"]
    missing = [k for k in required if k not in vs]
    if missing:
        return [ValidationResult(
            False, "vis_spec",
            f"visualSpecification missing: {', '.join(missing)}",
            "Add the missing keys (even empty objects/arrays) to visualSpecification.",
        )]
    return [ValidationResult(True, "vis_spec", "visualSpecification has all required keys.")]


def _check_marks_structure(p: dict) -> List[ValidationResult]:
    """Rules 4-7: marks structure checks."""
    results: List[ValidationResult] = []
    layout = p.get("visualSpecification", {}).get("layout", "Vizql")
    marks = p.get("visualSpecification", {}).get("marks", {})

    # Rule 4: No marks.ALL (old v65.11)
    if "ALL" in marks:
        results.append(ValidationResult(
            False, "marks_no_ALL",
            "marks.ALL found — this is the old v65.11 format.",
            "Replace marks.ALL with marks.panes + marks.headers.",
        ))
    else:
        results.append(ValidationResult(True, "marks_no_ALL", "No legacy marks.ALL key."))

    if layout == "Flow":
        mf = marks.get("fields")
        ml = marks.get("links")
        mn = marks.get("nodes")
        if not isinstance(mf, dict) or not mf:
            results.append(ValidationResult(
                False, "marks_flow_fields",
                "Flow layout requires non-empty marks.fields (Bar per level).",
            ))
        else:
            results.append(ValidationResult(True, "marks_flow_fields", "marks.fields present for Flow."))
        if not isinstance(ml, dict):
            results.append(ValidationResult(
                False, "marks_flow_links",
                "Flow layout requires marks.links (Line mark for flows).",
            ))
        else:
            lt = ml.get("type")
            if lt and lt not in VALID_MARK_TYPES:
                results.append(ValidationResult(
                    False, "mark_type",
                    f"marks.links.type '{lt}' is not valid.",
                ))
            elif lt:
                results.append(ValidationResult(True, "mark_type", f"marks.links.type '{lt}' is valid."))
            if "stack" not in ml:
                results.append(ValidationResult(
                    False, "marks_stack",
                    "marks.links.stack is missing.",
                    'Add "stack": {"isAutomatic": true, "isStacked": false}.',
                ))
            else:
                results.append(ValidationResult(True, "marks_stack", "marks.links.stack present."))
        if not isinstance(mn, dict):
            results.append(ValidationResult(
                False, "marks_flow_nodes",
                "Flow layout requires marks.nodes.",
            ))
        elif "stack" not in mn:
            results.append(ValidationResult(
                False, "marks_stack",
                "marks.nodes.stack is missing.",
            ))
        else:
            results.append(ValidationResult(True, "marks_stack", "marks.nodes.stack present."))
        if isinstance(mf, dict):
            for fk, fd in mf.items():
                if not isinstance(fd, dict):
                    continue
                t = fd.get("type")
                if t and t not in VALID_MARK_TYPES:
                    results.append(ValidationResult(
                        False, "mark_type",
                        f"marks.fields.{fk}.type '{t}' is not valid.",
                    ))
                if "stack" not in fd:
                    results.append(ValidationResult(
                        False, "marks_stack",
                        f"marks.fields.{fk}.stack is missing.",
                    ))
        return results

    if layout == "Radial":
        has_panes = "panes" in marks
        if not has_panes:
            results.append(ValidationResult(
                False, "marks_panes_headers",
                "Radial layout requires marks.panes.",
            ))
        else:
            results.append(ValidationResult(True, "marks_panes_headers", "Radial layout has marks.panes."))
        panes = marks.get("panes", {})
        mark_type = panes.get("type")
        if mark_type and mark_type not in VALID_MARK_TYPES:
            results.append(ValidationResult(
                False, "mark_type",
                f"marks.panes.type '{mark_type}' is not valid. Must be one of: {', '.join(sorted(VALID_MARK_TYPES))}",
            ))
        elif mark_type:
            results.append(ValidationResult(True, "mark_type", f"marks.panes.type '{mark_type}' is valid."))
        if has_panes and "stack" not in panes:
            results.append(ValidationResult(
                False, "marks_stack",
                "marks.panes.stack is missing.",
                'Add "stack": {"isAutomatic": true, "isStacked": true}.',
            ))
        elif has_panes:
            results.append(ValidationResult(True, "marks_stack", "marks.panes.stack present."))
        hdr = marks.get("headers")
        if isinstance(hdr, dict) and hdr:
            results.append(ValidationResult(
                False, "radial_marks_no_headers",
                "Radial layout must not include marks.headers (live New_Charts exports omit it).",
                "Remove marks.headers; keep marks.panes only.",
            ))
        else:
            results.append(ValidationResult(True, "radial_marks_no_headers", "Radial layout has no marks.headers."))
        # Radial-specific shape: rings/slices must reference defined fields.
        vs = p.get("visualSpecification", {})
        all_fields = p.get("fields", {})
        rings = vs.get("rings") or []
        slices = vs.get("slices") or []
        if not rings and not slices:
            results.append(ValidationResult(
                False, "radial_rings_or_slices",
                "Radial layout requires at least one of rings or slices to be non-empty.",
                "Populate visualSpecification.rings or visualSpecification.slices with field keys.",
            ))
        else:
            results.append(ValidationResult(True, "radial_rings_or_slices", "Radial layout has rings or slices populated."))
        unresolved = [fk for fk in list(rings) + list(slices) if fk not in all_fields]
        if unresolved:
            results.append(ValidationResult(
                False, "radial_unknown_field_keys",
                f"rings/slices reference unknown field keys: {', '.join(unresolved)}",
                "Ensure every key in rings/slices exists under top-level 'fields'.",
            ))
        else:
            results.append(ValidationResult(True, "radial_unknown_field_keys", "rings/slices reference defined fields."))
        return results

    if layout == "Map":
        has_panes = "panes" in marks
        if not has_panes:
            results.append(ValidationResult(
                False, "marks_panes_headers",
                "Map layout requires marks.panes.",
            ))
        else:
            results.append(ValidationResult(
                True, "marks_panes_headers",
                "Map layout has marks.panes.",
            ))
        panes = marks.get("panes", {})
        mark_type = panes.get("type")
        if mark_type and mark_type not in VALID_MARK_TYPES:
            results.append(ValidationResult(
                False, "mark_type",
                f"marks.panes.type '{mark_type}' is not valid. Must be one of: {', '.join(sorted(VALID_MARK_TYPES))}",
            ))
        elif mark_type:
            results.append(ValidationResult(True, "mark_type", f"marks.panes.type '{mark_type}' is valid."))
        if has_panes and "stack" not in panes:
            results.append(ValidationResult(
                False, "marks_stack",
                "marks.panes.stack is missing.",
                'Add "stack": {"isAutomatic": true, "isStacked": false}.',
            ))
        elif has_panes:
            results.append(ValidationResult(True, "marks_stack", "marks.panes.stack present."))
        hdr = marks.get("headers")
        if isinstance(hdr, dict) and hdr:
            results.append(ValidationResult(
                False, "map_marks_no_headers",
                "Map layout must not include marks.headers (API v66.12 JSON parser rejects it).",
                "Remove marks.headers; keep marks.fields and marks.panes only.",
            ))
        else:
            results.append(ValidationResult(True, "map_marks_no_headers", "Map layout has no marks.headers."))
        return results

    # Rule 5: panes + headers present (Vizql / standard)
    has_panes = "panes" in marks
    has_headers = "headers" in marks
    if not has_panes or not has_headers:
        missing = []
        if not has_panes:
            missing.append("panes")
        if not has_headers:
            missing.append("headers")
        results.append(ValidationResult(
            False, "marks_panes_headers",
            f"marks missing: {', '.join(missing)}",
            "marks must have both panes and headers.",
        ))
    else:
        results.append(ValidationResult(True, "marks_panes_headers", "marks.panes and marks.headers present."))

    # Rule 6: valid mark type
    panes = marks.get("panes", {})
    mark_type = panes.get("type")
    if mark_type and mark_type not in VALID_MARK_TYPES:
        results.append(ValidationResult(
            False, "mark_type",
            f"marks.panes.type '{mark_type}' is not valid. Must be one of: {', '.join(sorted(VALID_MARK_TYPES))}",
        ))
    elif mark_type:
        results.append(ValidationResult(True, "mark_type", f"marks.panes.type '{mark_type}' is valid."))

    # Rule 7: stack present
    if has_panes and "stack" not in panes:
        results.append(ValidationResult(
            False, "marks_stack",
            "marks.panes.stack is missing.",
            'Add "stack": {"isAutomatic": true, "isStacked": true}.',
        ))
    elif has_panes:
        results.append(ValidationResult(True, "marks_stack", "marks.panes.stack present."))

    headers_marks = marks.get("headers", {})
    if has_headers and isinstance(headers_marks, dict) and "stack" not in headers_marks:
        results.append(ValidationResult(
            False, "marks_headers_stack",
            "marks.headers.stack is missing (required at API v66.12).",
            'Add "stack": {"isAutomatic": true, "isStacked": false} alongside type and encodings.',
        ))
    elif has_headers and isinstance(headers_marks, dict):
        results.append(ValidationResult(True, "marks_headers_stack", "marks.headers.stack present."))

    return results


def _check_style(p: dict) -> List[ValidationResult]:
    """Rules 8-11: style checks."""
    results: List[ValidationResult] = []
    style = p.get("visualSpecification", {}).get("style", {})
    layout = p.get("visualSpecification", {}).get("layout", "Vizql")

    # Rule 8: style.marks range (Vizql: panes; Map: panes; Flow: fields + links + nodes)
    marks_style = style.get("marks", {})
    if layout == "Flow":
        sm_fields = marks_style.get("fields", {})
        if not isinstance(sm_fields, dict) or not sm_fields:
            results.append(ValidationResult(
                False, "style_range",
                "Flow layout requires style.marks.fields with range per level.",
            ))
        else:
            missing_range = [k for k, v in sm_fields.items() if isinstance(v, dict) and "range" not in v]
            if missing_range:
                results.append(ValidationResult(
                    False, "style_range",
                    f"style.marks.fields missing range for: {', '.join(missing_range)}",
                ))
            else:
                results.append(ValidationResult(True, "style_range", "style.marks.fields ranges present for Flow."))
        for key in ("links", "nodes"):
            sub = marks_style.get(key, {})
            if isinstance(sub, dict) and "range" not in sub:
                results.append(ValidationResult(
                    False, "style_range",
                    f"style.marks.{key}.range is missing (required for Flow).",
                ))
            elif isinstance(sub, dict):
                results.append(ValidationResult(True, "style_range", f"style.marks.{key}.range present."))
    else:
        panes_style = marks_style.get("panes", {})
        if "range" not in panes_style:
            results.append(ValidationResult(
                False, "style_range",
                "style.marks.panes.range is missing (required for this layout).",
                'Add "range": {"reverse": false} (or true for Bar/Donut).',
            ))
        else:
            results.append(ValidationResult(True, "style_range", "style.marks.panes.range present."))

        if layout in ("Vizql", "Table"):
            hdr_style = marks_style.get("headers", {})
            if not isinstance(hdr_style, dict) or "range" not in hdr_style:
                results.append(ValidationResult(
                    False, "style_marks_headers_range",
                    "style.marks.headers.range is missing (required for Vizql/Table at API v66.12).",
                    'Add "range": {"reverse": true|false} under style.marks.headers.',
                ))
            else:
                results.append(ValidationResult(True, "style_marks_headers_range", "style.marks.headers.range present."))
            if not isinstance(hdr_style, dict) or "size" not in hdr_style:
                results.append(ValidationResult(
                    False, "style_marks_headers_size",
                    "style.marks.headers.size is missing (required for Vizql/Table at API v66.12).",
                    'Add size with isAutomatic, type, and value under style.marks.headers.',
                ))
            else:
                results.append(ValidationResult(True, "style_marks_headers_size", "style.marks.headers.size present."))

    # Rule 9: style.axis exists (non-Table, non-Map, non-Flow) / forbidden keys for Table
    if layout == "Table":
        forbidden_in_table = {"axis", "referenceLines", "showDataPlaceholder"}
        present = forbidden_in_table & set(style.keys())
        if present:
            results.append(ValidationResult(
                False, "style_table_forbidden",
                f"Table style has forbidden key(s): {', '.join(sorted(present))}",
                "Remove axis, referenceLines, showDataPlaceholder from Table style.",
            ))
        else:
            results.append(ValidationResult(True, "style_table_forbidden", "Table style has no forbidden keys."))
    elif layout in ("Map", "Flow", "Radial"):
        results.append(ValidationResult(True, "style_axis", f"{layout} layout omits style.axis (expected)."))
    elif "axis" not in style:
        results.append(ValidationResult(
            False, "style_axis",
            "style.axis is missing (required even for Donut — use {\"fields\": {}}).",
            'Add "axis": {"fields": {}}.',
        ))
    else:
        results.append(ValidationResult(True, "style_axis", "style.axis present."))

    # Rule 10: fonts
    fonts = style.get("fonts", {})
    missing_fonts = REQUIRED_FONT_KEYS - set(fonts.keys())
    if missing_fonts:
        results.append(ValidationResult(
            False, "style_fonts",
            f"style.fonts missing key(s): {', '.join(sorted(missing_fonts))}",
            "All 7 font keys are required.",
        ))
    else:
        results.append(ValidationResult(True, "style_fonts", "style.fonts has all required keys."))

    # Rule 11: lines
    lines = style.get("lines", {})
    missing_lines = REQUIRED_LINE_KEYS - set(lines.keys())
    if missing_lines:
        results.append(ValidationResult(
            False, "style_lines",
            f"style.lines missing key(s): {', '.join(sorted(missing_lines))}",
            "All 4 line keys are required.",
        ))
    else:
        results.append(ValidationResult(True, "style_lines", "style.lines has all required keys."))

    return results


def _flow_encoding_field_keys(marks: dict) -> set:
    """Collect fieldKeys used in encodings for Flow marks (fields, links, nodes)."""
    keys: set = set()
    mf = marks.get("fields") or {}
    if isinstance(mf, dict):
        for fd in mf.values():
            if isinstance(fd, dict):
                for e in fd.get("encodings") or []:
                    if isinstance(e, dict) and e.get("fieldKey"):
                        keys.add(e["fieldKey"])
    for key in ("links", "nodes"):
        block = marks.get(key)
        if isinstance(block, dict):
            for e in block.get("encodings") or []:
                if isinstance(e, dict) and e.get("fieldKey"):
                    keys.add(e["fieldKey"])
    return keys


def _check_encoding_fields(p: dict) -> List[ValidationResult]:
    """Rules 12-14: encoding / header field checks."""
    results: List[ValidationResult] = []
    fields = p.get("fields", {})
    vs = p.get("visualSpecification", {})
    style = vs.get("style", {})
    columns = vs.get("columns", [])
    rows = vs.get("rows", [])
    layout = vs.get("layout", "Vizql")

    marks = vs.get("marks", {})
    panes = marks.get("panes", {})
    encodings = panes.get("encodings", [])
    if layout == "Flow":
        encoding_keys = _flow_encoding_field_keys(marks)
    else:
        encoding_keys = {e.get("fieldKey") for e in encodings if isinstance(e, dict) and e.get("fieldKey")}

    enc_style_fields = style.get("encodings", {}).get("fields", {})
    hdr_style_fields = style.get("headers", {}).get("fields", {})
    shelf_keys = set(columns) | set(rows)

    # Rule 12: every measure in encodings has style.encodings.fields entry
    missing_enc = []
    for fk in encoding_keys:
        fdef = fields.get(fk, {})
        if fdef.get("role") == "Measure" and fk not in enc_style_fields:
            missing_enc.append(fk)
    if missing_enc:
        results.append(ValidationResult(
            False, "enc_measure_style",
            f"Measure field(s) in encodings missing from style.encodings.fields: {', '.join(missing_enc)}",
            'Add {"defaults": {"format": {}}} for each.',
        ))
    else:
        results.append(ValidationResult(True, "enc_measure_style", "All encoded measures have style entries."))

    # Rule 13: style.encodings.fields must not contain dimension fields UNLESS they only have color configuration
    # (dimensions with Color encoding need color palette configuration in style.encodings.fields)
    # The API accepts dimensions in encodings.fields if they have color configuration
    bad_dims = []
    for fk in enc_style_fields:
        fdef = fields.get(fk, {})
        if fdef.get("role") == "Dimension" and fdef.get("type", "Field") == "Field":
            enc_entry = enc_style_fields.get(fk, {})
            # Allow dimensions if they have color configuration (for Color encoding)
            # Dimensions with Color encoding need color palette in style.encodings.fields
            has_colors = "colors" in enc_entry
            if not has_colors:
                # Dimension without colors shouldn't be in encodings.fields
                bad_dims.append(fk)
    if bad_dims:
        results.append(ValidationResult(
            False, "enc_no_dims",
            f"Dimension field(s) in style.encodings.fields: {', '.join(bad_dims)}",
            "Remove all dimension fields from style.encodings.fields — only measures belong there (dimensions with Color encoding may have color palette config).",
        ))
    else:
        results.append(ValidationResult(True, "enc_no_dims", "style.encodings.fields contains no invalid dimensions."))

    # Rule 14: style.headers.fields only for dims on rows/columns
    bad_hdrs = []
    for fk in hdr_style_fields:
        if fk not in shelf_keys:
            bad_hdrs.append(fk)
    if bad_hdrs:
        results.append(ValidationResult(
            False, "hdr_only_shelf_dims",
            f"style.headers.fields contains key(s) not on rows/columns: {', '.join(bad_hdrs)}",
            "Only dimensions explicitly on rows or columns belong in style.headers.fields.",
        ))
    else:
        results.append(ValidationResult(True, "hdr_only_shelf_dims", "style.headers.fields only has shelf dimensions."))

    # Rule 15: Fields cannot be BOTH on shelves AND in encodings (API limitation)
    shelf_and_encoding = shelf_keys & encoding_keys
    if shelf_and_encoding:
        results.append(ValidationResult(
            False, "shelf_and_encoding",
            f"Field(s) cannot be both on shelves AND in encodings: {', '.join(shelf_and_encoding)}. "
            "Use a separate field for the encoding that references the same measure.",
            "Create duplicate field definitions (e.g., F2 on rows, F3 in encoding, both reference same measure).",
        ))
    else:
        results.append(ValidationResult(True, "shelf_and_encoding", "No fields are both on shelves and in encodings."))

    # Rule 16: Donut charts must have Color(dimension) + Angle(measure) encodings.
    # Skip for Radial: Radial Donuts use rings/slices instead of Angle, and Color may
    # legitimately be on a measure (e.g. radial_pie_color_measure / radial_heatmap).
    mark_type = panes.get("type") if layout not in ("Flow", "Radial") else None
    if mark_type == "Donut":
        encoding_types = {e.get("type"): e.get("fieldKey") for e in encodings if isinstance(e, dict) and "fieldKey" in e}
        has_color_dim = False
        has_angle_measure = False
        
        for enc_type, fk in encoding_types.items():
            if enc_type == "Color" and fk in fields:
                fdef = fields.get(fk, {})
                if fdef.get("role") == "Dimension":
                    has_color_dim = True
            elif enc_type == "Angle" and fk in fields:
                fdef = fields.get(fk, {})
                if fdef.get("role") == "Measure":
                    has_angle_measure = True
        
        if not has_color_dim:
            results.append(ValidationResult(
                False, "donut_color_required",
                "Donut charts require a Color encoding with a dimension field.",
                "Add Color encoding with a dimension field (e.g., --encoding F1 type=Color where F1 is Dimension).",
            ))
        else:
            results.append(ValidationResult(True, "donut_color_required", "Donut has Color(dimension) encoding."))
        
        if not has_angle_measure:
            results.append(ValidationResult(
                False, "donut_angle_required",
                "Donut charts require an Angle encoding with a measure field.",
                "Add Angle encoding with a measure field (e.g., --encoding F2 type=Angle where F2 is Measure).",
            ))
        else:
            results.append(ValidationResult(True, "donut_angle_required", "Donut has Angle(measure) encoding."))

    return results


def _check_size_encoding_support(p: dict) -> List[ValidationResult]:
    """Rule 17: Size encoding support check."""
    results: List[ValidationResult] = []
    vs = p.get("visualSpecification", {})
    marks = vs.get("marks", {})
    panes = marks.get("panes", {})
    encodings = panes.get("encodings", [])
    mark_type = panes.get("type")
    
    # Check if Size encoding is used
    has_size_encoding = any(e.get("type") == "Size" for e in encodings if isinstance(e, dict))
    
    if has_size_encoding:
        # Size encoding is not supported for Line and Donut chart types
        if mark_type == "Line":
            results.append(ValidationResult(
                False, "size_encoding_line",
                "Size encoding is not supported for Line charts.",
                "Remove Size encoding from Line chart or use a different chart type (e.g., Scatter).",
            ))
        elif mark_type == "Donut":
            results.append(ValidationResult(
                False, "size_encoding_donut",
                "Size encoding is not supported for Donut charts.",
                "Remove Size encoding from Donut chart.",
            ))
        else:
            results.append(ValidationResult(True, "size_encoding_support", f"Size encoding is supported for {mark_type} charts."))
    
    return results


def _check_palette_schema(p: dict) -> List[ValidationResult]:
    """Rules 15-16: palette step validation."""
    results: List[ValidationResult] = []
    enc_fields = (
        p.get("visualSpecification", {})
        .get("style", {})
        .get("encodings", {})
        .get("fields", {})
    )
    found_palette = False
    for fk, fcfg in enc_fields.items():
        if not isinstance(fcfg, dict):
            continue
        colors = fcfg.get("colors")
        if not isinstance(colors, dict):
            continue
        palette = colors.get("palette")
        if not isinstance(palette, dict):
            continue
        found_palette = True
        has_middle = "middle" in palette
        if has_middle:
            # Rule 16: diverging — empty startToEndSteps is allowed (product exports); populated or wrong type is not
            stes = palette.get("startToEndSteps", None)
            bad_stes = False
            if stes is not None:
                if isinstance(stes, list):
                    bad_stes = len(stes) > 0
                else:
                    bad_stes = True
            if bad_stes:
                results.append(ValidationResult(
                    False, "palette_diverging",
                    f"Field {fk}: diverging palette has invalid 'startToEndSteps' (use startToMiddleSteps + middleToEndSteps).",
                    "Remove non-empty or non-list startToEndSteps; use startToMiddleSteps + middleToEndSteps for diverging palettes.",
                ))
            else:
                results.append(ValidationResult(True, "palette_diverging", f"Field {fk}: diverging palette is valid."))
        else:
            # Rule 15: sequential
            bad_keys = [k for k in ("startToMiddleSteps", "middleToEndSteps") if k in palette]
            if bad_keys:
                results.append(ValidationResult(
                    False, "palette_sequential",
                    f"Field {fk}: sequential palette has invalid key(s): {', '.join(bad_keys)}.",
                    "Remove those keys; use only startToEndSteps for 2-color palettes.",
                ))
            else:
                results.append(ValidationResult(True, "palette_sequential", f"Field {fk}: sequential palette is valid."))

    if not found_palette:
        results.append(ValidationResult(True, "palette_none", "No color palettes to validate."))

    return results


def validate_field_roles(
    viz_spec: Dict[str, Any],
    sdm_fields: Dict[str, Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Cross-check each field's SDM role against the role its template slot needs.

    The server has **no field-role validation** — it accepts a Text dimension
    in a measure slot (and vice-versa) and then fails opaquely at query/render
    time, collapsing to ``UNKNOWN_EXCEPTION`` with only an ErrorId. This catches
    the mismatch client-side, before POST, with an actionable message.

    The check is advisory-strict: it blocks a clear role mismatch (a Dimension
    SDM field used in a Measure slot, or a Measure field in a Dimension slot),
    but if a field's role is not discoverable for the SDM shape it *warns*
    (stderr) and passes, so it never blocks a legitimate spec.

    Args:
        viz_spec: a single viz spec (``template`` + ``fields: {slot: sdm_field}``).
        sdm_fields: discovered SDM field metadata (from ``discover_sdm_fields``);
            each value carries ``role`` ("Dimension"/"Measure") and ``dataType``.

    Returns:
        (is_valid, error_message). error_message names the field, its real SDM
        role, and the slot it was misused in.
    """
    from .viz_templates import get_template

    template_name = viz_spec.get("template")
    template = get_template(template_name) if template_name else None
    if not template:
        # Field-name validation already reported the unknown/missing template.
        return True, None

    slot_defs: Dict[str, Any] = {}
    slot_defs.update(template.get("required_fields", {}) or {})
    slot_defs.update(template.get("optional_fields", {}) or {})

    viz_name = viz_spec.get("name", "unknown")

    for slot, sdm_field_name in viz_spec.get("fields", {}).items():
        slot_def = slot_defs.get(slot)
        if not slot_def:
            continue  # unknown slot -> handled by validate_viz_spec_fields
        expected_role = slot_def.get("role")
        if not expected_role:
            continue  # slot has no role requirement

        field_meta = sdm_fields.get(sdm_field_name)
        if not field_meta:
            continue  # field existence handled by validate_viz_specs

        actual_role = field_meta.get("role")
        if not actual_role:
            # Role not discoverable for this SDM shape -> warn, do not block.
            print(
                f"⚠ Warning: could not determine SDM role for field "
                f"'{sdm_field_name}' (slot '{slot}') in visualization "
                f"'{viz_name}'; skipping role check.",
                file=sys.stderr,
            )
            continue

        if actual_role != expected_role:
            data_type = field_meta.get("dataType") or "unknown type"
            error_msg = (
                f"✗ Error: Field-role mismatch in visualization '{viz_name}':\n"
                f"  Field '{sdm_field_name}' is a {actual_role} ({data_type}) "
                f"in the SDM, but slot '{slot}' (template '{template_name}') "
                f"requires a {expected_role}.\n"
                f"  Fix: use a {expected_role}-role field in the '{slot}' slot. "
                f"(The server would otherwise accept this and fail opaquely with "
                f"UNKNOWN_EXCEPTION.)"
            )
            return False, error_msg

    return True, None


def validate_viz_specs(
    viz_specs: List[Dict[str, Any]],
    sdm_fields: Dict[str, Dict[str, Any]]
) -> bool:
    """Validate that visualization specs use correct field names and reference valid SDM fields.

    First validates field names against template definitions, then validates
    that SDM field names exist in the provided SDM fields dictionary, then
    cross-checks each field's SDM role against the role its template slot needs.

    Args:
        viz_specs: List of visualization specifications
        sdm_fields: Dict of available SDM fields (from discover_sdm_fields)

    Returns:
        True if all specs are valid, False otherwise

    Note:
        Requires viz_templates.validate_viz_spec_fields to be imported
    """
    from .viz_templates import validate_viz_spec_fields

    # First, validate field names against template definitions
    for viz_spec in viz_specs:
        is_valid, error_msg = validate_viz_spec_fields(viz_spec)
        if not is_valid:
            print(error_msg, file=sys.stderr)
            return False

    # Then, validate that SDM field names exist
    for viz_spec in viz_specs:
        fields = viz_spec.get("fields", {})
        for template_field, sdm_field_name in fields.items():
            if sdm_field_name not in sdm_fields:
                print(
                    f"✗ Error: Field '{sdm_field_name}' not found in SDM for visualization '{viz_spec.get('name', 'unknown')}'",
                    file=sys.stderr
                )
                return False

    # Finally, cross-check field roles against the SDM (reject Text-dim-as-measure etc.)
    for viz_spec in viz_specs:
        is_valid, error_msg = validate_field_roles(viz_spec, sdm_fields)
        if not is_valid:
            print(error_msg, file=sys.stderr)
            return False

    return True


def get_pattern_filter_requirements(pattern: str) -> Optional[int]:
    """Get required number of filters for a dashboard pattern.
    
    Args:
        pattern: Dashboard pattern name (e.g., "f_layout", "z_layout")
        
    Returns:
        Required number of filters, or None if pattern not found
        
    Note:
        Requires dashboard_patterns.PATTERN_REQUIREMENTS to be imported
    """
    from .dashboard_patterns import PATTERN_REQUIREMENTS
    
    if pattern not in PATTERN_REQUIREMENTS:
        return None
    
    req = PATTERN_REQUIREMENTS[pattern]
    return req["filters"].get("slots") or req["filters"].get("recommended")
