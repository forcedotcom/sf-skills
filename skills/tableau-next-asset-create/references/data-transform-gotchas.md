# Data Cloud SQL transforms — payloads and gotchas

Load this from `tasks/create-data-transform.md` (create **or** update). Not a
first hop.

Transforms run on **SparkInternal (SI)**, a subset of Data Cloud SQL. The
transform **creates its output object automatically** — do not pre-create the
target DLO/DMO.

## Contents

- Confirm before create / run / update → Confirmation
- Poll run history after run; `ACTIVE` ≠ rows ready → Run completion
- Fresh derived table (create) → Create
- Revise an existing transform-backed table → Update
- Nested `definitions` / `manifest` / `nodes.out` → Payload
- Flat body for create / update / validate (no envelope) → Payload
- BATCH↔DCSQL pairing, DMO `KQ_<pk>`, `fullRunFrequency` → Payload
- Output field names need `__c` → Payload
- SparkInternal unsupported ops → DCSQL
- Distinctive errors → Errors

## Confirmation

**NEVER call `create_data_transform`** or `update_data_transform` (or
`run_data_transform`) without explicit user approval. Show the generated SQL
plus a short `run_query` / `validate_data_transform` preview, state that a
new derived table will be created (or that `<outputApiName>` will be
redefined), and wait for an explicit "yes" / "proceed" / "go ahead". Silence
is not consent. Triggering the run is a **separate** confirmation gate.

Do not call `run_data_transform` while the transform is `PROCESSING` (it
fails). Lifecycle: `create → PROCESSING (~few min) → ACTIVE → run →
executes (typically 10–15 min)`. Creation becoming `ACTIVE` is not the
same as the output having rows — the run itself is the long step. After
`run_data_transform`, poll `get_data_transform_run_history` (see Run
completion).

## Run completion

After `run_data_transform`, poll `get_data_transform_run_history` until the
run succeeds or fails. Runs may be synchronous or asynchronous depending on
the transform's mode — do **not** infer completion from
`get_data_transform` status (`ACTIVE` means the definition is runnable, not
that this run finished or that the output has rows). If status looks stuck
(still running after the job should have finished), call
`refresh_data_transform_status` then poll history again.

## Create vs update

- **Create** when the target output object does **not** already exist.
- **Update** when the output is already transform-backed. Never create a
  second transform for a table that already has one.

**Create workflow:** `browse_data_assets` for the exact `assetApiName` (with
`__dll` / `__dlm`) — if multiple match, STOP and ask → generate DCSQL →
`validate_data_transform` and/or `run_query(sql, rowLimit: 10)` → confirm →
create → `add_workspace_asset` on the new output → confirm →
`run_data_transform` → poll `get_data_transform_run_history`. Persist the
returned `id`. Batch cadence can be set
on create via `fullRunFrequency` — do not assume scheduling only happens
through `set_data_transform_schedule`.

**Update workflow:** `get_data_transform` first and resend the **entire**
structure (not a partial patch). Change only editable fields (typically
`compiled_code` and `fields` if SELECT columns changed). Copy every 🔒
immutable field byte-for-byte. Validate → confirm → update. Skip add-to-
workspace. Confirm before run — the output stays OLD until the transform
runs. After run, poll `get_data_transform_run_history` (see Run completion).

**ALWAYS append the SAME 4-digit random number** (1000–9999) to all three API
names in one transform: `transform_<n>`, `definition_<n>`, and
`output_<n>__dll` (or `__dlm` for a DMO). Example: `my_transform_7521`,
`my_definition_7521`, `my_output_7521__dll`. Avoids "Duplicate name" errors.

## Payload (reference shape)

`outputDataObjects` is **required** — omitting it → *"Target Dlo not found"*.
`manifest.nodes.out.relation_name` must === `outputDataObjects[0].name`.
`fields` count/names/types must match SELECT columns. At least one
`fields[].isPrimaryKey` must be `true`. Pair top-level `type` with
`definitions[].type`: **BATCH → `DCSQL`**, **STREAMING → `SQL`**. The
schema otherwise allows `DCSQL` / `SQL` / `STL` as a free choice — a
mismatched pair fails. DMO outputs need `dataSpaceName` and
`type: "dataModelObject"` with a `__dlm` name, plus a key-qualifier:
each PK carries `"keyQualifierField": "KQ_<pk>"` and you add an explicit
`KQ_<pk>` field (same suffix as the PK name).

Date SQL (`cast(x AS date)`) maps to field type **`DateOnly`** (not `Date`).

**Every output field name must be `__c`-suffixed** (same convention as
DLO/DMO ingest fields) — SELECT column aliases in `compiled_code` and the
matching `fields[].name` entries all need the suffix, e.g. `status__c`,
`order_count__c`, not `status`, `order_count`. `validate_data_transform`
does **not** reject a bare alias — it silently derives an `__c`-suffixed
field in the schema it returns without warning. If you then create/update
with the bare alias still in `compiled_code`, the transform creates fine
and goes `ACTIVE`, but `run_data_transform` fails post-hoc with `"target
object ... doesn't have the required field <bare_alias>"` because the
runtime write binds by the literal SQL alias, which no longer matches the
silently-renamed backing field. Always write `__c`-suffixed aliases
yourself in both `compiled_code` and `fields[]` — do not rely on
`validate_data_transform`'s response to catch a bare one.

`create_data_transform`, `update_data_transform`, and
`validate_data_transform` all take this **same flat body** — `name`,
`type`, `definitions` at the top level. Do **not** wrap it in
`dataTransformObject` or `dataTransform`.

```json
{
  "name": "my_transform_1234",
  "label": "My Transform",
  "type": "BATCH",
  "dataSpaceName": "default",
  "definitions": [{
    "name": "my_definition_1234",
    "label": "Definition Label",
    "type": "DCSQL",
    "version": "65.0",
    "outputDataObjects": [{
      "name": "my_output_1234__dll",
      "label": "Output Label",
      "type": "dataLakeObject",
      "category": "Other",
      "recordModifiedFieldName": "",
      "fields": [
        { "name": "id__c", "label": "ID", "type": "Text", "isPrimaryKey": true },
        { "name": "amount__c", "label": "Amount", "type": "Number", "isPrimaryKey": false }
      ]
    }],
    "manifest": {
      "nodes": {
        "out": {
          "name": "out",
          "relation_name": "my_output_1234__dll",
          "config": { "materialized": "table" },
          "compiled_code": "SELECT id__c, cast(amount__c AS numeric) AS \"amount__c\" FROM \"source__dll\""
        }
      },
      "sources": { "src1": { "relation_name": "source__dll" } }
    }
  }]
}
```

DMO output fields (instead of the DLO pair above) — PK + explicit qualifier:

```json
[
  { "name": "id__c", "label": "ID", "type": "Text", "isPrimaryKey": true, "keyQualifierField": "KQ_id" },
  { "name": "KQ_id", "label": "KQ id", "type": "Text", "isPrimaryKey": false }
]
```

**🔒 immutable after create** (copy exactly on update): `name`, `type`,
`definitions[0].name`, `definitions[0].type`, `outputDataObjects[0].name`,
`outputDataObjects[0].type`, `outputDataObjects[0].recordModifiedFieldName`,
`manifest.nodes.out.name` (always `"out"`), `manifest.nodes.out.relation_name`
(**`relation_name` must ===** `outputDataObjects[0].name`),
`manifest.nodes.out.config` (`{"materialized":"table"}`).
**Changing any 🔒 field → 400.** Editable: labels, description, DMO
`dataSpaceName`, `category`, `fields[]`, `compiled_code`, `manifest.sources`.

## Update timeout

The update API may time out while the update **succeeds** on the server.
**NEVER blindly retry.** On `TIMEOUT` / 504 / "timed out":

1. `get_data_transform`.
2. Compare `definitions[0].manifest.nodes.out.compiled_code` to the new SQL.
3. If it **matches** → succeeded; do not retry.
4. If it **differs** → did not apply; retry once.

## DCSQL (SparkInternal)

This SI subset is **only** for `create_data_transform` / `update_data_transform`.
Do not carry it over to `run_query` (that is Hyper SQL / full SELECT — see
`tasks/query-model.md`).

Validate with `run_query(sql, rowLimit: 10)` for a fast preview; SI
compatibility is checked inside create/update. On failure, swap the
unsupported op and retry.

Compressed substitutions (do not use the left-hand ops):

| Unsupported | Use instead |
|---|---|
| `varpop(x)` / `varsamp(x)` | `power(stddevpop(x),2)` / `power(stddevsamp(x),2)` |
| `regexpreplace` / `regexpsubstr` | `replace()` + `substring()` |
| `position(x in y)` | `arrayposition(y,x)` (arrays) or compute manually |
| `age(d1,d2)` | `datediff(unit, d2, d1)` |
| `tochar(v,fmt)` | `cast(v AS varchar)` |
| `val <=all (subq)` / `>=all` | `val <= (select min(...) …)` / `>= (select max(...) …)` |

Also unsupported: `chr`, `overlay`, `similarto`, `trunc`, `sequence`,
`regexp*`, fiscal `extract*`, casts `date←timestamp` / `integer←bigint` /
`timestamp←varchar`. Avoid correlated subqueries and deeply nested `CASE`.

## Errors

| Error | Fix |
|---|---|
| `Target Dlo not found` | Include `outputDataObjects` |
| `Schema mismatch` | `fields` must match SELECT columns exactly |
| `At least one field must be primary key` | `isPrimaryKey: true` on ≥1 field |
| `Source relation not found` | exact `assetApiName` from `browse_data_assets`, with `__dll`/`__dlm` |
| `relation_name` mismatch | `manifest.nodes.out.relation_name` === `outputDataObjects[0].name` |
| `DMO requires dataSpaceName` | `"dataSpaceName": "default"` at transform level |
| `target object ... doesn't have the required field <name>` (on run, not create/validate) | Bare (non-`__c`) SELECT alias — re-suffix it `<name>__c` in both `compiled_code` and `fields[]`, then update |
