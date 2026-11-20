#!/bin/bash
# Verifies the target org's API version meets the minimum requirement.
# Usage: check-api-version.sh <min-version> <org-alias>
# Exit 0: version >= min-version (last line: ORG_API_VERSION=<version>).
# Exit 1: version below minimum. Exit 2: version could not be determined.
# The version comes from `sf org display`, else the highest entry of the org's /services/data/ list.

MIN_VERSION="${1:?Usage: check-api-version.sh <min-version> <org-alias>}"
ORG_ALIAS="${2:?Usage: check-api-version.sh <min-version> <org-alias>}"

API_VERSION=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('result', {}).get('apiVersion', ''))
except Exception:
    print('')
")

if [ -z "$API_VERSION" ]; then
  API_VERSION=$(sf api request rest "/services/data/" --target-org "$ORG_ALIAS" 2>/dev/null | python3 -c "
import json, sys
try:
    versions = [float(v['version']) for v in json.load(sys.stdin)]
    print(max(versions))
except Exception:
    print('')
")
fi

if [ -z "$API_VERSION" ]; then
  echo "WARNING: Could not determine API version for org '$ORG_ALIAS'."
  exit 2
fi

if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)" "$API_VERSION" "$MIN_VERSION"; then
  echo "OK: Org API version $API_VERSION meets minimum $MIN_VERSION."
  echo "ORG_API_VERSION=$API_VERSION"
  exit 0
else
  echo "ERROR: Org API version $API_VERSION is below minimum $MIN_VERSION. Use an org on the current Salesforce release (a sandbox or scratch org is fine), or ask your admin to confirm the org's release."
  exit 1
fi
