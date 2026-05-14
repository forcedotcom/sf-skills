# Salesforce Data Model Template

Data model diagram template using `flowchart LR` for visualizing Salesforce object relationships with color coding, LDV markers, and relationship type labels.

## When to Use
- Documenting object relationships
- Planning data model changes
- Understanding existing schema
- Design reviews and architecture discussions

## Cloud-Specific Templates

For pre-built cloud diagrams, see:
- **[Sales Cloud ERD](sales-cloud-erd.md)** - Account, Contact, Opportunity, Lead, Product, Campaign
- **[Service Cloud ERD](service-cloud-erd.md)** - Case, Entitlement, Knowledge, ServiceContract

## Preferred Format: `flowchart LR`

Use `flowchart LR` (left-to-right) for data model diagrams. This format supports:
- Individual node color coding by object type
- Thick arrows (`==>`) for Master-Detail relationships
- Left-to-right flow for readability
- Simple object nodes (name + record count, no fields)

---

## Quick Reference

### Object Type Colors

| Type | Fill | Stroke | Example |
|------|------|--------|---------|
| Standard | `#bae6fd` | `#0369a1` | Account, Contact |
| Custom (`__c`) | `#fed7aa` | `#c2410c` | Invoice__c |
| External (`__x`) | `#a7f3d0` | `#047857` | SAP_Order__x |

### Relationship Arrows

| Arrow | Type | Meaning |
|-------|------|---------|
| `-->` | Lookup (LK) | Optional parent, no cascade delete |
| `==>` | Master-Detail (MD) | Required parent, cascade delete |
| `-.->` | Special | Conversion, indirect relationship |

### Metadata Annotations

| Annotation | When to Use |
|------------|-------------|
| `LDV[~4M]` | Record count >2M |
| `(317)` | Record count <2M |

---

## Query Org Metadata

Enrich diagrams with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Account,Contact,Opportunity,Case \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    Account["Account<br/>(317)"]
    Contact["Contact<br/>(346)"]
    Opportunity["Opportunity<br/>(6)"]
    Case["Case<br/>(2)"]

    Account -->|"LK"| Contact
    Account -->|"LK"| Opportunity
    Account -->|"LK"| Case
    Contact -->|"LK"| Case

    %% Standard Objects - Sky Blue
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Opportunity fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback Template

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DATA MODEL (L→R)                                                           │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────┐         ┌────────────────┐         ┌────────────────┐
│    ACCOUNT     │── LK ──>│    CONTACT     │── LK ──>│     CASE       │
│     (317)      │         │     (346)      │         │      (2)       │
└───────┬────────┘         └────────────────┘         └────────────────┘
        │
        │ LK
        ▼
┌────────────────┐
│  OPPORTUNITY   │
│      (6)       │
└────────────────┘
```

---

## Custom Object Example

Shows mixing Standard (blue) and Custom (orange) objects:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% Standard Objects
    Account["Account<br/>(317)"]
    Product2["Product2<br/>(50)"]

    %% Custom Objects
    Invoice["Invoice__c<br/>(1,200)"]
    InvoiceLine["Invoice_Line_Item__c<br/>(5,400)"]

    Account ==>|"MD"| Invoice
    Invoice ==>|"MD"| InvoiceLine
    Product2 -->|"LK"| InvoiceLine

    %% Standard - Sky Blue
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Product2 fill:#bae6fd,stroke:#0369a1,color:#1f2937

    %% Custom - Orange
    style Invoice fill:#fed7aa,stroke:#c2410c,color:#1f2937
    style InvoiceLine fill:#fed7aa,stroke:#c2410c,color:#1f2937
```

---

## External Object Example

Shows Standard, Custom, and External objects together:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account<br/>(317)"]
    SAPOrder["SAP_Order__x<br/>(ext)"]
    OrderLine["Order_Line__c<br/>(2,400)"]

    Account -->|"LK"| SAPOrder
    SAPOrder -->|"LK"| OrderLine

    %% Standard - Sky Blue
    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937

    %% External - Green
    style SAPOrder fill:#a7f3d0,stroke:#047857,color:#1f2937

    %% Custom - Orange
    style OrderLine fill:#fed7aa,stroke:#c2410c,color:#1f2937
```

---

## LDV (Large Data Volume) Example

Objects with >2M records show LDV indicator:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Account["Account<br/>LDV[~4M]"]
    Contact["Contact<br/>LDV[~8M]"]
    Case["Case<br/>(450K)"]

    Account -->|"LK"| Contact
    Account -->|"LK"| Case
    Contact -->|"LK"| Case

    style Account fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Case fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow is easier to read
2. **Keep objects simple** - Show name + record count only (no fields)
3. **Color code by type** - Blue=Standard, Orange=Custom, Green=External
4. **Use correct arrows** - `-->` for Lookup, `==>` for Master-Detail
5. **Add LDV indicators** - For objects >2M records
6. **Use API names** - Show `Account` not "Accounts"

---

## ERD Conventions

See **[ERD Conventions](../../references/erd-conventions.md)** for full documentation.
