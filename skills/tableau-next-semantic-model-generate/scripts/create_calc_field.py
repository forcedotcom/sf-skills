#!/usr/bin/env python3
"""Create calculated measurements and dimensions on semantic models.

Usage:
    # Free-form measurement (with aggregation in expression → auto UserAgg)
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_SDM_1772196180 \\
      --type measurement \\
      --name Avg_Deal_Size_clc \\
      --label "Average Deal Size" \\
      --expression "AVG([Amount])" \\
      --aggregation Avg

    # Template-based
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_SDM_1772196180 \\
      --template win_rate \\
      --template-args '{"won_field": "Stage_Won_Count", "total_field": "Stage_Total_Count"}' \\
      --name Win_Rate_clc \\
      --label "Win Rate"

    # Boolean dimension
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_SDM_1772196180 \\
      --type dimension \\
      --name Is_Large_Deal_clc \\
      --label "Is Large Deal?" \\
      --expression "[Amount] > 100000" \\
      --data-type Boolean

    # Dry-run (show payload without POSTing)
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_SDM_1772196180 \\
      --template bucket_amount \\
      --template-args '{"field": "Amount", "small_threshold": 10000, "medium_threshold": 50000}' \\
      --name Deal_Size_Bucket_clc \\
      --label "Deal Size" \\
      --dry-run
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from _shared.calc_field_templates import (
    TEMPLATE_REGISTRY,
    build_calculated_dimension,
    build_calculated_measurement,
    validate_calc_field,
)
from _shared.sf_api import calculated_field_endpoint, get_credentials, sf_post
from _shared.verify import report_verification, verify_calc_field_has_data


def resolve_expression(
    template: Optional[str],
    template_args: Optional[str],
    expression: Optional[str]
) -> str:
    """Resolve expression from template or use provided expression.

    Args:
        template: Template name (win_rate, days_between, etc.)
        template_args: JSON string with template arguments
        expression: Direct expression string

    Returns:
        Resolved expression string
    """
    if template:
        if template not in TEMPLATE_REGISTRY:
            print(f"Error: Unknown template '{template}'. Valid: {', '.join(TEMPLATE_REGISTRY.keys())}", file=sys.stderr)
            sys.exit(1)

        if not template_args:
            print(f"Error: --template-args required when using --template", file=sys.stderr)
            sys.exit(1)

        try:
            args = json.loads(template_args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --template-args: {e}", file=sys.stderr)
            sys.exit(1)

        template_func = TEMPLATE_REGISTRY[template]
        try:
            return template_func(**args)
        except TypeError as e:
            print(f"Error: Template '{template}' arguments mismatch: {e}", file=sys.stderr)
            print(f"Expected arguments: {template_func.__code__.co_varnames[:template_func.__code__.co_argcount]}", file=sys.stderr)
            sys.exit(1)

    if expression:
        return expression

    print("Error: Either --template or --expression must be provided", file=sys.stderr)
    sys.exit(1)


def normalize_api_name(name: str) -> str:
    """Ensure API name ends with _clc and doesn't have double underscores.
    
    Salesforce API names cannot contain double underscores (__).

    Args:
        name: API name

    Returns:
        Normalized API name (no double underscores, ends with _clc)
    """
    name = name.strip()
    # Replace double underscores with single underscore
    while "__" in name:
        name = name.replace("__", "_")
    if not name.endswith("_clc"):
        return f"{name}_clc"
    return name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create calculated measurements and dimensions on semantic models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--sdm", required=True, help="Semantic model API name")
    parser.add_argument("--type", required=True, choices=["measurement", "dimension"], help="Field type")
    parser.add_argument("--name", required=True, help="API name (auto-appends _clc if missing)")
    parser.add_argument("--label", required=True, help="Display label")

    # Expression source (mutually exclusive). Not required at the argparse layer
    # so --verify-only can run without it; the create path enforces it below.
    expr_group = parser.add_mutually_exclusive_group(required=False)
    expr_group.add_argument("--expression", help="Tableau formula expression")
    expr_group.add_argument("--template", choices=list(TEMPLATE_REGISTRY.keys()), help="Template name")

    parser.add_argument("--template-args", help="JSON dict of template arguments (required with --template)")

    # Measurement-specific
    parser.add_argument("--aggregation", default="UserAgg",
                        choices=["Sum", "Avg", "Count", "Min", "Max", "UserAgg", "Median"],
                        help="Aggregation type (for measurements, default: UserAgg)")
    parser.add_argument("--data-type", choices=["Number", "Text", "Boolean", "DateTime"],
                        help="Data type (default: Number for measurements, inferred for dimensions)")
    parser.add_argument("--decimal-places", type=int, default=2, help="Decimal places for Number fields (default: 2)")
    parser.add_argument("--description", default="", help="Field description")

    parser.add_argument("--dry-run", action="store_true", help="Show payload without POSTing")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip the post-create query that confirms the field returns data")
    parser.add_argument("--verify-only", action="store_true",
                        help="Do not create; only query the EXISTING calc field (--name) and report "
                             "whether it returns data (verified-done / NOT-shippable). Use this to "
                             "re-check an already-created field — never re-run a create on one.")
    parser.add_argument("-o", "--output", help="Write JSON to file (default: stdout)")

    args = parser.parse_args()

    # Verify-only: skip creation, just query the existing calc field for data.
    if args.verify_only:
        existing = normalize_api_name(args.name)
        has_data, verify_err = verify_calc_field_has_data(args.sdm, existing)
        return report_verification("calc field", existing, has_data, verify_err, created=False)

    # Resolve expression
    expression = resolve_expression(args.template, args.template_args, args.expression)

    # Normalize API name
    api_name = normalize_api_name(args.name)

    # Determine data type
    data_type = args.data_type
    if not data_type:
        if args.type == "measurement":
            data_type = "Number"
        else:
            # Try to infer from expression (basic heuristics)
            if "THEN" in expression.upper() or "IF" in expression.upper():
                data_type = "Text"  # Likely a bucketing or conditional
            else:
                data_type = "Text"  # Default for dimensions

    # Validate
    is_valid, errors = validate_calc_field(
        api_name=api_name,
        field_type=args.type,
        aggregation_type=args.aggregation if args.type == "measurement" else None,
        data_type=data_type,
        expression=expression
    )
    if not is_valid:
        print("Validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Build payload
    if args.type == "measurement":
        payload = build_calculated_measurement(
            api_name=api_name,
            label=args.label,
            expression=expression,
            aggregation_type=args.aggregation,
            data_type=data_type,
            decimal_place=args.decimal_places,
            description=args.description,
        )
    else:
        payload = build_calculated_dimension(
            api_name=api_name,
            label=args.label,
            expression=expression,
            data_type=data_type,
            description=args.description,
        )

    # Output payload
    output_json = json.dumps(payload, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
            f.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output_json)

    # Dry-run mode - exit before POST
    if args.dry_run:
        print("\n[Dry-run mode - payload shown above, not POSTed]", file=sys.stderr)
        return 0

    # POST to API
    token, instance = get_credentials()
    endpoint = calculated_field_endpoint(args.sdm, f"{args.type}s")  # measurement -> measurements

    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    actual_name = api_name
    if resp:
        actual_name = resp.get('apiName', api_name)
        print(f"\n✓ Created calculated {args.type}: {api_name}", file=sys.stderr)
        if actual_name != api_name:
            print(f"  → Actual API name: {actual_name}", file=sys.stderr)
        if "label" in resp:
            print(f"  Label: {resp['label']}", file=sys.stderr)
    else:
        print(f"\n✓ Calculated {args.type} created successfully", file=sys.stderr)

    # Verify-by-querying: a created field that returns no data is NOT shippable.
    # Creation success is not data success — confirm before declaring done.
    if args.skip_verify:
        return 0
    has_data, verify_err = verify_calc_field_has_data(args.sdm, actual_name)
    return report_verification("calc field", actual_name, has_data, verify_err)


if __name__ == "__main__":
    sys.exit(main())
