# Setup Summary

After the voice channel is created and verified, present a summary to the user.

## Summary table

| Configuration | Value |
|---------------|-------|
| Phone Number | `<phone-number>` |
| Number Type | `<phone-type>` |
| Country | `<country>` |
| ChannelLine ID | `<channel-line-id>` |
| Phone Status | `<code-status>` |
| Channel ID | `<channel-id>` |
| Channel Status | Active |
| Routing model | `<Omni Queue \| Omni Flow>` |
| Queue | `<acc-queue-name>` |
| Agentforce agent (Omni Flow) | `<agent-label>` (`<agent-api-name>`) |
| Inbound flow (Omni Flow) | `<agent-api-name>_Voice_Omni_Flow` |
| Developer Name | `<dev-name>` |

Include the Agentforce agent / inbound flow rows only for the Omni Flow path.

## What's ready

- Phone number procured and provisioned
- ChannelLine resolved
- Voice channel created and activated
- **Omni Queue:** channel routed to the Agentforce Contact Center queue
- **Omni Flow:** channel routed to the Agentforce agent (Copilot inbound flow) with the queue as fallback; escalation flow deployed

## Suggested next steps

- **Omni Queue:** configure agents in the queue.
- **Omni Flow:** test the agent conversation; optionally tune voice (`modality voice:`) or wire outbound escalation to the agent.
- Test by calling the procured number.
