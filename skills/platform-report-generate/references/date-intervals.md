# Date Intervals Reference

Only use values from this table. Do NOT invent interval names like `INTERVAL_CURQ` — they will cause deployment failures.

## Fiscal Intervals (use when org has fiscal year configured)
| Interval | Description |
|----------|-------------|
| `INTERVAL_CURRENT` | **Current fiscal quarter** — use this for "this quarter" or "current quarter" |
| `INTERVAL_CURNEXT1` | Current + next fiscal quarter |
| `INTERVAL_CURPREV1` | Previous + current fiscal quarter |
| `INTERVAL_NEXT1` | Next fiscal quarter |
| `INTERVAL_PREV1` | Previous fiscal quarter |
| `INTERVAL_CURNEXT3` | Current + next 3 fiscal quarters |
| `INTERVAL_CURFY` | Current fiscal year |
| `INTERVAL_PREVFY` | Previous fiscal year |
| `INTERVAL_NEXTFY` | Next fiscal year |
| `INTERVAL_PREVCURFY` | Previous + current fiscal year |

## Calendar Intervals
| Interval | Description |
|----------|-------------|
| `INTERVAL_CURRENTQ` | Current calendar quarter |
| `INTERVAL_NEXTQ` | Next calendar quarter |
| `INTERVAL_PREVQ` | Previous calendar quarter |
| `INTERVAL_CURY` | Current calendar year |
| `INTERVAL_PREVY` | Previous calendar year |
| `INTERVAL_NEXTY` | Next calendar year |
| `INTERVAL_PREVCURY` | Previous + current calendar year |
| `INTERVAL_THISMONTH` | This month |
| `INTERVAL_LASTMONTH` | Last month |
| `INTERVAL_NEXTMONTH` | Next month |
| `INTERVAL_THISWEEK` | This week |
| `INTERVAL_LASTWEEK` | Last week |
| `INTERVAL_NEXTWEEK` | Next week |

## Day-Based Intervals
| Interval | Description |
|----------|-------------|
| `INTERVAL_YESTERDAY` | Yesterday |
| `INTERVAL_TODAY` | Today |
| `INTERVAL_TOMORROW` | Tomorrow |
| `INTERVAL_LAST7` | Last 7 days |
| `INTERVAL_LAST30` | Last 30 days |
| `INTERVAL_LAST60` | Last 60 days |
| `INTERVAL_LAST90` | Last 90 days |
| `INTERVAL_LAST120` | Last 120 days |
| `INTERVAL_NEXT7` | Next 7 days |
| `INTERVAL_NEXT30` | Next 30 days |
| `INTERVAL_NEXT60` | Next 60 days |
| `INTERVAL_NEXT90` | Next 90 days |
| `INTERVAL_NEXT120` | Next 120 days |

## Custom
| Interval | Description |
|----------|-------------|
| `INTERVAL_CUSTOM` | Custom date range — requires `<startDate>` and `<endDate>` |
