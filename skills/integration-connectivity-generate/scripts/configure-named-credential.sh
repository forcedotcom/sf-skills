#!/bin/bash
#
# configure-named-credential.sh
#
# Modern script to configure Enhanced Named Credentials with External Credentials
# Uses ConnectApi.NamedCredentials.createCredential() for secure credential storage
#
# PREREQUISITES:
#   1. External Credential metadata deployed (.externalCredential-meta.xml)
#   2. Named Credential metadata deployed (.namedCredential-meta.xml)
#   3. CSP Trusted Site OR Remote Site Setting deployed
#
# Usage:
#   ./configure-named-credential.sh <external-credential-name> <principal-name> <org-alias>
#
# Example:
#   ./configure-named-credential.sh VisualCrossingWeather weatherAPIKey AIZoom
#
# The script will:
#   1. Prompt for API key securely (won't echo to terminal)
#   2. Generate Apex code to configure the credential
#   3. Execute the Apex code to store the credential securely
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Usage function
usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 <external-credential-name> <principal-name> <org-alias>"
    echo ""
    echo -e "${BLUE}Parameters:${NC}"
    echo "  external-credential-name  - Developer name of the External Credential"
    echo "  principal-name           - Principal name (from External Credential metadata)"
    echo "  org-alias                - Org alias for deployment"
    echo ""
    echo -e "${BLUE}Example:${NC}"
    echo "  $0 VisualCrossingWeather weatherAPIKey AIZoom"
    echo ""
    echo -e "${BLUE}Available External Credentials in this project:${NC}"
    find . -name "*.externalCredential-meta.xml" -type f 2>/dev/null | while read file; do
        basename "$file" .externalCredential-meta.xml | sed 's/^/  - /'
    done
    echo ""
    echo -e "${BLUE}Available Orgs:${NC}"
    sf org list --json 2>/dev/null | jq -r '.result.nonScratchOrgs[]? | "  - \(.alias // .username) (\(.username))"' 2>/dev/null || echo "  Run 'sf org list' to see available orgs"
    echo ""
    echo -e "${CYAN}Order of Operations:${NC}"
    echo "  1. Deploy External Credential metadata"
    echo "  2. Deploy Named Credential metadata (references External Credential)"
    echo "  3. Deploy CSP Trusted Site OR Remote Site Setting"
    echo "  4. Run THIS script to set the API key"
    exit 1
}

# Check arguments
if [ $# -ne 3 ]; then
    echo -e "${RED}Error: Wrong number of arguments${NC}"
    echo ""
    usage
fi

EXTERNAL_CREDENTIAL_NAME=$1
PRINCIPAL_NAME=$2
ORG_ALIAS=$3

# Validate sf CLI is installed
if ! command -v sf &> /dev/null; then
    echo -e "${RED}Error: Salesforce CLI (sf) is not installed${NC}"
    echo "Install from: https://developer.salesforce.com/tools/salesforcecli"
    exit 1
fi

# Banner
echo -e "${CYAN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     Enhanced Named Credential Configuration Tool            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Validate org exists
echo -e "${BLUE}► Validating org connection...${NC}"
if ! sf org display --target-org "$ORG_ALIAS" &> /dev/null; then
    echo -e "${RED}✗ Cannot connect to org '$ORG_ALIAS'${NC}"
    echo "Run: sf org list"
    exit 1
fi

echo -e "${GREEN}✓ Connected to org: $ORG_ALIAS${NC}"
echo ""

# Verify External Credential exists
echo -e "${BLUE}► Checking External Credential...${NC}"
EXT_CRED_CHECK=$(sf data query \
    --query "SELECT Id, DeveloperName FROM ExternalCredential WHERE DeveloperName = '$EXTERNAL_CREDENTIAL_NAME' LIMIT 1" \
    --target-org "$ORG_ALIAS" \
    --json 2>&1 || echo '{"status":1}')

EXT_CRED_ID=$(echo "$EXT_CRED_CHECK" | jq -r '.result.records[0].Id // empty' 2>/dev/null)

if [ -z "$EXT_CRED_ID" ]; then
    echo -e "${RED}✗ External Credential '$EXTERNAL_CREDENTIAL_NAME' not found${NC}"
    echo ""
    echo "Deploy it first:"
    echo "  sf project deploy start --source-dir force-app/main/default/externalCredentials/${EXTERNAL_CREDENTIAL_NAME}.externalCredential-meta.xml --target-org $ORG_ALIAS"
    exit 1
fi

echo -e "${GREEN}✓ Found External Credential (ID: $EXT_CRED_ID)${NC}"
echo ""

# Prompt for API key (securely - won't echo to terminal)
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Enter API Key for '$EXTERNAL_CREDENTIAL_NAME'${NC}"
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

# Generate Apex code to configure credential
echo -e "${BLUE}► Generating Apex code to configure credential...${NC}"

TEMP_APEX=$(mktemp /tmp/set-credential-XXXXXX.apex)

cat > "$TEMP_APEX" << EOF
// Auto-generated by configure-named-credential.sh
// Configures External Credential: $EXTERNAL_CREDENTIAL_NAME

// Define the new credential input
ConnectApi.CredentialInput newCredentials = new ConnectApi.CredentialInput();

// Specify the External Credential
newCredentials.externalCredential = '$EXTERNAL_CREDENTIAL_NAME';

// Set authentication protocol
newCredentials.authenticationProtocol = ConnectApi.CredentialAuthenticationProtocol.Custom;

// Define the principal
newCredentials.principalType = ConnectApi.CredentialPrincipalType.NamedPrincipal;
newCredentials.principalName = '$PRINCIPAL_NAME';

// Create credentials map
Map<String, ConnectApi.CredentialValueInput> creds = new Map<String, ConnectApi.CredentialValueInput>();

// Create API key parameter
ConnectApi.CredentialValueInput apiKeyParam = new ConnectApi.CredentialValueInput();
apiKeyParam.encrypted = true; // Required for security
apiKeyParam.value = '$API_KEY';

// Add to credentials map
creds.put('apiKey', apiKeyParam);

// Assign to credential input
newCredentials.credentials = creds;

try {
    // Create the credential (first-time setup)
    ConnectApi.NamedCredentials.createCredential(newCredentials);
    System.debug('✓ External Credential configured successfully!');
    System.debug('Principal: $PRINCIPAL_NAME');
} catch (Exception e) {
    // If already exists, try patching instead
    if (e.getMessage().contains('already exists')) {
        try {
            ConnectApi.NamedCredentials.patchCredential(newCredentials);
            System.debug('✓ External Credential updated successfully!');
            System.debug('Principal: $PRINCIPAL_NAME');
        } catch (Exception e2) {
            System.debug('✗ Error updating credential: ' + e2.getMessage());
            throw e2;
        }
    } else {
        System.debug('✗ Error creating credential: ' + e.getMessage());
        throw e;
    }
}
EOF

echo -e "${GREEN}✓ Apex code generated${NC}"
echo ""

# Execute Apex code
echo -e "${BLUE}► Executing Apex code to configure credential...${NC}"

APEX_RESULT=$(sf apex run --file "$TEMP_APEX" --target-org "$ORG_ALIAS" 2>&1)

# Check if successful
if echo "$APEX_RESULT" | grep -q "✓ External Credential"; then
    echo -e "${GREEN}✓ Credential configured successfully!${NC}"

    # Cleanup temp file
    rm -f "$TEMP_APEX"

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ Configuration Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}What was configured:${NC}"
    echo "  • External Credential: $EXTERNAL_CREDENTIAL_NAME"
    echo "  • Principal: $PRINCIPAL_NAME"
    echo "  • Org: $ORG_ALIAS"
    echo ""
    echo -e "${BLUE}You can now use the Named Credential in your callouts!${NC}"
    echo ""
else
    echo -e "${RED}✗ Failed to configure credential${NC}"
    echo ""
    echo -e "${YELLOW}Apex execution output:${NC}"
    echo "$APEX_RESULT"
    echo ""
    echo -e "${YELLOW}Temp Apex file saved at: $TEMP_APEX${NC}"
    echo "Review the file and run manually if needed"
    exit 1
fi
