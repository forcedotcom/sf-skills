#!/usr/bin/env bash
# Retrieve a single voice configuration by Id.
# Usage: get-configuration.sh <org-alias> <configId>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: get-configuration.sh <org-alias> <configId>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; CONFIG_ID="$2"

sf api request rest \
  "/${VC_BASE}/configurations/$(urlenc "$CONFIG_ID")" \
  --target-org "$ALIAS"
