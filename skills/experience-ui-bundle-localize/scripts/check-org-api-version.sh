#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
#
# check-org-api-version.sh — Verify a target org supports API v68.0+ (Release 264).
#
# Runtime label resolution over GraphQL for UI Bundles ships in Salesforce
# Release 264 (API v68.0+). A `sourceApiVersion` in sfdx-project.json records
# what you declared, not what the org supports, so a newer CLI pointed at an
# older org can pass a static file check and then fail at runtime. This queries
# the org's actual maximum API version before you wire anything.
#
# `sf api request rest` keeps authentication at the CLI transport layer, so no
# access token enters this script's context. Do not extract a token and curl.
#
# Usage:
#   bash <skill-dir>/scripts/check-org-api-version.sh <org-alias-or-username>
#
# Exit codes:
#   0  org supports v68.0+ — proceed
#   1  org's max API version is below v68.0, or it could not be determined — stop

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  echo "ERROR: pass exactly one org alias or username. Usage: check-org-api-version.sh <org-alias-or-username>" >&2
  exit 1
fi
ORG="$1"

# FORCE_COLOR=0 stops the CLI from emitting ANSI color codes into stdout JSON,
# which would otherwise make jq fail with "Invalid numeric literal".
MAX_API=$(FORCE_COLOR=0 sf api request rest "/services/data/" --target-org "$ORG" \
          | jq -r '[.[].version | tonumber] | max') \
  || { echo "ERROR: could not determine the target org's API version (auth or network problem?). Verify the org is reachable, then retry." >&2; exit 1; }

[ -n "$MAX_API" ] && [ "$MAX_API" != "null" ] \
  || { echo "ERROR: the org returned an empty API version. Verify the target org and retry." >&2; exit 1; }

awk -v v="$MAX_API" 'BEGIN{ exit !(v+0 >= 68.0) }' \
  || { echo "ERROR: runtime label localization for UI Bundles requires Salesforce Release 264 (API v68.0+). Target org's maximum supported API version is v${MAX_API}. Retarget a Release 264+ org, or upgrade the org before adding localization." >&2; exit 1; }

echo "OK: target org '${ORG}' supports API v${MAX_API} (>= v68.0). Proceed."
