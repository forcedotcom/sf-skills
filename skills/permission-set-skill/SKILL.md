---
name: generate-permission-set-skill
description: Generate correct, deployable Salesforce permission set metadata with proper object, field, user, and app permissions. Use when generating permission set metadata.
license: Apache-2.0
compatibility: Salesforce Metadata API v60.0+
metadata:
  author: afv-library
  version: "1.0"
---

## When to Use This Skill

Use when you need to generate metadata for a permission set or need to grant additional permissions such as:
- Providing temporary or project-based access
- Enabling feature-specific permissions
- Implementing role-based access control
- Extending profile permissions for specific user groups

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
- Cannot set permissions on required fields, they are readable and editable by default
- For custom objects, read and use the object metadata file to determine correct names of fields and if they are required
- Use format `ObjectName.FieldName` for field references
- Both `readable` and `editable` can be true (editable implies readable)

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

**Tab visibility options:**
- `Visible`: Always shown
- `Available`: Available but not default
- `Hidden`: Not visible

**CRITICAL - Tab Naming:**
- Custom object tabs: MUST include the __c suffix (e.g., MyCustomObject__c)
- Standard object tabs: Use the object name without modification (e.g., Account, Contact)
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

## Validation Checklist

Before deploying, verify:
- [ ] All required fields (fullName, label, description) are set
- [ ] Object permissions follow least privilege principle
- [ ] No field permissions on required fields
- [ ] System permissions (ViewAllData, ModifyAllData) are reviewed
- [ ] No duplicate permissions within permission set
- [ ] Description clearly states intended use case
- [ ] Remove unnecessary comments, comments should be minimal and consice


## Deployment

Deploy using Salesforce CLI:
```bash
sf project deploy start --metadata-dir force-app/main/default/permissionsets
```

## Best Practices

- **Granularity**: Create focused permission sets for specific purposes
- **Documentation**: Maintain clear descriptions and naming
- **Security**: Never grant excessive permissions like ModifyAllData without justification

