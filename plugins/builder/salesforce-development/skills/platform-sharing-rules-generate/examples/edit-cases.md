# Sharing Rules — Edit Test Cases

Structured test scenarios for edit operations. Each test case defines an input, the expected behavior, and the expected output.

---

## TC-05: Edit access level of an existing rule

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: access level from `Read` to `Edit`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Locates the rule by `<fullName>` in the retrieved file
3. Modifies only `<accessLevel>` — all other elements unchanged

**Expected output (changed portion):**
```xml
<accessLevel>Edit</accessLevel>
```
All other elements (`fullName`, `label`, `sharedTo`, `criteriaItems`, `includeRecordsOwnedByAll`) remain identical.

---

## TC-06: Edit shared-to target of an existing rule (UNSUPPORTED)

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: shared-to from role `RegionalManager` to group `PropertyViewers`

**Expected behavior:**
1. Detects that the requested change targets `<sharedTo>`, which cannot be edited in place
2. Refuses the edit and informs the user that the platform does not support modifying `sharedTo` or `sharedFrom` on an existing rule
3. Suggests: delete the existing rule and create a new one with the desired sharing target

**Expected output:** No file changes. Guidance to user about delete + create workflow.

> **Note:** The same restriction applies to `<sharedFrom>` on owner-based rules. Any change to the sharing source or target requires delete + create.

---

## TC-07: Edit criteria of an existing rule

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager`
- Change: update criteria from `Status__c equals Active` to `Status__c equals Active` AND `Region__c equals West`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Locates the rule in the retrieved file
3. Replaces `<criteriaItems>` elements

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

## TC-08: Edit attempt on non-existent rule

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

## TC-16: Edit that would change rule type

**Input:**
- Object: `Property__c`
- Target rule: `ShareActivePropertiesWithRegionalManager` (criteria rule)
- Change: convert to owner-based rule

**Expected behavior:**
1. Detects that the change would alter the rule type
2. Informs user this is not supported as an edit
3. Suggests: delete the existing rule and create a new one with the desired type

**Expected output:** No file changes. Guidance to user about delete + create workflow.
