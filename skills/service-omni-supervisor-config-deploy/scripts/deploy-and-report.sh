#!/usr/bin/env bash
# deploy-and-report.sh - deploy a selected OmniSupervisorConfig (Profile scope + Queue list + Supervisor-user list) in one atomic, production-guarded Metadata deploy (async + poll); idempotent. Args, behavior, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash deploy-and-report.sh <org-alias> [supervisor_count] [additional_queues_csv] [profiles_csv] [skill_visibility] [config_developer_name]"}' >&2
  exit 1
fi

ORG="$1"
SUPERVISOR_COUNT="${2:-1}"
ADDITIONAL_QUEUES_CSV="${3:-}"
SKILL_VISIBILITY_INPUT="${5:-${OMNI_SUPERVISOR_SKILL_VISIBILITY:-}}"
CONFIG_DEVELOPER_NAME="${6:-${OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME:-Omni_Supervisor}}"
CONFIG_MASTER_LABEL_INPUT="${OMNI_SUPERVISOR_CONFIG_MASTER_LABEL:-}"

if ! [[ "$CONFIG_DEVELOPER_NAME" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid config_developer_name '$CONFIG_DEVELOPER_NAME'. It must start with a letter and contain only A-Z, a-z, 0-9, or _ (maximum 80 characters).\"}" >&2
  exit 1
fi

case "$SKILL_VISIBILITY_INPUT" in
  ""|AllSkills|AnySkill) ;;
  *)
    echo "{\"error\":\"Invalid skill_visibility '$SKILL_VISIBILITY_INPUT'. Allowed: AllSkills, AnySkill\"}" >&2
    exit 1
    ;;
esac

if ! [[ "$SUPERVISOR_COUNT" =~ ^[0-9]+$ ]] || [ "$SUPERVISOR_COUNT" -lt 1 ] || [ "$SUPERVISOR_COUNT" -gt 5 ]; then
  echo "{\"error\":\"Invalid supervisor_count '$SUPERVISOR_COUNT'. Must be integer 1..5\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"
TEMPLATE_XML="$ASSETS_DIR/force-app/main/default/omniSupervisorConfigs/Omni_Supervisor.omniSupervisorConfig-meta.xml"

emit_blocked() {
  local reason="$1"
  local click_path="$2"
  jq -n \
    --arg skill "service-omni-supervisor-config-deploy" \
    --arg reason "$reason" \
    --arg click_path "$click_path" \
    --arg config_developer_name "$CONFIG_DEVELOPER_NAME" \
    '{
      skill: $skill,
      status: "blocked",
      config_developer_name: $config_developer_name,
      config_id: null,
      supervisor_users_bound: [],
      supervisor_users_count: 0,
      queues_bound: [],
      queues_count: 0,
      deploy_id: null,
      state: null,
      manual_actions: [$click_path],
      blocking_issue: $reason
    }'
  exit 1
}

# emit read-only plan preview JSON and exit 0 (PLAN_ONLY mode)
emit_plan() {
  local status="$1"
  local detail="$2"
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    --arg config_developer_name "$CONFIG_DEVELOPER_NAME" \
    '{
      skill: "service-omni-supervisor-config-deploy",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      config_developer_name: $config_developer_name,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Safe-to-write guard: sandbox / CDO / trial / DE only
ORG_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1") || {
  emit_blocked "Failed to query Organization for safe_to_write guard." "Verify org auth: sf org display --target-org $ORG"
}
ORG_ID=$(echo "$ORG_JSON" | jq -r '.result.records[0].Id')
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON" | jq -r '.result.records[0].TrialExpirationDate')
ORG_TYPE=$(echo "$ORG_JSON" | jq -r '.result.records[0].OrganizationType')

SAFE="false"
if [ "$IS_SANDBOX" = "true" ]; then SAFE="true"; fi
if [ "$TRIAL_EXP" != "null" ] && [ "$TRIAL_EXP" != "" ]; then SAFE="true"; fi
if [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then SAFE="true"; fi

if [ "$SAFE" != "true" ]; then
  emit_blocked \
    "Refusing to deploy to non-sandbox, non-trial, non-DE org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, CDO, trial, or Developer Edition org." \
    "Verify org type: sf org display --target-org $ORG"
fi

# Org suffix (chars 11-18 of the Org Id, lowercased) scopes the supervisor-user search to THIS org
# (users-create provisions supervisor{N}.<suffix>@example.com).
SUFFIX=$(echo -n "${ORG_ID:10:8}" | tr '[:upper:]' '[:lower:]')

# Discover supervisor users for THIS org's suffix
SUPER_USERS_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT Id, Username, Profile.Name FROM User WHERE Username LIKE 'supervisor%.${SUFFIX}@example.com' AND IsActive=true ORDER BY Username LIMIT $SUPERVISOR_COUNT" 2>/dev/null || echo '{}')

# Distinguish query failure from a clean zero-result: only a parseable records array is authoritative.
if ! echo "$SUPER_USERS_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
  emit_blocked \
    "Supervisor-user discovery query was inconclusive (not a clean result set): $(echo "$SUPER_USERS_JSON" | head -c 200). Not proceeding on an inconclusive read." \
    "Verify org auth and retry"
fi

FOUND_COUNT=$(echo "$SUPER_USERS_JSON" | jq -r '.result.records | length')

# Require the requested number of active supervisors - a partial set would deploy a config that
# monitors fewer supervisors than the operator asked for, silently under-provisioning.
if [ "$FOUND_COUNT" -lt "$SUPERVISOR_COUNT" ]; then
  emit_blocked \
    "Expected $SUPERVISOR_COUNT active supervisor user(s) matching 'supervisor{1..N}.${SUFFIX}@example.com'; found only $FOUND_COUNT. Provision or reactivate the missing supervisor users, then rerun this skill." \
    ""
fi

SUPERVISOR_USERNAMES=$(echo "$SUPER_USERS_JSON" | jq -r '.result.records[].Username')
SUPERVISOR_IDS=$(echo "$SUPER_USERS_JSON" | jq -r '[.result.records[].Id]')

# Build <omniSupervisorConfigUser> blocks
SUPERVISOR_USERS_XML=""
while IFS= read -r uname; do
  [ -z "$uname" ] && continue
  SUPERVISOR_USERS_XML+="    <omniSupervisorConfigUser>
        <user>$uname</user>
    </omniSupervisorConfigUser>
"
done <<< "$SUPERVISOR_USERNAMES"

# Optional <omniSupervisorConfigProfile> companions. Core resolves config by user first, falling back
# to profile only when a supervisor has no user row; since we bind every supervisor by user, profile
# companions are omitted by default. Supply a profiles CSV (4th arg) of metadata fullNames to opt in.
PROFILES_CSV_OVERRIDE="${4:-}"
PROFILE_SCOPE_XML=""
RESOLVED_PROFILE_META=""
if [ -n "$PROFILES_CSV_OVERRIDE" ]; then
  # Only profiles that actually exist on the org can be deployed; a missing one fails the deploy with
  # "no Profile named <X> found", so validate each supplied fullName up front.
  META_PROFILE_FULLNAMES=$(sf org list metadata -m Profile -o "$ORG" --json 2>/dev/null | jq -r '.result[]?.fullName' 2>/dev/null || echo "")
  # `|| true`: grep -v exits 1 when every line is blank (e.g. profiles_csv is just "," ), which under
  # set -euo pipefail would kill the script mid-flight instead of yielding an empty list.
  PROFILE_NAMES=$(printf '%s' "$PROFILES_CSV_OVERRIDE" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' || true)
  UNRESOLVED_PROFILES=""
  while IFS= read -r pname; do
    [ -z "$pname" ] && continue
    if ! [[ "$pname" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
      emit_blocked "Invalid profile fullName '$pname' in profiles_csv (allowed: A-Z a-z 0-9 _; pass metadata fullNames such as Standard,ServiceCloud)." "sf org list metadata -m Profile -o $ORG"
    fi
    if printf '%s\n' "$META_PROFILE_FULLNAMES" | grep -Fxq "$pname"; then
      if ! printf '%s\n' "$RESOLVED_PROFILE_META" | grep -Fxq "$pname"; then
        RESOLVED_PROFILE_META+="$pname
"
        p_esc=$(printf '%s' "$pname" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
        PROFILE_SCOPE_XML+="    <omniSupervisorConfigProfile>
        <profile>$p_esc</profile>
    </omniSupervisorConfigProfile>
"
      fi
    else
      UNRESOLVED_PROFILES+="$pname "
    fi
  done <<< "$PROFILE_NAMES"
  if [ -n "$UNRESOLVED_PROFILES" ]; then
    emit_blocked \
      "profiles_csv contained profile fullName(s) not present on this org: $(printf '%s' "$UNRESOLVED_PROFILES" | sed 's/ *$//'). Pass metadata fullNames that exist (see 'sf org list metadata -m Profile')." \
      "sf org list metadata -m Profile -o $ORG"
  fi
fi

# Resolve the queues to bind: a caller-supplied CSV is authoritative (actual upstream queues), else
# fall back to canonical demo names. Either way, verify each queue exists before binding.
if [ -n "$ADDITIONAL_QUEUES_CSV" ]; then
  IFS=',' read -ra REQUESTED_QUEUES <<< "$ADDITIONAL_QUEUES_CSV"
  ALL_QUEUES=()
  for q in "${REQUESTED_QUEUES[@]}"; do
    q_trimmed=$(echo "$q" | xargs)
    [ -n "$q_trimmed" ] && ALL_QUEUES+=("$q_trimmed")
  done
  QUEUE_SOURCE="caller_supplied"
else
  ALL_QUEUES=("CaseQueue" "messagingqueue")
  QUEUE_SOURCE="canonical_default"
fi

QUEUE_LIST_XML=""
QUEUES_BOUND_JSON="[]"
MISSING_QUEUES=()
for q in "${ALL_QUEUES[@]}"; do
  # Validate DeveloperName shape (SOQL-injection guard) before querying.
  if ! [[ "$q" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
    emit_blocked "Invalid queue DeveloperName '$q' (allowed: A-Z a-z 0-9 _). Fix the queues argument." "Pass valid queue DeveloperNames"
  fi
  Q_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='$q' LIMIT 1" 2>/dev/null || echo '{}')
  if ! echo "$Q_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    emit_blocked "Queue existence check for '$q' was inconclusive: $(echo "$Q_JSON" | head -c 160). Not proceeding on an inconclusive read." "Verify org auth and retry"
  fi
  Q_EXISTS=$(echo "$Q_JSON" | jq -r '.result.records | length')
  if [ "$Q_EXISTS" -ge 1 ]; then
    QUEUE_LIST_XML+="    <omniSupervisorConfigQueue>
        <queue>$q</queue>
    </omniSupervisorConfigQueue>
"
    QUEUES_BOUND_JSON=$(echo "$QUEUES_BOUND_JSON" | jq --arg q "$q" '. + [$q]')
  else
    MISSING_QUEUES+=("$q")
  fi
done

QUEUES_COUNT=$(echo "$QUEUES_BOUND_JSON" | jq -r 'length')

# Every requested queue must exist; block if ANY is absent (dropping one would under-provision silently).
if [ "${#MISSING_QUEUES[@]}" -gt 0 ]; then
  emit_blocked \
    "Requested queue(s) not found on org: ${MISSING_QUEUES[*]} (of requested: ${ALL_QUEUES[*]}). Every requested queue must exist before the supervisor config can bind it. Run service-omni-queue-deploy first, or pass only queue DeveloperName(s) that exist as the 3rd argument." \
    "bash ../service-omni-queue-deploy/scripts/verify-and-align.sh $ORG"
fi

if [ "$QUEUES_COUNT" -lt 1 ]; then
  emit_blocked \
    "No queues resolved to bind (checked: ${ALL_QUEUES[*]}). Run service-omni-queue-deploy first, or pass the actual queue DeveloperName(s) as the 3rd argument." \
    "bash ../service-omni-queue-deploy/scripts/verify-and-align.sh $ORG"
fi

# A metadata redeploy replaces the config's Data API action/tab companions. Snapshot every
# reference-free companion before updating an existing config and restore it after the deploy.
# Unknown/reference-bearing rows are blocked before deploy because recreating an incomplete row
# would be worse than leaving the existing config untouched.
SAFE_ACTIONS="AllAgents.ChangeQueues AllAgents.ChangeSkills AllAgents.ChangeGroups AllAgents.AssignLearning QueuesBacklog.ManageQueues"
SAFE_TABS="Wallboard Agents QueuesBacklog AssignedWork SkillsBacklog Reports Alerts"
in_list() {
  local needle="$1"; shift
  local candidate
  for candidate in "$@"; do [ "$candidate" = "$needle" ] && return 0; done
  return 1
}

CFG_EXIST_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT Id, MasterLabel, SkillVisibility FROM OmniSupervisorConfig WHERE DeveloperName='$CONFIG_DEVELOPER_NAME' LIMIT 1" 2>/dev/null || echo '{}')
if ! echo "$CFG_EXIST_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
  emit_blocked "OmniSupervisorConfig discovery was inconclusive. Not deploying because existing skill visibility and surface companions cannot be preserved safely." "Verify org auth and retry"
fi

EXISTING_CONFIG_ID=$(echo "$CFG_EXIST_JSON" | jq -r '.result.records[0].Id // ""')
EXISTING_MASTER_LABEL=$(echo "$CFG_EXIST_JSON" | jq -r '.result.records[0].MasterLabel // ""')
EXISTING_SKILL_VISIBILITY=$(echo "$CFG_EXIST_JSON" | jq -r '.result.records[0].SkillVisibility // ""')
CONFIG_MASTER_LABEL="${CONFIG_MASTER_LABEL_INPUT:-${EXISTING_MASTER_LABEL:-${CONFIG_DEVELOPER_NAME//_/ }}}"
CONFIG_MASTER_LABEL_XML=$(printf '%s' "$CONFIG_MASTER_LABEL" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g; s/'"'"'/\&apos;/g')
SKILL_VISIBILITY="${SKILL_VISIBILITY_INPUT:-${EXISTING_SKILL_VISIBILITY:-AllSkills}}"
case "$SKILL_VISIBILITY" in
  AllSkills|AnySkill) ;;
  *) emit_blocked "Existing OmniSupervisorConfig has unsupported SkillVisibility '$SKILL_VISIBILITY'; pass AllSkills or AnySkill explicitly as the 5th argument." "Review Omni Supervisor configuration in Setup" ;;
esac

SNAPSHOT_ACTIONS='[]'
SNAPSHOT_TABS='[]'
if [ -n "$EXISTING_CONFIG_ID" ]; then
  ACTIONS_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT OmniSupervisorActionType, DisplayOrder FROM OmniSupervisorConfigAction WHERE OmniSupervisorConfigId='$EXISTING_CONFIG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
  TABS_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT OmniSupervisorTabType, DisplayOrder FROM OmniSupervisorConfigTab WHERE OmniSupervisorConfigId='$EXISTING_CONFIG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
  if ! echo "$ACTIONS_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1 \
     || ! echo "$TABS_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    emit_blocked "Existing supervisor surface discovery was inconclusive; its actions and tabs cannot be safely restored after a metadata deploy." "Verify OmniSupervisorConfigAction and OmniSupervisorConfigTab access, then retry"
  fi
  SNAPSHOT_ACTIONS=$(echo "$ACTIONS_JSON" | jq -c '[.result.records[] | {type:.OmniSupervisorActionType, order:.DisplayOrder}]')
  SNAPSHOT_TABS=$(echo "$TABS_JSON" | jq -c '[.result.records[] | {type:.OmniSupervisorTabType, order:.DisplayOrder}]')
  while IFS= read -r surface_type; do
    [ -z "$surface_type" ] && continue
    if ! in_list "$surface_type" $SAFE_ACTIONS; then
      emit_blocked "Existing supervisor action '$surface_type' cannot be safely restored by this skill; no deploy was attempted." "Preserve or reconfigure this action manually in Setup"
    fi
  done < <(echo "$SNAPSHOT_ACTIONS" | jq -r '.[].type')
  while IFS= read -r surface_type; do
    [ -z "$surface_type" ] && continue
    if ! in_list "$surface_type" $SAFE_TABS; then
      emit_blocked "Existing supervisor tab '$surface_type' cannot be safely restored by this skill; no deploy was attempted." "Preserve or reconfigure this tab manually in Setup"
    fi
  done < <(echo "$SNAPSHOT_TABS" | jq -r '.[].type')
fi

# PLAN_ONLY: prerequisites (supervisor users + queues) are validated above; report whether the
# OmniSupervisorConfig already exists (read-only) and stop before materializing/deploying.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ -n "$EXISTING_CONFIG_ID" ]; then
    emit_plan "reused" "OmniSupervisorConfig '$CONFIG_DEVELOPER_NAME' already exists; a --run would reconcile supervisor users and $QUEUES_COUNT queue(s), preserve SkillVisibility=$SKILL_VISIBILITY, and restore its existing action/tab surface."
  else
    emit_plan "action_needed" "Would deploy OmniSupervisorConfig '$CONFIG_DEVELOPER_NAME' binding supervisor users + $QUEUES_COUNT queue(s)."
  fi
fi

# Materialize the token-substituted deploy artifact under /tmp/ (mktemp -d + 0700; the artifact holds
# resolved usernames and is removed by the cleanup trap).
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p /tmp/omni-supervisor-config-deploy
chmod 700 /tmp/omni-supervisor-config-deploy 2>/dev/null || true
WORK_DIR="$(mktemp -d "/tmp/omni-supervisor-config-deploy/${STAMP}.XXXXXX")"
chmod 700 "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$WORK_DIR/force-app/main/default/omniSupervisorConfigs"

cp "$ASSETS_DIR/sfdx-project.json" "$WORK_DIR/sfdx-project.json"
PACKAGE_CONTENT=$(cat "$ASSETS_DIR/package.xml")
PACKAGE_CONTENT="${PACKAGE_CONTENT/Omni_Supervisor/$CONFIG_DEVELOPER_NAME}"
printf '%s' "$PACKAGE_CONTENT" > "$WORK_DIR/package.xml"

TEMPLATE_CONTENT=$(cat "$TEMPLATE_XML")

RESOLVED_XML="${TEMPLATE_CONTENT/__SUPERVISOR_USERS_XML__/$SUPERVISOR_USERS_XML}"
RESOLVED_XML="${RESOLVED_XML/__PROFILE_SCOPE_XML__/$PROFILE_SCOPE_XML}"
RESOLVED_XML="${RESOLVED_XML/__QUEUE_LIST_XML__/$QUEUE_LIST_XML}"
RESOLVED_XML="${RESOLVED_XML/__SKILL_VISIBILITY__/$SKILL_VISIBILITY}"
RESOLVED_XML="${RESOLVED_XML/__MASTER_LABEL__/$CONFIG_MASTER_LABEL_XML}"

DEPLOY_XML_PATH="$WORK_DIR/force-app/main/default/omniSupervisorConfigs/$CONFIG_DEVELOPER_NAME.omniSupervisorConfig-meta.xml"
printf '%s' "$RESOLVED_XML" > "$DEPLOY_XML_PATH"

# Deploy --async + poll so a synchronous ClientTimeoutError under org load can't produce a false failure.
cd "$WORK_DIR"
START_JSON=$(sf project deploy start --manifest package.xml --target-org "$ORG" --async --json 2>/dev/null || true)
DEPLOY_ID=$(echo "$START_JSON" | jq -r '.result.id // ""')

if [ -z "$DEPLOY_ID" ]; then
  RAW_ERR=$(echo "$START_JSON" | jq -c '.result // .' 2>/dev/null | head -c 800)
  emit_blocked \
    "Could not start the OmniSupervisorConfig deploy (no job id returned). Raw: $RAW_ERR" \
    "Retry: sf project deploy start --manifest package.xml --target-org $ORG"
fi

# Poll to a terminal state. Budget ~20 min (80 * 15s) - comfortably above the 705s/1178s
# retrieves observed on loaded CDOs, and resilient because each report call is non-blocking.
DEPLOY_JSON="$START_JSON"
POLL_STATUS=""
for _ in $(seq 1 80); do
  REPORT_JSON=$(sf project deploy report --job-id "$DEPLOY_ID" --target-org "$ORG" --json 2>/dev/null || true)
  CUR_STATUS=$(echo "$REPORT_JSON" | jq -r '.result.status // ""')
  case "$CUR_STATUS" in
    Succeeded|Failed|SucceededPartial|Canceled)
      DEPLOY_JSON="$REPORT_JSON"; POLL_STATUS="$CUR_STATUS"; break ;;
  esac
  sleep 15
done

if [ -z "$POLL_STATUS" ]; then
  emit_blocked \
    "OmniSupervisorConfig deploy job $DEPLOY_ID did not reach a terminal state within the ~20 min poll budget (server may still be processing under load)." \
    "Check status: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi

DEPLOY_ID=$(echo "$DEPLOY_JSON" | jq -r '.result.id // ""')
DEPLOY_STATUS=$(echo "$DEPLOY_JSON" | jq -r '.result.status // .status // ""')

# Only a fully "Succeeded" deploy is acceptable (SucceededPartial may mean the config never landed).
if [ "$DEPLOY_STATUS" != "Succeeded" ]; then
  RAW_ERR=$(echo "$DEPLOY_JSON" | jq -c '.result // .' 2>/dev/null | head -c 800)
  jq -n \
    --arg deploy_id "$DEPLOY_ID" \
    --arg raw "$RAW_ERR" \
    --arg config_developer_name "$CONFIG_DEVELOPER_NAME" \
    '{
      skill: "service-omni-supervisor-config-deploy",
      status: "blocked",
      config_developer_name: $config_developer_name,
      config_id: null,
      supervisor_users_bound: [],
      supervisor_users_count: 0,
      queues_bound: [],
      queues_count: 0,
      deploy_id: $deploy_id,
      state: "Failed",
      manual_actions: [("Inspect deploy: sf project deploy report --job-id " + $deploy_id)],
      blocking_issue: ("Metadata deploy did not succeed. Raw: " + $raw)
    }'
  exit 1
fi

STATE=$(echo "$DEPLOY_JSON" | jq -r --arg config_developer_name "$CONFIG_DEVELOPER_NAME" '.result.files[] | select(.fullName==$config_developer_name and .type=="OmniSupervisorConfig") | .state' | head -1)
STATE="${STATE:-unknown}"

# Map the deploy state to a status. An UNRECOGNIZED state must NOT silently become "reused"
# (that would mask a component that never actually deployed) - treat it as a hard failure.
case "$STATE" in
  Unchanged)  STATUS="reused" ;;
  Changed)    STATUS="updated" ;;
  Created)    STATUS="created" ;;
  *)
    emit_blocked \
      "Deploy reported '$DEPLOY_STATUS' but the OmniSupervisorConfig component state was '$STATE' (not Unchanged/Changed/Created). Cannot confirm the config landed." \
      "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
    ;;
esac

# Fetch config_id post-deploy (missing Id after success = hard failure). Bounded retry with backoff
# converts transient latency into a definitive read; the guards below still fail closed.
CFG_ID=""
CFG_ID_SLEEP=10
for cfg_attempt in $(seq 1 5); do
  CFG_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT Id FROM OmniSupervisorConfig WHERE DeveloperName='$CONFIG_DEVELOPER_NAME' LIMIT 1" 2>/dev/null || echo '{}')
  if echo "$CFG_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    CFG_ID=$(echo "$CFG_JSON" | jq -r '.result.records[0].Id // ""')
    [ -n "$CFG_ID" ] && break
  fi
  if [ "$cfg_attempt" -lt 5 ]; then sleep "$CFG_ID_SLEEP"; CFG_ID_SLEEP=$((CFG_ID_SLEEP + 10)); fi
done

if [ -z "$CFG_ID" ]; then
  emit_blocked \
    "Deploy reported '$DEPLOY_STATUS' (state=$STATE) but OmniSupervisorConfig '$CONFIG_DEVELOPER_NAME' is not queryable afterward (after retry) - the config did not persist." \
    "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi

# The parent metadata deploy can remove the config's action/tab rows. Restore only the validated
# snapshot and verify it by re-querying. The companion surface skill remains responsible for adding
# any new standard rows requested by the coordinator.
ACTIONS_RESTORED=0
TABS_RESTORED=0
CURRENT_ACTIONS_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT OmniSupervisorActionType, DisplayOrder FROM OmniSupervisorConfigAction WHERE OmniSupervisorConfigId='$CFG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
CURRENT_TABS_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT OmniSupervisorTabType, DisplayOrder FROM OmniSupervisorConfigTab WHERE OmniSupervisorConfigId='$CFG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
if ! echo "$CURRENT_ACTIONS_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1 \
   || ! echo "$CURRENT_TABS_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
  emit_blocked "Config deployed, but the post-deploy supervisor surface read was inconclusive; missing rows cannot be restored safely." "Review the Omni Supervisor surface in Setup"
fi
while IFS= read -r row; do
  [ -z "$row" ] && continue
  surface_type=$(echo "$row" | jq -r '.type')
  display_order=$(echo "$row" | jq -r '.order')
  if echo "$CURRENT_ACTIONS_JSON" | jq -e --arg type "$surface_type" \
      'any(.result.records[]?; .OmniSupervisorActionType == $type)' >/dev/null 2>&1; then
    continue
  fi
  CREATE_JSON=$(sf data create record --target-org "$ORG" --json \
    --sobject OmniSupervisorConfigAction \
    --values "OmniSupervisorConfigId=$CFG_ID OmniSupervisorActionType=$surface_type DisplayOrder=$display_order" 2>/dev/null || true)
  if [ "$(echo "$CREATE_JSON" | jq -r '.result.success // false' 2>/dev/null)" != "true" ]; then
    emit_blocked "Config deployed, but existing supervisor action '$surface_type' could not be restored." "Restore the action in Omni Supervisor Setup, then retry"
  fi
  ACTIONS_RESTORED=$((ACTIONS_RESTORED + 1))
done < <(echo "$SNAPSHOT_ACTIONS" | jq -c '.[]')
while IFS= read -r row; do
  [ -z "$row" ] && continue
  surface_type=$(echo "$row" | jq -r '.type')
  display_order=$(echo "$row" | jq -r '.order')
  if echo "$CURRENT_TABS_JSON" | jq -e --arg type "$surface_type" \
      'any(.result.records[]?; .OmniSupervisorTabType == $type)' >/dev/null 2>&1; then
    continue
  fi
  CREATE_JSON=$(sf data create record --target-org "$ORG" --json \
    --sobject OmniSupervisorConfigTab \
    --values "OmniSupervisorConfigId=$CFG_ID OmniSupervisorTabType=$surface_type DisplayOrder=$display_order" 2>/dev/null || true)
  if [ "$(echo "$CREATE_JSON" | jq -r '.result.success // false' 2>/dev/null)" != "true" ]; then
    emit_blocked "Config deployed, but existing supervisor tab '$surface_type' could not be restored." "Restore the tab in Omni Supervisor Setup, then retry"
  fi
  TABS_RESTORED=$((TABS_RESTORED + 1))
done < <(echo "$SNAPSHOT_TABS" | jq -c '.[]')

VERIFY_ACTIONS_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT OmniSupervisorActionType, DisplayOrder FROM OmniSupervisorConfigAction WHERE OmniSupervisorConfigId='$CFG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
VERIFY_TABS_JSON=$(sf data query --target-org "$ORG" --json \
  -q "SELECT OmniSupervisorTabType, DisplayOrder FROM OmniSupervisorConfigTab WHERE OmniSupervisorConfigId='$CFG_ID' ORDER BY DisplayOrder" 2>/dev/null || echo '{}')
if ! echo "$VERIFY_ACTIONS_JSON" | jq -e --argjson expected "$SNAPSHOT_ACTIONS" '
     [.result.records[]?.OmniSupervisorActionType] as $actual |
     all($expected[]; (.type as $type | $actual | index($type) != null))' >/dev/null 2>&1 \
   || ! echo "$VERIFY_TABS_JSON" | jq -e --argjson expected "$SNAPSHOT_TABS" '
     [.result.records[]?.OmniSupervisorTabType] as $actual |
     all($expected[]; (.type as $type | $actual | index($type) != null))' >/dev/null 2>&1; then
  emit_blocked "Config deployed, but post-deploy verification could not confirm every existing supervisor action and tab was restored." "Review the Omni Supervisor surface in Setup"
fi

# Companion-record verification: the parent existing doesn't prove the child user/queue rows landed.
# Query the child sObjects scoped to this config and require at least the counts we asked to bind.
# Bounded retry with backoff (children can lag the parent); only a parseable array is authoritative.
CFG_USER_JSON='{}'
CFG_USER_COUNT=0
CFG_USER_SLEEP=10
for cu_attempt in $(seq 1 5); do
  CFG_USER_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT Id FROM OmniSupervisorConfigUser WHERE OmniSupervisorConfigId='$CFG_ID'" 2>/dev/null || echo '{}')
  if echo "$CFG_USER_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    CFG_USER_COUNT=$(echo "$CFG_USER_JSON" | jq -r '.result.records | length')
    [ "$CFG_USER_COUNT" -ge "$FOUND_COUNT" ] && break
  fi
  if [ "$cu_attempt" -lt 5 ]; then sleep "$CFG_USER_SLEEP"; CFG_USER_SLEEP=$((CFG_USER_SLEEP + 10)); fi
done
if ! echo "$CFG_USER_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
  emit_blocked \
    "Companion OmniSupervisorConfigUser verification was inconclusive (after retry): $(echo "$CFG_USER_JSON" | head -c 160). Cannot confirm supervisor users bound; not proceeding on an inconclusive read." \
    "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi
CFG_USER_COUNT=$(echo "$CFG_USER_JSON" | jq -r '.result.records | length')

CFG_QUEUE_JSON='{}'
CFG_QUEUE_COUNT=0
CFG_QUEUE_SLEEP=10
for cq_attempt in $(seq 1 5); do
  CFG_QUEUE_JSON=$(sf data query --target-org "$ORG" --json \
    -q "SELECT Id FROM OmniSupervisorConfigQueue WHERE OmniSupervisorConfigId='$CFG_ID'" 2>/dev/null || echo '{}')
  if echo "$CFG_QUEUE_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    CFG_QUEUE_COUNT=$(echo "$CFG_QUEUE_JSON" | jq -r '.result.records | length')
    [ "$CFG_QUEUE_COUNT" -ge "$QUEUES_COUNT" ] && break
  fi
  if [ "$cq_attempt" -lt 5 ]; then sleep "$CFG_QUEUE_SLEEP"; CFG_QUEUE_SLEEP=$((CFG_QUEUE_SLEEP + 10)); fi
done
if ! echo "$CFG_QUEUE_JSON" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
  emit_blocked \
    "Companion OmniSupervisorConfigQueue verification was inconclusive (after retry): $(echo "$CFG_QUEUE_JSON" | head -c 160). Cannot confirm queues bound; not proceeding on an inconclusive read." \
    "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi
CFG_QUEUE_COUNT=$(echo "$CFG_QUEUE_JSON" | jq -r '.result.records | length')

if [ "$CFG_USER_COUNT" -lt "$FOUND_COUNT" ]; then
  emit_blocked \
    "Deploy reported '$DEPLOY_STATUS' (state=$STATE) and the parent config persisted, but only $CFG_USER_COUNT of $FOUND_COUNT intended supervisor-user companion record(s) are present on OmniSupervisorConfig '$CFG_ID'. The config is under-provisioned." \
    "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi
if [ "$CFG_QUEUE_COUNT" -lt "$QUEUES_COUNT" ]; then
  emit_blocked \
    "Deploy reported '$DEPLOY_STATUS' (state=$STATE) and the parent config persisted, but only $CFG_QUEUE_COUNT of $QUEUES_COUNT intended queue companion record(s) are present on OmniSupervisorConfig '$CFG_ID'. The config is under-provisioned." \
    "Inspect deploy: sf project deploy report --job-id $DEPLOY_ID --target-org $ORG"
fi

# Emit skill-report JSON
jq -n \
  --arg status "$STATUS" \
  --arg config_developer_name "$CONFIG_DEVELOPER_NAME" \
  --arg cfg_id "$CFG_ID" \
  --argjson supervisor_ids "$SUPERVISOR_IDS" \
  --arg supervisor_count "$FOUND_COUNT" \
  --argjson queues_bound "$QUEUES_BOUND_JSON" \
  --arg queues_count "$QUEUES_COUNT" \
  --arg queue_source "$QUEUE_SOURCE" \
  --arg cfg_user_count "$CFG_USER_COUNT" \
  --arg cfg_queue_count "$CFG_QUEUE_COUNT" \
  --arg deploy_id "$DEPLOY_ID" \
  --arg state "$STATE" \
  --arg skill_visibility "$SKILL_VISIBILITY" \
  --argjson actions_snapshot "$(echo "$SNAPSHOT_ACTIONS" | jq 'length')" \
  --argjson actions_restored "$ACTIONS_RESTORED" \
  --argjson tabs_snapshot "$(echo "$SNAPSHOT_TABS" | jq 'length')" \
  --argjson tabs_restored "$TABS_RESTORED" \
  '{
    skill: "service-omni-supervisor-config-deploy",
    status: $status,
    config_developer_name: $config_developer_name,
    config_id: (if $cfg_id == "" then null else $cfg_id end),
    supervisor_users_bound: $supervisor_ids,
    supervisor_users_count: ($supervisor_count | tonumber),
    queues_bound: $queues_bound,
    queues_count: ($queues_count | tonumber),
    queue_source: $queue_source,
    verified_companion_user_count: ($cfg_user_count | tonumber),
    verified_companion_queue_count: ($cfg_queue_count | tonumber),
    deploy_id: $deploy_id,
    state: $state,
    skill_visibility: $skill_visibility,
    surface_preservation: {
      actions_snapshot: $actions_snapshot,
      actions_restored: $actions_restored,
      tabs_snapshot: $tabs_snapshot,
      tabs_restored: $tabs_restored
    },
    manual_actions: [],
    blocking_issue: null
  }'
