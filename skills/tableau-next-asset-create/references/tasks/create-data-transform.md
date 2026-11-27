# Task: Read, create, or update a data transform

Inspect an existing transform, create a derived DLO/DMO from one or more
sources, or update an existing transform-backed output. For CSV ingestion use
`ingest-flat-file.md`; for a semantic-model calculation use `enrich-model.md`.

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1, G3** · Conditional: **G2** (◐, for externally discovered
sources)

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for
  that `tableau-next-*` server tool (`shared-gates.md`).
- **G3:** use tool-verified identifiers; resolve labels in the steps below.
- **G2** (◐): do not build on an empty or unmaterialized discovered source.
- **Confirmation (this guide):** create, update, and run each require explicit
  confirmation. Reading does not. Run requires a separate confirmation after
  create/update.

## Steps

Payload construction, immutable update fields, timeout recovery, and the
run-time DCSQL rules are in **`../data-transform-gotchas.md`**.

Treat `local_rate_limited` as a transient server response, not evidence that
the SQL is invalid. Keep the request unchanged, wait with increasing backoff,
and make only a bounded number of retries. Diagnose or rewrite the SQL only
when the server returns a query or validation error.

Choose the **Read**, **Create**, or **Update** path by intent. Source inspection,
SQL preview, and validation apply to Create and Update.

Any edit to SQL, fields, manifest, or output metadata invalidates the earlier
validation. Re-preview changed SQL, then validate the exact final body again
before approval or create/update. Never retry creation with a revised body
that has not been re-validated.

**Read (existing transform; read-only)**

Apply `../data-transform-gotchas.md` §Reading saved transforms when reporting
history, schedule, or saved definition types. Resolve an unverified transform
label with `browse_data_assets_v2`, then choose by intent: definition/outputs →
`get_data_transform`; run records → `get_data_transform_run_history`; current
status → `refresh_data_transform_status`; schedule →
`get_data_transform_schedule`.

**Create**

1. **Resolve sources.** Resolve every source label separately with
   `browse_data_assets_v2` unless its exact id/apiName is already tool-verified.
   Preserve returned `__dll` / `__dlm` suffixes. No match → report and stop;
   ambiguous matches → ask. A matching label is still not an identifier.
2. **Inspect columns.** Inspect every resolved source with a bounded
   `run_query`. Collect its complete column inventory and a small sample.
   `SELECT *` is allowed for inspection only; never save it as the transform
   SQL.
3. **Build and preview SQL.** Build explicit-column DCSQL and pass
   **`../data-transform-gotchas.md`** §Before returning SQL. Preview the
   complete transformation with `run_query` and inspect rows, types, joins,
   and grain. For joins or unions, preview the combined result—not only each
   source.
4. **Validate the request.** Build the exact flat create body from
   **`../data-transform-gotchas.md`** (§Payload (reference shape)) and pass it
   unchanged to `validate_data_transform`. Both checks must pass: `run_query`
   previews sampled results; transform validation checks the request contract.
   Fix every returned validation issue before creation. Neither check overrides
   the DCSQL rules. Apply the output-field naming and DMO qualifier rules in
   the payload reference.
5. **Confirm and create.** Show the resolved sources, output name, SQL, and a
   short result preview. Call `create_data_transform` only after the user
   confirms.
6. **Offer next actions.** After creation, offer—but never automatically
   perform—the optional workspace and data-space actions below.

**Update**

1. **Resolve the transform.** Resolve its label with `browse_data_assets_v2`
   unless its exact id/apiName is already tool-verified, then call
   `get_data_transform`.
2. **Preserve the contract.** Treat the update as a full replacement. Copy
   every immutable field exactly as described in
   **`../data-transform-gotchas.md`** (§Payload (reference shape)).
   A saved `STL` definition can be read here, but cannot be rewritten through
   this SQL workflow. Stop and explain that limitation rather than changing
   its immutable definition type or substituting SQL for its definition.
3. **Inspect sources.** Resolve and inspect every referenced DLO/DMO using
   Create steps 1–2.
4. **Build and preview SQL.** Apply Create step 3 to the **whole** revised
   SQL, not only the changed lines—saved SQL can predate the current rules.
   Preview the complete revised result with `run_query`.
5. **Validate the request.** Pass the exact full replacement body to
   `validate_data_transform`. Apply the same `__c` and DCSQL rule checks as
   Create.
6. **Confirm and update.** Show the revised SQL and preview. Call
   `update_data_transform` only after the user confirms. Never create a second
   transform as an update fallback. On timeout, follow
   **`../data-transform-gotchas.md`** (§Timeout recovery): read the transform
   back and compare the requested changes before retrying.

**Optional registration**

- **Workspace:** call `list_workspaces` and let the user choose unless the exact
  workspace id/apiName is already verified. Convert the transform's `1dt…` id
  with `get_data_transform_setup_id`, then pass the returned `1Dw…` setup id to
  `add_workspace_asset` as `assetId`. Use `assetType:
  "MktDataTransformSetup"` and `assetUsageType: "Created"` for a transform
  created in this workflow; otherwise use `"Referenced"`. Pass flat top-level
  arguments, not `body`.
- **Data space:** only output DLOs ending in `__dll` are accepted. Call
  `list_data_spaces` and let the user choose by label. Pass the returned `name`
  or `id` to `add_to_data_space` as `idOrName`, with
  `members: { members: [{ memberName: "<output__dll>" }] }`. Check the
  per-member errors list; empty means all DLOs were added.
- If the connected server does not advertise an operation, explain that the
  user must complete it in Tableau Next.

**Run**

1. **Wait for readiness.** Wait until the transform is `ACTIVE`, not
   `PROCESSING`.
2. **Confirm the run.** Ask separately whether to run it. Creation or update
   confirmation does not authorize a run.
3. **Run and monitor.** After confirmation, call `run_data_transform` and poll
   `get_data_transform_run_history` until success or failure. If it appears
   stuck, call `refresh_data_transform_status` and continue polling history.

`ACTIVE` proves only that the definition is ready; it does not prove that a
run completed or that output rows are ready.
