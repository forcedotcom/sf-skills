#!/usr/bin/env python3
"""Extract the org's current max REST API version from a headless-360 endpoint map.

Reads the JSON object returned by `GET /services/data/` (no version segment) from
stdin — a map of endpoint name to path, e.g. {"limits": "/services/data/v69.0/limits",
...}, not a `{version, label, url}` list. Scans every value for a `vNN.N` segment and
prints the highest one found as {"version": "69.0"}.

Usage:
    python3 scripts/resolve_api_version.py < endpoint_map.json
"""

from __future__ import annotations

import json
import re
import sys

VERSION_RE = re.compile(r"v(\d+\.\d+)")


def resolve(endpoint_map: dict) -> str:
    versions = set()
    for value in endpoint_map.values():
        if isinstance(value, str):
            match = VERSION_RE.search(value)
            if match:
                versions.add(match.group(1))
    if not versions:
        raise ValueError("No vNN.N version found in any endpoint path")
    return max(versions, key=lambda v: tuple(int(p) for p in v.split(".")))


def main() -> int:
    endpoint_map = json.load(sys.stdin)
    version = resolve(endpoint_map)
    json.dump({"version": version}, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
