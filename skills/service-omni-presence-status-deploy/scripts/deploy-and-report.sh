#!/usr/bin/env bash
# deploy-and-report.sh - deploy the sObject-specific "Available_<X>" presence status bound to the resolved ServiceChannel and reuse-or-deploy a universal "Busy" status (Busy is UI-only in the Metadata API). Args, channel binding, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash deploy-and-report.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall]"}' >&2
  exit 1
fi

ORG="$1"
SOBJECT_TYPE="${2:-Case}"
CHANNEL_DN_ARG="${3:-}"

case "$SOBJECT_TYPE" in
  Case)
    AVAILABLE_STATUS_DN="Available_Case"
    AVAILABLE_STATUS_LABEL="Available for Cases"
    DEFAULT_CHANNEL_DN="Cases"
    ;;
  Incident)
    AVAILABLE_STATUS_DN="Available_Incident"
    AVAILABLE_STATUS_LABEL="Available for Incidents"
    DEFAULT_CHANNEL_DN="Incidents"
    ;;
  MessagingSession)
    AVAILABLE_STATUS_DN="Available_Messaging"
    AVAILABLE_STATUS_LABEL="Available for Messaging"
    DEFAULT_CHANNEL_DN="sfdc_livemessage"
    ;;
  VoiceCall)
    AVAILABLE_STATUS_DN="Available_Voice"
    AVAILABLE_STATUS_LABEL="Available for Voice"
    DEFAULT_CHANNEL_DN="sfdc_phone"
    ;;
  *)
    echo "{\"error\":\"Unsupported sobject_type: '$SOBJECT_TYPE'. Supported: Case, Incident, MessagingSession, VoiceCall\"}" >&2
    exit 2
    ;;
esac

# Resolve the channel to bind: prefer the coordinator-supplied discovered channel, validate it,
# else fall back to the canonical default. Never silently ignore a passed-in channel name.
if [ -n "$CHANNEL_DN_ARG" ]; then
  if ! [[ "$CHANNEL_DN_ARG" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    echo "{\"error\":\"Invalid channel_developer_name '$CHANNEL_DN_ARG'. A Salesforce DeveloperName must start with a letter (allowed: A-Z a-z, then A-Z a-z 0-9 _; max 80).\"}" >&2
    exit 1
  fi
  BOUND_CHANNEL_DN="$CHANNEL_DN_ARG"
  CHANNEL_SOURCE="discovered"
else
  BOUND_CHANNEL_DN="$DEFAULT_CHANNEL_DN"
  CHANNEL_SOURCE="default"
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Write guard: deploys ServicePresenceStatus metadata, so self-enforce the production-org guard (directly invokable).
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
  echo "{\"skill\":\"service-omni-presence-status-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Refusing to deploy presence statuses to a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org.\",\"safe_to_write\":false}" >&2
  exit 1
fi

# emit read-only plan preview JSON and exit 0 (PLAN_ONLY mode)
emit_plan() {
  local status="$1"
  local detail="$2"
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    --arg sobject "$SOBJECT_TYPE" \
    --arg chan "$BOUND_CHANNEL_DN" \
    '{
      skill: "service-omni-presence-status-deploy",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      sobject_type: $sobject,
      channel_developer_name: $chan,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# PLAN_ONLY: detect the two statuses via SOQL (read-only); the channel binding is verified only in a
# real run (its junction is not queryable), so plan uses existence as the preview signal.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  PS_EXIST_JSON=$(sf data query --target-org "$ORG" --json \
    --query "SELECT DeveloperName FROM ServicePresenceStatus WHERE DeveloperName IN ('$AVAILABLE_STATUS_DN','Busy')" 2>/dev/null || echo '{}')
  AVAIL_PRESENT=$(echo "$PS_EXIST_JSON" | jq -r --arg dn "$AVAILABLE_STATUS_DN" '[.result.records[].DeveloperName] | index($dn) != null' 2>/dev/null || echo false)
  BUSY_PRESENT=$(echo "$PS_EXIST_JSON" | jq -r '[.result.records[].DeveloperName] | index("Busy") != null' 2>/dev/null || echo false)
  if [ "$AVAIL_PRESENT" = "true" ] && [ "$BUSY_PRESENT" = "true" ]; then
    emit_plan "reused" "Presence status '$AVAILABLE_STATUS_DN' and a 'Busy' status already exist."
  elif [ "$AVAIL_PRESENT" = "true" ]; then
    emit_plan "action_needed" "'$AVAILABLE_STATUS_DN' exists; would deploy a 'Busy' status (none found)."
  elif [ "$BUSY_PRESENT" = "true" ]; then
    emit_plan "action_needed" "A 'Busy' status exists (reuse); would deploy '$AVAILABLE_STATUS_DN' (→ channel '$BOUND_CHANNEL_DN')."
  else
    emit_plan "action_needed" "Would deploy presence status '$AVAILABLE_STATUS_DN' (→ channel '$BOUND_CHANNEL_DN') and a 'Busy' status."
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

if [ ! -f "$ASSETS_DIR/sfdx-project.json" ]; then
  echo "{\"error\":\"Assets DX project not found at $ASSETS_DIR\"}" >&2
  exit 1
fi

STATUS_XML="$ASSETS_DIR/force-app/main/default/servicePresenceStatuses/${AVAILABLE_STATUS_DN}.servicePresenceStatus-meta.xml"
if [ ! -f "$STATUS_XML" ]; then
  echo "{\"error\":\"Asset not found for sobject_type=$SOBJECT_TYPE at $STATUS_XML\"}" >&2
  exit 1
fi

# Materialize into a temp DX project so we can rewrite Available_<X>'s <channel> to the resolved
# channel. Reuse an existing "Busy" status if present (never redeploy it); deploy the bundled Busy only when absent.
BUSY_EXIST_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT DeveloperName FROM ServicePresenceStatus WHERE DeveloperName='Busy'" 2>/dev/null || echo '{}')
BUSY_EXISTS=$(echo "$BUSY_EXIST_JSON" | jq -r '(.result.totalSize // 0) > 0' 2>/dev/null || echo false)

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
DEST_DIR="$WORK/force-app/main/default/servicePresenceStatuses"
mkdir -p "$DEST_DIR"
cp "$ASSETS_DIR/sfdx-project.json" "$WORK/sfdx-project.json"

# Available_<X>: rewrite the single <channel>...</channel> to the resolved channel DN.
# The XML has exactly one <channel> element (see asset); a targeted sed keeps the rest intact.
sed -E "s|<channel>[^<]*</channel>|<channel>${BOUND_CHANNEL_DN}</channel>|" \
  "$STATUS_XML" > "$DEST_DIR/${AVAILABLE_STATUS_DN}.servicePresenceStatus-meta.xml"

# Build the --metadata deploy list. Always deploy the Available_<X> status; add "Busy" only when it
# does not already exist on the org.
DEPLOY_METADATA_ARGS=(--metadata "ServicePresenceStatus:${AVAILABLE_STATUS_DN}")
if [ "$BUSY_EXISTS" != "true" ]; then
  cp "$ASSETS_DIR/force-app/main/default/servicePresenceStatuses/Busy.servicePresenceStatus-meta.xml" \
    "$DEST_DIR/Busy.servicePresenceStatus-meta.xml"
  DEPLOY_METADATA_ARGS+=(--metadata "ServicePresenceStatus:Busy")
fi

# One atomic deploy, explicit --metadata (no sibling piggyback). Deploy --async + poll so a
# synchronous ClientTimeoutError under org load can't produce a false red; budget ~20 min (80 * 15s).
START_JSON=$(cd "$WORK" && sf project deploy start --target-org "$ORG" \
  "${DEPLOY_METADATA_ARGS[@]}" \
  --async --json 2>/dev/null || true)

DEPLOY_ID=$(echo "$START_JSON" | jq -r '.result.id // ""' 2>/dev/null)
DEPLOY_JSON="$START_JSON"

if [ -n "$DEPLOY_ID" ] && [ "$DEPLOY_ID" != "null" ]; then
  # Poll to a terminal state (Succeeded/Failed/SucceededPartial/Canceled); "in progress" is not blocked.
  POLL_STATUS=""
  for _ in $(seq 1 80); do
    REPORT_JSON=$(cd "$WORK" && sf project deploy report --job-id "$DEPLOY_ID" --target-org "$ORG" --json 2>/dev/null || true)
    CUR_STATUS=$(echo "$REPORT_JSON" | jq -r '.result.status // ""' 2>/dev/null)
    case "$CUR_STATUS" in
      Succeeded|Failed|SucceededPartial|Canceled)
        DEPLOY_JSON="$REPORT_JSON"; POLL_STATUS="$CUR_STATUS"; break ;;
    esac
    sleep 15
  done

  if [ -z "$POLL_STATUS" ]; then
    # No terminal state within budget - fail closed (don't report success on an unobserved deploy).
    jq -n \
      --arg deploy_id "$DEPLOY_ID" \
      --arg sobject "$SOBJECT_TYPE" \
      --arg avail_dn "$AVAILABLE_STATUS_DN" \
      --arg avail_lbl "$AVAILABLE_STATUS_LABEL" \
      --arg chan "$BOUND_CHANNEL_DN" \
      '{
        skill: "service-omni-presence-status-deploy",
        status: "blocked",
        sobject_type: $sobject,
        presence_statuses: [
          {developer_name: $avail_dn,      label: $avail_lbl,       channels: [$chan], state: "deploy_pending"},
          {developer_name: "Busy", label: "Busy", channels: [],      state: "deploy_pending"}
        ],
        deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
        manual_actions: [("Inspect deploy: sf project deploy report --job-id " + $deploy_id)],
        blocking_issue: ("Presence-status deploy job " + $deploy_id + " did not reach a terminal state within the ~20 min poll budget (org may still be processing under load). Not reporting success.")
      }'
    exit 1
  fi
fi

# Re-derive from the report JSON (or START_JSON if the async start had no job id → failure branch below).
DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // null'  2>/dev/null)

translate_deploy_error() {
  local raw="$1"
  case "$raw" in
    *INVALID_TYPE*"ServicePresenceStatus"*|*INVALID_TYPE*"OmniChannel"*)
      echo "OmniChannelSettings is not enabled on this org. Run service-omni-base-settings-configure first."
      ;;
    *INVALID_FIELD_VALUE*"$BOUND_CHANNEL_DN"*|*"Value '$BOUND_CHANNEL_DN' is not valid"*)
      echo "ServiceChannel '$BOUND_CHANNEL_DN' does not exist on this org. Run service-omni-service-channel-configure with sobject_type=$SOBJECT_TYPE first."
      ;;
    *"Element {http://soap.sforce.com/2006/04/metadata}statusType"*)
      echo "Deploy XML contains a <statusType> element that is not part of the ServicePresenceStatus schema. Remove <statusType> - online/busy is inferred from <channels> presence."
      ;;
    *)
      echo "$raw"
      ;;
  esac
}

if [ "$DEPLOY_SUCCESS" != "true" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  if [ -z "$FAILURES" ] || [ "$FAILURES" = "null" ]; then
    FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  fi
  FRIENDLY=$(translate_deploy_error "$FAILURES")

  MANUAL_ACTIONS='[]'
  case "$FRIENDLY" in
    *"service-omni-base-settings-configure"*)
      MANUAL_ACTIONS='[{"id":"MISSING_PREREQ","title":"Run prerequisite skill","target_skill":"service-omni-base-settings-configure"}]'
      ;;
    *"service-omni-service-channel-configure"*)
      MANUAL_ACTIONS='[{"id":"MISSING_PREREQ","title":"Run prerequisite skill","target_skill":"service-omni-service-channel-configure","sobject_type":"'"$SOBJECT_TYPE"'"}]'
      ;;
  esac

  jq -n \
    --arg deploy_id "$DEPLOY_ID" \
    --arg blocking "$FRIENDLY" \
    --arg raw "$FAILURES" \
    --arg sobject "$SOBJECT_TYPE" \
    --arg avail_dn "$AVAILABLE_STATUS_DN" \
    --arg avail_lbl "$AVAILABLE_STATUS_LABEL" \
    --arg chan "$BOUND_CHANNEL_DN" \
    --argjson ma "$MANUAL_ACTIONS" \
    '{
      skill: "service-omni-presence-status-deploy",
      status: "blocked",
      sobject_type: $sobject,
      presence_statuses: [
        {developer_name: $avail_dn,      label: $avail_lbl,       channels: [$chan], state: "not_deployed"},
        {developer_name: "Busy", label: "Busy", channels: [],      state: "not_deployed"}
      ],
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      manual_actions: $ma,
      blocking_issue: $blocking,
      raw_error: $raw
    }'
  exit 1
fi

get_state() {
  local fullname="$1"
  echo "$DEPLOY_JSON" | jq -r --arg fn "$fullname" \
    '.result.files[] | select(.fullName == $fn and .type == "ServicePresenceStatus") | .state' 2>/dev/null | head -1
}

STATE_AVAILABLE=$(get_state "$AVAILABLE_STATUS_DN")
STATE_AVAILABLE="${STATE_AVAILABLE:-unknown}"

# Busy: if it already existed we reused it (never deployed) → treat as Unchanged. Otherwise read
# its deploy state from the response.
if [ "$BUSY_EXISTS" = "true" ]; then
  STATE_BUSY="Unchanged"
else
  STATE_BUSY=$(get_state "Busy")
  STATE_BUSY="${STATE_BUSY:-unknown}"
fi

# Each component's state must be a known idempotency signal (Created/Changed/Unchanged); anything
# else means we can't prove it deployed - block rather than report success.
for pair in "AVAILABLE:$STATE_AVAILABLE" "BUSY:$STATE_BUSY"; do
  comp="${pair%%:*}"; st="${pair#*:}"
  case "$st" in
    Created|Changed|Unchanged) ;;
    *)
      jq -n \
        --arg sobject "$SOBJECT_TYPE" \
        --arg avail_dn "$AVAILABLE_STATUS_DN" \
        --arg chan "$BOUND_CHANNEL_DN" \
        --arg deploy_id "$DEPLOY_ID" \
        --arg comp "$comp" \
        --arg st "$st" \
        '{
          skill: "service-omni-presence-status-deploy",
          status: "blocked",
          sobject_type: $sobject,
          presence_statuses: [{developer_name: $avail_dn, channels: [$chan], state: $st}],
          deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
          manual_actions: [],
          blocking_issue: ("Deploy reported success overall but component " + $comp + " has an unrecognized/absent state \"" + $st + "\" (expected Created, Changed, or Unchanged). Not reporting success.")
        }'
      exit 1
      ;;
  esac
done

# Post-verify the channel binding by RETRIEVING the deployed metadata and reading its <channel>
# back - the ServicePresenceStatusChannel junction is not queryable (INVALID_TYPE). Bounded retry
# with backoff so transient empty retrieves don't flip to blocked; XML present is authoritative,
# exhausted budget leaves "unverified" (fail closed below).
BINDING_VERIFIED="unverified"
VERIFY_ATTEMPTS=5
VERIFY_SLEEP=10
for verify_attempt in $(seq 1 "$VERIFY_ATTEMPTS"); do
  VERIFY_WORK="$(mktemp -d)"
  cp "$ASSETS_DIR/sfdx-project.json" "$VERIFY_WORK/sfdx-project.json"
  mkdir -p "$VERIFY_WORK/force-app/main/default"
  # Retrieve for its side effect (writes XML into VERIFY_WORK); verified by inspecting the file below.
  ( cd "$VERIFY_WORK" && sf project retrieve start --target-org "$ORG" \
    --metadata "ServicePresenceStatus:${AVAILABLE_STATUS_DN}" --json >/dev/null 2>&1 || true )
  RETRIEVED_XML=$(find "$VERIFY_WORK" -name "${AVAILABLE_STATUS_DN}.servicePresenceStatus-meta.xml" 2>/dev/null | head -1)
  if [ -n "$RETRIEVED_XML" ] && [ -f "$RETRIEVED_XML" ]; then
    # Extract every <channel>...</channel> value and test for an exact match to the resolved channel.
    if grep -oE "<channel>[^<]*</channel>" "$RETRIEVED_XML" 2>/dev/null \
         | sed -E 's|<channel>([^<]*)</channel>|\1|' \
         | grep -qxF "$BOUND_CHANNEL_DN"; then
      BINDING_VERIFIED="true"
    else
      BINDING_VERIFIED="false"
    fi
    rm -rf "$VERIFY_WORK"
    break
  fi
  # No XML (likely transient latency) - back off and retry until the budget is exhausted.
  rm -rf "$VERIFY_WORK"
  if [ "$verify_attempt" -lt "$VERIFY_ATTEMPTS" ]; then
    sleep "$VERIFY_SLEEP"
    VERIFY_SLEEP=$((VERIFY_SLEEP + 10))
  fi
done

# Block on both a confirmed-missing binding ("false") and an inconclusive read ("unverified"); a
# report to STDOUT so the coordinator captures it rather than seeing empty_output.
if [ "$BINDING_VERIFIED" != "true" ]; then
  if [ "$BINDING_VERIFIED" = "false" ]; then
    BIND_MSG="Deploy reported success but $AVAILABLE_STATUS_DN is not bound to ServiceChannel $BOUND_CHANNEL_DN on post-verify (the retrieved presence-status metadata does not list this channel). The channel DeveloperName may not exist on this org."
    BIND_STATE="deployed_but_unbound"
  else
    BIND_MSG="Deploy reported success but the $AVAILABLE_STATUS_DN <-> $BOUND_CHANNEL_DN binding could not be verified (the metadata retrieve returned no presence-status XML - inconclusive). Not reporting success on an unverified binding."
    BIND_STATE="deployed_binding_unverified"
  fi
  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg avail_dn "$AVAILABLE_STATUS_DN" \
    --arg chan "$BOUND_CHANNEL_DN" \
    --arg deploy_id "$DEPLOY_ID" \
    --arg bind_state "$BIND_STATE" \
    --arg bind_msg "$BIND_MSG" \
    '{
      skill: "service-omni-presence-status-deploy",
      status: "blocked",
      sobject_type: $sobject,
      presence_statuses: [{developer_name: $avail_dn, channels: [$chan], state: $bind_state}],
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      manual_actions: [],
      blocking_issue: $bind_msg
    }'
  exit 1
fi

# Skill-level status: reused iff BOTH Unchanged; otherwise the "highest" activity wins (created > updated > reused).
STATUS="reused"
if [ "$STATE_AVAILABLE" != "Unchanged" ] || [ "$STATE_BUSY" != "Unchanged" ]; then
  # If any component was Created → status: created; else: updated
  if [ "$STATE_AVAILABLE" = "Created" ] || [ "$STATE_BUSY" = "Created" ]; then
    STATUS="created"
  else
    STATUS="updated"
  fi
fi

jq -n \
  --arg status "$STATUS" \
  --arg sobject "$SOBJECT_TYPE" \
  --arg avail_dn "$AVAILABLE_STATUS_DN" \
  --arg avail_lbl "$AVAILABLE_STATUS_LABEL" \
  --arg chan "$BOUND_CHANNEL_DN" \
  --arg state_avail "$STATE_AVAILABLE" \
  --arg state_busy "$STATE_BUSY" \
  --arg deploy_id "$DEPLOY_ID" \
  --arg channel_source "$CHANNEL_SOURCE" \
  --arg binding_verified "$BINDING_VERIFIED" \
  --arg busy_exists "$BUSY_EXISTS" \
  '{
    skill: "service-omni-presence-status-deploy",
    status: $status,
    sobject_type: $sobject,
    channel_developer_name: $chan,
    channel_source: $channel_source,
    binding_verified: ($binding_verified == "true"),
    presence_statuses: [
      {developer_name: $avail_dn,      label: $avail_lbl,       channels: [$chan], state: $state_avail},
      {developer_name: "Busy", label: "Busy", channels: [],      state: $state_busy, reused_existing: ($busy_exists == "true")}
    ],
    deploy_id: $deploy_id,
    manual_actions: [],
    blocking_issue: null
  }'
