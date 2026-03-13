---
name: salesforce-flow
description: Generate Salesforce Flows using the MCP tool execute_metadata_action. Use when the user asks to create, build, or generate a flow — including Screen, Autolaunched, Record-Triggered (before/after-save), Scheduled. Also trigger for flow-like requests such as "when a record is created", "trigger daily at", "send an email when", "update the field when", "automate", "workflow", or "flow XML/metadata". This is the only skill for Salesforce Flow generation.
---

## Goal

Generate Salesforce Flow metadata by running the required 3-step MCP pipeline (fetchGroundedObjectMetadata → flowElementSelection → flowElementGeneration) and return the flow XML.

## When to Use This Skill

Use this skill when you need to:
- Create any type of Flow (Screen, Autolaunched, Record-Triggered, Scheduled)
- Generate Flow metadata XML
- Automate business processes without code
- Build user-guided workflows or background automation
- Troubleshoot deployment errors related to Flows

## Specification

# Flow Metadata Specification

## Overview
Salesforce Flows are powerful automation tools that enable complex business process automation without code. Flows can collect and process data through interactive screens, execute logic and calculations, manipulate records, call external services, and trigger based on various events. Flow types include Screen Flows (user-guided), Autolaunched Flows (background processing), Record-Triggered Flows (database events) and Scheduled Flows (time-based).

## Purpose
- Automate complex business processes with declarative logic and branching
- Guide users through multi-step data collection and decision workflows via Screen Flows
- Perform CRUD operations on Salesforce records automatically
- Execute background processing and integrations via Autolaunched Flows
- React to record changes in real-time with Record-Triggered Flows
- Schedule recurring tasks and batch operations with Scheduled Flows
- Create reusable, maintainable automation that admins can modify without code

## Flow Generation Pipeline

**MANDATORY: You MUST follow this exact 3-step pipeline. No exceptions. No shortcuts. No skipping steps. Do NOT manually create flow metadata XML or attempt to generate flow metadata outside of this pipeline. Do NOT attempt to use any other tool, API, or method to generate flow metadata. This pipeline is the ONLY supported way to generate flows. Any deviation will produce invalid or broken metadata.**

### MCP Connection Details

**All 3 pipeline steps MUST be called using this MCP tool:**
- **MCP Tool Name:** `execute_metadata_action`
- **The `action` parameter** selects which pipeline step to run: `"fetchGroundedObjectMetadata"`, `"flowElementSelection"`, or `"flowElementGeneration"`


Flow generation is a **strict 3-step pipeline**. ALL steps must be called in order. Every step is required. **There is no alternative approach — this is the only way to generate flow metadata:**

### Step 1 (REQUIRED): Fetch Grounded Object Metadata (`fetchGroundedObjectMetadata`)
Fetches org schema metadata relevant to the flow generation request. This step is **mandatory** and must always be called first.

**Inputs (all required):**
- **userPrompt** (STRING, REQUIRED): The user's natural language request
- **inflightMetadata** (ARRAY, REQUIRED): Custom objects/fields from local sfdx project. Use empty array `[]` if none needed.

**Outputs:**
- **groundingMetadata** (STRING): Grounded object metadata for org schema relevant to the request, returned as a JSON string. **You must pass this directly to Step 2 — it is already a string and does not need to be serialized again.**

### Step 2 (REQUIRED): Flow Element Selection (`flowElementSelection`)
Selects flow elements (assignments, decisions, record ops, etc.) and their connections based on the user prompt and grounded metadata. This step is **mandatory** and must be called after Step 1.

**Inputs (all required):**
- **userPrompt** (STRING, REQUIRED): The user's natural language request (**must be the same value as Step 1**)
- **groundingMetadata** (STRING, REQUIRED): Org schema metadata (**must be the exact string returned from Step 1 output** — pass it directly, do NOT serialize it again)
- **operationId** (STRING, REQUIRED): Operation ID (use empty string `""` for first call)

**Outputs:**
- **operationId** (STRING): Operation ID. **You must pass this to Step 3.**
- **userOutput** (STRING): Reasoning for next steps. You can show this to the user.

### Step 3 (REQUIRED): Flow Element Generation (`flowElementGeneration`)
Generates flow metadata element by element. This step is **mandatory** and must be called after Step 2. **Must be called repeatedly in a loop until `isComplete` is `true`.**

**Inputs (all required):**
- **operationId** (STRING, REQUIRED): Operation ID **from Step 2 output**
- **requestSource** (STRING, REQUIRED): The source of the request. Use **`"A4V"`** to get flow metadata in XML format.

**Outputs:**
- **isComplete** (BOOLEAN): Indicates if the flow generation is complete. **You must check this value.**
- **result** (STRING): Result of the flow element generation. Contains the final flow metadata **only when `isComplete` is `true`**.

**MANDATORY: Loop until complete. NEVER pause or ask the user to confirm continuation.**
- A flow can have **any number of elements** (10, 15, or more). Each call generates one element at a time, so you may need **many** iterations. This is expected and normal.
- Call `flowElementGeneration` with the `operationId` from Step 2 and `requestSource` (use `"A4V"` for XML output, empty string or other value for JSON).
- Check the `isComplete` output and the `result` field after each call.
- If `isComplete` is `false` **and no errors are returned**, you **MUST** call `flowElementGeneration` again with the **same `operationId`** from Step 2. **Do NOT ask the user if they want to continue. Do NOT pause. Do NOT summarize progress mid-loop. Just keep calling.**
- **Do NOT stop** until `isComplete` is `true` **or** the invocable action returns errors. There is **no maximum** number of iterations — keep going regardless of how many calls it takes.
- When `isComplete` is `true`, extract the flow metadata from the `result` field.
- If errors are returned, stop the loop and surface the error to the user.

**STRICT CONSTRAINTS (CRITICAL):**
- DO NOT modify the content, values, or child nodes inside any block.
- DO NOT add new nodes, tags, attributes, or text (do not add missing labels, X/Y coordinates, etc.).
- DO NOT remove any existing nodes.

## inflightMetadata Format
**DATA TYPE: ARRAY (not string)**

**STRICT NAMING CONVENTION - MUST FOLLOW EXACTLY:**
| Property | Correct Name | Do NOT Use |
|----------|-------------|---------------|
| Object API name | `apiName` | `objectApiName`, `name`, `objectName` |
| Field API name | `apiName` | `fieldApiName`, `name`, `fieldName` |
| Field type | `type` | `fieldType`, `dataType` |
| Lookup target | `referenceTo` | `relatedTo`, `lookupTo`, `reference` |

When custom objects are needed (sample format showing multiple field data types):
```json
[
  {
    "type": "CustomObject",
    "apiName": "CustomerRequest__c",
    "label": "Customer Request",
    "fields": [
      {
        "apiName": "Status__c",
        "type": "Picklist",
        "label": "Status",
        "values": ["New", "In Progress", "Completed"]
      },
      {
        "apiName": "Priority__c",
        "type": "Number",
        "label": "Priority"
      },
      {
        "apiName": "AssignedTo__c",
        "type": "Lookup",
        "label": "Assigned To",
        "referenceTo": "User"
      },
      {
        "apiName": "Description__c",
        "type": "Textarea",
        "label": "Description"
      },
      {
        "apiName": "Email__c",
        "type": "Email",
        "label": "Contact Email"
      },
      {
        "apiName": "DueDate__c",
        "type": "Date",
        "label": "Due Date"
      },
      {
        "apiName": "IsUrgent__c",
        "type": "Boolean",
        "label": "Is Urgent"
      },
      {
        "apiName": "Amount__c",
        "type": "Currency",
        "label": "Amount"
      }
    ],
    "relationships": []
  }
]
```

**Supported field types**: Text, Textarea, Number, Picklist, Lookup, Email, Phone, URL, Date, Datetime, Boolean, Checkbox, Currency, Percent

When no custom objects needed:
```json
[]
```

### MANDATORY Decision Logic for inflightMetadata (DATA TYPE: ARRAY)

1. **REQUIRED - First**: Scan the local sfdx project for custom objects and fields that are relevant to the user's flow request.
2. **If relevant custom objects ARE found**: You MUST extract and pass them as an array of structured objects (see format above)
3. **If NO relevant custom objects found**: You MUST pass an empty array `[]` (NOT the string `"[]"`)
4. **NEVER**: Pass text descriptions, instructions, or string representations in inflightMetadata
5. **MANDATORY**: The data type MUST be ARRAY, not STRING

**Instructions for Vibes when custom objects ARE relevant:**
- Extract the object metadata and map to JSON properties:
    - `apiName`: The object's API name (with `__c` suffix for custom objects)
    - `label`: The object's display label
    - `type`: Set to `"CustomObject"`
    - `fields`: Array of field objects, each containing:
        - `apiName`: The field's API name (with `__c` suffix for custom fields)
        - `type`: The field type (Text, Number, Picklist, Lookup, etc.)
        - `label`: The field's display label
        - `values`: (Picklist only) Array of picklist values
        - `referenceTo`: (Lookup only) The target object API name
- Include only objects and fields that are relevant to the flow being generated

## 🎯 Mandatory Enhancement Rules
- **userPrompt**: REQUIRED.
    - If the user requests a **single flow**: use the user's prompt as-is.
    - If the user requests **multiple flows**: you MUST **split** the request and write a **separate, focused `userPrompt` for each individual flow**. Each `userPrompt` must describe only ONE flow. Do NOT pass the entire multi-flow request as a single `userPrompt`. See the multiple flows section below for examples.
- **inflightMetadata**: REQUIRED. Always use ARRAY data type.
    - MUST use `[]` (empty array) when no custom objects needed
    - MUST use structured array of objects when custom objects are relevant
    - NEVER use string `"[]"` - this is incorrect
    - NEVER use text descriptions - only structured object metadata

### MANDATORY: Multiple Flows = Multiple Separate Pipelines

**FIRST: Before calling any pipeline step, check if the user's request contains multiple flows. If it does, you MUST split it into separate single-flow prompts. Each flow gets its own 3-step pipeline with its own `userPrompt` that describes ONLY that one flow.**

**NEVER pass a multi-flow request as a single `userPrompt` field. NEVER club multiple flow descriptions into one `userPrompt`.**

When the user requests multiple flows (e.g., "Create flows for my app: 1) ... 2) ... 3) ..."), you MUST:
1. **Split** the request into separate individual flow descriptions.
2. **Run a separate 3-step pipeline for each flow**, using a `userPrompt` that describes ONLY that one flow.
3. **Execute ALL pipelines SEQUENTIALLY** — one after another, NEVER in parallel. Do NOT stop after the first flow. Do NOT wait for the user to ask you to continue. Do NOT summarize and stop. Keep going until every requested flow has been fully generated.

**WRONG - Multiple flows clubbed into one userPrompt:**
```json
{
  "userPrompt": "Create flows for the app: 1) Record-Triggered Flow on ResourceAllocation__c to update Resource__c. 2) Screen Flow to allocate resources. 3) Record-Triggered Flow on Supply__c to auto-flag Low_Stock__c.",
  ...
}
```

**CORRECT - Separate call for EACH flow:**

**Flow 1 - Step 1 (fetchGroundedObjectMetadata):**
```json
{
  "userPrompt": "Create a Screen Flow named Tenant_Onboarding that captures tenant details, selects a Unit__c with Status__c = 'Vacant', creates Lease__c...",
  "inflightMetadata": [...]
}
```
Then call Step 2 (`flowElementSelection`) with the `groundingMetadata` from Step 1, then Step 3 (`flowElementGeneration`) with the `operationId` from Step 2.

**Flow 2 - Step 1 (fetchGroundedObjectMetadata):**
```json
{
  "userPrompt": "Create an Autolaunched Flow named Generate_Onboarding_Checklist that given a Lease__c Id input, queries OnboardingTask__c...",
  "inflightMetadata": [...]
}
```
Then call Step 2 and Step 3 for this flow.

**Flow 3 - Step 1 (fetchGroundedObjectMetadata):**
```json
{
  "userPrompt": "Create a Record-Triggered Flow named Sync_Unit_On_Lease_Changes that on insert and update of Lease__c...",
  "inflightMetadata": [...]
}
```
Then call Step 2 and Step 3 for this flow.

**Mandatory Rules:**
- If there are N flows to generate, there MUST be N separate 3-step pipelines and ALL N pipelines MUST be executed. No exceptions. Do NOT stop after generating only one flow.
- **You MUST fully complete the current flow's 3-step pipeline (including looping Step 3 until `isComplete` is `true` or errors are returned) BEFORE starting the next flow's pipeline.** Do NOT interleave or parallelize pipelines across flows. **Everything is SEQUENTIAL — NEVER parallel.**
- After completing a flow's pipeline, **immediately start the next flow's pipeline**. Do NOT pause, summarize, or wait for user confirmation between flows.
- For each flow, you MUST scan the local sfdx project to populate `inflightMetadata` with custom objects/fields **specific to that flow prompt**.
- Each flow pipeline MUST have its own `inflightMetadata` containing only the objects/fields relevant to that particular flow.

## Example Tool Calls

**Example 1: Standard objects only (no custom objects)**

**Step 1 - fetchGroundedObjectMetadata:**
```json
{
  "userPrompt": "Create a scheduled-triggered Flow named Daily_Good_Morning that runs daily at 6:00 AM and sends an email to the running user saying good morning.",
  "inflightMetadata": []
}
```

**Step 2 - flowElementSelection:**
```json
{
  "userPrompt": "Create a scheduled-triggered Flow named Daily_Good_Morning that runs daily at 6:00 AM and sends an email to the running user saying good morning.",
  "groundingMetadata": "<groundingMetadata string from Step 1 — pass directly, do not serialize again>",
  "operationId": ""
}
```

**Step 3 - flowElementGeneration (call in a loop):**
```json
{
  "operationId": "<operationId from Step 2>",
  "requestSource": "A4V"
}
```
Call repeatedly with the same `operationId` until `isComplete` is `true` or errors are returned. A flow can have any number of elements, so expect multiple iterations. When `isComplete` is `true`, extract the flow metadata from the `result` field. Use `"requestSource": "A4V"` to get flow metadata in XML format.

**Example 2: With custom objects from local sfdx project**

**Step 1 - fetchGroundedObjectMetadata:**
```json
{
  "userPrompt": "Create a flow that updates the status of a Customer Request when it's assigned",
  "inflightMetadata": [
    {
      "type": "CustomObject",
      "apiName": "CustomerRequest__c",
      "label": "Customer Request",
      "fields": [
        {
          "apiName": "Status__c",
          "type": "Picklist",
          "label": "Status",
          "values": ["New", "In Progress", "Completed"]
        },
        {
          "apiName": "AssignedTo__c",
          "type": "Lookup",
          "label": "Assigned To",
          "referenceTo": "User"
        }
      ],
      "relationships": []
    }
  ]
}
```

**Step 2 - flowElementSelection:**
```json
{
  "userPrompt": "Create a flow that updates the status of a Customer Request when it's assigned",
  "groundingMetadata": "<groundingMetadata string from Step 1 — pass directly, do not serialize again>",
  "operationId": ""
}
```

**Step 3 - flowElementGeneration (call in a loop):**
```json
{
  "operationId": "<operationId from Step 2>",
  "requestSource": "A4V"
}
```
Call repeatedly with the same `operationId` until `isComplete` is `true` or errors are returned. A flow can have any number of elements, so expect multiple iterations. When `isComplete` is `true`, extract the flow metadata from the `result` field. Use `"requestSource": "A4V"` to get flow metadata in XML format.

## Mandatory Best Practices
- **ALWAYS** follow the 3-step pipeline: fetchGroundedObjectMetadata → flowElementSelection → flowElementGeneration. This is the ONLY way to generate flow metadata. There are no alternatives.
- Do NOT manually create flow metadata XML, JSON, or any other format outside of this pipeline.
- Do NOT attempt to "optimize" by skipping steps or combining steps. Each step is atomic and required.
- **NEVER** skip any step in the pipeline. All 3 steps are required.
- **NEVER** try to generate flow metadata without calling all 3 steps.
- **NEVER** deviate from this pipeline under any circumstance — even if you think you know the flow structure.
- For single flow requests: you MUST use the user prompt as `userPrompt`.
- For multiple flow requests: you MUST run a separate 3-step pipeline for each flow **SEQUENTIALLY (one after another, NEVER in parallel)**, and you MUST execute ALL of them — do NOT stop after the first flow.
- You MUST put flow requirements in `userPrompt`, NOT in `inflightMetadata`.
- `inflightMetadata` is ONLY for custom object/field metadata from local project (see above). No exceptions.
- Step 3 MUST be called in a loop with the same `operationId` from Step 2 until `isComplete` is `true` or errors are returned. A flow can have any number of elements — do NOT stop early, do NOT pause to ask the user if they want to continue, regardless of how many iterations it takes.
- You MUST only extract the flow metadata from the `result` field when `isComplete` is `true`.

## CRITICAL Verification Checklist (MUST VERIFY BEFORE AND AFTER EVERY FLOW GENERATION)

**Failure to follow this checklist exactly will result in broken or missing flow metadata.**

- [ ] **Pipeline**: ALL 3 steps are called in strict order (fetchGroundedObjectMetadata → flowElementSelection → flowElementGeneration). No step is skipped.
- [ ] **No manual metadata**: Flow metadata is NOT manually created, modified, or generated outside of this pipeline by any means
- [ ] **No deviation**: No alternative tools, APIs, or methods were used instead of or alongside this pipeline
- [ ] **userPrompt** contains a **single** flow prompt. If user requested multiple flows, the request was split and each pipeline received a separate `userPrompt` describing only one flow
- [ ] **userPrompt** is passed consistently to both Step 1 and Step 2 (same value)
- [ ] **inflightMetadata** is ARRAY data type (NOT string)
- [ ] **inflightMetadata** is `[]` when no custom objects needed
- [ ] **inflightMetadata** contains structured objects extracted by scanning the local sfdx project for relevant custom objects/fields
- [ ] **inflightMetadata** does NOT contain `"[]"` (string) - must be `[]` (array)
- [ ] **inflightMetadata** does NOT contain text descriptions or instructions
- [ ] **groundingMetadata** from Step 1 output is passed directly to Step 2 input (it is already a string — do NOT serialize it again)
- [ ] **operationId** from Step 2 output is passed to Step 3 input
- [ ] **requestSource** should be set to `"A4V"` always
- [ ] **Step 3** is called in a loop with the same `operationId` from Step 2 until `isComplete` is `true` or errors are returned — **no pausing, no asking the user to continue, no matter how many iterations**
- [ ] **Multi-flow**: Each flow's full pipeline is completed before starting the next flow's pipeline (no interleaving)
- [ ] **result** field is used to extract the XML flow metadata only when `isComplete` is `true`
- [ ] **No additions to XML**: NO elements, attributes, or properties were added that were not present in the original pipeline output. Nothing was inserted (no `<label>`, `<description>`, or any other node). The final XML must be identical to what the pipeline returned.
