#!/usr/bin/env bash
# run-create.sh - INTERNAL (invoke via detect-and-create.sh, which enforces the safe_to_write guard): render Apex tokens, execute, parse created users; passwords set via separate System.setPassword, never extracted from logs. Contract + security: SKILL.md + references/apex-template-notes.md.

set -euo pipefail

if [ $# -lt 4 ]; then
  echo '{"error":"Usage: bash run-create.sh <org-alias> <count> <profile-id> <org-suffix>"}' >&2
  exit 1
fi

ORG="$1"
COUNT="$2"
PROFILE_ID="$3"
SUFFIX="$4"

# Validate every arg BEFORE it is sed-substituted into anonymous Apex. These tokens are interpolated
# into executable Apex, so anything outside a strict grammar (Apex/sed metacharacters, code) is
# rejected up front rather than executed.
if ! [[ "$COUNT" =~ ^[1-9][0-9]{0,2}$ ]]; then
  echo "{\"error\":\"Invalid count '$COUNT' (expected a positive integer 1-999).\"}" >&2; exit 1
fi
if ! [[ "$PROFILE_ID" =~ ^[A-Za-z0-9]{15}([A-Za-z0-9]{3})?$ ]]; then
  echo "{\"error\":\"Invalid profile-id '$PROFILE_ID' (expected a 15- or 18-char Salesforce Id).\"}" >&2; exit 1
fi
if ! [[ "$SUFFIX" =~ ^[A-Za-z0-9]{1,18}$ ]]; then
  echo "{\"error\":\"Invalid org-suffix '$SUFFIX' (expected 1-18 alphanumeric chars).\"}" >&2; exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/../assets/create-users.apex.template"

if [ ! -f "$TEMPLATE" ]; then
  echo "{\"error\":\"Apex template not found: $TEMPLATE\"}" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
RESOLVED="$WORK/create-users.resolved.apex"

sed -e "s|__COUNT__|${COUNT}|g" \
    -e "s|__PROFILE_ID__|${PROFILE_ID}|g" \
    -e "s|__SUFFIX__|${SUFFIX}|g" \
    "$TEMPLATE" > "$RESOLVED"

# Execute Anonymous Apex. sf apex run --json shapes differ for compile-fail / runtime-fail /
# success / CLI-fail; each is handled below.
APEX_JSON=$(sf apex run --target-org "$ORG" --file "$RESOLVED" --json 2>/dev/null || true)

# Strip C0 control chars: sf embeds an unescaped debug log in .result.logs, which jq>=1.7 rejects.
# This merges the log to one line; the grep below is anchored to tolerate that.
APEX_JSON=$(printf '%s' "$APEX_JSON" | tr -d '\000-\037')

CLI_STATUS=$(echo "$APEX_JSON" | jq -r '.status // 0' 2>/dev/null || echo "0")
COMPILE_SUCCESS=$(echo "$APEX_JSON" | jq -r '.result.compiled // false' 2>/dev/null || echo "false")
EXEC_SUCCESS=$(echo "$APEX_JSON"    | jq -r '.result.success  // false' 2>/dev/null || echo "false")

translate_error() {
  local raw="$1"
  case "$raw" in
    *LICENSE_LIMIT_EXCEEDED*)
      echo "Org has reached its user license limit. Free up a license slot (deactivate unused users in Setup > Users) or request a larger CDO from OrgFarm."
      ;;
    *DUPLICATE_USERNAME*)
      echo "Username collision with another Salesforce org (globally unique constraint). Rare - retry the skill; if it persists, another agent may be concurrently running against the same suffix."
      ;;
    *INVALID_EMAIL_ADDRESS*)
      echo "Salesforce rejected the @example.com email. This should never happen - likely a bug in the skill's Apex template. Escalate."
      ;;
    *INSUFFICIENT_ACCESS*|*NoAccessException*)
      echo "Executing user lacks required permission. Ensure the sf-CLI-authenticated user has System Administrator profile or equivalent."
      ;;
    *INVALID_LOGIN*|*INVALID_SESSION_ID*)
      echo "Salesforce session expired. Re-authenticate: sf org login web -a $ORG -r <my-domain-url>"
      ;;
    *)
      echo "$raw"
      ;;
  esac
}

if [ "$CLI_STATUS" != "0" ]; then
  CLI_ERR=$(echo "$APEX_JSON" | jq -r '.message // "Unknown CLI error"' 2>/dev/null)
  FRIENDLY=$(translate_error "$CLI_ERR")
  echo "{\"error\":\"$FRIENDLY\",\"raw\":$(echo "$CLI_ERR" | jq -R .)}" >&2
  exit 1
fi

if [ "$COMPILE_SUCCESS" != "true" ]; then
  COMPILE_ERR=$(echo "$APEX_JSON" | jq -r '.result.compileProblem // "Unknown compile error"' 2>/dev/null)
  COMPILE_LINE=$(echo "$APEX_JSON" | jq -r '.result.line // "?"' 2>/dev/null)
  echo "{\"error\":\"Apex compile failed at line $COMPILE_LINE: $COMPILE_ERR\"}" >&2
  exit 1
fi

if [ "$EXEC_SUCCESS" != "true" ]; then
  EXEC_ERR=$(echo "$APEX_JSON" | jq -r '.result.exceptionMessage // "Unknown execution error"' 2>/dev/null)
  if [ -z "$EXEC_ERR" ] || [ "$EXEC_ERR" = "Unknown execution error" ] || [ "$EXEC_ERR" = "null" ]; then
    EXEC_ERR=$(echo "$APEX_JSON" | jq -r '.message // "Unknown execution error"' 2>/dev/null)
  fi
  FRIENDLY=$(translate_error "$EXEC_ERR")
  echo "{\"error\":\"$FRIENDLY\",\"raw\":$(echo "$EXEC_ERR" | jq -R .)}" >&2
  exit 1
fi

# Parse AGENT_USER_CREATED|<userId>|<username>|<email> from the log; decode the HTML-encoded pipe
# (&#124;) that sf emits, else the grep misses every user.
LOG=$(echo "$APEX_JSON" | jq -r '.result.logs // ""' 2>/dev/null | sed 's/&#124;/|/g')

# Anchor on a real 005 Id + @example.com domain so the match ignores the Apex source echoed in the merged log.
CREATED_RAW=$(echo "$LOG" | grep -oE 'AGENT_USER_CREATED\|005[a-zA-Z0-9]{15}\|[^|]+@example\.com\|[^|]+@example\.com' || true)

if [ -z "$CREATED_RAW" ]; then
  CREATED_USERS_JSON='[]'
else
  CREATED_USERS_JSON=$(echo "$CREATED_RAW" \
    | awk -F'|' '
        BEGIN { print "[" }
        NR > 1 { printf "," }
        {
          printf "{\"id\":\"%s\",\"username\":\"%s\",\"email\":\"%s\"}", $2, $3, $4
        }
        END { print "]" }
    ')
  if ! echo "$CREATED_USERS_JSON" | jq -c '.' >/dev/null 2>&1; then
    echo "{\"error\":\"Internal parse error: AGENT_USER_CREATED lines produced invalid JSON.\",\"raw_lines\":$(echo "$CREATED_RAW" | jq -Rs .)}" >&2
    exit 1
  fi
  CREATED_USERS_JSON=$(echo "$CREATED_USERS_JSON" | jq -c '.')
fi

# Set each User's password via System.setPassword (the only working path for Apex-inserted users).
# Fail-closed on the TraceFlag gate below; on failure the User stays active + reset_required.
# Full security rationale: references/apex-template-notes.md.
ENRICHED_USERS='[]'
NEEDS_RESET='[]'
ROLLED_BACK='[]'

# Generated passwords are written to a restricted (0600) file and NEVER returned in stdout, so
# plaintext cannot enter an AI/tool transcript when this leaf is invoked directly. The coordinator
# passes OMNI_CREDENTIALS_FILE/OMNI_CREDENTIALS_KEY to escrow into its own file; standalone runs
# default to ./CREDENTIALS.json. File format: { "<key>": [ {username, password}, ... ] }.
# Secrets never touch argv/env (both visible via process inspection): each {username,password} pair is
# appended as one JSON line to this 0600 temp file (inside $WORK, mode 0700) and fed to jq only via
# stdin / --slurpfile. $WORK is removed by the EXIT trap, so the plaintext file never persists.
CRED_PAIRS_FILE="$WORK/cred-pairs.jsonl"
: > "$CRED_PAIRS_FILE"; chmod 600 "$CRED_PAIRS_FILE" 2>/dev/null || true
CRED_COUNT=0
CRED_FILE="${OMNI_CREDENTIALS_FILE:-$PWD/CREDENTIALS.json}"
CRED_KEY="${OMNI_CREDENTIALS_KEY:-service-omni-agent-users-create}"
CRED_WRITTEN="false"
write_credentials() {
  # $1 = path to a JSONL file of {username,password} objects. Secret-bearing pairs are read via
  # --slurpfile (a file, never argv); the existing credentials file is piped in via stdin.
  local pairs_file="$1" existing='{}' tmp
  [ -f "$CRED_FILE" ] && existing=$(cat "$CRED_FILE" 2>/dev/null || echo '{}')
  tmp=$(mktemp) || return 1
  if ! printf '%s' "$existing" | jq --arg k "$CRED_KEY" --slurpfile c "$pairs_file" '. + {($k): $c}' > "$tmp" 2>/dev/null || [ ! -s "$tmp" ]; then
    rm -f "$tmp"; return 1
  fi
  if ! mv "$tmp" "$CRED_FILE" 2>/dev/null; then rm -f "$tmp"; return 1; fi
  chmod 600 "$CRED_FILE" 2>/dev/null || true
  return 0
}

set_password_via_apex() {
  # $1=user_id  $2=plaintext_password. Echoes "ok" on success, else the exception text.
  local uid="$1" pw="$2" apex_file res
  apex_file="$WORK/setpw.apex"
  # uid (18-char Id) and pw ([A-Za-z0-9]) can't break out of the Apex string literal.
  printf "System.setPassword('%s', '%s');\n" "$uid" "$pw" > "$apex_file"
  res=$(sf apex run --target-org "$ORG" --file "$apex_file" --json 2>/dev/null | tr -d '\000-\037' || true)
  rm -f "$apex_file"
  if [ "$(echo "$res" | jq -r '.result.success // false' 2>/dev/null)" = "true" ]; then
    echo "ok"
  else
    echo "$res" | jq -r '.result.exceptionMessage // .message // "setPassword failed"' 2>/dev/null
  fi
}

# TraceFlag gate (fail-closed): prove no active TraceFlag exists for the running user BEFORE any
# System.setPassword, else a password literal could persist to a queryable ApexLog. Cannot prove safe
# => no password set, users left active + reset_required. See references/apex-template-notes.md.
TRACEFLAG_SAFE=false
TRACEFLAG_REASON="TraceFlag state could not be determined"
ME_UNAME=$(sf org display --target-org "$ORG" --json 2>/dev/null | jq -r '.result.username // empty' 2>/dev/null || true)
if [ -z "${ME_UNAME:-}" ]; then
  TRACEFLAG_REASON="could not resolve the running user (sf org display failed)"
else
  ME_UID=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM User WHERE Username='$ME_UNAME' LIMIT 1" \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || true)
  if [ -z "${ME_UID:-}" ]; then
    TRACEFLAG_REASON="could not resolve the running user's Id"
  else
    NOW_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    if TF_JSON=$(sf data query --target-org "$ORG" --use-tooling-api \
        --query "SELECT Id FROM TraceFlag WHERE TracedEntityId='$ME_UID' AND ExpirationDate > $NOW_UTC" \
        --json 2>/dev/null) && [ -n "$TF_JSON" ]; then
      TF_STATUS=$(echo "$TF_JSON" | jq -r '.status // 1' 2>/dev/null || echo 1)
      if [ "$TF_STATUS" = "0" ]; then
        TF_COUNT=$(echo "$TF_JSON" | jq -r 'if (.result.totalSize != null) then .result.totalSize elif (.result.records != null) then (.result.records | length) else "unknown" end' 2>/dev/null || echo "unknown")
        if [ "$TF_COUNT" = "0" ]; then
          TRACEFLAG_SAFE=true
          TRACEFLAG_REASON=""
        elif [ "$TF_COUNT" = "unknown" ]; then
          TRACEFLAG_REASON="the TraceFlag query returned an unparseable result"
        else
          TRACEFLAG_REASON="an active Apex debug TraceFlag exists for the running user ($TF_COUNT found)"
        fi
      else
        TRACEFLAG_REASON="the TraceFlag Tooling API query returned an error status"
      fi
    else
      TRACEFLAG_REASON="the TraceFlag Tooling API query failed"
    fi
  fi
fi

if [ "$(echo "$CREATED_USERS_JSON" | jq -r 'length')" -gt 0 ]; then
  while IFS= read -r row; do
    USER_ID=$(echo "$row" | jq -r '.id')
    UNAME=$(echo "$row" | jq -r '.username')
    EMAIL=$(echo "$row" | jq -r '.email')

    if [ "$TRACEFLAG_SAFE" != "true" ]; then
      # Fail closed: skip setPassword, keep the User active + flag for manual reset.
      NEEDS_RESET=$(echo "$NEEDS_RESET" | jq -c --arg u "$UNAME" '. + [$u]')
      ENRICHED_USERS=$(echo "$ENRICHED_USERS" | jq -c \
        --arg id "$USER_ID" --arg u "$UNAME" --arg e "$EMAIL" \
        '. + [{id: $id, username: $u, email: $e, password: null, password_status: "reset_required", password_error: "skipped: TraceFlag safety could not be proven (fail-closed)"}]')
      continue
    fi

    # Strong [A-Za-z0-9] password + fixed mixed-class suffix (Salesforce complexity). The || true
    # swallows tr's SIGPIPE (head closes the pipe) so pipefail+set -e don't abort mid-insert.
    RAND="$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom 2>/dev/null | head -c 14 || true)"
    PW="${RAND}aB3"
    SETPW_RESULT=$(set_password_via_apex "$USER_ID" "$PW")

    if [ "$SETPW_RESULT" = "ok" ]; then
      # Feed the SECRET via stdin (never argv/env); username is not secret so --arg is fine.
      printf '%s' "$PW" | jq -Rsc --arg u "$UNAME" '{username: $u, password: .}' >> "$CRED_PAIRS_FILE"
      CRED_COUNT=$((CRED_COUNT + 1))
      ENRICHED_USERS=$(echo "$ENRICHED_USERS" | jq -c \
        --arg id "$USER_ID" --arg u "$UNAME" --arg e "$EMAIL" \
        '. + [{id: $id, username: $u, email: $e, password: null, password_status: "generated"}]')
    else
      # Non-destructive: keep the active User, flag it for a manual password reset.
      NEEDS_RESET=$(echo "$NEEDS_RESET" | jq -c --arg u "$UNAME" '. + [$u]')
      ENRICHED_USERS=$(echo "$ENRICHED_USERS" | jq -c \
        --arg id "$USER_ID" --arg u "$UNAME" --arg e "$EMAIL" --arg r "$SETPW_RESULT" \
        '. + [{id: $id, username: $u, email: $e, password: null, password_status: "reset_required", password_error: $r}]')
    fi
  done < <(echo "$CREATED_USERS_JSON" | jq -c '.[]')
fi

# Escrow generated passwords to the restricted file; never emit plaintext in stdout. Fail-closed:
# if escrow fails, the passwords were set on-org but cannot be handed back, so flag those users for a
# manual reset rather than leaking the plaintext.
CRED_WARNING=""
if [ "$CRED_COUNT" -gt 0 ]; then
  if write_credentials "$CRED_PAIRS_FILE"; then
    CRED_WRITTEN="true"
  else
    CRED_WARNING="Passwords were set on the created users but could NOT be escrowed to the credentials file ($CRED_FILE); plaintext was deliberately NOT emitted to stdout. Reset these users' passwords in Setup > Users."
    # Escrow failed → the plaintext is unrecoverable, so these users genuinely need a manual reset:
    # add them to users_needing_password_reset (not just the per-user status) before flipping status.
    ESCROW_FAILED_UNAMES=$(echo "$ENRICHED_USERS" | jq -c '[ .[] | select(.password_status=="generated") | .username ]')
    NEEDS_RESET=$(jq -c -n --argjson a "$NEEDS_RESET" --argjson b "$ESCROW_FAILED_UNAMES" '$a + $b | unique')
    ENRICHED_USERS=$(echo "$ENRICHED_USERS" | jq -c '[ .[] | if .password_status=="generated" then (.password_status="reset_required" | .password_error="escrow_failed") else . end ]')
  fi
fi

# Surface why password generation was skipped when the TraceFlag gate failed.
SECURITY_WARNING=""
if [ "$TRACEFLAG_SAFE" != "true" ]; then
  SECURITY_WARNING="Password generation was SKIPPED (fail-closed) because ${TRACEFLAG_REASON}. No System.setPassword was executed, so no plaintext could enter an ApexLog. The created users are ACTIVE and flagged password_status:\"reset_required\" - set their passwords in Setup > Users after confirming no debug TraceFlag is active, or disable the TraceFlag and re-run."
fi
[ -n "$CRED_WARNING" ] && SECURITY_WARNING="${SECURITY_WARNING:+$SECURITY_WARNING }$CRED_WARNING"

jq -n \
  --argjson created "$ENRICHED_USERS" \
  --argjson needs_reset "$NEEDS_RESET" \
  --argjson rolled_back "$ROLLED_BACK" \
  --arg security_warning "$SECURITY_WARNING" \
  --arg cred_written "$CRED_WRITTEN" \
  --arg cred_file "$CRED_FILE" \
  '{
    created_users: $created,
    created_count: ($created | length),
    users_needing_password_reset: $needs_reset,
    rolled_back_users: $rolled_back,
    credentials_written: ($cred_written == "true"),
    credentials_file: (if $cred_written == "true" then $cred_file else null end),
    security_warning: (if $security_warning == "" then null else $security_warning end),
    security_note: "Passwords are set via anonymous Apex System.setPassword. The plaintext appears in the inline executeAnonymous debug log and, ONLY when a debug-log TraceFlag is active for the running user, in a queryable ApexLog row. To avoid ever persisting plaintext to a log, this script FAILS CLOSED BEFORE the first System.setPassword: it proves via a SOQL-filtered Tooling API query (ExpirationDate > now) that no active TraceFlag exists for the running user. If safety cannot be positively proven - the running user cannot be resolved, the Tooling API query fails or is unparseable, or any active TraceFlag exists - NO password is generated at all; the created users are left ACTIVE and flagged password_status:\"reset_required\", and security_warning explains why. Generated passwords are NEVER returned in this output; they are written to a restricted 0600 credentials_file (default ./CREDENTIALS.json, or OMNI_CREDENTIALS_FILE) so plaintext cannot enter a tool/AI transcript. Read the file once, distribute securely, then delete it. Set passwords for reset_required users in Setup > Users after ensuring no debug TraceFlag is active (or disable the TraceFlag and re-run)."
  }'
