#!/usr/bin/env bash
# Check if sfdx-project.json exists and is valid JSON

if [ ! -f sfdx-project.json ]; then
  echo 'ERROR: sfdx-project.json not found'
  exit 1
fi

# Validate JSON format using python (more portable than node)
if ! python3 -c "import json; json.load(open('sfdx-project.json'))" 2>/dev/null; then
  echo 'ERROR: sfdx-project.json is not valid JSON'
  exit 1
fi

echo 'sfdx-project.json is valid'
