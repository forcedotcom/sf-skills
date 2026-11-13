---
name: service-de-channel-routing-configure-gotchas
description: "Load when debugging an unexpected result from service-de-channel-routing-configure, or before implementing changes to it. Covers the known gotchas: Group.Type filtering, DeveloperName uniqueness, QueueRoutingConfig naming, empty-queue caveats, Metadata-API-only queue creation, the per-domain FallbackQueue requirement matrix, the server-side nullQueueId enforcement point, the Standard-vs-Enhanced SessionHandler write restriction, and SessionHandler polymorphism differences across org shapes. DO NOT load this during a normal first-time routing configuration run — only when troubleshooting or modifying the skill."
metadata:
  version: "1.0"
  related-skills: service-de-channel-routing-configure
---

# Gotchas

1. **The `sf data query` `Group.Type='Queue'` filter matters.** `Group` also holds roles/role-and-subordinates/public-groups etc. Always filter on `Type='Queue'` when reading for a queue. (Entity shape confirmed on test1: 2 MessagingSession-capable queues present, both with `Type='Queue'`, both with matching `QueueSobject.SobjectType='MessagingSession'`.)

2. **`DeveloperName` must be unique across all Queues.** A deploy with a duplicate DevName is rejected with `duplicate value found: DeveloperName duplicates value on record with id: <existingId>`. Either detect that up front (query Group first) or let the deploy fail and re-prompt.

3. **`QueueRoutingConfig.DeveloperName` must also be globally unique.** The skill names it `{QUEUE_DEV_NAME}_Routing` to stay unique per queue. Keep this pattern — don't reuse a single routing config across queues unless the user explicitly asks.

4. **A queue without members still PATCHes fine, and `activateChannelUsage` still succeeds.** But the channel won't actually route messages anywhere until someone joins the queue with an Omni Presence. The skill's "add self" option papers over this for demo/test orgs; for prod, the caller is responsible for populating the queue separately.

5. **Queue + QueueRoutingConfig via Metadata API, NOT via `sf data create record`.** The REST sObject insert for `Group(Type=Queue)` works for the Group row itself but does NOT create the routing config, and some related `QueueMember`/Omni-Presence linkage is done server-side only by the Metadata API deploy. Stick with the metadata path — that's how `help-agent-accelerator` does it, and it's what we validated against test1.

6. **`FallbackQueueId` is required for some SessionHandler domains and forbidden for others — it is NOT interchangeable.** The rule (from `MessagingChannelFunctionsHelper.validateSessionHandler`, cross-verified live): Flow (`300`), ASA (`0Xx`), and Digital Worker (`1iE`) **require** a non-null FallbackQueue; Queue (`00G`) and User (`005`) **require it null** (a non-null value is rejected with `UnsupportedFallbackQueue`). Setting a Flow SessionHandler with a null FallbackQueue is rejected with *"A Fallback Queue must be specified when selecting a Flow routing method."* (verified live on sdb6c 2026-08-12). See `references/target-locate.md` for the full matrix. This is why the FallbackQueue-required paths write both fields in a single PATCH.

7. **The `channelRouteTrafficModal.js` enforcement is UI-side only.** Server-side, activation readiness (`MessagingChannelReadinessChecker.isRoutingConfiguredForChannel`) requires a **SessionHandler-based** routing method — Queue-as-SessionHandler (`00G`), User (`005`), Flow (`300`+FallbackQueue), or ASA (`0Xx`+FallbackQueue). It inspects `SessionHandler`, **not** `TargetQueue`. A legacy Standard/SCRT1 channel could route via `TargetQueueId`, but that does not satisfy this Enhanced-channel readiness check — and these skills only create Enhanced channels, so always route via `SessionHandler`. Neither-set raises `LiveMessageSetupException` (`nullQueueId`) at activation.

8. **Standard (SCRT1) channels only accept a Flow as SessionHandler; Enhanced (SCRT2) channels accept all five domains.** `validateSessionHandler` (the `PlatformType==STANDARD` branch) rejects any non-Flow SessionHandler on a Standard channel with *"Only flows of type Omni-Channel are supported for a Messaging Channel"* — verified live: a `00G` Queue and a `0Xx` ASA both failed with that exact message on a Standard channel, and both succeeded on an Enhanced one. These skills create only Enhanced channels, so Stage 2 confirms `PlatformType=Enhanced` and bails with `kind:"standard-channel"` if it ever sees otherwise.

9. **`MessagingChannel.SessionHandler` polymorphism is org-shape-dependent.** The full domain is `[Group, FlowDefinition, User, BotDefinition, AgenticCtxtDecorDefinition]`, but `BotDefinition` (ASA) only materializes on Agentforce-licensed orgs and `AgenticCtxtDecorDefinition` (Digital Worker) only when `orgHasOmniChannelScrt2DigitalWorkerRouting` is enabled (not present on sdb6c). The ASA precondition check (Stage 3-ASA.0) and the Digital Worker `INVALID_TYPE` guard (`references/target-locate.md`) catch the missing-domain cases before a PATCH is attempted. Note the SOQL field surface is thinner than the internal representation: the Data-API `BotDefinition` sObject exposes only `Type`/`AgentType`/`AgentTemplate`, so the active-version check goes through the `BotVersions` child relationship, not an `ActiveVersionId` column.
