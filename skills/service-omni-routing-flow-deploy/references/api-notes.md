# API notes — Flow (v66) + Actions REST invocation

## Two flow variants shipped by this skill

This skill ships **two** Flow assets under `assets/force-app/main/default/flows/`. They solve two different problems and are verified two different ways — do not conflate them.

| Asset | processType | Verified by | Routes real work? | Purpose |
|---|---|---|---|---|
| `Omni_Route_Cases` | `AutoLaunchedFlow` | Actions REST `dryRun` invoke | **No** (dry-run gate) | Proves headless CLI invocability — "can the platform/CLI execute a routing flow without a real work item?" |
| `Omni_Route_Case_Trigger` | `AutoLaunchedFlow` + record trigger (`RecordAfterSave`, Case Create) | Record DML → PendingServiceRouting / AgentWork query | **Yes** | Production routing — fires on real Case insert, calls `routeWork`, hands the Case to Omni-Channel for distribution |

The autolaunched variant answers *"is flow invocation wired up?"* in one HTTP call with no side effects. The record-triggered variant answers *"do real Cases actually reach an agent?"* — which can only be proven by inserting a Case and observing the routing side effects. Both are legitimate parts of the AFCC contract: the smoke test de-risks the CLI/headless path; the trigger closes the "basic happy-path omni flow which routes work item to given queue" gap.

**Why the trigger flow is `AutoLaunchedFlow` with a `<start>` record trigger, not a separate processType:** Salesforce implements record-triggered flows as `AutoLaunchedFlow` process type plus a `<start>` block carrying `<object>`, `<recordTriggerType>`, and `<triggerType>RecordAfterSave</triggerType>`. There is no distinct `RecordAfterSave` processType value — the trigger semantics live entirely in `<start>`. This is why the processType matrix below lists record-triggered rows: same processType, different `<start>` shape.

### Verifying the record-triggered variant (no Actions REST — use record DML)

The trigger flow is **not** invocable via Actions REST (record-triggered flows aren't exposed as custom actions). Verify it by exercising the trigger and observing side effects:

```bash
# 1. baseline
PSR0=$(sf data query -o "$ORG" -q "SELECT COUNT(Id) c FROM PendingServiceRouting" --json | jq -r '.result.records[0].c')
AW0=$(sf data query -o "$ORG" -q "SELECT COUNT(Id) c FROM AgentWork" --json | jq -r '.result.records[0].c')

# 2. insert a Case (fires the trigger)
CASE=$(sf data create record -o "$ORG" --sobject Case \
  --values "Subject='Omni trigger verify' Status='New' Origin='Email'" --json | jq -r '.result.id')

# 3. re-query — PSR should be +1 for this Case; AgentWork +1 if an agent is online
sf data query -o "$ORG" -q "SELECT WorkItemId, IsReadyForRouting, RoutingType, QueueId FROM PendingServiceRouting WHERE WorkItemId='$CASE'" --json | jq -c '.result.records[]'

# 4. cleanup
sf data delete record -o "$ORG" --sobject Case --record-id "$CASE"
```

Success signals: `PendingServiceRouting 0 → 1` with `IsReadyForRouting=true, RoutingType=QueueBased`, and `AgentWork +1` in `Assigned` status against the target queue when an agent is online with a Case-capable presence status. `AgentWork` does not increment when no agent is online — the PSR row alone (`IsReadyForRouting=true`) is sufficient proof the flow routed correctly; agent assignment is a separate Omni-distribution concern.

### Token resolution (record-triggered variant portability)

`Omni_Route_Case_Trigger` carries **tokenized** org-specific IDs so the asset is portable across the 15K-org migration fleet — hardcoding IDs would break every org but the one it was authored against. Tokens and how to resolve them by DeveloperName at deploy time:

| Token | Resolve from | Query |
|---|---|---|
| `__SERVICE_CHANNEL_ID__` | ServiceChannel (Case) | `SELECT Id FROM ServiceChannel WHERE RelatedEntity='Case'` |
| `__SERVICE_CHANNEL_DEVNAME__` | ServiceChannel | `SELECT DeveloperName FROM ServiceChannel WHERE RelatedEntity='Case'` |
| `__SERVICE_CHANNEL_LABEL__` | ServiceChannel | `SELECT MasterLabel FROM ServiceChannel WHERE RelatedEntity='Case'` |
| `__QUEUE_ID__` | Group (Queue) | `SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='<QueueDN>'` |
| `__ROUTING_CONFIG_ID__` | QueueRoutingConfig | `SELECT Id FROM QueueRoutingConfig WHERE DeveloperName='<ConfigDN>'` |

Resolve each token against the target org, `sd`/`sed`-substitute into a materialized copy of the asset, then deploy the resolved copy. Never commit the resolved copy — the committed asset stays tokenized.

## Flow XML skeleton (autolaunched)

Minimum shape a Flow XML must have to be deployable AND invocable via Actions REST:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <label>Omni Route Cases</label>
    <processType>AutoLaunchedFlow</processType>
    <status>Active</status>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector>
            <targetReference>Some_Element</targetReference>
        </connector>
    </start>
    <variables>
        <name>dryRun</name>
        <dataType>Boolean</dataType>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
    <variables>
        <name>dryRunOk</name>
        <dataType>Boolean</dataType>
        <isInput>false</isInput>
        <isOutput>true</isOutput>
    </variables>
    ...
</Flow>
```

**Required for CLI invocation:**

| Element | Required | Notes |
|---|---|---|
| `<processType>AutoLaunchedFlow</processType>` | yes | Screen/record-triggered/event-triggered flows are NOT exposed as custom actions |
| `<status>Active</status>` | yes | Draft/Obsolete flows deploy but return 404 from Actions REST |
| `<label>` | yes | Display label; ≤ 80 chars |
| At least one `<start>` connector + one downstream element | yes | Empty flows fail schema validation |
| Boolean input `dryRun` + Boolean output `dryRunOk` | for this skill's smoke test | The invocation posts `{"inputs":[{"dryRun":true}]}` and expects `outputValues.dryRunOk=true` |

**processType matrix** — which flow types support which invocation paths:

| processType | Deploy via Metadata API | Invoke via Actions REST | Invoke via `sf apex run` (`Flow.Interview.<Name>`) | Invoke via record DML |
|---|---|---|---|---|
| `AutoLaunchedFlow` | yes | **yes** | yes | no |
| `Flow` (screen flow) | yes | no | no | no (needs Lightning/Experience runtime) |
| `AutoLaunchedFlowFromAnywhere` | yes | yes | yes | no |
| `RecordAfterSave` / `RecordBeforeSave` (record-triggered — `Omni_Route_Case_Trigger`) | yes | no | no | **yes** (trigger via `sf data create record` / `sf data update record`) |
| `RoutingFlow` (Omni routing type) | yes | limited | limited | no (platform invokes when work item enters queue) |
| `CustomEvent` (platform-event-triggered) | yes | no | no | **yes** (publish via `sf data create record --sobject <Event__e>`) |

For Omni routing specifically, the recommended shape is `AutoLaunchedFlow` (this skill's asset) — it can be invoked both by the platform (when registered on a Queue's Routing Configuration) AND by the CLI for smoke testing. `RoutingFlow` processType is more restrictive.

**`RoutingFlow` rejects `<runInMode>`:** if you author a flow of type `RoutingFlow` (rather than the `AutoLaunchedFlow` this skill ships), a `<runInMode>SystemModeWithoutSharing</runInMode>` element fails the deploy with "Because the flow is of type RoutingFlow, it can't be configured to always run in system context." Drop `<runInMode>` entirely from `RoutingFlow`-type flows.

## `routeWork` routing targets

The `routeWork` action accepts several mutually exclusive target types; set exactly one pair and let `routingType` select which applies:

| Target inputs | Routes to |
|---|---|
| `queueId` / `queueLabel` | a queue (most common) |
| `agentId` / `agentLabel` | a specific agent |
| `botId` / `botLabel` | an Einstein / Service Agent bot |
| `copilotId` / `copilotLabel` | a Copilot |
| `agentforceEmployeeAgentId` / `agentforceEmployeeAgentLabel` | an Agentforce Employee Agent (the escalation handoff target) |
| `digitalWorkerId` / `digitalWorkerLabel` | an Agentforce Orchestrator |
| `externalConversationBotId` / `externalConversationBotLabel` | an external conversation bot |

## Actions REST API endpoint

```http
POST /services/data/v<API>/actions/custom/flow/<FlowDeveloperName>
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "inputs": [
    { "dryRun": true }
  ]
}
```

**Success response** (HTTP 200):

```json
[
  {
    "actionName": "Omni_Route_Cases",
    "errors": null,
    "isSuccess": true,
    "outputValues": {
      "dryRunOk": true,
      "routed": false
    }
  }
]
```

Note: response is always a JSON **array**, even for a single-input call. `outputValues` contains every Flow variable marked `isOutput=true`.

**Failure responses:**

| HTTP | Body | Meaning | Fix |
|---|---|---|---|
| 200 | `[{"isSuccess": false, "errors": [{"message": "..."}]}]` | Flow ran but failed a decision/action | Read `.errors[0].message`; usually a variable-type mismatch or a missing prereq for the non-dry-run branch |
| 404 | `[{"errorCode":"NOT_FOUND","message":"The requested resource does not exist"}]` | Flow DeveloperName not found OR flow is Draft/Obsolete | Confirm the Flow exists and `<status>Active</status>` |
| 400 | `[{"errorCode":"INVALID_TYPE","message":"..."}]` | `<processType>` is not AutoLaunched (typically `Flow` for screen flows) | Rewrite the flow as autolaunched, or skip invocation for this flow type |
| 401 | `INVALID_SESSION_ID` | Session expired | Re-authenticate: `sf org login web --alias <alias>` |
| 403 | `INSUFFICIENT_ACCESS` | User running the CLI lacks "Run Flows" permission | Grant Run Flows permission, or run as admin |

## SF CLI invocation patterns

### Path 1 — `sf api request rest` (preferred; language-agnostic, structured JSON)

```bash
sf api request rest \
  --method POST \
  --target-org <alias> \
  --body '{"inputs":[{"dryRun":true}]}' \
  /services/data/v66.0/actions/custom/flow/Omni_Route_Cases
```

Body must be valid JSON. The path is passed as a positional arg (no `--url` flag on recent `sf` versions — the last positional is the path).

**Parsing pitfall — beta warning on stdout:** as of `sf` CLI v2.139+, `sf api request rest` prints a `Warning: This command is currently in beta. ...` line to **stdout** (not stderr) before the JSON body. Naive `jq` parsing chokes on it. Strip everything up to the first `[` or `{`:

```bash
raw=$(sf api request rest --method POST --target-org "$ORG" --body "$BODY" "$PATH_")
json=$(printf '%s' "$raw" | awk '/^[[{]/,0')
echo "$json" | jq -r '.[0].outputValues.dryRunOk'
```

This skill's deploy-and-report.sh does exactly this. If Salesforce ever removes the beta warning, the `awk` filter is a no-op — safe forward.

### Path 2 — `sf apex run` (when Apex context is needed)

```bash
cat > /tmp/invoke.apex <<'EOF'
Map<String, Object> params = new Map<String, Object>{ 'dryRun' => true };
Flow.Interview.Omni_Route_Cases flow = new Flow.Interview.Omni_Route_Cases(params);
flow.start();
System.debug('OUT: dryRunOk=' + flow.getVariableValue('dryRunOk'));
EOF
sf apex run -f /tmp/invoke.apex -o <alias>
```

Returns unstructured `System.debug` output; parse with a regex if scripting. Requires no additional metadata beyond the Flow itself.

### Path 3 — `sf flow test run` (only if FlowTest metadata is shipped)

```bash
sf flow test run --flow-api-name Omni_Route_Cases --target-org <alias>
```

Requires a `FlowTest:<TestName>` metadata component that carries assertions. Heavier deploy surface; not used by this skill's smoke test.

## Deploy semantics

Metadata API deploy of `Flow:<DN>` returns per-file state:

- `Created` — new Flow record (first deploy or new DeveloperName)
- `Changed` — Flow existed, deploy created a new version
- `Unchanged` — Flow existed AND deploy determined no new version was needed

**Flow-specific quirk: `Changed` on identical redeploy is normal.** Unlike `ServicePresenceStatus`, `Queue`, `ServiceChannel`, and other static metadata types, Flows are not byte-idempotent through the Metadata API. Flow versioning treats every deploy as a potential new version — even when the deployed XML is byte-identical to the currently-Active version, the response is typically `Changed` and a new inactive version number is bumped internally. A first deploy returns `Created`; a second identical deploy returns `Changed` with a new deploy Id.

**Implication for the coordinator:** treat `Changed` for Flow components as "successfully redeployed" rather than "operator modified the flow." The skill's `status: "updated"` on second run does not necessarily mean anything semantically changed. If the coordinator needs true operator-modification detection, compare the `<label>`, `<processType>`, `<status>`, and top-level `<variables>` block between deploys.

**Workaround for strict idempotency:** deploy with `<status>Draft</status>` and only activate on first deploy — subsequent deploys of identical Draft XML often return `Unchanged`. But this breaks the CLI-invocability contract (Active required for Actions REST), so this skill doesn't take that path.

**XML element ordering does NOT affect deploy success** — Salesforce parses and re-serializes canonically. Elements in any order deploy the same.

**Whitespace/indentation does NOT affect deploy success** — normalized before parsing.

**Deploying a Flow with `<status>Draft</status>` does NOT overwrite the Active version** — the existing Active version stays live. This is why our post-verify retrieves and asserts Active: a Draft deploy that "succeeds" skills the org in a state where the CLI invocation still hits the previous Active version, giving misleading test results.

## Common deploy failures + translations

| Salesforce error | Skill translation | Fix |
|---|---|---|
| `INVALID_TYPE: Flow` | Flow metadata not enabled | Rare; usually indicates an org edition without Flow Builder. Escalate. |
| `The apiVersion X is not valid for this API version` | Flow XML `<apiVersion>` > org's API | Lower the Flow's `<apiVersion>` to ≤ the org's current version |
| `Invalid element name` / `was not expected` | Schema mismatch | Check element ordering and spelling against v66 Metadata API docs; some elements are strictly ordered |
| `INSUFFICIENT_ACCESS_OR_READONLY` | User lacks Metadata API deploy permissions | Re-auth as System Administrator, or grant Manage Flows + Deploy From Metadata API |
| `The version of the flow you're trying to activate isn't the latest version` | Someone deployed a newer draft in parallel | Retrieve the newer version, merge, redeploy |
| `You can't deploy flow XXX because it references field YYY` | Flow references a field that doesn't exist on the org | Deploy the field first, or edit the flow to remove the reference |

## Retrieve semantics

`sf project retrieve start --metadata "Flow:<DN>"` returns one XML file. Typically completes in ~2–5s (much faster than the presence-status ~4m 51s retrieve because Flow metadata is a single file, not a packaged set).

**Retrieved XML may not byte-match deployed XML** — Salesforce serializes flow elements in canonical order, which may differ from what you deployed. Grep for `<status>Active</status>` (structural) rather than diffing whole files.

## Standard vs custom flows

Orgs on Service Cloud typically ship with these standard Omni routing flows out of the box:

- `Standard_Omni_Routing_Flow` (if Omni-Channel is enabled)
- Various `Case_*` demo flows depending on Sales Cloud starter templates

Our `Omni_Route_Cases` is a custom addition — it won't collide, but it also won't be invoked by the platform automatically. To wire it into a queue's routing, register it via `service-omni-queue-routing-config-deploy` with `routing_flow_developer_name=Omni_Route_Cases`.

**Naming convention rule:** never use a Flow DeveloperName that starts with `Standard_` — reserved by Salesforce. Our skill uses `Omni_Route_<sObject>` prefix to stay clear of the standard namespace.

## Notes on API version selection

The Actions REST endpoint accepts any recent API version (`v58.0`+ has been stable for autolaunched flow invocation). The deploy script uses `sf org display --json | jq -r '.result.apiVersion'` to pick the org's current API version at runtime rather than hardcoding — this way a v70+ org gets v70 endpoints without a redeploy of the skill.

If the org's reported `apiVersion` is malformed (rare), the script falls back to `66.0` (the Flow XML's declared version).
