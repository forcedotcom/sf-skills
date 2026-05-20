# Retail Merchandising Field Service Seed Template

Scaffold. Not yet verified end-to-end against a live org.

## Business archetype

This customer provides field merchandising service to retail brands — restocking shelves, setting up promotional displays, capturing planogram-compliance photos, taking competitor pricing surveys — at grocery, drug, mass-merchant, and convenience-store locations. Technicians (often called "merchandisers" or "field reps") visit multiple stores per day with a list of pre-defined tasks per store. Planogram compliance, recent promotional activity, and store-specific access notes are the most useful grounding data.

## Recommended custom objects

### `Store_Visit_Plan__c`

Why: Each store visit has a structured task list: shelf reset, promo build, photo capture, etc. The plan determines whether the visit is 30 minutes or 3 hours.

| Field | Type | Notes |
|---|---|---|
| `Account__c` | Lookup → Account | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Visit_Type__c` | Picklist (restricted) | Routine Maintenance, New Item Cut-In, Promo Build, Compliance Audit |
| `Estimated_Minutes__c` | Number(4,0) | Time budget for the visit |
| `Tasks__c` | LongTextArea (1000) | Bullet list of tasks to complete |
| `Photos_Required__c` | Number(2,0) | How many photos the rep must capture |
| `Submission_Deadline__c` | DateTime | When the visit report must be uploaded |

Name field: AutoNumber `SVP-{0000}`.

### `Planogram_Compliance__c`

Why: A photo from the last visit showing what compliance looked like is the single most useful piece of grounding data — it tells the rep what the shelf should look like and what to fix.

| Field | Type | Notes |
|---|---|---|
| `Account__c` | Lookup → Account | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Visit_Date__c` | Date | When this compliance check was performed |
| `Compliance_Score__c` | Percent(5,2) | 0-100% compliance with the planogram |
| `Issues_Found__c` | LongTextArea (1000) | Free-text list of issues |
| `Photo_Url__c` | URL(255) | Link to the most recent shelf photo |
| `Resolved_By_Visit__c` | Lookup → WorkOrder | Which visit fixed the issues |

Name field: AutoNumber `PG-{0000}`. Enable history tracking.

## WorkOrder field additions

| Field | Type | Notes |
|---|---|---|
| `Store_Visit_Plan__c` | Lookup → Store_Visit_Plan__c | The plan driving this visit |
| `Store_Access_Window__c` | Text(100) | "6 AM - 10 AM only", "Backroom only after 8 PM", etc. |

## Standard objects + fields to query

| Object | Fields |
|---|---|
| Account | Name, Industry, Phone, BillingAddress, Description |
| Contact | Name, Title, Phone, Email |
| ServiceAppointment | AppointmentNumber, SchedStartTime, SchedEndTime, Address, Description, Status, Subject |

Note: this vertical typically does not use `Asset` (no specific equipment is being serviced). The "asset" is the shelf or display itself, which doesn't usually live as an Asset record.

## Flow structure

Connector chain: `start → GetAccount → GetVisitPlan → GetMostRecentCompliance → GetServiceAppointment → GetContact → BuildPrompt`.

`GetMostRecentCompliance` sorts by `Visit_Date__c DESC LIMIT 1`.

## Prompt template section structure

1. **Mission and time budget** — visit type, estimated time, store name + location. End with submission deadline.
2. **Task list** — the tasks from the visit plan, formatted as a numbered list. Photos required count.
3. **Last visit context** — most recent compliance score, key issues found, link to the prior photo if available.
4. **Store access** — access window (6 AM-10 AM, etc.), store contact name + phone, any backroom or stockroom notes.

## Rules

- Address the rep directly throughout. (Note: "rep" or "merchandiser" not "technician" for this vertical.)
- Lead with the time budget so the rep knows whether they're tight or have slack.
- If the last visit's compliance score was below 70%, lead the task list with the issues that need fixing first.
- For any field not grounded, write `[not provided]`.

## Cadence example

> "Perform a routine maintenance visit at Stop & Shop store #4218 in Quincy, MA. Estimated time: 45 minutes. Submission deadline is end of day today.
>
> Today's tasks: (1) restock the snack endcap to planogram, (2) verify the new chip flavor is on the secondary display in aisle 7, (3) capture 3 photos of the snack endcap and the chip secondary, (4) submit before 6 PM.
>
> Last visit was 14 days ago. Compliance score was 82%. Issues at that time: the salty-snack endcap was out of stock on two SKUs, and the secondary display had old promotional signage. The store manager committed to backroom restock; verify those two SKUs are now on the shelf.
>
> Store access: front entrance only between 6 AM and 10 AM. Your store contact is Dana Liu, store manager, reachable at the phone and email on file."

## Test data sample

Account: "Stop & Shop #4218 — Quincy MA" (Retail).

Store_Visit_Plan: routine maintenance, 45 minutes, 4 tasks, 3 photos required, end-of-day deadline.

Planogram_Compliance: most recent 14 days ago, score 82%, two SKU OOS issues.

Contact: Dana Liu, store manager.

Work Order: "Snack endcap restock + secondary display photo — Stop & Shop #4218", routine priority.
