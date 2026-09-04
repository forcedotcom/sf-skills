# Stage 4 — User Provisioning

Creates an active Field Sales Representative user for Life Sciences Cloud, assigns the required profile and permission sets, and assigns both the new user and the admin to the level-3 territory. This is Stage 4 of the `life-sciences-fieldsalesrep-coordinate` workflow; the coordinator invokes it after the territory model (Stage 3) is active.

## Stage Scope

- **In scope**: Creating an active user, assigning LSC Custom Profile, assigning permission sets, assigning users to territories, setting the user's password so they can log in
- **Out of scope**: Creating the profile (Stage 2), creating territories (Stage 3), validating prerequisites (Stage 1)

---

## Prerequisites

These must exist in the org before this stage runs (the coordinator sequences the earlier stages so they do):

| Prerequisite | Created by |
|---|---|
| `LSC Custom Profile` profile | Stage 2 (Starter Config Deploy) (Step 6) |
| Level-3 territory (e.g., `TMSPCSanFranciscoNorth20D02T11`) | Stage 3 (`life-sciences-territory-configure`) |
| Active Territory Model | Stage 3 (`life-sciences-territory-configure`, Phase 4) |

---

## Required Inputs

Gather before proceeding:

- **Target org**: The org alias or username (from `sf config get target-org` or user-specified)
- **New user details** (ask the user for each):
  - First Name
  - Last Name
  - Email
  - Username (must be globally unique — suggest `<email>.lsc` or similar if user is unsure)
  - Alias (max 8 chars — default to first initial + last name truncated)

---

## Workflow

### Phase 1 — Validate Prerequisites

1. **Verify the LSC Custom Profile exists** in the org:
   ```bash
   sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
   ```
   If it returns zero records, **stop** and tell the user to run Stage 2 (Starter Config Deploy) first.

2. **Verify the level-3 territory exists** and the model is Active:
   ```bash
   sf data query --query "SELECT Id, DeveloperName, Territory2Model.State FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
   ```
   If no results, try querying all territories to find the hierarchy:
   ```bash
   sf data query --query "SELECT Id, DeveloperName, Name, ParentTerritory2.DeveloperName FROM Territory2 WHERE Territory2Model.State = 'Active'" --target-org <org> --json
   ```
   Identify the level-3 territory (the one whose parent also has a parent). If none found, **stop** and tell the user to run `life-sciences-territory-configure` first.

3. **Identify the admin user** (the currently logged-in user):
   ```bash
   sf org display --target-org <org> --json
   ```
   Extract the username, then query the User ID:
   ```bash
   sf data query --query "SELECT Id, Username, Name FROM User WHERE Username = '<admin-username>'" --target-org <org> --json
   ```

### Phase 2 — Collect User Details and Confirm

4. **Ask the user** for the new rep's details:
   - First Name
   - Last Name
   - Email
   - Username (suggest: `<firstname>.<lastname>@<orgdomain>.lsc`)
   - Alias (suggest: first initial + up to 7 chars of last name)

5. **Show a preview** of what will be created:

   ```text
   === New User ===
   First Name: <firstName>
   Last Name: <lastName>
   Email: <email>
   Username: <username>
   Alias: <alias>
   Profile: LSC Custom Profile
   Active: true

   === Permission Sets to Assign ===
   1. Life Sciences Core
   2. Life Sciences Field Sales Representative
   3. Health Cloud Starter
   4. Life Sciences Key Account Management

   === Territory Assignment ===
   Territory: <level-3 territory name> (<DeveloperName>)
   Users to assign: <new user>, <admin user>
   ```

6. **Ask for confirmation**: "Ready to create this user and assign permissions? (yes/no)"

### Phase 3 — Create the User

7. **Get the Profile ID** for LSC Custom Profile (already queried in Phase 1, reuse the ID).

8. **Create the user** using `sf data create record`:
   ```bash
   sf data create record --sobject User --values "FirstName='<firstName>' LastName='<lastName>' Email='<email>' Username='<username>' Alias='<alias>' ProfileId='<profileId>' IsActive=true TimeZoneSidKey='America/Los_Angeles' LocaleSidKey='en_US' EmailEncodingKey='UTF-8' LanguageLocaleKey='en_US'" --target-org <org> --json
   ```

9. **Verify creation** — extract the new user's record ID from the response. If it fails, show the error and suggest remediation (e.g., duplicate username, invalid email).

### Phase 4 — Assign Permission Sets

10. **Query the permission set IDs**:
    ```bash
    sf data query --query "SELECT Id, Name FROM PermissionSet WHERE Name IN ('LifeSciencesCore', 'LifeSciencesFieldSalesRepresentative', 'HealthCloudStarter', 'LifeSciencesKeyAccountManager')" --target-org <org> --json
    ```

    > **Note:** Permission set API names may differ from labels. If the above returns fewer than 4 results, try querying by label:
    ```bash
    sf data query --query "SELECT Id, Label, Name FROM PermissionSet WHERE Label IN ('Life Sciences Core', 'Life Sciences Field Sales Representative', 'Health Cloud Starter', 'Life Sciences Key Account Management')" --target-org <org> --json
    ```

    > **STOP-GATE (found count).** The four permission sets are ALL required — `LifeSciencesCore`, `LifeSciencesFieldSalesRepresentative`, `HealthCloudStarter`, and `LifeSciencesKeyAccountManager`. If the combined result of the two queries above yields **fewer than 4 distinct IDs**, do NOT proceed. Report exactly which of the four are missing from the org and stop — a missing permission set is an org-provisioning gap, not something to skip past. Do not assign a subset and continue.

11. **Create PermissionSetAssignment records** — one per permission set. Collect the four IDs from step 10 into an explicit list and assign **all four**; do not stop after the two obviously-named ("core", "field sales rep") sets:
    ```bash
    sf data create record --sobject PermissionSetAssignment --values "AssigneeId='<newUserId>' PermissionSetId='<permSetId>'" --target-org <org> --json
    ```
    Run this once for **each of the 4** permission set IDs. Track how many succeeded (treat a `DUPLICATE_VALUE` error as an already-assigned success, not a failure).

12. **Verify assignments (hard count gate)** — filter out the profile-owned permission set so only the explicitly-assigned sets show:
    ```bash
    sf data query --query "SELECT PermissionSet.Name, PermissionSet.Label FROM PermissionSetAssignment WHERE AssigneeId = '<newUserId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
    ```

    > Every user has a hidden PermissionSet owned by their profile. Without `AND PermissionSet.IsOwnedByProfile = false`, this query returns 5 rows (the 4 assigned + the profile's) — the filter makes the result match the sets you assigned.

    > **STOP-GATE (assigned count).** This query MUST return **exactly 4 rows**, and the set of names MUST equal `{LifeSciencesCore, LifeSciencesFieldSalesRepresentative, HealthCloudStarter, LifeSciencesKeyAccountManager}`. If it returns fewer than 4, the assignment is INCOMPLETE — identify the missing set(s) by name, re-run step 11 for each missing ID, and re-run this verify until it returns 4. Do NOT advance to Phase 5 (territory assignment) or report success while the count is < 4. "Some permsets assigned" is a failure state, not a partial success.

### Phase 5 — Assign Users to Territory

13. **Assign the new user** to the level-3 territory:
    ```bash
    sf data create record --sobject UserTerritory2Association --values "UserId='<newUserId>' Territory2Id='<territory2Id>'" --target-org <org> --json
    ```

14. **Assign the admin user** to the same level-3 territory:
    ```bash
    sf data create record --sobject UserTerritory2Association --values "UserId='<adminUserId>' Territory2Id='<territory2Id>'" --target-org <org> --json
    ```

    > If the admin is already assigned (duplicate error), report that it's already assigned and continue.

15. **Verify territory assignments**:
    ```bash
    sf data query --query "SELECT User.Name, Territory2.Name FROM UserTerritory2Association WHERE Territory2Id = '<territory2Id>'" --target-org <org> --json
    ```

### Phase 6 — Grant Login Access (Set Password)

> **Creating a user via `sf data create record` sends NO welcome or set-password email, and the user has no usable password.** The user cannot log in until you set one. Do NOT tell the user to expect an email — none is sent by API creation.

16. **Set a password** for the new user. Use anonymous Apex `System.setPassword` — this is the reliable method for an API-created user. Write the Apex to a **project-local** temp file (a relative path in the CWD — never `/tmp` or any path outside the project) and delete it right after:
    ```bash
    echo "System.setPassword('<newUserId>', '<password>');" > .lsc-setpw.apex
    sf apex run --file .lsc-setpw.apex --target-org <org> --json
    rm -f .lsc-setpw.apex
    ```
    Choose a password meeting the org's policy (≥8 chars, mixed case, number, symbol — e.g. `Lsc!Rep2026`). Confirm `compiled: true` and `success: true` in the response. Deleting the file afterward avoids leaving the password on disk.

    > **Do NOT use `sf org generate password --on-behalf-of <username>` for this user.** That command only works for users the CLI holds a local auth entry for (e.g. created via `sf org create user`); for an API-created user it fails with `NamedOrgNotFoundError: No authorization information found for <username>`. As an alternative to setting a password directly, an admin can use Setup → Users → <user> → Reset Password to email a branded set-password link to the user's Email address.

17. **Get the login URL** (org instance URL) for the summary:
    ```bash
    sf org display --target-org <org> --json
    ```
    Use the `instanceUrl` field.

### Phase 7 — Report

18. **Display success summary** (include the password and login URL so the user can hand off credentials — this is the one place the password is shown, since the admin needs it to log in as the rep):

    ```text
    Life Sciences User Provisioning Complete
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    User Created:
      Name:     <firstName> <lastName>
      Username: <username>
      Password: <password>
      Email:    <email>
      Profile:  LSC Custom Profile
      Status:   Active
    
    Permission Sets Assigned:
      - Life Sciences Core
      - Life Sciences Field Sales Representative
      - Health Cloud Starter
      - Life Sciences Key Account Management
    
    Territory Assignment:
      Territory: <territory name> (<DeveloperName>)
      - <new user name> — assigned
      - <admin user name> — assigned
    
    Login URL: <instanceUrl>
    ```

    > The user will be prompted to change this password on first login. No email is sent automatically — deliver the credentials to the new user directly.

---

## Mid-Flow Change Requests (Impact Assessment)

If the user requests a change to inputs provided in an earlier phase while a later phase is in progress or completed, perform an impact assessment before applying.

### Behavior

1. **Acknowledge** the change request without applying it.
2. **Assess impact** — determine what must be undone or redone:

   ```text
   Change Request Impact Assessment
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Requested change: <describe>

   Impact:
     <list affected phases and what happens to each>

   Action required:
     <what will be undone/redone>
   ```

3. **Present options** and wait for the user's decision before acting.

### Impact Matrix

| Change requested | When (phase already done) | Impact | Action |
|---|---|---|---|
| Username or email | After Phase 3 (user created) | Old user becomes orphaned | Deactivate old user (`IsActive=false`) — this auto-removes its territory assignment — then create new user and re-assign permsets and territory |
| First/Last name | After Phase 3 (user created) | Name mismatch | Update existing user record in-place (no new user needed) |
| Permission sets | After Phase 4 (permsets assigned) | Wrong permsets on user | Remove unwanted assignments, add new ones |
| Territory | After Phase 5 (territory assigned) | User in wrong territory | Remove old `UserTerritory2Association`, create new one |
| Profile | After Phase 3 (user created) | Wrong profile on user | Update user's `ProfileId` in-place |

### Superseded User Deactivation

When a change requires creating a **new** user (username/email change after the original was already created):

1. **Deactivate the old user** immediately:
   ```bash
   sf data update record --sobject User --record-id <oldUserId> --values "IsActive=false" --target-org <org> --json
   ```

2. **Confirm the old user's territory assignment is gone.** Deactivating a user (`IsActive=false`) **auto-cascades** the deletion of their `UserTerritory2Association` records — you do NOT need to (and usually cannot) delete them explicitly. Verify rather than delete:
   ```bash
   sf data query --query "SELECT Id FROM UserTerritory2Association WHERE UserId = '<oldUserId>'" --target-org <org> --json
   ```
   Expect `totalSize: 0`. If any remain (rare), delete them:
   ```bash
   sf data delete record --sobject UserTerritory2Association --record-id <associationId> --target-org <org> --json
   ```
   > **Do not delete first / do not treat a failed delete as an error.** After deactivation the association is already gone, so an explicit delete targeting the old association Id fails with `INSUFFICIENT_ACCESS_OR_READONLY: insufficient access rights on object id` — a misleading message that actually means "record no longer exists." Treat that as success (the assignment is removed), not a failure to recover from.

3. **Report the deactivation** in the impact summary:
   ```text
   Superseded user handled:
     Deactivated: <oldUsername> (IsActive = false)
     Removed from territory: <territory name>
     New user will be created with updated details.
   ```

4. **Proceed** to create the new user through Phases 3–6 with the updated details.

> **Why deactivate, not delete:** Salesforce does not allow deleting User records. Deactivation (`IsActive=false`) prevents login and removes the user from active license counts while preserving audit history.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Validate prerequisites before creating the user | Avoids creating a user that can't be properly configured |
| User must be Active (`IsActive=true`) | Required for the field sales rep to log in and work |
| Always assign LSC Custom Profile | This profile has the required object and field permissions for LSC |
| Assign all 4 permission sets | Each provides distinct capabilities needed for field sales workflows |
| Assign both new user AND admin to territory | Admin needs territory access for management; rep needs it for account access |
| Use `--target-org` for every command | Explicit org targeting prevents accidental operations |
| Confirm details before creating | User creation is not easily reversible |
| Deactivate superseded users when a change requires a new user | Prevents orphaned active accounts consuming licenses |
| Perform impact assessment before applying mid-flow changes | User must understand what gets undone before committing |
| Never delete User records | Salesforce does not support User deletion — deactivate instead |
| Set a password after creating the user (Phase 6) and never promise a welcome email | API creation sends no email and leaves no usable password; the user cannot log in until a password is set |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Username must be globally unique across all Salesforce orgs | Suggest appending `.lsc` or org-specific suffix |
| Permission set API names differ from labels | Query by both `Name` and `Label` as fallback |
| Admin already assigned to territory | Catch duplicate error and continue — not a failure |
| Profile not found | User must run Stage 2 (Starter Config Deploy) first |
| Territory not found or model not Active | User must run `life-sciences-territory-configure` first |
| User creation fails with "DUPLICATE_USERNAME" | Ask user for a different username |
| Permission set assignment fails with "DUPLICATE_VALUE" | Permission set already assigned — skip and continue |
| User changes username after user created | Deactivate old user, remove territory assignment, create new user with full provisioning |
| User changes name (not username) after user created | Update in-place with `sf data update record` — no new user needed |
| Cannot delete old user | Salesforce prohibits User deletion; deactivation is the only option |
| `INSUFFICIENT_ACCESS_OR_READONLY: insufficient access rights on object id` when deleting a deactivated user's `UserTerritory2Association` | Deactivating the user already cascade-deleted the association; the record is gone. Treat as success — verify with a query returning `totalSize: 0` instead of deleting |
| New user got no email / can't log in | Expected — `sf data create record` sends no welcome email and sets no password. Set a password in Phase 6 (`System.setPassword` via `sf apex run`) and deliver credentials directly |
| `sf org generate password` fails with `NamedOrgNotFoundError: No authorization information found for <username>` | That command only works for users with a local CLI auth entry, not API-created users. Use `System.setPassword` via anonymous Apex, or reset the password from the Setup UI |

---

## Output Expectations

Deliverables:
- Active user created with LSC Custom Profile
- All 4 permission sets assigned to the new user
- New user assigned to the level-3 territory
- Admin user assigned to the level-3 territory
- Password set for the new user (so they can log in — no email is sent by API creation)
- Confirmation summary including username, password, email, profile, territory, and login URL (the password is shown here so the admin can log in as the rep)

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-4-user-provisioning-user-provisioning-details.md` | During all phases — contains permission set API names, required user field defaults, and territory assignment details |
