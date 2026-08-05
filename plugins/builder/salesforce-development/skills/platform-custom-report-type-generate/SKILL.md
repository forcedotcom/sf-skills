---
name: platform-custom-report-type-generate
description: "Use this skill when users need to create, generate, or validate Salesforce Custom Report Type metadata. Trigger when users mention custom report types, report types, CRTs, reporting frameworks, cross-object reports, report builder data sources, or ask to expose fields for reporting across related objects. Also use when users mention primary and related objects for reports, inner vs outer joins in reports, report type categories, or encounter deployment errors for .reportType-meta.xml files. Do NOT trigger for: running, editing, or filtering existing reports; creating report folders, dashboards, or list views; or general reporting questions that don't involve authoring a .reportType-meta.xml file."
metadata:
  version: "1.0"
  minApiVersion: "51.0"
---

## Specification

# Salesforce Custom Report Type Metadata Knowledge

## Overview
Custom Report Types (CRTs) define the **data framework** for Salesforce reports. They specify a primary object, up to 3 related objects, the relationship (join) between them, and which fields are available in the report builder.

## Purpose
- Enable reporting across custom objects and custom relationships not covered by standard report types
- Curate a focused set of fields for report builders (including fields reached via lookup)
- Control inner/outer join behavior to include or exclude primary records without related records

## Configuration

**File extension:** `.reportType-meta.xml`. The file basename is the report type's developer name (e.g. `AccountsWithProjects.reportType-meta.xml`). Each CRT is a single file, not nested under an object folder.

### Key Elements

Top-level `<ReportType>` children:

| Element | Required | Notes |
|---------|----------|-------|
| `<fullName>` | Yes | API identifier; must match the file name. Letters, numbers, underscores; must begin with a letter; no spaces; no trailing underscore; no consecutive underscores |
| `<label>` | Yes | Human-friendly name shown in the report type picker |
| `<description>` | Recommended | State the business "why" — who uses this and what they learn |
| `<baseObject>` | Yes | API name of the primary object (e.g. `Account`, `Project__c`). Cannot be changed after initial creation. All objects, including custom and external, are supported (external objects from API 38.0+) |
| `<category>` | Recommended | Report builder category — see `references/category-values.md` |
| `<deployed>` | Yes | `true` to expose to users; `false` while building/iterating |
| `<join>` | Conditional | Adds a related object and its join behavior. Nest further `<join>` blocks for deeper relationships |
| `<sections>` | Recommended | Groups of columns available to the report type. Though not strictly required, a report without columns isn't useful |

`<sections>` (group of columns) sub-elements:

| Element | Required | Notes |
|---------|----------|-------|
| `<masterLabel>` | Yes | Section heading shown in the report builder |
| `<columns>` | Conditional | One per field exposed in the section |

`<columns>` (single field) sub-elements:

| Element | Required | Notes |
|---------|----------|-------|
| `<field>` | Yes | Field API name (or dotted lookup-traversal path) |
| `<table>` | Yes | The object the field belongs to — base object name or dotted relationship path |
| `<checkedByDefault>` | Yes | `true` if the column is selected by default in the report builder |
| `<displayNameOverride>` | No | Custom column label shown in the report builder, overriding the field's default label |

## Critical Rules (Read First)

### Rule 1: If `<fullName>` Is Present, It Must Match the File Name
In source format, `fullName` is inherited from `Metadata` and derived from the file name, so the `<fullName>` element is technically optional. The repo convention is to include it. **If you include `<fullName>`, its value must equal the file name (everything before `.reportType-meta.xml`) exactly — same characters, same casing, same underscores.**

**Wrong** — file name and `<fullName>` differ:
- File: `account_projects.reportType-meta.xml`
- `<fullName>AccountProjects</fullName>`
  (Mismatch: file uses `account_projects`, fullName uses `AccountProjects`)

**Right** — file name and `<fullName>` are identical:
- File: `AccountProjects.reportType-meta.xml`
- `<fullName>AccountProjects</fullName>`

### Rule 2: Join Semantics — `outerJoin` Controls Inclusion

Each `<join>` block has an `<outerJoin>` element that determines which primary records appear in the report:

| `<outerJoin>` value | Behavior | Report Builder Label |
|---------------------|----------|----------------------|
| `false` | Inner join — only primary records that HAVE at least one related record | "Each 'A' record must have at least one related 'B' record" |
| `true` | Outer join — all primary records, with or without related records | "'A' records may or may not have related 'B' records" |

**Default when unspecified:** Use `true` (outer join) when the user wants to see all primary records regardless of children. Use `false` when the report only makes sense if children exist.

### Rule 3: Each Object Needs Its Own `<sections>` Block

Every object in the CRT (primary + each joined object) must have a corresponding `<sections>` block that lists the fields exposed for reporting. Without a section for an object, none of its fields appear in the report builder.

- `<masterLabel>` on each section is the section heading in the report builder
- `<columns>` entries list the fields — each with a `<field>` (API name) and `<table>` (object API name)
- For fields reached via lookup, use the relationship path in `<field>` (e.g. `Owner.Name` with `<table>` set to the owning object)

### Rule 4: Field API Names, Not Labels

Use exact API names for fields: standard fields use their defined names (`Name`, `CreatedDate`, `OwnerId`), custom fields use `Field__c`. Custom objects must include `__c`.

**Wrong:**
- `<field>Account Name</field>`

**Right:**
- `<field>Name</field>` with `<table>Account</table>`

### Rule 5: Relationship Path for Joined Objects

When adding a `<join>`, the `<relationship>` element must use the **child relationship name** as defined on the lookup/master-detail field pointing from the child object to the parent. For custom relationships, this typically ends in `__r`.

**Wrong:**
- `<relationship>Project</relationship>` (for a custom child relationship)

**Right:**
- `<relationship>Projects__r</relationship>` (child relationship name)
- `<relationship>Contacts</relationship>` (standard, non-custom child relationship)

### Rule 6: Maximum 4 Objects Total in a Join Chain

A single CRT can join a maximum of **four objects total** (the base object + up to 3 additional objects via nested `<join>` blocks).

### Rule 7: No Inner Join After an Outer Join

Once the join chain contains an outer join (`<outerJoin>true</outerJoin>`), every subsequent nested join must also be an outer join. An inner join that follows an outer join earlier in the sequence is not allowed.

**Wrong:**
```xml
<join>
    <outerJoin>true</outerJoin>        <!-- outer join first -->
    <relationship>Contacts</relationship>
    <join>
        <outerJoin>false</outerJoin>   <!-- WRONG: inner join after outer -->
        <relationship>Assets</relationship>
    </join>
</join>
```

**Right:**
```xml
<join>
    <outerJoin>true</outerJoin>
    <relationship>Contacts</relationship>
    <join>
        <outerJoin>true</outerJoin>    <!-- outer stays outer -->
        <relationship>Assets</relationship>
    </join>
</join>
```

### Rule 8: `<table>` for Joined Objects Uses Dotted Path

In `<sections>`, the `<table>` element identifies which object in the join chain each column belongs to. For the base object, use the object name directly (e.g. `Account`). For joined objects, use the **dotted relationship path** from the base object.

| Object in chain | `<table>` value |
|-----------------|-----------------|
| Base (Account) | `Account` |
| First join (Account → Contacts) | `Account.Contacts` |
| Nested join (Account → Contacts → Assets) | `Account.Contacts.Assets` |

### Rule 9: Field Paths Can Traverse Lookups

`<field>` values may reference fields reached via lookup relationships using dot notation — for example `Owner.Email` (owner User's email) or `ReportsTo.CreatedBy.Contact.Owner.MobilePhone`. The `<table>` must still be the object that owns the starting field.

### Rule 10: Historical Trending Fields Use `_hst` Suffix

For a field with `trackTrending=true`, the API name in `<field>` and `<table>` uses the `_hst` suffix:

```xml
<columns>
    <checkedByDefault>false</checkedByDefault>
    <field>Field2__c_hst</field>
    <table>CustomTrendedObject__c.CustomTrendedObject__c_hst</table>
</columns>
```

### Rule 11: Primary Object Cannot Be Changed After Deployment

Once deployed, the `<baseObject>` of a CRT is locked. To change the primary object, create a new CRT and retire the old one.

### Rule 12: `autogenerated` Is Reserved for Historical Trending

The `<autogenerated>` element (API 29.0+) marks CRTs that Salesforce created automatically when historical trending was enabled on an object. Do not set this manually on hand-authored CRTs.

## Generation Workflow

### Step 1: Gather Requirements
- Primary object API name (e.g. `Account`, `Project__c`)
- Related objects and the relationship between each (which has the lookup/master-detail to which)
- For each relationship: inner join (children required) or outer join (children optional)?
- Which fields to expose per object — aim for task-relevant, not the full field list
- Audience and category — where should this appear in the report builder picker?
- Whether this ships as `deployed=true` now or stays `deployed=false` during iteration

### Step 2: Examine Existing Examples
- Look in the project for in-project CRT patterns
- If existing report types have been retrieved from an org, compare against those structures

### Step 3: Write the Specification
Document before authoring:
- `fullName` and `label`
- `baseObject`
- Category and `deployed` state
- Join chain: for each related object — relationship name, outer vs inner join
- Section layout: one section per object, ordered list of fields
- Acceptance criteria: which records should appear when the report runs, which fields are available in the builder

### Step 4: Author the Metadata File

Start from the closest example in `examples/` and adapt it to the user's scenario:

- Primary object only (no joins) → `examples/AccountsWithIndustry.reportType-meta.xml`
- Outer join (primary records included even without children) → `examples/AccountsWithProjects.reportType-meta.xml`
- Nested inner join (every level requires children) → `examples/AccountProjectsWithTasks.reportType-meta.xml`

Name the file `<DeveloperName>.reportType-meta.xml`.

### Step 5: Validate
- Well-formed XML with correct namespace (`xmlns="http://soap.sforce.com/2006/04/metadata"`)
- File name (without `.reportType-meta.xml`) matches `<fullName>` when `<fullName>` is included
- `<baseObject>` is a valid API name and the object is deployed
- Every `<relationship>` uses the correct child relationship name (`__r` suffix for custom)
- Each object referenced in `<sections>` is part of the CRT (primary or joined)
- All `<field>` references exist on the parent `<table>` and use API names (not labels)
- `<category>` is a valid Salesforce category value
- `<deployed>` is `true` if users need to access the CRT immediately

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/AccountsWithIndustry.reportType-meta.xml` | Step 2 / Step 4 — primary-object-only template |
| `examples/AccountsWithProjects.reportType-meta.xml` | Step 2 / Step 4 — outer-join template (primary included even without children) |
| `examples/AccountProjectsWithTasks.reportType-meta.xml` | Step 2 / Step 4 — nested inner-join template (every level requires children) |
| `references/category-values.md` | Step 3 — to choose a valid `<category>` value from the `ReportTypeCategory` enum |
| `references/errors-and-troubleshooting.md` | When fields don't appear in the report builder or join requirements conflict |

## Verification Checklist

### Universal Checks
- [ ] File extension is `.reportType-meta.xml`
- [ ] File basename satisfies the developer-name rules (begins with a letter, only letters/numbers/underscores, no spaces, no trailing underscore, no consecutive underscores)
- [ ] If `<fullName>` is included, it matches the file basename exactly (same characters, casing, and underscores)
- [ ] `<label>` is human-readable and under 40 characters
- [ ] `<description>` explains the business purpose
- [ ] `<baseObject>` uses a valid API name and that object is deployed
- [ ] `<category>` is a valid `ReportTypeCategory` enum value
- [ ] `<deployed>` is set appropriately (`true` for user access, `false` for in-progress iteration)
- [ ] `<autogenerated>` is NOT set manually (reserved for historical-trending CRTs)

### Join Checks
- [ ] Each `<join>` uses the correct child **relationship name** (not the lookup field API name)
- [ ] Custom relationships use `__r` suffix
- [ ] `<outerJoin>` is set intentionally: `true` = optional children, `false` = required children
- [ ] No inner join (`<outerJoin>false</outerJoin>`) appears after an outer join earlier in the sequence
- [ ] Total object count (base + joins, including nested) is 4 or fewer

### Section Checks
- [ ] Every object in the CRT has a corresponding `<sections>` block
- [ ] `<masterLabel>` on each section is descriptive
- [ ] Every `<columns>` has both `<field>` (API name) and `<table>` (object API name or dotted path)
- [ ] `<checkedByDefault>` is set for each column
- [ ] `<table>` for base object is the object API name (e.g. `Account`)
- [ ] `<table>` for joined objects uses the dotted relationship path (e.g. `Account.Projects__r`, `Account.Projects__r.Tasks__r`)
- [ ] Field references use API names (not labels); custom fields use `__c`
- [ ] Lookup traversal fields use dot notation (e.g. `Owner.Email`) with `<table>` set to the object owning the starting field
- [ ] Historical trending fields use `_hst` suffix in both `<field>` and `<table>` when applicable
- [ ] No duplicate fields within a section
