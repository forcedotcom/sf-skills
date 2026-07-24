# Repair Diagnostics for Partially Configured Orgs

This reference provides a complete diagnostic checklist for orgs with incomplete Pipeline Management configuration.

---

## Diagnostic Checklist

Run these checks in order to identify what's missing or misconfigured:

### 1. Prerequisites

`readMetadata` on `EinsteinGptSettings` (`EinsteinGpt`) → expect `<enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>`; `readMetadata` on `EinsteinCopilotSettings` (`EinsteinCopilot`) → expect `<enableEinsteinGptCopilot>true</enableEinsteinGptCopilot>`; `readMetadata` on `AgentPlatformSettings` (`AgentPlatform`) → expect `<enableAgentPlatform>true</enableAgentPlatform>`.

Canonical snippets: `references/soap-api-enablement.md` → **§1 Einstein Generative AI Platform**, **§2 Agentforce Agent**, and **§2b Agentforce Studio (Agent Platform)**.

**If any is false**: enable via the SOAP API using the same reference. `AgentPlatformSettings.enableAgentPlatform` gates the Deal Agent — a disabled state here explains an otherwise-opaque `SalesDealAgentSettings.enableDealAgent` failure.

### 2. Pipeline Management Enabled

`readMetadata` on `SalesDealAgentSettings` (`SalesDealAgent`) via API v64.0+ → expect `<enableDealAgent>true</enableDealAgent>`.

Canonical snippet: `references/soap-api-enablement.md` → **§6 Pipeline Management**.

**If false**: enable via the SOAP API v64.0 (same reference).

### 3. Permission Set Groups Exist

```bash
sf data query -q "SELECT Id, MasterLabel, DeveloperName FROM PermissionSetGroup WHERE DeveloperName IN ('SalesManagementUserPsg','SalesManagementAgentUserPsg')" --target-org $ORG --use-tooling-api --json 2>/dev/null
# Expected: 2 records
```

**If 0 records**: Pipeline Management not fully provisioned — toggle off/on via SOAP API

### 4. Sales Management Agent Exists

```bash
# The agent is the SalesAgent BotDefinition. Use standard SOQL (NOT --use-tooling-api,
# which does not support BotDefinition) and do NOT select Status (no such column).
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null
# Expected: 1 record
```

**If 0 records**: Agent not created — see `references/agent-creation.md`. Note the agent
user (checked separately below) is provisioned with the PSGs during enablement and exists
even when the agent does not, so it is NOT evidence the agent was created.

### 5. Agent User Exists

```bash
sf data query -q "SELECT Id, Username, IsActive FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null
# Expected: 1 record with IsActive = true
```

**If 0 records**: Agent user not created — see `references/agent-creation.md`  
**If IsActive = false**: Activate user via Data API or Setup UI

### 6. Agent User Has Correct PSG

```bash
AGENT_USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

sf data query -q "SELECT PermissionSetGroup.DeveloperName FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroup.DeveloperName = 'SalesManagementAgentUserPsg'" --target-org $ORG --json 2>/dev/null
# Expected: 1 record
```

**If 0 records**: PSG not assigned — assign via Data API

### 7. Schedule-Triggered Flow Exists and Is Active

```bash
sf data query -q "SELECT Id, ApiName, IsActive FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null
# Expected: 1 record with IsActive = true
```

**If 0 records**: Flow not cloned from template — see `references/flow-clone-from-template.md`  
**If IsActive = false**: Flow deactivated — reactivate via Tooling API PATCH or Metadata API deploy

### 8. Prompt Templates Exist

```bash
# Note: GenAiPromptTemplate is not queryable — check via flow retrieval or UI
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__GetOppGroundingData" --target-org $ORG --json 2>/dev/null
# If retrieval succeeds, prompt flow exists
```

**If retrieval fails**: Prompt templates not provisioned — toggle Pipeline Management off/on

### 9. Stage Descriptions Exist

```bash
sf data query -q "SELECT COUNT() FROM OpptStageDescription" --target-org $ORG --use-tooling-api --json 2>/dev/null
# Expected: At least 1 record per active stage
```

**If 0 records**: Stage descriptions missing — see `references/opportunity-stages.md`

### 10. Data Sources Have Recent Activity

```bash
# Notes
sf data query -q "SELECT COUNT() FROM ContentNote WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null

# Opportunities
sf data query -q "SELECT COUNT() FROM Opportunity WHERE LastActivityDate = LAST_N_DAYS:7 AND IsClosed = false" --target-org $ORG 2>/dev/null

# Emails (if Einstein Activity Capture enabled)
sf data query -q "SELECT COUNT() FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null
```

**If all 0**: No data sources — agent will produce no suggestions even if fully configured

---

## Common Repair Scenarios

### Scenario 1: Flow Deactivated

**Symptoms**: Agent exists, PSGs exist, but no `AiGenActionItem` records (`Type = 'FIELD_UPDATE'`) created

**Diagnosis**: Flow is inactive

**Fix**:
```bash
# Get flow ID
FLOW_ID=$(sf data query -q "SELECT Id FROM FlowDefinitionView WHERE SourceTemplateId='sales_pipe_mgmt__OppSuggGenSchFlow' AND IsTemplate=false" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

# Reactivate via Tooling API PATCH
curl -X PATCH "${INSTANCE_URL}/services/data/v64.0/tooling/sobjects/Flow/${FLOW_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"Metadata":{"status":"Active"}}' 2>/dev/null
```

### Scenario 2: Agent Not Active

**Symptoms**: `BotDefinition` exists but `BotVersion.Status = 'Inactive'`

**Diagnosis**: Agent exists but not activated

**Fix** — preferred method (matches `scripts/create-agent.sh` and `references/agent-creation.md`):
```bash
# Resolve the latest published version and activate it.
# Retry on transient NoAgentsInOrgError right after publish.
VERSION=$(sf data query -q "SELECT VersionNumber FROM BotVersion WHERE BotDefinition.DeveloperName = 'SalesAgent' ORDER BY VersionNumber DESC LIMIT 1" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].VersionNumber // empty')
if [[ -z "$VERSION" ]]; then
  echo "Error: BotVersion not found or not queryable yet"
  echo "The agent may have been published but BotVersion is not provisioned yet (async)"
  exit 1
fi
sf agent activate --api-name SalesAgent --version "$VERSION" --target-org $ORG --json
```

**Fallback** — Metadata API (only if `sf agent activate` is unavailable or fails):
```bash
sf project retrieve start --metadata "Bot:SalesAgent" --target-org $ORG --json 2>/dev/null
# Edit force-app/main/default/bots/SalesAgent.bot-meta.xml
sed -i '' 's|<status>Draft</status>|<status>Active</status>|g' force-app/main/default/bots/SalesAgent.bot-meta.xml
sf project deploy start --metadata "Bot:SalesAgent" --target-org $ORG --json 2>/dev/null
```

### Scenario 3: Agent Doesn't Exist

**Symptoms**: PSGs exist but `BotDefinition` query returns 0 records

**Diagnosis**: Agent auto-creation failed

**Fix**: Publish the authoring bundle — `bash scripts/create-agent.sh <org-alias>` checks for the `SalesAgent` BotDefinition and, only if it is missing, publishes the bundle to create it (then activates). Do NOT use the SOAP `enableDealAgent` toggle to "re-provision" the agent; cycling the flag only re-creates the agent user and PSGs, not the agent. See `references/agent-creation.md`.

### Scenario 4: Missing Stage Descriptions

**Symptoms**: Next Step suggestions work, but Stage suggestions never appear

**Diagnosis**: No `OpptStageDescription` records

**Fix**: See `references/opportunity-stages.md` for bulk-create script

### Scenario 5: Permission Set Group Not Assigned

**Symptoms**: User can't see Pipeline Inspection or agent doesn't generate suggestions

**Diagnosis**: User missing `SalesManagementUserPsg` or agent missing `SalesManagementAgentUserPsg`

**Fix**:
```bash
# For user
PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username = 'user@example.com'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='${USER_ID}' PermissionSetGroupId='${PSG_ID}'" --target-org $ORG --json 2>/dev/null

# For agent
AGENT_PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementAgentUserPsg'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
AGENT_USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='${AGENT_USER_ID}' PermissionSetGroupId='${AGENT_PSG_ID}'" --target-org $ORG --json 2>/dev/null
```

### Scenario 5b: Agent Access Not Defined (users can't launch the agent) — W-23242378

**Symptoms**: The agent is active and users hold `SalesManagementUserPsg`, but users cannot launch or chat with the Sales Agent (it does not appear as an available agent for them).

**Diagnosis**: The Pipeline Management agent (a `BotDefinition` matched by `AgentTemplate`) has not been added to the **Agent Access** section of any permission set the users hold. Agent Access can only live on a **custom** permission set — the managed `SalesManagementUserPsg` cannot be edited directly. Verify:
```bash
# Custom access permset present?
sf data query -q "SELECT Id FROM PermissionSet WHERE Name = 'Sales_Agent_Access'" --target-org $ORG --json 2>/dev/null
# Agent granted on it? (BotDefinition detected by AgentTemplate, not a hardcoded name)
# Two-step lookup: find the bot by AgentTemplate, then confirm it has an Active
# BotVersion. The single-query correlated-subquery form hangs 60+s on some orgs.
BOT_DEF_ID=$(sf data query -q "SELECT Id FROM BotDefinition WHERE AgentTemplate IN ('SalesMgmt__NGASalesAgent','SalesMgmt__SalesAgent') ORDER BY LastModifiedDate DESC LIMIT 1" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
ACTIVE_COUNT=$(sf data query -q "SELECT COUNT() FROM BotVersion WHERE BotDefinitionId = '${BOT_DEF_ID}' AND Status = 'Active'" --target-org $ORG --json 2>/dev/null | jq -r '.result.totalSize // 0')
PS_ID=$(sf data query -q "SELECT Id FROM PermissionSet WHERE Name = 'Sales_Agent_Access'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data query -q "SELECT Id FROM SetupEntityAccess WHERE ParentId = '${PS_ID}' AND SetupEntityId = '${BOT_DEF_ID}'" --target-org $ORG --json 2>/dev/null
```

**Fix**: Run the dedicated script (idempotent — safe to re-run):
```bash
bash scripts/define-agent-access.sh $ORG
```
It creates the custom permset `Sales_Agent_Access` (License=None), grants Agent Access to the Pipeline Management BotDefinition (`SetupEntityAccess`, standard Data API — `SetupEntityType` is derived, do NOT set it), links the permset into `SalesManagementUserPsg` via `PermissionSetGroupComponent` (Tooling API), and confirms the PSG recalculates (poll `Status` until `Updated`). If the custom permset can't be linked into the managed PSG, it falls back to assigning the permset directly to the PSG's users.

**Fallback limitations** — the direct-assignment fallback only runs when the component link into the managed PSG fails, and it has two constraints worth knowing:
- **Point-in-time only**: it assigns the permset to users who hold the PSG *at the moment the script runs*. Users granted `SalesManagementUserPsg` *afterward* will NOT automatically get `Sales_Agent_Access` — you must re-run the script for them. (When the component link succeeds, this is a non-issue: PSG recalculation reaches all current and future members.)
- **Bounded fan-out**: the fallback processes at most 200 users (one sequential API call each). On larger orgs, fix the component link instead of relying on the fallback, so a single recalculation covers everyone.

**Note**: The autonomous agent user does NOT need Agent Access — this is only for human interactive users.

### Scenario 6: No Recent Data Sources

**Symptoms**: Everything configured correctly but no suggestions generated

**Diagnosis**: No recent notes, emails, or opportunities

**Fix**: 
- Create test notes on open opportunities
- Verify Einstein Activity Capture is syncing emails
- Verify Einstein Conversation Insights is syncing call transcripts
- Wait for next flow run (daily schedule)

---

## Complete Repair Script

For a comprehensive configuration check covering all components, use the dedicated verification script:

```bash
bash scripts/verify-all.sh <org-alias>
```

This runs all diagnostic checks (Prerequisites, Agent, PSGs, Flow, Stage Descriptions, Data Sources) and reports PASS/WARN/FAIL for each component with actionable fix instructions.

For individual component repair, use the targeted scripts:
- `scripts/enable-deal-agent.sh` — Re-enable Pipeline Management
- `scripts/create-flow.sh` — Deploy or activate the suggestion flow
- `scripts/create-agent.sh` — Re-provision agent user
- `scripts/define-agent-access.sh` — Define Agent Access so users can launch the agent (W-23242378)

---

## Notes

- Always run diagnostics top-to-bottom (prerequisites first, then features)
- Use SOAP API for Settings verification (most reliable)
- `BotDefinition` may not be queryable even when agent exists (depends on provisioning state)
- The authoritative enablement indicator is `SalesDealAgentSettings.enableDealAgent` (SOAP `readMetadata`). Partial configuration ("setup has run") is signaled by ANY of: an agent user holding `SalesManagementAgentUserPsg`, a scheduled flow cloned from `sales_pipe_mgmt__OppSuggGenSchFlow` (`IsTemplate=false`), or a PM `BotDefinition`. Permission set group existence alone only means the org holds the Agentforce-for-Sales license — it is NOT an enablement indicator
- Always use `2>/dev/null` on `sf ... --json` piped to jq
