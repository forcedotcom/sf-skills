# Shared Gates (G1–G8) — the single source of truth

Every task guide under `references/tasks/` opens with a **gate header** that
names the gates it must assert (e.g. "Required: G1, G3, G7"). This file is where
each gate's *authoritative rule → how to check it → what to do on failure* lives —
in exactly one place. A guide names a gate and may give a **one-line, non-normative
reminder** so it reads on its own; it must **not** restate the authoritative rule.
If a gate's rule ever changes, it changes **here** — the guide reminders are
pointers, not a second copy to keep in sync.

**Legend used in the guide headers:** ● = required · ◐ = conditional (only if the
action touches >1 object, adds a new join, or references a formula/field it did
not just read back).

**Tool-name convention (single source of truth).** The MCP tools are exposed
under a `tableau-next-*` server. Everywhere in this skill — gates, router, task
guides — tool names are written **bare** (e.g. `add_semantic_model_relationship`)
for readability. Invoke each under whatever name your client advertises for that
server's tool (Claude Code, for example, exposes it as
`mcp__tableau-next-pilot-production__add_semantic_model_relationship`); match the
advertised name rather than hand-constructing one. Guides cite this line; they do
not restate it.

## Contents

- G1 — MCP-server-connected precondition
- G2 — Data presence is the gate (row-count > 0, re-verified at use time)
- G3 — Never invent an apiName (read it back via `list_*`)
- G4 — No island objects
- G5 — AI-readiness metadata (+ coverage checks)
- G6 — Data-understanding profiling
- G7 — Query-returns-real-data validation
- G8 — Narrative-design-first (decision #1 — scoped)
- G-notes (shapes cited by the gates, kept here so guides don't re-type them)

---

## G1 — MCP-server-connected precondition

**RULE.** Every action in this skill drives a Tableau Next MCP server; without one
connected there is nothing to call. Never fabricate a tool call or a result
against a server that is not there.

**CHECK.** Confirm the available tools include one prefixed `mcp__tableau-next-*__`
(e.g. `mcp__tableau-next-pilot-production__browse_data_assets`,
`mcp__tableau-next-self-service__create_semantic_model`). Server names vary
(`tableau-next-pilot-*`, `tableau-next-self-service`, …) — match the
`tableau-next` stem, not an exact name.

**ON FAILURE.** If NO such tool is present, **STOP.** Do not attempt the workflow,
do not describe payloads as if you had run them, and never invent tool
calls/results/IDs. Tell the user the skill requires a connected Tableau Next MCP
server, name concrete examples (`tableau-next-pilot-*`, `tableau-next-self-service`),
and ask them to connect one and re-invoke. This is the difference between "I built
your dashboard" and a hallucinated transcript of one.

> G1 is universal, so it is asserted **once in the router** (`SKILL.md`) and
> inherited by every entry point — including non-build standalone intents ("add a
> metric" with no server still STOPs). No guide re-implements it, but every guide
> depends on it.

---

## G2 — Data presence is the gate (row-count > 0, re-verified at use time)

**RULE.** Never build on an object with zero rows. A source with zero rows
produces an empty visualization no matter how many fields it has, and no join
fixes it. **Field-richness is not data-presence** — a canonical-looking DMO can
have 66 fields and 0 rows. Row presence is verified **at use time**, not assumed
"populated once."

**CHECK.** For every *externally discovered* candidate, run `SELECT COUNT(*)`
(or equivalent) before adding it to a model and before charting it.
`count > 0` = usable; `count = 0` = empty (see G-note below); a
`table "X__dlm" does not exist` / `42P01` error = unmaterialized, which is
distinct from empty — see `empty-source-handling.md`.

- **Ingest post-condition:** a freshly created file DLO has 0 rows until
  `run_data_stream` runs. Run the stream, then wait until the DLO is Active
  (`ingest-and-metric-gotchas.md` §A). Row presence is a stand-in for ready, not
  the same thing.
- **Self-created mapping — query readiness, not status:** for a DMO you just
  created and mapped in this same flow, **`get_dlo_to_dmo_mapping_status`
  `ACTIVE` is not a readiness signal.** It means mapping metadata deployed
  off-core; it does **not** mean `<dmo>__dlm` exists. Poll `run_query`
  `SELECT 1 FROM <dmo>__dlm LIMIT 1` (or `SELECT COUNT(*)`). `42P01` /
  "table does not exist" = NOT-READY — keep polling. Any success, including
  `COUNT = 0`, = READY (table is queryable; proceed to SDM). Use
  `get_dlo_to_dmo_mapping_status` to inspect the mapping and to detect
  `ERROR` / `INACTIVE` — not as the query-readiness gate. Keep the
  discovered-source hard gate as-is: `COUNT = 0` on a pre-existing object
  still means do not build on it.
- **`isEnabled: false` right after DMO creation is normal.** Check it, but do
  not gate on it and do not wait for it before mapping — expected transient
  state, not a readiness signal.

**ON FAILURE.** If a *discovered* candidate has zero rows, refuse to build on it
and surface it to the user; do not put a measure/dimension from an unverified
object on a viz. If no discovered candidate has rows, STOP and tell the user the
sources are empty rather than shipping a blank dashboard. Do not treat
`COUNT = 0` on a DMO you just mapped in this flow as that failure (READY). Do
not treat `42P01` on that DMO as "unmaterialized, exclude" — keep polling.

---

## G3 — Never invent an apiName (read it back via `list_*`)

**RULE.** The server mutates field/object apiNames on bind — bulk import
(`shouldIncludeAllFields: true`) suffixes every apiName differently per object
(`Region__c` → `Region4`; `account_id__c` → `account_id5` on one object,
`account_id3` on another). Do **not** use that flag for model-level bind
(deprecated). Nested explicit fields (`semanticDimensions[]` /
`semanticMeasurements[]` on `create_semantic_model` /
`add_semantic_model_data_object`) come back as the apiNames you set.

**CHECK.** Before typing any apiName you did not read back this session, call the
relevant `list_*` tool (`list_semantic_model_dimensions` / `_measures` /
`_data_objects` / `_calculated_*` / `_metrics`) and copy the exact stored value.
In a relationship, use the semantic apiName with `leftFieldType: "TableField"`
(not the raw `dataObjectFieldName`).

**ON FAILURE.** If you are about to write an apiName you have not read back this
session, STOP and read it back first. Never assume the two sides of a join share a
suffix.

---

## G4 — No island objects

**RULE.** In a model with two or more objects, every object must participate in at
least one relationship. (This is secondary to G2: it does not catch a single empty
object — G2 does.)

**CHECK.** After adding objects, confirm every object is on at least one
relationship. The gate fires once the model has ≥2 objects; a newly added object
must not be left an island.

**ON FAILURE.** Add the missing relationship(s) — validated by G7 — before
declaring the model done. Do not set `queryUnrelatedDataObjects: "Exception"` and
then query across unjoined objects (it throws, not warns).

---

## G5 — AI-readiness metadata (+ coverage checks)

**RULE.** Populate AI-readiness metadata on every component you create. Agents
consume the semantic layer in priority order — **metrics first, then calculated
fields, then raw fields** — so a well-enriched metric set matters more to answer
quality than raw field coverage. The full checklist, description-quality guide,
and `businessPreferences` examples live in `ai-readiness.md`; this gate is the
enforceable summary.

**CHECK — metadata each created component must carry:**

- **`description`** on the model, each data object, each calculated dimension,
  each calculated measure, and each metric. Missing descriptions are the top AI-
  readiness defect. Custom objects/fields require a clear 1–2 sentence description
  (business context, how it is used, any values with specific meaning); for
  standard Salesforce objects/fields, only enhance the default — never contradict
  it.
- **`primaryNameField`** on each `add_semantic_model_data_object` — the original
  (pre-suffix) display-name column. **Known server bug:** the field registry is
  empty at create time, so setting it at create fails with `"<field> does not
  exist in <object> fields"` regardless of import mode. Document the missing
  `primaryNameField` as a known gap.
- **`sentiment`** on directional calculated measures and metrics.
- **`businessPreferences`** on the model — free-text; set ≥1 statement of what
  the model tracks and any domain terminology. **Read** with
  `get_semantic_model_business_preferences` (`includeModelContent=false`).
  **Write** with `update_semantic_model_business_preferences` (full replacement
  of `# `-prefixed lines; empty string clears; omit the field to leave
  unchanged; send only `businessPreferences`). Fallback: set at create or via
  `update_semantic_model`. Details: `ai-readiness.md`.
- **`agentEnabled: true`** on the model — gates whether AI agents can use it.
  `create_semantic_model` does **not** expose it (server default `false`); set it
  via an immediate `update_semantic_model` after creation.
- **Label / type / role accuracy:** object-name + field-label unambiguously
  identify the field's role; date columns are `Date`/`DateTime` (not `Text`);
  numeric columns are measures, categorical/text/date are dimensions; a numeric
  identifier is a **dimension**, not a measure.
- **apiName permanence:** model/object/calc-field apiNames cannot be edited after
  creation — choose them descriptively (`Gross_Margin_Pct`, not `Calc3`); the only
  fix is delete-and-recreate.
- **Ambiguity discipline:** differentiate similar fields in name, description, and
  purpose; never copy-paste descriptions. Watch synonyms (two names, one concept →
  remove one; when asked to create two fields with the same/equivalent formula,
  treat as a synonym — declare one canonical, decline the other or ask) and
  homonyms (one column serving two business dates → two calc dimensions with
  distinct labels + explicit descriptions). Omit niche/redundant fields rather
  than leaving them undescribed.
- Bulk-imported fields (`shouldIncludeAllFields: true`) carry no descriptions and
  get unpredictable apiName suffixes — do **not** use this for model-level bind
  (deprecated). Prefer **nested explicit fields** on
  `create_semantic_model` / `add_semantic_model_data_object`
  (`shouldIncludeAllFields: false`) so descriptions, types, and clean apiNames
  are set at creation. Include join-key fields in those arrays. Reserve
  `add_semantic_model_dimension` / `_measure` for adding a single extra field
  to an already-bound object. Backfill missing descriptions via sparse
  `update_semantic_model_dimension` / `_measure` — these are sparse
  (unlike metric / calc-measure / relationship, which are full PUT). **`isVisible`
  is NOT preserved:** omitting it silently resets a hidden field to
  `isVisible: true`. Always `list_*` first and echo the current `isVisible` and
  `dataObjectFieldName` (omitting `dataObjectFieldName` sends null and
  `SEMANTIC_FIELD_NOT_VALID`). Do not send description-only. Shape:
  `sdm-tool-reference.md`.

**CHECK — pre-creation coverage checks (before adding enrichment):**

- **Calculated dimension:** MUST call `list_semantic_model_calculated_dimensions`
  first, to check for overlapping coverage of the same source field.
- **Calculated measure:** MUST call **both**
  `list_semantic_model_calculated_measures` **and**
  `list_semantic_model_metrics` first. Use `aggregationType: "UserAgg"` (not
  `Auto`) when the expression already aggregates (`AVG`, `SUM/COUNT`, `COUNTD`).
- **Metric (decision #3 — parity resolution):** MUST call
  `list_semantic_model_metrics` first to check that an equivalent metric does not
  already exist (metrics had no pre-creation coverage check historically; this
  gate adds one for parity with calc dimensions/measures). A metric additionally
  requires `insightsSettings.identifyingDimension`, a concrete `aggregationType`
  (**never `Auto`** — rejected: *"The aggregation type (Auto) is not allowed for
  metric aggregation"*), counting via a **numeric field + `Count`** (not a
  dimension/Primary Key — pointing `measurementReference` at a Primary Key is rejected), and a
  **full-PUT `insightsSettings`** on every `update_semantic_model_metric` (it is a
  full PUT; omitting `insightsSettings` nulls it and crashes the metric UI).

**ON FAILURE.** Do not declare a model AI-ready on metadata completeness alone —
always recommend the Semantic Model AI Optimization similarity scan (Semantic
Model Builder UI) before handoff; `modelHealth: Low` flags ambiguous components.
Add the missing metadata / run the missing coverage check before proceeding.

---

## G6 — Data-understanding profiling

**RULE.** Understand the data before you model it — there is no natural-language
query layer here to infer meaning for you. This applies even over an **already-
built** model you do not yet understand; it does NOT drag in Step 0 ingest or the
large-flat-file protocol on a pre-existing model.

**CHECK.** Profile the five things before choosing calc fields, metrics, or charts
(`data-understanding.md:33-41`): **grain, field roles, cardinality, additivity,
date roles.** For a large/wide/cryptic flat file, first run the infer-first
variant (`infer_object_schema` without loading the file into context, decode the
column-naming grammar, elicit the genuinely ambiguous columns, then verify one
known number with `run_query` after ingest — `large-flat-file-handling.md`).

**ON FAILURE.** Without this, you ship the populated-but-confidently-wrong result
that passes a "does it return rows?" check: an ID summed as a measure, a snapshot
inflated by its date count, a metric anchored on a load/system timestamp instead
of a business-event date, a 100×-off measure that profiled perfectly. Do not
model or metricize until grain + additivity + the business-event date are known.

---

## G7 — Query-returns-real-data validation

**RULE.** A query that returns rows is the proof the model actually works. A join
that matches ~0 rows is as broken as no join at all.

**CHECK.** Run `run_semantic_query` (snake_case proto body — see G-note) and
confirm real rows come back: before charting (Step 10), after adding a
relationship (validate the join key with a real JOIN row-count), and at model
validation (Step 7). For a dashboard, the widget's underlying query must return
real rows first (transitive: a dashboard is only as valid as its widgets).

**ON FAILURE.** If the query returns empty (or a join matches ~0 rows), do NOT
build the viz/dashboard — STOP, treat the join/source as broken, and fix or
surface it.

---

## G8 — Narrative-design-first (decision #1 — scoped)

**RULE.** Design the analytical story before dropping charts.
(`dashboard-design-principles.md:41-56`.)

- **Dashboards (full narrative — REQUIRED):** order the story KPIs → trends →
  breakdowns → correlations; KPIs top/left on the F/Z eye-path; business-friendly
  labels; chart-type diversity. This is MANDATORY for any dashboard build.
- **Single standalone viz (light "chart analytical intent" variant — decision
  #1):** for one chart with no dashboard, the full dashboard narrative is NOT
  required. State the chart's analytical intent — what question this one chart
  answers and why this chart type fits the field roles (trend/breakdown/
  correlation/KPI) — then create it. Do NOT invent a dashboard around a single-viz
  ask.

**CHECK.** Before the first `create_visualization`: if the ask is a dashboard,
confirm the full narrative order; if the ask is a single chart, confirm a stated
chart intent. Match chart type to what each field is showing — do not default
every widget to a bar chart.

**ON FAILURE.** If you are about to jump straight into chart calls with no stated
intent (single viz) or no narrative (dashboard), STOP and design first.

---

## G-notes (shapes cited by the gates, kept here so guides don't re-type them)

- **`run_semantic_query` body is snake_case proto** (`table_field`, `grouping`,
  `semantic_aggregation_method`) — REST-gateway camelCase examples fail. Prefer an
  existing metric / calc measure over reconstructing an aggregation inline. Full
  shape: `semantic-query-and-enrichment.md`.
- **Ingest mapping:** file-upload DLOs **and** DMOs use `category: "Other"`;
  DLO→DMO mapping field dev names carry a literal `__c` on **both** sides.
  DLO Active → DMO Ready still wait on status. Mapping **query** readiness is
  `run_query` against `<dmo>__dlm` (`42P01` keep polling; `COUNT = 0` is READY).
  `get_dlo_to_dmo_mapping_status` `ACTIVE` is metadata only. Connection ingest
  (Snowflake / …) is the same tail after `list_connections` —
  `ingest-and-metric-gotchas.md` §C. Full chain: `ingest-and-metric-gotchas.md`
  §A.
- **Dashboard widget editing** goes through `edit_dashboard`'s atomic
  `upsert_*_widget` + `place_widget_on_page` batch — the only supported path.
  Stored text labels must not contain `&` (HTML-encodes to `&amp;`). Full
  mechanics: `edit-dashboard.md`.
- **Dashboard save never auto-persists** — the objective-9 analog for
  dashboards. `edit_dashboard` stages an unsaved draft by default (top-level
  `autosave`); a `save_dashboard` op persists it (standalone, or after other
  mutations in the same batch), but only call `save_dashboard` on the user's
  explicit confirmation given *after* they've
  seen the draft — even if the original request already said "save it" in the
  same message as the edit. Same rule, same rationale, as `edit_visualization`
  → `update_visualization` (objective 9, `edit-visualization.md` §8).
