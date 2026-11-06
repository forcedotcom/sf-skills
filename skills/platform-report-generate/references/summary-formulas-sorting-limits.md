# Custom Summary Formulas, Sorting & Row Limits

Covers three report-metadata capabilities beyond the core columns/groupings/filters:
custom summary formulas (`<aggregates>`), report and grouping sort
(`<sortColumn>` / `<sortOrder>` / grouping `<sortType>`), and tabular row limit /
top-N (`<rowLimit>`). See Rules 16–18 in `SKILL.md`.

## Custom Summary Formulas (`<aggregates>`)

Custom summary formulas (CSFs) compute a value from a report's summaries. They are valid
**only** in `Summary`, `Matrix`, and `Joined` reports.

**Summary report** (no `<acrossGroupingContext>`):

```xml
<aggregates>
    <calculatedFormula>AMOUNT:SUM / RowCount</calculatedFormula>
    <datatype>currency</datatype>
    <developerName>FORMULA1</developerName>
    <downGroupingContext>GRAND_SUMMARY</downGroupingContext>
    <isActive>true</isActive>
    <isCrossBlock>false</isCrossBlock>
    <masterLabel>Avg Deal Size</masterLabel>
    <scale>2</scale>
</aggregates>
```

**Matrix report only**: add `<acrossGroupingContext>` next to `<downGroupingContext>`:

```xml
    <acrossGroupingContext>GRAND_SUMMARY</acrossGroupingContext>
    <downGroupingContext>GRAND_SUMMARY</downGroupingContext>
```

| Sub-element | Notes |
|-------------|-------|
| `<developerName>` | Unique per report (`FORMULA1`, `FORMULA2`, …). Referenced by charts and grouping sort (`<sortByName>` with `<sortType>CustomSummaryFormula</sortType>`). |
| `<calculatedFormula>` | Uses summary references such as `AMOUNT:SUM`, `AMOUNT:AVG`, and `RowCount`. |
| `<datatype>` | `number`, `currency`, or `percent`. |
| `<scale>` | Decimal places (0–18). |
| `<downGroupingContext>` | `GRAND_SUMMARY` or a 0-based grouping level (`0`, `1`, …). Required. |
| `<acrossGroupingContext>` | Matrix only; `GRAND_SUMMARY` or a 0-based across-grouping level. |
| `<isCrossBlock>` | `true` only for cross-block formulas in Joined reports. |

Include `<acrossGroupingContext>` **only** for Matrix reports. On a Summary report it fails
to deploy with `acrossBreakContext not allowed for summary reports, only for matrix reports`
— use `<downGroupingContext>` alone. A grouping context that references a level the report
does not have is also a deployment failure.

## Sorting (`<sortColumn>`, `<sortOrder>`, grouping `<sortType>`)

**Sort detail rows** (Tabular, or the detail area of Summary/Matrix):

```xml
<sortColumn>AMOUNT</sortColumn>
<sortOrder>Desc</sortOrder>
```

The `<sortColumn>` must be a platform column name that also appears in `<columns>`.
`<sortOrder>` is case-sensitive — `Asc` or `Desc`.

**Sort a grouping by its own value:**

```xml
<groupingsDown>
    <field>STAGE_NAME</field>
    <sortOrder>Asc</sortOrder>
</groupingsDown>
```

**Sort a grouping by a summary** (e.g. show the group with the biggest total first):

```xml
<groupingsDown>
    <field>STAGE_NAME</field>
    <sortType>Aggregate</sortType>
    <sortByName>AMOUNT</sortByName>
    <sortOrder>Desc</sortOrder>
</groupingsDown>
```

With `<sortType>Aggregate</sortType>`, `<sortByName>` = a summarized column name (e.g.
`AMOUNT`, which must carry an `<aggregateTypes>`, or `RowCount`). Do NOT use the Analytics
REST `s!` prefix here — in report metadata the plain column name is required. Default
`<sortType>` is `Column` (sort by the grouping's own value).

**Sort a grouping by a custom summary formula**: use `<sortType>CustomSummaryFormula</sortType>`
with the CSF's `<developerName>`:

```xml
<groupingsDown>
    <field>STAGE_NAME</field>
    <sortType>CustomSummaryFormula</sortType>
    <sortByName>FORMULA1</sortByName>
    <sortOrder>Desc</sortOrder>
</groupingsDown>
```

Do NOT pair `<sortType>Aggregate</sortType>` with a CSF name: it deploys without error but
the sort silently falls back to the grouping field.

## Row Limit / Top-N (`<rowLimit>`)

Row Limit restricts a **Tabular** report to the top or bottom N rows — commonly used for
"Top N" dashboard table components. It requires a sort column that defines the ranking.

```xml
<format>Tabular</format>
<rowLimit>10</rowLimit>
<sortColumn>AMOUNT</sortColumn>
<sortOrder>Desc</sortOrder>
```

- `Desc` → top N; `Asc` → bottom N.
- Valid only on `Tabular`; requires `<sortColumn>` + `<sortOrder>`.
- Value 1–99.

Setting `<rowLimit>` on a Summary/Matrix report, or without a sort column, fails to deploy.
