# PstnVoice MessagingChannel

**`POST /services/data/v68.0/sobjects/MessagingChannel/`**

All calls go through `sf api request rest` — never extract the access token.

`SessionHandlerId` is the routing target: the **ACC queue Id** for Omni Queue, or the inbound
**FlowDefinition Id** (`300…`) for Omni Flow (with `FallbackQueueId` set to the queue). Both are
produced by `scripts/create-voice-channel.sh` — its optional 5th `fallback-queue-id` arg switches
it to Omni Flow. See `references/omni-flow-routing.md` for the Omni Flow contract.

## Request — Omni Queue (default)

```bash
sf api request rest \
  "/services/data/v68.0/sobjects/MessagingChannel/" \
  --method POST \
  --body '{
    "DeveloperName": "Voice_Channel_14155551234",
    "MasterLabel": "Voice Channel +14155551234",
    "MessageType": "PstnVoice",
    "MessagingPlatformKey": "+14155551234",
    "ChannelLineId": "<communication-channel-line-id>",
    "IsActive": true,
    "SessionHandlerId": "<acc-queue-id>"
  }' \
  --target-org <alias>
```

## Request — Omni Flow

Same call, but `SessionHandlerId` is the inbound FlowDefinition Id and `FallbackQueueId` is added:

```json
{
  "...": "same fields as above",
  "SessionHandlerId": "<inbound-flowdefinition-id-300>",
  "FallbackQueueId": "<acc-queue-id>"
}
```

## Field rules

| Field | Rule |
|-------|------|
| `MessageType` | Must be `PstnVoice` |
| `MessagingPlatformKey` | The E.164 phone number (with leading `+`) |
| `SessionHandlerId` | Omni Queue: the ACC queue Id (`00G…`). Omni Flow: the inbound RoutingFlow's `FlowDefinition` Id (`300…`). Resolve both — never hardcode |
| `FallbackQueueId` | Omni Flow only: the queue the agent overflows/escalates to (`00G…`). Omit for Omni Queue |
| `ChannelLineId` | The Id from `CommunicationChannelLine`; this is the writable create field that populates the `ChannelLine` relationship |
| `IsActive` | `true` activates the channel immediately |
| `IsoCountryCode` | Do NOT set on `PstnVoice` channels |
| Routing | Use `SessionHandlerId` (+ `FallbackQueueId` for Omni Flow) — not `TargetQueueId` or `RoutingType` |

## Success response

```json
{ "id": "0Mj...", "success": true, "errors": [] }
```

## Create-time errors

| Error | Meaning | Action |
|-------|---------|--------|
| `INVALID_FIELD: The value provided for foreign key reference ChannelLine is not a nested SObject` | The relationship name `ChannelLine` was used as a scalar Id field | Send the `CommunicationChannelLine` Id in `ChannelLineId` instead |
| `FIELD_INTEGRITY_EXCEPTION: ... status 'Provisioning'` | Number not yet live and validation is enforced | Wait for the number to become live (Step 6), then retry |
| Duplicate `DeveloperName` | A channel with that name exists | Derive a unique `DeveloperName` or reuse the existing channel |

## Verify

```sql
SELECT Id, DeveloperName, MasterLabel, MessageType, MessagingPlatformKey, ChannelLineId, IsActive, SessionHandlerId, FallbackQueueId
FROM MessagingChannel WHERE Id = '<channel-id>'
```

For Omni Flow, `SessionHandlerId` must start with `300` (inbound FlowDefinition) and `FallbackQueueId` with `00G` (queue). For Omni Queue, `SessionHandlerId` starts with `00G` and `FallbackQueueId` is null.
