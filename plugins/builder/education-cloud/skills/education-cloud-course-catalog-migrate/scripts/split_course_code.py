#!/usr/bin/env python3
"""Split course codes into SubjectAbbreviation + CourseNumber.

Reads a JSON array of course code strings from stdin (e.g. "BIO-201",
"bio 201l"). Prints a JSON array of {"code", "SubjectAbbreviation",
"CourseNumber"} objects — LearningCourse has no single CipCode field, so
these two fields must be populated separately.

Usage:
    python3 scripts/split_course_code.py
"""

from __future__ import annotations

import json
import re
import sys

PATTERN = re.compile(r"^\s*([A-Za-z]+)[\s-]*([0-9]+[A-Za-z]*)\s*$")


def split(code: str) -> dict:
    match = PATTERN.match(code)
    if not match:
        return {"code": code, "SubjectAbbreviation": None, "CourseNumber": None}
    subject, number = match.groups()
    return {"code": code, "SubjectAbbreviation": subject.upper(), "CourseNumber": number.upper()}


def main() -> int:
    codes = json.load(sys.stdin)
    results = [split(c) for c in codes]
    json.dump(results, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
