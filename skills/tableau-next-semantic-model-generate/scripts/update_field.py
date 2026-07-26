#!/usr/bin/env python3
"""Update a base dimension/measurement's description (or label) on an existing SDM.

A raw base field is updated the SAME safe way as a metric: the field
sub-resource accepts a **full-payload PUT** (PATCH is rejected with 405), so a
description change must re-send the COMPLETE field definition or other fields
(`dataType`, `aggregationType`, `dataObjectFieldName`, …) would be nulled. This
script does resolve-and-merge: GET the field's full definition, overlay the
change, then PUT the complete body.

This updates an EXISTING base field. Creating base fields is out of scope (use
add_data_object.py / the dimension/measurement add endpoints).

Usage:
    # Update a dimension's description
    python scripts/update_field.py Workforce_SDM qb_hw_calendar \\
      --dimension report_date \\
      --description "Business calendar date; the time anchor for all metrics."

    # Update a measurement's label + description
    python scripts/update_field.py Workforce_SDM qb_hw_employee \\
      --measurement headcount \\
      --label "Headcount" --description "Active employees at period end."

    # Dry-run: print the full PUT body without calling the org
    python scripts/update_field.py Workforce_SDM qb_hw_calendar \\
      --dimension report_date --description "..." --dry-run
"""

import argparse
import json
import sys

from _shared.sdm_ai_templates import build_base_field_put_payload
from _shared.sdm_discovery import get_base_field_definition
from _shared.sf_api import base_field_endpoint, get_credentials, sf_put


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update a base dimension/measurement via full-payload PUT (resolve-and-merge).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("sdm", help="SDM apiName")
    parser.add_argument("object", help="Data-object apiName (e.g. qb_hw_calendar)")
    role = parser.add_mutually_exclusive_group(required=True)
    role.add_argument("--dimension", metavar="FIELD", help="Base dimension apiName to update")
    role.add_argument("--measurement", metavar="FIELD", help="Base measurement apiName to update")
    parser.add_argument("--description", help="New field description.")
    parser.add_argument("--label", help="New field label.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the full PUT body and exit without calling the org.")
    args = parser.parse_args()

    if args.description is None and args.label is None:
        print("Error: nothing to change. Provide --description and/or --label.", file=sys.stderr)
        return 1

    field_role = "dimensions" if args.dimension else "measurements"
    field_name = args.dimension or args.measurement

    # RESOLVE: fetch the field's FULL definition (the body the PUT must re-send).
    existing = get_base_field_definition(args.sdm, args.object, field_role, field_name)
    if existing is None:
        print(
            f"Error: could not resolve {field_role[:-1]} '{field_name}' on "
            f"'{args.sdm}'/'{args.object}'. A full-payload PUT requires the "
            f"current definition to merge into.",
            file=sys.stderr,
        )
        return 1

    # MERGE: overlay the requested change onto the full definition.
    try:
        payload = build_base_field_put_payload(
            existing, description=args.description, label=args.label
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n[Dry-run mode - full PUT body shown above, not PUT]", file=sys.stderr)
        return 0

    # PUT the COMPLETE body.
    token, instance = get_credentials()
    path = base_field_endpoint(args.sdm, args.object, field_role, field_name)
    resp, err = sf_put(token, instance, path, payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"\n✓ Updated {field_role[:-1]}: {field_name}", file=sys.stderr)
    print(
        f"  Verify with: python scripts/discover_sdm.py {args.sdm} --json "
        f"(check the field's description).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
