#!/usr/bin/env bash
# verify-and-align.sh - verify or (with --create-if-missing) create the Queue for a routable sObject and align its QueueRoutingConfigId to a target QRC; production-guarded, idempotent. Args, queue-selection policy, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash verify-and-align.sh <org-alias> [Case|Incident|MessagingSession|VoiceCall] [routing_config_dn] [queue_developer_name] [--create-if-missing]"}' >&2
  exit 1
fi

# Extract --create-if-missing from anywhere in the arg list, leaving positionals intact.
CREATE_IF_MISSING="${QUEUE_CREATE_IF_MISSING:-0}"
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    --create-if-missing) CREATE_IF_MISSING="1" ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done
set -- "${POSITIONAL[@]}"

ORG="$1"
SOBJECT_TYPE="${2:-Case}"
ROUTING_CONFIG_DN="${3:-}"
EXPLICIT_QUEUE_DN="${4:-}"
API_VERSION="v66.0"
QUEUE_CREATED="false"

# Validate explicit queue DeveloperName shape early (prevents SOQL-injection via arg).
if [ -n "$EXPLICIT_QUEUE_DN" ] && ! [[ "$EXPLICIT_QUEUE_DN" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
  echo "{\"error\":\"Invalid queue_developer_name '$EXPLICIT_QUEUE_DN'. Allowed: A-Z a-z 0-9 _ (max 80).\"}" >&2
  exit 1
fi

# ROUTING_CONFIG_DN is interpolated into SOQL, so validate its DeveloperName shape before any sf call.
if [ -n "$ROUTING_CONFIG_DN" ] && ! [[ "$ROUTING_CONFIG_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid routing_config_developer_name '$ROUTING_CONFIG_DN'. Must start with a letter and contain only letters, digits, and underscores (max 80 chars).\"}" >&2
  exit 1
fi

case "$SOBJECT_TYPE" in
  Case)
    [ -z "$ROUTING_CONFIG_DN" ] && ROUTING_CONFIG_DN="Case_Routing_Config"
    SUGGESTED_QUEUE_DN="CaseQueue"
    ;;
  Incident)
    SUGGESTED_QUEUE_DN="IncidentQueue"
    ;;
  MessagingSession)
    SUGGESTED_QUEUE_DN="MessagingQueue"
    ;;
  VoiceCall)
    SUGGESTED_QUEUE_DN="VoiceQueue"
    ;;
  *)
    echo "{\"error\":\"Unsupported sobject_type: '$SOBJECT_TYPE'. Supported: Case, Incident, MessagingSession, VoiceCall\"}" >&2
    exit 2
    ;;
esac

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Write guard: mutates Group.QueueRoutingConfigId, so self-enforce the production-org guard (directly invokable).
ORG_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || {
  echo "{\"error\":\"Failed to query Organization for safe_to_write guard: $(printf '%s' "$ORG_JSON" | head -c 300)\"}" >&2
  exit 1
}
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  echo "{\"skill\":\"service-omni-queue-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Refusing to align queue routing on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org.\",\"safe_to_write\":false}" >&2
  exit 1
fi

# Escape the five XML predefined entities so a caller-supplied QUEUE_LABEL with & < > " ' cannot
# break or inject into the hand-built Queue metadata XML below.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"; s="${s//\'/&apos;}"
  printf '%s' "$s"
}

# create_queue - create a Queue (Group Type=Queue) bound to $SOBJECT_TYPE. Idempotent (deploy upserts
# by fullName); sets QUEUE_CREATED, or calls emit_blocked on failure.
create_queue() {
  local dn="$1"
  local label="${QUEUE_LABEL:-}"
  if [ -z "$label" ]; then
    label="$(printf '%s' "$dn" | tr '_' ' ')"
  fi

  # Collision guard: a Queue:<dn> deploy replaces the whole component, dropping an existing queue's
  # other bindings/members. If the queue already exists, additively bind the sObject via Data API instead.
  local existing_json existing_id
  existing_json=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM Group WHERE DeveloperName='$dn' AND Type='Queue'" --json 2>/dev/null || echo '{}')
  existing_id=$(echo "$existing_json" | jq -r '.result.records[0].Id // ""' 2>/dev/null || echo "")
  if [ -n "$existing_id" ]; then
    local bound_json
    bound_json=$(sf data query --target-org "$ORG" \
      --query "SELECT Id FROM QueueSobject WHERE QueueId='$existing_id' AND SobjectType='$SOBJECT_TYPE'" \
      --json 2>/dev/null || echo '{}')
    if [ "$(echo "$bound_json" | jq -r '.result.totalSize // 0' 2>/dev/null || echo 0)" -gt 0 ]; then
      # Already exists and already bound - nothing to do.
      QUEUE_CREATED="false"
      return 0
    fi
    local qs_post qs_err
    qs_post=$(sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/QueueSobject" --method POST \
      --body "$(jq -n --arg q "$existing_id" --arg s "$SOBJECT_TYPE" '{QueueId:$q, SobjectType:$s}')" 2>/dev/null || true)
    if [ "$(echo "$qs_post" | jq -r '.success // false' 2>/dev/null)" != "true" ]; then
      qs_err=$(echo "$qs_post" | jq -r '.[0].message // .message // "unknown error"' 2>/dev/null)
      emit_blocked "Queue '$dn' already exists but is bound to a different object, and additively binding '$SOBJECT_TYPE' failed: $qs_err. Refusing to overwrite an existing queue via Metadata API (that would drop its other object bindings and members)." \
        "Setup → Users → Queues → '$dn' → Supported Objects → add '$SOBJECT_TYPE' → Save" "$existing_id" "$dn"
    fi
    QUEUE_CREATED="true"
    return 0
  fi

  local work; work="$(mktemp -d)"
  mkdir -p "$work/force-app/main/default/queues"
  cat > "$work/sfdx-project.json" <<'JSON'
{
  "packageDirectories": [{ "path": "force-app", "default": true }],
  "namespace": "",
  "sfdcLoginUrl": "https://login.salesforce.com",
  "sourceApiVersion": "66.0"
}
JSON
  # Queue XML: fullName from the file name; <name> is the label (Queue has no <label>). Child order
  # follows the MD-API schema (doesSendEmailToMembers, name, queueSobject). QRC is bound later at
  # Step 3 (Data API). Full schema note: references/api-notes.md.
  cat > "$work/force-app/main/default/queues/${dn}.queue-meta.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<Queue xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesSendEmailToMembers>false</doesSendEmailToMembers>
    <name>$(xml_escape "$label")</name>
    <queueSobject>
        <sobjectType>${SOBJECT_TYPE}</sobjectType>
    </queueSobject>
</Queue>
XML

  local deploy_json
  deploy_json=$(cd "$work" && sf project deploy start --target-org "$ORG" \
    --metadata "Queue:${dn}" --json 2>/dev/null || true)
  rm -rf "$work"

  local ok
  ok=$(echo "$deploy_json" | jq -r '.result.success // false' 2>/dev/null)
  if [ "$ok" != "true" ]; then
    local err
    err=$(echo "$deploy_json" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
    [ -z "$err" ] || [ "$err" = "null" ] && err=$(echo "$deploy_json" | jq -r '.message // "Unknown deploy error"' 2>/dev/null)
    emit_blocked "Queue creation for '$dn' (sObject $SOBJECT_TYPE) failed via Metadata API: $err" "" "null" "$dn"
  fi
  QUEUE_CREATED="true"
}

emit_blocked() {
  local msg="$1"
  local click_path="${2:-}"
  local queue_id="${3:-null}"
  local queue_dn="${4:-null}"

  local manual_actions='[]'
  if [ -n "$click_path" ]; then
    manual_actions=$(jq -n --arg cp "$click_path" '[{id: "MANUAL_QUEUE_CREATE", title: "Manual queue creation required", click_path: $cp}]')
  fi

  jq -n \
    --arg msg "$msg" \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dn "$queue_dn" \
    --arg qid "$queue_id" \
    --arg rc_dn "$ROUTING_CONFIG_DN" \
    --argjson ma "$manual_actions" \
    '{
      skill: "service-omni-queue-deploy",
      status: "blocked",
      sobject_type: $sobject,
      developer_name: (if $dn == "null" then null else $dn end),
      id: (if $qid == "null" then null else $qid end),
      queue_routing_config_id: null,
      queue_routing_config_developer_name: (if $rc_dn == "" then null else $rc_dn end),
      queue_sobjects: [],
      before: {existed: (if $qid == "null" then false else true end), queue_routing_config_id: null, queue_sobjects: []},
      manual_actions: $ma,
      blocking_issue: $msg
    }'
  exit 1
}

# emit read-only plan preview JSON and exit 0 (PLAN_ONLY mode). Includes developer_name/id so the
# coordinator can chain the discovered queue into the queue-members detector, exactly as in --run.
emit_plan() {
  local status="$1"
  local detail="$2"
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    --arg sobject "$SOBJECT_TYPE" \
    --arg dn "$QUEUE_DN" \
    --arg qid "$QUEUE_ID" \
    '{
      skill: "service-omni-queue-deploy",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      sobject_type: $sobject,
      developer_name: $dn,
      id: $qid,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Step 0 - Prereq: target sObject exists on org
ENTITY_CHECK=$(sf data query --target-org "$ORG" \
  --query "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '$SOBJECT_TYPE'" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0')

if [ "$ENTITY_CHECK" != "1" ]; then
  CLICK=""
  case "$SOBJECT_TYPE" in
    Incident) CLICK="Enable the Incident Management feature via Setup, then re-run" ;;
    MessagingSession) CLICK="Enable Enhanced Messaging via Setup → Messaging, then re-run" ;;
    VoiceCall) CLICK="Enable Service Cloud Voice and set up a Contact Center via Setup → Voice, then re-run" ;;
    Case) CLICK="Contact admin - Case sObject expected on all Service Cloud orgs" ;;
  esac
  emit_blocked "Target sObject '$SOBJECT_TYPE' is not queryable on this org" "$CLICK"
fi

# Step 1 - Select the Queue bound to the target sObject. Enumerate ALL bound queues (no LIMIT 1) so
# selection is deliberate; mutating the wrong queue's QueueRoutingConfigId could hijack another queue.
QSO_DISCOVERY=$(sf data query --target-org "$ORG" \
  --query "SELECT QueueId, Queue.DeveloperName, Queue.Name FROM QueueSobject WHERE SobjectType='$SOBJECT_TYPE' ORDER BY Queue.DeveloperName" \
  --json 2>/dev/null)

QSO_COUNT=$(echo "$QSO_DISCOVERY" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")

if [ "$QSO_COUNT" = "0" ] || [ -z "$QSO_COUNT" ]; then
  # Distinguish a genuine "zero bound queues" from a failed/inconclusive query.
  if ! echo "$QSO_DISCOVERY" | jq -e '.result.totalSize != null' >/dev/null 2>&1; then
    emit_blocked \
      "Could not determine bound queues for '$SOBJECT_TYPE' - the QueueSobject query did not return a parseable result: $(echo "$QSO_DISCOVERY" | head -c 200). Not proceeding on an inconclusive read." \
      ""
  fi

  if [ "$CREATE_IF_MISSING" = "1" ]; then
    # PLAN_ONLY must not write: report the create as an action, don't perform it.
    if [ "${PLAN_ONLY:-}" = "1" ]; then
      QUEUE_DN="${EXPLICIT_QUEUE_DN:-$SUGGESTED_QUEUE_DN}"
      QUEUE_ID="null"
      emit_plan "action_needed" "No queue bound to $SOBJECT_TYPE; would CREATE queue '$QUEUE_DN' via Metadata API and bind it."
    fi
    # Create the canonical (or explicitly-named) queue, then re-discover so the rest of the
    # script treats it exactly like a pre-existing bound queue.
    CREATE_DN="${EXPLICIT_QUEUE_DN:-$SUGGESTED_QUEUE_DN}"
    create_queue "$CREATE_DN"
    QSO_DISCOVERY=$(sf data query --target-org "$ORG" \
      --query "SELECT QueueId, Queue.DeveloperName, Queue.Name FROM QueueSobject WHERE SobjectType='$SOBJECT_TYPE' ORDER BY Queue.DeveloperName" \
      --json 2>/dev/null)
    QSO_COUNT=$(echo "$QSO_DISCOVERY" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
    if [ "$QSO_COUNT" = "0" ] || [ -z "$QSO_COUNT" ]; then
      emit_blocked \
        "Created queue '$CREATE_DN' but no QueueSobject binding for '$SOBJECT_TYPE' is visible on re-query - creation did not converge." \
        "" "null" "$CREATE_DN"
    fi
  else
    emit_blocked \
      "No Queue is bound to sObject '$SOBJECT_TYPE' on this org. Re-run with --create-if-missing to create one automatically, or create it manually." \
      "Setup → Users → Queues → New → Label: '$SUGGESTED_QUEUE_DN', DeveloperName: '$SUGGESTED_QUEUE_DN'${ROUTING_CONFIG_DN:+, Routing Configuration: '$ROUTING_CONFIG_DN'}, Supported Objects: '$SOBJECT_TYPE' → Save"
  fi
fi

# Distinct DeveloperNames bound to this sObject (a queue may have multiple QueueSobject rows).
CANDIDATE_DNS=$(echo "$QSO_DISCOVERY" | jq -c '[.result.records[].Queue.DeveloperName] | unique')

# --- Selection policy ---
QUEUE_DN=""
QUEUE_SOURCE=""

if [ -n "$EXPLICIT_QUEUE_DN" ]; then
  # (a) Operator supplied an explicit queue - it MUST be bound to this sObject (or be created).
  if [ "$(echo "$CANDIDATE_DNS" | jq --arg q "$EXPLICIT_QUEUE_DN" 'index($q) != null')" != "true" ]; then
    if [ "$CREATE_IF_MISSING" = "1" ]; then
      create_queue "$EXPLICIT_QUEUE_DN"
      QSO_DISCOVERY=$(sf data query --target-org "$ORG" \
        --query "SELECT QueueId, Queue.DeveloperName, Queue.Name FROM QueueSobject WHERE SobjectType='$SOBJECT_TYPE' ORDER BY Queue.DeveloperName" \
        --json 2>/dev/null)
      CANDIDATE_DNS=$(echo "$QSO_DISCOVERY" | jq -c '[.result.records[].Queue.DeveloperName] | unique')
      if [ "$(echo "$CANDIDATE_DNS" | jq --arg q "$EXPLICIT_QUEUE_DN" 'index($q) != null')" != "true" ]; then
        emit_blocked "Created queue '$EXPLICIT_QUEUE_DN' but its '$SOBJECT_TYPE' binding is not visible on re-query." "" "null" "$EXPLICIT_QUEUE_DN"
      fi
    else
      emit_blocked \
        "Requested queue '$EXPLICIT_QUEUE_DN' is not bound to sObject '$SOBJECT_TYPE'. Bound queues: $(echo "$CANDIDATE_DNS" | jq -c .). Re-run with --create-if-missing, bind it (Setup → Queues → '$EXPLICIT_QUEUE_DN' → Supported Objects add '$SOBJECT_TYPE'), or pass one of the bound names." \
        ""
    fi
  fi
  QUEUE_DN="$EXPLICIT_QUEUE_DN"
  QUEUE_SOURCE="explicit"
elif [ "$(echo "$CANDIDATE_DNS" | jq --arg q "$SUGGESTED_QUEUE_DN" 'index($q) != null')" = "true" ]; then
  # (b) The canonical queue for this sObject exists among the bound queues - prefer it.
  QUEUE_DN="$SUGGESTED_QUEUE_DN"
  QUEUE_SOURCE="canonical"
elif [ "$(echo "$CANDIDATE_DNS" | jq 'length')" = "1" ]; then
  # (c) Exactly one bound queue - adopt it, and report that this was an adoption decision.
  QUEUE_DN=$(echo "$CANDIDATE_DNS" | jq -r '.[0]')
  QUEUE_SOURCE="sole_bound_queue"
else
  # (d) Multiple bound queues and no explicit/canonical pick - refuse to guess.
  emit_blocked \
    "Multiple queues are bound to '$SOBJECT_TYPE' ($(echo "$CANDIDATE_DNS" | jq -c .)) and no canonical '$SUGGESTED_QUEUE_DN' exists. Refusing to guess which queue to modify. Re-run passing an explicit queue DeveloperName as the 4th argument." \
    ""
fi

# Resolve the selected DeveloperName back to its QueueId.
QUEUE_ID=$(echo "$QSO_DISCOVERY" | jq -r --arg q "$QUEUE_DN" '[.result.records[] | select(.Queue.DeveloperName == $q)][0].QueueId')
if [ -z "$QUEUE_ID" ] || [ "$QUEUE_ID" = "null" ]; then
  emit_blocked "Internal error: selected queue '$QUEUE_DN' but could not resolve its QueueId." ""
fi

# Step 2 - Query current queue QRC binding + full sObject list
Q_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, DeveloperName, QueueRoutingConfigId FROM Group WHERE Id='$QUEUE_ID' AND Type='Queue'" \
  --json 2>/dev/null)

BEFORE_RC_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].QueueRoutingConfigId // "null"')

# Full sObject list for the queue (for reporting)
QSO_ALL_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT SobjectType FROM QueueSobject WHERE QueueId='$QUEUE_ID' ORDER BY SobjectType" \
  --json 2>/dev/null)
BEFORE_QSOS=$(echo "$QSO_ALL_JSON" | jq -c '[.result.records[].SobjectType]')

# PLAN_ONLY: Steps 0-2 are read-only (queue selection is a query). Report whether a --run would
# PATCH the queue's routing-config binding, and stop before Step 3's write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ -z "$ROUTING_CONFIG_DN" ]; then
    emit_plan "reused" "Queue '$QUEUE_DN' bound to $SOBJECT_TYPE; report-only (no routing_config to align)."
  fi
  RC_PLAN_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='$ROUTING_CONFIG_DN'" --json 2>/dev/null || echo '{}')
  RC_PLAN_COUNT=$(echo "$RC_PLAN_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo 0)
  if [ "$RC_PLAN_COUNT" -eq 0 ]; then
    emit_blocked \
      "QueueRoutingConfig '$ROUTING_CONFIG_DN' does not exist on org. Run service-omni-queue-routing-config-deploy first." \
      "" "$QUEUE_ID" "$QUEUE_DN"
  fi
  RC_PLAN_ID=$(echo "$RC_PLAN_JSON" | jq -r '.result.records[0].Id')
  if [ "$BEFORE_RC_ID" = "$RC_PLAN_ID" ]; then
    emit_plan "reused" "Queue '$QUEUE_DN' already aligned to QueueRoutingConfig '$ROUTING_CONFIG_DN'."
  else
    emit_plan "action_needed" "Would align queue '$QUEUE_DN' QueueRoutingConfigId → '$ROUTING_CONFIG_DN' (currently: $BEFORE_RC_ID)."
  fi
fi

# Step 3 - Optional QRC alignment (only if routing_config_dn provided).
if [ "$QUEUE_CREATED" = "true" ]; then STATUS="created"; else STATUS="reused"; fi
TARGET_RC_ID=""
CHANGES=()

if [ -n "$ROUTING_CONFIG_DN" ]; then
  RC_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='$ROUTING_CONFIG_DN'" \
    --json 2>/dev/null)

  RC_COUNT=$(echo "$RC_JSON" | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
  if [ "$RC_COUNT" -eq 0 ]; then
    emit_blocked \
      "QueueRoutingConfig '$ROUTING_CONFIG_DN' does not exist on org. Run service-omni-queue-routing-config-deploy first." \
      "" \
      "$QUEUE_ID" \
      "$QUEUE_DN"
  fi
  TARGET_RC_ID=$(echo "$RC_JSON" | jq -r '.result.records[0].Id')

  if [ "$BEFORE_RC_ID" != "$TARGET_RC_ID" ]; then
    # New queue stays "created"; a pre-existing queue whose binding we change is "updated".
    [ "$QUEUE_CREATED" = "true" ] || STATUS="updated"
    CHANGES+=("routing_config")

    # Drift #16: `sf api request rest` emits `Warning:` to STDERR; redirect away for clean parsing.
    PATCH_STDERR="$(mktemp)"
    PATCH_RESULT=$(sf api request rest --target-org "$ORG" \
      "/services/data/$API_VERSION/sobjects/Group/$QUEUE_ID" \
      --method PATCH \
      --body "{\"QueueRoutingConfigId\":\"$TARGET_RC_ID\"}" 2>"$PATCH_STDERR" || true)
    rm -f "$PATCH_STDERR"

    if echo "$PATCH_RESULT" | jq -e 'if type == "array" then .[0].errorCode else .errorCode end' >/dev/null 2>&1; then
      ERR=$(echo "$PATCH_RESULT" | jq -r 'if type == "array" then .[0].message else .message end')
      emit_blocked "PATCH Group.QueueRoutingConfigId failed: $ERR" "" "$QUEUE_ID" "$QUEUE_DN"
    fi
  fi
fi

# Step 4 - Re-query for post-check
AFTER_Q_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, QueueRoutingConfigId FROM Group WHERE Id='$QUEUE_ID'" --json)
AFTER_RC_ID=$(echo "$AFTER_Q_JSON" | jq -r '.result.records[0].QueueRoutingConfigId // "null"')

# Resolve AFTER_RC_ID → DeveloperName for reporting (may differ from ROUTING_CONFIG_DN if we didn't force)
AFTER_RC_DN="null"
if [ "$AFTER_RC_ID" != "null" ] && [ -n "$AFTER_RC_ID" ]; then
  AFTER_RC_DN=$(sf data query --target-org "$ORG" \
    --query "SELECT DeveloperName FROM QueueRoutingConfig WHERE Id='$AFTER_RC_ID'" --json 2>/dev/null | \
    jq -r '.result.records[0].DeveloperName // "null"')
fi

# If we forced a QRC and post-check doesn't match, escalate
if [ -n "$ROUTING_CONFIG_DN" ] && [ "$AFTER_RC_ID" != "$TARGET_RC_ID" ]; then
  emit_blocked "Post-check re-query shows QRC did not converge. After=$AFTER_RC_ID (target=$TARGET_RC_ID)." "" "$QUEUE_ID" "$QUEUE_DN"
fi

# Step 5 - Emit report
jq -n \
  --arg status "$STATUS" \
  --arg sobject "$SOBJECT_TYPE" \
  --arg dn "$QUEUE_DN" \
  --arg qid "$QUEUE_ID" \
  --arg after_rc "$AFTER_RC_ID" \
  --arg after_rc_dn "$AFTER_RC_DN" \
  --argjson after_qsos "$BEFORE_QSOS" \
  --arg before_rc "$BEFORE_RC_ID" \
  --argjson before_qsos "$BEFORE_QSOS" \
  --arg forced_rc "$ROUTING_CONFIG_DN" \
  --arg queue_source "$QUEUE_SOURCE" \
  --arg queue_created "$QUEUE_CREATED" \
  --argjson candidate_dns "$CANDIDATE_DNS" \
  '{
    skill: "service-omni-queue-deploy",
    status: $status,
    sobject_type: $sobject,
    developer_name: $dn,
    queue_created: ($queue_created == "true"),
    queue_selection_source: $queue_source,
    candidate_queue_developer_names: $candidate_dns,
    id: $qid,
    queue_routing_config_id: (if $after_rc == "null" or $after_rc == "" then null else $after_rc end),
    queue_routing_config_developer_name: (if $after_rc_dn == "null" or $after_rc_dn == "" then null else $after_rc_dn end),
    queue_routing_config_source: (if $forced_rc == "" then "discovered" else "forced" end),
    queue_sobjects: $after_qsos,
    before: {
      existed: true,
      queue_routing_config_id: (if $before_rc == "null" then null else $before_rc end),
      queue_sobjects: $before_qsos
    },
    manual_actions: [],
    blocking_issue: null
  }'
