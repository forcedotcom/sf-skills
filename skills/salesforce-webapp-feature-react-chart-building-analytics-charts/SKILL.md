---
name: salesforce-webapp-feature-react-chart-building-analytics-charts
description: Add or change charts from raw data. Use when the user asks for a chart, graph, or analytics visualization from JSON/data.
---

# Analytics charts (workflow)

When the user wants a chart or visualization from data, follow this workflow. Charts use **Recharts** via the **AnalyticsChart** component.

## Dependencies

Ensure the following package is installed in the project:

```bash
npm install recharts
```

## 1. Interpret data type

- **Time-series**: data over time or ordered (dates, timestamps). Use a line chart. Raw shape often has date-like keys and a numeric value.
- **Categorical**: data by category (labels, segments). Use a bar chart. Raw shape often has a category name and a numeric value.

If the user says "over time", "trend", or uses date-like keys → time-series. If they say "by category", "by X", or use label-like keys → categorical.

## 2. Map data to chart shape

- **Time-series**: produce `[{ x: string, y: number }, ...]` (e.g. map `date`→`x`, `value`→`y`).
- **Categorical**: produce `[{ name: string, value: number }, ...]` (e.g. map `category`→`name`, `total`→`value`).

See [schema-mapping.md](docs/schema-mapping.md) for examples.

## 3. Choose theme

- **red**: declining, loss, negative trend.
- **green**: growth, gain, positive trend.
- **neutral**: default or mixed.

## 4. Generate and place the chart

- Use **AnalyticsChart** with `chartType` (`"time-series"` or `"categorical"`), `data` (mapped array), `theme`, and optional `title`. Wrap in **ChartContainer** if the app uses it for chart blocks.
- Insert the chart inside the existing app (e.g. main content or a route), not as the entire page.
