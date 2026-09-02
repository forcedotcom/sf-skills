---
name: service-itsm-agentic-setup-configure
description: "Top-level orchestrator for setting up IT Service Management (ITSM) in Salesforce Service Cloud. Use when the user asks to set up ITSM, configure service management, wants a guided walkthrough, or asks what is needed to get ITSM running. Presents a paged multi-select track menu and delegates to domain sub-orchestrators — Incident Management, Agentforce for ITSM, CMDB, Channels (Portal, Notifications, Microsoft Teams, Slack), and Unified Catalog (find and deploy Service Process templates). Prerequisites (e.g., the Incident Management master switch) are owned inside the relevant sub-orchestrator, not at this level. Triggers on: set up ITSM, configure service management, ITSM setup, get ITSM running, set up CMDB / channels / Teams / Slack / Agentforce for ITSM / Unified Catalog templates. DO NOT TRIGGER when: the user asks about a specific feature directly (e.g., the priority matrix alone), asks only about Case management, wants to create a single user, or asks general ITSM questions without setup intent."
metadata:
  version: "1.6"
  domains: ["Service"]
  relatedSkills:
    - "service-catalog-template-coordinate"
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
| 5 | Unified Catalog | `service-catalog-template-coordinate` | Find and deploy Unified Catalog Service Process templates (search / rank, then install / activate) |

Additional ITSM setup tracks (e.g. employee provisioning) will be added here as their sub-orchestrators become available.

## Behavior

### 1. Extract context from conversation

Before presenting tracks, scan chat history for:

- Whether the user has already configured any Incident Management features (mark as in progress or done)
- Whether the org-level Incident Management master switch has already been confirmed on
- Any preferences or constraints mentioned (e.g., "we only need the priority matrix", "we just want CMDB")
- The target org (if mentioned)
- Any specific features mentioned that narrow the scope

Derive each track's status from the **most recent** sub-orchestrator activity in the transcript, not from the last-rendered menu — a track is only the "active" one if it is the latest track actually being worked. On a long or **resumed** conversation (e.g. a headless session continued later), the earlier transcript can still prominently show a prior track: do not treat the last highlighted row as current. If it is ambiguous which track is active, re-confirm with the user (`AskUserQuestion`) before rendering the menu rather than carrying a stale highlight forward.

### 2. Present the available tracks as a paged multi-select

Emit the **Track menu** table from `examples/output-templates.md` (visual map — every available track and `Full guided setup`). In the SAME response, dispatch the first page of a multi-select `AskUserQuestion`. `Full guided setup` is a first-class pickable option in the same multi-select — not a separate mode selector. The user picks any combination of tracks in one flow.

**`AskUserQuestion` accepts at most 4 options per call.** With today's 5 tracks + `Full guided setup` = 6 options, the menu is paged. Each page has up to **3 tracks (or `Full guided setup` + 2 tracks on page 1) + `Show more tracks →` as the 4th option** when more content follows. Selections **accumulate across pages** — a pick on page 1 stays picked when the user moves to page 2. Stop paging when the user submits a page without `Show more tracks →`, or the last page has been dispatched (no `Show more tracks →` sentinel needed on the last page). Strip `Show more tracks →` from the final accumulated selection before delegating.

**Selection resolution.** If the accumulated set contains `Full guided setup`, run every available track in dependency order (per-track confirmation from step 3 still applies — the user can stop between any two tracks). Otherwise, run only the picked tracks, in dependency order (or track number order if unspecified).

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
- ALWAYS present the track menu as a **paged multi-select** — a single `AskUserQuestion` per page with `multiSelect: true`. `Full guided setup` is a first-class option in the multi-select (page 1, first slot) — NEVER split it into a separate mode-selector stage. NEVER render more than 4 options in a single `AskUserQuestion` — the tool schema hard-caps `options` at 4 and the dispatch fails with an "invalid parameter" error before the user sees the menu
- WHEN the total options (tracks + `Full guided setup`) exceed 4, PAGE the menu. The algorithm is **scale-free** — more tracks produce more pages automatically without changing the shape: page 1 = `Full guided setup` + up to 2 tracks + `Show more tracks →` (4 slots); each middle page = up to 3 tracks + `Show more tracks →` (4 slots), repeated as many times as needed until ≤ 4 tracks remain; last page = the remaining ≤ 4 tracks with NO sentinel. Concrete page counts: 4 tracks → 2 pages, 7 tracks → 3 pages, 10 tracks → 4 pages (the count grows by one page for every ~3 new tracks). **Accumulate selections across pages** — a pick on page 1 stays picked when the user pages forward. Strip `Show more tracks →` from the final accumulated selection before delegating
- ALWAYS emit the ASCII table AND the page-1 `AskUserQuestion` in the same response — the table is the visual map (all tracks + `Full guided setup`); the multi-select is the selection channel. Emitting the table alone breaks the selection channel; emitting the multi-select alone hides the visual view
- WHEN the accumulated selection contains `Full guided setup`, expand to every available track in dependency order (step 3's per-track confirmation still runs so the user can stop between any two tracks). Otherwise, run only the picked tracks. `Full guided setup` picked alongside individual tracks means "run everything" — treat it as Full guided setup and ignore the per-track picks
- NEVER run domain-level prerequisites (such as the Incident Management master switch) at this level — each sub-orchestrator owns and runs its own prerequisites, so users who did not select the relevant track are never prompted for unrelated org-level changes
- NEVER show a track that has no working sub-orchestrator
- NEVER configure a feature directly — always delegate to the sub-orchestrator (delegating through the domain orchestrator ensures its menu, progress tracking, and per-feature confirmations are applied; configuring directly bypasses that state and leaves the setup inconsistent)
- Track progress across the conversation — re-derive each track's status from the latest sub-orchestrator activity in the transcript, not from the previously rendered highlight. On a resumed or long conversation, do not assume the last-highlighted track is still current; if ambiguous, re-confirm the active track with the user before rendering the menu
- Do not show Salesforce record IDs in any output — use human-readable names only
- If the user asks about a specific feature directly (e.g., "set up the priority matrix", "just enable CMDB"), you may skip the Behavior step 2 track menu and delegate directly to the corresponding sub-orchestrator; the sub-orchestrator will handle its own prerequisites as needed
- If the user asks for a setup area that is not yet available (e.g. employee provisioning, major incident management), tell them it is not yet available in this orchestrator and will be added as its sub-orchestrator merges

---

## Verification checklist

Before emitting any menu or summary in this skill, mentally confirm each of the following. If any box is unchecked, adjust the output before sending.

- [ ] The header line ends with `(via service-itsm-agentic-setup-configure)`
- [ ] Only tracks with a working sub-orchestrator are shown; placeholder tracks are hidden
- [ ] The track menu was emitted as a **single-stage paged multi-select** — `Full guided setup` is a first-class option in the multi-select (page 1, first slot), NOT a separate mode-selector stage
- [ ] The ASCII table AND the page-1 `AskUserQuestion` were emitted in the same response — never one without the other
- [ ] When total options (tracks + `Full guided setup`) > 4, pages followed the shape: page 1 = `Full guided setup` + up to 2 tracks + `Show more tracks →`; middle pages = up to 3 tracks + `Show more tracks →`; last page = remaining ≤ 4 tracks with no sentinel. Selections were accumulated across pages and `Show more tracks →` was stripped from the final selection
- [ ] If the accumulated selection contained `Full guided setup`, every available track was enqueued in dependency order with per-track confirmation between them (per-track picks were ignored when `Full guided setup` was included)
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
