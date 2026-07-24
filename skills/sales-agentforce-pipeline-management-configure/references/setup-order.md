# Setup Order — Quick Reference

Tested sequence for enabling Agentforce Pipeline Management in a greenfield org. All commands verified in Enterprise Edition with Agentforce for Sales add-on.

---

## Authentication

```bash
ORG="pipeline-mgmt-org"
BROWSER=/usr/bin/open sf org login web --instance-url https://login.salesforce.com --alias $ORG

# Get instance URL and access token
INSTANCE_URL=$(sf org display --target-org $ORG --json 2>/dev/null | jq -r '.result.instanceUrl')
ACCESS_TOKEN=$(sf org display --target-org $ORG --json 2>/dev/null | jq -r '.result.accessToken')

# Newer CLI versions (2.108+) redact the token — use fallback
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org $ORG --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty')
fi
```

---

## Step 1: Enable Prerequisites (SOAP API v62.0)

Enable **in this exact order** (dependency chain: #1 → #2 → #3). See `references/soap-api-enablement.md` for full scripts.

| # | Setting | Metadata Type | Required? | Depends On | Verification |
|---|---------|---------------|-----------|------------|--------------|
| 1 | Einstein Generative AI | `EinsteinGptSettings` | **required** | — | SOAP `readMetadata` → `<enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>` |
| 2 | Agentforce Agent | `EinsteinCopilotSettings` | **required** | **#1 must be enabled first** | SOAP `readMetadata` → `<enableEinsteinGptCopilot>true</enableEinsteinGptCopilot>` |
| 3 | Agentforce Studio / Agent Platform | `AgentPlatformSettings` | **required** | **#2 must be enabled first** — gates the Deal Agent | SOAP `readMetadata` → `<enableAgentPlatform>true</enableAgentPlatform>` |
| 4 | Notes (API: EnhancedNotesSettings) | `EnhancedNotesSettings` | **required** | — | `SELECT count() FROM ContentNote` succeeds |
| 5 | Enhanced Email | `EmailAdministrationSettings` | optional (recommended) | — | SOAP `readMetadata` → `<enableEnhancedEmailEnabled>true</enableEnhancedEmailEnabled>` |
| 6 | Opportunity Team Selling | `OpportunitySettings` | **required** | No Opportunity Splitting | `SELECT count() FROM OpportunityTeamMember` succeeds |

**Do NOT use CLI Metadata deploy** (`sf project deploy start`) — it has a silent failure mode where it reports success but the org reverts the setting.

**Do NOT enable `BotSettings`** (`enableBots`) — that is for legacy messaging bots and is completely unrelated to Pipeline Management. It requires legal terms acceptance and will fail. Use `EinsteinCopilotSettings` for Agentforce Agent instead.

---

## Step 2: Enable Pipeline Management (SOAP API v64.0)

**Critical**: Must use API v64.0+ (v62.0 returns "Property 'enableDealAgent' not valid"). `updateMetadata` on `SalesDealAgentSettings` with `<enableDealAgent>true</enableDealAgent>` and `<enableDealAgentAutoApproveAllTasks>false</enableDealAgentAutoApproveAllTasks>`, then `readMetadata` to confirm.

See the canonical SOAP snippets in `references/soap-api-enablement.md` → **§6 Pipeline Management**.

---

## Step 2b: Enable Pipeline Inspection

**Required.** Pipeline Inspection provides the UI where sales reps view and accept/dismiss agent suggestions. Suggestions still generate without it, but users have no way to see them — this is a required setting for the feature to be usable, not optional.

`updateMetadata` on `OpportunitySettings` with `<enablePipelineInspection>true</enablePipelineInspection>`, then `readMetadata` to confirm.

See the canonical SOAP snippets in `references/soap-api-enablement.md` → **§7 Pipeline Inspection**.

---

## Step 3: Verify Auto-Created Components

After enabling Pipeline Management, these components should auto-create:

```bash
# Check permission set groups
sf data query -q "SELECT Id, MasterLabel, DeveloperName FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" --target-org $ORG --use-tooling-api --json 2>/dev/null

# Check agent (may not exist in all editions — auto-creation varies)
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null

# Check agent user (if agent exists)
sf data query -q "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null
```

**Note:** The agent is the `SalesAgent` BotDefinition — check for it directly. The agent user is NOT a substitute signal: it is provisioned with the PSGs during enablement and exists even when the agent was never created.

If the agent doesn't exist, see `references/agent-creation.md` for creation methods.

---

## Step 3b: Clone Flow from Template

The schedule-triggered flow must be cloned from the template `sales_pipe_mgmt__OppSuggGenSchFlow`. The template is provisioned on enablement but never activates.

**Detection (use SourceTemplateId — NOT label-based):**
```bash
# Check if user already cloned the template
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null
# If 0 records → need to clone
```

**Clone method:**

**Managed namespace flows CANNOT be retrieved via Metadata API or SOAP readMetadata** — both return nil/errors. The ONLY working method is:

1. **Manual clone via Setup UI:**
   - Navigate to Setup → Flows
   - Find "Opportunity Suggestion Generator Schedule Flow" (API name: `sales_pipe_mgmt__OppSuggGenSchFlow`)
   - Click "Save As..." to create a copy
   - Name it "Process Field Update Suggestions" (or any name you choose)
   - Set schedule start date to today or future date
   - Activate the flow

2. **Automation after manual clone:**

Once cloned via UI, you CAN retrieve and redeploy the CLONE (not the template) to automate activation:

```bash
# Retrieve your cloned flow (replace with your chosen name)
CLONE_NAME="Process_Field_Update_Suggestions"
sf project retrieve start --metadata "Flow:${CLONE_NAME}" --target-org $ORG --json 2>/dev/null

CLONE_FILE="force-app/main/default/flows/${CLONE_NAME}.flow-meta.xml"

# Transform status to Active and update schedule
sed -i '' 's|<status>Draft</status>|<status>Active</status>|g' "$CLONE_FILE"
TODAY=$(date +%Y-%m-%d)
sed -i '' "s|<startDate>[^<]*</startDate>|<startDate>${TODAY}</startDate>|g" "$CLONE_FILE"

# Deploy the activated flow
sf project deploy start --metadata "Flow:${CLONE_NAME}" --target-org $ORG --json 2>/dev/null
```

**Reference: Non-functional API retrieval (for future reference):**

```bash
# ❌ This ALWAYS FAILS — managed namespace flows are blocked from retrieval
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__OppSuggGenSchFlow" --target-org $ORG --json 2>/dev/null
# Error: "Entity of type 'Flow' named 'sales_pipe_mgmt__OppSuggGenSchFlow' cannot be found"

# ❌ SOAP readMetadata also returns nil
```

**Verify:**
```bash
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null
# Expected: IsActive = true
```

See `references/flow-clone-from-template.md` for complete details.

---

## Step 4: Assign Permissions

```bash
# Get PSG and user IDs
PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username = 'user@example.com'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

# Assign via Data API (works in all CLI versions)
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='${USER_ID}' PermissionSetGroupId='${PSG_ID}'" --target-org $ORG --json 2>/dev/null
# DUPLICATE_VALUE error means assignment already exists — that's success
```

**If using Agentforce Data Library:**
```bash
sf org assign permset --name DataCloudUser --on-behalf-of user@example.com --target-org $ORG --json 2>/dev/null
```

---

## Step 5: Define Opportunity Stage Descriptions

Stage descriptions are stored in `OpptStageDescription` (Tooling API entity). The agent reads these to understand stage semantics. **Stage suggestions fail if any active stage lacks a description.**

**CRITICAL — Visibility Prerequisite**: `OpptStageDescription` is ONLY visible via Tooling API AFTER Pipeline Management is enabled (Step 2 above). Queries return `INVALID_TYPE` or empty results before enablement. Do NOT attempt stage description queries before confirming `enableDealAgent=true`.

**Important:** Stage descriptions MAY be auto-provisioned when Pipeline Management is enabled. Always CHECK for existing descriptions first to avoid DUPLICATE_VALUE errors.

**Query active stages:**
```bash
sf data query -q "SELECT MasterLabel, ApiName FROM OpportunityStage WHERE IsActive = true ORDER BY SortOrder" --target-org $ORG --json 2>/dev/null
```

**Check for existing stage descriptions:**
```bash
sf data query -q "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" --target-org $ORG --use-tooling-api --json 2>/dev/null
```

**Check-then-create-or-update pattern:**

```bash
# Query existing descriptions
EXISTING=$(sf data query -q "SELECT Id, OpportunityStageApiName FROM OpptStageDescription WHERE OpportunityStageApiName='Prospecting'" --target-org $ORG --use-tooling-api --json 2>/dev/null)
RECORD_ID=$(echo "$EXISTING" | jq -r '.result.records[0].Id // empty')

if [ -z "$RECORD_ID" ]; then
  # Create new description
  sf data create record --sobject OpptStageDescription \
    --values "DeveloperName='Prospecting' MasterLabel='Prospecting' OpportunityStageApiName='Prospecting' Description='Initial outreach and qualification. Entry: Lead converted or manual creation. Exit: Meeting scheduled or qualified out.'" \
    --target-org $ORG --use-tooling-api --json 2>/dev/null
else
  # Update existing description
  sf data update record --sobject OpptStageDescription --record-id "$RECORD_ID" \
    --values "Description='Initial outreach and qualification. Entry: Lead converted or manual creation. Exit: Meeting scheduled or qualified out.'" \
    --target-org $ORG --use-tooling-api --json 2>/dev/null
fi
```

Repeat for all active stages. See `references/opportunity-stages.md` for default descriptions by methodology.

---

## Step 6: Verify Data Sources

The agent needs recent activity to generate suggestions:

```bash
# Check notes
sf data query -q "SELECT COUNT() FROM ContentNote WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null

# Check recent opportunities
sf data query -q "SELECT COUNT() FROM Opportunity WHERE LastActivityDate = LAST_N_DAYS:7 AND IsClosed = false" --target-org $ORG 2>/dev/null

# Check emails (if Einstein Activity Capture enabled)
sf data query -q "SELECT COUNT() FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null
```

If no recent activity, the agent will produce no suggestions even after full setup.

For configuring additional data sources (Einstein Conversation Insights, Einstein Activity Capture), see `references/data-sources.md`.

---

## Step 7: Enable Agent Analytics

Note: Not required for suggestion generation. Enables visibility into agent performance metrics.

Agent Analytics tracks suggestion acceptance rates. UI-only configuration:

1. Go to Setup → Einstein Feedback and Monitoring → Agent Analytics
2. Enable for the Sales Management agent
3. Configure tracking preferences

---

## Troubleshooting

**If agent doesn't exist after 30 minutes:**
- See `references/agent-creation.md` for agent creation methods. The `BotDefinition:SalesAgent` is created by `sf agent publish authoring-bundle --api-name SalesAgent` (wrapped by `publish_and_activate_agent()` in `shared/agent-bundle-publish.sh`); the SOAP `enableDealAgent` toggle only re-provisions the agent user and PSGs, not the BotDefinition.

**If flow doesn't clone successfully:**
- See `references/flow-clone-from-template.md` for detailed troubleshooting

**If partially configured:**
- See `references/repair-diagnostics.md` for diagnostic checklist

**If prerequisites fail to enable:**
- See `references/soap-api-enablement.md` for troubleshooting SOAP API calls

---

## Notes

- Always use `2>/dev/null` on `sf ... --json` piped to jq (strips CLI warnings that corrupt JSON)
- Do NOT use CLI Metadata deploy for DealAgent enablement — SOAP API v64.0 only
- Do NOT enable `BotSettings` — legacy messaging bots, unrelated
- Pipeline Management does NOT use a managed package
- Flow uses `getOrExecFieldUpdtSuggestion` action type (preserved in clone — no manual construction)
- Flow detection uses `SourceTemplateId` (NOT label-based)
