# Healthcare Medical Devices Seed Template

Scaffold. Not yet verified end-to-end against a live org. High-stakes vertical — patient safety and FDA compliance shape every visit.

## Business archetype

This customer manufactures or services medical devices — infusion pumps, imaging equipment, dialysis machines, ventilators, surgical robots — at hospitals, clinics, and ambulatory surgery centers. Technicians perform calibration, software updates, recall remediation, and break/fix. Patient safety protocols (lockout-tagout during service, escorted access in surgical areas), FDA recall status, and last-calibration dates are critical grounding data. Many sites require the technician to coordinate with biomed engineering.

## Recommended custom objects

### `Device_Calibration__c`

Why: Medical devices require periodic calibration with documented results. Walking into a service call without knowing the last-calibration date risks patient safety and regulatory exposure.

| Field | Type | Notes |
|---|---|---|
| `Asset__c` | Lookup → Asset | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Calibration_Type__c` | Picklist (restricted) | Routine, Annual, Post-Repair, Pre-Use Check |
| `Last_Calibration_Date__c` | Date | When the last calibration was performed |
| `Next_Calibration_Due__c` | Date | When the next calibration is due |
| `Result__c` | Picklist (restricted) | Pass, Pass with notes, Fail, Out of tolerance |
| `Calibrated_By__c` | Lookup → User | Who performed the calibration |
| `Notes__c` | LongTextArea (500) | Calibration findings, drift, adjustments made |

Name field: AutoNumber `CAL-{0000}`. Enable history tracking.

### `FDA_Compliance_Log__c`

Why: FDA recalls, field safety notices, and corrective-action communications are mandatory grounding for any service visit on a regulated device.

| Field | Type | Notes |
|---|---|---|
| `Asset__c` | Lookup → Asset | `<deleteConstraint>SetNull</deleteConstraint>` |
| `Notice_Type__c` | Picklist (restricted) | Recall (Class I/II/III), Field Safety Notice, Corrective Action, Voluntary Update |
| `Notice_Date__c` | Date | When the notice was issued |
| `Action_Required__c` | LongTextArea (1000) | What the technician must do |
| `Status__c` | Picklist (restricted) | Pending, In Progress, Completed, N/A |
| `FDA_Reference__c` | Text(50) | FDA recall number or notice ID |

Name field: AutoNumber `FDA-{0000}`. Enable history tracking.

## WorkOrder field additions

| Field | Type | Notes |
|---|---|---|
| `Patient_Safety_Risk__c` | Picklist (restricted) | None, Low, Medium, High |
| `Biomed_Coordination_Required__c` | Checkbox | If true, the brief must instruct the technician to coordinate with hospital biomed before starting |
| `Lockout_Tagout_Required__c` | Checkbox | If true, the technician must confirm LOTO procedures before starting |

## Standard objects + fields to query

| Object | Fields |
|---|---|
| Account | Name, Industry, Phone, Description |
| Asset | Name, SerialNumber, InstallDate, Description, Status |
| Contact | Name, Title, Phone, Email |
| ServiceAppointment | AppointmentNumber, SchedStartTime, SchedEndTime, ArrivalWindowStartTime, ArrivalWindowEndTime, Description, Status, Subject |

## Flow structure

Connector chain: `start → GetAccount → GetAsset → GetMostRecentCalibration → GetActiveFDANotices → GetServiceAppointment → GetContact → BuildPrompt`.

`GetMostRecentCalibration` sorts by `Last_Calibration_Date__c DESC LIMIT 1`.

`GetActiveFDANotices` filters by `Asset__c = $Input.WorkOrder.AssetId AND Status__c IN ('Pending', 'In Progress')`. For a real deployment with multiple active notices, use a Loop pattern.

## Prompt template section structure

1. **Mission and contact** — work to perform, biomed contact + phone + email. End with patient-safety reminder.
2. **Patient safety protocol** — risk level, lockout-tagout requirement, biomed coordination requirement. If risk is Medium or High, list the specific safety steps.
3. **Active FDA notices** — any pending or in-progress notices for this asset, with the FDA reference and required action. If none, state "no active FDA notices."
4. **Calibration status** — last calibration date, result, days until next due. Call out overdue calibrations explicitly.
5. **Equipment context** — asset model, serial, install date, current status.

## Rules

- Address the technician directly throughout.
- If `Biomed_Coordination_Required__c = true`, the brief must explicitly instruct: "Confirm with hospital biomed before starting service. Do not power-cycle the device without their sign-off."
- If `Lockout_Tagout_Required__c = true`, the brief must list the LOTO steps from the asset's documented procedure.
- If an FDA recall has `Status__c = Pending`, this visit must include the recall remediation. Lead with that, not the customer's stated complaint.
- If the next calibration is overdue, the brief must state how many days overdue.
- For any field not grounded, write `[not provided]`.

## Cadence example

> "Perform a Class II FDA recall remediation on the customer's infusion pump (Serial INF-CN-220194). Your biomed contact is Dr. Patel, reachable at the provided phone and email. Do not leave the site until the recall remediation is complete and the device is signed off by biomed.
>
> This is a Medium patient-safety-risk visit. Lockout-tagout procedures are required: power off the device at the wall, apply your personal lock, verify the device is de-energized, and complete the LOTO log entry before opening the chassis.
>
> Active FDA notice: Class II Recall, FDA reference Z-2845-2026, issued 2026-04-12. Action required: install firmware version 7.4.1, verify pressure-sensor recalibration completes successfully, document the firmware checksum on the calibration log.
>
> Most recent calibration: 2026-02-10, result Pass with notes ("minor drift on flow sensor 2"). Next calibration is due in 6 days; if you have time after the recall remediation, perform an early calibration and update the log.
>
> The device is a 2023 model, currently in service. The customer's stated complaint (intermittent flow alarm) is likely related to the recall — the firmware update should resolve it."

## Test data sample

Account: "Mercy General Hospital — ICU Wing" (Healthcare).

Asset: "Infusion Pump INF-CN-220194", installed 2023-04-22.

Device_Calibration: most recent 2026-02-10, Pass with notes.

FDA_Compliance_Log: 1 active Class II recall, 1 completed Field Safety Notice from 2025.

Contact: Dr. Patel, biomed engineering lead.

Work Order: "Recall remediation Z-2845-2026 — Infusion Pump INF-CN-220194", High priority, biomed coordination required, LOTO required, Medium patient safety risk.
