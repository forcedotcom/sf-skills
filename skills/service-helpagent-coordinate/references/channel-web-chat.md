# Channel branch — Web Chat

> **When to read this file.** Load it only when the user has selected **Web Chat** at Checkpoint 3. If they selected Help Portal or Voice, read the matching `channel-help-portal.md` / `channel-voice.md` instead. You do not need all three channel files in context at once — read only the branch the user chose.

Web Chat embeds a chat widget on a website. This branch provisions a messaging channel + omni-channel routing, a new Embedded Service Deployment (`Help Chat`), and a prepared LWR Experience Cloud site. The agent script does **not** change here — this is channel/site metadata around the agent.

## Step A — Ask for the domain

Ask the user for **the domain** where the widget will live (e.g. `support.acme.com`). This is required — the embedded deployment ties the JavaScript snippet to that domain via a security key, so the snippet cannot be lifted onto an unauthorized site.

## Step B — CRITICAL, DO NOT SKIP: ask who will be chatting

This determines the MessagingChannel's `embeddedConfig.authMode`, which is set when the channel is deployed in Step C below. Choosing wrong silently breaks the deployment: the widget refuses to render on the Setup → ESD → "Test Enhanced Web Chat" page and for any anonymous visitor on the live site, with no error surfaced to the user. This is the single highest-risk decision in the Web Chat branch — previous runs defaulted to `Auth` and shipped a non-functional deployment that took manual debugging to discover. Ask explicitly and confirm the answer back to the user before proceeding.

Present three options:
1. **Public site / anonymous visitors only** → `authMode = UnAuth`.
2. **Both anonymous and authenticated visitors** *(default — recommended for any customer-facing portal)* → `authMode = UnAuth`. Despite the name, `UnAuth` *allows* both: guests chat anonymously, and signed-in users can upgrade the session by passing an `identityToken` at runtime.
3. **Authenticated visitors only** (no guests) → `authMode = Auth`. **Warn the user verbatim:** *"This requires your host app to mint a verified-user JWT for every visitor. The Setup → ESD → 'Test Enhanced Web Chat' button will not work because it loads the widget as a guest, and anonymous visitors on your Experience site will fail to load the chat. Pick this only if you have JWT issuance in place."*

Default to option 2 if the user is unsure. Never silently pick `Auth`. After the channel is deployed in Step C, fetch the MessagingChannel back and assert `embeddedConfig.authMode` matches the chosen value; if it doesn't, surface the discrepancy and stop the Web Chat branch. Always run the post-deploy re-fetch assertion. **The final `report.md` names the chosen `authMode` as a bare value (`authMode: UnAuth`) — do not narrate the rationale or the assertion in the report.** Never emit a legacy `esw.min.js` / Live Agent V1 bootstrap snippet — the V2 widget mounts via the `experience_messaging:embeddedMessaging` LWR component (Step C.3, Checkpoint 3.5 Check 3b).

## Step C — Provision (in order)

1. Deploy the messaging channel + omni-channel routing (`service-digital-engagement-channel-configure`, channel deploys INACTIVE). **Set `embeddedConfig.authMode` from the choice in Step B.** For `UnAuth`, also set `anonymousUserJwtExpirationTime` (e.g. `360`). For `Auth`, set `verifiedUserJwtExpirationTime` (e.g. `60`).
   > **Note on the ASA routing field.** The MessagingChannel field that binds an AgentforceServiceAgent as the session handler is `sessionHandlerAsa` — **not** `sessionHandlerFlow`. If you see `sessionHandlerFlow` in an older template or reference, that's for Flow-backed routing, not agent-backed. `service-digital-engagement-channel-configure` should set `sessionHandlerAsa` when the channel's routing type is `AgentforceServiceAgent`; verify this in the deployed channel before continuing.
2. Activate the MessagingChannel after the agent is Active (and re-verify at Checkpoint 4 — see step 4 below).
3. **Create a NEW Embedded Service Deployment named `Help Chat`** (DeveloperName `HelpChat`, MasterLabel `Help Chat`) bound to the user's domain (`service-digital-engagement-deployment-configure`). **Do NOT re-point or re-use any existing ESD from a prior deployment** — the Experience Builder dropdown must show `Help Chat` as a distinct option that the user can select when dragging the Embedded Messaging component onto the page. If creating the ESD requires a Connect API endpoint that's not available in this org, surface the gap to the user and stop the Web Chat branch — do not silently fall back to mutating an existing deployment.

   > **MANDATORY: Create as V2 (`WebV2`) via the Connect API — never via bare Metadata deploy.** The Metadata API path for `EmbeddedServiceConfig` defaults to legacy V1 (Live Agent-shaped), which shows up in the Setup UI as *"Web (v1)"* with a *"Switch to V2"* button and **does not work with Enhanced Web Chat / MIAW / Agentforce Service Agent routing**. Enhanced Web Chat requires V2. Use the Connect API on API v67.0+ (older versions return 404 for this endpoint):
   >
   > ```http
   > POST /services/data/v67.0/connect/embeddedmessaging/deployment/setup
   > {
   >   "name": "HelpChat",
   >   "masterLabel": "Help Chat",
   >   "deploymentType": "Web",
   >   "clientVersion": "WebV2",
   >   "hostDomain": "<the domain from Step A, e.g. support.acme.com>",
   >   "messagingChannelId": "<18-char MessagingChannel record Id from Step C.1>"
   > }
   > ```
   >
   > **CRITICAL — `messagingChannelId` is REQUIRED and is the single most common cause of an ESD that won't publish.** The `deployment/setup` call only publishes when a messaging channel is bound to it. Omit `messagingChannelId` and the ESD is created but stays **unpublished** — the Setup UI shows the deployment with *Published on:* / *Version:* **empty** and a red banner *"Select a Messaging Channel and then try publishing again."* on the Publish button. This is not fixable by clicking Publish in the UI (there is no channel to select on a V2 deployment there); it must be bound at creation time. Because Step C.1 creates the channel first (INACTIVE), its record Id is already available here — query it and pass it:
   > ```bash
   > sf data query --query "SELECT Id FROM MessagingChannel WHERE DeveloperName = 'HelpChat'" --target-org <alias>
   > ```
   > Also pass `hostDomain` (the domain from Step A) — it ties the widget's security key to that domain.
   >
   > **With the channel bound, the successful response includes `"isPublishSuccess": true` — the ESD is created *and* published in a single call.** There is no separate "publish" step to run afterwards. `EmbeddedServiceConfigPub` (the internal published-snapshot sObject) is not exposed via REST/Tooling/Metadata/Apex, so there is no other supported API to trigger publish; do not attempt bare `sf project deploy start -m EmbeddedServiceConfig:HelpChat` and expect it to publish (it deploys the config but leaves *Published on:* / *Version:* empty, which reads as unpublished in the Setup UI even though `IsEnabled=true`). **If the response comes back with `"isPublishSuccess": false` or the UI shows the "Select a Messaging Channel" banner, the channel was not bound — delete the ESD and recreate with `messagingChannelId` in the body.**
   >
   > If a legacy V1 `HelpChat` ESD already exists (e.g. from a prior run before this fix), **delete it first** (`sf project delete source -m EmbeddedServiceConfig:HelpChat`), then recreate via the Connect API path above — the V1→V2 in-place upgrade is a UI-only "Switch to V2" button that has no supported API equivalent, so recreation is the reliable path.

   > **Note on the auto-generated `<site>` field on the ESD itself.** The Connect API `deployment/setup` call auto-generates an internal site (two rows in `Site`, e.g. `ESW_HelpChat_<timestamp>` and `ESW_HelpChat_<timestamp>1`) for the ESD's own endpoint. Attempting to overwrite the site field via a Metadata deploy fails with an immutable-field error — the ESD's own site cannot be re-pointed. The ESD's endpoint URL (`https://<myDomainStem>.my.site.com/<UrlPathPrefix>`, where `<UrlPathPrefix>` is the row **without** the `vforcesite` suffix) IS the value the V2 LWR component takes as `siteEndpoint` — capture it from `SELECT Name, UrlPathPrefix FROM Site WHERE Name LIKE 'ESW_<EsdDeveloperName>%'` and hand it to Checkpoint 3.5 Check 3(b). **The customer-facing widget on the LWR site is embedded via the `experience_messaging:embeddedMessaging` LWR component in `homeGuestLayout.json` (+ `homeAuthenticated.json` if needed), with a six-attribute `componentAttributes` payload built around `deploymentName: "<EsdDeveloperName>"` and `clientVersion: "WebV2"`.** Do not embed via a bootstrap `<script>` in `mainAppPage.json` `headMarkup`; the correct key is `deploymentName` (not `configurationName`, which is stripped on deploy), and the six-attribute V2 shape round-trips cleanly through metadata deploy/retrieve. See Checkpoint 3.5 Check 3(b) for the full shape and end-to-end path.

   > **Note on patching an existing V2 ESD (guest access, branding, etc.).** Do NOT use the Metadata API to patch an existing V2 ESD — even a no-op deploy that passes the current `site` value unchanged fails with an immutable-field error. Use the **Tooling API** instead: `PATCH /services/data/v67.0/tooling/sobjects/EmbeddedServiceConfig/<id>` with a `{"Metadata": {...}}` body. GET the current `Metadata` object first and include **every** field on the PATCH — omitting `clientVersion`, `branding`, `masterLabel`, or `deploymentType` nulls them out. Successful PATCH returns HTTP 204. Common use cases: setting `areGuestUsersAllowed: true` for a public-visitor site, updating `branding` to point at a customized BrandingSet, or toggling `isTermsAndConditionsEnabled`.

   > **Verifying V2 published state after creation.**
   > - **In the UI:** open Setup → Embedded Service Deployments → **Help Chat**. The title should read *"Embedded Service Deployment Settings - Web"* with **no `(v1)` suffix** and **no "Switch to V2" button**. The top-right should show *"Published on: {date}"* and *"Version: 1"* (not empty).
   > - **Via API:** query the ESD and confirm the underlying metadata has `clientVersion: WebV2`. If `Published on:` is empty in the UI or the response shows `WebV1`, the Connect API path was not taken — delete and recreate.
4. Locate an existing LWR Experience Cloud site (or create one) and prepare it for the user to drop the widget on in Checkpoint 4. **Query-first pattern — do not hardcode a site name:**
   ```sql
   SELECT Id, Name, UrlPathPrefix, SiteType, Status
   FROM Site
   WHERE SiteType = 'ChatterNetworkPicasso'
     AND Status = 'Live'
   ```
   - **Zero Live LWR sites found** → defer to `experience-lwr-site-generate` to create one. Ask the user for a site name and URL path prefix; recommend the *Help Center* template as the natural default for this use case, since it's built around Knowledge browsing + a chat widget.
   - **Exactly one Live LWR site found** → **do not silently use it. Confirm with the user first.** Present the found site (Name + UrlPathPrefix + Id) and ask explicitly: *"Use this existing site for the Help Agent, or create a new one via `experience-lwr-site-generate`?"* — never assume the sole Live site is the right target. On a customer production org, an existing Experience Cloud site may be dedicated to a different audience (partner community, employee portal, marketing site) and wiring the Help Agent onto it would be intrusive. Only proceed once the user has explicitly confirmed which path to take.
   - **Multiple Live LWR sites found** → list them (Name + UrlPathPrefix) and ask the user which one to target. Do not silently pick. Include a "create a new site instead" option in the list.

   Do not filter by any hardcoded site name or `UrlPathPrefix` value — the correct site depends on the customer's org and is not knowable up front.
5. **Wire up knowledge citations.** The script's `knowledge:` block ships with `citations_enabled: True` and `citations_url: ""` (the URL isn't knowable until a site exists). Once the target site's public URL is resolved here, set `citations_url` to that URL so knowledge answers cite working links. If no customer-facing site URL can be resolved, set `citations_enabled: False` instead — do not leave citations enabled with an empty URL, or answers render broken/empty citation links.

## Handoff to Checkpoint 3.5 and Checkpoint 4

After Web Chat provisioning, the flow returns to the spec: Checkpoint 3.5 (silent pre-flight — including Check 3, which verifies the widget is actually placed on the site guest layout) then Checkpoint 4 (embed + go-live, including explicit channel activation and Embedded Service Deployment publish). Those gates live in the spec (`assets/help-agent-spec.md` §4.4–§4.5); do not re-implement them here.
