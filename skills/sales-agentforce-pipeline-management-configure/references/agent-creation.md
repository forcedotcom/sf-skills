# Agent Creation and Activation

A standalone `BotDefinition:SalesAgent` is **REQUIRED** for Pipeline Management. Auto-provisioning creates it in most editions; where it does not, the setup scripts publish it from the authoring bundle. Users need the interactive chat surface, so treating "Platform Copilot only" as acceptable leaves setup incomplete — the scripts enforce this and will fail without it.

---

## Required Components

Every Pipeline Management org must have all three of the following:

- ✅ **Agent user** — `salesmanagementagentuser@<uuid>.ext`; runs the schedule-triggered suggestion flow
- ✅ **Permission set groups** — `SalesManagementUserPsg` (end users) and `SalesManagementAgentUserPsg` (agent user); the second must be assigned to the agent user so the flow can read/write opportunities
- ✅ **`BotDefinition:SalesAgent`** — active; enables the interactive chat interface

The schedule-triggered flow (`Process_Field_Update_Suggestions`) runs as the agent user and calls `getOrExecFieldUpdtSuggestion` actions directly. The BotDefinition is what lets users chat with the agent — it is not optional.

`create-agent.sh` and `setup-all.sh` enforce all three: if `BotDefinition:SalesAgent` is missing, they publish it via `sf agent publish authoring-bundle --api-name SalesAgent` (wrapped by `publish_and_activate_agent()` in `shared/agent-bundle-publish.sh`) and activate it. `GenAiPlannerDefinition:EmployeeCopilotPlanner` may still be present alongside the BotDefinition — that is fine, but it does not substitute for the BotDefinition.

---

## Agent Type Distinction

Pipeline Management's required agent is a **classic Bot agent** (metadata type: `BotDefinition`/`Bot`), developer name `SalesAgent`. `GenAiPlannerDefinition:EmployeeCopilotPlanner` (metadata type: `GenAiPlannerDefinition`) may also be present in the org; when it is, PM plugins wire into it, but the planner does not replace the required `BotDefinition`.

The `sf agent generate authoring-bundle` / `sf agent publish authoring-bundle` CLI commands publish an `AiAuthoringBundle` that creates the required `BotDefinition:SalesAgent`. The authoring bundle asset in `assets/` is the canonical fallback path when auto-provisioning did not create the BotDefinition — it is not a last-resort curiosity, it is what `create-agent.sh` and `setup-all.sh` invoke.

---

## Detection: Verify Required Components

```bash
ORG="pipeline-mgmt-org"

# Step 1: Check for agent user (PRIMARY functional indicator)
sf data query -q "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null

# Step 2: Check for standalone BotDefinition (standard SOQL — NOT --use-tooling-api)
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null

# Step 3: Check for Platform Copilot planner (Tooling API) — informational only; presence does NOT substitute for BotDefinition
sf data query -q "SELECT Id, DeveloperName FROM GenAiPlannerDefinition WHERE DeveloperName = 'EmployeeCopilotPlanner'" --target-org $ORG --use-tooling-api --json 2>/dev/null

# Step 4: Check PSG assignment to agent user
AGENT_USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data query -q "SELECT PermissionSetGroup.DeveloperName FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroupId != null" --target-org $ORG --json 2>/dev/null
```

**Decision matrix**:

| Agent User | BotDefinition | Planner | Result | Action |
|-----------|---------------|---------|--------|--------|
| ✅ | ✅ | any | **Complete** — all required components present | ✅ No action needed |
| ✅ | ❌ | any | **Missing BotDefinition** — required for chat surface | **Publish authoring bundle** (`sf agent publish authoring-bundle --api-name SalesAgent`) — this is the ONLY path that creates the BotDefinition |
| ❌ | any | any | **Provisioning failed** — no agent user | See Creation Methods below: SOAP toggle re-provisions agent user + PSGs; then publish the bundle to create the BotDefinition |

The Planner column is informational: `EmployeeCopilotPlanner` may or may not be present in the org, but its presence never substitutes for `BotDefinition:SalesAgent`.

---

## Creation Method 1: Auto-Provisioning + Bundle Publish (Primary)

When Pipeline Management (`SalesDealAgentSettings.enableDealAgent`) is enabled, the platform auto-provisions:
- Agent user (`salesmanagementagentuser@<uuid>.ext`)
- Permission set groups `SalesManagementUserPsg` and `SalesManagementAgentUserPsg` (the latter assigned to the agent user)

Enabling `enableDealAgent` does NOT create `BotDefinition:SalesAgent`. The BotDefinition must be created explicitly by publishing the authoring bundle:

```bash
sf agent publish authoring-bundle --api-name SalesAgent --target-org $ORG --json
```

`create-agent.sh` and `setup-all.sh` invoke this via `publish_and_activate_agent()` in `shared/agent-bundle-publish.sh`. **Publishing the bundle is the only path that creates the BotDefinition** — see Method 2 for cases where the agent user or PSGs are also missing.

---

## Creation Method 2: SOAP Toggle (agent user + PSGs only — does NOT create the BotDefinition)

If the **agent user** or **permission set groups** are missing (auto-provisioning did not complete), toggling `SalesDealAgentSettings.enableDealAgent` off and back on re-runs the platform provisioning and re-creates them. This does **NOT** create the `BotDefinition:SalesAgent` — you must still publish the authoring bundle (Method 1) afterward.

**When to use**: agent user query returns 0 records, or PSGs are missing. Do NOT use this to try to "re-provision" a missing BotDefinition — the toggle has never created a BotDefinition and never will.

**Warning**: Disabling Pipeline Management temporarily removes the agent user and PSGs, which stops in-flight suggestion generation.

### Toggle Script

```bash
ORG="pipeline-mgmt-org"
AUTH_INFO=$(sf org display --target-org $ORG --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$AUTH_INFO" | jq -r '.result.accessToken')
INSTANCE_URL=$(echo "$AUTH_INFO" | jq -r '.result.instanceUrl')

echo "=== Step 1: Disable Pipeline Management ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>SalesDealAgent</met:fullName>
      <met:enableDealAgent>false</met:enableDealAgent>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|message)"

echo "=== Waiting 10 seconds for propagation ==="
sleep 10

echo "=== Step 2: Re-enable Pipeline Management ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>SalesDealAgent</met:fullName>
      <met:enableDealAgent>true</met:enableDealAgent>
      <met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|message)"

echo "=== Waiting 30 seconds for agent provisioning ==="
sleep 30

echo "=== Verifying agent exists ==="
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null
```

**Why this works**: Disabling Pipeline Management deprovisions the auto-created agent user and PSGs; re-enabling triggers a fresh provisioning cycle that re-creates them. The `BotDefinition:SalesAgent` is **not** touched by this cycle in either direction — publishing the authoring bundle (Method 1) is the only way to create it.

**Risk**: If the org had custom configurations wired to the PSGs (permission set component additions, custom user assignments), these may be lost. Use this method **only when the agent user or PSGs are missing** — for a missing BotDefinition, go straight to Method 1.

---

## Creation Method 3: Metadata API Deploy (Manual)

If the SOAP toggle approach doesn't create the agent (rare — usually indicates missing prerequisites), deploy Bot metadata directly:

```bash
ORG="pipeline-mgmt-org"

# 1. Check if another org has a working SalesAgent to use as reference
# Or create the metadata from scratch:
mkdir -p force-app/main/default/bots

cat > force-app/main/default/bots/SalesAgent.bot-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Bot xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>SalesAgent</fullName>
    <label>Sales Management Agent</label>
    <description>Provides opportunity field update suggestions based on notes, emails, and conversation insights.</description>
    <type>Bot</type>
    <status>Active</status>
</Bot>
EOF

# 2. Deploy
sf project deploy start --metadata "Bot:SalesAgent" --target-org $ORG --json 2>/dev/null
```

**Note**: This method requires that all prerequisites are already enabled (Einstein GenAI, Agentforce, Pipeline Management settings). The deployed agent may lack auto-provisioned topics/actions — these must be configured separately. Also, the `<status>Active</status>` above does **not** actually activate the BotVersion (metadata-deploy activation silently fails) — after deploying, activate with `sf agent activate` (see Agent Activation → Method 1).

---

## Activation Verification

After creation (any method), verify the agent is active:

```bash
# Check agent status (standard SOQL — NOT --use-tooling-api)
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null

# If found: agent exists (BotDefinition does not expose Status via SOQL)
# If 0 records: agent not created (may be normal — see Detection section)
```

---

## Agent Activation (if the auto-provisioned BotVersion is Inactive)

### Method 1: `sf agent activate` (PRIMARY — the working method)

Publishing the authoring bundle creates the `BotDefinition` and an auto-provisioned
`BotVersion` that lands **Inactive**. Activate that version directly:

```bash
sf agent activate --api-name SalesAgent --version 1 --target-org $ORG --json 2>/dev/null
```

`create-agent.sh` / `setup-all.sh` run this after publishing the bundle. Verify with the
`BotVersion ... Status = 'Active'` query in the Activation Verification section.

> **Do NOT rely on a `Bot:SalesAgent` metadata deploy with `<status>Active</status>`** — it
> reports success but **silently fails to activate** the BotVersion (org-verified). Use
> `sf agent activate`.
>
> `sf agent activate` (bare) is correct here. `sf agent activate authoring-bundle` is a
> *different* command that targets Agent Script agents (AiAuthoringBundle) — do NOT use that
> subcommand for Pipeline Management's BotDefinition agent.

### Method 2: Setup UI (fallback)

If `sf agent activate` is unavailable, use Setup:

1. Setup → Agents → Find "Sales Management Agent"
2. Click Activate

---

## Agent User Configuration

The agent runs as a system user (`salesmanagementagentuser@<uuid>.ext`) that needs:
1. **Permission Set Group**: `SalesManagementAgentUserPsg` (auto-assigned on creation)
2. **Opportunity Team Member Access**: Agent must be able to join opportunity teams to read/write opportunity fields

### Verify Agent User Permissions

```bash
# Get agent user ID
AGENT_USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

# Check PSG assignment
sf data query -q "SELECT PermissionSetGroup.DeveloperName FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroup.DeveloperName = 'SalesManagementAgentUserPsg'" --target-org $ORG --json 2>/dev/null

# Check if agent can query opportunities
sf data query -q "SELECT COUNT() FROM Opportunity" --target-org $ORG --json 2>/dev/null
# If this fails, agent doesn't have Read access to opportunities
```

### Manual PSG Assignment (if missing)

```bash
PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementAgentUserPsg'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

sf data create record --sobject PermissionSetAssignment --values "AssigneeId='${AGENT_USER_ID}' PermissionSetGroupId='${PSG_ID}'" --target-org $ORG --json 2>/dev/null
```

---

## Agent Access — Letting Users Launch the Agent (W-23242378)

Creating and activating the agent is **not sufficient** for end users to use it. The agent must also be added to the **Agent Access** section of a permission set that those users hold. Without this, a user assigned `SalesManagementUserPsg` sees the agent as unavailable even though it is active.

### Why a custom permission set is required

Agent Access is stored as a `SetupEntityAccess` record with `SetupEntityType='BotDefinition'`. Its `ParentId` must be a **PermissionSet** — and only a **custom** permission set can hold it. `SalesManagementUserPsg` is a **managed** permission set group; its Agent Access cannot be edited directly. So the pattern is:

1. Create a **custom** permission set (`Sales_Agent_Access`, `License = None`).
2. Grant Agent Access on it (add the Pipeline Management BotDefinition).
3. Add that custom permset as a **component** of `SalesManagementUserPsg`.
4. Recalculate the PSG so users inherit the access.

### Automated (recommended)

```bash
# Idempotent — safe to re-run. Must run AFTER the agent (BotDefinition) exists.
bash scripts/define-agent-access.sh <org-alias>
```

`setup-all.sh` runs this automatically (Phase 4c), and `create-agent.sh` calls it at the end.

**Bot-timing behavior (exit 0, not exit 1)**: Agent Access can only be defined once the agent exists and has an **Active** `BotVersion`. If the script runs before the agent is created (or before its version is activated), it prints a warning and **exits 0** — a deliberate non-error so that an orchestrating run (`setup-all.sh`) is not aborted just because the agent isn't ready yet. This is why running it early is harmless: re-run it after the agent is active and it will complete the grant. It exits non-zero only for genuine failures (bad org alias, missing `jq`/`sf`, PSG recalculation `Failed`, or an un-tolerated create error).

### Manual / API details

```bash
ORG="pipeline-mgmt-org"

# 1. BotDefinition Id — detect by AgentTemplate (the field the scheduled flow uses),
#    NOT a hardcoded DeveloperName. Only bots with an Active BotVersion qualify.
# Use a TWO-STEP query, not a correlated subquery: the single-query form
# `AND Id IN (SELECT BotDefinitionId FROM BotVersion WHERE Status = 'Active')`
# hangs 60+ seconds on some orgs and was removed in de77d520. First find the
# bot by AgentTemplate, then confirm it has an Active BotVersion separately.
BOT_DEF_ID=$(sf data query -q "SELECT Id FROM BotDefinition WHERE AgentTemplate IN ('SalesMgmt__NGASalesAgent','SalesMgmt__SalesAgent') ORDER BY LastModifiedDate DESC LIMIT 1" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data query -q "SELECT COUNT() FROM BotVersion WHERE BotDefinitionId = '${BOT_DEF_ID}' AND Status = 'Active'" --target-org $ORG --json 2>/dev/null  # expect totalSize >= 1

# 2. Create the custom permission set (standard Data API — omit License => None; required fields Name + Label)
PS_ID=$(sf data create record --sobject PermissionSet --values "Name='Sales_Agent_Access' Label='Sales Agent Access'" --target-org $ORG --json 2>/dev/null | jq -r '.result.id')

# 3. Grant Agent Access (SetupEntityAccess: Create/Delete/Query only — no Update).
#    Do NOT set SetupEntityType — it is derived from SetupEntityId. Requires API v64.0+.
sf data create record --sobject SetupEntityAccess --values "ParentId='${PS_ID}' SetupEntityId='${BOT_DEF_ID}'" --target-org $ORG --json 2>/dev/null

# 4. Link the custom permset into the managed PSG (PermissionSetGroupComponent is a TOOLING API object)
PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" --target-org $ORG --use-tooling-api --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data create record --sobject PermissionSetGroupComponent --values "PermissionSetGroupId='${PSG_ID}' PermissionSetId='${PS_ID}'" --target-org $ORG --use-tooling-api --json 2>/dev/null

# 5. Recalculate the PSG (no dedicated CLI verb — the component insert in step 4
#    is what triggers the async recalc; poll PermissionSetGroup.Status via Tooling
#    API until 'Updated'). Status is system-computed, NOT client-writable — writing
#    it (e.g. a PATCH) is rejected with a non-2xx (typically HTTP 400) and does
#    nothing, so the script does not attempt it: polling is the only mechanism.
```

**Key constraints**:
- `SetupEntityAccess` requires a **custom** permission set as `ParentId` — a managed/standard permission set is rejected.
- `SetupEntityType` is read-only/derived — setting it on insert errors.
- `PermissionSetGroupComponent` is Tooling-API-only (`--use-tooling-api`). A **custom** permset CAN be linked into the **managed** `SalesManagementUserPsg`.
- Adding a component triggers **automatic async recalculation**; `PermissionSetGroup.Status` is system-computed (Updated/Updating/Outdated/Failed) — poll it, do not try to write it.
- The BotDefinition is detected by `AgentTemplate` (`SalesMgmt__NGASalesAgent` / `SalesMgmt__SalesAgent`), so the grant matches whatever local name the agent was published with.
  - Two templates exist for historical reasons: `SalesMgmt__SalesAgent` is the **legacy** template, and `SalesMgmt__NGASalesAgent` is the newer **NGA** ("Next-Gen Agent") template that the current authoring bundle publishes. Detection matches either so the script works on both older and newer orgs; when both are present, **NGA is preferred** (it is the forward direction).
- The autonomous **agent user** does NOT need Agent Access — this is for **human interactive users** only.

---

## Troubleshooting

### Auto-provisioning didn't create agent

**Symptom**: Enabled Pipeline Management but `BotDefinition` query returns 0 records

**Cause**: Missing prerequisites or edition limitation

**Fix**:
1. Verify all prerequisites enabled (see `references/setup-order.md`)
2. Wait up to 5 minutes (agent user + PSG provisioning is async)
3. If the **BotDefinition** is missing → publish the authoring bundle (Method 1) — this is the only path
4. If the **agent user or PSGs** are missing → use SOAP toggle (Method 2) to re-provision those, then publish the bundle
5. If bundle publish itself fails, fall back to Metadata API deploy (Method 3)

### Agent creation succeeds but agent is not active

**Symptom**: `BotDefinition` exists but its `BotVersion` is Inactive

**Cause**: Agent was created but the auto-provisioned BotVersion was never activated

**Fix**: `sf agent activate --api-name SalesAgent --version 1` (see Agent Activation → Method 1). A `Bot:SalesAgent` metadata deploy with `<status>Active</status>` silently fails to activate — do not rely on it.

### Toggle didn't create the BotDefinition

**Symptom**: After toggling `enableDealAgent` off and back on, the agent user and PSGs came back but `BotDefinition:SalesAgent` still returns 0 records.

**Cause**: This is expected — the SOAP toggle does not create the BotDefinition. The toggle only re-provisions the agent user and PSGs.

**Fix**: Publish the authoring bundle:
```bash
sf agent publish authoring-bundle --api-name SalesAgent --target-org $ORG --json
```
Or run `bash scripts/create-agent.sh <org-alias>`, which wraps `publish_and_activate_agent()` and only publishes when the BotDefinition is missing.

If the bundle publish itself fails, verify prerequisites (see `references/setup-order.md`) and check the edition/license in Setup → Company Information.

### Agent exists but doesn't generate suggestions

**Symptom**: Agent is active but no `AiGenActionItem` records (`Type = 'FIELD_UPDATE'`) are created

**Cause**: 
- Flow is not active (see `references/flow-clone-from-template.md`)
- Stage descriptions missing (see `references/opportunity-stages.md`)
- No data sources (no recent notes, emails, or calls)
- Agent user doesn't have opportunity access

**Fix**: See `references/repair-diagnostics.md` for full checklist

---

## Decision Matrix: Which Creation Method to Use

| Scenario | Use Method |
|----------|------------|
| First enablement (greenfield org) | Method 1 — auto-provisioning creates agent user + PSGs; publish bundle to create BotDefinition |
| `BotDefinition:SalesAgent` missing (any org) | Method 1 (publish authoring bundle) — the SOAP toggle will NOT create it |
| Agent user or PSGs missing (BotDefinition may also be missing) | Method 2 (SOAP toggle) to re-provision the user + PSGs, then Method 1 to create the BotDefinition |
| Production org with active users | Method 1 only when possible (toggle causes brief downtime and can drop custom PSG components) |
| Bundle publish fails | Method 3 (Metadata API deploy) as a last resort |

---

## Notes

- Pipeline Management uses a classic `BotDefinition` agent, NOT an `AiAuthoringBundle` (Agent Script) agent
- `sf agent generate/validate/publish authoring-bundle` commands create Agent Script agents — do NOT use these for Pipeline Management
- The SOAP `enableDealAgent` toggle re-provisions only the agent user and PSGs — it does NOT create or re-create `BotDefinition:SalesAgent`. Publishing the authoring bundle is the only path that creates the BotDefinition.
- SOAP toggle causes temporary Pipeline Management downtime (suggestions stop generating during toggle)
- Agent creation is asynchronous — may take up to 5 minutes after enablement
- Agent user is auto-created with agent and auto-assigned `SalesManagementAgentUserPsg`
- Agent must be active AND have opportunity access to generate suggestions
- Always use `2>/dev/null` on `sf ... --json` piped to jq
