#!/usr/bin/env python3
"""WI-10 — Render a human-readable migration summary (migration-summary.md)
from the spec JSON produced by convert_to_dc_spec.py.

Deterministic and offline: reads a local JSON file, writes a local markdown
file. Emits no AI-generated prose (NFR-003) — AI content belongs only inside
the labeled Advisory placeholder. Status indicators are text prefixes, never
color (NFR-006).

Usage: generate_summary.py <spec.json> <output.md>
Exit:  0 success | 1 unreadable/invalid spec JSON | 2 usage error
"""
import json
import sys
from typing import Any, Dict, List


AGX_NOTE = (
    "- **AGX cards / actions:** A DataCaptureFlow has no user-facing action "
    "buttons; the only action a DC flow can invoke is an `AGX_FLOW` action. "
    "Button-driven FSM logic (`PlainButtons`) has no DC equivalent and is "
    "dropped — redesign it in Flow Builder. "
    "See `references/fsm-dc-capability-catalog.md`.")

LDS_WARNING = (
    "DataCaptureFlow forms are offline-first and rely on Lightning Data Service "
    "with Briefcase priming. Any object or field the migrated flow reads or "
    "writes must be added to the Briefcase and have correct FLS/sharing, or it "
    "will be unavailable on-device. Verify Briefcase, FLS, and OWD before "
    "activating. See `configure-field-service-mobile` and "
    "`references/migration-checklist.md`.")


def load_spec(path: str) -> Dict[str, Any]:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[ERROR] Cannot read spec JSON '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def _incomplete_names(spec: Dict[str, Any]) -> set:
    return {e["name"] for e in spec.get("_incompleteMigration", [])}


def field_status(field: Dict[str, Any], incomplete_names: set) -> str:
    label = field.get("fieldLabel", "")
    if label.startswith("[UNSUPPORTED:") or field.get("fieldName") in incomplete_names:
        return "[ERROR]"
    if field.get("_migrationNote"):
        return "[WARNING]"
    return "[OK]"


def _note_for(field: Dict[str, Any]) -> str:
    note = field.get("_migrationNote", "")
    if note:
        return note.replace("\n", " ").strip()
    return "migrated"


def render_mapping_table(spec: Dict[str, Any]) -> str:
    names = _incomplete_names(spec)
    lines = ["## Component Mapping", "",
             "| Component | Type | Status | Notes |",
             "|---|---|---|---|"]
    for fields in spec.get("screens", {}).values():
        for f in fields:
            lines.append(
                f"| {f.get('fieldName', '')} | {f.get('fieldType', '')} "
                f"| {field_status(f, names)} | {_note_for(f)} |")
    lines.append("")
    return "\n".join(lines)


def render_conditional_logic(spec: Dict[str, Any]) -> str:
    lines = ["## Conditional Logic", "",
             "| Construct | Migration status | Notes |", "|---|---|---|"]
    rows = 0
    for c in spec.get("_collapsedDecisions", []):
        target = c.get("section") or c.get("field") or "field visibility"
        fields = ", ".join(c.get("fields", []))
        lines.append(
            f"| Decision `{c.get('decision', '')}` | [OK] collapsed into "
            f"visibility on {target} | fields: {fields} |")
        rows += 1
    for d in spec.get("_decisionFlags", []):
        lines.append(
            f"| Decision `{d.get('decision', '')}` | [WARNING] kept as decision "
            f"| {d.get('reason', '').replace(chr(10), ' ')} |")
        rows += 1
    if rows == 0:
        return "## Conditional Logic\n\nNone detected.\n"
    lines.append("")
    return "\n".join(lines)


def render_unsupported(spec: Dict[str, Any]) -> str:
    entries = spec.get("_incompleteMigration", [])
    if not entries:
        return "## Unsupported Components\n\nNone detected.\n"
    lines = ["## Unsupported Components", "",
             "| Type | Name | Reason |", "|---|---|---|"]
    for e in entries:
        reason = e.get("reason", "").replace("\n", " ").strip()
        lines.append(f"| {e.get('type', '')} | {e.get('name', '')} | {reason} |")
    lines.append("")
    return "\n".join(lines)


def render_behavioral_notes(spec: Dict[str, Any]) -> str:
    lines = ["## Behavioral Notes", ""]
    had_plain_buttons = any(
        e.get("type") == "PlainButtons"
        for e in spec.get("_incompleteMigration", []))
    if had_plain_buttons:
        lines.append(AGX_NOTE)
    cud = spec.get("_cudAnalysis", {})
    for m in cud.get("manualRestructure", []):
        lines.append(f"- **CUD `{m.get('node')}`:** "
                     f"{m.get('reason', '').replace(chr(10), ' ')}")
    for c in cud.get("consolidated", []):
        lines.append(f"- **CUD `{c.get('node')}`:** auto-consolidated to "
                     f"end-of-flow ({c.get('from')} → {c.get('to')}).")
    for cf in spec.get("_ceilingFlags", []):
        lines.append(f"- **`{cf.get('name')}`:** "
                     f"{cf.get('reason', '').replace(chr(10), ' ')}")
    if spec.get("_subflowNote"):
        lines.append(f"- **Subflows:** {spec['_subflowNote']}")
    if spec.get("_automationNote"):
        lines.append(f"- **Automation:** {spec['_automationNote']}")
    if spec.get("_migrationNote"):
        lines.append(f"- **Note:** {spec['_migrationNote']}")
    if len(lines) == 2:
        lines.append("None specific to this flow.")
    lines.append("")
    return "\n".join(lines)


def render_review_checklist(spec: Dict[str, Any]) -> str:
    items = [
        "Open the migrated flow in Flow Builder and confirm it opens without errors",
        "Verify Briefcase priming, FLS, and sharing for every object/field the flow touches",
        "Test the flow on a real device before activating",
    ]
    if spec.get("_incompleteMigration"):
        items.append("Rebuild each unsupported component listed above in Flow Builder")
    if spec.get("_cudAnalysis", {}).get("manualRestructure"):
        items.append("Manually restructure the flagged CUD operations to run after the last screen")
    if spec.get("_decisionFlags"):
        items.append("Review decisions that could not be collapsed into visibility")
    lines = ["## Review Checklist", ""]
    lines += [f"- [ ] {i}" for i in items]
    lines.append("")
    return "\n".join(lines)


def render_lds_warning() -> str:
    return ("## Lightning Data Service (LDS) Warning\n\n" + LDS_WARNING + "\n")


def render_advisory() -> str:
    return (
        "## Advisory (AI-generated — review before relying on)\n\n"
        "> **Advisory (AI-generated, review before relying on):**\n"
        "> _(placeholder — flow-specific advisory prose may be appended here.)_\n")


def render_summary(spec: Dict[str, Any]) -> str:
    parts = [f"# Migration Summary: {spec.get('formTitle', 'Untitled')}", ""]
    parts.append(render_mapping_table(spec))
    parts.append(render_conditional_logic(spec))
    parts.append(render_unsupported(spec))
    parts.append(render_behavioral_notes(spec))
    parts.append(render_lds_warning())
    parts.append(render_review_checklist(spec))
    parts.append(render_advisory())
    return "\n".join(parts) + "\n"


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <spec.json> <output.md>", file=sys.stderr)
        return 2
    spec = load_spec(argv[1])
    markdown = render_summary(spec)
    try:
        with open(argv[2], "w") as f:
            f.write(markdown)
    except OSError as e:
        print(f"[ERROR] Cannot write output '{argv[2]}': {e}", file=sys.stderr)
        return 1
    print(f"Migration summary written to: {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
