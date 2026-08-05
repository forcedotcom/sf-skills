#!/bin/bash
# Verification script to ensure scripts are executed from files, not inline
# Usage: source this at the start of SKILL.md execution

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

verify_script_execution() {
  local script_name="$1"
  local expected_path="${SKILL_DIR}/scripts/${script_name}"

  if [[ ! -f "$expected_path" ]]; then
    echo "❌ ERROR: Script file not found: $expected_path"
    echo "This skill requires script files to be present in the deployment."
    return 1
  fi

  # Check if script has expected header
  if ! head -1 "$expected_path" | grep -q "#!/usr/bin/env node"; then
    echo "⚠️  WARNING: Script missing proper header: $expected_path"
  fi

  echo "✓ Script file verified: $script_name"
  return 0
}

# Export function for use in skill execution
export -f verify_script_execution
export SKILL_DIR
