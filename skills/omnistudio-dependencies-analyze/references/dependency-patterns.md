<!-- Parent: omnistudio-dependencies-analyze/SKILL.md -->

# OmniStudio Dependency Patterns

## Overview

OmniStudio components form a directed graph where each component type can reference others. Dependencies are not stored in lookup fields — they are embedded in JSON configuration fields (`PropertySetConfig`, FlexCard `DataSourceConfig`, `InputObjectName`/`OutputObjectName`). Extracting dependencies requires parsing these JSON structures.

---

## Dependency Direction Summary

```text
OmniScript ──→ Integration Procedure (via IP Action element)
OmniScript ──→ Data Mapper (via DataRaptor Action element)
OmniScript ──→ OmniScript (via embedded OmniScript element)
OmniScript ──→ Apex Class (via Remote Action element)
OmniScript ──→ LWC (via Custom Lightning Web Component element)
OmniScript ──→ HTTP Endpoint (via HTTP Action element)

Integration Procedure ──→ Data Mapper (via DataRaptor Action element)
Integration Procedure ──→ Apex Class (via Remote Action element)
Integration Procedure ──→ HTTP Endpoint (via HTTP Action element)
Integration Procedure ──→ Integration Procedure (via nested IP Action element)
Integration Procedure ──→ OmniScript (via OmniScript Action element — uncommon)

FlexCard ──→ Integration Procedure (via data source configuration)
FlexCard ──→ Apex Class (via Apex data source)
FlexCard ──→ FlexCard (via child card reference)
FlexCard ──→ OmniScript (via action configuration — launches OS)

Data Mapper ──→ Salesforce Object (via InputObjectName — read)
Data Mapper ──→ Salesforce Object (via OutputObjectName — write)
```

---

## OmniScript Dependencies

### Element Types and Their Dependency Targets

OmniScript elements are stored as `OmniProcessElement` records (Core) or `Element__c` records (Vlocity). Each element has a `PropertySetConfig` / `PropertySet__c` JSON field containing the configuration. In Core, `PropertySetConfig` is a **flat** JSON object of the element's properties; the element type is the separate `Type` field on `OmniProcessElement` (`<type>` in `.os-meta.xml` / `.oip-meta.xml`), not a key inside the JSON.

#### DataRaptor Extract / Transform / Post Action

Calls a Data Mapper (`DataRaptor Extract Action` = Extract, `DataRaptor Transform Action` = Transform, `DataRaptor Post Action` = Load).

**PropertySetConfig structure** (Type = `DataRaptor Transform Action`):
```json
{
  "bundle": "AccountTransform",
  "ignoreCache": false,
  "sendJSONPath": "",
  "responseJSONPath": ""
}
```

**Extraction rule**: `bundle` → resolves to an `OmniDataTransform` record by `Name`.

#### DataRaptor Turbo Action

High-performance variant of DataRaptor Transform Action. Same JSON structure, same extraction rule.

**PropertySetConfig structure** (Type = `DataRaptor Turbo Action`):
```json
{
  "bundle": "AccountTurboExtract"
}
```

#### Integration Procedure Action

Calls an Integration Procedure.

**PropertySetConfig structure**:
```json
{
  "integrationProcedureKey": "TypeName_SubTypeName",
  "remoteOptions": { "chainable": false, "useFuture": false }
}
```

**Extraction rule**: `integrationProcedureKey` → resolves to an `OmniProcess` record where `Type_SubType` matches and `IsIntegrationProcedure = true`.

#### OmniScript Action (Embedded OmniScript)

Embeds or launches another OmniScript.

**PropertySetConfig structure**:
```json
{
  "Type": "ChildScriptType",
  "Sub Type": "ChildScriptSubType",
  "Language": "English"
}
```

**Extraction rule**: `Type` + `["Sub Type"]` + `Language` → resolves to an `OmniProcess` where `IsIntegrationProcedure = false` and fields match. The same reference is also on the element record itself as `EmbeddedOmniScriptKey` (`<embeddedOmniScriptKey>ChildScriptType|ChildScriptSubType|English</embeddedOmniScriptKey>` in source).

#### Remote Action

Calls an Apex class method.

**PropertySetConfig structure**:
```json
{
  "remoteClass": "MyApexClassName",
  "remoteMethod": "myMethodName",
  "remoteTimeout": 30000
}
```

**Extraction rule**: `remoteClass` → Apex class name. `remoteMethod` → method name. Dependency is `remoteClass.remoteMethod`.

#### HTTP Action

Calls an external HTTP endpoint.

**PropertySetConfig structure**:
```json
{
  "httpUrl": "{externalEndpointUrl}",
  "httpMethod": "POST",
  "namedCredential": "MyNamedCredential"
}
```

**Extraction rule**: `httpUrl` or `namedCredential` → external dependency. If `namedCredential` is present, it references a Named Credential record.

#### Custom Lightning Web Component

Embeds an LWC inside the OmniScript.

**PropertySetConfig structure**:
```json
{
  "lwcName": "myCustomComponent",
  "bStandalone": false,
  "customAttributes": []
}
```

**Extraction rule**: `lwcName` → LWC component reference (camelCase bundle name, e.g. `cfMyCard` for a FlexCard-generated LWC).

#### DocuSign Envelope Action

Triggers a DocuSign envelope.

**PropertySetConfig structure**:
```json
{
  "docuSignTemplateId": "template-uuid"
}
```

**Extraction rule**: `docuSignTemplateId` → DocuSign template (external dependency).

---

## Integration Procedure Dependencies

Integration Procedures use the same element types as OmniScripts but are filtered by `IsIntegrationProcedure = true` (Core) or `IsIntegrationProcedure__c = true` (Vlocity).

### Element Types Available in IPs

| Element Type | Available in IP | Dependency Target |
|-------------|----------------|-------------------|
| DataRaptor Extract Action | Yes | Data Mapper |
| DataRaptor Transform Action | Yes | Data Mapper |
| DataRaptor Post Action | Yes | Data Mapper (Load) |
| DataRaptor Turbo Action | Yes | Data Mapper |
| Remote Action | Yes | Apex Class |
| HTTP Action | Yes | External endpoint |
| Integration Procedure Action | Yes (nested) | Another IP |
| Matrix Action | Yes | Calculation Matrix |
| Set Values | Yes | None (internal) |
| Conditional Block | Yes | None (internal) |
| Loop Block | Yes | None (internal) |
| Response Action | Yes | None (internal) |
| List Merge Action | Yes | None (internal) |
| Delete Action | Yes | sObject (via `deleteSObject[].Type`) |

### Nested IP Pattern

An Integration Procedure can call another Integration Procedure, creating a chain:

```text
IP: OrderValidation
  └── IP Action → IP: CustomerLookup
       └── DR Action → DM: CustomerExtract
  └── IP Action → IP: InventoryCheck
       └── HTTP Action → External inventory API
  └── DR Action → DM: OrderTransform
```

---

## FlexCard Dependencies

In Core, FlexCards (`OmniUiCard`) split their configuration across two JSON fields: `DataSourceConfig` (data source) and `PropertySetConfig` (states, elements, actions). There is NO `Definition` field on `OmniUiCard` (`Definition__c` exists only on Vlocity `VlocityUITemplate__c`).

### Data Source Parsing

`DataSourceConfig` contains a single `dataSource` object (not an array):

```json
{
  "dataSource": {
    "type": "IntegrationProcedures",
    "value": {
      "dsDelay": "",
      "ipMethod": "Type_SubType",
      "vlocityAsync": false,
      "inputMap": { "AccountId": "{recordId}" },
      "jsonMap": "{\"recordId\":\"{recordId}\"}"
    },
    "orderBy": { "name": "", "isReverse": "" },
    "contextVariables": []
  }
}
```

**Extraction rules by data source type**:

| Data Source Type | JSON Path | Dependency Target |
|-----------------|-----------|-------------------|
| `IntegrationProcedures` (plural) | `dataSource.value.ipMethod` | Integration Procedure (Type_SubType key) |
| `ApexRemote` | `dataSource.value.className` | Apex Class |
| `DataRaptor` | `dataSource.value.bundle` | Data Mapper |
| `Custom` | `dataSource.value.body` | None (static JSON) |

### Child Card References

FlexCards can embed other FlexCards. In `PropertySetConfig`, a child card is an element with `"element": "childCardPreview"`:

```json
{
  "name": "FlexCard",
  "element": "childCardPreview",
  "property": {
    "cardName": "ContactListCard",
    "recordId": "{recordId}",
    "cardNode": "{record}"
  }
}
```

**Extraction rule**: `element === 'childCardPreview'` → `property.cardName` → resolves to another `OmniUiCard` by Name. Flyout actions with `flyoutType: "childCard"` also reference a child card via `stateAction.flyoutLwc` / `stateAction.cardName`.

### Action References

FlexCard actions are `"element": "action"` entries in `PropertySetConfig`; each has a `property.actionList[].stateAction`. Actions can launch OmniScripts in a flyout:

```json
{
  "stateAction": {
    "type": "Flyout",
    "flyoutType": "OmniScripts",
    "osName": "editAccount/step1/English",
    "openFlyoutIn": "Modal"
  }
}
```

**Extraction rule**: `stateAction.type === 'Flyout'` and `flyoutType === 'OmniScripts'` → `osName` (`Type/SubType/Language`) → resolves to an OmniScript.

---

## Data Mapper Dependencies

Data Mappers (DataRaptors) reference Salesforce objects through their items.

### Object References via Items

Each `OmniDataTransformItem` (Core) or `DRMapItem__c` (Vlocity) record contains:

| Field | Purpose | Dependency Type |
|-------|---------|----------------|
| `InputObjectName` / `InterfaceObject__c` | Source sObject for reads | sObject (read access) |
| `OutputObjectName` / `TargetFieldObjectType__c` | Target sObject for writes | sObject (write access) |
| `InputFieldName` / `InterfaceFieldAPIName__c` | Source field | Field-level dependency |
| `OutputFieldName` / `TargetFieldAPIName__c` | Target field | Field-level dependency |

### Extract Type Data Mapper Example

```text
DM: AccountExtract (Type: Extract)
├── Item 1: InputObjectName = "Account"
│   InputFieldName = "Name"
│   OutputFieldName = "AccountName"
├── Item 2: InputObjectName = "Account"
│   InputFieldName = "Industry"
│   OutputFieldName = "AccountIndustry"
└── Item 3: InputObjectName = "Contact"
    InputFieldName = "Email"
    OutputFieldName = "PrimaryEmail"

Dependencies: Account (read), Contact (read)
```

### Load Type Data Mapper Example

```text
DM: OrderCreate (Type: Load)
├── Item 1: OutputObjectName = "Order"
│   InputFieldName = "OrderData.accountId"
│   OutputFieldName = "AccountId"
└── Item 2: OutputObjectName = "OrderItem"
    InputFieldName = "OrderData.lineItems[].productId"
    OutputFieldName = "Product2Id"

Dependencies: Order (write), OrderItem (write)
```

### Transform Type Data Mapper

Transform type Data Mappers do not reference Salesforce objects directly — they map between data structures. They have no sObject dependencies but may participate in a chain:

```text
OmniScript → DR Extract (reads Account) → DR Transform (reshapes data) → DR Load (writes CustomObj__c)
```

---

## Circular Dependency Detection

### Why Circular Dependencies Occur

Circular references happen when component A depends on component B, which directly or transitively depends back on component A. Common scenarios:

1. **OmniScript ↔ IP**: OmniScript calls IP via IP Action, IP calls back to OmniScript via OmniScript Action
2. **IP ↔ IP**: IP A calls IP B via nested IP Action, IP B calls IP A
3. **FlexCard → IP → OmniScript → FlexCard**: FlexCard sources data from IP, IP triggers OmniScript, OmniScript launches FlexCard

### Detection Algorithm

```javascript
function detectCircularDependencies(graph):
    cycles = []
    for each node N in graph:
        visited = empty set
        path = empty list
        dfs(N, visited, path, graph, cycles)
    return cycles

function dfs(node, visited, path, graph, cycles):
    if node is in path:
        // Circular reference found
        cycleStart = index of node in path
        cycle = path[cycleStart:] + [node]
        cycles.append(cycle)
        return
    if node is in visited:
        return
    visited.add(node)
    path.append(node)
    for each neighbor of node in graph:
        dfs(neighbor, visited, path, graph, cycles)
    path.removeLast()
```

### Reporting Circular References

When a cycle is detected, report it clearly:

```text
CIRCULAR DEPENDENCY DETECTED:
  OS:editAccount → IP:validateAccount → OS:editAccount

Components in cycle:
  1. OmniScript "editAccount" (IP Action → validateAccount)
  2. Integration Procedure "validateAccount" (OmniScript Action → editAccount)

Risk: Runtime infinite loop if not guarded by conditional logic.
Recommendation: Review whether the back-reference is intentional and has
a termination condition.
```

---

## Dependency Graph Construction

### Step-by-Step Process

```text
1. DETECT namespace (see namespace-guide.md)

2. QUERY all container objects:
   - OmniProcess (OmniScripts + IPs)
   - OmniUiCard (FlexCards)
   - OmniDataTransform (Data Mappers)

3. QUERY all element objects:
   - OmniProcessElement (for each OmniProcess)
   - OmniDataTransformItem (for each OmniDataTransform)

4. PARSE each element's PropertySetConfig:
   - Identify element Type
   - Extract dependency reference per extraction rules above
   - Resolve reference to a known component record

5. PARSE each FlexCard's DataSourceConfig and PropertySetConfig:
   - Extract dataSource (single object)
   - Extract childCardPreview elements
   - Extract action elements (actionList[].stateAction)
   - Resolve references to known components

6. PARSE each Data Mapper's items:
   - Extract InputObjectName / OutputObjectName
   - Resolve to sObject names

7. BUILD directed graph:
   - Nodes = all components + referenced sObjects + external endpoints
   - Edges = dependency references with type labels

8. DETECT circular references:
   - Run DFS cycle detection
   - Record all cycles found

9. COMPUTE impact analysis:
   - For each node, compute transitive closure of inbound edges
   - "If X changes, these components are affected"
```

### Impact Analysis: Reverse Dependency Lookup

To answer "what breaks if I change Data Mapper X?", reverse the dependency direction:

```text
Given: DM:AccountExtract

Direct dependents (components that reference this DM):
  → IP:fetchAccountData (DataRaptor Action)

Transitive dependents (components that reference the direct dependents):
  → OS:updateAccount (IP Action → fetchAccountData)
  → FC:AccountSummaryCard (Data Source → fetchAccountData)

Full impact set: [IP:fetchAccountData, OS:updateAccount, FC:AccountSummaryCard]
```

---

## Property Set Config Parsing Tips

### Handling Large JSON

`PropertySetConfig` can exceed 100KB for complex elements. When querying via SOQL:
- SOQL `SELECT` returns the full field value
- For very large configs, the Tooling API may be necessary
- Parse incrementally if memory is a concern

### Nested Property Sets

Some elements have nested structures. Always check for:
- `bundle` (top-level reference)
- `remoteOptions` (additional remote action config, e.g. `preTransformBundle` / `postTransformBundle` which also reference Data Mappers)

### Common Pitfalls

| Pitfall | Handling |
|---------|---------|
| `integrationProcedureKey` format | Always `Type_SubType` with underscore separator |
| Version-specific references | Some elements reference a specific version; default is latest active |
| Null PropertySetConfig | Skip elements with null/empty config — they have no dependencies |
| JSON parsing errors | Malformed JSON in PropertySetConfig can occur on manually edited records; catch and log |
