#!/usr/bin/env bash
# List all voice configurations for the org.
# Usage: list-configurations.sh <org-alias>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: list-configurations.sh <org-alias>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"

sf api request rest \
  "/${VC_BASE}/configurations" \
  --target-org "$ALIAS"
