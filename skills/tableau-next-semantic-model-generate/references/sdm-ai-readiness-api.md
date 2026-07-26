# SDM AI-Readiness API Reference

REST endpoints + payload shapes for the **last mile of an SDM**: making it
**AI-ready** (flip `agentEnabled`, write a `businessPreferences` context block,
set `description` + `categories`) and **updating an existing metric** safely
(full-payload PUT so `identifyingDimension` / `insightsSettings` survive). This
is the contract the update scripts (`update_sdm.py`, `update_metric.py`) build
against. All shapes are verified against the v66.0 semantic REST API; the example
request/response status is shown per endpoint.

## Base URL & conventions

```
https://{instance}.salesforce.com/services/data/v66.0
```

- **No `minorVersion`.** Semantic endpoints (`/ssot/semantic/...`) omit the
  `minorVersion` query param (matches `sdm-creation-api.md`).
- Bearer auth: `Authorization: Bearer {access_token}`, `Content-Type: application/json`.
- **Bodies are camelCase.**
- `agentEnabled` = expose-to-AI (the metric/model is queryable by the agent);
  `isAiDrafted` = provenance (the model was drafted by AI). **Distinct fields —
  never conflated.** Making a model AI-ready sets `agentEnabled`, not
  `isAiDrafted`.

---

## 1. Model-level update (AI-readiness) — **PATCH**

**`PATCH /services/data/v66.0/ssot/semantic/models/{sdm}`** → **200**

A partial update: send **only** the fields you want to change. The server merges
them onto the existing model and echoes the full updated model back. Verb
confirmed **PATCH** (not PUT) — a partial body is the normal, supported case
(unlike metric update, §3, which is full-payload PUT).

**Accepted allowlist** (each field is settable via the REST PATCH):
`app, sourceCreation, isAiDrafted, queryUnrelatedDataObjects, businessPreferences,
description, agentEnabled, currency, label, categories`.

**Request** (happy path, HTTP 200):
```json
{
  "agentEnabled": true,
  "description": "Workforce model: headcount, hires, leavers by org and department.",
  "businessPreferences": "PURPOSE: Track workforce headcount.\nGRAIN & JOINS: employee joined to calendar.\nKEY DEFINITIONS: Headcount = active employees at period end.",
  "categories": []
}
```

**Response (200, abbreviated)** — note the server **HTML-encodes** the
`businessPreferences` body on the way in (`&` → `&amp;`):
```json
{
  "agentEnabled": true,
  "apiName": "Workforce_SDM",
  "businessPreferences": "PURPOSE: Track workforce headcount.\nGRAIN &amp; JOINS: employee joined to calendar.\nKEY DEFINITIONS: Headcount = active employees at period end.",
  "categories": [],
  "currency": { "useOrgDefault": true },
  "dataspace": "default",
  "description": "Workforce model: headcount, hires, leavers by org and department."
}
```

- **`categories`** is a **JSON array** of **controlled values** — NOT free-form
  text. The server validates each entry against a "Semantic Category" enum and
  rejects unknown values: a PATCH with `["HR", "People"]` returns **HTTP 400
  `POST_BODY_PARSE_ERROR: Invalid value for Invalid Semantic Category: HR`**.
  Send `[]` (the common case) or only known category values; a comma string is
  the CLI's job to split into a list, but the values themselves must be valid.
- **`currency`** comes back as `{"useOrgDefault": true}` (object), not a scalar.
- **Idempotent:** re-sending the same fields produces the same stored state.

---

## 2. `description` length cap — **255, measured on the RAW input**

The server caps `description` at **255 characters, measured on the raw (decoded)
input string** — NOT on the HTML-encoded length. The server *does* HTML-encode
the value before storing it (so the **stored** string can exceed 255 once `&` →
`&amp;` etc. inflate it), but the **255 limit is checked against what you send**.

Two cases settle this:

**Case A — 94 raw chars / 298 HTML-encoded chars → ACCEPTED (HTTP 200).**
A description of 94 raw characters containing 51 `&` signs encodes to 298
characters and is **accepted**; the stored value is the 298-char encoded form
(`...&amp;&amp;...`). If the cap were on the encoded length, 298 > 255 would be
rejected. It isn't → **the cap is not on the encoded length.**

**Case B — 256 raw plain-ASCII chars → REJECTED (HTTP 400).**
```
HTTP 400
"Error while updating semantic object: The update of semantic entity with API
 name ({sdm}) failed. caused by: Description: data value too large:
 AAAA...AAAA (max length=255)"
```
256 plain-ASCII chars (no special chars, so raw == encoded == 256) is rejected
with `max length=255`. → **the cap is 255 on the raw input length.**

**Guidance for the client-side guard:** reject a `description` when
`len(description) > 255` (raw length). Do **not** HTML-encode before measuring —
that would over-reject legitimate `&`-containing descriptions that the server
accepts. When rejecting, point the user to put depth in `businessPreferences`
(which takes multi-paragraph blocks with no limit; see §2a).

### 2a. `businessPreferences` length

`businessPreferences` accepts a multi-paragraph block (the 6-heading template —
hundreds of characters) without error; there is **no observed length limit**. The
field is the right home for the context depth that does **not** fit in the
255-char `description`. Like `description`, the server HTML-encodes the stored
value.

---

## 3. Metric update — **full-payload PUT**

**`PUT /services/data/v66.0/ssot/semantic/models/{sdm}/metrics/{metric}`** → **200**

Metric update is a **full-payload PUT** (not PATCH). The PUT body **replaces** the
metric definition. Any field you omit is dropped / reset — there is **no
server-side merge**. So a single-field change must re-send the **complete**
definition.

### Required re-sent fields

Always re-send, on every update, the full metric definition — at minimum:
`label`, `measurementReference`, `timeDimensionReference`, `insightsSettings`
(plus `apiName`, `aggregationType`, `timeGrains`, `additionalDimensions`,
`filters`, `isCumulative`, `isGoalEditingBlocked`). Strip server read-only
fields before PUT: `id, createdBy, createdDate, lastModifiedBy, lastModifiedDate,
url`.

**The safe pattern (what `update_metric.py` does):** GET the metric's full
definition → overlay the requested change → strip read-only fields → PUT the
**complete** body.

### Full PUT happy path (HTTP 200)

GET `.../metrics/{metric}` returns the full definition; re-PUT it with one changed
field (`description`) and everything else re-sent → **HTTP 200**; re-resolving the
metric confirms `insightsSettings` and all `additionalDimensions` are retained.

### The regression a partial PUT causes

A **partial** PUT (only `apiName` + `label` + `description` +
`measurementReference` + `timeDimensionReference` + `timeGrains`, **omitting**
`insightsSettings` and `additionalDimensions`) returns **HTTP 200** but causes
data loss, visible when you re-resolve the metric:

| field | before | after partial PUT |
|---|---|---|
| `additionalDimensions` | N entries | **0 entries** |
| `insightsSettings.insightsDimensionsReferences` | N | re-derived |
| `additionalDimensions` backing the identifying dim | present | **gone** |

Dropping `additionalDimensions` orphans the `identifyingDimension` (which must
reference an additional dimension — see the metric-create superset rule). **This
is the regression the full resolve-and-merge PUT prevents:** a single-field change
made naively (partial body) silently strips the breakdown dimensions and the
identifying dimension that make the metric usable in the Tableau Next UI.

### `identifyingDimension` shape

`insightsSettings.identifyingDimension` carries an
`identifierDimensionReference`, which is a normal dimension reference:
```json
"insightsSettings": {
  "identifyingDimension": {
    "identifierDimensionReference": {
      "tableFieldReference": { "fieldApiName": "Date", "tableApiName": "Daily_Property_Performance" }
    }
  }
}
```
- **Same-object** reference: `tableFieldReference.{fieldApiName, tableApiName}`.
- **Cross-object** reference: the CLI accepts `Field:Object` and emits the same
  `tableFieldReference` with `tableApiName` = the other object's apiName (a
  metric can identify on a dimension from a joined object).
- The identifying field MUST also appear in top-level `additionalDimensions[]`
  (the create-time superset rule applies to updates too).

### Time-comparison settings

`primaryTimeComparison` / `secondaryTimeComparison` are **top-level** optional
fields on the metric (siblings of `timeGrains`), not nested in `insightsSettings`.
They default to unset (`null`); when the CLI sets them they ride along in the full
PUT body like any other field.

### Full metric definition (resolved shape)

```json
{
  "apiName": "Headcount_mtc",
  "label": "Headcount",
  "aggregationType": "UserAgg",
  "description": "Number of active employees at the last date of the selected period",
  "measurementReference": { "calculatedFieldApiName": "Headcount_clc" },
  "timeDimensionReference": {
    "tableFieldReference": { "fieldApiName": "report_date", "tableApiName": "qb_hw_calendar" }
  },
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "additionalDimensions": [
    { "tableFieldReference": { "fieldApiName": "position_title", "tableApiName": "qb_hw_position" } }
  ],
  "filters": [],
  "isCumulative": false,
  "isGoalEditingBlocked": false,
  "insightsSettings": {
    "insightTypes": [ /* ... */ ],
    "insightsDimensionsReferences": [ /* mirrors additionalDimensions */ ],
    "pluralNoun": "", "singularNoun": "", "sentiment": "SentimentTypeUpIsGood"
  }
}
```
(Server read-only fields `id`/`createdBy`/`createdDate`/`lastModifiedBy`/
`lastModifiedDate` are present on GET and must be stripped before PUT.)

---

## 4. Verify a calc field in a semantic query — `semanticField`, NOT `calculatedField`

**`POST /services/data/v66.0/semantic-engine/gateway`** → **201**, `status: "SUCCESS"`

To reference an **existing SDM calculated field** (`_clc`) in a semantic query,
use the **`semanticField {name}`** expression shape (REST camelCase:
`semanticField`). The `calculatedField {name}` shape is for an **on-the-fly**
formula (it expects an inline `expression`); pointing it at an existing calc
field's name fails.

**WRONG (`calculatedField` by name) → HTTP 400 `INVALID_API_INPUT`:**
```json
{ "semanticModelApiName": "Workforce_SDM",
  "structuredSemanticQuery": {
    "fields": [ { "expression": { "calculatedField": { "name": "Headcount_clc" } }, "alias": "v" } ],
    "options": { "limitOptions": { "limit": 3 } } } }
```
```
HTTP 400
[{ "errorCode": "INVALID_API_INPUT",
   "message": "...QUERY_PREPARE|INVALID_ARGUMENT: Expression cannot be null or empty" }]
```

**CORRECT (`semanticField` by name) → HTTP 201, SUCCESS:**
```json
{ "semanticModelApiName": "Workforce_SDM",
  "structuredSemanticQuery": {
    "fields": [ { "expression": { "semanticField": { "name": "Headcount_clc" } }, "alias": "v" } ],
    "options": { "limitOptions": { "limit": 3 } } } }
```
```json
{ "status": "SUCCESS",
  "queryResults": { "queryData": { "rows": [ { "values": [2172.0] } ] } } }
```

(A text-based query DSL spells the same distinction in snake_case —
`semantic_field` / `calculated_field`; the REST gateway uses the camelCase
`semanticField` / `calculatedField` keys.)

---

## 5. Update a dimension / measurement / data object (description/label) — **full-payload PUT**

```
PUT .../data-objects/{obj}/dimensions|measurements/{field}   (base field)
PUT .../data-objects/{obj}                                   (data object)
```
→ **200** in both cases.

A raw base field's or a data object's `description` (and `label`) **can be updated
after create** — the sub-resource takes a **full-payload PUT**. **`PATCH` is
rejected at every level:**

```
PATCH .../data-objects/{obj}/dimensions/{field}      (or .../measurements/{field}, or .../data-objects/{obj})
HTTP 405
[{ "errorCode": "METHOD_NOT_ALLOWED",
   "message": "HTTP Method 'PATCH' not allowed. Allowed are DELETE,GET,HEAD,PUT" }]
```

Because PUT **replaces** the resource, re-send the **complete** definition or the
other fields get nulled. Same resolve-and-merge pattern as the metric update: GET
the resource → overlay the change → PUT the full body.

**Base field** — GET (resolve) → PUT (changed `description`) → 200; the read-back
shows the new `description` with `dataType` / `aggregationType` /
`dataObjectFieldName` intact:
```json
{ "apiName": "report_date", "label": "Report Date",
  "dataObjectFieldName": "report_date__c", "dataType": "Date",
  "displayCategory": "Discrete", "description": "The primary date field..." }
```
`update_field.py --dimension|--measurement <field> --description <text>` does this.

**Data object** — GET (resolve) → PUT (changed `description`) → 200; re-send the
full object body so `dataObjectName` / `dataObjectType` / `tableType` and the
nested `semanticDimensions`/`semanticMeasurements` arrays survive:
```json
{ "apiName": "qb_hw_calendar", "label": "qb_hw_calendar",
  "dataObjectName": "qb_hw_calendar__dlm", "dataObjectType": "Dmo",
  "tableType": "Standard", "description": "A standard calendar table..." }
```
`update_object.py <obj> --description <text>` does this.

For all of these: strip the read-only `id`/`createdBy`/`createdDate`/
`lastModifiedBy`/`lastModifiedDate` (and, for the data object, the derived
`semanticDimensionsUrl`/`semanticMeasurementsUrl`) before PUT.

---

## Endpoint summary

| Operation | Method | Path (no `minorVersion`) | Status |
|---|---|---|---|
| Model-level update (AI-readiness) | **PATCH** | `/ssot/semantic/models/{sdm}` | 200 |
| Metric update (full-payload) | **PUT** | `/ssot/semantic/models/{sdm}/metrics/{metric}` | 200 |
| Read model (discovery) | GET | `/ssot/semantic/models/{sdm}` | 200 |
| Resolve one metric (full def) | GET | `/ssot/semantic/models/{sdm}/metrics/{metric}` | 200 |
| Resolve one base field | GET | `/ssot/semantic/models/{sdm}/data-objects/{obj}/dimensions\|measurements/{field}` | 200 |
| Base-field update (full-payload) | **PUT** | `/ssot/semantic/models/{sdm}/data-objects/{obj}/dimensions\|measurements/{field}` | 200 |
| Resolve one data object | GET | `/ssot/semantic/models/{sdm}/data-objects/{obj}` | 200 |
| Data-object update (full-payload) | **PUT** | `/ssot/semantic/models/{sdm}/data-objects/{obj}` | 200 |
| Verify field/metric query | POST | `/semantic-engine/gateway` | 201 (SUCCESS) |

## Key landmines

1. **`description` cap = 255 on the RAW input.** The server HTML-encodes for
   storage but measures the limit against what you send. Guard with
   `len(description) > 255` (raw) — do NOT encode before measuring. Over-long →
   move depth into `businessPreferences`.
2. **Metric update is full-payload PUT** (not PATCH). Omitted fields are dropped.
   Always resolve-and-merge: GET full def → overlay change → PUT complete body.
3. **`identifyingDimension` must survive the PUT** (and must be a member of
   `additionalDimensions`). A naive partial PUT drops `additionalDimensions`
   to empty, orphaning it — and the Tableau Next metric UI dereferences
   `identifyingDimension` on load.
4. **Dimension / measurement / data-object descriptions update via full-payload
   PUT, not PATCH.** `PATCH` on the sub-resource returns **405**
   (`Allowed are DELETE, GET, HEAD, PUT`); a `PUT` of the **complete** definition
   (with the changed `description`/`label`) returns **200** — confirmed at all
   three levels (base dimension, base measurement, data object). Resolve first,
   then re-send the full body — see §5.
5. **Reference existing calc fields via `semanticField {name}`**, not
   `calculatedField {name}` (→ `INVALID_API_INPUT`).

## `businessPreferences` template

`businessPreferences` is the AI context block — there is **no observed length limit** (unlike `description`, which is capped at 255; see Common Errors), so put the depth here. Structure it with these six headings so the agent has the join graph, the metric semantics, the user's vocabulary, and the data caveats:

```
PURPOSE: What this model answers and for whom. The headline metrics.

GRAIN & JOINS: The grain of each object and how they join (the join graph) —
  e.g. employee : calendar (snapshot), employee : position (ManyToOne).

KEY DEFINITIONS: Precise definitions of the metrics/terms — e.g.
  "Headcount = count of active employees at the LAST date of the selected period."

SYNONYMS: The words users use mapped to model terms — e.g.
  "workforce / staff / people = employees; attrition = turnover."

DATA CAVEATS: What to warn about — empty/partial sources, known gaps, date ranges
  that have data, fields that look usable but aren't.

PREFERRED MEASURES: Which measure/metric to reach for by default for a given
  question, so the agent doesn't pick a near-duplicate.
```

## Update an existing metric (full-payload PUT) — commands

Metric update is a **full-payload PUT** — the body **replaces** the metric definition, so a single-field change must re-send the **complete** metric or the server silently drops `insightsSettings` / `additionalDimensions` / `identifyingDimension`. `update_metric.py` does this safely (resolve-and-merge: GET the full definition → overlay the change → PUT the complete body):

```bash
# Set the identifying dimension (the TN metric UI dereferences this on load)
python scripts/update_metric.py {{SDM_NAME}} {{Metric_mtc}} \
  --identifying-dimension "position_title:qb_hw_position"

# Cross-object identifying dimension (Field:Object on a joined object)
python scripts/update_metric.py {{SDM_NAME}} {{Metric_mtc}} \
  --identifying-dimension "Date:Daily_Property_Performance"

# Time comparisons
python scripts/update_metric.py {{SDM_NAME}} {{Metric_mtc}} \
  --primary-comparison PriorPeriod --secondary-comparison PriorYear

# Dry-run: print the full PUT body without calling the org
python scripts/update_metric.py {{SDM_NAME}} {{Metric_mtc}} \
  --identifying-dimension "gender:qb_hw_employee" --dry-run
```

`--identifying-dimension` takes `Field:Object` (`fieldApiName:tableApiName`); the field is mirrored into `additionalDimensions` if absent (the UI requires the identifying dimension to be a member).

## Update a base field's or data object's description — commands

Base dimension/measurement and data-object descriptions are also updatable — via full-payload PUT (PATCH returns 405). `update_field.py` / `update_object.py` resolve the full definition, overlay the change, and PUT the complete body (so `dataType`/`aggregationType` and the object's nested field arrays survive):

```bash
# Update a dimension's description
python scripts/update_field.py {{SDM_NAME}} {{Object}} \
  --dimension {{field}} --description "Business calendar date; the metric time anchor."

# Update a measurement's label + description
python scripts/update_field.py {{SDM_NAME}} {{Object}} \
  --measurement {{field}} --label "Headcount" --description "Active employees at period end."

# Update a data object's description
python scripts/update_object.py {{SDM_NAME}} {{Object}} \
  --description "Business calendar table; the time spine for all metrics."
```
