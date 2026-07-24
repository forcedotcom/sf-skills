#!/bin/bash

# Retrieve and display Pipeline Management settings status
# Uses SOAP readMetadata (reliable) instead of CLI retrieve (empty results for many settings)
# Usage: ./retrieve-settings.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

echo "Retrieving Pipeline Management settings from org: $ORG_ALIAS"
echo ""

# Get credentials
INSTANCE_URL=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.instanceUrl // empty' 2>/dev/null || echo "")
ACCESS_TOKEN=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.accessToken // empty' 2>/dev/null || echo "")

if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org "$ORG_ALIAS" --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty' 2>/dev/null || echo "")
fi

if [[ -z "$INSTANCE_URL" || -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "Error: Cannot connect to org. Run: sf org login web --alias $ORG_ALIAS"
  exit 1
fi

# SOAP readMetadata helper
soap_read() {
  local TYPE="$1" NAME="$2"
  curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=UTF-8" \
    -H "SOAPAction: readMetadata" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>${TYPE}</met:type><met:fullNames>${NAME}</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null
}

check_setting() {
  local LABEL="$1" TYPE="$2" NAME="$3" FIELD="$4"
  printf "  %-35s" "$LABEL:"
  local RESPONSE
  RESPONSE=$(soap_read "$TYPE" "$NAME")
  local VALUE
  VALUE=$(echo "$RESPONSE" | grep -o "<${FIELD}>[^<]*" | sed "s/<${FIELD}>//" | head -1 || echo "")

  if [[ "$VALUE" == "true" ]]; then
    echo "ENABLED"
  elif [[ "$VALUE" == "false" ]]; then
    echo "DISABLED"
  elif [[ -z "$VALUE" ]]; then
    echo "NOT FOUND (type may not exist in this org)"
  else
    echo "$VALUE"
  fi
}

echo "=== Settings Status (via SOAP readMetadata) ==="
echo ""

check_setting "Einstein Generative AI" "EinsteinGptSettings" "EinsteinGpt" "enableEinsteinGptPlatform"
check_setting "Agentforce Agent (Copilot)" "EinsteinCopilotSettings" "EinsteinCopilot" "enableEinsteinGptCopilot"
check_setting "Pipeline Management" "SalesDealAgentSettings" "SalesDealAgent" "enableDealAgent"
check_setting "Auto-Approve All Tasks" "SalesDealAgentSettings" "SalesDealAgent" "enableDealAgentAutoApproveAllTasks"
check_setting "Pipeline Inspection" "OpportunitySettings" "Opportunity" "enablePipelineInspection"
check_setting "Enhanced Notes" "EnhancedNotesSettings" "EnhancedNotes" "enableEnhancedNotes"
check_setting "Enhanced Email" "EmailAdministrationSettings" "EmailAdministration" "enableEnhancedEmailEnabled"
check_setting "Opportunity Team Selling" "OpportunitySettings" "Opportunity" "enableOpportunityTeam"

echo ""
echo "=== Auto-Provisioned Components ==="
echo ""

# PSGs
PSG_RESULT=$(sf data query -q "SELECT DeveloperName FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null | jq -r '.result.records[].DeveloperName' 2>/dev/null || echo "")
printf "  %-35s" "Permission Set Groups:"
if [[ -n "$PSG_RESULT" ]]; then
  echo "$PSG_RESULT" | tr '\n' ',' | sed 's/,$/\n/'
else
  echo "NOT FOUND"
fi

# Agent user
AGENT_USER=$(sf data query -q "SELECT Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty' 2>/dev/null || echo "")
printf "  %-35s" "Agent User:"
if [[ -n "$AGENT_USER" ]]; then
  echo "$AGENT_USER"
else
  echo "NOT FOUND"
fi

# Flow — check by SourceTemplateId, then by naming convention, then by exact name
FLOW_QUERY=$(sf data query -q "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org "$ORG_ALIAS" --json 2>/dev/null)
FLOW_NAME=$(echo "$FLOW_QUERY" | jq -r '.result.records[0] | "\(.ApiName) (Active: \(.IsActive))"' 2>/dev/null | head -1 || echo "")

if [[ -z "$FLOW_NAME" || "$FLOW_NAME" == "null (Active: null)" ]]; then
  FLOW_QUERY=$(sf data query -q "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = 'Process_Field_Update_Suggestions' AND IsTemplate=false" --target-org "$ORG_ALIAS" --json 2>/dev/null)
  FLOW_NAME=$(echo "$FLOW_QUERY" | jq -r '.result.records[0] | "\(.ApiName) (Active: \(.IsActive))"' 2>/dev/null | head -1 || echo "")
fi

printf "  %-35s" "Schedule-Triggered Flow:"
if [[ -n "$FLOW_NAME" && "$FLOW_NAME" != "null (Active: null)" ]]; then
  echo "$FLOW_NAME"
else
  echo "NOT FOUND"
fi

# Stage descriptions
DESC_RESULT=$(sf data query -q "SELECT Id FROM OpptStageDescription" --target-org "$ORG_ALIAS" --use-tooling-api --json 2>/dev/null || echo '{"status":1}')
printf "  %-35s" "Stage Descriptions:"
if echo "$DESC_RESULT" | grep -qi "INVALID_TYPE\|NOT_FOUND\|sObject type.*not supported"; then
  echo "N/A (PM not fully enabled)"
else
  DESC_COUNT=$(echo "$DESC_RESULT" | jq -r '.result.totalSize // 0' 2>/dev/null | head -1 | tr -cd '0-9')
  echo "${DESC_COUNT:-0}"
fi

echo ""
echo "Done."
