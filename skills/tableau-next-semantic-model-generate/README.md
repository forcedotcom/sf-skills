# Tableau Next Semantic Model Generate

Build and enrich Semantic Data Models on Salesforce Data 360, powering the Tableau Next semantic layer. Author an SDM from scratch — create a model on an existing DLO/DMO, add data objects, and join them with model-level relationships — or enrich an existing SDM with calculated fields, dimensions, and metrics.

## Quick Start

```bash
# 1. Discover available SDMs
python scripts/discover_sdm.py --list

# 2. Inspect SDM structure
python scripts/discover_sdm.py --sdm Sales_Cloud12_backward --json

# 3. Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Won_Count]) / SUM([Total_Count])" \
  --aggregation UserAgg

# 4. Create metric referencing the calculated field
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Win_Rate_mtc \
  --label "Win Rate" \
  --calculated-field Win_Rate_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

## What This Skill Does

- **Discover** — List SDMs and inspect objects, fields, and relationships
- **Build an SDM from scratch** — Create a model on an existing DLO/DMO (anchor + incremental), add data objects, and join them with model-level relationships
- **Create calculated fields** — Add custom business logic (measurements and dimensions)
- **Create metrics** — Build time-based KPIs for Tableau Next dashboards
- **Validate** — Check Tableau expressions and structural payloads before POSTing

**Out of scope:** creating DLOs/DMOs, data streams, DLO→DMO mapping, and logical views (UI-only).

## When to Use

Use this skill **before** building Tableau Next dashboards when you need:
- Custom business logic (win rates, conversion rates, weighted pipelines)
- Categorical dimensions derived from other fields
- Reusable metrics across multiple dashboards
- Standardized business definitions on the semantic layer

## Scripts

All scripts live under `scripts/` and share library modules from `scripts/_shared/`. Verify the layout with:

```bash
python scripts/_shared/verify_paths.py
```

## Prerequisites

- Salesforce CLI (`sf`) authenticated to a Data 360-enabled org with semantic model access
- Python 3.8+ with the `requests` library (`pip install -r scripts/requirements.txt`)
- `jq` for JSON parsing

**Quick setup:**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org auth show-access-token --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

## Common Use Cases

### Create a Win Rate Metric

```bash
# Step 1: Create calculated field
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

### Create a Metric with Breakdown Dimensions

```bash
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Revenue_by_Region_mtc \
  --label "Revenue by Region" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud \
  --additional-dimension "Region:Opportunity_TAB_Sales_Cloud" \
  --additional-dimension "Industry:Account_TAB_Sales_Cloud"
```

### Create a Categorical Dimension

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Deal_Size_Category_clc \
  --label "Deal Size Category" \
  --expression "IF [Amount] > 100000 THEN 'Large' ELSEIF [Amount] > 50000 THEN 'Medium' ELSE 'Small' END"
```

## Next Steps

After enriching the semantic layer:
- **Build visualizations** — Reference your new calculated fields when authoring Tableau Next visualizations
- **Build dashboards** — Reference metrics in Tableau Next dashboard KPI widgets

## Documentation

See [SKILL.md](SKILL.md) for complete documentation including:
- Discovery workflow
- Calculated field patterns
- Metric design best practices
- Tableau function reference
- Common errors and fixes

---

