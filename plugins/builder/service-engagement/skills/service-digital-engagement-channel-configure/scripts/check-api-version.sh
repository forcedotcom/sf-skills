#!/bin/bash
# Verifies the target org's API version meets the minimum requirement.
# Usage: check-api-version.sh <min-version> <org-alias>
# Exits 0 if version >= min-version, exits 1 with error message otherwise.

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
  echo "ERROR: Could not determine API version for org '$ORG_ALIAS'."
  exit 1
fi

if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)" "$API_VERSION" "$MIN_VERSION"; then
  echo "OK: Org API version $API_VERSION meets minimum $MIN_VERSION."
  exit 0
else
  echo "ERROR: Org API version $API_VERSION is below minimum $MIN_VERSION. Generate a sfdx-project.json with \"sourceApiVersion\": \"$MIN_VERSION\" in the metadata output folder."
  exit 1
fi
