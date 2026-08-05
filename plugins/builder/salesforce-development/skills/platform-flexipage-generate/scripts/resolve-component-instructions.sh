#!/bin/bash
# resolve-component-instructions.sh — Resolve the instructions file path for a component.
#
# Usage: scripts/resolve-component-instructions.sh <componentDefinition>
#
# Arguments:
#   componentDefinition — Component FQN in colon format (e.g., "flexipage:fieldSection")
#
# Output: The path to the instructions file if it exists, or empty string if not found.
#
# Examples:
#   scripts/resolve-component-instructions.sh "record_flexipage:dynamicHighlights"
#   → references/record_flexipage_dynamicHighlights.md
#
#   scripts/resolve-component-instructions.sh "flexipage:fieldSection"
#   → references/flexipage_fieldSection.md
#
#   scripts/resolve-component-instructions.sh "c:expenseTracker"
#   → (empty — file does not exist)

set -euo pipefail

COMPONENT="${1:-}"

if [ -z "$COMPONENT" ]; then
  echo "Usage: $0 <componentDefinition>" >&2
  exit 1
fi

# Derive filename: replace ':' with '_', append .md
FILENAME=$(echo "$COMPONENT" | sed 's/:/_/g').md

# Resolve path relative to the skill directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
FILEPATH="$SKILL_DIR/references/$FILENAME"

if [ -f "$FILEPATH" ]; then
  echo "references/$FILENAME"
else
  echo ""
fi
