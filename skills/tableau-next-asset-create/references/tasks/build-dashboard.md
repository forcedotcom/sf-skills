# Task: Design / create a dashboard

Design a dashboard narrative, create a **new** dashboard, or add a global
filter. Entry points 18, 19, 21. (Entry point 20, "add/edit a widget on an
existing dashboard," now lives in `edit-dashboard.md`.)

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1, G8-full** · plus per-action:
- **Design narrative (18):** G1, G8-full · Conditional **G6** (◐, if you don't
  yet understand what the underlying data means).
- **Create dashboard (19):** G1, **G2/G7** (transitive), G3, G8-full.
- **Add global filter (21):** G1, G3 only — do NOT over-gate with G2/G7/G8.

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G8-full (decision #1):** design the narrative FIRST — KPIs → trends →
  breakdowns → correlations, KPIs top/left on the F/Z path, chart-type diversity
  (`../dashboard-design-principles.md`, MANDATORY for a dashboard).
- **G2/G7 (transitive):** a dashboard is only as valid as its widgets — each
  viz/metric widget's underlying query must have returned real rows first.
- **G3:** read back the exact metric apiName / viz `id`+`name` before referencing
  them in a widget.
- **G6** (◐, narrative design): if you don't yet understand grain/additivity of
  the data the narrative is built around, profile first (`../data-understanding.md`).

## Hard constraint — viz-type widgets (decision #2)

A **viz-type widget requires the `id` + generated `name` returned by a prior
`create_visualization` call** (`upsert_visualization_widget`'s `source: {id,
name}` — `../edit-dashboard.md` §2). This dashboard shell can self-serve
**metric + text** widgets once built, but **not** a viz widget from nothing. So:

- **Metric / text widgets:** self-serve via `tasks/edit-dashboard.md` once the
  shell exists.
- **Viz widget:** either (a) **compose** the `create-viz.md` flow first to get the
  `id`+`name`, or (b) **accept** a pre-existing viz `id`+`name` the user supplies.
  If the user asks for a chart on the dashboard and no viz exists yet, route
  through **`create-viz.md`** first, then place its `id`+`name` as a viz widget
  via `tasks/edit-dashboard.md`.

## Steps

Dashboard creation and the 48-column grid spec are in
**`../dashboard-authoring.md`**; `../build-workflow.md` Step 11 is the spine.
Once the shell exists, all widget/page editing — metric, viz, text, or any
other widget kind — routes through **`edit-dashboard.md`** via
**`tasks/edit-dashboard.md`**; this guide covers create + design + global
filter only.

- **Create empty shell** — `create_dashboard` (`widgets:{}`; seed one layout
  with an empty `page_1` since widgets get placed next — `layouts:[]` only if
  they won't — and always pass `minorVersion: -1` explicitly —
  `../dashboard-authoring.md` §1).
- **Metric / viz / text / any other widget** — hand off to
  **`tasks/edit-dashboard.md`** (`edit_dashboard`'s `upsert_*_widget` +
  `place_widget_on_page`, staged as a draft, saved only on confirmation) — the
  only supported path for widget/page editing.
- **Global filter** — `add_global_filter_to_dashboard`; self-contained (no
  separate read/replace round trip), value-matching rule of thumb, and the
  contrast with a per-viz filter — `../dashboard-authoring.md` §5.
- **Metric-card insight payload (app renderer only)** — `../insight-bundle.md`.
  Do **not** call `generate_insight_bundle` on a user chat turn.
- **Show / open an existing dashboard** — `render_dashboard`, not
  `get_dashboard`. Flags and metadata-vs-render split:
  `../dashboard-authoring.md` §8.
