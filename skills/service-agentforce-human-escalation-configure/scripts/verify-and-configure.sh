#!/usr/bin/env bash
# verify-and-configure.sh - configure + verify Agentforce agent → human escalation (queue/QRC/member/flow + doc-driven canEscalate/outboundRoute verify); idempotent, PLAN_ONLY=1 previews. Inputs, ownership, exit codes: SKILL.md + references/.

set -euo pipefail

SKILL_NAME="service-agentforce-human-escalation-configure"
API_VERSION="v66.0"
# Runtime flow developer name (env-overridable); the temp deploy is written as ${FLOW_DEV_NAME}.
FLOW_DEV_NAME="${FLOW_DEVELOPER_NAME:-Human_Escalation_Outbound_Flow}"
# Human-readable Flow label; defaults to the developer name with underscores as spaces.
FLOW_LABEL="${FLOW_LABEL:-${FLOW_DEV_NAME//_/ }}"
# Work object routed to the queue (default MessagingSession; Case/VoiceCall pair with SERVICE_CHANNEL_*).
CONTEXT_OBJECT="${CONTEXT_OBJECT:-MessagingSession}"
SERVICE_CHANNEL_DEV_NAME="${SERVICE_CHANNEL_DEV_NAME:-sfdc_livemessage}"
SERVICE_CHANNEL_LABEL="${SERVICE_CHANNEL_LABEL:-Messaging}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Bundled flow is a tokenized template; rendered into ${FLOW_DEV_NAME}.flow-meta.xml at deploy time.
ASSET_FLOW="$SCRIPT_DIR/../assets/force-app/main/default/flows/Human_Escalation_Outbound_Flow.flow-meta.xml"

# Escape the five XML predefined entities, then sed replacement metacharacters, so a caller-supplied
# FLOW_LABEL / SERVICE_CHANNEL_LABEL with & < > " ' | cannot corrupt the rendered flow XML.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"; s="${s//\'/&apos;}"
  printf '%s' "$s"
}
sed_repl_escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }

# Cleanup trap: remove temp working dirs on exit.
TWORK=""
_cleanup() { [ -n "$TWORK" ] && rm -rf "$TWORK" 2>/dev/null || true; }
trap _cleanup EXIT

# Args
if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash verify-and-configure.sh <org-alias> [<agent-developer-name>] [<queue-developer-name>] [<escalation-topic-api-name>] [<planner-bundle-api-name>]"}' >&2
  exit 1
fi

ORG="$1"
AGENT_DN="${2:-${AGENT_DEVELOPER_NAME:-Support_Agent}}"
QUEUE_DN="${3:-${QUEUE_DEVELOPER_NAME:-Human_Support_Queue}}"
ESCALATION_TOPIC="${4:-${ESCALATION_TOPIC_API_NAME:-}}"
PLANNER_BUNDLE="${5:-${PLANNER_BUNDLE_API_NAME:-}}"
THRESHOLD_AUTHORED="${THRESHOLD_AUTHORED:-0}"
# Consecutive failed attempts before hand-off (default 2); rendered into the directive + verdict.
DEFAULT_FAILURE_THRESHOLD="${DEFAULT_FAILURE_THRESHOLD:-2}"

# Input contract - validate BEFORE any sf call. DeveloperName grammar: leading letter, then
# letters/digits/underscore, max 80.
DN_RE='^[A-Za-z][A-Za-z0-9_]{0,79}$'
if ! [[ "$AGENT_DN" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid agent_developer_name '$AGENT_DN'. Must start with a letter and contain only letters, digits, and underscores (max 80 chars).\"}" >&2
  exit 1
fi
if ! [[ "$QUEUE_DN" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid queue_developer_name '$QUEUE_DN'. Must start with a letter and contain only letters, digits, and underscores (max 80 chars).\"}" >&2
  exit 1
fi
if [ -n "$ESCALATION_TOPIC" ] && ! [[ "$ESCALATION_TOPIC" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid escalation_topic_api_name '$ESCALATION_TOPIC'. Must match the DeveloperName grammar.\"}" >&2
  exit 1
fi
if [ -n "$PLANNER_BUNDLE" ] && ! [[ "$PLANNER_BUNDLE" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid planner_bundle_api_name '$PLANNER_BUNDLE'. Must match the DeveloperName grammar.\"}" >&2
  exit 1
fi
# CONTEXT_OBJECT is an sObject API name; validate with the same grammar (safe for SOQL/XML interpolation).
if ! [[ "$CONTEXT_OBJECT" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid context_object '$CONTEXT_OBJECT'. Must be an sObject API name (leading letter, then letters, digits, and underscores).\"}" >&2
  exit 1
fi
if ! [[ "$FLOW_DEV_NAME" =~ $DN_RE ]]; then
  echo "{\"error\":\"Invalid flow_developer_name '$FLOW_DEV_NAME'. Must match the DeveloperName grammar.\"}" >&2
  exit 1
fi
# DEFAULT_FAILURE_THRESHOLD must be a small positive integer (1-99).
if ! [[ "$DEFAULT_FAILURE_THRESHOLD" =~ ^[1-9][0-9]?$ ]]; then
  echo "{\"error\":\"Invalid DEFAULT_FAILURE_THRESHOLD '$DEFAULT_FAILURE_THRESHOLD'. Must be a positive integer between 1 and 99.\"}" >&2
  exit 1
fi

# QUEUE_MEMBER_USERNAMES (optional): parse/trim/validate the full list before any sf call, so bad
# input never mutates the org first. The cleaned, comma-joined list is what the members step consumes.
UNAME_RE='^[A-Za-z0-9._%+@-]+$'
QUEUE_MEMBER_USERNAMES_CLEAN=""
if [ -n "${QUEUE_MEMBER_USERNAMES:-}" ]; then
  IFS=',' read -ra _UNAMES <<< "$QUEUE_MEMBER_USERNAMES"
  for _raw in "${_UNAMES[@]}"; do
    uname="${_raw#"${_raw%%[![:space:]]*}"}"; uname="${uname%"${uname##*[![:space:]]}"}"
    [ -z "$uname" ] && continue
    if ! [[ "$uname" =~ $UNAME_RE ]]; then
      echo "{\"error\":\"Invalid QUEUE_MEMBER_USERNAMES entry '$uname'. Usernames may contain only letters, digits, and . _ % + @ - characters.\"}" >&2
      exit 1
    fi
    if [ -z "$QUEUE_MEMBER_USERNAMES_CLEAN" ]; then
      QUEUE_MEMBER_USERNAMES_CLEAN="$uname"
    else
      QUEUE_MEMBER_USERNAMES_CLEAN="$QUEUE_MEMBER_USERNAMES_CLEAN,$uname"
    fi
  done
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Helpers
emit_blocked() {
  local msg="$1"; local click_path="${2:-}"
  local manual_actions='[]'
  if [ -n "$click_path" ]; then
    manual_actions=$(jq -n --arg cp "$click_path" '[{id:"MANUAL_FIX", title:"Manual fix required", click_path:$cp}]')
  fi
  jq -n \
    --arg skill "$SKILL_NAME" --arg msg "$msg" --arg agent "$AGENT_DN" --arg queue "$QUEUE_DN" \
    --argjson ma "$manual_actions" \
    '{skill:$skill, status:"BLOCKED", agent:{developer_name:$agent}, queue:{developer_name:$queue},
      manual_actions:$ma, blocking_issue:$msg}'
  exit 1
}

emit_plan() {
  local detail="$1"
  jq -n --arg skill "$SKILL_NAME" --arg detail "$detail" --arg agent "$AGENT_DN" --arg queue "$QUEUE_DN" \
    '{skill:$skill, status:"PLAN", plan_mode:true, plan_detail:$detail,
      agent:{developer_name:$agent}, queue:{developer_name:$queue}, manual_actions:[], blocking_issue:null}'
  exit 0
}

# Step 1 - Organization + safe_to_write guard
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null)

IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ]; then
  SAFE_TO_WRITE=true
elif [ "$TRIAL_EXP" != "null" ]; then
  SAFE_TO_WRITE=true
elif [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  emit_blocked "Refusing to configure escalation on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."
fi

# Step 2 - Precondition: agent exists AND latest version Active
BOT_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE DeveloperName='$AGENT_DN'" \
  --json 2>/dev/null)

TWORK=$(mktemp -d)
echo "$BOT_JSON" > "$TWORK/bot.json"
AGENT_VERDICT=$(node "$SCRIPT_DIR/classify-agent-active.mjs" "$TWORK/bot.json" "$AGENT_DN") || {
  emit_blocked "Could not read BotDefinition for '$AGENT_DN' - surface the raw sf error and retry. Raw: $BOT_JSON"
}
AGENT_READY=$(echo "$AGENT_VERDICT" | jq -r '.ready')
if [ "$AGENT_READY" != "true" ]; then
  AGENT_REASON=$(echo "$AGENT_VERDICT" | jq -r '.reason')
  emit_blocked "Agent precondition failed ($AGENT_REASON). Create and activate the agent '$AGENT_DN' before wiring escalation." \
    "Setup → Agentforce → Agents → '$AGENT_DN' → activate the latest version"
fi
AGENT_ACTIVE=true

# Step 3 - Precondition: for MessagingSession handoff, an active Enhanced Chat / MIAW MessagingChannel
# must exist. Other context objects use a different transport and aren't gated here.
if [ "$CONTEXT_OBJECT" = "MessagingSession" ]; then
  MC_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id, DeveloperName FROM MessagingChannel WHERE IsActive=true LIMIT 1" \
    --json 2>/dev/null)
  MC_COUNT=$(echo "$MC_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
  if [ "$MC_COUNT" -eq 0 ]; then
    emit_blocked "No active MessagingChannel (Enhanced Chat / MIAW) found. Provision the messaging channel first, then re-run." \
      "Setup → Messaging Settings → New Channel (Messaging for In-App and Web)"
  fi
fi

# Step 3b - Preflight: determine which Agentforce authoring model the org exposes. classic =
# GenAiPlugin + GenAiPlannerBundle (canEscalate + outboundRouteConfigs surfaces). nga = AiAuthoringBundle
# (Agent Script; escalation via @utils.escalate/create-record, routed through channel Omni to the queue).
# none = neither -> fail closed. Model rationale: references/nga-escalation.md.
MDT_JSON=$(sf org list metadata-types --target-org "$ORG" --json 2>/dev/null || echo '{}')
HAS_PLUGIN=$(echo "$MDT_JSON" | jq -r '[.result.metadataObjects[]?.xmlName] | index("GenAiPlugin") // empty' 2>/dev/null || echo "")
HAS_BUNDLE=$(echo "$MDT_JSON" | jq -r '[.result.metadataObjects[]?.xmlName] | index("GenAiPlannerBundle") // empty' 2>/dev/null || echo "")
HAS_AIAUTHORING=$(echo "$MDT_JSON" | jq -r '[.result.metadataObjects[]?.xmlName] | index("AiAuthoringBundle") // empty' 2>/dev/null || echo "")

AUTHORING_MODEL="none"
HAS_CLASSIC_SURFACE=false
HAS_NGA_SURFACE=false
[ -n "$HAS_BUNDLE" ] && [ -n "$HAS_PLUGIN" ] && HAS_CLASSIC_SURFACE=true
[ -n "$HAS_AIAUTHORING" ] && HAS_NGA_SURFACE=true

# When an org exposes both authoring generations, classify the selected target rather
# than defaulting the whole org to classic. A target-specific retrieve is read-only and
# prevents an NGA agent from being verified against unrelated classic metadata.
TARGET_CLASSIC=false
TARGET_NGA=false
if [ "$HAS_NGA_SURFACE" = "true" ]; then
  MODEL_DIR="$TWORK/model-nga"
  mkdir -p "$MODEL_DIR"
  if sf project retrieve start --target-org "$ORG" --metadata "AiAuthoringBundle:$AGENT_DN" \
      --target-metadata-dir "$MODEL_DIR" --unzip --json >/dev/null 2>&1 \
     && find "$MODEL_DIR" -type f -print -quit | grep -q .; then
    TARGET_NGA=true
  fi
fi
if [ "$HAS_CLASSIC_SURFACE" = "true" ]; then
  MODEL_DIR="$TWORK/model-classic"
  mkdir -p "$MODEL_DIR"
  CLASSIC_TARGET="${PLANNER_BUNDLE:-$AGENT_DN}"
  if sf project retrieve start --target-org "$ORG" --metadata "GenAiPlannerBundle:$CLASSIC_TARGET" \
      --target-metadata-dir "$MODEL_DIR" --unzip --json >/dev/null 2>&1 \
     && find "$MODEL_DIR" -type f -print -quit | grep -q .; then
    TARGET_CLASSIC=true
  fi
fi

if [ "$TARGET_NGA" = "true" ] && [ "$TARGET_CLASSIC" != "true" ]; then
  AUTHORING_MODEL="nga"
elif [ "$TARGET_CLASSIC" = "true" ] && [ "$TARGET_NGA" != "true" ]; then
  AUTHORING_MODEL="classic"
elif [ "$TARGET_CLASSIC" = "true" ] && [ "$TARGET_NGA" = "true" ]; then
  if [ -z "${AUTHORING_MODEL_OVERRIDE:-}" ]; then
    emit_blocked "The selected agent resolves in both classic and next-gen Agentforce authoring metadata. Set AUTHORING_MODEL_OVERRIDE=classic or nga after confirming the intended target model."
  fi
elif [ "$HAS_CLASSIC_SURFACE" = "true" ] && [ "$HAS_NGA_SURFACE" != "true" ]; then
  AUTHORING_MODEL="classic"
elif [ "$HAS_NGA_SURFACE" = "true" ] && [ "$HAS_CLASSIC_SURFACE" != "true" ]; then
  AUTHORING_MODEL="nga"
elif [ "$HAS_CLASSIC_SURFACE" = "true" ] && [ "$HAS_NGA_SURFACE" = "true" ]; then
  if [ -z "${AUTHORING_MODEL_OVERRIDE:-}" ]; then
    emit_blocked "This org exposes both Agentforce authoring models, but the selected target could not be classified. Set AUTHORING_MODEL_OVERRIDE=classic or nga after confirming the target metadata."
  fi
fi
# AUTHORING_MODEL_OVERRIDE (classic|nga) lets a caller pin the branch when both surfaces coexist.
case "${AUTHORING_MODEL_OVERRIDE:-}" in
  classic) [ "$HAS_CLASSIC_SURFACE" = "true" ] && AUTHORING_MODEL="classic" ;;
  nga)     [ "$HAS_NGA_SURFACE" = "true" ] && AUTHORING_MODEL="nga" ;;
esac

if [ "$AUTHORING_MODEL" = "none" ]; then
  emit_blocked "This org exposes neither the classic Agentforce authoring metadata (GenAiPlugin + GenAiPlannerBundle) nor the next-gen AiAuthoringBundle, so no agent escalation surface can be authored or verified here. Enable Agentforce, then re-run. To provision only the deterministic routing infrastructure (queue, members, QueueRoutingConfig, outbound RoutingFlow) on this org, use the service-omni-* leaf skills directly." \
    "Setup → Einstein / Agentforce → enable Agentforce so the authoring metadata (GenAiPlannerBundle or AiAuthoringBundle) is exposed"
fi

# Step 4 - Create-or-adopt the human queue (+ QueueSobject for the context object)
Q_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id FROM Group WHERE DeveloperName='$QUEUE_DN' AND Type='Queue'" \
  --json 2>/dev/null)
QUEUE_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].Id // ""')

if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ -n "$QUEUE_ID" ]; then
    emit_plan "Agent '$AGENT_DN' active; queue '$QUEUE_DN' exists. Would ensure the $CONTEXT_OBJECT QueueSobject and at least one active direct-user member (adding from QUEUE_MEMBER_USERNAMES if empty); ONLY if the queue has an eligible member would it then create/adopt+bind the QueueRoutingConfig and deploy outbound flow '$FLOW_DEV_NAME'; finally round-trip escalation config."
  else
    emit_plan "Agent '$AGENT_DN' active; queue '$QUEUE_DN' missing. Would create the queue ($CONTEXT_OBJECT QueueSobject) and ensure at least one active direct-user member (adding from QUEUE_MEMBER_USERNAMES if empty); ONLY if the queue has an eligible member would it then create+bind the QueueRoutingConfig and deploy outbound flow '$FLOW_DEV_NAME'; finally round-trip escalation config."
  fi
fi

if [ -z "$QUEUE_ID" ]; then
  # Create the queue + context-object QueueSobject via Metadata API.
  TQ="$TWORK/queue/force-app/main/default/queues"
  mkdir -p "$TQ"
  cat > "$TWORK/queue/sfdx-project.json" <<'JSON'
{ "packageDirectories": [{ "path": "force-app", "default": true }], "namespace": "", "sourceApiVersion": "67.0" }
JSON
  # Queue XSD order: doesSendEmailToMembers, name, queueSobject (Metadata API rejects other orders).
  cat > "$TQ/${QUEUE_DN}.queue-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<Queue xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesSendEmailToMembers>false</doesSendEmailToMembers>
    <name>${QUEUE_DN}</name>
    <queueSobject>
        <sobjectType>${CONTEXT_OBJECT}</sobjectType>
    </queueSobject>
</Queue>
XML
  if ! DEPLOY_OUT=$(sf project deploy start --target-org "$ORG" --source-dir "$TWORK/queue/force-app" --json 2>/dev/null); then
    emit_blocked "Failed to create queue '$QUEUE_DN'. Raw: $(echo "$DEPLOY_OUT" | head -c 600)"
  fi
  Q_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM Group WHERE DeveloperName='$QUEUE_DN' AND Type='Queue'" --json 2>/dev/null)
  QUEUE_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].Id // ""')
  [ -z "$QUEUE_ID" ] && emit_blocked "Queue '$QUEUE_DN' not found after create attempt."
fi

# Ensure the context-object QueueSobject exists; an adopted queue may lack it - bind additively via Data API.
QS_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id FROM QueueSobject WHERE QueueId='$QUEUE_ID' AND SobjectType='$CONTEXT_OBJECT'" \
  --json 2>/dev/null)
QUEUE_SOBJECT_PRESENT=false
[ "$(echo "$QS_JSON" | jq -r '.result.totalSize // 0')" -gt 0 ] && QUEUE_SOBJECT_PRESENT=true

if [ "$QUEUE_SOBJECT_PRESENT" != "true" ]; then
  QS_STDERR="$(mktemp)"
  QS_POST=$(sf api request rest --target-org "$ORG" \
    "/services/data/$API_VERSION/sobjects/QueueSobject" \
    --method POST \
    --body "$(jq -n --arg q "$QUEUE_ID" --arg so "$CONTEXT_OBJECT" '{QueueId:$q, SobjectType:$so}')" 2>"$QS_STDERR" || true)
  rm -f "$QS_STDERR"
  if [ "$(echo "$QS_POST" | jq -r '.success // false' 2>/dev/null)" = "true" ]; then
    QUEUE_SOBJECT_PRESENT=true
  else
    QS_ERR=$(echo "$QS_POST" | jq -r '.[0].message // .message // "unknown error"' 2>/dev/null)
    emit_blocked "Queue '$QUEUE_DN' exists but is not bound to $CONTEXT_OBJECT, and the QueueSobject bind failed: $QS_ERR" \
      "Setup → Queues → '$QUEUE_DN' → Supported Objects → add the context object → Save"
  fi
fi

# Step 4b - Ensure the queue has >=1 active direct-user member (Id prefix 005); an empty queue can't
# receive escalations, so routing (Steps 5/6) is refused without one. Necessary but not sufficient for
# routability (Omni perms/presence proven only at runtime) - hence the honest evidence key
# queueHasActiveDirectUserMember. Members come from the pre-validated QUEUE_MEMBER_USERNAMES_CLEAN list.
count_active_user_members() {
  local gm ids uq
  gm=$(sf data query --target-org "$ORG" \
    --query "SELECT UserOrGroupId FROM GroupMember WHERE GroupId='$QUEUE_ID'" --json 2>/dev/null)
  # Only direct User members (Id prefix 005) can be resolved to IsActive deterministically.
  ids=$(echo "$gm" | jq -r '[.result.records[]?.UserOrGroupId | select(type=="string" and startswith("005"))] | join("\u0027,\u0027")' 2>/dev/null || echo "")
  if [ -z "$ids" ]; then echo 0; return; fi
  uq=$(sf data query --target-org "$ORG" \
    --query "SELECT COUNT(Id) c FROM User WHERE IsActive=true AND Id IN ('$ids')" --json 2>/dev/null)
  echo "$uq" | jq -r '.result.records[0].c // (.result.totalSize // 0)' 2>/dev/null || echo 0
}

MEMBER_COUNT=$(count_active_user_members)
[ -z "$MEMBER_COUNT" ] && MEMBER_COUNT=0

if [ "$MEMBER_COUNT" -eq 0 ] && [ -n "$QUEUE_MEMBER_USERNAMES_CLEAN" ]; then
  IFS=',' read -ra _UNAMES <<< "$QUEUE_MEMBER_USERNAMES_CLEAN"
  for uname in "${_UNAMES[@]}"; do
    [ -z "$uname" ] && continue
    U_JSON=$(sf data query --target-org "$ORG" \
      --query "SELECT Id FROM User WHERE Username='$uname' AND IsActive=true LIMIT 1" --json 2>/dev/null)
    U_ID=$(echo "$U_JSON" | jq -r '.result.records[0].Id // ""')
    if [ -z "$U_ID" ]; then
      emit_blocked "QUEUE_MEMBER_USERNAMES user '$uname' was not found as an active User on '$ORG'. Create or reactivate the user, or correct the username, then rerun."
    fi
    GM_STDERR="$(mktemp)"
    GM_POST=$(sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/GroupMember" \
      --method POST \
      --body "$(jq -n --arg g "$QUEUE_ID" --arg u "$U_ID" '{GroupId:$g, UserOrGroupId:$u}')" 2>"$GM_STDERR" || true)
    rm -f "$GM_STDERR"
    if [ "$(echo "$GM_POST" | jq -r '.success // false' 2>/dev/null)" != "true" ]; then
      # A duplicate membership (already a member) is benign; anything else is fatal.
      if ! echo "$GM_POST" | jq -e '((.[0].errorCode // "") | test("DUPLICATE"))' >/dev/null 2>&1; then
        GM_ERR=$(echo "$GM_POST" | jq -r '.[0].message // .message // "unknown error"' 2>/dev/null)
        emit_blocked "Failed to add '$uname' to queue '$QUEUE_DN' as a member: $GM_ERR"
      fi
    fi
  done
  MEMBER_COUNT=$(count_active_user_members)
  [ -z "$MEMBER_COUNT" ] && MEMBER_COUNT=0
fi

QUEUE_HAS_ACTIVE_DIRECT_USER_MEMBER=false
[ "$MEMBER_COUNT" -gt 0 ] && QUEUE_HAS_ACTIVE_DIRECT_USER_MEMBER=true

# Membership gate: Steps 5 (QRC bind) + 6 (Flow) run only with an eligible member; else left
# unconfigured and the verdict is INCOMPLETE (never a flow routing to nobody).
QUEUE_ROUTING_CONFIG_PRESENT=false
QUEUE_ROUTING_CONFIG_BOUND=false
RC_ID=""
FLOW_ACTIVE_ID=""
if [ "$QUEUE_HAS_ACTIVE_DIRECT_USER_MEMBER" = "true" ]; then

# Step 5 - Ensure a QueueRoutingConfig, then bind it to the queue (Group.QueueRoutingConfigId)
RC_DN="${QUEUE_DN}_RC"
RC_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='$RC_DN'" --json 2>/dev/null)
RC_ID=$(echo "$RC_JSON" | jq -r '.result.records[0].Id // ""')

if [ -z "$RC_ID" ]; then
  # Create QRC via Data API. RoutingPriority is required (REQUIRED_FIELD_MISSING if omitted).
  RC_STDERR="$(mktemp)"
  RC_POST=$(sf api request rest --target-org "$ORG" \
    "/services/data/$API_VERSION/sobjects/QueueRoutingConfig" \
    --method POST \
    --body "$(jq -n --arg dn "$RC_DN" --arg ml "${QUEUE_DN} Routing Config" \
              '{DeveloperName:$dn, MasterLabel:$ml, RoutingModel:"MostAvailable", CapacityWeight:5, RoutingPriority:1, IsAttributeBased:false}')" 2>"$RC_STDERR" || true)
  rm -f "$RC_STDERR"
  if [ "$(echo "$RC_POST" | jq -r '.success // false' 2>/dev/null)" = "true" ]; then
    RC_ID=$(echo "$RC_POST" | jq -r '.id')
  else
    if echo "$RC_POST" | jq -e '(.name // "") == "INVALID_TYPE" or ((.[0].errorCode // "") == "INVALID_TYPE")' >/dev/null 2>&1; then
      emit_blocked "QueueRoutingConfig is not available because Omni-Channel is not enabled on this org. Enable Omni-Channel in Setup, then rerun."
    fi
    RC_ERR=$(echo "$RC_POST" | jq -r '.[0].message // .message // "unknown error"' 2>/dev/null)
    emit_blocked "Failed to create QueueRoutingConfig '$RC_DN': $RC_ERR"
  fi
fi
QUEUE_ROUTING_CONFIG_PRESENT=false
[ -n "$RC_ID" ] && QUEUE_ROUTING_CONFIG_PRESENT=true

# Bind the QRC to the queue (Group.QueueRoutingConfigId) if not already linked.
QUEUE_ROUTING_CONFIG_BOUND=false
if [ -n "$RC_ID" ]; then
  G_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id, QueueRoutingConfigId FROM Group WHERE Id='$QUEUE_ID'" --json 2>/dev/null)
  CUR_RC=$(echo "$G_JSON" | jq -r '.result.records[0].QueueRoutingConfigId // ""')
  if [ "$CUR_RC" = "$RC_ID" ]; then
    QUEUE_ROUTING_CONFIG_BOUND=true
  else
    G_STDERR="$(mktemp)"
    sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/Group/$QUEUE_ID" \
      --method PATCH \
      --body "$(jq -n --arg rc "$RC_ID" '{QueueRoutingConfigId:$rc}')" >/dev/null 2>"$G_STDERR" || true
    G_ERR=$(head -c 400 "$G_STDERR" 2>/dev/null || true)
    rm -f "$G_STDERR"
    # PATCH returns 204 (empty body) on success - re-query to CONFIRM the binding persisted.
    G_JSON=$(sf data query --target-org "$ORG" \
      --query "SELECT Id, QueueRoutingConfigId FROM Group WHERE Id='$QUEUE_ID'" --json 2>/dev/null)
    [ "$(echo "$G_JSON" | jq -r '.result.records[0].QueueRoutingConfigId // ""')" = "$RC_ID" ] && QUEUE_ROUTING_CONFIG_BOUND=true
    if [ "$QUEUE_ROUTING_CONFIG_BOUND" != "true" ]; then
      emit_blocked "Created/adopted QueueRoutingConfig '$RC_DN' but failed to bind it to queue '$QUEUE_DN' (Group.QueueRoutingConfigId did not persist).${G_ERR:+ Raw: $G_ERR}"
    fi
  fi
fi

# Step 6 - Deploy the bundled outbound QueueBased RoutingFlow (tokens substituted)
FLOW_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='$FLOW_DEV_NAME' AND ProcessType='RoutingFlow'" \
  --json 2>/dev/null)
FLOW_ACTIVE_ID=$(echo "$FLOW_JSON" | jq -r '.result.records[0].ActiveVersionId // ""')

if [ -z "$FLOW_ACTIVE_ID" ]; then
  [ -f "$ASSET_FLOW" ] || emit_blocked "Bundled outbound flow asset not found at $ASSET_FLOW"
  TF="$TWORK/flow/force-app/main/default/flows"
  mkdir -p "$TF"
  cat > "$TWORK/flow/sfdx-project.json" <<'JSON'
{ "packageDirectories": [{ "path": "force-app", "default": true }], "namespace": "", "sourceApiVersion": "67.0" }
JSON
  SC_LABEL_SED="$(sed_repl_escape "$(xml_escape "$SERVICE_CHANNEL_LABEL")")"
  FLOW_LABEL_SED="$(sed_repl_escape "$(xml_escape "$FLOW_LABEL")")"
  sed -e "s|__QUEUE_DEVELOPER_NAME__|${QUEUE_DN}|g" \
      -e "s|__SERVICE_CHANNEL_DEV_NAME__|${SERVICE_CHANNEL_DEV_NAME}|g" \
      -e "s|__SERVICE_CHANNEL_LABEL__|${SC_LABEL_SED}|g" \
      -e "s|__FLOW_DEVELOPER_NAME__|${FLOW_DEV_NAME}|g" \
      -e "s|__FLOW_LABEL__|${FLOW_LABEL_SED}|g" \
      "$ASSET_FLOW" > "$TF/${FLOW_DEV_NAME}.flow-meta.xml"
  # Deploy from inside the temp project so sf uses its sourceApiVersion (67.0), not an ancestor's.
  if ! DEPLOY_OUT=$(cd "$TWORK/flow" && sf project deploy start --target-org "$ORG" --source-dir force-app --json 2>/dev/null); then
    emit_blocked "Failed to deploy outbound flow '$FLOW_DEV_NAME'. Raw: $(echo "$DEPLOY_OUT" | head -c 600)"
  fi
  FLOW_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='$FLOW_DEV_NAME' AND ProcessType='RoutingFlow'" \
    --json 2>/dev/null)
  FLOW_ACTIVE_ID=$(echo "$FLOW_JSON" | jq -r '.result.records[0].ActiveVersionId // ""')
fi

fi  # end membership gate - QRC bind + Flow activation skipped when the queue has no eligible member

# Step 6b - Optional deterministic authoring of the doc-driven surfaces (AUTHOR_SURFACES=1). Default is
# verify-only; with the topic/bundle names supplied this authors canEscalate + outboundRouteConfigs
# (retrieve → patch → deploy → reactivate). Runs only after the membership gate. See references/.
if [ "${AUTHOR_SURFACES:-0}" = "1" ] && [ "$QUEUE_HAS_ACTIVE_DIRECT_USER_MEMBER" = "true" ] && [ "$AUTHORING_MODEL" = "classic" ]; then
  if [ -z "$ESCALATION_TOPIC" ] && [ -z "$PLANNER_BUNDLE" ]; then
    emit_blocked "AUTHOR_SURFACES=1 requires escalation_topic_api_name and/or planner_bundle_api_name so the skill knows which topic/bundle to author. Re-run with those identifiers or omit AUTHOR_SURFACES."
  fi

  # Authoring lifecycle: publish → retrieve (metadata --unzip) → deactivate → XSD-ordered patch →
  # deploy (--metadata-dir) → activate (fail closed) → re-read latest BotVersion. See references/classifier-contracts.md.

  # 1) Publish so the compiled planner bundle exists/refreshed.
  if ! sf agent publish authoring-bundle --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1; then
    emit_blocked "AUTHOR_SURFACES: 'sf agent publish authoring-bundle' failed for '$AGENT_DN'; cannot author escalation surfaces."
  fi

  # 2) Retrieve in metadata format + --unzip (else --target-metadata-dir yields a ZIP); find the XML + package.xml root.
  APLUGIN=""; ABUNDLE=""; AROOT_PLUGIN=""; AROOT_BUNDLE=""
  if [ -n "$ESCALATION_TOPIC" ]; then
    ARET="$TWORK/author-plugin"; mkdir -p "$ARET"
    if ! sf project retrieve start --target-org "$ORG" --metadata "GenAiPlugin:$ESCALATION_TOPIC" \
         --target-metadata-dir "$ARET" --unzip >/dev/null 2>&1; then
      emit_blocked "AUTHOR_SURFACES: failed to retrieve GenAiPlugin '$ESCALATION_TOPIC' (metadata format)."
    fi
    APLUGIN=$(find "$ARET" -type f \( -name '*.genAiPlugin' -o -name '*.genAiPlugin-meta.xml' \) 2>/dev/null | head -1)
    AROOT_PLUGIN=$(dirname "$(find "$ARET" -type f -name package.xml 2>/dev/null | head -1)" 2>/dev/null || echo "")
    if [ -z "$APLUGIN" ] || [ -z "$AROOT_PLUGIN" ] || [ ! -d "$AROOT_PLUGIN" ]; then
      emit_blocked "AUTHOR_SURFACES: retrieved GenAiPlugin '$ESCALATION_TOPIC' but found no metadata-format file/package.xml to patch."
    fi
  fi
  if [ -n "$PLANNER_BUNDLE" ]; then
    ARETB="$TWORK/author-bundle"; mkdir -p "$ARETB"
    if ! sf project retrieve start --target-org "$ORG" --metadata "GenAiPlannerBundle:$PLANNER_BUNDLE" \
         --target-metadata-dir "$ARETB" --unzip >/dev/null 2>&1; then
      emit_blocked "AUTHOR_SURFACES: failed to retrieve GenAiPlannerBundle '$PLANNER_BUNDLE' (metadata format)."
    fi
    ABUNDLE=$(find "$ARETB" -type f \( -name '*.genAiPlannerBundle' -o -name '*.genAiPlannerBundle-meta.xml' \) 2>/dev/null | head -1)
    AROOT_BUNDLE=$(dirname "$(find "$ARETB" -type f -name package.xml 2>/dev/null | head -1)" 2>/dev/null || echo "")
    if [ -z "$ABUNDLE" ] || [ -z "$AROOT_BUNDLE" ] || [ ! -d "$AROOT_BUNDLE" ]; then
      emit_blocked "AUTHOR_SURFACES: retrieved GenAiPlannerBundle '$PLANNER_BUNDLE' but found no metadata-format file/package.xml to patch."
    fi
  fi

  # 3) Deactivate (deploys fail while active).
  if ! { echo "Y" | sf agent deactivate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1; }; then
    emit_blocked "AUTHOR_SURFACES: 'sf agent deactivate' failed for '$AGENT_DN'; refusing to deploy while the agent is active."
  fi
  AGENT_ACTIVE=false

  # 4) Patch (XSD-ordered) + deploy (--metadata-dir); on failure, best-effort reactivate then block.
  if [ -n "$APLUGIN" ]; then
    if ! node "$SCRIPT_DIR/patch-escalation-surfaces.mjs" canEscalate "$APLUGIN" >/dev/null 2>&1; then
      echo "Y" | sf agent activate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1 || true
      emit_blocked "AUTHOR_SURFACES: could not safely set canEscalate=true on GenAiPlugin '$ESCALATION_TOPIC' (no safe XSD-ordered insertion point)."
    fi
    if ! DEPLOY_OUT=$(sf project deploy start --target-org "$ORG" --metadata-dir "$AROOT_PLUGIN" --json 2>/dev/null); then
      echo "Y" | sf agent activate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1 || true
      emit_blocked "AUTHOR_SURFACES: failed to deploy canEscalate patch for '$ESCALATION_TOPIC'. Raw: $(echo "$DEPLOY_OUT" | head -c 400)"
    fi
  fi
  if [ -n "$ABUNDLE" ]; then
    if ! node "$SCRIPT_DIR/patch-escalation-surfaces.mjs" outboundRoute "$ABUNDLE" "$FLOW_DEV_NAME" >/dev/null 2>&1; then
      echo "Y" | sf agent activate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1 || true
      emit_blocked "AUTHOR_SURFACES: could not safely wire outboundRouteConfigs on a Messaging surface of '$PLANNER_BUNDLE' (no Messaging-class planner surface / <surface> anchor found)."
    fi
    if ! DEPLOY_OUT=$(sf project deploy start --target-org "$ORG" --metadata-dir "$AROOT_BUNDLE" --json 2>/dev/null); then
      echo "Y" | sf agent activate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1 || true
      emit_blocked "AUTHOR_SURFACES: failed to deploy outboundRouteConfigs patch for '$PLANNER_BUNDLE'. Raw: $(echo "$DEPLOY_OUT" | head -c 400)"
    fi
  fi

  # 5) Reactivate - FAIL CLOSED (never swallow with || true; an inactive agent cannot serve).
  if ! { echo "Y" | sf agent activate --api-name "$AGENT_DN" --target-org "$ORG" --json >/dev/null 2>&1; }; then
    emit_blocked "AUTHOR_SURFACES: 'sf agent activate' failed for '$AGENT_DN' after deploying the escalation surfaces; the agent is left INACTIVE." \
      "Setup → Agentforce → Agents → '$AGENT_DN' → activate the latest version"
  fi

  # 6) Re-verify the LATEST BotVersion is Active (never trust the pre-authoring AGENT_ACTIVE value).
  BOT_JSON_AFTER=$(sf data query --target-org "$ORG" \
    --query "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE DeveloperName='$AGENT_DN'" \
    --json 2>/dev/null)
  echo "$BOT_JSON_AFTER" > "$TWORK/bot-after.json"
  AGENT_VERDICT_AFTER=$(node "$SCRIPT_DIR/classify-agent-active.mjs" "$TWORK/bot-after.json" "$AGENT_DN" 2>/dev/null || echo '{"ready":false}')
  if [ "$(echo "$AGENT_VERDICT_AFTER" | jq -r '.ready')" = "true" ]; then
    AGENT_ACTIVE=true
  else
    AGENT_ACTIVE=false
    emit_blocked "AUTHOR_SURFACES: after authoring + reactivation the latest BotVersion for '$AGENT_DN' is not Active; refusing to report CONFIGURED against a stale/inactive version." \
      "Setup → Agentforce → Agents → '$AGENT_DN' → activate the latest version"
  fi
fi

# Step 7 - Verify doc-driven surfaces when their identifiers were provided
CAN_ESCALATE=false
if [ -n "$ESCALATION_TOPIC" ]; then
  RET="$TWORK/plugin"
  mkdir -p "$RET"
  # --unzip: without it --target-metadata-dir yields a ZIP and the grep below scans binary, so a
  # correctly configured topic is misreported as incomplete (mirrors the authoring path at Step 6).
  if sf project retrieve start --target-org "$ORG" --metadata "GenAiPlugin:$ESCALATION_TOPIC" \
       --target-metadata-dir "$RET" --unzip >/dev/null 2>&1; then
    if grep -Rql "<canEscalate>true</canEscalate>" "$RET" 2>/dev/null; then
      CAN_ESCALATE=true
    fi
  fi
fi

OUTBOUND_ROUTE_NAME=""
OUTBOUND_ROUTE_TYPE=""
OUTBOUND_ROUTE_SURFACE=""
OUTBOUND_ROUTE_SAME_BLOCK=false
OUTBOUND_ROUTE_MESSAGING_SURFACE=false
if [ -n "$PLANNER_BUNDLE" ]; then
  RETB="$TWORK/bundle"
  mkdir -p "$RETB"
  # --unzip: else --target-metadata-dir yields a ZIP and the find/cat below reads binary, so a wired
  # outbound route is misreported as missing.
  if sf project retrieve start --target-org "$ORG" --metadata "GenAiPlannerBundle:$PLANNER_BUNDLE" \
       --target-metadata-dir "$RETB" --unzip >/dev/null 2>&1; then
    # Couple outboundRouteName + outboundRouteType within the same planner-surface block.
    BUNDLE_CAT="$TWORK/bundle-cat.xml"
    find "$RETB" -type f -name '*.xml' -exec cat {} \; > "$BUNDLE_CAT" 2>/dev/null || true
    ROUTE_JSON=$(node "$SCRIPT_DIR/extract-outbound-route.mjs" "$BUNDLE_CAT" "$FLOW_DEV_NAME" 2>/dev/null || echo '{}')
    OUTBOUND_ROUTE_NAME=$(echo "$ROUTE_JSON" | jq -r '.name // ""')
    OUTBOUND_ROUTE_TYPE=$(echo "$ROUTE_JSON" | jq -r '.type // ""')
    OUTBOUND_ROUTE_SURFACE=$(echo "$ROUTE_JSON" | jq -r '.surface // ""')
    OUTBOUND_ROUTE_SAME_BLOCK=$(echo "$ROUTE_JSON" | jq -r '.sameBlock // false')
    OUTBOUND_ROUTE_MESSAGING_SURFACE=$(echo "$ROUTE_JSON" | jq -r '.messagingSurface // false')
  fi
fi

# Step 7b (NGA) - Verify the next-gen escalation surface by retrieving the agent's AiAuthoringBundle and
# scanning its Agent Script: a Service agent needs a reachable @utils.escalate (with connection messaging);
# an Employee agent (no messaging) needs a create-record action. Authoring the surface itself is delegated
# to agentforce-generate (see next_steps); this skill verifies + reports. Details: references/nga-escalation.md.
NGA_SURFACE_PRESENT=false
NGA_AGENT_TYPE="unknown"
if [ "$AUTHORING_MODEL" = "nga" ]; then
  NRET="$TWORK/nga-bundle"
  mkdir -p "$NRET"
  # --unzip: else --target-metadata-dir yields a ZIP and the NGA classifier scans binary, so a present
  # escalation surface is misreported as missing.
  if sf project retrieve start --target-org "$ORG" --metadata "AiAuthoringBundle:$AGENT_DN" \
       --target-metadata-dir "$NRET" --unzip >/dev/null 2>&1; then
    NGA_JSON=$(node "$SCRIPT_DIR/classify-nga-escalation.mjs" "$NRET" 2>/dev/null || echo '{}')
    NGA_SURFACE_PRESENT=$(echo "$NGA_JSON" | jq -r '.escalationSurfacePresent // false')
    NGA_AGENT_TYPE=$(echo "$NGA_JSON" | jq -r '.agentType // "unknown"')
  fi
fi

THRESHOLD_FLAG=false
[ "$THRESHOLD_AUTHORED" = "1" ] && THRESHOLD_FLAG=true

# Render the numeric threshold into the directive template (echoed in the verdict as evidence).
THRESHOLD_TEMPLATE="$SCRIPT_DIR/../assets/escalation-thresholds.instructions.md"
DIRECTIVE_RENDERED=false
if [ -f "$THRESHOLD_TEMPLATE" ]; then
  RENDERED_DIRECTIVE="$TWORK/escalation-thresholds.rendered.md"
  sed "s/__DEFAULT_FAILURES__/${DEFAULT_FAILURE_THRESHOLD}/g" "$THRESHOLD_TEMPLATE" > "$RENDERED_DIRECTIVE" 2>/dev/null \
    && DIRECTIVE_RENDERED=true
fi

# Step 8 - Assemble evidence + render the deterministic verdict
EVID="$TWORK/evidence.json"
jq -n \
  --argjson canEscalate "$CAN_ESCALATE" \
  --arg outboundRouteName "$OUTBOUND_ROUTE_NAME" \
  --arg outboundRouteType "$OUTBOUND_ROUTE_TYPE" \
  --arg outboundRouteSurface "$OUTBOUND_ROUTE_SURFACE" \
  --argjson outboundRouteSameBlock "$OUTBOUND_ROUTE_SAME_BLOCK" \
  --argjson outboundRouteMessagingSurface "$OUTBOUND_ROUTE_MESSAGING_SURFACE" \
  --arg expectedFlowName "$FLOW_DEV_NAME" \
  --arg flowActiveVersionId "$FLOW_ACTIVE_ID" \
  --arg queueId "$QUEUE_ID" \
  --argjson queueSobjectPresent "$QUEUE_SOBJECT_PRESENT" \
  --argjson queueHasActiveDirectUserMember "$QUEUE_HAS_ACTIVE_DIRECT_USER_MEMBER" \
  --argjson queueMemberCount "$MEMBER_COUNT" \
  --argjson queueRoutingConfigPresent "$QUEUE_ROUTING_CONFIG_PRESENT" \
  --argjson queueRoutingConfigBound "$QUEUE_ROUTING_CONFIG_BOUND" \
  --argjson agentActive "$AGENT_ACTIVE" \
  --argjson thresholdAuthored "$THRESHOLD_FLAG" \
  --argjson defaultFailureThreshold "$DEFAULT_FAILURE_THRESHOLD" \
  --arg authoringModel "$AUTHORING_MODEL" \
  --argjson ngaEscalationSurfacePresent "$NGA_SURFACE_PRESENT" \
  --arg ngaAgentType "$NGA_AGENT_TYPE" \
  '{canEscalate:$canEscalate, outboundRouteName:$outboundRouteName, outboundRouteType:$outboundRouteType,
    outboundRouteSurface:$outboundRouteSurface, outboundRouteSameBlock:$outboundRouteSameBlock,
    outboundRouteMessagingSurface:$outboundRouteMessagingSurface, expectedFlowName:$expectedFlowName,
    flowActiveVersionId:$flowActiveVersionId, queueId:$queueId, queueSobjectPresent:$queueSobjectPresent,
    queueHasActiveDirectUserMember:$queueHasActiveDirectUserMember, queueMemberCount:$queueMemberCount,
    queueRoutingConfigPresent:$queueRoutingConfigPresent, queueRoutingConfigBound:$queueRoutingConfigBound,
    agentActive:$agentActive, thresholdAuthored:$thresholdAuthored,
    defaultFailureThreshold:$defaultFailureThreshold, authoringModel:$authoringModel,
    ngaEscalationSurfacePresent:$ngaEscalationSurfacePresent, ngaAgentType:$ngaAgentType}' > "$EVID"

CONFIG_VERDICT=$(node "$SCRIPT_DIR/verify-escalation-config.mjs" "$EVID")
# Status mirrors the deterministic three-state verdict: CONFIGURED (routing + surface + policy),
# ROUTING_CONFIGURED_POLICY_PENDING (routing/surface done but failure-threshold directive missing),
# or INCOMPLETE. A missing policy can no longer masquerade as fully CONFIGURED.
STATUS=$(echo "$CONFIG_VERDICT" | jq -r '.verdict')
case "$STATUS" in
  CONFIGURED|ROUTING_CONFIGURED_POLICY_PENDING|INCOMPLETE) ;;
  *) STATUS="INCOMPLETE" ;;
esac

jq -n \
  --arg skill "$SKILL_NAME" \
  --arg status "$STATUS" \
  --arg agent "$AGENT_DN" \
  --arg queue "$QUEUE_DN" \
  --arg qid "$QUEUE_ID" \
  --argjson qmembers "$MEMBER_COUNT" \
  --arg flow "$FLOW_DEV_NAME" \
  --arg flowActive "$FLOW_ACTIVE_ID" \
  --arg topic "$ESCALATION_TOPIC" \
  --arg bundle "$PLANNER_BUNDLE" \
  --argjson config "$CONFIG_VERDICT" \
  --argjson thresholdValue "$DEFAULT_FAILURE_THRESHOLD" \
  --argjson thresholdAuthored "$THRESHOLD_FLAG" \
  --argjson directiveRendered "$DIRECTIVE_RENDERED" \
  --arg authoringModel "$AUTHORING_MODEL" \
  --argjson ngaSurface "$NGA_SURFACE_PRESENT" \
  --arg ngaAgentType "$NGA_AGENT_TYPE" \
  '{
    skill: $skill,
    status: $status,
    authoring_model: $authoringModel,
    agent: ({developer_name:$agent, active:true} + (if $authoringModel=="nga" then {type:$ngaAgentType, escalation_surface_present:$ngaSurface} else {} end)),
    queue: {developer_name:$queue, id:$qid, active_direct_user_member_count:$qmembers},
    outbound_flow: {api_name:$flow, active_version_id:(if $flowActive=="" then null else $flowActive end)},
    escalation_topic: (if $topic=="" then null else $topic end),
    planner_bundle: (if $bundle=="" then null else $bundle end),
    threshold: {default_failures:$thresholdValue, authored:$thresholdAuthored, directive_rendered:$directiveRendered},
    config_verification: $config,
    next_steps: (if $status=="CONFIGURED" then []
      elif $status=="ROUTING_CONFIGURED_POLICY_PENDING" then
      (["Routing and the agent escalation surface are verified, but the failure-threshold escalation policy (default two-failure / password-reset override) is not yet authored or confirmed. Author the threshold directive (AUTHOR_SURFACES=1) or confirm it in the topic instructions, then re-run to reach CONFIGURED. See references/failure-policy.md."])
      elif $authoringModel=="nga" then
      (["Deterministic routing infra is verified. Author the NGA escalation surface with agentforce-generate: for a Service agent add a reachable {!@utils.escalate} action (needs connection messaging:); for an Employee agent add a create-record (Case/Incident) action that Omni-routes to the queue. See references/nga-escalation.md, then re-run to reach CONFIGURED."]) else
      (["Author the doc-driven surfaces listed in config_verification.missing (see references/escalation-mechanism.md and failure-policy.md), then re-run to reach CONFIGURED."]) end),
    manual_actions: [],
    blocking_issue: null
  }'
