---
name: service-de-channel-routing-configure-asa-routing
description: "Load when the user picked Agentforce Service Agent (ASA) routing on service-de-channel-routing-configure. Covers the BotDefinition precondition check, enumerating live ASAs (with the routable-vs-not-yet-live filter and the INVALID_TYPE subquery fallback), and prompting the user to pick one. DO NOT load this for the Omni-Channel Queue routing path — see references/queue-creation.md for that."
metadata:
  version: "1.0"
  related-skills: service-de-channel-routing-configure
---

# Stage 3-ASA: Pick an existing ASA

*(This stage runs only on the ASA path. Queue path: skip to Stage 5.)*

## Stage 3-ASA.0: Precondition check

Verify the org has Agentforce licensed (`BotDefinition` sObject exists):

```bash
sf sobject describe --target-org '{ORG_ALIAS}' --sobject BotDefinition 2>&1 | grep -q "does not exist" \
  && echo "MISSING" \
  || echo "PRESENT"
```

If `MISSING` — emit and return:

```json
{"ok": false, "kind": "asa-not-supported", "hint": "this org doesn't have BotDefinition (Agentforce not licensed); use Queue routing instead"}
```

## Stage 3-ASA.1: Enumerate live ASAs

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MasterLabel, BotUserId, (SELECT Id, Status FROM BotVersions WHERE Status='Active' LIMIT 1) FROM BotDefinition WHERE Type='ExternalCopilot' AND AgentType='EinsteinServiceAgent' ORDER BY MasterLabel" \
  --json > /tmp/ccr-asas.json
```

Parse with `node -e`. For each row, extract:
- `Id` — `BotDefinition.Id` (used as `SessionHandlerId`)
- `MasterLabel` / `DeveloperName` — for display
- `BotUserId` — bot user already linked? (null = not linked, ASA can't actually serve sessions yet)
- `BotVersions[0]` — has an Active version? (null = ASA exists but isn't live)

Filter: an ASA is **routable** only if `BotUserId != null` AND `BotVersions[0].Status == 'Active'`. ASAs failing either check are listed but flagged as "not yet live — selecting will fail at activation time."

If the channel-relationship subquery returns `INVALID_TYPE` (the `BotVersions` child relationship isn't named on some orgs — same family of issue as the MessagingChannelUsage subquery gotcha), fall back to two queries:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MasterLabel, BotUserId FROM BotDefinition WHERE Type='ExternalCopilot' AND AgentType='EinsteinServiceAgent' ORDER BY MasterLabel" \
  --json > /tmp/ccr-asas.json
# then for each id, query BotVersion separately
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, BotDefinitionId, Status FROM BotVersion WHERE BotDefinitionId IN (<comma-sep ids>) AND Status='Active'" \
  --json > /tmp/ccr-asas-versions.json
```

If no live ASAs found (all rows have `BotUserId=null` or no Active BotVersion), emit:

```json
{"ok": false, "kind": "no-live-asa", "hint": "no live ASAs found on this org — create one in Setup → Agentforce first, then re-run this skill"}
```

## Stage 3-ASA.2: Prompt the user

Present a numbered list of live ASAs only:

```text
Existing live Agentforce Service Agents on {ORG_ALIAS}:

  1) Agentforce Service Agent KAFile (Agentforce_Service_Agent_KAFile) — 0XxRZ0000002ZWL0A2
  2) MON ASA Apex (MON_ASA_Apex) — 0XxRZ0000003APR0A2

Pick [1-N]:
```

Record `{ASA_ID}` = `BotDefinition.Id`, `{ASA_LABEL}`, `{ASA_DEV_NAME}`, `{BOT_USER_ID}`, `{BOT_VERSION_ID}`.

## Stage 3-ASA.3: Resolve a FallbackQueue (required)

ASA routing **requires a FallbackQueue** — `validateSessionHandler` rejects a null FallbackQueue on the `0Xx` SessionHandler path with `MissingFallbackQueueForAsaRouting`. Enumerate eligible queues (Omni-enabled, MessagingSession-capable) and let the user pick:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, Name, DeveloperName FROM Group WHERE Type = 'Queue' AND QueueRoutingConfigId != null AND Id IN (SELECT QueueId FROM QueueSobject WHERE SobjectType = 'MessagingSession') ORDER BY Name" \
  --json > /tmp/ccr-fallback-queues.json
```

Record `{FALLBACK_QUEUE_ID}` = the chosen `00G` `Group.Id`. If 0 rows, emit `{ok:false, kind:"no-fallback-queue", hint:"ASA routing needs a fallback queue but no MessagingSession-capable queue exists — create one (queue path) first"}` and return.

Continue to Stage 5 (PATCH), which writes `SessionHandlerId={ASA_ID} FallbackQueueId={FALLBACK_QUEUE_ID}` in one call.
