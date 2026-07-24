#!/usr/bin/env bash
# shared/stage-descriptions.sh
# ---------------------------------------------------------------------------
# OpptStageDescription creation, extracted from setup-all.sh so it can run in
# Block A (Call 1) BEFORE the StageName prompt is deployed / activated / tested,
# rather than as a trailing phase. Stage descriptions are the grounding source
# for StageName suggestions, so they must exist before the StageName prompt is
# verified.
#
# Sourced by setup-all.sh. Relies on the parent script's helpers (log_*, section,
# confirm, sanitize_dev_name, track_issue) — bash resolves these at call time, so
# they only need to be defined before run_stage_descriptions is CALLED (they are).
#
# Inputs (globals set by the caller): ORG_ALIAS, NON_INTERACTIVE,
#   CREATE_STAGE_DESCRIPTIONS, STAGENAME_SELECTED, SCRIPT_DIR.
# Output (global for the Phase 8.5 summary): STAGE_DESCRIPTIONS_BLOCKED.
# ---------------------------------------------------------------------------

# Generate a context-aware description for custom stages
# Args: $1=stage_label, $2=methodology_name, $3=record_type_name (optional)
generate_custom_stage_desc() {
  local stage_label="$1" meth_name="$2" rt_name="${3:-}"
  local stage_lower context_hint meth_hint

  stage_lower=$(printf '%s' "$stage_label" | tr '[:upper:]' '[:lower:]')

  if [[ $stage_lower =~ (technical|tech|solution|demo|poc|pilot|trial) ]]; then
    context_hint="Technical validation stage. Activities: solution demonstration, technical requirements review, feasibility assessment, stakeholder technical approval."
  elif [[ $stage_lower =~ (legal|contract|compliance|security|review|audit) ]]; then
    context_hint="Legal/compliance review stage. Activities: contract review, legal approval, security assessment, compliance validation, risk evaluation."
  elif [[ $stage_lower =~ (executive|c-level|leadership|sponsor|approval) ]]; then
    context_hint="Executive approval stage. Activities: executive presentation, C-level buy-in, budget approval, strategic alignment validation."
  elif [[ $stage_lower =~ (procurement|purchasing|vendor|sourcing) ]]; then
    context_hint="Procurement process stage. Activities: vendor evaluation, procurement approval, purchase order creation, budget allocation."
  elif [[ $stage_lower =~ (implementation|onboard|kickoff|setup|deploy) ]]; then
    context_hint="Implementation planning stage. Activities: project kickoff, resource allocation, timeline planning, onboarding preparation."
  elif [[ $stage_lower =~ (finance|financial|budget|pricing|cost) ]]; then
    context_hint="Financial validation stage. Activities: budget confirmation, ROI analysis, cost-benefit review, financial approval."
  else
    context_hint="Custom sales stage. Activities: progress opportunity through this specific phase, document key milestones and decisions."
  fi

  case "$meth_name" in
    MEDDIC)
      meth_hint="Apply MEDDIC framework: Validate Metrics (quantified impact), engage Economic Buyer, confirm Decision Criteria met, understand Decision Process steps, address Pain points, enable Champion support."
      ;;
    BANT)
      meth_hint="Apply BANT criteria: Confirm Budget available, validate Authority engaged, ensure Need remains urgent, verify Timeline realistic for this stage."
      ;;
    SPICED)
      meth_hint="Apply SPICED framework: Understand Situation context, quantify Pain severity, identify all Impacted stakeholders, validate Critical Event timing, navigate Decision process."
      ;;
    *)
      meth_hint="Document progress and next steps aligned to your sales methodology."
      ;;
  esac

  if [[ -n "$rt_name" ]]; then
    printf '%s' "Custom stage for $rt_name: $stage_label. $context_hint $meth_hint Entry: Previous stage criteria met. Exit: Stage-specific requirements completed to advance."
  else
    printf '%s' "Custom stage: $stage_label. $context_hint $meth_hint Entry: Previous stage criteria met. Exit: Stage-specific requirements completed to advance."
  fi
}

# run_stage_descriptions — relocated Phase 6 body; self-gates on STAGENAME_SELECTED.
run_stage_descriptions() {
  section "Phase 4c.5: Stage Descriptions (before StageName prompt)"

# OpptStageDescription requires PM fully enabled (Tooling API only)
DESC_QUERY=$(sf data query --query "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null || echo '{"status":1}')

# Detect inaccessibility (PM not fully provisioned yet)
if echo "$DESC_QUERY" | grep -qi "INVALID_TYPE\|NOT_FOUND\|sObject type.*not supported"; then
  log_warn "OpptStageDescription not accessible yet (PM provisioning may still be in progress)"
  echo "  Stage descriptions can be configured after provisioning completes."
  echo "  Re-run: bash setup-all.sh $ORG_ALIAS (in 2-5 minutes)"
  DESC_COUNT="0"
  STAGE_DESCRIPTIONS_BLOCKED="true"
else
  DESC_COUNT=$(echo "$DESC_QUERY" | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
  DESC_COUNT="${DESC_COUNT:-0}"
fi

if [[ "${STAGE_DESCRIPTIONS_BLOCKED:-}" == "true" ]]; then
  : # Already reported - skip Phase 6 entirely
elif [[ "$STAGENAME_SELECTED" != "true" ]]; then
  # StageName was not among the up-front-selected fields, so stage descriptions
  # are irrelevant this run — they only feed StageName suggestions. Skip the
  # whole gate rather than ask an irrelevant question (3-phase requirement:
  # stage descriptions asked ONLY when StageName is selected).
  log_pass "Stage descriptions: not needed (StageName not selected)"
elif [[ "$DESC_COUNT" -gt 0 ]]; then
  log_pass "Stage descriptions: $DESC_COUNT configured"
else
  # No stage descriptions found, and StageName IS selected.
  # CONSENT GATE (#11): stage descriptions are ONLY needed for StageName suggestions and
  # creating them may overwrite descriptions the org intentionally left blank. Creation is
  # therefore opt-in: gated on --create-stage-descriptions (non-interactive) or an explicit
  # interactive confirmation. We NEVER silently default to MEDDIC in non-interactive mode.
  log_info "No stage descriptions configured (StageName is selected — needed for its suggestions)."

  WANT_STAGE_DESCRIPTIONS=false
  if [[ "$CREATE_STAGE_DESCRIPTIONS" == "true" ]]; then
    WANT_STAGE_DESCRIPTIONS=true
  elif [[ "$NON_INTERACTIVE" != "true" ]]; then
    if confirm "Create stage descriptions now? (only needed if you want StageName suggestions)"; then
      WANT_STAGE_DESCRIPTIONS=true
    fi
  fi

  if [[ "$WANT_STAGE_DESCRIPTIONS" != "true" ]]; then
    log_pass "Stage descriptions: skipped (not requested)"
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
      echo "    To create them, re-run with --create-stage-descriptions"
    fi
    METHODOLOGY="4"  # sentinel: skip the creation branch below
  elif [[ "$NON_INTERACTIVE" == "true" ]]; then
    # Consent given via flag, but no TTY to choose a methodology — default to MEDDIC and say so.
    echo "  Creating stage descriptions with MEDDIC methodology (default for --create-stage-descriptions)..."
    METHODOLOGY="1"
  else
    echo "  Which sales methodology?"
    echo "    1) MEDDIC    2) BANT    3) SPICED    4) Skip"
    read -rp "  Choice (1-4): " METHODOLOGY
  fi

  if [[ "$METHODOLOGY" =~ ^[1-3]$ ]]; then
    # Map methodology choice to file name
    case "$METHODOLOGY" in
      1) METH_NAME="MEDDIC"; METH_FILE="meddic.txt" ;;
      2) METH_NAME="BANT"; METH_FILE="bant.txt" ;;
      3) METH_NAME="SPICED"; METH_FILE="spiced.txt" ;;
    esac

    # Load stage descriptions from asset file
    DESCRIPTIONS_FILE="$SCRIPT_DIR/../assets/stage-descriptions/$METH_FILE"
    if [[ ! -f "$DESCRIPTIONS_FILE" ]]; then
      log_fail "Stage description file not found: $DESCRIPTIONS_FILE"
      log_warn "Skipping stage description creation."
    else
      log_info "Creating stage descriptions using $METH_NAME methodology..."

      # Define the 11 standard OOTB stages (for custom stage detection)
      STANDARD_STAGES=(
        "Prospecting"
        "Qualification"
        "Needs Analysis"
        "Value Proposition"
        "Id. Decision Makers"
        "Perception Analysis"
        "Proposal/Price Quote"
        "Negotiation/Review"
        "Closed Won"
        "Closed Lost"
        "Most Likely"
      )

      # Count active Opportunity record types to decide which log path to take.
      # OpptStageDescription is global-per-stage regardless — we only use this count
      # for the log message, not to fan out the write loop.
      RT_QUERY=$(sf data query --query "SELECT COUNT() FROM RecordType WHERE SObjectType = 'Opportunity' AND IsActive = true" --target-org "$ORG_ALIAS" --json 2>/dev/null)
      RT_COUNT=$(echo "$RT_QUERY" | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
      RT_COUNT="${RT_COUNT:-0}"

      if [[ "$RT_COUNT" -eq 0 ]]; then
        log_warn "No Opportunity record types found. Using global stage picklist values."
        # Fall back to global picklist query (no record type context)
        STAGE_QUERY=$(sf data query --query "SELECT MasterLabel, ApiName FROM OpportunityStage WHERE IsActive=true ORDER BY SortOrder" --target-org "$ORG_ALIAS" --json 2>/dev/null)

        # Batch pre-fetch existing stage descriptions (avoid N+1 queries)
        EXISTING_DESCS=$(sf data query -q "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null || echo '{"result":{"records":[]}}')

        CREATED=0
        FAILED=0            # real API create/update failures only
        NO_DESC=0           # methodology file had no line for this stage (not an API error)
        CUSTOM_SKIPPED=0

        while IFS= read -r STAGE_JSON; do
          [[ -z "$STAGE_JSON" ]] && continue
          STAGE_LABEL=$(echo "$STAGE_JSON" | jq -r '.MasterLabel // empty' 2>/dev/null)
          STAGE_API=$(echo "$STAGE_JSON" | jq -r '.ApiName // empty' 2>/dev/null)
          [[ -z "$STAGE_LABEL" || -z "$STAGE_API" ]] && continue

          # Check if this is a standard stage
          IS_STANDARD=false
          for STD_STAGE in "${STANDARD_STAGES[@]}"; do
            if [[ "$STAGE_LABEL" == "$STD_STAGE" ]]; then
              IS_STANDARD=true
              break
            fi
          done

          if [[ "$IS_STANDARD" == "false" ]]; then
            # Custom stage detected
            echo ""
            log_info "Custom stage detected: $STAGE_LABEL"

            RECOMMENDED_DESC=$(generate_custom_stage_desc "$STAGE_LABEL" "$METH_NAME")

            if [[ ! -t 0 ]]; then
              # Non-interactive: skip custom stages with warning
              log_warn "Non-interactive mode: skipping custom stage '$STAGE_LABEL'"
              CUSTOM_SKIPPED=$((CUSTOM_SKIPPED + 1))
              continue
            fi

            echo "  Recommended description:"
            echo "    $RECOMMENDED_DESC"
            echo ""
            read -rp "  Use this description? (y/n/edit): " CUSTOM_CHOICE

            case "$CUSTOM_CHOICE" in
              y|Y|yes|Yes|YES)
                DESC="$RECOMMENDED_DESC"
                ;;
              e|E|edit|Edit|EDIT)
                echo "  Enter custom description (single line):"
                read -r DESC
                [[ -z "$DESC" ]] && { log_warn "Empty description - skipping stage"; continue; }
                ;;
              *)
                log_warn "Skipping custom stage: $STAGE_LABEL"
                CUSTOM_SKIPPED=$((CUSTOM_SKIPPED + 1))
                continue
                ;;
            esac
          else
            # Standard stage - load from file
            # Literal match on the first pipe-delimited field. A stage label can
            # contain regex metacharacters (the OOTB "Id. Decision Makers" has a
            # '.'), so grep "^LABEL|" would treat them as patterns and mis-match.
            DESC=$(awk -F'|' -v s="$STAGE_LABEL" '$1==s{sub(/^[^|]*\|/,""); print; exit}' "$DESCRIPTIONS_FILE")
            if [[ -z "$DESC" ]]; then
              log_info "No ${METH_NAME} description defined for standard stage '$STAGE_LABEL' — skipping (not an error)."
              NO_DESC=$((NO_DESC + 1))
              continue
            fi
          fi

          # Create/update OpptStageDescription record. Use the sanitizer so labels like
          # "Id. Decision Makers" yield a VALID DeveloperName (not "Id__Decision_Makers").
          DEV_NAME=$(sanitize_dev_name "$STAGE_LABEL")

          # Check if description already exists for this stage
          EXISTING_ID=$(printf '%s' "$EXISTING_DESCS" | jq -r --arg stage "$STAGE_API" '.result.records[] | select(.OpportunityStageApiName == $stage) | .Id' 2>/dev/null | head -1)
          EXISTING_ID="${EXISTING_ID:-}"

          # Idempotency: for custom stages with existing descriptions, offer to keep
          if [[ "$IS_STANDARD" == "false" && -n "$EXISTING_ID" && -t 0 ]]; then
            CURRENT_DESC=$(printf '%s' "$EXISTING_DESCS" | jq -r --arg id "$EXISTING_ID" '.result.records[] | select(.Id == $id) | .Description // ""' 2>/dev/null || echo "")
            if [[ -n "$CURRENT_DESC" ]]; then
              echo "    Current: ${CURRENT_DESC:0:100}"
              read -rp "    Keep current description? (y/n): " KEEP_CHOICE
              if [[ "$KEEP_CHOICE" =~ ^[yY] ]]; then
                CREATED=$((CREATED + 1))
                continue
              fi
            fi
          fi

          # Escape for SOQL/CLI: double single-quotes, strip backticks and shell metacharacters
          DESC_ESCAPED=$(printf '%s' "$DESC" | sed "s/'/''/g" | tr -d '`' | sed 's/\$/\\$/g')

          if [[ -n "$EXISTING_ID" ]]; then
            # Update existing record — capture stderr+json so a failure reports WHY.
            SD_RESULT=$(sf data update record --sobject OpptStageDescription --record-id "$EXISTING_ID" \
              --values "Description='${DESC_ESCAPED}'" \
              --target-org "$ORG_ALIAS" --use-tooling-api --json 2>&1 || true)
            if echo "$SD_RESULT" | jq -e '.result.id // .status == 0' >/dev/null 2>&1; then
              CREATED=$((CREATED + 1))
            else
              SD_ERR=$(echo "$SD_RESULT" | jq -r '.message // .result.message // empty' 2>/dev/null || echo "")
              log_fail "Failed to update '$STAGE_LABEL' (DeveloperName='$DEV_NAME'): ${SD_ERR:-$SD_RESULT}"
              FAILED=$((FAILED + 1))
            fi
          else
            # Create new record — capture stderr+json so a failure reports WHY.
            SD_RESULT=$(sf data create record --sobject OpptStageDescription \
              --values "DeveloperName='${DEV_NAME}' MasterLabel='${STAGE_LABEL}' OpportunityStageApiName='${STAGE_API}' Description='${DESC_ESCAPED}'" \
              --target-org "$ORG_ALIAS" --use-tooling-api --json 2>&1 || true)
            if echo "$SD_RESULT" | jq -e '.result.id // empty' >/dev/null 2>&1; then
              CREATED=$((CREATED + 1))
            else
              SD_ERR=$(echo "$SD_RESULT" | jq -r '.message // .result.message // empty' 2>/dev/null || echo "")
              log_fail "Failed to create '$STAGE_LABEL' (DeveloperName='$DEV_NAME'): ${SD_ERR:-$SD_RESULT}"
              FAILED=$((FAILED + 1))
            fi
          fi
        done < <(echo "$STAGE_QUERY" | jq -c '.result.records[]?' 2>/dev/null)

        # Summary — report each category distinctly so real API failures are not
        # conflated with stages that simply had no methodology line (#8).
        if [[ $FAILED -gt 0 ]]; then
          log_fail "Stage descriptions: $CREATED created/updated, $FAILED FAILED (see errors above), $NO_DESC no-description, $CUSTOM_SKIPPED custom skipped"
        elif [[ $CREATED -gt 0 ]]; then
          log_pass "Stage descriptions: $CREATED created/updated, $NO_DESC no-description, $CUSTOM_SKIPPED custom skipped"
        else
          log_warn "Stage descriptions: none created ($NO_DESC no-description, $CUSTOM_SKIPPED custom skipped)"
        fi

      else
        # Record types exist. OpptStageDescription is GLOBAL-PER-STAGE (keyed only by
        # OpportunityStageApiName — there is no OpportunityRecordTypeId column on the
        # object), so each active stage is written exactly ONCE regardless of how many
        # Opportunity record types exist. Descriptions are NOT partitioned by record
        # type, so we write against the global active-stage picklist directly. (W-23356857)
        log_info "Found $RT_COUNT opportunity record type(s). Writing global-per-stage descriptions (one per active stage)..."

        TOTAL_CREATED=0
        TOTAL_FAILED=0
        TOTAL_NO_DESC=0
        TOTAL_CUSTOM_SKIPPED=0

        # Batch pre-fetch ALL existing stage descriptions once (avoid redundant queries per stage)
        EXISTING_DESCS=$(sf data query -q "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null || echo '{"result":{"records":[]}}')

        # OpptStageDescription is global-per-stage: iterate the global active-stage picklist
        # once and write one description per stage (no per-record-type partitioning).
        RT_STAGES_QUERY=$(sf data query --query "SELECT MasterLabel, ApiName FROM OpportunityStage WHERE IsActive=true ORDER BY SortOrder" --target-org "$ORG_ALIAS" --json 2>/dev/null)

        while IFS= read -r STAGE_JSON; do
          [[ -z "$STAGE_JSON" ]] && continue
          STAGE_LABEL=$(echo "$STAGE_JSON" | jq -r '.MasterLabel // empty' 2>/dev/null)
          STAGE_API=$(echo "$STAGE_JSON" | jq -r '.ApiName // empty' 2>/dev/null)
          [[ -z "$STAGE_LABEL" || -z "$STAGE_API" ]] && continue

          # Check if this is a standard stage
          IS_STANDARD=false
          for STD_STAGE in "${STANDARD_STAGES[@]}"; do
            if [[ "$STAGE_LABEL" == "$STD_STAGE" ]]; then
              IS_STANDARD=true
              break
            fi
          done

          if [[ "$IS_STANDARD" == "false" ]]; then
            # Custom stage detected
            log_info "  Custom stage: $STAGE_LABEL"

            RECOMMENDED_DESC=$(generate_custom_stage_desc "$STAGE_LABEL" "$METH_NAME")

            if [[ ! -t 0 ]]; then
              # Non-interactive: skip custom stages with warning
              log_warn "  Non-interactive mode: skipping custom stage '$STAGE_LABEL'"
              TOTAL_CUSTOM_SKIPPED=$((TOTAL_CUSTOM_SKIPPED + 1))
              continue
            fi

            echo "    Recommended description:"
            echo "      $RECOMMENDED_DESC"
            echo ""
            read -rp "    Use this description? (y/n/edit): " CUSTOM_CHOICE

            case "$CUSTOM_CHOICE" in
              y|Y|yes|Yes|YES)
                DESC="$RECOMMENDED_DESC"
                ;;
              e|E|edit|Edit|EDIT)
                echo "    Enter custom description (single line):"
                read -r DESC
                [[ -z "$DESC" ]] && { log_warn "  Empty description - skipping stage"; continue; }
                ;;
              *)
                log_warn "  Skipping custom stage: $STAGE_LABEL"
                TOTAL_CUSTOM_SKIPPED=$((TOTAL_CUSTOM_SKIPPED + 1))
                continue
                ;;
            esac
          else
            # Standard stage - load from file
            # Literal match on the first pipe-delimited field. A stage label can
            # contain regex metacharacters (the OOTB "Id. Decision Makers" has a
            # '.'), so grep "^LABEL|" would treat them as patterns and mis-match.
            DESC=$(awk -F'|' -v s="$STAGE_LABEL" '$1==s{sub(/^[^|]*\|/,""); print; exit}' "$DESCRIPTIONS_FILE")
            if [[ -z "$DESC" ]]; then
              log_info "  No ${METH_NAME} description defined for standard stage '$STAGE_LABEL' — skipping (not an error)."
              TOTAL_NO_DESC=$((TOTAL_NO_DESC + 1))
              continue
            fi
          fi

          # Create/update the global OpptStageDescription record (keyed by stage only).
          # Sanitizer guards against invalid DeveloperNames (e.g. double underscores).
          DEV_NAME=$(sanitize_dev_name "$STAGE_LABEL")

          # Check if a description already exists for this stage.
          EXISTING_ID=$(printf '%s' "$EXISTING_DESCS" | jq -r --arg stage "$STAGE_API" '.result.records[] | select(.OpportunityStageApiName == $stage) | .Id' 2>/dev/null | head -1)
          EXISTING_ID="${EXISTING_ID:-}"

          # Idempotency: for custom stages with existing descriptions, offer to keep
          if [[ "$IS_STANDARD" == "false" && -n "$EXISTING_ID" && -t 0 ]]; then
            CURRENT_DESC=$(printf '%s' "$EXISTING_DESCS" | jq -r --arg id "$EXISTING_ID" '.result.records[] | select(.Id == $id) | .Description // ""' 2>/dev/null || echo "")
            if [[ -n "$CURRENT_DESC" ]]; then
              echo "    Current: ${CURRENT_DESC:0:100}"
              read -rp "    Keep current description? (y/n): " KEEP_CHOICE
              if [[ "$KEEP_CHOICE" =~ ^[yY] ]]; then
                TOTAL_CREATED=$((TOTAL_CREATED + 1))
                continue
              fi
            fi
          fi

          # Escape for SOQL/CLI: double single-quotes, strip backticks and shell metacharacters
          DESC_ESCAPED=$(printf '%s' "$DESC" | sed "s/'/''/g" | tr -d '`' | sed 's/\$/\\$/g')

          if [[ -n "$EXISTING_ID" ]]; then
            # Update existing record — capture the error on failure.
            SD_RESULT=$(sf data update record --sobject OpptStageDescription --record-id "$EXISTING_ID" \
              --values "Description='${DESC_ESCAPED}'" \
              --target-org "$ORG_ALIAS" --use-tooling-api --json 2>&1 || true)
            if echo "$SD_RESULT" | jq -e '.result.id // .status == 0' >/dev/null 2>&1; then
              TOTAL_CREATED=$((TOTAL_CREATED + 1))
            else
              SD_ERR=$(echo "$SD_RESULT" | jq -r '.message // .result.message // empty' 2>/dev/null || echo "")
              log_fail "  Failed to update '$STAGE_LABEL' (DeveloperName='$DEV_NAME'): ${SD_ERR:-$SD_RESULT}"
              TOTAL_FAILED=$((TOTAL_FAILED + 1))
            fi
          else
            # Create new global record — capture the error on failure.
            SD_RESULT=$(sf data create record --sobject OpptStageDescription \
              --values "DeveloperName='${DEV_NAME}' MasterLabel='${STAGE_LABEL}' OpportunityStageApiName='${STAGE_API}' Description='${DESC_ESCAPED}'" \
              --target-org "$ORG_ALIAS" --use-tooling-api --json 2>&1 || true)
            if echo "$SD_RESULT" | jq -e '.result.id // empty' >/dev/null 2>&1; then
              TOTAL_CREATED=$((TOTAL_CREATED + 1))
            else
              SD_ERR=$(echo "$SD_RESULT" | jq -r '.message // .result.message // empty' 2>/dev/null || echo "")
              log_fail "  Failed to create '$STAGE_LABEL' (DeveloperName='$DEV_NAME'): ${SD_ERR:-$SD_RESULT}"
              TOTAL_FAILED=$((TOTAL_FAILED + 1))
            fi
          fi
        done < <(echo "$RT_STAGES_QUERY" | jq -c '.result.records[]?' 2>/dev/null)

        # Overall summary — real API failures reported distinctly from no-description skips.
        echo ""
        if [[ $TOTAL_FAILED -gt 0 ]]; then
          log_fail "Stage descriptions: $TOTAL_CREATED created/updated, $TOTAL_FAILED FAILED (see errors above), ${TOTAL_NO_DESC:-0} no-description, $TOTAL_CUSTOM_SKIPPED custom skipped"
        elif [[ $TOTAL_CREATED -gt 0 ]]; then
          log_pass "Stage descriptions: $TOTAL_CREATED created/updated, ${TOTAL_NO_DESC:-0} no-description, $TOTAL_CUSTOM_SKIPPED custom skipped"
        else
          log_warn "Stage descriptions: none created (${TOTAL_NO_DESC:-0} no-description, $TOTAL_CUSTOM_SKIPPED custom skipped)"
        fi
      fi
    fi
  else
    log_warn "Skipped. Stage suggestions will NOT work without descriptions."
  fi
fi
}
