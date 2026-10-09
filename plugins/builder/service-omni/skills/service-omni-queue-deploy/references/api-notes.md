# Queue — API notes

Load this reference when the skill blocks on a queue it cannot safely create or align (needs the manual click-path) or on unexpected errors.

**sObject type:** `Group` with `Type='Queue'`. Queues in Salesforce are a special kind of Group.
**Child records:** `QueueSobject` (many-to-one to Group; links queue to which sObject types it can hold).
**Optional membership:** `GroupMember` records (many-to-one to Group; users in the queue). See `service-omni-queue-members-assign` — this skill does NOT touch members.
**API version verified:** v66 (Summer '26 baseline).

---

## Schema (fields we use)

### `Group` (queue-typed subset)

| Field | Type | Semantics |
|---|---|---|
| `Id` | Id | Primary key. 18 chars starting with `00G` |
| `Name` | string(40) | UI display name |
| `DeveloperName` | string(80) | Unique per-org API name. Used for cross-org idempotency |
| `Type` | picklist | Must be `Queue` (other values: `Role`, `RoleAndSubordinates`, `Territory`, etc. — this skill filters to Queue only) |
| `QueueRoutingConfigId` | Id | FK to `QueueRoutingConfig`. Null-able but required for Omni routing |

Note: PATCHing `Type` on an existing Group is not allowed — Salesforce rejects it. Type is set at creation.

### `QueueSobject`

| Field | Type | Semantics |
|---|---|---|
| `Id` | Id | Primary key. 18 chars starting with `03g` |
| `QueueId` | Id | FK to `Group.Id`. Must be a Queue-typed Group |
| `SobjectType` | string | e.g., `Case`, `Lead`, `ContactRequest`. One record per sObject type the queue can hold |

Notes:
- QueueSobject is create-only via Data API — Salesforce does not allow PATCH on any QueueSobject field
- To change which sObject types a queue holds: DELETE the unwanted QueueSobject + POST new ones (destructive)
- v1 skill ONLY POSTS missing QueueSobject records; never deletes existing ones (preserves other-team routing decisions)

---

## Data API operations

### Query queue by DeveloperName

```text
SELECT Id, DeveloperName, Type, QueueRoutingConfigId FROM Group WHERE DeveloperName='CaseQueue' AND Type='Queue'
```

Always include `AND Type='Queue'` — DeveloperName is unique across ALL Group types, but the filter guards against non-Queue Groups with the same DeveloperName in edge cases.

### Query QueueSobject for a queue

```text
SELECT SobjectType FROM QueueSobject WHERE QueueId='<queue-id>'
```

Returns array of sObject-type strings. Use `.index(target)` to check if target sObject type is present.

### PATCH routing config

```text
PATCH /services/data/v66.0/sobjects/Group/<queue-id>
{"QueueRoutingConfigId": "<new-routing-config-id>"}
```

Response: empty body (HTTP 204) on success. Errors: `INVALID_FIELD_VALUE` if the target Id doesn't exist or isn't a QueueRoutingConfig, `INSUFFICIENT_ACCESS` if user lacks perm.

### POST QueueSobject

```text
POST /services/data/v66.0/sobjects/QueueSobject
{"QueueId": "<queue-id>", "SobjectType": "Case"}
```

Response: `{"id":"03g...","success":true,"errors":[]}` (HTTP 201).

---

## Queue creation via the Metadata API

By default the skill verifies and aligns an existing queue. With `--create-if-missing` it creates one via the Metadata API using a `.queue-meta.xml` file, which upserts by fullName (so re-running adopts an existing same-named queue rather than duplicating it).

Notes on the moving parts:
- The `Group` record (`Type='Queue'`) and its `QueueSobject` binding are both what the creation ships.
- Behavioral flags like `doesIncludeBosses` exist only via the Metadata API (the Data API cannot set them); the creation ships the minimal safe set (`doesSendEmailToMembers=false` plus the sObject binding).
- Members are deliberately not touched here. Deploying `<queueMembers>` would replace existing members (destructive), so membership is left to `service-omni-queue-members-assign`, which adds `GroupMember` rows additively.

Creation never deletes existing `QueueSobject` rows — other sObjects may be intentionally routed through the same queue.

---

## Manual click-path (when Queue doesn't exist)

Setup UI:

1. **Setup → Feature Settings → Service → Queues → New**
2. **Label:** `CaseQueue`
3. **Name (DeveloperName):** `CaseQueue`
4. **Routing Configuration:** `Case_Routing_Config` (must exist first — see [service-omni-queue-routing-config-deploy](../../service-omni-queue-routing-config-deploy/))
5. **Send Email to Members:** unchecked (v1 default)
6. **Supported Objects:** move `Case` to Selected
7. **Queue Members:** leave empty (`service-omni-queue-members-assign` handles this)
8. **Save**
9. Re-run this skill — should return `status: reused`

Metadata API alternative (advanced):

```bash
mkdir -p /tmp/q-create/force-app/main/default/queues
cat > /tmp/q-create/sfdx-project.json <<'EOF'
{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}
EOF
cat > /tmp/q-create/force-app/main/default/queues/CaseQueue.queue-meta.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Queue xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesIncludeBosses>false</doesIncludeBosses>
    <doesSendEmailToMembers>false</doesSendEmailToMembers>
    <name>CaseQueue</name>
    <queueRoutingConfig>Case_Routing_Config</queueRoutingConfig>
    <queueSobject>
        <sobjectType>Case</sobjectType>
    </queueSobject>
</Queue>
EOF
cd /tmp/q-create && sf project deploy start --target-org <alias> --metadata "Queue:CaseQueue"
```text

**Warning:** if `CaseQueue` already exists on the org, this Metadata API deploy will REPLACE `queueMembers` with an empty list (destructive). Do NOT run this on a queue that has existing members you want to keep. This is why v1 verify-only defers create.

---

## Failure modes

| Symptom | Root cause | Skill behavior |
|---|---|---|
| SOQL query returns 0 rows for `Group WHERE DeveloperName='CaseQueue' AND Type='Queue'` and the queue cannot be created safely | Queue doesn't exist | Block with click-path (see above) |
| SOQL query returns 0 rows for `QueueRoutingConfig WHERE DeveloperName='Case_Routing_Config'` | Prereq skill not run | Block: "Run service-omni-queue-routing-config-deploy first" |
| PATCH `Group.QueueRoutingConfigId` returns `INVALID_FIELD_VALUE` | Target routing config Id doesn't exist or isn't a QueueRoutingConfig | Block: inconsistent state between the two SOQL queries; retry the skill |
| POST `QueueSobject` returns `DUPLICATE_VALUE` | Race with concurrent skill run; sObject already added | Not a failure — re-query will confirm the record exists |
| PATCH returns `INSUFFICIENT_ACCESS_OR_READONLY` | Executing user lacks perm | Block: escalate to a System Administrator |
