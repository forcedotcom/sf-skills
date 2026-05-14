# Field Service Lightning (FSL) Data Model Template

Pre-built data model for Salesforce Field Service (formerly Field Service Lightning) using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| WorkOrder | STD | Service jobs |
| WorkOrderLineItem | STD | Job tasks |
| ServiceAppointment | STD | Scheduled visits |
| ServiceResource | STD | Technicians/assets |
| ServiceTerritory | STD | Service areas |
| AssignedResource | STD | Appointment assignments |
| Shift | STD | Resource schedules |
| TimeSheet | STD | Time tracking |
| TimeSheetEntry | STD | Time details |
| ProductConsumed | STD | Parts used |
| ProductRequired | STD | Parts needed |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects WorkOrder,WorkOrderLineItem,ServiceAppointment,ServiceResource,ServiceTerritory \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% FIELD SERVICE LIGHTNING DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Work Order Structure
    WO["WorkOrder<br/>(count)"]
    WOLI["WorkOrderLineItem<br/>(count)"]

    %% Scheduling
    SA["ServiceAppointment<br/>(count)"]
    AR["AssignedResource<br/>(count)"]

    %% Resources
    SR["ServiceResource<br/>(count)"]
    ST["ServiceTerritory<br/>(count)"]
    STM["ServiceTerritoryMember<br/>(count)"]
    Shift["Shift<br/>(count)"]

    %% Time Tracking
    TS["TimeSheet<br/>(count)"]
    TSE["TimeSheetEntry<br/>(count)"]

    %% Products/Parts
    PC["ProductConsumed<br/>(count)"]
    PR["ProductRequired<br/>(count)"]

    %% Related
    Case["Case<br/>(count)"]
    Asset["Asset<br/>(count)"]
    Account["Account<br/>(count)"]

    %% Work Order Structure
    WO ==>|"MD"| WOLI
    Case -->|"LK"| WO
    Asset -->|"LK"| WO
    Account -->|"LK"| WO

    %% Work Order to Appointments
    WO -->|"LK"| SA
    WOLI -->|"LK"| SA
    ST -->|"LK"| SA

    %% Assignment
    SA ==>|"MD"| AR
    SR -->|"LK"| AR

    %% Resource Structure
    ST ==>|"MD"| STM
    SR -->|"LK"| STM
    SR ==>|"MD"| Shift

    %% Time Tracking
    SR -->|"LK"| TS
    TS ==>|"MD"| TSE
    WO -->|"LK"| TSE
    WOLI -->|"LK"| TSE

    %% Products
    WO ==>|"MD"| PC
    WO ==>|"MD"| PR
    WOLI ==>|"MD"| PC
    WOLI ==>|"MD"| PR

    %% Standard Objects - Sky Blue
    style WO fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WOLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SA fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style AR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ST fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style STM fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Shift fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style TS fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style TSE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PC fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Asset fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### FSL Object Hierarchy
```
Case/Asset → WorkOrder → WorkOrderLineItem → ServiceAppointment
                   ↓              ↓                    ↓
              ProductRequired  ProductConsumed   AssignedResource
                                                        ↓
                                                 ServiceResource
```

### Work Order vs Service Appointment
| Object | Purpose |
|--------|---------|
| WorkOrder | What needs to be done (job definition) |
| ServiceAppointment | When/where it will be done (scheduling) |

One WorkOrder can have multiple ServiceAppointments (multi-day jobs).

### Resource Types
| Type | Description |
|------|-------------|
| Technician | Field worker (User-based) |
| Crew | Group of technicians |
| Dispatcher | Scheduling coordinator |
| Tool | Equipment (Asset-based) |
| Contractor | External resource |

### Scheduling Policies
| Policy | Purpose |
|--------|---------|
| Customer First | Minimize customer wait |
| High Intensity | Maximize utilization |
| Soft Boundaries | Flexible territories |
| Emergency | Override normal rules |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core FSL flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    WO["WorkOrder"]
    SA["ServiceAppointment"]
    SR["ServiceResource"]
    ST["ServiceTerritory"]

    WO -->|"LK"| SA
    SA ==>|"assigned"| SR
    ST -->|"LK"| SA

    style WO fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SA fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ST fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Inventory/Parts Model

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    WO["WorkOrder"]
    WOLI["WorkOrderLineItem"]
    PR["ProductRequired"]
    PC["ProductConsumed"]
    PI["ProductItem"]
    PL["Location"]
    Product2["Product2"]

    WO ==>|"MD"| WOLI
    WOLI ==>|"MD"| PR
    WOLI ==>|"MD"| PC
    PR -->|"LK"| Product2
    PC -->|"LK"| Product2
    PI -->|"LK"| Product2
    PI -->|"LK"| PL

    style WO fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WOLI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PC fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PI fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style PL fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Time Tracking Model

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    SR["ServiceResource"]
    TS["TimeSheet"]
    TSE["TimeSheetEntry"]
    WO["WorkOrder"]
    SA["ServiceAppointment"]

    SR -->|"LK"| TS
    TS ==>|"MD"| TSE
    WO -->|"LK"| TSE
    SA -->|"LK"| TSE

    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style TS fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style TSE fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WO fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SA fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FIELD SERVICE LIGHTNING DATA MODEL (L→R)                                    │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                           WORK ORDER STRUCTURE
┌──────────────┐         ┌──────────────────┐         ┌──────────────────┐
│     CASE     │── LK ──>│    WORK_ORDER    │═══ MD ═>│ WORK_ORDER_LINE  │
│   (count)    │         │     (count)      │         │  ITEM (count)    │
└──────────────┘         └────────┬─────────┘         └────────┬─────────┘
                                  │                            │
┌──────────────┐                  │ LK                         │ LK
│    ASSET     │── LK ────────────┤                            │
│   (count)    │                  ▼                            ▼
└──────────────┘         ┌──────────────────┐         ┌──────────────────┐
                         │SERVICE_APPOINTMENT│◄────────│                  │
                         │     (count)      │         └──────────────────┘
                         └────────┬─────────┘
                                  │ MD
                                  ▼
                         ┌──────────────────┐         ┌──────────────────┐
                         │ASSIGNED_RESOURCE │── LK ──>│ SERVICE_RESOURCE │
                         │     (count)      │         │     (count)      │
                         └──────────────────┘         └────────┬─────────┘
                                                               │ MD
                                                               ▼
                                                      ┌──────────────────┐
                                                      │      SHIFT       │
                                                      │     (count)      │
                                                      └──────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| WorkOrder | WorkOrderLineItem | MD | Cascade delete |
| WorkOrder | ServiceAppointment | LK | Scheduling |
| ServiceAppointment | AssignedResource | MD | Cascade delete |
| ServiceResource | AssignedResource | LK | Resource reference |
| ServiceTerritory | ServiceTerritoryMember | MD | Cascade delete |
| ServiceResource | Shift | MD | Cascade delete |
| ServiceResource | TimeSheet | LK | Time owner |
| TimeSheet | TimeSheetEntry | MD | Cascade delete |
| WorkOrder | ProductConsumed | MD | Parts used |
| WorkOrder | ProductRequired | MD | Parts needed |
| Case | WorkOrder | LK | Source case |
| Asset | WorkOrder | LK | Serviced asset |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Work Order Line Items per WO | 200 (default) |
| Appointments per Work Order | Unlimited |
| Resources per Territory | Unlimited |
| Optimization batch size | 50 appointments |
| Shift duration | Max 24 hours |
| Service History retention | Configurable |

---

## FSL Managed Package Objects

| Object | Purpose |
|--------|---------|
| FSL__Scheduling_Policy__c | Optimization rules |
| FSL__Service_Goal__c | SLA definitions |
| FSL__Resource_Preference__c | Customer preferences |
| FSL__Time_Dependency__c | Appointment sequences |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom/Managed, Green=External
