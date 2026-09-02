# Output Templates — service-itsm-teams-coordinate

This orchestrator runs the Teams ITSM setup as one continuous autopilot (Stages 1–8), stopping only
at the three halts and the Stage 7 branch. Emit a **stage-progress** block as you move between
stages, and a **completion summary** at the end. Do **not** emit a feature-selection menu — the flow
is linear, not menu-driven.

## Stage-progress block (emit as you move between stages)

Report what just finished and what you're doing next, then keep going (no permission gate). Use the
child skill's ACTUAL verdict — a stage holding at a halt is `Waiting`, never `Done`.

```text
Microsoft Teams for ITSM Setup (via service-itsm-teams-coordinate)

┌───┬────────────────────────────────────────────┬──────────────────────┐
│ # │ Stage                                      │ Status               │
├───┼────────────────────────────────────────────┼──────────────────────┤
│ 1 │ Enable Teams for Employee Service feature  │ Done                 │
│ 2 │ Microsoft Entra app + Named Credentials    │ Waiting (Azure creds)│
│ 3 │ IT Desk (pref, access, Swarming, install)  │ Not started          │
│ 4 │ IT Service (pref, access, site, install)   │ Not started          │
│ 5 │ Verify login (fulfiller + UEL)             │ Not started          │
│ 6 │ IT Desk "Ask Agentforce" (automatic)       │ Not started          │
│ 7 │ Offer IT Service Agentforce agent          │ Not started          │
│ 8 │ Build IT Service embedded agent (optional) │ Not started          │
└───┴────────────────────────────────────────────┴──────────────────────┘

Next: send me the Azure app's Client ID and Tenant ID here. For the Client Secret, DON'T paste it in
chat — instead copy-paste this one command into the prompt (put your secret's Value between the
single quotes), then tell me it's done:
  ! umask 077; printf '%s' 'PASTE-CLIENT-SECRET-HERE' > <secret-file> && echo written
I'll read it from that file and write everything into the Named Credential and Auth Provider
automatically.
```

Status values: `Not started`, `In progress`, `Waiting (<what for>)`, `Blocked`, `Done`.

## Halt messages

- **HALT 1 (Stage 2 — Azure/Entra app):** deliver the child's app-registration instructions
  (including the Microsoft Graph permissions) and end with: *"Send me the **Client ID**
  and **Tenant ID** here. For the **Client Secret**, please don't paste it in chat — copy-paste this
  one command into the prompt with your secret's Value between the single quotes, then tell me it's
  done: `! umask 077; printf '%s' 'PASTE-CLIENT-SECRET-HERE' > <secret-file> && echo written`. I'll
  read it from that file and populate the Named Credential and Auth Provider automatically — no
  manual Setup entry needed."* (Substitute the real job/temp path for `<secret-file>`.) Then wait.
- **HALT 2 / HALT 3 (Stages 3 & 4 — app install):** deliver the Microsoft Marketplace link + help
  doc, then: *"Install the app in your Microsoft Teams admin center, then reply **installed** and
  I'll continue. Note: the Azure/Microsoft email the user signs in with must match that Salesforce
  user's email/Username, or login fails silently."* Then wait for `installed`.

## Completion summary

Fires at Stage 7 "no", after Stage 8 completes, or when the user stops. Substitute each stage's real
tracked status — never hard-code `Done`.

- Header: every stage `Done` → `Microsoft Teams for ITSM Setup — Complete`; any stage
  `Blocked`/`Waiting` → `Microsoft Teams for ITSM Setup — Incomplete (action required)`; otherwise →
  `Microsoft Teams for ITSM Setup — Finished`.
- Closing line: all `Done` → `Your Microsoft Teams for ITSM setup is complete.`; any
  `Blocked`/`Waiting` → `Setup is not complete — finish the outstanding step noted above (e.g. paste
  the Azure credentials, or install the Teams app) and I'll resume.`; otherwise → `You've finished
  the stages you chose. The IT Service embedded agent can be built later by re-invoking this
  orchestrator.`
- Never emit `Complete` while any stage is `Blocked`/`Waiting`.

Example — user declined the IT Service agent at Stage 7:

```text
Microsoft Teams for ITSM Setup — Finished
(via service-itsm-teams-coordinate)

┌────────────────────────────────────────────┬─────────────┐
│ Stage                                      │ Status      │
├────────────────────────────────────────────┼─────────────┤
│ Enable Teams for Employee Service feature  │ Done        │
│ Microsoft Entra app + Named Credentials    │ Done        │
│ IT Desk (pref, access, Swarming, install)  │ Done        │
│ IT Service (pref, access, site, install)   │ Done        │
│ Verify login (fulfiller + UEL)             │ Done        │
│ IT Desk "Ask Agentforce" (automatic)       │ Done        │
│ IT Service Agentforce agent                │ Declined    │
└────────────────────────────────────────────┴─────────────┘

You've finished the stages you chose. The IT Service embedded agent can be built later by
re-invoking this orchestrator.
```
