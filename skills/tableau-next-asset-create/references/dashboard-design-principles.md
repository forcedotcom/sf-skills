# Dashboard Design Principles — Supported Practices Mapped to MCP Tools

Load this alongside `viz-authoring.md` (Step 10) and `dashboard-authoring.md`
(Step 11). This file covers the **design layer** — narrative, visual
hierarchy, naming, field selection, color, filters, and the data-presence
gate — translated from universal dashboard design best practices to what the
`tableau-next-pilot` MCP tools **actually** expose.

> **No named templates/patterns exist.** The MCP surface is a small set of
> generic primitives: `create_visualization` (`marks.panes.type` ∈ `Bar`,
> `Line`, `Circle`, `Square`, `Text`, `Donut`; `layout` ∈ `Vizql`, `Radial`,
> `Table`), a raw 48-column dashboard grid (`create_dashboard` +
> `edit_dashboard`'s `upsert_*_widget`/`place_widget_on_page` batch),
> `add_global_filter_to_dashboard`,
> and the `list_/get_semantic_model_*` discovery tools. Every principle below
> is achieved by combining these primitives by hand — never invent a template,
> script, or param name that isn't in `viz-authoring.md` §11/§12 or
> `dashboard-authoring.md`.

## Contents

- 1. Think Like a Business User (before any `create_*` call)
- 2. Design the Narrative Before Picking Charts (REQUIRED)
- 3. Visual Storytelling Flow — KPIs → Trends → Breakdowns → Correlations
- 4. Visual Hierarchy — F-Pattern, Z-Pattern, Progressive Disclosure, Color, White Space
- 5. Business-Question → Chart-Type Mapping
- 6. Naming Conventions
- 7. Field Selection Priority
- 8. Color Encoding — Real Mechanism, Not `color_dim`/`stack_dim`
- 9. Filters — Dimensions Not Measures
- 10. Data-Presence Gate — Hard Stop Before Any Viz
- 11. Dashboard Quality Checklist (MCP Reality)
- Not supported by the tableau-next-pilot MCP (do not attempt)

---

## 1. Think Like a Business User (before any `create_*` call)

Before calling `create_visualization` or `create_dashboard`, answer three
questions in your own reasoning — no tool enforces this:

1. **What question does this chart answer?** If you can't state it in one
   sentence, don't build it.
2. **What action will the viewer take from this?** A chart with no
   actionable follow-up is decoration.
3. **Can a non-technical user read every label?** No raw field apiNames, no
   `_Clc`/`_mtc` suffixes, no bare object names.

This discipline feeds directly into `create_visualization`'s `label`/`title`
and the dashboard's `label` — pull field labels from `list_semantic_model_dimensions`
/ `list_semantic_model_measures` (their `label`, not `fieldName`), and cross-check
against the SDM's own `description` via `get_semantic_model`. This is pure
pre-authoring judgement; nothing downstream validates it for you.

---

## 2. Design the Narrative Before Picking Charts (REQUIRED)

Before the first `create_visualization` call, write out — even briefly:

- The business questions the dashboard must answer.
- The logical flow between them (what should the eye see first, second, third).
- Friendly names for every field you intend to use.
- Which dimensions are actually meaningful (not IDs, not descriptions).
- What action the viewer takes after seeing each section.

This is a hard **gate on Step 9** in SKILL.md — do not call
`create_visualization` until `run_semantic_query` (or `run_query`) has
returned real, non-empty rows for every source you plan to chart (§9 below).
The narrative is realized entirely through **intentional sequencing** of
`create_visualization` calls and widget placement — there is no
narrative/flow object to configure.

---

## 3. Visual Storytelling Flow — KPIs → Trends → Breakdowns → Correlations

There is no flow abstraction in the MCP. Realize the sequence by widget type
and grid row, top to bottom:

| Story beat | MCP realization | Placement guidance |
|---|---|---|
| **KPIs** | `edit_dashboard`'s `upsert_metric_widget` + `place_widget_on_page` (`parameters.metricOption.{sdmApiName, sdmId}`; `source` optionally references the metric) | Row 0, spanning the top band |
| **Trends** | `create_visualization` with `marks.panes.type: "Line"` | Immediately below the KPI band |
| **Breakdowns** | `create_visualization` with `marks.panes.type: "Bar"` (plain, stacked, or Donut for <5 categories) | Below trends |
| **Correlations** | `create_visualization` with `marks.panes.type: "Circle"` (scatter) | Bottom of the grid |

Sequence widgets top-to-bottom by **ascending `placement.row`** on the
48-column grid — that ascending-row order *is* the story order. There is no
server-side flow validation; if you place the scatter chart at `row: 0` and
the KPIs at `row: 40`, the story reads backwards with no warning.

---

## 4. Visual Hierarchy — F-Pattern, Z-Pattern, Progressive Disclosure, Color, White Space

No `f_layout` / `z_layout` pattern objects exist. Build the eye-path by hand
with `placement.{row,column,rowspan,colspan}` on the 48-column grid
(`rowHeight: 20`, `maxWidth: 1200`).

**F-pattern (metrics-left/top-heavy scan):**

```jsonc
// KPI band across the top
{ "row": 0,  "column": 0,  "rowspan": 8,  "colspan": 12 }  // metric 1
{ "row": 0,  "column": 12, "rowspan": 8,  "colspan": 12 }  // metric 2
{ "row": 0,  "column": 24, "rowspan": 8,  "colspan": 12 }  // metric 3
{ "row": 0,  "column": 36, "rowspan": 8,  "colspan": 12 }  // metric 4
// Primary trend, full width, second scan line
{ "row": 8,  "column": 0,  "rowspan": 18, "colspan": 48 }
// Secondary breakdowns, left-weighted third scan line
{ "row": 26, "column": 0,  "rowspan": 16, "colspan": 24 }
{ "row": 26, "column": 24, "rowspan": 16, "colspan": 24 }
```

**Z-pattern (left→right, then diagonal down to left→right again):**

```jsonc
{ "row": 0,  "column": 0,  "rowspan": 8,  "colspan": 24 }  // top-left
{ "row": 0,  "column": 24, "rowspan": 8,  "colspan": 24 }  // top-right
{ "row": 8,  "column": 0,  "rowspan": 18, "colspan": 24 }  // bottom-left
{ "row": 8,  "column": 24, "rowspan": 18, "colspan": 24 }  // bottom-right
```

**Progressive disclosure:** put the single most important KPI/chart at
`row: 0, column: 0` with the largest `colspan`/`rowspan`; secondary detail
(tables, drill-down breakdowns) go further down the grid. There is no
drill-down/expand mechanism — "progressive disclosure" here just means
"important things occupy the first screen's worth of rows."

**Color consistency:** the same category must map to the same color across
every chart on the dashboard. The only lever is the `Color` encoding
fieldKey in `marks.panes.encodings` — pick the *same underlying dimension*
(same `objectName`+`fieldName`) for the Color encoding on every chart that
breaks down by that category. There is no shared palette/legend registry;
consistency is achieved by field-binding discipline, not a setting.

**White space:** don't tile every grid cell. Leave gaps between widget
groups (skip a row or two between `placement.row` bands) and set
`layouts[].style.cellSpacingX` / `cellSpacingY` (verified default: `4`) on
the dashboard's `style` block — see `dashboard-authoring.md`. Overcrowding
the 48-column grid (i.e. every row fully packed edge-to-edge) is a real
readability failure with no tool-level guard; watch it yourself.

---

## 5. Business-Question → Chart-Type Mapping

Every row maps to an achievable `marks.panes.type` / `layout` combination —
no named templates. See `viz-authoring.md` §2–3 for the full decision matrix
and verified payloads; summarized here with the MCP-native mechanism:

| Business question | Data pattern | `marks.panes.type` / `layout` | Mechanism |
|---|---|---|---|
| Trending over time | Date + measure | `Line` / `Vizql` | Date on columns with `DateTruncMonth` (Continuous); measure on rows |
| Trend by category | Date + measure + dim | `Line` / `Vizql` | + `Color` encoding on the breakdown dimension |
| Best/worst performers | Dim + measure | `Bar` / `Vizql` | Server auto-sorts descending; override with `sortIntent` |
| Composition (<5 categories) | Dim (<5 vals) + measure | `Donut` / `Radial` | Measure on **`Angle`** encoding (not `rows`); dim on `Color` |
| Composition (≥5 categories) | Dim (≥5 vals) + measure | `Bar` / `Vizql` | Donut is unreadable beyond ~4 slices |
| Breakdown by two dimensions | 2 dims + measure | `Bar` / `Vizql` | + `Color` on 2nd dim + `stack: {isAutomatic:false, isStacked:true}` |
| Compare multiple measures | Dim + 2+ measures | `Bar` / `Vizql` | `MeasureNames`/`MeasureValues` synthetic fields, or both measures in `columns` |
| Performance hotspots | 2 dims + measure | `Square` / `Vizql` | Two dims on rows/columns; measure on `Color` encoding |
| Correlation | 2 measures | `Circle` / `Vizql` | X-measure on columns, Y-measure on rows; point dim on `Color`/`Detail` |
| Detailed rankings | Multiple dims + measures | `Text` / `Table` | Dims in `groups` (outer→inner), measures in `rows` |
| YoY comparison | Date + measure + year | `Line` / `Vizql` | `DatePartMonth` on axis, `DatePartYear` on `Color` — period overlay, not a continuous timeline |

**Map (point/geographic) and Flow (Sankey) are not on this table because
they are unsupported** — no matching mark type exists. See the closing
section for fallbacks.

---

## 6. Naming Conventions

**The mechanical rules — suffix stripping (`_Clc`/`_mtc`/`_MTC`/`_CLC`),
≥3-word business-friendly titles, never exposing a raw suffixed apiName like
`Region4`/`Amount7` — live in `viz-authoring.md` §4. Follow them.** The
design-layer points on top of those mechanics:

- **Pull display labels from the SDM's own `label`** (via
  `list_semantic_model_dimensions` / `list_semantic_model_measures`, or
  `get_semantic_model`) — there is no `sdm_fields[field]['label']` accessor —
  and cross-check the intent against the SDM `description`. The label should
  answer the business question, not just rename the field.
- **Read the transformed name back.** `create_dashboard` and
  `create_visualization` auto-transform the `name`/apiName you send
  (spaces → `_`, truncation, unicode stripped) — after creation, read back
  the actual stored `name` rather than assuming your input string survived
  unchanged.

---

## 7. Field Selection Priority

**The priority ladder (CLC/calculated → meaningful categorical → geographic/org
→ name fields → avoid generic text → never ID fields), the cardinality
thresholds (≤4 Donut / 5–50 Bar / 50+ Top-N), and the CLC + `UserAgg`
no-double-aggregation rule all live in `viz-authoring.md` §5 and §7.** The
design-layer framing on top of those mechanics:

- Field selection is a **judgement call, not an enforced check** — nothing
  downstream stops you from charting an ID field or a raw description, and
  there is no `recommend_diverse_chart_types()` scoring function. Apply the
  ladder yourself when choosing among fields returned by
  `list_semantic_model_*`.
- **Prefer CLC business-ready fields** precisely because they encode the
  business definition — discover them via
  `list_semantic_model_calculated_measures` /
  `list_semantic_model_calculated_dimensions` before falling back to raw
  fields.
- Binding note: a calculated measure takes `fieldName` only (**omit
  `objectName`** — including it on a calculated measure throws
  `UNKNOWN_EXCEPTION`) with `function: "UserAgg"`.

---

## 8. Color Encoding — Real Mechanism, Not `color_dim`/`stack_dim`

*(Encoding mechanics and the verified stacked-bar / `colorScale` payloads are
in `viz-authoring.md` §6 and §11 — this section covers the design intent and
the named-parameter myths.)*

**`color_dim` and `stack_dim` do not exist as parameters anywhere in the MCP
surface.** There is no automatic coloring for "templates when 2+ dimensions
are present" — nothing is automatic. Color is always an explicit encoding
entry:

```jsonc
"marks": {
  "panes": {
    "type": "Bar",
    "encodings": [{ "type": "Color", "fieldKey": "<dim_field_key>" }]
  }
}
```

- **Stacked bar** is NOT a `stack_dim` param — it is `type: "Bar"` +
  a `Color` encoding on the second dimension + an explicit
  `stack: { "isAutomatic": false, "isStacked": true }` block in `marks.panes`.
- **Any chart with a second dimension available** — add it as a `Color`
  encoding by hand. When 2+ dimensions exist and you skip this, the chart
  silently stays single-series; nothing warns you.
- **Diverging color scale** for signed / around-a-target measures (profit
  variance, YoY change): set `"colorScale": "Diverging"` on the
  Color-encoded measure's field binding. This is a real, verified param —
  use it only when the measure is genuinely centered on zero or a target;
  on all-positive data it misleads.

Cross-chart color coordination (same category → same color everywhere) is a
manual field-binding discipline (§4 above), not a dashboard-level setting.

---

## 9. Filters — Dimensions Not Measures

**Filter on dimensions, never on measures**, use business-friendly labels,
avoid ID fields, and prefer filter fields that also appear as encodings in
the vizzes on the same dashboard (so the filter visibly affects what the
user is looking at).

Two mechanisms, both real:

1. **Per-viz filters** — `create_visualization`'s `filters[]` array:
   `{ "fieldKey": ..., "type": "Dimension", "include": [...] }` (or
   `exclude`) for categorical filters; `ValueRange`/`DateRange` for
   continuous fields. A filter on a raw field is a WHERE (row filter); a
   filter on an aggregated measure becomes a HAVING (group filter) — the
   bucket is derived from the field, not chosen by you.
2. **Global dashboard filters** — `add_global_filter_to_dashboard`, which
   constructs the full filter-widget JSON and places it in one call
   (self-contained — no separate read/replace round trip). Required
   inputs: `dashboardIdOrApiName`, `semanticModelIdOrName`, `objectName`,
   `fieldName`, `placement`. Set `filterLabel` explicitly for a
   business-friendly display name (defaults to the raw `fieldName` if
   omitted — exactly the kind of technical-name leak §6 warns against).

**Always look up `objectName` — never guess it.** There is no
`sdm_fields[field]['objectName']` accessor. `objectName` is the field's
owning SDM data-object apiName, discovered via
`list_semantic_model_data_objects`; it is a **required** param on
`add_global_filter_to_dashboard`. Calculated fields have no owning object —
omit `objectName` for them in `create_visualization` (same rule as §7).

---

## 10. Data-Presence Gate — Hard Stop Before Any Viz

**Confirm rows exist before building anything.** This is Rule 1 of the
parent skill (SKILL.md) and the primary defense against empty dashboards.

- `run_query` — `SELECT COUNT(*) AS n FROM <table>__dll` (or `__dlm`/`__dlc`)
  for a raw-table presence check.
- `run_semantic_query` — for a model that traverses relationships, confirm
  the query returns non-empty rows before charting from it (this doubles as
  the Step 7 model-validation check in SKILL.md).

**If the result is zero rows or a "table does not exist" error, STOP.** Do
not call `create_visualization`. Report the empty/unmaterialized source to
the user and offer an alternative source or metric — see
`empty-source-handling.md` for exact wording.

**`query_data.py --count` and `lib.query.assert_has_rows` do not exist** —
those are constructs from an external scripting workflow, which has no
equivalent MCP tool. The gate is real; those helpers are not. Use
`run_query`/`run_semantic_query` directly.

---

## 11. Dashboard Quality Checklist (MCP Reality)

**Business clarity**
- [ ] Every chart title states the business question it answers (≥3 words, no jargon)
- [ ] Field labels come from SDM `label` (via `list_semantic_model_*`), not raw apiNames
- [ ] No `_Clc`/`_mtc`/`_MTC`/`_CLC` suffixes or raw apiNames visible to the end user
- [ ] KPIs → Trends → Breakdowns → Correlations story order reflected in ascending `placement.row`

**Visual design**
- [ ] Metrics placed top/left (row 0) per the F-pattern or Z-pattern grid coordinates in §4
- [ ] Same dimension used for `Color` encoding across every chart that breaks down by that category
- [ ] Grid not overcrowded — deliberate empty rows/`cellSpacingX/Y` between widget groups
- [ ] Donut used only for dimension cardinality < 5; Bar used at ≥ 5

**UX**
- [ ] Every `add_global_filter_to_dashboard` call has an explicit business-friendly `filterLabel`
- [ ] Filters target dimensions, never measures; avoid ID fields
- [ ] Filter fields also appear as an encoding in at least one on-dashboard viz where practical

**Technical**
- [ ] `run_query`/`run_semantic_query` confirmed non-empty rows before any `create_visualization` call (§10)
- [ ] CLC/calculated measures use `function: "UserAgg"`, never re-aggregated with `Sum`/`Avg`
- [ ] `objectName` omitted for calculated measures/dimensions; looked up (never guessed) for raw fields and global filters
- [ ] Bar charts left to auto-sort descending, or `sortIntent` set deliberately
- [ ] YoY comparisons use `DatePartMonth` + `DatePartYear` period overlay, not a continuous timeline
- [ ] Viz created before the dashboard widget references it by `source.{id,name}` (creation order matters)
- [ ] Text/label widgets added via `edit_dashboard`'s `upsert_text_widget` + `place_widget_on_page` — the only supported path
- [ ] A `401`/auth-failure on any `create_*`/`update_*`/`run_*` call is treated as an expired org auth token or MCP connection — refresh org auth and reconnect the MCP server, then retry the same call; do not misdiagnose it as an empty-source or malformed-payload error

---

## Not supported by the tableau-next-pilot MCP (do not attempt)

| Best-practices item | Why unsupported | Nearest achievable alternative |
|---|---|---|
| Map / geomap (point map, lat+lon+measure) | No map/geo mark type; lat/lon not routed | `Bar` chart by Region/Territory dimension |
| Flow / Sankey (`flow_sankey`, `flow_package_*`, `flow_simple_*`) | No flow/sankey mark type | Two `Bar` charts showing source→destination volumes separately |
| Conversion funnel | No funnel mark type | Sorted `Bar` by stage order; communicate each stage's count in the title/description |
| Dot matrix (2 dims + 2 measures) | No dot-matrix mark | `Circle` scatter (2 measures) or ranked `Bar` |
| Nightingale rose (measure-driven radius) | Radial layout supports `Donut` marks only — no measure-driven radius | Horizontal `Bar` |
| Radial spoke bars | Not available in current tools | `Bar` |
| Radial heatmap (2 ring dims + slice dim + measure) | Not available | `Square` heatmap (2D grid) |
| Map/Flow color variants (`geomap_*` encodings, `flow_uniform_fill`, node-size color rules) | No map or flow/sankey mark exists to carry them | N/A — see map/flow fallbacks above |
| Named layout patterns (`f_layout`, `z_layout`, `performance_overview`) with fixed filter/metric/viz counts | The patterns and their auto-select logic do not exist — only the raw 48-column grid | Hand-place widgets using the F-pattern/Z-pattern grid coordinates in §4; filter/metric/viz counts are an authoring choice, not a pattern constraint |
