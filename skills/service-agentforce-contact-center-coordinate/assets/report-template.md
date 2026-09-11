# Agentforce Contact Center Setup Report

## Setup

| Item | Value |
|------|-------|
| Org alias | `<alias>` |
| Org confirmed | `sf org display --target-org <alias>` → `<instanceUrl>` |
| Country | `<US\|CA>` |
| Phone number type | `<10DLC\|Toll Free>` |
| Routing model | `<Omni Queue \| Omni Flow>` |

## Commands run

Each API call went through `sf api request rest` (no raw access token was extracted).

1. Fetch numbers — `GET /services/data/v68.0/connect/number-management/v1/numbers?countryCode=<country>&phoneNumberType=<type>`
2. Procure number — `POST /services/data/v68.0/connect/number-management/v1/number` with `country=<country>`, `phoneNumberType=<type>`
3. Resolve ChannelLine — SOQL: `<query used>`
4. Verify live status — Tooling API `CodeStatus`<, numberStateReconcile if not live>
5. Resolve queue by name — SOQL: `SELECT Id FROM Group WHERE Type='Queue' AND Name='<queue-name>'`
6. Create channel — `POST` MessagingChannel (`PstnVoice`, `ChannelLineId=<channel-line-id>`, `IsActive=true`)

**Omni Flow only** — additional steps (omit for Omni Queue):

7. Agentforce prerequisite — `scripts/check-agentforce-prereq.sh` → canonical Einstein Agent User `<agent-user>` <reused/provisioned>
8. Agent — created/reused `<agent-api-name>` (`<agent-label>`), status Active
9. RoutingFlows — deployed `<agent-api-name>_Voice_Omni_Flow` (Copilot) + `<agent-api-name>_Voice_Escalation` (QueueBased)

## Result

| Field | Value |
|-------|-------|
| Routing model | `<Omni Queue \| Omni Flow>` |
| Procured phone number | `<number>` |
| CommunicationChannelLine Id | `<channel-line-id>` |
| CommunicationChannelLine status | `<code-status>` |
| Queue resolved by name | `<queue-name>` → `<queue-id>` |
| Agentforce agent (Omni Flow) | `<agent-api-name>` (`<agent-label>`) — Active |
| Inbound FlowDefinition (Omni Flow) | `<flow-dev-name>` → `<300-id>` |
| MessagingChannel Id | `<channel-id>` |
| MessagingChannel DeveloperName | `<dev-name>` |
| MessagingChannel ChannelLineId | `<channel-line-id>` |
| MessagingChannel IsActive | `true` |
| MessagingChannel SessionHandlerId | `<queue-id \| 300-flowdefinition-id>` |
| MessagingChannel FallbackQueueId | `<queue-id (Omni Flow) \| null>` |

Fill the Omni Flow rows only when that path was taken; leave them out for Omni Queue.

## Outcome

<One line: SUCCESS — active PstnVoice channel `<channel-id>` routed to `<queue `<queue-name>` (Omni Queue) | agent `<agent-label>` via Omni Flow, fallback queue `<queue-name>`>`; OR the exact error encountered and the step it failed at.>
