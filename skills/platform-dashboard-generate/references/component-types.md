# Component Types

Every widget is a `<dashboardGridComponents>` cell holding one `<dashboardComponent>`.
`componentType` decides which other elements are needed. All types below were deployed and
rendered on API 68.0 unless marked.

## Which type for which question

| Question | Type | Groupings | Summaries |
|----------|------|-----------|-----------|
| One headline number (KPI) | `Metric` | 0 | 1 |
| Progress towards a target | `Gauge` | 0 | 1 (+ `gaugeMin`/`gaugeMax`) |
| Compare categories | `Bar` (long labels) / `Column` | 1 | 1 |
| Compare categories split by a 2nd field | `BarStacked` / `ColumnStacked` (prefer) or `…Grouped` | 2 | 1 |
| Share of a whole across a 2nd field | `BarStacked100` / `ColumnStacked100` | 2 | 1 |
| Trend over time | `Line` (date grouping) / `LineCumulative` (running total) | 1 | 1 |
| Several trends | `LineGrouped` / `LineGroupedCumulative` | 2 | 1 |
| Parts of a whole (≤ 6 slices) | `Donut` (`showTotal` puts the total in the centre) | 1 | 1 |
| Pipeline stages | `Funnel` | 1 | 1 |
| Relationship between two measures | `Scatter` (one dot per group) / `ScatterGrouped` | 1 / 2 | 2 (`x` and `y`) |
| Bars plus a line on a 2nd axis | `ColumnLine` / `ColumnLineGrouped` / `ColumnLineStacked` | 1 / 2 / 2 | 2 (`y` and `y2`) |
| Records or grouped numbers | `FlexTable` (Lightning table) — see `tables.md` | 0–2 | any |
| Heading, notes, links | `RichText` — see `rich-text-image-lwc.md` | – | – |
| Logo / picture | `Image` — see `rich-text-image-lwc.md` | – | – |
| Custom visual | `LightningWebComponent` — see `rich-text-image-lwc.md` | – | – |

Other enum values: `Pie` (avoid, below), `Table` (classic table, `tables.md`), `VisualforcePage`
(`page`, `pageHeightInPixels`), `Scontrol` (legacy), `PulseMetric`.

## Rendering gotchas (deploy succeeds, result is wrong)

- **`Pie` renders as a ring without a centre total.** The Lightning builder has no pie chart. Use `Donut`.
- **`ColumnLineStacked100` drops the line.** The `y2` measure is not drawn; the widget looks exactly like
  `ColumnStacked100`. Use `ColumnLineStacked` or two widgets.
- **`expandOthers` is inverted from what it sounds like:** `false` merges groups ≤ 3% of the total into an
  "Other" slice; `true` shows every group.
- **Grouped charts with a busy 2nd grouping** (8+ values) produce unreadable axes (one label per
  sub-bar). Prefer the stacked variant, or `maxValuesDisplayed`.
- **Two `groupingColumn`s on a single-series type** (`Bar`, `Column`, `Line`, `Donut`, `Funnel`) fails
  to deploy with the misleading "not compatible with the autoselectColumnsFromReport mode for Bar".
- The describe API reports `ColumnLine*` as visualization type `Column` and `BarStacked100` as `Bar`,
  so you cannot tell the variants apart from describe output.

## Report chart type ↔ dashboard component type

A report's own `<chart>` and a dashboard widget use **different names** for the same chart. Use
these when converting, or set `useReportChart` to `true` to reuse the report's chart as-is
(the report must define one, or the widget shows "You must define a chart for the source report
used for this component.").

| Report `<chartType>` | Dashboard `<componentType>` |
|----------------------|-----------------------------|
| `HorizontalBar` | `Bar` |
| `HorizontalBarGrouped` | `BarGrouped` |
| `HorizontalBarStacked` | `BarStacked` |
| `HorizontalBarStackedTo100` | `BarStacked100` |
| `VerticalColumn` | `Column` |
| `VerticalColumnGrouped` | `ColumnGrouped` |
| `VerticalColumnStacked` | `ColumnStacked` |
| `VerticalColumnStackedTo100` | `ColumnStacked100` |
| `Line` | `Line` |
| `LineGrouped` | `LineGrouped` |
| `LineCumulative` | `LineCumulative` |
| `LineCumulativeGrouped` | `LineGroupedCumulative` (word order swaps) |
| `Pie` / `Donut` / `Funnel` | `Pie` / `Donut` / `Funnel` |
| `Scatter` / `ScatterGrouped` | `Scatter` / `ScatterGrouped` |

## Source report requirements

| Widget | Report format | Notes |
|--------|---------------|-------|
| Charts | Summary or Matrix | Groupings must be report groupings (for Matrix: down grouping, then across). Summaries must be report summaries (`aggregateTypes` on the column), `RowCount`, or a custom summary formula (`FORMULA1`). |
| Metric / Gauge | **Summary or Matrix only** | Uses the grand total. A Tabular source deploys, then shows "This report cannot be used as the source for this component. If it is a summary or matrix report, add one or more groupings in the report. …" — add any grouping (e.g. `STATUS`) to the report. |
| FlexTable | Any; Tabular for record lists | For a top-N list the table must sort by a table column — see `tables.md` "Top N / row limits". |
| Any chart | **Not** a row-limited Tabular report | Deploys, then shows "This row-limited tabular report cannot be used as the source for this component." |

A chart summary or grouping the report does not have deploys fine and then shows **"One or more of the
fields selected in the component is no longer available in the report."**

### Finding report column names

Report XML uses report-type column names, not field API names. When the report does not exist yet,
list the valid names for a report type with
`sf api request rest "/services/data/v66.0/analytics/reportTypes/<ReportType>" -o <org>`
(e.g. `CaseList`, `Opportunity`, or a custom report type `Name__c`). Useful standard names that are easy
to miss: `CLOSED` (a checkbox — "open" records are `CLOSED` equals `0`, which also excludes statuses like
Merged), `ORIGIN`, `CREATED_DATEONLY`, `RECORDTYPE`, `FULL_NAME` (opportunity owner), `OWNER` (case owner).
