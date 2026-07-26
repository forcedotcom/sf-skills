#!/usr/bin/env python3
"""Create semantic metrics on semantic models.

Metrics reference calculated fields via measurementReference and require a time dimension.

Usage:
    # Step 1: Create calculated field first
    python scripts/create_calc_field.py \\
      --sdm Sales_Cloud12_backward \\
      --type measurement \\
      --name Total_Revenue_clc \\
      --label "Total Revenue" \\
      --expression "SUM([Amount])" \\
      --aggregation Sum

    # Step 2: Create metric referencing the calculated field
    python scripts/create_metric.py \\
      --sdm Sales_Cloud12_backward \\
      --name Total_Revenue_mtc \\
      --label "Total Revenue" \\
      --calculated-field Total_Revenue_clc \\
      --time-field Close_Date \\
      --time-table Opportunity_TAB_Sales_Cloud

    # Dry-run (show payload without POSTing)
    python scripts/create_metric.py \\
      --sdm Sales_Cloud12_backward \\
      --name Account_Count_mtc \\
      --label "Account Count" \\
      --calculated-field Account_Count_clc \\
      --time-field Close_Date \\
      --time-table Opportunity_TAB_Sales_Cloud \\
      --dry-run
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from _shared.metric_templates import (
    METRIC_TEMPLATE_REGISTRY,
    build_semantic_metric,
    parse_metric_filter,
    validate_metric,
)
from _shared.sf_api import calculated_field_endpoint, get_credentials, sf_post
from _shared.verify import report_verification, verify_metric_has_data


def resolve_expression(
    template: Optional[str],
    template_args: Optional[str],
    expression: Optional[str]
) -> str:
    """Resolve expression from template or use provided expression.

    Args:
        template: Template name (sum, avg, win_rate, etc.)
        template_args: JSON string with template arguments
        expression: Direct expression string

    Returns:
        Resolved expression string
    """
    if template:
        if template not in METRIC_TEMPLATE_REGISTRY:
            print(
                f"Error: Unknown template '{template}'. Valid: {', '.join(METRIC_TEMPLATE_REGISTRY.keys())}",
                file=sys.stderr
            )
            sys.exit(1)

        if not template_args:
            print(f"Error: --template-args required when using --template", file=sys.stderr)
            sys.exit(1)

        try:
            args = json.loads(template_args)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --template-args: {e}", file=sys.stderr)
            sys.exit(1)

        template_func = METRIC_TEMPLATE_REGISTRY[template]
        try:
            return template_func(**args)
        except TypeError as e:
            print(f"Error: Template '{template}' arguments mismatch: {e}", file=sys.stderr)
            print(
                f"Expected arguments: {template_func.__code__.co_varnames[:template_func.__code__.co_argcount]}",
                file=sys.stderr
            )
            sys.exit(1)

    if expression:
        return expression

    print("Error: Either --template or --expression must be provided", file=sys.stderr)
    sys.exit(1)


def normalize_api_name(name: str) -> str:
    """Ensure API name ends with _mtc and doesn't have double underscores.
    
    Salesforce API names cannot contain double underscores (__).

    Args:
        name: API name

    Returns:
        Normalized API name (no double underscores, ends with _mtc)
    """
    name = name.strip()
    # Replace double underscores with single underscore
    while "__" in name:
        name = name.replace("__", "_")
    if not name.endswith("_mtc"):
        return f"{name}_mtc"
    return name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create semantic metrics on semantic models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--sdm", required=True, help="Semantic model API name")
    parser.add_argument("--name", required=True, help="API name (auto-appends _mtc if missing)")
    parser.add_argument("--label", required=True, help="Display label")

    # Calculated field reference (preferred method)
    parser.add_argument("--calculated-field", required=True, help="API name of calculated field to reference")
    
    # Time dimension (required for metrics)
    parser.add_argument("--time-field", required=True, help="Time dimension field API name (e.g., Close_Date)")
    parser.add_argument("--time-table", required=True, help="Time dimension table API name (e.g., Opportunity_TAB_Sales_Cloud)")

    # Legacy expression support (deprecated - metrics should reference calculated fields)
    expr_group = parser.add_mutually_exclusive_group(required=False)
    expr_group.add_argument("--expression", help="[DEPRECATED] Tableau formula expression - use --calculated-field instead")
    expr_group.add_argument("--template", choices=list(METRIC_TEMPLATE_REGISTRY.keys()), help="[DEPRECATED] Template name - use --calculated-field instead")

    parser.add_argument("--template-args", help="JSON dict of template arguments (required with --template)")
    parser.add_argument("--description", default="", help="Field description")

    # Additional dimensions for breakdown analysis
    parser.add_argument(
        "--additional-dimension",
        action="append",
        help="Additional dimension for breakdown analysis (format: fieldApiName:tableApiName). Can be repeated multiple times."
    )

    # Identifying dimension (the field the TN metric UI dereferences on load)
    parser.add_argument(
        "--identifying-dimension",
        help=(
            "Field used as the metric's identifying dimension "
            "(format: fieldApiName:tableApiName). Defaults to the first "
            "--additional-dimension. The TN metric UI crashes without it. "
            "If not already an additional dimension, it is added to the list."
        )
    )

    # Metric filters. The field must be fully qualified (Table.Field); it is
    # auto-mirrored into additionalDimensions so the metric stays queryable, and
    # filterLogic ("1 AND 2 AND ...") is auto-generated.
    parser.add_argument(
        "--filter",
        action="append",
        dest="filters",
        help=(
            "Metric filter (format: '<Table>.<Field> <op> <value>', e.g. "
            "'Opportunity.Region = West'). Operators (verified live): "
            "= (Equals), > (GreaterThan), < (LessThan), In, NotIn, Contains, "
            "NotContains, Between, StartsWith. No >=/<=/!= on the server. "
            "Field must be qualified Table.Field. Can be repeated."
        )
    )

    parser.add_argument(
        "--allow-junk-time-anchor",
        action="store_true",
        help=(
            "Override the junk-date guard and allow anchoring on a "
            "system/plumbing date (e.g. cdp_sys_PartitionDate, *_SourceVersion). "
            "By default such anchors are rejected — prefer a business event date."
        )
    )

    parser.add_argument("--dry-run", action="store_true", help="Show payload without POSTing")
    parser.add_argument("--skip-verify", action="store_true",
                        help="Skip the post-create query that confirms the metric returns data")
    parser.add_argument("--verify-only", action="store_true",
                        help="Do not create; only query the EXISTING metric (--name) and report "
                             "whether it returns data (verified-done / NOT-shippable). Use this to "
                             "re-check an already-created metric — never re-run a create on one.")
    parser.add_argument("-o", "--output", help="Write JSON to file (default: stdout)")

    args = parser.parse_args()

    # Verify-only: skip creation, just query the existing metric for data.
    if args.verify_only:
        existing = normalize_api_name(args.name)
        has_data, verify_err = verify_metric_has_data(args.sdm, existing)
        return report_verification("metric", existing, has_data, verify_err, created=False)

    # Use calculated field reference (required)
    calculated_field_api_name = args.calculated_field
    
    # Warn if legacy expression/template args are provided
    if args.expression or args.template:
        print("Warning: --expression and --template are deprecated. Using --calculated-field instead.", file=sys.stderr)

    # Parse additional dimensions
    additional_dims = []
    if args.additional_dimension:
        for dim_spec in args.additional_dimension:
            if ":" not in dim_spec:
                print(
                    f"Error: Invalid format for --additional-dimension: {dim_spec}. Expected format: fieldApiName:tableApiName",
                    file=sys.stderr
                )
                sys.exit(1)
            field_name, table_name = dim_spec.split(":", 1)
            additional_dims.append({
                "tableFieldReference": {
                    "fieldApiName": field_name.strip(),
                    "tableApiName": table_name.strip()
                }
            })

    # Parse identifying dimension override (same format as --additional-dimension)
    identifying_dim = None
    if args.identifying_dimension:
        if ":" not in args.identifying_dimension:
            print(
                f"Error: Invalid format for --identifying-dimension: {args.identifying_dimension}. Expected format: fieldApiName:tableApiName",
                file=sys.stderr
            )
            sys.exit(1)
        field_name, table_name = args.identifying_dimension.split(":", 1)
        identifying_dim = {
            "tableFieldReference": {
                "fieldApiName": field_name.strip(),
                "tableApiName": table_name.strip()
            }
        }

    # Parse metric filters (qualified Table.Field; auto-mirrored + filterLogic in builder)
    metric_filters = []
    if args.filters:
        for filter_spec in args.filters:
            try:
                metric_filters.append(parse_metric_filter(filter_spec))
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

    # Normalize API name
    api_name = normalize_api_name(args.name)

    # Validate
    is_valid, errors = validate_metric(
        api_name=api_name,
        expression=None  # No expression validation needed for calculated field reference
    )
    if not is_valid:
        print("Validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Build payload (raises ValueError on additionalDimensions superset violations)
    try:
        payload = build_semantic_metric(
            api_name=api_name,
            label=args.label,
            calculated_field_api_name=calculated_field_api_name,
            time_dimension_field_name=args.time_field,
            time_dimension_table_name=args.time_table,
            description=args.description,
            additional_dimensions=additional_dims if additional_dims else None,
            identifying_dimension=identifying_dim,
            filters=metric_filters if metric_filters else None,
            allow_junk_time_anchor=args.allow_junk_time_anchor,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

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
    endpoint = calculated_field_endpoint(args.sdm, "metrics")

    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    actual_name = api_name
    if resp:
        actual_name = resp.get('apiName', api_name)
        print(f"\n✓ Created semantic metric: {api_name}", file=sys.stderr)
        if actual_name != api_name:
            print(f"  → Actual API name: {actual_name}", file=sys.stderr)
        if "label" in resp:
            print(f"  Label: {resp['label']}", file=sys.stderr)
    else:
        print(f"\n✓ Semantic metric created successfully", file=sys.stderr)

    # Verify-by-querying: a created metric that returns no data is NOT shippable.
    # Creation success is not data success — confirm before declaring done.
    if args.skip_verify:
        return 0
    has_data, verify_err = verify_metric_has_data(args.sdm, actual_name)
    return report_verification("metric", actual_name, has_data, verify_err)


if __name__ == "__main__":
    sys.exit(main())
