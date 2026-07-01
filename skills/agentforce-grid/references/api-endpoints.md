# API Endpoints Reference

Complete documentation for Agentforce Grid public Connect API.

## Base URL

```
/services/data/v66.0/public/grid
```

All endpoints are prefixed with this base URL.

---

## Workbook Operations

### List All Workbooks

```
GET /workbooks
```

**Response:**
```json
{
  "workbooks": [
    {
      "id": "1W4xx0000004xxxx",
      "name": "My Workbook"
    }
  ]
}
```

**Note:** This endpoint returns minimal workbook data. Use `GET /workbooks/{id}` to get the `aiWorksheetList`.

### Create Workbook

```
POST /workbooks
```

**Request:**
```json
{
  "name": "Agent Test Suite"
}
```

**Response:**
```json
{
  "id": "1W4xx0000004xxxx",
  "name": "Agent Test Suite"
}
```

### Get Workbook

```
GET /workbooks/{workbookId}
```

**Response:**
```json
{
  "id": "1W4xx0000004xxxx",
  "name": "Agent Test Suite",
  "aiWorksheetList": [
    {
      "id": "1W1xx0000004xxxx",
      "name": "Test Cases",
      "workbookId": "1W4xx0000004xxxx"
    }
  ]
}
```

### Delete Workbook

```
DELETE /workbooks/{workbookId}
```

**Response:** 204 No Content

---

## Worksheet Operations

### Create Worksheet

```
POST /worksheets
```

**Request:**
```json
{
  "name": "Agent Test Cases",
  "workbookId": "1W4xx0000004xxxx"
}
```

**Response:**
```json
{
  "autoUpdate": true,
  "cells": [],
  "columns": [],
  "id": "1W1xx0000004xxxx",
  "name": "Agent Test Cases",
  "rows": [],
  "workbookId": "1W4xx0000004xxxx"
}
```

### Get Worksheet Metadata

```
GET /worksheets/{worksheetId}
```

**Response:**
```json
{
  "id": "1W1xx0000004xxxx",
  "name": "Agent Test Cases",
  "workbookId": "1W4xx0000004xxxx",
  "cells": [...],
  "columns": [
    {
      "id": "1W5xx0000004xxxx",
      "name": "Test Utterances",
      "type": "Text",
      "status": "New",
      "config": {},              // Note: GET responses may return empty config
      "precedingColumnId": null,
      "worksheetId": "1W1xx0000004xxxx"
    }
  ],
  "rows": ["row-id-1", "row-id-2", "row-id-3"]  // Array of row ID strings
}
```

### Get Worksheet Data (RECOMMENDED)

```
GET /worksheets/{worksheetId}/data
```

Returns complete worksheet data including all cells.

**IMPORTANT:** This is the most reliable endpoint for reading worksheet state. `GET /worksheets/{id}` may return empty columns/rows/cells even when they exist. Always use `/data` to get the full state.

**Response:**
```json
{
  "id": "1W1xx0000004xxxx",
  "name": "Agent Test Cases",
  "columns": [...],
  "rows": [...],
  "columnData": {
    "column-id-1": [
      {
        "id": "cell-id-1",
        "worksheetColumnId": "column-id-1",
        "worksheetRowId": "row-id-1",
        "displayContent": "Hello, I need help",
        "status": "Complete"
      }
    ]
  }
}
```

### Get Worksheet Data (Generic Format)

```
GET /worksheets/{worksheetId}/data-generic
```

Returns data in a generic JSON format.

### Update Worksheet

```
PUT /worksheets/{worksheetId}
```

**Request:**
```json
{
  "name": "Updated Worksheet Name"
}
```

### Delete Worksheet

```
DELETE /worksheets/{worksheetId}
```

**Response:** 204 No Content

### Get Supported Column Types

```
GET /worksheets/{worksheetId}/supported-columns
```

Returns column types available for this worksheet.

**Response:**
```json
{
  "columnTypes": [
    {"category": null, "description": null, "icon": null, "label": "AI", "name": "AI"},
    {"category": null, "description": null, "icon": null, "label": "Object", "name": "Object"},
    {"category": null, "description": null, "icon": null, "label": "Agent", "name": "Agent"},
    {"category": null, "description": null, "icon": null, "label": "AgentTest", "name": "AgentTest"}
  ]
}
```

---

## Column Operations

### Add Column to Worksheet

```
POST /worksheets/{worksheetId}/columns
```

**Request (Text Column) - MUST include nested config with `type`:**
```json
{
  "name": "Test Utterances",
  "type": "Text",
  "config": {
    "type": "Text",
    "autoUpdate": true,
    "config": {
      "autoUpdate": true
    }
  }
}
```

**CRITICAL:** An empty `"config": {}` will fail with a deserialization error. Always include the `type` field.

**Request (AgentTest Column):**
```json
{
  "name": "Agent Output",
  "type": "AgentTest",
  "config": {
    "type": "AgentTest",
    "numberOfRows": 50,
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "agentId": "0Xxxx0000000001CAA",
      "agentVersion": "0X9xx0000000001CAA",
      "inputUtterance": {
        "columnId": "utterance-col-id",
        "columnName": "Test Utterances",
        "columnType": "Text"
      },
      "contextVariables": []
    }
  }
}
```

**Response:**
```json
{
  "id": "1W5xx0000004xxxx",
  "name": "Agent Output",
  "worksheetId": "1W1xx0000004xxxx",
  "type": "AgentTest",
  "status": "New",
  "config": {...},
  "precedingColumnId": "previous-col-id"
}
```

### Update Column

**IMPORTANT:** Column operations use `/worksheets/{wsId}/columns/{colId}/...` path, NOT `/columns/{colId}/...`.

```
PUT /worksheets/{worksheetId}/columns/{columnId}
```

**Request:**
```json
{
  "name": "Updated Column Name",
  "config": {
    // updated configuration
  }
}
```

### Delete Column

```
DELETE /worksheets/{worksheetId}/columns/{columnId}
```

**Response:** 204 No Content

### Save Column (Without Processing)

```
POST /worksheets/{worksheetId}/columns/{columnId}/save
```

Saves column configuration without triggering cell processing.

**Request:**
```json
{
  "type": "Text",
  "name": "Column Name",
  "config": {}
}
```

**Note:** The `type` field is required in the save request body.

### Reprocess Column

```
POST /worksheets/{worksheetId}/columns/{columnId}/reprocess
```

Reprocesses all cells in the column. Request body: `{}`

### Get Column Data

```
GET /worksheets/{worksheetId}/columns/{columnId}/data
```

Returns all cell data for the column.

**Response:**
```json
{
  "cells": [
    {
      "id": "cell-id-1",
      "worksheetColumnId": "column-id",
      "worksheetRowId": "row-id-1",
      "displayContent": "Agent response text...",
      "fullContent": {...},
      "status": "Complete",
      "statusMessage": null
    }
  ]
}
```

---

## Row Operations

### Add Rows

```
POST /worksheets/{worksheetId}/rows
```

**Request:**
```json
{
  "numberOfRows": 10,
  "anchorRowId": "existing-row-id"
}
```

**Note:** `anchorRowId` is required when the worksheet already has rows.

**Response:**
```json
{
  "rowIds": [],
  "rowsAdded": 10,
  "success": true
}
```

### Delete Rows

```
POST /worksheets/{worksheetId}/delete-rows
```

**Request:**
```json
{
  "rowIds": ["row-id-1", "row-id-2", "row-id-3"]
}
```

---

## Cell Operations

### Update Cells

```
PUT /worksheets/{worksheetId}/cells
```

**IMPORTANT:** Cell updates use `fullContent` (an object), NOT `displayContent` (which is read-only).

**Request:**
```json
{
  "cells": [
    {
      "id": "cell-id-1",
      "fullContent": {"text": "New cell value"}
    }
  ]
}
```

**Note:** The `displayContent` field is read-only and cannot be used for updates. Use `fullContent` with an appropriate object structure. For populating cells with text data, prefer the Paste endpoint instead.
```

### Paste Data

```
POST /worksheets/{worksheetId}/paste
```

Paste a matrix of data into the worksheet. **Uses `matrix` field (not `data`).**

**Request:**
```json
{
  "startColumnId": "column-id",
  "startRowId": "row-id",
  "matrix": [
    [{"displayContent": "row1-col1"}, {"displayContent": "row1-col2"}],
    [{"displayContent": "row2-col1"}, {"displayContent": "row2-col2"}]
  ]
}
```

### Trigger Row Execution

```
POST /worksheets/{worksheetId}/trigger-row-execution
```

Triggers processing for specified rows.

**Request:**
```json
{
  "trigger": "RUN_ROW",
  "rowIds": ["row-id-1", "row-id-2"]
}
```

**Trigger Types:**
- `RUN_ROW` - Process all columns for specified rows (most common)
- `RUN_SELECTION` - Process specific cells (use `seedCellIds` instead of `rowIds`)
- `EDIT` - Re-trigger after cell edit (use `editedCells` array)
- `PASTE` - Re-trigger after paste (use `startColumnId` and `matrix`)

---

## Run Worksheet

### Run Worksheet

```
POST /run-worksheet
```

Runs a worksheet with specific row inputs and column configuration. Returns a job ID for polling via `GET /run-worksheet/{jobId}`.

**Request (default -- all columns in parallel):**
```json
{
  "worksheetId": "1W1xx0000004xxxx",
  "rowInputs": [...],
  "columnConfig": {...}
}
```

**Request (sequential -- columns run one at a time):**
```json
{
  "worksheetId": "1W1xx0000004xxxx",
  "rowInputs": [...],
  "columnConfig": {...},
  "runStrategy": "ColumnByColumn"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `worksheetId` | string | Yes | The worksheet to run |
| `rowInputs` | array | Yes | Row input data |
| `columnConfig` | object | Yes | Column configuration |
| `runStrategy` | string | No | Execution strategy. Omit (default) to run all columns in parallel. Set to `"ColumnByColumn"` to run columns sequentially, one at a time. |

**Response:**
```json
{
  "jobId": "job-id-string"
}
```

Use `GET /run-worksheet/{jobId}` to poll for results.

---

## CSV Import

### Import CSV to Worksheet

```
POST /worksheets/{worksheetId}/import-csv
```

Creates Text columns from uploaded CSV file.

---

## Agent Operations

### Get Available Agents

```
GET /agents
```

Returns list of active agents in the org.

**Response:**
```json
{
  "agents": [
    {
      "id": "0Xxxx0000000001CAA",
      "name": "Support Agent",
      "activeVersion": "0X9xx0000000001CAA"
    }
  ]
}
```

### Get Agent Variables

```
GET /agents/{activeVersionId}/variables
```

Returns context variables for an agent version. Use the `activeVersion` ID from the agents list (not the agent ID).

**Response:**
```json
{
  "variables": [
    {
      "name": "VerifiedCustomerId",
      "dataType": "Text",
      "description": null,
      "label": null
    }
  ]
}

---

## Prompt Template Operations

### Get Available Prompt Templates

```
GET /prompt-templates
```

**Response:**
```json
{
  "templates": [
    {
      "id": "Generate_Customer_Email",
      "developerName": "Generate_Customer_Email",
      "name": "Generate_Customer_Email"
    }
  ]
}
```

### Get Prompt Template by Name

```
GET /prompt-templates/{promptTemplateDevName}
```

Returns detailed template information including inputs.

---

## SObject Operations

### Get Available SObjects

```
GET /sobjects
```

Returns list of queryable SObjects.

**Response:**
```json
{
  "sobjects": [
    {
      "apiName": "Account",
      "label": "Account",
      "pluralLabel": "Accounts"
    }
  ]
}
```

### Get Fields for Display

```
POST /sobjects/fields-display
```

Returns fields suitable for display.

**Request:**
```json
{
  "sobjectList": ["Account", "Contact"]
}
```

**Note:** Use `sobjectList` in request body (array), NOT `objectApiName` query parameter.

### Get Fields for Filtering

```
POST /sobjects/fields-filter
```

Returns fields suitable for filtering.

**Request:**
```json
{
  "sobjectList": ["Account"]
}
```

### Get Fields for Record Update

```
POST /sobjects/fields-record-update
```

Returns fields that can be updated.

**Request:**
```json
{
  "sobjectList": ["Account"]
}
```

---

## Data Cloud Operations

### Get Available Dataspaces

```
GET /dataspaces
```

**Response:**
```json
{
  "dataspaces": [
    {
      "name": "default",
      "label": "Default Dataspace"
    }
  ]
}
```

### Get Data Model Objects

```
GET /dataspaces/{dataspace}/data-model-objects
```

Returns DMOs in the specified dataspace.

### Get DMO Fields

```
GET /dataspaces/{dataspace}/data-model-objects/{dmoName}/fields
```

Returns fields for a specific DMO.

---

## Invocable Action Operations

### Get Available Invocable Actions

```
GET /invocable-actions
```

Returns list of available invocable actions (Flows, Apex, etc.).

### Describe Invocable Action

```
GET /invocable-actions/describe?actionType=FLOW&actionName=Create_Case
```

Returns detailed information about a specific action including inputs/outputs.

### Generate Invocable Action Input

```
POST /worksheets/{worksheetId}/generate-ia-input
```

Generates input payload for an invocable action.

---

## Metadata Endpoints

### Get Column Types

```
GET /column-types
```

Returns all available column types.

### Get LLM Models

```
GET /llm-models
```

Returns available LLM models for AI columns.

**Response:**
```json
{
  "models": [
    {
      "name": "sfdc_ai__DefaultGPT4Omni",
      "label": "GPT 4 Omni",
      "maxContentLength": 16384,
      "encodingType": null
    },
    {
      "name": "sfdc_ai__DefaultGPT5",
      "label": "GPT 5",
      "maxContentLength": 128000,
      "encodingType": null
    },
    {
      "name": "sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet",
      "label": "Anthropic Claude Sonnet 4.5 on Amazon",
      "maxContentLength": 8192,
      "encodingType": null
    }
  ]
}
```

**Note:** The model `name` field is used for both `modelId` and `modelName` in column configs. Use `GET /llm-models` to discover all available models in your org. The API returns 37 models but not all are active.

**Active models (16 total - no prefix in label):**

**OpenAI:**
- `sfdc_ai__DefaultGPT41` (GPT 4.1) - 32768 tokens
- `sfdc_ai__DefaultGPT41Mini` (GPT 4.1 Mini) - 32768 tokens
- `sfdc_ai__DefaultGPT4Omni` (GPT 4 Omni) - 16384 tokens
- `sfdc_ai__DefaultGPT4OmniMini` (GPT 4 Omni Mini) - 16384 tokens
- `sfdc_ai__DefaultGPT5` (GPT 5) - 128000 tokens
- `sfdc_ai__DefaultGPT5Mini` (GPT 5 Mini) - 128000 tokens
- `sfdc_ai__DefaultO3` (O3) - 100000 tokens
- `sfdc_ai__DefaultO4Mini` (O4 Mini) - 100000 tokens
- `sfdc_ai__DefaultOpenAIGPT4OmniMini` (OpenAI GPT 4 Omni Mini) - 16384 tokens

**Anthropic (via Amazon Bedrock):**
- `sfdc_ai__DefaultBedrockAnthropicClaude45Haiku` (Anthropic Claude Haiku 4.5 on Amazon) - 8192 tokens
- `sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet` (Anthropic Claude Sonnet 4.5 on Amazon) - 8192 tokens
- `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet` (Anthropic Claude Sonnet 4 on Amazon) - 8192 tokens

**Google (via Vertex AI):**
- `sfdc_ai__DefaultVertexAIGemini25Flash001` (Google Gemini 2.5 Flash) - 65536 tokens
- `sfdc_ai__DefaultVertexAIGemini25FlashLite001` (Google Gemini 2.5 Flash Lite) - 65536 tokens
- `sfdc_ai__DefaultVertexAIGeminiPro25` (Google Gemini 2.5 Pro) - 65536 tokens

**Amazon:**
- `sfdc_ai__DefaultBedrockAmazonNovaLite` (Amazon Nova Lite) - 5000 tokens
- `sfdc_ai__DefaultBedrockAmazonNovaPro` (Amazon Nova Pro) - 5000 tokens

**Model Status Indicators:**
- **No prefix** = Active and recommended
- **(Disabled)** = Beta or disabled models
- **(Rerouted)** = Legacy models redirected to newer versions
- **(Deprecated)** = Older versions being phased out

### Get Evaluation Types

```
GET /evaluation-types
```

Returns available evaluation types.

**Response:**
```json
{
  "types": [
    {"name": "RESPONSE_MATCH", "label": null, "description": null},
    {"name": "INSTRUCTION_FOLLOWING", "label": null, "description": null},
    {"name": "ACTION_ASSERTION", "label": null, "description": null},
    {"name": "TOPIC_ASSERTION", "label": null, "description": null},
    {"name": "CUSTOM_LLM_EVALUATION", "label": null, "description": null},
    {"name": "CONCISENESS", "label": null, "description": null},
    {"name": "EXPRESSION_EVAL", "label": null, "description": null},
    {"name": "FACTUALITY", "label": null, "description": null},
    {"name": "BOT_RESPONSE_RATING", "label": null, "description": null},
    {"name": "COMPLETENESS", "label": null, "description": null},
    {"name": "LATENCY_ASSERTION", "label": null, "description": null},
    {"name": "COHERENCE", "label": null, "description": null}
  ]
}
```

**Note:** Returns `types` field (not `evaluationTypes`).

### Get Formula Functions

```
GET /formula-functions
```

Returns available formula functions for Formula columns.

### Get Formula Operators

```
GET /formula-operators
```

Returns available formula operators.

### Get Supported Types

```
GET /supported-types
```

Returns all supported types in Agentforce Grid.

---

## AI Generation Endpoints

### Create Column from Utterance

```
POST /worksheets/{worksheetId}/create-column-from-utterance
```

Uses AI to create a column based on natural language description.

**Request:**
```json
{
  "utterance": "Create an AI column that summarizes the account description"
}
```

### Generate SOQL from Natural Language

```
POST /generate-soql
```

Uses AI to generate SOQL from natural language.

**Request:**
```json
{
  "text": "Get all accounts in the Technology industry"
}
```

**Response:**
```json
{
  "soql": "SELECT Name, Id FROM Account WHERE Industry = 'Technology' LIMIT 50"
}
```

**Note:** Uses the `text` field (not `utterance` or `objectApiName`).
```

### Generate JSON Path

```
POST /worksheets/{worksheetId}/generate-json-path
```

Uses AI to generate JSON path for extracting fields.

---

## Formula Operations

### Validate Formula

```
POST /worksheets/{worksheetId}/validate-formula
```

Validates a formula configuration.

**Request:**
```json
{
  "formula": "CONCATENATE({$1}, ' ', {$2})",
  "returnType": "string",
  "referenceAttributes": [...]
}
```

---

## List View Operations

### Get Available List Views

```
GET /list-views
```

Returns available list views.

### Get List View SOQL

```
GET /list-views/{listViewId}/soql
```

Returns the SOQL query for a list view.

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "errorCode": "BAD_REQUEST",
  "message": "Required parameter 'worksheetId' is missing"
}
```

**Common Error Codes:**
- `BAD_REQUEST` (400) - Invalid request parameters
- `UNAUTHORIZED` (401) - Authentication required
- `NOT_FOUND` (404) - Resource not found
- `INTERNAL_SERVER_ERROR` (500) - Server error
