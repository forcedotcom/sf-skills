# Example: Get OWD Output

## Single Object Query

**User prompt:** "What are the org-wide defaults for Account?"

**Expected output format:**

| Object | Internal Access | External Access |
|--------|----------------|-----------------|
| Account | Public Read/Write | Private |

## Multiple Objects Query

**User prompt:** "Show me all org-wide defaults"

**Expected output format:**

| Object | Internal Access | External Access |
|--------|----------------|-----------------|
| Account | Public Read/Write | Private |
| Contact | Controlled by Parent | Controlled by Parent |
| Opportunity | Private | Private |
| Case | Public Read/Write/Transfer | Private |
| Lead | Public Read/Write/Transfer | Public Read Only |
| Campaign | Public Full Access | Private |
| Invoice__c | Private | Private |
| Project__c | Public Read Only | Private |

## Custom Object Query

**User prompt:** "Get the OWD for Invoice__c"

**Expected output format:**

| Object | Internal Access | External Access |
|--------|----------------|-----------------|
| Invoice__c | Private | Private |
