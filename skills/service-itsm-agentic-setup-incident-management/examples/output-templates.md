# Output Templates — service-itsm-agentic-setup-incident-management

Emit these blocks at the matching Behavior step. Every status is read from the org with
`references/status-checks.md` just before the block is shown — the statuses below show the shape, not an
org's real state. Each status cell is the label and its short note. Show every feature the master switch
enables.

## Feature menu (Behavior step 3)

The table is the menu: show every row, then the reply line below it. The user's typed reply is the
selection — don't collect it with `AskUserQuestion`.

Example — a resumed setup where the org shows some features already set up and others only partly:

```text
Incident Management Setup (via service-itsm-agentic-setup-incident-management)

Target org: <org>   (all steps below run against this org)
IT Service Enablement and Incident Management are on.

Here are the features available for Incident Management. Select one or more to configure:
```

| #  | Feature | What it does | Status |
| -- | ------- | ------------ | ------ |
| P  | Incident Preferences | The six setup toggles (validations, auto-close, triage, Einstein, group restriction, rich text) | Done — 4 of 6 on; off: Restrict Assigned Group to Regular Groups, Enable Rich Text for Incident Descriptions |
|    | **Set Up the Basics** | | |
| 1  | Incident Persona PSG | Manage User Access: give a user the Incident Fulfiller or Manager persona (bundle + licenses) | Done — Incident Fulfiller: 3 people · Incident Manager: 3 people |
| 2  | Priority Matrix | Configure Rules for Automatic Incident Priority: the Impact × Urgency grid that sets Priority | Not done — not turned on |
| 3  | SLA & Milestones | Define SLAs to Prioritize Incidents: turn on SLA Management, then a predefined or custom policy | Done — SLA Management is on; active Incident policies: Incident SLA Policy |
|    | **Unlock Advanced Functionality** | | |
| 4  | Incident Dashboards | Deploy the Incident Manager and/or Fulfiller dashboards, and dashboards on the Home page | Done — Incident Manager dashboards are on |
| 5  | Email-to-Incident | Report Incidents from Emails: email settings + routing addresses | In progress — turned on, but no routing address is set up yet |
| 6  | Major Incident Management | Review and Manage Major Incident Configuration: approval group + the two MIM preferences (auto-create problem, auto-close child) | In progress — 2 people have the Major Incident Manager license, but no approval group is set |
| 7  | Broadcast Communications | Set Up Broadcast Communication for Major Incidents: turn on, then sender access, channels (Email/In-app/Slack/Teams), objects | Not available — Broadcast Communications isn't available in this org; contact Salesforce Customer Support |
| 8  | Manage Incidents with AI | Auto-triage, Einstein assignment, and AI-drafted incidents from chat or voice transcripts | Done — all three are on |
| 9  | Service Management Privilege | Escalation level, privilege records + employee assignments, behind Enable Privilege Assignment | Done — turned on; 2 privileges; escalation level not set |
| 10 | Audit Tracking | Turn on field history tracking for the Incident fields you choose (who changed what, and when) | Not done — no Incident fields are tracked yet |

```text
Reply with the numbers of the features you want to set up (one or more, e.g. `2,10`; `P` for Incident Preferences).
```

When a gate reads In progress, or only its setup-step read failed, the gate line says so instead:

```text
Incident Management is on, but its Salesforce Go setup didn't finish: Turn on Email to Incident.
```

## Post-feature progress (Behavior step 5)

Example — re-read after the Priority Matrix feature turned automatic priority on and saved the grid:

```text
Priority Matrix — configured successfully
(via service-itsm-agentic-setup-incident-management)
```

| #  | Feature | Status |
| -- | ------- | ------ |
| P  | Incident Preferences | Done — 4 of 6 on; off: Restrict Assigned Group to Regular Groups, Enable Rich Text for Incident Descriptions |
| 1  | Incident Persona PSG | Done — Incident Fulfiller: 3 people · Incident Manager: 3 people |
| 2  | Priority Matrix | Done — turned on, 9 priority rules |
| 3  | SLA & Milestones | Done — SLA Management is on; active Incident policies: Incident SLA Policy |
| 4  | Incident Dashboards | Done — Incident Manager dashboards are on |
| 5  | Email-to-Incident | In progress — turned on, but no routing address is set up yet |
| 6  | Major Incident Management | In progress — 2 people have the Major Incident Manager license, but no approval group is set |
| 7  | Broadcast Communications | Not available — Broadcast Communications isn't available in this org |
| 8  | Manage Incidents with AI | Done — all three are on |
| 9  | Service Management Privilege | Done — turned on; 2 privileges; escalation level not set |
| 10 | Audit Tracking | Not done — no Incident fields are tracked yet |

```text
Next up: Email-to-Incident (5) — it's on, but no routing address is set up yet.
Say a number (or `P`) to configure the next feature, or `done` to finish.
```

When the re-read shows a feature still finishing, say so instead of calling it done — for example, right
after turning on Broadcast Communications in an org that has it:

| #  | Feature | Status |
| -- | ------- | ------ |
| 7  | Broadcast Communications | In progress — Salesforce Go is turning it on now |

```text
Salesforce Go is still turning on Broadcast Communications. Want me to check again?
```

## Completion summary (Behavior step 6)

The completion summary fires either (a) when every row reads Done, or (b) when the user says they are
finished — even if some features aren't done. When rendering:

- Re-read every row first, and show what the org reports. Do NOT hard-code `Done`.
- Header: `Incident Management Setup — Complete` only when every row reads Done (a row that reads Not
  available doesn't count against it); otherwise `Incident Management Setup — Finished`.
- Closing line:
  - Complete → `Your Incident Management features are configured.`
  - Finished → name what's left, then `Run this setup again any time — it re-reads the org and picks up where setup stands.`

Example — the user stopped after the Priority Matrix and a routing address for Email-to-Incident:

```text
Incident Management Setup — Finished
(via service-itsm-agentic-setup-incident-management)

Target org: <org>
```

| #  | Feature | Status |
| -- | ------- | ------ |
| P  | Incident Preferences | Done — 4 of 6 on; off: Restrict Assigned Group to Regular Groups, Enable Rich Text for Incident Descriptions |
| 1  | Incident Persona PSG | Done — Incident Fulfiller: 3 people · Incident Manager: 3 people |
| 2  | Priority Matrix | Done — turned on, 9 priority rules |
| 3  | SLA & Milestones | Done — SLA Management is on; active Incident policies: Incident SLA Policy |
| 4  | Incident Dashboards | Done — Incident Manager dashboards are on |
| 5  | Email-to-Incident | Done — turned on; 1 routing address |
| 6  | Major Incident Management | In progress — 2 people have the Major Incident Manager license, but no approval group is set |
| 7  | Broadcast Communications | Not available — Broadcast Communications isn't available in this org |
| 8  | Manage Incidents with AI | Done — all three are on |
| 9  | Service Management Privilege | Done — turned on; 2 privileges; escalation level not set |
| 10 | Audit Tracking | Not done — no Incident fields are tracked yet |

```text
Left to do: designate the major-incident approval group (6) and choose the Incident fields to track (10).
Broadcast Communications isn't available in this org. Run this setup again any time — it re-reads the
org and picks up where setup stands.
```

## A read that fails (any step)

Show **Couldn't check** with the reason in plain words — never **Not done**:

| #  | Feature | Status |
| -- | ------- | ------ |
| 6  | Major Incident Management | Couldn't check — reading this needs an admin with IT Service setup access |
| 10 | Audit Tracking | Couldn't check — the org didn't respond |

```text
I couldn't check Major Incident Management or Audit Tracking, so I haven't marked them either way.
Want me to try again?
```
