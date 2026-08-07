#!/usr/bin/env bash
# Deterministically verify the result of a pipeline operation by checking the
# command's JSON status and the relevant post-state fields from `pipeline get`.
# Usage:
#   scripts/verify-operation.sh status <json-file-or-'-'>
#       -> assert the captured CLI JSON has .status == 0
#   scripts/verify-operation.sh active <pipeline-id> <true|false> [target-org]
#       -> assert .result.isActive matches the expected boolean
#   scripts/verify-operation.sh has-stage <pipeline-id> <stage-name> [target-org]
#       -> assert a stage with that name exists in the chain
#   scripts/verify-operation.sh has-project <pipeline-id> <project-name> [target-org]
#       -> assert a connected project with that name exists
# Exits 0 when the assertion holds; prints an actionable error and exits 1 otherwise.

set -euo pipefail

MODE="${1:?Usage: verify-operation.sh <status|active|has-stage|has-project> ...}"

# Read a pipeline once and hand back validated JSON on stdout. Distinguishes a
# failed CLI read / non-zero JSON status from a successful read (whose fields the
# caller then evaluates), so post-state checks never mistake a read failure for a
# "not found" result. Exits 2 with an actionable message on any read/JSON error.
GET_JSON=""
read_pipeline() {
  local pid="$1" org="$2"
  local flag=() err rc
  [ -n "$org" ] && flag=(--target-org "$org")
  # Capture stdout and stderr separately; do not let pipefail abort silently.
  err=$(mktemp)
  rc=0
  GET_JSON=$(sf devops pipeline get --pipeline-id "$pid" "${flag[@]+"${flag[@]}"}" --json 2>"$err") || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: could not read pipeline '$pid' (sf exited $rc): $(tr '\n' ' ' <"$err")" >&2
    rm -f "$err"; exit 2
  fi
  rm -f "$err"
  local st
  st=$(echo "$GET_JSON" | jq -r '.status // 1' 2>/dev/null || echo 1)
  if [ "$st" != "0" ]; then
    local msg
    msg=$(echo "$GET_JSON" | jq -r '.message // "unknown error"' 2>/dev/null || echo "unparseable response")
    echo "ERROR: 'pipeline get' for '$pid' returned status $st — $msg" >&2
    exit 2
  fi
}

case "$MODE" in
  status)
    SRC="${2:?status mode needs a JSON file path or '-' for stdin}"
    JSON=$([ "$SRC" = "-" ] && cat || cat "$SRC")
    ST=$(echo "$JSON" | jq -r '.status // 1')
    if [ "$ST" = "0" ]; then echo "OK: command status 0"; exit 0; fi
    MSG=$(echo "$JSON" | jq -r '.message // "unknown error"')
    echo "ERROR: command returned status $ST — $MSG" >&2; exit 1
    ;;
  active)
    PID="${2:?}"; WANT="${3:?expected true|false}"; ORG="${4:-}"
    read_pipeline "$PID" "$ORG"   # exits 2 on read/JSON error before we evaluate fields
    GOT=$(echo "$GET_JSON" | jq -r '.result.isActive')
    if [ "$GOT" = "$WANT" ]; then echo "OK: isActive == $WANT"; exit 0; fi
    echo "ERROR: expected isActive=$WANT but pipeline '$PID' reports isActive=$GOT" >&2; exit 1
    ;;
  has-stage)
    PID="${2:?}"; NAME="${3:?stage name}"; ORG="${4:-}"
    read_pipeline "$PID" "$ORG"
    if echo "$GET_JSON" | jq -e --arg n "$NAME" '.result.stages[]? | select(.name == $n)' >/dev/null; then
      echo "OK: stage '$NAME' present"; exit 0
    fi
    echo "ERROR: stage '$NAME' not found in pipeline '$PID'" >&2; exit 1
    ;;
  has-project)
    PID="${2:?}"; NAME="${3:?project name}"; ORG="${4:-}"
    read_pipeline "$PID" "$ORG"
    if echo "$GET_JSON" | jq -e --arg n "$NAME" '.result.connectedProjects[]? | select(.name == $n)' >/dev/null; then
      echo "OK: project '$NAME' connected"; exit 0
    fi
    echo "ERROR: project '$NAME' not connected to pipeline '$PID'" >&2; exit 1
    ;;
  *)
    echo "ERROR: unknown mode '$MODE' (expected status|active|has-stage|has-project)" >&2; exit 1
    ;;
esac
