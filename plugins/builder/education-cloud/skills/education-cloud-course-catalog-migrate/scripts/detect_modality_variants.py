#!/usr/bin/env python3
"""Flag rows that share a CourseCode but differ in modality-bearing fields.

Reads a JSON array of course row objects from stdin, each with at least
"CourseCode" and optionally "Duration", "DurationUnit", "Description". Groups
rows by CourseCode; any group with 2+ rows that differ in Duration,
DurationUnit, or Description is a modality variant (e.g. Online vs.
On-Campus). Prints a JSON array of {"CourseCode", "rows"} for every flagged
group; groups with no variance are omitted.

Usage:
    python3 scripts/detect_modality_variants.py < courses.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

VARIANT_FIELDS = ("Duration", "DurationUnit", "Description")


def detect(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["CourseCode"]].append(row)

    flagged = []
    for code, group in grouped.items():
        if len(group) < 2:
            continue
        distinct = {tuple(row.get(f) for f in VARIANT_FIELDS) for row in group}
        if len(distinct) > 1:
            flagged.append({"CourseCode": code, "rows": group})
    return flagged


def main() -> int:
    rows = json.load(sys.stdin)
    flagged = detect(rows)
    json.dump(flagged, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
