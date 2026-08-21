# Embedded Agentforce Employee Agent in Microsoft Teams (verified recipe — build from scratch, 100% API)

Making the embedded Agentforce agent ("IT Service Employee Agent") actually reply inside the
Microsoft Teams custom client ("Salesforce Employee Assist" / "Ask AI Agent") is the hardest,
most under-documented part of Teams ITSM. Everything below is **verified end-to-end against a
real org** — the agent returns contextual replies inside Teams — and **every step has a working
API path, so the whole build runs headlessly with zero Setup-UI clicks.** The Teams custom client
loads the deployment named **exactly** `Teams_AgentForce` (hard-wired in committed Core config —
you cannot rename it per-org).

## The blessed architecture: Web channel + User Verification ON + a JWKS_URL Key Set

This is the product-provided manual, verified working. The agent replies when **all** of these are true:

1. A **Web** Enhanced-messaging channel routing (Omni-Flow) to a real, Active IT Service Employee Agent.
2. **User Verification ON** on that channel (`<embeddedConfig><authMode>Auth</authMode>`).
3. An **Enhanced Chat User Verification Key Set** (`PublicKeyCertificateSet`, type **`JWKS_URL`**)
   whose endpoint is `<Org_Url>/id/keys` and whose issuer is the **Employee Site URL**, **linked
   into the channel** via `<embeddedConfig><messagingAuthorizations>`.
4. The **`Teams_AgentForce`** custom-client Embedded Service Deployment (Enhanced Chat), linked to
   the channel and **published**.
5. The **portal user has an "Agent Access" permission set** enabling the IT Service Employee Agent.

Miss #2+#3 together, or #5, and you get the classic "agent joins the conversation, then leaves,
no reply" symptom.

> **This corrects an earlier version of this recipe** that insisted User Verification must be
> **OFF** and that a Key Set must **not** be attached. That was wrong — it was diagnosed on a
> build that turned **auth ON but never attached a Key Set**, so the Teams client fell back to the
> scrt2 *unauthenticated* token endpoint, which rejects an auth-ON channel with `BAD_REQUEST`
> "Set the auth mode to false." **The fix is not to turn auth off — it is to attach the Key Set.**
> With a Key Set present, the Teams client uses the *authenticated* token flow that the auth-ON
> channel expects, and the agent replies. The verified, product-blessed build is **auth ON +
> JWKS_URL Key Set** (screenshot-confirmed live).

## Concept map (what the Teams custom client actually needs)

| Layer | Object | Role |
|-------|--------|------|
| Deployment | `EmbeddedServiceConfig` (ESD), **named `Teams_AgentForce`**, Enhanced-chat **custom client** | The deployment the Teams app loads by its `DeveloperName` (`esDeveloperName`). Stored with `deploymentType: API` / `site: null` in Metadata even though the wizard flow is "Web / custom client" — that is expected. |
| Channel | `MessagingChannel` (MessageType=`EmbeddedMessaging`), **Web** deployment, **User Verification ON** | The Enhanced messaging channel. Domain = the Employee Site URL. Routes via `sessionHandlerFlow`/`SessionHandlerId`. `<embeddedConfig><authMode>Auth</authMode>` + a linked Key Set. |
| **Key Set** | **`PublicKeyCertificateSet`, type `JWKS_URL`** | Enhanced Chat User Verification Key Set. `jwksEndPoint` = `<Org_Url>/id/keys`; `jwtIssuer` = Employee Site URL. Linked into the channel's `<embeddedConfig><messagingAuthorizations>`. |
| Routing | `Flow` (ProcessType=`RoutingFlow`) → `FlowDefinitionView` | An Omni **RoutingFlow** whose `routeWork` action hardcodes the target agent id in `agentforceEmployeeAgentId`. |
| Agent | `BotDefinition` (Type=`InternalCopilot`, AgentType=`AgentforceEmployeeAgent`) + Active `BotVersion` | The Agentforce agent that generates replies. |
| **Agent access** | **Permission set with "Agent Access" → the IT Service Employee Agent**, assigned to the **portal user** | Without this, routing delivers the work but the running user cannot access the agent, so it joins then immediately leaves with no reply. |

## The full headless build (maps 1:1 to the product manual — zero manual steps)

The product manual and its API equivalent, step for step. All deploys use an isolated
`sfdx-project.json` (packageDir `force-app`) at `--api-version 67.0`. Run one step at a time.

| Manual step | API step |
|-------------|----------|
| 1–4. Setup → Messaging Settings → New channel; name; deployment type **Web**; domain = Employee Site URL | **§A** — Metadata-deploy the `MessagingChannel` |
| 5–6. Routing type = **Omni-Flow** → Flow = "Route to AEA"; Fallback Queue = chat_queue; Save | Channel `sessionHandlerFlow`/`sessionHandlerQueue` (§A) — the flow + queue must pre-exist (§E/§F) |
| 7. Enable **Add User Verification** + Save | Channel `<embeddedConfig><authMode>Auth</authMode>` (§A) |
| 8. Setup → Enhanced Chat User Verification → **New Key Set** (issuer = Site URL, endpoint = `<Org>/id/keys`) | **§B** — Metadata-deploy the `PublicKeyCertificateSet` (type `JWKS_URL`) |
| 9. Attach the Key Set to the channel (User Verification Configuration) | Channel `<embeddedConfig><messagingAuthorizations>` (§A) — deploy the Key Set **first**, then the channel |
| 10. New ESD → Enhanced Chat → Custom Client → name `Teams_AgentForce` → select the channel | **§C** — Metadata-deploy the `API`-type ESD |
| 11. Save & Publish | **§D** — Connect publish |
| (access) Permission set → Agent Access → the agent, assigned to the portal user | **§G** |

Deploy order matters: **Key Set (§B) → Channel (§A, which references the Key Set) → activate the
channel → ESD (§C) → publish (§D).** (The routing flow §E and fallback queue §F are prerequisites
of the channel — build/verify them first if they don't already exist.)

### §A. The `MessagingChannel` (Web, auth ON, Key Set linked)

`force-app/main/default/messagingChannels/<DevName>.messagingChannel-meta.xml`. The
`publicKeyCertificateSetName` must match the Key Set's dev name from §B, so **deploy the Key Set
first.** `sessionHandlerFlow` = the routing flow's dev name (e.g. `Route_To_MIAW_AEA`);
`sessionHandlerQueue` = the fallback queue's dev name (e.g. `chatqueue`).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MessagingChannel xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Teams AgentForce</masterLabel>
    <messagingChannelType>EmbeddedMessaging</messagingChannelType>
    <sessionHandlerFlow>Route_To_MIAW_AEA</sessionHandlerFlow>
    <sessionHandlerQueue>chatqueue</sessionHandlerQueue>
    <sessionHandlerType>Flow</sessionHandlerType>
    <embeddedConfig>
        <authMode>Auth</authMode>
        <messagingAuthorizations>
            <authorizationType>PublicKeyCertificateSet</authorizationType>
            <publicKeyCertificateSetName>Teams_AgentForce_KeySet</publicKeyCertificateSetName>
            <enabled>true</enabled>
            <authIdentifier>Teams_AgentForce_KeySet</authIdentifier>
        </messagingAuthorizations>
    </embeddedConfig>
</MessagingChannel>
```

```bash
sf project deploy start --metadata "MessagingChannel:<DevName>" \
  --target-org <org-alias> --api-version 67.0 --dry-run   # validate
sf project deploy start --metadata "MessagingChannel:<DevName>" \
  --target-org <org-alias> --api-version 67.0             # deploy
```

A freshly-deployed channel may be **`IsActive=false`** — activate it before publishing the ESD:

```text
# data-API record update (MessagingChannel is a data-API object, not Tooling)
sf data update record --sobject MessagingChannel --record-id <channelId> --values "IsActive=true"
```

Verify:

```text
SELECT Id, DeveloperName, IsActive, SessionHandlerId, ChannelAddressIdentifier, MessageType
  FROM MessagingChannel WHERE DeveloperName='<DevName>'
#   IsActive=true, MessageType=EmbeddedMessaging, SessionHandlerId resolves to the routing flow.
```

### §B. The Enhanced Chat User Verification Key Set (`PublicKeyCertificateSet`, `JWKS_URL`)

`force-app/main/default/PublicKeyCertificateSet/<DevName>.PublicKeyCertificateSet-meta.xml`.

> **Casing is load-bearing.** The directory must be `PublicKeyCertificateSet/` (capital P), and the
> file suffix must be `.PublicKeyCertificateSet-meta.xml`. Lowercase (`publicKeyCertificateSets/` /
> `.publicKeyCertificateSet-meta.xml`) fails with a `TypeInferenceError`.

> **The enum is `JWKS_URL`.** `PublicKeyCertificateSetType` has two values: **`JWKS_URL`** (retrieve
> keys from the remote `jwksEndPoint` — this is the mode the manual uses) and **`Jwks`** (an
> uploaded/local key via child `PublicKeyCertificateSetKey`). `Jwks` **rejects** a `jwksEndPoint`
> with "You can't configure JWKS_URL when the key type selected is JWKS_KEY." Use `JWKS_URL`. The
> sObject has **no REST describe** (both data-API and Tooling `/sobjects/PublicKeyCertificateSet/describe`
> return `NOT_FOUND`), so this enum can only be confirmed from the Metadata API docs — do not
> blind-guess camelCase variants (`JwksUrl`, `JwksEndpoint`, `RemoteJwks`, `SelfSignedCert`, … all
> fail enum validation).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PublicKeyCertificateSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>Teams AgentForce KeySet</masterLabel>
    <type>JWKS_URL</type>
    <jwksEndPoint>https://<org>.my.salesforce.com/id/keys</jwksEndPoint>
    <jwtIssuer>https://<org>.my.site.com/<sitePath></jwtIssuer>
</PublicKeyCertificateSet>
```

- `jwksEndPoint` = the org's **My Domain URL** + `/id/keys` (the `<Org_Url>/id/keys` from the manual).
- `jwtIssuer` = the **Employee Site URL** (Setup → All Sites → the employee portal).

```bash
sf project deploy start --metadata "PublicKeyCertificateSet:<DevName>" \
  --target-org <org-alias> --api-version 67.0 --dry-run   # validate
sf project deploy start --metadata "PublicKeyCertificateSet:<DevName>" \
  --target-org <org-alias> --api-version 67.0             # deploy
```

### §C. The `Teams_AgentForce` ESD (Enhanced Chat custom client, `API`-type)

`force-app/main/default/embeddedServiceConfigs/Teams_AgentForce.EmbeddedServiceConfig-meta.xml`.
The file/dir name **and** `<messagingChannel>` must be the channel's **metadata developer name**
(not its Id). `deploymentType` is **`API`** and `site` is left **null** — Teams stores the
Enhanced-chat custom-client deployment this way, so **no ESW Picasso site is required** (the Tooling
create of a *Web* ESD does need a platform-managed ESW site and fails `UNKNOWN_EXCEPTION` without
one — the Metadata `API`-type deploy sidesteps that entirely).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<EmbeddedServiceConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <areGuestUsersAllowed>false</areGuestUsersAllowed>
    <deploymentFeature>EmbeddedMessaging</deploymentFeature>
    <deploymentType>API</deploymentType>
    <embeddedServiceMessagingChannel>
        <isChatInvitationCustomizable>false</isChatInvitationCustomizable>
        <isEnabled>true</isEnabled>
        <isInvitationEnabled>false</isInvitationEnabled>
        <isSendInvtAllowedAfterAccept>false</isSendInvtAllowedAfterAccept>
        <isSendInvtAllowedAfterReject>false</isSendInvtAllowedAfterReject>
        <messagingChannel>Teams_AgentForce_Channel</messagingChannel>
        <shouldShowAgentforceTagline>false</shouldShowAgentforceTagline>
        <shouldShowDeliveryReceipts>false</shouldShowDeliveryReceipts>
        <shouldShowEmojiSelection>false</shouldShowEmojiSelection>
        <shouldShowReadReceipts>false</shouldShowReadReceipts>
        <shouldShowTypingIndicators>false</shouldShowTypingIndicators>
        <shouldStartNewLineOnEnter>false</shouldStartNewLineOnEnter>
    </embeddedServiceMessagingChannel>
    <isEnabled>true</isEnabled>
    <isTermsAndConditionsEnabled>false</isTermsAndConditionsEnabled>
    <isTermsAndConditionsRequired>false</isTermsAndConditionsRequired>
    <masterLabel>Teams AgentForce</masterLabel>
    <shouldHideAuthDialog>false</shouldHideAuthDialog>
</EmbeddedServiceConfig>
```

> Replace `Teams_AgentForce_Channel` with **your channel's** dev name from §A. The ESD's own
> dev/file name must remain exactly **`Teams_AgentForce`** (Teams hard-codes `esDeveloperName`).

```bash
sf project deploy start --metadata "EmbeddedServiceConfig:Teams_AgentForce" \
  --target-org <org-alias> --api-version 67.0 --dry-run   # validate
sf project deploy start --metadata "EmbeddedServiceConfig:Teams_AgentForce" \
  --target-org <org-alias> --api-version 67.0             # deploy
```

Get the ESD Id (Tooling):

```text
SELECT Id, DeveloperName FROM EmbeddedServiceConfig WHERE DeveloperName='Teams_AgentForce'
```

### §D. Publish the ESD (Connect API — makes it live)

```text
POST /services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<esdId>
body: {}
#   → 201 {"isSuccess": true}
```

The publish endpoint is **v67.0** (it 404s at v62/v64). Check `isSuccess:true`; publish can take up
to ~10 minutes to propagate. Then **retest from a brand-NEW Teams chat** — existing sessions bind
to the prior config.

### §E. The routing flow (`Route_To_MIAW_AEA`)

The channel's Omni-Flow target. When the agent is created via the **template-install path**, the org
already has a `Route_To_MIAW_AEA` `RoutingFlow` — but its `routeWork` action ships with **placeholder
ids** (e.g. `agentforceEmployeeAgentId=0Xxxx0000000001CAA`, `serviceChannelId=0N9xx…`, `queueId=00Gxx…`,
label "Agentforce HR Service Agent"). Left as-is it silently misroutes (agent joins then leaves).
**Repoint it to the real records before using the channel:**

1. Retrieve: `sf project retrieve start --metadata "Flow:Route_To_MIAW_AEA"` (create `force-app/main/default`
   + a minimal `sfdx-project.json` first).
2. In `routeWork`, set:
   - `agentforceEmployeeAgentId` → the **real** Active `BotDefinition` Id (`0Xx…`) — the same agent
     the Agent Access permset (§G) enables; **these two MUST match**.
   - `serviceChannelId` → real `sfdc_livemessage` `ServiceChannel` Id
     (`SELECT Id FROM ServiceChannel WHERE DeveloperName='sfdc_livemessage'` — standard, pre-existing).
   - `queueId` → the fallback queue's `Group` Id (§F).
   - `agentforceEmployeeAgentLabel` → the real agent label (cosmetic).
3. Deploy: `sf project deploy start --metadata "Flow:Route_To_MIAW_AEA"`. Deploying an Active flow
   makes a **new active version** (`FlowDefinitionView.DurableId` — the channel's `SessionHandlerId`
   — is unchanged; only `ActiveVersionId` bumps). Confirm:
   `SELECT DurableId, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='Route_To_MIAW_AEA'`.

If **no** routing flow exists at all, author one from scratch — the load-bearing `routeWork`
input parameters (verified from a live working flow) are:

- `routingType` = `AgentforceEmployeeAgent`
- `agentforceEmployeeAgentId` = the real, Active `BotDefinition` Id (must match the Agent Access permset)
- `serviceChannelDevName` = `sfdc_livemessage`, `serviceChannelLabel` = `Messaging`
- `serviceChannelId` = the Messaging `ServiceChannel` Id; `queueId` = the fallback queue's `Group` Id
- `recordId` = `{!recordId}` (input variable, elementReference)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>65.0</apiVersion>
    <actionCalls>
        <name>routeWork</name>
        <actionName>routeWork</actionName>
        <actionType>routeWork</actionType>
        <label>Route To MIAW AEA</label>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>recordId</name>
            <value><elementReference>recordId</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>routingType</name>
            <value><stringValue>AgentforceEmployeeAgent</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>agentforceEmployeeAgentId</name>
            <value><stringValue><REAL_ACTIVE_BOTDEFINITION_ID></stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelDevName</name>
            <value><stringValue>sfdc_livemessage</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelLabel</name>
            <value><stringValue>Messaging</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelId</name>
            <value><stringValue><SERVICE_CHANNEL_ID></stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>queueId</name>
            <value><stringValue><FALLBACK_QUEUE_GROUP_ID></stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>queueLabel</name>
            <value><stringValue>chatqueue</stringValue></value>
        </inputParameters>
    </actionCalls>
    <label>Route To MIAW AEA</label>
    <processType>RoutingFlow</processType>
    <start>
        <connector><targetReference>routeWork</targetReference></connector>
    </start>
    <status>Active</status>
    <variables>
        <name>recordId</name>
        <dataType>String</dataType>
        <isInput>true</isInput>
        <isCollection>false</isCollection>
        <isOutput>false</isOutput>
    </variables>
</Flow>
```

A subtly-wrong `routeWork` param set silently misroutes — most commonly a **ghost/mismatched
`agentforceEmployeeAgentId`** (points at a deleted agent, or one the portal user's Agent Access
permset doesn't enable → "joins then leaves, no reply").

### §F. The fallback queue (prerequisite of the routing flow)

The `routeWork` references a **queue** (`queueId`) as fallback. A "queue" is a `Group` of
`Type='Queue'` plus one `QueueSobject` per Messaging object it routes. Reuse an existing one if
present (`chatqueue`) — do not create a duplicate (`DeveloperName` must be unique;
`DUPLICATE_DEVELOPER_NAME` on a second `chatqueue`).

```text
# reuse if it exists
SELECT Id, Name, DeveloperName, Type FROM Group WHERE Type='Queue' AND DeveloperName='chatqueue'

# else create the Group…
POST /services/data/v67.0/sobjects/Group   body: {"Name":"chatqueue","DeveloperName":"chatqueue","Type":"Queue"}
# …then a QueueSobject per object (verified set: MessagingSession, MessagingEndUser, LiveChatTranscript)
POST /services/data/v67.0/sobjects/QueueSobject   body: {"QueueId":"<00G…>","SobjectType":"MessagingSession"}
#   repeat for MessagingEndUser and LiveChatTranscript

# verify (expect 3 rows)
SELECT Id, QueueId, SobjectType FROM QueueSobject WHERE QueueId='<00G…>'
```

The Omni service channel `sfdc_livemessage` the flow references is **standard/pre-existing** — query,
don't create: `SELECT Id, DeveloperName, RelatedEntity FROM ServiceChannel WHERE DeveloperName='sfdc_livemessage'`.

### §G. Agent Access permission set (required — the piece most often missing)

Routing delivers the work, but the **running portal user must be able to access the agent** or it
joins then immediately leaves with zero `ConversationEntry`.

- Create a dedicated permission set (label e.g. "Agent Access").
- Enable the **IT Service Employee Agent** under its **Agent Access** section. By API, this is a
  `SetupEntityAccess` row keyed on the agent's `BotDefinition` Id (no `SetupEntityType` needed — it
  auto-resolves). See the project memory note on granting embedded-agent access.
- **Assign the permission set to the portal user** (the user who signs in through Teams).

> **RBAC note.** Creating/assigning a permission set is a permission grant — get explicit user
> approval before assigning it, per standing policy.

## Prerequisite: the IT Service Employee Agent must exist and be Active (two provisioning paths)

The whole recipe needs a **real, Active** `BotDefinition` with `AgentType='AgentforceEmployeeAgent'`
(query: `SELECT Id FROM BotDefinition WHERE AgentType='AgentforceEmployeeAgent'`, with an `Active`
`BotVersion`). Two ways it gets created — **verify live, don't assume**:

1. **Feature-enable auto-provision (some orgs).** Enabling `service-cloud-it-service-employee-agent`
   via `POST /connect/setup/discovery/feature/service-cloud-it-service-employee-agent/enable` kicks
   off an async job that *may* create the agent, its ESD, an ESW Picasso `Site`, and its channel —
   **not guaranteed** (verified: in one org the feature flipped `ENABLED` but provisioned nothing).
2. **Explicit create + activate (reliable).** Use **`service-itsm-agentic-setup-employee-agent-configure`**
   (reads the shipped Employee template's Agent Script and creates + publishes + activates the agent
   as an NGA-native bundle). The equivalent underlying path is the ITSM Connect **agent-templates
   install + activate** against `EmployeeCopilot__AgentforceEmployeeAgent`:
   - `GET /connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent` — find
     `EmployeeCopilot__AgentforceEmployeeAgent`; its `agentScript` is HTML-entity-encoded (unescape it).
   - `POST /connect/service-itsm/agent-templates` with `agentConfigs:[{agentName, agentScript, companyDescription, templateId}]`
     → creates + publishes (BotVersion starts **Inactive**).
   - `POST /connect/service-itsm/activate-agents` with `{"agentTemplateIds":["EmployeeCopilot__AgentforceEmployeeAgent"]}`
     → flips `BotVersion` to **Active**.
   - Capture the new `BotDefinition` Id (`0Xx…`) — it is the `agentforceEmployeeAgentId` for the
     routing flow **and** the agent the Agent Access permset (§G) enables; the two MUST match.

Deploy the agent first, then run this recipe to embed it in Teams.

## Verify the chain via API (after publish + assignment)

```text
# Channel active + routes
SELECT Id, DeveloperName, IsActive, SessionHandlerId, ChannelAddressIdentifier, MessageType
  FROM MessagingChannel WHERE DeveloperName='<DevName>'
#   IsActive=true; ChannelAddressIdentifier must match the channelAddId claim in the scrt2 token JWT.

# Routing flow targets a REAL, Active agent
SELECT DurableId, ApiName, ActiveVersionId FROM FlowDefinitionView WHERE DurableId='<SessionHandlerId>'
SELECT Id, FullName, Metadata FROM Flow WHERE Id='<ActiveVersionId>'   (Tooling)
#   → inputParameters[name=agentforceEmployeeAgentId].value.stringValue  ← must be a real agent
SELECT Id FROM BotDefinition WHERE Id='<that id>'                       # ghost id → 0 rows
SELECT Id, DeveloperName, Status FROM BotVersion WHERE BotDefinitionId='<that id>'   # need Status=Active

# ESD published + linked
GET /services/data/v67.0/tooling/sobjects/EmbeddedServiceConfig/<esdId>

# Key Set exists
SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='Teams_AgentForce'   (Tooling)

# Portal user actually has the agent enabled (Agent Access)
SELECT Id, PermissionSetId, AssigneeId FROM PermissionSetAssignment WHERE AssigneeId='<portalUserId>'
#   One assigned set must be the "Agent Access" set that enables the IT Service Employee Agent.
```

## "Agent joins then leaves" (no reply) — diagnose, don't hand-wave

Work through these before escalating to the Agentforce team:

1. **User Verification / Key Set mismatch.** If the scrt2 token call returns `BAD_REQUEST`
   "Set the auth mode to false" and there is **no Key Set attached**, the client is on the
   *unauthenticated* endpoint while the channel demands auth. **Attach a JWKS_URL Key Set (§B) and
   link it into the channel (§A)** — do **not** turn auth off. Conversely, if a Key Set is attached
   but its `jwksEndPoint`/`jwtIssuer` are wrong, the authenticated mint fails → 401 on
   `/eventrouter/v1/sse`. Fix the endpoint (`<Org>/id/keys`) / issuer (Employee Site URL).
2. **Portal user lacks Agent Access.** Tokens mint, SSE connects, but the agent joins then leaves
   with no `ConversationEntry` → the running user cannot access the agent. Create + assign the
   Agent Access permset (§G).
3. **The `Teams_AgentForce` ESD does not exist** (`SELECT Id FROM EmbeddedServiceConfig WHERE
   DeveloperName='Teams_AgentForce'` → 0 rows) — the Teams client can't load a missing deployment.
   Create + publish it (§C/§D).
4. **Routing flow points at a placeholder/ghost agent id** — repoint `Route_To_MIAW_AEA` (§E).

Diagnostic queries:

```text
# Sessions on the channel
SELECT Id, Status, StartTime, EndTime, OwnerId, Origin, CreatedDate
  FROM MessagingSession WHERE MessagingChannelId='<channelId>' ORDER BY CreatedDate DESC
#   Broken: Status 'Waiting'/'Ended' quickly, OwnerId = the QUEUE (00G… Group), never the agent.
#   Working: session goes Active and an agent-authored entry appears.

# Conversation entries — who actually spoke
SELECT Id, ConversationId, EntryType, ActorType, ActorName, CreatedDate
  FROM ConversationEntry WHERE ConversationId='<messagingSessionId>' ORDER BY CreatedDate ASC
#   Broken: zero entries (or only user entries). Working: an entry with ActorType=Agent/Bot
#   ("IT Service Employee Agent") carrying the reply text.
```

If the agent *still* won't reply after all of the above are confirmed (auth ON + Key Set linked,
Agent Access assigned, ESD created + published, flow points at the real Active agent), **delegate to
`service-itsm-teams-debug`** — its `AGENTFORCE` pass/fail checklist walks the whole
token/routing/ESD/agent chain — before handing off to the Agentforce Employee Agent team (agent Omni
presence / capacity / GenAI planner) as the last resort.

## Gotchas index

Top runtime traps (build-time / API-mechanics issues are in the troubleshooting reference below).

| Issue | Fix |
|-------|-----|
| `/unauthenticated/access-token` → `BAD_REQUEST` "Set the auth mode to false." **and no Key Set attached** | The channel is auth-ON but the client fell back to the *unauthenticated* endpoint because no Key Set is linked. **Attach a `JWKS_URL` Key Set (§B) and link it into `<embeddedConfig><messagingAuthorizations>` (§A)** — do NOT turn auth off. |
| `GET /eventrouter/v1/sse` → **401** with a Key Set attached | The *authenticated* token mint failed — usually a wrong `jwksEndPoint` (must be `<Org>/id/keys`) or `jwtIssuer` (must be the Employee Site URL) on the Key Set. Fix §B and redeploy. |
| Key Set deploy: `'…' is not a valid value for the enum 'PublicKeyCertificateSetType'` | Use **`JWKS_URL`** (endpoint-URL mode). `Jwks` = uploaded-key mode (rejects `jwksEndPoint`). All camelCase guesses (`JwksUrl`, `JwksEndpoint`, `RemoteJwks`, `SelfSignedCert`, …) are invalid. |
| Key Set deploy: `TypeInferenceError` | Directory must be `PublicKeyCertificateSet/` and file suffix `.PublicKeyCertificateSet-meta.xml` (capital, singular). |
| `…/sobjects/PublicKeyCertificateSet/describe` → `NOT_FOUND` (data AND tooling) | This type has no REST describe surface. Confirm the enum from the Metadata API docs, not a describe call. |
| Channel deployed but `IsActive=false` | Activate before publishing the ESD: `sf data update record --sobject MessagingChannel --record-id <id> --values "IsActive=true"`. |
| Agent joins then leaves, no reply, empty `ConversationEntry`, session stays queue-owned | Portal user lacks **Agent Access** (§G), or the routing flow points at a placeholder/wrong agent id (§E). (First rule out the auth/Key-Set chain above.) |
| No agent exists even after enabling `service-cloud-it-service-employee-agent` | Feature auto-provisioning is **not guaranteed**. Fall back to `service-itsm-agentic-setup-employee-agent-configure` (or `agent-templates` install + `activate-agents`). Verify the agent + Active BotVersion by query. |
| `Route_To_MIAW_AEA` (template-installed) has **placeholder** `routeWork` ids | Retrieve → repoint `agentforceEmployeeAgentId`/`serviceChannelId`/`queueId`/label to real records → deploy (new active version; `DurableId`/`SessionHandlerId` unchanged). See §E. |
For build-time deployment and API-mechanics gotchas (ESD create/publish, naming, query surfaces),
see the next section.

## Deployment & API-mechanics troubleshooting reference

Lower-frequency, build-time issues (distinct from the runtime failures in the Gotchas index above) —
kept here as a troubleshooting reference so the Gotchas index stays focused on the top runtime traps:

| Issue | Fix |
|-------|-----|
| ESD create via **Tooling** API fails `UNKNOWN_EXCEPTION` | Only the Tooling create of a Web/custom-client ESD needs a platform-managed ESW Picasso `Site`, and no Connect *create* route exists (only *publish*). Deploy an **`API`-type** ESD via **Metadata API** (`site: null`) and publish it — verified working. §C/§D. |
| ESD publish → `NOT_FOUND` | The publish endpoint is **v67.0**: `POST /services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<esdId>` body `{}`. It 404s at v62/v64. |
| Deployment name must be exactly `Teams_AgentForce` | Teams hard-codes `esDeveloperName=Teams_AgentForce`. Cannot rename per-org; reuse the same DeveloperName if recreating. |
| ESD Metadata shows `deploymentType: API` even for the Web/custom-client wizard | Expected — the Enhanced-chat custom-client deployment is stored as `API` internally (`site: null`). Not a misconfiguration. |
| Publish shows "processing… up to 10 minutes" | Wait for propagation before retesting. |
| Old Teams chat still errors after the fix | Existing sessions bind to the old deployment/config. Always retest from a **brand-new** chat. |
| `MessagingChannel` not queryable via Tooling | It's a data-API object — query via `/services/data/vXX.0/query/`, not `/tooling/query/`. |
| `EmbeddedServiceConfig` not queryable via the data API | Query it via the **Tooling** API (`--use-tooling-api` / `/tooling/query`). |

## Related SSO note

For the Teams app to resolve the Microsoft user to a Salesforce user, the MS `email` claim must
exactly equal a Salesforce `User.Username` (custom Apex handler `MsTeamsItsmSSOHandler`), and the
Azure redirect URI must be registered under the **"Web"** platform, not "Single-page application."
See `service-itsm-teams-configure` and the project memory note on SSO user mapping.
