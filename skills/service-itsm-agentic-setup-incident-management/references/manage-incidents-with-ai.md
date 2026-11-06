# Feature: Manage Incidents with AI (delegated to the `service-itsm-manage-incidents-with-ai-configure` SOR)

How the orchestrator runs the **Manage Incidents with AI** feature: the three switches in the *Manage
Incidents with AI* section of Salesforce Go's IT Service Incident Management page — *Automatically Triage
Incidents*, *Let Einstein Assign Incidents* and *Report Incidents from Chat or Voice Using AI*. The SOR's own
steps and guidance decide *how*; the orchestrator runs them itself under its **SOR hand-off protocol** and
owns every user-facing gate. This file adds what is specific to this feature.

1. `discover` the SOR by intent (e.g. "manage incidents with AI") and `describe` the id `discover` returns.
   Its own prerequisite checks fall under protocol step 2.
2. If the request already says what to change, follow the SOR's rule: setting up the whole section turns
   on all three switches, and a request about one switch changes only that one and leaves the other two as
   they are. Otherwise read all three, show them with the block below, and ask which to change and in which
   direction (`AskUserQuestion`) — never infer the direction from the current state. Read each switch before
   changing it, and skip any already in the requested state.
3. Confirm the exact change, write each chosen switch and read each back; mark the feature `Done` only
   when every read-back matches.
4. If the SOR's read or change of triage or Einstein assignment is refused, read and change that switch
   through the `IncidentMgmt` SOR's preference steps instead (`getOrgPref_1`, `updateOrgPref_2`,
   `verify-update-org-pref`) — the same org preferences, and some orgs refuse the SOR's path even when the
   switch is licensed and on; this is the one exception to stopping on a refused call. Only if that path
   fails too does the org lack that switch's license (*IT Services: Agentforce Features for Employees* for
   triage, *IT Services: Einstein Features* for Einstein assignment): say so, skip it, and carry on with the
   others.
5. When turning on the chat and voice switch, ask whether the org already captures transcripts (an active
   messaging channel for chat, call transcription for voice); set one up only if the user asks, through the
   SOR's channel hand-offs. Offer the SOR's smoke test only after that switch reads on — it drafts from one
   conversation the user names and creates nothing.
6. Triage and Einstein assignment are the same org preferences as the *Automatically Triage Incidents* and
   *Assign Incidents with Einstein* toggles of **Incident Preferences**, so a switch set in either feature
   reads as already set in the other.

```text
  Automatically Triage Incidents ................. On | Off
  Let Einstein Assign Incidents .................. On | Off
  Report Incidents from Chat or Voice Using AI ... On | Off

Changed: <label> Off → On (SUCCEEDED | ALREADY-ON | FAILED)
```

## Rules

- ALWAYS change only the switches the user chose, confirm before the write, and verify by read-back before
  marking it `Done` (or verify the already-set state by live read with no write)

## Before marking it `Done`

- [ ] Only the chosen switches changed; any write was confirmed before it ran and verified by read-back,
      and a no-write `Done` came from a live read
