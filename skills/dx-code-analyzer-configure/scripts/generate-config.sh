#!/bin/bash
# generate-config.sh
# Generates a code-analyzer.yml with ONLY project-specific overrides.
# Does NOT duplicate built-in defaults — only writes what intentionally differs.
#
# Usage: bash <skill_dir>/scripts/generate-config.sh [--type apex|lwc|fullstack]
#
# If --type is not specified, auto-detects from workspace contents.

set -euo pipefail

CONFIG_FILE="code-analyzer.yml"
PROJECT_TYPE="${1:-auto}"

# Remove --type prefix if present
PROJECT_TYPE="${PROJECT_TYPE#--type=}"
PROJECT_TYPE="${PROJECT_TYPE#--type }"

# Auto-detect project type
if [ "$PROJECT_TYPE" = "auto" ] || [ "$PROJECT_TYPE" = "" ]; then
    HAS_APEX=false
    HAS_LWC=false
    HAS_NODE_MODULES=false

    [ -d "force-app" ] && HAS_APEX=true
    find . -maxdepth 4 -path "*/lwc/*" -name "*.js" 2>/dev/null | head -1 | grep -q . && HAS_LWC=true
    [ -d "node_modules" ] && HAS_NODE_MODULES=true

    if [ "$HAS_APEX" = true ] && [ "$HAS_LWC" = true ]; then
        PROJECT_TYPE="fullstack"
    elif [ "$HAS_LWC" = true ]; then
        PROJECT_TYPE="lwc"
    elif [ "$HAS_APEX" = true ]; then
        PROJECT_TYPE="apex"
    else
        PROJECT_TYPE="minimal"
    fi

    echo "Auto-detected project type: ${PROJECT_TYPE}"

    # Warn if no Salesforce project markers found
    if [ "$PROJECT_TYPE" = "minimal" ] && [ ! -f "sfdx-project.json" ] && [ ! -f "sf-project.json" ]; then
        echo "WARNING: No Salesforce project markers found (no sfdx-project.json, sf-project.json, or force-app/)."
        echo "         Are you running this from your project root?"
        echo "         Generating minimal config — re-run from project root for better detection."
    fi
fi

# Check if config already exists
if [ -f "$CONFIG_FILE" ] || [ -f "code-analyzer.yaml" ]; then
    echo "WARNING: Config file already exists."
    echo "Edit the existing file instead of regenerating."
    exit 1
fi

echo "Generating ${CONFIG_FILE} (overrides only)..."

case "$PROJECT_TYPE" in
    apex)
        cat > "$CONFIG_FILE" << 'YAML'
# Code Analyzer overrides for Apex project
# Only entries that differ from built-in defaults

ignores:
  files:
    - "**/node_modules/**"
    - "**/.sfdx/**"
    - "**/.sf/**"

engines:
  sfge:
    java_max_heap_size: "4g"
YAML
        ;;

    lwc)
        cat > "$CONFIG_FILE" << 'YAML'
# Code Analyzer overrides for LWC project
# Only entries that differ from built-in defaults

ignores:
  files:
    - "**/node_modules/**"
    - "**/.sfdx/**"
    - "**/.sf/**"
    - "**/jest-mocks/**"
    - "**/__tests__/**"

engines:
  eslint:
    auto_discover_eslint_config: true
YAML
        ;;

    fullstack)
        cat > "$CONFIG_FILE" << 'YAML'
# Code Analyzer overrides for full-stack Salesforce project
# Only entries that differ from built-in defaults

ignores:
  files:
    - "**/node_modules/**"
    - "**/.sfdx/**"
    - "**/.sf/**"
    - "**/jest-mocks/**"
    - "**/__tests__/**"

engines:
  sfge:
    java_max_heap_size: "4g"
  eslint:
    auto_discover_eslint_config: true
YAML
        ;;

    minimal)
        cat > "$CONFIG_FILE" << 'YAML'
# Code Analyzer overrides
# Only entries that differ from built-in defaults

ignores:
  files:
    - "**/node_modules/**"
YAML
        ;;

    *)
        echo "ERROR: Unknown project type: ${PROJECT_TYPE}"
        echo "Valid types: apex, lwc, fullstack, minimal"
        exit 1
        ;;
esac

echo ""
echo "Created: ${CONFIG_FILE}"
echo ""
echo "This file contains ONLY overrides — built-in defaults still apply for"
echo "everything not listed here. Add more overrides as needed."
echo ""
echo "Next steps:"
echo "  1. Review: cat ${CONFIG_FILE}"
echo "  2. Validate: sf code-analyzer config --config-file ${CONFIG_FILE}"
echo "  3. Run scan: sf code-analyzer run --output-file results.json --include-fixes"
