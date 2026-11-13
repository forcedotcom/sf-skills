# Onboarding contract — delegated mode, transport, pre-scan, registration

Read this when the invocation carries a `context` object, when you are about to write to the org, or when the
skill is being registered in an onboarding module. It implements the Feature Setup Skill Guidelines (Conversational
Onboarding, Service Cloud) for this skill.

## 1. Two entry points, one write procedure

| | Delegated | Standalone |
|---|---|---|
| Detected by | invocation has `context.calledFrom == "service-onboarding"` | no `context` object |
| Values come from | `values` in the payload — already approved in the plan table | you ask, using the defaults in SKILL.md |
| Questions | none. A missing required key is a caller bug: stop and report `failed` naming the key. Never default a value the admin did not approve | the Clarifying Questions in SKILL.md |
| Wording | `discoveryMode == "guided"` → plain business language (§4). `"pickAreas"` → Salesforce terminology | Salesforce terminology (the Clarifying Questions as written) |
| Ends with | the structured result in section 5 | a plain-language summary of the same outcome |

Both paths converge on the same pre-scan → write → validate procedure. The only difference is where values come from.

Delegated payload:

```json
{
  "values": {
    "operation": "create",
    "deploymentType": "Web",
    "deploymentName": "Acme Support Chat",
    "channelName": "Acme_Support_Channel",
    "siteName": "ESW_AcmeSupport_1700000000000"
  },
  "context": { "calledFrom": "service-onboarding", "discoveryMode": "guided" }
}
```

Required `values`: `deploymentName`, `deploymentType`, `channelName`. `deploymentName` is the label; the API name is
derived from it (SKILL.md Required Inputs: `Acme Support Chat` → `Acme_Support_Chat`). `operation` defaults to `create` when the pre-scan
finds nothing and `update` when it finds a deployment. `siteName` is required for Web updates. Optional feature keys
(pre-chat fields, business hours, T&C, branding) are applied only when present — do not invent them.

## 2. Transport — `/headless/metadata` first, `sf` CLI as fallback

**Transport A (primary): the headless-360 MCP `dispatch` / `dispatch_readonly` tools** against the synchronous
Metadata-CRUD route, fully-qualified: `/services/data/vXX.0/headless/metadata/<Type>?type=<Type>&fullName=<Name>`.

- `GET` = read (`dispatch_readonly`) → `{type, fullName, xmlRep}`. `POST` = create-only (duplicate → `DUPLICATE_VALUE`).
  `PUT` = update. On writes the body must carry `type`, `fullName` **and** `xmlRep`.
- Response is synchronous: `{results:[{success, errors[], ...}]}`. HTTP 200 can still be a failure — inner `success` wins.
- **PUT is not a safe merge for `EmbeddedServiceConfig`.** Child collections survive an omitted block but inline
  complex blocks can be silently cleared. Always GET → modify → PUT the **full** document. Never PUT a minimal payload.
  Re-GET after the PUT and diff, so a dropped block is caught here and not in the widget.
- Use the same `dispatch` tool for the probe and for the write. `sf api request rest` / `curl` carry the `sf` CLI's
  separate credential, which can be expired while the MCP token is valid — a REST URL called through the CLI is
  **not** Transport A.

**Probe per type, per operation — do not infer from another type.** Before the first write run a read-only
`GET` for `EmbeddedServiceConfig` (and for any other type you are about to touch).

| Probe result | Meaning | Action |
|---|---|---|
| `xmlRep` returned, or "Metadata not found" style error | type is onboarded | Transport A |
| `UNSUPPORTED_OPERATION` for the type or verb | not onboarded for that verb | Transport B for that call only |
| auth / connection error | MCP unavailable | Transport B; say so |

**Transport B (fallback): `sf` CLI** — the retrieve/deploy commands already in SKILL.md. Use it only when the probe
says Transport A is unavailable for that type/verb, never as a convenience.

What is not a transport choice:
- **Web deployment creation is a Connect API call — send it with `sf api request rest`, not `dispatch`.** Through
  `dispatch` it always fails with an `INTERNAL_ERROR` server error while building the ESW site; the same body via the CLI
  succeeds. Do not try `dispatch` first.
- **Publish is a Connect API call**, sent per SKILL.md step 17c (`dispatch`, `sf api request rest` on a route error).
- **Tooling API** work (custom labels, branding, reCAPTCHA) is not verified through `dispatch`. Use `sf` CLI.

## 3. Pre-scan (idempotency)

Run before any write, both modes. Read `EmbeddedServiceConfig` by `fullName` = the API name derived from `deploymentName` (Transport A GET).

| Finding | Outcome |
|---|---|
| No such deployment | not set up → create path |
| Exists, and every targeted field already equals the target (channel link, `isEnabled`, type, and each optional feature supplied) | **already configured** — make no write, return `already-configured` |
| Exists, some targeted field differs | **drift** — announce each change ("pre-chat form: on → off"), then write. Standalone: ask for a yes first. Delegated: the plan approval covers it |
| Exists but links a different channel than `channelName` | Standalone: ask before repointing. Delegated: return `failed`, `errorMessage` = "deployment <name> already uses channel <other>" |

Standalone, deployment exists: offer exactly three choices — no change / override / add to existing.

The metadata read does not say whether the latest edits are **published**. Web creation auto-publishes. If auto-publish succeeded
(isPublishSuccess=true), return published: true. For updates, publishing is a separate step (SKILL.md step 17c); delegated returns `published: false` so the coordinator can ask the admin.

## 4. Questions in the admin's language (guided mode)

Ask about the outcome, not the Salesforce feature. Keep it to a handful; state the default with each.

| Instead of | Ask |
|---|---|
| "Which deployment type: API, Mobile or Web?" | "Where will customers chat with you — on your website, in a mobile app, or through your own custom app?" (website=Web, mobile app=Mobile, custom=API) |
| "Associate which `channelPlatformKey`?" | Not asked. Delegated: comes from the channel step. Standalone: "Which messaging channel should this chat use?" listing existing ones |
| "Enable pre-chat form fields?" | "Do you want to ask customers for their name and email before the chat starts? (Default: yes — name and email.)" |
| "Enable `isTermsAndConditionsEnabled`?" | "Do customers need to accept terms before chatting? (Default: no.)" |
| "Business hours record?" | "Should the chat only be offered during your business hours? (Default: no.)" |
| "Chat invitation conditions" | Skip in guided mode unless the admin raises it. It is a pickAreas/expert option |

## 5. Result returned to the coordinator

```json
{
  "status": "success | already-configured | failed",
  "errorMessage": "<empty unless failed>",
  "outputs": {
    "deploymentName": "Acme_Support_Chat",
    "embeddedServiceConfigId": "<id or null>",
    "published": false
  }
}
```

`published` is `true` only when a Web create auto-published (`isPublishSuccess=true`).

`status` and `errorMessage` are the contract. `outputs` is always returned; it is an addition to the documented shape.
On `failed`: `errorMessage` names the failed step and the platform error; stop; do not retry.

## 6. Registration entry (draft for the onboarding team to place in a module)

```yaml
- id: messagingDeployment
  title: "Chat widget for your website or app"
  description: "Create the chat widget (embedded messaging deployment) that customers use to start a messaging conversation: where it appears, what it asks before chat starts, and publishing it live."
  delegateSkill: service-digital-engagement-deployment-configure
  dependsOn: [messagingChannel]
  revisionOwner: service-digital-engagement-deployment-configure
  # org perms: confirm exact names with Digital Engagement licensing (not yet confirmed)
  values:
    deploymentType:  { from: signal.messagingSurface,   default: "Web" }
    deploymentName:  { from: signal.messagingWidgetName, default: "<company> Support Chat" }
    channelName:     { from: outputs.messagingChannel.channelName }
  writes: "EmbeddedServiceConfig (Metadata CRUD); Web create via Connect API embeddedmessaging/deployment/setup (sf CLI); publish via Connect API; optional BrandingSet / custom labels via Tooling API"
  gating:
    irreversible: false
    note: "Reversible by disabling the deployment (isEnabled=false). Pre-chat form fields can be deactivated but the form cannot be fully deleted."
  validate:
    check: check-messaging-deployment
    passWhen: "GET EmbeddedServiceConfig fullName=<derived API name> returns isEnabled=true and the embeddedServiceMessagingChannel links values.channelName; for Web, publishing is left to the admin after review (published may be false)"
  alternative: "Setup > Embedded Service Deployments > New Deployment > Messaging for In-App and Web; choose the channel, set pre-chat, then Publish."
```

Open items for the onboarding team: the `signal.*` keys do not exist in `onboarding-state.schema.json` yet
(`channels` allows only email/web); the coordinator must accept `outputs` and pass `outputs.messagingChannel.channelName`
to this skill; org perm names are not yet confirmed.
