#!/usr/bin/env bash
# deploy-and-report.sh - populate the Omni Supervisor action + tab surface on an existing OmniSupervisorConfig by inserting OmniSupervisorConfigAction / OmniSupervisorConfigTab rows via the Data API. Idempotent (inserts only the missing types). Args, env, exit codes: SKILL.md; type vocabulary + reference-only exclusions: references/api-notes.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash deploy-and-report.sh <org-alias> [config_developer_name]"}' >&2
  exit 1
fi

ORG="$1"
CONFIG_DN="${2:-}"

# Reference-free standard types (safe to insert as bare companion rows).
DEFAULT_ACTIONS="AllAgents.ChangeQueues,AllAgents.ChangeSkills,AllAgents.ChangeGroups,AllAgents.AssignLearning,QueuesBacklog.ManageQueues"
DEFAULT_TABS="Wallboard,Agents,QueuesBacklog,AssignedWork,SkillsBacklog"
SAFE_ACTIONS="AllAgents.ChangeQueues AllAgents.ChangeSkills AllAgents.ChangeGroups AllAgents.AssignLearning QueuesBacklog.ManageQueues"
SAFE_TABS="Wallboard Agents QueuesBacklog AssignedWork SkillsBacklog Reports Alerts"

ACTIONS_CSV="${SUPERVISOR_ACTIONS:-$DEFAULT_ACTIONS}"
TABS_CSV="${SUPERVISOR_TABS:-$DEFAULT_TABS}"

if [ -n "$CONFIG_DN" ] && ! [[ "$CONFIG_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid config_developer_name '$CONFIG_DN'. Must start with a letter and contain only letters, digits, underscores (max 80).\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

emit_blocked() {
  local msg="$1"; local target_skill="${2:-}"
  local manual_actions='[]'
  if [ -n "$target_skill" ]; then
    manual_actions=$(jq -n --arg ts "$target_skill" '[{id:"MISSING_PREREQ",title:"Run prerequisite skill",target_skill:$ts}]')
  fi
  EMITTED=1
  jq -n --arg msg "$msg" --arg cdn "${CONFIG_DN:-}" --argjson ma "$manual_actions" \
    '{skill:"service-omni-supervisor-surface-deploy",status:"blocked",
      config:{developer_name:(if $cdn=="" then null else $cdn end),id:null},
      actions:{requested:[],created:[],reused:[],count:0},
      tabs:{requested:[],created:[],reused:[],count:0},
      manual_actions:$ma,blocking_issue:$msg}'
  exit 1
}

# Fail-safe: under `set -euo pipefail` an unguarded jq/sf failure could otherwise kill the
# script with empty stdout. Emit a structured blocked JSON on any exit before a real result so
# the coordinator never parses empty output. EMITTED flips to 1 before each intentional emit.
EMITTED=0
on_exit() {
  if [ "$EMITTED" != "1" ]; then
    jq -n --arg cdn "${CONFIG_DN:-}" \
      '{skill:"service-omni-supervisor-surface-deploy",status:"blocked",
        config:{developer_name:(if $cdn=="" then null else $cdn end),id:null},
        actions:{requested:[],created:[],reused:[],count:0},
        tabs:{requested:[],created:[],reused:[],count:0},
        manual_actions:[],
        blocking_issue:"Supervisor surface deploy aborted before completing (unexpected error; see stderr). Re-run."}'
  fi
}
trap on_exit EXIT

# Split a CSV into a space list, trimming blanks.
csv_to_items() { printf '%s' "$1" | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' || true; }

# Reject types that need an external reference (custom action, FlexiPage, AWS, AI) - a bare
# companion row cannot point at them (only OmniSupervisorConfigId/Type/DisplayOrder are createable).
requires_reference() {
  case "$1" in
    *CustomAction|*AWSDashboard|FlexipageType|AIAgents|AgentforceSDR) return 0 ;;
    *) return 1 ;;
  esac
}
in_list() { local needle="$1"; shift; local x; for x in $*; do [ "$x" = "$needle" ] && return 0; done; return 1; }

# ---- validate requested types up front (reject before any write) ----
REQ_ACTIONS=(); while IFS= read -r a; do REQ_ACTIONS+=("$a"); done < <(csv_to_items "$ACTIONS_CSV")
REQ_TABS=();    while IFS= read -r t; do REQ_TABS+=("$t");    done < <(csv_to_items "$TABS_CSV")

for a in "${REQ_ACTIONS[@]:-}"; do
  [ -z "$a" ] && continue
  if requires_reference "$a"; then
    emit_blocked "Action type '$a' needs an external reference (custom action / AWS dashboard) that a bare OmniSupervisorConfigAction row cannot carry; configure it in Setup. Supported reference-free types: $SAFE_ACTIONS."
  fi
  in_list "$a" $SAFE_ACTIONS || emit_blocked "Unsupported action type '$a'. Supported reference-free types: $SAFE_ACTIONS."
done
for t in "${REQ_TABS[@]:-}"; do
  [ -z "$t" ] && continue
  if requires_reference "$t"; then
    emit_blocked "Tab type '$t' needs an external reference (FlexiPage / AI agent) that a bare OmniSupervisorConfigTab row cannot carry; configure it in Setup. Supported reference-free types: $SAFE_TABS."
  fi
  in_list "$t" $SAFE_TABS || emit_blocked "Unsupported tab type '$t'. Supported reference-free types: $SAFE_TABS."
done

# Step 1 - safe_to_write guard
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
[ "$SAFE_TO_WRITE" = "true" ] || emit_blocked "Refusing to write the supervisor surface to a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."

# Step 2 - resolve the OmniSupervisorConfig (by DeveloperName, else the org's sole config)
if [ -n "$CONFIG_DN" ]; then
  CFG_JSON=$(sf data query --target-org "$ORG" --json \
    --query "SELECT Id, DeveloperName FROM OmniSupervisorConfig WHERE DeveloperName='$CONFIG_DN'" 2>/dev/null || echo '{}')
else
  CFG_JSON=$(sf data query --target-org "$ORG" --json \
    --query "SELECT Id, DeveloperName FROM OmniSupervisorConfig ORDER BY CreatedDate LIMIT 2" 2>/dev/null || echo '{}')
fi
CFG_COUNT=$(echo "$CFG_JSON" | jq -r '.result.records | length' 2>/dev/null || echo 0)
if [ "${CFG_COUNT:-0}" -eq 0 ]; then
  emit_blocked "No OmniSupervisorConfig found${CONFIG_DN:+ named '$CONFIG_DN'} on this org. Deploy it first." "service-omni-supervisor-config-deploy"
fi
if [ -z "$CONFIG_DN" ] && [ "$CFG_COUNT" -gt 1 ]; then
  NAMES=$(echo "$CFG_JSON" | jq -r '[.result.records[].DeveloperName] | join(", ")')
  emit_blocked "Multiple OmniSupervisorConfigs exist ($NAMES); pass one as the config_developer_name argument."
fi
CONFIG_ID=$(echo "$CFG_JSON" | jq -r '.result.records[0].Id')
CONFIG_DN=$(echo "$CFG_JSON" | jq -r '.result.records[0].DeveloperName')

# Step 3 - read existing surface rows (idempotency baseline). A failed/inconclusive read must
# NOT fall through to an empty baseline, or we would re-insert rows that already exist. Require a
# definitive .result.records array; otherwise block.
EX_ACTIONS_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT OmniSupervisorActionType, DisplayOrder FROM OmniSupervisorConfigAction WHERE OmniSupervisorConfigId='$CONFIG_ID'" 2>/dev/null) \
  || emit_blocked "Failed to read existing OmniSupervisorConfigAction rows (inconclusive; refusing to insert to avoid duplicates)."
echo "$EX_ACTIONS_JSON" | jq -e '.result.records' >/dev/null 2>&1 \
  || emit_blocked "OmniSupervisorConfigAction baseline read returned no records array (inconclusive; refusing to insert to avoid duplicates)."
EX_TABS_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT OmniSupervisorTabType, DisplayOrder FROM OmniSupervisorConfigTab WHERE OmniSupervisorConfigId='$CONFIG_ID'" 2>/dev/null) \
  || emit_blocked "Failed to read existing OmniSupervisorConfigTab rows (inconclusive; refusing to insert to avoid duplicates)."
echo "$EX_TABS_JSON" | jq -e '.result.records' >/dev/null 2>&1 \
  || emit_blocked "OmniSupervisorConfigTab baseline read returned no records array (inconclusive; refusing to insert to avoid duplicates)."
EXIST_ACTIONS=$(echo "$EX_ACTIONS_JSON" | jq -r '[.result.records[]?.OmniSupervisorActionType] | @json' 2>/dev/null || echo '[]')
EXIST_TABS=$(echo "$EX_TABS_JSON"       | jq -r '[.result.records[]?.OmniSupervisorTabType]  | @json' 2>/dev/null || echo '[]')
MAX_ACTION_ORDER=$(echo "$EX_ACTIONS_JSON" | jq -r '[.result.records[]?.DisplayOrder // 0] | max // 0' 2>/dev/null || echo 0)
MAX_TAB_ORDER=$(echo "$EX_TABS_JSON"       | jq -r '[.result.records[]?.DisplayOrder // 0] | max // 0' 2>/dev/null || echo 0)

has_existing() { echo "$1" | jq -e --arg v "$2" 'index($v) != null' >/dev/null 2>&1; }

# PLAN_ONLY - report intent, no write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  EMITTED=1
  jq -n --arg cdn "$CONFIG_DN" --arg cid "$CONFIG_ID" \
        --argjson ra "$(printf '%s\n' "${REQ_ACTIONS[@]:-}" | jq -R . | jq -s 'map(select(length>0))')" \
        --argjson rt "$(printf '%s\n' "${REQ_TABS[@]:-}"    | jq -R . | jq -s 'map(select(length>0))')" \
        --argjson ea "$EXIST_ACTIONS" --argjson et "$EXIST_TABS" \
    '{skill:"service-omni-supervisor-surface-deploy",status:"action_needed",plan_mode:true,
      config:{developer_name:$cdn,id:$cid},
      plan_detail:("Would ensure \($ra|length) action type(s) and \($rt|length) tab type(s) on OmniSupervisorConfig \($cdn); existing actions=\($ea|length), tabs=\($et|length). Inserts only the missing types."),
      actions:{requested:$ra,created:[],reused:$ea,count:($ea|length)},
      tabs:{requested:$rt,created:[],reused:$et,count:($et|length)},
      manual_actions:[],blocking_issue:null}'
  exit 0
fi

# Step 4 - insert missing action rows
CREATED_ACTIONS="[]"; REUSED_ACTIONS="[]"; ORDER=$MAX_ACTION_ORDER
for a in "${REQ_ACTIONS[@]:-}"; do
  [ -z "$a" ] && continue
  if has_existing "$EXIST_ACTIONS" "$a"; then
    REUSED_ACTIONS=$(echo "$REUSED_ACTIONS" | jq --arg v "$a" '. + [$v]')
    continue
  fi
  ORDER=$((ORDER + 1))
  RES=$(sf data create record --target-org "$ORG" --sobject OmniSupervisorConfigAction \
    --values "OmniSupervisorConfigId=$CONFIG_ID OmniSupervisorActionType=$a DisplayOrder=$ORDER" --json 2>/dev/null || true)
  OKID=$(echo "$RES" | jq -r '.result.id // ""' 2>/dev/null)
  if [ -z "$OKID" ] || [ "$OKID" = "null" ]; then
    MSG=$(echo "$RES" | jq -r '.message // "unknown insert error"' 2>/dev/null | tr -d '\n' | head -c 300)
    emit_blocked "Failed to insert OmniSupervisorConfigAction '$a': $MSG"
  fi
  CREATED_ACTIONS=$(echo "$CREATED_ACTIONS" | jq --arg v "$a" '. + [$v]')
done

# Step 5 - insert missing tab rows
CREATED_TABS="[]"; REUSED_TABS="[]"; ORDER=$MAX_TAB_ORDER
for t in "${REQ_TABS[@]:-}"; do
  [ -z "$t" ] && continue
  if has_existing "$EXIST_TABS" "$t"; then
    REUSED_TABS=$(echo "$REUSED_TABS" | jq --arg v "$t" '. + [$v]')
    continue
  fi
  ORDER=$((ORDER + 1))
  RES=$(sf data create record --target-org "$ORG" --sobject OmniSupervisorConfigTab \
    --values "OmniSupervisorConfigId=$CONFIG_ID OmniSupervisorTabType=$t DisplayOrder=$ORDER" --json 2>/dev/null || true)
  OKID=$(echo "$RES" | jq -r '.result.id // ""' 2>/dev/null)
  if [ -z "$OKID" ] || [ "$OKID" = "null" ]; then
    MSG=$(echo "$RES" | jq -r '.message // "unknown insert error"' 2>/dev/null | tr -d '\n' | head -c 300)
    emit_blocked "Failed to insert OmniSupervisorConfigTab '$t': $MSG"
  fi
  CREATED_TABS=$(echo "$CREATED_TABS" | jq --arg v "$t" '. + [$v]')
done

CREATED_TOTAL=$(( $(echo "$CREATED_ACTIONS" | jq 'length') + $(echo "$CREATED_TABS" | jq 'length') ))
STATUS="reused"; [ "$CREATED_TOTAL" -gt 0 ] && STATUS="created"

EMITTED=1
jq -n --arg status "$STATUS" --arg cdn "$CONFIG_DN" --arg cid "$CONFIG_ID" \
  --argjson ca "$CREATED_ACTIONS" --argjson rua "$REUSED_ACTIONS" \
  --argjson ct "$CREATED_TABS"    --argjson rut "$REUSED_TABS" \
  '{skill:"service-omni-supervisor-surface-deploy",status:$status,
    config:{developer_name:$cdn,id:$cid},
    actions:{requested:(($ca+$rua)|sort),created:$ca,reused:$rua,count:(($ca+$rua)|length)},
    tabs:{requested:(($ct+$rut)|sort),created:$ct,reused:$rut,count:(($ct+$rut)|length)},
    manual_actions:[],blocking_issue:null}'
