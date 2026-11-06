# Onboarding contract — delegated mode, transport, pre-scan, registration

Read this when the invocation carries a `context` object, before any org write, or when registering the skill in an
onboarding module. The sibling `service-digital-engagement-deployment-configure` has the same structure.

## 1. Two entry points, one write procedure

| | Delegated | Standalone |
|---|---|---|
| Detected by | `context.calledFrom == "service-onboarding"` | no `context` object |
| Values come from | `values` in the payload — already approved in the plan table | you ask for the Inputs in SKILL.md; defaults are in `references/channel_settings.md` |
| Questions | none. A missing required key is a caller bug: stop and return `failed` naming the key. Never default a value the admin did not approve | the Inputs list in SKILL.md |
| Wording | `discoveryMode == "guided"` → plain business language (§4). `"pickAreas"` → Salesforce terminology | Salesforce terminology (the Inputs as written) |
| Ends with | the structured result in section 5 | a plain-language summary of the same outcome |

Delegated payload:

```json
{
  "values": {
    "channelLabel": "Acme Support Chat",
    "routingType": "Queue",
    "routingTarget": "Support_Queue",
    "fallbackQueue": null,
    "userVerification": false
  },
  "context": { "calledFrom": "service-onboarding", "discoveryMode": "guided" }
}
```

Required `values`: `channelLabel`, `routingType`, `routingTarget`; `fallbackQueue` is required when `routingType` is
`Flow`, `User` or `AgentforceServiceAgent`. `userVerification` defaults to `false` (`UnAuth`); when `true`, `verificationKeyset` (an existing
keyset name) and `authIdentifier` are optional. Every other channel setting uses the defaults in
`references/channel_settings.md` unless a key is supplied.

Missing routing target, delegated: return `failed`, `errorMessage` = "<Flow|User|Bot|Queue> <name> not found". Never
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

**Transport B (fallback): `sf` CLI** — `sf project deploy start` and `sf data query` / `sf data update record` as in
SKILL.md. Use only when the probe says Transport A is unavailable for that type/verb.

Routing-target existence checks (Queue, Flow, User, Bot) are SOQL: `dispatch_readonly` on the REST query endpoint first; `sf data query` only if that call returns a path/route error.

## 3. Pre-scan (idempotency)

Run before any write, both modes. `GET` `MessagingChannel` by `fullName` = the normalized channel name.

| Finding | Outcome |
|---|---|
| No such channel | not set up → create (`POST`) |
| Exists, and every targeted setting equals the target (routing type and target, fallback queue, `authMode`, plus each supplied key) **and** `IsActive = true` | **already configured** — no write, return `already-configured` |
| Exists, matches, but `IsActive = false` | only activate; do not rewrite the metadata |
| Exists, some targeted setting differs | **drift** — announce each change ("routing: Queue A → Queue B"), then write the full document. Standalone: ask for a yes first. Delegated: the plan approval covers it |
| Exists but was created by Connect `channel/setup` (defaults populated: opt-out/help keywords, `embeddedConfig`) | you now own the whole document: GET, modify only targeted fields, PUT the full result |

Standalone, channel exists: offer exactly three choices — no change (stop) / override (replace the targeted settings, keep the rest) / add to existing (keep current settings, add only what the user lists).

## 4. Questions in the admin's language (guided mode)

Ask about the outcome; state the default with each; keep it to a handful.

| Instead of | Ask |
|---|---|
| "Routing type: Queue, Flow, User or Agentforce Service Agent?" | "When a customer starts a chat, who should get it first: a team (queue), a specific person, or your AI agent? (Default: a team.)" |
| "Fallback queue developer name?" | "If that person or agent isn't available, which team should the chat go to?" |
| "Enable User Verification (JWT)?" | "Will customers be signed in to your site when they chat, so you know who they are? (Default: no.)" Yes → Auth mode; an existing signing keyset name is optional, and setting up the keys is a separate step |
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
    "isActive": true
  }
}
```

`status` and `errorMessage` are the contract. `outputs` is always returned.
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
    userVerification: { from: signal.messagingSignedIn,    default: false }
    verificationKeyset: { from: signal.messagingKeyset }
    authIdentifier:   { from: signal.messagingAuthIdentifier }
  writes: "MessagingChannel (Metadata CRUD); IsActive via sObject update"
  gating:
    irreversible: false
    note: "Reversible by deactivating the channel. Pre-chat form fields can be deactivated but the form cannot be fully deleted; removing a channel custom parameter needs the form field removed and the deployment republished first."
  validate:
    check: check-messaging-channel
    passWhen: "GET MessagingChannel fullName=<normalized name> returns the targeted sessionHandlerType and target and the intended authMode; SOQL SELECT IsActive, SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE DeveloperName=<name> returns IsActive=true, and non-null SessionHandlerId/FallbackQueueId where the routing type requires them"
  alternative: "Setup > Messaging Settings > New Channel > Messaging for In-App and Web; choose routing, then activate."
```
