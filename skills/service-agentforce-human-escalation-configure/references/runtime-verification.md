# Runtime & manual verification checklist

The deterministic config surfaces are verified headlessly by `verify-and-configure.sh`
(see the JSON verdict). The conversational behaviour and context preservation **cannot be
driven headlessly** and must be confirmed with a live conversation (per the EC V2 reference).

## A. Deterministic config verdict (headless — done by the skill)

`verify-and-configure.sh` round-trips and asserts:

- `canEscalate=true` on the escalation topic (`GenAiPlugin`).
- `outboundRouteConfigs` on the `GenAiPlannerBundle` Messaging planner surface couples
  `outboundRouteName` (= the outbound flow API name) to `outboundRouteType=OmniChannelFlow`
  in the SAME block on a Messaging-class surface.
- Outbound `RoutingFlow` `ActiveVersionId` is non-null (`FlowDefinitionView`).
- The human queue exists with a `QueueSobject` for the context object (`MessagingSession`
  by default), a `QueueRoutingConfig` bound to the queue (`Group.QueueRoutingConfigId`), and
  **at least one active human member** (`GroupMember` resolving to an active `User`).
- The agent's latest `BotVersion` is `Active` after republish.

## B. Threshold policy (eval rubric — not a counter)

- ADK eval `TwoFailureThreshold`: on the 2nd consecutive failed attempt the agent escalates.
- ADK eval `PasswordResetOverride`: on the 1st failed password-reset attempt the agent escalates.

## C. Manual conversation test (runtime only)

1. Open the Enhanced Chat / MIAW deployment as an end user.
2. Ask the agent something it can resolve — confirm no premature escalation.
3. Trigger two consecutive failed attempts on the same request — confirm the agent emits
   the escalation message and hands off.
4. Confirm an `AgentWork` record is created against the human queue:

```bash
sf data query --target-org "$ORG" --json \
  --query "SELECT Id, Status, ServiceChannel, WorkItemId FROM AgentWork ORDER BY CreatedDate DESC LIMIT 5"
```

5. Confirm **context preservation**: the human agent receives the same `MessagingSession`
   with the full prior transcript (same `MessagingSession.Id`, not a new session).

```bash
sf data query --target-org "$ORG" --json \
  --query "SELECT Id, Status, Origin FROM MessagingSession ORDER BY LastModifiedDate DESC LIMIT 5"
```

Context preservation and `AgentWork` creation are runtime facts — record the result in the
run notes; they are not part of the headless verdict.

## D. Real-org proof record — 2026-08-17 (`sdb38` trial CDO)

Read-only §7 verification run against a non-production org (`IsSandbox=false`,
`TrialExpirationDate` non-null ⇒ `safe_to_write=true`). IDs abbreviated.

| Check | Result |
| --- | --- |
| Org safety | PASS — Enterprise trial CDO, non-production |
| Human queue + QRC bind | PASS — `General_IT_Queue`, `QueueRoutingConfigId=0K9…00BA` |
| `QueueSobject` context object | PASS — `MessagingSession` |
| Active human members | PASS — 2 active users |
| Outbound `RoutingFlow` active | PASS — `ActiveVersionId=301…pYBB` |
| Active MessagingChannels | PASS — 4 active |
| Queue-based routing runtime | PASS — `PendingServiceRouting` rows `IsReadyForRouting=true`, `RoutingType=QueueBased`; `AgentWork` rows `Closed`/`Declined` on `sfdc_livemessage`; `MessagingSession` rows `Ended`/`Waiting` |

**Not proven headlessly (manual step required):**

- Agent-authoring side (`canEscalate` + `outboundRouteConfigs` on a live Agentforce planner
  bundle) — the default agent developer name was absent on this org; running the authoring
  path requires an explicit `AGENT_DEVELOPER_NAME` (e.g. an Active `ExternalCopilot` agent).
- Phase 4 conversational escalation — must be driven through a live Enhanced Messaging
  conversation (section C). Queue-based routing→agent-accept is already demonstrated above,
  but the agent→human handoff trigger itself is a manual runtime confirmation.
