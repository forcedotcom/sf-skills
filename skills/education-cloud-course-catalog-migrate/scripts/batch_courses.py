#!/usr/bin/env python3
"""Split a list of course records into fixed-size batches.

Reads a JSON array of course record objects from stdin. Prints a JSON array
of batches (each a list of records), each capped at --batch-size records —
the Composite API's per-call record limit.

Usage:
    python3 scripts/batch_courses.py --batch-size 200
"""

from __future__ import annotations

import argparse
import json
import sys


def batch(records: list[dict], size: int) -> list[list[dict]]:
    return [records[i : i + size] for i in range(0, len(records), size)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    records = json.load(sys.stdin)
    batches = batch(records, args.batch_size)
    json.dump(batches, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
