# Calculated Field Patterns

Aggregation types + common expression patterns for creating `_clc` measurements and dimensions. Companion to the create-a-calc-field workflow in [SKILL.md](../SKILL.md#calculated-fields).

## Aggregation Types

When creating measurements, choose the correct aggregation type based on how the field should behave in visualizations:

| Aggregation | Use When | Example |
|-------------|----------|---------|
| `Sum` | Additive values (revenue, count) | `SUM([Table].[Amount])` |
| `Avg` | Average needed (rates, percentages when raw values available) | `AVG([Table].[Close_Days])` |
| `UserAgg` | Expression already includes aggregation | `SUM([Table].[Won]) / SUM([Table].[Total])` |
| `Min` | Minimum value | `MIN([Table].[Close_Date])` |
| `Max` | Maximum value | `MAX([Table].[Amount])` |
| `Count` | Row count | `COUNT([Table].[Opportunity_Id])` |

**Critical:** Don't guess aggregation types. If uncertain, inspect the SDM first to see how similar fields are configured, or use `UserAgg` when your expression already includes aggregation functions.

## Common Expression Patterns

**Time calculations:**
```tableau
DATEDIFF('day', [Table].[Created_Date], [Table].[Close_Date])
```

**Conditional aggregation:**
```tableau
SUM(IF [Table].[Stage] = 'Closed Won' THEN [Table].[Amount] ELSE 0 END)
```

**String manipulation:**
```tableau
UPPER([Table].[Account_Name])
LEFT([Table].[Opportunity_Name], 10)
```

**Null handling:**
```tableau
IFNULL([Table].[Amount], 0)
```

See [tableau-functions.md](tableau-functions.md) for complete function reference and [patterns.md](patterns.md) for production-derived ratio / LOD / dimension patterns.
