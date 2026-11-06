# SOQL recipes — subscribers & monitoring

Run all with `sf data query --target-org <devhub> --query "..."` (the **standard** data API — do **not**
add `--use-tooling-api`; the push objects return "sObject type not supported" under Tooling).
Add `--result-format csv` to pipe straight toward a CSV (strip the header before feeding `--org-file`).

Placeholders: `<033>` = package ID, `<04t>` = target version ID, `<0DV>` = push request ID.

---

## Discover subscribers

### All currently-installed subscribers for a package
```sql
SELECT OrgKey, OrgName, OrgType, OrgStatus, InstanceName,
       MetadataPackageVersionId, InstalledStatus, HasRestrictionEnabled, CustomUpgradeType
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i'
```

### Eligible production orgs, excluding restricted and already-on-target
```sql
SELECT OrgKey, OrgName, OrgStatus, InstanceName, MetadataPackageVersionId
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>'
  AND InstalledStatus = 'i'
  AND OrgType = 'Production'
  AND OrgStatus != 'Inactive'
  AND HasRestrictionEnabled = false
  AND CustomUpgradeType != 'BlockedBySubscriber'
  AND MetadataPackageVersionId != '<04t>'
```
> `OrgType` (Production/Sandbox) and `OrgStatus` (Active/Demo/Free/Inactive/Trial) are **independent**
> — a Production org can be `Trial`, `Demo`, or `Free`, not just `Active`. Don't whitelist
> `OrgStatus = 'Active'` or you'll silently drop paying-but-non-`Active` production subscribers. Exclude
> only what you mean to (typically `Inactive`), and select `OrgStatus` so you can eyeball the mix.

### Sandboxes only (pilot batch)
```sql
SELECT OrgKey, OrgName, InstanceName, MetadataPackageVersionId
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i' AND OrgType = 'Sandbox'
  AND HasRestrictionEnabled = false
  AND CustomUpgradeType != 'BlockedBySubscriber'
```

### Restricted / blocked orgs (report, then exclude from pushes)
```sql
SELECT OrgKey, OrgName, HasRestrictionEnabled, CustomUpgradeType
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i'
  AND (HasRestrictionEnabled = true OR CustomUpgradeType = 'BlockedBySubscriber')
```

### Orgs on a specific old version (target a known-bad build)
```sql
SELECT OrgKey, OrgName, OrgType, InstanceName
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i'
  AND MetadataPackageVersionId = '<04t-old-version>'
```

### Count by org type (population sanity check)
```sql
SELECT OrgType, COUNT(Id) total
FROM PackageSubscriber
WHERE MetadataPackageId = '<033>' AND InstalledStatus = 'i'
GROUP BY OrgType
```

> Note: `PackageSubscriber` has **no version-comparison operator** — you can only filter version by
> exact `MetadataPackageVersionId`. To push only to orgs *strictly below* the target, resolve each
> distinct installed version's numbers via `MetadataPackageVersion` and exclude any at/above the
> target before building the CSV.

---

## Resolve / validate versions

### Released versions of a package, newest first
```sql
SELECT Id, Name, MajorVersion, MinorVersion, PatchVersion, BuildNumber, ReleaseState, IsDeprecated
FROM MetadataPackageVersion
WHERE MetadataPackageId = '<033>' AND ReleaseState = 'Released'
ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC
```

### Validate a single target version
```sql
SELECT Id, MetadataPackageId, Name, MajorVersion, MinorVersion, PatchVersion, BuildNumber,
       ReleaseState, IsDeprecated
FROM MetadataPackageVersion
WHERE Id = '<04t>'
```
Target is valid only if `ReleaseState = 'Released'` and `IsDeprecated = false`.

---

## Monitor push requests

### Recent requests for a package
```sql
SELECT Id, PackageVersionId, Status, ScheduledStartTime, StartTime, EndTime, DurationSeconds, IsMigration
FROM PackagePushRequest
WHERE PackageVersionId IN (
  SELECT Id FROM MetadataPackageVersion WHERE MetadataPackageId = '<033>'
)
ORDER BY ScheduledStartTime DESC
```

### Jobs (per-org) for one request
```sql
SELECT Id, SubscriberOrganizationKey, Status, StartTime, EndTime, DurationSeconds
FROM PackagePushJob
WHERE PackagePushRequestId = '<0DV>'
ORDER BY Status
```

### Job status rollup for one request
```sql
SELECT Status, COUNT(Id) total
FROM PackagePushJob
WHERE PackagePushRequestId = '<0DV>'
GROUP BY Status
```

### Errors for a request (join through jobs)
```sql
SELECT PackagePushJobId, ErrorSeverity, ErrorType, ErrorTitle, ErrorMessage, ErrorDetails
FROM PackagePushError
WHERE PackagePushJobId IN (
  SELECT Id FROM PackagePushJob WHERE PackagePushRequestId = '<0DV>'
)
```

### Errors grouped by type (decide what to re-push)
```sql
SELECT ErrorType, ErrorSeverity, COUNT(Id) total
FROM PackagePushError
WHERE PackagePushJobId IN (
  SELECT Id FROM PackagePushJob WHERE PackagePushRequestId = '<0DV>'
)
GROUP BY ErrorType, ErrorSeverity
```
