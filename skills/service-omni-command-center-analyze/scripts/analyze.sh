#!/usr/bin/env bash
# analyze.sh - read-only analysis of the Omni supervisor experience (Command Center V2 vs classic) + recommended next action; SOQL/Tooling reads only, no writes. Args, states, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash analyze.sh <org-alias> [supervisor_username_or_id]"}' >&2
  exit 1
fi

ORG="$1"
SUP="${2:-}"

AUTH_CHECK=$(sf org display --target-org "$ORG" --json 2>/dev/null || true)
if [ -z "$AUTH_CHECK" ]; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Best-effort query helper: echoes the raw JSON; caller inspects .status and payload.
soql() { sf data query --target-org "$ORG" --json --query "$1" 2>/dev/null || true; }
soql_tooling() { sf data query --target-org "$ORG" --use-tooling-api --json --query "$1" 2>/dev/null || true; }

json_status() { echo "$1" | jq -r '.status // 1' 2>/dev/null || echo 1; }
json_total()  { echo "$1" | jq -r '.result.totalSize // (.result.records | length) // 0' 2>/dev/null || echo 0; }

# Signal 1 - V2 capability (does the user-permission column exist on the org schema?)
CAP_JSON=$(soql "SELECT Id FROM PermissionSet WHERE PermissionsCommandCenterForServiceUser = true LIMIT 1")
if [ "$(json_status "$CAP_JSON")" = "0" ]; then
  CAPABILITY=true
elif echo "$CAP_JSON" | grep -qiE "No such column|INVALID_FIELD|PermissionsCommandCenterForServiceUser"; then
  CAPABILITY=false
else
  CAPABILITY=unknown
fi

# Signal 2 - Seeded FlexiPage (proxy for the CommandCenterForServiceV2 preference being ON)
SEED_PRESENT=unknown
if [ "$CAPABILITY" = "true" ]; then
  SEED_JSON=$(soql_tooling "SELECT Id FROM FlexiPage WHERE DeveloperName='CommandCenterForServiceV2_L'")
  if [ "$(json_status "$SEED_JSON")" = "0" ]; then
    if [ "$(json_total "$SEED_JSON")" -gt 0 ]; then SEED_PRESENT=true; else SEED_PRESENT=false; fi
  else
    SEED_PRESENT=unknown
  fi
fi

# Signal 3 - V2 tab (best-effort cross-check)
TAB_PRESENT=unknown
if [ "$CAPABILITY" = "true" ]; then
  TAB_JSON=$(soql "SELECT Name FROM TabDefinition WHERE Name='standard-commandcenterforservicev2' LIMIT 1")
  if [ "$(json_status "$TAB_JSON")" = "0" ]; then
    if [ "$(json_total "$TAB_JSON")" -gt 0 ]; then TAB_PRESENT=true; else TAB_PRESENT=false; fi
  else
    TAB_PRESENT=unknown
  fi
fi

# Signal 4 - Legacy OmniSupervisorConfig count (informational)
LEG_JSON=$(soql_tooling "SELECT Id FROM OmniSupervisorConfig")
if [ "$(json_status "$LEG_JSON")" = "0" ]; then LEG_COUNT=$(json_total "$LEG_JSON"); else LEG_COUNT="null"; fi

# Signal 5 - Supervisor permission (only when a supervisor is supplied)
SUP_CHECKED=false
SUP_HAS_PERM=unknown
SUP_ID=""
SUP_IDENT="null"
SUP_CHECK_ERROR=""
if [ -n "$SUP" ]; then
  SUP_IDENT="$SUP"
  if [[ "$SUP" =~ ^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
    SUP_QUERY="SELECT Id FROM User WHERE Id='$SUP' LIMIT 1"
  elif [[ "$SUP" =~ ^[^,\'\"[:space:]]+@[^,\'\"[:space:]]+$ ]]; then
    SUP_QUERY="SELECT Id FROM User WHERE Username='$SUP' LIMIT 1"
  else
    echo "{\"error\":\"supervisor_username_or_id '$SUP' is neither a Username (...@...) nor a 15/18-char User Id (005...).\"}" >&2
    exit 1
  fi

  if [ "$CAPABILITY" = "true" ]; then
    UID_JSON=$(soql "$SUP_QUERY")
    if [ "$(json_status "$UID_JSON")" != "0" ]; then
      SUP_CHECK_ERROR="Supplied supervisor '$SUP_IDENT' could not be read through a supported API. Not guessing; verify User read access and retry."
    elif [ "$(json_total "$UID_JSON")" -ne 1 ]; then
      SUP_CHECK_ERROR="Supplied supervisor '$SUP_IDENT' was not found. Verify the username or User Id and retry."
    else
      SUP_ID=$(echo "$UID_JSON" | jq -r '.result.records[0].Id // ""' 2>/dev/null)
      if [ -z "$SUP_ID" ]; then
        SUP_CHECK_ERROR="Supplied supervisor '$SUP_IDENT' lookup returned no User Id. Not guessing; verify User read access and retry."
      fi
    fi

    if [ -z "$SUP_CHECK_ERROR" ]; then
      PERM_JSON=$(soql "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId='$SUP_ID' AND PermissionSet.PermissionsCommandCenterForServiceUser = true LIMIT 1")
      if [ "$(json_status "$PERM_JSON")" = "0" ]; then
        SUP_CHECKED=true
        if [ "$(json_total "$PERM_JSON")" -gt 0 ]; then SUP_HAS_PERM=true; else SUP_HAS_PERM=false; fi
      else
        SUP_CHECK_ERROR="CommandCenterForServiceUser permission could not be read for supplied supervisor '$SUP_IDENT'. Not guessing; verify PermissionSetAssignment read access and retry."
      fi
    fi
  fi
fi

# Derive state
STATE=""; REC_ACTION=""; REC_SKILL="null"; STATUS="detected"; BLOCKING="null"

if [ "$CAPABILITY" = "unknown" ]; then
  STATE="ambiguous"; STATUS="blocked"
  REC_ACTION="V2 capability could not be read through a supported API. Not guessing; re-run with an authenticated org that permits these read queries."
  BLOCKING="\"$REC_ACTION\""
elif [ "$CAPABILITY" = "false" ]; then
  STATE="legacy_selected"
  REC_ACTION="Command Center for Service V2 capability is not present on this org; configure the classic Omni Supervisor experience."
  REC_SKILL="\"service-omni-supervisor-config-deploy\""
elif [ -n "$SUP_CHECK_ERROR" ]; then
  STATE="ambiguous"; STATUS="blocked"
  REC_ACTION="$SUP_CHECK_ERROR"
  BLOCKING="\"$REC_ACTION\""
elif [ "$SEED_PRESENT" = "unknown" ]; then
  STATE="ambiguous"; STATUS="blocked"
  REC_ACTION="V2 capability is present but the seeded FlexiPage could not be read through a supported API. Not guessing; re-run with an org that permits the Tooling query."
  BLOCKING="\"$REC_ACTION\""
else
  # capability true, seed known (true/false)
  if [ "$SEED_PRESENT" = "true" ] && { [ "$TAB_PRESENT" = "true" ] || [ "$TAB_PRESENT" = "unknown" ]; }; then
    if [ "$SUP_CHECKED" = "true" ] && [ "$SUP_HAS_PERM" = "false" ]; then
      STATE="v2_permission_missing"
      REC_ACTION="V2 is enabled and seeded, but supervisor '$SUP_IDENT' lacks the CommandCenterForServiceUser permission. Assign it via a PermissionSet (headless-capable; see manual_actions for packaging)."
      REC_SKILL="null"
    else
      STATE="v2_ready"
      if [ "$SUP_CHECKED" = "true" ]; then
        REC_ACTION="V2 is enabled and seeded and supervisor '$SUP_IDENT' has the CommandCenterForServiceUser permission. Verify the seeded page and tab."
      else
        REC_ACTION="V2 is enabled and seeded at the org level. Supply a supervisor to verify per-user permission; otherwise verify the seeded page and tab."
      fi
    fi
  elif { [ "$SEED_PRESENT" = "true" ] && [ "$TAB_PRESENT" = "false" ]; } || { [ "$SEED_PRESENT" = "false" ] && [ "$TAB_PRESENT" = "true" ]; }; then
    STATE="v2_seed_incomplete"
    REC_ACTION="V2 capability is present but page/tab provisioning is inconsistent (seed_flexipage_present=$SEED_PRESENT, v2_tab_present=$TAB_PRESENT). Re-check in Setup → Omni-Channel → Supervisor Settings; there is no supported public write API to re-provision headlessly."
    REC_SKILL="null"
  else
    STATE="v2_available_not_enabled"
    REC_ACTION="Org supports V2 but the CommandCenterForServiceV2 preference is off (no seeded page). Enable it manually in Setup → Omni-Channel → Supervisor Settings; there is no supported Metadata/Tooling write API for this preference."
    REC_SKILL="null"
  fi
fi

# manual_actions: for permission_missing and ambiguous surface a concrete pointer.
MANUAL_ACTIONS='[]'
case "$STATE" in
  v2_permission_missing)
    MANUAL_ACTIONS=$(jq -n '[{id:"ASSIGN_V2_PERM",title:"Assign the CommandCenterForServiceUser permission to the supervisor (headless-capable via PermissionSet; packaging pending)",target_skill:null}]') ;;
  v2_available_not_enabled|v2_seed_incomplete)
    MANUAL_ACTIONS=$(jq -n '[{id:"ENABLE_V2_PREF",title:"Enable Command Center for Service V2 in Setup → Omni-Channel → Supervisor Settings (no supported public write API; manual)",target_skill:null}]') ;;
esac

# Emit
LEG_JQ="$LEG_COUNT"; [ "$LEG_COUNT" = "null" ] && LEG_JQ=null

jq -n \
  --arg status "$STATUS" \
  --arg state "$STATE" \
  --arg rec_action "$REC_ACTION" \
  --argjson rec_skill "$REC_SKILL" \
  --arg cap "$CAPABILITY" \
  --arg seed "$SEED_PRESENT" \
  --arg tab "$TAB_PRESENT" \
  --argjson sup_ident "$( [ "$SUP_IDENT" = "null" ] && echo null || jq -n --arg s "$SUP_IDENT" '$s' )" \
  --argjson sup_checked "$SUP_CHECKED" \
  --arg sup_perm "$SUP_HAS_PERM" \
  --argjson leg "$LEG_JQ" \
  --argjson manual "$MANUAL_ACTIONS" \
  --argjson blocking "$BLOCKING" \
  '{
    skill: "service-omni-command-center-analyze",
    status: $status,
    state: $state,
    recommended_action: $rec_action,
    recommended_skill: $rec_skill,
    signals: {
      v2_capability: $cap,
      seed_flexipage_present: $seed,
      v2_tab_present: $tab,
      supervisor: {
        identifier: $sup_ident,
        checked: $sup_checked,
        has_command_center_permission: (if $sup_checked then ($sup_perm=="true") else $sup_perm end)
      },
      legacy_omnisupervisorconfig_count: $leg
    },
    manual_actions: $manual,
    blocking_issue: $blocking
  }'

[ "$STATUS" = "blocked" ] && exit 1
exit 0
