# Error Handling — API and Data Issues

Recovery strategies for common errors during hierarchy creation.

## API Rate Limit Errors

**Error**: `API rate limit exceeded` or HTTP 429

**When it occurs**: During bulk BusinessProfile creation (Step 8) or when creating/patching many Accounts in rapid succession (Step 7)

**Resolution**:

1. **Track what succeeded**: Parse API response to identify which records were created successfully
2. **Retry failed records only**: Wait 2 seconds, then retry only the records that failed
3. **Exponential backoff**: If retry fails, wait 4 seconds, then 8 seconds (max 3 retries)
4. **Report status**: Print which records succeeded vs. failed after each attempt

**Example**:
```text
⚠️ API rate limit hit during BusinessProfile creation

Status: 21 of 23 BusinessProfiles created
Failed: 2 department-level profiles
  - Nursing Department (under School of Health Sciences, Main Campus)
  - Allied Health Department (under School of Health Sciences, Main Campus)

Retrying in 2 seconds...
```text

After retry:
```text
Retry successful — all 23 BusinessProfiles created
```text

**Implementation**: Retry with exponential backoff (sleep 2s, 4s, 8s between attempts). For each retry:
- `mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/BusinessProfile", "method": "POST", "body": {"AccountId": "[Account ID]"}})`

---

## Duplicate Record Errors

**Error**: `DUPLICATE_VALUE: duplicate value found`

**When it occurs**: Creating Account with name that already exists at the same hierarchy level

**Resolution**:

1. **Check if existing record is part of this hierarchy**: Look it up in `existingTree` (loaded in Step 5 via the `ChildAccounts` GET, or a SOQL `/query` — both are routable) — match on name under the intended parent.
2. **If yes (reused / leftover from previous run)**: Reuse the existing Account ID instead of creating new — this is the normal update-mode path
3. **If no (different hierarchy)**: Append disambiguating suffix to name (e.g., campus name in parentheses)

**Example**:
```text
⚠️ Account "School of Arts & Sciences" already exists

Found existing record under: North Campus
Creating under: Main Campus

Resolution: Renaming to "School of Arts & Sciences (Main Campus)"
```text

---

## Parent Record Not Found

**Error**: `INVALID_FIELD: ParentId — invalid cross-reference key`

**When it occurs**: Attempting to create child record before parent exists

**Root cause**: Workflow steps executed out of order, or API creation for parent failed silently

**Resolution**:

1. **Verify parent was created**: Check that the parent Account ID exists in `accountMap` (created this run) or in `existingTree` (reused in update mode)
2. **If missing**: Re-run creation for that parent level, then retry child creation
3. **If parent ID present but reference fails**: Query Salesforce to confirm parent record exists: `mcp__headless-360__dispatch_readonly({"url": "/services/data/v68.0/sobjects/Account/$PARENT_ID", "method": "GET"})`

**Prevention**: Follow workflow step order strictly — create parents before children.

---

## BusinessProfile Field Not Found

**Error**: `INVALID_FIELD: No such column 'AccountId' on sobject of type BusinessProfile`

**When it occurs**: User's org does not have Education Cloud provisioned, or BusinessProfile object not available

**Resolution**:

1. **Stop workflow**: Cannot proceed without Education Cloud
2. **Report to user**:
   ```text
   ⚠️ BusinessProfile creation failed — Education Cloud may not be provisioned

   Error: AccountId field not found on BusinessProfile object

   This usually means:
   • Education Cloud managed package not installed
   • User lacks Education Cloud license
   • Org does not have Education Cloud feature enabled

   Check prerequisites: IndustriesEducation.userHasEducationCloudAccess

   Would you like to proceed with Account creation only (no BusinessProfiles)?
   ```

3. **Fallback**: Offer to create Account hierarchy without BusinessProfiles

---

## Missing Fields in API Response

**Error**: sObject API POST returns success but does not include `id` field in response

**When it occurs**: Rare API issue or malformed response

**Resolution**:

1. **Prefer capturing `body.id` from the create response** — it is present on normal `201` responses. A SOQL `/query` lookup by Name under the intended parent also works as a fallback if the create response was lost.
2. **If `body.id` truly missing on a `201`**: do NOT blindly re-POST (risks a duplicate Account). Report to user with the node Name + intended parent Id and ask how to proceed (re-create vs. locate manually in the org).
3. **Log issue**: Print warning that the API response was incomplete, including the node Name and parent Id.

---

## Timeout Errors

**Error**: `ERROR: Request timeout` or `ETIMEDOUT`

**When it occurs**: Creating many records in quick succession, or org has slow custom triggers

**Resolution**:

1. **Batch size**: Create records in smaller batches (max 10 per batch) with 1-second pause between batches
2. **Retry failed records**: Use same retry logic as rate limit errors (exponential backoff)
3. **Identify slow triggers**: If timeout persists, check if Account or BusinessProfile has custom Apex triggers — these can slow creation

**Batching**: Split into batches of max 10 records, 1-second pause between batches. For each record in a batch:
- `mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/Account", "method": "POST", "body": {"Name": "[Node name]", "RecordTypeId": "[recordTypeId resolved in Step 3.5]", "ParentId": "[Parent node's Account ID]"}})`
  (Use `RecordTypeId` with the runtime-resolved value — never a hardcoded Id. Omit `ParentId` for the System node.)

---

## Incomplete Parsing (Zero Records at Level)

**Issue**: Parser extracts zero colleges or zero departments for a campus

**When it occurs**: PDF/HTML parsing misses section, or input format is non-standard

**Resolution**:

1. **Confirm with user before creating**: Show parsed structure and ask if zero records at that level is correct
2. **Offer to continue anyway**: User may add colleges/departments manually later
3. **Suggest simplified input**: If parsing quality is poor, ask user to provide plain text description instead

**Example confirmation**:
```text
I extracted this structure:

System: Riverside Community College System
├─ Campus: Main Campus
│  └─ (No colleges found)
└─ Campus: North Campus
   ├─ College: Technical Education
   └─ College: School of Arts & Sciences

Main Campus has no colleges — is this correct, or should I look for college info elsewhere?

[1] Correct — proceed
[2] Missing data — I'll provide college list
```text

---

## General Error Handling Pattern

For any unexpected API error:

1. **Capture full error message**: Log complete error text from API response
2. **Identify which record failed**: Include record Name and hierarchy level in error report
3. **Report status to user**: Show what succeeded so far vs. what failed
4. **Offer retry or manual fix**: Ask user if they want to retry, skip failed record, or provide corrected info
5. **Do not fail silently**: Every error must be reported to user with context

**Example error report**:
```text
⚠️ Error creating Department Account

Record: Computer Science Department
Parent: Technical Education (College)
Error: FIELD_CUSTOM_VALIDATION_EXCEPTION: Name must be unique within College

Status: 11 of 12 Department Accounts created successfully

Resolution options:
[1] Rename to "Computer Science Department (Tech Ed)" and retry
[2] Skip this department
[3] I'll provide a different name
```text
