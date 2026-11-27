#!/usr/bin/env bash
# Delete a voice config by Id (the org default cannot be deleted — API returns 400).
# Usage: delete-configuration.sh <org-alias> <configId>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: delete-configuration.sh <org-alias> <configId>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; CONFIG_ID="$2"

# Validate the Id before building the URL: an empty or malformed value would
# otherwise produce `DELETE /configurations/` (or a bad path) and hit the wrong
# endpoint. Voice configurations use the `1pK` key prefix and a 15- or 18-char Id.
if [[ ! "$CONFIG_ID" =~ ^1pK[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
  echo "delete-configuration.sh: '$CONFIG_ID' is not a valid voice configuration Id (expected a 15- or 18-char Id with the 1pK key prefix)" >&2
  exit 2
fi

# `sf api request rest` only attaches the required body `mode` when --body is
# non-empty; a DELETE with no body fails with "No 'mode' found in 'body' entry".
# Pass a dummy empty-object body (the API ignores it for DELETE) to satisfy the CLI.
sf api request rest \
  "/${VC_BASE}/configurations/$(urlenc "$CONFIG_ID")" \
  --method DELETE \
  --body '{}' \
  --target-org "$ALIAS"
