# Output Templates — service-itsm-agentic-setup-cmdb-coordinate

Emit one of these text blocks at the corresponding step in the workflow. Only features with a
working child skill appear — hide placeholder rows.

## Feature menu (Behavior step 2)

```text
CMDB Setup (via service-itsm-agentic-setup-cmdb-coordinate)

Here are the features available for CMDB. Select one or more to configure:

┌───┬───────────────────────────────┬──────────────────────────────────────────────────┬──────────┐
│ # │ Feature                       │ Description                                      │ Status   │
├───┼───────────────────────────────┼──────────────────────────────────────────────────┼──────────┤
│ 1 │ CMDB feature enablement       │ Verify org SKU, provision the ITOM tenant, and   │ Not done │
│   │                               │ turn on the service-cloud-cmdb feature           │          │
│ 2 │ CMDB Foundation bundle        │ Install the CMDB Foundation base content bundle  │ Not done │
│   │                               │ (CI types, layouts, sample records)              │          │
│ 3 │ User CMDB access              │ Assign CMDB permission sets and permission-set   │ Not done │
│   │                               │ licenses to a specific user                      │          │
└───┴───────────────────────────────┴──────────────────────────────────────────────────┴──────────┘

Reply with the numbers of the features you want to set up (one or more, e.g. `1` or `1, 2, 3`).
```

## Post-feature progress (Behavior step 4)

Example after CMDB feature enablement completes:

```text
CMDB feature — enabled successfully
(via service-itsm-agentic-setup-cmdb-configure)

┌───┬───────────────────────────────┬──────────┐
│ # │ Feature                       │ Status   │
├───┼───────────────────────────────┼──────────┤
│ 1 │ CMDB feature enablement       │ Done     │
│ 2 │ CMDB Foundation bundle        │ Not done │
│ 3 │ User CMDB access              │ Not done │
└───┴───────────────────────────────┴──────────┘

CMDB is enabled. Next up: install the CMDB Foundation base content bundle so
the org has CI types, page layouts, and sample records to work with.
```

## Completion summary (Behavior step 5)

The completion summary fires either (a) after every feature completes, or (b) when the user says
they are finished — even if some features are still `Not done`. When rendering:

- Substitute each feature's row with its actual tracked status: `Done`, `In progress`, or `Not done`.
  Do NOT hard-code `Done`.
- Choose the header line based on whether every feature is `Done`:
  - All features `Done` → `CMDB Setup — Complete`
  - Any feature still `Not done` or `In progress` → `CMDB Setup — Finished`
- Choose the closing line based on state:
  - All `Done` → `Your CMDB setup is complete.`
  - Otherwise → `You have finished the features you selected. The remaining features can be resumed later by re-invoking this orchestrator.`

Example — user finished after enabling the feature and installing the bundle (User CMDB access stayed `Not done`):

```text
CMDB Setup — Finished
(via service-itsm-agentic-setup-cmdb-coordinate)

┌───────────────────────────────┬──────────┐
│ Feature                       │ Status   │
├───────────────────────────────┼──────────┤
│ CMDB feature enablement       │ Done     │
│ CMDB Foundation bundle        │ Done     │
│ User CMDB access              │ Not done │
└───────────────────────────────┴──────────┘

You have finished the features you selected. The remaining features can be
resumed later by re-invoking this orchestrator.
```
