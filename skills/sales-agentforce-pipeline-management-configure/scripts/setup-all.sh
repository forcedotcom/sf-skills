#!/bin/bash
# Master orchestration script for Pipeline Management end-to-end setup
# Handles both greenfield and partially-configured orgs.
#
# Architecture: Each phase uses a "harness loop" pattern:
#   1. Check if already done (skip if yes)
#   2. Try primary approach (SOAP Metadata API)
#   3. If primary fails, try fallback (CLI retrieve/modify/deploy)
#   4. If fallback fails, try tertiary (Tooling API / REST)
#   5. VERIFY the result via readMetadata before proceeding
#   6. Only report BLOCKER after ALL approaches exhausted
#
# Working Directory Note:
#   Agent bundle publishing uses isolated temp directories with automatic cleanup.
#   Settings/flow deployment operations may create force-app/ in the current directory
#   when SOAP/Tooling API approaches fail and CLI deploy is attempted as fallback.
#
# Usage: ./setup-all.sh <org-alias> [flags]
#
# Flags (all optional; SAFE by default):
#   --autonomous                 Enable autonomous field updates (agent auto-applies
#                                without human review). OFF by default — suggestions only.
#   --create-stage-descriptions  Create sales-methodology stage descriptions (needed only
#                                for StageName suggestions). OFF by default.
#   --non-interactive | --yes    Run without prompts. Combined with the flags above this
#                                gives fully unattended setup; without them the run stays
#                                on the safe (suggestion-only, no stage-desc) defaults.
#   --users "a@x.com,b@x.com"    Explicit comma-separated usernames to also grant the
#                                SalesManagementUserPsg (in addition to the running user).
#                                This is the ONLY non-interactive way to add users — the
#                                script NEVER queries all/standard users and bulk-assigns.

set -euo pipefail

# Require bash 4.0+ for associative arrays (macOS ships bash 3.2 by default)
if [[ ${BASH_VERSINFO[0]} -lt 4 ]]; then
  echo "ERROR: bash 4.0+ required. Your version: $BASH_VERSION"
  echo "On macOS, install via: brew install bash"
  echo "Then run: /opt/homebrew/bin/bash $0 $*"
  exit 1
fi

# Set consistent locale to prevent jq parsing issues with special characters
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
# Exported here so they propagate to sourced libs and child bash subprocesses.
export NO_COLOR=1
export FORCE_COLOR=0

ORG_ALIAS="${1:-}"
# Validate org alias (prevent shell injection via metacharacters)
if [[ -n "$ORG_ALIAS" && ! "$ORG_ALIAS" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
  echo "ERROR: Invalid org alias. Only alphanumeric, dots, hyphens, and underscores allowed (must start with alphanumeric)."
  exit 1
fi

# --- Consent flags (SAFE by default) ---
# Autonomous updates and stage-description creation are BOTH opt-in. In non-interactive
# mode we never enable them implicitly; the operator must pass the explicit flag.
ENABLE_AUTONOMOUS=false        # --autonomous
CREATE_STAGE_DESCRIPTIONS=false # --create-stage-descriptions
NON_INTERACTIVE=false          # --non-interactive | --yes (also implied when stdin is not a TTY)
USERS_LIST=""                  # --users "a@x.com,b@x.com" — explicit PSG grantees (never bulk)

# --- Field selection (3-phase setup) ---
# Which Opportunity fields the suggestion flow should manage. Chosen UP FRONT
# (before the flow is built) so the flow is built with ONLY these fields — no
# deploy-then-strip. At least one field is REQUIRED; setup ABORTS if none are
# selected (there is no silent default). OOTB fields (NextStep, StageName) count
# toward the 5-field cap. Per-field goal/instruction customization is collected
# into FIELD_PROMPTS keyed "<Field>_goal" / "<Field>_instruction".
SELECTED_FIELDS=""             # --fields "NextStep,StageName,Risk__c"
SKIP_PROMPT_VERIFICATION=false # --skip-prompt-verification (bypass the Phase 2e gate)
declare -A FIELD_PROMPTS       # per-field goal/instruction, from --field-goal/--field-instruction
readonly MAX_SUGGESTION_FIELDS=5

# --- Phase split (agent-driven interactive tune-loop) ---
# The full run is one long non-interactive pass, which (a) can't pause for the
# agent to tune each field's prompt with the user and (b) can exceed the harness
# tool timeout. --through-phase / --from-phase cut the run at the prompt boundary
# so the AGENT owns the interactive tune-loop BETWEEN two calls:
#   Call 1: --through-phase prompts  → enable, provision, deploy+activate templates,
#           then STOP before the flow is built (context phases 0/1/1.7 always run).
#   (agent tunes each field via add-field-suggestion.sh --verify-with-note --note …)
#   Call 2: --from-phase flow        → build+activate flow, agent, PSG, final verify.
# Both calls are idempotent, so this is a resumable checkpoint, not new state.
# Recognized cut points: "prompts" (end of Phase 4d) and "flow" (start of Phase 5).
RUN_FROM_PHASE=""              # --from-phase flow   (skip everything before Phase 5)
RUN_THROUGH_PHASE=""           # --through-phase prompts (stop after templates, before flow)

# --- License preflight (agent's first action, before any clarifying question) ---
# --check-license runs ONLY auth + the Phase 0.5 capability gate, then exits. It
# takes no --fields (so it can run before the field questions the gate must
# precede), asks nothing, and mutates nothing. The SKILL drives this FIRST so an
# unlicensed org is blocked before the user is asked anything.
CHECK_LICENSE_ONLY=false       # --check-license

# Parse flags after the positional org alias. `shift` past $1 first if present.
if [[ $# -ge 1 ]]; then shift || true; fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --autonomous)                 ENABLE_AUTONOMOUS=true; shift ;;
    --create-stage-descriptions)  CREATE_STAGE_DESCRIPTIONS=true; shift ;;
    --non-interactive|--yes)      NON_INTERACTIVE=true; shift ;;
    --check-license)              CHECK_LICENSE_ONLY=true; shift ;;
    --skip-prompt-verification)   SKIP_PROMPT_VERIFICATION=true; shift ;;
    --users)                      { [[ $# -ge 2 ]] && [[ "$2" != --* ]]; } || { echo "ERROR: --users requires a value (comma-separated usernames), e.g. --users \"a@x.com,b@x.com\""; exit 1; }
                                  IFS=',' read -ra _TMP_USERS <<< "$2"
                                  for _u in "${_TMP_USERS[@]}"; do
                                    _u=$(echo "$_u" | xargs)
                                    [[ "$_u" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]] || { echo "ERROR: Invalid email format in --users: '$_u'. Each value must be a valid email address."; exit 1; }
                                  done
                                  USERS_LIST="$2"; shift 2 ;;
    --fields)                     { [[ $# -ge 2 ]] && [[ "$2" != --* ]]; } || { echo "ERROR: --fields requires a value (comma-separated field API names), e.g. --fields \"NextStep,Risk__c\""; exit 1; }; SELECTED_FIELDS="$2"; shift 2 ;;
    --field-goal)                 { [[ $# -ge 2 ]] && [[ "$2" == *:* ]]; } || { echo "ERROR: --field-goal requires \"FieldApiName:goal text\""; exit 1; }; FIELD_PROMPTS["${2%%:*}_goal"]="${2#*:}"; shift 2 ;;
    --field-instruction)          { [[ $# -ge 2 ]] && [[ "$2" == *:* ]]; } || { echo "ERROR: --field-instruction requires \"FieldApiName:instruction text\""; exit 1; }; FIELD_PROMPTS["${2%%:*}_instruction"]="${2#*:}"; shift 2 ;;
    --through-phase)              { [[ $# -ge 2 ]] && [[ "$2" != --* ]]; } || { echo "ERROR: --through-phase requires a value (currently: prompts)"; exit 1; }; RUN_THROUGH_PHASE="$2"; shift 2 ;;
    --from-phase)                 { [[ $# -ge 2 ]] && [[ "$2" != --* ]]; } || { echo "ERROR: --from-phase requires a value (currently: flow)"; exit 1; }; RUN_FROM_PHASE="$2"; shift 2 ;;
    *) echo "ERROR: Unknown option: $1"; echo "Usage: $0 <org-alias> [--check-license] [--fields \"NextStep,StageName,Risk__c\"] [--field-goal \"Field:text\"] [--field-instruction \"Field:text\"] [--through-phase prompts] [--from-phase flow] [--autonomous] [--create-stage-descriptions] [--skip-prompt-verification] [--non-interactive|--yes] [--users \"a@x.com,b@x.com\"]"; exit 1 ;;
  esac
done

# --- Validate phase-split flags ---
# Only "prompts" (--through-phase) and "flow" (--from-phase) are recognized. They
# are the two ends of the split; passing both, or an unknown name, is rejected so a
# typo never silently runs the whole thing.
if [[ -n "$RUN_THROUGH_PHASE" && "$RUN_THROUGH_PHASE" != "prompts" ]]; then
  echo "ERROR: --through-phase supports only 'prompts' (got '$RUN_THROUGH_PHASE')."; exit 1
fi
if [[ -n "$RUN_FROM_PHASE" && "$RUN_FROM_PHASE" != "flow" ]]; then
  echo "ERROR: --from-phase supports only 'flow' (got '$RUN_FROM_PHASE')."; exit 1
fi
if [[ -n "$RUN_THROUGH_PHASE" && -n "$RUN_FROM_PHASE" ]]; then
  echo "ERROR: --through-phase and --from-phase are mutually exclusive (they are the two halves of a split run)."; exit 1
fi

# A non-TTY stdin is treated as non-interactive regardless of flags, so prompts never hang.
if [[ ! -t 0 ]]; then NON_INTERACTIVE=true; fi

# The license preflight asks nothing and mutates nothing — force non-interactive
# so the Phase 0 Setup Options block (guarded below) is skipped entirely.
if [[ "$CHECK_LICENSE_ONLY" == "true" ]]; then NON_INTERACTIVE=true; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source shared libraries
source "$SCRIPT_DIR/shared/agent-bundle-publish.sh"
source "$SCRIPT_DIR/shared/soap.sh"
source "$SCRIPT_DIR/shared/psg.sh"
source "$SCRIPT_DIR/shared/flow-builder.sh"
source "$SCRIPT_DIR/shared/stage-descriptions.sh"

trap 'echo ""; echo "Setup interrupted."; exit 130' INT

# --- Configuration Constants ---
readonly API_VERSION="64.0"
readonly CURL_TIMEOUT=30
readonly SLEEP_SHORT=2
readonly SLEEP_MEDIUM=3
readonly SLEEP_LONG=5
readonly SLEEP_TOGGLE_OFF=10
readonly SLEEP_TOGGLE_ON=20

# --- Helpers ---
log_pass() { echo "  [PASS] $1"; }
log_warn() { echo "  [WARN] $1"; }
log_fail() { echo "  [FAIL] $1"; }
log_info() { echo "  [....] $1"; }
log_try()  { echo "  [TRY ] $1"; }
section()  { echo ""; echo "=== $1 ==="; echo ""; }

# with_timeout <seconds> <cmd...> — run a command under a wall-clock bound so a
# hung network call (e.g. the /generations REST request, which has no built-in
# --max-time) can't stall the whole run past the harness's tool timeout. Uses
# coreutils `timeout` (or `gtimeout`) when available; on a stock macOS that has
# neither, it degrades to running the command unwrapped rather than failing.
_TIMEOUT_BIN="$(command -v timeout 2>/dev/null || command -v gtimeout 2>/dev/null || true)"
with_timeout() {
  local secs="$1"; shift
  if [[ -n "$_TIMEOUT_BIN" ]]; then
    "$_TIMEOUT_BIN" "${secs}s" "$@"
  else
    "$@"
  fi
}

# confirm <prompt> — yes/no gate. In non-interactive mode returns the SAFE default
# (decline: return 1) without prompting. Only ever use as `if confirm ...; then`,
# never as a bare last statement (a nonzero return would trip `set -e`).
confirm() {
  local prompt="$1"
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    return 1
  fi
  local reply=""
  read -rp "  $prompt [y/N]: " reply || reply=""
  [[ "$reply" =~ ^[Yy] ]]
}

# schedule_flow_active <org-alias> — resolve the Pipeline Management suggestion flow
# using the SAME SourceTemplateId-first resolver as Phase 5 (NOT a fuzzy label match),
# and print its IsActive state as "true" | "false" | "none" (no flow found). This keeps
# the summary consistent with detection elsewhere (#6): the old summary read used a
# label LIKE '%OppSugg%' query that could miss the deployed flow and report it as
# "Not Found" even right after a successful deploy.
schedule_flow_active() {
  local org="$1" api_name="" q
  for q in \
    "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" \
    "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate=false" \
    "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = 'Process_Field_Update_Suggestions' AND IsTemplate=false"; do
    local rec
    rec=$(sf data query --query "$q" --target-org "$org" --json 2>/dev/null \
      | jq -r 'if (.result.records | length) > 0 then (if .result.records[0].IsActive == true then "true" else "false" end) else empty end' 2>/dev/null || echo "")
    if [[ -n "$rec" ]]; then printf '%s' "$rec"; return 0; fi
  done
  printf 'none'
}

# sanitize_dev_name <raw> [prefix] — derive a VALID Salesforce DeveloperName.
# DeveloperName must be alphanumeric/underscore, start with a letter, and must NOT
# contain consecutive underscores or a trailing underscore. The naive
# `tr ' ' '_' | sed 's/\./_/g'` turned "Id. Decision Makers" into "Id__Decision_Makers"
# (double underscore) which the platform REJECTS — the silent cause behind #8.
# This collapses runs of underscores, trims leading/trailing underscores, and
# ensures a leading letter.
sanitize_dev_name() {
  local raw="$1" prefix="${2:-}" name
  name=$(printf '%s' "${prefix:+${prefix}_}${raw}" \
    | tr ' ' '_' \
    | sed 's/[^A-Za-z0-9_]/_/g' \
    | sed -E 's/_+/_/g' \
    | sed -E 's/^_+//; s/_+$//')
  # DeveloperName must start with a letter.
  if [[ ! "$name" =~ ^[A-Za-z] ]]; then name="X_${name}"; fi
  printf '%s' "$name"
}

# Safe jq extraction - strips CLI warnings, handles parse failures gracefully
safe_jq() {
  local json="$1" expr="$2" default="${3:-}"
  [[ -z "$json" ]] && { printf '%s' "$default"; return; }
  local cleaned
  # Strip ANSI color escapes (sf --json can emit them into stdout), THEN find JSON start.
  cleaned=$(printf '%s' "$json" | sed -E 's/'$'\x1b''\[[0-9;]*m//g' | sed -n '/^[[:space:]]*[{[]/,$p')
  printf '%s' "$cleaned" | jq -r "$expr" 2>/dev/null || printf '%s' "$default"
}

safe_jq_int() {
  local result
  result=$(safe_jq "$1" "$2" "0")
  [[ "$result" =~ ^[0-9]+$ ]] && echo "$result" || echo "0"
}

# Progress indicators for long-running operations (write to stderr to avoid polluting piped output)
show_progress() {
  [[ -t 2 ]] || return 0
  local msg="${1:-Working...}"
  printf '\r  [....] %s...' "$msg" >&2
}

clear_progress() {
  [[ -t 2 ]] || return 0
  printf '\r\033[K' >&2
}

# Sanitize display strings (remove control chars, truncate)
sanitize_display() {
  local input="$1" max_len="${2:-80}"
  printf '%s' "$input" | tr -d '\000-\037' | cut -c1-"$max_len"
}

# Sanitize a value for safe SOQL interpolation (alphanumeric, underscores, dots, spaces, slashes)
sanitize_soql_value() {
  local input="$1"
  printf '%s' "$input" | tr -cd 'A-Za-z0-9_./ -'
}

# redact_token() is provided by shared/soap.sh (sourced above). The shared version
# fixes session-id tail under-redaction (W-23215519). Do not redefine it here.

# Helper: Get license count with error handling
# Returns: license count or "ERROR" if query fails
get_license_count() {
  local license_name="$1"
  local result
  result=$(sf data query --query "SELECT TotalLicenses FROM UserLicense WHERE Name = '$license_name'" \
    --target-org "$ORG_ALIAS" --json 2>&1)

  if echo "$result" | grep -qi "ERROR"; then
    echo "ERROR"
  else
    safe_jq "$result" '.result.records[0].TotalLicenses // 0' "0"
  fi
}

# --- State tracking for before/after summary ---
declare -A SETUP_STATE_BEFORE
declare -A SETUP_STATE_AFTER
declare -A SETUP_CHANGES
declare -a SETUP_ISSUES=()
declare -a SETUP_DEPENDENCIES=()

track_before() {
  local KEY=$1
  local VALUE=$2
  SETUP_STATE_BEFORE["$KEY"]="$VALUE"
}

track_after() {
  local KEY=$1
  local VALUE=$2
  SETUP_STATE_AFTER["$KEY"]="$VALUE"

  # Determine change status
  local BEFORE="${SETUP_STATE_BEFORE[$KEY]:-N/A}"
  if [[ "$BEFORE" == "N/A" ]]; then
    SETUP_CHANGES["$KEY"]="🆕 CREATED"
  elif [[ "$BEFORE" != "$VALUE" ]]; then
    SETUP_CHANGES["$KEY"]="✏️ CHANGED"
  else
    SETUP_CHANGES["$KEY"]="✅ NO CHANGE"
  fi
}

track_issue() {
  local SEVERITY=$1
  local DESCRIPTION=$2
  local RESOLUTION=$3
  SETUP_ISSUES+=("$SEVERITY|$DESCRIPTION|$RESOLUTION")
}

track_dependency() {
  local PHASE=$1
  local DEPENDS_ON=$2
  SETUP_DEPENDENCIES+=("$PHASE|$DEPENDS_ON")
}


if [[ -z "$ORG_ALIAS" ]]; then
  echo "Usage: $0 <org-alias> [--autonomous] [--create-stage-descriptions] [--non-interactive|--yes]"
  exit 1
fi

# ============================================================
# Phase 0: Consent preamble
# ============================================================
# Pipeline Management setup is provisioning-heavy. Two behaviours change what the
# agent does to the org and are therefore gated on explicit consent:
#   1. Autonomous field updates — the agent auto-applies suggestions with no human review.
#   2. Stage-description creation — only needed for StageName suggestions; may overwrite
#      or create descriptions the org intentionally left blank.
# Interactive runs are asked here; non-interactive runs use the SAFE resolved defaults
# (opt-in only via --autonomous / --create-stage-descriptions).
# The --check-license preflight skips this block wholesale — it decides nothing
# about provisioning behaviour and must ask the user nothing.
if [[ "$CHECK_LICENSE_ONLY" != "true" ]]; then
section "Phase 0: Setup Options"

if [[ "$NON_INTERACTIVE" == "true" ]]; then
  log_info "Non-interactive mode — using resolved options:"
else
  echo "  Before provisioning, confirm two optional behaviours (both default to OFF/safe):"
  echo ""
  # Autonomous updates: opt-in. Flag pre-answers; otherwise ask.
  if [[ "$ENABLE_AUTONOMOUS" != "true" ]]; then
    if confirm "Let the agent update fields AUTONOMOUSLY (auto-apply without human review)? Default is suggestions-only"; then
      ENABLE_AUTONOMOUS=true
    fi
  fi
  # Stage descriptions: opt-in, and only relevant if the user wants StageName suggestions.
  if [[ "$CREATE_STAGE_DESCRIPTIONS" != "true" ]]; then
    if confirm "Create sales-methodology stage descriptions (only needed for StageName suggestions)?"; then
      CREATE_STAGE_DESCRIPTIONS=true
    fi
  fi
  echo ""
fi

echo "  • Autonomous field updates:  $([[ "$ENABLE_AUTONOMOUS" == "true" ]] && echo "ENABLED (auto-apply)" || echo "off (suggestions only)")"
echo "  • Stage-description creation: $([[ "$CREATE_STAGE_DESCRIPTIONS" == "true" ]] && echo "ENABLED" || echo "off")"
fi  # END Phase 0 Setup Options (skipped under --check-license)

# ============================================================
# Phase 1: Authentication
# ============================================================
section "Phase 1: Authentication"

# Filter CLI warnings that pollute JSON output (causes jq parse errors)
# Use buffering pattern to avoid grep eating newlines that jq needs
ORG_DISPLAY_OUTPUT=$(sf org display --target-org "$ORG_ALIAS" --json 2>&1)
INSTANCE_URL=$(safe_jq "$ORG_DISPLAY_OUTPUT" '.result.instanceUrl // empty' "")
if [[ -z "$INSTANCE_URL" ]]; then
  log_fail "Cannot connect to org '$ORG_ALIAS'. Run: sf org login web --alias $ORG_ALIAS"
  exit 1
fi
# Enforce HTTPS on instance URL (prevent MITM with access tokens)
if [[ -n "$INSTANCE_URL" && ! "$INSTANCE_URL" =~ ^https:// ]]; then
  log_fail "Instance URL is not HTTPS: $INSTANCE_URL"
  log_fail "Refusing to send access tokens over insecure connection."
  exit 1
fi

# Extract access token with same warning filtering
ACCESS_TOKEN=$(safe_jq "$ORG_DISPLAY_OUTPUT" '.result.accessToken // empty' "")
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  TOKEN_OUTPUT=$(echo "y" | sf org auth show-access-token --target-org "$ORG_ALIAS" --no-prompt --json 2>&1)
  ACCESS_TOKEN=$(safe_jq "$TOKEN_OUTPUT" '.result.accessToken // empty' "")
fi

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  log_fail "Cannot extract access token. Re-authenticate: sf org login web --alias $ORG_ALIAS"
  exit 1
fi

log_pass "Connected to $(sanitize_display "$INSTANCE_URL" 80)"

# Detect test/trial/scratch orgs and warn about potential API restrictions
if [[ -n "$INSTANCE_URL" ]]; then
  if [[ "$INSTANCE_URL" =~ (test[0-9]*\.|\.pc-rnd\.|scratch|sandbox|-dev-ed\.|\.trailhead\.|--) ]]; then
    log_warn "TEST/TRIAL ORG DETECTED: $INSTANCE_URL"
    echo ""
    echo "  Note: Test, trial, and sandbox orgs may have SOAP API restrictions."
    echo "  This script will use alternative approaches (REST API, CLI) where possible."
    echo "  Some features may require manual UI enablement if API access is limited."
    echo ""
  fi
fi

# --- API Helpers ---
# NOTE: These helpers are defined here — right after Phase 1 Authentication — so
# they are available to the Step 0 capability gate (Phase 0.5, below) that must run
# BEFORE any interactive question. They depend only on INSTANCE_URL/ACCESS_TOKEN
# (set in Phase 1), API_VERSION/CURL_TIMEOUT (readonly, top), and
# show_progress/clear_progress (top-level) — nothing from Phase 1.7 onward. They
# are also used by BLOCK B (soap_read/soap_extract_bool in the AFTER snapshot,
# sed_inplace in the flow reconciliation, ensure_sfdx_project before flow/agent
# deploys); on a --from-phase flow run BLOCK A is skipped entirely, so defining
# them at this top level keeps them in scope for both blocks and Step 0.

# SOAP readMetadata — returns raw XML response
soap_read() {
  local TYPE="$1" NAME="$2"
  curl -s --max-time $CURL_TIMEOUT "${INSTANCE_URL}/services/Soap/m/${API_VERSION}" \
    -H "Content-Type: text/xml; charset=UTF-8" \
    -H "SOAPAction: readMetadata" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>${TYPE}</met:type><met:fullNames>${NAME}</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null
}

# Classify a readMetadata response via the shared shared/soap.sh parser.
# Distinguishes a genuine "false" from an auth/SOAP fault or a network/service
# error (the W-23215519 fix) instead of collapsing all three to empty.
# soap_read() does not capture an HTTP status, so "200" is passed as the
# nominal status; the parser still detects empty bodies, SOAP faults, HTML
# error pages, and truncated XML from the response content itself.
# Args: $1 = readMetadata XML, $2 = field name
# Echoes: "true" | "false" | "AUTH_ERROR:..." | "TYPE_UNAVAILABLE:..." | "NETWORK_ERROR"
soap_classify() {
  local XML="$1" FIELD="$2"
  parse_soap_response "$XML" "$FIELD" "200"
}

# SOAP updateMetadata — returns raw XML response
soap_update() {
  local BODY="$1"
  show_progress "SOAP Metadata API call"
  local response
  response=$(curl -s --max-time $CURL_TIMEOUT "${INSTANCE_URL}/services/Soap/m/${API_VERSION}" \
    -H "Content-Type: text/xml; charset=UTF-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>${BODY}</met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
  clear_progress
  printf '%s' "$response"
}

# Extract a boolean field value from SOAP XML response.
# Delegates to the shared shared/soap.sh parser for robust extraction (handles
# truncated XML, HTML error pages, multi-record responses) but preserves this
# function's original contract — "true", "false", or "" — so the ~15 call sites
# that only test `== "true"` keep their exact behavior. Auth/type/network
# classifications collapse to "" here (same as the old grep failure); callers
# that need to distinguish them use soap_classify directly (see the gate).
soap_extract_bool() {
  local XML="$1" FIELD="$2"
  local result
  result=$(parse_soap_response "$XML" "$FIELD" "200")
  case "$result" in
    true)  echo "true" ;;
    false) echo "false" ;;
    *)     echo "" ;;
  esac
}

# Cross-platform sed -i
sed_inplace() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

# Ensure sfdx-project.json exists for CLI operations
ensure_sfdx_project() {
  if [[ ! -f "sfdx-project.json" ]]; then
    cat > sfdx-project.json << 'SFDX'
{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "67.0"}
SFDX
  fi
}

# Print the "org can't enable Pipeline Management" blocker body (license list,
# edition guidance, Setup URL). Shared by the Step 0 gate (Phase 0.5) and the
# Phase 2.5 backstop so the message is authored once. Callers own the log_fail
# banner and the exit; this only prints the explanatory body.
# Args: $1 = Einstein Agent license count, $2 = Agentforce-for-Sales license count
#       (either may be a number, "unknown", or empty)
print_license_blocker() {
  local ea_count="${1:-unknown}" sales_count="${2:-unknown}"
  echo ""
  echo "  BLOCKER: This org cannot enable Pipeline Management programmatically."
  echo ""
  echo "  Reason: The SalesDealAgentSettings metadata type is not provisioned."
  echo "  This typically means the org is missing required licenses."
  echo ""
  echo "  Current org licenses:"
  echo "    • Einstein Agent licenses: $ea_count"
  echo "    • Agentforce for Sales licenses: $sales_count"
  echo ""
  echo "  Pipeline Management requires:"
  echo "    ✓ Agentforce for Sales add-on license, OR"
  echo "    ✓ Sales Cloud with Einstein capabilities, OR"
  echo "    ✓ Agentforce 1 Sales Edition"
  echo ""
  echo "  Actions:"
  echo "    1. Contact your Salesforce account team to provision Agentforce for Sales licenses"
  echo "    2. Verify org edition supports Pipeline Management (Enterprise Edition or higher)"
  echo "    3. Try manual enablement via Setup UI (if available):"
  echo "       ${INSTANCE_URL}/lightning/setup/PipelineManagement/home"
  echo "       (Note: Assumes Lightning Experience. For Classic, use Setup menu.)"
  echo ""
}

# ============================================================
# Phase 0.5: License & Capability Gate (Step 0)
# ============================================================
# Block an ineligible org UP FRONT — before any interactive question (Phase 1.7
# field selection) or mutation. The authoritative signal is the same one the
# Phase 2.5 backstop uses: probe the SalesDealAgentSettings metadata type over
# SOAP and hard-block ONLY on INVALID_TYPE (soap_classify => TYPE_UNAVAILABLE).
# License/edition COUNTS are informational context, never a block, because
# UserLicense can read 0 while PM still works via base Einstein Agent
# entitlements. An already-provisioned org has the type (probe => true/false),
# so it passes and idempotent re-runs stay green. Runs on BOTH the single-shot
# and --from-phase flow paths — it's read-only and fast.
section "Phase 0.5: License & Capability Gate"

STEP0_CAP=$(soap_classify "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")

# Informational context (non-blocking): edition + license counts.
STEP0_EDITION=$(sf data query --query "SELECT OrganizationType FROM Organization" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].OrganizationType // "unknown"' 2>/dev/null || echo "unknown")
STEP0_EA_COUNT=$(get_license_count "Einstein Agent")
[[ "$STEP0_EA_COUNT" == "ERROR" ]] && STEP0_EA_COUNT="unknown"
STEP0_SALES_COUNT=$(safe_jq_int "$(sf data query --query "SELECT COUNT(Id) FROM UserLicense WHERE (Name LIKE '%Agentforce for Sales%' OR Name LIKE '%Sales Cloud Einstein%' OR Name LIKE '%Agentforce 1%') AND TotalLicenses > 0" --target-org "$ORG_ALIAS" --json 2>/dev/null)" '.result.records[0].expr0 // 0')

echo "  Org edition: $STEP0_EDITION"
echo "  Einstein Agent licenses: $STEP0_EA_COUNT"
echo "  Agentforce for Sales / Sales Cloud Einstein / Agentforce 1 licenses: $STEP0_SALES_COUNT"
echo ""

case "$STEP0_CAP" in
  true|false)
    log_pass "GATE: Pipeline Management capability confirmed (SalesDealAgentSettings available) ✓"
    ;;
  TYPE_UNAVAILABLE:*)
    log_fail "GATE: This org is not licensed for Pipeline Management"
    print_license_blocker "$STEP0_EA_COUNT" "$STEP0_SALES_COUNT"
    echo "  Stopping now — before any configuration questions — so nothing is changed on an org that cannot run Pipeline Management."
    echo ""
    exit 1
    ;;
  AUTH_ERROR:*)
    log_warn "GATE: Couldn't confirm capability over SOAP yet (SOAP API access issue)."
    echo "  This is a separate, fixable prerequisite — it's re-checked and explained"
    echo "  at the SOAP prerequisites step (Phase 1.5). Proceeding."
    echo ""
    ;;
  NETWORK_ERROR|*)
    log_warn "GATE: Capability probe inconclusive (transient network/service error). Proceeding; the Phase 2.5 backstop will re-check."
    echo ""
    ;;
esac

# Non-blocking permission reminder — scripts cannot check these; the executing
# user must hold them for setup to complete (see SKILL.md "You must verify").
echo "  Reminder — the executing user needs these permissions (not script-checkable):"
echo "    • View Setup AND (Modify All Data OR Customize Application)"
echo "    • Manage AI Agents AND (Manage Agentforce Employee Agents OR Customize Application)"
echo "    • Assign Permission Sets"
echo ""

# --- License preflight stops here (--check-license) ---
# We've run auth + the Phase 0.5 gate. If the org were unlicensed the gate would
# already have printed the blocker and exit 1'd; reaching here means it's capable
# (or the probe was inconclusive — a non-blocking AUTH/NETWORK warning). Exit 0 so
# the driving agent can proceed to ask its clarifying questions. No mutation ran.
if [[ "$CHECK_LICENSE_ONLY" == "true" ]]; then
  log_pass "Preflight passed — org is capable of Pipeline Management. No changes made."
  echo "  Proceed to configuration (field selection, prompt tuning, then setup)."
  echo ""
  exit 0
fi

# ============================================================
# Phase 1.7: Field Selection (up front, before any provisioning)
# ============================================================
# 3-phase setup, part 1 of the "field" story: decide WHICH Opportunity fields the
# suggestion flow will manage BEFORE we build/deploy the flow, so the flow is built
# with only those fields (no deploy-then-strip). Done here — right after auth,
# before the heavy provisioning phases — so an empty/oversized selection fails fast
# rather than after minutes of enablement work.
#
# Rules:
#   - At least 1 field REQUIRED; setup ABORTS on an empty selection (no default).
#   - Hard cap MAX_SUGGESTION_FIELDS (OOTB NextStep/StageName count toward it).
#   - StageName is a picklist: NOT prompt-customizable, and it needs stage
#     descriptions (Phase 6) — flagged via STAGENAME_SELECTED.
#   - Per non-StageName field we collect an optional goal/instruction for the
#     prompt template (NextStep -> OOTB override; custom fields -> new template).
section "Phase 1.7: Field Selection"

if [[ -z "$SELECTED_FIELDS" ]]; then
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    log_fail "No fields selected. Pipeline Management needs at least one field to manage."
    echo "  Pass --fields with a comma-separated list of Opportunity field API names."
    echo "  OOTB fields: NextStep (Next Step), StageName (Opportunity Stage)."
    echo "  Example: $0 $ORG_ALIAS --fields \"NextStep\" --non-interactive"
    exit 1
  fi
  echo "Which Opportunity fields should the agent generate suggestions for?"
  echo "  • NextStep   — Next Step (OOTB; works out of the box)"
  echo "  • StageName  — Opportunity Stage (OOTB; requires stage descriptions)"
  echo "  • <API name> — any eligible custom text field (Text or Text Area <=255)"
  echo ""
  echo "  Enter a comma-separated list (at least 1, at most $MAX_SUGGESTION_FIELDS). Setup aborts if empty."
  read -rp "  Fields: " SELECTED_FIELDS || SELECTED_FIELDS=""
fi

# Normalize: trim whitespace around each entry, drop empties, de-dup (order-preserving).
declare -a FIELD_ARRAY=()
IFS=',' read -ra _raw_fields <<< "$SELECTED_FIELDS"
for _f in "${_raw_fields[@]}"; do
  _f="$(echo "$_f" | xargs)"   # trim
  [[ -z "$_f" ]] && continue
  _dup=false
  for _seen in "${FIELD_ARRAY[@]:-}"; do [[ "$_seen" == "$_f" ]] && { _dup=true; break; }; done
  [[ "$_dup" == "true" ]] || FIELD_ARRAY+=("$_f")
done

if [[ ${#FIELD_ARRAY[@]} -eq 0 ]]; then
  log_fail "No fields selected. Setup aborted — Pipeline Management requires at least one field."
  echo "  Re-run and select at least one field (e.g., NextStep)."
  exit 1
fi
if [[ ${#FIELD_ARRAY[@]} -gt $MAX_SUGGESTION_FIELDS ]]; then
  log_fail "Too many fields selected (${#FIELD_ARRAY[@]}). Maximum is $MAX_SUGGESTION_FIELDS (OOTB fields count toward the cap)."
  exit 1
fi

# Rebuild the canonical comma list from the normalized array so downstream
# consumers (flow builder, summary) see the de-duped, trimmed set.
SELECTED_FIELDS="$(IFS=,; echo "${FIELD_ARRAY[*]}")"

STAGENAME_SELECTED=false
for _f in "${FIELD_ARRAY[@]}"; do [[ "$_f" == "StageName" ]] && STAGENAME_SELECTED=true; done

log_pass "Fields selected (${#FIELD_ARRAY[@]}): $SELECTED_FIELDS"
[[ "$STAGENAME_SELECTED" == "true" ]] && log_info "StageName selected — stage descriptions will be needed (Phase 6)."

# Collect prompt customization for each non-StageName field. StageName is a
# picklist and is never customizable. Interactive only — in non-interactive mode
# the goal/instruction come from --field-goal / --field-instruction (or defaults
# inside add-field-suggestion.sh). NextStep with no customization stays on its
# curated OOTB managed prompt.
if [[ "$NON_INTERACTIVE" != "true" ]]; then
  for _f in "${FIELD_ARRAY[@]}"; do
    [[ "$_f" == "StageName" ]] && continue
    if [[ "$_f" == "NextStep" ]]; then
      confirm "Customize the AI prompt for NextStep? (N = keep the OOTB prompt)" || continue
    else
      echo ""
      echo "Configure the AI prompt for custom field '$_f':"
    fi
    read -rp "    Goal (completes 'You must think about ...'): " _goal || _goal=""
    read -rp "    Instruction (one line of extraction guidance): " _instr || _instr=""
    [[ -n "$_goal" ]]  && FIELD_PROMPTS["${_f}_goal"]="$_goal"
    [[ -n "$_instr" ]] && FIELD_PROMPTS["${_f}_instruction"]="$_instr"
  done
fi
echo ""

# ============================================================
# Pre-Block-A: Snapshot org state for accurate Configuration Summary
# (W-23277501 — status column must reflect before-vs-after, not hardcoded
#  greenfield literals, so idempotent reruns report UNCHANGED)
# ============================================================
# This is READ-ONLY org state and MUST run on BOTH the single-shot and the
# --from-phase flow paths, so it lives ABOVE the Block A `if`. It was previously
# inside Block A, which left BEFORE_* unbound on a --from-phase flow run and
# crashed the Phase 8 before/after table under `set -u`. All helpers it calls
# (soap_read, soap_extract_bool, schedule_flow_active, sanitize_display) are
# top-level, so this is safe here.
# Cache one SOAP read so both settings are extracted from the same document
SOAP_SETTINGS_BEFORE=$(soap_read "SalesDealAgentSettings" "SalesDealAgent" 2>/dev/null || echo "")
BEFORE_PM=$(soap_extract_bool "$SOAP_SETTINGS_BEFORE" "enableDealAgent" 2>/dev/null || echo "false")
BEFORE_AUTO=$(soap_extract_bool "$SOAP_SETTINGS_BEFORE" "enableDealAgentAutoApproveAllTasks" 2>/dev/null || echo "false")
BEFORE_AGENT_USER=$(sf data query --query "SELECT Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // "Not Created"' 2>/dev/null || echo "Not Created")
BEFORE_AGENT_USER=$(sanitize_display "$BEFORE_AGENT_USER" 60)
BEFORE_PSG_COUNT=$(sf data query --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
BEFORE_PSG_COUNT=$((${BEFORE_PSG_COUNT:-0} + 0))
# Normalize jq boolean output — treat literal null / missing / non-true as "none"
BEFORE_FLOW_ACTIVE=$(schedule_flow_active "$ORG_ALIAS")
# OpptStageDescription does not exist until Pipeline Management is enabled, so on
# a greenfield org this query fails with INVALID_TYPE. Under `set -o pipefail` the
# failed pipeline leaves jq's "0" on stdout AND (with a trailing `|| echo "0"`)
# would append a second "0", yielding a two-line value that crashes the arithmetic
# below with "0\n0". Swallow the failure with `|| true` and let jq's `// 0` supply
# the default — this preserves the BEFORE snapshot (W-23277501) on greenfield orgs.
BEFORE_STAGE_DESC_COUNT=$(sf data query --query "SELECT Id FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null || true)
BEFORE_STAGE_DESC_COUNT=$((${BEFORE_STAGE_DESC_COUNT:-0} + 0))

# ============================================================
# BLOCK A — Provisioning & Prompts (Phase 1.5 → 4e)
# ============================================================
# Everything from SOAP prereqs through prompt-template deploy + the verification
# gate. On a --from-phase flow run this entire block is SKIPPED: the org was
# already enabled/provisioned and the templates deployed+tuned in the prior
# --through-phase prompts call, so we jump straight to building the flow (Phase 5)
# from the agent-approved --fields set. The context phases above (0/1/1.7) always
# run, so SELECTED_FIELDS / FIELD_ARRAY / STAGENAME_SELECTED are populated either way.
if [[ "$RUN_FROM_PHASE" == "flow" ]]; then
  section "Provisioning & Prompts (Phase 1.5–4e)"
  log_info "Skipped (--from-phase flow): org already enabled and prompt templates deployed in the prior --through-phase prompts run."
  log_info "Building the flow from the approved field set: $SELECTED_FIELDS"
else

# ============================================================
# Phase 1.5: SOAP API Prerequisites Verification
# ============================================================
section "Phase 1.5: SOAP API Prerequisites"

echo "This script requires SOAP API access to enable Pipeline Management settings."
echo "Testing SOAP API connectivity..."
echo ""

# Test SOAP API with a simple read operation
show_progress "Testing SOAP API connectivity"
SOAP_TEST=$(curl -s --max-time $CURL_TIMEOUT "${INSTANCE_URL}/services/Soap/m/${API_VERSION}" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>EinsteinGptSettings</met:type><met:fullNames>EinsteinGpt</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>&1)

clear_progress

# Check for INVALID_LOGIN error (most common SOAP access issue)
if echo "$SOAP_TEST" | grep -q "INVALID_LOGIN"; then
  log_fail "SOAP API login failed"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  BLOCKER: SOAP API Access Not Enabled"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "This script uses the SOAP Metadata API to enable Pipeline Management"
  echo "settings. Your org or user account does not have SOAP API access enabled."
  echo ""
  echo "Error received: INVALID_LOGIN"
  echo ""
  echo "SOAP API requires two prerequisites:"
  echo ""
  echo "1️⃣  ORG-LEVEL SETTING: Enable SOAP API Login"
  echo ""
  echo "   a. Navigate to: ${INSTANCE_URL}/lightning/setup/UserInterfaceUI/home"
  echo "      OR: Setup → Quick Find: 'User Interface'"
  echo ""
  echo "   b. Check the box: ☑ Enable SOAP API login()"
  echo ""
  echo "   c. Click Save"
  echo ""
  echo "2️⃣  USER-LEVEL PERMISSION: Grant 'Use Any API Auth' Permission"
  echo ""
  echo "   Option A: Via Permission Set (Recommended)"
  echo "   ─────────────────────────────────────────"
  echo "   a. Navigate to: ${INSTANCE_URL}/lightning/setup/PermSets/home"
  echo "      OR: Setup → Quick Find: 'Permission Sets'"
  echo ""
  echo "   b. Create new Permission Set (e.g., 'API Access')"
  echo ""
  echo "   c. Click 'System Permissions' → Edit"
  echo ""
  echo "   d. Enable: ☑ Use Any API Auth"
  echo ""
  echo "   e. Save → Manage Assignments → Assign to your user"
  echo ""
  echo "   Option B: Via Profile (Alternative)"
  echo "   ────────────────────────────────────"
  echo "   a. Navigate to your user profile settings"
  echo ""
  echo "   b. Edit → System Permissions"
  echo ""
  echo "   c. Enable: ☑ Use Any API Auth"
  echo ""
  echo "   d. Save"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "After enabling both prerequisites, re-run this script:"
  echo "  bash setup-all.sh $ORG_ALIAS"
  echo ""
  exit 1
fi

# Check for other SOAP errors
if echo "$SOAP_TEST" | grep -q "<faultcode>"; then
  FAULT_CODE=$(echo "$SOAP_TEST" | grep -o "<faultcode>[^<]*" | sed 's/<faultcode>//')
  FAULT_STRING=$(redact_token "$(echo "$SOAP_TEST" | grep -o "<faultstring>[^<]*" | sed 's/<faultstring>//')")

  log_warn "SOAP API test returned an error"
  echo ""
  echo "  Fault Code: $FAULT_CODE"
  echo "  Fault Message: $FAULT_STRING"
  echo ""

  if [[ "$FAULT_CODE" == *"INVALID_TYPE"* ]]; then
    log_info "This may be expected for test/trial orgs. Proceeding..."
    track_issue "⚠️ WARN" "SOAP API returned INVALID_TYPE" "Expected for test/trial orgs - Continued"
    echo ""
  else
    echo "  This may indicate a SOAP API configuration issue."
    echo "  If setup fails, verify SOAP API prerequisites above."
    track_issue "⚠️ WARN" "SOAP API error: $FAULT_CODE" "User confirmed continue"
    echo ""
    # Non-interactive: skip (don't block on user input in agent context)
    if [[ -t 0 ]]; then
      read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
    fi
    echo ""
  fi
else
  log_pass "SOAP API access verified ✓"
fi

# --- Generic enable-and-verify harness ---
# Tries SOAP → CLI deploy → verifies via SOAP readMetadata
# Returns:
#   0 = success
#   1 = failure (all approaches exhausted)
#   2 = metadata type not available (INVALID_TYPE - org lacks license/edition)
#
# Usage: enable_setting <MetadataType> <fullName> <field> <displayName>
enable_setting() {
  local META_TYPE="$1"
  local FULL_NAME="$2"
  local FIELD="$3"
  local DISPLAY_NAME="$4"

  # --- CHECK: already enabled? ---
  local CURRENT
  local READ_RESULT
  READ_RESULT=$(soap_read "$META_TYPE" "$FULL_NAME")

  # Check for INVALID_TYPE in read response (metadata type not available)
  if echo "$READ_RESULT" | grep -qi "INVALID_TYPE"; then
    log_warn "$DISPLAY_NAME: metadata type not available in this org (licensing/edition limitation)"
    return 2
  fi

  CURRENT=$(soap_extract_bool "$READ_RESULT" "$FIELD")
  if [[ "$CURRENT" == "true" ]]; then
    log_pass "$DISPLAY_NAME: enabled"
    return 0
  fi

  # --- APPROACH 1: SOAP updateMetadata ---
  log_try "$DISPLAY_NAME: enabling via SOAP Metadata API..."
  local SOAP_RESULT
  SOAP_RESULT=$(soap_update "<met:metadata xsi:type='met:${META_TYPE}' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'><met:fullName>${FULL_NAME}</met:fullName><met:${FIELD}>true</met:${FIELD}></met:metadata>")

  # Check for INVALID_TYPE in update response
  if echo "$SOAP_RESULT" | grep -qi "INVALID_TYPE"; then
    log_warn "$DISPLAY_NAME: metadata type not available in this org (licensing/edition limitation)"
    return 2
  fi

  if echo "$SOAP_RESULT" | grep -q "<success>true</success>"; then
    sleep $SLEEP_SHORT
    # VERIFY
    CURRENT=$(soap_extract_bool "$(soap_read "$META_TYPE" "$FULL_NAME")" "$FIELD")
    if [[ "$CURRENT" == "true" ]]; then
      log_pass "$DISPLAY_NAME: enabled (SOAP)"
      return 0
    fi
    log_warn "$DISPLAY_NAME: SOAP reported success but verification failed. Retrying..."
    sleep $SLEEP_LONG
    CURRENT=$(soap_extract_bool "$(soap_read "$META_TYPE" "$FULL_NAME")" "$FIELD")
    if [[ "$CURRENT" == "true" ]]; then
      log_pass "$DISPLAY_NAME: enabled (SOAP, delayed verification)"
      return 0
    fi
  fi

  local SOAP_ERR
  SOAP_ERR=$(echo "$SOAP_RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || echo "")
  [[ -n "$SOAP_ERR" ]] && echo "    SOAP error: $(redact_token "$SOAP_ERR")"

  # --- APPROACH 2: CLI retrieve → modify → deploy ---
  # Map MetadataType to CLI settings name (strip "Settings" suffix for CLI)
  local CLI_NAME="${META_TYPE%Settings}"
  # Special cases where CLI name differs
  case "$META_TYPE" in
    EinsteinGptSettings) CLI_NAME="EinsteinGpt" ;;
    EinsteinCopilotSettings) CLI_NAME="EinsteinCopilot" ;;
    AgentPlatformSettings) CLI_NAME="AgentPlatform" ;;
    EnhancedNotesSettings) CLI_NAME="EnhancedNotes" ;;
    OpportunitySettings) CLI_NAME="Opportunity" ;;
    SalesDealAgentSettings) CLI_NAME="SalesDealAgent" ;;
  esac

  log_try "$DISPLAY_NAME: trying CLI retrieve/modify/deploy..."
  ensure_sfdx_project
  mkdir -p force-app/main/default/settings

  # Attempt retrieve
  sf project retrieve start --metadata "Settings:${CLI_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null || true

  local SETTINGS_FILE="force-app/main/default/settings/${CLI_NAME}.settings-meta.xml"
  if [[ -f "$SETTINGS_FILE" ]]; then
    # Modify: update existing field or insert new field
    if grep -q "<${FIELD}>" "$SETTINGS_FILE"; then
      sed_inplace "s|<${FIELD}>[^<]*</${FIELD}>|<${FIELD}>true</${FIELD}>|g" "$SETTINGS_FILE"
    else
      # Insert before closing tag
      sed_inplace "/<\/.*Settings>/i\\
    <${FIELD}>true</${FIELD}>" "$SETTINGS_FILE"
    fi

    # Deploy
    local DEPLOY_RESULT
    DEPLOY_RESULT=$(sf project deploy start --source-dir force-app/main/default/settings --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')

    if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
      sleep $SLEEP_MEDIUM
      # VERIFY
      CURRENT=$(soap_extract_bool "$(soap_read "$META_TYPE" "$FULL_NAME")" "$FIELD")
      if [[ "$CURRENT" == "true" ]]; then
        log_pass "$DISPLAY_NAME: enabled (CLI deploy)"
        return 0
      fi
      log_warn "$DISPLAY_NAME: CLI deploy succeeded but SOAP verification failed"
    else
      local DEPLOY_ERR
      DEPLOY_ERR=$(safe_jq "$DEPLOY_RESULT" '.result.details.componentFailures[0].problem // .message // "unknown"' "unknown")
      echo "    CLI deploy error: $DEPLOY_ERR"
    fi
  else
    echo "    CLI retrieve returned no settings file for $CLI_NAME"
  fi

  # --- APPROACH 3: REST Composite API (for settings that support it) ---
  log_try "$DISPLAY_NAME: trying REST API PATCH..."
  show_progress "REST API PATCH for $DISPLAY_NAME"
  local REST_RESULT
  REST_RESULT=$(curl -s --max-time $CURL_TIMEOUT -X PATCH "${INSTANCE_URL}/services/data/v${API_VERSION}/tooling/sobjects/${META_TYPE}/${FULL_NAME}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"${FIELD}\": true}" 2>/dev/null || echo "")
  clear_progress

  # REST may return empty on success (204) or an error body
  if [[ -z "$REST_RESULT" ]] || echo "$REST_RESULT" | grep -qi "\"success\":true\|\"id\""; then
    sleep $SLEEP_MEDIUM
    CURRENT=$(soap_extract_bool "$(soap_read "$META_TYPE" "$FULL_NAME")" "$FIELD")
    if [[ "$CURRENT" == "true" ]]; then
      log_pass "$DISPLAY_NAME: enabled (REST API)"
      return 0
    fi
  fi

  # --- ALL APPROACHES EXHAUSTED ---
  # Final verification attempt after waiting
  sleep $SLEEP_LONG
  CURRENT=$(soap_extract_bool "$(soap_read "$META_TYPE" "$FULL_NAME")" "$FIELD")
  if [[ "$CURRENT" == "true" ]]; then
    log_pass "$DISPLAY_NAME: enabled (delayed propagation)"
    return 0
  fi

  log_fail "$DISPLAY_NAME: COULD NOT ENABLE (all 3 approaches failed)"
  return 1
}

# ============================================================
# Phase 2: Prerequisites (with verification gate)
# ============================================================
section "Phase 2: Prerequisites"

PREREQ_BLOCKERS=0

# --- 2a: Einstein Generative AI (CRITICAL — everything depends on this) ---
GENAI_RESULT=0
enable_setting "EinsteinGptSettings" "EinsteinGpt" "enableEinsteinGptPlatform" "Einstein Generative AI" || GENAI_RESULT=$?

if [[ "$GENAI_RESULT" -eq 2 ]]; then
  # Metadata type not available (INVALID_TYPE) - org lacks required license/edition
  echo ""
  echo "  BLOCKER: Einstein Generative AI metadata type not available in this org."
  echo "  This is the foundation for ALL Agentforce features."
  echo ""
  echo "  Root cause: EinsteinGptSettings metadata type returned INVALID_TYPE"
  echo "  This means the org is missing:"
  echo "    - Enterprise Edition (or higher) with Einstein features"
  echo "    - Einstein Generative AI licenses"
  echo "    - Platform-level Einstein feature enablement"
  echo ""
  echo "  Resolution:"
  echo "    1. Verify org edition: Setup → Company Information"
  echo "       Required: Enterprise Edition or higher"
  echo "    2. Check licenses: Setup → Company Information → User Licenses"
  echo "       Look for: 'Einstein', 'Sales Cloud Einstein', 'Service Cloud Einstein'"
  echo "    3. If licenses are missing:"
  echo "       → Contact your Salesforce account team to provision Einstein licenses"
  echo "       → Trial orgs: Request Einstein trial extension"
  echo "    4. Re-run this script: ./setup-all.sh $ORG_ALIAS"
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
elif [[ "$GENAI_RESULT" -ne 0 ]]; then
  # Other failure (return code 1) - could be ToS, permissions, or other config issue
  echo ""
  echo "  BLOCKER: Einstein Generative AI cannot be enabled."
  echo "  This is the foundation for ALL Agentforce features."
  echo ""
  echo "  Common causes:"
  echo "    - Org edition doesn't include Einstein GenAI features"
  echo "    - Einstein Terms of Service not accepted (Setup → Einstein Setup)"
  echo "    - Org-level feature toggle disabled by Salesforce"
  echo "    - Missing required licenses for Einstein features"
  echo ""
  echo "  Manual resolution:"
  echo "    1. Setup → Einstein Setup → Review and accept Terms of Service"
  echo "    2. Setup → Einstein Generative AI → Enable"
  echo "    3. Check Setup → Company Information → User Licenses for Einstein/Agentforce licenses"
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
fi

# --- 2b: Agentforce Agent (CRITICAL — depends on GenAI) ---
COPILOT_RESULT=0
enable_setting "EinsteinCopilotSettings" "EinsteinCopilot" "enableEinsteinGptCopilot" "Agentforce Agent" || COPILOT_RESULT=$?

if [[ "$COPILOT_RESULT" -eq 2 ]]; then
  # Metadata type not available (INVALID_TYPE) - org lacks required license/edition
  echo ""
  echo "  BLOCKER: Agentforce Agent metadata type not available in this org."
  echo "  This indicates the org does NOT have the required Salesforce edition or licenses."
  echo ""
  echo "  Root cause: EinsteinCopilotSettings metadata type returned INVALID_TYPE"
  echo "  This means the org is missing:"
  echo "    - Enterprise Edition (or higher) with Einstein/Agentforce features"
  echo "    - Einstein Agent licenses"
  echo "    - Agentforce for Sales add-on licenses"
  echo ""
  echo "  Resolution:"
  echo "    1. Verify org edition: Setup → Company Information"
  echo "       Required: Enterprise Edition or higher"
  echo "    2. Check licenses: Setup → Company Information → User Licenses"
  echo "       Look for: 'Einstein Agent', 'Agentforce for Sales', 'Sales Cloud Einstein'"
  echo "    3. If licenses are missing:"
  echo "       → Contact your Salesforce account team to provision licenses"
  echo "       → Trial orgs: Request Einstein/Agentforce trial extension"
  echo "    4. Re-run this script: ./setup-all.sh $ORG_ALIAS"
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
elif [[ "$COPILOT_RESULT" -ne 0 ]]; then
  # Other failure (return code 1) - could be ToS, permissions, or other config issue
  echo ""
  echo "  BLOCKER: Agentforce Agent cannot be enabled."
  echo "  Requires Einstein Generative AI (step above) to be enabled first."
  echo ""
  echo "  Common causes:"
  echo "    - Missing Einstein Agent licenses"
  echo "    - Org edition doesn't include Einstein/Agentforce features"
  echo "    - Einstein Terms of Service not accepted"
  echo ""
  # Check if Einstein Agent licenses exist
  EA_LICENSE=$(get_license_count "Einstein Agent")
  if [[ "$EA_LICENSE" == "ERROR" ]]; then
    echo "  License Check: ⚠️  Could not verify license status (API error)"
    echo "    → Check org connectivity and try again"
    echo ""
  elif [[ "$EA_LICENSE" -eq 0 ]]; then
    echo "  License Check: ❌ No Einstein Agent licenses found"
    echo "    → Contact your Salesforce account team to provision Einstein Agent licenses"
    echo "    → View licenses: Setup → Company Information → User Licenses"
    echo ""
  else
    echo "  License Check: ✓ Einstein Agent licenses available ($EA_LICENSE)"
    echo ""
    echo "  Most likely cause: Einstein Terms of Service NOT accepted"
    echo ""
    echo "  Required action:"
    echo "    1. Navigate to: ${INSTANCE_URL}/lightning/setup/EinsteinGPTSetup/home"
    echo "       (Note: Assumes Lightning Experience. For Classic, use Setup menu.)"
    echo "    2. Review and accept the Einstein Terms of Service"
    echo "    3. Then enable Agentforce Agent at: ${INSTANCE_URL}/lightning/setup/EinsteinCopilot/home"
    echo "    4. Re-run this script: ./setup-all.sh $ORG_ALIAS"
    echo ""
  fi
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
fi

# --- 2b2: Agentforce Studio / Agent Platform (CRITICAL — gates Deal Agent) ---
# AgentPlatformSettings.enableAgentPlatform (OrgPreference AgentPlatformEnabled)
# must be ON before SalesDealAgentSettings can be enabled. Core enforces this:
# DealAgentEnabledOrgPreference.validateAgentforcePlatformAndLog() throws if the
# Agentforce Platform preference is not enabled, so a missing step here surfaces
# later as an opaque Deal Agent activation failure. Ordering: GenAI → Copilot →
# AgentPlatform → SalesDealAgent.
AGENT_PLATFORM_RESULT=0
enable_setting "AgentPlatformSettings" "AgentPlatform" "enableAgentPlatform" "Agentforce Studio (Agent Platform)" || AGENT_PLATFORM_RESULT=$?

if [[ "$AGENT_PLATFORM_RESULT" -eq 2 ]]; then
  # Metadata type not available (INVALID_TYPE) - org lacks required license/edition
  echo ""
  echo "  BLOCKER: Agentforce Studio (Agent Platform) metadata type not available in this org."
  echo "  AgentPlatformSettings returned INVALID_TYPE — the org is missing the"
  echo "  Enterprise Edition (or higher) or Agentforce licenses required for Agent Platform."
  echo ""
  echo "  Resolution:"
  echo "    1. Verify org edition: Setup → Company Information (Enterprise Edition or higher)"
  echo "    2. Check licenses: Setup → Company Information → User Licenses"
  echo "       Look for: 'Agentforce', 'Einstein Agent', 'Agentforce for Sales'"
  echo "    3. Re-run this script: ./setup-all.sh $ORG_ALIAS"
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
elif [[ "$AGENT_PLATFORM_RESULT" -ne 0 ]]; then
  echo ""
  echo "  BLOCKER: Agentforce Studio (Agent Platform) cannot be enabled."
  echo "  This preference (AgentPlatformEnabled) gates the Sales Deal Agent —"
  echo "  Deal Agent activation fails downstream if it is not enabled first."
  echo ""
  echo "  Common causes:"
  echo "    - Einstein Generative AI / Agentforce Agent not enabled (steps above)"
  echo "    - Missing Agentforce licenses"
  echo "    - Einstein Terms of Service not accepted"
  echo ""
  echo "  Manual resolution:"
  echo "    1. Enable Einstein GenAI and Agentforce Agent (steps above)"
  echo "    2. Navigate to: ${INSTANCE_URL}/lightning/setup/EinsteinAgentBuilder/home"
  echo "       (Agentforce Studio) and confirm the platform is enabled"
  echo "    3. Re-run this script: ./setup-all.sh $ORG_ALIAS"
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
fi

# --- 2c: Enhanced Notes (CRITICAL — PM data source) ---
if ! enable_setting "EnhancedNotesSettings" "EnhancedNotes" "enableEnhancedNotes" "Enhanced Notes"; then
  echo ""
  echo "  BLOCKER: Enhanced Notes cannot be enabled."
  echo "  Pipeline Management uses ContentNote as a primary data source."
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
fi

# --- 2d: Opportunity Team (CRITICAL — flow uses OpportunityTeamMember) ---
if ! enable_setting "OpportunitySettings" "Opportunity" "enableOpportunityTeam" "Opportunity Team"; then
  echo ""
  echo "  BLOCKER: Opportunity Team cannot be enabled."
  echo "  Pipeline Management flow requires OpportunityTeamMember object access."
  echo ""
  PREREQ_BLOCKERS=$((PREREQ_BLOCKERS + 1))
fi

# --- 2e: Pipeline Inspection (required for UI review of suggestions) ---
enable_setting "OpportunitySettings" "Opportunity" "enablePipelineInspection" "Pipeline Inspection" || \
  log_warn "Pipeline Inspection not enabled — suggestions generate but users have no UI to review/accept them"

# --- 2f: Enhanced Email (optional) ---
enable_setting "EmailAdministrationSettings" "EmailAdministration" "enableEnhancedEmailEnabled" "Enhanced Email" || \
  log_warn "Enhanced Email not enabled (email body indexing unavailable — agent uses notes instead)"

# --- VERIFICATION GATE: All critical prerequisites must pass ---
echo ""
echo "  --- Prerequisite Verification Gate ---"

GATE_PASS=true

# Classify each gate setting so a real "disabled" is distinguished from an
# auth/SOAP fault or a network/service error (W-23215519). gate_check logs the
# right diagnostic and fails the gate for any non-"true" outcome.
# Args: $1 = display label, $2 = classification string from soap_classify
gate_check() {
  local label="$1" status="$2"
  case "$status" in
    true)
      return 0
      ;;
    false)
      log_fail "GATE: $label NOT confirmed (setting is disabled)"
      ;;
    AUTH_ERROR:*)
      log_fail "GATE: $label cannot be verified — auth/SOAP fault (${status#AUTH_ERROR:})"
      echo "    Re-authenticate: sf org login web --alias $ORG_ALIAS"
      ;;
    TYPE_UNAVAILABLE:*)
      log_fail "GATE: $label cannot be verified — metadata type unavailable (${status#TYPE_UNAVAILABLE:})"
      ;;
    NETWORK_ERROR)
      log_fail "GATE: $label cannot be verified — network/service error (check connectivity)"
      ;;
    *)
      log_fail "GATE: $label NOT confirmed (unexpected status: $status)"
      ;;
  esac
  GATE_PASS=false
  return 1
}

GENAI_STATUS=$(soap_classify "$(soap_read "EinsteinGptSettings" "EinsteinGpt")" "enableEinsteinGptPlatform")
COPILOT_STATUS=$(soap_classify "$(soap_read "EinsteinCopilotSettings" "EinsteinCopilot")" "enableEinsteinGptCopilot")
AGENT_PLATFORM_STATUS=$(soap_classify "$(soap_read "AgentPlatformSettings" "AgentPlatform")" "enableAgentPlatform")
NOTES_STATUS=$(soap_classify "$(soap_read "EnhancedNotesSettings" "EnhancedNotes")" "enableEnhancedNotes")
OPP_TEAM_STATUS=$(soap_classify "$(soap_read "OpportunitySettings" "Opportunity")" "enableOpportunityTeam")

# Keep boolean mirrors for the existing failure-summary conditionals below.
VERIFY_GENAI=$([[ "$GENAI_STATUS" == "true" ]] && echo "true" || echo "false")
VERIFY_COPILOT=$([[ "$COPILOT_STATUS" == "true" ]] && echo "true" || echo "false")
VERIFY_AGENT_PLATFORM=$([[ "$AGENT_PLATFORM_STATUS" == "true" ]] && echo "true" || echo "false")
VERIFY_NOTES=$([[ "$NOTES_STATUS" == "true" ]] && echo "true" || echo "false")
VERIFY_OPP_TEAM=$([[ "$OPP_TEAM_STATUS" == "true" ]] && echo "true" || echo "false")

gate_check "Einstein Generative AI" "$GENAI_STATUS" || true
gate_check "Agentforce Agent" "$COPILOT_STATUS" || true
gate_check "Agentforce Studio (Agent Platform)" "$AGENT_PLATFORM_STATUS" || true
gate_check "Enhanced Notes" "$NOTES_STATUS" || true
gate_check "Opportunity Team" "$OPP_TEAM_STATUS" || true

if [[ "$GATE_PASS" != "true" ]]; then
  echo ""
  log_fail "PREREQUISITE GATE FAILED — cannot proceed to Pipeline Management enablement."
  echo ""
  echo "  The following critical settings must be enabled before PM can be activated:"
  [[ "$VERIFY_GENAI" != "true" ]] && echo "    ❌ EinsteinGptSettings.enableEinsteinGptPlatform"
  [[ "$VERIFY_COPILOT" != "true" ]] && echo "    ❌ EinsteinCopilotSettings.enableEinsteinGptCopilot"
  [[ "$VERIFY_AGENT_PLATFORM" != "true" ]] && echo "    ❌ AgentPlatformSettings.enableAgentPlatform"
  [[ "$VERIFY_NOTES" != "true" ]] && echo "    ❌ EnhancedNotesSettings.enableEnhancedNotes"
  [[ "$VERIFY_OPP_TEAM" != "true" ]] && echo "    ❌ OpportunitySettings.enableOpportunityTeam"
  echo ""
  echo "  Manual resolution:"
  echo "    1. Setup → Einstein → Einstein Generative AI → Enable"
  echo "    2. Setup → Einstein → Copilot → Enable"
  echo "    3. Setup → Agentforce Studio → Enable (Agent Platform)"
  echo "    4. Setup → Notes → Enable Enhanced Notes"
  echo "    5. Setup → Opportunity Settings → Enable Opportunity Team"
  echo "    6. Re-run: bash setup-all.sh $ORG_ALIAS"
  exit 1
fi

log_pass "GATE: All critical prerequisites verified ✓"

# ============================================================
# Phase 2.5: License and Metadata Type Validation
# ============================================================
echo ""
echo "  --- Pipeline Management Compatibility Gate ---"

# Expected license names: "Agentforce for Sales", "Sales Cloud Einstein", "Agentforce 1"
# If Salesforce introduces new variants, this query may need updating
SALES_LICENSE_OUTPUT=$(sf data query --query "SELECT COUNT(Id) FROM UserLicense WHERE (Name LIKE '%Agentforce for Sales%' OR Name LIKE '%Sales Cloud Einstein%' OR Name LIKE '%Agentforce 1%') AND TotalLicenses > 0" --target-org "$ORG_ALIAS" --json 2>/dev/null)
SALES_LICENSE_COUNT=$(safe_jq_int "$SALES_LICENSE_OUTPUT" '.result.records[0].expr0 // 0')

EINSTEIN_AGENT_COUNT=$(get_license_count "Einstein Agent")
# Handle API errors gracefully
if [[ "$EINSTEIN_AGENT_COUNT" == "ERROR" ]]; then
  EINSTEIN_AGENT_COUNT="unknown"
fi

# Check if SalesDealAgentSettings metadata type is available
METADATA_TYPE_CHECK=$(soap_read "SalesDealAgentSettings" "SalesDealAgent" 2>/dev/null || echo "")

# Backstop only — the Step 0 gate (Phase 0.5) is the primary check and normally
# stops an unlicensed org before any question. This catches a post-enablement
# regression (e.g. the type going away mid-run). Shares print_license_blocker().
if echo "$METADATA_TYPE_CHECK" | grep -q "INVALID_TYPE"; then
  log_fail "GATE: SalesDealAgentSettings metadata type NOT available"
  print_license_blocker "$EINSTEIN_AGENT_COUNT" "$SALES_LICENSE_COUNT"
  exit 1
fi

if [[ "$SALES_LICENSE_COUNT" -eq 0 ]]; then
  log_warn "GATE: No Agentforce for Sales licenses found (but metadata type exists)"
  echo ""
  echo "  Warning: The org has the metadata type but no explicit Sales licenses."
  echo "  Pipeline Management may work via base Einstein Agent licenses ($EINSTEIN_AGENT_COUNT)."
  echo "  Proceeding with enablement attempt..."
  echo ""
else
  log_pass "GATE: Agentforce for Sales licenses found ($SALES_LICENSE_COUNT) ✓"
fi

# ============================================================
# Phase 3: Enable Pipeline Management (with multi-approach + verification)
# ============================================================
section "Phase 3: Pipeline Management"

PM_ENABLED=false

# Check current state
PM_CURRENT=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")
if [[ "$PM_CURRENT" == "true" ]]; then
  log_pass "Pipeline Management: already enabled"
  PM_ENABLED=true
fi

if [[ "$PM_ENABLED" != "true" ]]; then
  # --- APPROACH 1: SOAP updateMetadata ---
  log_try "Enabling via SOAP Metadata API v${API_VERSION}..."
  RESULT=$(soap_update "<met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'><met:fullName>SalesDealAgent</met:fullName><met:enableDealAgent>true</met:enableDealAgent><met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks></met:metadata>")

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    sleep $SLEEP_MEDIUM
    PM_CHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")
    if [[ "$PM_CHECK" == "true" ]]; then
      log_pass "Pipeline Management: enabled (SOAP)"
      PM_ENABLED=true
    fi
  fi

  if [[ "$PM_ENABLED" != "true" ]]; then
    SOAP_ERR=$(echo "$RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || echo "")
    [[ -n "$SOAP_ERR" ]] && echo "    SOAP error: $(redact_token "$SOAP_ERR")"
  fi
fi

if [[ "$PM_ENABLED" != "true" ]]; then
  # --- APPROACH 2: CLI Metadata deploy (SalesDealAgent settings XML) ---
  log_try "Enabling via CLI Metadata deploy..."
  ensure_sfdx_project
  mkdir -p force-app/main/default/settings

  # Create settings XML directly (CLI retrieve fails for this type)
  cat > force-app/main/default/settings/SalesDealAgent.settings-meta.xml << 'XMLEOF'
<?xml version="1.0" encoding="UTF-8"?>
<SalesDealAgentSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableDealAgent>true</enableDealAgent>
    <enableDealAgentAutoApproveAllTasks>false</enableDealAgentAutoApproveAllTasks>
</SalesDealAgentSettings>
XMLEOF

  DEPLOY_RESULT=$(sf project deploy start --source-dir force-app/main/default/settings/SalesDealAgent.settings-meta.xml --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
  if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
    sleep $SLEEP_LONG
    PM_CHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")
    if [[ "$PM_CHECK" == "true" ]]; then
      log_pass "Pipeline Management: enabled (CLI deploy)"
      PM_ENABLED=true
    fi
  else
    DEPLOY_ERR=$(safe_jq "$DEPLOY_RESULT" '.result.details.componentFailures[0].problem // .message // "unknown"' "unknown")
    echo "    CLI deploy error: $DEPLOY_ERR"
  fi
fi

if [[ "$PM_ENABLED" != "true" ]]; then
  # --- APPROACH 3: Recognize genuine mid-provisioning WITHOUT asserting enablement ---
  # #9: PSG existence is NOT a setup signal — SalesManagementUserPsg /
  # SalesManagementAgentUserPsg ship with the Agentforce-for-Sales license and exist even
  # in a never-configured org, so "PSGs exist" says nothing about whether PM was set up.
  # The authoritative signal is SalesDealAgentSettings.enableDealAgent via SOAP readMetadata
  # (checked above). Here we re-read it authoritatively; only if it reads true do we mark
  # enabled. If it's still false, we check the REAL "setup has run" signals — an agent user
  # holding SalesManagementAgentUserPsg, a cloned scheduled flow, or a PM BotDefinition. If
  # any is present, a bundle-publish/template-provisioned org may be mid-flight, so we mark
  # "unconfirmed" and continue, letting the downstream verification gate confirm. Otherwise
  # we fall through to Approach 4.
  log_try "Re-reading enableDealAgent authoritatively (SOAP) and checking real setup signals..."
  PM_RECHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")

  if [[ "$PM_RECHECK" == "true" ]]; then
    log_pass "Pipeline Management: enabled (confirmed via SOAP enableDealAgent)"
    PM_ENABLED=true
  else
    AGENT_PSG_HELD=$(pm_agent_user_holds_psg "$ORG_ALIAS")
    PM_FLOW_EXISTS=$(pm_flow_clone_exists "$ORG_ALIAS")
    PM_BOT_EXISTS=$(pm_bot_count "$ORG_ALIAS")
    if [[ "$AGENT_PSG_HELD" -ge 1 || "$PM_FLOW_EXISTS" -ge 1 || "$PM_BOT_EXISTS" -ge 1 ]]; then
      log_warn "enableDealAgent not confirmed true, but real setup signals exist (agentPSG=$AGENT_PSG_HELD flow=$PM_FLOW_EXISTS bot=$PM_BOT_EXISTS) — provisioning likely in progress."
      echo "    Continuing with setup; enablement is UNCONFIRMED and will be re-verified in Phase 8."
      PM_ENABLED="unconfirmed"
    fi
  fi
fi

if [[ "$PM_ENABLED" != "true" && "$PM_ENABLED" != "unconfirmed" ]]; then
  # --- APPROACH 4: OrgPreference via Tooling API ---
  log_try "Enabling via OrgPreference Tooling API..."
  show_progress "Tooling API OrgPreference update"
  PREF_RESULT=$(curl -s --max-time $CURL_TIMEOUT -X PATCH "${INSTANCE_URL}/services/data/v${API_VERSION}/tooling/sobjects/OrganizationSettingsDetail/DealAgentEnabled" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"value": true}' 2>/dev/null || echo "")
  clear_progress

  sleep $SLEEP_LONG
  PM_CHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgent")
  if [[ "$PM_CHECK" == "true" ]]; then
    log_pass "Pipeline Management: enabled (Tooling API OrgPreference)"
    PM_ENABLED=true
  else
    # Do NOT treat PSG presence as a provisioning signal (the PM PSGs ship with the
    # license). Re-check the same real signals as Approach 3: an agent user holding
    # SalesManagementAgentUserPsg, a cloned scheduled flow, or a PM BotDefinition.
    AGENT_PSG_HELD=$(pm_agent_user_holds_psg "$ORG_ALIAS")
    PM_FLOW_EXISTS=$(pm_flow_clone_exists "$ORG_ALIAS")
    PM_BOT_EXISTS=$(pm_bot_count "$ORG_ALIAS")
    if [[ "$AGENT_PSG_HELD" -ge 1 || "$PM_FLOW_EXISTS" -ge 1 || "$PM_BOT_EXISTS" -ge 1 ]]; then
      log_warn "Tooling API approach uncertain, but real setup signals appeared (agentPSG=$AGENT_PSG_HELD flow=$PM_FLOW_EXISTS bot=$PM_BOT_EXISTS) — PM provisioning in progress"
      PM_ENABLED="unconfirmed"
    fi
  fi
fi

# --- PM VERIFICATION GATE ---
if [[ "$PM_ENABLED" != "true" && "$PM_ENABLED" != "unconfirmed" ]]; then
  echo ""
  log_fail "PIPELINE MANAGEMENT GATE FAILED — all 4 approaches exhausted."
  echo ""
  echo "  Attempted:"
  echo "    1. SOAP Metadata API v${API_VERSION} (updateMetadata SalesDealAgentSettings)"
  echo "    2. CLI Metadata deploy (settings XML)"
  echo "    3. Authoritative SOAP re-read + provisioning-signal detection (agent-user / flow / bot presence)"
  echo "    4. Tooling API OrgPreference (DealAgentEnabled)"
  echo ""
  echo "  This org may require manual enablement:"
  echo "    Setup → Sales → Pipeline Management → Enable toggle"
  echo "    URL: ${INSTANCE_URL}/lightning/setup/PipelineManagement/home"
  echo ""
  echo "  After enabling, re-run: bash setup-all.sh $ORG_ALIAS"
  exit 1
fi

# ============================================================
# Phase 3.5: Enable Autonomous Field Updates
# ============================================================
section "Phase 3.5: Autonomous Field Updates"

# After Pipeline Management is enabled, set enableDealAgentAutoApproveAllTasks=true
# to allow the agent to update opportunity fields without user approval.
#
# CONSENT GATE (#2): autonomous updates are opt-in only. Without --autonomous (or an
# interactive "yes" in Phase 0), the agent stays in suggestion-only mode and this phase
# makes NO change. This prevents the agent from silently auto-applying field writes.

AUTO_APPROVE_CURRENT=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgentAutoApproveAllTasks")

if [[ "$ENABLE_AUTONOMOUS" != "true" ]]; then
  if [[ "$AUTO_APPROVE_CURRENT" == "true" ]]; then
    log_warn "Autonomous updates are currently ON in this org, but --autonomous was not passed."
    echo "    Leaving the existing org setting unchanged (not disabling)."
    echo "    To turn autonomous updates OFF, use the Pipeline Management setup UI."
  else
    log_pass "Autonomous updates: OFF (suggestions only) — not enabled without --autonomous"
  fi
elif [[ "$AUTO_APPROVE_CURRENT" == "true" ]]; then
  log_pass "Autonomous updates: already enabled"
else
  log_info "Enabling autonomous field updates (enableDealAgentAutoApproveAllTasks=true)..."

  # SOAP Metadata API approach
  RESULT=$(soap_update "<met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'><met:fullName>SalesDealAgent</met:fullName><met:enableDealAgent>true</met:enableDealAgent><met:enableDealAgentAutoApproveAllTasks>true</met:enableDealAgentAutoApproveAllTasks></met:metadata>")

  if echo "$RESULT" | grep -qi "success.*true"; then
    AUTO_CHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgentAutoApproveAllTasks")
    if [[ "$AUTO_CHECK" == "true" ]]; then
      log_pass "Autonomous updates: enabled (SOAP API)"
    else
      log_warn "SOAP update reported success, but verification failed"
    fi
  else
    log_warn "SOAP API update failed, trying CLI metadata deploy..."

    # CLI metadata deploy approach (fallback)
    TMP_DIR=$(mktemp -d)
    mkdir -p "$TMP_DIR/settings"

    cat > "$TMP_DIR/settings/SalesDealAgent.settings-meta.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<SalesDealAgentSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableDealAgent>true</enableDealAgent>
    <enableDealAgentAutoApproveAllTasks>true</enableDealAgentAutoApproveAllTasks>
</SalesDealAgentSettings>
EOF

    CLI_RESULT=$(sf project deploy start --metadata-dir "$TMP_DIR/settings" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
    rm -rf "$TMP_DIR"

    CLI_SUCCESS=$(echo "$CLI_RESULT" | jq -r '.status // 1' 2>/dev/null | head -1 || echo "1")
    if [[ "$CLI_SUCCESS" == "0" ]]; then
      AUTO_CHECK=$(soap_extract_bool "$(soap_read "SalesDealAgentSettings" "SalesDealAgent")" "enableDealAgentAutoApproveAllTasks")
      if [[ "$AUTO_CHECK" == "true" ]]; then
        log_pass "Autonomous updates: enabled (CLI deploy)"
      else
        log_warn "CLI deploy succeeded but verification failed"
      fi
    else
      log_warn "CLI deploy failed. Autonomous updates may require manual enablement:"
      echo "    Setup → Sales → Pipeline Management → Settings"
      echo "    Enable: 'Update Fields Autonomously'"
      echo "    URL: ${INSTANCE_URL}/lightning/setup/PipelineManagement/home"
    fi
  fi
fi

# ============================================================
# Phase 4: Wait for Provisioning (with polling loop)
# ============================================================
section "Phase 4: Provisioning (agent user + PSG assignment)"

MAX_WAIT_SECONDS=90
POLL_INTERVAL=5

# Provisioning is complete when the agent user exists AND holds
# SalesManagementAgentUserPsg. The two PM PSGs themselves ship with the
# Agentforce-for-Sales license and exist even in a never-configured org, so
# "PSG count >= 2" is NOT a completion signal — the agent-user assignment is.
check_agent_provisioned() {  # sets AGENT_USER (Username) + AGENT_PSG_HELD; returns 0 when complete
  local rec agent_id
  rec=$(sf data query --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0] // empty' 2>/dev/null || echo "")
  AGENT_USER=$(echo "$rec" | jq -r '.Username // empty' 2>/dev/null || echo "")
  AGENT_PSG_HELD=0
  if [[ -n "$AGENT_USER" ]]; then
    AGENT_PSG_HELD=$(pm_agent_user_holds_psg "$ORG_ALIAS")
  fi
  [[ -n "$AGENT_USER" && "${AGENT_PSG_HELD:-0}" -ge 1 ]]
}

if check_agent_provisioned; then
  log_pass "Agent user: $AGENT_USER"
  log_pass "Agent user holds SalesManagementAgentUserPsg"
else
  echo -n "  Waiting for auto-provisioning (up to ${MAX_WAIT_SECONDS}s)"
  WAITED=0
  while [[ $WAITED -lt $MAX_WAIT_SECONDS ]]; do
    if check_agent_provisioned; then
      echo ""
      log_pass "Agent user: $AGENT_USER"
      log_pass "Agent user holds SalesManagementAgentUserPsg"
      break
    fi

    echo -n "."
    sleep "$POLL_INTERVAL"
    WAITED=$((WAITED + POLL_INTERVAL))
  done

  if [[ $WAITED -ge $MAX_WAIT_SECONDS ]]; then
    echo ""
    # Report what we have
    if [[ -n "$AGENT_USER" ]]; then
      log_pass "Agent user: $AGENT_USER"
      [[ "${AGENT_PSG_HELD:-0}" -ge 1 ]] && log_pass "Agent user holds SalesManagementAgentUserPsg" || log_warn "Agent user does not yet hold SalesManagementAgentUserPsg"
    else
      log_warn "Agent user: not yet provisioned"
    fi
    echo ""
    echo "  Provisioning may still be in progress. Continuing..."
    echo "  (Re-run verify-all.sh after 5 minutes to confirm.)"
  fi
fi

# ------------------------------------------------------------
# Phase 4a: Report recalculation Status for BOTH PSGs (no waiting)
# ------------------------------------------------------------
# #10: report the recalculation Status for BOTH SalesManagementUserPsg AND the
# autonomous agent user's SalesManagementAgentUserPsg (previously only the former
# was surfaced).
#
# What triggers each PSG's recalc:
#   - SalesManagementUserPsg: define-agent-access.sh inserts a
#     PermissionSetGroupComponent (the custom Agent Access permset), which fires
#     its recalc. That is a CUSTOM addition this skill owns.
#   - SalesManagementAgentUserPsg: this is a MANAGED PSG owned by the Deal Agent
#     package. Its components (and thus its recalc) are established by provisioning
#     (bundle publish / enablement) — we deliberately do NOT insert a component
#     into it, because writing to a managed PSG's membership is not ours to do and
#     PermissionSetGroup.Status is not client-writable. So for the agent PSG we
#     only REPORT Status; a lingering non-'Updated' here points to a provisioning
#     issue, not something setup can nudge.
#
# Both recalcs converge asynchronously — we deliberately do NOT block on either
# (completion only matters when a user views suggestions in the UI or the
# scheduled flow runs). We read Status once for reporting; a 'Failed' Status is
# tracked as an issue.
for PSG_NAME in SalesManagementUserPsg SalesManagementAgentUserPsg; do
  PSG_STATE=$(psg_status "$ORG_ALIAS" "$PSG_NAME")
  case "$PSG_STATE" in
    Updated)   log_pass "PSG '$PSG_NAME' Status: Updated" ;;
    not-found) log_info "PSG '$PSG_NAME' not present yet (provisioning may still be in progress)" ;;
    Failed)    track_issue "🟡 WARNING" "PSG '$PSG_NAME' recalculation reported Failed" "Permissions from this PSG may be incomplete. Investigate the PSG in Setup and re-run verify-all.sh." ;;
    *)         log_info "PSG '$PSG_NAME' Status: $PSG_STATE — recalculation is async and will complete on its own." ;;
  esac
done

# ============================================================
# Phase 4b: Agent Verification
# ============================================================
# CRITICAL: A Pipeline Management BotDefinition is REQUIRED for a functional
# Pipeline Management agent. Users need an interactive Sales Agent they can
# chat with.
#
# Detection matches the scheduled flow's logic: BotDefinition.AgentTemplate
# IN ('SalesMgmt__NGASalesAgent','SalesMgmt__SalesAgent'). We do NOT match
# by hardcoded DeveloperName — different orgs publish under different local
# names (SalesAgent, Sale_Agent, etc.).
#
# This phase verifies:
#   1. A PM BotDefinition exists (created via authoring bundle)
#   2. Agent user + PSG provisioned
#
# If BotDefinition is missing, it MUST be created. The script exits 1 on failure.
# ============================================================

section "Phase 4b: Agent Architecture Verification"

# Check 1: Does a PM BotDefinition exist (matched by AgentTemplate)?
AGENT_EXISTS=$(pm_bot_count "$ORG_ALIAS")

if [[ "$AGENT_EXISTS" -ge 1 ]]; then
  PM_BOT_NAME=$(pm_bot_developer_name "$ORG_ALIAS")
  log_pass "BotDefinition:${PM_BOT_NAME:-<unknown>} exists (matched by AgentTemplate)"

  # Existence is not enough: auto-provisioning leaves the BotVersion Inactive.
  # An inactive agent means the scheduled flow never adds the agent user to
  # opportunity teams (no suggestions) and Agent Access (Phase 4c) can't be
  # defined. Verify an active version exists and activate the latest if not.
  BOT_ACTIVE_COUNT=$(pm_bot_active_version_count "$ORG_ALIAS")
  if [[ "$BOT_ACTIVE_COUNT" -ge 1 ]]; then
    log_pass "BotDefinition:${PM_BOT_NAME:-<unknown>} has an active version"
  else
    log_warn "BotDefinition:${PM_BOT_NAME:-<unknown>} has no active version — activating (auto-provisioned bots land Inactive)..."
    if activate_pm_bot_if_inactive "$ORG_ALIAS"; then
      log_pass "BotDefinition:${PM_BOT_NAME:-<unknown>} activated"
    else
      track_issue "🔴 BLOCKER" "BotDefinition exists but has no active version and activation failed" "The scheduled flow will not generate suggestions and Agent Access cannot be defined. Activate the Sales Agent (Setup → Agents) or re-run: bash create-agent.sh $ORG_ALIAS"
    fi
  fi
else
  # BotDefinition missing - must be created
  # Re-check agent user (may have been set in Phase 4)
  AGENT_USER_RECHECK=$(sf data query --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")

  if [[ -n "$AGENT_USER_RECHECK" ]]; then
    # Agent user exists but BotDefinition missing - create it via bundle publish
    log_warn "No PM BotDefinition (AgentTemplate match) found - attempting to create..."
    log_pass "  Agent user: $AGENT_USER_RECHECK"
    echo "    The agent user + PSGs are sufficient for suggestion generation."
    echo "    The schedule-triggered flow runs as the agent user directly."

    # OPTIONAL: Deploy standalone agent for richer agent experience
    log_info "Deploying standalone Sales Management Agent for enhanced capabilities..."

    # Use shared library function (returns on failure so setup-all can track issues)
    if ! publish_and_activate_agent "$ORG_ALIAS" "return" "structured"; then
      track_issue "🔴 BLOCKER" "Agent bundle publish/activate failed" "A Pipeline Management BotDefinition (AgentTemplate match) is REQUIRED"
      echo "    SETUP FAILED: Cannot proceed without an active Sales Agent."
      exit 1
    fi
  else
    # Neither BotDefinition nor agent user — genuinely failed provisioning
    log_warn "No agent user or BotDefinition found after provisioning wait"
    track_issue "🔴 ERROR" "Agent user not provisioned after enablement" "Attempting SOAP toggle to re-provision agent user + PSGs, then publish authoring bundle for BotDefinition"
    echo ""
    echo "    Pipeline Management provisioning appears incomplete."
    echo "    This is unusual — the agent user is normally created on enablement."
    echo ""

    # Only attempt fallback deployment if we have NO agent user at all
    # --- APPROACH 1: SOAP toggle — re-provisions the agent user and PSGs only.
    #     It does NOT create BotDefinition:SalesAgent; that comes from the
    #     authoring-bundle publish in APPROACH 2 below.
    log_try "Attempting SOAP toggle to re-provision agent user + PSGs (does NOT create BotDefinition)..."
    # Disable
    soap_update "<met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'><met:fullName>SalesDealAgent</met:fullName><met:enableDealAgent>false</met:enableDealAgent></met:metadata>" >/dev/null
    sleep $SLEEP_TOGGLE_OFF
    # Re-enable
    soap_update "<met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'><met:fullName>SalesDealAgent</met:fullName><met:enableDealAgent>true</met:enableDealAgent><met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks></met:metadata>" >/dev/null
    sleep $SLEEP_TOGGLE_ON

    # Verify: check for agent user (primary indicator that the toggle took effect)
    AGENT_USER_RETRY=$(sf data query --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")
    if [[ -n "$AGENT_USER_RETRY" ]]; then
      log_pass "Agent user + PSGs re-provisioned via SOAP toggle: $AGENT_USER_RETRY"
    else
      log_warn "SOAP toggle did not re-provision the agent user"
    fi

    # --- APPROACH 2: Publish the authoring bundle to create BotDefinition:SalesAgent.
    #     Always attempt this: the toggle above never creates the BotDefinition,
    #     so it must come from the bundle publish regardless of whether the
    #     toggle re-provisioned the agent user.
    log_try "Publishing authoring bundle to create BotDefinition:SalesAgent..."
    if publish_and_activate_agent "$ORG_ALIAS" "return" "structured"; then
      log_pass "BotDefinition:SalesAgent published and activated via authoring bundle"
    else
      log_warn "Authoring bundle publish/activate failed"
    fi

    # Final check
    FINAL_AGENT_USER=$(sf data query --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")
    if [[ -z "$FINAL_AGENT_USER" ]]; then
      log_warn "Agent provisioning failed via all approaches"
      echo "    BLOCKER: No agent user found. Suggestions cannot generate without it."
      echo ""
      echo "    Manual resolution:"
      echo "      1. Setup → Sales → Pipeline Management → disable and re-enable"
      echo "      2. Wait 5 minutes for provisioning"
      echo "      3. Re-run: bash verify-all.sh $ORG_ALIAS"
      # Recovery exhausted: upgrade the provisional ERROR to a terminal BLOCKER so the
      # final gate reports SETUP INCOMPLETE / exit 1 instead of a false SETUP COMPLETE.
      track_issue "🔴 BLOCKER" "Agent user not provisioned after all recovery attempts" "Manually disable/re-enable Pipeline Management (Setup → Sales), wait 5 min, then re-run: bash setup-all.sh $ORG_ALIAS"
    fi
  fi
fi

# ============================================================
# Phase 4c: Agent Access (W-23242378)
# Once a PM BotDefinition exists, add it to "Agent Access" on a custom permset
# linked into SalesManagementUserPsg so human users can launch the agent.
# define-agent-access.sh is idempotent and exits gracefully if no active bot.
# ============================================================
section "Phase 4c: Agent Access"

if [[ -f "$SCRIPT_DIR/define-agent-access.sh" ]]; then
  bash "$SCRIPT_DIR/define-agent-access.sh" "$ORG_ALIAS" \
    || track_issue "🟡 WARNING" "Agent Access definition reported an issue" "Users holding SalesManagementUserPsg may not be able to launch the agent until Agent Access is defined (re-run: bash define-agent-access.sh $ORG_ALIAS)"
else
  log_warn "define-agent-access.sh not found — skipping Agent Access definition"
fi

# ============================================================
# Phase 4c.5: Stage Descriptions (BEFORE the StageName prompt)
# ============================================================
# Stage descriptions are the grounding source the managed StageName template reads;
# they MUST exist before Phase 4d deploys/activates and Phase 4e tests that prompt,
# otherwise a StageName-selected run would verify a prompt that can generate nothing.
# run_stage_descriptions() self-gates on STAGENAME_SELECTED (no-op otherwise) and
# sets the script-global STAGE_DESCRIPTIONS_BLOCKED for the Phase 8.5 summary. This
# lives in Block A, so on a --from-phase flow (Call 2) run it is skipped entirely —
# by then Call 1 has already created the descriptions.
run_stage_descriptions

# ============================================================
# Phase 4d: Prompt Templates for Selected Fields
# ============================================================
# 3-phase setup: create/activate the field-completion prompt templates BEFORE
# the flow goes live, so the verification gate (Phase 4e) can test them and the
# admin can confirm output before any scheduled run. Delegates to
# add-field-suggestion.sh --skip-flow (the flow wiring is owned by Phase 5).
#   - StageName: picklist, uses the managed template — nothing to deploy.
#   - NextStep : has a curated OOTB managed prompt. Deploy an OVERRIDE only when
#     the admin supplied a goal/instruction; otherwise leave the OOTB prompt.
#   - Custom fields: always deploy a new field-completion template (with the
#     admin's goal/instruction, or add-field-suggestion.sh's defaults).
section "Phase 4d: Prompt Templates for Selected Fields"

declare -a DEPLOYED_TEMPLATE_FIELDS=()
for _f in "${FIELD_ARRAY[@]}"; do
  if [[ "$_f" == "StageName" ]]; then
    log_info "StageName: uses the managed picklist template (nothing to deploy)."
    continue
  fi
  _goal="${FIELD_PROMPTS["${_f}_goal"]:-}"
  _instr="${FIELD_PROMPTS["${_f}_instruction"]:-}"
  if [[ "$_f" == "NextStep" && -z "$_goal" && -z "$_instr" ]]; then
    log_info "NextStep: keeping the OOTB managed prompt (no customization requested)."
    DEPLOYED_TEMPLATE_FIELDS+=("$_f")
    continue
  fi

  # Build the add-field-suggestion.sh argument list safely (array, not eval).
  _afs_args=("$ORG_ALIAS" "$_f" --skip-flow)
  [[ -n "$_goal" ]]  && _afs_args+=(--goal "$_goal")
  [[ -n "$_instr" ]] && _afs_args+=(--instruction "$_instr")

  log_try "Deploying prompt template for '$_f'..."
  if bash "$SCRIPT_DIR/add-field-suggestion.sh" "${_afs_args[@]}"; then
    log_pass "Prompt template ready for '$_f'."
    DEPLOYED_TEMPLATE_FIELDS+=("$_f")
  else
    log_warn "Prompt template deploy failed for '$_f' — suggestions for this field may not generate."
    track_issue "🟡 WARNING" "Prompt template deploy failed for field '$_f'" "Re-run: bash add-field-suggestion.sh $ORG_ALIAS $_f"
  fi
done

# --- Prune fields whose template deploy failed, BEFORE the flow is built ---
# A field with no active template that is still wired into the flow produces zero
# suggestions at runtime — the exact silent failure this 3-phase refactor exists to
# prevent. The wired set must be: successfully-deployed fields + StageName (managed
# picklist template, nothing to deploy). Rebuild SELECTED_FIELDS/FIELD_ARRAY from
# those survivors so Phase 5 wires only fields that will actually generate.
_WIRE_FIELDS=("${DEPLOYED_TEMPLATE_FIELDS[@]}")
if [[ "$STAGENAME_SELECTED" == "true" ]]; then
  _WIRE_FIELDS+=("StageName")
fi
if [[ ${#_WIRE_FIELDS[@]} -lt ${#FIELD_ARRAY[@]} ]]; then
  # At least one selected field was dropped (template deploy failed).
  _dropped=()
  for _sf in "${FIELD_ARRAY[@]}"; do
    _keep=false
    for _wf in "${_WIRE_FIELDS[@]}"; do [[ "$_sf" == "$_wf" ]] && { _keep=true; break; }; done
    [[ "$_keep" == "false" ]] && _dropped+=("$_sf")
  done
  log_warn "Dropping field(s) with no active template from the flow: ${_dropped[*]}"
fi
# Abort if every field fell out — a flow with an empty OpportunityFields collection
# would be a no-op, and this preserves the up-front abort-on-zero invariant.
if [[ ${#_WIRE_FIELDS[@]} -eq 0 ]]; then
  log_fail "No field has an active prompt template — cannot build a working flow."
  echo "  Every selected field's template failed to deploy in Phase 4d (see warnings above)."
  echo "  Fix the template deploy(s), then re-run setup."
  exit 1
fi
FIELD_ARRAY=("${_WIRE_FIELDS[@]}")
SELECTED_FIELDS=$(IFS=,; echo "${_WIRE_FIELDS[*]}")

# Fields to VERIFY (Phase 4e) — a superset of DEPLOYED_TEMPLATE_FIELDS. StageName
# deploys nothing (managed picklist template) so it's absent from the deployed set,
# but it still generates a default suggestion the admin should see and get a chance
# to override. Same for NextStep left uncustomized (OOTB prompt) — it's already in
# the deployed set. So: show a default suggestion for every SELECTED field, even
# uncustomized ones ("only when selected" — never pull in unselected fields).
declare -a VERIFY_FIELDS=("${DEPLOYED_TEMPLATE_FIELDS[@]}")
if [[ "$STAGENAME_SELECTED" == "true" ]]; then
  VERIFY_FIELDS+=("StageName")
fi

# --- --through-phase prompts: stop here, hand off to the agent tune-loop ---
# The templates are deployed and active but the flow is NOT built. The agent now
# runs the interactive per-field tune-loop (generate a tailored note → seed → run
# /generations → show the suggestion → loop until the user approves), then resumes
# with `--from-phase flow`. We STOP BEFORE the built-in Phase 4e gate because the
# agent's loop supersedes it (and a piped-stdin run couldn't block on it anyway).
if [[ "$RUN_THROUGH_PHASE" == "prompts" ]]; then
  section "Prompt templates ready — handing off for tuning"
  log_pass "Deployed/active prompt template field(s): ${DEPLOYED_TEMPLATE_FIELDS[*]:-none}"
  if [[ "$STAGENAME_SELECTED" == "true" ]]; then
    log_info "StageName is also selected (managed picklist template; no per-field tuning)."
  fi
  echo ""
  echo "  NEXT (agent tune-loop): for each CUSTOMIZED field, seed a tailored note and test:"
  echo "    bash add-field-suggestion.sh $ORG_ALIAS <Field> --skip-flow --force \\"
  echo "         --goal '<goal>' --instruction '<instruction>' \\"
  echo "         --verify-with-note --note '<note tailored to the instruction>'"
  echo ""
  echo "  ALSO show the DEFAULT suggestion for every selected field left UNCUSTOMIZED"
  echo "  (StageName always; NextStep when no goal/instruction was given) so the user"
  echo "  can decide whether to keep or change the default even though they didn't tune it:"
  echo "    bash verify-prompt-generation.sh $ORG_ALIAS <Field> <oppId>"
  echo "  To CHANGE it: NextStep is tunable via add-field-suggestion.sh (above);"
  echo "  StageName's suggestion is shaped by its stage descriptions — re-run with"
  echo "  --create-stage-descriptions (or edit OpptStageDescription) to change it."
  echo ""
  echo "  Loop until the user approves each suggestion, then build & activate the flow:"
  echo "    bash setup-all.sh $ORG_ALIAS --fields \"$SELECTED_FIELDS\" --from-phase flow"
  echo ""
  log_info "Stopping after Phase 4d (--through-phase prompts). Flow NOT yet built."
  exit 0
fi

# ============================================================
# Phase 4e: Prompt Verification Gate (before the flow goes live)
# ============================================================
# 3-phase setup: the templates from Phase 4d are now active but the flow is NOT
# yet deployed/activated. Test each template SYNCHRONOUSLY against a real
# opportunity + a seeded note, show the admin exactly what the AI will suggest,
# and (interactively) gate flow activation on their approval. This catches a bad
# goal/instruction BEFORE the scheduled run ever fires — far cheaper to fix now
# than after go-live.
#
# We verify VERIFY_FIELDS — every SELECTED field that generates a suggestion,
# including ones left uncustomized (NextStep on its OOTB prompt, and StageName on
# the managed picklist template). Showing those defaults lets the admin override a
# default they never explicitly tuned. StageName generates only because Phase 4c.5
# already created its grounding stage descriptions.
#
# Fully skipped when:
#   - --skip-prompt-verification was passed (explicit opt-out), OR
#   - no selected field generates a suggestion (VERIFY_FIELDS empty).
# In NON_INTERACTIVE runs (incl. agent-driven — a piped stdin forces it) the
# generation still RUNS and the suggestions are PRINTED for review; only the human
# yes/no gate degrades to informational (the flow proceeds without blocking).
section "Phase 4e: Prompt Verification Gate"

if [[ "$SKIP_PROMPT_VERIFICATION" == "true" ]]; then
  log_info "Prompt verification skipped (--skip-prompt-verification)."
elif [[ ${#VERIFY_FIELDS[@]} -eq 0 ]]; then
  log_info "No selected field generates a suggestion to verify."
else
  # NOTE ON NON-INTERACTIVE RUNS (incl. agent-driven, since a piped stdin forces
  # NON_INTERACTIVE): we STILL seed a test opp/note and run /generations below so
  # the generated suggestions are printed for review. What a non-interactive run
  # cannot do is BLOCK on a human yes/no — so the approval gate at the end degrades
  # to informational output and the flow proceeds. An agent relays this output to
  # the user; a true unattended run (cron/CI) simply logs it.
  # --- Find an eligible open opportunity (matches the flow's own filter) ---
  # IsClosed=false AND CloseDate within +90 days, so we don't test against an opp
  # the scheduled flow would itself skip (which would look like a false negative).
  VERIFY_OPP_ID=$(sf data query -q "SELECT Id FROM Opportunity WHERE IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90 ORDER BY LastModifiedDate DESC LIMIT 1" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')

  if [[ -z "$VERIFY_OPP_ID" ]]; then
    log_try "No eligible open opportunity found — creating one for verification."
    # A bare Name + future CloseDate + open Stage satisfies the flow's eligibility
    # filter. Don't hardcode 'Prospecting' — orgs with custom Sales Processes/record
    # types may not have it. Query the first active, open (non-won/lost) stage.
    _open_stage=$(sf data query -q "SELECT MasterLabel FROM OpportunityStage WHERE IsActive=true AND IsClosed=false ORDER BY SortOrder LIMIT 1" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].MasterLabel // empty')
    [[ -z "$_open_stage" ]] && _open_stage="Prospecting"  # last-resort default
    VERIFY_OPP_ID=$(sf data create record --sobject Opportunity \
      --values "Name='PM Setup Verification Opp' StageName='${_open_stage}' CloseDate=$(python3 -c 'import datetime; print((datetime.date.today()+datetime.timedelta(days=30)).isoformat())')" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty')
    if [[ -n "$VERIFY_OPP_ID" ]]; then
      log_pass "Created verification opportunity $VERIFY_OPP_ID"
    else
      log_warn "Could not create a verification opportunity; skipping the prompt gate."
      track_issue "🟡 WARNING" "Prompt verification skipped — no eligible opportunity" "Create an open Opportunity (CloseDate within 90 days) and test with verify-prompt-generation.sh."
      VERIFY_OPP_ID=""
    fi
  else
    log_pass "Using eligible opportunity $VERIFY_OPP_ID for verification."
  fi

  if [[ -n "$VERIFY_OPP_ID" ]]; then
    # --- Seed a ContentNote with sample conversation signal + link to the opp ---
    # Interpolate relative dates (today / today+9d) so the sample never reads as
    # stale to the model on a run weeks after this was authored.
    _note_today=$(python3 -c 'import datetime; print(datetime.date.today().strftime("%B %-d"))')
    _note_soon=$(python3 -c 'import datetime; print((datetime.date.today()+datetime.timedelta(days=9)).strftime("%B %-d"))')
    NOTE_BODY="Call with John Smith on ${_note_today}: Discussed Q4 budget approval. John mentioned competitor Acme Corp is being evaluated. Next step: Schedule executive sponsor meeting by ${_note_soon}. Risk: Budget freeze possible if exec sponsor changes."
    # macOS/BSD `base64` line-wraps at 76 cols (embeds newlines); GNU's `-w0` isn't
    # portable. `tr -d '\n'` strips wraps on both so the value stays single-line and
    # doesn't break the --values string below.
    NOTE_B64=$(printf '%s' "$NOTE_BODY" | base64 | tr -d '\n')
    log_try "Seeding a ContentNote with sample conversation data."
    # Note-seeding is best-effort: `|| true` keeps a create failure from tripping
    # `set -e` so it degrades to the log_warn fallback instead of aborting the gate.
    VERIFY_NOTE_ID=$(sf data create record --sobject ContentNote --values "Title='PM Setup Verification Note' Content='${NOTE_B64}'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty' || true)
    if [[ -n "$VERIFY_NOTE_ID" ]]; then
      # ContentNote Id IS the ContentDocumentId (shared 069 prefix); link directly.
      # The ContentVersion→LatestVersionId subquery returns null on some orgs.
      if sf data create record --sobject ContentDocumentLink --values "ContentDocumentId='${VERIFY_NOTE_ID}' LinkedEntityId='${VERIFY_OPP_ID}' ShareType='V' Visibility='AllUsers'" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null; then
        log_pass "Seeded note and linked to $VERIFY_OPP_ID"
      else
        log_warn "Note created but could not link to the opportunity; generation runs against existing grounding data only."
      fi
    else
      log_warn "Could not seed a note; generation runs against existing grounding data only."
    fi

    # --- Generate a suggestion per verified field and show it to the admin ---
    echo ""
    echo "  Testing each prompt against opportunity $VERIFY_OPP_ID:"
    echo ""
    _gen_ok=0   # count templates that returned usable output
    for _vf in "${VERIFY_FIELDS[@]}"; do
      # Resolve the template name the /generations endpoint expects:
      #   - StageName: the managed picklist template (nothing deployed, but it still
      #     generates a default the admin should see and can choose to override).
      #   - NextStep: the managed template (an override folds into it as a new
      #     version; the OOTB prompt shares the same name), so always query the
      #     managed name.
      #   - Custom field: Recommend<Field, stripped of __c and non-alnum>forOpp,
      #     matching add-field-suggestion.sh's dev-name derivation.
      if [[ "$_vf" == "StageName" ]]; then
        _vtmpl="sales_pipe_mgmt__RecommendStageforOpp"
      elif [[ "$_vf" == "NextStep" ]]; then
        _vtmpl="sales_pipe_mgmt__RecommendNextStepforOpp"
      else
        _vtmpl="Recommend$(printf '%s' "$_vf" | sed 's/__c$//' | sed 's/[^A-Za-z0-9]//g')forOpp"
      fi

      # Bound at 120s: generation can legitimately take longer than a plain REST
      # call (CURL_TIMEOUT=30), but must not hang indefinitely and blow the run's
      # tool timeout. A timeout yields non-zero → the `|| echo '{}'` fallback, so a
      # stall reads as "no output" and flows into the blocked-field handling below.
      _gen=$(with_timeout 120 sf api request rest "/services/data/v${API_VERSION}/einstein/prompt-templates/${_vtmpl}/generations" \
        --method POST --target-org "$ORG_ALIAS" \
        --body "{\"isPreview\":false,\"inputParams\":{\"valueMap\":{\"Input:Opportunity\":{\"value\":{\"id\":\"${VERIFY_OPP_ID}\"}}}},\"additionalConfig\":{\"numGenerations\":1,\"temperature\":0,\"applicationName\":\"PromptTemplateGenerationsInvocable\"}}" 2>/dev/null || echo '{}')
      _gentext=$(echo "$_gen" | jq -r '.generations[0].text // empty' 2>/dev/null)
      if [[ -n "$_gentext" ]]; then
        # The generation text is itself a JSON blob (FieldName/SuggestedNewValue/Reasoning).
        _sugg=$(echo "$_gentext" | jq -r '.SuggestedNewValue // empty' 2>/dev/null)
        _reason=$(echo "$_gentext" | jq -r '.Reasoning // empty' 2>/dev/null)
        _gen_ok=$((_gen_ok + 1))
        if [[ -n "$_sugg" ]]; then
          echo "  ── $_vf ($_vtmpl)"
          echo "     Suggested: $_sugg"
          [[ -n "$_reason" ]] && echo "     Reasoning: $_reason"
        else
          echo "  ── $_vf ($_vtmpl)"
          echo "     Raw output: $_gentext"
        fi
      else
        _generr=$(echo "$_gen" | jq -r '.[0].message // .message // empty' 2>/dev/null | head -1)
        echo "  ── $_vf ($_vtmpl)"
        log_warn "No suggestion generated${_generr:+ — $_generr}"
      fi
      echo ""
    done

    # --- The gate: admin must approve before the flow is deployed/activated ---
    # If NOT ONE template produced output, the gate tested nothing — approving
    # "prompts look good" here would be meaningless. Require an explicit,
    # differently-worded override so a reviewer who saw only warnings cannot
    # wave through unvalidated prompts on autopilot.
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
      # No TTY to block on — the gate degrades to informational output. Report
      # what was (or wasn't) generated and proceed; the caller (agent/operator)
      # reviews the printed suggestions and can re-run add-field-suggestion.sh to
      # adjust a prompt afterward.
      if [[ "$_gen_ok" -eq 0 ]]; then
        log_warn "Non-interactive run: NO template produced output — flow will activate on UNVERIFIED prompts."
        echo "  Review the warnings above; adjust with:"
        echo "    bash add-field-suggestion.sh $ORG_ALIAS <Field> --skip-flow --goal '...' --instruction '...' --force"
        track_issue "🟡 WARNING" "Prompts unverified (non-interactive, no generation output)" "Review suggestions; re-run add-field-suggestion.sh to adjust, then re-run setup."
      else
        log_info "Non-interactive run: suggestions shown above are informational — proceeding to flow activation."
        echo "  If a suggestion looks wrong, adjust its prompt with:"
        echo "    bash add-field-suggestion.sh $ORG_ALIAS <Field> --skip-flow --goal '...' --instruction '...' --force"
      fi
    elif [[ "$_gen_ok" -eq 0 ]]; then
      log_warn "No template produced any output — the prompts could NOT be validated."
      echo ""
      echo "  Common causes: templates still activating (retry in a minute), no"
      echo "  grounding data on the opportunity, or a template deploy that failed above."
      echo "  Proceeding now would activate the flow on UNVERIFIED prompts."
      echo ""
      if ! confirm "Proceed to build & activate the flow anyway, WITHOUT verified prompt output?"; then
        log_fail "Verification could not complete and was not overridden. Flow NOT activated."
        echo ""
        echo "  The prompt templates are deployed and active, but the suggestion flow"
        echo "  has not been built or activated, so no scheduled suggestions will run."
        echo "  Inspect a prompt with:"
        echo "    bash verify-prompt-generation.sh $ORG_ALIAS <Field>"
        echo "  or adjust one with:"
        echo "    bash add-field-suggestion.sh $ORG_ALIAS <Field> --skip-flow --goal '...' --instruction '...' --force"
        echo "  Then re-run this setup to complete flow activation."
        exit 1
      fi
      log_warn "Proceeding to flow activation on UNVERIFIED prompts (explicit override)."
    elif ! confirm "Prompts look good — proceed to build & activate the flow?"; then
      log_fail "Verification declined. Flow NOT activated."
      echo ""
      echo "  The prompt templates are deployed and active, but the suggestion flow"
      echo "  has not been built or activated, so no scheduled suggestions will run."
      echo "  To adjust a prompt, edit it with:"
      echo "    bash add-field-suggestion.sh $ORG_ALIAS <Field> --skip-flow --goal '...' --instruction '...' --force"
      echo "  Then re-run this setup to complete flow activation."
      exit 1
    else
      log_pass "Verification approved — proceeding to flow activation."
    fi
  fi
fi

fi  # END BLOCK A (Phase 1.5–4e) — skipped entirely on a --from-phase flow run.

# ============================================================
# BLOCK B — Flow, Agent wiring & Verification (Phase 5 → 8)
# ============================================================
# Builds the suggestion flow from the approved field set, activates it, wires the
# agent/PSG, and runs final verification. Self-contained: everything it needs it
# re-derives from the org (bot count, PSG id/state) or from the context vars set in
# Phase 0/1/1.7 — so it runs correctly both in a full end-to-end pass and as the
# second half of a split (--from-phase flow) run.

# --- Split-path re-prune: fields must have an ACTIVE prompt template ---
# On a full run, Block A already pruned SELECTED_FIELDS/FIELD_ARRAY to fields with
# a successfully-deployed active template (lines ~1635-1664). On a --from-phase flow
# run Block A is skipped, so SELECTED_FIELDS is still the RAW --fields the agent
# passed. Wiring a field with no active template into the flow yields zero
# suggestions at runtime — the exact silent failure this refactor prevents. So
# re-derive the survivor set here from the org (read-only), mirroring Block A's
# invariant: keep StageName unconditionally (managed picklist, nothing to deploy),
# keep any other field whose GenAiPromptTemplate is active.
if [[ "$RUN_FROM_PHASE" == "flow" ]]; then
  _ACTIVE_TEMPLATES=$(sf api request rest "/services/data/v${API_VERSION}/einstein/prompt-templates" --target-org "$ORG_ALIAS" 2>/dev/null \
    | jq -r '.promptRecords[]? | select(.fields.IsActive.value==true or .fields.IsActive.value=="true") | .fields.DeveloperName.value' 2>/dev/null || echo "")
  _WIRE_FIELDS=()
  _dropped=()
  for _sf in "${FIELD_ARRAY[@]}"; do
    if [[ "$_sf" == "StageName" ]]; then
      _WIRE_FIELDS+=("StageName")
      continue
    fi
    # Expected dev name: Recommend<Field-without-__c-and-non-alnum>forOpp. Match with
    # or without the sales_pipe_mgmt__ namespace prefix (NextStep's managed template
    # is namespaced; standalone custom-field templates are not).
    _clean=$(echo "$_sf" | sed 's/__c$//' | sed 's/[^A-Za-z0-9]//g')
    _expect="Recommend${_clean}forOpp"
    if echo "$_ACTIVE_TEMPLATES" | grep -qiE "(^|__)${_expect}\$"; then
      _WIRE_FIELDS+=("$_sf")
    else
      _dropped+=("$_sf")
    fi
  done
  if [[ ${#_dropped[@]} -gt 0 ]]; then
    log_warn "Dropping field(s) with no active prompt template from the flow: ${_dropped[*]}"
    echo "  These templates were not active on the org. Re-run the tune-loop"
    echo "  (add-field-suggestion.sh ... --force) for each, then re-run --from-phase flow."
  fi
  if [[ ${#_WIRE_FIELDS[@]} -eq 0 ]]; then
    log_fail "No selected field has an active prompt template — cannot build a working flow."
    echo "  Deploy/activate at least one field's template (Call 1 + tune-loop), then re-run --from-phase flow."
    exit 1
  fi
  FIELD_ARRAY=("${_WIRE_FIELDS[@]}")
  SELECTED_FIELDS=$(IFS=,; echo "${_WIRE_FIELDS[*]}")
  log_info "Flow will wire ${#FIELD_ARRAY[@]} field(s) with active templates: $SELECTED_FIELDS"
fi

# ============================================================
# Phase 5: Schedule-Triggered Flow (with deploy + activation)
# ============================================================
section "Phase 5: Schedule-Triggered Flow"

# Detection: check by SourceTemplateId, naming convention, and exact API name
FLOW_NAME=""
for QUERY in \
  "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" \
  "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate=false" \
  "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = 'Process_Field_Update_Suggestions' AND IsTemplate=false"; do

  FLOW_NAME=$(sf data query --query "$QUERY" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")
  [[ -n "$FLOW_NAME" ]] && break
done

if [[ -n "$FLOW_NAME" ]]; then
  log_pass "Flow found: $FLOW_NAME"
else
  log_info "Flow not found. Deploying from pre-retrieved template..."

  TEMPLATE_FILE="$SCRIPT_DIR/../assets/pipeline_management_flow.flow-meta.xml"

  if [[ -f "$TEMPLATE_FILE" ]]; then
    ensure_sfdx_project
    mkdir -p force-app/main/default/flows
    FLOW_FILE="force-app/main/default/flows/Process_Field_Update_Suggestions.flow-meta.xml"

    # Greenfield: BUILD the flow with ONLY the up-front-selected fields (no
    # deploy-then-strip). build_field_collection reads the base template and
    # writes FLOW_FILE with exactly SELECTED_FIELDS wired into
    # AddOppFieldsToCollection, emitting a distinct nonzero exit on each failure
    # (2 empty set / 3 parse-fail / 4 assignment-missing / 5 write-fail).
    # We do NOT fall back to copying the base template: that verbatim copy wires
    # BOTH OOTB fields, which would ship StageName the admin excluded (and with no
    # supporting stage descriptions). The selected set is already validated
    # non-empty (Phase 1.7) and pruned to fields with active templates, so a build
    # failure here is a genuine environment problem — abort loudly instead.
    if build_field_collection "$SELECTED_FIELDS" "$TEMPLATE_FILE" "$FLOW_FILE"; then
      log_pass "Flow built with ${#FIELD_ARRAY[@]} selected field(s): $SELECTED_FIELDS"
    else
      _bfc_rc=$?
      log_fail "Could not build the flow from selected fields (build_field_collection rc=$_bfc_rc)."
      case $_bfc_rc in
        2) echo "  Empty field set after pruning — nothing to wire." ;;
        3) echo "  Base flow template did not parse as XML: $TEMPLATE_FILE" ;;
        4) echo "  AddOppFieldsToCollection assignment not found in the base template." ;;
        5) echo "  Could not write the built flow to $FLOW_FILE (permissions/disk)." ;;
        *) echo "  Unexpected failure; check that python3 is on PATH." ;;
      esac
      echo "  Flow NOT deployed. Fix the above and re-run setup."
      exit 1
    fi

    # Update startDate to today
    TODAY=$(date +%Y-%m-%d)
    sed_inplace "s|<startDate>[^<]*</startDate>|<startDate>${TODAY}</startDate>|g" "$FLOW_FILE"

    # Sync the flow's SalesManagementAgentTemplate constant with the actual
    # AgentTemplate of the bot deployed to this org. The template's default
    # value is the legacy SalesMgmt__SalesAgent, but our authoring bundle
    # publishes the NGA variant (SalesMgmt__NGASalesAgent). The flow's
    # BotDefinition lookup matches on this constant, so a mismatch means
    # the action silently fails to find the agent at runtime.
    set +e  # Allow pm_bot_agent_template to return non-zero without aborting
    DETECTED_TEMPLATE=$(pm_bot_agent_template "$ORG_ALIAS")
    DETECT_RC=$?
    set -e
    case $DETECT_RC in
      0)
        PM_BOT_TOTAL=$(pm_bot_count "$ORG_ALIAS")
        if [[ "${PM_BOT_TOTAL:-0}" -gt 1 ]]; then
          log_warn "Multiple active Pipeline Management bots detected on org (${PM_BOT_TOTAL}). Flow will bind to: $DETECTED_TEMPLATE (NGA preferred). Clean up stale bots to avoid runtime ambiguity."
        fi
        sed_inplace "s|<stringValue>SalesMgmt__SalesAgent</stringValue>|<stringValue>${DETECTED_TEMPLATE}</stringValue>|g" "$FLOW_FILE"
        log_info "Flow template constant set to: $DETECTED_TEMPLATE"
        ;;
      1)
        log_fail "No active Pipeline Management bot found on org. Phase 4b should have created and activated the bot before flow deploy. Aborting flow deploy to prevent binding the flow to a missing or inactive agent."
        exit 1
        ;;
      *)
        log_fail "Could not query BotDefinition for AgentTemplate (sf data query failed — auth, network, or API error). Re-run after resolving the underlying issue."
        exit 1
        ;;
    esac

    # Field wiring for the greenfield flow is already done: build_field_collection
    # (above) wrote FLOW_FILE with exactly the up-front-selected fields. There is
    # no deploy-then-strip here. strip_flow_field / add_flow_field (from
    # shared/flow-builder.sh) are reserved for the REPAIR path below, which reconciles
    # an already-deployed flow's wired fields to the selected set.

    # --- APPROACH 1: Deploy as source ---
    log_try "Deploying flow via source deploy..."
    DEPLOY_RESULT=$(sf project deploy start --source-dir "$FLOW_FILE" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')

    if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
      FLOW_NAME="Process_Field_Update_Suggestions"
      log_pass "Flow deployed: $FLOW_NAME"
    else
      DEPLOY_ERR=$(safe_jq "$DEPLOY_RESULT" '.result.details.componentFailures[0].problem // .message // "unknown"' "unknown")
      echo "    Source deploy error: $DEPLOY_ERR"

      # --- APPROACH 2: Deploy as metadata ---
      log_try "Retrying as metadata deploy..."
      DEPLOY_RESULT=$(sf project deploy start --metadata "Flow:Process_Field_Update_Suggestions" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
      if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
        FLOW_NAME="Process_Field_Update_Suggestions"
        log_pass "Flow deployed: $FLOW_NAME (metadata approach)"
      else
        log_warn "Both deploy approaches failed."
      fi
    fi
  else
    log_warn "Template file not found at: $TEMPLATE_FILE"
  fi

  # --- If still no flow, UI guidance ---
  if [[ -z "$FLOW_NAME" ]]; then
    log_warn "Flow requires manual creation via Setup UI."
    echo ""
    echo "  Steps:"
    echo "    1. Open: ${INSTANCE_URL}/lightning/setup/Flows/home"
    echo "    2. Find 'OppSuggGenSchFlow' (template, sales_pipe_mgmt namespace)"
    echo "    3. Click 'Save As' → Label: 'Process Field Update Suggestions'"
    echo "    4. Click 'Activate'"
    echo ""

    # Non-interactive: skip (don't block on user input in agent context)
    if [[ -t 0 ]]; then
      while true; do
        read -rp "  Press Enter after completing (or 'skip' to continue): " RESPONSE
        if [[ "$RESPONSE" == "skip" ]]; then break; fi
        FLOW_NAME=$(sf data query --query "SELECT ApiName FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")
        [[ -n "$FLOW_NAME" ]] && { log_pass "Flow detected: $FLOW_NAME"; break; }
        log_warn "Flow not detected yet."
      done
    fi
  fi
fi

# --- Flow Activation + Field Reconciliation (REPAIR path for an existing flow) ---
# When the flow already exists we do NOT rebuild it from the base template (that
# would discard the org-specific SalesManagementAgentTemplate constant the
# deployed flow carries). Instead we RECONCILE the flow's wired fields to the
# up-front selected set — the "fix method": strip fields no longer selected,
# add newly-selected ones (via strip_flow_field / add_flow_field). We then set
# it Active and redeploy. This runs whether or not the flow is currently active,
# because the field set may have changed even on an active flow.
if [[ -n "$FLOW_NAME" ]]; then
  FLOW_ACTIVE=$(sf data query --query "SELECT IsActive FROM FlowDefinitionView WHERE ApiName='${FLOW_NAME}'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].IsActive // "false"' 2>/dev/null || echo "false")

  log_try "Reconciling existing flow to selected fields + activating..."

  # Retrieve → reconcile fields → set Active → reconcile constant → deploy
  ensure_sfdx_project
  mkdir -p force-app/main/default/flows
  sf project retrieve start --metadata "Flow:${FLOW_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null || true

  FLOW_FILE="force-app/main/default/flows/${FLOW_NAME}.flow-meta.xml"
  if [[ -f "$FLOW_FILE" ]]; then
      # --- Field reconciliation: make the wired set == SELECTED_FIELDS ---
      # Strip any wired field not in the selected set; add any selected field
      # not yet wired. Both helpers are idempotent and namespace-safe (python3).
      # The AddOppFieldsToCollection assignment must never end up empty — the
      # selected set is guaranteed non-empty (validated in Phase 1.7), so as long
      # as we add-before-we-finish the assignment stays valid.
      FIELDS_CHANGED=false
      WIRED_FIELDS="$(flow_wired_fields "$FLOW_FILE" 2>/dev/null || echo "")"
      # Normalized ",a,b,c," form computed once for exact-comma membership tests
      # (mirrors the ,$SELECTED_FIELDS, idiom on the strip side).
      WIRED_CSV=",$(printf '%s' "$WIRED_FIELDS" | tr '\n' ',' | sed 's/,,*/,/g'),"
      if [[ -n "$WIRED_FIELDS" ]]; then
        while IFS= read -r _wired; do
          [[ -z "$_wired" ]] && continue
          if [[ ",$SELECTED_FIELDS," != *",$_wired,"* ]]; then
            # strip: rc 0 = removed, 2 = not present (benign), other = real error.
            _rc=0; strip_flow_field "$FLOW_FILE" "$_wired" || _rc=$?
            case $_rc in
              0) FIELDS_CHANGED=true; log_info "Unwired field no longer selected: $_wired" ;;
              2) : ;;  # not present — nothing to do
              *) log_warn "Could not unwire '$_wired' (rc=$_rc) — it may remain in the flow."
                 track_issue "🟡 WARNING" "Flow field reconcile: strip of '$_wired' failed (rc=$_rc)" "The flow's wired field set may not match the selected set. Re-run setup or edit the flow manually." ;;
            esac
          fi
        done <<< "$WIRED_FIELDS"
      fi
      for _sel in "${FIELD_ARRAY[@]}"; do
        if [[ "$WIRED_CSV" != *",$_sel,"* ]]; then
          # add: rc 0 = added, 2 = already wired (benign), other = real error.
          _rc=0; add_flow_field "$FLOW_FILE" "$_sel" || _rc=$?
          case $_rc in
            0) FIELDS_CHANGED=true; log_info "Wired newly-selected field: $_sel" ;;
            2) : ;;  # already wired — nothing to do
            *) log_warn "Could not wire '$_sel' (rc=$_rc) — it may not generate suggestions."
               track_issue "🟡 WARNING" "Flow field reconcile: add of '$_sel' failed (rc=$_rc)" "The selected field '$_sel' may not be wired into the flow. Re-run: bash add-field-suggestion.sh $ORG_ALIAS $_sel" ;;
          esac
        fi
      done
      if [[ "$FIELDS_CHANGED" == "true" ]]; then
        log_pass "Flow fields reconciled to: $SELECTED_FIELDS"
      else
        log_info "Flow fields already match selected set: $SELECTED_FIELDS"
      fi

      # Short-circuit only when nothing needs deploying: already active AND no
      # field change. Otherwise fall through to set-Active + redeploy.
      if [[ "$FLOW_ACTIVE" == "true" && "$FIELDS_CHANGED" == "false" ]]; then
        log_pass "Flow is ACTIVE (no field changes needed)"
      else
      sed_inplace 's|<status>Draft</status>|<status>Active</status>|g' "$FLOW_FILE"
      sed_inplace 's|<status>Obsolete</status>|<status>Active</status>|g' "$FLOW_FILE"

      # Reconcile the flow's SalesManagementAgentTemplate constant with the
      # on-org bot. The retrieved flow carries whatever template was wired
      # in at last deploy; if the org has since been upgraded (legacy ->
      # NGA) the constant is stale and the BotDefinition lookup misses.
      # The second sed handles the symmetric NGA -> legacy downgrade case.
      #
      # In this reconcile path we warn-and-skip rather than exit on failure:
      # the flow already exists on the org, so the worst case is that we
      # leave the existing constant in place and the deploy below may fail
      # loudly with a Salesforce-specific error — preferable to aborting
      # the whole setup script just because we couldn't sync the constant.
      set +e  # Allow pm_bot_agent_template to return non-zero without aborting
      DETECTED_TEMPLATE=$(pm_bot_agent_template "$ORG_ALIAS")
      DETECT_RC=$?
      set -e
      case $DETECT_RC in
        0)
          PM_BOT_TOTAL=$(pm_bot_count "$ORG_ALIAS")
          if [[ "${PM_BOT_TOTAL:-0}" -gt 1 ]]; then
            log_warn "Multiple active Pipeline Management bots detected on org (${PM_BOT_TOTAL}). Flow will bind to: $DETECTED_TEMPLATE (NGA preferred). Clean up stale bots to avoid runtime ambiguity."
          fi
          sed_inplace "s|<stringValue>SalesMgmt__SalesAgent</stringValue>|<stringValue>${DETECTED_TEMPLATE}</stringValue>|g" "$FLOW_FILE"
          sed_inplace "s|<stringValue>SalesMgmt__NGASalesAgent</stringValue>|<stringValue>${DETECTED_TEMPLATE}</stringValue>|g" "$FLOW_FILE"
          log_info "Flow template constant reconciled to: $DETECTED_TEMPLATE"
          ;;
        1)
          log_warn "No active Pipeline Management bot found on org. Skipping template-constant reconciliation; activation will proceed with the existing constant and may fail if the bot is missing or inactive."
          ;;
        *)
          log_warn "Could not query BotDefinition for AgentTemplate (sf data query failed). Skipping template-constant reconciliation; activation will proceed with the existing constant."
          ;;
      esac

      if sf project deploy start --metadata "Flow:${FLOW_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -e '.status == 0' >/dev/null 2>&1; then
        log_pass "Flow activated"
      else
        log_warn "Flow activation failed. Activate manually: Setup → Flows → ${FLOW_NAME} → Activate"
      fi
      fi  # end: active+unchanged short-circuit vs set-Active+redeploy
    else
      log_warn "Could not retrieve flow. Activate manually in Setup → Flows."
    fi
fi

# ============================================================
# Phase 6: Stage Descriptions — RELOCATED
# ============================================================
# Stage-description creation now runs earlier, in Block A as Phase 4c.5 (before the
# StageName prompt is deployed/activated/tested), via run_stage_descriptions() in
# shared/stage-descriptions.sh. It is a prerequisite for the managed StageName template
# to generate anything, so it must precede Phase 4d/4e. Nothing to do here.

# ============================================================
# Phase 7: User Permissions
# ============================================================
section "Phase 7: User Permissions"

CURRENT_USER=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.username // empty' 2>/dev/null || echo "")
CURRENT_USER=$(sanitize_display "$CURRENT_USER" 80)
# Sanitize for SOQL interpolation (prevent injection)
CURRENT_USER_SAFE=$(sanitize_soql_value "$CURRENT_USER")

PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

if [[ -z "$PSG_ID" ]]; then
  log_warn "SalesManagementUserPsg not found (provisioning may still be in progress)"
else
  # The PSG recalc is triggered by provisioning and converges asynchronously; we do
  # NOT block on it. Report its current Status for context, then attempt assignment.
  # #5: if the PSG has not finished recalculating, the insert is rejected with
  # INVALID_CROSS_REFERENCE_KEY — assign_user_psg() classifies that explicitly and
  # tells the operator to re-run, instead of the old `|| log_pass` that masked the
  # rejection as a bogus "Already assigned".
  PSG_STATE=$(psg_status "$ORG_ALIAS" "SalesManagementUserPsg")
  if [[ "$PSG_STATE" != "Updated" ]]; then
    log_info "SalesManagementUserPsg Status: $PSG_STATE — recalculation may still be in progress; assignment may need a re-run."
  fi

  # assign_user_psg <user-id> <display-name> — insert PermissionSetAssignment and
  # classify the outcome. Never masks a real rejection as success.
  assign_user_psg() {
    local user_id="$1" display="$2" res msg
    res=$(sf data create record --sobject PermissionSetAssignment \
      --values "AssigneeId='${user_id}' PermissionSetGroupId='${PSG_ID}'" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')
    if echo "$res" | jq -e '.result.id // empty' >/dev/null 2>&1; then
      log_pass "Assigned SalesManagementUserPsg to: $display"; return 0
    fi
    msg=$(echo "$res" | jq -r '.message // .result.message // ""' 2>/dev/null || echo "")
    if echo "$msg" | grep -qi "DUPLICATE_VALUE"; then
      log_info "Already assigned: $display"
    elif echo "$msg" | grep -qi "INVALID_CROSS_REFERENCE_KEY"; then
      log_warn "Assignment for $display rejected (INVALID_CROSS_REFERENCE_KEY) — SalesManagementUserPsg has not finished recalculating."
      echo "    Re-run: bash setup-all.sh $ORG_ALIAS once the PSG Status reads 'Updated'."
      track_issue "🟡 WARNING" "User PSG assignment deferred (PSG recalculating)" "Re-run setup-all.sh once SalesManagementUserPsg Status is 'Updated' to finish assigning $display."
    else
      log_warn "Failed to assign $display: ${msg:-unknown}"
    fi
    return 1
  }

  # assign_user_list <comma-separated-usernames> — resolve each username to an Id and
  # assign the PSG. Only ever processes the EXPLICIT list handed to it; there is no
  # code path that queries all/standard users and bulk-grants. Adding users is always
  # deliberate: the running user, an operator-typed interactive list, or --users.
  assign_user_list() {
    local raw_list="$1" raw_user username username_safe user_id
    IFS=',' read -ra _USERS <<< "$raw_list"
    for raw_user in "${_USERS[@]}"; do
      username=$(echo "$raw_user" | xargs)
      [[ -z "$username" ]] && continue
      username_safe=$(sanitize_soql_value "$username")
      user_id=$(sf data query -q "SELECT Id FROM User WHERE Username = '${username_safe}'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")
      if [[ -z "$user_id" ]]; then
        log_fail "User not found: $username"
      else
        assign_user_psg "$user_id" "$username" || true
      fi
    done
  }

  # Assign current user
  if [[ -n "$CURRENT_USER" ]]; then
    USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username = '${CURRENT_USER_SAFE}'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")
    if [[ -n "$USER_ID" ]]; then
      assign_user_psg "$USER_ID" "$CURRENT_USER" || true
    fi
  fi

  # Explicit --users list (works in both interactive and non-interactive runs).
  if [[ -n "$USERS_LIST" ]]; then
    log_info "Assigning SalesManagementUserPsg to --users: $USERS_LIST"
    assign_user_list "$USERS_LIST"
  fi

  # Interactive: ask for more users. Non-interactive runs NEVER prompt and NEVER
  # bulk-assign — the only additional grantees come from the explicit --users flag.
  if [[ "$NON_INTERACTIVE" != "true" ]]; then
    echo ""
    echo "  Assign SalesManagementUserPsg to additional users?"
    read -rp "  Usernames (comma-separated, or Enter to skip): " EXTRA_USERS

    if [[ -n "$EXTRA_USERS" ]]; then
      assign_user_list "$EXTRA_USERS"
    fi
  fi
fi

# ============================================================
# Phase 8: Final Verification
# ============================================================
section "Phase 8: Final Verification"

if [[ -f "$SCRIPT_DIR/verify-all.sh" ]]; then
  # verify-all.sh is a DIAGNOSTIC: it exits nonzero when it reports any FAIL
  # (e.g. stage descriptions absent on a NextStep-only run). That is informational
  # status, NOT a setup failure — swallow it with `|| true` so `set -e` does not
  # abort here and skip the Configuration Summary table below. Capture the exit so
  # the summary can note that verification flagged issues to review.
  VERIFY_EXIT=0
  bash "$SCRIPT_DIR/verify-all.sh" "$ORG_ALIAS" || VERIFY_EXIT=$?
  if [[ "$VERIFY_EXIT" -ne 0 ]]; then
    log_warn "verify-all.sh reported issues (exit $VERIFY_EXIT) — review its output above; setup summary follows."
  fi
else
  log_warn "verify-all.sh not found. Run manually to confirm setup."
fi

# ============================================================
# Phase 8.5: Stage Descriptions Summary Table
# ============================================================
# Display all persisted OpptStageDescription records after setup

if [[ "${STAGE_DESCRIPTIONS_BLOCKED:-}" != "true" ]]; then
  # Query all stage descriptions (global-per-stage; no OpportunityRecordTypeId column)
  SUMMARY_QUERY=$(sf data query --query "SELECT Id, MasterLabel, OpportunityStageApiName, Description FROM OpptStageDescription ORDER BY MasterLabel" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null || echo '{"status":1}')

  SUMMARY_COUNT=$(echo "$SUMMARY_QUERY" | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
  SUMMARY_COUNT="${SUMMARY_COUNT:-0}"

  if [[ "$SUMMARY_COUNT" -gt 0 ]]; then
    echo ""
    section "Stage Descriptions Summary"
    echo ""
    echo "Persisted OpptStageDescription records: $SUMMARY_COUNT"
    echo ""

    # Determine methodology from descriptions (detect MEDDIC/BANT/SPICED keywords)
    FIRST_DESC=$(echo "$SUMMARY_QUERY" | jq -r '.result.records[0].Description // ""' 2>/dev/null)
    METHODOLOGY="Unknown"
    if echo "$FIRST_DESC" | grep -qi "MEDDIC\|Metrics.*Economic Buyer"; then
      METHODOLOGY="MEDDIC"
    elif echo "$FIRST_DESC" | grep -qi "BANT\|Budget.*Authority"; then
      METHODOLOGY="BANT"
    elif echo "$FIRST_DESC" | grep -qi "SPICED\|Situation.*Pain.*Impact"; then
      METHODOLOGY="SPICED"
    fi

    # Print table header — descriptions are global-per-stage, no record-type column
    printf "┌──────────────────────────┬──────────────────────────────────────────────────────────────┬────────────┐\n"
    printf "│ %-24s │ %-60s │ %-10s │\n" "Stage Name" "Description (first 60 chars)" "Methodology"
    printf "├──────────────────────────┼──────────────────────────────────────────────────────────────┼────────────┤\n"

    # Print table rows
    while IFS= read -r DESC_JSON; do
      [[ -z "$DESC_JSON" ]] && continue

      STAGE_NAME=$(echo "$DESC_JSON" | jq -r '.MasterLabel // .OpportunityStageApiName // "N/A"' 2>/dev/null)
      STAGE_DESC=$(echo "$DESC_JSON" | jq -r '.Description // "N/A"' 2>/dev/null)

      # Truncate description to 60 characters
      if [[ ${#STAGE_DESC} -gt 60 ]]; then
        STAGE_DESC_TRUNC="${STAGE_DESC:0:57}..."
      else
        STAGE_DESC_TRUNC="$STAGE_DESC"
      fi

      # Print row
      printf "│ %-24s │ %-60s │ %-10s │\n" "$STAGE_NAME" "$STAGE_DESC_TRUNC" "$METHODOLOGY"

    done < <(echo "$SUMMARY_QUERY" | jq -c '.result.records[]?' 2>/dev/null)

    # Print table footer
    printf "└──────────────────────────┴──────────────────────────────────────────────────────────────┴────────────┘\n"
    echo ""
    echo "Note: Full descriptions are stored in Salesforce. This table shows first 60 characters only."
    echo ""
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                            PIPELINE MANAGEMENT SETUP - CONFIGURATION SUMMARY                        "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Query current org configuration state
log_info "Querying final org configuration state..."
echo ""

# Build configuration summary
printf "┌──────────────────────────────────────────┬─────────────────────┬─────────────────────┬────────────────┐\n"
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Configuration Item" "Before Setup" "After Setup" "Status"
printf "├──────────────────────────────────────────┼─────────────────────┼─────────────────────┼────────────────┤\n"

# Configuration Summary rows compare BEFORE_* (snapshot captured pre-Phase-3)
# vs. AFTER_* (live post-run query). Emit UNCHANGED when they match so
# idempotent reruns don't misreport as CHANGED. See W-23277501.

# Cache one SOAP read so both settings come from the same document
SOAP_SETTINGS_AFTER=$(soap_read "SalesDealAgentSettings" "SalesDealAgent" 2>/dev/null || echo "")

# --- Pipeline Management ---
AFTER_PM=$(soap_extract_bool "$SOAP_SETTINGS_AFTER" "enableDealAgent" 2>/dev/null || echo "false")
PM_BEFORE_LABEL=$([ "$BEFORE_PM" == "true" ] && echo "✅ Enabled" || echo "❌ Not Enabled")
PM_AFTER_LABEL=$([ "$AFTER_PM" == "true" ] && echo "✅ Enabled" || echo "❌ Not Enabled")
if [[ "$BEFORE_PM" == "$AFTER_PM" ]]; then
  PM_STATUS_COL=$([ "$AFTER_PM" == "true" ] && echo "✅ UNCHANGED" || echo "⚠️ NOT ENABLED")
else
  PM_STATUS_COL=$([ "$AFTER_PM" == "true" ] && echo "✅ CHANGED" || echo "⚠️ REVERTED")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Pipeline Management" "$PM_BEFORE_LABEL" "$PM_AFTER_LABEL" "$PM_STATUS_COL"

# --- Autonomous Field Updates ---
AFTER_AUTO=$(soap_extract_bool "$SOAP_SETTINGS_AFTER" "enableDealAgentAutoApproveAllTasks" 2>/dev/null || echo "false")
AUTO_BEFORE_LABEL=$([ "$BEFORE_AUTO" == "true" ] && echo "✅ Enabled" || echo "❌ Disabled")
AUTO_AFTER_LABEL=$([ "$AFTER_AUTO" == "true" ] && echo "✅ Enabled" || echo "❌ Disabled")
if [[ "$BEFORE_AUTO" == "$AFTER_AUTO" ]]; then
  AUTO_STATUS_COL=$([ "$AFTER_AUTO" == "true" ] && echo "✅ UNCHANGED" || echo "⚠️ NOT ENABLED")
else
  AUTO_STATUS_COL=$([ "$AFTER_AUTO" == "true" ] && echo "✅ CHANGED" || echo "⚠️ REVERTED")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Autonomous Field Updates" "$AUTO_BEFORE_LABEL" "$AUTO_AFTER_LABEL" "$AUTO_STATUS_COL"

# --- Agent User ---
AFTER_AGENT_USER=$(sf data query --query "SELECT Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // "Not Created"' 2>/dev/null || echo "Not Created")
AFTER_AGENT_USER=$(sanitize_display "$AFTER_AGENT_USER" 60)
AGENT_BEFORE_LABEL=$([ "$BEFORE_AGENT_USER" != "Not Created" ] && echo "✅ Created" || echo "Not Created")
AGENT_AFTER_LABEL=$([ "$AFTER_AGENT_USER" != "Not Created" ] && echo "✅ Created" || echo "❌ Not Created")
if [[ "$BEFORE_AGENT_USER" == "$AFTER_AGENT_USER" ]]; then
  AGENT_STATUS_COL=$([ "$AFTER_AGENT_USER" != "Not Created" ] && echo "✅ UNCHANGED" || echo "⚠️ NOT CREATED")
else
  AGENT_STATUS_COL=$([ "$AFTER_AGENT_USER" != "Not Created" ] && echo "✅ CREATED" || echo "⚠️ REMOVED")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Agent User (salesmanagementagent...)" "$AGENT_BEFORE_LABEL" "$AGENT_AFTER_LABEL" "$AGENT_STATUS_COL"

# --- PSGs ---
AFTER_PSG_COUNT=$(sf data query --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null || echo "0")
AFTER_PSG_COUNT=$((${AFTER_PSG_COUNT:-0} + 0))
if [[ "$BEFORE_PSG_COUNT" == "$AFTER_PSG_COUNT" ]]; then
  PSG_STATUS_COL=$([ "$AFTER_PSG_COUNT" -ge 2 ] && echo "✅ UNCHANGED" || echo "⚠️ PARTIAL")
else
  PSG_STATUS_COL=$([ "$AFTER_PSG_COUNT" -ge 2 ] && echo "✅ CREATED" || echo "⚠️ PARTIAL")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Permission Set Groups (license)" "$BEFORE_PSG_COUNT PSGs" "$AFTER_PSG_COUNT PSGs" "$PSG_STATUS_COL"

# --- Schedule Flow ---
# Resolve via the shared SourceTemplateId-first resolver (#6) so a freshly deployed
# flow is not misreported as "Not Found" by a fuzzy label query.
AFTER_FLOW_ACTIVE=$(schedule_flow_active "$ORG_ALIAS")
case "$BEFORE_FLOW_ACTIVE" in
  true)  FLOW_BEFORE_LABEL="✅ Active" ;;
  false) FLOW_BEFORE_LABEL="⚠️ Draft" ;;
  *)     FLOW_BEFORE_LABEL="Not Deployed" ;;
esac
case "$AFTER_FLOW_ACTIVE" in
  true)  FLOW_AFTER_LABEL="✅ Active" ;;
  false) FLOW_AFTER_LABEL="⚠️ Draft" ;;
  *)     FLOW_AFTER_LABEL="❌ Not Found" ;;
esac
if [[ "$BEFORE_FLOW_ACTIVE" == "$AFTER_FLOW_ACTIVE" ]]; then
  FLOW_STATUS_COL=$([ "$AFTER_FLOW_ACTIVE" == "true" ] && echo "✅ UNCHANGED" || echo "⚠️ PARTIAL")
else
  FLOW_STATUS_COL=$([ "$AFTER_FLOW_ACTIVE" == "true" ] && echo "✅ CHANGED" || echo "⚠️ PARTIAL")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Schedule Flow (Suggestions)" "$FLOW_BEFORE_LABEL" "$FLOW_AFTER_LABEL" "$FLOW_STATUS_COL"

# --- Stage Descriptions ---
# Same INVALID_TYPE / "0\n0" arithmetic-crash guard as the BEFORE snapshot above:
# if OpptStageDescription is not yet queryable (PM enable still settling), `|| true`
# lets jq's `// 0` default stand instead of appending a second line.
AFTER_STAGE_DESC_COUNT=$(sf data query --query "SELECT Id FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null || true)
AFTER_STAGE_DESC_COUNT=$((${AFTER_STAGE_DESC_COUNT:-0} + 0))
if [[ "$BEFORE_STAGE_DESC_COUNT" == "$AFTER_STAGE_DESC_COUNT" ]]; then
  DESC_STATUS_COL=$([ "$AFTER_STAGE_DESC_COUNT" -gt 0 ] && echo "✅ UNCHANGED" || echo "⚠️ NONE")
else
  DESC_STATUS_COL=$([ "$AFTER_STAGE_DESC_COUNT" -gt 0 ] && echo "✅ CREATED" || echo "⚠️ NONE")
fi
printf "│ %-40s │ %-19s │ %-19s │ %-14s │\n" "Opportunity Stage Descriptions" "$BEFORE_STAGE_DESC_COUNT descriptions" "$AFTER_STAGE_DESC_COUNT descriptions" "$DESC_STATUS_COL"

printf "└──────────────────────────────────────────┴─────────────────────┴─────────────────────┴────────────────┘\n"
echo ""

# Feature Dependency Sequence
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                                    FEATURE DEPENDENCY SEQUENCE                                      "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Phase 1: Prerequisites"
echo "    ├─ SOAP API Enabled"
echo "    ├─ User: 'Use Any API Auth' Permission"
echo "    ├─ Einstein GenAI Enabled"
echo "    └─ Enhanced Notes Enabled"
echo "       │"
echo "       ▼"
echo "  Phase 2: Prerequisite Objects"
echo "    ├─ Enhanced Notes Configuration"
echo "    └─ Opportunity Splits Configuration"
echo "       │"
echo "       ▼"
echo "  Phase 3: Pipeline Management Enablement"
echo "    └─ SalesDealAgentSettings.enableDealAgent = true"
echo "       │"
echo "       ▼"
echo "  Phase 3.5: Autonomous Field Updates (opt-in via --autonomous)"
echo "    ├─ Requires: Phase 3 Complete"
echo "    └─ Sets: enableDealAgentAutoApproveAllTasks = true (only when opted in; else suggestions-only)"
echo "       │"
echo "       ▼"
echo "  Phase 4: Provisioning (async)"
echo "    ├─ Agent User: salesmanagementagentuser@..."
echo "    └─ PSGs: SalesManagementUserPsg, SalesManagementAgentUserPsg"
echo "       │"
echo "       ▼"
echo "  Phase 4c.5: Opportunity Stage Descriptions (only if StageName selected; opt-in via --create-stage-descriptions)"
echo "    ├─ Requires: Phase 4 Complete (OpptStageDescription API accessible)"
echo "    ├─ Runs BEFORE the StageName prompt is deployed/tested (it is the grounding)"
echo "    ├─ Standard Stages: Methodology-specific descriptions"
echo "    └─ Custom Stages: Context-aware recommendations (user confirmation)"
echo "       │"
echo "       ▼"
echo "  Phase 5: Schedule-Triggered Flow"
echo "    └─ Deploy & Activate: Process_Field_Update_Suggestions"
echo "       │"
echo "       ▼"
echo "  Phase 7: User Permissions"
echo "    └─ Assign: SalesManagementUserPsg to users"
echo ""

# Issues Encountered
if [[ ${#SETUP_ISSUES[@]} -gt 0 ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "                                       ISSUES ENCOUNTERED                                           "
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  printf "┌──────────┬────────────────────────────────────────────────────────────┬──────────────────────────────────┐\n"
  printf "│ %-8s │ %-58s │ %-32s │\n" "Severity" "Issue Description" "Resolution"
  printf "├──────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────┤\n"

  for ISSUE in "${SETUP_ISSUES[@]}"; do
    IFS='|' read -r SEVERITY DESC RESOLUTION <<< "$ISSUE"
    printf "│ %-8s │ %-58s │ %-32s │\n" "$SEVERITY" "${DESC:0:58}" "${RESOLUTION:0:32}"
  done

  printf "└──────────┴────────────────────────────────────────────────────────────┴──────────────────────────────────┘\n"
  echo ""
fi

# A tracked "🔴 BLOCKER" means setup did NOT complete — do not report success.
# (track_issue only records; some blocking paths exit inline, but a BLOCKER can also
# be recorded without an inline exit, e.g. bot-activation failure at Phase 4b. This
# gate ensures such a run reports SETUP INCOMPLETE and exits non-zero.)
# NOTE: only "🔴 BLOCKER" is terminal. "🔴 ERROR" is provisional — it marks a state
# the script then attempts to recover from (e.g. SOAP re-provisioning toggle); a
# recovered run must still be allowed to report SETUP COMPLETE.
BLOCKER_COUNT=0
for ISSUE in "${SETUP_ISSUES[@]}"; do
  case "$ISSUE" in
    "🔴 BLOCKER"*) BLOCKER_COUNT=$((BLOCKER_COUNT + 1)) ;;
  esac
done

if [[ "$BLOCKER_COUNT" -gt 0 ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "                                       SETUP INCOMPLETE                                             "
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "  $BLOCKER_COUNT blocking issue(s) (🔴) were recorded above. Setup did not finish successfully."
  echo "  Resolve the issue(s) in the table and re-run: bash setup-all.sh $ORG_ALIAS"
  echo ""
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                                         SETUP COMPLETE                                             "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  - If stage descriptions show FAIL, re-run in 5 minutes (provisioning)"
echo "  - Add notes/emails to opportunities to give the agent data"
echo "  - Wait for daily schedule flow (or check Setup → Flows → run history)"
echo "  - Agent Analytics: Setup → Einstein Feedback and Monitoring"
echo ""
echo "Setup URL: $(sanitize_display "${INSTANCE_URL}/lightning/setup/PipelineManagement/home" 80)"
echo ""
