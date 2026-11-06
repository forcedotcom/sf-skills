---
name: service-itsm-agentic-setup-incident-management
description: "Orchestrator for Incident Management setup in Service Cloud ITSM: presents the features with live org status, and configures each — Incident preferences, Incident persona PSG assignment, Priority Matrix, SLA & Milestones, Incident dashboards, Email-to-Incident, Major Incident Management (approval group + MIM preferences), Broadcast Communications, Manage Incidents with AI, Service Management Privilege (privilege escalation), and audit tracking. Use for: set up or configure incident management, a walkthrough, what incident features can I configure; the incident preference toggles (default field validations, auto-close child incidents, auto-triage, assign with Einstein, restrict assigned group, rich text descriptions); assigning the Incident Fulfiller or Incident Manager persona PSG. DO NOT TRIGGER for: the master on/off switch alone (use the IncidentMgmt SOR), the Priority Matrix, SLA, or field history tracking alone, the Major Incident Manager PSG, creating/editing PSGs, or Problem/Change/Case Management."
metadata:
  version: "3.2"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-manage-incidents-with-ai-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck: "(UserPermissions.CustomizeApplication) && (IncidentMgmt.orgHasITSMOrgPermission)"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Incident Management Setup Orchestrator

Guide the user through setting up Incident Management features in Salesforce Service Cloud ITSM by
presenting the available capabilities with their status read from the org, and **delegating** each feature
to the Setup Operation Recipes (SORs) whose own steps this skill runs.

## Goal

Act as the coordinator for Incident Management feature configuration. Present a menu of configurable
features with each one's status read from the org, handle each selection, and after each feature completes,
re-read the statuses and return to the menu until the user is done.

## How each feature is handled

| # | Feature | Handled by | Reference |
|---|---------|-----------|-----------|
| P | Incident Preferences | **Delegate** → `IncidentMgmt` (its preference steps) | `references/incident-preferences.md` |
| 1 | Incident Persona PSG | **Delegate** → `service-itsm-incident-persona-assign` | `references/incident-persona-psg.md` |
| 2 | Priority Matrix | **Delegate** → `ItsmPriorityMatrix` (entity type `Incident`) | `references/priority-matrix.md` |
| 3 | SLA & Milestones | **Delegate** → `SLASettings`, then `sla-management-setup` (custom policy) | `references/sla-milestones.md` |
| 4 | Incident Dashboards | **Delegate** → `itsm-incident-dashboard-enablement` (Manager) and `itsm-incident-fulfiller-dashboard-enablement` (Fulfiller) | `references/incident-dashboards.md` |
| 5 | Email-to-Incident | **Delegate** → `EmailToIncident` | `references/email-to-incident.md` |
| 6 | Major Incident Management | **Delegate** → `MIM` | `references/major-incident-management.md` |
| 7 | Broadcast Communications | **Delegate** → `service-itsm-broadcast-communications-setup` | `references/broadcast-communications.md` |
| 8 | Manage Incidents with AI | **Delegate** → `service-itsm-manage-incidents-with-ai-configure` | `references/manage-incidents-with-ai.md` |
| 9 | Service Management Privilege | **Delegate** → `ServiceMgmtPrivilegeSetup` | `references/service-mgmt-privilege.md` |
| 10 | Audit Tracking | **Delegate** → `FieldHistoryTracking` | `references/audit-tracking.md` |

Every feature runs on SORs; this skill hands no feature off to another skill. A SOR is a recipe, not an
agent: this skill runs the SOR's steps itself under the **SOR hand-off protocol** below and owns every
user-facing gate — the questions, the confirmation before each write, and the read-back. The SOR's own steps
and guidance decide *how*. **Read a feature's reference file before running that feature**: it adds only
what is specific to this skill. Every operation is fetched at runtime through the `headless-360` MCP server:
`discover` by intent, `describe` for the current route/schema/labels, then `dispatch_readonly` (reads) /
`dispatch` (writes).
**Hardcode nothing — `describe` wins.** If a described path repeats the `/services/data/v{version}` prefix,
send the prefix once.

### SOR hand-off protocol (every feature)

1. **Find it.** `discover` the SOR by intent and `describe` the id `discover` returns. Judge availability by
   what the calls return, not by a step's `status` label — a step labelled `proposed` may still be served.
   A `discover` miss or a `401`/`403`/`404` means the surface isn't available to this user or org: surface
   it and stop.
2. **This skill owns both prerequisite gates.** Behavior step 2 already confirmed IT Service Enablement and
   the master switch on. If a SOR's own check reads either as anything but `ENABLED`, go back to step 2 —
   never run a SOR's own enable or delegate step for them, and never follow a hand-off a SOR names for
   either gate or for another feature on this menu.
3. **Read before write.** Read the current state through the SOR's read steps. If it already matches what
   the user wants, that read is the verification — no write.
4. **Confirm the exact change.** State the current value and the exact change, and get an explicit yes
   (`AskUserQuestion`) before any write. The user's initial request is not that confirmation; one yes can
   cover several writes if you listed them all.
5. **Write, then read back.** Write only through the SOR's write steps, then read back through its verify
   steps. The feature is finished only when the read-back shows the chosen state — a write response alone
   is not proof.

## Behavior

### 0. Read every status from the org

Every status you show — both prerequisite gates, the menu, the table after a feature runs, the completion
summary — comes from reading the org with `references/status-checks.md` just before you show it. Never
carry a status over from earlier in the conversation, from a previous session, or from what the user says
is already done: setup may have changed since. A failed read is **Couldn't check**, never **Not done**. If
the org disagrees with what the user said, show the org's status and say so. Only the **target org**
carries over, unless the user switches orgs.

### 1. Extract context from conversation

Scan chat history for the target org, the features the user named, any stated preferences/constraints, and
business context that informs which features are relevant — never for which features are done.

### 2. Verify IT Service Enablement, then ensure the Incident Management master switch is on

Every feature below depends on IT Service Enablement (`service-cloud-itsm-setup`) and uses the recommended
ITSM Incident Management check (`service-cloud-itsm-incident`). Before showing the menu—or before a direct
single-feature handoff—`discover` the `IncidentMgmt` SOR by intent and `describe` its steps, then check the
two gates in this order, using that SOR for every read, enable, and verify
(`read-/enable-/verify-itsm-setup-feature-status`, `read-/enable-/verify-itsm-incident-feature-status`).
Follow its current invocation and prefix each stored path as its version note says: use the org's full API
version with its minor, such as `v68.0`, never a bare major. If a feature read fails, stop and do not retry
other version strings. Never read or toggle `service-cloud-incident-management`, and do
not use the Service-Foundation `IncidentManagement` look-alike or its broadcast toggles.

Read each gate with the Salesforce Go rule in `references/status-checks.md` and act on it as that file's
gates section says: `ENABLED` continues even with blocked reasons or an unfinished Salesforce Go setup step;
`NOT_AVAILABLE` or a blocked reason halts — show the reason as plain text (its message is HTML-escaped
markup) and do not attempt enable. Never infer success from a write response.

1. **IT Service Enablement** — only exact `ENABLED` continues. Exact `NOT_ENABLED` with no blocked reasons:
   ask **“IT Service Enablement is off — enable it now?”** with `AskUserQuestion` (single-select, exactly
   two options: Yes and No) — every time, never as plain text, and do not preview the menu before it is
   answered. Yes → delegate to the `IncidentMgmt` SOR (read → enable → verify), stating the user already
   confirmed this exact change so it does not ask again; continue only when verify reads exact `ENABLED`.
   Delegating means the MCP tools, not a Claude Code skill: `describe` the `IncidentMgmt` SOR, read
   its steps by `id`, and `dispatch` each step exactly as the SOR defines it. Never call `Skill` for
   it and never invent an enable URL.
   No → stop and point to Setup. Missing entry, blocked reasons, error, or any other status → stop and explain
   plainly; no question.
2. **Incident Management** — same pattern, second: exact `NOT_ENABLED` with no blocked reasons →
   `AskUserQuestion` **“Incident Management is off — enable it now?”** (Yes/No); Yes → delegate to the
   `IncidentMgmt` SOR with the same already-confirmed statement and continue only on verify exact
   `ENABLED`; No → stop and point to Setup. `NOT_AVAILABLE`, blocked reasons, error, or anything else → stop
   and explain; no question.

Never offer to bypass either gate.

**Re-read both gates each time the menu is about to show and before a direct single-feature handoff** —
never reuse an earlier result (step 0).

### 3. Present the feature menu

Read every row's status (step 0), then emit the **Feature menu** template from `examples/output-templates.md`.
The table is the menu; the user replies with the numbers they want. Never collect the choice with
`AskUserQuestion`: a question holds four options at most, so it can't carry every row. Every row stays
selectable. Selecting one feature is valid; several enqueue for sequential handling in step 4.

### 4. Handle each selected feature in order

Handle selected features sequentially in dependency order (or the order given). For each, **read its
reference file**, then run its SORs under the hand-off protocol. This skill does the writing, so always
**read live state before writing, confirm before every write, and verify every write by read-back**. Honor
the per-feature invariants below.

### 5. After each feature completes

Re-read every status (step 0), suggest the next logical step — the first row that isn't **Done** or **Not
available** — and re-present the menu using the **Post-feature progress** template in
`examples/output-templates.md`.

### 6. Completion summary

When the user says they're done (or every row reads **Done**), present the **Completion summary** template
in `examples/output-templates.md`, with every status read just before it (step 0).

---

## Critical invariants (load-bearing — the SORs carry the full detail)

The **Everywhere** rules apply to every feature; the rest apply to the named feature. They are irreversible
or silently wrong if missed.

- **Resolve the right node (Preferences).** Target the ITSM Incident Management org-preferences node
  (the one with the six per-feature toggles), **not** the Service-Foundation look-alike whose toggles
  are broadcast channels plus its own master switch.
- **Two preferences are one-way / enable-only (Preferences).** *Restrict Assigned Group to Regular Groups*
  and *Enable Rich Text for Incident Descriptions* cannot be turned off once on. Never offer to disable
  them; require an explicit "I understand this can't be undone" confirmation before enabling; never enable
  to test. *Restrict Assigned Group…* also **freezes once the org has any Incident record** — an enable can
  fail outright; do not retry.
- **PSL before PSG (Persona).** Assign the union of a persona PSG's member permission-set **licenses first,
  then the PSG** (keyed on `PermissionSetGroupId`, never a permission-set Id) — otherwise the persona is
  silently half-provisioned. Query the persona PSGs by `DeveloperName` with **no** `NamespacePrefix` filter.
- **The Priority Matrix save is a full replacement (Priority Matrix).** Any cell left out of the save is
  deleted — always send the complete matrix, using only active Priority values.
- **SLA Versioning is permanent; the predefined seed is not idempotent (SLA & Milestones).** Turn on SLA
  Versioning only after the explicit **Enable** answer, and never offer to turn it off. Detect the
  predefined *Standard Support for Incidents* policy before seeding and never re-seed it. Never deactivate,
  reorder, or broaden another SLA policy; halt on the first failed milestone create; never ask for an
  Account.
- **One-way features (Email-to-Incident, Broadcast Communications).** Turning on Email-to-Incident or the
  Broadcast Communications feature can't be undone — say so before asking, and never offer or attempt to
  turn either off.
- **License, not assignment (Major Incident Management).** MIM is the approval group + two preferences on
  top of **base** Incident Management, and MIM itself must already be active — Salesforce provisions it, so
  never try to turn it on. The Major Incident Manager grant is a **LICENSE**
  (`PermissionSetLicenseAssign`), never a `PermissionSetAssignment`. **License before group membership;
  the approval group is a public Group, never a User, and its users must validate true before you designate
  it; to reassign, validate the new group, then remove, then create.** Only two preference names are
  valid: `AutoCreationOfProblem`, `AutoClosureChildIncidents`.
- **Destructive delete + unverifiable assignments (Service Management Privilege).** Deleting a Service
  Management Privilege is irreversible — confirm explicitly, never delete to test. Bulk employee↔privilege
  assignments have **no read-back** — report them as applied, not verified. Turn on the reversible *Enable
  Privilege Assignment* toggle before any escalation-level or privilege step, as the SOR orders it; if the
  user declines, stop. No public API substitute exists — a `404` / discover-miss means the surface isn't
  served on this org; surface it and stop.
- **Everywhere:** read before write; treat "already in that state" / a duplicate as idempotent success;
  verify by read-back (a write response alone is not proof); each license consumes a seat; on `401`/`403`/
  `404` surface the raw error and stop; keep record Ids, HTTP codes, route paths, and tooling terms
  (`dispatch`, `headless-360`, SOR/step ids) out of user-facing output.

---

## Feature Dependencies & Recommended Order

```text
P.  Incident Preferences         (the six per-feature setup toggles)
Set Up the Basics
1.  Incident Persona PSG         (Fulfiller / Manager persona for a user)
2.  Priority Matrix              (Impact × Urgency → Incident.Priority)
3.  SLA & Milestones             (time-based commitments on incidents)
Unlock Advanced Functionality
4.  Incident Dashboards          (Manager / Fulfiller dashboards + Home pages)
5.  Email-to-Incident            (incoming email → Incidents, routing addresses)
6.  Major Incident Management    (approval group + two MIM preferences)
7.  Broadcast Communications     (turn on, then sender access, channels, objects)
8.  Manage Incidents with AI     (AI triage, Einstein assignment, chat/voice drafts)
9.  Service Management Privilege (escalation level + privilege assignments)
10. Audit Tracking               (field history on chosen Incident fields)
```

Features 1–8 follow Salesforce Go's IT Service Incident Management page; Service Management Privilege and
Audit Tracking aren't on that page.

A priority-tiered SLA needs the Priority Matrix on: with it off, every Incident gets the default priority,
so only that tier's milestones fire.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-incident-management)" in the setup header
- ALWAYS check the IT Service Enablement and master-switch prerequisites (Behavior step 2) through
  the `IncidentMgmt` SOR before showing the menu or handing off a named feature
- ALWAYS ask each off gate with `AskUserQuestion` (single-select Yes/No), every time, never as plain text,
  before delegating the enable; No stops and points to Setup
- ALWAYS require exact `ENABLED` verification for `service-cloud-itsm-setup` before the Incident switch;
  anything else stops. Never read or toggle `service-cloud-incident-management`
- ALWAYS present the feature menu before configuring any selected feature (the master-switch prerequisite
  is the only permitted action before the menu) — do not assume which feature the user wants, **except**
  when the user named a specific feature, in which case go straight to it (single-select is fine)
- ALWAYS show the feature menu as the table and take the choice from the user's typed reply, never from
  an `AskUserQuestion`
- ALWAYS read a feature's reference file before executing it, follow its rules, and follow the SOR at
  runtime — never hardcode a route, body, or preference name
- ALWAYS run a feature's SORs under the hand-off protocol; NEVER hand a feature off to another skill, and
  never follow a SOR's hand-off for either prerequisite gate or for another feature on this menu
- NEVER set up a feature the user did not select; for "set up everything", walk each feature sequentially
  in recommended order, confirming between each step
- ALWAYS read each status from the org just before you show it (step 0) — a failed read is **Couldn't
  check**, never **Not done**
- Do not show Salesforce record IDs in any output — human-readable names only

---

## Verification checklist

Before emitting any menu or summary, confirm each; adjust the output before sending if any is unchecked.

- [ ] The header line ends with `(via service-itsm-agentic-setup-incident-management)`
- [ ] Both prerequisite gates were read from the org through the `IncidentMgmt` SOR just before the menu
      or direct feature handoff; each off gate was asked with `AskUserQuestion` (Yes/No), not plain text,
      before the enable was delegated
- [ ] The exact `service-cloud-itsm-setup` entry verified exact `ENABLED` before the Incident-switch
      sequence; any other result stopped
- [ ] The feature menu is the full table, every row with its status, then the reply line — no
      `AskUserQuestion` for the choice
- [ ] Each status was read from the org just before this output (step 0) — a label and a short note
- [ ] A feature is being handled only because the user explicitly selected it (or is being walked through
      sequentially with confirmation under an "all" / "everything" request)
- [ ] For each feature: its reference file was read and its checks passed; its SORs ran under the
      hand-off protocol and no other skill was used; live state was read before any write; each
      write was confirmed and verified by read-back, and a no-write `Done` came from a live read; one-way /
      license-ordering invariants were honored
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

Read each `references/` file before executing its feature.

| File | When to read |
|------|--------------|
| `references/status-checks.md` | **Every run** — every status you show (step 0) and both gates (step 2): the labels, the Salesforce Go rule, each row's reads, the track roll-up |
| `examples/output-templates.md` | Behavior steps 3, 5, 6 — feature menu, post-feature progress, completion summary |
| `references/incident-preferences.md` | **Incident Preferences** — where to start in the `IncidentMgmt` SOR, the steps never to run, the one-way confirmations, and the licensed toggles |
| `references/incident-persona-psg.md` | **Incident Persona PSG** — the not-provisioned stop, the persona menu, one pass per PSG, and the settling status |
| `references/priority-matrix.md` | **Priority Matrix** — the reads, the full-replacement save, the read-back, and the Salesforce Go step |
| `references/sla-milestones.md` | **SLA & Milestones** — the one gate question, the lowercase seed, predefined vs custom, the milestone strategy, and milestone actions |
| `references/incident-dashboards.md` | **Incident Dashboards** — the persona choice, the two preferences each, and the dashboard check |
| `references/email-to-incident.md` | **Email-to-Incident** — the one-way enable, the full-map settings save, and routing addresses |
| `references/major-incident-management.md` | **Major Incident Management** — MIM must be active, the questions, reusing the approvers group, and validating before designating |
| `references/broadcast-communications.md` | **Broadcast Communications** — the one-way enable, then sender access, channels, and objects |
| `references/manage-incidents-with-ai.md` | **Manage Incidents with AI** — the three switches, which ones a request covers, the licensed ones, transcripts, and the smoke test |
| `references/service-mgmt-privilege.md` | **Service Management Privilege** — the toggle first, Tag-first, the irreversible delete, and the unverifiable assignments |
| `references/audit-tracking.md` | **Audit Tracking** — the field choice, the additive save, object-level tracking, and the read-back |
