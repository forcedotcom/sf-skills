---
name: service-helpagent-coordinate
description: "Use to set up, configure, ground, or go live with a Salesforce Help Agent (an Agentforce Service Agent in Service Cloud) via a guided four-checkpoint flow. Use whenever a user says any of: set up / create / build / add a help agent, service agent, or support chat agent; add or embed a chat widget on a website or Experience Cloud / LWR site; put a help agent on a channel (web chat, voice, phone, help portal), even while rejecting web chat; ground a help agent on Salesforce Knowledge; or wants an AI to answer customer questions, manage support cases, and escalate to a human. The right skill even when the request names only one part, names a coming-soon channel this skill hard-stops on, or references help-agent-spec.md or the Agentforce Quick Setup wizard. DO NOT TRIGGER when authoring a brand-new agent with no Help Agent lineage (use agentforce-generate), configuring OAuth/ECAs (use integration-connectivity-connected-app-configure), or only deploying metadata (use platform-metadata-deploy)."
allowed-tools: Bash Read Write Edit Glob Grep WebFetch AskUserQuestion TodoWrite
metadata:
  version: "0.9"
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "dx-org-permission-set-assign"
    - "experience-lwr-site-generate"
    - "integration-connectivity-connected-app-configure"
    - "platform-metadata-deploy"
    - "service-digital-engagement-channel-configure"
    - "service-digital-engagement-deployment-configure"
    - "service-digital-engagement-messaging-site-integrate"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.139.6"
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
| `service-digital-engagement-channel-configure` | Messaging channel setup (uses `sessionHandlerAsa` for AgentforceServiceAgent routing — see `references/channel-web-chat.md`) |
| `service-digital-engagement-deployment-configure` | Embedded Service Deployment (targets `SiteType = 'ChatterNetworkPicasso'` sites — Aura won't work) |
| `experience-lwr-site-generate` | Experience Cloud (LWR) site — used when the org has no Live LWR site yet |
| `service-digital-engagement-messaging-site-integrate` | Widget placement + embed (Checkpoint 3.5 / 4) |

## Workflow

Read `assets/help-agent-spec.md` first — it is the authoritative flow and is intentionally kept small. **Do not pre-load the rest.** The heavy or conditional material is split into `references/` and read only when the flow reaches it (progressive disclosure — this is deliberate, to keep token usage low):

- **`references/agent-script.md`** — the ~500-line canonical agent script + placeholder list. Load it **only when you are ready to create the agent, after Checkpoint 2** — not during Checkpoints 1, 3, or 4.
- **`references/channel-web-chat.md`** — Web Chat provisioning detail. Load **only if the user picks Web Chat** at Checkpoint 3.
- **`references/channel-help-portal.md`** / **`references/channel-voice.md`** — coming-soon channel hard-stops. Load only if the user picks that channel.

Read the one channel file that matches the user's selection — never all three. Then run the interactive setup **without one-shotting**: walk the user through four checkpoints in order, waiting for a reply at each.

### Readiness check (silent, MANDATORY, do not reorder)
Order is load-bearing — running step 3 before step 2 fails with `PermissionSet not found: GenieUserEnhancedSecurity` because the Data Cloud permission sets do not exist in the org until Data Cloud itself is turned on:
1. Verify licenses + Einstein Agent User.
2. **Enable Data Cloud** — must complete before step 3 (permission sets don't exist until Data Cloud is on). If Data Cloud is not yet provisioned, offer the user the choice up front — enable and come back later, or wait through it now.
3. **CRITICAL — Assign the Data Cloud permission sets immediately after enablement.** Non-negotiable — skipping it ships an agent whose grounding returns empty `knowledgeSummary` at runtime even though ADL indexing reports SUCCESS.

Also verify the `SvcCopilotTmpl` and `EmployeeCopilot` namespaces are present. These are Salesforce out-of-the-box platform artifacts surfaced by `enableEinsteinGptPlatform: true` — not AppExchange managed packages — and will not appear in `sf package installed list`. Probe the namespace directly (e.g. `SELECT DeveloperName FROM Flow WHERE NamespacePrefix = 'SvcCopilotTmpl' LIMIT 1`).

### Recognizing where the user is entering
Do not assume every run starts at Checkpoint 1. Read the opening prompt and enter at the right checkpoint: if identity is already decided, start at Checkpoint 2 (grounding); if grounding is already in place, start at Checkpoint 3 (channel). Never restart at Checkpoint 1 or re-ask decisions the user already stated. If the opening prompt names **Voice / phone / telephony / IVR / Amazon Connect**, asks to "reach" or "contact" the agent "by phone" / "by call", or asks for it "as a Voice channel" (even phrased as a rejection of web chat), or **Help Portal** as the channel, take the coming-soon hard stop immediately: respond verbatim *"This feature is coming soon, please select Web Chat."* and re-present the channel options — do not run the checkpoints or write any Voice/Help-Portal plan.

### Checkpoint 1 — Meet Your Agent
Agent name, language, greeting, tone. Offer defaults.

### Checkpoint 2 — Give Your Agent Context (grounding)
Ask which knowledge source (Salesforce Knowledge / files / website sync). Grounding is **provisioning an Agentforce Data Library**, not designing a search — the agent's `knowledge:` block does the retrieval at runtime. This checkpoint MUST produce all five of:
1. **Delegate provisioning to `agentforce-generate`** — it owns ADL create/index/publish. Do not hand-roll data-library metadata.
2. **A dedicated, named library** — create `Help_Agent_Knowledge`. **Never wire the stock `All_Records_and_Fields_Default`** (it sits in `NOT_SCHEDULED` on trial or preloaded sample-data orgs and returns empty `knowledgeSummary` with no error).
3. **Category selection** — for Salesforce Knowledge, query the org's Data Category Groups and ask which categories to ground on. Do not assume "all."
4. **Wait-for-indexing gate** — poll and only proceed once `indexingStatus.status ∈ {COMPLETED, READY, SUCCESS}`. `NOT_SCHEDULED` is not success.
5. **Capture the `rag_feature_config_id`** (format `ARFPC_<libraryId>`) and wire it into the agent script's `knowledge:` block — never hardcode.

**Anti-rule:** never respond to a grounding request by designing a SOQL/SOSL/GraphQL/Apex search over Knowledge articles. Grounding is ADL provisioning; retrieval is the agent's job at runtime.

### Checkpoint 3 — Add to Channels
Web Chat / Help Portal / Voice. Create messaging channel + Embedded Service Deployment; locate the target site via a **query-first pattern**:

```sql
SELECT Id, Name, UrlPathPrefix, SiteType, Status
FROM Site
WHERE SiteType = 'ChatterNetworkPicasso' AND Status = 'Live'
```

Only ever present or target `ChatterNetworkPicasso` (LWR) sites — never Aura (`ChatterNetwork`). Resolve the site **in the same turn**, do not defer:
- **Zero Live LWR sites** → create one via `experience-lwr-site-generate` (recommend the Help Center template).
- **Exactly one** → confirm it with the user before using (an existing site may serve a different audience); do not silently adopt it.
- **Multiple** → in the SAME turn, show the executed SOQL, enumerate the results as a table (`Name | UrlPathPrefix | Id`), state plainly "no site is created or modified until you choose," then ask which one to target (include a "create a new site instead" option). Do not answer "I'll query and get back to you" — run the query and present results now.

Do not filter by hardcoded name or URL path prefix — the correct site depends on the customer's org.

**Coming-soon channels are hard stops.** If the user selects **Help Portal** or **Voice**, respond verbatim *"This feature is coming soon, please select Web Chat."*, re-present the channel options, and wait. Never write a provisioning plan, phone number, portal site, or "planning-only" scaffold for these channels — even adjacent objects produce broken half-configurations. See `references/channel-voice.md` / `references/channel-help-portal.md`.

### Checkpoint 3.5 — Silent pre-flight (INTERNAL — never announce)
Run silently; surface output only on failure. Every check must pass before Checkpoint 4:
1. Data Cloud access in place for running user **and** Einstein Agent User (defer to `agentforce-generate`).
2. ADL is Activated **and** grounded — run a canary retrieval with the captured `rag_feature_config_id`; if empty despite SUCCESS, surface the **Known manual step** (Data Space scope on the permission set) verbatim, wait for confirmation, re-run.
3. Messaging channel is **Active** (assert status; activation is `service-digital-engagement-channel-configure`'s job, not the site-integrate skill's), **and** the widget is actually placed — independently re-read the deployed guest-layout JSON for the `experience_messaging:embeddedMessaging` node rather than trusting the site-integrate skill's 200-only signal; inject if missing.

### Checkpoint 4 — Review & Go Live
Embed (LWR + Aura), then complete four explicit go-live steps: (a) wire the **Escalation Flow** to the agent (reuse `Help_Agent_Escalation_Flow` if it already exists — do not create a duplicate); (b) confirm the **Messaging Channel is Active** in Setup → Messaging Settings; (c) **Publish the Embedded Service Deployment** in Setup → Embedded Service Deployments; (d) offer to test together. An unpublished deployment or an inactive channel silently ships a dead widget.

## Rules / Constraints

| Rule | Rationale |
|---|---|
| Never one-shot the setup | It is a guided conversation; wait for user input at each checkpoint |
| Never skip or reorder the readiness steps | Permission sets don't exist before Data Cloud enablement — you'll see `PermissionSet not found: GenieUserEnhancedSecurity` |
| Never advance past 3.5 with empty ADL retrieval | Ships a silently-broken agent |
| Never hardcode a site name or URL path prefix | The correct target LWR site depends on the customer's org — query first, then decide |
| Never assume `SvcCopilotTmpl` / `EmployeeCopilot` are packages | They are OOB namespaces surfaced by `enableEinsteinGptPlatform`; probe the namespace directly |
| Never wire an Embedded Service Deployment to an Aura (`ChatterNetwork`) site | It must target `ChatterNetworkPicasso` (LWR) or the widget will fail silently |
| Create the Embedded Service Deployment as V2 via the Connect API, never bare Metadata deploy — and embed the V2 ESD via the `experience_messaging:embeddedMessaging` LWR component | Metadata API defaults to legacy V1 (`WebV1`, *"Web (v1)"* in Setup) which breaks Enhanced Web Chat; create via Connect API on v67.0+ with `clientVersion: WebV2`. The customer widget mounts via the LWR component keyed on `deploymentName` (not a bootstrap `<script>`). Full six-attribute shape, the Tooling-API patch path, and guest-browser verification are in `references/channel-web-chat.md` — do NOT verify with <!-- skill-validate: ignore-start -->`curl \| grep`<!-- skill-validate: ignore-end --> |
| Always create a dedicated ADL for the Help Agent — never wire the stock `All_Records_and_Fields_Default` library | On trial or preloaded sample-data orgs the stock library is stuck in `NOT_SCHEDULED` and never indexes; wiring the agent to it produces empty `knowledgeSummary` at runtime with no visible error. Create `Help_Agent_Knowledge` at Checkpoint 2 and wait for `indexingStatus ∈ {COMPLETED, READY, SUCCESS}` before wiring |
| Never leave Checkpoint 4 without publishing the Embedded Service Deployment and activating the channel | Both are required for the widget to actually serve on the site. If the ESD was created via the Connect API `deployment/setup` call, it is already published — verify *"Published on:"* is stamped (not empty) and the title has no `(v1)` suffix |
| Web Chat is the only buildable channel; Voice and Help Portal are hard stops | Coming-soon channels have no supporting skill — respond verbatim *"This feature is coming soon, please select Web Chat."* and re-present options; never scaffold. For Web Chat, always run the post-deploy assertion (re-fetch the MessagingChannel, assert `embeddedConfig.authMode`; default `UnAuth`) — a wrong choice silently ships a widget that won't render for guests. The report names `authMode` as a bare value (`authMode: UnAuth`); do not narrate the rationale or the assertion in the report. Never emit a legacy `esw.min.js` / Live Agent V1 snippet |

## Output Expectations

The one deliverable is a single `report.md`: a **status report of what was decided and done**, not a design doc, plan, or architecture write-up. Two rules govern quality:

1. **Report concrete outcomes, never intentions.** Write what *is* — the decided value, the created resource, the resolved ID — not what you *would* or *plan to* do. If a step could not run to completion because this is a non-interactive run, **decide the sensible default, state it as the decision, and report it as such** — do not stall on "awaiting confirmation," "to be resolved," "pending user input," or "please provide…". Hedging language ("will create", "to be executed", "once confirmed") reads as an unfinished plan and is scored as incomplete. Name the agent, the locale, the grounding source, `authMode`, the ADL name, the `rag_feature_config_id`, the site `UrlPathPrefix`, the ESD publish state — as settled facts.
2. **No padding, no scaffolding prose.** No preamble, no design-doc sections, no restating the prompt. Dense, declarative lines only.

**Before writing, choose the report shape by what the run actually did. There are three:**
- **A coming-soon stop** — the run hard-stopped on a coming-soon channel (Voice / Help Portal).
- **A settled-facts report** — the flow *executed a step*: the user directed a concrete action ("set up the grounding", "put it on <named site>") and every input was supplied or has a sensible skill-owned default. Report what was decided and done.
- **A guided-decision report** — the flow is at a *decision the user owns*: an opening request with no agent details yet ("set up a help agent", "add a chat widget"), **or** a checkpoint surfacing multiple real alternatives the skill must not invent (e.g. several Live LWR sites). Presenting the checkpoint's questions/options *is* the deliverable; stay draft-first.

Use the settled-facts report, not the guided-decision one, when the missing value is a mechanical default the skill can just pick (data category → org default) — decide it and report it done. Use the guided-decision report only when the choice genuinely belongs to the user (identity at an opener; which of several existing sites). The guided-decision report is **not** an escape hatch for hedging on an execute request.

**Coming-soon stop — the flow hard-stopped on a coming-soon channel (Voice / Help Portal).** Short and fixed — the four H2 sections below, nothing more. Do NOT describe how Voice/Portal would be built, do NOT list architecture options, telephony, IVR, Amazon Connect, or "planning-only" steps — that content is an automatic fail. Write exactly:

```markdown
# Help Agent Setup Report

## Blocking Issue
<Channel> is a coming-soon channel with no supported setup path. Response given verbatim: "This feature is coming soon, please select Web Chat."

## Channel Options
- Web Chat — supported; the only buildable channel.
- Voice / phone — coming soon, not available.
- Help Portal — coming soon, not available.

## No Provisioning Performed
No Voice/telephony channel, phone number, messaging channel, or Embedded Service Deployment was created or configured. No supported channel was selected, so the flow did not proceed past the channel gate.

## Next Action
Re-run and select Web Chat as the channel.
```

**Settled-facts report — the flow ran (completed, or blocked on something other than a coming-soon channel).** Start with the exact H1 `# Help Agent Setup Report`, then the two tables and two short sections below, in order. Every cell is a **concrete, decided value** — a bare value, not a sentence. Keep prose out.

**Report DECISIONS as settled facts, never placeholders or intentions.** This is a non-interactive run: you do not get to defer. Do NOT emit "to be captured", "not yet reached", "flow is paused", "awaiting", "once confirmed", or "will create". For a value the flow **decides** (agent name, locale, tone, ADL name, `authMode`, data category), state the concrete decision as done — a cell with nothing decided gets `None`. For an **opaque ID the run generates** (the `rag_feature_config_id`, a Salesforce record Id, a site's URL path prefix), report the **actual value produced this run** — never invent a plausible-looking one and never copy an ID from this template; if the run genuinely did not produce it, name that in Blocking Issues rather than fabricating. Hedging is scored as incomplete; fabricated IDs are scored as inaccurate. Include every value below and nothing else.

**Scope the report to the checkpoint(s) the request targeted — do not narrate checkpoints the run never entered.** When the user directs a single checkpoint ("set up the grounding", "ground it on Knowledge" → Checkpoint 2 only), the report centers on that checkpoint. Fill its row with settled facts; give each checkpoint the run did **not** reach a bare `Not started` in its Decision cell — no plan, no "pending", no "not yet reached", no downstream detail. Do **not** manufacture a `Blocking Issues` entry or a `Next Action` about a later checkpoint you were never asked to run: if the targeted checkpoint completed, `Blocking Issues` is `None` and `Next Action` is the single next checkpoint by name (e.g. "Checkpoint 3 (channel) when you're ready"). A report that sprawls into unrequested checkpoints and hedges there is scored as incomplete even when the targeted checkpoint is perfect.

**When the request centers on one decision, carry that decision's reasoning — not a bare value.** Some requests are about a single load-bearing choice: *why the readiness steps run in a specific order*, or *which `authMode` to pick and why*. For these, the targeted cell (or a short `## <Topic>` section right after the tables) must state the **decision, its rationale, and the concrete failure it avoids** — because that reasoning is the deliverable, not scaffolding:
- **Readiness ordering** — give the ordered sequence (licenses / Einstein Agent User → **enable Data Cloud** → **assign Data Cloud permission sets**), say *why* the order is load-bearing (the permission sets do not exist until Data Cloud is enabled — assigning first fails with `PermissionSet not found: GenieUserEnhancedSecurity`), and warn that skipping the assignment yields empty runtime grounding even when ADL indexing reports SUCCESS. Do not compress this to "perm sets assigned". If Data Cloud is not yet enabled on this org, the Readiness row must say so — never assert "Data Cloud enabled; perm sets assigned" while `Blocking Issues` says it isn't; that contradiction is scored as inaccurate.
- **`authMode` choice** — name the value (`UnAuth` for an anonymous-or-mixed audience), state the rationale (`UnAuth` allows **both** guests and authenticated upgrades via `identityToken`; `Auth` is authenticated-only and silently breaks the guest widget and the Setup "Test Enhanced Web Chat" page), confirm the audience it was chosen for, and state the assertion as a settled part of the flow — "the deployed MessagingChannel is re-fetched and `embeddedConfig.authMode = UnAuth` is asserted" — **present tense, not "will be re-fetched"**. Do not compress this to "authMode UnAuth". The `authMode` decision is complete once chosen: do **not** frame it as pending ("to be confirmed"), and do **not** manufacture a `Blocking Issues` entry or `Next Action` about the *adjacent* site-resolution step — a scoped `authMode` request is not blocked on the LWR site. If nothing stopped the scoped decision, `Blocking Issues` is `None`.

The `‹…›` slots below mark where **this run's** real values go — replace each slot, never emit the slot text itself:

```markdown
# Help Agent Setup Report

## Setup Summary
| Field | Value |
|---|---|
| Readiness | Data Cloud enabled; perm sets assigned (GenieUserEnhancedSecurity, GenieAnalytics, DataSpacePermSet); Einstein Agent User assigned |
| Failure mode guarded | Stock NOT_SCHEDULED ADL → empty knowledgeSummary; guarded via dedicated ADL, indexing gated to COMPLETED |
| Delegation | agentforce-generate → agent + ADL; dx-org-permission-set-assign → Data Cloud perms; service-digital-engagement-* → channel + ESD |

## Checkpoint Outcomes
| # | Checkpoint | Decision |
|---|---|---|
| 1 | Identity | ‹agent name› (‹DeveloperName›), ‹locale›, ‹tone› |
| 2 | Grounding | Salesforce Knowledge via agentforce-generate; dedicated ADL ‹library name› (stock All_Records_and_Fields_Default not wired); indexing gated to COMPLETED before wiring; rag_feature_config_id ‹ARFPC_ id from this run's adl publish› captured |
| 3 | Channel | Web Chat; authMode ‹UnAuth or Auth›; site ‹target site UrlPathPrefix›; ESD HelpChat WebV2 — *or* `Not started` if the run never entered this checkpoint |
| 4 | Go-live | ESD Published; channel Active; escalation flow wired — *or* `Not started` |

## Blocking Issues
‹the one thing that actually stopped the flow — one line — or `None`›

## Next Action
One line — the single next step for the user.
```

Non-slot values above (Data Cloud, perm-set names, `HelpChat WebV2`, delegation targets) are the skill's canonical defaults — reproduce them as-is. Fill the `‹…›` slots from this run (including `authMode`, which is decided per run from the Step B choice — do not default it in the report). **Any checkpoint the run did not reach gets a bare `Not started` — not a plan, forecast, or "pending" note.** For a request scoped to one checkpoint (e.g. Checkpoint 2 grounding), only that row carries settled facts; rows 3 and 4 read `Not started`, `Blocking Issues` is `None`, and `Next Action` names the next checkpoint (e.g. "Checkpoint 3 (channel) when you're ready").

**Blocked run?** `Blocking Issues` is the one sanctioned place to state a real blocker — one honest line there (e.g. "multiple Live LWR sites — asked user to choose"; "Knowledge data category not specified — chose the org's default group") is **required and is not hedging**. It records what stopped a checkpoint the run *actually entered* — never a checkpoint the request never targeted (a scoped Checkpoint-2 run is not "blocked" on Checkpoint 3). Keep the checkpoint cells decisive for what *was* settled; put the single unresolved thing here. What is scored as incomplete is hedging *inside the decision cells* ("to be captured", "not yet", "pending") — not a clear one-line blocker in this section.

**Guided-decision report — a decision the user owns.** Here the deliverable is *the decision point itself*, presented cleanly. This is not hedging: at an opener or a genuine fork, asking with sensible defaults is the correct, complete response. Do **not** provision, deploy, or fabricate the value the user still owns. Orient, present the current checkpoint's choices with defaults, sketch what the remaining checkpoints will cover, and confirm nothing is live yet. Use exactly these sections:

```markdown
# Help Agent Setup Report

## Guided Setup
Help Agent setup runs as four checkpoints: identity → grounding → channel → go-live. Nothing is created, deployed, or published until you confirm at each step.

## Current Checkpoint
Checkpoint ‹n — name›. This agent will ‹map the user's stated needs to the design in one line: knowledge-grounded Q&A from Salesforce Knowledge, support-case create/update, and escalation to a live human when needed›, delivered as ‹the channel the user named, e.g. a Web Chat widget on their site›.

## Decisions Needed
- ‹Question 1 — offered default› (e.g. Agent name — `Help Agent`, API name `Help_Agent`)
- ‹Question 2 — offered default› (e.g. Language — `en_US`)
- ‹Question 3 — offered default› (e.g. Greeting, Tone)
- ‹…the real choices for THIS checkpoint only; for a multi-option fork, list the actual alternatives found (e.g. each Live LWR site by Name + UrlPathPrefix) and never pick for the user›

## Checkpoint Roadmap
- Readiness (silent, before provisioning): confirm licenses / Einstein Agent User → enable Data Cloud → assign the Data Cloud permission sets, in that order.
- 2 Grounding: connect Salesforce Knowledge via a dedicated Agentforce Data Library, indexing gated to COMPLETED.
- 3 Channel: deploy the chosen channel + Embedded Service Deployment; confirm `authMode` from who will be chatting.
- 4 Go-live: embed, publish, and verify with a live round-trip — only after you confirm.

## Next Action
Reply with your choices (or accept the defaults) and I'll proceed to the next checkpoint. Nothing is created, grounded, embedded, or published until you confirm at each step.
```

Fill every `‹…›` from this run's context. Keep to these five sections — the Roadmap names what later checkpoints will do (it is not a settled-fact table and must not claim any of it is done); no provisioning tables, no settled-fact cells for steps not yet reached.

**Never include** (each is a scored failure): a preamble restating the prompt or the request; "End of report." trailers; decorative `---` / `===` rules; `Scope`, `Assumptions`, `Out-of-Scope`, `Architecture`, `Options Considered`, `Next Steps`, `Steps:`, or `Outcome Gate:` sections; the checkpoints re-listed as questions; the agent script or reference-file contents pasted inline; emoji; marketing adjectives ("seamless", "robust", "powerful", "comprehensive").

## Reference File Index

| File | When to read |
|---|---|
| `assets/help-agent-spec.md` | Always (first) — the canonical flow; small by design. Points to the files below |
| `references/agent-script.md` | At agent creation only (after Checkpoint 2) — the canonical agent script + placeholders |
| `references/channel-web-chat.md` | Only if the user selects Web Chat at Checkpoint 3 |
| `references/channel-help-portal.md` | Only if the user selects Help Portal (coming-soon hard stop) |
| `references/channel-voice.md` | Only if the user selects Voice (coming-soon hard stop) |
