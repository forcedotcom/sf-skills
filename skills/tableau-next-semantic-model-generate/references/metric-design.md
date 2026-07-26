# Metric Design Patterns

Semantic metrics (`_mtc`) are lightweight wrappers for Tableau Next dashboard KPI widgets. The semantic layer lives in Data 360. This guide covers common patterns and design decisions.

## Metric Anatomy

Every metric has:
1. **measurementReference** — references a calculated field (`_clc`)
2. **timeDimensionReference** — field + table for time-based analysis
3. **timeGrains** — granularities (Day, Week, Month, Quarter, Year)
4. **additionalDimensions** — optional breakdown dimensions
5. **insightsSettings** — auto-generated when additional dimensions exist

## Basic Patterns

### Simple Metric (No Breakdowns)

Use when you need a single KPI without dimensional breakdown.

**Example: Total Revenue**

```bash
# Step 1: Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Amount])" \
  --aggregation Sum

# Step 2: Create metric
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**When to use:** Dashboard metric widgets showing a single trend over time.

### Metric with Single Breakdown Dimension

Use when you want to analyze the metric by one categorical dimension (e.g., "Revenue by Region").

**Example: Revenue by Region**

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Revenue_by_Region_mtc \
  --label "Revenue by Region" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --additional-dimension "Region:Opportunity_TAB_Sales_Cloud"
```

**When to use:** 
- Breakdown insights with "Top contributors" or "Top detractors"
- Dashboard widgets with dimension filters
- Analysis of metric performance across categories

### Metric with Multiple Breakdown Dimensions

Use when you want to analyze the metric across several dimensions simultaneously.

**Example: Revenue by Region and Industry**

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Revenue_Multi_Dim_mtc \
  --label "Revenue by Region and Industry" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --additional-dimension "Region:Opportunity_TAB_Sales_Cloud" \
  --additional-dimension "Account_Industry:Account_TAB_Sales_Cloud"
```

**When to use:**
- Complex metrics with multiple dimension breakdowns
- Flexible analysis where users choose which dimension to focus on
- Comprehensive insights across organizational hierarchy

**Note:** The system automatically generates `insightsSettings` with `insightsDimensionsReferences` matching the `additionalDimensions`.

## The `additionalDimensions` Superset Rule

**Every field referenced by `identifyingDimension`, `insightsDimensionsReferences[]`, or `filters[].fieldName` MUST also appear in the metric's top-level `additionalDimensions[]`.** The builder enforces this pre-POST and the `--identifying-dimension` / `--filter` flags auto-mirror their fields into `additionalDimensions`, so following the documented usage keeps you compliant. There are two distinct server failure modes if the rule is broken:

1. **Insight / identifying dimensions** missing from `additionalDimensions` fail at **create** time:

   > `Validation Failed: ... Insight dimension (<Table>.<Field>) is missing from the metric additional dimensions.`

2. **Filter fields** missing from `additionalDimensions` *succeed* at create but make the metric **unqueryable**:

   > `Metric Definition Filter Field <Field> is not found in Metric Definition.`

The skill raises a clear pre-POST `ValueError` quoting these strings rather than letting the metric reach the server in a broken state.

### Metric Filters

Use `--filter` to scope a metric to a subset of rows (e.g. revenue for the West region only). Rules enforced by the skill:

- **Field must be fully qualified** as `Table.Field` — a bare field name is rejected (it would trigger the "is not found in Metric Definition" error above).
- **`filterLogic` is auto-generated**: `"1"` for one filter, `"1 AND 2"` for two, etc. (1-based, in filter order). It is required by the server alongside a non-empty `filters[]`.
- **Filter fields are auto-mirrored into `additionalDimensions`** so the metric stays queryable.
- **Operators** (verified live against a v66.0 org, 2026-06-23): `=` (Equals), `>` (GreaterThan), `<` (LessThan), `In`, `NotIn`, `Contains`, `NotContains`, `Between`, `StartsWith`. The server uses CamelCase enum values and **rejects** SQL-style `EQUAL`/`NOT_EQUAL`/`GREATER_THAN_OR_EQUAL`; there is **no** `>=`, `<=`, or `!=` operator.

**Example: West-region revenue**

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name West_Revenue_mtc \
  --label "West Region Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --filter "Opportunity_TAB_Sales_Cloud.Region = West"
```

**When to use:** Pre-scoped KPIs (a segment-specific metric) where the filter is part of the metric's definition rather than a dashboard-level filter.

## Advanced Patterns

### Ratio Metrics (Win Rate, Conversion Rate)

Metrics representing rates or percentages always use `UserAgg` aggregation.

**Example: Win Rate**

```bash
# Step 1: Create win rate calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation UserAgg

# Step 2: Create metric
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_mtc \
  --label "Win Rate" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**When to use:** Any percentage, rate, or ratio metric (conversion rate, churn rate, success rate).

### Weighted Metrics

Metrics where values are weighted by another field (e.g., weighted pipeline by probability).

**Example: Weighted Pipeline Value**

```bash
# Step 1: Create weighted pipeline field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Weighted_Pipeline_clc \
  --label "Weighted Pipeline Value" \
  --expression "SUM([Amount] * [Probability])" \
  --aggregation Sum

# Step 2: Create metric
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Weighted_Pipeline_mtc \
  --label "Weighted Pipeline Value" \
  --calculated-field Weighted_Pipeline_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**When to use:** Risk-adjusted revenue, weighted scores, probabilistic forecasting.

### Time-Based Metrics (Sales Cycle, Days to Close)

Metrics representing time durations or date differences.

**Example: Average Sales Cycle**

```bash
# Step 1: Create sales cycle field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Avg_Sales_Cycle_clc \
  --label "Average Sales Cycle (Days)" \
  --expression "AVG(DATEDIFF('day', [Created_Date], [Close_Date]))" \
  --aggregation Avg

# Step 2: Create metric
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Avg_Sales_Cycle_mtc \
  --label "Average Sales Cycle" \
  --calculated-field Avg_Sales_Cycle_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**When to use:** Process duration metrics (time to close, time to resolution, cycle time).

### Cumulative Metrics

Metrics that accumulate over time (running totals).

**Example: Cumulative Revenue**

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Cumulative_Revenue_mtc \
  --label "Cumulative Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --is-cumulative
```

**When to use:** Year-to-date totals, running sums, cumulative counts.

**Note:** Add `--is-cumulative` flag to `create_metric.py` script (you may need to add this flag if not already supported).

## Sentiment Configuration

Metrics support sentiment indicators that affect how insights are displayed.

### SentimentTypeUpIsGood (Default)

Use when increases are positive (revenue, wins, customer satisfaction).

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
  # Default sentiment is UpIsGood
```

### SentimentTypeUpIsBad

Use when increases are negative (costs, churn, complaints).

**Example: Customer Churn Rate**

```bash
# Assuming you add --sentiment flag to create_metric.py:
python scripts/create_metric.py \
  --sdm Customer_Success_Model \
  --name Churn_Rate_mtc \
  --label "Customer Churn Rate" \
  --calculated-field Churn_Rate_clc \
  --time-field Churn_Date \
  --time-table Customer_TAB \
  --sentiment SentimentTypeUpIsBad
```

### SentimentTypeNone

Use for neutral metrics (headcount, capacity, inventory).

**Example: Headcount**

```bash
python scripts/create_metric.py \
  --sdm HR_Workforce_Model \
  --name Headcount_mtc \
  --label "Headcount" \
  --calculated-field Headcount_clc \
  --time-field Hire_Date \
  --time-table Employee_TAB \
  --sentiment SentimentTypeNone
```

## Time Dimension Selection

Choosing the right time dimension affects metric behavior:

### Transaction Date

Use the date when the event occurred (most common).

- **Revenue metrics** → `Close_Date`
- **Lead metrics** → `Created_Date`
- **Support metrics** → `Case_Created_Date`

### Effective Date

Use when you want to measure state at a point in time.

- **Headcount** → `Hire_Date` or `Snapshot_Date`
- **Inventory** → `Inventory_Date`

### Reporting Date

Use for fiscal/reporting period alignment.

- **Fiscal metrics** → `Fiscal_Period_Date`

### Anchor on a business-meaningful date — not a plumbing column

A metric's time anchor must be a **business event date**. Anchoring on a
system/load column produces a time series that tracks the *data pipeline*, not
the business — a silent correctness bug: the metric "works," renders, and is
wrong. `create_metric.py` **rejects** a plumbing-date anchor by default.

Negative list (rejected unless you pass `--allow-junk-time-anchor`):

| Pattern | Examples | Why it's not a business date |
|---|---|---|
| `cdp_sys_*` | `cdp_sys_PartitionDate` | Data Cloud partitioning/system column |
| `*_SourceVersion` | `Account_SourceVersion` | Ingest version stamp, not an event |
| load / ingest timestamps | `load_timestamp`, `ingest_date`, `system_ts` | When the row landed, not when the event happened |
| `KQ_*` | `KQ_flightid__c` | Data Cloud key-qualifier system field |
| connector bookkeeping | `DataSourceObject__c`, `DataSource__c` | Pipeline metadata |

If a "plumbing"-named column genuinely is the intended anchor (rare), override
explicitly:

```bash
python scripts/create_metric.py ... \
  --time-field cdp_sys_PartitionDate --time-table My_Object \
  --allow-junk-time-anchor
```

## Metric Naming Best Practices

**Good metric names:**
- `Total_Revenue_mtc` — Clear, specific
- `Win_Rate_mtc` — Concise, business-friendly
- `Avg_Sales_Cycle_mtc` — Descriptive, indicates aggregation

**Bad metric names:**
- `Metric_1_mtc` — Generic, meaningless
- `Rev_mtc` — Too abbreviated
- `Total_Revenue_by_Region_mtc` — Don't include dimension in name (use `additionalDimensions` instead)

**Rules:**
- Describe WHAT is measured, not HOW it's broken down
- Use business terminology, not technical jargon
- Be specific but concise
- Always end with `_mtc`

## Testing Metrics

After creating a metric, test it by:

1. **Dashboard widget test** — Reference the metric in a Tableau Next dashboard KPI widget
2. **Verify in consumption layer** — Reference the metric in Tableau Next dashboard widgets
3. **Breakdown test** — Verify additional dimensions enable proper insights

**Verification checklist:**
- Metric appears in SDM discovery
- Time dimension enables proper time-series analysis
- Additional dimensions (if any) generate proper insights
- Values are calculated correctly
- Sentiment displays correctly

## Common Patterns Summary

| Pattern | Calc Field Expression | Aggregation | Use Case |
|---------|----------------------|-------------|----------|
| Simple sum | `SUM([Field])` | Sum | Total revenue, total count |
| Average | `AVG([Field])` | Avg | Average deal size, average duration |
| Ratio | `SUM([A]) / SUM([B])` | UserAgg | Win rate, conversion rate |
| Weighted | `SUM([A] * [B])` | Sum | Weighted pipeline, risk-adjusted |
| Time calc | `AVG(DATEDIFF('day', [Start], [End]))` | Avg | Sales cycle, time to close |
| Conditional sum | `SUM(IF condition THEN [Field] ELSE 0 END)` | Sum | Won revenue, qualified leads |

## Metric Lifecycle

1. **Design** — Identify business question and required calc field
2. **Create calc field** — Build the measurement logic
3. **Create metric** — Wrap calc field with time dimension and breakdowns
4. **Test** — Verify in Tableau Next dashboard widget
5. **Iterate** — Adjust based on user feedback
6. **Reuse** — Reference metric in multiple Tableau Next dashboards

Metrics are designed for reuse—create once, use everywhere. This centralizes business logic and ensures consistency across dashboards.

## Metric Structure (fields on the payload)

Metrics include:
- `measurementReference.calculatedFieldApiName` — references the calc field
- `timeDimensionReference` — field + table for time-based analysis
- `timeGrains` — defaults to `["Day", "Week", "Month", "Quarter", "Year"]`
- `additionalDimensions` — optional breakdown dimensions
- `insightsSettings` — auto-generated when additional dimensions exist
- `isCumulative` — set to `true` for cumulative metrics (default `false`)
- `sentiment` — `SentimentTypeUpIsGood`, `SentimentTypeUpIsBad`, or `SentimentTypeNone`

## Automatic insightsSettings when additional dimensions are provided

When additional dimensions are provided, the system automatically generates `insightsSettings` with enabled insight types (TopContributors, TrendChangeAlert, BottomContributors, etc.) and maps the dimensions to `insightsDimensionsReferences`.
