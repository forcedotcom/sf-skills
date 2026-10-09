#!/usr/bin/env bash
# deploy-and-report.sh - ensure a ServiceChannel exists for the requested sObject, reusing any existing (standard/custom) one and deploying the canonical template only if none exists (Salesforce allows one channel per RelatedEntity). Args, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash deploy-and-report.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall]"}' >&2
  exit 1
fi

ORG="$1"
SOBJECT_TYPE="${2:-Case}"

case "$SOBJECT_TYPE" in
  Case)
    CANONICAL_DEVELOPER_NAME="Cases"
    TARGET_CAPACITY_MODEL="TAB_BASED"
    ;;
  Incident)
    CANONICAL_DEVELOPER_NAME="Incidents"
    TARGET_CAPACITY_MODEL="TAB_BASED"
    ;;
  MessagingSession)
    CANONICAL_DEVELOPER_NAME="MessagingSessions"
    TARGET_CAPACITY_MODEL="TAB_BASED"
    ;;
  VoiceCall)
    CANONICAL_DEVELOPER_NAME="VoiceCalls"
    TARGET_CAPACITY_MODEL="TAB_BASED"
    ;;
  *)
    echo "{\"error\":\"Unsupported sobject_type: '$SOBJECT_TYPE'. Supported: Case, Incident, MessagingSession, VoiceCall\"}" >&2
    exit 2
    ;;
esac

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Write guard: can deploy a ServiceChannel, so self-enforce the production-org guard (directly invokable).
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || {
  echo "{\"error\":\"Failed to query Organization for safe_to_write guard: $(printf '%s' "$ORG_JSON" | head -c 300)\"}" >&2
  exit 1
}
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  # Structured `blocked` results go to stdout so the coordinator/caller can parse them (stderr would look like empty output).
  echo "{\"skill\":\"service-omni-service-channel-configure\",\"status\":\"blocked\",\"blocking_issue\":\"Refusing to deploy a ServiceChannel to a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org.\",\"safe_to_write\":false}"
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
    --arg dn "$CANONICAL_DEVELOPER_NAME" \
    '{
      skill: "service-omni-service-channel-configure",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      sobject_type: $sobject,
      channel_developer_name: $dn,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

# Prereq: target sObject exists on the org.
ENTITY_CHECK=$(sf data query --target-org "$ORG" \
  --query "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '$SOBJECT_TYPE'" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0')

if [ "$ENTITY_CHECK" != "1" ]; then
  jq -n --arg sobject "$SOBJECT_TYPE" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: null,
      channel_origin: null,
      target_capacity_model: null,
      target_related_entity_type: $sobject,
      before_state: "unknown",
      deploy_id: null,
      manual_actions: [{
        id: "prereq-entity-missing",
        title: ("sObject " + $sobject + " not available on this org"),
        click_path: (
          if $sobject == "Incident" then "Enable the Incident Management feature via Setup, then re-run"
          elif $sobject == "MessagingSession" then "Enable Enhanced Messaging via Setup → Messaging, then re-run"
          else "Contact your admin - expected sObject missing"
          end
        )
      }],
      blocking_issue: ("Target sObject " + $sobject + " is not queryable on this org")
    }'
  exit 1
fi

# Step 1: Discover an existing ServiceChannel (Tooling API only). Treat the result as authoritative
# only when it parses to a numeric totalSize - an inconclusive read must not deploy a duplicate.
EXISTING_JSON=$(sf data query --use-tooling-api --target-org "$ORG" \
  --query "SELECT Id, DeveloperName, MasterLabel FROM ServiceChannel WHERE RelatedEntity = '$SOBJECT_TYPE' ORDER BY DeveloperName LIMIT 1" \
  --json 2>/dev/null || true)

if ! echo "$EXISTING_JSON" | jq -e '.result.totalSize | numbers' >/dev/null 2>&1; then
  jq -n --arg sobject "$SOBJECT_TYPE" --arg raw "$(printf '%s' "$EXISTING_JSON" | head -c 400)" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: null,
      channel_origin: null,
      before_state: "unknown",
      deploy_id: null,
      manual_actions: [],
      blocking_issue: ("Could not determine whether a ServiceChannel already exists for " + $sobject + " - the discovery query was inconclusive. Not deploying on an inconclusive read. Raw: " + $raw)
    }'
  exit 1
fi

EXISTING_COUNT=$(echo "$EXISTING_JSON" | jq -r '.result.totalSize // 0')

if [ "$EXISTING_COUNT" = "1" ]; then
  # Step 2a: REUSE the existing channel - no deploy.
  EXISTING_DEV_NAME=$(echo "$EXISTING_JSON" | jq -r '.result.records[0].DeveloperName')
  EXISTING_ID=$(echo "$EXISTING_JSON"       | jq -r '.result.records[0].Id')
  # Origin taxonomy: salesforce_standard (OOTB), canonical_asset (matches our asset names), custom (else).
  CHANNEL_ORIGIN="custom"
  case "$EXISTING_DEV_NAME" in
    sfdc_*|Cases) CHANNEL_ORIGIN="salesforce_standard" ;;
    Incidents|MessagingSessions) CHANNEL_ORIGIN="canonical_asset" ;;
  esac

  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dev_name "$EXISTING_DEV_NAME" \
    --arg existing_id "$EXISTING_ID" \
    --arg origin "$CHANNEL_ORIGIN" \
    --arg cap_model "$TARGET_CAPACITY_MODEL" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "reused",
      sobject_type: $sobject,
      channel_developer_name: $dev_name,
      channel_id: $existing_id,
      channel_origin: $origin,
      target_capacity_model: $cap_model,
      target_related_entity_type: $sobject,
      before_state: "Unchanged",
      deploy_id: null,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
fi

# PLAN_ONLY: reaching here means no channel exists for this sObject (the reuse path above already
# returned). A --run would deploy the canonical template. Report that and stop before the deploy.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  emit_plan "action_needed" "No ServiceChannel bound to $SOBJECT_TYPE; would deploy canonical '$CANONICAL_DEVELOPER_NAME'."
fi

# Step 2b: No existing channel - deploy our canonical XML.
if [ ! -f "$ASSETS_DIR/sfdx-project.json" ]; then
  echo "{\"error\":\"Assets DX project not found at $ASSETS_DIR\"}" >&2
  exit 1
fi

CHANNEL_XML="$ASSETS_DIR/force-app/main/default/serviceChannels/${CANONICAL_DEVELOPER_NAME}.serviceChannel-meta.xml"
if [ ! -f "$CHANNEL_XML" ]; then
  echo "{\"error\":\"ServiceChannel asset not found for sobject_type=$SOBJECT_TYPE at $CHANNEL_XML\"}" >&2
  exit 1
fi

DEPLOY_JSON=$(cd "$ASSETS_DIR" && sf project deploy start --target-org "$ORG" --metadata "ServiceChannel:${CANONICAL_DEVELOPER_NAME}" --json 2>/dev/null || true)

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"     | jq -r '.result.id     // null'  2>/dev/null)

translate_deploy_error() {
  local raw="$1"
  case "$raw" in
    *INVALID_TYPE*"ServiceChannel"*)
      echo "OmniChannelSettings is not enabled on this org. Run service-omni-base-settings-configure first."
      ;;
    *"already in use by another Service channel"*)
      echo "Race condition: another process created a ServiceChannel for $SOBJECT_TYPE between our detect and deploy. Re-run to reuse it."
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
  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
    --arg cap_model "$TARGET_CAPACITY_MODEL" \
    --arg deploy_id "$DEPLOY_ID" \
    --arg blocking "$FRIENDLY" \
    --arg raw "$FAILURES" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: $dev_name,
      channel_id: null,
      channel_origin: "canonical_template",
      target_capacity_model: $cap_model,
      target_related_entity_type: $sobject,
      before_state: "unknown",
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      manual_actions: [],
      blocking_issue: $blocking,
      raw_error: $raw
    }'
  exit 1
fi

# Require a clean Succeeded (SucceededPartial / anything else is not success).
DEPLOY_STATUS=$(echo "$DEPLOY_JSON" | jq -r '.result.status // "unknown"' 2>/dev/null)
if [ "$DEPLOY_STATUS" != "Succeeded" ]; then
  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
    --arg cap_model "$TARGET_CAPACITY_MODEL" \
    --arg deploy_id "$DEPLOY_ID" \
    --arg deploy_status "$DEPLOY_STATUS" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: $dev_name,
      channel_id: null,
      channel_origin: "canonical_template",
      target_capacity_model: $cap_model,
      target_related_entity_type: $sobject,
      before_state: "unknown",
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      manual_actions: [],
      blocking_issue: ("Deploy did not fully succeed (result.status=" + $deploy_status + "). Refusing to report success on a partial/ambiguous deploy.")
    }'
  exit 1
fi

# Component state must be a recognized idempotency signal (Created/Changed/Unchanged); else block.
BEFORE_STATE=$(echo "$DEPLOY_JSON" | jq -r '.result.files[0].state // "unknown"' 2>/dev/null)
case "$BEFORE_STATE" in
  Created|Changed) STATUS="created" ;;
  Unchanged)       STATUS="reused"  ;;
  *)
    jq -n \
      --arg sobject "$SOBJECT_TYPE" \
      --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
      --arg cap_model "$TARGET_CAPACITY_MODEL" \
      --arg deploy_id "$DEPLOY_ID" \
      --arg before_state "$BEFORE_STATE" \
      '{
        skill: "service-omni-service-channel-configure",
        status: "blocked",
        sobject_type: $sobject,
        channel_developer_name: $dev_name,
        channel_id: null,
        channel_origin: "canonical_template",
        target_capacity_model: $cap_model,
        target_related_entity_type: $sobject,
        before_state: $before_state,
        deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
        manual_actions: [],
        blocking_issue: ("Unrecognized component deploy state \"" + $before_state + "\" - expected Created, Changed, or Unchanged. Not reporting success.")
      }'
    exit 1
    ;;
esac

# Post-deploy verify: re-query via Tooling API to confirm the channel exists, capture its Id, and
# check RelatedEntity matches the target (a deploy state alone isn't proof of correct binding).
VERIFY_JSON=$(sf data query --use-tooling-api --target-org "$ORG" \
  --query "SELECT Id, DeveloperName, MasterLabel, RelatedEntity FROM ServiceChannel WHERE DeveloperName = '$CANONICAL_DEVELOPER_NAME' LIMIT 1" \
  --json 2>/dev/null || true)

if ! echo "$VERIFY_JSON" | jq -e '.result.totalSize | numbers' >/dev/null 2>&1 \
   || [ "$(echo "$VERIFY_JSON" | jq -r '.result.totalSize')" != "1" ]; then
  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
    --arg deploy_id "$DEPLOY_ID" \
    --arg raw "$(printf '%s' "$VERIFY_JSON" | head -c 300)" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: $dev_name,
      channel_id: null,
      channel_origin: "canonical_template",
      target_related_entity_type: $sobject,
      before_state: "unknown",
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      manual_actions: [],
      blocking_issue: ("Deploy reported success but post-deploy re-query could not confirm the ServiceChannel exists. Raw: " + $raw)
    }'
  exit 1
fi

VERIFIED_ID=$(echo "$VERIFY_JSON"      | jq -r '.result.records[0].Id')
VERIFIED_RELATED=$(echo "$VERIFY_JSON" | jq -r '.result.records[0].RelatedEntity // "null"')

if [ "$VERIFIED_RELATED" != "$SOBJECT_TYPE" ]; then
  jq -n \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
    --arg channel_id "$VERIFIED_ID" \
    --arg related "$VERIFIED_RELATED" \
    '{
      skill: "service-omni-service-channel-configure",
      status: "blocked",
      sobject_type: $sobject,
      channel_developer_name: $dev_name,
      channel_id: $channel_id,
      channel_origin: "canonical_template",
      target_related_entity_type: $sobject,
      before_state: "unknown",
      manual_actions: [],
      blocking_issue: ("ServiceChannel exists but RelatedEntity=\"" + $related + "\" does not match the requested sObject \"" + $sobject + "\".")
    }'
  exit 1
fi

jq -n \
  --arg status "$STATUS" \
  --arg sobject "$SOBJECT_TYPE" \
  --arg dev_name "$CANONICAL_DEVELOPER_NAME" \
  --arg channel_id "$VERIFIED_ID" \
  --arg related "$VERIFIED_RELATED" \
  --arg cap_model "$TARGET_CAPACITY_MODEL" \
  --arg before_state "$BEFORE_STATE" \
  --arg deploy_id "$DEPLOY_ID" \
  '{
    skill: "service-omni-service-channel-configure",
    status: $status,
    sobject_type: $sobject,
    channel_developer_name: $dev_name,
    channel_id: $channel_id,
    channel_origin: "canonical_template",
    target_capacity_model: $cap_model,
    target_related_entity_type: $sobject,
    related_entity_verified: $related,
    before_state: $before_state,
    deploy_id: $deploy_id,
    manual_actions: [],
    blocking_issue: null
  }'
