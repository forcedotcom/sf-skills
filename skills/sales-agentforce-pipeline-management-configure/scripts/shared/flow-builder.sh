#!/bin/bash
# shared/flow-builder.sh — build the suggestion flow's field collection from a
# selected set of Opportunity fields.
#
# The base flow template (assets/pipeline_management_flow.flow-meta.xml) ships
# with a hardcoded AddOppFieldsToCollection assignment wiring BOTH NextStep and
# StageName. Historically setup deployed both and then STRIPPED the unwanted one
# (see strip_flow_field in setup-all.sh, still used for the repair path). For a
# greenfield setup we instead build the flow with ONLY the selected fields from
# the start — no deploy-then-strip round trip.
#
# This file only DEFINES a function; it makes no org calls and mutates no files
# when sourced. build_field_collection reads the base template and writes a NEW
# output file; it never edits the template in place.

# build_field_collection <comma-separated-fields> <base-template> <output-file>
#
# Rewrites the AddOppFieldsToCollection assignment so its <assignmentItems>
# contain exactly the given fields (in order, de-duplicated by the caller).
# Uses python3 for a namespace-safe edit — the same requirement as
# strip_flow_field. Returns non-zero (without writing) if python3 is missing,
# the template is unreadable, the assignment/fields are absent, or the write
# fails, so callers can fall back rather than deploy a corrupt/empty flow.
#
# A zero-item AddOppFieldsToCollection is INVALID Flow metadata and fails to
# deploy, so this function refuses to write when the field list is empty.
build_field_collection() {
  local fields="$1" base_template="$2" output_file="$3"

  if ! command -v python3 >/dev/null 2>&1; then
    echo "  [FAIL] python3 not available — cannot build flow field collection." >&2
    return 1
  fi
  if [[ ! -f "$base_template" ]]; then
    echo "  [FAIL] Base flow template not found: $base_template" >&2
    return 1
  fi

  python3 - "$base_template" "$output_file" "$fields" <<'PYEOF'
import sys, xml.etree.ElementTree as ET

base_template, output_file, raw_fields = sys.argv[1], sys.argv[2], sys.argv[3]

# Order-preserving de-dup of trimmed, non-empty field names.
fields = []
for f in raw_fields.split(","):
    f = f.strip()
    if f and f not in fields:
        fields.append(f)

if not fields:
    sys.stderr.write("  [FAIL] No fields provided — refusing to write an empty AddOppFieldsToCollection.\n")
    sys.exit(2)

ns = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", ns)
try:
    tree = ET.parse(base_template)
except Exception as e:  # noqa: BLE001
    sys.stderr.write("  [FAIL] Could not parse base flow template: %s\n" % e)
    sys.exit(3)

root = tree.getroot()
q = lambda t: "{%s}%s" % (ns, t)

target = None
for assign in root.findall(q("assignments")):
    name_elem = assign.find(q("name"))
    if name_elem is not None and name_elem.text == "AddOppFieldsToCollection":
        target = assign
        break

if target is None:
    sys.stderr.write("  [FAIL] AddOppFieldsToCollection assignment not found in template.\n")
    sys.exit(4)

# Drop existing assignmentItems, then rebuild from the selected fields.
for item in list(target.findall(q("assignmentItems"))):
    target.remove(item)

# The FlowAssignment schema requires every <assignmentItems> to be contiguous
# and positioned BEFORE <connector>. A plain ET.SubElement(target, ...) appends
# to the end of the element — AFTER <connector> when the template has one — which
# the Metadata API rejects with "Element assignmentItems is duplicated at this
# location". Find the connector's index and insert each new block just before it
# (falling back to append when there is no connector).
conn_idx = next((i for i, c in enumerate(list(target)) if c.tag == q("connector")), None)
insert_at = conn_idx
for field in fields:
    item = ET.Element(q("assignmentItems"))
    ref = ET.SubElement(item, q("assignToReference"))
    ref.text = "OpportunityFields"
    op = ET.SubElement(item, q("operator"))
    op.text = "Add"
    val = ET.SubElement(item, q("value"))
    sv = ET.SubElement(val, q("stringValue"))
    sv.text = field
    if insert_at is None:
        target.append(item)
    else:
        target.insert(insert_at, item)
        insert_at += 1

try:
    tree.write(output_file, xml_declaration=True, encoding="UTF-8")
except Exception as e:  # noqa: BLE001
    sys.stderr.write("  [FAIL] Could not write flow output file: %s\n" % e)
    sys.exit(5)

sys.exit(0)
PYEOF
}

# strip_flow_field <flow-file> <field> — remove the matching <assignmentItems>
# from the AddOppFieldsToCollection assignment of an EXISTING flow file, in place.
# This is the "fix method" used by the REPAIR path (a flow already deployed with
# fields the admin no longer wants). Greenfield never strips — it builds only the
# selected fields via build_field_collection. Requires python3 for a
# namespace-safe edit; if it is unavailable the field is left wired rather than
# risk corrupting the XML with a regex. Returns 0 if a field was removed, 2 if
# the field was not present (nothing to strip), non-zero on error.
strip_flow_field() {
  local flow_file="$1" field="$2"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "  [WARN] python3 not available — cannot strip '$field' from the flow; leaving it wired." >&2
    return 1
  fi
  python3 - "$flow_file" "$field" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
flow_file, field = sys.argv[1], sys.argv[2]
ns = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", ns)
tree = ET.parse(flow_file)
root = tree.getroot()
q = lambda t: "{%s}%s" % (ns, t)
removed = 0
for assign in root.findall(q("assignments")):
    name = assign.find(q("name"))
    if name is None or name.text != "AddOppFieldsToCollection":
        continue
    for item in list(assign.findall(q("assignmentItems"))):
        sv = item.find("%s/%s" % (q("value"), q("stringValue")))
        if sv is not None and sv.text == field:
            assign.remove(item)
            removed += 1
if removed:
    tree.write(flow_file, xml_declaration=True, encoding="UTF-8")
sys.exit(0 if removed else 2)
PYEOF
}

# add_flow_field <flow-file> <field> — idempotently ADD a field's <assignmentItems>
# to the AddOppFieldsToCollection assignment of an EXISTING flow file, in place.
# The symmetric counterpart to strip_flow_field, used by the REPAIR path to wire a
# newly-selected field into an already-deployed flow without a full rebuild (a full
# rebuild would discard the org-specific SalesManagementAgentTemplate constant the
# retrieved flow carries). No-op if the field is already wired. Returns 0 if added,
# 2 if it was already present, non-zero on error.
add_flow_field() {
  local flow_file="$1" field="$2"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "  [WARN] python3 not available — cannot add '$field' to the flow." >&2
    return 1
  fi
  python3 - "$flow_file" "$field" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
flow_file, field = sys.argv[1], sys.argv[2]
ns = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", ns)
tree = ET.parse(flow_file)
root = tree.getroot()
q = lambda t: "{%s}%s" % (ns, t)
target = None
for assign in root.findall(q("assignments")):
    name = assign.find(q("name"))
    if name is not None and name.text == "AddOppFieldsToCollection":
        target = assign
        break
if target is None:
    sys.stderr.write("  [FAIL] AddOppFieldsToCollection assignment not found.\n")
    sys.exit(4)
children = list(target)
last_ai_idx = -1
for idx, item in enumerate(children):
    if item.tag != q("assignmentItems"):
        continue
    last_ai_idx = idx
    sv = item.find("%s/%s" % (q("value"), q("stringValue")))
    if sv is not None and sv.text == field:
        sys.exit(2)  # already wired

# Build the new assignmentItems block.
item = ET.Element(q("assignmentItems"))
ref = ET.SubElement(item, q("assignToReference")); ref.text = "OpportunityFields"
op = ET.SubElement(item, q("operator")); op.text = "Add"
val = ET.SubElement(item, q("value"))
sv = ET.SubElement(val, q("stringValue")); sv.text = field

# The FlowAssignment schema requires every <assignmentItems> to be contiguous
# and positioned before <connector>. A plain append() lands the new block at
# the end of the element — AFTER <connector> when one exists — which the
# Metadata API rejects with "Element assignmentItems is duplicated at this
# location". Insert immediately after the last existing assignmentItems; if
# there are none, insert just before <connector> (else fall back to append).
if last_ai_idx >= 0:
    target.insert(last_ai_idx + 1, item)
else:
    conn_idx = next((i for i, c in enumerate(children) if c.tag == q("connector")), None)
    if conn_idx is not None:
        target.insert(conn_idx, item)
    else:
        target.append(item)
tree.write(flow_file, xml_declaration=True, encoding="UTF-8")
sys.exit(0)
PYEOF
}

# flow_wired_fields <flow-file> — print the field API names currently wired into
# AddOppFieldsToCollection, one per line (in document order). Used by the repair
# path to diff the deployed flow against the admin's selected set.
flow_wired_fields() {
  local flow_file="$1"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$flow_file" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
ns = "http://soap.sforce.com/2006/04/metadata"
tree = ET.parse(sys.argv[1])
q = lambda t: "{%s}%s" % (ns, t)
for assign in tree.getroot().findall(q("assignments")):
    name = assign.find(q("name"))
    if name is None or name.text != "AddOppFieldsToCollection":
        continue
    for item in assign.findall(q("assignmentItems")):
        sv = item.find("%s/%s" % (q("value"), q("stringValue")))
        if sv is not None and sv.text:
            print(sv.text)
PYEOF
}
