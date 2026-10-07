# Task: Ingest a file or existing connection → DLO → DMO

Ingest local CSV/Excel **or** a table from an existing Data Cloud connection
into Data Lake Objects and Data Model Objects — the front half that the SDM
build assumes already exists. Entry point 1. (Entry point 3 — probing a
large/cryptic file *before* ingesting — is diagnostic and lives in
`profile-dataset.md` / `../large-flat-file-handling.md`; this guide's G6 bullet
below just points there.)

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1, G2, G5-light** · Conditional: **G6** (◐, for a large/cryptic file)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G6** (◐): if the file is large/wide/cryptic, use `infer_object_schema`
  FIRST, decode the column-naming grammar, then verify one known number with
  `run_query` after ingest (`../large-flat-file-handling.md`). Do not slurp the
  whole file into context or add a local parsing step.
- **G2 (post-ingest):** `run_data_stream` is mandatory; then wait until the DLO
  is Active and the DMO is Ready. Mapping **query** readiness is `run_query`
  against `<dmo>__dlm` (`42P01` keep polling; `COUNT = 0` is READY).
  `get_dlo_to_dmo_mapping_status` `ACTIVE` is metadata only — not that gate
  (`shared-gates.md` G2). For a self-created mapped DMO, do not refuse SDM
  create because `COUNT = 0`; do not proceed while the table is missing.
- **G5-light:** file-upload DLOs **and** DMOs require `category: "Other"` (never
  `"Engagement"`); DLO→DMO mapping field dev names carry a literal `__c` on both
  sides — copy them from the materialized table, not from `get_data_stream`.
  Full AI-readiness metadata lands later when objects/fields are added.
- **Schema confirmation:** after `infer_object_schema`, present the fields and
  **wait for the user to explicitly confirm** or adjust types / primary key /
  skipped columns. Do not call `create_data_stream` until they approve or say
  to proceed.

## Steps

The fixed, ordered ingestion chain with verified payloads is in
**`../ingest-and-metric-gotchas.md`**:

**File CSV / Excel — §A:**
`get_upload_connection` → `generate_presigned_credential` (per file; PUT with
decoded URL + optional `headers`; opaque `parentDirectory` /
`importDirectory`; re-call if `expiryTime` passed) → Excel: `list_data_connection_objects` for sheets →
`infer_object_schema` → **confirm schema** → `create_data_stream` (`*__dll`
DLO, including `mappings` / `refreshConfig` / `advancedAttributes`) →
**`run_data_stream` + wait until Active** → SCHEMA REALITY CHECK
(materialized DLO, not `get_data_stream`) + real Primary Key read-back →
`create_data_model_object` (unsuffixed name — `Orders`, not
`Orders__dlm`; the platform adds `__dlm`) → **wait until Ready** →
`create_dlo_to_dmo_mapping` → inspect mapping
(`get_dlo_to_dmo_mapping_status` for `ERROR`) → **poll `run_query` until
`<dmo>__dlm` exists** (`COUNT = 0` is READY).

**Existing database / lakehouse connection — §C:**
`list_connections` (exact `connectorType` casing) → optional
`test_existing_connection` (once; `9cg` id) → `list_data_connection_objects`
→ `infer_object_schema` (table `resourceName`; uppercase `SCHEMA`/`DATABASE`)
→ **confirm schema** → `create_data_stream` with `dataAccessMode:
"Direct_Access"` and the connection **developer name** → `run_data_stream`
`interactive: false` → then the same SCHEMA REALITY CHECK → DMO → mapping
tail as §A.

After `run_query` succeeds on the `__dlm` table, continue with `edit-sdm.md`
(build the model) or `build-end-to-end.md` Step 4. `COUNT = 0` on that
successful query is READY for these self-created DMOs (G2); `42P01` is not.
Ingestion gotchas (status waits, SCHEMA REALITY CHECK, `category:"Other"`,
universal-`__c`, stream payload traps) are in
`../ingest-and-metric-gotchas.md` §A / §C.
