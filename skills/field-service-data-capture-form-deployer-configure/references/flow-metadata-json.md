# Flow Metadata JSON — Data Capture Flow

A Data Capture Flow is a Salesforce Flow with `processType=DataCaptureFlow`. It is created and updated through the **Tooling API `Flow` sObject**, whose `Metadata` field is a JSON object — the same shape you get back from `GET /services/data/vXX.0/tooling/sobjects/Flow/{id}`. There is **no `.flow-meta.xml`, no zip, and no SFDX project** — the agent assembles this JSON inline and POSTs it.

The shape below is the JSON transliteration of the Metadata blob retrieved from real flows in a live Field Service org (`Data_Capture_Asset_Inspection`, `Inventory_Transfer`) and verified against that org's `Flow` describe.

## The deploy call

```http
POST /services/data/vXX.0/tooling/sobjects/Flow
{
  "FullName": "<FlowApiName>",
  "Metadata": { ...the object below... }
}
```

- `FullName` is the Flow API name (matches `^[A-Z][A-Za-z0-9_]*$`). `FullName` is set-on-create only.
- A 201 with `success: true` returns the new Flow version id.
- To **activate on create**, set `Metadata.status: "Active"`. Default `"Draft"` so the user reviews in Flow Builder first — activation is via `Flow.Metadata.status`, not a separate `FlowDefinition` write (`FlowDefinition.ActiveVersionId` is not directly writable).
- To **update** an existing version, `PATCH /services/data/vXX.0/tooling/sobjects/Flow/{id}` with `{"Metadata": {...full metadata...}}` (the editor skill's redeploy path).

## JSON ↔ XML mapping rule

The Metadata JSON is a mechanical transliteration of the Flow XML:

- Each XML element becomes a JSON key. `<label>X</label>` → `"label": "X"`.
- **Repeated** elements become a JSON **array**: multiple `<screens>` → `"screens": [ {...}, {...} ]`; multiple `<choiceReferences>` → `"choiceReferences": ["A","B"]`.
- Typed value wrappers keep their wrapper key: `<value><stringValue>X</stringValue></value>` → `"value": {"stringValue": "X"}`; `<booleanValue>true</booleanValue>` → `{"booleanValue": true}`; `<numberValue>1.0</numberValue>` → `{"numberValue": 1.0}`; `<elementReference>Foo</elementReference>` → `{"elementReference": "Foo"}`.
- Booleans and numbers are real JSON scalars, not strings.

## Minimum-deployable shape

```json
{
  "processType": "DataCaptureFlow",
  "environments": ["Offline"],
  "areMetricsLoggedToDataCloud": false,
  "label": "HVAC Compressor Inspection",
  "interviewLabel": "HVAC Compressor Inspection {!$Flow.CurrentDateTime}",
  "description": "Generated from spec: HVAC Compressor Inspection",
  "status": "Draft",

  "processMetadataValues": [
    { "name": "BuilderType", "value": { "stringValue": "LightningFlowBuilder" } },
    { "name": "CanvasMode",  "value": { "stringValue": "AUTO_LAYOUT_CANVAS" } }
  ],

  "choices": [
    { "name": "Good", "choiceText": "Good", "dataType": "String", "value": { "stringValue": "Good" } }
  ],

  "start": { "locationX": 0, "locationY": 0, "connector": { "targetReference": "Screen_HeaderInformation" } },

  "screens": [
    {
      "name": "Screen_HeaderInformation",
      "label": "Header Information",
      "locationX": 0, "locationY": 0,
      "allowBack": true, "allowFinish": true, "allowPause": true,
      "showFooter": true, "showHeader": true,
      "connector": { "targetReference": "Screen_OperatingParameters" },
      "fields": [

        {
          "name": "jobName",
          "extensionName": "runtime_service_fieldservice:dcTextInput",
          "fieldType": "ComponentInstance",
          "inputParameters": [
            { "name": "label",    "value": { "stringValue": "Job Name" } }
          ],
          "inputsOnNextNavToAssocScrn": "UseStoredValues",
          "isRequired": true,
          "storeOutputAutomatically": true,
          "styleProperties": {
            "verticalAlignment": { "stringValue": "top" },
            "width": { "stringValue": "12" }
          }
        },

        {
          "name": "Quantity",
          "extensionName": "runtime_service_fieldservice:dcCounter",
          "fieldType": "ComponentInstance",
          "inputParameters": [
            { "name": "label", "value": { "stringValue": "Quantity" } },
            { "name": "min",   "value": { "numberValue": 1.0 } },
            { "name": "value", "value": { "numberValue": 1.0 } }
          ]
        },

        {
          "name": "To",
          "choiceReferences": ["Truck", "Work_Order"],
          "extensionName": "runtime_service_fieldservice:dcRbGroup",
          "fieldText": "To",
          "fieldType": "ComponentChoice"
        },

        {
          "name": "issuesIdentified",
          "choiceReferences": ["Corrosion", "Wear", "Leakage"],
          "extensionName": "runtime_service_fieldservice:dcCbGroup",
          "fieldText": "Issues Identified",
          "fieldType": "ComponentMultiChoice"
        },

        {
          "name": "Work_Order_Number",
          "extensionName": "runtime_service_fieldservice:dcTextInput",
          "fieldType": "ComponentInstance",
          "inputParameters": [
            { "name": "label",    "value": { "stringValue": "Work Order Number" } }
          ],
          "isRequired": true,
          "visibilityRule": {
            "conditionLogic": "and",
            "conditions": [
              { "leftValueReference": "Work_Order", "operator": "EqualTo", "rightValue": { "booleanValue": true } }
            ]
          }
        },

        {
          "name": "Part",
          "fieldType": "Repeater",
          "fields": [
            { "name": "Quantity",    "extensionName": "runtime_service_fieldservice:dcCounter",   "fieldType": "ComponentInstance" },
            { "name": "Part_Number", "extensionName": "runtime_service_fieldservice:dcTextInput", "fieldType": "ComponentInstance" }
          ],
          "isRequired": false,
          "styleProperties": { "verticalAlignment": { "stringValue": "top" }, "width": { "stringValue": "12" } }
        },

        {
          "name": "safetyInstructions",
          "fieldText": "<p>All personnel must wear PPE.</p>",
          "fieldType": "DisplayText"
        }
      ]
    }
  ],

  "decisions": [
    {
      "name": "Transfer_Location_Decision",
      "label": "Transfer Location Decision",
      "locationX": 0, "locationY": 0,
      "defaultConnectorLabel": "Error",
      "rules": [
        {
          "name": "Truck_Decision",
          "conditionLogic": "and",
          "conditions": [
            { "leftValueReference": "To.selectedChoiceValues", "operator": "EqualTo", "rightValue": { "elementReference": "Truck" } }
          ],
          "connector": { "targetReference": "Get_Truck" },
          "label": "Truck"
        }
      ]
    }
  ],

  "recordLookups": [
    {
      "name": "Get_Truck",
      "label": "Get Truck",
      "locationX": 0, "locationY": 0,
      "assignNullValuesIfNoRecordsFound": false,
      "connector": { "targetReference": "Part_Transfers" },
      "filterLogic": "and",
      "filters": [
        { "field": "Service_Resource__c", "operator": "EqualTo", "value": { "elementReference": "$User.Id" } }
      ],
      "object": "Location",
      "outputAssignments": [
        { "assignToReference": "Transfer_Destination", "field": "Id" }
      ]
    }
  ],

  "loops": [
    {
      "name": "Part_Transfers",
      "label": "Part Transfers",
      "locationX": 0, "locationY": 0,
      "collectionReference": "Part.AddedItems",
      "iterationOrder": "Asc",
      "nextValueConnector": { "targetReference": "Transfer_Part" }
    }
  ],

  "recordCreates": [
    {
      "name": "Transfer_Part",
      "label": "Transfer Part",
      "locationX": 0, "locationY": 0,
      "connector": { "targetReference": "Part_Transfers" },
      "inputAssignments": [
        { "field": "Product2Id", "value": { "elementReference": "Part_Transfers.Part_Number.value" } }
      ],
      "object": "ProductTransfer",
      "storeOutputAutomatically": true
    }
  ],

  "variables": [
    { "name": "parentObjectType",   "dataType": "String", "isCollection": false, "isInput": true,  "isOutput": false },
    { "name": "parentRecordId",     "dataType": "String", "isCollection": false, "isInput": true,  "isOutput": false },
    { "name": "recordId",           "dataType": "String", "isCollection": false, "isInput": true,  "isOutput": false },
    { "name": "Transfer_Destination","dataType": "String", "isCollection": false, "isInput": false, "isOutput": false }
  ]
}
```

## Field-rendering strategies

| Strategy | Triggered by | Key JSON differences |
|----------|--------------|----------------------|
| `ComponentInstance` | most types: TextInput, Email, Phone, Numeric, Counter, Date, DateTime, Checkbox, Toggle, LongText | `"fieldType": "ComponentInstance"`, label via `inputParameters` |
| `ComponentChoice` | Picklist, Radio (`dcRbGroup`) | `"fieldType": "ComponentChoice"`, label via `fieldText`, options via `choiceReferences` array |
| `ComponentMultiChoice` | CheckboxGroup | `"fieldType": "ComponentMultiChoice"`, label via `fieldText`, options via `choiceReferences` array |
| native `DisplayText` | DisplayText | `"fieldType": "DisplayText"`, body via `fieldText` (HTML), no `extensionName` |
| native `Repeater` | Repeater | `"fieldType": "Repeater"`, child fields via nested `fields` array, no `extensionName` |

## Requiredness — `isRequired` only, never a `required` inputParameter

Mark a mandatory field with the field-level `"isRequired": true` key **only**. Do **not** add `{ "name": "required", ... }` to `inputParameters` — `dcName`, `dcSignature`, and other Field Service components reject it, and the deploy fails with `We can't find this input attribute: 'required'`. This is the single most common deploy error; the examples above intentionally carry `isRequired` with no `required` inputParameter.

## Connector pattern

- `start.connector` points to screen #1.
- Each screen — *except* the last — has a `connector` to the next screen.
- The **last screen** connects to `postScreen` (decision/lookup/loop/create) if present, otherwise omits `connector`.
- All screens set `"allowFinish": true`.

## Things deliberately not generated

- No formulas, assignments, or text templates.
- No nested loops or decisions inside loops.
- No subflows.
- No `dcLookup` without an `objectApiName` (specs missing `lookupObject` fall back to a labeled TextInput placeholder).
- No `dcFileView` without a `fileName` (specs missing `fileName` fall back to a labeled TextInput placeholder).
- No visual polish HTML (banners, progress bars, callouts).
