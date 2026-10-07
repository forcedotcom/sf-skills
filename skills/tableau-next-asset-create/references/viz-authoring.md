# Visualization Authoring — Tool Guide & Best Practices

Load this for **Step 10** (create visualizations). Covers tool selection,
chart-type best practices mapped to the available MCP tools, field binding rules,
aggregation handling, naming conventions, and verified payloads.

**Best-practice principles** for dashboard design live in
`references/dashboard-design-principles.md`; this file maps the chart-level
mechanics to what the tools actually support. For chart types not currently
supported by the tools, see §9.

> **⚠ Single-tool surface (verified 2026-07-09):** The MCP server exposes one
> viz creation tool: `create_visualization`. The formerly-documented specialized
> tools (`create_timeseries_viz`, `create_comparative_viz`,
> `create_compositional_viz`, `create_relationship_viz`) are **not available**.
> All chart types are built via `create_visualization` with the appropriate
> `marks.panes.type` and `visualSpecification`. Payloads in §11 are verified
> against the live server.

---

## Contents

- 1. Data Presence Gate (prerequisite — hard stop)
- 2. Chart Type Parameters
- 3. Chart Type Decision Matrix
- 4. Naming Conventions
- 5. Field Selection Priorities
- 6. Color Encoding and Breakdown
- 7. Aggregation Handling
- 8. Year-over-Year Period Overlay Pattern
- 9. Unsupported Chart Types — Fallbacks
- §10 — Filter Security
- 10. Field Reference Shape (`create_visualization`)
- 11. Verified Payloads (`create_visualization`)
- 12. `create_visualization` Encoding Reference
- 13. Quality Checklist
- 14. Filters — WHERE vs. HAVING
- 15. Forecasts (Timeseries Only)
- 16. Calculated-Measure Level → Function Pairing
- 17. Reference Line Knob
- 18. Common Errors

---

## 1. Data Presence Gate (prerequisite — hard stop)

**Never create a visualization on a source with zero rows.**

This is Rule 1 from SKILL.md: field-richness is NOT data-presence. Before
calling any viz creation tool, confirm that Step 9 (`run_semantic_query`)
returned real rows. If the query returned empty → **STOP**. Do not call
`create_visualization`. Communicate clearly that the source is empty and offer
alternatives (different data source, different metric).

---

## 2. Chart Type Parameters

**One tool handles all chart types:** `create_visualization`. Control the
chart type via `marks.panes.type` and `visualSpecification.layout`:

| Chart Type / Pattern | `marks.panes.type` | `layout` | Notes |
|---|---|---|---|
| **Line / Time Series** | `Line` | `Vizql` | Date on columns with `DateTruncMonth`; measure on rows |
| **Multi-series Line** | `Line` | `Vizql` | As above + Color encoding on breakdown dimension |
| **Bar (comparative, sorted)** | `Bar` | `Vizql` | Dim on columns, measure on rows; set `sortIntent: "MeasureDescending"` |
| **Stacked Bar** | `Bar` | `Vizql` | As above + `stack: {isAutomatic: false, isStacked: true}` + Color on second dim |
| **Side-by-Side Bar** | `Bar` | `Vizql` | Dim on columns; `MeasureValues` on rows + `MeasureNames` on Color; see `measureValues` |
| **Donut / Pie** | `Donut` | `Radial` | Measure on **`Angle` encoding** (NOT `rows`); dimension on Color; use when dim has < 5 unique values |
| **Scatter / Correlation** | `Circle` | `Vizql` | X-measure on columns, Y-measure on rows; point dimension on Color |
| **Heatmap** | `Square` | `Vizql` | Two dims on rows/columns; measure on Color encoding |
| **Table** | `Text` | `Table` | Dims in `groups`; measures in `rows`; `marks.panes.type` is ignored |

> **Donut gotcha:** Set `layout: "Radial"`, empty `rows`/`columns`. The measure
> goes on the `Angle` encoding, the dimension on `Color` — NOT on `rows` or
> `columns`. If you put the measure on `rows` the call will fail or render
> incorrectly. See §11 for the verified payload.

---

## 3. Chart Type Decision Matrix

| Business Question | Data Pattern | Chart Type |
|---|---|---|
| "How are we trending over time?" | 1 Date + 1 Measure | Line |
| "How do trends compare across categories?" | 1 Date + 1 Measure + 1 Dimension | Multi-series Line |
| "Which categories perform best?" | 1 Dimension + 1 Measure | Bar (sorted descending) |
| "What's our composition?" (< 5 categories) | 1 Dimension (< 5 vals) + 1 Measure | Donut |
| "What's our composition?" (≥ 5 categories) | 1 Dimension (≥ 5 vals) + 1 Measure | Bar — more readable beyond 4 slices |
| "What's the breakdown by two dimensions?" | 2 Dimensions + 1 Measure | Stacked Bar |
| "How do multiple measures compare?" | 1 Dimension + 2+ Measures | Side-by-Side Bar |
| "Where are the performance hotspots?" | 2 Dimensions + 1 Measure | Heatmap |
| "What correlates with success?" | 2 Continuous Measures + Grouping | Scatter |
| "What are the detailed rankings?" | Multiple Dimensions + Measures | Table |
| "How do 2024 vs 2023 compare month by month?" | Period + Measure + Year | Line (year-over-year — see §8) |
| "Predict next quarter revenue" | 1 Continuous date + 1 Measure | Line + `visualSpecification.forecasts` (HoltWinters / RidgeRegression) |

**Priority rules:**
1. Use the decision matrix first: data pattern → tool
2. When multiple patterns fit, prefer the tool that requires fewer manual
   encoding overrides
3. Prefer diverse chart types over defaulting to bar for every request

**Analysis-intent → chart (do this before picking marks):**

| User intent (example) | Analysis type | Tool guidance | §reference |
|---|---|---|---|
| "revenue over time" | trend | Line (date on columns) | §11 Time Series |
| "top categories by sales" | comparison | Bar (dim on columns, sorted) | §11 Bar |
| "market-share breakdown" | part-to-whole | Donut (< 5 vals) or Bar (≥ 5) | §11 Donut |
| "discount vs profit relationship" | correlation | Scatter (2 measures, 1 color dim) | §11 Scatter |
| "predict next quarter revenue" | forecast | Line + `forecasts` map (timeseries only) | §11 Time Series (forecast) |

**Forecast** is supported on timeseries **Line** charts via
`visualSpecification.forecasts` (API 262+): continuous `DateTrunc*` date on the
axis, measure to forecast, `HoltWinters` or `RidgeRegression`, horizon under
`to.forecastInterval`. Non-Line / non-timeseries forecasts fail with
`INVALID_INPUT`.

---

## 4. Naming Conventions

Chart titles are **user-facing**. Every chart must answer a business question
and have a clear, non-technical title (use SDM labels over technical names;
strip suffixes).

**Rules:**
1. Title must be ≥ 3 words describing what the chart answers.
2. Strip technical suffixes from display labels: `_Clc`, `_mtc`, `_MTC`, `_CLC`.
3. Never expose raw field API names or suffixed names (`Region4`, `Amount7`).
4. Make titles actionable: "Sales Performance by Region" not "Sales by Region".
5. The `name` (apiName) returned by the tool must be meaningful if you control
   it (e.g. specify `title`); the generated name (`monthly_sales_trend_…`) is
   acceptable for dashboard placement but label the chart clearly.

✅ **Good:** `"Sales Performance by Region"`, `"Monthly Revenue Trend"`,
`"Discount vs Profit by Product"`

❌ **Bad:** `"Viz_1"`, `"Account_Industry_2"`, `"Pipeline_Generation_Clc_Trend"`,
`"Chart"`, `"Region4 by Amount7"`

---

## 5. Field Selection Priorities

**Always select meaningful dimensions — never ID fields.** CLC fields rank
highest (calculated, business-ready); ID fields are excluded (thousands of
unique values destroy chart readability).

Priority order (highest to lowest):
1. **CLC fields** (`*_clc`, `*_Clc`) — calculated, business-ready
2. Industry, Type, Stage, Status, Region, Segment, Category, Group, Class, Tier,
   Level, Phase
3. Country, State, Territory, Department, Division, Account, Opportunity,
   Product, Service
4. Name fields (Account_Name, Product_Name, etc.)
5. **Avoid:** Description, Comment, Note, Detail, Text (generic catch-all fields)
6. **Never:** ID fields (`_id`, `_ids` suffix) — thousands of unique values;
   destroys chart readability

**Cardinality thresholds:**
- ≤ 4 unique values → Donut acceptable
- 5–50 values → Bar chart preferred dimension
- 50+ values → Apply a Top-N limit, or group to a higher-level category
  (e.g., use `Category` instead of `Product_Name` with 200 values)

---

## 6. Color Encoding and Breakdown

**Color encodes meaning, not decoration.** When a second dimension is available,
always add it as a `breakdown` or Color encoding — this creates multi-series or
stacked visuals automatically.

| Chart type | How to add a color / second dimension |
|---|---|
| **All chart types** | `{ "type": "Color", "fieldKey": "<dim_field_key>" }` in `marks.panes.encodings` |
| **YoY line** | Color fieldKey = date field with `function: "DatePartYear"`, `displayCategory: "Discrete"` |
| **Stacked bar** | Color fieldKey = second dimension; also set `stack: { isAutomatic: false, isStacked: true }` |
| **Donut** | Color fieldKey = the category dimension (same field as Angle slice) |

**Rule:** When 2+ dimensions are available for a bar or line chart, add the
second dimension as a breakdown/Color encoding. Color should reference a
specific field, not be a static palette applied without data binding.

**Color vs. Detail by cardinality.** Use `Color` for series with ≤10 distinct
values, `Detail` for higher cardinality.

**Default stacking:** Bar → stacked, others → not stacked. Override with
`marks.panes.stack: { isAutomatic: false, isStacked: <bool> }`.

**Cross-chart color coordination** (same category = same color across multiple
charts) is a dashboard-level concern, not a per-chart rule.

---

## 7. Aggregation Handling

### UserAgg for CLC / Calculated Fields

CLC fields (e.g., `Win_Rate_Clc`, `Avg_Deal_Size_Clc`) contain expressions like
`SUM([Field]) / COUNT([Field])` that aggregate at their own level.
**Never override UserAgg with Sum, Average, or any other function.**

```jsonc
"fields": {
  "F_clc": { "fieldName": "Win_Rate_Clc", "function": "UserAgg", "displayCategory": "Continuous" }
  // objectName omitted — calc measures never carry objectName
}
```

Overriding with `Sum` or `Average` causes double-aggregation → mathematically
incorrect results (e.g., `SUM(Average_Deal_Size)` is meaningless).

### Aggregation Selection by Analytical Question

| Question | Aggregation |
|---|---|
| "Total revenue / sum" | `Sum` |
| "Average deal size / mean" | `Avg` |
| "Number of records / count" | `Count` |
| "Unique customer count" | `CountD` |
| "Calculated rate / ratio (CLC field)" | `UserAgg` |
| "Highest / lowest value" | `Max` / `Min` |

### Pre-Aggregated Field Handling

Fields identified as pre-aggregated (marked `[AGG]` or using `usr:` derivation
in the semantic model) must not be re-aggregated. Set `function: "UserAgg"` on
the field's entry in the `fields` map and pass the field directly — the
aggregation is already embedded in the field expression.

---

## 8. Year-over-Year Period Overlay Pattern

**Always use period overlay, NOT a continuous date timeline, for YoY comparison.**

| Approach | X-axis | Color | Result |
|---|---|---|---|
| ✅ Period overlay (correct) | Month/Quarter (`DatePartMonth`) | Year dimension | Multiple aligned lines; seasonal patterns obvious |
| ❌ Continuous timeline (wrong) | Full date range (Jan 2023–Dec 2024) | — | Hard to compare same period across years |

**Why period overlay works:** Each year's January lands on the same X position
(month 1), making the same-period comparison direct and vertical rather than
requiring horizontal eye movement across a 2-year timeline.

**Implementation with `create_visualization`:**

Two date fields from the same date column — one with `DatePartMonth` (X-axis)
and one with `DatePartYear` (Color). No calculated dimension is needed; the
date part functions split the field into the two analytical roles inline:

```jsonc
{
  "workspaceId": "1Dy…", "workspaceName": "my_workspace",
  "semanticModelName": "My_SDM", "semanticModelLabel": "My SDM",
  "fields": {
    "F_month": {
      "objectName": "Orders", "fieldName": "Order_Date",
      "function": "DatePartMonth", "displayCategory": "Discrete",
      "label": "Month"
    },
    "F_year": {
      "objectName": "Orders", "fieldName": "Order_Date",
      "function": "DatePartYear", "displayCategory": "Discrete",
      "label": "Year"
    },
    "F_meas": {
      "objectName": "Orders", "fieldName": "Sales",
      "function": "Sum", "displayCategory": "Continuous",
      "numberFormat": "Currency"
    }
  },
  "visualSpecification": {
    "rows": ["F_meas"],
    "columns": ["F_month"],
    "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Line",
        "encodings": [{ "fieldKey": "F_year", "type": "Color" }]
      }
    }
  },
  "title": "Monthly Sales: Year-over-Year Comparison"
}
```

The `DatePartYear` Color encoding creates one line per year, all sharing the
same 12-month X-axis.

---

## 9. Unsupported Chart Types — Fallbacks

The following types appear in the universal visualization best practices guide
but are **not supported by the current MCP tools**. Use the recommended
fallback and communicate the limitation to the user:

| Unsupported Type | Reason | Recommended Fallback |
|---|---|---|
| **Funnel Chart** | No funnel tool | `create_visualization (Bar marks)`, sorted by stage order; communicate each stage's count |
| **Dot Matrix** | No dot matrix tool | `create_visualization (Circle marks)` for 2 measures, or `create_visualization (Bar marks)` for ranking |
| **Map (Point / Geographic)** | No map tool; lat/lon not routed | `create_visualization (Bar marks)` by Region or Territory dimension |
| **Flow / Sankey** | No flow tool | `create_visualization (Bar marks)` showing source → destination volumes as two separate charts |
| **Nightingale Rose** | Radial layout supports Donut marks only | `create_visualization (Bar marks)` (horizontal bar) |
| **Spoke Bars (Radial)** | Not available in current tools | `create_visualization (Bar marks)` |
| **Radial Heatmap** | Not available | `create_visualization` Square-mark heatmap (2D grid) |

**When the user explicitly requests an unsupported type:** say so clearly —
"This chart type is not currently available. I'll use [fallback] instead, which
answers the same question with [benefit]." Do not silently substitute without
explaining.

**Note:** Funnel, Dot Matrix, Map, Flow/Sankey, Nightingale Rose, and Spoke Bar
chart types cannot be verified via MCP tool call trace with the current toolset.
Validate the fallback communication behavior for these instead.

---

## §10 — Filter Security

### Hidden Filters Are Not a Security Control

When a user asks to hide a filter, lock a filter to a specific value, or restrict
which data users see by hiding a filter dimension, issue this warning before
proceeding:

> **Warning:** Hidden filters in dashboards are not a security control. Any user
> with direct API or URL access to the underlying data source can bypass a hidden
> filter and retrieve the full dataset. Do not rely on hidden filters to enforce
> data access restrictions or row-level security.
>
> **Recommendation:** For genuine data access restrictions, implement row-level
> security at the data source level (e.g., data source permissions,
> entitlement-based filtering in the semantic model). Hidden filters are
> appropriate only for UI/UX convenience (e.g., pre-selecting a default value
> the user can still change).

This warning applies when the user's intent is access restriction — not when they
simply want a pre-set default filter value that the end user can still override.
This applies regardless of whether the user says the restriction is "just for
convenience."

---

## 10. Field Reference Shape (`create_visualization`)

`create_visualization` uses a **`fields` map + `visualSpecification`** format —
NOT the `fieldRef` / `measureFunction` shape from older specialized tools.

```jsonc
"fields": {
  "<fieldKey>": {
    "objectName": "<SDM data-object apiName>",  // OMIT for model-level calc measures
    "fieldName":  "<field apiName on that object>",
    "displayCategory": "Discrete | Continuous",
    "function":   "<aggregation or date function>",  // optional
    "level":      "Row | AggregateFunction | TableCalc | Lod",  // required when calc + function
    "label":      "<display label override>",        // optional
    "numberFormat": "Currency | Percent | Abbreviated | Precise",  // optional, measures only
    "referenceLine": "Average | Sum | Min | Max | Target",         // optional, measures only — see §17
    "referenceLineValue": 1000000,                                 // required iff referenceLine=Target
    "colorScale":  "Diverging"                                     // optional, Color-encoded measure — see §11 Heatmap
  }
}
```

**Server hydrates the rest — do NOT send these unless overriding:** `type:
"Field"` (auto-filled) and the field's inferred `role` (Measure when any
aggregation `function` is set, else Dimension); and at the spec level
`marks.headers` (default Text mark), `marks.fields` (one per continuous-axis
fieldKey on rows/columns), `legends` (auto-derived from Color encodings),
`referenceLines` (`{}`), `measureValues` (`[]`), `style` (full default
scaffold), `view` (empty), and `interactions` (`[]`).

**Critical rules:**
- `workspaceId` — workspace Id (e.g. `0Za...`). Get from `list_workspaces`
  (`id` field). `workspaceName` — workspace API name (no spaces). Get from
  `list_workspaces` (`name` field). **Do NOT pass the label-with-spaces.**
- `objectName` is the **SDM data-object apiName** (e.g., `Orders`, `Products`),
  NOT the underlying DLO/DMO table name (`orders__dll`, `Orders__dlm`).
- `fieldName` is the field's apiName on that SDM object — use the **suffixed**
  apiName for bulk-imported fields (e.g., `Category3` not `Category`; see
  `shared-gates.md` G3 / `sdm-tool-reference.md` for the suffix read-back rule).
- **Calculated measures: omit `objectName`** entirely. Including `objectName`
  for a calculated measure causes an `UNKNOWN_EXCEPTION`. When supplying
  `function` on a calc, also set `level` from
  `list_semantic_model_calculated_measures` (`UserAgg` only for
  `AggregateFunction` / `TableCalc`).
- `displayCategory: "Continuous"` → measures and `DateTrunc*` date functions.
- `displayCategory: "Discrete"` → plain dimensions and `DatePart*` date functions.
- FieldKeys you define in `fields` must **exactly match** the strings used in
  `visualSpecification.rows`, `columns`, and encoding `fieldKey` values
  (these are the generate-viz field pointers).
- The tool returns the saved visualization's identifying triple (`id`, `label`,
  `name`). **Capture `id` and `name`** for `edit_dashboard`'s
  `upsert_visualization_widget`.
  To inspect the full hydrated body (style, legends, marks.fields), GET the
  visualization by id with `get_visualization`.

**`function` values:**
- Aggregations: `Sum`, `Avg`, `Median`, `Count`, `CountD`, `Min`, `Max`,
  `UserAgg` (`UserAgg` only for model-level calc measures at
  `AggregateFunction` / `TableCalc`)
- Continuous date trunc: `DateTruncYear`, `DateTruncQuarter`, `DateTruncMonth`,
  `DateTruncWeek`, `DateTruncDay` (plus `FiscalDateTrunc*` variants)
- Discrete date part: `DatePartYear`, `DatePartQuarter`, `DatePartMonth`,
  `DatePartWeek`, `DatePartDay`
- Fiscal-calendar variants (anchored to the org's fiscal year, no `Day`
  granularity): `FiscalDateTruncYear/Quarter/Month/Week` (Continuous),
  `FiscalDatePartYear/Quarter/Month/Week` (Discrete) — use only when the
  request says "fiscal" explicitly; "this quarter" ≠ "this fiscal quarter".
- Plain dimensions: omit `function`

---

## 11. Verified Payloads (`create_visualization`)

All calls share: `workspaceId`, `workspaceName`, `semanticModelName`, `semanticModelLabel`, `label` (the viz display title).

### Time Series (Line chart)

```jsonc
{
  "workspaceId": "1Dy…", "workspaceName": "my_workspace",
  "semanticModelName": "My_SDM", "semanticModelLabel": "My SDM",
  "label": "Monthly Sales Trend",
  "fields": {
    "F_date": {
      "objectName": "Orders", "fieldName": "Order_Date",
      "function": "DateTruncMonth", "displayCategory": "Continuous"
    },
    "F_meas": {
      "objectName": "Orders", "fieldName": "Sales",
      "function": "Sum", "displayCategory": "Continuous",
      "numberFormat": "Currency"
    }
  },
  "visualSpecification": {
    "rows": ["F_meas"],
    "columns": ["F_date"],
    "layout": "Vizql",
    "marks": { "panes": { "type": "Line" } }
  }
}
```

With multi-series breakdown (Color = second dimension):
```jsonc
{
  "fields": {
    "F_date": { "objectName": "Orders", "fieldName": "Order_Date", "function": "DateTruncMonth", "displayCategory": "Continuous" },
    "F_meas": { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" },
    "F_dim":  { "objectName": "Orders", "fieldName": "Region", "displayCategory": "Discrete" }
  },
  "visualSpecification": {
    "rows": ["F_meas"], "columns": ["F_date"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Line",
        "encodings": [{ "fieldKey": "F_dim", "type": "Color" }]
      }
    }
  },
  "label": "Monthly Sales Trend by Region"
}
```

With year-over-year period overlay:
```jsonc
{
  "fields": {
    "F_month": { "objectName": "Orders", "fieldName": "Order_Date", "function": "DatePartMonth", "displayCategory": "Discrete", "label": "Month" },
    "F_year":  { "objectName": "Orders", "fieldName": "Order_Date", "function": "DatePartYear",  "displayCategory": "Discrete", "label": "Year" },
    "F_meas":  { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous", "numberFormat": "Currency" }
  },
  "visualSpecification": {
    "rows": ["F_meas"], "columns": ["F_month"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Line",
        "encodings": [{ "fieldKey": "F_year", "type": "Color" }]
      }
    }
  },
  "label": "Monthly Sales: Year-over-Year Comparison"
}
```

With forecast (HoltWinters, 6-month horizon) — fieldKeys are pointers into
`fields`; both `dateDim.fieldKey` and `measureFieldKey` must match:
```jsonc
{
  "label": "Sales Forecast — Next 6 Months",
  "fields": {
    "F_date": {
      "objectName": "Orders", "fieldName": "Order_Date",
      "function": "DateTruncMonth", "displayCategory": "Continuous"
    },
    "F_meas": {
      "objectName": "Orders", "fieldName": "Sales",
      "function": "Sum", "displayCategory": "Continuous",
      "numberFormat": "Currency"
    }
  },
  "visualSpecification": {
    "rows": ["F_meas"],
    "columns": ["F_date"],
    "layout": "Vizql",
    "marks": { "panes": { "type": "Line" } },
    "forecasts": {
      "FC1": {
        "forecastModel": "HoltWinters",
        "dimensionFields": [
          { "dateDim": { "fieldKey": "F_date", "granularity": "InferFromData" } }
        ],
        "measureFieldKey": "F_meas",
        "from": { "predefinedDate": "LatestData" },
        "to": { "forecastInterval": { "value": 6, "timeUnit": "Months" } },
        "includeBounds": true,
        "confidenceLevel": 95
      }
    }
  }
}
```

---

### Bar / Comparative (sorted descending)

```jsonc
{
  "label": "Top Products by Revenue",
  "fields": {
    "F_dim":  { "objectName": "Products", "fieldName": "Product_Name", "displayCategory": "Discrete" },
    "F_meas": { "objectName": "Orders",   "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous", "numberFormat": "Currency" }
  },
  "visualSpecification": {
    "rows": ["F_meas"], "columns": ["F_dim"], "layout": "Vizql",
    "marks": { "panes": { "type": "Bar" } }
  },
  "sortIntent": "MeasureDescending"
}
```

With Color on a second dimension (auto-adds color encoding):
```jsonc
{
  "label": "Revenue by Region and Category",
  "fields": {
    "F_dim1": { "objectName": "Orders",   "fieldName": "Region",    "displayCategory": "Discrete" },
    "F_dim2": { "objectName": "Products", "fieldName": "Category3", "displayCategory": "Discrete" },
    "F_meas": { "objectName": "Orders",   "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_meas"], "columns": ["F_dim1"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Bar",
        "encodings": [{ "fieldKey": "F_dim2", "type": "Color" }]
      }
    }
  },
  "sortIntent": "MeasureDescending"
}
```

With a CLC calculated measure (omit `objectName`):
```jsonc
{
  "label": "Win Rate by Stage",
  "fields": {
    "F_clc": { "fieldName": "Win_Rate_Clc", "function": "UserAgg", "displayCategory": "Continuous" },
    "F_dim": { "objectName": "Opportunities", "fieldName": "Stage8", "displayCategory": "Discrete" }
  },
  "visualSpecification": {
    "rows": ["F_clc"], "columns": ["F_dim"], "layout": "Vizql",
    "marks": { "panes": { "type": "Bar" } }
  },
  "sortIntent": "MeasureDescending"
}
```

---

### Stacked Bar (2 dimensions + 1 measure)

```jsonc
{
  "label": "Revenue by Region and Category",
  "fields": {
    "F_dim1": { "objectName": "Orders",   "fieldName": "Region",    "displayCategory": "Discrete" },
    "F_dim2": { "objectName": "Products", "fieldName": "Category3", "displayCategory": "Discrete" },
    "F_meas": { "objectName": "Orders",   "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_meas"], "columns": ["F_dim1"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Bar",
        "encodings": [{ "fieldKey": "F_dim2", "type": "Color" }],
        "stack": { "isAutomatic": false, "isStacked": true }
      }
    }
  },
  "sortIntent": "MeasureDescending"
}
```

---

### Side-by-Side Bar (1 dimension + 2+ measures)

Uses `MeasureNames` / `MeasureValues` synthetic fields. Put `MeasureValues` on
rows, `MeasureNames` on Color. List the real measure fieldKeys in `measureValues`.

> **Required:** `displayCategory` is **not optional** for synthetic fields.
> Omitting it causes an `UNKNOWN_EXCEPTION` (HTTP 500). Always set:
> - `MeasureNames` → `"displayCategory": "Discrete"`
> - `MeasureValues` → `"displayCategory": "Continuous"`

```jsonc
{
  "label": "Revenue and Units by Region",
  "fields": {
    "F_dim":  { "objectName": "Orders", "fieldName": "Region", "displayCategory": "Discrete" },
    "F_mv":   { "type": "MeasureValues", "displayCategory": "Continuous" },
    "F_mn":   { "type": "MeasureNames",  "displayCategory": "Discrete" },
    "F_rev":  { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous", "numberFormat": "Currency" },
    "F_units":{ "objectName": "Orders", "fieldName": "Quantity", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_mv"], "columns": ["F_dim"], "layout": "Vizql",
    "measureValues": ["F_rev", "F_units"],
    "marks": {
      "panes": {
        "type": "Bar",
        "encodings": [{ "fieldKey": "F_mn", "type": "Color" }]
      }
    }
  }
}
```

---

### Multi-Measure (direct shelf listing — separate adjacent axes)

The simpler multi-measure form: just list two (or more) measure fieldKeys on
one shelf — no `MeasureNames`/`MeasureValues` needed. This renders the measures
as **separate adjacent axes** (distinct from the shared-axis Side-by-Side Bar
above, which pivots them onto one axis via the measure-names construct). Works
for Bar and Line.

Multi-measure bar (both measures in `columns`):
```jsonc
{
  "label": "Sales and Profit by Category",
  "fields": {
    "F_dim":   { "objectName": "Orders", "fieldName": "Category", "displayCategory": "Discrete" },
    "F_sales": { "objectName": "Orders", "fieldName": "Sales",  "function": "Sum", "displayCategory": "Continuous" },
    "F_profit":{ "objectName": "Orders", "fieldName": "Profit", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_dim"], "columns": ["F_sales", "F_profit"], "layout": "Vizql",
    "marks": { "panes": { "type": "Bar" } }
  }
}
```

Multi-measure line (two lines sharing the date axis — both measures in `columns`):
```jsonc
{
  "label": "Sales and Profit over Time",
  "fields": {
    "F_date":  { "objectName": "Orders", "fieldName": "Order_Date", "function": "DateTruncMonth", "displayCategory": "Continuous" },
    "F_sales": { "objectName": "Orders", "fieldName": "Sales",  "function": "Sum", "displayCategory": "Continuous" },
    "F_profit":{ "objectName": "Orders", "fieldName": "Profit", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_date"], "columns": ["F_sales", "F_profit"], "layout": "Vizql",
    "marks": { "panes": { "type": "Line" } }
  }
}
```

Prefer this direct form for a quick side-by-side of a few measures; use the
`MeasureNames`/`MeasureValues` Side-by-Side Bar above when the measures should
share a single axis.

---

### Donut / Compositional (Radial layout)

> **Gotcha:** Set `layout: "Radial"`, empty `rows`/`columns`. Place the measure
> on the **`Angle` encoding**, NOT on `rows`. Putting a measure on `rows` with
> Radial layout causes the call to fail or render incorrectly. Verified working
> shape:

```jsonc
{
  "label": "Revenue Distribution by Region",
  "fields": {
    "F_meas": { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" },
    "F_dim":  { "objectName": "Orders", "fieldName": "Region", "displayCategory": "Discrete" }
  },
  "visualSpecification": {
    "layout": "Radial",
    "rows": [],
    "columns": [],
    "marks": {
      "panes": {
        "type": "Donut",
        "encodings": [
          { "fieldKey": "F_meas", "type": "Angle" },
          { "fieldKey": "F_dim",  "type": "Color" }
        ]
      }
    }
  }
}
```

Use when dimension has **< 5 unique values**. For ≥ 5 values, use a Bar chart —
donut slices become unreadable beyond 4.

#### Part-to-whole / Donut — field-binding gotchas (`create_visualization`)

The Donut payload above is the current unified `create_visualization` shape
(`type: "Donut"`, `layout: "Radial"`). Older scripts may still name the retired
`create_compositional_viz` tool — that tool is **not** on the pilot MCP; always
use `create_visualization`.

**`objectName` / `level` for measures (matches generate-viz / IR-v2):**

- **Raw measure** (from `list_semantic_model_measures`): supply BOTH
  `objectName` (SDM data-object apiName) and `fieldName`.
  ```jsonc
  "F_meas": { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" }
  ```
- **Model-level calculated measure** (from
  `list_semantic_model_calculated_measures`): supply ONLY `fieldName` — **omit
  `objectName`**. Including `objectName` yields `UNKNOWN_EXCEPTION`. Copy the
  calc's `level` from the list call whenever you set `function`:
  - `AggregateFunction` / `TableCalc` → `function: "UserAgg"`
  - `Row` / `Lod` → ordinary agg (`Avg` for Average, `CountD` for CountDistinct);
    do **not** use `UserAgg`
  ```jsonc
  "F_meas": { "fieldName": "Profit_Margin", "level": "AggregateFunction", "function": "UserAgg", "displayCategory": "Continuous" }
  ```

**FieldKeys are pointers:** every `rows` / `columns` / encoding `fieldKey` must
exactly match a key in the `fields` map — mismatches return
`INVALID_VISUALIZATION_METADATA`.

Validate dimensions/measures via `list_semantic_model_*` **before** calling
`create_visualization`. Donut is donut-only (no pie / treemap); for ≥ 5 unique
dimension values prefer §11 Bar.

---

### Scatter / Correlation (Circle marks)

```jsonc
{
  "label": "Discount vs Profit by Product",
  "fields": {
    "F_x":   { "objectName": "Orders",   "fieldName": "Discount", "function": "Avg", "displayCategory": "Continuous" },
    "F_y":   { "objectName": "Orders",   "fieldName": "Profit",   "function": "Sum", "displayCategory": "Continuous" },
    "F_dim": { "objectName": "Products", "fieldName": "Product_Name", "displayCategory": "Discrete" }
  },
  "visualSpecification": {
    "rows": ["F_y"], "columns": ["F_x"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Circle",
        "encodings": [{ "fieldKey": "F_dim", "type": "Color" }]
      }
    }
  }
}
```

---

### Heatmap (Square marks + Color(measure))

```jsonc
{
  "label": "Sales Performance by Region and Quarter",
  "fields": {
    "F_dim1": { "objectName": "Orders", "fieldName": "Region",   "displayCategory": "Discrete" },
    "F_dim2": { "objectName": "Orders", "fieldName": "Quarter3", "displayCategory": "Discrete" },
    "F_meas": { "objectName": "Orders", "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "rows": ["F_dim1"], "columns": ["F_dim2"], "layout": "Vizql",
    "marks": {
      "panes": {
        "type": "Square",
        "encodings": [{ "fieldKey": "F_meas", "type": "Color" }]
      }
    }
  }
}
```

For diverging color scales (values above/below a threshold), add
`"colorScale": "Diverging"` to the measure's field binding — only for a measure
genuinely centered on zero/a target (profit, variance, YoY change); on
all-positive data a diverging scale misleads.

---

### Table

Use `groups` for the categorical grouping column(s) and `rows` for measures
(API version 262+). The `groups`/`rows` split is the recommended form — it
gives the grouping column merged-cell styling. Putting a dimension directly in
`rows` (alongside measures) also works and renders as a plain Text column;
prefer `groups` for the leftmost grouping dimension for cleaner output.
Every field renders as a discrete text column (`marks.panes.type` is ignored).

```jsonc
{
  "label": "Top Products by Revenue",
  "fields": {
    "F_dim":  { "objectName": "Products", "fieldName": "Product_Name", "displayCategory": "Discrete" },
    "F_meas": { "objectName": "Orders",   "fieldName": "Sales", "function": "Sum", "displayCategory": "Continuous" }
  },
  "visualSpecification": {
    "groups": ["F_dim"],
    "rows": ["F_meas"],
    "layout": "Table",
    "marks": { "panes": { "type": "Text" } }
  },
  "sortIntent": "MeasureDescending"
}
```

Sort the primary measure descending via `sortIntent: "MeasureDescending"` or by
pre-sorting the data query via `run_semantic_query` with `sort_orders: DESC`.
`sortIntent` is an input-only convenience field: the server does not persist it
verbatim — it is translated into an explicit `sortOrders` entry on the
dimension field (`{ byField: <measure>, order: "Descending", type: "Field" }`),
so `get_visualization` will show `sortOrders`, not `sortIntent`.

Top-level `sortIntent` values: `MeasureDescending` | `MeasureAscending` |
`DimensionAscending` | `DimensionDescending` | `None`. Use `DimensionAscending`
for lookup tables (A→Z is the point) and `None` to preserve data order — it
overrides the auto-sort described below.

---

## 12. `create_visualization` Encoding Reference

| Encoding type | Valid mark types | Purpose |
|---|---|---|
| `Color` | Bar, Line, Circle, Square, Donut | Category or measure heat gradient |
| `Label` | All | Text labels on marks |
| `Tooltip` | All | Hover detail |
| `Detail` | Bar, Line, Circle, Square | High-cardinality grouping without color |
| `Size` | Circle | Bubble size mapping (third measure) |
| `Range` | Line | Confidence interval band |
| `Angle` | Donut | Slice sizing (Radial layout) |

**`displayCategory` for field bindings:**
- `"Continuous"` → measures and `DateTrunc*` date functions
- `"Discrete"` → plain dimensions and `DatePart*` date functions

**Number formatting options:**
- `Currency` → `"$1.2M"` (assumes USD)
- `Percent` → `"45.2%"` (expects values stored as 0–1; do NOT use on a value
  stored as `45.2`)
- `Abbreviated` → `"1.2K"` / `"1.2M"` (default for large numbers)
- `Precise` → `"1,234,567"` (full digits)

By default (no `numberFormat` set) the server applies `NumberShort` with K/M/B
units at **1 decimal place** — **0 decimals for `Count`/`CountD`** — so axes read
`$1.2M`-style, not `1234567.89`.

**Auto-sort only fires for the single-dim + single-measure case.** A bar chart
with exactly one categorical (non-date) dimension and one measure is sorted by
the measure descending automatically ("unsorted bars are nearly useless"). Date
axes stay chronological regardless. Charts with 2+ shelf dimensions or 2+
measures are left unsorted — the sort key is ambiguous — so use `sortIntent`
explicitly for those.

---

## 13. Quality Checklist

Before submitting any viz creation call:

- [ ] Step 9 confirmed real data (non-empty source) before calling `create_visualization`
- [ ] Title is ≥ 3 words, business-friendly, no raw API names or technical suffixes
- [ ] `fields.<key>.fieldName` uses the **suffixed** apiName from Step 5 (if bulk-imported)
- [ ] `objectName` is **omitted** for calculated measures
- [ ] `function: "UserAgg"` for CLC / calculated fields — not overridden
- [ ] Second dimension added as `breakdown` or Color encoding when available
- [ ] `MeasureNames` synthetic field has `displayCategory: "Discrete"` and `MeasureValues` has `displayCategory: "Continuous"` — both are required; omitting either causes HTTP 500
- [ ] Donut (Radial layout) only for dimension cardinality < 5; measure on `Angle` encoding, NOT `rows`
- [ ] Year-over-year uses `DatePartMonth` + Year breakdown, NOT continuous timeline
- [ ] Unsupported chart type → fallback communicated clearly to user
- [ ] Chart type matches the business question (decision matrix applied)

---

## 14. Filters — WHERE vs. HAVING

`create_visualization`'s optional `filters` array persists filter clauses at
create time (distinct from `edit_visualization`'s `addFilter` op —
`edit-visualization.md` — which mutates an already-saved viz). You don't
choose the bucket; it's derived from the target field's role:

- Filter on a **raw field** (no aggregation `function`) → rows/WHERE —
  `Processing_Fee between 0 and 21`.
- Filter on an **aggregated measure** (field carries `Sum`/`Avg`/`Count`/…) →
  aggregated groups/HAVING — `SUM(Refund_Amount) between 100 and 500`.

Shape: `{fieldKey, type: "Dimension"|"ValueRange"|"DateRange", ...}`.
Dimension filters take exactly one of `include`/`exclude` (never both/neither)
plus optional `includeNulls` (default false; ignored on range filters, which
always exclude nulls). `ValueRange`/`DateRange` need at least one of
`min`/`max` or `dateStart`/`dateEnd` — one-sided emits a GreaterThanOrEqualTo/
LessThanOrEqualTo, both emits Between (inclusive; `min` must be ≤ `max`) — and
only apply to `Continuous` fields; use a Dimension filter for a `Discrete`
(string) one. `DateRange` bounds must be real calendar dates (ISO 8601
`YYYY-MM-DD` or full timestamp) — a malformed value like `2025-99-99` is
rejected up front. Filters compose with `excludeNulls` (which adds its own
aggregated null filter) without clobbering each other.

**Sorted-dimension subtlety:** filtering the auto-sorted categorical
dimension of a bar chart keeps the auto-sort (filter runs on an internal
copy). Filtering the *measure* the chart sorts by drops the auto-sort — a
measure can't be both a sort key and a filter target.

## 15. Forecasts (Timeseries Only)

`visualSpecification.forecasts` is a map of `forecastKey -> config`, valid
**only** on a Line chart with a continuous `DateTrunc*` dimension on the
timeseries axis — a non-timeseries chart (e.g. Bar) fails `INVALID_INPUT`.

Required: `forecastModel` (`HoltWinters` — seasonality/trend — or
`RidgeRegression` — linear/L2); `dimensionFields` (one entry, `dateDim.
fieldKey` matching a `Continuous` `DateTrunc*` field in `fields`,
`granularity: "InferFromData"` only); `measureFieldKey` (a measure field);
`from: {predefinedDate: "LatestData"}`; `to.forecastInterval` (`value` > 0 +
`timeUnit` ∈ Minutes/Hours/Days/Weeks/Months/Quarters/Years).

Optional: `includeBounds` (default true), `confidenceLevel` (90/95/99,
default 95), `ignoreLastPeriods` (default 0), `fillNullsWithZero` (default
false). A `dateDim`/`measureFieldKey` missing from `fields`, or of the wrong
type, fails `INVALID_INPUT` naming the offending forecastKey.

## 16. Calculated-Measure Level → Function Pairing

When binding a model-level calculated measure (from
`list_semantic_model_calculated_measures`, omit `objectName` — §10), copy its
`level` into the field's `level` property whenever `function` is set, then
pick `function` by that level:

| `level` | `function` |
|---|---|
| `AggregateFunction` / `TableCalc` | `UserAgg` |
| `Row` / `Lod` (LOD) | ordinary aggregation matching `aggregationType` (`Average`→`Avg`, `CountDistinct`→`CountD`), or omit `function` when `aggregationType` is `Auto`/`None` |

A missing or mismatched level/function pair is rejected before the
visualization saves.

## 17. Reference Line Knob

A per-measure-field knob (`fields.<key>.referenceLine`), distinct from
`edit_visualization`'s `addReferenceLine`/`editReferenceLine` operations
(`edit-visualization.md` §6) which target an already-saved viz. Values:
`Average`/`Sum`/`Min`/`Max` (computed line) or `Target` with a required
`referenceLineValue` (constant quota/threshold) — no `Median`. Keep to at
most one per chart.

## 18. Common Errors

| Error | Root cause |
|---|---|
| `INVALID_INPUT` | Missing top-level required field (`workspaceId`/`workspaceName`/`semanticModelName`/`semanticModelLabel`/`label`/`fields`/`visualSpecification`); malformed filter (both `include`+`exclude`, `min`>`max`, empty date bounds); or a forecast referencing a missing/mistyped field, non-Line chart, `forecastInterval.value`≤0, or invalid `confidenceLevel`. |
| `INVALID_VISUALIZATION_METADATA` | A fieldKey used in `rows`/`columns`/an encoding/a filter isn't in the `fields` map, or an encoding type doesn't fit the mark (e.g. `Angle` outside `Donut`). |
| `JSON_PARSER_ERROR` | Body shape mismatch — `fields` must be a map (not an array); `marks.panes` is a single object (not an array of panes); `visualSpecification` must be a top-level object, not nested under `body`. |
| `UNKNOWN_EXCEPTION` | Most common fixable cause: binding a **calculated measure** with `objectName` set — drop it (§10/§16). Also the generic fallback for `MeasureNames`/`MeasureValues` missing `displayCategory`. |
