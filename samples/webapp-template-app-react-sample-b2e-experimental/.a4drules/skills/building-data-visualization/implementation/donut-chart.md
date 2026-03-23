# Donut / Pie Chart — Implementation Guide

Requires **recharts** (install from the web app directory; see SKILL.md Step 2).

---

## Data structure

Charts expect an array of objects with `name`, `value`, and `color`:

```ts
interface ChartData {
  name: string;
  value: number;
  color: string;
}
```

---

## Donut chart component

Create at `components/DonutChart.tsx`:

```tsx
import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { Card } from "@/components/ui/card";

interface ChartData {
  name: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  title: string;
  data: ChartData[];
}

export const DonutChart: React.FC<DonutChartProps> = ({ title, data }) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const mainPercentage = total > 0 ? Math.round((data[0]?.value / total) * 100) : 0;

  return (
    <Card className="p-4 border-gray-200 shadow-sm flex flex-col">
      <h3 className="text-sm font-medium text-primary mb-2 uppercase tracking-wide">
        {title}
      </h3>

      <div className="relative flex items-center justify-center">
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="text-5xl font-bold text-primary">{mainPercentage}%</div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 grid grid-cols-2 gap-3">
        {data.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-sm text-gray-700">{item.name}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};
```

---

## Key Recharts concepts

| Component | Purpose |
|-----------|---------|
| `ResponsiveContainer` | Wraps chart to make it fill its parent's width |
| `PieChart` | Chart container for pie/donut |
| `Pie` | The data ring; `innerRadius` > 0 makes it a donut |
| `Cell` | Individual segment; accepts `fill` color |
| `paddingAngle` | Gap between segments (degrees) |

### Donut vs Pie

| Property | Donut | Pie |
|----------|-------|-----|
| `innerRadius` | `> 0` (e.g. `70`) | `0` |
| Center label | Yes, positioned absolutely | Not typical |

---

## Preparing chart data from raw records

Transform API data into the `ChartData[]` format before passing to the chart:

```tsx
const CATEGORIES = ["Plumbing", "HVAC", "Electrical"] as const;
const OTHER_LABEL = "Other";
const COLORS = ["#7C3AED", "#EC4899", "#14B8A6", "#06B6D4"];

const chartData = useMemo(() => {
  const counts: Record<string, number> = {};
  CATEGORIES.forEach((c) => (counts[c] = 0));
  counts[OTHER_LABEL] = 0;

  records.forEach((record) => {
    const type = record.category;
    if (CATEGORIES.includes(type as (typeof CATEGORIES)[number])) {
      counts[type]++;
    } else {
      counts[OTHER_LABEL]++;
    }
  });

  return [
    ...CATEGORIES.map((name, i) => ({ name, value: counts[name], color: COLORS[i] })),
    { name: OTHER_LABEL, value: counts[OTHER_LABEL], color: COLORS[CATEGORIES.length] },
  ];
}, [records]);
```

---

## Color palette recommendations

| Use case | Colors |
|----------|--------|
| Categorical (4 items) | `#7C3AED` `#EC4899` `#14B8A6` `#06B6D4` |
| Status (3 items) | `#22C55E` `#F59E0B` `#EF4444` (green/amber/red) |
| Sequential | Use opacity variants of one hue: `#7C3AED` at 100%, 75%, 50%, 25% |

Keep chart colors consistent with the app's design system. Define them as constants, not inline values.

---

## Other chart types

For **bar charts** and **line / area charts**, see `bar-line-chart.md` in this directory.

---

## Accessibility

- Always include a text legend (not just colors).
- Chart should be wrapped in a section with a visible heading.
- For critical data, provide a text summary or table alternative.
- Use sufficient color contrast between segments.
- Consider `prefers-reduced-motion` for chart animations.

---

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Missing `ResponsiveContainer` | Chart won't resize; always wrap in `ResponsiveContainer` |
| Fixed width/height on `PieChart` | Let `ResponsiveContainer` control sizing |
| No legend | Add a grid legend below the chart |
| Inline colors | Extract to constants for consistency |
| No fallback for empty data | Show "No data" message when `data` is empty |
