#!/usr/bin/env bash
# Procure a selected phone number.
# Usage: procure-number.sh <org-alias> <country> <phone-type> <phone-number>
# Output: JSON response body on stdout. Non-zero exit on API error.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 4 ]]; then
  echo "Usage: procure-number.sh <org-alias> <country> <phone-type> <phone-number>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; COUNTRY="$2"; PHONE_TYPE="$3"; NUMBER="$4"

BODY=$(jq -n --arg t "$PHONE_TYPE" --arg c "$COUNTRY" --arg p "$NUMBER" \
  '{phoneNumberType:$t, country:$c, phoneNumber:$p}')

sf api request rest \
  "/${NM_BASE}/number" \
  --method POST \
  --body "$BODY" \
  --target-org "$ALIAS"
