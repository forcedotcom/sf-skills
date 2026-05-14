# Salesforce Scheduler Data Model Template

Pre-built data model for Salesforce Scheduler (Lightning Scheduler) using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| ServiceAppointment | STD | Scheduled appointments |
| ServiceResource | STD | People/equipment |
| ServiceTerritory | STD | Service locations |
| ServiceTerritoryMember | STD | Resource assignments |
| WorkType | STD | Service types |
| WorkTypeGroup | STD | Grouped work types |
| AssignedResource | STD | Appointment assignments |
| ResourceAbsence | STD | Time off/unavailability |
| TimeSlot | STD | Available time slots |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects ServiceAppointment,ServiceResource,ServiceTerritory,WorkType \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% SALESFORCE SCHEDULER DATA MODEL
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Core Scheduling Objects
    SA["ServiceAppointment<br/>(count)"]
    SR["ServiceResource<br/>(count)"]
    ST["ServiceTerritory<br/>(count)"]

    %% Resource Assignments
    STM["ServiceTerritoryMember<br/>(count)"]
    AR["AssignedResource<br/>(count)"]

    %% Work Types
    WT["WorkType<br/>(count)"]
    WTG["WorkTypeGroup<br/>(count)"]
    WTGM["WorkTypeGroupMember<br/>(count)"]

    %% Availability
    RA["ResourceAbsence<br/>(count)"]
    TS["TimeSlot<br/>(count)"]

    %% Related Objects
    Account["Account<br/>(count)"]
    Contact["Contact<br/>(count)"]
    User["User<br/>(count)"]

    %% Service Appointment
    Account -->|"LK"| SA
    Contact -->|"LK"| SA
    ST -->|"LK"| SA
    WT -->|"LK"| SA

    %% Resource Structure
    User -->|"LK"| SR
    SR ==>|"MD"| STM
    ST -->|"LK"| STM

    %% Appointment Assignment
    SA ==>|"MD"| AR
    SR -->|"LK"| AR

    %% Work Type Groups
    WTG ==>|"MD"| WTGM
    WT -->|"LK"| WTGM

    %% Availability
    SR ==>|"MD"| RA

    %% Operating Hours
    ST -->|"LK"| TS

    %% Standard Objects - Sky Blue
    style SA fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ST fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style STM fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style AR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WT fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WTG fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style WTGM fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style RA fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style TS fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style User fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Scheduling Flow
```
Customer (Contact) → WorkType → ServiceAppointment ← ServiceResource
                                        ↓
                               ServiceTerritory
```

### Resource Availability
| Object | Purpose |
|--------|---------|
| OperatingHours | Business hours definition |
| TimeSlot | Available booking slots |
| ResourceAbsence | Time off, breaks |
| ServiceTerritoryMember | Territory assignment + hours |

### ServiceResource Types
| Type | Description |
|------|-------------|
| Technician | Field service worker |
| Dispatcher | Scheduling coordinator |
| Crew | Group of resources |
| Asset | Equipment, vehicles |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core scheduling flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Contact["Contact"]
    SA["ServiceAppointment"]
    SR["ServiceResource"]
    ST["ServiceTerritory"]

    Contact -->|"LK"| SA
    ST -->|"LK"| SA
    SA ==>|"MD assigned"| SR

    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SA fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style ST fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Territory & Resource Model

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    ST["ServiceTerritory"]
    SR["ServiceResource"]
    STM["ServiceTerritoryMember"]
    OpHrs["OperatingHours"]

    ST ==>|"MD"| STM
    SR -->|"LK"| STM
    ST -->|"LK"| OpHrs

    style ST fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style SR fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style STM fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style OpHrs fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SALESFORCE SCHEDULER DATA MODEL (L→R)                                       │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐                              ┌──────────────────────┐
│   ACCOUNT    │──────────── LK ─────────────>│ SERVICE_APPOINTMENT  │
│   (count)    │                              │       (count)        │
└──────────────┘                              └──────────┬───────────┘
                                                         │
┌──────────────┐                                         │ MD
│   CONTACT    │──────────── LK ─────────────────────────┤
│   (count)    │                                         ▼
└──────────────┘                              ┌──────────────────────┐
                                              │   ASSIGNED_RESOURCE  │
┌──────────────┐                              │       (count)        │
│  WORK_TYPE   │──────────── LK ──────────────│                      │
│   (count)    │                              └──────────┬───────────┘
└──────────────┘                                         │ LK
                                                         ▼
┌───────────────────┐         ┌────────────────────────────────────────┐
│ SERVICE_TERRITORY │═══ MD ═>│ SERVICE_TERRITORY_MEMBER               │
│     (count)       │         │            (count)                     │
└───────────────────┘         └────────────────────┬───────────────────┘
         │                                         │ LK
         │ LK                                      ▼
         └───────────────────────────────>┌──────────────────────┐
                                          │   SERVICE_RESOURCE   │
                                          │       (count)        │
                                          └──────────┬───────────┘
                                                     │ MD
                                                     ▼
                                          ┌──────────────────────┐
                                          │   RESOURCE_ABSENCE   │
                                          │       (count)        │
                                          └──────────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| ServiceTerritory | ServiceTerritoryMember | MD | Cascade delete |
| ServiceResource | ServiceTerritoryMember | LK | Resource reference |
| ServiceAppointment | AssignedResource | MD | Cascade delete |
| ServiceResource | AssignedResource | LK | Resource reference |
| ServiceResource | ResourceAbsence | MD | Cascade delete |
| WorkTypeGroup | WorkTypeGroupMember | MD | Cascade delete |
| WorkType | WorkTypeGroupMember | LK | Work type reference |
| Account | ServiceAppointment | LK | Customer |
| Contact | ServiceAppointment | LK | Contact person |
| ServiceTerritory | ServiceAppointment | LK | Service location |
| WorkType | ServiceAppointment | LK | Appointment type |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Resources per territory | Unlimited |
| Territories per resource | Unlimited |
| Appointments per day | Performance consideration |
| Operating hours slots | 24 per day max |
| Time slot duration | Configurable (minutes) |

---

## Scheduler vs Field Service

| Feature | Scheduler | Field Service |
|---------|-----------|---------------|
| Focus | Appointments | Work orders |
| Optimization | Basic | Advanced (FSL) |
| Gantt | No | Yes |
| Dispatch | Manual | Automated |
| Mobile | Standard app | FSL Mobile |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
