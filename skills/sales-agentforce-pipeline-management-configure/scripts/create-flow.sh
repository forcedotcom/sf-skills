#!/bin/bash

# Detect, create/deploy, and activate Pipeline Management suggestion processing flow
#
# Strategy (in order of preference):
#   1. Check if flow clone already exists (by SourceTemplateId or naming convention)
#   2. If missing: deploy from pre-retrieved template (assets/pipeline_management_flow.flow-meta.xml)
#   3. If deploy fails: instruct user to perform Setup UI "Save As" from managed template
#   4. If exists but inactive: activate via retrieve → transform → deploy
#
# The template (assets/) was retrieved from a live org with Pipeline Management enabled.
# It contains the complete flow logic including sourceTemplate reference, so the deployed
# flow registers as a proper clone of sales_pipe_mgmt__OppSuggGenSchFlow.
#
# Usage: ./create-flow.sh <org-alias>

set -euo pipefail

# sf CLI can emit ANSI color codes inside --json stdout, breaking jq parsing.
# 2>/dev/null only strips stderr; these env vars are the reliable fix (see PM notes).
export NO_COLOR=1
export FORCE_COLOR=0

# Cross-platform sed -i (macOS requires '' arg, GNU does not)
sed_inplace() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

ORG_ALIAS="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$ORG_ALIAS" ]]; then
  echo "Error: Missing org alias"
  echo "Usage: $0 <org-alias>"
  exit 1
fi

echo "Pipeline Management Flow: Detect + Deploy + Activate"
echo ""

TEMPLATE_NAME="sales_pipe_mgmt__OppSuggGenSchFlow"
FLOW_API_NAME="Process_Field_Update_Suggestions"

# --- Detection ---
echo -n "Checking if flow clone exists... "

# Attempt 1: Query by SourceTemplateId (verified field on FlowDefinitionView in API v67.0)
EXISTING_QUERY=$(sf data query \
  --query "SELECT Id, ApiName, IsActive, SourceTemplateId FROM FlowDefinitionView WHERE SourceTemplateId = '${TEMPLATE_NAME}' AND IsTemplate = false" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null)

EXISTING_FLOW=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")
IS_ACTIVE=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null || echo "")

# Attempt 2: Fallback to naming convention match
if [[ -z "$EXISTING_FLOW" ]]; then
  EXISTING_QUERY=$(sf data query \
    --query "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate = false" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null)

  EXISTING_FLOW=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")
  IS_ACTIVE=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null || echo "")
fi

# Attempt 3: Check by standard API name
if [[ -z "$EXISTING_FLOW" ]]; then
  EXISTING_QUERY=$(sf data query \
    --query "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = '${FLOW_API_NAME}'" \
    --target-org "$ORG_ALIAS" \
    --json 2>/dev/null)

  EXISTING_FLOW=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].ApiName // empty' 2>/dev/null || echo "")
  IS_ACTIVE=$(echo "$EXISTING_QUERY" | jq -r '.result.records[0].IsActive // empty' 2>/dev/null || echo "")
fi

# --- Flow Not Found: Deploy from Template ---
if [[ -z "$EXISTING_FLOW" ]]; then
  echo "not found"
  echo ""

  TEMPLATE_FILE="$SCRIPT_DIR/../assets/pipeline_management_flow.flow-meta.xml"

  if [[ -f "$TEMPLATE_FILE" ]]; then
    echo "Deploying flow from pre-retrieved template..."
    echo "  Template: assets/pipeline_management_flow.flow-meta.xml"
    echo "  API Name: $FLOW_API_NAME"
    echo ""

    # Ensure sfdx-project.json exists
    if [[ ! -f "sfdx-project.json" ]]; then
      cat > sfdx-project.json << 'EOF'
{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "67.0"}
EOF
    fi

    FLOW_DIR="force-app/main/default/flows"
    mkdir -p "$FLOW_DIR"
    FLOW_FILE="${FLOW_DIR}/${FLOW_API_NAME}.flow-meta.xml"
    cp "$TEMPLATE_FILE" "$FLOW_FILE"

    # Update startDate to today
    TODAY=$(date +%Y-%m-%d)
    sed_inplace "s|<startDate>[^<]*</startDate>|<startDate>${TODAY}</startDate>|g" "$FLOW_FILE"

    echo "  Schedule start: $TODAY (daily at 11:55 UTC)"
    echo "  Status: Active"
    echo ""

    # Deploy
    echo "  Deploying..."
    DEPLOY_RESULT=$(sf project deploy start --source-dir "$FLOW_FILE" --target-org "$ORG_ALIAS" --json 2>/dev/null || echo '{"status":1}')

    if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
      EXISTING_FLOW="$FLOW_API_NAME"
      IS_ACTIVE="true"
      echo "  Deploy SUCCEEDED"
      echo ""
      echo "Flow '$FLOW_API_NAME' deployed and activated."
      echo "Suggestions will generate daily at 11:55 UTC."
    else
      DEPLOY_ERR=$(echo "$DEPLOY_RESULT" | jq -r '.result.details.componentFailures[0].problem // .message // "unknown"' 2>/dev/null || echo "unknown")
      echo "  Deploy FAILED: $DEPLOY_ERR"
      echo ""
      echo "Falling back to manual Setup UI clone..."
      echo ""
    fi
  fi

  # If still no flow, guide user through UI
  if [[ -z "$EXISTING_FLOW" ]]; then
    echo "ACTION REQUIRED: Clone the template manually via Setup UI."
    echo ""
    echo "  The template flow is in the 'sales_pipe_mgmt' managed namespace."
    echo ""
    echo "  Steps:"
    echo "    1. Open Setup -> Flows"
    echo "    2. Find 'Process Field Update Suggestions' (marked with template icon)"
    echo "    3. Open the flow -> click 'Save As'"
    echo "    4. Label: 'Process Field Update Suggestions' -> Save"
    echo "    5. Click 'Activate' on the new flow"
    echo "    6. Re-run this script to verify"
    echo ""
    exit 1
  fi
fi

# --- Flow Found ---
if [[ -n "$EXISTING_FLOW" ]]; then
  echo "found: $EXISTING_FLOW (active: $IS_ACTIVE)"
  echo ""
fi

# --- Already Active ---
if [[ "$IS_ACTIVE" == "true" ]]; then
  echo "Flow '$EXISTING_FLOW' is ACTIVE."
  echo "Suggestions will generate on schedule. No action needed."
  echo ""
  echo "Done."
  exit 0
fi

# --- Exists But Inactive: Activate ---
echo "Flow '$EXISTING_FLOW' exists but is INACTIVE. Activating..."
echo ""

# Ensure sfdx-project.json exists for retrieve/deploy
if [[ ! -f "sfdx-project.json" ]]; then
  cat > sfdx-project.json << 'EOF'
{"packageDirectories": [{"path": "force-app", "default": true}], "sourceApiVersion": "67.0"}
EOF
fi

FLOW_DIR="force-app/main/default/flows"
mkdir -p "$FLOW_DIR"

# Retrieve the CLONE (not the template — the clone is in the org's namespace and IS retrievable)
echo "  Retrieving flow metadata..."
sf project retrieve start \
  --metadata "Flow:${EXISTING_FLOW}" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null >/dev/null || true

FLOW_FILE="${FLOW_DIR}/${EXISTING_FLOW}.flow-meta.xml"

if [[ ! -f "$FLOW_FILE" ]]; then
  echo "  Warning: Could not retrieve flow file."
  echo "  Activate manually: Setup -> Flows -> ${EXISTING_FLOW} -> Activate"
  exit 1
fi

echo "  Retrieved successfully."

# Transform status to Active
echo "  Setting status to Active..."
sed_inplace 's|<status>Draft</status>|<status>Active</status>|g' "$FLOW_FILE"
sed_inplace 's|<status>Obsolete</status>|<status>Active</status>|g' "$FLOW_FILE"

# Deploy
echo "  Deploying activated flow..."
DEPLOY_RESULT=$(sf project deploy start \
  --metadata "Flow:${EXISTING_FLOW}" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null)

if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
  echo "  Deployed successfully."
else
  ERROR_MSG=$(echo "$DEPLOY_RESULT" | jq -r '.message // .result.details.componentFailures[0].problem // "unknown error"' 2>/dev/null || echo "unknown error")
  echo "  Warning: Deploy may have failed: $ERROR_MSG"
  echo "  Activate manually: Setup -> Flows -> ${EXISTING_FLOW} -> Activate"
fi

echo ""

# --- Final Verification ---
echo "Verifying final state..."
sleep 2  # Brief propagation wait

VERIFY_RESULT=$(sf data query \
  --query "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName = '${EXISTING_FLOW}'" \
  --target-org "$ORG_ALIAS" \
  --json 2>/dev/null)

FINAL_ACTIVE=$(echo "$VERIFY_RESULT" | jq -r '.result.records[0].IsActive // "unknown"' 2>/dev/null || echo "unknown")

if [[ "$FINAL_ACTIVE" == "true" ]]; then
  echo "  Flow: $EXISTING_FLOW"
  echo "  Status: ACTIVE"
  echo ""
  echo "Flow activated successfully. Suggestions will generate on schedule."
else
  echo "  Flow: $EXISTING_FLOW"
  echo "  Status: $FINAL_ACTIVE"
  echo ""
  echo "  Flow may need manual activation via Setup UI."
fi

echo ""
echo "Done."
echo ""
echo "Next steps:"
echo "  1. Verify agent is active (./create-agent.sh $ORG_ALIAS)"
echo "  2. Configure opportunity stages (see references/opportunity-stages.md)"
echo "  3. Wait for schedule to trigger, or test with manual notes/emails"
