# Channel types reference

## Channel type matrix

| Channel type | SobjectType (queue) | Routing branch | SERVICE_CHANNEL_DEV_NAME | SERVICE_CHANNEL_LABEL |
|---|---|---|---|---|
| Enhanced Chat | `MessagingSession` | Branch A — set `sessionHandlerAsa` on MessagingChannel | `sfdc_livemessage` | `Messaging` |
| Enhanced Messaging (3rd-party: WhatsApp, SMS, etc.) | `MessagingSession` | Branch A — set `sessionHandlerAsa` on MessagingChannel | `sfdc_livemessage` | `Messaging` |
| Voice | `VoiceCall` | Branch B — create inbound RoutingFlow (`routingType: Copilot`) | `sfdc_phone` | `Phone` |
| Email-to-Case | `Case` | Branch C — create inbound RoutingFlow (`routingType: Copilot`) | *(query required — see below)* | *(query required)* |

## Email-to-Case: query the org-specific ServiceChannel

The Case-based ServiceChannel DeveloperName and Label are not system-generated and vary by org. Query before writing the RoutingFlow:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT DeveloperName, MasterLabel FROM ServiceChannel WHERE RelatedEntityType='Case'"
```

- **Zero rows** → stop; surface gap to user. The channel cannot be wired until a Case-based ServiceChannel exists.
- **One row** → use its `DeveloperName` as `SERVICE_CHANNEL_DEV_NAME` and `MasterLabel` as `SERVICE_CHANNEL_LABEL`.
- **Multiple rows** → ask user to choose via `AskUserQuestion`.

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
