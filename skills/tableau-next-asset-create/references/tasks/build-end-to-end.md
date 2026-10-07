# Task: Build a semantic model + dashboard end-to-end (greenfield)

The greenfield "nothing is modeled yet" path — analyze flat files, a table
on an existing connection, or other unmodeled data all the way through to a
dashboard.

This guide is the **gate map** for the greenfield flow, not a second copy of the
spine: it declares which gates fire across the whole build (below), maps each step
to the gate it enforces and the slice-guide that can be entered standalone, then
hands the actual procedure to `../build-workflow.md`. The router points here rather
than straight to `build-workflow.md` so the full-flow gate coverage is asserted
before Step 0 and the mid-flow entry points stay discoverable.

## Gates (assert before any tool call) → `../shared-gates.md`

Required across the flow: **G1, G2, G3, G4, G5, G6, G7, G8**. Each step below
inherits the gates its action needs (per the coverage matrix). At minimum:

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G6** *first*: profile before you model — grain, field roles, cardinality,
  additivity, date roles. For a large/wide/cryptic file, infer its schema before
  creating the data stream, then do value-level checks with `run_query`.
- **G2** before adding any *discovered* object. For a DMO you just created and
  mapped in this flow, poll `run_query` until `<dmo>__dlm` exists (`COUNT = 0`
  is READY; `42P01` keep polling) — `shared-gates.md` G2. Keep the discovered
  row-count gate as-is.
- **G3** before writing any apiName you did not just read back.
- **G4 + G7** once ≥2 objects exist: every object joined, every join row-verified.
- **G5** on every component you create (metrics first).
- **G7 + G8** before any `create_visualization`.

## Steps

The full procedural spine with verified per-tool payloads and inline gotchas lives
in **`../build-workflow.md`** — load it and follow Step 0 → Step 11:

- **Step 0 — Ingest** (CSV/Excel upload **or** existing database connection) →
  see `../ingest-and-metric-gotchas.md` §A (file) / §C (connection) and
  `ingest-flat-file.md` standalone. File chain: `get_upload_connection` →
  `infer_object_schema` → `create_data_stream` → `run_data_stream` → wait DLO
  Active → SCHEMA REALITY CHECK + real Primary Key read-back →
  `create_data_model_object` (unsuffixed name; platform adds `__dlm`) → wait
  DMO Ready → `create_dlo_to_dmo_mapping` → poll `run_query` until
  `<dmo>__dlm` exists (`get_dlo_to_dmo_mapping_status` `ACTIVE` is metadata
  only). Connection chain: `list_connections` →
  `list_data_connection_objects` → `infer_object_schema` →
  `create_data_stream` (`dataAccessMode: "Direct_Access"`, connection
  developer name) → `run_data_stream` `interactive: false` → then the same
  DMO / mapping tail.
- **Step 0.5 / 1 — Profile + discover** (G6) → `../data-understanding.md`,
  `../large-flat-file-handling.md`; or `profile-dataset.md`.
- **Step 2 — Verify data presence** (G2) → `../empty-source-handling.md`. For
  DMOs you just created and mapped in Step 0, wait until `run_query` succeeds
  on `__dlm` (`COUNT = 0` is READY); keep the discovered-source row-count
  gate as-is.
- **Step 3 — Confirm join keys** (G7) with a real JOIN row-count.
- **Steps 4–6 — Create model with nested fields, add remaining objects, add
  relationships** (G2, G3, G4, G5) → `../sdm-tool-reference.md`; or
  `edit-sdm.md`. Bind via one `create_semantic_model` with explicit
  `semanticDimensions[]` / `semanticMeasurements[]` (`shouldIncludeAllFields:
  false`); do not N-call `add_semantic_model_dimension` / `_measure`.
- **Step 7 — Validate (BLOCKING)** (G4, G7): every object joined +
  `run_semantic_query` returns real rows; empty → STOP.
- **Step 8 — Enrich** (G5, G6, G7): calc dimensions/measures + metrics →
  `../semantic-query-and-enrichment.md`; metric gotchas `../ingest-and-metric-gotchas.md`
  §B; or `enrich-model.md`.
- **Step 9 — Query the model** (G7) → `../semantic-query-and-enrichment.md`; or
  `query-model.md`.
- **Step 10 — Create visualizations** (G7, G8) → `../dashboard-design-principles.md`
  (narrative first), `../viz-authoring.md`; or `create-viz.md`.
- **Step 11 — Build the dashboard** (G7 transitive, G8) → `../dashboard-authoring.md`;
  or `build-dashboard.md`.
