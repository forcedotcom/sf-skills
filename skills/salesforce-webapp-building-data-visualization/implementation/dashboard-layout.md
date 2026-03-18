# Dashboard Layout — Implementation Guide

## Anatomy of a dashboard page

A typical dashboard combines stat cards, charts, and data tables:

```
┌────────────────────────────────────────────────────┐
│  Search / global action bar                         │
├──────────┬──────────┬──────────────────────────────┤
│ Stat 1   │ Stat 2   │ Stat 3                       │
├──────────┴──────────┴──────┬───────────────────────┤
│                            │                       │
│  Data table / list         │  Donut chart          │
│  (70% width)               │  (30% width)          │
│                            │                       │
└────────────────────────────┴───────────────────────┘
```

---

## Layout implementation

```tsx
import { PageContainer } from "@/components/layout/PageContainer";
import { StatCard } from "@/components/StatCard";
import { DonutChart } from "@/components/DonutChart";

export default function Dashboard() {
  return (
    <PageContainer>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Search bar */}
        <div>{/* global search component */}</div>

        {/* Main content: 70/30 split */}
        <div className="grid grid-cols-1 lg:grid-cols-[70%_30%] gap-6">
          <div className="space-y-6">
            {/* Stat cards row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatCard title="Metric A" value={42} />
              <StatCard title="Metric B" value={18} />
              <StatCard title="Metric C" value={7} />
            </div>

            {/* Data table */}
            <div>{/* table component */}</div>
          </div>

          {/* Sidebar chart */}
          <div>
            <DonutChart title="Distribution" data={chartData} />
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
```

---

## Responsive behavior

| Breakpoint | Layout |
|------------|--------|
| Mobile (`< 768px`) | Single column, everything stacked |
| Tablet (`md`) | Stat cards in 3-col grid, rest stacked |
| Desktop (`lg`) | 70/30 split for table + chart |

Key Tailwind classes:

```
grid grid-cols-1 lg:grid-cols-[70%_30%] gap-6
grid grid-cols-1 md:grid-cols-3 gap-6
```

---

## Loading state

Show a full-page loading state while dashboard data is being fetched:

```tsx
if (loading) {
  return (
    <PageContainer>
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Loading dashboard…</p>
      </div>
    </PageContainer>
  );
}
```

Or use a skeleton layout:

```tsx
if (loading) {
  return (
    <PageContainer>
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-[70%_30%] gap-6">
          <div className="h-64 animate-pulse rounded-xl bg-muted" />
          <div className="h-64 animate-pulse rounded-xl bg-muted" />
        </div>
      </div>
    </PageContainer>
  );
}
```

---

## Data fetching pattern

Use `useEffect` with cancellation for dashboard metrics:

```ts
const [metrics, setMetrics] = useState<Metrics | null>(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  let cancelled = false;
  (async () => {
    try {
      setLoading(true);
      const data = await fetchDashboardMetrics();
      if (!cancelled) setMetrics(data);
    } catch (error) {
      if (!cancelled) console.error("Error loading metrics:", error);
    } finally {
      if (!cancelled) setLoading(false);
    }
  })();
  return () => { cancelled = true; };
}, []);
```

---

## Combining multiple data sources

Dashboards often aggregate data from several APIs. Load them in parallel:

```ts
const [metrics, setMetrics] = useState<Metrics | null>(null);
const [requests, setRequests] = useState<Request[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  let cancelled = false;
  Promise.all([fetchMetrics(), fetchRecentRequests()])
    .then(([metricsData, requestsData]) => {
      if (!cancelled) {
        setMetrics(metricsData);
        setRequests(requestsData);
      }
    })
    .catch((err) => {
      if (!cancelled) console.error(err);
    })
    .finally(() => {
      if (!cancelled) setLoading(false);
    });
  return () => { cancelled = true; };
}, []);
```

---

## PageContainer wrapper

A simple wrapper for consistent page padding:

```tsx
interface PageContainerProps {
  children: React.ReactNode;
}

export function PageContainer({ children }: PageContainerProps) {
  return <div className="p-6">{children}</div>;
}
```
