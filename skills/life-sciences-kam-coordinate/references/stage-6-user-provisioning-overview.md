# Stage 6 — KAM User Provisioning

Creates the KAM end user, assigns the four KAM permission sets, sets a password, assigns both the user and the admin to the Stage-3 level-3 territory, and generates the mobile metadata cache. This is the final stage of `life-sciences-kam-coordinate`; the coordinator invokes it after the KAM data & plan templates (Stage 5) exist.

## Stage Scope

- **In scope**: creating one Active user (username contains `kam`) on the `LSC Custom Profile`, assigning 4 permission sets, setting a password, assigning the user + admin to the level-3 territory, and generating + verifying the mobile metadata cache
- **Out of scope**: everything in Stages 1–5

## Required Inputs

- **Target org / admin**: admin alias or username (the metadata-cache generation runs as admin)
- **KAM user details**: shown to the admin as **defaults for confirmation** before creation — the admin can edit **FirstName / LastName / Email**; the **username is auto-generated** (always containing `kam`) and the rest are fixed defaults (see the details reference)
- **Stage-3 level-3 territory Id**: from `OrchestrationState.territoryId` — **MUST be the same territory used for `ProductTerritoryAvailability` in Stage 5**, or the KAM user sees no product/account data

## Workflow

### Phase A — Create the user

1. Query the `LSC Custom Profile` Id.
2. **Confirm the user details with the admin BEFORE creating.** Present the default/derived details as a table (see "Default User Details & Confirmation" in the details reference). The admin may edit **FirstName / LastName / Email**; the **username is auto-generated** (always containing `kam`) from the name, and the remaining fields are fixed defaults. If the admin edits the name, re-derive the username + alias and re-display. **Do NOT create the user until the admin confirms.**
3. Create the user with the confirmed fields (username MUST contain `kam`, `IsActive=true`). Full field table, username rule, and error handling: **`references/stage-6-user-provisioning-details.md`**.
4. Set the user's password with anonymous Apex, writing the temp file to a **project-local** relative path (never `/tmp`) and removing it right after — see the password section in the details reference.
5. Capture the login URL (`sf org display`) for the credential handoff.

### Phase B — Assign the four permission sets

Assign **exactly four** permission sets:

| Label | Expected API name |
|-------|-------------------|
| Health Cloud Starter | HealthCloudStarter |
| Life Sciences Key Account Management | LifeSciencesKeyAccountManager |
| Life Sciences Field Sales Representative | LifeSciencesFieldSalesRepresentative |
| Life Sciences Core | LifeSciencesCore |

Resolve the API names by label first (they may be namespace-prefixed) — see the details reference. Create a `PermissionSetAssignment` for each.

> **STOP-GATE (permset count = 4).** After assigning, query the count filtered to non-profile-owned sets:
> ```bash
> sf data query --query "SELECT COUNT(Id) c FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <admin> --json
> ```
> This MUST return **exactly 4** (`{HealthCloudStarter, LifeSciencesKeyAccountManager, LifeSciencesFieldSalesRepresentative, LifeSciencesCore}`). More or fewer means the wrong sets were assigned — reconcile before proceeding.

### Phase C — Territory assignment (user + admin)

Assign **both** the KAM user and the admin to the Stage-3 level-3 territory via `UserTerritory2Association`. Confirm with the admin that this is the same territory used for `ProductTerritoryAvailability` in Stage 5. Field details + verification: the details reference.

```bash
sf data query --query "SELECT User.Name, User.Username, Territory2.Name FROM UserTerritory2Association WHERE Territory2Id = '<territoryId>'" --target-org <admin> --json
```

Expect ≥2 rows (KAM user + admin).

### Phase D — Generate the mobile metadata cache

Run entirely as the admin. Create the parent + child `LifeSciMobileMetadataRecord` (both `ValidationCompleted`), call the Connect API generate endpoint with `sf api request rest`, and poll until `Status='Active'`. Full commands, request body, and error table: **`references/stage-6-metadata-cache-generation.md`**.

## Verification Gate

```bash
sf data query --query "SELECT Id, Username, Profile.Name, IsActive FROM User WHERE Username = '<username>'" --target-org <admin> --json
sf data query --query "SELECT Id, Status FROM LifeSciMobileMetadataRecord ORDER BY LastModifiedDate DESC LIMIT 1" --target-org <admin> --json
```

Expect the user `IsActive=true` on `LSC Custom Profile`, permset count = 4, ≥2 territory rows, and a metadata record at `Status='Active'`.

## Credential Handoff

At the end, present the KAM username, the login URL, and the temporary password in the **single** credential-handoff summary. Do not print the password anywhere else.

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Username MUST contain `kam` | KAM-user identification requirement |
| Assign exactly 4 permission sets | KAM users get Health Cloud Starter + Life Sciences Key Account Management + Life Sciences Field Sales Representative + Life Sciences Core |
| Assign the SAME level-3 territory used in Stage 5 | A mismatch hides all product/account data from the KAM user |
| Assign BOTH the user and the admin to the territory | Admin visibility + user data access |
| Write temp files (password Apex, mdgen body) project-local | Never `/tmp` or outside the project |
| Deactivate, never delete, unwanted users | Deletion is unsafe; deactivation cascade-deletes territory associations |
| Print the password only in the single credential-handoff summary | Credential hygiene |

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-6-user-provisioning-details.md` | Phases A–C — user fields, username rule, permsets, password, territory, verification |
| `references/stage-6-metadata-cache-generation.md` | Phase D — parent/child record creation + Connect API generate call + polling |
