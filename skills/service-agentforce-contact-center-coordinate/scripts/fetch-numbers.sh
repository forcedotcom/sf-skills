#!/usr/bin/env bash
# Fetch available default phone numbers for a country + phone-number type.
# Usage: fetch-numbers.sh <org-alias> <country> <phone-type>
#   country:    US | CA
#   phone-type: 10DLC | "Toll Free"
# Output: JSON { "phoneNumbers": [...] } on stdout.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 3 ]]; then
  echo "Usage: fetch-numbers.sh <org-alias> <country> <phone-type>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; COUNTRY="$2"; PHONE_TYPE="$3"

sf api request rest \
  "/${NM_BASE}/numbers?countryCode=${COUNTRY}&phoneNumberType=$(urlenc_spaces "$PHONE_TYPE")" \
  --target-org "$ALIAS"
