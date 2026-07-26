#!/usr/bin/env python3
"""Add a data object — or a base dimension/measure — to an existing SDM.

Three modes (one per call, to dodge the bulk-create timeout):

  --mode object     add a data object incrementally to the SDM
  --mode dimension  add ONE base (non-calc) dimension with a controlled apiName
  --mode measure    add ONE base (non-calc) measure with a controlled apiName

After every add the script reads the SDM back and prints the server-stored
(possibly suffixed) field apiNames — the primary source of join keys for
add_relationship.py. A single-field add (dimension/measure) preserves the
caller-supplied apiName verbatim (no auto-suffix), giving clean join-key names.

Usage:
    # Add a data object (auto-bind all fields → apiNames get suffixed)
    python scripts/add_data_object.py --mode object \\
      --sdm Join_SDM --data-object qb_hw_position__dlm

    # Add a base dimension with a controlled apiName (preserved verbatim)
    python scripts/add_data_object.py --mode dimension \\
      --sdm Join_SDM --object qb_hw_position \\
      --api-name Position_Title --source-field position_title__c --data-type Text

    # Add a base measure (agg/dataType allow-list enforced)
    python scripts/add_data_object.py --mode measure \\
      --sdm Join_SDM --object qb_hw_position \\
      --api-name Headcount --source-field employee_count__c \\
      --data-type Number --aggregation Sum

    # Dry-run
    python scripts/add_data_object.py --mode object \\
      --sdm Join_SDM --data-object qb_hw_position__dlm --dry-run
"""

import argparse
import json
import sys
from typing import Optional

from _shared.sdm_discovery import extract_object_field_apinames, get_sdm_details
from _shared.sdm_structure_templates import (
    build_base_dimension,
    build_base_measure,
    build_data_object,
    infer_data_object_type,
    validate_data_object_name,
    validate_measure_aggregation,
)
from _shared.sf_api import (
    get_credentials,
    sdm_data_objects_endpoint,
    sdm_dimensions_endpoint,
    sdm_measurements_endpoint,
    sf_post,
)


def _print_readback(sdm_name: str, focus_object: Optional[str] = None) -> None:
    """Fetch the SDM and print the resolved (suffixed) field apiNames."""
    data = get_sdm_details(sdm_name)
    if not data:
        print("  (SDM fetch failed: could not fetch SDM)", file=sys.stderr)
        return
    field_map = extract_object_field_apinames(data)
    print("\nStored field apiNames (use these as join keys — never guess the suffix):", file=sys.stderr)
    for obj, fields in field_map.items():
        if focus_object and obj != focus_object:
            continue
        print(f"  {obj}:", file=sys.stderr)
        if fields["dimensions"]:
            print(f"    dimensions: {', '.join(fields['dimensions'])}", file=sys.stderr)
        if fields["measures"]:
            print(f"    measures:   {', '.join(fields['measures'])}", file=sys.stderr)


def _build_object_payload(args) -> tuple:
    """Returns (payload, endpoint, focus_object) for --mode object."""
    ok, err = validate_data_object_name(args.data_object)
    if not ok:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    object_api_name = args.object_api_name
    if not object_api_name:
        object_api_name = args.data_object
        for suffix in ("__dll", "__dlm", "__dlc"):
            if object_api_name.endswith(suffix):
                object_api_name = object_api_name[: -len(suffix)]
                break
    payload = build_data_object(
        api_name=object_api_name,
        data_object_name=args.data_object,
        label=args.object_label or object_api_name,
        data_object_type=args.object_type or infer_data_object_type(args.data_object),
        should_include_all_fields=not args.no_include_all_fields,
    )
    return payload, sdm_data_objects_endpoint(args.sdm), object_api_name


def _build_dimension_payload(args) -> tuple:
    if not args.object or not args.api_name or not args.source_field:
        print("Error: --mode dimension requires --object, --api-name, and --source-field.", file=sys.stderr)
        sys.exit(1)
    payload = build_base_dimension(
        api_name=args.api_name,
        data_object_field_name=args.source_field,
        label=args.label or args.api_name,
        data_type=args.data_type or "Text",
        description=args.description,
    )
    return payload, sdm_dimensions_endpoint(args.sdm, args.object), args.object


def _build_measure_payload(args) -> tuple:
    if not args.object or not args.api_name or not args.source_field:
        print("Error: --mode measure requires --object, --api-name, and --source-field.", file=sys.stderr)
        sys.exit(1)
    data_type = args.data_type or "Number"
    aggregation = args.aggregation or "Sum"
    ok, err = validate_measure_aggregation(data_type, aggregation)
    if not ok:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    payload = build_base_measure(
        api_name=args.api_name,
        data_object_field_name=args.source_field,
        label=args.label or args.api_name,
        data_type=data_type,
        aggregation_type=aggregation,
        description=args.description,
    )
    return payload, sdm_measurements_endpoint(args.sdm, args.object), args.object


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a data object / base dimension / base measure to an SDM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--mode", required=True, choices=["object", "dimension", "measure"])
    parser.add_argument("--sdm", required=True, help="Target SDM apiName")

    # object mode
    parser.add_argument("--data-object", help="[object] source name with suffix (__dll/__dlm/__dlc)")
    parser.add_argument("--object-api-name", help="[object] SDM-level object apiName (default: source without suffix)")
    parser.add_argument("--object-label", help="[object] object display label")
    parser.add_argument("--object-type", choices=["Dlo", "Dmo", "Cio"], help="[object] dataObjectType (default: inferred)")
    parser.add_argument("--no-include-all-fields", action="store_true",
                        help="[object] do not auto-bind all source columns")

    # dimension / measure mode
    parser.add_argument("--object", help="[dimension/measure] SDM-level object apiName to add the field to")
    parser.add_argument("--api-name", help="[dimension/measure] caller-controlled field apiName (preserved verbatim)")
    parser.add_argument("--source-field", help="[dimension/measure] raw source column (e.g. position_title__c)")
    parser.add_argument("--label", help="[dimension/measure] field display label")
    parser.add_argument("--data-type", help="[dimension/measure] dataType (dim default Text, measure default Number)")
    parser.add_argument("--aggregation", help="[measure] aggregationType (default Sum; allow-list enforced)")
    parser.add_argument("--description", default="", help="[dimension/measure] field description")

    parser.add_argument("--dry-run", action="store_true", help="Print payload without POSTing")
    args = parser.parse_args()

    if args.mode == "object":
        if not args.data_object:
            print("Error: --mode object requires --data-object.", file=sys.stderr)
            sys.exit(1)
        payload, endpoint, focus = _build_object_payload(args)
    elif args.mode == "dimension":
        payload, endpoint, focus = _build_dimension_payload(args)
    else:
        payload, endpoint, focus = _build_measure_payload(args)

    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not POSTed]", file=sys.stderr)
        return

    token, instance = get_credentials()
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    stored_name = (resp or {}).get("apiName", payload["apiName"])
    print(f"\n✓ Added {args.mode}: {stored_name}", file=sys.stderr)
    if args.mode in ("dimension", "measure") and stored_name != payload["apiName"]:
        print(f"  → Server stored apiName as: {stored_name} (differs from requested {payload['apiName']})", file=sys.stderr)

    # Always resolve the stored apiNames after an add (the join-key source).
    _print_readback(args.sdm, focus_object=focus)


if __name__ == "__main__":
    main()
