---
name: platform-trust-archive-manage
description: "ALWAYS USE THIS SKILL for anything involving Salesforce Archive (also called Trusted Services Archive) — search, view, unarchive, analyze, mask, and erase (RTBF) archived records via the Archive Connect API, and reading archive job status from the ArchiveActivity object. TRIGGER when: user mentions Salesforce Archive, Trusted Services Archive, archive/unarchive records, ArchiveActivity, archive jobs, archive policy, archive analyzer, archived record search, archive storage, archive failure logs, right to be forgotten / RTBF on archived data, or masking archived PII — including phrasings like 'find records that were archived', 'restore archived data', 'why did the archive job fail', 'download the archive failure log', or 'monitor my archive jobs', AND even when they ask you to explain, give guidance, or write a runbook/doc about these topics rather than run code. SKIP when: the user wants generic data-export/backup unrelated to the Archive add-on, or wants to build the archive policy UI metadata."
metadata:
  version: "1.0"
---

# Salesforce Archive

Operate Salesforce Archive (also called Trusted Services Archive) through its Connect API and the `ArchiveActivity` job-metadata object. This skill covers how to search and restore archived records, run the analyzer, handle RTBF erasure and PII masking, check storage, and — the part most often missed — how to read archive job status from `ArchiveActivity` and use a job's Id + Type to download its logs.

## Scope

- **In scope**: Calling the Archive Connect API operations under `/platform/data-resilience/archive/`; querying the `ArchiveActivity` object via SOQL/Connect; correlating a job's `ArchiveActivity` record with its log-download endpoints; the verify-after-write pattern for each async operation.
- **Out of scope**: Defining archive policies / `ArchivePolicyDefinition` metadata; building UI; generating Flows over archive data (`ArchiveActivity` is **not** Flow-queryable — see Gotchas); generic backup/export tooling unrelated to the add-on.

---

## Required Inputs

Gather or infer before acting:

- **Operation intent**: search, view, unarchive, analyze, mask, RTBF, storage check, or job-status/log lookup.
- **Target sObject** (`sobjectName`): required for search and unarchive.
- **Filters**: search and unarchive require `sobjectName` + at least one filter.
- **For log downloads**: the `requestId` (an `ArchiveActivity` Id, `8qv…` prefix) of a completed, log-producing job, and `reportType` = that activity's `Type`.

Preconditions (confirm or surface to the user if a call returns a not-permitted error):
- The **org** must have Salesforce Archive enabled (the `TrustedServicesArchive` / `TrustedServicesArchiveBt` org permission). Every operation is gated on this first.
- Each operation requires a **specific user permission** on top of the org gate — see the Permissions table below. There is no single "archive admin" role; access is per-capability.

---

## Permissions

Every operation first requires the org to have Salesforce Archive enabled (`hasTrustedServicesArchive` = `OrgPermissions.TrustedServicesArchive || TrustedServicesArchiveBt`). On top of that org gate, each capability is gated by a distinct **user permission**. A call the user isn't permitted for fails with a "not permitted" error — match the error to the missing permission below.

| Operation | User permission required |
|-----------|--------------------------|
| `search-archived-records`, `get-search-archived-records-next-page` | `ViewSearchPage` (Archive Search) — the Connect search endpoint runs the global-search path, gated by Archive Search, **not** `ViewArchivedRecords` |
| `search-archived-records-with-sharing-rules` (Agentforce) | `ViewArchivedRecords` |
| `unarchive-records` | `UnarchiveSdk` |
| `forget-archived-records` (RTBF) + `get-rtbf-status` | `Rtbf` |
| `mask-archived-records` + `get-masking-status` | `Rtbf` (masking shares the same `Rtbf` permission — **not** a separate entitlement) |
| `run-analyzer`, `get-analyzer-report`, `get-archive-storage-used` | `ArchiveAnalyzer` |
| `get-execution-details-stream-url`, `get-failed-records-stream-url` | `ViewActivitiesPage` (Archive Activities) |

> Source of truth: the Connect API resource classes in `trusted-services-archive-connect-impl` → `TrustedServicesArchiveSdkImpl` guards → `TrustedServicesArchive.accessChecks.xml`. Note `search-archived-records` routes through `performArchiverGlobalSearch` (gated by `canRunArchiveSearch` = `ViewSearchPage`); the separate Apex-SDK `searchArchivedRecords()` method is gated by `ViewArchivedRecords`, but the **Connect API** search endpoint does not use it.

---

## Workflow

All steps are sequential within a task. Read the referenced file the first time you touch that area.

1. **Identify the operation and read the contract** — do not rely on general knowledge of the Archive API, which has non-obvious contracts. Load `references/connect-api-operations.md` for the exact request/response shape, required inputs, and per-operation gotchas of every Archive Connect API operation. Do this before constructing any call (e.g. `dateRanges` plural vs singular, `isSuccess` flag vs HTTP status, `url: null` meaning no log).

2. **For job status / monitoring, read the data model** — when the task involves archive jobs, failures, progress, counts, or logs, load `references/archive-activity-entity.md` for the `ArchiveActivity` field reference and how it links to the Connect API. Query `ArchiveActivity` via SOQL or Connect — **not** Flow. For a worked end-to-end example (find failed/in-progress jobs, then pull their execution-detail and failed-records logs), load `examples/monitor-failed-jobs.md`.

3. **Construct and send the call** — follow the contract exactly. For searches, supply `sobjectName` + ≥1 filter; for date filtering use the plural `dateRanges` array of `{field, from, to}` with full ISO-8601 datetimes.

4. **Branch on the right signal** — some operations return HTTP 201 with a body-level success flag (`body.statusCode`, `body.isSuccess`). Read `references/connect-api-operations.md` for which signal to trust per operation; never assume the HTTP status alone means success.

5. **Verify after every write** — re-read state to confirm the effect (see the Verify-After-Write table below). Async operations (analyzer, RTBF, masking) return a request id you must poll.

---

## Verify-After-Write

| After this write | Confirm by |
|------------------|-----------|
| `run-analyzer` | Poll `get-analyzer-report` until the report is populated |
| `unarchive-records` | Re-run `search-archived-records` — confirm records left the archive |
| `forget-archived-records` (RTBF) | Poll `get-rtbf-status` with the returned `request_id` |
| `mask-archived-records` | Poll `get-masking-status` with the returned `request_id` |

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Search & unarchive require `sobjectName` + at least one filter | The controller rejects an unfiltered request with "Search must be based on at least 1 field" — a full-object operation is never allowed. |
| Date filters must be full ISO-8601 datetimes (`2020-01-01T00:00:00Z`) | A date-only value (`2020-01-01`) returns `400 JSON_PARSER_ERROR` because the field is typed `xsd:dateTime`. |
| Search uses `dateRanges` (plural array); unarchive uses `dateRange` (singular) | They are genuinely different fields on the two endpoints; using the wrong shape silently drops the filter or 400s. |
| Stop pagination when `scroll_id == "-1"` | Calling `get-search-archived-records-next-page` with `"-1"` returns 500. |
| Log downloads need a real `ArchiveActivity` Id as `requestId` + that activity's `Type` as `reportType` | The backend resolves the log by the activity record; a mismatched `reportType` returns no log. |
| Never use the deprecated lookups | `global-search-by-id`, `get-global-search-results`, and `view-archived-records` are deprecated with no successor and currently 500. Use `search-archived-records` (+ next-page) instead. |
| Excluded objects are not retrievable | `Feed`, `History`, `Relation`, `Share` are not searchable; Files/Attachments are not retrievable via this API — do not promise them. |
| Query `ArchiveActivity` via SOQL/Connect, never Flow | `ArchiveActivity` has `isProcessEnabled=false`, so a Flow "Get Records" element on it fails with "You can't get ArchiveActivity records in a flow." |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Treating HTTP 201 as success | Several operations return 201 with a body-level outcome. Branch on `body.statusCode` (search) or `body.isSuccess` (`with-sharing-rules`), not the HTTP code. |
| `run-analyzer.isRunning` used as a signal | It is **always** `null`; the endpoint only populates `message`. Poll `get-analyzer-report` to confirm completion instead. |
| `search-archived-records-with-sharing-rules` (Agentforce) filters as an array | `filtersJson` must be a JSON-encoded **object map** `{"Field":"Value"}`, not an array of `{field,value}`; the array form returns `isSuccess:false "No valid filters provided"`. |
| Log `url` treated as present because status is 201 | `get-*-stream-url` returns `{url}`; `url: null` means no log was resolved. Always check `url != null`. |
| Misreading `get-archive-storage-used` | `usedStorage[]`/`availableStorage[]` are parallel positional arrays: index 0=org DATA, 1=org FILE, 2=archive RECORDS, 3=archive FILE. `availableStorage[2]`/`[3]` are **always 0** (archive tier is unmetered) — that means "not tracked", not "full". |
| Expecting `ArchiveActivity` in a Flow | It is not Flow-enabled (`isProcessEnabled=false`). Use SOQL/Connect/Reports. |
| Hitting unarchive caps | Unarchive processes ≤1000 matched records per request and ≤50 requests/hour/org, and restores the whole archived hierarchy of each match. |
| RTBF/masking caps | `criteria` ≤10 entries (one per object); ≤10,000 root records/day (shared between RTBF and masking); masking is irreversible. Both RTBF and masking are gated by the same `Rtbf` user permission. |

---

## Output Expectations

This is a knowledge/API skill — it produces API calls and their interpreted results, plus SOQL against `ArchiveActivity`. It does not generate deployable metadata. Deliverables per task: the correct operation invocation(s), the right success-signal branching, and a verify-after-write confirmation.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/connect-api-operations.md` | Before constructing any Archive Connect API call — full per-operation contracts, success signals, and limits |
| `references/archive-activity-entity.md` | For any job-status / failure / progress / log task — `ArchiveActivity` field reference and its link to the log-download endpoints |
| `examples/monitor-failed-jobs.md` | To follow an end-to-end monitoring flow: find failed/in-progress jobs, then download their logs |
