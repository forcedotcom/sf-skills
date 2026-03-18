---
paths:
  - "**/*.tsx"
  - "**/components/**/*.ts"
---

# Analytics charts (standards)

When adding or editing chart UI in this project, follow these conventions.

## Components and library

- Use the shared **AnalyticsChart** component (and **ChartContainer** when a framed block is needed). Do not use raw Recharts components for standard line or bar charts.
- The project must have **recharts** installed (`npm install recharts`).

## Data shape

- **Time-series** (line): data must be an array of `{ x: string, y: number }`. Map raw fields (e.g. `date`, `value`) to these keys before passing to the chart.
- **Categorical** (bar): data must be an array of `{ name: string, value: number }`. Map raw fields (e.g. `category`, `total`) accordingly.

## Theming

- Use only the **theme** prop on AnalyticsChart: `red` (decline/loss), `green` (growth/gain), `neutral` (default or mixed). Do not introduce ad-hoc color schemes for these semantics.

## Placement

- Render charts inside the existing application frame (e.g. main content or a route). Do not replace the full app shell with a single chart.
