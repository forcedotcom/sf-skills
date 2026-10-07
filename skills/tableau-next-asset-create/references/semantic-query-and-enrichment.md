# Semantic Query & Enrichment Reference

Field-shape matrix, aggregation mapping, and worked payloads for querying an
SDM and enriching it with calculated fields and metrics. Substitute apiNames
from `list_*` — do not copy example names into a live call.

> **Our MCP is NOT the REST gateway.** Public/Cursor "semantic-query" guides
> target `POST /services/data/vXX/semantic-engine/gateway` with a **camelCase**
> body (`tableField`, `rowGrouping: true`, `semanticAggregationMethod`). The
> MCP `run_semantic_query` tool takes a **proto-shaped snake_case** body
> (`table_field`, `grouping: "ROW_GROUPING"`, `semantic_aggregation_method`).
> Do not copy camelCase payloads — they fail. Use the shapes here.

## Contents

- run_semantic_query — top-level body (`semantic_context` nested there)
- Field-shape matrix
- options block
- Reading the response
- Query recovery
- Worked query (verified): sum of a measure by a joined dimension
- Detail rows (`detailed_rows: true`)
- Filtered query (`filter.binary_predicate`)
- Enrichment — calculated dimension
- Enrichment — calculated measure
- Enrichment — metric (named, time-bound KPI)

## run_semantic_query — top-level body

```jsonc
{
  "semanticModelApiName": "<SDM apiName>",   // NOT semanticModelId (deprecated here)
  "source": "tableau-next-pilot-mcp",
  "dataspace": "default",                     // omit unless multi-dataspace
  "structuredSemanticQuery": { "fields": [...], "options": {...} }
  // OR structuredMetricQuery — mutually exclusive; do not send both
}
```

Only `fields`, `filter` XOR `flatten_filter` (never both), `options`,
`semantic_context`, `aggregate_filter`, `parameters` are valid keys inside
`structuredSemanticQuery`. Putting `limit`, `sort_orders`, or `row_grouping`
at that level fails with `Cannot find field: <key>`. Prefer
`options.limit_options.limit` + `sort_orders` for top-N over proto
`top_n_filter`.

Pass **ONE** of `structuredSemanticQuery` (recommended) **OR**
`structuredMetricQuery` (alternative) — mutually exclusive dispatch paths.
Do not send both. Outer-request `context` (`timezone`, `locale`) is distinct
from per-query `semantic_context`. Most queries omit `semantic_context` — the
engine picks defaults. Pass it when fiscal-year filters or timezone-sensitive
date math matters:

```jsonc
"semantic_context": {
  "timezone": { "id": "America/Los_Angeles" },
  "locale":   { "code": "en_US" }
}
```

Query is org-level / SDM-level — it does **NOT** take a `workspaceId`. Any SDM
visible via `list_semantic_models` is queryable regardless of workspace.

Treat any **2xx** as success (the wrapper has been observed to return 201).
Provisioning is gated on `orgHasDataCloudReportingEnabled` OR
`orgHasSemanticQuery` — a permission error is a **provisioning gap**, not a
caller payload bug.

## Field-shape matrix

| Field kind | expression | grouping / aggregation |
|---|---|---|
| **Raw dimension** | `{ "table_field": { "name": "<dimApiName>", "table_name": "<objApiName>" } }` | `"grouping": "ROW_GROUPING"` |
| **Raw measure** | `{ "table_field": { "name": "<measApiName>", "table_name": "<objApiName>" } }` | `"semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_<AGG>"` |
| **Calculated dimension** | `{ "semantic_field": { "name": "<calcDimApiName>" } }` | `"grouping": "ROW_GROUPING"` |
| **Calculated measure** | `{ "semantic_field": { "name": "<calcMeasApiName>" } }` | `"semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_USER_AGG"` (for AVG/ratio/COUNTD expressions) |

- `table_name` MUST be the SDM **data-object apiName** from
  `list_semantic_model_data_objects` — NOT the `__dll`/`__dlm` source name
  (that → `Failed to resolve table`).
- `name` MUST be the **suffixed** field apiName from
  `list_semantic_model_dimensions` / `list_semantic_model_measures`.
- `semantic_field` is ONLY for **calculated** SDM fields. It takes ONLY
  `name` (no `table_name`). Using `semantic_field` for a raw/physical column
  fails `Failed to resolve semantic field <name>...`. Rule of thumb:
  calculated → `semantic_field`; physical column → `table_field`.
- `alias` convention: `"<objApiName>.<fieldApiName>"` for table fields,
  `"<apiName>"` for semantic (calculated) fields.
- A third shape, on-the-fly `calculated_field`, exists; prefer a pre-defined
  calc on the model over inventing one in the query.
- **In an aggregated query, every measure needs `semantic_aggregation_method`.**
  A measure with no aggregation is treated as a detail row and errors
  `Detail Rows with Metric must have the corresponding dimension` — this fires
  on the **MISSING aggregation**, NOT a missing dimension (adding
  `ROW_GROUPING` does NOT satisfy it). A grouping dimension is optional
  (measure-only = grand total). **Exception:** `options.detailed_rows: true` is
  the one shape where omitting the aggregation method is valid.

### Aggregation method enum

Valid query-time suffixes only: `SUM`, `AVG`, `COUNT`, `MIN`, `MAX`,
`UNIQUE_COUNT`, `USER_AGG`. Map the model's `aggregationType` enum value (left)
to the query-time suffix (right): `Sum→SUM`, `Average→AVG`, `Count→COUNT`,
`CountDistinct→UNIQUE_COUNT`, `Min→MIN`, `Max→MAX`. Note the model enum uses
`Average` (not `Avg`), and there is no `SEMANTIC_AGGREGATION_METHOD_COUNTDISTINCT`
at query time — `CountDistinct` maps to `SEMANTIC_AGGREGATION_METHOD_UNIQUE_COUNT`,
a distinct enum value from plain `COUNT` (`COUNT` counts all rows; `UNIQUE_COUNT`
counts distinct values). A calculated measure whose expression already
aggregates uses `USER_AGG`.

## options block

```jsonc
"options": {
  "limit_options": { "limit": 10 },
  "sort_orders": [ { "simple_sort_order": { "sort_by_field_alias": "<alias>", "sorting_order": "DESC" } } ],
  "grand_total": true        // OR "detailed_rows": true — never both
}
```

- Aggregate query (≥1 measure/calc measure): `grand_total: true` adds a total
  row. Detail query (dimensions only): `detailed_rows: true`. (These two
  option flags are documented independently in the schema; whether they
  combine is **unverified** — the worked query below used neither.)
- Aggregate queries should include ≥1 dimension with `ROW_GROUPING` (a
  measure-only query returns a single grand-total row — valid for "total X").

## Reading the response

Double-wrapped: parse `JSON.parse(response.defaultExc)`. Treat any **2xx** as
success (wrapper has been observed to return 201). Then:
`status === "SUCCESS"`; `queryResults.queryMetadata.fields[<alias>].placeInOrder`
indexes into each `queryResults.queryData.rows[i].values[]`. A `null` grouping
value is the unmatched/blank bucket (verified: a `null` region row appeared
alongside the real groups). `status != "SUCCESS"` is a failure — read
`errorMessage`. `status != "SUCCESS"` with an **empty** `errorMessage` is an
unknown failure — ask the user to check the org's CDP / Reporting
configuration. A confirmed **permission** error is the provisioning-gap
signal (`orgHasDataCloudReportingEnabled` / `orgHasSemanticQuery`), not a
caller payload bug.

**Display rules.** Render rows as a markdown table for ≤20 rows, else row
count + first 10 + "… and N more". Order by `placeInOrder`. Do **NOT** echo
the raw `queryResults` JSON. Surface `errorMessage` verbatim on failure.

## Query recovery

| Signal | Cause / fix |
|---|---|
| `Failed to resolve table` | Used `__dll`/`__dlm` instead of the SDM data-object apiName |
| `Failed to resolve semantic field` | Used `semantic_field` for a raw/physical column — use `table_field` |
| `Cannot find field: <key>` | Non-proto top-level key (`limit`/`sort_orders`/`row_grouping` outside `options`) |
| `Query returns more records than allowed. The limit is: 5000` | Add `limit_options` or aggregate |
| `USER_ILLEGAL_ARGUMENT_RESOLVE_ENTITY_ERROR` | Typo / wrong table / physical column as `table_field.name` |
| `Detail Rows with Metric must have the corresponding dimension` | Missing `semantic_aggregation_method` on a measure (not a missing dimension) |
| Permission error | `orgHasDataCloudReportingEnabled` / `orgHasSemanticQuery` provisioning gap |
| `status != SUCCESS` with empty `errorMessage` | Unknown failure — check org CDP / Reporting configuration |

## Worked query (verified): sum of a measure by a joined dimension

```jsonc
{
  "semanticModelApiName": "ZZ_Trap_base0",
  "source": "tableau-next-pilot-mcp",
  "structuredSemanticQuery": {
    "fields": [
      { "expression": { "table_field": { "name": "region18", "table_name": "Accounts" } },
        "alias": "Accounts.region18", "grouping": "ROW_GROUPING" },
      { "expression": { "table_field": { "name": "Amount7", "table_name": "Opportunities" } },
        "alias": "Opportunities.Amount7",
        "semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_SUM" }
    ],
    "options": { "limit_options": { "limit": 10 },
      "sort_orders": [ { "simple_sort_order": { "sort_by_field_alias": "Opportunities.Amount7", "sorting_order": "DESC" } } ] }
  }
}
```

Returned per-region sums by traversing the Accounts↔Opportunities join.

## Detail rows (`detailed_rows: true`)

The one shape where a measure may omit `semantic_aggregation_method`. Do not
also set `grand_total`. Field names below are illustrative — copy apiNames from
`list_*`.

```jsonc
{
  "semanticModelApiName": "Sales_Performance_SDM",
  "structuredSemanticQuery": {
    "fields": [
      { "expression": { "table_field": { "name": "Account_ID", "table_name": "Account" } },
        "alias": "account_id" },
      { "expression": { "table_field": { "name": "Account_Name", "table_name": "Account" } },
        "alias": "account_name" },
      { "expression": { "table_field": { "name": "Revenue", "table_name": "Account" } },
        "alias": "revenue" }
    ],
    "options": {
      "detailed_rows": true,
      "limit_options": { "limit": 20 }
    }
  },
  "dataspace": "default"
}
```

## Filtered query (`filter.binary_predicate`)

`filter` XOR `flatten_filter` — never both. Count-distinct uses
`SEMANTIC_AGGREGATION_METHOD_UNIQUE_COUNT` (not `COUNTDISTINCT`).

```jsonc
{
  "semanticModelApiName": "Sales_Performance_SDM",
  "structuredSemanticQuery": {
    "fields": [
      {
        "expression": {
          "table_field": { "name": "Account_ID", "table_name": "Account" }
        },
        "semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_UNIQUE_COUNT",
        "alias": "distinct_accounts"
      }
    ],
    "filter": {
      "binary_predicate": {
        "left_expression": { "table_field": { "name": "Segment", "table_name": "Account" } },
        "binary_operator": "BINARY_OPERATOR_EQUALS",
        "right_expression": { "string_expression": "Enterprise" }
      }
    }
  }
}
```

## Enrichment — calculated dimension

`add_semantic_model_calculated_dimension`. TuA expression with **bracketed
qualified references** `[ObjApiName].[FieldApiName]` (suffixed apiNames). Bare
identifiers fail with "Missing reference". Verified:

```jsonc
{
  "modelApiNameOrId": "ZZ_Trap_base0",
  "apiName": "Region_Upper",
  "label": "Region Upper",
  "expression": "UPPER([Accounts].[region18])",
  "dataType": "Text",
  "displayCategory": "Discrete"
}
```

Row-level expression → server sets `level: "Row"` automatically.

- Calculated-measure TuA conditionals are **simple CASE only**:
  `CASE <expr> WHEN <value> THEN <result> ... [ELSE <result>] END`.
  Searched CASE (`CASE WHEN <condition> THEN ...`) and `IF(condition, then, else)`
  are rejected (`Syntax Error - no viable alternative at input 'WHEN'` /
  `mismatched input ','`). Key the CASE off a value, not a boolean predicate.
  Block `IF`/`ELSEIF`/`END` and `IIF(...)` are **pending live verification** —
  do not use them in a calc measure or dimension until confirmed.

## Enrichment — calculated measure

`add_semantic_model_calculated_measure`. Verified (level-aware AVG):

```jsonc
{
  "modelApiNameOrId": "ZZ_Trap_base0",
  "apiName": "Avg_Deal_Size",
  "label": "Avg Deal Size",
  "expression": "AVG([Opportunities].[Amount7])",
  "dataType": "Number",
  "aggregationType": "UserAgg",      // required when the expression aggregates
  "displayCategory": "Continuous"
}
```

- Expression that already aggregates (`AVG`, `SUM/COUNT`, `COUNTD`) → must use
  `aggregationType: "UserAgg"`; a bare `Average`/`Sum` is rejected with
  "AggregativeFunction-level calculated fields require UserAgg". Server sets
  `level: "AggregateFunction"`.
- Row-level arithmetic (`[O].[Profit] / [O].[Sales]`) → `aggregationType: "Auto"`.
- The server overlays defaults that were not passed (`decimalPlace: 2`,
  `directionality: "Up"`, `sentiment`, `totalAggregationType: "Sum"`,
  `level: "Row"`, `shouldTreatNullsAsZeros: false`) — set them explicitly to
  override.
- No arithmetic check: `/ 0` is accepted and fails only at query time.
- Do not set `externalLevel` or `externalConnectionApiName` unless connecting
  to an external definition.
- Updates are **full PUT**: GET via `get_semantic_model_calculated_measure`,
  then send the complete object. Omitted fields reset to those defaults.

To query a UserAgg calc measure, reference it as a `semantic_field` with
`SEMANTIC_AGGREGATION_METHOD_USER_AGG` (verified returning per-group averages).

## Enrichment — metric (named, time-bound KPI)

`add_semantic_model_metric`. `label` is required. **Create a metric by default
when the request implies a tracked business number** (revenue, win rate,
engagement, count over time) **and a business-meaningful event date exists to
anchor it** — not only on explicit demand. Set EXACTLY ONE shape on
`measurementReference` (and on `timeDimensionReference`). Verified shape:

```jsonc
{
  "modelApiNameOrId": "Pipeline_Analysis",
  "apiName": "Total_Pipeline",
  "label": "Total Pipeline",
  "measurementReference": { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Amount7" } },
  // OR a derived measure: "measurementReference": { "calculatedFieldApiName": "Avg_Deal_Size" }
  "timeDimensionReference": { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Created_Date14" } },
  "aggregationType": "Sum",   // matches the RAW-measure branch (sum of Amount). For the
                              // calculatedFieldApiName branch, set the calc field's own
                              // aggregation (e.g. "UserAgg" for Avg_Deal_Size) — do NOT Sum an average.
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "insightsSettings": {       // REQUIRED — omit identifyingDimension and the metric UI crashes
    "identifyingDimension": {
      "identifierDimensionReference": {
        "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Opportunity_Id5" }
      }
    }
  },
  "additionalDimensions": [   // must include identifyingDimension (and every insights/filter field)
    { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Opportunity_Id5" } }
  ]
}
```

Do not ship this block without `insightsSettings`, and always mirror
`identifyingDimension` into `additionalDimensions` (create fails with
`Insight dimension (...) is missing from the metric additional dimensions`).
Nouns, extra `additionalDimensions`, and `insightsDimensionsReferences` live in
`ingest-and-metric-gotchas.md` §B and `build-workflow.md` Step 8.

- `aggregationType` enum values: `Sum`, `Average`, `Count`, `CountDistinct`,
  `Min`, `Max`, `UserAgg`, `Auto`, etc. (note `Average`, not `Avg`).
- `fieldApiName` on BOTH references is the **suffixed** apiName **from the
  object that owns the field**. A date field from a *different* object is
  rejected with `Table field with table name: (X) and field name: (Y) was not
  found in the model` (the exact error hit when an Accounts date dim was passed
  for an Opportunities reference). Read each object's own dimensions with
  `list_semantic_model_dimensions` and match the owner.
- The time dimension must be a **business-meaningful** `Date`/`DateTime`
  dimension (`dataType: "Date"`) — a real event date (created/close/order/
  activity), NOT a `cdp_sys_PartitionDate`, `*_SourceVersion`, or load
  timestamp. A metric on a plumbing date is worse than no metric.
- With `filters`, also pass `filterLogic` (e.g. `"1"` / `"1 AND 2"`) and
  fully-qualify filter `fieldName` as `<tableApiName>.<fieldApiName>`.
- Skip the metric only if no meaningful date dimension resolves.
- Pass **ONE** of `structuredSemanticQuery` **OR** `structuredMetricQuery` on
  `run_semantic_query` — mutually exclusive. Prefer `structuredMetricQuery`
  when querying a named metric (see `build-workflow.md` Step 9). Do not
  reconstruct the metric from raw fields unless no metric exists.
