# Omni-Channel inventory API notes

## Supported operation

```text
POST /services/data/v66.0/headless/invoke
```

Call it through `sf api request rest --method POST --target-org <alias>` with this invoke envelope:

```json
{
  "className": "ui.omnichannel.home.controller.OmniChannelInstancesController",
  "action": "getChannelInstances"
}
```

The Project Codey route is logically read-only even though the shared dispatcher transport is POST-only. Salesforce CLI owns authentication, so do not extract the org access token or build an Authorization header. Treat the inner `status_code` as authoritative and read the inventory from `body`.

Project Codey's approved `OmniChannelHome` source-of-record identifies this Aura-backed headless operation as canonical. The owning-team review was approved on 2026-08-20. The operation aggregates providers for Live Chat buttons, Messaging channels, Service channels, and Voice, then derives routing labels and setup URLs. Independent Connect, Tooling, Metadata, or sObject calls do not reproduce that contract.

## Permission boundary

The running user needs both customer-facing permissions:

- View Setup and Configuration
- Customize Application

A permission failure is not evidence that the org has no channel instances. Return `status: blocked` and ask the user to run with an appropriately authorized setup user.

## Response fields

Each channel instance can include:

```text
id
label
channelUrl
omniChannelInstanceType
routingType
icon
routingRequirementId
routingRequirementLabel
routingRequirementUrl
messages
```

Known channel-type labels are `Voice`, `Email`, `Chat`, `SMS`, `Facebook`, `WhatsApp`, and `InApp`. Known routing labels are `Queue`, `Flow`, and `Other`. The script accepts these labels case-insensitively and emits their canonical display spelling.

## Response handling

The supported operation's contract is an array of channel instances. The analyzer also tolerates a raw array or the same array nested under a standard `body`, `result`, `data`, `items`, `records`, `value`, or `channelInstances` envelope so Salesforce CLI response wrapping does not silently turn valid results into failures. Any other shape is blocked as malformed.
