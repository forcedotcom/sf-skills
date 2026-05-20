# HVAC Commercial Maintenance Seed Template

Canonical seed. Verified end-to-end against `afvuser` trial org, 2026-05-20: deployed 2 custom objects, 11 fields, a from-scratch flow, prompt template, permission set, and a test WO + SA. Brief renders on Field Service Mobile.

## Business archetype

This customer operates commercial HVAC systems — rooftop units, chillers, heat pumps, and associated controls — at retail, healthcare, education, grocery, and office locations. Technicians perform planned maintenance, emergency break/fix, and refrigerant handling. Refrigerant logs are EPA-required and must be referenced for any work involving the refrigerant circuit. Site access constraints (escort requirements, hours, tenant coordination) and SLA tier (response-time commitment) shape every visit.

## Recommended custom objects

### `Maintenance_Contract__c`

Why: SLA tier and coverage scope are the most-referenced grounding context in commercial HVAC briefs. A Platinum-tier customer with a 4-hour response commitment needs the technician to know that before they leave.

| Field | Type | Notes |
|---|---|---|
| `Account__c` | Lookup → Account | `<deleteConstraint>SetNull</deleteConstraint>`, not required |
| `SLA_Tier__c` | Picklist (restricted) | Platinum (4hr), Gold (8hr), Silver (24hr), Bronze (48hr) |
| `Coverage_Scope__c` | LongTextArea (1000) | Free-text scope of services covered |
| `Site_Access_Notes__c` | LongTextArea (500) | Gate codes, escort requirements, hours, tenant coordination |
| `Required_Certifications__c` | Text (255) | EPA Section 608 Universal, OSHA 10, etc. |

Name field: AutoNumber `MC-{0000}`.

### `Refrigerant_Log__c`

Why: EPA-required documentation. Last-service-date and prior charge level inform whether the current visit is a leak diagnostic vs. routine top-up.

| Field | Type | Notes |
|---|---|---|
| `Asset__c` | Lookup → Asset | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Refrigerant_Type__c` | Picklist (unrestricted) | R-410A, R-454B, R-32, R-22 (legacy) |
| `Charge_Level_Lbs__c` | Number(6,2) | Pounds of refrigerant in system |
| `Last_Service_Date__c` | Date | Used as sort key (most recent first) |
| `Notes__c` | LongTextArea (500) | Leak detection results, top-off amounts |

Name field: AutoNumber `RL-{0000}`. Enable history tracking (compliance audit trail).

## WorkOrder field additions

| Field | Type | Notes |
|---|---|---|
| `Maintenance_Contract__c` | Lookup → Maintenance_Contract__c | Not required; flow uses `$Input.WorkOrder.Maintenance_Contract__c` to fetch SLA + coverage |

## Standard objects + fields to query

| Object | Fields beyond the default flow's set |
|---|---|
| Account | Name, Industry, Phone, Description |
| Asset | Name, SerialNumber, InstallDate, Description, Status |
| Contact | Name, Title, Phone, Email |
| ServiceAppointment | AppointmentNumber, SchedStartTime, SchedEndTime, ArrivalWindowStartTime, ArrivalWindowEndTime, EarliestStartTime, DueDate, Description, Status, Subject |

Avoid `Asset.ProductDescription` — it's read-only for non-admin profiles in some org configurations. Use `Asset.Description` for narrative text instead.

## Flow structure

Connector chain: `start → GetAccount → GetAsset → GetMaintenanceContract → GetRefrigerantLog → GetServiceAppointment → GetContact → BuildPrompt`.

All record lookups use `getFirstRecordOnly=true`. The `BuildPrompt` assignment writes a structured `$Output.Prompt` with sections: Work Order, Customer, On-site Contact, Asset, Maintenance Contract, Most Recent Refrigerant Log, Service Appointment.

`GetRefrigerantLog` sorts by `Last_Service_Date__c DESC` to surface the latest entry.

## Prompt template section structure

Four sections, in order:

1. **Mission and contact** — opens with active-voice imperative ("Perform a refrigerant top-up..."), names contact + phone + email, ends with "do not leave the site until the issue is resolved."
2. **Customer and SLA** — customer name, SLA tier, coverage scope. Call out Platinum/Gold tiers as high-priority.
3. **Site access and certifications** — site access notes, required certifications. Instruct technician to verify they hold the certs before arrival.
4. **Equipment and refrigerant context** — asset (model, serial, install date, status), most recent refrigerant log (type, prior charge, last service date). Call out anomalies: service >12 months ago, charge below normal range.

## Rules

- Address the technician directly throughout (second person).
- Opening sentence must use an active-voice verb appropriate to the work.
- For any field not grounded, write `[not provided]`.
- All times in technician's local time zone.
- Brief under 300 words.
- Prose paragraphs, not bullet lists.
- If most recent refrigerant service >12 months ago OR charge level below typical spec for the unit, explicitly note this as a likely contributor to the current issue.

## Cadence example

> "Perform a refrigerant top-up and leak inspection on the building's rooftop unit RTU-3. The customer reports inadequate cooling during peak hours; you will verify charge level and locate any leaks before adjusting refrigerant. Your on-site contact is Maria Reyes, Facilities Manager, reachable at 415-555-0118 and m.reyes@example.com. Do not leave the site until the issue is resolved.
>
> This is a Platinum SLA customer (4-hour response commitment). Coverage scope includes preventive maintenance and emergency break/fix on all rooftop units in the building.
>
> Site access requires escort by building security; check in at the loading dock between 7 AM and 6 PM. Confirm before arrival that you hold an active EPA Section 608 Universal certification, which is required for any refrigerant handling on this site.
>
> The asset is a 10-ton rooftop unit installed 2018, currently in service. The most recent refrigerant log shows R-410A charge of 14.2 lbs, last serviced 2025-09-12. Charge level is below the typical 16 lb spec for this unit, which is consistent with the cooling complaint."

## Test data sample

Account: "Greenfield Grocery — Mission District" (Retail), with description noting refrigeration criticality.

Asset: "Rooftop Unit RTU-3 — Produce Section", Serial `CR-RTU-388291`, Carrier 48HC 10-ton, installed 2018-06-12.

Maintenance_Contract: Platinum (4hr), full coverage scope text, site access notes, required certs `EPA Section 608 Universal, OSHA 10`.

Refrigerant_Log: R-410A, 14.2 lbs (below 16 lb spec), last service 2025-09-12.

Contact: Maria Reyes, Store Facilities Manager.

Work Order: "Refrigerant top-up and leak inspection — RTU-3", High priority, with description detailing the cooling complaint and required diagnostic steps.

Service Appointment: today, 2-hour window, assigned to the chosen Service Resource.
