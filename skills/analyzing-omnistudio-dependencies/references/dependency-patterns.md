<!-- Parent: analyzing-omnistudio-dependencies/SKILL.md -->

# OmniStudio Dependency Patterns

## Overview

OmniStudio components form a directed graph where each component type can reference others. Dependencies are not stored in lookup fields — they are embedded in JSON configuration fields (`PropertySetConfig`, `Definition`, `InputObjectName`/`OutputObjectName`). Extracting dependencies requires parsing these JSON structures.

---

## Dependency Direction Summary

```
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

OmniScript elements are stored as `OmniProcessElement` records (Core) or `Element__c` records (Vlocity). Each element has a `PropertySetConfig` / `PropertySet__c` JSON field containing the configuration.

#### DataRaptor Transform Action

Calls a Data Mapper to extract, transform, or load data.

**PropertySetConfig structure**:
```json
{
  "Type": "DataRaptor Transform Action",
  "PropertySet": {
    "bundle": "AccountExtract",
    "bundleName": "AccountExtract",
    "dataRaptorType": "Extract"
  }
}
```

**Extraction rule**: `PropertySet.bundle` or `PropertySet.bundleName` → resolves to an `OmniDataTransform` record by `Name`.

#### DataRaptor Turbo Action

High-performance variant of DataRaptor Transform Action. Same JSON structure, same extraction rule.

**PropertySetConfig structure**:
```json
{
  "Type": "DataRaptor Turbo Action",
  "PropertySet": {
    "bundle": "AccountTurboExtract",
    "bundleName": "AccountTurboExtract"
  }
}
```

#### Integration Procedure Action

Calls an Integration Procedure.

**PropertySetConfig structure**:
```json
{
  "Type": "Integration Procedure Action",
  "PropertySet": {
    "integrationProcedureKey": "TypeName_SubTypeName",
    "ipMethod": "TypeName",
    "ipType": "SubTypeName",
    "integrationProcedureVersion": 1
  }
}
```

**Extraction rule**: `PropertySet.integrationProcedureKey` → resolves to an `OmniProcess` record where `Type_SubType` matches and `TypeCategory = 'IntegrationProcedure'`.

#### OmniScript Action (Embedded OmniScript)

Embeds or launches another OmniScript.

**PropertySetConfig structure**:
```json
{
  "Type": "OmniScript",
  "PropertySet": {
    "Type": "ChildScriptType",
    "Sub Type": "ChildScriptSubType",
    "Language": "English"
  }
}
```

**Extraction rule**: `PropertySet.Type` + `PropertySet["Sub Type"]` + `PropertySet.Language` → resolves to an `OmniProcess` where `TypeCategory = 'OmniScript'` and fields match.

#### Remote Action

Calls an Apex class method.

**PropertySetConfig structure**:
```json
{
  "Type": "Remote Action",
  "PropertySet": {
    "remoteClass": "MyApexClassName",
    "remoteMethod": "myMethodName",
    "remoteTimeout": 30000
  }
}
```

**Extraction rule**: `PropertySet.remoteClass` → Apex class name. `PropertySet.remoteMethod` → method name. Dependency is `remoteClass.remoteMethod`.

#### HTTP Action

Calls an external HTTP endpoint.

**PropertySetConfig structure**:
```json
{
  "Type": "HTTP Action",
  "PropertySet": {
    "httpUrl": "{externalEndpointUrl}",
    "httpMethod": "POST",
    "namedCredential": "MyNamedCredential"
  }
}
```

**Extraction rule**: `PropertySet.httpUrl` or `PropertySet.namedCredential` → external dependency. If `namedCredential` is present, it references a Named Credential record.

#### Custom Lightning Web Component

Embeds an LWC inside the OmniScript.

**PropertySetConfig structure**:
```json
{
  "Type": "Custom Lightning Web Component",
  "PropertySet": {
    "lwcName": "myCustomComponent",
    "lwcComponentName": "c-my-custom-component"
  }
}
```

**Extraction rule**: `PropertySet.lwcName` or `PropertySet.lwcComponentName` → LWC component reference.

#### DocuSign Envelope Action

Triggers a DocuSign envelope.

**PropertySetConfig structure**:
```json
{
  "Type": "DocuSign Envelope Action",
  "PropertySet": {
    "docuSignTemplateId": "template-uuid"
  }
}
```

**Extraction rule**: `PropertySet.docuSignTemplateId` → DocuSign template (external dependency).

---

## Integration Procedure Dependencies

Integration Procedures use the same element types as OmniScripts but are filtered by `TypeCategory = 'IntegrationProcedure'` (Core) or `IsIntegrationProcedure__c = true` (Vlocity).

### Element Types Available in IPs

| Element Type | Available in IP | Dependency Target |
|-------------|----------------|-------------------|
| DataRaptor Transform Action | Yes | Data Mapper |
| DataRaptor Turbo Action | Yes | Data Mapper |
| Remote Action | Yes | Apex Class |
| HTTP Action | Yes | External endpoint |
| Integration Procedure Action | Yes (nested) | Another IP |
| Matrix Action | Yes | Calculation Matrix |
| Set Values | Yes | None (internal) |
| Conditional Block | Yes | None (internal) |
| Loop Block | Yes | None (internal) |
| Response Action | Yes | None (internal) |
| List Action | Yes | None (internal) |

### Nested IP Pattern

An Integration Procedure can call another Integration Procedure, creating a chain:

```
IP: OrderValidation
  └── IP Action → IP: CustomerLookup
       └── DR Action → DM: CustomerExtract
  └── IP Action → IP: InventoryCheck
       └── HTTP Action → External inventory API
  └── DR Action → DM: OrderTransform
```

---

## FlexCard Dependencies

FlexCards store their entire configuration in the `Definition` JSON field on `OmniUiCard` (Core) or `VlocityUITemplate__c` (Vlocity).

### Data Source Parsing

The `Definition` JSON contains a `dataSources` array:

```json
{
  "dataSources": [
    {
      "name": "AccountData",
      "type": "IntegrationProcedure",
      "value": {
        "key": "fetchAccountData",
        "inputMap": { "AccountId": "{recordId}" }
      }
    },
    {
      "name": "DirectApex",
      "type": "Apex",
      "value": {
        "className": "AccountSummaryController",
        "methodName": "getSummary"
      }
    },
    {
      "name": "SObjectData",
      "type": "SObject",
      "value": {
        "sObjectType": "Account",
        "fields": ["Name", "Industry", "Phone"]
      }
    }
  ]
}
```

**Extraction rules by data source type**:

| Data Source Type | JSON Path | Dependency Target |
|-----------------|-----------|-------------------|
| `IntegrationProcedure` | `value.key` | Integration Procedure (Type_SubType key) |
| `Apex` | `value.className` | Apex Class |
| `SObject` | `value.sObjectType` | Salesforce Object (direct SOQL) |
| `DataRaptor` | `value.bundle` | Data Mapper |

### Child Card References

FlexCards can embed other FlexCards:

```json
{
  "children": [
    {
      "cardName": "ContactListCard",
      "cardType": "childCard"
    }
  ]
}
```

**Extraction rule**: `children[].cardName` → resolves to another `OmniUiCard` by Name.

### Action References

FlexCard actions can launch OmniScripts:

```json
{
  "actions": [
    {
      "actionType": "OmniScript",
      "actionValue": {
        "type": "editAccount",
        "subType": "step1",
        "language": "English"
      }
    }
  ]
}
```

**Extraction rule**: `actions[].actionValue.type` + `subType` + `language` → resolves to an OmniScript.

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

```
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

```
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

```
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

```
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

```
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

```
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

5. PARSE each FlexCard's Definition:
   - Extract dataSources array
   - Extract children array
   - Extract actions array
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

```
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
- `PropertySet.bundle` (top-level reference)
- `PropertySet.elementProperties` (per-field configs)
- `PropertySet.conditionalProperties` (conditional logic)
- `PropertySet.remoteOptions` (additional remote action config)

### Common Pitfalls

| Pitfall | Handling |
|---------|---------|
| `bundleName` vs `bundle` | Both may exist; prefer `bundle` as the canonical reference |
| `integrationProcedureKey` format | Always `Type_SubType` with underscore separator |
| Version-specific references | Some elements reference a specific version; default is latest active |
| Null PropertySetConfig | Skip elements with null/empty config — they have no dependencies |
| JSON parsing errors | Malformed JSON in PropertySetConfig can occur on manually edited records; catch and log |
