# B2B Commerce Data Model Template

Pre-built data model for Salesforce B2B Commerce using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| WebStore | STD | Online storefront |
| WebCart | STD | Shopping cart |
| CartItem | STD | Cart products |
| BuyerGroup | STD | Customer groups |
| BuyerAccount | STD | B2B customers |
| ProductCatalog | STD | Product catalog |
| CommerceEntitlementPolicy | STD | Access policies |
| CartCheckoutSession | STD | Checkout process |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects WebStore,WebCart,CartItem,BuyerGroup,BuyerAccount \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% B2B COMMERCE DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Store Structure
    WebStore["WebStore<br/>(count)"]
    ProductCatalog["ProductCatalog<br/>(count)"]
    Product2["Product2<br/>(count)"]

    %% Buyer Structure
    BuyerGroup["BuyerGroup<br/>(count)"]
    BuyerAccount["BuyerAccount<br/>(count)"]
    BuyerGroupMember["BuyerGroupMember<br/>(count)"]
    Account["Account<br/>(count)"]

    %% Cart Structure
    WebCart["WebCart<br/>(count)"]
    CartItem["CartItem<br/>(count)"]
    CartCheckout["CartCheckoutSession<br/>(count)"]

    %% Entitlements
    CEPolicy["CommerceEntitlementPolicy<br/>(count)"]
    CEProduct["CommerceEntitlementProduct<br/>(count)"]
    CEBuyerGroup["CommerceEntitlementBuyerGroup<br/>(count)"]

    %% Store to Products
    WebStore -->|"LK"| ProductCatalog
    ProductCatalog ==>|"MD"| Product2

    %% Buyer Structure
    BuyerGroup ==>|"MD"| BuyerGroupMember
    Account -->|"LK"| BuyerAccount
    WebStore -->|"LK"| BuyerAccount
    BuyerAccount -->|"LK"| BuyerGroupMember

    %% Cart
    WebStore -->|"LK"| WebCart
    Account -->|"LK"| WebCart
    WebCart ==>|"MD"| CartItem
    Product2 -->|"LK"| CartItem
    WebCart -->|"LK"| CartCheckout

    %% Entitlements
    CEPolicy ==>|"MD"| CEProduct
    CEPolicy ==>|"MD"| CEBuyerGroup
    Product2 -->|"LK"| CEProduct
    BuyerGroup -->|"LK"| CEBuyerGroup

    %% Standard Objects - Sky Blue
    style WebStore fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ProductCatalog fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style BuyerGroup fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style BuyerAccount fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style BuyerGroupMember fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WebCart fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CartItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CartCheckout fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CEPolicy fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CEProduct fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CEBuyerGroup fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### B2B Commerce Flow
```
WebStore → ProductCatalog → Product2
    ↓           ↓
BuyerAccount → WebCart → CartItem → Order
    ↓
BuyerGroup → Entitlements (What they can see/buy)
```

### Buyer vs Account
| Object | Purpose |
|--------|---------|
| Account | Standard CRM account |
| BuyerAccount | Commerce-enabled account |
| BuyerGroup | Pricing/entitlement grouping |

### Entitlement Model
```
CommerceEntitlementPolicy
    ├── CommerceEntitlementProduct (What products)
    └── CommerceEntitlementBuyerGroup (Who can see)
```

Controls which products each BuyerGroup can view and purchase.

### Cart States
| Status | Description |
|--------|-------------|
| Active | Current shopping cart |
| Checkout | In checkout process |
| Closed | Converted to Order |
| Abandoned | Inactive cart |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core commerce flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    WebStore["WebStore"]
    BuyerAccount["BuyerAccount"]
    WebCart["WebCart"]
    Order["Order"]

    WebStore -->|"hosts"| BuyerAccount
    BuyerAccount -->|"LK"| WebCart
    WebCart -.->|"converts"| Order

    style WebStore fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style BuyerAccount fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WebCart fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Pricing Model

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    BuyerGroup["BuyerGroup"]
    Pricebook2["Pricebook2"]
    PBE["PricebookEntry"]
    Product2["Product2"]
    WebStorePB["WebStorePricebook"]
    WebStore["WebStore"]

    BuyerGroup -->|"LK"| Pricebook2
    Pricebook2 ==>|"MD"| PBE
    Product2 -->|"LK"| PBE
    WebStore ==>|"MD"| WebStorePB
    Pricebook2 -->|"LK"| WebStorePB

    style BuyerGroup fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Pricebook2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PBE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WebStorePB fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WebStore fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Cart to Order Conversion

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    WebCart["WebCart"]
    CartItem["CartItem"]
    CartCheckout["CartCheckoutSession"]
    Order["Order"]
    OrderItem["OrderItem"]
    OrderSummary["OrderSummary"]

    WebCart ==>|"MD"| CartItem
    WebCart -->|"LK"| CartCheckout
    CartCheckout -.->|"creates"| Order
    Order ==>|"MD"| OrderItem
    Order -->|"LK"| OrderSummary

    style WebCart fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CartItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CartCheckout fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Order fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OrderItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OrderSummary fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  B2B COMMERCE DATA MODEL (L→R)                                               │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                           STORE & PRODUCTS
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   WEBSTORE   │── LK ──>│ PRODUCT_CATALOG  │═══ MD ═>│   PRODUCT2   │
│   (count)    │         │     (count)      │         │   (count)    │
└──────┬───────┘         └──────────────────┘         └──────────────┘
       │
       │                       BUYERS
       │
       │ LK              ┌──────────────────┐         ┌──────────────┐
       └────────────────>│  BUYER_ACCOUNT   │◄── LK ──│   ACCOUNT    │
                         │     (count)      │         │   (count)    │
                         └────────┬─────────┘         └──────────────┘
                                  │
                                  │ LK
                                  ▼
                         ┌──────────────────┐
                         │ BUYER_GROUP_     │◄══ MD ══┌──────────────┐
                         │ MEMBER (count)   │         │ BUYER_GROUP  │
                         └──────────────────┘         │   (count)    │
                                                      └──────────────┘

                               CART
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   WEBSTORE   │── LK ──>│     WEBCART      │═══ MD ═>│  CART_ITEM   │
│              │         │     (count)      │         │   (count)    │
└──────────────┘         └────────┬─────────┘         └──────────────┘
                                  │
                                  │ LK
                                  ▼
                         ┌──────────────────┐ converts ┌──────────────┐
                         │CART_CHECKOUT_    │·········>│    ORDER     │
                         │SESSION (count)   │          │   (count)    │
                         └──────────────────┘          └──────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| WebStore | ProductCatalog | LK | Store products |
| WebStore | BuyerAccount | LK | Store customers |
| WebStore | WebCart | LK | Shopping carts |
| ProductCatalog | Product2 | MD | Catalog products |
| BuyerGroup | BuyerGroupMember | MD | Group members |
| Account | BuyerAccount | LK | Commerce enablement |
| WebCart | CartItem | MD | Cart products |
| WebCart | CartCheckoutSession | LK | Checkout |
| CommerceEntitlementPolicy | CommerceEntitlementProduct | MD | Product access |
| CommerceEntitlementPolicy | CommerceEntitlementBuyerGroup | MD | Group access |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Products per store | Unlimited (LDV) |
| Buyer accounts per store | Unlimited |
| Cart items per cart | 500 |
| Active carts per buyer | 1 |
| Price books per buyer group | Multiple |
| Entitlement policies | Unlimited |

---

## B2B vs B2C Commerce

| Feature | B2B Commerce | B2C Commerce |
|---------|--------------|--------------|
| Customer | Business (Account) | Consumer (Contact) |
| Pricing | Contract/negotiated | List price |
| Catalog | Entitlement-based | Public |
| Checkout | Quote/approval | Immediate |
| Platform | LWR/Aura | LWR/Headless |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
