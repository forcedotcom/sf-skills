#!/usr/bin/env python3
"""Data-presence gate for DLO/DMO objects.

Prove an object returns rows before authoring fields/metrics on it. Field-richness
is not data-presence: an object can carry dozens of fields and still return zero
rows. See references/empty-source-handling.md.

Exit codes:
    0 — count > 0 (shippable)
    1 — indeterminate (count query failed / unreadable; treat as advisory, not empty)
    2 — count == 0 (confirmed empty; do NOT build on it)

Usage:
    python scripts/query_data.py --count <Object__dll-or-__dlm>
    python scripts/query_data.py --count <Object> --dataspace <ds>
"""

import argparse
import sys

from _shared.query import count_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Confirm a DLO/DMO returns rows before authoring on it."
    )
    parser.add_argument(
        "--count",
        metavar="OBJECT",
        required=True,
        help="Object API name (e.g. Account_Home__dll or Opportunity__dlm).",
    )
    parser.add_argument(
        "--dataspace",
        default=None,
        help="Optional dataspace; omit for the org default.",
    )
    args = parser.parse_args()

    count, err = count_rows(args.count, dataspace=args.dataspace)
    if count is None:
        print(
            f"INDETERMINATE: could not confirm data presence for '{args.count}' ({err}). "
            "Advisory only — a transient query failure must not false-block authoring.",
            file=sys.stderr,
        )
        sys.exit(1)
    if count == 0:
        print(
            f"EMPTY: '{args.count}' returned 0 rows. NOT shippable — anything built on "
            "it will render 'No results to show.' See empty-source-handling.md."
        )
        sys.exit(2)
    print(f"OK: '{args.count}' has {count} row(s). Shippable.")


if __name__ == "__main__":
    main()
