# Channel types reference

## Channel type matrix

| Channel type | SobjectType (queue) | Routing branch | SERVICE_CHANNEL_DEV_NAME | SERVICE_CHANNEL_LABEL |
|---|---|---|---|---|
| Enhanced Chat | `MessagingSession` | Branch A — set `sessionHandlerAsa` on MessagingChannel | `sfdc_livemessage` | `Messaging` |
| Enhanced Messaging (3rd-party: WhatsApp, SMS, etc.) | `MessagingSession` | Branch A — set `sessionHandlerAsa` on MessagingChannel | `sfdc_livemessage` | `Messaging` |
| Voice | `VoiceCall` | Branch B — create inbound RoutingFlow (`routingType: Copilot`) | `sfdc_phone` | `Phone` |
| Service Email (Email-to-Case) | `Case` | Branch C — create inbound RoutingFlow (`routingType: Copilot`) | *(query required — see below)* | *(query required)* |

## Email-to-Case: query the org-specific ServiceChannel

The Case-based ServiceChannel DeveloperName and Label are not system-generated and vary by org. Query before writing the RoutingFlow:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT DeveloperName, MasterLabel FROM ServiceChannel WHERE RelatedEntity='Case'"
```

The SObject column is `RelatedEntity` — `RelatedEntityType` is the *metadata* field name (used in the deploy below) and errors as `No such column` in SOQL.

- **Zero rows** → no Case-based ServiceChannel exists yet. This is **provisionable, not a dead end** — tell the user one is required for routing and provision it (see "Provision a Case ServiceChannel" below), then continue with the new channel's `DeveloperName`/`MasterLabel`.
- **One row** → use its `DeveloperName` as `SERVICE_CHANNEL_DEV_NAME` and `MasterLabel` as `SERVICE_CHANNEL_LABEL`.
- **Multiple rows** → ask user to choose via `AskUserQuestion`.

### Provision a Case ServiceChannel (Branch C only)

This applies **only to Branch C (Email-to-Case)** — Branches A and B use the fixed system channels `sfdc_livemessage`/`sfdc_phone`, which always exist and never reach this path.

When none exists, deploy one. `ServiceChannel` is in the SDR registry and has no v68-only fields, so a source deploy is fine (no `sourceApiVersion` concern). Write `serviceChannels/Case_Channel.serviceChannel-meta.xml` under the project's package directory:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ServiceChannel xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesMinimizeWidgetOnAccept>false</doesMinimizeWidgetOnAccept>
    <hasAutoAcceptEnabled>false</hasAutoAcceptEnabled>
    <isInterruptible>false</isInterruptible>
    <label>Cases</label>
    <relatedEntityType>Case</relatedEntityType>
</ServiceChannel>
```

The *metadata* field is `relatedEntityType` (here), while the SOQL column queried above is `RelatedEntity` — don't conflate them. Deploy:

```bash
sf project deploy start --metadata "ServiceChannel:Case_Channel" --target-org $ORG --json
```

Then use `Case_Channel` as `SERVICE_CHANNEL_DEV_NAME` and `Cases` as `SERVICE_CHANNEL_LABEL`. Deploy-time only needs the channel to exist; live Omni routing additionally needs presence configuration (reps online) before work actually routes.

## Voice: native vs partner — MUST CHECK before Branch B

Branch B only works with **native Service Cloud Voice**. Partner telephony providers (Amazon Connect, Genesys, Avaya, etc.) manage their own routing pipelines and do not honour Salesforce RoutingFlows — wiring the agent via `routingType: Copilot` on a partner channel will have no effect.

**Detection method: query `CommunicationChannelLine` via the Tooling API.**

`CommunicationChannelLine` is a Tooling API object (not SOQL-queryable). Native SCV phone numbers have a `CommunicationChannelLine` record whose `DeveloperName` follows the pattern `DEV_{digits}` (e.g. `DEV_13375909051`). Partner voice channels do not.

**Step 1 — Extract the digits from the MessagingChannel DeveloperName.**

`PstnVoice` channels follow the pattern `VOICE_PSTN_{digits}` (e.g. `VOICE_PSTN_13375909051`). Strip the `VOICE_PSTN_` prefix to get the digits (e.g. `13375909051`).

**Step 2 — Query `CommunicationChannelLine` via the Tooling API:**

```bash
sf data query --target-org $ORG --json --use-tooling-api \
  --query "SELECT Id, DeveloperName FROM CommunicationChannelLine WHERE DeveloperName='DEV_{DIGITS}' LIMIT 1"
```

Interpret results:

| Result | Verdict |
|---|---|
| Query returns 1+ row | **Native SCV** — Branch B is supported |
| Query returns 0 rows | **Partner voice** — Branch B not supported |

**If partner voice:** stop and surface this to the user:

> *"This voice channel uses a partner telephony provider. Routing to an Agentforce agent via a Salesforce RoutingFlow is not supported — routing is managed by the partner's system. Contact your telephony provider for agent routing options."*

Do not proceed with RoutingFlow creation for partner voice channels.

## Routing branch summary

- **Branch A (messaging channels)**: No RoutingFlow. Set `sessionHandlerAsa` + `sessionHandlerQueue` directly on the existing `MessagingChannel` metadata. No agent republish.
- **Branch B (Voice, native only)**: Detect native vs 3rd-party first (see above). If native, create an inbound RoutingFlow with `routingType: Copilot` pointing to the agent by label, with the queue as fallback. No agent file changes.
- **Branch C (Email-to-Case)**: Same inbound RoutingFlow shape as Branch B, but with the org-specific Case-based ServiceChannel. No agent file changes.
