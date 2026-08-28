# Output Templates — service-itsm-agentic-setup-configure

Emit one of these text blocks at the corresponding step in the workflow. Only tracks with a
working sub-orchestrator appear.

## Track menu (Behavior step 2)

```text
ITSM Setup (via service-itsm-agentic-setup-configure)

┌───┬──────────────────────────┬──────────────────────────────────────────────────────┬──────────┐
│ # │ Track                    │ What it covers                                       │ Status   │
├───┼──────────────────────────┼──────────────────────────────────────────────────────┼──────────┤
│ 1 │ Incident Management      │ Configure Incident Management features — currently   │ Not done │
│   │                          │ SLA & Milestones and Priority Matrix                 │          │
│ 2 │ Agentforce for ITSM      │ Enable Agentforce Studio (org-level Agentforce and   │ Not done │
│   │                          │ Einstein GenAI) and create/activate the IT Service   │          │
│   │                          │ Fulfiller and Employee agents                        │          │
│ 3 │ CMDB                     │ Enable the Configuration Management Database         │ Not done │
│   │                          │ feature, deploy the CMDB Foundation content bundle,  │          │
│   │                          │ and grant users CMDB access                          │          │
│ 4 │ Channels                 │ Set up Employee Service channels — Portal,           │ Not done │
│   │                          │ Notifications, Microsoft Teams (IT Desk / IT         │          │
│   │                          │ Service), and Slack                                  │          │
│ A │ Full guided setup        │ Run every available track in dependency order —      │ —        │
│   │                          │ per-track confirmation between them so you can stop  │          │
│   │                          │ any time. Mutually exclusive with per-track picks.   │          │
└───┴──────────────────────────┴──────────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the tracks you want to set up (one or more, e.g. `1` or `1, 3`), or `A` for the full guided setup.
```

## Completion summary (Behavior step 6)

The completion summary fires either (a) after every track completes, or (b) when the user says
they are finished — even if some tracks are still `Not done`. When rendering:

- Substitute each track's row with its actual tracked status: `Done`, `In progress`, or `Not done`.
  Do NOT hard-code `Done`.
- Choose the header line based on whether every track is `Done`:
  - All tracks `Done` → `ITSM Setup — Complete`
  - Any track still `Not done` or `In progress` → `ITSM Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your ITSM setup is complete.`
  - Otherwise → `You have finished the tracks you selected. The remaining tracks can be resumed later by re-invoking this orchestrator.`

Example — user finished after only Incident Management and Agentforce (the two tracks they chose to set up in this session; CMDB and Channels stayed `Not done`):

```text
ITSM Setup — Finished
(via service-itsm-agentic-setup-configure)

┌──────────────────────────┬──────────┐
│ Track                    │ Status   │
├──────────────────────────┼──────────┤
│ Incident Management      │ Done     │
│ Agentforce for ITSM      │ Done     │
│ CMDB                     │ Not done │
│ Channels                 │ Not done │
└──────────────────────────┴──────────┘

You have finished the tracks you selected. The remaining tracks can be resumed
later by re-invoking this orchestrator.
```
