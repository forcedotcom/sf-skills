#!/bin/bash
#
# Setup Credentials Template with CSP Trusted Sites / Remote Site Settings
#
# TEMPLATE FOR CREATING NEW INTEGRATION SKILLS
#
# This template includes automatic deployment of endpoint security
# (CSP Trusted Sites or Remote Site Settings) along with credential configuration.
#
# How to use this template:
# 1. Copy to your skill: cp scripts/templates/setup-credentials-with-csp.sh my-skill/scripts/setup-credentials.sh
# 2. Replace all {{PLACEHOLDERS}} with your values
# 3. Create corresponding .cspTrustedSite-meta.xml and .remoteSite-meta.xml in assets/
# 4. Test with your API
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration - REPLACE THESE
SKILL_NAME="{{SkillName}}"              # e.g., "Bland.ai", "Stripe", "Twilio"
CUSTOM_SETTING_NAME="{{SettingName}}"  # e.g., "BlandAI", "StripeAPI", "TwilioAPI"
CSP_NAME="{{CSPName}}"                  # e.g., "BlandAPI", "StripeAPI", "TwilioAPI"
API_KEY_URL="{{APIKeyURL}}"             # e.g., "https://app.bland.ai/settings/api"

# Banner
echo -e "${CYAN}"
cat << EOF
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        ${SKILL_NAME} Integration - Credential Setup              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Usage
usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 <org-alias>"
    echo ""
    echo -e "${BLUE}Example:${NC}"
    echo "  $0 AIZoom"
    echo ""
    echo -e "${YELLOW}Get your ${SKILL_NAME} API key at:${NC}"
    echo -e "  ${CYAN}${API_KEY_URL}${NC}"
    exit 1
}

if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Missing org alias${NC}"
    echo ""
    usage
fi

ORG_ALIAS=$1

# Validate sf CLI
if ! command -v sf &> /dev/null; then
    echo -e "${RED}Error: Salesforce CLI (sf) is not installed${NC}"
    exit 1
fi

# Validate org
echo -e "${BLUE}► Validating org connection...${NC}"
if ! sf org display --target-org "$ORG_ALIAS" &> /dev/null; then
    echo -e "${RED}✗ Cannot connect to org '$ORG_ALIAS'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to org: $ORG_ALIAS${NC}"
echo ""

# Get API key
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Enter your ${SKILL_NAME} API key${NC}"
echo -e "${CYAN}Get it from: ${API_KEY_URL}${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}API Key (input hidden):${NC}"
read -s API_KEY
echo ""

if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: API key cannot be empty${NC}"
    exit 1
fi

echo -e "${GREEN}✓ API key received${NC}"
echo ""

# Configure Custom Setting (same logic as before)
echo -e "${BLUE}► Checking for API_Credentials__c Custom Setting...${NC}"
# ... [rest of Custom Setting logic - same as bland-ai-calls] ...

# Configure CSP Trusted Site / Remote Site Settings
echo -e "${BLUE}► Configuring endpoint security (CSP Trusted Sites)...${NC}"

CSP_CHECK=$(sf data query \
    --query "SELECT Id FROM CspTrustedSite WHERE DeveloperName = '${CSP_NAME}' LIMIT 1" \
    --target-org "$ORG_ALIAS" \
    --json 2>&1 || echo '{"status":1}')

if echo "$CSP_CHECK" | grep -q "sObject type 'CspTrustedSite' is not supported"; then
    # Fallback to Remote Site Settings
    echo -e "${YELLOW}⚠ CSP Trusted Sites not supported. Using Remote Site Settings...${NC}"

    REMOTE_SITE_CHECK=$(sf data query \
        --query "SELECT Id FROM RemoteSiteSetting WHERE SiteName = '${CSP_NAME}' LIMIT 1" \
        --target-org "$ORG_ALIAS" \
        --json 2>&1 || echo '{"status":1}')

    REMOTE_SITE_ID=$(echo "$REMOTE_SITE_CHECK" | jq -r '.result.records[0].Id // empty' 2>/dev/null)

    if [ -z "$REMOTE_SITE_ID" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        SKILL_DIR="$(dirname "$SCRIPT_DIR")"

        sf project deploy start \
            --source-dir "$SKILL_DIR/assets/${CSP_NAME}.remoteSite-meta.xml" \
            --target-org "$ORG_ALIAS" \
            --wait 5 > /dev/null 2>&1 || true

        echo -e "${GREEN}✓ Remote Site Setting configured${NC}"
    else
        echo -e "${GREEN}✓ Remote Site Setting already exists${NC}"
    fi
else
    CSP_ID=$(echo "$CSP_CHECK" | jq -r '.result.records[0].Id // empty' 2>/dev/null)

    if [ -z "$CSP_ID" ]; then
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        SKILL_DIR="$(dirname "$SCRIPT_DIR")"

        sf project deploy start \
            --source-dir "$SKILL_DIR/assets/${CSP_NAME}.cspTrustedSite-meta.xml" \
            --target-org "$ORG_ALIAS" \
            --wait 5 > /dev/null 2>&1 || true

        echo -e "${GREEN}✓ CSP Trusted Site configured${NC}"
    else
        echo -e "${GREEN}✓ CSP Trusted Site already exists${NC}"
    fi
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ ${SKILL_NAME} integration configured successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}🎉 Setup complete!${NC}"
