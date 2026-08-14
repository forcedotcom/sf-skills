---
name: platform-sharing-rules-generate
description: "Use this skill when users need to get, create, edit, delete, or manage Salesforce Sharing Rules metadata. TRIGGER when: users mention sharing rules, record sharing, criteria-based sharing, role-based sharing, guest user sharing, sharingRules, sharingCriteriaRules, sharingGuestRules, sharingOwnerRules, .sharingRules-meta.xml files, or ask to share records with specific roles or groups. Also trigger when users want to retrieve or view existing sharing rules from an org, modify or remove existing sharing rules, or update sharing rule criteria or access levels. DO NOT TRIGGER when user needs permission sets or profiles (use platform-permission-set-generate), or needs object-level security rather than record-level sharing (use platform-permission-set-generate)."
metadata:
  version: "1.3"
  minApiVersion: "60.0"
  relatedSkills:
    - "platform-custom-object-generate"
    - "platform-permission-set-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Sharing Rules Generator

Get, create, edit, and delete Salesforce Sharing Rules metadata to control record-level access beyond org-wide defaults. Supports criteria-based rules, role/group-based owner rules, and guest user rules for Experience Sites.

## Scope

- **In scope**: Creating, editing, deleting, and retrieving (getting) `sharingCriteriaRules`, `sharingOwnerRules`, and `sharingGuestRules` metadata; retrieving existing sharing rules from an org using the Metadata API Retrieve pattern; appending new rules to existing files; modifying rule criteria or access levels; removing rules from metadata files; configuring rules for Guest and Portal profiles.
- **Out of scope**: Changing org-wide defaults (OWD/sharing model), creating Experience Sites, configuring permission sets or profiles (use `platform-permission-set-generate`), territory-based sharing rules.

---

## Clarifying Questions

Before proceeding, confirm with the user if not already clear:

### For Get operations:
- Which object's sharing rules should be retrieved? (standard or custom object API name, or all objects)
- Which target org should the rules be retrieved from? (org alias or default)

### For Create operations:
- Which object should the sharing rule apply to? (standard or custom object API name)
- What type of rule? (criteria-based, role/group-based owner rule, or guest user rule)
- Who should records be shared with? (role name, group, portal role, or guest user nickname)
- What access level? (Read or Read/Write)
- For criteria-based rules: what field conditions should match?

### For Edit operations:
- Which existing rule should be modified? (rule fullName or label)
- What should change? (access level, criteria, label — note: `sharedTo` and `sharedFrom` cannot be edited in place)

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

Steps are sequential within each phase. Phase 3 branches by operation type — execute only the matching branch. Phase 4 applies to create, edit, and delete only (get operations end at Phase 3).

### Phase 1 — Discover

1. **Resolve the SFDX project path** — find the project's `sfdx-project.json` and identify the package directory for `sharingRules/`.

2. **Always retrieve the latest sharing rules from the org** using the Metadata API Retrieve pattern:
   ```bash
   sf project retrieve start --metadata "SharingRules:<ObjectName>" --target-org <org>
   ```
   This ensures the local file reflects the current org state. Never trust a local file that may be stale — edits or deletes against a stale file can recreate rules that were already removed in the org or overwrite changes made by other users.

3. **Read the retrieved file** — parse `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` to understand existing rules and avoid duplicates.

### Phase 2 — Determine Operation and Rule Type

4. **Identify the operation** — determine whether the user wants to **get**, **create**, **edit**, or **delete** a sharing rule.

5. **Select the rule type** based on user intent. Read `references/rule-types.md` for the complete schema of each type and its required elements.

6. **For Account sharing rules**: the `accountSettings` element is required. Default sub-access levels to `None` unless the user specifies otherwise.

7. **For Guest rules**: the `sharedTo` must use `<guestUser>` with the site guest user's community nickname. Never use `<role>` or `<group>` for guest rules.

### Phase 3 — Execute Operation

#### For Get:

8a. **Use the file already retrieved in Phase 1** — the retrieve in step 2 already pulled the latest `<ObjectName>.sharingRules-meta.xml` from the org. No additional retrieve is needed.

8b. **Read and present the retrieved rules** — parse the `.sharingRules-meta.xml` file and present the rules to the user in a readable format showing:
    - Rule name (`fullName`) and label
    - Rule type (criteria-based, owner-based, or guest)
    - Access level
    - Shared-to target
    - Criteria (if applicable)

    For get operations, skip Phase 4 (no write needed). The retrieve itself writes the metadata file to the local project.

#### For Create:

8a. **Construct the XML** following the schema in `references/rule-types.md`. Key structure:
    - One `.sharingRules-meta.xml` file per object
    - All rules for the same object go in the same file
    - If appending to an existing file, add the new rule element inside the existing `<SharingRules>` root

8b. **Name the rule** — derive `<fullName>` from the intent (PascalCase, no spaces, descriptive). Generate a matching `<label>` in Title Case with spaces.

#### For Edit:

8a. **Locate the target rule** — find the rule by `<fullName>` or `<label>` in the existing `.sharingRules-meta.xml` file.

8b. **Gate unsupported edits** — the platform does NOT support in-place modification of `<sharedTo>` or `<sharedFrom>` elements. If the user requests a change to the sharing target or source, refuse the edit and instruct them to delete the existing rule and create a new one with the desired target. This is the same pattern used for rule-type changes (see TC-16).

8c. **Determine modifications based on rule type**:
    - **Owner-based rules (`sharingOwnerRules`)**: only `<accessLevel>` can be edited. The platform does not support modifying any other element (`sharedTo`, `sharedFrom`, `label`) on owner rules. If the user requests changes beyond access level, refuse and instruct them to delete + create.
    - **Criteria-based rules (`sharingCriteriaRules`)**: supported editable elements are `<accessLevel>`, `<criteriaItems>`, `<label>`, and `<booleanFilter>`.
    - **Guest rules (`sharingGuestRules`)**: supported editable elements are `<accessLevel>`, `<criteriaItems>`, `<label>`, and `<includeHVUOwnedRecords>`.

#### For Delete:

8a. **Locate the target rule** — find the rule by `<fullName>` or `<label>` in the existing `.sharingRules-meta.xml` file.

8b. **Count remaining rules** — run `scripts/count-remaining-rules.sh <file>` to get the total rule count. If the count is 1 (only the rule being deleted), the file must be removed entirely in Phase 4.

8c. **Delegate destructive deployment to `platform-destructive-deploy`** — a normal `sf project deploy start` is additive and will NOT remove a rule from the org. Delegate to the `platform-destructive-deploy` skill with the following context:
    - Metadata type: `SharingCriteriaRule`, `SharingOwnerRule`, or `SharingGuestRule` (depending on the rule type)
    - Member: `<ObjectName>.<RuleFullName>`
    - Target org: the user's specified org

### Phase 4 — Write and Verify

9. **Apply the change**:
    - **Create**: Write the file to `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml`.
    - **Edit**: Update only the elements identified in step 8b; preserve all other elements exactly as they were.
    - **Delete (rules remain)**: Write the updated file with the target rule removed.
    - **Delete (last rule)**: Remove the file `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` entirely.

10. **Run the verification checklist** below and consult the examples files (`examples/create-cases.md`, `examples/edit-cases.md`, `examples/delete-cases.md`) for scenario-specific expected behaviors before presenting output.

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
- [ ] Was the edit against a freshly retrieved file (not a stale local copy)?
- [ ] Is the edit limited to supported fields for the rule type?
  - Owner rules: only `accessLevel`
  - Criteria rules: `accessLevel`, `criteriaItems`, `label`, `booleanFilter`
  - Guest rules: `accessLevel`, `criteriaItems`, `label`, `includeHVUOwnedRecords`
- [ ] Was `sharedTo`/`sharedFrom` left unchanged? (if user requested that change, refuse and advise delete + create)
- [ ] Was only the intended element modified?
- [ ] Are all required elements still present after the edit?
- [ ] Does the modified rule still pass the universal checks above?

### Delete Operation Checks
- [ ] Was the correct rule removed (matched by `<fullName>`)?
- [ ] Is the remaining XML well-formed with proper `<SharingRules>` root?
- [ ] If no rules remain, was the file removed entirely?
- [ ] Was `platform-destructive-deploy` delegated to with the correct metadata type (`SharingCriteriaRule`, `SharingOwnerRule`, or `SharingGuestRule`)?

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
| `sharedTo` and `sharedFrom` cannot be edited in place | Platform does not support modifying sharing targets — deploy will fail. Delete the rule and create a new one instead |
| Owner-based rules only support editing `accessLevel` | No other field (`label`, `sharedTo`, `sharedFrom`) can be modified on owner rules — delete and recreate instead |
| Always retrieve from the org before edit or delete | Local files may be stale; editing a stale file can recreate deleted rules or overwrite concurrent changes |
| Deleting a rule requires a destructive deployment | A normal deploy is additive — it will not remove rules from the org. Delegate to `platform-destructive-deploy` |
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
| User requests edit to `sharedTo` or `sharedFrom` | Not supported — refuse the edit and instruct user to delete + create a new rule |
| User requests edit to owner rule beyond `accessLevel` | Not supported — owner rules only allow `accessLevel` edits. Refuse and instruct user to delete + create |
| Editing changes rule type (e.g., criteria → owner) | Not supported — delete the old rule and create a new one instead |
| Local file is stale (rule deleted/changed in org) | Always retrieve fresh from org before edit or delete to avoid recreating removed rules |
| Delete deployed with normal deploy (no destructive manifest) | Rule remains in the org — delegate to `platform-destructive-deploy` for proper removal |
| Deleting a rule referenced by other automation | Warn the user about potential downstream impact |
| Delete leaves malformed XML | Ensure proper XML structure after removal; validate the file is well-formed |

---

## Output Expectations

Deliverables:
- **For get operations**: `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` — retrieved sharing rules file from the org, plus a formatted summary of all rules found
- **For create/edit/delete operations**: `<packageDir>/sharingRules/<ObjectName>.sharingRules-meta.xml` — complete sharing rules file for the target object

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Permission set configuration | `platform-permission-set-generate` skill |
| Custom object creation (if target object doesn't exist) | `platform-custom-object-generate` skill |
| Destructive deployment (rule deletion from org) | `platform-destructive-deploy` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/rule-types.md` | Phase 2 — before generating any rule, to get the complete XML schema for each rule type |
| `scripts/count-remaining-rules.sh` | Phase 3, step 8b (Delete) — count sharing rule elements to determine if file should be removed |
| `examples/create-cases.md` | Phase 4, step 10 — expected behavior for create and append scenarios |
| `examples/edit-cases.md` | Phase 4, step 10 — expected behavior for edit scenarios |
| `examples/delete-cases.md` | Phase 4, step 10 — expected behavior for delete scenarios |
