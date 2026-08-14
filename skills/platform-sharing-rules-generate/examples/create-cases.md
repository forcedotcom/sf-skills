# Sharing Rules — Create Test Cases

Structured test scenarios for create operations. Each test case defines an input, the expected behavior, and the expected output.

---

## TC-01: Create a criteria-based sharing rule

**Input:**
- Object: `Property__c`
- Rule type: criteria-based
- Share with: role `RegionalManager`
- Access level: Read
- Criteria: `Status__c` equals `Active`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Checks for existing `Property__c.sharingRules-meta.xml` — no duplicates found
3. Writes the file

**Expected output:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingCriteriaRules>
        <fullName>ShareActivePropertiesWithRegionalManager</fullName>
        <accessLevel>Read</accessLevel>
        <includeRecordsOwnedByAll>true</includeRecordsOwnedByAll>
        <label>Share Active Properties With Regional Manager</label>
        <sharedTo>
            <role>RegionalManager</role>
        </sharedTo>
        <criteriaItems>
            <field>Status__c</field>
            <operation>equals</operation>
            <value>Active</value>
        </criteriaItems>
    </sharingCriteriaRules>
</SharingRules>
```

---

## TC-02: Create a guest user sharing rule

**Input:**
- Object: `Listing__c`
- Rule type: guest
- Share with: guest user with CommunityNickname `PropertySiteGuest`
- Access level: Read
- Criteria: `Published__c` equals `true`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Queries org for guest user nickname if not provided
3. Writes file using `<guestUser>` (not `<role>` or `<group>`)

**Expected output:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingGuestRules>
        <fullName>SharePublishedListingsWithSiteGuest</fullName>
        <accessLevel>Read</accessLevel>
        <includeHVUOwnedRecords>false</includeHVUOwnedRecords>
        <label>Share Published Listings With Site Guest</label>
        <sharedTo>
            <guestUser>PropertySiteGuest</guestUser>
        </sharedTo>
        <criteriaItems>
            <field>Published__c</field>
            <operation>equals</operation>
            <value>true</value>
        </criteriaItems>
    </sharingGuestRules>
</SharingRules>
```

---

## TC-03: Create an Account owner-based sharing rule

**Input:**
- Object: `Account`
- Rule type: owner-based
- Share from: role `SalesDirector`
- Share to: role and subordinates `SalesTeam`
- Access level: Edit

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Checks for existing Account sharing rules
3. Includes `<accountSettings>` with all three sub-elements defaulted to `None`
4. Writes the file

**Expected output:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingOwnerRules>
        <fullName>ShareDirectorAccountsWithSalesTeam</fullName>
        <accessLevel>Edit</accessLevel>
        <accountSettings>
            <caseAccessLevel>None</caseAccessLevel>
            <contactAccessLevel>None</contactAccessLevel>
            <opportunityAccessLevel>None</opportunityAccessLevel>
        </accountSettings>
        <label>Share Director Accounts With Sales Team</label>
        <sharedFrom>
            <role>SalesDirector</role>
        </sharedFrom>
        <sharedTo>
            <roleAndSubordinates>SalesTeam</roleAndSubordinates>
        </sharedTo>
    </sharingOwnerRules>
</SharingRules>
```

---

## TC-04: Append a rule to an existing file

**Input:**
- Object: `Property__c` (org already contains TC-01's rule)
- Rule type: criteria-based
- Share with: group `AllAgents`
- Access level: Edit
- Criteria: `Price__c` greaterThan `1000000`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Reads existing file and finds TC-01's rule already present
3. Does not duplicate existing rule
4. Appends new rule inside existing `<SharingRules>` root

**Expected output:** File contains both TC-01's rule AND the new rule within the same `<SharingRules>` element.

---

## TC-17: Create rule with duplicate fullName

**Input:**
- Object: `Property__c` (org already contains rule `ShareActivePropertiesWithRegionalManager`)
- Create a new rule also named `ShareActivePropertiesWithRegionalManager`

**Expected behavior:**
1. Retrieves from org, reads file, finds duplicate `<fullName>`
2. Informs user of the conflict
3. Suggests an alternative name or asks user to choose

**Expected output:** No file changes until conflict is resolved.
