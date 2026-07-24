#!/bin/bash

# Comprehensive verification of Pipeline Management configuration
#
# Checks all components and reports status. Run after setup to confirm
# everything is working, or to diagnose a partially configured org.
#
# Usage: ./verify-all.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

# Source shared libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared/soap.sh"
source "$SCRIPT_DIR/shared/agent-detection.sh"

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

# Validate org alias (prevent shell injection via metacharacters)
if [[ ! "$ORG_ALIAS" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]; then
  echo "ERROR: Invalid org alias. Only alphanumeric, dots, hyphens, and underscores allowed (must start with alphanumeric)."
  exit 1
fi

echo "============================================"
echo " PIPELINE MANAGEMENT CONFIGURATION STATUS"
echo "============================================"
echo ""
echo "Org: $ORG_ALIAS"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

PASS=0
WARN=0
FAIL=0

check_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
check_warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }
check_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
check_error() { echo "  [ERROR] $1"; echo "          $2"; FAIL=$((FAIL + 1)); }

# --- Prerequisites ---
echo "--- Prerequisites ---"

# Get auth details for SOAP checks
INSTANCE_URL=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.instanceUrl // empty' 2>/dev/null || echo "")

# Get access token — newer CLI versions redact it in `sf org display --json`
# so we use `sf org auth show-access-token --json` which always returns the real token
ACCESS_TOKEN=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.accessToken // empty' 2>/dev/null || echo "")

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org "$ORG_ALIAS" --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty' 2>/dev/null || echo "")
fi

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "  [FAIL] Cannot retrieve access token. Is the org authenticated?"
  echo "         Run: sf org login web --instance-url <url> --alias $ORG_ALIAS"
  exit 1
fi

# Check Pipeline Management (SOAP only)
PM_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>SalesDealAgentSettings</met:type>
    <met:fullNames>SalesDealAgent</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
PM_HTTP_STATUS=$(echo "$PM_RESPONSE" | tail -1)
PM_XML=$(echo "$PM_RESPONSE" | sed '$d')
PM_STATUS=$(parse_soap_response "$PM_XML" "enableDealAgent" "$PM_HTTP_STATUS")

case "$PM_STATUS" in
  true)
    check_pass "Pipeline Management: enabled"
    ;;
  false)
    check_fail "Pipeline Management: DISABLED"
    echo "         → Enable via: Setup → Sales → Pipeline Management → Turn On"
    ;;
  AUTH_ERROR:*)
    check_error "Pipeline Management: Authentication failed" "${PM_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  TYPE_UNAVAILABLE:*)
    check_error "Pipeline Management: Not available in this org" "${PM_STATUS#TYPE_UNAVAILABLE:}"
    echo "         → Check: org edition and enabled features in Setup"
    ;;
  NETWORK_ERROR)
    check_error "Pipeline Management: Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_fail "Pipeline Management: Unknown status ($PM_STATUS)"
    ;;
esac

# Check Einstein GenAI
GENAI_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>EinsteinGptSettings</met:type>
    <met:fullNames>EinsteinGpt</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
GENAI_HTTP_STATUS=$(echo "$GENAI_RESPONSE" | tail -1)
GENAI_XML=$(echo "$GENAI_RESPONSE" | sed '$d')
GENAI_STATUS=$(parse_soap_response "$GENAI_XML" "enableEinsteinGptPlatform" "$GENAI_HTTP_STATUS")

case "$GENAI_STATUS" in
  true)
    check_pass "Einstein Generative AI: enabled"
    ;;
  false)
    check_fail "Einstein Generative AI: DISABLED"
    echo "         → Enable via: Setup → Einstein → Einstein Generative AI → Turn On"
    ;;
  AUTH_ERROR:*)
    check_error "Einstein Generative AI: Authentication failed" "${GENAI_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  NETWORK_ERROR)
    check_error "Einstein Generative AI: Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_fail "Einstein Generative AI: Unknown status ($GENAI_STATUS)"
    ;;
esac

# Check Agentforce Agent
COPILOT_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>EinsteinCopilotSettings</met:type>
    <met:fullNames>EinsteinCopilot</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
COPILOT_HTTP_STATUS=$(echo "$COPILOT_RESPONSE" | tail -1)
COPILOT_XML=$(echo "$COPILOT_RESPONSE" | sed '$d')
COPILOT_STATUS=$(parse_soap_response "$COPILOT_XML" "enableEinsteinGptCopilot" "$COPILOT_HTTP_STATUS")

case "$COPILOT_STATUS" in
  true)
    check_pass "Agentforce Agent: enabled"
    ;;
  false)
    check_fail "Agentforce Agent: DISABLED"
    echo "         → Enable via: Setup → Einstein → Agentforce Agent → Turn On"
    ;;
  AUTH_ERROR:*)
    check_error "Agentforce Agent: Authentication failed" "${COPILOT_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  NETWORK_ERROR)
    check_error "Agentforce Agent: Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_fail "Agentforce Agent: Unknown status ($COPILOT_STATUS)"
    ;;
esac

# Check Agentforce Studio / Agent Platform (CRITICAL — AgentPlatformSettings
# .enableAgentPlatform gates the Sales Deal Agent; core rejects Deal Agent
# enablement when this OrgPreference is off, so a disabled state here explains
# an otherwise-opaque Deal Agent activation failure).
AGENT_PLATFORM_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>AgentPlatformSettings</met:type>
    <met:fullNames>AgentPlatform</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
AGENT_PLATFORM_HTTP_STATUS=$(echo "$AGENT_PLATFORM_RESPONSE" | tail -1)
AGENT_PLATFORM_XML=$(echo "$AGENT_PLATFORM_RESPONSE" | sed '$d')
AGENT_PLATFORM_STATUS=$(parse_soap_response "$AGENT_PLATFORM_XML" "enableAgentPlatform" "$AGENT_PLATFORM_HTTP_STATUS")

case "$AGENT_PLATFORM_STATUS" in
  true)
    check_pass "Agentforce Studio (Agent Platform): enabled"
    ;;
  false)
    check_fail "Agentforce Studio (Agent Platform): DISABLED"
    echo "         → Enable via: Setup → Agentforce Studio → Turn On (gates Deal Agent)"
    ;;
  AUTH_ERROR:*)
    check_error "Agentforce Studio (Agent Platform): Authentication failed" "${AGENT_PLATFORM_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  NETWORK_ERROR)
    check_error "Agentforce Studio (Agent Platform): Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_fail "Agentforce Studio (Agent Platform): Unknown status ($AGENT_PLATFORM_STATUS)"
    ;;
esac

# Check Opportunity Team (CRITICAL — PM flow uses OpportunityTeamMember; without
# it, flow deployment fails with an OppTeamMemRec error)
OPP_TEAM_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>OpportunitySettings</met:type>
    <met:fullNames>Opportunity</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
OPP_TEAM_HTTP_STATUS=$(echo "$OPP_TEAM_RESPONSE" | tail -1)
OPP_TEAM_XML=$(echo "$OPP_TEAM_RESPONSE" | sed '$d')
OPP_TEAM_STATUS=$(parse_soap_response "$OPP_TEAM_XML" "enableOpportunityTeam" "$OPP_TEAM_HTTP_STATUS")

case "$OPP_TEAM_STATUS" in
  true)
    check_pass "Opportunity Team: enabled"
    ;;
  false)
    check_fail "Opportunity Team: DISABLED (flow deploy fails with OppTeamMemRec error)"
    echo "         → Enable via: Setup → Opportunity → Opportunity Team Settings → Turn On"
    ;;
  AUTH_ERROR:*)
    check_error "Opportunity Team: Authentication failed" "${OPP_TEAM_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  NETWORK_ERROR)
    check_error "Opportunity Team: Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_fail "Opportunity Team: Unknown status ($OPP_TEAM_STATUS)"
    ;;
esac

# Check Pipeline Inspection
PI_RESPONSE=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>OpportunitySettings</met:type>
    <met:fullNames>Opportunity</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)
PI_HTTP_STATUS=$(echo "$PI_RESPONSE" | tail -1)
PI_XML=$(echo "$PI_RESPONSE" | sed '$d')
PI_STATUS=$(parse_soap_response "$PI_XML" "enablePipelineInspection" "$PI_HTTP_STATUS")

case "$PI_STATUS" in
  true)
    check_pass "Pipeline Inspection: enabled"
    ;;
  false)
    check_warn "Pipeline Inspection: DISABLED (suggestions won't show in UI)"
    ;;
  AUTH_ERROR:*)
    check_error "Pipeline Inspection: Authentication failed" "${PI_STATUS#AUTH_ERROR:}"
    echo "         → Fix: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
    ;;
  NETWORK_ERROR)
    check_error "Pipeline Inspection: Cannot verify (network/service error)" "Check instance URL and connectivity"
    ;;
  *)
    check_warn "Pipeline Inspection: Unknown status ($PI_STATUS)"
    ;;
esac

echo ""

# --- Agent ---
echo "--- Agent ---"

AGENT_USER=$(sf data query \
  --query "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")

if [[ -n "$AGENT_USER" ]]; then
  check_pass "Agent user: $AGENT_USER"
else
  check_fail "Agent user: NOT FOUND"
fi

# Detect the PM bot by AgentTemplate — the same field the scheduled flow
# uses — instead of a hardcoded DeveloperName.
BOT_DEF=$(pm_bot_developer_name "$ORG_ALIAS")

if [[ -n "$BOT_DEF" ]]; then
  check_pass "BotDefinition: $BOT_DEF (matched by AgentTemplate)"
else
  check_fail "BotDefinition: NOT FOUND — no bot with a PM AgentTemplate (run create-agent.sh)"
fi

echo ""

# --- Permission Set Groups ---
echo "--- Permission Set Groups ---"

PSG_COUNT=$(sf data query \
  --query "SELECT Id, DeveloperName FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" \
  --target-org "$ORG_ALIAS" \
  --use-tooling-api \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
PSG_COUNT="${PSG_COUNT:-0}"

# These two PSGs ship with the Agentforce-for-Sales license, so their presence is a
# license check — NOT a Pipeline Management enablement indicator. The real functional
# checks are the agent-user PSG assignment and user PSG assignments below.
if [[ "$PSG_COUNT" -ge 2 ]]; then
  check_pass "Permission Set Groups (license): both present ($PSG_COUNT/2)"
else
  check_warn "Permission Set Groups (license): only $PSG_COUNT/2 found — org may lack the Agentforce-for-Sales license"
fi

# Check if agent user has PSG
if [[ -n "$AGENT_USER" ]]; then
  AGENT_USER_ID=$(sf data query \
    --query "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

  if [[ -n "$AGENT_USER_ID" ]]; then
    AGENT_PSG=$(sf data query \
      --query "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroup.DeveloperName = 'SalesManagementAgentUserPsg'" \
      --target-org "$ORG_ALIAS" \
      --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
    AGENT_PSG="${AGENT_PSG:-0}"

    if [[ "$AGENT_PSG" -ge 1 ]]; then
      check_pass "Agent PSG assignment: assigned"
    else
      check_warn "Agent PSG assignment: NOT assigned to agent user"
    fi
  fi
fi

# Count users with SalesManagementUserPsg
USER_PSG_COUNT=$(sf data query \
  --query "SELECT COUNT() FROM PermissionSetAssignment WHERE PermissionSetGroup.DeveloperName = 'SalesManagementUserPsg'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
USER_PSG_COUNT="${USER_PSG_COUNT:-0}"

if [[ "$USER_PSG_COUNT" -ge 1 ]]; then
  check_pass "User PSG assignments: $USER_PSG_COUNT user(s) assigned"
else
  check_warn "User PSG assignments: 0 users have SalesManagementUserPsg"
fi

echo ""

# --- Agent Access (W-23242378) ---
# Users holding SalesManagementUserPsg can only launch the agent if it is added
# to "Agent Access" on a permission set. This is done via the custom permset
# Sales_Agent_Access (SetupEntityAccess -> BotDefinition) linked into the PSG.
echo "--- Agent Access ---"

ACCESS_PS_ID=$(sf data query \
  --query "SELECT Id FROM PermissionSet WHERE Name = 'Sales_Agent_Access'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

if [[ -z "$ACCESS_PS_ID" ]]; then
  check_warn "Agent Access permset: 'Sales_Agent_Access' not found (run define-agent-access.sh)"
else
  check_pass "Agent Access permset: Sales_Agent_Access"

  # Is the agent (BotDefinition, matched by AgentTemplate) granted on that permset?
  # Query by AgentTemplate only — the `Id IN (SELECT ... FROM BotVersion)` subquery
  # was removed in de77d520 because it hangs 60+ seconds on some orgs. Active-version
  # verification is reported separately by the BotDefinition check above (line ~270).
  if [[ -n "$BOT_DEF" ]]; then
    BOT_DEF_ID=$(sf data query \
      --query "SELECT Id FROM BotDefinition WHERE AgentTemplate IN (${PM_AGENT_TEMPLATES_SOQL}) ORDER BY LastModifiedDate DESC LIMIT 1" \
      --target-org "$ORG_ALIAS" \
      --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

    if [[ -n "$BOT_DEF_ID" ]]; then
      ACCESS_COUNT=$(sf data query \
        --query "SELECT COUNT() FROM SetupEntityAccess WHERE ParentId = '${ACCESS_PS_ID}' AND SetupEntityId = '${BOT_DEF_ID}'" \
        --target-org "$ORG_ALIAS" \
        --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
      ACCESS_COUNT="${ACCESS_COUNT:-0}"

      if [[ "$ACCESS_COUNT" -ge 1 ]]; then
        check_pass "Agent Access grant: $BOT_DEF added to Sales_Agent_Access"
      else
        check_fail "Agent Access grant: agent NOT in Sales_Agent_Access (users cannot launch agent)"
      fi
    fi
  else
    check_warn "Agent Access grant: BotDefinition absent — cannot verify grant"
  fi

  # Is the custom permset linked into the managed PSG?
  ACCESS_PSG_ID=$(sf data query \
    --query "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" \
    --target-org "$ORG_ALIAS" \
    --use-tooling-api \
    --json 2>/dev/null | jq -r '.result.records[0].Id // empty' 2>/dev/null || echo "")

  if [[ -n "$ACCESS_PSG_ID" ]]; then
    COMPONENT_COUNT=$(sf data query \
      --query "SELECT COUNT() FROM PermissionSetGroupComponent WHERE PermissionSetGroupId = '${ACCESS_PSG_ID}' AND PermissionSetId = '${ACCESS_PS_ID}'" \
      --target-org "$ORG_ALIAS" \
      --use-tooling-api \
      --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
    COMPONENT_COUNT="${COMPONENT_COUNT:-0}"

    if [[ "$COMPONENT_COUNT" -ge 1 ]]; then
      check_pass "Agent Access link: Sales_Agent_Access is a component of SalesManagementUserPsg"
    else
      check_warn "Agent Access link: Sales_Agent_Access not linked into SalesManagementUserPsg (may be assigned directly)"
    fi
  fi
fi

echo ""

# --- Schedule-Triggered Flow ---
echo "--- Schedule-Triggered Flow ---"

# Check by SourceTemplateId first
FLOW_QUERY=$(sf data query \
  --query "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null)

FLOW_NAME=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null | head -1 || echo "")
FLOW_ACTIVE=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null | head -1 || echo "")

# Fallback: check by naming convention
if [[ -z "$FLOW_NAME" ]]; then
  FLOW_QUERY=$(sf data query \
    --query "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate=false" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null)

  FLOW_NAME=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null | head -1 || echo "")
  FLOW_ACTIVE=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null | head -1 || echo "")
fi

# Fallback: check by exact deployed name
if [[ -z "$FLOW_NAME" ]]; then
  FLOW_QUERY=$(sf data query \
    --query "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = 'Process_Field_Update_Suggestions' AND IsTemplate=false" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null)

  FLOW_NAME=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null | head -1 || echo "")
  FLOW_ACTIVE=$(echo "$FLOW_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null | head -1 || echo "")
fi

if [[ -z "$FLOW_NAME" ]]; then
  check_fail "Schedule flow: NOT FOUND (must clone via Setup UI 'Save As')"
elif [[ "$FLOW_ACTIVE" == "true" ]]; then
  check_pass "Schedule flow: $FLOW_NAME (ACTIVE)"
else
  check_warn "Schedule flow: $FLOW_NAME (INACTIVE — needs activation)"
fi

# Check template exists
TEMPLATE_EXISTS=$(sf data query \
  --query "SELECT Id, ApiName FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate=true" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")

if [[ -n "$TEMPLATE_EXISTS" ]]; then
  check_pass "Template flow: present"
else
  check_fail "Template flow: NOT provisioned (Pipeline Management may not be fully enabled)"
fi

echo ""

# --- Grounding Flows (managed sales_pipe_mgmt) ---
# Deactivated grounding flows silently kill all suggestion generation.
echo "--- Grounding Flows ---"

GROUNDING_QUERY=$(sf data query \
  --query "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE NamespacePrefix='sales_pipe_mgmt' AND ApiName IN ('GetOppGroundingData','GetRcmdConvTscp')" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null)

for GROUNDING_FLOW in GetOppGroundingData GetRcmdConvTscp; do
  GROUNDING_ACTIVE=$(echo "$GROUNDING_QUERY" | jq -r --arg n "$GROUNDING_FLOW" '.result.records[] | select(.ApiName==$n) | .IsActive' 2>/dev/null | head -1)
  if [[ -z "$GROUNDING_ACTIVE" ]]; then
    check_fail "Grounding flow $GROUNDING_FLOW: NOT FOUND (sales_pipe_mgmt namespace not provisioned)"
  elif [[ "$GROUNDING_ACTIVE" == "true" ]]; then
    check_pass "Grounding flow $GROUNDING_FLOW: ACTIVE"
  else
    check_fail "Grounding flow $GROUNDING_FLOW: INACTIVE (suggestions will not generate)"
  fi
done

echo ""

# --- Stage Descriptions ---
echo "--- Stage Descriptions ---"

STAGE_COUNT=$(sf data query \
  --query "SELECT MasterLabel FROM OpportunityStage WHERE IsActive = true" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
STAGE_COUNT="${STAGE_COUNT:-0}"

DESC_RESULT=$(sf data query \
  --query "SELECT Id FROM OpptStageDescription" \
  --target-org "$ORG_ALIAS" \
  --use-tooling-api \
  --json 2>/dev/null || echo '{"status":1}')

# OpptStageDescription may be inaccessible if PM isn't fully enabled
if echo "$DESC_RESULT" | grep -qi "INVALID_TYPE\|NOT_FOUND\|sObject type.*not supported"; then
  DESC_COUNT="0"
  check_warn "Stage descriptions: OpptStageDescription not accessible (Pipeline Management may not be fully enabled)"
else
  DESC_COUNT=$(echo "$DESC_RESULT" | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
  DESC_COUNT="${DESC_COUNT:-0}"

  if [[ "$DESC_COUNT" -ge "$STAGE_COUNT" && "$DESC_COUNT" -gt 0 ]]; then
    check_pass "Stage descriptions: $DESC_COUNT/$STAGE_COUNT stages described"
  elif [[ "$DESC_COUNT" -gt 0 ]]; then
    check_warn "Stage descriptions: $DESC_COUNT/$STAGE_COUNT stages (some missing — stage suggestions may fail)"
  else
    check_fail "Stage descriptions: NONE configured (stage suggestions will not work)"
  fi
fi

echo ""

# --- Data Sources ---
echo "--- Data Sources ---"

NOTE_COUNT=$(sf data query \
  --query "SELECT COUNT() FROM ContentNote WHERE CreatedDate = LAST_N_DAYS:30" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
NOTE_COUNT="${NOTE_COUNT:-0}"

if [[ "$NOTE_COUNT" -gt 0 ]]; then
  check_pass "Recent notes (30d): $NOTE_COUNT"
else
  check_warn "Recent notes (30d): 0 (agent needs notes to generate suggestions)"
fi

OPP_COUNT=$(sf data query \
  --query "SELECT COUNT() FROM Opportunity WHERE IsClosed = false" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
OPP_COUNT="${OPP_COUNT:-0}"

if [[ "$OPP_COUNT" -gt 0 ]]; then
  check_pass "Open opportunities: $OPP_COUNT"
else
  check_warn "Open opportunities: 0 (agent needs open opps to generate suggestions)"
fi

EMAIL_COUNT=$(sf data query \
  --query "SELECT COUNT() FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9' || echo "0")
EMAIL_COUNT="${EMAIL_COUNT:-0}"

if [[ "$EMAIL_COUNT" -gt 0 ]]; then
  check_pass "Recent emails (30d): $EMAIL_COUNT"
else
  check_warn "Recent emails (30d): 0 (optional — agent can use notes instead)"
fi

echo ""

# --- Summary ---
echo "============================================"
echo " SUMMARY"
echo "============================================"
echo ""
echo "  PASS: $PASS"
echo "  WARN: $WARN"
echo "  FAIL: $FAIL"
echo ""

if [[ "$FAIL" -eq 0 && "$WARN" -eq 0 ]]; then
  echo "  Status: FULLY CONFIGURED"
  echo ""
  echo "  Pipeline Management is fully operational."
  echo "  Suggestions will generate on the next scheduled flow run."
elif [[ "$FAIL" -eq 0 ]]; then
  echo "  Status: CONFIGURED WITH WARNINGS"
  echo ""
  echo "  Core functionality is in place. Review warnings above."
else
  echo "  Status: INCOMPLETE — $FAIL issue(s) must be resolved"
  echo ""
  echo "  Fix the FAIL items above before Pipeline Management will function."
  echo ""
  echo "  Common fixes:"
  [[ "$OPP_TEAM_STATUS" != "true" ]] && echo "    - Enable Opportunity Team: ./enable-prerequisites.sh $ORG_ALIAS"
  [[ "$PM_STATUS" != "true" ]] && echo "    - Enable Pipeline Management: ./enable-deal-agent.sh $ORG_ALIAS"
  [[ -z "$AGENT_USER" ]] && echo "    - Create agent: ./create-agent.sh $ORG_ALIAS"
  [[ -z "$FLOW_NAME" ]] && echo "    - Clone flow: Setup UI → Flows → OppSuggGenSchFlow → Save As"
  [[ "${DESC_COUNT:-0}" -eq 0 ]] && echo "    - Add stage descriptions: see references/opportunity-stages.md"

  # Exit with error status when FAIL > 0 (a PM BotDefinition is now REQUIRED)
  exit 1
fi

echo ""
