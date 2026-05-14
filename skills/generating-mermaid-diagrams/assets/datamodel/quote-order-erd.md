# Quote & Order Data Model Template

Pre-built data model for Salesforce Quotes and Orders using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Opportunity | STD | Sales deals |
| Quote | STD | Price quotes |
| QuoteLineItem | STD | Quote products |
| Order | STD | Customer orders |
| OrderItem | STD | Order products |
| Product2 | STD | Product catalog |
| PricebookEntry | STD | Product prices |
| Pricebook2 | STD | Price lists |
| Contract | STD | Customer contracts |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Opportunity,Quote,QuoteLineItem,Order,OrderItem,Product2,Contract \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% QUOTE & ORDER DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Product Catalog
    Pricebook2["Pricebook2<br/>(count)"]
    Product2["Product2<br/>(count)"]
    PBE["PricebookEntry<br/>(count)"]

    %% Quote Objects
    Opportunity["Opportunity<br/>(count)"]
    Quote["Quote<br/>(count)"]
    QLI["QuoteLineItem<br/>(count)"]

    %% Order Objects
    Order["Order<br/>(count)"]
    OrderItem["OrderItem<br/>(count)"]
    Contract["Contract<br/>(count)"]

    %% Account
    Account["Account<br/>(count)"]

    %% Product Catalog Relationships
    Pricebook2 ==>|"MD"| PBE
    Product2 -->|"LK"| PBE

    %% Quote Relationships
    Opportunity ==>|"MD"| Quote
    Quote ==>|"MD"| QLI
    PBE -->|"LK"| QLI
    Product2 -->|"LK"| QLI
    Pricebook2 -->|"LK"| Quote

    %% Order Relationships
    Account -->|"LK"| Order
    Contract -->|"LK"| Order
    Quote -->|"LK"| Order
    Order ==>|"MD"| OrderItem
    PBE -->|"LK"| OrderItem
    Product2 -->|"LK"| OrderItem
    Pricebook2 -->|"LK"| Order

    %% Contract
    Account -->|"LK"| Contract

    %% Standard Objects - Sky Blue
    style Pricebook2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PBE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Quote fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style QLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OrderItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contract fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Quote-to-Cash Flow
```
Opportunity → Quote → Order → Invoice → Payment
      ↓          ↓        ↓
    OLI        QLI   OrderItem
```

### Synced Quote
- One Quote per Opportunity can be marked as **Synced**
- Synced Quote copies line items to OpportunityLineItems
- `IsSyncing = true` on Synced Quote

### Quote to Order Conversion
| Action | Result |
|--------|--------|
| Create Order from Quote | Creates Order + OrderItems |
| Quote.OrderId | Links Quote to created Order |
| Reduction Orders | Negative quantity adjustments |

### Pricebook Structure
```
Pricebook2 (Standard + Custom)
    ↓
PricebookEntry (Product + Price per Pricebook)
    ↓
Product2 (Catalog)
```

---

## Simplified Version (Core Flow)

For presentations focusing on Quote-to-Order flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Opportunity["Opportunity"]
    Quote["Quote"]
    Order["Order"]
    Contract["Contract"]

    Opportunity ==>|"MD"| Quote
    Quote -->|"creates"| Order
    Contract -->|"LK"| Order

    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Quote fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contract fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Product Catalog Detail

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Pricebook2["Pricebook2<br/>(Standard + Custom)"]
    Product2["Product2<br/>(Catalog)"]
    PBE["PricebookEntry<br/>(Price per Book)"]

    Pricebook2 ==>|"MD"| PBE
    Product2 -->|"LK"| PBE

    style Pricebook2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PBE fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  QUOTE & ORDER DATA MODEL (L→R)                                              │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                 PRODUCT CATALOG                           QUOTE FLOW
┌──────────────┐         ┌─────────────────┐         ┌──────────────┐
│  PRICEBOOK2  │═══ MD ═>│ PRICEBOOKENTRY  │         │ OPPORTUNITY  │
│   (count)    │         │    (count)      │         │   (count)    │
└──────────────┘         └────────┬────────┘         └──────┬───────┘
                                  │                         │ MD
                                  │ LK                      ▼
┌──────────────┐                  │                  ┌──────────────┐
│   PRODUCT2   │─────── LK ───────┤                  │    QUOTE     │
│   (count)    │                  │                  │   (count)    │
└──────────────┘                  │                  └──────┬───────┘
       │                          │                         │ MD
       │                          │                         ▼
       │                          │                  ┌──────────────┐
       └────────── LK ────────────┼─────────────────>│QUOTELINEITEM │
                                  └─────── LK ──────>│   (count)    │
                                                     └──────────────┘

                                 ORDER FLOW
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   ACCOUNT    │── LK ──>│    ORDER     │═══ MD ═>│  ORDERITEM   │
│   (count)    │         │   (count)    │         │   (count)    │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                │
┌──────────────┐                │
│   CONTRACT   │────── LK ──────┘
│   (count)    │
└──────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Opportunity | Quote | MD | Cascade delete |
| Quote | QuoteLineItem | MD | Cascade delete |
| Order | OrderItem | MD | Cascade delete |
| Pricebook2 | PricebookEntry | MD | Cascade delete |
| Product2 | PricebookEntry | LK | Product reference |
| PricebookEntry | QuoteLineItem | LK | Price reference |
| PricebookEntry | OrderItem | LK | Price reference |
| Account | Order | LK | Customer |
| Contract | Order | LK | Contract reference |
| Quote | Order | LK | Source quote |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Quotes per Opportunity | Unlimited (1 synced) |
| QuoteLineItems per Quote | 200 (configurable) |
| Orders per Account | Unlimited |
| OrderItems per Order | 200 (configurable) |
| Custom Pricebooks | Unlimited |
| Products | 5 million (LDV) |

---

## Contract-Based Orders

For orgs using Contracts with Orders:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account"]
    Contract["Contract"]
    Order["Order"]
    ReductionOrder["Order<br/>(Reduction)"]

    Account -->|"LK"| Contract
    Contract -->|"LK"| Order
    Order -.->|"reduces"| ReductionOrder

    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contract fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ReductionOrder fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
