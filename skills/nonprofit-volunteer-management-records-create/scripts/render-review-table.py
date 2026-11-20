#!/usr/bin/env python3
"""Render one entity's "Records to insert" review table with a fixed column order.

The review table is the user's last look before a write, so a cell that lands under the
wrong header (a Status value showing under Description) is a real defect, not cosmetics.
That happens when rows are typed out by hand, cell by cell, and the fields of each record
arrive in a different order. This script removes the hand step: the agent passes the
entity's records as data (field -> value + origin tag) and the script prints the markdown
table. The column order is decided once, for every row:

  1. ``Record`` — row number and the record's name;
  2. the entity's non-lookup fields, in ``references/field-guide.md`` tier order
     (T1, then T2, then T3; ties keep the field guide's row order), then any custom fields;
  3. lookup fields last, in the same tier order.

Field facts (API names, tiers, which fields are lookups, which are schema-required) are read
from ``references/field-guide.md`` so the table and the field guide can't drift apart.
Headers are field labels ("Parent Volunteer Initiative"), never API names: a label passed in
``labels`` (from a live describe, so an admin rename wins) is used first; otherwise the label
is spelled out from the field guide's field name.

USAGE
-----
    python3 scripts/render-review-table.py < records.json
    python3 scripts/render-review-table.py --expand < records.json   # list grouped rows one by one

SPEC (stdin JSON)
-----------------
    {
      "entity": "JobPosition",
      "records": [
        {"fields": {
          "Name":   {"value": "Greeter — Eastside", "origin": "given"},
          "Title":  {"value": "Greeter", "origin": "generated"},
          "Status": {"value": "Upcoming", "origin": "default"},
          "VolunteerInitiativeId": {"value": "Food Pantry 2027", "origin": "new"}
        }}
      ],
      "labels": {"VolunteerInitiativeId": "Related Volunteer Initiative"},   # optional
      "requiredCustomFields": ["Region__c"],                                 # optional
      "title": "Records to insert — 12 Job Position Shifts (1 series)"       # optional
    }

  * Fields are keyed by API name (``VolunteerInitiativeId``) or by the field guide's
    relationship name (``VolunteerInitiative``); both resolve to the same column.
  * ``origin`` is one of: given, default, generated, reuse, new, needs-input. A lookup cell
    is tagged ``reuse`` (an existing record) or ``new`` (created this run) and shows the
    referenced record's Name, never an Id. The origin is checked, but only ``reuse`` and
    ``needs-input`` are printed: every other value is reviewed the same way whatever its
    origin.
  * A record may carry ``"label"`` to name its row; otherwise the row uses its ``Name`` value.
  * A required field (schema-required or always-set in the field guide) always gets a column.
    When a record has no value for it the cell shows ``needs-input``. A field that is always
    set but not schema-required (e.g. an Address street) may be left blank on purpose by
    passing it with an empty value and a non-``needs-input`` origin; the cell shows ``—``.
  * An optional field gets a column only when at least one record has a value for it.
  * When every row's label is its ``Name``, the Name column is dropped (the Record cell shows
    the name) so the name isn't printed twice.
  * With more than one row, a column whose cell is the same on every row moves into one
    ``Same on every row: …`` line above the table. A ``needs-input`` column always stays.
  * Consecutive rows whose field cells are all identical collapse into one group row
    (``say "show all N"``); ``--expand`` lists them one by one.
  * ``title`` replaces the default ``Records to insert — N <Object>`` heading — use it when a
    row stands for a whole shift series, so the heading counts shifts, not rows.

Exit non-zero with a message on any spec error (unknown entity, a field the field guide
doesn't document, a system-managed field, a bad origin tag, a raw Id in a lookup cell, ...).
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FIELD_GUIDE = os.path.join(os.path.dirname(HERE), "references", "field-guide.md")

ORIGINS = ("given", "default", "generated", "reuse", "new", "needs-input")
LOOKUP_ORIGINS = ("reuse", "new")
NEEDS_INPUT = "needs-input"
BLANK = "—"
# Tiers 4 and 5 are system-managed or belong to another feature — never written.
WRITABLE_TIERS = (1, 2, 3)

ENTITY_HEADING = re.compile(r"^###\s+(\w+)\s+—")
RELATIONSHIP_CELL = re.compile(r"^`(\w+)`\s*\(`(\w+)`\)")
BACKTICKED = re.compile(r"`(\w+)`")
# A 15- or 18-character record Id: alphanumeric with several digits. Names rarely look
# like this; Ids almost always do.
RECORD_ID = re.compile(r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")


def fail(msg):
    sys.stderr.write("render-review-table: %s\n" % msg)
    sys.exit(1)


def spell_out(name):
    """``ParentVolunteerInitiative`` -> ``Parent Volunteer Initiative``."""
    if name.endswith("__c"):
        name = name[:-3]
    name = name.replace("_", " ")
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name).strip()


def plural(label):
    if label.endswith("Hours"):
        return label
    if label.endswith("s"):
        return label + "es"
    if label.endswith("y") and label[-2:-1] not in "aeiou":
        return label[:-1] + "ies"
    return label + "s"


def parse_field_guide(path):
    """Return {entity: [field, ...]} in field-guide row order.

    Each field is a dict: api, name (the field guide's display name), tier, lookup,
    schema_required, order.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        fail("cannot read the field guide at %s: %s" % (path, e))
    entities = {}
    current = None
    for line in lines:
        heading = ENTITY_HEADING.match(line)
        if heading:
            current = heading.group(1)
            entities[current] = []
            continue
        if line.startswith("## "):
            current = None
            continue
        if current is None or not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        field_cell, type_cell, req_cell, tier_cell = cells[:4]
        tier_match = re.search(r"T(\d)", tier_cell)
        if not tier_match:
            continue
        tier = int(tier_match.group(1))
        lookup = bool(re.search(r"(?i)lookup|master-detail", type_cell))
        schema_required = req_cell.strip("* ").lower() == "yes"
        rel = RELATIONSHIP_CELL.match(field_cell)
        if rel:
            pairs = [(rel.group(2), rel.group(1))]
        else:
            pairs = [(name, name) for name in BACKTICKED.findall(field_cell)]
        for api, name in pairs:
            entities[current].append({
                "api": api, "name": name, "tier": tier, "lookup": lookup,
                "schema_required": schema_required, "order": len(entities[current]),
            })
    return entities


def resolve_columns(spec, guide):
    entity = spec.get("entity")
    if entity not in guide:
        fail("unknown entity %r — use one documented in field-guide.md (%s)"
             % (entity, ", ".join(sorted(guide))))
    fields = guide[entity]
    by_key = {}
    for f in fields:
        by_key[f["api"]] = f
        by_key[f["name"]] = f
    return entity, fields, by_key


def cell_text(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_record(index, record, by_key, custom_required):
    """Return (row_label, {api: (value, origin)}, custom_apis) for one record."""
    if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
        fail("records[%d] must be an object with a 'fields' map" % index)
    out = {}
    customs = []
    for key, entry in record["fields"].items():
        where = "records[%d].%s" % (index, key)
        if not isinstance(entry, dict) or "origin" not in entry:
            fail("%s must be an object with 'value' and 'origin'" % where)
        origin = entry["origin"]
        if origin not in ORIGINS:
            fail("%s origin %r is not one of %s" % (where, origin, ", ".join(ORIGINS)))
        value = entry.get("value")
        field = by_key.get(key)
        if field is None:
            if not key.endswith("__c"):
                fail("%s is not in field-guide.md for this entity — never assume a field "
                     "exists (custom fields end in __c)" % where)
            api = key
            customs.append(api)
            lookup = False
        else:
            api = field["api"]
            lookup = field["lookup"]
            if field["tier"] not in WRITABLE_TIERS:
                fail("%s is system-managed or owned by another feature (tier T%d) — never "
                     "set it" % (where, field["tier"]))
        if api in out:
            fail("%s duplicates a field already given for this record" % where)
        if origin != NEEDS_INPUT and not is_empty(value):
            if lookup and origin not in LOOKUP_ORIGINS:
                fail("%s is a lookup — tag it 'reuse' (existing record) or 'new' (created "
                     "this run)" % where)
            if not lookup and origin in LOOKUP_ORIGINS:
                fail("%s is not a lookup — 'reuse'/'new' tags are only for lookup cells"
                     % where)
            if lookup and isinstance(value, str) and RECORD_ID.match(value) \
                    and sum(ch.isdigit() for ch in value) >= 3:
                fail("%s looks like a record Id — show the referenced record's Name; Ids "
                     "appear only in the final insert report" % where)
        out[api] = (value, origin)
    label = record.get("label")
    if is_empty(label):
        name = out.get("Name", (None, None))[0]
        label = name if not is_empty(name) else ""
    return str(label), out, customs


def build_table(spec, guide, expand=False):
    entity, fields, by_key = resolve_columns(spec, guide)
    records = spec.get("records")
    if not isinstance(records, list) or not records:
        fail("records must be a non-empty list")
    labels = spec.get("labels") or {}
    if not isinstance(labels, dict):
        fail("labels must be a map of API name -> label")
    custom_required = spec.get("requiredCustomFields") or []
    if not isinstance(custom_required, list) or any(
            not isinstance(c, str) or not c.endswith("__c") for c in custom_required):
        fail("requiredCustomFields must be a list of custom field API names ending in __c")

    rows = []
    custom_seen = []
    for i, rec in enumerate(records):
        label, values, customs = normalize_record(i, rec, by_key, custom_required)
        rows.append((label, values))
        for c in customs:
            if c not in custom_seen:
                custom_seen.append(c)
    for c in custom_required:
        if c not in custom_seen:
            custom_seen.append(c)

    def has_value(api):
        return any(api in v and v[api][1] != NEEDS_INPUT for _, v in rows)

    def required(f):
        return f["schema_required"] or f["tier"] == 1

    writable = [f for f in fields if f["tier"] in WRITABLE_TIERS]
    plain = sorted((f for f in writable if not f["lookup"]),
                   key=lambda f: (f["tier"], f["order"]))
    lookups = sorted((f for f in writable if f["lookup"]),
                     key=lambda f: (f["tier"], f["order"]))
    columns = []  # (api, header, required, schema_required)
    for f in plain:
        if required(f) or has_value(f["api"]):
            columns.append((f["api"], labels.get(f["api"]) or spell_out(f["name"]),
                            required(f), f["schema_required"]))
    for c in custom_seen:
        if c in custom_required or has_value(c):
            columns.append((c, labels.get(c) or spell_out(c), c in custom_required,
                            c in custom_required))
    for f in lookups:
        if required(f) or has_value(f["api"]):
            columns.append((f["api"], labels.get(f["api"]) or spell_out(f["name"]),
                            required(f), f["schema_required"]))

    missing = {}  # header -> [row numbers]

    def render_cell(row_no, values, api, header, is_required, schema_required):
        entry = values.get(api)
        if entry is None or entry[1] == NEEDS_INPUT:
            if is_required:
                missing.setdefault(header, []).append(row_no)
                return "`%s`" % NEEDS_INPUT
            return BLANK
        value, origin = entry
        if is_empty(value):
            if schema_required:
                missing.setdefault(header, []).append(row_no)
                return "`%s`" % NEEDS_INPUT
            return BLANK
        # Only a reused lookup is tagged: it attaches the new records to data already in the
        # org, which the user should notice. Every other value is reviewed the same way
        # whatever its origin, so its tag would only widen the row.
        if origin == "reuse":
            return "%s `reuse`" % cell_text(value)
        return cell_text(value)

    body = []
    for n, (label, values) in enumerate(rows, 1):
        cells = [render_cell(n, values, *col) for col in columns]
        body.append((n, label, cells))

    # The row label already shows the Name, so a Name column would repeat it. The label
    # still keeps records with different names from grouping.
    name_dropped = False
    if "Name" in [c[0] for c in columns] and all(
            "Name" in v and v["Name"][1] != NEEDS_INPUT and not is_empty(v["Name"][0])
            and str(v["Name"][0]) == label for label, v in rows):
        name_dropped = True
        idx = [c[0] for c in columns].index("Name")
        columns.pop(idx)
        for _, _, cells in body:
            cells.pop(idx)

    # A column with the same value on every row is stated once above the table instead of
    # widening every row. A needs-input column stays so the gap is visible on its rows.
    shared = []
    if len(body) > 1:
        keep = []
        for i, col in enumerate(columns):
            first = body[0][2][i]
            if first != "`%s`" % NEEDS_INPUT and all(b[2][i] == first for b in body):
                shared.append("%s %s" % (cell_text(col[1]), first))
            else:
                keep.append(i)
        if shared:
            columns = [columns[i] for i in keep]
            body = [(n, label, [cells[i] for i in keep]) for n, label, cells in body]

    lines = []
    entity_label = spell_out(entity)
    title = spec.get("title")
    if title is not None and (not isinstance(title, str) or not title.strip()):
        fail("title must be a non-empty string")
    lines.append(title or "Records to insert — %d %s"
                 % (len(rows), entity_label if len(rows) == 1 else plural(entity_label)))
    lines.append("")
    if shared:
        lines.append("Same on every row: " + " · ".join(shared))
        lines.append("")
    headers = ["Record"] + [cell_text(c[1]) for c in columns]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")

    def record_cell(n, label):
        return "%d · %s" % (n, cell_text(label)) if label else str(n)

    def same_row(a, b):
        return a[2] == b[2] and (not name_dropped or a[1] == b[1])

    i = 0
    while i < len(body):
        j = i
        while not expand and j + 1 < len(body) and same_row(body[j + 1], body[i]):
            j += 1
        if j > i:
            size = j - i + 1
            n_first, label, cells = body[i]
            first = "Rows %d–%d" % (n_first, body[j][0])
            if label:
                first += " · %s" % cell_text(label)
            first += " (%d identical — say \"show all %d\")" % (size, size)
            lines.append("| " + " | ".join([first] + cells) + " |")
        else:
            n, label, cells = body[i]
            lines.append("| " + " | ".join([record_cell(n, label)] + cells) + " |")
        i = j + 1

    rendered = "\n".join(lines)
    notes = []
    if "`reuse`" in rendered:
        notes.append("`reuse` = links to a record already in your org")
    if missing:
        notes.append("`needs-input` = required, still missing")
    lines.append("")
    if notes:
        lines.append(" · ".join(notes))
    if missing:
        parts = ["%s (row%s %s)" % (h, "s" if len(r) > 1 else "", ", ".join(map(str, r)))
                 for h, r in missing.items()]
        lines.append("Still needed before this can be written: " + "; ".join(parts))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Render a VM records review table.")
    ap.add_argument("--expand", action="store_true",
                    help="list identical rows one by one instead of grouping them")
    ap.add_argument("--field-guide", default=DEFAULT_FIELD_GUIDE,
                    help="path to field-guide.md (default: the skill's references copy)")
    args = ap.parse_args()

    raw = sys.stdin.read()
    if not raw.strip():
        fail("no spec on stdin — pipe a JSON spec (see the module docstring)")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        fail("spec is not valid JSON: %s" % e)
    if not isinstance(spec, dict):
        fail("spec must be a JSON object (got %s)" % type(spec).__name__)

    guide = parse_field_guide(args.field_guide)
    sys.stdout.write(build_table(spec, guide, expand=args.expand))


if __name__ == "__main__":
    main()
