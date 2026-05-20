---
name: customizing-pre-work-brief
description: "Generate a vertical-specific Pre-Work Brief on Field Service Mobile, deployable as code. The admin provides industry, website, and a sentence describing what their technicians do; this skill produces custom objects, an autolaunched flow, a prompt template, a permission set, and a test record. TRIGGER when: user wants Pre-Work Brief tailored to their company or industry; user wants the brief to reference custom objects or fields specific to their business; user mentions website-grounded or vertical-specific briefs; user wants a second 'customized' brief alongside the default; user asks to clone or extend the managed Field Service flow; user references a specific vertical (HVAC, banking, telecom, healthcare, retail merchandising). DO NOT TRIGGER when: org has not yet completed base setup (use setting-up-pre-work-brief first); user wants Voice to Form; user wants Post-Work Summary; user wants a brand-new prompt template type from scratch (use Prompt Builder docs)."
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
license: Apache-2.0
metadata:
  version: "0.2.0"
  last_updated: "2026-05-20"
  argument-hint: "<org-alias> --company <name> --industry <hvac|banking|telecom|healthcare|retail-merchandising|other> --website <url> [--description <text>] [--service-resource <id>]"
  compatibility: claude-code
---

# Customizing Pre-Work Brief

Generate a vertical-specific Pre-Work Brief that grounds on the customer's business and the data model their technicians actually work with. The skill produces a deployable bundle — custom objects, autolaunched flow, prompt template, permission set, plus a test Work Order — so an admin goes from "the default brief works but feels generic" to "the brief reads like someone who knows our business wrote it" in one run.

This skill is the second half of a two-step adoption journey. Step one — `setting-up-pre-work-brief` — gets PWB working at all on the managed flow. Step two — this skill — replaces the managed flow with a customer-specific bundle deployable entirely from metadata. No Save-As click in Flow Builder is required; the only manual step is one click to activate the prompt template, consistent with the base setup pattern.

The skill is **vertical-agnostic by design.** It ships with seed templates for common Field Service archetypes (HVAC, banking, telecom, healthcare, retail merchandising) at `templates/<industry>.md`. The seed contributes a section structure, recommended custom objects, and grounding patterns. For verticals not in the library, the skill synthesizes from the website + admin description and adds the result back into `templates/` for next time.

---

## Prerequisites

The base setup must be complete. Run `setting-up-pre-work-brief` against the same org first if any of the checks below fail:

```bash
ORG_ALIAS="${1:-}"
[ -z "$ORG_ALIAS" ] && { echo "Usage: customizing-pre-work-brief <org-alias> --company <name> --industry <vertical> --website <url>"; exit 1; }

echo "Checking base setup is in place..."

sf org list metadata --metadata-type GenAiPromptTemplate --target-org "$ORG_ALIAS" --json | \
  jq -r '[.result[]? | select(.fullName == "Pre_Work_Brief")] | length as $n |
    if $n > 0 then "✓ Default Pre_Work_Brief template deployed" else "✗ Default template missing — run setting-up-pre-work-brief first" end'

sf data query --target-org "$ORG_ALIAS" \
  --query "SELECT DeveloperName FROM PermissionSetLicense WHERE DeveloperName = 'EinsteinFieldServicePsl' AND TotalLicenses > 0" --json | \
  jq -r '.result.totalSize as $n | if $n > 0 then "✓ Einstein for Field Service PSL present" else "✗ PSL missing — run setting-up-pre-work-brief first" end'

sf sobject describe --sobject WorkOrder --target-org "$ORG_ALIAS" --json | \
  jq -r '[.result.fields[]? | select(.name == "PreWorkBriefPromptTemplate")] | length as $n |
    if $n > 0 then "✓ PreWorkBriefPromptTemplate field present" else "✗ Field missing — run setting-up-pre-work-brief first" end'
```

All three must report `✓` before continuing.

---

## Args

| Arg | Required | Default | Purpose |
|---|---|---|---|
| `<org-alias>` | yes | — | Target org. |
| `--company <name>` | yes | — | Company name. Used in the prompt template label and in business context generation. |
| `--industry <vertical>` | yes | — | One of: `hvac`, `banking`, `telecom`, `healthcare`, `retail-merchandising`, or `other`. Picks the seed template at `templates/<industry>.md`. If `other`, the skill synthesizes a template at runtime. |
| `--website <url>` | yes | — | Public website URL. The skill fetches the homepage to derive technician context. |
| `--description <text>` | no | (admin prompted) | 1-2 sentence description of what the company's technicians actually do on-site. If omitted, the skill asks. |
| `--service-resource <id>` | no | (admin prompted) | ServiceResource Id to assign the test Service Appointment to. |
| `--customized-template-name <name>` | no | `PreWorkBrief_<Industry>_<Company>` | Developer name of the new prompt template. Increment if running multiple times for the same org. |

Parse args:

```bash
COMPANY=""
INDUSTRY=""
WEBSITE=""
DESCRIPTION=""
SERVICE_RESOURCE_ID=""
TEMPLATE_NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --company) COMPANY="$2"; shift 2 ;;
    --industry) INDUSTRY="$2"; shift 2 ;;
    --website) WEBSITE="$2"; shift 2 ;;
    --description) DESCRIPTION="$2"; shift 2 ;;
    --service-resource) SERVICE_RESOURCE_ID="$2"; shift 2 ;;
    --customized-template-name) TEMPLATE_NAME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[ -z "$COMPANY" ] && { echo "--company is required"; exit 1; }
[ -z "$INDUSTRY" ] && { echo "--industry is required (hvac|banking|telecom|healthcare|retail-merchandising|other)"; exit 1; }
[ -z "$WEBSITE" ] && { echo "--website is required"; exit 1; }

# Default template name
if [ -z "$TEMPLATE_NAME" ]; then
  CLEAN_COMPANY=$(echo "$COMPANY" | tr -cd '[:alnum:]_')
  CLEAN_INDUSTRY=$(echo "$INDUSTRY" | tr '[:lower:]' '[:upper:]' | head -c 1)$(echo "$INDUSTRY" | tail -c +2)
  TEMPLATE_NAME="PreWorkBrief_${CLEAN_INDUSTRY}_${CLEAN_COMPANY}"
fi
```

---

## Step 1: Build the business context

Combine the company website with the admin's description into a short technician-facing brief.

**1a. Fetch the website.**

Use Claude's `WebFetch` tool against `$WEBSITE` with the prompt:

> Read this company's homepage and any obvious sub-pages. Return a 5-bullet summary of (1) what the company does, (2) the products or services they sell, (3) who their typical customer is, (4) what kind of work a field technician would perform on-site for them, (5) any specialized equipment, certifications, or terminology a technician would need to know. Keep it factual and pulled directly from the page. Do not invent details.

Capture the response as `$WEBSITE_SUMMARY`.

**1b. Get the admin's description.**

If `--description` was passed, use it directly. Otherwise ask:

> "In 1-2 sentences, what do your technicians actually do on-site for this business?"

Capture as `$ADMIN_DESCRIPTION`.

**1c. Synthesize.**

Combine `$WEBSITE_SUMMARY` and `$ADMIN_DESCRIPTION` into a single 3-5 sentence paragraph saved as `$BUSINESS_CONTEXT`. Show the result to the admin and ask for sign-off before continuing.

---

## Step 2: Load the vertical seed template

```bash
SEED_PATH="templates/${INDUSTRY}.md"

if [ -f "$SEED_PATH" ]; then
    echo "✓ Found seed template at $SEED_PATH"
    SEED=$(cat "$SEED_PATH")
else
    echo "No seed for industry '$INDUSTRY'. Synthesizing one from business context."
    INDUSTRY="other"
    SEED=""
fi
```

The seed contributes:

- **Section structure** for the prompt template (e.g., HVAC = Mission and contact / Customer and SLA / Site access and certifications / Equipment and refrigerant context).
- **Recommended custom objects** with the fields each typically carries.
- **Standard objects + fields** to query in the flow.
- **Cadence example** to anchor the model's tone.

If the seed doesn't exist, the skill writes one at the end of the run so the next admin in the same vertical gets it.

---

## Step 3: Audit the org's existing schema

Some of what the seed proposes may already exist in the org. Audit before creating duplicates.

```bash
GROUNDING_OBJECTS="Account Asset Contact Case WorkOrder WorkOrderLineItem ServiceAppointment WorkPlan WorkStep"
EXCLUDE_NAMESPACES="FSL__,FSSK__,SDO__,FSLDemoTools__"

for obj in $GROUNDING_OBJECTS; do
    echo ""
    echo "Custom fields on $obj:"
    sf sobject describe --sobject "$obj" --target-org "$ORG_ALIAS" --json 2>/dev/null | \
      jq -r --arg obj "$obj" --arg exclude "$EXCLUDE_NAMESPACES" '
        ($exclude | split(",")) as $ns_list |
        .result.fields[]?
        | select(.name | endswith("__c"))
        | . as $f
        | select(any($ns_list[]; . as $ns | $f.name | startswith($ns)) | not)
        | "  \($obj).\(.name) | type=\(.type) | label=\(.label)"
      '
done > /tmp/pwb-existing-customs.txt

# Check whether the seed's recommended custom objects already exist
sf sobject list --target-org "$ORG_ALIAS" --sobject-type custom --json | \
  jq -r '.result[]?' > /tmp/pwb-existing-objects.txt

cat /tmp/pwb-existing-customs.txt
echo ""
echo "Existing custom objects: $(wc -l < /tmp/pwb-existing-objects.txt)"
```

Cross-reference against the seed's recommended objects. For each recommended object:

- Already exists → skip object creation, audit its fields.
- Doesn't exist → propose to admin for creation.

Show the diff to the admin and ask for confirmation before deploying anything.

---

## Step 4: Generate and deploy custom objects

For each approved custom object, write metadata files. The general shape (using HVAC's `Refrigerant_Log__c` as an illustration; the actual fields come from the seed):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <description>{seed-supplied description}</description>
    <enableActivities>true</enableActivities>
    <enableHistory>true</enableHistory>
    <enableReports>true</enableReports>
    <enableSearch>true</enableSearch>
    <label>{seed-supplied label}</label>
    <nameField>
        <label>{Object} Number</label>
        <type>AutoNumber</type>
        <displayFormat>{prefix}-{0000}</displayFormat>
        <startingNumber>1</startingNumber>
    </nameField>
    <pluralLabel>{seed-supplied plural label}</pluralLabel>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

Lookup field rules to avoid the "must specify either cascade delete or restrict delete" deploy error:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Asset__c</fullName>
    <deleteConstraint>SetNull</deleteConstraint>
    <label>Asset</label>
    <referenceTo>Asset</referenceTo>
    <relationshipLabel>Refrigerant Logs</relationshipLabel>
    <relationshipName>Refrigerant_Logs</relationshipName>
    <type>Lookup</type>
</CustomField>
```

Note: do not set `<required>true</required>` on lookups — pair it with `<deleteConstraint>` or the deploy fails. For the customs the brief queries, optional lookups are fine.

If any new lookup goes onto WorkOrder (e.g., `WorkOrder.Maintenance_Contract__c`), write that field too — the flow will reference it via `$Input.WorkOrder.<New_Field>__c`.

Deploy:

```bash
mkdir -p /tmp/pwb-custom-build/force-app/main/default
cat > /tmp/pwb-custom-build/sfdx-project.json <<'EOF'
{"packageDirectories":[{"path":"force-app","default":true}],"namespace":"","sourceApiVersion":"65.0"}
EOF

# (Write all object + field XMLs into /tmp/pwb-custom-build/force-app/main/default/objects/...)

cd /tmp/pwb-custom-build
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app --wait 30 --api-version 65.0
```

---

## Step 5: Generate the from-scratch flow

Write a `PromptFlow` flow that grounds on the relevant standard objects + the new customs. The pattern (verified working against the `afvuser` trial org, 2026-05-20):

- `<processType>PromptFlow</processType>`
- `<apiVersion>65.0</apiVersion>` (the managed flow's `getCustomerSignalsInsights` action requires v65+; from-scratch flows that don't use it can stay lower, but 65 is the safe default)
- `<start>` block has `<triggerType>Capability</triggerType>` and a `<capabilityTypes>` element declaring `PromptTemplateType://einstein_gpt__fieldServicePreWorkBrief` with a `WorkOrder` SObject input
- A chain of `<recordLookups>` elements with `getFirstRecordOnly=true` (single-record references resolve cleanly; collections require Loops which complicate the demo)
- An `<assignments>` element with `<elementSubtype>AddPromptInstructions</elementSubtype>` that builds `$Output.Prompt` from grounded references

Skeleton:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>65.0</apiVersion>
    <description>{Industry}-specific Pre-Work Brief grounding flow for {Company}.</description>
    <interviewLabel>Pre-Work Brief {Industry} {!$Flow.CurrentDateTime}</interviewLabel>
    <label>Pre-Work Brief {Industry} Custom</label>
    <processType>PromptFlow</processType>
    <status>Active</status>
    <start>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <capabilityTypes>
            <name>PromptTemplateType://einstein_gpt__fieldServicePreWorkBrief</name>
            <capabilityName>PromptTemplateType://einstein_gpt__fieldServicePreWorkBrief</capabilityName>
            <inputs>
                <name>WorkOrder</name>
                <capabilityInputName>WorkOrder</capabilityInputName>
                <dataType>SOBJECT://WorkOrder</dataType>
                <isCollection>false</isCollection>
            </inputs>
        </capabilityTypes>
        <connector>
            <targetReference>{first lookup}</targetReference>
        </connector>
        <triggerType>Capability</triggerType>
    </start>
    <!-- recordLookups, then a single assignments that builds $Output.Prompt -->
</Flow>
```

The seed at `templates/<industry>.md` enumerates which lookups to chain, what each queries, and how `$Output.Prompt` is structured.

Deploy:

```bash
cd /tmp/pwb-custom-build
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app/main/default/flows --wait 30 --api-version 65.0
```

Activate the flow (deploying with `<status>Active</status>` is necessary but not sufficient — Salesforce treats it as draft until explicitly activated):

```bash
FD_ID=$(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT Id FROM FlowDefinition WHERE DeveloperName = '${TEMPLATE_NAME}_Flow'" --json | \
  jq -r '.result.records[0].Id')

LATEST_VERSION=$(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
  --query "SELECT VersionNumber FROM Flow WHERE Definition.DeveloperName = '${TEMPLATE_NAME}_Flow' ORDER BY VersionNumber DESC LIMIT 1" --json | \
  jq -r '.result.records[0].VersionNumber')

cat > /tmp/activate-flow.json <<EOF
{"Metadata": {"activeVersionNumber": $LATEST_VERSION}}
EOF
sf api request rest --target-org "$ORG_ALIAS" --method PATCH \
  "/services/data/v65.0/tooling/sobjects/FlowDefinition/$FD_ID" \
  --body @/tmp/activate-flow.json
```

---

## Step 6: Generate the prompt template

Build a `GenAiPromptTemplate` with three sections from the seed: business-context paragraph, flow reference, instruction block (sections + rules + cadence example). The flow reference is the single line:

```
{!$Flow:<flow-developer-name>.Prompt}
```

Skeleton:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<GenAiPromptTemplate xmlns="http://soap.sforce.com/2006/04/metadata">
    <developerName>{TEMPLATE_NAME}</developerName>
    <masterLabel>Pre-Work Brief — {Company} ({Industry})</masterLabel>
    <templateVersions>
        <content>You are briefing a {Industry} field technician on the job they are about to perform on-site. Address the technician directly, in the second person.

Business context (do not contradict):
{BUSINESS_CONTEXT}

Specific job grounding:
{!$Flow:{flow-developer-name}.Prompt}

{INSTRUCTION_BLOCK from seed — sections + rules + cadence example}
</content>
        <inputs>
            <apiName>WorkOrder</apiName>
            <definition>SOBJECT://WorkOrder</definition>
            <referenceName>Input:WorkOrder</referenceName>
            <required>true</required>
        </inputs>
        <primaryModel>sfdc_ai__DefaultOpenAIGPT4OmniMini</primaryModel>
        <status>Published</status>
        <templateDataProviders>
            <definition>flow://{flow-developer-name}</definition>
            <parameters>
                <definition>SOBJECT://WorkOrder</definition>
                <isRequired>true</isRequired>
                <parameterName>WorkOrder</parameterName>
                <valueExpression>{!$Input:WorkOrder}</valueExpression>
            </parameters>
            <referenceName>Flow:{flow-developer-name}</referenceName>
        </templateDataProviders>
    </templateVersions>
    <type>einstein_gpt__fieldServicePreWorkBrief</type>
    <visibility>Global</visibility>
</GenAiPromptTemplate>
```

Deploy and surface the activation deeplink:

```bash
cd /tmp/pwb-custom-build
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app/main/default/genAiPromptTemplates --wait 30 --api-version 65.0

# Resolve the template Id
TEMPLATE_ID=$(sf api request rest "/services/data/v62.0/einstein/prompt-templates?pageSize=200" --target-org "$ORG_ALIAS" 2>/dev/null | \
  python3 -c "
import sys, json, os
d = json.loads(sys.stdin.read())
name = os.environ.get('TEMPLATE_NAME')
for t in d.get('promptRecords', []):
    if t.get('fields', {}).get('DeveloperName', {}).get('value') == name:
        print(t.get('fields', {}).get('Id', {}).get('value'))
        break")

# Fall back to deploy report if runtime catalog hasn't picked it up yet
if [ -z "$TEMPLATE_ID" ]; then
  for did in $(sf data query --target-org "$ORG_ALIAS" --use-tooling-api \
      --query "SELECT Id FROM DeployRequest WHERE NumberComponentsDeployed > 0 ORDER BY CompletedDate DESC LIMIT 10" --json | \
      jq -r '.result.records[]?.Id'); do
    cand=$(sf project deploy report --target-org "$ORG_ALIAS" --job-id "$did" --json 2>/dev/null | \
      jq -r ".result.details.componentSuccesses[]? | select(.componentType == \"GenAiPromptTemplate\" and .fullName == \"$TEMPLATE_NAME\") | .id" | head -1)
    [ -n "$cand" ] && TEMPLATE_ID="$cand" && break
  done
fi

echo ""
echo "  ⚠ Action required: click Activate in Prompt Builder."
echo "  The template is deployed and Published, but until activated, it"
echo "  won't appear in the runtime catalog. The mobile app will fail with"
echo "  'We hit a snag' until activation is complete."
echo ""
echo "  Generating sign-in link to the template (valid ~15 minutes):"
sf org open --target-org "$ORG_ALIAS" \
  --path "/lightning/setup/EinsteinPromptStudio/$TEMPLATE_ID/edit" \
  --url-only 2>&1 | grep -oE 'https://[^[:cntrl:][:space:]]+frontdoor[^[:cntrl:][:space:]]+' | head -1 | sed 's/\x1b\[[0-9;]*m//g'
```

Pause until the admin confirms activation. Verify:

```bash
sf api request rest "/services/data/v62.0/einstein/prompt-templates?pageSize=200" --target-org "$ORG_ALIAS" 2>/dev/null | \
  python3 -c "
import sys, json, os
d = json.loads(sys.stdin.read())
name = os.environ.get('TEMPLATE_NAME')
hit = [t for t in d.get('promptRecords', []) if t.get('fields', {}).get('DeveloperName', {}).get('value') == name]
print('✓ Active in runtime catalog' if hit else '✗ Not yet active — click Activate in Prompt Builder')"
```

> **Why a click is still required.** Salesforce does not currently expose a programmatic activation path for `GenAiPromptTemplate`. We tried Tooling REST PATCH on `IsActive`, Connect API `/activate` endpoints across v62-v66, Apex `ConnectApi.EinsteinLLM` methods, and metadata `activeVersionNumber` — none work for `GenAiPromptTemplate` (the `activeVersionNumber` PATCH does work for Flow, which is why Step 5 can activate the flow programmatically). The skill follows the same one-click activation pattern the base `setting-up-pre-work-brief` skill uses for consistency.

---

## Step 7: Generate the permission set

Bundle CRUD on the new objects, FLS on the new fields (including any new WorkOrder lookups), and assign to admin + technician:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Read/Edit on {Industry} custom objects + new fields used by the {Industry} Pre-Work Brief flow for {Company}.</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Pre-Work Brief {Industry} Access ({Company})</label>
    <objectPermissions>
        <allowCreate>true</allowCreate>
        <allowDelete>true</allowDelete>
        <allowEdit>true</allowEdit>
        <allowRead>true</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>{Custom_Object__c}</object>
        <viewAllRecords>true</viewAllRecords>
    </objectPermissions>
    <!-- Repeat objectPermissions for each new custom object -->
    <fieldPermissions><editable>true</editable><field>{Object}.{Field__c}</field><readable>true</readable></fieldPermissions>
    <!-- Repeat fieldPermissions for each new field -->
</PermissionSet>
```

Deploy + assign:

```bash
cd /tmp/pwb-custom-build
sf project deploy start --target-org "$ORG_ALIAS" --source-dir force-app/main/default/permissionsets --wait 30 --api-version 65.0

PERMSET_NAME="PreWorkBrief_${INDUSTRY}_Access"
sf org assign permset --name "$PERMSET_NAME" --target-org "$ORG_ALIAS"
sf org assign permset --name "$PERMSET_NAME" --on-behalf-of "$TECH_USERNAME" --target-org "$ORG_ALIAS"
```

> **Asset.ProductDescription gotcha.** Verified during the HVAC dry-run on `afvuser` (2026-05-19): even with full Asset CRUD granted, `ProductDescription` is read-only for non-admin profiles in some org configurations. If the seed proposes populating it, fall back to writing the same content into `Asset.Description` instead.

---

## Step 8: Create a fresh test Work Order with seed data

Mirrors the `setting-up-pre-work-brief` Step 8-fresh pattern. Resolve Service Resource + Service Territory dynamically; create Account → Asset → custom-object records → Contact → WO → SA → AssignedResource as a chain so the brief has real data to ground on.

The seed contributes example values for the test record (e.g., HVAC seed populates a 10-ton rooftop unit, Platinum SLA contract, R-410A refrigerant log at 14.2 lbs).

After creation, hand off to the admin:

> The {Industry} Pre-Work Brief is wired up. Open the Field Service mobile app, sign in as **`$TECH_USERNAME`**, navigate to today's schedule. The new Work Order **`$WO_NUMBER`** should appear. Open it; the Pre-Work Brief should render in the Overview tab and reference {Company}'s business context plus the custom-object data this skill just created.

---

## Adding a new vertical seed

If you ran with `--industry other` and want to contribute the synthesized template back, the skill writes a draft to `templates/<your-industry>.md` at the end of the run. Review the draft, edit as needed, and commit. The next admin in your industry skips the synthesis step.

A seed should contain:

| Section | What it specifies |
|---|---|
| **Business archetype** | One-sentence description of the vertical's typical customer + technician work |
| **Recommended custom objects** | 2-4 objects with field lists. Include why each matters (compliance, SLA, asset history). |
| **Standard objects + fields to query** | Which standard fields the flow's Get-record elements should pull (e.g., `ServiceAppointment.ArrivalWindowStartTime`, `Contact.Email`) |
| **Prompt template section structure** | The 3-5 sections the brief should contain (e.g., HVAC = Mission and contact / Customer and SLA / Site access and certifications / Equipment and refrigerant context) |
| **Rules** | Vertical-specific rules (e.g., HVAC = "if last refrigerant service was >12 months ago, call it out") |
| **Cadence example** | Tone-anchoring example paragraph using the section structure |
| **Test data sample** | Realistic values for the test WO + seed records the skill creates in Step 8 |

See `templates/hvac.md` as the canonical example.

---

## Idempotency

Re-running this skill against the same org with the same `--customized-template-name`:

- Re-fetches the website and re-prompts for description (cheap; admins re-confirm).
- Re-audits org schema; new customs may have appeared since last run.
- Skips object creation if Step 4 finds the customs already exist.
- Re-deploys the flow as a new version (Salesforce treats identical metadata as no-op).
- Re-deploys the prompt template (same; identical metadata is a no-op).
- Creates a **new** test WO + SA every run.

For a second vertical in the same org, pass a different `--industry` and `--customized-template-name`. The skill produces a parallel pipeline (objects + flow + permset + template + test WO) without touching the first.

---

## Related afv-library Skills

- `setting-up-pre-work-brief` — required prerequisite. Runs the base setup that this skill builds on.
- `generating-flow` — useful when the from-scratch flow needs deeper edits than this skill performs (e.g., complex Loops over collections, Decision elements). Open the deployed flow in Flow Builder for visual review.
- `generating-permission-set` — for orgs that already have a permission set pattern to extend rather than create anew.

---

## References

- Pre-Work Brief setup: `https://help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief.htm`
- Pre-Work Brief data model: `https://help.salesforce.com/s/articleView?id=service.mfs_einstein_pre_work_brief_data.htm`
- Prompt Builder: `https://help.salesforce.com/s/articleView?id=ai.prompt_builder_about.htm`
- Flow Reference (PromptFlow processType): `https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_visual_workflow.htm`

---

## Known Limitations

- Programmatic activation of `GenAiPromptTemplate` is not exposed in the API today. Step 6's deeplink is the supported path until Salesforce ships an Activate REST endpoint. The skill follows the same one-click pattern as `setting-up-pre-work-brief` for consistency.
- Flows with multi-record record lookups (`getFirstRecordOnly=false`) require a Loop element to reference individual records in the Output.Prompt assignment; the from-scratch pattern in Step 5 uses `getFirstRecordOnly=true` to keep the demo simple. For verticals where a Work Order has multiple Refrigerant Logs / Compliance Checks / etc., the seed should specify a Loop pattern.
- `WebFetch` results depend on the company's homepage being public and not paywalled or JS-only. Pages rendered entirely by client-side JS may return little usable content; in that case fall back to admin description only.
- `AssignedResource` create may fail in orgs that require a Service Territory on the Service Appointment. Step 8 resolves Service Territory from the chosen Service Resource's `ServiceTerritoryMember` and includes it on create. If the resource has no territory membership, ask the admin to pick a different resource or assign a territory in Setup.
- `Asset.ProductDescription` is read-only for non-admin profiles in some org configurations (verified on `afvuser` 2026-05-19). Seeds should write descriptive text to `Asset.Description` instead.
