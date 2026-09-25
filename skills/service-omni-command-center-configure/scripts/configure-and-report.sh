#!/usr/bin/env bash
# Configure Command Center for Service V2 through a preserved OmniChannel Settings document.

set -euo pipefail

usage() {
  echo '{"status":"blocked","reason_code":"invalid_arguments","blocking_issue":"Usage: bash configure-and-report.sh <plan|run> <org-alias> [--apply] [--conversation-monitoring true|false] [--agent-sneak-peek true|false] [--customer-sneak-peek true|false] [--whisper-messaging true|false] [--queues-and-skills true|false]"}' >&2
  exit 1
}

[ "$#" -ge 2 ] || usage

MODE="$1"
ORG="$2"
shift 2

case "$MODE" in
  plan|run) ;;
  *) usage ;;
esac

APPLY=false
REQUESTED_JSON='{"enableCommandCenterForServiceV2":true}'
ASSIGNMENTS=("enableCommandCenterForServiceV2=true")

add_setting() {
  local metadata_name="$1"
  local value="$2"
  if [ "$value" != "true" ] && [ "$value" != "false" ]; then
    jq -n --arg name "$metadata_name" --arg value "$value" \
      '{status:"blocked",reason_code:"invalid_arguments",blocking_issue:("Expected true or false for " + $name + ", received: " + $value)}' >&2
    exit 1
  fi
  REQUESTED_JSON=$(jq -c --arg name "$metadata_name" --argjson value "$value" '. + {($name):$value}' <<<"$REQUESTED_JSON")
  ASSIGNMENTS+=("$metadata_name=$value")
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply)
      APPLY=true
      shift
      ;;
    --conversation-monitoring|--agent-sneak-peek|--customer-sneak-peek|--whisper-messaging|--queues-and-skills)
      [ "$#" -ge 2 ] || usage
      case "$1" in
        --conversation-monitoring) FIELD="enableConversationMonitoring" ;;
        --agent-sneak-peek) FIELD="enableAgentSneakPeek" ;;
        --customer-sneak-peek) FIELD="enableClientSneakPeek" ;;
        --whisper-messaging) FIELD="enableWhisperMessaging" ;;
        --queues-and-skills) FIELD="enableSkillsAndQueueActions" ;;
      esac
      add_setting "$FIELD" "$2"
      shift 2
      ;;
    *) usage ;;
  esac
done

if [ "$MODE" = "plan" ] && [ "$APPLY" = "true" ]; then
  jq -n '{status:"blocked",reason_code:"invalid_arguments",blocking_issue:"--apply is not valid in plan mode."}' >&2
  exit 1
fi

if [ "$MODE" = "run" ] && [ "$APPLY" != "true" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" \
    '{status:"blocked",reason_code:"apply_required",requested:$requested,safe_to_write:null,deploy_id:null,blocking_issue:"run mode requires explicit --apply consent; no org changes were made."}'
  exit 1
fi

for dependency in sf jq python3; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    jq -n --arg dependency "$dependency" \
      '{status:"blocked",reason_code:"missing_dependency",blocking_issue:("Required command is unavailable: " + $dependency)}' >&2
    exit 1
  fi
done

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  jq -n --arg org "$ORG" \
    '{status:"blocked",reason_code:"org_not_authenticated",blocking_issue:("Org alias is not authenticated: " + $org)}' >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCUMENT_TOOL="$SCRIPT_DIR/settings_document.py"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/omni-command-center-configure.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

create_project() {
  local directory="$1"
  mkdir -p "$directory/force-app/main/default"
  printf '%s\n' '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}' > "$directory/sfdx-project.json"
}

retrieve_settings() {
  local directory="$1"
  create_project "$directory"
  (cd "$directory" && sf project retrieve start --target-org "$ORG" --metadata "Settings:OmniChannel" --json >/dev/null 2>&1)
}

settings_path() {
  printf '%s/force-app/main/default/settings/OmniChannel.settings-meta.xml' "$1"
}

if ! retrieve_settings "$WORK_DIR/before"; then
  jq -n --argjson requested "$REQUESTED_JSON" \
    '{status:"blocked",reason_code:"retrieve_failed",requested:$requested,blocking_issue:"Could not retrieve Settings:OmniChannel. Verify org access and retry."}'
  exit 1
fi

BEFORE_XML="$(settings_path "$WORK_DIR/before")"
if [ ! -f "$BEFORE_XML" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" \
    '{status:"blocked",reason_code:"retrieve_failed",requested:$requested,blocking_issue:"The retrieve completed without an OmniChannel settings document."}'
  exit 1
fi

if ! BEFORE_JSON=$(python3 "$DOCUMENT_TOOL" inspect "$BEFORE_XML" 2>/dev/null); then
  jq -n --argjson requested "$REQUESTED_JSON" \
    '{status:"blocked",reason_code:"invalid_settings_document",requested:$requested,blocking_issue:"The retrieved OmniChannel settings document could not be parsed."}'
  exit 1
fi

API_PRESENT=$(jq -r '.settings.enableCommandCenterForServiceV2.present' <<<"$BEFORE_JSON")
if [ "$API_PRESENT" != "true" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" \
    '{status:"blocked",reason_code:"platform_api_unavailable",requested:$requested,before:$before,after:null,safe_to_write:null,deploy_id:null,verification:null,manual_actions:[{id:"WAIT_FOR_W_24039822",title:"Use a target release containing the W-24039822 Metadata API contract (Core PR #16874)."}],blocking_issue:"The target org does not expose enableCommandCenterForServiceV2 in Settings:OmniChannel; no deployment was attempted."}'
  exit 1
fi

values_match() {
  local snapshot="$1"
  jq -ne --argjson requested "$REQUESTED_JSON" --argjson snapshot "$snapshot" '
    all($requested | to_entries[];
      (.key as $name | .value as $wanted |
        $snapshot.settings[$name].present == true and $snapshot.settings[$name].value == $wanted)
    )
  ' >/dev/null
}

query_verification() {
  local seed_json tab_json seed tab
  seed_json=$(sf data query --target-org "$ORG" --use-tooling-api --json \
    --query "SELECT Id FROM FlexiPage WHERE DeveloperName='CommandCenterForServiceV2_L'" 2>/dev/null || true)
  if [ "$(jq -r '.status // 1' <<<"$seed_json" 2>/dev/null)" = "0" ]; then
    if [ "$(jq -r '.result.totalSize // 0' <<<"$seed_json")" -gt 0 ]; then seed=true; else seed=false; fi
  else
    seed=unknown
  fi

  tab_json=$(sf data query --target-org "$ORG" --json \
    --query "SELECT Name FROM TabDefinition WHERE Name='standard-commandcenterforservicev2' LIMIT 1" 2>/dev/null || true)
  if [ "$(jq -r '.status // 1' <<<"$tab_json" 2>/dev/null)" = "0" ]; then
    if [ "$(jq -r '.result.totalSize // 0' <<<"$tab_json")" -gt 0 ]; then tab=true; else tab=false; fi
  else
    tab=unknown
  fi

  jq -n --arg seed "$seed" --arg tab "$tab" \
    '{seed_flexipage_present:$seed,v2_tab_present:$tab,complete:($seed == "true" and $tab == "true")}'
}

BEFORE_MATCH=false
if values_match "$BEFORE_JSON"; then BEFORE_MATCH=true; fi

if [ "$BEFORE_MATCH" = "true" ]; then
  VERIFY_JSON=$(query_verification)
  if [ "$(jq -r '.complete' <<<"$VERIFY_JSON")" != "true" ]; then
    jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --argjson verification "$VERIFY_JSON" \
      '{status:"blocked",reason_code:"seed_incomplete",requested:$requested,before:$before,after:$before,safe_to_write:null,deploy_id:null,verification:$verification,manual_actions:[{id:"REPAIR_V2_SEED",title:"The V2 preference is already enabled but its page or tab cannot be proven. Diagnose the platform seed before retrying; this skill will not force an OFF-to-ON cycle."}],blocking_issue:"Command Center V2 is enabled but its seed artifacts are missing or unreadable."}'
    exit 1
  fi

  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --argjson verification "$VERIFY_JSON" \
    '{status:"reused",reason_code:"already_configured",requested:$requested,before:$before,after:$before,safe_to_write:null,deploy_id:null,verification:$verification,manual_actions:[{id:"ASSIGN_V2_PERMISSION",title:"Assign CommandCenterForServiceUser to each intended supervisor, then verify with service-omni-command-center-analyze."}],blocking_issue:null}'
  exit 0
fi

if [ "$MODE" = "plan" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" \
    '{status:"action_needed",reason_code:"changes_required",requested:$requested,before:$before,after:null,safe_to_write:null,deploy_id:null,verification:null,manual_actions:[],blocking_issue:null}'
  exit 0
fi

ORG_GUARD_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" 2>/dev/null || true)
if [ "$(jq -r '.status // 1' <<<"$ORG_GUARD_JSON" 2>/dev/null)" != "0" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" \
    '{status:"blocked",reason_code:"guard_query_failed",requested:$requested,before:$before,safe_to_write:null,deploy_id:null,blocking_issue:"Could not evaluate the non-production safe_to_write guard."}'
  exit 1
fi

IS_SANDBOX=$(jq -r '.result.records[0].IsSandbox' <<<"$ORG_GUARD_JSON")
TRIAL_EXP=$(jq -r '.result.records[0].TrialExpirationDate // "null"' <<<"$ORG_GUARD_JSON")
ORG_TYPE=$(jq -r '.result.records[0].OrganizationType // ""' <<<"$ORG_GUARD_JSON")
SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] || [ "$TRIAL_EXP" != "null" ] || [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" \
    '{status:"blocked",reason_code:"unsafe_target",requested:$requested,before:$before,safe_to_write:false,deploy_id:null,blocking_issue:"Refusing to configure Command Center V2 in a production customer org."}'
  exit 1
fi

create_project "$WORK_DIR/deploy"
DEPLOY_XML="$(settings_path "$WORK_DIR/deploy")"
if ! python3 "$DOCUMENT_TOOL" render "$BEFORE_XML" "$DEPLOY_XML" "${ASSIGNMENTS[@]}" >/dev/null; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" \
    '{status:"blocked",reason_code:"render_failed",requested:$requested,before:$before,safe_to_write:true,deploy_id:null,blocking_issue:"Could not construct the preserved OmniChannel settings document."}'
  exit 1
fi

DEPLOY_JSON=$(cd "$WORK_DIR/deploy" && sf project deploy start --target-org "$ORG" --source-dir "$DEPLOY_XML" --json 2>/dev/null || true)
DEPLOY_SUCCESS=$(jq -r '.result.success // false' <<<"$DEPLOY_JSON" 2>/dev/null)
DEPLOY_STATUS=$(jq -r '.result.status // ""' <<<"$DEPLOY_JSON" 2>/dev/null)
DEPLOY_ID=$(jq -r '.result.id // ""' <<<"$DEPLOY_JSON" 2>/dev/null)
if [ "$DEPLOY_SUCCESS" != "true" ] || [ "$DEPLOY_STATUS" = "SucceededPartial" ]; then
  DEPLOY_ERROR=$(jq -r '.result.details.componentFailures // [] | if type == "array" then map(.problem) | join("; ") else .problem // "" end' <<<"$DEPLOY_JSON" 2>/dev/null)
  if [ -z "$DEPLOY_ERROR" ] || [ "$DEPLOY_ERROR" = "null" ]; then
    DEPLOY_ERROR=$(jq -r '.message // .result.errorMessage // "Unknown deploy error"' <<<"$DEPLOY_JSON" 2>/dev/null)
  fi
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --arg id "$DEPLOY_ID" --arg error "$DEPLOY_ERROR" \
    '{status:"blocked",reason_code:"deploy_failed",requested:$requested,before:$before,after:null,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:null,blocking_issue:("OmniChannel settings deployment failed: " + $error)}'
  exit 1
fi

if ! retrieve_settings "$WORK_DIR/after"; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --arg id "$DEPLOY_ID" \
    '{status:"blocked",reason_code:"verification_failed",requested:$requested,before:$before,after:null,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:null,blocking_issue:"Deployment succeeded, but post-deploy Settings:OmniChannel retrieval failed."}'
  exit 1
fi

AFTER_XML="$(settings_path "$WORK_DIR/after")"
if [ ! -f "$AFTER_XML" ] || ! AFTER_JSON=$(python3 "$DOCUMENT_TOOL" inspect "$AFTER_XML" 2>/dev/null); then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --arg id "$DEPLOY_ID" \
    '{status:"blocked",reason_code:"verification_failed",requested:$requested,before:$before,after:null,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:null,blocking_issue:"Deployment succeeded, but the post-deploy settings document could not be inspected."}'
  exit 1
fi

if ! values_match "$AFTER_JSON"; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --argjson after "$AFTER_JSON" --arg id "$DEPLOY_ID" \
    '{status:"blocked",reason_code:"verification_failed",requested:$requested,before:$before,after:$after,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:null,blocking_issue:"Deployment reported success, but one or more requested settings did not persist."}'
  exit 1
fi

VERIFY_JSON=$(query_verification)
if [ "$(jq -r '.complete' <<<"$VERIFY_JSON")" != "true" ]; then
  jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --argjson after "$AFTER_JSON" --argjson verification "$VERIFY_JSON" --arg id "$DEPLOY_ID" \
    '{status:"blocked",reason_code:"seed_incomplete",requested:$requested,before:$before,after:$after,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:$verification,manual_actions:[{id:"INSPECT_V2_SEED",title:"The settings persisted, but the V2 page and tab were not both observable. Inspect the platform seed hook before claiming readiness."}],blocking_issue:"Command Center V2 settings persisted, but seed verification is incomplete."}'
  exit 1
fi

jq -n --argjson requested "$REQUESTED_JSON" --argjson before "$BEFORE_JSON" --argjson after "$AFTER_JSON" --argjson verification "$VERIFY_JSON" --arg id "$DEPLOY_ID" \
  '{status:"configured",reason_code:"configured_and_verified",requested:$requested,before:$before,after:$after,safe_to_write:true,deploy_id:(if $id == "" then null else $id end),verification:$verification,manual_actions:[{id:"ASSIGN_V2_PERMISSION",title:"Assign CommandCenterForServiceUser to each intended supervisor, then verify with service-omni-command-center-analyze."}],blocking_issue:null}'
