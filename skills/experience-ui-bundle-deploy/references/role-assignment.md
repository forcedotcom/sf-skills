# Role assignment

Detail for the **role** step. Source of truth: reference `org-setup.mjs`
`assignRoleToCurrentUser` (743-822).

Run this step **only** when a role is configured
(`role: { assignee: "currentUser", roleName: "<UserRole name>" }` in
`org-setup.config.json`). If absent, no-op cleanly. `assignee` is always
`currentUser` — it is the only value the flow honors. Assigning a role to the
current user is what makes Experience Cloud self-registration work correctly, so
this step normally runs before/with self-reg.

Validate `roleName` against the SOQL-name whitelist before querying.

## Sequence

1. **Resolve the role Id**:
   ```sql
   SELECT Id FROM UserRole WHERE Name = '<roleName>'
   ```
   Zero rows → hard error (`role "<roleName>" not found in org`).

2. **Resolve the current user**: `sf org display --target-org <org> --json` →
   `result.username`. If absent → hard error.

3. **Idempotency check**:
   ```sql
   SELECT Id, UserRoleId FROM User WHERE Username = '<username>'
   ```
   If `UserRoleId` is already set, **skip** — do not override an existing role
   assignment (lines 796-805).

4. **Assign**:
   ```bash
   sf data update record --sobject User \
     --where "Username='<username>'" \
     --values "UserRoleId='<roleId>'" \
     --target-org <org> --json
   ```
   Non-zero exit → hard error (`failed to assign role "<roleName>" to
   <username>`).
