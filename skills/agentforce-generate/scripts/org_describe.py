#!/usr/bin/env python3
"""Query SObject field definitions and match them to action inputs/outputs for smart code generation.

Usage:
    python3 scripts/org_describe.py --sobject Account -o OrgAlias
    python3 scripts/org_describe.py --sobject Case -o OrgAlias --json
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class FieldInfo:
    """SObject field metadata."""
    name: str
    label: str
    data_type: str
    filterable: bool


@dataclass
class FieldMapping:
    """Mapping between action inputs/outputs and SObject fields."""
    input_mappings: dict[str, str] = field(default_factory=dict)   # input_name → field_name
    output_mappings: dict[str, str] = field(default_factory=dict)  # output_name → field_name
    select_fields: list[str] = field(default_factory=list)
    where_fields: list[str] = field(default_factory=list)


def describe_sobject(object_name: str, target_org: str) -> list[FieldInfo]:
    """Query FieldDefinition for an SObject's fields."""
    query = (
        f"SELECT QualifiedApiName, Label, DataType, IsCompactLayoutable "
        f"FROM FieldDefinition "
        f"WHERE EntityDefinition.QualifiedApiName = '{object_name}'"
    )
    cmd = ["sf", "data", "query", "--query", query, "-o", target_org, "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
        records = data.get("result", {}).get("records", [])
        return [
            FieldInfo(
                name=r.get("QualifiedApiName", ""),
                label=r.get("Label", ""),
                data_type=r.get("DataType", ""),
                filterable=r.get("IsCompactLayoutable", False),
            )
            for r in records
            if r.get("QualifiedApiName")
        ]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []


def match_fields(
    inputs: list[dict],
    outputs: list[dict],
    fields: list[FieldInfo],
) -> FieldMapping:
    """Match action inputs/outputs to SObject fields.

    Args:
        inputs: List of dicts with 'name' and 'type' keys.
        outputs: List of dicts with 'name' and 'type' keys.
        fields: SObject field definitions from describe_sobject().

    Returns:
        FieldMapping with matched input/output mappings.
    """
    mapping = FieldMapping()

    # Build field lookup
    field_names = [f.name for f in fields]
    filterable_fields = [f.name for f in fields if f.filterable]

    # Match inputs to filterable fields (for WHERE clause)
    for inp in inputs:
        if _is_computed_output(inp["name"]):
            continue
        best = _find_best_match(inp["name"], filterable_fields)
        if best:
            mapping.input_mappings[inp["name"]] = best
            mapping.where_fields.append(best)

    # Match outputs to any fields (for SELECT clause)
    for out in outputs:
        if _is_computed_output(out["name"]):
            continue
        best = _find_best_match(out["name"], field_names)
        if best:
            mapping.output_mappings[out["name"]] = best
            mapping.select_fields.append(best)

    return mapping


def _find_best_match(name: str, candidates: list[str], threshold: float = 0.5) -> str | None:
    """Find the best matching field name using fuzzy matching."""
    normalized = _normalize(name)

    # Exact normalized match
    for cand in candidates:
        if _normalize(cand) == normalized:
            return cand

    # Fuzzy sequence matching
    best_score = 0.0
    best_match = None
    for cand in candidates:
        score = difflib.SequenceMatcher(None, normalized, _normalize(cand)).ratio()
        # Bonus for word containment
        if normalized in _normalize(cand) or _normalize(cand) in normalized:
            score += 0.2
        if score > best_score and score >= threshold:
            best_score = score
            best_match = cand

    return best_match


def _normalize(name: str) -> str:
    """Normalize a field name for comparison."""
    # Remove __c suffix
    name = re.sub(r"__c$", "", name)
    # Split camelCase
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    # Replace underscores with spaces
    name = name.replace("_", " ")
    return name.lower().strip()


def _is_computed_output(name: str) -> bool:
    """Detect computed output names that shouldn't be mapped to fields."""
    computed_patterns = [
        "total_count", "result_json", "error_message", "status_code",
        "success", "is_valid", "record_count",
    ]
    return name.lower() in computed_patterns or name.endswith("_count") or name.endswith("_json")


def main():
    parser = argparse.ArgumentParser(description="Describe SObject fields")
    parser.add_argument("--sobject", required=True, help="SObject API name (e.g. Account, Case)")
    parser.add_argument("-o", "--target-org", required=True, help="Salesforce org alias")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    fields = describe_sobject(args.sobject, args.target_org)
    if not fields:
        print(f"No fields found for {args.sobject}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps([{"name": f.name, "label": f.label, "type": f.data_type, "filterable": f.filterable} for f in fields], indent=2))
    else:
        print(f"\n{args.sobject} — {len(fields)} fields\n")
        print(f"{'Field':<40} {'Label':<30} {'Type':<15} {'Filter'}")
        print(f"{'-'*40} {'-'*30} {'-'*15} {'-'*6}")
        for f in fields:
            filt = "✓" if f.filterable else ""
            print(f"{f.name:<40} {f.label:<30} {f.data_type:<15} {filt}")


if __name__ == "__main__":
    main()
