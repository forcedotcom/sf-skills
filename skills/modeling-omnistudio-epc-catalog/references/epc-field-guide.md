<!-- Parent: modeling-omnistudio-epc-catalog/SKILL.md -->

# EPC Field Guide (Product2 + Bundles + Attributes)

This quick guide captures the minimum field set for creating CME EPC products and offer bundles in DataPack-style metadata.

## Root Template Files (`assets/`)

The skill root `assets/` directory contains a full template set aligned to the Business Internet Essential (VPL) bundle:

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

## Product2: Minimum Recommended EPC Fields

| Field | Purpose | Example |
|---|---|---|
| `Name` | Human-readable catalog name | `Business Internet Essential (VPL)` |
| `ProductCode` | Stable technical identifier | `VEPC_OFFERING_BUSINESS_INTERNET_ESSENTIAL` |
| `%vlocity_namespace%__GlobalKey__c` | Cross-environment stable key | UUID-like value |
| `%vlocity_namespace%__SpecificationType__c` | Product classification | `Offer` |
| `%vlocity_namespace%__SpecificationSubType__c` | Product subtype | `Bundle` |
| `%vlocity_namespace%__Status__c` | EPC status | `Active` |
| `%vlocity_namespace%__IsOrderable__c` | Order eligibility | `true` |
| `IsActive` | Product availability | `true` |
| `%vlocity_namespace%__SellingStartDate__c` | Sales lifecycle start | `2021-07-31T04:00:00.000Z` |

## Attribute Metadata Blocks

### `%vlocity_namespace%__AttributeMetadata__c`

Contains category/group metadata and product attribute records:

- category `Code__c`, `Name`, `displaySequence`
- per-attribute `code`, `label`, `inputType`, `required`, `values[]`

### `%vlocity_namespace%__AttributeDefaultValues__c`

Map from attribute code to default value:

```json
{
  "VEPC_ATTR_DOWNLOAD_SPEED": "50 Mbps",
  "VEPC_ATTR_CONTRACT_TERM": "Month-to-Month"
}
```

## Product Bundle Modeling (`%vlocity_namespace%__ProductChildItem__c`)

Offer bundles are composed through child item rows:

- one root row: `IsRootProductChildItem = true`
- child rows: parent and child references + sequence and quantity settings

Key quantity fields:

- `%vlocity_namespace%__MinQuantity__c`
- `%vlocity_namespace%__MaxQuantity__c`
- `%vlocity_namespace%__Quantity__c`
- `%vlocity_namespace%__MinMaxDefaultQty__c` (e.g., `"0, 1, 1"`)

## Common Field Pitfalls

| Pitfall | Impact | Fix |
|---|---|---|
| `ProductCode` reused for multiple products | Cart and quote ambiguity | Enforce unique catalog code |
| Default attribute value missing from values list | Runtime configuration errors | Keep defaults inside valid value set |
| Missing root ProductChildItem | Broken offer traversal | Always add root row |
| Direct org-specific IDs in DataPack | Deploy failures across orgs | Use lookup source keys and global keys |

## Included Example Packs

The skill ships with:

- `assets/` (canonical EPC bundle template set)
- `assets/examples/samsung-galaxy-s22-bundle/` (bundle offer example)
- `assets/examples/business-internet-premium-fttc-simple-offer/` (simple offer example)
- `assets/examples/business-internet-pro-vpl-simple-offer/` (simple offer example)
- `assets/examples/static-ip-simple-offer/` (simple offer example)

The example folders contain related DataPack-style files, including Product2 payloads, attribute assignments, product child items, and pricing artifacts.
