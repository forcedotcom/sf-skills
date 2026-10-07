# Data Understanding (profile before you author)

Load this **after** the data is queryable — either after you've profiled and
ingested a flat file (`large-flat-file-handling.md`, then the Step 0 ingest), or
over an already-built model — and **before** you choose
calculated fields, metrics, or charts. Proving the data has *rows and joins* shows
it's *queryable*; this step proves you understand what the data *means* so the
analysis and the chart actually answer the user's question. The single most common
quality failure after "empty dashboard" is a **populated dashboard that charts the
wrong thing** — a count of an ID treated as a measure, a sum of a ratio, a
200-category bar chart, a line over a load timestamp.

> Tableau Desktop profiles a published datasource or extract; Tableau Next
> profiles the **SDM over Data Cloud** — the grain, types, cardinality, and date
> roles all come from `list_semantic_model_*` + `run_semantic_query` /
> `run_query`, never from XML metadata. The *questions* below are
> product-agnostic; the *tools* are Next-native.

> **Where the build happens.** This file is the bridge between *understanding* the
> data and *building* the SDM. The actual model/metric/chart construction (the
> **Step N** references below — Step 5 read-back, Step 8 metric creation, Step 10
> charting — and the **`viz-authoring.md` / `dashboard-authoring.md` /
> `semantic-query-and-enrichment.md`**
> reference files) is the workflow in this skill's `SKILL.md`. The
> **"From data understanding to the SDM"** map at the end of this file translates
> each profiling finding into the exact authoring choice it constrains there.

Before any of the five, run the **elicitation gate** (below): if a field, segment,
value, or requested metric you need is load-bearing but its *meaning* is ambiguous —
on any dataset, modeled or flat — STOP and ask the user with your best guess
attached. Profiling tells you the data's shape; it cannot tell you what a column
*means*, and meaning is what the analysis depends on.

## Contents

- The five things to know before authoring
- Snapshot / panel grain — dedup to latest before aggregating
- Window flags & counts → calc measures (the `_7D/_30D/_90D` grammar)
- Profiling queries (cheap, run before authoring)
- Elicitation gate — ask what a load-bearing field MEANS (hard stop, any dataset)
- From data shape to the right question
- From data understanding to the SDM (the handoff)
- Common mistakes

## The five things to know before authoring

| # | Question | How to find it | Why it matters |
|---|---|---|---|
| 1 | **Grain** — what is one row? | `run_query SELECT COUNT(*)` vs `COUNT(DISTINCT <pk>)` on the fact object; read object labels | Determines whether a "count" is meaningful and what a measure sums to. One row per order ≠ one row per line item. **A relationship can change the grain** — a 1:N join fans the fact out, so re-profile after adding one (mistake #7). |
| 2 | **Field roles** — dim / measure / date | `list_semantic_model_dimensions`, `list_semantic_model_measures`; check `dataType` | A numeric ID is a *dimension*, not a measure. A `Date`/`DateTime` dim gates timeseries + metrics. |
| 3 | **Cardinality** — distinct values per dimension | `run_semantic_query` grouping by the dim with `limit_options` + a count, or `run_query SELECT COUNT(DISTINCT col)` | Drives chart choice: 2–7 → bar/pie ok; 8–20 → horizontal bar; 20+ → top-N + "Other", treemap, or a different cut. |
| 4 | **Measure additivity** — sum-safe vs ratio | inspect the measure's meaning + `aggregationType`; ratios/rates/percentages are NOT additive | Summing a margin %, a rate, or an average across groups is wrong. Additive (amount, count, quantity) → `Sum`; ratio → `Average`/`UserAgg` or recompute from numerator/denominator. |
| 5 | **Date roles** — event date vs plumbing | `list_semantic_model_dimensions` → `dataType: "Date"`; read the name | Only a **business event date** (created/close/order/activity) anchors a timeseries or metric. `cdp_sys_PartitionDate`, `*_SourceVersion`, ingestion timestamps are plumbing — never the time axis. |

## Snapshot / panel grain — dedup to latest before aggregating

A frequent shape (especially from wide enterprise extracts — see
`large-flat-file-handling.md`) is a **periodic snapshot**: a date column (`SNAP_DT`,
`SNAPSHOT_DATE`, `AS_OF`, `PARTITION_DATE`) repeated for every entity, so the
grain is **entity × snapshot-date**, not entity. Detect it: if
`COUNT(DISTINCT snapshot_date) × COUNT(DISTINCT entity_id) ≈ COUNT(*)`, it's a
panel. This is a **grain question (row 1)** with a sharp consequence — most exec
KPIs want *current state per entity*, so you must **dedup to the latest snapshot
per entity** (`max(snapshot_date)` per id) before any count or %. Aggregating the
raw panel multiplies every count by the number of snapshots.

The identity is **necessary, not sufficient**: a once-per-period **transaction fact**
(one row per order/invoice per period) matches it too, and deduping *that* to
latest-per-entity would discard real events. Confirm it's an as-of snapshot first —
the date should be a stamp **shared across the population** (≈ one row per entity per
date), not sparse per-entity event dates — and profile rows-per-snapshot-date so a
**short final load** doesn't dedup you onto a truncated population. Both discriminators
are worked out in `large-flat-file-handling.md §4`.

- The deduped row set is the **population** every headline % divides by — verify
  it (`large-flat-file-handling.md §5`) before authoring.
- Use `max` *per entity*, not a global `WHERE date = max(date)` — entities that
  dropped out earlier still have a valid "latest" row.
- Expose the deduped grain to the SDM **in the model**, with a **Text latest-flag
  calculated dimension + a metric filter** (`large-flat-file-handling.md §4`): a
  constant `As_Of_Date` anchor, a `Text` `Is_Latest_Snapshot` flag (`IF [Obj].[ds] =
  DATE("<max>") THEN "Y" ELSE "N" END`), then `filters: [Is_Latest_Snapshot = "Y"]`
  on every snapshot metric. Author the flag as a `Text` "Y"/"N" value so the metric
  filters on a discrete scalar, not a raw `Date` comparison
  (`large-flat-file-handling.md §4`).

## Window flags & counts → calc measures (the `_7D/_30D/_90D` grammar)

Wide behavioral extracts encode trailing-window activity as **per-row flags and
counts**, not as raw events: `X_30D` (did X in the last 30 days, 0/1),
`X_TOT_30D` (count of X in 30 days), `X_DISTINCT_30D` (distinct count). After
deduping to latest (above), these become straightforward derived measures over
the population:

| Want | From | Calc |
|---|---|---|
| **% of population who did X (30D)** | `X_30D` flag | `SUM(flag) / COUNT(entity)` → a ratio calc measure (`UserAgg`), or a metric counting truthy flags ÷ population |
| **avg events per entity** | `X_TOT_30D` | `SUM(X_TOT_30D) / COUNT(entity)` |
| **avg events per active entity** | `X_TOT_30D`, `X_30D` | `SUM(X_TOT_30D) / SUM(X_30D flag)` |
| **frequency bucket** (e.g. daily-equiv) | `X_TOT_30D` | a calc **dimension** bucketing the count (`>=60` → "≥2/day", `30–59` → "~1/day") — confirm thresholds with the user |
| **segment membership** | one or more flags | a calc dimension; **if the segment has no single backing column, ASK the user for its definition** (`large-flat-file-handling.md §3`) before encoding it |

Per the skill's default, build these **both** as calc measures/dimensions (the
point-in-time KPI on the latest snapshot) **and**, where the panel supports it, as
metrics anchored on the snapshot date so the trend across snapshots is available.
A percentage is a **ratio → not additive** (row 4): use `UserAgg` / recompute from
numerator and denominator, never `Sum` across groups.

> **Anchoring a snapshot metric: a constant as-of date, never a per-row activity
> timestamp.** A metric's `timeDimensionReference` is **required** (you cannot omit
> it to make the metric "non-temporal"), and the KPI card renders the value at the
> **latest time period**. A deduped snapshot is *one* period's worth of truth — the
> as-of moment — so every row the metric counts must share **one** anchor date. If
> you instead anchor on a per-row event/activity attribute (a `LAST_*_TS`, "last
> login", "last export"), the card fractures the population: rows scatter across
> the months of their individual timestamps, rows with a `null` timestamp orphan
> into a null bucket, and the card displays only the latest month's slice — silently
> under-reporting the true total. This is the snapshot form of mistake #4 below, and
> it is the single most common way a snapshot KPI ships *plausibly* wrong (a number
> in the right ballpark, just not the real total).
>
> A single extract often has **no snapshot-date column at all** — there is no `SNAP_DT` /
> `AS_OF` to anchor on. **Create one as a constant** calc dimension, then point
> **every** snapshot metric's `timeDimensionReference` at it:
>
> ```jsonc
> // 1. the constant as-of dimension — add_semantic_model_calculated_dimension
> //    substitute the snapshot's ACTUAL as-of date (the extract date, or the
> //    max(snapshot_date) you deduped to, or today if that's the as-of) for the literal
> { "apiName": "As_Of_Date", "label": "As Of Date",
>   "expression": "DATE(\"2026-06-23\")", "dataType": "Date",
>   "displayCategory": "Continuous" }
> // 2. EVERY snapshot metric anchors on it — add/update_semantic_model_metric
> "timeDimensionReference": { "calculatedFieldApiName": "As_Of_Date" }
> ```
>
> The whole population then collapses into a single time bucket and the card shows
> the real headline (population count, flag-sum, etc.). **Point `measurementReference`
> at a fully-populated numeric measure with `aggregationType: "Count"`** (Count counts
> non-null values, so a gappy field under-reports) — **never at the entity text Primary Key**
> (e.g. `Employee_ID`), which the API rejects (`field … was not found in the model`);
> the Primary Key is still the `identifyingDimension` (see Step 8).
>
> **This constant as-of date is NOT the "junk/plumbing date" the Step 8 rule warns
> against.** That rule forbids a load/system timestamp (`cdp_sys_*`, `*_SourceVersion`)
> standing in for a real event — and a per-row activity timestamp on a snapshot. For a
> single deduped snapshot there is no event date to use; the constant as-of date IS the
> business-meaningful anchor (it states "as of `<date>`, the population is N"). Keep the
> four anchor cases distinct: a **real event date** → event streams; a **genuinely
> differing snapshot date** → multi-snapshot trends; a **constant as-of date** → a
> single snapshot; a **plumbing/load timestamp** → always wrong. Only with multiple
> snapshots does anchoring on the snapshot date itself yield a real trend; on one
> snapshot, the constant is correct.
>
> After authoring, verify (`large-flat-file-handling.md §5`): query the metric at
> `Month` grain and confirm it returns **one** bucket equal to the known total, not
> a scatter across months plus a null bucket.

> **These calc fields are queryable, but the chart tools want native fields.**
> Everything in the table above is a **calculated** measure/dimension —
> `run_semantic_query` reads them, and a calc *measure* can back a **metric** (hence a
> KPI card). But the chart tools (`create_timeseries_viz` /
> `create_comparative_viz` / `create_relationship_viz`, `viz-authoring.md`)
> place **native** object fields on their shelves — a calc dimension/measure does not
> chart directly. So the natural home for these window-flag numbers is **metric
> widgets / KPI cards**, not bars. Plan for that from the start: a snapshot/adoption
> file becomes a **KPI-card dashboard** (one card per rate/count), with a chart only
> where a **native** field carries it.

### Materialize segments as native columns (when you truly need to chart them)

If a derived **segment** (an adoption bucket, a frequency tier, a window flag) must
appear **on a chart axis or Color** — not just as a KPI number — it has to be a
**native column on the data object**, because a calc dimension won't bind. Create
it at **DMO-create / DLO→DMO mapping time** (a mapped/derived field, or a
transform that writes the bucket as a real column), so by Step 5 it reads back as a
native dimension you can put on a shelf. Decide this **early**, while modelling — you
cannot retrofit a native column after the chart fails. Default, though, is *don't*:
report segments as KPI cards (above) and reserve native-column materialization for a
segment that genuinely earns a bar. **If the segment has no single backing column
and no clear definition, ASK the user before encoding it** (`large-flat-file-handling.md §3`).

## Profiling queries (cheap, run before authoring)

Row count and grain check (raw `run_query`, source-suffixed name):

```sql
SELECT COUNT(*) AS rows, COUNT(DISTINCT order_id) AS distinct_orders FROM orders__dll
```

Cardinality + distribution of a candidate breakdown dimension (semantic query —
use SDM data-object apiName + suffixed field apiName, see
`semantic-query-and-enrichment.md`):

```jsonc
{ "fields": [
    { "expression": { "table_field": { "name": "Category3", "table_name": "Orders" } },
      "alias": "Orders.Category3", "grouping": "ROW_GROUPING" },
    { "expression": { "table_field": { "name": "Sales7", "table_name": "Orders" } },
      "alias": "Orders.Sales7", "semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_COUNT" } ],
  "options": { "limit_options": { "limit": 50 },
    "sort_orders": [ { "simple_sort_order": { "sort_by_field_alias": "Orders.Sales7", "sorting_order": "DESC" } } ] } }
```

Read the number of returned groups = cardinality; read the spread to spot a
dominant category or a long tail (the "Other" candidates). A `null` grouping row
is the blank/unmatched bucket — note it; it often signals a data-quality gap
worth surfacing to the user rather than charting silently.

Date-range / freshness check on a candidate time anchor:

```sql
SELECT MIN(order_date) AS first, MAX(order_date) AS last, COUNT(DISTINCT order_date) AS n_dates FROM orders__dll
```

A single distinct date (or first==last) means there is no trend to plot — a
timeseries would be a single point; pick a comparison chart instead.

## Elicitation gate — ask what a load-bearing field MEANS (hard stop, any dataset)

Profiling tells you the *shape* of the data (grain, type, cardinality, dates). It
does **not** tell you the *business meaning* of a field, a segment, or a value —
and meaning is what the analysis turns on. **Whenever a field, dimension value,
segment, or requested metric is load-bearing for the user's question but its
meaning cannot be resolved from the schema alone, STOP and ask before authoring.**
This gate fires for ANY dataset — modeled SDM or flat file, large or small,
cryptically or friendly named. Ambiguity is a property of the request against the
data, not of the file's size or naming. The four triggers:

- **Ambiguous meaning** — a field/dimension/value whose definition is unclear and
  the analysis depends on it: an opaque numeric measure of unknown derivation
  (`health_index`, `engagement_score`), or a low-cardinality dimension whose values
  are codes you can't decode (`stage` = `S2`/`CW`/`CL`, `tier` = `A`/`B`/`C`). It
  profiles cleanly (tidy cardinality, sum-safe type) and will chart silently as
  opaque labels — that is exactly the trap. Ask, e.g.: *"`stage` has values S2/CW/CL
  — what do those mean and what order? My guess: Stage 2 / Closed-Won / Closed-Lost."*
  or *"What does `health_index` measure and how is it derived — is it sum-safe or a
  per-entity ratio I should average?"*
- **Derived segment with no single backing column** — "high-value account",
  "at-risk customer", "engaged account", "active user": ask which columns/thresholds
  define it, with your best guess attached: *"There's no single `at_risk` column. How
  do you define at-risk — e.g. `renewal_date < 90d AND health < 0.5`?"*
- **Requested-but-absent metric** — the user named something with no backing field.
  Say so and ask; **never fabricate a value**: *"There's no column for churn rate in
  this model. Should I show it as N/A, drop it, or derive it from a column I'm not
  recognizing?"* Surface an explicit 0 / "not present" only with the user's say-so.
- **Clean-but-conventional measure — units, sign, currency, window basis.** The most
  dangerous field is the one that profiles *perfectly*: a tidy numeric `Amount`,
  sum-safe type, no nulls — and is silently off by 100×, or backwards, or mixed. A
  field's shape can't tell you its **convention**, and a `SUM`/`AVG` inherits the
  convention whether or not you checked it. Before aggregating a money/quantity/rate
  measure, resolve four conventions that don't show up in the schema — ask only the
  ones the analysis actually turns on, best guess attached:
  - **Units & scale** — *"Is `revenue` in dollars or cents? Is `margin` a fraction
    (0–1) or a percent (0–100)?"* Cents-vs-dollars or 0–1-vs-0–100 is a 100× error
    that charts cleanly.
  - **Sign convention** — *"Do returns/credits/adjustments carry a negative sign in
    `amount`, or is direction in a separate `type` column?"* If refunds are negative,
    `SUM(amount)` is net, not gross — and a naive `SUM` of a mixed-sign column silently
    nets them when the user wanted gross (or vice versa).
  - **Single currency** — *"Is `amount` all one currency, or is there a `currency_code`
    I should split/convert by?"* Summing mixed currencies into one bar is meaningless.
  - **Trailing-window basis** — for `_7D/_30D/_90D`-style fields (see
    `large-flat-file-handling.md §2`): *"Is `LOGIN_30D` a trailing-30-day window as of
    the snapshot, a calendar-month count, or life-to-date?"* The window basis decides
    whether two `_30D` fields are even comparable, and never appears in the type.

Ask **targeted, bounded** questions — only about the residue that blocks authoring,
never "what does everything mean?" — and **propose your best guess** so the user
confirms or corrects in one line. **Never silently infer a load-bearing definition
and proceed.** Ten seconds of confirmation prevents a confidently-wrong dashboard.

**The gate is not one-and-done — re-fire it when profiling surprises you.** You run
the gate *before* profiling on what the schema reveals, but profiling itself turns
up meaning questions the schema hid: a column that's **60% null**, a dimension with
an enormous **`null`/`Unknown` bucket**, a measure whose range is implausible
(negatives where you expected counts, a max 100× the others), a date that's a single
value. Each of these **re-opens the meaning question** — a huge null bucket isn't
just "a data-quality note to surface," it may mean the field means something other
than you assumed (optional-by-design, a sentinel, a default), and charting past it
encodes the wrong assumption. When a profiling result contradicts your decode, stop
and re-ask (with your best guess) before you build on it.

**No human available (unattended / eval harness): do not block.** Record the exact
question and your best-guess assumption verbatim in the run notes / source line,
proceed on that stated assumption, and flag the resulting field/metric as
assumption-based so it can be reviewed — the same "surface it, state it, proceed"
pattern used for the dedup/source line, never a silent guess and never a hard halt.

The wide-extract instance of this same gate (decoding a column-naming grammar, then
asking about the window-flag / threshold / snapshot residue) is worked out in
`large-flat-file-handling.md §3`; that is one shape of this gate, not its only home.

## From data shape to the right question

Profiling tells you which analytical questions the data can actually answer.
Map the user's intent to a question category, then to the matching chart tool in
`viz-authoring.md`:

- **One measure across a low-cardinality dimension** → comparison (**Bar**,
  `create_comparative_viz`).
- **One measure over a real event date** → trend (**Line**, `create_timeseries_viz`).
- **Two measures per entity** → relationship (**Circle** / scatter,
  `create_relationship_viz`).
- **Spread/shape of one measure** (deal sizes, response times) → distribution. Next's
  chart tools have no native histogram/box mark, so render it as a **binned bar**:
  bucket the measure into a calc/native dimension and chart counts per bucket with
  `create_comparative_viz`.
- **A part-to-whole of one measure across 2–5 segments** → composition (**Donut**)
  *only if the segment is a native dimension*; if the split is a calc dimension,
  report it as KPI cards instead (see below).
- **A single tracked headline number anchored on an event date** → a **metric** (Step 8), not a chart.
- **"How many adopting / how intensely" over a deduped snapshot (adoption/health)**
  → a **KPI-card dashboard**, not charts: the rates and counts are calc
  measures/flags that don't chart directly, so present them as metric widgets laid out
  per `dashboard-authoring.md`. Add a trend strip only across multiple snapshots, on
  a native date.

(Each chart tool and its payload shape — `create_*_viz` — is in
`viz-authoring.md`.)

If the data cannot answer the literal request (no event date for a "trend over
time", no second measure for a "correlation", every value in one category),
**say so and offer the closest answerable question** — do not silently
substitute a chart that misrepresents the data.

## From data understanding to the SDM (the handoff)

Profiling is not an end in itself — every finding above **constrains a specific
authoring decision** in the SDM build (this skill's `SKILL.md` workflow).
Carry the findings forward as a checklist; each row is a profiling result on the left
and the exact build choice it dictates on the right. Skipping this is how a correctly
*profiled* dataset still ships a wrong *model*.

| You learned (profiling) | So in the SDM you must… | Where (SKILL.md workflow) |
|---|---|---|
| **Grain** = one row per `<pk>` (`COUNT(*)==COUNT(DISTINCT pk)`) | set that `<pk>` as the metric's **`insightsSettings.identifyingDimension`** (required); never count by summing the ID | Step 8 metric shape |
| **Grain is entity × snapshot-date** (panel) | build the **latest-flag `Text` calc dimension + metric `filters[]`**, and anchor every snapshot metric on a **constant `As_Of_Date`** calc dimension | `large-flat-file-handling.md §4`; snapshot-anchor box above |
| A field is a **numeric ID** (dimension, not measure) | use it as a dimension / `identifyingDimension`; to count records point **`measurementReference` at a real numeric measure + `aggregationType: "Count"`** (an ID/dimension is rejected: "field … was not found in the model") | Step 8 |
| **Additive** measure (amount/count/qty) | `aggregationType: "Sum"` (or `Count`) | Step 8 |
| **Non-additive** ratio/rate/% (the clean-but-conventional gate) | `Average` / `UserAgg`, or recompute from numerator ÷ denominator — **never `Sum`**; and **never `Auto`** (rejected on metrics) | Step 8; mistake #3 |
| **Units/scale/sign/currency** convention (from the gate) | bake the correction into the **calc measure expression** (×100, `ABS`, currency split) *before* it backs a metric — the metric inherits whatever the measure emits | Step 8; calc-field step |
| A **real business event date** exists | use it as the metric's **`timeDimensionReference`** + `timeGrains`; a single constant/plumbing date is not a trend | Step 8 |
| Only a **constant/plumbing date** (or a deduped snapshot) | anchor on a **constant `DATE("<as-of>")`** calc dimension, not `cdp_sys_*` and not a per-row `LAST_*_TS` | snapshot-anchor box; mistake #4 |
| Dimension **cardinality** (2–7 / 8–20 / 20+) | drives chart family + whether to top-N/"Other"; a 20+-cardinality field is not a bar/pie | `viz-authoring.md`; Step 10 |
| A derived **segment / bucket** needs to be **charted** (not just a KPI) | it won't bind as a calc dimension — **materialize it as a native column at DLO→DMO mapping time**, decided *now*, not after the chart fails | "materialize segments" above; Step 10 |
| A field's **meaning is ambiguous / requested-but-absent** | the elicitation gate already fired — carry the user's confirmed definition (or the flagged assumption) into the calc field; never author on a silent guess | Elicitation gate above |
| A **1:N relationship** will be added | re-profile the **post-join** grain; aggregate the "one"-side measure on its owning object or via `COUNT(DISTINCT)` to avoid fan-out double-counting | mistake #7; Step 6 relationships (validated Step 7) |

This map is the contract between the two halves of this skill: data understanding
decides *what is true about the data*; the SDM build decides *how to encode it*. Hand
the right-hand column to the build as settled decisions, not open questions.

## Common mistakes

1. **Charting before profiling.** Building a viz off the field *labels* without
   checking cardinality, type, or date role. This is how a 200-bar chart or a
   line over a load timestamp ships.
2. **Treating an ID as a measure.** `Order_ID`, `Account_Id` are dimensions even
   though they're numeric. Counting records goes through a numeric measure +
   `Count` (Step 8), not a sum of the ID.
3. **Summing a non-additive measure.** Margin %, win rate, average deal size are
   ratios — summing them across groups is meaningless. Use `Average`/`UserAgg`,
   or recompute from the underlying numerator and denominator.
4. **Picking the wrong time anchor for a metric.** Two forms: (a) a `cdp_sys_*` or
   `*_SourceVersion` **plumbing** date produces a technically-valid but
   business-meaningless trend; (b) on a **deduped snapshot**, a **per-row activity
   timestamp** (`LAST_*_TS`, "last activity") fractures the population across months and
   orphans null-timestamp rows, so the KPI card shows only the latest month's slice
   instead of the true total. A snapshot count/flag-sum metric must anchor on a
   **uniform/constant** as-of date (a `DATE("…")` calc dimension), since the anchor
   is required and the card renders the latest period (see the snapshot-anchor box
   above and the Step 8 rule).
5. **Ignoring the `null` bucket.** A large `null` grouping row is a data-quality
   signal (unmapped keys, missing values) — surface it; don't let it sit as an
   unlabeled slice on a chart.
6. **Plotting a trend with one date.** If `MIN(date) == MAX(date)` or there's a
   single distinct date, a timeseries is a single point — choose comparison
   instead.
7. **Aggregating across a join without re-profiling the grain.** Adding a 1:N
   relationship **fans out** the fact object — a customer joined to its orders now
   has one row per order, so `SUM(customer_value)` double-counts and a `COUNT` of
   customers inflates. The grain you profiled (row 1) was the *pre-join* grain; the
   query runs at the *post-join* grain. After adding a relationship, re-run the
   `COUNT(*)` vs `COUNT(DISTINCT pk)` check on the joined result and confirm a measure
   from the "one" side isn't being summed at the "many" side's multiplied grain (use
   `COUNT(DISTINCT)`, a row-level dedup, or aggregate on the owning object).
