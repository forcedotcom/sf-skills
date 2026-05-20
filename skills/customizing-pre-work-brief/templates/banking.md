# Banking / ATM Service Seed Template

Scaffold. Not yet verified end-to-end against a live org. Adapted from the Unisys customization work (2026-05-19) and standard banking field service patterns.

## Business archetype

This customer services banking and financial-services hardware — ATMs, bank branch teller stations, drive-thru tubes, vault systems — at retail bank locations and remote ATM sites. Technicians perform cash replenishment, hardware repair, software updates, and compliance audits. Cassette levels and last-audit timestamps are critical to every visit. Many sites have escort requirements, time-of-day windows, and dual-control protocols (two technicians required for vault access).

## Recommended custom objects

### `ATM_Cassette__c`

Why: Cash levels and denomination mix drive whether the visit is a routine replenishment vs. emergency.

| Field | Type | Notes |
|---|---|---|
| `Asset__c` | Lookup → Asset | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Cassette_Position__c` | Picklist (restricted) | Top, Middle Upper, Middle Lower, Bottom |
| `Denomination__c` | Picklist (restricted) | $1, $5, $10, $20, $50, $100 |
| `Current_Notes_Count__c` | Number(6,0) | Notes remaining at last reading |
| `Capacity__c` | Number(6,0) | Max notes the cassette holds |
| `Last_Replenishment__c` | Date | Used as sort key |

Name field: AutoNumber `CS-{0000}`.

### `Compliance_Check__c`

Why: Banking equipment requires periodic audits (PCI-DSS for card readers, ADA for screen-reader and audio, internal policy for camera coverage). Last-audit-date drives whether this visit needs to include a compliance pass.

| Field | Type | Notes |
|---|---|---|
| `Asset__c` | Lookup → Asset | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Audit_Type__c` | Picklist (restricted) | PCI-DSS, ADA, Camera Coverage, Lighting, Internal Policy |
| `Last_Audit_Date__c` | Date | When was this audit type last completed |
| `Next_Audit_Due__c` | Date | When the next audit is due |
| `Status__c` | Picklist (restricted) | Compliant, Action Required, Failed |
| `Notes__c` | LongTextArea (500) | Findings from last audit |

Name field: AutoNumber `CC-{0000}`. Enable history tracking (audit trail).

## WorkOrder field additions

| Field | Type | Notes |
|---|---|---|
| `Site_Access_Protocol__c` | Picklist (restricted) | Single Tech, Dual Control Required, Escort Required, After-Hours Only |
| `Cash_Handling_Required__c` | Checkbox | If true, the technician must hold a cash-handling certification |

## Standard objects + fields to query

| Object | Fields |
|---|---|
| Account | Name, Industry, Phone, Description |
| Asset | Name, SerialNumber, InstallDate, Description, Status |
| Contact | Name, Title, Phone, Email |
| ServiceAppointment | AppointmentNumber, SchedStartTime, SchedEndTime, ArrivalWindowStartTime, ArrivalWindowEndTime, Description, Status, Subject |

## Flow structure

Connector chain: `start → GetAccount → GetAsset → GetCassettes → GetComplianceChecks → GetServiceAppointment → GetContact → BuildPrompt`.

`GetCassettes` filters by `Asset__c = $Input.WorkOrder.AssetId`, sorts by `Last_Replenishment__c ASC` (oldest first surfaces what needs attention).

`GetComplianceChecks` filters by `Asset__c = $Input.WorkOrder.AssetId`, sorts by `Next_Audit_Due__c ASC` (most-urgent due-date first).

Both use `getFirstRecordOnly=true` for the demo. For real deployments where one ATM has 4-6 cassettes, switch to a Loop pattern (see Known Limitations in main SKILL.md).

## Prompt template section structure

1. **Mission and contact** — work to perform, on-site contact, end with site security reminder.
2. **Site access protocol** — single tech vs. dual control, time window, escort requirements. If `Cash_Handling_Required__c = true`, instruct the technician to verify their cash-handling cert.
3. **Cash status** — current cassette levels by denomination, time since last replenishment.
4. **Compliance status** — most recently due audit type, last completion date, any action items from the prior audit.

## Rules

- Address the technician directly throughout.
- For dual-control sites, explicitly state "you are the second technician" or "you are the lead; confirm your partner is on-site before opening the vault."
- Never disclose actual cash amounts in the brief — use ranges ("low", "below 25%", "near capacity") to reduce risk if the device is screenshot or shoulder-surfed.
- For any field not grounded, write `[not provided]`.

## Cadence example

> "Perform cash replenishment and a routine PCI-DSS compliance check on ATM-12 at the customer's downtown branch. Your on-site contact is the branch operations manager, reachable at the provided phone number and email. Do not leave the site until both tasks are completed and you have confirmed the device is back in service.
>
> This site requires dual-control access — confirm your partner is on-site before opening the vault. Service window is 6 AM to 8 AM only, before the branch opens to customers.
>
> Cassette status as of last reading: $20 cassette is below 25% capacity, $50 cassette is near capacity, $100 cassette is mid-range. Replenishment was last performed 11 days ago.
>
> The PCI-DSS audit is due within 30 days. The last audit on 2025-12-04 found one finding: receipt printer paper feed was misaligned. Verify the finding has been addressed."

## Test data sample

Account: "First Coastal Bank — Downtown Branch" (Banking), with description noting branch hours and ATM count.

Asset: "ATM-12 — Lobby", Serial `NCR-ATM-554821`, NCR SelfServ 84.

ATM_Cassette records: 4 entries (one per denomination), with current note counts and replenishment dates.

Compliance_Check records: 3 entries (PCI-DSS, ADA, Camera Coverage), with audit dates spanning the last 18 months.

Contact: branch operations manager.

Work Order: "Cash replenishment + PCI-DSS spot check — ATM-12", Medium priority.
