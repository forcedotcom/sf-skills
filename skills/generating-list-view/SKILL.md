---
name: generating-list-view
description: Use this skill when users need to create, generate, or validate Salesforce List View metadata. Trigger when users mention list views, filtered record lists, creating views, setting up record columns, filtering records by criteria, or ask about list view visibility. Also use when users say things like "I need a view that shows...", "filter records by...", "create a list view for...", or when they're working with ListView XML files and need validation or troubleshooting.
---

## When to Use This Skill

Use this skill when you need to:
- Create list views for objects
- Generate filtered, column-based record listings
- Configure list view visibility and sharing
- Troubleshoot deployment errors related to List Views

## Specification

# Salesforce List View Metadata Knowledge

## 📋 Overview
Salesforce List Views define filtered, column-based record listings on an object's tab.

## 🎯 Purpose
- Provide curated, role- or task-specific subsets of records
- Standardize commonly used filters and visible fields across teams

## 🔧 Configuration

Unless specifically requested to be generated inline, List Views are stored at:
- force-app/main/default/objects/<ObjectName>/listViews/<fullName>.listView-meta.xml
Only if the user requests are they to be included in the object's metadata file:
- fore-app/main/default/objects/<ObjectName>/<ObjectName>.object-meta.xml

Key elements:
- label: Human-friendly name shown in UI (must be under 40 characters in length)
- fullName (fullName): API identifier used in metadata and file name
- filterScope: Everything | Mine | Queue
- filters: field/operation/value triples
- booleanFilterLogic: Combine multiple filters logically with AND/OR (e.g., "1 AND (2 OR 3)")
- columns: Ordered list of field API names to display

References:
- listViews appear on the entity's tab
- listViews can be referenced by flexipages using the "filterListCard" component

### Critical Decision: Visibility Strategy
Choose how broadly the view should appear in the org.

**Choose "Visible to all users" when:**
- The view is useful across profiles/roles
- It's a governed, shared artifact to be managed via source control
- Data contained is appropriate for broad visibility

**Choose "Owner-only/Restricted" when:**
- It is experimental or niche during iteration
- It is specifically requested to be limited to Users, Groups or Roles
- There are governance/security reviews pending

**When in doubt:** Default to "Visible to all users".

### Critical Decision: Columns Density
**Choose minimal, high-signal columns when:**
- Users need at-a-glance scanning
- Mobile/responsive performance matters

**Choose richer column sets when:**
- Desktop heavy workflows need more context without opening records
- It serves as a work queue and extra fields reduce clicks

**When in doubt:** Start with 4–6 columns that directly support the primary task.

## Critical Rules (Read First)

### Rule 1: Custom Field API Names
For custom fields, use exact API names (e.g., Status__c), not labels.

Wrong:
- Status (label)

Right:
- Status__c (API name)

### Rule 2: Standard Field Names
For standard fields on Custom Objects, use already defined names:

Wrong:
- Name (API Name)

Right:
- NAME

The standard fields on Custom Objects are:
- NAME
- RECORDTYPE
- OWNER.ALIAS
- OWNER.FIRST_NAME
- OWNER.LAST_NAME
- CREATEDBY_USER.ALIAS
- CREATEDBY_USER
- CREATED_DATE
- UPDATEDBY_USER.ALIAS
- UPDATEDBY_USER
- LAST_UPDATE
- LAST_ACTIVITY

### Rule 3: Operations Must Match Field Types
Picklists require equals/notEqual; date fields require date operators; boolean values are 0 and 1; do not mix text-only operators with non-text fields.

Wrong:
- operation="contains" on a picklist
- value=True on a boolean

Right:
- operation="equals" with a valid picklist value
- value=1 on a boolean

### Rule 4: Name and Path Alignment
File name, fullName (also sometimes referred to as DeveloperName), and uniqueness must align.

Wrong:
- File: My_List.listView-meta.xml
- fullName: MyList

Right:
- File: MyList.listView-meta.xml
- fullName: MyList

### Rule 5: Folder Placement
Place files under the object's listViews directory or deployments will fail to resolve components.  Only if a user
requests it, may the listView may be included inline in force-app/main/default/objects/<ObjectName>/<ObjectName>.object-meta.xml

Path:
- force-app/main/default/objects/<ObjectName>/listViews/<fullName>.listView-meta.xml

## Generation Workflow

### Step 1: Get Metadata Information
- Identify the target object API name (e.g., Object__c).
- Gather business requirements: purpose, audience, fields, filters.
- Validate values and operator compatibility with field types.

### Step 2: Examine Existing Examples
- Repo: force-app/main/default/objects/<Object>/listViews/ (unless otherwise required by end user)
- Org: retrieve existing list views for proven patterns (filters, logic, columns).
- Note what passed review/deployment and delivered expected UX.

### Step 3: Create Specification
Document before implementation:
- Name: fullName and Label
- Audience: Visibility scope ("all users" vs. shared)
- Filter scope: Everything | Mine | Queue
- Filter items: filter, operator, value; plus booleanFilterLogic if multiple
- Columns: Ordered list of field API names
- Acceptance criteria: Which records appear, paging behavior, key scenarios

### Step 4: Author Metadata File
Use a Lightning-compatible template and ensure valid XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ListView xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>OpenMine</fullName>
    <label>Open - My Records</label>
    <filterScope>Mine</filterScope>
    <columns>NAME</columns>
    <columns>Status__c</columns>
    <columns>OWNER.ALIAS</columns>
    <columns>LAST_UPDATE</columns>
    <filters>
        <field>Status__c</field>
        <operation>equals</operation>
        <value>Open</value>
    </filters>
    <sharedTo>
        <role>CEO</role>
        <roleAndSubordinatesInternal>COO</roleAndSubordinatesInternal>
    </sharedTo>
</ListView>
```

Notes:
- For "My" views, use filterScope="Mine".
- Keep columns tight and purposeful.
- If intended for all users, omit the "sharedTo" section.

### Step 5: Validate Locally
- Well-formed XML; correct namespace
- Field names exist on the object; operators and values match field types
- Path and fullName alignment
- If multiple filters: set booleanFilterLogic correctly (e.g., "1 AND (2 OR 3)")

### Step 6: Deploy and Verify in Org
- Deploy the component path or the whole object.
- In the UI, open the object tab and:
    - Confirm records match filters
    - Confirm columns render correctly
    - Confirm visibility matches audience

## Common Deployment Errors

| Error | Cause                                                                                       | Fix                                                                                |
|-------|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| "Invalid field Status" | Used label instead of API name, or used API Name instead of defined name for Standard Field | Use Status__c (or correct API name), or NAME instead of Name (for Standard Fields) |
| "Invalid filter operator" | Operator not valid for field type  | Choose operation compatible with field type (e.g., equals for picklist)            |
| "Component not found at path" | Wrong folder or file name  | Place in objects/<Object>/listViews and align file name with fullName              |
| "Malformed booleanFilterLogic" | Syntax or index mismatch  | Use "1 AND 2" style, ensure filters index order matches                            |

## Verification Checklist
- [ ] All required fields populated (fullName, label, filterScope, columns)
- [ ] Property values are XML-encoded where needed
- [ ] Custom Field references use API names (e.g., Status__c)
- [ ] Standard Field references use defined names (e.g., NAME)
- [ ] Operations match field types; picklist values are valid
- [ ] booleanFilterLogic (if used) matches filters ordering and count
- [ ] File path and fullName/developerName are aligned
- [ ] No deprecated or Classic-only properties included
- [ ] Deployed successfully and visible as intended
- [ ] Records, columns, and filtering behave as specified
