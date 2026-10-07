# SDM build workflow — Steps 0–11

The procedural spine for building a Tableau Next semantic model end to end. Load
this whenever the work requires creating or extending a model. SKILL.md holds the
priority rules and the one-line step map that routes here; this file holds the
full per-step detail and verified payloads. The deeper single-topic guides
(`data-understanding.md`, `sdm-tool-reference.md`, `semantic-query-and-enrichment.md`,
`viz-authoring.md`, `dashboard-authoring.md`, `ai-readiness.md`,
`large-flat-file-handling.md`, `empty-source-handling.md`) are referenced inline.

## Contents

- [Workflow](#workflow)
  - Step 0 — Ingest (CSV/Excel upload or existing database connection)
  - Step 0.5 — Profile source schema before adding fields
  - Step 1 — Discover candidate sources
  - Step 2 — Verify data presence (HARD GATE — before building)
  - Step 3 — Confirm join keys actually match
  - Step 4 — Create the model and bind objects (one nested call)
  - Step 5 — Confirm apiNames match expectations
  - Step 6 — Create a relationship for every join
  - Step 7 — Validate (BLOCKING — both checks must pass)
  - Step 8 — Enrich: calculated fields and metrics
  - Step 9 — Query the model (answer the question; also the Step 7 proof)
  - Step 10 — Create visualizations (only when the user wants charts/dashboard)
  - Step 11 — Build the dashboard

Copy this checklist into your working notes and check off each step as you complete it:

```text
- [ ] Step 0 — Ingest (CSV/Excel upload or existing database connection)
- [ ] Step 0.5 — Profile source schema before adding fields
- [ ] Step 1 — Discover candidate sources
- [ ] Step 2 — Verify data presence (HARD GATE — before building)
- [ ] Step 3 — Confirm join keys actually match
- [ ] Step 4 — Create the model and bind objects (one nested call)
- [ ] Step 5 — Confirm apiNames match expectations
- [ ] Step 6 — Create a relationship for every join
- [ ] Step 7 — Validate (BLOCKING — both checks must pass)
- [ ] Step 8 — Enrich: calculated fields and metrics
- [ ] Step 9 — Query the model (answer the question; also the Step 7 proof)
- [ ] Step 10 — Create visualizations (only when the user wants charts/dashboard)
- [ ] Step 11 — Build the dashboard
```

## Workflow

### Step 0 — Ingest (CSV/Excel upload or existing database connection)

When the user points at local files **or** a table on an existing Data Cloud
connection instead of already-modeled data assets, ingest them into DLOs and
DMOs first. The chain is fixed — **wait for status at each create**, do not
use row-count as a stand-in for ready. Payloads: `ingest-and-metric-gotchas.md`
§A (file) / §C (connection).

**File CSV / Excel — §A:**
`get_upload_connection` → `generate_presigned_credential` (per file) →
`infer_object_schema` (per file) → `create_data_stream` (per file, creates
the `*__dll` DLO) → **`run_data_stream` (per stream — materializes rows; do
this BEFORE the Step 2 row gate) + wait until the DLO is Active** →
**SCHEMA REALITY CHECK** (query the materialized DLO / `browse_data_assets`;
**not** `get_data_stream`) and copy the real Primary Key →
`create_data_model_object` (unsuffixed name — `Orders`, not `Orders__dlm`;
the platform adds `__dlm`) → **wait until the DMO is Ready** (`isEnabled:
false` is normal — do not gate on it) and copy the real Primary Key again →
`create_dlo_to_dmo_mapping` (per DMO) → inspect mapping via
`get_dlo_to_dmo_mapping_status` (`ERROR` / `INACTIVE`) → **poll `run_query`
until `<dmo>__dlm` exists** (`ACTIVE` on the status tool is metadata only;
`COUNT = 0` is READY).

**Existing database / lakehouse connection — §C:**
`list_connections` (exact `connectorType` casing) → optional
`test_existing_connection` (once; `9cg` id) → `list_data_connection_objects`
→ `infer_object_schema` (table `resourceName`; uppercase `SCHEMA`/`DATABASE`)
→ `create_data_stream` with `dataAccessMode: "Direct_Access"` and the
connection **developer name** → `run_data_stream` `interactive: false` →
then the same SCHEMA REALITY CHECK → DMO → mapping tail as §A.

Three non-obvious rules that each cost a failed call:
- **`category: "Other"`** on both the DLO (`dataLakeObjectInfo.category`) and the
  DMO (`create_data_model_object.category`). File uploads are category-neutral;
  `"Engagement"` or other semantic categories are wrong here.
- **DLO→DMO mapping field names carry a literal `__c` suffix on BOTH sides**
  (`Order_ID__c` → `Order_ID__c`), matched 1:1. This is a *different* suffix from
  the numeric `shouldIncludeAllFields` one (Step 5) — do not strip it or
  numerically suffix it. Confirm the actual names from the materialized table
  first — do not assume the CSV column survived ingestion.
- **The mapping isn't query-ready when `create_dlo_to_dmo_mapping` returns.**
  Capture the returned `developerName` and call `get_dlo_to_dmo_mapping_status`
  to inspect `fieldMappings` and to detect `ERROR` / `INACTIVE` (`ERROR` means
  the mapping failed — do not re-POST create). `ACTIVE` is metadata deployed,
  not "the `__dlm` table exists." Poll `run_query`
  `SELECT 1 FROM <dmo>__dlm LIMIT 1` (or `COUNT(*)`): `42P01` / "table does
  not exist" = keep polling; any success including `COUNT = 0` = READY.
  `create_dlo_to_dmo_mapping` is **non-idempotent** — a duplicate call is a
  hard error — so an ambiguous failure must be checked via the status tool
  before assuming it needs retrying, never blindly retried.

Then build the SDM (Step 4) over the DMOs with `dataObjectType: "Dmo"` and
`dataObjectName: "<Entity>__dlm"`. For a DMO you just created and mapped in
this flow, wait until `run_query` succeeds on `__dlm` (`COUNT = 0` is READY;
`42P01` keep polling) — G2. Keep Step 2 as-is for any *discovered* extra
source. See `references/ingest-and-metric-gotchas.md` §A (file) / §C
(connection) for the complete per-tool payload shapes, the SCHEMA REALITY
CHECK, and the mapping query-readiness poll.

### Step 0.5 — Profile source schema before adding fields

Before adding any field to a model, profile the source DMO/DLO to classify
every field. This replaces the blind bulk import and is what lets you set clean
apiNames, correct types, and field-level descriptions at creation time.

**Fetch schema and sample data:**

```sql
SELECT * FROM "<dmo_name>__dlm" LIMIT 20
```

(use the `__dll` DLO name for a DLO). From the sample, derive per-field signals
and classify **every** field into one of three buckets:

**Bucket A — Business fields to include (with descriptions).** All non-system
fields. Subdivide by confidence:
- *High confidence* — clear field name + type matches role + sample values
  available → the AI can draft the description.
- *Low confidence* — ambiguous name, or values carry internal meanings the AI
  cannot infer (e.g. `status = 'NA'`) → ask the user **one targeted question**
  per ambiguity (never a blank form).

**Bucket B — System fields to hide (`isVisible: false`).** Names matching
`DataSource*`, `KQ_*`, `InternalOrg*`, `*SourceVersion*`, `cdp_sys_*`. Added to
the model **silently** — no user interaction, and **no descriptions required**
(they are hidden from agents). Add them with `isVisible: false`. If a Bucket B
name is also a Step 3 join key (e.g. `PartKey`), still include it in the nested
create payload — hidden is fine; omitted is not.

**Bucket C — Type mismatch warnings.** Fields where `storageDataType` conflicts
with the intended semantic type:
- `storageDataType: Text` but values match a `YYYY-MM-DD` pattern → date stored
  as Varchar.
- numeric type but values look like sequential IDs (numeric **identifiers**, not
  measures).
  Flag these with an explanation **before** proceeding; document the workaround in
  `businessPreferences`. These are source-data problems the SDM layer cannot fix.

This classification feeds the nested `semanticDimensions[]` /
`semanticMeasurements[]` on `create_semantic_model` (Step 4). Present it to
the user as a markdown table **before** that create call:

```text
Sales Transactions — 9 fields found

BUSINESS FIELDS (6)
  ✓ Region        [Text → Dimension]     High confidence
  ✓ Product       [Text → Dimension]     High confidence
  ✓ Amount        [Number → Measure]     High confidence
  ✓ Order Date    [⚠️ Text, date values] Low confidence — date stored as Varchar
  ✓ Order ID      [Number → Dimension]   High confidence (identifier, not measure)
  ? Status        [Text → Dimension]     Low confidence — what do values mean?

SYSTEM FIELDS (3) — will be hidden from agents
  DataSource__c, KQ_order_id__c, InternalOrganization__c

WARNINGS
  ⚠️  Order Date: stored as Varchar. Agents cannot do date math on this field.
      Recommended: fix at DMO level. Workaround: DATE() calc dimension.
```

Use `AskUserQuestion` for the **low-confidence Bucket A fields only** — one
question per ambiguity, not a form (e.g. "For `Status`, what do these values
mean? I see: 'Active', 'NA', 'Pending'"). Include the user's answer verbatim in
the field description per the AI readiness doc.

### Step 1 — Discover candidate sources

Call `browse_data_assets` with `searchTerm: ""` plus an `AssetType` filter per
type: `MktDataModelObject` (DMOs, e.g. `ssot__Account`),
`MktDataLakeObject` (DLOs, e.g. `accounts`), `MktCalculatedInsightObject`
(CIOs). Matching the user's words to object **labels** is how the wrong
objects get picked — treat the label match as a candidate list, not an answer.
Calling convention, the `AssetType` case-sensitivity trap, and the
empty-`searchTerm` matrix are in `sdm-tool-reference.md`.

### Step 2 — Verify data presence (HARD GATE — before building)

**Self-created mapping:** if the only sources are DMOs you just created and
mapped in Step 0 of this same flow, poll `run_query` until `<dmo>__dlm`
exists (`COUNT = 0` is READY; `42P01` / "table does not exist" = keep
polling). `get_dlo_to_dmo_mapping_status` `ACTIVE` is not this gate. Do not
skip the poll and proceed on metadata. Keep this gate as-is for every
*externally discovered* candidate (G2; `empty-source-handling.md`).

For every **discovered** candidate, check it has rows with `run_query` using the
source table name and suffix (DLO `__dll`, DMO `__dlm`, CIO `__dlc`):

```sql
SELECT COUNT(*) AS n FROM accounts__dll
```

Interpret the result:

| Result | Meaning | Action |
|---|---|---|
| count > 0 | usable | eligible to build on |
| count = 0 | empty table (has fields, no data) | do NOT build on it — surface to user |
| query errors `table … does not exist` | unmaterialized (0 fields) — **an error, not a zero** | exclude; cannot be joined; tell user |

A `run_query` error like `table "ssot__Activity__dlm" does not exist` is the
**signal that the object is unmaterialized** — do not retry it as a transient
failure and do not abort the whole task; record it as unusable and move on.
(Pre-creation, field presence comes from `browse_data_assets` metadata or this
error — `list_semantic_model_dimensions` has nothing to read until Step 5.)

**Hard gate:** a measure or dimension may only go on a viz/dashboard from an
object with verified `count > 0`. If **no** candidate matching the request has
rows, STOP and tell the user the sources are empty — do not build a model that
will render blank (the empty-of-rows vs. empty-of-fields distinction is drawn
in the table above). See `references/empty-source-handling.md` for the
authoritative exact wording to use when reporting this to the user.

### Step 3 — Confirm join keys actually match

Find how the chosen objects relate and confirm the keys match across tables
using two separate `run_query` calls:

```sql
-- 1. total rows on the candidate left table
SELECT COUNT(*) AS total_left FROM opportunities__dll

-- 2. rows that survive the join
SELECT COUNT(*) AS matched FROM opportunities__dll o
JOIN accounts__dll a ON o.account_id = a.account_id
```

A key that matches ~0 rows produces an empty join — as broken as no
relationship. If the best candidate key matches roughly zero rows, do NOT
create the relationship on it: find another key, or report that the objects do
not actually relate. Record the matching `(leftColumn = rightColumn)` pairs for
Step 6.

### Step 4 — Create the model and bind objects (one nested call)

`create_semantic_model` (apiName `[A-Za-z][A-Za-z0-9_]{0,79}`, no spaces;
`dataspace: "default"` unless told otherwise). **Always set `description`** on
the model — it is a first-class AI readiness requirement. If it returns `Label of
SemanticModel is required and cannot be empty`, that error is misleading — it
means the **apiName is malformed** (spaces or invalid characters), not that a
label is missing; fix the apiName.

**Bind fields in this same call.** Nested `semanticDataObjects[]` accept
explicit `semanticDimensions[]` / `semanticMeasurements[]` with
`shouldIncludeAllFields: false`. Build those arrays from the Step 0.5
classification **and** the Step 3 join keys, then send **one**
`create_semantic_model`. Do **not** follow with N
`add_semantic_model_dimension` / `_measure` calls (that is the 27-call bind
path). Do **not** use `shouldIncludeAllFields: true` — the flag is deprecated
and suffixes every apiName.

**Register the model with a workspace immediately after create succeeds.**
Call `add_workspace_asset` with the semantic model's returned id as `assetId`,
`assetType: "SemanticModel"`, and `assetUsageType: "Created"`. If the user did
not explicitly name a target workspace, call `list_workspaces` and **STOP to
ask the user which workspace to use** — do not infer or guess one.

For objects beyond the first few (bulk-create timeout at ≥ ~5
`semanticDataObjects[]`), create with the **anchor object and its nested
fields**, then `add_semantic_model_data_object` with the same nested
`semanticDimensions[]` / `semanticMeasurements[]` shape for each additional
object. If a table has no FK to the anchor, add the intermediate first, then
bridge through it.

**AI readiness requirements for `create_semantic_model`:**
- `description`: Required for AI readiness. Write a 1–2 sentence description
  that states the model's goals and primary use cases (e.g. `"Tracks open
  pipeline opportunities and associated account data for sales forecasting and
  rep performance analysis"`). Include what the model is used for, not just
  what data it contains.
- `categories`: Set to the relevant product category (`["Sales"]`,
  `["Marketing"]`, etc.) where determinable from context.
- `agentEnabled`: Set to `true` explicitly. This gates whether AI agents
  (Concierge / Agentforce for Analytics) can use this model.
- `businessPreferences`: One `# `-prefixed line per statement (hash + space),
  matching the dedicated tools and the Edit Business Preferences UI. At
  minimum include what the core measure means and any non-obvious terminology,
  e.g.

  ```text
  # Revenue = sum of Amount on closed-won opportunities only
  # Stage names: 0-Prospecting through 6-Closed Won
  ```

  Prefer `get_semantic_model_business_preferences` (`includeModelContent=false`)
  then `update_semantic_model_business_preferences` (full replacement of that
  string; send only `businessPreferences`). Fallback: set at create or via
  `update_semantic_model` using the **same** `# `-prefixed-line format. **When the user provides no
  domain context** (e.g. they say only "make it AI-ready" without explaining
  the business meaning of fields): infer at least one substantive statement
  from the column names and object. For example, for a `sales_data` object
  with columns `amount`, `region`, `order_date`, write:

  ```text
  # amount = the transaction sale value
  # region = the sales territory on the record, verify with domain owner whether this is geographic region or sales org territory
  ```

  Do not use a generic placeholder — that gives agents nothing
  to work with. If you cannot infer meaningful context from the schema, ask
  the user one targeted question: "To set businessPreferences, what does
  `amount` represent and are there any non-obvious field values I should
  know about?"

**AI readiness requirements for nested data objects** (same fields on
`create_semantic_model.semanticDataObjects[]` or a later
`add_semantic_model_data_object`):
- `description`: Required for AI readiness. Describe what this entity
  represents (e.g. `"Active sales opportunities with stage and amount"`).
- `primaryNameField`: The field the AI uses to identify records in insight
  narratives. Use `"Name"` for standard CRM objects; for file-upload DMOs use
  the column that identifies the record (e.g. `"Product_Name"`, `"Account_Name"`).
  **Known server bug:** `primaryNameField` cannot be set at creation time — the
  server validates it against the field registry, which is always empty when the
  data object is first created. This fails with `"<field> does not exist in
  <object> fields"` regardless of bind mode. Document as a known gap; omit it
  from the create / add-data-object call.

**Nested field arrays (Bucket A, B, and join keys)**

Put every classified field into `semanticDimensions[]` / `semanticMeasurements[]`
on the data object — **including Step 3 join keys** (e.g. `PartKey`,
`account_id__c`) even when they look like system columns. Omitting a join key
makes `add_semantic_model_relationship` fail with "field could not be found".
You control each `apiName` (clean, no suffix). Do not call
`add_semantic_model_dimension` / `_measure` for this initial bind; those tools
are only for adding a *single extra field* to an already-bound object.

Worked one-call payload (anchor object): `sdm-tool-reference.md`
(`create_semantic_model`). Extra objects after the timeout floor use the same
nested arrays on `add_semantic_model_data_object`:

```jsonc
{
  "modelApiNameOrId": "Pipeline_Analysis",
  "apiName": "Opportunities",
  "dataObjectName": "opportunities__dlm",   // __dll DLO, __dlm DMO, __dlc CIO
  "dataObjectType": "Dmo",
  "label": "Opportunities",
  "description": "Active sales opportunities with stage, amount, and close date",
  "tableType": "Standard",
  "shouldIncludeAllFields": false,
  "semanticDimensions": [ /* Bucket A dims + join keys + Bucket B */ ],
  "semanticMeasurements": [ /* Bucket A measures */ ]
}
```

**Bucket A dimensions:** set `apiName` clean with no suffix, `label`,
`dataObjectFieldName` (the original `__c` column name), `dataType` (validated
against `storageDataType`), `displayCategory`, `description`, and
`isVisible: true`.

```jsonc
{
  "apiName": "Region",              // clean, no suffix
  "label": "Region",
  "dataObjectFieldName": "region__c",
  "dataType": "Text",               // validated against storageDataType
  "displayCategory": "Discrete",
  "description": "Sales territory for the transaction. Values: West, East, North, South.",
  "isVisible": true
}
```

**Bucket A measures:** set `aggregationType` explicitly (**never `Auto`** on a
measure), `description`, `sentiment` for directional measures, and
`isVisible: true`.

```jsonc
{
  "apiName": "Amount",
  "label": "Amount",
  "dataObjectFieldName": "amount__c",
  "dataType": "Number",
  "aggregationType": "Sum",         // explicit, never Auto on a measure
  "description": "Gross transaction sale value in USD. Primary revenue measure.",
  "sentiment": "SentimentTypeUpIsGood",
  "isVisible": true
}
```

**Critical fix — numeric identifiers.** Fields like `order_id__c` that are
numeric but are **identifiers** (high cardinality, sequential) must be added as
**dimensions** with `displayCategory: "Discrete"` and a description noting
"Record identifier — do not aggregate." This is what prevents an agent from
summing order IDs and returning a meaningless number. It also makes the field
usable as a metric `identifyingDimension` (bulk import ingested it as a Sum
measure and broke this).

```jsonc
{
  "apiName": "Order_ID",
  "label": "Order ID",
  "dataObjectFieldName": "order_id__c",
  "dataType": "Number",
  "displayCategory": "Discrete",    // signals: group by, don't aggregate
  "description": "Unique numeric identifier for the sales order. Record identifier — do not aggregate.",
  "isVisible": true
}
```

**Bucket B system fields** (`isVisible: false`): no description needed — they
are hidden from agents. If a Bucket B name is also a Step 3 join key, still
include it (hidden is fine; omitted is not).

```jsonc
{
  "apiName": "DataSource",
  "label": "Data Source",
  "dataObjectFieldName": "DataSource__c",
  "dataType": "Text",
  "isVisible": false               // hidden from agents; no description needed
}
```

**Bucket C Varchar dates.** Add the raw field as `Text` with a description
noting it is not suitable for date math, then **immediately** add a calculated
dimension using `DATE([Object].[RawField])` to produce the canonical date field.
The raw field stays visible but clearly non-recommended; the calc dimension is
the field agents should use — no ambiguity. The calc itself is still a
post-create `add_semantic_model_calculated_dimension` (Step 8) — nest only the
raw `Text` field in the create payload.

```jsonc
{
  "apiName": "Order_Date_Raw",
  "label": "Order Date (Raw Text)",
  "dataObjectFieldName": "order_date__c",
  "dataType": "Text",
  "description": "Order date stored as text (YYYY-MM-DD format). NOT suitable for date arithmetic. Use Order_Date calculated dimension for time-based analysis.",
  "isVisible": true
}
```

```jsonc
{
  "apiName": "Order_Date",
  "label": "Order Date",
  "expression": "DATE([Sales_Transactions].[Order_Date_Raw])",
  "description": "Order date, parsed from text into Date type for time-based filtering and grouping."
}
```

### Step 5 — Confirm apiNames match expectations

With nested explicit fields (Step 4), apiNames are the values you set — they
are clean and known. Step 5 is a **light confirmation**: confirm the first few
match expectations with `list_semantic_model_dimensions` before writing
relationships or calculated fields.

**If you inherited a bulk-bound object (`shouldIncludeAllFields: true`):**

`shouldIncludeAllFields: true` **numerically suffixes every field apiName**
(`account_id__c` → `account_id5`) unpredictably, and the suffix differs per
object — the same logical column can become `account_id5` on one object and
`account_id3` on another. For every object to be joined, call
`list_semantic_model_dimensions` (and `list_semantic_model_data_objects` for
object apiNames) and copy the exact stored apiName. Never construct or assume
the suffixed name, and never assume the two sides of a join share a suffix.
Do not choose this bind for new objects — see the decision table.

### Decision Table: How to bind fields

| Scenario | Approach |
|---|---|
| New SDM | Nested explicit fields in `create_semantic_model` (`shouldIncludeAllFields: false`). One call. |
| ≥ ~5 objects (bulk-create timeout) | Create with the anchor object + its nested fields; then `add_semantic_model_data_object` with nested arrays per extra object |
| Add an object to an existing SDM | Nested explicit fields on `add_semantic_model_data_object` (`shouldIncludeAllFields: false`) |
| Add one field to an already-bound object | `add_semantic_model_dimension` / `_measure` |
| Wide DMO (60+ fields) | Nest the top 15–20 business fields + **all join keys** + hidden Bucket B; omit niche columns rather than bulk-importing them undescribed |
| HardJoin logical view | `shouldIncludeAllFields: true` still — apiNames are assigned at first save (read back before joining) |
| NEVER | `shouldIncludeAllFields: true` on model-level create/add (deprecated; suffixes every apiName) |

### Step 6 — Create a relationship for every join

For each key pair from Step 3, call `add_semantic_model_relationship` using the
**semantic dimension apiName you set in Step 4** (light-confirmed in Step 5)
with `leftFieldType: "TableField"` — NOT the underlying `dataObjectFieldName`
(that returns "field could not be found"). Because you controlled the apiName
at bind time, this resolves first-try. The apiNames below are illustrative —
replace them with the exact values from Step 4 / Step 5:

```jsonc
{
  "modelApiNameOrId": "Pipeline_Analysis",
  "apiName": "Opp_To_Account",
  "label": "Opportunity to Account",        // REQUIRED (schema says optional; server rejects without it)
  "joinType": "Auto",                        // MUST be Auto at model level
  "cardinality": "ManyToOne",
  "leftSemanticDefinitionApiName": "Opportunities",
  "rightSemanticDefinitionApiName": "Accounts",
  "criteria": [{
    "joinOperator": "Equals",
    "leftFieldType": "TableField",
    "leftSemanticFieldApiName": "<Opportunities account-FK apiName from Step 5>",
    "rightFieldType": "TableField",
    "rightSemanticFieldApiName": "<Accounts Primary Key apiName from Step 5>"
  }]
}
```

### Step 7 — Validate (BLOCKING — both checks must pass)

1. `list_semantic_model_relationships` → confirm **every** object from Step 4
   appears on the left or right of at least one relationship. Any object in no
   relationship is an island — return to Step 6.
2. `run_semantic_query` for a real measure grouped by a dimension (traversing a
   join when there is more than one object). In this query, reference tables by
   the **SDM data-object apiName** (from `list_semantic_model_data_objects`),
   NOT the `__dll`/`__dlm` SQL name used by `run_query` — the underlying name is
   rejected with `Failed to resolve table`, which is a query-construction bug,
   not an empty-source signal. **If the result is genuinely empty, the model is
   not shippable: do NOT create dashboards or viz — STOP and report to the
   user.** An empty result means an empty source (Step 2) or a non-matching key
   (Step 3) got through. This check is blocking even for a single-object model.

**After enrichment (Step 8), before shipping:** If you have added calculated
fields or metrics, use the Semantic Model AI Optimization similarity scan (in
Tableau Next's Semantic Model Builder UI) to check for overlapping or ambiguous
components. A `modelHealth: Low` result indicates fields that agents will
struggle to differentiate — resolve by improving descriptions or removing
redundant components before exposing the model to AI users.

### Step 8 — Enrich: calculated fields and metrics

Raw fields are often not the answer the user asked for — engagement,
margin, win-rate, "deal size" are **derived**. Add them so the model
answers the real question, not just exposes columns.

**Identify the analysis intent first** (trend / comparison / part-to-whole /
correlation / forecast — see the Step 10 map in `tasks/create-viz.md`) so
enrichment produces the fields that intent needs: a business-meaningful date
anchor for trend/forecast, a slicing dimension for part-to-whole, two measures
for correlation.

**Create a metric by default when the request implies a tracked business
number AND a meaningful time dimension exists to anchor it.** Analytical asks
("analyze account engagement", "pipeline health", "revenue by region", "win
rate over time") almost always want a named, time-bound **KPI** — a metric —
not just a raw column. A common miss is building the model and stopping; if
the user's intent names or implies a headline number, create the metric for it.

The time anchor must be **business-meaningful** — a real event date like
created/close/order/activity date — NOT a plumbing column. Skip the metric (or
ask) when the only date fields are system/load timestamps (e.g.
`cdp_sys_PartitionDate`, `*_SourceVersion`, ingestion timestamps), or when the
request is purely structural ("just model these tables"). A metric anchored on
a junk date is worse than no metric.

**For AI-readiness requirements** on the three component types below —
descriptions, value-meaning pairs, sentiment enums, singularNoun/pluralNoun,
insightsDimensionsReferences, pre-creation `list_*` duplicate checks, and the
unique-purpose test — see [ai-readiness.md](ai-readiness.md). What follows
here is build-order and payload mechanics only.

- **Calculated dimension** (derived grouping, e.g. bucketing, `UPPER(...)`,
  date-part): `add_semantic_model_calculated_dimension`. Use TuA bracketed
  references `[DataObjectApiName].[FieldApiName]` with the **suffixed**
  apiNames from Step 5 — bare names fail with "Missing reference". Row-level
  expressions get `level: "Row"` automatically.
- **Calculated measure** (derived numeric, e.g. ratio, average):
  `add_semantic_model_calculated_measure`. For an expression that already
  aggregates (`AVG(...)`, `SUM(...)/COUNT(...)`, `COUNTD(...)`), set
  `aggregationType: "UserAgg"` — a level-aware aggregation with a bare
  `Average`/`Sum` is rejected with "AggregativeFunction-level calculated
  fields require UserAgg". A row-level arithmetic expression
  (`[O].[Profit] / [O].[Sales]`) can use `aggregationType: "Auto"`.
- **Metric** (named, time-bound KPI — create one by default per above):
  `add_semantic_model_metric`. Set exactly one of
  `measurementReference.calculatedFieldApiName` (a calc measure) or
  `measurementReference.tableFieldReference {tableApiName, fieldApiName}`
  (a raw measure, suffixed apiName); add a `timeDimensionReference` pointing
  at a **business-meaningful Date/DateTime** dimension (find candidates via
  `list_semantic_model_dimensions` — `dataType: "Date"` — and pick a real event
  date like created/close/order date, not a `cdp_sys_*`/load timestamp) and
  `timeGrains`. Skip the metric only if no meaningful date dimension resolves.
  Three mechanical rules — each costs a rejected call or a broken metric:
    1. **`insightsSettings.identifyingDimension` is REQUIRED** (point it at the
       grain's primary key). The server accepts a metric without it (create
       returns 201) but it then crashes the Tableau Next metric UI on open — a
       downstream failure a "did the call succeed?" check won't catch. Always
       set it; see ai-readiness.md for the full explanation.
    2. **`aggregationType` may NEVER be `Auto` on a metric** ("The aggregation type
       (Auto) is not allowed for metric aggregation"). Use a concrete enum: `Sum`,
       `Count`, `Average`, `Min`, `Max`. A metric over a *row-level ratio* calc
       measure (e.g. `Profit_Margin`) takes `Average`, not `Auto`.
    3. **To count records, point `measurementReference` at a measurable (numeric)
       field with `aggregationType: "Count"` — NOT at a dimension/Primary Key.** Counting via
       `Order_ID` is rejected ("field name: (Order_ID) was not found in the model"
       — it's a dimension). Use a numeric column (e.g. `Sales`) + `Count`; it counts
       one row per record. The `identifyingDimension` can still be the Primary Key.

  Verified shape (AI-ready):

  ```jsonc
  {
    "modelApiNameOrId": "Pipeline_Analysis",
    "apiName": "Total_Pipeline",
    "label": "Total Pipeline",
    "description": "Total open pipeline amount summed across active opportunities",
    "measurementReference": { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Amount7" } },
    "timeDimensionReference": { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Created_Date14" } },
    "aggregationType": "Sum",
    "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
    "sentiment": "SentimentTypeUpIsGood",
    "insightsSettings": {
      "identifyingDimension": {
        "identifierDimensionReference": {
          "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Opportunity_Id5" }
        }
      },
      "sentiment": "SentimentTypeUpIsGood",
      "singularNoun": "opportunity",
      "pluralNoun": "opportunities",
      "insightsDimensionsReferences": [
        { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Stage8" } },
        { "tableFieldReference": { "tableApiName": "Accounts", "fieldApiName": "Region4" } }
      ]
    },
    "additionalDimensions": [
      { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Opportunity_Id5" } },
      { "tableFieldReference": { "tableApiName": "Opportunities", "fieldApiName": "Stage8" } },
      { "tableFieldReference": { "tableApiName": "Accounts", "fieldApiName": "Region4" } }
    ]
  }
  ```
  `additionalDimensions` **must mirror every field in `insightsSettings.identifyingDimension`,
  `insightsDimensionsReferences`, and `filters`** — create validates the insight
  dims (`Insight dimension (...) is missing from the metric additional dimensions`);
  omitting a filter field makes the metric unqueryable
  (`Metric Definition Filter Field ... is not found`).
  **Exception: the server rejects `Date`-type fields in `additionalDimensions`**
  (`"Field should have one of these data types: Text, Number, Boolean, Email,
  PhoneNumber, Url. Actual data type: Date"`). If a filter field is a Date, do
  not add it to `additionalDimensions`.
  `fieldApiName` on the measurement/time/identifier references is the
  **suffixed** apiName from the owning object (Step 5) — a date field from a
  *different* object is rejected with "Table field … was not found in the
  model".

If a calc measure references a calc dimension, create the dimension first.
Build calc fields only on objects that passed the Step 2 row check — a
derived field over an empty source is still empty.

**Step 8 closing checklist — run before proceeding to Step 9:**

For every visible raw measure in the model, verify one of the following is
true — if neither is, create the missing metric:

| Check | Pass condition |
|---|---|
| A metric already covers this measure | A metric's `measurementReference` points at this field (or a calc measure derived from it) |
| No meaningful time anchor exists | The only date fields are system/load timestamps (`cdp_sys_*`, `*SourceVersion`, ingestion columns) |
| Request is purely structural | User explicitly asked to "just model the tables" with no analytical intent |

This sweep must cover **every** visible raw measure — not just the first
one. The failure mode is anchoring on the primary KPI and stopping,
leaving secondary measures (e.g. `Amount` alongside `Engagement_Score`)
without metrics. A missing metric means agents fall back to raw field
aggregation, losing time-scoping, period comparison, and insight
breakdown context.

### Step 9 — Query the model (answer the question; also the Step 7 proof)

**Before constructing a raw `run_semantic_query`:** if the user's question
implies a derived or named business number (e.g. "average order value",
"win rate", "gross margin"), call `list_semantic_model_calculated_measures`
and `list_semantic_model_metrics` first. If a calculated measure or metric
already satisfies the request, reference it directly rather than
reconstructing the aggregation from raw fields:
- A calculated measure → `semantic_field: { name: "<calc_measure_apiName>" }`
  with `semantic_aggregation_method: "SEMANTIC_AGGREGATION_METHOD_USER_AGG"`
  (for UserAgg expressions).
- A metric → use `run_semantic_query` with `structuredMetricQuery` (see shape below).

Do NOT bypass an existing `Avg_Order_Value` calculated measure to write
`AVG(Amount)` from a raw table field — the calculated measure encodes the
authoritative business definition.

`run_semantic_query` both validates the model (Step 7) and answers the user's
data question from it. Our MCP uses a **proto-shaped snake_case** body — NOT
the REST gateway's camelCase.

**Querying a metric** (`structuredMetricQuery`) — verified working shape:

```jsonc
{
  "semanticModelApiName": "Pipeline_Analysis",
  "source": "tableau-next-pilot-mcp",
  "structuredMetricQuery": {
    "submetric_definition": { "metric_api_name": "Total_Pipeline" },
    "time_grain": "Month"   // Day | Week | Month | Quarter | Year
  }
}
```

`metric_api_name` is the only accepted key inside `submetric_definition` — all
other variants (`metricApiName`, `metricName`, `api_name`, `name`, `metric`) are
rejected with `Cannot find field`. `time_grain` is required.

**Querying raw fields** (`structuredSemanticQuery`) — verified working shape:

```jsonc
{
  "semanticModelApiName": "Pipeline_Analysis",
  "source": "tableau-next-pilot-mcp",
  "structuredSemanticQuery": {
    "fields": [
      { "expression": { "table_field": { "name": "region18", "table_name": "Accounts" } },
        "alias": "Accounts.region18", "grouping": "ROW_GROUPING" },
      { "expression": { "table_field": { "name": "Amount7", "table_name": "Opportunities" } },
        "alias": "Opportunities.Amount7",
        "semantic_aggregation_method": "SEMANTIC_AGGREGATION_METHOD_SUM" }
    ],
    "options": { "limit_options": { "limit": 10 },
                 "sort_orders": [ { "simple_sort_order":
                   { "sort_by_field_alias": "Opportunities.Amount7", "sorting_order": "DESC" } } ] }
  }
}
```

Rules that differ from raw SQL and from the REST gateway:
- Reference tables by the **SDM data-object apiName** (`table_field.table_name`),
  never the `__dll`/`__dlm` name. The latter → `Failed to resolve table`.
- Dimensions carry `grouping: "ROW_GROUPING"`; raw measures carry
  `semantic_aggregation_method: "SEMANTIC_AGGREGATION_METHOD_<SUM|AVG|COUNT|MIN|MAX>"`.
- A **calculated** field is referenced by `semantic_field: { name }` (no
  `table_name`); a UserAgg calc measure uses
  `semantic_aggregation_method: "SEMANTIC_AGGREGATION_METHOD_USER_AGG"`.
- `grand_total`, `limit`, `sort_orders` all live **inside** `options` — at the
  top level they fail with `Cannot find field`.

The shapes above cover the common cases. See
`references/semantic-query-and-enrichment.md` for the full field-shape matrix,
aggregation-method mapping, and worked enrichment payloads when a
`run_semantic_query` or `add_semantic_model_calculated_*` /
`add_semantic_model_metric` call falls outside them.

See `references/sdm-tool-reference.md` for the complete tool list and the full
suffix-rule / apiName-mutation reference (the specific mutation gotcha is
already called out inline at Step 5 above).

### Step 10 — Create visualizations (only when the user wants charts/dashboard)

**MANDATORY — design the narrative before touching a chart tool.** Before
calling `create_visualization`, design the story: KPIs → trends → breakdowns →
correlations, use business-friendly labels (never raw/technical field names),
pick diverse chart types (not every widget as a bar chart), and plan KPIs
top/left in the eventual layout. This is a hard gate alongside the Step 2/9
data-presence check (row count > 0) — do not build on an empty source. Read
`references/dashboard-design-principles.md` (MANDATORY, not optional) for the
full narrative-design guidance before proceeding.

Do this only after Step 9 returns real data — never chart a model that queried
empty.

**First, identify the user's analysis intent — it picks the analysis type, which
picks the chart.** Don't jump straight to a bar chart. Full intent → type →
tool map (including Line + `visualSpecification.forecasts` for predictive asks)
lives in `tasks/create-viz.md` / `viz-authoring.md` §3; payloads are in
`viz-authoring.md` §11.

One tool handles all chart types: `create_visualization`. It uses a
**`fields` map + `visualSpecification`** shape — NOT the `fieldRef /
measureFunction` shape from older tools. `objectName` is the **SDM
data-object apiName** (`Orders`), `fieldName` is the field apiName on that
object — use the **suffixed** apiName (Step 5) for any renamed field (e.g. a
breakdown on `Category3`). Each call returns the viz `id` and a generated
`name` (e.g. `monthly_sales_trend_1782144120674`) — **capture both** for the
dashboard.

Control chart type via `marks.panes.type` and `visualSpecification.layout`:
- **Line / Time Series** — `type: "Line"`, `layout: "Vizql"`, date on columns
- **Bar (comparative, sorted)** — `type: "Bar"`, `layout: "Vizql"`, dim on
  columns + measure on rows, `sortIntent: "MeasureDescending"`
- **Donut / Pie** — `type: "Donut"`, `layout: "Radial"`, measure on **`Angle`
  encoding** (NOT rows), dimension on Color; use when dim has < 5 unique values
- **Scatter / Correlation** — `type: "Circle"`, `layout: "Vizql"`, X-measure on
  columns, Y-measure on rows, point dimension on Color
- **Heatmap** — `type: "Square"`, `layout: "Vizql"`, two dims on rows/columns,
  measure on Color encoding
- **Table** — `type: "Text"`, `layout: "Table"`, dims in `groups`, measures in `rows`

The shape and rules above cover the common charts. See
`references/viz-authoring.md` for the full chart-type decision matrix, field
binding rules, `marks.panes.type` values, and verified payloads for every
chart type, plus the fallback approach for unsupported chart types (Funnel,
Dot Matrix, Map, Flow/Sankey).

### Step 11 — Build the dashboard

`create_dashboard` (empty `widgets: {}`; seed one layout with an empty
`page_1` — full `style` + `columnCount`, since widgets get placed next; see
`dashboard-authoring.md` §1 — and always pass `minorVersion: -1` explicitly),
then place widgets on a **48-column grid**
(`rowHeight 20`, `maxWidth 1200`; half-width = colspan 24, quarter KPI = 12).
Place KPI widgets top/left per the narrative designed in Step 10 — see
`references/dashboard-design-principles.md` (MANDATORY, not optional).

- **Every widget kind (metric, visualization, text, or any other)** → hand
  off to `tasks/edit-dashboard.md` (`edit_dashboard`'s atomic `upsert_*_widget`
  + `place_widget_on_page` batch — upsert → place, same batch or a later one).
  Viz widgets need the `id`/`name` from Step 10's `create_visualization` call;
  metric widgets need `parameters.metricOption.{sdmApiName, sdmId}` (`source`
  optionally references the metric); text widgets
  need a Quill delta (`parameters.content: [{ insert, attributes }]`). This
  is a **staged draft by default** — send `minorVersion: -1`, then only
  persist via `save_dashboard` after the user confirms.
- See `references/dashboard-authoring.md` for the complete verified
  `create_dashboard` payload shapes, grid spec, and the `&`-encoding gotcha,
  and `references/edit-dashboard.md` for the full `edit_dashboard` operation
  table and widget-name-location rule.
