#!/bin/bash
# inspect-dataspace-scopes.sh — extract dataspaceScopes from retrieved PermissionSet metadata
# Usage: scripts/inspect-dataspace-scopes.sh <retrieved-dir> [dataspace-api-name]
# Output: PermissionSet|dataspaceScope|dataAccessLevel|objectAccessLevel (one per line)
#         "NO_PERMISSIONSETS_FOUND" if retrieval yielded no permission sets, or
#         "NO_MATCHES" if no retrieved permission set matched
set -euo pipefail

RETRIEVED_DIR="${1:-}"
DATASPACE_FILTER="${2:-}"

[[ -d "$RETRIEVED_DIR" ]] || {
  echo "ERROR: retrieved-dir '$RETRIEVED_DIR' not found" >&2
  exit 1
}

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 required" >&2
  exit 1
}

python3 - "$RETRIEVED_DIR" "$DATASPACE_FILTER" <<'PYEOF'
import sys, os, glob, xml.etree.ElementTree as ET

retrieved_dir, dataspace_filter = sys.argv[1], sys.argv[2]
ns = {"md": "http://soap.sforce.com/2006/04/metadata"}
rows = []
paths = sorted(glob.glob(
    os.path.join(retrieved_dir, "**", "*.permissionset-meta.xml"), recursive=True
))

if not paths:
    print("NO_PERMISSIONSETS_FOUND")
    sys.exit()

for path in paths:
    permset_name = os.path.basename(path).replace(".permissionset-meta.xml", "")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        continue

    for scope in root.findall("md:dataspaceScopes", ns):
        name = (scope.findtext("md:dataspaceScope", "", ns) or "").strip()
        if dataspace_filter and name != dataspace_filter:
            continue

        rows.append((
            permset_name,
            name,
            (scope.findtext("md:dataAccessLevel", "", ns) or "").strip(),
            (scope.findtext("md:objectAccessLevel", "", ns) or "").strip()
        ))

print("NO_MATCHES" if not rows else "\n".join("|".join(r) for r in rows))
PYEOF
