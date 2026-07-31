# Sharing Rules — Delete Test Cases

Structured test scenarios for delete operations and confirmation flow. Each test case defines an input, the expected behavior, and the expected output.

---

## TC-09: Delete a single rule (other rules remain)

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

## TC-10: Delete the last rule in a file

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

## TC-11: Delete with user declining confirmation

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

## TC-12: Delete attempt on non-existent rule

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
