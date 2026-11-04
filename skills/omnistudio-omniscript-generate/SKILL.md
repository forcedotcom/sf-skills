---
name: omnistudio-omniscript-generate
description: "OmniStudio OmniScript creation and validation with 120-point scoring. Use when building guided digital experiences, multi-step forms, or interactive processes that orchestrate Integration Procedures and Data Mappers. TRIGGER when: user creates OmniScripts, designs step flows, configures element types, or reviews existing OmniScript configurations. DO NOT TRIGGER when: building FlexCards (use omnistudio-flexcard-generate), creating Integration Procedures directly (use omnistudio-integration-procedure-generate), or analyzing dependencies (use omnistudio-dependencies-analyze)."
metadata:
  version: "1.0"
  domains: ["OmniStudio"]
  minApiVersion: "66.0"
  relatedSkills:
    - "omnistudio-datamapper-generate"
    - "omnistudio-dependencies-analyze"
    - "omnistudio-flexcard-generate"
    - "omnistudio-integration-procedure-generate"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# omnistudio-omniscript-generate: OmniStudio OmniScript Creation and Validation

Expert OmniStudio OmniScript builder for declarative, step-based guided digital experiences. OmniScripts are the OmniStudio analog of Screen Flows: multi-step, interactive processes that collect input, orchestrate server-side logic (Integration Procedures, DataRaptors), and present results to the user — all without code.

## Quick Reference

**Scoring**: 120 points across 6 categories. **Thresholds**: [PASS] 90+ (Deploy) | [REVIEW] 67-89 (Review) | [BLOCK] <67 (Block - fix required)

---

## Scope

- **In scope**: Creating OmniScripts from requirements, element selection and PropertySetConfig design, dependency analysis (Integration Procedures, DataRaptors), data flow tracing, 120-point validation scoring, deployment and activation
- **Out of scope**: Building FlexCards (use `omnistudio-flexcard-generate`), creating Integration Procedures directly (use `omnistudio-integration-procedure-generate`), mapping full dependency trees (use `omnistudio-dependencies-analyze`), deploying metadata to org (use `platform-metadata-deploy`)

---

## Required Inputs

Gather these before building:

| Input | Description | Default |
|-------|-------------|---------|
| **Type** | Process category (e.g., `ServiceRequest`, `Enrollment`) | None — required |
| **SubType** | Specific variation (e.g., `NewCase`, `UpdateAddress`) | None — required |
| **Language** | Locale for the OmniScript | `English` |
| **Purpose** | Business process this OmniScript guides | None — required |
| **Target org** | Org alias for deployment | Current default org |
| **Data sources** | Objects/APIs to query or update | Identify from requirements |

---

## Core Responsibilities

1. **OmniScript Generation**: Create well-structured OmniScripts from requirements, selecting appropriate element types for each step
2. **Element Design**: Configure PropertySetConfig JSON for each element with correct data binding, validation, and conditional logic
3. **Dependency Analysis**: Map all references to Integration Procedures, DataRaptors, and embedded OmniScripts before deployment
4. **Data Flow Analysis**: Trace data through the OmniScript JSON structure — from prefill through user input to final save actions

---

## CRITICAL: Orchestration Order

**omnistudio-dependencies-analyze → omnistudio-datamapper-generate → omnistudio-integration-procedure-generate → omnistudio-omniscript-generate → omnistudio-flexcard-generate** (you are here: omnistudio-omniscript-generate)

OmniScripts consume Integration Procedures and DataRaptors. Build those FIRST. FlexCards may launch OmniScripts — build FlexCards AFTER. Use omnistudio-dependencies-analyze to map the full dependency tree before starting.

---

## Key Insights

| Insight | Details |
|---------|---------|
| **Type/SubType/Language triplet** | Uniquely identifies an OmniScript. All three values are required and form the composite key. Example: Type=`ServiceRequest`, SubType=`NewCase`, Language=`English` |
| **PropertySetConfig** | JSON blob containing all element configuration — layout, data binding, validation rules, conditional visibility. This is where the real logic lives |
| **Core namespace** | OmniProcess with `IsIntegrationProcedure = false` (equivalently `OmniProcessType='OmniScript'`). Elements are child OmniProcessElement records |
| **Element hierarchy** | Elements use `Level`, `SequenceNumber` and `ParentElementId` for tree structure. Level 0 = Steps (and top-level actions), Level 1+ = elements within Steps/Blocks. `SequenceNumber` determines order within a parent. In source metadata (`.os-meta.xml`) children are nested `<childElements>` |
| **Version management** | Multiple versions can exist; only one can be active per Type/SubType/Language triplet. Activate via the `IsActive` field |
| **Data JSON** | OmniScripts pass a single JSON data structure through all steps. Elements read from and write to this shared JSON via merge field syntax |

---

## Workflow Design (5-Phase Pattern)

### Phase 1: Requirements Gathering

**Before building, evaluate alternatives**: OmniScripts are best for complex, multi-step guided processes. For simple single-screen data entry, consider Screen Flows. For data display without interaction, consider FlexCards.

**Ask the user** to gather:
- **Type**: The process category (e.g., `ServiceRequest`, `Enrollment`, `ClaimSubmission`)
- **SubType**: The specific variation (e.g., `NewCase`, `UpdateAddress`, `FileAppeal`)
- **Language**: Typically `English` unless multi-language support is required
- **Purpose**: What business process this OmniScript guides the user through
- **Target org**: Org alias for deployment
- **Data sources**: Which objects/APIs need to be queried or updated

**Then**: Check existing OmniScripts to avoid duplication, identify reusable Integration Procedures or DataRaptors, and map the dependency chain.

### Phase 2: Design & Element Selection

Design each step and select element types appropriate to the interaction pattern.

#### Container Elements

| Element Type | Purpose | Key Config |
|-------------|---------|------------|
| **Step** | Top-level container for a group of UI elements; each Step is a page in the wizard | `chartLabel`, `knowledgeOptions`, `show` (conditional visibility) |
| **Block** (conditional) | Show/hide a group of elements based on conditions | `conditionType`, `show` expression |
| **Block** (repeat) | Repeat a group of elements for each item in a data list | `repeat: true` (bound to the data JSON array with the Block's name), `repeatLimit` |
| **Edit Block** | Inline editing container for tabular data | `editFields`, `dataSource` |

#### Input Elements

| Element Type | Purpose | Key Config |
|-------------|---------|------------|
| **Text** | Single-line text input | `label`, `placeholder`, `pattern` (regex validation), `ptrnErrText` |
| **Text Area** | Multi-line text input | `label`, `maxLength`, `rows` |
| **Number** | Numeric input with optional formatting | `label`, `min`, `max`, `step`, `format` |
| **Date** | Date picker | `label`, `dateFormat`, `minDate`, `maxDate` |
| **Date/Time (Local)** | Date and time picker | `label`, `dateFormat`, `timeFormat` |
| **Checkbox** | Boolean toggle | `label`, `defaultValue` |
| **Radio** | Radio button group for single selection | `label`, `options` (static or data-driven) |
| **Select** | Dropdown selection | `label`, `options`, `optionSource` (static/data) |
| **Multi-select** | Multiple item selection | `label`, `options`, `optionSource` |
| **Type Ahead Block** | Search/autocomplete input | `label`, `typeAheadKey`, `useDataJson`, `dataJsonPath`, `minSearchLength`, `enableLookup` |
| **Signature** | Signature capture pad | `label` |
| **File** | File upload | `label`, `fileSizeLimit` (MB), `fileExtension`, `allowMultiple`, `uploadContDoc` |
| **Currency** | Currency input with locale formatting | `label`, `currencyCode`, `min`, `max` |
| **Email** | Email input with format validation | `label`, `placeholder` |
| **Telephone** | Phone number input with masking | `label`, `mask`, `placeholder` |
| **URL** | URL input with format validation | `label`, `placeholder` |
| **Password** | Masked text input | `label`, `minLength` |
| **Range** | Slider input | `label`, `min`, `max`, `step` |
| **Time** | Time picker | `label`, `timeFormat` |

#### Display Elements

| Element Type | Purpose | Key Config |
|-------------|---------|------------|
| **Text Block** | Static content display (HTML supported) | `text`, `sanitize`, `HTMLTemplateId` |
| **Headline** | Section heading | `text`, `level` (h1-h6) |
| **Aggregate** | Calculated summary display | `aggregateExpression`, `format` |
| **Disclosure** | Expandable/collapsible content | `label`, `defaultExpanded` |
| **Image** | Image display | `imageURL`, `altText` |

#### Action Elements

| Element Type | Purpose | Key Config |
|-------------|---------|------------|
| **DataRaptor Extract Action** | Pull data from Salesforce | `bundle`, `dataRaptor Input Parameters`, `responseJSONPath`, `responseJSONNode` |
| **DataRaptor Post Action** | Push data to Salesforce (Load Data Mapper) | `bundle`, `sendJSONPath`, `sendJSONNode` |
| **Integration Procedure Action** | Call server-side Integration Procedure | `integrationProcedureKey` (Type_SubType), `extraPayload`, `sendOnlyExtraPayload`, `sendJSONPath`, `responseJSONPath`, `responseJSONNode`, `remoteOptions` |
| **Remote Action** | Call an Apex class (`Callable` / `VlocityOpenInterface`) method | `remoteClass`, `remoteMethod`, `extraPayload`, `sendOnlyExtraPayload`, `remoteOptions` |
| **Navigate Action** | Page navigation or redirection | `targetType`, `targetId`, `URL` |
| **DocuSign Envelope Action** | Trigger DocuSign envelope | `templateId`, `recipientMap` |
| **Email Action** | Send email | `emailTemplateId`, `recipientMap` |

#### Logic Elements

| Element Type | Purpose | Key Config |
|-------------|---------|------------|
| **Set Values** | Variable assignment and data transformation | `elementValueMap` (key-value pairs; prefix a value with `=` to evaluate it as a formula) |
| **Validation** | Input validation rules with custom messages | `validateExpression` (condition group), `messages` |
| **Formula** | Calculate values using formula expressions (functions: `references/formula-functions.md`) | `expression`, `dataType` |

There is no separate "Submit Action" element in OmniScripts: the final save is an Integration Procedure Action / DataRaptor Post Action / Remote Action (typically in or after the last Step).

### Phase 3: Generation & Validation

Run `scripts/check-duplicate-omniscript.sh <Type> <SubType> <Language> <org>` to verify no duplicate Type/SubType/Language exists.

**Build the OmniScript**:
1. Create the OmniProcess record with Type, SubType, Language, and IsIntegrationProcedure=false (OmniProcessType is derived)
2. Create OmniProcessElement child records for each Step (Level=0)
3. Create OmniProcessElement child records for each element within Steps (Level=1+, `ParentElementId` = parent, ordered by `SequenceNumber`)
4. Configure PropertySetConfig JSON for each element
5. Wire action elements to their Integration Procedures / DataRaptors

**Validation (STRICT MODE)**:
- **BLOCK**: Missing Type/SubType/Language, circular OmniScript embedding, broken IP/DataRaptor references, missing required PropertySetConfig fields
- **WARN**: Steps with no elements, input elements without validation, missing error handling on actions, unused data paths, deeply nested elements (>4 levels)

**Validation Report Format** (6-Category Scoring 0-120):
```yaml
Score: 102/120 ---- Very Good
-- Design & Structure: 22/25 (88%)
-- Data Integration: 18/20 (90%)
-- Error Handling: 17/20 (85%)
-- Performance: 18/20 (90%)
-- User Experience: 17/20 (85%)
-- Security: 10/15 (67%)
```

### Phase 4: Deployment

1. **Prerequisites**: Verify org auth (`sf org display -o <org>`). Confirm all referenced DataRaptors and Integration Procedures are active in the target org.
2. Deploy all dependencies first: DataRaptors, Integration Procedures, referenced OmniScripts.
3. Run `scripts/deploy-omniscript.sh <Type> <SubType> <Language> <Version> <org>` — this deploys the OmniScript (metadata member `<Type>_<SubType>_<Language>_<Version>`) and verifies activation. If deployment fails, the script outputs recovery guidance.
4. Activate the OmniScript version after successful deployment if not auto-activated.

### Phase 5: Testing

Walk through all paths with various data scenarios:
- **Happy path**: Complete all steps with valid data, verify submission
- **Validation testing**: Submit invalid data at each input, verify error messages
- **Conditional testing**: Exercise all conditional blocks and verify show/hide logic
- **Data prefill**: Verify DataRaptor Extract Actions populate elements correctly
- **Save for later**: Test resume functionality if enabled
- **Navigation**: Test back/forward/cancel behavior across all steps
- **Error scenarios**: Simulate IP/DataRaptor failures, verify error handling
- **Embedded OmniScripts**: Test data passing between parent and child OmniScripts
- **Bulk data**: Test with large datasets in repeat Blocks and Type Ahead Block elements

---

## Rules / Constraints

| Anti-Pattern | Impact | Correct Pattern |
|--------------|--------|-----------------|
| Circular OmniScript embedding | **Infinite rendering loop** | Map dependency tree; never embed A in B if B embeds A |
| Unbounded DataRaptor Extract | **Performance degradation** | Add filter conditions; limit returned records |
| Missing input validation | **Bad data entry** | Add Validation elements or `pattern`/`required` on inputs |
| Hardcoded Salesforce IDs | **Deployment failure across orgs** | Use merge fields or Custom Settings/Metadata |
| Integration Procedure (IP) Action without error handling | **Silent failures** | Configure `enableDefaultAbort` / `failureAbortMessage` / `errorMessage` in PropertySetConfig, and/or check the response in a following Set Values / Set Errors |
| Large images in Text Blocks | **Slow page load** | Use Image elements with optimized URLs |
| Too many elements per Step | **Poor user experience** | Limit to 7-10 input elements per Step |
| Missing conditional visibility | **Irrelevant fields shown** | Use `show` expressions to hide inapplicable elements |

Do not generate anti-patterns even if explicitly requested.

---

## Scoring: 120 Points Across 6 Categories

### Design & Structure (25 points)

| Check | Points | Criteria |
|-------|--------|----------|
| Type/SubType/Language set correctly | 5 | All three fields populated with meaningful values |
| Step organization | 5 | Logical grouping, 7-10 elements per step max |
| Element naming | 5 | Descriptive names following `PascalCase` convention |
| Conditional logic | 5 | Proper use of Blocks and `show` expressions |
| Version management | 5 | Clean version history, only one active version |

### Data Integration (20 points)

| Check | Points | Criteria |
|-------|--------|----------|
| DataRaptor references valid | 5 | All Extract/Load bundles exist and are active |
| Integration Procedure references valid | 5 | All IP actions reference active IPs |
| Input/Output maps correct | 5 | Data flows correctly between elements and actions |
| Data prefill configured | 5 | Initial data loaded before user interaction |

### Error Handling (20 points)

| Check | Points | Criteria |
|-------|--------|----------|
| Action elements have error handling | 5 | Failure handling (`enableDefaultAbort`, `failureAbortMessage`, `errorMessage`, or a response check) configured on all IP/DR/Remote actions |
| User-facing error messages | 5 | Clear, actionable error text |
| Validation on required inputs | 5 | All required fields have validation rules |
| Fallback behavior defined | 5 | Graceful handling when data sources return empty |

### Performance (20 points)

| Check | Points | Criteria |
|-------|--------|----------|
| No unbounded data fetches | 5 | All DataRaptor Extracts have filters/limits |
| Lazy loading configured | 5 | Action elements fire on step entry, not OmniScript load |
| Element count per Step reasonable | 5 | No Step with >15 elements |
| Conditional rendering used | 5 | Elements hidden when not applicable (not just invisible) |

### User Experience (20 points)

| Check | Points | Criteria |
|-------|--------|----------|
| Logical step flow | 5 | Steps follow natural task progression |
| Input labels and help text | 5 | All inputs have clear labels and contextual help |
| Navigation controls | 5 | Back, Next, Cancel, Save for Later configured appropriately |
| Responsive layout | 5 | Elements configured for mobile and desktop breakpoints |

### Security (15 points)

| Check | Points | Criteria |
|-------|--------|----------|
| No sensitive data in client-side JSON | 5 | Passwords, SSNs, tokens kept server-side |
| IP actions use server-side processing | 5 | Sensitive logic in Integration Procedures, not client OmniScript |
| Field-level access respected | 5 | Data access matches user profile/permission set |

---

## CLI Commands

See `scripts/cli-reference.sh` for the full command reference. Common commands:

```bash
# List active OmniScripts
sf data query -q "SELECT Id,Name,Type,SubType,Language,IsActive,VersionNumber FROM OmniProcess WHERE IsActive=true AND OmniProcessType='OmniScript' LIMIT 50" -o <org>

# Query elements for a specific OmniScript
sf data query -q "SELECT Id,Name,Type,Level,SequenceNumber,ParentElementId FROM OmniProcessElement WHERE OmniProcessId='<id>' ORDER BY Level,SequenceNumber LIMIT 200" -o <org>

# Check OmniScript versions
sf data query -q "SELECT Id,VersionNumber,IsActive,LastModifiedDate FROM OmniProcess WHERE Type='<Type>' AND SubType='<SubType>' AND OmniProcessType='OmniScript' ORDER BY VersionNumber DESC LIMIT 10" -o <org>
```

---

## Cross-Skill Integration

| From Skill | To omnistudio-omniscript-generate | When |
|------------|------------------|------|
| omnistudio-dependencies-analyze | -> omnistudio-omniscript-generate | "Analyze dependencies before building OmniScript" |
| omnistudio-datamapper-generate | -> omnistudio-omniscript-generate | "DataRaptor ready, build the OmniScript that uses it" |
| omnistudio-integration-procedure-generate | -> omnistudio-omniscript-generate | "IP ready, wire it into the OmniScript action" |

| From omnistudio-omniscript-generate | To Skill | When |
|--------------------|----------|------|
| omnistudio-omniscript-generate | -> omnistudio-flexcard-generate | "Build FlexCard that launches this OmniScript" |
| omnistudio-omniscript-generate | -> platform-metadata-deploy | "Deploy OmniScript to target org" |
| omnistudio-omniscript-generate | -> omnistudio-dependencies-analyze | "Map full dependency tree before deployment" |
| omnistudio-omniscript-generate | -> omnistudio-integration-procedure-generate | "Need a new IP for this OmniScript action" |
| omnistudio-omniscript-generate | -> omnistudio-datamapper-generate | "Need a DataRaptor for data prefill" |

---

## Gotchas

| Issue | Resolution |
|-------|-----------|
| Multi-language OmniScript | Create separate versions per Language with shared Type/SubType; use translation workbench for labels |
| Embedded OmniScript data passing | An embedded OmniScript shares the parent's data JSON — the child reads parent keys directly; use matching key names (or a Set Values before the embed); test data round-trip |
| Large repeat Block datasets | Paginate or limit DataRaptor results; consider server-side filtering in Integration Procedure (IP) |
| OmniScript in FlexCard flyout | Ensure FlexCard passes required context data; test flyout sizing |
| Community/Experience Cloud deployment | Verify OmniScript component is available in Experience Builder; check guest user permissions |
| Save & Resume (Save for Later) | Configure `saveNameTemplate`, `saveExpireInDays`; test resume with partial data |
| Versioning conflicts | Deactivate old version before activating new; never have two active versions for same Type/SubType/Language triplet |
| Custom LWC in OmniScript | Extend `OmniscriptBaseMixin` (import from `omnistudio/omniscriptBaseMixin`) and set `<runtimeNamespace>omnistudio</runtimeNamespace>` in the LWC's `.js-meta.xml` |
| Namespaced orgs | Orgs on standard OmniStudio objects use un-prefixed names (`OmniProcess`, `OmniScript` metadata). Only managed-package custom-object orgs (`vlocity_cmt__`, `vlocity_ins__`, `omnistudio__` objects) need namespace prefixes, and they use Vlocity Build DataPacks instead of Metadata API |
| `OmniProcessType` cannot be set on create | `OmniProcessType` is computed from `IsIntegrationProcedure` (false for OmniScripts); do not set it directly |

For common runtime troubleshooting (element not rendering, data not prefilling, IP action failing silently), see `references/best-practices.md` Section 8.

---

## Notes

**API**: 66.0 | **Mode**: Strict (warnings block) | **Scoring**: Block deployment if score < 67

**Required upstream skills**: `omnistudio-datamapper-generate`, `omnistudio-integration-procedure-generate`

**Optional skills**: `platform-metadata-deploy`, `omnistudio-flexcard-generate`, `omnistudio-dependencies-analyze`

**Creating OmniScripts programmatically**: Use REST API (`sf api request rest --method POST --body @file.json`). Required fields: `Name`, `Type`, `SubType`, `Language`, `VersionNumber`. OmniScripts default to `IsIntegrationProcedure=false` — do NOT set `OmniProcessType` directly (it is computed). The `sf data create record --values` flag cannot handle JSON textarea fields like `PropertySetConfig`. Create child `OmniProcessElement` records via REST API for each Step and element.

---

## Output Expectations

Deliverables produced by this skill:

- **OmniScript JSON** (`assets/omni-process-omniscript.json` template) — OmniProcess record ready for REST API creation
- **Step element JSON** (`assets/omni-process-element-step.json` template) — OmniProcessElement record for each Step (Level=0)
- **Element JSON** (`assets/omni-process-element-text-block.json` and similar) — OmniProcessElement records for child elements (Level=1+)
- **Validation report** — 120-point score across 6 categories with pass/warn/block threshold result

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/element-types.md` | Phase 2 — Element selection: read before configuring PropertySetConfig for any element type |
| `references/best-practices.md` | Phase 2-5 — Design patterns: read for step design, data prefill, validation, navigation, performance, and troubleshooting guidance |
| `references/formula-functions.md` | Phase 2-3 — Read before writing any Formula / Aggregate expression or `=` Set Values value; lists the supported OmniScript functions and known gotchas |
| `assets/omni-process-omniscript.json` | Phase 3 — Generation: use as the OmniProcess record template when building the OmniScript via REST API |
| `assets/omni-process-element-step.json` | Phase 3 — Generation: use as the Step (Level=0) OmniProcessElement record template |
| `assets/omni-process-element-text-block.json` | Phase 3 — Generation: use as the Text Block element template; adapt for other display element types |
| `scripts/check-duplicate-omniscript.sh` | Phase 3 — Run before creating a new OmniScript to verify no duplicate Type/SubType/Language exists |
| `scripts/deploy-omniscript.sh` | Phase 4 — Run to deploy OmniScript and verify activation; includes prerequisite checks and recovery guidance |
| `scripts/cli-reference.sh` | Any phase — Full CLI command reference for querying, retrieving, deploying, and verifying OmniScripts |
