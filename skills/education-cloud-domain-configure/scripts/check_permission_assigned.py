#!/usr/bin/env python3
"""Check whether the running user has one of the org's Education Cloud permission sets assigned.

Reads a JSON object from stdin shaped like a SOQL query result for
`SELECT Id, PermissionSet.Name FROM PermissionSetAssignment WHERE
AssigneeId='<id>' AND PermissionSet.Name LIKE '%EducationCloud%'` (the
`records` array, or a bare list). Prints a JSON verdict.

Usage:
    python3 scripts/check_permission_assigned.py <<'JSON'
    {"records": [{"PermissionSet": {"Name": "EducationCloudAccess"}}]}
    JSON
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    records = payload.get("records", payload) if isinstance(payload, dict) else payload

    names = []
    for rec in records or []:
        permission_set = rec.get("PermissionSet") or {}
        name = permission_set.get("Name")
        if name:
            names.append(name)

    result = {"assigned": bool(names), "matchingPermissionSets": names}
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
