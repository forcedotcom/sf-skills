#!/bin/bash

# Deploy Pipeline Management settings from local metadata files
# Usage: ./deploy-settings.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

ORG_ALIAS="${1:-}"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "❌ Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

if [[ ! -f "sfdx-project.json" ]]; then
  echo "❌ Error: sfdx-project.json not found in current directory"
  echo "Copy from ../assets/sfdx-project.json first"
  exit 1
fi

SETTINGS_DIR="force-app/main/default/settings"

if [[ ! -d "$SETTINGS_DIR" ]]; then
  echo "❌ Error: Settings directory not found: $SETTINGS_DIR"
  echo "Run ./retrieve-settings.sh first to retrieve settings"
  exit 1
fi

echo "📤 Deploying Pipeline Management settings to org: $ORG_ALIAS"
echo ""

# Count available settings files
SETTINGS_COUNT=$(find "$SETTINGS_DIR" -name "*.settings-meta.xml" -type f | wc -l | tr -d ' ')

if [[ "$SETTINGS_COUNT" -eq 0 ]]; then
  echo "❌ No settings files found in $SETTINGS_DIR"
  exit 1
fi

echo "Found $SETTINGS_COUNT settings file(s) to deploy"
echo ""

# Deploy all settings
echo "Deploying settings..."

if sf project deploy start \
  --source-dir "$SETTINGS_DIR" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null | jq -e '.status == 0' >/dev/null 2>&1; then
  echo "✅ Settings deployed successfully"
else
  echo "❌ Deployment failed"
  echo ""
  echo "Retrying with verbose output..."
  sf project deploy start \
    --source-dir "$SETTINGS_DIR" \
    --target-org "$ORG_ALIAS"
  exit 1
fi

echo ""

# List deployed files
echo "Deployed settings:"
find "$SETTINGS_DIR" -name "*.settings-meta.xml" -type f | while read -r FILE; do
  BASENAME=$(basename "$FILE" .settings-meta.xml)
  echo "  ✅ $BASENAME"
done

echo ""
echo "✅ Deployment complete"
