#!/usr/bin/env python3
"""Update an existing semantic metric — the SAFE (full-payload PUT) way.

Metric update is a full-payload PUT: the body REPLACES the metric definition, so
a single-field change must re-send the COMPLETE metric or the server silently
drops ``insightsSettings`` / ``additionalDimensions`` / ``identifyingDimension``
(a partial body drops additionalDimensions to empty). This script does
resolve-and-merge: GET the metric's full definition, overlay only the
requested change, then PUT the complete body.

Use this to set the ``identifyingDimension`` (which the Tableau Next metric UI
dereferences on load — a metric without it can crash the UI) or the
time-comparison settings on an existing metric. Metric CREATION stays in
create_metric.py (untouched).

Usage:
    # Set the identifying dimension (same-object)
    python scripts/update_metric.py Workforce_SDM Headcount_mtc \\
      --identifying-dimension "position_title:qb_hw_position"

    # Cross-object identifying dimension (Field:Object on a joined object)
    python scripts/update_metric.py Hotel_SDM ADR_mtc \\
      --identifying-dimension "Date:Daily_Property_Performance"

    # Set time comparisons
    python scripts/update_metric.py Sales_SDM Total_Sales_mtc \\
      --primary-comparison PriorPeriod --secondary-comparison PriorYear

    # Dry-run: print the FULL PUT body without calling the org
    python scripts/update_metric.py Workforce_SDM Headcount_mtc \\
      --identifying-dimension "gender:qb_hw_employee" --dry-run
"""

import argparse
import json
import sys

from _shared.sdm_ai_templates import build_metric_put_payload
from _shared.sdm_discovery import get_metric_definition
from _shared.sf_api import (
    get_credentials,
    metric_endpoint,
    parse_too_large_error,
    sf_put,
)


def explain_too_large_error(err: str):
    """Translate the server's 'data value too large (max length=N)' 400 for a metric.

    Returns actionable guidance naming the over-long field + its cap, or None when
    ``err`` is not a length-cap error (caller prints the raw message).
    """
    parsed = parse_too_large_error(err)
    if parsed is None:
        return None
    field, max_len = parsed
    if field is None:
        return "The server rejected the update: a metric field value is too long."
    limit = f" of {max_len} characters" if max_len is not None else ""
    return (
        f"The server rejected the update: the metric '{field}' field exceeds its "
        f"maximum length{limit} (measured on the raw input). Shorten it."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update an existing metric via full-payload PUT (resolve-and-merge).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("sdm", help="SDM apiName")
    parser.add_argument("metric", help="Metric apiName (e.g. Headcount_mtc)")
    parser.add_argument(
        "--identifying-dimension",
        help="Set insightsSettings.identifyingDimension. Format 'Field:Object' "
             "(fieldApiName:tableApiName); cross-object is allowed (the object "
             "can be a joined one). The field is mirrored into "
             "additionalDimensions if absent (the UI requires membership).",
    )
    parser.add_argument("--primary-comparison",
                        help="Set primaryTimeComparison (top-level time-comparison field).")
    parser.add_argument("--secondary-comparison",
                        help="Set secondaryTimeComparison.")
    parser.add_argument("--description", help="Replace the metric description.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the full PUT body and exit without calling the org.")
    args = parser.parse_args()

    if not any([args.identifying_dimension, args.primary_comparison,
                args.secondary_comparison, args.description]):
        print(
            "Error: nothing to change. Provide at least one of "
            "--identifying-dimension, --primary-comparison, --secondary-comparison, "
            "--description.",
            file=sys.stderr,
        )
        return 1

    # RESOLVE: fetch the metric's FULL definition (the body the PUT must re-send
    # in full). On --dry-run without creds this still needs the metric; we fetch
    # it (the get_credentials call inside will exit if unset). To keep --dry-run
    # usable without an org, a --from-file override is out of scope; dry-run still
    # resolves the live metric so the printed body is real.
    existing = get_metric_definition(args.sdm, args.metric)
    if existing is None:
        print(
            f"Error: could not read metric '{args.metric}' on SDM '{args.sdm}'. "
            f"A full-payload PUT requires the current definition to merge into.",
            file=sys.stderr,
        )
        return 1

    # MERGE: overlay only the requested change onto the full definition.
    try:
        payload = build_metric_put_payload(
            existing,
            identifying_dimension=args.identifying_dimension,
            primary_comparison=args.primary_comparison,
            secondary_comparison=args.secondary_comparison,
            description=args.description,
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
    resp, err = sf_put(token, instance, metric_endpoint(args.sdm, args.metric), payload)
    if err:
        # Catch the server's length-cap rejection and re-surface it clearly.
        friendly = explain_too_large_error(err)
        print(f"Error: {friendly or err}", file=sys.stderr)
        return 1

    print(f"\n✓ Updated metric: {args.metric}", file=sys.stderr)
    # Confirm actual state, not just the success code — discovery is the proof
    # that identifyingDimension survived the PUT.
    print(
        f"  Verify with: python scripts/discover_sdm.py {args.sdm} --metric {args.metric} "
        f"(confirm insightsSettings.identifyingDimension is still present).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
