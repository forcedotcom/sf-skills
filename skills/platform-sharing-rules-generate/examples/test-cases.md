# Sharing Rules — Test Cases

Structured test scenarios for create, edit, and delete operations. Each test case defines an input, the expected behavior, and the expected output.

---

## Create Operations

### TC-01: Create a criteria-based sharing rule

**Input:**
- Object: `Property__c`
- Rule type: criteria-based
- Share with: role `RegionalManager`
- Access level: Read
- Criteria: `Status__c` equals `Active`

**Expected behavior:**
1. Discovers SFDX project path and checks for existing `Property__c.sharingRules-meta.xml`
2. Presents confirmation summary to user and waits for approval
3. After confirmation, writes the file

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

### TC-02: Create a guest user sharing rule

**Input:**
- Object: `Listing__c`
- Rule type: guest
- Share with: guest user with CommunityNickname `PropertySiteGuest`
- Access level: Read
- Criteria: `Published__c` equals `true`

**Expected behavior:**
1. Discovers project path and checks for existing file
2. Queries org for guest user nickname if not provided
3. Presents confirmation summary and waits for approval
4. After confirmation, writes file using `<guestUser>` (not `<role>` or `<group>`)

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

### TC-03: Create an Account owner-based sharing rule

**Input:**
- Object: `Account`
- Rule type: owner-based
- Share from: role `SalesDirector`
- Share to: role and subordinates `SalesTeam`
- Access level: Edit

**Expected behavior:**
1. Discovers project path, checks for existing Account sharing rules
2. Includes `<accountSettings>` with all three sub-elements defaulted to `None`
3. Presents confirmation summary and waits for approval
4. After confirmation, writes the file

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

### TC-04: Append a rule to an existing file

**Input:**
- Object: `Property__c` (file already exists with TC-01's rule)
- Rule type: criteria-based
- Share with: group `AllAgents`
- Access level: Edit
- Criteria: `Price__c` greaterThan `1000000`

**Expected behavior:**
1. Reads existing file and finds TC-01's rule already present
2. Does not duplicate existing rule
3. Presents confirmation showing the new rule will be appended
4. After confirmation, appends new rule inside existing `<SharingRules>` root

**Expected output:** File contains both TC-01's rule AND the new rule within the same `<SharingRules>` element.

---

## Edit Operations

### TC-05: Edit access level of an existing rule

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: access level from `Read` to `Edit`

**Expected behavior:**
1. Locates the rule by `<fullName>` in the existing file
2. Presents confirmation showing current vs. proposed change:
   > **Operation:** Edit
   > **Object:** `Property__c`
   > **Rule:** `ShareActivePropertiesWithRegionalManager` (Share Active Properties With Regional Manager)
   > **Changes:** accessLevel: Read → Edit
   >
   > Proceed? (yes / no / edit)
3. Waits for user confirmation
4. After confirmation, modifies only `<accessLevel>` — all other elements unchanged

**Expected output (changed portion):**
```xml
<accessLevel>Edit</accessLevel>
```
All other elements (`fullName`, `label`, `sharedTo`, `criteriaItems`, `includeRecordsOwnedByAll`) remain identical.

---

### TC-06: Edit shared-to target of an existing rule

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: shared-to from role `RegionalManager` to group `PropertyViewers`

**Expected behavior:**
1. Locates the rule in the file
2. Presents confirmation showing:
   > **Changes:** sharedTo: role `RegionalManager` → group `PropertyViewers`
3. Waits for confirmation
4. Replaces `<sharedTo>` content only

**Expected output (changed portion):**
```xml
<sharedTo>
    <group>PropertyViewers</group>
</sharedTo>
```

---

### TC-07: Edit criteria of an existing rule

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: update criteria from `Status__c equals Active` to `Status__c equals Active` AND `Region__c equals West`

**Expected behavior:**
1. Locates the rule in the file
2. Presents confirmation showing current criteria vs. proposed criteria
3. Waits for confirmation
4. Replaces `<criteriaItems>` elements

**Expected output (changed portion):**
```xml
<criteriaItems>
    <field>Status__c</field>
    <operation>equals</operation>
    <value>Active</value>
</criteriaItems>
<criteriaItems>
    <field>Region__c</field>
    <operation>equals</operation>
    <value>West</value>
</criteriaItems>
```

---

### TC-08: Edit attempt on non-existent rule

**Input:**
- Object: `Property__c`
- Target rule: `NonExistentRule`
- Change: access level to `Edit`

**Expected behavior:**
1. Searches for the rule by `<fullName>` in the file
2. Rule not found — reports error to user
3. Suggests listing available rules in the file and asks user to clarify

**Expected output:** No file changes. Error message listing available rule names in the file.

---

## Delete Operations

### TC-09: Delete a single rule (other rules remain)

**Input:**
- Object: `Property__c` (file contains 2 rules)
- Delete rule: `ShareActivePropertiesWithRegionalManager`

**Expected behavior:**
1. Locates the rule in the file
2. Presents confirmation:
   > **Operation:** Delete
   > **Object:** `Property__c`
   > **Rule:** `ShareActivePropertiesWithRegionalManager` (Share Active Properties With Regional Manager)
   > **Changes:** Remove this criteria-based sharing rule entirely. 1 other rule(s) will remain in the file.
   >
   > Proceed? (yes / no / edit)
3. Waits for confirmation
4. Removes the entire `<sharingCriteriaRules>` block for that rule
5. Other rules in the file remain intact

**Expected output:** File retains `<SharingRules>` root and all other rules, with the deleted rule's block completely removed.

---

### TC-10: Delete the last rule in a file

**Input:**
- Object: `Listing__c` (file contains only 1 rule)
- Delete rule: `SharePublishedListingsWithSiteGuest`

**Expected behavior:**
1. Locates the rule — confirms it is the only rule in the file
2. Presents confirmation warning that the entire file will be removed:
   > **Operation:** Delete
   > **Object:** `Listing__c`
   > **Rule:** `SharePublishedListingsWithSiteGuest` (Share Published Listings With Site Guest)
   > **Changes:** Remove this guest sharing rule. This is the last rule — the entire file `Listing__c.sharingRules-meta.xml` will be deleted.
   >
   > Proceed? (yes / no / edit)
3. Waits for confirmation
4. Deletes the entire file

**Expected output:** File `Listing__c.sharingRules-meta.xml` no longer exists.

---

### TC-11: Delete with user declining confirmation

**Input:**
- Object: `Account`
- Delete rule: `ShareDirectorAccountsWithSalesTeam`
- User response to confirmation: "no"

**Expected behavior:**
1. Locates the rule
2. Presents confirmation
3. User says "no"
4. Aborts — no changes written

**Expected output:** No file changes. Acknowledgment that the operation was cancelled.

---

### TC-12: Delete attempt on non-existent rule

**Input:**
- Object: `Property__c`
- Delete rule: `RuleThatDoesNotExist`

**Expected behavior:**
1. Searches for the rule by `<fullName>` in the file
2. Rule not found — reports error
3. Lists available rules and asks user to clarify

**Expected output:** No file changes. Error message listing available rule names.

---

## Confirmation Flow Tests

### TC-13: User confirms with "yes"

**Input:** Any create/edit/delete operation where user responds "yes" to confirmation.

**Expected behavior:** Changes are written to disk as presented in the summary.

---

### TC-14: User responds with "edit" and provides feedback

**Input:**
- Create operation for a criteria rule
- User responds "edit" to confirmation with: "Change the access level to Edit instead of Read"

**Expected behavior:**
1. Original summary presented
2. User says "edit" with feedback
3. Incorporates feedback (changes `accessLevel` to `Edit`)
4. Re-presents updated summary
5. Waits for new confirmation before writing

---

### TC-15: User declines with "no"

**Input:** Any create/edit/delete operation where user responds "no" to confirmation.

**Expected behavior:** No file changes. Operation aborted with acknowledgment.

---

## Edge Cases

### TC-16: Edit that would change rule type

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager` (criteria rule)
- Change: convert to owner-based rule

**Expected behavior:**
1. Detects that the change would alter the rule type
2. Informs user this is not supported as an edit
3. Suggests: delete the existing rule and create a new one with the desired type

**Expected output:** No file changes. Guidance to user about delete + create workflow.

---

### TC-17: Create rule with duplicate fullName

**Input:**
- Object: `Property__c` (file already contains rule `ShareActivePropertiesWithRegionalManager`)
- Create a new rule also named `ShareActivePropertiesWithRegionalManager`

**Expected behavior:**
1. Reads existing file, finds duplicate `<fullName>`
2. Informs user of the conflict
3. Suggests an alternative name or asks user to choose

**Expected output:** No file changes until conflict is resolved.
