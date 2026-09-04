#!/usr/bin/env bash
# detect-and-create.sh - canonical entry point: chains detect-existing.sh → run-create.sh (plan|run), idempotent, production-guarded. Args, JSON status contract, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 2 ]; then
  echo '{"status":"blocked","blocking_issue":"Missing required args","usage":"bash detect-and-create.sh <plan|run> <org-alias> [count=3] [profile-name=\"Standard User\"]"}' >&2
  exit 1
fi

MODE="$1"
ORG="$2"
COUNT="${3:-3}"
PROFILE_NAME="${4:-Standard User}"

case "$MODE" in
  plan|run) ;;
  *)
    echo "{\"status\":\"blocked\",\"blocking_issue\":\"Invalid mode '$MODE'. Expected 'plan' or 'run'.\"}" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DETECT_SCRIPT="$SCRIPT_DIR/detect-existing.sh"
CREATE_SCRIPT="$SCRIPT_DIR/run-create.sh"

if [ ! -f "$DETECT_SCRIPT" ]; then
  echo "{\"status\":\"blocked\",\"blocking_issue\":\"Sibling script not found: $DETECT_SCRIPT\"}" >&2
  exit 1
fi
if [ "$MODE" = "run" ] && [ ! -f "$CREATE_SCRIPT" ]; then
  echo "{\"status\":\"blocked\",\"blocking_issue\":\"Sibling script not found: $CREATE_SCRIPT\"}" >&2
  exit 1
fi

# Step 1: detect
DETECT_EXIT=0
DETECT_JSON=$(bash "$DETECT_SCRIPT" "$ORG" "$COUNT" "$PROFILE_NAME" 2>&1) || DETECT_EXIT=$?

if [ "$DETECT_EXIT" -ne 0 ]; then
  jq -n --arg raw "$DETECT_JSON" --argjson exit "$DETECT_EXIT" \
    '{status:"blocked",blocking_issue:("detect-existing.sh exited " + ($exit|tostring)),detect_raw:$raw,create:null}'
  exit 1
fi

if ! echo "$DETECT_JSON" | jq -e . >/dev/null 2>&1; then
  jq -n --arg raw "$DETECT_JSON" \
    '{status:"blocked",blocking_issue:"detect-existing.sh produced non-JSON output",detect_raw:$raw,create:null}'
  exit 1
fi

MISSING_COUNT=$(echo "$DETECT_JSON" | jq -r '.missing_count // 0')
SAFE_TO_WRITE=$(echo "$DETECT_JSON" | jq -r '.safe_to_write // false')
PROFILE_ID=$(echo "$DETECT_JSON" | jq -r '.profile_id // ""')
ORG_SUFFIX=$(echo "$DETECT_JSON" | jq -r '.org_suffix // ""')
EXISTING_COUNT=$(echo "$DETECT_JSON" | jq -r '.existing_users | length')
# A deactivated user in a slot is neither reusable nor recreatable (globally-unique username);
# surface it as a manual action so a dead slot never passes as clean.
INACTIVE_COUNT=$(echo "$DETECT_JSON" | jq -r '.inactive_count // 0')
INACTIVE_ACTION=""
if [ "$INACTIVE_COUNT" -gt 0 ]; then
  INACTIVE_ACTION="$INACTIVE_COUNT supervisor slot(s) are occupied by DEACTIVATED users (see inactive_users). Their usernames are globally unique so they cannot be recreated - reactivate them in Setup → Users, or free the usernames, before those slots can be used."
fi

# Step 2: early returns. Nothing missing => "reused" (or action_needed if a dead slot is present).
if [ "$MISSING_COUNT" = "0" ]; then
  if [ "$INACTIVE_COUNT" -gt 0 ]; then
    jq -n \
      --argjson detect "$DETECT_JSON" \
      --argjson reused_count "$EXISTING_COUNT" \
      --arg action "$INACTIVE_ACTION" \
      '{
        status: "action_needed",
        action_required: $action,
        detect: $detect,
        create: null,
        created_count: 0,
        reused_count: $reused_count,
        total_present_after: $reused_count,
        safe_to_write: $detect.safe_to_write
      }'
    exit 0
  fi
  jq -n \
    --argjson detect "$DETECT_JSON" \
    --argjson reused_count "$EXISTING_COUNT" \
    '{
      status: "reused",
      detect: $detect,
      create: null,
      created_count: 0,
      reused_count: $reused_count,
      total_present_after: $reused_count,
      safe_to_write: $detect.safe_to_write
    }'
  exit 0
fi

# --plan mode: never create. Report action_needed with the missing indexes (and any dead slots).
if [ "$MODE" = "plan" ]; then
  jq -n \
    --argjson detect "$DETECT_JSON" \
    --argjson reused_count "$EXISTING_COUNT" \
    --argjson missing_count "$MISSING_COUNT" \
    --arg inactive_action "$INACTIVE_ACTION" \
    '{
      status: "action_needed",
      action_required: (
        "Missing " + ($missing_count|tostring) + " user(s) at indexes " + ($detect.missing_indexes | map(tostring) | join(",")) + ". Re-run in --run mode to create."
        + (if $inactive_action == "" then "" else " ALSO: " + $inactive_action end)
      ),
      detect: $detect,
      create: null,
      created_count: 0,
      reused_count: $reused_count,
      total_present_after: $reused_count,
      safe_to_write: $detect.safe_to_write
    }'
  exit 0
fi

# Step 3: --run mode with missing users - safe_to_write guard, then create.
if [ "$SAFE_TO_WRITE" != "true" ]; then
  jq -n --argjson detect "$DETECT_JSON" \
    '{status:"blocked",blocking_issue:"safe_to_write=false - refusing to create users on a production customer org.",detect:$detect,create:null,created_count:0,reused_count:0,total_present_after:0,safe_to_write:false}'
  exit 1
fi

if [ -z "$PROFILE_ID" ] || [ -z "$ORG_SUFFIX" ]; then
  jq -n --argjson detect "$DETECT_JSON" \
    '{status:"blocked",blocking_issue:"detect-existing.sh did not resolve profile_id or org_suffix - cannot invoke create.",detect:$detect,create:null,created_count:0,reused_count:0,total_present_after:0,safe_to_write:$detect.safe_to_write}'
  exit 1
fi

CREATE_EXIT=0
CREATE_JSON=$(bash "$CREATE_SCRIPT" "$ORG" "$COUNT" "$PROFILE_ID" "$ORG_SUFFIX" 2>&1) || CREATE_EXIT=$?

if [ "$CREATE_EXIT" -ne 0 ]; then
  jq -n --argjson detect "$DETECT_JSON" --arg raw "$CREATE_JSON" --argjson exit "$CREATE_EXIT" \
    '{status:"blocked",blocking_issue:("run-create.sh exited " + ($exit|tostring)),detect:$detect,create:null,create_raw:$raw,created_count:0,reused_count:0,total_present_after:0,safe_to_write:$detect.safe_to_write}'
  exit 1
fi

if ! echo "$CREATE_JSON" | jq -e . >/dev/null 2>&1; then
  jq -n --argjson detect "$DETECT_JSON" --arg raw "$CREATE_JSON" \
    '{status:"blocked",blocking_issue:"run-create.sh produced non-JSON output",detect:$detect,create:null,create_raw:$raw,created_count:0,reused_count:0,total_present_after:0,safe_to_write:$detect.safe_to_write}'
  exit 1
fi

CREATED_COUNT=$(echo "$CREATE_JSON" | jq -r '.created_count // 0')
ROLLED_BACK_COUNT=$(echo "$CREATE_JSON" | jq -r '.rolled_back_users | length')
# A created user without a working password (setPassword failed, non-destructive: stays active +
# reset_required) is not login-ready; any pending reset forces "partial" with a manual action.
PW_RESET_COUNT=$(echo "$CREATE_JSON" | jq -r '(.users_needing_password_reset // []) | length')

# Classify: created (all landed with a password) / partial (some landed, rollbacks, or pending
# password resets) / blocked (nothing landed).
if [ "$CREATED_COUNT" = "0" ]; then
  STATUS="blocked"
elif [ "$ROLLED_BACK_COUNT" -gt 0 ] || [ "$CREATED_COUNT" -lt "$MISSING_COUNT" ] || [ "$PW_RESET_COUNT" -gt 0 ] || [ "$INACTIVE_COUNT" -gt 0 ]; then
  STATUS="partial"
else
  STATUS="created"
fi

jq -n \
  --argjson detect "$DETECT_JSON" \
  --argjson create "$CREATE_JSON" \
  --argjson created_count "$CREATED_COUNT" \
  --argjson reused_count "$EXISTING_COUNT" \
  --argjson pw_reset_count "$PW_RESET_COUNT" \
  --arg inactive_action "$INACTIVE_ACTION" \
  --arg status "$STATUS" \
  '{
    status: $status,
    detect: $detect,
    create: $create,
    created_count: $created_count,
    reused_count: $reused_count,
    total_present_after: ($created_count + $reused_count),
    users_needing_password_reset: ($create.users_needing_password_reset // []),
    action_required: (
      [
        (if $pw_reset_count > 0 then
          ($pw_reset_count | tostring) + " supervisor user(s) were created but could NOT have a password set automatically and cannot log in yet. Manually reset their passwords (Setup → Users → Reset Password, or `sf org open` → user record) before use. See users_needing_password_reset and CREDENTIALS.json."
        else empty end),
        (if $inactive_action == "" then empty else $inactive_action end)
      ] | if length == 0 then null else join(" ") end
    ),
    safe_to_write: $detect.safe_to_write
  }'

case "$STATUS" in
  created|partial) exit 0 ;;
  blocked) exit 1 ;;
esac
