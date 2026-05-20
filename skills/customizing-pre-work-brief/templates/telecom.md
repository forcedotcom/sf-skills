# Telecom / Fiber Install Seed Template

Scaffold. Not yet verified end-to-end against a live org.

## Business archetype

This customer provides residential and small-business telecommunications service — fiber-to-the-home, broadband internet, voice — and dispatches technicians for new-customer installs, service drops, outage repair, and equipment swaps. Signal strength readings, ONT (optical network terminal) serial numbers, and recent outage history at the address are the most useful grounding data for a pre-work brief.

## Recommended custom objects

### `Service_Drop__c`

Why: Each install or repair visit interacts with a specific service drop (the physical line from the street to the customer). Signal-strength history at the drop predicts whether the visit will be a quick swap or a longer troubleshoot.

| Field | Type | Notes |
|---|---|---|
| `Account__c` | Lookup → Account | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Asset__c` | Lookup → Asset | The ONT or modem at this drop |
| `Signal_Strength_Db__c` | Number(5,2) | Last measured signal strength in dBm |
| `Last_Reading_Date__c` | DateTime | When the signal was last measured |
| `ONT_Serial__c` | Text(50) | Optical network terminal serial number |
| `Connection_Type__c` | Picklist (restricted) | Fiber, Copper, Coax, Hybrid |

Name field: AutoNumber `SD-{0000}`.

### `Outage_History__c`

Why: A pattern of outages at the address (vs. a one-off) suggests the technician is walking into a recurring problem, not an isolated incident.

| Field | Type | Notes |
|---|---|---|
| `Account__c` | Lookup → Account | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Outage_Start__c` | DateTime | When the outage began |
| `Duration_Minutes__c` | Number(6,0) | How long it lasted |
| `Resolution_Type__c` | Picklist (restricted) | Self-healed, Tech-resolved, CenOps-resolved, Carrier escalation |
| `Ticket_Reference__c` | Text(50) | Internal incident ticket number |
| `Notes__c` | LongTextArea (500) | What was found and fixed |

Name field: AutoNumber `OH-{0000}`. Enable history tracking.

## WorkOrder field additions

| Field | Type | Notes |
|---|---|---|
| `Service_Drop__c` | Lookup → Service_Drop__c | Which drop this WO services |
| `Install_Type__c` | Picklist (restricted) | New Install, Upgrade, Repair, Disconnect |

## Standard objects + fields to query

| Object | Fields |
|---|---|
| Account | Name, Phone, BillingAddress, Description |
| Asset | Name, SerialNumber, InstallDate, Description, Status |
| Contact | Name, Phone, Email, MobilePhone |
| ServiceAppointment | AppointmentNumber, SchedStartTime, SchedEndTime, ArrivalWindowStartTime, ArrivalWindowEndTime, Address, Description, Status, Subject |

## Flow structure

Connector chain: `start → GetAccount → GetServiceDrop → GetAsset → GetOutageHistory → GetServiceAppointment → GetContact → BuildPrompt`.

`GetOutageHistory` sorts by `Outage_Start__c DESC LIMIT 5` for the 5 most-recent incidents at the address.

`GetServiceDrop` filters by `Id = $Input.WorkOrder.Service_Drop__c`.

## Prompt template section structure

1. **Mission and contact** — work to perform, customer name + phone + email.
2. **Service drop snapshot** — connection type, ONT serial, last signal reading + date. Call out signal degradation (>5 dBm drop from a typical -20 dBm baseline) as a likely root cause.
3. **Recent outage history** — count + dates of outages in the last 90 days. If 3+ outages in 30 days, flag as recurring problem.
4. **Appointment timing** — local arrival window, scheduled start/end.

## Rules

- Address the technician directly throughout.
- For "Repair" install types where outage history shows a recurring problem, recommend the technician check upstream (street-side) infrastructure before swapping customer equipment.
- For any field not grounded, write `[not provided]`.

## Cadence example

> "Perform a service-drop repair at the customer's residence. The customer reports intermittent outages over the last 10 days. Your contact is the account holder, reachable at the phone and email on file. Do not leave the site until you have confirmed sustained signal and tested speed at the ONT.
>
> The drop is a fiber connection terminating at ONT serial NS-FOH-882910. Last signal reading was -29.4 dBm on 2026-05-12, which is 9 dBm below the typical -20 dBm baseline for this neighborhood and is consistent with the customer's outage complaints.
>
> Outage history at this address: 4 incidents in the last 30 days, all resolved by the customer's modem auto-recovering after 2-15 minutes. This is a recurring pattern, not a one-off — check the street-side splitter and the OLT port assignment before swapping the ONT.
>
> Your appointment window is 1:00 PM to 5:00 PM today, with a scheduled start of 2:30 PM."

## Test data sample

Account: "Reyes Residence — 22 Chestnut St", with phone + billing address.

Asset: "ONT NS-FOH-882910", installed 2023-08-15.

Service_Drop: signal -29.4 dBm last reading, fiber connection.

Outage_History: 4 entries in last 30 days, all self-healed.

Contact: account holder.

Work Order: "Recurring outage investigation at 22 Chestnut St", Medium priority, install type Repair.
