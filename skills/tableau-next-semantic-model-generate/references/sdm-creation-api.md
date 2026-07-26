# SDM Creation API Reference

REST endpoints + payload shapes for **building a Semantic Data Model from
scratch** — create the model with an anchor data object, add further objects
incrementally, bind base dimensions/measures, and author model-level
relationships (joins). This is the contract the SDM-creation scripts
(`create_sdm.py`, `add_data_object.py`, `add_relationship.py`) build against.
All shapes are verified against the v66.0 semantic REST API. The examples below
use a `Workforce_SDM` model joining the DMOs `qb_hw_employee__dlm` and
`qb_hw_calendar__dlm`.

## Base URL & conventions

```
https://{instance}.salesforce.com/services/data/v66.0
```

- **No `minorVersion`.** Semantic endpoints (`/ssot/semantic/...`) omit the
  `minorVersion` query param that visualization/dashboard endpoints require.
- Bearer auth: `Authorization: Bearer {access_token}`, `Content-Type: application/json`.
- **Bodies are camelCase.** The relationship body uses
  `leftSemanticFieldApiName`/`rightSemanticFieldApiName`, captured below.

---

## 1. Create SDM (anchor-only)

**`POST /services/data/v66.0/ssot/semantic/models`** → **201**

Creates the model with a single **anchor** data object embedded in
`semanticDataObjects[]`. Keep it to one object per create call (the anchor +
incremental rule dodges the bulk-create timeout).

**Request:**
```json
{
  "apiName": "Workforce_SDM",
  "label": "Workforce SDM",
  "dataspace": "default",
  "semanticDataObjects": [
    {
      "apiName": "qb_hw_employee",
      "label": "qb_hw_employee",
      "dataObjectName": "qb_hw_employee__dlm",
      "dataObjectType": "Dmo",
      "tableType": "Standard",
      "shouldIncludeAllFields": true
    }
  ]
}
```

**Response (201, abbreviated):** full SDM body echoed back, including the
suffixed field apiNames the server assigned and the sub-resource URLs used by
operations 2–5:
```json
{
  "apiName": "Workforce_SDM",
  "label": "Workforce SDM",
  "dataspace": "default",
  "id": "2SMMM0000005Zd34AE",
  "queryUnrelatedDataObjects": "Exception",
  "semanticDataObjects": [
    {
      "apiName": "qb_hw_employee",
      "dataObjectName": "qb_hw_employee__dlm",
      "dataObjectType": "Dmo",
      "tableType": "Standard",
      "shouldIncludeAllFields": true,
      "isQueryable": "Queryable",
      "semanticDimensions": [
        { "apiName": "first_name1", "dataObjectFieldName": "first_name__c", "dataType": "Text", "displayCategory": "Discrete", "label": "first_name" },
        { "apiName": "Data_Source58", "dataObjectFieldName": "DataSource__c", "dataType": "Text", "displayCategory": "Discrete", "label": "Data Source" }
      ],
      "semanticMeasurements": [
        { "apiName": "position_id2", "dataObjectFieldName": "position_id__c", "dataType": "Number", "aggregationType": "Sum", "decimalPlace": 2, "displayCategory": "Continuous", "label": "position_id" },
        { "apiName": "organization_id2", "dataObjectFieldName": "organization_id__c", "dataType": "Number", "aggregationType": "Sum", "label": "organization_id" }
      ],
      "semanticDimensionsUrl": "/services/data/v66.0/ssot/semantic/models/Workforce_SDM/data-objects/qb_hw_employee/dimensions",
      "semanticMeasurementsUrl": "/services/data/v66.0/ssot/semantic/models/Workforce_SDM/data-objects/qb_hw_employee/measurements"
    }
  ],
  "semanticDataObjectsUrl": "/services/data/v66.0/ssot/semantic/models/Workforce_SDM/data-objects",
  "semanticRelationshipsUrl": "/services/data/v66.0/ssot/semantic/models/Workforce_SDM/relationships"
}
```

### apiName regex

The SDM `apiName` rules — the server rejects a malformed name (e.g. `1BadName`)
with a 400:

> *"The Semantic Model API Name can only contain underscores and alphanumeric
> characters. It must be unique, begin with a letter, not include spaces, not
> end with an underscore, and not contain two consecutive underscores."*

So the practical regex is `[A-Za-z][A-Za-z0-9_]{0,79}` with extra rules:
- begins with a letter,
- alphanumeric + single underscores only,
- **no trailing underscore**, **no consecutive `__`**,
- 1–80 chars, unique within the org.

The builder validates this client-side so the user never sees a server round-trip
for an obvious mistake.

### Data-object source suffixes

`dataObjectName` requires a type suffix; bare names are rejected. `dataObjectType`
must match:

| Source type | `dataObjectType` | `dataObjectName` suffix | Example |
|---|---|---|---|
| Data Lake Object | `Dlo` | `__dll` | `accounts__dll` |
| Data Model Object | `Dmo` | `__dlm` | `qb_hw_employee__dlm` |
| Calculated Insight | `Cio` | `__dlc` | `churn_score__dlc` |

The skill **accepts either** a DLO or a DMO. **Prefer `__dlm` (DMO) in
examples when a DMO is present**; accept `__dll` directly when only a DLO exists.
DMO/DLO *creation* is out of scope — the SDM is built on objects that already
exist.

### The apiName-suffixing landmine

With `shouldIncludeAllFields: true`, the server **numerically suffixes every
auto-bound apiName**, even on the first object with no name collision. For
example:

| Source column | Stored `apiName` |
|---|---|
| `first_name__c` | `first_name1` |
| `position_id__c` | `position_id2` |
| `organization_id__c` | `organization_id2` |
| `DataSource__c` | `Data_Source58` |

The suffix is **not predictable** from the source name. **Always resolve the
stored apiName** (operation 6 / `discover_sdm.py --json`) before referencing a
field in a relationship or query. Never construct the suffixed name yourself.

---

## 2. Add data object (incremental)

**`POST /services/data/v66.0/ssot/semantic/models/{sdm}/data-objects`** → **200**

Add one further object to an existing SDM. Same object shape as the anchor.
One object per call (avoids the bulk-create timeout).

**Request:**
```json
{
  "apiName": "qb_hw_position",
  "label": "qb_hw_position",
  "dataObjectName": "qb_hw_position__dlm",
  "dataObjectType": "Dmo",
  "tableType": "Standard",
  "shouldIncludeAllFields": true
}
```

**Response (200, abbreviated):** the object with server-suffixed field apiNames
(`position_id3`, `department_id2`, `Data_Source59`, …). Resolve these before
using them as join keys.

---

## 3. Add base dimension (controllable apiName)

**`POST /services/data/v66.0/ssot/semantic/models/{sdm}/data-objects/{obj}/dimensions`** → **201**

Bind a single base (non-calc) dimension with a **caller-supplied apiName that is
preserved verbatim** — no suffixing, because you are binding one field by hand
rather than via `shouldIncludeAllFields`. This is the clean-naming path.

**Request:**
```json
{
  "apiName": "Position_Title_Ctl",
  "label": "Position Title Controlled",
  "dataObjectFieldName": "position_title__c",
  "dataType": "Text",
  "displayCategory": "Discrete"
}
```

**Response (201):** `apiName` returned **unchanged** (`Position_Title_Ctl`) —
confirming the caller controls the apiName on a single-field add.

---

## 4. Add base measure (controllable apiName)

**`POST /services/data/v66.0/ssot/semantic/models/{sdm}/data-objects/{obj}/measurements`** → **201**

**Request:**
```json
{
  "apiName": "Dept_Id_Measure_Ctl",
  "label": "Department Id Measure Controlled",
  "dataObjectFieldName": "department_id__c",
  "dataType": "Number",
  "aggregationType": "Sum",
  "decimalPlace": 2,
  "displayCategory": "Continuous"
}
```

**Response (201):** `apiName` preserved (`Dept_Id_Measure_Ctl`),
`aggregationType: "Sum"`, `displayCategory: "Continuous"`.

### dataType ↔ aggregationType allow-list

Match the column's real storage type:

| `dataType` | Valid `aggregationType` |
|---|---|
| `Number`, `Percent`, `Currency` | `Sum`, `Avg`, `Count`, `CountDistinct`, `Min`, `Max` |
| `Text`, `Boolean` | `Count`, `CountDistinct`, `Min`, `Max` (no `Sum`/`Avg`) |
| `Date`, `DateTime` | `Count`, `CountDistinct`, `Min`, `Max` |

A `Sum`/`Avg` on a Text/Boolean/Date measure is invalid — the builder rejects it
pre-POST (the server otherwise fails opaquely at query time).

---

## 5. Add relationship (model-level join)

**`POST /services/data/v66.0/ssot/semantic/models/{sdm}/relationships`** → **201**

Relationships author and become queryable on REST. The join-key references use
the **resolved apiName** — bind the fields first (via the data-object
add) then reference their stored apiNames here.

**Request:**
```json
{
  "apiName": "qb_hw_employee_qb_hw_position",
  "label": "qb_hw_employee : qb_hw_position",
  "joinType": "Auto",
  "cardinality": "ManyToOne",
  "leftSemanticDefinitionApiName": "qb_hw_employee",
  "rightSemanticDefinitionApiName": "qb_hw_position",
  "criteria": [
    {
      "joinOperator": "Equals",
      "leftFieldType": "TableField",
      "leftSemanticFieldApiName": "position_id2",
      "rightFieldType": "TableField",
      "rightSemanticFieldApiName": "position_id3"
    }
  ]
}
```

**Response (201):**
```json
{
  "apiName": "qb_hw_employee_qb_hw_position",
  "cardinality": "ManyToOne",
  "joinType": "Auto",
  "label": "qb_hw_employee : qb_hw_position",
  "isEnabled": true,
  "isQueryable": "Queryable",
  "leftSemanticDefinitionApiName": "qb_hw_employee",
  "rightSemanticDefinitionApiName": "qb_hw_position",
  "criteria": [
    { "joinOperator": "Equals",
      "leftFieldType": "TableField", "leftSemanticFieldApiName": "position_id2",
      "rightFieldType": "TableField", "rightSemanticFieldApiName": "position_id3" }
  ]
}
```

### Relationship rules

- **`joinType` MUST be `"Auto"`** for model-level relationships.
  `Left`/`Right`/`Inner`/`Full` are valid only inside a logical view
  (`logicalViewId` set) — and logical views are **UI-only / out of scope**.
- **`label` is REQUIRED** despite the schema marking it optional.
- **`cardinality`** ∈ `OneToOne` / `OneToMany` / `ManyToOne` / `ManyToMany` /
  `Unspecified`. A fact→dimension join is typically **`ManyToOne`** (the default).
- **`leftSemanticDefinitionApiName` / `rightSemanticDefinitionApiName`** name the
  two data-object apiNames (the SDM-level object apiNames, e.g. `qb_hw_employee`).
- **`criteria[]`** is usually a single `joinOperator: "Equals"` on the natural key.
- **`leftFieldType` / `rightFieldType` = `"TableField"`** for regular
  dimensions/measures (the common case).
- **`leftSemanticFieldApiName` / `rightSemanticFieldApiName`** MUST be the
  **resolved semantic apiName** (e.g. `position_id2`) — read from the
  add-object response or `discover_sdm.py --json`.

### The #1 relationship error — do NOT use the raw source column name

Passing the raw `__c` source column name (e.g. `join_1__c`) instead of the
resolved semantic apiName returns **HTTP 400**:

> *"The field with API name (join_1__c) used in the relationship (neg_test_join)
> could not be found in the data object or logical view (qb_hw_employee). Verify
> that the field exists and matches the API name in the source configuration."*

The field DOES exist — but its semantic apiName is `join_12`, not `join_1__c`.
`add_relationship.py` rejects a `__c`-style reference pre-POST with guidance
pointing at the resolved apiName.

> Other `*FieldType` values (informational; not used by the base join path):
> `SemanticField` for calculated dimensions (`leftSemanticFieldApiName` = the
> calc dim apiName; row-level dependency required); `Formula` for
> expression-based joins. The skill's `add_relationship.py` builds the
> `TableField` case.

---

## 6. Resolve apiNames (discovery)

**`GET /services/data/v66.0/ssot/semantic/models/{sdm}`** → **200**

After every create/add, fetch the SDM to resolve the server-stored apiNames.
The relevant arrays:
- `semanticDataObjects[].apiName` — object apiNames.
- `semanticDataObjects[].semanticDimensions[].apiName` /
  `semanticMeasurements[].apiName` — the **suffixed** field apiNames (with
  `dataObjectFieldName` = the raw source column for reference).
- `semanticRelationships[]` — the authored joins, each with `criteria[]`,
  `leftSemanticDefinitionApiName`/`rightSemanticDefinitionApiName`,
  `cardinality`, `joinType`, and `isQueryable`.

`discover_sdm.py --json` surfaces these (objects/dims/measures + relationships).

---

## Proof the join works (cross-object query)

**`POST /services/data/v66.0/semantic-engine/gateway`** → **201**,
`status: "SUCCESS"`

The semantic-query gateway takes a **camelCase** body (`tableField`,
`semanticAggregationMethod`, `limitOptions`, `simpleSortOrder`). Worked query
spanning the **employee↔calendar** join (keys `join_12`↔`join_13`):

```json
{
  "semanticModelApiName": "Workforce_SDM",
  "structuredSemanticQuery": {
    "fields": [
      { "expression": { "tableField": { "name": "report_date1", "tableName": "qb_hw_calendar" } },
        "alias": "cal.report_date", "grouping": "ROW_GROUPING" },
      { "expression": { "tableField": { "name": "occupation_rate1", "tableName": "qb_hw_employee" } },
        "alias": "emp.occ_rate", "semanticAggregationMethod": "SEMANTIC_AGGREGATION_METHOD_SUM" }
    ],
    "options": {
      "limitOptions": { "limit": 8 },
      "sortOrders": [ { "simpleSortOrder": { "sortByFieldAlias": "emp.occ_rate", "sortingOrder": "DESC" } } ]
    }
  }
}
```

Returned `status: "SUCCESS"` with **non-null** `report_date` values (from
`qb_hw_calendar`) alongside `SUM(occupation_rate)` (from `qb_hw_employee`):

```json
{ "status": "SUCCESS",
  "queryResults": { "queryData": { "rows": [
    { "values": ["2023-02-24", 234670.0] },
    { "values": ["2025-05-15", 234670.0] },
    { "values": ["2024-10-01", 234670.0] }
  ] } } }
```

Because the model's `queryUnrelatedDataObjects` is `"Exception"`, a cross-object
query with **no join path throws** rather than returning data. This query
returned grouped rows that combine fields from both objects — **definitive proof
the relationship authored and is traversed**. `table_name`/`tableName` MUST be
the SDM **object apiName** (`qb_hw_calendar`), and `name` MUST be the
**suffixed** field apiName (`report_date1`).

- Aggregation method enum (query-time suffixes): `SUM`, `AVG`, `COUNT`, `MIN`,
  `MAX`, `USER_AGG`. Model `aggregationType` maps: `Sum→SUM`, `Average→AVG`,
  `Count→COUNT`, `CountDistinct→COUNT`, `Min→MIN`, `Max→MAX`.

---

## 6b. Register the SDM in a workspace

**`POST /services/data/v66.0/tableau/workspaces/{ws}/assets`** → **201**

After create, register the SDM so it surfaces in a workspace. The body takes
**exactly** `{assetId, assetType, assetUsageType}` — `assetId` is the SDM's
server **id** (NOT its apiName), and `name`/`label` are **rejected**
(`Unrecognized field "name"`; omitting `assetUsageType` gives `MISSING_PARAM`).

**Request:**
```json
{
  "assetId": "2SMMM0000005a654AA",
  "assetType": "SemanticModel",
  "assetUsageType": "Referenced"
}
```

**Response (201):** the asset echoed back with `name`/`label`/`createdBy`/`url`.
`create_sdm.py --workspace <ws>` does this automatically after a successful
create.

## 7. Delete SDM (cleanup)

**`DELETE /services/data/v66.0/ssot/semantic/models/{sdm}`** → **204**

Deletes the SDM (a subsequent GET returns 404). There is **no delete-DMO/DLO**
surface — only the SDM itself can be deleted.

---

## Endpoint summary

| Operation | Method | Path (no `minorVersion`) | Status |
|---|---|---|---|
| Create SDM (anchor) | POST | `/ssot/semantic/models` | 201 |
| Add data object | POST | `/ssot/semantic/models/{sdm}/data-objects` | 200 |
| Add base dimension | POST | `/ssot/semantic/models/{sdm}/data-objects/{obj}/dimensions` | 201 |
| Add base measure | POST | `/ssot/semantic/models/{sdm}/data-objects/{obj}/measurements` | 201 |
| Add relationship | POST | `/ssot/semantic/models/{sdm}/relationships` | 201 |
| Resolve apiNames (discovery) | GET | `/ssot/semantic/models/{sdm}` | 200 |
| Cross-object query | POST | `/semantic-engine/gateway` | 201 |
| Delete SDM | DELETE | `/ssot/semantic/models/{sdm}` | 204 |

## Bulk-create timeout recovery

Creating an SDM with **many** `semanticDataObjects[]` in one call can return a
generic timeout/error even though the SDM **persists** ~10–30s later. **Recovery:
wait ~30s, then `discover_sdm.py --list` to confirm persistence — do NOT
blind-retry the POST** (a retry hits `"Unique constraint violated"`). This is why
the skill creates with a **single anchor** object and adds the rest incrementally
(one object per call).

## Key guidance

1. **DLO or DMO:** accept either; **prefer `__dlm` (DMO)** when one is present.
2. **Join keys:** use the **resolved apiName** (e.g. `position_id2`) —
   the auto-bound name from the create/add response or `discover_sdm.py --json`.
   Never the raw `__c` source column, and never a guessed suffix.
3. **Relationships author on REST** (`isQueryable: "Queryable"`); confirm with a
   cross-object query that returns join-spanning rows.
