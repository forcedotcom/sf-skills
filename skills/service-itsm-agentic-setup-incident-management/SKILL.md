---
name: service-itsm-agentic-setup-incident-management
description: "Orchestrator for Incident Management setup in Service Cloud ITSM: presents the features, tracks progress, and configures each — SLA & Milestones, Priority Matrix, Incident preferences, Major Incident Management, Incident persona PSG assignment, Service Management Privilege, and Incident audit tracking. Use for: set up or configure incident management, incident management walkthrough, what incident features can I configure; the incident preference toggles (default field validations, auto-close child incidents, auto-triage, assign with Einstein, restrict assigned group, rich text descriptions); Major Incident Management (approval group + MIM preferences); assigning the Incident Fulfiller or Incident Manager persona PSG; Service Management Privilege / privilege escalation setup. DO NOT TRIGGER for: the master on/off switch (service-itsm-incident-mgmt-configure), the Priority Matrix, SLA, or field history tracking alone, the Major Incident Manager PSG, creating/editing PSGs, or Problem/Change/Case Management."
metadata:
  version: "2.1"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "dx-org-permission-set-assign"
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-incident-sla-configure"
    - "service-itsm-agentic-setup-itsm-agentforce-permset-assign"
    - "service-itsm-incident-mgmt-configure"
    - "service-itsm-incident-priority-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Incident Management Setup Orchestrator

Guide the user through setting up Incident Management features in Salesforce Service Cloud ITSM by
presenting the available capabilities, tracking progress, and — per feature — either **delegating** it (to
a specialized child skill, or to a Setup Operation Recipe (SOR) whose own steps this skill follows), or
**executing it inline** from this skill's reference file over its SOR.

## Goal

Act as the coordinator for Incident Management feature configuration. Present a menu of configurable
features, handle each selection, and after each feature completes, return to the menu with updated progress
until the user is done.

## How each feature is handled

| # | Feature | Handled by |
|---|---------|-----------|
| 1 | SLA & Milestones | **Delegate** → `service-itsm-agentic-setup-incident-sla-configure` |
| 2 | Priority Matrix | **Delegate** → `service-itsm-incident-priority-configure` |
| 3 | Incident Preferences | **Inline over SOR** → `references/incident-preferences.md` |
| 4 | Major Incident Management | **Inline over SOR** → `references/major-incident-management.md` |
| 5 | Incident Persona PSG | **Inline over SOR** → `references/incident-persona-psg.md` |
| 6 | Service Management Privilege | **Inline over SOR** → `references/service-mgmt-privilege.md` |
| 7 | Audit Tracking | **Delegate** → `FieldHistoryTracking` (the Field History Tracking SOR) |

**Delegated** features hand off to their child skill or SOR. A child skill runs its own confirmations and
read-backs, so this skill only coordinates. A SOR is a recipe, not an agent: for a SOR hand-off this skill
runs the SOR's steps itself and owns the confirmation and read-back (see Audit Tracking below).
**Inline** features are run by this skill directly through the `headless-360` MCP server — **read the
matching reference file before executing that feature** and follow it. Every inline operation is fetched at
runtime: `discover` by intent, `describe` for the current route/schema/labels, then `dispatch_readonly`
(reads) / `dispatch` (writes). **Hardcode nothing — `describe` wins.**

**Audit Tracking is delegated to the Field History Tracking SOR.** This skill has no reference file for it
and re-derives none of its steps — the SOR's own steps and guidance decide *how*. This skill runs them and
owns the user-facing gates:

1. `discover` the SOR by intent (e.g. "field history tracking") and `describe` the id `discover` returns
   (`FieldHistoryTracking`). Judge availability by what the calls return, not by a step's `status` label —
   a step labelled `proposed` may still be served. A `discover` miss or a `401`/`403`/`404` means the
   surface isn't available to this user or org: surface it and stop.
2. Use the Incident fields the user already named, or ask which fields to track if the choice is missing
   or ambiguous, plus anything else `describe` says it needs. If the user chooses no fields, leave the
   feature `Not done` and stop; do not treat an empty choice as already configured.
3. Through the SOR, check Setup access, read Incident with `get-single-entity-data-with-metadata`, and get
   its per-object tracked-field limit. Use the returned tracking flag, field labels, `canBeTracked` values,
   current tracked set, and `fieldEnumOrId` keys to resolve the user's choices; do not guess field keys.
4. The save replaces the object's whole tracked-field set, so send the **union** of what's already tracked
   and the chosen fields using their returned keys, with Incident's object-level tracking flag on — never
   drop an already-tracked field unless the user asks. If a chosen field can't be tracked, or the union
   would exceed the limit, say so plainly; never untrack another field to make room. Report it as done
   with no write only if the nonempty chosen set is already tracked **and** Incident's object-level tracking
   is on. If the fields are selected but that flag is off, the change still needs a save.
5. Show the exact final tracked-field list by field label (disambiguate matching labels) in either case.
   Before any save, also show that object-level tracking will be enabled and get an explicit yes
   (`AskUserQuestion`) for that plan; when the user already named the fields, this confirms the selection.
6. After any save, read Incident's tracked fields back through the SOR. Mark the feature `Done` only when
   the live read (for the no-write case) or post-save read-back shows Incident's object-level tracking on,
   the chosen fields tracked, and no field dropped that the user didn't ask to drop — a save response alone
   is not proof.

## Behavior

### 0. Reuse what the session already knows

Before running any preflight below, check whether the same fact was already established earlier in this
conversation. Cache-eligible: the **master switch state** (reuse **only when confirmed *enabled***; a
cached "off" MUST NOT let step 2 skip), **already-completed features** (stay "Done"; don't re-run unless
asked to reconfigure), and the **target org**. **When in doubt, re-check.** Skip only when the earlier fact
is unambiguously in context AND you have not switched orgs — a wrong skip on a live write is worse than a
duplicated read.

### 1. Extract context from conversation

Scan chat history for which features are already done, any stated preferences/constraints, the target org,
and business context that informs which features are relevant.

### 2. Ensure the Incident Management master switch is on (prerequisite)

Every feature below depends on the org-level `service-cloud-itsm-incident` master switch being enabled.
Before showing the menu, delegate to `service-itsm-incident-mgmt-configure` to read current state; if on,
it is a no-op — otherwise it confirms with the user before flipping it. **Skip only when the master switch
was already confirmed *enabled* in this session** (see step 0). A cached "off"/unknown state MUST fall
through to the delegation.

### 3. Present the feature menu as a multi-select

Emit the **Feature menu** template from `examples/output-templates.md` AND, in the same response, a single
`AskUserQuestion` (`multiSelect: true`) whose options mirror the rendered rows — the table is the visual
view; the tool call collects the selection. Both MUST appear together. Selecting one feature is valid;
several enqueue for sequential handling in step 4.

### 4. Handle each selected feature in order

Handle selected features sequentially in dependency order (or the order given). For each: if it is a
**delegated** feature, hand off to its child skill — or, for Audit Tracking, run the Field History Tracking
SOR through the six steps above; if it is an **inline** feature, **read its reference file** and execute it
there. Whenever this skill itself writes (inline, or a SOR hand-off), always **read live state before
writing, confirm before every write, and verify every write by read-back**. Honor the per-feature
invariants below.

### 5. After each feature completes

Mark it "Done", suggest the next logical step, and re-present the menu with updated status using the
**Post-feature progress** template in `examples/output-templates.md`.

### 6. Completion summary

When the user says they're done (or all features are configured), present the **Completion summary**
template in `examples/output-templates.md`.

---

## Critical inline-execution invariants (load-bearing — full detail in each reference)

Apply these whenever an inline feature runs; the **Everywhere** rules also apply to the Audit Tracking SOR
hand-off. They are irreversible or silently-wrong if missed.

- **Resolve the right node (Preferences).** Target the ITSM Incident Management org-preferences node
  (controller `IPCManagementSetupController`), **not** the Service-Foundation look-alike
  (`IncidentMgmtSetupController`, broadcast channels + a master switch).
- **Two preferences are one-way / enable-only (Preferences).** *Restrict Assigned Group to Regular Groups*
  and *Enable Rich Text for Incident Descriptions* cannot be turned off once on. Never offer to disable
  them; require an explicit "I understand this can't be undone" confirmation before enabling; never enable
  to test. *Restrict Assigned Group…* also **freezes once the org has any Incident record** — an enable can
  fail outright; do not retry.
- **License, not assignment (Major Incident Management).** MIM is the approval group + two preferences on
  top of **base** Incident Management. The Major Incident Manager grant is a **LICENSE**
  (`PermissionSetLicenseAssign`), never a `PermissionSetAssignment`. **License before group membership;
  validate group users before designating a group; remove before reassign.** Only two preference names are
  valid: `AutoCreationOfProblem`, `AutoClosureChildIncidents`.
- **PSL before PSG (Persona).** Assign the union of a persona PSG's member permission-set **licenses first,
  then the PSG** (keyed on `PermissionSetGroupId`, never a permission-set Id) — otherwise the persona is
  silently half-provisioned. Query the persona PSGs by `DeveloperName` with **no** `NamespacePrefix` filter.
- **Destructive delete + unverifiable assignments (Service Management Privilege).** Deleting a Service
  Management Privilege is irreversible — confirm explicitly, never delete to test. Bulk employee↔privilege
  assignments have **no read-back** — report them as applied, not verified. The *Enable Privilege Assignment*
  master toggle is the UI entry gate (reversible; the controller does not re-check it), so enable it first as
  workflow ordering, not a hard precondition. No public API substitute exists — a `404` / discover-miss means
  the surface isn't served on this org yet; surface it and stop.
- **Everywhere:** read before write; treat "already in that state" / a duplicate as idempotent success;
  verify by read-back (a write response alone is not proof); each license consumes a seat; on `401`/`403`/
  `404` surface the raw error and stop; keep record Ids, HTTP codes, route paths, and tooling terms
  (`dispatch`, `headless-360`, SOR/step ids) out of user-facing output.

---

## Feature Dependencies & Recommended Order

```text
1. SLA & Milestones            (time-based commitments on incidents)      [delegated]
2. Priority Matrix             (Impact × Urgency → Incident.Priority)      [delegated]
3. Incident Preferences        (the six per-feature setup toggles)         [inline]
4. Major Incident Management   (approval group + two MIM preferences)      [inline]
5. Incident Persona PSG        (Fulfiller / Manager persona for a user)    [inline]
6. Service Management Privilege (escalation level + privilege assignments) [inline]
7. Audit Tracking              (field history on chosen Incident fields)   [delegated]
```

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-incident-management)" in the setup header
- ALWAYS run the master-switch prerequisite (Behavior step 2) before showing the menu, unless the user
  already confirmed the switch is on earlier in this conversation
- ALWAYS present the feature menu before configuring any selected feature (the master-switch prerequisite
  is the only permitted action before the menu) — do not assume which feature the user wants, **except**
  when the user named a specific feature, in which case go straight to it (single-select is fine)
- ALWAYS pair the rendered feature-menu table with an `AskUserQuestion` (`multiSelect: true`) in the same
  response — the table is the visual view; the tool call is the selection channel
- For an **inline** feature, ALWAYS read its reference file first and follow the SOR at runtime — never
  hardcode a route, body, or preference name
- For **Audit Tracking**, ALWAYS keep every already-tracked Incident field in the save unless the user asked
  to stop tracking it, confirm the exact final field list before the save, and verify by read-back before
  marking it `Done` (or verify the already-configured state by live read with no write) — the SOR asks the
  user nothing itself
- NEVER set up a feature the user did not select; for "set up everything", walk each feature sequentially
  in recommended order, confirming between each step
- Track progress across the conversation — do not re-present completed features as "Not done"
- Do not show Salesforce record IDs in any output — human-readable names only

---

## Verification checklist

Before emitting any menu or summary, confirm each; adjust the output before sending if any is unchecked.

- [ ] The header line ends with `(via service-itsm-agentic-setup-incident-management)`
- [ ] The master switch was confirmed on (via `service-itsm-incident-mgmt-configure`) before the menu,
      unless already confirmed earlier in this conversation
- [ ] The feature menu emitted BOTH the ASCII table AND an `AskUserQuestion` (`multiSelect: true`) in the
      same response (single-select only if the user already named a specific feature)
- [ ] Each feature row's `Status` reflects the actual tracked state (`Not done`, `In progress`, `Done`)
- [ ] A feature is being handled only because the user explicitly selected it (or is being walked through
      sequentially with confirmation under an "all" / "everything" request)
- [ ] For an inline feature: its reference file was read; live state was read before any write; each write
      was confirmed and verified by read-back; one-way / license-ordering invariants were honored
- [ ] For a delegated feature: the child skill (or, for Audit Tracking, the Field History Tracking SOR) was
      used, not configured inline
- [ ] For Audit Tracking: a live metadata read resolved the fields and complete labeled set; any save kept
      every already-tracked field the user didn't ask to drop, was confirmed before it ran, and was verified
      by read-back; a no-write `Done` also had Incident's object-level tracking confirmed on
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Behavior steps 3, 5, 6 — feature menu (multi-select), post-feature progress, completion summary |
| `references/incident-preferences.md` | Before executing the **Incident Preferences** feature — the six preferences, the one-way rules, the SOR delegation map, invariants, and failure taxonomy |
| `references/major-incident-management.md` | Before executing the **Major Incident Management** feature — the two surfaces (approval group + preferences), licensing preconditions, ordering, invariants |
| `references/incident-persona-psg.md` | Before executing the **Incident Persona PSG** feature — the two persona PSGs, PSL-before-PSG ordering, resolution rules, invariants |
| `references/service-mgmt-privilege.md` | Before executing the **Service Management Privilege** feature — the Enable Privilege Assignment toggle, escalation level, privilege CRUD (destructive delete), bulk assignments (no read-back), and the SOR step map |
