# Tables

Use the **Lightning table** (`FlexTable`). The classic `Table` still works but has fewer options.

## Lightning table (FlexTable)

```xml
<dashboardComponent>
    <autoselectColumnsFromReport>false</autoselectColumnsFromReport>
    <componentType>FlexTable</componentType>
    <flexComponentProperties>
        <decimalPrecision>-1</decimalPrecision>
        <flexTableColumn>
            <reportColumn>OPPORTUNITY_NAME</reportColumn>
            <showSubTotal>false</showSubTotal>
            <showTotal>false</showTotal>
            <type>detail</type>
        </flexTableColumn>
        <flexTableColumn>
            <breakPoint1>20000.0</breakPoint1>
            <breakPoint2>50000.0</breakPoint2>
            <breakPointOrder>0</breakPointOrder>
            <highRangeColor>29035</highRangeColor>
            <lowRangeColor>12728628</lowRangeColor>
            <midRangeColor>16758621</midRangeColor>
            <reportColumn>AMOUNT</reportColumn>
            <showSubTotal>false</showSubTotal>
            <showTotal>true</showTotal>
            <type>detail</type>
        </flexTableColumn>
        <flexTableSortInfo>
            <sortColumn>AMOUNT</sortColumn>
            <sortOrder>2</sortOrder>
        </flexTableSortInfo>
        <hideChatterPhotos>true</hideChatterPhotos>
        <useReportTableSetting>false</useReportTableSetting>
    </flexComponentProperties>
    <groupingSortProperties/>
    <header>Top 10 open opportunities</header>
    <report>Sales_Reports/Top_10_Open_Opps</report>
</dashboardComponent>
```

### Columns

| `type` | `reportColumn` | Use |
|--------|----------------|-----|
| `detail` | a report column (`OPPORTUNITY_NAME`, `Opportunity.Field__c`) | Record list |
| `grouping` | a grouping field (`STAGE_NAME`) | Grouped table, up to 2 levels |
| `aggregate` | `RowCount`, or **prefix + column**: `s!AMOUNT` (sum), `a!AMOUNT` (average), `mx!AMOUNT` (max), `m!AMOUNT` (min), or `FORMULA1` | Summary columns |

- Types are lower case. Aggregate columns use the Analytics-API prefixes (`s!…`), **unlike** `chartSummary`
  which uses `<aggregate>Sum</aggregate><column>AMOUNT</column>`.
- `detail` columns may be **any field of the report type**, not only the report's own columns
  (`TYPE`, `LEAD_SOURCE` on an Opportunity report that doesn't show them both work). A name the report
  type does not have fails the deploy: "NOT_A_COLUMN column is missing".
- Aggregate columns are calculated by the table itself: `mx!AMOUNT` works even when the report only
  summarises `AMOUNT` with Sum. (Charts are different: they need the report's summary.)
- Aggregate columns display in the report's aggregate order, not XML order.
- `showTotal` adds a totals row; `showSubTotal` adds subtotals on grouped tables.
- UI limits: **10 columns, 200 rows** (not checked on deploy — an 11-column table deploys).

### Sort (required)

- `<flexTableSortInfo>` is **required** — without it the deploy fails with "Sort info should be always
  present". `sortOrder`: **`1` = ascending, `2` = descending**.
- `sortColumn` must be **one of the table's own columns**. A `sortColumn` that is not a table column
  deploys and is silently dropped (no sort, and no row limit — see below).
- With only `sortOrder` and no `sortColumn`, rows come back in no particular order.

### Top N / row limits — read before building a "top 10" table

A table does **not** simply inherit its report's row limit. Tested on a report with
`<rowLimit>10</rowLimit>` sorted by `AMOUNT` descending:

| Table setting | Rows returned |
|---------------|---------------|
| `sortColumn` `AMOUNT`, `sortOrder` `2` | **10** — the 10 largest (what you want) |
| `sortColumn` `OPPORTUNITY_NAME`, `sortOrder` `1` | 10 — but the first 10 *names*, not the largest |
| `sortOrder` only, no `sortColumn` | **all** rows (336) |
| table without the report's sort column, `sortOrder` only | **all** rows |
| `useReportTableSetting` `true` | 10, by the report's own sort |

So for a top-N table: include the ranking column in the table and set `sortColumn` to it with the
direction you want (`2` = largest/newest first). The row limit applies, and the table's sort picks the
N rows. `maxValuesDisplayed` is **not** allowed on a FlexTable ("The dashboard componentType FlexTable
cannot use the maxValuesDisplayed attribute") — the row limit has to come from the report.
`verify_dashboard.py` prints the row count of each table and warns when a row-limited report returns
more rows than its limit.

Sizing: a 12 × 8 cell shows about 7 rows without scrolling; allow about one grid row per table row plus
one (10 rows → `rowSpan` 11).

### Conditional highlighting

Per numeric column: `breakPoint1`, `breakPoint2`, `breakPointOrder` (0, 1, … when several columns are
highlighted), and `lowRangeColor` / `midRangeColor` / `highRangeColor` as **decimal RGB integers**:

| Hex | Integer |
|-----|---------|
| `#C23934` (red) | `12728628` |
| `#FFB75D` (amber) | `16758621` |
| `#00716B` (green) | `29035` |

Convert: `int("C23934", 16)` → `12728628`.

### Table settings from report

`<useReportTableSetting>true</useReportTableSetting>` (API 65+) runs the table with the report's own
columns, groupings, formulas, buckets, sort and row limit — the `flexTableColumn` list is then not what
viewers see. Use it when the report already looks right; otherwise build the columns yourself.
UI limit: 3 such tables per dashboard (not checked on deploy).

## Classic table (`Table`)

```xml
<dashboardComponent>
    <autoselectColumnsFromReport>true</autoselectColumnsFromReport>
    <componentType>Table</componentType>
    <groupingSortProperties/>
    <header>Pipeline by stage</header>
    <indicatorHighColor>#00716B</indicatorHighColor>
    <indicatorLowColor>#C23934</indicatorLowColor>
    <indicatorMiddleColor>#FFB75D</indicatorMiddleColor>
    <report>Sales_Reports/Opps_by_Stage</report>
    <sortBy>RowLabelAscending</sortBy>
</dashboardComponent>
```

With `autoselectColumnsFromReport` `true` it shows the first grouping and first summary. For explicit
columns set it to `false` and add `<dashboardTableColumn>` entries (`column`, `aggregateType`,
`calculatePercent`, `decimalPlaces`, `showSubTotal`, `showTotal`, `sortBy`). Indicator colours are required.
