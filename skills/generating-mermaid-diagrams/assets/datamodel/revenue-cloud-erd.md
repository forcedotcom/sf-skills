# Revenue Cloud Data Model Template

Pre-built data model for Salesforce Revenue Cloud (CPQ, Billing, Subscription Management) using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| ProductCatalog | STD | Product catalogs |
| ProductCategory | STD | Category hierarchy |
| ProductSellingModel | STD | Selling configurations |
| ProductSellingModelOption | STD | Model options |
| PriceAdjustmentSchedule | STD | Discount schedules |
| PriceAdjustmentTier | STD | Discount tiers |
| ProductAttribute | STD | Product attributes |
| ProductAttributeSet | STD | Attribute groupings |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects ProductCatalog,ProductCategory,ProductSellingModel,PriceAdjustmentSchedule \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% REVENUE CLOUD DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Product Catalog
    Catalog["ProductCatalog<br/>(count)"]
    Category["ProductCategory<br/>(count)"]
    Product2["Product2<br/>(count)"]

    %% Selling Models
    PSM["ProductSellingModel<br/>(count)"]
    PSMO["ProductSellingModelOption<br/>(count)"]

    %% Pricing
    PAS["PriceAdjustmentSchedule<br/>(count)"]
    PAT["PriceAdjustmentTier<br/>(count)"]
    Pricebook2["Pricebook2<br/>(count)"]
    PBE["PricebookEntry<br/>(count)"]

    %% Attributes
    AttrSet["ProductAttributeSet<br/>(count)"]
    Attr["ProductAttribute<br/>(count)"]
    AttrSetItem["ProductAttributeSetItem<br/>(count)"]

    %% Catalog Structure
    Catalog ==>|"MD"| Category
    Category -.->|"Parent"| Category
    Category -->|"LK"| Product2

    %% Selling Models
    Product2 -->|"LK"| PSM
    PSM ==>|"MD"| PSMO

    %% Pricing
    PAS ==>|"MD"| PAT
    Pricebook2 ==>|"MD"| PBE
    Product2 -->|"LK"| PBE

    %% Attributes
    AttrSet ==>|"MD"| AttrSetItem
    Attr -->|"LK"| AttrSetItem
    Product2 -->|"LK"| AttrSet

    %% Standard Objects - Sky Blue
    style Catalog fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Category fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PSM fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PSMO fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PAS fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PAT fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Pricebook2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PBE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style AttrSet fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Attr fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style AttrSetItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Revenue Cloud Components
| Component | Purpose |
|-----------|---------|
| **Industries CPQ** | Configure-Price-Quote |
| **Subscription Management** | Recurring billing |
| **Revenue Lifecycle** | Rev rec, forecasting |
| **Dynamic Revenue Orchestration** | Guided selling |

### Product Hierarchy
```
ProductCatalog
    └── ProductCategory (Hierarchy)
            └── Product2
                    ├── ProductSellingModel
                    ├── ProductAttribute
                    └── PricebookEntry
```

### Selling Model Types
| Type | Description |
|------|-------------|
| One-Time | Single purchase |
| Subscription | Recurring billing |
| Usage-Based | Consumption pricing |
| Evergreen | Auto-renewing |
| Term | Fixed duration |

### Price Adjustment Schedules
| Schedule Type | Use Case |
|---------------|----------|
| Volume Discount | Quantity-based tiers |
| Contract Discount | Agreement discounts |
| Promotional | Time-limited offers |
| Bundled | Package pricing |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core revenue structure:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Catalog["ProductCatalog"]
    Category["ProductCategory"]
    Product2["Product2"]
    PSM["ProductSellingModel"]

    Catalog ==>|"MD"| Category
    Category -->|"LK"| Product2
    Product2 -->|"LK"| PSM

    style Catalog fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Category fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PSM fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Subscription Management Model

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account"]
    Quote["Quote"]
    QLI["QuoteLineItem"]
    Order["Order"]
    OrderItem["OrderItem"]
    Asset["Asset"]
    BillingSchedule["BillingSchedule"]

    Account -->|"LK"| Quote
    Quote ==>|"MD"| QLI
    Quote -.->|"converts"| Order
    Order ==>|"MD"| OrderItem
    OrderItem -.->|"creates"| Asset
    Asset -->|"LK"| BillingSchedule

    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Quote fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style QLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OrderItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Asset fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style BillingSchedule fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Pricing Model Detail

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Product2["Product2"]
    Pricebook2["Pricebook2"]
    PBE["PricebookEntry"]
    PAS["PriceAdjustmentSchedule"]
    PAT["PriceAdjustmentTier"]

    Pricebook2 ==>|"MD"| PBE
    Product2 -->|"LK"| PBE
    PAS ==>|"MD"| PAT
    Product2 -->|"LK"| PAS

    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Pricebook2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PBE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PAS fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PAT fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Industries CPQ Objects

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Quote["Quote"]
    QLI["QuoteLineItem"]
    ProposalDoc["ProposalDocument"]
    ProposalTerm["ProposalTerm"]
    DocTemplate["DocumentTemplate"]

    Quote ==>|"MD"| QLI
    Quote -->|"LK"| ProposalDoc
    ProposalDoc ==>|"MD"| ProposalTerm
    DocTemplate -->|"LK"| ProposalDoc

    style Quote fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style QLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ProposalDoc fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ProposalTerm fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style DocTemplate fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REVENUE CLOUD DATA MODEL (L→R)                                              │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                           PRODUCT CATALOG
┌──────────────────┐         ┌──────────────────┐
│ PRODUCT_CATALOG  │═══ MD ═>│ PRODUCT_CATEGORY │◄──── Parent (self)
│     (count)      │         │     (count)      │
└──────────────────┘         └────────┬─────────┘
                                      │ LK
                                      ▼
                             ┌──────────────────┐
                             │     PRODUCT2     │
                             │     (count)      │
                             └────────┬─────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │ LK              │ LK              │ LK
                    ▼                 ▼                 ▼
         ┌──────────────────┐ ┌─────────────┐ ┌──────────────────┐
         │PRODUCT_SELLING_  │ │PRICEBOOK_   │ │PRODUCT_ATTRIBUTE │
         │MODEL (count)     │ │ENTRY(count) │ │_SET (count)      │
         └────────┬─────────┘ └─────────────┘ └────────┬─────────┘
                  │ MD                                 │ MD
                  ▼                                    ▼
         ┌──────────────────┐                ┌──────────────────┐
         │PRODUCT_SELLING_  │                │PRODUCT_ATTRIBUTE_│
         │MODEL_OPTION      │                │SET_ITEM (count)  │
         │    (count)       │                └────────┬─────────┘
         └──────────────────┘                         │ LK
                                                      ▼
                                             ┌──────────────────┐
                                             │PRODUCT_ATTRIBUTE │
                                             │     (count)      │
                                             └──────────────────┘

                           PRICE ADJUSTMENTS
┌────────────────────────┐         ┌──────────────────────────┐
│PRICE_ADJUSTMENT_       │═══ MD ═>│PRICE_ADJUSTMENT_TIER     │
│SCHEDULE (count)        │         │        (count)           │
└────────────────────────┘         └──────────────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| ProductCatalog | ProductCategory | MD | Cascade delete |
| ProductCategory | ProductCategory | LK | Parent (hierarchy) |
| ProductCategory | Product2 | LK | Product classification |
| Product2 | ProductSellingModel | LK | Selling configuration |
| ProductSellingModel | ProductSellingModelOption | MD | Model options |
| PriceAdjustmentSchedule | PriceAdjustmentTier | MD | Discount tiers |
| Pricebook2 | PricebookEntry | MD | Product prices |
| Product2 | PricebookEntry | LK | Product reference |
| ProductAttributeSet | ProductAttributeSetItem | MD | Attribute membership |
| ProductAttribute | ProductAttributeSetItem | LK | Attribute reference |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Product categories depth | 10 levels |
| Products per catalog | Unlimited (LDV) |
| Selling models per product | Multiple |
| Discount tiers per schedule | Unlimited |
| Attributes per product | Unlimited |
| Pricebooks per org | Unlimited |

---

## Revenue Cloud vs Salesforce CPQ

| Feature | Revenue Cloud | Salesforce CPQ |
|---------|---------------|----------------|
| Platform | Industries | Core |
| Bundles | Dynamic | Static |
| Attributes | Dynamic | Limited |
| Selling Models | Native | Custom |
| Subscription | Native | Requires add-on |
| Target | Industry-specific | General |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
