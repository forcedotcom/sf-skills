# Core Concepts (Deep Dive)

Extended definitions and the create-and-verify contract. Companion to the [Core Concepts summary in SKILL.md](../SKILL.md#core-concepts).

## Base Fields vs Calculated Fields

**Base field** (`data-objects/{obj}/measurements|dimensions`) binds an existing source column (`dataObjectFieldName`) to one object — use it when building model structure (e.g. a clean-named join key); **calculated field** (`_clc`, `calculated-measurements|dimensions`) is a model-level formula (`expression`) — use it when you must *compute* a value (ratio, conditional, LOD) that no column holds.

## Calculated Fields vs Metrics

**Calculated Fields (`_clc`):**
- Rich structure: aggregation type, data type, decimal places, expression
- Used directly in visualizations (charts, tables)
- Can be measurements (aggregated) or dimensions (categorical)
- Example: `Win_Rate_clc` with expression `SUM([Table].[Won]) / SUM([Table].[Total])`

**Semantic Metrics (`_mtc`):**
- Lightweight wrappers for dashboard metric widgets
- Reference a calculated field via `measurementReference.calculatedFieldApiName`
- Include time dimension (`timeDimensionReference`) and time grains (Day, Week, Month, Quarter, Year)
- Support additional dimensions for breakdown analysis
- Example: `Win_Rate_mtc` references `Win_Rate_clc` with `Close_Date` as time dimension

**When to use each:**
- Create calc field when you need a reusable formula for visualizations
- Create metric when you need a time-based KPI for Tableau Next dashboard widgets
- Always create the calc field first, then the metric (two-step workflow)

## Creation is verified by querying

`create_calc_field.py` and `create_metric.py` run a small semantic query against the new field/metric after the create call succeeds, and only report **done** when it returns non-empty data. A created-but-empty field/metric is reported **NOT shippable** (non-zero exit) — do not proceed to dashboards; investigate the source/expression (see [empty-source-handling.md](empty-source-handling.md)). If the verify query can't run, creation is reported as **unconfirmed** rather than done. Pass `--skip-verify` only when you have a deliberate reason to skip the check.

## A created metric/field is not "ready" until it returns data

**Creation success is not data success.** A metric or calc field that the API accepted can still return **zero rows** (empty source, filter excludes everything, expression resolves to nothing) — and a dashboard built on it shows "No results to show." So "did the create succeed?" and "is it ready to use?" are different questions. To answer *ready*, **query it**:

- At create time, `create_metric.py` and `create_calc_field.py` run this verify automatically — a small semantic query against the new field/metric. They report **done only when it returns non-empty data**; an empty result is reported **NOT shippable** (non-zero exit) and you should not proceed to dashboards. (Don't pass `--skip-verify` unless you have a deliberate reason — it disables exactly this check.)
- If asked whether an **already-created** metric/field is ready, **do not** just inspect its structure with `discover_sdm.py` — that only proves it *exists*, not that it returns data. **Query it for data** with `--verify-only`, which runs just the verify (no create) against the existing field/metric:

  ```bash
  python scripts/create_metric.py --sdm <SDM> --name <Metric_mtc> --verify-only
  python scripts/create_calc_field.py --sdm <SDM> --type measurement --name <Field_clc> --verify-only
  ```

  It exits non-zero and prints **NOT shippable** when the metric/field returns no data. Do **not** re-run a full `create_metric.py` on an existing metric — a second create fails with a unique-constraint violation (`--verify-only` is the re-check path). If the verify comes back empty, say it is **NOT shippable** and investigate the source/expression (see [empty-source-handling.md](empty-source-handling.md)). There is no `query_data.py --metric`; `query_data.py` is for raw object row-counts (`--count`), and metric/field data is confirmed via the verify step above.
