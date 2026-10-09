#!/usr/bin/env bash
# upsert-and-report.sh - detect + POST (create) or PATCH (align) a QueueRoutingConfig via the Data API; an omitted routing-model preserves an existing record, idempotent (SOQL pre/post-check). Args, env overrides, output contract: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash upsert-and-report.sh <org-alias> [routing-model] [developer-name] [master-label] [capacity-weight] [routing-priority]"}' >&2
  exit 1
fi

ORG="$1"

# Optional routing-model input: 2nd positional arg, or ROUTING_MODEL_INPUT env var (coordinator path).
# Empty => preserve existing / use default-on-create (see header).
REQUESTED_ROUTING_MODEL="${2:-${ROUTING_MODEL_INPUT:-}}"
ALLOWED_ROUTING_MODELS="MostAvailable LeastActive"
if [ -n "$REQUESTED_ROUTING_MODEL" ]; then
  case " $ALLOWED_ROUTING_MODELS " in
    *" $REQUESTED_ROUTING_MODEL "*) : ;;
    *) echo "{\"error\":\"Invalid routing-model '$REQUESTED_ROUTING_MODEL'. Allowed: $ALLOWED_ROUTING_MODELS\"}" >&2; exit 1 ;;
  esac
fi

# Routing target drives the canonical naming defaults when no explicit developer-name/label is given.
ROUTING_TARGET="${QRC_ROUTING_TARGET:-Case}"
case "$ROUTING_TARGET" in
  Case)             TARGET_DEFAULT_DN="Case_Routing_Config";      TARGET_DEFAULT_LABEL="Case Routing Config" ;;
  VoiceCall)        TARGET_DEFAULT_DN="Voice_Routing_Config";     TARGET_DEFAULT_LABEL="Voice Routing Config" ;;
  Incident)         TARGET_DEFAULT_DN="Incident_Routing_Config";  TARGET_DEFAULT_LABEL="Incident Routing Config" ;;
  MessagingSession) TARGET_DEFAULT_DN="Messaging_Routing_Config"; TARGET_DEFAULT_LABEL="Messaging Routing Config" ;;
  *) echo "{\"error\":\"Invalid QRC_ROUTING_TARGET '$ROUTING_TARGET'. Allowed: Case, VoiceCall, Incident, MessagingSession\"}" >&2; exit 1 ;;
esac

# Resolve DeveloperName / MasterLabel / capacity / priority from positional args, then env, then
# create-time defaults. On an existing record, omitted values are replaced with persisted values
# after the pre-check so a targeted rerun does not reset operator-managed configuration.
DEVELOPER_NAME="${3:-${QRC_DEVELOPER_NAME:-$TARGET_DEFAULT_DN}}"
MASTER_LABEL="${4:-${QRC_MASTER_LABEL:-$TARGET_DEFAULT_LABEL}}"
CAPACITY_WEIGHT="${5:-${QRC_CAPACITY_WEIGHT:-5}}"
ROUTING_PRIORITY="${6:-${QRC_ROUTING_PRIORITY:-1}}"
MASTER_LABEL_EXPLICIT=false
{ [ -n "${4:-}" ] || [ -n "${QRC_MASTER_LABEL:-}" ]; } && MASTER_LABEL_EXPLICIT=true
ROUTING_PRIORITY_EXPLICIT=false
{ [ -n "${6:-}" ] || [ -n "${QRC_ROUTING_PRIORITY:-}" ]; } && ROUTING_PRIORITY_EXPLICIT=true
# Optional fallback/overflow assignee (QueueRoutingConfig.OverflowAssigneeId): a Username or 005 Id.
# Empty preserves an existing value (never cleared). 7th positional, or QRC_OVERFLOW_ASSIGNEE env.
OVERFLOW_ASSIGNEE_INPUT="${7:-${QRC_OVERFLOW_ASSIGNEE:-}}"

# CapacityWeight and CapacityPercentage are mutually exclusive. The steel-thread
# contract uses percentage mode (100%); callers that omit it keep weight mode.
CAPACITY_PERCENTAGE_INPUT="${QRC_CAPACITY_PERCENTAGE:-}"
WEIGHT_EXPLICIT=false
{ [ -n "${5:-}" ] || [ -n "${QRC_CAPACITY_WEIGHT:-}" ]; } && WEIGHT_EXPLICIT=true
CAPACITY_MODE="weight"
if [ -n "$CAPACITY_PERCENTAGE_INPUT" ]; then
  CAPACITY_MODE="percentage"
  if [ "$WEIGHT_EXPLICIT" = "true" ]; then
    echo '{"error":"capacity-weight and capacity-percentage are mutually exclusive; provide only one."}' >&2
    exit 1
  fi
  if ! [[ "$CAPACITY_PERCENTAGE_INPUT" =~ ^[0-9]+([.][0-9]+)?$ ]] \
     || awk "BEGIN{exit !($CAPACITY_PERCENTAGE_INPUT < 0 || $CAPACITY_PERCENTAGE_INPUT > 100)}"; then
    echo "{\"error\":\"Invalid capacity-percentage '$CAPACITY_PERCENTAGE_INPUT'. Must be a number 0..100.\"}" >&2
    exit 1
  fi
fi

# PushTimeout is opt-in. Omitted input preserves an existing value and is left
# out of a create; an explicit value is written and verified after the write.
PUSH_TIMEOUT_INPUT="${8:-${QRC_PUSH_TIMEOUT:-}}"
if [ -n "$PUSH_TIMEOUT_INPUT" ] \
   && { ! [[ "$PUSH_TIMEOUT_INPUT" =~ ^[0-9]+$ ]] || [ "$PUSH_TIMEOUT_INPUT" -gt 3600 ]; }; then
  echo "{\"error\":\"Invalid push-timeout '$PUSH_TIMEOUT_INPUT'. Must be integer seconds 0..3600.\"}" >&2
  exit 1
fi

# Validate DeveloperName grammar (interpolated into SOQL below - reject injection-shaped input).
if ! [[ "$DEVELOPER_NAME" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid developer-name '$DEVELOPER_NAME'. Must start with a letter, only letters/digits/underscore (max 80).\"}" >&2
  exit 1
fi
if ! [[ "$CAPACITY_WEIGHT" =~ ^[0-9]+$ ]] || [ "$CAPACITY_WEIGHT" -lt 1 ] || [ "$CAPACITY_WEIGHT" -gt 100 ]; then
  echo "{\"error\":\"Invalid capacity-weight '$CAPACITY_WEIGHT'. Must be integer 1..100.\"}" >&2
  exit 1
fi
if ! [[ "$ROUTING_PRIORITY" =~ ^[0-9]+$ ]] || [ "$ROUTING_PRIORITY" -lt 1 ]; then
  echo "{\"error\":\"Invalid routing-priority '$ROUTING_PRIORITY'. Must be integer >= 1.\"}" >&2
  exit 1
fi
# Validate the overflow assignee (005 Id or Username) before any sf call; it's interpolated into SOQL.
if [ -n "$OVERFLOW_ASSIGNEE_INPUT" ] \
   && ! [[ "$OVERFLOW_ASSIGNEE_INPUT" =~ ^(005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?|[A-Za-z0-9._@+-]{3,240})$ ]]; then
  echo "{\"error\":\"Invalid overflow-assignee '$OVERFLOW_ASSIGNEE_INPUT'. Provide an active User Username or a 005 User Id.\"}" >&2
  exit 1
fi

DEFAULT_ROUTING_MODEL="MostAvailable"
# Model for a new record; recomputed below to preserve an existing record's model when unspecified.
ROUTING_MODEL="${REQUESTED_ROUTING_MODEL:-$DEFAULT_ROUTING_MODEL}"
# RoutingPriority is required on QueueRoutingConfig (omitting it fails with REQUIRED_FIELD_MISSING);
# 1 = highest, the canonical demo default.
IS_ATTRIBUTE_BASED=false
API_VERSION="v66.0"

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Write guard: POSTs/PATCHes a QueueRoutingConfig, so self-enforce the production-org guard (directly invokable).
ORG_GUARD_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || {
  echo "{\"error\":\"Failed to query Organization for safe_to_write guard: $(printf '%s' "$ORG_GUARD_JSON" | head -c 300)\"}" >&2
  exit 1
}
IS_SANDBOX=$(echo "$ORG_GUARD_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_GUARD_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_GUARD_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  echo "{\"skill\":\"service-omni-queue-routing-config-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Refusing to upsert a QueueRoutingConfig on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org.\",\"safe_to_write\":false}" >&2
  exit 1
fi

# Resolve the optional overflow assignee to an active-User Id (read-only). OVERFLOW_REQUESTED
# distinguishes "set/change overflow" from "leave it alone".
OVERFLOW_REQUESTED=false
DESIRED_OVERFLOW_ID=""
if [ -n "$OVERFLOW_ASSIGNEE_INPUT" ]; then
  OVERFLOW_REQUESTED=true
  if [[ "$OVERFLOW_ASSIGNEE_INPUT" =~ ^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
    OV_JSON=$(sf data query --target-org "$ORG" --json \
      --query "SELECT Id, IsActive FROM User WHERE Id='$OVERFLOW_ASSIGNEE_INPUT'" 2>/dev/null || true)
  else
    OV_JSON=$(sf data query --target-org "$ORG" --json \
      --query "SELECT Id, IsActive FROM User WHERE Username='$OVERFLOW_ASSIGNEE_INPUT'" 2>/dev/null || true)
  fi
  if ! echo "$OV_JSON" | jq -e '.result.totalSize | numbers' >/dev/null 2>&1; then
    echo "{\"skill\":\"service-omni-queue-routing-config-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Overflow-assignee lookup was inconclusive for '$OVERFLOW_ASSIGNEE_INPUT'. Raw: $(printf '%s' "$OV_JSON" | head -c 200)\"}" >&2
    exit 1
  fi
  if [ "$(echo "$OV_JSON" | jq -r '.result.totalSize')" != "1" ]; then
    echo "{\"skill\":\"service-omni-queue-routing-config-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Overflow assignee '$OVERFLOW_ASSIGNEE_INPUT' did not resolve to exactly one User.\"}" >&2
    exit 1
  fi
  if [ "$(echo "$OV_JSON" | jq -r '.result.records[0].IsActive')" != "true" ]; then
    echo "{\"skill\":\"service-omni-queue-routing-config-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Overflow assignee '$OVERFLOW_ASSIGNEE_INPUT' is not an active User; overflow work would never be delivered.\"}" >&2
    exit 1
  fi
  DESIRED_OVERFLOW_ID=$(echo "$OV_JSON" | jq -r '.result.records[0].Id')
fi

# emit read-only plan preview JSON and exit 0 (PLAN_ONLY mode)
emit_plan() {
  local status="$1"
  local detail="$2"
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    --arg dn "$DEVELOPER_NAME" \
    '{
      skill: "service-omni-queue-routing-config-deploy",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      developer_name: $dn,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Step 1 - Pre-check: query existing record by DeveloperName
QUERY_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, DeveloperName, MasterLabel, RoutingModel, RoutingPriority, IsAttributeBased, CapacityWeight, CapacityPercentage, PushTimeout, OverflowAssigneeId FROM QueueRoutingConfig WHERE DeveloperName='$DEVELOPER_NAME'" \
  --json 2>/dev/null || true)

# Check for OmniChannelSettings-not-enabled error (would surface as INVALID_TYPE)
if echo "$QUERY_JSON" | jq -e '.name == "INVALID_TYPE"' >/dev/null 2>&1; then
  jq -n '{
    skill: "service-omni-queue-routing-config-deploy",
    status: "blocked",
    developer_name: "'"$DEVELOPER_NAME"'",
    id: null,
    manual_actions: [],
    blocking_issue: "OmniChannelSettings is not enabled on this org. Run service-omni-base-settings-configure first."
  }'
  exit 1
fi

# Only a numeric totalSize is authoritative; an inconclusive read must not be treated as absence
# (which would trigger a spurious create).
if ! echo "$QUERY_JSON" | jq -e '.result.totalSize | numbers' >/dev/null 2>&1; then
  jq -n --arg raw "$(printf '%s' "$QUERY_JSON" | head -c 400)" '{
    skill: "service-omni-queue-routing-config-deploy",
    status: "blocked",
    developer_name: "'"$DEVELOPER_NAME"'",
    id: null,
    manual_actions: [],
    blocking_issue: ("QueueRoutingConfig pre-check query was inconclusive (not a clean zero-record result). Not creating on an inconclusive read. Raw: " + $raw)
  }'
  exit 1
fi

RECORD_COUNT=$(echo "$QUERY_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")

# Step 2 - Decide action based on existing state
EXISTING_ID=""
BEFORE_CAPACITY_WEIGHT="null"
BEFORE_CAPACITY_PERCENTAGE="null"
BEFORE_PUSH_TIMEOUT="null"
BEFORE_ROUTING_MODEL="null"
BEFORE_MASTER_LABEL="null"
BEFORE_ROUTING_PRIORITY="null"
BEFORE_IS_ATTRIBUTE_BASED="false"
BEFORE_OVERFLOW_ASSIGNEE="null"
BEFORE_EXISTED=false
NEEDS_UPDATE=false

if [ "$RECORD_COUNT" -gt 0 ]; then
  BEFORE_EXISTED=true
  EXISTING_ID=$(echo "$QUERY_JSON" | jq -r '.result.records[0].Id')
  BEFORE_CAPACITY_WEIGHT=$(echo "$QUERY_JSON" | jq -r '.result.records[0].CapacityWeight // "null"')
  BEFORE_ROUTING_MODEL=$(echo "$QUERY_JSON" | jq -r '.result.records[0].RoutingModel // "null"')
  BEFORE_MASTER_LABEL=$(echo "$QUERY_JSON" | jq -r '.result.records[0].MasterLabel // "null"')
  BEFORE_ROUTING_PRIORITY=$(echo "$QUERY_JSON" | jq -r '.result.records[0].RoutingPriority // "null"')
  BEFORE_IS_ATTRIBUTE_BASED=$(echo "$QUERY_JSON" | jq -r '.result.records[0].IsAttributeBased // false')
  BEFORE_OVERFLOW_ASSIGNEE=$(echo "$QUERY_JSON" | jq -r '.result.records[0].OverflowAssigneeId // "null"')
  BEFORE_CAPACITY_PERCENTAGE=$(echo "$QUERY_JSON" | jq -r '.result.records[0].CapacityPercentage // "null"')
  BEFORE_PUSH_TIMEOUT=$(echo "$QUERY_JSON" | jq -r '.result.records[0].PushTimeout // "null"')

  # Preserve the org's routing model when none was explicitly requested (an explicit request wins).
  if [ -z "$REQUESTED_ROUTING_MODEL" ] && [ "$BEFORE_ROUTING_MODEL" != "null" ]; then
    ROUTING_MODEL="$BEFORE_ROUTING_MODEL"
  fi
  if [ "$MASTER_LABEL_EXPLICIT" = "false" ] && [ "$BEFORE_MASTER_LABEL" != "null" ]; then
    MASTER_LABEL="$BEFORE_MASTER_LABEL"
  fi
  if [ "$ROUTING_PRIORITY_EXPLICIT" = "false" ] && [ "$BEFORE_ROUTING_PRIORITY" != "null" ]; then
    ROUTING_PRIORITY="$BEFORE_ROUTING_PRIORITY"
  fi
  # This leaf does not expose an attribute-based-routing input; preserve that independent setting.
  IS_ATTRIBUTE_BASED="$BEFORE_IS_ATTRIBUTE_BASED"
  if [ -z "$CAPACITY_PERCENTAGE_INPUT" ] && [ "$WEIGHT_EXPLICIT" = "false" ]; then
    if [ "$BEFORE_CAPACITY_PERCENTAGE" != "null" ]; then
      CAPACITY_MODE="percentage"
      CAPACITY_PERCENTAGE_INPUT="$BEFORE_CAPACITY_PERCENTAGE"
    elif [ "$BEFORE_CAPACITY_WEIGHT" != "null" ]; then
      CAPACITY_MODE="weight"
      CAPACITY_WEIGHT="$BEFORE_CAPACITY_WEIGHT"
    fi
  fi

  # Compare each field against the effective target values; if any differ, mark for PATCH
  if [ "$BEFORE_ROUTING_MODEL" != "$ROUTING_MODEL" ] \
     || [ "$BEFORE_MASTER_LABEL" != "$MASTER_LABEL" ] \
     || [ "$BEFORE_ROUTING_PRIORITY" != "$ROUTING_PRIORITY" ] \
     || [ "$BEFORE_IS_ATTRIBUTE_BASED" != "$IS_ATTRIBUTE_BASED" ]; then
    NEEDS_UPDATE=true
  fi
  if [ "$CAPACITY_MODE" = "percentage" ]; then
    if [ "$BEFORE_CAPACITY_PERCENTAGE" = "null" ] \
       || awk "BEGIN{exit !($BEFORE_CAPACITY_PERCENTAGE != $CAPACITY_PERCENTAGE_INPUT)}"; then
      NEEDS_UPDATE=true
    fi
  elif [ "$BEFORE_CAPACITY_WEIGHT" != "$CAPACITY_WEIGHT" ]; then
    NEEDS_UPDATE=true
  fi
  if [ -n "$PUSH_TIMEOUT_INPUT" ] && [ "$BEFORE_PUSH_TIMEOUT" != "$PUSH_TIMEOUT_INPUT" ]; then
    NEEDS_UPDATE=true
  fi
  # Overflow drift counts only when an explicit assignee differs from the persisted one.
  if [ "$OVERFLOW_REQUESTED" = "true" ] && [ "$BEFORE_OVERFLOW_ASSIGNEE" != "$DESIRED_OVERFLOW_ID" ]; then
    NEEDS_UPDATE=true
  fi
fi

OVERFLOW_PLAN_NOTE=""
[ "$OVERFLOW_REQUESTED" = "true" ] && OVERFLOW_PLAN_NOTE=" Fallback/overflow assignee would be set to User $DESIRED_OVERFLOW_ID."
[ "$CAPACITY_MODE" = "percentage" ] && OVERFLOW_PLAN_NOTE=" Capacity model: percentage=${CAPACITY_PERCENTAGE_INPUT}%.$OVERFLOW_PLAN_NOTE"
[ -n "$PUSH_TIMEOUT_INPUT" ] && OVERFLOW_PLAN_NOTE=" PushTimeout=${PUSH_TIMEOUT_INPUT}s.$OVERFLOW_PLAN_NOTE"

# PLAN_ONLY: Steps 1-2 are read-only. Report what a --run would do and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ "$BEFORE_EXISTED" = "false" ]; then
    emit_plan "action_needed" "Would create QueueRoutingConfig '$DEVELOPER_NAME' with v1-canonical values.$OVERFLOW_PLAN_NOTE"
  elif [ "$NEEDS_UPDATE" = "true" ]; then
    emit_plan "action_needed" "QueueRoutingConfig '$DEVELOPER_NAME' exists but drifts from v1-canonical values; would PATCH.$OVERFLOW_PLAN_NOTE"
  else
    emit_plan "reused" "QueueRoutingConfig '$DEVELOPER_NAME' already matches v1-canonical values.$OVERFLOW_PLAN_NOTE"
  fi
fi

# Step 3 - POST (create) or PATCH (update) or no-op (reused)
STATUS="reused"
FINAL_ID="$EXISTING_ID"

if [ "$BEFORE_EXISTED" = "false" ]; then
  # POST new record
  STATUS="created"
  POST_BODY=$(jq -n \
    --arg dn "$DEVELOPER_NAME" \
    --arg ml "$MASTER_LABEL" \
    --arg rm "$ROUTING_MODEL" \
    --argjson rp "$ROUTING_PRIORITY" \
    --argjson iab "$IS_ATTRIBUTE_BASED" \
    '{
      DeveloperName: $dn,
      MasterLabel: $ml,
      RoutingModel: $rm,
      RoutingPriority: $rp,
      IsAttributeBased: $iab
    }')
  if [ "$CAPACITY_MODE" = "percentage" ]; then
    POST_BODY=$(echo "$POST_BODY" | jq --argjson cp "$CAPACITY_PERCENTAGE_INPUT" '. + {CapacityPercentage: $cp}')
  else
    POST_BODY=$(echo "$POST_BODY" | jq --argjson cw "$CAPACITY_WEIGHT" '. + {CapacityWeight: $cw}')
  fi
  if [ -n "$PUSH_TIMEOUT_INPUT" ]; then
    POST_BODY=$(echo "$POST_BODY" | jq --argjson pt "$PUSH_TIMEOUT_INPUT" '. + {PushTimeout: $pt}')
  fi
  # Only set OverflowAssigneeId when explicitly requested (never write a null on create).
  if [ "$OVERFLOW_REQUESTED" = "true" ]; then
    POST_BODY=$(echo "$POST_BODY" | jq --arg oa "$DESIRED_OVERFLOW_ID" '. + {OverflowAssigneeId: $oa}')
  fi

  # sf api request rest (beta) writes a warning to STDERR; redirect it so stdout is pure JSON.
  POST_STDERR="$(mktemp)"
  POST_RESULT=$(sf api request rest --target-org "$ORG" \
    "/services/data/$API_VERSION/sobjects/QueueRoutingConfig" \
    --method POST \
    --body "$POST_BODY" 2>"$POST_STDERR" || true)
  rm -f "$POST_STDERR"

  POST_SUCCESS=$(echo "$POST_RESULT" | jq -r '.success // false' 2>/dev/null || echo "false")
  if [ "$POST_SUCCESS" != "true" ]; then
    ERR_MSG=$(echo "$POST_RESULT" | jq -r '.[0].message // .message // "Unknown POST error"' 2>/dev/null)
    jq -n \
      --arg blocking "POST failed: $ERR_MSG" \
      --arg dn "$DEVELOPER_NAME" \
      '{
        skill: "service-omni-queue-routing-config-deploy",
        status: "blocked",
        developer_name: $dn,
        id: null,
        manual_actions: [],
        blocking_issue: $blocking
      }'
    exit 1
  fi
  FINAL_ID=$(echo "$POST_RESULT" | jq -r '.id')

elif [ "$NEEDS_UPDATE" = "true" ]; then
  # PATCH existing record
  STATUS="updated"
  PATCH_BODY=$(jq -n \
    --arg ml "$MASTER_LABEL" \
    --arg rm "$ROUTING_MODEL" \
    --argjson rp "$ROUTING_PRIORITY" \
    --argjson iab "$IS_ATTRIBUTE_BASED" \
    '{
      MasterLabel: $ml,
      RoutingModel: $rm,
      RoutingPriority: $rp,
      IsAttributeBased: $iab
    }')
  if [ "$CAPACITY_MODE" = "percentage" ]; then
    PATCH_BODY=$(echo "$PATCH_BODY" | jq --argjson cp "$CAPACITY_PERCENTAGE_INPUT" '. + {CapacityPercentage: $cp}')
    [ "${BEFORE_CAPACITY_WEIGHT:-null}" = "null" ] || PATCH_BODY=$(echo "$PATCH_BODY" | jq '. + {CapacityWeight: null}')
  else
    PATCH_BODY=$(echo "$PATCH_BODY" | jq --argjson cw "$CAPACITY_WEIGHT" '. + {CapacityWeight: $cw}')
    [ "${BEFORE_CAPACITY_PERCENTAGE:-null}" = "null" ] || PATCH_BODY=$(echo "$PATCH_BODY" | jq '. + {CapacityPercentage: null}')
  fi
  if [ -n "$PUSH_TIMEOUT_INPUT" ]; then
    PATCH_BODY=$(echo "$PATCH_BODY" | jq --argjson pt "$PUSH_TIMEOUT_INPUT" '. + {PushTimeout: $pt}')
  fi
  # Only touch OverflowAssigneeId when explicitly requested - an omitted input leaves it as-is.
  if [ "$OVERFLOW_REQUESTED" = "true" ]; then
    PATCH_BODY=$(echo "$PATCH_BODY" | jq --arg oa "$DESIRED_OVERFLOW_ID" '. + {OverflowAssigneeId: $oa}')
  fi

  # PATCH returns 204 (empty) on success; detect success by the absence of an error field.
  PATCH_STDERR="$(mktemp)"
  PATCH_RESULT=$(sf api request rest --target-org "$ORG" \
    "/services/data/$API_VERSION/sobjects/QueueRoutingConfig/$EXISTING_ID" \
    --method PATCH \
    --body "$PATCH_BODY" 2>"$PATCH_STDERR" || true)
  rm -f "$PATCH_STDERR"

  # PATCH success = empty result OR result contains success:true. Error = has errorCode or message with error.
  if echo "$PATCH_RESULT" | jq -e 'if type == "array" then .[0].errorCode else .errorCode end' >/dev/null 2>&1; then
    ERR_MSG=$(echo "$PATCH_RESULT" | jq -r 'if type == "array" then .[0].message else .message end' 2>/dev/null)
    jq -n \
      --arg blocking "PATCH failed: $ERR_MSG" \
      --arg dn "$DEVELOPER_NAME" \
      --arg id "$EXISTING_ID" \
      '{
        skill: "service-omni-queue-routing-config-deploy",
        status: "blocked",
        developer_name: $dn,
        id: $id,
        manual_actions: [],
        blocking_issue: $blocking
      }'
    exit 1
  fi
fi

# Step 4 - Post-check: re-query to confirm final state
FINAL_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, DeveloperName, MasterLabel, RoutingModel, RoutingPriority, IsAttributeBased, CapacityWeight, CapacityPercentage, PushTimeout, OverflowAssigneeId FROM QueueRoutingConfig WHERE Id='$FINAL_ID'" \
  --json 2>/dev/null)

if [ "$(echo "$FINAL_JSON" | jq -r '.result.totalSize')" != "1" ]; then
  jq -n \
    --arg blocking "Post-check re-query returned unexpected count. Expected 1, got $(echo "$FINAL_JSON" | jq -r '.result.totalSize')." \
    --arg dn "$DEVELOPER_NAME" \
    --arg id "$FINAL_ID" \
    '{
      skill: "service-omni-queue-routing-config-deploy",
      status: "blocked",
      developer_name: $dn,
      id: $id,
      manual_actions: [],
      blocking_issue: $blocking
    }'
  exit 1
fi

# Read the persisted values back (reporting input constants would mask a silently coerced field).
ACTUAL_DN=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].DeveloperName // "null"')
ACTUAL_ML=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].MasterLabel // "null"')
ACTUAL_RM=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].RoutingModel // "null"')
ACTUAL_CW=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].CapacityWeight // "null"')
ACTUAL_CP=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].CapacityPercentage // "null"')
ACTUAL_RP=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].RoutingPriority // "null"')
# IsAttributeBased is boolean; read it explicitly since jq's // would map a genuine false to "null".
ACTUAL_IAB=$(echo "$FINAL_JSON" | jq -r '.result.records[0].IsAttributeBased | if . == null then "null" else tostring end')
ACTUAL_PT=$(echo "$FINAL_JSON"  | jq -r '.result.records[0].PushTimeout')
ACTUAL_OAI=$(echo "$FINAL_JSON" | jq -r '.result.records[0].OverflowAssigneeId')

# For a create/update, the persisted values must equal what we wrote; a mismatch blocks.
if [ "$STATUS" = "created" ] || [ "$STATUS" = "updated" ]; then
  MISMATCHES=""
  [ "$ACTUAL_ML" = "$MASTER_LABEL" ]      || MISMATCHES="$MISMATCHES MasterLabel(got='$ACTUAL_ML' want='$MASTER_LABEL')"
  [ "$ACTUAL_RM" = "$ROUTING_MODEL" ]     || MISMATCHES="$MISMATCHES RoutingModel(got='$ACTUAL_RM' want='$ROUTING_MODEL')"
  if [ "$CAPACITY_MODE" = "percentage" ]; then
    if [ "$ACTUAL_CP" = "null" ] \
       || awk "BEGIN{exit !($ACTUAL_CP != $CAPACITY_PERCENTAGE_INPUT)}"; then
      MISMATCHES="$MISMATCHES CapacityPercentage(got='$ACTUAL_CP' want='$CAPACITY_PERCENTAGE_INPUT')"
    fi
  else
    [ "$ACTUAL_CW" = "$CAPACITY_WEIGHT" ] || MISMATCHES="$MISMATCHES CapacityWeight(got='$ACTUAL_CW' want='$CAPACITY_WEIGHT')"
  fi
  if [ -n "$PUSH_TIMEOUT_INPUT" ]; then
    [ "$ACTUAL_PT" = "$PUSH_TIMEOUT_INPUT" ] || MISMATCHES="$MISMATCHES PushTimeout(got='$ACTUAL_PT' want='$PUSH_TIMEOUT_INPUT')"
  fi
  [ "$ACTUAL_RP" = "$ROUTING_PRIORITY" ]  || MISMATCHES="$MISMATCHES RoutingPriority(got='$ACTUAL_RP' want='$ROUTING_PRIORITY')"
  [ "$ACTUAL_IAB" = "$IS_ATTRIBUTE_BASED" ] || MISMATCHES="$MISMATCHES IsAttributeBased(got='$ACTUAL_IAB' want='$IS_ATTRIBUTE_BASED')"
  if [ "$OVERFLOW_REQUESTED" = "true" ]; then
    [ "$ACTUAL_OAI" = "$DESIRED_OVERFLOW_ID" ] || MISMATCHES="$MISMATCHES OverflowAssigneeId(got='$ACTUAL_OAI' want='$DESIRED_OVERFLOW_ID')"
  fi
  if [ -n "$MISMATCHES" ]; then
    jq -n \
      --arg dn "$DEVELOPER_NAME" \
      --arg id "$FINAL_ID" \
      --arg blocking "Post-write verification failed - persisted QueueRoutingConfig does not match intended values:$MISMATCHES" \
      '{
        skill: "service-omni-queue-routing-config-deploy",
        status: "blocked",
        developer_name: $dn,
        id: $id,
        manual_actions: [],
        blocking_issue: $blocking
      }'
    exit 1
  fi
fi

# Step 5 - Emit report JSON (actual persisted values, read back from the org)
jq -n \
  --arg status "$STATUS" \
  --arg id "$FINAL_ID" \
  --arg actual_dn "$ACTUAL_DN" \
  --arg actual_ml "$ACTUAL_ML" \
  --arg actual_rm "$ACTUAL_RM" \
  --arg actual_cw "$ACTUAL_CW" \
  --arg actual_cp "$ACTUAL_CP" \
  --arg capacity_mode "$CAPACITY_MODE" \
  --arg actual_rp "$ACTUAL_RP" \
  --arg actual_iab "$ACTUAL_IAB" \
  --arg actual_pt "$ACTUAL_PT" \
  --arg actual_oai "$ACTUAL_OAI" \
  --argjson before_existed "$BEFORE_EXISTED" \
  --arg before_cw "$BEFORE_CAPACITY_WEIGHT" \
  --arg before_rm "$BEFORE_ROUTING_MODEL" \
  --arg routing_target "$ROUTING_TARGET" \
  --argjson overflow_requested "$OVERFLOW_REQUESTED" \
  '{
    skill: "service-omni-queue-routing-config-deploy",
    status: $status,
    routing_target: $routing_target,
    overflow_assignee_requested: $overflow_requested,
    developer_name: $actual_dn,
    id: $id,
    master_label: $actual_ml,
    routing_model: $actual_rm,
    capacity_mode: $capacity_mode,
    capacity_weight: (if $actual_cw == "null" then null else ($actual_cw | tonumber?) end),
    capacity_percentage: (if $actual_cp == "null" then null else ($actual_cp | tonumber?) end),
    routing_priority: (if $actual_rp == "null" then null else ($actual_rp | tonumber?) end),
    is_attribute_based: (if $actual_iab == "true" then true elif $actual_iab == "false" then false else null end),
    push_timeout: (if $actual_pt == "null" then null else ($actual_pt | tonumber?) end),
    overflow_assignee_id: (if $actual_oai == "null" then null else $actual_oai end),
    values_source: "requeried",
    before: (
      if $before_existed then
        {
          existed: true,
          capacity_weight: (if $before_cw == "null" then null else ($before_cw | tonumber?) end),
          routing_model: (if $before_rm == "null" then null else $before_rm end)
        }
      else
        {existed: false, capacity_weight: null, routing_model: null}
      end
    ),
    manual_actions: [],
    blocking_issue: null
  }'
