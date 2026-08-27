#!/usr/bin/env bash
# Verify that the project contains a React-based UI bundle
# Exit 0 if React is found, exit 1 otherwise

set -euo pipefail

if ! grep -q '"react"' uiBundles/*/package.json 2>/dev/null; then
  echo "ERROR: Not a React bundle - @salesforce/ui-bundle-features requires React"
  echo "Found bundle type: $(grep '"type"' uiBundles/*/package.json 2>/dev/null || echo 'unknown')"
  exit 1
fi

echo "React bundle detected"
exit 0
