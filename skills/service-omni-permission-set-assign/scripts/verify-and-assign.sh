#!/usr/bin/env bash
# verify-and-assign.sh - assign PermissionSets to N agent users via PermissionSetAssignment POSTs; idempotent (SOQL detects existing pairs), non-destructive. Args, output contract, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash verify-and-assign.sh <org-alias> [<count>] [<permission-set-names-csv>]"}' >&2
  exit 1
fi

ORG="$1"
COUNT="${2:-3}"
PS_NAMES_CSV="${3:-Omni_Agent}"
API_VERSION="v66.0"

# Sanity: count 1..10
if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [ "$COUNT" -lt 1 ] || [ "$COUNT" -gt 10 ]; then
  echo "{\"error\":\"Invalid count '$COUNT' - must be integer 1..10\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Parse CSV into a JSON array
PS_NAMES_JSON=$(echo "$PS_NAMES_CSV" | jq -R -c 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')
PS_COUNT=$(echo "$PS_NAMES_JSON" | jq 'length')

# Each PermissionSet Name is interpolated into SOQL, so validate its DeveloperName shape before any
# sf call; an empty CSV is also rejected.
if [ "$PS_COUNT" -lt 1 ]; then
  echo "{\"error\":\"No permission-set names supplied.\"}" >&2
  exit 1
fi
while IFS= read -r ps_name; do
  if ! [[ "$ps_name" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    echo "{\"error\":\"Invalid permission-set name '$ps_name'. Each must start with a letter and contain only letters, digits, and underscores (max 80 chars).\"}" >&2
    exit 1
  fi
done < <(echo "$PS_NAMES_JSON" | jq -r '.[]')

# Helper: emit blocked JSON
emit_blocked() {
  local msg="$1"
  local click_path="${2:-}"
  local suffix="${3:-}"

  local manual_actions='[]'
  if [ -n "$click_path" ]; then
    manual_actions=$(jq -n --arg cp "$click_path" '[{id: "MANUAL_FIX", title: "Manual fix required", click_path: $cp}]')
  fi

  jq -n \
    --arg msg "$msg" \
    --arg suf "$suffix" \
    --argjson count "$COUNT" \
    --argjson ps_count "$PS_COUNT" \
    --argjson ma "$manual_actions" \
    '{
      skill: "service-omni-permission-set-assign",
      status: "blocked",
      permission_sets: [],
      org_suffix: (if $suf == "" then null else $suf end),
      requested_count: $count,
      expected_assignment_count: ($count * $ps_count),
      before: null,
      assigned_this_run: [],
      assigned_count: 0,
      reused_count: 0,
      after: null,
      manual_actions: $ma,
      blocking_issue: $msg
    }'
  exit 1
}

# Helper: emit read-only plan preview JSON and exit 0 (PLAN_ONLY mode)
emit_plan() {
  local status="$1"
  local detail="$2"
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    '{
      skill: "service-omni-permission-set-assign",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Step 1 - Organization + safe_to_write
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null)

ORG_ID=$(echo "$ORG_JSON"     | jq -r '.result.records[0].Id')
IS_SANDBOX=$(echo "$ORG_JSON"  | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"   | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"    | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

SUFFIX=$(echo "$ORG_ID" | tr '[:upper:]' '[:lower:]' | tail -c 9 | head -c 8)

if [ "$SAFE_TO_WRITE" != "true" ]; then
  emit_blocked "Refusing to assign permission sets on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org." "" "$SUFFIX"
fi

# Step 2 - Locate target PermissionSets
# Build IN clause for PS names
PS_IN_CLAUSE=""
for name in $(echo "$PS_NAMES_JSON" | jq -r '.[]'); do
  if [ -n "$PS_IN_CLAUSE" ]; then PS_IN_CLAUSE="$PS_IN_CLAUSE,"; fi
  PS_IN_CLAUSE="$PS_IN_CLAUSE'$name'"
done

PS_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ($PS_IN_CLAUSE)" \
  --json 2>/dev/null)
FOUND_PS_COUNT=$(echo "$PS_JSON" | jq -r '.result.totalSize // 0')

# Self-heal: if an expected PermissionSet is missing but bundled as an asset, deploy it and re-query
# (so the chain works on a fresh org). safe_to_write was already enforced above.
if [ "$FOUND_PS_COUNT" -lt "$PS_COUNT" ]; then
  FOUND_NAMES=$(echo "$PS_JSON" | jq -c '[.result.records[].Name]')
  MISSING_NAMES=$(jq -n --argjson e "$PS_NAMES_JSON" --argjson f "$FOUND_NAMES" '$e - $f')
  # PLAN_ONLY must be read-only: report the missing perm set(s) and stop before the deploy below.
  if [ "${PLAN_ONLY:-}" = "1" ]; then
    emit_plan "action_needed" "PermissionSet(s) $MISSING_NAMES not present. A --run would deploy the bundled asset (or require manual creation) before assigning; --plan makes no writes."
  fi
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ASSETS_DIR="$SCRIPT_DIR/../assets"
  DEPLOYED_ANY=false
  SELF_HEAL_ERR=""

  # A PermissionSet deploy fails if it references a ServicePresenceStatus absent on the org, so
  # rebuild the servicePresenceStatusAccesses block from the curated statuses that actually exist
  # (none → deploy with no presence access, still a valid grant, rather than failing the chain).
  build_omni_agent_permset() {
    local out_file="$1"
    local existing accesses="" s
    existing=$(sf data query --target-org "$ORG" \
      --query "SELECT DeveloperName FROM ServicePresenceStatus" --json 2>/dev/null \
      | jq -r '[.result.records[].DeveloperName] // []' 2>/dev/null)
    for s in Available_Case Available_Voice Available_Messaging Available_Chat Available_Incident Busy; do
      if echo "$existing" | jq -e --arg s "$s" 'index($s)' >/dev/null 2>&1; then
        accesses="${accesses}    <servicePresenceStatusAccesses>
        <enabled>true</enabled>
        <servicePresenceStatus>${s}</servicePresenceStatus>
    </servicePresenceStatusAccesses>
"
      fi
    done
    cat > "$out_file" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Omni-Channel agent access for demo/test orgs: grants the service presence statuses that exist on the org so agents go online and receive routed work. No ViewAllData/ModifyAllData/ManageUsers or license-gated perms.</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Omni Agent</label>
${accesses}</PermissionSet>
XML
  }

  for miss in $(echo "$MISSING_NAMES" | jq -r '.[]'); do
    if [ -f "$ASSETS_DIR/force-app/main/default/permissionsets/$miss.permissionset-meta.xml" ]; then
      if [ "$miss" = "Omni_Agent" ]; then
        # Deploy a dynamically-generated Omni_Agent (never references a non-existent presence status).
        SH_WORK="$(mktemp -d)"
        mkdir -p "$SH_WORK/force-app/main/default/permissionsets"
        cat > "$SH_WORK/sfdx-project.json" <<'JSON'
{ "packageDirectories": [{ "path": "force-app", "default": true }], "namespace": "", "sourceApiVersion": "66.0" }
JSON
        build_omni_agent_permset "$SH_WORK/force-app/main/default/permissionsets/Omni_Agent.permissionset-meta.xml"
        DEPLOY_OUT=$( cd "$SH_WORK" && sf project deploy start --target-org "$ORG" --metadata "PermissionSet:Omni_Agent" --json 2>/dev/null ) && DEPLOYED_ANY=true || \
          SELF_HEAL_ERR="$SELF_HEAL_ERR $(echo "$DEPLOY_OUT" | jq -r '(.result.details.componentFailures // [] | map(.problem) | join("; ")) // .message // ""' 2>/dev/null)"
        rm -rf "$SH_WORK"
      else
        DEPLOY_OUT=$( cd "$ASSETS_DIR" && sf project deploy start --target-org "$ORG" --metadata "PermissionSet:$miss" --json 2>/dev/null ) && DEPLOYED_ANY=true || \
          SELF_HEAL_ERR="$SELF_HEAL_ERR $(echo "$DEPLOY_OUT" | jq -r '(.result.details.componentFailures // [] | map(.problem) | join("; ")) // .message // ""' 2>/dev/null)"
      fi
    fi
  done
  if [ "$DEPLOYED_ANY" = "true" ]; then
    PS_JSON=$(sf data query --target-org "$ORG" \
      --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ($PS_IN_CLAUSE)" \
      --json 2>/dev/null)
    FOUND_PS_COUNT=$(echo "$PS_JSON" | jq -r '.result.totalSize // 0')
  fi
fi

# Block only if a permission set is STILL missing after the self-heal deploy attempt.
if [ "$FOUND_PS_COUNT" -lt "$PS_COUNT" ]; then
  FOUND_NAMES=$(echo "$PS_JSON" | jq -c '[.result.records[].Name]')
  MISSING_NAMES=$(jq -n --argjson expected "$PS_NAMES_JSON" --argjson found "$FOUND_NAMES" \
    '$expected - $found')
  emit_blocked \
    "Expected PermissionSets $PS_NAMES_JSON; found $FOUND_NAMES. Missing: $MISSING_NAMES. Bundled perm sets deploy automatically; a non-bundled name must be created first via Setup or a package deploy.${SELF_HEAL_ERR:+ Self-heal deploy failed:${SELF_HEAL_ERR}}" \
    "The bundled Omni_Agent grants whichever Omni service presence statuses exist on the org (Available_Case/Available_Voice/Available_Messaging/Busy). Run service-omni-presence-status-deploy first so at least one presence status exists. Otherwise: Setup → Permission Sets → New → Name: (missing DeveloperName) → configure access → Save, or deploy from your manifest: sf project deploy start -x <path-to-package.xml> -o $ORG" \
    "$SUFFIX"
fi

# Build permission_sets array for the report
PERMISSION_SETS_JSON=$(echo "$PS_JSON" | jq -c '[.result.records[] | {developer_name: .Name, id: .Id, label: .Label}]')
PS_IDS_ARR=$(echo "$PS_JSON" | jq -c '[.result.records[].Id]')

# Build SOQL IN clause for PS IDs
PS_IDS_IN=""
for pid in $(echo "$PS_IDS_ARR" | jq -r '.[]'); do
  if [ -n "$PS_IDS_IN" ]; then PS_IDS_IN="$PS_IDS_IN,"; fi
  PS_IDS_IN="$PS_IDS_IN'$pid'"
done

# Step 3 - Locate expected agent users
EXPECTED_USERNAMES=()
for i in $(seq 1 "$COUNT"); do
  EXPECTED_USERNAMES+=("agent${i}.${SUFFIX}@example.com")
done

USER_IN_CLAUSE=""
for un in "${EXPECTED_USERNAMES[@]}"; do
  if [ -n "$USER_IN_CLAUSE" ]; then USER_IN_CLAUSE="$USER_IN_CLAUSE,"; fi
  USER_IN_CLAUSE="$USER_IN_CLAUSE'$un'"
done

# Only active users are valid assignees; filter IsActive=true so an inactive occupant can't satisfy the count.
U_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, Username FROM User WHERE Username IN ($USER_IN_CLAUSE) AND IsActive=true" \
  --json 2>/dev/null)

U_COUNT=$(echo "$U_JSON" | jq -r '.result.totalSize // 0')
if [ "$U_COUNT" -lt "$COUNT" ]; then
  FOUND=$(echo "$U_JSON" | jq -c '[.result.records[].Username]')
  emit_blocked \
    "Expected $COUNT ACTIVE agent users matching pattern 'agent{1..$COUNT}.$SUFFIX@example.com'; found $U_COUNT active ($FOUND). Run service-omni-agent-users-create with count=$COUNT first (and reactivate any deactivated agent users)." \
    "" "$SUFFIX"
fi

USERS_JSON=$(echo "$U_JSON" | jq -c '[.result.records[] | {id: .Id, username: .Username}]')
USER_IDS_ARR=$(echo "$USERS_JSON" | jq -c '[.[].id]')

USER_IDS_IN=""
for uid in $(echo "$USER_IDS_ARR" | jq -r '.[]'); do
  if [ -n "$USER_IDS_IN" ]; then USER_IDS_IN="$USER_IDS_IN,"; fi
  USER_IDS_IN="$USER_IDS_IN'$uid'"
done

# Step 4 - Query existing PermissionSetAssignments for these pairs
PSA_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, AssigneeId, PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId IN ($USER_IDS_IN) AND PermissionSetId IN ($PS_IDS_IN)" \
  --json 2>/dev/null)

# Build the "existing_pairs" set as JSON array of {user_id, permission_set_id}
EXISTING_PAIRS=$(echo "$PSA_JSON" | jq -c '[.result.records[] | {user_id: .AssigneeId, permission_set_id: .PermissionSetId}]')
EXISTING_COUNT=$(echo "$EXISTING_PAIRS" | jq 'length')

# Build the "expected_pairs" set as cross-product of users x perm-sets
EXPECTED_PAIRS=$(jq -n --argjson users "$USERS_JSON" --argjson pss "$PERMISSION_SETS_JSON" \
  '[$users[] as $u | $pss[] as $p | {user_id: $u.id, username: $u.username, permission_set_id: $p.id, permission_set_developer_name: $p.developer_name}]')

EXPECTED_COUNT=$((COUNT * PS_COUNT))

# missing = expected - existing (compared on user_id + permission_set_id keys)
MISSING_PAIRS=$(jq -n --argjson expected "$EXPECTED_PAIRS" --argjson existing "$EXISTING_PAIRS" \
  '[$expected[] | . as $e | select($existing | map(select(.user_id == $e.user_id and .permission_set_id == $e.permission_set_id)) | length == 0)]')
MISSING_COUNT=$(echo "$MISSING_PAIRS" | jq 'length')

# PLAN_ONLY: all detection above is read-only. Report what a --run would do and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ "$MISSING_COUNT" -eq 0 ]; then
    emit_plan "reused" "All $EXPECTED_COUNT (user x permission-set) assignment(s) already present."
  else
    emit_plan "action_needed" "Would assign $MISSING_COUNT missing of $EXPECTED_COUNT expected (user x permission-set) pair(s)."
  fi
fi

# Step 5 - POST PermissionSetAssignment for each missing pair
ASSIGNED_THIS_RUN='[]'
ASSIGNED_COUNT=0
PARTIAL_ERRORS=()

if [ "$MISSING_COUNT" -gt 0 ]; then
  for row in $(echo "$MISSING_PAIRS" | jq -c '.[]'); do
    USER_ID=$(echo "$row"        | jq -r '.user_id')
    USERNAME=$(echo "$row"       | jq -r '.username')
    PS_ID=$(echo "$row"          | jq -r '.permission_set_id')
    PS_DEV_NAME=$(echo "$row"    | jq -r '.permission_set_developer_name')

    # Redirect the sf beta warning off stderr so stdout is pure JSON for jq.
    POST_STDERR="$(mktemp)"
    POST_RESULT=$(sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/PermissionSetAssignment" \
      --method POST \
      --body "{\"AssigneeId\":\"$USER_ID\",\"PermissionSetId\":\"$PS_ID\"}" 2>"$POST_STDERR" || true)

    POST_SUCCESS=$(echo "$POST_RESULT" | jq -r '.success // false' 2>/dev/null || echo "false")

    if [ "$POST_SUCCESS" = "true" ]; then
      PSA_ID=$(echo "$POST_RESULT" | jq -r '.id')
      ASSIGNED_THIS_RUN=$(echo "$ASSIGNED_THIS_RUN" | jq -c \
        --arg uid "$USER_ID" --arg un "$USERNAME" \
        --arg psdn "$PS_DEV_NAME" --arg psaid "$PSA_ID" \
        '. + [{user_id: $uid, username: $un, permission_set_developer_name: $psdn, assignment_id: $psaid}]')
      ASSIGNED_COUNT=$((ASSIGNED_COUNT + 1))
    else
      ERR_CODE=$(echo "$POST_RESULT" | jq -r 'if type == "array" then .[0].errorCode else .errorCode // "UNKNOWN" end' 2>/dev/null || echo "UNKNOWN")
      ERR_MSG=$(echo "$POST_RESULT"  | jq -r 'if type == "array" then .[0].message   else .message   // "Unknown POST error" end' 2>/dev/null || echo "Unknown POST error")

      if [ "$ERR_CODE" = "UNKNOWN" ] && [ -z "$POST_RESULT" ]; then
        ERR_MSG=$(grep -v '^Warning:' "$POST_STDERR" | head -1 || echo "sf CLI produced no output")
      fi

      if [ "$ERR_CODE" = "DUPLICATE_VALUE" ]; then
        # Concurrent race (assigned between detect and POST); treat as reused, don't increment.
        :
      else
        PARTIAL_ERRORS+=("$USERNAME ($USER_ID) → $PS_DEV_NAME: $ERR_CODE - $ERR_MSG")
      fi
    fi
    rm -f "$POST_STDERR"
  done
fi

# Step 6 - Re-query final assignment state
AFTER_PSA_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT AssigneeId, PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId IN ($USER_IDS_IN) AND PermissionSetId IN ($PS_IDS_IN)" \
  --json 2>/dev/null)

AFTER_PAIRS=$(echo "$AFTER_PSA_JSON" | jq -c '[.result.records[] | {user_id: .AssigneeId, permission_set_id: .PermissionSetId}]')
AFTER_COUNT=$(echo "$AFTER_PAIRS" | jq 'length')

# Step 7 - Compute status
REUSED_COUNT=$EXISTING_COUNT

if [ ${#PARTIAL_ERRORS[@]} -gt 0 ] || [ "$AFTER_COUNT" -lt "$EXPECTED_COUNT" ]; then
  STATUS="partial"
  BLOCKING_ISSUE="Partial assign: after re-query, $AFTER_COUNT of $EXPECTED_COUNT expected pairs are present. Failures: ${PARTIAL_ERRORS[*]:-"(none; count mismatch only)"}"
elif [ "$ASSIGNED_COUNT" -eq 0 ]; then
  STATUS="reused"
  BLOCKING_ISSUE=""
else
  STATUS="assigned"
  BLOCKING_ISSUE=""
fi

# Step 8 - Emit report
BLOCKING_JQ_ARG='null'
if [ -n "$BLOCKING_ISSUE" ]; then
  BLOCKING_JQ_ARG=$(jq -n --arg s "$BLOCKING_ISSUE" '$s')
fi

jq -n \
  --arg status "$STATUS" \
  --argjson pss "$PERMISSION_SETS_JSON" \
  --arg suf "$SUFFIX" \
  --argjson count "$COUNT" \
  --argjson expected "$EXPECTED_COUNT" \
  --argjson before_pairs "$EXISTING_PAIRS" \
  --argjson before_count "$EXISTING_COUNT" \
  --argjson assigned "$ASSIGNED_THIS_RUN" \
  --argjson assigned_count "$ASSIGNED_COUNT" \
  --argjson reused_count "$REUSED_COUNT" \
  --argjson after_pairs "$AFTER_PAIRS" \
  --argjson after_count "$AFTER_COUNT" \
  --argjson blocking "$BLOCKING_JQ_ARG" \
  '{
    skill: "service-omni-permission-set-assign",
    status: $status,
    permission_sets: $pss,
    org_suffix: $suf,
    requested_count: $count,
    expected_assignment_count: $expected,
    before: {
      existing_assignment_pairs: $before_pairs,
      existing_count: $before_count
    },
    assigned_this_run: $assigned,
    assigned_count: $assigned_count,
    reused_count: $reused_count,
    after: {
      assignment_pairs: $after_pairs,
      assignment_count: $after_count
    },
    manual_actions: [],
    blocking_issue: $blocking
  }'
