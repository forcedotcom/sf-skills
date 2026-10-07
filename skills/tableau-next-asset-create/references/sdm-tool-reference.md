# SDM Tool Reference

Input shapes and gotchas for the Tableau Next MCP semantic-model tools. Tool
names are shown bare; invoke each under your client's name for that
`tableau-next-*` server tool (see `shared-gates.md`).

## Contents

Jump to the section that matches the current intent — do not apply the rest.

- `*__dll` / `*__dlm` / `*__dlc` rejected or missing → Source-name suffixes
- Invented / suffixed field apiName after auto-bind → The apiName-mutation gotcha
- Bind fields at create (one call, no N add_dimension) → create_semantic_model
- Join "field could not be found" / `leftFieldType` → add_semantic_model_relationship
- Cross-object query throws with no join path → queryUnrelatedDataObjects
- List DLOs / DMOs / models / dashboards → Discovering assets — browse_data_assets
- Create or extend an SDM / bulk-create timeout → create_semantic_model
- Measure agg vs `dataType` mismatch → add_semantic_model_measure
- Description-only or hidden-field update (`isVisible` echo) → Updates — sparse vs PUT
- Parameter PUT (`label`/`type`/`dataType`/`defaultValue`; `List` values) → Parameters
- HardJoin / Union / CustomSQL payloads → Logical views
- Component delete (calc / metric / object / LV / relationship) → Deleting a semantic definition
- `defaultExc` string vs flat object → Response double-wrap

---

## Source-name suffixes

`add_semantic_model_data_object.dataObjectName` requires a type suffix. Bare
names from `browse_data_assets` are rejected with "DMO/CI/DLO does not exist".

| Source type | `dataObjectType` | Suffix | Example |
|---|---|---|---|
| Data Lake Object | `Dlo` | `__dll` | `accounts__dll` |
| Data Model Object | `Dmo` | `__dlm` | `ssot__Account__dlm` |
| Calculated Insight | `Cio` | `__dlc` | `churn_score__dlc` |

If `__dlm` fails for a CSV-backed object that `browse_data_assets` labeled as a
DMO, retry once with `__dll` — the browse filter sometimes mislabels DLO-backed
CSV objects. This one-time suffix correction is distinct from a `run_query`
"table does not exist" error during the Step 2 row-count check: for an
*externally discovered* candidate that error means the object is unmaterialized
(0 fields) and must NOT be retried — exclude it. For a DMO you just created
and mapped in this same flow, the same error is NOT-READY — poll `run_query`
until the table exists (`COUNT = 0` is READY; `empty-source-handling.md`; G2).

The same `__dll` / `__dlm` / `__dlc` table names are what `run_query` selects
from for the Step 2 row-count checks.

## The apiName-mutation gotcha (most common failure)

**Do not bind with `shouldIncludeAllFields: true`.** That flag is deprecated
and the server **numerically suffixes every
auto-bound dimension/measure apiName**, even on the first object with no name
collision:

- `Order_ID__c` → `Order_ID3`
- `Region__c` → `Region4`
- `account_id__c` → `account_id5`

It also sometimes rewrites `dataObjectFieldName` (`Id__c` → `Idc__c`). The
suffix is not predictable from the source name. The suffixed apiName is what
`list_semantic_model_dimensions` returns, and it is the value to pass to
`add_semantic_model_relationship`.

**Preferred bind:** fetch the DMO/DLO fields first, then pass explicit
`semanticDimensions[]` / `semanticMeasurements[]` **nested in
`create_semantic_model`** (or `add_semantic_model_data_object` for a later
object) with `shouldIncludeAllFields: false`. You control each field's
`apiName`, so `add_semantic_model_relationship` resolves first-try. Do **not**
follow create with N incremental `add_semantic_model_dimension` /
`add_semantic_model_measure` calls — that is the 27-call / 365s bind path.

HardJoin logical-view objects still use `shouldIncludeAllFields: true`
(apiNames are assigned at first save — see Logical views). If you ever inherit
a bulk-bound object, always call `list_semantic_model_dimensions` (and
`list_semantic_model_data_objects` for object apiNames) and copy the exact
stored apiName into the next call. Never construct the suffixed name yourself.

## add_semantic_model_relationship — criteria field rules

The `criteria[].leftFieldType` / `rightFieldType` determines what apiName form
to use:

| fieldType | When | apiName to use |
|---|---|---|
| `TableField` | regular dimensions/measures (the common case) | the **semantic dimension apiName** from `list_semantic_model_dimensions` (e.g. `Account_Id5`) — NOT `dataObjectFieldName` |
| `SemanticField` | calculated dimensions only | the calculated dimension's apiName; must have a row-level dependency on the object (pure constants rejected; aggregations rejected with `SEMANTIC_FIELD_LEVEL_ERROR`) |
| `Formula` | expression-based joins | a TUA expression like `POWER([object].[field], 1)`; row-level only; left/right return types must match |

Using `dataObjectFieldName` with `TableField` returns "field could not be
found" even though the field exists — this is the single most common
relationship error.

Other relationship constraints:

- `joinType` MUST be `Auto` for model-level relationships. `Left` / `Right` /
  `Inner` / `Full` are valid only inside a logical view (`logicalViewId` set).
- `label` is REQUIRED despite the schema marking it optional.
- `cardinality`: `OneToOne` / `OneToMany` / `ManyToOne` / `ManyToMany` /
  `Unspecified`. A fact→dimension join is typically `ManyToOne`.
- `criteria` is usually a single `Equals` on the natural key.
- **Formula** left/right return types must match or the API returns
  `CREATE_SEMANTIC_ENTITY_FAILED` with a message containing "must be of the
  same type".

## queryUnrelatedDataObjects

`list_semantic_models` returns `queryUnrelatedDataObjects` per model. When it
is `"Exception"`, a semantic query that spans two objects with no join path
**throws** rather than returning partial data. This is why an island object
breaks queries hard, not softly. Joining every object avoids it.

**`list_semantic_models`: an unknown `dataspace` returns a raw 500**, not an
empty list or a 400. Verify the dataspace exists before filtering on it.

## Discovering assets — browse_data_assets

The single discovery endpoint across all asset types — DLOs/DMOs/CIOs, dashboards,
visualizations, workspaces, semantic models. Step 1 of the happy path below.

**Calling convention.** To list all assets of one type: `searchTerm: ""` (a literal
empty string — omitting it returns `UNKNOWN_EXCEPTION`) plus an `AssetType In [...]`
filter.

```jsonc
// Literal "" — omit searchTerm → UNKNOWN_EXCEPTION. Repeat with
// MktDataModelObject / MktCalculatedInsightObject for DMOs / CIOs.
{
  "searchTerm": "",
  "filters": {
    "filters": [
      { "field": "AssetType", "operator": "In",
        "values": ["MktDataLakeObject"] }
    ]
  },
  "limit": 50
}
```

**`AssetType` is case-sensitive and unvalidated — a typo returns zero results, not
an error.** Use the exact-cased values only: `AnalyticsDashboard`,
`AnalyticsVisualization`, `AnalyticsWorkspace`, `SemanticModel`,
`SemanticDefinition`, `MktDataLakeObject` (DLO), `MktDataModelObject` (DMO),
`MktCalculatedInsightObject` (CIO). A zero-result response for a plausible-looking
type name means "check the casing/spelling," not "no assets exist."

**Empty-`searchTerm` matrix.** `searchTerm: ""` works for `MktDataLakeObject` /
`MktDataModelObject` / `MktCalculatedInsightObject` but throws `UNKNOWN_EXCEPTION`
for `AnalyticsDashboard` / `AnalyticsVisualization` / `AnalyticsWorkspace` /
`SemanticModel` / `SemanticDefinition`. For those five, either use the per-type
list tool (`list_dashboards` / `list_visualizations` / `list_workspaces` /
`list_semantic_models`) or pass a real ≥2-character search term (1-char terms are
rejected with `search term must be longer than one character`).

**`And` behaves like `Or`.** `conjunctiveOperator: "And"` over multiple
`AssetType In` clauses returns the union, not an intersection — true intersection
isn't implemented (e.g. `AssetType In [SemanticModel] And AssetType In
[AnalyticsWorkspace]` returns the union, not the empty set). `conjunctiveOperator:
"Or"` over heterogeneous filter shapes also frequently returns `UNKNOWN_EXCEPTION`.
Compose at most one filter clause per call and intersect client-side if you need one.

**Only `AssetType` filters universally.** Type-specific fields (e.g. `CreatedBy`
on `SemanticModel`) return `Invalid filter field for type ...` — don't assume
per-type filter validity.

**Scope: current org only.**

Prefer the per-type tools (`list_visualizations`, `list_semantic_models`,
`list_workspace_assets`) when you need their richer per-type detail (dataSource,
chaining URLs, workspace scoping) rather than the generic `assets[]` shape.

**`list_workspaces` has no pagination metadata and an undocumented oldest-first
sort** (ascending by `createdDate`, no `total`/`hasNextPage`/page URL). To find
the *most recently created* workspace, don't page through everything — call
`browse_data_assets_v2` with `assetTypesFilter: ["AnalyticsWorkspace"]`,
`sortField: "LastModifiedDate"`, `sortOrder: "Descending"` instead.

## create_semantic_model — surface and recovery

- **Param names are `apiName` + `dataspace`, not `name` + `dataSpaceName`.**
  The natural-sounding `name`/`dataSpaceName` guess is rejected — use
  `apiName` (model's developer name) and `dataspace` (lowercase, e.g.
  `"default"`) as shown in the payload below.
- Nested `semanticDataObjects[].label` is REQUIRED — the server
  rejects without it.
- **Bind fields in this call.** Each `semanticDataObjects[]` item accepts
  nested `semanticDimensions[]` / `semanticMeasurements[]` with
  `shouldIncludeAllFields: false`. Fetch the DMO/DLO fields first (`run_query`
  `SELECT * … LIMIT 20` or the ingest SCHEMA REALITY CHECK), classify them
  (G5 / Step 0.5), and pass the explicit arrays — including join-key fields
  from Step 3 (e.g. `PartKey`) even if they look like system columns. You
  control each field's `apiName`, so a later `add_semantic_model_relationship`
  resolves first-try. Do **not** use `shouldIncludeAllFields: true` (deprecated;
  numeric-suffix mutation) and do **not** follow with N
  `add_semantic_model_dimension` / `_measure` calls.
- **Still post-create:** relationships, metrics, calculated fields, parameters,
  and logical views require `add_semantic_model_*` after create. Adding a
  *single extra field* to an already-bound object also uses
  `add_semantic_model_dimension` / `_measure`.
- **Extend a Model** uses the same tool: pass `baseModels[]` of
  `{ "apiName": "<existing SDM apiName>" }` in the **same `dataspace`**. There is
  no separate extend tool. Typical label `"<Base Label> (Extended)"`.

```jsonc
// One-call bind. shouldIncludeAllFields:false + explicit nested fields.
// Include every join-key column from Step 3 (PartKey, account_id__c, …).
{
  "apiName": "Pipeline_Analysis",
  "dataspace": "default",
  "label": "Pipeline Analysis",
  "description": "Tracks open pipeline opportunities and associated account data for sales forecasting.",
  "sourceCreation": "Other",
  "categories": ["Sales"],
  "semanticDataObjects": [
    {
      "apiName": "Opportunities",
      "label": "Opportunities",
      "description": "Active sales opportunities with stage, amount, and close date",
      "dataObjectName": "opportunities__dlm",
      "dataObjectType": "Dmo",
      "tableType": "Standard",
      "shouldIncludeAllFields": false,
      "semanticDimensions": [
        {
          "apiName": "Stage",
          "label": "Stage",
          "dataObjectFieldName": "stage__c",
          "dataType": "Text",
          "displayCategory": "Discrete",
          "description": "Opportunity sales stage. Values: Prospecting through Closed Won.",
          "isVisible": true
        },
        {
          "apiName": "Account_Id",
          "label": "Account ID",
          "dataObjectFieldName": "account_id__c",
          "dataType": "Text",
          "displayCategory": "Discrete",
          "description": "Join key to Accounts. Record identifier — do not aggregate.",
          "isVisible": true
        },
        {
          "apiName": "DataSource",
          "label": "Data Source",
          "dataObjectFieldName": "DataSource__c",
          "dataType": "Text",
          "isVisible": false
        }
      ],
      "semanticMeasurements": [
        {
          "apiName": "Amount",
          "label": "Amount",
          "dataObjectFieldName": "amount__c",
          "dataType": "Number",
          "aggregationType": "Sum",
          "description": "Gross opportunity amount in org currency. Primary pipeline measure.",
          "sentiment": "SentimentTypeUpIsGood",
          "isVisible": true
        }
      ]
    }
  ]
}
```

```jsonc
// Same create_semantic_model tool — no separate extend API.
{
  "apiName": "<NEW_SDM_API_NAME>",
  "dataspace": "default",
  "label": "<Base Label> (Extended)",
  "sourceCreation": "Other",
  "baseModels": [{ "apiName": "<BASE_SDM_API_NAME>" }]
}
```
- **Bulk-create timeout (>= ~5 objects).** Many `semanticDataObjects[]` in one
  call returns `"Unexpected error while invoking tool postSemanticModelCollection"`
  but the SDM **does persist** ~10–30s later. A naive retry hits
  `"Unique constraint violated"`. Recovery: wait ~30s, then `list_semantic_models`
  to confirm. Prefer create-with-anchor **and its nested fields**, then
  incremental `add_semantic_model_data_object` with the same nested
  `semanticDimensions[]` / `semanticMeasurements[]` shape. If a table has no FK
  to the anchor, add the intermediate first, then bridge through it.
- Optional final sanity check: `get_semantic_model` with
  `includeModelContent=true`.

## add_semantic_model_measure — agg / type allow-list

Create does **not** fully cross-validate `aggregationType` against `dataType` /
`storageDataType`. Some mismatches return 201 and fail at query time
(`Cannot convert from TEXT to NUMBER`); others reject at create. Per-type
allow-list (plus `Auto`, which resolves to the type default):

- `Text` / `Boolean`: only `Min`, `Max`, `Count`, `CountDistinct`.
- `Url` / `Email` / `Phone` / `Geo`: only `Count`, `CountDistinct`.
- `Number` / `Percentage` / `Currency`: all aggregations.

**`dataType: "Currency"` requires a backing record-currency field on the
DMO.** On a DMO with no `CurrencyIsoCode`-backed column, `Currency` is
rejected at create — fall back to `dataType: "Number"` for that measure
instead of retrying `Currency`.

Always set `dataType` to match the column's real `storageDataType` from
`list_semantic_model_dimensions` / `_measures`. PUT on an existing measure also
skips this allow-list — invalid combos return 200 and fail at query time.
Changing `aggregationType` on a measure referenced by a metric may break that
metric — `list_semantic_model_metrics` first.

Do not set `externalLevel` or `externalConnectionApiName` on a calculated
measure unless connecting to an external definition.

## Updates — sparse vs PUT

| Tool | Semantics | Must echo / re-send |
|---|---|---|
| `update_semantic_model_dimension` / `_measure` | **Sparse** — omitted fields stay put, except `isVisible` | Always echo `isVisible` and `dataObjectFieldName` |
| `update_semantic_model_data_object` | **Full PUT** | GET via `get_semantic_model_data_object`, send the complete object including nested `semanticDimensions[]` / `semanticMeasurements[]`; a partial body discards omitted nested fields |
| `update_semantic_model_metric` | **Full PUT** | Re-send `label`, `measurementReference`, `timeDimensionReference`, `insightsSettings` (GET first via `get_semantic_model_metric`) |
| `update_semantic_model_calculated_dimension` | **Full PUT** | GET via `get_semantic_model_calculated_dimension`, send the complete object (`apiName`, `label`, `expression`, `dataType`, `displayCategory`); omitted fields clear or reset to defaults |
| `update_semantic_model_calculated_measure` | **Full PUT** | GET via `get_semantic_model_calculated_measure`, send the complete object; omitted fields reset to defaults (`decimalPlace: 2`, `directionality: "Up"`, `sentiment: "SentimentTypeUpIsGood"`, …) |
| `update_semantic_model_relationship` | **Full PUT** | GET via `get_semantic_model_relationship`, modify, send the returned body back complete. Validate cardinality in the data before changing it. |
| `update_semantic_model_logical_view` | **PATCH** — only `description`, `filterLogic`, `filters` persist | GET first via `get_semantic_model_logical_view`. Empty body `{}` rejected. Label / SQL / view-type changes are discarded — delete-and-recreate for SQL or type |
| `update_semantic_model_parameter` | **Full PUT** — not PATCH | Re-send `label`, `type`, `dataType`, `defaultValue` even for a description-only change. `apiName` immutable — omit it. `List` needs `values`. See Parameters. |
| `update_semantic_model` (model) | Empty/missing body NPEs | Never call with no body |

**`isVisible` is NOT preserved by sparse update (server bug).** If a dimension or
measure is currently `isVisible: false`, omitting `isVisible` silently resets it
to `true`. Echo it from `list_semantic_model_dimensions` / `_measures` on every
call, even description-only backfills.

```jsonc
// Description-only backfill of a hidden measure. Same keys on
// update_semantic_model_dimension. Do NOT send description alone.
{
  "modelApiNameOrId": "My_Model",
  "dataObjectNameOrId": "My_Object",
  "measurementNameOrId": "My_Measure",
  "apiName": "My_Measure",
  "dataObjectFieldName": "my_measure__c",  // omit → [null] SEMANTIC_FIELD_NOT_VALID
  "isVisible": false,                      // echoed from list_*; omit → unhides
  "description": "Net revenue after discounts, in org currency."
}
```

`apiName` and `dataObjectFieldName` are immutable. Omitting `dataObjectFieldName`
sends `null` → `SEMANTIC_FIELD_NOT_VALID` / `UPDATE_ENTITY_API_NAME_ERROR`
("The referenced Data Cloud fields ([null]) could not be found…"). A wrong
(non-null) name uses the same error code — distinguish by `[null]` in the
brackets vs a literal field name. Empty-body dimension/measure updates return
500, not 400.

`dataType` transitions on a dimension (e.g. Text → Number) are permitted
without checking `storageDataType`. A mismatch fails at **query** time — read
`storageDataType` before changing `dataType`.

Path exception: metric tools use `metricNameOrId`, not `*ApiNameOrId`.
`apiName` on a metric PUT is immutable — a different value in the body is
silently ignored.

**Response wrap:** dimension/measure updates return a **flat parsed object** —
NOT double-wrapped (no `defaultExc` wrapper). Metric / calc-measure /
relationship updates double-wrap like the add tools. Errors on the unwrapped
pair use `{enhancedErrorType, message, output}`.

Incomplete metric PUT: omitting `measurementReference` → HTTP 500 NPE;
`{description: "x"}` → `"Required fields are missing: [MasterLabel]"` (the
payload field is `label`); `{}` → 500 NPE on `Parameter.getValue()`.

## Parameters

Parameters cannot be created inline on `create_semantic_model` — they
require post-create `add_semantic_model_parameter`. Enumerate with
`list_semantic_model_parameters`. Delete with
`delete_semantic_model_parameter` (destructive, no undo; success is often
HTTP 204).

### `update_semantic_model_parameter` — PUT, not PATCH

Full payload required every call. MUST re-send `label`, `type`,
`dataType`, and `defaultValue` even if only changing `description`.
Incomplete bodies fail validation.

- **Inputs:** `modelApiNameOrId`; `parameterApiNameOrId`; `label`; `type`
  (`All` or `List`); `dataType`; `defaultValue`. `description` is optional.
- **`apiName` is immutable** — omit it from the body. A different value is
  silently ignored.
- **`dataType` (live tool):** `Boolean` / `Date` / `DateTime` / `Email` /
  `Number` / `Percentage` / `PhoneNumber` / `Text`. **`Url` is not on the
  live sidecar** — do not send it.
- **`List` type:** `values` is required (array of plain strings) and
  `defaultValue` must exactly match one entry in `values`.
- **Scope:** current org only.
- **Response:** the API double-wraps as `{"defaultExc": "<stringified
  JSON>", "responseCode": <number>}`, but the MCP tool unwraps
  transparently — callers receive the parsed parameter object directly.

```jsonc
// Description-only change still re-sends the full PUT body.
{
  "modelApiNameOrId": "My_Model",
  "parameterApiNameOrId": "RegionPick",
  "label": "Region",
  "type": "List",
  "dataType": "Text",
  "values": ["East", "West", "Central"],
  "defaultValue": "East",              // must match one entry in values
  "description": "Sales territory, not billing geography."
}
```

## Logical views

A logical view is a virtual table (pre-joined / filtered / union) without
modifying base data objects. Enumerate existing ones via `get_semantic_model`
(`semanticLogicalViews[]`) before creating. `label` is required.
`Hierarchy` is **not currently supported via MCP**.

**HardJoin 3-step** (field apiNames are assigned at first save — unknown in
advance):

1. `add_semantic_model_logical_view` with `semanticDataObjects` only — **no**
   `semanticRelationships`.
2. `get_semantic_model_logical_view` to read assigned field apiNames.
3. `add_semantic_model_relationship` with those names. LV joins use `joinType`
   `Left`/`Right`/`Inner`/`Full`, **not** `Auto`.

Each LV data-object `apiName` must be unique vs model-level objects
(`Unique constraint violated` — prefix `LV_`). `dataObjectName` still needs
`__dll` / `__dlm` / `__dlc`. Auto-bind suffixes still apply — read back before
joining.

```jsonc
// HardJoin step 1 — objects only. Do NOT send semanticRelationships here.
{
  "modelApiNameOrId": "SalesSDM",
  "apiName": "OrdersWithCustomers_LV",
  "label": "Orders with Customers",
  "semanticViewTypeEnum": "HardJoin",
  "semanticDataObjects": [
    {
      "apiName": "LV_Orders",
      "label": "Orders",
      "dataObjectName": "orders__dll",
      "dataObjectType": "Dlo",
      "shouldIncludeAllFields": true
    },
    {
      "apiName": "LV_Customers",
      "label": "Customers",
      "dataObjectName": "customers__dll",
      "dataObjectType": "Dlo",
      "shouldIncludeAllFields": true
    }
  ]
}
```

**Union:** all tables live in **exactly one** `semanticUnions[]` entry. Use
`semanticUnions[]`, not top-level `semanticDataObjects[]`. **Do NOT pass
`"semanticViewTypeEnum": "Union"`** — the server infers Union from
`semanticUnions[]` and returns 500 if the enum is set to `"Union"`. GET
responses may show `semanticViewTypeEnum: "HardJoin"` for a Union (cosmetic
server bug). `semanticMappedFields[].fields[].fieldApiName` must be the
**locally-scoped** semantic dim/measure apiName defined on that ULV data
object — NOT `dataObjectFieldName` and NOT the base model's suffixed names.
Both fail `"Field API name X not found in either measurements or dimensions."`
Mapped-field `semanticDimension` / `semanticMeasurement` must be fully
populated (`apiName`, `label`, `dataObjectFieldName`, `dataType`) or GET 500s
with `Required fields are missing: [MasterLabel]`. Use `scanMinimalTables: true`
when the Union is used in a shared-dimension merge model.

```jsonc
// Union — omit semanticViewTypeEnum. fieldApiName is the local dim/measure
// apiName (US_OrderId), not order_id__c and not a base-model suffix (Order_Id8).
{
  "modelApiNameOrId": "SalesSDM",
  "apiName": "AllOrders_LV",
  "label": "All Orders",
  "semanticUnions": [
    {
      "apiName": "AllOrders_ULV",
      "label": "All Orders ULV",
      "semanticDataObjects": [
        {
          "apiName": "LV_Orders_US",
          "label": "Orders US",
          "dataObjectName": "orders_us__dll",
          "dataObjectType": "Dlo",
          "semanticDimensions": [
            {
              "apiName": "US_OrderId",
              "label": "Order ID",
              "dataObjectFieldName": "order_id__c",
              "dataType": "Text"
            }
          ],
          "semanticMeasurements": [
            {
              "apiName": "US_Revenue",
              "label": "Revenue",
              "dataObjectFieldName": "revenue__c",
              "dataType": "Currency",
              "aggregationType": "Sum"
            }
          ]
        },
        {
          "apiName": "LV_Orders_EU",
          "label": "Orders EU",
          "dataObjectName": "orders_eu__dll",
          "dataObjectType": "Dlo",
          "semanticDimensions": [
            {
              "apiName": "EU_OrderId",
              "label": "Order ID",
              "dataObjectFieldName": "order_id__c",
              "dataType": "Text"
            }
          ],
          "semanticMeasurements": [
            {
              "apiName": "EU_Revenue",
              "label": "Revenue",
              "dataObjectFieldName": "revenue__c",
              "dataType": "Currency",
              "aggregationType": "Sum"
            }
          ]
        }
      ],
      "semanticMappedFields": [
        {
          "apiName": "MF_OrderId",
          "label": "Order ID",
          "fields": [
            { "tableApiName": "LV_Orders_US", "fieldApiName": "US_OrderId" },
            { "tableApiName": "LV_Orders_EU", "fieldApiName": "EU_OrderId" }
          ],
          "semanticDimension": {
            "apiName": "MF_OrderId_dim",
            "label": "Order ID",
            "dataObjectFieldName": "order_id__c",
            "dataType": "Text"
          }
        },
        {
          "apiName": "MF_Revenue",
          "label": "Revenue",
          "fields": [
            { "tableApiName": "LV_Orders_US", "fieldApiName": "US_Revenue" },
            { "tableApiName": "LV_Orders_EU", "fieldApiName": "EU_Revenue" }
          ],
          "semanticMeasurement": {
            "apiName": "MF_Revenue_meas",
            "label": "Revenue",
            "dataObjectFieldName": "revenue__c",
            "dataType": "Currency",
            "aggregationType": "Sum"
          }
        }
      ]
    }
  ]
}
```

**CustomSQL:** prefer `customSQLV2`. Exactly **one** `semanticDataObjects`
entry with `dataObjectType: "CustomSQL"`. That entry must have explicit
dims/measures — `shouldIncludeAllFields: true` does **NOT** satisfy CustomSQL
validation. Measurements also need `aggregationType`.

```jsonc
{
  "modelApiNameOrId": "SalesSDM",
  "apiName": "TopCustomers_LV",
  "label": "Top Customers",
  "semanticViewTypeEnum": "CustomSQL",
  "customSQLV2": "SELECT customer_id__c, customer_name__c, SUM(revenue__c) AS total_revenue__c FROM orders__dll GROUP BY customer_id__c, customer_name__c",
  "semanticDataObjects": [
    {
      "apiName": "LV_TopCustomers_SQL",
      "label": "Top Customers SQL",
      "dataObjectName": "orders__dll",
      "dataObjectType": "CustomSQL",
      "semanticDimensions": [
        {
          "apiName": "CustomerId_dim",
          "label": "Customer ID",
          "dataObjectFieldName": "customer_id__c",
          "dataType": "Text"
        },
        {
          "apiName": "CustomerName_dim",
          "label": "Customer Name",
          "dataObjectFieldName": "customer_name__c",
          "dataType": "Text"
        }
      ],
      "semanticMeasurements": [
        {
          "apiName": "TotalRevenue_meas",
          "label": "Total Revenue",
          "dataObjectFieldName": "total_revenue__c",
          "dataType": "Currency",
          "aggregationType": "Sum"
        }
      ]
    }
  ]
}
```

`filterLogic` is required when `filters` has more than one entry;
`filters[].fieldName` is fully qualified `<dataObjectApiName>.<fieldApiName>`.

**Updates (PATCH).** `update_semantic_model_logical_view` only persists
`description`, `filterLogic`, and `filters` — see Updates above. GET first.
Label is silently ignored. SQL or `semanticViewTypeEnum` changes require
delete-and-recreate. Empty body `{}` is rejected.

## Tool sequence (happy path)

1. `browse_data_assets` (per AssetType) — discover candidates
2. `run_query` `SELECT COUNT(*)` per candidate — verify rows (Step 2)
3. `run_query` JOIN probe — confirm keys match (Step 3)
4. `run_query` `SELECT * … LIMIT 20` (or ingest SCHEMA REALITY CHECK) — fetch fields, classify (Step 0.5 / G5)
5. `create_semantic_model` — one call with nested `semanticDataObjects[]` that include explicit `semanticDimensions[]` / `semanticMeasurements[]` (`shouldIncludeAllFields: false`, join keys included). Extra objects after the anchor: `add_semantic_model_data_object` with the same nested arrays. HardJoin LV objects still use `shouldIncludeAllFields: true` (Logical views).
6. `list_semantic_model_data_objects` + `list_semantic_model_dimensions` — light confirm the apiNames you set
7. `add_semantic_model_relationship` per key pair (uses the apiNames you set — first-try)
8. `list_semantic_model_relationships` — confirm zero islands
9. `run_semantic_query` — confirm non-empty cross-object result

## Deleting a semantic definition

Component deletes (calculated dimension/measure, metric, data object, logical
view, relationship) are DESTRUCTIVE with no undo — get explicit user
confirmation first.
Whole-asset deletes (`delete_semantic_model` / viz / dashboard / workspace)
stay on `SKILL.md`. Cross-asset dependents of a viz or dashboard (how many
dashboards embed this viz) are `list_asset_dependencies` — details in
`dashboard-authoring.md`, **not** this section's
`list_semantic_model_dependencies`.

Use the real tool names: `delete_semantic_model_calculated_dimension`,
`delete_semantic_model_calculated_measure`, `delete_semantic_model_metric`,
`delete_semantic_model_data_object`, `delete_semantic_model_logical_view`,
`delete_semantic_model_relationship`.
There is no `delete_semantic_model_calculated_field`. Metric delete does **not**
cascade to the underlying measure (use `_calculated_measure` separately).
Confirm the target apiName with `list_*` / `get_*` first. Metric path is
`metricNameOrId`. For a logical view, confirm with
`get_semantic_model_logical_view`. For a relationship, confirm with
`list_semantic_model_relationships`; path is `relationshipNameOrId`.

Relationship delete has **no** `relationshipCascadeDelete` escape hatch —
direct dependents must be removed or repointed manually after the
`rawEdges: true` preflight. Calculations or metrics that only reference fields
on the joined objects depend on those **data objects**, not the join, and do
**not** block deleting the relationship.

### Preflight

Call `list_semantic_model_dependencies` with **`rawEdges: true`** before every
component delete. Default `rawEdges: false` is LOSSY — it collapses every edge
to the leaf data object, hiding calc-on-calc and metric-on-calc dependents. The
call still returns **200 OK with a plausible graph** (silent false negative).

Optional `types` is **TitleCase** (`CalculatedDimension`,
`CalculatedMeasurement`, `Metric`, `Relationship`, `LogicalView`), not
screaming-case. When omitted, defaults to CalculatedDimension and
CalculatedMeasurement **only** — Metric / Relationship / LogicalView are
omitted unless you ask.

The result is keyed by depender: `definitionApiName` + `dependencies[]`. With
`rawEdges: true`, dependency `definitionType` / `label` / `modelApiName` may be
null — rely on `apiName`. **Ignore `fieldApiName`** (null here). To find
dependents of X, scan entries whose `dependencies[]` contains apiName X. For a
data object, also scan child dimensions/measures. Scope is the current model
and its **base models** only — extending-model dependers are not returned.

### Operation ordering

Delete is **BLOCKED** if dependents exist. Delete **leaf dependents first**,
then re-query the graph, then delete this field.

| Flag | What it actually clears |
|---|---|
| `relationshipCascadeDelete: true` | Dependent **relationship rows** only — **not** calc / metric / LV / dimension dependents. Does **not** touch native columns |
| Metric delete | **No** cascade escape hatch — clear dependents manually. Does not delete the underlying calc/raw measure |
| Relationship delete | **No** `relationshipCascadeDelete` escape hatch — remove or repoint direct dependents manually. Calcs/metrics that only reference fields on the joined objects depend on those **data objects**, not the join, and do not block this delete |
| Data-object delete | Cascade flag auto-removes **joins** that reference the object; calc fields, metrics, and dimensions must be removed first |

Set `relationshipCascadeDelete: true` on LV / calc / data-object deletes unless
you are preserving orphaned relationship rows — still clear non-relationship
dependents first.

### Recovery

- **Multi-dependent errors concatenate entries WITHOUT a separator** (e.g.
  `...CALCULATED_DIMENSIONDependency API name: m_uses_dim...`). Do **not**
  string-parse the error — read dependents from the pre-flight.
- **Logical-view blocked delete is a different shape.** Calc/metric deletes
  return a clean "can't be deleted because it has dependent elements" message.
  A blocked LV delete currently surfaces as **HTTP 500 with a raw Java stack
  trace** whose root contains `VetoDataChangeException ... DEPENDENCY_EXISTS`
  ("This semantic definition is referenced elsewhere in Salesforce…"). Treat
  500 + `DEPENDENCY_EXISTS` as a **dependency block, NOT a transient failure —
  do not retry.** The stack does not name the blocker; use the pre-flight.
- Success is often HTTP 204: `defaultExc` is the literal string `"204"` (not
  JSON-parseable) — branch on `responseCode === 204`.

## Response double-wrap

Some tools (e.g. `add_semantic_model_dimension`, `run_query`,
`run_semantic_query`, `create_workspace`) wrap the body as
`{"defaultExc": "<stringified JSON>", "responseCode": <number>}`. Parse
`JSON.parse(response.defaultExc)` to read the result. Read tools like
`list_semantic_model_*` and `get_dashboard` are NOT wrapped — read fields
directly.
