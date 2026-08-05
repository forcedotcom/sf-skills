# Chart Types Reference

Charts can only be added to Summary or Matrix reports. A Tabular report with a `<chart>` element will fail deployment.

## Available Chart Types

| Chart Type | Category | Notes |
|-----------|----------|-------|
| `HorizontalBar` | Bar | Single-series horizontal bar |
| `HorizontalBarGrouped` | Bar | Grouped horizontal bars (requires secondaryGroupingColumn) |
| `HorizontalBarStacked` | Bar | Stacked horizontal bars |
| `HorizontalBarStackedTo100` | Bar | Stacked to 100% |
| `VerticalColumn` | Column | Single-series vertical column |
| `VerticalColumnGrouped` | Column | Grouped vertical columns |
| `VerticalColumnStacked` | Column | Stacked vertical columns |
| `VerticalColumnStackedTo100` | Column | Stacked to 100% |
| `Line` | Line | Single-series line |
| `LineGrouped` | Line | Grouped line chart |
| `LineCumulative` | Line | Cumulative line chart |
| `LineCumulativeGrouped` | Line | Grouped cumulative line |
| `Pie` | Circular | Pie chart |
| `Donut` | Circular | Donut chart |
| `Funnel` | Other | Funnel chart |
| `Scatter` | Other | Scatter chart |
| `ScatterGrouped` | Other | Grouped scatter chart |

## legendPosition

Only use `legendPosition` with grouped/stacked chart types (e.g., `VerticalColumnGrouped`, `HorizontalBarStacked`). Do NOT include it for simple single-series charts like `VerticalColumn`, `HorizontalBar`, `Pie`, `Donut`.

Valid values: `Right`, `Bottom`, `OnChart`
