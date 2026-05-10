# BDT Reference — Overview (always loaded)

> **Last synced:** 2026-04-23 from canonical BDT Connect API Java sources
> (`cdp-connect-api` module, `sfdc.cdp.connect.api.{input,enums}.datatransform` packages,
> release 264). Cross-verified identical across releases 260, 262, and 264. See
> `research/bdt-schema-canonical.md` for the full machine-extracted schema.

## What a BDT is

**Batch Data Transform (BDT)** — a repeatable, scheduled or on-demand data pipeline inside
Salesforce Data Cloud. It reads from one or more source objects, applies a DAG of
transformations (joins, filters, formulas, aggregations, etc.), and writes one or more
outputs. BDTs run over batches; their streaming counterpart is **SDT** (Streaming Data
Transform).

- Salesforce object type: `MktDataTransform`.
- Typical export: a JSON file from the BDT viewer, or via Workbench
  `/ssot/data-transforms?htmlEncode=false`.
- Underlying runtime: the Data Processing Engine (DPE) / DCSQL.

## Top-level JSON shape

A BDT JSON can arrive in **three** shapes. The skill's parser accepts all three
transparently (since commit `ee2485c`); the inner node graph is identical in every case.

### 1. Editor export (the default "download" shape)

What you get when you export a BDT from the BDT editor UI, or fetch it via
`/ssot/data-transforms?htmlEncode=false` on Workbench. The outer object is the
**definition** itself, with no wrapper metadata:

```jsonc
{
  "version": "66.0",               // Schema version string
  "nodes": { /* NodeName → Node */ },
  "ui": {                          // Optional: layout hints + human-readable labels
    "nodes":      { /* NodeName → { label, description, type, top, left } */ },
    "connectors": [ /* { source, target } edges */ ],
    "hiddenColumns": []
  }
}
```

**Note:** editor exports have no top-level `type` field. The definition-type
discriminator (`"STL"`) only appears when the definition is nested inside a Connect
API payload (see below).

### 2. Connect API create payload — single definition

What developers POST to the `MktDataTransform` Connect API when authoring
programmatically. The outer object is a `DataTransformInputRepresentation`; the
editor-export shape is nested inside under `definition`:

```jsonc
{
  "name": "MyTransform",           // Required — API name of the transform
  "label": "My Transform",         // Required — user-visible label
  "description": "…",              // Optional
  "type": "BATCH",                 // DataTransformType: "BATCH" | "STREAMING"
  "dataSpaceName": "default",      // Data space the transform lives in
  "definition": {
    "version": "66.0",
    "type": "STL",                 // DataTransformDefinitionType: "STL" | "SQL" | "DCSQL" | …
    "nodes": { /* … */ },
    "ui":    { /* … */ }
  }
}
```

Two distinct `type` fields live at different nesting levels:
- Outer `type` = `DataTransformType` (batch vs streaming).
- Inner `definition.type` = `DataTransformDefinitionType` (STL for batch BDTs; SQL /
  DCSQL for raw-SQL transforms; hidden variants exist but are not surfaced to users).

### 3. Connect API create payload — multi-definition variant

For transforms with multiple definitions. Same outer fields; instead of a single
`definition` object there's a `definitions` array:

```jsonc
{
  "name": "…", "label": "…", "type": "BATCH", "dataSpaceName": "default",
  "definitions": [
    { "version": "66.0", "type": "STL", "nodes": { /* … */ }, "ui": { /* … */ } },
    /* … additional definitions … */
  ]
}
```

v1 of this skill reads the first definition and explains only that one; multi-definition
explanations are out of scope.

### Each node (inner shape, identical in all three outer shapes)

```jsonc
{
  "action": "<action-type>",         // One of the 25 documented action strings below
  "sources": ["NODE_A", "NODE_B"],   // Array of node names (empty for load/roots)
  "parameters": { /* action-specific */ },
  "schema": { /* optional — slice/rename at node boundary */ }
}
```

## The 25 canonical action types

| `action` string | Purpose (one line) |
|---|---|
| `load` | Read rows from a DMO or DLO |
| `filter` | Keep rows matching structured filter criteria |
| `sqlFilter` | Keep rows matching a raw SQL predicate |
| `join` | Join two upstream streams by key |
| `formula` | Add derived columns via per-row SQL formulas |
| `computeRelative` | Window function over partitioned / ordered rows |
| `aggregate` | Group-by aggregation |
| `extractGrains` | Fan out rows across time grains |
| `extractTable` | Extract a table from a flatten-JSON output |
| `schema` | Rename / drop / reshape columns |
| `outputD360` | Write rows to a target DMO or DLO |
| `appendV2` | Union rows from multiple upstream streams (v2 variant) |
| `flatten` | Flatten nested structure |
| `flattenJson` | Flatten a JSON field into rows/columns |
| `split` | Split rows into multiple downstream branches |
| `typeCast` | Cast field types |
| `update` | Update records |
| `bucket` | Assign bucket labels to field values |
| `formatDate` | Reformat date values |
| `extension` | Run a custom extension node |
| `extensionFunction` | Run a custom extension function |
| `cdpPredict` | Apply a prediction model |
| `jsonAggregate` | Aggregate JSON fields |
| `save` | Save an intermediate result |
| `recommendation` | Apply a recommendation model |

**For full parameter shapes, enums, and examples: see `references/bdt-node-catalog.md`.**
**For SFSQL functions used in `formula` expressions: see `references/bdt-function-catalog.md`.**
**For window functions used in `computeRelative`: see `references/bdt-window-functions.md`.**

## Terminology

- **DMO** — Data Model Object. Canonical modeled entity. Suffix convention: `__dlm`.
- **DLO** — Data Lake Object. Raw-lake table. Suffix convention: `__dll`.
- **SFSQL** — Salesforce's internal SQL dialect used in formula expressions and SQL filters.
- **DCSQL** — a related SQL dialect used for Spark push-down execution (you may see it as
  an `expressionType` value).
- **`ssot__` prefix** — Salesforce Standard Schema field, canonical / semantic.
- **`__c` suffix** — Custom field.
- **`KQ_` prefix** — Key-qualifier pattern (external ID / composite-key helper). Observed in
  practice; not always documented.
- **UI label vs. JSON action name** — The JSON uses concise strings (e.g., `computeRelative`);
  the BDT editor shows friendlier labels (e.g., "Window Transform"). The `ui.nodes[X].label`
  field in the JSON carries the user-specified human-readable name per node. **Always use
  the UI label in explanations when present.**

## Key enums (for quick orientation)

- **`DataTransformType`**: `BATCH`, `STREAMING`
- **`JoinType`**: `INNER`, `OUTER`, `LEFT_OUTER`, `RIGHT_OUTER`, `LOOKUP`, `MULTI_VALUE_LOOKUP`, `CROSS`
- **`WriteModeEnum`** (outputD360): `APPEND`, `MERGE`, `OVERWRITE`, `MERGE_UPSERT_DELETE`, `DELETE_ONLY`
- **`D360OutputTypeEnum`**: `dataLakeObject`, `dataModelObject`
- **`SliceMode`**: `SELECT`, `DROP`
- **`AggregateType`**: `UNIQUE`, `SUM`, `AVG`, `COUNT`, `MAX`, `MIN`, `MEDIAN`, `STDDEVP`, `STDDEV`, `VARP`, `VAR`
- **`DataType`**: `TEXT`, `NUMBER`, `DATE_ONLY`, `DATETIME`, `BOOLEAN`
- **`SortDirection`**: `ASC`, `DESC`

For exhaustive enum lists with semantics: `bdt-node-catalog.md` or (for the raw extraction)
`research/bdt-schema-canonical.md`.

## How this skill uses these references

- `bdt-reference.md` (this file) — always in context.
- `bdt-node-catalog.md` — consulted before explaining any node type not previously covered
  in the current conversation.
- `bdt-function-catalog.md` — consulted before interpreting any `formulaExpression` (job I1)
  or reasoning about conditional logic (I2).
- `bdt-window-functions.md` — consulted whenever a `computeRelative` node is narrated.

**If a node type or function isn't in any of the reference files**, the skill narrates what's
visible in the JSON and explicitly flags the item as undocumented in the materials available.
It does not guess at semantics.
