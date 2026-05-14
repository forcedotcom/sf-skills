# Consent Data Model Template

Pre-built data model for Salesforce Consent Management (GDPR/Privacy) using `flowchart LR` format with color coding and relationship indicators.

## Objects Included

| Object | Type | Description |
|--------|------|-------------|
| Individual | STD | Privacy identity |
| Contact | STD | Contact record |
| Lead | STD | Lead record |
| ContactPointEmail | STD | Email contact points |
| ContactPointPhone | STD | Phone contact points |
| ContactPointAddress | STD | Address contact points |
| DataUsePurpose | STD | Purpose definitions |
| ContactPointConsent | STD | Consent per contact point |
| CommSubscription | STD | Communication subscriptions |
| CommSubscriptionConsent | STD | Subscription consent |

---

## Query Org Metadata (Recommended)

Enrich diagram with live org data:

```bash
python3 ~/.claude/skills/generating-mermaid-diagrams/scripts/query-org-metadata.py \
    --objects Individual,ContactPointEmail,ContactPointPhone,DataUsePurpose,ContactPointConsent \
    --target-org myorg
```

---

## Mermaid Template (Preferred)

Left-to-right flowchart with color coding.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    %% ═══════════════════════════════════════════════════════════════
    %% CONSENT DATA MODEL (GDPR/PRIVACY)
    %% LEGEND: LK = Lookup (-->), MD = Master-Detail (==>)
    %% Colors: Blue = Standard, Orange = Custom, Green = External
    %% ═══════════════════════════════════════════════════════════════

    %% Party Objects
    Individual["Individual<br/>(count)"]
    Contact["Contact<br/>(count)"]
    Lead["Lead<br/>(count)"]

    %% Contact Points
    CPEmail["ContactPointEmail<br/>(count)"]
    CPPhone["ContactPointPhone<br/>(count)"]
    CPAddress["ContactPointAddress<br/>(count)"]

    %% Consent Objects
    DataUsePurpose["DataUsePurpose<br/>(count)"]
    CPConsent["ContactPointConsent<br/>(count)"]

    %% Subscriptions
    CommSub["CommSubscription<br/>(count)"]
    CommSubConsent["CommSubscriptionConsent<br/>(count)"]

    %% Individual Links
    Individual -->|"LK"| Contact
    Individual -->|"LK"| Lead

    %% Contact Points to Party
    Individual ==>|"MD"| CPEmail
    Individual ==>|"MD"| CPPhone
    Individual ==>|"MD"| CPAddress

    %% Consent
    CPEmail -->|"LK"| CPConsent
    CPPhone -->|"LK"| CPConsent
    DataUsePurpose -->|"LK"| CPConsent

    %% Subscriptions
    CommSub ==>|"MD"| CommSubConsent
    Contact -->|"LK"| CommSubConsent

    %% Standard Objects - Sky Blue
    style Individual fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style Lead fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPEmail fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPPhone fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPAddress fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style DataUsePurpose fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPConsent fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CommSub fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CommSubConsent fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Key Concepts

### Individual Object
- **Privacy identity** that links to Contact/Lead/User
- Required for consent tracking
- Can be auto-created when Contact/Lead created
- Stores global privacy preferences

### Contact Points
| Object | Purpose |
|--------|---------|
| ContactPointEmail | Email addresses |
| ContactPointPhone | Phone numbers |
| ContactPointAddress | Physical addresses |
| ContactPointSocialHandle | Social media IDs |

Each contact point links to an Individual.

### Consent Model
```
DataUsePurpose  →  ContactPointConsent  ←  ContactPoint
(e.g., Marketing)        (Opt-In/Out)        (Email/Phone)
```

### Consent Values
| Value | Meaning |
|-------|---------|
| **OptIn** | Consent given |
| **OptOut** | Consent withdrawn |
| **Seen** | Notice displayed |
| **NotSeen** | Notice not yet shown |

---

## Simplified Version (Core Objects Only)

For presentations focusing on core consent flow:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Individual["Individual"]
    CPEmail["ContactPointEmail"]
    DataUsePurpose["DataUsePurpose"]
    CPConsent["ContactPointConsent"]

    Individual ==>|"MD"| CPEmail
    CPEmail -->|"LK"| CPConsent
    DataUsePurpose -->|"LK"| CPConsent

    style Individual fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPEmail fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style DataUsePurpose fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CPConsent fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## Communication Subscriptions Model

For email preference centers:

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 80}} }%%
flowchart LR
    Contact["Contact"]
    CommSub["CommSubscription<br/>(Newsletter)"]
    CommSubConsent["CommSubscriptionConsent"]
    CommChannel["CommSubscriptionChannel"]

    CommSub ==>|"MD"| CommSubConsent
    Contact -->|"LK"| CommSubConsent
    CommSub ==>|"MD"| CommChannel

    style Contact fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CommSub fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CommSubConsent fill:#bae6fd,stroke:#0369a1,color:#1f2937
    style CommChannel fill:#bae6fd,stroke:#0369a1,color:#1f2937
```

---

## ASCII Fallback

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CONSENT DATA MODEL (GDPR/PRIVACY) (L→R)                                     │
│  Legend: LK = Lookup (-->), MD = Master-Detail (==>)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  INDIVIDUAL  │─────── LK ──────┬──────────────────────────────────┐
│   (count)    │                 │                                  │
└──────┬───────┘                 ▼                                  ▼
       │                  ┌──────────────┐              ┌──────────────┐
       │                  │   CONTACT    │              │     LEAD     │
       │                  │   (count)    │              │   (count)    │
       │                  └──────────────┘              └──────────────┘
       │
       ├═══ MD ═══>┌────────────────────┐
       │           │ CONTACT_POINT_EMAIL│─── LK ──>┌────────────────────┐
       │           │      (count)       │          │CONTACT_POINT_      │
       │           └────────────────────┘          │    CONSENT         │
       │                                           │    (count)         │
       ├═══ MD ═══>┌────────────────────┐          └─────────┬──────────┘
       │           │ CONTACT_POINT_PHONE│─── LK ───────────>│
       │           │      (count)       │                   │
       │           └────────────────────┘                   │
       │                                                    │ LK
       └═══ MD ═══>┌────────────────────┐                   │
                   │CONTACT_POINT_ADDR  │          ┌────────┴───────────┐
                   │      (count)       │          │  DATA_USE_PURPOSE  │
                   └────────────────────┘          │     (count)        │
                                                   └────────────────────┘
```

---

## Key Relationships Summary

| Parent | Child | Type | Behavior |
|--------|-------|------|----------|
| Individual | Contact | LK | Privacy identity |
| Individual | Lead | LK | Privacy identity |
| Individual | ContactPointEmail | MD | Cascade delete |
| Individual | ContactPointPhone | MD | Cascade delete |
| Individual | ContactPointAddress | MD | Cascade delete |
| ContactPointEmail | ContactPointConsent | LK | Email consent |
| ContactPointPhone | ContactPointConsent | LK | Phone consent |
| DataUsePurpose | ContactPointConsent | LK | Purpose reference |
| CommSubscription | CommSubscriptionConsent | MD | Cascade delete |
| Contact | CommSubscriptionConsent | LK | Subscriber |

---

## GDPR Compliance Considerations

| Right | Implementation |
|-------|----------------|
| **Right to Access** | Query Individual + Contact Points |
| **Right to Rectification** | Update Contact Points |
| **Right to Erasure** | Delete Individual (cascades) |
| **Right to Restrict** | Set ConsentCaptureSource |
| **Right to Object** | ContactPointConsent = OptOut |

---

## Limits & Considerations

| Limit | Value |
|-------|-------|
| Contact Points per Individual | Unlimited |
| Data Use Purposes | Unlimited |
| Consent records | LDV consideration |
| Audit trail retention | Configurable |

---

## Best Practices

1. **Use `flowchart LR`** - Left-to-right flow for readability
2. **Keep objects simple** - Name + record count only
3. **Replace `(count)` placeholders** - With actual counts from query
4. **Add LDV indicator** - For objects >2M records: `LDV[~4M]`
5. **Color code object types** - Blue=Standard, Orange=Custom, Green=External
