# Use Case Patterns Reference

Complete workflow examples for common Agentforce Grid use cases using MCP tool calls.

All tool calls use the MCP server prefix `mcp__grid-connect-mcp__`. For brevity, examples show just the tool name and parameters.

---

## Pattern 1: Agent Testing Pipeline

**Goal:** Test an agent with different utterances and evaluate responses.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Test Utterances | Text | Input test cases |
| 2 | Expected Responses | Text | Ground truth (optional) |
| 3 | Expected Topics | Text | Expected topic routing (optional) |
| 4 | Agent Output | AgentTest | Run agent |
| 5 | Response Match | Evaluation | Compare to expected |
| 6 | Topic Check | Evaluation | Verify topic routing |
| 7 | Quality Score | Evaluation | Assess coherence |

### Quick Path: setup_agent_test

For the most common case, use the all-in-one orchestration tool:

```
setup_agent_test({
  agentId: "0XxRM000000xxxxx",
  agentVersion: "0XyRM000000xxxxx",
  utterances: [
    "I need help resetting my password",
    "What's my account balance?",
    "Transfer me to a human"
  ],
  workbookName: "Agent Test Suite",
  worksheetName: "Sales Agent Tests",
  evaluationTypes: ["COHERENCE", "RESPONSE_MATCH", "TOPIC_ASSERTION"],
  expectedResponses: [
    "I can help you reset your password...",
    "Your account balance is...",
    "Let me transfer you..."
  ]
})
```

This single call creates the workbook, worksheet, Text columns, pastes data, adds the AgentTest column, and wires up evaluations.

### Step-by-Step Implementation (Manual)

Use this approach when you need more control over the pipeline.

**Step 1: Create Workbook and Worksheet**

```
create_workbook_with_worksheet({
  workbookName: "Agent Test Suite",
  worksheetName: "Sales Agent Tests"
})
// Returns: { workbookId, worksheetId, ... }
```

**Step 2: Add Text Column for Utterances**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Test Utterances",
  type: "Text",
  config: '{"name":"Test Utterances","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}'
})
```

**Step 3: Add Text Column for Expected Responses**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Expected Responses",
  type: "Text",
  config: '{"name":"Expected Responses","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}'
})
```

**Step 4: Add Text Column for Expected Topics**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Expected Topics",
  type: "Text",
  config: '{"name":"Expected Topics","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}'
})
```

**Step 5: Paste Test Data**

```
// First, get worksheet data to find row IDs
get_worksheet_data({ worksheetId: "{worksheetId}" })

// Paste utterances into the Text columns
paste_data({
  worksheetId: "{worksheetId}",
  startColumnId: "{utterances-column-id}",
  startRowId: "{first-row-id}",
  matrix: '[[{"displayContent":"I need help resetting my password"}],[{"displayContent":"What is my account balance?"}]]'
})
```

**Step 6: Add AgentTest Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Agent Output",
  type: "AgentTest",
  config: '{"name":"Agent Output","type":"AgentTest","config":{"type":"AgentTest","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"agentId":"0XxRM000000xxxxx","agentVersion":"0XyRM000000xxxxx","inputUtterance":{"columnId":"{utterances-column-id}","columnName":"Test Utterances","columnType":"Text"},"contextVariables":[]}}}'
})
```

**Step 7: Add Response Match Evaluation**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Response Match",
  type: "Evaluation",
  config: '{"name":"Response Match","type":"Evaluation","config":{"type":"Evaluation","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"evaluationType":"RESPONSE_MATCH","inputColumnReference":{"columnId":"{agent-output-column-id}","columnName":"Agent Output","columnType":"AgentTest"},"referenceColumnReference":{"columnId":"{expected-responses-column-id}","columnName":"Expected Responses","columnType":"Text"},"autoEvaluate":true}}}'
})
```

**Step 8: Add Topic Assertion Evaluation**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Topic Check",
  type: "Evaluation",
  config: '{"name":"Topic Check","type":"Evaluation","config":{"type":"Evaluation","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"evaluationType":"TOPIC_ASSERTION","inputColumnReference":{"columnId":"{agent-output-column-id}","columnName":"Agent Output","columnType":"AgentTest"},"referenceColumnReference":{"columnId":"{expected-topics-column-id}","columnName":"Expected Topics","columnType":"Text"},"autoEvaluate":true}}}'
})
```

**Step 9: Add Coherence Evaluation**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Quality Score",
  type: "Evaluation",
  config: '{"name":"Quality Score","type":"Evaluation","config":{"type":"Evaluation","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"evaluationType":"COHERENCE","inputColumnReference":{"columnId":"{agent-output-column-id}","columnName":"Agent Output","columnType":"AgentTest"},"autoEvaluate":true}}}'
})
```

**Step 10: Monitor Processing**

```
poll_worksheet_status({
  worksheetId: "{worksheetId}",
  maxAttempts: 30,
  intervalMs: 3000
})
```

Or for a one-time status check:

```
get_worksheet_summary({ worksheetId: "{worksheetId}" })
```

---

## Pattern 2: Data Enrichment with AI

**Goal:** Enrich Salesforce Account records with AI-generated summaries.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Accounts | Object | Query Account records |
| 2 | Company Summary | AI | Generate summaries |

### Step-by-Step Implementation

**Step 1: Create Worksheet**

```
create_workbook_with_worksheet({
  workbookName: "Account Enrichment",
  worksheetName: "Tech Account Enrichment"
})
```

**Step 2: Add Object Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Accounts",
  type: "Object",
  config: '{"name":"Accounts","type":"Object","config":{"type":"Object","numberOfRows":50,"queryResponseFormat":{"type":"WHOLE_COLUMN","splitByType":"OBJECT_PER_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"objectApiName":"Account","fields":[{"name":"Id","type":"ID"},{"name":"Name","type":"STRING"},{"name":"Industry","type":"PICKLIST"},{"name":"Description","type":"TEXTAREA"},{"name":"AnnualRevenue","type":"CURRENCY"}],"filters":[{"field":"Industry","operator":"In","values":[{"value":"Technology","type":"STRING"},{"value":"Finance","type":"STRING"}]}]}}}'
})
```

**Step 3: Add AI Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Company Summary",
  type: "AI",
  config: '{"name":"Company Summary","type":"AI","config":{"type":"AI","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"mode":"llm","modelConfig":{"modelId":"sfdc_ai__DefaultGPT4Omni","modelName":"sfdc_ai__DefaultGPT4Omni"},"instruction":"Write a brief 2-3 sentence summary of this company based on the following information:\\n\\nCompany Name: {$1}\\nIndustry: {$2}\\nDescription: {$3}\\nAnnual Revenue: {$4}\\n\\nFocus on their market position and key business characteristics.","referenceAttributes":[{"columnId":"{accounts-column-id}","columnName":"Accounts","columnType":"Object","fieldName":"Name"},{"columnId":"{accounts-column-id}","columnName":"Accounts","columnType":"Object","fieldName":"Industry"},{"columnId":"{accounts-column-id}","columnName":"Accounts","columnType":"Object","fieldName":"Description"},{"columnId":"{accounts-column-id}","columnName":"Accounts","columnType":"Object","fieldName":"AnnualRevenue"}],"responseFormat":{"type":"PLAIN_TEXT","options":[]}}}}'
})
```

**Step 4: Monitor**

```
poll_worksheet_status({ worksheetId: "{worksheetId}" })
```

---

## Pattern 3: Prompt Template Batch Processing

**Goal:** Run a prompt template across a dataset and evaluate quality.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Customer Names | Text | Input data |
| 2 | Issues | Text | Input data |
| 3 | Generated Emails | PromptTemplate | Execute template |
| 4 | Coherence | Evaluation | Quality check |
| 5 | Completeness | Evaluation | Coverage check |

### Step-by-Step Implementation

**Step 1: Create Input Columns**

```
create_workbook_with_worksheet({
  workbookName: "Prompt Testing",
  worksheetName: "Email Generator"
})
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Customer Names",
  type: "Text",
  config: '{"name":"Customer Names","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}'
})
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Issues",
  type: "Text",
  config: '{"name":"Issues","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}'
})
```

**Step 2: Add PromptTemplate Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Generated Emails",
  type: "PromptTemplate",
  config: '{"name":"Generated Emails","type":"PromptTemplate","config":{"type":"PromptTemplate","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"promptTemplateDevName":"Customer_Support_Email","promptTemplateType":"flex","modelConfig":{"modelId":"sfdc_ai__DefaultGPT4Omni","modelName":"sfdc_ai__DefaultGPT4Omni"},"promptTemplateInputConfigs":[{"referenceName":"CustomerName","definition":"Customer name","referenceAttribute":{"columnId":"{customer-names-column-id}","columnName":"Customer Names","columnType":"Text"}},{"referenceName":"Issue","definition":"Customer issue","referenceAttribute":{"columnId":"{issues-column-id}","columnName":"Issues","columnType":"Text"}}]}}}'
})
```

**Step 3: Add Evaluation Columns**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Coherence",
  type: "Evaluation",
  config: '{"name":"Coherence","type":"Evaluation","config":{"type":"Evaluation","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"evaluationType":"COHERENCE","inputColumnReference":{"columnId":"{generated-emails-column-id}","columnName":"Generated Emails","columnType":"PromptTemplate"},"autoEvaluate":true}}}'
})
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Completeness",
  type: "Evaluation",
  config: '{"name":"Completeness","type":"Evaluation","config":{"type":"Evaluation","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"evaluationType":"COMPLETENESS","inputColumnReference":{"columnId":"{generated-emails-column-id}","columnName":"Generated Emails","columnType":"PromptTemplate"},"autoEvaluate":true}}}'
})
```

---

## Pattern 4: Flow/Apex Testing

**Goal:** Test a Flow with different inputs and extract outputs.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Subject | Text | Flow input |
| 2 | Description | Text | Flow input |
| 3 | Priority | Text | Flow input |
| 4 | Flow Result | InvocableAction | Execute Flow |
| 5 | Case Id | Reference | Extract output |
| 6 | Status | Reference | Extract output |

### Step-by-Step Implementation

**Step 1: Discover the Flow**

```
get_invocable_actions()
// Find the Flow you want to test

describe_invocable_action({
  actionName: "Create_Support_Case",
  actionType: "FLOW"
})
// Returns input/output schema
```

**Step 2: Create Input Columns**

```
create_workbook_with_worksheet({
  workbookName: "Flow Testing",
  worksheetName: "Create Case Tests"
})
```

```
add_column({ worksheetId: "{worksheetId}", name: "Subject", type: "Text",
  config: '{"name":"Subject","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })

add_column({ worksheetId: "{worksheetId}", name: "Description", type: "Text",
  config: '{"name":"Description","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })

add_column({ worksheetId: "{worksheetId}", name: "Priority", type: "Text",
  config: '{"name":"Priority","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })
```

**Step 3: Add InvocableAction Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Flow Result",
  type: "InvocableAction",
  config: '{"name":"Flow Result","type":"InvocableAction","config":{"type":"InvocableAction","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"actionInfo":{"actionType":"FLOW","actionName":"Create_Support_Case","url":"/services/data/v66.0/actions/custom/flow/Create_Support_Case","label":"Create Support Case"},"inputPayload":"{\\\"Subject\\\": \\\"{$1}\\\", \\\"Description\\\": \\\"{$2}\\\", \\\"Priority\\\": \\\"{$3}\\\"}","referenceAttributes":[{"columnId":"{subject-column-id}","columnName":"Subject","columnType":"Text"},{"columnId":"{description-column-id}","columnName":"Description","columnType":"Text"},{"columnId":"{priority-column-id}","columnName":"Priority","columnType":"Text"}]}}}'
})
```

**Step 4: Add Reference Columns to Extract Outputs**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Case Id",
  type: "Reference",
  config: '{"name":"Case Id","type":"Reference","config":{"type":"Reference","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"referenceColumnId":"{flow-result-column-id}","referenceField":"outputValues.caseId"}}}'
})
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Status",
  type: "Reference",
  config: '{"name":"Status","type":"Reference","config":{"type":"Reference","queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"referenceColumnId":"{flow-result-column-id}","referenceField":"outputValues.status"}}}'
})
```

---

## Pattern 5: Multi-Turn Agent Conversation Testing

**Goal:** Test multi-turn conversations with conversation history.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Turn 1 Utterance | Text | First user message |
| 2 | Turn 1 Response | Agent | First agent response |
| 3 | Turn 2 Utterance | Text | Follow-up message |
| 4 | Turn 2 Response | Agent | Second response with history |

### Implementation

**Step 1: Create First Turn**

```
add_column({ worksheetId: "{worksheetId}", name: "Turn 1 Utterance", type: "Text",
  config: '{"name":"Turn 1 Utterance","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Turn 1 Response",
  type: "Agent",
  config: '{"name":"Turn 1 Response","type":"Agent","config":{"type":"Agent","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"agentId":"0XxRM000000xxxxx","agentVersion":"0XyRM000000xxxxx","utterance":"{$1}","utteranceReferences":[{"columnId":"{turn1-utterance-id}","columnName":"Turn 1 Utterance","columnType":"Text"}]}}}'
})
```

**Step 2: Create Second Turn with History**

```
add_column({ worksheetId: "{worksheetId}", name: "Turn 2 Utterance", type: "Text",
  config: '{"name":"Turn 2 Utterance","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Turn 2 Response",
  type: "Agent",
  config: '{"name":"Turn 2 Response","type":"Agent","config":{"type":"Agent","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"agentId":"0XxRM000000xxxxx","agentVersion":"0XyRM000000xxxxx","utterance":"{$1}","utteranceReferences":[{"columnId":"{turn2-utterance-id}","columnName":"Turn 2 Utterance","columnType":"Text"}],"conversationHistory":{"columnId":"{turn1-response-id}","columnName":"Turn 1 Response","columnType":"Agent","fieldName":"conversationHistory"}}}}'
})
```

---

## Pattern 6: AI Classification with Single Select

**Goal:** Classify text into categories using AI.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Customer Feedback | Text | Input text |
| 2 | Sentiment | AI | Classification |
| 3 | Category | AI | Classification |

### Implementation

```
add_column({ worksheetId: "{worksheetId}", name: "Customer Feedback", type: "Text",
  config: '{"name":"Customer Feedback","type":"Text","config":{"type":"Text","autoUpdate":true,"config":{"autoUpdate":true}}}' })
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Sentiment",
  type: "AI",
  config: '{"name":"Sentiment","type":"AI","config":{"type":"AI","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"mode":"llm","modelConfig":{"modelId":"sfdc_ai__DefaultGPT4Omni","modelName":"sfdc_ai__DefaultGPT4Omni"},"instruction":"Classify the sentiment of this customer feedback: {$1}","referenceAttributes":[{"columnId":"{feedback-column-id}","columnName":"Customer Feedback","columnType":"Text"}],"responseFormat":{"type":"SINGLE_SELECT","options":[{"label":"Positive","value":"positive"},{"label":"Negative","value":"negative"},{"label":"Neutral","value":"neutral"}]}}}}'
})
```

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Category",
  type: "AI",
  config: '{"name":"Category","type":"AI","config":{"type":"AI","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"mode":"llm","modelConfig":{"modelId":"sfdc_ai__DefaultGPT4Omni","modelName":"sfdc_ai__DefaultGPT4Omni"},"instruction":"Categorize this customer feedback: {$1}","referenceAttributes":[{"columnId":"{feedback-column-id}","columnName":"Customer Feedback","columnType":"Text"}],"responseFormat":{"type":"SINGLE_SELECT","options":[{"label":"Product Issue","value":"product"},{"label":"Service Issue","value":"service"},{"label":"Billing Issue","value":"billing"},{"label":"Feature Request","value":"feature"},{"label":"General Inquiry","value":"general"}]}}}}'
})
```

---

## Pattern 7: Data Cloud / DMO Enrichment

**Goal:** Query Data Cloud DMOs and enrich with AI-generated insights.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Unified Profiles | DataModelObject | Query DMO records |
| 2 | Profile Summary | AI | Generate insights |

### Step-by-Step Implementation

**Step 1: Discover Data Cloud Schema**

```
get_dataspaces()
// Returns: { dataspaces: [{ name: "default", label: "Default Dataspace" }] }

get_data_model_objects({ dataspace: "default" })
// Returns available DMOs in the dataspace

get_data_model_object_fields({ dataspace: "default", dmoName: "UnifiedIndividual__dlm" })
// Returns field definitions for the DMO
```

**Step 2: Create Workbook and Worksheet**

```
create_workbook_with_worksheet({
  workbookName: "Data Cloud Analysis",
  worksheetName: "Unified Profiles"
})
```

**Step 3: Add DataModelObject Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Unified Profiles",
  type: "DataModelObject",
  config: '{"name":"Unified Profiles","type":"DataModelObject","config":{"type":"DataModelObject","numberOfRows":50,"queryResponseFormat":{"type":"WHOLE_COLUMN","splitByType":"OBJECT_PER_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"dataModelObjectApiName":"UnifiedIndividual__dlm","dataspaceName":"default","fields":[{"name":"Id__c","type":"string"},{"name":"FirstName__c","type":"string"},{"name":"LastName__c","type":"string"},{"name":"Email__c","type":"string"}]}}}'
})
```

**Step 4: Add AI Enrichment Column**

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Profile Summary",
  type: "AI",
  config: '{"name":"Profile Summary","type":"AI","config":{"type":"AI","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"mode":"llm","modelConfig":{"modelId":"sfdc_ai__DefaultGPT4Omni","modelName":"sfdc_ai__DefaultGPT4Omni"},"instruction":"Create a brief customer profile summary:\\nName: {$1} {$2}\\nEmail: {$3}","referenceAttributes":[{"columnId":"{profiles-column-id}","columnName":"Unified Profiles","columnType":"DataModelObject","fieldName":"FirstName__c"},{"columnId":"{profiles-column-id}","columnName":"Unified Profiles","columnType":"DataModelObject","fieldName":"LastName__c"},{"columnId":"{profiles-column-id}","columnName":"Unified Profiles","columnType":"DataModelObject","fieldName":"Email__c"}],"responseFormat":{"type":"PLAIN_TEXT","options":[]}}}}'
})
```

---

## Pattern 8: List View Import

**Goal:** Import records from a Salesforce List View and enrich them.

### Column Setup

| Order | Column Name | Type | Purpose |
|-------|-------------|------|---------|
| 1 | Records | Object | Import via List View SOQL |
| 2 | Enrichment | AI | Process the records |

### Step-by-Step Implementation

**Step 1: Discover List Views**

```
get_list_views()
// Returns available list views with IDs

get_list_view_soql({
  listViewId: "{listViewId}",
  sObjectType: "Account"
})
// Returns: { soql: "SELECT Id, Name, ... FROM Account WHERE ..." }
```

**Step 2: Create Object Column with advancedMode**

Use the SOQL from the list view directly in an Object column's advanced mode:

```
add_column({
  worksheetId: "{worksheetId}",
  name: "List View Records",
  type: "Object",
  config: '{"name":"List View Records","type":"Object","config":{"type":"Object","numberOfRows":50,"queryResponseFormat":{"type":"WHOLE_COLUMN","splitByType":"OBJECT_PER_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"objectApiName":"Account","advancedMode":{"type":"SOQL","inputs":{"queryString":"SELECT Id, Name, Industry, Description FROM Account WHERE Industry = \'Technology\' LIMIT 50"}}}}}'
})
```

---

## Pattern 9: Draft Agent Testing

**Goal:** Test an unpublished (draft) agent before deploying it.

### Step-by-Step Implementation

**Step 1: Discover Draft Agents and Their Topics**

```
get_agents({ includeDrafts: true })
// Returns agents including drafts; draft agents have activeVersion but no published version

get_draft_topics({
  config: '{"id": "0XxRM000000xxxxx", "name": "My Draft Agent"}'
})
// Returns topic definitions for the draft agent

get_draft_context_variables({
  config: '{"id": "0XxRM000000xxxxx", "name": "My Draft Agent"}'
})
// Returns context variables the draft agent expects
```

**Step 2: Set Up the Test Using setup_agent_test with isDraft**

```
setup_agent_test({
  agentId: "0XxRM000000xxxxx",
  agentVersion: "0XyRM000000xxxxx",
  utterances: [
    "Test utterance for draft agent",
    "Another test case"
  ],
  workbookName: "Draft Agent Tests",
  worksheetName: "Pre-Deploy Validation",
  evaluationTypes: ["COHERENCE", "TOPIC_ASSERTION"],
  expectedResponses: ["Expected topic 1", "Expected topic 2"],
  isDraft: true
})
```

**Step 3: Or Build Manually with isDraft Flag**

When adding an AgentTest column manually, set `isDraft: true` in the inner config:

```
add_column({
  worksheetId: "{worksheetId}",
  name: "Draft Agent Output",
  type: "AgentTest",
  config: '{"name":"Draft Agent Output","type":"AgentTest","config":{"type":"AgentTest","numberOfRows":50,"queryResponseFormat":{"type":"EACH_ROW"},"autoUpdate":true,"config":{"autoUpdate":true,"agentId":"0XxRM000000xxxxx","agentVersion":"0XyRM000000xxxxx","inputUtterance":{"columnId":"{utterance-col-id}","columnName":"Utterances","columnType":"Text"},"contextVariables":[],"isDraft":true,"enableSimulationMode":false}}}'
})
```

**Step 4: Monitor and Compare**

```
poll_worksheet_status({ worksheetId: "{worksheetId}" })

// Once complete, review results
get_worksheet_summary({ worksheetId: "{worksheetId}" })
```

---

## Best Practices

### Column Ordering

1. **Input columns first** -- Text, Object columns that provide data
2. **Processing columns next** -- Agent, AI, PromptTemplate, InvocableAction
3. **Extraction columns** -- Reference columns to pull specific fields
4. **Evaluation columns last** -- Depend on processing columns

### Reference Management

- Always use the exact column ID returned from the `add_column` response
- Use `fieldName` in ReferenceAttribute to extract specific fields from JSON
- For Object columns, `fieldName` specifies which SObject field to use

### Error Handling

- Check column status via `get_worksheet_summary` after processing
- Use `reprocess_column` to retry failed cells
- Use `get_worksheet_data` and inspect cell `statusMessage` for error details

### State Refresh

- After any mutation (add_column, paste_data, trigger_row_execution), call `get_worksheet_data` to get updated IDs and statuses
- Use `poll_worksheet_status` for long-running operations instead of manual polling
