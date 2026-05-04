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
| **`default_agent_user` in config** | Required | Omit entirely |
| **Respects Sharing Rules** | No (consistent permissions) | Yes (user's data access) |

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

### Step 5: Set `default_agent_user` in Agent Config

In your `.agent` file:
```yaml
config:
  developer_name: "AgentName"
  agent_description: "Your agent description"
  agent_type: "AgentforceServiceAgent"
  default_agent_user: "{agent_name}_agent@{orgId}.ext"  # Service agents ONLY
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

See [preview-test-loop.md](preview-test-loop.md) for the complete smoke test workflow.

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
- No `default_agent_user` in agent config

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

### Step 3: Configure Agent Script (No `default_agent_user`)

```yaml
config:
  developer_name: "Employee_Agent"
  agent_description: "Internal employee assistant"
  agent_type: "AgentforceEmployeeAgent"
  # NO default_agent_user — agent runs as logged-in user
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

# 5. Agent config has default_agent_user
# Check your .agent file's config: block

# 6. Agent publishes successfully
sf agent publish authoring-bundle --json --api-name AgentName -o TARGET_ORG
```

Checklist:
- [ ] Einstein Agent User created and active (`IsActive = true`)
- [ ] Profile is "Einstein Agent User" (or "Minimum Access - Salesforce")
- [ ] `AgentforceServiceAgentUser` system PS assigned
- [ ] Custom `{AgentName}_Access` PS deployed with ALL Apex classes
- [ ] Custom PS assigned to the agent user
- [ ] `default_agent_user` set in `.agent` config block
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
