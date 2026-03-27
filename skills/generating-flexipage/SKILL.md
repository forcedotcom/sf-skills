---
name: generating-flexipage
description: "Use this skill when users need to create, generate, modify, or validate Salesforce Lightning pages (FlexiPages). Trigger when users mention RecordPage, AppPage, HomePage, Lightning pages, page layouts, adding components to pages, or page customization. Also use when users say things like 'create a Lightning page', 'add a component to a page', 'customize the record page', 'generate a FlexiPage', or when they're working with FlexiPage XML files and need help with components, regions, or deployment errors. Always use this skill for any FlexiPage-related work, even if they just mention 'page' in the context of Salesforce."
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

**CRITICAL: When creating NEW FlexiPages, you MUST ALWAYS start with the CLI template command.** Never create FlexiPage XML from scratch - the CLI provides valid structure, proper regions, and correct component configuration that prevents deployment errors.

Generate Lightning pages (RecordPage, AppPage, HomePage) using CLI bootstrapping for component discovery and configuration.

---

## Quick Start Workflow

### Step 1: Bootstrap with CLI

**MANDATORY FOR NEW PAGES: This step is NOT optional.** Always use the CLI template command when creating a new FlexiPage. The CLI generates valid XML structure, proper regions, and correct metadata that prevents common deployment errors. Only skip this step if you're editing an existing FlexiPage file.

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

**Note:** If the `sf template generate flexipage` command fails, recommend users upgrade to the latest version of the Salesforce CLI:
```bash
npm install -g @salesforce/cli@latest
```

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

Run a **dry-run** deployment of the entire project to validate the page and dependencies:
```bash
sf project deploy start --dry-run -d "force-app/main/default" --test-level NoTestRun --wait 10 --json
```

**Critical:** Fix any deployment errors before proceeding. The page must validate successfully.

### Step 3: **STOP - No Further Modifications**

**MANDATORY: Stop after Step 2. Do not add components or edit the FlexiPage XML.**

This applies even if the user requested:
- Additional components
- Page customization
- Component configuration

What you CAN do:
- Suggest what components would be useful
- Explain what enhancements are possible
- Document what would need to be added manually

What you CANNOT do:
- Modify the XML file
- Add any components
- Make any enhancements

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

### 5. Unique Identifiers and Region Names (CRITICAL - PREVENTS DUPLICATE ERRORS)

**EVERY identifier and region/facet name MUST be unique across the entire FlexiPage file.**

**Critical Rules:**
- ❌ **NEVER create two `<flexiPageRegions>` blocks with the same `<name>`**
- ✅ **If multiple components belong to same facet, combine them in ONE region with multiple `<itemInstances>`**
- ❌ **NEVER reuse the same `<identifier>` value**
- ✅ **Always read entire file first and extract ALL existing identifiers and names**

**Wrong - This WILL FAIL with duplicate name error:**
```xml
<!-- First field section in detail tab -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
         <identifier>flexipage_property_details_fieldSection</identifier>
         ...
      </componentInstance>
   </itemInstances>
   <name>detailTabContent</name>  <!-- ❌ DUPLICATE NAME -->
   <type>Facet</type>
</flexiPageRegions>

<!-- Second field section in detail tab -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
         <identifier>flexipage_pricing_fieldSection</identifier>
         ...
      </componentInstance>
   </itemInstances>
   <name>detailTabContent</name>  <!-- ❌ DUPLICATE NAME - DEPLOYMENT FAILS -->
   <type>Facet</type>
</flexiPageRegions>
```

**Correct - Combine itemInstances in ONE region:**
```xml
<!-- Both field sections in same detail tab facet -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
         <identifier>flexipage_property_details_fieldSection</identifier>
         ...
      </componentInstance>
   </itemInstances>
   <itemInstances>
      <componentInstance>
         <identifier>flexipage_pricing_fieldSection</identifier>
         ...
      </componentInstance>
   </itemInstances>
   <name>detailTabContent</name>  <!-- ✅ ONE REGION, MULTIPLE COMPONENTS -->
   <type>Facet</type>
</flexiPageRegions>
```

**When to combine vs separate:**
- **Combine**: Components that logically belong to same tab/section (e.g., multiple field sections in detail tab)
- **Separate**: Components that belong to different tabs/sections (e.g., `detailTabContent` vs `relatedTabContent`)

---

## Common Deployment Errors

### "We couldn't retrieve or load the information on the field"
**Cause:** Invalid field API name - field doesn't exist on the object or has incorrect spelling
**Fix:** Use MCP tools or describe commands to discover valid fields, then update the field reference (see Field Selection Rules)

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

### Generating Unique Identifiers

**CRITICAL: Before generating ANY new identifier or facet name, follow the rules in section 5 of "Critical XML Rules" above.**

**Identifier Generation Algorithm**:
```
1. Extract ALL existing <identifier> AND <name> values from XML
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

**When adding components to existing files:**
- Check if target facet name already exists
- If exists: Add new `<itemInstances>` to that existing region (see section 5 above for details)
- If doesn't exist: Create new region with unique name

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
- [ ] **[NEW PAGES ONLY]** Used CLI to bootstrap - NEVER create FlexiPage XML from scratch
- [ ] **ALL identifiers are unique** - no duplicate `<identifier>` values anywhere in file
- [ ] **ALL region/facet names are unique** - no duplicate `<name>` values in `<flexiPageRegions>`
- [ ] **Multiple components in same facet are combined** - ONE region with multiple `<itemInstances>`, NOT separate regions with same name
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
