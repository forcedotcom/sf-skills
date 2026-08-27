# Branch B — Voice inbound routing

Wires an Agentforce agent to a `PstnVoice` MessagingChannel via an inbound RoutingFlow. The queue resolved in Phase 1 acts as the fallback when the agent is unavailable.

## Step 0 — Existing channel or new number?

Query for existing `PstnVoice` MessagingChannels on the org:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT DeveloperName, MasterLabel, MessagingPlatformKey FROM MessagingChannel WHERE MessageType='PstnVoice' AND IsActive=true"
```

Ask the user via `AskUserQuestion`:
- **One or more found** → present each as an option (`{MasterLabel} — {MessagingPlatformKey}`), plus *"Provision a new phone number"*
- **Zero found** → skip the question; proceed directly to provision a new number

**If provisioning a new number:** phone number provisioning is handled upstream by `service-helpagent-coordinate` (its own `channel-voice.md` reference) before this skill is invoked. By the time Branch B runs, the `PstnVoice` MessagingChannel already exists — set `CHANNEL_DEVELOPER_NAME` to its `DeveloperName` and proceed.

**If using an existing channel:** set `CHANNEL_DEVELOPER_NAME` to the selected channel's `DeveloperName`.

> **Check native vs 3rd-party telephony before creating the RoutingFlow.** See `channel-types.md` — if the org uses a partner telephony provider, stop and surface the message there. Do not proceed with RoutingFlow creation.

## Step 1 — Determine names

- Flow label: `{AgentLabel} Inbound Voice Flow`
- DeveloperName: `{AgentDevName}_Inbound_Voice_Flow`
- `SERVICE_CHANNEL_DEV_NAME`: `sfdc_phone`
- `SERVICE_CHANNEL_LABEL`: `Phone`

## Step 2 — Write the RoutingFlow XML

Write to `force-app/main/default/flows/{FLOW_DEVELOPER_NAME}.flow-meta.xml` using the template in `routing-flow.md`. Substitute all tokens including `{QUEUE_ID}` from Phase 1.

## Step 3 — Deploy and verify

Deploy and verify `ActiveVersionId` is non-null (see `routing-flow.md`).

## Step 4 — Assign the flow to the MessagingChannel

Deploy a `MessagingChannel` metadata file for `{CHANNEL_DEVELOPER_NAME}` with `sessionHandlerType=Flow`, `sessionHandlerFlow={FLOW_DEVELOPER_NAME}`, and `sessionHandlerQueue={QUEUE_DEVELOPER_NAME}`. This sets the "Flow Definition" field in Setup — without this step the flow is deployed but never executed and calls hang up immediately.

```xml
<MessagingChannel xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel>{CHANNEL_LABEL}</masterLabel>
    <messagingChannelType>PstnVoice</messagingChannelType>
    <sessionHandlerFlow>{FLOW_DEVELOPER_NAME}</sessionHandlerFlow>
    <sessionHandlerQueue>{QUEUE_DEVELOPER_NAME}</sessionHandlerQueue>
    <sessionHandlerType>Flow</sessionHandlerType>
</MessagingChannel>
```

Verify: query `MessagingChannel WHERE DeveloperName='{CHANNEL_DEVELOPER_NAME}'` and confirm `SessionHandlerId` starts with `300` (FlowDefinition prefix).

## Step 5 — Add `modality voice:` to the agent and republish

Retrieve the agent's authoring bundle, then add the following block at the end of the `.agent` file if it is not already present:

```yaml
modality voice:
    voice_id: "UgBBYS2sOqTuMpoF3BR0"
    outbound_speed: 1.0
    outbound_stability: 0.65
    outbound_similarity: 0.75
```

Do not ask the user for a `voice_id` — always use the platform default above ("Mark", en_US). The user can customize the voice afterward in Agent Builder → Connections → Voice. Then validate, publish, and activate the agent per `agent-wiring.md`. Verify the block round-tripped by re-retrieving the bundle.

Proceed to Phase 3 (optional).
