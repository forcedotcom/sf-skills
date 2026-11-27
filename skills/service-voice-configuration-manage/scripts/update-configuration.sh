#!/usr/bin/env bash
# Update a voice config. Body = update-input JSON (required: name; no developerName;
# userIds/profileIds replace the full list). Usage: update-configuration.sh <org-alias> <configId> <json-body>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 3 ]]; then
  echo "Usage: update-configuration.sh <org-alias> <configId> <json-body>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; CONFIG_ID="$2"; BODY="$3"

sf api request rest \
  "/${VC_BASE}/configurations/$(urlenc "$CONFIG_ID")" \
  --method PUT \
  --body "$BODY" \
  --target-org "$ALIAS"
