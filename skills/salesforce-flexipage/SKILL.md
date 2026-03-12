---
name: salesforce-flexipage
description: Use this skill when users need to create, generate, modify, or validate Salesforce Lightning pages (FlexiPages). Trigger when users mention RecordPage, AppPage, HomePage, Lightning pages, page layouts, adding components to pages, or page customization. Also use when users say things like "create a Lightning page", "add a component to a page", "customize the record page", "generate a FlexiPage", or when they're working with FlexiPage XML files and need help with components, regions, or deployment errors. Always use this skill for any FlexiPage-related work, even if they just mention "page" in the context of Salesforce.
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

# FlexiPage Generation Guide

## Overview

Generate Lightning pages (RecordPage, AppPage, HomePage) using CLI bootstrapping for component discovery and configuration.

---

## Quick Start Workflow

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

### Step 3: Update and Redeploy

Modify the generated XML, adding components discovered via MCP. Deploy incrementally.

**Note:** Warn users to use caution with updates beyond this step when using this command.

---

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

Every fieldInstance requires:
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
- Each fieldInstance in its own `<itemInstances>` wrapper
- Must have `fieldInstanceProperties` with `uiBehavior`
- Use `Record.{Field}` format

---

## Common Deployment Errors

### "Invalid field reference"
**Cause:** Used `ObjectName.Field` instead of `Record.Field`  
**Fix:** Change to `Record.{FieldApiName}`

### "Element fieldInstance is duplicated"
**Cause:** Multiple fieldInstances in one itemInstances  
**Fix:** Each fieldInstance needs its own `<itemInstances>` wrapper

### "Missing fieldInstanceProperties"
**Cause:** No uiBehavior specified  
**Fix:** Add `fieldInstanceProperties` with `uiBehavior`

### "Unused Facet"
**Cause:** Facet defined but not referenced by any component  
**Fix:** Remove Facet or reference it in a component property

### "XML parsing error"
**Cause:** Unencoded HTML/XML in property values  
**Fix:** Manually encode `<`, `>`, `&`, `"`, `'` in all `<value>` tags

### "Cannot create component with namespace"
**Cause:** Invalid page name (don't use `__c` suffix in page names)  
**Fix:** Use "Volunteer_Record_Page" not "Volunteer__c_Record_Page"

### "Region specifies mode that parent doesn't support"
**Cause:** Added `<mode>` tag to region  
**Fix:** Remove `<mode>` tags - they're not needed for standard regions

---

## Incremental Development Pattern

**Philosophy:** Deploy small, working increments. Don't build entire complex page at once.

**Process:**
1. **CLI bootstrap** → Deploy base page
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

## Adding Components to Existing FlexiPages

### Workflow

When user provides an existing FlexiPage file path:

1. **Read the file** using native file I/O
2. **Parse XML** to extract:
   - Existing component identifiers
   - Available regions (parse from file, don't assume names)
   - Existing facets
3. **Generate component XML** (apply all rules from "Critical XML Rules" section)
4. **Insert** into appropriate region
5. **Write** modified XML back to file
6. **Deploy**: `sf project deploy start --source-dir force-app/...`

---

### Generating Unique Identifiers

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

### Region Selection

**Parse regions from file** - don't hardcode names. Templates vary:
- `flexipage:recordHomeTemplateDesktop` → `header`, `main`, `sidebar`
- `runtime_service_fieldservice:...` → `header`, `main`, `footer`
- Others may have different region names

**Default placement**: End of target region (after last `<itemInstances>`)

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

### Container Components with Facets

Components like tabs, accordions, field sections require facets.

**Pattern**:
```xml
<!-- 1. Component in region -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
         <componentName>flexipage:tabset2</componentName>
         <identifier>tabs_main_1</identifier>
         <componentInstanceProperties>
            <name>tabs</name>
            <value>tab1_content</value>
            <value>tab2_content</value>
         </componentInstanceProperties>
      </componentInstance>
   </itemInstances>
   <name>main</name>
   <type>Region</type>
</flexiPageRegions>

        <!-- 2. Facets (siblings of region, NOT nested inside) -->
<flexiPageRegions>
<itemInstances><!-- Tab 1 content --></itemInstances>
<name>tab1_content</name>
<type>Facet</type>
</flexiPageRegions>

<flexiPageRegions>
<itemInstances><!-- Tab 2 content --></itemInstances>
<name>tab2_content</name>
<type>Facet</type>
</flexiPageRegions>
```

**Critical**: Facet regions are siblings of template regions at the same level, not nested inside them.
---
## Component-Specific Tips
### dynamicHighlights (RecordPage Header)
**Location:** Must be in `header` region.
**Explicit Fields** (via CLI): Use the most important fields to show a summary of the record. The single primary field is used to identify the record, like a name. The secondary fields (max 12, recommended 6) are used as a summary of the record.
```bash
--primary-field Name
--secondary-fields Phone,Industry,AnnualRevenue
```
CLI generates Facets with field references automatically.
### fieldSection
**Use for:** Displaying fields in columns.
**Structure:** Three-level nesting:
1. Template Region (Region type)
2. Column Facets (Facet type)
3. Field Facets (Facet type)
   **Referenced in component property:**
```xml
<componentInstanceProperties>
   <name>columns</name>
   <value>Facet-{uuid}</value>
</componentInstanceProperties>
```

### rich Text component

Component name: flexipage:richText

Use for: Displaying HTML-formatted rich text content with support for text formatting, headings, lists, tables, images, links, forms, and multimedia elements. Preserves styling and layout. Escape all special characters in the default text.

Location: Can be used in any region on any page type (Home, Record, App, Community pages).


CLI generates the component directly without nested structures.

User: "Add a rich text component to force-app/.../Account_Record_Page.flexipage-meta.xml"

Structure: Single-level component (no facets):
1. Component instance (flexipage:richText) with direct properties

XML Structure Example:
```xml
<itemInstances>
   <componentInstance>
      <componentInstanceProperties>
         <name>decorate</name>
         <value>true</value>
      </componentInstanceProperties>
      <componentName>flexipage:richText</componentName>
      <identifier>flexipage_richText</identifier>
   </componentInstance>
</itemInstances>
```

Identifier Pattern: flexipage_richText or flexipage_richText_{sequence}

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

Before deploying:
- [ ] Used CLI to bootstrap (don't start from scratch)
- [ ] All field references use `Record.{Field}` format
- [ ] Each fieldInstance has `fieldInstanceProperties` with `uiBehavior`
- [ ] Each fieldInstance in own `<itemInstances>` wrapper
- [ ] Template regions use `<type>Region</type>`
- [ ] Component facets use `<type>Facet</type>`
- [ ] Property values with HTML/XML are manually encoded
- [ ] No `<mode>` tags in regions
- [ ] No `__c` suffix in page names
- [ ] Each Facet referenced by exactly one component property

---

## Quick Reference: CLI Command

```bash
# RecordPage with fields
sf template generate flexipage \
  --name Account_Custom_Page \
  --template RecordPage \
  --sobject Account \
  --primary-field Name \
  --secondary-fields Phone,Industry,AnnualRevenue \
  --detail-fields Street,City,State,Name,Phone,Email

# AppPage
sf template generate flexipage \
  --name Sales_Dashboard \
  --template AppPage \
  --label "Sales Dashboard"

# HomePage
sf template generate flexipage \
  --name Custom_Home \
  --template HomePage \
  --description "Custom home for sales team"
```

**All templates support:**
- `--output-dir` (default: current directory)
- `--api-version` (default: latest)
- `--label` (default: page name)
- `--description`
