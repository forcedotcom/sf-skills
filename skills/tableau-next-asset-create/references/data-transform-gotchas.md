# Data Cloud SQL transforms — payloads and gotchas

Read `tasks/create-data-transform.md` first. This file contains the response
interpretation and technical contract needed for that workflow.

Transforms run on **SparkInternal (SI)**, a subset of Data Cloud SQL. The
transform **creates its output object automatically** — do not pre-create the
target DLO/DMO.

## Contents

- Reading saved transforms — empty history/schedule, saved `STL` types
- Naming — shared suffix, 40-character output limit
- Payload (reference shape) — flat body, `__c` fields, DMO `KQ_<pk>`, 🔒 fields
- Timeout recovery — read back before any retry
- DCSQL (SparkInternal) — **writing SQL: read this whole section**
  - Before returning SQL (mandatory) · Not supported → use instead ·
    No alternative · Patterns · Cross-engine safety · Diagnostics

## Reading saved transforms

Empty run history means **no visible run records**; an empty schedule response
means **no schedule returned**. Neither proves how the transform has or has
not run. Report saved types as returned: a BATCH transform with an `STL`
definition is not invalid because the create/update workflow authors BATCH +
`DCSQL`.

## Naming

Transform, definition, and output apiNames must be unique. When generating
names automatically, apply the same four-digit suffix to all three:

`transform_<n>` · `definition_<n>` · `output_<n>__dll`

Use `__dlm` for a DMO output.

Keep each output object's `name` and `label` at **40 characters or fewer**.
Derive a short output name independently of the transform label, while
preserving the `__dll` or `__dlm` suffix; do not blindly copy a long
transform label into either field. Count the suffix within the 40-character
name limit; validation may pass a name that creation rejects.

## Payload (reference shape)

`outputDataObjects` is **required** — omitting it → *"Target Dlo not found"*.
`manifest.nodes.out.relation_name` must === `outputDataObjects[0].name`.
`fields` count/names/types must match SELECT columns. At least one
`fields[].isPrimaryKey` must be `true`; choose a non-null key unique at the
output grain, including after joins or aggregation. For transforms authored
through this create/update workflow, pair **BATCH → `DCSQL`** and
**STREAMING → `SQL`**.
Set field types and primary-key flags in the submitted body. Validation can
return an inferred schema with every field as `Text` and every primary-key flag
as `false`; do not use that response to overwrite the submitted field contract.
DMO outputs need `dataSpaceName` and
`type: "dataModelObject"` with a `__dlm` name, plus a key-qualifier:
each PK carries `"keyQualifierField": "KQ_<pk>"` and you add the matching
qualifier to both `fields[]` and the SQL output. Preserve the PK's `__c`
suffix in the qualifier name, for example `id__c` → `KQ_id__c`.

A SQL `date` column maps to field type **`DateOnly`** (not `Date`).

**Every output field name must be `__c`-suffixed.** Use the same suffixed name
in the `compiled_code` SELECT alias and `fields[].name`, for example
`status__c`, not `status`. `validate_data_transform` may silently suffix its
derived schema without rejecting the bare SQL alias; creation then succeeds,
but `run_data_transform` fails because the SQL alias and backing field differ.
Never rely on validation to catch this mismatch.

`create_data_transform`, `update_data_transform`, and
`validate_data_transform` all take this **same flat body** — `name`,
`type`, `definitions` at the top level. Do **not** wrap it in
`dataTransformObject` or `dataTransform`. Pass a structured object, not a
JSON-encoded string; `definitions` must be an array, not serialized JSON text.

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
          "depends_on": { "nodes": [] },
          "compiled_code": "SELECT id__c, try_cast(amount__c AS decimal(18,2)) AS \"amount__c\" FROM \"source__dll\""
        }
      },
      "sources": { "src1": { "relation_name": "source__dll" } }
    }
  }]
}
```

`depends_on.nodes` names upstream **manifest nodes**, not entries in
`manifest.sources`. For an output node that reads a source directly, use `[]`;
putting a source key there can cause opaque mapping/output validation errors.

For a new DLO, project business columns explicitly rather than copying source
system fields such as `DataSource__c`, `DataSourceObject__c`, `KQ_*`,
`cdp_sys_*`, or `InternalOrganization__c`; validation can drop them and create
can then fail with `MktDataLakeField CDPServiceException`. The explicit
`KQ_<pk>` field required for a **DMO output** above is a separate exception.

DMO output fields (instead of the DLO pair above) — PK + explicit qualifier:

```json
[
  { "name": "id__c", "label": "ID", "type": "Text", "isPrimaryKey": true, "keyQualifierField": "KQ_id__c" },
  { "name": "KQ_id__c", "label": "KQ id", "type": "Text", "isPrimaryKey": false }
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

## Timeout recovery

An API timeout does not establish whether a write succeeded. On `TIMEOUT` /
504 / "timed out", read back before retrying:

- **Create:** resolve the submitted transform name with
  `browse_data_assets_v2` and inspect any match with `get_data_transform`.
  Do not generate another name or create a duplicate. Retry the same validated,
  approved body only after absence is established.
- **Update:** call `get_data_transform` and compare every requested change,
  including `compiled_code`, fields, and output metadata. Matching SQL alone
  does not prove a field- or metadata-only update applied. If all requested
  changes match, report success. If processing is still pending or the read
  cannot establish the outcome, report it as unresolved. Once processing has
  settled and the requested changes are absent, retry the same validated,
  approved body at most once.

## DCSQL (SparkInternal)

This SI subset is **only** for `create_data_transform` / `update_data_transform`.
Do not carry it over to `run_query` (that is Hyper SQL / full SELECT — see
`tasks/query-model.md`).

`run_query(sql, rowLimit: 10)` previews rows; `validate_data_transform` checks
the request contract. **Neither proves the transform will run.** Everything
below can pass both and still fail at run time. These rules override any
passing check.

### Before returning SQL (mandatory)

Scan the **whole** SQL — including SQL kept from a saved transform — and fix
every hit before you preview, validate, show, create, or update:

1. **§Not supported** → rewrite to the listed alternative.
2. **§No alternative** → remove it, simplify the output, and tell the user
   what was dropped.
3. **`NOT IN` / `<> ALL`** → add `col IS NOT NULL`.
4. **`ORDER BY`** (query-level and inside `OVER`) → add `NULLS FIRST` or
   `NULLS LAST`. Exception: write percentiles exactly as
   `percentile_cont(0.5) WITHIN GROUP (ORDER BY x)`, with no `NULLS` clause.

If preview rejects an alternative, never revert to the unsupported form; drop
that expression from the preview and tell the user.

### Not supported → use instead

`col` column · `n` number · `ts` timestamp · `d` date

**Casts**

- Plain `cast` from text → `try_cast` (plain cast fails at run time).
- `numeric` / `decimal` without precision, `bignumeric`, `real` →
  `decimal(18,2)` or `numeric(38,18)`.
- Text numbers →
  `try_cast(nullif(trim(replace(replace(col, '$', ''), ',', '')), '') AS decimal(18,2))`.
- Text-parsed timestamp straight to `date` →
  `try_cast(try_cast(col AS timestamptz) AS date)`.
- `timestamp` / `time` / `double` to `varchar`, `interval`, `char(n)`,
  `varchar(n)` → keep the native type.
- Decimal to text → `cast(cast(x AS numeric(38,2)) AS varchar)`.
- `integer` / `smallint` from `bigint` → `try_cast`.
- `bool` to a number → `CASE WHEN b THEN 1 WHEN NOT b THEN 0 END`.

**Strings and regex**

- `||` on nullable inputs (returns `NULL`) → `concat()`, which skips `NULL`s.
  When the result must stay `NULL`, guard it (§Cross-engine).
- `regexp_replace` without a flag → `regexp_replace(col, pattern, replacement, 'g')`
  (or `'ig'`). Without it, preview replaces only the first match and
  validation can return `invalidStl`.
- `regexp_substr` with an occurrence argument → `split_part(col, delimiter, n)`
  or `regexp_substr(col, pattern[, start])`.
- `instr`, `locate` → `position(sub IN col)` or `strpos(col, sub)`.
- `translate` → nested `replace()`.
- `overlay` → `concat(substring(…), 'X', substring(…))`.
- `SIMILAR TO` with regex classes → `~` or `regexp_like`.

**JSON**

- `->`, `->>`, `json_value`, `get_json_object`, `json_extract_path_text`,
  `from_json` → `split_part(regexp_substr(col, '"key"\s*:\s*"[^"]*'), '"', 4)`.
  String values only. The SQL has one backslash before `s`; the JSON request
  body carries it as `\\s`.

**Dates and times**

- `dateadd`, `ts + interval`, `justify_*`, `make_interval` →
  `date_add('day', cast(n AS integer), ts)`.
- `date_diff`, `age`, `ts - ts`, interval arithmetic → `datediff('day', a, b)`.
- `to_char`, `trunc(date)` → `date_trunc('month', ts)`, `extract`, or
  `try_cast`.
- `current_time` → `current_timestamp`.
- `make_time`, `make_timestamp` →
  `try_cast(concat(date_text, ' ', time_text) AS timestamp)`.
- `last_day(d)` →
  `date_add('day', -1, date_add('month', 1, date_trunc('month', d)))`.

**Numeric**

- `trunc(number)` → `CASE WHEN x >= 0 THEN floor(x) ELSE ceil(x) END`.
- `div(a, b)` → the same `CASE` on `a / b`.
- `log10` → `ln(x) / ln(10)`. **`log` is base 10; `ln` is natural.**
- `try_log`, `try_power` → `CASE` guard + `log` / `power`, e.g.
  `CASE WHEN x > 0 THEN log(x) END`.

**Aggregates**

- `count_if(cond)` → `sum(CASE WHEN cond THEN 1 ELSE 0 END)`.
- `variance`, `var_samp` → `covar_samp(x, x)`.
- `var_pop` → `covar_pop(x, x)`.
- `corr(x, y)` → `covar_pop(x, y) / (stddev_pop(x) * stddev_pop(y))`.
- `median(x)` → `percentile_cont(0.5) WITHIN GROUP (ORDER BY x)` with
  `GROUP BY`.
- `mode`, `percent_mode` → §Patterns: top value per group.

**Window functions**

- `median`, `percentile_cont`, `percentile_disc`, `covar_*`, or
  `count(DISTINCT …)` with `OVER` → §Patterns: aggregate joined back.
- `QUALIFY` → subquery + outer `WHERE`.
- `modified_rank` → `rank()` or `dense_rank()`.
- `lag` / `lead` default of another type, e.g. `lag(x, 1, 0)` →
  `lag(x, 1, x)` or `lag(x, 1, cast(0 AS numeric(38,18)))`.

**Other**

- `unnest`, `sequence`, `generate_series` with column bounds →
  `CROSS JOIN generate_series(1, <constant>) AS g(n)`.
- Bare `sha256` (binary) → `encode(sha256(col), 'hex')`.
- Bare `decode` (binary) → `encode(decode(col, 'base64'), 'escape')`.
- `greatest` / `least` that must preserve `NULL`s → `CASE WHEN`.

### No alternative — never emit

Simplify the request instead, and tell the user.

- **Arrays:** `ARRAY[]`, `array_*`, `string_to_array`, `split`, `cardinality`,
  `array_agg`.
- **Vectors:** `dot_product`, `cosine_similarity`, `binary_quantize`,
  `hamming_similarity`.
- **Aggregates:** ordered `string_agg`, `listagg`, `regr_*`.
- **Characters and bits:** `chr`, `try_chr`, `to_hex`, `quote_ident`,
  `quote_literal`, `get_bit`, `set_bit`, `set_byte`.
- **Regex:** `tb_regexp_extract_nth`.
- **Dates:** fiscal extracts, timezone extracts, `extract` on `time`,
  `to_timestamp(number)`.

### Patterns

**Aggregate joined back** (windowed median, percentile, `covar_*`,
`count(DISTINCT)`):

```sql
SELECT o.order_id__c, o.region__c, m.region_median__c
FROM "orders__dll" o
LEFT JOIN (
  SELECT region__c,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY amount__c) AS region_median__c
  FROM "orders__dll"
  GROUP BY region__c
) m ON m.region__c = o.region__c
```

**Top value per group** (`mode`; the outer `WHERE` is also the `QUALIFY`
rewrite):

```sql
SELECT region__c, product__c AS top_product__c
FROM (
  SELECT region__c, product__c,
         row_number() OVER (
           PARTITION BY region__c
           ORDER BY count(*) DESC NULLS LAST, product__c ASC NULLS LAST
         ) AS rn
  FROM "orders__dll"
  GROUP BY region__c, product__c
) ranked
WHERE rn = 1
```

### Cross-engine and payload safety

The same SQL crosses three compatibility boundaries: Hyper executes the
preview, SparkInternal executes the transform, and JSON carries the SQL in the
request body. Write for all three:

- **Guard nullable expressions explicitly.** Do not rely on
  `concat(NULL, suffix)` to stay `NULL`; Hyper can treat the null argument as
  an empty string. When a missing input must yield `NULL`, guard the complete
  expression before parsing or casting:

  ```sql
  CASE
    WHEN iso_date IS NULL THEN NULL
    ELSE try_cast(concat(substring(iso_date, 1, 7), '-01') AS date)
  END
  ```

- **Avoid escape-sensitive predicates.** Do not use `LIKE ... ESCAPE` or
  backslash-dependent patterns when a supported string primitive is enough;
  behavior can differ between engines and JSON adds another escaping layer.
  For example, detect a percent sign with `replace(value, '%', '') <> value`.
  The JSON pattern above is the one exception.
- **Preserve SQL text and literals.** Use a JSON serializer for the request;
  do not flatten SQL by globally collapsing whitespace or rewriting escapes.
  Such cleanup can change spaces inside string literals and silently alter the
  transform. Send actual newlines in the `sql` argument, not literal `\n` text.
- **Use a preview-compatible numeric type.** Hyper rejects `DOUBLE` as a cast
  target, while validation can infer `DOUBLE PRECISION` as `Text`. Use an
  explicit precision and scale such as `decimal(18,2)`. Preserve negative
  signs when cleaning parenthesized amounts.

### Preview and validation diagnostics

- `Mapping set Cannot Be Empty` and `At least one output object is required`
  may be follow-on validation errors. Inspect the other issue first:
  `invalidStl` points to SQL (including a missing regex flags argument);
  `unable to validate: {manifest}` can mean `depends_on.nodes` incorrectly
  contains a source key.
- In `run_query`, `REGEXP_SUBSTR` accepts only the string, pattern, and optional
  start position; group index, `e` flag, and occurrence `-1` are unsupported.
  `SUBSTRING(x FROM regex)`, regex lookaheads, `REGEXP_EXTRACT`, `JSON_VALUE`,
  `JSON_QUERY`, `json_extract`, `json_extract_string`, `STRFTIME`, and
  `STRPTIME` are not reliable preview substitutes here. Avoid
  `TO_DATE(x, 'M/D/YYYY')`: `D` is interpreted as day-of-week by this parser.
