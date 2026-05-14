---
name: building-omnistudio-datamapper
description: "OmniStudio Data Mapper (formerly DataRaptor) creation and validation with 100-point scoring. Use when building Extract, Transform, Load, or Turbo Extract Data Mappers, mapping Salesforce object fields, or reviewing existing Data Mapper configurations. TRIGGER when: user creates Data Mappers, configures field mappings, works with OmniDataTransform metadata, or asks about DataRaptor/Data Mapper patterns. DO NOT TRIGGER when: building Integration Procedures (use building-omnistudio-integration-procedure), authoring OmniScripts (use building-omnistudio-omniscript), or analyzing cross-component dependencies (use analyzing-omnistudio-dependencies)."
license: MIT
metadata:
  version: "1.0"
---

# building-omnistudio-datamapper: OmniStudio Data Mapper Creation and Validation

Expert OmniStudio Data Mapper developer specializing in Extract, Transform, Load, and Turbo Extract configurations. Generate production-ready, performant, and maintainable Data Mapper definitions with proper field mappings, query optimization, and data integrity safeguards.

---

## Scope

- **In scope**: Creating and validating OmniStudio Data Mapper configurations (Extract, Transform, Load, Turbo Extract); field mapping design; query optimization; FLS (Field-Level Security) validation; deployment via deploying-metadata skill
- **Out of scope**: Building Integration Procedures (use `building-omnistudio-integration-procedure`), authoring OmniScripts (use `building-omnistudio-omniscript`), designing FlexCards (use `building-omnistudio-flexcard`), analyzing cross-component dependencies (use `analyzing-omnistudio-dependencies`)

---

## Core Responsibilities

1. **Generation**: Create Data Mapper configurations (Extract, Transform, Load, Turbo Extract) from requirements
2. **Field Mapping**: Design object-to-output field mappings with proper type handling, lookup resolution, and null safety
3. **Dependency Tracking**: Identify related OmniStudio components (Integration Procedures, OmniScripts, FlexCards) that consume or feed Data Mappers
4. **Validation & Scoring**: Score Data Mapper configurations against 5 categories (0-100 points)

---

## CRITICAL: Orchestration Order

**analyzing-omnistudio-dependencies -> building-omnistudio-datamapper -> building-omnistudio-integration-procedure -> building-omnistudio-omniscript -> building-omnistudio-flexcard** (you are here: building-omnistudio-datamapper)

Data Mappers are the data access layer of the OmniStudio stack. They must be created and deployed before Integration Procedures or OmniScripts that reference them. Use analyzing-omnistudio-dependencies FIRST to understand existing component dependencies.

---

## Key Insights

| Insight | Details |
|---------|---------|
| **Extract vs Turbo Extract** | Extract uses standard SOQL with relationship queries. Turbo Extract uses server-side compiled queries for read-heavy, high-volume scenarios (10x+ faster). Turbo Extract does not support formula fields, related lists, or write operations. |
| **Transform is in-memory** | Transform Data Mappers operate entirely in memory with no DML or SOQL. They reshape data structures between steps in an Integration Procedure. Use for JSON-to-JSON transformations, field renaming, and data flattening. |
| **Load = DML** | Load Data Mappers perform insert, update, upsert, or delete operations. They require proper FLS checks and error handling. Always validate field-level security before deploying Load Data Mappers to production. |
| **OmniDataTransform metadata** | Data Mappers are stored as OmniDataTransform and OmniDataTransformItem records. Retrieve and deploy using these metadata type names, not the legacy DataRaptor API names. |

---

## Workflow (5-Phase Pattern)

### Phase 1: Requirements Gathering

**Ask the user** to gather:
- Data Mapper type (Extract, Transform, Load, Turbo Extract)
- Target Salesforce object(s) and fields
- Target org alias
- Consuming component (Integration Procedure, OmniScript, or FlexCard name)
- Data volume expectations (record counts, frequency)

**Then**:
1. Check existing Data Mappers: `Glob: **/OmniDataTransform*`
2. Check existing OmniStudio metadata: `Glob: **/omnistudio/**`
3. Create a task list

---

### Phase 2: Design & Type Selection

| Type | Use Case | Naming Prefix | Supports DML | Supports SOQL |
|------|----------|---------------|--------------|---------------|
| **Extract** | Read data from one or more objects with relationship queries | `DR_Extract_` | No | Yes |
| **Turbo Extract** | High-volume read-only queries, server-side compiled | `DR_TurboExtract_` | No | Yes (compiled) |
| **Transform** | In-memory data reshaping between procedure steps | `DR_Transform_` | No | No |
| **Load** | Write data (insert, update, upsert, delete) | `DR_Load_` | Yes | No |

**Naming Format**: `[Prefix][Object]_[Purpose]` using PascalCase

**Examples**:
- `DR_Extract_Account_Details` -- Extract Account with related Contacts
- `DR_TurboExtract_Case_List` -- High-volume Case list for FlexCard
- `DR_Transform_Lead_Flatten` -- Flatten nested Lead data structure
- `DR_Load_Opportunity_Create` -- Insert Opportunity records

---

### Phase 3: Generation & Validation

**For Generation**:
1. Read `assets/omni-data-transform-extract.json` (Extract), `assets/omni-data-transform-transform.json` (Transform), or `assets/omni-data-transform-load.json` (Load) for the OmniDataTransform record template
2. Read `assets/omni-data-transform-item.json` for each field mapping (OmniDataTransformItem) template
3. Configure query filters, sort order, and limits for Extract types
4. Set up lookup mappings and default values for Load types
5. Validate field-level security for all mapped fields

**For Review**:
1. Read existing Data Mapper configuration
2. Run validation against best practices
3. Generate improvement report with specific fixes

**Run Validation**: Read `assets/completion-summary-template.md` for the scoring output format and thresholds.

---

### Generation Guardrails (MANDATORY)

**BEFORE generating ANY Data Mapper configuration, Claude MUST verify no anti-patterns are introduced.**

If ANY of these patterns would be generated, **STOP and ask the user**:
> "I noticed [pattern]. This will cause [problem]. Should I:
> A) Refactor to use [correct pattern]
> B) Proceed anyway (not recommended)"

| Anti-Pattern | Detection | Impact |
|--------------|-----------|--------|
| Extracting all fields | No field list specified, wildcard selection | Performance degradation, excessive data transfer |
| Missing lookup mappings | Load references lookup field without resolution | DML failure, null foreign key |
| Writing without FLS check | Load Data Mapper with no security validation | Security violation, data corruption in restricted profiles |
| Unbounded Extract query | No LIMIT or filter on Extract | Governor limit failure, timeout on large objects |
| Transform with side effects | Transform attempting DML or callout | Runtime error, Transform is in-memory only |
| Hardcoded record IDs | 15/18-char ID literal in filter or mapping | Deployment failure across environments |
| Nested relationship depth >3 | Extract with deeply nested parent traversal | Query performance degradation, SOQL complexity limits |
| Load without error handling | No upsert key or duplicate rule consideration | Silent data corruption, duplicate records |

**DO NOT generate anti-patterns even if explicitly requested.** Ask user to confirm the exception with documented justification.

**See**: [references/best-practices.md](references/best-practices.md) for detailed patterns
**See**: [references/naming-conventions.md](references/naming-conventions.md) for naming rules

---

### Phase 4: Deployment

**Step 1: Validation**
Use the **deploying-metadata** skill: "Deploy OmniDataTransform [Name] to [target-org] with --dry-run"

**Step 2: Deploy** (only if validation succeeds)
Use the **deploying-metadata** skill: "Proceed with actual deployment to [target-org]"

**Post-Deploy**: Activate the Data Mapper in the target org. Verify it appears in OmniStudio Designer.

**If deploy fails**: Check error for specific cause — common issues: `Entity cannot be found` (Data Mapper is in Draft status; activate first), namespace prefix mismatch (check `sfdx-project.json`), or missing parent `OmniDataTransform` record for item deployments.

**If Load DM fails at runtime**: Check debug logs via `sf apex log list -o <org>`; verify FLS and object permissions for the running user profile; confirm the upsert key field is populated and unique; Salesforce Load DMs follow `allOrNone=false` by default — partial successes are possible, check for `isSuccess=false` rows in the response.

---

### Phase 5: Testing & Documentation

**Completion Summary**: Read `assets/completion-summary-template.md` for the completion summary format.

**Testing Checklist**:
- [ ] Preview data output in OmniStudio Designer
- [ ] Verify field mappings produce expected JSON structure
- [ ] Test with representative data volume (not just 1 record)
- [ ] Validate FLS enforcement with restricted profile user
- [ ] Confirm consuming Integration Procedure/OmniScript receives correct data shape

---

## Best Practices (100-Point Scoring)

| Category | Points | Key Rules |
|----------|--------|-----------|
| **Design & Naming** | 20 | Correct type selection; naming follows `DR_[Type]_[Object]_[Purpose]` convention; single responsibility per Data Mapper |
| **Field Mapping** | 25 | Explicit field list (no wildcards); correct input/output paths; proper type conversions; null-safe default values |
| **Data Integrity** | 25 | FLS validation on all fields; lookup resolution for Load types; upsert keys defined; duplicate handling configured |
| **Performance** | 15 | Bounded queries with LIMIT/filters; Turbo Extract for read-heavy scenarios; minimal relationship depth; indexed filter fields |
| **Documentation** | 15 | Description on OmniDataTransform record; field mapping rationale documented; consuming components identified |

**Thresholds**: ✅ 90+ (Deploy) | ⚠️ 67-89 (Review) | ❌ <67 (Block - fix required)

---

## CLI Commands

### Query Existing Data Mappers

```bash
sf data query -q "SELECT Id,Name,Type FROM OmniDataTransform LIMIT 200" -o <org>
```

### Query Data Mapper Field Mappings

```bash
sf data query -q "SELECT Id,Name,InputObjectName,OutputObjectName,LookupObjectName FROM OmniDataTransformItem WHERE OmniDataTransformationId='<id>' LIMIT 200" -o <org>
```

### Retrieve Data Mapper Metadata

```bash
sf project retrieve start -m OmniDataTransform:<Name> -o <org>
```

### Deploy Data Mapper Metadata

```bash
sf project deploy start -m OmniDataTransform:<Name> -o <org>
```

---

## Output Expectations

Deliverables produced by this skill:

- **OmniDataTransform record** — main Data Mapper record built from `assets/omni-data-transform-*.json` template
- **OmniDataTransformItem records** — one per mapped field, built from `assets/omni-data-transform-item.json` template
- **Validation score report** — 100-point score across 5 categories (format in `assets/completion-summary-template.md`)
- **Deployment confirmation** — Data Mapper activated and visible in OmniStudio Designer

---

## Cross-Skill Integration

| From Skill | To building-omnistudio-datamapper | When |
|------------|------------------|------|
| analyzing-omnistudio-dependencies | -> building-omnistudio-datamapper | "Analyze dependencies before creating Data Mapper" |
| generating-custom-object / generating-custom-field | -> building-omnistudio-datamapper | "Describe target object fields before mapping" |
| querying-soql | -> building-omnistudio-datamapper | "Validate Extract query logic" |

| From building-omnistudio-datamapper | To Skill | When |
|--------------------|----------|------|
| building-omnistudio-datamapper | -> building-omnistudio-integration-procedure | "Create Integration Procedure that calls this Data Mapper" |
| building-omnistudio-datamapper | -> deploying-metadata | "Deploy Data Mapper to target org" |
| building-omnistudio-datamapper | -> building-omnistudio-omniscript | "Wire Data Mapper output into OmniScript" |
| building-omnistudio-datamapper | -> building-omnistudio-flexcard | "Display Data Mapper Extract results in FlexCard" |

---

## Gotchas

| Issue | Resolution |
|-------|-----------|
| Large data volume (>10K records) | Use Turbo Extract; add pagination via Integration Procedure; warn about heap limits |
| Polymorphic lookup fields | Specify the concrete object type in the mapping; test each type separately |
| Formula fields in Extract | Standard Extract supports formula fields; Turbo Extract does not — fall back to standard Extract |
| Cross-object Load (master-detail) | Insert parent records first, then child records in a separate Load step; use Integration Procedure to orchestrate sequence |
| Namespace-prefixed fields | Include namespace prefix in field paths (e.g., `ns__Field__c`); verify prefix matches target org |
| Multi-currency orgs | Map CurrencyIsoCode explicitly; do not rely on default currency assumption |
| RecordType-dependent mappings | Filter by RecordType in Extract; set RecordTypeId in Load; document which RecordTypes are supported |
| Draft Data Mapper not retrievable | `sf project retrieve start -m OmniDataTransform:<Name>` only works for active DMs; activate before retrieving |
| Foreign key field name wrong | The parent lookup on `OmniDataTransformItem` is `OmniDataTransformationId` (full word "Transformation"), not `OmniDataTransformId` |

---

## Notes

- **Metadata Type**: OmniDataTransform (not DataRaptor — legacy name deprecated)
- **API Version**: Requires OmniStudio managed package or Industries Cloud
- **Scoring**: Block deployment if score < 67; read `assets/completion-summary-template.md` for score format
- **Turbo Extract Limitations**: No formula fields, no related lists, no aggregate queries, no polymorphic fields
- **Activation**: Data Mappers must be activated after deployment to be callable from Integration Procedures (see Gotchas for draft retrieval behavior)
- **Creating via Data API**: Use `sf api request rest --method POST --body @file.json` to create OmniDataTransform and OmniDataTransformItem records. The `sf data create record --values` flag cannot handle JSON in textarea fields. Write the JSON body to a temp file first.

---

## Reference File Index

| File | When to Read |
|------|-------------|
| `assets/omni-data-transform-extract.json` | Phase 3 Generation — template for Extract type OmniDataTransform records |
| `assets/omni-data-transform-transform.json` | Phase 3 Generation — template for Transform type OmniDataTransform records |
| `assets/omni-data-transform-load.json` | Phase 3 Generation — template for Load type OmniDataTransform records |
| `assets/omni-data-transform-item.json` | Phase 3 Generation — template for each OmniDataTransformItem field mapping |
| `assets/completion-summary-template.md` | Phase 3 & 5 — scoring output format and completion summary template |
| `references/best-practices.md` | Phase 3 Guardrails — detailed patterns for field mapping, query optimization, null handling, and performance |
| `references/naming-conventions.md` | Phase 2 Design — full naming rules for all Data Mapper types and field mapping conventions |

---
