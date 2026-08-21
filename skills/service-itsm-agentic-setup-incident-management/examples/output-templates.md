# Output Templates — service-itsm-agentic-setup-incident-management

Emit one of these text blocks at the corresponding step in the workflow. Only features with a
working child skill appear — hide placeholder rows.

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
└───┴───────────────────────────────┴──────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the features you want to set up (one or more, e.g. `1,2`).
```

## Post-feature progress (Behavior step 5)

Example after the SLA & Milestones child skill completes (Priority Matrix still `Not done`):

```text
SLA & Milestones — configured successfully
(via service-itsm-agentic-setup-incident-sla-configure)

┌───┬───────────────────────────────┬──────────┐
│ # │ Feature                       │ Status   │
├───┼───────────────────────────────┼──────────┤
│ 1 │ SLA & Milestones              │ Done     │
│ 2 │ Priority Matrix               │ Not done │
└───┴───────────────────────────────┴──────────┘

The next logical step is Priority Matrix — say `2` to configure it now, or `done` to finish.
```

## Completion summary (Behavior step 6)

The completion summary fires either (a) after every feature completes, or (b) when the user says
they are finished — even if some features are still `Not done`. When rendering:

- Substitute each feature's row with its actual tracked status: `Done`, `In progress`, or `Not done`.
  Do NOT hard-code `Done`.
- Choose the header line based on whether every feature is `Done`:
  - All features `Done` → `Incident Management Setup — Complete`
  - Any feature still `Not done` or `In progress` → `Incident Management Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your Incident Management features are configured.`
  - Otherwise → `You have finished the features you selected. The remaining features can be resumed later by re-invoking this orchestrator.`

Example — user finished the setup with both features configured:

```text
Incident Management Setup — Complete
(via service-itsm-agentic-setup-incident-management)

┌───────────────────────────────┬──────────┐
│ Feature                       │ Status   │
├───────────────────────────────┼──────────┤
│ SLA & Milestones              │ Done     │
│ Priority Matrix               │ Done     │
└───────────────────────────────┴──────────┘

Your Incident Management features are configured.
```
