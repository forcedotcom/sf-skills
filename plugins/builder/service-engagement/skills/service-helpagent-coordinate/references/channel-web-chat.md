# Channel branch — Web Chat

> **When to read this file.** Load it only when the user has selected **Web Chat** at Checkpoint 3. If they selected Voice, read `channel-voice.md` instead. If they selected Help Portal, delegate to the sibling skill `service-concierge-portal-generate` — do not inline portal steps here. You do not need every channel file in context at once — read only the branch the user chose.

Web Chat embeds a chat widget on a website. This branch provisions a messaging channel + omni-channel routing, a new Embedded Service Deployment (`Help Chat`), and a prepared LWR Experience Cloud site. The agent script does **not** change here — this is channel/site metadata around the agent.

## Step A — Ask for the domain

Ask the user for **the domain** where the widget will live (e.g. `support.acme.com`). This is required — the embedded deployment ties the JavaScript snippet to that domain via a security key, so the snippet cannot be lifted onto an unauthorized site.

## Step B — CRITICAL, DO NOT SKIP: ask who will be chatting

**Step B checklist (do all three, in order):**
1. **Audience** — ask (or infer from the prompt) who will chat: `Public / anonymous`, `Both anonymous and authenticated (default)`, or `Authenticated only`.
2. **`authMode`** — map audience → `authMode`: anonymous or mixed → `UnAuth`; authenticated-only → `Auth`. Name the chosen value explicitly in the settled-facts report as a bare value (`authMode: UnAuth`).
3. **Post-deploy assertion** — after the channel is deployed in Step C, re-fetch the MessagingChannel and assert `embeddedConfig.authMode` matches the chosen value; if it doesn't, surface the discrepancy and stop the Web Chat branch. Always run this assertion.

This determines the MessagingChannel's `embeddedConfig.authMode`, which is set when the channel is deployed in Step C below. Choosing wrong silently breaks the deployment: the widget refuses to render on the Setup → ESD → "Test Enhanced Web Chat" page and for any anonymous visitor on the live site, with no error surfaced to the user. This is the single highest-risk decision in the Web Chat branch — previous runs defaulted to `Auth` and shipped a non-functional deployment that took manual debugging to discover. Ask explicitly and confirm the answer back to the user before proceeding.

Present three options:
1. **Public site / anonymous visitors only** → `authMode = UnAuth`.
2. **Both anonymous and authenticated visitors** *(default — recommended for any customer-facing portal)* → `authMode = UnAuth`. Despite the name, `UnAuth` *allows* both: guests chat anonymously, and signed-in users can upgrade the session by passing an `identityToken` at runtime.
3. **Authenticated visitors only** (no guests) → `authMode = Auth`. **Warn the user verbatim:** *"This requires your host app to mint a verified-user JWT for every visitor. The Setup → ESD → 'Test Enhanced Web Chat' button will not work because it loads the widget as a guest, and anonymous visitors on your Experience site will fail to load the chat. Pick this only if you have JWT issuance in place."*

Default to option 2 if the user is unsure. Never silently pick `Auth`. Never emit a legacy `esw.min.js` / Live Agent V1 bootstrap snippet — the V2 widget mounts via the `experience_messaging:embeddedMessaging` LWR component (Step C.3, Checkpoint 3.5 Check 3b).

## Step C — Provision (in order)

### C.0 — Resolve escalation queue

Run immediately after Step B (before any deploy), once the channel type is known.

**Query existing queues that already support the relevant SobjectType for this channel:**

| Channel | SobjectType |
|---|---|
| Web Chat / Help Portal / WhatsApp / SMS / Messaging | `MessagingSession` |
| Voice / Phone | `VoiceCall` |
| Email / Case | `Case` |

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Queue.Name, Queue.DeveloperName, Queue.Id
           FROM QueueSobject
           WHERE SobjectType='MessagingSession'"
```

Branch via `AskUserQuestion`:
- **One or more queues found** → present each as an option (`{Name} ({DeveloperName})`), plus a final option *"Create a new queue for this agent"*. If the user picks an existing queue, capture its `DeveloperName` and skip queue-creation below.
- **Zero queues found** → inform the user no compatible queue exists and proceed to create one.

**If creating a new queue:**

1. Name: `{AgentLabel} Queue`, DeveloperName: `{AgentDevName}_Queue`
2. Create the `Group` record:
   ```bash
   QUEUE_ID=$(sf data create record --target-org $ORG \
     --sobject Group \
     --values "Type='Queue' Name='{AgentLabel} Queue' DeveloperName='{AgentDevName}_Queue'" \
     --json | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['id'])")
   ```
3. Grant the queue access to `MessagingSession`:
   ```bash
   sf data create record --target-org $ORG \
     --sobject QueueSobject \
     --values "QueueId='$QUEUE_ID' SobjectType='MessagingSession'"
   ```
4. Add the executing user to the queue:
   ```bash
   RUNNING_USER_ID=$(sf org display --target-org $ORG --json \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['userId'])")
   sf data create record --target-org $ORG \
     --sobject GroupMember \
     --values "GroupId='$QUEUE_ID' UserOrGroupId='$RUNNING_USER_ID'"
   ```

Capture the resolved `QUEUE_DEVELOPER_NAME` (either from an existing queue or the one just created). It is used in both Step C.1 (MessagingChannel `sessionHandlerQueue`) and Step C.2 (RoutingFlow queue lookup).

---

### C.1 — Create the Outbound (Escalation) RoutingFlow

> **This step is owned by `service-agentforce-channel-configure` Phase 3.** The full template, naming convention, check-before-create logic, and deploy/verify steps are in that skill's `routing-flow.md` Part 2. Follow that reference — do not duplicate the XML here.

For Web Chat, the channel type label is **Enhanced Chat**, so:
- Flow label: `{AgentLabel} Outbound Enhanced Chat Flow`
- DeveloperName: `{AgentDevName}_Outbound_Enhanced_Chat_Flow`
- `SERVICE_CHANNEL_DEV_NAME`: `sfdc_livemessage`, `SERVICE_CHANNEL_LABEL`: `Messaging`
- Queue: `QUEUE_DEVELOPER_NAME` from Step C.0

Follow the template and steps in `service-agentforce-channel-configure`'s `routing-flow.md` Part 2. Capture `{FLOW_DEVELOPER_NAME}` for use in the agent's `connection customer_web_client:` block at Checkpoint 4 (`outbound_route_name: "flow://{FLOW_DEVELOPER_NAME}"`). Note: Web Chat uses `connection customer_web_client:` — not `connection messaging:` — see `service-agentforce-channel-configure`'s `agent-wiring.md`.

---

### C.2 — Deploy MessagingChannel

Deploy the messaging channel + omni-channel routing (`service-digital-engagement-channel-configure`, channel deploys INACTIVE). **Set `embeddedConfig.authMode` from the choice in Step B.** For `UnAuth`, also set `anonymousUserJwtExpirationTime` (e.g. `360`). For `Auth`, set `verifiedUserJwtExpirationTime` (e.g. `60`). Set `sessionHandlerQueue` to the `QUEUE_DEVELOPER_NAME` resolved in Step C.0.

   > **v67 ASA routing note.** `service-digital-engagement-channel-configure` handles the v67 limitation automatically for ASA routing: it deploys the XML without `sessionHandlerAsa` (rejected by the Metadata API), then binds `SessionHandlerId` + `FallbackQueueId` via Data API PATCH (its step 15a). Verify both fields are non-null after the skill completes. Also ensure the bot is Active before invoking the skill — the PATCH is rejected with "Only active Agentforce Service Agents are supported" otherwise.

### C.3 — Activate MessagingChannel

Activate the MessagingChannel after the agent is Active (and re-verify at Checkpoint 4).

### C.4 — Create a NEW Embedded Service Deployment named `Help Chat`

Delegate to **`service-digital-engagement-deployment-configure`** with these inputs:

- **Operation**: `create`
- **Deployment type**: `Web`
- **Deployment name / DeveloperName**: `HelpChat` / MasterLabel `Help Chat`
- **Channel**: MessagingChannel DeveloperName from Step C.1 (skill will query the record Id)
- **hostDomain**: the customer domain from Step A (e.g. `support.acme.com`) — ties the widget's security key to that domain

The skill creates the ESD via `POST /connect/embeddedmessaging/deployment/setup` (V2, Connect API), binds the messaging channel at creation time so `isPublishSuccess: true` is returned, and auto-generates the `ESW_*` scaffolding site. **Do NOT re-point or re-use any existing ESD from a prior deployment.**

After the skill completes, capture the ESC Id:

```bash
sf data query --target-org $ORG --use-tooling-api \
  -q "SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='HelpChat'" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])"
```

The ESD's endpoint URL (needed for the `siteEndpoint` attribute on the LWR component) is the `ESW_HelpChat_*` site row **without** the `vforcesite` suffix:

```bash
sf data query --target-org $ORG \
  -q "SELECT Name, UrlPathPrefix FROM Site WHERE Name LIKE 'ESW_HelpChat%' AND SiteType='ChatterNetworkPicasso'" --json
```

Pass `siteEndpoint` (`https://<myDomainStem>.my.site.com/<UrlPathPrefix>`) to Checkpoint 3.5 Check 3(b).
### C.5 — Resolve deployment target (Experience Cloud site or own website)

Ask the user where they want to deploy the chat widget via `AskUserQuestion`:
- **"I'll embed it on my own website"** *(Recommended for most customers)* — skip Experience Cloud site creation. The ESD was already created above without a `<site>` reference; skip widget injection (Steps D.1–D.7). Proceed to Step D.8 for the embed snippet instructions.
- **"Deploy on a Salesforce Experience Cloud site"** — continue with the site resolution below.

**If Experience Cloud path:** Query for real (non-auto-generated) sites — both LWR and Aura:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Id, Name, MasterLabel, UrlPathPrefix, SiteType, Status FROM Site WHERE Status='Active' AND SiteType IN ('ChatterNetworkPicasso','ChatterNetwork') ORDER BY SiteType, Name" \
  | python3 -c "
import sys, json
recs = json.load(sys.stdin)['result']['records']
real = [r for r in recs if not r['Name'].startswith('ESW_')]
esw  = [r for r in recs if r['Name'].startswith('ESW_')]

for r in real:
    r['_type'] = 'LWR' if r['SiteType'] == 'ChatterNetworkPicasso' else 'Aura'

print(f'Real sites: {len(real)} ({sum(1 for r in real if r[\"_type\"]==\"LWR\")} LWR, {sum(1 for r in real if r[\"_type\"]==\"Aura\")} Aura) | ESW-filtered: {len(esw)}')
for r in real:
    print(f'  {r[\"MasterLabel\"]:40} ({r[\"_type\"]}) | /{r[\"UrlPathPrefix\"]}')
"
```

> **ESW filtering — why and how:** Every ESD auto-creates a pair of `Site` records named `ESW_{EsdName}_{timestamp}` (one Aura, one LWR). These are internal endpoint scaffolding, not real Experience Cloud destinations. SOQL `NOT LIKE` cannot be combined with `AND` in the `sf data query` CLI without a shell-quoting error, so filter them out in Python post-processing as shown above. If all sites after filtering are ESW-prefixed, treat as "zero real sites found."
>
> **Duplicate MasterLabels:** Each real Experience Cloud site generates two `Site` records with the same `MasterLabel` — one `ChatterNetwork` (Aura) and one `ChatterNetworkPicasso` (LWR). Both are shown to the user. The `SiteType` on the record the user picks determines which metadata layout path `service-digital-engagement-messaging-site-integrate` follows (LWR: patches `sfdc_cms__themeLayout/*/content.json` footer regions; Aura: patches `homeGuestLayout.json`).
>
> **Status value:** `Site.Status` is `'Active'` (not `'Live'`) on all org shapes tested. Using `'Live'` returns zero rows.

**Branch by what's found:**

- **Zero real sites found** → ask: deploy on own website (give snippet), or create a new LWR Experience Cloud site via `experience-lwr-site-generate` (recommend *Help Center* template).

- **Real sites found** → present using the **long-list presentation rules** from SKILL.md. Do not label sites as LWR/Aura — show each as `{MasterLabel} (/{UrlPathPrefix})`. Always include "Create a new Experience Cloud site" and "Deploy on my own website (get snippet)" as fixed options on the final page.

**After the user selects:**

- **Site selected (either type)** → delegate to `service-digital-engagement-messaging-site-integrate`. The skill reads `SiteType` from the selected site's record and patches the correct layout automatically (LWR: `sfdc_cms__themeLayout/*/content.json` footer regions; Aura: `homeGuestLayout.json` and `homeAuthenticated.json`). After the skill completes, confirm: *"The chat widget has been added to [site name] and will appear as a floating overlay on every page."* Publish the site and verify the smoke-test URL returns 200.
- **Own website selected** → proceed to Step D.8 snippet instructions.

Do not filter by any hardcoded site name or `UrlPathPrefix` value — the correct site depends on the customer's org and is not knowable up front.

### C.6 — Wire up knowledge citations The script's `knowledge:` block ships with `citations_enabled: True` and `citations_url: ""` (the URL isn't knowable until a site exists). Once the target site's public URL is resolved here, set `citations_url` to that URL so knowledge answers cite working links. If no customer-facing site URL can be resolved, set `citations_enabled: False` instead — do not leave citations enabled with an empty URL, or answers render broken/empty citation links.

## Step D.8 — Post-setup next steps (Checkpoint 4, after go-live)

Print these after the ESD is published and the channel is Active.

**If deployed on an Experience Cloud site:**
- Test URL: `https://{siteBaseUrl}/{siteUrlPathPrefix}/s` — open in an incognito browser as a guest. The floating chat launcher should appear. Send a message to confirm the agent responds.
- Test escalation: say *"I need to speak to a human"* — the agent should transfer to the queue resolved in Step C.0. This requires at least one agent to be available in the Omni-Channel widget in the Service Console; set your own status to Available to test.

**If deploying on own website:**
- Direct the user to Setup → Embedded Service Deployments → {ESD Name} → **Get Code** to copy the JavaScript snippet. The snippet is org-specific and must be retrieved from Setup — do not attempt to generate or reconstruct it.
- The snippet goes in the `<head>` or before `</body>` of any page where the widget should appear. It must be served over HTTPS.

**Testing checklist (both paths):**
1. Agent responds to a greeting → channel is live
2. Agent answers a question from the knowledge source → grounding is working
3. Agent escalates to a human when asked → RoutingFlow and queue are wired correctly (requires an agent available in Omni-Channel)
4. Widget closes and reopens without losing session → widget state is healthy

## Handoff to Checkpoint 3.5 and Checkpoint 4

After Web Chat provisioning, the flow returns to the spec: Checkpoint 3.5 (silent pre-flight — including Check 3, which verifies the widget is actually placed on the site guest layout) then Checkpoint 4 (embed + go-live, including explicit channel activation and Embedded Service Deployment publish). Those gates live in the spec (`assets/help-agent-spec.md` §4.4–§4.5); do not re-implement them here.
