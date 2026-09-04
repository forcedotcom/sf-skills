#!/usr/bin/env python3
"""Check a list of course records for missing required/recommended fields.

Reads a JSON array of course record objects from stdin. Prints a JSON report
of per-field present/missing counts and which records are missing which
fields. Works for both raw parsed data (before create) and org-record
read-backs (after create) — pass the field names present in that record shape.

Usage:
    python3 scripts/validate_completeness.py --required Name,Duration --recommended Description,CourseType
"""

from __future__ import annotations

import argparse
import json
import sys


def is_missing(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def check(records: list[dict], required: list[str], recommended: list[str]) -> dict:
    report = {"total": len(records), "required": {}, "recommended": {}}
    for label, fields in (("required", required), ("recommended", recommended)):
        for field_name in fields:
            missing_indexes = [i for i, r in enumerate(records) if is_missing(r.get(field_name))]
            report[label][field_name] = {
                "present": len(records) - len(missing_indexes),
                "missing": len(missing_indexes),
                "missing_indexes": missing_indexes,
            }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", default="", help="Comma-separated required field names")
    parser.add_argument("--recommended", default="", help="Comma-separated recommended field names")
    args = parser.parse_args()

    records = json.load(sys.stdin)
    required = [f for f in args.required.split(",") if f]
    recommended = [f for f in args.recommended.split(",") if f]

    report = check(records, required, recommended)
    json.dump(report, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
