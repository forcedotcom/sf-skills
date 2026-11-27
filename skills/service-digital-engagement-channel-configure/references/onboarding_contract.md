# Onboarding contract — delegated mode, transport, pre-scan, registration

Read this when `delegationFrom` is set on the invocation, before any org write, or when registering the skill in an
onboarding module. The sibling `service-digital-engagement-deployment-configure` has the same structure.

## 1. Two entry points, one write procedure

| | Delegated | Standalone |
|---|---|---|
| Detected by | `delegationFrom == "service-onboarding"` (alias until onboarding drops it: `context.calledFrom == "service-onboarding"`) | `delegationFrom` absent |
| Values come from | `intent` — prose citing the facts the admin already approved in the plan. Read every Input from it first | you ask for the Inputs in SKILL.md; defaults are in `references/channel_settings.md` |
| Questions | ask only for an Input the `intent` leaves open, plus (a) confirming drift on an existing channel (§3), and (b) when verification is on and `intent` names no keyset: after the channel exists, ask once whether to create a keyset, use an existing one, or skip. Never fabricate or default a value the admin did not approve. A missing routing target is `failed` (below) | the Inputs list in SKILL.md |
| Wording | `discoveryMode == "guided"` → plain business language (§4). Any other mode → Salesforce terminology | Salesforce terminology (the Inputs as written) |
| Ends with | the structured result in section 5, then stop: no "what next?", no onward delegation | a plain-language summary of the same outcome |

Delegated runtime values (shared rules: the Service-Onboarding delegation guidelines linked from SKILL.md):

```json
{
  "intent": "Create a Queue-routed messaging channel 'Acme Support Chat' routed to Support_Queue; customers are not signed in.",
  "delegationFrom": "service-onboarding",
  "discoveryMode": "guided"
}
```

Inputs to read from `intent`: `channelLabel`, `routingType`, `routingTarget` (required); a fallback queue is required when `routingType` is
`Flow` or `AgentforceServiceAgent` and must be absent for `Queue` and `User`; a `QueueRoutingConfig` is required when
`routingType` is `User`. User verification defaults to off (`UnAuth`); when on, a keyset name (an existing keyset) and `authIdentifier` are optional. Every other channel setting uses the defaults in
`references/channel_settings.md` unless `intent` states it.

Missing routing target, delegated: return `failed`, `errorMessage` = "<Flow|User|Bot|Queue|RoutingConfig> <name> not found". Never
create one — queues come from the `queues` feature this one depends on.

## 2. Transport — `/headless/metadata` first, `sf` CLI as fallback

**Transport A (primary): the headless-360 MCP `dispatch` / `dispatch_readonly` tools** against the synchronous
Metadata-CRUD route, fully-qualified: `/services/data/vXX.0/headless/metadata/<Type>?type=<Type>&fullName=<Name>`.

- `GET` = read (`dispatch_readonly`) → `{type, fullName, xmlRep}`. `POST` = create-only; re-POSTing an existing
  `fullName` returns `DUPLICATE_VALUE`. `PUT` = update. On writes the body must carry `type`, `fullName` **and** `xmlRep`.
- Response is synchronous: `{results:[{success, errors[], ...}]}`. HTTP 200 can still be a failure — inner `success` wins.
- **Create once, then update.** Never re-run `POST` for a later change.
- **A minimal PUT silently drops inline blocks.** On `MessagingChannel`, a PUT that omitted `embeddedConfig` cleared
  it while `automatedResponses` and `messagingKeywords` survived. Always GET → modify → PUT the **full** document.
  Re-GET after the PUT and diff.
- Activation is not metadata: `IsActive` is absent from the `MessagingChannel` representation. Activate with an
  sObject update (`{"IsActive": true}`) through `dispatch`, or `sf data update record` on Transport B.
- Use the same `dispatch` tool for the probe and the write. `sf api request rest` / `curl` carry the `sf` CLI's separate
  credential, which can be expired while the MCP token is valid — a REST URL called through the CLI is **not** Transport A.
- Metadata references Flow/Queue by **API name** (`sessionHandlerFlow`, `sessionHandlerQueue`), not by runtime Id.

**Probe per type, per operation — never infer from another type.** Run a read-only `GET` for each type you are about
to touch (`MessagingChannel`; and `Queue` if you must create one).

| Probe result | Meaning | Action |
|---|---|---|
| `xmlRep` returned, or "Metadata not found" style error | type is onboarded | Transport A |
| `UNSUPPORTED_OPERATION` for the type or verb | not onboarded for that verb | Transport B for that call only |
| auth / connection error | MCP unavailable | Transport B; say so |
| `dispatch` not in your tool list | tool not loaded, not unavailable | load it (e.g. ToolSearch), then probe again before choosing B |

**Transport B (fallback): `sf` CLI** — `sf project deploy start` and `sf data query` / `sf data update record` as in
SKILL.md. Use only when the probe says Transport A is unavailable for that type/verb.

Routing-target existence checks (Queue, Flow, User, Bot) are SOQL: `dispatch_readonly` on the REST query endpoint first; `sf data query` only if that call returns a path/route error. The same applies to the channel Id and bind queries in steps 15 and 15a.

**Setup review link.** The activation update needs the channel Id, so step 15 looks it up: `SELECT Id FROM MessagingChannel WHERE DeveloperName='<CHANNEL_DEV_NAME>'` (Transport A `dispatch_readonly`; Transport B `sf data query`). The link is `<instanceUrl>/lightning/setup/LiveMessageSetup/<ChannelId>/view?lightning__channelType=EmbeddedMessaging`. `instanceUrl` comes from `sf org display --target-org '<alias>' --json | jq -r .result.instanceUrl` (always pipe through `jq`, never print the access token) and is usually unknown on Transport A, which has no `sf` session: then give the path alone. The link is the one exception to "no record Ids unless asked".

**Confirm the target org before the first write.** Read it with `SELECT Id, Name, IsSandbox, InstanceName FROM Organization` (Transport A `dispatch_readonly`; Transport B `sf data query -o '<alias>'`). State name, org Id and sandbox/production, and get a yes (standalone) or name it in the announced write (delegated). Treat production as a heightened case: restate that the change is live. Falling from Transport A to B changes the credential and possibly the org: run the same query on B and continue only if the org Id matches; otherwise stop and ask (delegated: `failed`, "transport B targets a different org").

## 3. Pre-scan (idempotency)

Run before any write, both modes. `GET` `MessagingChannel` by `fullName` = the normalized channel name.

| Finding | Outcome |
|---|---|
| No such channel | not set up → create (`POST`) |
| Exists, and every targeted setting equals the target (routing type and target, fallback queue, `authMode`, plus each supplied key) **and** `IsActive = true` | **already configured** — no write, return `already-configured` |
| Exists, matches, but `IsActive = false` | only activate; do not rewrite the metadata |
| Exists, some targeted setting differs | **drift** — announce each change ("routing: Queue A → Queue B"), then write the full document. Standalone: ask for a yes first. Delegated: confirm the changed settings and target org with the user before writing; the plan did not name the change. A `sessionHandlerType` change is the exception: return `failed` (`references/routing_transitions.md`) |
| Exists but was created by Connect `channel/setup` (defaults populated: opt-out/help keywords, `embeddedConfig`) | you now own the whole document: GET, modify only targeted fields, PUT the full result |

Standalone, channel exists: offer exactly three choices — no change (stop) / override (replace the targeted settings, keep the rest) / add to existing (keep current settings, add only what the user lists).

## 4. Questions in the admin's language (guided mode)

Ask about the outcome; state the default with each; keep it to a handful.

| Instead of | Ask |
|---|---|
| "Routing type: Queue, Flow, User or Agentforce Service Agent?" | "When a customer starts a chat, who should get it first: a team (queue), a specific person, or your AI agent? (Default: a team.)" |
| "Fallback queue developer name?" | "If the chat goes to your AI agent or an automated flow and it can't take it, which team should get it?" (Not asked for a team or a person.) |
| "Enable User Verification (JWT)?" | "Will customers be signed in to your site when they chat, so you know who they are? (Default: no.)" Yes → Auth mode; a keyset name is optional. With none, after the channel exists ask once: create a keyset, use an existing one, or skip (`references/keyset_setup.md`) |
| "Pre-chat form / custom parameters" | "What should we ask customers before the chat starts? (Default: name and email.)" |
| "`isAbandonedChatsEnabled`, `chatAbandonmentTimeout`…" | Not asked; use the defaults in `references/channel_settings.md` |

## 5. Result returned to the coordinator

```json
{
  "status": "success | already-configured | failed",
  "errorMessage": "<empty unless failed>",
  "outputs": {
    "channelName": "Acme_Support_Chat",
    "messagingChannelId": "<id or null>",
    "isActive": true,
    "verificationActive": false,
    "keysetChoice": "created | existing | skipped | not-asked"
  }
}
```

`status` and `errorMessage` are the contract. `outputs` is always returned. `verificationActive` is `true` only when `messagingAuthorizations` is on the channel; `keysetChoice` records the answer to the §1 keyset question (`not-asked` when verification is off or a `verificationKeyset` was given).
On `failed`: `errorMessage` names the failed step and the platform error; stop; do not retry.

## 6. Registration entry (for the onboarding team to place in a module)

```yaml
- id: messagingChannel
  title: "Customer messaging channel"
  description: "Create and switch on the channel that receives customer chats from your website or app, and decide who answers first (a team, a person, or an AI agent)."
  delegateSkill: service-digital-engagement-channel-configure
  dependsOn: [queues]
  revisionOwner: service-digital-engagement-channel-configure
  values:
    channelLabel:     { from: signal.messagingChannelName, default: "<company> Support Chat" }
    routingType:      { from: signal.messagingRouting,     default: "Queue" }
    routingTarget:    { from: signal.messagingRoutingTarget }
    fallbackQueue:    { from: signal.messagingFallbackQueue }
    queueRoutingConfig: { from: signal.messagingRoutingConfig }
    userVerification: { from: signal.messagingSignedIn,    default: false }
    verificationKeyset: { from: signal.messagingKeyset }
    authIdentifier:   { from: signal.messagingAuthIdentifier }
  writes: "MessagingChannel (Metadata CRUD); IsActive via sObject update; PublicKeyCertificate and PublicKeyCertificateSet (Metadata CRUD) only when the admin chooses to create a keyset"
  gating:
    irreversible: false
    note: "Reversible by deactivating the channel. A created keyset or key cannot be deleted while a channel's messagingAuthorizations references it (remove the authorization first), and a key's kid is unique per org. Pre-chat form fields can be deactivated but the form cannot be fully deleted; removing a channel custom parameter needs the form field removed and the deployment republished first."
  validate:
    check: check-messaging-channel
    passWhen: "GET MessagingChannel fullName=<normalized name> returns the targeted sessionHandlerType and target and the intended authMode, plus a messagingAuthorizations entry naming the keyset when keysetChoice is created or existing; SOQL SELECT IsActive, SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE DeveloperName=<name> returns IsActive=true, and non-null SessionHandlerId/FallbackQueueId where the routing type requires them"
  alternative: "Setup > Messaging Settings > New Channel > Messaging for In-App and Web; choose routing, then activate."
```
