---
name: setting-up-pre-work-brief
description: "Set up Pre-Work Brief end-to-end on Field Service Mobile in a Salesforce org. TRIGGER when: user asks to enable, configure, install, or set up Pre-Work Brief or PWB; user asks to turn on the AI brief on Work Order in the Field Service mobile app; user wants to deploy or activate the Field Service Pre-Work Brief prompt template; user wants to wire the Field Service Mobile: Generate Pre-Work Brief flow to a prompt template; user troubleshoots a missing or empty Pre-Work Brief on a Work Order. DO NOT TRIGGER when: user wants Voice to Form (separate skill); user wants Post-Work Summary; user wants to author a brand-new prompt template type from scratch (use Prompt Builder docs); user wants to build a generic Agentforce agent (use developing-agentforce)."
allowed-tools: Bash Read Write Edit Glob Grep
license: Apache-2.0
metadata:
  version: "0.1.0"
  last_updated: "2026-05-13"
  argument-hint: "<org-alias> [--technician <username>]"
  compatibility: claude-code
---

# Setting up Pre-Work Brief

Configure Pre-Work Brief on Field Service Mobile from a fresh Field Service org. Pre-Work Brief uses generative AI to give a mobile worker a concise summary of their upcoming Work Order, grounded in real Salesforce data. The brief renders in the **Overview tab of a Work Order** in the Field Service mobile app on iOS and Android.

This skill walks through the complete setup path documented at `help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief.htm`, in the order Salesforce documents it. Each step is idempotent. Re-running the skill on an already-configured org applies zero changes.

---

## Platform Notes

- All `sf` commands assume Salesforce CLI 2.x or later.
- Replace `jq` with `python -c "import json,sys; ..."` if jq is not installed.
- `$ORG_ALIAS` throughout refers to the target org alias the user has set or supplied.
- Many setup steps are clicks-only in **Setup**. The skill prints exact Quick Find search terms and UI paths for those.

---

## What Pre-Work Brief is

Pre-Work Brief is built on three Salesforce primitives:

1. A **prompt template** of type `Field Service Pre-Work Brief` in Prompt Builder.
2. The managed flow **Field Service Mobile: Generate Pre-Work Brief**, which gathers the grounding data (Account, Case, Contact, Work Order, Work Plan, Work Step, Service Appointment, and more) and feeds it to the prompt.
3. A field on the Work Order object — **Pre-Work Brief Prompt Template ID** — that points each Work Order at the prompt template it should run.

When a mobile worker opens a Work Order in the Field Service app while connected to the internet, the brief is generated once and rendered in the Overview tab. It is regenerated only after 24 hours.

**Editions and licensing:** Enterprise, Performance, or Unlimited Edition with the **Einstein for Field Service** add-on or the **Agentforce for Field Service** add-on. Also available in Einstein 1 Field Service Edition. Mobile workers must hold the Field Service Mobile license.

**Salesforce branding note:** Field Service is now Agentforce Field Service and Operations. The product retains "Field Service" in many UI labels and API names. This skill follows the API names that exist in the org today.

---

## Prerequisites

Before running the setup sequence, confirm all four:

1. **Edition + add-on.** The org has the Einstein for Field Service or Agentforce for Field Service add-on. See step 1 of the setup sequence.
2. **Lightning Data Service for Field Service Mobile is enabled.** Pre-Work Brief depends on LDS to render correctly on mobile. See step 2.
3. **Einstein generative AI is enabled.** Pre-Work Brief is one of several Einstein generative AI features and shares a base setup path with the rest of them.
4. **Admin user has the right permissions:** `Customize Application` to build and manage Pre-Work Brief, and `Manage Profiles and Permission Sets` to assign permission sets.

---

## Setup Sequence

Run steps in order. Each step prints its own check before applying changes. If a check fails, the step exits without modifying the org.

### Step 0: Detect provisioning state and route

Before walking the setup steps, run four detection queries to classify the org. The results route you into the right path: a fully-provisioned org skips ahead to the customization steps; a partially-provisioned org stops and contacts Salesforce for the AI flow templates; an unprovisioned org stops and contacts the account team for the license.

```bash
echo "1. Edition + add-on PSL:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT DeveloperName FROM PermissionSetLicense
           WHERE (DeveloperName LIKE '%FieldService%' OR MasterLabel LIKE '%Field Service%')
             AND (DeveloperName LIKE '%Einstein%' OR DeveloperName LIKE '%Agentforce%'
                  OR MasterLabel LIKE '%Einstein%' OR MasterLabel LIKE '%Agentforce%')" \
  --json | jq -r '.result.totalSize as $n |
    if $n > 0 then "PRESENT (\($n) row(s))" else "MISSING" end'

echo "2. Three permission sets:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Name FROM PermissionSet
           WHERE Name IN ('EinsteinFieldServiceUser','EinsteinGPTPromptTemplateManager','EinsteinGPTPromptTemplateUser')" \
  --json | jq -r '.result.totalSize as $n |
    if $n == 3 then "PRESENT (all 3)" elif $n > 0 then "PARTIAL (\($n)/3)" else "MISSING" end'

echo "3. Work Order PreWorkBriefPromptTemplate field:"
sf sobject describe --sobject WorkOrder --target-org "$ORG_ALIAS" --json | \
  jq -r '.result.fields | map(select(.name == "PreWorkBriefPromptTemplate")) | length as $n |
    if $n > 0 then "PRESENT" else "MISSING" end'

echo "4. Pre-Work Brief prompt template (Pre_Work_Brief or any with PWB type):"
sf org list metadata --metadata-type GenAiPromptTemplate --target-org "$ORG_ALIAS" --json | \
  jq -r '[.result[]? | select((.fullName // "") | test("PreWorkBrief|Pre_Work_Brief"; "i"))] | length as $n |
    if $n > 0 then "PRESENT (\($n))" else "MISSING — deploy in step 5" end'

echo "5. Lightning SDK for Field Service Mobile (enableLsdkMode):"
sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT FullName, Metadata FROM FieldServiceSettings" --json | \
  jq -r '.result.records[0].Metadata.enableLsdkMode as $v |
    if $v == true then "ENABLED" elif $v == false then "DISABLED (auto-fixable, see Step 2)" else "UNKNOWN" end'
```

Interpret the five results to classify the org:

| Diagnostic 1 (PSL) | Diagnostic 4 (template) | State | What to do |
|---|---|---|---|
| MISSING | any | **Unprovisioned** | Stop. Contact your Salesforce account executive to purchase the Einstein for Field Service or Agentforce for Field Service add-on. The skill cannot continue. |
| PRESENT | MISSING | **Template not yet deployed** | Continue to step 1. Step 5 deploys the Pre-Work Brief prompt template via metadata. The backing flow `sfdc_fieldservice__GenPreWorkBrief` is a platform-level managed flow that ships with the Einstein for Field Service add-on; it is not metadata-listed but is referenced by the template. |
| PRESENT | PRESENT | **Fully provisioned** | Continue to step 1. Step 5 will detect the existing template and skip re-deploy. |

Diagnostics 2 and 3 are sub-signals. If diagnostic 1 is PRESENT but 2 or 3 are MISSING, the Einstein generative AI base setup (step 3 below) hasn't completed in this org yet. Run that first, then re-check.

Diagnostic 5 is the Lightning SDK toggle. If it returns DISABLED, run step 2 — the skill enables it via a metadata deploy without requiring a Setup UI click.

**Note on the managed flow.** Earlier versions of this skill checked for a Flow named `PreWorkBrief` in metadata listings. That check returns zero rows even in fully-working orgs, because the backing flow `sfdc_fieldservice__GenPreWorkBrief` is provisioned at the platform layer and is not exposed via the standard metadata API. The flow is real, addressable from Prompt Builder's Resource → Flows dropdown as `{!$Flow:sfdc_fieldservice__GenPreWorkBrief.Prompt}`, and used by the prompt template the skill deploys in step 5. Diagnostic 4 has been updated to check for the prompt template directly.

### Step 0.5: Choose the target technician user

Pre-Work Brief is a per-user feature. Each technician who should see the brief needs three things assigned: the Field Service Mobile license, the Einstein for Field Service PSL, and the Einstein for Field Service permission sets. The skill targets one technician at a time so the admin can pilot with a specific user before rolling out broadly.

Ask the admin: **"Do you have a specific technician user you want to enable Pre-Work Brief for?"**

**If yes:** the admin supplies a username or User Id. Validate that the user is active, has a `ServiceResource` record, and is `ResourceType = 'T'` (technician):

```bash
TECH_USER="<username-or-id>"

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, Name, Username, IsActive, Profile.Name FROM User WHERE (Username = '$TECH_USER' OR Id = '$TECH_USER') AND IsActive = true" \
  --json | jq -r '.result.records[]? | "User: \(.Name) | \(.Username) | \(.Id) | profile=\(.Profile.Name)"'

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, Name, ResourceType FROM ServiceResource WHERE RelatedRecordId IN (SELECT Id FROM User WHERE Username = '$TECH_USER' OR Id = '$TECH_USER') AND IsActive = true" \
  --json | jq -r '.result.records[]? | "ServiceResource: \(.Name) | \(.Id) | type=\(.ResourceType)"'
```

If neither query returns a row, the supplied user isn't a technician in this org. Stop and ask for a different one.

**If no:** auto-pick a candidate. Pick the first active technician whose user is also active and is on a non-administrator profile, and surface the choice to the admin so they know which user the skill is configuring:

```bash
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, Name, RelatedRecord.Id, RelatedRecord.Username, RelatedRecord.Name, RelatedRecord.Profile.Name FROM ServiceResource WHERE IsActive = true AND ResourceType = 'T' AND RelatedRecordId != null AND RelatedRecord.IsActive = true AND RelatedRecord.Profile.Name NOT IN ('System Administrator') AND (NOT RelatedRecord.Profile.Name LIKE '%Customer Community%') AND (NOT RelatedRecord.Profile.Name LIKE '%Partner Community%') ORDER BY Name LIMIT 1" \
  --json | jq -r '.result.records[]? | "Auto-selected technician for Pre-Work Brief setup:\n  ServiceResource: \(.Name) (\(.Id))\n  User:            \(.RelatedRecord.Name) (\(.RelatedRecord.Username))\n  User Id:         \(.RelatedRecord.Id)\n  Profile:         \(.RelatedRecord.Profile.Name)\n\nThe skill will configure Pre-Work Brief for this user. To pick a different one, re-run with --technician <username>."'
```

If the auto-pick query returns zero rows, the org has no technicians on a non-administrator, non-community profile. The admin needs to either create a technician user, or supply a specific username via `--technician` and accept the profile.

Capture the chosen `User.Id` as `$TECH_USER_ID` and `Username` as `$TECH_USERNAME` for use in step 4.

### Step 1: Confirm target org and check the Einstein for Field Service license

```bash
sf org display --target-org "$ORG_ALIAS" --json
```

Verify the org has one of the Einstein for Field Service permission set licenses. The DeveloperName values currently shipped are `EinsteinFieldServicePsl` ("Einstein for Field Service") and `EinsteinForFieldServiceMobilePsl` ("Einstein for Field Service Mobile"). Salesforce branding may shift to "Agentforce for Field Service" in future releases; the skill matches both.

```bash
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT DeveloperName, MasterLabel, TotalLicenses, UsedLicenses
           FROM PermissionSetLicense
           WHERE (DeveloperName LIKE '%FieldService%' OR MasterLabel LIKE '%Field Service%')
             AND (DeveloperName LIKE '%Einstein%' OR DeveloperName LIKE '%Agentforce%'
                  OR MasterLabel LIKE '%Einstein%' OR MasterLabel LIKE '%Agentforce%')" \
  --json
```

- **Pass:** At least one row returned with `TotalLicenses > 0`.
- **Fail:** No row, or all rows have `TotalLicenses = 0`. Stop. Contact your Salesforce account executive to purchase the Einstein for Field Service or Agentforce for Field Service add-on.

### Step 2: Enable Lightning Data Service for the Field Service mobile app

Pre-Work Brief renders in an LDS-aware container. Without LDS, the brief shows blank.

LDS is enabled by default for new orgs and sandboxes from Winter '25. All orgs are auto-migrated by Spring '26. If diagnostic 5 in step 0 returned DISABLED for `enableLsdkMode`, enable it now.

**Path A — CLI deploy (preferred, no Setup UI needed).**

Create a tiny SFDX project and deploy a `FieldServiceSettings` metadata file that flips `enableLsdkMode` to `true`:

```bash
mkdir -p /tmp/fs-lds-enable/force-app/main/default/settings
cat > /tmp/fs-lds-enable/sfdx-project.json <<'EOF'
{
  "packageDirectories": [{"path": "force-app", "default": true}],
  "namespace": "",
  "sfdcLoginUrl": "https://login.salesforce.com",
  "sourceApiVersion": "62.0"
}
EOF
cat > /tmp/fs-lds-enable/force-app/main/default/settings/FieldService.settings-meta.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<FieldServiceSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <enableLsdkMode>true</enableLsdkMode>
    <fieldServiceOrgPref>true</fieldServiceOrgPref>
</FieldServiceSettings>
EOF
cd /tmp/fs-lds-enable
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app --wait 10
```

Verify the toggle flipped:

```bash
sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT FullName, Metadata FROM FieldServiceSettings" --json | \
  jq '.result.records[0].Metadata.enableLsdkMode'
```

Expect `true`.

**Path B — Setup UI (manual fallback).** In Setup, in the Quick Find box, enter and select **Field Service Settings**. Under **Lightning SDK for Field Service Mobile**, select **Enable Lightning SDK for Field Service Mobile**.

Reference: `help.salesforce.com/s/articleView?id=service.mfs_lightning_data_service.htm`

### Step 3: Set up Einstein generative AI in the org

Before configuring Pre-Work Brief, complete Salesforce's base Einstein generative AI setup. Do not skip the Data 360 portion of that setup.

Reference: `help.salesforce.com/s/articleView?id=ai.generative_ai_enable.htm`

### Step 4: Assign Einstein for Field Service PSL and permission sets

Two users get assignments in this step: the **admin** running the setup (so they can see and create prompt templates in Prompt Builder) and the **technician** chosen in step 0.5 (so they can run the brief on their mobile device). The two roles get different permission sets.

> **Critical:** if the admin doesn't have `EinsteinGPTPromptTemplateManager` and `EinsteinGPTPromptTemplateUser` assigned, the **Field Service Pre-Work Brief** prompt template type will not appear in Prompt Builder and step 5 will fail with no error message — just a missing option in a dropdown. Don't skip 4a.

| Role | EinsteinFieldServicePsl | EinsteinFieldServiceUser | EinsteinGPTPromptTemplateManager | EinsteinGPTPromptTemplateUser |
|---|---|---|---|---|
| Admin (creates and manages the prompt template) | yes | yes | **yes** | yes |
| Technician (runs the brief on mobile) | yes | yes | no | yes |

**4a. Verify the three permission sets exist in the org.**

```bash
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Name, Label FROM PermissionSet
           WHERE Name IN ('EinsteinFieldServiceUser','EinsteinGPTPromptTemplateManager','EinsteinGPTPromptTemplateUser')" \
  --json | jq -r '.result.records[] | "\(.Name) | \(.Label)"'
```

All three rows should return. If any are missing, the Einstein generative AI base setup (step 3) hasn't completed for this org.

**4b. Identify the admin user.**

The admin is whoever is running this skill — typically the user authenticated via `sf org login`. Capture their username and Id:

```bash
ADMIN_USERNAME=$(sf org display --target-org "$ORG_ALIAS" --json | jq -r '.result.username')
ADMIN_USER_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id FROM User WHERE Username = '$ADMIN_USERNAME'" --json | \
  jq -r '.result.records[0].Id')
echo "Admin user: $ADMIN_USERNAME ($ADMIN_USER_ID)"
```

**4c. Assign PSLs to the admin.**

```bash
sf org assign permsetlicense --name EinsteinFieldServicePsl --on-behalf-of "$ADMIN_USERNAME" --target-org "$ORG_ALIAS"
sf org assign permsetlicense --name EinsteinForFieldServiceMobilePsl --on-behalf-of "$ADMIN_USERNAME" --target-org "$ORG_ALIAS" 2>/dev/null || true
```

**4d. Assign all three permission sets to the admin.**

The admin gets all three so they can manage prompt templates and run them for previewing.

```bash
for ps in EinsteinFieldServiceUser EinsteinGPTPromptTemplateManager EinsteinGPTPromptTemplateUser; do
  sf org assign permset --name "$ps" --on-behalf-of "$ADMIN_USERNAME" --target-org "$ORG_ALIAS"
done
```

**4e. Assign PSLs to the technician.**

```bash
sf org assign permsetlicense --name EinsteinFieldServicePsl --on-behalf-of "$TECH_USERNAME" --target-org "$ORG_ALIAS"
sf org assign permsetlicense --name EinsteinForFieldServiceMobilePsl --on-behalf-of "$TECH_USERNAME" --target-org "$ORG_ALIAS" 2>/dev/null || true
```

**4f. Assign two permission sets to the technician.**

The technician gets `EinsteinFieldServiceUser` (for the Field Service AI feature itself) and `EinsteinGPTPromptTemplateUser` (so they can run the prompt template). They do **not** get `EinsteinGPTPromptTemplateManager` — that's an admin-only permission for editing templates.

```bash
for ps in EinsteinFieldServiceUser EinsteinGPTPromptTemplateUser; do
  sf org assign permset --name "$ps" --on-behalf-of "$TECH_USERNAME" --target-org "$ORG_ALIAS"
done
```

**4g. Verify all assignments landed.**

```bash
echo "Admin ($ADMIN_USERNAME) PSLs:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign
           WHERE AssigneeId = '$ADMIN_USER_ID'
             AND PermissionSetLicense.DeveloperName LIKE '%Einstein%FieldService%'" \
  --json | jq -r '.result.records[] | "  \(.PermissionSetLicense.DeveloperName)"'

echo "Admin permission sets:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT PermissionSet.Name FROM PermissionSetAssignment
           WHERE AssigneeId = '$ADMIN_USER_ID'
             AND PermissionSet.Name IN ('EinsteinFieldServiceUser','EinsteinGPTPromptTemplateManager','EinsteinGPTPromptTemplateUser')" \
  --json | jq -r '.result.records[] | "  \(.PermissionSet.Name)"'

echo ""
echo "Technician ($TECH_USERNAME) PSLs:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign
           WHERE AssigneeId = '$TECH_USER_ID'
             AND PermissionSetLicense.DeveloperName LIKE '%Einstein%FieldService%'" \
  --json | jq -r '.result.records[] | "  \(.PermissionSetLicense.DeveloperName)"'

echo "Technician permission sets:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT PermissionSet.Name FROM PermissionSetAssignment
           WHERE AssigneeId = '$TECH_USER_ID'
             AND PermissionSet.Name IN ('EinsteinFieldServiceUser','EinsteinGPTPromptTemplateManager','EinsteinGPTPromptTemplateUser')" \
  --json | jq -r '.result.records[] | "  \(.PermissionSet.Name)"'
```

Expected admin output: 3 permission sets and at least `EinsteinFieldServicePsl`. Expected technician output: 2 permission sets (no `Manager`) and at least `EinsteinFieldServicePsl`.

Reference: `help.salesforce.com/s/articleView?id=service.fs_einstein_gen_ai_setup.htm`

### Step 5: Ensure exactly one Pre-Work Brief prompt template exists

Pre-Work Brief is delivered as a `GenAiPromptTemplate` of type `einstein_gpt__fieldServicePreWorkBrief`. The template's content references the platform-level managed flow `sfdc_fieldservice__GenPreWorkBrief`, which ships with the Einstein for Field Service add-on and is addressable from Prompt Builder's Resource dropdown as `{!$Flow:sfdc_fieldservice__GenPreWorkBrief.Prompt}`.

This step is **detect-then-deploy** so re-running the skill on an already-configured org applies zero changes.

**5a. Detect existing PWB templates.**

```bash
sf org list metadata --metadata-type GenAiPromptTemplate --target-org "$ORG_ALIAS" --json | \
  jq -r '.result[]? | select((.fullName // "") | test("PreWorkBrief|Pre_Work_Brief"; "i")) | "  \(.fullName) | ns=\(.namespacePrefix // "none") | mgr=\(.manageableState // "?")"'
```

| CLI result | Action |
|---|---|
| **One row returned** | Template exists. Skip 5b and 5c. Note the `fullName` for use in step 8. |
| **Zero rows** | Continue to 5b. The skill deploys a reference template. |
| **Multiple rows** | Pick one to standardize on. Use the destructive-deploy command at 5d to remove the others. |

After running this step, also open Prompt Builder in Setup (Quick Find: **Einstein Generative AI → Prompt Builder**) to visually confirm the template list matches CLI output. If Prompt Builder shows a template that didn't appear in CLI output, it may be a recently-viewed-items artifact rather than a real template — refresh the page to clear.

**5b. (Only if 5a returned zero) Write the prompt template metadata.**

Create a tiny SFDX project and write the template XML:

```bash
mkdir -p /tmp/pwb-template/force-app/main/default/genAiPromptTemplates
cat > /tmp/pwb-template/sfdx-project.json <<'EOF'
{
  "packageDirectories": [{"path": "force-app", "default": true}],
  "namespace": "",
  "sfdcLoginUrl": "https://login.salesforce.com",
  "sourceApiVersion": "62.0"
}
EOF
cat > /tmp/pwb-template/force-app/main/default/genAiPromptTemplates/Pre_Work_Brief.genAiPromptTemplate-meta.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">
    <developerName>Pre_Work_Brief</developerName>
    <masterLabel>Pre-Work Brief</masterLabel>
    <templateVersions>
        <content>{!$Flow:sfdc_fieldservice__GenPreWorkBrief.Prompt}</content>
        <inputs>
            <apiName>WorkOrder</apiName>
            <definition>SOBJECT://WorkOrder</definition>
            <referenceName>Input:WorkOrder</referenceName>
            <required>true</required>
        </inputs>
        <primaryModel>sfdc_ai__DefaultOpenAIGPT4OmniMini</primaryModel>
        <status>Published</status>
        <templateDataProviders>
            <definition>flow://sfdc_fieldservice__GenPreWorkBrief</definition>
            <parameters>
                <definition>SOBJECT://WorkOrder</definition>
                <isRequired>true</isRequired>
                <parameterName>WorkOrder</parameterName>
                <valueExpression>{!$Input:WorkOrder}</valueExpression>
            </parameters>
            <referenceName>Flow:sfdc_fieldservice__GenPreWorkBrief</referenceName>
        </templateDataProviders>
    </templateVersions>
    <type>einstein_gpt__fieldServicePreWorkBrief</type>
    <visibility>Global</visibility>
</GenAiPromptTemplate>
EOF
```

Key elements:

- `<type>einstein_gpt__fieldServicePreWorkBrief</type>` — the prompt template type. Required for Prompt Builder to recognize this as a Field Service Pre-Work Brief template.
- `<content>` — the prompt body. The expression `{!$Flow:sfdc_fieldservice__GenPreWorkBrief.Prompt}` injects the prompt that the platform-level managed flow generates from the Work Order grounding data.
- `<templateDataProviders>` — wires the flow up as the data source. The flow takes a `WorkOrder` SObject input and returns the grounded prompt.
- `<primaryModel>sfdc_ai__DefaultOpenAIGPT4OmniMini</primaryModel>` — the LLM the template runs on. The `DefaultOpenAIGPT4OmniMini` model is a Salesforce-managed routing alias and the standard for new Field Service prompt templates.
- `<status>Published</status>` — marks the template version as Published. **Note:** this is not the same as Active. After deploy, the template still needs a one-click activation in Prompt Builder UI before it appears in the runtime catalog and can be used by the mobile app. Salesforce does not currently expose a programmatic activation path (we tried Tooling REST PATCH on `IsActive`, Connect API `/activate` endpoints across v62-v66, Apex `ConnectApi.EinsteinLLM` methods, and metadata `activeVersionNumber` — none work).
- `<visibility>Global</visibility>` — exposes the template across the org.

**5c. Deploy, then surface the activation link to the admin.**

```bash
cd /tmp/pwb-template
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app --wait 10

# Verify it appears in metadata listing:
DEPLOYED=$(sf org list metadata --metadata-type GenAiPromptTemplate --target-org "$ORG_ALIAS" --json | \
  jq -r '.result[]? | select(.fullName == "Pre_Work_Brief") | .fullName')

if [ "$DEPLOYED" = "Pre_Work_Brief" ]; then
  echo ""
  echo "✓ Prompt template Pre_Work_Brief deployed."
  echo ""
  # Resolve the template Id from the deploy report so we can build a deeplink
  TEMPLATE_ID=$(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
    --query "SELECT Id FROM DeployRequest WHERE NumberComponentsDeployed > 0 ORDER BY CompletedDate DESC LIMIT 20" --json | \
    jq -r '.result.records[]?.Id' | while read did; do
      cand=$(sf project deploy report --target-org "$ORG_ALIAS" --job-id "$did" --json 2>/dev/null | \
        jq -r '.result.details.componentSuccesses[]? | select(.componentType == "GenAiPromptTemplate" and .fullName == "Pre_Work_Brief") | .id' | head -1)
      if [ -n "$cand" ]; then echo "$cand"; break; fi
    done | head -1)

  echo "  Template Id: $TEMPLATE_ID"
  echo ""
  echo "  ⚠ Action required: Activate the template in Prompt Builder."
  echo "  The template is deployed and Published, but until activated, it"
  echo "  won't appear in the runtime catalog. The mobile app will fail with"
  echo "  'We hit a snag' until activation is complete."
  echo ""
  echo "  Generating sign-in link to the template (valid ~15 minutes):"
  sf org open --target-org "$ORG_ALIAS" \
    --path "/lightning/setup/EinsteinPromptStudio/$TEMPLATE_ID/edit" \
    --url-only 2>&1 | grep -oE 'https://[^[:cntrl:][:space:]]+frontdoor[^[:cntrl:][:space:]]+' | head -1 | sed 's/\x1b\[[0-9;]*m//g'
  echo ""
  echo "  Click the link above, then in Prompt Builder click the **Activate**"
  echo "  button (typically top-right of the editor). After activation,"
  echo "  re-run the verification query below to confirm."
  echo ""
fi

# Verify activation took effect:
sf api request rest "/services/data/v62.0/einstein/prompt-templates?pageSize=200" --target-org "$ORG_ALIAS" 2>/dev/null | \
  python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
hit = [t for t in d.get('promptRecords', []) if t.get('fields', {}).get('DeveloperName', {}).get('value') == 'Pre_Work_Brief']
print('✓ Active in runtime catalog' if hit else '✗ Not yet active — click Activate in Prompt Builder')"
```

Expect to see "✓ Active in runtime catalog" once the admin clicks Activate. To preview the template content before activation, click into the template, enter a Work Order Id under **Work Order**, and click Preview — the Resolution pane will show the prompt that will be generated.

**Optional: customize the prompt content.** The `<content>` block above is the minimal form — just the flow reference. To layer custom instructions on top of the flow's grounded data, replace `<content>` with a multi-line block like:

```xml
<content>You are tasked with completing maintenance on Asset: {!$Input:WorkOrder.Asset.Name}
for {!$Input:WorkOrder.WorkOrderNumber}.

Specific Job Information:
{!$Flow:sfdc_fieldservice__GenPreWorkBrief.Prompt}

Always include a Summary section and an On-Site Considerations bullet list.</content>
```

Tune as needed and re-deploy.

**5d. (Only if cleanup needed) Remove an admin-deployed duplicate template.**

If the org has both a platform-managed Pre-Work Brief template and a previously admin-deployed one (for example, from an earlier run of this skill), delete the admin-deployed template:

```bash
mkdir -p /tmp/pwb-cleanup
cat > /tmp/pwb-cleanup/destructiveChanges.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Pre_Work_Brief</members>
        <name>GenAiPromptTemplate</name>
    </types>
    <version>62.0</version>
</Package>
EOF
cat > /tmp/pwb-cleanup/empty-package.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>62.0</version>
</Package>
EOF
cat > /tmp/pwb-cleanup/sfdx-project.json <<'EOF'
{"packageDirectories": [{"path": "force-app", "default": true}], "namespace": "", "sourceApiVersion": "62.0"}
EOF
mkdir -p /tmp/pwb-cleanup/force-app
cd /tmp/pwb-cleanup
sf project deploy start --target-org "$ORG_ALIAS" --manifest empty-package.xml --post-destructive-changes destructiveChanges.xml --wait 10
```

Replace `<members>Pre_Work_Brief</members>` with the developer name of whichever template you're removing. Platform-managed templates (those without an `mgr=unmanaged` flag in the CLI listing) cannot be deleted this way; if you want to suppress those, hide them via Prompt Builder UI access controls instead.

### Step 6: Verify the data the flow uses exists in your org

The default Pre-Work Brief flow grounds on a fixed set of objects and fields documented at `help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief_data.htm`. The objects are: Account, Case, Contact, Pricebook 2, Service Appointment, Work Order, Work Order Line Item, Work Plan, Work Step.

If the default flow doesn't run, walk the field list in the Help article above. For any field that doesn't exist in your org, edit the flow to remove that field. For each field that does exist, confirm field-level security is set to **Visible** for the relevant profiles, and that mobile workers have access.

```bash
# Read the default field list:
sf sobject describe --sobject WorkOrder --target-org "$ORG_ALIAS" --json | \
  jq '.fields[] | {name, label, type}' | head -40
```

Repeat for Account, Case, Contact, Pricebook2, ServiceAppointment, WorkOrderLineItem, WorkPlan, WorkStep.

### Step 7: Add the Pre-Work Brief Prompt Template ID field to the Work Order layout

The brief is gated per Work Order by a field on the Work Order object: `PreWorkBriefPromptTemplate` (label "Pre-Work Brief Prompt Template ID"). The field exists in the org once the Einstein for Field Service add-on is provisioned; it just needs to be added to the page layout assigned to the technician's profile.

**7a. Identify the layout assigned to the technician's profile.**

```bash
TECH_PROFILE_NAME=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Profile.Name FROM User WHERE Username = '$TECH_USERNAME'" --json | \
  jq -r '.result.records[0].Profile.Name')

LAYOUT_NAME=$(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT Layout.Name FROM ProfileLayout WHERE Profile.Name = '$TECH_PROFILE_NAME' AND Layout.TableEnumOrId = 'WorkOrder'" --json | \
  jq -r '.result.records[0].Layout.Name')

LAYOUT_FULLNAME="WorkOrder-$LAYOUT_NAME"
echo "Updating layout: $LAYOUT_FULLNAME (assigned to $TECH_PROFILE_NAME)"
```

**7b. Retrieve, edit, and re-deploy the layout.**

```bash
mkdir -p /tmp/wo-layout/force-app/main/default
cat > /tmp/wo-layout/sfdx-project.json <<'EOF'
{"packageDirectories":[{"path":"force-app","default":true}],"namespace":"","sourceApiVersion":"62.0"}
EOF
cat > /tmp/wo-layout/package.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>$LAYOUT_FULLNAME</members>
        <name>Layout</name>
    </types>
    <version>62.0</version>
</Package>
EOF
cd /tmp/wo-layout
sf project retrieve start --manifest package.xml --target-org "$ORG_ALIAS"

# Insert PreWorkBriefPromptTemplate as a new layoutItem in the first column
# of the first layoutSection (typically labeled "Information"):
LAYOUT_FILE="force-app/main/default/layouts/$LAYOUT_FULLNAME.layout-meta.xml"
python3 - <<'PY' "$LAYOUT_FILE"
import sys, re
path = sys.argv[1]
with open(path, "r") as f:
    text = f.read()
if "PreWorkBriefPromptTemplate" in text:
    print("Field already on layout; no change.")
    sys.exit(0)
# Inject before the first </layoutColumns>:
inject = """            <layoutItems>
                <behavior>Edit</behavior>
                <field>PreWorkBriefPromptTemplate</field>
            </layoutItems>
        </layoutColumns>"""
new_text = text.replace("        </layoutColumns>", inject, 1)
with open(path, "w") as f:
    f.write(new_text)
print("Field inserted.")
PY

sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app --wait 5
```

**7c. Verify the field is on the layout.**

```bash
cd /tmp/wo-layout && sf project retrieve start --manifest package.xml --target-org "$ORG_ALIAS"
grep -c "PreWorkBriefPromptTemplate" "force-app/main/default/layouts/$LAYOUT_FULLNAME.layout-meta.xml"
```

Expect `1`. The field is now visible to anyone whose profile is assigned this layout.

**7d. Grant field-level security via a scoped permission set.**

The `PreWorkBriefPromptTemplate` field needs Read/Edit access on every user who interacts with Pre-Work Brief: the admin (to set the field on test Work Orders) and the technician (so the field renders correctly on the mobile record page).

Rather than editing the technician's Profile XML directly (risky — Profile deploys can stomp on unrelated FLS settings), the skill deploys a tiny dedicated permission set and assigns it to both users. Idempotent and scoped.

```bash
mkdir -p /tmp/pwb-fls/force-app/main/default/permissionsets
cat > /tmp/pwb-fls/sfdx-project.json <<'EOF'
{"packageDirectories":[{"path":"force-app","default":true}],"namespace":"","sourceApiVersion":"62.0"}
EOF
cat > /tmp/pwb-fls/force-app/main/default/permissionsets/PreWorkBrief_Field_Access.permissionset-meta.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Grants Read/Edit on Work Order.PreWorkBriefPromptTemplate. Assign to admins (so they can set the field on test Work Orders) and to mobile technicians (so the field is readable when the brief renders).</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Pre-Work Brief Field Access</label>
    <fieldPermissions>
        <editable>true</editable>
        <field>WorkOrder.PreWorkBriefPromptTemplate</field>
        <readable>true</readable>
    </fieldPermissions>
</PermissionSet>
EOF

cd /tmp/pwb-fls
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app --wait 5

# Assign to admin and technician:
sf org assign permset --name PreWorkBrief_Field_Access --on-behalf-of "$ADMIN_USERNAME" --target-org "$ORG_ALIAS"
sf org assign permset --name PreWorkBrief_Field_Access --on-behalf-of "$TECH_USERNAME" --target-org "$ORG_ALIAS"

# Verify:
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Assignee.Username FROM PermissionSetAssignment WHERE PermissionSet.Name = 'PreWorkBrief_Field_Access'" \
  --json | jq -r '.result.records[]? | "  \(.Assignee.Username)"'
```

Expect both `$ADMIN_USERNAME` and `$TECH_USERNAME` to appear in the verify output.

### Step 8: Wire the prompt template to a Work Order for testing

Each Work Order points at a prompt template via the `PreWorkBriefPromptTemplate` field. The skill gives the admin two paths: **8-existing** mutates a Work Order already in the org, or **8-fresh** creates a new test Work Order plus an auto-scheduled Service Appointment assigned to the chosen technician. Path 8-fresh is the recommended default — the admin gets a known-good test artifact without touching live records.

Ask the admin: **"Create a fresh test Work Order, or set the prompt template Id on an existing one?"**

- Fresh (recommended): jump to **Step 8-fresh**.
- Existing: continue with **Step 8-existing**.

### Step 8-existing: Set the prompt template Id on an existing Work Order

Use this path when the admin wants to point a real, in-pipeline Work Order at the prompt template — for example, to test against a job whose data the technician already knows.

**8a. Get the prompt template Id from a deploy record.**

`GenAiPromptTemplate` is not queryable via SOQL or standard REST, so the Id has to come from a side channel. The most reliable CLI path is to read it from the deploy record that created the template (the deploy report records the component Id Salesforce assigned).

```bash
TEMPLATE_DEV_NAME="Pre_Work_Brief"   # or whatever exists in the org

# Find recent deploys, scan each for a GenAiPromptTemplate component matching the developer name:
DEPLOY_IDS=$(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT Id FROM DeployRequest WHERE NumberComponentsDeployed > 0 ORDER BY CompletedDate DESC LIMIT 50" \
  --json | jq -r '.result.records[]?.Id')

TEMPLATE_ID=""
for did in $DEPLOY_IDS; do
  cand=$(sf project deploy report --target-org "$ORG_ALIAS" --job-id "$did" --json 2>/dev/null | \
    jq -r ".result.details.componentSuccesses[]? | select(.componentType == \"GenAiPromptTemplate\" and .fullName == \"$TEMPLATE_DEV_NAME\") | .id" | head -1)
  if [ -n "$cand" ]; then
    TEMPLATE_ID="$cand"
    break
  fi
done
echo "Template Id: $TEMPLATE_ID"
```

If `TEMPLATE_ID` is empty, the template wasn't deployed via this org's recent deploy history. Two fallbacks:

- **Re-deploy** the template (step 5) so a new deploy record carries the Id.
- **Read the Id from Prompt Builder URL.** In Setup, Quick Find **Einstein Generative AI → Prompt Builder**, click into the template, copy the Id from the URL after `EinsteinPromptStudio/`. Example URL `.../lightning/setup/EinsteinPromptStudio/0hfSG000001SUFVYA4/edit?...` → Id is `0hfSG000001SUFVYA4`.

```bash
# Manual fallback if CLI lookup didn't find it:
TEMPLATE_ID="<paste-id-from-url>"
```

**8b. Choose the target Work Order.**

Ask the admin: **"Do you have a specific Work Order you want to add Pre-Work Brief to for testing?"**

**If yes:** the admin supplies a Work Order Id or Number. Validate:

```bash
WO_INPUT="<work-order-id-or-number>"

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, WorkOrderNumber, Subject, Status, Account.Name FROM WorkOrder
           WHERE (Id = '$WO_INPUT' OR WorkOrderNumber = '$WO_INPUT') LIMIT 1" \
  --json | jq -r '.result.records[]? |
    "Test Work Order:\n  Id:      \(.Id)\n  Number:  \(.WorkOrderNumber)\n  Subject: \(.Subject)\n  Account: \(.Account.Name)\n  Status:  \(.Status)"'

WO_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id FROM WorkOrder WHERE Id = '$WO_INPUT' OR WorkOrderNumber = '$WO_INPUT' LIMIT 1" --json | \
  jq -r '.result.records[0].Id')
```

If validation returns nothing, stop and ask for a different Id or Number.

**If no:** auto-pick a Work Order. Pick one that has groundable data (Account, Subject, Status of New / Scheduled / In Progress) and surface it to the admin:

```bash
WO_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id FROM WorkOrder
           WHERE AccountId != null AND Subject != null
             AND Status IN ('New','Scheduled','Dispatched','In Progress')
           ORDER BY CreatedDate DESC LIMIT 1" --json | \
  jq -r '.result.records[0].Id')

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, WorkOrderNumber, Subject, Account.Name, Status FROM WorkOrder WHERE Id = '$WO_ID'" \
  --json | jq -r '.result.records[]? |
    "Auto-selected Work Order for Pre-Work Brief test:\n  Id:      \(.Id)\n  Number:  \(.WorkOrderNumber)\n  Subject: \(.Subject)\n  Account: \(.Account.Name)\n  Status:  \(.Status)\n\nThe skill will set the Pre-Work Brief Prompt Template Id on this Work Order. To pick a different one, re-run with --workorder <Id-or-Number>."'
```

**8c. Set the field on the Work Order.**

```bash
sf data update record --target-org "$ORG_ALIAS" \
  --sobject WorkOrder --record-id "$WO_ID" \
  --values "PreWorkBriefPromptTemplate=$TEMPLATE_ID"
```

**8d. Schedule the Work Order's Service Appointment for today.**

The Field Service Mobile app shows technicians their schedule for today. Even if a Work Order has the prompt template Id set, the technician won't see it on their mobile schedule unless the related Service Appointment falls in today's date window. The skill updates the Service Appointment's `SchedStartTime` and `SchedEndTime` to a 2-hour window in the next few hours, and also sets the Work Order's `StartDate` and `EndDate` to today.

```bash
SA_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id FROM ServiceAppointment WHERE ParentRecordId = '$WO_ID' LIMIT 1" --json | \
  jq -r '.result.records[0].Id // empty')

# Compute timestamps in UTC. Window: 1 hour from now, 2 hours long.
# macOS / BSD date:
START_TIME=$(date -u -v+1H +"%Y-%m-%dT%H:00:00.000Z" 2>/dev/null || \
  # GNU date fallback:
  date -u -d '+1 hour' +"%Y-%m-%dT%H:00:00.000Z")
END_TIME=$(date -u -v+3H +"%Y-%m-%dT%H:00:00.000Z" 2>/dev/null || \
  date -u -d '+3 hours' +"%Y-%m-%dT%H:00:00.000Z")
TODAY=$(date -u +"%Y-%m-%d")

echo "Scheduling Work Order $WO_ID for today:"
echo "  WO StartDate / EndDate: $TODAY"
echo "  SA SchedStartTime: $START_TIME"
echo "  SA SchedEndTime:   $END_TIME"

# Update Work Order date window:
sf data update record --target-org "$ORG_ALIAS" \
  --sobject WorkOrder --record-id "$WO_ID" \
  --values "StartDate=$TODAY EndDate=$TODAY"

# Update Service Appointment if one exists:
if [ -n "$SA_ID" ]; then
  sf data update record --target-org "$ORG_ALIAS" \
    --sobject ServiceAppointment --record-id "$SA_ID" \
    --values "SchedStartTime=$START_TIME SchedEndTime=$END_TIME"
else
  echo "  Note: no Service Appointment found for this Work Order. The technician"
  echo "  may not see the WO in today's schedule. Either pick a Work Order that"
  echo "  has a Service Appointment, or create one manually before testing."
fi
```

Some Field Service orgs assign the Service Appointment to a specific Service Resource; if that's the case, the Work Order will only appear on that resource's schedule. If the auto-picked Work Order's appointment is assigned to a different resource than the chosen technician, either pick a Work Order whose appointment is already assigned to the technician, or assign one manually.

**8e. Verify all updates.**

```bash
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT WorkOrderNumber, PreWorkBriefPromptTemplate, StartDate, EndDate FROM WorkOrder WHERE Id = '$WO_ID'" \
  --json | jq -r '.result.records[0]'

if [ -n "$SA_ID" ]; then
  sf data query --target-org "$ORG_ALIAS" \
    --query "SELECT AppointmentNumber, SchedStartTime, SchedEndTime, Status FROM ServiceAppointment WHERE Id = '$SA_ID'" \
    --json | jq -r '.result.records[0]'
fi
```

Confirm `PreWorkBriefPromptTemplate` matches `$TEMPLATE_ID`, dates fall on today, and the Service Appointment time window is in the next few hours.

**8e. (Optional) Roll out to many Work Orders.** Once the test Work Order works on-device (step 9), set the field on additional Work Orders. Two patterns:

- **Bulk update by CSV.** Export a list of Work Order Ids, build a CSV with `Id,PreWorkBriefPromptTemplate`, and use `sf data import bulk`.
- **Auto-fill via a Flow.** Salesforce's documented production pattern: a record-triggered Flow on Work Order creation that sets `PreWorkBriefPromptTemplate` based on Work Type, Subject, or any other rule. Use the afv-library `generating-flow` skill to build the Flow. See `help.salesforce.com/s/articleView?id=platform.flow.htm`.

### Step 8-fresh: Create a fresh test Work Order + Service Appointment

A fresh record is cleaner than mutating one in the org's existing pipeline. Existing operations keep working, and the admin gets a clearly-labeled artifact to validate Pre-Work Brief end-to-end.

The path needs a Service Resource so the auto-created Service Appointment lands on a real technician's schedule. The skill defaults to the technician chosen in Step 0.5; if that user doesn't have a `ServiceResource` row, the admin supplies one.

**8-fresh-a. Resolve the Service Resource.**

```bash
SERVICE_RESOURCE_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id FROM ServiceResource WHERE RelatedRecordId = '$TECH_USER_ID' AND IsActive = true LIMIT 1" --json | \
  jq -r '.result.records[0].Id // empty')

if [ -z "$SERVICE_RESOURCE_ID" ]; then
  echo "No active ServiceResource found for technician $TECH_USERNAME."
  echo "Available active technician resources:"
  sf data query --target-org "$ORG_ALIAS" \
    --query "SELECT Id, Name, RelatedRecord.Username FROM ServiceResource WHERE IsActive = true AND ResourceType = 'T' AND RelatedRecord.IsActive = true ORDER BY Name LIMIT 10" \
    --json | jq -r '.result.records[]? | "  \(.Id) | \(.Name) | \(.RelatedRecord.Username)"'
  echo ""
  echo "Re-run with --service-resource <Id> to pick one, or assign a ServiceResource to $TECH_USERNAME first."
  exit 1
fi

echo "Service Resource: $SERVICE_RESOURCE_ID"
```

**8-fresh-b. Pick an Account to attach the test WO to.**

```bash
TEST_ACCOUNT_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT Id, Name FROM Account WHERE IsDeleted = false ORDER BY CreatedDate DESC LIMIT 1" --json | \
  jq -r '.result.records[0].Id')

echo "Attaching test WO to Account Id: $TEST_ACCOUNT_ID"
```

If the org has no Accounts, ask the admin to supply one or create a quick test Account first.

**8-fresh-c. Create the Work Order with the prompt template Id pre-filled.**

```bash
TODAY=$(date -u +"%Y-%m-%d")
START_TIME=$(date -u -v+1H +"%Y-%m-%dT%H:00:00.000Z" 2>/dev/null || date -u -d '+1 hour' +"%Y-%m-%dT%H:00:00.000Z")
END_TIME=$(date -u -v+3H +"%Y-%m-%dT%H:00:00.000Z" 2>/dev/null || date -u -d '+3 hours' +"%Y-%m-%dT%H:00:00.000Z")

WO_ID=$(sf data create record --target-org "$ORG_ALIAS" --sobject WorkOrder \
  --values "Subject='PWB Test (auto-created)' AccountId=$TEST_ACCOUNT_ID Status='New' StartDate=$TODAY EndDate=$TODAY PreWorkBriefPromptTemplate=$TEMPLATE_ID" \
  --json | jq -r '.result.id')

echo "✓ Work Order: $WO_ID"

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT WorkOrderNumber, Subject, PreWorkBriefPromptTemplate FROM WorkOrder WHERE Id = '$WO_ID'" \
  --json | jq -r '.result.records[0]'
```

If the create fails on `PreWorkBriefPromptTemplate` not being writable, assign the `PreWorkBrief_Field_Access` permission set (deployed in Step 7d) to the admin running this skill, then retry.

**8-fresh-d. Create the Service Appointment scheduled for today.**

The Service Appointment needs a Service Territory in most orgs (the field is technically nillable but populated territories are the norm in real configurations and several orgs require one). Resolve the territory the chosen Service Resource is a member of and pass it on create.

```bash
SERVICE_TERRITORY_ID=$(sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT ServiceTerritoryId FROM ServiceTerritoryMember WHERE ServiceResourceId = '$SERVICE_RESOURCE_ID' AND EffectiveEndDate = null LIMIT 1" --json | \
  jq -r '.result.records[0].ServiceTerritoryId // empty')

echo "Service Territory: ${SERVICE_TERRITORY_ID:-<none — will create SA without territory>}"

SA_VALUES="ParentRecordId=$WO_ID Subject='PWB Test (auto-created)' SchedStartTime=$START_TIME SchedEndTime=$END_TIME EarliestStartTime=$START_TIME DueDate=$END_TIME Status=Scheduled"
[ -n "$SERVICE_TERRITORY_ID" ] && SA_VALUES="$SA_VALUES ServiceTerritoryId=$SERVICE_TERRITORY_ID"

SA_ID=$(sf data create record --target-org "$ORG_ALIAS" --sobject ServiceAppointment \
  --values "$SA_VALUES" --json | jq -r '.result.id')

echo "✓ Service Appointment: $SA_ID"
```

If the create still fails with a Service Territory error and the resource has no `ServiceTerritoryMember`, ask the admin to either pick a different resource or add the resource to a territory in Setup → Service Territories.

**8-fresh-e. Assign the Service Appointment to the Service Resource.**

```bash
AR_ID=$(sf data create record --target-org "$ORG_ALIAS" --sobject AssignedResource \
  --values "ServiceAppointmentId=$SA_ID ServiceResourceId=$SERVICE_RESOURCE_ID" \
  --json | jq -r '.result.id')

echo "✓ AssignedResource: $AR_ID"
```

**8-fresh-f. Verify the chain end-to-end.**

```bash
echo ""
echo "Test artifact summary:"
sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT WorkOrderNumber, Subject, Account.Name, PreWorkBriefPromptTemplate, StartDate FROM WorkOrder WHERE Id = '$WO_ID'" \
  --json | jq -r '.result.records[0]'

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT AppointmentNumber, SchedStartTime, SchedEndTime, Status FROM ServiceAppointment WHERE Id = '$SA_ID'" \
  --json | jq -r '.result.records[0]'

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT ServiceResource.Name, ServiceResource.RelatedRecord.Username FROM AssignedResource WHERE Id = '$AR_ID'" \
  --json | jq -r '.result.records[0]'
```

The admin can now sign in as `$TECH_USERNAME` on the Field Service mobile app and find the auto-created Work Order on today's schedule. Skip ahead to Step 9 for on-device verification.

### Step 9: Verify on a mobile device

Open the Field Service mobile app on iOS or Android. Sign in as a user who holds the **Einstein Field Service User** and **Prompt Template User** permission sets, plus the Field Service Mobile license. Connect the device to the internet.

1. Open a Work Order whose **Pre-Work Brief Prompt Template ID** field is set.
2. Confirm the Pre-Work Brief renders in the **Overview tab** of the Work Order.
3. Confirm the brief content references the actual Work Order, not generic boilerplate.
4. After 24 hours, re-open the same Work Order and confirm the brief regenerates.

If the brief is missing or empty, see **Common Issues** below.

---

## Optional: Modify the brief

The default flow and prompt are a starting point. You can clone them and customize:

1. In Setup, Quick Find **Process Automation → Flows**.
2. Open **Field Service Mobile: Generate Pre-Work Brief**.
3. Click **Save As** to clone the flow.
4. Edit the cloned flow:
   - Modify the **Serialize Pre-Work Brief Records** action to include additional objects.
   - Add fields to the **Get Contacts** element.
   - Add elements for custom fields used in your org.
5. To modify the prompt itself, open the **Add Pre-Work Brief Prompt Instructions** element. Add or remove instructions. Examples:
   - "Make sure the brief is no longer than 200 words."
   - "Present the brief in bullet points."
6. Create a new prompt template (step 5 again) that points at the cloned flow.
7. Update the Work Order field to use the new prompt template ID.

For different scenarios — for example, an emergency-appointment brief versus a routine-appointment brief — create multiple flow + prompt template pairs and set the Work Order field per record.

> Avoid telling the prompt to always include a specific field. If the value is missing, generative AI can hallucinate inaccurate results.
>
> Add examples of what you expect the brief to look like rather than rigid rules.

---

## Configuration Reference

| Concern | Where it lives | How to change |
|---|---|---|
| Who can see Pre-Work Brief | `Einstein Field Service User` + `Prompt Template User` permission sets, plus the Field Service Mobile license | Setup → Permission Sets → Manage Assignments (step 4) |
| Who can edit prompts | `Prompt Template Manager` permission set | Setup → Permission Sets → Manage Assignments (step 4) |
| What the brief says | The `Field Service Pre-Work Brief` prompt template, plus the linked Flow | Prompt Builder + Flow Builder (steps 5, 6, optional Modify) |
| Which prompt template runs for a given Work Order | `Pre-Work Brief Prompt Template ID` field on Work Order | Manual edit, CLI update, or a Flow that sets it (step 8) |
| Which LLM generates the brief | Salesforce-managed | Not customer-configurable |
| Where the brief renders | **Overview tab of the Work Order** in the FS Mobile app | Not configurable |
| When the brief regenerates | First view online, then every 24 hours | Not configurable |

---

## Common Issues

**The brief is missing entirely on a Work Order.**

Check in this order:

1. The Work Order's **Pre-Work Brief Prompt Template ID** field is set to a valid prompt template ID.
2. The signed-in user holds **Einstein Field Service User** and **Prompt Template User** permission sets.
3. Lightning Data Service is enabled for Field Service Mobile.
4. The mobile device was online when the Work Order was opened. The brief is generated only on first online view; offline opens do not generate it.

**The brief renders but is generic and doesn't reference the actual job.**

The Flow grounding is failing. Walk the field list in `mfs_einstein_pre_work_brief_data.htm`:

- Some fields the Flow expects don't exist in your org. Edit the cloned Flow to remove them.
- Field-level security is hiding fields from the running user. Set the relevant fields to **Visible** for the user's profile.

**The prompt template fails to activate.**

The Resource lookup couldn't find **Field Service Mobile: Generate Pre-Work Brief**. Confirm the managed Field Service flow templates are deployed in the org. If they are missing, the org may not have the Einstein for Field Service add-on fully provisioned — return to step 1.

**The brief shows on desktop but not on mobile.**

Almost always a Lightning Data Service issue. Confirm step 2 was completed. Then confirm the mobile user has the LDS permission set assigned per `mfs_lightning_data_service.htm`.

**The brief never regenerates after I change the Flow.**

Pre-Work Brief regenerates only after 24 hours, or when the Work Order's prompt template ID changes. To force regeneration during testing, point the Work Order at a different (or newly created) prompt template.

---

## Verification Checklist

Run before declaring Pre-Work Brief enabled in production:

- [ ] `sf org display --target-org "$ORG_ALIAS"` returns the expected org.
- [ ] At least one Einstein for Field Service PSL is present with `TotalLicenses > 0`.
- [ ] Lightning Data Service for Field Service Mobile is enabled.
- [ ] Einstein generative AI base setup is complete, including Data 360.
- [ ] `EinsteinFieldServiceUser`, `EinsteinGPTPromptTemplateManager`, and `EinsteinGPTPromptTemplateUser` permission sets exist in the org and are assigned to the appropriate users.
- [ ] The managed flow **Field Service Mobile: Generate Pre-Work Brief** is present in the org (visible via `sf org list metadata --metadata-type Flow`).
- [ ] A `Field Service Pre-Work Brief` prompt template exists, points at that flow, and is activated.
- [ ] The Work Order field `PreWorkBriefPromptTemplate` (label "Pre-Work Brief Prompt Template ID") is on the layouts assigned to mobile workers and admins, and is set to a valid prompt template ID on at least one test Work Order.
- [ ] On-device test: a real mobile worker opens that Work Order online and the brief renders in the Overview tab with job-specific content.

---

## Conventions

- **Idempotent.** Re-running the full sequence on an already-configured org applies zero changes. Each step's check passes silently if the change is already in place.
- **Production safety.** Prompt for explicit confirmation before running any `sf data update record` against a production org.
- **Read API names back from the org.** PSL `DeveloperName` and the prompt template ID are read from the target org rather than hard-coded.
- **Single source of truth.** Where Salesforce Help documents a setup step, this skill cites the article rather than reproducing or contradicting it.
- **No external dependencies.** The skill uses the Salesforce CLI, POSIX shell, and `jq`. It runs unchanged on any machine with `sf` installed.

---

## Related afv-library Skills

This skill composes with several existing afv-library skills:

- `generating-flow` — recommended for step 8's "Flow that auto-fills the prompt template ID" pattern. Also useful when cloning and customizing the **Field Service Mobile: Generate Pre-Work Brief** flow in the optional Modify section.
- `generating-permission-set` — useful if you want to bundle the three Einstein for Field Service permission sets into a single org-specific permission set for assignment.
- `developing-agentforce` — for related Agentforce features in Field Service (Service Agent, Customer-Initiated Scheduling). Pre-Work Brief itself is not built as an Agentforce agent; it is a prompt template + flow, no agent required.

---

## References

External (Salesforce Help):

- Pre-Work Brief setup: `https://help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief.htm`
- Pre-Work Brief data and grounding fields: `https://help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief_data.htm`
- Set Up Permissions for Einstein for Field Service Mobile: `https://help.salesforce.com/s/articleView?id=service.fs_einstein_gen_ai_setup.htm`
- Lightning Data Service for Field Service Mobile: `https://help.salesforce.com/s/articleView?id=service.mfs_lightning_data_service.htm`
- Set Up Einstein Generative AI: `https://help.salesforce.com/s/articleView?id=ai.generative_ai_enable.htm`
- Prompt Builder: `https://help.salesforce.com/s/articleView?id=ai.prompt_builder_about.htm`
- Agentforce and Einstein for Field Service feature catalog: `https://help.salesforce.com/s/articleView?id=service.fs_einstein_setup_parent.htm`

---

## Known Limitations

- The brief regenerates only after 24 hours. There is no customer-facing setting to shorten this interval.
- Mobile workers must be online for the first view of a Work Order to generate the brief.
- Pre-Work Brief is a one-shot summary, not a conversation. There is no built-in handoff to a conversational agent today.
- Pre-Work Brief targets the Work Order Overview tab. It does not render on the Service Appointment record page.
- Mobile Extension Toolkit (MET) is not supported alongside Lightning Data Service. If your org uses MET extensions, plan for migration before enabling Pre-Work Brief.
