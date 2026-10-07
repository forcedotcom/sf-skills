# Task: Query an existing model

Pull figures from an already-built SDM via `run_semantic_query`: a plain count,
total, or scalar ("how many / how much / what is total…"), a "give / run me the
numbers" retrieval, or a structured table. The model does **not** have to be
named up front — discover it with `list_semantic_models` when it isn't given.
Prefer this over `analyze_data` whenever the user wants the figures themselves
rather than an interpreted breakdown, ranking, trend, or comparison.

Raw SQL against a DLO/DMO (`run_query`) also enters here when no SDM covers
the data or the user asked for SQL — still prefer `run_semantic_query` when
an SDM exists.

Interpreted breakdowns, rankings, trends, and comparisons go to
`analyze-data.md` / `analyze_data`. Scoring candidate SQL against expected
SQL is `review-verified-questions.md` (`run_regression_evaluator`) — it
does not query data.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1, G2, G3** · Conditional: **G4** (◐, if querying across objects),
**G6** (◐, if you don't yet understand what the returned numbers mean)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G2:** the target object has rows (a query over an empty object returns empty).
- **G3:** reference fields by their exact stored apiName — read back via `list_*`
  if unsure; never invent a suffixed name.
- **G4** (◐): only query across objects that are actually joined; do not set
  `queryUnrelatedDataObjects:"Exception"` and query across unjoined objects.
- **G6** (◐): if the additivity/grain of the returned numbers isn't understood,
  profile first (`../data-understanding.md`).

## Steps

If the user did not name an SDM, call `list_semantic_models` and pick the
matching populated model before querying.

The proto-shaped `run_semantic_query` body, field-shape matrix, recovery strings,
aggregation enum, detail-row, and `filter` XOR `flatten_filter` payloads are in
**`../semantic-query-and-enrichment.md`**.

- **Prefer `run_semantic_query` when an SDM exists** for the data. Fall back
  to `run_query` (Data Cloud / Hyper SQL against a DLO `__dll` or DMO `__dlm`)
  when the user asks for raw SQL, no SDM covers the tables, or you are
  checking ingest materialization (`ingest-and-metric-gotchas.md` §A).
  Discover SQL table names from `list_semantic_model_data_objects`
  `dataObjectName` when an SDM is in play — that value already includes the
  suffix and is ground truth. Otherwise use the suffixed DLO/DMO developer
  name (`__dll` DLO, `__dlm` DMO). A bare DMO name (no `__dlm`) fails with
  `42P01` / "table does not exist". Double-quote reserved words and names
  with spaces.
  `run_query` is Hyper SQL (full SELECT / WHERE / GROUP BY / JOIN /
  aggregates / windows). That is a **different** engine from the SparkInternal
  DCSQL subset on `create_data_transform` / `update_data_transform` — do not
  copy those unsupported-op restrictions onto `run_query`, or vice versa.
  `run_query` returns the **first chunk only** — if `returnedRows` looks short
  or `status.completionStatus` is not `Finished`, say so and narrow with WHERE
  / a lower `rowLimit`. Pagination tools (`query_data_status`, `query_data_rows`)
  are not available. Response `data` is an array of **row arrays** (values in
  `metadata` order), not row objects — join column names/types from the
  separate `metadata` array.
  Bind user input with `:name` placeholders and `sqlParameters` (the `name`
  field is `"p1"` for `:p1`, no colon). `name` and `value` are required on every
  parameter; `value` is always a serialized **string**. `type` defaults to
  Varchar — set Integer / BigInt / Double / Boolean / Date / DateTime for
  non-string columns (`type` tells the server how to interpret the string).
  `dataspace` is optional; omitting it targets **default**. In a
  multi-dataspace org that is easy to get wrong — pass the dataspace that
  actually holds the `__dll` / `__dlm` (same name used on create/mapping)
  rather than assuming default.

- Pass **ONE** of `structuredSemanticQuery` (recommended) **OR**
  `structuredMetricQuery` — mutually exclusive. Prefer an existing metric
  (`structuredMetricQuery`) / calc measure over reconstructing a `SUM(...)`
  aggregation inline.
- Write the semantic-query body in **snake_case proto** shape (`table_field`,
  `grouping`, `semantic_aggregation_method`) — REST-gateway camelCase examples
  fail here.
- Group by the correct date grain (e.g. month), not by a raw timestamp.
- Query is org-level / SDM-level — it does **NOT** take a `workspaceId`. Any SDM
  visible via `list_semantic_models` is queryable regardless of workspace.
- Provisioning is gated on `orgHasDataCloudReportingEnabled` /
  `orgHasSemanticQuery`. A permission error is a **provisioning gap**, not a
  caller payload bug.
- **Display:** render rows as a markdown table for ≤20 rows, else row count +
  first 10 + "… and N more". Order by `placeInOrder`. Do **NOT** echo the raw
  `queryResults` JSON. Surface `errorMessage` verbatim on failure.

This is a read/query entry point — it does not model, enrich, or visualize. If the
answer needs a chart, continue to `create-viz.md` (which re-asserts G7 before
charting).
