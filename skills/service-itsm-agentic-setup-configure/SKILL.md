---
name: service-itsm-agentic-setup-configure
description: "Top-level orchestrator for setting up IT Service Management (ITSM) in Salesforce Service Cloud. Use when the user asks to set up ITSM, configure service management, enable ITSM capabilities, wants a guided walkthrough, or asks what is needed to get ITSM running. Presents a multi-select track menu and delegates to domain sub-orchestrators — Incident Management, Agentforce for ITSM (Studio + Fulfiller), CMDB, and Channels (Portal, Notifications, Microsoft Teams, Slack). Any prerequisites (such as the Incident Management master switch for Track 1) are owned and enforced inside the relevant sub-orchestrator, not at this level. Triggers on: set up ITSM, configure service management, ITSM setup, get ITSM running, walkthrough, set up CMDB / channels / Teams / Slack / Agentforce for ITSM. DO NOT TRIGGER when: the user asks about a specific feature directly (e.g., the priority matrix alone), asks only about Case management, wants to create a single user, or asks general ITSM questions without setup intent."
metadata:
  version: "1.3"
  domains: ["Service"]
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-coordinate"
    - "service-itsm-agentic-setup-cmdb-coordinate"
    - "service-itsm-agentic-setup-incident-management"
    - "service-itsm-channels-coordinate"
allowed-tools: Read AskUserQuestion
---

# ITSM Setup Orchestrator

Top-level coordinator for setting up IT Service Management in Salesforce Service Cloud. Guides the user through the available ITSM setup tracks by delegating to specialized domain sub-orchestrators.

## Goal

Present the user with the available ITSM setup tracks, help them understand what each covers, invoke the appropriate sub-orchestrator, and track overall progress until the environment is configured.

## Setup Tracks

Only tracks with a working sub-orchestrator appear in the menu — use the **Track menu** template in `examples/output-templates.md`.

## Sub-Orchestrators

| # | Track | Sub-Orchestrator Skill | Features |
|---|-------|------------------------|----------|
| 1 | Incident Management | `service-itsm-agentic-setup-incident-management` | SLA & Milestones |
| 2 | Agentforce for ITSM | `service-itsm-agentic-setup-agentforce-coordinate` | Agentforce Studio enablement, Fulfiller Agent, Employee Agent |
| 3 | CMDB (Configuration Management Database) | `service-itsm-agentic-setup-cmdb-coordinate` | CMDB feature enablement, CMDB Foundation bundle, User CMDB access |
| 4 | Channels | `service-itsm-channels-coordinate` | Employee Service channel setup — Portal, Notifications, Microsoft Teams (IT Desk / IT Service / embedded agent), and Slack |

Additional ITSM setup tracks (e.g. employee provisioning) will be added here as their sub-orchestrators become available.

## Behavior

### 1. Extract context from conversation

Before presenting tracks, scan chat history for:

- Whether the user has already configured any Incident Management features (mark as in progress or done)
- Whether the org-level Incident Management master switch has already been confirmed on
- Any preferences or constraints mentioned (e.g., "we only need the priority matrix", "we just want CMDB")
- The target org (if mentioned)
- Any specific features mentioned that narrow the scope

### 2. Present the available tracks as a multi-select

Emit the **Track menu** template from `examples/output-templates.md` AND, in the same response, a single `AskUserQuestion` call with `multiSelect: true` whose options mirror the rendered rows — the table is the visual view; the tool call is how the selection is collected. Both MUST appear together, never one without the other. Do NOT show tracks that have no working sub-orchestrator. Selecting one track is valid; selecting several enqueues them for sequential handling in step 3.

The menu MUST also include a **"Full guided setup"** option in addition to the per-track rows. Selecting it expands to *every* available track (all rows currently rendered in the table, in dependency order — see the "Sub-Orchestrators" table above). Treat it as if the user had selected every track in one interaction; step 3's sequential-confirmation loop still runs per-track, so the user can bail between any two tracks. Full guided setup is mutually exclusive with per-track selections — if the user picks it alongside individual tracks, treat it as "Full guided setup" and ignore the per-track picks. Emitting only per-track rows without the Full guided setup option violates this rule.

Do NOT run any org-level prerequisites at this level — each sub-orchestrator owns its own prerequisites (e.g., the Incident Management sub-orchestrator handles the master-switch confirmation internally). Delegating without pre-checking keeps this orchestrator agnostic about domain-specific dependencies and avoids prompting the user to change org state for a track they did not select.

### 3. Delegate to the selected sub-orchestrators in order

Handle the selections sequentially in the order the user listed them (or, if no order was expressed, in track number order). For each track, invoke the matching sub-orchestrator; that skill handles its own internal menu, prerequisites, and feature selection. When it returns, update the tracked status and move to the next selected track. Do not re-present the full track menu between selected tracks — the user already committed to that set in step 2.

### 4. After each sub-orchestrator completes

When the user returns from a sub-orchestrator:

1. **Update track status** — mark it as "Done"
2. **Move to the next selected track** if one remains

### 5. Offer additional tracks after the selected set completes

After the last track in the user's selection completes, ask whether they want to configure any of the remaining tracks. If yes, run step 2 again with the *remaining* tracks only. If not, go to step 6.

### 6. Completion summary

When the user says they're finished (or every available track is `Done`), present the **Completion summary** template from `examples/output-templates.md`.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-configure)" in the setup header
- ALWAYS present the track menu as a multi-select — accept a set of one or more tracks in a single interaction
- ALWAYS pair the rendered track-menu table with an `AskUserQuestion` (`multiSelect: true`) call in the same response — the table is the visual view; the tool call is the selection channel. Emitting the table alone breaks the selection channel; emitting the tool call alone hides the visual view
- ALWAYS include a **"Full guided setup"** option in the track menu (in addition to the per-track rows). It expands to every available track in dependency order — the sequential-confirmation loop still runs per-track so the user can stop between any two tracks. Full guided setup is mutually exclusive with per-track selections; if picked with individual tracks, treat it as Full guided setup and ignore the per-track picks
- NEVER run domain-level prerequisites (such as the Incident Management master switch) at this level — each sub-orchestrator owns and runs its own prerequisites, so users who did not select the relevant track are never prompted for unrelated org-level changes
- NEVER show a track that has no working sub-orchestrator
- NEVER configure a feature directly — always delegate to the sub-orchestrator (delegating through the domain orchestrator ensures its menu, progress tracking, and per-feature confirmations are applied; configuring directly bypasses that state and leaves the setup inconsistent)
- Track progress across the conversation
- Do not show Salesforce record IDs in any output — use human-readable names only
- If the user asks about a specific feature directly (e.g., "set up the priority matrix", "just enable CMDB"), you may skip the Behavior step 2 track menu and delegate directly to the corresponding sub-orchestrator; the sub-orchestrator will handle its own prerequisites as needed
- If the user asks for a setup area that is not yet available (e.g. employee provisioning, major incident management), tell them it is not yet available in this orchestrator and will be added as its sub-orchestrator merges

---

## Verification checklist

Before emitting any menu or summary in this skill, mentally confirm each of the following. If any box is unchecked, adjust the output before sending.

- [ ] The header line ends with `(via service-itsm-agentic-setup-configure)`
- [ ] Only tracks with a working sub-orchestrator are shown; placeholder tracks are hidden
- [ ] The track menu is presented as a multi-select (single-select is only acceptable when the user has already named a specific track directly)
- [ ] The track menu emitted BOTH the ASCII table AND an `AskUserQuestion` (`multiSelect: true`) presenting the same options in the same response — never one without the other
- [ ] The track menu included a **"Full guided setup"** option in addition to the per-track rows; if the user selected it, all available tracks were enqueued in dependency order with per-track confirmation between them
- [ ] Each track row's `Status` column reflects the actual tracked state from the conversation (`Not done`, `In progress`, or `Done`) — not a hard-coded default
- [ ] For a completion summary, the header line and closing line are chosen by the rubric in `examples/output-templates.md` (all `Done` → *Complete*; any `Not done`/`In progress` → *Finished*)
- [ ] No org-level prerequisites are being run at this level — the selected sub-orchestrator handles its own prerequisites
- [ ] The next action delegates to a sub-orchestrator, never directly to a feature child skill
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Behavior steps 2 and 6 — track menu (multi-select) and completion summary text blocks |
