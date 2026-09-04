#!/usr/bin/env bash
# Deterministically update a DevOps Center project's name, description, and/or
# active status. Accepts a project ID or a project name (resolved via the list).
# At least one of --name / --description / --is-active|--no-is-active is required.
# Usage:
#   scripts/update-project.sh --project (<id>|name:<name>) \
#     [--name <new-name>] [--description <new-desc>] \
#     [--is-active|--no-is-active] [--target-org <alias>]
# Prints "UPDATED <id>" on success; exits 2 on CLI error, 3 if the name cannot
# be resolved, 1 on usage error.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="" NEW_NAME="" NEW_DESC="" ACTIVE="" ORG=""
have_name=0 have_desc=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --name) NEW_NAME="${2:?}"; have_name=1; shift 2 ;;
    --description) NEW_DESC="${2:?}"; have_desc=1; shift 2 ;;
    --is-active) ACTIVE="true"; shift ;;
    --no-is-active) ACTIVE="false"; shift ;;
    --target-org) ORG="${2:?}"; shift 2 ;;
    *) echo "ERROR: unknown arg '$1'" >&2; exit 1 ;;
  esac
done

[ -n "$PROJECT" ] || { echo "ERROR: --project (<id>|name:<name>) is required" >&2; exit 1; }
if [ "$have_name" -eq 0 ] && [ "$have_desc" -eq 0 ] && [ -z "$ACTIVE" ]; then
  echo "ERROR: at least one of --name, --description, or --is-active/--no-is-active is required" >&2; exit 1
fi

# Resolve name:<name> to an ID; otherwise treat as a literal ID. list-projects.sh
# --resolve exits 3 (no such project) or 2 (auth / CLI / JSON failure); propagate
# the real code so a failed read is never masked as a clean "not found".
case "$PROJECT" in
  name:*)
    rrc=0
    PID=$("$HERE/list-projects.sh" --resolve "${PROJECT#name:}" "$ORG") || rrc=$?
    [ "$rrc" -eq 0 ] || exit "$rrc"
    ;;
  *) PID="$PROJECT" ;;
esac

flag=(); [ -n "$ORG" ] && flag=(--target-org "$ORG")
args=(--project-id "$PID")
[ "$have_name" -eq 1 ] && args+=(--name "$NEW_NAME")
[ "$have_desc" -eq 1 ] && args+=(--description "$NEW_DESC")
[ "$ACTIVE" = "true" ] && args+=(--is-active)
[ "$ACTIVE" = "false" ] && args+=(--no-is-active)

err=$(mktemp); rc=0
sf devops project update "${args[@]}" "${flag[@]+"${flag[@]}"}" --json >/dev/null 2>"$err" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "ERROR: project update failed (sf exited $rc): $(tr '\n' ' ' <"$err")" >&2
  rm -f "$err"; exit 2
fi
rm -f "$err"

# Verify persistence: re-read the project from the authoritative
# .result.projects[] list envelope and assert each requested field took effect.
# Never trust the update command's own exit code / output shape alone.
verr=$(mktemp); vrc=0
LIST=$(sf devops project list "${flag[@]+"${flag[@]}"}" --json 2>"$verr") || vrc=$?
if [ "$vrc" -ne 0 ]; then
  echo "ERROR: update succeeded but the verification re-read failed (sf exited $vrc): $(tr '\n' ' ' <"$verr")" >&2
  rm -f "$verr"; exit 2
fi
rm -f "$verr"

REC=$(echo "$LIST" | jq -c --arg id "$PID" '.result.projects[]? | select(.Id == $id)')
if [ -z "$REC" ]; then
  echo "ERROR: update reported success but project '$PID' is not in the project list" >&2; exit 2
fi

if [ "$have_name" -eq 1 ]; then
  GOT=$(echo "$REC" | jq -r '.Name')
  [ "$GOT" = "$NEW_NAME" ] || { echo "ERROR: name not persisted (expected '$NEW_NAME', got '$GOT')" >&2; exit 2; }
fi
if [ "$have_desc" -eq 1 ]; then
  GOT=$(echo "$REC" | jq -r '.Description // ""')
  [ "$GOT" = "$NEW_DESC" ] || { echo "ERROR: description not persisted (expected '$NEW_DESC', got '$GOT')" >&2; exit 2; }
fi
if [ -n "$ACTIVE" ]; then
  # The list envelope exposes IsActive only on some API versions. Assert it when
  # present; when absent (null), the field is not verifiable from the list, so we
  # fall back to the update command's success (already confirmed above) for it.
  GOT=$(echo "$REC" | jq -r '.IsActive // "absent"')
  if [ "$GOT" != "absent" ] && [ "$GOT" != "$ACTIVE" ]; then
    echo "ERROR: active status not persisted (expected '$ACTIVE', got '$GOT')" >&2; exit 2
  fi
fi

echo "UPDATED $PID"; exit 0
