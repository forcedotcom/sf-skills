---
name: tableau-next-semantic-model-generate
description: "Salesforce Data 360 Semantic Layer authoring for Tableau Next. Build and enrich Semantic Data Models (SDMs): author from scratch on existing DLOs/DMOs, add data objects, define model-level joins, and enrich with calculated measurements (_clc), calculated dimensions (_clc), and semantic metrics (_mtc). TRIGGER when: the user asks to create/build a semantic data model or SDM, add a data object to an SDM, join two data objects with a model-level relationship, create a metric or calculated field, enrich or make an SDM AI-ready, validate a Tableau expression, or discover SDM fields. DO NOT TRIGGER when: creating DLOs/DMOs/data streams or DLO→DMO mapping (use data360-prepare/harmonize), designing Tableau Next visualizations or dashboards, defining a Pulse metric on Tableau Cloud, or writing standard CRM SOQL (use platform-soql-query)."
compatibility: "Requires Salesforce CLI (sf), Python 3.8+, and jq. Requires an authenticated Data 360-enabled org with semantic model access."
metadata:
  version: "1.0"
  api-version: "v66.0"
---

# Semantic Layer Authoring

Enrich Semantic Data Models (SDMs) with calculated fields, dimensions, and metrics. This skill focuses on data modeling—creating reusable business logic on the semantic layer before visualization or dashboard authoring.

## When to Use This Skill

Use this skill when you need to:
- **Author an SDM from scratch** — create a model on an existing DLO/DMO, add data objects, and join them with model-level relationships
- Create calculated measurements or dimensions on an SDM
- Build semantic metrics for Tableau Next dashboard KPI widgets
- Validate Tableau expressions before creating fields
- Discover SDM structure and identify missing fields
- Standardize business logic across dashboards

**Build vs. enrich:** *Building* an SDM (this skill's "Author an SDM from
scratch" workflow) creates the model and its objects/joins on data that already
exists in Data 360. *Enriching* adds `_clc`/`_mtc` business logic on top. The creation of
data objects themselves (DLOs/DMOs, data streams, DLO→DMO mapping) is **out of scope here**.

**Don't use this skill for:** visualizations, dashboards, or Pulse metric definitions (Pulse is Tableau Cloud; those have dedicated skills).

**Trigger examples (SHOULD use this skill):**
- "Create a win rate metric on Sales_Cloud12_backward"
- "Add a calculated field for deal size categories"
- "What fields are available in the Sales model?"
- "Build a metric for revenue by region"
- "Validate this Tableau expression: SUM([Table].[Won]) / SUM([Table].[Total])"
- "Create a dimension that extracts month from Close_Date"

**Don't trigger (use other skills):**
- "Create a bar chart showing revenue by region" → a Tableau Next visualization/dashboard skill
- "Build a sales dashboard" → a Tableau Next visualization/dashboard skill
- "Set up a Pulse metric definition" → Tableau Cloud (Pulse) tooling

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Build an SDM from scratch | [Author an SDM from Scratch](#author-an-sdm-from-scratch) |
| See available SDMs | [Discovery Workflow](#discovery-workflow) |
| Create a calculated field | [Calculated Fields](#calculated-fields) |
| Create a metric | [Semantic Metrics](#semantic-metrics) |
| Make a model AI-ready / update a metric | [Make the SDM AI-Ready](#make-the-sdm-ai-ready) |
| Validate an expression | [Validation](#validation) |
| Fix common errors | [Common Errors](#common-errors) |
| See script examples | [Script Cheat Sheet](#script-cheat-sheet) |

## Core Concepts

- **Base field** binds an existing source column to one object (`data-objects/{obj}/measurements|dimensions`) — use for model structure.
- **Calculated field** (`_clc`) is a model-level formula — use when you must compute a value no column holds.
- **Metric** (`_mtc`) is a lightweight wrapper over a calc field, with time dimension + grains, used by dashboard KPI widgets.
- **Two-step workflow**: create calc field first, then the metric that references it by API name.
- **Creation is verified by querying**: `create_calc_field.py` / `create_metric.py` run a semantic query on the new field/metric and report **done** only when it returns non-empty data. Empty → **NOT shippable** (non-zero exit). Use `--skip-verify` only with a deliberate reason.

Deep dive + verify contract details in **[references/concepts.md](references/concepts.md)**.

### Naming Conventions

- Calculated fields end with `_clc` (e.g., `Win_Rate_clc`, `Total_Revenue_clc`)
- Metrics end with `_mtc` (e.g., `Win_Rate_mtc`, `Total_Revenue_mtc`)
- No double underscores (`__`) anywhere in the name — Salesforce rejects them
- Use descriptive names that communicate business meaning (not `Field_1` or `Metric_2`)

## Author an SDM from Scratch

Build a Semantic Data Model on data objects that **already exist** in Data 360
(DLOs / DMOs / Calculated Insights). The **anchor + incremental** workflow dodges
the bulk-create timeout, the apiName auto-suffixing, and the relationship
field-lookup error. See [references/sdm-creation-api.md](references/sdm-creation-api.md)
for the endpoint + payload reference.

> **Out of scope:** creating the DLOs/DMOs themselves, data streams, DLO→DMO
> mapping, and **logical views** (UI-only — there is no `create_logical_view` REST surface).
> Don't attempt to author those here.

### The sequence

**discover data objects → create anchor → resolve apiNames → add object →
add relationship (one at a time) → verify by querying the join.**

```bash
# 1. DISCOVER what data objects exist to anchor on, and what's already modeled.
python scripts/discover_sdm.py --list

# 2. CREATE the model with ONE anchor data object (one object dodges the timeout).
#    Prefer a DMO (__dlm) when present; a DLO (__dll) or CIO (__dlc) also works.
python scripts/create_sdm.py \
  --api-name Workforce_SDM --label "Workforce SDM" \
  --data-object qb_hw_employee__dlm \
  --workspace HR_Workforce

# 3. RESOLVE the server-stored (suffixed) field apiNames — create_sdm.py prints
#    them, or re-read any time. NEVER guess a suffix; copy the exact stored name.
python scripts/discover_sdm.py --sdm Workforce_SDM --json

# 4. ADD a second data object incrementally (one per call).
python scripts/add_data_object.py --mode object \
  --sdm Workforce_SDM --data-object qb_hw_calendar__dlm
# (prints the new object's stored apiNames for the join key)

# 5. ADD the relationship using the RESOLVED apiNames as join keys.
python scripts/add_relationship.py \
  --sdm Workforce_SDM \
  --left-object qb_hw_employee --right-object qb_hw_calendar \
  --left-field join_12 --right-field join_13 \
  --label "Employee : Calendar"

# 6. VERIFY by querying across the join — a field from each object in one query.
#    Non-empty grouped rows prove the relationship authored (see api-reference).
python scripts/discover_sdm.py --sdm Workforce_SDM --json   # confirm relationship + isQueryable
```

### Data-object source suffixes

The `--data-object` source name **requires a type suffix** (bare names are
rejected with "DMO/CI/DLO does not exist"). The script infers `dataObjectType`
from it:

| Source type | suffix | `dataObjectType` | Example |
|---|---|---|---|
| Data Lake Object | `__dll` | `Dlo` | `accounts__dll` |
| Data Model Object | `__dlm` | `Dmo` | `qb_hw_employee__dlm` |
| Calculated Insight | `__dlc` | `Cio` | `churn_score__dlc` |

**Default: accept either DLO or DMO; prefer `__dlm` (DMO) in examples when a DMO
is present.** DMO/DLO *creation* is out of scope — build on what exists.

### Landmine 1 — apiName auto-suffixing (resolve, never guess)

With `shouldIncludeAllFields=true` (the default for `--mode object`), the server
**numerically suffixes every auto-bound apiName**, even with no name collision:
`first_name__c` → `first_name1`, `position_id__c` → `position_id2`,
`organization_id__c` → `organization_id2`. The suffix is **not predictable**.

- **Always resolve** the stored apiName (`discover_sdm.py --json`, or the
  apiNames the create/add scripts print) and use it verbatim as a join key.
- For a **controlled apiName** (clean naming, no suffix), bind one field by hand:
  ```bash
  python scripts/add_data_object.py --mode dimension \
    --sdm Workforce_SDM --object qb_hw_employee \
    --api-name Employee_Name --source-field last_name__c --data-type Text
  ```
  A single-field add **preserves the apiName verbatim**.

### Landmine 2 — bulk-create timeout (wait + list, never blind-retry)

Creating with **many** objects in one call can return a generic timeout/"Unexpected
error" even though the SDM **persists ~10–30s later**. A naive re-POST then hits
**"Unique constraint violated"**. `create_sdm.py` handles this: on a timeout it
**waits ~30s then lists** to confirm persistence — it does **not** re-POST. This
is why you create with a single anchor and add the rest one object per call.

### Landmine 3 — relationship rules (joinType=Auto, label required, resolved key)

Model-level relationships authored via REST and become queryable (proven live).
The rules `add_relationship.py` enforces:

- **`joinType` MUST be `Auto`** at the model level. `Left`/`Right`/`Inner`/`Full`
  are valid only inside a logical view (UI-only, out of scope).
- **`label` is REQUIRED** despite the schema marking it optional.
- **`cardinality`** defaults to **`ManyToOne`** (fact→dimension); also
  `OneToOne`/`OneToMany`/`ManyToMany`/`Unspecified`.
- **Join keys MUST be the resolved semantic apiNames**
  (`position_id2`), with `leftFieldType`/`rightFieldType="TableField"`. Using the
  raw `__c` source column (`position_id__c`) fails with **"field could not be
  found"** — the single most common relationship error. `add_relationship.py`
  rejects a `__c`-style key pre-POST and points you to the resolved apiName.

### Verify the join works

After adding a relationship, run a cross-object query (a field from **each**
object in one query). Non-empty grouped rows prove the join is traversed (an
unjoined cross-object query throws when `queryUnrelatedDataObjects: "Exception"`).
The cross-object query gateway and a worked example are in
[references/sdm-creation-api.md](references/sdm-creation-api.md) ("Proof the join
works"). `discover_sdm.py --json` also surfaces each relationship with its
`isQueryable` status.

## Discovery Workflow

Before creating fields or metrics, discover what already exists on the SDM:

```bash
python scripts/discover_sdm.py --list                          # all SDMs
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json       # full structure of one SDM
```

Two gates you **must** clear before authoring, both detailed in **[references/discovery.md](references/discovery.md)**:

1. **Data presence (field-richness is NOT data-presence).** An object with dozens of fields can still return zero rows. Confirm with `python scripts/query_data.py --count <Object>` or `lib.query.assert_has_rows()` — the latter **hard-blocks** a 0-row object. See also [references/empty-source-handling.md](references/empty-source-handling.md).
2. **Field-name syntax.** Table fields (`semanticMeasurements`/`semanticDimensions`) require **qualified** syntax `[Table].[Field]`; calculated fields (`_clc`) require **unqualified** `[Field]`. Server auto-suffixes on joins (`Amount` → `Amount1`), so always resolve from `discover_sdm.py --json`.

## Calculated Fields

Calculated fields add custom business logic to the semantic layer. They're reusable across visualizations and can be measurements (aggregated) or dimensions (categorical).

### Creating Calculated Measurements

Measurements are aggregated numeric fields (sum, average, count, etc.).

**Basic example:**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum
```

**Ratio example (win rate):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Won_Count]) / SUM([Opportunity_TAB_Sales_Cloud].[Total_Count])" \
  --aggregation UserAgg
```

**Why `UserAgg` for ratios:** The expression already includes aggregation functions (`SUM`). Using `Sum` or `Avg` would add another aggregation layer on top, producing incorrect results. `UserAgg` preserves the expression's aggregation logic.

### Creating Calculated Dimensions

Dimensions are categorical fields used for grouping and filtering.

**DATEPART returns numbers:** DATEPART and DATEDIFF return numeric values. For dimensions, wrap in STR() to convert to text. For measurements (to calculate averages or sums), use without STR() and specify aggregation type.

**Example (extracting month from date for grouping):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Close_Month_clc \
  --label "Close Month" \
  --expression "STR(DATEPART('month', [Opportunity_TAB_Sales_Cloud].[Close_Date]))"
```

**Example (conditional logic):**

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type dimension \
  --name Deal_Size_Category_clc \
  --label "Deal Size Category" \
  --expression "IF [Opportunity_TAB_Sales_Cloud].[Amount] > 100000 THEN 'Large' ELSEIF [Opportunity_TAB_Sales_Cloud].[Amount] > 50000 THEN 'Medium' ELSE 'Small' END"
```

### Aggregation Types + Common Expression Patterns

Full aggregation-type table (`Sum` / `Avg` / `UserAgg` / `Min` / `Max` / `Count`) and common expression patterns (time calcs, conditional aggregation, string manipulation, null handling) live in **[references/calc-field-patterns.md](references/calc-field-patterns.md)**. Complete function reference in [references/tableau-functions.md](references/tableau-functions.md). Production-derived ratio / LOD / weighted-calc / dimension patterns in [references/patterns.md](references/patterns.md).

**Critical:** Don't guess aggregation types. If uncertain, inspect the SDM first, or use `UserAgg` when your expression already includes aggregation functions.

## Semantic Metrics

Metrics are lightweight wrappers for Tableau Next dashboard KPI widgets. They reference existing calculated fields and include time dimension configuration.

### Creating a Basic Metric

**Prerequisite:** Create the calculated field first. Metrics reference calculated fields by API name, so the calc field must exist before the metric can be created.

```bash
# Step 1: Create calculated field
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum

# Step 2: Create metric referencing it
python scripts/create_metric.py \
  --sdm Sales_Cloud12_backward \
  --name Total_Revenue_mtc \
  --label "Total Revenue" \
  --calculated-field Total_Revenue_clc \
  --time-field Close_Date \
  --time-table Opportunity_TAB_Sales_Cloud
```

**Anchor the time dimension on a business event date — never a plumbing
column.** `--time-field` must be a business-meaningful date (`Close_Date`,
`Created_Date`, `Hire_Date`, `Order_Date`). **Reject** system/load columns:
`cdp_sys_*` (e.g. `cdp_sys_PartitionDate`, `cdp_sys_SourceVersion__c`),
`*_SourceVersion`, `KQ_*`, and load/ingest timestamps. Anchoring on one of these
produces a metric whose time series tracks the *data pipeline*, not the business
— a silent correctness bug. If the user names a plumbing column, suggest a real
event date instead. `create_metric.py` rejects a junk anchor unless
`--allow-junk-time-anchor` is passed. (Full negative list:
[references/metric-design.md](references/metric-design.md).)

### Metric with Additional Dimensions

Additional dimensions enable breakdown analysis (e.g., "Revenue by Region" or "Top contributors by Industry").

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

Format: `fieldApiName:tableApiName` (repeat `--additional-dimension` for multiple dimensions). When additional dimensions are provided, `insightsSettings` is auto-generated with enabled insight types (TopContributors, TrendChangeAlert, BottomContributors, etc.). Full metric payload fields (`timeGrains`, `isCumulative`, `sentiment`, etc.) + design patterns in **[references/metric-design.md](references/metric-design.md)**.

### A created metric/field is not "ready" until it returns data

**Creation success is not data success.** Empty results (empty source, filter excludes everything, expression resolves to nothing) → dashboard shows "No results to show." Check with `--verify-only`:

```bash
python scripts/create_metric.py --sdm <SDM> --name <Metric_mtc> --verify-only
python scripts/create_calc_field.py --sdm <SDM> --type measurement --name <Field_clc> --verify-only
```

Non-zero exit + **NOT shippable** = don't proceed to dashboards. Full protocol (why not to re-POST, `query_data.py --count` for raw objects, empty-source guidance) in **[references/concepts.md](references/concepts.md)** and [references/empty-source-handling.md](references/empty-source-handling.md).

## Make the SDM AI-Ready

A model humans can query is not automatically queryable by the **AI agent**. AI-readiness = flip `agentEnabled` on, add a structured `businessPreferences` context block, and set `description` + `categories`. This is a **model-level PATCH** via `update_sdm.py` — distinct from `_clc`/`_mtc` creation (untouched).

> `agentEnabled` = **expose-to-AI** (agent can query it). `isAiDrafted` = **provenance** (model was drafted by AI). Different fields — AI-ready sets `agentEnabled`, not `isAiDrafted`.

```bash
# Flip a model AI-ready: agentEnabled + businessPreferences + description
python scripts/update_sdm.py {{SDM_NAME}} \
  --agent-enabled \
  --description "Workforce model: headcount, hires, leavers by org and department." \
  --business-preferences-file ./business_preferences.txt

# Dry-run (print the PATCH payload, no network call)
python scripts/update_sdm.py {{SDM_NAME}} --agent-enabled --dry-run

# Confirm via discovery (stored state, not CLI success message)
python scripts/discover_sdm.py {{SDM_NAME}} --json
```

The update is a PATCH (partial body — server merges), idempotent. `--categories` takes controlled "Semantic Category" values only — the server rejects unknown values with `Invalid Semantic Category`.

### More: businessPreferences template + updating an existing metric or base field

The 6-heading `businessPreferences` template (PURPOSE / GRAIN & JOINS / KEY DEFINITIONS / SYNONYMS / DATA CAVEATS / PREFERRED MEASURES), the full-payload PUT commands for `update_metric.py` (identifying dimension, time comparisons, dry-run), and the full-payload PUT flow for `update_field.py` / `update_object.py` (base dimension / measurement / data-object descriptions — PATCH returns 405) all live in **[references/sdm-ai-readiness-api.md](references/sdm-ai-readiness-api.md)**.

## Validation

### Validate Expressions Before Creating Fields

Dry-run mode shows the payload without POSTing:

```bash
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Win_Rate_clc \
  --label "Win Rate" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Won]) / SUM([Opportunity_TAB_Sales_Cloud].[Total])" \
  --aggregation UserAgg \
  --dry-run
```

Review the JSON output to verify:
- Expression syntax is correct
- Field references exist in the SDM (check with `discover_sdm.py`)
- Aggregation type matches the expression
- API name follows conventions (`_clc`, no `__`)

### Supported Tableau Functions

Common categories — aggregation (`SUM`/`AVG`/`MIN`/`MAX`/`COUNT`/`COUNTD`), date (`DATEPART`/`DATEDIFF`/`DATEADD`/`NOW`/`TODAY`), string (`LEFT`/`RIGHT`/`MID`/`UPPER`/`LOWER`/`CONTAINS`/`SPLIT`), logic (`IF`/`CASE`/`IFNULL`/`ISNULL`/`ZN`), math (`ABS`/`ROUND`/`CEILING`/`FLOOR`/`POWER`/`SQRT`). Full list in **[references/tableau-functions.md](references/tableau-functions.md)**.

### Semantic query gotcha: `semantic_field`, not `calculated_field`

When referencing an existing SDM calc field (`_clc`) in a semantic query, use `semantic_field {name}` (REST: `semanticField`). `calculated_field {name}` is for on-the-fly formulas and expects an inline expression — pointing it at an existing name fails `INVALID_API_INPUT`. Detail in [references/sdm-ai-readiness-api.md](references/sdm-ai-readiness-api.md) §4.

## Script Cheat Sheet

Three most-used commands (full reference in **[references/scripts.md](references/scripts.md)**):

```bash
# Discover SDM structure (objects, fields, calc fields, metrics, relationships)
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json

# Create a calculated measurement
python scripts/create_calc_field.py --sdm {{SDM_NAME}} --type measurement \
  --name {{FIELD_NAME}}_clc --label "{{Display Label}}" \
  --expression "{{TABLEAU_FORMULA}}" --aggregation {{Sum|UserAgg|...}}

# Create a metric on top of a calc field
python scripts/create_metric.py --sdm {{SDM_NAME}} \
  --name {{METRIC_NAME}}_mtc --label "{{Display Label}}" \
  --calculated-field {{CALC_FIELD_NAME}}_clc \
  --time-field {{TIME_FIELD}} --time-table {{TABLE_NAME}}
```

All scripts support `--dry-run` (print payload, no network call). Scripts live under `scripts/`; shared modules in `scripts/_shared/`. Verify with `python scripts/_shared/verify_paths.py`.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `API name cannot contain double underscores` | Name includes `__` | Remove `__`: `Field__Name` → `Field_Name` |
| `API name must end with '_clc'` | Missing suffix | Add `_clc`: `Win_Rate` → `Win_Rate_clc` |
| `Invalid function 'SUMIF'` | Function not supported in Tableau | Use `SUM(IF ... THEN ... END)` instead |
| `Field 'Amount' not found` | Field doesn't exist in SDM | Run `discover_sdm.py` to verify field name |
| `Validation error: aggregationType required` | Missing `--aggregation` flag | Add `--aggregation Sum` (or appropriate type) |
| `measurementReference.calculatedFieldApiName not found` | Calc field doesn't exist yet | Create calc field first, then metric |
| `The field with API name (X__c) ... could not be found` (relationship) | Used the raw `__c` source column as a join key | Use the **resolved** semantic apiName (e.g. `position_id2`) from `discover_sdm.py --json`, not `__c` |
| `DMO/CI/DLO does not exist` | Data-object source name missing its type suffix | Add `__dlm` (DMO) / `__dll` (DLO) / `__dlc` (CIO) |
| `API Name ... must ... begin with a letter, not end with an underscore, and not contain two consecutive underscores` | Malformed SDM apiName | Fix the apiName (letter-led, no spaces/`__`/trailing `_`). The skill validates this pre-POST |
| `Unique constraint violated` (on create retry) | Blind-retried a create that actually persisted after a timeout | Don't re-POST — `discover_sdm.py --list` to confirm; `create_sdm.py` does this automatically |
| `401 Unauthorized` | Token expired | Refresh: `sf org auth show-access-token --target-org $SF_ORG` |

### AI-readiness gotchas (four landmines)

1. **`description` capped at 255 chars — measured on RAW input** (not the HTML-encoded stored value). `update_sdm.py` guards it — move depth into `businessPreferences` (no length limit).
2. **Metric update is a full-payload PUT** (not PATCH). Naive partial body drops `additionalDimensions` + `insightsSettings`. Use `update_metric.py` — it resolve-and-merges.
3. **`identifyingDimension` must be a member of `additionalDimensions`** or the TN UI crashes. `update_metric.py --identifying-dimension Field:Object` preserves it.
4. **Base-field / data-object descriptions update via full-payload PUT** (PATCH on the sub-resource → 405). Use `update_field.py` / `update_object.py` — both resolve-and-merge.

Full detail + payload contract in [references/sdm-ai-readiness-api.md](references/sdm-ai-readiness-api.md).

## Prerequisites

Salesforce CLI (`sf`), Python 3.8+ with `requests` (`pip install -r scripts/requirements.txt`), `jq` (`brew install jq` / `apt install jq`), and an authenticated org (`sf org login web --alias myorg`). Quick auth setup:

```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org auth show-access-token --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

Scripts automatically use these environment variables.

## API Endpoints

All REST endpoints (discovery, build-from-scratch, enrichment, AI-readiness/update) and the `Authorization: Bearer {token}` requirement live in **[references/api-reference.md](references/api-reference.md)**.

## Best Practices

- **Prefer `_clc` fields over raw fields** — centralize business logic even for simple formulas.
- **Use meaningful names** — `Win_Rate_clc`, `Total_Revenue_mtc`, not `Field_1_clc` / `Calc_Field_clc`.
- **Two-step for metrics** — create the calc field first (metric references it by API name).
- **Test fields before creating metrics** — verify with `discover_sdm.py`, spot-check in a viz.
- **Read aggregation types from the SDM** — don't guess; inspect similar existing measurements.

Long-form rationale + examples for each in **[references/best-practices.md](references/best-practices.md)**.

## Real-World Patterns

Metric design patterns, calculated-field patterns (ratios, LOD, weighted), dimension patterns, and industry-specific KPI templates learned from 25+ production dashboards live in **[references/patterns.md](references/patterns.md)**. Time-based aggregation, composite KPI formulas, and color semantics live in **[references/kpi-formulas.md](references/kpi-formulas.md)**.

## Next Steps

After enriching the semantic layer:
- **Create visualizations:** Build charts referencing your new calculated fields
- **Build dashboards:** Reference metrics in Tableau Next dashboard KPI widgets

---

## Reference Files

- [references/sdm-creation-api.md](references/sdm-creation-api.md) — Build an SDM from scratch: create/add-object/add-field/add-relationship endpoints + payloads, the suffixing + timeout + relationship landmines, and the cross-object query that proves a join
- [references/sdm-ai-readiness-api.md](references/sdm-ai-readiness-api.md) — Make an SDM AI-ready + update a metric: model-level PATCH allowlist, 255-char raw `description` cap, metric full-payload PUT contract, `semantic_field`-not-`calculated_field` verification note, `businessPreferences` template, update-metric/field/object commands
- [references/api-reference.md](references/api-reference.md) — Full REST API documentation + endpoint quick reference
- [references/concepts.md](references/concepts.md) — Base vs calc fields, calc-vs-metric, create-and-verify contract, "not ready until returns data" protocol
- [references/discovery.md](references/discovery.md) — Discovery deep dive: data-presence gate, field-name verification rules, common errors
- [references/calc-field-patterns.md](references/calc-field-patterns.md) — Aggregation-type table + common expression patterns (time, conditional, string, null)
- [references/metric-design.md](references/metric-design.md) — Metric design patterns, metric payload structure, auto-insightsSettings behavior
- [references/patterns.md](references/patterns.md) — Real-world patterns from 25+ production dashboards: metric design, calc field (ratios/LOD/weighted), dimensions, industry-specific KPIs
- [references/scripts.md](references/scripts.md) — Full command reference for every top-level script
- [references/best-practices.md](references/best-practices.md) — Long-form rationale + examples for each best-practice principle
- [references/tableau-functions.md](references/tableau-functions.md) — Complete Tableau function reference
- [references/field-types.md](references/field-types.md) — Measurements vs dimensions deep dive
- [references/kpi-formulas.md](references/kpi-formulas.md) — Time-based aggregation patterns, composite KPI formulas, color semantics, 40+ industry-specific KPI templates
- [references/empty-source-handling.md](references/empty-source-handling.md) — Empty-of-rows vs unmaterialized sources + user-facing wording
