#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash analyze.sh <org-alias> [--type Voice|Email|Chat|SMS|Facebook|WhatsApp|InApp]" >&2
}

emit_blocked() {
  local issue="$1"
  jq -n \
    --argjson filter "$FILTER_JSON" \
    --arg issue "$issue" \
    '{
      skill: "service-omni-channel-inventory-analyze",
      status: "blocked",
      filter: $filter,
      summary: {total_configured: null, returned: 0, by_channel_type: {}, by_routing_type: {}},
      instances: [],
      blocking_issue: $issue
    }'
}

canonical_type() {
  local normalized
  normalized=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$normalized" in
    voice) echo "Voice" ;;
    email) echo "Email" ;;
    chat) echo "Chat" ;;
    sms) echo "SMS" ;;
    facebook) echo "Facebook" ;;
    whatsapp) echo "WhatsApp" ;;
    inapp) echo "InApp" ;;
    *) return 1 ;;
  esac
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

ORG="$1"
shift
FILTER=""
FILTER_JSON="null"

while [ $# -gt 0 ]; do
  case "$1" in
    --type)
      if [ $# -lt 2 ] || [ -z "$2" ]; then
        usage
        exit 1
      fi
      if ! FILTER=$(canonical_type "$2"); then
        FILTER_JSON="null"
        emit_blocked "Unsupported channel type '$2'. Use Voice, Email, Chat, SMS, Facebook, WhatsApp, or InApp."
        exit 1
      fi
      FILTER_JSON=$(jq -n --arg value "$FILTER" '$value')
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

if ! FORCE_COLOR=0 sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  emit_blocked "The target org is not authenticated or cannot be reached. Authenticate it with Salesforce CLI and retry."
  exit 1
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/omni-channel-inventory.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT
RAW_RESPONSE="$WORK_DIR/response.json"
ERROR_RESPONSE="$WORK_DIR/error.txt"
ENDPOINT="/services/data/v66.0/headless/invoke"
INVOKE_BODY=$(jq -cn '{
  className:"ui.omnichannel.home.controller.OmniChannelInstancesController",
  action:"getChannelInstances"
}')

if ! FORCE_COLOR=0 sf api request rest "$ENDPOINT" \
  --method POST \
  --body "$INVOKE_BODY" \
  --target-org "$ORG" \
  >"$RAW_RESPONSE" 2>"$ERROR_RESPONSE"; then
  if grep -qiE 'insufficient|permission|access denied|forbidden' "$ERROR_RESPONSE"; then
    emit_blocked "The inventory read was denied. Run it as a user with View Setup and Configuration and Customize Application."
  else
    emit_blocked "The supported Omni-Channel inventory operation failed. Verify org connectivity and feature availability, then retry."
  fi
  exit 1
fi

if ! jq -e . "$RAW_RESPONSE" >/dev/null 2>&1; then
  emit_blocked "The inventory operation returned malformed JSON. No channel state was inferred."
  exit 1
fi

INNER_STATUS=$(jq -r 'if type=="object" then .status_code // empty else empty end' "$RAW_RESPONSE")
if [ -n "$INNER_STATUS" ] && { ! [[ "$INNER_STATUS" =~ ^[0-9]+$ ]] || [ "$INNER_STATUS" -lt 200 ] || [ "$INNER_STATUS" -ge 300 ]; }; then
  INNER_ERROR=$(jq -r '.body.message // .body[0].message // .body.error // "unknown error"' "$RAW_RESPONSE")
  if printf '%s' "$INNER_ERROR" | grep -qiE 'insufficient|permission|access denied|forbidden'; then
    emit_blocked "The inventory read was denied. Run it as a user with View Setup and Configuration and Customize Application."
  else
    emit_blocked "The supported Omni-Channel inventory operation failed: $INNER_ERROR."
  fi
  exit 1
fi

EXTRACT_FILTER='def inventory:
  if type == "array" then .
  elif (.body? | type) == "array" then .body
  elif (.channelInstances? | type) == "array" then .channelInstances
  elif (.result? | type) == "array" then .result
  elif (.result?.channelInstances? | type) == "array" then .result.channelInstances
  elif (.data? | type) == "array" then .data
  elif (.items? | type) == "array" then .items
  elif (.records? | type) == "array" then .records
  elif (.value? | type) == "array" then .value
  else null
  end;
inventory'

if ! jq -e "$EXTRACT_FILTER | type == \"array\" and all(.[]; type == \"object\")" "$RAW_RESPONSE" >/dev/null 2>&1; then
  emit_blocked "The inventory operation returned an unsupported response shape. No channel state was inferred."
  exit 1
fi

jq \
  --arg filter "$FILTER" \
  "$EXTRACT_FILTER as \$source |
  def channel_type:
    (. // null) as \$value |
    if (\$value | type) != \"string\" then null
    elif (\$value | ascii_downcase) == \"voice\" then \"Voice\"
    elif (\$value | ascii_downcase) == \"email\" then \"Email\"
    elif (\$value | ascii_downcase) == \"chat\" then \"Chat\"
    elif (\$value | ascii_downcase) == \"sms\" then \"SMS\"
    elif (\$value | ascii_downcase) == \"facebook\" then \"Facebook\"
    elif (\$value | ascii_downcase) == \"whatsapp\" then \"WhatsApp\"
    elif (\$value | ascii_downcase) == \"inapp\" then \"InApp\"
    else \$value
    end;
  def routing_type:
    (. // null) as \$value |
    if (\$value | type) != \"string\" then null
    elif (\$value | ascii_downcase) == \"queue\" then \"Queue\"
    elif (\$value | ascii_downcase) == \"flow\" then \"Flow\"
    elif (\$value | ascii_downcase) == \"other\" then \"Other\"
    else \$value
    end;
  [\$source[] | {
    id: (.id // null),
    label: (.label // null),
    channelUrl: (.channelUrl // null),
    omniChannelInstanceType: (.omniChannelInstanceType | channel_type),
    routingType: (.routingType | routing_type),
    icon: (.icon // null),
    routingRequirementId: (.routingRequirementId // null),
    routingRequirementLabel: (.routingRequirementLabel // null),
    routingRequirementUrl: (.routingRequirementUrl // null),
    messages: (if (.messages | type) == \"array\" then .messages else [] end)
  }] as \$all |
  (if \$filter == \"\" then \$all else [\$all[] | select(.omniChannelInstanceType == \$filter)] end) as \$returned |
  {
    skill: \"service-omni-channel-inventory-analyze\",
    status: \"analyzed\",
    filter: (if \$filter == \"\" then null else \$filter end),
    summary: {
      total_configured: (\$all | length),
      returned: (\$returned | length),
      by_channel_type: (reduce \$returned[] as \$item ({}; .[(\$item.omniChannelInstanceType // \"Unknown\")] += 1)),
      by_routing_type: (reduce \$returned[] as \$item ({}; .[(\$item.routingType // \"Unknown\")] += 1))
    },
    instances: \$returned,
    blocking_issue: null
  }" "$RAW_RESPONSE"
