<!-- Parent: analyzing-omnistudio-dependencies/SKILL.md -->

# OmniStudio Namespace Reference Guide

## Overview

Salesforce OmniStudio exists under three distinct namespaces depending on the org's industry package and migration status. Every OmniStudio operation must target the correct namespace — queries, metadata retrieval, and deployment all use namespace-specific object and field API names.

| Namespace | Package Context | Typical Orgs |
|-----------|----------------|--------------|
| **Core** (no prefix) | Industries / OmniStudio managed package migrated to Core | Orgs on API 234.0+ (Spring '22+) that have completed the Core migration |
| **vlocity_cmt** | Vlocity Communications, Media & Energy | Telco, media, energy & utilities industry orgs |
| **vlocity_ins** | Vlocity Insurance & Health | Insurance, health, and life sciences industry orgs |

---

## Detection Algorithm

### Step-by-Step Probing

Run SOQL queries against each namespace's primary object. The first query that succeeds determines the namespace.

```
1. Probe Core:
   SELECT COUNT() FROM OmniProcess
   → Success? Namespace = Core. Stop.
   → Failure (INVALID_TYPE)? Continue.

2. Probe vlocity_cmt:
   SELECT COUNT() FROM vlocity_cmt__OmniScript__c
   → Success? Namespace = vlocity_cmt. Stop.
   → Failure (INVALID_TYPE)? Continue.

3. Probe vlocity_ins:
   SELECT COUNT() FROM vlocity_ins__OmniScript__c
   → Success? Namespace = vlocity_ins. Stop.
   → Failure (INVALID_TYPE)? OmniStudio not installed.
```

### CLI Implementation

```bash
# Core probe
sf data query --query "SELECT COUNT() FROM OmniProcess" --target-org myorg --json 2>/dev/null
# Check: result.totalSize >= 0 means Core namespace

# vlocity_cmt probe
sf data query --query "SELECT COUNT() FROM vlocity_cmt__OmniScript__c" --target-org myorg --json 2>/dev/null

# vlocity_ins probe
sf data query --query "SELECT COUNT() FROM vlocity_ins__OmniScript__c" --target-org myorg --json 2>/dev/null
```

### Interpreting Results

- **Exit code 0 + JSON with `totalSize`**: Namespace is present
- **Exit code non-zero or `INVALID_TYPE` error**: Namespace not installed
- **Exit code 0 + `totalSize: 0`**: Namespace exists but no components created yet (still valid)

---

## Object Mapping

### Primary Container Objects

These objects store OmniScript, Integration Procedure, FlexCard, and Data Mapper definitions.

| Concept | Core | vlocity_cmt | vlocity_ins |
|---------|------|-------------|-------------|
| OmniScript / Integration Procedure | `OmniProcess` | `vlocity_cmt__OmniScript__c` | `vlocity_ins__OmniScript__c` |
| OmniScript / IP Elements | `OmniProcessElement` | `vlocity_cmt__Element__c` | `vlocity_ins__Element__c` |
| FlexCard | `OmniUiCard` | `vlocity_cmt__VlocityUITemplate__c` | `vlocity_ins__VlocityUITemplate__c` |
| Data Mapper (DataRaptor) | `OmniDataTransform` | `vlocity_cmt__DRBundle__c` | `vlocity_ins__DRBundle__c` |
| Data Mapper Item | `OmniDataTransformItem` | `vlocity_cmt__DRMapItem__c` | `vlocity_ins__DRMapItem__c` |
| Calculation Matrix | `CalculationMatrix` | `vlocity_cmt__CalculationMatrix__c` | `vlocity_ins__CalculationMatrix__c` |
| Calculation Procedure | `CalculationProcedure` | `vlocity_cmt__CalculationProcedure__c` | `vlocity_ins__CalculationProcedure__c` |

### Relationship Fields (Element → Parent)

| Concept | Core | vlocity_cmt | vlocity_ins |
|---------|------|-------------|-------------|
| Element → Process lookup | `OmniProcessId` | `vlocity_cmt__OmniScriptId__c` | `vlocity_ins__OmniScriptId__c` |
| DM Item → DM lookup | `OmniDataTransformId` | `vlocity_cmt__DRBundleId__c` | `vlocity_ins__DRBundleId__c` |

---

## Field Mapping

### OmniProcess / OmniScript Fields

| Concept | Core (OmniProcess) | vlocity_cmt (OmniScript__c) | vlocity_ins (OmniScript__c) |
|---------|-------------------|---------------------------|---------------------------|
| Type | `Type` | `vlocity_cmt__Type__c` | `vlocity_ins__Type__c` |
| SubType | `SubType` | `vlocity_cmt__SubType__c` | `vlocity_ins__SubType__c` |
| Language | `Language` | `vlocity_cmt__Language__c` | `vlocity_ins__Language__c` |
| Is Active | `IsActive` | `vlocity_cmt__IsActive__c` | `vlocity_ins__IsActive__c` |
| Version | `VersionNumber` | `vlocity_cmt__Version__c` | `vlocity_ins__Version__c` |
| Type Category | `TypeCategory` | N/A (use `vlocity_cmt__IsIntegrationProcedure__c`) | N/A (use `vlocity_ins__IsIntegrationProcedure__c`) |
| Custom HTML | `CustomHtmlTemplates` | `vlocity_cmt__CustomHtmlTemplates__c` | `vlocity_ins__CustomHtmlTemplates__c` |
| Is Reusable | `IsReusable` | `vlocity_cmt__IsReusable__c` | `vlocity_ins__IsReusable__c` |
| Procedure Key | N/A | `vlocity_cmt__ProcedureKey__c` | `vlocity_ins__ProcedureKey__c` |

**Note on TypeCategory vs IsIntegrationProcedure**: In Core namespace, `TypeCategory` distinguishes OmniScripts from Integration Procedures (`'OmniScript'` vs `'IntegrationProcedure'`). In Vlocity namespaces, use the boolean field `IsIntegrationProcedure__c` instead.

### Element Fields

| Concept | Core (OmniProcessElement) | vlocity_cmt (Element__c) | vlocity_ins (Element__c) |
|---------|--------------------------|-------------------------|-------------------------|
| Name | `Name` | `Name` | `Name` |
| Type | `Type` | `vlocity_cmt__Type__c` | `vlocity_ins__Type__c` |
| Property Set Config | `PropertySetConfig` | `vlocity_cmt__PropertySet__c` | `vlocity_ins__PropertySet__c` |
| Order | `SequenceNumber` | `vlocity_cmt__Order__c` | `vlocity_ins__Order__c` |
| Is Active | `IsActive` | `vlocity_cmt__Active__c` | `vlocity_ins__Active__c` |
| Parent Element | `ParentElementId` | `vlocity_cmt__ParentElementId__c` | `vlocity_ins__ParentElementId__c` |
| Level | `Level` | `vlocity_cmt__Level__c` | `vlocity_ins__Level__c` |

### FlexCard / UI Template Fields

| Concept | Core (OmniUiCard) | vlocity_cmt (VlocityUITemplate__c) | vlocity_ins (VlocityUITemplate__c) |
|---------|-------------------|-----------------------------------|-----------------------------------|
| Name | `Name` | `Name` | `Name` |
| Is Active | `IsActive` | `vlocity_cmt__IsActive__c` | `vlocity_ins__IsActive__c` |
| Definition | `Definition` | `vlocity_cmt__Definition__c` | `vlocity_ins__Definition__c` |
| Author Name | `AuthorName` | `vlocity_cmt__Author__c` | `vlocity_ins__Author__c` |
| Version | `VersionNumber` | `vlocity_cmt__Version__c` | `vlocity_ins__Version__c` |
| Template Type | N/A | `vlocity_cmt__TemplateType__c` | `vlocity_ins__TemplateType__c` |

### Data Mapper / DataRaptor Fields

| Concept | Core (OmniDataTransform) | vlocity_cmt (DRBundle__c) | vlocity_ins (DRBundle__c) |
|---------|-------------------------|--------------------------|--------------------------|
| Name | `Name` | `Name` | `Name` |
| Type | `Type` | `vlocity_cmt__Type__c` | `vlocity_ins__Type__c` |
| Is Active | `IsActive` | `vlocity_cmt__IsActive__c` | `vlocity_ins__IsActive__c` |
| Input Type | `InputType` | `vlocity_cmt__InputType__c` | `vlocity_ins__InputType__c` |
| Output Type | `OutputType` | `vlocity_cmt__OutputType__c` | `vlocity_ins__OutputType__c` |

### Data Mapper Item Fields

| Concept | Core (OmniDataTransformItem) | vlocity_cmt (DRMapItem__c) | vlocity_ins (DRMapItem__c) |
|---------|------------------------------|---------------------------|---------------------------|
| Input Object | `InputObjectName` | `vlocity_cmt__InterfaceObject__c` | `vlocity_ins__InterfaceObject__c` |
| Output Object | `OutputObjectName` | `vlocity_cmt__TargetFieldObjectType__c` | `vlocity_ins__TargetFieldObjectType__c` |
| Input Field | `InputFieldName` | `vlocity_cmt__InterfaceFieldAPIName__c` | `vlocity_ins__InterfaceFieldAPIName__c` |
| Output Field | `OutputFieldName` | `vlocity_cmt__TargetFieldAPIName__c` | `vlocity_ins__TargetFieldAPIName__c` |
| Filter Data Type | `FilterDataType` | `vlocity_cmt__FilterDataType__c` | `vlocity_ins__FilterDataType__c` |
| Query Sequence | `InputObjectQuerySequence` | `vlocity_cmt__InterfaceObjectLookupOrder__c` | `vlocity_ins__InterfaceObjectLookupOrder__c` |

---

## Metadata Type Names for Deployment

When using `sf project retrieve start` or `sf project deploy start`, reference the correct metadata type:

| Component | Core Metadata Type | Vlocity Metadata Type |
|-----------|-------------------|----------------------|
| OmniScript | `OmniScript` | N/A (use Vlocity Build Tool) |
| Integration Procedure | `OmniIntegrationProcedure` | N/A (use Vlocity Build Tool) |
| FlexCard | `OmniUiCard` | N/A (use Vlocity Build Tool) |
| Data Mapper | `OmniDataTransform` | N/A (use Vlocity Build Tool) |
| Data Mapper Item | `OmniDataTransformItem` | N/A (use Vlocity Build Tool) |

**Note**: Only Core namespace components support standard Salesforce metadata API deployment. Vlocity namespace components require the Vlocity Build Tool (`vlocity_build`) for migration between orgs.

### Retrieve Example (Core)
```bash
sf project retrieve start --metadata OmniScript --target-org myorg
sf project retrieve start --metadata OmniDataTransform --target-org myorg
```

---

## Mixed Namespace Scenarios

### During Core Migration

Organizations migrating from a Vlocity namespace to Core may temporarily have components under both namespaces. During this transition:

1. **Probe both namespaces** — if both return results, the org is mid-migration
2. **Core components take precedence** — runtime uses Core namespace objects when both exist
3. **Report the state** — alert the user that migration is in progress and both namespaces contain data
4. **Do not modify Vlocity-namespace components** — they are frozen during migration

### Detection of Mixed State

```bash
# Check if Core has components
sf data query --query "SELECT COUNT() FROM OmniProcess" --target-org myorg --json 2>/dev/null

# Also check if Vlocity still has components
sf data query --query "SELECT COUNT() FROM vlocity_cmt__OmniScript__c" --target-org myorg --json 2>/dev/null
```

If both return `totalSize > 0`, the org is in a mixed namespace state.

### Recommended Actions During Mixed State

- Inventory components under both namespaces
- Compare counts to assess migration progress
- Flag components that exist only in the old namespace (not yet migrated)
- Do not create components under the old namespace

---

## Data Mapper Type Values

The `Type` field on OmniDataTransform / DRBundle indicates the mapper's purpose:

| Type Value | Description |
|-----------|-------------|
| `Extract` | Reads data from Salesforce objects |
| `Transform` | Maps and transforms data between structures |
| `Load` | Writes data to Salesforce objects |
| `Turbo Extract` | High-performance read (bypasses sharing rules) |

---

## SOQL Query Templates

### Core Namespace — Full Inventory

```soql
-- All OmniScripts
SELECT Id, Type, SubType, Language, IsActive, VersionNumber, LastModifiedDate
FROM OmniProcess
WHERE TypeCategory = 'OmniScript'
ORDER BY Type, SubType, Language, VersionNumber DESC

-- All Integration Procedures
SELECT Id, Type, SubType, Language, IsActive, VersionNumber, LastModifiedDate
FROM OmniProcess
WHERE TypeCategory = 'IntegrationProcedure'
ORDER BY Type, SubType, Language, VersionNumber DESC

-- All FlexCards
SELECT Id, Name, IsActive, AuthorName, VersionNumber, LastModifiedDate
FROM OmniUiCard
ORDER BY Name, VersionNumber DESC

-- All Data Mappers
SELECT Id, Name, Type, IsActive, InputType, OutputType, LastModifiedDate
FROM OmniDataTransform
ORDER BY Name
```

### vlocity_cmt Namespace — Full Inventory

```soql
-- All OmniScripts
SELECT Id, vlocity_cmt__Type__c, vlocity_cmt__SubType__c,
       vlocity_cmt__Language__c, vlocity_cmt__IsActive__c, vlocity_cmt__Version__c
FROM vlocity_cmt__OmniScript__c
WHERE vlocity_cmt__IsIntegrationProcedure__c = false
ORDER BY vlocity_cmt__Type__c, vlocity_cmt__SubType__c

-- All Integration Procedures
SELECT Id, vlocity_cmt__Type__c, vlocity_cmt__SubType__c,
       vlocity_cmt__Language__c, vlocity_cmt__IsActive__c, vlocity_cmt__Version__c
FROM vlocity_cmt__OmniScript__c
WHERE vlocity_cmt__IsIntegrationProcedure__c = true
ORDER BY vlocity_cmt__Type__c, vlocity_cmt__SubType__c

-- All FlexCards / UI Templates
SELECT Id, Name, vlocity_cmt__IsActive__c, vlocity_cmt__Version__c
FROM vlocity_cmt__VlocityUITemplate__c
ORDER BY Name

-- All Data Mappers (DataRaptors)
SELECT Id, Name, vlocity_cmt__Type__c, vlocity_cmt__IsActive__c
FROM vlocity_cmt__DRBundle__c
ORDER BY Name
```

### vlocity_ins Namespace — Full Inventory

```soql
-- All OmniScripts
SELECT Id, vlocity_ins__Type__c, vlocity_ins__SubType__c,
       vlocity_ins__Language__c, vlocity_ins__IsActive__c, vlocity_ins__Version__c
FROM vlocity_ins__OmniScript__c
WHERE vlocity_ins__IsIntegrationProcedure__c = false
ORDER BY vlocity_ins__Type__c, vlocity_ins__SubType__c

-- All Integration Procedures
SELECT Id, vlocity_ins__Type__c, vlocity_ins__SubType__c,
       vlocity_ins__Language__c, vlocity_ins__IsActive__c, vlocity_ins__Version__c
FROM vlocity_ins__OmniScript__c
WHERE vlocity_ins__IsIntegrationProcedure__c = true
ORDER BY vlocity_ins__Type__c, vlocity_ins__SubType__c

-- All FlexCards / UI Templates
SELECT Id, Name, vlocity_ins__IsActive__c, vlocity_ins__Version__c
FROM vlocity_ins__VlocityUITemplate__c
ORDER BY Name

-- All Data Mappers (DataRaptors)
SELECT Id, Name, vlocity_ins__Type__c, vlocity_ins__IsActive__c
FROM vlocity_ins__DRBundle__c
ORDER BY Name
```
