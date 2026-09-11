# Omni Flow routing (Agentforce agent on voice)

Two routing models attach a `PstnVoice` channel to the contact center:

| Model | `SessionHandlerId` | `FallbackQueueId` | Use when |
|-------|--------------------|-------------------|----------|
| **Omni Queue** (default) | ACC queue Id (`00G…`) | — | Calls land straight in the contact center queue for human reps. |
| **Omni Flow** | inbound RoutingFlow **FlowDefinition** Id (`300…`) | ACC/voice queue Id (`00G…`) | Calls route to an Agentforce agent first, with the queue as fallback/escalation. |

Omni Queue is the skill's original behavior (Step 8). This file covers **Omni Flow**.

## The wiring contract

An Omni Flow channel points its `SessionHandlerId` at an **inbound RoutingFlow** (not a queue) and names the queue in `FallbackQueueId`. That inbound flow references a **published, active** Agentforce agent. So the flow and agent must exist *before* the channel is created:

```text
agent (published + Active)  ->  inbound RoutingFlow (Active, 300-prefix)  ->  channel
                                escalation RoutingFlow (Active)           ->  agent outbound (optional)
```

`FlowDefinition` (Id prefix `300`) is the stable handle used in `SessionHandlerId` — not the per-version `Flow` (prefix `301`).

## Sub-fork: new vs existing

- **Use existing** — the user supplies an already-published agent and an active inbound RoutingFlow. Resolve the flow's `300` Id with `scripts/resolve-flow-definition.sh <alias> <flow-dev-name>`, then create the channel (below). Skip agent/flow creation.
- **Create new** — build both, in order:
  1. **Preflight** — `scripts/check-agentforce-prereq.sh <alias>` must return a canonical `Einstein Agent User` profile user. It can provision one with `sf org create agent-user` if the org has capacity. Do not use broad Agent/Bot profile matches.
  2. **Work dir** — `scripts/prepare-agent-workdir.sh acc-voice-build`, then run `sf agent generate agent-spec ... --output-file specs/<api-name>.yaml --target-org <alias>` from inside `acc-voice-build`; the spec generator requires SFDX project context.
  3. **Agent** — from the parent/original work dir, run `scripts/create-voice-agent.sh <alias> <api-name> <label> acc-voice-build/specs/<api-name>.yaml acc-voice-build`. The script generates the authoring bundle, replaces the generator's `default_agent_user: "NEW AGENT USER"` placeholder with the spec's `agentUser`, deploys the `AiAuthoringBundle`, validates, publishes, and activates.
  4. **Flows** — `scripts/create-routing-flows.sh <alias> <api-name> <label> <queue-id> <queue-name> acc-voice-build`. Renders and deploys the inbound (`_Voice_Omni_Flow`) and escalation (`_Voice_Escalation`) flows from inside the SFDX work dir and prints the inbound `300` Id.

## Create the channel

```bash
scripts/create-voice-channel.sh <alias> <number> <channelLineId> <flowDefinitionId> <queueId>
# 5th arg present -> Omni Flow: SessionHandlerId=<flowDefinitionId 300>, FallbackQueueId=<queueId>
```

## RoutingFlow field contract

Both flows are `processType: RoutingFlow`, `status: Active`, on the `sfdc_phone` service channel (`serviceChannelLabel: Phone`). Templates: `assets/omni-flow.flow-meta.xml`, `assets/escalation-flow.flow-meta.xml`.

| Field | Inbound (`_Voice_Omni_Flow`) | Escalation (`_Voice_Escalation`) |
|-------|------------------------------|----------------------------------|
| `routingType` | `Copilot` (routes to the agent) | `QueueBased` (routes to the queue) |
| `copilotId` | `<setupReference>` → `BotDefinition` = agent api-name (required) | — |
| `copilotLabel` | agent `MasterLabel` | — |
| `queueId` / `queueLabel` | fallback queue (18-char Id + `Name`) | escalation queue |

## Deviation — planner type

Do **not** switch the agent's `plannerType` to `Atlas__VoiceAgent` (or add `plannerSurfaces`). This org (API ≤ 67) rejects it with an opaque server error (e.g. `-1103525358`), even with a complete published bundle. Keep the `Atlas__ConcurrentMultiAgentOrchestration` planner that `sf agent publish` generates — **inbound voice routes correctly via the `Copilot` RoutingFlow regardless of planner type** (verified against the org's own working voice agent). `create-voice-agent.sh` never touches the planner, so no action is needed; just don't add a planner-swap step.

## Fallback to Omni Queue

If the Agentforce prerequisite can't be confirmed (`references/agentforce-prerequisite.md`), or agent/flow creation fails, stop and report unless the user explicitly accepts a queue-only fallback. Some runs require an Agentforce agent and Omni Flow channel, so do not silently downgrade the routing model.

## Agent creation gotchas

| Symptom | Fix |
|---------|-----|
| `RequiresProjectError` from `sf agent generate agent-spec` | Prepare and run from `acc-voice-build` with `scripts/prepare-agent-workdir.sh` |
| `default agent user NEW AGENT USER` during publish | Let `create-voice-agent.sh` patch the generated `.agent` from the spec's `agentUser` before deploy/publish |
| `Unable to access the Salesforce Agent APIs` / `User doesn't have access to use agent` | Ensure `agentUser` is a canonical `Einstein Agent User` profile user, not a generic Agent/Bot-profile user |
| `InvalidProjectWorkspaceError` during flow deploy | Reuse the prepared work dir; `create-routing-flows.sh` deploys from inside it |

## Verify

```sql
SELECT Id, DeveloperName, MessageType, SessionHandlerId, FallbackQueueId, IsActive
FROM MessagingChannel WHERE Id = '<channel-id>'
```

`SessionHandlerId` must start with `300` (the inbound FlowDefinition) and `FallbackQueueId` with `00G` (the queue).
