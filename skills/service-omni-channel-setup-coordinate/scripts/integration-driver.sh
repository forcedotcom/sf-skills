#!/usr/bin/env bash
# integration-driver.sh - orchestrate the Omni-Channel skills in canonical order (--plan read-only detect, --run full execution requiring safe_to_write); array-based invocation (never eval), production-guarded. Modes, design, artifacts, exit codes: SKILL.md.

set -euo pipefail

MODE=""
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan|--dry-run)  MODE="plan"; shift ;;
    --run)             MODE="run";  shift ;;
    -h|--help)
      cat >&2 <<'EOF'
Usage:
  bash integration-driver.sh --plan <org-alias> [<count>] [<routing_targets_csv>] [<supervisor_count>]
  bash integration-driver.sh --run  <org-alias> [<count>] [<routing_targets_csv>] [<supervisor_count>]

Modes:
  --plan  Read-only. Runs only detect scripts. Emits {dry_run: true, ...}.
  --run   Executes deploys/POSTs. Enforces safe_to_write. Emits {dry_run: false, ...}.

Positional args (same for both modes):
  org-alias             sf CLI alias for the target org (required).
  count                 Number of agents / queue members expected 1..10 (default 3).
  routing_targets_csv   Comma-separated sObject list. Default "Case".
                        Supported: Case, Incident, MessagingSession, VoiceCall.
  supervisor_count      Number of supervisor users expected 1..5 (default 1).
EOF
      exit 0
      ;;
    --) shift; POSITIONAL+=("$@"); break ;;
    -*)
      echo "{\"error\":\"Unknown flag: $1. Use --plan or --run. See --help.\"}" >&2
      exit 2
      ;;
    *)
      POSITIONAL+=("$1"); shift
      ;;
  esac
done

if [ -z "$MODE" ]; then
  echo '{"error":"Must specify --plan or --run. See --help."}' >&2
  exit 2
fi

# Reset positional params; guard empty-array expansion for bash 3.2 nounset.
if [ "${#POSITIONAL[@]}" -gt 0 ]; then
  set -- "${POSITIONAL[@]}"
else
  set --
fi

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required <org-alias>. See --help."}' >&2
  exit 2
fi

ORG="$1"
COUNT="${2:-3}"
ROUTING_TARGETS_CSV="${3:-Case}"
SUPERVISOR_COUNT="${4:-1}"

# Agent/supervisor profile: a full Salesforce + Service Cloud profile (not Platform, which fails the
# ContactCenterSupervisor assignment). Override via OMNI_AGENT_PROFILE / OMNI_SUPERVISOR_PROFILE.
# Empty here means "resolve against the org after auth" (see resolve_profile below) rather than
# hard-coding "Service Cloud User", which does not exist on every org.
AGENT_PROFILE="${OMNI_AGENT_PROFILE:-}"
SUPERVISOR_PROFILE="${OMNI_SUPERVISOR_PROFILE:-}"
SUPERVISOR_CONFIG_DN="${OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME:-Omni_Supervisor}"

# A complete WorkSkillRouting mapping is an unambiguous SBR request. Infer SkillsBased so callers do
# not need a hidden second switch; an explicit OMNI_ROUTING_TYPE still wins.
ROUTING_TYPE="${OMNI_ROUTING_TYPE:-}"
WSR_INPUT_COUNT=0
for wsr_value in "${OMNI_WSR_ENTITY:-}" "${OMNI_WSR_FIELD:-}" "${OMNI_WSR_SKILL:-}" "${OMNI_WSR_VALUE:-}"; do
  [ -z "$wsr_value" ] || WSR_INPUT_COUNT=$((WSR_INPUT_COUNT + 1))
done
if [ -z "$ROUTING_TYPE" ]; then
  if [ "$WSR_INPUT_COUNT" -eq 4 ]; then
    ROUTING_TYPE="SkillsBased"
  else
    ROUTING_TYPE="QueueBased"
  fi
fi
SKILL_OPTION="${OMNI_SKILL_OPTION:-RunSBRRules}"
SBR_SKILL="${OMNI_SBR_SKILL:-${OMNI_WSR_SKILL:-}}"

case "$ROUTING_TYPE" in
  QueueBased|SkillsBased) ;;
  *) echo "{\"error\":\"Invalid OMNI_ROUTING_TYPE '$ROUTING_TYPE'. Supported: QueueBased, SkillsBased.\"}" >&2; exit 2 ;;
esac

if [ "$WSR_INPUT_COUNT" -gt 0 ] && [ "$WSR_INPUT_COUNT" -lt 4 ]; then
  echo '{"error":"Incomplete WorkSkillRouting input. Set all four of OMNI_WSR_ENTITY, OMNI_WSR_FIELD, OMNI_WSR_SKILL, and OMNI_WSR_VALUE."}' >&2
  exit 2
fi

if [ "$ROUTING_TYPE" = "SkillsBased" ]; then
  if [ "$WSR_INPUT_COUNT" -ne 4 ]; then
    echo '{"error":"SkillsBased routing requires a complete WorkSkillRouting mapping: OMNI_WSR_ENTITY, OMNI_WSR_FIELD, OMNI_WSR_SKILL, and OMNI_WSR_VALUE."}' >&2
    exit 2
  fi
  if [ "$SKILL_OPTION" != "RunSBRRules" ]; then
    echo "{\"error\":\"The coordinator supports OMNI_SKILL_OPTION=RunSBRRules for SkillsBased routing; got '$SKILL_OPTION'.\"}" >&2
    exit 2
  fi
  if [ -z "$SBR_SKILL" ] || [ "$SBR_SKILL" != "${OMNI_WSR_SKILL:-}" ]; then
    echo '{"error":"SkillsBased routing requires OMNI_SBR_SKILL to be unset or match OMNI_WSR_SKILL, so provisioned agents receive the skill required by the WorkSkillRouting rule."}' >&2
    exit 2
  fi
fi

# Optional fallback assignee for Case/VoiceCall QRCs (Username or 005 Id); exported to each QRC leaf.
if [ -n "${OMNI_OVERFLOW_ASSIGNEE:-}" ]; then export QRC_OVERFLOW_ASSIGNEE="$OMNI_OVERFLOW_ASSIGNEE"; fi
if [ -n "${OMNI_QRC_PUSH_TIMEOUT:-}" ]; then export QRC_PUSH_TIMEOUT="$OMNI_QRC_PUSH_TIMEOUT"; fi
if [ -n "${OMNI_QRC_CAPACITY_PERCENTAGE:-}" ]; then export QRC_CAPACITY_PERCENTAGE="$OMNI_QRC_CAPACITY_PERCENTAGE"; fi

if ! [[ "$ORG" =~ ^[A-Za-z0-9._@-]+$ ]]; then
  echo "{\"error\":\"Invalid org-alias '$ORG'. Allowed: A-Z, a-z, 0-9, . _ @ -\"}" >&2
  exit 2
fi

# Agent count 1..10 - matches the leaf contracts; validate before any org write.
if ! [[ "$COUNT" =~ ^([1-9]|10)$ ]]; then
  echo "{\"error\":\"Invalid count '$COUNT'. Must be integer 1..10.\"}" >&2
  exit 2
fi

# Supervisor count 1..5 - matches the leaf contracts; validate before any org write.
if ! [[ "$SUPERVISOR_COUNT" =~ ^[1-5]$ ]]; then
  echo "{\"error\":\"Invalid supervisor_count '$SUPERVISOR_COUNT'. Must be integer 1..5.\"}" >&2
  exit 2
fi

if ! [[ "$SUPERVISOR_CONFIG_DN" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid OMNI_SUPERVISOR_CONFIG_DEVELOPER_NAME '$SUPERVISOR_CONFIG_DN'. It must start with a letter and contain only A-Z, a-z, 0-9, or _ (maximum 80 characters).\"}" >&2
  exit 2
fi

IFS=',' read -r -a ROUTING_TARGETS <<< "$ROUTING_TARGETS_CSV"
for target in "${ROUTING_TARGETS[@]}"; do
  case "$target" in
    Case|Incident|MessagingSession|VoiceCall) ;;
    *)
      echo "{\"error\":\"Unsupported routing target: '$target'. Supported: Case, Incident, MessagingSession, VoiceCall.\"}" >&2
      exit 2
      ;;
  esac
done

SKILLS_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# Artifacts may hold generated credentials: 0700 parent + umask 077 (files default 0600) so nothing
# is group/other readable; mktemp -d avoids same-second $TIMESTAMP collisions.
umask 077
mkdir -p "/tmp/omni-driver"
chmod 700 "/tmp/omni-driver" 2>/dev/null || true
ARTIFACTS_DIR="$(mktemp -d "/tmp/omni-driver/${TIMESTAMP}.XXXXXX")"
chmod 700 "$ARTIFACTS_DIR"

# Secrets split out of per-skill JSON into one restricted file (see redact_credentials).
CREDENTIALS_FILE="$ARTIFACTS_DIR/CREDENTIALS.json"
# The user-create leaves escrow generated passwords directly to this restricted file instead of ever
# printing plaintext to stdout; point them at the coordinator's file so all credentials land here.
# redact_credentials still runs on artifacts as defense-in-depth (it is a no-op when none are present).
export OMNI_CREDENTIALS_FILE="$CREDENTIALS_FILE"

SKILL_RESULTS='[]'
OVERALL_STATUS="green"
BLOCKING_SKILL=""
FIRST_YELLOW_SKILL=""
ATTENTION_LEAVES='[]'

# Global safe_to_write guard - enforced BEFORE any skill runs (both --plan and --run)
if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated.\"}" >&2
  exit 1
fi

ORG_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" 2>/dev/null) || {
  echo "{\"error\":\"Failed to query Organization. SOQL error: $(printf '%s' "$ORG_JSON" | head -c 400)\"}" >&2
  exit 1
}

IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE="false"
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE="true"
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  jq -n \
    --arg org "$ORG" \
    --arg is_sandbox "$IS_SANDBOX" \
    --arg trial_exp "$TRIAL_EXP" \
    --arg org_type "$ORG_TYPE" \
    --arg mode "$MODE" \
    '{
      error: "Refusing to run integration driver against a real production customer org.",
      org_alias: $org,
      mode: $mode,
      org_shape: {
        is_sandbox: ($is_sandbox == "true"),
        trial_expiration_date: (if $trial_exp == "null" then null else $trial_exp end),
        organization_type: $org_type
      },
      safe_to_write: false,
      required_shape: "Target must have IsSandbox=true OR TrialExpirationDate!=null OR OrganizationType in (Developer Edition, Base Edition)."
    }' >&2
  exit 1
fi

echo "" >&2
echo "=== Omni Integration Driver (mode=$MODE) ===" >&2
echo "Org:               $ORG" >&2
echo "Count:             $COUNT" >&2
echo "Supervisor count:  $SUPERVISOR_COUNT" >&2
echo "Supervisor config: $SUPERVISOR_CONFIG_DN" >&2
echo "Routing targets:   ${ROUTING_TARGETS[*]}" >&2
echo "Timestamp:         $TIMESTAMP" >&2
echo "Artifacts:         $ARTIFACTS_DIR" >&2
echo "safe_to_write:     true (IsSandbox=$IS_SANDBOX TrialExp=$TRIAL_EXP OrgType=$ORG_TYPE)" >&2

# Resolve a usable profile on THIS org rather than assuming "Service Cloud User" exists. An explicit
# override is trusted as-is (only warned if absent); otherwise prefer "Service Cloud User", then fall
# back to "Standard User" (a full-Salesforce-license profile present in every org).
ORG_PROFILES_JSON=$(sf data query --target-org "$ORG" --json \
  --query "SELECT Name FROM Profile" 2>/dev/null || echo '{}')
profile_exists() { echo "$ORG_PROFILES_JSON" | jq -e --arg n "$1" 'any(.result.records[]?; .Name==$n)' >/dev/null 2>&1; }
resolve_profile() {
  local want="$1" label="$2" p
  if [ -n "$want" ]; then
    profile_exists "$want" || echo "  [!] $label profile '$want' not found on org; the create leaf may fail or fall back." >&2
    printf '%s' "$want"; return 0
  fi
  for p in "Service Cloud User" "Standard User"; do
    profile_exists "$p" && { printf '%s' "$p"; return 0; }
  done
  printf '%s' "Standard User"
}
AGENT_PROFILE="$(resolve_profile "$AGENT_PROFILE" "Agent")"
SUPERVISOR_PROFILE="$(resolve_profile "$SUPERVISOR_PROFILE" "Supervisor")"
echo "Agent profile:     $AGENT_PROFILE" >&2
echo "Supervisor profile: $SUPERVISOR_PROFILE" >&2
echo "" >&2

echo "  Preflight: entity availability" >&2
for target in "${ROUTING_TARGETS[@]}"; do
  if [ "$target" = "Case" ]; then continue; fi
  ENTITY_CHECK=$(sf data query --target-org "$ORG" --json \
    --query "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = '$target'" 2>/dev/null \
    | jq -r '.result.totalSize // 0')
  if [ "$ENTITY_CHECK" != "1" ]; then
    echo "  [x] Target sObject '$target' not available on this org." >&2
    echo "     Enable required feature (Incident Management / Enhanced Messaging) and retry." >&2
    exit 2
  fi
  echo "    [ok] $target" >&2
done
echo "" >&2

OVERALL_START=$(date +%s)

# --plan: export PLAN_ONLY so each writer self-gates to its read-only detection path.
if [ "$MODE" = "plan" ]; then export PLAN_ONLY=1; fi

# Dependency tracking: never write after a red prerequisite (green/yellow allow dependents).
BASE_OK="true"
AGENT_USERS_OK="true"
SUPERVISOR_USERS_OK="true"
SUPERVISOR_CONFIG_OK="true"
# Per-target flags without associative arrays (macOS bash 3.2 has no declare -A): namespaced
# scalars + indirect expansion.
_flag_var() {           # $1=namespace $2=key -> safe scalar var name
  local key; key=$(printf '%s' "$2" | tr -c 'A-Za-z0-9' '_')
  printf '%s' "__FLAG_${1}_${key}"
}
set_flag() {            # $1=namespace $2=key $3=value
  local v; v=$(_flag_var "$1" "$2"); printf -v "$v" '%s' "$3"
}
get_flag() {            # $1=namespace $2=key $3=default -> echoes value or default
  # set +u guards indirect expansion of an unset key under nounset (bash 3.2); scoped to this subshell.
  local v val; v=$(_flag_var "$1" "$2"); set +u; val="${!v}"; set -u; printf '%s' "${val:-$3}"
}

# Canonical QRC DeveloperName per target; only Case/VoiceCall get a QRC + created queue.
qrc_dn_for_target() {
  case "$1" in
    Case)             printf 'Case_Routing_Config' ;;
    VoiceCall)        printf 'Voice_Routing_Config' ;;
    Incident)         printf 'Incident_Routing_Config' ;;
    MessagingSession) printf 'Messaging_Routing_Config' ;;
  esac
}
qrc_override_for_target() {
  case "$1" in
    Case)             printf '%s' "${OMNI_CASE_ROUTING_CONFIG_DEVELOPER_NAME:-}" ;;
    VoiceCall)        printf '%s' "${OMNI_VOICE_ROUTING_CONFIG_DEVELOPER_NAME:-}" ;;
    Incident)         printf '%s' "${OMNI_INCIDENT_ROUTING_CONFIG_DEVELOPER_NAME:-}" ;;
    MessagingSession) printf '%s' "${OMNI_MESSAGING_ROUTING_CONFIG_DEVELOPER_NAME:-}" ;;
  esac
}
queue_override_for_target() {
  case "$1" in
    Case)             printf '%s' "${OMNI_CASE_QUEUE_DEVELOPER_NAME:-}" ;;
    VoiceCall)        printf '%s' "${OMNI_VOICE_QUEUE_DEVELOPER_NAME:-}" ;;
    Incident)         printf '%s' "${OMNI_INCIDENT_QUEUE_DEVELOPER_NAME:-}" ;;
    MessagingSession) printf '%s' "${OMNI_MESSAGING_QUEUE_DEVELOPER_NAME:-}" ;;
  esac
}
resolve_qrc_dn_for_target() {
  local target="$1" explicit queue_dn linked_json linked_id qrc_json linked_dn
  explicit="$(qrc_override_for_target "$target")"
  if [ -n "$explicit" ]; then
    if ! [[ "$explicit" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
      echo "Invalid routing-config DeveloperName '$explicit' for $target." >&2
      return 1
    fi
    printf '%s' "$explicit"
    return 0
  fi

  queue_dn="$(queue_override_for_target "$target")"
  if [ -z "$queue_dn" ]; then
    qrc_dn_for_target "$target"
    return 0
  fi
  if ! [[ "$queue_dn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
    echo "Invalid queue DeveloperName '$queue_dn' for $target." >&2
    return 1
  fi

  linked_json=$(sf data query --target-org "$ORG" --json \
    --query "SELECT QueueRoutingConfigId FROM Group WHERE Type='Queue' AND DeveloperName='$queue_dn' LIMIT 1" 2>/dev/null || echo '{}')
  if ! echo "$linked_json" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    echo "Queue-to-routing-config discovery was inconclusive for '$queue_dn'." >&2
    return 1
  fi
  linked_id=$(echo "$linked_json" | jq -r '.result.records[0].QueueRoutingConfigId // ""')
  if [ -z "$linked_id" ]; then
    qrc_dn_for_target "$target"
    return 0
  fi
  if ! [[ "$linked_id" =~ ^[A-Za-z0-9]{15,18}$ ]]; then
    echo "Queue '$queue_dn' returned an invalid QueueRoutingConfigId." >&2
    return 1
  fi

  qrc_json=$(sf data query --target-org "$ORG" --json \
    --query "SELECT DeveloperName FROM QueueRoutingConfig WHERE Id='$linked_id' LIMIT 1" 2>/dev/null || echo '{}')
  if ! echo "$qrc_json" | jq -e '.result.records | arrays' >/dev/null 2>&1; then
    echo "Linked routing-config discovery was inconclusive for queue '$queue_dn'." >&2
    return 1
  fi
  linked_dn=$(echo "$qrc_json" | jq -r '.result.records[0].DeveloperName // ""')
  if [ -z "$linked_dn" ]; then
    echo "Queue '$queue_dn' references a QueueRoutingConfig that could not be resolved." >&2
    return 1
  fi
  if ! [[ "$linked_dn" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    echo "Queue '$queue_dn' returned an invalid linked QueueRoutingConfig DeveloperName." >&2
    return 1
  fi
  printf '%s' "$linked_dn"
}
# Whether this target participates in the create-queue + QRC + routing-flow steel thread.
target_has_routing_thread() {
  case "$1" in Case|VoiceCall) return 0 ;; *) return 1 ;; esac
}

# --plan readiness flags: a downstream detector runs only when its prerequisites are present on the
# org; otherwise it is deferred as pending (yellow), since probing an Omni-dependent skill before
# Omni is enabled raises INVALID_TYPE and would mislead as red. Clean --plan (all reused) => org
# already configured; any action_needed (yellow) => real setup work remains.
BASE_ENABLED="false"            # Omni-Channel settings already enabled (base plan .all_enabled)
AGENT_USERS_PRESENT="false"      # all agent users already exist (agent-users plan status == reused)
SUPERVISOR_USERS_PRESENT="false" # all supervisor users already exist (supervisor plan == reused)
SUPERVISOR_CONFIG_PRESENT="false" # OmniSupervisorConfig already exists (config plan == reused)

# Record a plan skill deferred because a prerequisite isn't in place yet (pending/yellow, not blocked).
record_plan_pending() {
  local name="$1" key="$2" desc="$3" reason="$4"
  printf "  [  0s] %-55s → pending (yellow)\n" "$key" >&2
  echo "           -> $reason" >&2
  SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
    --arg name "$name" --arg key "$key" --arg desc "$desc" --arg reason "$reason" \
    '. + [{name: $name, invocation_key: $key, description: $desc, status: "action_needed", color: "yellow", elapsed_sec: 0, artifact_path: null, exit_code: 0, action_required: $reason}]')
  ATTENTION_LEAVES=$(echo "$ATTENTION_LEAVES" | jq -c --arg k "$key" '. + [$k]')
  if [ -z "$FIRST_YELLOW_SKILL" ]; then FIRST_YELLOW_SKILL="$key"; fi
  if [ "$OVERALL_STATUS" = "green" ]; then OVERALL_STATUS="yellow"; fi
}

# Record a skill that was intentionally NOT run because a prerequisite failed.
record_dependency_skip() {
  local name="$1" key="$2" desc="$3" reason="$4"
  printf "  [  0s] %-55s → blocked_by_dependency\n" "$key" >&2
  echo "           -> $reason" >&2
  SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
    --arg name "$name" --arg key "$key" --arg desc "$desc" --arg reason "$reason" \
    '. + [{name: $name, invocation_key: $key, description: $desc, status: "blocked_by_dependency", color: "red", elapsed_sec: 0, artifact_path: null, exit_code: 0, blocking_issue: $reason}]')
  OVERALL_STATUS="red"
  if [ -z "$BLOCKING_SKILL" ]; then BLOCKING_SKILL="$key"; fi
}

# Move plaintext passwords from a per-skill artifact into restricted CREDENTIALS.json (0600),
# replacing them with "[redacted - see CREDENTIALS.json]"; handles top-level and nested .create shapes.
CREDENTIALS_WRITTEN="false"
redact_credentials() {
  local artifact="$1" key="$2"
  [ -s "$artifact" ] || return 0
  # Fast path: nothing to redact if no password field is present anywhere.
  if ! jq -e '.. | objects | select(has("password")) | .password | strings' "$artifact" >/dev/null 2>&1; then
    return 0
  fi

  # Extract [{username,password}] pairs (both shapes) with non-null passwords.
  local creds
  creds=$(jq -c '
    [ (.created_users // []), (.create.created_users // []) ]
    | add // []
    | map(select(.password != null) | {username: .username, password: .password})
  ' "$artifact" 2>/dev/null || echo '[]')

  if [ "$(echo "$creds" | jq 'length')" -gt 0 ]; then
    # Escrow credentials fail-closed: build to a temp file, verify, atomically replace, and on any
    # failure delete the plaintext source artifact and abort so credentials never leak.
    local existing='{}' credtmp
    [ -f "$CREDENTIALS_FILE" ] && existing=$(cat "$CREDENTIALS_FILE" 2>/dev/null || echo '{}')
    credtmp=$(mktemp)
    if ! echo "$existing" | jq --arg k "$key" --argjson c "$creds" '. + {($k): $c}' > "$credtmp" 2>/dev/null \
         || [ ! -s "$credtmp" ] \
         || ! jq -e --arg k "$key" '.[$k] | length > 0' "$credtmp" >/dev/null 2>&1; then
      rm -f "$credtmp"
      rm -f "$artifact"
      printf "  [x] SECURITY: could not escrow credentials to CREDENTIALS.json; deleted plaintext artifact %s and aborting.\n" "$artifact" >&2
      exit 1
    fi
    if ! mv "$credtmp" "$CREDENTIALS_FILE"; then
      rm -f "$credtmp"
      rm -f "$artifact"
      printf "  [x] SECURITY: could not persist CREDENTIALS.json; deleted plaintext artifact %s and aborting.\n" "$artifact" >&2
      exit 1
    fi
    chmod 600 "$CREDENTIALS_FILE" 2>/dev/null || true
    CREDENTIALS_WRITTEN="true"
  fi

  # Null every .password in place, fail-closed: on failure delete the plaintext original and abort.
  local tmp
  tmp=$(mktemp)
  if ! jq '(.. | objects | select(has("password")) | .password) |= (if . == null then null else "[redacted - see CREDENTIALS.json]" end)' \
         "$artifact" > "$tmp" 2>/dev/null; then
    rm -f "$tmp"
    rm -f "$artifact"
    printf "  [x] SECURITY: could not redact credentials in %s; deleted plaintext artifact and aborting.\n" "$artifact" >&2
    exit 1
  fi
  # Verify the rewritten file is non-empty and that no original plaintext password value survived.
  if [ ! -s "$tmp" ] || jq -e '.. | objects | select(has("password")) | .password
        | strings | select(. != "[redacted - see CREDENTIALS.json]")' "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    rm -f "$artifact"
    printf "  [x] SECURITY: redaction verification failed for %s; deleted plaintext artifact and aborting.\n" "$artifact" >&2
    exit 1
  fi
  # Atomic replace only after verification succeeded.
  if ! mv "$tmp" "$artifact"; then
    rm -f "$tmp"
    rm -f "$artifact"
    printf "  [x] SECURITY: could not persist redacted artifact %s; deleted plaintext artifact and aborting.\n" "$artifact" >&2
    exit 1
  fi
  chmod 600 "$artifact" 2>/dev/null || true
}

# Per-skill runner (array-based invocation - NO eval).
run_skill() {
  local skill_name="$1"
  local invocation_key="$2"
  local skill_desc="$3"
  local status_expr="$4"
  local script_file="$5"
  shift 5
  local -a script_args=("$@")

  local skill_dir="$SKILLS_DIR/$skill_name"
  if [ ! -d "$skill_dir" ]; then
    printf "  [x] Skill directory missing: %s\n" "$skill_dir" >&2
    SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
      --arg name "$skill_name" \
      --arg key  "$invocation_key" \
      --arg desc "$skill_desc" \
      '. + [{name: $name, invocation_key: $key, description: $desc, status: "missing_skill", color: "red", elapsed_sec: 0, artifact_path: null, exit_code: 127}]')
    OVERALL_STATUS="red"
    if [ -z "$BLOCKING_SKILL" ]; then BLOCKING_SKILL="$invocation_key"; fi
    return 1
  fi

  local script_dir="$skill_dir/scripts"
  local script_path="$script_dir/$script_file"
  if [ ! -x "$script_path" ] && [ ! -f "$script_path" ]; then
    printf "  [x] Skill script missing: %s\n" "$script_path" >&2
    SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
      --arg name "$skill_name" \
      --arg key  "$invocation_key" \
      --arg desc "$skill_desc" \
      '. + [{name: $name, invocation_key: $key, description: $desc, status: "missing_skill_script", color: "red", elapsed_sec: 0, artifact_path: null, exit_code: 127}]')
    OVERALL_STATUS="red"
    if [ -z "$BLOCKING_SKILL" ]; then BLOCKING_SKILL="$invocation_key"; fi
    return 1
  fi

  local start_ts artifact stderr_log exit_code status end_ts elapsed
  start_ts=$(date +%s)
  artifact="$ARTIFACTS_DIR/${invocation_key}.json"
  stderr_log="$ARTIFACTS_DIR/${invocation_key}.stderr.log"

  exit_code=0
  ( cd "$skill_dir" && bash "$script_path" "${script_args[@]}" ) > "$artifact" 2> "$stderr_log" || exit_code=$?
  # umask 077 above already forces 0600, but be explicit in case the skill pre-created the file.
  chmod 600 "$artifact" "$stderr_log" 2>/dev/null || true

  # Move any plaintext passwords out of the artifact into CREDENTIALS.json.
  redact_credentials "$artifact" "$invocation_key"

  end_ts=$(date +%s)
  elapsed=$((end_ts - start_ts))

  if [ -s "$artifact" ]; then
    status=$(jq -r "$status_expr" "$artifact" 2>/dev/null || echo "parse_error")
  else
    status="empty_output"
  fi

  # Status → traffic light. Green success states (shared enum): reused/updated/created/deployed/
  # configured/bound/assigned/ok/success/skipped.
  local color
  case "$status" in
    reused|updated|created|deployed|configured|bound|assigned|ok|success|skipped)
      color="green"
      ;;
    action_needed|partial|unsupported_v1|not_evaluated)
      color="yellow"
      ;;
    blocked|blocked_by_dependency|empty_output|parse_error)
      color="red"
      ;;
    *)
      color="unknown"
      ;;
  esac

  if [ "$exit_code" -ne 0 ] && [ "$color" != "red" ]; then
    printf "  [!]  skill exit_code=%d contradicts status='%s' - escalating to blocked\n" "$exit_code" "$status" >&2
    status="crashed_after_reporting_${status}"
    color="red"
  fi
  if [ "$color" = "unknown" ]; then
    printf "  [!]  unrecognized skill status='%s' - treating as attention_required\n" "$status" >&2
    color="yellow"
  fi

  printf "  [%3ds] %-55s → %s (%s)\n" "$elapsed" "$invocation_key" "$status" "$color" >&2
  if [ "$color" = "red" ]; then
    local msg
    msg=$(jq -r '.blocking_issue // .error // .message // "no message"' "$artifact" 2>/dev/null || echo "(unparseable)")
    echo "           -> $msg" >&2
  elif [ "$color" = "yellow" ]; then
    local msg
    msg=$(jq -r '.action_required // .manual_actions // .blocking_issue // ""' "$artifact" 2>/dev/null || echo "")
    if [ -n "$msg" ] && [ "$msg" != "null" ] && [ "$msg" != "[]" ]; then
      echo "           -> action needed: $msg" >&2
    fi
  fi

  SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
    --arg name "$skill_name" \
    --arg key  "$invocation_key" \
    --arg desc "$skill_desc" \
    --arg status "$status" \
    --arg color "$color" \
    --argjson elapsed "$elapsed" \
    --arg artifact "$artifact" \
    --argjson exit_code "$exit_code" \
    '. + [{name: $name, invocation_key: $key, description: $desc, status: $status, color: $color, elapsed_sec: $elapsed, artifact_path: $artifact, exit_code: $exit_code}]')

  case "$color" in
    red)
      if [ -z "$BLOCKING_SKILL" ]; then BLOCKING_SKILL="$invocation_key"; fi
      OVERALL_STATUS="red"
      return 1
      ;;
    yellow)
      ATTENTION_LEAVES=$(echo "$ATTENTION_LEAVES" | jq -c --arg k "$invocation_key" '. + [$k]')
      if [ -z "$FIRST_YELLOW_SKILL" ]; then FIRST_YELLOW_SKILL="$invocation_key"; fi
      if [ "$OVERALL_STATUS" = "green" ]; then OVERALL_STATUS="yellow"; fi
      ;;
    green)
      :
      ;;
  esac

  return 0
}

# ---- Base settings ----
# Plan detects; run deploys the 5 OmniChannelSettings toggles + re-verifies. Hard prerequisite for
# every write skill below (INVALID_TYPE when Omni is off), so a red here fails fast.
if [ "$MODE" = "plan" ]; then
  run_skill "service-omni-base-settings-configure" \
    "service-omni-base-settings-configure" \
    "Omni base settings (detect-existing)" \
    '(if .all_enabled == true then "reused" else "action_needed" end)' \
    configure-and-report.sh plan "$ORG" \
    || BASE_OK="false"
  base_art="$ARTIFACTS_DIR/service-omni-base-settings-configure.json"
  if [ -f "$base_art" ] && [ "$(jq -r '.all_enabled // false' "$base_art" 2>/dev/null)" = "true" ]; then
    BASE_ENABLED="true"
  fi
else
  run_skill "service-omni-base-settings-configure" \
    "service-omni-base-settings-configure" \
    "Omni base settings (detect → deploy → verify)" \
    '.status' \
    configure-and-report.sh run "$ORG" \
    || BASE_OK="false"
fi

# ---- Agent users (detect-and-create.sh chains detect → run-create in --run mode) ----
# Agents provision on Service Cloud User (Omni requires a Service Cloud license).
run_skill "service-omni-agent-users-create" \
  "service-omni-agent-users-create" \
  "Agent users (detect + create when missing)" \
  '.status' \
  detect-and-create.sh "$MODE" "$ORG" "$COUNT" "$AGENT_PROFILE" \
  || AGENT_USERS_OK="false"

if [ "$MODE" = "plan" ]; then
  du_art="$ARTIFACTS_DIR/service-omni-agent-users-create.json"
  if [ -f "$du_art" ] && [ "$(jq -r '.status // ""' "$du_art" 2>/dev/null)" = "reused" ]; then
    AGENT_USERS_PRESENT="true"
  fi
fi

# ---- Service channel (per target) ----
for target in "${ROUTING_TARGETS[@]}"; do
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ]; then
      run_skill "service-omni-service-channel-configure" \
        "service-omni-service-channel-configure-${target}" \
        "ServiceChannel for $target (plan detect)" \
        '.status' \
        deploy-and-report.sh "$ORG" "$target" || true
    else
      record_plan_pending "service-omni-service-channel-configure" \
        "service-omni-service-channel-configure-${target}" \
        "ServiceChannel for $target (pending)" \
        "Omni-Channel is not yet enabled; the ServiceChannel for $target will be configured after base settings."
    fi
    set_flag SC_OK "$target" "true"
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-service-channel-configure" \
      "service-omni-service-channel-configure-${target}" \
      "ServiceChannel for $target (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping ServiceChannel deploy for $target."
    set_flag SC_OK "$target" "false"
  else
    if run_skill "service-omni-service-channel-configure" \
      "service-omni-service-channel-configure-${target}" \
      "ServiceChannel for $target (Metadata deploy)" \
      '.status' \
      deploy-and-report.sh "$ORG" "$target"; then
      set_flag SC_OK "$target" "true"
    else
      set_flag SC_OK "$target" "false"
    fi
  fi
done

# ---- QRC (per target: Case + VoiceCall) ----
# Each routing-thread target gets its own QRC; the leaf derives naming from QRC_ROUTING_TARGET.
for target in "${ROUTING_TARGETS[@]}"; do
  set_flag QRC_OK "$target" "true"
  target_has_routing_thread "$target" || continue
  if ! qrc_dn="$(resolve_qrc_dn_for_target "$target")"; then
    record_dependency_skip "service-omni-queue-routing-config-deploy" \
      "service-omni-queue-routing-config-deploy-${target}" \
      "QueueRoutingConfig resolution for $target (blocked)" \
      "Could not safely resolve the existing or requested QueueRoutingConfig DeveloperName for $target."
    set_flag QRC_OK "$target" "false"
    continue
  fi
  set_flag QRC_DN "$target" "$qrc_dn"
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ]; then
      QRC_ROUTING_TARGET="$target" QRC_DEVELOPER_NAME="$qrc_dn" run_skill "service-omni-queue-routing-config-deploy" \
        "service-omni-queue-routing-config-deploy-${target}" \
        "$qrc_dn (plan detect)" \
        '.status' \
        upsert-and-report.sh "$ORG" || set_flag QRC_OK "$target" "false"
    else
      record_plan_pending "service-omni-queue-routing-config-deploy" \
        "service-omni-queue-routing-config-deploy-${target}" \
        "$qrc_dn (pending)" \
        "Omni-Channel is not yet enabled; the QueueRoutingConfig for $target will be created after base settings."
    fi
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-queue-routing-config-deploy" \
      "service-omni-queue-routing-config-deploy-${target}" \
      "$qrc_dn (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping QueueRoutingConfig upsert for $target."
    set_flag QRC_OK "$target" "false"
  else
    QRC_ROUTING_TARGET="$target" QRC_DEVELOPER_NAME="$qrc_dn" run_skill "service-omni-queue-routing-config-deploy" \
      "service-omni-queue-routing-config-deploy-${target}" \
      "$qrc_dn (Data API upsert)" \
      '.status' \
      upsert-and-report.sh "$ORG" \
      || set_flag QRC_OK "$target" "false"
  fi
done

# ---- Queue (per target) ----
# Needs base settings; routing-thread targets also need their QRC first (the queue binds to it).
# --create-if-missing builds + binds a queue on fresh orgs instead of hard-blocking.
for target in "${ROUTING_TARGETS[@]}"; do
  set_flag QUEUE_OK "$target" "true"
  qrc_dn="$(get_flag QRC_DN "$target" "$(qrc_dn_for_target "$target")")"
  queue_override="$(queue_override_for_target "$target")"
  in_thread="false"; target_has_routing_thread "$target" && in_thread="true"
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" != "true" ]; then
      record_plan_pending "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue verify+align for $target (pending)" \
        "Omni-Channel is not yet enabled; the queue verify+align for $target will run after base settings."
      set_flag QUEUE_OK "$target" "false"
    elif [ "$in_thread" = "true" ] && [ "$(get_flag QRC_OK "$target" true)" != "true" ]; then
      record_plan_pending "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue verify+align for $target (pending)" \
        "QueueRoutingConfig is not yet present; the $target queue create/align will run after it is created."
      set_flag QUEUE_OK "$target" "false"
    elif [ "$in_thread" = "true" ]; then
      run_skill "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue create+align for $target (plan detect)" \
        '.status' \
        verify-and-align.sh "$ORG" "$target" "$qrc_dn" "$queue_override" --create-if-missing \
        || set_flag QUEUE_OK "$target" "false"
    else
      run_skill "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue verify+align for $target (plan detect)" \
        '.status' \
        verify-and-align.sh "$ORG" "$target" "" "$queue_override" \
        || set_flag QUEUE_OK "$target" "false"
    fi
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-queue-deploy" \
      "service-omni-queue-deploy-${target}" \
      "Queue verify+align for $target (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping queue verify+align for $target."
    set_flag QUEUE_OK "$target" "false"
  elif [ "$in_thread" = "true" ] && [ "$(get_flag QRC_OK "$target" true)" != "true" ]; then
    record_dependency_skip "service-omni-queue-deploy" \
      "service-omni-queue-deploy-${target}" \
      "Queue verify+align for $target (skipped)" \
      "Prerequisite service-omni-queue-routing-config-deploy did not succeed for $target; cannot bind the queue to $qrc_dn."
    set_flag QUEUE_OK "$target" "false"
  else
    if [ "$in_thread" = "true" ]; then
      run_skill "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue create+align for $target (Metadata + Data API)" \
        '.status' \
        verify-and-align.sh "$ORG" "$target" "$qrc_dn" "$queue_override" --create-if-missing \
        || set_flag QUEUE_OK "$target" "false"
    else
      run_skill "service-omni-queue-deploy" \
        "service-omni-queue-deploy-${target}" \
        "Queue verify+align for $target (Data API)" \
        '.status' \
        verify-and-align.sh "$ORG" "$target" "" "$queue_override" \
        || set_flag QUEUE_OK "$target" "false"
    fi
  fi
done

# ---- Queue members (per target - chained to queue-deploy's discovered queue DN) ----
# Needs both the queue (queue-deploy ok) and the agent users to exist.
for target in "${ROUTING_TARGETS[@]}"; do
  if [ "$MODE" = "plan" ]; then
    if [ "$(get_flag QUEUE_OK "$target" true)" != "true" ]; then
      record_plan_pending "service-omni-queue-members-assign" \
        "service-omni-queue-members-assign-${target}" \
        "Queue members for $target (pending)" \
        "The $target queue is not yet in place; member binding will run after the queue is aligned."
      continue
    fi
    if [ "$AGENT_USERS_PRESENT" != "true" ]; then
      record_plan_pending "service-omni-queue-members-assign" \
        "service-omni-queue-members-assign-${target}" \
        "Queue members for $target (pending)" \
        "Agent users are not yet created; member binding will run after they exist."
      continue
    fi
    q_artifact="$ARTIFACTS_DIR/service-omni-queue-deploy-${target}.json"
    queue_dn=""
    [ -f "$q_artifact" ] && queue_dn=$(jq -r '.developer_name // ""' "$q_artifact" 2>/dev/null || true)
    if [ -z "$queue_dn" ] || [ "$queue_dn" = "null" ] || ! [[ "$queue_dn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
      record_plan_pending "service-omni-queue-members-assign" \
        "service-omni-queue-members-assign-${target}" \
        "Queue members for $target (pending)" \
        "Queue DeveloperName was not resolved in plan; member binding will run once the queue is confirmed."
      continue
    fi
    run_skill "service-omni-queue-members-assign" \
      "service-omni-queue-members-assign-${target}" \
      "Queue members for $target (plan detect, queue $queue_dn)" \
      '.status' \
      verify-and-bind.sh "$ORG" "$queue_dn" "$COUNT" \
      || true
    # Plan: only "reused" means members are already bound; else a --run would bind them first.
    mem_status=$(jq -r '.status // ""' "$ARTIFACTS_DIR/service-omni-queue-members-assign-${target}.json" 2>/dev/null || echo "")
    if [ "$mem_status" = "reused" ]; then
      set_flag QUEUE_MEMBERS_OK "$target" "true"
    else
      set_flag QUEUE_MEMBERS_OK "$target" "false"
    fi
    continue
  fi
  if [ "$(get_flag QUEUE_OK "$target" true)" != "true" ]; then
    record_dependency_skip "service-omni-queue-members-assign" \
      "service-omni-queue-members-assign-${target}" \
      "Queue members for $target (skipped)" \
      "Prerequisite service-omni-queue-deploy did not succeed for $target; skipping member binding."
    continue
  fi
  if [ "$AGENT_USERS_OK" != "true" ]; then
    record_dependency_skip "service-omni-queue-members-assign" \
      "service-omni-queue-members-assign-${target}" \
      "Queue members for $target (skipped)" \
      "Prerequisite service-omni-agent-users-create did not succeed; no agent users to bind as queue members."
    continue
  fi

  q_artifact="$ARTIFACTS_DIR/service-omni-queue-deploy-${target}.json"
  queue_dn=""
  if [ -f "$q_artifact" ]; then
    queue_dn=$(jq -r '.developer_name // ""' "$q_artifact" 2>/dev/null || true)
  fi

  if [ -z "$queue_dn" ] || [ "$queue_dn" = "null" ]; then
    printf "  [  0s] %-55s → skipped (queue not resolved)\n" "service-omni-queue-members-assign-${target}" >&2
    SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
      --arg name "service-omni-queue-members-assign" \
      --arg key  "service-omni-queue-members-assign-${target}" \
      --arg desc "Queue members for $target (skipped)" \
      '. + [{name: $name, invocation_key: $key, description: $desc, status: "skipped", color: "green", elapsed_sec: 0, artifact_path: null, exit_code: 0}]')
    continue
  fi

  if ! [[ "$queue_dn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
    printf "  [  0s] %-55s → blocked (invalid queue_dn: %q)\n" "service-omni-queue-members-assign-${target}" "$queue_dn" >&2
    SKILL_RESULTS=$(echo "$SKILL_RESULTS" | jq -c \
      --arg name "service-omni-queue-members-assign" \
      --arg key  "service-omni-queue-members-assign-${target}" \
      --arg desc "Queue members for $target (blocked: bad DN)" \
      '. + [{name: $name, invocation_key: $key, description: $desc, status: "blocked", color: "red", elapsed_sec: 0, artifact_path: null, exit_code: 1}]')
    OVERALL_STATUS="red"
    if [ -z "$BLOCKING_SKILL" ]; then BLOCKING_SKILL="service-omni-queue-members-assign-${target}"; fi
    continue
  fi

  run_skill "service-omni-queue-members-assign" \
    "service-omni-queue-members-assign-${target}" \
    "Queue members bind to $queue_dn for $target" \
    '.status' \
    verify-and-bind.sh "$ORG" "$queue_dn" "$COUNT" \
    || true
  # Record whether member binding fully succeeded; a partial bind blocks the routing-flow gate below.
  mem_status=$(jq -r '.status // ""' "$ARTIFACTS_DIR/service-omni-queue-members-assign-${target}.json" 2>/dev/null || echo "")
  case "$mem_status" in
    bound|reused) set_flag QUEUE_MEMBERS_OK "$target" "true" ;;
    *)            set_flag QUEUE_MEMBERS_OK "$target" "false" ;;
  esac
done

# Resolve provisioned and reused agent usernames once. SkillsBased routing needs these bindings before
# the WorkSkillRouting rule and routing flow are activated; rep-experience stages reuse the same list.
REP_AGENT_USERNAMES=""
au_art="$ARTIFACTS_DIR/service-omni-agent-users-create.json"
if [ -f "$au_art" ]; then
  REP_AGENT_USERNAMES=$(jq -r '
    [ (.created_users // []), (.create.created_users // []), (.reused_users // []),
      (.detect.existing_users // []), (.users // []) ]
    | add // [] | map(.username // empty) | unique | join(",")
  ' "$au_art" 2>/dev/null || echo "")
fi

# ---- SkillsBased prerequisites ----
# The Skill/agent bindings and WorkSkillRouting rule must exist before the trigger flow is activated.
# Otherwise an immediate record insert can produce a PSR with no SkillRequirement rows.
SBR_READY="true"
WSR_READY="true"
if [ "$ROUTING_TYPE" = "SkillsBased" ]; then
  SBR_READY="false"
  WSR_READY="false"

  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ] && [ "$AGENT_USERS_PRESENT" = "true" ] && [ -n "$REP_AGENT_USERNAMES" ]; then
      run_skill "service-omni-skills-based-routing-configure" \
        "service-omni-skills-based-routing-configure" \
        "Skills-based routing for $SBR_SKILL (plan detect)" \
        '.status' \
        configure-and-report.sh "$ORG" "$SBR_SKILL" "$REP_AGENT_USERNAMES" || true
    else
      record_plan_pending "service-omni-skills-based-routing-configure" \
        "service-omni-skills-based-routing-configure" \
        "Skills-based routing for $SBR_SKILL (pending)" \
        "Skills-based routing will run after Omni is enabled and agent users exist."
    fi
  elif [ "$BASE_OK" != "true" ] || [ "$AGENT_USERS_OK" != "true" ]; then
    record_dependency_skip "service-omni-skills-based-routing-configure" \
      "service-omni-skills-based-routing-configure" \
      "Skills-based routing (skipped)" \
      "Prerequisites (base settings + agent users) did not succeed; skipping agent bindings for $SBR_SKILL."
  elif [ -z "$REP_AGENT_USERNAMES" ]; then
    record_dependency_skip "service-omni-skills-based-routing-configure" \
      "service-omni-skills-based-routing-configure" \
      "Skills-based routing (skipped)" \
      "No active agent usernames were resolved; refusing to activate SkillsBased routing without a skilled agent."
  else
    run_skill "service-omni-skills-based-routing-configure" \
      "service-omni-skills-based-routing-configure" \
      "Skills-based routing bind $SBR_SKILL" \
      '.status' \
      configure-and-report.sh "$ORG" "$SBR_SKILL" "$REP_AGENT_USERNAMES" || true
    sbr_status=$(jq -r '.status // ""' "$ARTIFACTS_DIR/service-omni-skills-based-routing-configure.json" 2>/dev/null || echo "")
    case "$sbr_status" in configured|reused) SBR_READY="true" ;; esac
  fi

  WSR_LABEL="${OMNI_WSR_LABEL:-}"
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ]; then
      run_skill "service-omni-work-skill-routing-configure" \
        "service-omni-work-skill-routing-configure" \
        "Field-based skill routing $OMNI_WSR_ENTITY.$OMNI_WSR_FIELD=$OMNI_WSR_VALUE -> $OMNI_WSR_SKILL (plan detect)" \
        '.status' \
        configure-and-report.sh "$ORG" "$OMNI_WSR_ENTITY" "$OMNI_WSR_FIELD" "$OMNI_WSR_SKILL" "$OMNI_WSR_VALUE" "$WSR_LABEL" || true
    else
      record_plan_pending "service-omni-work-skill-routing-configure" \
        "service-omni-work-skill-routing-configure" \
        "Field-based skill routing (pending)" \
        "Omni-Channel is not yet enabled; the WorkSkillRouting rule will be authored after base settings."
    fi
  elif [ "$SBR_READY" != "true" ]; then
    record_dependency_skip "service-omni-work-skill-routing-configure" \
      "service-omni-work-skill-routing-configure" \
      "Field-based skill routing (skipped)" \
      "Agent skill provisioning did not succeed; refusing to activate a WorkSkillRouting rule with no eligible skilled agents."
  else
    run_skill "service-omni-work-skill-routing-configure" \
      "service-omni-work-skill-routing-configure" \
      "Field-based skill routing $OMNI_WSR_ENTITY.$OMNI_WSR_FIELD=$OMNI_WSR_VALUE -> $OMNI_WSR_SKILL" \
      '.status' \
      configure-and-report.sh "$ORG" "$OMNI_WSR_ENTITY" "$OMNI_WSR_FIELD" "$OMNI_WSR_SKILL" "$OMNI_WSR_VALUE" "$WSR_LABEL" || true
    wsr_status=$(jq -r '.status // ""' "$ARTIFACTS_DIR/service-omni-work-skill-routing-configure.json" 2>/dev/null || echo "")
    case "$wsr_status" in created|updated|reused) WSR_READY="true" ;; esac
  fi
fi

# ---- Routing flow (per routing-thread target: Case + VoiceCall) ----
# Record-triggered flow, last leg of the thread; runs only after queue + members exist. Passes the
# discovered ServiceChannel/Queue/QRC DeveloperNames so the flow binds the same resources, not its
# defaults. OMNI_RUNTIME_PROOF=1 fires the trigger (fail-soft); OMNI_RUNTIME_PROOF_REQUIRED=1 blocks on failure.
RF_FLAGS=(--routing-type "$ROUTING_TYPE")
[ "$ROUTING_TYPE" != "SkillsBased" ] || RF_FLAGS+=(--skill-option "$SKILL_OPTION")
[ "${OMNI_RUNTIME_PROOF:-0}" = "1" ] && RF_FLAGS+=(--runtime-proof)
[ "${OMNI_RUNTIME_PROOF_REQUIRED:-0}" = "1" ] && RF_FLAGS+=(--require-proof)
for target in "${ROUTING_TARGETS[@]}"; do
  target_has_routing_thread "$target" || continue
  rf_qrc="$(get_flag QRC_DN "$target" "$(qrc_dn_for_target "$target")")"
  # Resolve the queue + channel DeveloperNames this run established, from artifacts.
  rf_queue=""
  q_art="$ARTIFACTS_DIR/service-omni-queue-deploy-${target}.json"
  [ -f "$q_art" ] && rf_queue=$(jq -r '.developer_name // ""' "$q_art" 2>/dev/null || true)
  rf_channel=""
  sc_art="$ARTIFACTS_DIR/service-omni-service-channel-configure-${target}.json"
  [ -f "$sc_art" ] && rf_channel=$(jq -r '.channel_developer_name // ""' "$sc_art" 2>/dev/null || true)
  if [ "$MODE" = "plan" ]; then
    if [ "$(get_flag QUEUE_OK "$target" true)" != "true" ]; then
      record_plan_pending "service-omni-routing-flow-deploy" \
        "service-omni-routing-flow-deploy-${target}" \
        "Routing flow for $target (pending)" \
        "The $target queue is not yet in place; the routing flow will deploy after the queue + members."
    elif [ "$(get_flag QUEUE_MEMBERS_OK "$target" false)" != "true" ]; then
      record_plan_pending "service-omni-routing-flow-deploy" \
        "service-omni-routing-flow-deploy-${target}" \
        "Routing flow for $target (pending)" \
        "The $target queue has no members bound yet; the routing flow will deploy after queue members are assigned (routing to an empty queue is refused)."
    elif [ "$ROUTING_TYPE" = "SkillsBased" ]; then
      record_plan_pending "service-omni-routing-flow-deploy" \
        "service-omni-routing-flow-deploy-${target}" \
        "SkillsBased routing flow for $target (pending)" \
        "The Skill bindings and WorkSkillRouting rule will be created before the SkillsBased trigger flow is activated."
    else
      SERVICE_CHANNEL_DEVELOPER_NAME="$rf_channel" QUEUE_DEVELOPER_NAME="$rf_queue" ROUTING_CONFIG_DEVELOPER_NAME="$rf_qrc" \
      run_skill "service-omni-routing-flow-deploy" \
        "service-omni-routing-flow-deploy-${target}" \
        "Routing flow for $target (plan detect)" \
        '.status' \
        deploy-and-report.sh "$ORG" --target "$target" --trigger "${RF_FLAGS[@]}" \
        || true
    fi
  elif [ "$(get_flag QUEUE_OK "$target" true)" != "true" ]; then
    record_dependency_skip "service-omni-routing-flow-deploy" \
      "service-omni-routing-flow-deploy-${target}" \
      "Routing flow for $target (skipped)" \
      "Prerequisite service-omni-queue-deploy did not succeed for $target; the routing flow has no queue to route to."
  elif [ "$(get_flag QUEUE_MEMBERS_OK "$target" false)" != "true" ]; then
    # Never route to an empty queue: members must be fully bound (bound/reused) first.
    record_dependency_skip "service-omni-routing-flow-deploy" \
      "service-omni-routing-flow-deploy-${target}" \
      "Routing flow for $target (skipped)" \
      "Prerequisite service-omni-queue-members-assign did not fully succeed for $target; refusing to deploy the routing flow to a queue with no bound members."
  elif [ "$ROUTING_TYPE" = "SkillsBased" ] && { [ "$SBR_READY" != "true" ] || [ "$WSR_READY" != "true" ]; }; then
    record_dependency_skip "service-omni-routing-flow-deploy" \
      "service-omni-routing-flow-deploy-${target}" \
      "SkillsBased routing flow for $target (skipped)" \
      "SkillsBased prerequisites did not complete: agent skill bindings ready=$SBR_READY, WorkSkillRouting ready=$WSR_READY. Refusing to activate a flow that could create a PSR without SkillRequirement rows."
  else
    SERVICE_CHANNEL_DEVELOPER_NAME="$rf_channel" QUEUE_DEVELOPER_NAME="$rf_queue" ROUTING_CONFIG_DEVELOPER_NAME="$rf_qrc" \
    run_skill "service-omni-routing-flow-deploy" \
      "service-omni-routing-flow-deploy-${target}" \
      "Routing flow for $target (record-triggered deploy)" \
      '.status' \
      deploy-and-report.sh "$ORG" --target "$target" --trigger "${RF_FLAGS[@]}" \
      || true
  fi
done

# ---- Presence status (per target - chained to service-channel's discovered channel DN) ----
# Needs base settings + the target's ServiceChannel (the Available_<X> status binds to it).
for target in "${ROUTING_TARGETS[@]}"; do
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" != "true" ]; then
      record_plan_pending "service-omni-presence-status-deploy" \
        "service-omni-presence-status-deploy-${target}" \
        "Presence statuses for $target (pending)" \
        "Omni-Channel is not yet enabled; presence statuses for $target will deploy after base settings."
    else
      sc_artifact="$ARTIFACTS_DIR/service-omni-service-channel-configure-${target}.json"
      channel_dn=""
      [ -f "$sc_artifact" ] && channel_dn=$(jq -r '.channel_developer_name // ""' "$sc_artifact" 2>/dev/null || true)
      if [ -n "$channel_dn" ] && [[ "$channel_dn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
        run_skill "service-omni-presence-status-deploy" \
          "service-omni-presence-status-deploy-${target}" \
          "Presence statuses for $target (plan detect, channel $channel_dn)" \
          '.status' \
          deploy-and-report.sh "$ORG" "$target" "$channel_dn" || true
      else
        run_skill "service-omni-presence-status-deploy" \
          "service-omni-presence-status-deploy-${target}" \
          "Presence statuses for $target (plan detect, default channel)" \
          '.status' \
          deploy-and-report.sh "$ORG" "$target" || true
      fi
    fi
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-presence-status-deploy" \
      "service-omni-presence-status-deploy-${target}" \
      "Presence statuses for $target (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping presence-status deploy for $target."
  elif [ "$(get_flag SC_OK "$target" true)" != "true" ]; then
    record_dependency_skip "service-omni-presence-status-deploy" \
      "service-omni-presence-status-deploy-${target}" \
      "Presence statuses for $target (skipped)" \
      "Prerequisite service-omni-service-channel-configure did not succeed for $target; the Available_$target status has no channel to bind to."
  else
    sc_artifact="$ARTIFACTS_DIR/service-omni-service-channel-configure-${target}.json"
    channel_dn=""
    if [ -f "$sc_artifact" ]; then
      channel_dn=$(jq -r '.channel_developer_name // ""' "$sc_artifact" 2>/dev/null || true)
    fi
    if [ -n "$channel_dn" ] && [[ "$channel_dn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
      run_skill "service-omni-presence-status-deploy" \
        "service-omni-presence-status-deploy-${target}" \
        "Presence statuses for $target (bound to $channel_dn)" \
        '.status' \
        deploy-and-report.sh "$ORG" "$target" "$channel_dn" \
        || true
    else
      run_skill "service-omni-presence-status-deploy" \
        "service-omni-presence-status-deploy-${target}" \
        "Presence statuses for $target (channel DN unresolved, using skill default)" \
        '.status' \
        deploy-and-report.sh "$ORG" "$target" \
        || true
    fi
  fi
done

# Optional rep-experience stages (opt-in OMNI_REP_EXPERIENCE=1, default off): presence-user-config
# and sidebar-enable. SkillsBased prerequisites run earlier whenever SkillsBased routing is requested.
if [ "${OMNI_REP_EXPERIENCE:-0}" = "1" ]; then
  # ---- Presence user config (decline + decline reason + ACW), once ----
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ]; then
      AGENT_USERNAMES_CSV="$REP_AGENT_USERNAMES" run_skill "service-omni-presence-user-config-deploy" \
        "service-omni-presence-user-config-deploy" \
        "Presence user config (plan detect)" \
        '.status' \
        deploy-and-report.sh "$ORG" || true
    else
      record_plan_pending "service-omni-presence-user-config-deploy" \
        "service-omni-presence-user-config-deploy" \
        "Presence user config (pending)" \
        "Omni-Channel is not yet enabled; the presence user config will deploy after base settings."
    fi
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-presence-user-config-deploy" \
      "service-omni-presence-user-config-deploy" \
      "Presence user config (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping presence user config."
  else
    AGENT_USERNAMES_CSV="$REP_AGENT_USERNAMES" run_skill "service-omni-presence-user-config-deploy" \
      "service-omni-presence-user-config-deploy" \
      "Presence user config (Metadata deploy)" \
      '.status' \
      deploy-and-report.sh "$ORG" \
      || true
  fi

  # ---- Omni sidebar ---- (empty OMNI_CONSOLE_APP => leaf auto-detects the console app)
  SIDEBAR_APP="${OMNI_CONSOLE_APP:-}"
  if [ "$MODE" = "plan" ]; then
    if [ "$BASE_ENABLED" = "true" ]; then
      run_skill "service-omni-sidebar-configure" \
        "service-omni-sidebar-configure" \
        "Omni sidebar (plan detect)" \
        '.status' \
        enable-and-report.sh "$ORG" "$SIDEBAR_APP" || true
    else
      record_plan_pending "service-omni-sidebar-configure" \
        "service-omni-sidebar-configure" \
        "Omni sidebar (pending)" \
        "Omni-Channel is not yet enabled; the sidebar will be enabled after base settings."
    fi
  elif [ "$BASE_OK" != "true" ]; then
    record_dependency_skip "service-omni-sidebar-configure" \
      "service-omni-sidebar-configure" \
      "Omni sidebar (skipped)" \
      "Prerequisite service-omni-base-settings-configure did not succeed; skipping sidebar enablement."
  else
    run_skill "service-omni-sidebar-configure" \
      "service-omni-sidebar-configure" \
      "Omni sidebar (CustomApplication deploy)" \
      '.status' \
      enable-and-report.sh "$ORG" "$SIDEBAR_APP" \
      || true
  fi
fi

# ---- Permission set assign (Omni_Agent) ----
# Needs agent users to exist.
if [ "$MODE" = "plan" ]; then
  if [ "$AGENT_USERS_PRESENT" = "true" ]; then
    run_skill "service-omni-permission-set-assign" \
      "service-omni-permission-set-assign" \
      "Omni_Agent PSA (plan detect)" \
      '.status' \
      verify-and-assign.sh "$ORG" "$COUNT" "Omni_Agent" || true
  else
    record_plan_pending "service-omni-permission-set-assign" \
      "service-omni-permission-set-assign" \
      "Omni_Agent PSA (pending)" \
      "Agent users are not yet created; the Omni_Agent permission-set assignment will run after they exist."
  fi
elif [ "$AGENT_USERS_OK" != "true" ]; then
  record_dependency_skip "service-omni-permission-set-assign" \
    "service-omni-permission-set-assign" \
    "Omni_Agent PSA (skipped)" \
    "Prerequisite service-omni-agent-users-create did not succeed; no agent users to assign Omni_Agent to."
else
  run_skill "service-omni-permission-set-assign" \
    "service-omni-permission-set-assign" \
    "Omni_Agent to users (Data API POST)" \
    '.status' \
    verify-and-assign.sh "$ORG" "$COUNT" "Omni_Agent" \
    || true
fi

# ---- Supervisor users (create N; independent of routing targets) ----
# On Service Cloud User (Omni Supervisor is a Service Cloud feature; the Salesforce license pool is
# often exhausted on demo orgs). detect-and-create runs a real read-only detector in --plan.
run_skill "service-omni-supervisor-users-create" \
  "service-omni-supervisor-users-create" \
  "Supervisor users (detect + create when missing)" \
  '.status' \
  detect-and-create.sh "$MODE" "$ORG" "$SUPERVISOR_COUNT" "$SUPERVISOR_PROFILE" \
  || SUPERVISOR_USERS_OK="false"

if [ "$MODE" = "plan" ]; then
  su_art="$ARTIFACTS_DIR/service-omni-supervisor-users-create.json"
  if [ -f "$su_art" ] && [ "$(jq -r '.status // ""' "$su_art" 2>/dev/null)" = "reused" ]; then
    SUPERVISOR_USERS_PRESENT="true"
  fi
fi

# ---- Supervisor permset (ContactCenterSupervisor to supervisor users) ----
# Needs supervisor users. Use standard ContactCenterSupervisor, not custom Omni_Supervisor (which
# re-declares license-gated perms that fail on standard licenses); the leaf already defaults to it.
if [ "$MODE" = "plan" ]; then
  if [ "$SUPERVISOR_USERS_PRESENT" = "true" ]; then
    run_skill "service-omni-supervisor-permset-assign" \
      "service-omni-supervisor-permset-assign" \
      "ContactCenterSupervisor PSA (plan detect)" \
      '.status' \
      verify-and-assign.sh "$ORG" "$SUPERVISOR_COUNT" "ContactCenterSupervisor" || true
  else
    record_plan_pending "service-omni-supervisor-permset-assign" \
      "service-omni-supervisor-permset-assign" \
      "ContactCenterSupervisor PSA (pending)" \
      "Supervisor users are not yet created; the ContactCenterSupervisor permission-set assignment will run after they exist."
  fi
elif [ "$SUPERVISOR_USERS_OK" != "true" ]; then
  record_dependency_skip "service-omni-supervisor-permset-assign" \
    "service-omni-supervisor-permset-assign" \
    "ContactCenterSupervisor PSA (skipped)" \
    "Prerequisite service-omni-supervisor-users-create did not succeed; no supervisor users to assign ContactCenterSupervisor to."
else
  run_skill "service-omni-supervisor-permset-assign" \
    "service-omni-supervisor-permset-assign" \
    "ContactCenterSupervisor to supervisor users (Data API POST)" \
    '.status' \
    verify-and-assign.sh "$ORG" "$SUPERVISOR_COUNT" "ContactCenterSupervisor" \
    || true
fi

# ---- Command Center surface analysis (read-only advisory) ----
# Reports whether the org is on the classic Omni Supervisor surface or Command Center V2 (Enhanced
# Omni-Channel). Advisory only: this coordinator configures the classic surface; V2 enablement is an
# org-preference flip outside the Metadata API. It never writes, so it runs identically in plan and
# run and never hard-blocks - ambiguous detection surfaces as yellow, a clean read as green.
run_skill "service-omni-command-center-analyze" \
  "service-omni-command-center-analyze" \
  "Command Center surface analysis (classic vs V2, read-only)" \
  '(if .status=="detected" then "ok" else "action_needed" end)' \
  analyze.sh "$ORG" \
  || true

# ---- Supervisor config (deploy OmniSupervisorConfig binding supervisors + queues) ----
# Needs base settings + supervisor users. Pass the actual discovered queue DeveloperNames so it
# binds the real (possibly reused) queues, not the skill's canonical defaults.
if [ "$MODE" = "plan" ]; then
  if [ "$BASE_ENABLED" != "true" ]; then
    record_plan_pending "service-omni-supervisor-config-deploy" \
      "service-omni-supervisor-config-deploy" \
      "OmniSupervisorConfig (pending)" \
      "Omni-Channel is not yet enabled; the OmniSupervisorConfig will deploy after base settings."
  elif [ "$SUPERVISOR_USERS_PRESENT" != "true" ]; then
    record_plan_pending "service-omni-supervisor-config-deploy" \
      "service-omni-supervisor-config-deploy" \
      "OmniSupervisorConfig (pending)" \
      "Supervisor users are not yet created; the OmniSupervisorConfig will deploy after they exist."
  else
    DISCOVERED_QUEUES_CSV=""
    for target in "${ROUTING_TARGETS[@]}"; do
      [ "$(get_flag QUEUE_OK "$target" true)" = "true" ] || continue
      q_artifact="$ARTIFACTS_DIR/service-omni-queue-deploy-${target}.json"
      [ -f "$q_artifact" ] || continue
      qdn=$(jq -r '.developer_name // ""' "$q_artifact" 2>/dev/null || true)
      if [ -n "$qdn" ] && [ "$qdn" != "null" ] && [[ "$qdn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
        if [ -z "$DISCOVERED_QUEUES_CSV" ]; then
          DISCOVERED_QUEUES_CSV="$qdn"
        else
          DISCOVERED_QUEUES_CSV="$DISCOVERED_QUEUES_CSV,$qdn"
        fi
      fi
    done
    run_skill "service-omni-supervisor-config-deploy" \
      "service-omni-supervisor-config-deploy" \
      "OmniSupervisorConfig (plan detect)" \
      '.status' \
      deploy-and-report.sh "$ORG" "$SUPERVISOR_COUNT" "$DISCOVERED_QUEUES_CSV" "" "" "$SUPERVISOR_CONFIG_DN" || true
  fi
elif [ "$BASE_OK" != "true" ]; then
  record_dependency_skip "service-omni-supervisor-config-deploy" \
    "service-omni-supervisor-config-deploy" \
    "OmniSupervisorConfig (skipped)" \
    "Prerequisite service-omni-base-settings-configure did not succeed; skipping OmniSupervisorConfig deploy."
elif [ "$SUPERVISOR_USERS_OK" != "true" ]; then
  record_dependency_skip "service-omni-supervisor-config-deploy" \
    "service-omni-supervisor-config-deploy" \
    "OmniSupervisorConfig (skipped)" \
    "Prerequisite service-omni-supervisor-users-create did not succeed; no supervisor users to bind into the OmniSupervisorConfig."
else
  # Actual queue DeveloperNames from succeeded queue-deploy artifacts (authoritative over defaults).
  DISCOVERED_QUEUES_CSV=""
  for target in "${ROUTING_TARGETS[@]}"; do
    [ "$(get_flag QUEUE_OK "$target" true)" = "true" ] || continue
    q_artifact="$ARTIFACTS_DIR/service-omni-queue-deploy-${target}.json"
    [ -f "$q_artifact" ] || continue
    qdn=$(jq -r '.developer_name // ""' "$q_artifact" 2>/dev/null || true)
    if [ -n "$qdn" ] && [ "$qdn" != "null" ] && [[ "$qdn" =~ ^[A-Za-z0-9_]{1,80}$ ]]; then
      if [ -z "$DISCOVERED_QUEUES_CSV" ]; then
        DISCOVERED_QUEUES_CSV="$qdn"
      else
        DISCOVERED_QUEUES_CSV="$DISCOVERED_QUEUES_CSV,$qdn"
      fi
    fi
  done

  run_skill "service-omni-supervisor-config-deploy" \
    "service-omni-supervisor-config-deploy" \
    "OmniSupervisorConfig deploy (Metadata API)" \
    '.status' \
    deploy-and-report.sh "$ORG" "$SUPERVISOR_COUNT" "$DISCOVERED_QUEUES_CSV" "" "" "$SUPERVISOR_CONFIG_DN" \
    || true
fi

# Derive the supervisor-config disposition (from its artifact) to gate the surface stage below.
# plan: PRESENT iff the config already exists (status reused); run: OK iff it now exists.
supcfg_art="$ARTIFACTS_DIR/service-omni-supervisor-config-deploy.json"
supcfg_status=""
SUPERVISOR_CONFIG_RESOLVED_DN="$SUPERVISOR_CONFIG_DN"
[ -f "$supcfg_art" ] && supcfg_status=$(jq -r '.status // ""' "$supcfg_art" 2>/dev/null || echo "")
if [ -f "$supcfg_art" ]; then
  artifact_config_dn=$(jq -r '.config_developer_name // ""' "$supcfg_art" 2>/dev/null || echo "")
  if [[ "$artifact_config_dn" =~ ^[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
    SUPERVISOR_CONFIG_RESOLVED_DN="$artifact_config_dn"
  fi
fi
if [ "$MODE" = "plan" ]; then
  [ "$supcfg_status" = "reused" ] && SUPERVISOR_CONFIG_PRESENT="true"
else
  case "$supcfg_status" in created|updated|reused) SUPERVISOR_CONFIG_OK="true" ;; *) SUPERVISOR_CONFIG_OK="false" ;; esac
fi

# ---- Supervisor surface (Action + Tab companions on the OmniSupervisorConfig) ----
# Needs base settings + an OmniSupervisorConfig. Inserts the standard action/tab rows via the Data
# API against the parent config's Id - independent of the config metadata file and idempotent.
if [ "$MODE" = "plan" ]; then
  if [ "$BASE_ENABLED" != "true" ]; then
    record_plan_pending "service-omni-supervisor-surface-deploy" \
      "service-omni-supervisor-surface-deploy" \
      "Supervisor action/tab surface (pending)" \
      "Omni-Channel is not yet enabled; the supervisor action/tab surface will be populated after base settings."
  elif [ "$SUPERVISOR_CONFIG_PRESENT" != "true" ]; then
    record_plan_pending "service-omni-supervisor-surface-deploy" \
      "service-omni-supervisor-surface-deploy" \
      "Supervisor action/tab surface (pending)" \
      "OmniSupervisorConfig is not yet present; the supervisor action/tab surface will be populated after the config is deployed."
  else
    run_skill "service-omni-supervisor-surface-deploy" \
      "service-omni-supervisor-surface-deploy" \
      "Supervisor action/tab surface (plan detect)" \
      '.status' \
      deploy-and-report.sh "$ORG" "$SUPERVISOR_CONFIG_RESOLVED_DN" || true
  fi
elif [ "$BASE_OK" != "true" ]; then
  record_dependency_skip "service-omni-supervisor-surface-deploy" \
    "service-omni-supervisor-surface-deploy" \
    "Supervisor action/tab surface (skipped)" \
    "Prerequisite service-omni-base-settings-configure did not succeed; skipping the supervisor action/tab surface."
elif [ "$SUPERVISOR_CONFIG_OK" != "true" ]; then
  record_dependency_skip "service-omni-supervisor-surface-deploy" \
    "service-omni-supervisor-surface-deploy" \
    "Supervisor action/tab surface (skipped)" \
    "Prerequisite service-omni-supervisor-config-deploy did not succeed; no OmniSupervisorConfig to populate the action/tab surface on."
else
  run_skill "service-omni-supervisor-surface-deploy" \
    "service-omni-supervisor-surface-deploy" \
    "Supervisor action/tab surface (Data API inserts)" \
    '.status' \
    deploy-and-report.sh "$ORG" "$SUPERVISOR_CONFIG_RESOLVED_DN" || true
fi

OVERALL_END=$(date +%s)
TOTAL_ELAPSED=$((OVERALL_END - OVERALL_START))

# Run artifacts (run mode only): run.log (sanitized sequence + result), deploy_ids.json (provenance
# manifest per skill), teardown.sh (dry-run reverse-order plan; makes NO changes - removal is manual).
RUN_LOG=""
DEPLOY_IDS=""
TEARDOWN=""
if [ "$MODE" = "run" ]; then
  RUN_LOG="$ARTIFACTS_DIR/run.log"
  DEPLOY_IDS="$ARTIFACTS_DIR/deploy_ids.json"
  TEARDOWN="$ARTIFACTS_DIR/teardown.sh"

  {
    echo "# Omni coordinator run log"
    echo "# org=$ORG mode=$MODE timestamp=$TIMESTAMP"
    echo "# overall_status=$OVERALL_STATUS elapsed=${TOTAL_ELAPSED}s"
    echo "#"
    echo "$SKILL_RESULTS" | jq -r '.[] | "[\(.elapsed_sec)s] \(.invocation_key) → \(.status) (\(.color))"'
  } > "$RUN_LOG"
  chmod 600 "$RUN_LOG" 2>/dev/null || true

  DEPLOY_MANIFEST='[]'
  while IFS= read -r res; do
    [ -z "$res" ] && continue
    key=$(echo "$res" | jq -r '.invocation_key')
    skill=$(echo "$res" | jq -r '.name')
    status=$(echo "$res" | jq -r '.status')
    color=$(echo "$res" | jq -r '.color')
    art=$(echo "$res" | jq -r '.artifact_path // ""')
    case "$status" in
      created|deployed)                               prov="created" ;;
      updated)                                        prov="updated" ;;
      reused|assigned|bound|configured|ok|success|skipped) prov="reused" ;;
      *)                                              prov="none" ;;
    esac
    ids='[]'; before='null'; devname='null'
    # Require a NON-EMPTY artifact (-s, not -f): a leaf that crashed can leave a 0-byte file, and
    # jq over empty input yields an empty string (not "null"), which would make --argjson below throw
    # and abort the whole run under set -e before the final report. Empty-string results are also
    # normalized back to valid JSON as a second guard.
    if [ -n "$art" ] && [ "$art" != "null" ] && [ -s "$art" ]; then
      ids=$(jq -c '[ .id?, .developer_name?, .channel_developer_name?,
                     (.created_users[]?.id), (.agents[]?.service_resource_id),
                     (.assignments[]?.id) ] | map(select(. != null and . != "" and . != "null"))' "$art" 2>/dev/null || echo '[]')
      before=$(jq -c '.before? // null' "$art" 2>/dev/null || echo 'null')
      devname=$(jq -r '.developer_name // "null"' "$art" 2>/dev/null || echo 'null')
      [ -z "$ids" ] && ids='[]'
      [ -z "$before" ] && before='null'
      [ -z "$devname" ] && devname='null'
    fi
    DEPLOY_MANIFEST=$(echo "$DEPLOY_MANIFEST" | jq -c \
      --arg key "$key" --arg skill "$skill" --arg status "$status" --arg color "$color" \
      --arg prov "$prov" --arg art "$art" --arg dn "$devname" \
      --argjson ids "$ids" --argjson before "$before" \
      '. + [{invocation_key:$key, skill:$skill, status:$status, color:$color, provenance:$prov, developer_name:(if $dn=="null" then null else $dn end), resource_ids:$ids, before:$before, artifact_path:(if $art=="" then null else $art end)}]')
  done < <(echo "$SKILL_RESULTS" | jq -c '.[]')

  jq -n --arg org "$ORG" --arg ts "$TIMESTAMP" --argjson entries "$DEPLOY_MANIFEST" \
    '{coordinator:"service-omni-channel-setup-coordinate", org_alias:$org, timestamp:$ts, note:"Provenance manifest. Per-skill artifacts remain the source of truth. Only entries with provenance=created were created by this run.", entries:$entries}' > "$DEPLOY_IDS"
  chmod 600 "$DEPLOY_IDS" 2>/dev/null || true

  cat > "$TEARDOWN" <<TDEOF
#!/usr/bin/env bash
# AUTO-GENERATED teardown plan for the Omni coordinator run at $TIMESTAMP (org $ORG).
# DRY-RUN: prints a reverse-order plan, makes NO changes. Removal is manual - metadata components
# need destructiveChanges deploys, only run-created resources may be removed, reused records never.
set -euo pipefail
ORG="$ORG"
MANIFEST="\$(cd "\$(dirname "\$0")" && pwd)/deploy_ids.json"
if [ ! -f "\$MANIFEST" ]; then echo "manifest not found: \$MANIFEST" >&2; exit 1; fi
echo "Teardown plan (reverse dependency order) for org \$ORG"
echo "Source manifest: \$MANIFEST"
echo ""
jq -r '.entries | reverse | .[]
  | if .provenance=="created" then
      "REMOVE   \(.invocation_key): created \((.developer_name // (.resource_ids | join(", "))) // "-")  [artifact: \(.artifact_path // "-")]"
    elif .provenance=="updated" then
      "RESTORE  \(.invocation_key): restore prior values \(.before | tojson)  [artifact: \(.artifact_path // "-")]"
    else
      "KEEP     \(.invocation_key): \(.status) - adopted/reused, do not delete"
    end' "\$MANIFEST"
echo ""
echo "Plan only - no changes made. Reverse each REMOVE using its per-skill artifact; metadata"
echo "components need a destructiveChanges deploy; data records use sf api request rest --method DELETE."
TDEOF
  chmod 700 "$TEARDOWN" 2>/dev/null || true
fi

echo "" >&2
# The create leaves now escrow directly into CREDENTIALS_FILE, so recognise that too (redact_credentials
# only flips CREDENTIALS_WRITTEN when it finds plaintext to move, which no longer happens).
if [ "$CREDENTIALS_WRITTEN" != "true" ] && [ -s "$CREDENTIALS_FILE" ]; then
  chmod 600 "$CREDENTIALS_FILE" 2>/dev/null || true
  CREDENTIALS_WRITTEN="true"
fi
if [ "$CREDENTIALS_WRITTEN" = "true" ]; then
  echo "  Generated credentials written to (mode 0600): $CREDENTIALS_FILE" >&2
  echo "     Read them once, distribute securely, then delete: rm -f \"$CREDENTIALS_FILE\"" >&2
  echo "     Passwords have been redacted from all other artifacts." >&2
  echo "" >&2
fi
jq -n \
  --arg org "$ORG" \
  --arg mode "$MODE" \
  --arg timestamp "$TIMESTAMP" \
  --arg artifacts_dir "$ARTIFACTS_DIR" \
  --arg overall_status "$OVERALL_STATUS" \
  --arg blocking_skill "$BLOCKING_SKILL" \
  --arg first_yellow_skill "$FIRST_YELLOW_SKILL" \
  --argjson attention_leaves "$ATTENTION_LEAVES" \
  --argjson total_elapsed "$TOTAL_ELAPSED" \
  --argjson results "$SKILL_RESULTS" \
  --argjson requested_count "$COUNT" \
  --argjson requested_supervisor_count "$SUPERVISOR_COUNT" \
  --arg routing_targets "$ROUTING_TARGETS_CSV" \
  --argjson safe_to_write true \
  --arg credentials_file "$CREDENTIALS_FILE" \
  --arg credentials_written "$CREDENTIALS_WRITTEN" \
  --arg run_log "$RUN_LOG" \
  --arg deploy_ids_file "$DEPLOY_IDS" \
  --arg teardown_script "$TEARDOWN" \
  '{
    coordinator: "service-omni-channel-setup-coordinate",
    mode: $mode,
    dry_run: ($mode == "plan"),
    org_alias: $org,
    timestamp: $timestamp,
    safe_to_write: $safe_to_write,
    run_log: (if $run_log == "" then null else $run_log end),
    deploy_ids_file: (if $deploy_ids_file == "" then null else $deploy_ids_file end),
    teardown_script: (if $teardown_script == "" then null else $teardown_script end),
    requested_count: $requested_count,
    requested_supervisor_count: $requested_supervisor_count,
    routing_targets: ($routing_targets | split(",")),
    artifacts_dir: $artifacts_dir,
    credentials_file: (if $credentials_written == "true" then $credentials_file else null end),
    credentials_note: (if $credentials_written == "true" then "Generated passwords are in credentials_file (mode 0600) and redacted from all other artifacts. Read once, distribute securely, then delete." else null end),
    overall_status: $overall_status,
    blocking_skill: (if $blocking_skill == "" then null else $blocking_skill end),
    first_attention_skill: (if $first_yellow_skill == "" then null else $first_yellow_skill end),
    attention_leaves: $attention_leaves,
    total_elapsed_sec: $total_elapsed,
    leaves_executed: ($results | length),
    skills: $results,
    exit_semantics: "exit 0 iff overall_status == green. yellow exits 2 (setup work still required). red exits 1 (blocked)."
  }'

case "$OVERALL_STATUS" in
  green)  exit 0 ;;
  yellow) exit 2 ;;
  red)    exit 1 ;;
  *)      exit 1 ;;
esac
