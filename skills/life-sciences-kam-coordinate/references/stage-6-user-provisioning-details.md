# KAM User Provisioning Details

## Required Permission Sets

The KAM user gets **exactly four** permission sets:

| Permission Set Label | Expected API Name | Purpose |
|---------------------|-------------------|---------|
| Health Cloud Starter | HealthCloudStarter | Health Cloud foundation permissions |
| Life Sciences Key Account Management | LifeSciencesKeyAccountManager | Key account management permissions |
| Life Sciences Field Sales Representative | LifeSciencesFieldSalesRepresentative | Life Sciences field sales rep permissions |
| Life Sciences Core | LifeSciencesCore | Life Sciences core platform permissions |

> **Resolve by label, not API name.** The API names above are the expected values; managed-package sets may be namespace-prefixed. Always confirm the actual `Name` via the label query below before assigning.

### Querying Permission Sets

Permission sets from managed packages may have namespace-prefixed API names. If the standard names don't return results, try:

```bash
sf data query --query "SELECT Id, Name, NamespacePrefix, Label FROM PermissionSet WHERE Label LIKE '%Key Account%' OR Label LIKE '%Health Cloud%' OR Label LIKE '%Field Sales%' OR Label LIKE '%Life Sciences Core%'" --target-org <org> --json
```

---

## Required User Fields

When creating a user via `sf data create record`, these fields are mandatory:

| Field | Description | Default Value | Admin can edit? |
|-------|-------------|---------------|-----------------|
| `FirstName` | User's first name | `Jordan` | Yes |
| `LastName` | User's last name | `Lee` | Yes |
| `Email` | User's email address | `jordan.lee@<orgdomain>` | Yes |
| `Username` | Globally unique username — **must contain the text `kam`** | `jordan.lee.kam@<orgdomain>` (auto-generated) | No — auto |
| `Alias` | Max 8 characters | `jlee` — first initial + last name (truncated) | No — auto |
| `ProfileId` | 18-char record ID | `LSC Custom Profile` (queried from org) | No — fixed |
| `IsActive` | Must be `true` | `true` | No — fixed |
| `TimeZoneSidKey` | User's timezone | `America/Los_Angeles` | No — default |
| `LocaleSidKey` | User's locale | `en_US` | No — default |
| `EmailEncodingKey` | Email encoding | `UTF-8` | No — default |
| `LanguageLocaleKey` | Language | `en_US` | No — default |

> **Username must contain `kam`.** The KAM spec requires the text `kam` in the username (e.g. `jordan.lee.kam@<orgdomain>`). The username is **auto-generated** from the (possibly edited) name — never asked for. If the derived form lacks `kam`, insert a `.kam` segment.

## Default User Details & Confirmation (show BEFORE creating)

Before creating the user, present the default/derived details above as a table to the admin and get explicit confirmation. **The admin may edit `FirstName`, `LastName`, and `Email` only.** The `Username` and `Alias` are **auto-generated** (never asked for); the remaining fields are fixed defaults. If the admin edits the name, **re-derive the `Username` and `Alias` and re-display** before proceeding. **Do NOT create the user until the admin confirms** — this is the only user-detail confirmation in Stage 6 (permsets, territory, and password proceed automatically per the stage rules).

Example prompt: *"Before I create the KAM user, here are the details — First name **Jordan**, Last name **Lee**, Email **jordan.lee@\<orgdomain\>**. I'll auto-generate the username as **jordan.lee.kam@\<orgdomain\>** (Active, on LSC Custom Profile, en_US / America/Los_Angeles). Change the first/last name or email, or shall I create it as-is?"*

- **Username auto-generation:** derive from the (possibly edited) name as `<first>.<last>.kam@<orgdomain>` (lowercased); it MUST contain `kam`. `<orgdomain>` keeps it globally unique. On `DUPLICATE_USERNAME`, append a unique suffix while preserving `kam` (e.g. `.kam.dev`).
- **Alias auto-generation:** first initial + last name, truncated to 8 characters (e.g. `Jordan Lee` → `jlee`).

### Optional Fields

| Field | Description |
|-------|-------------|
| `Title` | Job title (e.g., "KAM User") |
| `Department` | Department name |
| `Phone` / `MobilePhone` | Phone numbers |

---

## Territory Assignment

### UserTerritory2Association Fields

| Field | Description |
|-------|-------------|
| `UserId` | 18-char User record ID |
| `Territory2Id` | 18-char Territory2 record ID — **the same Stage-3 level-3 territory used for ProductTerritoryAvailability in Stage 5** |
| `RoleInTerritory2` | Optional — leave blank unless the user specifies |

### Identifying the Level-3 Territory

The level-3 territory is the leaf node in the 3-level hierarchy created (or reused) by `life-sciences-territory-configure` in Stage 3. The coordinator captured its ID in `OrchestrationState.territoryId`. **Use that exact territory** — it MUST match the territory used for `ProductTerritoryAvailability` in Stage 5, or the KAM user sees no product/account data. Query to confirm:

```bash
sf data query --query "SELECT Id, Name, DeveloperName, ParentTerritory2.Name, ParentTerritory2.ParentTerritory2.Name FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
```

Both the KAM user **and** the admin are assigned to this same leaf territory.

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `DUPLICATE_USERNAME` | Username exists in another org | Append a unique suffix while keeping `kam` (e.g., `.kam.dev`) |
| `DUPLICATE_VALUE` on PermissionSetAssignment | Permission set already assigned | Skip — not an error |
| `DUPLICATE_VALUE` on UserTerritory2Association | User already assigned to territory | Skip — not an error |
| `INVALID_CROSS_REFERENCE_KEY` on ProfileId | Profile ID wrong or from a different org | Re-query the profile ID |
| `FIELD_INTEGRITY_EXCEPTION` on Username | Username format invalid | Must be email-like format (contains `@`) |
| `REQUIRED_FIELD_MISSING` | A mandatory field was omitted | Check all required fields are provided |

---

## Setting the User's Password

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

### Verify permission set assignments (hard count = 4)

Filter out the profile-owned permission set (`IsOwnedByProfile = false`) so the result matches the 4 sets you assigned rather than a hidden profile-owned row:

```bash
sf data query --query "SELECT PermissionSet.Label, PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
```

This MUST return **exactly 4 rows**: `{HealthCloudStarter, LifeSciencesKeyAccountManager, LifeSciencesFieldSalesRepresentative, LifeSciencesCore}`.

### Verify territory assignments

```bash
sf data query --query "SELECT User.Name, User.Username, Territory2.Name, Territory2.DeveloperName FROM UserTerritory2Association WHERE Territory2Id = '<territoryId>'" --target-org <org> --json
```

Expect at least 2 rows (the KAM user + the admin).
