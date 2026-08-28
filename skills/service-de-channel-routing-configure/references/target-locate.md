---
name: service-de-channel-routing-configure-target-locate
description: "Load when configuring a non-queue routing type on service-de-channel-routing-configure (Flow, ASA, Digital Worker, or direct User). Holds the per-domain SOQL to locate and validate an eligible SessionHandler target, the exact Id shape each PATCH needs, the FallbackQueue requirement matrix, and the per-domain 'no eligible target' Setup pointer. DO NOT load this for the Omni-Channel Queue path — see references/queue-creation.md."
metadata:
  version: "1.0"
  related-skills: service-de-channel-routing-configure
---

# Locating a SessionHandler target (Flow / ASA / Digital Worker / User)

`MessagingChannel.SessionHandler` is a polymorphic foreign key. Its domain (from `MessagingChannel.entity.xml`) is `Queue, FlowDefinition, User, BotDefinition, AgenticCtxtDecorDefinition`. The Id prefix identifies the domain, and the server-side `validateSessionHandler` enforces a per-domain FallbackQueue rule that this skill must satisfy before the PATCH will succeed.

## FallbackQueue requirement matrix (server-enforced)

| routingType | SessionHandlerId prefix | FallbackQueueId |
| --- | --- | --- |
| queue | `00G` | **must be null** — a non-null value is rejected with `UnsupportedFallbackQueue` |
| flow | `300` | **required** — null is rejected with *"A Fallback Queue must be specified when selecting a Flow routing method."* (verified live on sdb6c 2026-08-12) |
| asa | `0Xx` | **required** — null rejected with `MissingFallbackQueueForAsaRouting` |
| digital_worker | `1iE` | **required** — null rejected with `MissingFallbackQueueForDigitalWorkerRouting` |
| user | `005` | **must be null** |

For every FallbackQueue-required path, resolve a FallbackQueue **first** (see below) so the SessionHandler + FallbackQueue can be written in a single PATCH — the record must never sit in an invalid intermediate state.

## Resolving a FallbackQueue (flow / asa / digital_worker)

The FallbackQueue is an Omni-Channel-enabled, MessagingSession-capable Queue — the same eligibility as the primary Queue path. Enumerate and let the user pick (or reuse the one they already have in mind):

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, Name, DeveloperName FROM Group WHERE Type = 'Queue' AND QueueRoutingConfigId != null AND Id IN (SELECT QueueId FROM QueueSobject WHERE SobjectType = 'MessagingSession') ORDER BY Name" \
  --json > /tmp/ccr-fallback-queues.json
```

Each row's `Id` (a `00G` `Group.Id`) is a valid `{FALLBACK_QUEUE_ID}`. If this returns 0 rows, emit `{ok:false, kind:"no-fallback-queue", ...}` — the user must create a MessagingSession queue (queue path → `references/queue-creation.md`) before Flow/ASA/Digital Worker routing can be configured.

---

## Flow (`300` FlowDefinition) — VERIFIED live on sdb6c

The SessionHandler value is the **`FlowDefinition.Id`** (`300`-prefixed), not the flow version. Eligible flows are `ProcessType='RoutingFlow'` with an active version. `ProcessType` lives on `FlowDefinitionView` (the `FlowDefinition` sObject has no `ProcessType` column), and `FlowDefinitionView.DurableId` equals the `300` FlowDefinition Id **only for org-local flows** (namespaced/packaged flows carry a `<namespace>__<ApiName>` DurableId that is *not* a `300` id and can't be used directly). So filter to org-local, active RoutingFlows:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT DurableId, Label, ApiName, NamespacePrefix, IsActive, ActiveVersionId FROM FlowDefinitionView WHERE ProcessType = 'RoutingFlow' AND IsActive = true AND NamespacePrefix = null ORDER BY Label" \
  --json > /tmp/ccr-flows.json
```

Keep only rows where `DurableId` starts with `300`. That `DurableId` is `{TARGET_ID}`. Present the list, let the user pick, resolve a FallbackQueue, then Stage 5 PATCH (`SessionHandlerId={TARGET_ID} FallbackQueueId={FALLBACK_QUEUE_ID}`).

If 0 eligible rows: `{ok:false, kind:"no-eligible-target", routingType:"flow", hint:"no active Omni-Channel RoutingFlow found — build one in Setup → Flows (template 'Route Work Item' / process type Routing Flow) and activate it, then re-run this skill"}`.

**Verified 2026-08-12 (sdb6c):** `DirectToAgentFlow` (`300SG0000002gw1YAA`, active RoutingFlow) + FallbackQueue `Messaging_Queue` (`00GSG0000000LSf2AM`) PATCHed onto Enhanced channel `Customer_Support` (`0MjSG0000004rIf0AI`) → success, both fields persisted. Nulling the FallbackQueue afterward was rejected with the "A Fallback Queue must be specified" message. Channel restored to null/null.

---

## ASA (`0Xx` BotDefinition) — VERIFIED live on sdb6c

ASA = an Agentforce Service Agent bot: `BotDefinition WHERE Type='ExternalCopilot' AND AgentType='EinsteinServiceAgent'`, routable only if it has a linked bot user AND an active version. The full precondition/enumeration/selection detail lives in `references/asa-routing.md` — load that. ASA additionally **requires a FallbackQueue** (resolve one as above), which the PATCH writes alongside the `0Xx` SessionHandler.

**Verified 2026-08-12 (sdb6c):** `Type='ExternalCopilot' AND AgentType='EinsteinServiceAgent'` returns two bots; one (`0XxSG000000Sv9p0AC`) has both `BotUserId` and an active `BotVersion` (routable), the other (`ASA2`) has no active version (listed but flagged not-live). Note: the Data-API `BotDefinition` sObject exposes only `Type` / `AgentType` / `AgentTemplate` (no version/rich-content columns) — the active-version check must go through the `BotVersions` child relationship / `BotUserId`, exactly as `references/asa-routing.md` does.

---

## Digital Worker (`1iE` AgenticCtxtDecorDefinition) — NOT live-verifiable on sdb6c

The SessionHandler domain `AgenticCtxtDecorDefinition` (Digital Worker, added v262) is gated by the org permission `orgHasOmniChannelScrt2DigitalWorkerRouting` (per `LiveAgentPresenceUtilImpl.isActiveDigitalWorker`). On sdb6c that object is **not SOQL-addressable** (`INVALID_TYPE`), which means the perm/feature isn't enabled there — so this path could not be verified against a live org.

Intended locate (unverified — validate against an org that has the perm before relying on it):

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MasterLabel FROM AgenticCtxtDecorDefinition ORDER BY MasterLabel" \
  --json > /tmp/ccr-digital-workers.json
```

`Id` (`1iE`-prefixed) is `{TARGET_ID}`. FallbackQueue is **required** (server rejects null with `MissingFallbackQueueForDigitalWorkerRouting`). If the object errors with `INVALID_TYPE`, emit `{ok:false, kind:"no-eligible-target", routingType:"digital_worker", hint:"this org doesn't have Digital Worker routing enabled (AgenticCtxtDecorDefinition not available) — use a different routing type or contact your Salesforce rep to enable it"}`.

---

## User (`005`) — PARTIALLY verified on sdb6c

Direct-to-user routing points SessionHandler at a `User` with FallbackQueue **null**. `validateSessionHandler` additionally requires the user to have a RoutingConfiguration (else `NoRoutingConfigDefined`) — but this is **not** a direct field on `User` (`User.RoutingConfigurationId` does not exist). The linkage runs through Omni-Channel presence configuration: `PresenceUserConfig` (the config, which references a routing/priority setup) joined to users via `PresenceUserConfigUser`.

Locate eligible users (those assigned to a presence config, which carries the routing configuration):

```bash
# users assigned to an Omni-Channel presence config
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT UserId, User.Name, PresenceUserConfigId FROM PresenceUserConfigUser WHERE User.IsActive = true ORDER BY User.Name" \
  --json > /tmp/ccr-users.json
```

`UserId` (`005`-prefixed) is `{TARGET_ID}`; FallbackQueue stays null. Present, let the user pick, then Stage 5 PATCH (`SessionHandlerId={TARGET_ID}` only).

If 0 rows: `{ok:false, kind:"no-eligible-target", routingType:"user", hint:"no users are assigned to an Omni-Channel presence configuration with routing — set one up in Setup → Omni-Channel → Presence Configurations, then re-run this skill"}`.

**Verified 2026-08-12 (sdb6c):** the *persisted-state* rule is confirmed — Enhanced channel `Facebook_US_104218168883106` (`0MjSG0000000C7d0AE`) carries `SessionHandlerId=005SG00000051bNYAQ` with `FallbackQueueId=null`, so User-as-SessionHandler with a null FallbackQueue is a valid live configuration. The *locate query* (`PresenceUserConfigUser`) and the RoutingConfiguration precondition were not exercised end-to-end via a fresh PATCH; treat the enumeration query as best-effort and confirm the picked user actually has routing before relying on activation.
