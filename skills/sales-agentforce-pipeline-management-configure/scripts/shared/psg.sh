#!/bin/bash
# shared/psg.sh — shared PermissionSetGroup recalculation helper.
#
# PermissionSetGroup.Status is a system-computed field (Updated / Updating /
# Outdated / Failed), NOT client-writable. A component change (inserting a
# PermissionSetGroupComponent) is what TRIGGERS the async recalculation — there
# is no CLI recalc verb and no client-writable nudge.
#
# Design choice (deliberate): setup does NOT block waiting for recalculation to
# finish. Firing the trigger is sufficient for the org to converge on its own.
# The recalc's completion only matters later, when a user tries to VIEW
# suggestions in the UI or the scheduled flow RUNS a generation — both of which
# happen well after setup exits. So callers only ever read Status once, for
# reporting, and never sleep-poll.
#
# This file only DEFINES a function; it makes no org calls when sourced.

# psg_status <org-alias> <psg-developer-name>
#
# Reads the named PSG's recalculation Status ONCE (no waiting). Prints one of:
#   Updated | Updating | Outdated | Failed   (the raw Status value), or
#   not-found                                 (PSG DeveloperName did not resolve), or
#   unknown                                   (query/parse failed)
# Always returns 0 — the caller inspects the printed value. Never sleeps.
psg_status() {
  local org="$1" psg_name="$2"
  local psg_id
  psg_id=$(sf data query \
    --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = '${psg_name}'" \
    --target-org "$org" \
    --use-tooling-api \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

  if [[ -z "$psg_id" ]]; then
    printf 'not-found'
    return 0
  fi

  local status
  status=$(sf data query \
    --query "SELECT Status FROM PermissionSetGroup WHERE Id = '${psg_id}'" \
    --target-org "$org" \
    --use-tooling-api \
    --json 2>/dev/null | jq -r '.result.records[0].Status // empty' 2>/dev/null || echo "")

  printf '%s' "${status:-unknown}"
  return 0
}
