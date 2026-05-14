# Forecasting Data Model Template

Pre-built data model for Salesforce Collaborative Forecasts using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| ForecastingType | STD | Forecast configuration |
| ForecastingItem | STD | Individual forecasts |
| ForecastingQuota | STD | User quotas |
| ForecastingAdjustment | STD | Manager adjustments |
| Opportunity | STD | Source opportunities |
| OpportunitySplit | STD | Revenue splits |
| User | STD | Forecast owners |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects ForecastingItem,ForecastingQuota,Opportunity,OpportunitySplit \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% COLLABORATIVE FORECASTS DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Forecast Configuration
    FType["ForecastingType<br/>(count)"]

    %% Forecast Data
    FItem["ForecastingItem<br/>(count)"]
    FQuota["ForecastingQuota<br/>(count)"]
    FAdjust["ForecastingAdjustment<br/>(count)"]

    %% Source Objects
    Opportunity["Opportunity<br/>(count)"]
    OppSplit["OpportunitySplit<br/>(count)"]

    %% Users
    User["User<br/>(count)"]

    %% Period
    Period["Period<br/>(count)"]

    %% Forecast Type Configuration
    FType -->|"LK"| FItem
    FType -->|"LK"| FQuota

    %% Forecast Items
    User -->|"LK"| FItem
    Period -->|"LK"| FItem
    Opportunity -->|"LK"| FItem

    %% Quotas
    User -->|"LK"| FQuota
    Period -->|"LK"| FQuota

    %% Adjustments
    FItem -->|"LK"| FAdjust
    User -->|"adjusts"| FAdjust

    %% Opportunity Splits
    Opportunity ==>|"MD"| OppSplit
    User -->|"LK"| OppSplit

    %% Standard Objects - Sky Blue
    style FType fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FQuota fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FAdjust fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OppSplit fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style User fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Period fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Forecasting Types
| Type | Source Field | Description |
|------|--------------|-------------|
| **Opportunity Revenue** | Amount | Standard opportunity forecasting |
| **Opportunity Quantity** | Quantity | Unit-based forecasting |
| **Product Family** | Product2.Family | By product category |
| **Opportunity Splits** | Split Amount | Team selling |
| **Custom Measure** | Custom field | Custom currency/number |

### Forecast Categories
| Category | Stage Mapping |
|----------|---------------|
| Pipeline | Early stages |
| Best Case | High probability |
| Commit | Committed deals |
| Closed | Won deals |
| Omitted | Excluded from forecast |

### Forecast Rollup Hierarchy
```
CEO
 └── VP Sales
      ├── Regional Manager 1
      │    ├── Sales Rep A
      │    └── Sales Rep B
      └── Regional Manager 2
           └── Sales Rep C
```

Forecasts roll up through **Role Hierarchy** or **Forecast Hierarchy**.

---

## Simplified Version (Core Objects Only)

For presentations focusing on core forecast flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    User["User"]
    Opportunity["Opportunity"]
    FItem["ForecastingItem"]
    FQuota["ForecastingQuota"]

    User -->|"owns"| Opportunity
    Opportunity -->|"contributes"| FItem
    User -->|"has"| FQuota
    User -->|"owns"| FItem

    style User fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FItem fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FQuota fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Opportunity Splits Model

For team selling with revenue splits:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Opportunity["Opportunity<br/>($100K)"]
    Split1["OpportunitySplit<br/>(Rep A: 60%)"]
    Split2["OpportunitySplit<br/>(Rep B: 40%)"]
    FItem1["ForecastingItem<br/>(Rep A: $60K)"]
    FItem2["ForecastingItem<br/>(Rep B: $40K)"]

    Opportunity ==>|"MD"| Split1
    Opportunity ==>|"MD"| Split2
    Split1 -->|"contributes"| FItem1
    Split2 -->|"contributes"| FItem2

    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Split1 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Split2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FItem1 fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style FItem2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  COLLABORATIVE FORECASTS DATA MODEL (L→R)                                    │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│ FORECASTING_TYPE │─────── LK ──────┬──────────────────────────────────┐
│     (count)      │                 │                                  │
└──────────────────┘                 ▼                                  ▼
                          ┌──────────────────┐              ┌──────────────────┐
                          │ FORECASTING_ITEM │              │FORECASTING_QUOTA │
                          │     (count)      │              │     (count)      │
                          └────────┬─────────┘              └────────┬─────────┘
                                   │                                 │
                                   │ LK                              │ LK
                                   ▼                                 ▼
┌──────────────┐         ┌──────────────────┐              ┌──────────────────┐
│ OPPORTUNITY  │── LK ──>│                  │              │      USER        │
│   (count)    │         │                  │<──── LK ─────│     (count)      │
└──────┬───────┘         └──────────────────┘              └──────────────────┘
       │
       │ MD
       ▼
┌──────────────────┐
│ OPPORTUNITY_SPLIT│
│     (count)      │
└──────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| ForecastingType | ForecastingItem | LK | Type configuration |
| ForecastingType | ForecastingQuota | LK | Type configuration |
| User | ForecastingItem | LK | Forecast owner |
| User | ForecastingQuota | LK | Quota owner |
| Period | ForecastingItem | LK | Time period |
| Period | ForecastingQuota | LK | Time period |
| Opportunity | ForecastingItem | LK | Source opportunity |
| Opportunity | OpportunitySplit | MD | Cascade delete |
| User | OpportunitySplit | LK | Split owner |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Forecasting types | 4 (standard) + 4 (custom) |
| Forecast hierarchy levels | Role hierarchy depth |
| Splits per opportunity | Unlimited |
| Quota periods | Fiscal periods |
| Adjustment history | 12 months |

---

## Forecast Hierarchy vs Role Hierarchy

| Option | Use Case |
|--------|----------|
| **Role Hierarchy** | Forecasts follow org chart |
| **Forecast Hierarchy** | Custom forecast rollup path |
| **Territory Hierarchy** | Territory-based forecasting |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
