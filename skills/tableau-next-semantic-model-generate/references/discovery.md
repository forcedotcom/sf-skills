# Discovery Workflow (Deep Dive)

Full data-presence and field-name-verification protocol. Companion to the [Discovery Workflow summary in SKILL.md](../SKILL.md#discovery-workflow).

## List All SDMs

```bash
python scripts/discover_sdm.py --list
```

Returns all semantic models with labels and descriptions. Use this to identify which SDM to enrich.

## Inspect SDM Fields

```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

Returns complete SDM structure including:
- Semantic data objects (tables)
- Semantic dimensions (categorical fields)
- Semantic measurements (aggregated fields)
- Calculated fields (`_clc`)
- Semantic metrics (`_mtc`)

**What to look for:**
- Missing business logic (e.g., no win rate field but you have won/total counts)
- Field data types and aggregation types (you'll need these when creating calc fields)
- Table names (`objectName`) for dimension/measurement references
- Existing calculated fields that metrics could reference

## Before Creating Fields: Verify Data Presence

**Field-richness is not data-presence.** An object can carry dozens of fields and still return **zero rows** — a calc field or metric authored on it will be empty no matter how correct the expression is. Before authoring fields/metrics, confirm the underlying object has rows:

```bash
# Row count for the source object (the data-presence gate)
python scripts/query_data.py --count <Object__dll-or-__dlm>
```

Or call `lib.query.assert_has_rows(<Object>)`: it **hard-blocks** a confirmed 0-row object (`EmptyDataError`) and **warns — does not block** — when the count can't be obtained (advisory-strict; a transient query failure must not false-block authoring). If a source is genuinely empty, **stop and surface it, then offer the user a choice** — point them at a populated source, or hold until data lands — rather than silently authoring fields that will never return data. A DMO can also be empty because its DLO→DMO mapping hasn't materialized yet — see [empty-source-handling.md](empty-source-handling.md) for empty-of-rows vs. unmaterialized sources and the exact wording to use with the user.

## Before Creating Fields: Verify Field Names

Always verify field names exist in the SDM before referencing them in expressions.

**Field Reference Rules:**

1. **Table fields** (semanticMeasurements/semanticDimensions): MUST use qualified syntax `[TableName].[FieldName]`
2. **Calculated fields** (_clc suffix): Use unqualified syntax `[FieldName]` (they're model-level, not table-specific)

```bash
# 1. Discover SDM fields first
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json

# 2. Check available fields in the JSON output
# - semanticDataObjects[].objectName (table) and .semanticMeasurements/.semanticDimensions (table fields)
# - calculatedMeasurements/calculatedDimensions (model-level calc fields)

# 3. Use correct syntax based on field type
[Opportunity_TAB_Sales_Cloud].[Amount]   # Correct - table field (qualified)
[Total_Revenue_clc]                      # Correct - calculated field (unqualified)
[Amount]                                  # Wrong - table field must be qualified
[Opportunity_TAB_Sales_Cloud].[Total_Revenue_clc] # Wrong - calc fields are model-level, not table-specific
```

**Common errors:**
- Using unqualified names for table fields (they must be qualified)
- Using qualified names for calculated fields (they're model-level, cannot be qualified)
- Referencing field names without checking SDM output (apiName may be `Amount`, `Amount1`, etc. depending on joins)
- Referencing fields that don't exist in the SDM
