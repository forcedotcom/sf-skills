# Empty-source handling

A data object can be "empty" for two very different reasons, and the right
response differs. Authoring (a viz, a dashboard, a calc field, a metric) on
either kind of empty source produces something that renders but shows nothing —
the most expensive failure mode, because it looks like success. Diagnose which
kind you have **before** building, and tell the user clearly.

**Field-richness is not data-presence.** An object can carry dozens of fields and
return zero rows. The field list proves the *schema* exists, not that *data*
does. Prove data presence by querying — `python scripts/query_data.py --count
<Object>` — never by inspecting the field list.

## The two empty states

### 1. Empty-of-rows (has fields, joinable, queries blank)

The object is fully defined: it has fields, it can participate in joins, a query
against it succeeds — it just returns **0 rows**.

- **How it looks:** `SELECT COUNT(*) FROM <object>` → `0`. Schema/field discovery
  succeeds. No error.
- **What it means:** the table exists and is materialized but currently holds no
  data (e.g. a filtered segment with no members yet, a freshly created DLO before
  its first ingest, a date-partitioned object with nothing in range).
- **Response:** treat as a real, query-confirmed empty. The data-presence gate
  (`lib.query.assert_has_rows`) **hard-blocks** here. Do not build on it; surface
  it (see *User-facing wording* below).

### 2. Unmaterialized / 0-field (cannot be joined; underlying table may not exist)

The object is declared but not actually backed by a queryable table.

- **How it looks:** discovery returns **0 fields**, or a count query **errors**
  (rather than returning 0) — e.g. "table not found" / failed to resolve. It
  cannot be joined.
- **What it means:** the underlying physical table hasn't been created/populated
  yet. The object is a definition with nothing behind it.
- **Response:** this is *indeterminate*, not a confirmed 0-row count, so the gate
  **warns rather than hard-blocks** (a query failure must not be mistaken for a
  definite empty). Do not author on it — there is nothing to query. Resolve the
  upstream materialization first.

**Distinguishing them quickly:**

| Signal | Empty-of-rows | Unmaterialized / 0-field |
|---|---|---|
| Field discovery | returns fields | returns **0 fields** |
| `COUNT(*)` | returns `0` (succeeds) | **errors** (table not found) |
| Joinable? | yes | no |
| Gate behavior | hard-block (confirmed 0) | warn (indeterminate) |

## DMO materialization is asynchronous — re-check before declaring empty

A **DMO is empty until its DLO→DMO mapping materializes.** After a mapping is
created (or data is freshly ingested), there is a lag before rows appear in the
DMO. A `COUNT(*)` of `0` immediately after mapping is expected and **transient**,
not a real empty.

- Before declaring a DMO empty, **wait and re-check** the count. If it goes from
  `0` to non-zero, it was simply mid-materialization.
- If it stays `0` well past the expected materialization window, treat it as a
  genuine empty-of-rows (state 1) and surface it.
- Discovery of the DLO→DMO mapping itself is the `data-cloud-connect-api` skill's
  job — use it to confirm a mapping exists before assuming the DMO will ever fill.

## User-facing wording

When a build's sources come back empty, don't silently ship a blank result and
don't silently pick a different source — **tell the user what you found and offer
a choice.**

### Some sources empty, others populated

> "`<Object A>` returned 0 rows, so a chart built on it would be blank. `<Object
> B>` and `<Object C>` have data (`<n>` and `<m>` rows). Want me to build the
> dashboard from the populated sources and drop `<Object A>`, or hold until
> `<Object A>` has data?"

Default: build from the populated sources, clearly noting which were dropped and
why.

### All sources empty

> "Every source I checked for this dashboard returned 0 rows (`<Object A>`:
> empty; `<Object B>`: empty). I can't build a meaningful dashboard on empty
> data — it would render 'No results to show' everywhere. This usually means
> either the data hasn't been ingested yet, or (for DMOs) the DLO→DMO mapping
> hasn't materialized. Do you want me to hold until data lands, or point me at a
> different, populated source?"

Default: **stop** and ask — do not proceed to a blank dashboard.

### Unmaterialized source

> "`<Object>` isn't queryable yet (it has no fields / the table doesn't resolve),
> which usually means it hasn't been materialized. I can't author on it until the
> upstream data lands. Want me to use a different source, or check back after
> materialization?"
