# Campaigns Data Model Template

Pre-built data model for Salesforce Campaigns using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Campaign | STD | Marketing campaigns |
| CampaignMember | STD | Campaign responses (Lead/Contact) |
| CampaignMemberStatus | STD | Status values per campaign |
| CampaignInfluence | STD | Attribution to opportunities |
| Lead | STD | Potential customers |
| Contact | STD | Existing contacts |
| Opportunity | STD | Influenced deals |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Campaign,CampaignMember,CampaignInfluence,Lead,Contact,Opportunity \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% CAMPAIGNS DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Core Campaign Objects
    Campaign["Campaign<br/>(count)"]
    CampaignMember["CampaignMember<br/>(count)"]
    CampaignMemberStatus["CampaignMemberStatus<br/>(count)"]

    %% Attribution
    CampaignInfluence["CampaignInfluence<br/>(count)"]

    %% Related Objects
    Lead["Lead<br/>(count)"]
    Contact["Contact<br/>(count)"]
    Opportunity["Opportunity<br/>(count)"]

    %% Relationships - Campaign to Members
    Campaign ==>|"MD"| CampaignMember
    Campaign ==>|"MD"| CampaignMemberStatus
    Lead -->|"LK"| CampaignMember
    Contact -->|"LK"| CampaignMember

    %% Relationships - Attribution
    Campaign -->|"LK"| CampaignInfluence
    Contact -->|"LK"| CampaignInfluence
    Opportunity -->|"LK"| CampaignInfluence

    %% Campaign Hierarchy
    Campaign -.->|"Parent"| Campaign

    %% Primary Campaign Source
    Campaign -->|"LK"| Opportunity

    %% Standard Objects - Sky Blue
    style Campaign fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CampaignMember fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CampaignMemberStatus fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CampaignInfluence fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Lead fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Campaign Hierarchy
- Campaigns support **Parent Campaign** self-lookup
- Enables rollup reporting across campaign groups
- Max hierarchy depth: 5 levels

### CampaignMember Polymorphism
- CampaignMember links to **either** Lead OR Contact (not both)
- Uses `LeadId` or `ContactId` lookup fields
- Status tracked via CampaignMemberStatus

### Campaign Influence Models
| Model | Description |
|-------|-------------|
| **Primary Campaign Source** | First-touch attribution (Opportunity.CampaignId) |
| **Campaign Influence 1.0** | Manual influence records |
| **Customizable Campaign Influence** | Multi-touch with weighted attribution |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core campaign flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Campaign["Campaign"]
    CampaignMember["CampaignMember"]
    Lead["Lead"]
    Contact["Contact"]

    Campaign ==>|"MD"| CampaignMember
    Lead -->|"LK"| CampaignMember
    Contact -->|"LK"| CampaignMember

    style Campaign fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CampaignMember fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Lead fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CAMPAIGNS DATA MODEL (L→R)                                                  │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────┐
                         ┌───>│ CAMPAIGN_MEMBER     │<─── LK ──┬──────────────┐
                         │ MD │     (count)         │          │              │
                         │    └─────────────────────┘          │              │
┌──────────────┐         │                                ┌────┴─────┐   ┌────┴─────┐
│   CAMPAIGN   │─────────┤                                │   LEAD   │   │ CONTACT  │
│   (count)    │         │    ┌─────────────────────┐     │ (count)  │   │ (count)  │
└──────┬───────┘         └───>│ CAMPAIGN_MEMBER_    │     └──────────┘   └────┬─────┘
       │                   MD │ STATUS (count)      │                         │
       │ Parent               └─────────────────────┘                         │
       ▼                                                                      │
┌──────────────┐              ┌─────────────────────┐                         │
│   CAMPAIGN   │── LK ───────>│ CAMPAIGN_INFLUENCE  │<──── LK ────────────────┤
│   (parent)   │              │     (count)         │                         │
└──────────────┘              └──────────┬──────────┘                         │
                                         │                                    │
                                         │ LK                                 │
                                         ▼                                    │
                              ┌─────────────────────┐                         │
                              │    OPPORTUNITY      │                         │
                              │      (count)        │                         │
                              └─────────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Campaign | CampaignMember | MD | Cascade delete |
| Campaign | CampaignMemberStatus | MD | Cascade delete |
| Lead | CampaignMember | LK | Optional (polymorphic) |
| Contact | CampaignMember | LK | Optional (polymorphic) |
| Campaign | CampaignInfluence | LK | Attribution link |
| Campaign | Opportunity | LK | Primary Campaign Source |
| Campaign | Campaign | LK | Parent Campaign (hierarchy) |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Campaign hierarchy depth | 5 levels |
| CampaignMembers per campaign | No hard limit (LDV consideration) |
| CampaignInfluence records | Depends on attribution model |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
