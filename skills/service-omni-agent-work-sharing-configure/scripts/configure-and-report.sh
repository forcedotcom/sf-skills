#!/usr/bin/env bash

set -euo pipefail

ORG="${1:-}"
MODE="run"
CONFIRMED="false"

if [ "$#" -gt 0 ]; then
  shift
fi
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan) MODE="plan" ;;
    --confirm-org-wide-visibility) CONFIRMED="true" ;;
    *)
      echo '{"status":"blocked","blocking_issue":"Usage: configure-and-report.sh <org-alias> [--plan] [--confirm-org-wide-visibility]"}'
      exit 1
      ;;
  esac
  shift
done

if [ -z "$ORG" ]; then
  echo '{"status":"blocked","blocking_issue":"An authenticated org alias is required."}'
  exit 1
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/agentwork-sharing.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

emit_result() {
  local status="$1" previous_model="$2" current_model="$3" external_model="$4"
  local changed="$5" dry_run="$6" deploy_id="$7" blocking_issue="$8"
  jq -n \
    --arg status "$status" \
    --arg previous "$previous_model" \
    --arg current "$current_model" \
    --arg external "$external_model" \
    --arg changed "$changed" \
    --arg dry_run "$dry_run" \
    --arg deploy_id "$deploy_id" \
    --arg blocking_issue "$blocking_issue" \
    '{
      skill: "service-omni-agent-work-sharing-configure",
      status: $status,
      previous_sharing_model: (if $previous == "" then null else $previous end),
      sharing_model: (if $current == "" then null else $current end),
      external_sharing_model: (if $external == "" then null else $external end),
      changed: ($changed == "true"),
      dry_run: ($dry_run == "true"),
      deploy_id: (if $deploy_id == "" then null else $deploy_id end),
      blocking_issue: (if $blocking_issue == "" then null else $blocking_issue end)
    }'
}

xml_value() {
  local tag="$1" file="$2"
  tr -d '\n\r' < "$file" | sed -n "s:.*<$tag>\([^<]*\)</$tag>.*:\1:p"
}

retrieve_agent_work() {
  local destination="$1" result object_file
  mkdir -p "$destination"
  if ! result=$(sf project retrieve start \
      --metadata "CustomObject:AgentWork" \
      --target-org "$ORG" \
      --target-metadata-dir "$destination" \
      --unzip \
      --json 2>&1); then
    return 1
  fi
  if [ "$(jq -r '.status // 1' <<<"$result" 2>/dev/null)" != "0" ]; then
    return 1
  fi
  object_file=$(find "$destination" -type f -name 'AgentWork.object' -print -quit)
  if [ -z "$object_file" ]; then
    return 1
  fi
  printf '%s' "$object_file"
}

dry_run="false"
if [ "$MODE" = "plan" ]; then
  dry_run="true"
fi

org_result=$(sf data query \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --target-org "$ORG" \
  --json 2>&1) || {
    emit_result "blocked" "" "" "" false "$dry_run" "" \
      "Unable to classify the target org; refusing an org-wide sharing change."
    exit 1
  }

is_sandbox=$(jq -r '.result.records[0].IsSandbox // false' <<<"$org_result" 2>/dev/null)
trial_expiration=$(jq -r '.result.records[0].TrialExpirationDate // empty' <<<"$org_result" 2>/dev/null)
organization_type=$(jq -r '.result.records[0].OrganizationType // empty' <<<"$org_result" 2>/dev/null)
if [ "$MODE" = "run" ] \
    && [ "$is_sandbox" != "true" ] \
    && [ -z "$trial_expiration" ] \
    && [ "$organization_type" != "Developer Edition" ] \
    && [ "$organization_type" != "Base Edition" ]; then
  emit_result "blocked" "" "" "" false false "" \
    "Production customer org detected; org-wide AgentWork sharing changes are refused."
  exit 1
fi

if ! object_file=$(retrieve_agent_work "$WORK_DIR/before"); then
  emit_result "blocked" "" "" "" false "$dry_run" "" \
    "Unable to retrieve CustomObject:AgentWork through the Metadata API."
  exit 1
fi

previous_model=$(xml_value sharingModel "$object_file")
external_model=$(xml_value externalSharingModel "$object_file")
if [[ ! "$previous_model" =~ ^(Private|Read|ReadWrite)$ ]] || [[ ! "$external_model" =~ ^(Private|Read|ReadWrite)$ ]]; then
  emit_result "blocked" "$previous_model" "$previous_model" "$external_model" false "$dry_run" "" \
    "AgentWork sharing metadata was incomplete or used an unsupported sharing model."
  exit 1
fi

if [ "$previous_model" = "Read" ] || [ "$previous_model" = "ReadWrite" ]; then
  emit_result "reused" "$previous_model" "$previous_model" "$external_model" false "$dry_run" "" ""
  exit 0
fi

if [ "$MODE" = "plan" ]; then
  emit_result "action_needed" "$previous_model" "Read" "$external_model" false true "" ""
  exit 2
fi

if [ "$CONFIRMED" != "true" ]; then
  emit_result "blocked" "$previous_model" "$previous_model" "$external_model" false false "" \
    "Changing AgentWork from Private to Read expands org-wide internal visibility. Re-run with --confirm-org-wide-visibility after reviewing the blast radius."
  exit 1
fi

source_root="$WORK_DIR/source"
mkdir -p "$source_root/force-app/main/default/objects/AgentWork"
cat > "$source_root/sfdx-project.json" <<'JSON'
{"packageDirectories":[{"path":"force-app","default":true}],"namespace":"","sourceApiVersion":"66.0"}
JSON
cat > "$source_root/force-app/main/default/objects/AgentWork/AgentWork.object-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <externalSharingModel>${external_model}</externalSharingModel>
    <sharingModel>Read</sharingModel>
</CustomObject>
XML

if ! deploy_result=$(cd "$source_root" && sf project deploy start \
    --source-dir force-app/main/default/objects/AgentWork/AgentWork.object-meta.xml \
    --target-org "$ORG" \
    --wait 20 \
    --json 2>&1); then
  emit_result "blocked" "$previous_model" "$previous_model" "$external_model" false false "" \
    "The AgentWork sharing metadata deploy failed."
  exit 1
fi

deploy_status=$(jq -r '.result.status // empty' <<<"$deploy_result" 2>/dev/null)
deploy_success=$(jq -r '.result.success // false' <<<"$deploy_result" 2>/dev/null)
deploy_id=$(jq -r '.result.id // empty' <<<"$deploy_result" 2>/dev/null)
if [ "$deploy_status" != "Succeeded" ] && [ "$deploy_success" != "true" ]; then
  emit_result "blocked" "$previous_model" "$previous_model" "$external_model" false false "$deploy_id" \
    "The AgentWork sharing metadata deploy did not succeed."
  exit 1
fi

if ! readback_file=$(retrieve_agent_work "$WORK_DIR/readback"); then
  emit_result "blocked" "$previous_model" "" "$external_model" true false "$deploy_id" \
    "The AgentWork sharing read-back could not be retrieved after deployment."
  exit 1
fi

readback_model=$(xml_value sharingModel "$readback_file")
readback_external=$(xml_value externalSharingModel "$readback_file")
if [ "$readback_model" != "Read" ] || [ "$readback_external" != "$external_model" ]; then
  emit_result "blocked" "$previous_model" "$readback_model" "$readback_external" true false "$deploy_id" \
    "The AgentWork sharing read-back did not match the requested internal model or preserved external model."
  exit 1
fi

emit_result "configured" "$previous_model" "$readback_model" "$readback_external" true false "$deploy_id" ""
