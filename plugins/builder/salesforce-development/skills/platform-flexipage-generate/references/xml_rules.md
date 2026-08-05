# Critical XML Rules & Deployment Errors

## Contents

0. [STOP — Read Before Writing ANY componentInstance](#stop--read-before-writing-any-componentinstance)
1. [Property Value Encoding](#1-property-value-encoding-most-common-error)
2. [Field References](#2-field-references)
3. [Region vs Facet Types](#3-region-vs-facet-types)
4. [itemInstances — ONE Child Per Wrapper](#4-iteminstances--one-child-per-wrapper-critical)
5. [Unique Identifiers and Region Names](#5-unique-identifiers-and-region-names-critical---prevents-duplicate-errors)
6. [Correct Element Names](#6-correct-element-names-critical--prevents-invalid-xml-errors)
7. [Common Deployment Errors](#common-deployment-errors)

---

## STOP — Read Before Writing ANY componentInstance

**The element name is `<componentInstanceProperties>`, NEVER `<properties>`.**

```xml
<!-- WRONG — WILL FAIL DEPLOYMENT -->
<componentInstance>
    <properties>
        <name>label</name>
        <value>Hello</value>
    </properties>
    <componentName>flexipage:fieldSection</componentName>
    <identifier>id1</identifier>
</componentInstance>

<!-- CORRECT — the ONLY valid element name -->
<componentInstance>
    <componentInstanceProperties>
        <name>label</name>
        <value>Hello</value>
    </componentInstanceProperties>
    <componentName>flexipage:fieldSection</componentName>
    <identifier>id1</identifier>
</componentInstance>
```

**There is no `<properties>` element in FlexiPage XML. It does not exist. Every time you write a property inside `<componentInstance>`, you MUST write `<componentInstanceProperties>`. If you find yourself typing `<properties>`, STOP and correct it to `<componentInstanceProperties>`.**

---

## 1. Property Value Encoding (MOST COMMON ERROR)

**Any property value with HTML/XML characters MUST be manually encoded in the following order** (wrong order causes double-encoding corruption):

```text
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

## 2. Field References

Use `Record.{FieldApiName}` — never `{ObjectName}.{FieldApiName}` (Salesforce resolves from Record, not object name).

```xml
<!-- Correct -->
<fieldItem>Record.Name</fieldItem>

<!-- Wrong -->
<fieldItem>Account.Name</fieldItem>
```

## 3. Region vs Facet Types

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

## 4. itemInstances — ONE Child Per Wrapper (CRITICAL)

**Each `<itemInstances>` can contain exactly ONE child element** — either one `<componentInstance>` OR one `<fieldInstance>`. Never put multiple children inside a single `<itemInstances>`.

```xml
<!-- WRONG — multiple componentInstance in one itemInstances -->
<itemInstances>
    <componentInstance>
        <componentName>flexipage:field</componentName>
        <identifier>field1</identifier>
    </componentInstance>
    <componentInstance>
        <componentName>flexipage:field</componentName>
        <identifier>field2</identifier>
    </componentInstance>
</itemInstances>

<!-- CORRECT — each componentInstance in its own itemInstances -->
<itemInstances>
    <componentInstance>
        <componentName>flexipage:field</componentName>
        <identifier>field1</identifier>
    </componentInstance>
</itemInstances>
<itemInstances>
    <componentInstance>
        <componentName>flexipage:field</componentName>
        <identifier>field2</identifier>
    </componentInstance>
</itemInstances>
```

### fieldInstance Structure

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

**Valid `uiBehavior` values (lowercase only):**

| Value | Meaning |
|-------|---------|
| `none` | Field respects standard editability settings (default) |
| `readonly` | Field is permanently locked on this page |
| `required` | Field must be filled out before saving on this page |

**Rules:**
- Each `<itemInstances>` gets exactly ONE child (`<componentInstance>` or `<fieldInstance>`)
- fieldInstance must have `fieldInstanceProperties` with `uiBehavior`
- Use `Record.{Field}` format
- There is NO `edit` value — use `none` for standard editable fields

## 5. Unique Identifiers and Region Names (CRITICAL - PREVENTS DUPLICATE ERRORS)

**EVERY identifier and region/facet name MUST be unique across the entire FlexiPage file.**

- **NEVER create two `<flexiPageRegions>` blocks with the same `<name>`**
- **If multiple components belong to same facet, combine them in ONE region with multiple `<itemInstances>`**
- **NEVER reuse the same `<identifier>` value**
- **Always read entire file first and extract ALL existing identifiers and names**
- **Element order inside `<flexiPageRegions>`**: `<itemInstances>` FIRST, then `<mode>` (if needed), then `<name>`, then `<type>` — NEVER put `<name>`/`<type>` before `<itemInstances>`

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
   <name>detailTabContent</name>  <!-- WRONG: DUPLICATE NAME -->
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
   <name>detailTabContent</name>  <!-- WRONG: DUPLICATE NAME - DEPLOYMENT FAILS -->
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
   <name>detailTabContent</name>  <!-- CORRECT: ONE REGION, MULTIPLE COMPONENTS -->
   <type>Facet</type>
</flexiPageRegions>
```

**When to combine vs separate:**
- **Combine**: Components that logically belong to same tab/section (e.g., multiple field sections in detail tab)
- **Separate**: Components that belong to different tabs/sections (e.g., `detailTabContent` vs `relatedTabContent`)

---

## 6. Correct Element Names (CRITICAL — PREVENTS INVALID XML ERRORS)

**FlexiPage XML uses specific element names. Common LLM hallucinations use WRONG names that cause deployment failures.**

| WRONG (do NOT use) | CORRECT |
|---|---|
| `<entityType>` | `<sobjectType>` |
| `<properties>` | `<componentInstanceProperties>` |
| `<regions>` | `<flexiPageRegions>` |
| `<components>` | `<itemInstances>` |
| `<innerComponents>` | (does not exist — use facets for nesting) |
| `<fieldItems>` | `<itemInstances>` containing `<fieldInstance>` |
| `<template>value</template>` | `<template><name>value</name></template>` |
| `<parentFlexiPage>flexipage:templateName</parentFlexiPage>` | `<parentFlexiPage>flexipage__default_rec_L</parentFlexiPage>` |

**Do NOT invent elements or component names:**

Only use component names discovered through the 3-tier discovery process or present in the template from CLI. Do NOT add any XML element that is not present in the template structure from the CLI template. If a component name did not come from discovery or the CLI template.

| WRONG (do NOT use) | Why / What to use instead |
|---|---|
| `<apiVersion>` | Not a FlexiPage element — API version lives in `sfdx-project.json` |
| `<description>` | Not a FlexiPage element — use `<masterLabel>` for the page name |
| `flexipage:tabs` | Does not exist — use `flexipage:tabset` + `flexipage:tab` in facets |
| `flexipage:tabset2` | Does not exist — correct name is `flexipage:tabset` |
| `flexipage:facet` | Does not exist — use `flexipage:column` with `body` property |
| `flexipage:fields` | Does not exist — use individual `fieldInstance` elements in a field facet |
| `<type>String</type>` inside `componentInstanceProperties` | Remove — only valid `<type>` value is `decorator`, and only for UtilityBar pages |

**Correct top-level FlexiPage structure (element order):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">
    <flexiPageRegions>...</flexiPageRegions>
    <masterLabel>Page Name</masterLabel>
    <parentFlexiPage>flexipage__default_rec_L</parentFlexiPage>
    <sobjectType>Account</sobjectType>
    <template>
        <name>flexipage:recordHomeTemplateDesktop</name>
    </template>
    <type>RecordPage</type>
</FlexiPage>
```

**Correct componentInstance structure:**
```xml
<componentInstance>
    <componentInstanceProperties>
        <name>propertyName</name>
        <value>propertyValue</value>
    </componentInstanceProperties>
    <componentName>lightning:card</componentName>
    <identifier>unique_id_1</identifier>
</componentInstance>
```

**`<componentInstanceProperties>` children — `<name>`, `<value>`, and optionally `<type>`:**

```xml
<!-- WRONG — "String", "Facet", etc. are NOT valid <type> values -->
<componentInstanceProperties>
    <name>fieldApiName</name>
    <type>String</type>
    <value>Record.Name</value>
</componentInstanceProperties>

<!-- CORRECT — omit <type> for standard properties (most cases) -->
<componentInstanceProperties>
    <name>fieldApiName</name>
    <value>Record.Name</value>
</componentInstanceProperties>

<!-- CORRECT — <type>decorator</type> ONLY for UtilityBar component decorators -->
<componentInstanceProperties>
    <name>panelHeight</name>
    <type>decorator</type>
    <value>480</value>
</componentInstanceProperties>
```

**`<type>` rules:**
- If omitted (default): the property applies to the Lightning component itself
- If `decorator`: the property applies to the **component decorator** (a wrapper that adds capabilities like height/width when opened)
- The ONLY valid value is `decorator` — never `String`, `Facet`, `Integer`, etc.
- Component decorators are ONLY supported on **UtilityBar** page types — do NOT use `<type>decorator</type>` on RecordPage, AppPage, or HomePage

**Nesting is done via facets, NOT via inner elements.** Components that contain other components reference a facet name in their properties; the facet is a sibling `<flexiPageRegions>` with `<type>Facet</type>`.

| Error | Cause | Fix |
|-------|-------|-----|
| "Element regions invalid in FlexiPage" | Used `<regions>` instead of `<flexiPageRegions>` | Replace with `<flexiPageRegions>` |
| "Element components invalid in FlexiPageRegion" | Used `<components>` instead of `<itemInstances>` | Replace with `<itemInstances>` |
| "couldn't retrieve design time component information" | Used hallucinated component name (`flexipage:tabs`, `flexipage:tabset2`) | Use `flexipage:tabset` — see `identifiers_and_regions.md` for the full 3-layer tab pattern |

---

## Common Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "We couldn't retrieve or load the information on the field" | Invalid field API name — field doesn't exist or has incorrect spelling | Use MCP tools or describe commands to discover valid fields |
| "Invalid field reference" | Used `ObjectName.Field` instead of `Record.Field` | Change to `Record.{FieldApiName}` |
| "Element componentInstance is duplicated at this location in type ItemInstance" | Multiple `<componentInstance>` in one `<itemInstances>` | Each `<componentInstance>` needs its own `<itemInstances>` wrapper |
| "Element fieldInstance is duplicated" | Multiple fieldInstances in one `<itemInstances>` | Each fieldInstance needs its own `<itemInstances>` wrapper |
| "Missing fieldInstanceProperties" | No uiBehavior specified | Add `fieldInstanceProperties` with `uiBehavior` |
| "Unused Facet" | Facet defined but not referenced by any component | Remove Facet or reference it in a component property |
| "XML parsing error" | Unencoded HTML/XML in property values | Encode `<`, `>`, `&`, `"`, `'` in all `<value>` tags |
| "Cannot create component with namespace" | Invalid page name (used `__c` suffix) | Use `Volunteer_Record_Page` not `Volunteer__c_Record_Page` |
| "Region specifies mode that parent doesn't support" | Added `<mode>` to a region that doesn't support it | Only use `<mode>` where required (e.g., `<mode>Replace</mode>` in `detailTabContent` for Dynamic Forms) |
| "We couldn't retrieve the design time component information for component X" | Hallucinated component name (e.g., `flexipage:tabs`, `flexipage:tabset2`) | Use correct component name — see Section 6 table and `identifiers_and_regions.md` for valid patterns |
| "'String' is not a valid value for the enum 'ComponentInstancePropertyTypeEnum'" | Used invalid `<type>` value (e.g., `String`, `Facet`, `Integer`) inside `<componentInstanceProperties>` | Remove `<type>` entirely — the only valid value is `decorator`, and only for UtilityBar page types |
| "Element apiVersion invalid at this location in type FlexiPage" | Added `<apiVersion>` to FlexiPage XML | Remove — API version belongs in `sfdx-project.json`, not in FlexiPage metadata |
