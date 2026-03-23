# Bar & Line / Area Chart — Implementation Guide

Requires **recharts** (install from the web app directory; see SKILL.md Step 2).

---

## Data shapes

### Time-series (line / area chart)

Use when data represents a trend over time or ordered sequence.

```ts
interface TimeSeriesDataPoint {
  x: string;   // date or label on the x-axis
  y: number;   // numeric value
}
```

Map raw fields to this shape: e.g. `date` → `x`, `revenue` → `y`.

### Categorical (bar chart)

Use when data compares discrete categories.

```ts
interface CategoricalDataPoint {
  name: string;   // category label
  value: number;  // numeric value
}
```

Map raw fields to this shape: e.g. `product` → `name`, `sales` → `value`.

### How to decide

| Signal | Type |
|--------|------|
| "over time", "trend", date-like keys | Time-series → line chart |
| "by category", "by X", label-like keys | Categorical → bar chart |

---

## Theme colors

Pick a theme based on the data's sentiment:

| Theme | Stroke / Fill | When to use |
|-------|---------------|-------------|
| `green` | `#22c55e` | Growth, gain, positive trend |
| `red` | `#ef4444` | Decline, loss, negative trend |
| `neutral` | `#6366f1` | Default or mixed data |

Define colors as constants — do not use inline hex values.

```ts
const THEME_COLORS = {
  red: "#ef4444",
  green: "#22c55e",
  neutral: "#6366f1",
} as const;

type ChartTheme = keyof typeof THEME_COLORS;
```

---

## Line chart component

Create at `components/LineChart.tsx` (or colocate with the page):

```tsx
import React from "react";
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const THEME_COLORS = {
  red: "#ef4444",
  green: "#22c55e",
  neutral: "#6366f1",
} as const;

type ChartTheme = keyof typeof THEME_COLORS;

interface TimeSeriesDataPoint {
  x: string;
  y: number;
}

interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  theme?: ChartTheme;
  title?: string;
  className?: string;
}

export function TimeSeriesChart({
  data,
  theme = "neutral",
  title,
  className = "",
}: TimeSeriesChartProps) {
  if (data.length === 0) {
    return <p className="text-muted-foreground text-center py-8">No data to display</p>;
  }

  const color = THEME_COLORS[theme];

  return (
    <div className={className}>
      {title && (
        <h3 className="text-sm font-medium text-primary mb-2 uppercase tracking-wide">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={300}>
        <RechartsLineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="y" stroke={color} strokeWidth={2} dot={false} />
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Bar chart component

Create at `components/BarChart.tsx` (or colocate with the page):

```tsx
import React from "react";
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const THEME_COLORS = {
  red: "#ef4444",
  green: "#22c55e",
  neutral: "#6366f1",
} as const;

type ChartTheme = keyof typeof THEME_COLORS;

interface CategoricalDataPoint {
  name: string;
  value: number;
}

interface CategoricalChartProps {
  data: CategoricalDataPoint[];
  theme?: ChartTheme;
  title?: string;
  className?: string;
}

export function CategoricalChart({
  data,
  theme = "neutral",
  title,
  className = "",
}: CategoricalChartProps) {
  if (data.length === 0) {
    return <p className="text-muted-foreground text-center py-8">No data to display</p>;
  }

  const color = THEME_COLORS[theme];

  return (
    <div className={className}>
      {title && (
        <h3 className="text-sm font-medium text-primary mb-2 uppercase tracking-wide">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={300}>
        <RechartsBarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Area chart variant

For a filled area chart (useful for volume-over-time), swap `Line` for `Area`:

```tsx
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

<ResponsiveContainer width="100%" height={300}>
  <AreaChart data={data}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="x" />
    <YAxis />
    <Tooltip />
    <Area type="monotone" dataKey="y" stroke={color} fill={color} fillOpacity={0.2} />
  </AreaChart>
</ResponsiveContainer>
```

---

## Chart container wrapper

Wrap any chart in a styled card for consistent spacing:

```tsx
import { Card } from "@/components/ui/card";

interface ChartContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function ChartContainer({ children, className = "" }: ChartContainerProps) {
  return (
    <Card className={`p-4 border-gray-200 shadow-sm ${className}`}>
      {children}
    </Card>
  );
}
```

Usage:

```tsx
<ChartContainer>
  <TimeSeriesChart data={monthlyData} theme="green" title="Monthly Revenue" />
</ChartContainer>
```

---

## Preparing raw data

Map API responses to the expected shape before passing to the chart:

```tsx
const timeSeriesData = useMemo(
  () => apiRecords.map((r) => ({ x: r.date, y: r.revenue })),
  [apiRecords],
);

const categoricalData = useMemo(
  () => apiRecords.map((r) => ({ name: r.product, value: r.sales })),
  [apiRecords],
);
```

---

## Key Recharts concepts

| Component | Purpose |
|-----------|---------|
| `ResponsiveContainer` | Wraps chart to fill parent width |
| `CartesianGrid` | Background grid lines |
| `XAxis` / `YAxis` | Axis labels; `dataKey` maps to the data field |
| `Tooltip` | Hover info |
| `Legend` | Series labels |
| `Line` | Line series; `type="monotone"` for smooth curves |
| `Bar` | Bar series; `radius` rounds top corners |
| `Area` | Filled area; `fillOpacity` controls transparency |

---

## Accessibility

- Always include a text legend (not just colors).
- Chart should be wrapped in a section with a visible heading.
- For critical data, provide a text summary or table alternative.
- Use sufficient color contrast between the chart stroke/fill and background.
- Consider `prefers-reduced-motion` for chart animations.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Missing `ResponsiveContainer` | Chart won't resize; always wrap |
| Fixed width/height on chart | Let `ResponsiveContainer` control sizing |
| No empty-data handling | Show "No data" message when `data.length === 0` |
| Inline colors | Extract to `THEME_COLORS` constant |
| Using raw Recharts for every chart type | Use `DonutChart` (see `donut-chart.md`) for pie/donut |
