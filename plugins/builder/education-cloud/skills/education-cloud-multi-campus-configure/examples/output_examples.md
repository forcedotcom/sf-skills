# Example Output Structures

## Step 6 — pre-write preview templates

New setup:
```text
About to create:
• [N] Account records across [M] levels
  - System: 1
  - [Level 1 name]: [count]
  ...
• [N] BusinessProfile records (1 per new Account)
• RecordType: [recordTypeDeveloperName]
```

Update/reconcile — show the delta explicitly:
```text
Reconcile plan (update mode):
• Create: [C] new Accounts  ([list level: count])
• Rename: [R] Accounts      ([old → new])
• Move:   [V] Accounts      ([node → new parent])
• Unchanged (reused): [U] Accounts
• Extra in org, NOT touched: [E]  ([list])
• BusinessProfiles to create: [only for new Accounts missing one]
```

## Step 10 — completion report

Example output structure (new setup):
```text
Institutional hierarchy created successfully.

Created:
- 1 System Account (Riverside Community College System)
- 3 Campus Accounts (Main, North, South)
- 7 College Accounts (across all campuses)
- 12 Department Accounts (across all colleges)
- 23 Business Profiles (linked to all accounts)

Total: 23 Account records with proper parent-child relationships
System (root) Account Id: 001XXXXXXXXXXXXXXX (use this to update later)
```

Example output structure (update/reconcile):
```text
Hierarchy reconciled.

- Created:   2 Accounts (Department: Data Science, Department: Robotics)
- Renamed:   1 Account  (English Dept renamed to Department of English)
- Moved:     1 Account  (School of Business moved to North Campus)
- Unchanged: 19 Accounts (reused, no write)
- Extra in org (left untouched): 1  (Legacy Extension Center)
- Business Profiles created: 2 (for the new Departments)
```
