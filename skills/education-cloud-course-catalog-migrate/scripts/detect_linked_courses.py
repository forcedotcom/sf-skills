#!/usr/bin/env python3
"""Pair lecture/lab course codes by suffix.

Reads a JSON array of course code strings from stdin. A code is treated as a
lab section of another code if it equals that code plus one of the configured
suffixes (default: L, LAB). Prints a JSON array of {"lecture", "lab"} pairs
for every match found; codes with no match are omitted.

Usage:
    python3 scripts/detect_linked_courses.py --suffixes L,LAB,-L
"""

from __future__ import annotations

import argparse
import json
import sys


def normalize(code: str) -> str:
    return code.strip().upper()


def detect(codes: list[str], suffixes: list[str]) -> list[dict]:
    normalized = {normalize(c): c for c in codes}
    pairs = []
    for norm_code, original in normalized.items():
        for suffix in suffixes:
            if norm_code.endswith(suffix) and len(norm_code) > len(suffix):
                base = norm_code[: -len(suffix)]
                if base in normalized:
                    pairs.append({"lecture": normalized[base], "lab": original})
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffixes", default="L,LAB", help="Comma-separated lab-code suffixes")
    args = parser.parse_args()

    codes = json.load(sys.stdin)
    suffixes = [s.strip().upper() for s in args.suffixes.split(",") if s.strip()]

    pairs = detect(codes, suffixes)
    json.dump(pairs, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
