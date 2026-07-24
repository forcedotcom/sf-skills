# Example: Update OWD Output

## Standard Object Update

**User prompt:** "Change Account OWD to Private"

**Expected output format:**

### OWD Updated Successfully

| Object | Field | Before | After |
|--------|-------|--------|-------|
| Account | Internal Access | Public Read/Write | Private |
| Account | External Access | Private | Private |

> **Note:** Sharing recalculation has been triggered. This may take time on large orgs. Check Setup > Sharing Settings to monitor progress.

## Custom Object Update

**User prompt:** "Set Invoice__c org-wide default to Public Read Only for internal and Private for external"

**Expected output format:**

### OWD Updated Successfully

| Object | Field | Before | After |
|--------|-------|--------|-------|
| Invoice__c | Internal Access | Private | Public Read Only |
| Invoice__c | External Access | Private | Private |

## Update with Warning

**User prompt:** "Change Opportunity OWD to Public Read/Write"

**Expected output format:**

### OWD Updated Successfully

| Object | Field | Before | After |
|--------|-------|--------|-------|
| Opportunity | Internal Access | Private | Public Read/Write |
| Opportunity | External Access | Private | Private |

> **Warning:** Opening access from Private to Public Read/Write means all users will be able to view and edit all Opportunity records regardless of ownership. Ensure this aligns with your security requirements.
