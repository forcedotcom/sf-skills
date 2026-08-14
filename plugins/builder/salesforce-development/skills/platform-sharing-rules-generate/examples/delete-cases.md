# Sharing Rules — Delete Test Cases

Structured test scenarios for delete operations. Each test case defines an input, the expected behavior, and the expected output.

> **Important:** A normal `sf project deploy start` is additive and will NOT remove a sharing rule from the org. Deleting a rule from the org requires a destructive deployment using `destructiveChanges.xml` with the `--post-destructive-changes` flag.

---

## TC-09: Delete a single rule (other rules remain)

**Input:**
- Object: `Property__c` (file contains 2 rules)
- Delete rule: `ShareActivePropertiesWithRegionalManager`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Locates the rule in the retrieved file
3. Removes the entire `<sharingCriteriaRules>` block for that rule from the local file
4. Other rules in the file remain intact
5. Creates `destructiveChanges.xml` with:
   ```xml
   <types>
       <members>Property__c.ShareActivePropertiesWithRegionalManager</members>
       <name>SharingCriteriaRule</name>
   </types>
   ```
6. Deploys with: `sf project deploy start --manifest package.xml --post-destructive-changes destructiveChanges.xml --target-org <org>`

**Expected output:** Local file retains `<SharingRules>` root and all other rules, with the deleted rule's block completely removed. Org has the rule removed via destructive deployment.

---

## TC-10: Delete the last rule in a file

**Input:**
- Object: `Listing__c` (file contains only 1 rule)
- Delete rule: `SharePublishedListingsWithSiteGuest`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Locates the rule — confirms it is the only rule in the file
3. Removes the local file entirely
4. Creates `destructiveChanges.xml` with:
   ```xml
   <types>
       <members>Listing__c.SharePublishedListingsWithSiteGuest</members>
       <name>SharingGuestRule</name>
   </types>
   ```
5. Deploys with: `sf project deploy start --manifest package.xml --post-destructive-changes destructiveChanges.xml --target-org <org>`

**Expected output:** File `Listing__c.sharingRules-meta.xml` no longer exists locally. Org has the rule removed via destructive deployment.

---

## TC-12: Delete attempt on non-existent rule

**Input:**
- Object: `Property__c`
- Delete rule: `RuleThatDoesNotExist`

**Expected behavior:**
1. Retrieves the latest sharing rules from the org
2. Searches for the rule by `<fullName>` in the retrieved file
3. Rule not found — reports error
4. Lists available rules and asks user to clarify

**Expected output:** No file changes. Error message listing available rule names.
