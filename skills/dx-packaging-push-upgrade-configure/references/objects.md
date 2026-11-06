# Push upgrade — object reference

All live on the **Dev Hub / License Management Org**, not subscriber orgs.

**Query with the standard data API — NOT `--use-tooling-api`.** `PackageSubscriber`,
`PackagePushRequest`, `PackagePushJob`, and `PackagePushError` return "sObject type not supported"
under the Tooling API; query them with plain `sf data query --target-org <devhub> --query "..."`.
`MetadataPackage` and `MetadataPackageVersion` work under either API — use the standard one for
consistency. (Field lists below were verified via `sf sobject describe`, which works on both APIs and
is not a guarantee the object is Tooling-queryable — the query itself is.)

---

## PackageSubscriber — who has the package installed

The discovery object. One row per org/package install.

| Field | Type | Notes |
|-------|------|-------|
| `Id` | id | |
| `MetadataPackageId` | reference | The **033** package ID. Filter on this to scope to your package. |
| `MetadataPackageVersionId` | reference | The **04t** version the subscriber currently has. Compare to your target to find orgs that are behind. |
| `InstalledStatus` | picklist | `i` = installed, `u` = not installed / uninstalled. Filter `= 'i'`. |
| `OrgKey` | string | **The org ID that goes in the schedule CSV / `--org-list`.** |
| `OrgName` | string | Subscriber org name. |
| `OrgType` | picklist | `Production`, `Sandbox`. Pilot in sandboxes first. |
| `OrgStatus` | picklist | `Active`, `Demo`, `Free`, `Inactive`, `Trial`. Usually skip `Inactive`. |
| `InstanceName` | string | Instance (e.g. `NA123`) — useful proxy for time-zone batching. |
| `ParentOrg` | string | Parent org key (sandboxes trace to a parent). |
| `IsCustomUpgradeAllowed` | boolean | Whether custom upgrade handling is allowed. |
| `CustomUpgradeType` | picklist | `None`, `BlockedBySubscriber`. |
| `HasRestrictionEnabled` | boolean | `true` = subscriber has restricted push upgrades — **exclude these**; pushing to them errors. |
| `SystemModstamp` | datetime | |

---

## MetadataPackageVersion — resolve/validate the target version

| Field | Type | Notes |
|-------|------|-------|
| `Id` | id | The **04t** version ID. |
| `MetadataPackageId` | reference | The **033** package. |
| `Name` | string | Version name. |
| `MajorVersion` / `MinorVersion` / `PatchVersion` / `BuildNumber` | int | Compare against subscriber versions to confirm "strictly higher". |
| `ReleaseState` | picklist | `Beta`, `Released`. Push target must be `Released`. |
| `IsDeprecated` | boolean | Must be `false`. |
| `SystemModstamp` | datetime | |

---

## PackagePushRequest — one scheduled push (the `0DV`)

| Field | Type | Notes |
|-------|------|-------|
| `Id` | id | The **0DV** request ID. |
| `PackageVersionId` | reference | Target 04t version. |
| `ScheduledStartTime` | datetime | The UTC start you requested (null = ASAP). |
| `Status` | picklist | `Created`, `Pending`, `InProgress`, `Succeeded`, `Failed`, `Canceled`. |
| `StartTime` / `EndTime` | datetime | Actual execution window. |
| `DurationSeconds` | int | |
| `IsMigration` | boolean | `true` for 1GP→2GP push migrations. |
| `SystemModstamp` | datetime | |

Note: CLI `--status` filter shows `Cancelled`/`In Progress` (spacing); the object picklist uses
`Canceled`/`InProgress`.

---

## PackagePushJob — one per org within a request

| Field | Type | Notes |
|-------|------|-------|
| `Id` | id | |
| `PackagePushRequestId` | reference | Parent **0DV** request. |
| `SubscriberOrganizationKey` | string | The org this job targets (matches `PackageSubscriber.OrgKey`). |
| `Status` | picklist | `Created`, `Pending`, `InProgress`, `Succeeded`, `Failed`, `Canceled`. |
| `StartTime` / `EndTime` | datetime | |
| `DurationSeconds` | int | |
| `IsMigration` | boolean | |
| `SystemModstamp` | datetime | |

---

## PackagePushError — failure detail, attached to a job

| Field | Type | Notes |
|-------|------|-------|
| `Id` | id | |
| `PackagePushJobId` | reference | Parent job. |
| `ErrorSeverity` | picklist | `Warning`, `Error`. |
| `ErrorType` | picklist | `DeployError`, `ApexTestFailure`, `LockingFailure`, `IneligibleUpgrade`, … |
| `ErrorTitle` | string | Short label. |
| `ErrorMessage` | string | Human-readable message. |
| `ErrorDetails` | string | Extended detail / stack. |
| `SystemModstamp` | datetime | |

---

## ID prefix cheat sheet

| Prefix | Object |
|--------|--------|
| `033` | MetadataPackage (the package) — used by `push-upgrade list`. |
| `04t` | MetadataPackageVersion (the version) — the push **target**, `push-upgrade schedule --package`. |
| `0DV` | PackagePushRequest — returned by `schedule`, consumed by `report`/`abort`. |
| `00D` | Subscriber org ID — the `OrgKey` values in the CSV. |
