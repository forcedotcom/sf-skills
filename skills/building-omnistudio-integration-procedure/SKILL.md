---
name: building-omnistudio-integration-procedure
description: "OmniStudio Integration Procedure creation and validation with 110-point
  scoring. Use when building server-side process orchestrations that combine Data Mapper
  actions, Apex Remote Actions, HTTP callouts, and conditional logic.
  TRIGGER when: user creates Integration Procedures, adds Data Mapper steps,
  configures Remote Actions, or reviews existing IP configurations.
  DO NOT TRIGGER when: building OmniScripts (use building-omnistudio-omniscript),
  creating Data Mappers directly (use building-omnistudio-datamapper), or analyzing
  cross-component dependencies (use analyzing-omnistudio-dependencies)."
license: MIT
metadata:
  version: "1.0"
---

# building-omnistudio-integration-procedure: OmniStudio Integration Procedure Creation and Validation

Expert OmniStudio Integration Procedure (IP) builder with deep knowledge of server-side process orchestration. Create production-ready IPs that combine DataRaptor/Data Mapper actions, Apex Remote Actions, HTTP callouts, conditional logic, and nested procedure calls into declarative multi-step operations.

## Scope

- **In scope**: Creating well-structured Integration Procedures from requirements; selecting and wiring element types (DataRaptor, Remote Action, HTTP, Conditional Block, Loop, Set Values, nested IP); dependency validation; error handling patterns; 110-point scoring; deployment and activation
- **Out of scope**: Building OmniScripts (use `building-omnistudio-omniscript`), creating Data Mappers directly (use `building-omnistudio-datamapper`), designing FlexCards (use `building-omnistudio-flexcard`), mapping full dependency trees (use `analyzing-omnistudio-dependencies`), deploying metadata to org (use `deploying-metadata`)

---

## Required Inputs

- **Purpose**: What business process is this IP orchestrating? (e.g., "onboard a new account", "process an order")
- **Target objects / data sources**: Which Salesforce objects, external APIs, or both?
- **Type / SubType naming**: PascalCase pair that uniquely identifies the IP (e.g., `Type=OrderProcessing`, `SubType=Standard`)
- **Target org alias**: Authenticated org alias for deployment (e.g., `myDevOrg`)

---

## Quick Reference

**Scoring**: 110 points across 6 categories. **Thresholds**: ✅ 90+ (Deploy) | ⚠️ 67-89 (Review) | ❌ <67 (Block - fix required)

---

## Core Responsibilities

1. **IP Generation**: Create well-structured Integration Procedures from requirements, selecting correct element types and wiring inputs/outputs
2. **Element Composition**: Assemble DataRaptor actions, Remote Actions, HTTP callouts, conditional blocks, loops, and nested IP calls into coherent orchestrations
3. **Dependency Analysis**: Validate that referenced DataRaptors, Apex classes, and nested IPs exist and are active before deployment
4. **Error Handling**: Enforce try/catch patterns, conditional rollback, and response validation across all data-modifying steps (DML — Data Manipulation Language)

---

## CRITICAL: Orchestration Order

**analyzing-omnistudio-dependencies -> building-omnistudio-datamapper -> building-omnistudio-integration-procedure -> building-omnistudio-omniscript -> building-omnistudio-flexcard** (you are here: building-omnistudio-integration-procedure)

Data Mappers referenced by the IP must exist FIRST. Build and deploy DataRaptors/Data Mappers before the IP that calls them. The IP must be active before any OmniScript or FlexCard can invoke it.

---

## Key Insights

| Insight | Details |
|---------|---------|
| **Chaining** | IPs call other IPs via Integration Procedure Action elements. Output of one step feeds input of the next via response mapping. Design data flow linearly where possible. |
| **Response Mapping** | Each element's output is namespaced under its element name in the response JSON. Use `%elementName:keyPath%` syntax to reference upstream outputs in downstream inputs. |
| **Caching** | IPs support platform cache for read-heavy orchestrations. Set `cacheType` and `cacheTTL` in the procedure's PropertySet. Avoid caching procedures that perform DML. |
| **Versioning** | Type/SubType pairs uniquely identify an IP. Use SubType for versioning (e.g., `Type=AccountOnboarding`, `SubType=v2`). Only one version can be active at a time per Type/SubType. |

**Core Namespace Discriminator**: OmniStudio Core stores both Integration Procedures and OmniScripts in the `OmniProcess` table. Use `IsIntegrationProcedure = true` or `OmniProcessType = 'Integration Procedure'` to filter IPs. Without a filter, queries return mixed results.

> **CRITICAL — Creating IPs via Data API**: When creating OmniProcess records, set `IsIntegrationProcedure = true` to make the record an Integration Procedure. The `OmniProcessType` picklist is **computed from this boolean** and cannot be set directly. Also, `Name` is a required field on `OmniProcess` (not documented in standard OmniStudio docs). Use `sf api request rest --method POST --body @file.json` for creation — the `sf data create record --values` flag cannot handle JSON textarea fields like `PropertySetConfig`.

---

## Workflow Design (5-Phase Pattern)

### Phase 1: Requirements Gathering

**Before building, evaluate alternatives**: Sometimes a single DataRaptor, an Apex service, or a Flow is the better choice. IPs are optimal when you need declarative multi-step orchestration with branching, error handling, and mixed data sources.

**Ask the user** to gather:
- Purpose and business process being orchestrated
- Target objects and data sources (Salesforce objects, external APIs, or both)
- Type/SubType naming (e.g., `Type=OrderProcessing`, `SubType=Standard`)
- Target org alias for deployment

**Then**: Check existing IPs via CLI query (see CLI Commands below), identify reusable DataRaptors/Data Mappers, and review dependent components with analyzing-omnistudio-dependencies.

### Phase 2: Design & Element Selection

| Element Type | Use Case | PropertySet Key |
|--------------|----------|-----------------|
| DataRaptor Extract Action | Read Salesforce data | `bundle` |
| DataRaptor Load Action | Write Salesforce data | `bundle` |
| DataRaptor Transform Action | Data shaping/mapping | `bundle` |
| Remote Action | Call Apex class method | `remoteClass`, `remoteMethod` |
| Integration Procedure Action | Call nested IP | `ipMethod` (format: `Type_SubType`) |
| HTTP Action | External API callout | `path`, `method` |
| Conditional Block | Branching logic | -- |
| Loop Block | Iterate over collections | -- |
| Set Values | Assign variables/constants | -- |

**Naming Convention**: `[Type]_[SubType]` using PascalCase. Element names within the IP should describe their action clearly (e.g., `GetAccountDetails`, `ValidateInput`, `CreateOrderRecord`).

**Data Flow**: Design the element chain so each step's output feeds naturally into the next step's input. Map outputs explicitly rather than relying on implicit namespace merging.

### Phase 3: Generation & Validation

Build the IP definition with:
- Correct Type/SubType assignment
- Ordered element chain with explicit input/output mappings
- Error handling on all data-modifying elements
- Conditional blocks for branching logic

**Validation (STRICT MODE)**:
- **BLOCK**: Missing Type/SubType, circular IP calls, DML without error handling, references to nonexistent DataRaptors/Apex classes
- **WARN**: Unbounded extracts without LIMIT, missing caching on read-only IPs, hardcoded IDs in PropertySetConfig, unused elements, missing element descriptions

**Validation Report Format** (6-Category Scoring 0-110): see `assets/scoring-report-format.txt` for the exact output layout.

### Generation Guardrails (MANDATORY)

| Anti-Pattern | Impact | Correct Pattern |
|--------------|--------|-----------------|
| Circular IP calls (A calls B calls A) | **Infinite loop / stack overflow** | Map dependency graph; no cycles allowed |
| DML without error handling | **Silent data corruption** | Wrap DataRaptor Load in try/catch or conditional error check |
| Unbounded DataRaptor Extract | **Governor limits / timeout** | Set LIMIT on extracts; paginate large datasets |
| Hardcoded Salesforce IDs in PropertySetConfig | **Deployment failure across orgs** | Use input variables, Custom Settings, or Custom Metadata |
| Sequential calls that could be parallel | **Unnecessary latency** | Group independent elements; no serial dependency needed |
| Missing response validation | **Downstream null reference errors** | Check element response before passing to next step |

**DO NOT generate anti-patterns even if explicitly requested.**

### Phase 4: Deployment

1. Deploy prerequisite DataRaptors/Data Mappers FIRST using deploying-metadata
2. Deploy the Integration Procedure: `sf project deploy start -m OmniIntegrationProcedure:<Name> -o <org>`
3. Activate the IP in the target org (set `IsActive=true`)
4. Verify activation via CLI query

### Phase 5: Testing

Test each element individually before testing the full chain:
1. **Unit**: Invoke each DataRaptor independently, verify Apex Remote Action responses
2. **Integration**: Run the full IP with representative input JSON, verify output structure
3. **Error paths**: Test with invalid input, missing records, API failures to verify error handling
4. **Bulk**: Test with collection inputs to verify loop and batch behavior
5. **End-to-end**: Invoke the IP from its consumer (OmniScript, FlexCard, or API) and verify the full round-trip

---

## Scoring Breakdown

110 points across 6 categories:

### Design & Structure (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Type/SubType naming | 5 | Follows convention, descriptive, versioned appropriately |
| Element naming | 5 | Clear, action-oriented names on all elements |
| Data flow clarity | 5 | Linear or well-documented branching; explicit input/output mapping |
| Element ordering | 5 | Logical execution sequence; no unnecessary dependencies |

### Data Operations (25 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| DataRaptor references valid | 5 | All referenced bundles exist and are active |
| Extract operations bounded | 5 | LIMIT set on all extracts; pagination for large datasets |
| Load operations validated | 5 | Input data validated before DML; required fields checked |
| Response mapping correct | 5 | Outputs correctly mapped between elements |
| Data transformation accuracy | 5 | Transform actions produce expected output structure |

### Error Handling (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| DML error handling | 8 | All DataRaptor Load actions have error handling |
| HTTP error handling | 4 | All HTTP actions check status codes and handle failures |
| Remote Action error handling | 4 | Apex exceptions caught and surfaced |
| Rollback strategy | 4 | Multi-step DML has conditional rollback or compensating actions |

### Performance (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| No unbounded queries | 5 | All extracts have reasonable LIMIT values |
| Caching applied | 5 | Read-only procedures use platform cache where appropriate |
| Parallel execution | 5 | Independent elements not serialized unnecessarily |
| No redundant calls | 5 | Same data not fetched multiple times across elements |

### Security (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| No hardcoded IDs | 5 | IDs passed as input variables or from metadata |
| No hardcoded credentials | 5 | API keys/tokens use Named Credentials or Custom Settings |
| Input validation | 5 | User-supplied input sanitized before use in queries or DML |

### Documentation (10 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Procedure description | 3 | Clear description of purpose and business context |
| Element descriptions | 4 | Each element has a description explaining its role |
| Input/output documentation | 3 | Expected input JSON and output JSON structure documented |

---

## CLI Commands

**Read `scripts/cli-commands.sh`** before querying or deploying Integration Procedures — it contains all SOQL queries and `sf project` deploy/retrieve commands ready to adapt.

**Core Namespace Note**: The `IsIntegrationProcedure=true` filter is REQUIRED (or equivalently `OmniProcessType='Integration Procedure'`). OmniScript and Integration Procedure records share the `OmniProcess` sObject. Without this filter, queries return both types and produce misleading results.

---

## Cross-Skill Integration

| From Skill | To building-omnistudio-integration-procedure | When |
|------------|----------------------------|------|
| analyzing-omnistudio-dependencies | -> building-omnistudio-integration-procedure | "Analyze dependencies before building IP" |
| building-omnistudio-datamapper | -> building-omnistudio-integration-procedure | "DataRaptor/Data Mapper is ready, wire it into IP" |
| generating-apex | -> building-omnistudio-integration-procedure | "Apex Remote Action class deployed, configure in IP" |

| From building-omnistudio-integration-procedure | To Skill | When |
|-------------------------------|----------|------|
| building-omnistudio-integration-procedure | -> deploying-metadata | "Deploy IP to target org" |
| building-omnistudio-integration-procedure | -> building-omnistudio-omniscript | "IP is active, build OmniScript that calls it" |
| building-omnistudio-integration-procedure | -> building-omnistudio-flexcard | "IP is active, build FlexCard data source" |
| building-omnistudio-integration-procedure | -> analyzing-omnistudio-dependencies | "Verify IP dependency graph before deployment" |

---

## Edge Cases

| Scenario | Solution |
|----------|----------|
| IP calls itself (direct recursion) | Block at design time; circular dependency check is mandatory |
| IP calls IP that calls original (indirect recursion) | Map full call graph; analyzing-omnistudio-dependencies detects cycles |
| DataRaptor not yet deployed | Deploy DataRaptors first; IP deployment will fail on missing references |
| External API timeout | Set timeout values on HTTP Action elements; implement retry logic or graceful degradation |
| Large collection input to Loop Block | Set batch size; test with realistic data volumes to avoid CPU timeout |
| Type/SubType collision with existing IP | Query existing IPs before creating; SubType versioning avoids collisions |
| Mixed namespace (Vlocity vs Core) | Confirm org namespace; element property names differ between packages |

**Debug**: IP not executing -> check IsActive flag + Type/SubType match | Elements skipped -> verify conditional block logic + input data shape | Timeout -> check DataRaptor query scope + HTTP timeout settings | Deployment failure -> verify all referenced components deployed and active

---

## Output Expectations

Deliverables produced by this skill:

- **Integration Procedure JSON** (`assets/omni-process-ip.json` template) — `OmniProcess` record ready for REST API creation with `IsIntegrationProcedure=true`
- **Element JSON records** (`assets/omni-process-element-dr-extract.json`, `assets/omni-process-element-set-values.json` templates) — `OmniProcessElement` records for each action step with `PropertySetConfig` wired
- **Validation report** — 110-point score across 6 categories with deploy/review/block threshold result
- **Deployment checklist** — confirms prerequisite DataRaptors are active, IP is activated, and consuming OmniScript or FlexCard can invoke it

---

## Notes

**API**: Latest (check current Salesforce release notes; was 66.0 at time of authoring) | **Mode**: Strict (warnings block) | **Scoring**: Block deployment if score < 67

**Dependencies** (optional): deploying-metadata, building-omnistudio-datamapper, analyzing-omnistudio-dependencies

**Creating IPs programmatically**: Use REST API (`sf api request rest --method POST --body @file.json`). Required fields: `Name`, `Type`, `SubType`, `Language`, `VersionNumber`, `IsIntegrationProcedure=true`. Then create `OmniProcessElement` child records for each action step (also via REST API for JSON PropertySetConfig). Activate by setting `IsActive=true` after all elements are created.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/omni-process-ip.json` | Phase 3 — Generation: use as the OmniProcess record template when creating the Integration Procedure via REST API |
| `assets/omni-process-element-dr-extract.json` | Phase 3 — Generation: use as the DataRaptor Extract Action element template; adapt for other DR action types |
| `assets/omni-process-element-set-values.json` | Phase 3 — Generation: use as the Set Values element template for variable assignment steps |
| `assets/scoring-report-format.txt` | Phase 3 — Validation: use as the output layout template when presenting the 110-point validation report |
| `references/best-practices.md` | Phase 2-5 — Design patterns: element composition, error handling, caching, parallel execution, and security guidance |
| `references/element-types.md` | Phase 2 — Element selection: read before configuring PropertySetConfig for any element type |
| `scripts/cli-commands.sh` | Phase 1 & 4 — CLI queries and deploy/retrieve commands; adapt by replacing `<Name>` and `<org>` placeholders |
