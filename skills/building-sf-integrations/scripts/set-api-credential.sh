#!/bin/bash
#
# set-api-credential.sh
#
# Simple script to set API credentials programmatically using Custom Settings
# Alternative to Named Credentials that allows full automation
#
# Usage:
#   ./set-api-credential.sh <setting-name> <api-key> <org-alias>
#
# Example:
#   ./set-api-credential.sh BlandAI sk_live_abc123 AIZoom
#
# For Named Credentials, use this to store the API key in a Custom Setting,
# then reference it in your Apex code
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 <setting-name> <api-key> <org-alias>"
    echo ""
    echo -e "${BLUE}Example:${NC}"
    echo "  $0 BlandAI sk_live_abc123xyz AIZoom"
    echo ""
    echo -e "${BLUE}Or use secure input (recommended):${NC}"
    echo "  $0 BlandAI - AIZoom"
    echo "  (Script will prompt for API key securely)"
    exit 1
}

if [ $# -ne 3 ]; then
    usage
fi

SETTING_NAME=$1
API_KEY=$2
ORG_ALIAS=$3

# If API key is "-", prompt securely
if [ "$API_KEY" = "-" ]; then
    echo -e "${YELLOW}Enter API key (input hidden):${NC}"
    read -s API_KEY
    echo ""
fi

# Validate inputs
if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: API key cannot be empty${NC}"
    exit 1
fi

# Validate org
echo -e "${BLUE}Validating org connection...${NC}"
if ! sf org display --target-org "$ORG_ALIAS" &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to org '$ORG_ALIAS'${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Connected to org: $ORG_ALIAS${NC}"

# Check if Custom Setting exists
echo -e "${BLUE}Checking for API_Credentials__c Custom Setting...${NC}"

SETTING_CHECK=$(sf data query \
    --query "SELECT Id FROM API_Credentials__c WHERE Name = '$SETTING_NAME' LIMIT 1" \
    --target-org "$ORG_ALIAS" \
    --json 2>&1 || echo '{"status":1}')

if echo "$SETTING_CHECK" | grep -q "sObject type 'API_Credentials__c' is not supported"; then
    echo -e "${YELLOW}⚠️  API_Credentials__c Custom Setting not found${NC}"
    echo ""
    echo -e "${BLUE}Creating Custom Setting...${NC}"

    # Create the Custom Setting metadata
    mkdir -p force-app/main/default/objects/API_Credentials__c

    cat > force-app/main/default/objects/API_Credentials__c/API_Credentials__c.object-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <enableFeeds>false</enableFeeds>
    <label>API Credentials</label>
    <visibility>Protected</visibility>
</CustomObject>
EOF

    cat > force-app/main/default/objects/API_Credentials__c/fields/API_Key__c.field-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>API_Key__c</fullName>
    <label>API Key</label>
    <type>Text</type>
    <length>255</length>
    <required>false</required>
</CustomField>
EOF

    echo -e "${BLUE}Deploying Custom Setting...${NC}"
    sf project deploy start \
        --source-dir force-app/main/default/objects/API_Credentials__c \
        --target-org "$ORG_ALIAS" \
        --wait 10

    echo -e "${GREEN}✓ Custom Setting created${NC}"
fi

# Insert or update the credential
EXISTING_ID=$(echo "$SETTING_CHECK" | jq -r '.result.records[0].Id // empty' 2>/dev/null)

if [ -z "$EXISTING_ID" ]; then
    echo -e "${BLUE}Creating new credential record...${NC}"
    sf data create record \
        --sobject API_Credentials__c \
        --values "Name='$SETTING_NAME' API_Key__c='$API_KEY'" \
        --target-org "$ORG_ALIAS"
    echo -e "${GREEN}✓ Credential created${NC}"
else
    echo -e "${BLUE}Updating existing credential...${NC}"
    sf data update record \
        --sobject API_Credentials__c \
        --record-id "$EXISTING_ID" \
        --values "API_Key__c='$API_KEY'" \
        --target-org "$ORG_ALIAS"
    echo -e "${GREEN}✓ Credential updated${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ API Credential configured successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}How to use in Apex:${NC}"
echo ""
echo -e "${YELLOW}API_Credentials__c cred = API_Credentials__c.getInstance('$SETTING_NAME');${NC}"
echo -e "${YELLOW}String apiKey = cred.API_Key__c;${NC}"
echo -e "${YELLOW}req.setHeader('Authorization', apiKey);${NC}"
echo ""
