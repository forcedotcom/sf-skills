# Output Templates — service-itsm-agentic-setup-agentforce-coordinate

Emit one of these text blocks at the corresponding step in the workflow. Only features with a
working child skill appear — hide placeholder rows.

## Feature menu (Behavior step 2)

```text
Agentforce for ITSM Setup (via service-itsm-agentic-setup-agentforce-coordinate)

Here are the features available for Agentforce ITSM. Select one or more to configure:

┌───┬───────────────────────────────┬──────────────────────────────────────────────────┬──────────┐
│ # │ Feature                       │ Description                                      │ Status   │
├───┼───────────────────────────────┼──────────────────────────────────────────────────┼──────────┤
│ 1 │ Agentforce Studio enablement  │ Turn on org-level Agentforce, Einstein GenAI,    │ Not done │
│   │                               │ and IT Service agent features                    │          │
│ 2 │ Fulfiller Agent lifecycle     │ Create the IT Service Fulfiller agent from       │ Not done │
│   │                               │ template, commit, and activate a version         │          │
│ 3 │ Employee Agent lifecycle      │ Create the IT Service Employee agent from        │ Not done │
│   │                               │ template, commit, and activate a version         │          │
└───┴───────────────────────────────┴──────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the features you want to set up (one or more, e.g. `1` or `1, 2`).
```

## Post-feature progress (Behavior step 4)

Example after Agentforce Studio enablement completes:

```text
Agentforce Studio — enabled successfully
(via service-itsm-agentic-setup-agentforce-studio-configure)

┌───┬───────────────────────────────┬──────────┐
│ # │ Feature                       │ Status   │
├───┼───────────────────────────────┼──────────┤
│ 1 │ Agentforce Studio enablement  │ Done     │
│ 2 │ Fulfiller Agent lifecycle     │ Not done │
│ 3 │ Employee Agent lifecycle      │ Not done │
└───┴───────────────────────────────┴──────────┘

Agentforce Studio is enabled. Next up: create and activate the IT Service
Fulfiller and Employee agents — the Fulfiller agent gives IT technicians an
assistant for triage, case summaries, and record automations, while the
Employee agent gives requesters self-service help with their own requests.
```

## Completion summary (Behavior step 5)

The completion summary fires either (a) after every feature completes, or (b) when the user says
they are finished — even if some features are still `Not done`. When rendering:

- Substitute each feature's row with its actual tracked status: `Done`, `In progress`, or `Not done`.
  Do NOT hard-code `Done`.
- Choose the header line based on whether every feature is `Done`:
  - All features `Done` → `Agentforce for ITSM Setup — Complete`
  - Any feature still `Not done` or `In progress` → `Agentforce for ITSM Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your Agentforce for ITSM setup is complete.`
  - Otherwise → `You have finished the features you selected. The remaining features can be resumed later by re-invoking this orchestrator.`

Example — user finished after only enabling Agentforce Studio (Fulfiller and Employee Agent lifecycles stayed `Not done`):

```text
Agentforce for ITSM Setup — Finished
(via service-itsm-agentic-setup-agentforce-coordinate)

┌───────────────────────────────┬──────────┐
│ Feature                       │ Status   │
├───────────────────────────────┼──────────┤
│ Agentforce Studio enablement  │ Done     │
│ Fulfiller Agent lifecycle     │ Not done │
│ Employee Agent lifecycle      │ Not done │
└───────────────────────────────┴──────────┘

You have finished the features you selected. The remaining features can be
resumed later by re-invoking this orchestrator.
```
