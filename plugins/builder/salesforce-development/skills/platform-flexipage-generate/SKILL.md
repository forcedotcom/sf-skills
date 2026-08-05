---
name: platform-flexipage-generate
description: "Use this skill when users need to create, generate, modify, or validate Salesforce Lightning pages (FlexiPages). Trigger when users mention RecordPage, AppPage, HomePage, Lightning pages, page layouts, adding components to pages, or page customization. Also use when users say things like 'create a Lightning page', 'add a component to a page', 'customize the record page', 'generate a FlexiPage', or when they're working with FlexiPage XML files and need help with components, regions, or deployment errors. Always use this skill for any FlexiPage-related work, even if they just mention 'page' in the context of Salesforce. DO NOT TRIGGER when users ask about Visualforce pages, Aura components without FlexiPage context, page layout assignments in the UI, or Lightning Web Component development that does not involve placing components on a FlexiPage."
allowed-tools: Bash Read Write
metadata:
  version: "1.1"
  minApiVersion: "51.0"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.126.4"
  mcpTools:
    metadata-experts:
      tools: ["execute_metadata_action"]
      semver: ">=1.0.0"
---

## When to Use This Skill

Use this skill when you need to:
- Create Lightning pages (RecordPage, AppPage, HomePage)
- Generate FlexiPage metadata XML
- Add components to existing FlexiPages
- Troubleshoot FlexiPage deployment errors
- Understand FlexiPage structure and component configuration
- Work with page layouts or Lightning page customization
- Edit or update ANY *.flexipage-meta.xml file

## Specification

## Overview

**CRITICAL: When creating NEW FlexiPages, you MUST ALWAYS start with the CLI template command.** Never create FlexiPage XML from scratch - the CLI provides valid structure, proper regions, and correct component configuration that prevents deployment errors.

Generate Lightning pages (RecordPage, AppPage, HomePage) using CLI bootstrapping for component discovery and configuration.

---

## Quick Start Workflow

### Step 1: Bootstrap with CLI

**MANDATORY FOR NEW PAGES: This step is NOT optional.** Always use the CLI template command when creating a new FlexiPage. The CLI generates valid XML structure, proper regions, and correct metadata that prevents common deployment errors. Only skip this step if you're editing an existing FlexiPage file.

**`<packageDirectory>`** = the `path` value from `sfdx-project.json` → `packageDirectories[0]` (e.g., `force-app`). Read it from the project file before running commands.

```bash
sf template generate flexipage \
  --name <PageName> \
  --template <RecordPage|AppPage|HomePage> \
  --sobject <SObject> \
  --primary-field <Field1> \
  --secondary-fields <Field2,Field3> \
  --detail-fields <Field4,Field5,Field6,Field7> \
  --output-dir <packageDirectory>/main/default/flexipages
```

**CRITICAL:** If the `sf template generate flexipage` command fails, **STOP**.

1. Install the templates plugin:
   ```bash
   sf plugins install templates
   ```
2. Retry the `sf template generate flexipage` command
3. Verify the FlexiPage XML file was created

Do NOT continue to Step 2 until the template command succeeds. The generated XML is required for the entire workflow.

#### **Template-specific requirements**

**RecordPage:**
- Requires `--sobject` (e.g., Account, Custom_Object__c)
- Requires field parameters:
  - `--primary-field`: Most important identifying field (e.g., Name)
  - `--secondary-fields`: Record summary (recommended 4-6, max 12)
  - `--detail-fields`: Full record details, including required fields (e.g., Name)

**AppPage:**
- No additional requirements

**HomePage:**
- No additional requirements

#### **Field Selection Rules**
- **Validate fields exist**: Use MCP tools or describe commands to discover available fields for the object before specifying them in the command
- **Prefer compound fields**: Use `Name` (not `FirstName`/`LastName`), `BillingAddress` (not `BillingStreet`/`BillingCity`/`BillingState`), `MailingAddress`, etc. when available
- **Include required fields in detail-fields**: Always include object required fields (like `Name`) in the `--detail-fields` parameter, even if they're also used in `--primary-field` or `--secondary-fields`

#### **What you get**
- Valid FlexiPage XML with correct structure
- Pre-configured regions and basic components
- Proper field references and facet structure
- Ready to deploy as-is or enhance further

### Step 2: Deploy Base Page

Run a **dry-run** deployment to validate the page and dependencies (use the default package directory from `sfdx-project.json`):
```bash
sf project deploy start --dry-run -d "<packageDirectory>/main/default" --test-level NoTestRun --wait 10 --json
```

**Critical:** Fix any deployment errors before proceeding. The page must validate successfully.

### Step 3: Add Components Dynamically (if requested)

After the base page deploys successfully, if the user wants additional components, follow the **Adding Components Dynamically** workflow below. All component additions MUST go through the discovery and inference pipeline — never write component XML from memory alone.

---

## Critical XML Rules

**Read `references/xml_rules.md`** for all XML encoding rules, field reference format, region/facet types, fieldInstance structure, unique identifier requirements, and common deployment error resolutions.

**Key rules (quick reminder):**
- Encode HTML in `<value>` tags: `&` first, then `<`, `>`, `"`, `'`
- Field references: `Record.{FieldApiName}` (never `Object.Field`)
- Every `<identifier>` and region `<name>` must be unique across the file
- Multiple components in same facet → combine in ONE region with multiple `<itemInstances>`

---

### Identifiers, Regions, and Containers

**Read `references/identifiers_and_regions.md`** for the identifier generation algorithm, facet naming patterns (named vs UUID), region selection rules, and container component facet structure.

---

## Component-Specific Tips

### dynamicHighlights (RecordPage Header)
**Location:** `header` region only. See `references/record_flexipage_dynamicHighlights.md` for full structure.
CLI generates Facets automatically from `--primary-field` and `--secondary-fields`.

### fieldSection
**Use for:** Displaying fields in columns. Three-level nesting: Region → Column Facets → Field Facets.
See `references/flexipage_fieldSection.md` for full structure and XML example.
**Critical:** The `columns` property value is a Facet name, not a number.

### richText
See `references/flexipage_richText.md` for encoding rules and XML structure.
Identifier: `flexipage_richText` or `flexipage_richText_{N}`

---
## Required Metadata Structure

```xml
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
   <flexiPageRegions>
      <!-- Regions and components here -->
   </flexiPageRegions>
   <masterLabel>Page Label</masterLabel>
   <template>
      <name>flexipage:recordHomeTemplateDesktop</name>
   </template>
   <type>RecordPage</type>
   <sobjectType>Object__c</sobjectType> <!-- RecordPage only -->
</FlexiPage>
```

**Page Types:**
- `RecordPage` - requires `<sobjectType>`
- `AppPage` - no sobjectType
- `HomePage` - no sobjectType

---

## Validation Checklist

### Structure (new pages)
- [ ] Used CLI to bootstrap — never create FlexiPage XML from scratch

### Identifiers & Regions
- [ ] All `<identifier>` values unique across entire file
- [ ] All region/facet `<name>` values unique across entire file
- [ ] Multiple components in same facet combined in ONE region with multiple `<itemInstances>`

### Field Instances
- [ ] All field references use `Record.{Field}` format
- [ ] Each fieldInstance has `fieldInstanceProperties` with `uiBehavior`
- [ ] Each fieldInstance in its own `<itemInstances>` wrapper

### Types & Encoding
- [ ] Template regions use `<type>Region</type>`; component facets use `<type>Facet</type>`
- [ ] Property values with HTML/XML are entity-encoded
- [ ] No unnecessary `<mode>` tags (only where component patterns require them)
- [ ] No `__c` suffix in page names
- [ ] Each Facet referenced by exactly one component property

---

## Quick Reference: CLI Command

**Read `references/cli_commands.md`** for full CLI examples (RecordPage, AppPage, HomePage) and available options.

---

## Adding Components Dynamically

> **MANDATORY WORKFLOW:** ALL component additions to a FlexiPage MUST follow this workflow. Do not write component XML from memory or skip discovery. This applies to standard OOTB components, custom LWC components, and any other component type.

### Overview

When the user requests components (e.g., "add a related list of contacts and a report"), follow this pipeline:

```text
1. Parse Intent → identify ALL requested components
2. Discover ALL → batch components through 3-tier discovery
3. Infer Properties → run 3-step inference for EACH discovered component
4. Generate XML → produce valid XML for all components together
5. Validate → check identifiers, regions, property completeness
```

**Key rule:** Discover ALL components as a batch first (one scan, one MCP call), THEN infer properties for each. Do not invoke discovery steps per-component or interleave discovery and inference.

### Step 1: Parse User Intent

Extract every component request from the user's utterance. Examples:
- "Create Account page with a report and related contacts" → 2 components: report, related list
- "Add activities, chatter, and a DRL of Cases" → 3 components: activities, chatter, dynamic related list

### Step 2: 3-Tier Component Discovery

Complete each tier for ALL components before moving to the next tier — do NOT run Tier 1→2→3 per component:

| Tier | Source | When | Calls |
|------|--------|------|-------|
| **1** | Local workspace scan | Always first — run for ALL components | 0 (local only) |
| **2** | `discoverUiComponents` MCP action | Single call for all components unresolved after Tier 1 | 1 |
| **3** | Generate new LWC bundle | Only for components still unresolved after Tier 2 + user confirms | 0 |

After Tier 1 completes for all components, collect only the unresolved ones and pass them to Tier 2 in a single MCP call. Only components still unresolved after Tier 2 proceed to Tier 3.

See **Local Workspace Scanner** and **MCP Action Integration** sections below for details.

### Step 3: Property Inference (per component)

For EACH discovered component, infer properties using the 3-step strategy:

1. **Fetch schema or read source** — For Tier 2 (org) components, call `getUiComponentSchemas`; for Tier 1 (local), extract `@api` props from source
2. **Apply component instructions** — If `references/<name>.md` exists, read and follow its inference rules
3. **Resolve remaining** — Smart defaults → LLM inference → user prompts (last resort)

See **Hybrid Property Inference Strategy** below for full details.

### Step 4: Generate XML

What you CANNOT do:
- Modify top level structure in the XML file
- Add any components from memory which is not resolved from 3-Tier Component Discovery
- Make any enhancements

**Read `references/xml_rules.md` before writing any XML.** Follow all element naming and structure rules defined there. 

Produce `<itemInstances>` XML for all resolved components:
- Use `<componentInstanceProperties>` for every property (NOT `<properties>`)
- Assign unique identifiers across the full set (see references/identifiers_and_regions.md)
- Insert into appropriate regions (header, main, sidebar, or facets)
- Follow each component's XML structure from its instructions file or schema

### Step 5: Validate

Check the complete FlexiPage for:
- Identifier uniqueness (no duplicates across entire file)
- Region validity (components in correct regions)
- Property completeness (all required properties populated)
- XML encoding (HTML values entity-encoded)
- Element name correctness (see references/xml_rules.md §6)

Deploy with dry-run (use default package directory from `sfdx-project.json`):
```bash
sf project deploy start --dry-run -d "<packageDirectory>/main/default" --test-level NoTestRun --wait 10 --json
```

---

## MCP Action Integration

**Read `references/mcp_action_examples.md`** for full input/output examples and parameter tables.

Two MCP actions via `execute_metadata_action`:

| Action | Purpose | When |
|--------|---------|------|
| `DISCOVER_UI_COMPONENTS` | Find components for a page type | Tier 2 discovery — single call for all unresolved components |
| `GET_UI_COMPONENT_SCHEMAS` | Get property schemas | Property inference Step 1 (Tier 2 org components only) |

**Key conventions:**
- Component definition format: `namespace/blockName` (forward-slash) in MCP calls, `namespace:blockName` (colon) in XML
- `pageContext` with `entityName` is required for RECORD_PAGE
- `getUiComponentSchemas` supports partial failures — check each component's `success` boolean

---

## Local Workspace Scanner

Scans the local SFDX project for custom LWC components before making any MCP calls (Tier 1 discovery).

### Algorithm

Run the scanner for each component query (local scan — no network calls):

```bash
scripts/scan-lwc-components.sh "<query>" [packageDirectory]
```

The script scans `<packageDirectory>/**/lwc/*/`, tokenizes camelCase component names, scores them against user intent keywords, and returns a JSON array of matches with confidence tiers:

- **High confidence (≥70%):** auto-select, confirm with user
- **Medium confidence (40-69%):** present ranked list for user selection
- **Low confidence (<40%):** skip, proceed to Tier 2

Run Tier 1 for ALL components before moving any to Tier 2. Collect all unresolved components from Tier 1, then pass them to Tier 2 in a single MCP call.

### Disambiguation

For medium-confidence matches (40-69%) or multiple high-confidence matches:
1. Read each candidate's `.js-meta.xml` for `<description>` and `<targetConfigs>`
2. Present ranked list to user with component name + description
3. User selects or says "none of these" (→ proceed to Tier 2)

### When to Skip

Skip local scan when:
- User explicitly mentions an org-level component ("use the standard report component")
- User intent clearly maps to a known standard component (DRL, richText, etc.)
- No `<packageDirectory>` directory exists in the workspace

---

## Hybrid Property Inference Strategy

For EACH discovered component, populate its properties using this 3-step strategy in order:

### Step 1: Fetch Latest Schema (conditional)

Call `getUiComponentSchemas` only when the component does **not** exist on the local machine (i.e., Tier 2 org-discovered components). For local components (Tier 1), extract `@api` properties directly from the source code instead.

**When to call:**
- Tier 2 (org discovery): Always — the schema is the only source of property info
- Tier 1 (local): Skip — read `@api` properties from the component's `.js` source file
- Tier 3 (generated): Skip — you just created the source, so properties are already known

### Step 2: Apply Component Instructions (if present)

Run `scripts/resolve-component-instructions.sh <namespace:component>` — it returns the instructions file path if it exists, or empty string.

Examples:
- `record_flexipage:dynamicHighlights` → `references/record_flexipage_dynamicHighlights.md`
- `flexipage:fieldSection` → `references/flexipage_fieldSection.md`
- `c:expenseTracker` → (empty — no file)

If a file is returned: read and follow its inference rules, XML patterns, and defaults.
If empty: skip directly to Step 3.

Instructions files augment the schema — they provide *how* to derive values from user intent. Any properties in the schema not covered by the instructions file are resolved in Step 3.

### Step 3: Resolve Remaining Properties

For any properties not yet resolved, apply in this priority order:

**3a. Smart Default Heuristics:**

| Property Pattern | Default Value |
|-----------------|---------------|
| `recordId` | `{!recordId}` |
| `objectApiName` / `sObjectName` | Page's `<sobjectType>` value |
| `show*` / `visible*` / `display*` | `true` |
| `hide*` / `hidden*` / `disabled*` | `false` |
| Boolean without prefix | `false` |
| Schema specifies `"default"` | Use schema default |

**3b. LLM Inference:**
Use the component schema + user intent + page context to infer reasonable values. Example: user says "report showing top opportunities" → infer `reportName` should reference an opportunities report.

**3c. User Prompts (last resort):**
Only prompt the user for critical required properties that cannot be inferred. If user says "skip", omit the component entirely.

### Tier-Specific Behavior

| Tier | Extra Step | Schema Call | Instructions |
|------|-----------|-------------|--------------|
| Tier 1 (local) | Extract `@api` props from source | No (use source) | If exists |
| Tier 2 (org) | — | Yes | If exists |
| Tier 3 (generated) | Extract `@api` from just-generated source | No (just created) | No |

---

## New LWC Generation (Tier 3)

When no component is found locally (Tier 1) or in the org (Tier 2), offer to generate a new LWC.

### Trigger Conditions

- Tier 1 and Tier 2 both miss or user rejected all candidates
- User has not explicitly said "skip" or "don't create"

### Confirmation

Always confirm before creating. Explain: component name. If user declines: skip, continue with other components.

### Post-Generation

After creating the LWC bundle:
1. Treat as a Tier 1 local component immediately
2. Extract `@api` properties from the generated source
3. Apply smart defaults for `recordId` and `objectApiName`
4. Generate FlexiPage XML with `c:{componentName}` as the componentName

### Naming Convention

- Derive from user intent: "customer health score" → `customerHealthScore`
- camelCase, no hyphens, no underscores in the JS class name
- Folder name matches class name (lowercase first letter): `customerHealthScore/`

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/xml_rules.md` | Before writing or editing any FlexiPage XML — encoding, field refs, identifiers, deployment errors |
| `references/identifiers_and_regions.md` | When adding components — identifier algorithm, facet naming, region selection, container pattern |
| `references/cli_commands.md` | When bootstrapping new pages — full CLI examples for RecordPage, AppPage, HomePage |
| `references/mcp_action_examples.md` | When calling MCP actions — full input/output JSON for discoverUiComponents and getUiComponentSchemas |
| `references/flexipage_fieldSection.md` | When adding a Field Section with columns |
| `references/record_flexipage_dynamicHighlights.md` | When adding a Dynamic Highlights panel |
| `references/flexipage_richText.md` | When adding a Rich Text component |
| `scripts/scan-lwc-components.sh` | Tier 1 local workspace scan — tokenizes and scores LWC component names against user query |
| `scripts/resolve-component-instructions.sh` | Property inference Step 2 — resolves component definition to instructions file path |

**To add a new component pattern:** Create `references/<namespace>_<componentName>.md` following the structure in existing files. The skill automatically checks for the file during Step 2 of property inference.

---

## Validation Rules for Dynamic Components

After generating XML for dynamically added components, verify ALL of the following before deployment:

### Identifier Uniqueness
- Extract ALL `<identifier>` values from the entire FlexiPage file
- Confirm zero duplicates
- If conflict: auto-increment suffix (`_2`, `_3`, etc.)

### Region Validity
- Components placed in correct regions for their type:
  - `record_flexipage:dynamicHighlights` → `header` only
  - `flexipage:fieldSection` → `main` or tab facets
  - `flexipage:richText` → any region

### Property Completeness
- All properties marked required in schema have values
- All values match expected types (String, Boolean, valueList, Integer)
- No raw HTML in `<value>` tags (must be entity-encoded)

### Structural Integrity
- Every Facet referenced by a component property exists as a `<flexiPageRegions>` block
- No orphan Facets (every Facet is referenced by exactly one component)
- Multiple components in same region use ONE `<flexiPageRegions>` block with multiple `<itemInstances>`

### Cross-Component Consistency
- For multi-component additions: identifiers are unique across ALL new components
- Facet UUIDs don't collide between components
- Components that require singleton placement (dynamicHighlights, recordDetailPanelMobile) are not duplicated
