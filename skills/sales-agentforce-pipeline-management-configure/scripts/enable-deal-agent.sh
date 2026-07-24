#!/bin/bash

# Enable Pipeline Management (SalesDealAgentSettings) via SOAP API
# Usage: ./enable-deal-agent.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "❌ Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

echo "🚀 Enabling Pipeline Management for org: $ORG_ALIAS"
echo ""

# Get org details
ORG_INFO=$(sf org display --target-org "$ORG_ALIAS" --json 2>/dev/null)
ORG_ID=$(echo "$ORG_INFO" | jq -r '.result.id')
INSTANCE_URL=$(echo "$ORG_INFO" | jq -r '.result.instanceUrl')
ACCESS_TOKEN=$(echo "$ORG_INFO" | jq -r '.result.accessToken')

# Newer CLI versions redact accessToken — use show-access-token fallback
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org "$ORG_ALIAS" --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty')
fi

if [[ -z "$ORG_ID" || -z "$INSTANCE_URL" || -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" ]]; then
  echo "Error: Could not retrieve org details. Is the org authenticated?"
  exit 1
fi

echo "Org ID: $ORG_ID"
echo "Instance URL: $INSTANCE_URL"
echo ""

# Pre-flight checks
echo "🔍 Running pre-flight checks..."
echo ""

PREFLIGHT_FAILED=false

# Check Einstein GPT is enabled (critical) — via SOAP readMetadata
GENAI_CHECK=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>EinsteinGptSettings</met:type><met:fullNames>EinsteinGpt</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableEinsteinGptPlatform>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$GENAI_CHECK" == "true" ]]; then
  echo "  ✅ Einstein GPT enabled"
else
  echo "  ❌ Einstein GPT NOT enabled (required)"
  PREFLIGHT_FAILED=true
fi

# Check Agentforce Agent is enabled (required) — via SOAP readMetadata
COPILOT_CHECK=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>EinsteinCopilotSettings</met:type><met:fullNames>EinsteinCopilot</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableEinsteinGptCopilot>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$COPILOT_CHECK" == "true" ]]; then
  echo "  ✅ Agentforce Agent enabled"
else
  echo "  ❌ Agentforce Agent NOT enabled (required)"
  PREFLIGHT_FAILED=true
fi

# Check Agentforce Studio / Agent Platform is enabled (required) — via SOAP readMetadata.
# AgentPlatformSettings.enableAgentPlatform (OrgPreference AgentPlatformEnabled) gates
# SalesDealAgentSettings: core's DealAgentEnabledOrgPreference validates the Agentforce
# Platform preference and rejects Deal Agent enablement if it is off, so this must pass
# before we attempt the SalesDealAgent update below.
AGENT_PLATFORM_CHECK=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>AgentPlatformSettings</met:type><met:fullNames>AgentPlatform</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableAgentPlatform>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$AGENT_PLATFORM_CHECK" == "true" ]]; then
  echo "  ✅ Agentforce Studio (Agent Platform) enabled"
else
  echo "  ❌ Agentforce Studio (Agent Platform) NOT enabled (required — gates Deal Agent)"
  PREFLIGHT_FAILED=true
fi

# Check Enhanced Notes (required dependency) — via SOAP readMetadata
NOTES_CHECK=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>EnhancedNotesSettings</met:type><met:fullNames>EnhancedNotes</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableEnhancedNotes>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$NOTES_CHECK" == "true" ]]; then
  echo "  ✅ Enhanced Notes enabled"
else
  echo "  ❌ Enhanced Notes NOT enabled (required)"
  PREFLIGHT_FAILED=true
fi

# Check org edition compatibility
ORG_EDITION=$(sf data query --query "SELECT OrganizationType FROM Organization" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].OrganizationType')
echo "  ℹ️  Org Edition: $ORG_EDITION"

if [[ "$ORG_EDITION" == "Developer Edition" ]]; then
  echo "  ⚠️  Warning: Pipeline Management may have limited functionality in Developer Edition"
fi

echo ""

if [[ "$PREFLIGHT_FAILED" == "true" ]]; then
  echo "❌ Pre-flight checks failed. Run ./enable-prerequisites.sh first."
  exit 1
fi

echo "✅ Pre-flight checks passed"
echo ""

# Check if already enabled (via SOAP readMetadata — SalesDealAgentSettings is NOT queryable via SOQL)
echo -n "Checking current SalesDealAgent status... "
CURRENT_STATUS=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>SalesDealAgentSettings</met:type><met:fullNames>SalesDealAgent</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null | grep -o "<enableDealAgent>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$CURRENT_STATUS" == "true" ]]; then
  echo "✅ (already enabled)"
  echo ""
  echo "✅ Pipeline Management is already enabled"
  exit 0
fi

echo "⏳ (not enabled)"
echo ""

# Enable via SOAP API v64.0
echo "Enabling Pipeline Management via SOAP API v64.0..."
echo ""

SOAP_REQUEST=$(cat <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>{{ACCESS_TOKEN}}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type="met:SalesDealAgentSettings" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <met:fullName>SalesDealAgent</met:fullName>
        <met:enableDealAgent>true</met:enableDealAgent>
        <met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>
EOF
)

# Substitute access token
SOAP_REQUEST="${SOAP_REQUEST//\{\{ACCESS_TOKEN\}\}/$ACCESS_TOKEN}"

# Send SOAP request
RESPONSE=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=utf-8" \
  -H "SOAPAction: update" \
  -d "$SOAP_REQUEST")

# Check response
if echo "$RESPONSE" | grep -q "<success>true</success>"; then
  echo "✅ SOAP API call succeeded"
else
  echo "❌ SOAP API call failed"
  echo ""
  echo "Response:"
  echo "$RESPONSE"
  exit 1
fi

echo ""

# Verify enablement (via SOAP readMetadata)
echo "🔍 Verifying Pipeline Management is enabled..."
sleep 2  # Brief wait for propagation

VERIFY_RESULT=$(curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>SalesDealAgentSettings</met:type><met:fullNames>SalesDealAgent</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)

VERIFY_DEAL_AGENT=$(echo "$VERIFY_RESULT" | grep -o "<enableDealAgent>[^<]*" | grep -o "true\|false" || echo "")

if [[ "$VERIFY_DEAL_AGENT" == "true" ]]; then
  echo "  ✅ enableDealAgent: true"

  AUTO_APPROVE=$(echo "$VERIFY_RESULT" | grep -o "<enableDealAgentAutoApproveAllTasks>[^<]*" | grep -o "true\|false" || echo "false")
  echo "  ℹ️  enableDealAgentAutoApproveAllTasks: $AUTO_APPROVE (default: false)"

  echo ""
  echo "✅ Pipeline Management enabled successfully"
  echo ""
  echo "Next steps:"
  echo "  1. Run ./create-flow.sh $ORG_ALIAS to create the suggestion processing flow"
  echo "  2. Run ./create-agent.sh $ORG_ALIAS <bundle-path> to create and activate the agent"
else
  echo "  ❌ Verification failed"
  echo ""
  echo "Query result:"
  echo "$VERIFY_RESULT"
  exit 1
fi
