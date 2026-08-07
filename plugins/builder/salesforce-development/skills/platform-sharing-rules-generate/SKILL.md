---
name: platform-sharing-rules-generate
description: "Use this skill when users need to create, edit, delete, or manage Salesforce Sharing Rules metadata. TRIGGER when: users mention sharing rules, record sharing, criteria-based sharing, role-based sharing, guest user sharing, sharingRules, sharingCriteriaRules, sharingGuestRules, sharingOwnerRules, .sharingRules-meta.xml files, or ask to share records with specific roles or groups. Also trigger when users want to modify or remove existing sharing rules, or update sharing rule criteria or access levels. DO NOT TRIGGER when user needs permission sets or profiles (use platform-permission-set-generate), or needs object-level security rather than record-level sharing (use platform-permission-set-generate)."
metadata:
  version: "1.2"
  minApiVersion: "60.0"
  relatedSkills:
    - "platform-custom-object-generate"
    - "platform-permission-set-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Sharing Rules Generator

Create, edit, and delete Salesforce Sharing Rules metadata to control record-level access beyond org-wide defaults. Supports criteria-based rules, role/group-based owner rules, and guest user rules for Experience Sites.

## Scope

- **In scope**: Creating, editing, and deleting `sharingCriteriaRules`, `sharingOwnerRules`, and `sharingGuestRules` metadata; retrieving existing sharing rules from an org; appending new rules to existing files; modifying rule criteria, access levels, or shared-to targets; removing rules from metadata files; configuring rules for Guest and Portal profiles.
- **Out of scope**: Changing org-wide defaults (OWD/sharing model), creating Experience Sites, configuring permission sets or profiles (use `platform-permission-set-generate`), territory-based sharing rules.

---

## Clarifying Questions

Before proceeding, confirm with the user if not already clear:

### For Create operations:
- Which object should the sharing rule apply to? (standard or custom object API name)
- What type of rule? (criteria-based, role/group-based owner rule, or guest user rule)
- Who should records be shared with? (role name, group, portal role, or guest user nickname)
- What access level? (Read or Read/Write)
- For criteria-based rules: what field conditions should match?

### For Edit operations:
- Which existing rule should be modified? (rule fullName or label)
- What should change? (access level, shared-to target, criteria, label)

### For Delete operations:
- Which rule(s) should be removed? (rule fullName or label)
- Confirm the object the rule belongs to

---

## Required Inputs

Gather or infer before proceeding:

- **Object API name**: The sObject the rule targets (e.g., `Account`, `Property__c`)
- **Rule type**: One of `sharingCriteriaRules`, `sharingOwnerRules`, or `sharingGuestRules`
- **Shared-to target**: Role, group, portal role, or guest user community nickname
- **Access level**: `Read` or `Edit` (maps to Read-Only or Read/Write)
- **Criteria** (for criteria/guest rules): Field name, operation, and value for each filter item

Defaults unless specified:
- Access level: `Read`
- `includeRecordsOwnedByAll`: `true` for criteria rules
- `includeHVUOwnedRecords`: `false` for guest rules
- Account sharing rules include `accountSettings` with all sub-access levels set to `None`

---

## Workflow

Steps are sequential within each phase. Phase 3 branches by operation type — execute only the matching branch.

### Phase 1 — Discover

1. **Resolve the SFDX project path** — find the project's `sfdx-project.json` and identify the package directory for `sharingRules/`.

2. **Check for existing sharing rules** — look for `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml`. If found, read it to understand existing rules and avoid duplicates.

3. **If no local file exists**, retrieve from the org: `sf project retrieve start --metadata "SharingRules:<ObjectName>" --target-org <org>`

### Phase 2 — Determine Operation and Rule Type

4. **Identify the operation** — determine whether the user wants to **create**, **edit**, or **delete** a sharing rule.

5. **Select the rule type** based on user intent. Read `references/rule-types.md` for the complete schema of each type and its required elements.

6. **For Account sharing rules**: the `accountSettings` element is required. Default sub-access levels to `None` unless the user specifies otherwise.

7. **For Guest rules**: the `sharedTo` must use `<guestUser>` with the site guest user's community nickname. Never use `<role>` or `<group>` for guest rules.

### Phase 3 — Execute Operation

#### For Create:

8a. **Construct the XML** following the schema in `references/rule-types.md`. Key structure:
    - One `.sharingRules-meta.xml` file per object
    - All rules for the same object go in the same file
    - If appending to an existing file, add the new rule element inside the existing `<SharingRules>` root

8b. **Name the rule** — derive `<fullName>` from the intent (PascalCase, no spaces, descriptive). Generate a matching `<label>` in Title Case with spaces.

#### For Edit:

8a. **Locate the target rule** — find the rule by `<fullName>` or `<label>` in the existing `.sharingRules-meta.xml` file.

8b. **Determine modifications** — identify which elements to change (e.g., `<accessLevel>`, `<sharedTo>`, `<criteriaItems>`, `<label>`) and what the new values will be. Do not write yet — all disk writes happen in Phase 5 after user confirmation.

#### For Delete:

8a. **Locate the target rule** — find the rule by `<fullName>` or `<label>` in the existing `.sharingRules-meta.xml` file.

8b. **Count remaining rules** — run: `grep -c '<sharingCriteriaRules>\|<sharingOwnerRules>\|<sharingGuestRules>' <file>` to get the total rule count. If the count is 1 (only the rule being deleted), the file must be removed entirely in Phase 5. Do not write yet — all disk writes happen in Phase 5 after user confirmation.

### Phase 4 — Confirm with User   CRITICAL

9. **Present a summary of changes** before writing to disk. You MUST stop and wait for user confirmation. Format the summary as:

    > **Operation:** Create / Edit / Delete
    > **Object:** `<ObjectName>`
    > **Rule:** `<fullName>` (`<label>`)
    > **Changes:** (describe what will be created/modified/removed)
    >
    > Proceed? (yes / no / edit)

    **Do NOT write any file changes until the user explicitly confirms.** If the user says "no", abort. If the user says "edit", incorporate their feedback and re-present.

### Phase 5 — Write and Verify

10. **Apply the change** only after user confirmation:
    - **Create**: Write the file to `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml`.
    - **Edit**: Update only the elements identified in step 8b; preserve all other elements exactly as they were.
    - **Delete (rules remain)**: Write the updated file with the target rule removed.
    - **Delete (last rule)**: Remove the file `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` entirely.

11. **Run the verification checklist** below and consult the examples files (`examples/create-cases.md`, `examples/edit-cases.md`, `examples/delete-cases.md`) for scenario-specific expected behaviors before presenting output.

---

## Verification Checklist

### Universal Checks
- [ ] Does the file have the XML declaration and `<SharingRules xmlns="http://soap.sforce.com/2006/04/metadata">` root?
- [ ] Is there exactly one file per object with all rules inside it?
- [ ] Does `<fullName>` use PascalCase with no spaces?
- [ ] Is `<label>` present and human-readable?
- [ ] Is `<accessLevel>` one of `Read` or `Edit`?

### Criteria Rule Checks
- [ ] Is `<includeRecordsOwnedByAll>` present (required boolean)?
- [ ] Does each `<criteriaItems>` have `<field>`, `<operation>`, and `<value>`?
- [ ] Are picklist values valid for the target org?

### Guest Rule Checks   CRITICAL
- [ ] Does `<sharedTo>` use `<guestUser>` (NOT `<role>` or `<group>`)?
- [ ] Is `<includeHVUOwnedRecords>` present (required boolean)?
- [ ] Is `<includeRecordsOwnedByAll>` ABSENT (only for criteria rules, not guest rules)?

### Owner Rule Checks
- [ ] Does the rule have both `<sharedFrom>` and `<sharedTo>` elements?
- [ ] Do both use valid `<role>`, `<roleAndSubordinates>`, or `<group>` targets?

### Edit Operation Checks
- [ ] Was only the intended element modified?
- [ ] Are all required elements still present after the edit?
- [ ] Does the modified rule still pass the universal checks above?
- [ ] Was user confirmation received before writing?

### Delete Operation Checks
- [ ] Was the correct rule removed (matched by `<fullName>`)?
- [ ] Is the remaining XML well-formed with proper `<SharingRules>` root?
- [ ] If no rules remain, was the file removed entirely?
- [ ] Was user confirmation received before writing?

### Account-Specific Checks   CRITICAL
- [ ] If object is Account, is `<accountSettings>` present with all three sub-elements?
- [ ] Are `<caseAccessLevel>`, `<contactAccessLevel>`, `<opportunityAccessLevel>` all set?

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| One `.sharingRules-meta.xml` file per object | Platform requirement — multiple files cause deployment errors |
| Guest rules must use `<guestUser>` in `sharedTo` | Using `<role>` or `<group>` causes: "Specify a guest user's nickname for the guestUser field" |
| Account rules require `<accountSettings>` | Without it: "AccountSettings is required for account sharing rules" |
| `includeRecordsOwnedByAll` is required on criteria rules | Missing it causes: "Required field is missing: sharingCriteriaRules" |
| `includeHVUOwnedRecords` is required on guest rules | Missing it causes deployment failure |
| Criteria field values must exist as picklist values on the org | Invalid values cause: "Picklist value does not exist" |
| Never hardcode file paths — resolve from `sfdx-project.json` | Customer projects use custom package directories |
| For managed package custom objects, use the full API name including namespace prefix (e.g., `ns__Object__c`) | Namespace-prefixed objects store sharing rules under the prefixed name |
| Always confirm before writing changes | Prevents accidental creation, modification, or deletion of sharing rules |
| Edit must preserve unmodified elements | Changing only `accessLevel` must not alter `criteriaItems` or other fields |
| Delete must remove the entire rule block | Partial deletion leaves invalid XML and causes deployment failures |
| Delete last rule removes the file | An empty `<SharingRules>` root with no children is invalid metadata |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Guest rule uses `<role>` instead of `<guestUser>` | Replace with `<guestUser>CommunityNickname</guestUser>` |
| Account rule missing `accountSettings` | Add `<accountSettings>` with all three access level sub-elements set to `None` |
| Criteria rule missing `includeRecordsOwnedByAll` | Add `<includeRecordsOwnedByAll>true</includeRecordsOwnedByAll>` |
| Picklist value mismatch | Query the org for valid values before generating criteria |
| Appending duplicates existing rule name | Check existing `<fullName>` values before writing |
| Guest user nickname not found | Query: `SELECT CommunityNickname FROM User WHERE UserType='Guest' AND IsActive=true` |
| Editing a rule that doesn't exist locally | Retrieve from org first before attempting edit |
| Deleting a rule referenced by other automation | Warn the user about potential downstream impact before confirming |
| Editing changes rule type (e.g., criteria → owner) | Not supported — delete the old rule and create a new one instead |
| Delete leaves malformed XML | Ensure proper XML structure after removal; validate the file is well-formed |

---

## Output Expectations

Deliverables:
- `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` — complete sharing rules file for the target object

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Permission set configuration | `platform-permission-set-generate` skill |
| Custom object creation (if target object doesn't exist) | `platform-custom-object-generate` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/rule-types.md` | Phase 2 — before generating any rule, to get the complete XML schema for each rule type |
| `examples/create-cases.md` | Phase 5, step 11 — expected behavior for create and append scenarios |
| `examples/edit-cases.md` | Phase 5, step 11 — expected behavior for edit scenarios |
| `examples/delete-cases.md` | Phase 5, step 11 — expected behavior for delete and confirmation flow scenarios |
