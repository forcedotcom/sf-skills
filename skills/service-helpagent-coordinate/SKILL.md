---
name: service-helpagent-coordinate
description: "Use to set up, configure, ground, or go live with a Salesforce Help Agent (an Agentforce Service Agent in Service Cloud) via a guided four-checkpoint flow. Use whenever a user says any of: set up / create / build / add a help agent, service agent, or support chat agent; add or embed a chat widget on a website or Experience Cloud / LWR site; put a help agent on a channel (web chat, voice, phone, help portal); ground a help agent on Salesforce Knowledge; or wants an AI to answer customer questions, manage support cases, and escalate to a human. The right skill even when the request names only one part or references help-agent-spec.md or the Agentforce Quick Setup wizard. DO NOT TRIGGER when authoring a brand-new agent with no Help Agent lineage (use agentforce-generate), configuring OAuth/ECAs (use integration-connectivity-connected-app-configure), or only deploying metadata (use platform-metadata-deploy)."
allowed-tools: Bash Read Write Edit Glob Grep WebFetch AskUserQuestion TodoWrite
metadata:
  version: "0.9"
  domains: ["Service", "Agentforce", "Experience"]
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "dx-org-permission-set-assign"
    - "experience-lwr-site-generate"
    - "integration-connectivity-connected-app-configure"
    - "platform-metadata-deploy"
    - "service-agentforce-channel-configure"
    - "service-concierge-portal-generate"
    - "service-digital-engagement-channel-configure"
    - "service-digital-engagement-deployment-configure"
    - "service-digital-engagement-messaging-site-integrate"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.139.6"
    - tool: ["python3"]
      semver: ">=3.8"
---

# service-helpagent-coordinate: Service Cloud Help Agent, guided setup

Use this skill to stand up a **Service Cloud Help Agent** (an Agentforce Service Agent) on a Salesforce org from Claude Code, following the same guided flow as the Help Agent Quick Setup wizard. This is a **coordinate** skill: it orchestrates existing skills against a canonical spec — it does **not** author a new agent primitive.

## Why this skill exists

Salesforce's official Help Agent template-creation API is not yet shipped. Without it, Claude has no built-in concept of "Help Agent" and would otherwise generate a generic agent. `assets/help-agent-spec.md` substitutes for the missing API: its agent script is the canonical template the eventual Quick Start UI will produce. Treat the spec as source of truth for the agent's lineage (topics, actions, instructions).

## Scope

**In scope:**
- Guided, four-checkpoint Help Agent setup (identity → grounding → channel → go-live)
- Knowledge grounding via Agentforce Data Library (ADL)
- Web Chat / Help Portal channel setup and Experience Cloud site embed
- Readiness checks (licenses, Einstein Agent User, Data Cloud permission sets)

**Out of scope — delegate elsewhere:**
- OAuth / External Client App setup → [integration-connectivity-connected-app-configure](../integration-connectivity-connected-app-configure/SKILL.md)
- Raw agent authoring with no Help Agent lineage → `agentforce-generate`
- Metadata deploy/retrieve → `platform-metadata-deploy`

## Prerequisites

- Claude Code + Salesforce CLI installed and an authenticated org (see repo `README.md`)
- MCP servers registered: `salesforce-api-context`, `metadata-experts`, `sobject-reads`
- Salesforce Skills installed into `.agents/skills/` (or `.claude/skills/`)
- **A Salesforce org with the required features enabled (or enable-able via metadata):** Agentforce, Einstein Generative AI, Knowledge, Experience Cloud, and Data Cloud. Any org shape that meets this bar works — production, sandbox, scratch, or Developer Edition. The readiness check in `assets/help-agent-spec.md` §4.0 detects each feature and enables what can be enabled; it stops with a clear message if a required capability is missing and cannot be turned on.

## Skills this coordinates

The spec feeds these existing skills — do **not** author a new Help Agent skill:

| Skill | Role |
|---|---|
| `agentforce-generate` | Agent authoring + ADL provisioning/grounding (see its `references/data-library-reference.md`, `references/org-setup-for-adl.md`) |
| `dx-org-permission-set-assign` | Data Cloud permission-set assignment |
| `service-digital-engagement-channel-configure` + `service-agentforce-channel-configure` | Deploy channel (Queue routing), then PATCH `SessionHandlerId` to bind agent (see `references/channel-web-chat.md`) |
| `service-digital-engagement-deployment-configure` | Embedded Service Deployment — supports both LWR (`ChatterNetworkPicasso`) and Aura (`ChatterNetwork`) sites |
| `experience-lwr-site-generate` | Experience Cloud (LWR) site — used when the org has no Live LWR site yet |
| `service-digital-engagement-messaging-site-integrate` | Widget placement + embed (Checkpoint 4) |

## Skills inventory pre-flight (advisory — never a hard stop)

This skill delegates to several sibling skills. Depending on the runtime, those dependencies resolve one of two ways: as directories under `.claude/skills/`, **or** through a runtime skill catalog that the harness resolves on demand (no local directory). An absent `.claude/skills/<name>` directory therefore does **not** prove a dependency is unavailable — it is normal when the catalog resolves skills at invocation time.

Run this check **once, silently, for your own awareness** — never as the run's first user-facing output:

```bash
for skill in agentforce-generate dx-org-permission-set-assign service-digital-engagement-channel-configure service-digital-engagement-deployment-configure experience-lwr-site-generate service-digital-engagement-messaging-site-integrate service-concierge-portal-generate service-agentforce-channel-configure; do
  [ -d ".claude/skills/$skill" ] && echo "OK: $skill" || echo "resolve-at-runtime: $skill"
done
```

**Do not stop, and do not open the run with a missing-dependency roll call.** Proceed with the checkpoints; delegate to each sibling skill only when the flow actually reaches it. If — and only if — a delegation step is actually reached and that specific skill cannot be resolved at that moment, surface *that one skill* by name at that point. Never front-load the full eight-skill inventory as the deliverable; it is not a decision the user owns and it is not the report.

---

## Workflow

Read `assets/help-agent-spec.md` first — it is the authoritative flow and is intentionally kept small. **Do not pre-load the rest.** The heavy or conditional material is split into `references/` and read only when the flow reaches it (progressive disclosure — this is deliberate, to keep token usage low):

- **`references/agent-script.md`** — the ~500-line canonical agent script + placeholder list. Load it **only when you are ready to create the agent, after Checkpoint 2** — not during Checkpoints 1, 3, or 4.
- **`references/channel-web-chat.md`** — Web Chat provisioning detail. Load **only if the user picks Web Chat** at Checkpoint 3.
- **`service-concierge-portal-generate`** — Help Portal / Agentforce Concierge portal deploy. **Delegate to this skill** if the user picks Help Portal at Checkpoint 3 — do not inline the portal runbook steps here. Pass `$ORG`, `$BOT_ID`, and `$BOT_DEV_NAME` as context so the skill skips its own entry-point questions.
- **`references/channel-voice.md`** — Voice channel wiring detail (existing numbers only). Load only if the user picks Voice.

Read the one channel file that matches the user's selection — never all three. Then run the interactive setup **without one-shotting**: walk the user through four checkpoints in order, waiting for a reply at each.

### Readiness check (silent, MANDATORY, do not reorder)
Order is load-bearing — running step 3 before step 2 fails with `PermissionSet not found: GenieUserEnhancedSecurity` because the Data Cloud permission sets do not exist in the org until Data Cloud itself is turned on:
1. **Verify PSL seat availability, then create a dedicated Einstein Agent User for this agent.** First confirm the three required PSLs have available seats:
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT MasterLabel, TotalLicenses, UsedLicenses FROM PermissionSetLicense WHERE DeveloperName IN ('AgentforceServiceAgentUserPsl', 'GenieDataPlatformStarterPsl', 'EinsteinGPTPromptTemplatesPsl')"
   ```
   For each, `UsedLicenses < TotalLicenses` must be true. If any PSL is at capacity, stop and surface which one is exhausted — the PSG assignment will fail and there is nothing the skill can do until a seat is freed or provisioned.

   If all three have capacity, create the user. Do not reuse any existing Einstein Agent User — each Help Agent gets its own. Username: `{agentDevName}_user@{orgId}.ext` (15-char org Id from `sf org display`). Email: `noreply@salesforce.com`. Profile: `Einstein Agent User` (query `SELECT Id FROM Profile WHERE Name = 'Einstein Agent User'` to get the ProfileId, then `sf data create record --sobject User`). If a user with exactly that username already exists, reuse it (idempotent). Then assign all four of the following **before publishing the agent**:
   - `AgentforceServiceAgentUserPsg` (Permission Set Group) — assigns three PSLs in one call: `Agentforce Service Agent User`, `Data Cloud`, and `Einstein Prompt Templates`. Use `sf org assign permsetgroup`.
   - `AgentforceServiceAgentSecureBase` (Permission Set) — required for all service agents. Use `sf org assign permset`.
   - `AgentforceKnowledgeUser` (Permission Set, `force` namespace) — required because the Help Agent uses the `knowledge:` block. Use `sf org assign permset`.
   - `{AgentName}_Access` (custom Permission Set) — created by `agentforce-generate` for agent-specific Apex/object access.

   Verify PSL assignments landed: `SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username = '{agentDevName}_user@{orgId}.ext'` — expect `AgentforceServiceAgentUser`, `DataCloud`, `EinsteinPromptTemplates`.

   **Capture the username** (`{agentDevName}_user@{orgId}.ext`) — it is the value for `<default_agent_user_placeholder>` in the agent script. The agent runs as this user at runtime.

   **Pre-publish gate — verify before every `sf agent publish authoring-bundle` call.** Skipping this causes a masked 401→404: SFAP returns HTTP 401 "User doesn't have access to agent" when the Einstein Agent User is missing `AgentforceServiceAgentUserPsg`, and jsforce's session-refresh retry silently converts that 401 to `ERROR_HTTP_404`. Verify all four assignments are present before invoking the CLI:

   ```bash
   AGENT_USER_ID=$(sf data query --target-org $ORG --json \
     --query "SELECT Id FROM User WHERE Username='{agentDevName}_user@{orgId}.ext'" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")

   # Must return exactly 1 row — if 0, assign before continuing
   sf data query --target-org $ORG --json \
     --query "SELECT PermissionSetGroup.DeveloperName FROM PermissionSetAssignment \
              WHERE AssigneeId='${AGENT_USER_ID}' \
              AND PermissionSetGroup.DeveloperName='AgentforceServiceAgentUserPsg'"

   # Must return 2 rows — if any are missing, assign before continuing
   sf data query --target-org $ORG --json \
     --query "SELECT PermissionSet.Name FROM PermissionSetAssignment \
              WHERE AssigneeId='${AGENT_USER_ID}' \
              AND PermissionSet.Name IN ('AgentforceServiceAgentSecureBase','AgentforceKnowledgeUser')"
   ```

   Do not call `sf agent publish authoring-bundle` until all four assignments return non-empty results.

2. **Enable Data Cloud** — must complete before step 3 (permission sets don't exist until Data Cloud is on). If Data Cloud is not yet provisioned, offer the user the choice up front — enable and come back later, or wait through it now.
3. **CRITICAL — Assign the Data Cloud permission sets immediately after enablement.** Non-negotiable — skipping it ships an agent whose grounding returns empty `knowledgeSummary` at runtime even though ADL indexing reports SUCCESS. The PSG assigned in step 1 covers this once Data Cloud is on.


### Recognizing where the user is entering

**Checkpoint 1 (agent identity) and Checkpoint 3 (channel) must always be confirmed with the user in the current conversation — never inferred from a previous session, a compacted summary, or skill arguments.** These are decisions the user owns; acting on stale context from a prior run will configure the wrong agent or the wrong channel.

If the user's opening message *in the current conversation turn* explicitly names the agent and/or channel (e.g. "set up Master Yoda on Web Chat"), accept those as the inputs and confirm them before proceeding. If not stated in the current turn, ask.

For the org alias: if the user has been working against a specific org in the current session, use that. Otherwise ask.

**Do not assume every run starts at Checkpoint 1.** Read the opening prompt and enter at the right checkpoint: identity decided → Checkpoint 2 (grounding); grounding done → Checkpoint 3 (channel). When the prompt explicitly names or implies a later checkpoint (e.g. "set up the grounding", "wire up the web chat channel") — and states or clearly implies prior checkpoints are already done — accept those prior checkpoints as established, enter scoped at the named checkpoint, and produce a settled-facts report for it. Do NOT force a full guided-identity re-confirmation, do NOT restart at Checkpoint 1, and do NOT demand in-conversation re-confirmation of prior decisions. Values the prompt supplies for the entered checkpoint (audience → `authMode`, named site, categories) are decided, not questions to re-ask.

If the opening prompt names **Voice / phone / telephony / IVR**, read `references/channel-voice.md` and follow it from the top of Checkpoint 3 as the Voice branch.

### Checkpoint 1 — Meet Your Agent
Ask for four things (offer these exact defaults so the guided-decision report can enumerate them without loading `assets/help-agent-spec.md`):
1. **Agent Name** — default `Help Agent` (DeveloperName `Help_Agent`).
2. **Language** — default `en_US`.
3. **Welcome Greeting** — default `"Hi, I'm {Agent Name}. How can I help you today?"`.
4. **Tone** — default `"calm, patient, friendly service agent — warm but professional, short sentences, never robotic."`

When the opener names Q&A / case management / human escalation, note explicitly that these map to the canonical four-subagent shape (Agent Router → General FAQ, Service Customer Verification, Case Management, Escalation) — do not invent a different design.

### Checkpoint 2 — Give Your Agent Context (grounding)
Ask which knowledge source (Salesforce Knowledge / files / website sync). Grounding is **provisioning an Agentforce Data Library**, not designing a search — the agent's `knowledge:` block does the retrieval at runtime. This checkpoint MUST produce all five of:
1. **Delegate provisioning to `agentforce-generate`** — it owns ADL create/index/publish. Do not hand-roll data-library metadata.
2. **A dedicated, named library** — create `Help_Agent_Knowledge`. **Never wire the stock `All_Records_and_Fields_Default`** (it sits in `NOT_SCHEDULED` on trial or preloaded sample-data orgs and returns empty `knowledgeSummary` with no error).
3. **Category selection** — for Salesforce Knowledge, query the org's Data Category Groups. Ask which categories to ground on **only in an interactive run**; for a non-interactive/scoped run, decide the sensible default (**the org's default Data Category Group**, or all groups if none is designated) and note the default explicitly in the settled-facts report's Blocking Issues line (e.g. "Knowledge data category not specified — chose the org's default group"). Do not stall the report asking.
4. **Wait-for-indexing gate** — poll and only proceed once `indexingStatus.status ∈ {COMPLETED, READY, SUCCESS}`. `NOT_SCHEDULED` is not success.
5. **Capture the `rag_feature_config_id`** (format `ARFPC_<libraryId>`) and wire it into the agent script's `knowledge:` block — never hardcode.

**Anti-rule:** never respond to a grounding request by designing a SOQL/SOSL/GraphQL/Apex search over Knowledge articles. Grounding is ADL provisioning; retrieval is the agent's job at runtime.

### Checkpoint 3 — Add to Channels

**First, always discover what already exists — never present only Web Chat / Help Portal / Voice as if they were the only options.** Follow `assets/help-agent-spec.md` §4.3 Step 1 in full: query every `MessagingChannel`, classify each by `<messagingChannelType>`, and surface every type present (WhatsApp, SMS, etc.), not just the three branches below. Skipping this discovery is the bug this section prevents.

Deploy new channels with Queue routing (`service-digital-engagement-channel-configure`), then delegate agent wiring to `service-agentforce-channel-configure`. Branch by channel type:

- **Web Chat** → read `references/channel-web-chat.md`. Create messaging channel + Embedded Service Deployment. **Ask deployment target first, before querying anything**: "own (non-Salesforce) website" (recommended default — short-circuits to the embed-snippet path) or "a Salesforce Experience Cloud site". Only if the user picks Experience Cloud, run the **query-first pattern**:

  ```sql
  SELECT Id, Name, UrlPathPrefix, SiteType, Status
  FROM Site
  WHERE SiteType IN ('ChatterNetworkPicasso', 'ChatterNetwork') AND Status = 'Active'
  ```

  Both LWR (`ChatterNetworkPicasso`) and Aura (`ChatterNetwork`) sites support the `experience_messaging:embeddedMessaging` widget. Filter out `ESW_`-prefixed sites (internal ESD scaffolding, not real Experience Cloud sites). Resolve the site **in the same turn**, do not defer:
  - **Zero real sites** → create one via `experience-lwr-site-generate` (recommend the Help Center template), or fall back to "Deploy on my own website (get snippet)".
  - **Exactly one** → confirm it with the user before using (an existing site may serve a different audience); do not silently adopt it.
  - **Multiple** → in the SAME turn, show the executed SOQL, list results as a table (`Name | Type | UrlPathPrefix`), state "no site is created or modified until you choose," then ask which to target (offer "Create a new LWR site" and "Deploy on my own website"). Don't defer with "I'll get back to you" — present results now.

  Do not filter by hardcoded name or URL path prefix — the correct site depends on the customer's org.

- **Help Portal** → delegate to `service-concierge-portal-generate` (deploys an Agentforce Concierge experience on an LWR site). Pass the resolved `$ORG`, `$BOT_ID`, and `$BOT_DEV_NAME` so it can skip its entry-point questions.

- **Voice** → read `references/channel-voice.md` and follow it fully. Voice wires an existing `PstnVoice` MessagingChannel via `service-agentforce-channel-configure` Branch B — it does not provision a phone number.

- **Any other existing channel (WhatsApp, SMS, Facebook, Apple Business Chat, Line, Email-to-Case, Custom)** → no dedicated reference file. List channels of that type from discovery, let the user pick one (`"Add agent to: {MasterLabel}"`), and delegate straight to `service-agentforce-channel-configure` with the agent and channel DeveloperNames — it resolves the fallback queue and picks the routing branch itself (Branch A for Enhanced Chat/Messaging, Branch C for Email-to-Case). This skill only wires an agent to a channel that already exists; it never provisions the underlying 3rd-party/email infrastructure.

**After each channel branch completes, loop — ask if the user wants to add another channel.** Once a channel branch finishes (success or failure), present via `AskUserQuestion`:

- **Add another [same type] channel** — offer remaining unwired channels of that type; re-run the branch, skipping channels already wired this session.
- **Add a different channel type** — return to the top of Checkpoint 3 (re-query `MessagingChannel`, rebuild the type list, omit already-wired channels from the options).
- **Done — proceed to go-live** — exit the loop and advance to Checkpoint 4.

Track wired channels so they are not re-offered; the loop continues until the user selects "Done" or all channels are wired.

**Outbound escalation is wired here, immediately after inbound routing, not at Checkpoint 4.** For Web Chat/Voice branches, invoke `service-agentforce-channel-configure` Phase 3 (resolve escalation queue → create/reuse RoutingFlow → add connection block → republish) within the same delegated call as inbound routing. Deferring connection-block wiring to Checkpoint 4 duplicates Phase 3's atomic sequencing and forces an extra republish.

**When the opening prompt names two or more channels up front** (e.g. "add web chat, then also Voice — add both"), the prompt authorizes every named channel — treat them all as committed work. No fresh user reply is needed to advance from one named channel to the next; the up-front request *is* that authorization. Skip the between-branch `AskUserQuestion` for prompt-named channels, wire each in stated order, and fall back to the loop's `AskUserQuestion` only for channels the prompt did *not* name. The report must show every named channel wired — never only the first with the rest framed as an intention or "next step" (that scores as an incomplete loop even when the first channel is perfect). In the settled-facts Checkpoint 3 row (or a short trace below the tables), make all of these explicit, in order:
1. **First-channel completion** as a settled fact (channel type, `authMode` for Web Chat, resolved site/number, ESD state) — not "will then add".
2. **Authorization to continue**: the prompt named the next channel, so the flow advanced without a between-branch prompt. Never report a user reply that did not occur — claiming the user "continued after an AskUserQuestion" for a prompt-named channel fabricates an interaction and breaks the contract.
3. **Later-channel entry**: the flow re-entered Checkpoint 3 for each next named channel, each carried to its own settled outcome. Report a between-branch prompt's options and selection only if one genuinely ran (a channel the prompt did *not* name).
4. Only after every named channel is wired (or blocked with a one-line reason) does the flow reach go-live.

### Checkpoint 4 — Review & Go Live
Once the channel loop exits ("Done"), run two phases (Phase A below is what used to be a standalone "Checkpoint 3.5"):

**Phase A — Silent pre-flight (INTERNAL — never announce).** Run silently; surface output only on failure. Every check must pass before Phase B:
1. Data Cloud access in place for running user **and** Einstein Agent User (defer to `agentforce-generate`).
2. ADL is Activated **and** grounded — run a canary retrieval with the captured `rag_feature_config_id`; if empty despite SUCCESS, surface the **Known manual step** (Data Space scope on the permission set) verbatim, wait for confirmation, re-run.
3. Messaging channel is **Active** (assert; initial activation is the channel-configure skill's job, not the site-integrate skill's). This is the only place the flow checks or sets channel-active state — Phase B does not repeat it.

**Phase B — Explicit go-live steps (narrated to the user).** Verify the widget landed on the site (LWR + Aura) — placement already happened at Checkpoint 3 Step C.5 via `service-digital-engagement-messaging-site-integrate`; re-run injection only if verification fails. Then: (a) confirm the **Escalation Flow** is wired (configured at Checkpoint 3 via Phase 3 — verify, don't re-wire); (b) **Publish the Embedded Service Deployment** in Setup → Embedded Service Deployments; then offer to test together. An unpublished deployment silently ships a dead widget.

## Rules / Constraints

## Long-list presentation rules

`AskUserQuestion` is capped at 4 options. For discovered item lists (sites, channels, queues, ADLs) where the user picks **one**: **1–6 items** — paginate 3 per page, "Show more (N remaining)" as option 4, fixed options (Create new, etc.) on the final page only. **7+ items** — list names in plain text, ask the user to type their choice, validate case-insensitively, confirm before proceeding.

**Exception — multi-select lists (e.g. Checkpoint 3's channel-type picker) never paginate.** Pagination assumes single-select. For any multi-select list, once options exceed 4, skip straight to the plain-text list-and-type pattern regardless of count — see `assets/help-agent-spec.md` §4.3 Step 1.

| Rule | Rationale |
|---|---|
| Never one-shot the setup | It is a guided conversation; wait for user input at each checkpoint |
| Never skip or reorder the readiness steps | Permission sets don't exist before Data Cloud enablement — you'll see `PermissionSet not found: GenieUserEnhancedSecurity` |
| Never advance past Checkpoint 4 Phase A with empty ADL retrieval | Ships a silently-broken agent |
| Never hardcode a site name or URL path prefix | The correct target LWR site depends on the customer's org — query first, then decide |
| Never present ESW-prefixed sites as widget deployment targets | `ESW_*` sites are internal ESD endpoint scaffolding — filter them out in post-processing before presenting site options to the user |
| Create the Embedded Service Deployment as V2 via the Connect API, never bare Metadata deploy — and embed the V2 ESD via the `experience_messaging:embeddedMessaging` LWR component | Metadata API defaults to legacy V1 (`WebV1`, *"Web (v1)"* in Setup) which breaks Enhanced Web Chat; create via Connect API on v67.0+ with `clientVersion: WebV2`. The customer widget mounts via the LWR component keyed on `deploymentName`. Full six-attribute shape, the Tooling-API patch path, and guest-browser verification are in `references/channel-web-chat.md` |
| Always create a dedicated ADL for the Help Agent — never wire the stock `All_Records_and_Fields_Default` library | On trial or preloaded sample-data orgs the stock library is stuck in `NOT_SCHEDULED` and never indexes; wiring the agent to it produces empty `knowledgeSummary` at runtime with no visible error. Create `Help_Agent_Knowledge` at Checkpoint 2 and wait for `indexingStatus ∈ {COMPLETED, READY, SUCCESS}` before wiring |
| Never leave Checkpoint 4 without publishing the Embedded Service Deployment and activating the channel | Both are required for the widget to serve. If the ESD was created via the Connect API `deployment/setup` call it is already published — verify *"Published on:"* is stamped and the title has no `(v1)` suffix |
| Web Chat, Help Portal, and Voice have dedicated branches; any other existing channel type (WhatsApp, SMS, Facebook, Apple Business Chat, Line, Email-to-Case, Custom) is wired generically via `service-agentforce-channel-configure` | Discovery (§4.3 Step 1) must surface every channel type present — offering only the three dedicated branches when others exist is the bug this checkpoint guards against. For Web Chat, always run the post-deploy assertion (re-fetch the MessagingChannel, assert `embeddedConfig.authMode`; default `UnAuth`) — a wrong choice silently ships a widget that won't render for guests. Report `authMode` as a bare value (`authMode: UnAuth`); don't narrate the assertion. Never emit a legacy `esw.min.js` / Live Agent V1 snippet |

## Output Expectations

The one deliverable is a single `report.md`: a **status report of what was decided and done**, not a design doc. Two shapes exist — a **settled-facts report** when the flow executed a step (concrete decided values in tables), and a **guided-decision report** when the flow is at a decision the user owns (present the choices, do not fabricate). Never hedge inside decision cells ("to be captured", "pending", "will create"); never fabricate opaque IDs; never manufacture blockers on checkpoints the request did not target. Full templates, per-shape rules, one-decision reasoning callouts (readiness ordering, `authMode`), and the "never include" scored-failure list live in **`references/output-report-format.md`** — read it before writing the report.


## Reference File Index

| File | When to read |
|---|---|
| `assets/help-agent-spec.md` | Always (first) — the canonical flow; small by design. Points to the files below |
| `references/agent-script.md` | At agent creation only (after Checkpoint 2) — the canonical agent script + placeholders |
| `references/channel-web-chat.md` | Only if the user selects Web Chat at Checkpoint 3 |
| `service-concierge-portal-generate` (external skill) | Only if the user selects Help Portal at Checkpoint 3 — delegate, do not inline |
| `references/channel-voice.md` | Only if the user selects Voice (wires an existing `PstnVoice` channel; no number provisioning) |
| `references/output-report-format.md` | Right before writing the final `report.md` — the two report shapes, templates, and scored-failure list |
