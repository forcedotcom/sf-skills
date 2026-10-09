#!/usr/bin/env python3
"""Check whether an org's edition meets Education Cloud's minimum requirement.

Reads a JSON object from stdin shaped like a SOQL query result for
`SELECT OrganizationType FROM Organization` (the `records` array, or a bare
list containing that one record). Prints a JSON verdict.

Usage:
    python3 scripts/check_org_edition.py \
        --allowed "Enterprise Edition,Performance Edition,Unlimited Edition,Developer Edition" <<'JSON'
    {"records": [{"OrganizationType": "Enterprise Edition"}]}
    JSON
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowed", required=True, help="Comma-separated list of qualifying OrganizationType values")
    args = parser.parse_args()
    allowed = [a.strip() for a in args.allowed.split(",") if a.strip()]

    payload = json.load(sys.stdin)
    records = payload.get("records", payload) if isinstance(payload, dict) else payload

    if not records:
        json.dump({"eligible": False, "organizationType": None, "reason": "no Organization record returned"}, sys.stdout, indent=2)
        print()
        return 0

    org_type = records[0].get("OrganizationType")
    result = {"eligible": org_type in allowed, "organizationType": org_type, "allowed": allowed}
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
