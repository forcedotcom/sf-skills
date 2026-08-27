#!/bin/bash
# Checks that sourceApiVersion in sfdx-project.json is 67.0 or higher.
# If lower, updates it to "67.0".

set -e

PROJECT_FILE="sfdx-project.json"

if [[ ! -f "$PROJECT_FILE" ]]; then
  echo "ERROR: $PROJECT_FILE not found in current directory"
  exit 1
fi

# Extract sourceApiVersion and check if it's below 67.0
version=$(jq -r '.sourceApiVersion // "0"' "$PROJECT_FILE")
is_below=$(jq --arg v "$version" -n '($v | split(".") | .[0] | tonumber) < 67')

if [[ "$is_below" == "true" ]]; then
  echo "WARNING: sourceApiVersion is $version (< 67.0)"
  echo "Updating $PROJECT_FILE to set sourceApiVersion to \"67.0\""

  # Update the file
  jq '.sourceApiVersion = "67.0"' "$PROJECT_FILE" > "$PROJECT_FILE.tmp"
  mv "$PROJECT_FILE.tmp" "$PROJECT_FILE"

  echo "OK: Updated sourceApiVersion to 67.0"
  exit 0
fi

echo "OK: sourceApiVersion is $version (>= 67.0)"
