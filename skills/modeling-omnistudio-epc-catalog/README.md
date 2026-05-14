# modeling-omnistudio-epc-catalog

Salesforce Industries CME EPC product-modeling skill for Product2-based catalog design. Build offer bundles, attributes, Product Child Items, and companion DataPack JSON artifacts with a 120-point quality rubric.

## Features

- **Offer Bundle Modeling**: Create `Product2` offers with `SpecificationType=Offer` and `SpecificationSubType=Bundle`
- **Attribute Modeling**: Define attribute metadata, defaults, valid values, and assignment payloads
- **Bundle Composition**: Build root and child `%vlocity_namespace%__ProductChildItem__c` rows with quantity semantics
- **Companion DataPack Generation**: Produce pricing, orchestration, decomposition, override, and parent-key files
- **DataPack Integrity Controls**: Keep global keys, source keys, and lookup references consistent
- **120-Point Scoring**: Validate bundle quality across 6 EPC-focused categories

## Quick Start

### 1. Invoke the skill

```
Skill: modeling-omnistudio-epc-catalog
Request: "Create a Product2 offer bundle named Business Internet Plus with ProductCode BIZ-INT-PLUS-01, 3 child products, and generate all companion DataPack JSON files from the assets templates."
```

### 2. Typical operations

| Operation | Example Request |
|-----------|-----------------|
| Create bundle | "Create a Product2 offer bundle for Business Fiber Pro with 3 child products and full companion metadata." |
| Add attributes | "Add Contract Term and Download Speed attributes with defaults and valid values." |
| Build child items | "Create root and child ProductChildItem records with min/max/default quantity rules." |
| Generate companions | "Generate pricebook, price list, object field attribute, orchestration, decomposition, override, and parent key files." |
| Review and score | "Review this bundle DataPack and score it with the 120-point rubric." |

## Companion Files for Full Bundle Payload

When generating a complete bundle, include:

- `*_DataPack.json`
- `*_AttributeAssignments.json`
- `*_ProductChildItems.json`
- `*_PricebookEntries.json`
- `*_PriceListEntries.json`
- `*_ObjectFieldAttributes.json`
- `*_OrchestrationScenarios.json`
- `*_DecompositionRelationships.json`
- `*_CompiledAttributeOverrides.json`
- `*_OverrideDefinitions.json`
- `*_ParentKeys.json`

## Bundled Examples

- [assets/](assets/) - canonical EPC bundle template set for DataPack authoring
- [assets/examples/](assets/examples/) - additional bundle and simple-offer sample packs
- [examples/business-internet-plus-bundle/](examples/business-internet-plus-bundle/) - generated Business Internet Plus example with transcript

## Scoring System (120 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Catalog Identity and Naming | 20 | Product naming, ProductCode quality, stable key strategy |
| EPC Product Structure | 20 | Required Product2/EPC fields, lifecycle and activation coherence |
| Attribute Modeling | 25 | Category quality, valid values/defaults, required/display behavior |
| Offer Bundle Composition | 25 | Root PCI, child integrity, quantity semantics |
| DataPack Integrity | 15 | Namespace placeholder usage, lookup portability, key consistency |
| Documentation and Handoff | 15 | Intent clarity, risks, verification guidance |

**Thresholds**: `>=95` Deploy-ready | `70-94` Needs review | `<70` Block and fix

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| analyzing-omnistudio-dependencies | Inventory namespace and dependencies before modeling |
| building-omnistudio-omniscript | Build guided selling UX on top of modeled catalog |
| building-omnistudio-integration-procedure | Orchestrate product and pricing interactions server-side |
| building-omnistudio-callable-apex | Implement callable Apex actions used by OmniStudio/IP flows over EPC selections |
| deploying-metadata | Validate and deploy generated metadata artifacts |

## Documentation

- [SKILL.md](SKILL.md) - Full EPC workflow, guardrails, and scoring
- [references/epc-field-guide.md](references/epc-field-guide.md) - EPC field-level guidance
- [references/naming-conventions.md](references/naming-conventions.md) - Naming and keying conventions
- [../building-omnistudio-callable-apex/README.md](../building-omnistudio-callable-apex/README.md) - Companion callable Apex patterns

## Requirements

- Salesforce Industries org with EPC enabled
- sf CLI v2 (for validation/deploy workflows)
- Compatible namespace model (`%vlocity_namespace%`, `vlocity_cmt`, or Core)
