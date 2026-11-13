# Charts: Measures, Groupings, Sorting

## chartSummary (what is measured)

```xml
<chartSummary>
    <aggregate>Sum</aggregate>      <!-- Sum | Average | Maximum | Minimum (also Median, Unique) -->
    <axisBinding>y</axisBinding>    <!-- y | y2 (combo line) | x (scatter) -->
    <column>AMOUNT</column>         <!-- report column, RowCount, or FORMULA1… -->
</chartSummary>
```

- `RowCount` and custom summary formulas (`FORMULA1`, `FORMULA2`, … from the report's `<aggregates>`)
  take **no** `<aggregate>`. `Sum` + `RowCount` fails ("not compatible with the autoselectColumnsFromReport mode").
- The column must be summarised in the report with that aggregate (`<aggregateTypes>Sum</aggregateTypes>`
  on the report column). Otherwise the deploy succeeds and the widget shows "One or more of the fields
  selected in the component is no longer available in the report."
- Column names are the **report's** names: standard types use platform names (`AMOUNT`, `CLOSE_DATE`,
  `STAGE_NAME`, `RECORDTYPE`, `FULL_NAME`); custom fields `Object__c.Field__c` / `Opportunity.Field__c`;
  custom report types `$` paths (`Campaign.Opportunities__r$Amount`); buckets `BucketField_12345678`.
- Repeat `chartSummary` for combos and scatter:
  - `ColumnLine*`: first summary `y` (columns), second `y2` (line on a right-hand axis).
  - `Scatter*`: one `x` and one `y` summary; each group becomes a dot.

## groupingColumn (what is compared)

- One `<groupingColumn>` per level, in report order (down grouping first, then the second down
  grouping or, for a Matrix report, the across grouping).
- Date groupings use the report's date granularity (month, fiscal quarter …); set it in the report.
- Two levels require a grouped / stacked / 100% / grouped-line / grouped-scatter / grouped-combo type.

## Sorting

Sort is held in **two** places; keep them consistent.

```xml
<groupingSortProperties>
    <groupingSorts>
        <groupingLevel>g1</groupingLevel>   <!-- g1 = first grouping, g2 = second -->
        <sortColumn>RowCount</sortColumn>   <!-- present = sort by this measure; absent = sort by label -->
        <sortOrder>d</sortOrder>            <!-- a = ascending, d = descending -->
    </groupingSorts>
</groupingSortProperties>
<sortBy>RowValueDescending</sortBy>          <!-- RowLabelAscending | RowLabelDescending | RowValueAscending | RowValueDescending -->
```

| Want | groupingSorts | sortBy |
|------|---------------|--------|
| Alphabetical (default) | omit, or `g1` + `a` | `RowLabelAscending` |
| Biggest first | `g1` + `sortColumn` (measure) + `d` | `RowValueDescending` |
| Keep the report's sort | `g1` + `<inheritedReportGroupingSort>r</inheritedReportGroupingSort>` | `RowLabelAscending` |

- `<groupingSortProperties/>` (empty) is valid and is what the editor writes for unsorted widgets.
- Editor-built files also contain `inheritedReportGroupingSort` `i`; prefer the forms above when writing new XML.
- For a second level add another `groupingSorts` with `g2` (two-level sorting).
- `sortLegendValues` `true` sorts the legend alphabetically/numerically.

## Display options

| Element | Values / effect |
|---------|-----------------|
| `header` / `title` / `footer` | Widget title (≤ 80; not shown on text widgets) / subtitle (≤ 40) / footer (≤ 255). |
| `expandOthers` | `false` merges groups ≤ 3% of the total into "Other" (Donut, Funnel); `true` shows every group. |
| `componentChartTheme` | `light` / `dark` override for one widget. |
| `useReportChart` | `true` = use the report's own chart; the report must define a chart. |
| `displayUnits` | `Auto` = 1.2K / 2.6M; `Integer` = full; `Hundreds` … `Trillions`. Omitted = full number. |
| `decimalPrecision` | `-1` default, `0`–`5`. |
| `showValues` | Value labels on bars/points. |
| `showPercentage` | Percentages on Donut / Funnel / Pie (and Gauge). |
| `showTotal` | Total in the centre of a Donut; value on a Gauge. |
| `legendPosition` | `Bottom`, `Right`, `OnChart`. |
| `maxValuesDisplayed` | Plot only the first N groups (after sorting). Charts only; rejected on FlexTable (see `tables.md`). |
| `chartAxisRange` | `Auto`, or `Manual` with `chartAxisRangeMin` / `chartAxisRangeMax`. |
| `enableHover` | Tooltips. |
| `showPicturesOnCharts` | Chatter photos on horizontal bar charts grouped by user. |
| `drillEnabled` | `true` = clicking a bar opens the report filtered to it. |
| `drillDownUrl` | Custom link on click; overrides drill settings. Use a relative `/lightning/…` path. An absolute `https://` URL needs the user's explicit agreement; other schemes are refused by the validator. Never put data in the URL. |

## Matrix and formula sources

- Matrix report: `groupingColumn` = down grouping then across grouping; works with stacked / grouped types.
- Custom summary formula as the measure: `<chartSummary><axisBinding>y</axisBinding><column>FORMULA1</column></chartSummary>`.
