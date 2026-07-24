#!/usr/bin/env bash
#
# test-opp.sh — shared test-opportunity + grounding-note resolution for the two
# admin verification scripts (flow-debug-and-verify.sh and
# verify-prompt-generation.sh).
#
# The skill invokes those two scripts SEPARATELY (prompt path vs. flow path), but
# both must converge on ONE shared test Opportunity and ONE shared grounding Note
# so a suggestion generated on one path is visible on the other and duplicates
# never pile up. Keeping this logic in a single sourced lib is what guarantees the
# two stay byte-for-byte identical (they drifted before this was extracted).
#
# Contract:
#   - Sourced, not executed. Relies on the CALLER having defined:
#       * $ORG_ALIAS                 (target org)
#       * log_info / log_pass / log_warn   (helpers — resolved at call time)
#   - Honors optional env var $PM_GROUNDING_NOTE: an agent/LLM-composed grounding
#     note body. When set it is what grounds the AI suggestion; absent, a generic
#     literal is used so standalone runs still work (a contextless note grounds on
#     nothing and returns an empty suggestion, making a working setup look broken).
#   - resolve_test_opportunity sets the global OPP_ID (empty if none could be
#     resolved) and seeds/refreshes the grounding note on it.
#
# NOTE: no `set -euo pipefail` here — the caller owns shell options. Every sf/jq
# pipeline is guarded with `|| echo ""` so a transient CLI/network blip can't trip
# the caller's `set -e` and abort the whole verification run.

# Canonical name for the reusable test opp. The `[PM-TEST]` prefix makes every
# opp this tooling creates findable in one place (Opportunity WHERE Name LIKE
# '[PM-TEST]%') so they can be spotted/cleaned up and never confused with real
# pipeline in Flow Builder's Debug record picker or Pipeline Inspection.
PM_TEST_OPP_NAME='[PM-TEST] Test Pipeline Verification Opp'
# Title of the grounding note this tooling manages (used to find/refresh it).
PM_GROUNDING_NOTE_TITLE='PM grounding note'
# base64 of "Test grounding data for Pipeline Management verification." — the
# fallback body when the driver passes no PM_GROUNDING_NOTE.
PM_GROUNDING_NOTE_FALLBACK_B64='VGVzdCBncm91bmRpbmcgZGF0YSBmb3IgUGlwZWxpbmUgTWFuYWdlbWVudCB2ZXJpZmljYXRpb24u'

# Resolve the shared test opportunity, setting the global OPP_ID.
#   1. Reuse the stable [PM-TEST] opp if one exists (and roll its CloseDate +30d
#      so it stays flow-eligible over repeated sessions).
#   2. Else create it (owner = current user; Pipeline Inspection is owner-scoped,
#      so a suggestion on someone else's opp is invisible to the admin verifying).
#   3. Else fall back to any user-owned open opp.
#   4. Seed or refresh the grounding note against whichever opp resolved.
resolve_test_opportunity() {
  local current_user_id close_date stage_label opp_values

  current_user_id=$(NO_COLOR=1 FORCE_COLOR=0 sf org display user --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty' 2>/dev/null || echo "")

  # macOS/BSD `date -v+30d`; GNU `date -d '+30 days'`. Empty => skip create/roll.
  close_date=$(date -v+30d '+%Y-%m-%d' 2>/dev/null || date -d '+30 days' '+%Y-%m-%d' 2>/dev/null || echo "")

  # 1) Reuse the stable, prefixed test opp if it exists.
  if [[ -n "$current_user_id" ]]; then
    OPP_ID=$(sf data query -q "SELECT Id FROM Opportunity WHERE Name='${PM_TEST_OPP_NAME}' AND OwnerId='${current_user_id}' AND IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90 ORDER BY CreatedDate DESC LIMIT 1" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty' || echo "")
    if [[ -n "$OPP_ID" ]]; then
      log_pass "Reusing existing test opportunity: $OPP_ID ($PM_TEST_OPP_NAME)"
      # Roll CloseDate forward so the reused opp keeps meeting the flow's
      # "CloseDate within 90 days" eligibility filter across sessions.
      if [[ -n "$close_date" ]]; then
        if sf data update record --sobject Opportunity --record-id "$OPP_ID" \
          --values "CloseDate='${close_date}'" --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null; then
          log_info "Rolled CloseDate to ${close_date}"
        else
          log_warn "Could not roll CloseDate on $OPP_ID (continuing)"
        fi
      fi
    fi
  fi

  # 2) Create the prefixed test opp if none exists yet.
  if [[ -z "${OPP_ID:-}" && -n "$close_date" ]]; then
    stage_label=$(sf data query -q "SELECT MasterLabel FROM OpportunityStage WHERE IsActive=true AND IsClosed=false ORDER BY SortOrder LIMIT 1" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].MasterLabel // empty')
    # Skip creation if the stage label contains a single quote — it would break
    # --values parsing.
    if [[ -n "$stage_label" ]] && [[ "$stage_label" != *"'"* ]]; then
      opp_values="Name='${PM_TEST_OPP_NAME}' StageName='${stage_label}' CloseDate='${close_date}'"
      [[ -n "$current_user_id" ]] && opp_values="${opp_values} OwnerId='${current_user_id}'"
      OPP_ID=$(sf data create record --sobject Opportunity --values "$opp_values" \
        --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty' || echo "")
      [[ -n "$OPP_ID" ]] && log_pass "Created test opportunity: $OPP_ID ($PM_TEST_OPP_NAME)"
    fi
  fi

  # 3) Fall back to a user-owned open opp (owner filter only when user is known).
  if [[ -z "${OPP_ID:-}" ]]; then
    if [[ -n "$current_user_id" ]]; then
      OPP_ID=$(sf data query -q "SELECT Id FROM Opportunity WHERE OwnerId='${current_user_id}' AND IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90 ORDER BY LastModifiedDate DESC LIMIT 1" \
        --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty' || echo "")
    else
      OPP_ID=$(sf data query -q "SELECT Id FROM Opportunity WHERE IsClosed=false AND CloseDate>=TODAY AND CloseDate<=NEXT_N_DAYS:90 ORDER BY LastModifiedDate DESC LIMIT 1" \
        --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty' || echo "")
    fi
    [[ -n "$OPP_ID" ]] && log_pass "Using opportunity: $OPP_ID"
  fi

  # 4) Seed / refresh the grounding note against the FINALLY-resolved opp so a
  #    freshly created opp, a reused opp, AND a fallback opp all end up grounded.
  [[ -n "${OPP_ID:-}" ]] && seed_grounding_note "$OPP_ID"
}

# Ensure the shared grounding note exists (and matches the driver's note) on the
# given opp. Idempotent: seeds when absent, refreshes only when the composed note
# differs from what's stored, and otherwise leaves the existing note untouched.
seed_grounding_note() {
  local opp_id="$1"
  local note_b64 existing_doc_id existing_content note_id

  # base64 line-wraps at 76 cols on macOS/BSD; `tr -d '\n'` keeps it single-line
  # (GNU's `-w0` isn't portable).
  if [[ -n "${PM_GROUNDING_NOTE:-}" ]]; then
    note_b64=$(printf '%s' "$PM_GROUNDING_NOTE" | base64 | tr -d '\n')
  else
    note_b64="$PM_GROUNDING_NOTE_FALLBACK_B64"
  fi

  # Find a grounding note this tooling previously seeded on the opp. ContentNote's
  # own 069-prefix Id IS the ContentDocumentId, so the link's ContentDocumentId is
  # the note's Id. `|| echo ""` keeps a query blip from tripping the caller's set -e.
  existing_doc_id=$(sf data query -q "SELECT ContentDocumentId FROM ContentDocumentLink WHERE LinkedEntityId='${opp_id}' AND ContentDocument.Title='${PM_GROUNDING_NOTE_TITLE}' ORDER BY ContentDocument.CreatedDate DESC LIMIT 1" \
    --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].ContentDocumentId // empty' || echo "")

  if [[ -n "$existing_doc_id" ]]; then
    # A grounding note already exists. Refresh it ONLY when the driver passed a
    # note whose content differs from what's stored — otherwise reuse it so we
    # don't churn the note (and its ContentVersion history) every run.
    # ContentNote.Content is a base64Url BLOB field: SOQL returns the REST *path*
    # to the blob, not the bytes, so we fetch the decoded body via that endpoint
    # and compare it to the raw PM_GROUNDING_NOTE plaintext (not base64).
    if [[ -n "${PM_GROUNDING_NOTE:-}" ]]; then
      existing_content=$(sf api request rest "/services/data/v64.0/sobjects/ContentNote/${existing_doc_id}/Content" \
        --target-org "$ORG_ALIAS" 2>/dev/null || echo "")
      if [[ -n "$existing_content" && "$existing_content" != "$PM_GROUNDING_NOTE" ]]; then
        # ContentNote.Content isn't reliably updatable in place (it's
        # ContentVersion-backed), so replace by delete + recreate: dropping the
        # ContentDocument cascades its link and versions.
        sf data delete record --sobject ContentDocument --record-id "$existing_doc_id" \
          --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null || true
        existing_doc_id=""
        log_info "Grounding note changed — refreshing it on $opp_id"
      else
        log_info "Reusing existing grounding note on $opp_id"
      fi
    else
      log_info "Reusing existing grounding note on $opp_id"
    fi
  fi

  # Seed when none exists (fresh opp) or the stale one was just dropped above.
  if [[ -z "$existing_doc_id" ]]; then
    note_id=$(sf data create record --sobject ContentNote \
      --values "Title='${PM_GROUNDING_NOTE_TITLE}' Content='${note_b64}'" \
      --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.id // empty' || echo "")
    if [[ -n "$note_id" ]]; then
      sf data create record --sobject ContentDocumentLink \
        --values "ContentDocumentId='${note_id}' LinkedEntityId='${opp_id}' ShareType='V'" \
        --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null || true
      log_info "Seeded ContentNote for grounding on test opportunity"
    else
      log_warn "Could not seed grounding ContentNote (Notes may not be enabled on this org) — suggestion quality may be lower"
    fi
  fi
}
