# Live-traffic warning gate (Phase 2)

Runs once, before any branch, whenever Phase 2 begins. Prevents an unattended re-route of live traffic on a channel that already has active inbound routing.

## Detect existing routing

- **Branch A (Enhanced Chat / Enhanced Messaging):** retrieve the MessagingChannel and inspect `SessionHandlerType`. If it is non-empty, routing is live.
- **Branches B/C (Voice / Email-to-Case):** query `FlowDefinitionView WHERE ProcessType='RoutingFlow'` for any flow assigned to this service channel with a non-null `ActiveVersionId`.

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

Set `DEFER_INBOUND_ROUTING=true` and continue:

- **Branch A:** create the queue normally. Skip the `sf project deploy start` for the MessagingChannel entirely.
- **Branches B/C:** create the queue and write + deploy the RoutingFlow normally (the flow is safe to deploy — it only becomes live when assigned to the channel). Skip any step that assigns the flow as the active routing flow for the channel.

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

### Branches B/C — activate when ready

> The RoutingFlow `{FLOW_DEVELOPER_NAME}` is deployed and active. To assign it as the inbound routing flow, go to **Setup → Omni-Channel → Service Channels** and point the channel at this flow — or re-run this skill against the same channel; the existing flow will be detected and reused, and only the channel assignment step will run.
