#!/usr/bin/env bash
# Create a voice config. Body = create-input JSON (required: name); see references/voice_config_api.md.
# Usage: create-configuration.sh <org-alias> <json-body>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: create-configuration.sh <org-alias> <json-body>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; BODY="$2"

sf api request rest \
  "/${VC_BASE}/configurations" \
  --method POST \
  --body "$BODY" \
  --target-org "$ALIAS"
