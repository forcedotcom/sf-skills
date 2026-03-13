---
name: salesforce-flexipage
description: Generate valid, deployable Salesforce Lightning Page (FlexiPage) metadata XML. Always use this skill when working with .flexipage-meta.xml files. Trigger when users mention Lightning pages, creating pages, adding components to pages, or page customization. Always use this skill for any FlexiPage-related work, even if they just mention "page" in the context of Salesforce.
---

# CONTEXT

## When to Use This Skill

Use this skill when you need to:
- Edit ANY `*.flexipage-meta.xml` file
- Create new Lightning Pages (FlexiPages) for records, apps, or home pages
- Edit existing pages by adding or changing components
- Troubleshoot FlexiPage deployment errors

## Goal

Generate valid, deployable FlexiPage metadata XML using CLI bootstrapping, with incremental enhancement and deployment. Ensure all generated XML follows Salesforce metadata conventions and passes deployment validation.

## Overview

Generate Lightning Pages (RecordPage, AppPage, HomePage) using CLI bootstrapping for component discovery and configuration.

**Terminology:** Lightning Pages are the marketing/UX name for FlexiPage metadata. Users may refer to them simply as "pages", "Lightning pages", or "FlexiPages". The metadata type is `FlexiPage` and files use the `.flexipage-meta.xml` extension.

---

# CRITICAL FOUNDATION (Read First!)

## Critical XML Rules

### 1. Property Value Encoding (MOST COMMON ERROR)

**Any property value with HTML/XML characters MUST be manually encoded in the following order** (wrong order causes double-encoding corruption):

```
1. & → &amp;   (FIRST! Encode this before others)
2. < → &lt;
3. > → &gt;
4. " → &quot;
5. ' → &apos;
```

**Wrong:**
```xml
<value><b>Important</b> text</value>
```

**Correct:**
```xml
<value>&lt;b&gt;Important&lt;/b&gt; text</value>
```

**Check your XML:** Search for `<value>` tags - they should never contain raw `<` or `>` characters.

### 2. Field References

**ALWAYS:** `Record.{FieldApiName}`
**NEVER:** `{ObjectName}.{FieldApiName}`

```xml
<!-- Correct -->
<fieldItem>Record.Name</fieldItem>

<!-- Wrong -->
<fieldItem>Account.Name</fieldItem>
```

### 3. Region vs Facet Types

**Template Regions** (header, main, sidebar):
```xml
<name>header</name>
<type>Region</type>
```

**Component Facets** (internal slots like fieldSection columns):
```xml
<name>Facet-12345</name>
<type>Facet</type>
```

**Rule:** If it's a template region name → `Region`. If it's a component slot → `Facet`.

### 4. fieldInstance Structure

Ensure every fieldInstance includes:
```xml
<itemInstances>
   <fieldInstance>
      <fieldInstanceProperties>
         <name>uiBehavior</name>
         <value>none</value> <!-- none|readonly|required -->
      </fieldInstanceProperties>
      <fieldItem>Record.FieldName__c</fieldItem>
      <identifier>RecordFieldName_cField</identifier>
   </fieldInstance>
</itemInstances>
```

**Rules:**
- Place each fieldInstance in its own `<itemInstances>` wrapper
- Always include `fieldInstanceProperties` with `uiBehavior`
- Always use `Record.{Field}` format

---

## Component-Specific Rules

**REQUIRED READING:** Before working with ANY component, you MUST read the relevant documentation files. This is NOT optional.

### Mandatory Documentation by Component Type

**Container Components** (tabs, accordions, field sections):
- **MUST READ:** `examples/container-facets-example.xml`
- This shows the correct facet structure that is required for all container components
- Read this BEFORE generating any container component XML

**Related Lists** (`lst:dynamicRelatedList`):
- **MUST READ:** `docs/components/lst-dynamicRelatedList.md`
- Contains critical rules for `parentFieldApiName`, `relatedListApiName`, and field configuration
- Inform the user you've read this file (the file itself requires this)

**Other Component Documentation:**
- `record_flexipage-dynamicHighlights.md` - RecordPage header / summary (MUST read when working with highlights)
- `flexipage-fieldSection.md` - Field display columns (MUST read when working with field sections)
- `flexipage-richText.md` - Rich text content (MUST read when working with rich text)

**General Rule:** For ANY component listed above, you MUST read its documentation file BEFORE generating XML. For components without specific documentation, apply the general Critical XML Rules.

---

## Component Selection Guidelines

When choosing components, prefer the following options for better performance and flexibility:

1. **Related Lists:** ALWAYS use `lst:dynamicRelatedList` for related lists. Do NOT use `force:relatedListQuickLink` or `force:relatedListSingleContainer`. The `lst:dynamicRelatedList` component is more performant and offers more FlexiPage configuration options. When using this component, you MUST read `docs/components/lst-dynamicRelatedList.md` before proceeding.

2. **Field Display:** Prefer field sections with specific fields over `force:detailPanel`. Field sections provide more versatility and control over layout and field behavior.

---

# MAIN WORKFLOWS

## Decision Tree: New Page or Existing Page?

**Does the FlexiPage file already exist?**

- **NO** → Use "Creating New Pages" workflow below (bootstrap first, then add components)
- **YES** → Skip to "Adding/Editing Components" workflow (no bootstrap needed)

---

## Creating New Pages

**Use this workflow when the `.flexipage-meta.xml` file does NOT exist yet.**

### Step 1: Bootstrap with CLI

```bash
sf template generate flexipage \
  --name <PageName> \
  --template <RecordPage|AppPage|HomePage> \
  --sobject <SObject> \
  --primary-field <Field1> \
  --secondary-fields <Field2,Field3> \
  --detail-fields <Field4,Field5,Field6,Field7> \
  --output-dir force-app/main/default/flexipages
```

**Template-specific requirements:**
- **RecordPage**: Requires `--sobject` (e.g., Account, Custom_Object__c)
- **RecordPage**: Requires `--primary-field` and `--secondary-fields` for dynamic highlights, `--detail-fields` for full record details. Use the most important identifying field as primary, e.g. Name. Use the secondary fields (max 12, recommended 4-6) to show a summary of the record. Use detail fields to show the full details of the record.
- **AppPage**: No additional requirements
- **HomePage**: No additional requirements

**Note:** If the `sf template generate flexipage` command fails, recommend users upgrade to the latest version of the Salesforce CLI:
```bash
npm install -g @salesforce/cli@latest
```

**What you get:**
- Valid FlexiPage XML with correct structure
- Pre-configured regions and basic components
- Proper field references and facet structure
- Ready to deploy as-is or enhance further

### Step 2: Deploy Base Page

```bash
sf project deploy start --source-dir force-app/main/default/flexipages
```

**Deploy early, deploy often.** Start with the bootstrapped page, validate it works, then enhance.

### Step 3: Add More Components (if needed)

If the user wants to add additional components beyond what the CLI generated, proceed to the "Adding/Editing Components" workflow below. The process is identical whether you just bootstrapped a new page or are working with an existing page.

---

## Adding/Editing Components

**Use this workflow when:**
- The FlexiPage file already exists, OR
- You've just bootstrapped a new page and need to add more components

### Workflow Steps

1. **Read the FlexiPage file** using native file I/O
2. **Parse XML** to extract:
   - Existing component identifiers
   - Available regions (parse from file, don't assume names)
   - Existing facets
3. **Select component** based on the user's request
4. **READ REQUIRED DOCUMENTATION** - See "Component-Specific Rules" section and read ALL relevant documentation files for your component type (this is MANDATORY, not optional)
5. **Generate component XML** using only known, valid properties (apply all rules from "Critical XML Rules" section AND component-specific documentation)
6. **Insert** into appropriate region
7. **Write** modified XML back to file
8. **Deploy**: `sf project deploy start --source-dir force-app/...`

---

# IMPLEMENTATION DETAILS

## Container Components with Facets

When generating tabs, accordions, or field sections, always create corresponding facet regions. Components like these require facets to define content areas.

**Critical**: Facet regions are siblings of template regions at the same level, not nested inside them.

**MANDATORY**: Before generating ANY container component, you MUST read [examples/container-facets-example.xml](examples/container-facets-example.xml). This file shows the exact structure required for container components with facets. Reading this file is NOT optional.

---

## Generating Unique Identifiers

**Algorithm**:
```
1. Extract all existing <identifier> values from XML
2. Generate base name: {componentType}_{context}
   Examples: "relatedList_contacts", "richText_header", "tabs_main"
3. Find first available number:
   - Try "{base}_1"
   - If exists, try "{base}_2", "{base}_3", etc.
   - Use first available
```

**Examples**:
- First contacts related list: `relatedList_contacts_1`
- Second contacts related list: `relatedList_contacts_2`
- Rich text in header: `richText_header_1`
- Field section: `fieldSection_details_1`

**Facet Naming - Two Patterns**:

1. **Named facets** (for major content areas):
   - `detailTabContent` (detail tab content)
   - `maintabs` (main tab container)
   - `sidebartabs` (sidebar tab container)
   - Use when facet represents meaningful content area

2. **UUID facets** (for internal structure):
   - Format: `Facet-{8hex}-{4hex}-{4hex}-{4hex}-{12hex}`
   - Example: `Facet-66d5a4b3-bf14-4665-ba75-1ceaa71b2cde`
   - Use for field section columns, nested containers, anonymous slots

---

## Region Selection

Always parse regions from the file - never hardcode region names. Templates vary:
- `flexipage:recordHomeTemplateDesktop` → `header`, `main`, `sidebar`
- `runtime_service_fieldservice:...` → `header`, `main`, `footer`
- Others may have different region names

Place new components at the end of the target region (after last `<itemInstances>`)

**Insertion pattern**:
```xml
<flexiPageRegions>
   <name>main</name>  <!-- or whatever region name exists -->
   <type>Region</type>
   <itemInstances><!-- Existing component 1 --></itemInstances>
   <itemInstances><!-- Existing component 2 --></itemInstances>
   <itemInstances>
      <!-- INSERT NEW COMPONENT HERE -->
   </itemInstances>
</flexiPageRegions>
```

---

# QUALITY & DEPLOYMENT

## Incremental Development Pattern

**Philosophy:** Deploy small, working increments. Don't build entire complex page at once.

**Process:**
1. **For new pages: CLI bootstrap** → Deploy base page
2. **Add one component** → Deploy
3. **Add another component** → Deploy
4. **Repeat** until complete

**Benefits:**
- Isolated errors (know exactly what broke)
- Faster debugging
- Build confidence with each success
- Get user feedback early

**Anti-pattern:** Building entire complex page → one giant error cascade.

---

## Validation Checklist

Before deploying:
- [ ] If creating new page: Used CLI to bootstrap (don't start from scratch)
- [ ] All field references use `Record.{Field}` format
- [ ] Each fieldInstance has `fieldInstanceProperties` with `uiBehavior`
- [ ] Each fieldInstance in own `<itemInstances>` wrapper
- [ ] Template regions use `<type>Region</type>`
- [ ] Component facets use `<type>Facet</type>`
- [ ] Component-specific docs have been read for each component and all rules followed
- [ ] Property values with HTML/XML are manually encoded
- [ ] No `<mode>` tags in regions
- [ ] No `__c` suffix in page names
- [ ] Each Facet referenced by exactly one component property

---

## Common Deployment Errors

See [docs/common-deployment-errors.md](docs/common-deployment-errors.md) for detailed error patterns, causes, and fixes.

---

# REFERENCE

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

## Output

A valid `.flexipage-meta.xml` file containing properly structured FlexiPage XML with correct region types, field references, component identifiers, and encoded property values
