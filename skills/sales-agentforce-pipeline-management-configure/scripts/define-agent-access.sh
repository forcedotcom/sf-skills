#!/bin/bash

# Define Agent Access for the Pipeline Management Sales Agent (W-23242378)
#
# PROBLEM this solves:
#   When the Pipeline Management Sales Agent (a BotDefinition matched by
#   AgentTemplate — SalesMgmt__NGASalesAgent / SalesMgmt__SalesAgent) is created,
#   it is NOT added to the "Agent Access" section of any permission set that
#   human users hold. Users assigned the managed PSG `SalesManagementUserPsg`
#   therefore cannot launch or chat with the agent, even though the agent is
#   active and the PSG is assigned.
#
# WHY it can't be done directly on the PSG:
#   `SalesManagementUserPsg` is a MANAGED permission set group — its Agent Access
#   cannot be edited. Agent Access (SetupEntityAccess with SetupEntityType=
#   'BotDefinition') can only live on a CUSTOM permission set (License=None).
#
# THE FIX (mirrors the manual Setup UI flow):
#   1. Create a CUSTOM permission set `Sales_Agent_Access` (License=None).
#   2. Add the agent to its Agent Access: insert SetupEntityAccess
#      (ParentId=<permset Id>, SetupEntityId=<BotDefinition Id>). Standard Data API.
#      SetupEntityType is derived — do NOT set it on insert. Requires API v64.0+.
#   3. Add the custom permset to `SalesManagementUserPsg` via
#      PermissionSetGroupComponent (Tooling API object — needs --use-tooling-api).
#   4. Confirm the PSG recalculates (the component insert triggers async recalc;
#      poll Status until 'Updated'). => Agent becomes available to all users
#      holding SalesManagementUserPsg.
#
# The BotDefinition is detected by AgentTemplate (via shared/agent-detection.sh),
# NOT by a hardcoded DeveloperName, so it matches whatever local name the agent
# was published with (SalesAgent, Sale_Agent, etc.) — the same logic the
# scheduled flow uses.
#
# This script is idempotent (query-then-skip; SetupEntityAccess has no Update)
# and safe to re-run. It must run AFTER the agent (BotDefinition) exists.
#
# Usage: ./define-agent-access.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Shared PM bot detection (AgentTemplate-based). Provides PM_AGENT_TEMPLATES_SOQL
# and pm_bot_developer_name().
source "$SCRIPT_DIR/shared/agent-detection.sh"
# Shared PSG recalculation status reader (psg_status).
source "$SCRIPT_DIR/shared/psg.sh"

ORG_ALIAS="${1:-}"

# --- Helpers (mirror setup-all.sh conventions) ---
log_pass() { echo "  [PASS] $1"; }
log_warn() { echo "  [WARN] $1"; }
log_fail() { echo "  [FAIL] $1"; }
log_info() { echo "  [....] $1"; }
log_try()  { echo "  [TRY ] $1"; }

if [[ -z "$ORG_ALIAS" ]]; then
  echo "Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

# Validate org alias (prevent shell injection via metacharacters), matching
# the pattern used by setup-all.sh and verify-all.sh.
if [[ ! "$ORG_ALIAS" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
  echo "ERROR: Invalid org alias. Only alphanumeric, dots, hyphens, and underscores allowed (must start with alphanumeric)."
  exit 1
fi

# Preflight: this script parses every CLI response with jq and calls the sf CLI,
# and SetupEntityAccess for BotDefinition needs the sf CLI's default API (v64.0+,
# shipped by sf CLI v2.x). Fail fast with an actionable message instead of a
# cryptic mid-run error.
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: 'jq' is required but not installed. Install it (e.g. 'brew install jq') and re-run."
  exit 1
fi
if ! command -v sf >/dev/null 2>&1; then
  echo "ERROR: Salesforce CLI ('sf') is required but not installed. Install the v2.x 'sf' CLI and re-run."
  exit 1
fi
SF_MAJOR=$(sf --version 2>/dev/null | grep -oE '@salesforce/cli/[0-9]+' | grep -oE '[0-9]+$' || echo "")
if [[ -n "$SF_MAJOR" && "$SF_MAJOR" -lt 2 ]]; then
  echo "ERROR: Salesforce CLI v2.x or newer is required (found major version ${SF_MAJOR})."
  echo "       Agent Access (SetupEntityAccess for BotDefinition) needs API v64.0+, which ships with sf CLI v2.x."
  exit 1
fi

# Configurable identifiers
ACCESS_PS_NAME="Sales_Agent_Access"
ACCESS_PS_LABEL="Sales Agent Access"
USER_PSG_NAME="SalesManagementUserPsg"
AGENT_PSG_NAME="SalesManagementAgentUserPsg"

echo "=== Define Agent Access for Pipeline Management Sales Agent ==="
echo ""

# ------------------------------------------------------------
# Step 0: The agent must exist first (BotDefinition Id is runtime-only).
# Detect it by AgentTemplate, matching the scheduled flow's own lookup — not by
# a hardcoded DeveloperName. Uses a TWO-STEP query: first find the BotDefinition
# by AgentTemplate (no subquery), then separately confirm it has an Active
# BotVersion. The single-query `Id IN (SELECT ... FROM BotVersion WHERE Status =
# 'Active')` form was removed in de77d520 because that correlated subquery hangs
# 60+ seconds on some orgs.
# ------------------------------------------------------------
BOT_DEF=$(sf data query \
  --query "SELECT Id, DeveloperName FROM BotDefinition WHERE AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL}) ORDER BY LastModifiedDate DESC LIMIT 1" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0] // empty' 2>/dev/null || echo "")

BOT_DEF_ID=$(echo "$BOT_DEF" | jq -r '.Id // empty' 2>/dev/null || echo "")
BOT_DEF_NAME=$(echo "$BOT_DEF" | jq -r '.DeveloperName // empty' 2>/dev/null || echo "")

# BOT_DEF_ID is interpolated into later SOQL; reject anything that is not a
# valid Salesforce record Id (15 or 18 char alphanumeric).
if [[ -n "$BOT_DEF_ID" && ! "$BOT_DEF_ID" =~ ^[a-zA-Z0-9]{15,18}$ ]]; then
  log_fail "Invalid BotDefinition ID format: $BOT_DEF_ID"
  exit 1
fi

if [[ -z "$BOT_DEF_ID" ]]; then
  log_warn "No Pipeline Management BotDefinition found — cannot define Agent Access yet."
  echo "    Agent Access can only be defined after the agent exists and has an Active version."
  echo "    Create the agent first (./create-agent.sh $ORG_ALIAS), then re-run this script."
  exit 0
fi

# Separately confirm the bot has an Active BotVersion (flat query on BotVersion,
# no correlated subquery). Agent Access on an inactive bot has no runtime effect.
ACTIVE_VERSION_COUNT=$(sf data query \
  --query "SELECT COUNT() FROM BotVersion WHERE BotDefinitionId = '${BOT_DEF_ID}' AND Status = 'Active'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
ACTIVE_VERSION_COUNT="${ACTIVE_VERSION_COUNT:-0}"

if [[ "$ACTIVE_VERSION_COUNT" -lt 1 ]]; then
  log_warn "Agent BotDefinition '${BOT_DEF_NAME:-<unknown>}' has no Active BotVersion — cannot define Agent Access yet."
  echo "    Activate the agent version first, then re-run this script."
  exit 0
fi
log_pass "Found active agent BotDefinition: ${BOT_DEF_NAME:-<unknown>} ($BOT_DEF_ID)"

# ------------------------------------------------------------
# Step 1: Create the custom permission set (idempotent)
# PermissionSet is createable via the STANDARD Data API (NOT Tooling).
# Omitting License leaves LicenseId null (= "None"), which is required so the
# permset can be added as a component of the managed PSG.
# ------------------------------------------------------------
PS_ID=$(sf data query \
  --query "SELECT Id FROM PermissionSet WHERE Name = '${ACCESS_PS_NAME}'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

if [[ -n "$PS_ID" ]]; then
  log_pass "Custom permission set '${ACCESS_PS_NAME}' already exists ($PS_ID)"
else
  log_try "Creating custom permission set '${ACCESS_PS_NAME}' (License=None)..."
  CREATE_PS=$(sf data create record \
    --sobject PermissionSet \
    --values "Name='${ACCESS_PS_NAME}' Label='${ACCESS_PS_LABEL}'" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null || echo '{"status":1}')

  PS_ID=$(echo "$CREATE_PS" | jq -r '.result.id // empty' 2>/dev/null || echo "")
  if [[ -z "$PS_ID" ]]; then
    # Re-query in case of a race / partial output. A concurrent create or a
    # not-yet-visible write can make the row lag briefly, so retry with a short
    # backoff rather than giving up after a single lookup.
    for _ in $(seq 1 5); do
      PS_ID=$(sf data query \
        --query "SELECT Id FROM PermissionSet WHERE Name = '${ACCESS_PS_NAME}'" \
        --target-org "$ORG_ALIAS" \
        --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")
      [[ -n "$PS_ID" ]] && break
      sleep 2
    done
  fi

  if [[ -z "$PS_ID" ]]; then
    log_fail "Could not create permission set '${ACCESS_PS_NAME}'"
    echo "$CREATE_PS" | jq -r '.message // .result.message // empty' 2>/dev/null || true
    exit 1
  fi
  log_pass "Created custom permission set '${ACCESS_PS_NAME}' ($PS_ID)"
fi

# ------------------------------------------------------------
# Step 2: Add the agent to Agent Access on that permission set
# SetupEntityAccess: Create/Delete/Query only (NO Update). SetupEntityType is
# derived from SetupEntityId — do NOT set it on insert. BotDefinition is a valid
# SetupEntityType only at API v64.0+ (sf CLI default is well above this).
# ------------------------------------------------------------
EXISTING_ACCESS=$(sf data query \
  --query "SELECT Id FROM SetupEntityAccess WHERE ParentId = '${PS_ID}' AND SetupEntityId = '${BOT_DEF_ID}'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

if [[ -n "$EXISTING_ACCESS" ]]; then
  log_pass "Agent Access already granted to '${ACCESS_PS_NAME}' ($EXISTING_ACCESS)"
else
  log_try "Granting Agent Access (SetupEntityAccess) to '${ACCESS_PS_NAME}'..."
  CREATE_ACCESS=$(sf data create record \
    --sobject SetupEntityAccess \
    --values "ParentId='${PS_ID}' SetupEntityId='${BOT_DEF_ID}'" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null || echo '{"status":1}')

  # The query-then-create above is non-atomic: a concurrent run can insert the
  # same grant between our SELECT and INSERT, so tolerate DUPLICATE_VALUE — the
  # grant exists either way, which is the outcome we want (idempotent).
  if echo "$CREATE_ACCESS" | jq -e '.result.id // empty' >/dev/null 2>&1; then
    log_pass "Agent Access granted (agent added to '${ACCESS_PS_NAME}')"
  elif echo "$CREATE_ACCESS" | jq -r '.message // .result.message // ""' 2>/dev/null | grep -qi "DUPLICATE_VALUE"; then
    log_pass "Agent Access already granted (duplicate insert ignored)"
  else
    ACCESS_ERR=$(echo "$CREATE_ACCESS" | jq -r '.message // .result.message // "unknown"' 2>/dev/null || echo "unknown")
    log_fail "Could not grant Agent Access: $ACCESS_ERR"
    echo "    SetupEntityAccess requires a CUSTOM permission set and API v64.0+."
    exit 1
  fi
fi

# ------------------------------------------------------------
# Step 3: Add the custom permset as a component of the managed PSG
# PermissionSetGroupComponent is a TOOLING API object — must use --use-tooling-api.
# ------------------------------------------------------------
PSG_ID=$(sf data query \
  --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = '${USER_PSG_NAME}'" \
  --target-org "$ORG_ALIAS" \
  --use-tooling-api \
  --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

COMPONENT_LINKED=0
if [[ -z "$PSG_ID" ]]; then
  log_warn "PSG '${USER_PSG_NAME}' not found — skipping component link + recalc."
  echo "    The custom permission set '${ACCESS_PS_NAME}' still carries Agent Access;"
  echo "    it can be assigned directly to users as a fallback (see below)."
else
  EXISTING_COMPONENT=$(sf data query \
    --query "SELECT Id FROM PermissionSetGroupComponent WHERE PermissionSetGroupId = '${PSG_ID}' AND PermissionSetId = '${PS_ID}'" \
    --target-org "$ORG_ALIAS" \
    --use-tooling-api \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

  if [[ -n "$EXISTING_COMPONENT" ]]; then
    log_pass "'${ACCESS_PS_NAME}' is already a component of '${USER_PSG_NAME}'"
    COMPONENT_LINKED=1
  else
    log_try "Adding '${ACCESS_PS_NAME}' as a component of '${USER_PSG_NAME}'..."
    CREATE_COMPONENT=$(sf data create record \
      --sobject PermissionSetGroupComponent \
      --values "PermissionSetGroupId='${PSG_ID}' PermissionSetId='${PS_ID}'" \
      --target-org "$ORG_ALIAS" \
      --use-tooling-api \
      --json 2>/dev/null || echo '{"status":1}')

    if echo "$CREATE_COMPONENT" | jq -e '.result.id // empty' >/dev/null 2>&1; then
      log_pass "Linked '${ACCESS_PS_NAME}' into '${USER_PSG_NAME}'"
      COMPONENT_LINKED=1
    elif echo "$CREATE_COMPONENT" | jq -r '.message // .result.message // ""' 2>/dev/null | grep -qi "DUPLICATE_VALUE"; then
      log_pass "'${ACCESS_PS_NAME}' already a component of '${USER_PSG_NAME}' (duplicate insert ignored)"
      COMPONENT_LINKED=1
    else
      COMPONENT_ERR=$(echo "$CREATE_COMPONENT" | jq -r '.message // .result.message // "unknown"' 2>/dev/null || echo "unknown")
      log_warn "Could not link custom permset into managed PSG: $COMPONENT_ERR"
      echo "    Falling back to direct assignment of '${ACCESS_PS_NAME}' to PSG users."
    fi
  fi
fi

# ------------------------------------------------------------
# Step 3b: Add the custom permset as a component of the agent-user PSG too.
# The autonomous agent user runs the suggestion flow AS the agent, so it also
# needs Agent Access — wire the same custom permset into SalesManagementAgentUserPsg.
# Mirrors Step 3 (Tooling API object; idempotent query-then-skip). No direct-
# assignment fallback: the agent user is a single system user, so the component
# link is the right (and only) path.
# ------------------------------------------------------------
AGENT_COMPONENT_LINKED=0
AGENT_PSG_ID=$(sf data query \
  --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = '${AGENT_PSG_NAME}'" \
  --target-org "$ORG_ALIAS" \
  --use-tooling-api \
  --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

if [[ -z "$AGENT_PSG_ID" ]]; then
  log_warn "PSG '${AGENT_PSG_NAME}' not found — skipping agent component link + recalc."
else
  EXISTING_AGENT_COMPONENT=$(sf data query \
    --query "SELECT Id FROM PermissionSetGroupComponent WHERE PermissionSetGroupId = '${AGENT_PSG_ID}' AND PermissionSetId = '${PS_ID}'" \
    --target-org "$ORG_ALIAS" \
    --use-tooling-api \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

  if [[ -n "$EXISTING_AGENT_COMPONENT" ]]; then
    log_pass "'${ACCESS_PS_NAME}' is already a component of '${AGENT_PSG_NAME}'"
    AGENT_COMPONENT_LINKED=1
  else
    log_try "Adding '${ACCESS_PS_NAME}' as a component of '${AGENT_PSG_NAME}'..."
    CREATE_AGENT_COMPONENT=$(sf data create record \
      --sobject PermissionSetGroupComponent \
      --values "PermissionSetGroupId='${AGENT_PSG_ID}' PermissionSetId='${PS_ID}'" \
      --target-org "$ORG_ALIAS" \
      --use-tooling-api \
      --json 2>/dev/null || echo '{"status":1}')

    if echo "$CREATE_AGENT_COMPONENT" | jq -e '.result.id // empty' >/dev/null 2>&1; then
      log_pass "Linked '${ACCESS_PS_NAME}' into '${AGENT_PSG_NAME}'"
      AGENT_COMPONENT_LINKED=1
    elif echo "$CREATE_AGENT_COMPONENT" | jq -r '.message // .result.message // ""' 2>/dev/null | grep -qi "DUPLICATE_VALUE"; then
      log_pass "'${ACCESS_PS_NAME}' already a component of '${AGENT_PSG_NAME}' (duplicate insert ignored)"
      AGENT_COMPONENT_LINKED=1
    else
      AGENT_COMPONENT_ERR=$(echo "$CREATE_AGENT_COMPONENT" | jq -r '.message // .result.message // "unknown"' 2>/dev/null || echo "unknown")
      log_warn "Could not link custom permset into agent PSG: $AGENT_COMPONENT_ERR"
    fi
  fi
fi

# ------------------------------------------------------------
# Step 4: Confirm the PSG recalculates so the added component takes effect.
# The PermissionSetGroupComponent insert in Step 3 is what actually TRIGGERS the
# async recalculation — PermissionSetGroup.Status is a system-computed field
# (Updated/Updating/Outdated/Failed), NOT client-writable. There is no CLI recalc
# verb, so we simply POLL Status until it returns to 'Updated'. A Failed status
# means Agent Access is NOT live and must be surfaced as a hard error.
# ------------------------------------------------------------
# The PermissionSetGroupComponent insert in Step 3 IS the recalc trigger — the
# async recalculation is already under way and the org converges on its own; we
# deliberately do NOT block waiting for it (recalc completion only matters when a
# user later launches the agent). We read Status once, for reporting.
if [[ "$COMPONENT_LINKED" -eq 1 && -n "$PSG_ID" ]]; then
  log_try "Recalculation triggered for '${USER_PSG_NAME}' (component linked)."
  PSG_STATUS=$(psg_status "$ORG_ALIAS" "$USER_PSG_NAME")
  case "$PSG_STATUS" in
    Updated)
      log_pass "PSG '${USER_PSG_NAME}' Status: Updated" ;;
    Failed)
      log_fail "PSG '${USER_PSG_NAME}' recalculation Status: Failed — Agent Access not active"
      exit 1 ;;
    *)
      log_info "PSG '${USER_PSG_NAME}' Status: ${PSG_STATUS} — recalculation is async and will complete on its own."
      echo "    Agent Access takes effect once Status reaches 'Updated' (verify-all.sh reports it)." ;;
  esac
fi

# ------------------------------------------------------------
# Step 4b: Report the agent-user PSG recalc, mirroring Step 4 (read Status once,
# never sleep-poll — the Step 3b component insert already triggered the async
# recalculation).
# ------------------------------------------------------------
if [[ "$AGENT_COMPONENT_LINKED" -eq 1 && -n "$AGENT_PSG_ID" ]]; then
  log_try "Recalculation triggered for '${AGENT_PSG_NAME}' (component linked)."
  AGENT_PSG_STATUS=$(psg_status "$ORG_ALIAS" "$AGENT_PSG_NAME")
  case "$AGENT_PSG_STATUS" in
    Updated)
      log_pass "PSG '${AGENT_PSG_NAME}' Status: Updated" ;;
    Failed)
      log_fail "PSG '${AGENT_PSG_NAME}' recalculation Status: Failed — Agent Access not active"
      exit 1 ;;
    *)
      log_info "PSG '${AGENT_PSG_NAME}' Status: ${AGENT_PSG_STATUS} — recalculation is async and will complete on its own."
      echo "    Agent Access takes effect once Status reaches 'Updated' (verify-all.sh reports it)." ;;
  esac
fi

# ------------------------------------------------------------
# Fallback: if the component link failed, assign the custom permset directly to
# the users who hold the managed PSG so they still get Agent Access.
# ------------------------------------------------------------
if [[ "$COMPONENT_LINKED" -eq 0 && -n "$PSG_ID" ]]; then
  log_info "Fallback: assigning '${ACCESS_PS_NAME}' directly to users of '${USER_PSG_NAME}'..."
  # LIMIT 200 caps the fan-out: each user below costs one sequential API call, so
  # an unbounded query on a large org could issue hundreds of calls. The linked
  # component (Step 3) is the scalable path; this direct-assignment fallback is a
  # best-effort stopgap. If the PSG has >200 users, prefer fixing the component
  # link so recalculation reaches everyone at once.
  ASSIGNEE_IDS=$(sf data query \
    --query "SELECT AssigneeId FROM PermissionSetAssignment WHERE PermissionSetGroup.DeveloperName = '${USER_PSG_NAME}' LIMIT 200" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null | jq -r '.result.records[].AssigneeId' 2>/dev/null || echo "")

  if [[ -z "$ASSIGNEE_IDS" ]]; then
    log_warn "No users currently hold '${USER_PSG_NAME}' — nothing to assign."
  else
    # NOTE: do not name this loop var UID — UID is a readonly special var in bash.
    while IFS= read -r ASSIGNEE_ID; do
      [[ -z "$ASSIGNEE_ID" ]] && continue
      CREATE_RESULT=$(sf data create record \
        --sobject PermissionSetAssignment \
        --values "AssigneeId='${ASSIGNEE_ID}' PermissionSetId='${PS_ID}'" \
        --target-org "$ORG_ALIAS" \
        --json 2>/dev/null || echo '{"status":1}')

      # Distinguish "already assigned" (benign) from real failures like a
      # deactivated user or license conflict — don't paper over the latter.
      RESULT_MSG=$(echo "$CREATE_RESULT" | jq -r '.message // .result.message // ""' 2>/dev/null || echo "")
      if echo "$CREATE_RESULT" | jq -e '.result.id // empty' >/dev/null 2>&1; then
        log_pass "Assigned '${ACCESS_PS_NAME}' to user $ASSIGNEE_ID"
      elif echo "$RESULT_MSG" | grep -qi "DUPLICATE_VALUE"; then
        log_info "Already assigned: $ASSIGNEE_ID"
      elif echo "$RESULT_MSG" | grep -qi "FIELD_INTEGRITY_EXCEPTION"; then
        log_warn "License conflict for $ASSIGNEE_ID (FIELD_INTEGRITY_EXCEPTION) — user may need a license upgrade"
      elif echo "$RESULT_MSG" | grep -qi "INVALID_CROSS_REFERENCE_KEY"; then
        log_warn "Assignment for $ASSIGNEE_ID rejected (INVALID_CROSS_REFERENCE_KEY) — the PSG has not finished recalculating (Status not yet 'Updated'). Re-run after recalculation completes."
      else
        ASSIGN_ERR="${RESULT_MSG:-unknown}"
        log_warn "Failed to assign to $ASSIGNEE_ID: $ASSIGN_ERR"
      fi
    done <<< "$ASSIGNEE_IDS"
  fi
fi

echo ""
echo "=== Agent Access definition complete ==="
echo ""
echo "  Custom permission set : ${ACCESS_PS_NAME} ($PS_ID)"
echo "  Agent                 : ${BOT_DEF_NAME:-<unknown>} ($BOT_DEF_ID)"
echo "  Target PSG            : ${USER_PSG_NAME}"
echo "  Agent PSG             : ${AGENT_PSG_NAME}"
echo ""
echo "  Users holding '${USER_PSG_NAME}' can launch the Sales Agent once the PSG"
echo "  recalculation completes (Status 'Updated'). The recalc runs asynchronously."
