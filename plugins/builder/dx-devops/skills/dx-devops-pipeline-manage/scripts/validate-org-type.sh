#!/usr/bin/env bash
# Validate a stage-environment --org-type value against the fixed CLI enum.
# Usage: scripts/validate-org-type.sh <org-type>
# Exits 0 if the value is exactly "Production" or "Sandbox"; otherwise prints
# an actionable error and exits 1.

set -euo pipefail

ORG_TYPE="${1:-}"

if [ "$ORG_TYPE" = "Production" ] || [ "$ORG_TYPE" = "Sandbox" ]; then
  echo "OK: --org-type '$ORG_TYPE' is valid"
  exit 0
fi

echo "ERROR: --org-type must be exactly 'Production' or 'Sandbox' (case-sensitive). Got: '${ORG_TYPE}'" >&2
exit 1
