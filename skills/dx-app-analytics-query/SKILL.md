---
name: dx-app-analytics-query
description: "ISV App Analytics metadata types — AppAnalyticsQueryRequest and AppAnalyticsSettings. Use this skill when the user asks about retrieving managed package usage data, configuring App Analytics simulation mode, querying subscriber snapshots, or understanding the AppAnalyticsQueryRequest lifecycle (New → Pending → Complete → Expired). TRIGGER when: user mentions App Analytics, AppAnalyticsQueryRequest, AppAnalyticsSettings, package usage data, subscriber analytics, ISV analytics, or simulation mode for app analytics. DO NOT TRIGGER when: the task is about standard Salesforce reports/dashboards (use reporting skills), custom SOQL on Account/Contact (use platform-soql-query), or Data Cloud query/search (use data360-query)."
metadata:
  version: "1.0"
  minApiVersion: "56.0"
---

# App Analytics

## When This Skill Owns the Task

Use `dx-app-analytics-query` when the work involves:
- Creating `AppAnalyticsQueryRequest` records via the REST/sObject API
- Configuring `AppAnalyticsSettings` via the Metadata API (simulation mode, opt-out)
- Understanding the query lifecycle: New → Pending → Complete → Expired → Failed
- Choosing between dataType values: PackageUsageSummary, PackageUsageLog, SubscriberSnapshot
- File format and compression options for analytics downloads
- Time-range filtering with startTime, endTime, availableSince
- Troubleshooting failed or expired analytics queries

Delegate elsewhere when the user is:
- Running standard CRM SOQL queries → platform-soql-query
- Working with Data Cloud SQL or DMOs → data360-query
- Building reports/dashboards on standard objects → reporting skills
- Deploying or retrieving generic metadata XML → platform-metadata-deploy / retrieving-metadata

---

## Available Types

### AppAnalyticsQueryRequest (REST/sObject API)

An asynchronous query request that ISV partners use to retrieve usage analytics data for their managed packages from the ISV Intelligence Data Lake. Records are created via `POST /services/data/vXX.0/sobjects/AppAnalyticsQueryRequest` and polled via `GET /services/data/vXX.0/sobjects/AppAnalyticsQueryRequest/<id>`. The system processes the query and provides a presigned download URL upon completion.

**Fields (14 properties):**

| Field | Type | Description |
|-------|------|-------------|
| DataType | string (filterable) | Type of analytics data. Values: `PackageUsageSummary`, `PackageUsageLog`, `SubscriberSnapshot` |
| RequestState | string (filterable) | Processing status. Values: `New`, `Pending`, `Complete`, `Expired`, `Failed`, `NoData`, `Delivered` |
| StartTime | string | Start of time range for requested data |
| EndTime | string | End of time range. Should be set on an hour boundary |
| AvailableSince | string | Limits query to data indexed after this time (inclusive). Use for incremental retrieval |
| PackageIds | string | Comma-delimited list of managed package IDs (033-prefix) |
| OrganizationIds | string | Comma-delimited list of subscriber org IDs to filter results |
| DownloadUrl | string | Presigned URL for downloading results. Populated when RequestState is Complete |
| DownloadSize | long | Size in bytes of the result data file |
| DownloadExpirationTime | string | Time at which the download URL expires |
| FileType | string (filterable) | Output format. Values: `csv`, `parquet` |
| FileCompression | string (filterable) | Compression. Values: `none`, `gzip`, `snappy` |
| QuerySubmittedTime | string | Time the query was submitted to the Data Lake |
| ErrorMessage | string | Diagnostic message for failed queries |

### AppAnalyticsSettings (Metadata API)

Configuration settings for ISV App Analytics that control simulation mode and opt-out behavior. Deployed via the Metadata API (`sf project deploy`) or Tooling API.

**Fields (2 properties):**

| Field | Type | Description |
|-------|------|-------------|
| enableSimulationMode | boolean (filterable) | When true, allows querying sample usage logs for integration testing without real subscriber data |
| enableAppAnalyticsOptOut | boolean (filterable) | When true, opts this subscriber org out of AppExchange App Analytics data collection |

---

## Request Lifecycle

```text
New → Pending → Complete → (download within expiration window)
                         → Expired (download URL no longer valid)
                         → Delivered (download confirmed received)
         → Failed (check errorMessage)
         → NoData (no matching records for the criteria)
```

---

## Common Patterns

### Query Package Usage Summary (last 7 days)

Create a record via the REST API:

```bash
POST /services/data/v60.0/sobjects/AppAnalyticsQueryRequest
Content-Type: application/json

{
  "DataType": "PackageUsageSummary",
  "StartTime": "<7-days-ago>T00:00:00Z",
  "EndTime": "<today-on-hour-boundary>T00:00:00Z",
  "PackageIds": "033XXXXXXXXXXXX",
  "FileType": "csv",
  "FileCompression": "gzip"
}
```

Poll the record via GET until `RequestState` reaches `Complete`, then download from `DownloadUrl`.

### Incremental Data Retrieval

Set `AvailableSince` to the timestamp of your last successful query completion to avoid re-downloading data you already have.

### Enable Simulation Mode for Testing

Deploy `AppAnalyticsSettings` via Metadata API with `enableSimulationMode: true` to query sample data without real subscribers.

---

## High-Signal Gotchas

- AppAnalyticsQueryRequest is an **sObject** — create and poll records via the REST Data API (`/sobjects/AppAnalyticsQueryRequest`), NOT via Metadata API XML deployment.
- AppAnalyticsQueryRequest does NOT have Apex triggers and does NOT flow through custom objects or Flows.
- Download URLs expire — always check `DownloadExpirationTime` before attempting download.
- `EndTime` should be set on an hour boundary for consistent results.
- `AvailableSince` is inclusive — data indexed at exactly that timestamp will be included.
- `PackageIds` uses 033-prefix IDs, not 04t (package version) IDs.
- Data is processed asynchronously by the ISV Intelligence Data Lake infrastructure. There is no synchronous query option.
- `FileType: parquet` with `FileCompression: snappy` gives optimal performance for large datasets.

---

## Output Format

```text
Analytics task: <query / configure / troubleshoot>
Data type: <PackageUsageSummary / PackageUsageLog / SubscriberSnapshot>
Package IDs: <033-prefixed IDs>
Time range: <startTime> to <endTime>
File format: <csv|parquet> / <none|gzip|snappy>
Request state: <current state>
Next step: <poll for completion / download / investigate failure>
```
