# Output Templates — service-itsm-agentic-setup-incident-management

Emit one of these text blocks at the corresponding step in the workflow. Show every feature the master
switch enables; render each row's `Status` from the actual tracked state (`Not done`, `In progress`,
`Done`) — never hard-code it.

## Feature menu (Behavior step 3)

```text
Incident Management Setup (via service-itsm-agentic-setup-incident-management)

Here are the features available for Incident Management. Select one or more to configure:

┌───┬───────────────────────────────┬──────────────────────────────────────────────────┬──────────┐
│ # │ Feature                       │ Description                                      │ Status   │
├───┼───────────────────────────────┼──────────────────────────────────────────────────┼──────────┤
│ 1 │ SLA & Milestones              │ Create a MilestoneType, SLA Policy, and          │ Not done │
│   │                               │ Entitlement so Incidents inherit SLA milestones  │          │
│ 2 │ Priority Matrix               │ Enable and shape the Impact × Urgency grid that  │ Not done │
│   │                               │ derives Priority on Incident records             │          │
│ 3 │ Incident Preferences          │ The six per-feature setup toggles (validations,  │ Not done │
│   │                               │ auto-close, triage, Einstein assign, rich text)  │          │
│ 4 │ Major Incident Management     │ Approval group + the two MIM preferences         │ Not done │
│   │                               │ (auto-create problem, auto-close child)          │          │
│ 5 │ Incident Persona PSG          │ Assign the Incident Fulfiller / Incident Manager │ Not done │
│   │                               │ persona to a user (bundle + backing licenses)    │          │
│ 6 │ Service Management Privilege  │ Escalation level, privilege records + employee   │ Not done │
│   │                               │ assignments, behind Enable Privilege Assignment  │          │
│ 7 │ Audit Tracking                │ Turn on field history tracking for the Incident  │ Not done │
│   │                               │ fields you choose (who changed what, and when)   │          │
└───┴───────────────────────────────┴──────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the features you want to set up (one or more, e.g. `1,3`).
```

## Post-feature progress (Behavior step 5)

Example after the Incident Preferences feature completes (others still `Not done`):

```text
Incident Preferences — configured successfully
(via service-itsm-agentic-setup-incident-management)

┌───┬───────────────────────────────┬──────────┐
│ # │ Feature                       │ Status   │
├───┼───────────────────────────────┼──────────┤
│ 1 │ SLA & Milestones              │ Not done │
│ 2 │ Priority Matrix               │ Not done │
│ 3 │ Incident Preferences          │ Done     │
│ 4 │ Major Incident Management     │ Not done │
│ 5 │ Incident Persona PSG          │ Not done │
│ 6 │ Service Management Privilege  │ Not done │
│ 7 │ Audit Tracking                │ Not done │
└───┴───────────────────────────────┴──────────┘

Say a number to configure the next feature, or `done` to finish.
```

## Completion summary (Behavior step 6)

The completion summary fires either (a) after every feature completes, or (b) when the user says they are
finished — even if some features are still `Not done`. When rendering:

- Substitute each feature's row with its actual tracked status: `Done`, `In progress`, or `Not done`.
- Choose the header line based on whether every feature is `Done`:
  - All features `Done` → `Incident Management Setup — Complete`
  - Any feature still `Not done` or `In progress` → `Incident Management Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your Incident Management features are configured.`
  - Otherwise → `You have finished the features you selected. The remaining features can be resumed later by re-invoking this orchestrator.`

Example — user finished with three features configured, four left:

```text
Incident Management Setup — Finished
(via service-itsm-agentic-setup-incident-management)

┌───────────────────────────────┬──────────┐
│ Feature                       │ Status   │
├───────────────────────────────┼──────────┤
│ SLA & Milestones              │ Done     │
│ Priority Matrix               │ Not done │
│ Incident Preferences          │ Done     │
│ Major Incident Management     │ Done     │
│ Incident Persona PSG          │ Not done │
│ Service Management Privilege  │ Not done │
│ Audit Tracking                │ Not done │
└───────────────────────────────┴──────────┘

You have finished the features you selected. The remaining features can be resumed later by re-invoking this orchestrator.
```
