# Sales Cloud Data Model Template

Pre-built data model for Salesforce Sales Cloud using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Account | STD | Companies and organizations |
| Contact | STD | People associated with accounts |
| Lead | STD | Potential customers |
| Opportunity | STD | Sales deals and revenue |
| OpportunityLineItem | STD | Products on opportunities |
| Product2 | STD | Product catalog |
| Campaign | STD | Marketing campaigns |
| CampaignMember | STD | Campaign responses |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Account,Contact,Lead,Opportunity,Product2,Campaign \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% SALES CLOUD DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Core Objects
    Lead["Lead<br/>(count)"]
    Account["Account<br/>(count)"]
    Contact["Contact<br/>(count)"]
    Opportunity["Opportunity<br/>(count)"]

    %% Product Objects
    Product2["Product2<br/>(count)"]
    OLI["OpportunityLineItem<br/>(count)"]

    %% Campaign Objects
    Campaign["Campaign<br/>(count)"]
    CampaignMember["CampaignMember<br/>(count)"]

    %% Relationships - Lead Conversion
    Lead -.->|"converts"| Account
    Lead -.->|"converts"| Contact

    %% Relationships - Account to children
    Account -->|"LK"| Contact
    Account -->|"LK"| Opportunity

    %% Relationships - Opportunity
    Opportunity ==>|"MD"| OLI
    Product2 -->|"LK"| OLI
    Contact -->|"LK"| Opportunity

    %% Relationships - Campaign
    Campaign ==>|"MD"| CampaignMember
    Lead -->|"LK"| CampaignMember
    Contact -->|"LK"| CampaignMember
    Campaign -->|"LK"| Opportunity

    %% Standard Objects - Sky Blue
    style Lead fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Campaign fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CampaignMember fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Simplified Version (Core Objects Only)

For presentations focusing on core sales flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Lead["Lead"]
    Account["Account"]
    Contact["Contact"]
    Opportunity["Opportunity"]

    Lead -.->|"converts"| Account
    Lead -.->|"converts"| Contact
    Account -->|"LK"| Contact
    Account -->|"LK"| Opportunity
    Contact -->|"LK"| Opportunity

    style Lead fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SALES CLOUD DATA MODEL (L→R)                                               │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>), -.-> = converts       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐          ┌──────────┐          ┌──────────────┐
│   LEAD   │··········│ ACCOUNT  │── LK ───>│   CONTACT    │
│ (count)  │ converts │ (count)  │          │   (count)    │
└────┬─────┘          └────┬─────┘          └──────┬───────┘
     │                     │                       │
     │ converts            │ LK                    │ LK
     │                     ▼                       ▼
     │                ┌──────────────┐       ┌─────────────────┐
     └───────────────>│ OPPORTUNITY  │<──────│  (via OCR)      │
                      │   (count)    │       └─────────────────┘
                      └──────┬───────┘
                             │ MD
                             ▼
                      ┌──────────────────────┐
                      │ OPPORTUNITY_LINE_ITEM│◄── LK ──┌───────────┐
                      │      (count)         │         │ PRODUCT2  │
                      └──────────────────────┘         │  (count)  │
                                                       └───────────┘

┌──────────┐          ┌─────────────────┐
│ CAMPAIGN │═══ MD ══>│ CAMPAIGN_MEMBER │
│ (count)  │          │    (count)      │
└──────────┘          └─────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Account | Contact | LK | Optional parent |
| Account | Opportunity | LK | Optional parent |
| Opportunity | OpportunityLineItem | MD | Cascade delete |
| Product2 | OpportunityLineItem | LK | Optional parent |
| Campaign | CampaignMember | MD | Cascade delete |
| Campaign | Opportunity | LK | Primary campaign source |
| Lead | (converts to) | - | Account + Contact created |

---

## Adding Custom Objects

Use orange styling for custom objects:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account<br/>(317)"]
    Invoice["Invoice__c<br/>(1,200)"]

    Account ==>|"MD"| Invoice

    %% Standard - Sky Blue
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    %% Custom - Orange
    style Invoice fill:#fed7aa,stroke:#c2410c,color:#1f2937
```

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
