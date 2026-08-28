---
name: service-agentforce-channel-configure
description: "Wires an existing, active Agentforce agent to a channel by resolving a fallback queue, setting up inbound routing (either PATCH SessionHandlerId on the MessagingChannel, or an inbound RoutingFlow for Voice/Email), and optionally configuring outbound escalation. Use when the user wants to add a channel to an existing agent, connect an agent to a messaging or voice channel, route Voice or Email-to-Case to an Agentforce agent, or set up a fallback queue for an agent channel. Also applies to an existing Help Agent. The channel infrastructure must already exist — this skill adds routing. DO NOT TRIGGER when the agent does not yet exist or still needs Help Agent setup (use agentforce-generate or service-helpagent-coordinate), when setting up Email-to-Case with an agent end-to-end (use service-email-to-case-configure), when creating the MessagingChannel itself (use service-digital-engagement-channel-configure), or when creating an Embedded Service Deployment (use service-digital-engagement-deployment-configure)."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion
metadata:
  version: "1.1"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "service-digital-engagement-channel-configure"
    - "service-digital-engagement-deployment-configure"
    - "service-email-to-case-configure"
    - "service-helpagent-coordinate"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# service-agentforce-channel-configure: Wire an Agentforce agent to a channel

Adds inbound routing between an existing channel and an existing Agentforce agent. The agent receives work items from the channel; a fallback queue handles overflow when the agent is unavailable.

This skill is generic — it works for any Agentforce agent, not just the Help Agent template.

## Scope

**In scope:**
- Resolving or creating a fallback queue with the correct `QueueSobject` SobjectType
- Branch A (Enhanced Chat / Enhanced Messaging): deploying `sessionHandlerType=AgentforceServiceAgent` + `sessionHandlerQueue` on an existing MessagingChannel, then binding `SessionHandlerId` via Data API PATCH
- Branch B (Voice): assumes the phone number and `PstnVoice` MessagingChannel already exist (provisioned by the caller, e.g. `service-helpagent-coordinate`), then creating an inbound RoutingFlow (`routingType: Copilot`) that routes to the agent with the queue as fallback
- Branch C (Email-to-Case): inbound routing via direct case-owner assignment or an Omni-Channel RoutingFlow, plus deploying a `BotEmailDefinition` (Email Configuration) that links the agent to Service Email and binding it to the routing address
- Optional outbound escalation: adding the appropriate `connection {type}:` block to the agent and republishing

**Out of scope:**
- Creating the agent — use `agentforce-generate` or `service-helpagent-coordinate`
- Creating the MessagingChannel — use `service-digital-engagement-channel-configure`
- Creating the Embedded Service Deployment — use `service-digital-engagement-deployment-configure`
- Creating the Voice or Email-to-Case channel infrastructure
- Outbound escalation RoutingFlow creation — surface the gap if one is needed and doesn't exist

---

## Required inputs

- **Agent `DeveloperName`** and **agent label** (`MasterLabel`) — must be an existing, active agent
- **Channel type** — one of: Enhanced Chat, Enhanced Messaging (3rd-party), Voice, Email-to-Case
- **Channel identifier** — MessagingChannel `DeveloperName` (Branch A), or the channel name/context (Branches B/C)
- **Target org alias**

---

## Workflow

Steps are sequential. Read `references/channel-types.md` first to confirm the routing branch before proceeding.

### Phase 1 — Verify agent and resolve queue

1. **Confirm the agent exists and has an active version:**
   ```bash
   # Get the definition
   sf data query --target-org $ORG --json \
     --query "SELECT Id, DeveloperName, MasterLabel FROM BotDefinition WHERE DeveloperName='{AGENT_DEVELOPER_NAME}'"

   # Check for an Active version
   sf data query --target-org $ORG --json \
     --query "SELECT Id, Status FROM BotVersion WHERE BotDefinitionId='{BOT_DEFINITION_ID}' AND Status='Active' LIMIT 1"
   ```
   Stop with a clear message if the definition is not found or no version has `Status = Active`.

2. **Resolve the fallback queue and routing configuration** — follow `references/queue-resolution.md`:
   - Determine SobjectType from the channel type (see `references/channel-types.md`)
   - Query existing compatible queues; present via `AskUserQuestion` or create new
   - Query for an existing `QueueRoutingConfig`; create one with the correct capacity percentage if absent
   - Capture `QUEUE_DEVELOPER_NAME`, `QUEUE_NAME`, and `QUEUE_ID`

---

### Phase 2 — Wire inbound routing

#### Live-traffic warning gate (runs before any branch)

Before making any routing change, detect whether the channel already has active inbound routing (Branch A: non-empty `SessionHandlerType`; Branches B/C: any active RoutingFlow assigned to the service channel). If it does, first check whether the user's prompt already answered the timing choice ("do not cut over" / "wire manually" / "review first" → defer silently; "cut over now" / "activate immediately" → proceed silently). Only if the prompt is silent, warn via `AskUserQuestion` and let the user choose **"Re-route now"** or **"Set up, then wire manually"** — and on any ambiguous or no-selection response, default to the deferred path (never to a live re-route). When deferred, set `DEFER_INBOUND_ROUTING=true`, skip the channel-activation step in the chosen branch, and print the manual wiring instructions at the end of Phase 2.

If the channel has no existing routing, skip this gate entirely and proceed directly.

Full detection queries, exact `AskUserQuestion` block, deferred-flow rules per branch, and manual-wiring copy: `references/live-traffic-gate.md`.

---

#### Branch A — Enhanced Chat / Enhanced Messaging (3rd-party)

No RoutingFlow required. Deploy the MessagingChannel with `sessionHandlerType` + `sessionHandlerQueue` only, then bind the bot via a Data API PATCH. `sessionHandlerAsa` is not accepted by the Metadata API at v67 — the deploy silently drops it and `SessionHandlerId` stays null unless you run the PATCH. The bot must be Active before the PATCH ("Only active Agentforce Service Agents are supported" otherwise).

All five steps below are mandatory and must run in order — do **not** skip the retrieve/edit/deploy and jump straight to the PATCH. Run the retrieve and edit in the **current working directory** (a real SFDX project), so the edited `.messagingChannel-meta.xml` is saved into the project's `force-app` tree — not a throwaway temp dir. Steps 1–3 record the routing change in source; steps 4–5 apply the binding the Metadata API can't.

1. **Retrieve the current MessagingChannel metadata** into the working-directory project:
   ```bash
   sf project retrieve start \
     --metadata "MessagingChannel:{CHANNEL_DEVELOPER_NAME}" \
     --target-org $ORG
   ```

2. **Edit the retrieved `.messagingChannel-meta.xml` in place** — set exactly these two fields (do NOT add `<sessionHandlerAsa>`):
   ```xml
   <sessionHandlerType>AgentforceServiceAgent</sessionHandlerType>
   <sessionHandlerQueue>{QUEUE_DEVELOPER_NAME}</sessionHandlerQueue>
   ```
   Apply this edit with the file-editing tool (Edit/Write) so the change is saved to the retrieved file at `force-app/main/default/messagingChannels/{CHANNEL_DEVELOPER_NAME}.messagingChannel-meta.xml` in the working directory — do **not** hand-edit it through an inline `sed`/`cat` heredoc into a temp path. The deploy in step 3 must read this same on-disk file.

3. **Deploy:**
   ```bash
   sf project deploy start \
     --metadata "MessagingChannel:{CHANNEL_DEVELOPER_NAME}" \
     --target-org $ORG
   ```

4. **Bind the bot via Data API PATCH:**
   ```bash
   CHAN_ID=$(sf data query --target-org $ORG --json \
     --query "SELECT Id FROM MessagingChannel WHERE DeveloperName='{CHANNEL_DEVELOPER_NAME}'" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
   BOT_ID=$(sf data query --target-org $ORG --json \
     --query "SELECT Id FROM BotDefinition WHERE DeveloperName='{AGENT_DEVELOPER_NAME}'" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
   QUEUE_ID=$(sf data query --target-org $ORG --json \
     --query "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='{QUEUE_DEVELOPER_NAME}'" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")

   sf api request rest --method PATCH -o $ORG \
     "/services/data/v67.0/sobjects/MessagingChannel/${CHAN_ID}" \
     --body "{\"SessionHandlerId\":\"${BOT_ID}\",\"FallbackQueueId\":\"${QUEUE_ID}\"}"
   # Expected: HTTP 204
   ```

5. **Verify:**
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE Id='${CHAN_ID}'"
   ```
   Both `SessionHandlerId` and `FallbackQueueId` must be non-null.

No agent file changes — no republish needed. Proceed to Phase 3 (optional).

---

#### Branch B — Voice

Wires a `PstnVoice` MessagingChannel to the agent via an inbound `Copilot`-type RoutingFlow with the queue as fallback. Distinct from Branch A: no `sessionHandlerAsa`; the channel is bound to the flow (`sessionHandlerType=Flow`), and the agent needs a `modality voice:` block appended before republish.

Follow `references/channel-branch-voice.md` end to end. Highlights:

- Step 0 — reuse an existing `PstnVoice` MessagingChannel or have `service-helpagent-coordinate` provision one first (its `references/channel-voice.md`); abort if the org uses a partner telephony provider (see `references/channel-types.md`).
- Steps 1–3 — write and deploy the inbound RoutingFlow using the template in `references/routing-flow.md`, verifying `ActiveVersionId` is non-null.
- Step 4 — deploy a `MessagingChannel` metadata file for `{CHANNEL_DEVELOPER_NAME}` with `sessionHandlerType=Flow`, `sessionHandlerFlow={FLOW_DEVELOPER_NAME}`, `sessionHandlerQueue={QUEUE_DEVELOPER_NAME}`. Without this the flow is never executed and calls hang up. Verify `SessionHandlerId` starts with `300`.
- Step 5 — append the platform-default `modality voice:` block (voice_id `UgBBYS2sOqTuMpoF3BR0`, "Mark", en_US) to the `.agent` file if missing; do not ask the user. Republish per `references/agent-wiring.md`.

Proceed to Phase 3 (optional).

---

#### Branch C — Email-to-Case

Inbound routing to the agent via direct case-owner assignment or an Omni-Channel `Copilot` RoutingFlow — user chooses in Step 2. Additionally requires the `connection service_email:` **surface** block and a mandatory BotEmailDefinition step (Email Configuration). It gates on API v68.0+ up front (see `references/channel-branch-email.md`).

Follow `references/channel-branch-email.md` end to end. Load-bearing gotchas (full walkthrough in that file):

- Step 1 — bind routing-address fields via Tooling-API PATCH or a `--metadata-dir` `Settings:Case` deploy, **never** a source `--metadata Settings:Case` deploy (it reads `sourceApiVersion` and mutates the user's project).
- Step 2 — choose inbound routing (`AskUserQuestion`): **case-owner** (`caseOwner` = the agent's bot user) or **Omni-Channel flow** (`Copilot` RoutingFlow + `routingFlow`/`fallbackQueue`). Resolve the bot user either way; routing fields go in the Step 4d deploy.
- Step 3 — the agent is already active, so add the mandatory `connection service_email:` surface via **deactivate → publish → activate** (a plain publish fails with `couldn't find the default agent user`). Batch the outbound route here too if escalation is wanted.
- Step 4 — BotEmailDefinition: preflight the save-time gates, validate the reply template, deploy via `--metadata-dir`, then bind the routing address in one `Settings:Case` deploy (`botEmailDefinition` + Step 2 routing fields + the required `casePriority`). Stop on failure.

Branch C is complete once the routing-address binding is verified. Proceed to Phase 3.

---

### Phase 3 — Outbound escalation (optional)

After inbound routing is confirmed, ask the user:

> *"Inbound routing is now set up — the channel will route to [agent name]. Do you also want to configure outbound escalation so the agent can hand off to a human when requested?"*

If yes:

1. **Resolve the escalation queue** — follow the escalation queue resolution steps in `references/queue-resolution.md` (Step 6). The user may want a different queue for escalation than the inbound fallback. Capture `ESCALATION_QUEUE_DEVELOPER_NAME` and `ESCALATION_QUEUE_ID`.

2. **Determine the outbound flow name** from the channel type (see naming table in `references/routing-flow.md` Part 2).

3. **Check if an active outbound flow already exists:**
   ```bash
   sf data query --target-org $ORG --json \
     --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='{OUTBOUND_FLOW_DEVELOPER_NAME}' AND ProcessType='RoutingFlow'"
   ```
   - Row exists with non-null `ActiveVersionId` → reuse it; skip to step 4.
   - Row missing or `ActiveVersionId` null → create the flow using the QueueBased template in `references/routing-flow.md` Part 2, substituting `ESCALATION_QUEUE_DEVELOPER_NAME` for `QUEUE_DEVELOPER_NAME`. Deploy and verify `ActiveVersionId` is non-null before continuing.

4. **Add the connection block** to the agent's `.agent` file and republish — follow `references/agent-wiring.md`. The connection key depends on channel type:
   - **Enhanced Chat (EmbeddedMessaging)** → `connection customer_web_client:`
   - **Enhanced Messaging (3rd-party)** → `connection messaging:`
   - **Voice** → `connection telephony:`
   - **Email-to-Case** → `connection service_email:`

---

## Rules / constraints

| Rule | Rationale |
|---|---|
| Verify the agent exists and is Active before making any changes | Wiring a channel to a non-existent or inactive agent silently fails at runtime |
| If the channel already has active inbound routing, honor an explicit defer/cutover intent in the prompt without asking; otherwise warn via `AskUserQuestion` and default to defer on ambiguity | Re-routing takes effect immediately and affects live traffic — queue and RoutingFlow creation always proceed; only the activation step is gated, and the safe default is non-destructive |
| When deferred, print exact manual wiring instructions before Phase 3 | The operator needs to know precisely what to run when they're ready to cut over |
| Never modify the MessagingChannel without retrieving the current metadata first | Overwriting without retrieval discards existing settings |
| Branch A: no RoutingFlow, no agent republish; deploy `sessionHandlerType` + `sessionHandlerQueue` via metadata, then bind `SessionHandlerId` via Data API PATCH | `sessionHandlerAsa` is not accepted by the Metadata API at v67 — the deploy silently drops it, so bot binding must happen via the Data API PATCH after deploy. Bot must be Active before the PATCH |
| Branches B/C: always create a new RoutingFlow — never reuse existing org flows | OOB platform flows commonly have `ActiveVersionId: null` and cannot be referenced |
| Branches B/C: use `routingType: Copilot` and `copilotLabel` — not `QueueBased` | `QueueBased` routes to the queue directly; `Copilot` routes to the agent first with the queue as fallback |
| Queue `Id` must be queried and embedded in the RoutingFlow XML | The `queueId` parameter requires a hardcoded 18-char record Id — do not leave it empty |
| Queue naming: `{ChannelTypeLabel} Queue` | Named after the channel type, not the agent |
| Outbound escalation is optional — never block inbound routing completion on it | Inbound and outbound are independent; inbound wiring is complete without the outbound step |
| Branch C: deploy BotEmailDefinition via `--metadata-dir`, never `--metadata BotEmailDefinition:<name>` | Not in the CLI's SDR registry, so the named-type deploy fails; metadata-format works |
| Branch C: do not wire an agent carrying a `ServiceCustomerVerification` topic to email | Detect and stop — do not auto-remove (may be legitimate for a multi-surface agent). See `channel-branch-email.md` Step 4a |

---

## Verification checklist

### Queue
- [ ] Queue has a `QueueSobject` record with the correct `SobjectType` for the channel type
- [ ] Running user is a member of the queue (if newly created)
- [ ] Queue has a `QueueRoutingConfig` with the correct `CapacityPercentage` (50 / 100 / 25 for Chat / Voice / Email)

### Branch A — MessagingChannel
- [ ] `SessionHandlerType = AgentforceServiceAgent` after deploy
- [ ] Bot is Active before the Data API PATCH
- [ ] `SessionHandlerId` is non-null after the Data API PATCH (matches the bot's `BotDefinition.Id`, starts with `0Xx`)
- [ ] `FallbackQueueId` is non-null after the Data API PATCH (matches the resolved queue Id)

### Branches B/C — RoutingFlow
- [ ] RoutingFlow `ActiveVersionId` is non-null
- [ ] `routingType = Copilot` in the flow's `routeWork` action
- [ ] `copilotLabel` matches the agent's exact `MasterLabel`
- [ ] `queueId` is populated (non-empty)

### Branch C — Email routing address
- [ ] If new: `EmailRoutingAddress` record created with correct `PersonalName` and `Address`
- [ ] If new: CaseSettings patched with `caseOrigin`, `saveEmailHeaders: true`, `addressType: EmailToCase`
- [ ] If new: user informed that a verification email was sent to the support address (non-blocking)

### Branch C — BotEmailDefinition
- [ ] Preflight passed: agent is `EinsteinServiceAgent` with a bot user holding `agentforceServiceAgentUser`; active version carries the `ServiceEmail` surface; no `ServiceCustomerVerification` topic on the email agent
- [ ] Reply `EmailTemplate` is SFX, HTML, public, and contains `[[[GENERATED_CONTENT]]]` + `[[[LEGAL_DISCLOSURE]]]`
- [ ] Headless path (API ≥68): `BotEmailDefinition` deployed via `--metadata-dir` with `success: true`; `legalDisclaimer`/`signature` ≥10 chars
- [ ] Routing address's `botEmailDefinition` child set to the deployed component `fullName`
- [ ] Inbound routing set on the same routing address: `caseOwner`+`caseOwnerType` or `routingFlow`+`fallbackQueue`, with `casePriority` present

### Optional Phase 3 — Outbound escalation
- [ ] Correct connection block used: `customer_web_client:` for EmbeddedMessaging, `messaging:` for 3rd-party, `telephony:` for Voice, `service_email:` for Email-to-Case
- [ ] `outboundRouteName` and `outboundRouteType` present in the correct `<plannerSurfaces>` entry of the deployed bundle
- [ ] Agent status is Active after republish

---

## Reference file index

| File | When to read |
|---|---|
| `references/channel-types.md` | Phase 1 — determine SobjectType and routing branch |
| `references/queue-resolution.md` | Phase 1 — queue lookup, creation, and Id capture |
| `references/live-traffic-gate.md` | Phase 2 — detection queries, deferred-flow rules, and manual wiring copy for the live-traffic warning gate |
| `references/channel-branch-voice.md` | Branch B — full Voice inbound wiring: PstnVoice channel selection, RoutingFlow, MessagingChannel assignment, `modality voice:` republish |
| `references/channel-branch-email.md` | Branch C — full Email-to-Case wiring: API v68.0+ precondition gate, CaseSettings flags, EmailRoutingAddress + read-modify-write patch, inbound RoutingFlow, mandatory `connection service_email:` surface block, headless BotEmailDefinition deploy, routing-address binding |
| `references/botemaildefinition.md` | Branch C Step 4 — BotEmailDefinition fields, save-time validation order, ASA template rules, `--metadata-dir` deploy recipe, `ServiceEmail` surface prerequisite, composite org gate |
| `references/routing-flow.md` | Branches B/C — inbound RoutingFlow XML template, deploy, verify |
| `references/agent-wiring.md` | Phase 3 (optional) — outbound escalation `connection` block |
| `assets/BotEmailDefinition.botEmailDefinition-meta.xml` | Branch C Step 4c — starting template for the BotEmailDefinition source file |
| `assets/mdapi-package.xml` | Branch C Step 4c — metadata-format `package.xml` for the `--metadata-dir` deploy |
| `assets/email/unfiled$public/AgentforceForServiceEmailTemplate.email` + `.email-meta.xml` | Branch C Step 4b (fallback) — minimal ASA-compliant SFX reply template when the user has none |
| `scripts/validate-botemaildefinition.py` | Branch C Step 4c — validate the BotEmailDefinition file before deploy |
| `scripts/validate-emailtemplate.py` | Branch C Step 4b (fallback) — validate the SFX template before deploy |
