# Org Setup for ADL

Configure a fresh Salesforce org so it's ready for Agentforce Data Library (ADL) usage — all three source types (SFDRIVE, KNOWLEDGE, RETRIEVER).

## Overview

The ADLC `/agentforce-generate` skill assumes the org is already configured for ADL. A fresh org (even with correct licenses provisioned) still needs several setup steps before ADL can work. This skill automates those steps via SF CLI.

**What this skill sets up:**
- Lightning Knowledge (required for KNOWLEDGE source type)
- Data Cloud verification (required for all ADL source types)
- CRM Connector validation (required for Knowledge article ingestion)
- Sample Knowledge articles (optional, for testing)
- Einstein Agent User permissions (Data Cloud permset + Knowledge FLS)
- Language alignment verification (prevents silent empty results)

**After this skill completes**, you can run `/agentforce-generate` to create knowledge-grounded agents with any source type.

## Platform Notes

- Shell examples below use bash syntax. On Windows, use PowerShell equivalents or Git Bash.
- Replace `python3` with `python` on Windows.
- Replace `/tmp/` with `$env:TEMP\` (PowerShell) or `%TEMP%\` (cmd).

## Rules That Always Apply

1. **Always `--json`.** ALWAYS include `--json` on EVERY `sf` CLI command. Read the full JSON response directly.

2. **Verify target org.** Before any org interaction, run `sf config get target-org --json` to confirm a target org is set. If none configured, ask the user to set one with `sf config set target-org <alias> --global` (the `--global` flag is required when not inside an SFDX project directory).

3. **Stop on auth failure.** If org authentication fails, do NOT proceed. Ask the user to re-authenticate.

4. **Confirm destructive actions.** Before deploying metadata that changes org-wide settings (like enabling Lightning Knowledge), confirm with the user.

---

## Prerequisites

Before starting, verify:

### 1. SF CLI is available

```bash
sf --version --json
```

Minimum version: `@salesforce/cli 2.139.6`. If missing, offer install options but do NOT auto-install.

### 2. Org is authenticated

```bash
sf org display --target-org $TARGET_ORG --json
```

Set the target-org alias as a shell variable for all subsequent steps:

```bash
TARGET_ORG="<org-alias>"
```

### 3. Required licenses exist

Query for the add-on licenses needed:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Name, Status, TotalLicenses FROM UserLicense WHERE Name LIKE '%Einstein%' OR Name LIKE '%Knowledge%' OR Name LIKE '%Agent%'"
```

Expected licenses/add-ons:

| License/AddOn | Purpose | Required For |
|---|---|---|
| `EinsteinGPTCopilotAddOn` | Agentforce / Agent platform | All ADL types |
| `EinsteinGPTServiceAddOn` | BOTS VSaaS framework | All ADL types |
| `GenieDataPlatformStarter` (AddOn) | Data Cloud — triggers DC provisioning | All ADL types |
| `CDP Base User` (PSL) | Per-user Data Cloud access | Agent user runtime |
| `EinsteinGPTPromptBuilderAddOn` | Einstein Prompt Templates — for Prompt Builder UI (optional for ADL) | Optional — only needed if using Prompt Builder directly |
| `KnowledgeAddOn` | Knowledge feature | KNOWLEDGE source type only |

To verify Data Cloud is provisioned (not just licensed):

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT COUNT() FROM DataKnowledgeSpace"
```

If this returns `INVALID_TYPE`, Data Cloud is not provisioned. Check Setup → Data Cloud Setup — if it says "get a Data Cloud license," the `GenieDataPlatformStarter` add-on is missing.

If licenses are missing, STOP and inform the user. These must be provisioned at the org level (SKU assignment, contract update, or trial enablement). No CLI command can add licenses.

---

## Step 0 -- Enable Platform Features and Assign Admin Permissions

The org needs Einstein and Agentforce platform features turned on, and the admin user needs permission sets assigned BEFORE they can access Data Cloud or Agentforce.

**Temp directory for deploys:** Commands below use `/tmp/adl-setup/` as a temp workspace. On Windows, substitute with `%TEMP%\adl-setup\` (cmd) or `$env:TEMP/adl-setup` (PowerShell). The key requirement is that `sfdx-project.json` must exist in the same directory tree, and `sf project deploy start` must run from within that directory.

### 0a. Enable Einstein GPT Platform

Deploy the EinsteinGpt settings to turn on Einstein:

```bash
mkdir -p /tmp/adl-setup/main/default/settings
cat > /tmp/adl-setup/main/default/settings/EinsteinGpt.settings-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<EinsteinGptSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>
    <enableEinsteinGptGlobalLangSupport>true</enableEinsteinGptGlobalLangSupport>
</EinsteinGptSettings>
EOF
cat > /tmp/adl-setup/sfdx-project.json << 'EOF'
{"packageDirectories":[{"path":"main/default","default":true}],"namespace":"","sourceApiVersion":"67.0"}
EOF
cd /tmp/adl-setup && sf project deploy start --source-dir main/default/settings/EinsteinGpt.settings-meta.xml --target-org $TARGET_ORG --json
```

**IMPORTANT:** `sf project deploy start` must run from within a directory that has `sfdx-project.json`. Always `cd` into the temp directory before deploying.

If this fails with "object does not exist," the org may not have the `EinsteinGPTCopilotAddOn` license. STOP and inform the user.

### 0b. Enable Agentforce (Einstein Copilot)

Deploy the EinsteinCopilot settings to turn on Agentforce:

```bash
cat > /tmp/adl-setup/main/default/settings/EinsteinCopilot.settings-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<EinsteinCopilotSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableEinsteinGptCopilot>true</enableEinsteinGptCopilot>
</EinsteinCopilotSettings>
EOF
cd /tmp/adl-setup && sf project deploy start --source-dir main/default/settings/EinsteinCopilot.settings-meta.xml --target-org $TARGET_ORG --json
```

If this fails, the org may not have the Agentforce license (`EinsteinGPTCopilotAddOn`). STOP and inform the user.

### 0b2. Enable Agent Platform

ADL SFDRIVE creation requires the `AgentPlatformEnabled` org preference in addition to `EinsteinGPTPlatformEnabled`. Deploy the AgentPlatform settings:

```bash
cat > /tmp/adl-setup/main/default/settings/AgentPlatform.settings-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<AgentPlatformSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableAgentPlatform>true</enableAgentPlatform>
</AgentPlatformSettings>
EOF
cd /tmp/adl-setup && sf project deploy start --source-dir main/default/settings/AgentPlatform.settings-meta.xml --target-org $TARGET_ORG --json
```

Without this, `sf agent adl create --source-type sfdrive` returns: `"To create a File data library, enable Agentforce in your org. Required org preferences: EinsteinGPTPlatformEnabled, AgentPlatformEnabled."`

### 0c. Find required permission sets

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ('GenieAdmin', 'CopilotSalesforceAdmin') ORDER BY Name"
```

Note:
- `GenieAdmin` has Label "Data Cloud Architect" in the UI (do NOT query by `Name = 'DataCloudArchitect'` — that doesn't exist)
- `CopilotSalesforceAdmin` has Label "Agentforce Default Admin" in the UI

**Optional:** `PromptTemplateManager` / `PromptTemplatePermSet` is only needed for Prompt Builder UI access. It is NOT required for ADL knowledge grounding — preview, publish, and runtime all work without it.

### 0d. Get the current user ID

```bash
sf org display --target-org $TARGET_ORG --json
```

Extract `userId` from the response.

### 0e. Assign Data Cloud Architect

Required to view Data Cloud Setup pages, manage data streams, search indexes, and retrievers.

```bash
sf data create record --sobject PermissionSetAssignment --target-org $TARGET_ORG --json \
  --values "AssigneeId='<adminUserId>' PermissionSetId='<DataCloudArchitectId>'"
```

### 0f. (Optional) Assign Prompt Template Manager

Only needed if the admin wants to use Prompt Builder UI. NOT required for ADL knowledge grounding.

```bash
# Skip this step unless the user needs Prompt Builder access.
# Requires EinsteinGPTPromptBuilderAddOn license on the org.
sf data create record --sobject PermissionSetAssignment --target-org $TARGET_ORG --json \
  --values "AssigneeId='<adminUserId>' PermissionSetId='<PromptTemplateManagerId>'"
```

### 0g. Assign CopilotSalesforceAdmin (Agentforce Default Admin)

Required to access Agentforce Studio, agent APIs, and author/publish agents. Without this, `sf agent preview` and `sf agent publish` return 503.

```bash
sf data create record --sobject PermissionSetAssignment --target-org $TARGET_ORG --json \
  --values "AssigneeId='<adminUserId>' PermissionSetId='<CopilotSalesforceAdminId>'"
```

### 0h. Verify assignments

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '<adminUserId>' AND PermissionSet.Name IN ('GenieAdmin', 'CopilotSalesforceAdmin')"
```

Both should appear in the results (plus `PromptTemplateManager` if 0f was run). If the org shows a "Data Cloud standard permission sets have changed" banner in Setup, acknowledge it — Salesforce periodically updates DC permset structures.

---

## Step 1 -- Enable Knowledge User on Running User

The current authenticated user needs the Knowledge User permission before any Knowledge operations.

First, get the current user ID:

```bash
sf org display --target-org $TARGET_ORG --json
```

Extract `userId` from the response. Then enable the Knowledge User permission:

```bash
sf data update record --sobject User --record-id <userId> --values "UserPermissionsKnowledgeUser=true" --target-org $TARGET_ORG --json
```

**Verification:**

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, Username, UserPermissionsKnowledgeUser FROM User WHERE Id = '<userId>'"
```

Confirm `UserPermissionsKnowledgeUser` is `true`.

---

## Step 2 -- Enable Lightning Knowledge via Metadata Deploy

Lightning Knowledge must be enabled org-wide. Deploy via KnowledgeSettings metadata.

### 2a. Create a temporary deployment directory

```bash
mkdir -p /tmp/knowledge-settings/main/default/settings
```

### 2b. Write the KnowledgeSettings metadata file

Create `/tmp/knowledge-settings/main/default/settings/Knowledge.settings-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<KnowledgeSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableKnowledge>true</enableKnowledge>
    <enableLightningKnowledge>true</enableLightningKnowledge>
</KnowledgeSettings>
```

### 2c. Write a minimal sfdx-project.json

Create `/tmp/knowledge-settings/sfdx-project.json`:

```json
{
    "packageDirectories": [
        { "path": "main/default", "default": true }
    ],
    "sourceApiVersion": "62.0"
}
```

### 2d. Deploy

```bash
sf project deploy start --source-dir /tmp/knowledge-settings/main/default/settings --target-org $TARGET_ORG --json
```

**Important:** This is an org-wide settings change. If it fails with a permissions error, the user may need to enable Knowledge via Setup UI first (Setup > Knowledge Settings > Enable Knowledge).

### 2e. Verify

```bash
sf org open --target-org $TARGET_ORG --path "/lightning/setup/KnowledgeSettings/home" --json
```

Or query for the Knowledge article object:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = 'Knowledge__kav'"
```

If the query returns a result, Lightning Knowledge is enabled.

---

## Step 3 -- Verify CRM Connector is Active

The CRM Connector (Home org connection) is required for Knowledge article indexing. It auto-activates when Data Cloud provisioning completes — no manual step needed on fresh orgs.

Verify it's active:

```bash
sf org open --target-org $TARGET_ORG --path "/lightning/setup/CdpSalesforceCrm/home" --json
```

Check that the "Home" connection shows Status = `Active`.

**If not active (rare):** Navigate to Setup > Data Cloud > Salesforce CRM and click "Activate." This should only happen on sandbox orgs or orgs with non-standard DC provisioning.

---

## Step 4 -- Create Sample Knowledge Articles (Optional)

Creating sample articles is recommended for testing ADL grounding. Skip this step if the user already has articles or passes `--skip-sample-articles`.

### 4a. Create articles

```bash
sf data create record --sobject Knowledge__kav --values "Title='Getting Started with Our Product' UrlName='getting-started' Summary='This article covers the basics of setting up and using our product for the first time.'" --target-org $TARGET_ORG --json
```

```bash
sf data create record --sobject Knowledge__kav --values "Title='Troubleshooting Common Issues' UrlName='troubleshooting-common' Summary='Solutions for the most frequently reported problems including login failures, sync errors, and performance issues.'" --target-org $TARGET_ORG --json
```

```bash
sf data create record --sobject Knowledge__kav --values "Title='Account Management FAQ' UrlName='account-management-faq' Summary='Answers to common questions about creating accounts, managing users, resetting passwords, and billing.'" --target-org $TARGET_ORG --json
```

### 4b. Publish articles

Articles must be published to be indexed. Use the KnowledgeManagement API:

```bash
sf apex run --target-org $TARGET_ORG --json -f /dev/stdin <<'EOF'
List<Knowledge__kav> drafts = [SELECT Id, KnowledgeArticleId FROM Knowledge__kav WHERE PublishStatus = 'Draft'];
for (Knowledge__kav article : drafts) {
    KbManagement.PublishingService.publishArticle(article.KnowledgeArticleId, true);
}
System.debug('Published ' + drafts.size() + ' articles.');
EOF
```

### 4c. Verify published articles

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, Title, PublishStatus, Language FROM Knowledge__kav WHERE PublishStatus = 'Online'"
```

---

## Step 5 -- Verify Data Cloud Provisioning

ADL requires Data Cloud. Verify it is provisioned and can see Knowledge data:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT COUNT() FROM DataKnowledgeSpace"
```

If this returns a count > 0, Data Cloud recognizes the Knowledge data space.

If it fails or returns 0, Data Cloud may not be fully provisioned. Direct the user to:
1. Setup > Data Cloud Setup
2. Ensure provisioning is complete
3. Wait for the CRM Connector sync to complete (can take 5-15 minutes after activation)

---

## Step 6 -- Set Up Agent User Permissions (Runtime)

For the agent to retrieve Knowledge at runtime, the Einstein Agent User needs proper permissions.

### 6a. Find or Create the Einstein Agent User

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, Username, Name FROM User WHERE Profile.Name = 'Einstein Agent User' LIMIT 1"
```

If no agent user exists, **create one now** — it's needed for preview/testing, not just activation:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'"
```

```bash
sf data create record --sobject User --target-org $TARGET_ORG --json \
  --values "FirstName='Digital' LastName='Agent' Username='digitalagent.<orgId>@salesforce.com' Email='noreply@salesforce.com' Alias='dagent' ProfileId='<profileId>' TimeZoneSidKey='America/Los_Angeles' LocaleSidKey='en_US' LanguageLocaleKey='en_US' EmailEncodingKey='UTF-8'"
```

Replace `<orgId>` with the org's 18-character ID (from `sf org display`). The username must be globally unique.

**IMPORTANT:** `default_agent_user` is required in the `.agent` file even for "employee" agents when using `AnswerQuestionsWithKnowledge` with `--use-live-actions`. The platform treats any agent using the knowledge action as requiring an Einstein Agent User context at runtime.

### 6b. Assign required permission sets to agent user

The agent user needs THREE permsets for knowledge grounding to work at preview/runtime:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ('GenieUserEnhancedSecurity', 'AgentforceServiceAgentUser') ORDER BY Name"
```

Assign both:

```bash
# Data Cloud access (retriever queries)
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='<agentUserId>' PermissionSetId='<GenieUserEnhancedSecurityId>'" --target-org $TARGET_ORG --json

# Agent runtime access (required for preview sessions)
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='<agentUserId>' PermissionSetId='<AgentforceServiceAgentUserId>'" --target-org $TARGET_ORG --json
```

Without `AgentforceServiceAgentUser`, preview returns "Unable to access the Salesforce Agent APIs" even when all other permissions are correct.

### 6c. Assign Knowledge FLS permission set

The agent user needs:
- **`AllowViewKnowledge` user permission** — critical, without this Knowledge fields are inaccessible regardless of FLS grants
- **Object-level Read** on `Knowledge__kav`
- **Field-level Read** on ALL `contentFields` configured in the ADL (note: field permissions on Knowledge__kav may be silently stripped by the platform for Einstein Agent User license — the `AllowViewKnowledge` permission is what actually grants access)

Deploy a permission set that includes all of these:

Deploy the Knowledge access permission set:

```bash
mkdir -p /tmp/adl-setup/main/default/permissionsets
cat > /tmp/adl-setup/main/default/permissionsets/KnowledgeAgentAccess.permissionset-meta.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Knowledge Agent Access</label>
    <userPermissions>
        <enabled>true</enabled>
        <name>AllowViewKnowledge</name>
    </userPermissions>
    <objectPermissions>
        <allowRead>true</allowRead>
        <object>Knowledge__kav</object>
        <viewAllRecords>true</viewAllRecords>
    </objectPermissions>
</PermissionSet>
EOF
cd /tmp/adl-setup && sf project deploy start --source-dir main/default/permissionsets --target-org $TARGET_ORG --json
```

Then assign to the agent user:

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id FROM PermissionSet WHERE Name = 'KnowledgeAgentAccess'"
sf data create record --sobject PermissionSetAssignment --target-org $TARGET_ORG --json \
  --values "AssigneeId='<agentUserId>' PermissionSetId='<KnowledgeAgentAccessId>'"
```

**CRITICAL:** The `AllowViewKnowledge` user permission is what actually grants Knowledge field access for the Einstein Agent User license. Raw field-level permissions get silently stripped by the platform for this license type. The `AllowViewKnowledge` + `viewAllRecords` combination grants access through a different mechanism that works.

### 6d. Verify language alignment

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Id, LanguageLocaleKey FROM User WHERE Name = 'Einstein Agent User'"
```

```bash
sf data query --target-org $TARGET_ORG --json -q "SELECT Language, COUNT(Id) cnt FROM Knowledge__kav WHERE PublishStatus = 'Online' GROUP BY Language"
```

**CRITICAL -- Language Filter:** The retriever filters indexed chunks by language. The article `Language` field MUST match the agent user's language context. Even `en_US` vs `en_GB` causes a mismatch and returns zero results. Reference: W-21956266.

If there is a mismatch:
- Update article language to match the agent user locale, OR
- Update the agent user locale to match the articles

```bash
sf data update record --sobject User --record-id <agentUserId> --values "LanguageLocaleKey='en_US'" --target-org $TARGET_ORG --json
```

---

## Verification Checklist

After completing all steps, verify the full setup:

| Check | Command | Expected |
|-------|---------|----------|
| Knowledge User enabled | Query User.UserPermissionsKnowledgeUser | `true` |
| Lightning Knowledge active | Query EntityDefinition for Knowledge__kav | Row returned |
| CRM Connector active | Query DataSourceInstance WHERE Type='CRM' | Status = Active |
| Published articles exist | Query Knowledge__kav WHERE PublishStatus='Online' | Count > 0 |
| Data Cloud sees Knowledge | Query DataKnowledgeSpace | Count > 0 |
| Agent user has permissions | Query PermissionSetAssignment for agent user | DC + Knowledge permsets assigned |
| Language alignment | Compare User.LanguageLocaleKey vs article Language | Match |

---

## Troubleshooting

### "Knowledge is not enabled in this org"

- Ensure Step 2 metadata deploy succeeded
- Try enabling manually: Setup > Knowledge Settings > Enable Knowledge
- Some org editions require a specific license SKU

### "INVALID_FIELD: UserPermissionsKnowledgeUser"

- The org may not have the Knowledge feature license provisioned
- Check: `sf data query --target-org $TARGET_ORG --json -q "SELECT Id FROM UserLicense WHERE Name = 'Knowledge Only'"`

### Articles not appearing in ADL after indexing

- Verify articles are Published (not Draft)
- Check language alignment (most common cause -- see Step 6d)
- Verify CRM Connector sync completed
- Wait 5-15 minutes after publishing for Data Cloud sync

### "Insufficient access" when agent retrieves Knowledge

- Verify object-level Read on Knowledge__kav (not just field-level)
- Verify field-level Read on ALL configured contentFields
- Check the GenieUserEnhancedSecurity permset is assigned to the agent user

---

## Known Issues and Notes

- **Language filter (W-21956266)**: Retriever filters chunks by language. Even minor locale variants (en_US vs en_GB) cause zero results. Always verify alignment.
- **Knowledge FLS for Einstein Agent User**: Raw field-level permissions are silently stripped by the platform for the Einstein Agent license. The correct fix is `AllowViewKnowledge` user permission + `viewAllRecords: true` on Knowledge__kav. Do NOT attempt individual field grants.
- **CRM Connector**: Auto-activates when Data Cloud provisioning completes. No manual step needed on fresh orgs. Only check manually if DC provisioning completed but Knowledge indexing fails.
- **Intermittent DNS failures for api.salesforce.com**: The SF CLI's Node.js process (with @mswjs/interceptors) can intermittently fail DNS for `api.salesforce.com`. If `sf agent preview start` alternates between ENOTFOUND and 404 "Unable to access Agent APIs" — retry. The underlying DNS works (verifiable with `nslookup`), it's an MSW interception issue. Set `SF_DISABLE_MSW=1` if using a linked plugin.
- **Data Cloud provisioning time**: First-time DC provisioning can take 30 min – 2 hours. The skill cannot speed this up.
- **SFDRIVE doesn't need Knowledge**: Steps 1-4 (Knowledge enablement) are only required for KNOWLEDGE source type. SFDRIVE and RETRIEVER only need Data Cloud (Step 5) and agent user setup (Step 6).
- **default_agent_user required for knowledge agents**: Even "employee" type agents require `default_agent_user` in the `.agent` file when using `AnswerQuestionsWithKnowledge` with live actions. The platform treats it as needing an Einstein Agent User context at runtime.
- **Always specify contentFields explicitly**: When creating a KNOWLEDGE ADL, always pass `--content-fields "Summary,Answer__c"` (or your fields). If `contentFields` is empty, the retriever checks FLS on ALL Knowledge fields at query time — if even one non-required field is inaccessible, you get `INSUFFICIENT_ACCESS`.
- **Agentforce Studio URL**: The correct path is `/lightning/setup/EinsteinCopilot/home` (not `/lightning/setup/CopilotStudio/home`).

---

## Next Steps

Once setup is complete, use `/agentforce-generate` to create a knowledge-grounded agent:

```text
You: Create a knowledge-grounded agent from ~/docs/manual.pdf on org myOrg
     → Skill routes to SFDRIVE, provisions ADL, wires into agent

You: Ground my agent on Knowledge articles on org myOrg
     → Skill routes to KNOWLEDGE, creates library, indexes articles

You: Use custom retriever 1CxXXX on org myOrg
     → Skill routes to RETRIEVER, wraps retriever, immediately ready
```

For all source types, the `/agentforce-generate` skill handles ADL creation, wiring, preview, and publish automatically — this setup skill just ensures the org is ready for it.
