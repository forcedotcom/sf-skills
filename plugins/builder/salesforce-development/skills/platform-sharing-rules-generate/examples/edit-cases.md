# Sharing Rules — Edit Test Cases

Structured test scenarios for edit operations. Each test case defines an input, the expected behavior, and the expected output.

---

## TC-05: Edit access level of an existing rule

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

## TC-06: Edit shared-to target of an existing rule

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

## TC-07: Edit criteria of an existing rule

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
