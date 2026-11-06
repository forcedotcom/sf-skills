---
name: experience-afv-analytics-query
description: "System-of-record for the public Lightning Instrumentation Headless Connect REST API route that retrieves Agentforce Vibes (AFV) metrics, analytics, data, and adoption/usage insights, including token/LOC, weekly active-user, and per-user activity. Supports local result filtering by period (default current), orgType (default All), recordType, modelName (default All), and other explicitly returned row fields after one parameterless API call."
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  accessCheck: "(DxDevopsAnalytics.orgHasDevopsAnalyticsAccess)"
  domains:
  - "Experience"
  - "Agentforce"
---

# Agentforce Vibes metrics

Use this skill when a user asks to retrieve Agentforce Vibes (AFV) usage or
instrumentation metrics for the current Salesforce org.

This skill describes one public, read-only Connect API operation:

- **Get AFV metrics** — trigger phrases: "get afv metrics", "agentforce vibes metrics", "afv analytics", "fetch agentforce vibes analytics", "headless afv metrics", "afv data", "agentforce vibes data", "get afv adoption usage data", "Vibes adoption", "token/LOC metrics", "weekly active users", "per-user AFV activity", "current or prior AFV metrics", "AFV model metrics", "AFV metrics by org type", and "filter AFV metrics by record type". Primary route: `GET /instrumentation/afv-metrics` (`operationId: getAFVMetrics`).

The route is available at external API version **v68.0 or later**. Call it at
v68.0; do not infer a lower version from the source
spec's generic `info.version` or `servers` example. v67.0 returns
`404 NOT_FOUND`. A version above the org's own maximum also returns `404`;
that is an org limit, not a reason to call a version below v68.0.

## Workflow

1. Call `GET /services/data/v68.0/instrumentation/afv-metrics`.
2. Send no path parameters, query parameters, or request body.
3. Read the returned `AFVMetricsOutputRepresentation`:
   - `success` — whether the metrics download succeeded.
   - `message` — an optional status or failure message.
   - `rows` — an array of metric maps; each map can contain heterogeneous
     metric names and values.
4. If `success` is `false`, surface `message` and the raw response. Do not
   present the rows as a successful metrics result or retry automatically.
5. If `success` is `true` and `rows` is empty, report the no-data result and
   stop. Do not retry, treat it as an API error, or fall back to an internal
   API.
6. Branch on each row's `recordType` before reading class-specific fields.
   Do not assume that any particular record class is present. Preserve unknown
   record types and fields instead of dropping them.

## Optional result filters

Users can narrow the displayed metrics with optional result filters. These
filters control local processing after the complete response is received; they
are not Connect API query parameters or `get-afv-metrics` dispatch inputs.

| Filter | Accepted value | Matching rule |
|---|---|---|
| `period` | `current` (default) or `prior` | Exact match on `rows[*].period`. Reject another explicit value before calling the API. |
| `orgType` | `All` (default) or an org-type value returned by the API | Case-insensitive exact match on `rows[*].orgType`. `All` is a literal roll-up value, not a wildcard. |
| `recordType` | One or more record-type names | Exact match on `rows[*].recordType`. Known values include `aggregate`, `dailyTimeSeries`, `modelMetrics`, `orgBreakdown`, `userMetrics`, and `weeklyActiveUsers`, but accept an exact future value when the user supplies it. |
| `modelName` | `All` (default) or a model name returned by the API | Case-insensitive exact match on `rows[*].modelName`. `All` is a literal roll-up value, not a wildcard. |
| Other returned row field | Explicit field name and value supplied by the user | Exact match only when that field is present. Do not invent aliases or assume the field exists on every record type. |

If the user does not supply `period`, apply `period=current`; if the user does
not supply `orgType`, apply `orgType=All`; if the user does not supply
`modelName`, apply `modelName=All`. These are default local result filters. An
explicit value overrides its corresponding default. A request that compares
the current and prior periods explicitly selects both values and therefore
overrides the single-period default. Likewise, a request to compare or rank
models explicitly selects the concrete model names present in the response
instead of the `All` model roll-up. If the user supplies more than one filter
name, combine them with AND. If the user supplies multiple values for the same
field, match any of those values. Each default still applies when the user
supplies another filter but omits one of these three fields.

Apply filters only after checking HTTP status, `success`, and the unfiltered
`rows` array:

1. Capture the requested result filters from the user's prompt and add the
   defaults `period=current`, `orgType=All`, and `modelName=All` when those
   fields were omitted and the request does not imply a multi-value comparison.
2. Call `get-afv-metrics` once with no arguments and no query string.
3. If `success` is `false` or the complete `rows` array is empty, follow the
   normal response handling without filtering.
4. Otherwise, filter the returned rows in memory and render the matching rows.
5. Report the filters applied, the total rows returned by the API, and the
   number of rows matched.

A successful response with rows but zero filter matches, including when a
default filter finds no rows, is a successful zero-match view, not an empty
API response. Report that the complete response
contained no matching rows. Do not retry, change the request URL, infer zero
metric values, or report that the API itself returned no data. When the
requested `recordType` is `userMetrics`, also apply the permission-dependent
guidance below instead of treating the absence as proof of zero user activity.

## Permission-dependent results

HTTP status is part of the gate and permission contract. Do not treat every
denial as HTTP `200` with `success: false`.

The route returns a metrics body only when the org gate is enabled and the
caller passes the user access check. The user access check passes when any
of these is true:

- the caller has both **Customize Application** and **Modify All Data**, or
- the caller has **Lifecycle Center Developer-Level Insights**, or
- the caller has **Lifecycle Center User**.

- **Org gate disabled, or the caller fails the user access check:** the
  route returns HTTP `403`. Surface the response as an access denial.
  Recommend verifying that AFV metrics are enabled for the org and that the
  caller has `Lifecycle Center User`, `Lifecycle Center Developer-Level
  Insights`, or both Customize Application and Modify All Data. Do not retry,
  and do not present a `403` as an empty dataset or as `success: false`.
- **`Lifecycle Center User` only:** the call can return HTTP `200` with
  `success: true`, but `userMetrics` rows are omitted. The message then
  includes `Some per-user metrics were omitted because you do not have
  permission to view them.` Other record classes remain subject to data
  availability. Absence of `userMetrics` does not prove that no users used
  AFV.
- **`Lifecycle Center Developer-Level Insights`, or Customize Application
  together with Modify All Data:** the caller is eligible to receive rows
  whose `recordType` is `userMetrics` when that class has data. A populated
  System Administrator probe returned those rows with message
  `AFV metrics retrieved successfully.` and no omission sentence.

When the user specifically asks for per-user results and no `userMetrics`
rows are visible, explain that the class can be absent because
`Lifecycle Center Developer-Level Insights` is not assigned or because the
current dataset has no rows of that class. Recommend verifying
`Lifecycle Center Developer-Level Insights`; do not report zero per-user
activity from an absent record class.

## Variable record classes

Production exports show that successful populated responses can contain only a
subset of the known record classes. Treat `aggregate`, `dailyTimeSeries`,
`modelMetrics`, `orgBreakdown`, `userMetrics`, and `weeklyActiveUsers` as
independently optional collections. For a requested class that is absent,
report that the current response contains no rows of that class. Do not infer a
zero value, fail the whole response, or retry. Row counts are data-dependent.

## Output

On success, report the server message when present, the number of rows, and
the rows themselves. Preserve the keys returned in each row; the schema
intentionally permits arbitrary metric-name/value pairs.

```markdown
## AFV metrics

- Success: `<success>`
- Message: `<message, when present>`
- Result filters: `<filters, including period=current, orgType=All, and modelName=All defaults when applicable>`
- Rows returned by API: `<unfiltered rows.length>`
- Rows matched: `<filtered rows.length, when filters are present>`

<render the rows without inventing or renaming fields>
```

For every successful populated response with no user-supplied result filters,
append a compact filter-discovery block even though the default
`period=current AND orgType=All AND modelName=All` view was applied. Compute
distinct values from the full, unfiltered API response and include only fields
that occur in at least one row. Do not present known-but-absent values as
available in the current result, and do not make a second API call.

```markdown
### Available result filters in this response

- `period`: `<distinct rows[*].period values>` (default: `current`)
- `orgType`: `<distinct rows[*].orgType values>` (default: `All`)
- `recordType`: `<distinct rows[*].recordType values>`
- `modelName`: `<distinct rows[*].modelName values>` (default: `All`)

Example: `Get AFV metrics for period=prior, orgType=Sandbox, recordType=modelMetrics, and modelName=<returned model name>.`
```

When user-supplied filters were provided, show the effective filters in
`Result filters` and omit the discovery block. The default
`period=current AND orgType=All AND modelName=All` filters alone do not
suppress discovery. The filter list and example are part of the same final
result, not a follow-up question. Available `orgType` and `modelName` values
are data-dependent; never hardcode values observed in one org.

An empty `rows` array is a valid successful response. The no-data result is
HTTP `200` with `success: true`, message
`No AFV metrics are available yet for this org.`, and `rows: []`. Report
that no metric rows were returned, include the server's message, and stop
without retrying. Distinguish this from `success: false` with `rows: []`,
which is a service failure, and from HTTP `403`, which is an access denial.

## Error handling

- `400` — surface the returned AFV result as a bad request.
- `401` — authentication is missing or invalid; ask the user to reconnect to
  the org, then retry only when they request it.
- `403` — the org gate is disabled or the caller fails the user access check.
  Surface the response and recommend verifying org enablement plus
  `Lifecycle Center User`, `Lifecycle Center Developer-Level Insights`, or
  both Customize Application and Modify All Data. Do not retry automatically.
- `500` — the metrics service failed internally; surface the response and
  advise retrying later.
- HTTP `200` with `success: false` — surface `message` and `rows` as returned.
  The caller-facing service-failure message is
  `Unable to retrieve AFV metrics at this time. Please try again later.`
  This is not a permission or gate denial. Do not recommend a permission
  change for it.
- HTTP `200` with `success: true` and the per-user omission sentence — follow
  the permission-dependent guidance. Do not treat the remaining rows as a
  failure.
- Route not found at a lower API version — retry at v68.0 or later. v67.0
  returns `404`. Do not probe a matrix of versions automatically.
- Rate limiting — the public family enables rate limits. Surface the error and
  do not auto-retry.

## Constraints

- Read-only and idempotent.
- Never send result filters to the server: the operation declares
  `parameters: []`. Apply optional user filters only after the full response is
  received, including the default
  `period=current AND orgType=All AND modelName=All` view.
- Never call the internal Aura-only Lightning Instrumentation Agentforce API;
  this skill uses the separate public headless Connect API family.
- Never infer that an absent record class represents zero-valued data. In
  particular, `userMetrics` can be omitted by permission-based filtering.
- Do not rely on fixed row counts. Counts observed during validation describe
  that test dataset, not the API contract.
- Return one final result. Do not make a follow-up write or verification call.

<!-- skill-validate: ignore-start -->
<!-- codey:operations start -->
## Operations Reference

Operations this skill uses — routing and dependency reference.

| Operation | Purpose | Status | Call | Depends on |
|-----------|---------|--------|------|------------|
| `get-afv-metrics` | read | — | `GET /services/data/v68.0/instrumentation/afv-metrics` | — |
<!-- codey:operations end -->
<!-- skill-validate: ignore-end -->
