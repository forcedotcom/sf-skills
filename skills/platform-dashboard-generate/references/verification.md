# Verification

Check three layers; a "Succeeded" deploy proves none of them. Arguments, exit codes and JSON output
formats are in `tool-contracts.md`.

## 1. Before deploying: `scripts/validate_dashboard.py`

```bash
python3 "<skill_dir>/scripts/validate_dashboard.py" force-app/main/default/dashboards/Sales/Pipeline.dashboard-meta.xml \
    --reports force-app/main/default/reports
```

Checks: required elements, enum values, invented elements, value types, grid overlap and bounds, widget
limits, filter-column counts, `autoselectColumnsFromReport` consistency, grouping counts per chart type,
indicator colours, text-widget encoding and links, `drillDownUrl`, LWC `componentParameters`, image
`fileAssetName`, record-type filter values, and (for folder files) org-wide shares. With `--reports` it
also checks that each report exists, that every chart's groupings and summaries are really in its
report, that no chart, metric or gauge reads a Tabular report, and that top-N tables will apply their
report's row limit.

## 2. After deploying: `scripts/verify_dashboard.py`

```bash
python3 "<skill_dir>/scripts/verify_dashboard.py" -o <org alias> Sales_Dashboards/Sales_Pipeline --json
python3 "<skill_dir>/scripts/verify_dashboard.py" -o <org alias> Sales_Dashboards/Sales_Pipeline --filter "Close Date=THIS_FISCAL_YEAR"
```

What it calls, through `sf api request rest`:

| Call | Purpose |
|------|---------|
| `GET /analytics/dashboards/<id>/describe` | Widget list, layout positions, filter options; each text widget must `JSON.parse` strictly (what the viewer's browser does). |
| `PUT /analytics/dashboards/<id>[?filter1=<0IC…>]` (body `{}`) | Refresh, optionally for a filtered view. **At most once a minute** per dashboard ("You can't refresh this dashboard more than once in a minute."); the script waits 61 s and retries once, and reports a problem rather than stale data. |
| `GET /analytics/dashboards/<id>/status[?filter1=…]` | Poll until every widget is `IDLE`. |
| `GET /analytics/dashboards/<id>[?filter1=…]` | Per-widget `componentDataStatus`, `errorMessage`, grand totals and (tables) rows. A filtered GET without a filtered refresh returns `NO_DATA` everywhere. |
| `GET /analytics/reports/<id>/describe` | For tables: the source report's row limit, to catch a "top 10" table that returns every row. |

Text output, one line per widget: order and grid position (`#3 r6c4`), type, title, status and labelled
grand totals (`s!AMOUNT=2,577,399, RowCount=336`; `s!` sum, `a!` average).

- `ok` / `DATA`: renders.
- `--` / `NO_DATA` with no message: the report returned no rows (report filters, running-user access, a
  dashboard-filter value that matches nothing, or no refresh yet).
- `BAD`: viewers see the quoted error instead of the widget (`errors-and-troubleshooting.md`), a text
  widget cannot be parsed, a widget has no chart type, or a table returns more rows than its report's limit.
- With `--filter`: a warning when every widget totals 0, usually a filter option that matches nothing
  (record types written as names).
- Text widgets are checked through describe. Image and LWC widgets are listed but cannot be checked.

## 3. Look at it once

Open `/lightning/r/Dashboard/<01Z…Id>/view` and check layout: clipped text, unreadable grouped axes,
legends squeezing small charts, metrics in an unintended colour. The API cannot see these.

## Round-trip check (optional)

Retrieve the dashboard after deploying and diff it with your file. The platform adds defaults
(`<groupingSortProperties/>`, `showRange`, `dashboardType`, `owner`, `runningUser` without the sandbox
suffix); anything else that differs is worth a look.
