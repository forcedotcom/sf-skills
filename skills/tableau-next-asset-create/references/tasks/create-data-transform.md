# Task: Create or update a Data Cloud SQL transform

Materialize a **derived** DLO/DMO from one or more source objects via a Data
Cloud SQL (DCSQL) transform. Use this when the user wants a new derived table
or to change how an existing transform-backed table is produced — not for
CSV ingest (`ingest-flat-file.md`) and not for semantic-model calculated
fields (`enrich-model.md`).

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1** · Conditional: **G2** (◐, source object must exist)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **Confirmation (this guide):** never call `create_data_transform`,
  `update_data_transform`, or `run_data_transform` without an explicit "yes"
  after showing SQL + preview. Run is a **separate** yes from create/update.
- **G2** (◐): the **source** relation must be a real `__dll` / `__dlm` from
  `browse_data_assets`. Do not invent the apiName.

## Steps

Payloads, immutable-vs-editable fields, timeout recovery, SparkInternal
substitutions, and error strings are in
**`../data-transform-gotchas.md`**.

1. Disambiguate: **create** if the output object does not exist; **update**
   if it is already transform-backed (never a second transform on that table).
2. Resolve the source `assetApiName` (with suffix). Multiple matches → STOP
   and ask.
3. Generate DCSQL; validate (`validate_data_transform` and/or `run_query`
   with `rowLimit: 10`). **Every output SELECT alias / `fields[].name` must
   be `__c`-suffixed** — validate does not error on a bare alias, it
   silently renames the derived field, and the mismatch only fails later
   on `run_data_transform` (see the deep ref).
4. Confirm with the user (SQL + preview + output name).
5. Create (full nested `definitions`/`manifest`) or update (GET first; full
   replace; copy 🔒 fields). Create, update, and validate send the **same
   flat body** (`name` / `type` / `definitions` at the top level — no
   `dataTransformObject` / `dataTransform` envelope). On update timeout, GET
   and compare `compiled_code` — do not blindly retry.
6. Create-only: add the new output object to the workspace the user named
   (else list and ask).
7. Confirm, then `run_data_transform` only after the transform is `ACTIVE`
   (not `PROCESSING`). Runs may be sync or async; poll
   `get_data_transform_run_history` until the run succeeds or fails
   (typically 10–15 minutes). If status looks stuck, call
   `refresh_data_transform_status` then poll history again. Do **not** treat
   `get_data_transform` `ACTIVE` as “rows are ready.” BATCH definitions use
   `DCSQL`; STREAMING uses `SQL`. DMO outputs need `KQ_<pk>` (see the deep
   ref).
