#!/bin/bash

# Verify and ensure Pipeline Management agent is functional.
#
# CRITICAL: BotDefinition:SalesAgent is REQUIRED for a functional Pipeline Management agent.
# Users need an interactive Sales Agent they can chat with, which requires the BotDefinition.
# The agent user + PSG provision the backend identity, but without the BotDefinition,
# users CANNOT interact with the Sales Agent via chat/conversation interface.
#
# This script ensures:
#   Step 1: Agent user exists with SalesManagementAgentUserPsg assigned
#   Step 2: BotDefinition:SalesAgent is created and activated (via authoring bundle)
#   Step 3: Both are verified functional (backend + user-facing)
#
# If the agent user exists but BotDefinition is missing, the script CREATES it.
# If BotDefinition creation fails, the script EXITS 1 (setup incomplete).
#
# Usage: ./create-agent.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source shared library
source "$SCRIPT_DIR/shared/agent-bundle-publish.sh"

# Define Agent Access (W-23242378) so human users holding SalesManagementUserPsg
# can launch the agent. Idempotent; exits gracefully if no active bot exists.
define_agent_access() {
  local org="$1"
  if [[ -f "$SCRIPT_DIR/define-agent-access.sh" ]]; then
    echo ""
    echo "=== Defining Agent Access (W-23242378) ==="
    local rc=0
    bash "$SCRIPT_DIR/define-agent-access.sh" "$org" || rc=$?
    if [[ $rc -ne 0 ]]; then
      echo "  Warning: Agent Access definition failed (exit $rc) — see above"
      return $rc
    fi
  fi
}

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

echo "Verifying Pipeline Management agent setup"
echo ""

# --- Step 1: Check functional indicators (agent user + PSG) ---
echo "=== Step 1: Checking agent user (primary functional indicator) ==="
AGENT_USER=$(sf data query \
  --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0] // empty' 2>/dev/null || echo "")

if [[ -n "$AGENT_USER" ]]; then
  AGENT_USERNAME=$(echo "$AGENT_USER" | jq -r '.Username')
  AGENT_USER_ID=$(echo "$AGENT_USER" | jq -r '.Id')
  echo "  Agent user found: $AGENT_USERNAME"
  echo ""

  # Check PSG assignment
  PSG_ASSIGNED=$(sf data query \
    --query "SELECT PermissionSetGroup.DeveloperName FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroup.DeveloperName = 'SalesManagementAgentUserPsg'" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null | jq -r '.result.records[0] // empty' 2>/dev/null || echo "")

  if [[ -n "$PSG_ASSIGNED" ]]; then
    echo "  PSG assigned: SalesManagementAgentUserPsg ✓"
  else
    echo "  Warning: SalesManagementAgentUserPsg not assigned — attempting assignment..."
    PSG_ID=$(sf data query \
      --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementAgentUserPsg'" \
      --target-org "$ORG_ALIAS" \
      --json 2>/dev/null | jq -r '.result.records[0].Id // empty')
    if [[ -n "$PSG_ID" ]]; then
      sf data create record --sobject PermissionSetAssignment \
        --values "AssigneeId='${AGENT_USER_ID}' PermissionSetGroupId='${PSG_ID}'" \
        --target-org "$ORG_ALIAS" --json 2>/dev/null >/dev/null \
        && echo "  PSG assigned successfully ✓" \
        || echo "  Assignment failed (may already be assigned)"
    fi
  fi
  echo ""

  # Determine architecture — match the bot by AgentTemplate (the field the
  # scheduled flow uses), not by hardcoded DeveloperName.
  echo "=== Architecture Detection ==="
  EXISTING_BOT=$(pm_bot_developer_name "$ORG_ALIAS")

  if [[ -n "$EXISTING_BOT" ]]; then
    echo "  Architecture: Standalone Bot (BotDefinition:$EXISTING_BOT matched by AgentTemplate)"
    echo ""

    # A BotDefinition can exist yet have no ACTIVE version — the state
    # auto-provisioning leaves it in. Without an active version the scheduled
    # flow never adds the agent user to opportunity teams (no suggestions) and
    # Agent Access can't be defined. Activate the latest version if needed.
    BOT_ACTIVE_COUNT=$(pm_bot_active_version_count "$ORG_ALIAS")
    if [[ "$BOT_ACTIVE_COUNT" -ge 1 ]]; then
      echo "  BotVersion: active ✓"
    else
      echo "  BotVersion: no active version — activating (auto-provisioned bots land Inactive)..."
      if ! activate_pm_bot_if_inactive "$ORG_ALIAS"; then
        echo ""
        echo "  BLOCKER: BotDefinition:$EXISTING_BOT exists but has no active version and activation failed."
        echo "  The scheduled flow will not generate suggestions until the agent is active."
        echo "    Resolve via Setup → Agents → $EXISTING_BOT → activate, then re-run: $0 $ORG_ALIAS"
        exit 1
      fi
    fi

    echo ""
    echo "Agent setup is FUNCTIONAL."
    echo "  - Agent user: $AGENT_USERNAME"
    echo "  - PSG: SalesManagementAgentUserPsg"
    echo "  - BotDefinition: $EXISTING_BOT (active)"
    echo "  - Schedule-triggered flow will run as this user"
    echo ""
    echo "No further agent creation/deployment needed."
    define_agent_access "$ORG_ALIAS"
    exit $?
  else
    echo "  Architecture: Platform Copilot (no standalone BotDefinition found)"
    echo "  Attempting to create Sales Agent BotDefinition for user interaction..."
    echo ""

    # Use shared library function to publish and activate agent
    if publish_and_activate_agent "$ORG_ALIAS" "exit" "plain"; then
      echo ""
      echo "Agent setup is COMPLETE."
      echo "  - Agent user: $AGENT_USERNAME"
      echo "  - PSG: SalesManagementAgentUserPsg"
      echo "  - BotDefinition: ${AGENT_API_NAME:-SalesAgent} (ACTIVE, version $AGENT_VERSION)"
      echo "  - Schedule-triggered flow will run as this user"
      define_agent_access "$ORG_ALIAS"
      exit $?
    fi
    # If function returned non-zero, it already exited (on-error="exit")
  fi
fi

# --- Step 2: No agent user found — need remediation ---
echo "  Agent user NOT found."
echo ""
echo "=== Step 2: Attempting SOAP toggle to re-provision agent user + PSGs ==="
echo "  (The toggle re-creates the agent user and permission set groups only."
echo "   It does NOT create BotDefinition:SalesAgent — that comes from the bundle"
echo "   publish in Step 3 below.)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTH_INFO=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$AUTH_INFO" | jq -r '.result.accessToken')
INSTANCE_URL=$(echo "$AUTH_INFO" | jq -r '.result.instanceUrl')

# Newer CLI versions redact accessToken — use show-access-token fallback
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org "$ORG_ALIAS" --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty')
fi

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "Error: Could not retrieve org credentials. Is the org authenticated?"
  exit 1
fi

# Pre-check: Is org in "partially enabled" state (PSGs exist but enableDealAgent=false)?
# In that state, the toggle is harmful — disable may succeed but re-enable will fail.
PM_READ=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
<soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
<soapenv:Body><met:readMetadata><met:type>SalesDealAgentSettings</met:type><met:fullNames>SalesDealAgent</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableDealAgent>[^<]*" | grep -o "true\|false" || echo "")

# PSG existence does NOT count as a partial signal — SalesManagementUserPsg /
# SalesManagementAgentUserPsg ship with the Agentforce-for-Sales license and exist
# in never-configured orgs. The real partial signals (with enableDealAgent=false)
# are a cloned scheduled flow or a PM BotDefinition. (The agent user was already
# ruled out in Step 1 above.)
PM_FLOW_EXISTS=$(pm_flow_clone_exists "$ORG_ALIAS")
PM_BOT_EXISTS=$(pm_bot_count "$ORG_ALIAS")

if [[ "$PM_READ" != "true" && ( "${PM_FLOW_EXISTS:-0}" -ge 1 || "${PM_BOT_EXISTS:-0}" -ge 1 ) ]]; then
  echo "Detected partial-enablement state: enableDealAgent reads false but PM components exist (flow=$PM_FLOW_EXISTS bot=$PM_BOT_EXISTS)."
  echo ""
  echo "  The SOAP toggle is NOT safe in this state (re-enable may fail mid-provisioning)."
  echo "  This org was likely provisioned via org template."
  echo ""
  echo "  To resolve:"
  echo "    1. Open: ${INSTANCE_URL}/lightning/setup/PipelineManagement/home"
  echo "    2. Enable Pipeline Management in the Setup UI"
  echo "    3. Wait 2-5 minutes for agent user provisioning"
  echo "    4. Re-run this script"
  exit 0
fi

echo "  Using SOAP toggle to re-provision agent user + PSGs (NOT the BotDefinition)..."
echo "  WARNING: This will temporarily disable Pipeline Management (~40 seconds)."
echo ""

# Disable Pipeline Management
echo "  Disabling Pipeline Management..."
DISABLE_RESPONSE=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=utf-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
<soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
<soapenv:Body><met:updateMetadata>
  <met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
    <met:fullName>SalesDealAgent</met:fullName>
    <met:enableDealAgent>false</met:enableDealAgent>
  </met:metadata>
</met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

if echo "$DISABLE_RESPONSE" | grep -q "<success>true</success>"; then
  echo "  Disabled successfully. Waiting 10 seconds..."
  sleep 10

  # Re-enable Pipeline Management
  echo "  Re-enabling Pipeline Management..."
  ENABLE_RESPONSE=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
<soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
<soapenv:Body><met:updateMetadata>
  <met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
    <met:fullName>SalesDealAgent</met:fullName>
    <met:enableDealAgent>true</met:enableDealAgent>
    <met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks>
  </met:metadata>
</met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

  if echo "$ENABLE_RESPONSE" | grep -q "<success>true</success>"; then
    echo "  Re-enabled successfully. Waiting 30 seconds for provisioning..."
    sleep 30
  else
    echo "  Error: Failed to re-enable Pipeline Management"
    echo "$ENABLE_RESPONSE" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || true
    exit 1
  fi
else
  ERR_MSG=$(echo "$DISABLE_RESPONSE" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || echo "unknown error")
  echo "  SOAP toggle failed: $ERR_MSG"
  echo ""
fi

# Check if agent user was provisioned
AGENT_USER_CHECK=$(sf data query \
  --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")

if [[ -n "$AGENT_USER_CHECK" ]]; then
  echo ""
  echo "  Agent user provisioned: $AGENT_USER_CHECK"
  echo "  BotDefinition:SalesAgent is still missing — the toggle does not create it."
  echo "  Proceeding to Step 3 to publish the authoring bundle."
fi

# --- Step 3: Last resort — authoring bundle deployment ---
echo ""
echo "=== Step 3: Attempting authoring bundle deployment (last resort) ==="

# Use shared library function with return-on-error behavior
if publish_and_activate_agent "$ORG_ALIAS" "return" "plain"; then
  echo "  Agent deployed and activated via authoring bundle"
  define_agent_access "$ORG_ALIAS"
  exit $?
else
  echo "  Authoring bundle publish/activate failed"
fi

# --- All approaches failed ---
echo ""
echo "=== BLOCKER: Agent provisioning failed ==="
echo ""
echo "  No agent user was created via any automated method."
echo "  Suggestions cannot generate without the agent user."
echo ""
echo "  Manual resolution:"
echo "    1. Open: ${INSTANCE_URL}/lightning/setup/PipelineManagement/home"
echo "    2. Disable Pipeline Management, wait 30 seconds, re-enable"
echo "    3. Wait 2-5 minutes for agent user provisioning"
echo "    4. Re-run: $0 $ORG_ALIAS"
exit 1
