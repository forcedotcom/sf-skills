# Worked examples: `service-de-channel-routing-configure`

Reference runs:

- Queue path: reuse an existing queue (fast path) and create a new queue via the Metadata API (slow path). Both validated against test1.
- Flow path: attach an active Omni-Channel RoutingFlow with a fallback queue. Validated live against sdb6c 2026-08-12.
- ASA path: pick an existing live ASA with a fallback queue. Enumeration/selection validated against sdb14-test; the ASA `Type/AgentType` filter and routable-vs-not-live split re-verified live on sdb6c 2026-08-12.

---

## Worked example: reuse an existing Queue on test1

Verified by inspection on `messagingsdb6ccom.test1.my.pc-rnd.salesforce.com`, 2026-04-30. Input:

- `{CHANNEL_ID}` = `0MjSG000000Fc1l0AC` (the WhatsApp channel)

**Stage 1** read shows `SessionHandlerId = 00GSG0000000LSf2AM`, so this channel would short-circuit to the no-op path and report:

```json
{"ok": true, "noop": true, "sessionHandlerId": "00GSG0000000LSf2AM", "queueName": "Messaging Queue", "message": "Routing already configured"}
```

If the channel were freshly inserted with `SessionHandlerId = null`, the skill would:
- Stage 3: list existing queues (`Messaging Queue`, `MyQueue`, ...)
- User picks `Messaging Queue` → `{QUEUE_ID} = 00GSG0000000LSf2AM`
- Stage 5: PATCH
- Stage 6: verify
- Stage 7: report `Success — Routing configured — channel 0MjSG000000Fc1l0AC now routes to Queue 'Messaging Queue' (reused existing queue).`

## Worked example: create a new Queue

Input:
- `{CHANNEL_ID}` = `0MjSG000000NewChannel`
- User chooses "create new" with `Label="WhatsApp Demo Queue"`, `DevName="WhatsApp_Demo_Queue"`, `RoutingModel=MostAvailable`, `AddSelf=Y`

**Stages 1–3**: channel has null routing, user picks "create new".

**Stage 4**: skill writes to `/tmp/ccr-metadata-<ts>/`:
- `force-app/main/default/queues/WhatsApp_Demo_Queue.queue-meta.xml`
- `force-app/main/default/queueRoutingConfigs/WhatsApp_Demo_Queue_Routing.queueRoutingConfig-meta.xml`
- `sfdx-project.json`

`sf project deploy start` succeeds. Re-query returns `{Id: '00GSG00000NewQueue01'}`.

GroupMember insert adds the current user to the queue.

**Stage 5**: PATCH `MessagingChannel.SessionHandlerId = 00GSG00000NewQueue01`.

**Stage 6**: verify.

**Stage 7**: `Success — Routing configured — channel 0MjSG000000NewChannel now routes to Queue 'WhatsApp Demo Queue'.`

---

## Worked example: attach an Omni-Channel Flow (verified live on sdb6c)

Verified live on `messaging_sdb6c` 2026-08-12. Input:

- `{CHANNEL_ID}` = `0MjSG0000004rIf0AI` (Enhanced channel `Customer_Support`, `SessionHandlerId = null`)

**Stage 1**: read shows `SessionHandlerId = null, FallbackQueueId = null`. Continue.

**Stage 2**: `PlatformType = Enhanced` confirmed. User picks `2) flow`.

**Locate (references/target-locate.md)** — active, org-local RoutingFlows:

```soql
SELECT DurableId, Label, ApiName, NamespacePrefix, IsActive, ActiveVersionId
FROM FlowDefinitionView
WHERE ProcessType = 'RoutingFlow' AND IsActive = true AND NamespacePrefix = null
ORDER BY Label
```

Returns org-local flows whose `DurableId` is the `300` FlowDefinition Id (e.g. `DirectToAgentFlow` → `300SG0000002gw1YAA`). User picks it → `{TARGET_ID} = 300SG0000002gw1YAA`.

**Resolve FallbackQueue** (required for Flow): eligible-queue query returns `Messaging_Queue` (`00GSG0000000LSf2AM`). User picks it → `{FALLBACK_QUEUE_ID} = 00GSG0000000LSf2AM`.

**Stage 5**: single PATCH writing both fields:

```bash
$ sf data update record --sobject MessagingChannel --record-id 0MjSG0000004rIf0AI \
    --values 'SessionHandlerId=300SG0000002gw1YAA FallbackQueueId=00GSG0000000LSf2AM'
# → success
```

(A PATCH that sets the Flow SessionHandler but leaves FallbackQueue null is rejected server-side: *"A Fallback Queue must be specified when selecting a Flow routing method."* — observed live.)

**Stage 6**: re-read returns `SessionHandlerId = 300SG0000002gw1YAA, FallbackQueueId = 00GSG0000000LSf2AM`. Verified.

**Stage 7**:

```json
{"ok": true, "routingType": "flow", "sessionHandlerId": "300SG0000002gw1YAA",
 "fallbackQueueId": "00GSG0000000LSf2AM", "flowName": "DirectToAgentFlow",
 "flowDeveloperName": "DirectToAgentFlow", "created": false}
```

User-facing: `Success — Routing configured — channel 0MjSG0000004rIf0AI now routes to Omni-Flow 'DirectToAgentFlow' (300SG0000002gw1YAA), fallback Queue 00GSG0000000LSf2AM.`

*(The test channel was restored to `SessionHandlerId=null, FallbackQueueId=null` afterward.)*

---

## Worked example: pick an existing live ASA on sdb14-test

Verified on `sdb14com-a8.test2.my.pc-rnd.salesforce.com` (`sdb14-test`), 2026-05-12. The fast path: an Agentforce-licensed org has ASAs already authored and we just need to attach one. Input:

- `{CHANNEL_ID}` = `0MjRZ00000004210AA` (a freshly-inserted WhatsApp channel)

**Stage 1**: channel has `SessionHandlerId = null, FallbackQueueId = null`. Continue.

**Stage 2**: user picks `2) asa`.

**Stage 3-ASA.0** precondition check:
```bash
$ sf sobject describe --target-org sdb14-test --sobject BotDefinition 2>&1 | grep -q "does not exist" && echo MISSING || echo PRESENT
PRESENT
```
Continue.

**Stage 3-ASA.1** enumerate active ASAs (one query, child-relationship form works on this org):

```soql
SELECT Id, DeveloperName, MasterLabel, BotUserId,
       (SELECT Id, Status FROM BotVersions WHERE Status='Active' LIMIT 1)
FROM BotDefinition
WHERE Type='ExternalCopilot' AND AgentType='EinsteinServiceAgent'
ORDER BY MasterLabel
```

Returns 25 rows. After post-processing (filter rows where `BotUserId != null` AND `BotVersions[0].Status == 'Active'`), 13 are routable.

**Stage 3-ASA.2** prompt:

```text
Existing Agentforce Service Agents on sdb14-test:

  1) Agentforce Service Agent KAFile (Agentforce_Service_Agent_KAFile) — 0XxRZ0000002ZWL0A2 [live]
  2) Agentforce Service Agent Test (Agentforce_Service_Agent_Test) — 0XxRZ0000002kJh0AI [live]
  3) BYO Service Agent (BYO_Service_Agent) — 0XxRZ0000002lAv0AI [live]
  4) MON ASA Apex (MON_ASA_Apex) — 0XxRZ0000003APR0A2 [live]
  ...

Pick [1-13]: 4
```

Records: `{ASA_ID} = 0XxRZ0000003APR0A2`, `{ASA_LABEL} = "MON ASA Apex"`, `{ASA_DEV_NAME} = "MON_ASA_Apex"`, `{BOT_USER_ID} = 005RZ000001wJ3JYAU`, `{BOT_VERSION_ID} = 0X9RZ0000002b8L0AQ`.

**Stage 3-ASA.3** resolve FallbackQueue (required for ASA): eligible-queue query returns a MessagingSession queue; user picks it → `{FALLBACK_QUEUE_ID} = 00GRZ0000000abc0AA`.

**Stage 5**: single PATCH writing both fields — `sf data update record --sobject MessagingChannel --record-id 0MjRZ00000004210AA --values 'SessionHandlerId=0XxRZ0000003APR0A2 FallbackQueueId=00GRZ0000000abc0AA'` succeeds. (Omitting the FallbackQueue would be rejected with `MissingFallbackQueueForAsaRouting`.)

**Stage 6**: re-read returns `SessionHandlerId = 0XxRZ0000003APR0A2, FallbackQueueId = 00GRZ0000000abc0AA`. Verified.

**Stage 7**:

```json
{
  "ok": true,
  "routingType": "asa",
  "sessionHandlerId": "0XxRZ0000003APR0A2",
  "fallbackQueueId": "00GRZ0000000abc0AA",
  "asaName": "MON ASA Apex",
  "asaDeveloperName": "MON_ASA_Apex",
  "botUserId": "005RZ000001wJ3JYAU",
  "botVersionId": "0X9RZ0000002b8L0AQ",
  "created": false
}
```

User-facing: `Success — Routing configured — channel 0MjRZ00000004210AA now routes to Agentforce Service Agent 'MON ASA Apex' (0XxRZ0000003APR0A2), fallback Queue 00GRZ0000000abc0AA. Bot user: 005RZ000001wJ3JYAU. Active version: 0X9RZ0000002b8L0AQ.`

Total elapsed: ~3s (SOQL + PATCH, no external callouts needed).

