#!/usr/bin/env bash
# deploy-and-report.sh - deploy + verify an Omni routing Flow: autolaunched dryRun smoke flow (default, verified via Actions REST) or record-triggered production flow (--trigger, token-resolved, optional --runtime-proof). Args, token resolution, exit codes: SKILL.md.

set -euo pipefail

# Escape the five XML predefined entities so a ServiceChannel MasterLabel with & < > " ' cannot
# corrupt the flow XML when substituted into the asset below.
xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"; s="${s//\'/&apos;}"
  printf '%s' "$s"
}
# Escape sed replacement metacharacters (\ & and the | delimiter) so an escaped value is inserted
# literally by the sed substitution.
sed_repl_escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash deploy-and-report.sh <org-alias> [flow_developer_name] [--skip-invoke] [--target Case|VoiceCall] [--trigger] [--runtime-proof]"}' >&2
  exit 1
fi

# --- Parse flags out of the arg list, leaving positional args intact ---
SKIP_INVOKE="false"
TRIGGER_MODE="false"
RUNTIME_PROOF="false"
# --require-proof (or OMNI_RUNTIME_PROOF_REQUIRED=1): make runtime routing proof mandatory (a missing
# PendingServiceRouting|AgentWork blocks instead of fail-soft); the Voice release gate. Implies --runtime-proof.
REQUIRE_PROOF="${OMNI_RUNTIME_PROOF_REQUIRED:-0}"
[ "$REQUIRE_PROOF" = "1" ] && { REQUIRE_PROOF="true"; RUNTIME_PROOF="true"; TRIGGER_MODE="true"; } || REQUIRE_PROOF="false"
TARGET="Case"
# Routing type for the record-triggered production flow: QueueBased (default, backward-compatible) or
# SkillsBased. SkillsBased selects the skills-based flow variant (${FLOW_DN}.SkillsBased.flow-meta.xml)
# and REQUIRES a non-null skillOption - a null skillOption makes the platform routeWork action NPE and
# roll back the triggering insert (W-24069761).
ROUTING_TYPE="${OMNI_ROUTING_TYPE:-QueueBased}"
# skillOption for SkillsBased routing (ignored for QueueBased). RunSBRRules (default) makes the platform
# evaluate the org's WorkSkillRouting rules server-side and attach matching SkillRequirement rows;
# DefineSkillRequirements uses only skills the flow passes; Both does both. Closed set - mirrors
# OmniFlowConstants.SkillOption in core.
SKILL_OPTION="${OMNI_SKILL_OPTION:-RunSBRRules}"
SKILL_OPTION_EXPLICIT="false"
POSITIONAL=()
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-invoke)    SKIP_INVOKE="true" ;;
    --trigger)        TRIGGER_MODE="true" ;;
    --runtime-proof)  RUNTIME_PROOF="true"; TRIGGER_MODE="true" ;;
    --require-proof)  REQUIRE_PROOF="true"; RUNTIME_PROOF="true"; TRIGGER_MODE="true" ;;
    --target)         shift; TARGET="${1:-Case}" ;;
    --target=*)       TARGET="${1#*=}" ;;
    --routing-type)   shift; ROUTING_TYPE="${1:-}" ;;
    --routing-type=*) ROUTING_TYPE="${1#*=}" ;;
    --skill-option)   shift; SKILL_OPTION="${1:-}"; SKILL_OPTION_EXPLICIT="true" ;;
    --skill-option=*) SKILL_OPTION="${1#*=}"; SKILL_OPTION_EXPLICIT="true" ;;
    *)                POSITIONAL+=("$1") ;;
  esac
  shift
done
set -- "${POSITIONAL[@]}"

ORG="$1"

case "$TARGET" in
  Case)      DEFAULT_SMOKE_FLOW="Omni_Route_Cases";      DEFAULT_TRIGGER_FLOW="Omni_Route_Case_Trigger";      DEFAULT_SC_DEVNAME="Cases" ;;
  VoiceCall) DEFAULT_SMOKE_FLOW="Omni_Route_VoiceCalls"; DEFAULT_TRIGGER_FLOW="Omni_Route_VoiceCall_Trigger"; DEFAULT_SC_DEVNAME="sfdc_phone" ;;
  *) echo "{\"error\":\"Invalid --target '$TARGET'. Supported: Case, VoiceCall\"}" >&2; exit 2 ;;
esac

case "$ROUTING_TYPE" in
  QueueBased|SkillsBased) ;;
  *) echo "{\"error\":\"Invalid --routing-type '$ROUTING_TYPE'. Supported: QueueBased, SkillsBased\"}" >&2; exit 2 ;;
esac
# 761 guard: a SkillsBased routeWork with a null/invalid skillOption NPEs in the platform action and
# rolls back the triggering insert. Refuse to emit one - the skill never ships a null skillOption.
if [ "$ROUTING_TYPE" = "SkillsBased" ]; then
  case "$SKILL_OPTION" in
    RunSBRRules|DefineSkillRequirements|Both) ;;
    "") echo "{\"error\":\"routing-type SkillsBased requires a non-empty --skill-option (RunSBRRules|DefineSkillRequirements|Both). Refusing to deploy a SkillsBased routeWork flow with a null skillOption: it would NPE in the platform action and roll back the triggering insert (W-24069761).\"}" >&2; exit 2 ;;
    *)  echo "{\"error\":\"Invalid --skill-option '$SKILL_OPTION'. Supported: RunSBRRules, DefineSkillRequirements, Both\"}" >&2; exit 2 ;;
  esac
fi

if [ "$ROUTING_TYPE" = "QueueBased" ] && [ "$SKILL_OPTION_EXPLICIT" = "true" ]; then
  echo '{"error":"--skill-option is valid only with --routing-type SkillsBased."}' >&2
  exit 2
fi

# Flow to operate on: explicit positional wins; else target+mode default.
if [ "$TRIGGER_MODE" = "true" ]; then
  FLOW_DN="${2:-$DEFAULT_TRIGGER_FLOW}"
else
  FLOW_DN="${2:-$DEFAULT_SMOKE_FLOW}"
fi

if ! [[ "$FLOW_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid flow_developer_name '$FLOW_DN'. Must start with a letter, only A-Z a-z 0-9 _ (max 80).\"}" >&2
  exit 1
fi

if ! [[ "$ORG" =~ ^[A-Za-z0-9._@-]{1,128}$ ]]; then
  echo "{\"error\":\"Invalid org alias '$ORG'.\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

# Write guard: deploys Flow metadata, so self-enforce the production-org guard (directly invokable).
ORG_GUARD_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || {
  echo "{\"error\":\"Failed to query Organization for safe_to_write guard: $(printf '%s' "$ORG_GUARD_JSON" | head -c 300)\"}" >&2
  exit 1
}
IS_SANDBOX=$(echo "$ORG_GUARD_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_GUARD_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_GUARD_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  echo "{\"skill\":\"service-omni-routing-flow-deploy\",\"status\":\"blocked\",\"blocking_issue\":\"Refusing to deploy Flow metadata to a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org.\",\"safe_to_write\":false}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"
FLOW_XML="$ASSETS_DIR/force-app/main/default/flows/${FLOW_DN}.flow-meta.xml"
# Template the deploy reads from. The SkillsBased trigger variant is a sibling asset carrying
# routingType=SkillsBased + a non-null skillOption; QueueBased and the smoke/dryRun flows use the base
# asset. Either way the temp copy is written as ${FLOW_DN}.flow-meta.xml, so the deployed DeveloperName
# stays $FLOW_DN (the SkillsBased flow REPLACES the QueueBased one - never two triggers on one object).
TEMPLATE_XML="$FLOW_XML"
if [ "$TRIGGER_MODE" = "true" ] && [ "$ROUTING_TYPE" = "SkillsBased" ]; then
  TEMPLATE_XML="$ASSETS_DIR/force-app/main/default/flows/${FLOW_DN}.SkillsBased.flow-meta.xml"
fi

if [ ! -f "$ASSETS_DIR/sfdx-project.json" ]; then
  echo "{\"error\":\"Assets DX project not found at $ASSETS_DIR\"}" >&2
  exit 1
fi

if [ ! -f "$TEMPLATE_XML" ]; then
  echo "{\"error\":\"Flow asset not found at $TEMPLATE_XML. Add the .flow-meta.xml file, or pick a different flow_developer_name / --routing-type.\"}" >&2
  exit 1
fi

# Resolve the org's API version so we hit the right Actions REST endpoint. The Flow metadata
# is written at 66.0 but the org may serve a newer API - the endpoint takes any recent version.
API_VERSION=$(sf org display --target-org "$ORG" --json 2>/dev/null \
  | jq -r '.result.apiVersion // "66.0"')
if ! [[ "$API_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
  API_VERSION="66.0"
fi

# TRIGGER MODE - deploy the record-triggered production flow (token-resolved), then optionally prove
# routing at runtime. Self-contained: emits its own report and exits.
if [ "$TRIGGER_MODE" = "true" ]; then
  # Cleanup on EVERY exit path: remove the temp DX project + delete any throwaway proof record.
  TWORK=""
  CLEANUP_RECORD_ID=""
  _rf_cleanup() {
    [ -n "$TWORK" ] && rm -rf "$TWORK" 2>/dev/null || true
    if [ -n "$CLEANUP_RECORD_ID" ]; then
      sf data delete record --target-org "$ORG" --sobject "$TARGET" --record-id "$CLEANUP_RECORD_ID" >/dev/null 2>&1 || true
    fi
  }
  trap _rf_cleanup EXIT

  trigger_blocked() {
    jq -n --arg flow "$FLOW_DN" --arg target "$TARGET" --arg msg "$1" \
      '{skill:"service-omni-routing-flow-deploy", status:"blocked", mode:"record_triggered",
        target:$target, flow_developer_name:$flow, flow_active:false,
        runtime_proof:{attempted:false,success:false,reason:"blocked_before_proof"},
        manual_actions:[], blocking_issue:$msg}'
    exit 1
  }

  # --- Resolve the Queue bound to the target sObject ---
  QDN="${QUEUE_DEVELOPER_NAME:-}"
  if [ -n "$QDN" ] && ! [[ "$QDN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    trigger_blocked "Invalid QUEUE_DEVELOPER_NAME '$QDN'."
  fi
  if [ -z "$QDN" ]; then
    QSO=$(sf data query --target-org "$ORG" \
      --query "SELECT QueueId, Queue.DeveloperName FROM QueueSobject WHERE SobjectType='$TARGET' ORDER BY Queue.DeveloperName" --json 2>/dev/null)
    QSO_DNS=$(echo "$QSO" | jq -c '[.result.records[].Queue.DeveloperName] | unique' 2>/dev/null || echo '[]')
    QSO_N=$(echo "$QSO_DNS" | jq 'length' 2>/dev/null || echo 0)
    if [ "$QSO_N" = "0" ]; then
      trigger_blocked "No queue is bound to '$TARGET'. Run service-omni-queue-deploy --create-if-missing first, or set QUEUE_DEVELOPER_NAME."
    elif [ "$QSO_N" != "1" ]; then
      trigger_blocked "Multiple queues bound to '$TARGET' ($QSO_DNS). Set QUEUE_DEVELOPER_NAME to disambiguate."
    fi
    QDN=$(echo "$QSO_DNS" | jq -r '.[0]')
  fi
  Q_JSON=$(sf data query --target-org "$ORG" \
    --query "SELECT Id, QueueRoutingConfigId FROM Group WHERE DeveloperName='$QDN' AND Type='Queue'" --json 2>/dev/null)
  QUEUE_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].Id // empty')
  [ -z "$QUEUE_ID" ] && trigger_blocked "Queue '$QDN' not found on org."
  QUEUE_RC_ID=$(echo "$Q_JSON" | jq -r '.result.records[0].QueueRoutingConfigId // empty')

  # --- Resolve the QueueRoutingConfig ---
  RC_DN="${ROUTING_CONFIG_DEVELOPER_NAME:-}"
  if [ -n "$RC_DN" ] && ! [[ "$RC_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    trigger_blocked "Invalid ROUTING_CONFIG_DEVELOPER_NAME '$RC_DN'."
  fi
  if [ -z "$RC_DN" ] && [ -n "$QUEUE_RC_ID" ]; then
    RC_DN=$(sf data query --target-org "$ORG" \
      --query "SELECT DeveloperName FROM QueueRoutingConfig WHERE Id='$QUEUE_RC_ID'" --json 2>/dev/null \
      | jq -r '.result.records[0].DeveloperName // empty')
  fi
  if [ -z "$RC_DN" ]; then
    case "$TARGET" in
      VoiceCall) RC_DN="Voice_Routing_Config" ;;
      *)         RC_DN="Case_Routing_Config" ;;
    esac
  fi
  RC_ID=$(sf data query --target-org "$ORG" \
    --query "SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='$RC_DN'" --json 2>/dev/null \
    | jq -r '.result.records[0].Id // empty')
  [ -z "$RC_ID" ] && trigger_blocked "QueueRoutingConfig '$RC_DN' does not exist. Run service-omni-queue-routing-config-deploy (QRC_ROUTING_TARGET=$TARGET) first, or set ROUTING_CONFIG_DEVELOPER_NAME."

  # --- Resolve the ServiceChannel (Tooling API), FAIL CLOSED if absent ---
  # The flow embeds the ServiceChannel Id in routeWork; an empty id would deploy a flow routing
  # nothing. The coordinator passes the discovered channel via SERVICE_CHANNEL_DEVELOPER_NAME.
  SC_DN="${SERVICE_CHANNEL_DEVELOPER_NAME:-$DEFAULT_SC_DEVNAME}"
  if [ -n "$SC_DN" ] && ! [[ "$SC_DN" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
    trigger_blocked "Invalid SERVICE_CHANNEL_DEVELOPER_NAME '$SC_DN'."
  fi
  SC_TOOLING=$(sf data query --target-org "$ORG" --use-tooling-api \
    --query "SELECT Id, MasterLabel FROM ServiceChannel WHERE DeveloperName='$SC_DN'" --json 2>/dev/null || echo '{}')
  SC_ID=$(echo "$SC_TOOLING" | jq -r '.result.records[0].Id // empty')
  SC_LABEL=$(echo "$SC_TOOLING" | jq -r '.result.records[0].MasterLabel // empty')
  if [ -z "$SC_ID" ]; then
    trigger_blocked "ServiceChannel '$SC_DN' not found on org (Tooling API returned no row). For $TARGET run service-omni-service-channel-configure (sobject_type=$TARGET) first - the standard Voice channel is 'sfdc_phone' - or set SERVICE_CHANNEL_DEVELOPER_NAME to an existing channel. Refusing to deploy a flow with an unresolved ServiceChannel."
  fi
  [ -z "$SC_LABEL" ] && SC_LABEL="$SC_DN"

  # --- PLAN_ONLY: report the resolution, do not write ---
  if [ "${PLAN_ONLY:-}" = "1" ]; then
    jq -n --arg flow "$FLOW_DN" --arg target "$TARGET" --arg q "$QDN" --arg rc "$RC_DN" --arg sc "$SC_DN" \
      --arg routing_type "$ROUTING_TYPE" --arg skill_option "$SKILL_OPTION" \
      '{skill:"service-omni-routing-flow-deploy", status:"action_needed", plan_mode:true, mode:"record_triggered",
        target:$target, flow_developer_name:$flow, routing_type:$routing_type,
        skill_option:(if $routing_type=="SkillsBased" then $skill_option else null end),
        resolved:{queue:$q, routing_config:$rc, service_channel:$sc},
        plan_detail:("Would deploy record-triggered \($routing_type) flow \($flow) binding queue \($q), QRC \($rc), channel \($sc)" + (if $routing_type=="SkillsBased" then " with skillOption \($skill_option)." else "." end)),
        manual_actions:[], blocking_issue:null}'
    exit 0
  fi

  # --- Idempotency guard with stale-binding detection ---
  # A Flow deploy always mints a new version, so re-runs would grow the version count. If an active
  # version exists AND its embedded queue/QRC/channel Ids still match, report "reused" and skip;
  # if the bindings have drifted, redeploy. OMNI_FLOW_FORCE=1 always redeploys.
  EXISTING_ACTIVE=$(sf data query --target-org "$ORG" --use-tooling-api \
    --query "SELECT Id FROM Flow WHERE Definition.DeveloperName='$FLOW_DN' AND Status='Active' LIMIT 1" --json 2>/dev/null \
    | jq -r '.result.records[0].Id // empty')
  BINDINGS_MATCH="false"
  if [ -n "$EXISTING_ACTIVE" ]; then
    RWORK="$(mktemp -d)"
    cp "$ASSETS_DIR/sfdx-project.json" "$RWORK/sfdx-project.json"
    mkdir -p "$RWORK/force-app/main/default"
    ( cd "$RWORK" && sf project retrieve start --target-org "$ORG" --metadata "Flow:${FLOW_DN}" --json >/dev/null 2>&1 || true )
    ACTIVE_XML=$(find "$RWORK" -name "${FLOW_DN}.flow-meta.xml" 2>/dev/null | head -1)
    if [ -n "$ACTIVE_XML" ] && [ -f "$ACTIVE_XML" ]; then
      # Resource bindings and routing semantics must all match. Without the routing-mode checks, a
      # QueueBased flow with current IDs could be incorrectly reused for a SkillsBased request.
      if grep -qF "$QUEUE_ID" "$ACTIVE_XML" 2>/dev/null \
         && grep -qF "$RC_ID" "$ACTIVE_XML" 2>/dev/null \
         && grep -qF "$SC_ID" "$ACTIVE_XML" 2>/dev/null \
         && grep -qF "<stringValue>${ROUTING_TYPE}</stringValue>" "$ACTIVE_XML" 2>/dev/null \
         && { [ "$ROUTING_TYPE" != "SkillsBased" ] \
              || grep -qF "<stringValue>${SKILL_OPTION}</stringValue>" "$ACTIVE_XML" 2>/dev/null; }; then
        BINDINGS_MATCH="true"
      fi
    fi
    rm -rf "$RWORK"
  fi
  if [ -n "$EXISTING_ACTIVE" ] && [ "$BINDINGS_MATCH" = "true" ] && [ "${OMNI_FLOW_FORCE:-0}" != "1" ]; then
    TRIG_STATUS="reused"
    TSTATE="Unchanged"
  else
  # --- Substitute tokens into a temp copy of the asset and deploy ---
  TWORK="$(mktemp -d)"
  mkdir -p "$TWORK/force-app/main/default/flows"
  cp "$ASSETS_DIR/sfdx-project.json" "$TWORK/sfdx-project.json"
  SC_LABEL_SED="$(sed_repl_escape "$(xml_escape "$SC_LABEL")")"
  sed \
    -e "s|__SERVICE_CHANNEL_ID__|${SC_ID}|g" \
    -e "s|__SERVICE_CHANNEL_DEVNAME__|${SC_DN}|g" \
    -e "s|__SERVICE_CHANNEL_LABEL__|${SC_LABEL_SED}|g" \
    -e "s|__ROUTING_CONFIG_ID__|${RC_ID}|g" \
    -e "s|__QUEUE_ID__|${QUEUE_ID}|g" \
    -e "s|__SKILL_OPTION__|${SKILL_OPTION}|g" \
    "$TEMPLATE_XML" > "$TWORK/force-app/main/default/flows/${FLOW_DN}.flow-meta.xml"

  TDEPLOY=$(cd "$TWORK" && sf project deploy start --target-org "$ORG" --metadata "Flow:${FLOW_DN}" --json 2>/dev/null || true)
  TDEPLOY_OK=$(echo "$TDEPLOY" | jq -r '.result.success // false' 2>/dev/null)
  if [ "$TDEPLOY_OK" != "true" ]; then
    TERR=$(echo "$TDEPLOY" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
    [ -z "$TERR" ] || [ "$TERR" = "null" ] && TERR=$(echo "$TDEPLOY" | jq -r '.message // "Unknown deploy error"' 2>/dev/null)
    trigger_blocked "Record-triggered flow deploy failed: $TERR"
  fi
  TSTATE=$(echo "$TDEPLOY" | jq -r --arg fn "$FLOW_DN" '.result.files[] | select(.fullName==$fn and .type=="Flow") | .state' 2>/dev/null | head -1)
  TSTATE="${TSTATE:-unknown}"
  TRIG_STATUS="reused"
  case "$TSTATE" in Created) TRIG_STATUS="created";; Changed) TRIG_STATUS="updated";; Unchanged) TRIG_STATUS="reused";; *) trigger_blocked "Deploy ok but Flow state unrecognized ('$TSTATE').";; esac
  fi

  # --- Round-trip active-version proof ---
  # Component state only proves the deploy transaction; a flow with no active version never fires.
  # Prefer FlowDefinitionView, then fall back to the Tooling Flow row because an unrelated malformed
  # managed-package definition can make FlowDefinitionView fail for the entire org.
  TRIG_ACTIVE_VER=$(sf data query --target-org "$ORG" \
    --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='$FLOW_DN'" --json 2>/dev/null \
    | jq -r '.result.records[0].ActiveVersionId // ""' 2>/dev/null || echo "")
  if [ -z "$TRIG_ACTIVE_VER" ] || [ "$TRIG_ACTIVE_VER" = "null" ]; then
    TRIG_ACTIVE_VER=$(sf data query --target-org "$ORG" --use-tooling-api \
      --query "SELECT Id FROM Flow WHERE Definition.DeveloperName='$FLOW_DN' AND Status='Active' LIMIT 1" --json 2>/dev/null \
      | jq -r '.result.records[0].Id // ""' 2>/dev/null || echo "")
  fi
  if [ -z "$TRIG_ACTIVE_VER" ] || [ "$TRIG_ACTIVE_VER" = "null" ]; then
    trigger_blocked "Record-triggered flow '$FLOW_DN' deployed (state=$TSTATE), but neither FlowDefinitionView nor the Tooling Flow query found an active version, so routing would not fire. Re-run, or activate the flow in Setup → Flows."
  fi

  # --- Runtime proof (optional): fire the trigger and look for a PendingServiceRouting/AgentWork ---
  RP_ATTEMPTED="false"; RP_SUCCESS="false"; RP_REASON=""; RP_RECORD_ID=""; RP_PSR="null"; RP_AW="null"
  # SkillsBased acceptance signal: SkillRequirement rows the platform attached to the PSR (the exact
  # thing that was missing when routeWork hardcoded QueueBased - W-24069467).
  RP_SKILLREQS="null"; RP_SKILLREQ_COUNT="0"
  if [ "$RUNTIME_PROOF" = "true" ]; then
    RP_ATTEMPTED="true"
    case "$TARGET" in
      Case)      REC=$(sf data create record --target-org "$ORG" --sobject Case --values "Subject='Omni routing proof' Status='New' Origin='Phone'" --json 2>/dev/null || true) ;;
      VoiceCall) REC=$(sf data create record --target-org "$ORG" --sobject VoiceCall --values "CallType='Inbound'" --json 2>/dev/null || true) ;;
    esac
    RP_RECORD_ID=$(echo "$REC" | jq -r '.result.id // empty' 2>/dev/null)
    # Register the record for deletion on exit (trap) so the proof never leaves test data behind.
    [ -n "$RP_RECORD_ID" ] && CLEANUP_RECORD_ID="$RP_RECORD_ID"
    if [ -z "$RP_RECORD_ID" ]; then
      RP_REASON="Could not create a $TARGET record to fire the trigger: $(echo "$REC" | jq -r '.message // (.result.errors[0].message) // "unknown"' 2>/dev/null | head -c 240). On orgs without Service Cloud Voice provisioned, VoiceCall is not directly insertable - deploy is proven, runtime proof is not."
    else
      # Poll for PendingServiceRouting then AgentWork (async). Cadence env-tunable
      # (OMNI_PROOF_POLL_TRIES / OMNI_PROOF_POLL_SLEEP); defaults ~30s.
      RP_TRIES="${OMNI_PROOF_POLL_TRIES:-6}"
      RP_SLEEP="${OMNI_PROOF_POLL_SLEEP:-5}"
      for _ in $(seq 1 "$RP_TRIES"); do
        PSR=$(sf data query --target-org "$ORG" \
          --query "SELECT Id, IsReadyForRouting, RoutingModel FROM PendingServiceRouting WHERE WorkItemId='$RP_RECORD_ID' ORDER BY CreatedDate DESC LIMIT 1" --json 2>/dev/null || echo '{}')
        if [ "$(echo "$PSR" | jq -r '.result.totalSize // 0')" != "0" ]; then
          RP_PSR=$(echo "$PSR" | jq -c '.result.records[0]')
          if [ "$ROUTING_TYPE" = "SkillsBased" ]; then
            _psr_id=$(echo "$PSR" | jq -r '.result.records[0].Id')
            # SkillRequirement has no SkillLevel column; its skill-strength field is SkillNumber.
            SREQ=$(sf data query --target-org "$ORG" \
              --query "SELECT Id, SkillId, SkillNumber, IsAdditionalSkill, SkillPriority FROM SkillRequirement WHERE RelatedRecordId='$_psr_id'" --json 2>/dev/null || true)
            # A failed query prints error JSON to stdout THEN exits non-zero, so a `|| echo '{}'`
            # fallback would concatenate two JSON values and break the downstream --argjson. Validate
            # that we captured a single well-formed value and fall back to empty otherwise.
            echo "$SREQ" | jq -e . >/dev/null 2>&1 || SREQ='{}'
            RP_SKILLREQ_COUNT=$(echo "$SREQ" | jq -r '.result.totalSize // 0' 2>/dev/null || echo 0)
            RP_SKILLREQS=$(echo "$SREQ" | jq -c '.result.records // []' 2>/dev/null || echo '[]')
            if [ "$RP_SKILLREQ_COUNT" -gt 0 ]; then
              RP_SUCCESS="true"
              break
            fi
          else
            RP_SUCCESS="true"
            break
          fi
        fi
        AW=$(sf data query --target-org "$ORG" \
          --query "SELECT Id, Status FROM AgentWork WHERE WorkItemId='$RP_RECORD_ID' ORDER BY CreatedDate DESC LIMIT 1" --json 2>/dev/null || echo '{}')
        if [ "$(echo "$AW" | jq -r '.result.totalSize // 0')" != "0" ]; then
          RP_AW=$(echo "$AW" | jq -c '.result.records[0]')
          if [ "$ROUTING_TYPE" != "SkillsBased" ]; then
            RP_SUCCESS="true"
            break
          fi
        fi
        sleep "$RP_SLEEP"
      done
      if [ "$RP_SUCCESS" != "true" ] && [ "$ROUTING_TYPE" = "SkillsBased" ] \
         && [ "$RP_PSR" != "null" ] && [ "$RP_SKILLREQ_COUNT" = "0" ]; then
        RP_REASON="A PendingServiceRouting row appeared for record $RP_RECORD_ID, but it has no SkillRequirement rows. SkillsBased runtime proof requires at least one SkillRequirement produced by the active WorkSkillRouting rule."
      elif [ "$RP_SUCCESS" != "true" ]; then
        RP_REASON="Record $RP_RECORD_ID created but no PendingServiceRouting/AgentWork appeared within the proof window. The flow deployed and is Active; routing may require an online agent, a configured Contact Center, or more time."
      fi
    fi
  fi

  # Mandatory-proof gate: when proof is required, a missing PendingServiceRouting|AgentWork blocks.
  if [ "$REQUIRE_PROOF" = "true" ] && [ "$RP_SUCCESS" != "true" ]; then
    jq -n \
      --arg flow "$FLOW_DN" --arg target "$TARGET" --arg state "$TSTATE" --arg active_ver "$TRIG_ACTIVE_VER" \
      --arg routing_type "$ROUTING_TYPE" --arg skill_option "$SKILL_OPTION" \
      --arg q "$QDN" --arg qid "$QUEUE_ID" --arg rc "$RC_DN" --arg rcid "$RC_ID" --arg sc "$SC_DN" --arg scid "$SC_ID" \
      --arg rp_rec "$RP_RECORD_ID" --argjson rp_psr "$RP_PSR" --argjson rp_aw "$RP_AW" --arg rp_reason "$RP_REASON" \
      --argjson rp_skillreqs "$RP_SKILLREQS" --arg rp_skillreq_count "$RP_SKILLREQ_COUNT" \
      '{skill:"service-omni-routing-flow-deploy", status:"blocked", mode:"record_triggered", target:$target,
        flow_developer_name:$flow, flow_state:$state, flow_active:true, flow_active_version_id:$active_ver,
        routing_type:$routing_type, skill_option:(if $routing_type=="SkillsBased" then $skill_option else null end),
        resolved:{queue:{developer_name:$q,id:$qid}, routing_config:{developer_name:$rc,id:$rcid}, service_channel:{developer_name:$sc,id:(if $scid=="" then null else $scid end)}},
        runtime_proof:{attempted:true, required:true, success:false, record_id:(if $rp_rec=="" then null else $rp_rec end), pending_service_routing:$rp_psr, agent_work:$rp_aw, skill_requirement_count:($rp_skillreq_count|tonumber), skill_requirements:(if $routing_type=="SkillsBased" then $rp_skillreqs else null end), reason:(if $rp_reason=="" then null else $rp_reason end)},
        manual_actions:[], blocking_issue:("Runtime routing proof REQUIRED but not observed: " + (if $rp_reason=="" then "no PendingServiceRouting/AgentWork appeared" else $rp_reason end) + " (VoiceCall runtime proof needs a provisioned Contact Center + an online agent).")}'
    exit 1
  fi

  jq -n \
    --arg status "$TRIG_STATUS" --arg flow "$FLOW_DN" --arg target "$TARGET" --arg state "$TSTATE" --arg active_ver "$TRIG_ACTIVE_VER" \
    --arg routing_type "$ROUTING_TYPE" --arg skill_option "$SKILL_OPTION" \
    --arg q "$QDN" --arg qid "$QUEUE_ID" --arg rc "$RC_DN" --arg rcid "$RC_ID" --arg sc "$SC_DN" --arg scid "$SC_ID" \
    --arg rp_attempted "$RP_ATTEMPTED" --arg rp_success "$RP_SUCCESS" --arg rp_reason "$RP_REASON" \
    --arg rp_required "$REQUIRE_PROOF" \
    --arg rp_rec "$RP_RECORD_ID" --argjson rp_psr "$RP_PSR" --argjson rp_aw "$RP_AW" \
    --argjson rp_skillreqs "$RP_SKILLREQS" --arg rp_skillreq_count "$RP_SKILLREQ_COUNT" \
    '{
      skill:"service-omni-routing-flow-deploy",
      status:$status,
      mode:"record_triggered",
      target:$target,
      flow_developer_name:$flow,
      flow_state:$state,
      flow_active:true,
      flow_active_version_id:$active_ver,
      routing_type:$routing_type,
      skill_option:(if $routing_type=="SkillsBased" then $skill_option else null end),
      resolved:{queue:{developer_name:$q, id:$qid}, routing_config:{developer_name:$rc, id:$rcid}, service_channel:{developer_name:$sc, id:(if $scid=="" then null else $scid end)}},
      runtime_proof:{
        attempted:($rp_attempted=="true"),
        required:($rp_required=="true"),
        success:($rp_success=="true"),
        record_id:(if $rp_rec=="" then null else $rp_rec end),
        pending_service_routing:$rp_psr,
        agent_work:$rp_aw,
        skill_requirement_count:($rp_skillreq_count|tonumber),
        skill_requirements:(if $routing_type=="SkillsBased" then $rp_skillreqs else null end),
        reason:(if $rp_reason=="" then null else $rp_reason end)
      },
      manual_actions:[],
      blocking_issue:null
    }'
  exit 0
fi

# Deploy - explicit --metadata (not --source-dir) so a sibling metadata file can't piggyback.
DEPLOY_JSON=$(cd "$ASSETS_DIR" && sf project deploy start --target-org "$ORG" \
  --metadata "Flow:${FLOW_DN}" \
  --json 2>/dev/null || true)

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // null'  2>/dev/null)

translate_deploy_error() {
  local raw="$1"
  case "$raw" in
    *INVALID_TYPE*"Flow"*)
      echo "Flow metadata type not enabled on this org (unusual - usually indicates the org edition doesn't include Flow Builder)."
      ;;
    *"Flow.*is not valid for this API version"*|*"API version"*)
      echo "Flow XML apiVersion or asset version mismatch. Confirm assets/force-app/main/default/flows/${FLOW_DN}.flow-meta.xml <apiVersion> is <= the org's current API version ($API_VERSION)."
      ;;
    *"Invalid element name"*|*"was not expected"*)
      echo "Flow XML schema mismatch. The Flow metadata schema is strict; check element ordering and spelling against v66 Metadata API docs."
      ;;
    *INSUFFICIENT_ACCESS*)
      echo "Executing user lacks Metadata API deploy permissions. Re-authenticate as a System Administrator or grant Author Apex + Manage Flows."
      ;;
    *)
      echo "$raw"
      ;;
  esac
}

if [ "$DEPLOY_SUCCESS" != "true" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  if [ -z "$FAILURES" ] || [ "$FAILURES" = "null" ]; then
    FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  fi
  FRIENDLY=$(translate_deploy_error "$FAILURES")

  jq -n \
    --arg deploy_id "$DEPLOY_ID" \
    --arg flow "$FLOW_DN" \
    --arg blocking "$FRIENDLY" \
    --arg raw "$FAILURES" \
    '{
      skill: "service-omni-routing-flow-deploy",
      status: "blocked",
      flow_developer_name: $flow,
      flow_state: "not_deployed",
      flow_active: false,
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      invocation_smoke_test: {attempted: false, success: false, reason: "deploy_failed"},
      manual_actions: [],
      blocking_issue: $blocking,
      raw_error: $raw
    }'
  exit 1
fi

FLOW_STATE=$(echo "$DEPLOY_JSON" | jq -r --arg fn "$FLOW_DN" \
  '.result.files[] | select(.fullName == $fn and .type == "Flow") | .state' 2>/dev/null | head -1)
FLOW_STATE="${FLOW_STATE:-unknown}"

case "$FLOW_STATE" in
  Created|Changed|Unchanged) ;;
  *)
    jq -n \
      --arg flow "$FLOW_DN" \
      --arg st "$FLOW_STATE" \
      --arg deploy_id "$DEPLOY_ID" \
      '{
        skill: "service-omni-routing-flow-deploy",
        status: "blocked",
        flow_developer_name: $flow,
        flow_state: $st,
        flow_active: false,
        deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
        invocation_smoke_test: {attempted: false, success: false, reason: "unrecognized_component_state"},
        manual_actions: [],
        blocking_issue: ("Deploy reported success overall but Flow component has an unrecognized/absent state \"" + $st + "\" (expected Created, Changed, or Unchanged).")
      }'
    exit 1
    ;;
esac

# Post-verify #1: retrieve the deployed Flow and confirm <status>Active</status> (a flow can deploy
# in Draft/Obsolete - a silent failure, since autolaunched flows must be Active to be CLI-invocable).
VERIFY_WORK="$(mktemp -d)"
trap 'rm -rf "$VERIFY_WORK"' EXIT
cp "$ASSETS_DIR/sfdx-project.json" "$VERIFY_WORK/sfdx-project.json"
mkdir -p "$VERIFY_WORK/force-app/main/default"
# Retrieve for its side effect (writes the flow XML); verified by inspecting the file below.
( cd "$VERIFY_WORK" && sf project retrieve start --target-org "$ORG" \
  --metadata "Flow:${FLOW_DN}" --json >/dev/null 2>&1 || true )
RETRIEVED_XML=$(find "$VERIFY_WORK" -name "${FLOW_DN}.flow-meta.xml" 2>/dev/null | head -1)

FLOW_ACTIVE="unverified"
if [ -n "$RETRIEVED_XML" ] && [ -f "$RETRIEVED_XML" ]; then
  if grep -qE "<status>Active</status>" "$RETRIEVED_XML"; then
    FLOW_ACTIVE="true"
  else
    FLOW_ACTIVE="false"
  fi
fi

if [ "$FLOW_ACTIVE" != "true" ]; then
  if [ "$FLOW_ACTIVE" = "false" ]; then
    BLOCK_MSG="Flow deployed but not Active on post-verify (the retrieved metadata does not carry <status>Active</status>). The flow XML must declare <status>Active</status> for autolaunched CLI invocation to work."
  else
    BLOCK_MSG="Flow deployed but the Active-status verification could not be performed (retrieve returned no Flow XML - inconclusive)."
  fi
  jq -n \
    --arg flow "$FLOW_DN" \
    --arg st "$FLOW_STATE" \
    --arg deploy_id "$DEPLOY_ID" \
    --arg active "$FLOW_ACTIVE" \
    --arg msg "$BLOCK_MSG" \
    '{
      skill: "service-omni-routing-flow-deploy",
      status: "blocked",
      flow_developer_name: $flow,
      flow_state: $st,
      flow_active: ($active == "true"),
      deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
      invocation_smoke_test: {attempted: false, success: false, reason: "flow_not_active"},
      manual_actions: [],
      blocking_issue: $msg
    }'
  exit 1
fi

# Post-verify #2: invoke the flow via Actions REST with dryRun=true (proves CLI-executability).
# POST /services/data/vXX.X/actions/custom/flow/<FlowDN>, body {"inputs":[{"dryRun":true}]};
# success = [0].isSuccess && [0].outputValues.dryRunOk.
INVOKE_ATTEMPTED="false"
INVOKE_SUCCESS="false"
INVOKE_REASON=""
INVOKE_RAW="{}"
INVOKE_DRY_RUN_OK="false"

if [ "$SKIP_INVOKE" != "true" ]; then
  INVOKE_ATTEMPTED="true"
  INVOKE_ENDPOINT="/services/data/v${API_VERSION}/actions/custom/flow/${FLOW_DN}"
  INVOKE_BODY='{"inputs":[{"dryRun":true}]}'

  INVOKE_RAW=$(sf api request rest \
    --method POST \
    --target-org "$ORG" \
    --body "$INVOKE_BODY" \
    "$INVOKE_ENDPOINT" \
    2>&1 || true)

  # sf api request rest (beta) prints a warning line before the JSON body; strip everything up to
  # the first line starting with [ or { - that's the actual body.
  INVOKE_JSON=$(printf '%s' "$INVOKE_RAW" | awk '/^[[{]/,0')

  # Parse the stripped payload (raw array for Actions API, or an error-wrapping object).
  if echo "$INVOKE_JSON" | jq -e '.' >/dev/null 2>&1; then
    IS_SUCCESS=$(echo "$INVOKE_JSON" | jq -r 'if type == "array" then .[0].isSuccess else .isSuccess // false end' 2>/dev/null)
    INVOKE_DRY_RUN_OK=$(echo "$INVOKE_JSON" | jq -r 'if type == "array" then (.[0].outputValues.dryRunOk // false) else (.outputValues.dryRunOk // false) end' 2>/dev/null)
    if [ "$IS_SUCCESS" = "true" ] && [ "$INVOKE_DRY_RUN_OK" = "true" ]; then
      INVOKE_SUCCESS="true"
    else
      INVOKE_REASON=$(echo "$INVOKE_JSON" | jq -r '
        if type == "array" then
          (.[0].errors // []) | map(.message) | join("; ")
        else
          (.errors // []) | map(.message) | join("; ")
        end' 2>/dev/null)
      if [ -z "$INVOKE_REASON" ] || [ "$INVOKE_REASON" = "null" ]; then
        INVOKE_REASON="Invocation returned isSuccess=$IS_SUCCESS, dryRunOk=$INVOKE_DRY_RUN_OK (expected true/true)."
      fi
    fi
  else
    INVOKE_REASON="Actions API returned non-JSON after stripping the sf beta-warning preamble. Raw first 200 chars: $(printf '%s' "$INVOKE_RAW" | head -c 200)"
  fi

  if [ "$INVOKE_SUCCESS" != "true" ]; then
    jq -n \
      --arg flow "$FLOW_DN" \
      --arg st "$FLOW_STATE" \
      --arg deploy_id "$DEPLOY_ID" \
      --arg reason "$INVOKE_REASON" \
      --argjson raw "$(echo "$INVOKE_JSON" | jq -R -s '.' 2>/dev/null || echo '""')" \
      '{
        skill: "service-omni-routing-flow-deploy",
        status: "blocked",
        flow_developer_name: $flow,
        flow_state: $st,
        flow_active: true,
        deploy_id: (if $deploy_id == "null" or $deploy_id == "" then null else $deploy_id end),
        invocation_smoke_test: {attempted: true, success: false, reason: $reason, raw_response: $raw},
        manual_actions: [{id: "INVOCATION_FAILED", title: "Flow deployed & Active but Actions REST invocation failed. Rerun with --skip-invoke to accept deploy-only, or investigate the API response.", endpoint: ("/services/data/v" + "'"$API_VERSION"'" + "/actions/custom/flow/" + $flow)}],
        blocking_issue: ("Flow deployed and Active, but invocation via Actions REST failed: " + $reason)
      }'
    exit 1
  fi
fi

# Skill-level status.
STATUS="reused"
case "$FLOW_STATE" in
  Created)   STATUS="created"  ;;
  Changed)   STATUS="updated"  ;;
  Unchanged) STATUS="reused"   ;;
esac

jq -n \
  --arg status "$STATUS" \
  --arg flow "$FLOW_DN" \
  --arg flow_state "$FLOW_STATE" \
  --arg deploy_id "$DEPLOY_ID" \
  --arg api_ver "$API_VERSION" \
  --arg invoke_attempted "$INVOKE_ATTEMPTED" \
  --arg invoke_success "$INVOKE_SUCCESS" \
  --arg dry_run_ok "$INVOKE_DRY_RUN_OK" \
  '{
    skill: "service-omni-routing-flow-deploy",
    status: $status,
    flow_developer_name: $flow,
    flow_state: $flow_state,
    flow_active: true,
    deploy_id: $deploy_id,
    invocation_smoke_test: {
      attempted: ($invoke_attempted == "true"),
      success: ($invoke_success == "true"),
      cli_path: "actions_rest",
      endpoint: ("/services/data/v" + $api_ver + "/actions/custom/flow/" + $flow),
      dry_run_ok: ($dry_run_ok == "true")
    },
    manual_actions: [],
    blocking_issue: null
  }'
