---
name: service-de-channel-routing-configure-queue-creation
description: "Load when the user picked 'create a new queue' on the Queue routing path of service-de-channel-routing-configure. Covers the full Metadata API creation flow: collecting queue inputs, scaffolding a minimal sfdx project with Queue + QueueRoutingConfig metadata, deploying it, looking up the new Queue's Id, and optionally adding the current user as a member. DO NOT load this when the user picked an existing queue from the enumerated list — that path skips straight to Stage 5 (PATCH)."
metadata:
  version: "1.0"
  related-skills: service-de-channel-routing-configure
---

# Stage 3-Queue, continued: Create a new Queue via Metadata API

*(Continuation of the Queue path. Skip if the user picked an existing queue above.)*

We deploy a Queue + QueueRoutingConfig pair using a minimal scratch sfdx project. This mirrors the `help-agent-accelerator` pattern (`force-app-static/main/default/queues/Help_Support_Queue.queue-meta.xml`), which is the battle-tested route for MessagingSession queues.

## Stage 3-Queue.1: Collect inputs

Ask the user:

```text
New queue details:
  Display name (e.g. "WhatsApp Support Queue"):
  API name (DeveloperName, letters/digits/underscores, e.g. "WhatsApp_Support_Queue")
    [press enter to derive from display name]:
  Routing model [MostAvailable / LeastActive / HighestPriority] (default: MostAvailable):
  Add the current user as a queue member? [Y/n]:
```

Derive `DeveloperName` by slugifying the display name if the user leaves it blank:
- Replace any non-alphanumeric run with `_`
- Collapse repeats: `__` → `_`
- Trim leading/trailing `_`
- If the result starts with a digit, prepend `X_`

Validate `DeveloperName`: must match `^[A-Za-z][A-Za-z0-9_]*$`, length ≤ 40. If invalid, re-prompt.

Record:
- `{QUEUE_LABEL}` — display name
- `{QUEUE_DEV_NAME}` — DeveloperName
- `{ROUTING_MODEL}` — `MostAvailable` | `LeastActive` | `HighestPriority` (maps to `QueueRoutingConfig.routingModel`)
- `{ADD_SELF}` — boolean

## Stage 3-Queue.2: Write the sfdx project

```bash
TMP_DIR=/tmp/ccr-metadata-$(date +%s)
mkdir -p "$TMP_DIR/force-app/main/default/queues"
mkdir -p "$TMP_DIR/force-app/main/default/queueRoutingConfigs"

# sfdx-project.json
cat > "$TMP_DIR/sfdx-project.json" <<'JSON_EOF'
{
  "packageDirectories": [{"path": "force-app", "default": true}],
  "namespace": "",
  "sourceApiVersion": "66.0"
}
JSON_EOF

# QueueRoutingConfig — named <DevName>_Routing so one config per queue
cat > "$TMP_DIR/force-app/main/default/queueRoutingConfigs/{QUEUE_DEV_NAME}_Routing.queueRoutingConfig-meta.xml" <<'XML_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<QueueRoutingConfig xmlns="http://soap.sforce.com/2006/04/metadata">
    <capacityType>INHERITED</capacityType>
    <capacityWeight>1.0</capacityWeight>
    <isAttributeBased>false</isAttributeBased>
    <label>{QUEUE_LABEL} Routing</label>
    <routingModel>{ROUTING_MODEL}</routingModel>
    <routingPriority>1</routingPriority>
</QueueRoutingConfig>
XML_EOF

# Queue
cat > "$TMP_DIR/force-app/main/default/queues/{QUEUE_DEV_NAME}.queue-meta.xml" <<'XML_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Queue xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesSendEmailToMembers>false</doesSendEmailToMembers>
    <name>{QUEUE_LABEL}</name>
    <queueRoutingConfig>{QUEUE_DEV_NAME}_Routing</queueRoutingConfig>
    <queueSobject>
        <sobjectType>MessagingSession</sobjectType>
    </queueSobject>
</Queue>
XML_EOF
```

**Substitute** `{QUEUE_LABEL}`, `{QUEUE_DEV_NAME}`, `{ROUTING_MODEL}` into both files. Use `sed` or a Node script — watch the XML escape if the label contains `&`, `<`, `>`, `"`, `'`.

## Stage 3-Queue.3: Deploy

```bash
(cd "$TMP_DIR" && sf project deploy start --target-org '{ORG_ALIAS}' --wait 5 --json) > /tmp/ccr-deploy.json 2>&1
```

Parse `/tmp/ccr-deploy.json`:
- `result.status === "Succeeded"` → continue
- anything else → emit `{ok:false, kind:"metadata-deploy-failed", message:<result.details.componentFailures[0].problem || raw tail>}` and return

## Stage 3-Queue.4: Look up the new Queue's ID

The deploy returns component results but not the Group sObject id. Query it:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='{QUEUE_DEV_NAME}' LIMIT 1" \
  --json
```

Record the Id as `{QUEUE_ID}`. If the query returns 0 records, something is wrong (deploy reported success but row not visible) — halt with `Error: Deploy reported success but Queue {QUEUE_DEV_NAME} not findable — check user permissions for viewing Group.`

## Stage 3-Queue.5: Optionally add current user as member

If `{ADD_SELF}` is true:

```bash
# Get the current user id
USER_ID=$(sf org display --target-org '{ORG_ALIAS}' --json | node -e 'console.log(JSON.parse(require("fs").readFileSync(0,"utf8")).result.id)')
# Insert GroupMember
sf data create record --target-org '{ORG_ALIAS}' --sobject GroupMember \
  --values "GroupId={QUEUE_ID} UserOrGroupId=${USER_ID}" --json
```

A failure here (e.g. duplicate GroupMember) is not fatal — log it and continue.

After this stage, jump to Stage 5 (PATCH).
