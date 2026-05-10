# Window Functions — for `computeRelative` nodes

> **Last synced:** 2026-04-23 from the SFSQL window-functions reference and the BDT
> canonical schema. Consult this file whenever narrating a `computeRelative` node or
> explaining a window-function expression.

## When this applies

`computeRelative` nodes evaluate a **window function** over rows. The `parameters`:

```jsonc
{
  "partitionBy": ["ssot__AccountId__c"],              // → SQL `PARTITION BY`
  "orderBy": [                                         // → SQL `ORDER BY`
    {"fieldName": "ssot__CreatedDate__c", "direction": "ASC"}
  ],
  "expressionType": "SQL",                             // or "DCSQL"
  "fields": [
    {
      "name": "OrderRank__c",
      "formulaExpression": "row_number()",             // the window function call
      "type": "NUMBER", "businessType": "Number",
      "precision": 18, "scale": 0
    }
  ]
}
```

The `formulaExpression` names the window function; partitioning and ordering come from the
top-level `partitionBy` and `orderBy`. **A computeRelative node may include at most one
compute-relative function per expression** (per upstream BDT docs).

## Available window functions

| Function | Returns | What it does |
|---|---|---|
| `row_number()` | NUMBER | 1, 2, 3… for each row in its partition, in the given order. Non-deterministic when sort keys tie. |
| `rank()` | NUMBER | Like `row_number` but peers share a rank; next rank after N peers is N+1 (gaps). |
| `dense_rank()` | NUMBER | Like `rank` but no gaps — consecutive integers even with ties. |
| `percent_rank()` | NUMBER | `(rank - 1) / (partition_rows - 1)` — relative rank within partition, 0 to 1. |
| `cume_dist()` | NUMBER | Cumulative distribution: fraction of partition rows at or before current. |
| `ntile(n)` | NUMBER | Bucket number 1..n, dividing partition rows as evenly as possible. |
| `lag(value)` / `lag(value, offset)` / `lag(value, offset, default)` | same as value | Value at offset rows *before* current (default offset=1; default if no such row is NULL unless a default is supplied). |
| `lead(value)` / `lead(value, offset)` / `lead(value, offset, default)` | same as value | Symmetric with `lag` but looks forward. |
| `first_value(value)` | same as value | Value at the first row of the current window frame. |
| `last_value(value)` | same as value | Value at the last row of the frame. Default frame ends at "current + peers", which is often *not* what users want. |
| `nth_value(value, n)` | same as value | Value at the nth row of the frame (counting from 1). NULL if no such row. |
| Any aggregate with `OVER(...)` | depends | Runs the aggregate over the window (running sum, etc.). |

## How this maps to BDT JSON

- `partitionBy` is the SQL `PARTITION BY` — the columns that group rows into windows.
- `orderBy` is the SQL `ORDER BY` — the ordering within each partition.
- **Peers** are rows with identical sort keys.
- Default **frame** (when not otherwise specified): rows from the first row of the partition
  through the current row's last peer. For `last_value` and `nth_value` this is often not
  the user's intent — narrate accordingly.

## Common narration patterns

- **`row_number()` partitioned by X** → "numbers each row within the same X, in the order
  given by `orderBy`."
- **`rank() partitioned by X order by Y`** → "ranks rows within each X group by Y; ties
  share a rank and the next rank has gaps."
- **`case when row_number()=1 then VAL else 0 end`** → "keeps VAL only on the first ranked
  row per partition; everything else is 0. This is the canonical 'first-occurrence extract'
  idiom."

## Sources

- SFSQL window-functions reference (internal Data Cloud / SDB SFSQL docs).
- BDT canonical schema: `ComputeRelativeParametersInputRepresentation`,
  `ComputeRelativeSortParametersInputRepresentation`.
