# AFV Connect API reference

## Authoritative Core contract

The API was introduced by Core pull request 25670. The accepted IDL-first API
definition and implementation are the authority for the contract summarized
here.

Contract facts used by this skill:

- Public, REST-callable Connect API.
- Available at external API v68.0 or later.
- Route: `GET /instrumentation/afv-metrics`.
- Operation: `getAFVMetrics`.
- No request parameters.
- Rate limiting enabled.
- API integrations declared for Catalog, Flow, Agentforce, and MCP.
- No Aura controller or LDS adapter is generated for this family.

The generated unified OpenAPI document must advertise
`/services/data/v68.0` in `servers[0].url`. The skill-derived base generator's
generic v67.0 server is not valid for this route: a live probe returned
`404 NOT_FOUND` at v67.0, and the same route returned the AFV response at
v68.0 and v69.0. A version above the org catalog maximum also returns `404`;
that limit is not a route restriction.

The generated unified OpenAPI projection must keep the six known
`recordType` values on the property itself. The description may explain that
future values are possible, but it must not remove this `enum` metadata:

```yaml
recordType:
  type: string
  enum:
    - aggregate
    - modelMetrics
    - dailyTimeSeries
    - weeklyActiveUsers
    - orgBreakdown
    - userMetrics
```

## Response representation

`AFVMetricsOutputRepresentation` is an object with:

| Field | Type | Meaning |
|---|---|---|
| `success` | boolean | Whether the dashboard-metrics download succeeded. |
| `message` | string | Optional status or failure detail. |
| `rows` | array of object maps | Dashboard metric rows. Each row permits arbitrary property names and value types. |

The implementation delegates to the existing dashboard metrics service and
copies its `success`, `message`, and `rows` values directly into the public
representation.

An empty dataset is still a successful response: HTTP `200` with
`success: true`, message `No AFV metrics are available yet for this org.`,
and `rows: []`.

A populated success response uses message
`AFV metrics retrieved successfully.` A service failure that still returns
HTTP `200` uses `success: false` and message
`Unable to retrieve AFV metrics at this time. Please try again later.`

## Result-filtering boundary

The operation has no path, query, or body parameters. User phrases such as
`period=current`, `orgType=Sandbox`, `recordType=modelMetrics`, or
`modelName=<name>` are skill-level result filters, not part of the Connect API
request. The runtime must first call the parameterless endpoint and then filter
the complete `rows` array in memory.

The supported filter semantics are:

- `period` defaults to `current` when the user does not supply one. An explicit
  `current` or `prior` value overrides the default and matches
  `rows[*].period` exactly. A comparison request can explicitly select both
  values, which uses OR semantics within the field.
- `orgType` defaults to the literal `All` roll-up when the user does not supply
  an org type. An explicit value overrides the default and uses a
  case-insensitive exact match against `rows[*].orgType`; `All` is not a
  wildcard.
- `recordType` matches one or more exact discriminator values. The known
  record classes are examples, not a closed enum; a future value can be used
  when it is actually returned.
- `modelName` defaults to the literal `All` roll-up when the user does not
  supply a model. An explicit model name overrides the default and uses a
  case-insensitive exact match. A request to compare or rank models selects
  the concrete model names present in the response instead of the `All`
  roll-up; those names must be derived from the response rather than hardcoded.
- Another explicitly named row field can be matched exactly, but the consumer
  must not invent aliases or assume the field exists on every heterogeneous
  row.
- Different filter names use AND semantics; multiple values for one field use
  OR semantics. The defaults `period=current`, `orgType=All`, and
  `modelName=All` participate in the AND expression whenever the user omits the
  corresponding field and does not request a multi-value comparison.

Unknown query parameters are silently ignored by the live endpoint, so a
filter-shaped URL can return HTTP `200` and the same unfiltered body. A zero-row
result after local filtering therefore means "no rows in the complete response
matched these filters," which is distinct from the API returning `rows: []`.
When the requested filter is `recordType=userMetrics`, the permission-dependent
absence rules still apply; zero matches do not establish zero user activity.
The SOR step inputs and OpenAPI operation parameters must remain empty.

For a successful populated call without user-supplied filters, the final result
should render the default
`period=current AND orgType=All AND modelName=All` view and advertise the
filter values available in the complete response. Derive the distinct
non-empty `period`, `orgType`, `recordType`, and `modelName` values from the
unfiltered `rows` and include only fields that are present. This is response
discovery, not a second API operation. Available `orgType` and `modelName`
values are org- and time-dependent and must never be copied into the skill as
fixed lists.

## Permission-dependent responses

The public permission-set labels are `Lifecycle Center User` and
`Lifecycle Center Developer-Level Insights`. HTTP status changes when the
org gate is disabled or the caller fails the user access check.

The user access check passes when the caller has both Customize Application
and Modify All Data, or has `Lifecycle Center Developer-Level Insights`, or
has `Lifecycle Center User`.

| Access state | HTTP | Body |
|---|---|---|
| Org gate disabled, or the caller fails the user access check | `403` | Access denial. Not a metrics body with `success: false`. |
| `Lifecycle Center User` only | `200` | `success: true`. `userMetrics` rows are omitted, and the message includes `Some per-user metrics were omitted because you do not have permission to view them.` |
| `Lifecycle Center Developer-Level Insights`, or Customize Application with Modify All Data | `200` | Eligible for `userMetrics` when that class has data. A populated System Administrator probe returned `success: true`, message `AFV metrics retrieved successfully.`, and `userMetrics` rows, with no omission sentence. |

The structural conclusions are:

- A disabled org gate and a failed user access check both return HTTP `403`.
  Callers must surface that status instead of the older HTTP `200` service
  failure.
- `Lifecycle Center User` is enough to call the route, but not enough to
  receive `userMetrics`.
- `Lifecycle Center Developer-Level Insights` controls visibility of
  `userMetrics`. Customize Application together with Modify All Data also
  receives that class.
- Missing `userMetrics` rows on an HTTP `200` are an authorization-filtered
  representation, not proof that the org has no per-user activity.
- `success: false` with
  `Unable to retrieve AFV metrics at this time. Please try again later.`
  is a service failure inside HTTP `200`. It is not the permission or gate
  denial.
- `success: true`, `rows: []`, and
  `No AFV metrics are available yet for this org.` remain a distinct, valid
  empty-dataset response.

## Production record-class variability

The supplied production exports use the same field vocabulary but contain
different record-class combinations. Some responses contain only
`aggregate`, `dailyTimeSeries`, and `modelMetrics`; others add
`orgBreakdown` and `userMetrics`; and some also contain
`weeklyActiveUsers`. The number of rows in every class also varies by org and
over time.

Consequently, none of the known record classes or their row counts is required
for a successful populated response. Consumers must branch on the
`recordType` of each returned row, handle an absent requested class as
unavailable in the current response, and preserve unknown future classes and
fields. Permission filtering remains one possible reason that `userMetrics` is
absent, but absence alone does not identify the cause.

## Declared responses

The source OAS declares `200`, `400`, `401`, `403`, and `500`. The `403`
response is the declarative access denial: the org gate is disabled or the
user access check fails. These are contract declarations. The populated
success path was wire-probed; the `403` path was not reproduced on an
administrator session where the gate was open.
