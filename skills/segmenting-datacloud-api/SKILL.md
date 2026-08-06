---
name: segmenting-datacloud-api
description: "Manage Salesforce Data Cloud segments via the Connect REST API using `sf api request rest`. Use this skill when the user wants to create, list, get, update, delete, publish, deactivate, or count segments in Data Cloud — even if they say \"Data 360\", \"CDP segments\", or just \"segments\". Also use when the user asks about segment members or segment status. TRIGGER when: user manages segments via REST API, needs full endpoint schemas, or wants to bypass the sf data360 plugin. DO NOT TRIGGER when: user explicitly uses sf data360 CLI commands (use segmenting-datacloud), or the task is DMO/mapping/identity-resolution/activation work."
compatibility: "Requires an org with Data Cloud enabled and the sf CLI installed"
metadata:
  version: "1.0"
---

# Data Cloud Segments — REST API via SF CLI

This skill manages Data Cloud segments through the Salesforce Connect API Segments endpoints, executed via `sf api request rest`.

## Authentication

All Segments endpoints require the **Core Salesforce token** (not the CDP token). The `sf api request rest` command handles authentication automatically using the target org.

Always include `-o <org-alias>` or rely on the default target org. The user's current default org is shown in the `sf api request rest --help` output.

## API Base Path

All endpoints live under `/services/data/v65.0/ssot/segments`. When calling `sf api request rest`, pass the full path starting with `/services/data/v65.0/`.

## Command Pattern

```bash
# GET request (no body)
sf api request rest "/services/data/v65.0/ssot/segments" -o <org>

# POST/PATCH with inline body
sf api request rest "/services/data/v65.0/ssot/segments" -X POST \
  -H "Content-Type:application/json" \
  -b '{"field":"value"}' \
  -o <org>

# POST/PATCH with body from file
sf api request rest "/services/data/v65.0/ssot/segments" -X POST \
  -H "Content-Type:application/json" \
  -b @/tmp/segment-body.json \
  -o <org>

# DELETE (requires empty JSON body due to sf CLI quirk)
sf api request rest "/services/data/v65.0/ssot/segments/MySegment" -X DELETE \
  -H "Content-Type:application/json" \
  -b '{}' \
  -o <org>
```

**Important sf CLI quirks:**
- DELETE requests require `-H "Content-Type:application/json" -b '{}'` — the CLI errors without a body.
- POST endpoints that accept no body (publish, deactivate) also need `-H "Content-Type:application/json" -b '{}'`.
- For complex JSON bodies, prefer writing to a temp file first and using `-b @/tmp/file.json` to avoid shell quoting issues.

## Operations

### 1. List Segments

```bash
sf api request rest "/services/data/v65.0/ssot/segments?batchSize=20&offset=0" -o <org>
```

**Query parameters** (all optional):
| Parameter | Type | Description |
|-----------|------|-------------|
| `batchSize` | integer | 1-200, default 20 |
| `offset` | integer | Number of segments to skip |
| `orderby` | string | Sort field + direction, e.g. `Name ASC`, `MarketSegmentType DESC` |
| `dataspace` | string | Data space name (default data space if omitted) |
| `filters` | string | Up to 10 filters joined by AND. See Filters section below |

**Response:**
```json
{
  "batchSize": 20,
  "offset": 0,
  "orderByExpression": "[Name asc]",
  "segments": [ ... ],
  "totalSize": 42
}
```

Each segment object in the array contains: `apiName`, `dataSpace`, `description`, `displayName`, `lastModifiedDate`, `marketSegmentDefinitionId`, `marketSegmentId`, `publishInterval`, `segmentOnApiName`, `segmentOnId`, `segmentStatus`, `segmentType`.

#### List Filters

Filterable fields: `Name` (displayName), `SegmentStatus`, `MarketSegmentType` (segmentType), `SegmentOn` (segmentOnApiName), `LastPublishedEndDateTime`.

Operators: `eq`, `contains`, `in` (comma-separated values), `!=`.

```
filters=Name contains MySegment AND SegmentStatus eq Active
filters=MarketSegmentType in Dbt,Waterfall AND SegmentOn eq individual
```

### 2. Create Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments" -X POST \
  -H "Content-Type:application/json" \
  -b @/tmp/create-segment.json \
  -o <org>
```

**Required fields:**
| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Segment description |
| `displayName` | string | Segment display name |
| `segmentOnApiName` | string | API name of the entity to segment on (e.g. `ssot__Individual__dlm`, `ssot__Account__dlm`) |
| `segmentType` | string | One of: `Dbt`, `Dynamic`, `Lookalike`, `Realtimez`, `Waterfall`. **Default to `Dbt` when the user does not specify a type.** |

**Optional fields:**
| Field | Type | Description |
|-------|------|-------------|
| `developerName` | string | API name for the segment (required for POST) |
| `additionalMetadata` | object | Map of additional metadata |
| `dataSpace` | string | Data space (use `dataspace` query param in v59+) |
| `publishSchedule` | string | Enum: `NoRefresh`, `One`, `Two`, `Four`, `Six`, `Twelve`, `TwentyFour` (hours) |
| `publishScheduleStartDateTime` | string | ISO datetime for schedule start — **must be in the future** |
| `publishScheduleEndDate` | string | ISO datetime for schedule end — despite the name, use full `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` format |
| `includeDbt` | object | SQL-based segment definition for Dbt segments. Structure: `{"models": {"models": [{"name": "m1", "sql": "..."}]}}`. Note the nested `models.models` — the outer `models` is an object, the inner `models` is an array of model objects each with `name` and `sql`. The SQL SELECT must include both the primary key (`ssot__Id__c`) and the key qualifier (`KQ_Id__c`) of the segmentOn entity. See [Data Cloud SQL Reference](https://developer.salesforce.com/docs/data/data-cloud-query-guide/guide/dc-query-section.html) for query syntax |
| `lookalikeCriteria` | object | Lookalike criteria |
| `lookbackPeriod` | string | Lookback period |

**Example — create a Dbt segment (default type):**
```json
{
  "description": "Customers with more than 5 purchases in the last 30 days",
  "displayName": "Frequent Recent Buyers",
  "developerName": "Frequent_Recent_Buyers",
  "segmentOnApiName": "ssot__Individual__dlm",
  "segmentType": "Dbt",
  "additionalMetadata": {},
  "includeDbt": {
    "models": {
      "models": [
        {
          "name": "m1",
          "sql": "SELECT ssot__Individual__dlm.ssot__Id__c, ssot__Individual__dlm.KQ_Id__c FROM ssot__Individual__dlm WHERE ssot__Individual__dlm.ssot__Id__c IN (SELECT IndividualId__c FROM ssot__SalesOrder__dlm WHERE CreatedDate__c >= DATEADD(day, -30, CURRENT_DATE) GROUP BY IndividualId__c HAVING COUNT(*) > 5)"
        }
      ]
    }
  },
  "publishSchedule": "TwentyFour",
  "publishScheduleStartDateTime": "2026-04-17T00:00:00.000Z",
  "publishScheduleEndDate": "2026-05-17T23:59:59.000Z"
}
```

**Important notes on Dbt SQL:**
- The SQL SELECT must include both the primary key (`ssot__Id__c`) and the key qualifier (`KQ_Id__c`) of the segmentOn entity, or the API will return an `ENTITY_SAVE_ERROR`.
- The `includeDbt` structure uses nested `models.models` — the outer `models` is an object, the inner `models` is an array of model objects each with `name` (e.g. `"m1"`) and `sql`.
- The GET response flattens this to `includeDbt.models: [...]` (single-level array), but the POST body requires the nested `models.models` structure.
- The SQL must follow Data Cloud SQL syntax. See the [Data Cloud SQL Reference](https://developer.salesforce.com/docs/data/data-cloud-query-guide/guide/dc-query-section.html) for supported functions, operators, and DMO querying patterns.

**Response (200):** Returns the full segment object with `apiName`, `marketSegmentId`, `marketSegmentDefinitionId`, `segmentStatus` (typically `PROCESSING`), and all provided fields.

**Error responses:**
- 400: Invalid segment type, empty developerName/displayName, parse error
- 409: Segment already exists

### 3. Get Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiNameOrId>" -o <org>
```

Pass either the segment API name (developerName) or the segment ID.

**Response (200):**
```json
{
  "segments": [ { ...segment object... } ]
}
```

### 4. Update Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiName>" -X PATCH \
  -H "Content-Type:application/json" \
  -b @/tmp/update-segment.json \
  -o <org>
```

Uses the same body schema as Create, with these differences:
- `developerName` is **not supported** for PATCH (can't rename the API name)
- `segmentType` is **not supported** for PATCH (can't change type after creation)
- `additionalMetadata` is **not supported** for PATCH

Include only the fields you want to change. The required fields (`description`, `displayName`, `segmentOnApiName`) must still be present.

**Example — update description and publish schedule:**
```json
{
  "description": "Updated description",
  "displayName": "Recent High Value Customers",
  "segmentOnApiName": "ssot__Individual__dlm",
  "publishSchedule": "TwentyFour"
}
```

### 5. Delete Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiName>" -X DELETE \
  -H "Content-Type:application/json" \
  -b '{}' \
  -o <org>
```

Returns **204 No Content** on success (empty output).

### 6. Publish Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentId>/actions/publish" -X POST \
  -H "Content-Type:application/json" -b '{}' \
  -o <org>
```

Uses the segment **ID** (not API name). No request body.

**Response (200):**
```json
{
  "errors": [],
  "jobId": "1f8f521f-0616-4bdf-a515-d95192475c95",
  "partitionId": "1sgxx00000000Pp_6157146b-...",
  "publishStatus": "PUBLISHING",
  "segmentId": "1sgxx00000000PpAAI",
  "success": true
}
```

### 7. Count Segment

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiName>/actions/count" -X POST \
  -H "Content-Type:application/json" \
  -b '{"preferApproxCount": true}' \
  -o <org>
```

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `preferApproxCount` | boolean | yes | `true` for approximate count (faster), `false` for exact |

**Response (200):**
```json
{
  "errors": [],
  "segmentId": "1sgxx00000000MbAAI",
  "success": true
}
```

### 8. Deactivate Segment

By API name:
```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiName>/actions/deactivate" -X POST \
  -H "Content-Type:application/json" -b '{}' \
  -o <org>
```

By segment ID:
```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentId>/actions/deactivate" -X POST \
  -H "Content-Type:application/json" -b '{}' \
  -o <org>
```

**Response (200):**
```json
{
  "errors": [],
  "segmentApiName": "TestFilter",
  "segmentId": "1sgxx00000000UfAAI",
  "success": true
}
```

### 9. Get Segment Members

**The segment must be published before you can retrieve members.** If the segment has never been published, the API will return a 404 `ITEM_NOT_FOUND` error.

```bash
sf api request rest "/services/data/v65.0/ssot/segments/<segmentApiName>/members?limit=100&offset=0" -o <org>
```

**Query parameters** (all optional):
| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated: `Id__c`, `KQ_Id__c`, `Delta_Type__c`, `Segment_Id__c`, `Parent_Segment_Id__c`, `Snapshot_Type__c`, `Timestamp__c`, `Version_Stamp__c` |
| `filters` | string | e.g. `Delta_Type__c IN ('New','Existing') AND Timestamp__c IN 2026-04-09T14:12:41.111Z` |
| `limit` | integer | 1-1000, default 100 |
| `offset` | integer | Rows to skip |
| `orderBy` | string | e.g. `Timestamp__c DESC` |

**Response (200):**
```json
{
  "data": [ ... ],
  "endTime": "2025-04-11T15:16:10.000Z",
  "filter": "Delta_Type__c in ( new , existing )",
  "limit": 100,
  "offSet": 0,
  "orderBy": "Id__c asc",
  "rowCount": 5,
  "startTime": "2025-04-11T15:16:10.000Z",
  "totalCount": 5
}
```

## Common Segment Entity API Names

| Entity | API Name |
|--------|----------|
| Individual | `ssot__Individual__dlm` |
| Account | `ssot__Account__dlm` |

When the user says "segment on individuals" or "segment on accounts", use these API names.

## Workflow: Create and Publish a Segment

A typical end-to-end flow:

1. **Create** the segment (POST) — returns `marketSegmentId`
2. **Get** the segment to confirm it was created and check status
3. **Publish** the segment using the `marketSegmentId` from step 1
4. **Check status** by getting the segment again — look at `segmentStatus`
5. **Count** the segment to trigger population count
6. **Get members** to see who's in the segment

## Troubleshooting

- **401 Unauthorized**: Run `sf org login web -a <alias>` to re-authenticate
- **404 Not Found**: Check the segment API name is correct (case-sensitive)
- **400 Bad Request**: Validate required fields are present; check `segmentType` enum values
- **409 Conflict**: Segment with that `developerName` already exists
