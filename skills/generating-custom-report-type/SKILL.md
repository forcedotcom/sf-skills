---
name: generating-custom-report-type
description: "Use this skill when users need to create, generate, or validate Salesforce Custom Report Type metadata. Trigger when users mention custom report types, report types, CRTs, reporting frameworks, cross-object reports, report builder data sources, or ask to expose fields for reporting across related objects. Also use when users mention primary and related objects for reports, inner vs outer joins in reports, report type categories, or encounter deployment errors for .reportType-meta.xml files. Do NOT trigger for: running, editing, or filtering existing reports; creating report folders, dashboards, or list views; or general reporting questions that don't involve authoring a .reportType-meta.xml file."
---

## When to Use This Skill

Use this skill when you need to:
- Create a Custom Report Type (CRT) so users can build reports that span related objects
- Define which primary and related objects appear in the report builder
- Expose specific fields (including fields via lookup) for a report
- Choose between inner and outer join behavior across object relationships
- Troubleshoot deployment errors related to `.reportType-meta.xml` files

## Specification

# Salesforce Custom Report Type Metadata Knowledge

## 📋 Overview
Custom Report Types (CRTs) define the **data framework** for Salesforce reports. They specify a primary object, up to 3 related objects, the relationship (join) between them, and which fields are available in the report builder.

## 🎯 Purpose
- Enable reporting across custom objects and custom relationships not covered by standard report types
- Curate a focused set of fields for report builders (including fields reached via lookup)
- Control inner/outer join behavior to include or exclude primary records without related records

## 🔧 Configuration

Custom Report Types are stored at:
- `force-app/main/default/reportTypes/<fullName>.reportType-meta.xml`

Each CRT is a single file (not nested under an object folder).

### Key Elements

| Element | Required | Notes |
|---------|----------|-------|
| `<fullName>` | Yes | API identifier; must match the file name. Letters, numbers, underscores; must begin with a letter; no spaces; no trailing underscore; no consecutive underscores |
| `<label>` | Yes | Human-friendly name shown in the report type picker |
| `<description>` | Recommended | State the business "why" — who uses this and what they learn |
| `<baseObject>` | Yes | API name of the primary object (e.g. `Account`, `Project__c`). Cannot be changed after initial creation. All objects, including custom and external, are supported (external objects from API 38.0+) |
| `<category>` | Recommended | Report builder category — see category values below |
| `<deployed>` | Yes | `true` to expose to users; `false` while building/iterating |
| `<join>` | Conditional | Adds a related object and its join behavior. Nest further `<join>` blocks for deeper relationships |
| `<sections>` | Recommended | Groups of columns available to the report type. Though not strictly required, a report without columns isn't useful |
| `<displayNameOverride>` (on `<columns>`) | No | Custom column label shown in the report builder, overriding the field's default label |

### Valid `<category>` Values (`ReportTypeCategory` enumeration)

The `category` value determines where the CRT appears in the report builder's "Create New Report Type" wizard. Use one of these Salesforce-defined values (per the Metadata API `ReportTypeCategory` enum):

| Category value | Typical use |
|----------------|-------------|
| `accounts` | Accounts & Contacts |
| `opportunities` | Opportunities |
| `forecasts` | Forecasts |
| `cases` | Customer Support Reports |
| `leads` | Leads |
| `campaigns` | Campaigns |
| `activities` | Activities |
| `busop` | Business operations |
| `products` | Price Books, Products and Assets |
| `admin` | Administrative Reports |
| `territory` | Territory management |
| `territory2` | Territory management (Enterprise Territory Management) — API 31.0+ |
| `usage_entitlement` | Usage entitlements |
| `wdc` | Work.com / Calibration — API 29.0+ |
| `calibration` | Calibration — API 29.0+ |
| `other` | Other Reports (default for custom-object-based CRTs without a natural home) |
| `content` | Content |
| `quotes` | Quotes |
| `individual` | Individual (privacy) — API 45.0+ |
| `employee` | Employee — API 46.0+ |
| `data_cloud` | Data Cloud — API 55.0+ |
| `commerce` | Commerce — API 60.0+ |
| `flow` | Flow — API 60.0+ |
| `semantic_model` | Semantic model — API 60.0+ |

**When in doubt:** Use `other` for custom-object-based CRTs.

## Critical Rules (Read First)

### Rule 1: File Name and `fullName` Must Match
The `.reportType-meta.xml` file name (without extension) must equal `<fullName>`.

**Wrong:**
- File: `Account_Projects.reportType-meta.xml`
- `<fullName>AccountProjects</fullName>`

**Right:**
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
- Repo: `force-app/main/default/reportTypes/` for in-project CRT patterns
- Org: retrieve existing report types via `sf project retrieve start --metadata ReportType` to compare structures

### Step 3: Write the Specification
Document before authoring:
- `fullName` and `label`
- `baseObject`
- Category and `deployed` state
- Join chain: for each related object — relationship name, outer vs inner join
- Section layout: one section per object, ordered list of fields
- Acceptance criteria: which records should appear when the report runs, which fields are available in the builder

### Step 4: Author the Metadata File

**Example A — Primary object only (no joins):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ReportType xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>AccountsWithIndustry</fullName>
    <baseObject>Account</baseObject>
    <category>accounts</category>
    <deployed>true</deployed>
    <label>Accounts with Industry Detail</label>
    <description>Report framework for reviewing accounts with industry and revenue fields surfaced.</description>
    <sections>
        <masterLabel>Account Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account</table>
        </columns>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Industry</field>
            <table>Account</table>
        </columns>
        <columns>
            <checkedByDefault>false</checkedByDefault>
            <field>AnnualRevenue</field>
            <table>Account</table>
        </columns>
    </sections>
</ReportType>
```

**Example B — Outer join (Accounts with or without Projects):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ReportType xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>AccountsWithProjects</fullName>
    <baseObject>Account</baseObject>
    <category>accounts</category>
    <deployed>true</deployed>
    <label>Accounts with or without Projects</label>
    <description>Shows every account; related project fields appear when projects exist.</description>
    <join>
        <outerJoin>true</outerJoin>
        <relationship>Projects__r</relationship>
    </join>
    <sections>
        <masterLabel>Account Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account</table>
        </columns>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Industry</field>
            <table>Account</table>
        </columns>
    </sections>
    <sections>
        <masterLabel>Project Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account.Projects__r</table>
        </columns>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Status__c</field>
            <table>Account.Projects__r</table>
        </columns>
        <columns>
            <checkedByDefault>false</checkedByDefault>
            <field>CreatedDate</field>
            <table>Account.Projects__r</table>
        </columns>
    </sections>
</ReportType>
```

**Example C — Inner join with nested join (Accounts with Projects with Tasks):**

Note: `<table>` values use the dotted relationship path (`Account.Projects__r`, `Account.Projects__r.Tasks__r`) — not the raw object API name.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ReportType xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>AccountProjectsWithTasks</fullName>
    <baseObject>Account</baseObject>
    <category>other</category>
    <deployed>true</deployed>
    <label>Accounts with Projects with Tasks</label>
    <description>Reports on accounts that have projects, and those projects that have tasks — useful for active-engagement tracking.</description>
    <join>
        <outerJoin>false</outerJoin>
        <relationship>Projects__r</relationship>
        <join>
            <outerJoin>false</outerJoin>
            <relationship>Tasks__r</relationship>
        </join>
    </join>
    <sections>
        <masterLabel>Account Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account</table>
        </columns>
    </sections>
    <sections>
        <masterLabel>Project Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account.Projects__r</table>
        </columns>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Status__c</field>
            <table>Account.Projects__r</table>
        </columns>
    </sections>
    <sections>
        <masterLabel>Task Fields</masterLabel>
        <columns>
            <checkedByDefault>true</checkedByDefault>
            <field>Name</field>
            <table>Account.Projects__r.Tasks__r</table>
        </columns>
        <columns>
            <checkedByDefault>false</checkedByDefault>
            <field>Due_Date__c</field>
            <table>Account.Projects__r.Tasks__r</table>
        </columns>
    </sections>
</ReportType>
```

### Step 5: Validate Locally
- Well-formed XML with correct namespace
- File name matches `<fullName>`; file is under `force-app/main/default/reportTypes/`
- `<baseObject>` exists and is deployed
- Every `<relationship>` uses the correct child relationship name (`__r` suffix for custom)
- Each object referenced in `<sections>` is part of the CRT (primary or joined)
- All `<field>` references exist on the parent `<table>` and use API names (not labels)
- `<category>` is a valid Salesforce category value
- `<deployed>` is `true` if users need to access the CRT immediately

### Step 6: Deploy and Verify in Org

Deploy:
```bash
sf project deploy start --source-dir force-app/main/default/reportTypes/<fullName>.reportType-meta.xml
```

In the UI:
- Reports → New Report → confirm the CRT appears under the configured category
- Select the CRT and confirm all expected fields appear in the report builder field panel
- Run a test report; confirm join behavior (inner vs outer) returns the expected record set

## Common Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid object name 'X'` on `<baseObject>` | Primary object doesn't exist or isn't deployed | Deploy the custom object before the CRT |
| `Invalid relationship name 'X'` on `<join>` | Used the field API name instead of the child relationship name, or forgot `__r` | Use the child relationship name (e.g. `Projects__r` for a custom relationship) |
| `Invalid field 'X' for object 'Y'` | Field doesn't exist on `<table>`, used label instead of API name, or field not yet deployed | Verify field API name; deploy dependent fields first |
| `Invalid category value 'X'` | Typo or non-existent category | Use a valid `ReportTypeCategory` value from the table above (e.g. `other` for general-purpose custom-object CRTs) |
| Inner join after outer join | A nested `<join>` has `<outerJoin>false</outerJoin>` following an earlier outer join | Switch the nested join to `<outerJoin>true</outerJoin>`, or restructure so inner joins come first |
| Fields from joined object not visible in report builder | `<table>` in `<sections>` for the joined object doesn't use the dotted relationship path | Change `<table>` to the full path (e.g. `Account.Projects__r` not `Project__c`) |
| `Cannot change base object` on update | Attempted to change `<baseObject>` after initial deploy | Create a new CRT with the new primary object; retire the old one |
| File not found / fullName mismatch | File name doesn't match `<fullName>` | Rename file so `<fullName>.reportType-meta.xml` matches |

## Verification Checklist

### Universal Checks
- [ ] File path is `force-app/main/default/reportTypes/<fullName>.reportType-meta.xml`
- [ ] File name (without extension) matches `<fullName>` exactly
- [ ] `<fullName>` begins with a letter; no spaces; no trailing underscore; no consecutive underscores
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

### Post-Deployment Checks
- [ ] CRT appears in Report Builder under the expected category
- [ ] All fields appear in the report builder field panel
- [ ] A test report returns records consistent with the configured join behavior (inner vs outer)
