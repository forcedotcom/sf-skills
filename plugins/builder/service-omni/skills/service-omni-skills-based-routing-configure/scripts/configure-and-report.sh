#!/usr/bin/env bash
# configure-and-report.sh - make agents routable via skills-based routing: ensure a Skill and a SkillUser
# binding per agent (the classic Omni-Channel agent-skill model); detect-before-write, idempotent.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo '{"error":"Usage: bash configure-and-report.sh <org-alias> <skill_developer_name> [agent_members_csv] [skill_master_label]"}' >&2
  exit 1
fi

ORG="$1"
SKILL_DN="$2"
AGENTS_CSV="${3:-${AGENT_MEMBERS_CSV:-}}"
SKILL_LABEL_ARG="${4:-}"
API_VERSION="v66.0"

# Skill DeveloperName grammar: leading letter, then letters/digits/underscore, max 80.
if ! [[ "$SKILL_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid skill_developer_name '$SKILL_DN'. Must start with a letter and contain only letters, digits, and underscores (max 80).\"}" >&2
  exit 1
fi

if [ -z "$AGENTS_CSV" ]; then
  echo '{"error":"No agents supplied. Pass agent_members_csv (Usernames and/or 005... User Ids) or set AGENT_MEMBERS_CSV."}' >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Default MasterLabel from DeveloperName (underscores -> spaces) when not supplied.
if [ -n "$SKILL_LABEL_ARG" ]; then
  SKILL_LABEL="$SKILL_LABEL_ARG"
else
  SKILL_LABEL=$(printf '%s' "$SKILL_DN" | tr '_' ' ')
fi

# Escape the five XML predefined entities so a caller-supplied SKILL_LABEL with & < > " ' cannot
# break or inject into the hand-built Skill metadata XML below.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"; s="${s//\'/&apos;}"
  printf '%s' "$s"
}

emit_blocked() {
  local msg="$1"; local target_skill="${2:-}"
  local manual_actions='[]'
  if [ -n "$target_skill" ]; then
    manual_actions=$(jq -n --arg ts "$target_skill" '[{id:"MISSING_PREREQ",title:"Run prerequisite skill",target_skill:$ts}]')
  fi
  jq -n --arg msg "$msg" --arg dn "$SKILL_DN" --argjson ma "$manual_actions" \
    '{skill:"service-omni-skills-based-routing-configure",status:"blocked",
      skill_configured:{developer_name:$dn,id:null,state:"not_created"},
      agents:[],created_counts:{},reused_counts:{},manual_actions:$ma,blocking_issue:$msg}'
  exit 1
}

emit_plan() {
  local status="$1"; local detail="$2"
  jq -n --arg status "$status" --arg detail "$detail" --arg dn "$SKILL_DN" \
    '{skill:"service-omni-skills-based-routing-configure",status:$status,plan_mode:true,
      plan_detail:$detail,skill_configured:{developer_name:$dn},manual_actions:[],blocking_issue:null}'
  exit 0
}

# REST POST helper: echoes the created Id on success, empty on failure. Error detail is written to a
# file because this function is called inside command substitution and shell variables would be lost.
POST_ERR_FILE="$(mktemp)"
trap 'rm -f "$POST_ERR_FILE"' EXIT
post_err() { cat "$POST_ERR_FILE" 2>/dev/null || true; }
rest_post() {
  local sobject="$1"; local body="$2"
  local stderr_f; stderr_f="$(mktemp)"
  local res
  res=$(sf api request rest --target-org "$ORG" \
    "/services/data/$API_VERSION/sobjects/$sobject" --method POST --body "$body" 2>"$stderr_f" || true)
  local ok; ok=$(echo "$res" | jq -r '.success // false' 2>/dev/null || echo false)
  if [ "$ok" = "true" ]; then
    : > "$POST_ERR_FILE"
    echo "$res" | jq -r '.id'
  else
    local code msg
    code=$(echo "$res" | jq -r 'if type=="array" then .[0].errorCode else .errorCode // "UNKNOWN" end' 2>/dev/null || echo UNKNOWN)
    msg=$(echo "$res"  | jq -r 'if type=="array" then .[0].message   else .message   // "" end' 2>/dev/null || echo "")
    if [ -z "$msg" ] || [ "$msg" = "null" ]; then
      msg=$(printf '%s' "$res" | tr '\n' ' ' | head -c 200)
      [ -n "$msg" ] || msg=$(grep -v '^Warning:' "$stderr_f" | head -1)
      [ -n "$msg" ] || msg="no error detail returned by the sf CLI"
    fi
    printf '%s - %s' "$code" "$msg" > "$POST_ERR_FILE"
    echo ""
  fi
  rm -f "$stderr_f"
}

# Step 1 - Organization + safe_to_write guard
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" --json 2>/dev/null) \
  || emit_blocked "Failed to query Organization for the safe_to_write guard."
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')
SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi
[ "$SAFE_TO_WRITE" = "true" ] || emit_blocked "Refusing to configure skills-based routing on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."

# Step 2 - Resolve active agents from the CSV (Usernames and/or 005... Ids)
USERNAME_IN=""; ID_IN=""; BADTOK=""
while IFS= read -r tok; do
  [ -z "$tok" ] && continue
  if [[ "$tok" =~ ^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
    ID_IN="${ID_IN:+$ID_IN,}'$tok'"
  elif [[ "$tok" =~ ^[^,\'\"[:space:]]+@[^,\'\"[:space:]]+$ ]]; then
    USERNAME_IN="${USERNAME_IN:+$USERNAME_IN,}'$tok'"
  else
    BADTOK="$BADTOK '$tok'"
  fi
done <<< "$(printf '%s' "$AGENTS_CSV" | tr ',' '\n' | sed 's/^ *//;s/ *$//')"
[ -z "$BADTOK" ] || emit_blocked "agent_members_csv contains token(s) that are neither a Username (...@...) nor a 15/18-char User Id (005...):$BADTOK"

WHERE_PARTS=""
[ -n "$USERNAME_IN" ] && WHERE_PARTS="Username IN ($USERNAME_IN)"
[ -n "$ID_IN" ] && WHERE_PARTS="${WHERE_PARTS:+$WHERE_PARTS OR }Id IN ($ID_IN)"

# Fail-closed with structured JSON: without `|| emit_blocked`, a non-zero query makes the command
# substitution fail and set -e would exit before any blocked output. The jq -e guard separates a real
# zero-result from an inconclusive/unparseable read so the two get distinct remediation.
U_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, Username, Name FROM User WHERE ($WHERE_PARTS) AND IsActive=true" --json 2>/dev/null) \
  || emit_blocked "Could not query User to resolve agent_members_csv (query failed: authentication, network, or API access). Re-run with a reachable org." "service-omni-agent-users-create"
echo "$U_JSON" | jq -e '.result.totalSize | numbers' >/dev/null 2>&1 \
  || emit_blocked "User resolution returned no parseable result (inconclusive). Re-run against a reachable org." "service-omni-agent-users-create"
U_COUNT=$(echo "$U_JSON" | jq -r '.result.totalSize')
[ "$U_COUNT" -gt 0 ] || emit_blocked "No ACTIVE users resolved from agent_members_csv. Verify the usernames/IDs are correct and the users are active." "service-omni-agent-users-create"

USERS_JSON=$(echo "$U_JSON" | jq -c '[.result.records[] | {id:.Id, username:.Username, name:.Name}]')
USER_IDS_IN=$(echo "$USERS_JSON" | jq -r '[.[].id] | map("'"'"'" + . + "'"'"'") | join(",")')

# Step 3 - Ensure the Skill exists (reuse sObject; else deploy Skill metadata, then re-query)
skill_id_by_name() {
  sf data query --target-org "$ORG" --json \
    --query "SELECT Id FROM Skill WHERE DeveloperName='$SKILL_DN'" 2>/dev/null \
    | jq -r '.result.records[0].Id // ""' 2>/dev/null
}
SKILL_ID=$(skill_id_by_name)
SKILL_STATE="reused"

# PLAN_ONLY - report intent from read-only detection and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ -n "$SKILL_ID" ]; then
    emit_plan "action_needed" "Skill '$SKILL_DN' exists; would ensure a SkillUser binding for $U_COUNT active agent(s)."
  else
    emit_plan "action_needed" "Would deploy Skill '$SKILL_DN' and ensure a SkillUser binding for $U_COUNT active agent(s)."
  fi
fi

if [ -z "$SKILL_ID" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  WORK="$(mktemp -d)"; trap 'rm -rf "$WORK" "$POST_ERR_FILE"' EXIT
  cp "$SCRIPT_DIR/../assets/sfdx-project.json" "$WORK/sfdx-project.json" 2>/dev/null \
    || echo '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}' > "$WORK/sfdx-project.json"
  SKILL_DIR="$WORK/force-app/main/default/skills"; mkdir -p "$SKILL_DIR"
  cat > "$SKILL_DIR/${SKILL_DN}.skill-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<Skill xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Created by service-omni-skills-based-routing-configure.</description>
    <label>$(xml_escape "$SKILL_LABEL")</label>
</Skill>
XML
  DEP_JSON=$(cd "$WORK" && sf project deploy start --target-org "$ORG" \
    --metadata "Skill:${SKILL_DN}" --json 2>/dev/null || true)
  DEP_OK=$(echo "$DEP_JSON" | jq -r '.result.success // false' 2>/dev/null || echo false)
  if [ "$DEP_OK" != "true" ]; then
    FAIL=$(echo "$DEP_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
    [ -n "$FAIL" ] && [ "$FAIL" != "null" ] || FAIL=$(echo "$DEP_JSON" | jq -r '.message // "Unknown deploy error"' 2>/dev/null)
    emit_blocked "Failed to deploy Skill '$SKILL_DN': $FAIL. Ensure skills-based routing is enabled in Omni-Channel settings." "service-omni-base-settings-configure"
  fi
  SKILL_ID=$(skill_id_by_name)
  SKILL_STATE="created"
  [ -n "$SKILL_ID" ] || emit_blocked "Deployed Skill '$SKILL_DN' but could not re-query its Id (org may still be indexing). Re-run to bind agents."
fi

# Step 4 - Ensure a SkillUser binding (SkillId, UserId) per active agent. This is the classic
# Omni-Channel agent-skill model used by Setup > Skills > Assign Users. ServiceResourceSkill is a
# Field Service model and cannot be used on a plain Service Cloud org where ServiceResource.IsActive
# is unavailable.
SU_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT Id, UserId FROM SkillUser WHERE SkillId='$SKILL_ID' AND UserId IN ($USER_IDS_IN)" 2>/dev/null || echo '{}')
EXISTING_SU=$(echo "$SU_JSON" | jq -c '[.result.records[]? | {user_id:.UserId, su_id:.Id}]' 2>/dev/null || echo '[]')

AGENTS_OUT='[]'
BIND_CREATED=0; BIND_REUSED=0
PARTIAL_ERRORS=()

# For each agent: ensure a SkillUser binding.
while IFS= read -r row; do
  [ -z "$row" ] && continue
  USR_ID=$(echo "$row" | jq -r '.id')
  UNAME=$(echo "$row" | jq -r '.username')

  SU_ID=$(echo "$EXISTING_SU" | jq -r --arg u "$USR_ID" '.[] | select(.user_id==$u) | .su_id' | head -1)
  BIND_STATE="reused"
  if [ -z "$SU_ID" ] || [ "$SU_ID" = "null" ]; then
    SU_ID=$(rest_post "SkillUser" "{\"SkillId\":\"$SKILL_ID\",\"UserId\":\"$USR_ID\"}")
    if [ -z "$SU_ID" ]; then
      ERR=$(post_err)
      if printf '%s' "$ERR" | grep -q "DUPLICATE_VALUE"; then
        BIND_STATE="reused"; BIND_REUSED=$((BIND_REUSED+1))
        SU_ID=""
      else
        PARTIAL_ERRORS+=("$UNAME: skill binding failed - $ERR")
        BIND_STATE="not_created"
      fi
    else
      BIND_STATE="created"; BIND_CREATED=$((BIND_CREATED+1))
    fi
  else
    BIND_REUSED=$((BIND_REUSED+1))
  fi

  SU_JQ='null'; [ -n "$SU_ID" ] && [ "$SU_ID" != "null" ] && SU_JQ=$(jq -n --arg s "$SU_ID" '$s')
  AGENTS_OUT=$(echo "$AGENTS_OUT" | jq -c \
    --arg u "$UNAME" --arg uid "$USR_ID" --argjson su "$SU_JQ" --arg bs "$BIND_STATE" \
    '. + [{username:$u,user_id:$uid,skill_binding_id:$su,skill_binding_state:$bs}]')
done < <(echo "$USERS_JSON" | jq -c '.[]')

# Step 5 - Status + report
if [ ${#PARTIAL_ERRORS[@]} -gt 0 ]; then
  # Any success at all → partial; nothing succeeded → blocked.
  if [ "$BIND_CREATED" -gt 0 ] || [ "$BIND_REUSED" -gt 0 ]; then
    STATUS="partial"
  else
    STATUS="blocked"
  fi
  BLOCKING="Partial skills-based-routing configuration. Failures: ${PARTIAL_ERRORS[*]}"
elif [ "$BIND_CREATED" -eq 0 ] && [ "$SKILL_STATE" = "reused" ]; then
  STATUS="reused"; BLOCKING=""
else
  STATUS="configured"; BLOCKING=""
fi

BLOCKING_JQ='null'
[ -n "$BLOCKING" ] && BLOCKING_JQ=$(jq -n --arg s "$BLOCKING" '$s')

jq -n \
  --arg status "$STATUS" \
  --arg dn "$SKILL_DN" \
  --arg sid "$SKILL_ID" \
  --arg sstate "$SKILL_STATE" \
  --argjson agents "$AGENTS_OUT" \
  --argjson bind_created "$BIND_CREATED" \
  --argjson bind_reused "$BIND_REUSED" \
  --argjson blocking "$BLOCKING_JQ" \
  '{
    skill: "service-omni-skills-based-routing-configure",
    status: $status,
    skill_configured: {developer_name:$dn, id:$sid, state:$sstate},
    agents: $agents,
    created_counts: {skill_bindings:$bind_created},
    reused_counts:  {skill_bindings:$bind_reused},
    manual_actions: [],
    blocking_issue: $blocking
  }'
