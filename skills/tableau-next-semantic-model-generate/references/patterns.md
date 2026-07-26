# Real-World Patterns

Patterns learned from analyzing 25+ production dashboard packages. Use these as guidance when designing your own fields and metrics.

**See also:** [kpi-formulas.md](kpi-formulas.md) for time-based aggregation patterns (snapshot sums, annualization, DATEDIFF) and 40+ composite KPI formulas from finance/banking domains.

## Metric Design Patterns

**Additional Dimensions:**
- Sales metrics typically include 4–5 breakdown dimensions: Account_Name, Opportunity_Type, Account_Industry, Account_Type, Full_Name
- Choose dimensions that enable meaningful "Top contributors" and "Top detractors" insights
- Avoid using too many dimensions (5+ can dilute insights)

**Time Dimension Selection:**
- Pipeline/forecast metrics → Use `Created_Date` (when opportunity entered pipeline)
- Revenue/closed metrics → Use `Close_Date` (when deal closed)
- Process metrics → Use event date (when action occurred)

**Insights Settings (common pattern):**
```json
{
  "insightTypes": [
    {"enabled": false, "type": "TopContributors"},
    {"enabled": false, "type": "ComparisonToExpectedRangeAlert"},
    {"enabled": true, "type": "TrendChangeAlert"},
    {"enabled": true, "type": "BottomContributors"},
    {"enabled": true, "type": "ConcentratedContributionAlert"},
    {"enabled": true, "type": "TopDrivers"},
    {"enabled": true, "type": "TopDetractors"},
    {"enabled": true, "type": "CurrentTrend"}
  ]
}
```

TopContributors and ComparisonToExpectedRangeAlert are often disabled; trend-based insights are enabled.

**Plural/Singular Nouns:**
Often left empty (`""`) in production packages, but can improve readability when specified (e.g., `"calls"`, `"opportunities"`).

## Calculated Field Patterns

**Ratios → UserAgg:**
```tableau
SUM([Table].[Won_Count]) / SUM([Table].[Total_Count])
```
Always use `aggregationType: UserAgg` when expression includes aggregation functions.

**Conditional Aggregation → UserAgg:**
```tableau
SUM(IF [Table].[Stage] = 'Closed Won' THEN [Table].[Amount] ELSE 0 END)
```
Or referencing a calculated field (unqualified):
```tableau
SUM(IF NOT [Is_Open_Opportunity_clc] THEN [OpportunityLineItem_TAB_Sales_Cloud].[Product_Quantity]*[OpportunityLineItem_TAB_Sales_Cloud].[List_Price_Amount] END)
```

**Referencing Other Calc Fields:**
```tableau
SUM([Total_Sales_clc])/[Total_Closed_Opportunities_Amount_clc]
```
Valid to reference other calculated fields in expressions. Calculated fields are model-level and use unqualified syntax `[FieldName_clc]`. Table fields require qualified syntax `[Table].[Field]`.

**Weighted Calculations:**
```tableau
SUM(FLOAT([Probability_clc] * [Table].[Quantity]*[Table].[Price]))
```
Use FLOAT() for probability-weighted values.

**LOD (Level of Detail) Expressions:**
```tableau
{ FIXED [Table].[Fiscal_Quarter] : SUM([Table].[Quota_USD]) }
```
FIXED expressions compute aggregations at specific dimension levels, independent of other dimensions in the view. Common uses:
- Quota allocation across time periods
- Percent of total calculations
- Running totals or cumulative metrics
- Comparing values across different granularities

LOD syntax: `{ FIXED [Table].[dimension] : aggregation_function([Table].[measure]) }`

## Dimension Patterns

**Tiering by Thresholds:**
```tableau
IF [Table].[CSAT] >= 60 THEN "Tier 1"
ELSEIF [Table].[CSAT] <= 20 THEN "Tier 3 - Escalated"
ELSE "Tier 2"
END
```

**Mapping with CASE:**
```tableau
CASE [Table].[Call_Reason]
  WHEN "Benefits Inquiry" THEN "General Platform Issues"
  WHEN "Billing Question" THEN "Regulatory Document Upload Issues"
  ELSE [Table].[Call_Reason]
END
```

**Boolean Flags:**
```tableau
If [Table].[Type]="Self" then "Site User" else "Participant" end
```

**Referencing Calculated Fields in Dimensions:**
```tableau
IF [Is_Open_Opportunity_clc] THEN 'Open' ELSEIF [Is_Won_Opportunity_clc] THEN 'Won' ELSE 'Lost' END
```
Calculated fields use unqualified syntax. Table fields require `[TableName].[FieldName]`:
```tableau
[HLS_Call_Center_Dataverse].[Member_CSAT]
```

## Industry-Specific Patterns

**Sales:**
- Win_Rate_clc, Conversion_Rate_clc, Pipeline_Generation_clc
- Weighted_Pipeline_Value_clc (probability * amount)
- Sales_Cycle_Won_clc (time between Created_Date and Close_Date)
- Quota_Per_Fiscal_Quarter_clc (FIXED LOD for quota allocation)

**Service:**
- Average_Time_To_Close_clc (UserAgg)
- CSAT_clc, Volume_clc (UserAgg)
- Reopen_Rate_clc (ratio)

**HR:**
- Headcount_clc, Turnover_Rate_clc
- Employee tiering by age ranges or seniority

**Healthcare:**
- Call volume, wait times
- Tiering by CSAT or priority
- Channel mapping (Portal, Call, Email, etc.)

## See also

- **[kpi-formulas.md](kpi-formulas.md)** — Time-based aggregation patterns (snapshot sums, annualization, DATEDIFF), composite KPI formulas, and color semantics. 40+ production dashboard templates across Finance, Banking, Sales, HR domains. Covers lifecycle tracking (new/lost counts via LOD) and period-constrained calculations.
