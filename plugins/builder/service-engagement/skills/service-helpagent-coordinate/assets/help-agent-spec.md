# Help Agent — Setup Spec

> **Who this is for.** You're a Salesforce admin standing up the Help Agent. You will *run* the setup flow (a guided, checkpoint-by-checkpoint conversation) and you need to *understand* the agent that gets built — its topics, subagents, and what it's allowed to do — so you can review it in Agentforce Builder and explain it to stakeholders. You are **not** hand-authoring the `.agent` YAML: the skills generate that from the canonical script in [`references/agent-script.md`](../references/agent-script.md). Read that script for comprehension when you reach agent creation (after Checkpoint 2), not to edit it block-by-block.

> **How to read this file.** §1–§2 tell you what you're building and its shape at a glance. §3 is the global voice/behavior. §4 is the execution flow you'll walk the user through — readiness, then four checkpoints. Reference details (placeholders, package deps, deployment target) live in §5–§6 right where the flow needs them or as a short appendix. §7 points to the full canonical agent script (`references/agent-script.md`), which you load only at agent-creation time. **Progressive disclosure:** the large or conditional pieces — the agent script and each channel branch — live in `references/` and are read only when the flow reaches them, so this file stays small in context.

---

## 1. What this is and why it exists

Create a Salesforce Agentforce Service Agent ("help agent") in the connected org with the shape and behavior described in the agent script (§7), then expose it on a customer-facing Experience Cloud site via an embedded chat widget.

This file is the spec for the Help Agent we're building. The accompanying Claude Code prompt will simply reference this file ("create an agent out of the spec I have created here in `assets/help-agent-spec.md`"). Use the skills under `.claude/skills/` — do **not** author a new Help Agent skill. The relevant skills in this repo are `agentforce-adlc:agentforce-generate` (agent authoring + Agentforce Data Library provisioning/grounding, in its `references/data-library-reference.md` and `references/org-setup-for-adl.md`), `dx-org-permission-set-assign`, `service-digital-engagement-channel-configure` (initial Queue-routed channel setup and activation), `service-agentforce-channel-configure` (replaces the initial routing with the agent binding — fallback queue + `sessionHandlerAsa`), `service-digital-engagement-deployment-configure`, `experience-lwr-site-generate`, and `service-digital-engagement-messaging-site-integrate` (widget placement + embed, used in Checkpoint 4). The spec is custom data feeding standard skills, not a new skill itself.

**Why the spec, not an API.** Salesforce's official Help Agent template-creation API is not yet shipped. Without that API, you (Claude) have no built-in concept of "Help Agent" and would otherwise generate a generic agent. This file substitutes for the missing API: the agent script in §7 is the canonical template that the eventual Quick Start UI will produce. Treat it as the source-of-truth shape — the agent you build should have the same lineage (topics, actions, instructions) as the agent that template would create.

**In scope:**

- Knowledge-grounded Q&A using Salesforce Knowledge, uploaded files (file-based Agentforce Data Library), or website-sourced content.
- Case management — create new cases on behalf of the customer and report on existing cases.

## 2. Agent shape at a glance

The agent is one front-door **router** that hands off to **four subagents**. In plain language:

- **Agent Router** *(front door)* — greets the customer, reads their intent, and routes to the right subagent. It's the only entry point; there is no separate topic selector.
- **Service Customer Verification** — confirms who the customer is (via an emailed verification code) before anything sensitive happens. Anything touching orders, cases, account details, or personal data goes through here first. Once verified in a session, the customer isn't re-verified.
- **General FAQ** — answers company/product/policy questions by searching Knowledge articles (grounded on the Agentforce Data Library). If the customer actually wants a case created, or if the knowledge search itself fails, it routes to verification → case management instead of dead-ending.
- **Case Management** — creates new support cases, looks up existing cases, and adds comments — all for a *verified* customer.
- **Escalation** — hands off to a live human agent when asked; if no human is available, it falls back to creating a support case.

Routing rules the sysadmin should know:

- Verification gates the sensitive paths. `isVerified` is the switch: while `False`, the router sends sensitive/case work to **Verification**; once `True`, straight to **Case Management**.
- **FAQ** and **Escalation** are reachable without verification (answering a policy question or asking for a human doesn't require identity).
- Both **FAQ** and **Escalation** have the same safety net: a failed action (empty knowledge search, no human available) becomes an *offer to create a case*, not a dead end.

Each of these maps to a block in §7 — the router is `start_agent agent_router`, and the four subagents are `subagent ServiceCustomerVerification / GeneralFAQ / CaseManagement / Escalation`. The agent script defines all of them; build the agent as-written and don't surgically drop topics — the script is the source of truth for shape.

---

## 3. Global behavioral rules (apply throughout the flow)

**Persona for all user-facing prompts.** When you ask the user anything during this setup, speak as a **calm, patient, friendly service agent** — first-person, warm, never robotic. Short sentences. One question (or one tight group of related questions) per checkpoint. Acknowledge each answer before moving on ("Great, got it." / "Perfect — moving on."). Never dump a wall of options without context. This is a guided conversation, not a form.

**No unexplained acronyms in user-facing text.** Customers are not expected to know Salesforce internal jargon. Terms like **ADL** (Agentforce Data Library), **ESD** (Embedded Service Deployment), **PS/PSL** (Permission Set / Permission Set License), **MIAW** (Messaging for In-App and Web), **ASA** (Agentforce Service Agent), **JWT** (JSON Web Token), **RAG** (Retrieval-Augmented Generation), and similar shorthand may appear internally in this spec and in skill logic, but **must be either expanded on first use or replaced with a plain-language description** when shown to the user. Prefer plain-language descriptions (e.g. "Knowledge library that grounds the agent's answers") over acronym-with-expansion when possible. If you find yourself typing an acronym into a user-facing message, stop and rewrite.

**Interactive, never one-shot.** This setup mirrors the Help Agent Quick Setup wizard. Walk the user through **four checkpoints**, in order. At each checkpoint, ask the questions, **wait for the user's reply**, confirm what you heard, then proceed. Do not move to the next checkpoint without explicit user input.

---

## 4. Execution flow

The checkpoints below are both the conversation you run *and* the order the underlying work executes in. Each checkpoint states what it provisions and links to the script block (§7) it fills.

### 4.0 Readiness check (silent, before Checkpoint 1)

Before Checkpoint 1, silently run a **readiness check**. **THIS PHASE IS MANDATORY. Run the steps in exactly the order below — reordering fails with a concrete, unambiguous error, and previous runs have wasted cycles on it. Specifically, running step 3 (permission-set assignment) before step 2 (Data Cloud enablement) fails with:**

> `PermissionSet not found: GenieUserEnhancedSecurity`

The Data Cloud permission sets *do not exist in the org* until Data Cloud is turned on in step 2. If you see that exact error, you (or a prior run) skipped ahead — go back to step 2 and confirm Data Cloud is enabled before retrying step 3.

**Step 1 — Detect.** Use `agentforce-adlc:agentforce-generate` (feature/Data-Cloud detection lives in its `references/org-setup-for-adl.md` Step 0) to verify: Agentforce, Einstein Generative AI, Knowledge, Experience Cloud, **and Data Cloud** are enabled. Verify the running user has the licenses/permissions/SKUs needed for Agentforce + Embedded Messaging + Experience Cloud.

**Step 2 — Enable anything missing.** If any of the features above are off (especially **Data Cloud** — it's the most commonly disabled and it's the one that gates step 3), enable them via `agentforce-adlc:agentforce-generate` before doing anything else. If something is missing and cannot be enabled, surface the gap to the user clearly and stop. **Do not proceed to step 3 until every required feature is confirmed enabled** — re-run detection if needed to confirm.

  > **If Data Cloud is not yet provisioned, offer the user a choice up front.** Data Cloud provisioning can be enabled programmatically (`CustomerDataPlatformSettings.enableCustomerDataPlatform: true` — see `agentforce-adlc:agentforce-generate`'s `references/org-setup-for-adl.md`) but the underlying platform work takes time to finish in the background. Give the user two options before proceeding: (a) enable Data Cloud now and pause the flow — they can come back and resume once provisioning completes; (b) wait through it in this session, which may take some minutes. Do not silently block on provisioning without asking.

**Step 3 — CRITICAL/MANDATORY: Assign the Data Cloud permission sets immediately after step 2 completes.** This step is non-negotiable and must run the moment enablement finishes — do not defer it, do not batch it with Checkpoint 1, do not skip it because "the org looks fine." Skipping it ships a broken agent: grounding returns empty `knowledgeSummary` results at runtime even though ADL indexing reports SUCCESS. This is a hard prerequisite for Knowledge grounding, not optional polish.

  Both the **running user** (so they can configure the Agentforce Data Library) and the **Einstein Agent User** (so the agent's retriever returns results at runtime) need Data Cloud access. Defer to `agentforce-adlc:agentforce-generate` for this: it resolves the Einstein Agent User, assigns the required Data Cloud permission set and license, and verifies the assignment stuck. Do not resolve the user or assign permission sets by hand here.

  Note: the Data Space scope on that permission set is a separate UI-only step that cannot be automated — that's handled reactively in Checkpoint 4 Phase A (Check 2) if grounded queries still return empty after ADL indexing completes.

### 4.1 Checkpoint 1 — Meet Your Agent

*Provisions:* the placeholder values wired into the script's `config`, `system`, and `language` blocks (§7). *Fills:* `<agent_label_placeholder>`, `<developer_name_placeholder>`, `<agent_welcome_message_placeholder>`, `<agent_tone_placeholder>`, `<gc:languageSettings_language>`.

Ask the user for four things (you can ask together):
1. **Agent Name** — used for both the user-facing label (`<agent_label_placeholder>`) and the API/developer name (`<developer_name_placeholder>`; sanitize to alphanumeric + underscore, no leading digit). Offer the user two options: accept the default **`Help Agent`**, or type a name of their own choosing. Do not present a list of alternative names — just the default vs. custom.
2. **Language** — used for `language: default_locale` (`<gc:languageSettings_language>`). Default suggestion: `en_US` (English).
3. **Welcome Greeting** — used for `<agent_welcome_message_placeholder>`. Suggest a neutral default the user can accept or override (e.g. *"Hi, I'm {Agent Name}. How can I help you today?"*).
4. **Tone** — used for `<agent_tone_placeholder>`. Ask the user how they want the agent to sound when speaking with customers. They can describe it in their own words (e.g. *"friendly and casual, like a knowledgeable friend"*, *"formal and precise, like a banking concierge"*, *"playful, upbeat, brand-forward"*) or accept the default: *"calm, patient, friendly service agent — warm but professional, short sentences, never robotic."* Keep the captured tone string to one or two sentences — long persona prose competes with action-routing instructions and degrades tool-calling reliability. Tone affects *how* the agent speaks, not *what* it's allowed to do; the verification, PII, and case-management rules in the subagent reasoning blocks are not overridable by tone.

### 4.2 Checkpoint 2 — Give Your Agent Context (grounding)

*Provisions:* an Agentforce Data Library, then wires its `rag_feature_config_id` into the script's `knowledge:` block (§7). *Fills:* `<rag_feature_config_id>`.

**Before asking** — run `sf agent adl list --target-org $ORG` to see what ADLs already exist. Then present all options via `AskUserQuestion`:

- **Each existing ADL with a ready status** — list as *"Use existing library: {name} ({status})"*. Include only libraries with `indexingStatus ∈ {COMPLETED, READY, SUCCESS}`; skip `NOT_SCHEDULED` entries (they never indexed and will produce empty grounding at runtime).
- **Salesforce Knowledge** — create a new library grounded on existing Knowledge articles, filtered by Data Category.
- **Upload Files** — create a new library grounded on files the user provides.
- **Website Sync** *[Coming soon]* — fetch content from a public website.

Do not assume any existing ADL is the right one — the user must explicitly choose. Do not default to reusing a library that happens to share the expected name.

**CRITICAL — Wait for the user's selection before proceeding.** The `AskUserQuestion` above is a gate: you must receive the user's explicit reply before asking any follow-up questions. Do NOT ask about Data Category Groups, file paths, website URLs, or anything else in the same turn as the source-selection question. The user answers first; then you branch. If the user's reply names a grounding source other than "Salesforce Knowledge", do NOT ask about Data Categories at all — not now, not as a clarifying question, not as part of a combined question. Data Category questions are ONLY appropriate after the user has explicitly selected "Salesforce Knowledge."

Then, depending on selection:
- **If Salesforce Knowledge:** query the org for available Data Category Groups (and their categories) and **list them to the user**. Ask which specific categories the agent should ground on. Do not assume "all." Wire the selection into the ADL configuration.
- **If Upload Files:** ask the user to paste the file name (or file path) they want to upload. **After each file is submitted, present a selection prompt (e.g. via `AskUserQuestion`) with these options:**
  - **Upload another file** — collect the next file path and repeat.
  - **Done — proceed with these N files** — move on to ADL provisioning.

  Do not ask a yes/no question ("do you want to upload another?") — the user shouldn't have to type "yes" just to add another file. The selection itself is the action. Loop until the user picks "Done", then provision a file-based Agentforce Data Library with the full collected list.
- **If Website Sync:** ask the user for the website URL to fetch content from. Configure the data library to sync that URL.

The `rag_feature_config_id` returned by ADL provisioning gets wired into the agent script's `knowledge:` block — do not hardcode.

> **CRITICAL — Always create a fresh, named ADL for this agent — do not reuse `All_Records_and_Fields_Default`.** Every org ships with a stock library named `All Records and Fields (Default)` (DeveloperName `All_Records_and_Fields_Default`). It shows up in `sf agent adl list` with a valid `libraryId` and a `rag_feature_config_id` can be derived from it — but on trial or preloaded sample-data orgs it is typically stuck in `NOT_SCHEDULED` state and never actually indexes any content. Wiring the agent to that library produces empty `knowledgeSummary` at runtime even though the ID is valid and the platform reports no error.
>
> The right behavior: create a dedicated `Help_Agent_Knowledge` library at Checkpoint 2 (idempotent on DeveloperName — reuse only if it already exists AND its `indexingStatus.status ∈ {COMPLETED, READY, SUCCESS}`). Poll with `sf agent adl status --library-id <id>` and only wire the ID into the agent script's `knowledge:` block once the status is one of those terminal-success values. `NOT_SCHEDULED` is NOT a success signal — treat it as "must recreate."

> **`rag_feature_config_id` format.** The ID looks like `ARFPC_<libraryId>`, where `<libraryId>` is the 18-character ID returned by `adl create`. Note: `adl get` does NOT return a field named `ragFeatureConfigId` — the value only surfaces in the `adl publish` error message on a failed publish, and the format is documented in `references/agent-script.md`. If you can't find the value, run the publish once against a placeholder and read the ID out of the error, or construct it as `ARFPC_` + the library ID from `adl create`.

> **Knowledge ADL primary-index and content fields (read before configuring a Knowledge ADL).** Two related constraints — both silently break grounding if you get them wrong:
>
> 1. **`--primary-index-field1` and `--primary-index-field2` on `adl create` accept only *standard* KnowledgeArticleVersion fields** (`Title`, `Summary`, `Body`, `UrlName`, etc.). Custom `__c` fields on `Knowledge__kav` are rejected by the ADL API even though `Apex describeFields` confirms they exist. Use `Title` and `Summary` as the primary index fields.
> 2. **`--content-fields` on `adl update` also rejects custom `__c` fields** on `Knowledge__kav` in some org shapes — inspect the API response after `adl update` and fall back to standard rich-text fields (e.g. `Body`) if a custom field is rejected. **Do not list `Title` or `Summary` as content fields** either — the API rejects overlap with the primary index (`OVERLAPPING_CONTENT_FIELD`).
>
> **Pick body fields by inspection, not by name.** Query the org's `Knowledge__kav` schema and identify the rich-text body fields that actually contain article content (rich-text or long-text-area fields; describe the object and look for fields with type `TextArea` / `LongTextArea` and Length > 4000). Ask the user which one(s) hold the article body. Common patterns on Salesforce-shipped Knowledge configurations include `FAQ_Answer__c`, `KCSArticle_Issue__c`, and `KCSArticle_Resolution__c` — but these are conventions, not guarantees, and are not present on every org. Never assume a field name; inspect first. If the body-field set is wrong, grounded queries return empty results even though indexing reports SUCCESS.

**After Checkpoint 2, create the agent.** With placeholders (CP1) and `rag_feature_config_id` (CP2) in hand, create the agent per §7, then publish and activate it by deferring to `agentforce-adlc:agentforce-generate` — it owns the publish/activate lifecycle, including the retry-on-transient-failure path. Do not hand-roll publish/activate here.

**Before passing the agent script to `agentforce-adlc:agentforce-generate`, substitute `<default_agent_user_placeholder>` with the Einstein Agent User username captured in the readiness check (step 1): `{agentDevName}_user@{orgId}.ext`.** Do this substitution explicitly in the script text — never pass the literal placeholder string to the skill. If the username was not captured or is unclear, re-derive it as `{agentDevName}_user@{15-char-orgId}.ext` using `sf org display --target-org $ORG` to get the org Id.

### 4.3 Checkpoint 3 — Add to Channels

*Provisions (Web Chat path):* a messaging channel initially configured, deployed, and activated with Queue routing via `service-digital-engagement-channel-configure`, then rewired to the agent via `service-agentforce-channel-configure` (same fallback queue + `sessionHandlerAsa`), a new Embedded Service Deployment (`Help Chat`), and optionally a prepared LWR Experience Cloud site. The agent script (§7) does not change here — this is channel/site metadata around the agent.

**Step 1 — Discover what channels exist in the org, then present channel types.**

Query existing MessagingChannels. Note: `MessagingChannelType` is **not** a SOQL field — get names via SOQL, then retrieve metadata to determine type:

```bash
# Get channel names
sf data query --target-org $ORG --json \
  --query "SELECT Id, DeveloperName, MasterLabel FROM MessagingChannel ORDER BY MasterLabel"

# Retrieve all channel metadata to read <messagingChannelType> from each XML
sf project retrieve start --metadata "MessagingChannel" --target-org $ORG

# Extract types
grep -rh "messagingChannelType" force-app/main/default/messagingChannels/
```

Classify by `<messagingChannelType>` value: `EmbeddedMessaging` → Web Chat; `PstnVoice`/`InternalVoice` → Phone; `WhatsApp`/`AppleBusinessChat` → WhatsApp; `Sms` → SMS.

Use the results to determine which channel types to surface. Always show:
- **Web Chat** (create new, or add to any existing `EmbeddedMessaging` channels)
- **Help Portal** (create new Agentforce Concierge experience on an LWR site)

Show these only if the org has existing channels of that type:
- **Voice** — only if `PstnVoice` channels exist (this skill does not provision a new phone number). Detect native vs partner: extract digits from DeveloperName (`VOICE_PSTN_{digits}`), query `CommunicationChannelLine WHERE DeveloperName='DEV_{digits}'` via Tooling API. A row returned = native SCV (wiring supported); 0 rows = partner voice (wiring not supported — show but surface the limitation). See `service-agentforce-channel-configure`'s `channel-types.md` reference for detection steps.
- **WhatsApp** — if any WhatsApp channels exist
- **SMS** — if any Sms channels exist

Present the channel types via `AskUserQuestion` (multiSelect: true) **only when there are 4 or fewer types to show** — `AskUserQuestion` caps at 4 options per question, and pagination doesn't work for a multi-select choice (there is no way to select one item from page 1 and another from page 2 in a single answer). Label each with how many existing channels of that type are in the org (e.g. "Voice — 2 existing channels"), so the user knows what they'd be choosing from.

**If there are more than 4 types to show:** do not paginate. List every type in plain text (with its existing-channel count) and ask the user to type their selection(s) as a comma-separated list, e.g. "Web Chat, WhatsApp, SMS". Validate each typed name case-insensitively against the listed types, and confirm the resolved set back to the user before proceeding to Step 2. This is a deliberate exception to the general Long-list presentation rules pagination pattern — it applies specifically to this multi-select type list, not to single-select instance lists (sites, queues, ADLs, or the "which existing channel of this type" list in Step 2).

**Step 2 — For each selected channel type, ask: new or existing?**

After the user picks channel type(s), for each one ask a follow-up via `AskUserQuestion`:
- **Web Chat:** "Create a new Web Chat channel" OR list each existing `EmbeddedMessaging` channel as *"Add agent to: {MasterLabel}"*
- **Help Portal:** "Create a new Help Portal" — delegate to `service-concierge-portal-generate`.
- **Voice:** list each existing `PstnVoice` channel as *"Add agent to: {MasterLabel}"* — read [`references/channel-voice.md`](references/channel-voice.md) and follow it fully.
- **WhatsApp / SMS:** list each existing MessagingChannel as *"Add agent to: {MasterLabel}"*. "Create a new [type] channel" is NOT offered.

**Step 3 — Branch by selection.**

- **New Web Chat channel** → read [`references/channel-web-chat.md`](references/channel-web-chat.md) and follow it fully (domain, `authMode`, channel + ESD + site provisioning).
- **New Help Portal** → delegate to `service-concierge-portal-generate`, passing `$ORG`, `$BOT_ID`, and `$BOT_DEV_NAME`. **Immediately after that skill returns, capture its `PUBLISHED_PORTAL_URL` return value and store it as `$PORTAL_URL`. Then run Step 4 (the channel-add loop) before doing anything else — do NOT advance to Checkpoint 4 yet.**
- **Existing channel (any type, including Voice/WhatsApp/SMS)** → delegate wiring to `service-agentforce-channel-configure`, passing the agent DeveloperName and the selected channel's DeveloperName. That skill owns queue resolution, routing flow, and agent wiring for existing channels.

**Outbound escalation runs here, not at Checkpoint 4.** Immediately after inbound wiring is confirmed for a Web Chat or Voice branch (Branches A/B of `service-agentforce-channel-configure`), invoke that skill's Phase 3 (ask the user whether to configure outbound escalation; if yes, resolve the queue, create/reuse the RoutingFlow, add the connection block, republish) as part of the same delegated call — do not defer any part of it to Checkpoint 4. This is a single atomic unit owned by that skill; do not split flow-creation from connection-wiring across checkpoints.

Handle each selected channel branch independently. If one branch fails, report it and continue with the others — do not abort the whole setup.

**Step 4 — After EACH channel branch completes, immediately ask if the user wants to add another channel. This is the next thing you do — before Checkpoint 4, before any summary, before anything else.**

After each branch (success or failure), present via `AskUserQuestion`:

- **Add another [same type] channel** — e.g. if the user just wired a Phone channel, default to showing remaining unwired Phone channels first. Re-run Step 2 for that type. Skip channels already wired in this session.
- **Add a different channel type** — return to Step 1 (re-query `MessagingChannel`, rebuild the type list, omit already-wired channels from the options).
- **Done — proceed to go-live** — exit the loop and advance to Checkpoint 4.

Track which channels have been wired in this session so they are not re-offered. The loop continues until the user selects "Done" or all available channels have been wired.

### 4.4 Checkpoint 4 — Review & Go Live

Once the user exits the Checkpoint 3 channel loop ("Done"), run Checkpoint 4 in two phases. There is no separate numbered checkpoint between channel setup and go-live — Phase A below is what used to be "Checkpoint 3.5"; it now lives inside Checkpoint 4 because it runs at the same point in the flow and Checkpoint 4 is where verification belongs.

#### Phase A — Silent pre-flight (INTERNAL — never announce)

**Do NOT announce this phase, do NOT print a "running checks" message, do NOT tell the user it exists.** Run these three checks, in order, silently; only surface output if a check FAILS, and only then to explain the specific fix needed before proceeding to Phase B.

**Check 1 — Data Cloud access is in place for both the running user and the Einstein Agent User.** Re-confirm the Data Cloud grounding prerequisites by deferring to `agentforce-adlc:agentforce-generate` (the same gate used in the readiness phase). If it reports the access is missing or was changed out-of-band, re-run that gate; if it still fails, surface the specific missing user/permset and stop — do not proceed to Phase B.

**Check 2 — Agentforce Data Library is Activated AND grounded.** Using the `rag_feature_config_id` captured during Checkpoint 2:
  - Confirm the library is indexed and ready by deferring to `agentforce-adlc:agentforce-generate`, which owns the readiness gate. Do not poll it here.
  - Execute a canary grounded retrieval query against the library (e.g. a generic term likely to hit at least one indexed article, such as `"help"` or `"return"`). Confirm the response contains a non-empty `knowledgeSummary` / retrieval-results array. An empty result here — even with status=SUCCESS — is the classic silent-failure signature and means the Data Space scope or the Einstein Agent User's Data Cloud assignment is broken.
  - If the library is not Activated: activate it and re-check.
  - If retrieval returns empty despite SUCCESS status: surface the **Known manual step** (Data Space scope on the permission set) to the user verbatim, wait for confirmation that they've completed it in Setup, then re-run the canary query. Do not proceed to Phase B with an empty retrieval.

    > **Known manual step — Data Space scope for the Einstein Agent User.** When grounding is configured (Knowledge ADL), the Einstein Agent User needs Data Cloud access for the ADL retriever to return content. The `agentforce-adlc:agentforce-generate` skill's setup assigns the required permission set (e.g. `GenieUserEnhancedSecurity`) and PSL (`GenieDataPlatformStarterPsl`) automatically. **However, the Data Space scope on that permission set is a UI-only assignment** — there's no API to grant it. If grounded queries return empty `knowledgeSummary` after ADL indexing completes, pause the flow and instruct the user to:
    > 1. Setup → Permission Sets → **Data Cloud User** (`GenieUserEnhancedSecurity`)
    > 2. Open the assignment for the Einstein Agent User → **Data Space Access** → add the default Data Space → Save
    >
    > Then resume validation. Do not attempt to publish the agent until a grounded test query returns non-empty `knowledgeSummary`.

**Check 3 — The MessagingChannel is Active.** Fetch the MessagingChannel back from the org and assert its status is `Active` (not `Inactive`/`Draft`). `service-digital-engagement-channel-configure` activates the initially Queue-routed channel after deployment; `service-agentforce-channel-configure` then replaces that routing with the agent binding. `service-digital-engagement-messaging-site-integrate` does **not** own activation, so verify that the Agentforce routing deploy preserved the active state rather than assuming widget placement activated it. If the channel is not Active, activate it (the agent must already be Active) and re-fetch to confirm the status flipped. If it still won't activate, surface the specific channel and stop — do not proceed to Phase B with an inactive channel. **This is the only place in the flow that checks or sets channel-active state — Phase B does not repeat it.**

Only after all three checks pass silently, move to Phase B.

#### Phase B — Explicit go-live steps (narrated to the user)

1. Tell the user the agent is built, and **link them to Agentforce Builder** for this agent so they can review the agent definition, subagents, and topics.

2. **For the Web Chat / Help Portal path, verify the V2 Embedded Messaging widget is placed on the site — do not re-inject it here.** Placement already happened in Checkpoint 3, Step C.5 of `references/channel-web-chat.md`, which delegates to `service-digital-engagement-messaging-site-integrate` the moment the user picks a real Experience Cloud site. This step is a verification, not a repeat of that work: retrieve the ExperienceBundle for the target site (`sf project retrieve start --metadata "ExperienceBundle:<SiteName>"`), confirm all six `componentAttributes` keys (`clientVersion`, `deploymentName`, `hideChatButtonOnLoad`, `isExpSiteAuthMode`, `scrtUrl`, `siteEndpoint`) are present on `experience_messaging:embeddedMessaging` in `homeGuestLayout.json` (and `homeAuthenticated.json` if signed-in visitors are expected), then open the live customer URL in an incognito browser and confirm the floating chat launcher renders. Do NOT use `curl | grep` — the launcher mounts at runtime and is absent from server-rendered HTML, so a curl check always reports "missing" and misleads the diagnosis.

   **This verification does not apply to the own-website deployment path** (Step C.5's "I'll embed it on my own website" branch) — that path has no Salesforce-owned site layout to check; the customer embeds the Setup → Embedded Service Deployments → Get Code snippet on their own pages instead (see Step D.8 of `references/channel-web-chat.md`).

   **If verification fails** — the componentAttributes are missing, incomplete, or the launcher doesn't render — run the repair procedure below. This is the same procedure Step C.5 should have already run; only re-run it because something went wrong the first time (e.g. a prior deploy dropped attributes, or a `configurationName`-shaped node survived from an older run).

    1. **Retrieve the ExperienceBundle for the target site** to a scratch directory: `sf project retrieve start --metadata "ExperienceBundle:<SiteName>"`.
    2. **Resolve the values the component needs:**
       - `deploymentName` — the ESD's DeveloperName, e.g. `HelpChat` (from Step C.3).
       - `siteEndpoint` — the ESD's own auto-generated site URL. Query `SELECT Name, UrlPathPrefix FROM Site WHERE Name LIKE 'ESW_<DeploymentName>%'`; there will be two rows — pick the one whose `UrlPathPrefix` does **not** end in `vforcesite` (the vforcesite variant is the internal preview endpoint, not the customer-facing one). Build the endpoint as `https://<myDomainStem>.my.site.com/<UrlPathPrefix>`.
       - `scrtUrl` — the org's SCRT domain. Take the org's instance URL from `sf org display --json` and replace `.my.salesforce.com` with `.my.salesforce-scrt.com`.
       - `isExpSiteAuthMode` — `false` for public/anonymous visitors (matches the MessagingChannel `authMode: UnAuth` chosen in Step B of `channel-web-chat.md`); `true` only if the channel is `Auth`-mode.
    3. **Inject or overwrite the `experience_messaging:embeddedMessaging` component in the site's home layout(s).** For a public site the guest layout is required; for authenticated visitors add the same node to `homeAuthenticated.json`. The component node MUST include `"type": "component"` at the top level (missing it fails deploy with *"You seem to be missing the property type"*). Set `componentAttributes` to exactly these six keys:
       ```json
       {
         "componentAttributes": {
           "clientVersion": "WebV2",
           "deploymentName": "HelpChat",
           "hideChatButtonOnLoad": "Visible",
           "isExpSiteAuthMode": false,
           "scrtUrl": "https://<myDomainStem>.my.salesforce-scrt.com",
           "siteEndpoint": "https://<myDomainStem>.my.site.com/ESW<DeploymentName><timestamp>"
         },
         "componentName": "experience_messaging:embeddedMessaging",
         "id": "<uuid>",
         "renderPriority": "NEUTRAL",
         "renditionMap": {},
         "type": "component"
       }
       ```
       Any older `configurationName`-shaped node from a previous run must be replaced, not merged — the platform silently drops `configurationName` and the node round-trips with `componentAttributes: {}`.
    4. **Patch the ESD via the Tooling API to allow guest users (do not use Metadata API for this).** Metadata API rejects any update that touches the ESD's `site` field with an immutable-field error, even if you pass the current value unchanged. Use the Tooling REST API instead:
       ```http
       PATCH /services/data/v67.0/tooling/sobjects/EmbeddedServiceConfig/<id>
       {"Metadata": { ...all current Metadata fields..., "areGuestUsersAllowed": true, "clientVersion": "WebV2", "isEnabled": true }}
       ```
       **Read the current `Metadata` first with a GET and include every field on the PATCH** — omitting a field (e.g. `clientVersion`, `branding`, `masterLabel`) nulls it out on write. Successful PATCH returns HTTP 204.
    5. **Deploy the ExperienceBundle** back to the org: `sf project deploy start -m "ExperienceBundle:<SiteName>"`.
    6. **Publish the site.** Use the site's **community name** (from `Network.Name`) — not the site's `Site.Name`. On some org shapes these can differ: e.g. `Site.Name = Consumer_Site1` but `Network.Name = "Consumer Site"`. Query `SELECT Name FROM Network WHERE Status = 'Live'` to get the community name, then `sf community publish -n "<CommunityName>"`. `sf community publish` returns immediately; poll `SELECT Status FROM BackgroundOperation WHERE Id='<jobId>'` and wait for `Complete`.
    7. **Verify by retrieving the ExperienceBundle again and confirming all six `componentAttributes` keys survived the round-trip. Then verify the widget renders by opening the live customer URL in a guest browser.** Do NOT use `curl | grep` to check for the widget — the launcher mounts at runtime and is not present in the server-rendered HTML the raw GET returns, so a curl check will always report "missing" and lead to a wrong diagnosis. The check that matters: open `<customerSiteUrl>` in an incognito window and confirm the floating chat launcher (branded label like "Ask Me Anything") appears bottom-right. Only then does the widget count as placed.

    **Placement scope: the widget is placed on the home layouts you inject the component into.** Unlike the bootstrap-in-`mainAppPage.json` approach (which was site-wide), the LWR-component approach is per-layout. If the user wants the widget on every page of the site, either add the component to each page's layout JSON or (simpler) drop it onto the site's site-wide template in Experience Builder. This is a deliberate tradeoff: metadata-component placement is more surgical but more work to fan out to every page than a headMarkup script would be.

    **When to fall back to Experience Builder UI.** If the metadata round-trip in step 7 still shows attributes stripped after two retries — or if `sf community publish` reports errors — surface the problem to the user and direct them to place the component manually in Experience Builder (Setup → Digital Experiences → All Sites → Builder → drag *Embedded Messaging* onto the page → pick `HelpChat` from the *Deployment Name* dropdown → Publish). The UI is the authoritative fallback path; do not chase deploy failures indefinitely.

3. **Confirm the Escalation Flow is wired.** This was configured at Checkpoint 3 via `service-agentforce-channel-configure` Phase 3 (RoutingFlow creation, `connection customer_web_client:` block, republish) — not here. Just verify: `@utils.escalate` should transfer to the resolved queue when tested. If the user skipped Phase 3's escalation offer at Checkpoint 3 and now wants it, go back and run it there rather than hand-wiring it in this checkpoint.

4. **Verify the Embedded Service Deployment is published (V2, Version stamped).** If Step C.3 of `references/channel-web-chat.md` was followed correctly, the ESD was created *and* published in a single call via the Connect API `POST /services/data/v67.0/connect/embeddedmessaging/deployment/setup` (with `clientVersion: WebV2`) — that response includes `"isPublishSuccess": true` and no further publish step is needed. Verify the outcome by opening Setup → Embedded Service Deployments → **Help Chat** and checking:
   - Title reads *"Embedded Service Deployment Settings - Web"* with **no `(v1)` suffix and no "Switch to V2" button**.
   - Top-right shows *"Published on: {date}"* and *"Version: 1"* (not empty).

   **If *Published on:* is blank even though the title reads *Web (v2)* and `IsEnabled=true`** — and especially if the Publish button shows a red *"Select a Messaging Channel and then try publishing again."* banner — the ESD was created **without a messaging channel bound** (the `deployment/setup` call omitted `messagingChannelId`). Delete the ESD (`sf project delete source -m EmbeddedServiceConfig:HelpChat`) and recreate via the Connect API path in Step C.4 **with `messagingChannelId` (and `hostDomain`) in the body**.

   **If the Connect API itself returned `INTERNAL_ERROR`** and a Metadata API fallback was used instead, the ESD will not be auto-published. Attempt `POST /connect/embeddedmessaging/deployment/HelpChat/publish` to trigger publish programmatically. If that endpoint is also unavailable, surface the gap to the user: direct them to Setup → Embedded Service Deployments → Help Chat → Publish, and note the widget will not serve until *Published on:* is stamped.

   **If the title still says `(v1)`**, the ESD was created via bare Metadata deploy without `clientVersion: WebV2`. Delete it and recreate via the Connect API path. An unpublished or V1 deployment never serves the widget to visitors, even when the channel is Active.

5. Confirm the agent is live. For the Help Portal path, print the live portal URL — use `$PORTAL_URL` captured when `service-concierge-portal-generate` returned. If `$PORTAL_URL` is not in context (e.g. after context compression), re-derive it: query `SELECT UrlPathPrefix FROM Site WHERE Name='<DEB site name>'` and build `https://<orgDomain>.my.site.com/<UrlPathPrefix>/`. Do NOT reconstruct the URL from the instance URL or the org slug — always derive it from the `Site` record. Then print the post-setup next steps from Step D.8 of `references/channel-web-chat.md`: the test URL (or embed snippet instructions for own-website deployments) and the four-item testing checklist. Stay in the conversation — offer to walk through the checklist together and ask if they want any adjustments before signing off.

---

## 5. Placeholders to fill in (script companion)

The canonical agent script contains several `<...>` placeholders (agent label, developer name, welcome message, tone, default agent user, `rag_feature_config_id`, locale). Most are captured in Checkpoint 1 / Checkpoint 2 above. The full list, with example values and where each comes from, lives alongside the script in [`references/agent-script.md`](../references/agent-script.md) — read it when you load the script (after Checkpoint 2).

## 6. Deployment target

Connect to whichever Salesforce org is currently authenticated. All resources (agent, ADL, channels, sites) are created in that org. Authenticate the target org before running the prompt.

---

## 7. Canonical agent script (Quick ASA Help Agent template)

The full canonical agent script — the source-of-truth shape for topics, subagents, actions, instructions, and grounding config — lives in [`references/agent-script.md`](../references/agent-script.md), together with the placeholder list (§5) and the agent-shape summary (§2).

**Load it only when you are ready to create the agent — after Checkpoint 2**, once the Checkpoint 1 placeholders and the `rag_feature_config_id` are in hand. It is comprehension-and-generation material, not part of the interactive conversation, so keeping it out of context during Checkpoints 1, 3, and 4 saves a large number of tokens. Where the script conflicts with anything in this spec, the behavioral rules in §3–§4 win.
