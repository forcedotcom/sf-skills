#!/bin/bash

# Enable all prerequisite settings for Pipeline Management
# Usage: ./enable-prerequisites.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

# Source shared SOAP parsing library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/shared/soap.sh"

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "❌ Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

if [[ ! -f "sfdx-project.json" ]]; then
  echo "❌ Error: sfdx-project.json not found in current directory"
  echo "Copy from ../assets/sfdx-project.json first"
  exit 1
fi

echo "🚀 Enabling Pipeline Management prerequisites for org: $ORG_ALIAS"
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

# Function to enable setting via SOAP API
enable_via_soap() {
  local SETTING_NAME="$1"
  local DISPLAY_NAME="$2"
  local FIELD_NAME="$3"
  local API_VERSION="${4:-62.0}"

  echo -n "Enabling ${DISPLAY_NAME}... "

  # Check if already enabled
  local QUERY="SELECT ${FIELD_NAME} FROM ${SETTING_NAME}"
  local CURRENT_VALUE
  CURRENT_VALUE=$(sf data query --query "$QUERY" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r ".result.records[0].${FIELD_NAME}")

  if [[ "$CURRENT_VALUE" == "true" ]]; then
    echo "✅ (already enabled)"
    return 0
  fi

  # Build SOAP request
  local SOAP_REQUEST
  SOAP_REQUEST=$(cat <<EOF
<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://soap.sforce.com/2006/04/metadata">
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type="met:${SETTING_NAME}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <met:fullName>${SETTING_NAME}</met:fullName>
        <met:${FIELD_NAME}>true</met:${FIELD_NAME}>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>
EOF
)

  # Send SOAP request
  local RESPONSE
  RESPONSE=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/${API_VERSION}" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "$SOAP_REQUEST")

  if echo "$RESPONSE" | grep -q "<success>true</success>"; then
    echo "✅"
    return 0
  else
    echo "❌"
    echo "SOAP Response: $RESPONSE"
    return 1
  fi
}

# Function to enable setting via CLI retrieve+modify+deploy
enable_via_cli() {
  local SETTING_NAME="$1"
  local DISPLAY_NAME="$2"
  local FIELD_NAME="$3"
  local FIELD_VALUE="${4:-true}"

  echo -n "Enabling ${DISPLAY_NAME}... "

  # Check if already enabled
  local QUERY="SELECT ${FIELD_NAME} FROM ${SETTING_NAME}"
  local CURRENT_VALUE
  CURRENT_VALUE=$(sf data query --query "$QUERY" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r ".result.records[0].${FIELD_NAME}" 2>/dev/null || echo "null")

  if [[ "$CURRENT_VALUE" == "$FIELD_VALUE" || "$CURRENT_VALUE" == "true" ]]; then
    echo "✅ (already enabled)"
    return 0
  fi

  # Retrieve current settings
  local SETTINGS_DIR="force-app/main/default/settings"
  mkdir -p "$SETTINGS_DIR"

  if ! sf project retrieve start --metadata "Settings:${SETTING_NAME}" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -e '.status == 0' >/dev/null 2>&1; then
    echo "❌ (retrieve failed)"
    return 1
  fi

  local SETTINGS_FILE="${SETTINGS_DIR}/${SETTING_NAME}.settings-meta.xml"

  if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "❌ (file not found after retrieve)"
    return 1
  fi

  # Modify setting using sed (non-greedy)
  if grep -q "<${FIELD_NAME}>" "$SETTINGS_FILE"; then
    # Update existing field
    sed -i.bak "0,/<${FIELD_NAME}>[^<]*<\/${FIELD_NAME}>/s|<${FIELD_NAME}>[^<]*</${FIELD_NAME}>|<${FIELD_NAME}>${FIELD_VALUE}</${FIELD_NAME}>|" "$SETTINGS_FILE"
  else
    # Insert field before closing tag
    sed -i.bak "/<\/.*Settings>/i\\
    <${FIELD_NAME}>${FIELD_VALUE}</${FIELD_NAME}>" "$SETTINGS_FILE"
  fi

  # Deploy
  if sf project deploy start --source-dir "$SETTINGS_DIR" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -e '.status == 0' >/dev/null 2>&1; then
    echo "✅"
    rm -f "${SETTINGS_FILE}.bak"
    return 0
  else
    echo "❌ (deploy failed)"
    mv "${SETTINGS_FILE}.bak" "$SETTINGS_FILE" 2>/dev/null || true
    return 1
  fi
}

# Read a settings boolean via SOAP readMetadata and classify the response using
# the shared shared/soap.sh parser. Distinguishes a genuine "false" from an
# auth/SOAP fault or a network/service error instead of collapsing all three to
# empty (the W-23215519 bug). Captures the HTTP status so 5xx/HTML error pages
# are not mistaken for a disabled setting.
# Args: $1 = metadata type, $2 = fullName, $3 = field name
# Echoes: "true" | "false" | "AUTH_ERROR:..." | "TYPE_UNAVAILABLE:..." | "NETWORK_ERROR"
read_setting_status() {
  local type="$1"
  local full_name="$2"
  local field="$3"
  local response http_status xml
  response=$(curl -s -w "\n%{http_code}" "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=UTF-8" \
    -H "SOAPAction: readMetadata" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>${type}</met:type><met:fullNames>${full_name}</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null || echo "")
  http_status=$(echo "$response" | tail -1)
  xml=$(echo "$response" | sed '$d')
  parse_soap_response "$xml" "$field" "$http_status"
}

# Read OpportunitySettings.enableOpportunityTeam via SOAP readMetadata.
# OpportunitySettings is NOT queryable via SOQL, so SOAP is the only option
# (the fullName for OpportunitySettings is "Opportunity", not the type name).
# Echoes a classification string (see read_setting_status).
get_opp_team_status() {
  read_setting_status "OpportunitySettings" "Opportunity" "enableOpportunityTeam"
}

# Step 1: Enable EinsteinGptSettings (MUST succeed for Copilot)
# NOTE: The critical field for Pipeline Management is enableEinsteinGptPlatform.
# We enable it via SOAP with the correct fullName pattern (fullName = type name for settings).
echo "Step 1: Enabling Einstein Generative AI"
echo -n "  Checking EinsteinGptSettings... "

GENAI_CURRENT=$(read_setting_status "EinsteinGptSettings" "EinsteinGpt" "enableEinsteinGptPlatform")

if [[ "$GENAI_CURRENT" == "true" ]]; then
  echo "✅ (already enabled)"
else
  echo "enabling..."
  RESULT=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:EinsteinGptSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>EinsteinGpt</met:fullName>
      <met:enableEinsteinGptPlatform>true</met:enableEinsteinGptPlatform>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    echo "  ✅ Einstein Generative AI enabled (SOAP)"
  else
    echo "  ⚠️  SOAP failed — trying CLI deploy fallback..."
    enable_via_cli "EinsteinGptSettings" "Einstein Generative AI (CLI)" "enableEinsteinGptPlatform"
    GENAI_VERIFY=$(read_setting_status "EinsteinGptSettings" "EinsteinGpt" "enableEinsteinGptPlatform")
    if [[ "$GENAI_VERIFY" != "true" ]]; then
      echo "  ❌ Critical failure: Cannot enable Einstein Generative AI (all approaches failed)"
      echo "$RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || true
      exit 1
    fi
    echo "  ✅ Einstein Generative AI enabled (CLI fallback)"
  fi
  sleep 3
fi
echo ""

# Step 2: Enable EinsteinCopilotSettings (depends on GPT)
echo "Step 2: Enabling Agentforce Agent (Einstein Copilot)"
echo -n "  Checking EinsteinCopilotSettings... "

COPILOT_CURRENT=$(read_setting_status "EinsteinCopilotSettings" "EinsteinCopilot" "enableEinsteinGptCopilot")

if [[ "$COPILOT_CURRENT" == "true" ]]; then
  echo "✅ (already enabled)"
else
  echo "enabling..."
  RESULT=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:EinsteinCopilotSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>EinsteinCopilot</met:fullName>
      <met:enableEinsteinGptCopilot>true</met:enableEinsteinGptCopilot>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    echo "  ✅ Agentforce Agent enabled (SOAP)"
  else
    echo "  ⚠️  SOAP failed — trying CLI deploy fallback..."
    enable_via_cli "EinsteinCopilotSettings" "Agentforce Agent (CLI)" "enableEinsteinGptCopilot"
    COPILOT_VERIFY=$(read_setting_status "EinsteinCopilotSettings" "EinsteinCopilot" "enableEinsteinGptCopilot")
    if [[ "$COPILOT_VERIFY" != "true" ]]; then
      echo "  ⚠️  Warning: Agentforce Agent enable failed (all approaches — continuing)"
      echo "$RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || true
    else
      echo "  ✅ Agentforce Agent enabled (CLI fallback)"
    fi
  fi
  sleep 3
fi
echo ""

# Step 2b: Enable AgentPlatformSettings (Agentforce Studio — gates Deal Agent)
# AgentPlatformSettings.enableAgentPlatform (OrgPreference AgentPlatformEnabled)
# must be ON before SalesDealAgentSettings can be enabled; core rejects Deal Agent
# enablement otherwise. Depends on Einstein GPT + Copilot (Steps 1–2).
echo "Step 2b: Enabling Agentforce Studio (Agent Platform)"
echo -n "  Checking AgentPlatformSettings... "

AGENT_PLATFORM_CURRENT=$(read_setting_status "AgentPlatformSettings" "AgentPlatform" "enableAgentPlatform")

if [[ "$AGENT_PLATFORM_CURRENT" == "true" ]]; then
  echo "✅ (already enabled)"
else
  echo "enabling..."
  RESULT=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:AgentPlatformSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>AgentPlatform</met:fullName>
      <met:enableAgentPlatform>true</met:enableAgentPlatform>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    echo "  ✅ Agentforce Studio (Agent Platform) enabled (SOAP)"
  else
    echo "  ⚠️  SOAP failed — trying CLI deploy fallback..."
    enable_via_cli "AgentPlatformSettings" "Agentforce Studio (CLI)" "enableAgentPlatform"
    AGENT_PLATFORM_VERIFY=$(read_setting_status "AgentPlatformSettings" "AgentPlatform" "enableAgentPlatform")
    if [[ "$AGENT_PLATFORM_VERIFY" != "true" ]]; then
      echo "  ⚠️  Warning: Agentforce Studio enable failed (all approaches — continuing)"
      echo "$RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || true
    else
      echo "  ✅ Agentforce Studio (Agent Platform) enabled (CLI fallback)"
    fi
  fi
  sleep 3
fi
echo ""

# Step 3: Enable Enhanced Notes (required for Pipeline Management data sources)
echo "Step 3: Enabling Enhanced Notes"
echo -n "  Checking EnhancedNotesSettings... "

NOTES_CURRENT=$(read_setting_status "EnhancedNotesSettings" "EnhancedNotes" "enableEnhancedNotes")

if [[ "$NOTES_CURRENT" == "true" ]]; then
  echo "✅ (already enabled)"
else
  echo "enabling..."
  RESULT=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:EnhancedNotesSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>EnhancedNotes</met:fullName>
      <met:enableEnhancedNotes>true</met:enableEnhancedNotes>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>")

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    echo "  ✅ Enhanced Notes enabled"
  else
    echo "  ⚠️  SOAP failed — trying CLI deploy fallback..."
    enable_via_cli "EnhancedNotesSettings" "Enhanced Notes" "enableEnhancedNotes" || echo "  ❌ Enhanced Notes failed (Pipeline Management may not activate)"
  fi
  sleep 2
fi
echo ""

# Step 4: Enable Email Administration (CLI is OK, handle compliance field removal)
echo "Step 4: Enabling Email Administration"
if ! enable_via_cli "EmailAdministrationSettings" "Email Administration" "enableInternalNotesInEmailSnippet"; then
  echo "⚠️  Retrying without enableEmailSenderIdCompliance..."

  # Retrieve again
  sf project retrieve start --metadata "Settings:EmailAdministrationSettings" --target-org "$ORG_ALIAS" >/dev/null 2>&1 || true

  SETTINGS_FILE="force-app/main/default/settings/EmailAdministrationSettings.settings-meta.xml"

  if [[ -f "$SETTINGS_FILE" ]]; then
    # Remove problematic field if present
    sed -i.bak '/<enableEmailSenderIdCompliance>/d' "$SETTINGS_FILE"

    # Ensure enableInternalNotesInEmailSnippet is true
    if grep -q "<enableInternalNotesInEmailSnippet>" "$SETTINGS_FILE"; then
      sed -i.bak2 "0,/<enableInternalNotesInEmailSnippet>[^<]*<\/enableInternalNotesInEmailSnippet>/s|<enableInternalNotesInEmailSnippet>[^<]*</enableInternalNotesInEmailSnippet>|<enableInternalNotesInEmailSnippet>true</enableInternalNotesInEmailSnippet>|" "$SETTINGS_FILE"
    fi

    sf project deploy start --source-dir "force-app/main/default/settings" --target-org "$ORG_ALIAS" >/dev/null 2>&1 || true
    rm -f "${SETTINGS_FILE}.bak" "${SETTINGS_FILE}.bak2" 2>/dev/null || true
  fi
fi
echo ""

# Step 5: Enable Opportunity Team (CRITICAL — flow uses OpportunityTeamMember)
# Without this, the Pipeline Management flow deploy fails with an OppTeamMemRec error.
# OpportunitySettings is NOT queryable via SOQL, so we use SOAP readMetadata/update
# (matching Steps 1-3 and setup-all.sh). The fullName for OpportunitySettings is
# "Opportunity", not the type name.
echo "Step 5: Enabling Opportunity Team"
echo -n "  Checking OpportunitySettings.enableOpportunityTeam... "

OPP_TEAM_CURRENT=$(get_opp_team_status)

if [[ "$OPP_TEAM_CURRENT" == "true" ]]; then
  echo "✅ (already enabled)"
else
  echo "enabling..."
  RESULT=$(curl -s -X POST "${INSTANCE_URL}/services/Soap/m/64.0" \
    -H "Content-Type: text/xml; charset=utf-8" \
    -H "SOAPAction: update" \
    -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:OpportunitySettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>Opportunity</met:fullName>
      <met:enableOpportunityTeam>true</met:enableOpportunityTeam>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" 2>/dev/null)

  if echo "$RESULT" | grep -q "<success>true</success>"; then
    echo "  ✅ Opportunity Team enabled"
  else
    echo "  ❌ Opportunity Team enable failed — verifying below..."
    echo "$RESULT" | grep -o '<message>[^<]*</message>' | sed 's/<[^>]*>//g' | head -1 || true
    echo "     Note: cannot coexist with Opportunity Splits — disable Splits first if enabled."
  fi
  sleep 2
fi
echo ""

# Step 6: Enable Opportunity settings (Find Similar Opportunities — optional)
echo "Step 6: Enabling Opportunity Settings"
enable_via_cli "OpportunitySettings" "Opportunity Settings" "enableFindSimilarOpportunities" || echo "⚠️  Warning: Opportunity Settings failed but continuing..."
echo ""

# Verification — use SOAP readMetadata (matches enable-deal-agent.sh pre-flight checks)
echo "🔍 Verifying prerequisites via SOAP readMetadata..."
echo ""

VERIFICATION_FAILED=false

# Report a verification status classified by shared/soap.sh. Distinguishes a
# genuine disabled setting from an auth fault or a network/service error so the
# operator knows whether to re-auth, check connectivity, or actually enable the
# setting (the W-23215519 fix). Args: $1=label, $2=status string, $3=severity
#   severity "critical" → sets VERIFICATION_FAILED on a real "false"
#   severity "warn"     → reports but never blocks
report_status() {
  local label="$1"
  local status="$2"
  local severity="$3"
  case "$status" in
    true)
      echo "  ✅ ${label}: enabled"
      ;;
    false)
      if [[ "$severity" == "critical" ]]; then
        echo "  ❌ ${label}: NOT enabled (CRITICAL)"
        VERIFICATION_FAILED=true
      else
        echo "  ⚠️  ${label}: NOT enabled"
      fi
      ;;
    AUTH_ERROR:*)
      echo "  ❌ ${label}: cannot verify — authentication/SOAP fault (${status#AUTH_ERROR:})"
      echo "     Re-authenticate: sf org login web --instance-url $INSTANCE_URL --alias $ORG_ALIAS"
      # if/then/fi (not `[[ ]] && ...`): a bare `&&` would return 1 when severity
      # is "warn", and as the case arm's last statement that makes report_status
      # return 1 — aborting the script at the bare warn call sites under set -e.
      if [[ "$severity" == "critical" ]]; then VERIFICATION_FAILED=true; fi
      ;;
    TYPE_UNAVAILABLE:*)
      echo "  ❌ ${label}: not available in this org edition (${status#TYPE_UNAVAILABLE:})"
      if [[ "$severity" == "critical" ]]; then VERIFICATION_FAILED=true; fi
      ;;
    NETWORK_ERROR)
      echo "  ❌ ${label}: cannot verify — network/service error (check instance URL and connectivity)"
      if [[ "$severity" == "critical" ]]; then VERIFICATION_FAILED=true; fi
      ;;
    *)
      echo "  ⚠️  ${label}: unknown status ($status)"
      ;;
  esac
}

# Verify Einstein GPT (critical — checked by enable-deal-agent.sh pre-flight)
VERIFY_GENAI=$(read_setting_status "EinsteinGptSettings" "EinsteinGpt" "enableEinsteinGptPlatform")
report_status "Einstein Generative AI (enableEinsteinGptPlatform)" "$VERIFY_GENAI" "critical"

# Verify Einstein Copilot (checked by enable-deal-agent.sh pre-flight)
VERIFY_COPILOT=$(read_setting_status "EinsteinCopilotSettings" "EinsteinCopilot" "enableEinsteinGptCopilot")
report_status "Agentforce Agent (enableEinsteinGptCopilot)" "$VERIFY_COPILOT" "warn"

# Verify Agentforce Studio / Agent Platform (gates Deal Agent; enable-deal-agent.sh
# pre-flight hard-blocks on this — a disabled state here explains a downstream
# Deal Agent activation failure).
VERIFY_AGENT_PLATFORM=$(read_setting_status "AgentPlatformSettings" "AgentPlatform" "enableAgentPlatform")
report_status "Agentforce Studio / Agent Platform (enableAgentPlatform)" "$VERIFY_AGENT_PLATFORM" "warn"

# Verify Enhanced Notes (checked by enable-deal-agent.sh pre-flight)
VERIFY_NOTES=$(read_setting_status "EnhancedNotesSettings" "EnhancedNotes" "enableEnhancedNotes")
report_status "Enhanced Notes (enableEnhancedNotes)" "$VERIFY_NOTES" "warn"

# Verify Opportunity Team (CRITICAL — PM flow deploy fails with OppTeamMemRec error
# without it). OpportunitySettings is not queryable via SOQL — use SOAP readMetadata.
VERIFY_OPP_TEAM=$(get_opp_team_status)
if [[ "$VERIFY_OPP_TEAM" != "true" ]]; then
  report_status "Opportunity Team (enableOpportunityTeam)" "$VERIFY_OPP_TEAM" "critical"
  echo "     The Pipeline Management flow requires OpportunityTeamMember access;"
  echo "     without it, flow deployment fails with an OppTeamMemRec error."
  echo "     Note: cannot coexist with Opportunity Splits — disable Splits first if enabled."
else
  report_status "Opportunity Team (enableOpportunityTeam)" "$VERIFY_OPP_TEAM" "critical"
fi

# Verify Email Administration (best-effort, not blocking)
VERIFY_EMAIL=$(sf data query --query "SELECT enableEnhancedEmailEnabled FROM EmailAdministrationSettings" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].enableEnhancedEmailEnabled // "unknown"' 2>/dev/null || echo "unknown")
if [[ "$VERIFY_EMAIL" == "true" ]]; then
  echo "  ✅ Enhanced Email: enabled"
else
  echo "  ⚠️  Enhanced Email: not enabled (optional — email body indexing)"
fi

# Verify Opportunity Settings (best-effort, not blocking)
VERIFY_OPP=$(sf data query --query "SELECT enableFindSimilarOpportunities FROM OpportunitySettings" --target-org "$ORG_ALIAS" --json 2>/dev/null | jq -r '.result.records[0].enableFindSimilarOpportunities // "unknown"' 2>/dev/null || echo "unknown")
if [[ "$VERIFY_OPP" == "true" ]]; then
  echo "  ✅ Opportunity Settings: enabled"
else
  echo "  ⚠️  Opportunity Settings: not enabled (optional)"
fi

echo ""

if [[ "$VERIFICATION_FAILED" == "true" ]]; then
  echo "❌ Critical prerequisites failed. Cannot proceed to Deal Agent setup."
  exit 1
fi

echo "✅ All prerequisites enabled successfully"
echo ""
echo "Next step: Run ./enable-deal-agent.sh $ORG_ALIAS"
