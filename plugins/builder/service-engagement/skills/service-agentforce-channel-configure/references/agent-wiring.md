# Agent wiring — outbound escalation (optional)

This step is optional and presented to the user after inbound routing is complete. It configures the agent to hand off to a human agent via outbound escalation.

> **Scope note:** This is distinct from inbound routing (which routes incoming work items *to* the agent). Outbound escalation adds a `connection {type}:` block to the agent's `.agent` YAML so the agent can transfer a conversation *to a queue* when the customer requests a human. The outbound routing flow used here is a different flow from the inbound one created in Phase 2.

## Connection block by channel type

The connection block name depends on the channel type being wired:

| Channel type | Connection block | `outbound_route_type` |
|---|---|---|
| Enhanced Chat (EmbeddedMessaging) | `connection customer_web_client:` | `OmniChannelFlow` |
| Enhanced Messaging (3rd-party) | `connection messaging:` | `OmniChannelFlow` |
| Voice | `connection telephony:` | `OmniChannelFlow` |
| Email-to-Case | `connection service_email:` | `OmniChannelFlow` |

## Prerequisite

An outbound RoutingFlow (`routingType: QueueBased`, routes to the fallback queue) must already exist. If one doesn't exist, create it using the QueueBased template in `references/routing-flow.md` Part 2 before proceeding here.

Verify the outbound flow exists:
```bash
sf data query --target-org $ORG --json \
  --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ProcessType='RoutingFlow' AND ApiName='{OUTBOUND_FLOW_DEVELOPER_NAME}'"
```
`ActiveVersionId` must be non-null.

## Add the connection block to the agent

Retrieve the agent's authoring bundle:
```bash
sf project retrieve start \
  --metadata "GenAiPlannerBundle:{AGENT_DEVELOPER_NAME}" \
  --target-org $ORG
```

Add the appropriate block to the agent's `.agent` YAML. For **Enhanced Chat** (`connection customer_web_client:`):

```yaml
connection customer_web_client:
    outbound_route_type: "OmniChannelFlow"
    outbound_route_name: "flow://{OUTBOUND_FLOW_DEVELOPER_NAME}"
    escalation_message: "Transferring you to a live agent — please hold on a moment."
    adaptive_response_allowed: True
```

For **Enhanced Messaging** (`connection messaging:`):

```yaml
connection messaging:
    outbound_route_type: "OmniChannelFlow"
    outbound_route_name: "flow://{OUTBOUND_FLOW_DEVELOPER_NAME}"
    escalation_message: "Transferring you to a live agent — please hold on a moment."
    adaptive_response_allowed: True
```

For **Voice** (`connection telephony:` + `modality voice:`):

Voice requires two blocks. Add both if they are not already present:

```yaml
modality voice:
    voice_id: "UgBBYS2sOqTuMpoF3BR0"
    outbound_speed: 1.0
    outbound_stability: 0.65
    outbound_similarity: 0.75

connection telephony:
    outbound_route_type: "OmniChannelFlow"
    outbound_route_name: "flow://{OUTBOUND_FLOW_DEVELOPER_NAME}"
    escalation_message: "Finding an associate for you..."
    adaptive_response_allowed: True
```

For **Email-to-Case** (`connection service_email:`):

```yaml
connection service_email:
    outbound_route_type: "OmniChannelFlow"
    outbound_route_name: "flow://{OUTBOUND_FLOW_DEVELOPER_NAME}"
    adaptive_response_allowed: True
```

If a block for the relevant connection type already exists in the file, **add the outbound fields to the existing block** rather than creating a duplicate. Do not overwrite fields that are already present. If `modality voice:` already exists, leave it as-is — do not overwrite existing voice tuning values.

## Republish and activate the agent

```bash
sf agent validate authoring-bundle --api-name {AGENT_DEVELOPER_NAME} --json
sf agent publish  authoring-bundle --api-name {AGENT_DEVELOPER_NAME} --json
echo "Y" | sf agent activate       --api-name {AGENT_DEVELOPER_NAME} --json
```

## Verify the wiring round-tripped

After publish, retrieve the bundle and check:
```bash
grep -n "outboundRouteName\|outboundRouteType" \
  force-app/main/default/genAiPlannerBundles/{AGENT_DEVELOPER_NAME}_v*/\*.genAiPlannerBundle
```

Both `outboundRouteName` and `outboundRouteType` must be present in the correct `<plannerSurfaces>` entry. The compiled XML maps the connection blocks as:
- `connection customer_web_client:` → `<surfaceType>CustomerWebClient</surfaceType>`
- `connection messaging:` → `<surfaceType>Messaging</surfaceType>`
- `connection service_email:` → `<surfaceType>ServiceEmail</surfaceType>`

If absent, the connection block was not serialised correctly — re-retrieve the `.agent` file and confirm the YAML was written before publishing.

> **AiAuthoringBundle / Email-to-Case caveat (`connection service_email:`).** For an agent authored as an **AiAuthoringBundle** — the `ExternalCopilot` Agentforce Service Agent used by Email-to-Case (Branch C) — `sf project retrieve start --metadata "GenAiPlannerBundle:{AGENT_DEVELOPER_NAME}"` can report `files: 1` yet write **nothing** under `genAiPlannerBundles/`. With no compiled file to grep, the command above returns empty — a **false negative**, not a wiring failure. Do not conclude the surface is missing. Verify instead by:
> - **Grepping the `AiAuthoringBundle` source** (the source of truth), which retains the block through publish:
>   ```bash
>   sf project retrieve start --metadata "AiAuthoringBundle:{AGENT_DEVELOPER_NAME}" --target-org $ORG
>   grep -n "connection service_email:" \
>     force-app/main/default/aiAuthoringBundles/{AGENT_DEVELOPER_NAME}/{AGENT_DEVELOPER_NAME}.agent
>   ```
> - **Treating the `BotEmailDefinition` deploy as the definitive `ServiceEmail`-surface check.** Its save-time validation fires `SurfaceMissingForSave` **last**, so a successful `Created` deploy (Branch C, Step 4c) proves the surface is live on the active version — authoritative over the empty GenAiPlannerBundle grep.
