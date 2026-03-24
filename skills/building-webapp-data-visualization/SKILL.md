---
name: building-webapp-data-visualization
description: "Adds data visualization components (charts, stat cards, KPI metrics) to React pages using Recharts. Use when the user asks to add a chart, graph, donut chart, pie chart, bar chart, stat card, KPI metric, dashboard visualization, or analytics component to the web application."
---

# Data Visualization

## When to Use

Use this skill when:
- Adding charts (donut, pie, bar, line, area) to a dashboard or analytics page
- Displaying KPI/metric stat cards with trend indicators
- Building a dashboard layout with mixed chart types and summary cards

---

## Step 1 — Determine the visualization type

Identify what the user needs:

- **Donut / pie chart** — categorical breakdown (e.g. issue types, status distribution)
- **Bar chart** — comparison across categories or time periods
- **Line / area chart** — trends over time
- **Stat card** — single KPI metric with optional trend indicator
- **Combined dashboard** — stat cards + one or more charts

If unclear, ask:

> "What data should the chart display, and would a donut chart, bar chart, line chart, or stat cards work best?"

---

## Step 2 — Install dependencies

All chart types in this skill use **recharts**. Install once from the web app directory:

```bash
npm install recharts
```

Recharts is built on D3 and provides declarative React components. No additional CSS is needed.

---

## Step 3 — Choose implementation path

Read the corresponding guide:

- **Bar chart** — read `implementation/bar-line-chart.md` (categorical data)
- **Line / area chart** — read `implementation/bar-line-chart.md` (time-series data)
- **Donut / pie chart** — read `implementation/donut-chart.md`
- **Stat card with trend** — read `implementation/stat-card.md`
- **Dashboard layout** — read `implementation/dashboard-layout.md`

---

## Verification

Before completing:

1. Chart renders with correct data and colors.
2. Chart is responsive (resizes with container).
3. Legend labels match the data categories.
4. Stat card trends display correct positive/negative indicators.
5. Run from the web app directory:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed.
