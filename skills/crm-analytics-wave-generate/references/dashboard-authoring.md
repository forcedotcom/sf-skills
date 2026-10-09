# Dashboard Authoring

## Deploy-time rules

The `.wdash` file contains ONLY the `state` object — no `label`, `description`, or `application` keys at root (those belong in `.wdash-meta.xml`).

Critical deploy-time rules:
- `state.dataSourceLinksInfo` must be an **object** (`{}`), not an array.
- `state.gridLayouts[].numColumns` is `24` for modern dashboards.
- **Widget `type` and `parameters` go in the top-level `widgets` dict, NOT in `gridLayouts`.** `gridLayouts[].pages[].widgets[]` entries hold positioning keys: `name`, `row`, `column`, `colspan`, `rowspan`, and optionally `widgetStyle`. Do NOT use `col` (singular) — that triggers `Unrecognized field "col"`.
- Do NOT include `type` on gridLayouts widget entries — rejected with `Unrecognized field "type" (Class GridLayoutWidgetInputRepresentation)`.
- Step `type`: use `saql` or `aggregateflex`. SAQL steps must NOT include `isGlobal`, `receiveFacet`, `datasets`, or `label`.
- Keep widget `parameters` minimal at deploy time: `{ step }` for listselector/valuestable, `{ step, measureField }` for number, `{ step, visualizationType }` for chart. Add everything else via PATCH.

## Proven-accepted PATCH fields per widget type

| Widget type | Accepted in `parameters` |
|-------------|--------------------------|
| `number` | `step`, `measureField`, `title`, `titleColor`, `titleSize`, `numberColor`, `numberSize`, `textAlignment`, `compact`, `showActionMenu`, `exploreLink`, `tooltip: { customizeTooltip: true }`, `interactions: []` |
| `chart` | `step`, `visualizationType`, `title` (object), `titleColor`, `titleSize`, `legend`, `trellis`, `theme`, `showActionMenu`, `exploreLink`, `interactions: []`, `dimensionAxis`, `measureAxis1` — **no `tooltip`** |
| `listselector` | `step`, `title`, `compact`, `displayMode`, `expanded`, `exploreLink`, `filterStyle: { titleColor, valueColor }`, `instant`, `interactions: []`, `showActionMenu` |
| `valuestable` | `step` ONLY — all styling fields rejected. Use `chart` with `visualizationType: "flatTable"` for dark theming |
| `text` | `content` (rich text), `interactions: []` — no styling fields |

**`chart` `title` object shape** (not a plain string):
```json
"title": { "label": "Revenue by Industry", "fontSize": 14, "subtitleFontSize": 11, "align": "left", "subtitleLabel": "" }
```

**`chart` `dimensionAxis` and `measureAxis1`** (make bars draw with labelled axes):
```json
"dimensionAxis": { "showTitle": false, "customSize": "auto", "showAxis": true, "title": "Industry" },
"measureAxis1":  { "sqrtScale": false, "showTitle": false, "showAxis": true, "title": "Revenue ($)", "customDomain": { "showDomain": false } }
```

## Outer PATCH fields

- `gridLayouts[i].style`: `backgroundColor`, `cellSpacingX`, `cellSpacingY`, `gutterColor`, `alignmentX`, `alignmentY`, `fit`.
- `gridLayouts[i].pages[j].widgets[k].widgetStyle`: `backgroundColor`, `borderColor`, `borderEdges`, `borderRadius` (**integer**, e.g. `8`), `borderWidth`.

**Dark theme values** (page bg `#0d1117`, card bg `#161b22`, accent `#4cc9f0`):
```json
"gridLayouts[0].style": { "backgroundColor": "#0d1117", "cellSpacingX": 8, "cellSpacingY": 8, "gutterColor": "#0d1117" }
"widgetStyle": { "backgroundColor": "#161b22", "borderColor": "#30363d", "borderEdges": ["all"], "borderRadius": 8, "borderWidth": 1 }
```

## The SAQL re-encoding trap

When the API stores a dashboard, it HTML-entity-encodes SAQL (e.g. `"` → `&quot;`). Single-level encoding is normal. If you GET → PATCH without decoding, the API encodes again → `&amp;quot;`. After two cycles widgets render "Error" with errorCode 119 `Unexpected character '&'`.

**Always decode every `state.steps[*].query` immediately after a GET, before any mutation + PATCH.**

```javascript
function decodeAll(s) {
  let prev = null;
  while (prev !== s) {
    prev = s;
    s = s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  }
  return s;
}
```

## Dataset references in SAQL

Store name-based load: `q = load "DTS_OpportunityRev"; …`. The dashboard runtime resolves the name internally.

Do NOT use id/version form `q = load "0Fb.../0Fc..."` — the PATCH input rep rejects the `datasets` binding required for id-based loads, so widgets render *"To use the [0Fb...] datasets in the query, add them to the lens first."*

To verify a stored name-based SAQL step: fetch → decode → **swap name for `datasetId/currentVersionId`** → POST to `/wave/query`. The `/wave/query` endpoint cannot resolve names.

## KPI total — always use `group q by all`

```saql
q = load "MyDataset";
q = group q by all;
q = foreach q generate sum('TotalRevenue') as 'TotalRevenue';
```

`foreach` without `group by all` acts as a window function returning one row per source row.

## Query bindings — selection widget driving another step's SAQL

Faceting (`broadcastFacet: true` / `useGlobal: true`) is the default filter path. When a listselector must drive a **specific** SAQL filter in another step — not a global facet — use an explicit query binding.

Proven pattern from working org dashboards:

```saql
q = load "DTS_PipelineByIndustry";
q = filter q by {{column(step_industry_sel.selection, ["Industry"]).asEquality("Account.Industry")}};
q = group q by all;
q = foreach q generate sum('TotalRevenue') as 'TotalRevenue';
```

| Binding | Use when |
|---|---|
| `{{column(step.selection, ["Field"]).asEquality("TargetField")}}` | Selection should become `TargetField == value` (or `in` for multi). Empty selection is a no-op (all rows). **This is the default for a listselector driving a filter.** |
| `{{column(step.selection, ["Field"]).asObject()}}` | Inject the selected values as a SAQL list. Empty selection can yield zero rows — prefer `asEquality` unless you need the raw list. |
| `{{cell(step.selection, 0, "Field").asString()}}` | Single-cell string (e.g. a title). Do **not** use this as the filter itself — null selection breaks the query. |

Rules:
- The selector step aliases the field to the name used in `column(..., ["Industry"])`. If the step projects `'Account.Industry' as 'Industry'`, bind `["Industry"]`, not `["Account.Industry"]`.
- Set `broadcastFacet: false` and `useGlobal: false` on **both** the selector step and the bound data steps. Combining faceting with an explicit binding double-filters.
- Bindings are dashboard-runtime only. `/wave/query` cannot resolve `{{column(...)}}`. To verify a bound step: strip the `filter q by {{...}}` clause (or substitute a literal), swap the dataset name for `id/version`, then POST.
- Store the binding in the SAQL string with raw quotes. Never HTML-encode it yourself — the API encodes on write. Always `decodeAll` before PATCH (see below).

Selector step (no binding on itself):

```saql
q = load "DTS_PipelineByIndustry";
q = group q by 'Account.Industry';
q = foreach q generate 'Account.Industry' as 'Industry';
q = order q by 'Industry' asc;
```

## Filter widgets — use `listselector`

`toggleGroup` does not exist as a stored type. Always use `listselector`.

For a measure-typed field (e.g. CloseMonth as NUMBER): use `foreach` without GROUP BY — `listselector` deduplicates internally:
```saql
q = load "MyDataset";
q = foreach q generate 'CloseMonth' as 'CloseMonth';
q = limit q 1000;
```

## Step shape that renders correctly

```json
{
  "type": "saql",
  "query": "q = load \"<DatasetName>\"; …",
  "broadcastFacet": true,
  "useGlobal": true,
  "selectMode": "single",
  "groups": [],
  "numbers": [],
  "strings": []
}
```

Do NOT include: `datasets`, `start`, `isGlobal`, `receiveFacet`, `visualizationParameters`, `label`.

## Common errors → fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `errorCode 264 "Classic Dashboards have been retired"` on POST | REST POST only creates legacy dashboards | Use Metadata API deploy |
| `Unrecognized field "label"` on deploy | Top-level metadata inside `.wdash` | Move `label`, `description`, `application` to `.wdash-meta.xml` |
| `Can not deserialize … out of START_ARRAY token` | `dataSourceLinksInfo` was an array | Change to empty object `{}` |
| `Unrecognized field "type" (Class GridLayoutWidgetInputRepresentation)` | Widget `type` in gridLayouts entries | Move `type` + `parameters` to top-level `widgets` dict |
| `Unrecognized field "col"` | Used `col` instead of `column` | Rename to `column` |
| All widgets "Error" after PATCH | SAQL re-encoding | Apply `decodeAll` before every PATCH |
| Bound step shows all rows even when a value is selected | Selector uses `broadcastFacet`/`useGlobal` *and* an explicit `{{column}}` binding, or the `column` alias doesn't match the `as 'Industry'` projection | Set both flags `false`; bind the projected alias |
| `/wave/query` 400 on a bound step | Bindings are dashboard-runtime only | Strip `filter q by {{...}}` (or substitute a literal) before posting |
| `Unrecognized field "datasets"` on PATCH | `state.steps[*].datasets` is output-only | Remove from PATCH body |
| Widgets: "To use [0Fb...] datasets … add them to the lens first" | Stored SAQL uses id/version load | Switch to name-based `q = load "<DatasetName>"` |
