#!/usr/bin/env bash
# Deterministically list DevOps Center projects, or resolve a single project
# name to its ID. Handles the empty-list case explicitly.
# Usage:
#   scripts/list-projects.sh [target-org]
#       -> print "Id<TAB>Name<TAB>Description" for every project (one per line);
#          prints "NO_PROJECTS" to stdout and exits 0 when none exist
#   scripts/list-projects.sh --resolve <project-name> [target-org]
#       -> print the matching project's Id on stdout; exits 3 if not found
# Exits 2 on any CLI read / JSON error.
#
# project list returns SObject records under .result.projects[] with capitalized
# fields (Id, Name, Description).

set -euo pipefail

read_projects() {
  local org="$1" flag=() err rc json st
  [ -n "$org" ] && flag=(--target-org "$org")
  err=$(mktemp); rc=0
  json=$(sf devops project list "${flag[@]+"${flag[@]}"}" --json 2>"$err") || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: could not list projects (sf exited $rc): $(tr '\n' ' ' <"$err")" >&2
    rm -f "$err"; exit 2
  fi
  rm -f "$err"
  st=$(echo "$json" | jq -r '.status // 1' 2>/dev/null || echo 1)
  if [ "$st" != "0" ]; then
    local msg; msg=$(echo "$json" | jq -r '.message // "unknown error"' 2>/dev/null || echo "unparseable response")
    echo "ERROR: 'project list' returned status $st — $msg" >&2; exit 2
  fi
  printf '%s' "$json"
}

if [ "${1:-}" = "--resolve" ]; then
  NAME="${2:?--resolve needs a project name}"; ORG="${3:-}"
  JSON=$(read_projects "$ORG")
  ID=$(echo "$JSON" | jq -r --arg n "$NAME" '.result.projects[]? | select(.Name == $n) | .Id' | head -n1)
  if [ -z "$ID" ] || [ "$ID" = "null" ]; then
    echo "ERROR: no project named '$NAME' found" >&2; exit 3
  fi
  echo "$ID"; exit 0
fi

ORG="${1:-}"
JSON=$(read_projects "$ORG")
COUNT=$(echo "$JSON" | jq '.result.projects | length')
if [ "$COUNT" -eq 0 ]; then
  echo "NO_PROJECTS"; exit 0
fi
echo "$JSON" | jq -r '.result.projects[] | "\(.Id)\t\(.Name)\t\(.Description // "")"'
