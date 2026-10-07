# Dashboard Authoring — Tool Guide & Verified Payloads

Load this for **Step 11** (build the dashboard). Covers dashboard creation,
widget placement grid, metric/viz widgets, text/label widgets, and critical gotchas.

> **Before placing widgets on the 48-col grid:** design the narrative and
> visual hierarchy first — see `references/dashboard-design-principles.md`
> (KPIs top/left, F/Z eye-path, story order: KPIs → Trends → Breakdowns →
> Correlations). Grid placement below is the mechanics; the design doc is
> the intent.

## Contents

- 1. Create the Empty Dashboard
- 2. Grid Specification
- 3. Editing Widgets — `edit_dashboard` (primary path)
- 4. Gotchas Summary
- 5. Global Filters — `add_global_filter_to_dashboard`
- 6. Deleting a Dashboard — `delete_dashboard`
- 7. Preflight before deleting a viz or dashboard — `list_asset_dependencies`
- 8. Show a dashboard vs metadata-only — `render_dashboard` / `get_dashboard`

---

## 1. Create the Empty Dashboard

Always start with an empty shell, then populate it with widgets.

```jsonc
{
  "name": "Brightleaf_Sales_Overview",
  "label": "Brightleaf Sales Overview",
  "workspaceIdOrApiName": "brightleaf_demo",
  "description": "Overview of Brightleaf sales performance by region and product",
  "widgets": {},
  "layouts": [{
    "columnCount": 48,
    "rowHeight": 20,
    "maxWidth": 1200,
    "style": { "backgroundColor": "#ffffff", "gutterColor": "#f3f3f3", "cellSpacingX": 4, "cellSpacingY": 4 },
    "pages": [{ "name": "page_1", "label": "Overview", "widgets": [] }]
  }],
  "minorVersion": -1
}
```

This seeded-`page_1` shell is the **default** shape — see the decision rule
below for when `layouts: []` is the right call instead.

**`workspaceIdOrApiName` is an id like `1Dyxx...` or apiName from `list_workspaces`. NOT the workspace label with spaces — that 404s.**

**Silent name transforms — always read `name` back.** `create_dashboard` mutates the
`name` you send with no warning: a duplicate name in the org gets a numeric suffix,
non-ASCII/unicode characters are silently stripped, names past ~78-80 characters are
silently truncated, and spaces are silently converted to underscores. Never assume
the requested `name` was stored verbatim — read the response back before referencing
it (e.g. in a widget's `source` or a navigation target).

**Don't call `create_dashboard` with just `{name, label, workspaceIdOrApiName}`.**
That leaks a raw Java NPE (`Cannot invoke "java.util.Map.values()" ...getWidgets()`).
`widgets: {}` and a `layouts` value (`[]` or seeded, per the decision rule below)
are de-facto required even when empty — never omit either.

**Pick one create recipe based on what happens next — verified live
(2026-09-13):**

- **You will `edit_dashboard` immediately after — the common "create, then
  place widgets" flow.** Seed one layout with an empty `page_1` (full `style`
  block + `columnCount`, as in the shell above), then `edit_dashboard`.
  `add_page`/`place_widget_on_page` operate *within* an existing layout — they
  do not create the first one. A `create_dashboard` done with `layouts: []`
  yields a dashboard with **no layout at all**, and the next `edit_dashboard`
  `add_page` fails: `INVALID_INPUT: "Dashboard has no layout to add the page
  to"`.
- **You will NOT edit/populate the dashboard next** (e.g. handing off a bare
  shell). `layouts: []` is fine — there's nothing to place yet anyway.

If you do seed a page up front, give every layout a full `style` block and
`columnCount` — omitting `style` at create time renders an **unstyled
dashboard** (no crash), and omitting `columnCount` breaks grid math for every
widget placed later.

**Workspace cascade on delete.** `delete_workspace` cascade-deletes every
workspace-asset row whose `assetUsageType="Created"`, and that delete propagates
to the underlying asset — confirmed for `AnalyticsVisualization`, `SemanticModel`,
AND `AnalyticsDashboard` (not just dashboards). Assets added with
`assetUsageType="Referenced"` are NOT deleted — only their workspace association
is removed. `create_dashboard` and `create_*_viz` each auto-create a `"Created"`
workspace-asset row for the new asset, so any chart or dashboard authored in that
workspace will be swept up. ALWAYS call `list_workspace_assets` first to inventory
`Created`-typed assets before deleting a workspace — there's no undo.

**Scope and response shape.** `create_dashboard` creates in the current org only —
it does not copy a dashboard from another org. Verified live (2026-08-30): as
observed through this tool, `create_dashboard`'s response is a **flat JSON
object**, NOT double-wrapped. `edit_dashboard` and
`delete_dashboard`, by contrast, ARE double-wrapped as
`{"defaultExc": "<stringified JSON>", "responseCode": <number>}` (parse
`JSON.parse(response.defaultExc)`; see §6 for `delete_dashboard`'s success-path
exception). The wrapping is per-tool, don't assume it's family-wide.

**`minorVersion` must be sent explicitly.** The schema shows `minorVersion:
-1` as a default, but omitting it can surface a live client-visible error:
`ILLEGAL_QUERY_PARAMETER_VALUE: Illegal value for query parameter
'minorVersion': ''`. Always pass `minorVersion: -1` on `create_dashboard` (and
on `edit_dashboard` — `edit-dashboard.md` §1).

---

## 2. Grid Specification

The grid is **48 columns** (`columnCount: 48`), `rowHeight 20`, `maxWidth 1200`.
Plan colspans in 48ths (a half-width chart = 24, a quarter KPI = 12).
`columnCount` is required on every layout at create time, alongside a full
`style` block (§1).

**Always name AND label every page.** If you seed a non-empty `layouts` block
on `create_dashboard`, each `layouts[].pages[]` entry needs both `name` (API
id, e.g. `page_1`) and `label` (display name) set explicitly — `create_dashboard`
does **not** auto-derive `page_N`. An omitted `name` is stored empty (any
navigation widget targeting it by `page_N` won't resolve) and an omitted
`label` renders a blank page tab. Set both at create time rather than fixing
page one up later via `edit_dashboard`'s `rename_page`.

---

## 3. Editing Widgets — `edit_dashboard` (primary path)

**Use `edit_dashboard` for all widget/page editing on an existing dashboard** —
add, replace, move, or remove a widget of any kind (metric, visualization, text,
button, container, filter, parameter, navigation), and add/rename/delete a
page. It is the only supported tool for this purpose — never hand-build a
dashboard-JSON PATCH.

Full operation-type table, the widget-identity rule (`widget.name`/`widget.id`
vs. `placement.name`), grid placement, draft-vs-persist mechanics
(`save_dashboard`/`undo`/`discard_dashboard`), and full widget deletion via
`remove_widget_from_dashboard` are all in **`edit-dashboard.md`**
(task guide: `tasks/edit-dashboard.md`).

---

## 4. Gotchas Summary

`create_dashboard` gotchas below. For `edit_dashboard` (§3, primary path)
gotchas, see `edit-dashboard.md` §7.

| Gotcha | Rule |
|---|---|
| Omitting `minorVersion` on `create_dashboard` | Client-visible `ILLEGAL_QUERY_PARAMETER_VALUE` on an empty value — always send `minorVersion: -1` explicitly |
| `create_dashboard` response wrapping | Flat JSON, NOT double-wrapped (verified live) — don't apply the `defaultExc`/`responseCode` parse to it |
| `&` in text labels | HTML-encodes to `&amp;` in round-trip — use "and" or "/" |
| `create_dashboard` `name` mutated silently | Dup → suffix; non-ASCII stripped; ~78-80 char truncation; spaces → underscores — always read `name` back |
| `create_dashboard` with no `widgets`/`layouts` | Leaks a raw NPE — always pass `widgets: {}` and a `layouts` value (`[]` or seeded) at minimum |
| `add_page`/`place_widget_on_page` right after `create_dashboard` with `layouts: []` | Fails `INVALID_INPUT: "Dashboard has no layout to add the page to"` (verified live 2026-09-13) — seed one layout with an empty `page_1` in `create_dashboard` instead when you'll edit immediately (§1) |
| Missing `layouts[].style`/`columnCount` on `create_dashboard` bulk-create | Renders an unstyled dashboard (no runtime crash at create time) — always include a full `style` block and `columnCount` |
| Bulk-create pages with no `name`/`label` | `create_dashboard` does NOT auto-derive `page_N` — set both explicitly on every page at create time |
| `delete_workspace` on a workspace with `Created`-typed assets | Cascades — deletes every viz/SDM/dashboard whose workspace-asset row is `assetUsageType="Created"` (`Referenced` rows only lose their association, asset itself survives); list workspace assets first |
| `delete_visualization` / `delete_dashboard` without `list_asset_dependencies` | Preflight first (§7) — returns **counts not ids**; if `analyticsdashboard` > 0, widgets are not cleaned (`source` silently nulled) — `remove_widget_from_dashboard` first |
| `workspaceIdOrApiName` is the workspace label with spaces | 404s — pass the id (`1Dyxx...`) or apiName from `list_workspaces`, NOT the label |

---

## 5. Global Filters — `add_global_filter_to_dashboard`

A global filter is **dashboard-wide**, not baked into one chart — it drives every
viz/metric widget on the dashboard that shares the filtered field's semantic model
and object. This is a different mechanism from `create_visualization`'s own
per-chart `filters` array (`viz-authoring.md`) or an `edit_visualization`
`addFilter` op (`edit-visualization.md`), which each scope to one visualization
only. Ask which the user means when it's ambiguous ("filter this chart" vs. "filter
the dashboard").

**Self-contained.** This tool builds the full filter-widget JSON and places it
on the grid internally — no separate read/replace round trip needed. Required
inputs: `dashboardIdOrApiName`, `semanticModelIdOrName`, `objectName`,
`fieldName`, and a grid `placement` (48-col grid, same conventions as §2; a
common size is full-width `colspan: 48, rowspan: 4` or half-width
`colspan: 24, rowspan: 4`).

**Value-matching rule of thumb:**

- **Relative-date presets** (e.g. "default to current quarter") — pass `operator`
  alone (`CurrentQuarter`, `CurrentMonth`, `PreviousMonth`, `LastNDays`, …); omit
  `initialValues`.
- **Exact/contains/range matching** — pass `operator` (`Equals`, `In`, `Contains`,
  `GreaterThan`, …) **and** `initialValues` as a JSON array, even for one value
  (`["West"]`, not `"West"`). Use a multi-element array for `In`.

One line each: `dataType` (`Text`/`Number`/`Date`/`Boolean`/`measure`) is
case-sensitive and defaults to `Text`; `selectionType` (`single`/`multiple`) defaults
to `multiple`; `filterLabel` (optional display label) defaults to `fieldName`;
`widgetName` (optional unique name) auto-generates as `filter_N` when omitted.
A global filter is just a widget under the hood — `edit_dashboard`'s
`remove_widget_from_page` only unplaces it; to fully remove one, use
`remove_widget_from_dashboard` with its `widgetName` (`edit-dashboard.md` §6).

---

## 6. Deleting a Dashboard — `delete_dashboard`

`delete_dashboard` permanently removes a dashboard. **Destructive, no undo** —
always get explicit user confirmation first (`SKILL.md` lifecycle bullets).

**Inputs:** `dashboardIdOrApiName` only (the id or apiName from
`list_dashboards`/`browse_data_assets`). Scope is the current org only.

**Response shape — verified live (2026-08-30):** double-wrapped as
`{"defaultExc": "<stringified JSON>", "responseCode": <number>}`. On the
success path (`responseCode: 204`), `defaultExc` is an **empty string** (`""`)
— NOT the literal string `"204"`, and not JSON-parseable either way. Branch on
`responseCode === 204` for success; don't try to parse `defaultExc` on that
path.

**Not idempotent.** A second `delete_dashboard` call against an
already-deleted (or never-existent) id returns a 404:
`RESOURCE_NOT_FOUND: "We couldn't find dashboard."` Treat that specific error
as success-equivalent if your flow might double-call delete.

**No cascade to referenced assets.** Deleting a dashboard does not delete the
visualizations/metrics it displayed — only the dashboard and its widget
placements. Compare `delete_workspace`'s cascade behavior (§1), which is a
different, broader operation.

---

## 7. Preflight before deleting a viz or dashboard — `list_asset_dependencies`

Call this before `delete_visualization` or `delete_dashboard`. Distinct from
`list_semantic_model_dependencies` (in-model calc/metric graph; see
`sdm-tool-reference.md`).

- **`assetId` is the 18-char id only** — an apiName returns a misleading
  workspace error.
- Returns **COUNTS by type**, not dependent ids/names — you cannot name which
  dashboards will break. `totalCount`/`nextOffset` page the queried-asset list,
  not the dependents.
- Show the counts, then **end the turn and wait for a new unambiguous yes**.
  A prior "delete" in the same request is a plan, not confirmation.
- `delete_visualization` does NOT clean dashboard widgets. If
  `dependentAssets.analyticsdashboard` is nonzero, N dashboards will keep a
  broken widget (`source` silently nulled). Prefer
  `remove_widget_from_dashboard` first (`edit-dashboard.md` §6) for a clean
  remove.

---

## 8. Show a dashboard vs metadata-only — `render_dashboard` / `get_dashboard`

**If the user wants to see, open, view, display, render, bring up, pull up,
load, or look at a dashboard** (its charts, filters, or layout) — including
when they name or id a dashboard and want to see it — call `render_dashboard`.
That is the dashboard analog of `get_visualization` for
charts. **`get_dashboard` does not render.**

Do **not** call `get_dashboard` just because the skill already uses it for
`edit_dashboard` prep. Metadata-only is for inspect / `edit_dashboard` prep.
Current org only.

### `render_dashboard` — inline render

Retrieves the dashboard's full metadata **bundled with its referenced
assets** (semantic models and visualizations) so visualization / filter /
parameter widgets can render immediately — no extra per-asset fetches.

**Required inputs** (live sidecar — always send all four flags):

- `dashboardIdOrApiName` — id or apiName from `list_dashboards` or
  `browse_data_assets`
- `addVisualization=true` — so visualization tiles can render
- `addSdm=true` — so filter / parameter widgets that need SDM metadata can
  render
- `showDraft=true` — include an in-progress `edit_dashboard` draft;
  `get_dashboard` will not show that draft
- `minorVersion=-1` — latest **Salesforce API** minor version, **not** a
  dashboard revision

**Optional:** `pageName` (page GUID), `customViewId`, `height` (viewport
pixels — when passed, only assets visible within that height are included).

**Returns:** `{dashboard, bundledAssets}`. `dashboard` is the full metadata
(layout, widgets, owning workspace, `url`). `bundledAssets` is a map of
asset id → referenced semantic model / visualization. Read them at
`response.dashboard` and `response.bundledAssets`.

### `get_dashboard` — metadata only (cheaper, no bundled assets)

Use when you need `label` / `widgets` / `layout` / owning workspace
programmatically, to diff two dashboards, or to prepare an `edit_dashboard`
batch. Do **not** use it when the intent is to *see* the dashboard — for that,
call `render_dashboard` above.

**Inputs:** `dashboardIdOrApiName`. Optional `minorVersion` is the Salesforce
API version (e.g. `67.42`), **not** a dashboard revision — invalid values
produce `Invalid version`.

**Returns:** fields **directly** on the response (`label`, `widgets`,
`layout`, `folder`, `url`) — flat, like `create_dashboard`; unlike
`edit_dashboard` / `delete_dashboard`, which double-wrap (§6, `edit-dashboard.md`
§1). `url` is a canonical **external**
Analytics-app link — it does not render the dashboard inline. For inline
rendering, call `render_dashboard`.
