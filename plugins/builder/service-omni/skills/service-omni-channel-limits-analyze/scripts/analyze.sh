#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash analyze.sh <org-alias> [--routing-model enhanced|legacy] [--max-psrs <1-1000000>]" >&2
}

ROUTING_MODEL="enhanced"
MAX_PSRS=""
MAX_SOURCE="reference_default"
ORG=""

emit_blocked() {
  local issue="$1"
  jq -n \
    --arg model "$ROUTING_MODEL" \
    --arg issue "$issue" \
    '{
      skill: "service-omni-channel-limits-analyze",
      status: "blocked",
      routing_model: $model,
      metrics: null,
      caveats: [],
      blocking_issue: $issue
    }'
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

ORG="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --routing-model)
      if [ $# -lt 2 ]; then
        usage
        exit 1
      fi
      ROUTING_MODEL=$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')
      if [ "$ROUTING_MODEL" != "enhanced" ] && [ "$ROUTING_MODEL" != "legacy" ]; then
        emit_blocked "Unsupported routing model '$2'. Use enhanced or legacy."
        exit 1
      fi
      shift 2
      ;;
    --max-psrs)
      if [ $# -lt 2 ] || ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -lt 1 ] || [ "$2" -gt 1000000 ]; then
        emit_blocked "max-psrs must be an integer from 1 through 1000000."
        exit 1
      fi
      MAX_PSRS="$2"
      MAX_SOURCE="admin_supplied"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [ -z "$MAX_PSRS" ]; then
  if [ "$ROUTING_MODEL" = "enhanced" ]; then
    MAX_PSRS="300000"
  else
    MAX_PSRS="200000"
  fi
fi

if ! FORCE_COLOR=0 sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  emit_blocked "The target org is not authenticated or cannot be reached. Authenticate it with Salesforce CLI and retry."
  exit 1
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/omni-channel-limits.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT
RAW_OUTPUT="$WORK_DIR/query-output.txt"
QUERY_JSON="$WORK_DIR/query.json"
ERROR_OUTPUT="$WORK_DIR/query-error.txt"
QUERY="SELECT COUNT() FROM PendingServiceRouting"

if ! FORCE_COLOR=0 sf data query \
  --query "$QUERY" \
  --target-org "$ORG" \
  --json >"$RAW_OUTPUT" 2>"$ERROR_OUTPUT"; then
  sed -n '/^[[:space:]]*{/,$p' "$RAW_OUTPUT" >"$QUERY_JSON"
  QUERY_ERROR=$(jq -r '.name // .message // empty' "$QUERY_JSON" 2>/dev/null || true)
  if printf '%s' "$QUERY_ERROR" | grep -qiE 'INVALID_TYPE|not supported'; then
    emit_blocked "PendingServiceRouting is unavailable. Confirm Omni-Channel is enabled and the running user can access the object; usage was not treated as zero."
  elif printf '%s' "$QUERY_ERROR" | grep -qiE 'insufficient|permission|access denied|forbidden'; then
    emit_blocked "The PendingServiceRouting query was denied. Run the analysis as a user with permission to view Omni routing records."
  else
    emit_blocked "The PendingServiceRouting query failed. Verify org connectivity, feature availability, and permissions, then retry."
  fi
  exit 1
fi

sed -n '/^[[:space:]]*{/,$p' "$RAW_OUTPUT" >"$QUERY_JSON"
if ! jq -e '.status == 0 and (.result | type == "object")' "$QUERY_JSON" >/dev/null 2>&1; then
  emit_blocked "The PendingServiceRouting query returned an unsupported response. No usage was inferred."
  exit 1
fi

CURRENT_PSRS=$(jq -r '.result.records[0].expr0 // .result.totalSize // empty' "$QUERY_JSON")
if ! [[ "$CURRENT_PSRS" =~ ^[0-9]+$ ]]; then
  emit_blocked "The PendingServiceRouting query did not return a valid count. No usage was inferred."
  exit 1
fi

USAGE_PERCENT=$(jq -n \
  --argjson current "$CURRENT_PSRS" \
  --argjson maximum "$MAX_PSRS" \
  '($current * 10000 / $maximum | round) / 100')

jq -n \
  --arg model "$ROUTING_MODEL" \
  --argjson current "$CURRENT_PSRS" \
  --argjson maximum "$MAX_PSRS" \
  --argjson usage "$USAGE_PERCENT" \
  --arg max_source "$MAX_SOURCE" \
  '{
    skill: "service-omni-channel-limits-analyze",
    status: "analyzed",
    routing_model: $model,
    metrics: {
      current_pending_service_routings: {
        used: $current,
        limit: $maximum,
        usage_percent: $usage,
        used_source: "live_soql",
        limit_source: $max_source,
        limit_verified_by_api: false,
        usage_is_approximate: true
      },
      pending_service_routing_rate_per_hour: {
        used: null,
        limit: 45000,
        usage_percent: null,
        used_source: "not_available_via_supported_api",
        limit_source: "reference_default",
        limit_verified_by_api: false
      }
    },
    caveats: [
      "The PSR count is a point-in-time live query.",
      "The PSR maximum is not API-verified; it is an administrator-supplied value or a routing-model reference default.",
      "Live hourly usage is not exposed by a supported customer-org API and was not inferred.",
      "No org configuration was changed."
    ],
    blocking_issue: null
  }'
