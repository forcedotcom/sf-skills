# Permission targeting reference — nonprofit-fundraising-configure

## Org-wide role classification (steps 6, 8)

This skill provisions every active human user on the org, not just the invoking user. Query:

```sql
SELECT Id, Username, Name, UserType, IsActive, ProfileId, Profile.Name,
       Profile.UserLicense.LicenseDefinitionKey, CreatedBy.Name
FROM User
WHERE IsActive = true AND UserType = 'Standard'
  AND Profile.UserLicense.LicenseDefinitionKey = 'SFDC'
```

`UserType = 'Standard'` alone is not sufficient — built-in integration/bot accounts (seen live:
"SalesforceIQ Integration", "Insights Integration", "Bot User", "DigitalAgent.*") also carry
`UserType = 'Standard'`. The `LicenseDefinitionKey = 'SFDC'` clause keeps only full Salesforce
licenses, which drops service accounts on Salesforce Integration or other non-full licenses. It is
not enough on its own, because some integration users hold a full license, so also exclude:

- rows whose `Name` matches the patterns above; and
- rows whose `CreatedBy.Name` is an automation identity ("Automated Process", "Integration User",
  "Platform Integration", or a name matching the patterns above) **and** whose `Username` or `Name`
  also looks like a service account (contains the whole word `integration`, `bot`, `service`,
  `svc` or `noreply`; not a substring, and not generic words like `system` or `api`, which appear in real
  names). `CreatedBy.Name` alone is not enough: trial, dev and SCIM-provisioned orgs create
  real admins through those same identities, so a real person must not be dropped on creator alone.

Users on a non-full license (e.g. Salesforce Platform) are skipped by the query, not misclassified.
Run the same query once more without the license clause to find them, and list them separately in the plan confirmation as "not provisioned — non-full license" so the admin
can request them explicitly. Show the included users and the excluded accounts to the admin before
any assignment is written, and never add an excluded account back without the admin's explicit say-so.

Classify each remaining user by `Profile.Name`:

- `'System Administrator'` → **Admin** — gets `FundraisingAccess` (step 6) + `Fundraising_Admin`
  (step 8).
- `'Standard User'` → **Standard** — gets `FundraisingAccess` (step 6) + `Fundraising_User`
  (step 8).
- Anything else → gets `FundraisingAccess` only (step 6); step 8 skips them — never assign a
  group to a user this classification didn't resolve.

**Known limitation**: literal `Profile.Name` matching misses custom or cloned admin/standard
profiles (e.g. an org-specific "Admin - Fundraising" clone). Users on such a profile fall through
to the plain-permission-set-only branch and will not get a permission set group. This is an
accepted gap, not a bug to work around — do not attempt profile-permission introspection to guess
at equivalence.

Idempotency for both steps: query for an existing `PermissionSetAssignment`
(`AssigneeId`+`PermissionSetId`, or the group-assignment equivalent) before creating. Treat a
match as already-satisfied rather than re-creating it (`DUPLICATE_VALUE` otherwise) — this skill
has no persisted resume state, so every invocation replays against live org state.
