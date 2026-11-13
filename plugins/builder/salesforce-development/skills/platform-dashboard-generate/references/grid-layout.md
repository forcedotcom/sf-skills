# Grid Layout

Lightning dashboards use a grid. Classic dashboards (`leftSection` / `middleSection` / `rightSection`
with `columnSize`) still deploy, but never create new ones.

```xml
<dashboardGridLayout>
    <dashboardGridComponents>…one per widget…</dashboardGridComponents>
    <numberOfColumns>12</numberOfColumns>
    <rowHeight>36</rowHeight>
</dashboardGridLayout>
<isGridLayout>true</isGridLayout>
```

- `numberOfColumns`: the editor offers **12** (default) or **9**. Use 12 unless told otherwise.
- `rowHeight`: the editor always writes **36** (pixels). Other values deploy; keep 36.
- Each cell: `colSpan`, `columnIndex` (0-based), `dashboardComponent`, `rowIndex` (0-based), `rowSpan`,
  in that (alphabetical) order.

## Rules the deploy enforces

| Mistake | Error |
|---------|-------|
| Two cells share any grid square | `Invalid layout. Components cannot overlap one another.` |
| `columnIndex + colSpan` > `numberOfColumns` | `4 is not a valid column span. Valid column spans range from 1 to 12` (it reports the *span*, though the real problem is the start column) |

Gaps (empty rows or columns) are allowed and are kept.

## Sizing guide (12 columns × 36 px rows)

| Widget | colSpan × rowSpan | Fits |
|--------|-------------------|------|
| Heading (one line, 20–32 px text) | 12 × 2 | Text widgets clip anything taller than rowSpan × 36 px — a 96 px heading needs ≥ 4 rows |
| KPI metric | 3 × 4 (four per row) or 4 × 4 (three per row) | |
| Gauge | 4 × 6 or 6 × 6 | |
| Chart | 6 × 8 (two per row) or 12 × 8 | Legends on `Right` need ≥ 6 columns |
| Donut / Funnel | 4 × 8 | |
| Lightning table | 12 × 8 (≈ 7 visible rows), 6 × 8 for 2–3 columns | |
| Notes / caption | 12 × 1–2 | |

A common layout: row 0 heading (12 × 2), row 2 KPI strip (4 × 3 × 4), row 6 two charts (6 × 8 each),
row 14 table (12 × 8).

## Limits (UI limits; the Metadata API does NOT check them)

| Limit | Value |
|-------|-------|
| Widgets per dashboard | 25 (text widgets can fill all 25) |
| Charts + tables — **metrics and gauges count** | 20 |
| Image widgets | 3 |
| Custom LWC widgets | 1 |
| Tables using "table settings from report" | 3 |

Over-limit dashboards deploy and **render for viewers**, but the builder refuses to save them
("You can have up to 20 chart and table widgets on dashboards.") until widgets are removed — so the
next person to edit it in the UI is stuck. Text, image and LWC widgets do not count toward the 20.
