#!/usr/bin/env bash
# Probes the target org and writes org_profile.json.
# Usage: bash audit_org.sh <alias> [output_file]
set -euo pipefail

ALIAS="$1"
OUT_FILE="${2:-org_profile.json}"

echo "⧗ Auditing org: $ALIAS"

# Org identity
ORG_JSON=$(sf org display --target-org "$ALIAS" --json 2>/dev/null)
ORG_ID=$(echo "$ORG_JSON"    | jq -r '.result.id // empty')
INSTANCE_URL=$(echo "$ORG_JSON" | jq -r '.result.instanceUrl // empty')
API_VERSION=$(echo "$ORG_JSON"  | jq -r '.result.apiVersion // "67.0"')
IS_SANDBOX=$(echo "$ORG_JSON"   | jq -r '.result.isSandbox // false')

if [ -z "$ORG_ID" ]; then
  echo "✖ Could not retrieve org info for alias '$ALIAS'. Is the org authenticated?"
  exit 1
fi

echo "  Org: $ORG_ID  |  API: $API_VERSION  |  Sandbox: $IS_SANDBOX"

# A failed query must not look like an empty result. run_query runs inside $(...), a subshell, so it
# records failures in a file the parent reads back after the probes; a shell variable would be lost.
ERR_FILE=$(mktemp)
trap 'rm -f "$ERR_FILE"' EXIT
run_query() {
  local label="$1"; shift
  local out err_tmp rc=0
  err_tmp=$(mktemp)
  # stderr is kept apart from the JSON: sf CLI warnings/update notices must not turn a good query into a failure.
  out=$(sf data query --target-org "$ALIAS" "$@" --json 2>"$err_tmp") || rc=$?
  if echo "$out" | jq -e '.status == 0' >/dev/null 2>&1; then
    echo "$out" | jq '.result.records // []'
  else
    local msg
    msg=$(echo "$out" | jq -r '.message // empty' 2>/dev/null || true)
    [ -n "$msg" ] || msg=$(grep -v '^ *Warning' "$err_tmp" | head -3 | tr '\n' ' ')
    [ -n "$msg" ] || msg="sf data query exited $rc with no output"
    jq -cn --arg l "$label" --arg m "$msg" '{query: $l, error: $m}' >> "$ERR_FILE"
    echo "  ✖ query failed: $label" >&2
    echo '[]'
  fi
  rm -f "$err_tmp"
}

# Active users
echo "  Querying users..."
USERS=$(run_query "users" --query "SELECT Id, Name, Username, IsActive, Profile.Name FROM User WHERE IsActive=true ORDER BY Name")

# Service channels
echo "  Querying service channels..."
SERVICE_CHANNELS=$(run_query "serviceChannels" --query "SELECT Id, DeveloperName, MasterLabel FROM ServiceChannel")

# Queues
echo "  Querying queues..."
QUEUES=$(run_query "queues" --query "SELECT Id, Name, DeveloperName FROM Group WHERE Type='Queue'")

# Queue routing configs
echo "  Querying routing configs..."
ROUTING_CONFIGS=$(run_query "routingConfigs" --query "SELECT Id, DeveloperName, MasterLabel, RoutingModel FROM QueueRoutingConfig")

# Presence statuses
echo "  Querying presence statuses..."
PRESENCE_STATUSES=$(run_query "presenceStatuses" --query "SELECT Id, DeveloperName, MasterLabel FROM ServicePresenceStatus")

# Messaging channels
echo "  Querying messaging channels..."
MESSAGING_CHANNELS=$(run_query "messagingChannels" --query "SELECT Id, DeveloperName, MasterLabel, MessageType, IsActive FROM MessagingChannel")

# Communication channel lines (Tooling API)
echo "  Querying communication channel lines..."
CHANNEL_LINES=$(run_query "channelLines" --use-tooling-api --query "SELECT Id, Code, CodeStatus FROM CommunicationChannelLine")

# Permission sets the skill assigns or depends on, and who holds them
echo "  Querying permission sets..."
PERMISSION_SETS=$(run_query permissionSets \
  --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ('Omni_Agent','ContactCenterAdminNativeCCaaS','ContactCenterAgentNativeCCaaS','ContactCenterSupervisorNativeCCaaS')")
PERMISSION_SET_ASSIGNMENTS=$(run_query permissionSetAssignments \
  --query "SELECT AssigneeId, Assignee.Username, PermissionSet.Name FROM PermissionSetAssignment WHERE PermissionSet.Name IN ('Omni_Agent','ContactCenterAdminNativeCCaaS','ContactCenterAgentNativeCCaaS','ContactCenterSupervisorNativeCCaaS')")

# Console apps (Step 7 reuses one if present)
echo "  Querying console apps..."
CONSOLE_APPS=$(run_query consoleApps \
  --query "SELECT DurableId, DeveloperName, Label, NavType FROM AppDefinition WHERE NavType='Console'")

# Artifacts a freshly licensed AFCC org ships with. If one is absent it was most likely deleted, so
# it is reported for restoring rather than planned as a normal create.
PERMISSION_SET_LICENSE_NAMES='["ContactCenterAdminNativeCCaaS","ContactCenterAgentNativeCCaaS","ContactCenterSupervisorNativeCCaaS"]'
ERRORS=$(jq -cs '.' "$ERR_FILE")

MISSING_DEFAULTS=$(jq -n \
  --argjson channels "$SERVICE_CHANNELS" --argjson queues "$QUEUES" --argjson psets "$PERMISSION_SETS" \
  --argjson psnames "$PERMISSION_SET_LICENSE_NAMES" '
  [ (["sfdc_livemessage","sfdc_phone"][] as $d | select(($channels | map(.DeveloperName) | index($d)) == null)
      | {type: "ServiceChannel", name: $d}),
    (select(($queues | map(.DeveloperName) | index("Default_Queue_Agentforce_Contact_Center")) == null)
      | {type: "Queue", name: "Default_Queue_Agentforce_Contact_Center"}),
    ($psnames[] as $d | select(($psets | map(.Name) | index($d)) == null)
      | {type: "PermissionSet", name: $d}) ]')
# A type whose source query failed has no data to judge, so it must not be reported as deleted.
MISSING_DEFAULTS=$(jq -n --argjson md "$MISSING_DEFAULTS" --argjson errs "$ERRORS" '
  {ServiceChannel: "serviceChannels", Queue: "queues", PermissionSet: "permissionSets"} as $src
  | $md | map(select(. as $m | ($errs | map(.query) | index($src[$m.type])) == null))')
if [ "$(echo "$MISSING_DEFAULTS" | jq 'length')" -gt 0 ]; then
  echo "  ⚠ Expected out-of-the-box artifacts are missing (likely deleted):" >&2
  echo "$MISSING_DEFAULTS" | jq -r '.[] | "    - \(.type) \(.name)"' >&2
fi

# Write org_profile.json
jq -n \
  --arg alias        "$ALIAS" \
  --arg orgId        "$ORG_ID" \
  --arg instanceUrl  "$INSTANCE_URL" \
  --arg apiVersion   "$API_VERSION" \
  --argjson isSandbox        "$IS_SANDBOX" \
  --argjson users            "$USERS" \
  --argjson serviceChannels  "$SERVICE_CHANNELS" \
  --argjson queues           "$QUEUES" \
  --argjson routingConfigs   "$ROUTING_CONFIGS" \
  --argjson presenceStatuses "$PRESENCE_STATUSES" \
  --argjson messagingChannels "$MESSAGING_CHANNELS" \
  --argjson channelLines     "$CHANNEL_LINES" \
  --argjson permissionSets   "$PERMISSION_SETS" \
  --argjson permissionSetAssignments "$PERMISSION_SET_ASSIGNMENTS" \
  --argjson consoleApps      "$CONSOLE_APPS" \
  --argjson errors           "$ERRORS" \
  --argjson missingDefaults  "$MISSING_DEFAULTS" \
  '{
    alias:       $alias,
    orgId:       $orgId,
    instanceUrl: $instanceUrl,
    apiVersion:  $apiVersion,
    isSandbox:   $isSandbox,
    errors:      $errors,
    missingDefaults: $missingDefaults,
    existing: {
      users:            $users,
      serviceChannels:  $serviceChannels,
      queues:           $queues,
      routingConfigs:   $routingConfigs,
      presenceStatuses: $presenceStatuses,
      messagingChannels: $messagingChannels,
      channelLines:     $channelLines,
      permissionSets:   $permissionSets,
      permissionSetAssignments: $permissionSetAssignments,
      consoleApps:      $consoleApps
    }
  }' > "$OUT_FILE"

if [ "$(echo "$ERRORS" | jq 'length')" -gt 0 ]; then
  echo "✖ Org profile written to $OUT_FILE with query errors:" >&2
  echo "$ERRORS" | jq -r '.[] | "  - \(.query): \(.error)"' >&2
  exit 1
fi

echo "✔ Org profile written to $OUT_FILE"
