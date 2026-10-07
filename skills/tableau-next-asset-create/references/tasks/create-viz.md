# Task: Create a visualization (single chart)

Create one visualization with `create_visualization` on a built, populated model.
Entry point 17. (For a dashboard, use `build-dashboard.md`.) This is also the
**first hop** for a chart-type / `create_visualization` payload lookup — do not
start at `viz-authoring.md`.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1, G2, G3, G7, G8-light** · Conditional: **G4** (◐, if the chart
queries across >1 object), **G5/G6** (◐, consume-not-create)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G7:** run `run_semantic_query` and confirm real rows come back BEFORE
  `create_visualization` — never chart a model that returned empty.
- **G2:** don't chart an empty/unverified source — field-richness ≠ data-presence.
- **G3:** read field apiNames back via `list_*`; `create_visualization` uses a
  `fields` map keyed by fieldKey (`{objectName, fieldName, function}`; `objectName`
  omitted for calc measures) — NOT the retired `fieldRef`/`measureFunction` shape,
  and distinct from `run_semantic_query`'s snake_case `table_field`.
- **G8-light (decision #1):** state the chart's **analytical intent** — the one
  question this chart answers and why the chart type fits the field roles
  (trend/comparison/part-to-whole/correlation/forecast). A single standalone viz
  does NOT require the full dashboard narrative, and you must **not invent a
  dashboard** around it.
- **G5/G6** (◐): viz *consumes* metadata rather than creating it — business-
  friendly labels depend on upstream descriptions already existing.
- **G4** (◐): only chart across objects that are actually joined — do not set
  `queryUnrelatedDataObjects:"Exception"` and chart across unjoined objects.

## Steps

The visualization tool-selection guide, chart-type decision matrix (mapped to MCP
tools), field-selection priorities, color/breakdown encoding, UserAgg handling,
and verified payloads are in **`../viz-authoring.md`**; narrative/labeling
guidance is `../dashboard-design-principles.md`.

**First, identify the user's analysis intent — it picks the analysis type, which
picks the chart.** Don't jump straight to a bar chart:

| User intent (example) | Analysis type | Tool guidance | §reference |
|---|---|---|---|
| "revenue over time" | trend | Line (date on columns) | `viz-authoring.md` §11 Time Series |
| "top categories by sales" | comparison | Bar (dim on columns, sorted) | `viz-authoring.md` §11 Bar |
| "market-share breakdown" | part-to-whole | Donut (< 5 vals) or Bar (≥ 5) | `viz-authoring.md` §11 Donut |
| "discount vs profit relationship" | correlation | Scatter (2 measures, 1 color dim) | `viz-authoring.md` §11 Scatter |
| "predict next quarter revenue" | forecast | Line + `visualSpecification.forecasts` | `viz-authoring.md` §3 / §11 Time Series (forecast) |

- Pick the chart type matched to intent + field roles — do not default every
  chart to a bar chart.
- Build with `create_visualization` (`fields` map + `visualSpecification`), only
  after Step 9 / G7 returns real data. FieldKeys in `fields` are pointers —
  they must exactly match `rows` / `columns` / encoding `fieldKey` strings.
- For forecast asks: timeseries Line only, continuous `DateTrunc*` date +
  measure, then a `forecasts` entry (`HoltWinters` or `RidgeRegression`).
- Keep the returned viz `id` + generated `name` — a dashboard viz-widget needs
  both (see `build-dashboard.md`).
