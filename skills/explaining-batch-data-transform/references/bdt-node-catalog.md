# BDT Node Catalog — per-action reference (on-demand)

> **Source of truth:** `research/bdt-schema-canonical.md`, extracted from the BDT Connect
> API Java sources (`cdp-connect-api` module, release 264) on 2026-04-23. The entries
> below are curated to answer the skill's job — explaining BDT JSON. For the full
> extraction (all fields, minVersion annotations, polymorphism map), see the research doc.

Consult this file before explaining any node type. Each section covers:
- **JSON action name** and UI name(s).
- **Purpose** in plain English.
- **Key parameters** with types (and enum values where applicable).
- **How it affects lineage** — rename? add? drop? change row cardinality?
- **Common gotchas**.
- **Example JSON snippet**.
- **Source citation** back to the canonical Java input-rep class.

---

## `action: "load"` — UI: "Load" / "Data Source"

**Purpose.** Reads rows from a DMO or DLO into the pipeline. Every BDT has at least one
load node (they are the graph roots — `sources: []`).

**Key parameters** (class `LoadParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `dataset` | `LoadDatasetInputRepresentation` | `{ name: string, type: "dataModelObject" \| "dataLakeObject" }` |
| `fields` | `string[]` | Field names to pull from the source. Not pulling a field means it's unavailable downstream. |
| `sampleDetails` | `{ type: "TopN" \| "Custom" \| "Unique", sortBy: string[] }` | Editor-only sampling behavior; doesn't affect runtime. |

**Lineage effect.** Defines the *initial* set of field names available downstream. No row
cardinality change (all rows are loaded).

**Gotchas.**
- A field referenced by a downstream node must appear in some load's `fields` array, **or**
  be generated later by a formula/aggregate. If you can't trace a field to a load or a
  derivation, the BDT is broken.
- `dataset.type` was historically called `dataLakeObject` in some older dialects; per
  canonical schema both `dataModelObject` and `dataLakeObject` are valid.
- `sampleDetails.sortBy` is a list of strings — may be empty.

**Example.**
```jsonc
{
  "action": "load",
  "sources": [],
  "parameters": {
    "dataset": {"name": "ssot__SalesOrder__dlm", "type": "dataModelObject"},
    "fields": ["ssot__Id__c", "ssot__AccountId__c", "ssot__GrandTotalAmount__c"],
    "sampleDetails": {"type": "TopN", "sortBy": []}
  }
}
```

**Source.** `LoadNodeInputRepresentation` + `LoadParametersInputRepresentation` +
`LoadDatasetInputRepresentation`.

---

## `action: "join"` — UI: "Join"

**Purpose.** Joins two upstream streams by key. Always has exactly two `sources`; field names
on the right-hand side get a qualifier prefix so they don't collide with left-hand names.

**Key parameters** (class `JoinParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `joinType` | enum `JoinType`: `INNER`, `OUTER`, `LEFT_OUTER`, `RIGHT_OUTER`, `LOOKUP`, `MULTI_VALUE_LOOKUP`, `CROSS` | |
| `leftKeys` | `string[]` | Join keys on the left (first) source. |
| `rightKeys` | `string[]` | Join keys on the right (second) source. |
| `leftQualifier` | `string` (optional) | Prefix for left-side field names in the output. Often omitted. |
| `rightQualifier` | `string` (required) | Prefix for right-side fields (e.g., `SalesOrder` → right-side field `ssot__Id__c` becomes `SalesOrder.ssot__Id__c`). |

**Optional node-level** `schema.slice`:
- `{ mode: "DROP" | "SELECT", fields: string[], ignoreMissingFields: bool }`
- Used to trim unwanted fields from the joined output.

**Lineage effect.** Combines two field sets. Fields from the right side get renamed with
`rightQualifier` prefix. Row cardinality depends on join type:
- `INNER` — only matched pairs.
- `LEFT_OUTER` — all left rows + matching right.
- `RIGHT_OUTER` — all right rows + matching left.
- `OUTER` — all rows from both sides.
- `LOOKUP` — 1:1 left-side preserving.
- `MULTI_VALUE_LOOKUP` — left-side preserving; multi-valued right.
- `CROSS` — Cartesian product; every left paired with every right.

**Gotchas.**
- Data types of joined keys should match. Type mismatches cause silent no-match or errors
  depending on pair.
- `rightQualifier` is the *only* way to disambiguate same-named fields from two sources.
  Always surface it when narrating.
- `schema.slice` on a join is a post-join projection, not a pre-join filter.

**Example.**
```jsonc
{
  "action": "join",
  "sources": ["JOIN7", "FILTER4"],
  "parameters": {
    "joinType": "LEFT_OUTER",
    "leftKeys": ["ssot__Id__c"],
    "rightQualifier": "SalesOrder",
    "rightKeys": ["ssot__SalesOrderId__c"]
  },
  "schema": {
    "slice": {
      "mode": "DROP",
      "ignoreMissingFields": true,
      "fields": ["SalesOrder.ssot__InternalOrganizationId__c"]
    }
  }
}
```

**Source.** `JoinNodeInputRepresentation` + `JoinParametersInputRepresentation`.

---

## `action: "filter"` — UI: "Filter"

**Purpose.** Keep only rows satisfying filter criteria combined by boolean logic.

**Key parameters** (class `FilterParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `filterExpressions` | `FilterExpression[]` | Each expression is `{ field, operator, type, operands[] }`. |
| `filterBooleanLogic` | `string` | A formula like `"1 AND (2 OR 3)"` indexed 1..N into `filterExpressions`. If omitted, default is all AND. |

**FilterExpression fields** (class `FilterExpressionInputRepresentation`):
- `field` — the field the filter examines.
- `operator` — `string` (no typed enum in the canonical input-rep; free-form in the API).
  Commonly observed values: `EQUAL`, `NOT_EQUAL`, `GREATER_THAN`, `LESS_THAN`,
  `GREATER_OR_EQUAL`, `LESS_OR_EQUAL`, `IN_RANGE`, `LIKE`, `IS_NULL`, `IS_NOT_NULL`.
- `type` — enum `DataType` (same as elsewhere in BDT): `TEXT`, `NUMBER`, `BOOLEAN`,
  `DATE_ONLY`, `DATETIME`.
- `operands` — array of operand values (strings in JSON; interpreted per `type`).

**Lineage effect.** Does not change field names; only reduces rows.

**Gotchas.**
- `filterBooleanLogic` operands are **1-indexed** into `filterExpressions`. Be careful when
  narrating which expression is "expression 1".
- If a referenced field is dropped upstream, the filter becomes invalid at runtime.

**Example.**
```jsonc
{
  "action": "filter",
  "sources": ["LOAD_DATASET0"],
  "parameters": {
    "filterExpressions": [
      {"type": "TEXT", "field": "MobilePhone_Formatted_Flag__c", "operator": "EQUAL", "operands": ["Y"]},
      {"type": "TEXT", "field": "IsActive__c", "operator": "EQUAL", "operands": ["true"]}
    ],
    "filterBooleanLogic": "1 AND 2"
  }
}
```

**Source.** `FilterNodeInputRepresentation` + `FilterParametersInputRepresentation` +
`FilterExpressionInputRepresentation`.

---

## `action: "sqlFilter"` — UI: "SQL Filter"

**Purpose.** A filter whose predicate is a raw SQL expression — more expressive than the
structured `filter` node, at the cost of being harder to validate statically.

**Key parameters** (class `SqlFilterParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `sqlFilterExpression` | `string` | A SQL WHERE-clause-like predicate referring to fields by name. |

**Lineage effect.** Same as `filter` — reduces rows only.

**Example.**
```jsonc
{
  "action": "sqlFilter",
  "sources": ["JOIN1"],
  "parameters": {
    "sqlFilterExpression": "ssot__CreatedDate__c >= current_date() - interval '30' day"
  }
}
```

**Source.** `SqlFilterNodeInputRepresentation` + `SqlFilterParametersInputRepresentation`.

---

## `action: "formula"` — UI: "Formula"

**Purpose.** Add one or more derived columns via per-row SQL formulas. No window / cross-row
semantics — for that, see `computeRelative`.

**Key parameters** (class `FormulaParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `expressionType` | enum `FormulaExpressionType`: `SQL`, `DCSQL` | |
| `fields` | `SqlFormulaFieldInputRepresentation[]` | One entry per derived field. |

**Each field** carries:
- `name` — the output field name.
- `label` — user-visible label.
- `formulaExpression` — SFSQL (or DCSQL) expression. See `bdt-function-catalog.md`.
- `type` — enum `DataType`: `TEXT`, `NUMBER`, `BOOLEAN`, `DATE_ONLY`, `DATETIME`.
- **`businessType`** — a user-facing business-semantic type name. Enum `BusinessTypeEnum` —
  **canonical values** (complete list; matches `BusinessTypeEnum.java` as of the capture date
  at the top of this file):
  - `"TEXT"`, `"NUMBER"`, `"BOOLEAN"`
  - `"EMAIL"`, `"PHONE"`, `"URL"` — text-valued with semantic meaning
  - `"PERCENT"`, `"CURRENCY"` — number-valued with semantic meaning
  - `"DATE"` — semantically a date, stored as datetime at the underlying `type` level
  - `"DATE_ONLY"` — date-only value (no time component)
  - `"DATETIME"` — full datetime

  Note: `businessType` values map to underlying `type` (`DataType`) values. E.g.,
  `businessType: "PERCENT"` is stored as `type: "NUMBER"`; `businessType: "DATE"` is stored
  as `type: "DATETIME"`; `businessType: "EMAIL"` is stored as `type: "TEXT"`. If the skill
  ever encounters a `businessType` value outside this list, that is a sign the upstream BDT
  schema has evolved — surface the raw value in narration and flag it as undocumented.
- `precision` — integer precision (default 10 for numbers; characters for text).
- `scale` — decimal places; only for NUMBER.
- `defaultValue` — value when the expression yields NULL.

**Lineage effect.** Adds new columns to the downstream row stream. Original columns pass
through unchanged unless dropped later by a `schema` node. Row cardinality unchanged.

**Gotchas.**
- If a field referenced in `formulaExpression` is removed upstream, the formula fails at
  runtime.
- **`type` and `businessType`** — both use UPPER wire form per canonical enums
  (`type: "NUMBER"`, `businessType: "NUMBER"`). Some user-authored BDT JSON
  may show capitalized forms (`"Number"`) — the runtime is case-insensitive
  per `BusinessTypeEnum.valueOfInternal()`, but the canonical wire form is
  UPPER.
- Concrete sub-classes exist for typed fields (`SqlFormulaNumericFieldInputRepresentation`,
  etc.) but the JSON shape is the same.

**Example.**
```jsonc
{
  "action": "formula",
  "sources": ["JOIN5"],
  "parameters": {
    "expressionType": "SQL",
    "fields": [
      {
        "name": "ssot__SalesOrderProductConcat__c",
        "label": "SalesOrderProductConcat",
        "formulaExpression": "concat(coalesce(\"SalesOrder.ssot__Id__c\",'NULL'),coalesce(\"SalesOrder.ssot__Id__c\",''))",
        "type": "TEXT",
        "businessType": "TEXT",
        "precision": 60,
        "defaultValue": ""
      }
    ]
  }
}
```

**Source.** `FormulaNodeInputRepresentation` + `FormulaParametersInputRepresentation` +
`SqlFormulaFieldInputRepresentation`.

---

## `action: "computeRelative"` — UI: "Window Transform"

**Purpose.** A formula that evaluates a **window function** over partitioned, ordered rows.
Used for ranking, lead/lag, running totals, etc.

**Key parameters** (class `ComputeRelativeParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `partitionBy` | `string[]` | Column(s) to partition rows by. Empty = whole stream. |
| `orderBy` | `ComputeRelativeSortParametersInputRepresentation[]` | Each `{ fieldName, direction: "ASC" \| "DESC" }`. |
| `expressionType` | enum `FormulaExpressionType`: `SQL`, `DCSQL` | |
| `fields` | `SqlFormulaFieldInputRepresentation[]` | Same shape as `formula` fields. |

**Lineage effect.** Adds one or more columns. Original columns pass through. Row cardinality
unchanged.

**Gotchas.**
- The documentation states "A formula can include only one Compute Relative function" — if
  you see multiple compute-relative calls in one expression, flag as unusual.
- If `partitionBy` is empty, the function runs over the whole stream (one big window).
- `orderBy` is required for order-dependent functions (`row_number`, `rank`, `lag`, etc.).
  Without it, results are non-deterministic.

**Example.**
```jsonc
{
  "action": "computeRelative",
  "sources": ["LOAD_ORDERS"],
  "parameters": {
    "partitionBy": ["ssot__AccountId__c"],
    "orderBy": [{"fieldName": "ssot__CreatedDate__c", "direction": "ASC"}],
    "expressionType": "SQL",
    "fields": [
      {
        "name": "OrderRank__c",
        "label": "Order Rank",
        "formulaExpression": "row_number()",
        "type": "NUMBER",
        "businessType": "NUMBER",
        "precision": 18,
        "scale": 0,
        "defaultValue": ""
      }
    ]
  }
}
```

**Source.** `ComputeRelativeNodeInputRepresentation` +
`ComputeRelativeParametersInputRepresentation` +
`ComputeRelativeSortParametersInputRepresentation`. For the function catalog, see
`bdt-window-functions.md`.

---

## `action: "aggregate"` — UI: "Aggregate" / "Group and Aggregate"

**Purpose.** Group-by aggregation. Also supports a hierarchical mode for parent/child aggregation.

**Key parameters** (class `AggregateParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `groupings` | `string[]` | Group-by field names. **Not** `groupBy`. |
| `aggregations` | `AggregateInputRepresentation[]` | Each `{ action: AggregateType, name, source, label? }`. |
| `nodeType` | enum `AggregateNodeEnum`: `STANDARD`, `HIERARCHICAL` | |
| `selfField`, `parentField`, `percentageField` | `string` (hierarchical-only) | |
| `pivot_v2` | `PivotV2InputRepresentation` (optional) | Advanced; pivot in the same node. |

**Aggregation functions** (enum `AggregateType`):
`UNIQUE`, `SUM`, `AVG`, `COUNT`, `MAX`, `MIN`, `MEDIAN`, `STDDEVP`, `STDDEV`, `VARP`, `VAR`.

**Lineage effect.**
- Output columns = `groupings` (pass-through) + each `aggregation.name` (new derived column).
- Row cardinality: one output row per unique combination of `groupings`.

**Gotchas.**
- Group-by column is called `groupings` not `groupBy` in the JSON.
- `aggregation.source` is the field being aggregated; `aggregation.name` is the output column name.
- In `HIERARCHICAL` mode, the three `*Field` parameters carry parent-child semantics; the
  aggregations roll up across the hierarchy.

**Example.**
```jsonc
{
  "action": "aggregate",
  "sources": ["FILTER0"],
  "parameters": {
    "groupings": ["ssot__AccountId__c"],
    "aggregations": [
      {"action": "SUM", "name": "TotalAmount__c", "source": "ssot__GrandTotalAmount__c"},
      {"action": "COUNT", "name": "OrderCount__c", "source": "ssot__Id__c"}
    ],
    "nodeType": "STANDARD"
  }
}
```

**Source.** `AggregateNodeInputRepresentation` + `AggregateParametersInputRepresentation` +
`AggregateInputRepresentation`.

---

## `action: "schema"` — UI: "Edit Attributes" / "Drop Fields"

**Purpose.** Modify column-level schema: rename columns, change properties, or slice the set
of columns.

**Key parameters** (class `SchemaParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `fields` | `SchemaFieldParametersInputRepresentation[]` | Per-field: `{ name, newProperties: { name?, label? } }`. |
| `slice` | `SchemaSliceInputRepresentation` (optional) | `{ mode: "DROP" \| "SELECT", fields: string[], ignoreMissingFields: bool }`. |

**Slice semantics.**
- `mode: DROP` — remove the listed fields from the output.
- `mode: SELECT` — keep only the listed fields.
- `ignoreMissingFields: true` means listed fields that aren't present are silently ignored.
  Without this flag, missing fields would error.

**Lineage effect.** Schema-only: renames or drops columns. Row cardinality unchanged.

**Gotchas.**
- `ignoreMissingFields: true` plus a typo = silent failure. When explaining a schema node
  that uses it, flag the risk ("these field names are silently skipped if missing").
- `fields[].newProperties.name` is where a rename lands; the original `name` is the key.

**Example (drop).**
```jsonc
{
  "action": "schema",
  "sources": ["FORMULA43"],
  "parameters": {
    "slice": {
      "mode": "DROP",
      "ignoreMissingFields": true,
      "fields": ["ssot__SalesOrderProductConcat__c", "FirstPurchase__c"]
    }
  }
}
```

**Example (rename).**
```jsonc
{
  "action": "schema",
  "sources": ["AGGREGATE0"],
  "parameters": {
    "fields": [
      {"name": "sum_amount", "newProperties": {"name": "TotalAmount__c", "label": "Total Amount"}}
    ]
  }
}
```

**Source.** `SchemaNodeInputRepresentation` + `SchemaParametersInputRepresentation` +
`SchemaFieldParametersInputRepresentation` + `SchemaSliceInputRepresentation`.

---

## `action: "outputD360"` — UI: "Output" / "Writeback"

**Purpose.** Writes the row stream to a target DMO or DLO. Every BDT has at least one
outputD360 node — these are the graph sinks.

**Key parameters** (class `OutputD360ParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `name` | `string` | Target object's API name (e.g., `Account_Upper__dlm`). |
| `type` | enum `D360OutputTypeEnum`: `dataModelObject`, `dataLakeObject` | |
| `writeMode` | enum `WriteModeEnum`: `APPEND`, `MERGE`, `OVERWRITE`, `MERGE_UPSERT_DELETE`, `DELETE_ONLY` | Write semantics. |
| `fieldsMappings` | `OutputD360FieldsMappingInputRepresentation[]` | Each `{ sourceField, targetField }` pair. |
| `dedupOrder` | `SortSpecificationRepresentation[]` | Tiebreaker for deduplicating records with the same primary key. |
| `streaming` | `StreamingParametersInputRepresentation` (optional) | Streaming-specific; not relevant for BDT. |

**Write modes.**
- `APPEND` — add rows; no primary-key checks.
- `OVERWRITE` — replace the target with the dataset.
- `MERGE` — merge on PK: update matching rows (only for columns present in the input), insert
  new rows.
- `MERGE_UPSERT_DELETE` — merge with per-row UPSERT/DELETE markers.
- `DELETE_ONLY` — delete matching rows.

The underlying DaaS library supports more modes (`OVERWRITE_PARTITIONS`,
`OVERWRITE_PARTITION_FILTER`, `SECONDARY_INDEX_INCREMENTAL_WRITE`), but the BDT Connect API
exposes only the five above.

**Lineage effect.** Terminal node. Maps source-stream fields to target-object fields; any
unmapped source field is discarded.

**Gotchas.**
- `OUTPUT0 nodes must have DataModelObject type` is a known restriction in some frameworks
  (data-kit templates). If a BDT has `type: dataLakeObject` and is failing to install in a
  template context, that may be the cause.
- If multiple input rows have the same primary key, `dedupOrder` decides which wins.
- Fields not listed in `fieldsMappings` are not written.

**Example.**
```jsonc
{
  "action": "outputD360",
  "sources": ["DROP_FIELDS0"],
  "parameters": {
    "name": "Kohler_Internal_Users__dlm",
    "type": "dataModelObject",
    "writeMode": "MERGE",
    "fieldsMappings": [
      {"sourceField": "Formatted_MobilePhone__c", "targetField": "Formatted_MobilePhone__c"},
      {"sourceField": "Kohler_Internal_User_Flag", "targetField": "Kohler_Internal_User_Flag__c"}
    ]
  }
}
```

**Source.** `OutputD360NodeInputRepresentation` + `OutputD360ParametersInputRepresentation` +
`OutputD360FieldsMappingInputRepresentation`.

---

## `action: "appendV2"` — UI: "Append"

**Purpose.** Union rows from two or more upstream streams into one output.

**Key parameters** (class `AppendParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `columnMappings` | `Map<string, string>` | Map of source-stream-node-name → column mapping. |
| `fieldMappings` | `AppendMappingInputRepresentation[]` | Explicit per-field mappings. |
| `allowImplicitDisjointSchema` | `boolean` | When true, sources with different fields are merged; missing fields become NULL. |

**Lineage effect.**
- Rows: union of input streams.
- Columns: the merged schema (union if `allowImplicitDisjointSchema`; otherwise intersection).

**Gotchas.**
- Source nodes must have the same column count *and* matching column names (in order), unless
  `allowImplicitDisjointSchema: true`.
- Append can accept up to 200 fields total from its sources (per help docs).

**Example.**
```jsonc
{
  "action": "appendV2",
  "sources": ["LOAD_A", "LOAD_B"],
  "parameters": {
    "fieldMappings": [
      {"targetField": "Id__c", "sources": [{"node": "LOAD_A", "field": "ssot__Id__c"},
                                            {"node": "LOAD_B", "field": "ssot__Id__c"}]}
    ]
  }
}
```

**Source.** `AppendV2NodeInputRepresentation` + `AppendParametersInputRepresentation` +
`AppendMappingInputRepresentation`.

---

## `action: "split"` — UI: "Split"

**Purpose.** Split the value of one source string field into multiple target columns based on a delimiter. One row in, one row out — each row's `sourceField` is split into the named `targetFields`.

**Key parameters** (class `SplitParametersInputRepresentation`):

| Param | Type | Notes |
|---|---|---|
| `sourceField` | `string` | Name of the field whose value will be split. |
| `delimiter` | `string` | Delimiter used to split the source value. |
| `targetFields` | `{name, label}[]` | One entry per column the split produces. Order matches the left-to-right order of the split parts. |

**Lineage effect.**
- Rows: unchanged. Row cardinality is preserved — split does not route rows into branches.
- Columns: adds each `targetFields[i].name` as a new column. The original `sourceField` passes through unchanged.

**Gotchas.**
- `split` is string-splitting, not row-routing. If you need to route rows into multiple branches based on predicates, use `filter` nodes downstream of a common source, not `split`.
- If a row's `sourceField` has fewer delimited parts than the `targetFields` length, the remaining target columns are populated with NULL (no error).
- If a row's `sourceField` has more delimited parts than `targetFields` length, the extra parts are discarded.

**Example.**
```jsonc
{
  "action": "split",
  "sources": ["LOAD_RAW"],
  "parameters": {
    "sourceField": "FullName__c",
    "delimiter": " ",
    "targetFields": [
      {"name": "FirstName__c", "label": "First Name"},
      {"name": "LastName__c",  "label": "Last Name"}
    ]
  }
}
```

**Source.** `SplitNodeInputRepresentation` + `SplitParametersInputRepresentation` + `NameLabelInputRepresentation`.

---

## `action: "flatten"` / `"flattenJson"` — UI: "Flatten" / "Flatten JSON"

**Purpose.**
- `flatten` — flatten a nested (array-valued or structured) field into additional rows.
- `flattenJson` — flatten a JSON string field by parsing it and emitting its fields as
  columns (or extracting array elements as rows via a subsequent `extractTable`).

**Key parameters** (`FlattenParametersInputRepresentation`,
`FlattenJsonParametersInputRepresentation`):

- `fields` — list of `FlattenFieldInputRepresentation { name, attributePath?, label? }`.
- For JSON, a schema description may be embedded.

**Lineage effect.** May increase rows (array-explode) or add columns (object-flatten).

**Source.** `FlattenNodeInputRepresentation`, `FlattenJsonNodeInputRepresentation`.

---

## `action: "extractGrains"` — UI: "Extract Grains"

**Purpose.** Expand rows across time grains — e.g., a date column + list of grains produces
one row per source row per grain.

**Key parameters** (class `ExtractGrainParametersInputRepresentation`):

- `grainExtractions` — each `{ source, targets: [{ name, label, grainType }] }`.
- `dateConfigurationName` — which date configuration (fiscal calendar, etc.) to use.

**Valid `grainType` values** (enum `DateGrain`):
`YEAR, QUARTER, MONTH, WEEK, DAY, HOUR, MINUTE, SECOND, DAY_EPOCH, SEC_EPOCH, FISCAL_YEAR,
FISCAL_QUARTER, FISCAL_MONTH, FISCAL_WEEK`.

**Lineage effect.** Usually adds one column per grain type; may or may not multiply rows
depending on configuration.

**Source.** `ExtractGrainNodeInputRepresentation` + `ExtractGrainParametersInputRepresentation`.

---

## `action: "extractTable"` — UI: "Extract Table"

**Purpose.** Pairs with `flattenJson`: extract a named table (from a JSON array) as a
separate output stream.

**Key parameters.** See `ExtractTableParametersInputRepresentation`.

**Source.** `ExtractTableNodeInputRepresentation`.

---

## `action: "typeCast"` — UI: "Type Cast"

**Purpose.** Cast one or more fields to new types.

**Key parameters.** See `TypecastParametersInputRepresentation`,
`SchemaTypePropertiesCastInputRepresentation`.

**Lineage effect.** Schema-only; row cardinality unchanged.

---

## `action: "bucket"` — UI: "Bucket Date/Dimension/Measure"

**Purpose.** Assign bucket labels to values of a source field, per a bucket setup.

**Key parameters** (class `BucketParametersInputRepresentation`):

- `fields` — list of `BucketFieldInputRepresentation`, polymorphic on the field type:
  - Boolean: `BucketBooleanFieldInputRepresentation`
  - DateOnly: `BucketDateOnlyFieldInputRepresentation`
  - DateTime: `BucketDateTimeFieldInputRepresentation`
  - Dimension: `BucketDimensionFieldInputRepresentation`
  - Measure: `BucketMeasureFieldInputRepresentation`

Each sub-class includes a `setup` object describing the buckets (ranges, algorithms, labels).

**Algorithm type** (enum `BucketAlgorithmType`): `TYPOGRAPHIC_CLUSTERING` (and potentially
others — verify against sample if needed).

**Lineage effect.** Adds a derived bucket-label column. Row cardinality unchanged.

---

## `action: "formatDate"` — UI: "Format Dates"

**Purpose.** Reformat date fields — e.g., parse a custom string format into a date type,
or produce a formatted text representation.

**Key parameters.** See `FormatDateParametersInputRepresentation`,
`FormatDatePatternInputRepresentation`.

---

## `action: "update"` — UI: "Update"

**Purpose.** Update records in place in the pipeline (used in specific update workflows).

**Key parameters.** See `UpdateParametersInputRepresentation`.

---

## `action: "extension"` / `"extensionFunction"` — UI: custom extensions

**Purpose.** Run a custom extension node / function registered with Data Cloud.

**Key parameters.** See `ExtensionParametersInputRepresentation`,
`ExtensionFunctionParametersInputRepresentation`,
`ExtensionFunctionOutputFieldInputRepresentation`.

**Gotcha.** Extensions are user-defined; explanation must rely on parameter content since
the semantics are defined outside the BDT spec.

---

## `action: "cdpPredict"` — UI: "Predict"

**Purpose.** Apply a prediction model (CDP Predict / Einstein).

**Key parameters.** See `CdpPredictNodeInputRepresentation` +
`CdpPredictParametersInputRepresentation` + `PredictionFieldInputRepresentation` +
`PredictSourceInputRepresentation`.

---

## `action: "jsonAggregate"` — UI: "JSON Aggregate"

**Purpose.** Aggregate JSON-valued fields into structured output.

**Key parameters.** See the `JsonAggregateEnum` enum and the relevant input representations
(currently sparsely documented — inspect raw parameters when encountered).

---

## `action: "save"` — UI: "Save"

**Purpose.** Save an intermediate result to a checkpoint (not a final output). Less common.

---

## `action: "recommendation"` — UI: "Recommendation"

**Purpose.** Apply a recommendation model (product recommendations).

**Key parameters.** See `PredictionContributorInputRepresentation`.

---

## Common `schema.slice` block (can appear on most node types)

Many nodes accept an optional top-level `schema.slice` block to trim fields at the node
boundary. Its shape is always the same:

```jsonc
"schema": {
  "slice": {
    "mode": "DROP" | "SELECT",
    "fields": ["Field1", "Field2"],
    "ignoreMissingFields": true
  }
}
```

- `DROP` — remove the listed fields.
- `SELECT` — keep only the listed fields.
- `ignoreMissingFields: true` — silent skip when a listed field doesn't exist.

---

## Polymorphism map (for JSON parsers)

Several input reps are polymorphic; the discriminator is a JSON property:

- `AbstractBucketAlgorithmInputRepresentation` discriminated by `"type"`:
  - `"TYPOGRAPHIC_CLUSTERING"` → `TypographicClusterInputRepresentation`.

Other polymorphic classes (e.g., `SqlFormulaFieldInputRepresentation` → numeric / text /
boolean / date variants) are resolved at deserialization based on `type`. When narrating,
the field-level JSON usually carries the concrete fields directly — no special handling
needed.

## Source citations

Every section above traces back to one or more classes in the BDT Connect API
`cdp-connect-api` module, packages `sfdc.cdp.connect.api.{input,enums}.datatransform`.
See `research/bdt-schema-canonical.md` for the full machine-extracted schema plus
version-drift verification across releases 260, 262, and 264.
