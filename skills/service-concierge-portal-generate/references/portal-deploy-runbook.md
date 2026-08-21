# Agentforce Concierge portal — deploy runbook

> **When to read this file.** Load it as part of `service-concierge-portal-generate` — read from the skill's entry point after org alias and agent are resolved. Also used by `service-helpagent-coordinate` (Checkpoint 3 → Help Portal branch) via delegation to this skill.

Help Portal deploys an **Agentforce Concierge experience** on an LWR Experience Cloud site: an agent-first landing page with a welcome greeting, prompt bar, suggestion chiclets, and full chat surface. This is different from Web Chat, which embeds a chat *widget* on top of an existing site. The Concierge experience IS the portal.

The agent script does **not** change here — this is channel/site metadata around the agent.

## Execution model — headless with one operator pause

Every step in §A–§S below is executed headlessly via `sf` CLI + Data API + Metadata API + Tooling API. There is exactly **one** step that requires the operator to click a Setup toggle: enabling the **Agentforce Orchestrator** OrgPerm (see §F.4). When the flow reaches that step, pause, present the operator with a direct Setup URL and clear instructions, and wait for them to reply `done` before continuing. Every other Setup-URL fallback in this document is a *last resort* — attempt the headless path first, and only fall back to UI if the headless path returns an unrecoverable error.

If a non-critical step fails (branding polish, suggestion themes, progressive-rendering toggle), log the failure, continue, and surface the gap to the operator at the end. Do NOT abort the deploy for cosmetic gaps.

At the end of the run, print the live customer-facing portal URL for the operator to open in an Incognito window.

---

## §0 — Successful headless path (execute top-to-bottom)

> **This is the runbook.** Execute in order. Only dive into detail sections (§A–§S) if a step fails or you need branch-specific templates.
>
> **Session variables** to capture up front (§A + §C output):
>
> ```bash
> ORG=<sf org alias>                                # e.g. helpportal
> SITE_NAME=<Site Name from §A>                     # e.g. "Skyline Support Center"
> BUNDLE_NAME=<sanitized bundle name>               # ChatterNetworkPicasso name — e.g. Skyline_Support_Center1 (trailing "1")
> WRAPPER_SITE_NAME=<ChatterNetwork wrapper name>   # BUNDLE_NAME with trailing "1" stripped — e.g. Skyline_Support_Center
> NETWORK_ID=<from POST /connect/communities>       # e.g. 0DBgL0000026DJBWA2
> BOT_ID=<Bot's BotDefinition Id>                   # from prior agent-authoring flow
> BOT_DEV_NAME=<Bot DeveloperName>                  # e.g. Help_Agent
> ESC_ID=<EmbeddedServiceConfig Id, auth>           # created in §F.3.a
> GUEST_ESC_ID=<EmbeddedServiceConfig Id, guest>    # single-ESD model: same as ESC_ID; split model: separate
> NSSE_ID=<NetworkSelfServiceExtension Id>          # created in §F.3.b
> SEARCH_CUST_ID=<SearchCustomization Id>           # created in §O.2
> SCRT2_URL=<from ESD Install Code Snippet>         # e.g. https://…my.salesforce-scrt.com
> BASE_SITE_URL=<siteURL from ESD snippet, base>    # e.g. https://…my.site.com
> PUBLISHED_PORTAL_URL=$BASE_SITE_URL/$URL_PATH/    # e.g. https://…my.site.com/skylinesupportcenter/ — trailing slash, NO /s suffix (LWR, not Aura)
> ```
>
> ### Stage-by-stage execution order
>
> | # | Step | Command / surface | Verify |
> |---|---|---|---|
> | 1 | Collect branding + access | §A `AskUserQuestion` × 7 | User confirms values |
> | 2 | Prerequisite check | §B — `GET /connect/communities` returns 200 | JSON has `communities` array |
> | 3 | Provision the site | §C — `POST /connect/communities` | Returns `id` (Network Id) |
> | 4 | Channel + routing + escalation | §E — `sf agent activate` first; if `MESSAGING_CHANNEL_DEV_NAME` not passed in, delegate to `service-digital-engagement-channel-configure` to create the channel (deploy XML with `<sessionHandlerType>AgentforceServiceAgent</sessionHandlerType>` + `<sessionHandlerQueue>` only — `sessionHandlerAsa` is not accepted by the v67 Metadata API); then delegate to `service-agentforce-channel-configure` (Phase 1: queue, Phase 2: Data API PATCH of `SessionHandlerId` + `FallbackQueueId` on the MessagingChannel, Phase 3: escalation question) | SOQL confirms `SessionHandlerId=$BOT_ID`, `FallbackQueueId` set; `BotVersion.Status=Active`; escalation answered by operator |
> | 6 | Retrieve + edit + deploy bundle | §F.0 — retrieve `DigitalExperienceBundle:site/$BUNDLE_NAME`; **edit `sfdc_cms__brandingSet/*/content.json` with the four colors from §A (§D)**; replace home placeholder with 4 Concierge components (empty `attributes: {}`); add `Conversation__c` route + `conversation` view (§F.0.a); flip `authenticationType`; deploy | Retrieve confirms components + route; branding JSON contains user-specified hex values |
> | 7 | Wire Concierge runtime binding | §F.3.a–d — create `EmbeddedServiceConfig` via Connect API `POST /connect/embeddedmessaging/deployment/setup` (same as Web Chat §C.4, omit `hostDomain`; auto-generates `ESW_*` site + test page), insert NSSE, **deploy AND assign** guest permset to Site's `GuestUserId` | `/webruntime/api/…/concierge/config` returns `deploymentName + siteUrl + scrtUrl` **AND** `SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId=<GuestUserId>` returns the `<Bundle>_Guest_Concierge` row |
> | 8 | **⏸ Enable Agentforce Orchestrator (operator pause)** | §F.4 — preflight SOQL on `AgenticCtxtDecorDefinition`; if not supported, pause and ask operator to flip the toggle at the printed Setup URL; wait for `done` reply; then `POST /connect/self-service/setup/agentOrchestrator {name, developerName, agentId}` | Connect GET returns orchestrator with agentId |
> | 9 | Deploy the bundle | §G — `sf project deploy start -m DigitalExperienceBundle:site/$BUNDLE_NAME` | Status: Succeeded |
> | 10 | Publish the site | §I — `POST /connect/communities/$NETWORK_ID/publish`; PATCH `Network.Status=Live` | Site loads at `PUBLISHED_PORTAL_URL` |
> | 11 | Network guest flags | §L.0 — PATCH `Network.OptionsGuestChatterEnabled=true AND OptionsGuestMemberVisibility=true` (single Data API call). ALSO verify auth ESC `AreGuestUsersAllowed=true` — flip via mdapi + republish if false. | `/concierge/config?asGuest=true` returns 200; SOQL confirms both Network flags + ESC flag true |
> | 12 | CORS — 3 writes | §L.1 — 3× `CorsWhitelistEntry` inserts for SCRT2/base/portal URLs | Query returns 3 rows |
> | 13 | Trusted URLs — 3 mdapi records | §L.2 — deploy 3 `CspTrustedSite` records with 6 directives each | SOQL returns 3 rows |
> | 14 | Trusted Domains for Inline Frames | §L.3 — 3× `IframeWhiteListUrl` org-level inserts (`Context=LightningOut`); 2× `SiteIframeWhiteListUrl` on the ChatterNetwork wrapper SiteId | Both queries return rows |
> | 15 | Experience Builder Security — Clickjack + CSP + LWS | §L.4 — `CustomSite:$WRAPPER_SITE_NAME` mdapi flip `clickjackProtectionLevel=AllowAllFraming`; DEB bundle `mainAppPage/content.json` flip `isLockerServiceEnabled=false, isRelaxedCSPLevel=true`; redeploy + republish | Roundtrip retrieve confirms all 3 |
> | 16 | AI Experiences toggles | §M — preflight `AiExperienceContextDefinition` describe (skip section on NOT_FOUND). PATCH `Network.OptionsDataCategoryContextPassingEnabled=true, OptionsSlfSrvcPersonalizationEnabled=false`. | Network PATCHes return 204 |
> | 17 | Bot-routing wiring | §N — 3 writes: `PresenceUserConfigUser` (BotUser → default presence), `GroupMember` (BotUser → fallback queue), `Group.QueueRoutingConfigId` (queue → MessagingSession routing config) | SOQL verify all 3 |
> | 18 | Search Manager Query Configuration | §O — deploy `searchCustomization` mdapi (channel=`LWRExperienceSiteSearch`, `<selectedObject>` for Case/Knowledge__kav/Product2); §O.5 PATCH `NSSE.SearchCustomizationId=$SEARCH_CUST_ID` | Roundtrip retrieve confirms |
> | 19a | S.1 — Member profiles *(only for auth paths)* | §S.1 — 4× `POST /sobjects/NetworkMemberGroup {NetworkId, ParentId=<ProfileId>}` for Customer Community × 4 | SOQL count ≥ 5 (incl. SysAdmin) |
> | 19b | S.2 — Login & Reg + reCAPTCHA | §S.2 — PATCH `NetworkAuthApiSettings` booleans + `RecaptchaScoreThreshold` via Data API | Row PATCHed; SOQL confirms fields |
> | 19c | S.3 — Head Markup verify | §S.3 — grep bundle `mainAppPage/content.json` for `headMarkup` key (default-populated) | Key present |
> | 20 | Publish + Activate (final) | §S.5 — `sf community publish`, then `sf data update record Network.Status=Live` | `Status=Live` + `curl -I` returns HTTP/2 301 |
> | 21 | Smoke verify guest access + print URL | §J + §K — `curl` `/concierge/config` as guest; print `PUBLISHED_PORTAL_URL` and instruct the operator to open it in Incognito | All 3 chatConfig fields populated |
>
> ### The 3 preflight skips (do NOT block deploy if these fire)
>
> - **`AgenticCtxtDecorDefinition` sObject "not supported" AND the operator confirms they cannot enable the Orchestrator right now** → skip §F.4. Bot works via `SessionHandlerId` alone. Prompt bar responses are ungrounded, but chat still routes.
> - **`AiExperienceContextDefinition` sObject NOT_FOUND** → skip §M (older-API orgs). No AI Experiences panel exists.
> - **`SearchCustomization` describe NOT_FOUND** → skip §O (older-API orgs). Chat still works; search corpus falls back to platform default.
>
> ### Steps that require a manual UI touch (log and continue — do NOT abort)
>
> - **§S.4 Progressive Rendering OFF toggle** — UI-only at v67 with no verified metadata surface. Default is empirically OFF on freshly-provisioned bundles — skip on a fresh deploy. If a downstream visual test shows jank, log the step and continue. Fallback: Experience Builder → Settings → Advanced → Progressive Rendering.
> - **§P Smart Search Assistance subagent** — asset lives in a Salesforce-hosted registry; no headless path exists yet. Log the step and continue; chat still works without it (Knowledge grounding path via ADL is unaffected).
>
> ### Critical gotchas the recipe traps for you
>
> 1. **`BUNDLE_NAME` (e.g. `Skyline_Support_Center1`) vs `WRAPPER_SITE_NAME` (`Skyline_Support_Center`)** — the DEB Picasso bundle has the `*1` suffix; the ChatterNetwork wrapper site does NOT. `CustomSite:$BUNDLE_NAME` returns an empty package; only `CustomSite:$WRAPPER_SITE_NAME` retrieves the `.site` XML.
> 2. **Never inject credential attributes (`conversationPage`, `Org_ID`, `siteURL`, `scrt2URL`) on `conciergePromptBar`/`conciergeChat`/`conciergeChicletGroupContainer`** — v67 DEB pipeline strips them silently. Runtime resolves credentials from ESC + NSSE + Site + Network. Two attributes on `conciergeWelcomeGreeting` are valid: `textAlignment` and `customGreeting`.
> 3. **Route `urlPrefix` MUST be `conversation`, NOT `concierge`** — `conciergePromptBar` hardcodes submit navigation to `routeType=concierge-conversation` / `urlPrefix=conversation`. Renaming causes "Invalid Page" on prompt-bar submit.
> 4. **`CspTrustedSite` v67 accepts only 6 directive booleans** — `connect-src`, `font-src`, `frame-src`, `img-src`, `media-src`, `style-src`. Adding others fails deploy with schema error.
> 5. **`OptionsGuestChatterEnabled` AND `OptionsGuestMemberVisibility` both default to False on freshly-POSTed Networks** — always PATCH BOTH to True in §L.0, not conditionally. Also verify `EmbeddedServiceConfig.AreGuestUsersAllowed=true` on the auth ESC. These three flags are necessary but NOT sufficient — the §F.3.d guest permset must also be assigned to the site's Guest User.
> 6. **Republish is mandatory after DEB flag changes** — `isRelaxedCSPLevel` / `isLockerServiceEnabled` / `headMarkup` / `authenticationType` do not reach the runtime until `POST /connect/communities/$NETWORK_ID/publish` completes. Deploy alone is insufficient.
>
> ### If the recipe fails: which section to dive into
>
> - Deploy fails / schema error / bundle-shape confusion → §F.0 (full JSON templates)
> - Guest `/concierge/config` returns 401 → §L.0 first, then §F.3 wiring
> - `/conversation/guest` is BLANK in Incognito but `/concierge/config` returns 200 → run BOTH checks in order: (a) §L.0 THREE-flag check, (b) §F.3.d permset check — confirm the site's Guest User has the `<Bundle>_Guest_Concierge` PermissionSetAssignment
> - Guest `/concierge/config` returns 200 but prompt bar says "Agents are not available" → §N (bot-routing wiring)
> - Prompt bar submit lands on "Invalid Page" → §F.0.a (Conversation route/view templates)
> - Chat responds in Incognito but blank in SysAdmin session → expected, not a bug (see anti-patterns table)

---

## Step A — Collect branding + access

Ask each question via `AskUserQuestion`, one at a time, in the order below. This mirrors the Salesforce Quick Setup wizard's Branding + Login panels.

**Every color field — Primary Color, Text Color, Border Color, Page Background Color — is mandatory. The assistant MUST ask all four, in order, one at a time. Do not skip any. Do not silently apply defaults. Logo is handled separately in §D.1 and is NOT asked in this flow.**

**Two-option shape for every color question.** Each `AskUserQuestion` for the four colors MUST present **exactly two options**. The harness renders an *Other* free-text input on every question automatically — that is where custom hex values are typed; it is **not** a third option.

- Option 1: *"Use default `<value>`"* — accepts the stock value.
- Option 2: *"Type a custom value"* — the user provides a hex via the *Other* free-text input.

Validate hex responses against `^#[0-9a-fA-F]{6}$`. If invalid, re-ask.

1. **Site Name** — required, free text.
   - Example: `Skyline Support Center`
   - Used for the Connect API `communities` POST body (`name` field).
   - Derive the URL path prefix by sanitizing → **alphanumeric only, no dashes, no spaces** (e.g. `Skyline Support Center` → `skylinesupportcenter`). The Connect API rejects any other characters with `INVALID_INPUT: The URL can only contain alphanumeric characters.`

2. **Primary Color** — mandatory. Default `#066afe`.

3. **Text Color** — mandatory. Default `#181818`.

4. **Border Color** — mandatory. Default `#e5e5e5`.

5. **Page Background Color** — mandatory. Default `#ffffff`.

6. **Visitor access** — mandatory `AskUserQuestion` with two options; drives Step E's `authMode` **and** the `authenticationType` field on the site config in Step F.0.
   - *"Public access — guests and authenticated visitors (Recommended)"* → `authMode = UnAuth`, `authenticationType = AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED`.
   - *"Authenticated visitors only (no guests)"* → `authMode = Auth`, `authenticationType = AUTHENTICATED`. Follow up with the same JWT-configuration `AskUserQuestion` documented in `channel-web-chat.md` Step B.

   There is no "anonymous only" mode — `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED` accepts both guests and logged-in users. The legacy `UNAUTHENTICATED` value is not recommended and must not be offered.

**Confirm the collected values back to the user before starting deploy.** Present as a single summary block and give them one chance to change any field.

## Step B — Prerequisite check

Before provisioning, verify the org has:

- **Digital Experiences enabled.** Definitive headless signal: `GET /services/data/v67.0/connect/communities` returns 200 with a JSON body containing a `communities` array. HTTP 404 or a `NOT_FOUND` payload means Digital Experiences is disabled. Enabling the feature is a Setup-UI-only one-time-per-org step on v67 — on any trial/SDO/SDO-Lite org this is pre-enabled; on a clean Developer Edition it isn't. Hard-fail with the setup URL fallback: `<INSTANCE_LIGHTNING_URL>/lightning/setup/CommunitiesSettings/home`.
- **Experience Cloud** enabled (Communities license active).
- **Agentforce** enabled — required for the Concierge components to render.
- **Data Cloud** enabled and permission sets assigned to the running user (the coordinate skill's readiness check at §4.0 handles this; do not re-run here).
- **Knowledge** enabled with published articles — the Concierge prompt bar and chat surface both need Knowledge to answer.

If any prerequisite fails, hard-stop and surface the specific gap.

## Step C — Provision the Experience Cloud site

Create a new LWR site via Connect API — **always** use the *Build Your Own (LWR)* template. Do not use the *Help Center* template (it's Aura-based and won't host Concierge components).

Construct the `description` from context before the POST: `"Agentforce Concierge portal for <Site Name>, powered by the <BOT_DEV_NAME> agent."` (e.g. `"Agentforce Concierge portal for Claude Skill Testing, powered by the Yoda agent."`).

```bash
SITE_DESCRIPTION="Agentforce Concierge portal for $SITE_NAME, powered by the $BOT_DEV_NAME agent."

sf api request rest "/services/data/v67.0/connect/communities" \
  --method POST \
  --body "{
    \"name\": \"$SITE_NAME\",
    \"urlPathPrefix\": \"$URL_PATH\",
    \"templateName\": \"Build Your Own (LWR)\",
    \"description\": \"$SITE_DESCRIPTION\"
  }" \
  --target-org $ORG
```

> **`urlPathPrefix` is alphanumeric-only.** No dashes, no underscores, no spaces.

Site creation is async. The Connect API returns a `jobId`; poll `BackgroundOperation` until `Status = Complete`:

```bash
sf data query --target-org $ORG --json --query \
  "SELECT Id, Status, Error FROM BackgroundOperation WHERE Id='<job-id>'"
```

**Resolve the bundle name.** Salesforce creates two Site rows and one Network — the LWR Site has `1` appended to the sanitized site name with `SiteType = 'ChatterNetworkPicasso'`; the non-`1` Site is the vforcesite wrapper (`ChatterNetwork`) and is not what you edit. Confirm both via SOQL, then keep only the Picasso Id:

```bash
sf data query --target-org $ORG --json --query \
  "SELECT Id, Name, SiteType, UrlPathPrefix FROM Site WHERE UrlPathPrefix='<sanitized-url-path>'"
```

**Set the Site description.** The Connect API `description` field populates `Network.Description`, not `Site.Description`. Setup → All Sites shows `Site.Description`, so patch it explicitly on the Picasso Site after the SOQL above resolves `$PICASSO_SITE_ID`:

```bash
sf data update record -o $ORG --sobject Site --record-id $PICASSO_SITE_ID \
  --values "Description='$SITE_DESCRIPTION'"
```

**Verify the site is LWR before proceeding.** After `BackgroundOperation` completes, confirm the new bundle appears under `DigitalExperienceBundle` — NOT `ExperienceBundle`. If it only appears under `ExperienceBundle` the wrong template was used (an Aura site was created) and you must delete it via Setup → All Sites and recreate with `templateName: "Build Your Own (LWR)"`:

```bash
sf org list metadata --metadata-type DigitalExperienceBundle --target-org $ORG --json | python3 -c "
import sys,json
names=[r['fullName'] for r in json.load(sys.stdin).get('result',[])]
target='site/$BUNDLE_NAME'
print('✅ LWR confirmed' if target in names else '❌ NOT a DEB — wrong template, delete and recreate')
"
```

- Newer orgs (Summer '25+): site appears under **`DigitalExperienceBundle`** → §F.0 path.
- Legacy orgs: site appears under **`ExperienceBundle`** only → §F.1 path (this is expected for pre-Summer '25 orgs, not an error).

Store the metadata type and full name in `$BUNDLE_TYPE` and `$BUNDLE_NAME`.

## Step D — Apply branding

Best-effort branding. If any of the writes below fails, log the failure, continue the deploy, and surface the gap to the operator at the end — do NOT abort.

**Apply colors during the Step F bundle edit — not as a separate deploy.** The four colors from §A live in `sfdc_cms__brandingSet/<themeName>/content.json` inside the retrieved DEB bundle. Edit this file **in the same pass** as the home-page Concierge component injection, before the single Step G deploy. Doing it as a separate deploy wastes a round-trip.

**Color → brandingSet field mapping:**

| §A field | `content.json` key |
|---|---|
| Primary Color | `PrimaryAccentColor` |
| Text Color | `TextColor` |
| Border Color | `_NeutralColor` |
| Page Background Color | `BackgroundColor` |

Edit those four keys in `sfdc_cms__brandingSet/<themeName>/content.json`. Leave all other keys unchanged. The theme name is whatever directory exists under `sfdc_cms__brandingSet/` in the retrieved bundle (e.g. `Build_Your_Own_LWR`).

**Logo:**

Leave `SiteLogo` and `_SiteLogoUrl` as empty strings — the Concierge page renders without a logo. See §D.1 for the optional logo branch if a custom logo is needed.

If a branding step fails at runtime: deploy the portal without branding and note "Apply branding via Experience Builder → Branding" in the operator handoff.

## Step E — Bind the agent via MessagingChannel

> **⚠️ Bot provisioning prerequisite — the Bot MUST be created via the Setup wizard's "From Template" path, not via a headless Metadata deploy or direct `POST /sobjects/BotDefinition`.** A Bot created outside the wizard has `BotDefinition.AgentTemplate=null` and is silently excluded from the Agentforce Orchestrator's Add Tool → Agent picker. The field is not writeable via any public API — the only recovery is to **delete the Bot and recreate it via Setup → Agentforce Agents → New Agent → From Template → Agentforce Service Agent**. Assume the Bot pre-exists (created by the user via the wizard).

This step provisions the MessagingChannel and wires the agent's routing and escalation. **This skill owns none of that work** — it delegates entirely to `service-digital-engagement-channel-configure` (channel infrastructure) and `service-agentforce-channel-configure` (queue, routing, escalation). This ensures queue and escalation questions are always asked by the right skills, not silently resolved here.

**Substep 1 — Activate the Bot first (always).**

```bash
sf agent activate -o $ORG --api-name $BOT_DEV_NAME
```

Verify `BotVersion.Status = Active` before continuing. The channel PATCH is rejected with "Only active Agentforce Service Agents are supported" if the bot is inactive.

**Substep 2 — Resolve or create the MessagingChannel.**

Branch on whether `MESSAGING_CHANNEL_DEV_NAME` was passed in:

- **Passed in:** verify the channel exists, is Active, and is bound to this agent:
  ```bash
  sf data query --target-org $ORG --json \
    --query "SELECT Id, DeveloperName, IsActive, SessionHandlerId FROM MessagingChannel WHERE DeveloperName='$MESSAGING_CHANNEL_DEV_NAME'"
  ```
  If Active and `SessionHandlerId = $BOT_ID` → capture `MESSAGING_CHANNEL_ID` and skip to Substep 3.
  If not Active or not bound to this agent → treat as not passed in and delegate below.

- **Not passed in:** delegate to **`service-digital-engagement-channel-configure`** to create the channel. Pass:
  - Org: `$ORG`
  - Channel type: `EmbeddedMessaging`
  - Agent DeveloperName: `$BOT_DEV_NAME`
  - `authMode`: from Step A #7 (`UnAuth` for access options 1/2; `Auth` for option 3)

  On completion, capture `MESSAGING_CHANNEL_DEV_NAME` and `MESSAGING_CHANNEL_ID`.

**Substep 3 — Wire routing and escalation.**

Delegate to **`service-agentforce-channel-configure`** (all three phases). Pass:
- Org: `$ORG`
- Agent DeveloperName: `$BOT_DEV_NAME`
- Channel type: Enhanced Chat (EmbeddedMessaging)
- MessagingChannel DeveloperName: `$MESSAGING_CHANNEL_DEV_NAME`

That skill will:
- Phase 1: resolve or create the fallback queue
- Phase 2 Branch A: bind the agent via Data API PATCH — `sessionHandlerAsa` is NOT accepted by the v67 Metadata API, so the channel XML is deployed with only `<sessionHandlerType>AgentforceServiceAgent</sessionHandlerType>` + `<sessionHandlerQueue>`, then bound via `sf api request rest --method PATCH -o $ORG "/services/data/v67.0/sobjects/MessagingChannel/<CHAN_ID>" --body "{\"SessionHandlerId\":\"<BOT_ID>\",\"FallbackQueueId\":\"<QUEUE_ID>\"}"`. Bot must be Active before the PATCH. Verify `SessionHandlerId` + `FallbackQueueId` non-null via SOQL.
- Phase 3: ask the operator about outbound escalation and wire the `connection customer_web_client:` block if requested

## Step F — Deploy Concierge components into the bundle

> **Successful headless path (one recipe, run top-to-bottom):**
>
> 1. **Welcome Greeting + Prompt Bar + Chiclet on Home** → three `runtime_service_concierge:*` components inside `sfdc_cms__view/home/content.json`. Set `textAlignment` and `customGreeting` on `conciergeWelcomeGreeting`. **Do NOT populate credential attributes** on `conciergePromptBar`/`conciergeChicletGroupContainer` — v67 DEB strips them. `conciergeChat` goes on the Conversation page only. See §F.0 for the JSON snippets.
> 2. **Link prompt bar to Query Configuration** → does NOT live on the component. Lives on `NetworkSelfServiceExtension.SearchCustomizationId` (per-Network row). Recipe in §O.5.
> 3. **Concierge Conversation page** → `sfdc_cms__route/Conversation__c/` + `sfdc_cms__view/conversation/`. **`urlPrefix` must be `conversation`, not `concierge`.** Copy both directories from a working reference bundle (see §F.0.a); do NOT hand-author the stringly-typed JSON.
> 4. **Credentials on `conciergeChat`** → **no-op at the metadata layer**. Runtime resolves Org_ID / ESD_Developer_Name / siteURL / scrt2URL from `EmbeddedServiceConfig` + `NetworkSelfServiceExtension` + `Site` + `Network` at page-render time.
> 5. **Concierge Sidebar in Theme Footer** → add `runtime_service_concierge:conciergeNavigationBar` to the `footer` region of `sfdc_cms__themeLayout/scopedHeaderAndFooter/content.json`. See §F.0 for the JSON shape.
>
> The whole stage is a single mdapi deploy of the bundle (Step G) + one NSSE PATCH (§O.5).

**The retrieve/edit shape depends on `$BUNDLE_TYPE` from Step C.** `sf project retrieve start` must run from a valid SFDX project workspace (`sfdx-project.json` at cwd or above).

### F.0 — DigitalExperienceBundle path *(newer orgs — Summer '25+ CMS-based LWR)*

Retrieve:

```bash
sf project retrieve start --metadata "DigitalExperienceBundle:site/$BUNDLE_NAME" --target-org $ORG
```

The bundle lands at `force-app/main/default/digitalExperiences/site/$BUNDLE_NAME/` with these sub-directories: `sfdc_cms__appPage/`, `sfdc_cms__view/`, `sfdc_cms__route/`, `sfdc_cms__theme/`, `sfdc_cms__brandingSet/`, `sfdc_cms__site/`, plus a top-level `.digitalExperience-meta.xml`.

**Component JSON shape is different from the classic ExperienceBundle:**

- Component identifier field is `"definition"`, **not** `"componentName"`.
- Components live in nested `children` arrays under section → column → region → root, not in a flat `components` array.
- IDs are full UUIDs (36 chars with dashes). Generate with `python3 -c 'import uuid; print(uuid.uuid4())'` or `uuidgen`.
- No `renderPriority` or `renditionMap` fields.

**Guest access — headless via site-level `authenticationType`.**

| Aspect | Value |
|---|---|
| Metadata type | `DigitalExperienceBundle` |
| Bundle member | `sfdc_cms__site/$BUNDLE_NAME/content.json` |
| Field | `contentBody.authenticationType` (string enum, required) |
| Deploy | `sf project deploy start --metadata "DigitalExperienceBundle:site/$BUNDLE_NAME"` (Step G) |
| Activation | Deploy alone doesn't push the flag to the runtime — Step I's publish + `Network.Status=Live` PATCH does. |

The retrieved file ships with `"authenticationType" : "AUTHENTICATED"`. Change it to the value driven by Step A #7:

```json
{
  "type" : "sfdc_cms__site",
  "title" : "<Site Name>",
  "contentBody" : {
    "authenticationType" : "AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED"
  },
  "urlName" : "<sanitized-url-path>"
}
```

Valid enum values:

| Value | Meaning | When to set |
|---|---|---|
| `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED` | Site accepts both guests and authenticated users. | Step A #7 option 1 (UnAuth) — the recommended default |
| `AUTHENTICATED` | Login required. Guests bounced to `/login`. | Step A #7 option 2 (Auth-only) |
| `UNAUTHENTICATED` | Legacy public-only site. Not recommended. | Never |

**Home page — edit `sfdc_cms__view/home/content.json`.** The bundle ships with a placeholder `community_builder:htmlEditor` inside the first column of the `content` region. Replace that placeholder's `children` array with these three Concierge components:

```json
"children" : [ {
  "attributes" : {
    "textAlignment" : "center",
    "customGreeting" : "Welcome! How can I help you today?"
  },
  "definition" : "runtime_service_concierge:conciergeWelcomeGreeting",
  "id" : "<uuid-1>",
  "type" : "component"
}, {
  "attributes" : { },
  "definition" : "runtime_service_concierge:conciergePromptBar",
  "id" : "<uuid-2>",
  "type" : "component"
}, {
  "attributes" : { },
  "definition" : "runtime_service_concierge:conciergeChicletGroupContainer",
  "id" : "<uuid-3>",
  "type" : "component"
} ]
```

> **⚠️ `conciergeChat` must NOT appear on the Home page.** It belongs only on the Conversation page (`sfdc_cms__view/conversation/content.json`). Adding it to Home renders the full chat UI on every page load, breaking the portal flow.
>
> **⚠️ Credential attributes are blocked on v67 orgs.** Do not attempt to inject `conversationPage`, `Org_ID`, `siteURL`, `scrt2URL`, or any credential attribute on `conciergePromptBar`, `conciergeChat`, or `conciergeChicletGroupContainer` — the v67 DEB metadata pipeline strips them silently. Only two attributes on `conciergeWelcomeGreeting` survive: `textAlignment` and `customGreeting`. Font attributes (`fontFamily`, `fontSize`, `fontWeight`) are also stripped silently.

**Theme Footer — add `conciergeNavigationBar` to `sfdc_cms__themeLayout/scopedHeaderAndFooter/content.json`.** The Concierge Sidebar (history / navigation) lives in the Theme Footer, not on a page view. Edit the `footer` region to add a `community_layout:section` containing a `footerSection` column region with the component:

```json
{
  "id": "<footer-region-uuid>",
  "name": "footer",
  "title": "Theme Footer",
  "type": "region",
  "children": [ {
    "attributes": {
      "sectionConfig": "{\"UUID\":\"<section-uuid>\",\"columns\":[{\"UUID\":\"<col-uuid>\",\"columnName\":\"Column 1\",\"columnKey\":\"col1\",\"columnWidth\":\"12\",\"seedComponents\":null}]}"
    },
    "children": [ {
      "children": [ {
        "attributes": {},
        "definition": "runtime_service_concierge:conciergeNavigationBar",
        "id": "<component-uuid>",
        "type": "component"
      } ],
      "id": "<col-uuid>",
      "name": "footerSection",
      "title": "Theme Footer",
      "type": "region"
    } ],
    "definition": "community_layout:section",
    "id": "<section-uuid>",
    "type": "component"
  } ]
}
```

Replace `<footer-region-uuid>`, `<section-uuid>`, `<col-uuid>`, and `<component-uuid>` with fresh UUIDs (`uuidgen`). Note: `<section-uuid>` and `<col-uuid>` appear twice each — once in `sectionConfig` (the stringified JSON) and once as the `id` field on the corresponding component/region. They must match.

### F.0.a — Conversation route + view (inline templates — no reference bundle needed)

The prompt bar's submit navigates to `routeType=concierge-conversation` with `urlPrefix=conversation`. Without a matching route + view in the bundle, LWR returns "Invalid Page" on submit.

**Do not copy from a reference bundle** — use the verified templates below directly.

**`sfdc_cms__route/Conversation__c/content.json`:**
```json
{
  "type": "sfdc_cms__route",
  "title": "Conversation",
  "contentBody": {
    "activeViewId": "conversation",
    "configurationTags": [],
    "pageAccess": "UseParent",
    "routeType": "concierge-conversation",
    "urlPrefix": "conversation"
  },
  "urlName": "conversation"
}
```

**`sfdc_cms__route/Conversation__c/_meta.json`:**
```json
{"apiName":"Conversation__c","type":"sfdc_cms__route","path":"routes"}
```

**`sfdc_cms__view/conversation/content.json`** — replace `<uuid-chat>`, `<uuid-seo>`, and `<uuid-content-region>` with fresh UUIDs (`uuidgen`). All three must be unique across the entire file. The remaining UUID constants (`sectionConfig`, section `id`, column region `id`, root component `id`) are stable structural anchors and can be reused as-is across deployments:
```json
{
  "type": "sfdc_cms__view",
  "title": "Conversation",
  "contentBody": {
    "component": {
      "children": [
        {
          "children": [
            {
              "attributes": {
                "backgroundImageConfig": "",
                "backgroundImageOverlay": "rgba(0,0,0,0)",
                "componentSpacerSize": "",
                "layoutDirectionDesktop": "row",
                "layoutDirectionMobile": "column",
                "layoutDirectionTablet": "column",
                "maxContentWidth": "",
                "sectionColumnGutterWidth": "",
                "sectionConfig": "{\"UUID\":\"3a36dbf4-ea89-4538-a9a8-9395d75df15f\",\"columns\":[{\"UUID\":\"6005d4c3-89cc-4a96-ab13-20d6104c6ec6\",\"columnName\":\"Column 1\",\"columnKey\":\"col1\",\"columnWidth\":\"12\",\"seedComponents\":null}]}",
                "sectionMinHeight": "",
                "sectionVerticalAlign": "flex-start"
              },
              "children": [
                {
                  "children": [
                    {
                      "attributes": {},
                      "definition": "runtime_service_concierge:conciergeChat",
                      "id": "<uuid-chat>",
                      "type": "component"
                    }
                  ],
                  "id": "6005d4c3-89cc-4a96-ab13-20d6104c6ec6",
                  "name": "col1",
                  "title": "Column 1",
                  "type": "region"
                }
              ],
              "definition": "community_layout:section",
              "id": "3a36dbf4-ea89-4538-a9a8-9395d75df15f",
              "type": "component"
            }
          ],
          "id": "<uuid-content-region>",
          "name": "content",
          "title": "Content",
          "type": "region"
        },
        {
          "children": [
            {
              "attributes": {
                "customHeadTags": "",
                "description": "",
                "pageTitle": "Conversation",
                "recordId": "{!recordId}"
              },
              "definition": "community_builder:seoAssistant",
              "id": "<uuid-seo>",
              "type": "component"
            }
          ],
          "id": "7e6fea67-e160-4002-9dba-c0eecd4508c4",
          "name": "sfdcHiddenRegion",
          "title": "sfdcHiddenRegion",
          "type": "region"
        }
      ],
      "definition": "community_layout:sldsFlexibleLayout",
      "id": "c4679f2c-19e8-4d49-a196-440a40533f0c",
      "type": "component"
    },
    "dataProviders": [],
    "themeLayoutType": "Inner",
    "viewType": "concierge-conversation"
  },
  "urlName": "conversation"
}
```

**`sfdc_cms__view/conversation/_meta.json`:**
```json
{"apiName":"conversation","type":"sfdc_cms__view","path":"views"}
```

> **Common sub-errors:** (a) `routeType=home` on the route is wrong — must be `concierge-conversation`; (b) `viewType` must match `routeType` exactly; (c) the `sfdcHiddenRegion` with `community_builder:seoAssistant` is required — omitting it causes a deploy schema error.

Verify post-publish: `curl -sSL -w "HTTP=%{http_code}\n" "$PUBLISHED_PORTAL_URL/conversation" -o /dev/null` should chain 301 → 200.

### F.1 — ExperienceBundle path *(legacy orgs, pre-Summer '25)*

Retrieve:

```bash
sf project retrieve start --metadata "ExperienceBundle:$BUNDLE_NAME" --target-org $ORG
```

Edit `experiences/$BUNDLE_NAME/views/home.json`. Add three components at the beginning of the `content` region's `components` array:

```json
{
  "componentAttributes": {
    "textAlignment": "center",
    "customGreeting": "Welcome! How can I help you today?"
  },
  "componentName": "runtime_service_concierge:conciergeWelcomeGreeting",
  "id": "<16-char-hex>",
  "renderPriority": "NEUTRAL",
  "renditionMap": {},
  "type": "component"
},
{
  "componentAttributes": {},
  "componentName": "runtime_service_concierge:conciergePromptBar",
  "id": "<16-char-hex>",
  "renderPriority": "NEUTRAL",
  "renditionMap": {},
  "type": "component"
},
{
  "componentAttributes": {},
  "componentName": "runtime_service_concierge:conciergeChicletGroupContainer",
  "id": "<16-char-hex>",
  "renderPriority": "NEUTRAL",
  "renditionMap": {},
  "type": "component"
}
```

Generate a fresh 16-char hex `id` per component (`openssl rand -hex 8`).

### F.2 — Conversation page: full chat surface *(ExperienceBundle path only)*

Create two files inside the retrieved bundle.

**`routes/conversationPage.json`**:

```json
{
  "activeViewId": "<view-uuid>",
  "appPageId": "<use-appPageId-from-home.json>",
  "configurationTags": [],
  "devName": "Conversation_Page__c",
  "id": "<16-char-hex>",
  "label": "Conversation Page",
  "pageAccess": "UseParent",
  "routeType": "concierge-conversation",
  "type": "route",
  "urlPrefix": "concierge-chat"
}
```

**`views/conversationPage.json`** — hosts `conciergeChat` in the `content` region. Copy the full six-region skeleton (`header`, `content`, `footer`, `sfdcHiddenRegion`, `sidebar`, `sidebarAlt`) from an existing view file in the retrieved bundle, then drop this component into `content`:

```json
{
  "componentAttributes": {},
  "componentName": "runtime_service_concierge:conciergeChat",
  "id": "<16-char-hex>",
  "renderPriority": "NEUTRAL",
  "renditionMap": {},
  "type": "component"
}
```

Also set: `themeLayoutType: "Inner"`, `componentName: "siteforce:sldsThreeCol363Layout"`, `viewType: "concierge-conversation"`.

The route's `activeViewId` must match the view's `id`. The `appPageId` on both must match the one from `home.json`.

### F.3 — Wire the Concierge runtime binding *(required)*

Four artifacts must exist for the LWR runtime endpoint (`/webruntime/api/services/data/vXX.X/connect/self-service/concierge/config`) to resolve. All four are fully headless.

1. **`EmbeddedServiceConfig` (ESC)** — created via Connect API, same path as Web Chat.
2. **`NetworkSelfServiceExtension` (NSSE)** — a runtime record linking the Network to the ESC.
3. **PermissionSet + assignment** — the site's guest user must have read access on the objects the endpoint joins through.
4. **Republish** — the LWR runtime caches the binding at publish time.

**F.3.a — Resolve the EmbeddedServiceConfig.**

**Branch: was `ESC_ID` passed in by the calling skill?**

- **Yes (passed in):** query the org to confirm the ESC exists:
  ```bash
  sf data query -o $ORG --use-tooling-api \
    -q "SELECT Id, DeveloperName, AreGuestUsersAllowed FROM EmbeddedServiceConfig WHERE Id='$ESC_ID'" --json
  ```
  Capture `ESC_DEV_NAME` and proceed to F.3.b. Verify `AreGuestUsersAllowed=true`; if false, patch it via Tooling API before continuing (see §L.0).

- **Not passed in:** delegate to **`service-digital-engagement-deployment-configure`** with these inputs:

- **Operation**: `create`
- **Deployment type**: `Web`
- **Deployment name / DeveloperName**: `<Bundle>_Concierge` (e.g. `Einstein_Support_Center1_Concierge`) / MasterLabel `<Site Name> Concierge`
- **Channel**: MessagingChannel DeveloperName from Step E (skill will query the record Id)
- **hostDomain**: the org's `*.my.site.com` hostname — query it from any existing Site: `SELECT UrlPathPrefix, SiteType FROM Site WHERE SiteType='ChatterNetworkPicasso' LIMIT 1` and derive the base domain from its URL, or read it from `sf org display` instance URL replacing `.salesforce.com` with `.my.site.com` (e.g. `trailsignup-ca7498a0804351.my.site.com`)

The skill creates the ESD via `POST /connect/embeddedmessaging/deployment/setup` (V2, Connect API), binds the messaging channel at creation time so `isPublishSuccess: true` is returned, and auto-generates the `ESW_*` scaffolding site and test page in Setup → Embedded Service Deployments.

After the skill completes, capture the ESC Id:

```bash
ESC_ID=$(sf data query -o $ORG --use-tooling-api \
  -q "SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='<Bundle>_Concierge'" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
```

**F.3.b — Insert the NSSE record (standard REST DML).**

```bash
NETWORK_ID=$(sf data query -o $ORG -q "SELECT Id FROM Network WHERE Name='<Site Name>' LIMIT 1" --json | jq -r '.result.records[0].Id')
# Guard: abort if NETWORK_ID is unset or null — an empty NetworkId causes a 400 at smoke-test time with no obvious link back to NSSE
if [ -z "$NETWORK_ID" ] || [ "$NETWORK_ID" = "null" ]; then
  echo "ERROR: NETWORK_ID not resolved. Verify the Network exists and Name matches exactly." >&2; exit 1
fi

sf data create record -o $ORG --sobject NetworkSelfServiceExtension \
  --values "DeveloperName=<Bundle>_Concierge MasterLabel='<Site Name> Concierge' NetworkId=$NETWORK_ID Language=en_US"
```

**F.3.c — Bind NSSE → ESC via Tooling PATCH.** For UnAuth sites (Step A #7 options 1 & 2), set `GuestEmbeddedServiceCnfgId`. For Auth-only sites (option 3), set `EmbeddedServiceCnfgId`. Setting **both** to the same value fails with `INVALID_INPUT: Select different deployments for guest and authenticated users`.

```bash
NSSE_ID=$(sf data query -o $ORG -q "SELECT Id FROM NetworkSelfServiceExtension WHERE NetworkId='$NETWORK_ID' LIMIT 1" --json | jq -r '.result.records[0].Id')
ESC_ID=<from F.3.a>

# UnAuth (guest-facing)
sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v67.0/tooling/sobjects/NetworkSelfServiceExtension/$NSSE_ID" \
  --body "{\"GuestEmbeddedServiceCnfgId\":\"$ESC_ID\"}"
```

HTTP 204 = success.

**F.3.d — 🚨 CRITICAL: Grant the site's guest user read on the runtime-config objects.** Deploy a `PermissionSet` (Guest User License is compatible — do **not** use `Enhanced Chat User`, which requires a license the guest profile can't hold) and assign it to the guest user.

> **Missing this step is the single most-common cause of blank `/conversation/guest` when §L.0's three flags are already True.** A PermissionSet that exists but isn't assigned to the Site's `GuestUserId` has zero effect — both `sf project deploy start` AND `sf data create record` must run.

Create `force-app/main/default/permissionsets/<Bundle>_Guest_Concierge.permissionset-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <hasActivationRequired>false</hasActivationRequired>
    <label><Bundle> Guest Concierge</label>
    <objectPermissions>
        <allowRead>true</allowRead>
        <object>EmbeddedServiceConfig</object>
    </objectPermissions>
    <objectPermissions>
        <allowRead>true</allowRead>
        <object>MessagingChannel</object>
    </objectPermissions>
    <objectPermissions>
        <allowRead>true</allowRead>
        <object>NetworkSelfServiceExtension</object>
    </objectPermissions>
    <objectPermissions>
        <allowRead>true</allowRead>
        <object>BrandingSet</object>
    </objectPermissions>
</PermissionSet>
```

Deploy and assign:

```bash
sf project deploy start -o $ORG --metadata "PermissionSet:<Bundle>_Guest_Concierge"

GUEST_USER_ID=$(sf data query -o $ORG -q "SELECT GuestUserId FROM Site WHERE Name='<LWR Site Name>'" --json | jq -r '.result.records[0].GuestUserId')
PSET_ID=$(sf data query -o $ORG -q "SELECT Id FROM PermissionSet WHERE Name='<Bundle>_Guest_Concierge'" --json | jq -r '.result.records[0].Id')

sf data create record -o $ORG --sobject PermissionSetAssignment \
  --values "AssigneeId=$GUEST_USER_ID PermissionSetId=$PSET_ID"
```

**F.3.e — Republish.** The LWR runtime caches the ESC/NSSE binding at publish time. Re-run Step I's publish + `Network.Status=Live` PATCH after F.3.a-d.

**F.3.f — Verify.** Use the LWR runtime proxy (`/webruntime/api/...`), **not** `/services/data/...` — the latter returns `Error querying NetworkSelfServiceExtension FK fields` under guest identity even when everything is wired.

```bash
curl -sS "$PUBLISHED_PORTAL_URL/webruntime/api/services/data/v67.0/connect/self-service/concierge/config?language=en-US&asGuest=false&htmlEncode=false" \
  | jq '.chatConfig | {deploymentName, siteUrl, scrtUrl}'
```

All three fields must be non-null. If `deploymentName` is null, the bound ESC references a different site or MessagingChannel — verify the `<site>` in the ESC metadata is the LWR site (F.3.a).

### F.4 — Wire the Agentforce Orchestrator *(one operator pause, then fully headless)*

The Agentforce Orchestrator provides the personalized greeting, Action/Object recommendations, and Concierge proactive routing. The "Enable Agentforce Orchestrator" OrgPerm gates the agent-binding surfaces (Connect POST, Data API sObject, SOQL). Detect the toggle state with a SOQL write-probe, prompt one manual click if off, then continue fully headless.

**F.4.0 — Detection preflight.**

Run the probe up to **2 times** before concluding the toggle is off. The `sf` CLI occasionally mixes warning output into stdout on the first call, which causes a false "not supported" parse. Re-running the identical query without waiting resolves the issue — no org state changes between attempts.

```bash
TOGGLE_STATE="UNKNOWN"
for _attempt in 1 2; do
  _raw=$(sf data query -o "$ORG" -q "SELECT Id FROM AgenticCtxtDecorDefinition LIMIT 1" --json 2>&1)
  if echo "$_raw" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('status')==0 else 1)" 2>/dev/null; then
    TOGGLE_STATE="ON"; break
  fi
  if echo "$_raw" | grep -qi "not supported"; then
    TOGGLE_STATE="OFF"
    # do NOT break on first failure — retry once to rule out transient parse failure
  fi
done
```

- ✅ `TOGGLE_STATE=ON` → proceed with §F.4.2.
- ❌ `TOGGLE_STATE=OFF` (both attempts) → toggle is genuinely OFF, **pause and prompt the operator**.

**F.4.1 — ⏸ OPERATOR PAUSE: enable the Orchestrator OrgPerm.**

If the SOQL probe returned "not supported", send this message verbatim to the operator, then wait for their reply:

> **One manual step needed.** Please open this URL and enable Agentforce Orchestrator:
>
> `<INSTANCE_LIGHTNING_URL>/lightning/setup/AgentforceOrchestrator/home`
>
> 1. Click **Enable Agentforce Orchestrator** (top of the page).
> 2. Wait for the confirmation banner.
> 3. Reply `done` here and I'll continue.

When the operator replies `done`, re-run the F.4.0 SOQL probe. If it still returns "not supported", either the toggle wasn't flipped or there's an org-shape gap. Ask them to double-check, then re-probe. If the org genuinely does not have this surface (older-API pod), fall through to the F.4 skip: continue the deploy without the Orchestrator, and log the gap in the operator handoff.

**F.4.2 — Bot prerequisite check.**

```bash
sf data query -o "$ORG" -q "SELECT DeveloperName, AgentTemplate FROM BotDefinition WHERE DeveloperName='<BotDevName>'"
```

If `AgentTemplate` is `null`, the Bot was created outside the wizard and MUST be deleted and recreated via **Setup → Agentforce Agents → New Agent → From Template → Agentforce Service Agent**. There is no API path to patch `AgentTemplate` on an existing Bot.

Grab the Bot Id for the POST payload:

```bash
BOT_ID=$(sf data query -o "$ORG" -q "SELECT Id FROM BotDefinition WHERE DeveloperName='<BotDevName>'" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
```

**F.4.3 — Create the Orchestrator + Retriever + Parameters via one Connect POST.**

```bash
cat > /tmp/orch.json <<EOF
{
  "name": "Help Portal Concierge Orchestrator",
  "developerName": "Help_Portal_Concierge_Orch",
  "agentId": "$BOT_ID"
}
EOF

sf api request rest -o "$ORG" --method POST \
  "/services/data/v67.0/connect/self-service/setup/agentOrchestrator" \
  --body @/tmp/orch.json
# → {"orchestratorId":"1iExx0000000..."}
```

**Payload field reference:**

| Field | Required | Notes |
|---|---|---|
| `agentId` | ✅ Yes | The `0Xx`-prefix `BotDefinition.Id`. |
| `name` | Optional | Human label. Defaults to the agent's MasterLabel. |
| `developerName` | Optional | API name. Defaults to `name`. |
| `description` | ❌ **Rejected** on v67 |
| `agenticContextDecoratorType` | ❌ **Rejected** on v67 (type is set implicitly — Concierge is the default). |
| `type` / `digitalWorkerType` | ❌ **Rejected** on v67 |
| `greetingPrompt` | Optional | DeveloperName of a `GenAiPromptTemplate` (Flex type). |
| `enableRecommendations` | Optional | Boolean. |

Response: `{"orchestratorId":"1iE...UAM"}`. Capture this for verification.

**F.4.4 — NO NSSE PATCH on v67.** On v67, `NetworkSelfServiceExtension` has no `AgenticCtxtDecorDefinitionId` field. Binding is implicit: an org can only have one Orchestrator with `AgenticContextDecoratorType=Concierge`, and every LWR Concierge site picks it up automatically. Skip this step on v67. On v68+ where the NSSE field exists, PATCH it:

```bash
# ONLY run this block on v68+ orgs
NSSE_ID=$(sf data query -o "$ORG" -q "SELECT Id FROM NetworkSelfServiceExtension WHERE NetworkId='$NETWORK_ID' LIMIT 1" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v68.0/tooling/sobjects/NetworkSelfServiceExtension/$NSSE_ID" \
  --body "{\"AgenticCtxtDecorDefinitionId\":\"$ORCHESTRATOR_ID\"}"
```

**F.4.5 — Verify.**

```bash
sf data query -o "$ORG" -q "SELECT Id, DeveloperName, MasterLabel, Status, AgenticContextDecoratorType FROM AgenticCtxtDecorDefinition"

sf api request rest -o "$ORG" --method GET \
  "/services/data/v67.0/connect/self-service/setup/agentOrchestrator"
# orchestrators[].agentIds should include your $BOT_ID
```

**F.4.6 — Republish the site** *(only required when NSSE was patched — skip on v67)*.

## Step G — Deploy the modified bundle

```bash
sf project deploy start --metadata "$BUNDLE_TYPE:$BUNDLE_NAME_FOR_DEPLOY" --target-org $ORG --json \
  | jq '{status,success,errors:[.result.details.componentFailures[]?|{fullName,problem}]}'
```

For DigitalExperienceBundle, `$BUNDLE_NAME_FOR_DEPLOY` is `site/$BUNDLE_NAME`. For ExperienceBundle, it's just `$BUNDLE_NAME`.

Watch for UUID collisions — every `id` field in the bundle must be unique. If deploy fails with a UUID conflict, re-retrieve the current bundle, re-apply changes, redeploy.

## Step H — Personalization *(best-effort, non-blocking)*

Concierge chiclets (`conciergeChicletGroupContainer`) surface personalized recommended actions and recommended knowledge articles. This requires a Data Graph linked to the Agentforce Orchestrator for the site, plus AES (Agentic Enterprise Search) as the org's search engine.

Attempt both linkages headlessly:

- **Data Graph linkage:** `sf api request rest` against the Orchestrator configuration endpoint.
- **AES:** headless via Search Query Manager configuration.

If either fails, log the gap and continue — chat still works without personalized chiclets. Note "Configure Data Graph + AES in Setup → Agentforce Orchestrator" in the operator handoff.

## Step I — Publish the site

**Resolve `NETWORK_ID` by the LWR site**, not by `UrlPathPrefix`. `Network.UrlPathPrefix` on new sites appends `vforcesite` even though the LWR URL uses the un-suffixed prefix on `.my.site.com`. Filter by `Name` instead:

```bash
NETWORK_ID=$(sf data query --target-org $ORG --json --query \
  "SELECT Id FROM Network WHERE Name = '<Site Name>' LIMIT 1" \
  | jq -r '.result.records[0].Id')

sf api request rest "/services/data/v67.0/connect/communities/$NETWORK_ID/publish" \
  --method POST --body '{}' --target-org $ORG
```

Publish is async. Poll `BackgroundOperation` until `Status = Complete`.

**Post-publish activation.** On many org shapes, `Status` remains `UnderConstruction` even after publish completes. Go fully live headlessly:

```bash
sf api request rest "/services/data/v67.0/sobjects/Network/$NETWORK_ID" \
  --method PATCH --body '{"Status":"Live"}' --target-org $ORG
```

HTTP 204 = success. Re-query to confirm `Status = Live`.

## Step J — Verify guest access (post-publish smoke check)

After Step I finishes publishing, verify the portal is publicly reachable:

```bash
curl -sSI "$PUBLISHED_PORTAL_URL/" | head -1
```

Expected: `HTTP/2 200`. If instead you see `HTTP/2 302 Location: .../login?ec=302&startURL=...`, then:

1. Confirm `sfdc_cms__site/$BUNDLE_NAME/content.json` on disk has `"authenticationType" : "AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED"`.
2. Re-deploy the bundle (Step G) and re-publish (Step I).
3. Re-probe.

For **Auth-only sites** (Step A #7 option 3): `authenticationType = AUTHENTICATED` is correct — a 302 to `/login` is the intended behavior.

**Also probe the LWR runtime's Concierge config endpoint** to confirm Step F.3's binding is complete:

```bash
curl -sS "$PUBLISHED_PORTAL_URL/webruntime/api/services/data/v67.0/connect/self-service/concierge/config?language=en-US&asGuest=false&htmlEncode=false" \
  | jq '.chatConfig | {deploymentName, siteUrl, scrtUrl}'
```

If any of the three is null, revisit Step F.3.

## Step L — Trust surface: CORS + Trusted URLs + Trusted Domains + Experience Builder security

All four sub-steps are headless — no Setup UI clicks required.

**Extract the four URL values first**, from the ESD's Install Code Snippet (Setup → Embedded Service Deployments → *your ESD* → Code Snippet):

| Value | How to extract | Example |
|---|---|---|
| `Org_ID` | 1st positional argument to `embeddedservice_bootstrap.init(...)` | `00Dbm00000rSNZR` |
| `ESD_Developer_Name` | 2nd positional argument | `Help_Portal_Concierge` |
| `siteURL` | 3rd positional argument | `https://<myDomainStem>.my.site.com/ESWHelpPortalConcierge…` |
| `scrt2URL` | Value inside the curly braces (`scrt2URL: '...'`) | `https://<myDomainStem>.my.salesforce-scrt.com` |

Compute a **base siteURL** by stripping the path from `siteURL`, and a **published portal URL** — the LWR site's own base.

### L.0 — Network + ESC guest-access flags *(THREE flags, ALL must be True)*

> **🚨 CRITICAL — the most common cause of a blank `/conversation/guest` page is this section.** Three independent flags gate guest chat rendering; ALL THREE must be True:
>
> 1. `Network.OptionsGuestChatterEnabled = True` — master gate for `/self-service/*` endpoints.
> 2. `Network.OptionsGuestMemberVisibility = True` — gates the conversation route rendering.
> 3. `EmbeddedServiceConfig.AreGuestUsersAllowed = True` on **BOTH** the auth ESC AND the guest ESC bound to NSSE.

Diagnostic + fix (headless, Data API):

```bash
# 1. Find the Network id
sf data query -o $ORG -q "SELECT Id, Name, Status FROM Network WHERE Name LIKE '%<SitePrefix>%'" --json

# 2. Check both guest flags
sf data query -o $ORG -q "SELECT Id, OptionsGuestChatterEnabled, OptionsGuestMemberVisibility FROM Network WHERE Id='$NETWORK_ID'" --json

# 3. PATCH both to True
sf data update record -o $ORG --sobject Network --record-id $NETWORK_ID \
  --values "OptionsGuestChatterEnabled=true OptionsGuestMemberVisibility=true"

# 4. Reprobe — should return 200
curl -sS -w "HTTP=%{http_code}\n" \
  "$PUBLISHED_PORTAL_URL/webruntime/api/services/data/v67.0/connect/self-service/concierge/config?asGuest=true"

# 5. Verify every ESC bound via NSSE has AreGuestUsersAllowed=true
#    Filter by DeveloperName so this runs before §M resolves AUTH_ESC_ID by Id.
sf api request rest -o $ORG "/services/data/v67.0/tooling/query?q=SELECT+Id,DeveloperName,AreGuestUsersAllowed+FROM+EmbeddedServiceConfig+WHERE+DeveloperName+IN+('<AuthESDDevName>','<GuestESDDevName>')"
# If either row is false: retrieve via mdapi, sed the tag, redeploy, republish site.
```

### L.1 — Setup CORS

```bash
for ORIGIN in "$SCRT2_URL" "$BASE_SITE_URL" "$PUBLISHED_PORTAL_URL"; do
  sf data create record --sobject CorsWhitelistEntry \
    --values "UrlPattern=$ORIGIN" --target-org $ORG || true
done
```

Skip an origin if `CorsWhitelistEntry` already lists it. Expect at least one of the three inserts to be a no-op on trial pods.

### L.2 — Trusted URLs (`CspTrustedSite`)

Trusted URLs power the org-wide CSP allowlist. Deploy 3 records with the 6 supported directives.

**Query first to check what's already covered:**

```bash
sf data query -o $ORG -q "SELECT DeveloperName, EndpointUrl FROM CspTrustedSite" -r csv
```

Then deploy the missing patterns via metadata. Example `force-app/main/default/cspTrustedSites/HelpPortal_SCRT2.cspTrustedSite-meta.xml`:

```xml
<CspTrustedSite xmlns="http://soap.sforce.com/2006/04/metadata">
    <context>All</context>
    <description>Help Portal SCRT2</description>
    <endpointUrl><!-- bare host only, e.g. trailsignup-c29680009d2f9b.my.salesforce-scrt.com — NO https:// prefix --></endpointUrl>
    <isActive>true</isActive>
    <isApplicableToConnectSrc>true</isApplicableToConnectSrc>
    <isApplicableToFontSrc>true</isApplicableToFontSrc>
    <isApplicableToFrameSrc>true</isApplicableToFrameSrc>
    <isApplicableToImgSrc>true</isApplicableToImgSrc>
    <isApplicableToMediaSrc>true</isApplicableToMediaSrc>
    <isApplicableToStyleSrc>true</isApplicableToStyleSrc>
</CspTrustedSite>
```

Deploy:

```bash
sf project deploy start -o $ORG -m CspTrustedSite
```

**Gotcha:** `isApplicableToScriptSrc` and related booleans (`isApplicableToChildSrc`, `isApplicableToWorkerSrc`, `isApplicableToObjectSrc`, `isApplicableToManifestSrc`, `isApplicableToFrameAncestors`) DO NOT EXIST in the v67 Metadata API schema for `CspTrustedSite`. Only the 6 booleans above are accepted.

> **`endpointUrl` must be the bare hostname only** — no `https://` prefix, no path. The API rejects full URLs. Strip the scheme from `$SCRT2_URL` before populating: `SCRT2_HOST=${SCRT2_URL#https://}`. Use `$SCRT2_HOST` in the `<endpointUrl>` tag, not `$SCRT2_URL`.

Repeat for base siteURL and published portal URL, changing `DeveloperName` per record.

### L.3 — Trusted Domains for Inline Frames (per-Site)

Each `Site` has a private list of domains it will let host it inside an iframe. Two variants:

- **`IframeWhiteListUrl` (org-level, no `SiteId`)** — Data API POST with `{Url, Context}`. Context enum: `LightningOut`, `Surveys`, `UIEmbedding`, `VisualforcePages`, `DCH_ADDIN_APP`.
- **`SiteIframeWhiteListUrl` (per-Site, has `SiteId + Url`)** — only accepts inserts against the ChatterNetwork wrapper Site. The Picasso `SiteType='ChatterNetworkPicasso'` id is rejected with `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`.

```bash
# Path A — org-level trust
for URL in "$SCRT2_URL" "$BASE_SITE_URL" "$ORG_URL"; do
  sf api request rest -o $ORG --method POST -H "Content-Type: application/json" \
    -b "{\"Url\":\"$URL\",\"Context\":\"LightningOut\"}" \
    "/services/data/v67.0/sobjects/IframeWhiteListUrl"
done

# Path B — per-Site trust (ChatterNetwork wrapper Site only)
sf data query -o $ORG -q "SELECT Id, Name, SiteType FROM Site WHERE Name='$SITE_NAME' AND SiteType='ChatterNetwork'"
# → capture $WRAPPER_SITE_ID

for URL in "$BASE_SITE_HOST" "*.${BASE_SITE_HOST}"; do
  sf api request rest -o $ORG --method POST -H "Content-Type: application/json" \
    -b "{\"SiteId\":\"$WRAPPER_SITE_ID\",\"Url\":\"$URL\"}" \
    "/services/data/v67.0/sobjects/SiteIframeWhiteListUrl"
done
```

**Gotchas:**
- URL field accepts **bare hosts and wildcards only**. Full URLs with paths return `Enter a valid URL or URI`.
- `SiteId` must be the ChatterNetwork wrapper — the Picasso Site is rejected.

### L.4 — Experience Builder Security & Privacy

Three knobs on the site's Security & Privacy panel — all headless-writable.

**1. Clickjack Protection Level — headless via `CustomSite` mdapi (targeting the ChatterNetwork wrapper site name, NOT the Picasso `*1` name).**

```bash
WRAPPER_SITE_NAME=<strip the trailing "1" from BUNDLE_NAME>
mkdir -p /tmp/cj-deploy/sites

rm -rf /tmp/cs-retrieve
sf project retrieve start -o "$ORG" -m "CustomSite:$WRAPPER_SITE_NAME" --target-metadata-dir /tmp/cs-retrieve
unzip -qo /tmp/cs-retrieve/unpackaged.zip -d /tmp/cs-retrieve/e

sed "s|<clickjackProtectionLevel>[^<]*</clickjackProtectionLevel>|<clickjackProtectionLevel>AllowAllFraming</clickjackProtectionLevel>|" \
  /tmp/cs-retrieve/e/unpackaged/sites/${WRAPPER_SITE_NAME}.site > /tmp/cj-deploy/sites/${WRAPPER_SITE_NAME}.site

cat > /tmp/cj-deploy/package.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>${WRAPPER_SITE_NAME}</members><name>CustomSite</name></types>
    <version>67.0</version>
</Package>
EOF

sf project deploy start -o "$ORG" --metadata-dir /tmp/cj-deploy
```

Picklist values (v67): `AllowAllFraming`, `External`, `SameOriginOnly` (default), `NoFraming`. `AllowAllFraming` is required for Concierge chat (which mounts an SCRT-hosted iframe).

**2 + 3. CSP Level + Lightning Web Security — headless via DEB bundle `mainAppPage/content.json`.**

```bash
BUNDLE_FILE="force-app/main/default/digitalExperiences/site/${BUNDLE_NAME}/sfdc_cms__appPage/mainAppPage/content.json"
python3 -c "
import json
d=json.load(open('$BUNDLE_FILE'))
d['contentBody']['isLockerServiceEnabled']=False
d['contentBody']['isRelaxedCSPLevel']=True
json.dump(d, open('$BUNDLE_FILE','w'), indent=2)
"
sf project deploy start -o "$ORG" -m "DigitalExperienceBundle:site/${BUNDLE_NAME}" --ignore-conflicts
sf api request rest -o "$ORG" --method POST \
  "/services/data/v67.0/connect/communities/${NETWORK_ID}/publish" \
  -H "Content-Type: application/json" --body "{}"
```

Verification:

```bash
# ⚠️ CRITICAL: Use --target-metadata-dir to a TEMP dir — never retrieve back into the live
# project directory here. A bare `sf project retrieve start` without --target-metadata-dir
# overwrites force-app/main/default/ with whatever the org currently has, clobbering any
# locally-written files (conversation view, route, etc.) that haven't been round-tripped yet.
rm -rf /tmp/l4-verify
sf project retrieve start -o "$ORG" -m "DigitalExperienceBundle:site/${BUNDLE_NAME}" \
  --target-metadata-dir /tmp/l4-verify
unzip -qo /tmp/l4-verify/unpackaged.zip -d /tmp/l4-verify/e 2>/dev/null || true
VERIFY_FILE="/tmp/l4-verify/e/unpackaged/digitalExperiences/site/${BUNDLE_NAME}/sfdc_cms__appPage/mainAppPage/content.json"
python3 -c "
import json
cb=json.load(open('$VERIFY_FILE'))['contentBody']
print('isLockerServiceEnabled:', cb.get('isLockerServiceEnabled'))
print('isRelaxedCSPLevel:', cb.get('isRelaxedCSPLevel'))
"
# Expected: False, True
```

**Security note:** these settings weaken the site's script-execution / frame-embedding posture. They are required for Concierge chat (which mounts a cross-origin SCRT iframe with inline scripts). Do not enable them on Experience Cloud sites that don't need Concierge.

### L.5 — Verify the trust surface

```bash
# CORS
sf data query -q "SELECT UrlPattern FROM CorsWhitelistEntry WHERE UrlPattern IN ('$SCRT2_URL','$BASE_SITE_URL','$PUBLISHED_PORTAL_URL')" -t

# Trusted URLs
sf data query -q "SELECT DeveloperName, EndpointUrl, IsApplicableToConnectSrc, IsApplicableToFrameSrc FROM CspTrustedSite WHERE EndpointUrl IN ('$SCRT2_URL','$BASE_SITE_URL','$PUBLISHED_PORTAL_URL')" -t
```

Both must return three rows each.

## Step M — AI Experiences ESD assignment

> **Preflight:** `sf sobject describe --sobject AiExperienceContextDefinition -o $ORG 2>&1 | head -3`
>
> If this returns `The requested resource does not exist`, skip §M entirely (older-API orgs).

Two Network toggles are headless-writable:

| Toggle | Target value | Headless path |
|---|---|---|
| Share search queries with Agentforce Service Agent | OFF | **No-op — OFF is the org default on v67.** |
| Share Data Category Selection with Agentforce Service Agent (Beta) | ON | ✅ `Network.OptionsDataCategoryContextPassingEnabled = true` |
| Self Service Personalization | OFF | ✅ `Network.OptionsSlfSrvcPersonalizationEnabled = false` |

**Headless PATCH:**

```bash
sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v67.0/sobjects/Network/$NETWORK_ID" \
  --body '{"OptionsDataCategoryContextPassingEnabled":true,"OptionsSlfSrvcPersonalizationEnabled":false}'
# Expected: HTTP 204 No Content
```

**Auth-ESD NSSE bind** *(only for portals serving authenticated users)*:

```bash
AUTH_ESC_ID=$(sf data query -o "$ORG" -q "SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='<AuthESDDevName>'" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v67.0/tooling/sobjects/NetworkSelfServiceExtension/$NSSE_ID" \
  --body "{\"EmbeddedServiceCnfgId\":\"$AUTH_ESC_ID\"}"
```

For UnAuth-only Help Portals, guest binding alone is sufficient — skip this PATCH.

## Step N — Bot-routing wiring *(runtime layer — required for "Agents are available")*

`/concierge/config` returning 200 unblocks the guest **bootstrap** (portal loads, prompt bar renders). It does NOT wire the Bot to actually pick up messaging sessions. Without Step N, every guest submission lands in `MessagingSession.Status='Waiting'` and the chat surface shows **"Agents are not available. Try again later."**

**Three writes** (all Data API, all reversible). Run them AFTER `MessagingChannel.IsActive=true` (Step E) and `BotVersion.Status=Active`:

```bash
# Prerequisites
BOT_ID="0Xx..."                     # BotDefinition Id from Step E
CHAN_ID="0Mj..."                    # MessagingChannel Id
FALLBACK_Q=$(sf data query -o $ORG -q "SELECT FallbackQueueId FROM MessagingChannel WHERE Id='$CHAN_ID'" --json | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['FallbackQueueId'])")
BOT_USER=$(sf data query -o $ORG -q "SELECT BotUserId FROM BotDefinition WHERE Id='$BOT_ID'" --json | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['BotUserId'])")
PRESENCE_CFG=$(sf data query -o $ORG -q "SELECT Id FROM PresenceUserConfig WHERE DeveloperName='default_presence_config'" --json | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
ROUTING_CFG=$(sf data query -o $ORG -q "SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='MessagingSession'" --json | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")

# N.1 — presence enable the BotUser
sf data create record -o $ORG --sobject PresenceUserConfigUser \
  --values "UserId=$BOT_USER PresenceUserConfigId=$PRESENCE_CFG"

# N.2 — make BotUser a member of the fallback queue
sf data create record -o $ORG --sobject GroupMember \
  --values "GroupId=$FALLBACK_Q UserOrGroupId=$BOT_USER"

# N.3 — bind the fallback queue to the MessagingSession routing config
sf data update record -o $ORG --sobject Group --record-id $FALLBACK_Q \
  --values "QueueRoutingConfigId=$ROUTING_CFG"
```

**Verification:**

```bash
sf data query -o $ORG -q "SELECT COUNT(Id) n FROM PresenceUserConfigUser WHERE UserId='$BOT_USER'"
sf data query -o $ORG -q "SELECT COUNT(Id) n FROM GroupMember WHERE GroupId='$FALLBACK_Q' AND UserOrGroupId='$BOT_USER'"
sf data query -o $ORG -q "SELECT QueueRoutingConfigId FROM Group WHERE Id='$FALLBACK_Q'"
```

**Live-runtime step**: Salesforce requires the BotUser to be `Online` in Omni-Presence for routing to consider it available. For Agentforce Service Agent (`Type=ExternalCopilot`), this is typically auto-provisioned when the BotVersion is activated *if* N.1–N.3 exist first. If sessions still stay in `Waiting` after N.1–N.3, verify:

```bash
sf data query -o $ORG -q "SELECT Id, IsCurrentState, ServicePresenceStatusId FROM UserServicePresence WHERE UserId='$BOT_USER' ORDER BY CreatedDate DESC LIMIT 1"
```

If zero rows or `IsCurrentState=false`, re-activate the BotVersion:

```bash
sf agent deactivate -o $ORG --api-name $BOT_DEV_NAME
sf agent activate -o $ORG --api-name $BOT_DEV_NAME
```

Wait a few minutes for the Automated Process pickup path to spin up, then re-test in a browser.

## Step O — Search Manager Query Configuration

Configures a `SearchCustomization` that scopes the portal's object search results (Product / Knowledge / Case).

**Fully headless via Metadata API using `channel=LWRExperienceSiteSearch`** (NOT `CustomChannel` / `CustomExperience`).

### O.1 — Preflight

```bash
sf api request rest -o "$ORG" --method GET \
  "/services/data/v67.0/tooling/sobjects/SearchCustomization/describe" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('EXISTS' if d.get('name') else 'NOT_FOUND')"
```

If `NOT_FOUND` (very old orgs), skip §O.

### O.2 — Deploy the config

`force-app/main/default/searchCustomizations/Help_Portal_LWR_Search.searchCustomization-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SearchCustomization xmlns="http://soap.sforce.com/2006/04/metadata">
    <channel>LWRExperienceSiteSearch</channel>
    <masterLabel>Help Portal LWR Search</masterLabel>
    <selectedObject>Product2</selectedObject>
    <selectedObject>Knowledge__kav</selectedObject>
    <selectedObject>Case</selectedObject>
</SearchCustomization>
```

```bash
sf project deploy start -o "$ORG" --source-dir force-app
```

**Enum values on `SearchCustomization.Channel` (v67):** `GlobalSearch`, `CustomChannel`, `KnowledgeComponentSearch`, `LWRExperienceSiteSearch`. `LWRExperienceSiteSearch` is the correct choice for Help Portal.

### O.3 — Verify

```bash
sf data query -o "$ORG" --use-tooling-api \
  -q "SELECT Id, DeveloperName, MasterLabel, Channel FROM SearchCustomization WHERE DeveloperName='Help_Portal_LWR_Search'"
```

Round-trip retrieval:

```bash
sf project retrieve start -o "$ORG" -m SearchCustomization:Help_Portal_LWR_Search
cat force-app/main/default/searchCustomizations/Help_Portal_LWR_Search.searchCustomization-meta.xml
```

Expected: 3 `<selectedObject>` lines in alphabetical order.

### O.4 — Bind SearchCustomization to NSSE

> **Skip this step on orgs with only one LWR site.** With a single `channel=LWRExperienceSiteSearch` SearchCustomization, the platform applies it by implicit channel-match — the explicit PATCH is unnecessary and fails with "Select a custom experience query configuration. Other configurations aren't supported." Only run this PATCH when the org has multiple LWR sites and you want to assign different query configs per site.

```bash
SEARCH_CONFIG_ID=$(sf api request rest -o "$ORG" \
  "/services/data/v67.0/tooling/query?q=SELECT+Id+FROM+SearchCustomization+WHERE+DeveloperName='Help_Portal_LWR_Search'" \
  | python3 -c "import sys,json,re;raw=sys.stdin.read();raw=re.sub(r'^\s*Warning[^\n]*\n','',raw,flags=re.M);print(json.loads(raw)['records'][0]['Id'])")

sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v67.0/tooling/sobjects/NetworkSelfServiceExtension/$NSSE_ID" \
  --body "{\"SearchCustomizationId\":\"$SEARCH_CONFIG_ID\"}"
```

**Effect scope:** With `SearchCustomizationId=null`, the platform still applies the org's single `channel=LWRExperienceSiteSearch` SearchCustomization by implicit channel-match. The explicit PATCH matters when the org has multiple LWR sites and you want them to point at different query configs.

## Step P — Smart Search Assistance subagent *(UI-only — log and continue)*

Adding a **Smart Search Assistance** subagent to the Agentforce Builder enhances the agent's Knowledge search behavior. The asset lives in a Salesforce-hosted cloud registry with no headless surface at v67. **Log the step in the operator handoff and continue** — chat works without it.

If the operator wants to add it later:

1. Setup → Agentforce Agents → open the agent → Subagents panel → **+** → **Add from Asset Library** → **Smart Search Assistance**.
2. Wire Advanced Settings variable bindings: Search Configuration → `SearchCustomization` variable, Network ID → `NetworkId` variable.
3. Verify the 7 context variables are present: `SmsVerificationKey`, `customerId`, `customerType`, `isVerified`, `VerifiedCustomerId`, `SearchCustomization`, `NetworkId`.
4. Save + activate the agent version.

## Step S — Login & Registration + Head Markup + Publish

### S.1 — Member profile assignments *(auth paths only)*

For UnAuth portals (Step A #7 option 3), the Guest User is auto-added via the site-level `authenticationType` flip in §F.0 — no `NetworkMemberGroup` writes needed.

For AuthOnly / MixedAuth (options 1/2), bind 4 Customer Community profiles via Data API:

```bash
sf data query -o "$ORG" -q "SELECT Id, Name FROM Profile WHERE Name IN ('Customer Community User','Customer Community Login User','Customer Community Plus User','Customer Community Plus Login User')" -r csv

for PROFILE_ID in <the 4 Ids above>; do
  sf api request rest -o "$ORG" --method POST \
    "/services/data/v67.0/sobjects/NetworkMemberGroup" \
    --body "{\"NetworkId\":\"$NETWORK_ID\",\"ParentId\":\"$PROFILE_ID\"}"
done
```

The polymorphic field is `ParentId` (keyPrefix `00e` = Profile, `0PS` = PermissionSet). Verify:

```bash
sf data query -o "$ORG" -q "SELECT Id, NetworkId, ParentId FROM NetworkMemberGroup WHERE NetworkId='$NETWORK_ID'" -r csv
# Expect 5 rows after INSERT (SysAdmin + 4 Customer Community variants)
```

### S.2 — Login & Registration

Three of four toggles map to `NetworkAuthApiSettings` fields headlessly. The fourth ("Require reCAPTCHA for username-password login") has no matching v67 field — Setup UI fallback only.

| UI toggle | Field | Recommended value |
|---|---|---|
| Uncheck "Allow self-registration via Headless Registration API" | `IsHeadlessUserRegistrationAllowed` | `false` |
| Uncheck "Allow password reset via Headless Forgot Password API" | `IsForgotPwdAllowed` | `false` |
| Check "Require reCAPTCHA for username-password login" | No field found — Setup UI fallback | — |
| Set "Score Threshold" to 0 | `RecaptchaScoreThreshold` | `0.0` |

No `NetworkAuthApiSettings` row exists by default. Zero-row SOQL means INSERT (not PATCH):

```bash
sf api request rest -o "$ORG" --method POST \
  "/services/data/v67.0/sobjects/NetworkAuthApiSettings" \
  --body "{
    \"NetworkId\":\"$NETWORK_ID\",
    \"IsHeadlessUserRegistrationAllowed\":false,
    \"IsForgotPwdAllowed\":false,
    \"RecaptchaScoreThreshold\":0.0
  }"
```

If a row already exists, PATCH the existing Id:

```bash
NAAS_ID=$(sf data query -o "$ORG" -q "SELECT Id FROM NetworkAuthApiSettings WHERE NetworkId='$NETWORK_ID'" --json \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['records'][0]['Id'])")
sf api request rest -o "$ORG" --method PATCH \
  "/services/data/v67.0/sobjects/NetworkAuthApiSettings/$NAAS_ID" \
  --body '{"IsHeadlessUserRegistrationAllowed":false,"IsForgotPwdAllowed":false,"RecaptchaScoreThreshold":0.0}'
```

**Server-side reCAPTCHA dependency:** the server refuses `IsHeadlessUserRegistrationAllowed=true` and `IsForgotPwdAllowed=true` unless auth OR reCAPTCHA is enabled. `IsRecaptcha*` boolean writes are silently rejected when `RecaptchaSecretKey` is empty. For UnAuth-only portals, leave these fields at `false` — cosmetic only.

### S.3 — Head Markup

The `headMarkup` string in the DEB's `sfdc_cms__appPage/mainAppPage/content.json` is pre-populated with SLDS + DXP stylesheet imports — no additional write needed. Preflight verify:

```bash
mkdir -p /tmp/hm-verify && cat > /tmp/hm-verify/package.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types><members>site/${BUNDLE_NAME}</members><name>DigitalExperienceBundle</name></types>
  <version>67.0</version>
</Package>
EOF
sf project retrieve start -o "$ORG" --manifest /tmp/hm-verify/package.xml --target-metadata-dir /tmp/hm-verify-out --wait 5
unzip -qo /tmp/hm-verify-out/unpackaged.zip -d /tmp/hm-verify-ex
grep -l '"headMarkup"' /tmp/hm-verify-ex/**/mainAppPage/content.json && echo 'Head Markup present ✓'
```

### S.4 — Progressive Rendering *(UI-only — skip, log if visual jank)*

No verified headless surface. Default is OFF on freshly-provisioned DEB sites — skip on a fresh deploy. If a downstream visual test shows layout jank, log the step for the operator (Experience Builder → Settings → Advanced → Progressive Rendering).

### S.5 — Publish + Activate

```bash
# 1. Publish
sf community publish -o "$ORG" --name "$SITE_NAME"

# 2. Activate
sf data update record -o "$ORG" --sobject Network --record-id "$NETWORK_ID" --values "Status=Live"

# 3. Verify runtime reachability
sf data query -o "$ORG" -q "SELECT Status FROM Network WHERE Id='$NETWORK_ID'" -r csv
curl -sI "$PUBLISHED_PORTAL_URL"
```

**Ordering matters:** Publish before Activate. Every subsequent config change (F.3.a-d ESC binding, §L.4 bundle flags, §S.2 NAAS INSERT) requires a re-publish; Activate is one-shot.

## Step K — Open the portal for the user

At the end of the run, print the customer-facing portal URL and instruct the operator to open it in an Incognito window (a Salesforce SysAdmin session shows a blank chat surface — that's expected, not a bug).

```text
✅ Help Portal deployed.

Open this URL in a fresh Incognito / Private window to test as a guest visitor:

  $PUBLISHED_PORTAL_URL

You should see the welcome greeting, prompt bar, suggestion chiclets, and chat surface on the home page. Type a question and submit — the agent should respond within a few seconds.

Follow-up manual steps (if any were logged during the deploy):
  - <populate from the manual-step log>
```

Also open it locally for convenience:

```bash
sf org open --target-org $ORG --path "/<url-path>/"
```

> **Do NOT append `/s` to the portal URL.** LWR Experience Cloud sites (DigitalExperienceBundle) use path-based routing — the home page is at `/<urlPathPrefix>/` (trailing slash). The `/s` suffix is an Aura/Classic Experience Cloud convention and routes to a 404 on LWR sites.

## Anti-patterns table

| Symptom | Cause | Fix |
|---|---|---|
| Site creation returns `INVALID_INPUT: The URL can only contain alphanumeric characters` | `urlPathPrefix` contained dashes / underscores / spaces | Sanitize to alphanumeric-only before POST |
| Site creation 400 with wrong template | Template name typo | Must be exactly `Build Your Own (LWR)` — not `Help Center`, not `Customer Service` |
| `sf project retrieve start` fails with `InvalidProjectWorkspaceError` | Ran from a directory without `sfdx-project.json` | `cd` into the SFDX project root before retrieve/deploy |
| Retrieve returns `success: true` with `file count: 0` | Retrieved with wrong metadata type | Run both `sf org list metadata -m DigitalExperienceBundle` and `... -m ExperienceBundle`; use whichever type the site is registered under |
| Deploy fails: *"Provide a URL with only valid characters and no spaces"* on custom route | `urlPrefix` on a custom `sfdc_cms__route` contained a dash | Use camelCase or lowercase alphanumeric only |
| Deploy fails: *"The route ID X is invalid. To create or update a custom route, suffix the route ID with __c"* | New route folder didn't end in `__c` | Rename directory and `apiName` in `_meta.json` to `<Name>__c` |
| Prompt bar submits but next page shows "Invalid Page" | Missing `sfdc_cms__route/Conversation__c/` + `sfdc_cms__view/conversation/` in the deployed DigitalExperienceBundle | Copy both directories from a working reference bundle (§F.0.a), redeploy, republish |
| Prompt bar submits and navigates, but the destination renders as a **blank page** when opened by a Salesforce SysAdmin | SysAdmin session has no Guest ESD binding — `conciergeChat` runtime binds to the site's Guest ESD | Open the portal in a private/Incognito window and re-test |
| `/conversation/guest` blank in Incognito, Home renders, `/concierge/config?asGuest=true` returns 200 | (1) Guest-visibility flags: `OptionsGuestChatterEnabled` + `OptionsGuestMemberVisibility` + `EmbeddedServiceConfig.AreGuestUsersAllowed` on all bound ESCs. (2) Guest permset assignment: the site's `GuestUserId` needs the `<Bundle>_Guest_Concierge` permset assigned via `PermissionSetAssignment` | Run §L.0 diagnostic block (all 5 steps) + §F.3.d permset check + republish |
| Concierge components edited but don't render — no deploy error | Edited using `componentName` (ExperienceBundle field) on a DigitalExperienceBundle org, which needs `definition` instead | Use the JSON shape from §F.0 — `definition:`, UUID `id`, no `renderPriority` / `renditionMap` |
| Bundle deploy fails on UUID | Duplicate `id` across components | Regenerate any UUID that collides; re-retrieve the bundle first if unsure of current state |
| Concierge components don't render | Wrong region — placed in a custom or hidden region | Must go in the existing `content` region, inside the first column of the layout section |
| `conciergePromptBar` renders but chat doesn't respond | MessagingChannel not bound to agent, or channel is inactive | Verify `SessionHandlerId` = BotDefinition Id via SOQL (`SELECT SessionHandlerId, FallbackQueueId, IsActive FROM MessagingChannel WHERE Id='$CHAN_ID'`) — bound via Data API PATCH, not `sessionHandlerAsa` in XML (rejected at v67); PATCH `IsActive=true` if deploy left it inactive |
| `/services/data/.../connect/self-service/concierge/config` returns **HTTP 400 — `Error querying NetworkSelfServiceExtension FK fields`** | Misleading error — this is what the raw Connect endpoint returns under guest identity regardless of wiring | Ignore the raw endpoint and probe `/webruntime/api/services/data/vXX.X/connect/self-service/concierge/config?asGuest=false` instead |
| `/webruntime/api/.../concierge/config` returns `deploymentName: null` even after F.3 records exist | Site wasn't republished after F.3.a-d | Run Step I publish + `Network.Status=Live` PATCH again |
| ESC deploy fails: *"This field requires the site type ChatterNetworkPicasso"* | `<site>` in `EmbeddedServiceConfig` metadata pointed at the classic companion site instead of the LWR site | Query `Site.Name` and pick the row matching `$BUNDLE_NAME` |
| PermissionSet assignment fails: *"user's user license doesn't support it"* | Attempted to assign a licensed permset to a Guest User License user | Build a license-free permset with just the object-read grants — see §F.3.d template |
| Tooling PATCH on NSSE fails with `INVALID_INPUT: Select different deployments for guest and authenticated users` | Attempted to set `EmbeddedServiceCnfgId` and `GuestEmbeddedServiceCnfgId` to the same ESC | Set only one — UnAuth sites use `GuestEmbeddedServiceCnfgId`; Auth-only sites use `EmbeddedServiceCnfgId` |
| `Network.Status` still `UnderConstruction` after publish job returned `Complete` | Publish alone doesn't activate on this org shape | PATCH `Network/{Id}` with `{"Status":"Live"}` (HTTP 204) |
| Portal loads but redirects visitor to `/login` even though `authMode=UnAuth` | `authenticationType` in `sfdc_cms__site/{Bundle}/content.json` is still the retrieved default `AUTHENTICATED` | Change to `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED`, redeploy, re-publish |
| `Network` query by `UrlPathPrefix` returns nothing | Network's UrlPathPrefix has a `vforcesite` suffix while the LWR site uses the un-suffixed value | Query by `Name` instead |
| Widget-style embed attempted | Confused Help Portal with Web Chat | Help Portal is Concierge components on the site itself, not a widget. Read `channel-web-chat.md` for widget flow |
| Aura site used as target | Concierge components are LWR-only | Verify `SiteType = 'ChatterNetworkPicasso'` before deploy |
| Guest curl to `/webruntime/api/.../connect/self-service/*` returns `HTTP 401 UNAUTHORIZED` | `Network.OptionsGuestChatterEnabled = False` on target | Run §L.0 diagnostic; PATCH to True via Data API — no republish required |
| Portal loads, `/concierge/config` returns 200, prompt bar renders but says **"Agents are not available. Try again later."** | Bot-routing wiring missing. Typical gaps: `PresenceUserConfigUser`, `GroupMember`, `Group.QueueRoutingConfigId` | Run §N — three Data-API writes |
| §N writes all succeed but chat *still* shows "Agents are not available" immediately | Automated-Process pickup path needs to spin up after routing wiring changes | Re-activate the BotVersion via CLI (`sf agent deactivate` + `sf agent activate`). Wait a few minutes. Do NOT rely on `UserServicePresence` COUNT as the readiness signal |
| Prompt bar responses are ungrounded / navigate to `/error` on newer-API orgs | Agentforce Orchestrator not wired | See §F.4 — enable the OrgPerm (operator pause) then `POST /connect/self-service/setup/agentOrchestrator` |
| Agentforce Orchestrator's "Add Tool → Agent" picker is empty | `BotDefinition.AgentTemplate` is `null` — Bot was created via headless Metadata deploy, not the Setup wizard | Delete the Bot and recreate via Setup → Agentforce Agents → New Agent → From Template → Agentforce Service Agent |

---

## Handoff to Checkpoint 3.5 and Checkpoint 4

After Help Portal provisioning, the flow returns to the spec: Checkpoint 3.5 (silent pre-flight — verify MessagingChannel is Active, ADL is grounded, and the Concierge components round-tripped in the deployed bundle) then Checkpoint 4 (go-live: activate channel, wire escalation flow, offer to test). Those gates live in `assets/help-agent-spec.md` §4.4–§4.5.
