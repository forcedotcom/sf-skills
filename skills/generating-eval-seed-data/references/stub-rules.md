# Stub Generation Rules

Rules for generating minimal seed-data stubs. Stubs declare what exists and what type
it is — nothing more.

---

## General Principles

- **Stubs, not full metadata**: generate the absolute minimum XML to declare a field,
  object, or class. No optional attributes, no invented values.
- **Only what gold references**: for picklists, include ONLY values explicitly named in
  the gold file. For objects, do not add fields beyond what gold uses.
- **No optional attributes**: omit `description`, `trackHistory`, `trackTrending`,
  `required`, `externalId`, `inlineHelpText`, `restricted`, `sorted`, `default`,
  `relationshipLabel`, and any other non-essential element.
- **Standard objects don't need definitions**: Account, Contact, Opportunity, Case, Lead,
  User, and other standard objects already exist. Only stub their custom fields (`__c`).
- **API version**: use `62.0` unless gold specifies otherwise.

---

## Custom Field Stubs

**Path**: `seed-data/objects/{ObjectName}/fields/{FieldApiName}.field-meta.xml`

Include ONLY these elements per field type:

| Field Type | Required Elements |
|-----------|------------------|
| Lookup | `fullName`, `label`, `type`, `referenceTo`, `relationshipName` |
| Master-Detail | `fullName`, `label`, `type`, `referenceTo`, `relationshipName` |
| Picklist | `fullName`, `label`, `type`, `valueSet` (only referenced values) |
| Text | `fullName`, `label`, `type`, `length` |
| Number | `fullName`, `label`, `type`, `precision`, `scale` |
| Currency | `fullName`, `label`, `type`, `precision`, `scale` |
| Percent | `fullName`, `label`, `type`, `precision`, `scale` |
| Date | `fullName`, `label`, `type` |
| DateTime | `fullName`, `label`, `type` |
| Checkbox | `fullName`, `label`, `type`, `defaultValue` |
| Email | `fullName`, `label`, `type` |
| Phone | `fullName`, `label`, `type` |
| Url | `fullName`, `label`, `type` |
| TextArea | `fullName`, `label`, `type` |
| LongTextArea | `fullName`, `label`, `type`, `length`, `visibleLines` |

### Picklist Value Rules

Only include picklist values that appear explicitly in the gold file. Common patterns:

| Gold Pattern | Extract |
|-------------|---------|
| `ISPICKVAL(Status__c, "UNPAID")` | `UNPAID` only |
| `IF(Stage__c = "Closed Won", ...)` | `Closed Won` only |
| `<value><fullName>Active</fullName>...</value>` | `Active` only |

Do NOT add values "for completeness." If the gold formula checks for `"UNPAID"`, do not
add `PAID`, `PARTIALLY_PAID`, or any other values.

---

## Custom Object Stubs

**Path**: `seed-data/objects/{ObjectApiName}/{ObjectApiName}.object-meta.xml`

Include ONLY these elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <label>{Object Label}</label>
    <nameField>
        <label>{Object Label} Name</label>
        <type>Text</type>
    </nameField>
    <pluralLabel>{Object Plural Label}</pluralLabel>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

Do NOT add `description`, `enableActivities`, `enableBulkApi`, `enableHistory`,
`enableReports`, `enableSearch`, or any other optional element.

---

## Apex Class Stubs

**Path**: `seed-data/classes/{ClassName}.cls` + `seed-data/classes/{ClassName}.cls-meta.xml`

The `.cls` file is an empty stub — class signature only:

```java
public class MyUtilClass {
}
```

For interfaces:
```java
public interface MyInterface {
}
```

For abstract classes:
```java
public abstract class MyBaseClass {
}
```

The `.cls-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

Do NOT generate method bodies, business logic, or implementations.

---

## Dependency Detection Patterns

| Gold Pattern | Dependency Type | Stub Needed |
|-------------|----------------|-------------|
| `Payment_Due_Date__c` in formula | Custom field | Date field stub |
| `AssetProvided__r.Name` in formula | Lookup relationship | Lookup field stub for `AssetProvided__c` |
| `ISPICKVAL(Status__c, "X")` | Picklist field | Picklist stub with value `X` |
| `<referenceTo>Animal__c</referenceTo>` | Custom object | Object stub for `Animal__c` |
| `extends BaseHandler` | Apex parent class | Class stub for `BaseHandler` |
| `implements Queueable` | Standard interface | No stub needed (standard) |
| `Account.Name` | Standard object + field | No stub needed |
| `CustomObj__c.Custom_Field__c` | Custom field on custom object | Both object and field stubs |

---

## Common Validation Errors and Fixes

| Error Pattern | Fix |
|--------------|-----|
| `Field does not exist: FieldName__c` | Add the missing field stub |
| `Invalid type: ObjectName__c` | Add the custom object stub |
| `Missing required field: X` | Add the required XML element |
| `Invalid picklist value` | Add the missing value to the picklist stub |
| `Relationship not found` | Add the lookup field that defines the relationship |
| `apiVersion is required` | Add `<apiVersion>62.0</apiVersion>` |
