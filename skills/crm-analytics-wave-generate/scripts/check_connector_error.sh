#!/usr/bin/env bash
# GET /wave/dataConnectors/{id}, parse errorCategory, exit 0 if safe to retry (System), 1 if not (User/Limit/unknown).
# Usage: bash scripts/check_connector_error.sh <alias> <connectorId>
# Exit codes: 0 = System error (safe to retry) | 1 = User/Limit/unknown (do not retry, fix config first)

set -euo pipefail

ALIAS="${1:?Usage: check_connector_error.sh <alias> <connectorId>}"
CONNECTOR_ID="${2:?Usage: check_connector_error.sh <alias> <connectorId>}"

ORG_JSON=$(sf org display -o "$ALIAS" --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$ORG_JSON" | grep -o '"accessToken": *"[^"]*"' | cut -d'"' -f4)
INSTANCE_URL=$(echo "$ORG_JSON" | grep -o '"instanceUrl": *"[^"]*"' | cut -d'"' -f4)

if [[ -z "$ACCESS_TOKEN" || -z "$INSTANCE_URL" ]]; then
  echo '{"error":"Could not retrieve org credentials. Run: sf org display -o <alias>"}' >&2
  exit 1
fi

RESPONSE=$(curl -s -f \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "${INSTANCE_URL}/services/data/v59.0/wave/dataConnectors/${CONNECTOR_ID}")

ERROR_CATEGORY=$(echo "$RESPONSE" | grep -o '"errorCategory":"[^"]*"' | cut -d'"' -f4)
ERROR_MESSAGE=$(echo "$RESPONSE" | grep -o '"errorMessage":"[^"]*"' | cut -d'"' -f4)
STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

echo "{\"connectorId\":\"$CONNECTOR_ID\",\"status\":\"$STATUS\",\"errorCategory\":\"$ERROR_CATEGORY\",\"errorMessage\":\"$ERROR_MESSAGE\"}"

case "$ERROR_CATEGORY" in
  System)
    echo "errorCategory=System: platform-side issue — safe to retry." >&2
    exit 0
    ;;
  User)
    echo "errorCategory=User: config or credential issue — retry will not fix this. Check connector settings." >&2
    exit 1
    ;;
  Limit)
    echo "errorCategory=Limit: org quota exceeded — retry will not fix this. Check org limits." >&2
    exit 1
    ;;
  *)
    # Unknown category — check for generic "contact support" message
    if echo "$ERROR_MESSAGE" | grep -qi "contact support"; then
      echo "errorCategory unknown but message contains 'contact support' — treating as System, safe to retry once." >&2
      exit 0
    fi
    echo "errorCategory='$ERROR_CATEGORY' unrecognised — treating as non-retryable." >&2
    exit 1
    ;;
esac
