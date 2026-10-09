# Deploy to channels, Omni-Channel routing & user verification

Read at Workflow steps 12–13. This is the full per-agent channel stack: each agent gets its own Experience Cloud site, messaging channel, Omni-Channel routing configuration, fallback queue, and inbound routing flow. User verification (auth/AEA only) is set inline during channel + site creation (Step 12 sub-steps 5–6), not as a separate step. **Prerequisite:** Omni-Channel must be enabled (`platform-enablement.md` Toggle 3) — the inbound flow's Route Work element routes through Omni-Channel objects, so it is required for channel deploy, not optional.

## Two "channel" objects — do not conflate them

- **`ServiceChannel`** = the Omni-Channel routing *work-type*. **One per org, SHARED by both agents.** The relevant one is `Messaging` (DeveloperName `sfdc_livemessage`, RelatedEntity `MessagingSession`) — this is what the Route Work element's *Service Channel* field points at. Reuse it; do not create a new one.
- **`MessagingChannel`** = the MIAW embedded messaging channel (MessageType `EmbeddedMessaging`). **One PER agent.** This is the customer-facing channel bound to a site.

## Shared vs per-agent — read everything FIRST

Before creating anything, read the current state of every layer. Shared layers usually already exist on any Service-Cloud org; per-agent layers are SRA-specific and absent until you create them. Attempt each read at tier 1 (`dispatch_readonly` `/query` or `/headless/metadata` GET); fall back to `sf data query` (tier 2) or a UI check (tier 3) if a call doesn't return.

| Layer | Scope | Read to run first |
|---|---|---|
| Omni-Channel enabled | **Shared** | GET `/headless/metadata?type=OmniChannelSettings&fullName=OmniChannel` → confirm `<enableOmniChannel>true</enableOmniChannel>` |
| `ServiceChannel` (Messaging) | **Shared** | `SELECT Id, DeveloperName, MasterLabel, RelatedEntity FROM ServiceChannel` — **note: no `IsActive` column; do not query it.** The `Messaging` row (DeveloperName `sfdc_livemessage`, RelatedEntity `MessagingSession`) is standard on any messaging org — **reuse it, do not create** |
| Experience Cloud site (`Network`) | **Per agent** | `SELECT Id, Name, Status FROM Network` |
| `MessagingChannel` | **Per agent** | `SELECT Id, MasterLabel, MessageType, MessagingPlatformKey FROM MessagingChannel` — **note: there is no `ChannelType` column; do not query it** |
| Routing config (`QueueRoutingConfig`) | **Per agent** | `SELECT Id, DeveloperName FROM QueueRoutingConfig` |
| Fallback queue (`Group` Type=Queue + 2×`QueueSobject` + `GroupMember`) | **Per agent** | `SELECT Id, DeveloperName, Type FROM Group WHERE Type='Queue'`; `SELECT QueueId, SobjectType FROM QueueSobject` (expect `MessagingSession` **and** `MessagingEndUser`); `SELECT GroupId, UserOrGroupId FROM GroupMember` (expect ≥1 member) |
| Inbound routing flow (`RoutingFlow`) | **Per agent** | `SELECT ApiName, ProcessType, IsActive FROM FlowDefinitionView WHERE ProcessType='RoutingFlow'` — query by **`ApiName`**, not `DeveloperName` (`FlowDefinitionView` has no `DeveloperName` column) |

**Interactive gate — Experience Cloud sites.** If the `Network` read returns existing sites, **stop and ask the user** whether to use any of them for the agents, and — if both agents are in scope — which agent maps to which site. Do not silently reuse or stand up sites. If no sites exist, hand the user the tier-3 UI create for one per agent (Step 12 sub-step 1). **WARNING:** Note the read may return an internal **ESW plumbing site** (from the deployment wizard in Step 12 sub-step 5, named `ESW_...`) — that is not a customer-facing placement site; do not offer it as one.

## Step 12 — Per-agent channel + routing stack

One inbound channel serves **one** agent, so build a full stack for **each** agent in scope: the Service (ASA, unauthenticated) agent and the Employee (AEA, authenticated) agent. The numbered list below is Step 12's own internal sequence — referred to as **"sub-step N"** throughout this file to keep it distinct from the top-level SKILL.md workflow steps (1–14) referenced alongside it.

**Front-load the slowest part — the site — then build the routing layer while it provisions, then come back and finish the site.** Community/site creation is async and wizard-heavy — the slowest single thing in this stack — so kick it off first rather than last; the routing config → queue → inbound flow → channel/ESD are otherwise self-contained and don't need the site to exist first. The site only *embeds* the deployment's already-built component at the very end:

1. **Resolve site status per agent (see the interactive gate above), then front-load creation for any agent that still needs one** — **T3**. For every agent in scope that doesn't already have a site, create it now, before anything else in this stack, and explain why to the customer per SKILL.md's deferred-wait narration guidance — provisioning is the slowest part of this build, so starting it first means it's more likely to be ready by the time it's actually needed. Setup → Digital Experiences → **All Sites** → **New** → **Education Portal** → **Get Started**, then set the URL path. Don't wait for it to reach `Live` here — move straight into sub-step 2 once creation is kicked off. **If both agents are in scope, each needs its own separate site — no sharing one between them.** If every in-scope agent already has a site, skip straight to sub-step 2.
2. **Routing configuration (`QueueRoutingConfig`)** [T1] — one per agent. Create this **before the queue** — the queue links to it, not the reverse (the `QueueRoutingConfigId` FK lives on `Group`, pointing up at the config). Create via plain **sObject REST (tier 1)** — `POST /sobjects/QueueRoutingConfig`; fall back to `sf` / UI (Setup → Omni-Channel → Routing Configurations). **WARNING: A capacity field is mandatory but not flagged in the field metadata:** the required set is `DeveloperName` + `MasterLabel` + `RoutingModel` (`MostAvailable` | `LeastActive` | `ExternalRouting`) + `RoutingPriority` (int) + **exactly one of** `CapacityWeight` (Units of Capacity) or `CapacityPercentage`. Omitting both returns `FIELD_INTEGRITY_EXCEPTION: "One capacity field must be defined."` even though `describe` marks the capacity fields nillable — set one (e.g. `CapacityWeight: 1`).
3. **Fallback queue** [T1] — one per agent, created **with its routing config already linked**. A queue is a `Group` (`Type='Queue'`) plus **two `QueueSobject` rows — `MessagingSession` AND `MessagingEndUser`** — and **at least one `GroupMember`** (the running/admin user). Set `QueueRoutingConfigId` to the sub-step-2 config **inline in the `POST /sobjects/Group` body** (it is a field on `Group`) so no follow-up edit is needed — the inline FK persists at create. All writes are plain **sObject REST (tier 1)** — `POST /sobjects/Group`, then two `POST /sobjects/QueueSobject`, then `POST /sobjects/GroupMember` (`{GroupId, UserOrGroupId}`); the `Queue` metadata type is read-only, so writes stay on sObject REST.
   - **WARNING: API-name trap:** the second supported object's `SobjectType` is **`MessagingEndUser`**, NOT `MessagingUser` — "Messaging User" is the Setup UI label only. `QueueSobject.SobjectType` is a restricted picklist; posting `MessagingUser` returns `400 INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST`. (Same UI-label-≠-API-name trap as the non-existent `MessagingChannel.ChannelType` column.)
   - **Read first:** a messaging org often already has a generic `FallbackQueue` wired to `MessagingSession` — offer to reuse it before creating a per-agent one (check it carries BOTH supported objects + a member, not just `MessagingSession`).
   - **WARNING:** Queue setup is **non-atomic** (Group → QueueSobject×2 → GroupMember are separate calls, no spanning transaction) — capture the `00G` Id and `DELETE /sobjects/Group/{id}` (cascades to `QueueSobject`/`GroupMember`) to roll back a partial. A blind re-POST of an existing member returns `DUPLICATE_VALUE`, not a no-op.
4. **Inbound routing flow (`RoutingFlow`)** [T1] — one per agent, built from scratch (see the two shapes below). Its Route Work references the queue (sub-step 3) and the agent (already created in Steps 9–10, with its ASA flows cloned in Step 11), so both must exist first. The full lifecycle — author (`save`) and activate — is tier 1 headless (see the flow section below for the exact activation path).
5. **Embedded service deployment + `MessagingChannel`** [T3] — one per agent; its routing points at the inbound flow (sub-step 4) and fallback queue (sub-step 3), so build both first. The channel and its ESD are created together as **one wizard cascade** (ESD + an internal ESW plumbing site + a `Network` + a branding set) — do not attempt a standalone `POST /sobjects/MessagingChannel`; the wizard doesn't attach an ESD to a pre-existing channel (an API-created one comes out ESD-less and non-functional, and a standalone Tooling `POST /tooling/sobjects/EmbeddedServiceConfig` dead-ends headlessly demanding the wizard-minted `SiteId`), so splitting the two buys nothing.
   - **Setup path:** Setup → Messaging Settings → **New Channel** → **Start** → **Native Channels → Enhanced Chat** → Next.
   - **Name your channel:** set **Channel Name** + **Developer Name**; **Deployment Type = Web**; **Domain** = the org's Experience Cloud Sites domain (Setup → Domains → the row whose *Current Domain Configuration Option* is **Experience Cloud Sites Domain**) → Next.
   - **Channel Routing:** **Routing Type = Omni-Flow**; **Flow Definition** = the inbound flow from sub-step 4; **Fallback Queue** = the queue from sub-step 3 — both are required to Save, so a missing/wrong selection here is a loud failure, not a silent one → **Save**.
   - **WARNING: The channel cannot be torn down afterward — neither API nor UI** (not API-deletable; Setup offers no delete for a channel either). Create deliberately — the only "undo" is leaving it inactive.
   - **Auth/AEA channel only — enable user verification** [T3, in the channel edit screen]: Setup → Messaging Settings → in the **row-level dropdown for your channel select Edit** (do NOT click into the channel and hit Edit there — that only edits the name/API name) → check **Add User Verification** → Save. **Ignore the *Authorization Token Expiration Time* box** — credential-based verification is fixed at 15 minutes (auto-renewing), so that value has no effect. The unauthenticated/Service (ASA) channel gets **no** user verification.
6. **Back to the site — confirm it's ready, then finish it** [**T3** — read T1, everything else UI] — one per agent; this is where the sub-step-5 deployment's component actually gets placed, so it's the last thing touched even though creation (sub-step 1) happened first. Do **not** conflate the placement site with the ESD's internal **ESW plumbing site** (sub-step 5): the ESW site is auto-provisioned by the deployment wizard to host the embedded endpoint; the placement site here is the deliberate, customer-facing one from sub-step 1.
   - **Re-check `Network` — T1** (`GET /connect/communities` → 200, or the `Network` query) — confirm the sub-step-1 site(s) reached `Status = Live`. If still provisioning, that's fine — none of sub-steps 2–5 depend on it; just don't publish until it's `Live`.
   - **CRITICAL: Add the Embedded Messaging component and suppress the raw JSON output before publishing [T3, manual, Experience Builder].** By default the agent renders the **raw JSON** its actions return, which is unusable for a prospective student, and the messaging widget isn't on the page until it's placed there:
     1. **Add the component.** Setup → Digital Experiences → **All Sites** → click **Builder** next to the site's name (not **Workspaces** — that opens a different screen) → Experience Builder opens → the **Components** icon in the left nav → search "embedded" → drag **Embedded Messaging** (under the *Support* category) anywhere onto the page. **WARNING: Don't confuse it with `Embedded Service Chat`**, a similarly-named, similarly-iconed component in the same *Support* category — that's the older live-chat widget, not this deployment's component.
     2. **Disable streaming responses.** Add this to the site's page `<head>` markup (Experience Builder → Settings → Advanced → Edit Head Markup):
        ```html
        <script>
          window.addEventListener('onEmbeddedMessagingReady', () => {
            embeddedservice_bootstrap.settings.disableStreamingResponses = true;
          });
        </script>
        ```
     3. **Set the security level to Relaxed CSP.** Setup → Digital Experiences → the site → **Security & Privacy** → Security Level → **Relaxed CSP: Permit Access to Inline Scripts and Allowed Hosts** (the inline `<script>` above won't run under the stricter default CSP).
     4. **Trust the site's own host for scripts.** Add the site as a trusted site for scripts (Security & Privacy → Trusted URLs / *Allow Hosts of Script Resources*). Get the site URL from Setup → Digital Experiences → **All Sites** → the site's URL in the list view.
     5. **Auth/AEA site only — activate user verification on the component** [T3, Experience Builder]: highlight the **Embedded Messaging** component → in the property editor check **Add credential-based user verification**. This is the site-side half of the channel's Add-User-Verification checkbox (sub-step 5); both must be set for the authenticated path. Skip on an unauthenticated/Service site.
     6. **Publish (or re-publish) the site** so the component, head markup, CSP changes, and (auth path) the verification setting all go live.

> **Note on ordering:** site *creation* (sub-step 1) is front-loaded because it's the slowest part of this stack; the `MessagingChannel`/ESD it will eventually host (sub-step 5) are built independently in the meantime and only get embedded into the site at sub-step 6. The ESD does bind to its own internal ESW plumbing site, minted by the same deployment wizard — never the sub-step-1/sub-step-6 placement site.

### Inbound routing flow — two shapes

`ProcessType` is **`RoutingFlow`** (the Flow Builder UI labels this "Omni-Channel Flow," but the stored process type is `RoutingFlow` — verify on `ProcessType`, not the UI label). Each flow's `{!recordId}` is the `MessagingSession` Id. The whole lifecycle — author (`save`) → activate → verify — is **tier 1 headless**. Do **not** use a template — author the elements directly.

**Author — `POST /flowbuilder/flow/actions/save` (`saveType:"createNewFlow"`, `builderType:"FlowBuilder"`), T1 both shapes.** Same tier-1 surface used for the admissions flows — note the `/actions/` segment; the bare `/flowbuilder/flow/save` path 405s `METHOD_NOT_ALLOWED` (GET/HEAD only).
- **WARNING: Save-contract:** send **only `fullName` + `metadata`** on the flow object. Including top-level `status`/`processType`/`masterLabel`/`label` alongside `metadata` → `400 "Only the Metadata and FullName fields may be specified on Flow…"`. (`validate-flow` is lenient; `save` enforces it.)
- **WARNING: The `recordId` String input variable is REQUIRED** and may be missing from a UI screenshot — add it explicitly (the Route Work `recordId` input is an `elementReference` to it).

**Activate — Tooling `FlowDefinition` PATCH is the reliable path (NOT `/flowbuilder/.../activate`).** Walk this ladder:
1. **Primary (the path that returns 204):** query `FlowDefinition` by DeveloperName (`SELECT Id, DeveloperName, ActiveVersionId FROM FlowDefinition WHERE DeveloperName='<apiName>'` → the `300`-prefix def Id), then `PATCH /tooling/sobjects/FlowDefinition/{defId}` `{"Metadata":{"activeVersionNumber":N}}` (N = version, usually 1) → **204**. Deactivate with `activeVersionNumber:0`.
2. **Optional native endpoint:** `POST /flowbuilder/flow/{flowId}/actions/activate?builderType=FlowBuilder` — not reliably available (it 404s on some orgs). If preferred, try it first and **fall back to the FlowDefinition PATCH on a 404**. Do **NOT** use `PATCH /tooling/sobjects/Flow/{flowId}` `{Metadata:{status:'Active'}}` — that overwrites the version body and returns `400 INVALID_STATUS` once a version has been active.
3. **UI last:** Setup → Flows → activate.

Then verify on `FlowDefinitionView` (`SELECT ApiName, IsActive, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='<apiName>'` → `IsActive:true`). If any leg fails, fall back to building/activating the flow in the UI (Setup → Flows → New → *Omni-Channel Flow*).

**Route Work element inputs (both flows):** *How Many Work Records* = **Single**; *Record ID Variable* = `{!recordId}`; *Service Channel* = **Messaging**; *Fallback Queue* = the per-agent queue from sub-step 3.

**WARNING: The Route Work agent parameter encoding DIFFERS by agent type** — do not reuse the Service-agent field for an Employee agent:
- **Service / ASA (unauthenticated):** `routingType:"Copilot"`; agent → **`copilotId`** setupReference (the `BotDefinition` DeveloperName) + `copilotLabel`.
- **Employee / AEA (authenticated):** `routingType:"AgentforceEmployeeAgent"`; agent → **`agentforceEmployeeAgentId`** setupReference (the `BotDefinition` DeveloperName) + `agentforceEmployeeAgentLabel`; **leave `copilotId` empty.**
- **Both share:** `recordId` input (elementReference to the `recordId` variable); the service channel as **three** inputs — `serviceChannelId` setupReference `sfdc_livemessage` (setupReferenceType `ServiceChannel`) + `serviceChannelDevName` **stringValue** `sfdc_livemessage` + `serviceChannelLabel:"Messaging"`; `queueId` as a plain **stringValue** (the 18-char `00G…` queue Id, NOT a setupReference) + `queueLabel`.

- **Service / ASA (unauthenticated) — minimal.** The ASA runs as the Einstein Agent User service account with no end-user to resolve, so route straight through:
  ```text
  Start → Route to ASA Agent (Route Work) → End
  ```
- **Employee / AEA (authenticated) — user-resolution chain before Route Work.** Resolve the verified end-user to their Contact and stamp it on the Messaging User before routing:
  ```text
  Start
    → Get Messaging Session   (Get Records; Messaging Session ID = {!recordId})
    → Get Messaging User      (Messaging User ID = {!Get_Messaging_Session.MessagingEndUserId})
    → Get User                (User ID = {!Get_Messaging_User.AuthenticatedEndUserId})
    → Update Messaging User   (find by Messaging User ID = {!Get_Messaging_Session.MessagingEndUserId};
                               set Contact ID = {!Get_User.ContactId})
    → Route to AEA Agent (Route Work)
    → End
  ```
  Element API names (underscore form, matching the platform's own emitted flow): `Get_Messaging_Session`, `Get_Messaging_User`, `Get_User`, `Update_Messaging_User`, `Route_to_AEA_Agent` (ASA uses `Route_to_ASA_Agent`). The `elementReference` expressions above must use these exact names.

## Verify deployment (concrete calls — run after channel setup)

`/query` and `/headless/metadata` GET route over `dispatch_readonly` (tier 1) — attempt tier 1 first for each read, falling back to tier 2 (`sf`) or a tier-3 UI check. **For verifying a specific record you just created (known Id), prefer an sObject GET-by-Id (`/sobjects/<Type>/<Id>` over `dispatch_readonly`) over a `/query` filter** — it is the more robust cold-read for a known Id and confirms the persisted field values (including an inline FK like `Group.QueueRoutingConfigId`) directly. Use `/query` for the population/existence sweeps below where no Id is known yet.

```bash
# Tier 1 first: dispatch_readonly /query with the equivalent SOQL below; fall back to tier 2 (sf).
# Omni-Channel enabled (headless GET; confirm enableOmniChannel true in the xmlRep).
# Experience Cloud sites (one per agent, Live):
sf data query -q "SELECT Id, Name, Status FROM Network" --target-org <alias>
# Messaging channels (one per agent) — NOTE: no ChannelType column:
sf data query -q "SELECT Id, MasterLabel, MessageType, MessagingPlatformKey FROM MessagingChannel" --target-org <alias>
# Per-agent fallback queues (Group), their supported objects (expect MessagingSession + MessagingEndUser), and members:
sf data query -q "SELECT Id, DeveloperName, Type, QueueRoutingConfigId FROM Group WHERE Type='Queue'" --target-org <alias>
sf data query -q "SELECT QueueId, SobjectType FROM QueueSobject" --target-org <alias>
sf data query -q "SELECT GroupId, UserOrGroupId FROM GroupMember WHERE Group.Type='Queue'" --target-org <alias>
# Per-agent routing configs:
sf data query -q "SELECT Id, DeveloperName FROM QueueRoutingConfig" --target-org <alias>
# Inbound routing flows active (query by ApiName; ProcessType RoutingFlow):
sf data query -q "SELECT ApiName, ProcessType, IsActive FROM FlowDefinitionView WHERE ProcessType='RoutingFlow'" --target-org <alias>
```
Confirm one site, one messaging channel, one queue, one routing config, and one active `RoutingFlow` **per agent**, and the sites are `Live`.

## Step 13 — Final structural verification

Run the headless structural roll-up and summarize; **do not wait on any manual action.** This is the last skill-run step — everything here is queryable, so it never blocks on the user.

**Structural roll-up (headless, tier 1):** confirm the agent is active, all subagents are present, the ASA flows are active, and the channel + site are up — via `/query` / `/tooling/query` over `dispatch_readonly` (the per-layer verify queries above plus the agent/subagent checks in `agent-and-subagents.md`). Then summarize which tier each step landed on (headless / `sf` CLI / manual UI) and list anything left manual on the T3-only steps.

**Conversational smoke test — hand to the user, do NOT verify inline.** Messaging the deployed agent (subagents respond, Learning Program + Knowledge grounding answer, the record-creating actions fire) needs a live channel session that can't be driven headlessly — and polling for records the user hasn't created yet would hang. So **finish the skill on the structural roll-up** and leave the user a short checklist to run themselves once live:

- Message each subagent — Admissions and Enrollments FAQ, Admissions Application, Campus Tours, Visits, and Events Registration, Request for Information, and Escalation — and confirm it responds.
- Ask a program/FAQ question and confirm grounded, cited answers come back.
- Exercise Create Inquiry / Campus Tour Registration / Admissions Application / Academic Interest, then confirm the records landed (list view / report, or a `SELECT … ORDER BY CreatedDate DESC` query if they have a shell).

**Do not create customer data during or after this build** — this skill wires configuration and grounding, not org content. Once the structural roll-up is done, close with this guidance to the customer:

- *"The agent is configured and ready to answer questions from what's already in Knowledge and Data Cloud. To keep FAQ answers current, keep adding Knowledge articles — newly published ones are picked up automatically, no re-wire needed."*
- *"To support Request for Information and Campus Tours, make sure your Recruitment & Admissions data is populated — Learning Programs, Academic Terms, and the Campaigns tied to campus tours/events. Without that data, those subagents have nothing to retrieve or register against."*
- If the customer then asks Claude to create a specific program, term, or campaign for them, that's outside this skill's scope — say so rather than building it inline here.
