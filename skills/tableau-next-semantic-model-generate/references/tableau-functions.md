# Tableau Functions Reference

Supported Tableau functions for use in calculated field expressions. Functions are case-insensitive (`SUM` and `sum` both work).

**Field Reference Syntax:**
- **Table fields** (from semanticMeasurements/semanticDimensions): Use qualified syntax `[TableName].[FieldName]`
- **Calculated fields** (_clc suffix): Use unqualified syntax `[FieldName_clc]` (they're model-level)

## Aggregation Functions

| Function | Description | Example |
|----------|-------------|---------|
| `SUM(expression)` | Sum of all values | `SUM([Table].[Amount])` |
| `AVG(expression)` | Average of all values | `AVG([Table].[Close_Days])` |
| `MIN(expression)` | Minimum value | `MIN([Table].[Close_Date])` |
| `MAX(expression)` | Maximum value | `MAX([Table].[Amount])` |
| `COUNT(expression)` | Count of non-null values | `COUNT([Table].[Opportunity_Id])` |
| `COUNTD(expression)` | Count of distinct values | `COUNTD([Table].[Account_Id])` |
| `MEDIAN(expression)` | Median value | `MEDIAN([Table].[Amount])` |
| `STDEV(expression)` | Standard deviation | `STDEV([Table].[Amount])` |
| `VAR(expression)` | Variance | `VAR([Table].[Amount])` |

**Note:** When your expression already includes aggregation functions (e.g., `SUM([Table].[Won]) / SUM([Table].[Total])`), use `aggregationType: UserAgg` when creating the field.

## Date Functions

| Function | Description | Example |
|----------|-------------|---------|
| `DATEPART(part, date)` | Extract part of date | `DATEPART('month', [Table].[Close_Date])` |
| `DATEDIFF(part, start, end)` | Difference between dates | `DATEDIFF('day', [Table].[Created_Date], [Table].[Close_Date])` |
| `DATEADD(part, increment, date)` | Add to date | `DATEADD('month', 3, [Table].[Close_Date])` |
| `NOW()` | Current date and time | `NOW()` |
| `TODAY()` | Current date | `TODAY()` |
| `YEAR(date)` | Year component | `YEAR([Close_Date])` |
| `MONTH(date)` | Month component | `MONTH([Close_Date])` |
| `DAY(date)` | Day component | `DAY([Close_Date])` |
| `QUARTER(date)` | Quarter component | `QUARTER([Close_Date])` |
| `WEEK(date)` | Week component | `WEEK([Close_Date])` |

**Date parts:** `'year'`, `'quarter'`, `'month'`, `'week'`, `'day'`, `'hour'`, `'minute'`, `'second'`

**Important:** DATEPART and DATEDIFF return **numbers**, not dates or strings. When using them in calculated dimensions (for grouping/filtering), wrap the result in STR() to convert to text: `STR(DATEPART('year', [Table].[Date]))`. When using them in measurements (for aggregation), use without STR() and specify appropriate aggregation type.

## String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `STR(expression)` | Convert to string (required for dimensions using DATEPART/DATEDIFF) | `STR(DATEPART('year', [Table].[Close_Date]))` |
| `LEFT(string, num)` | First N characters | `LEFT([Name], 5)` |
| `RIGHT(string, num)` | Last N characters | `RIGHT([Name], 3)` |
| `MID(string, start, length)` | Substring | `MID([Name], 2, 5)` |
| `UPPER(string)` | Uppercase | `UPPER([Name])` |
| `LOWER(string)` | Lowercase | `LOWER([Name])` |
| `TRIM(string)` | Remove whitespace | `TRIM([Name])` |
| `CONTAINS(string, substring)` | Check if contains | `CONTAINS([Name], 'Corp')` |
| `STARTSWITH(string, substring)` | Check if starts with | `STARTSWITH([Name], 'Acme')` |
| `ENDSWITH(string, substring)` | Check if ends with | `ENDSWITH([Name], 'Inc')` |
| `REPLACE(string, pattern, replacement)` | Replace text | `REPLACE([Name], 'Corp', 'Corporation')` |
| `SPLIT(string, delimiter, token)` | Split and extract | `SPLIT([Email], '@', 1)` |
| `LEN(string)` | String length | `LEN([Name])` |

## Logical Functions

| Function | Description | Example |
|----------|-------------|---------|
| `IF condition THEN value1 ELSE value2 END` | Conditional | `IF [Amount] > 100000 THEN 'Large' ELSE 'Small' END` |
| `IF condition THEN value1 ELSEIF condition2 THEN value2 ELSE value3 END` | Multi-condition | `IF [Amount] > 100000 THEN 'Large' ELSEIF [Amount] > 50000 THEN 'Medium' ELSE 'Small' END` |
| `CASE expression WHEN value1 THEN result1 WHEN value2 THEN result2 ELSE default END` | Case statement | `CASE [Stage] WHEN 'Closed Won' THEN 1 ELSE 0 END` |
| `IFNULL(expression, alt_value)` | Replace null | `IFNULL([Amount], 0)` |
| `ISNULL(expression)` | Check if null | `ISNULL([Amount])` |
| `ZN(expression)` | Zero if null | `ZN([Amount])` |
| `AND` | Logical AND | `[Amount] > 100000 AND [Stage] = 'Closed Won'` |
| `OR` | Logical OR | `[Stage] = 'Closed Won' OR [Stage] = 'Closed Lost'` |
| `NOT` | Logical NOT | `NOT [Stage] = 'Closed Lost'` |

## Math Functions

| Function | Description | Example |
|----------|-------------|---------|
| `ABS(number)` | Absolute value | `ABS([Amount])` |
| `ROUND(number, decimals)` | Round to decimals | `ROUND([Amount], 2)` |
| `CEILING(number)` | Round up | `CEILING([Amount])` |
| `FLOOR(number)` | Round down | `FLOOR([Amount])` |
| `POWER(number, power)` | Exponentiation | `POWER([Amount], 2)` |
| `SQRT(number)` | Square root | `SQRT([Amount])` |
| `EXP(number)` | e raised to power | `EXP([Rate])` |
| `LOG(number)` | Natural log | `LOG([Amount])` |
| `LOG10(number)` | Base-10 log | `LOG10([Amount])` |

## Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal | `[Stage] = 'Closed Won'` |
| `!=` or `<>` | Not equal | `[Stage] != 'Closed Lost'` |
| `>` | Greater than | `[Amount] > 100000` |
| `>=` | Greater or equal | `[Amount] >= 100000` |
| `<` | Less than | `[Amount] < 50000` |
| `<=` | Less or equal | `[Amount] <= 50000` |

## Arithmetic Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `+` | Addition | `[Amount] + [Tax]` |
| `-` | Subtraction | `[Revenue] - [Cost]` |
| `*` | Multiplication | `[Amount] * [Probability]` |
| `/` | Division | `[Won_Count] / [Total_Count]` |
| `%` | Modulo | `[Amount] % 100` |

## Common Patterns

### LOD (Level of Detail) Expressions

LOD expressions allow you to compute aggregations at specific dimension levels, independent of other dimensions in the view.

**FIXED Syntax:**
```tableau
{ FIXED [Dimension] : Aggregation([Measure]) }
```

**Examples:**

**Quota per fiscal quarter:**
```tableau
{ FIXED [Fiscal_Quarter] : SUM([Quota]) }
```

**Percent of total:**
```tableau
SUM([Sales]) / { FIXED : SUM([Sales]) }
```

**Average per category:**
```tableau
{ FIXED [Category] : AVG([Amount]) }
```

**Common use cases:**
- Quota allocation across time periods
- Percent of total calculations
- Comparing values at different granularities
- Removing dimension influence from calculations

### Win Rate
```tableau
SUM([Won_Count]) / SUM([Total_Count])
```

### Conversion Rate
```tableau
SUM([Converted_Count]) / SUM([Total_Count])
```

### Weighted Pipeline
```tableau
SUM([Amount] * [Probability])
```

### Sales Cycle (days)
```tableau
AVG(DATEDIFF('day', [Created_Date], [Close_Date]))
```

### Deal Size Category
```tableau
IF [Amount] > 100000 THEN 'Large'
ELSEIF [Amount] > 50000 THEN 'Medium'
ELSE 'Small'
END
```

### Null-Safe Division
```tableau
IF SUM([Total_Count]) = 0 THEN 0
ELSE SUM([Won_Count]) / SUM([Total_Count])
END
```

### Conditional Aggregation
```tableau
SUM(IF [Stage] = 'Closed Won' THEN [Amount] ELSE 0 END)
```

### Year-over-Year Growth
```tableau
(SUM([Current_Year_Amount]) - SUM([Previous_Year_Amount])) / SUM([Previous_Year_Amount])
```

## Function Not Supported?

Common functions that look similar but don't exist in Tableau:

| Incorrect | Correct Alternative |
|-----------|---------------------|
| `SUMIF(condition, field)` | `SUM(IF condition THEN field ELSE 0 END)` |
| `AVERAGEIF(condition, field)` | `AVG(IF condition THEN field ELSE NULL END)` |
| `CONCAT(str1, str2)` | `str1 + str2` |
| `SUBSTRING(string, start, length)` | `MID(string, start, length)` |

If you get an "Invalid function" error, check the spelling and compare against this reference. Function names are case-insensitive but must be spelled exactly as shown.
