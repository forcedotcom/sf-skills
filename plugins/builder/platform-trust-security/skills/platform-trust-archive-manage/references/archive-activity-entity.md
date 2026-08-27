# ArchiveActivity — Data Model Reference

`ArchiveActivity` is the platform entity that records **job metadata for Salesforce Archive jobs** (archive, purge, analyze, unarchive, export). Every archive job produces one `ArchiveActivity` record; you read it to learn a job's status, progress, and outcome, and you use its `Id` + `Type` to download the job's logs.

## Entity facts

| Property | Value |
|----------|-------|
| API name | `ArchiveActivity` |
| Key prefix | `8qv` (record Ids start `8qv…`) |
| Owning product | Salesforce Archive (Trusted Services Archive) |
| Kind | **Standard platform entity** (not a custom object) |
| License gate | Requires the Trusted Services Archive add-on — absent on orgs without the add-on |
| Name field | Auto-number, mask `ARCV-{0000000000}` |
| Flow-enabled? | **No** — `isProcessEnabled=false`. A Flow "Get Records" element on it fails: "You can't get ArchiveActivity records in a flow." Query via SOQL / Connect / Reports. |

## Fields

| Field | Type | Meaning |
|-------|------|---------|
| `Name` | Auto-number | `ARCV-…` job identifier |
| `Status` | enum `ArchiveActivityStatus` | Lifecycle: scheduled, running / **In Progress**, completed, **Failed**, canceled, **Ended With Errors** |
| `Type` | enum `ArchiveActivityType` | The job mode: Archive, Purge, Analyze(r), Unarchive, Export-to-external-bucket, Export-and-download. **This is the `reportType` for log downloads.** |
| `StartTime` | DateTime | When execution began |
| `EndTime` | DateTime | When execution finished/terminated (blank while running) |
| `ArchivePolicyDefinition` | Lookup (FK) | Parent `ArchivePolicyDefinition`; child relationship `ArchiveActivities` |
| `RootEntityName` | Text | API name of the target sObject being archived |
| `TotalRecordCount` | Long | Records initially selected (succeeded + failed + skipped) |
| `AttemptedRootRecordsCount` | Long (formula) | `SkippedRootRecordsCount + FailedCount + SucceededCount` — top-level records actually attempted |
| `SkippedRootRecordsCount` | Long | Top-level records skipped (validation, exclusion filters, data-protection thresholds) |
| `SucceededCount` | Long | Records processed without error |
| `FailedCount` | Long | Records that failed (validation, missing refs, exceptions) |
| `ProgressPercentage` | Double | Percent complete |
| `FailureReason` | Long text | Why the job failed/partially completed (system error messages or policy-level failures) |
| `RecordsSizeInMb` | Text | Estimated total size of processed records (MB) |

> The entity also defines a `ProgressIcon` display formula for list views; it is not useful for programmatic monitoring — read `Status`, `ProgressPercentage`, and the count fields directly.

## How ArchiveActivity links to the Connect API

The log-download endpoints (`get-execution-details-stream-url`, `get-failed-records-stream-url`) take:

- `requestId` = an `ArchiveActivity` **`Id`** (`8qv…`) of a completed, log-producing job, and
- `reportType` = that same activity's **`Type`** value.

So the monitoring pattern is: **query `ArchiveActivity` → pick the job(s) of interest → pass each job's `Id` and `Type` to the stream-url operation → check `url != null`.** See `../examples/monitor-failed-jobs.md`.

## Example SOQL

```sql
-- Failed or in-progress jobs in the last 7 days, newest first
SELECT Id, Name, Status, Type, StartTime, EndTime, ProgressPercentage,
       TotalRecordCount, SucceededCount, FailedCount, SkippedRootRecordsCount,
       RootEntityName, FailureReason, ArchivePolicyDefinitionId
FROM ArchiveActivity
WHERE (Status = 'Failed' OR Status = 'In Progress' OR Status = 'Ended With Errors')
  AND StartTime >= LAST_N_DAYS:7
ORDER BY StartTime DESC
```
