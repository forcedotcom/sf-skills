# Sharing Rule Types — Complete XML Schema

Reference for all supported sharing rule types. Read this before generating any rule.

---

## File Structure

All sharing rules for a single object live in one file:

```xml
<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml
```

The root element wraps all rule types:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <!-- One or more rule elements of any type -->
</SharingRules>
```

---

## Criteria-Based Rules (`sharingCriteriaRules`)

Share records that match specific field conditions with a target role, group, or portal role.

```xml
<sharingCriteriaRules>
    <fullName>RuleApiName</fullName>
    <accessLevel>Read</accessLevel>
    <includeRecordsOwnedByAll>true</includeRecordsOwnedByAll>
    <label>Human Readable Rule Name</label>
    <sharedTo>
        <role>RoleDeveloperName</role>
    </sharedTo>
    <criteriaItems>
        <field>FieldApiName</field>
        <operation>equals</operation>
        <value>FieldValue</value>
    </criteriaItems>
</sharingCriteriaRules>
```

### Required Elements

| Element | Type | Notes |
|---------|------|-------|
| `fullName` | string | PascalCase API name, unique within the object's sharing rules |
| `accessLevel` | enum | `Read` or `Edit` |
| `includeRecordsOwnedByAll` | boolean | `true` = all records matching criteria; `false` = only records not owned by the sharedTo target |
| `label` | string | Human-readable name displayed in Setup |
| `sharedTo` | SharedTo | Target users/roles/groups (see SharedTo section below) |
| `criteriaItems` | FilterItem[] | One or more field criteria (see FilterItem section below) |

### Optional Elements

| Element | Type | Notes |
|---------|------|-------|
| `booleanFilter` | string | Custom logic for multiple criteria (e.g., `"1 AND (2 OR 3)"`) |
| `description` | string | Optional description |
| `accountSettings` | AccountSettings | **Required if object is Account** |

---

## Guest Rules (`sharingGuestRules`)

Share records with Experience Site guest (unauthenticated) users. The `sharedTo` MUST use `<guestUser>` — never `<role>` or `<group>`.

```xml
<sharingGuestRules>
    <fullName>ShareRecordsWithSiteGuest</fullName>
    <accessLevel>Read</accessLevel>
    <includeHVUOwnedRecords>false</includeHVUOwnedRecords>
    <label>Share Records With Site Guest</label>
    <sharedTo>
        <guestUser>Site Guest User CommunityNickname</guestUser>
    </sharedTo>
    <criteriaItems>
        <field>Status__c</field>
        <operation>equals</operation>
        <value>Published</value>
    </criteriaItems>
</sharingGuestRules>
```

### Required Elements

| Element | Type | Notes |
|---------|------|-------|
| `fullName` | string | PascalCase API name |
| `accessLevel` | enum | `Read` or `Edit` |
| `includeHVUOwnedRecords` | boolean | Whether to include records owned by high-volume users |
| `label` | string | Human-readable name |
| `sharedTo` | SharedTo | Must contain `<guestUser>` with the CommunityNickname |
| `criteriaItems` | FilterItem[] | One or more field criteria |

### Finding the Guest User Nickname

Query the org to find the correct community nickname:

```sql
SELECT CommunityNickname, Name FROM User WHERE UserType = 'Guest' AND IsActive = true
```

The `CommunityNickname` value goes in the `<guestUser>` element.

---

## Owner Rules (`sharingOwnerRules`)

Share records based on record ownership — records owned by users in one role/group are shared with users in another role/group.

```xml
<sharingOwnerRules>
    <fullName>ShareManagerRecordsWithTeam</fullName>
    <accessLevel>Read</accessLevel>
    <label>Share Manager Records With Team</label>
    <sharedFrom>
        <role>Manager</role>
    </sharedFrom>
    <sharedTo>
        <roleAndSubordinates>TeamLead</roleAndSubordinates>
    </sharedTo>
</sharingOwnerRules>
```

### Required Elements

| Element | Type | Notes |
|---------|------|-------|
| `fullName` | string | PascalCase API name |
| `accessLevel` | enum | `Read` or `Edit` |
| `label` | string | Human-readable name |
| `sharedFrom` | SharedTo | Source — whose records are being shared |
| `sharedTo` | SharedTo | Target — who gets access |

---

## SharedTo Element

The `<sharedTo>` (and `<sharedFrom>` for owner rules) element specifies the target. Use exactly ONE of these child elements:

| Element | Use for |
|---------|---------|
| `<role>RoleDeveloperName</role>` | A specific role |
| `<roleAndSubordinates>RoleName</roleAndSubordinates>` | A role and all subordinates in the hierarchy |
| `<group>GroupDeveloperName</group>` | A public group |
| `<guestUser>CommunityNickname</guestUser>` | Experience Site guest user (guest rules only) |
| `<portalRole>PortalRoleName</portalRole>` | Portal user role |
| `<portalRoleAndSubordinates>PortalRoleName</portalRoleAndSubordinates>` | Portal role + subordinates |
| `<allInternalUsers>AllInternalUsers</allInternalUsers>` | All internal users |
| `<allCustomerPortalUsers>AllCustomerPortalUsers</allCustomerPortalUsers>` | All customer portal users |

---

## FilterItem (criteriaItems)

Each `<criteriaItems>` element specifies one condition:

```xml
<criteriaItems>
    <field>FieldApiName</field>
    <operation>equals</operation>
    <value>MatchValue</value>
</criteriaItems>
```

| Element | Required | Notes |
|---------|----------|-------|
| `field` | Yes | API name of the field (no object prefix) |
| `operation` | Yes | One of: `equals`, `notEqual`, `lessThan`, `greaterThan`, `lessOrEqual`, `greaterOrEqual`, `contains`, `notContain`, `startsWith` |
| `value` | Conditional | Required unless operation is a null check |

Multiple `<criteriaItems>` are ANDed by default. Use `<booleanFilter>` for custom logic.

---

## AccountSettings (Account object only)

When creating sharing rules for the Account object, you MUST include `<accountSettings>`:

```xml
<accountSettings>
    <caseAccessLevel>None</caseAccessLevel>
    <contactAccessLevel>None</contactAccessLevel>
    <opportunityAccessLevel>None</opportunityAccessLevel>
</accountSettings>
```

| Element | Valid Values | Notes |
|---------|-------------|-------|
| `caseAccessLevel` | `None`, `Read`, `Edit` | Access to related Cases |
| `contactAccessLevel` | `None`, `Read`, `Edit` | Access to related Contacts |
| `opportunityAccessLevel` | `None`, `Read`, `Edit` | Access to related Opportunities |

Place `<accountSettings>` inside the rule element, after `<accessLevel>`.
