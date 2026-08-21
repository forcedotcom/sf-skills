---
name: service-itsm-agentic-setup-incident-management
description: "Orchestrator skill for setting up Incident Management features in Salesforce Service Cloud ITSM. Use when the user asks to set up incident management, configure ITSM incident features, wants a guided walkthrough of incident management configuration, or asks what incident features are available to configure. Presents the available Incident Management capabilities and delegates each selection to a specialized child skill — currently SLA & Milestones — while tracking progress across the setup. Triggers on: set up incident management, configure ITSM incident features, incident management walkthrough, incident management capabilities, what incident features can I configure. DO NOT TRIGGER when: the user asks about a specific feature directly (e.g., an SLA alone without mentioning incident management setup), asks to create, clone, or provision users, Case management setup, or general ITSM questions without setup intent."
metadata:
  version: "1.2"
  domains: ["Service"]
  relatedSkills:
    - "service-itsm-agentic-setup-incident-sla-configure"
    - "service-itsm-incident-mgmt-configure"
    - "service-itsm-incident-priority-configure"
allowed-tools: Read AskUserQuestion
---

# Incident Management Setup Orchestrator

Guide the user through setting up Incident Management features in Salesforce Service Cloud ITSM by presenting the available capabilities, delegating to specialized child skills, and tracking progress.

## Goal

Act as the coordinator for Incident Management feature configuration. Present the user with a menu of configurable features, invoke the appropriate child skill for each selection, and after each feature completes, return to the menu with updated progress until the user is done.

## Behavior

### 0. Reuse what the session already knows

Before running any preflight below, check whether the same fact was already established
earlier in this conversation. Cache-eligible facts for this orchestrator:

- **Master switch state** — reuse **only when the master switch was confirmed
  enabled** by an earlier read or flip in this conversation. A cached "off" value
  MUST NOT let step 2 skip: the delegation exists precisely to flip an off switch
  on with user confirmation before downstream feature setup runs.
- **Already-completed features** — features the user (or a child skill) reported "Done"
  in an earlier turn stay "Done" — do not re-run their child skill unless the user asks
  to reconfigure.
- **Target org** — if the target org was already confirmed earlier in the conversation,
  reuse it; do not re-ask.

**When in doubt, re-check.** Skip only when the earlier fact is unambiguously in context
AND you have not switched orgs. If the user hints at a different org, or a child skill's
write elsewhere in the session could have invalidated the cached state (e.g., the master
switch was toggled off after being confirmed on), re-run the check. A wrong skip on a
live org write is worse than a duplicated read.

### 1. Extract context from conversation

Before presenting options, scan chat history for:

- Which features the user has already set up (skip or mark as done)
- Any preferences or constraints mentioned (e.g., "we only need the SLA milestones")
- The target org (if mentioned)
- Business context that informs which features are relevant

### 2. Ensure the Incident Management master switch is on (prerequisite)

Every Incident Management feature below depends on the org-level `service-cloud-itsm-incident` master switch being enabled — SLA milestones and downstream features cannot function while the switch is off. Before showing the feature menu, delegate to `service-itsm-incident-mgmt-configure` to read current state; if the switch is already on, it is a no-op — otherwise it confirms with the user before flipping it. **Skip this delegation only when the master switch was already confirmed *enabled* in this session — see Behavior step 0**. A cached "off" or unknown state MUST fall through to the delegation; a wrong skip here would silently let downstream feature setup run against an org where the master is off.

### 3. Present the Incident Management feature menu as a multi-select

Show the user what's available and what's done. Only features with a working child skill appear in the menu. Emit the **Feature menu** template from `examples/output-templates.md` AND, in the same response, a single `AskUserQuestion` call with `multiSelect: true` whose options mirror the rendered rows — the table is the visual view; the tool call is how the selection is collected. Both MUST appear together, never one without the other. Selecting one feature is valid; selecting several enqueues them for sequential handling in step 4. Do NOT show placeholder features that cannot be executed. Additional Incident Management features (Major Incident Management, Custom Fields, incident permission assignment, user provisioning) will be added to this menu as their child skills become available.

### 4. Delegate to child skills for each selected feature in order

Handle the user's selected features sequentially in dependency order (or the order given). For each selected feature, invoke the corresponding child skill:

| # | Feature | Child Skill |
|---|---------|-------------|
| 1 | SLA & Milestones | `service-itsm-agentic-setup-incident-sla-configure` |
| 2 | Priority Matrix | `service-itsm-incident-priority-configure` |

### 5. After each feature completes

Once a child skill finishes:

1. **Update the status** — mark the completed feature as "Done"
2. **Suggest the next logical step** — if another feature is available, recommend it based on the dependency order
3. **Re-present the menu** with updated status — use the **Post-feature progress** template in `examples/output-templates.md`

### 6. Completion summary

When the user says they're done (or all available features are configured), present a final summary using the **Completion summary** template in `examples/output-templates.md`.

---

## Feature Dependencies & Recommended Order

```text
1. SLA & Milestones      (attaches time-based commitments to incidents)
2. Priority Matrix       (derives Incident.Priority from Impact × Urgency)
```

Additional Incident Management features (Major Incident Management, Custom Fields, incident permission assignment, user provisioning) will be added to this menu as their child skills merge.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-incident-management)" in the setup header
- ALWAYS run the Incident Management master-switch prerequisite (Behavior step 2) before showing the feature menu, unless the user has already confirmed the switch is on earlier in this conversation — every downstream feature depends on it
- ALWAYS present the feature menu before configuring any selected feature — do not assume which feature the user wants (the master-switch prerequisite in Behavior step 2 is the only permitted action before the menu)
- ALWAYS present the feature menu as a multi-select — accept a set of one or more features in a single interaction
- ALWAYS pair the rendered feature-menu table with an `AskUserQuestion` (`multiSelect: true`) call in the same response — the table is the visual view; the tool call is the selection channel. Emitting the table alone breaks the selection channel; emitting the tool call alone hides the visual view
- NEVER set up a feature without the user selecting it (explicit selection confirms intent and avoids partial configurations if the user cancels mid-flow; for "set up everything" requests, use the sequential-confirmation loop in the rule below rather than batching all features in one pass)
- NEVER show features that do not have a working child skill
- If the user says "set up everything" or "all", walk through each available feature sequentially in the recommended order, confirming between each step
- Track progress across the conversation — do not re-present completed features as "Not done"
- Do not show Salesforce record IDs in any output — use human-readable names only
- If the user asks to create, clone, or provision users, or to assign incident permission sets, tell them those features are not yet available in this orchestrator and will be added as their child skills merge

---

## Verification checklist

Before emitting any menu or summary in this skill, mentally confirm each of the following. If any box is unchecked, adjust the output before sending.

- [ ] The header line ends with `(via service-itsm-agentic-setup-incident-management)`
- [ ] The Incident Management master switch has been confirmed on (via `service-itsm-incident-mgmt-configure`) before the feature menu is emitted, unless the user already confirmed it earlier in this conversation
- [ ] Only features with a working child skill are shown; placeholder features are hidden
- [ ] The feature menu is presented as a multi-select (single-select only if the user has already named a specific feature)
- [ ] The feature menu emitted BOTH the ASCII table AND an `AskUserQuestion` (`multiSelect: true`) presenting the same options in the same response — never one without the other
- [ ] Each feature row's `Status` column reflects the actual tracked state from the conversation (`Not done`, `In progress`, or `Done`) — not a hard-coded default
- [ ] For a completion summary, the header line and closing line are chosen by the rubric in `examples/output-templates.md` (all `Done` → *Complete*; any `Not done`/`In progress` → *Finished*)
- [ ] A feature is being configured only because the user explicitly selected it (or is being walked through sequentially with confirmation under an "all" / "everything" request)
- [ ] The next action delegates to a child skill, never configures a feature inline
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Behavior steps 3, 5, and 6 — feature menu (multi-select), post-feature progress, and completion summary text blocks |
