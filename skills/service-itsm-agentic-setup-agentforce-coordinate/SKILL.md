---
name: service-itsm-agentic-setup-agentforce-coordinate
description: "Orchestrator for setting up Agentforce in Salesforce Service Cloud ITSM — Agentforce Studio enablement, the IT Service Fulfiller agent lifecycle, and the IT Service Employee agent lifecycle. Use when the user asks to set up Agentforce for ITSM, enable Studio and the Fulfiller/Employee agents together, wants a guided Agentforce ITSM walkthrough, or asks what Agentforce features are available for IT Service. Presents available Agentforce capabilities and delegates each selection to a specialized child skill while tracking progress. Triggers on: set up agentforce for itsm, configure agentforce studio and fulfiller, agentforce itsm walkthrough, what agentforce features for it service. DO NOT TRIGGER when: the user asks to enable Agentforce Studio alone, asks to create or activate the Fulfiller or Employee agent alone, or asks about CMDB, Incident Management, Teams, or general ITSM setup without Agentforce intent."
metadata:
  version: "1.2"
  domains: ["Service", "Agentforce"]
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-configure"
    - "service-itsm-agentic-setup-agentforce-studio-validate"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
allowed-tools: Read Bash Write AskUserQuestion
---

# Agentforce for ITSM Setup Orchestrator

Guide the user through setting up Agentforce Studio, the IT Service Fulfiller agent, and the IT Service Employee agent in Salesforce Service Cloud ITSM by presenting the available capabilities, delegating to specialized child skills, and tracking progress.

## Goal

Act as the coordinator for Agentforce feature configuration in ITSM. Present the user with a menu of configurable features, invoke the appropriate child skill for each selection, and after each feature completes, return to the menu with updated progress until the user is done.

## Behavior

### 1. Extract context from conversation

Before presenting options, scan chat history for:

- Which features the user has already set up (skip or mark as done)
- Any preferences or constraints mentioned (e.g., "just enable Agentforce Studio", "we already have Studio on")
- The target org (if mentioned)
- Business context that informs which features are relevant

### 2. Confirm the target org

Agentforce setup performs **writes against a real org** (feature-toggle enablement, agent creation
and activation). Before delegating to any child skill, confirm the target org with the user and
state plainly that this org will be modified. Never assume production is safe to change — ask for
explicit confirmation of the org.

### 3. Present the Agentforce feature menu as a multi-select

Show the user what's available and what's done. Only features with a working child skill appear in the menu — use the **Feature menu** template in `examples/output-templates.md`. Collect the user's selections through a single multi-select prompt (use `AskUserQuestion` with `multiSelect: true` when tooling permits, otherwise ask the user to reply with a list of numbers such as `1, 2`). Do NOT show placeholder features that cannot be executed.

**Report file (harness / non-interactive runs).** If a `${outputDir}` is provided (via the harness's generated-file location directive), write the menu emission (attribution header + feature table with status + delegation targets + dependency signal + the multi-select prompt itself) to `${outputDir}/report.md` **before** raising `AskUserQuestion` — so the report file always exists even when the harness parks at the confirmation gate. Overwrite the same file after each feature completes with the updated status table. Skip these writes when running interactively for a user in a chat surface — write only when `${outputDir}` was passed as an explicit destination.

### 4. Delegate to child skills in dependency order

**Studio-first rule (unconditional).** If Agentforce Studio enablement (#1) is in the user's selection and not already done, run it **first**, always — regardless of the order the user listed their numbers in. Both the Fulfiller Agent (#2) and Employee Agent (#3) lifecycles depend on Studio being enabled and will fail if attempted first. Reorder the queue silently so Studio runs before either agent lifecycle. This rule is non-negotiable and applies whether the user selected two features (Studio + one agent) or all three.

**User-order rule (between #2 and #3 only).** Fulfiller Agent (#2) and Employee Agent (#3) are independent of each other — neither depends on the other. If **both** are selected, run them in the order the user listed them (default 2 → 3 when unspecified). This rule applies **only** to the ordering between #2 and #3; it never overrides the Studio-first rule above.

| # | Feature | Child Skill |
|---|---------|-------------|
| 1 | Agentforce Studio enablement | `service-itsm-agentic-setup-agentforce-studio-configure` |
| 2 | Fulfiller Agent lifecycle | `service-itsm-agentic-setup-fulfiller-agent-configure` |
| 3 | Employee Agent lifecycle (broad or specialized template) | `service-itsm-agentic-setup-employee-agent-configure` |

`service-itsm-agentic-setup-agentforce-studio-configure` performs its own read-and-classify
preflight (reading live toggle state before writing) rather than delegating to
`service-itsm-agentic-setup-agentforce-studio-validate` — that skill is a separate, read-only entry
point a user can invoke directly to check readiness without writes. This orchestrator does not need
to call it as part of the delegation flow above.

### 5. After each feature completes

Once a child skill finishes:

1. **Verify** the child skill's own deterministic verdict by running
   `node "<skill_dir>/scripts/verify-child-verdict.mjs" <studio|fulfiller|employee> <verdict>` — never
   re-derive the success/failure comparison in prose. Pass Studio's `overall` field from
   `classify-final-report.mjs`, or Fulfiller/Employee Agent's Phase 8 aggregate verdict, as
   `<verdict>`. Exit code `0` means advance; exit code `1` means **stop and surface the failure in
   plain language — do not advance to the next feature in the queue.** A partially-enabled Studio
   (e.g. Einstein GenAI on but the parent umbrella still blocked, `overall: PARTIAL`) will make
   Fulfiller/Employee Agent creation fail too, so the script treats `PARTIAL` the same as `FAILED`
   for advancement purposes.
2. **Update the status** — mark the completed feature as "Done"
3. **Suggest the next logical step** — if another feature is available, recommend it based on the dependency order
4. **Re-present the menu** with updated status — use the **Post-feature progress** template in `examples/output-templates.md`

### 6. Completion summary

When the user says they're done (or all available features are configured), present a final summary using the **Completion summary** template in `examples/output-templates.md`.

---

## Feature Dependencies & Recommended Order

```text
1. Agentforce Studio enablement   (foundation — org-level Agentforce and Einstein GenAI toggles)
2. Fulfiller Agent lifecycle      (create, commit, activate the IT Service Fulfiller agent)
3. Employee Agent lifecycle       (create, commit, activate the IT Service Employee agent)
```

Agentforce Studio enablement is the foundation: it turns on the org-level Agentforce and Einstein GenAI features that both the Fulfiller and Employee agents depend on. Configure Studio first — attempting to create or activate either agent before Studio is enabled will fail. Fulfiller and Employee are independent siblings (neither depends on the other) — both can be selected together and run in either order after Studio.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-agentforce-coordinate)" in the setup header
- ALWAYS present the feature menu before doing anything — do not assume which feature the user wants
- ALWAYS present the feature menu as a multi-select — accept a set of one or more features in a single interaction
- NEVER set up a feature without the user selecting it. (Explicit selection ensures the user confirms intent and avoids partial configurations if they cancel mid-flow; use the sequential-confirmation loop in the "set up everything" rule for bulk requests.)
- NEVER show features that do not have a working child skill
- If the user says "set up everything" or "all", walk through each available feature sequentially in the recommended order, confirming between each step
- Track progress across the conversation — do not re-present completed features as "Not done"
- NEVER advance to the next feature in the queue if the current one failed or only partially
  succeeded — stop and surface the failure in plain language instead
- If Agentforce Studio enablement reports the org lacks the Agentforce license (`accessCheck`), STOP
  the whole flow — this is a license/edition prerequisite no API can grant, and neither the
  Fulfiller nor the Employee Agent lifecycle can succeed without it
- ALWAYS confirm the target org before delegating to any child skill, and state that the org will be modified
- Do NOT expose internal technical jargon in user-facing output. This includes Salesforce record
  IDs and org IDs, raw HTTP status codes (403, 500, …), API error codes (`FUNCTIONALITY_NOT_ENABLED`,
  `DUPLICATE_VALUE`, …), internal endpoint/API names, developer names (feature apiNames like
  `sales-cloud-agent-studio`), and CLI/tooling internals. Translate everything to plain, human-readable
  language. Child-skill names shown as next-step pointers are fine.
- If the user asks about Agentforce features that are not yet available (e.g., Requester agent, custom topic packs, agent metrics dashboards), tell them those features are not yet available in this orchestrator and will be added as their child skills merge

---

## Verification checklist

Before emitting any menu or summary in this skill, mentally confirm each of the following. If any box is unchecked, adjust the output before sending.

- [ ] The header line ends with `(via service-itsm-agentic-setup-agentforce-coordinate)`
- [ ] The target org was confirmed with the user, and they were told it will be modified, before any child skill ran
- [ ] The current feature's child-skill result was verified as a full success before advancing to the next queued feature — a failed or partial result stopped the queue instead
- [ ] Only features with a working child skill are shown; placeholder features are hidden
- [ ] The feature menu is presented as a multi-select (single-select only if the user has already named a specific feature)
- [ ] Each feature row's `Status` column reflects the actual tracked state from the conversation (`Not done`, `In progress`, or `Done`) — not a hard-coded default
- [ ] For a completion summary, the header line and closing line are chosen by the rubric in `examples/output-templates.md` (all `Done` → *Complete*; any `Not done`/`In progress` → *Finished*)
- [ ] A feature is being configured only because the user explicitly selected it (or is being walked through sequentially with confirmation under an "all" / "everything" request)
- [ ] Studio enablement is verified done before delegating to the Fulfiller Agent or Employee Agent child skill
- [ ] The next action delegates to a child skill, never configures a feature inline
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Behavior steps 2, 4, and 5 — feature menu (multi-select), post-feature progress, and completion summary text blocks |
| `scripts/verify-child-verdict.mjs` | Behavior step 5 — run via `Bash` (`node`) to check a child skill's verdict deterministically before advancing the queue |
