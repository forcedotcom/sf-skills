# Large / wide flat files — infer, decode, elicit (before ingesting)

## Gates → `shared-gates.md`

Required **G1, G6** (entry point 3 — infer a large/cryptic file's schema),
asserted from `profile-dataset.md`. G1: a `mcp__tableau-next-*__` tool must be
connected because this workflow uses `infer_object_schema`. G6 is this file's
entire content: infer the fields and types, decode their likely roles, then use
`run_query` after ingest for value-level profiling.

Load this **first**, before any ingestion, whenever the user points at a CSV/Excel
file that is **large** (tens of MB+ / >100k rows) or **wide** (dozens of columns),
or whose columns are cryptically named. The failure this prevents is twofold: (1)
reading an 80 MB file into context and blowing the window, and (2) authoring a
dashboard off **guessed** column meanings — charting the wrong thing with full
confidence.

> Tableau Desktop teaches "profile the datasource before you build." The
> published-datasource case lets you lean on its metadata. For a **raw uploaded
> CSV**, call `infer_object_schema` before creating the data stream and use the
> returned fields and types as the profile. Same profile-first discipline,
> earlier stage.
> After ingestion, normal SDM profiling (`data-understanding.md`) resumes.

> **Where ingestion and the SDM build happen.** This reference covers the *file*
> and the *model's meaning*; the actual ingest chain
> (`get_upload_connection` → `infer_object_schema` → `create_data_stream` →
> `run_data_stream` → wait DLO Active → SCHEMA REALITY CHECK + real Primary
> Key read-back → `create_data_model_object` → wait DMO Ready →
> `create_dlo_to_dmo_mapping` → inspect mapping status → poll `run_query`
> until `<dmo>__dlm` exists (`ACTIVE` is metadata only))
> and the SDM / metric / visualization build are the **workflow steps in this
> skill's `SKILL.md`**. References below to **"Step 0" and "Step 10"** and to
> **`viz-authoring.md` / `dashboard-authoring.md` /
> `semantic-query-and-enrichment.md`** point at that
> workflow and those sibling reference files — load them when you move from
> *understanding* the data to *building* on it.

The three disciplines below are a hard sequence: **infer → decode → elicit**,
and only then create the data stream (Step 0). Do not skip ahead on a file whose
schema you have not inferred and confirmed.

---

## Contents

- 1. Infer the schema, never read the whole file
- 2. Decode the naming convention before asking anything
- 3. Elicitation gate — ASK before authoring (hard stop)
- 4. Snapshot / panel files — find the grain, dedup to latest
- 5. Verify before you author — a hard gate, not a nicety
- Common mistakes

---

## 1. Infer the schema, never read the whole file

Never `Read` the whole file and never paste it into context. Use the standard
upload flow only far enough to obtain a server-inferred schema:

1. Call `get_upload_connection` with `connectorType: "UploadedFiles"`.
2. Use the exact `parentDirectory`, `importDirectory`, file name, and file type
   from the upload flow. For Excel, call `list_data_connection_objects` first and
   infer each selected sheet separately.
3. Call `infer_object_schema` for the file or sheet. Do not recreate, trim, or
   normalize the opaque directory values.
4. Inspect every returned field's name, type, and, for Date/DateTime fields,
   `format` and `originalType`. Present the inferred fields and wait for the user
   to confirm or adjust types, primary key, and skipped columns before
   `create_data_stream`.

`infer_object_schema` is the source of truth for CSV quoting and type inference.
Do not add a local parsing or profiling step. If the inferred schema leaves a
field's business meaning ambiguous, handle it through the decode and elicitation
steps below. Once the DLO is materialized, use `run_query` for value-level checks
such as row count, null count, distinct count, min/max, date distribution, and
sample values. Those checks operate on the platform-parsed table and cannot be
silently shifted by embedded delimiters.

Read query results as gates, not trivia: a **non-trivial null rate** on a date or
metric column means it may not be a clean anchor; disagreeing distinct counts
between candidate IDs mean the keys do not define the same grain; and a numeric
ID rendered in scientific notation may already have lost precision. Surface each
issue and confirm the intended key/type before authoring.

---

## 2. Decode the naming convention before asking anything

Wide enterprise extracts almost always follow a column-naming **grammar**.
Decode it from the header inventory alone — that resolves most columns for free
and shrinks what you have to ask the user about to the genuinely ambiguous
residue. Look for:

- **Repeated prefixes** = entity/family groupings (`ACCT_*` = account
  attributes; `LOGIN_*`, `EXPORT_*` = behavior families).
- **Repeated suffixes** = a metric grammar across a window or aggregation:
  - `_7D / _30D / _90D` → a trailing-window flag or value (7/30/90-day).
  - `_TOT_` → an event **count** in the window; `_DISTINCT_` → distinct count;
    `_LAST_TS` / `_LTD` → a last-event timestamp / life-to-date marker.
  - `_IND` / `_FLG` → boolean indicator; `_TXT` / `_NM` / `_DESC` → label
    dimension; `_NUM` / `_CNT` / `_AMT` → measure.
- **Numbered sequences** (`..._LVL_01..10_NM`) = a hierarchy unrolled into columns.

Write the decode down (a small table mapping prefix/suffix → meaning) and infer
each column's **role** (dimension / measure / date / id) from it. You will be
right about most. The point of decoding is not to *finish* understanding — it is
to **isolate the few columns the grammar can't explain**, which is exactly what
to ask the user about.

---

## 3. Elicitation gate — ASK before authoring (hard stop)

After decoding, you will have three kinds of column: **resolved** (the grammar
explains it), **load-bearing-but-ambiguous** (you need it for the requested
analysis but its definition lives in the user's head), and **requested-but-
absent** (the user asked for a metric with no backing column). The last two are a
**hard gate: STOP and ask the user before authoring anything.** Do not infer a
load-bearing definition and silently proceed.

Ask **targeted, bounded** questions — never "what do all these columns mean?" Ask
only about the residue, and propose your best guess so the user can confirm or
correct in one line:

- **Derived segment with no single column** (e.g. a "power user" segment, an
  "active account" definition): *"I don't see a single `POWER_USER` column. How
  do you define that segment — which columns/thresholds? My guess: `X_30D > 0`."*
- **Requested metric, no backing column** (e.g. "seats provisioned" when no such
  column exists): say so explicitly and ask — *"There's no column for seats
  provisioned in this file. Should I show it as an explicit 0 / N-A, drop it, or
  is it derivable from a column I'm not recognizing?"* **Never fabricate a value
  for an absent field.** (The default, per this skill, is to pause and ask; a
  surfaced 0 / "field not present" is acceptable only with the user's say-so.)
- **Threshold / bucket definitions** (e.g. "daily-equivalent", tiering): confirm
  the cutoffs — *"For 'at least daily-equivalent' over 30 days, I'll bucket
  `EVENTS_TOT_30D >= 60` as ≥2/day and `30–59` as ~1/day. Correct?"*
- **Clean-but-conventional measure** — units/scale, sign, currency, window basis. A
  column the grammar *did* resolve (`REVENUE_AMT`, `MARGIN`, `LOGIN_30D`) can still
  carry an unstated convention that the type can't reveal: dollars vs cents, fraction
  vs percent, negative-for-credit, mixed currency, or a trailing-30-day vs calendar
  vs life-to-date window basis. Before summing/averaging it, confirm the convention —
  *"Is `REVENUE_AMT` dollars or cents? Do credits go negative? Is `LOGIN_30D` a
  trailing-30-day window as of the snapshot?"* This is the wide-file face of the
  `data-understanding.md` gate's "clean-but-conventional" trigger; a 100×, sign-flipped,
  or window-mismatched measure profiles perfectly and ships silently wrong.
- **Grain / dedup choice** (see §4): confirm which row wins per entity.
- **Ambiguous date semantics**: which date is the business event vs a snapshot/
  load stamp.

Keep the batch small (the few that block authoring), propose guesses, and wait.
This is the single most leverage-y step for a wide unknown file: ten minutes of
questions prevents a confidently-wrong dashboard.

---

## 4. Snapshot / panel files — find the grain, dedup to latest

A very common wide-extract shape is a **daily (or periodic) snapshot**: a date
column (often `SNAP_DT`, `SNAPSHOT_DATE`, `AS_OF`, `PARTITION_DATE`) repeated across
every entity, so the grain is **entity × snapshot-date**, not entity. Identify the
candidate entity/date fields from the inferred schema, then validate it after
ingest with `run_query`:

```text
distinct snapshot-dates  ×  distinct entity-ids  ≈  row count
```

If that identity roughly holds, it's a panel/snapshot file. **Most exec KPIs want
"the current state per entity," which means deduping to the latest snapshot per
entity before aggregating.** Skipping the dedup multiplies every count by the
number of snapshots.

**The identity is necessary, not sufficient — confirm it's an as-of snapshot before
you dedup.** A once-per-period **transaction fact** (one row per order per day, one
row per invoice per period) satisfies `distinct dates × distinct entities ≈ rows`
just as well as a true daily snapshot, and deduping it to "latest per entity" would
**throw away real events** — the opposite of the snapshot fix. Two cheap
discriminators tell them apart:

- **Does the date repeat *identically* across entities?** In a real snapshot, the
  date column is an **as-of stamp shared by the whole population** on a given load —
  on any one snapshot date, (nearly) every still-active entity has exactly one row.
  In a transaction fact the dates are **per-event and entity-specific** — entity A
  transacts on the 3rd and 9th, entity B on the 5th, and most (date, entity) pairs
  don't exist. Profile it: `rows-per-(date) ≈ active-entity-count` and
  `rows-per-(entity) ≈ snapshot-count` → snapshot; sparse, ragged per-entity dates →
  transaction fact (don't dedup; it's already event grain — anchor on the event
  date). Use grouped `run_query` results to distinguish these shapes.
- **Profile rows-per-snapshot-date before trusting `max(date)`.** A snapshot's
  **final** date is often a **short or partial load** (the extract ran mid-day, or
  the last partition is still filling). If the latest date has materially fewer rows
  than the prior dates, `max(date)` dedups to a **truncated population** and every
  headline under-reports. Check the tail of the per-date counts; if the last
  snapshot is short, dedup to the last *complete* snapshot (and say so in the source
  line), or flag it to the user. Use `run_query` grouped by the inferred snapshot
  date field; do not build a separate local parser.

The robust rule is **dedup to `max(snapshot_date)` per entity-id**. Validate that
rule with `run_query`, then implement it in Tableau Next as described below so it
continues to apply after refresh.

Do **not** assume all entities share the same latest date — some may have dropped
out earlier; `max` per entity is correct even when, in a given extract, every
row happens to land on the same final date. State the dedup rule to the user as
part of the source line (e.g. *"latest row per account by SNAP_DT"*).

**Implementing dedup in Tableau Next — the in-platform recipe.** The file ingests
whole as the DLO (Step 0); you then expose the deduped grain to the SDM *in the
model* so the dashboard stays live and re-dedups on every refresh (never by
pre-trimming the file offline — that ships a snapshot that can't refresh). The
authorable path is a **latest-flag calculated dimension + a metric filter**, in
three steps:

1. **A constant `As_Of_Date` calc dimension** — `add_semantic_model_calculated_dimension`
   with `expression: "DATE(\"<max-snapshot-date>\")"`, `dataType: "Date"`,
   `displayCategory: "Continuous"`. This is the single as-of anchor every snapshot
   metric will point its (required) `timeDimensionReference` at (see the box below
   and `data-understanding.md` "Anchoring a snapshot metric").
2. **A Text latest-flag calc dimension** — e.g.
   `IF [Obj].[SNAP_DT] = DATE("<max>") THEN "Y" ELSE "N" END`, `dataType: "Text"`,
   `displayCategory: "Discrete"`. **Author the flag as a `Text` "Y"/"N" value, not a
   raw `Date` comparison** — a snapshot metric filters on the flag value, so it needs
   to be a discrete scalar the filter can match, not a date. For a per-entity-correct
   latest (entities that dropped out early still keep their own last row), compute the
   max **per entity** when shaping the flag rather than hardcoding the global max.
3. **Filter every snapshot metric to the flag** — `filters: [{ fieldName:
   "<Obj>.<Latest_Flag>", ... }]` with `filterLogic`, so the metric counts only the
   one-row-per-entity latest population.

Pre-deduping the CSV locally and ingesting the trimmed file *will* also produce
correct one-shot numbers, but the resulting dashboard cannot refresh from a
re-uploaded extract — reserve it for a throwaway local readout, not a delivered
asset.

**Plan the dashboard shape NOW: snapshot → KPI cards, not charts.** An adoption /
health request over a deduped snapshot resolves into **rates, counts, and window
flags** — all of which become **calculated** measures/dimensions. A calc *measure*
can back a **metric** (and thus a KPI card), but the chart tools
(`create_timeseries_viz` / `create_comparative_viz` / `create_relationship_viz`,
`viz-authoring.md`) put **native** fields on their shelves — a calc dimension
or calc measure does not chart directly. So report these as metric widgets.

> **And anchor those KPI metrics on a constant as-of date, not a per-row
> timestamp.** A metric's time anchor is **required** and the card renders the
> **latest period**, so a deduped snapshot (one as-of moment) must collapse into a
> single bucket: create a constant `DATE("<as-of>")` calc dimension and point every
> snapshot metric's `timeDimensionReference` at it. Anchoring on a per-row
> `LAST_*_TS` / "last activity" attribute scatters the population across months,
> orphans null-timestamp rows, and makes the card under-report the true total. Full
> doctrine + the post-authoring one-bucket check: `data-understanding.md`
> "Anchoring a snapshot metric."

So the right deliverable is a **KPI-card dashboard** — metric widgets laid out per
`dashboard-authoring.md` ("Build the dashboard") — with a chart only where a
**native** field carries it. If a derived **segment** must appear on a chart axis
(not just as a number), it has to be a **native column** — and the cheapest place to
create it is **right here, at the DLO→DMO modelling step**, alongside the
latest-flag selection (see `data-understanding.md` "materialize segments as native
columns"). Decide native-vs-calc while you're shaping the deduped object; you cannot
retrofit a native column after a chart fails at Step 10.

---

## 5. Verify before you author — a hard gate, not a nicety

This is a **hard gate, exactly like the §3 elicitation stop**: do not author a
single widget until it passes. A decode can be wrong in ways that profile cleanly
and survive every earlier step — a mis-read suffix, a wrong dedup key, a column
shifted by an embedded comma — and the *only* thing that catches them is
reproducing a number you can check against ground truth. Skipping this ships a
dashboard that is plausibly, confidently wrong. Three checks, all before authoring:

**(a) Reproduce one headline number the user already knows** — a population count,
a top-line %. If your decode is right it matches *exactly*; if it doesn't, your
column understanding is wrong and every metric built on it would be wrong — fix the
decode (or re-ask, §3) first. **No external number to check against?** (Common for a
brand-new extract — "what's in this file?") Then manufacture ground truth from the
materialized table itself: reproduce the population with two independent
`run_query` aggregations (deduped population vs `COUNT(DISTINCT pk)`) and
reconcile any two columns that should agree. (b) and (c)
below are **mandatory regardless** of whether the user supplied a number.

**(b) Verify the population independently — don't let the ratio hide a wrong
denominator.** A percentage can come out right with *both* its numerator and
denominator wrong (3,140/8,250 and 3,768/9,900 are both ~38%). So check the
denominator on its own terms: assert the deduped population equals the distinct
entity count — compare the deduped population with
`COUNT(DISTINCT entity_id)` in separate `run_query` checks — and reproduce the
**numerator and the denominator separately**, not just their ratio.
A matching ratio over an unverified population is not a passed gate.

**(c) Spot-check one entity end-to-end.** Pick one real entity, trace it from raw
rows → dedup-to-latest → its contribution to the headline metric, and confirm each
step by hand. This is what catches a mis-decoded suffix that an aggregate can't:
the file-wide total was *computed from* the mis-decode, so it agrees with itself —
only walking one entity through the actual values exposes that `_TOT_30D` was a
distinct-count, not an event-count, or that the "latest" row you kept isn't the one
you meant.

Cheap insurance, stated concretely: *"deduped population = 8,250 = COUNT(DISTINCT
EMP_ID); `LOGIN_30D` truthy = 3,140; 3,140/8,250 = 38.06%; spot-check emp 4471 →
3 raw snapshot rows, latest = 2026-06-09, `LOGIN_30D` = 1 → counted once."* That
one block confirms the decode, the population, and the per-row semantics at once.
Carry the verified numbers forward as the source-of-truth the dashboard's calc
measures/metrics must reproduce — and after authoring, re-query the live metric to
confirm it still returns them (`data-understanding.md` one-bucket check).

---

## Common mistakes

1. **Reading the file into context.** An 80 MB CSV does not belong in the window.
   Infer its schema with `infer_object_schema` (§1).
2. **Adding a local parsing step.** Use the inferred schema for fields/types and
   `run_query` against the materialized table for value-level profiling.
3. **Authoring on guessed column meanings.** Decode the grammar (§2), then **ask**
   about the residue (§3). Don't infer a load-bearing segment definition silently.
4. **Fabricating an absent metric.** A requested field with no backing column is a
   question for the user (surface as 0 / N-A only with their say-so), never an
   invented value.
5. **Aggregating a snapshot file without deduping.** entity×date grain inflates
   every count by the snapshot count — dedup to latest per entity first (§4).
6. **Assuming all entities share the latest snapshot date.** Use `max` per
   entity; some entities drop out earlier.
7. **Building before verifying — treating §5 as optional.** Verification is a hard
   gate, not a nicety: reproduce a number the user knows, **verify the denominator
   independently** (a right-looking ratio can hide a wrong population), and
   **spot-check one entity end-to-end** (an aggregate computed from a mis-decode
   agrees with itself — only one traced entity exposes it). All three before you
   author (§5).
