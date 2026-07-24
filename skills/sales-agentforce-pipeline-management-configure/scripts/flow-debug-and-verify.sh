#!/usr/bin/env bash
#
# flow-debug-and-verify.sh — Verify Pipeline Management flow is working correctly
#
# Usage:
#   bash flow-debug-and-verify.sh <org-alias> [opportunity-id]           # flow-debug-start: pick opp + print Debug URL
#   bash flow-debug-and-verify.sh <org-alias> <opportunity-id> verify    # verify: after the debug run
#
# ADMIN VERIFICATION TOOL: Verifies that Pipeline Management is configured
# correctly and generating field suggestions.
#
# The suggestion flow (Process_Field_Update_Suggestions) is a SCHEDULED
# record-triggered flow. Its $Record global is bound ONLY when the flow runs —
# by the platform scheduler at cron time, or by Flow Builder's Debug runner
# (which asks you to pick the record). Starting the interview manually from Apex
# leaves $Record null and the flow silently no-ops, so this tool drives it as a
# guided MANUAL step split into two phases:
#
#   FLOW DEBUG START  (default)  — picks an eligible opportunity and prints the
#                        flow's Debug URL. You then run Debug against that
#                        opportunity in the browser (leave rollback mode
#                        UNCHECKED).
#   VERIFY  ("verify") — run after the debug run finishes; confirms the flow
#                        reached its action (agent user on the Opportunity Team)
#                        and polls for the generated AiGenActionItem suggestions.
#
# The wait between phases happens in the DRIVER (the human or the agent invoking
# this), not inside the script — so an agent can relay the URL, wait in the
# conversation for you to finish the debug run, then invoke the verify phase.
# When run in an interactive terminal, FLOW DEBUG START additionally offers to
# pause and chain straight into VERIFY for convenience.
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
OPP_ID="${2:-}"
MODE="${3:-flow-debug-start}"   # flow-debug-start (default) | verify
BASELINE_ARG="${4:-}"           # verify: suggestion count captured BEFORE the debug run
FLOW_API_NAME="Process_Field_Update_Suggestions"

if [[ -z "$ORG_ALIAS" ]]; then
  cat >&2 <<EOF
Usage:
  $0 <org-alias> [opportunity-id]           # FLOW DEBUG START: pick opp + print the Debug URL
  $0 <org-alias> <opportunity-id> verify    # VERIFY: run after the debug finishes

ADMIN VERIFICATION: Verifies the Pipeline Management suggestion flow works by
guiding you through a manual Flow Builder Debug run (the only on-demand path
that binds a real \$Record on a scheduled record-triggered flow), then checks
the resulting Opportunity Team membership and AiGenActionItem suggestions.

Arguments:
  org-alias       Salesforce org alias or username
  opportunity-id  (Optional in flow-debug-start) Specific opportunity to test.
                  If omitted, a test opportunity owned by the current user is
                  created (and a grounding Note seeded); otherwise falls back to
                  a user-owned open opportunity.
                  REQUIRED in verify (use the ID that flow-debug-start reported).

Two-phase flow:
  1. FLOW DEBUG START prints the flow's Debug URL and the opportunity to select.
  2. You open the URL, click Debug, pick that opportunity as the trigger
     record, leave 'rollback mode' UNCHECKED, and Run.
  3. VERIFY confirms the agent user joined the Opportunity Team and polls for
     the generated suggestion(s).

Example:
  $0 connected-seller-home
  # ...run the debug in the browser against the reported opportunity...
  $0 connected-seller-home 006SB00000J73XjYAJ verify
EOF
  exit 1
fi

# ============================================================
# Helper Functions
# ============================================================
log_info()  { echo "  [....] $*"; }
log_pass()  { echo "  [PASS] $*"; }
log_fail()  { echo "  [FAIL] $*" >&2; }
log_warn()  { echo "  [WARN] $*"; }
log_try()   { echo "  [TRY ] $*"; }

die() {
  echo "Error: $*" >&2
  exit 1
}

# Shared test-opp + grounding-note resolution (kept identical to
# verify-prompt-generation.sh via this one sourced shared library). Defines
# resolve_test_opportunity, which sets OPP_ID and seeds/refreshes the note.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared/test-opp.sh"

# ============================================================
# VERIFY phase — check the flow reached its action + polled suggestions
# ============================================================
run_verify() {
  local opp_id="$1"
  local opp_name="$2"
  local note_count="$3"
  local baseline_count="$4"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  VERIFY — checking the debug run's results"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # The flow adds the agent user to the Opportunity Team BEFORE calling the
  # suggestion action, within the same synchronous debug run. So once the debug
  # run has finished, that membership must exist — its absence means the flow
  # no-op'd (ineligible opp, missing agent user, inactive Bot, or rollback mode
  # left on) rather than a timing issue.
  log_info "Confirming the agent user joined the Opportunity Team..."

  local agent_user_id
  agent_user_id=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%' LIMIT 1" \
    --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')

  if [[ -z "$agent_user_id" ]]; then
    die "Agent user (salesmanagementagentuser) not found — Pipeline Management may not be fully provisioned."
  fi

  local agent_otm
  agent_otm=$(sf data query -q "SELECT TeamMemberRole, OpportunityAccessLevel FROM OpportunityTeamMember WHERE OpportunityId='$opp_id' AND UserId='$agent_user_id' LIMIT 1" \
    --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0] // empty')

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Results"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  if [[ -z "$agent_otm" ]]; then
    log_fail "Agent user is NOT on the Opportunity Team for $opp_id."
    echo ""
    echo "  The debug run did not reach the suggestion action. Rule out real gaps:"
    echo "    - Did you select this opportunity ($opp_id) as the trigger record?"
    echo "    - Was 'rollback mode' left UNCHECKED? (rollback discards the DML)"
    echo "    - Opportunity eligible? (IsClosed=false, CloseDate within 90 days)"
    echo "    - Agent user holds SalesManagementAgentUserPsg?"
    echo "    - Active BotDefinition/BotVersion for the Sales agent?"
    echo "    - Bot AgentTemplate matches the flow's SalesManagementAgentTemplate"
    echo "      (SalesMgmt__SalesAgent vs __NGASalesAgent) — a mismatch makes the"
    echo "      flow exit BEFORE the Opportunity Team step."
    echo ""
    die "Flow did not queue opportunity $opp_id for suggestion generation."
  fi

  local otm_role otm_access
  otm_role=$(echo "$agent_otm" | jq -r '.TeamMemberRole // "?"')
  otm_access=$(echo "$agent_otm" | jq -r '.OpportunityAccessLevel // "?"')
  log_pass "Agent user is on the Opportunity Team (role: $otm_role, access: $otm_access)"
  log_pass "Flow reached its suggestion action for opportunity $opp_id."
  echo ""

  # The action writes AiGenActionItem asynchronously. On-org timing: 0 rows at
  # 90s, suggestions landing ~165s — so poll to ~4 min before concluding failure
  # (a short poll is the #1 false negative). Compare this opportunity's
  # FIELD_UPDATE count against the baseline captured BEFORE the debug run.
  log_info "Polling for generated suggestion(s) (up to ~4 min)..."

  local suggestion_found=0 current_count
  for _ in $(seq 1 16); do
    sleep 15
    # `|| echo` keeps a transient sf/network blip (ECONNRESET is a known flake on
    # this org) from aborting the whole verify under `set -o pipefail`.
    current_count=$(sf data query -q "SELECT COUNT() FROM AiGenActionItem WHERE ParentId='$opp_id' AND Type='FIELD_UPDATE'" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.totalSize // 0' || echo "$baseline_count")
    if [[ "$current_count" -gt "$baseline_count" ]]; then
      local delta=$((current_count - baseline_count))
      log_pass "Generated $delta new suggestion(s) for $opp_id (AiGenActionItem)."
      suggestion_found=1
      break
    fi
  done

  if [[ "$suggestion_found" -eq 0 ]]; then
    if [[ "$note_count" -gt 0 ]]; then
      log_warn "No new suggestions after ~4 min, though this opp has $note_count note(s)."
      log_warn "Generation can lag; check Pipeline Inspection on $opp_name shortly. If it"
      log_warn "stays empty, verify the field prompt templates are active and grounded."
    else
      log_info "No suggestions after ~4 min. Expected here — this opp has no notes to"
      log_info "ground on. Link a ContentNote and re-run to see grounded suggestions."
    fi
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Verification Complete"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Test Opportunity:  $opp_id ($opp_name)"
}

# ============================================================
# Setup
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pipeline Management Flow Debug Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Org:  $ORG_ALIAS"
echo "Flow: $FLOW_API_NAME"
echo "Mode: $MODE"
echo ""

if [[ "$MODE" != "flow-debug-start" && "$MODE" != "verify" ]]; then
  die "Unknown mode '$MODE'. Use 'flow-debug-start' (default) or 'verify'."
fi

if [[ "$MODE" == "verify" && -z "$OPP_ID" ]]; then
  die "verify mode requires an opportunity id: $0 <org-alias> <opportunity-id> verify [baseline]"
fi

# ============================================================
# Resolve / validate the target opportunity
# ============================================================
if [[ -z "$OPP_ID" ]]; then
  # Pipeline Inspection is owner-scoped, so a suggestion on an opp owned by someone
  # else is invisible to the admin verifying. resolve_test_opportunity (shared lib)
  # reuses/creates the stable [PM-TEST] opp owned by the current user, falls back to
  # a user-owned open opp, and seeds/refreshes the grounding note on whichever
  # resolved — the SAME opp + note the prompt-verification path uses.
  log_info "No opportunity given — resolving a user-owned test opportunity..."

  resolve_test_opportunity

  if [[ -z "$OPP_ID" ]]; then
    log_warn "No eligible opportunity found for the current user."
    echo "         To verify: create an open Opportunity owned by you with CloseDate within 90 days,"
    echo "         then re-run: $0 $ORG_ALIAS <opportunity-id>"
    echo ""
    log_info "Skipping output verification — no opportunity available"
    exit 0
  fi
else
  log_info "Using opportunity: $OPP_ID"

  # In flow-debug-start mode, warn if it doesn't meet flow criteria (verify mode
  # trusts the id flow-debug-start already vetted).
  if [[ "$MODE" != "verify" ]]; then
    IS_ELIGIBLE=$(sf data query -q "SELECT Id FROM Opportunity WHERE Id='$OPP_ID' AND IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')

    if [[ -z "$IS_ELIGIBLE" ]]; then
      log_warn "Opportunity $OPP_ID may not meet flow criteria (must be open with CloseDate within 90 days)"
    fi
  fi
fi

# Opportunity details (name for messaging; note count feeds the suggestion check)
OPP_DETAILS=$(sf data query -q "SELECT Name, StageName, CloseDate FROM Opportunity WHERE Id='$OPP_ID'" \
  --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0] // empty')
if [[ -z "$OPP_DETAILS" || "$OPP_DETAILS" == "null" ]]; then
  die "Opportunity '$OPP_ID' not found in org '$ORG_ALIAS'. Check the id (a missing opp would otherwise look like a flow no-op)."
fi
OPP_NAME=$(echo "$OPP_DETAILS" | jq -r '.Name')
OPP_STAGE=$(echo "$OPP_DETAILS" | jq -r '.StageName')
OPP_CLOSE=$(echo "$OPP_DETAILS" | jq -r '.CloseDate')

NOTE_COUNT=$(sf data query -q "SELECT COUNT() FROM ContentDocumentLink WHERE LinkedEntityId='$OPP_ID'" \
  --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.totalSize // 0')

# The baseline must be the suggestion count BEFORE the debug run. flow-debug-start
# captures it here (pre-run) and prints it into the verify command; verify reuses
# that value. Re-querying in verify would fold the run's own output into the
# baseline, so the delta poll could never detect it — a guaranteed false negative.
# Scoped to THIS opp + FIELD_UPDATE so a concurrent run elsewhere can't false-positive.
if [[ "$MODE" == "verify" ]]; then
  if [[ -n "$BASELINE_ARG" ]]; then
    BASELINE_COUNT="$BASELINE_ARG"
  else
    # Standalone verify with no baseline: fall back to absolute detection (any
    # FIELD_UPDATE item counts). Weaker than the delta, but never a false negative.
    log_warn "No baseline passed; using absolute count (any FIELD_UPDATE suggestion = pass)."
    BASELINE_COUNT=0
  fi
  run_verify "$OPP_ID" "$OPP_NAME" "$NOTE_COUNT" "$BASELINE_COUNT"
  exit 0
fi

BASELINE_COUNT=$(sf data query -q "SELECT COUNT() FROM AiGenActionItem WHERE ParentId='$OPP_ID' AND Type='FIELD_UPDATE'" \
  --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.totalSize // 0')

# ============================================================
# FLOW DEBUG START mode: resolve the flow's Debug URL and hand off
# ============================================================
echo ""
echo "Test Opportunity:"
echo "  ID:         $OPP_ID"
echo "  Name:       $OPP_NAME"
echo "  Stage:      $OPP_STAGE"
echo "  Close Date: $OPP_CLOSE"
echo "  Notes:      $NOTE_COUNT"
echo ""

if [[ "$NOTE_COUNT" -eq 0 ]]; then
  log_warn "No ContentNotes linked to this opportunity - suggestions may be empty"
fi

# Instance URL for the Debug link.
INSTANCE_URL=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.instanceUrl // empty')
[[ -z "$INSTANCE_URL" ]] && die "Could not resolve instance URL for org '$ORG_ALIAS' — is it authenticated?"
INSTANCE_URL="${INSTANCE_URL%/}"

log_info "Locating flow '$FLOW_API_NAME'..."

# FlowDefinitionView has no 'ActiveVersion' relationship — use the scalar
# ActiveVersionId, then read VersionNumber from the Flow tooling object.
FLOW_DEF=$(sf data query -q "SELECT Id, ActiveVersionId, ProcessType, TriggerType FROM FlowDefinitionView WHERE ApiName='$FLOW_API_NAME' AND IsActive=true" \
  --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0] // empty')

if [[ -z "$FLOW_DEF" || "$FLOW_DEF" == "null" ]]; then
  die "Flow '$FLOW_API_NAME' not found or not active"
fi

FLOW_VERSION_ID=$(echo "$FLOW_DEF" | jq -r '.ActiveVersionId')
FLOW_PROCESS_TYPE=$(echo "$FLOW_DEF" | jq -r '.ProcessType')
FLOW_TRIGGER_TYPE=$(echo "$FLOW_DEF" | jq -r '.TriggerType // "None"')

FLOW_VERSION_NUM=$(sf data query -q "SELECT VersionNumber FROM Flow WHERE Id='$FLOW_VERSION_ID'" \
  --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.records[0].VersionNumber // "?"')

log_pass "Flow found (version $FLOW_VERSION_NUM, type: $FLOW_PROCESS_TYPE, trigger: $FLOW_TRIGGER_TYPE)"

# Flow Builder opens on the active version by its FlowVersion (301) Id. From
# there the Debug button lets you pick the record to bind as $Record.
DEBUG_URL="${INSTANCE_URL}/builder_platform_interaction/flowBuilder.app?flowId=${FLOW_VERSION_ID}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MANUAL STEP — Debug the flow in your browser"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  This is a scheduled record-triggered flow, so \$Record is only bound"
echo "  when you run it. Flow Builder's Debug runner lets you pick the record."
echo ""
echo "  1. Open the flow (active version $FLOW_VERSION_NUM):"
echo ""
echo "     $DEBUG_URL"
echo ""
echo "  2. Click the Debug button (top-right in Flow Builder)."
echo "  3. In 'Debug the flow' → for the record that triggers the flow, select:"
echo ""
echo "        $OPP_NAME"
echo "        ($OPP_ID)"
echo ""
echo "  4. Leave 'Run the Flow in rollback mode' UNCHECKED so the DML persists,"
echo "     then click Run."
echo "  5. Wait for the debug panel to show the run finished."
echo ""
echo "  When the debug run is finished, verify the results with (the trailing"
echo "  $BASELINE_COUNT is the pre-run suggestion baseline — keep it so the delta is exact):"
echo ""
echo "     bash $0 $ORG_ALIAS $OPP_ID verify $BASELINE_COUNT"
echo ""

# Best-effort: open the URL in the default browser for convenience. Requires you
# to already be logged into this org in that browser, else it lands on login.
if command -v open >/dev/null 2>&1; then
  open "$DEBUG_URL" >/dev/null 2>&1 || true
fi

# Convenience for a human at an interactive terminal: offer to pause here and
# chain into VERIFY. Gate on stdin being a real TTY (`-t 0`), NOT merely on
# /dev/tty existing — an agent driving this via a tool call has no interactive
# stdin, so it skips this and calls the verify command above once the user
# confirms in the conversation (no hang).
if [[ -t 0 ]]; then
  printf '  Press ENTER once the debug run has finished to verify now (or Ctrl-C to verify later): '
  if read -r _; then
    run_verify "$OPP_ID" "$OPP_NAME" "$NOTE_COUNT" "$BASELINE_COUNT"
  fi
fi
