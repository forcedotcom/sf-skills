# KPI Formulas & Aggregation Patterns

Business-logic reference for building calculated fields (`_clc`) and metrics (`_mtc`) on a Tableau Next semantic model. Provides lookup tables for custom aggregations, composite KPI formulas, and color semantics observed across finance, banking, sales, HR, retail, marketing, procurement, supply-chain, travel, and executive dashboards.

---

## Table of Contents

- [Time-Based Aggregation Patterns](#time-based-aggregation-patterns)
- [Composite KPI Patterns](#composite-kpi-patterns)
- [Color Coding Guide](#color-coding-guide)
- [Palette Usage by Metric Type](#palette-usage-by-metric-type)
- [Metric Clarifications](#metric-clarifications)
- [Industry-Specific KPI Patterns](#industry-specific-kpi-patterns)

---

## Time-Based Aggregation Patterns

Native Tableau formulas for time-based business calculations. Replace `[Date]`, `[Measure]`, `[Dimension]` placeholders with actual field names from your semantic model.

### Snapshot & Position Aggregations

| Pattern | Tableau Formula | Business Use Case |
|---------|-----------------|-------------------|
| **Sum of (last period only)** | `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [Measure] ELSE NULL END)` | Balance sheets, headcount snapshots, portfolio positions, inventory levels |
| **Sum of (first period only)** | `SUM(IF [Date] = { INCLUDE : MIN([Date]) } THEN [Measure] ELSE NULL END)` | Initial investment positions, opening balances |
| **Average of (last period only)** | `AVG(IF [Date] = { INCLUDE : MAX([Date]) } THEN [Measure] ELSE NULL END)` | Staff demographics at period end, current average values |
| **Median of (last period only)** | `MEDIAN(IF [Date] = { INCLUDE : MAX([Date]) } THEN [Measure] ELSE NULL END)` | Central tendency for period-end snapshots |
| **Count Distinct of (last period only)** | `COUNTD(IF [Date] = { INCLUDE : MAX([Date]) } THEN [Dimension] ELSE NULL END)` | Ending counts of unique items (Active Customers EOP, Open Positions) |

**When to use:** For metrics that represent a state at a specific point in time rather than cumulative totals. Q1 value = last known value in Q1.

### Time-Scaled Aggregations

| Pattern | Tableau Formula | Business Use Case |
|---------|-----------------|-------------------|
| **Sum of (annualized)** | `SUM([Measure]) * (12 / COUNTD(DATEPART('month', [Date])))` | Revenue projections; 1 month × 12, 2 months × 6, 3 months × 4 |
| **Sum of (monthly average)** | `SUM([Measure]) / COUNTD(DATEPART('year', [Date]) + DATEPART('month', [Date]))` | Avg Monthly Inventory, Avg Monthly Assets |

**Annualization logic:** Extrapolate partial-period values to full year.

### Period Range Aggregations

| Pattern | Tableau Formula | Business Use Case |
|---------|-----------------|-------------------|
| **Sum of (from to)** | `SUM(IF [Date] >= [FromDate] AND [Date] <= [ToDate] THEN [Measure] END)` | Total Sales During Contract, Revenue in Date Range |
| **Average of (from to)** | `AVG(IF [Date] >= [FromDate] AND [Date] <= [ToDate] THEN [Measure] END)` | Avg Deal Size During Q1-Q3 |
| **Min/Max/Median (from to)** | Same pattern with MIN, MAX, MEDIAN | Lowest inventory, peak revenue, median ticket |
| **Count Distinct (from to)** | `COUNTD(IF [Date] >= [FromDate] AND [Date] <= [ToDate] THEN [Dimension] END)` | Unique Customers Between Launch-EOY |

**When to use:** For metrics that need to aggregate data only within a specific date range.

### Lifecycle & Cohort Aggregations

| Pattern | Tableau Formula | Business Use Case |
|---------|-----------------|-------------------|
| **Count Distinct of New** | `COUNTD(IF [Date] = { FIXED [Dimension] : MIN([Date]) } THEN [Dimension] END)` | New Customers, New Products, New Hires |
| **Count Distinct of Ending** | `COUNTD(IF [Date] = { FIXED [Dimension] : MAX([Date]) } THEN [Dimension] END)` | Lost Customers, Discontinued Products |
| **Sum of (for New)** | `SUM(IF [Date] = { FIXED [Dimension] : MIN([Date]) } THEN [Measure] END)` | Revenue from New Customers only |
| **Avg Lifetime of** | `DATEDIFF('day', { FIXED [Dimension] : MIN([Date]) }, { INCLUDE [Dimension] : MAX([Date]) }) / 365` | Customer tenure (years), Product lifetime, Employee tenure |

**When to use:** For cohort analysis, churn tracking, and new/lost item identification.

### Time Interval Calculations

| Pattern | Tableau Formula | Business Use Case |
|---------|-----------------|-------------------|
| **Avg Years between** | `DATEDIFF('day', [StartDate], [EndDate]) / 365` | Avg Years to Maturity, Avg Investment Horizon |
| **Avg Months between** | `DATEDIFF('day', [StartDate], [EndDate]) / 365 * 12` | Avg Months to Close, Loan Duration |
| **Avg Days between** | `DATEDIFF('minute', [StartDate], [EndDate]) / (24 * 60)` | Days to Close, Days Between Booking-Travel |
| **Avg Hours between** | `DATEDIFF('minute', [StartDate], [EndDate]) / 60` | Avg Response Time |
| **Avg Minutes between** | `DATEDIFF('minute', [StartDate], [EndDate])` | Avg Call Duration |
| **Avg Seconds between** | `DATEDIFF('second', [StartDate], [EndDate])` | Avg Page Load Time |

---

## Composite KPI Patterns

Real-world KPI formulas from production dashboards (finance, banking, sales).

### Financial Statement Patterns

#### Income Statement (Profit & Loss)

| Pattern | Formula | Example |
|---------|---------|---------|
| **Gross Profit** | Revenues - Cost of Revenues | `KPI1 - KPI2` where KPI1=Total Revenues, KPI2=COGS |
| **Gross Margin %** | Gross Profit / Revenues | `(Revenues - COGS) / Revenues` |
| **Operating Income** | Gross Profit - (OpEx + Depreciation) | `KPI2 - (KPI4 + KPI12)` |
| **Operating Income %** | Operating Income / Revenues | `Operating Income / Total Revenues` |
| **Net Income** | Operating Income - (Interests + Taxes) | `KPI13 - KPI15` |

**Tableau Implementation:**
```xml
<kpi-simple name='KPI1' aggregation='SUM' canonical-attribute='IF STARTSWITH(UPPER(Dim2),"REVENUES") THEN Value END' />
<kpi-simple name='KPI11' aggregation='SUM' canonical-attribute='IF STARTSWITH(UPPER(Dim2),"COST OF REVENUES") THEN Value END' />
<kpi-composite name='KPI2' caption='Gross Profit' kpi1-name='KPI1' calculation='-' kpi2-name='KPI11' />
```

#### Balance Sheet

| Pattern | Formula | Example |
|---------|---------|---------|
| **Working Capital** | Current Assets - Current Liabilities | `KPI17 - KPI18` using snapshot aggregation |
| **Total Assets** | Current Assets + Non-Current Assets | Sum all asset categories with snapshot aggregation |
| **Total Equity** | Total Assets - Total Liabilities | `KPI21 - KPI22` |
| **Current Ratio** | Current Assets / Current Liabilities | `KPI17 / KPI18` |
| **Quick Ratio** | (Cash + AR) / Current Liabilities | `KPI24 / KPI18` |
| **Debt to Equity** | Total Liabilities / Total Equity | `KPI22 / KPI7` |

**Critical:** Use snapshot aggregation (`SUM(IF [Date] = MAX([Date]) THEN ... END)`) for balance sheet accounts.

### Banking & Wealth Management Patterns

#### Assets under Management (AuM)

| Pattern | Formula | Business Meaning |
|---------|---------|------------------|
| **Net New Money (NNM)** | Inflows - Outflows | `zn(Inflows) + zn(Outflows)` (Outflows are negative) |
| **AuM Balance** | Last period AuM (snapshot) | Use snapshot aggregation: `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [AuM] END)` |
| **AuM per Client** | Total AuM / Nb of Clients | `KPI3 / KPI6` |
| **Return on Assets %** | Annualized Income / Avg Monthly AuM | `SUM(Income)*12/COUNTD(Month) / (SUM(AuM)/COUNTD(Month))` |
| **New Clients** | Count new occurrences | `COUNTD(IF [Date] = { FIXED [Client] : MIN([Date]) } THEN [Client] END)` |
| **Lost Clients** | Count ending occurrences | `COUNTD(IF [Date] = { FIXED [Client] : MAX([Date]) } THEN [Client] END)` |
| **Client Asset & Liabilities (CAL)** | AuM + Lending Stock | `KPI3 + KPI17` |
| **Net New Lending (NNL)** | Lending Inflows + Lending Outflows | `KPI21 + KPI23` |

#### Lending & Loans

| Pattern | Formula | Business Meaning |
|---------|---------|------------------|
| **Total Revenue** | Interests + Fees | `KPI2 + KPI4` (monthly totals) |
| **Revenue Rate %** | (Interests + Fees) / Loan Amortization | `KPI11 / KPI3` |
| **Delinquent Loans Rate %** | Delinquent Count / Total Active Loans | `KPI14 / KPI5` |
| **Default Rate %** | Defaulted Count / Total Active Loans | `KPI15 / KPI5` |
| **Client Liabilities (EOP)** | Outstanding balance at period end | `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [ClientLiabilities] END)` |

### Sales & Travel Patterns

| Pattern | Formula | Example |
|---------|---------|---------|
| **Average Spend per Customer** | Total Amount / Count Distinct Customers | `KPI1 / KPI7` |
| **Share of Metric** | AVG(IF condition THEN 1 ELSE 0 END) | `AVG(if upper(Dim11)="Y" then 1 else 0 end)` for "% Online" |
| **Over-pricing %** | (Actual - Lowest) / Lowest | `(TicketAmount - LowestFare) / LowestFare` |
| **Days Between Events** | `DATEDIFF('minute', [Date1], [Date2]) / (24 * 60)` | Days between booking and travel |
| **Tickets per Traveler** | Total Tickets / Distinct Travelers | `KPI5 / KPI7` |

### Supply Chain Patterns

| Pattern | Formula | Business Meaning |
|---------|---------|------------------|
| **Product Demand Index** | Integer scale 1-5 (Low to High) | Direct measure, no calculation |
| **Logistics Reliability** | Integer scale 1-5 | Direct measure, use MEDIAN or AVG |
| **Inflation Impact** | Integer scale 1-5 | Direct measure for risk scoring |

---

## Usage Notes

### Aggregation Selection Criteria

1. **Snapshot metrics** (balance sheet, headcount, inventory): Use `SUM(IF [Date] = MAX([Date]) THEN ... END)`
2. **Flow metrics** (revenue, expenses, transactions): Use standard `SUM`, `AVG`, `COUNT`
3. **New/lost tracking**: Use `COUNTD(IF [Date] = { FIXED [Dim] : MIN/MAX([Date]) } THEN [Dim] END)`
4. **Time-between calculations**: Use `DATEDIFF('day', [Start], [End])` with appropriate unit
5. **Annualized projections**: Use `SUM([Measure]) * (12 / COUNTD(Month))`
6. **Period-constrained aggregations**: Use `SUM(IF [Date] >= [From] AND [Date] <= [To] THEN ... END)`

---

## Cross-References

- See [metric-design.md](metric-design.md) for Tableau Next semantic metric patterns
- See [field-types.md](field-types.md) for calculated measurement vs dimension guidance
- See [tableau-functions.md](tableau-functions.md) for Tableau expression functions

---

## Metric Clarifications

Before implementing a KPI, determine which variant matches the business question. Many pattern names suggest lifetime or strategic metrics, but the formula may be period-specific.

### Period vs Lifetime Metrics

| Type | When to Use | Formula Pattern | Example |
|------|-------------|-----------------|---------|
| **Period** | "Revenue per customer this month" | `SUM(Measure) / COUNTD(Dimension)` | Total Sales / Active Customers |
| **Lifetime** | "Total value of a customer over their entire relationship" | `{ FIXED [Dimension]: SUM(Measure) }` | `{ FIXED [Customer]: SUM([Revenue]) }` |

**Rule:** If the metric name includes "Lifetime," "LTV," "CLV," or "Total Value," use an LOD expression to aggregate at the entity level first, then average or sum as needed.

### Simple vs Fully-Loaded Costs

| Type | When to Use | Example |
|------|-------------|---------|
| **Simple** | Quick operational view | CAC = Marketing Spend / New Customers |
| **Fully-Loaded** | Strategic investment decisions | CAC = (Marketing + Sales salaries + Overhead + Tools) / New Customers |

**Rule:** Document which cost components are included. "CAC" without qualification typically means marketing-only; "fully-loaded CAC" includes sales and overhead.

### Snapshot vs Flow Metrics

| Type | When to Use | Aggregation | Example |
|------|-------------|-------------|---------|
| **Snapshot** | State at a point in time | `SUM(IF [Date] = MAX([Date]) THEN ... END)` | MRR, Headcount (EOP), Inventory |
| **Flow** | Activity over a period | `SUM`, `COUNT` | Revenue, Orders, New Customers |

**Rule:** Use snapshot aggregation for balance-sheet style metrics; use `SUM`/`COUNT` for income-statement style metrics.

### Attribution Models

For marketing metrics (ROAS, CPA, Conversion Rate), clarify:
- **Total:** All revenue in period ÷ ad spend (simple, may over-attribute)
- **Attributed:** Revenue/conversions filtered to ad-sourced customers only (requires attribution dimension)

---

## Industry-Specific KPI Patterns

Business formulas extracted from 61 production dashboard templates across multiple industries.

### Sales & E-Commerce

**Customer Lifetime Value (CLV) Patterns**

Real CLV answers: "How much total revenue will this customer generate over their entire relationship?" Use these patterns when the user asks for CLV, LTV, or Customer Lifetime Value.

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **CLV per Customer** | `{ FIXED [Customer]: SUM([Revenue]) }` | Total revenue per customer over entire history |
| **Average CLV** | `AVG([CLV per Customer])` | Portfolio average lifetime value |
| **Predictive CLV** | AOV × Purchase Frequency × Customer Lifespan | Forward-looking estimate; use `DATEDIFF('day', { FIXED [Customer] : MIN([Date]) }, { INCLUDE [Customer] : MAX([Date]) }) / 365` for lifespan |
| **Cohort CLV** | `SUM([CLV per Customer])` where Customer in cohort | Total value of a cohort |

**When to use each:** CLV per Customer is the base calc field; Average CLV for KPI cards; Predictive CLV when you need forward-looking estimates without full history.

**Period Metrics (not lifetime):**

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Sales per Customer** | Total Sales / Active Customers | `KPI1 / KPI2` - Average customer spend in period; for lifetime value, see CLV patterns above |
| **New Customers** | `COUNTD(IF [Date] = { FIXED [Customer] : MIN([Date]) } THEN [Customer] END)` | Count first-time customers in period |
| **Sales Margin %** | Total Margin / Total Sales | `KPI4 / KPI1` - Profitability percentage |
| **Sales Costs %** | (Sales - Margin) / Sales | `KPI9 / KPI1` - Cost ratio |
| **Average Selling Price** | Total Sales / Total Quantity | `KPI1 / KPI5` - Price per unit |
| **Gross Discount %** | (Volume at List Price - Sales Incl VAT) / Volume at List Price | Discount effectiveness |
| **Net Discount %** | (Volume at List Price - Sales Excl VAT) / Volume at List Price | After-tax discount |
| **VAT Amount** | Sales Incl VAT - Sales Excl VAT | Tax calculation |

**E-Commerce Specific:**

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Customer Acquisition Cost (CAC)** | Marketing Costs / New Customers | `SUM(IF [Date] = { FIXED [Customer] : MIN([Date]) } THEN [MarketingCosts] END) / COUNTD(IF [Date] = { FIXED [Customer] : MIN([Date]) } THEN [Customer] END)` |
| **CLV/CAC Ratio** | Average CLV / CAC | Profitability of acquisition; CLV = `{ FIXED [Customer]: SUM([Revenue]) }` averaged (see CLV patterns above) |
| **Conversion Rate** | Orders / Visits | Visitor-to-customer conversion |
| **Average Order Value (AOV)** | Total Revenue / Number of Orders | Revenue per transaction |
| **Cart Abandonment %** | (Carts Created - Orders) / Carts Created | Lost sales opportunity |

### Recurring Revenue (SaaS/Subscription)

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **MRR (Monthly Recurring Revenue)** | `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [MonthlyRecurringRevenue] END)` | Snapshot at period end |
| **ARR (Annual Recurring Revenue)** | `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN 12 * [MonthlyRecurringRevenue] END)` | Annualized recurring revenue |
| **Total Revenue** | SUM(ZN(OneTimeFee) + ZN(MonthlyRecurringRevenue)) | Recurring + one-time fees |
| **Recurring Revenue %** | Period Recurring Revenue / Total Revenue | `KPI5 / KPI1` - Subscription mix |
| **Contract Duration (months)** | `DATEDIFF('day', [StartDate], [EndDate]) / 365 * 12` | Average contract length |
| **Revenue per Account** | Total Revenue / Active Accounts | `KPI1 / KPI2` - Period metric; for account lifetime value, use `{ FIXED [Account]: SUM([Revenue]) }` |
| **New Active Accounts** | `COUNTD(IF [Date] = { FIXED [Account] : MIN([Date]) } THEN [Account] END)` | First-time contracts |

**Key Insight:** Use snapshot aggregation for MRR/ARR (last period value), not `SUM`.

### Retail & Inventory

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Sales per Store** | Total Sales / Active Stores | `KPI1 / KPI7` - Store productivity |
| **Distinct Products Sold** | COUNTD(Product) | Catalog depth |
| **Average Inventory Value** | SUM(On-Hand Amount) / COUNTD(Date) | Average inventory holding |
| **Total On-Hand Inventory** | `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [OnHandAmount] END)` | Snapshot inventory value |
| **Inventory Turnover** | (Days in Year × Total Sales) / Total On-Hand Inventory | `(DAYSinYEAR * KPI1) / KPI101` - Turns per year; higher = faster sell-through |
| **Days Sales of Inventory (DSI)** | Total On-Hand Inventory / (Total Sales / 365) | Days to sell current inventory; use `Inventory / Daily Sales` for correct time dimension |
| **Average Selling Price** | Total Sales / Total Sales Units | `KPI1 / KPI50` - Price per unit |
| **Out-of-Stock Positions** | SUM(IF On-Hand Units = 0 THEN 1 END) | Count of stockouts |
| **Out-of-Stocks %** | Out-of-Stock Positions / Inventory Positions | `KPI13 / KPI14` - Stockout rate |

### Procurement & Supply Chain

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Spend per Vendor** | Total Spend / Active Vendors | `KPI1 / KPI2` - Vendor concentration |
| **New Vendor #** | `COUNTD(IF [Date] = { FIXED [Vendor] : MIN([Date]) } THEN [Vendor] END)` | First-time suppliers |
| **Average Buying Price** | Purchasing Volume / Total Purchase Quantity | `KPI1 / KPI5` - Unit cost |
| **Spend Under Management (SuM)** | `SUM(IF [Date] >= [StartDate] AND [Date] <= [EndDate] THEN [Amount] END)` | Contracted spend in period |
| **Ongoing Contracts** | `COUNTD(IF [Date] >= [StartDate] AND [Date] <= [EndDate] THEN [Contract] END)` | Active contracts during period |
| **Active Suppliers** | `COUNTD(IF [Date] >= [StartDate] AND [Date] <= [EndDate] THEN [Supplier] END)` | Suppliers with active contracts |
| **Avg Contract Size** | Spend Under Management / Ongoing Contracts | `KPI1 / KPI2` - Contract value |


### Digital Marketing & Advertising

**Google Analytics:**

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Bounce Rate %** | Bounced Sessions / Total Sessions | Single-page visits |
| **Pages per Session** | Total Pageviews / Total Sessions | Engagement depth |
| **Avg Session Duration** | `DATEDIFF('second', [SessionStart], [SessionEnd])` | Time on site |
| **Conversion Rate %** | Goal Completions / Total Sessions | Success rate |
| **Cost per Click (CPC)** | Total Ad Spend / Total Clicks | Click efficiency |
| **Click-Through Rate (CTR) %** | Clicks / Impressions | Ad engagement |

**Google/Facebook/Twitter Ads:**

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Cost per Acquisition (CPA)** | Total Spend / Conversions | `KPI1 / KPI3` - Conversion cost |
| **Return on Ad Spend (ROAS)** | Revenue / Ad Spend | `KPI4 / KPI1` - Total period revenue ÷ ad spend; for attributed ROAS, filter revenue to ad-sourced conversions |
| **CPM (Cost per 1000 Impressions)** | (Total Spend / Impressions) × 1000 | Reach cost |
| **Conversion Rate %** | Conversions / Clicks | Click-to-conversion rate |
| **Quality Score** | (CTR × Relevance × Landing Page Experience) | Ad platform ranking |
| **Cost per Lead (CPL)** | Total Spend / Leads Generated | Lead acquisition cost |

**Email Marketing:**

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Open Rate %** | Emails Opened / Emails Delivered | Email engagement |
| **Click Rate %** | Clicks / Emails Delivered | Link engagement |
| **Click-to-Open Rate (CTOR) %** | Clicks / Opens | Engaged reader action |
| **Unsubscribe Rate %** | Unsubscribes / Emails Delivered | List health |
| **Bounce Rate %** | Bounced Emails / Total Emails Sent | Deliverability |
| **Conversion Rate %** | Conversions / Emails Delivered | Campaign effectiveness |

### Sales Performance & Quotas

| Pattern | Formula | Business Use Case |
|---------|---------|-------------------|
| **Sales vs Quota** | Total Sales - Total Quota | `KPI1 - KPI2` - Variance amount |
| **Quota Attainment %** | Total Sales / Total Quota | `KPI1 / KPI2` - Achievement rate |
| **Market Share %** | Our Sales / Total Market Size | `KPI2 / KPI1` - Competitive position |

### RFM Analysis (Customer Segmentation)

**Recency, Frequency, Monetary analysis** - Template focuses on segmentation visualizations rather than formulas. Primary KPIs:
- Total Sales: SUM(SalesAmount)
- Active Customers #: COUNTD(Customer)

Segmentation happens in visualization layer using FIXED LOD calculations on last purchase date, purchase count, and average spend.

---

## Advanced Aggregation Use Cases by Industry

### Finance: Balance Sheet Accounts
- **Use:** Snapshot aggregation for all asset/liability accounts
- **Why:** Balance sheets are snapshots at period end, not cumulative totals
- **Formula:** `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [Measure] END)`

### Banking: Portfolio Positions
- **Use:** Snapshot aggregation for AuM, Lending Stock
- **Why:** Account balances are point-in-time values
- **Pattern:** `COUNTD(IF [Date] = { FIXED [Client] : MIN/MAX([Date]) } THEN [Client] END)` for client churn

### Sales: New/Lost Customer Tracking
- **Use:** `COUNTD(IF [Date] = { FIXED [Customer] : MIN([Date]) } THEN [Customer] END)` for new customers
- **Why:** First transaction ever per customer
- **Pattern:** New Customers = first transaction in period

### Retail: Inventory Management
- **Use:** Snapshot aggregation for on-hand inventory, `SUM` for sales
- **Why:** Inventory is snapshot; sales are cumulative
- **Pattern:** Inventory Turnover = (Annual Sales) / (Average Inventory)

### Recurring Revenue: MRR/ARR
- **Use:** Snapshot aggregation for MRR (not SUM!)
- **Why:** MRR is the recurring revenue at period end, not summed across days
- **Formula:** `SUM(IF [Date] = { INCLUDE : MAX([Date]) } THEN [MonthlyRecurringRevenue] END)`

### Procurement: Contract Duration
- **Use:** `SUM(IF [Date] >= [From] AND [Date] <= [To] THEN [Amount] END)` for active contracts
- **Why:** Only count/sum contracts active between start/end dates
- **Pattern:** Spend Under Management = contracts overlapping the analysis period

### Digital Marketing: Time-Based Metrics
- **Use:** `DATEDIFF('second', [Start], [End])` for session duration, response time
- **Why:** Native time difference calculations
- **Pattern:** Avg Session Duration = `DATEDIFF('second', [SessionStart], [SessionEnd])`

---

**Coverage:** 61 production dashboard templates across Finance (P&L, Balance Sheet, Cash Flow), Banking (AuM, Lending, Loans), Sales (Basic, Expert, Margin, Discount/VAT, RFM, Market Share), Recurring Revenue (SaaS/Subscription), Retail (Sales, Inventory), E-Commerce, Digital Marketing (Google Analytics, Google Ads, Facebook Ads, Twitter Ads, Email Marketing), Procurement (Spend Analytics, Purchasing, Contracts), Supply Chain, Travel, and CEO Cockpits.
