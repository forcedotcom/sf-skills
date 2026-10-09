#!/usr/bin/env bash
# deploy-and-report.sh - deploy a PresenceUserConfig (+ referenced PresenceDeclineReason) as one atomic Metadata package with the validator-safe decline/ACW rep profile; idempotent. Args, env, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash deploy-and-report.sh <org-alias> [config_developer_name] [agent_usernames_csv]"}' >&2
  exit 1
fi

ORG="$1"
CONFIG_DN="${2:-Omni_Demo_Presence_Config}"
AGENTS_CSV="${3:-${AGENT_USERNAMES_CSV:-}}"

DECLINE_REASON_LABEL="${DECLINE_REASON_LABEL:-Training}"
DECLINE_REASON_DN="${DECLINE_REASON_DEVELOPER_NAME:-$(printf '%s' "$DECLINE_REASON_LABEL" | tr ' ' '_' | tr -cd 'A-Za-z0-9_')}"
CAPACITY="${CAPACITY:-5}"
ACW_SECONDS="${ACW_SECONDS:-60}"
PRESENCE_STATUS_ON_DECLINE="${PRESENCE_STATUS_ON_DECLINE:-}"
CONFIG_LABEL=$(printf '%s' "$CONFIG_DN" | tr '_' ' ')

# ---- validation ----
if ! [[ "$CONFIG_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid config_developer_name '$CONFIG_DN'. Must start with a letter and contain only letters, digits, underscores (max 80).\"}" >&2
  exit 1
fi
if ! [[ "$DECLINE_REASON_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid DECLINE_REASON_DEVELOPER_NAME '$DECLINE_REASON_DN'.\"}" >&2
  exit 1
fi
if ! [[ "$CAPACITY" =~ ^[0-9]+$ ]] || [ "$CAPACITY" -lt 1 ] || [ "$CAPACITY" -gt 100 ]; then
  echo "{\"error\":\"Invalid CAPACITY '$CAPACITY' - must be an integer 1..100.\"}" >&2
  exit 1
fi
if ! [[ "$ACW_SECONDS" =~ ^[0-9]+$ ]] || [ "$ACW_SECONDS" -lt 10 ] || [ "$ACW_SECONDS" -gt 3600 ]; then
  echo "{\"error\":\"Invalid ACW_SECONDS '$ACW_SECONDS' - must be an integer 10..3600 (Metadata API bound).\"}" >&2
  exit 1
fi
if [ -n "$PRESENCE_STATUS_ON_DECLINE" ] && ! [[ "$PRESENCE_STATUS_ON_DECLINE" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid PRESENCE_STATUS_ON_DECLINE '$PRESENCE_STATUS_ON_DECLINE'.\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Escape the five XML predefined entities so a label/username with & < > " ' cannot break the
# hand-built metadata XML (or inject elements) when interpolated into the heredocs below.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"; s="${s//\'/&apos;}"
  printf '%s' "$s"
}

emit_blocked() {
  local msg="$1"; local target_skill="${2:-}"
  local manual_actions='[]'
  if [ -n "$target_skill" ]; then
    manual_actions=$(jq -n --arg ts "$target_skill" '[{id:"MISSING_PREREQ",title:"Run prerequisite skill",target_skill:$ts}]')
  fi
  jq -n --arg msg "$msg" --arg cdn "$CONFIG_DN" --arg rdn "$DECLINE_REASON_DN" --argjson ma "$manual_actions" \
    '{skill:"service-omni-presence-user-config-deploy",status:"blocked",
      config:{developer_name:$cdn,state:"not_deployed"},
      decline_reason:{developer_name:$rdn,state:"not_deployed"},
      assigned_usernames:[],deploy_id:null,manual_actions:$ma,blocking_issue:$msg}'
  exit 1
}

emit_plan() {
  local detail="$1"
  jq -n --arg detail "$detail" --arg cdn "$CONFIG_DN" \
    '{skill:"service-omni-presence-user-config-deploy",status:"action_needed",plan_mode:true,
      plan_detail:$detail,config:{developer_name:$cdn},manual_actions:[],blocking_issue:null}'
  exit 0
}

# Step 1 - Organization + safe_to_write guard
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
[ "$SAFE_TO_WRITE" = "true" ] || emit_blocked "Refusing to deploy a presence configuration to a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."

# Step 2 - Resolve agent usernames (accept usernames and/or 005... Ids)
USERNAMES=()
if [ -n "$AGENTS_CSV" ]; then
  ID_IN=""; RAW_USERNAMES=()
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    if [[ "$tok" =~ ^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$ ]]; then
      ID_IN="${ID_IN:+$ID_IN,}'$tok'"
    elif [[ "$tok" =~ ^[^,\'\"[:space:]]+@[^,\'\"[:space:]]+$ ]]; then
      RAW_USERNAMES+=("$tok")
    else
      emit_blocked "agent_usernames_csv token is neither a Username (...@...) nor a 15/18-char User Id (005...): '$tok'"
    fi
  done <<< "$(printf '%s' "$AGENTS_CSV" | tr ',' '\n' | sed 's/^ *//;s/ *$//')"

  for u in "${RAW_USERNAMES[@]}"; do USERNAMES+=("$u"); done
  if [ -n "$ID_IN" ]; then
    # Fail-closed: a swallowed query failure would silently drop the Id-resolved users and deploy a
    # config bound to fewer agents than requested. Block on both a non-zero query and an unparseable body.
    IDU_JSON=$(sf data query --target-org "$ORG" --json \
      --query "SELECT Username FROM User WHERE Id IN ($ID_IN) AND IsActive=true" 2>/dev/null) \
      || emit_blocked "Could not resolve agent User Ids to usernames (query failed: authentication, network, or API access). Refusing to deploy a presence config bound to an unverified user set."
    echo "$IDU_JSON" | jq -e '.result.records' >/dev/null 2>&1 \
      || emit_blocked "Agent User Id resolution returned no parseable records (inconclusive). Refusing to deploy against an unverified user set."
    while IFS= read -r u; do [ -n "$u" ] && USERNAMES+=("$u"); done \
      < <(echo "$IDU_JSON" | jq -r '.result.records[].Username // empty')
  fi
fi

# PLAN_ONLY - detection is read-only; report intent and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  emit_plan "Would deploy PresenceDeclineReason '$DECLINE_REASON_DN' and PresenceUserConfig '$CONFIG_DN' (capacity=$CAPACITY, ACW=${ACW_SECONDS}s, decline+decline-reason on, auto-accept off) assigned to ${#USERNAMES[@]} agent(s)."
fi

# Step 3 - Materialize the two components in XSD order
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
cp "$SCRIPT_DIR/../assets/sfdx-project.json" "$WORK/sfdx-project.json" 2>/dev/null \
  || echo '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}' > "$WORK/sfdx-project.json"
DR_DIR="$WORK/force-app/main/default/presenceDeclineReasons"
PUC_DIR="$WORK/force-app/main/default/presenceUserConfigs"
mkdir -p "$DR_DIR" "$PUC_DIR"

# PresenceDeclineReason (label only).
cat > "$DR_DIR/${DECLINE_REASON_DN}.presenceDeclineReason-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<PresenceDeclineReason xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>$(xml_escape "$DECLINE_REASON_LABEL")</label>
</PresenceDeclineReason>
XML

# Build the <assignments> block only when we have usernames.
ASSIGN_BLOCK=""
if [ ${#USERNAMES[@]} -gt 0 ]; then
  USER_LINES=""
  for u in "${USERNAMES[@]}"; do USER_LINES+="            <user>$(xml_escape "$u")</user>
"; done
  ASSIGN_BLOCK="    <assignments>
        <users>
${USER_LINES}        </users>
    </assignments>
"
fi

# Optional presenceStatusOnDecline (emitted in XSD order, after label).
PSOD_LINE=""
[ -n "$PRESENCE_STATUS_ON_DECLINE" ] && PSOD_LINE="    <presenceStatusOnDecline>${PRESENCE_STATUS_ON_DECLINE}</presenceStatusOnDecline>
"

# PresenceUserConfig - elements in strict XSD order:
# afterConvoWorkMaxTime, assignments, capacity, declineReasons, enableAutoAccept, enableDecline,
# enableDeclineReason, hasAfterConvoWorkTimer, label, presenceStatusOnDecline.
cat > "$PUC_DIR/${CONFIG_DN}.presenceUserConfig-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<PresenceUserConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <afterConvoWorkMaxTime>${ACW_SECONDS}</afterConvoWorkMaxTime>
${ASSIGN_BLOCK}    <capacity>${CAPACITY}</capacity>
    <declineReasons>${DECLINE_REASON_DN}</declineReasons>
    <enableAutoAccept>false</enableAutoAccept>
    <enableDecline>true</enableDecline>
    <enableDeclineReason>true</enableDeclineReason>
    <hasAfterConvoWorkTimer>true</hasAfterConvoWorkTimer>
    <label>$(xml_escape "$CONFIG_LABEL")</label>
${PSOD_LINE}</PresenceUserConfig>
XML

# Step 4 - Deploy both components (async + poll to terminal state)
START_JSON=$(cd "$WORK" && sf project deploy start --target-org "$ORG" \
  --metadata "PresenceDeclineReason:${DECLINE_REASON_DN}" \
  --metadata "PresenceUserConfig:${CONFIG_DN}" \
  --async --json 2>/dev/null || true)
DEPLOY_ID=$(echo "$START_JSON" | jq -r '.result.id // ""' 2>/dev/null)
DEPLOY_JSON="$START_JSON"

if [ -n "$DEPLOY_ID" ] && [ "$DEPLOY_ID" != "null" ]; then
  POLL_STATUS=""
  for _ in $(seq 1 60); do
    REPORT_JSON=$(cd "$WORK" && sf project deploy report --job-id "$DEPLOY_ID" --target-org "$ORG" --json 2>/dev/null || true)
    CUR_STATUS=$(echo "$REPORT_JSON" | jq -r '.result.status // ""' 2>/dev/null)
    case "$CUR_STATUS" in
      Succeeded|Failed|SucceededPartial|Canceled) DEPLOY_JSON="$REPORT_JSON"; POLL_STATUS="$CUR_STATUS"; break ;;
    esac
    sleep 15
  done
  [ -n "$POLL_STATUS" ] || emit_blocked "Presence-config deploy job $DEPLOY_ID did not reach a terminal state within the poll budget. Not reporting success."
fi

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // ""'    2>/dev/null)

if [ "$DEPLOY_SUCCESS" != "true" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  [ -n "$FAILURES" ] && [ "$FAILURES" != "null" ] || FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  # The presence-status arm must only fire when PRESENCE_STATUS_ON_DECLINE is set; as a case glob an
  # empty value becomes `**`, which matches ANY failure and misattributes every error. Check it
  # explicitly (literal grep -F) after the base-settings arm to preserve the original priority.
  case "$FAILURES" in
    *INVALID_TYPE*|*"OmniChannel"*) emit_blocked "Presence-config deploy failed ($FAILURES). Omni-Channel base settings may not be enabled." "service-omni-base-settings-configure" ;;
    *)
      if [ -n "$PRESENCE_STATUS_ON_DECLINE" ] && printf '%s' "$FAILURES" | grep -qF -- "$PRESENCE_STATUS_ON_DECLINE"; then
        emit_blocked "Presence-config deploy failed: presenceStatusOnDecline '$PRESENCE_STATUS_ON_DECLINE' does not exist. Deploy it first." "service-omni-presence-status-deploy"
      fi
      emit_blocked "Presence-config deploy failed: $FAILURES"
      ;;
  esac
fi

get_state() {
  local fn="$1"; local type="$2"
  echo "$DEPLOY_JSON" | jq -r --arg fn "$fn" --arg t "$type" \
    '.result.files[] | select(.fullName==$fn and .type==$t) | .state' 2>/dev/null | head -1
}
STATE_DR=$(get_state "$DECLINE_REASON_DN" "PresenceDeclineReason"); STATE_DR="${STATE_DR:-unknown}"
STATE_PUC=$(get_state "$CONFIG_DN" "PresenceUserConfig");           STATE_PUC="${STATE_PUC:-unknown}"

for pair in "DECLINE_REASON:$STATE_DR" "CONFIG:$STATE_PUC"; do
  st="${pair#*:}"
  case "$st" in
    Created|Changed|Unchanged) ;;
    *) emit_blocked "Deploy reported success overall but component ${pair%%:*} has an unrecognized/absent state \"$st\" (expected Created, Changed, or Unchanged). Not reporting success." ;;
  esac
done

# Skill status: created if any Created; else updated if any Changed; else reused.
STATUS="reused"
if [ "$STATE_DR" = "Created" ] || [ "$STATE_PUC" = "Created" ]; then
  STATUS="created"
elif [ "$STATE_DR" = "Changed" ] || [ "$STATE_PUC" = "Changed" ]; then
  STATUS="updated"
fi

ASSIGNED_JSON=$(printf '%s\n' "${USERNAMES[@]:-}" | jq -R . | jq -s 'map(select(length>0))')

jq -n \
  --arg status "$STATUS" \
  --arg cdn "$CONFIG_DN" --arg clbl "$CONFIG_LABEL" --argjson cap "$CAPACITY" --argjson acw "$ACW_SECONDS" --arg cstate "$STATE_PUC" \
  --arg rdn "$DECLINE_REASON_DN" --arg rlbl "$DECLINE_REASON_LABEL" --arg rstate "$STATE_DR" \
  --argjson assigned "$ASSIGNED_JSON" \
  --arg deploy_id "$DEPLOY_ID" \
  '{
    skill: "service-omni-presence-user-config-deploy",
    status: $status,
    config: {developer_name:$cdn, label:$clbl, capacity:$cap, acw_seconds:$acw, state:$cstate},
    decline_reason: {developer_name:$rdn, label:$rlbl, state:$rstate},
    assigned_usernames: $assigned,
    deploy_id: (if $deploy_id=="" then null else $deploy_id end),
    manual_actions: [],
    blocking_issue: null
  }'
