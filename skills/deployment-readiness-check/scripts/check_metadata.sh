#!/bin/bash
# Metadata validation script for Salesforce deployments
# Checks for common issues before deployment

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "=========================================="
echo "Salesforce Metadata Validation"
echo "=========================================="
echo ""

# Check if we're in an SFDX project
if [ ! -f "sfdx-project.json" ]; then
    echo -e "${RED}ERROR: Not in an SFDX project directory${NC}"
    echo "Please run this script from your project root"
    exit 1
fi

echo "✓ Found SFDX project"
echo ""

# 1. Check XML format
echo "Checking XML format..."
XML_ERRORS=0

find force-app -name "*.xml" -o -name "*.object" -o -name "*.layout" | while read file; do
    if ! xmllint --noout "$file" 2>/dev/null; then
        echo -e "${RED}✗ Invalid XML: $file${NC}"
        XML_ERRORS=$((XML_ERRORS + 1))
    fi
done

if [ $XML_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All XML files are well-formed${NC}"
else
    echo -e "${RED}✗ Found $XML_ERRORS XML errors${NC}"
    ERRORS=$((ERRORS + XML_ERRORS))
fi
echo ""

# 2. Check API versions
echo "Checking API versions..."
MIN_API_VERSION=56.0

find force-app -name "*.cls-meta.xml" -o -name "*.trigger-meta.xml" | while read file; do
    VERSION=$(grep -o '<apiVersion>[0-9.]*</apiVersion>' "$file" | grep -o '[0-9.]*')
    if [ -n "$VERSION" ] && (( $(echo "$VERSION < $MIN_API_VERSION" | bc -l) )); then
        echo -e "${YELLOW}⚠ Old API version $VERSION in: $file${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

echo -e "${GREEN}✓ API version check complete${NC}"
echo ""

# 3. Check for deprecated features
echo "Checking for deprecated features..."

# Check for old-style custom settings
DEPRECATED_SETTINGS=$(find force-app -name "*.object-meta.xml" -exec grep -l "customSettingsType>List" {} \; | wc -l)
if [ $DEPRECATED_SETTINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Found $DEPRECATED_SETTINGS list custom settings (consider Custom Metadata Types)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check for old Aura components (should migrate to LWC)
AURA_COMPONENTS=$(find force-app -name "*.cmp" | wc -l)
if [ $AURA_COMPONENTS -gt 5 ]; then
    echo -e "${YELLOW}⚠ Found $AURA_COMPONENTS Aura components (consider migrating to LWC)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo -e "${GREEN}✓ Deprecation check complete${NC}"
echo ""

# 4. Check naming conventions
echo "Checking naming conventions..."

# Check for spaces in API names (not allowed)
SPACE_ERRORS=$(find force-app -name "*.xml" -exec grep -l "fullName>.*\s.*<" {} \; | wc -l)
if [ $SPACE_ERRORS -gt 0 ]; then
    echo -e "${RED}✗ Found $SPACE_ERRORS files with spaces in API names${NC}"
    ERRORS=$((ERRORS + SPACE_ERRORS))
fi

# Check for lowercase custom object names (should be PascalCase)
LOWERCASE_OBJECTS=$(find force-app/main/default/objects -name "*.object-meta.xml" -exec basename {} \; | grep -E "^[a-z]" | wc -l)
if [ $LOWERCASE_OBJECTS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Found $LOWERCASE_OBJECTS custom objects with lowercase names${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo -e "${GREEN}✓ Naming convention check complete${NC}"
echo ""

# 5. Check for hardcoded IDs or URLs
echo "Checking for hardcoded values..."

# Check for record IDs (15 or 18 character Salesforce IDs)
HARDCODED_IDS=$(grep -r -E "'[a-zA-Z0-9]{15,18}'" force-app/main/default/classes force-app/main/default/triggers 2>/dev/null | wc -l)
if [ $HARDCODED_IDS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Found $HARDCODED_IDS potential hardcoded record IDs in Apex${NC}"
    echo "  Review and replace with custom settings or custom metadata"
    WARNINGS=$((WARNINGS + 1))
fi

# Check for hardcoded URLs
HARDCODED_URLS=$(grep -r "https://.*\.salesforce\.com" force-app/main/default/ 2>/dev/null | wc -l)
if [ $HARDCODED_URLS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Found $HARDCODED_URLS hardcoded Salesforce URLs${NC}"
    echo "  Consider using Named Credentials or Custom Settings"
    WARNINGS=$((WARNINGS + 1))
fi

echo -e "${GREEN}✓ Hardcoded value check complete${NC}"
echo ""

# 6. Check meta.xml files
echo "Checking for missing meta.xml files..."

MISSING_META=0
find force-app -name "*.cls" | while read file; do
    if [ ! -f "${file}-meta.xml" ]; then
        echo -e "${RED}✗ Missing meta.xml for: $file${NC}"
        MISSING_META=$((MISSING_META + 1))
    fi
done

if [ $MISSING_META -eq 0 ]; then
    echo -e "${GREEN}✓ All source files have meta.xml files${NC}"
else
    echo -e "${RED}✗ Found $MISSING_META missing meta.xml files${NC}"
    ERRORS=$((ERRORS + MISSING_META))
fi
echo ""

# 7. Check for test classes
echo "Checking test coverage..."

TOTAL_CLASSES=$(find force-app -name "*.cls" | wc -l)
TEST_CLASSES=$(find force-app -name "*Test.cls" -o -name "*_Test.cls" | wc -l)

if [ $TOTAL_CLASSES -gt 0 ]; then
    TEST_RATIO=$(echo "scale=2; $TEST_CLASSES / $TOTAL_CLASSES * 100" | bc)
    echo "Test class ratio: $TEST_CLASSES/$TOTAL_CLASSES (${TEST_RATIO}%)"
    
    if (( $(echo "$TEST_RATIO < 50" | bc -l) )); then
        echo -e "${YELLOW}⚠ Low test class coverage (${TEST_RATIO}%)${NC}"
        echo "  Consider adding more test classes"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}✓ Good test class coverage (${TEST_RATIO}%)${NC}"
    fi
else
    echo "No Apex classes found"
fi
echo ""

# 8. Check package.xml
echo "Checking package.xml..."

if [ -f "manifest/package.xml" ]; then
    echo -e "${GREEN}✓ Found package.xml${NC}"
    
    # Validate it's well-formed XML
    if xmllint --noout manifest/package.xml 2>/dev/null; then
        echo -e "${GREEN}✓ package.xml is valid XML${NC}"
    else
        echo -e "${RED}✗ package.xml is invalid XML${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠ No package.xml found in manifest/ directory${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "Errors: ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ Metadata validation passed!${NC}"
    echo "Your metadata is ready for deployment."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Validation passed with warnings${NC}"
    echo "Review warnings before deploying."
    exit 0
else
    echo -e "${RED}✗ Validation failed${NC}"
    echo "Fix errors before deploying."
    exit 1
fi
