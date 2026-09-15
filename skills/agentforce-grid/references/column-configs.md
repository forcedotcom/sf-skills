# Column Configurations Reference

Complete JSON configurations for all 12 Agentforce Grid column types.

## CRITICAL: Config Structure

**All column configs follow this nested structure:**

```json
{
  "name": "Column Name",
  "type": "AI",                          // Type value (see table below)
  "config": {
    "type": "AI",                        // type repeated inside config (REQUIRED)
    "numberOfRows": 50,                  // Optional, at config level
    "queryResponseFormat": {...},        // REQUIRED for processing columns
    "autoUpdate": true,                  // REQUIRED
    "config": {                          // Nested config with column-specific fields
      "autoUpdate": true,
      // ... column-specific configuration
    }
  }
}
```

## Type Values

| Column Type | type value | columnType in referenceAttributes |
|-------------|------------|-----------------------------------|
| AI | `"Ai"` (canonical) or `"AI"` | `"AI"` |
| Object | `"Object"` | `"Object"` |
| Reference | `"Reference"` | `"Reference"` |
| Text | `"Text"` | `"Text"` |
| PromptTemplate | `"PromptTemplate"` | `"PromptTemplate"` |
| InvocableAction | `"InvocableAction"` | `"InvocableAction"` |
| Action | `"Action"` | `"Action"` |
| AgentTest | `"AgentTest"` | `"AgentTest"` |
| Agent | `"Agent"` | `"Agent"` |
| Evaluation | `"Evaluation"` | `"Evaluation"` |
| Formula | `"Formula"` | `"Formula"` |
| DataModelObject | `"DataModelObject"` | `"DataModelObject"` |

**Note:** `type` and `columnType` in referenceAttributes both use PascalCase (e.g., `"Text"`, `"Object"`, `"AgentTest"`). The Connect API canonical wire value for AI columns is `"Ai"`, but the server is case-insensitive -- `"AI"`, `"Ai"`, `"ai"` all work.

## queryResponseFormat (CRITICAL)

**This determines whether a column imports new data or processes existing rows.**

```json
// EACH_ROW - Process each existing row (USE THIS when worksheet already has data)
"queryResponseFormat": {
  "type": "EACH_ROW"
}

// WHOLE_COLUMN - Import new data into the worksheet
"queryResponseFormat": {
  "type": "WHOLE_COLUMN",
  "splitByType": "OBJECT_PER_ROW"
}
```

**IMPORTANT RULE**: When a worksheet already has data (from Object, Text, CSV import, etc.), new columns should use `EACH_ROW` to process each existing row. Only use `WHOLE_COLUMN` when importing new data.

| Scenario | queryResponseFormat |
|----------|---------------------|
| Adding AI column to process existing Account data | `{"type": "EACH_ROW"}` |
| Adding Agent column to test with existing utterances | `{"type": "EACH_ROW"}` |
| Adding Object column to import new records | `{"type": "WHOLE_COLUMN", "splitByType": "OBJECT_PER_ROW"}` |
| Adding Text column from CSV import | `{"type": "WHOLE_COLUMN", "splitByType": "OBJECT_PER_ROW"}` |

## ReferenceAttribute

Used to reference other columns in configurations. **Use PascalCase for columnType.**

```json
{
  "columnId": "1W5SB000005zk6H0AQ",
  "columnName": "Accounts",
  "columnType": "Object",
  "fieldName": "Name"
}
```

**For Reference columns, fieldName can be empty:**
```json
{
  "columnId": "1W5SB0000060AqL0AU",
  "columnName": "Leads.Title",
  "columnType": "Reference"
}

By default, `referenceAttributes` are optional (`isRequired` defaults to `false`). If the referenced cell is empty, an empty string is substituted. Set `"isRequired": true` on a referenceAttribute to block execution when the reference is missing -- the cell will get status `MissingInput` instead of processing.
```

## ModelConfig (Required for AI/PromptTemplate)

**Always specify modelConfig. Use the model `name` for both fields:**

```json
{
  "modelId": "sfdc_ai__DefaultGPT4Omni",
  "modelName": "sfdc_ai__DefaultGPT4Omni"
}
```

**Recommended models (active, high-capability):**
- `sfdc_ai__DefaultGPT4Omni` - GPT 4 Omni (16K tokens)
- `sfdc_ai__DefaultGPT41` - GPT 4.1 (32K tokens)
- `sfdc_ai__DefaultGPT5` - GPT 5 (128K tokens)
- `sfdc_ai__DefaultGPT5Mini` - GPT 5 Mini (128K tokens)
- `sfdc_ai__DefaultO3` - O3 (100K tokens)
- `sfdc_ai__DefaultO4Mini` - O4 Mini (100K tokens)
- `sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet` - Claude 4.5 Sonnet (8K tokens)
- `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet` - Claude 4 Sonnet (8K tokens)
- `sfdc_ai__DefaultVertexAIGemini25Flash001` - Gemini 2.5 Flash (64K tokens)
- `sfdc_ai__DefaultVertexAIGeminiPro25` - Gemini 2.5 Pro (64K tokens)

Use `GET /llm-models` for the full list of available models in your org.

---

## 1. AI Column

Generate text using LLM with custom prompts.

**Type value:** `"AI"`

**Required fields in `config.config`:**
- `mode` (String, **required**) - Always `"llm"`
- `modelConfig` (ModelConfig, **required**) - LLM model selection
- `instruction` (String, **required**) - Prompt with `{$1}`, `{$2}` placeholders
- `referenceAttributes` (List, **required** when using placeholders) - Columns to substitute
- `responseFormat` (object, **required**) - Response format control
  - `type`: `"PLAIN_TEXT"` or `"SINGLE_SELECT"`
  - `options`: Array (empty `[]` for PLAIN_TEXT, or list of `{label, value}` for SINGLE_SELECT)

**Example - Processing Existing Row Data (MOST COMMON):**
```json
{
  "name": "Draft Email",
  "type": "AI",
  "config": {
    "type": "AI",
    "numberOfRows": 20,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "mode": "llm",
      "modelConfig": {
        "modelId": "sfdc_ai__DefaultGPT4Omni",
        "modelName": "sfdc_ai__DefaultGPT4Omni"
      },
      "instruction": "Write a personalized email for:\nName: {$1}\nTitle: {$2}\nCompany: {$3}",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "Leads", "columnType": "Object", "fieldName": "FirstName"},
        {"columnId": "col-uuid-2", "columnName": "Leads.Title", "columnType": "Reference"},
        {"columnId": "col-uuid-3", "columnName": "Leads.Company", "columnType": "Reference"}
      ],
      "responseFormat": {
        "type": "PLAIN_TEXT",
        "options": []
      }
    }
  }
}
```

**Example - Single Select Classification:**
```json
{
  "name": "Sentiment",
  "type": "AI",
  "config": {
    "type": "AI",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "mode": "llm",
      "modelConfig": {
        "modelId": "sfdc_ai__DefaultGPT4Omni",
        "modelName": "sfdc_ai__DefaultGPT4Omni"
      },
      "instruction": "Classify the sentiment of this text: {$1}",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "CustomerFeedback", "columnType": "Text"}
      ],
      "responseFormat": {
        "type": "SINGLE_SELECT",
        "options": [
          {"label": "Positive", "value": "positive"},
          {"label": "Negative", "value": "negative"},
          {"label": "Neutral", "value": "neutral"}
        ]
      }
    }
  }
}
```

---

## 2. Agent Column

Run agent conversations with dynamic inputs.

**Type value:** `"Agent"`

**Required fields in `config.config`:**
- `agentId` (String, required) - Agent definition ID
- `agentVersion` (String, required) - Agent version ID
- `utterance` (String, required) - Message with `{$1}`, `{$2}` placeholders
- `utteranceReferences` (List, optional) - Columns for placeholder substitution
- `contextVariables` (List, optional) - Agent context variables
- `initialState` (ReferenceAttribute, optional) - For multi-turn conversations
- `conversationHistory` (ReferenceAttribute, optional) - For multi-turn

**ContextVariable Structure:**
```json
// Static value
{
  "variableName": "Priority",
  "type": "Text",
  "value": "High"
}

// Column reference
{
  "variableName": "CustomerName",
  "type": "Text",
  "reference": {"columnId": "col-uuid", "columnName": "Name", "columnType": "Object"}
}
```

**CRITICAL**: Each ContextVariable must have EITHER `value` OR `reference`, not both.

**Note:** `testMode` is deprecated on Agent columns and has no effect. Do not include it in Agent column configs.

**Example:**
```json
{
  "name": "Sales Agent Response",
  "type": "Agent",
  "config": {
    "type": "Agent",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "agentId": "0XxRM000000xxxxx",
      "agentVersion": "0XyRM000000xxxxx",
      "utterance": "Hello, I need help with {$1}",
      "utteranceReferences": [
        {"columnId": "col-uuid-1", "columnName": "CustomerQuery", "columnType": "Text"}
      ],
      "contextVariables": [
        {
          "variableName": "CustomerName",
          "type": "Text",
          "reference": {"columnId": "col-uuid-2", "columnName": "Customers", "columnType": "Object", "fieldName": "Name"}
        },
        {
          "variableName": "Priority",
          "type": "Text",
          "value": "High"
        }
      ]
    }
  }
}
```

---

## 3. AgentTest Column

Test agents with utterances from a column. Used for batch testing.

**Type value:** `"AgentTest"`

**Required fields in `config.config`:**
- `agentId` (String, required)
- `agentVersion` (String, required)
- `inputUtterance` (ReferenceAttribute, required) - References Text column with test utterances
- `contextVariables` (List, optional)
- `initialState` (ReferenceAttribute, optional)
- `conversationHistory` (ReferenceAttribute, optional)
- `isDraft` (boolean, optional) - Test draft agent version
- `enableSimulationMode` (boolean, optional)

**Example:**
```json
{
  "name": "Agent Test",
  "type": "AgentTest",
  "config": {
    "type": "AgentTest",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "agentId": "0XxRM000000xxxxx",
      "agentVersion": "0XyRM000000xxxxx",
      "inputUtterance": {
        "columnId": "col-uuid-1",
        "columnName": "Test Utterances",
        "columnType": "Text"
      },
      "contextVariables": [],
      "isDraft": false,
      "enableSimulationMode": false
    }
  }
}
```

**Example with Context Variables:**
```json
{
  "name": "Agent Test with Context",
  "type": "AgentTest",
  "config": {
    "type": "AgentTest",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "agentId": "0XxRM000000xxxxx",
      "agentVersion": "0XyRM000000xxxxx",
      "inputUtterance": {
        "columnId": "col-uuid-1",
        "columnName": "Utterances",
        "columnType": "Text"
      },
      "contextVariables": [
        {
          "variableName": "AccountId",
          "type": "Text",
          "reference": {"columnId": "col-uuid-2", "columnName": "Accounts", "columnType": "Object", "fieldName": "Id"}
        }
      ]
    }
  }
}
```

---

#### Voice Testing (Conversation Level only)

AgentTest columns support voice testing when `evaluationMode` is `"TEXT_VOICE"`:
- `voiceMode`: `"LIVE"` | `"REPLAY"` | `"VOICE_CONV_MODE"`
- `selectedPersonas`: Array of persona types (e.g., `"DEFAULT"`, `"FRUSTRATED"`)
- `noiseType`: Background noise simulation (`"traffic"`, `"factory"`, `"airport"`, `"marketplace"`, etc.)
- `noiseVolume`: 0.0 to 1.0
- `audioEffects`: Object with sub-configs for lowPassFilter, clipping, gaussianNoise, packetLoss, compression

---

## 4. Object Column

Query Salesforce SObjects.

**Type value:** `"Object"`

**Required fields in `config.config`:**
- `objectApiName` (String, required) - SObject API name (e.g., "Account", "Contact")
- `fields` (List, required) - Fields to query with `name` and `type`
- `filters` (List, optional) - Filter conditions
- `advancedMode` (object, optional) - For raw SOQL queries
  - Uses `inputs.queryString` for the SOQL query
  - **IMPORTANT**: Placeholders use `{ColumnName}` or `{ColumnName.FieldName}` format (NOT `{$1}`)

**FieldConfig Structure:**

Fields must include both `name` and `type` properties. The `type` must match Salesforce field data types (UPPERCASE):

```json
{"name": "Id", "type": "ID"}
{"name": "Name", "type": "STRING"}
{"name": "Industry", "type": "PICKLIST"}
{"name": "AnnualRevenue", "type": "CURRENCY"}
{"name": "Phone", "type": "PHONE"}
{"name": "Website", "type": "URL"}
{"name": "Description", "type": "TEXTAREA"}
```

**Common Field Types:**
- `ID`, `STRING`, `TEXTAREA`
- `INTEGER`, `DOUBLE`, `LONG`, `CURRENCY`, `PERCENT`
- `BOOLEAN`, `DATE`, `DATETIME`, `TIME`
- `PICKLIST`, `MULTIPICKLIST`
- `PHONE`, `EMAIL`, `URL`
- `REFERENCE`, `ADDRESS`, `LOCATION`

Use `get_sobject_fields_display` or `get_sobject_fields_filter` tools to get the correct field types for your object.

**FilterOperator Values:**
- `In`, `NotIn`
- `EqualTo`, `NotEqualTo`
- `Contains`, `StartsWith`, `EndsWith`
- `IsNull`, `IsNotNull`
- `LessThan`, `LessThanOrEqualTo`, `GreaterThan`, `GreaterThanOrEqualTo`

**Example - Basic Query:**
```json
{
  "name": "Accounts",
  "type": "Object",
  "config": {
    "type": "Object",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "WHOLE_COLUMN",
      "splitByType": "OBJECT_PER_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "objectApiName": "Account",
      "fields": [
        {"name": "Id", "type": "ID"},
        {"name": "Name", "type": "STRING"},
        {"name": "Industry", "type": "PICKLIST"},
        {"name": "Description", "type": "TEXTAREA"}
      ],
      "filters": [
        {
          "field": "Industry",
          "operator": "In",
          "values": [
            {"value": "Technology", "type": "STRING"},
            {"value": "Finance", "type": "STRING"}
          ]
        }
      ]
    }
  }
}
```

**Example - Advanced SOQL:**
```json
{
  "name": "Custom Query",
  "type": "Object",
  "config": {
    "type": "Object",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "WHOLE_COLUMN",
      "splitByType": "OBJECT_PER_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "objectApiName": "Account",
      "advancedMode": {
        "type": "SOQL",
        "inputs": {
          "queryString": "SELECT Id, Name, Industry FROM Account WHERE Industry = '{TargetIndustry}' AND CreatedDate > LAST_N_DAYS:30 LIMIT 50"
        },
        "referenceAttributes": [
          {"columnId": "col-uuid-1", "columnName": "TargetIndustry", "columnType": "Text"}
        ]
      }
    }
  }
}
```

---

## 5. Formula Column

Compute values using formula expressions.

**Type value:** `"Formula"`

**Required fields in `config.config`:**
- `formula` (String, required) - Formula with `{$1}`, `{$2}` placeholders
- `returnType` (String, required) - Return type
- `referenceAttributes` (List, required) - Columns referenced in formula

**Common Return Types:**
- `string`, `boolean`, `double`, `integer`, `long`
- `date`, `datetime`, `time`
- `id`, `reference`

**Example - String Concatenation:**
```json
{
  "name": "Full Name",
  "type": "Formula",
  "config": {
    "type": "Formula",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "formula": "CONCATENATE({$1}, ' ', {$2})",
      "returnType": "string",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "FirstName", "columnType": "Text"},
        {"columnId": "col-uuid-2", "columnName": "LastName", "columnType": "Text"}
      ]
    }
  }
}
```

**Example - Boolean Expression:**
```json
{
  "name": "Is High Value",
  "type": "Formula",
  "config": {
    "type": "Formula",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "formula": "{$1} > 100000",
      "returnType": "boolean",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "Accounts", "columnType": "Object", "fieldName": "AnnualRevenue"}
      ]
    }
  }
}
```

---

## 6. PromptTemplate Column

Execute GenAI prompt templates.

**Type value:** `"PromptTemplate"`

**Required fields in `config.config`:**
- `promptTemplateDevName` (String, required) - Template developer name
- `promptTemplateVersionId` (String, optional)
- `promptTemplateType` (String, optional) - e.g., "flex"
- `modelConfig` (ModelConfig, required) - LLM model selection
- `promptTemplateInputConfigs` (List, required) - Input mappings

**PromptTemplateInputConfig Structure:**
```json
{
  "referenceName": "InputVariableName",
  "definition": "Description of the input",
  "referenceAttribute": {"columnId": "...", "columnName": "...", "columnType": "..."}
}
```

**Example:**
```json
{
  "name": "Email Generator",
  "type": "PromptTemplate",
  "config": {
    "type": "PromptTemplate",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "promptTemplateDevName": "Generate_Customer_Email",
      "promptTemplateType": "flex",
      "modelConfig": {
        "modelId": "sfdc_ai__DefaultGPT4Omni",
        "modelName": "sfdc_ai__DefaultGPT4Omni"
      },
      "promptTemplateInputConfigs": [
        {
          "referenceName": "CustomerName",
          "definition": "The customer's name",
          "referenceAttribute": {"columnId": "col-uuid-1", "columnName": "Customers", "columnType": "Object", "fieldName": "Name"}
        },
        {
          "referenceName": "Issue",
          "definition": "The customer's issue",
          "referenceAttribute": {"columnId": "col-uuid-2", "columnName": "CaseDescription", "columnType": "Text"}
        }
      ]
    }
  }
}
```

---

## 7. InvocableAction Column

Execute Flows, Apex, or other invocable actions.

**Type value:** `"InvocableAction"`

**Required fields in `config.config`:**
- `actionInfo` (object, required)
  - `actionType`: `FLOW`, `APEX`, etc.
  - `actionName`: Flow/Apex API name
  - `url`: Action URL
  - `label`: Display label
- `inputPayload` (String, required) - JSON payload with `{$1}` placeholders
- `referenceAttributes` (List, required) - Columns for placeholder substitution

**Example - Flow Execution:**
```json
{
  "name": "Create Case",
  "type": "InvocableAction",
  "config": {
    "type": "InvocableAction",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "actionInfo": {
        "actionType": "FLOW",
        "actionName": "Create_Support_Case",
        "url": "/services/data/v66.0/actions/custom/flow/Create_Support_Case",
        "label": "Create Support Case"
      },
      "inputPayload": "{\"Subject\": \"{$1}\", \"Description\": \"{$2}\", \"Priority\": \"{$3}\"}",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "Subject", "columnType": "Text"},
        {"columnId": "col-uuid-2", "columnName": "Description", "columnType": "Text"},
        {"columnId": "col-uuid-3", "columnName": "Priority", "columnType": "Text"}
      ]
    }
  }
}
```

**Example - Apex Action:**
```json
{
  "name": "Process Record",
  "type": "InvocableAction",
  "config": {
    "type": "InvocableAction",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "actionInfo": {
        "actionType": "APEX",
        "actionName": "ProcessRecordAction",
        "url": "/services/data/v66.0/actions/custom/apex/ProcessRecordAction",
        "label": "Process Record"
      },
      "inputPayload": "{\"recordId\": \"{$1}\"}",
      "referenceAttributes": [
        {"columnId": "col-uuid-1", "columnName": "Records", "columnType": "Object", "fieldName": "Id"}
      ]
    }
  }
}
```

---

## 8. Evaluation Column

Evaluate agent or prompt outputs using built-in or custom evaluations.

**Type value:** `"Evaluation"`

**Required fields in `config.config`:**
- `evaluationType` (String, required) - One of 13 evaluation types
- `inputColumnReference` (ReferenceAttribute, required) - Column to evaluate
- `referenceColumnReference` (ReferenceAttribute, conditional) - For comparison evaluations
- `autoEvaluate` (boolean, optional) - Auto-run evaluation
- `expressionFormula` (String, optional) - For EXPRESSION_EVAL type
- `customEvaluation` (object, optional) - For CUSTOM_LLM_EVALUATION

See [Evaluation Types Reference](evaluation-types.md) for complete guidance.

**Example - Response Match:**
```json
{
  "name": "Response Match",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "RESPONSE_MATCH",
      "inputColumnReference": {
        "columnId": "col-uuid-1",
        "columnName": "Agent Output",
        "columnType": "AgentTest"
      },
      "referenceColumnReference": {
        "columnId": "col-uuid-2",
        "columnName": "Expected Response",
        "columnType": "Text"
      },
      "autoEvaluate": true
    }
  }
}
```

**Example - Quality Score (No Reference):**
```json
{
  "name": "Coherence Score",
  "type": "Evaluation",
  "config": {
    "type": "Evaluation",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "evaluationType": "COHERENCE",
      "inputColumnReference": {
        "columnId": "col-uuid-1",
        "columnName": "Agent Output",
        "columnType": "AgentTest"
      },
      "autoEvaluate": true
    }
  }
}
```

---

## 9. DataModelObject Column

Query Data Cloud Data Model Objects (DMOs).

**Type value:** `"DataModelObject"`

**Required fields in `config.config`:**
- `dataModelObjectApiName` (String, required) - DMO API name
- `dataspaceName` (String, required) - Data Cloud dataspace
- `fields` (List, required) - Fields to query with `name` and `type`
- `filters` (List, optional) - Filter conditions
- `advancedMode` (object, optional) - For DCSQL queries
  - Uses `inputs.queryString` for the DCSQL query
  - **IMPORTANT**: Placeholders use `{ColumnName}` or `{ColumnName.FieldName}` format (NOT `{$1}`)

**Example:**
```json
{
  "name": "Unified Individuals",
  "type": "DataModelObject",
  "config": {
    "type": "DataModelObject",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "WHOLE_COLUMN",
      "splitByType": "OBJECT_PER_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "dataModelObjectApiName": "UnifiedIndividual__dlm",
      "dataspaceName": "default",
      "fields": [
        {"name": "Id__c", "type": "string"},
        {"name": "FirstName__c", "type": "string"},
        {"name": "LastName__c", "type": "string"},
        {"name": "Email__c", "type": "string"}
      ]
    }
  }
}
```

**Example - Advanced DCSQL:**
```json
{
  "name": "Custom DMO Query",
  "type": "DataModelObject",
  "config": {
    "type": "DataModelObject",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "WHOLE_COLUMN",
      "splitByType": "OBJECT_PER_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "dataModelObjectApiName": "UnifiedIndividual__dlm",
      "dataspaceName": "default",
      "advancedMode": {
        "type": "DCSQL",
        "inputs": {
          "queryString": "SELECT Id__c, FirstName__c, Email__c FROM UnifiedIndividual__dlm WHERE Email__c LIKE '%{EmailDomain}%'"
        },
        "referenceAttributes": [
          {"columnId": "col-uuid-1", "columnName": "EmailDomain", "columnType": "Text"}
        ]
      }
    }
  }
}
```

---

## 10. Reference Column

Extract specific fields from other columns using JSON path.

**Type value:** `"Reference"`

**Required fields in `config.config`:**
- `referenceColumnId` (String, required) - Source column ID
- `referenceField` (String, required) - JSON path to extract

**Example - Extract Agent Topic:**
```json
{
  "name": "Agent Topic",
  "type": "Reference",
  "config": {
    "type": "Reference",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "referenceColumnId": "agent-test-col-uuid",
      "referenceField": "response.topicName"
    }
  }
}
```

**Example - Extract Object Field (e.g., Account Name from Object column):**
```json
{
  "name": "Account Name",
  "type": "Reference",
  "config": {
    "type": "Reference",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "referenceColumnId": "accounts-col-uuid",
      "referenceField": "Name"
    }
  }
}
```

**Example - Extract Nested Field:**
```json
{
  "name": "First Bot Message",
  "type": "Reference",
  "config": {
    "type": "Reference",
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "referenceColumnId": "agent-col-uuid",
      "referenceField": "response.botMessages[0].text"
    }
  }
}
```

---

## 11. Text Column

Static or editable text input. Also supports CSV import.

**Type value:** `"Text"`

**CRITICAL:** Text columns CANNOT use an empty `config: {}`. The `type` field is required inside config.

**Optional fields in `config.config`:**
- `documentId` (String, optional) - For CSV import
- `documentColumnIndex` (Integer, optional) - CSV column index
- `includeHeaders` (Boolean, optional) - Include CSV headers

**Example - Manual Entry (Minimum required config):**
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

**Example - CSV Import:**
```json
{
  "name": "Imported Data",
  "type": "Text",
  "config": {
    "type": "Text",
    "numberOfRows": 100,
    "queryResponseFormat": {
      "type": "WHOLE_COLUMN",
      "splitByType": "OBJECT_PER_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "documentId": "069xxxxxxxxxxxxxxx",
      "documentColumnIndex": 0,
      "includeHeaders": true
    }
  }
}
```

---

## 12. Action Column

Execute standard platform actions.

**Type value:** `"Action"`

Similar to InvocableAction but for standard Salesforce actions.

**Required fields in `config.config`:**
- `actionName` (String, required) - Action API name
- `inputParams` (List, optional) - Input parameters with references

**InputParam Structure:**
```json
{
  "inputParamName": "parameterName",
  "referenceAttribute": {"columnId": "...", "columnName": "...", "columnType": "..."}
}
```

**Example:**
```json
{
  "name": "Chatter Post",
  "type": "Action",
  "config": {
    "type": "Action",
    "numberOfRows": 50,
    "queryResponseFormat": {
      "type": "EACH_ROW"
    },
    "autoUpdate": true,
    "config": {
      "autoUpdate": true,
      "actionName": "chatterPost",
      "inputParams": [
        {
          "inputParamName": "text",
          "referenceAttribute": {"columnId": "col-uuid-1", "columnName": "Message", "columnType": "Text"}
        }
      ]
    }
  }
}
```
