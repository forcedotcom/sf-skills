# Example — Monitor failed archive jobs and check their logs

End-to-end flow for the most common archive-admin task: find the jobs that failed or stalled, read why, and check whether logs exist that show which records didn't make it.

## 1. Find the jobs (query ArchiveActivity)

`ArchiveActivity` is not Flow-queryable, so use SOQL/Connect:

```sql
SELECT Id, Name, Status, Type, StartTime, ProgressPercentage,
       TotalRecordCount, SucceededCount, FailedCount, SkippedRootRecordsCount,
       RootEntityName, FailureReason
FROM ArchiveActivity
WHERE (Status = 'Failed' OR Status = 'In Progress' OR Status = 'Ended With Errors')
  AND StartTime >= LAST_N_DAYS:7
ORDER BY StartTime DESC
```

Read each row's `ProgressPercentage`, `SucceededCount`/`FailedCount`, `RootEntityName`, and `FailureReason` to summarize health. In-progress jobs have a blank `EndTime`.

## 2. For each failed job, check whether logs exist

Take the job's `Id` (`8qv…`) as `requestId` and its `Type` as `reportType`. `{activity.Type}` below is a placeholder for that job's own `Type` field value (e.g. `Archive`, `Purge`, `Unarchive`, `Analyzer`) — substitute the actual value per job; a hardcoded/mismatched `reportType` returns no log.

**Execution-detail log:**
```text
GET /platform/data-resilience/archive/log/execution-details-stream-url
    ?requestId={activity.Id}&reportType={activity.Type}
```

**Failed-records log:**
```text
GET /platform/data-resilience/archive/log/failed-records-stream-url
    ?requestId={activity.Id}&reportType={activity.Type}
```

Each returns `{ url }`, a one-time presigned URL. **Use it only to check `url != null`; never echo the value.** A `null` url means no log was resolved for that job/type (e.g. the job produced no failed-records file), not an error to retry blindly.

## 3. Summarize

Per failed/in-progress job, report: Name, Status, ProgressPercentage, SucceededCount, FailedCount, RootEntityName (target object), FailureReason, and whether each log is available ("log available" or "no log available" when `url` is null). Never include raw presigned URLs in summaries or agent output -- they contain time-limited access tokens. If the user needs the log contents, direct them to the Archive Activities page in Setup (`ViewActivitiesPage` access).

## Pitfalls this flow avoids

- **Not** attempting a Flow over `ArchiveActivity` (`isProcessEnabled=false` → "You can't get ArchiveActivity records in a flow").
- Passing the activity's real `Type` as `reportType` (a mismatch returns no log).
- Treating a 201 with `url: null` as a usable log.
- Echoing the presigned `url` in a summary or transcript.
