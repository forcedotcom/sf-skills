#!/usr/bin/env bash
#
# verify-prompt-generation.sh — Verify a field's prompt template generates suggestions
#
# Usage:
#   bash verify-prompt-generation.sh <org-alias> <field> [opportunity-id]
#
# Examples:
#   bash verify-prompt-generation.sh my-org NextStep
#   bash verify-prompt-generation.sh my-org Risk__c 006xx000000ABCD
#
# ADMIN VERIFICATION TOOL: Tests the field-completion prompt template BEHIND A FIELD
# by calling the Einstein /generations API directly. Validates the JSON output
# structure and shows the generated suggestion, helping admins confirm their prompts
# work. The <field> argument mirrors the docs and setup-all.sh's echoed guidance:
# pass the Opportunity field API name (NextStep, StageName, or a custom __c field) —
# NOT a raw template developer name. The field is resolved to the managed/derived
# template name here, identically to setup-all.sh Phase 4e and add-field-suggestion.sh,
# so the namespaced managed template is always queried (a bare, un-namespaced managed
# name returns ENTITY_IS_DELETED). A fully-qualified template dev name is still
# accepted as-is for power users.
#
set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

# ============================================================
# Arguments
# ============================================================
ORG_ALIAS="${1:-}"
FIELD_ARG="${2:-}"
OPP_ID="${3:-}"
# Must carry the leading "v" — the REST path is /services/data/v64.0/... and a
# bare "67.0" produces /services/data/67.0/... which 404s. Same 64.0 API version
# as add-field-suggestion.sh (which also stores it with the leading "v") and
# setup-all.sh (which stores a bare "64.0" and prepends "v" at each call site).
API_VERSION="v64.0"

if [[ -z "$ORG_ALIAS" || -z "$FIELD_ARG" ]]; then
  cat >&2 <<EOF
Usage: $0 <org-alias> <field> [opportunity-id]

ADMIN VERIFICATION: Verifies the prompt template behind an Opportunity field
generates correct field suggestions by calling the Einstein API directly and
validating the JSON response structure.

Arguments:
  org-alias       Salesforce org alias or username
  field           Opportunity field API name (e.g., NextStep, StageName, Risk__c).
                  Resolved to its managed/derived prompt template automatically.
                  A fully-qualified template dev name is also accepted as-is.
  opportunity-id  (Optional) Opportunity ID. If omitted, a test Opportunity
                  owned by the current user is created (and a grounding Note
                  seeded); otherwise falls back to a user-owned open Opportunity
                  (CloseDate within 90 days).

Examples:
  $0 connected-seller-home NextStep
  $0 connected-seller-home Risk__c 006SB00000J73XjYAJ

Output:
  - Calls /einstein/prompt-templates/{template}/generations
  - Validates JSON structure (FieldName, SuggestedNewValue, Reasoning, etc.)
  - Reports success/failure with suggested value preview
EOF
  exit 1
fi

# ------------------------------------------------------------
# Resolve the field to the template dev name the /generations endpoint expects.
# Kept inline (not sourced) and IDENTICAL to setup-all.sh Phase 4e + the
# OOTB_MANAGED_TEMPLATE map / dev-name derivation in add-field-suggestion.sh:
#   - NextStep  -> sales_pipe_mgmt__RecommendNextStepforOpp  (managed)
#   - StageName -> sales_pipe_mgmt__RecommendStageforOpp     (managed picklist template)
#   - custom    -> Recommend<Field w/o __c, alnum-only>forOpp
# A value that is already a template dev name (namespaced, or Recommend...forOpp)
# is used verbatim so power users can still pass a raw template name.
resolve_template_name() {
  local f="$1"
  # Passthrough only well-formed template dev names (anchored regex, not a glob):
  # a namespaced managed name, or Recommend<alnum>forOpp. A permissive glob would
  # accept malformed input like "RecommendZ for Opp" and defer failure to a cryptic
  # API error; the anchor makes bad names fall through to the case map / API instead.
  if [[ "$f" =~ ^sales_pipe_mgmt__[A-Za-z0-9_]+$ || "$f" =~ ^Recommend[A-Za-z0-9]+forOpp$ ]]; then
    printf '%s' "$f"; return 0
  fi
  case "$f" in
    NextStep)  printf 'sales_pipe_mgmt__RecommendNextStepforOpp' ;;
    StageName) printf 'sales_pipe_mgmt__RecommendStageforOpp' ;;
    *)         printf 'Recommend%sforOpp' "$(printf '%s' "$f" | sed 's/__c$//' | sed 's/[^A-Za-z0-9]//g')" ;;
  esac
}
TEMPLATE_DEV_NAME="$(resolve_template_name "$FIELD_ARG")"

# ============================================================
# Helper Functions
# ============================================================
log_info()  { echo "  [....] $*"; }
log_pass()  { echo "  [PASS] $*"; }
log_fail()  { echo "  [FAIL] $*" >&2; }
log_warn()  { echo "  [WARN] $*"; }

die() {
  echo "Error: $*" >&2
  exit 1
}

# Shared test-opp + grounding-note resolution (kept identical to
# flow-debug-and-verify.sh via this one sourced shared library). Defines
# resolve_test_opportunity, which sets OPP_ID and seeds/refreshes the note.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared/test-opp.sh"

# ============================================================
# Setup
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pipeline Management Prompt Template Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Org:         $ORG_ALIAS"
echo "Field:       $FIELD_ARG"
echo "Template:    $TEMPLATE_DEV_NAME"
echo "Opportunity: ${OPP_ID:-<create test opp>}"
echo ""

# ============================================================
# Get Access Token
# ============================================================
log_info "Authenticating to org..."

# Use sf org auth show-access-token for CLI v2.x (hides tokens in org display)
ACCESS_TOKEN=$(sf org auth show-access-token --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.accessToken // empty')
INSTANCE_URL=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.instanceUrl // empty')

if [[ -z "$ACCESS_TOKEN" || -z "$INSTANCE_URL" ]]; then
  die "Could not retrieve access token or instance URL. Verify org alias '$ORG_ALIAS' exists."
fi

log_pass "Connected to $INSTANCE_URL"
echo ""

# ============================================================
# Resolve the target Opportunity (create a user-owned test opp when omitted)
# ============================================================
# Pipeline Inspection is owner-scoped, so a suggestion on an opp owned by someone
# else is invisible to the admin verifying. Prefer creating a fresh test opp owned
# by the current user; fall back to a user-owned open opp; skip gracefully if none.
if [[ -z "$OPP_ID" ]]; then
  log_info "No opportunity given — resolving a user-owned test opportunity..."

  # resolve_test_opportunity (shared lib) reuses/creates the stable [PM-TEST] opp
  # owned by the current user, falls back to a user-owned open opp, and
  # seeds/refreshes the grounding note on whichever resolved — the SAME opp + note
  # the flow-verification path uses (both scripts share this one lib).
  resolve_test_opportunity

  if [[ -z "$OPP_ID" ]]; then
    log_warn "No eligible opportunity found for the current user."
    echo "         To verify: create an open Opportunity owned by you with CloseDate within 90 days,"
    echo "         then re-run: $0 $ORG_ALIAS $FIELD_ARG <opportunity-id>"
    echo ""
    log_info "Skipping output verification — no opportunity available"
    exit 0
  fi
  echo ""
fi

# ============================================================
# Resolve Template Developer Name to API Name/ID
# ============================================================
log_info "Looking up prompt template '$TEMPLATE_DEV_NAME'..."

# The sf CLI wraps the REST API and handles name resolution
# We'll use sf api request which accepts the developer name directly
echo ""

# ============================================================
# Call Einstein Prompt Template API
# ============================================================
log_info "Calling Einstein /generations API..."

RESPONSE_FILE=$(mktemp)

# Use sf api request which handles authentication and name resolution.
# GUARD the call with `|| CLI_EXIT=$?`: under `set -e` an unguarded non-zero exit
# would abort the script immediately, making the `$?` capture and the error block
# below dead code. Capturing the exit status keeps the diagnostic branch live.
CLI_EXIT=0
sf api request rest "/services/data/${API_VERSION}/einstein/prompt-templates/${TEMPLATE_DEV_NAME}/generations" \
  --method POST \
  --target-org "$ORG_ALIAS" \
  --body "{\"isPreview\":false,\"inputParams\":{\"valueMap\":{\"Input:Opportunity\":{\"value\":{\"id\":\"${OPP_ID}\"}}}},\"additionalConfig\":{\"numGenerations\":1,\"temperature\":0,\"applicationName\":\"PromptTemplateGenerationsInvocable\"}}" \
  > "$RESPONSE_FILE" 2>&1 || CLI_EXIT=$?

# Check the CLI exit status BEFORE filtering. Two reasons:
#   1. Under `set -e`, an unguarded sed failure below would abort the script
#      before this check runs, turning the diagnostic branch into dead code.
#   2. On failure the raw response usually holds a non-JSON CLI error that the
#      JSON-only filter would strip — show it verbatim instead of an empty file.
if [[ "$CLI_EXIT" -ne 0 ]]; then
  log_fail "API call failed (sf CLI exit code: $CLI_EXIT)"
  echo ""
  echo "Response:"
  cat "$RESPONSE_FILE"
  rm -f "$RESPONSE_FILE"
  exit 1
fi

# Filter out CLI warnings from response (keep only lines starting with { or [)
sed -n '/^[{\[]/,/^[}\]]/p' "$RESPONSE_FILE" > "${RESPONSE_FILE}.clean"
mv "${RESPONSE_FILE}.clean" "$RESPONSE_FILE"

# Check if response file is empty or contains error
if [[ ! -s "$RESPONSE_FILE" ]]; then
  log_fail "Empty response from API"
  rm -f "$RESPONSE_FILE"
  exit 1
fi

# Check if response contains error
if jq -e '.[0].errorCode' "$RESPONSE_FILE" >/dev/null 2>&1; then
  ERROR_CODE=$(jq -r '.[0].errorCode' "$RESPONSE_FILE")
  ERROR_MSG=$(jq -r '.[0].message' "$RESPONSE_FILE")
  log_fail "API returned error: $ERROR_CODE - $ERROR_MSG"
  rm -f "$RESPONSE_FILE"
  exit 1
fi

log_pass "API call succeeded"
echo ""

# ============================================================
# Extract and Validate JSON
# ============================================================
log_info "Parsing response..."

# Extract the generation text (which itself is JSON)
GENERATION_TEXT=$(cat "$RESPONSE_FILE" | jq -r '.generations[0].text // empty')

if [[ -z "$GENERATION_TEXT" ]]; then
  log_fail "No generation text in response"
  echo ""
  echo "Full Response:"
  cat "$RESPONSE_FILE" | jq '.'
  rm -f "$RESPONSE_FILE"
  exit 1
fi

# Parse the inner JSON
PARSED_JSON=$(echo "$GENERATION_TEXT" | jq '.' 2>/dev/null || echo "")

if [[ -z "$PARSED_JSON" ]]; then
  log_fail "Generation text is not valid JSON"
  echo ""
  echo "Generation Text:"
  echo "$GENERATION_TEXT"
  rm -f "$RESPONSE_FILE"
  exit 1
fi

log_pass "JSON parsing successful"
echo ""

# ============================================================
# Validate Required Fields
# ============================================================
log_info "Validating JSON structure..."

REQUIRED_FIELDS=("FieldName" "SuggestedNewValue" "OriginalValue" "Reasoning" "DueDate" "Sources")
MISSING_FIELDS=()

for field in "${REQUIRED_FIELDS[@]}"; do
  if ! echo "$PARSED_JSON" | jq -e ".$field" >/dev/null 2>&1; then
    MISSING_FIELDS+=("$field")
  fi
done

if [[ ${#MISSING_FIELDS[@]} -gt 0 ]]; then
  log_fail "Missing required fields: ${MISSING_FIELDS[*]}"
  echo ""
  echo "Generated JSON:"
  echo "$PARSED_JSON" | jq '.'
  rm -f "$RESPONSE_FILE"
  exit 1
fi

log_pass "All required fields present"

# Validate Sources is an array
SOURCES_COUNT=$(echo "$PARSED_JSON" | jq '.Sources | length // 0')
if [[ "$SOURCES_COUNT" -eq 0 ]]; then
  log_warn "Sources array is empty (no citations)"
else
  log_pass "Sources array contains $SOURCES_COUNT citation(s)"
fi

echo ""

# ============================================================
# Display Results
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ TEST PASSED - AI Suggestion Generated"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

FIELD_NAME=$(echo "$PARSED_JSON" | jq -r '.FieldName')
SUGGESTED_VALUE=$(echo "$PARSED_JSON" | jq -r '.SuggestedNewValue')
REASONING=$(echo "$PARSED_JSON" | jq -r '.Reasoning')
DUE_DATE=$(echo "$PARSED_JSON" | jq -r '.DueDate')

echo "Field:           $FIELD_NAME"
echo "Suggested Value: $SUGGESTED_VALUE"
echo "Reasoning:       $REASONING"
echo "Due Date:        $DUE_DATE"
echo "Sources:         $SOURCES_COUNT citation(s)"
echo ""

# Character length check
CHAR_COUNT=${#SUGGESTED_VALUE}
echo "Length Check:    $CHAR_COUNT characters"

if [[ $CHAR_COUNT -gt 255 ]]; then
  log_warn "Suggested value exceeds 255 characters (may be truncated on field write)"
fi

echo ""
echo "Full JSON:"
echo "$PARSED_JSON" | jq '.'
echo ""

# Save response for inspection
SAVE_PATH="/tmp/prompt-test-${TEMPLATE_DEV_NAME}-$(date +%Y%m%d-%H%M%S).json"
echo "$PARSED_JSON" | jq '.' > "$SAVE_PATH"
echo "💾 Full response saved to: $SAVE_PATH"

rm -f "$RESPONSE_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
