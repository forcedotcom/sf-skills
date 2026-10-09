#!/usr/bin/env bash
# configure-and-report.sh - WRITE entry point (plan|run): detect the five OmniChannelSettings toggles and, when any are off and safe_to_write, deploy canonical settings + re-verify. Args, JSON status contract, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo '{"status":"blocked","blocking_issue":"Missing required args","usage":"bash configure-and-report.sh <plan|run> <org-alias>"}' >&2
  exit 1
fi

MODE="$1"
ORG="$2"

case "$MODE" in
  plan|run) ;;
  *)
    echo "{\"status\":\"blocked\",\"blocking_issue\":\"Invalid mode '$MODE'. Expected 'plan' or 'run'.\"}" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DETECT_SCRIPT="$SCRIPT_DIR/detect-existing.sh"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

if [ ! -f "$DETECT_SCRIPT" ]; then
  echo "{\"status\":\"blocked\",\"blocking_issue\":\"Sibling script not found: $DETECT_SCRIPT\"}" >&2
  exit 1
fi

# Step 1 - detect current settings
DETECT_EXIT=0
BEFORE_JSON=$(bash "$DETECT_SCRIPT" "$ORG" 2>&1) || DETECT_EXIT=$?

if [ "$DETECT_EXIT" -ne 0 ] || ! echo "$BEFORE_JSON" | jq -e . >/dev/null 2>&1; then
  jq -n --arg raw "$BEFORE_JSON" --argjson exit "$DETECT_EXIT" \
    '{status:"blocked",blocking_issue:("detect-existing.sh failed (exit " + ($exit|tostring) + ")"),before_raw:$raw}'
  exit 1
fi

ALL_ENABLED=$(echo "$BEFORE_JSON" | jq -r '.all_enabled')

# Step 2 - already fully enabled → reused (both modes)
if [ "$ALL_ENABLED" = "true" ]; then
  jq -n --argjson before "$BEFORE_JSON" \
    '{status:"reused",all_enabled:true,before:$before,after:$before,deploy_id:null,safe_to_write:true,
      manual_actions:[{id:"login_behavior",title:"Omni-Channel login behavior (UI-only)",detail:"The Omni-Channel utility auto-open-on-login behavior is a UI-only setting not exposed via the Metadata API. Set it manually if desired: Setup → Omni-Channel → Omni-Channel Settings."}]}'
  exit 0
fi

# Step 3 - plan mode never deploys
if [ "$MODE" = "plan" ]; then
  jq -n --argjson before "$BEFORE_JSON" \
    '{
      status:"action_needed",
      all_enabled:false,
      action_required:"One or more OmniChannelSettings toggles are disabled. Re-run in run mode to deploy.",
      before:$before,
      after:null,
      deploy_id:null,
      manual_actions:[{id:"login_behavior",title:"Omni-Channel login behavior (UI-only)",detail:"The Omni-Channel utility auto-open-on-login behavior is a UI-only setting not exposed via the Metadata API. Set it manually if desired: Setup → Omni-Channel → Omni-Channel Settings."}]
    }'
  exit 0
fi

# Step 4 - run mode: safe_to_write guard (settings deploy mutates the org)
ORG_GUARD_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || {
  jq -n --arg raw "$(printf '%s' "$ORG_GUARD_JSON" | head -c 300)" \
    '{status:"blocked",blocking_issue:("Failed to query Organization for safe_to_write guard: " + $raw)}'
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
  jq -n --argjson before "$BEFORE_JSON" \
    --arg is_sandbox "$IS_SANDBOX" --arg trial "$TRIAL_EXP" --arg type "$ORG_TYPE" \
    '{
      status:"blocked",
      blocking_issue:("Refusing to deploy OmniChannelSettings to a real production customer org (IsSandbox=" + $is_sandbox + ", TrialExpirationDate=" + $trial + ", OrganizationType=" + $type + ")."),
      before:$before,
      safe_to_write:false,
      deploy_id:null
    }'
  exit 1
fi

if [ ! -f "$ASSETS_DIR/sfdx-project.json" ]; then
  echo "{\"status\":\"blocked\",\"blocking_issue\":\"Assets DX project not found at $ASSETS_DIR\"}" >&2
  exit 1
fi

# Step 5 - deploy the canonical settings
SETTINGS_SOURCE="$ASSETS_DIR/force-app/main/default/settings/OmniChannel.settings-meta.xml"
DEPLOY_JSON=$(cd "$ASSETS_DIR" && sf project deploy start --target-org "$ORG" \
  --source-dir "$SETTINGS_SOURCE" --json 2>/dev/null || true)

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_STATUS=$(echo "$DEPLOY_JSON"  | jq -r '.result.status  // .status // ""' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // ""' 2>/dev/null)

if [ "$DEPLOY_SUCCESS" != "true" ] || [ "$DEPLOY_STATUS" = "SucceededPartial" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  if [ -z "$FAILURES" ] || [ "$FAILURES" = "null" ]; then
    FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  fi
  jq -n --argjson before "$BEFORE_JSON" --arg raw "$FAILURES" --arg did "$DEPLOY_ID" \
    '{
      status:"blocked",
      blocking_issue:("OmniChannelSettings deploy did not fully succeed: " + $raw),
      before:$before,
      after:null,
      safe_to_write:true,
      deploy_id:(if $did == "" then null else $did end)
    }'
  exit 1
fi

# Step 6 - re-detect and verify all five toggles are now enabled
AFTER_EXIT=0
AFTER_JSON=$(bash "$DETECT_SCRIPT" "$ORG" 2>&1) || AFTER_EXIT=$?

if [ "$AFTER_EXIT" -ne 0 ] || ! echo "$AFTER_JSON" | jq -e . >/dev/null 2>&1; then
  jq -n --argjson before "$BEFORE_JSON" --arg raw "$AFTER_JSON" --arg did "$DEPLOY_ID" \
    '{status:"blocked",blocking_issue:"Post-deploy re-detect failed",before:$before,after_raw:$raw,deploy_id:(if $did == "" then null else $did end)}'
  exit 1
fi

AFTER_ALL=$(echo "$AFTER_JSON" | jq -r '.all_enabled')

if [ "$AFTER_ALL" != "true" ]; then
  jq -n --argjson before "$BEFORE_JSON" --argjson after "$AFTER_JSON" --arg did "$DEPLOY_ID" \
    '{
      status:"blocked",
      blocking_issue:"Deploy reported success but post-verify shows not all OmniChannelSettings toggles are enabled.",
      before:$before,
      after:$after,
      safe_to_write:true,
      deploy_id:(if $did == "" then null else $did end)
    }'
  exit 1
fi

jq -n --argjson before "$BEFORE_JSON" --argjson after "$AFTER_JSON" --arg did "$DEPLOY_ID" \
  '{
    status:"configured",
    all_enabled:true,
    before:$before,
    after:$after,
    safe_to_write:true,
    deploy_id:(if $did == "" then null else $did end),
    manual_actions:[{id:"login_behavior",title:"Omni-Channel login behavior (UI-only)",detail:"The Omni-Channel utility auto-open-on-login behavior is a UI-only setting not exposed via the Metadata API. Set it manually if desired: Setup → Omni-Channel → Omni-Channel Settings."}]
  }'
