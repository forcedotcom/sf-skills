# Field Types: Measurements vs Dimensions

Understanding when to create measurements versus dimensions is fundamental to semantic layer design.

**Field Reference Syntax:**
- **Table fields**: Use qualified syntax `[TableName].[FieldName]`
- **Calculated fields** (_clc): Use unqualified syntax `[FieldName_clc]` (model-level)

## Quick Decision

**Create a measurement when:**
- The field represents a numeric value that should be aggregated (summed, averaged, counted)
- It answers "how much" or "how many"
- Examples: revenue, count, rate, percentage, days

**Create a dimension when:**
- The field represents a category, label, or grouping
- It answers "which" or "what kind"
- Examples: status, category, region, name, date component

## Measurements

Measurements are numeric fields designed for aggregation. They appear as measures in visualizations and require an aggregation type.

### Characteristics

- **Data type:** Numeric (integer, decimal)
- **Aggregation:** Required (`Sum`, `Avg`, `Min`, `Max`, `Count`, `UserAgg`)
- **Display category:** Continuous (typically)
- **Decimal places:** Configurable (0 for counts, 2 for currency)
- **Usage:** Y-axis in charts, metric values, numeric calculations

### When to Use

Use measurements for:
- **Revenue/amounts:** `Total_Revenue_clc`, `Average_Deal_Size_clc`
- **Counts:** `Opportunity_Count_clc`, `Contact_Count_clc`
- **Rates/percentages:** `Win_Rate_clc`, `Conversion_Rate_clc`
- **Time durations:** `Sales_Cycle_Days_clc`, `Time_to_Close_clc`
- **Ratios:** `Cost_to_Revenue_Ratio_clc`, `Leads_per_Account_clc`

### Aggregation Types Explained

| Type | When to Use | Example Expression |
|------|-------------|-------------------|
| `Sum` | Additive values (revenue, count) | `SUM([Table].[Amount])` |
| `Avg` | Average needed | `AVG([Table].[Close_Days])` |
| `UserAgg` | Expression already includes aggregation | `SUM([Table].[Won]) / SUM([Table].[Total])` |
| `Min` | Minimum value | `MIN([Table].[Close_Date])` (can be used for dates too) |
| `Max` | Maximum value | `MAX([Table].[Amount])` |
| `Count` | Row count | `COUNT([Table].[Opportunity_Id])` |

**Critical:** When your expression includes aggregation functions like `SUM()` or `AVG()`, always use `UserAgg` (user-defined aggregation). This tells the system "don't add another aggregation layer—the expression already handles it."

### Examples

**Total Revenue (Sum):**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB].[Amount])" \
  --aggregation Sum
```

**Win Rate (UserAgg):**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation UserAgg
```

**Average Sales Cycle (Avg):**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Avg_Sales_Cycle_clc \
  --label "Average Sales Cycle" \
  --expression "AVG(DATEDIFF('day', [Opportunity_TAB].[Created_Date], [Opportunity_TAB].[Close_Date]))" \
  --aggregation Avg
```

## Dimensions

Dimensions are categorical fields used for grouping, filtering, and breaking down data. They appear as dimensions in visualizations and don't require aggregation.

### Characteristics

- **Data type:** Text, Date, Boolean (typically)
- **Aggregation:** Not required
- **Display category:** Discrete (typically)
- **Decimal places:** Not applicable
- **Usage:** X-axis in charts, filters, color encoding, grouping

### When to Use

Use dimensions for:
- **Categories:** `Deal_Size_Category_clc`, `Lead_Source_Category_clc`
- **Status/stage:** `Opportunity_Status_clc`, `Case_Priority_clc`
- **Date components:** `Close_Month_clc`, `Close_Quarter_clc`, `Fiscal_Year_clc`
- **Derived labels:** `Account_Segment_clc`, `Customer_Tier_clc`
- **Boolean flags:** `Is_High_Value_clc`, `Is_Repeat_Customer_clc`

### Examples

**Deal Size Category:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Deal_Size_Category_clc \
  --label "Deal Size Category" \
  --expression "IF [Opportunity_TAB].[Amount] > 100000 THEN 'Large' ELSEIF [Opportunity_TAB].[Amount] > 50000 THEN 'Medium' ELSE 'Small' END"
```

**Close Month:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Close_Month_clc \
  --label "Close Month" \
  --expression "STR(DATEPART('month', [Opportunity_TAB].[Close_Date]))"
```

**High Value Flag:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Is_High_Value_clc \
  --label "Is High Value" \
  --expression "[Opportunity_TAB].[Amount] > 100000"
```

**Account Segment:**
```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Account_Segment_clc \
  --label "Account Segment" \
  --expression "CASE [Account_TAB].[Account_Type] WHEN 'Enterprise' THEN 'Strategic' WHEN 'Mid-Market' THEN 'Growth' ELSE 'Standard' END"
```

## Time-Based Fields: DATEPART and DATEDIFF

DATEPART and DATEDIFF return **numeric values**, not dates or strings.

### When to Use Dimension vs Measurement

**Use Measurement when you want to aggregate time values:**

```bash
# Average sales cycle (days)
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type measurement \
  --name Avg_Sales_Cycle_clc \
  --label "Average Sales Cycle (Days)" \
  --expression "AVG(DATEDIFF('day', [Opportunity_TAB].[Created_Date], [Opportunity_TAB].[Close_Date]))" \
  --aggregation Avg
```

**Use Dimension (with STR) when you want to group by time components:**

```bash
# Close year for grouping
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type dimension \
  --name Close_Year_clc \
  --label "Close Year" \
  --expression "STR(DATEPART('year', [Opportunity_TAB].[Close_Date]))"

# Close quarter for grouping
python scripts/create_calc_field.py \
  --sdm Sales_Model \
  --type dimension \
  --name Close_Quarter_clc \
  --label "Close Quarter" \
  --expression "'Q' + STR(DATEPART('quarter', [Opportunity_TAB].[Close_Date]))"
```

**Don't use DATEPART/DATEDIFF as dimensions without STR():**

```bash
# WRONG - This will fail (DATEPART returns number, dimension needs text)
--type dimension \
--expression "DATEPART('year', [Table].[Close_Date])"

# CORRECT - Wrap in STR() for dimension
--type dimension \
--expression "STR(DATEPART('year', [Table].[Close_Date]))"

# CORRECT - Or use as measurement if aggregating
--type measurement \
--expression "AVG(DATEPART('month', [Table].[Close_Date]))" \
--aggregation Avg
```

## Common Patterns

### Revenue Tiers (Dimension from Measurement)

Convert a numeric measurement into categorical buckets:

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Revenue_Tier_clc \
  --label "Revenue Tier" \
  --expression "IF [Total_Revenue] > 1000000 THEN 'Tier 1' ELSEIF [Total_Revenue] > 500000 THEN 'Tier 2' ELSEIF [Total_Revenue] > 100000 THEN 'Tier 3' ELSE 'Tier 4' END"
```

### Time-Based Dimensions

Extract date components for time-based grouping:

```bash
# Fiscal Quarter (assuming fiscal year starts in April)
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Fiscal_Quarter_clc \
  --label "Fiscal Quarter" \
  --expression "CASE WHEN MONTH([Opportunity_TAB].[Close_Date]) >= 4 AND MONTH([Opportunity_TAB].[Close_Date]) <= 6 THEN 'Q1' WHEN MONTH([Opportunity_TAB].[Close_Date]) >= 7 AND MONTH([Opportunity_TAB].[Close_Date]) <= 9 THEN 'Q2' WHEN MONTH([Opportunity_TAB].[Close_Date]) >= 10 AND MONTH([Opportunity_TAB].[Close_Date]) <= 12 THEN 'Q3' ELSE 'Q4' END"
```

### Boolean Flags

Create yes/no dimensions for filtering and breakdown:

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Is_Won_clc \
  --label "Is Won" \
  --expression "[Opportunity_TAB].[Stage] = 'Closed Won'"
```

### Conditional Aggregation as Measurement

When you need to sum only certain rows:

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Won_Revenue_clc \
  --label "Won Revenue" \
  --expression "SUM(IF [Opportunity_TAB].[Stage] = 'Closed Won' THEN [Opportunity_TAB].[Amount] ELSE 0 END)" \
  --aggregation Sum
```

## Decision Tree

```
What does the expression return?
├─ Numeric (numbers, DATEDIFF, DATEPART, calculations)
│  ├─ Should be aggregated (sum, avg, count)? → Measurement
│  │  └─ Does expression include aggregation functions (SUM/AVG)?
│  │     ├─ Yes → aggregation: UserAgg
│  │     └─ No → aggregation: Sum/Avg/Min/Max/Count
│  └─ Should be categorical (for grouping)? → Dimension with STR()
│     └─ Wrap expression: STR(DATEPART(...)) or STR(DATEDIFF(...))
└─ Text/Boolean (strings, CASE statements, boolean comparisons)
   └─ Dimension (no STR() needed)
```

## Common Mistakes

### Using Dimension When Measurement is Needed

**Wrong:**
```bash
# This creates a dimension but contains numeric aggregation
--type dimension \
--expression "SUM([Amount])"
```

**Right:**
```bash
# Numeric aggregation requires measurement type
--type measurement \
--expression "SUM([Amount])" \
--aggregation Sum
```

### Using Wrong Aggregation Type

**Wrong:**
```bash
# Expression already has SUM(), but aggregation is set to Sum
--type measurement \
--expression "SUM([Won]) / SUM([Total])" \
--aggregation Sum  # WRONG - adds another aggregation layer
```

**Right:**
```bash
# Expression has aggregation, use UserAgg
--type measurement \
--expression "SUM([Won]) / SUM([Total])" \
--aggregation UserAgg  # Correct - respects user's aggregation
```

### Creating Dimension for Numeric Calculation

**Wrong:**
```bash
# Win rate is numeric and should be aggregated
--type dimension \
--expression "SUM([Won]) / SUM([Total])"
```

**Right:**
```bash
# Win rate is a measurement
--type measurement \
--expression "SUM([Won]) / SUM([Total])" \
--aggregation UserAgg
```

## Testing Your Field

After creating a field, test it in a visualization to verify behavior:

**For measurements:**
- Should appear in measure shelf
- Should aggregate correctly in charts
- Should support color encoding by gradient

**For dimensions:**
- Should appear in dimension shelf
- Should create discrete groups in charts
- Should support color encoding by category

Create a test visualization in Tableau Next referencing your new fields to confirm behavior end-to-end.
