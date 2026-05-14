#!/bin/bash
# check-prerequisites.sh - Verify generating-visual-diagrams requirements before use
# Returns 0 if all required checks pass, 1 if any required fail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GRAY='\033[0;90m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  📸 SF-IMAGEN PREREQUISITES CHECK${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GRAY}  REQUIRED:${NC}"

# Check 1: macOS (required for Preview app)
echo -n "  Checking macOS (for Preview app)... "
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${GREEN}✓ macOS detected${NC}"
else
    echo -e "${RED}✗ Not macOS${NC}"
    echo -e "    ${YELLOW}→ generating-visual-diagrams uses macOS Preview app for image display${NC}"
    echo -e "    ${YELLOW}→ Current OS: $OSTYPE${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Gemini API Key
echo -n "  Checking GEMINI_API_KEY... "
if [[ -n "$GEMINI_API_KEY" ]]; then
    # Mask the key for display
    MASKED_KEY="${GEMINI_API_KEY:0:10}...${GEMINI_API_KEY: -4}"
    echo -e "${GREEN}✓ Set ($MASKED_KEY)${NC}"
else
    echo -e "${RED}✗ Not set${NC}"
    echo -e "    ${YELLOW}→ Nano Banana Pro requires a personal API key${NC}"
    echo -e "    ${YELLOW}→ Get one at: https://aistudio.google.com/apikey${NC}"
    echo -e "    ${YELLOW}→ Add to ~/.zshrc: export GEMINI_API_KEY=\"your-key\"${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Gemini CLI
echo -n "  Checking Gemini CLI... "
if command -v gemini &> /dev/null; then
    GEMINI_VERSION=$(gemini --version 2>/dev/null | head -1 || echo "installed")
    echo -e "${GREEN}✓ $GEMINI_VERSION${NC}"
else
    echo -e "${RED}✗ Not installed${NC}"
    echo -e "    ${YELLOW}→ Install: npm install -g @google/gemini-cli${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Nano Banana Extension
echo -n "  Checking Nano Banana extension... "
if gemini extensions list 2>/dev/null | grep -q "nanobanana"; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not installed${NC}"
    echo -e "    ${YELLOW}→ Install: gemini extensions install nanobanana${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo -e "${GRAY}  OPTIONAL (for 4K/editing via Python script):${NC}"

# Check 5: uv (optional, for Python script)
echo -n "  Checking uv (Python runner)... "
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1 | head -1)
    echo -e "${GREEN}✓ $UV_VERSION${NC}"
else
    echo -e "${YELLOW}○ Not installed (optional)${NC}"
    echo -e "    ${GRAY}→ For 4K resolution/editing: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [[ $ERRORS -eq 0 ]]; then
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "  ${GREEN}✅ All required prerequisites met!${NC}"
        echo -e "  ${YELLOW}⚠️  $WARNINGS optional feature(s) unavailable${NC}"
    else
        echo -e "  ${GREEN}✅ All prerequisites met! generating-visual-diagrams is ready to use.${NC}"
    fi
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    exit 0
else
    echo -e "  ${RED}❌ $ERRORS required prerequisite(s) missing.${NC}"
    echo -e "  ${RED}   Please fix before using generating-visual-diagrams.${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    exit 1
fi
