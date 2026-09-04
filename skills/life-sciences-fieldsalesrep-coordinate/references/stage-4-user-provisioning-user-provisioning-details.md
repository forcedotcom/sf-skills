# User Provisioning Details

## Required Permission Sets

| Permission Set Label | Expected API Name | Purpose |
|---------------------|-------------------|---------|
| Life Sciences Core | LifeSciencesCore | Core LSC platform permissions |
| Life Sciences Field Sales Representative | LifeSciencesFieldSalesRepresentative | Field sales workflow permissions |
| Health Cloud Starter | HealthCloudStarter | Health Cloud foundation permissions |
| Life Sciences Key Account Management | LifeSciencesKeyAccountManager | Key account management permissions |

### Querying Permission Sets

Permission sets from managed packages may have namespace-prefixed API names. If the standard names don't return results, try:

```bash
sf data query --query "SELECT Id, Name, NamespacePrefix, Label FROM PermissionSet WHERE Label LIKE '%Life Sciences%' OR Label LIKE '%Health Cloud%'" --target-org <org> --json
```

---

## Required User Fields

When creating a user via `sf data create record`, these fields are mandatory:

| Field | Description | Default Value |
|-------|-------------|---------------|
| `FirstName` | User's first name | (user-provided) |
| `LastName` | User's last name | (user-provided) |
| `Email` | User's email address | (user-provided) |
| `Username` | Globally unique username | (user-provided) |
| `Alias` | Max 8 characters | First initial + last name (truncated) |
| `ProfileId` | 18-char record ID | (queried from org) |
| `IsActive` | Must be `true` | `true` |
| `TimeZoneSidKey` | User's timezone | `America/Los_Angeles` |
| `LocaleSidKey` | User's locale | `en_US` |
| `EmailEncodingKey` | Email encoding | `UTF-8` |
| `LanguageLocaleKey` | Language | `en_US` |

### Optional Fields

These can be set if the user provides them:

| Field | Description |
|-------|-------------|
| `Title` | Job title (e.g., "Field Sales Representative") |
| `Department` | Department name |
| `Phone` | Phone number |
| `MobilePhone` | Mobile phone number |

---

## Territory Assignment

### UserTerritory2Association Fields

| Field | Description |
|-------|-------------|
| `UserId` | 18-char User record ID |
| `Territory2Id` | 18-char Territory2 record ID |
| `RoleInTerritory2` | Optional — leave blank unless user specifies |

### Identifying the Level-3 Territory

The level-3 territory is the leaf node in the 3-level hierarchy created by `life-sciences-territory-configure`:

```text
Level 1 (Region): RD - West 20D
  └── Level 2 (District): DM - San Francisco 20D02
        └── Level 3 (Territory): TM - SPC - San Francisco North 20D02T11  ← assign here
```

Query to find territories with two levels of parents (i.e., level-3):

```bash
sf data query --query "SELECT Id, Name, DeveloperName, ParentTerritory2.Name, ParentTerritory2.ParentTerritory2.Name FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
```

If the territory model has only one level-3 territory, use it directly. If multiple exist, present them to the user and ask which one to use.

---

## Error Handling

### Common Errors and Remediation

| Error | Cause | Fix |
|-------|-------|-----|
| `DUPLICATE_USERNAME` | Username exists in another org | Append a unique suffix (e.g., `.lsc`, `.dev`) |
| `DUPLICATE_VALUE` on PermissionSetAssignment | Permission set already assigned | Skip — not an error |
| `DUPLICATE_VALUE` on UserTerritory2Association | User already assigned to territory | Skip — not an error |
| `INVALID_CROSS_REFERENCE_KEY` on ProfileId | Profile ID is wrong or from different org | Re-query the profile ID |
| `FIELD_INTEGRITY_EXCEPTION` on Username | Username format invalid | Must be email-like format (contains `@`) |
| `REQUIRED_FIELD_MISSING` | A mandatory field was omitted | Check all required fields are provided |

---

## Setting the User's Password (Phase 6)

A user created via `sf data create record` has **no password and receives no email** — they cannot log in until a password is set. Set one with anonymous Apex, writing the temp file to a **project-local** relative path (never `/tmp` or any path outside the project) and removing it right after:

```bash
echo "System.setPassword('<newUserId>', '<password>');" > .lsc-setpw.apex
sf apex run --file .lsc-setpw.apex --target-org <org> --json
rm -f .lsc-setpw.apex
```

Confirm `compiled: true` and `success: true`. The password must meet the org's policy (default: ≥8 chars, mixed case, at least one number and one symbol). The user is prompted to change it on first login.

**Do not use `sf org generate password --on-behalf-of <username>`** — it only works for users with a local CLI auth entry (e.g. created via `sf org create user`) and fails for API-created users with `NamedOrgNotFoundError`. Alternatively, an admin can reset the password from Setup → Users → <user> → Reset Password to email a set-password link.

Get the login URL for the credential handoff:

```bash
sf org display --target-org <org> --json    # use the instanceUrl field
```

---

## Verification Queries

### Verify user was created correctly

```bash
sf data query --query "SELECT Id, Name, Username, Profile.Name, IsActive FROM User WHERE Username = '<username>'" --target-org <org> --json
```

### Verify permission set assignments

Filter out the profile-owned permission set (`IsOwnedByProfile = false`) so the result matches the 4 sets you assigned rather than returning a 5th hidden profile-owned row:

```bash
sf data query --query "SELECT PermissionSet.Label, PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
```

### Verify territory assignments

```bash
sf data query --query "SELECT User.Name, User.Username, Territory2.Name, Territory2.DeveloperName FROM UserTerritory2Association WHERE Territory2Id = '<territoryId>'" --target-org <org> --json
```
