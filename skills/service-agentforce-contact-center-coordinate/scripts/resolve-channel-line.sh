#!/usr/bin/env bash
# Resolve the CommunicationChannelLine for a procured number, retrying while it propagates.
# Usage: resolve-channel-line.sh <org-alias> <phone-number>
# Output: JSON { "id": "...", "codeStatus": "..." } on success. Exit 1 if not found
# after retries; 2 on usage error; 4 if the query API returns an error envelope.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: resolve-channel-line.sh <org-alias> <phone-number>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; NUMBER="$2"
ENCODED_PHONE="${NUMBER//+/%2B}"
QUERY="SELECT+Id,CodeStatus+FROM+CommunicationChannelLine+WHERE+Code='${ENCODED_PHONE}'+LIMIT+1"

for attempt in 1 2 3; do
  DATA=$(sf api request rest \
    "/services/data/${API_VERSION}/tooling/query?q=${QUERY}" \
    --target-org "$ALIAS" 2>/dev/null || true)
  # A success query is an object; an API error is a JSON array [{errorCode,...}].
  # Stop on the error shape instead of letting jq crash on `.records` below.
  echo "$DATA" | jq -e 'type == "array"' >/dev/null 2>&1 && { echo "error: query failed for ${NUMBER}: $DATA" >&2; exit 4; }
  ID=$(echo "$DATA" | jq -r '.records[0].Id // empty')
  STATUS=$(echo "$DATA" | jq -r '.records[0].CodeStatus // empty')
  if [[ -n "$ID" ]]; then
    jq -n --arg id "$ID" --arg s "$STATUS" '{id:$id, codeStatus:$s}'
    exit 0
  fi
  [[ $attempt -lt 3 ]] && sleep 3
done

echo "error: CommunicationChannelLine not found for ${NUMBER} after 3 attempts" >&2
exit 1
