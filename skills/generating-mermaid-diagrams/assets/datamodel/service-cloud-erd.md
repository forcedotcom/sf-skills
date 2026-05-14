# Service Cloud Data Model Template

Pre-built data model for Salesforce Service Cloud using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Account | STD | Customer accounts |
| Contact | STD | Customer contacts |
| Case | STD | Support cases/tickets |
| CaseComment | STD | Case comments |
| Entitlement | STD | Support entitlements |
| ServiceContract | STD | Service agreements |
| ContractLineItem | STD | Contract products |
| Asset | STD | Customer installed products |
| KnowledgeArticle | STD | Knowledge base articles |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Account,Contact,Case,Entitlement,ServiceContract,Asset \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% SERVICE CLOUD DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Customer Objects
    Account["Account<br/>(count)"]
    Contact["Contact<br/>(count)"]
    Asset["Asset<br/>(count)"]

    %% Case Management
    Case["Case<br/>(count)"]
    CaseComment["CaseComment<br/>(count)"]

    %% Entitlement Objects
    Entitlement["Entitlement<br/>(count)"]
    ServiceContract["ServiceContract<br/>(count)"]
    CLI["ContractLineItem<br/>(count)"]

    %% Knowledge
    Knowledge["KnowledgeArticle<br/>(count)"]

    %% Relationships - Customer to Case
    Account -->|"LK"| Contact
    Account -->|"LK"| Case
    Contact -->|"LK"| Case
    Account -->|"LK"| Asset
    Asset -->|"LK"| Case

    %% Relationships - Case internal
    Case ==>|"MD"| CaseComment
    Case -->|"LK"| Knowledge

    %% Relationships - Entitlement
    Entitlement -->|"LK"| Case
    Account -->|"LK"| Entitlement
    Account -->|"LK"| ServiceContract
    ServiceContract -->|"LK"| Entitlement
    ServiceContract ==>|"MD"| CLI

    %% Standard Objects - Sky Blue
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Asset fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CaseComment fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Entitlement fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ServiceContract fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Knowledge fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Simplified Version (Core Objects Only)

For presentations focusing on core service flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account"]
    Contact["Contact"]
    Case["Case"]
    Entitlement["Entitlement"]

    Account -->|"LK"| Contact
    Account -->|"LK"| Case
    Contact -->|"LK"| Case
    Entitlement -->|"LK"| Case
    Account -->|"LK"| Entitlement

    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Entitlement fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SERVICE CLOUD DATA MODEL (L→R)                                             │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐          ┌──────────┐          ┌──────────────┐
│ ACCOUNT  │── LK ───>│ CONTACT  │── LK ───>│     CASE     │
│ (count)  │          │ (count)  │          │   (count)    │
└────┬─────┘          └──────────┘          └──────┬───────┘
     │                                             │
     │ LK                                          │ MD
     ▼                                             ▼
┌──────────────┐                           ┌──────────────┐
│    ASSET     │── LK ────────────────────>│ CASE_COMMENT │
│   (count)    │                           │   (count)    │
└──────────────┘                           └──────────────┘

┌──────────┐          ┌──────────────────┐          ┌───────────────────┐
│ ACCOUNT  │── LK ───>│ SERVICE_CONTRACT │═══ MD ══>│ CONTRACT_LINE_ITEM│
│          │          │     (count)      │          │      (count)      │
└────┬─────┘          └────────┬─────────┘          └───────────────────┘
     │                         │
     │ LK                      │ LK
     ▼                         ▼
┌──────────────┐        ┌──────────────┐
│ ENTITLEMENT  │◄───────│              │
│   (count)    │        └──────────────┘
└──────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Account | Contact | LK | Customer contacts |
| Account | Case | LK | Customer cases |
| Contact | Case | LK | Reporter/requestor |
| Case | CaseComment | MD | Cascade delete |
| Entitlement | Case | LK | SLA coverage |
| Account | Entitlement | LK | Customer entitlements |
| ServiceContract | Entitlement | LK | Contract includes entitlements |
| ServiceContract | ContractLineItem | MD | Cascade delete |
| Account | Asset | LK | Customer installed products |
| Asset | Case | LK | Asset-related cases |

---

## Service Cloud Patterns

### Case Flow
```
Customer → Contact → Case → CaseComment
              ↓
         Entitlement (SLA)
```

### Entitlement Coverage
```
Account → ServiceContract → Entitlement → Case
    └─────────────────────────────────────┘
                  (direct)
```

---

## Adding Custom Objects

Use orange styling for custom objects:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Case["Case<br/>(1,200)"]
    Survey["Survey_Response__c<br/>(450)"]

    Case -->|"LK"| Survey

    %% Standard - Sky Blue
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
    %% Custom - Orange
    style Survey fill:#fed7aa,stroke:#c2410c,color:#1f2937
```

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
