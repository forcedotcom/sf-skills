# Semantic Authoring API Reference

Complete REST API documentation for creating calculated fields, dimensions, and metrics on Semantic Data Models.

## Base URL

All endpoints use the base URL:
```
https://{instance}.salesforce.com/services/data/v66.0
```

Where `{instance}` is your Salesforce instance (e.g., `myorg` for `myorg.salesforce.com`)

**Important:** Semantic authoring endpoints do NOT use `minorVersion` query parameter (unlike visualization/dashboard endpoints).

## Authentication

All requests require Bearer token authentication:

```bash
-H "Authorization: Bearer {access_token}"
-H "Content-Type: application/json"
```

**Getting an Access Token (using SF CLI):**
```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org auth show-access-token --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')
```

**Required Permissions:**
- View Semantic Models
- Create/Edit Semantic Models

---

## Discovery Endpoints

### List Semantic Models

Get all semantic models available to the authenticated user.

**Endpoint:** `GET /ssot/semantic/models`

**Request:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Response:**
```json
{
  "semantic_models": [
    {
      "id": "0FKxx0000000001",
      "apiName": "Sales_Cloud12_backward",
      "label": "Sales Analytics",
      "description": "Sales performance metrics and trends",
      "dataspace": "default",
      "categories": ["Sales"],
      "createdDate": "2024-01-15T10:30:00Z",
      "lastModifiedDate": "2024-02-20T14:45:00Z"
    }
  ],
  "count": 1
}
```

### Get Semantic Model Definition

Retrieve complete structure of a semantic model including objects, dimensions, measurements, and metrics.

**Endpoint:** `GET /ssot/semantic/models/{sdmApiNameOrId}`

**Request:**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Response Structure:**
```json
{
  "id": "0FKxx0000000001",
  "apiName": "Sales_Cloud12_backward",
  "label": "Sales Analytics",
  "dataspace": "default",
  "semanticDataObjects": [
    {
      "apiName": "Opportunity_TAB_Sales_Cloud",
      "label": "Opportunities",
      "semanticDimensions": [
        {
          "apiName": "Region",
          "label": "Region",
          "fieldName": "Region__c",
          "dataType": "Text",
          "objectName": "Opportunity_TAB_Sales_Cloud"
        }
      ],
      "semanticMeasurements": [
        {
          "apiName": "Amount",
          "label": "Amount",
          "fieldName": "Amount",
          "dataType": "Number",
          "aggregationType": "Sum",
          "decimalPlace": 2,
          "objectName": "Opportunity_TAB_Sales_Cloud"
        }
      ]
    }
  ],
  "calculatedMeasurements": [
    {
      "apiName": "Total_Revenue_clc",
      "label": "Total Revenue",
      "expression": "SUM([Amount])",
      "aggregationType": "Sum",
      "dataType": "Number"
    }
  ],
  "calculatedDimensions": [
    {
      "apiName": "Deal_Size_Category_clc",
      "label": "Deal Size Category",
      "expression": "IF [Amount] > 100000 THEN 'Large' ELSE 'Small' END",
      "dataType": "Text"
    }
  ],
  "semanticMetrics": [
    {
      "apiName": "Total_Revenue_mtc",
      "label": "Total Revenue",
      "measurementReference": {
        "calculatedFieldApiName": "Total_Revenue_clc"
      },
      "timeDimensionReference": {
        "tableFieldReference": {
          "fieldApiName": "Close_Date",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      },
      "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"]
    }
  ]
}
```

---

## Creation Endpoints

### Create Calculated Measurement

Create a calculated measurement field on an SDM.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/calculated-measurements`

**Request body:**
```json
{
  "apiName": "Total_Revenue_clc",
  "label": "Total Revenue",
  "expression": "SUM([Amount])",
  "aggregationType": "Sum",
  "dataType": "Number",
  "decimalPlace": 2,
  "description": "Total revenue from all opportunities"
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-measurements" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Total_Revenue_clc",
    "label": "Total Revenue",
    "expression": "SUM([Amount])",
    "aggregationType": "Sum",
    "dataType": "Number",
    "decimalPlace": 2
  }'
```

**Required fields:**
- `apiName` (must end with `_clc`, no double underscores)
- `label`
- `expression` (Tableau formula)
- `aggregationType` (Sum, Avg, Min, Max, Count, UserAgg)
- `dataType` (Number, Text, Date, Boolean)

**Optional fields:**
- `description`
- `decimalPlace` (for Number type, default 2)

**Response:**
```json
{
  "id": "0Fmxx0000000001",
  "apiName": "Total_Revenue_clc",
  "label": "Total Revenue",
  "success": true
}
```

### Create Calculated Dimension

Create a calculated dimension field on an SDM.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/calculated-dimensions`

**Request body:**
```json
{
  "apiName": "Deal_Size_Category_clc",
  "label": "Deal Size Category",
  "expression": "IF [Amount] > 100000 THEN 'Large' ELSEIF [Amount] > 50000 THEN 'Medium' ELSE 'Small' END",
  "dataType": "Text",
  "description": "Categorizes deals by size"
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-dimensions" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Deal_Size_Category_clc",
    "label": "Deal Size Category",
    "expression": "IF [Amount] > 100000 THEN '\''Large'\'' ELSEIF [Amount] > 50000 THEN '\''Medium'\'' ELSE '\''Small'\'' END",
    "dataType": "Text"
  }'
```

**Required fields:**
- `apiName` (must end with `_clc`, no double underscores)
- `label`
- `expression` (Tableau formula)
- `dataType` (Text, Date, Boolean)

**Optional fields:**
- `description`

**Note:** Dimensions don't require `aggregationType` (only measurements do).

### Create Semantic Metric

Create a semantic metric on an SDM. Metrics reference existing calculated fields.

**Endpoint:** `POST /ssot/semantic/models/{{modelName}}/metrics`

**Request body (basic):**
```json
{
  "apiName": "Total_Revenue_mtc",
  "label": "Total Revenue",
  "aggregationType": "UserAgg",
  "measurementReference": {
    "calculatedFieldApiName": "Total_Revenue_clc"
  },
  "timeDimensionReference": {
    "tableFieldReference": {
      "fieldApiName": "Close_Date",
      "tableApiName": "Opportunity_TAB_Sales_Cloud"
    }
  },
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "filters": [],
  "isCumulative": false,
  "isGoalEditingBlocked": false
}
```

**curl example:**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/metrics" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Total_Revenue_mtc",
    "label": "Total Revenue",
    "aggregationType": "UserAgg",
    "measurementReference": {
      "calculatedFieldApiName": "Total_Revenue_clc"
    },
    "timeDimensionReference": {
      "tableFieldReference": {
        "fieldApiName": "Close_Date",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    },
    "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
    "filters": [],
    "isCumulative": false,
    "isGoalEditingBlocked": false
  }'
```

**Required fields:**
- `apiName` (must end with `_mtc`, no double underscores)
- `label`
- `aggregationType` (typically `UserAgg`)
- `measurementReference.calculatedFieldApiName` (must exist on SDM)
- `timeDimensionReference` (field + table for time-based analysis)
- `timeGrains` (array of: "Day", "Week", "Month", "Quarter", "Year")

**Optional fields:**
- `description`
- `additionalDimensions` (for breakdown analysis)
- `insightsSettings` (auto-generated if not provided)
- `filters`
- `isCumulative` (default false)
- `isGoalEditingBlocked` (default false)
- `sentiment` (SentimentTypeUpIsGood, SentimentTypeUpIsBad, SentimentTypeNone)

**Request body (with additional dimensions):**
```json
{
  "apiName": "Revenue_by_Region_mtc",
  "label": "Revenue by Region",
  "aggregationType": "UserAgg",
  "measurementReference": {
    "calculatedFieldApiName": "Total_Revenue_clc"
  },
  "timeDimensionReference": {
    "tableFieldReference": {
      "fieldApiName": "Close_Date",
      "tableApiName": "Opportunity_TAB_Sales_Cloud"
    }
  },
  "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
  "additionalDimensions": [
    {
      "tableFieldReference": {
        "fieldApiName": "Region",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    }
  ],
  "insightsSettings": {
    "insightTypes": [
      {"enabled": true, "type": "TopContributors"},
      {"enabled": true, "type": "TrendChangeAlert"},
      {"enabled": true, "type": "BottomContributors"}
    ],
    "insightsDimensionsReferences": [
      {
        "tableFieldReference": {
          "fieldApiName": "Region",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      }
    ],
    "pluralNoun": "regions",
    "singularNoun": "region",
    "sentiment": "SentimentTypeUpIsGood"
  },
  "filters": [],
  "isCumulative": false,
  "isGoalEditingBlocked": false
}
```

**Note:** `additionalDimensions` can reference either `tableFieldReference` (SDM fields) or `calculatedFieldApiName` (calculated dimensions).

**The `additionalDimensions` superset rule.** Every field referenced by `insightsSettings.identifyingDimension`, `insightsSettings.insightsDimensionsReferences[]`, or `filters[].fieldName` MUST also appear in top-level `additionalDimensions[]`. Two failure modes:

1. Insight / identifying dimension missing → **create fails**: `Validation Failed: ... Insight dimension (<Table>.<Field>) is missing from the metric additional dimensions.`
2. Filter field missing → **create succeeds but the metric is unqueryable**: `Metric Definition Filter Field <Field> is not found in Metric Definition.`

Downstream builders that consume this contract should enforce this pre-POST and auto-mirror `--identifying-dimension` / `--filter` fields into `additionalDimensions`.

**`identifyingDimension`.** The Tableau Next metric UI dereferences `insightsSettings.identifyingDimension` on load and crashes if it is absent. The builder emits it, defaulting to the first additional dimension:

```json
"insightsSettings": {
  "identifyingDimension": {
    "identifierDimensionReference": {
      "tableFieldReference": {
        "fieldApiName": "Region",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    }
  }
}
```

**Metric filters.** A non-empty `filters[]` requires a sibling `filterLogic` and fully-qualified `fieldName` values:

```json
"filters": [
  {
    "fieldName": "Opportunity_TAB_Sales_Cloud.Region",
    "operator": "Equals",
    "values": ["West"]
  }
],
"filterLogic": "1"
```

- `fieldName` must be qualified `Table.Field` (a bare name triggers "is not found in Metric Definition").
- `filterLogic` is `"1"` for one filter, `"1 AND 2"` for two, etc.
- Each filter field is auto-mirrored into `additionalDimensions` (the superset rule).
- **Operator enum** (verified live against a v66.0 org, 2026-06-23): `Equals`, `In`, `NotIn`, `Contains`, `NotContains`, `GreaterThan`, `LessThan`, `Between`, `StartsWith`. The server uses these CamelCase names and **rejects** SQL-style `EQUAL`/`GREATER_THAN_OR_EQUAL`/`NOT_EQUAL`; there is **no** `>=`, `<=`, or `!=` operator.

---

## Error Responses

All endpoints return structured error responses:

```json
{
  "error": {
    "code": "INVALID_FIELD",
    "message": "Field 'Amount' not found in semantic model 'Sales_Cloud12_backward'",
    "details": {
      "fieldName": "Amount",
      "availableFields": ["Total_Amount", "Close_Date", "Stage"]
    }
  }
}
```

**Common Error Codes:**
- `INVALID_TOKEN`: Authentication token is invalid or expired
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `RESOURCE_NOT_FOUND`: SDM not found
- `INVALID_FIELD`: Field reference doesn't exist in SDM
- `INVALID_JSON`: Malformed JSON structure
- `VALIDATION_ERROR`: JSON structure valid but business rules violated
- `DUPLICATE_API_NAME`: API name already exists on SDM

---

## Common Validation Rules

### API Name Rules

- Must end with `_clc` (calculated fields) or `_mtc` (metrics)
- Cannot contain double underscores (`__`)
- Must be unique within the SDM
- 1-80 characters, alphanumeric + underscore only

**Valid:**
- `Total_Revenue_clc`
- `Win_Rate_mtc`

**Invalid:**
- `Total__Revenue_clc` (double underscore)
- `Total_Revenue` (missing suffix)
- `Total Revenue_clc` (space not allowed)

### Expression Rules

- Must use valid Tableau functions
- Field references must exist in SDM: `[Field_Name]`
- String literals use single quotes: `'Large'`
- Case-insensitive function names: `SUM`, `Sum`, `sum` all work

### Aggregation Type Rules

- Required for measurements, not for dimensions
- Use `UserAgg` when expression includes aggregation functions
- Don't use `UserAgg` for simple field references

### Field-Reference Rules

- **Read back the auto-bind–suffixed apiName; never guess it.** Binding a field auto-suffixes its apiName *even with no collision* — `Region` → `Region5`, `Revenue` → `Revenue5`. The suffix is unpredictable. After creating/binding a field, read the real `apiName` from `discover_sdm.py --json` and use it verbatim; guessing yields "Field not found" or an opaque failure.
- **Calculated measures are model-level — omit `objectName`.** A calculated measure (`_clc`) is not bound to a single data object. When referencing it (e.g. in viz creation), omit `objectName` (leave it `null`). Supplying any `objectName` for a calc measure returns `UNKNOWN_EXCEPTION`. Raw SDM fields, by contrast, carry `objectName` = the owning `semanticDataObjects[].apiName`.
- **The server does no field-role validation.** It accepts a field in the wrong role (Text dimension as a measure, numeric measure as a dimension) and fails opaquely later with `UNKNOWN_EXCEPTION`. Validate roles client-side from discovery before constructing the call.

---

## Complete Workflow Example

**Scenario:** Create a win rate metric with regional breakdown.

**Step 1: Discover SDM**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Step 2: Create calculated field (win rate)**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/calculated-measurements" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Win_Rate_clc",
    "label": "Win Rate",
    "expression": "SUM([Won_Count]) / SUM([Total_Count])",
    "aggregationType": "UserAgg",
    "dataType": "Number",
    "decimalPlace": 4
  }'
```

**Step 3: Create metric with regional breakdown**
```bash
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward/metrics" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "apiName": "Win_Rate_by_Region_mtc",
    "label": "Win Rate by Region",
    "aggregationType": "UserAgg",
    "measurementReference": {
      "calculatedFieldApiName": "Win_Rate_clc"
    },
    "timeDimensionReference": {
      "tableFieldReference": {
        "fieldApiName": "Close_Date",
        "tableApiName": "Opportunity_TAB_Sales_Cloud"
      }
    },
    "timeGrains": ["Day", "Week", "Month", "Quarter", "Year"],
    "additionalDimensions": [
      {
        "tableFieldReference": {
          "fieldApiName": "Region",
          "tableApiName": "Opportunity_TAB_Sales_Cloud"
        }
      }
    ],
    "filters": [],
    "isCumulative": false,
    "isGoalEditingBlocked": false
  }'
```

**Step 4: Verify creation**
```bash
curl -X GET \
  "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/Sales_Cloud12_backward" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

Check response for `calculatedMeasurements` and `semanticMetrics` arrays to verify your new field and metric appear.

---

## Rate Limits

Salesforce API rate limits apply:
- **Standard:** 15,000 API requests per 24 hours per org
- **Unlimited:** 25,000 API requests per 24 hours per org

**Best Practices:**
- Batch field creation when possible
- Cache SDM definitions (they change infrequently)
- Use dry-run mode (`--dry-run` flag) to validate payloads before POSTing

---

## Additional Resources

- [Salesforce Semantic Layer API Docs](https://developer.salesforce.com/docs/data/semantic-layer)
- [OAuth 2.0 Authentication Guide](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_flows.htm)
- [SKILL.md](../SKILL.md) - Main workflow guide
- [tableau-functions.md](tableau-functions.md) - Complete function reference

## Endpoint Quick Reference (all in one place)

```
Discovery (no minor version):
GET    /services/data/v66.0/ssot/semantic/models
GET    /services/data/v66.0/ssot/semantic/models/{sdmName}

Build an SDM from scratch (no minor version):
POST   /services/data/v66.0/ssot/semantic/models                                   (create, anchor)
POST   /services/data/v66.0/ssot/semantic/models/{sdmName}/data-objects             (add object)
POST   /services/data/v66.0/ssot/semantic/models/{sdmName}/data-objects/{obj}/dimensions
POST   /services/data/v66.0/ssot/semantic/models/{sdmName}/data-objects/{obj}/measurements
POST   /services/data/v66.0/ssot/semantic/models/{sdmName}/relationships            (add join)
POST   /services/data/v66.0/semantic-engine/gateway                                 (cross-object query)
DELETE /services/data/v66.0/ssot/semantic/models/{sdmName}                          (cleanup)

Enrichment (no minor version):
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-measurements
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/calculated-dimensions
POST /services/data/v66.0/ssot/semantic/models/{sdmName}/metrics

AI-readiness / update (no minor version):
PATCH /services/data/v66.0/ssot/semantic/models/{sdmName}                       (model-level: agentEnabled, businessPreferences, description, categories)
GET   /services/data/v66.0/ssot/semantic/models/{sdmName}/metrics/{metricName}  (resolve full metric)
PUT   /services/data/v66.0/ssot/semantic/models/{sdmName}/metrics/{metricName}  (full-payload metric update)
PUT   /services/data/v66.0/ssot/semantic/models/{sdmName}/data-objects/{obj}/dimensions|measurements/{field}  (full-payload base-field update; PATCH=405)
PUT   /services/data/v66.0/ssot/semantic/models/{sdmName}/data-objects/{obj}     (full-payload data-object update; PATCH=405)
```

**Authentication:** All requests require `Authorization: Bearer {token}` header.
