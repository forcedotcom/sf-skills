# Flow Clone from Template

The schedule-triggered flow for Pipeline Management must be cloned from the template `sales_pipe_mgmt__OppSuggGenSchFlow`. This template is provisioned when Pipeline Management is enabled but never activates itself.

## Why Clone Instead of Build

The template flow contains:
- Complete flow body with all elements and connectors
- Invocable action calls using `getOrExecFieldUpdtSuggestion` action type (NOT `generatePromptResponse`)
- Namespace-prefixed references to prompt templates (`sales_pipe_mgmt__RecommendStageforOpp`, `sales_pipe_mgmt__RecommendNextStepforOpp`)
- Bot definition lookups and opportunity team member assignment logic
- Schedule trigger configuration

Building this from scratch would require knowing:
- Exact action type and input parameters
- Internal action names
- Flow element connection paths
- Variable declarations and assignments

The template already has all of this correct — cloning preserves the entire working structure.

---

## Flow Detection: ApiName is primary; SourceTemplateId is best-effort

`SourceTemplateId` is a real field on `FlowDefinitionView` (confirmed in API v67.0). The
Setup-UI "Save As" clone path populates it with the template's fully-qualified name
(e.g., `sales_pipe_mgmt__OppSuggGenSchFlow`). **However, a Metadata-API deploy of the
pre-retrieved template (the PRIMARY clone path — Method 1) does NOT populate
`FlowDefinitionView.SourceTemplateId`**, even though the deployed XML carries the
`<sourceTemplate>` element and the flow is fully active and wired. Org-verified on a
fresh SDB3 org: the `SourceTemplateId` query returned zero rows while the flow was
active. So detect by **ApiName first**, and treat `SourceTemplateId` as a best-effort
signal that only the UI path sets.

**Primary approach** (by ApiName — reliable after both the deploy and the UI paths):
```bash
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName='Process_Field_Update_Suggestions' AND IsTemplate=false" --target-org pipeline-mgmt-org --json 2>/dev/null
```

**Supplementary approach** (by `SourceTemplateId` — matches only UI "Save As" clones, empty after a Metadata-API deploy):
```bash
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org pipeline-mgmt-org --json 2>/dev/null
```

**Incorrect approach** (label-based):
```bash
# DO NOT USE — fragile, language-dependent
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE IsTemplate=false AND Label LIKE '%Field Update%'" --target-org pipeline-mgmt-org --json 2>/dev/null
```

**Why label-based detection fails**:
- Labels can be changed by admins
- Labels are translated in multi-language orgs
- Multiple flows could have similar labels
- Not the intended API design

---

## Clone Approach

Two methods are available:

1. **Primary — Deploy pre-retrieved template** (fully automated via `scripts/create-flow.sh`)
2. **Fallback — Setup UI "Save As"** (if deploy fails due to org-specific constraints)
3. **Verify** the clone exists and has `SourceTemplateId` set
4. **Activate** if saved as Draft (via retrieve → transform status → deploy)

---

## Method 1: Deploy Pre-Retrieved Template (PRIMARY)

The skill includes a complete flow template retrieved from a live org (`assets/pipeline_management_flow.flow-meta.xml`, 548 lines, API v67.0). This template:
- Contains all flow elements, connectors, action calls, variables, and schedule trigger
- Includes `<sourceTemplate>sales_pipe_mgmt__OppSuggGenSchFlow</sourceTemplate>` in the flow body (records provenance in the metadata; note this does **not** populate the queryable `FlowDefinitionView.SourceTemplateId` — detect the clone by ApiName, see "Flow Detection" above)
- Sets `<status>Active</status>` — deploys ready to run
- Uses `getOrExecFieldUpdtSuggestion` action type with correct input parameters

**Usage:**
```bash
bash scripts/create-flow.sh <org-alias>
```

**What it does:**
1. Checks if a clone already exists (by SourceTemplateId or naming convention)
2. If missing: copies template to `force-app/main/default/flows/`, updates `startDate` to today
3. Deploys via `sf project deploy start`
4. If deploy fails: falls back to Setup UI guidance

**Why this works**: While you cannot RETRIEVE the managed template via API, you CAN deploy a flow that references it as `sourceTemplate`. The platform accepts the deployment because the flow body is valid metadata — the namespace protection only blocks reads, not writes of clones.

**When deploy may fail:**
- Org has flow governance rules blocking new Active schedule-triggered flows
- API version mismatch (template uses v67.0; org may be on older API)
- Missing prerequisites (Pipeline Management not enabled, template not provisioned)
- Permission issues (user lacks `ManageFlows` permission)

---

## Method 2: Setup UI "Save As" (FALLBACK)

If the programmatic deploy fails, the Setup UI method always works:

1. Setup → Flows → Find "Process Field Update Suggestions" (template, marked with template icon)
2. Open the flow → Click **"Save As"** → New label: "Process Field Update Suggestions" → Save
3. The platform creates a full copy with all flow elements, connectors, and action calls intact
4. **Activate** the new flow (it saves as Draft by default)
5. The platform sets `SourceTemplateId` automatically on the clone

---

## Why Direct Template Retrieval Fails (Reference)

**Critical finding (verified)**: The template flow `sales_pipe_mgmt__OppSuggGenSchFlow` is in a managed namespace. **Neither programmatic retrieval method works**:

- **CLI retrieve**: `sf project retrieve start --metadata "Flow:sales_pipe_mgmt__OppSuggGenSchFlow"` → FAILS with "Entity of type 'Flow' named 'sales_pipe_mgmt__OppSuggGenSchFlow' cannot be found"
- **SOAP readMetadata**: Returns `<records xsi:nil="true"/>` — the managed package prevents metadata reads even with a valid session

Both methods were tested against a real org (orgfarm-88724451ea, API v64.0). This is by design — managed namespace flows are protected from external metadata reads.

**However**, the pre-retrieved template approach works because:
1. We retrieved the flow from a live org where it was ALREADY CLONED (user-space clone is readable)
2. Deploying a flow with `<sourceTemplate>` is a write operation — not subject to managed namespace read protection
3. The deployed flow registers correctly with `SourceTemplateId` for future detection

### What the template contains

- Flow metadata (`<fullName>`, `<label>`, `<status>`, `<isTemplate>`)
- All flow elements (`<actionCalls>`, `<assignments>`, `<decisions>`, `<loops>`, etc.)
- All connectors (`<connector>` with `<targetReference>`)
- All variable declarations
- Schedule configuration (`<startDate>`, `<frequency>`)
- Action call parameters (`getOrExecFieldUpdtSuggestion` with `recordId`, `fieldApiNames`, `agentUserId`, `agentBotDefinitionId`)

---

## Step 2: Transform the XML

```bash
TEMPLATE_FILE="force-app/main/default/flows/sales_pipe_mgmt__OppSuggGenSchFlow.flow-meta.xml"
NEW_FILE="force-app/main/default/flows/Process_Field_Update_Suggestions.flow-meta.xml"

# Copy template to new file
cp "$TEMPLATE_FILE" "$NEW_FILE"

# Transform metadata (macOS sed syntax — use sed -i '' on macOS, sed -i on Linux)
# 1. Rename the flow
sed -i '' 's|<fullName>sales_pipe_mgmt__OppSuggGenSchFlow</fullName>|<fullName>Process_Field_Update_Suggestions</fullName>|g' "$NEW_FILE"

# 2. Change the top-level flow label ONLY (first occurrence; non-greedy to avoid corrupting nested element labels)
sed -i '' '0,/<label>[^<]*<\/label>/s|<label>[^<]*</label>|<label>Process Field Update Suggestions</label>|' "$NEW_FILE"

# 3. Mark as non-template
sed -i '' 's|<isTemplate>true</isTemplate>|<isTemplate>false</isTemplate>|g' "$NEW_FILE"

# 4. Activate (handle both Draft and Obsolete status)
sed -i '' 's|<status>Draft</status>|<status>Active</status>|g' "$NEW_FILE"
sed -i '' 's|<status>Obsolete</status>|<status>Active</status>|g' "$NEW_FILE"

# 5. Set schedule start date to today
TODAY=$(date +%Y-%m-%d)
sed -i '' "s|<startDate>[^<]*</startDate>|<startDate>${TODAY}</startDate>|g" "$NEW_FILE"
```

**What NOT to change**:
- Namespace-prefixed references (`sales_pipe_mgmt__*`) — these remain valid in the clone
- Action type (`getOrExecFieldUpdtSuggestion`) — preserved automatically
- Action parameters (`recordId`, `fieldApiNames`, etc.) — preserved automatically
- Flow elements and connectors — preserved automatically

---

## Step 3: Deploy the Cloned Flow

```bash
sf project deploy start --metadata "Flow:Process_Field_Update_Suggestions" --target-org $ORG --json 2>/dev/null
```

**Why deployment works**: The transformed XML is a valid Flow metadata file with:
- Unique `<fullName>` (no conflict with template)
- `<isTemplate>false</isTemplate>` (so it's a real flow, not a template)
- `<status>Active</status>` (so it runs immediately)
- All namespace-prefixed references intact (so action calls work)

---

## Verification

```bash
# Check that flow exists and is active — query by ApiName (reliable after a
# Metadata-API deploy, which does NOT populate SourceTemplateId).
sf data query -q "SELECT Id, ApiName, IsActive, SourceTemplateId FROM FlowDefinitionView WHERE ApiName='Process_Field_Update_Suggestions' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null

# Expected output (SourceTemplateId is typically null after a Metadata-API deploy):
# {
#   "status": 0,
#   "result": {
#     "records": [
#       {
#         "Id": "...",
#         "ApiName": "Process_Field_Update_Suggestions",
#         "IsActive": true,
#         "SourceTemplateId": null
#       }
#     ],
#     "totalSize": 1
#   }
# }
```

**Key indicators of success**:
- `IsActive: true` — Flow is running
- `totalSize: 1` — Exactly one clone named `Process_Field_Update_Suggestions`
- `SourceTemplateId` — populated only for UI "Save As" clones; **expect `null` after a Metadata-API deploy** (does not indicate failure)

---

## Complete Script: Detect + Verify + Activate

The PRIMARY path deploys the pre-retrieved template automatically (Method 1). This script handles detection and post-clone verification/activation; it only prompts for the Setup UI "Save As" fallback if no clone is found (i.e. the deploy was skipped or failed).

```bash
#!/bin/bash
set -euo pipefail

ORG="${1:-pipeline-mgmt-org}"

echo "=== Checking if template clone already exists ==="
CLONE_QUERY=$(sf data query -q "SELECT Id, ApiName, IsActive, SourceTemplateId FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org "$ORG" --json 2>/dev/null)

CLONE_COUNT=$(echo "$CLONE_QUERY" | jq -r '.result.totalSize // 0')

if [[ "$CLONE_COUNT" -eq 0 ]]; then
  # Fallback: check by naming convention
  CLONE_QUERY=$(sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE ApiName LIKE '%OppSuggGen%' AND IsTemplate=false" --target-org "$ORG" --json 2>/dev/null)
  CLONE_COUNT=$(echo "$CLONE_QUERY" | jq -r '.result.totalSize // 0')
fi

if [[ "$CLONE_COUNT" -eq 0 ]]; then
  echo "No template clone found."
  echo ""
  echo "ACTION REQUIRED: Clone the template flow manually via Setup UI:"
  echo "  1. Setup → Flows → Find 'Process Field Update Suggestions' (template)"
  echo "  2. Open the flow → Save As → Label: 'Process Field Update Suggestions' → Save"
  echo "  3. Activate the new flow"
  echo "  4. Re-run this script to verify"
  echo ""
  echo "NOTE: Programmatic retrieval of managed namespace flows is not possible."
  echo "  - CLI retrieve returns: 'Entity of type Flow cannot be found'"
  echo "  - SOAP readMetadata returns: <records xsi:nil=\"true\"/>"
  exit 1
fi

echo "Found $CLONE_COUNT clone(s):"
echo "$CLONE_QUERY" | jq '.result.records[] | {ApiName, IsActive, SourceTemplateId}'
echo ""

# Check if active
IS_ACTIVE=$(echo "$CLONE_QUERY" | jq -r '.result.records[0].IsActive')
FLOW_API_NAME=$(echo "$CLONE_QUERY" | jq -r '.result.records[0].ApiName')

if [[ "$IS_ACTIVE" == "true" ]]; then
  echo "Flow '$FLOW_API_NAME' is ACTIVE. Suggestions will generate on schedule."
  echo ""
  echo "=== Done ==="
  exit 0
fi

echo "Flow '$FLOW_API_NAME' exists but is INACTIVE. Attempting activation..."
echo ""

# Activate via retrieve → transform → deploy
sf project retrieve start --metadata "Flow:${FLOW_API_NAME}" --target-org "$ORG" --json 2>/dev/null >/dev/null || true

FLOW_FILE="force-app/main/default/flows/${FLOW_API_NAME}.flow-meta.xml"

if [[ -f "$FLOW_FILE" ]]; then
  # Cross-platform sed in-place
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' 's|<status>Draft</status>|<status>Active</status>|g' "$FLOW_FILE"
    sed -i '' 's|<status>Obsolete</status>|<status>Active</status>|g' "$FLOW_FILE"
  else
    sed -i 's|<status>Draft</status>|<status>Active</status>|g' "$FLOW_FILE"
    sed -i 's|<status>Obsolete</status>|<status>Active</status>|g' "$FLOW_FILE"
  fi

  DEPLOY_RESULT=$(sf project deploy start --metadata "Flow:${FLOW_API_NAME}" --target-org "$ORG" --json 2>/dev/null)

  if echo "$DEPLOY_RESULT" | jq -e '.status == 0' >/dev/null 2>&1; then
    echo "Flow activated successfully via Metadata API deploy."
  else
    echo "Warning: Deploy returned non-zero status. Check flow in Setup → Flows."
    echo "$DEPLOY_RESULT" | jq '.message // .result.details.componentFailures[0].problem // "unknown error"' 2>/dev/null || true
  fi
else
  echo "Warning: Could not retrieve flow metadata for activation."
  echo "Activate manually: Setup → Flows → ${FLOW_API_NAME} → Activate"
fi

echo ""

# Final verification
echo "=== Final verification ==="
sf data query -q "SELECT ApiName, IsActive FROM FlowDefinitionView WHERE ApiName='${FLOW_API_NAME}'" --target-org "$ORG" --json 2>/dev/null | jq '.result.records[0] | {ApiName, IsActive}'

echo ""
echo "=== Done ==="
```

---

## Understanding the Flow Action Type

The cloned flow uses the `getOrExecFieldUpdtSuggestion` action type (NOT `generatePromptResponse`). This action:
- Takes inputs: `recordId`, `fieldApiNames`, `agentUserId`, `agentBotDefinitionId`
- Generates field update suggestions via prompt templates
- Stores results as `AiGenActionItem` records (`Type = 'FIELD_UPDATE'`, `Subject` = the field API name, `ParentId` = the Opportunity Id)

**Why you don't need to know this**: The template already has the correct action type configured. When you clone it, you preserve the entire action call structure — no manual construction needed.

**What happens if you try to build from scratch**:
- You'd need to know the exact action name (`getOrExecFieldUpdtSuggestion`)
- You'd need to know the exact input parameter names and types
- You'd need to know the namespace prefix for prompt template references
- You'd risk getting any of these wrong and producing a non-functional flow

**The clone approach avoids all of this** — the template is the source of truth.

---

## Namespace-Prefixed References

The template flow references prompt templates with namespace prefixes:
- `sales_pipe_mgmt__RecommendStageforOpp`
- `sales_pipe_mgmt__RecommendNextStepforOpp`

**Do NOT strip these prefixes** — they're required even in the cloned flow. The namespace prefix is how Salesforce identifies these as Pipeline Management provisioned templates (not user-created custom templates).

**Why this works in the clone**: When you deploy the transformed XML with these references intact, Salesforce validates that:
1. The referenced prompt templates exist in the org
2. They were provisioned with the `sales_pipe_mgmt__` namespace
3. They're active and available

If you strip the namespace prefixes, the references break and the flow fails validation.

---

## Troubleshooting

### Template doesn't exist

**Symptom**: `sf project retrieve start` fails with "No source-backed components present"

**Cause**: Pipeline Management is not enabled or template hasn't been provisioned yet

**Fix**:
```bash
# Verify Pipeline Management is enabled
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata>
    <met:type>SalesDealAgentSettings</met:type>
    <met:fullNames>SalesDealAgent</met:fullNames>
  </met:readMetadata></soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableDealAgent>[^<]*</enableDealAgent>"

# Expected: <enableDealAgent>true</enableDealAgent>
# If false: Enable Pipeline Management first (see references/setup-order.md)
```

### Deploy fails with validation errors

**Symptom**: Deploy reports errors about missing prompt templates or invalid action types

**Cause**: Namespace-prefixed references were removed or template was modified incorrectly

**Fix**:
1. Re-retrieve the template (don't use a cached copy)
2. Only transform the metadata fields listed in Step 2 — don't modify flow elements
3. Check that namespace prefixes are intact (`grep "sales_pipe_mgmt__" "$NEW_FILE"`)

### Flow deploys but doesn't run

**Symptom**: Flow exists, `IsActive: true`, but no suggestions generated

**Cause**: Missing prerequisites (agent not active, stage descriptions missing, no data sources)

**Fix**: See `references/repair-diagnostics.md` for full checklist

### Clone already exists

**Symptom**: Deploy fails with "A flow with this name already exists"

**Cause**: Flow was already cloned

**Fix**:
```bash
# Check existing flow status
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null

# If IsActive: false → reactivate via Tooling API
FLOW_ID=$(sf data query -q "SELECT Id FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

curl -X PATCH "${INSTANCE_URL}/services/data/v64.0/tooling/sobjects/Flow/${FLOW_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"Metadata":{"status":"Active"}}' 2>/dev/null
```

---

## Setup UI Quick Reference (Fallback only)

Deploying the pre-retrieved template (Method 1, PRIMARY) is fully automated and is what
`scripts/create-flow.sh` / `setup-all.sh` use. The Setup UI "Save As" below is the **fallback**
for the rare org where the programmatic deploy fails on org-specific constraints:

1. Go to Setup → Flows → Find "Process Field Update Suggestions" (look for template icon)
2. Open the flow → **Save As** → Label: "Process Field Update Suggestions" → Save
3. **Activate** the new flow
4. Verify: Run the detection query from "Flow Detection" section above

**Limitations of the UI fallback**:
- Requires manual interaction (not fully automatable)
- Cannot be batched across multiple orgs via script
- Requires System Administrator access to Setup → Flows

**What is automatable after a manual fallback clone**:
- Detection (query `SourceTemplateId` to confirm clone exists)
- Activation (Tooling API PATCH if saved as Draft)
- Verification (query `IsActive` status)
- Schedule configuration (deploy modified flow XML after initial clone)

---

## Notes

- Always use `2>/dev/null` on `sf ... --json` piped to jq
- Flow detection uses `SourceTemplateId` (NOT label-based)
- Clone preserves `getOrExecFieldUpdtSuggestion` action type automatically
- Namespace-prefixed references must remain intact
- Pipeline Management generates NO suggestions until this flow is active
- Template is provisioned on Pipeline Management enablement but never self-activates
