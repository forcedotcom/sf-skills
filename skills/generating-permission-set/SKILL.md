---
name: generating-permission-set
description: "Generates correct, deployable Salesforce permission set metadata (PermissionSet XML) with object, field, user, and app permissions. Use this skill when creating or editing permission set metadata, object permissions, field-level security (FLS), tab visibility, or deploying permission sets."
compatibility: Salesforce Metadata API v60.0+
metadata:
  author: sf-skills
  version: "1.0"
---

## When to Use This Skill

Use when generating or editing permission set metadata, or when granting object, field, user, and app permissions.

## Step 1: Define Core Properties

Start by defining the required permission set properties:

```xml
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>YourPermissionSetName</fullName>
    <label>Display Name for Administrators</label>
    <description>Clear description of purpose and intended audience</description>
</PermissionSet>
```

**Naming conventions:**
- Use descriptive API names (e.g., `Sales_Manager_Access`)

## Step 2: Configure Object Permissions

Add CRUD permissions for standard and custom objects:

```xml
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowRead>true</allowRead>
    <allowEdit>true</allowEdit>
    <allowDelete>false</allowDelete>
    <modifyAllRecords>false</modifyAllRecords>
    <viewAllRecords>false</viewAllRecords>
    <viewAllFields>false</viewAllFields>
    <object>Account</object>
</objectPermissions>
```

## Step 3: Set Field-Level Security

Define field permissions for sensitive or custom fields:

```xml
<fieldPermissions>
    <editable>true</editable>
    <readable>true</readable>
    <field>Account.SSN__c</field>
</fieldPermissions>
```

**Important:**
- Required fields must NEVER appear in list of field permissions. Granting field-level security on required fields is not allowed by the platform and will cause deployment failure. 
- Before adding any field, confirm from the object metadata that the field exists and is not required
- A field is required when its metadata contains `<required>true</required>`:
- Formula fields cannot be editable
- Master-detail fields are required fields on the child (detail) object

```xml
<fields>
    <fullName>FieldName__c</fullName>
    <required>true</required>
</fields>
```

**A field counts as required (and must be omitted from `<fieldPermissions>`) when ANY of these are true:**
- Field metadata contains `<required>true</required>`
- Field is a **Master-Detail** relationship (`<type>MasterDetail</type>`) — implicitly required on the child object
- Field is a **system required** standard field (e.g. `Name` on most objects, `OwnerId`, `CreatedById`)
- Field is a **Lookup** with `<required>true</required>` set

**Detection:** read the field's `*.field-meta.xml` before emitting a `<fieldPermissions>` entry. If you cannot read it, do not emit the entry — flag the field for manual review.

- Use format `ObjectName.FieldName` for field references
- Set both readable and editable to true when the user needs edit access; editable implies readable
- If all fields should be visible, can alternatively enable the "viewAllFields" object permission

## Step 4: Grant User Permissions

Add system-level permissions for features and capabilities:

```xml
<userPermissions>
    <enabled>true</enabled>
    <name>ApiEnabled</name>
</userPermissions>
<userPermissions>
    <enabled>true</enabled>
    <name>RunReports</name>
</userPermissions>
```

**Common permissions:**
- `ApiEnabled`: API access
- `ViewSetup`: View Setup menu
- `ManageUsers`: User management
- `RunReports`: Report execution

**Security review required for:**
- `ViewAllData`: Read all records
- `ModifyAllData`: Edit all records
- `ManageUsers`: User administration

## Step 5: Configure App and Tab Visibility

Make applications and tabs visible to users:

```xml
<applicationVisibilities>
    <application>Sales_Console</application>
    <visible>true</visible>
</applicationVisibilities>
<tabSettings>
    <tab>CustomTab__c</tab>
    <visibility>Visible</visibility>
</tabSettings>
```

**Application visibility options:**
- <visible> can be true or false

**Tab visibility options:**
- `Visible`: The tab is available on the All Tabs page and appears in the visible tabs for its associated app. Can be customized.
- `Available`: The tab is available on the All Tabs page. Individual users can customize their display to make the tab visible in any app
- `None`: Not visible

**CRITICAL - Tab Naming:**
- Custom object tabs: MUST include the __c suffix (e.g., MyCustomObject__c)
- Standard object tabs: Use the object name with "standard-" prefix (e.g., standard-Account, standard-Contact)
- The tab name matches the object's API name exactly

## Step 6: Add Apex and Visualforce Access (Optional)

Grant access to custom code:

```xml
<classAccesses>
    <apexClass>CustomController</apexClass>
    <enabled>true</enabled>
</classAccesses>
<pageAccesses>
    <apexPage>CustomPage</apexPage>
    <enabled>true</enabled>
</pageAccesses>
```

## Step 7: Set License and Record Type Settings (Optional)

Specify license requirements and record type visibility:

```xml
<license>Salesforce</license>
<hasActivationRequired>false</hasActivationRequired>
<recordTypeVisibilities>
    <recordType>Account.Business</recordType>
    <visible>true</visible>
    <default>true</default>
</recordTypeVisibilities>
```
## Step 8: Set Agent Access (Optional)
                                              
Enable access to Agentforce Employee Agents for users assigned to this permission set:

<agentAccesses>
    <agentName>Sales_Assistant_Agent</agentName>
    <enabled>true</enabled>
</agentAccesses>

Field requirements:
- agentName (Required): The developer name of the employee agent
- enabled (Required): Set to true to grant access, false to deny

Important:
- Agent names must match existing Agentforce Employee Agent developer names

## Validation Checklist

Before deploying, verify:
- [ ] fullName, label, description set
- [ ] Permissions follow least privilege
- [ ] No required fields in `<fieldPermissions>` — for each entry, verified the field's `*.field-meta.xml` does NOT have `<required>true</required>` and is NOT a Master-Detail
- [ ] No duplicate permissions
- [ ] No lengthy comments

## What Causes Deployment Failure

- **Field permissions on required fields:** Any required field in `<fieldPermissions>` fails deployment with an error like:

  > `You can't edit field-level security for a required field, universally required field, or master-detail relationship field. Remove [Object.Field__c] from the permission set.`

  Required fields cannot have explicit FLS — the platform grants it automatically. Omit them entirely. Always confirm from the field's `*.field-meta.xml` that the field is not required (see Step 3 "What counts as required") before adding it; never assume.
- **Incorrect API names:** Using the wrong name or missing suffixes (e.g. missing `__c` for custom objects, fields, tabs) cause failure.

## Deployment

Deploy using Salesforce CLI