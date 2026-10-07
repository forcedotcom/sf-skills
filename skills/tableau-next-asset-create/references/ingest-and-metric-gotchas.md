# Ingestion & Metric Gotchas — verified payloads

Load this for **Step 0** (file or existing-connection ingestion → DLO → DMO →
mapping) and for **Step 8** (metric creation gotchas).

For visualization authoring (Step 10), see `references/viz-authoring.md`.
For dashboard building (Step 11), see `references/dashboard-authoring.md`.

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected.

## Contents

Intent → heading (this file is cited by `ingest-flat-file.md` and
`enrich-model.md`; it is not a first hop):

- File CSV / Excel ingest (upload → DLO → DMO → mapping) → §A
- Presigned PUT / SfDrive (`&amp;`, opaque directories, `expiryTime`, 400 codes) → §A step 2
- Excel sheets vs CSV → §A step 3
- `create_data_stream` payload traps (format, mappings, timeout, name collision) → §A step 4 + Ingestion gotchas
- Existing database / lakehouse connection ingest (Snowflake, …) → §C
- Table already `inUse` by another stream → opaque `INTERNAL_ERROR` on create → §C step 5
- `Direct_Access` streams never call `run_data_stream` — go `ACTIVE` → `run_query` → §C step 6
- Connection list / test (`connectorType` casing, `9cg` id, paging bounds) → §C
- By-id connection lookup (`get_connection` typed 400 vs 404) → §C step 1
- DMO create + mapping traps (`__dlm`, Engagement event field, duplicate map, `ACTIVE` ≠ table exists) → §A steps 8–11 + Ingestion gotchas
- Metric creation (`Auto`, identifying dimension, count-via-numeric) → §B

---

## A. Ingest flat files (CSV / upload) → DLO → DMO → mapping

This is the front half that SKILL.md Steps 1–7 assume already exists. Run it
when the user points at local files instead of existing data assets. The order
is fixed; each tool feeds the next.

1. **`get_upload_connection`** `{ "connectorType": "UploadedFiles" }` → returns
   the `connectionId` used by every `infer_object_schema` call. Prefer this
   singleton lookup over `list_connections` for the file-upload flow.
2. **`generate_presigned_credential`** `{ "fileName": "fact_orders.csv" }` once
   **per file** → returns the presigned upload target plus opaque
   `parentDirectory` and `importDirectory`. PUT the file body to `presignedUrl`
   out of band:
   - Decode HTML-encoded `&amp;` in the URL to `&` before the PUT.
   - If the response includes `headers`, attach them on the PUT (BYOK).
   - Pass `parentDirectory` and `importDirectory` **verbatim** into
     `infer_object_schema` and `create_data_stream`. Never construct, trim, or
     substitute them — downstream fails with *"Given file is not present in the given location"*.
   - `sfdrive_not_provisioned` (503): do **not** retry; uploads are not enabled
     for the org. `sfdrive_unavailable` (503) may be retried once; if it
     persists, treat it as not-provisioned.
   - `invalid_file_name` (400): empty name, missing extension, or path-traversal
     characters (`..`, `/`, `\`). `unsupported_file_type` (400): extension is
     present but not `.csv` / `.xls` / `.xlsx`. Do not treat those as the same
     error.
   - `expiryTime` (ISO-8601) is when `presignedUrl` stops accepting writes. PUT
     promptly. If the flow stalls past `expiryTime`, re-call this tool for a
     fresh URL — do not PUT to a stale one.
   - Do not show raw URLs, S3 paths, or directory tokens to the user.
3. **Excel vs CSV.** CSV has no sheets — go straight to infer. For `.xls` /
   `.xlsx`, call **`list_data_connection_objects` first** (same
   `advancedAttributes` as infer, `fileType: "EXCEL"`) to list sheet names.
   Each selected sheet becomes a **separate** DLO; pass `sheetName` on every
   subsequent infer/create. Listing sheets is **NOT needed for CSV**.
4. **`infer_object_schema`** per file (and per Excel sheet) — detects column
   names + types. `resourceName` is always `"files"` for uploads.

   ```jsonc
   {
     "connectionId": "9cg…",
     "resourceName": "files",
     "advancedAttributes": {
       "driveLibraryId": "fileUploads$tua",
       "parentDirectory": "<verbatim from generate_presigned_credential>",  // often "$tua$"
       "importDirectory": "005a…/1782143244125/",  // verbatim from step 2, per file
       "fileName": "fact_orders.csv",
       "fileType": "CSV"
     }
   }
   ```

   Forward each Date/DateTime field's `format` and `originalType` into
   `create_data_stream` `sourceFields`. Dropping `format` on a Date column
   causes ingest to fail with *"missing required format string"*
   (`DATACLOUD_API_CLIENT_EXCEPTION: Date field [...] is missing required
   format string`).

   Present the inferred fields, then **wait for the user to explicitly confirm
   or adjust** before `create_data_stream` (see `ingest-flat-file.md`).

5. **`create_data_stream`** per file — creates the **DLO** (`*__dll`). Pass
   `sourceFields` (the inferred raw columns, including Date `format`),
   `dataLakeObjectInfo` (name `*__dll`, `category`, fields, ≥1 primary key),
   **`mappings`** (1:1 passthrough per source column), **`refreshConfig`**, and
   file **`advancedAttributes`** (same directory tokens as infer).
   `sourceFields` must be non-empty and `dataLakeObjectInfo.fields` must contain
   at least one `isPrimaryKey: true` — the tool does not validate that
   client-side.

   The server silently **strips a trailing `__dlm`** from stream `name` (only
   the DLO keeps `__dll`). Use the **returned** developer name for
   `run_data_stream` / `get_data_stream`. Pre-check DLO name collisions with
   `browse_data_assets` (`AssetType` `MktDataLakeObject`) — a duplicate
   `dataLakeObjectInfo.name` surfaces as opaque `INTERNAL_ERROR` *"Unable to
   create…"*, not `ALREADY_EXISTS`. There is no overwrite.

   This call can take ~3 minutes; the MCP layer often times out after the
   stream has already persisted. A naive retry against an already-persisted stream returns `INTERNAL_ERROR` *"Unable to create"* again. On timeout:
   `get_data_stream` with the submitted name (`__dlm` stripped); if it exists,
   proceed to `run_data_stream` (do not pick a different existing stream); if
   it does not, retry create once.

   After a successful create, register the DLO with `add_workspace_asset`:
   `assetId` = `dataLakeObjectInfo.id`, `assetType` = `"MktDataLakeObject"`,
   `assetUsageType` = `"Created"`. Resolve workspace: use one the user named,
   else `list_workspaces` and **STOP to ask** — do not infer a workspace.

   Reference shape (file source):

   ```jsonc
   {
     "name": "fact_orders",
     "label": "Fact Orders",
     "connectorInfo": { "connectorType": "DataConnector",
                        "connectorDetails": { "name": "UploadedFiles" } },
     "sourceFields": [
       { "name": "Order_ID", "dataType": "Text" },
       { "name": "Order_Date", "dataType": "Date", "format": "yyyy-MM-dd" },
       { "name": "Sales", "dataType": "Number" }
       /* … every column; forward infer format + originalType unchanged … */
     ],
     "dataLakeObjectInfo": {
       "name": "fact_orders__dll",
       "label": "Fact Orders",
       "category": "Other",                 // ← see gotcha below; NOT "Engagement"
       "dataspaceInfo": [{ "name": "default" }],
       "fields": [
         { "name": "Order_ID", "label": "Order ID", "dataType": "Text", "isPrimaryKey": true },
         { "name": "Order_Date", "label": "Order Date", "dataType": "Date", "isPrimaryKey": false }
         /* … clean names, NO __c — the platform adds it … */
       ]
     },
     "mappings": [
       { "sourceFieldLabel": "Order_ID", "targetFieldName": "Order_ID", "targetFieldReturntype": "TEXT" },
       { "sourceFieldLabel": "Order_Date", "targetFieldName": "Order_Date", "targetFieldReturntype": "DATE" },
       { "sourceFieldLabel": "Sales", "targetFieldName": "Sales", "targetFieldReturntype": "NUMBER" }
       /* … 1:1 passthrough; targetFieldReturntype is UPPERCASE; omit transformationFormula … */
     ],
     "refreshConfig": { "refreshMode": "TOTAL_REPLACE", "frequency": { "frequencyType": "None" } },
     "advancedAttributes": {
       "driveLibraryId": "fileUploads$tua",
       "parentDirectory": "<verbatim from generate_presigned_credential>",
       "importDirectory": "<verbatim from generate_presigned_credential>",
       "fileName": "fact_orders.csv",
       "fileType": "CSV"
     }
   }
   ```

   Synthetic PK **only** when the source has no natural per-row unique column
   (e.g. event logs): add
   `{"transformationFormula": "UUID()", "targetFieldName": "record_id",
   "targetFieldReturntype": "TEXT"}` and a matching `record_id` field with
   `isPrimaryKey: true`.

   **Type-enum asymmetry.** `sourceFields[].dataType` and
   `mappings[].targetFieldReturntype` only have five values (`Text`/`Number`/
   `Date`/`DateTime`/`Boolean`, resp. `TEXT`/`NUMBER`/`DATE`/`DATETIME`/
   `BOOLEAN`). `dataLakeObjectInfo.fields[].dataType` also allows `Email` /
   `Phone` / `Url` / `Percent` / `Currency` — there is no matching mapping
   return type. A DLO field using one of those specializations still maps via
   `TEXT` (Email/Phone/Url) or `NUMBER` (Percent/Currency).

   **DLO category extras (file default is still `"Other"`).** `"Profile"`
   requires `orgUnitIdentifierFieldName`. `"Engagement"` requires that plus
   `eventDateTimeFieldName`. Do not pick those categories unless the source
   actually has those columns — inventing them to satisfy the enum still
   breaks mapping (Engagement DMO → `MISSING_ARGUMENT`). Ambiguous event/log
   data without a natural entity identifier stays `"Other"`.

6. **`run_data_stream`** `{ "recordIdOrDeveloperName": "fact_orders", "interactive": true }`
   per stream — materializes rows into the DLO. **Do this before the Step 2
   row-count gate** — a stream that hasn't run leaves the DLO at 0 rows.
   **Then wait until the DLO is Active** before going on — "does it have rows
   yet?" is a stand-in, not the same as ready. Only call this on a stream
   created in the **current** DLO-creation flow.
   - **Wait for stream `ACTIVE` first.** A freshly created stream returns
     `PROCESSING` and flips to `ACTIVE` within ~5-15 seconds; calling
     `run_data_stream` before that errors with *"Data Stream status must be
     ACTIVE"*. Poll `get_data_stream` for stream status `ACTIVE`, or just retry
     once after a short wait. (`get_data_stream` is valid for this status poll
     only — not for schema or Primary Key; see step 7.)
   - **`interactive` is picked by source type, not preference.** Uploaded files
     use `interactive: true` (synchronous fast-ingest). Database/BYOL sources
     (Snowflake, Databricks, BigQuery, Redshift, any connector-based source)
     MUST use `interactive: false` — those connectors don't **support fast
     ingest** and `interactive: true` fails deterministically with
     `BAD_REQUEST` (*"Only connections configured with connectors that support fast ingest are permitted to execute data streams in interactive mode"*).
     Never retry a DB source with `true`.
   - **HTTP 412 on an uploaded file → retry the same call with
     `interactive: false`.** 412 Precondition Failed means the file is too
     large for the synchronous path; re-issuing the identical call with
     `interactive: false` routes it through the async path instead. Don't loop
     on 412 with the same `interactive` value.
   - **`{success: true}` means the run was accepted, NOT that ingestion has finished.** Treat it as kicked off.
   - **Verify row materialization with `run_query`, not `get_data_stream`.**
     Confirm with a `SELECT COUNT(*)` against the `*__dll` table —
     `get_data_stream`'s `lastRunStatus` field is unreliable/never updated via
     the MCP path (it can stay `"NONE"` indefinitely even after CDP has rows).
     Do **not** poll `lastRunStatus` until `"Success"` — that completion check
     is not valid on this path. Wait at least ~10 seconds after
     `run_data_stream` returns before the count. `0` or `table does not exist`
     is catalog lag — wait 15–30 seconds and retry; that is not ingestion
     failure.
   - **Not-found:** `run_data_stream` says *"... DataStream is not found"*;
     `get_data_stream` says *"DataStream found null for developerName = ..."*.
     Match `errorCode: ITEM_NOT_FOUND`, not the message wording.
   - **`get_data_stream` `mappings: []` after create** is a known read-time
     projection quirk — mappings submitted on create were not lost.
7. **Read back the real Primary Key and field names from the materialized DLO** — do not
   assume the CSV column name survives ingestion (same doctrine as the
   apiName-mutation rule / G3).

   **SCHEMA REALITY CHECK — `get_data_stream` is not a valid source for this.**
   `get_data_stream` returns the stream's *declared* schema — what was passed
   into `dataLakeObjectInfo.fields[]` at `create_data_stream` time (i.e., what
   `infer_object_schema` inferred from the raw CSV header, echoed back). It is
   not the same source this check requires. Query the actual materialized
   table: `run_query SELECT * FROM <dlo>__dll LIMIT 5`, or `browse_data_assets`,
   to confirm actual field names. Real ingested DLOs commonly rename/suffix
   fields (e.g. `sales_id` may actually be `sales_id_a__c` and nullable) and
   sometimes carry a non-null surrogate key instead. Copy the actual Primary Key
   field name from that result into the DMO create and the mapping.
8. **`create_data_model_object`** per logical entity — creates the **DMO**
   (`*__dlm`). Do **NOT** append the `__dlm` suffix yourself; the platform
   adds it (`Orders`, not `Orders__dlm`). Same field list (using the
   *read-back* names from step 7), `category: "Other"`, `dataSpaceName:
   "default"`. **`isPrimaryKey` is required on every field object** — at least
   one `true`, every other field explicit `false`. Omitting it (null) NPEs as UNKNOWN_EXCEPTION when a field's `isPrimaryKey` arrives null.

   `category` is REQUIRED (`INVALID_INPUT` *"Please provide a category for the
   Data Model Object."*). **Do NOT use `Engagement`** for a DMO you will map
   from a file-upload DLO: mapping then hard-fails with `MISSING_ARGUMENT`
   *"Unable to find Event Field for Engagement DLO in POST request of Mapping
   Creation"* (this tool exposes no event-time parameter). If the data looks
   like events but has no natural per-row entity identifier, pick `"Other"`
   rather than inventing an org-unit field.

   Field `dataType` **must match the source DLO column**. A numeric DLO column
   is `Number`, not `Currency`/`Percent` — mapping fails with `INTERNAL_ERROR`
   *"<field>'s type X is different from <field>'s type Y"*.

   Duplicate developer name surfaces as `DB_SAVE_FAILED` with
   `Duplicate_Developer_Name` in the message (not `ALREADY_EXISTS`). Pre-check
   `browse_data_assets` (`MktDataModelObject`).

   Field names in the **create response** are stored with `__c` (you send
   `Order_ID`, the DMO stores `Order_ID__c`). The platform also injects
   `DataSource__c`, `DataSourceObject__c`, `InternalOrganization__c`, and a
   `KQ_<pk>__c` key-qualifier. Use the **returned** `__c` names as mapping
   `targetFieldDeveloperName` values — don't reconstruct them.

   After mapping succeeds, `add_workspace_asset` with `assetType`
   `"MktDataModelObject"` and `assetUsageType` `"Created"`. If the create
   response has no usable id, look it up via `browse_data_assets`. Same
   workspace rule as the DLO: named workspace, else STOP and ask.

   ```jsonc
   {
     "name": "Orders", "label": "Orders",
     "category": "Other", "dataSpaceName": "default",
     "fields": [
       { "name": "Order_ID", "label": "Order ID", "dataType": "Text", "isPrimaryKey": true },
       { "name": "Sales", "label": "Sales", "dataType": "Number", "isPrimaryKey": false }
       /* … */
     ]
   }
   ```

9. **Wait until the DMO is Ready** before mapping. This is the check that was
   missing — using "does it have rows yet?" as a stand-in for "is this thing
   actually ready?" skips the DMO entirely. If the DMO isn't fully ready by
   the time we try to map it, `create_dlo_to_dmo_mapping` fails with
   "Primary Key not found".

   - **`isEnabled: false` right after DMO creation is normal.** Check it, but
     don't gate on it and don't wait for it before mapping — it's expected
     transient state, not a readiness signal.
   - Mapping may briefly fail with `INTERNAL_ERROR` *"DMO not found for the given developer name ... in the data space"* until the DMO is
     mapping-eligible. Wait a few seconds and retry the **mapping** (not the
     create). There is no delete-DMO tool.
   - After the DMO is Ready, query/describe it and **copy its actual Primary Key
     field name** again — don't assume the DLO Primary Key survived unchanged.
10. **`create_dlo_to_dmo_mapping`** per DMO — wires the DLO rows into the DMO.
   **Both sides carry the `__c` suffix** that the platform adds to every
   file-ingested field, matched 1:1. This is a *different* suffix from the
   numeric `shouldIncludeAllFields` suffix (SKILL.md Step 5) — here it is a
   literal `__c` on the source AND target field dev names. Bare field names
   (no `__c`) hard-fail; the server demands the `__c` form, including on the
   PK. Bare entity names without `__dll`/`__dlm` suffixes are also rejected.

   **Not idempotent.** Call exactly once per DLO→DMO pair. A duplicate is a
   HARD error: `INTERNAL_ERROR`/500 whose message contains
   `DUPLICATE_DLO_TO_DMO_MAPPING` (legacy path: `DUPLICATE_ARGUMENT_VALUE`/400).
   The server never emits `ALREADY_EXISTS` here. Do **not** retry create. If
   `get_dlo_to_dmo_mapping_status` returns `ERROR`, the mapping failed — read
   the message and fix the cause; do **not** re-POST create (hits the duplicate
   guard). `ERROR` = the mapping failed.

   ```jsonc
   {
     "sourceEntityDeveloperName": "fact_orders__dll",
     "targetEntityDeveloperName": "Orders__dlm",
     "fieldMapping": [
       { "sourceFieldDeveloperName": "Order_ID__c",   "targetFieldDeveloperName": "Order_ID__c" },
       { "sourceFieldDeveloperName": "Order_Date__c", "targetFieldDeveloperName": "Order_Date__c" },
       { "sourceFieldDeveloperName": "Sales__c",      "targetFieldDeveloperName": "Sales__c" }
       /* … one entry per field … */
     ]
   }
   ```

11. **Mapping status vs query readiness.** `create_dlo_to_dmo_mapping` returns
    `status: CREATING`. Use **`get_dlo_to_dmo_mapping_status`** (returned
    `developerName` as `objectSourceTargetMapDeveloperName`) to inspect the
    field mapping and to detect `ERROR` / `INACTIVE`. `ACTIVE` means only that
    mapping metadata was deployed off-core — it is **not** a readiness signal
    and does **not** mean the `<dmo>__dlm` table exists.

    **Authoritative readiness gate:** poll `run_query`
    `SELECT 1 FROM <dmo>__dlm LIMIT 1` (or `SELECT COUNT(*)`). Treat `42P01` /
    "table does not exist" as NOT-READY (keep polling). Treat any success,
    including `COUNT = 0`, as READY. Also query the actual mapped fields — a
    partial/bad field mapping often surfaces only when that field is selected.
    If `run_query` succeeds, the mapping committed — do not re-POST create.

Then build the SDM (Step 4) over the DMOs with `dataObjectType: "Dmo"` and
`dataObjectName: "Orders__dlm"`.

**Carve-out to the Step 2 hard gate:** for a DMO you just created and mapped
yourself in this same flow, `COUNT = 0` after a successful `run_query` is
READY — do not refuse to build as if it were a discovered empty object.
`42P01` is not READY — keep polling; do not proceed to SDM on metadata while
the table is missing. Keep the existing hard gate as-is for externally
discovered candidate sources (picking an empty pre-existing object).
Authoritative statement: `shared-gates.md` G2.

**`__dlm` still missing after a long poll:** keep treating `42P01` as
not-ready. Only fall back to querying the raw DLO if a query through the
semantic model itself, later (at the viz/query stage), fails with
table-not-found. Authoritative statement: `empty-source-handling.md`.

### Ingestion gotchas
- **`category: "Other"` for file-upload DLOs *and* DMOs.** Using `"Engagement"`
  (or another semantic category) on a file-backed object is wrong and causes
  downstream grief. File uploads are category-neutral → `Other`. An Engagement
  DMO cannot be mapped here: `MISSING_ARGUMENT` *"Unable to find Event Field
  for Engagement DLO in POST request of Mapping Creation"*. A DLO `"Profile"`
  also requires `orgUnitIdentifierFieldName`; `"Engagement"` requires that
  plus `eventDateTimeFieldName` — do not pick those without real columns.
- **DLO/DMO status waits are not the mapping query gate.** Create DLO → wait
  until Active; create DMO → wait until Ready. Mapping: use
  `get_dlo_to_dmo_mapping_status` for `ERROR` / `INACTIVE`; **query readiness
  is `run_query`** (`42P01` keep polling; `COUNT = 0` is READY). `ACTIVE` on
  the status tool is metadata only. Skipping the DMO-ready wait before
  `create_dlo_to_dmo_mapping` still produces "Primary Key not found".
- **`run_data_stream` is mandatory** before treating the DLO as Active. A
  freshly created DLO has 0 rows until the stream runs.
- **Read back the real Primary Key, don't assume it.** After DLO creation (and
  again after DMO creation), query/describe the materialized object and copy
  its actual Primary Key field name. `get_data_stream` is the declared schema, not the
  materialized one — do not use it for the SCHEMA REALITY CHECK.
- **`isEnabled: false` right after DMO creation is normal** — not a readiness
  signal; do not wait for it before mapping.
- **The `__c` suffix is universal on ingested fields.** Mapping field dev names
  are `Field_Name__c` on both sides — do not strip it, do not add a numeric
  suffix here. Confirm the actual names from the materialized table first.
- **`mappings` + `refreshConfig` + `advancedAttributes` are part of create, not
  optional commentary.** `targetFieldReturntype` is UPPERCASE (`TEXT` /
  `NUMBER` / `DATE`); field `dataType` is capitalized (`Text` / `Number` /
  `Date`). Mapping return types are only those five — DLO `Email` / `Phone` /
  `Url` / `Percent` / `Currency` still map via `TEXT` or `NUMBER`. File refresh
  is `TOTAL_REPLACE` + `"frequencyType": "None"` (`None`
  is the only valid frequency for one-time uploads and for federated
  Direct_Access).
- **Mapping is not idempotent.** `DUPLICATE_DLO_TO_DMO_MAPPING` means the pair
  is already mapped — stop. `ERROR` on `get_dlo_to_dmo_mapping_status` means
  the mapping failed; do not re-POST create.

---

## C. Ingest from an existing database / lakehouse connection

Same DLO → DMO → mapping tail as §A. The front half is connection discovery
instead of SfDrive upload. Connection **creation** is not on this server —
reuse an existing connection.

1. **`list_connections`** — `connectorType` is REQUIRED, **case-sensitive**, and
   cased inconsistently. Database / lakehouse connectors are UPPERCASE
   (`SNOWFLAKE`, `BIGQUERY`, `REDSHIFT`, `DATABRICKS_UNITY`); others are
   CamelCase (`UploadedFiles`, `AwsS3`, `SalesforceDotCom`, `Databricks`).
   Omitting it returns 400 `ILLEGAL_QUERY_PARAMETER_VALUE` *"ConnectorType must be provided"*. A 400 *"ConnectorType [X] is not supported"* almost always
   means the string is cased wrong (`"Snowflake"` is rejected; `"SNOWFLAKE"`
   returns the connection) — match an exact string; do not brute-force casing.
   Reuse the echoed `connectorType` for follow-up calls. `label` / `devName`
   are EXACT-match, not prefix/contains. `limit` is 1–299 (default 50);
   `offset` must be ≥ 0 (default 0); out of range → 400. A 200 with an empty
   collection means no connection matched the filter, not a failure — do not
   retry; report "none found". Empty collection means no connection matched.
   If the org is not provisioned for CDP / connections, the upstream returns
   a typed `INTERNAL_ERROR` that includes a tenant id (sometimes a Java
   stacktrace fragment on infer / list-objects). That is a **provisioning
   gap**, not a bad `connectorType` — do not retry, brute-force casing, or
   treat it as a client payload bug. Same convention on
   `get_connection`, `test_existing_connection`,
   `list_data_connection_objects`, and `infer_object_schema`.

   **By-id companion: `get_connection`.** When you already have a
   `connectionId` from `list_connections` and need that one record's full
   detail (`label`, `developerName`, `connectorType`, config), call
   `get_connection`. Unknown id is a typed error, not a crash: a malformed
   `connectionId` → 400 `"Entity ID Not Valid."`; a well-formed but
   non-existent id → 404 `"Invalid Connection Id"`. Report the error; do
   not retry. Unprovisioned org is the same CDP `INTERNAL_ERROR` + tenant
   id as `list_connections` — a provisioning gap, not a client bug. Do not
   surface the raw connection id unless the user needs it; present the
   label / connector type. For the singleton UploadedFiles connection after
   a file PUT, `get_upload_connection` is the more specific tool. To test
   reachability, `test_existing_connection`.

2. **`test_existing_connection`** (optional, once) — live round-trip; **do not call it in a loop** or poll it. `connectionId` is an 18-char Salesforce id beginning `9cg` (from `list_connections`), **not** a developer name, label,
   or setup URL. A malformed id → 400 *"Entity ID Not Valid."*; well-formed
   missing id → 404. HTTP **a 200 alone does NOT mean healthy** — read the
   `success` flag. A failed test is a real connection failure; do not retry
   until the stored config is fixed. Unprovisioned CDP: same `INTERNAL_ERROR`
   + tenant id as `list_connections` — do not retry.

3. **`list_data_connection_objects`** — list tables. `advancedAttributes` may
   be `{}` when the connection already pins database/schema, or carry
   uppercase `DATABASE` / `SCHEMA` to scope. Restrict to tables:

   ```json
   {
     "filters": { "filtersByProperty": [
       { "name": "objectTypes", "filterOperator": "EqualsOp",
         "values": ["StructuredData"] }
     ]}
   }
   ```

   Omit `filters` for file/Excel sources. Present names; each selected table
   becomes a separate DLO.

4. **`infer_object_schema`** — `connectionId` from `list_connections`;
   `resourceName` = the **table name** (same value you will pass as create's
   object). Body: `SCHEMA` (uppercase) for the schema; add `DATABASE`
   (uppercase) when the connection does not already pin a database. The table
   itself is the path `resourceName`, not an advancedAttribute. Remember
   database / schema / table for create. Same Date `format` forward rule as
   §A. Confirm the schema with the user before create.

5. **`create_data_stream`** — `connectorInfo.connectorDetails.name` is the
   connection **developer name** from `list_connections` (e.g.
   `My_Snowflake_Conn`), **not** the connector type `"SNOWFLAKE"`. Set
   **`dataAccessMode`: `"Direct_Access"`** (federated / zero-copy External
   DLO). Do **not** set a top-level `datasource` field — the federated path
   rejects it with *"DataSource name should be empty for External data streams"*. `refreshConfig` is the same `TOTAL_REPLACE` +
   `"frequencyType": "None"` as files (Upsert / recurring frequency are
   rejected on this non-accelerated path). Do not send `incrementalColumn` /
   `deleteColumn`.

   **`advancedAttributes` location keys — two-step casing:**
   1. First attempt: lowercase `object`, `database`, `schema` (documented
      Connect API contract). Live path: this casing is accepted on the first
      attempt; do not skip it.
   2. Fallback **only** if that fails with *"<name> attribute is required, but missed"*: resend the **same** request with uppercase `objectName`,
      `DATABASE`, `SCHEMA`. Send only one casing per attempt. Infer uses
      uppercase `SCHEMA`/`DATABASE`; create tries lowercase first — do not
      collapse those into one rule.
   3. After create, `get_data_stream` may echo `DATABASE` / `SCHEMA` /
      `objectName` (uppercase) even when lowercase was accepted on input.
      That is storage/normalization, not the create contract — do not rewrite
      the next `create_data_stream` to match the echo.

   **A table already `inUse` by another stream fails opaquely — not a payload
   bug.** `create_data_stream` against a table some other stream already
   targets returns the same generic `INTERNAL_ERROR` *"Unable to create a
   data-stream. <name>__dll"* that a casing or field mistake produces, so a
   failure here does not mean the casing fallback or field list is wrong.
   `list_data_connection_objects`'s response carries a per-object `inUse` flag
   (not called out in its own description) — check it for the target table
   before create. If `inUse: true`, pick a different, unused table rather than
   retrying the same table with different casing/field-count variations, which
   will not help.

   Reference shape (database source). Substitute apiNames from `list_*`:

   ```jsonc
   {
     "name": "snowflake_orders",
     "label": "Snowflake Orders",
     "connectorInfo": { "connectorType": "DataConnector",
                        "connectorDetails": { "name": "<list_connections.developerName>" } },
     "dataAccessMode": "Direct_Access",
     "sourceFields": [
       { "name": "ORDER_ID", "dataType": "Text" },
       { "name": "ORDER_DATE", "dataType": "Date", "format": "yyyy-MM-dd" }
     ],
     "dataLakeObjectInfo": {
       "name": "snowflake_orders__dll",
       "label": "Snowflake Orders",
       "category": "Other",
       "dataspaceInfo": [{ "name": "default" }],
       "fields": [
         { "name": "ORDER_ID", "label": "Order ID", "dataType": "Text", "isPrimaryKey": true },
         { "name": "ORDER_DATE", "label": "Order Date", "dataType": "Date", "isPrimaryKey": false }
       ]
     },
     "mappings": [
       { "sourceFieldLabel": "ORDER_ID", "targetFieldName": "ORDER_ID", "targetFieldReturntype": "TEXT" },
       { "sourceFieldLabel": "ORDER_DATE", "targetFieldName": "ORDER_DATE", "targetFieldReturntype": "DATE" }
     ],
     "refreshConfig": { "refreshMode": "TOTAL_REPLACE", "frequency": { "frequencyType": "None" } },
     "advancedAttributes": {
       "object": "<table>",
       "database": "<database>",
       "schema": "<schema>"
     }
   }
   ```

6. **Skip `run_data_stream` entirely for `Direct_Access` streams — go straight
   from `ACTIVE` to `run_query`.** A federated/zero-copy DLO queries the
   source table live; there is no ingestion run to trigger. Calling
   `run_data_stream` on one of these streams fails deterministically with
   `DATACLOUD_API_CLIENT_EXCEPTION "Connector type <X> is not allowed to
   process now"` — a server-side guard on any `Direct_Access`/streaming/
   file-federated stream, not a
   payload, casing, or timing problem, and not fixable by retrying, waiting
   longer, or trying `interactive: true` (also illegal for DB sources, for the
   unrelated fast-ingest reason above). Confirmed live: once
   `get_data_stream`'s DLO `status` reaches `ACTIVE`, `run_query SELECT
   COUNT(*) FROM <dll>` already returns real row counts pulled live from the
   source — no run step needed or possible. Go straight from `ACTIVE` to §A's
   SCHEMA REALITY CHECK through DMO + mapping.

   (This guide only ever creates `Direct_Access` streams for database
   sources — see step 5 above — so `run_data_stream` never applies to the
   database path in this flow. The `interactive: false` /
   accept-not-finished / verify-via-`run_query` guidance a few paragraphs up
   is for **file** sources only.)

---

## B. Enrichment — metric gotchas beyond SKILL.md Step 8

SKILL.md Step 8 has the calc-measure / metric basics. These three rules were
each a failed call in the run — encode them:

1. **A metric's `aggregationType` may never be `Auto`.** Rejected with *"The
   aggregation type (Auto) is not allowed for metric aggregation."* Use a
   concrete enum: `Sum`, `Count`, `Average`, `Min`, `Max`. (`Auto` is valid only
   on a *row-level calculated measure*, not on a metric.)
2. **`insightsSettings.identifyingDimension` is REQUIRED on every metric** — the
   bare `measurementReference` + `timeDimensionReference` shape in older notes is
   incomplete. Point the identifier at the grain's primary key, and list that
   same field in top-level `additionalDimensions[]` (create fails with
   `Insight dimension (...) is missing from the metric additional dimensions`).
   Verified shape:

   ```jsonc
   {
     "modelApiNameOrId": "Brightleaf_Sales",
     "apiName": "Total_Sales", "label": "Total Sales",
     "measurementReference": { "tableFieldReference": { "tableApiName": "Orders", "fieldApiName": "Sales" } },
     "timeDimensionReference": { "tableFieldReference": { "tableApiName": "Orders", "fieldApiName": "Order_Date" } },
     "aggregationType": "Sum",
     "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
     "sentiment": "SentimentTypeUpIsGood",
     "insightsSettings": {
       "identifyingDimension": {
         "identifierDimensionReference": {
           "tableFieldReference": { "tableApiName": "Orders", "fieldApiName": "Order_ID" }
         }
       }
     },
     "additionalDimensions": [
       { "tableFieldReference": { "tableApiName": "Orders", "fieldApiName": "Order_ID" } }
     ]
   }
   ```

3. **To count records, point `measurementReference` at a *measurable* field with
   `aggregationType: "Count"` — NOT at a dimension/Primary Key.** Counting via the Primary Key
   (`Order_ID`) is rejected: *"Table field … field name: (Order_ID) was not
   found in the model"* — because `Order_ID` is a dimension, not a measurement.
   Use a numeric measure column (e.g. `Sales`) as the `measurementReference` and
   `aggregationType: "Count"`; it counts one row per record. The
   `identifyingDimension` can still be `Order_ID`.

4. **A metric whose `measurementReference.calculatedFieldApiName` is a *row-level
   ratio* calc measure needs `aggregationType: "Average"`** (or another concrete
   agg), not `Auto`. E.g. a `Profit_Margin` calc = `[Orders].[Profit] /
   [Orders].[Sales]` with row-level `Auto` becomes a metric with
   `aggregationType: "Average"`.
5. **Preflight `additionalDimensions` cardinality before finalizing a metric.**
   Detail view auto-groups by every dimension listed in `additionalDimensions`;
   if the grouped result exceeds ~5,000 rows the metric detail becomes
   unopenable, even though `create`/`update` itself succeeds. This is
   especially damaging on **LOCKED** models, where the metric can't easily be
   fixed after the fact. Verify each candidate `additionalDimensions`
   combination with a grouped `run_semantic_query` *before* finalizing the
   metric, and omit, filter, or replace any dimension whose grouped
   cardinality exceeds the cap. (Keep the skill **Date-type exception**: the
   server rejects `Date` fields in `additionalDimensions` — do not mirror a
   Date insight/filter field there.)

6. **`identifyingDimension` MAY point at a field on a joined object**
   (cross-object identifying dimension). The identifier does not have to live
   on the same object as `measurementReference`.

7. **Inputs must be a JSON object, NOT a stringified JSON string.** Passing a
   stringified body fails at the tool layer.

8. **Optional `secondaryTimeComparison`** alongside `primaryTimeComparison`
   (`None` / `PreviousYear` / `PriorPeriod`) — a dual comparison window, not
   a replacement for the primary.

9. **Metric PUT recovery.** `update_semantic_model_metric` is full PUT — GET
   via `get_semantic_model_metric` first. Omitting `measurementReference` →
   HTTP 500 NPE; `{description: "x"}` → `"Required fields are missing:
   [MasterLabel]"` (the payload field is `label`); `{}` → 500 NPE on
   `Parameter.getValue()`. Path is `metricNameOrId`.

---

*For visualization authoring (Step 10), see `references/viz-authoring.md`.*
*For dashboard building (Step 11), see `references/dashboard-authoring.md`.*
