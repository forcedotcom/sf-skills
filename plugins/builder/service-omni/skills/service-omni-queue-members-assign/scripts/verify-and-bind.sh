#!/usr/bin/env bash
# verify-and-bind.sh - bind agent users into a Queue via GroupMember POSTs (explicit usernames/IDs or the generated demo pattern); idempotent, non-destructive (never removes members). Args, output contract, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash verify-and-bind.sh <org-alias> [<queue-developer-name>] [<count>] [<explicit-members-csv>]"}' >&2
  exit 1
fi

ORG="$1"
QUEUE_DN="${2:-CaseQueue}"
COUNT="${3:-3}"
API_VERSION="v66.0"
USERNAME_PREFIX="agent"
USERNAME_DOMAIN="example.com"

# Explicit real-agent members: 4th positional, or env (IDs take precedence over usernames).
EXPLICIT_MEMBERS_CSV="${4:-${MEMBER_USER_IDS_CSV:-${MEMBER_USERNAMES_CSV:-}}}"
EXPLICIT_MODE="false"
if [ -n "$EXPLICIT_MEMBERS_CSV" ]; then
  EXPLICIT_MODE="true"
  # Derive COUNT from the explicit list length (trim blanks) - it overrides the positional count.
  COUNT=$(printf '%s' "$EXPLICIT_MEMBERS_CSV" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -c . || true)
fi

# Sanity: count must be integer 1..10
if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [ "$COUNT" -lt 1 ] || [ "$COUNT" -gt 10 ]; then
  echo "{\"error\":\"Invalid count '$COUNT' - must be integer 1..10${EXPLICIT_MODE:+ (derived from explicit-members-csv)}\"}" >&2
  exit 1
fi

# QUEUE_DN is interpolated into SOQL, so validate its DeveloperName shape before any sf call.
if ! [[ "$QUEUE_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid queue_developer_name '$QUEUE_DN'. Must start with a letter and contain only letters, digits, and underscores (max 80 chars).\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Helper: emit blocked JSON and exit 1
emit_blocked() {
  local msg="$1"
  local click_path="${2:-}"
  local queue_id="${3:-null}"
  local suffix="${4:-}"

  local manual_actions='[]'
  if [ -n "$click_path" ]; then
    manual_actions=$(jq -n --arg cp "$click_path" '[{id: "MANUAL_FIX", title: "Manual fix required", click_path: $cp}]')
  fi

  jq -n \
    --arg msg "$msg" \
    --arg dn "$QUEUE_DN" \
    --arg qid "$queue_id" \
    --arg suf "$suffix" \
    --argjson count "$COUNT" \
    --argjson ma "$manual_actions" \
    '{
      skill: "service-omni-queue-members-assign",
      status: "blocked",
      queue: {
        developer_name: $dn,
        id: (if $qid == "null" then null else $qid end)
      },
      org_suffix: (if $suf == "" then null else $suf end),
      requested_count: $count,
      before: null,
      bound_this_run: [],
      bound_count: 0,
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
    --arg dn "$QUEUE_DN" \
    '{
      skill: "service-omni-queue-members-assign",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      queue: {developer_name: $dn},
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Step 1 - Organization + safe_to_write
# Fail-closed with structured JSON: without the `|| emit_blocked`, an auth/network/API failure makes
# the command substitution non-zero and `set -e` would kill the script before any blocked JSON is
# emitted. The jq -e guard covers a zero-exit-but-empty/unparseable response for the same reason.
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) \
  || emit_blocked "Could not query the Organization object (authentication, network, or API access failed). Re-run with a valid, reachable org connection." "" "null" ""
echo "$ORG_JSON" | jq -e '.result.records[0].Id' >/dev/null 2>&1 \
  || emit_blocked "Organization query returned no parseable record (inconclusive). Refusing to proceed without confirming the org is safe to write." "" "null" ""

ORG_ID=$(echo "$ORG_JSON"    | jq -r '.result.records[0].Id')
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ]; then
  SAFE_TO_WRITE=true
elif [ "$TRIAL_EXP" != "null" ]; then
  SAFE_TO_WRITE=true
elif [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

# Canonical org suffix: chars 10-17 of the 18-char Org Id, lowercased. Uses the SAME expression as the
# user-create leaves' detect-existing.sh so the generated agent/supervisor usernames match exactly.
SUFFIX=$(echo -n "${ORG_ID:10:8}" | tr '[:upper:]' '[:lower:]')

if [ "$SAFE_TO_WRITE" != "true" ]; then
  emit_blocked "Refusing to bind queue members on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org." "" "null" "$SUFFIX"
fi

# Step 2 - Locate the Queue
Q_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id FROM Group WHERE DeveloperName='$QUEUE_DN' AND Type='Queue'" \
  --json 2>/dev/null)

Q_COUNT=$(echo "$Q_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
if [ "$Q_COUNT" -eq 0 ]; then
  emit_blocked \
    "Queue '$QUEUE_DN' does not exist on org. Run service-omni-queue-deploy first, or create manually via the click-path." \
    "Setup → Queues → New → Label: '$QUEUE_DN', DeveloperName: '$QUEUE_DN', Supported Objects: Case → Save" \
    "null" "$SUFFIX"
fi

QUEUE_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].Id')

# Step 3 - Locate the users to bind (generated demo pattern OR explicit real agents)
if [ "$EXPLICIT_MODE" = "true" ]; then
  # Explicit real agents: each token is a Username (...@...) or a 15/18-char User Id (005...).
  USERNAME_IN=""
  ID_IN=""
  BADTOK=""
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    if [[ "$tok" =~ ^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
      ID_IN="${ID_IN:+$ID_IN,}'$tok'"
    elif [[ "$tok" =~ ^[^,\'\"[:space:]]+@[^,\'\"[:space:]]+$ ]]; then
      USERNAME_IN="${USERNAME_IN:+$USERNAME_IN,}'$tok'"
    else
      BADTOK="$BADTOK '$tok'"
    fi
  done <<< "$(printf '%s' "$EXPLICIT_MEMBERS_CSV" | tr ',' '\n' | sed 's/^ *//;s/ *$//')"

  if [ -n "$BADTOK" ]; then
    emit_blocked "explicit-members-csv contains token(s) that are neither a Username (...@...) nor a 15/18-char User Id (005...):$BADTOK" "" "$QUEUE_ID" "$SUFFIX"
  fi

  # Build the WHERE predicate from whichever token kinds were supplied.
  WHERE_PARTS=""
  [ -n "$USERNAME_IN" ] && WHERE_PARTS="Username IN ($USERNAME_IN)"
  [ -n "$ID_IN" ] && WHERE_PARTS="${WHERE_PARTS:+$WHERE_PARTS OR }Id IN ($ID_IN)"

  U_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id, Username FROM User WHERE ($WHERE_PARTS) AND IsActive=true" \
    --json 2>/dev/null)

  U_COUNT=$(echo "$U_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
  if [ "$U_COUNT" -lt "$COUNT" ]; then
    FOUND=$(echo "$U_JSON" | jq -c '[.result.records[].Username]')
    emit_blocked \
      "Expected $COUNT ACTIVE user(s) from the explicit list; resolved only $U_COUNT active ($FOUND). Check the usernames/IDs are correct and the users are active." \
      "" "$QUEUE_ID" "$SUFFIX"
  fi
else
  # Demo pattern: agent1..N.<suffix>@example.com
  EXPECTED_USERNAMES=()
  for i in $(seq 1 "$COUNT"); do
    EXPECTED_USERNAMES+=("${USERNAME_PREFIX}${i}.${SUFFIX}@${USERNAME_DOMAIN}")
  done

  # Build SOQL IN clause: 'un1','un2',...
  IN_CLAUSE=""
  for un in "${EXPECTED_USERNAMES[@]}"; do
    if [ -n "$IN_CLAUSE" ]; then IN_CLAUSE="$IN_CLAUSE,"; fi
    IN_CLAUSE="$IN_CLAUSE'$un'"
  done

  # Only active users can be routed work; filter IsActive=true so an inactive occupant can't satisfy the count.
  U_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id, Username FROM User WHERE Username IN ($IN_CLAUSE) AND IsActive=true" \
    --json 2>/dev/null)

  U_COUNT=$(echo "$U_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
  if [ "$U_COUNT" -lt "$COUNT" ]; then
    FOUND=$(echo "$U_JSON" | jq -c '[.result.records[].Username]')
    emit_blocked \
      "Expected $COUNT ACTIVE agent users matching pattern 'agent{1..$COUNT}.$SUFFIX@example.com'; found $U_COUNT active ($FOUND). Run service-omni-agent-users-create with count=$COUNT first (and reactivate any deactivated agent users)." \
      "" "$QUEUE_ID" "$SUFFIX"
  fi
fi

# Map username → userId, and build user Id array for downstream queries
USERS_JSON=$(echo "$U_JSON" | jq -c '[.result.records[] | {id: .Id, username: .Username}]')
USER_IDS_ARR=$(echo "$USERS_JSON" | jq -c '[.[].id]')

# Build SOQL IN clause for user IDs
USER_IDS_IN=""
for uid in $(echo "$USER_IDS_ARR" | jq -r '.[]'); do
  if [ -n "$USER_IDS_IN" ]; then USER_IDS_IN="$USER_IDS_IN,"; fi
  USER_IDS_IN="$USER_IDS_IN'$uid'"
done

# Step 4 - Query existing GroupMember rows for this queue + these users
GM_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, UserOrGroupId FROM GroupMember WHERE GroupId='$QUEUE_ID' AND UserOrGroupId IN ($USER_IDS_IN)" \
  --json 2>/dev/null)

EXISTING_USER_IDS=$(echo "$GM_JSON" | jq -c '[.result.records[].UserOrGroupId]')
EXISTING_COUNT=$(echo "$EXISTING_USER_IDS" | jq 'length')

# Compute missing = expected - existing
MISSING_USERS=$(echo "$USERS_JSON" | jq -c --argjson existing "$EXISTING_USER_IDS" \
  '[.[] | select(.id as $id | ($existing | index($id)) == null)]')
MISSING_COUNT=$(echo "$MISSING_USERS" | jq 'length')

# PLAN_ONLY: all detection above is read-only. Report what a --run would do and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ "$MISSING_COUNT" -eq 0 ]; then
    emit_plan "reused" "All $COUNT agent user(s) already members of queue '$QUEUE_DN'."
  else
    emit_plan "action_needed" "Would bind $MISSING_COUNT missing of $COUNT agent user(s) into queue '$QUEUE_DN'."
  fi
fi

# Step 5 - POST GroupMember for each missing user
BOUND_THIS_RUN='[]'
BOUND_COUNT=0
PARTIAL_ERRORS=()

if [ "$MISSING_COUNT" -gt 0 ]; then
  for row in $(echo "$MISSING_USERS" | jq -c '.[]'); do
    USER_ID=$(echo "$row" | jq -r '.id')
    USERNAME=$(echo "$row" | jq -r '.username')

    # sf api request rest (beta) writes a warning to stderr; redirect it so stdout is pure JSON.
    POST_STDERR="$(mktemp)"
    POST_RESULT=$(sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/GroupMember" \
      --method POST \
      --body "{\"GroupId\":\"$QUEUE_ID\",\"UserOrGroupId\":\"$USER_ID\"}" 2>"$POST_STDERR" || true)

    # Success = {id, success:true, errors:[]}; error = array of {errorCode, message} or single obj
    POST_SUCCESS=$(echo "$POST_RESULT" | jq -r '.success // false' 2>/dev/null || echo "false")

    if [ "$POST_SUCCESS" = "true" ]; then
      GM_ID=$(echo "$POST_RESULT" | jq -r '.id')
      # GroupMember dedupes server-side (a duplicate POST returns success with the existing Id), so
      # the detect step above is what prevents inflated bound_count; any success here is a new bind.
      BOUND_THIS_RUN=$(echo "$BOUND_THIS_RUN" | jq -c \
        --arg uid "$USER_ID" --arg un "$USERNAME" --arg gmid "$GM_ID" \
        '. + [{user_id: $uid, username: $un, group_member_id: $gmid}]')
      BOUND_COUNT=$((BOUND_COUNT + 1))
    else
      # Try to extract error code + message
      ERR_CODE=$(echo "$POST_RESULT" | jq -r 'if type == "array" then .[0].errorCode else .errorCode // "UNKNOWN" end' 2>/dev/null || echo "UNKNOWN")
      ERR_MSG=$(echo "$POST_RESULT" | jq -r 'if type == "array" then .[0].message else .message // "Unknown POST error" end' 2>/dev/null || echo "Unknown POST error")

      # Fallback: if POST_RESULT was empty (CLI-level failure), pull first non-Warning stderr line
      if [ "$ERR_CODE" = "UNKNOWN" ] && [ -z "$POST_RESULT" ]; then
        ERR_MSG=$(grep -v '^Warning:' "$POST_STDERR" | head -1 || echo "sf CLI produced no output")
      fi

      if [ "$ERR_CODE" = "DUPLICATE_VALUE" ]; then
        # Safety net for a concurrent re-POST; detect-before-POST already prevents duplicate binds.
        :
      else
        PARTIAL_ERRORS+=("$USERNAME ($USER_ID): $ERR_CODE - $ERR_MSG")
      fi
    fi
    rm -f "$POST_STDERR"
  done
fi

# Step 6 - Re-query final membership
AFTER_GM_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT UserOrGroupId FROM GroupMember WHERE GroupId='$QUEUE_ID' AND UserOrGroupId IN ($USER_IDS_IN)" \
  --json 2>/dev/null)

AFTER_USER_IDS=$(echo "$AFTER_GM_JSON" | jq -c '[.result.records[].UserOrGroupId]')
AFTER_COUNT=$(echo "$AFTER_USER_IDS" | jq 'length')

# Step 7 - Compute status
REUSED_COUNT=$EXISTING_COUNT

if [ ${#PARTIAL_ERRORS[@]} -gt 0 ] || [ "$AFTER_COUNT" -lt "$COUNT" ]; then
  STATUS="partial"
  # Assemble blocking_issue string
  BLOCKING_ISSUE="Partial bind: after re-query, $AFTER_COUNT of $COUNT expected users are members. Failures: ${PARTIAL_ERRORS[*]:-"(none; count mismatch only)"}"
elif [ "$BOUND_COUNT" -eq 0 ]; then
  STATUS="reused"
  BLOCKING_ISSUE=""
else
  STATUS="bound"
  BLOCKING_ISSUE=""
fi

# Step 8 - Emit report
BLOCKING_JQ_ARG='null'
if [ -n "$BLOCKING_ISSUE" ]; then
  BLOCKING_JQ_ARG=$(jq -n --arg s "$BLOCKING_ISSUE" '$s')
fi

jq -n \
  --arg status "$STATUS" \
  --arg dn "$QUEUE_DN" \
  --arg qid "$QUEUE_ID" \
  --arg suf "$SUFFIX" \
  --argjson count "$COUNT" \
  --argjson before_ids "$EXISTING_USER_IDS" \
  --argjson before_count "$EXISTING_COUNT" \
  --argjson bound "$BOUND_THIS_RUN" \
  --argjson bound_count "$BOUND_COUNT" \
  --argjson reused_count "$REUSED_COUNT" \
  --argjson after_ids "$AFTER_USER_IDS" \
  --argjson after_count "$AFTER_COUNT" \
  --argjson blocking "$BLOCKING_JQ_ARG" \
  --arg member_source "$([ "$EXPLICIT_MODE" = "true" ] && echo explicit || echo generated_pattern)" \
  '{
    skill: "service-omni-queue-members-assign",
    status: $status,
    queue: {developer_name: $dn, id: $qid},
    org_suffix: $suf,
    member_source: $member_source,
    requested_count: $count,
    before: {
      existing_member_user_ids: $before_ids,
      existing_member_count: $before_count
    },
    bound_this_run: $bound,
    bound_count: $bound_count,
    reused_count: $reused_count,
    after: {
      member_user_ids: $after_ids,
      member_count: $after_count
    },
    manual_actions: [],
    blocking_issue: $blocking
  }'
