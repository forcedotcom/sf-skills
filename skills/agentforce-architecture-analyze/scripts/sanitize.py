#!/usr/bin/env python3
"""Scrub dangerous characters from a string before splicing into the RESULT block.

Strips characters that would corrupt the `KEY=VALUE` line format parsers use to read
the RESULT block: backtick, dollar, double-quote, backslash, CR, tab, NUL, newline.

Used when interpolating user-controlled values (session_id, org_alias, sf CLI stderr
excerpts) into ERROR_DETAIL and other RESULT fields. Without scrubbing, a malicious
or malformed input could inject fake KEY=VALUE pairs that downstream consumers
would treat as authoritative.

Usage:
    _safe=$(python3 "$SKILL/scripts/sanitize.py" "$raw_value")

Arguments:
    argv[1]  raw string (may be empty)

Output:
    stdout   scrubbed string (no trailing newline)
    exit 0   always (even on empty input)
"""
import sys

BAD = set("`$\"\\\r\t\0\n")


def scrub(s: str) -> str:
    return "".join(c for c in s if c not in BAD)


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.stdout.write(scrub(raw))
