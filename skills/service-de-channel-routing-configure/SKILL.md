---
name: service-de-channel-routing-configure
description: "Configure routing on a newly-inserted Enhanced `MessagingChannel` so that activation will accept it. Given a `{CHANNEL_ID}`, walks the user through picking a routing type (Omni-Channel Queue, Omni-Flow, Agentforce Service Agent, Digital Worker, or direct User), locates or provisions the routing target, then PATCHes the channel's `SessionHandlerId` (plus `FallbackQueueId` where required) to it. Use between the insertion skill and the activation skill — activation fails server-side with `nullQueueId` / `LiveMessageSetupException` if no valid `SessionHandlerId` is set on the channel."
metadata:
  version: "1.1"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-consent-configure"
    - "service-de-channel-create"
    - "service-de-headless-channel-configure"
---

# Configuring Channel Routing

## What this skill does

Ensures a `MessagingChannel` has valid routing configured before activation. The channel's `SessionHandler` field is a **polymorphic foreign key** (verified against `MessagingChannel.entity.xml`, `domain="Queue, FlowDefinition, User, BotDefinition, AgenticCtxtDecorDefinition"`) — it names *who* the channel routes incoming sessions to. Some targets additionally require a `FallbackQueue` (an Omni-Channel Queue that catches sessions the primary target can't take).

These skills create **Enhanced** channels (`PlatformType=Enhanced`, SCRT2). All five SessionHandler domains are writable on Enhanced channels. (A Standard/SCRT1 channel would only accept a Flow as SessionHandler — the server rejects any other domain with "Only flows of type Omni-Channel are supported". These skills never create Standard channels, so that path isn't handled here.)

**Where this fits:** the channel is inserted by `service-de-channel-create` (or a per-type leaf); this skill sets routing; `service-de-channel-consent-configure` sets consent; then `service-de-channel-activate` flips it live — activation requires both routing and consent. The `service-de-headless-channel-configure` orchestrator runs all four in sequence.

Supported routing types — all set `SessionHandlerId`, some also set `FallbackQueueId`:

| Type | SessionHandler target | Id prefix | FallbackQueue |
| --- | --- | --- | --- |
| **Omni-Channel Queue** | `Group` (Type=Queue) | `00G` | must be **null** |
| **Omni-Flow** | `FlowDefinition` (ProcessType=RoutingFlow) | `300` | **required** |
| **Agentforce Service Agent (ASA)** | `BotDefinition` (Type=ExternalCopilot) | `0Xx` | **required** |
| **Digital Worker** | `AgenticCtxtDecorDefinition` | `1iE` | **required** |
| **User** | `User` (with a RoutingConfiguration) | `005` | must be **null** |

Provisioning behavior:
- **Queue** — pick an existing `MessagingSession`-capable Queue, or create a new Queue + QueueRoutingConfig via Metadata API.
- **Flow / ASA / Digital Worker / User** — locate an existing eligible target and PATCH it. These skills do **not** create Flows, bots, digital workers, or users — if none eligible exist, the skill reports the precondition and points the user at Setup.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/queue-creation.md` | The user picked "create a new queue" on the Queue routing path — full Metadata API scaffold → deploy → ID lookup → optional member add. |
| `references/target-locate.md` | You need the per-domain SOQL to locate and validate an eligible target (Queue, Flow, ASA, Digital Worker, User) and the FallbackQueue requirement matrix. |
| `references/asa-routing.md` | The user picked ASA (Agentforce Service Agent) routing — precondition check, enumerating live ASAs, and selection. |
| `references/gotchas.md` | Troubleshooting an unexpected result, or before modifying this skill — the known gotchas. |
| `references/worked-examples.md` | You want a reference run of the reuse-existing-queue, create-new-queue, Flow, or ASA paths. |

## When NOT to use this skill

- **The channel already has `SessionHandlerId` or `FallbackQueueId` set.** This skill no-ops and tells you — nothing to do. Proceed to activation.
- **The channel doesn't exist yet.** Run the insertion skill first; this skill expects a real `MessagingChannel.Id`.
- **You want to replace existing routing.** Safer to clear `SessionHandlerId` manually in the UI, then re-run this skill. The no-op check is a guardrail, not a limitation worth bypassing automatically.

## Inputs (from caller)

- `{CHANNEL_ID}` — a 15- or 18-char `MessagingChannel.Id` (prefix `0Mj`). The channel must already exist.
- `{ORG_ALIAS}` — optional; the `sf` CLI target-org alias. Default: whatever `sf config get target-org` returns. All SOQL, PATCH, and Metadata deploys run against this org.

## Output (to caller)

One of:

**Success — no change needed:**
```json
{"ok": true, "noop": true, "routingType": "queue|flow|asa|digital_worker|user", "sessionHandlerId": "00G...|300...|0Xx...|1iE...|005...", "fallbackQueueId": "00G...|null", "targetName": "...", "message": "Routing already configured"}
```

**Success — Queue routing configured:**
```json
{"ok": true, "routingType": "queue", "sessionHandlerId": "00G...", "fallbackQueueId": null, "queueName": "...", "queueDeveloperName": "...", "created": true|false}
```

**Success — Flow routing configured:**
```json
{"ok": true, "routingType": "flow", "sessionHandlerId": "300...", "fallbackQueueId": "00G...", "flowName": "...", "flowDeveloperName": "...", "created": false}
```

**Success — ASA routing configured:**
```json
{"ok": true, "routingType": "asa", "sessionHandlerId": "0Xx...", "fallbackQueueId": "00G...", "asaName": "...", "asaDeveloperName": "...", "botUserId": "005...", "botVersionId": "0X9...", "created": false}
```

**Success — Digital Worker routing configured:**
```json
{"ok": true, "routingType": "digital_worker", "sessionHandlerId": "1iE...", "fallbackQueueId": "00G...", "workerName": "...", "created": false}
```

**Success — User routing configured:**
```json
{"ok": true, "routingType": "user", "sessionHandlerId": "005...", "fallbackQueueId": null, "userName": "...", "created": false}
```

**Precondition not met:**
```json
{"ok": false, "kind": "no-eligible-target", "routingType": "flow|asa|digital_worker|user", "hint": "no eligible <target> found on this org — <how to create one in Setup>, then re-run this skill"}
{"ok": false, "kind": "no-fallback-queue", "hint": "Flow/ASA/Digital Worker routing requires a FallbackQueue but no MessagingSession-capable queue exists — create one (Queue routing path) first"}
{"ok": false, "kind": "asa-not-supported", "hint": "this org doesn't have BotDefinition (Agentforce not licensed); use Queue routing instead"}
{"ok": false, "kind": "standard-channel", "hint": "this is a Standard (SCRT1) channel — only Flow routing is supported; these skills only create Enhanced channels, so this is unexpected"}
```

**Failure:**
```json
{"ok": false, "kind": "metadata-deploy-failed", "message": "..."}
{"ok": false, "kind": "patch-failed", "message": "..."}
{"ok": false, "kind": "verify-failed", "hint": "PATCH returned success but re-read shows SessionHandlerId still null — permission or trigger issue"}
```

The PATCH failure `message` often carries the server-side validation error verbatim (from `MessagingChannelFunctionsHelper.validateSessionHandler`). Surface it — it tells the user exactly which linking rule failed. Common ones: `MissingFallbackQueueForFlowRouting` / `...ForAsaRouting` / `...ForDigitalWorkerRouting` (FallbackQueue required but null), `UnsupportedFallbackQueue` (FallbackQueue set on a Queue/User path where it must be null), `InvalidSessionHandlerFlowType` (Flow isn't ProcessType=RoutingFlow, **or** the channel is Standard/SCRT1), `NoRoutingConfigDefined` (User has no RoutingConfiguration).

---

## Stage 1: Read current routing state

Query the channel. If it already has `SessionHandlerId` OR `FallbackQueueId`, no-op. Otherwise, continue.

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" \
  --json > /tmp/ccr-channel.json
```

Parse with `node -e` or `jq`. If the record is missing — halt with `Error: Channel {CHANNEL_ID} not found — check the id, or run the insertion skill first.`

If `SessionHandlerId` is non-null, branch on the Id prefix to figure out what the existing routing target is, then no-op with the right envelope. The prefix maps 1:1 to the SessionHandler domain (verified against `MessagingChannel.entity.xml`):

| Prefix | Domain / Target | Lookup query | routingType |
| --- | --- | --- | --- |
| `00G` | `Group` (Type=Queue) | `SELECT Id, Name, DeveloperName FROM Group WHERE Id='<sh>' AND Type='Queue'` | `queue` |
| `300` | `FlowDefinition` | `SELECT DurableId, Label, ApiName FROM FlowDefinitionView WHERE DurableId='<sh>'` | `flow` |
| `0Xx` | `BotDefinition` (ASA) | `SELECT Id, DeveloperName, MasterLabel, AgentType FROM BotDefinition WHERE Id='<sh>'` | `asa` |
| `1iE` | `AgenticCtxtDecorDefinition` (Digital Worker) | `SELECT Id, DeveloperName, MasterLabel FROM AgenticCtxtDecorDefinition WHERE Id='<sh>'` | `digital_worker` |
| `005` | `User` | `SELECT Id, Name FROM User WHERE Id='<sh>'` | `user` |

```bash
SESSION_HANDLER_ID="$(node -e 'console.log(JSON.parse(require("fs").readFileSync("/tmp/ccr-channel.json","utf8")).result.records[0].SessionHandlerId)')"
PREFIX="${SESSION_HANDLER_ID:0:3}"
case "$PREFIX" in
  00G) sf data query --target-org '{ORG_ALIAS}' --query "SELECT Id, Name, DeveloperName FROM Group WHERE Id = '$SESSION_HANDLER_ID' AND Type = 'Queue'" --json > /tmp/ccr-noop-target.json ;;
  300) sf data query --target-org '{ORG_ALIAS}' --query "SELECT DurableId, Label, ApiName FROM FlowDefinitionView WHERE DurableId = '$SESSION_HANDLER_ID'" --json > /tmp/ccr-noop-target.json ;;
  0Xx) sf data query --target-org '{ORG_ALIAS}' --query "SELECT Id, DeveloperName, MasterLabel, AgentType FROM BotDefinition WHERE Id = '$SESSION_HANDLER_ID'" --json > /tmp/ccr-noop-target.json ;;
  1iE) sf data query --target-org '{ORG_ALIAS}' --query "SELECT Id, DeveloperName, MasterLabel FROM AgenticCtxtDecorDefinition WHERE Id = '$SESSION_HANDLER_ID'" --json > /tmp/ccr-noop-target.json ;;
  005) sf data query --target-org '{ORG_ALIAS}' --query "SELECT Id, Name FROM User WHERE Id = '$SESSION_HANDLER_ID'" --json > /tmp/ccr-noop-target.json ;;
  *)   echo "{\"records\":[{\"Id\":\"$SESSION_HANDLER_ID\"}]}" > /tmp/ccr-noop-target.json ;;
esac
```

Report the success-noop envelope (include the existing `FallbackQueueId` from the Stage 1 read) and return.

If `FallbackQueueId` is non-null but `SessionHandlerId` is null — still no-op. That's a partially-configured Flow/ASA state; don't touch it, but flag it in the envelope `message` (`"FallbackQueue set but SessionHandler null — incomplete routing, review in Setup"`) since activation will still fail readiness without a SessionHandler.

---

## Stage 2: Confirm the channel is Enhanced, then choose routing type

First confirm `PlatformType`. The Stage 1 read didn't include it — add it, or re-query:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, PlatformType FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" --json > /tmp/ccr-platform.json
```

If `PlatformType != 'Enhanced'` (i.e. Standard/SCRT1), only Flow routing is writable. These skills only create Enhanced channels, so a Standard channel here is unexpected — emit `{ok:false, kind:"standard-channel", ...}` and stop rather than guessing.

Then ask the user (via a prompt — do NOT auto-pick):

```text
The MessagingChannel '{developerName}' ({CHANNEL_ID}) has no routing configured.
Which routing type do you want?

  1) queue          — Omni-Channel queue routing
  2) flow           — Omni-Flow (RoutingFlow) + fallback queue
  3) asa            — Agentforce Service Agent (requires Agentforce license) + fallback queue
  4) digital_worker — Digital Worker (Agentic) + fallback queue
  5) user           — Direct to a specific user (requires a RoutingConfiguration on the user)

Pick [1-5]:
```

Branch on the user's pick. For every non-queue path, **load `references/target-locate.md`** — it holds the per-domain locate SOQL, eligibility filters, FallbackQueue rules, and exact PATCH shape:

- **1 (queue)** — continue to Stage 3-Queue below.
- **2 (flow)** — locate an eligible `FlowDefinition` (ProcessType=RoutingFlow, active version) + a FallbackQueue, then Stage 5.
- **3 (asa)** — continue to Stage 3-ASA; ASA requires a FallbackQueue too.
- **4 (digital_worker)** — locate an eligible `AgenticCtxtDecorDefinition` + a FallbackQueue, then Stage 5.
- **5 (user)** — locate a `User` that has a RoutingConfiguration, then Stage 5.

If a path finds no eligible target, emit `{ok:false, kind:"no-eligible-target", routingType, hint}` (see `references/target-locate.md` for the per-domain Setup pointer) and return — do not fabricate an id.

---

## Stage 3-Queue: Pick an existing queue, or create a new one

*(This stage runs only on the Queue path. ASA path: see Stage 3-ASA below.)*

Enumerate eligible queues. The UI's routing dropdown (`MessagingRoutingMethodDataProviderController.getOmniQueues`) lists Groups where `QueueRoutingConfigId != null` — i.e. Omni-Channel-enabled queues. For a MessagingChannel we additionally want the queue to accept `MessagingSession`. Query the intersection: enumerate MessagingSession-capable queues, then keep only those with a QueueRoutingConfig.

```bash
# MessagingSession-capable queues that are also Omni-enabled (QueueRoutingConfigId != null)
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, Name, DeveloperName FROM Group WHERE Type = 'Queue' AND QueueRoutingConfigId != null AND Id IN (SELECT QueueId FROM QueueSobject WHERE SobjectType = 'MessagingSession') ORDER BY Name" \
  --json > /tmp/ccr-queues.json
```

Each row's `Id` is the `00G` `Group.Id` — that is what gets written to `SessionHandlerId`. (If the semi-join subquery errors on an org, fall back to two queries: list `QueueSobject WHERE SobjectType='MessagingSession'`, then filter to those whose `Group.QueueRoutingConfigId != null`.)

Present the user with a numbered list plus a final "create new" option:

```text
Omni-enabled MessagingSession queues on {ORG_ALIAS}:

  1) Messaging Queue (Messaging_Queue) — 00GSG0000000LSf2AM
  2) MyQueue (MyQueue) — 00GSG000000144n2AA
  ...
  N) Create a new queue

Pick [1-N]:
```

- **If the user picks an existing queue**: record its `Id` as `{QUEUE_ID}` (this is the `Group.Id`). Skip to Stage 5.
- **If the user picks "create new"**: go to Stage 4.

If the list is empty AND the user picks (1) "Create a new queue" implicitly, skip directly to Stage 4.

---

## Stage 3-Queue, continued: Create a new Queue via Metadata API

*(Continuation of the Queue path. Skip if the user picked an existing queue above.)*

We deploy a Queue + QueueRoutingConfig pair using a minimal scratch sfdx project (the `help-agent-accelerator` pattern), then look up the new Queue's Id and optionally add the current user as a member.

**To create a new Queue via the Metadata API (sfdx project scaffold → deploy → ID lookup → optional member add), load `references/queue-creation.md` and follow it — it is the complete guide for this flow.**

After that stage, jump to Stage 5 (PATCH).

---

## Stage 3-ASA: Pick an existing ASA

*(This stage runs only on the ASA path. Queue path: skip to Stage 5.)*

ASA routing points `SessionHandlerId` at an existing, live Agentforce Service Agent (`BotDefinition`). This skill never creates a new ASA — it verifies the org supports one (Agentforce licensed), enumerates the live/routable ones, and lets the user pick.

**For ASA precondition checks, enumeration, and selection, load `references/asa-routing.md`.** After selection, continue to Stage 5 (PATCH).

---

## Stage 5: PATCH `MessagingChannel.SessionHandlerId` (+ `FallbackQueueId`)

By this point we have a **routing target id** in `{TARGET_ID}` and know its `{ROUTING_TYPE}`:

| routingType | `{TARGET_ID}` | FallbackQueue write |
| --- | --- | --- |
| `queue` | `00G` `Group.Id` | none (must stay null) |
| `flow` | `300` `FlowDefinition` id | set `FallbackQueueId={FALLBACK_QUEUE_ID}` |
| `asa` | `0Xx` `BotDefinition.Id` | set `FallbackQueueId={FALLBACK_QUEUE_ID}` |
| `digital_worker` | `1iE` `AgenticCtxtDecorDefinition.Id` | set `FallbackQueueId={FALLBACK_QUEUE_ID}` |
| `user` | `005` `User.Id` | none (must stay null) |

`SessionHandler` is a polymorphic FK spanning `[Group, FlowDefinition, User, BotDefinition, AgenticCtxtDecorDefinition]` (per `MessagingChannel.entity.xml`; the BotDefinition/AgenticCtxtDecorDefinition targets only materialize on Agentforce-licensed orgs). The standard REST sObject PATCH accepts whichever Id type fits. The **FallbackQueue rule is enforced server-side** (`validateSessionHandler`): Flow/ASA/Digital Worker reject a null FallbackQueue; Queue/User reject a non-null one.

For the FallbackQueue paths, write both fields in one PATCH so the record never passes through an invalid intermediate state:

```bash
# queue / user — SessionHandler only
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' \
  --values 'SessionHandlerId={TARGET_ID}' --json > /tmp/ccr-patch.json

# flow / asa / digital_worker — SessionHandler + FallbackQueue together
sf data update record --target-org '{ORG_ALIAS}' --sobject MessagingChannel \
  --record-id '{CHANNEL_ID}' \
  --values 'SessionHandlerId={TARGET_ID} FallbackQueueId={FALLBACK_QUEUE_ID}' --json > /tmp/ccr-patch.json
```

If `status !== 0`: emit `{ok:false, kind:"patch-failed", message: ...}` and return. Surface the server message verbatim — it names the exact linking rule that failed (see the failure-envelope note under "Output (to caller)").

---

## Stage 6: Verify

Re-read the channel:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" \
  --json
```

If the freshly-read `SessionHandlerId` doesn't equal `{TARGET_ID}` — or (for flow/asa/digital_worker) `FallbackQueueId` doesn't equal `{FALLBACK_QUEUE_ID}`:
```json
{"ok": false, "kind": "verify-failed", "hint": "PATCH returned success but re-read shows SessionHandlerId/FallbackQueueId not persisted — check user permissions or field-level security on MessagingChannel"}
```

Otherwise, emit the path-appropriate success envelope (see "Output (to caller)" at the top of this file — one shape per routingType, each carrying `fallbackQueueId`).

---

## Stage 7: Report to caller

Report the JSON envelope. If this skill is the leaf (user invoked it directly), render:

**Queue path:**
- `Success — Routing configured — channel {CHANNEL_ID} now routes to Queue '{QUEUE_LABEL}' ({QUEUE_ID}).{'' if created else ' (reused existing queue)'}`
- `Info: Routing already configured — Queue '{name}' ({QUEUE_ID}). No changes.` (no-op path)

**Flow path:**
- `Success — Routing configured — channel {CHANNEL_ID} now routes to Omni-Flow '{FLOW_LABEL}' ({TARGET_ID}), fallback Queue {FALLBACK_QUEUE_ID}.`

**ASA path:**
- `Success — Routing configured — channel {CHANNEL_ID} now routes to Agentforce Service Agent '{ASA_LABEL}' ({ASA_ID}), fallback Queue {FALLBACK_QUEUE_ID}. Bot user: {BOT_USER_ID}. Active version: {BOT_VERSION_ID}.`
- `Info: Routing already configured — ASA '{MasterLabel}' ({ASA_ID}). No changes.` (no-op path)

**Digital Worker path:**
- `Success — Routing configured — channel {CHANNEL_ID} now routes to Digital Worker '{WORKER_LABEL}' ({TARGET_ID}), fallback Queue {FALLBACK_QUEUE_ID}.`

**User path:**
- `Success — Routing configured — channel {CHANNEL_ID} now routes directly to User '{USER_NAME}' ({TARGET_ID}).`

**Failure / precondition:**
- `Warning: No eligible {routingType} target found. {per-domain Setup pointer from references/target-locate.md}. Then re-run this skill.` (no-eligible-target)
- `Warning: {routingType} routing needs a fallback queue but none exists. Create a MessagingSession queue first (queue path), then re-run.` (no-fallback-queue)
- `Warning: This org doesn't have Agentforce licensed (no BotDefinition entity). Use Queue routing instead.` (asa-not-supported)
- `Warning: This is a Standard (SCRT1) channel — only Flow routing is supported. These skills only create Enhanced channels, so this is unexpected; check the channel.` (standard-channel)
- `Error: {kind}: {message}` (other failures — the message names the server-side validation rule that failed)

---

## Worked examples

For reference runs of both the reuse-an-existing-queue fast path (validated on test1) and the create-a-new-queue-via-Metadata-API path, see `references/worked-examples.md`.

---

## Gotchas

Known gotchas — `Group.Type` filtering, DeveloperName uniqueness, QueueRoutingConfig naming, empty-queue caveats, Metadata-API-only queue creation, the per-domain **FallbackQueue requirement matrix**, the server-side `nullQueueId` / readiness enforcement point, the **Standard-vs-Enhanced** SessionHandler write restriction, and `SessionHandler` polymorphism across org shapes.

**When troubleshooting an unexpected result, or before modifying this skill, load `references/gotchas.md` and follow it — it is the complete list.**
