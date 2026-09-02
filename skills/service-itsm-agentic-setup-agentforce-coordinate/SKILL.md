---
name: service-itsm-agentic-setup-agentforce-coordinate
description: "Orchestrator for setting up Agentforce in Salesforce Service Cloud ITSM — Agentforce Studio enablement, the IT Service Fulfiller agent, the IT Service Employee agent, and specialized employee agents. Use when the user asks to set up Agentforce for ITSM, enable Studio and the Fulfiller/Employee agents together, wants a guided Agentforce ITSM walkthrough, or asks what Agentforce features are available for IT Service. Presents available Agentforce capabilities and delegates each selection to a specialized child skill while tracking progress. Triggers on: set up agentforce for itsm, configure agentforce studio and fulfiller, agentforce itsm walkthrough, what agentforce features for it service. DO NOT TRIGGER when: the user asks to enable Agentforce Studio alone, asks to create or activate the Fulfiller or Employee agent alone, or asks about CMDB, Incident Management, Teams, or general ITSM setup without Agentforce intent."
metadata:
  version: "1.7"
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

Guide the user through setting up Agentforce Studio, the IT Service Fulfiller agent, the IT Service Employee agent, and specialized employee agents in Salesforce Service Cloud ITSM by presenting the available capabilities, delegating to specialized child skills, and tracking progress.

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

Show the user what's available and what's done, organized into the **two sequential setup stages** —
**Stage 1: enable platform features** (Agentforce Studio enablement) and **Stage 2: install &
activate agent templates** (the Fulfiller and Employee agents). This separation is load-bearing:
Stage 1 *enables* org-level platform toggles/preferences, while Stage 2 *installs and activates*
agents from a template — they are distinct kinds of action and must read as distinct stages, not one
undifferentiated list. Only features with a working child skill appear in the menu — use the
**Feature menu** template in `examples/output-templates.md`. Collect the user's selections through a single multi-select prompt (use `AskUserQuestion` with `multiSelect: true` when tooling permits, otherwise ask the user to reply with a list of numbers such as `1, 2`). Use the **exact Item names from the Feature menu table** as the multi-select option labels — verbatim, including each item's parenthetical note and the word "Agent" and its capitalization (`Agentforce Studio enablement (Foundation for all agents)`, `IT Service Fulfiller Agent`, `IT Service Employee Agent`, `Specialized Agents for Employee`) — so the picker options and the table never diverge. Each item's **Description column matches the wording on the Salesforce Setup → Agentforce for IT Service page** (the Fulfiller and Employee agent-template descriptions and the Specialized Agents for Employee text are used verbatim) so a user evaluating which template to install reads the same purpose/scope here as they would in Setup — do not paraphrase or shorten that product copy. For the three Stage 2 agent items, follow the verbatim product copy with one short trailing `Setup:` line stating what installing does (`Setup: creates the agent from this template and activates a version.` for the Fulfiller and Employee agents; `Setup: pick one specialized template (e.g. Password Manager, Onboarding), then create and activate that standalone agent. Re-run this item to add more.` for Specialized Agents for Employee, for which you first ask the user which specialized template they want and pass that name to the child skill) so a single row carries purpose, scope, and the install action together. The Stage 1 row (Agentforce Studio enablement) is a platform-enablement toggle, not a template install, so it carries no `Setup:` line. When raising `AskUserQuestion`, put that same Description text (product copy + the `Setup:` line) in each option's `description` field so the picker carries the detail too. Do NOT show placeholder features that cannot be executed.

**Report file (harness / non-interactive runs).** If a `${outputDir}` is provided (via the harness's generated-file location directive), write the menu emission (attribution header + feature table with status + delegation targets + dependency signal + the multi-select prompt itself) to `${outputDir}/report.md` **before** raising `AskUserQuestion` — so the report file always exists even when the harness parks at the confirmation gate. Overwrite the same file after each feature completes with the updated status table. Skip these writes when running interactively for a user in a chat surface — write only when `${outputDir}` was passed as an explicit destination.

### 4. Delegate to child skills in dependency order

**Studio-first rule (unconditional).** If Agentforce Studio enablement (#1) is in the user's selection and not already done, run it **first**, always — regardless of the order the user listed their numbers in. The Fulfiller Agent (#2), Employee Agent (#3), and Specialized Agents for Employee (#4) all depend on Studio being enabled and will fail if attempted first. Reorder the queue silently so Studio runs before any agent. This rule is non-negotiable and applies whether the user selected two features (Studio + one agent) or everything.

**User-order rule (among #2, #3, and #4 only).** The Fulfiller Agent (#2), Employee Agent (#3), and Specialized Agents for Employee (#4) are independent of each other — none depends on the others. If more than one is selected, run them in the order the user listed them (default 2 → 3 → 4 when unspecified). This rule applies **only** to the ordering among #2, #3, and #4; it never overrides the Studio-first rule above.

| # | Feature | Stage | Child Skill |
|---|---------|-------|-------------|
| 1 | Agentforce Studio enablement (Foundation for all agents) | 1 | `service-itsm-agentic-setup-agentforce-studio-configure` |
| 2 | IT Service Fulfiller Agent | 2 | `service-itsm-agentic-setup-fulfiller-agent-configure` |
| 3 | IT Service Employee Agent | 2 | `service-itsm-agentic-setup-employee-agent-configure` |
| 4 | Specialized Agents for Employee | 2 | `service-itsm-agentic-setup-employee-agent-configure` |

**How #3 and #4 relate.** Both #3 and #4 delegate to the same child skill,
`service-itsm-agentic-setup-employee-agent-configure` — the difference is which template it installs.
#3 (IT Service Employee Agent) installs the **broad, ready-to-go** employee agent, which is the child
skill's default whenever no specialization is named. #4 (Specialized Agents for Employee) installs a
**specialized** employee agent instead — but the child skill only takes the specialized path when it
is handed the name of a specialized template; handed nothing, it silently falls back to the broad
agent, which would just re-create #3. So when the user selects #4, **ask which specialized employee
agent they want before delegating** — offer common examples (Password Manager, Certificate Management,
Onboarding, Hardware Request) and note that more are available; the child skill holds the full catalog
and will disambiguate a partial or ambiguous name. Then delegate to the child skill **with that named
specialization**, and it will pin the matching template (the chosen template names the agent it
creates). **Never delegate #4 without a named specialization** — that is the one case that produces a
duplicate broad agent. The specialized templates themselves are turned on in Stage 1 (Agentforce
Studio enablement); #4 is where an agent is built and activated from one of them.

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

## Setup Stages & Recommended Order

Setup runs in **two sequential stages**. Stage 1 (enable platform features) must complete before
Stage 2 (install & activate agent templates).

```text
Stage 1 — Foundation: enable platform features
  1. Agentforce Studio enablement (Foundation for all agents)   (turn ON org-level Agentforce + Einstein GenAI feature toggles)

Stage 2 — Agent templates: install & activate   (only after Stage 1)
  2. IT Service Fulfiller Agent          (install from template, commit, and activate the agent)
  3. IT Service Employee Agent           (install the broad employee agent from its template and activate it)
  4. Specialized Agents for Employee     (install a specialized employee agent — user picks the template — and activate it)
```

Stage 1 (Agentforce Studio enablement) is the **foundation**: it turns on the org-level Agentforce
and Einstein GenAI feature toggles that all the agents are **built on top of** (including the
specialized employee templates). Enable it first — attempting to install or activate any agent
before this foundation is enabled will fail. The three Stage 2 items (Fulfiller, Employee, and
Specialized Agents for Employee) are independent siblings (none depends on the others) — they can be
selected together and installed in any order once Stage 1 is done. Specialized Agents for Employee
is listed right after the IT Service Employee Agent because both build employee agents from the same
child skill: #3 the broad default, #4 a specialized template the user chooses.

---

## Rules

- ALWAYS show "(via service-itsm-agentic-setup-agentforce-coordinate)" in the setup header
- ALWAYS present the feature menu before doing anything — do not assume which feature the user wants
- ALWAYS present the feature menu as a multi-select — accept a set of one or more features in a single interaction
- NEVER set up a feature without the user selecting it. (Explicit selection ensures the user confirms intent and avoids partial configurations if they cancel mid-flow; use the sequential-confirmation loop in the "set up everything" rule for bulk requests.)
- NEVER show features that do not have a working child skill
- If the user says "set up everything" or "all", walk through each available feature sequentially in the recommended order, confirming between each step
- Track progress across the conversation — do not re-present completed features as "Not done"
- Specialized Agents for Employee (#4) is **re-selectable** — each run builds a *different* specialized employee agent from a template the user picks. Mark the agent just built as `Done`, but keep #4 available to run again for additional specialized agents; do not treat a completed #4 as permanently finished the way #1–#3 are. If the user picks #4 again, ask which specialized template to use next
- NEVER advance to the next feature in the queue if the current one failed or only partially
  succeeded — stop and surface the failure in plain language instead
- If Agentforce Studio enablement reports the org lacks the Agentforce license (`accessCheck`), STOP
  the whole flow — this is a license/edition requirement no API can grant, and neither the
  Fulfiller nor the Employee Agent can succeed without it
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
- [ ] Each feature row's `Description` matches the Salesforce Setup → Agentforce for IT Service page wording (Fulfiller and Employee agent-template descriptions verbatim, not paraphrased), the three Stage 2 rows each end with a short `Setup:` install line, and the `AskUserQuestion` option descriptions carry the same text
- [ ] The Specialized Agents for Employee row is present as a Stage 2 item shown right after the IT Service Employee Agent, and #4 is never delegated to `service-itsm-agentic-setup-employee-agent-configure` without first asking the user which specialized template they want (handed no name, the child skill defaults to the broad agent and duplicates #3), and it carries its `Setup:` install line
- [ ] For a completion summary, the header line and closing line are chosen by the rubric in `examples/output-templates.md` (all `Done` → *Complete*; any `Not done`/`In progress` → *Finished*)
- [ ] A feature is being configured only because the user explicitly selected it (or is being walked through sequentially with confirmation under an "all" / "everything" request)
- [ ] Studio enablement is verified done before delegating to any Stage 2 agent (Fulfiller, Employee, or Specialized Agents for Employee)
- [ ] The next action delegates to a child skill, never configures a feature inline
- [ ] No Salesforce record IDs appear in the output — human-readable names only

---

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Behavior steps 3, 5, and 6 — feature menu (two-stage, multi-select), post-feature progress, and completion summary text blocks |
| `scripts/verify-child-verdict.mjs` | Behavior step 5 — run via `Bash` (`node`) to check a child skill's verdict deterministically before advancing the queue |
