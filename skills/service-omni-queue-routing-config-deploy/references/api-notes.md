# QueueRoutingConfig — API notes

Load this reference **only when the skill hits an unexpected error or when customizing fields**. The happy path is straightforward and doesn't need this doc.

**sObject type:** `QueueRoutingConfig` (first-class, SOQL-queryable via the Data API). **API version:** v66.

---

## Schema (fields we use)

| Field | Type | v1 default | Semantics |
|---|---|---|---|
| `Id` | Id | (auto-generated) | Primary key |
| `DeveloperName` | string(80) | `Case_Routing_Config` | Unique per-org identifier; used for idempotent detection |
| `MasterLabel` | string(80) | `Case Routing Config` | UI display name |
| `RoutingModel` | picklist | `MostAvailable` | See RoutingModel Semantics below |
| `RoutingPriority` | integer | `1` | **REQUIRED, non-nillable** (confirmed via `sf sobject describe`). Omitting it makes every POST fail with `REQUIRED_FIELD_MISSING`. `1` = highest priority |
| `IsAttributeBased` | boolean | `false` | Whether to use attribute-based routing (v1 does not — requires attribute definitions) |
| `CapacityWeight` | integer(1..10) | `5` | How much of an agent's capacity ONE work item from this queue consumes. See CapacityWeight interaction below |
| `PushTimeout` | integer (sec) | `null` | Seconds to wait before pushing work back to queue if agent doesn't accept. `null` = use Omni default of 30 sec |
| `OverflowAssigneeId` | User Id | `null` | Fallback User that work is assigned to when all queue members are unavailable. `null` = no overflow (work stays queued indefinitely). Settable via the skill's `overflow-assignee` input (`QRC_OVERFLOW_ASSIGNEE`) — a Username or `005` Id resolved to an **active** User before the write; omitting it preserves the existing value rather than clearing it |

## RoutingModel semantics

| Value | Behavior |
|---|---|
| `MostAvailable` | Route to the agent with the most remaining capacity (i.e., handling the fewest current work items) |
| `LeastActive` | Route to the agent whose last work-item interaction was longest ago (load-balancing over time) |

**Not supported on v66:** `Priority` (removed), `SkillsBased` (moved to WorkSkillRouting on v66).

For most Omni Case setups, `MostAvailable` is the right default — it maximizes queue throughput. `LeastActive` is useful when you want to keep all agents equally busy over time (e.g., to prevent burnout of high-performers).

## CapacityWeight interaction with agent capacity

Capacity in Omni-Channel v66 is a three-way math:

- **Agent total capacity:** `PresenceUserConfig.Capacity` (default 10) — how much total work an agent can hold at once
- **Per-queue weight:** `QueueRoutingConfig.CapacityWeight` (this skill's default 5) — how much a single work item from this queue consumes
- **Per-channel weight:** removed on v66 — used to be `ServiceChannel.CapacityWeight`; no longer configurable

**Concrete example:**
- Agent with `PresenceUserConfig.Capacity=10`
- Case routes through `Case_Routing_Config` with `CapacityWeight=5`
- Agent can hold `10 / 5 = 2` cases simultaneously
- If a third case comes in, it stays queued until the agent completes one

**Rules of thumb:**
- Weight = 1 → agent holds 10 cases at once (high-throughput but hard to focus)
- Weight = 5 → agent holds 2 cases at once (this skill's default — balanced)
- Weight = 10 → agent holds 1 case at a time (deep focus, low throughput)

---

## Data API endpoints used

**GET (query):**

```text
GET /services/data/v66.0/query?q=SELECT+Id,+DeveloperName,+MasterLabel,+RoutingModel,+IsAttributeBased,+CapacityWeight,+PushTimeout,+OverflowAssigneeId+FROM+QueueRoutingConfig+WHERE+DeveloperName='Case_Routing_Config'
```

Or equivalently via `sf data query --query "SELECT ... FROM QueueRoutingConfig WHERE ..."` (which is what the skill's script uses).

**POST (create):**

```text
POST /services/data/v66.0/sobjects/QueueRoutingConfig
Content-Type: application/json

{
  "DeveloperName": "Case_Routing_Config",
  "MasterLabel": "Case Routing Config",
  "RoutingModel": "MostAvailable",
  "RoutingPriority": 1,
  "CapacityWeight": 5,
  "IsAttributeBased": false
}
```

Response: `{"id":"0K9RZ...", "success":true, "errors":[]}` (HTTP 201).
`RoutingPriority` is REQUIRED — a POST without it fails with `REQUIRED_FIELD_MISSING`.

**PATCH (update):**

```text
PATCH /services/data/v66.0/sobjects/QueueRoutingConfig/<id>
Content-Type: application/json

{
  "MasterLabel": "Case Routing Config",
  "RoutingModel": "MostAvailable",
  "RoutingPriority": 1,
  "CapacityWeight": 5,
  "IsAttributeBased": false
}
```

Response: empty body (HTTP 204). Note that PATCH does NOT include `DeveloperName` — Salesforce doesn't allow renaming via PATCH on QueueRoutingConfig.

Both invoked via `sf api request rest --target-org <alias> <path> --method POST|PATCH --body <json>`.

---

## Failure modes

| Symptom | Root cause | Skill behavior |
|---|---|---|
| Query returns `INVALID_TYPE` for QueueRoutingConfig | OmniChannelSettings not enabled | Skill translates to: `"OmniChannelSettings is not enabled on this org. Run service-omni-base-settings-configure first."` |
| POST returns `DUPLICATE_VALUE` on DeveloperName | Race with concurrent skill run | Retry once — the pre-check will now find the record and PATCH instead |
| POST/PATCH returns `INVALID_FIELD_VALUE` on RoutingModel | Value is not `MostAvailable` or `LeastActive` | Fail with a clear message naming the valid values |
| POST/PATCH returns `INVALID_FIELD_VALUE` on CapacityWeight | Value < 1 or > 10 | Fail with a clear message naming the valid range |
| PATCH silently changes nothing | Field values already match | Not a failure — just means Salesforce detected no diff. Skill correctly reports `status: reused` from its own pre-check |
| POST returns `INSUFFICIENT_ACCESS_OR_READONLY` | Executing user lacks `Manage Public List Views` OR the org has other Omni restrictions | Fail with escalation guidance |

---

## Why Data API instead of Metadata API

QueueRoutingConfig is a first-class sObject on Salesforce (unlike ServiceChannel, whose tuning fields are Metadata-only). The Data API has these advantages here:

- **Speed:** ~1 sec per call vs ~10 sec for Metadata deploy
- **Idempotency:** SOQL query returns clean field values for pre-check comparison; Metadata retrieve is slower and returns XML that needs parsing
- **Reversibility:** PATCH just updates fields; Metadata deploy replaces the whole record
- **No DX project overhead:** no `assets/`, no `sfdx-project.json`, no `package.xml`

Metadata API is still supported (`sf project deploy start --metadata "QueueRoutingConfig:Case_Routing_Config"` works), but adds latency with no functional benefit for this entity.
