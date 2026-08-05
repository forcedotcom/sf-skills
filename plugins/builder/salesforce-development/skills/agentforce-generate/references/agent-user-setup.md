# Agent User Setup & Permission Model
Complete provisioning workflow for Einstein Agent Users and permission sets. Validated against ORM1, ORM2, AutomotiveSupport, and SalesforceProductAssistant agents.

---

## License Requirement
PID_DigitalAgent (typically included with Agentforce licenses)

## Agent Type Decision Matrix

| Aspect | AgentforceServiceAgent | AgentforceEmployeeAgent |
|--------|------------------------|-------------------------|
| **Use Case** | Customer-facing, external users | Internal employees |
| **Runs As** | Dedicated Einstein Agent User | Logged-in user |
| **Einstein Agent User?** | Required | Not needed |
| **System PS (`AgentforceServiceAgentUser`)** | Required | Not needed |
| **Custom PS (`{AgentName}_Access`)** | Assigned to agent user | Assigned to employees |
| **Data Cloud permset/PSL** (one of `GenieDataPlatformStarterPsl` PSL, `GenieUserEnhancedSecurity` PS, or `DataCloudUser` PS) | **Required when agent has `knowledge:` block** | Not needed |
| **`access.default_agent_user`** | Required | Omit unless a capability explicitly requires it |
| **Respects Sharing Rules** | No (consistent permissions) | Yes (user's data access) |

> **Why the Data Cloud permset name varies:** which permset/PSL grants Data Cloud access depends on org shape (scratch / Dev Edition / Trailhead trial / sandbox / production) and platform release. Three names are seen in the wild:
> - `GenieDataPlatformStarterPsl` — a Permission Set License (assigned via `PermissionSetLicenseAssign`, not `PermissionSetAssignment`).
> - `GenieUserEnhancedSecurity` — a Permission Set, label "Data Cloud User".
> - `DataCloudUser` — a Permission Set on some org shapes.
>
> The skill discovers which one exists in this org, then assigns it (Step 3b below). Hardcoding any single name fails on at least one org shape.

**How to check agent type**: Look at the `agent_type` field in the `config:` block of your `.agent` file, or query: `sf data query --json --query "SELECT DeveloperName, Type FROM BotDefinition WHERE DeveloperName = 'AgentName'" -o TARGET_ORG`

---

## CLI Fast Track: Complete Workflow

For CLI-first workflow (tested: ~8 minutes total):

```bash
# Step 1: Query existing Einstein Agent Users (30 seconds)
sf data query --json \
  --query "SELECT Id, Username, IsActive FROM User WHERE Profile.Name = 'Einstein Agent User' AND IsActive = true" \
  -o TARGET_ORG

# Step 2: Create Einstein Agent User (2 minutes)
# Get Profile ID (read result.records[0].Id from JSON response)
sf data query --json \
  --query "SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'" \
  -o TARGET_ORG

# For Production/Sandbox (non-scratch org):
# Use the ProfileId from the query above
sf data create record --json --sobject User --values \
  "Username=<agent_name>_user@<orgId>.ext \
   LastName=<AgentName> \
   Email=admin@example.com \
   Alias=<alias> \
   TimeZoneSidKey=America/Los_Angeles \
   LocaleSidKey=en_US \
   EmailEncodingKey=UTF-8 \
   ProfileId=<PROFILE_ID> \
   LanguageLocaleKey=en_US" \
  -o TARGET_ORG

# For Scratch Orgs (use user definition file):
# sf org create user --definition-file config/einstein-agent-user.json -o TARGET_ORG

# Step 3: Assign System Permission Set (1 minute)
sf org assign permset --json \
  --name AgentforceServiceAgentUser \
  --on-behalf-of <agent_name>_user@<orgId>.ext \
  -o TARGET_ORG

# Step 3b: Assign Data Cloud access (ONLY if agent has knowledge: block)
# Discovery-then-assign — see "Step 3b" section below for full procedure
# and Data Space scope manual fallback. Skip this step entirely for agents
# without knowledge grounding.

# Step 4: Deploy Custom Permission Set (3 minutes)
# (Create the .permissionset-meta.xml file first - see Section 3.2 template)
sf project deploy start --json \
  --metadata PermissionSet:<AgentName>_Access \
  -o TARGET_ORG

# Assign custom PS
sf org assign permset --json \
  --name <AgentName>_Access \
  --on-behalf-of <agent_name>_user@<orgId>.ext \
  -o TARGET_ORG

# Step 5: Verify All Permissions (1 minute)
sf data query --json \
  --query "SELECT PermissionSet.Name, PermissionSet.Label FROM PermissionSetAssignment WHERE Assignee.Username = '<agent_name>_user@<orgId>.ext' ORDER BY PermissionSet.Name" \
  -o TARGET_ORG

# Expected: AgentforceServiceAgentUser + <AgentName>_Access
#           Plus a Data Cloud permset/PSL if the agent has a knowledge: block (Step 3b)
#
# To check PSL assignments (different SObject than permsets):
sf data query --json \
  --query "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username = '<agent_name>_user@<orgId>.ext'" \
  -o TARGET_ORG

# Step 6: Deploy Agent Bundle (unpublished metadata)
sf project deploy start --json \
  --source-dir force-app/main/default/aiAuthoringBundles/<AgentName> \
  -o TARGET_ORG

# Step 7: Test BEFORE Publishing (recommended)
sf agent preview start --json \
  --api-name <AgentName> \
  -o TARGET_ORG
# Test all subagents and actions to verify permissions

# Step 8: Publish & Activate (only after testing passes)
sf agent publish authoring-bundle --json \
  --api-name <AgentName> \
  -o TARGET_ORG

sf agent activate --json \
  --api-name <AgentName> \
  -o TARGET_ORG
```

Critical notes:
- For **scratch orgs**, use `sf org create user --definition-file`
- For **production/sandbox**, use `sf data create record` as shown above
- `sf org create user` only works in scratch orgs — it will fail in production/sandbox
- Always test with preview BEFORE publishing to avoid version management overhead
- Assign `AgentforceServiceAgentUser` BEFORE publishing to prevent "Internal Error"
- Publishing does NOT activate — you must run `sf agent activate` separately

---

## Step 3b: Assign Data Cloud Access (Knowledge-Grounded Service Agents Only)

Run this ONLY when the agent has a top-level `knowledge:` block (i.e., it grounds answers on an Agentforce Data Library). Without Data Cloud access, the agent user cannot read the ADL's data space and `AnswerQuestionsWithKnowledge` returns empty `knowledgeSummary` — the anti-hallucination guard then refuses every utterance.

Skip this step for non-grounded agents.

### 3b.1 — Discover which Data Cloud permset/PSL exists in this org

Three names are seen in the wild; which one applies depends on org shape and platform release. Run both queries:

```bash
# (a) Look for the PSL form first (codey-cko2's preferred path):
sf data query --json \
  --query "SELECT DeveloperName FROM PermissionSetLicense WHERE DeveloperName = 'GenieDataPlatformStarterPsl' LIMIT 1" \
  -o TARGET_ORG

# (b) Look for the PS form(s) — the names that test-agent17 found working:
sf data query --json \
  --query "SELECT Name, Label FROM PermissionSet WHERE Name IN ('GenieUserEnhancedSecurity', 'DataCloudUser', 'DataCloudArchitect')" \
  -o TARGET_ORG
```

Pick **one** to assign, in this priority order:

1. `GenieDataPlatformStarterPsl` (PSL) — if (a) returned a record. Use the PSL flow.
2. `GenieUserEnhancedSecurity` (PS, label "Data Cloud User") — if (b) returned this name.
3. `DataCloudUser` (PS) — if (b) returned this name.
4. `DataCloudArchitect` (PS) — last resort; this is typically an admin permset (over-privileged for an agent user) but if nothing else exists in the org, it works.

If none of the four exist: Data Cloud is likely not provisioned. Run the Step 0 preflight from [Data Library Reference](data-library-reference.md) to confirm; if DC is missing, surface that to the user and skip ADL grounding for this run.

### 3b.2 — Assign

For a **PSL**, use `sf org assign permsetlicense`:

```bash
sf org assign permsetlicense --json \
  --name GenieDataPlatformStarterPsl \
  --on-behalf-of <agent_name>_user@<orgId>.ext \
  -o TARGET_ORG
```

For a **PS**, use `sf org assign permset`:

```bash
sf org assign permset --json \
  --name <PS_NAME_FROM_DISCOVERY> \
  --on-behalf-of <agent_name>_user@<orgId>.ext \
  -o TARGET_ORG
```

Both are idempotent — re-running on an already-assigned user returns success without effect.

### 3b.3 — Verify what landed (don't trust the apparent-success response)

Apex-driven assignments can silently roll back inside transactions, leaving the user with no permset while the API reports success. Read back from the assignment SObjects directly:

```bash
# Permsets (PS):
sf data query --json \
  --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '<agent_name>_user@<orgId>.ext'" \
  -o TARGET_ORG

# Permission set licenses (PSL — different SObject):
sf data query --json \
  --query "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username = '<agent_name>_user@<orgId>.ext'" \
  -o TARGET_ORG
```

The Data Cloud name you assigned in 3b.2 must appear in one of the two result sets. If it does not, the assignment failed silently — surface the failure and try the next-priority name from 3b.1.

### 3b.4 — Verify the assignment stuck (pinned to resolved IDs)

Run this in the main assignment flow, immediately after 3b.3 and before any code generation or preview. 3b.3 checks that a Data Cloud permset name appears for the agent user's `Username`. That is necessary but not sufficient: assignment writes can silently roll back inside an Apex transaction while the API reports success, and the "N rows for N users" shape of an unpinned query hides the specific miss. This step pins verification to the exact agent-user Id so a missing agent-user row is a HARD failure — not a row-count that happens to look plausible.

**The agent user is the one that must hold the assigned permset.** 3b.2 assigns the Data Cloud permset to the Einstein Agent User, which runs the retriever at runtime; if it is missing, grounding surfaces as empty `knowledgeSummary` and anti-hallucination refusals at preview/runtime. The running user (whoever runs `sf`, configuring the ADL) also needs Data Cloud access, but that access commonly comes from its profile (e.g. a System Administrator) rather than one of the discovered permsets — so the running user is a **soft** check here, not a hard gate.

**Resolve the agent-user Id first** (this is the pin):

```bash
sf data query --json \
  --query "SELECT Id, Username FROM User WHERE Username = '<agent_name>_user@<orgId>.ext'" \
  -o TARGET_ORG
# Read result.records[0].Id — this is the agent user's Id.
```

**Re-query the assignment SObject pinned to that Id.** Substitute the resolved agent-user Id and the exact PS/PSL name assigned in 3b.2:

```bash
# PS form (if 3b.2 assigned a PermissionSet):
sf data query --json \
  --query "SELECT AssigneeId, Assignee.Username, PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '<AGENT_USER_ID>' AND PermissionSet.Name = '<PS_NAME_FROM_3b.2>'" \
  -o TARGET_ORG

# PSL form (if 3b.2 assigned a PermissionSetLicense):
sf data query --json \
  --query "SELECT AssigneeId, Assignee.Username, PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE AssigneeId = '<AGENT_USER_ID>' AND PermissionSetLicense.DeveloperName = '<PSL_NAME_FROM_3b.2>'" \
  -o TARGET_ORG
```

**Assertion — read the returned `AssigneeId`, not the row count.** `<AGENT_USER_ID>` must appear in the `AssigneeId` column of the appropriate result. An empty result is a FAILURE — do not proceed on "a row came back" reasoning; the specific agent-user Id must be present.

**On failure:**
1. Re-run 3b.2 for the agent user, then re-run this 3b.4 verification once.
2. If the agent user is still missing after one retry, STOP. Surface which PS/PSL name did not stick. Do NOT proceed to code generation, deploy, publish, or preview — grounding will fail silently at runtime and the failure is easier to diagnose here than after a broken ship. If nothing in 3b.1's priority list assigns cleanly, treat this as a Data Cloud provisioning problem and re-run the Step 0 preflight from [Data Library Reference](data-library-reference.md).

When the agent-user Id appears for the intended PS/PSL, Step 3b's assignment gate is satisfied and callers upstream (SKILL.md, spec/orchestrator) can treat "Step 3b passed" as an authoritative gate on Data Cloud grounding access — no need to re-run inline SOQL from the caller. If grounded queries still return empty at runtime, apply the Data Space scope fallback in 3b.5.

### 3b.5 — Data Space scope (UI-only manual fallback if grounded queries still fail)

Some org shapes require a **separate** Data Space scope grant on the assigned permset, in addition to the assignment itself. There is currently no API for this — it must be done in Setup UI.

Do this only if 3b.1–3b.4 succeeded but the agent still returns empty `knowledgeSummary` at runtime:

> Setup → Permission Sets → click the assigned Data Cloud permset → "Data Cloud Data Space Management" under the Apps section → Edit → add the ADL's data space (typically `default`) to the **Enabled Data Spaces** list → Save.
>
> The data-space ID can be found via `sf data query --json -q "SELECT Id, DeveloperName FROM DataSpace"`.

After granting the scope, retest with a grounded utterance — the agent should now return populated `knowledgeSummary`.

---

## Service Agent Setup (6 Steps)

### Step 1: Create Einstein Agent User

Service agents need a dedicated service account with consistent permissions.

**Get Org ID first** (needed for username format):
```bash
sf org display --json -o TARGET_ORG
# Read result.id from the JSON response
```

**Query existing Einstein Agent Users** (skip creation if one exists):
```bash
sf data query --json --query "SELECT Id, Username, IsActive FROM User WHERE Profile.Name = 'Einstein Agent User' AND IsActive = true" -o TARGET_ORG
```

**Create the user** (if none exists):

1. Get the Einstein Agent User profile ID:
   ```bash
   sf data query --json --query "SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'" -o TARGET_ORG
   ```

2. Create a user definition file (`config/einstein-agent-user.json`):
   ```json
   {
     "Username": "{agent_name}_agent@{orgId}.ext",
     "LastName": "{AgentName} Agent",
     "Email": "placeholder@example.com",
     "Alias": "agntuser",
     "ProfileId": "<profile-id-from-step-1>",
     "TimeZoneSidKey": "America/Los_Angeles",
     "LocaleSidKey": "en_US",
     "EmailEncodingKey": "UTF-8",
     "LanguageLocaleKey": "en_US",
     "UserPermissionsKnowledgeUser": true
   }
   ```

3. Create the user:

   **Option A: Scratch Org (Definition File)**
   ```bash
   sf org create user --json \
     --definition-file config/einstein-agent-user.json \
     -o TARGET_ORG
   ```

   **Option B: Production/Sandbox (Direct Record Creation)**
   ```bash
   # Get Profile ID first
   # Get Profile ID (read result.records[0].Id from JSON response)
   sf data query --json \
     --query "SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'" \
     -o TARGET_ORG

   # Create user directly (use ProfileId from query above)
   sf data create record --json --sobject User --values \
     "Username='{agent_name}_agent@{orgId}.ext' LastName='{AgentName} Agent' Email='placeholder@example.com' Alias='agntuser' ProfileId='<PROFILE_ID>' TimeZoneSidKey='America/Los_Angeles' LocaleSidKey='en_US' EmailEncodingKey='UTF-8' LanguageLocaleKey='en_US'" \
     -o TARGET_ORG
   ```

   **Note**: `sf org create user` only works in scratch orgs. For production/sandbox, use `sf data create record`. Attempting `sf org create user` in a non-scratch org fails with an authorization error.

4. Verify creation:
   ```bash
   sf data query --json --query "SELECT Id, Username, IsActive FROM User WHERE Username = '{agent_name}_agent@{orgId}.ext'" -o TARGET_ORG
   ```

**Username format**: `{agent_name}_agent@{orgId}.ext` (production) or `{agent_name}.{suffix}@{orgfarm}.salesforce.com` (dev/scratch). Always query the target org to confirm the exact format.

---

### Step 2: Assign System Permission Set (`AgentforceServiceAgentUser`)

Critical: Must be assigned BEFORE publishing the agent. Without it, publish fails with "Internal Error".

Via Setup UI:
1. Setup > Permission Sets > search "AgentforceServiceAgentUser"
2. Manage Assignments > Add Assignments > select the Einstein Agent User > Save

Via CLI:
```bash
sf org assign permset --json --name AgentforceServiceAgentUser --on-behalf-of "{agent_name}_agent@{orgId}.ext" -o TARGET_ORG
```

Verify assignment:
```bash
sf data query --json --query "SELECT Id, PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '{agent_name}_agent@{orgId}.ext' AND PermissionSet.Name = 'AgentforceServiceAgentUser'" -o TARGET_ORG
```

---

### Step 3: Create Custom Permission Set for Apex Classes

The custom PS grants the agent user permission to execute your Apex invocable actions.

Naming convention: `{AgentName}_Access` (e.g., `AutomotiveSupport_Access`)

File: `force-app/main/default/permissionsets/{AgentName}_Access.permissionset-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Grants access to {AgentName} Agent Apex classes</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>{AgentName} Access</label>

    <!-- Add one entry per Apex class the agent calls -->
    <classAccesses>
        <apexClass>YourApexClassName</apexClass>
        <enabled>true</enabled>
    </classAccesses>
    <!-- Repeat for ALL Apex classes referenced via apex:// in agent script -->
</PermissionSet>
```

Key rule: Include EVERY Apex class referenced via `apex://` in your agent script. Missing even one causes "invocable action does not exist" at runtime.

Deploy the permission set:
```bash
sf project deploy start --json --source-dir force-app/main/default/permissionsets/{AgentName}_Access.permissionset-meta.xml -o TARGET_ORG
```

---

### Step 4: Assign Custom Permission Set to Agent User

Via CLI:
```bash
sf org assign permset --json --name {AgentName}_Access --on-behalf-of "{agent_name}_agent@{orgId}.ext" -o TARGET_ORG
```

Verify both permission sets are assigned:
```bash
sf data query --json --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '{agent_name}_agent@{orgId}.ext'" -o TARGET_ORG
```

Expected output includes both:
- `AgentforceServiceAgentUser` (system)
- `{AgentName}_Access` (custom)

---

### Step 5: Set `default_agent_user` in Agent Access

In your `.agent` file:
```yaml
access:
  default_agent_user: "{agent_name}_agent@{orgId}.ext"  # Service agents ONLY

config:
  developer_name: "AgentName"
  agent_description: "Your agent description"
  agent_type: "AgentforceServiceAgent"
```

---

### Step 6: Deploy, Test, Publish & Activate

**Validated workflow pattern**: Deploy as unpublished metadata, test with preview, then publish only when tests pass. This avoids version management overhead during iteration.

#### 6.1: Deploy Agent Bundle (Unpublished)

```bash
sf project deploy start --json \
  --source-dir force-app/main/default/aiAuthoringBundles/<AgentName> \
  -o TARGET_ORG
```

This deploys the agent as **unpublished metadata** — you can edit freely without version management.

#### 6.2: Test with Preview (Before Publishing)

```bash
sf agent preview start --json \
  --api-name <AgentName> \
  -o TARGET_ORG
```

What to test:
1. All subagents trigger correctly
2. All Apex actions execute without "Insufficient Privileges" errors
3. Agent responds with expected data
4. No compilation errors

If testing reveals problems, edit your agent script or Apex classes, redeploy, and test again — no publish required.

**⚠️ `WITH USER_MODE` Object Permissions:** Apex using `WITH USER_MODE` requires the Einstein Agent User to have read access on queried objects. Class-level access alone is not enough. Missing object permissions fail silently — 0 rows, no error. If live preview returns empty but simulated works, check Setup > Profiles > Einstein Agent User > Object Permissions. Fix by adding `<objectPermissions>` to your custom PS:

```xml
<objectPermissions>
    <allowRead>true</allowRead>
    <object>Vehicle__c</object>
</objectPermissions>
```

See [agent-validation-and-debugging.md](agent-validation-and-debugging.md) for the complete smoke-test and trace workflow.

#### 6.3: Publish Agent

Only publish after all tests pass.

```bash
sf agent publish authoring-bundle --json \
  --api-name <AgentName> \
  -o TARGET_ORG
```

**Publishing does NOT activate.** The new BotVersion is created as `Inactive`. You must explicitly activate.

#### 6.4: Activate Agent

```bash
sf agent activate --json \
  --api-name <AgentName> \
  -o TARGET_ORG
```

Note: `sf agent activate` may not support `--json` in all CLI versions. It prints a plain-text confirmation.

#### 6.5: Verify Activation

```bash
sf data query --json \
  --query "SELECT Id, DeveloperName, Status FROM BotVersion WHERE BotDefinition.DeveloperName = '<AgentName>' ORDER BY CreatedDate DESC LIMIT 1" \
  -o TARGET_ORG
```

Expected: `Status = 'Active'`

After publish: Any further changes require version management. Test thoroughly before publishing.

---

## Employee Agent Setup

Employee agents run as the logged-in user. The permission model is simpler.

### What You DO NOT Need

- No Einstein Agent User creation
- No `AgentforceServiceAgentUser` system permission set
- No `access.default_agent_user`

### What You DO Need

Custom permission set(s) assigned to **employees** who will use the agent.

### Step 1: Create Custom Permission Set

Same XML template as Step 3 above. Include `<classAccesses>` for all Apex classes the agent calls.

### Step 2: Assign to Employees

Assign the custom PS to employees (not to a service account):

```bash
sf org assign permset --json --name {AgentName}_Access --on-behalf-of "employee@company.com" -o TARGET_ORG
```

Or use Permission Set Groups for role-based access.

### Step 3: Configure Agent Script (No `access` Block)

```yaml
config:
  developer_name: "Employee_Agent"
  agent_description: "Internal employee assistant"
  agent_type: "AgentforceEmployeeAgent"
# No access.default_agent_user — the agent runs as the logged-in user
```

### Step 4: Publish

```bash
sf agent publish authoring-bundle --json --api-name Employee_Agent -o TARGET_ORG
```

---

## Auto-Generated Permission Set Warning

Salesforce auto-generates `NextGen_{AgentName}_Permissions` when an agent is published. Do NOT rely on this PS — it is often incomplete.

### ORM1 Testing Example
- Agent script referenced 4 Apex classes: `OrderManagementVerification`, `FraudRiskCalculator`, `OrderLookupService`, `ShipmentTracker`
- Auto-generated `NextGen_ORM1_Permissions` only included 3 classes (missing `ShipmentTracker`)
- Runtime error: "invocable action track_delivery does not exist"
- Fix: Created custom `ORM1_Access` with all 4 classes — no errors

Best practice: Always create your own custom `{AgentName}_Access` PS with explicit `<classAccesses>` for every Apex class. Ignore the auto-generated PS.

---

## End-to-End Verification Checklist

Run this combined query to verify all setup steps for a Service Agent:

```bash
# 1. Einstein Agent User exists and is active
sf data query --json --query "SELECT Id, Username, IsActive, Profile.Name FROM User WHERE Username = '{agent_name}_agent@{orgId}.ext'" -o TARGET_ORG

# 2. System PS assigned
sf data query --json --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '{agent_name}_agent@{orgId}.ext' AND PermissionSet.Name = 'AgentforceServiceAgentUser'" -o TARGET_ORG

# 3. Custom PS assigned
sf data query --json --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '{agent_name}_agent@{orgId}.ext' AND PermissionSet.Name = '{AgentName}_Access'" -o TARGET_ORG

# 4. All permission sets for user (combined view)
sf data query --json --query "SELECT PermissionSet.Name, PermissionSet.Label FROM PermissionSetAssignment WHERE Assignee.Username = '{agent_name}_agent@{orgId}.ext'" -o TARGET_ORG

# 5. Agent access has default_agent_user
# Check your .agent file's access: block

# 6. Agent publishes successfully
sf agent publish authoring-bundle --json --api-name AgentName -o TARGET_ORG
```

Checklist:
- [ ] Einstein Agent User created and active (`IsActive = true`)
- [ ] Profile is "Einstein Agent User" (or "Minimum Access - Salesforce")
- [ ] `AgentforceServiceAgentUser` system PS assigned
- [ ] Custom `{AgentName}_Access` PS deployed with ALL Apex classes
- [ ] Custom PS assigned to the agent user
- [ ] `default_agent_user` set in the `.agent` `access` block
- [ ] Agent tested with preview before publishing
- [ ] Agent publishes without error
- [ ] Agent activated (publish does NOT auto-activate)

---

## Common Pitfalls (Validated)

### 1. "Internal Error" on First Publish
- **Cause:** Publishing before assigning `AgentforceServiceAgentUser`
- **Prevention:** Assign system PS (Step 2) before publishing (Step 6.3)
- **Result:** First-time publish success (no retries needed)

### 2. "Insufficient Privileges" on Apex Actions
- **Cause:** Missing `<classAccesses>` in custom permission set
- **Prevention:** Custom PS template includes all Apex classes (Step 3)
- **Result:** All actions execute without permission errors

### 3. Testing After Publishing
- **Cause:** Publishing before testing, then needing version management for fixes
- **Prevention:** Deploy → Test → Publish workflow (Step 6.1-6.3)
- **Result:** No version management overhead during development

### 4. Wrong User Creation Command
- **Cause:** Using `sf org create user` in non-scratch orgs
- **Prevention:** Step 1 provides correct commands for each org type (Option A vs B)
- **Result:** User created successfully without authorization errors

### 5. Auto-Generated Permission Set Gaps
- **Cause:** Relying on `NextGen_{AgentName}_Permissions` (often incomplete)
- **Prevention:** Custom PS with explicit Apex access (Step 3)
- **Result:** All Apex classes accessible from the start

### 6. Forgot to Activate After Publish
- **Cause:** Assuming publish automatically activates
- **Prevention:** Step 6 splits publish and activate into separate steps with verification
- **Result:** Agent is both published AND activated

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Internal Error" on publish | `AgentforceServiceAgentUser` PS not assigned to Einstein Agent User | Assign system PS (Step 2), wait 2-3 min, retry publish |
| "Insufficient Privileges" at runtime | Custom PS missing or incomplete `<classAccesses>` | Verify custom PS includes ALL Apex classes, redeploy + reassign |
| "invocable action does not exist" | Apex class not in custom PS (auto-generated PS incomplete) | Create custom `{AgentName}_Access` with all `<classAccesses>` (Step 3) |
| "Invalid default_agent_user" | Username typo or user not active | Query Einstein Agent Users, verify exact username + `IsActive = true` |
| Agent runs but returns wrong data | Employee agent using wrong user context | Verify `agent_type` — Service agents use dedicated user, Employee agents use logged-in user |
| `sf org create user` fails | Used in production/sandbox org | Use `sf data create record` instead (Step 1, Option B) |

---

## Permission Set XML Template (Complete Example)

**AutomotiveSupport agent** (5 Apex classes):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Grants access to Automotive Support Agent Apex classes</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Automotive Support Access</label>

    <classAccesses>
        <apexClass>VehicleLookupService</apexClass>
        <enabled>true</enabled>
    </classAccesses>
    <classAccesses>
        <apexClass>ErrorCodeDiagnosticsService</apexClass>
        <enabled>true</enabled>
    </classAccesses>
    <classAccesses>
        <apexClass>CheckEngineDiagnosticsService</apexClass>
        <enabled>true</enabled>
    </classAccesses>
    <classAccesses>
        <apexClass>BehaviorAnalysisService</apexClass>
        <enabled>true</enabled>
    </classAccesses>
    <classAccesses>
        <apexClass>ServiceSchedulerService</apexClass>
        <enabled>true</enabled>
    </classAccesses>
</PermissionSet>
```

---

*Validated against: ORM1, ORM2, AutomotiveSupport, SalesforceProductAssistant agents. Last validated: 2026-03-07.*
