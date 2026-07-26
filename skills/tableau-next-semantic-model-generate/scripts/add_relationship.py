#!/usr/bin/env python3
"""Add a model-level relationship (join) between two SDM data objects.

Builds the relationship: joinType="Auto",
cardinality (default ManyToOne, fact→dimension), criteria[] with
leftFieldType/rightFieldType="TableField", and a REQUIRED label. The join-key
field references MUST be the resolved semantic apiNames (printed by
create_sdm.py / add_data_object.py, or from `discover_sdm.py --json`) —
NOT the raw "__c" source column, which fails with "field could not be found"
(the #1 relationship error).

Usage:
    # Single-key join (most common): employee.position_id2 -> position.position_id3
    python scripts/add_relationship.py \\
      --sdm Join_SDM \\
      --left-object qb_hw_employee --right-object qb_hw_position \\
      --left-field position_id2 --right-field position_id3 \\
      --label "Employee : Position"

    # Explicit cardinality + apiName
    python scripts/add_relationship.py \\
      --sdm Join_SDM --api-name emp_dept \\
      --left-object Employee --right-object Department \\
      --left-field dept_id1 --right-field dept_id \\
      --cardinality ManyToOne --label "Employee : Department"

    # Dry-run
    python scripts/add_relationship.py \\
      --sdm Join_SDM --left-object A --right-object B \\
      --left-field a1 --right-field b1 --label "A : B" --dry-run

After a successful add, verify the join with a cross-object semantic query
(see references/sdm-creation-api.md, "Proof the join works").
"""

import argparse
import json
import sys

from _shared.sdm_structure_templates import (
    build_join_criterion,
    build_relationship,
    validate_relationship,
)
from _shared.sf_api import (
    get_credentials,
    sdm_relationships_endpoint,
    sf_post,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a model-level relationship (join) between two SDM data objects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--sdm", required=True, help="Target SDM apiName")
    parser.add_argument("--left-object", required=True, help="Left data-object apiName (e.g. the fact)")
    parser.add_argument("--right-object", required=True, help="Right data-object apiName (e.g. the dimension)")
    parser.add_argument("--left-field", required=True,
                        help="Left join-key: the RESOLVED semantic apiName (NOT the __c source name)")
    parser.add_argument("--right-field", required=True,
                        help="Right join-key: the RESOLVED semantic apiName (NOT the __c source name)")
    parser.add_argument("--label", required=True, help="Relationship display label (REQUIRED)")
    parser.add_argument("--api-name", help="Relationship apiName (default: <left>_<right>)")
    parser.add_argument(
        "--cardinality", default="ManyToOne",
        choices=["OneToOne", "OneToMany", "ManyToOne", "ManyToMany", "Unspecified"],
        help="Join cardinality (default ManyToOne, fact->dimension)",
    )
    parser.add_argument("--join-operator", default="Equals", help="Criterion operator (default Equals)")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without POSTing")
    args = parser.parse_args()

    api_name = args.api_name or f"{args.left_object}_{args.right_object}"
    criterion = build_join_criterion(
        left_field_api_name=args.left_field,
        right_field_api_name=args.right_field,
        join_operator=args.join_operator,
    )
    payload = build_relationship(
        api_name=api_name,
        label=args.label,
        left_object=args.left_object,
        right_object=args.right_object,
        criteria=[criterion],
        cardinality=args.cardinality,
    )

    # Validate pre-POST — catches empty label, non-Auto join, bad cardinality,
    # and the #1 error: a raw "__c" source-column join key.
    ok, errors = validate_relationship(payload)
    if not ok:
        print("Validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not POSTed]", file=sys.stderr)
        return

    token, instance = get_credentials()
    resp, err = sf_post(token, instance, sdm_relationships_endpoint(args.sdm), payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    queryable = (resp or {}).get("isQueryable", "")
    print(f"\n✓ Added relationship: {api_name}", file=sys.stderr)
    if queryable:
        print(f"  isQueryable: {queryable}", file=sys.stderr)
    print(
        "\nVerify the join with a cross-object query (a field from each object "
        "in one query). See references/sdm-creation-api.md.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
