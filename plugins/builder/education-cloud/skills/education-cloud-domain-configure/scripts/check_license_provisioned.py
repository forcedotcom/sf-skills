#!/usr/bin/env python3
"""Decide whether Education Cloud is licensed/provisioned on the org.

Permission set names for Education Cloud vary by org/release, so a single
exact-name match is unreliable. Reads a JSON object from stdin:

{
  "permissionSets": [ { "Id": "...", "Name": "..." }, ... ],
  "businessProfileDescribe": { "createable": true, ... } | null
}

`permissionSets` is the `records` array from
`SELECT Id, Name FROM PermissionSet WHERE Name LIKE '%EducationCloud%'`.
`businessProfileDescribe` is the describe result for the `BusinessProfile`
sobject, or null/omitted if that describe call 404'd.

Rows found in `permissionSets` -> provisioned. Zero rows -> cross-check
`businessProfileDescribe.createable` before concluding not-provisioned.

Usage:
    python3 scripts/check_license_provisioned.py <<'JSON'
    {"permissionSets": [], "businessProfileDescribe": {"createable": true}}
    JSON
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    permission_sets = payload.get("permissionSets") or []
    describe = payload.get("businessProfileDescribe")

    if permission_sets:
        result = {
            "provisioned": True,
            "reason": "matching permission set(s) found",
            "matchingPermissionSets": [ps.get("Name") for ps in permission_sets],
        }
    elif isinstance(describe, dict) and describe.get("createable") is True:
        result = {
            "provisioned": True,
            "reason": "zero permission-set matches, but BusinessProfile is createable — treat as provisioned, note the mismatch",
            "matchingPermissionSets": [],
        }
    else:
        result = {
            "provisioned": False,
            "reason": "zero permission-set matches and BusinessProfile is not createable (404 or createable:false) — license not provisioned",
            "matchingPermissionSets": [],
        }

    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
