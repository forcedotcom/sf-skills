---
name: modeling-omnistudio-epc-catalog
description: "Salesforce Industries CME EPC product-modeling skill for Product2-based catalog creation. Use when creating EPC products, configuring product attributes, building offer bundles with Product Child Items, or reviewing EPC DataPack JSON metadata for product catalog changes. TRIGGER when: user creates or updates Product2 EPC records, AttributeAssignment payloads, AttributeMetadata/AttributeDefaultValues, Offer bundles, or ProductChildItem relationships. DO NOT TRIGGER when: designing OmniScripts/FlexCards/Integration Procedures (use building-omnistudio-omniscript, building-omnistudio-flexcard, or building-omnistudio-integration-procedure), implementing Apex business logic (use generating-apex), or troubleshooting deployment pipelines (use deploying-metadata)."
license: MIT
metadata:
  version: "1.0"
---

# modeling-omnistudio-epc-catalog: CME EPC Product and Offer Modeling

Expert Salesforce Industries CME EPC modeler for creating Product2-based catalog entries, assigning configurable attributes, and building offer bundles through Product Child Item relationships.

This skill is optimized for DataPack-style metadata authoring. Use the canonical template set in `assets/`:

- `assets/product2-offer-template.json`
- `assets/attribute-assignment-template.json`
- `assets/product-child-item-template.json`
- `assets/pricebook-entries-template.json`
- `assets/price-list-entries-template.json`
- `assets/object-field-attributes-template.json`
- `assets/orchestration-scenarios-template.json`
- `assets/decomposition-relationships-template.json`
- `assets/compiled-attribute-overrides-template.json`
- `assets/override-definitions-template.json`
- `assets/parent-keys-template.json`

Additional packaged examples are available under `assets/examples/`, organized by offer type:

- `assets/examples/samsung-galaxy-s22-bundle/` — bundle offer example
- `assets/examples/business-internet-premium-fttc-simple-offer/` — simple offer example
- `assets/examples/business-internet-pro-vpl-simple-offer/` — simple offer example
- `assets/examples/static-ip-simple-offer/` — simple offer example

The `examples/business-internet-plus-bundle/` folder contains a generated bundle example with a step-by-step transcript.

The root `assets/` folder contains the canonical baseline template set for bundle authoring.

---

## Scope

- **In scope**: Creating and reviewing EPC Product2 records, Product Child Items, attribute metadata, offer bundles, pricing entries, decomposition and orchestration artifacts, and DataPack JSON payloads
- **Out of scope**: OmniScript/FlexCard/Integration Procedure design (use `building-omnistudio-omniscript`, `building-omnistudio-flexcard`, or `building-omnistudio-integration-procedure`), Apex business logic implementation (use `generating-apex`), deployment pipeline troubleshooting (use `deploying-metadata`)

---

## Quick Reference

- **Primary object**: `Product2` (EPC product and offer records)
- **Attribute data**: `%vlocity_namespace%__AttributeMetadata__c`, `%vlocity_namespace%__AttributeDefaultValues__c`, and `%vlocity_namespace%__AttributeAssignment__c`
- **Offer bundle composition**: `%vlocity_namespace%__ProductChildItem__c`
- **Offer marker**: `%vlocity_namespace%__SpecificationType__c = "Offer"` and `%vlocity_namespace%__SpecificationSubType__c = "Bundle"`
- **Companion bundle artifacts**: pricebook entries, price list entries, object field attributes, orchestration scenarios, decomposition relationships, compiled attribute overrides, override definitions, and parent keys

**Scoring**: 120 points across 6 categories.  
**Thresholds**: `>= 95` Deploy-ready | `70-94` Needs review | `< 70` Block and fix.

**Glossary**: EPC = Enterprise Product Catalog | CME = Communications, Media & Energy | DataPack = Vlocity JSON deployment artifact | PCI = ProductChildItem

---

## Asset Template Set

Use the root `assets/` templates when creating a bundle payload:

- `product2-offer-template.json`
- `attribute-assignment-template.json`
- `product-child-item-template.json`
- `pricebook-entries-template.json`
- `price-list-entries-template.json`
- `object-field-attributes-template.json`
- `orchestration-scenarios-template.json`
- `decomposition-relationships-template.json`
- `compiled-attribute-overrides-template.json`
- `override-definitions-template.json`
- `parent-keys-template.json`

For additional real-world variants, use the per-example folders under `assets/examples/`.

---

## Core Responsibilities

1. **Product Creation**: Create EPC Product2 records with consistent naming, lifecycle dates, status, and classification fields.
2. **Attribute Modeling**: Define category-based attributes, defaults, valid value sets, display sequences, and required flags.
3. **Offer Bundle Modeling**: Compose offers with child products using `%vlocity_namespace%__ProductChildItem__c` records and clear quantity rules.
4. **Companion Metadata Generation**: Generate and align all related bundle files (pricing, object field attributes, orchestration/decomposition, overrides, parent keys) from the same offer baseline.
5. **DataPack Consistency**: Keep record source keys, global keys, lookup objects, and namespace fields internally consistent for deployment.

---

## Invocation Rules (Mandatory)

Route to this skill whenever the prompt intent matches either of these:

1. **Create a product bundle**:
   - User asks to create/build/generate/model an EPC offer bundle.
   - User asks for Product2 offer setup with Product Child Items.
   - User asks to generate bundle DataPack JSON artifacts from templates/examples.

2. **Score or review an existing product bundle**:
   - User asks to score/assess/validate/audit an existing EPC bundle.
   - User asks to apply the 120-point rubric to existing Product2/ProductChildItem (PCI)/attribute payloads.
   - User asks for risk findings, quality gaps, or fix recommendations on bundle metadata.

**Instruction priority**: treat these two intents as direct triggers for `modeling-omnistudio-epc-catalog`, even if the prompt is brief and does not mention EPC by name.

---

## Workflow (Create/Review)

### Phase 0: Prerequisites

Before proceeding, verify:

1. Salesforce Industries org with EPC enabled
2. Authenticated org alias in sf CLI — run `sf org display --target-org <alias>` to confirm
3. Namespace model identified: `%vlocity_namespace%`, `vlocity_cmt`, or Core

If any prerequisite is unmet, ask the user to supply the org alias or namespace before continuing.

---

### Phase 1: Identify Catalog Intent

Ask for:

- Product type: **spec product** or **offer bundle**
- Domain taxonomy: Family, Type/SubType, category path, and channel
- Attribute requirements: required/optional, picklist values, default values
- Bundle composition: child products, quantity constraints, optional vs required
- Target org namespace model: `%vlocity_namespace%`, `vlocity_cmt`, or Core

**Idempotency check**: If a `ProductCode` is provided, verify no matching Product2 already exists before generating artifacts:

```bash
sf data query --query "SELECT Id, Name, ProductCode FROM Product2 WHERE ProductCode = '<code>'" --target-org <alias>
```

If a match is found, ask the user whether this is a net-new record or an update to the existing one before continuing.

### Phase 1A: Clarifying Questions for Complete Bundle (Mandatory)

Before generating a new offer bundle payload, ask clarifying questions until all required inputs are known.

Required clarification checklist:

1. **Offer identity**
   - What is the offer name and `ProductCode`?
   - Is this net-new or an update to an existing Product2 offer?
2. **Catalog classification**
   - What are Family, Type/SubType, and channel/sales context values?
   - Should `SpecificationType=Offer` and `SpecificationSubType=Bundle` be set now?
3. **Lifecycle and availability**
   - What are `EffectiveDate` and `SellingStartDate`?
   - Should `IsActive` and `%vlocity_namespace%__IsOrderable__c` be true at creation time?
4. **Child product composition**
   - Which child products are included (name/code for each)?
   - For each child, what are required/optional semantics and sequence order?
5. **Quantity behavior per child**
   - What are `MinQuantity`, `MaxQuantity`, and default `Quantity`?
   - Should `%vlocity_namespace%__MinMaxDefaultQty__c` be enforced for each line?
6. **Attribute model**
   - Which attributes are required vs optional?
   - What are valid values, defaults, display types, and display sequences?
7. **Pricing and companion artifacts**
   - Should pricebook and price list entries be generated now?
   - Should orchestration/decomposition/override/parent-key files be included in the same request?
8. **Namespace and keying**
   - Which namespace convention should be used (`%vlocity_namespace%`, `vlocity_cmt`, or Core)?
   - Are there existing global keys/source keys to preserve?

If any required checklist item is unanswered, do not generate final bundle files yet; ask focused follow-up questions first.

### Phase 2: Build Product2 Backbone

For every new EPC record, define:

- `Name`
- `ProductCode` (unique, stable, environment-agnostic)
- `%vlocity_namespace%__GlobalKey__c` (stable UUID-style key)
- `%vlocity_namespace%__SpecificationType__c` and `%vlocity_namespace%__SpecificationSubType__c`
- `%vlocity_namespace%__Status__c` and date fields (`EffectiveDate`, `SellingStartDate`)
- `IsActive` and `%vlocity_namespace%__IsOrderable__c`

Use `assets/product2-offer-template.json` as baseline structure.

### Phase 3: Add Attributes

When attributes are required:

1. Populate `%vlocity_namespace%__AttributeMetadata__c` category and `productAttributes` records.
2. Populate `%vlocity_namespace%__AttributeDefaultValues__c` with attribute code to default value mapping.
3. Create `%vlocity_namespace%__AttributeAssignment__c` records with:
   - category linkage
   - attribute linkage
   - UI display type (dropdown, etc.)
   - valid values and default marker

Use `assets/attribute-assignment-template.json` as the assignment baseline.

### Phase 4: Build Offer Bundles

For offers:

1. Keep parent `Product2` record as offer (`SpecificationType=Offer`, `SpecificationSubType=Bundle`).
2. Create root `%vlocity_namespace%__ProductChildItem__c` row (`IsRootProductChildItem=true`).
3. Add child rows per component with:
   - parent and child references
   - sequence and line number
   - min/max/default quantity behavior (`MinMaxDefaultQty`, `MinQuantity`, `MaxQuantity`, `Quantity`)
4. Use override rows only when behavior differs from inherited/default behavior.

Use `assets/product-child-item-template.json` for child relationship structure.

For complete bundle payloads, also align and include:

- `assets/pricebook-entries-template.json`
- `assets/price-list-entries-template.json`
- `assets/object-field-attributes-template.json`
- `assets/orchestration-scenarios-template.json`
- `assets/decomposition-relationships-template.json`
- `assets/compiled-attribute-overrides-template.json`
- `assets/override-definitions-template.json`
- `assets/parent-keys-template.json`

### Phase 4B: Generate Companion Metadata Files

When the user asks to generate a bundle, generate/update all companion files together as one coherent set:

1. `pricebook-entries-template.json` and `price-list-entries-template.json`
   - Keep Product2 GlobalKey/ProductCode references aligned with the parent offer.
2. `object-field-attributes-template.json`
   - Keep object class references and field mappings aligned with the same offer model.
3. `orchestration-scenarios-template.json` and `decomposition-relationships-template.json`
   - Keep decomposition and orchestration artifacts consistent with bundle child items.
4. `compiled-attribute-overrides-template.json` and `override-definitions-template.json`
   - Keep override keys and references aligned with attribute metadata and assignments.
5. `parent-keys-template.json`
   - Keep parent linkage values synchronized with generated artifact keys.

**Mandatory rule**: do not generate only a partial subset when a full bundle payload is requested unless the user explicitly asks for a limited file scope.

### Phase 5: Validate and Handoff

Read `assets/completion-block-template.txt` and fill in each field to produce the handoff summary block.

---

## Output Expectations

For a full offer bundle request, the following files are produced:

| File pattern | Content |
|---|---|
| `*_DataPack.json` | Product2 offer record |
| `*_AttributeAssignments.json` | Attribute category and assignment payloads |
| `*_ProductChildItems.json` | Root and child ProductChildItem (PCI) rows |
| `*_PricebookEntries.json` | Standard and custom pricebook entries |
| `*_PriceListEntries.json` | Price list entries |
| `*_ObjectFieldAttributes.json` | Object field mapping |
| `*_OrchestrationScenarios.json` | Orchestration metadata |
| `*_DecompositionRelationships.json` | Decomposition metadata |
| `*_CompiledAttributeOverrides.json` | Compiled attribute override payload |
| `*_OverrideDefinitions.json` | Override definition payload |
| `*_ParentKeys.json` | Parent key linkage |

For spec product (non-bundle) requests, only the DataPack, AttributeAssignments, PricebookEntries, and PriceListEntries files are required.

If generation of any file fails, stop immediately. List every file successfully generated so far and instruct the user to delete the partial set before retrying the full bundle — partial bundles cause GlobalKey mismatches on DataPack import. Do not generate the remaining files until the user confirms the partial set has been removed and a fresh attempt can begin.

---

## Gotchas

| Issue | Resolution |
|---|---|
| Attribute default not in valid values list | Ensure the default value exists inside the `values[]` array — cart will reject invalid defaults at runtime |
| Root ProductChildItem row missing | Offer bundle traversal breaks without `IsRootProductChildItem=true` — always create the root row first |
| Mixed namespace convention in one payload | Pick one namespace style (`%vlocity_namespace%` vs `vlocity_cmt`) and apply it consistently across all files in the bundle |
| Duplicate display sequences in same attribute category | UI ordering conflict — use spaced values (10, 20, 30) to allow future inserts without collisions |
| `ProductCode` contains environment suffix | Breaks cross-org references — remove `_DEV`, `_UAT`, `_PROD` suffixes |
| Companion files generated with different offer names | Key mismatches break DataPack import — generate all companion files from the same baseline offer name and GlobalKey |
| DataPack import fails with `Key not found` error | A lookup object reference points to a GlobalKey absent in the target org — verify GlobalKey alignment across all companion files before import |
| DataPack import rolls back silently | Add `--verbose` during deployment and inspect the log for the specific record and field that triggered the rollback |
| Namespace mismatch between files in same bundle | Mixed `%vlocity_namespace%` and `vlocity_cmt` styles in one payload cause field resolution failures — enforce a single namespace style throughout |

---

## Generation Guardrails (Mandatory)

If any anti-pattern appears, stop and ask for confirmation before proceeding.

| Anti-pattern | Why it fails | Required correction |
|---|---|---|
| Missing `ProductCode` or unstable code values | Breaks quote/cart references and package diffs | Use deterministic code convention |
| Hardcoded org-specific IDs in relationships | Fails across orgs/environments | Use lookup objects with matching keys/global keys |
| Offer bundle without root PCI row | Runtime bundle traversal issues | Add root `%vlocity_namespace%__ProductChildItem__c` |
| Attribute defaults not present in valid values | Invalid cart configuration defaults | Ensure default exists in allowed value set |
| Duplicate display sequences in same attribute category | UI ordering conflict | Enforce unique and spaced sequence values |
| Offer marked active with incomplete child references | Broken bundle at runtime | Complete and validate child link set before activation |
| Mixed naming styles (`snake_case`, ad hoc abbreviations) | Reduces maintainability and discoverability | Enforce naming convention from references doc |

---

## Scoring Model (120 Points)

Read `references/scoring-model.md` for the full 6-category rubric and per-category criteria.

| Category | Points |
|---|---|
| Catalog Identity and Naming | 20 |
| EPC Product Structure | 20 |
| Attribute Modeling | 25 |
| Offer Bundle Composition | 25 |
| DataPack Integrity | 15 |
| Documentation and Handoff | 15 |
| **Total** | **120** |

---

## CLI and Validation Commands

Read `scripts/cli-validation-commands.sh` for sf CLI queries to inspect and validate EPC artifacts in your org. Replace `<org>` with your authenticated org alias before running.

---

## Sample Skill Invocation Commands

Read `scripts/sample-invocations.sh` for example invocations covering common EPC modeling tasks. Replace `cursor-agent` with your local agent command wrapper if different.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/product2-offer-template.json` | Phase 2 — baseline structure for every new Product2 offer record |
| `assets/attribute-assignment-template.json` | Phase 3 — attribute assignment structure |
| `assets/product-child-item-template.json` | Phase 4 — root and child PCI row structure |
| `assets/pricebook-entries-template.json` | Phase 4B — pricebook entry companion file |
| `assets/price-list-entries-template.json` | Phase 4B — price list entry companion file |
| `assets/object-field-attributes-template.json` | Phase 4B — object field mapping companion file |
| `assets/orchestration-scenarios-template.json` | Phase 4B — orchestration scenarios companion file |
| `assets/decomposition-relationships-template.json` | Phase 4B — decomposition relationships companion file |
| `assets/compiled-attribute-overrides-template.json` | Phase 4B — compiled attribute overrides companion file |
| `assets/override-definitions-template.json` | Phase 4B — override definitions companion file |
| `assets/parent-keys-template.json` | Phase 4B — parent keys companion file |
| `assets/completion-block-template.txt` | Phase 5 — handoff summary block template |
| `assets/examples/samsung-galaxy-s22-bundle/` | Phase 4 — bundle offer example; load `*_DataPack.json` and `*_ProductChildItems.json` first, then companion files as needed |
| `assets/examples/business-internet-premium-fttc-simple-offer/` | Phase 4 — simple offer (FTTC) example; load `*_DataPack.json` and `*_AttributeAssignments.json` first |
| `assets/examples/business-internet-premium-fttc-simple-offer/Business-Internet-Premium-FTTC_RuleAssignments.json` | Phase 4 — FTTC offer rule assignment example; load when modeling rule-based attribute constraints |
| `assets/examples/business-internet-pro-vpl-simple-offer/` | Phase 4 — simple offer (Pro VPL) example; load `*_DataPack.json` and `*_AttributeAssignments.json` first |
| `assets/examples/static-ip-simple-offer/` | Phase 4 — simple offer (Static IP) example; load `*_DataPack.json` and `*_AttributeAssignments.json` first |
| `examples/business-internet-plus-bundle/` | Phase 4 — generated bundle example with step-by-step transcript; load `TRANSCRIPT.md` first, then specific JSON files referenced in it |
| `references/epc-field-guide.md` | Phase 2 & 3 — EPC field-level guidance and common pitfalls |
| `references/naming-conventions.md` | Phase 2 & 3 — naming and keying conventions |
| `references/scoring-model.md` | Phase 5 — full 6-category scoring rubric with per-category criteria |
| `scripts/cli-validation-commands.sh` | Phase 5 — sf CLI queries for validating EPC artifacts in org |
| `scripts/sample-invocations.sh` | On Start — reference example invocations for common EPC tasks |

---

## Cross-Skill Integration

| From Skill | To `modeling-omnistudio-epc-catalog` | When |
|---|---|---|
| analyzing-omnistudio-dependencies | -> modeling-omnistudio-epc-catalog | Need current dependency and namespace inventory first |
| generating-custom-object / generating-custom-field | -> modeling-omnistudio-epc-catalog | Need object or field readiness before EPC modeling |
| querying-soql | -> modeling-omnistudio-epc-catalog | Need existing catalog query analysis |

| From `modeling-omnistudio-epc-catalog` | To Skill | When |
|---|---|---|
| modeling-omnistudio-epc-catalog | -> building-omnistudio-omniscript | Configure guided selling UX using the modeled catalog |
| modeling-omnistudio-epc-catalog | -> building-omnistudio-integration-procedure | Build server-side orchestration over product and pricing payloads |
| modeling-omnistudio-epc-catalog | -> deploying-metadata | Deploy validated catalog metadata |

---

## External References

Local references:

- [references/epc-field-guide.md](references/epc-field-guide.md) — EPC field-level guidance and minimum required fields
- [references/naming-conventions.md](references/naming-conventions.md) — Naming and keying conventions for products, attributes, and bundles

---

## Notes

- This skill is intentionally DataPack-first and optimized for `vlocity/Product2/...` artifact authoring.
- Keep `%vlocity_namespace%` placeholders intact in templates to preserve portability.
- Prefer creating reusable spec products first, then assemble offers via child relationships.

---
