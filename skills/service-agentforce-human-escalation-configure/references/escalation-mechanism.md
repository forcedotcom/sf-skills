# Escalation mechanism reference

Agent → human escalation in Agentforce is assembled from three declarative surfaces plus
one instruction surface. Only the first three are deterministically writable and verifiable
via the Metadata/Data API; the fourth (threshold policy) is directive text verified by
eval, and the actual conversational trigger is manual/runtime.

## 1. `canEscalate` on the escalation topic (`GenAiPlugin`)

The agent topic that represents "hand off to a human" must have `<canEscalate>true</canEscalate>`.
Retrieve the topic, set the flag, redeploy.

```bash
sf project retrieve start --target-org "$ORG" \
  --metadata "GenAiPlugin:${ESCALATION_TOPIC_API_NAME}" --target-metadata-dir /tmp/esc
# edit <canEscalate>true</canEscalate> in the retrieved -meta.xml
sf project deploy start --target-org "$ORG" --metadata "GenAiPlugin:${ESCALATION_TOPIC_API_NAME}"
```

Verify (the retrieved XML must contain `<canEscalate>true</canEscalate>`). There is no
SOQL object for `canEscalate`; the source of truth is the retrieved metadata.

## 2. `outboundRouteConfigs` on the agent's Messaging planner surface (`GenAiPlannerBundle`)

The `GenAiPlannerBundle` for the agent carries the Messaging surface. Its
`outboundRouteConfigs` block wires the escalation to an Omni-Channel outbound flow:

```xml
<outboundRouteConfigs>
    <escalationMessage>Transferring you to a live support agent.</escalationMessage>
    <outboundRouteName>Human_Escalation_Outbound_Flow</outboundRouteName>
    <outboundRouteType>OmniChannelFlow</outboundRouteType>
</outboundRouteConfigs>
```

Retrieve the bundle, add/update the block on the Messaging surface, redeploy. `outboundRouteName`
must equal the active outbound `RoutingFlow` API name (see #3).

## 3. Outbound QueueBased `RoutingFlow`

The bundled asset `assets/force-app/main/default/flows/Human_Escalation_Outbound_Flow.flow-meta.xml`
is a QueueBased outbound flow template that routes the escalated conversation to the human
queue. It looks the queue up by `DeveloperName` at runtime (no hardcoded Id), so it is
portable across orgs. Tokens `__FLOW_DEVELOPER_NAME__`, `__FLOW_LABEL__`,
`__QUEUE_DEVELOPER_NAME__`, `__SERVICE_CHANNEL_DEV_NAME__`, `__SERVICE_CHANNEL_LABEL__`
are substituted before deploy.

After deploy, `FlowDefinitionView.ActiveVersionId` for the flow must be non-null.

## 4. Human queue

The escalation target is a queue whose `QueueSobject` includes the routed context object
(`MessagingSession` by default, for Enhanced Chat / MIAW), plus a `QueueRoutingConfig`. See
[queue-resolution.md](../../service-agentforce-channel-configure/references/queue-resolution.md)
for the create-or-adopt recipe. Provision any broader routing infrastructure through an
approved Omni setup workflow before running this skill.

## Handoff to `service-agentforce-channel-configure`

Inbound transport (`sessionHandlerAsa` on the MessagingChannel, Branch A) and the outbound
`connection customer_web_client:` connection block on the agent are owned by
`service-agentforce-channel-configure`. This skill focuses on the escalation-specific
surfaces (#1, #2, #3, #4) and the threshold policy, delegating transport wiring to that skill.
