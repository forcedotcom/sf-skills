# Territory Management Data Model Template

Pre-built data model for Salesforce Enterprise Territory Management (Territory2) using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Territory2Model | STD | Territory model container |
| Territory2 | STD | Individual territories |
| Territory2Type | STD | Territory classification |
| UserTerritory2Association | STD | User-to-territory assignments |
| ObjectTerritory2Association | STD | Account-to-territory assignments |
| RuleTerritory2Association | STD | Assignment rule linkage |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Territory2Model,Territory2,Territory2Type,UserTerritory2Association,ObjectTerritory2Association \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% ENTERPRISE TERRITORY MANAGEMENT DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Territory Model (Container)
    T2Model["Territory2Model<br/>(count)"]

    %% Territory Structure
    Territory2["Territory2<br/>(count)"]
    T2Type["Territory2Type<br/>(count)"]

    %% Associations
    UserT2Assoc["UserTerritory2Association<br/>(count)"]
    ObjT2Assoc["ObjectTerritory2Association<br/>(count)"]
    RuleT2Assoc["RuleTerritory2Association<br/>(count)"]

    %% Related Objects
    User["User<br/>(count)"]
    Account["Account<br/>(count)"]

    %% Relationships - Model Structure
    T2Model ==>|"MD"| Territory2
    T2Model ==>|"MD"| T2Type
    T2Type -->|"LK"| Territory2

    %% Territory Hierarchy (Self-reference)
    Territory2 -.->|"Parent"| Territory2

    %% Relationships - User Assignments
    Territory2 ==>|"MD"| UserT2Assoc
    User -->|"LK"| UserT2Assoc

    %% Relationships - Account Assignments
    Territory2 ==>|"MD"| ObjT2Assoc
    Account -->|"LK"| ObjT2Assoc

    %% Relationships - Rule Assignments
    Territory2 ==>|"MD"| RuleT2Assoc

    %% Standard Objects - Sky Blue
    style T2Model fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Territory2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style T2Type fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style UserT2Assoc fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ObjT2Assoc fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style RuleT2Assoc fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style User fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Territory2Model States
| State | Description |
|-------|-------------|
| **Planning** | Model being configured (not active) |
| **Active** | Live model in use |
| **Archived** | Historical model (read-only) |

Only **one model can be Active** at a time.

### Territory Hierarchy
- Territories support **ParentTerritory2Id** self-lookup
- Creates hierarchy within a model
- Opportunity access rolls up through hierarchy

### Assignment Types
| Object | Purpose |
|--------|---------|
| **UserTerritory2Association** | Assigns users to territories |
| **ObjectTerritory2Association** | Assigns accounts to territories |
| **RuleTerritory2Association** | Links assignment rules to territories |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core territory structure:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    T2Model["Territory2Model"]
    Territory2["Territory2"]
    User["User"]
    Account["Account"]

    T2Model ==>|"MD"| Territory2
    Territory2 -.->|"Parent"| Territory2
    Territory2 -->|"assigns"| User
    Territory2 -->|"assigns"| Account

    style T2Model fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Territory2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style User fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Opportunity Territory Assignment

Territory Management also affects Opportunities:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Territory2["Territory2"]
    Account["Account"]
    Opportunity["Opportunity"]

    Territory2 -->|"assigns"| Account
    Account -->|"LK"| Opportunity
    Territory2 -->|"Territory2Id"| Opportunity

    style Territory2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTERPRISE TERRITORY MANAGEMENT DATA MODEL (L→R)                           │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│ TERRITORY2_MODEL │═══ MD ═>│   TERRITORY2     │◄──── Parent (self)
│     (count)      │         │     (count)      │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         │ MD                         ├─── MD ──>┌────────────────────────┐
         ▼                            │          │ USER_TERRITORY2_ASSOC  │
┌──────────────────┐                  │          │       (count)          │
│ TERRITORY2_TYPE  │── LK ───────────>┤          └───────────┬────────────┘
│     (count)      │                  │                      │ LK
└──────────────────┘                  │                      ▼
                                      │          ┌────────────────────────┐
                                      │          │         USER           │
                                      │          │       (count)          │
                                      │          └────────────────────────┘
                                      │
                                      ├─── MD ──>┌────────────────────────┐
                                      │          │ OBJECT_TERRITORY2_ASSOC│
                                      │          │       (count)          │
                                      │          └───────────┬────────────┘
                                      │                      │ LK
                                      │                      ▼
                                      │          ┌────────────────────────┐
                                      │          │       ACCOUNT          │
                                      │          │       (count)          │
                                      │          └────────────────────────┘
                                      │
                                      └─── MD ──>┌────────────────────────┐
                                                 │ RULE_TERRITORY2_ASSOC  │
                                                 │       (count)          │
                                                 └────────────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Territory2Model | Territory2 | MD | Cascade delete |
| Territory2Model | Territory2Type | MD | Cascade delete |
| Territory2Type | Territory2 | LK | Type classification |
| Territory2 | Territory2 | LK | Parent (hierarchy) |
| Territory2 | UserTerritory2Association | MD | Cascade delete |
| Territory2 | ObjectTerritory2Association | MD | Cascade delete |
| Territory2 | RuleTerritory2Association | MD | Cascade delete |
| User | UserTerritory2Association | LK | User assignment |
| Account | ObjectTerritory2Association | LK | Account assignment |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Territory models (total) | Unlimited (1 active) |
| Territories per model | 1,000 |
| Territory hierarchy levels | 10 |
| Users per territory | No hard limit |
| Accounts per territory | No hard limit |
| Assignment rules | 15 per model |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
