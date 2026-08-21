#!/usr/bin/env bash
#
# get_signup_request.sh — Read back a SignupRequest to pick up the assigned
# trial org id, applying a fixed polling policy, and (optionally) write the
# record as the skill's output artifact.
#
# Trial-org provisioning is asynchronous: the insert only returns the 0SR
# handle, while CreatedOrgId / Status populate shortly after. This script
# encapsulates the deterministic policy so every invocation behaves the same:
#   - read the record;
#   - stop as soon as CreatedOrgId is populated (this typically happens while
#     Status is still InProgress — the caller need not wait for Success);
#   - otherwise re-read up to --max-attempts times TOTAL, sleeping --delay
#     seconds between reads, then return the current state (no infinite loop);
#   - stop immediately on a terminal Status (Success or Error) or a CLI error.
#
# It always prints the resolved record (its `result` object) as JSON on stdout.
# With --output-dir it also writes that JSON to <dir>/signup-request-result.json.
#
# Auth is handled by the `sf` CLI (the access token never surfaces here).
#
# Usage:
#   get_signup_request.sh --target-org <org> --id <0SR...> [--output-dir <dir>]
#   get_signup_request.sh --target-org <org> --id <0SR...> --max-attempts 3 --delay 20
#
# Options:
#   --target-org, -o <org>  REQUIRED. Host org alias or username.
#   --id, -i <0SR...>       REQUIRED. SignupRequest id to read.
#   --output-dir <dir>      Write the record JSON to <dir>/signup-request-result.json.
#   --max-attempts <n>      TOTAL reads before giving up on an empty CreatedOrgId
#                           (1 to 3; default 3). Provisioning is async, so we do
#                           not poll indefinitely: at most three lookups, then
#                           hand back the request id (exit 3) for the user to
#                           re-check.
#   --delay <seconds>       Sleep between reads (default 20).
#   --help, -h              Show this help.
#
# Output:
#   The SignupRequest record (the `sf` envelope's `result`) as JSON on stdout.
#
# Exit codes:
#   0  CreatedOrgId populated (org allocated) — the only exit that carries an org id
#   1  Status=Error, or the record could not be read (auth / id not found)
#   2  bad usage or missing dependency (sf or jq)
#   3  no org id available — record read but CreatedOrgId still empty (still
#      provisioning after --max-attempts, or a terminal status with no id).
#      Not an error. The caller reports the 0SR id and the record's REAL Status,
#      and tells the user to re-check later. The exit code never reflects a
#      synthesized status — only what is actually on the record.

set -uo pipefail

die() { echo "Error: $*" >&2; exit 2; }

command -v sf >/dev/null 2>&1 || die "Salesforce CLI ('sf') not found on PATH."
command -v jq >/dev/null 2>&1 || die "'jq' not found on PATH."

TARGET_ORG=""
SR_ID=""
OUTPUT_DIR=""
MAX_ATTEMPTS=3
DELAY=20

usage() { sed -n '2,/^set -uo/p' "$0" | sed '/^set -uo/d; s/^# \{0,1\}//; s/^#//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target-org|-o) TARGET_ORG="${2:-}"; shift 2 ;;
    --id|-i)         SR_ID="${2:-}"; shift 2 ;;
    --output-dir)    OUTPUT_DIR="${2:-}"; shift 2 ;;
    --max-attempts)  MAX_ATTEMPTS="${2:-}"; shift 2 ;;
    --delay)         DELAY="${2:-}"; shift 2 ;;
    --help|-h)       usage; exit 0 ;;
    *)               die "Unknown argument: $1" ;;
  esac
done

[ -n "$TARGET_ORG" ] || die "--target-org is required."
[ -n "$SR_ID" ]      || die "--id is required (the 0SR... SignupRequest id)."
case "$MAX_ATTEMPTS" in 1|2|3) ;; *) die "--max-attempts must be 1, 2, or 3 (provisioning is async; we do not poll more than three times)." ;; esac
case "$DELAY" in ''|*[!0-9]*) die "--delay must be a non-negative integer." ;; esac

# read the record once; sets RESULT (the `result` object) and RECORD_STATUS,
# or returns non-zero on a CLI error (RESULT holds the raw error envelope).
read_record() {
  local resp env_status
  resp="$(sf data get record --target-org "$TARGET_ORG" --sobject SignupRequest \
    --record-id "$SR_ID" --json 2>/dev/null)"
  env_status="$(printf '%s' "$resp" | jq -r '.status // 1' 2>/dev/null)"
  if [ "$env_status" != "0" ]; then
    printf '%s' "$resp" | jq -r '"\(.name // .code // "ERROR"): \(.message // "unknown error")"' >&2
    return 1
  fi
  RESULT="$(printf '%s' "$resp" | jq '.result')"
  RECORD_STATUS="$(printf '%s' "$RESULT" | jq -r '.Status // ""' | tr '[:upper:]' '[:lower:]')"
  CREATED_ORG_ID="$(printf '%s' "$RESULT" | jq -r '.CreatedOrgId // ""')"
  return 0
}

RESULT=""
RECORD_STATUS=""
CREATED_ORG_ID=""
FINAL_RC=0

# At most MAX_ATTEMPTS total reads (1 to 3). Provisioning is async, so if the
# org id has not appeared by the final read we stop and hand back the request
# id rather than polling on — the caller reports 0SR and asks the user to
# re-check later (exit 3).
attempt=0
while : ; do
  if ! read_record; then
    exit 1
  fi
  attempt=$((attempt + 1))
  # Stop as soon as the org is allocated, or on a terminal status. Success and
  # Error are both terminal — there is nothing to gain by re-reading either, so
  # neither consumes the retry budget. The exit code is driven by what is
  # actually on the record, never by a synthesized value:
  #   - CreatedOrgId present            -> 0 (org allocated; caller shares the id)
  #   - Status=Error                    -> 1 (provisioning failed)
  #   - terminal but no id (e.g. odd
  #     Success with empty CreatedOrgId) -> 3 (no id to give; report real Status)
  if [ -n "$CREATED_ORG_ID" ]; then
    FINAL_RC=0
    break
  fi
  if [ "$RECORD_STATUS" = "error" ]; then
    FINAL_RC=1
    break
  fi
  if [ "$RECORD_STATUS" = "success" ]; then
    # Terminal, but the org id never populated — stop (nothing to re-read) and
    # hand back the request id with the record's real Status.
    FINAL_RC=3
    break
  fi
  # CreatedOrgId still empty and status not yet terminal. Give up once we've
  # used our lookup budget.
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    FINAL_RC=3
    break
  fi
  sleep "$DELAY"
done

# Always emit the record as JSON on stdout.
printf '%s\n' "$RESULT"

# Defined output artifact: write the record when an output dir is given.
if [ -n "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_DIR"
  printf '%s\n' "$RESULT" > "$OUTPUT_DIR/signup-request-result.json"
fi

exit "$FINAL_RC"
