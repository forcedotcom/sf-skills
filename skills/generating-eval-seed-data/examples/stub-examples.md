# Seed-Data Stub Examples

Input/output examples showing gold file analysis and the resulting seed-data stubs.

---

## Example 1: Formula Field with Date and Picklist Dependencies

**Gold file**: `gold/objects/Contract/fields/Payment_Overdue__c.field-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Payment_Overdue__c</fullName>
    <label>Payment Overdue</label>
    <type>Text</type>
    <formula>IF(AND(Payment_Due_Date__c &lt; TODAY(), ISPICKVAL(Payment_Status__c, "UNPAID")), "PAYMENT OVERDUE", null)</formula>
    <formulaTreatBlanksAs>BlankAsZero</formulaTreatBlanksAs>
    <length>20</length>
</CustomField>
```

**Analysis**: Formula references `Payment_Due_Date__c` (Date) and `Payment_Status__c`
(Picklist with value `UNPAID`).

**Generated stubs**:

`seed-data/objects/Contract/fields/Payment_Due_Date__c.field-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Payment_Due_Date__c</fullName>
    <label>Payment Due Date</label>
    <type>Date</type>
</CustomField>
```

`seed-data/objects/Contract/fields/Payment_Status__c.field-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Payment_Status__c</fullName>
    <label>Payment Status</label>
    <type>Picklist</type>
    <valueSet>
        <valueSetDefinition>
            <value>
                <fullName>UNPAID</fullName>
                <label>UNPAID</label>
            </value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

Only `UNPAID` is included — no other values.

---

## Example 2: Flow Referencing Custom Objects

**Gold file**: A Flow XML that triggers on `Adoption__c` record creation and references
a Lookup to `Animal__c`.

**Generated stubs**:

`seed-data/objects/Adoption__c/Adoption__c.object-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <label>Adoption</label>
    <nameField>
        <label>Adoption Name</label>
        <type>Text</type>
    </nameField>
    <pluralLabel>Adoptions</pluralLabel>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

`seed-data/objects/Animal__c/Animal__c.object-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <label>Animal</label>
    <nameField>
        <label>Animal Name</label>
        <type>Text</type>
    </nameField>
    <pluralLabel>Animals</pluralLabel>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

`seed-data/objects/Adoption__c/fields/Animal__c.field-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Animal__c</fullName>
    <label>Animal</label>
    <type>Lookup</type>
    <referenceTo>Animal__c</referenceTo>
    <relationshipName>Adoptions</relationshipName>
</CustomField>
```

---

## Example 3: Apex Class with Parent Class Dependency

**Gold file**: `gold/classes/OrderProcessor.cls` extends `BaseProcessor`.

**Generated stubs**:

`seed-data/classes/BaseProcessor.cls`:
```java
public abstract class BaseProcessor {
}
```

`seed-data/classes/BaseProcessor.cls-meta.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

Empty stub — no method bodies or implementations.
