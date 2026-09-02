# Output Templates — service-itsm-agentic-setup-configure

Emit one of these text blocks at the corresponding step in the workflow. Only tracks with a
working sub-orchestrator appear.

## Track menu (Behavior step 2)

Emit the ASCII table first (visual map — every track and `Full guided setup` visible up
front), then dispatch a **single-stage paged multi-select** `AskUserQuestion`. `Full guided
setup` is a first-class pickable option in the same multi-select — NOT a separate mode
selector. `AskUserQuestion` accepts at most **4 options per call**, so when the total
(tracks + `Full guided setup`) > 4 the menu is paged.

### ASCII table (part of the response body)

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
│ 5 │ Unified Catalog          │ Find and deploy Unified Catalog Service Process      │ Not done │
│   │                          │ templates (search / rank, then install / activate)   │          │
│ A │ Full guided setup        │ Run every available track in dependency order with a │ —        │
│   │                          │ per-track confirmation between them. Pickable in the │          │
│   │                          │ same multi-select as the individual tracks. Wins if  │          │
│   │                          │ picked alongside individual tracks.                  │          │
└───┴──────────────────────────┴──────────────────────────────────────────────────────┴──────────┘
```

### Paged multi-select `AskUserQuestion`

**Paging rule.** `AskUserQuestion` caps `options` at 4 per call.

- **Page 1** always leads with `Full guided setup` in slot 1 so it's visible immediately
  without paging. If total options > 4, page 1 = `Full guided setup` + up to 2 tracks +
  `Show more tracks →` (4 slots).
- **Middle pages** (only reached if more content follows after middle) = up to 3 tracks +
  `Show more tracks →` (4 slots).
- **Last page** = the remaining ≤ 4 tracks with NO `Show more tracks →` sentinel — submitting
  the last page ends the selection loop naturally.
- **Small case** (total options ≤ 4): a single page holds `Full guided setup` + all tracks
  with no sentinel.

**Selection accumulation.** A track picked on page 1 stays picked when the user pages
forward — the skill maintains an accumulator across page dispatches. `Show more tracks →` is
stripped from the final selection before delegating.

**Selection resolution.** If the accumulated set contains `Full guided setup`, run every
available track in dependency order (per-track confirmation still runs so the user can stop
between any two tracks). Otherwise, run only the picked tracks in dependency order (or track
number order if unspecified). `Full guided setup` alongside individual tracks means "run
everything" — per-track picks are ignored.

### Scaling — how the page count grows with more tracks

The algorithm is scale-free: page 1 always fits `Full guided setup` + 2 tracks + `Show more
tracks →`, each middle page fits 3 tracks + `Show more tracks →`, and the last page fits
the remaining ≤ 4 tracks with no sentinel. So the page count grows by one page for every
~3 new tracks. Same shape at every scale — the skill does not need to change as new
sub-orchestrators land.

| Available tracks | Total options (incl. `Full guided setup`) | Pages | Shape |
|---|---|---|---|
| 3  | 4  | 1 (no paging) | `Full guided setup` + T1 + T2 + T3 |
| 4  | 5  | 2 | P1: `FGS` + T1 + T2 + `Show more →` · P2: T3 + T4 |
| 5  | 6  | 2 | P1: `FGS` + T1 + T2 + `Show more →` · P2: T3 + T4 + T5 |
| 7  | 8  | 3 | P1: `FGS` + T1 + T2 + `Show more →` · P2: T3 + T4 + T5 + `Show more →` · P3: T6 + T7 |
| 10 | 11 | 4 | P1: `FGS` + T1 + T2 + `Show more →` · P2: T3 + T4 + T5 + `Show more →` · P3: T6 + T7 + T8 + `Show more →` · P4: T9 + T10 |

### Today's 5 tracks (6 total with `Full guided setup`) — 2 pages

Page 1 (4 options):

- `Full guided setup`
- `Incident Management`
- `Agentforce for ITSM`
- `Show more tracks →`

Page 2 (fires only after `Show more tracks →` was picked on page 1; 3 options, no sentinel):

- `CMDB`
- `Channels`
- `Unified Catalog`

Never try to render >4 options in one `AskUserQuestion` — the tool schema hard-caps `options`
at 4 and the dispatch fails with an "invalid parameter" error before the user sees the menu.

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
│ Unified Catalog          │ Not done │
└──────────────────────────┴──────────┘

You have finished the tracks you selected. The remaining tracks can be resumed
later by re-invoking this orchestrator.
```
