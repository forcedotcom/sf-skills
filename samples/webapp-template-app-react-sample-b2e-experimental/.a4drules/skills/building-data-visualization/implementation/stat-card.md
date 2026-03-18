# Stat Card — Implementation Guide

## What is a stat card

A stat card displays a single KPI metric with an optional trend indicator. Used on dashboards to show at-a-glance numbers like "Total Properties: 42 (+10%)".

---

## Component interface

```ts
interface StatCardProps {
  title: string;
  value: number | string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  subtitle?: string;
  onClick?: () => void;
}
```

---

## StatCard component

Create at `components/StatCard.tsx`:

```tsx
import React from "react";
import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number | string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  subtitle?: string;
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, trend, subtitle, onClick }) => {
  return (
    <Card
      className={`p-4 border-gray-200 shadow-sm relative ${
        onClick ? "cursor-pointer hover:shadow-lg transition-shadow" : ""
      }`}
      onClick={onClick}
    >
      <div className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
        <div className="flex items-baseline gap-3">
          <p className="text-4xl font-bold text-primary">{value}</p>
          {trend && (
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-medium ${
                trend.isPositive
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-pink-100 text-pink-800"
              }`}
            >
              {trend.isPositive ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <TrendingDown className="w-4 h-4" />
              )}
              {Math.abs(trend.value)}%
            </span>
          )}
        </div>
        {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
      </div>
    </Card>
  );
};
```

This version uses Lucide icons (`TrendingUp`/`TrendingDown`) instead of custom SVGs for portability across projects.

---

## Layout: stat card grid

Display stat cards in a responsive grid:

```tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
  <StatCard
    title="Total Properties"
    value={metrics.totalProperties}
    trend={{ value: 10, isPositive: true }}
    subtitle="Last month total 38"
  />
  <StatCard
    title="Units Available"
    value={metrics.unitsAvailable}
    trend={{ value: 5, isPositive: false }}
    subtitle="Last month total 12/42"
  />
  <StatCard
    title="Occupied Units"
    value={metrics.occupiedUnits}
    trend={{ value: 8, isPositive: true }}
    subtitle="Last month total 27"
  />
</div>
```

---

## Computing trend values

Calculate trends from current vs previous period:

```ts
const trends = useMemo(() => {
  const previousTotal = metrics.totalProperties - Math.round(metrics.totalProperties * 0.1);
  const trendPercent = previousTotal > 0
    ? Math.round(((metrics.totalProperties - previousTotal) / previousTotal) * 100)
    : 0;

  return {
    value: Math.abs(trendPercent),
    isPositive: trendPercent >= 0,
  };
}, [metrics]);
```

---

## Trend badge color conventions

| Trend | Background | Text | Meaning |
|-------|------------|------|---------|
| Positive (up) | `bg-emerald-100` | `text-emerald-800` | Growth, improvement |
| Negative (down) | `bg-pink-100` | `text-pink-800` | Decline, concern |
| Neutral | `bg-gray-100` | `text-gray-600` | No change |

---

## Accessibility

- Card uses `cursor-pointer` and `hover:shadow-lg` only when `onClick` is provided.
- Trend icons have implicit meaning from color + direction icon.
- Stat values use large, bold text for visibility.
- Title uses `uppercase tracking-wide` for visual hierarchy without heading tags (appropriate in a card grid).
