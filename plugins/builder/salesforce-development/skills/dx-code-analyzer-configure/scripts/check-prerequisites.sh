#!/bin/bash
# check-prerequisites.sh
# Checks all Code Analyzer prerequisites and reports status.
# Usage: bash <skill_dir>/scripts/check-prerequisites.sh
#
# Exit codes:
#   0 = All prerequisites met
#   1 = Some prerequisites missing (details in output)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

PASS="${GREEN}PASS${NC}"
FAIL="${RED}FAIL${NC}"
WARN="${YELLOW}WARN${NC}"

MISSING_COUNT=0
WARNINGS_COUNT=0

echo "========================================="
echo "  Code Analyzer Prerequisites Check"
echo "========================================="
echo ""

# --- Check sf CLI ---
echo -n "Salesforce CLI (sf): "
if command -v sf &> /dev/null; then
    SF_VERSION=$(sf --version 2>&1 | head -1)
    echo -e "${PASS} - ${SF_VERSION}"
else
    echo -e "${FAIL} - Not installed"
    echo "  Install: npm install -g @salesforce/cli"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi

# --- Check Code Analyzer Plugin ---
echo -n "Code Analyzer plugin: "
if command -v sf &> /dev/null; then
    CA_VERSION=$(sf plugins --core 2>&1 | grep -i "code-analyzer" | head -1)
    if [ -n "$CA_VERSION" ]; then
        echo -e "${PASS} - ${CA_VERSION}"
    else
        echo -e "${FAIL} - Not installed"
        echo "  Install: sf plugins install @salesforce/plugin-code-analyzer"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
else
    echo -e "${FAIL} - Cannot check (sf CLI missing)"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi

# --- Check Java ---
echo -n "Java 11+ (PMD, CPD, SFGE): "
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -1)
    # Extract major version number
    JAVA_MAJOR=$(java -version 2>&1 | head -1 | sed -E 's/.*"([0-9]+)\..*/\1/')
    if [ "$JAVA_MAJOR" -ge 11 ] 2>/dev/null; then
        echo -e "${PASS} - ${JAVA_VERSION}"
    else
        echo -e "${WARN} - ${JAVA_VERSION} (need 11+)"
        echo "  Upgrade: brew install openjdk@11"
        WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
    fi
else
    echo -e "${FAIL} - Not installed"
    echo "  Install: brew install openjdk@11 (macOS) / sdk install java 11.0.x-tem"
    echo "  Needed for: PMD, CPD, SFGE engines"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi

# --- Check JAVA_HOME ---
echo -n "JAVA_HOME: "
if [ -n "${JAVA_HOME:-}" ]; then
    echo -e "${PASS} - ${JAVA_HOME}"
else
    echo -e "${WARN} - Not set (may cause issues with some Java installations)"
    WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
fi

# --- Check Node.js ---
echo -n "Node.js 18+ (ESLint, RetireJS): "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed -E 's/v([0-9]+)\..*/\1/')
    if [ "$NODE_MAJOR" -ge 18 ] 2>/dev/null; then
        echo -e "${PASS} - ${NODE_VERSION}"
    else
        echo -e "${WARN} - ${NODE_VERSION} (need 18+)"
        echo "  Upgrade: nvm install 20 && nvm use 20"
        WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
    fi
else
    echo -e "${FAIL} - Not installed"
    echo "  Install: brew install node@20 (macOS) / nvm install 20"
    echo "  Needed for: ESLint, RetireJS engines"
    MISSING_COUNT=$((MISSING_COUNT + 1))
fi

# --- Check Python 3 ---
echo -n "Python 3 (Flow engine): "
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    echo -e "${PASS} - ${PY_VERSION}"
else
    echo -e "${WARN} - Not installed (only needed for Flow scanning)"
    echo "  Install: brew install python3 (macOS) / apt install python3 (Linux)"
    echo "  Needed for: Flow engine only"
    WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
fi

# --- Check authenticated org ---
echo -n "Authenticated Org (ApexGuru): "
if command -v sf &> /dev/null; then
    ORG_INFO=$(sf org display 2>&1)
    if echo "$ORG_INFO" | grep -qi "username\|access token"; then
        ORG_USER=$(echo "$ORG_INFO" | grep -i "username" | head -1 | awk '{print $NF}')
        echo -e "${PASS} - ${ORG_USER}"
    else
        echo -e "${WARN} - No default org (only needed for ApexGuru)"
        echo "  Login: sf org login web --alias my-org"
        WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
    fi
else
    echo -e "${WARN} - Cannot check (sf CLI missing)"
    WARNINGS_COUNT=$((WARNINGS_COUNT + 1))
fi

# --- Check for existing config ---
echo ""
echo "-----------------------------------------"
echo -n "Config file (code-analyzer.yml): "
if [ -f "code-analyzer.yml" ] || [ -f "code-analyzer.yaml" ]; then
    CONFIG_FILE=$(ls code-analyzer.yml code-analyzer.yaml 2>/dev/null | head -1)
    echo -e "${PASS} - Found: ${CONFIG_FILE}"
else
    echo -e "${WARN} - Not found (will use defaults)"
    echo "  Generate: sf code-analyzer config --output-file code-analyzer.yml"
fi

# --- Check project type ---
echo -n "Project type: "
HAS_APEX=false
HAS_LWC=false
HAS_FLOWS=false
HAS_SFDX=false

[ -d "force-app" ] && HAS_APEX=true
find . -maxdepth 4 -path "*/lwc/*" -name "*.js" 2>/dev/null | head -1 | grep -q . && HAS_LWC=true
find . -maxdepth 4 -name "*.flow-meta.xml" 2>/dev/null | head -1 | grep -q . && HAS_FLOWS=true
[ -f "sfdx-project.json" ] || [ -f "sf-project.json" ] && HAS_SFDX=true

PROJECT_TYPES=""
[ "$HAS_APEX" = true ] && PROJECT_TYPES="${PROJECT_TYPES}Apex, "
[ "$HAS_LWC" = true ] && PROJECT_TYPES="${PROJECT_TYPES}LWC, "
[ "$HAS_FLOWS" = true ] && PROJECT_TYPES="${PROJECT_TYPES}Flows, "
[ "$HAS_SFDX" = true ] && PROJECT_TYPES="${PROJECT_TYPES}SFDX Project, "

if [ -n "$PROJECT_TYPES" ]; then
    echo "${PROJECT_TYPES%, }"
else
    echo "Unknown (no Salesforce project markers found)"
fi

# --- Summary ---
echo ""
echo "========================================="
echo "  Summary"
echo "========================================="

if [ $MISSING_COUNT -eq 0 ] && [ $WARNINGS_COUNT -eq 0 ]; then
    echo -e "${GREEN}All prerequisites met! Ready to scan.${NC}"
    exit 0
elif [ $MISSING_COUNT -eq 0 ]; then
    echo -e "${YELLOW}${WARNINGS_COUNT} warning(s) - some engines may not work.${NC}"
    echo "Core functionality (PMD, ESLint) should work if Java and Node.js are available."
    exit 0
else
    echo -e "${RED}${MISSING_COUNT} required prerequisite(s) missing.${NC}"
    [ $WARNINGS_COUNT -gt 0 ] && echo -e "${YELLOW}${WARNINGS_COUNT} additional warning(s).${NC}"
    echo ""
    echo "Install missing prerequisites before running Code Analyzer."
    exit 1
fi
