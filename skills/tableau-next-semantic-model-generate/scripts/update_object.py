#!/usr/bin/env python3
"""Update a data object's description (or label) on an existing SDM.

A data object is updated the same safe way as a base field/metric: its
sub-resource takes a **full-payload PUT** (PATCH is rejected with 405), so a
description change must re-send the COMPLETE object definition or other fields
(`dataObjectName`, `dataObjectType`, `tableType`, the nested field arrays) would
be lost. This script does resolve-and-merge: GET the object's full definition,
overlay the change, then PUT the complete body.

This updates an EXISTING data object's description/label. Adding/removing data
objects is out of scope (use add_data_object.py).

Usage:
    # Update a data object's description
    python scripts/update_object.py Workforce_SDM qb_hw_calendar \\
      --description "Business calendar table; the time spine for all metrics."

    # Update label + description
    python scripts/update_object.py Workforce_SDM qb_hw_employee \\
      --label "Employees" --description "One row per employee snapshot."

    # Dry-run: print the full PUT body without calling the org
    python scripts/update_object.py Workforce_SDM qb_hw_calendar \\
      --description "..." --dry-run
"""

import argparse
import json
import sys

from _shared.sdm_ai_templates import build_data_object_put_payload
from _shared.sdm_discovery import get_data_object_definition
from _shared.sf_api import data_object_endpoint, get_credentials, sf_put


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update a data object's description/label via full-payload PUT (resolve-and-merge).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("sdm", help="SDM apiName")
    parser.add_argument("object", help="Data-object apiName (e.g. qb_hw_calendar)")
    parser.add_argument("--description", help="New data-object description.")
    parser.add_argument("--label", help="New data-object label.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the full PUT body and exit without calling the org.")
    args = parser.parse_args()

    if args.description is None and args.label is None:
        print("Error: nothing to change. Provide --description and/or --label.", file=sys.stderr)
        return 1

    # RESOLVE: fetch the object's FULL definition (the body the PUT must re-send).
    existing = get_data_object_definition(args.sdm, args.object)
    if existing is None:
        print(
            f"Error: could not resolve data object '{args.object}' on "
            f"'{args.sdm}'. A full-payload PUT requires the current definition "
            f"to merge into.",
            file=sys.stderr,
        )
        return 1

    # MERGE: overlay the requested change onto the full definition.
    try:
        payload = build_data_object_put_payload(
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
    resp, err = sf_put(token, instance, data_object_endpoint(args.sdm, args.object), payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"\n✓ Updated data object: {args.object}", file=sys.stderr)
    print(
        f"  Verify with: python scripts/discover_sdm.py {args.sdm} --json "
        f"(check the object's description).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
