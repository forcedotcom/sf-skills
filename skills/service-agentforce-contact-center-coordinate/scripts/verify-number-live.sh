#!/usr/bin/env bash
# Verify a procured number is live, reconciling state and polling if needed.
# Usage: verify-number-live.sh <org-alias> <phone-number>
# Output: final CodeStatus value on stdout. Exit 0 if Live, 2 on usage error, 3 if
# still not Live after polling, 4 if a status query or numberStateReconcile returned
# an API error (details printed to stderr).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: verify-number-live.sh <org-alias> <phone-number>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; NUMBER="$2"

# CommunicationChannelLine is Tooling-API-only (not queryable via `sf data query`) and its
# live-status field is CodeStatus, not Status__c — query it the same way
# resolve-channel-line.sh does.
query_status() {
  local encoded_phone="${NUMBER//+/%2B}"
  local query="SELECT+CodeStatus+FROM+CommunicationChannelLine+WHERE+Code='${encoded_phone}'+LIMIT+1"
  local resp
  resp=$(sf api request rest \
    "/services/data/${API_VERSION}/tooling/query?q=${query}" \
    --target-org "$ALIAS" 2>/dev/null || true)
  # A success query is an object; an API error is a JSON array [{errorCode,...}].
  # Stop on the error shape instead of letting jq crash on `.records` below.
  echo "$resp" | jq -e 'type == "array"' >/dev/null 2>&1 && { echo "error: status query failed for ${NUMBER}: $resp" >&2; exit 4; }
  echo "$resp" | jq -r '.records[0].CodeStatus // empty'
}

STATUS=$(query_status)
if [[ "$STATUS" == "Live" ]]; then
  echo "Live"; exit 0
fi

# Reconcile, then poll every 5s up to 3 times.
# A non-2xx here (auth/API failure) must stop the workflow per the skill's
# stop-on-non-2xx rule — do NOT swallow it, or the script could create a channel
# on top of a failed reconciliation. Report the API error and exit.
RECONCILE_RESP=$(sf api request rest \
  "/${NM_BASE}/numberStateReconcile" \
  --method POST \
  --body "$(jq -n --arg p "$NUMBER" '{phoneNumber:$p}')" \
  --target-org "$ALIAS" 2>&1) || {
    echo "numberStateReconcile failed:" >&2
    echo "$RECONCILE_RESP" >&2
    exit 4
  }

for attempt in 1 2 3; do
  sleep 5
  STATUS=$(query_status)
  if [[ "$STATUS" == "Live" ]]; then
    echo "Live"; exit 0
  fi
done

echo "${STATUS:-Provisioning}"
exit 3
