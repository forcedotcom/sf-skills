# Queue resolution

Run this before any channel wiring. The fallback queue must exist and have the correct `QueueSobject` record for the channel type's SobjectType.

## Step 1 — Query existing compatible queues

Determine the SobjectType from the channel type (see `references/channel-types.md`), then query:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Queue.Name, Queue.DeveloperName, Queue.Id
           FROM QueueSobject
           WHERE SobjectType='{SOBJECT_TYPE}'"
```

## Step 2 — Present to user via AskUserQuestion

- **One or more found** → present each as an option: `{Queue.Name} ({Queue.DeveloperName})`, plus a final option *"Create a new queue"*. If the user picks an existing queue, capture its `DeveloperName` and `Id` and skip queue creation.
- **Zero found** → inform the user no compatible queue exists; proceed directly to create one.

## Step 3 — Create a new queue (if needed)

**Naming:** `{ChannelTypeLabel} Queue` / DeveloperName `{Channel_Type_Label}_Queue`

Examples:
- Voice → `Voice Queue` / `Voice_Queue`
- Enhanced Chat → `Enhanced Chat Queue` / `Enhanced_Chat_Queue`
- Email → `Email Queue` / `Email_Queue`

### 1. Create the Group record
```bash
QUEUE_ID=$(sf data create record --target-org $ORG \
  --sobject Group \
  --values "Type='Queue' Name='{QUEUE_NAME}' DeveloperName='{QUEUE_DEVELOPER_NAME}'" \
  --json | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['id'])")
```

### 2. Grant queue access to the correct SobjectType
```bash
sf data create record --target-org $ORG \
  --sobject QueueSobject \
  --values "QueueId='$QUEUE_ID' SobjectType='{SOBJECT_TYPE}'"
```

### 3. Add the running user as a queue member
```bash
ORG_USERNAME=$(sf org display --target-org $ORG --json \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['username'])")
RUNNING_USER_ID=$(sf data query --target-org $ORG --json \
  --query "SELECT Id FROM User WHERE Username='$ORG_USERNAME'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
sf data create record --target-org $ORG \
  --sobject GroupMember \
  --values "GroupId='$QUEUE_ID' UserOrGroupId='$RUNNING_USER_ID'"
```

## Step 4 — Resolve or create a Routing Configuration

The queue must have a `QueueRoutingConfig` so Omni-Channel knows how to handle capacity. `QueueRoutingConfig` has **no `QueueId` column** — the link is the reverse direction (the queue's `Group` record points at the config via `QueueRoutingConfigId`), so resolve an existing config through the `Group` record, not by filtering the config on a queue Id:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT QueueRoutingConfigId FROM Group WHERE Id='{QUEUE_ID}'"
```

- **`QueueRoutingConfigId` is non-null** → the queue already has a routing config; use it as-is and skip creation.
- **`QueueRoutingConfigId` is null** → create one using the capacity percentage for the channel type, then link it to the queue:

| Channel type | `CapacityPercentage` |
|---|---|
| Enhanced Chat / Enhanced Messaging | `50` |
| Voice | `100` |
| Email-to-Case | `25` |

All use `RoutingModel: LeastActive`.

`QueueRoutingConfig` uses `MasterLabel` (there is **no `Name` field**), has **no `QueueId`**, and **requires `RoutingPriority`** — a non-nillable integer with no default; set `1`. Create the config standalone, capture its Id, then point the queue's `Group` record at it:

```bash
QRC_ID=$(sf data create record --target-org $ORG \
  --sobject QueueRoutingConfig \
  --values "MasterLabel='{QUEUE_NAME} Routing' DeveloperName='{QUEUE_DEVELOPER_NAME}_Routing' CapacityPercentage={CAPACITY_PERCENTAGE} RoutingModel='LeastActive' RoutingPriority=1 IsAttributeBased=false" \
  --json | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['id'])")

# Link is the REVERSE direction — the queue's Group record points at the config:
sf data update record --target-org $ORG \
  --sobject Group --record-id "{QUEUE_ID}" \
  --values "QueueRoutingConfigId='$QRC_ID'"
```

Verify the queue now references the config:
```bash
sf data query --target-org $ORG --json \
  --query "SELECT Id, QueueRoutingConfigId FROM Group WHERE Id='{QUEUE_ID}'"
```
`QueueRoutingConfigId` must be non-null.

## Step 5 — Capture for use in Phase 2

Store:
- `QUEUE_DEVELOPER_NAME` — used in the MessagingChannel XML (Branch A) or RoutingFlow `queueId` lookup (Branches B/C)
- `QUEUE_NAME` (the `Name` field, e.g. `Voice Queue`) — used as `queueLabel` in the RoutingFlow XML
- `QUEUE_ID` (18-char record Id) — used as `queueId` in the RoutingFlow XML

If an existing queue was chosen, query its Id if not already available:
```bash
QUEUE_ID=$(sf data query --target-org $ORG --json \
  --query "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='{QUEUE_DEVELOPER_NAME}'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
```

---

## Step 6 — Escalation queue resolution (Phase 3 only)

Run this step when the user opts into outbound escalation (Branches A/B). The escalation queue is the human queue that receives escalated conversations — it may be the same as the inbound fallback queue, or a different one.

### Check whether other compatible queues exist

Query for queues with the correct SobjectType, excluding the inbound fallback queue already selected:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT Queue.Name, Queue.DeveloperName, Queue.Id
           FROM QueueSobject
           WHERE SobjectType='{SOBJECT_TYPE}'
           AND Queue.DeveloperName != '{QUEUE_DEVELOPER_NAME}'"
```

### Branch on results

**Zero other queues exist** → no choice to offer; reuse the inbound fallback queue. Set `ESCALATION_QUEUE_DEVELOPER_NAME = QUEUE_DEVELOPER_NAME` and `ESCALATION_QUEUE_ID = QUEUE_ID`. Continue without asking.

**One or more other queues exist** → ask the user via `AskUserQuestion`:

> *"Which queue should receive escalated conversations from the agent?"*
> - *Use the same queue as inbound fallback: `{QUEUE_NAME}` ({QUEUE_DEVELOPER_NAME})* **(Recommended)**
> - *{OtherQueue.Name} ({OtherQueue.DeveloperName})* — one option per additional compatible queue

If the user picks the fallback: `ESCALATION_QUEUE_DEVELOPER_NAME = QUEUE_DEVELOPER_NAME`, `ESCALATION_QUEUE_ID = QUEUE_ID`.

If the user picks a different queue: capture its `DeveloperName` and `Id` as `ESCALATION_QUEUE_DEVELOPER_NAME` and `ESCALATION_QUEUE_ID`.

Use `ESCALATION_QUEUE_DEVELOPER_NAME` (not `QUEUE_DEVELOPER_NAME`) when writing the outbound RoutingFlow XML in Phase 3.
