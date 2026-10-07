# Task: Enrich the model — calculated dimension / measure / metric

Add a **calculated** dimension or measure, or create a metric, on a model that
already exists. This is the guardrail-densest entry point. Entry points 11, 12, 13.

## Gates (assert before any tool call) → `../shared-gates.md`

This guide serves three intents; G7 required-ness differs per intent:

- **Add calculated dimension (entry 11):** Required **G1, G2, G3, G5, G6** ·
  Conditional **G7** (◐, only if the calc references data you haven't just
  verified with `run_semantic_query`).
- **Add calculated measure (entry 12):** Required **G1, G2, G3, G5, G6** ·
  Conditional **G7** (◐, same rule as entry 11).
- **Create metric (entry 13):** Required **G1, G2, G3, G5, G6, G7** — a metric is
  always query-facing, so G7 is unconditional here.

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G6:** confirm grain + additivity + that your date is a **business-event date**
  (`../data-understanding.md`) — a metric on a load/system/partition timestamp is
  wrong even if it returns rows. Applies on a pre-existing model; do NOT re-ingest.
- **G5:** run the per-component coverage `list_*` check FIRST (calc dimension, calc
  measure, and metric each require different `list_*` calls) and set the required
  metric shape — the authoritative sub-rules (`UserAgg`-not-`Auto`, concrete
  `aggregationType`, `identifyingDimension`, count-via-numeric, full-PUT
  `insightsSettings`) are in `shared-gates.md` G5. Don't proceed without it.
- **G3:** read back exact apiNames via `list_*` before referencing them in a
  formula or `measurementReference`.
- **G2:** the underlying object has rows (required for all three intents).
- **G7:** `run_semantic_query` returns real data before you trust the
  calculation — required for a metric (entry 13); for a calc dimension/measure
  (entries 11/12) only re-verify if you haven't already confirmed the query
  path on this data (see header above).

## Steps

Worked calc-dimension / calc-measure / metric payloads and the field-shape matrix
are in **`../semantic-query-and-enrichment.md`**; the extra metric gotchas
(`Auto` rejection, `identifyingDimension`, count-by-numeric, the row-level-ratio
`Average` case) are in `../ingest-and-metric-gotchas.md` §B; `../build-workflow.md` Step 8
is the spine.

**Identify the analysis intent first** (trend / comparison / part-to-whole /
correlation / forecast — see `create-viz.md` / `viz-authoring.md` §3) so
enrichment produces the fields that intent needs: a business-meaningful date
anchor for trend/forecast, a slicing dimension for part-to-whole, two measures
for correlation.

- **Calc dimension** — `add_semantic_model_calculated_dimension` (after the
  coverage `list_*`); distinct label + description (homonym dates → two dims).
- **Calc measure** — `add_semantic_model_calculated_measure`; `UserAgg` when the
  expression aggregates. Inputs are a **JSON object, NOT a stringified JSON
  string**. Do not set `externalLevel` / `externalConnectionApiName` unless
  connecting to an external definition. Updates are **full PUT**: GET via
  `get_semantic_model_calculated_measure`, then send the complete object
  (omitted fields reset to defaults).
- **Metric** — `add_semantic_model_metric` with the full verified shape (concrete
  `aggregationType`, `identifyingDimension`, count-via-numeric, `sentiment`).
  `identifyingDimension` MAY point at a field on a **joined** object
  (cross-object). Create the metric by default when the request implies a
  tracked number and a meaningful event date exists. Updates are full PUT
  (GET via `get_semantic_model_metric` first; `{description}` → `MasterLabel`
  means send `label`).

When asked to create two fields with the same/equivalent formula, treat it as a
synonym (G5): declare one canonical, decline or ask about the other — don't
silently create both.
