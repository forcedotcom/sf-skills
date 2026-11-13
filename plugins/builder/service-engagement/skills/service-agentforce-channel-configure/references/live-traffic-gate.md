# Live-traffic warning gate (Phase 2)

Runs once per Phase 2, before the first step that changes routing: at the start of Branch A or B, and in Branch C right after the Step 1 address choice, since whether routing is live depends on which address is chosen (Steps 0–1 bind nothing to the agent). Prevents an unattended re-route of live traffic on a channel that already has active inbound routing.

## Detect existing routing

- **Branch A (Enhanced Chat / Enhanced Messaging):** retrieve the MessagingChannel and inspect `SessionHandlerType`. If it is non-empty, routing is live.
- **Branch B (Voice):** routing is live if the `PstnVoice` MessagingChannel already has a non-null `SessionHandlerId`, or if `FlowDefinitionView WHERE ProcessType='RoutingFlow'` shows a flow assigned to this service channel with a non-null `ActiveVersionId`.
- **Branch C (Email-to-Case):** run this check after the Step 1 address choice in `channel-branch-email.md`. An **existing** routing address chosen there is live: it already turns inbound email into cases, so changing its BotEmailDefinition, owner, or flow re-routes them. A **new** address created in Step 1 is not live.

If the channel has no existing routing, skip this gate entirely and proceed directly to the branch.

## Infer from the user's prompt before asking

Before raising `AskUserQuestion`, re-read the user's original prompt. If it already resolves the timing choice unambiguously, honor it silently — do NOT ask.

- **Defer intent already stated** — treat as if the user picked **"Set up, then wire manually"**. Set `DEFER_INBOUND_ROUTING=true` and proceed to the deferred path (below) without raising the question. Non-exhaustive trigger phrases: "do not cut over", "don't cut over", "do not cut live traffic over", "don't switch live traffic yet", "wire manually", "wire it manually when I'm ready", "review first", "let me review", "hold off on activating", "set up but don't activate", "prepare but don't route", "leave live traffic alone".
- **Cutover intent already stated** — treat as if the user picked **"Re-route now"**. Leave `DEFER_INBOUND_ROUTING` unset and proceed with immediate re-routing without raising the question. Non-exhaustive trigger phrases: "go ahead and cut over now", "re-route immediately", "cut over now", "switch live traffic now", "activate immediately", "just do it now".

Only fall through to `AskUserQuestion` when the prompt is silent or genuinely ambiguous about timing.

## If existing routing detected and prompt is silent, ask

```yaml
AskUserQuestion:
  question: "'{CHANNEL_MASTER_LABEL}' already has active inbound routing configured.
             Deploying will re-route live traffic immediately — any in-progress
             conversations or calls on this channel will be affected.
             How would you like to proceed?"
  header: "Live traffic"
  options:
    - label: "Re-route now"
      description: "Deploy immediately. Live traffic will be affected."
    - label: "Set up, then wire manually"
      description: "Create the queue and RoutingFlow (Voice/Email) now, but skip activating
                   inbound routing. Manual wiring instructions will be provided at the end."
```

### Safe default on ambiguous / no-selection response

If `AskUserQuestion` returns without a clear selection — timeout, empty answer, unrecognized reply, or any headless-run auto-resolution — default to **"Set up, then wire manually"** (set `DEFER_INBOUND_ROUTING=true`). Never default to a live re-route: the deferred path is non-destructive and recoverable; an unintended cutover is not.

## If the user chooses "Set up, then wire manually"

Set `DEFER_INBOUND_ROUTING=true` and continue. Steps that create new, unbound components still run; every step that points the live channel or routing address at the agent is skipped:

- **Branch A:** create the queue normally. Skip Steps 3–5: (1) the `sf project deploy start` for the MessagingChannel, (2) the Data API PATCH that binds `SessionHandlerId`/`FallbackQueueId` on the channel, and (3) the verify that expects them set.
- **Branch B:** create the queue and write + deploy the RoutingFlow normally (the flow is safe to deploy — it only becomes live when assigned to the channel). Skip `channel-branch-voice.md` Step 4, the MessagingChannel deploy that assigns the flow to the channel.
- **Branch C:** create the queue, write + deploy the RoutingFlow (Omni-Channel path), and deploy the BotEmailDefinition (Step 4c) normally; none takes effect until a routing address references it. Skip: (1) the Step 4d Settings:Case metadata deploy that binds `botEmailDefinition`, `caseOwner`, or `routingFlow` on the routing address, and (2) any direct Tooling API PATCH that sets those fields on the target address.

After Phase 2 completes, if `DEFER_INBOUND_ROUTING=true`, print manual wiring instructions before the Phase 3 prompt.

### Branch A — activate when ready

`sessionHandlerAsa` is not accepted by the Metadata API at v67 — deploy `sessionHandlerType` + `sessionHandlerQueue` only, then bind the bot via a Data API PATCH. The bot must be Active before the PATCH ("Only active Agentforce Service Agents are supported" otherwise).

```bash
sf project retrieve start --metadata "MessagingChannel:{CHANNEL_DEVELOPER_NAME}" --target-org {ORG}
# In the retrieved XML, set ONLY:
#   <sessionHandlerType>AgentforceServiceAgent</sessionHandlerType>
#   <sessionHandlerQueue>{QUEUE_DEVELOPER_NAME}</sessionHandlerQueue>
# Do NOT add <sessionHandlerAsa> — the Metadata API silently rejects it at v67.
sf project deploy start --metadata "MessagingChannel:{CHANNEL_DEVELOPER_NAME}" --target-org {ORG}

# Resolve Ids, then bind the bot via Data API PATCH:
CHAN_ID=$(sf data query -o {ORG} --json \
  -q "SELECT Id FROM MessagingChannel WHERE DeveloperName='{CHANNEL_DEVELOPER_NAME}'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
BOT_ID=$(sf data query -o {ORG} --json \
  -q "SELECT Id FROM BotDefinition WHERE DeveloperName='{AGENT_DEVELOPER_NAME}'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
QUEUE_ID=$(sf data query -o {ORG} --json \
  -q "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='{QUEUE_DEVELOPER_NAME}'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")

sf api request rest --method PATCH -o {ORG} \
  "/services/data/v67.0/sobjects/MessagingChannel/${CHAN_ID}" \
  --body "{\"SessionHandlerId\":\"${BOT_ID}\",\"FallbackQueueId\":\"${QUEUE_ID}\"}"
# Expected: HTTP 204

# Verify — both must be non-null:
sf data query -o {ORG} --json \
  -q "SELECT SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE Id='${CHAN_ID}'"
```

### Branch B — activate when ready

> The RoutingFlow `{FLOW_DEVELOPER_NAME}` is deployed and active. To assign it as the inbound routing flow, run `channel-branch-voice.md` Step 4 (the MessagingChannel deploy that sets `sessionHandlerFlow`) — or re-run this skill against the same channel; the existing flow will be detected and reused, and only the channel assignment step will run.

### Branch C — activate when ready

> The BotEmailDefinition `{BOT_EMAIL_DEFINITION_NAME}` (and, on the Omni-Channel path, the RoutingFlow `{INBOUND_FLOW_DEVELOPER_NAME}`) is deployed but not yet bound to `{SUPPORT_EMAIL}`. To cut over, run `channel-branch-email.md` Step 4d against that address. Re-read CaseSettings first, because addresses may have changed since setup, and carry every other address over exactly as read.
