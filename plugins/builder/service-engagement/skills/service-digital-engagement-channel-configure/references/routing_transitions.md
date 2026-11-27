# Routing transitions and target lookups

Read when step 3a finds that `sessionHandlerType` changes, or to look up the routing targets in step 4. This skill never writes a queue, routing config or flow itself; a missing queue or routing config is created by the owning skill after the user agrees (SKILL.md → step 4, Cross-Skill Integration).

## Why a plain redeploy fails

A Metadata deploy writes only the new type's fields. It never clears the old type's `FallbackQueueId` or `RoutingConfigurationId`, and the platform rejects them on the new type.

| Change | Stale field | Error |
|---|---|---|
| Flow or Agentforce Service Agent to Queue or User | `FallbackQueueId` | "A Fallback Queue can only be specified when selecting a Flow, Bot, Agentforce Orchestrator, or AI Agent routing method" |
| User to Queue, Flow, or Agentforce Service Agent | `RoutingConfigurationId` | "Only a Queue or Flow Routing Method with Fallback Queue can be configured for this Messaging Channel." |

Changes from Queue, and between Flow and Agentforce Service Agent, carry no stale field and deploy as is. A failed deploy leaves the channel unchanged.

## Procedure

1. Announce the change and which fields will be cleared. If the channel is active (`IsActive`), say that new sessions route differently from the moment of the update. Then let the user choose to **continue** or **stop**. Write nothing until they choose continue; if they stop, leave the channel as is and report no change. Delegated: a routing-type change is the exception to confirming drift with the user (contract §3), so return `failed` with `errorMessage` "routing type change Flow → Queue needs the user's confirmation" (naming the real types) and write nothing.
2. Names must match `^[A-Za-z0-9][A-Za-z0-9_.@+-]*$` before they go into a query; otherwise stop and ask. Resolve the Ids: queue `SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='<NAME>'`; flow `SELECT DurableId FROM FlowDefinitionView WHERE ApiName='<NAME>' AND IsActive=true AND ProcessType='RoutingFlow'` (the `300` Id); user `SELECT Id FROM User WHERE Username='<USERNAME>' AND IsActive=true`; routing config `SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='<NAME>'`; bot `SELECT Id FROM BotDefinition WHERE DeveloperName='<NAME>'` (its active version must be Active, SKILL.md step 7); the channel `SELECT Id FROM MessagingChannel WHERE DeveloperName='<CHANNEL>'`.
3. First query and keep the channel's current `SessionHandlerId`, `FallbackQueueId`, and `RoutingConfigurationId`. Then update the `MessagingChannel` record with all fields in one update (Transport A: sObject update through `dispatch`; Transport B: `sf data update record --sobject MessagingChannel --record-id <Id> --values "..."`):

   | To | Values |
   |---|---|
   | Queue | `SessionHandlerId=<queueId> FallbackQueueId='' RoutingConfigurationId=''` |
   | User | `SessionHandlerId=<userId> RoutingConfigurationId=<routingConfigId> FallbackQueueId=''` |
   | Flow | `SessionHandlerId=<flowId> FallbackQueueId=<fallbackQueueId> RoutingConfigurationId=''` |
   | Agentforce Service Agent | `SessionHandlerId=<botId> FallbackQueueId=<fallbackQueueId> RoutingConfigurationId=''` |

   One update matters: a record holding a User handler needs its routing config in the same write, so setting only `FallbackQueueId=''` when moving to User is rejected with "Select a routing configuration."
4. Deploy the full document for the new type (SKILL.md step 14). If the deploy fails, the record update has already happened: write the three saved values back in one update, re-query to confirm, and report the platform error. If the restore update also fails, stop and give the admin the saved Ids and the channel's Setup link. Otherwise re-query `SessionHandlerId`, `FallbackQueueId`, and `RoutingConfigurationId` and confirm they match the new type.

## If the record update is not allowed

The update needs Update on `MessagingChannel` plus field access to `SessionHandlerId`, `FallbackQueueId`, and `RoutingConfigurationId`; the Metadata API permission does not cover it. If it is denied, do not deploy. Give the admin the channel's Setup page (`/lightning/setup/LiveMessageSetup/<ChannelId>/view?lightning__channelType=EmbeddedMessaging`, plain link, same login limitation as `recaptcha_handoff.md`) and have them change **Routing Type** in the inline editor there, then continue at step 4 above.

## Target lookups

Names must match `^[A-Za-z0-9][A-Za-z0-9_.@+-]*$` before they go into a query. Use `sf data query --target-org '<org-alias>' --query "..."`.

- Queue: `SELECT Id, DeveloperName FROM Group WHERE Type='Queue' AND DeveloperName='<QUEUE_NAME>'`
- Flow: `SELECT Id, ApiName FROM FlowDefinitionView WHERE ApiName='<FLOW_NAME>' AND IsActive=true AND ProcessType='RoutingFlow'`
- User: `SELECT Id, Username FROM User WHERE Username='<USERNAME>' AND IsActive=true`, plus `SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='<CONFIG_NAME>'`
- ASA: `SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName='<BOT_NAME>'`
- Fallback queue (Flow and ASA): the Queue lookup above.

## Agentforce Service Agent

`<sessionHandlerAsa>` is required (omitting it fails with "Missing required Agentforce Service Agent"); the deploy binds `SessionHandlerId`, no PATCH needed. The bot must be Active first (inactive fails with "Only active Agentforce Service Agents are supported"). If it is not: standalone, ask, then run `sf agent activate -o '<org>' --api-name '<BotDevName>'` and confirm `BotVersion.Status = Active`; delegated, return `failed` "Agentforce Service Agent <name> is not active".
