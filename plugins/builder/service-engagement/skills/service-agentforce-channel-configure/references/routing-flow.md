# RoutingFlows — inbound and outbound

Two distinct RoutingFlows are used when wiring an agent to a channel:

| Flow | `processType` | `routingType` | Purpose |
|---|---|---|---|
| Inbound | `RoutingFlow` | `Copilot` | Routes arriving work items *to* the agent; queue is fallback when agent unavailable |
| Outbound | `RoutingFlow` | `QueueBased` | Routes *from* the agent to a human queue when the customer requests escalation |

Both flows reference the same fallback queue resolved in Phase 1. The inbound flow is created in Phase 2 for **Branch B (Voice)**, and for **Branch C (Email-to-Case)** when the user picks the Omni-Channel flow path over direct case-owner assignment, and Branch A uses `sessionHandlerAsa`. The outbound flow is created in Phase 3 if the user opts into outbound escalation.

---

## Part 1 — Inbound RoutingFlow (Copilot routing)

Used for Voice (Branch B), and for Email-to-Case (Branch C) on the Omni-Channel flow path. When a work item arrives on the channel, it routes directly to the Agentforce Agent, with the fallback queue used when the agent is unavailable.

The `routingType` is `Copilot` (the platform token for Agentforce Agent routing). The agent is referenced by its **label** (`copilotLabel`), not its DeveloperName. The queue fallback is expressed via `queueLabel` (the queue's `Name` field) and `queueId` (the queue's 18-char record Id).

## Naming convention

| Channel | Flow Label | DeveloperName |
|---|---|---|
| Voice | `{AgentLabel} Inbound Voice Flow` | `{AgentDevName}_Inbound_Voice_Flow` |
| Service Email (Email-to-Case) | `{AgentLabel} Inbound Email Flow` | `{AgentDevName}_Inbound_Email_Flow` |

## Lookup the queue Id before writing the XML

The `queueId` parameter must be a hardcoded 18-char Id in the XML. Query it from the `QUEUE_DEVELOPER_NAME` resolved in Phase 1:

```bash
QUEUE_ID=$(sf data query --target-org $ORG --json \
  --query "SELECT Id FROM Group WHERE Type='Queue' AND DeveloperName='{QUEUE_DEVELOPER_NAME}'" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['records'][0]['Id'])")
```

## XML template

Substitute: `{FLOW_LABEL}`, `{FLOW_DEVELOPER_NAME}`, `{AGENT_LABEL}`, `{AGENT_DEV_NAME}` (BotDefinition DeveloperName), `{QUEUE_LABEL}` (the queue's `Name`, e.g. `Voice Queue`), `{QUEUE_ID}` (18-char Id), `{SERVICE_CHANNEL_DEV_NAME}`, `{SERVICE_CHANNEL_LABEL}`.

> **`copilotId` is required.** Without it the platform cannot resolve the agent at runtime and routes to the fallback queue instead. Use a `<setupReference>` pointing to the `BotDefinition` by DeveloperName — do not use a hardcoded Salesforce Id.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <actionCalls>
        <name>Route_to_Agent</name>
        <label>Route to Agent</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>routeWork</actionName>
        <actionType>routeWork</actionType>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>recordId</name>
            <value><elementReference>recordId</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelLabel</name>
            <value><stringValue>{SERVICE_CHANNEL_LABEL}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelDevName</name>
            <value><stringValue>{SERVICE_CHANNEL_DEV_NAME}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>routingType</name>
            <value><stringValue>Copilot</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>copilotLabel</name>
            <value><stringValue>{AGENT_LABEL}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>copilotId</name>
            <value>
                <setupReference>{AGENT_DEV_NAME}</setupReference>
                <setupReferenceType>BotDefinition</setupReferenceType>
            </value>
        </inputParameters>
        <inputParameters>
            <name>queueLabel</name>
            <value><stringValue>{QUEUE_LABEL}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>queueId</name>
            <value><stringValue>{QUEUE_ID}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelId</name>
            <value>
                <setupReference>{SERVICE_CHANNEL_DEV_NAME}</setupReference>
                <setupReferenceType>ServiceChannel</setupReferenceType>
            </value>
        </inputParameters>
        <nameSegment>routeWork</nameSegment>
        <offset>0</offset>
        <versionString>2.0.0</versionString>
    </actionCalls>
    <apiVersion>67.0</apiVersion>
    <areMetricsLoggedToDataCloud>false</areMetricsLoggedToDataCloud>
    <environments>Default</environments>
    <interviewLabel>{FLOW_DEVELOPER_NAME} {!$Flow.CurrentDateTime}</interviewLabel>
    <label>{FLOW_LABEL}</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value>
    </processMetadataValues>
    <processMetadataValues>
        <name>OriginBuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processType>RoutingFlow</processType>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector><targetReference>Route_to_Agent</targetReference></connector>
    </start>
    <status>Active</status>
    <variables>
        <name>recordId</name>
        <dataType>String</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
</Flow>
```

## Deploy and verify

Write the XML to `force-app/main/default/flows/{FLOW_DEVELOPER_NAME}.flow-meta.xml`, then deploy:

```bash
sf project deploy start -m "Flow:{FLOW_DEVELOPER_NAME}" --target-org $ORG
```

Verify the flow is active:
```bash
sf data query --target-org $ORG --json \
  --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='{FLOW_DEVELOPER_NAME}'"
```

`ActiveVersionId` must be non-null. If it is null, the deploy did not produce an active version — check the deploy report for errors.

## Common failures (inbound)

| Symptom | Cause |
|---|---|
| `ActiveVersionId` is null after deploy | Flow saved as inactive draft — check for XML validation errors in the deploy report |
| Work items route to queue instead of agent | `copilotId` is missing (most common), `routingType` is `QueueBased` instead of `Copilot`, or `copilotLabel` doesn't match the agent's exact label — all three must be present and correct |
| Flow deploys but doesn't appear in Omni-Channel routing config | The flow is not yet referenced in a routing config — this skill doesn't create the routing config; the channel's own routing config must reference this flow |

---

## Part 2 — Outbound RoutingFlow (QueueBased escalation)

Used in Phase 3 for all channel types. When the agent escalates to a human, this flow routes the conversation to the fallback queue resolved in Phase 1.

### Naming convention

| Channel | Flow Label | DeveloperName |
|---|---|---|
| Enhanced Chat | `{AgentLabel} Outbound Enhanced Chat Flow` | `{AgentDevName}_Outbound_Enhanced_Chat_Flow` |
| Enhanced Messaging | `{AgentLabel} Outbound Messaging Flow` | `{AgentDevName}_Outbound_Messaging_Flow` |
| Voice | `{AgentLabel} Outbound Voice Flow` | `{AgentDevName}_Outbound_Voice_Flow` |
| Service Email (Email-to-Case) | `{AgentLabel} Outbound Email Flow` | `{AgentDevName}_Outbound_Email_Flow` |

### Check before creating

```bash
sf data query --target-org $ORG --json \
  --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='{FLOW_DEVELOPER_NAME}' AND ProcessType='RoutingFlow'"
```

If a row exists with non-null `ActiveVersionId`, reuse it — capture the `ApiName` and skip creation. If `ActiveVersionId` is null (inactive draft / OOB platform flow), create a new flow anyway — do not attempt to activate an existing draft.

### Service channel values by channel type

| Channel | `SERVICE_CHANNEL_DEV_NAME` | `SERVICE_CHANNEL_LABEL` |
|---|---|---|
| Enhanced Chat / Enhanced Messaging | `sfdc_livemessage` | `Messaging` |
| Voice | `sfdc_phone` | `Phone` |
| Service Email (Email-to-Case) | *(org-specific — the Case-based ServiceChannel; resolve or provision it, see below)* | *(its `MasterLabel`)* |

For **Email-to-Case (Branch C)**, there is no fixed platform token — the outbound flow needs the org's **Case-based `ServiceChannel`** (`RelatedEntity = 'Case'`). Resolve it here, and provision it if absent, before writing the flow:

```bash
sf data query --target-org $ORG --json \
  --query "SELECT DeveloperName, MasterLabel FROM ServiceChannel WHERE RelatedEntity='Case' LIMIT 1"
```

Use the returned `DeveloperName` as `SERVICE_CHANNEL_DEV_NAME` and `MasterLabel` as `SERVICE_CHANNEL_LABEL`. If no row is returned, provision one first — see `references/channel-types.md` § "Provision a Case ServiceChannel".

### XML template

Substitute: `{FLOW_LABEL}`, `{FLOW_DEVELOPER_NAME}`, `{QUEUE_DEVELOPER_NAME}` (from Phase 1), `{SERVICE_CHANNEL_DEV_NAME}`, `{SERVICE_CHANNEL_LABEL}`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <actionCalls>
        <name>Check_Availability</name>
        <label>Check Availability for Routing</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>checkAvailabilityForRouting</actionName>
        <actionType>checkAvailabilityForRouting</actionType>
        <connector>
            <targetReference>Are_Reps_Available</targetReference>
        </connector>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>serviceChannelId</name>
            <value>
                <setupReference>{SERVICE_CHANNEL_DEV_NAME}</setupReference>
                <setupReferenceType>ServiceChannel</setupReferenceType>
            </value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelLabel</name>
            <value><stringValue>{SERVICE_CHANNEL_LABEL}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelDevName</name>
            <value><stringValue>{SERVICE_CHANNEL_DEV_NAME}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>routingType</name>
            <value><stringValue>QueueBased</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>queueId</name>
            <value><elementReference>Lookup_Queue_by_Name.Id</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>isQueueVariable</name>
            <value><booleanValue>true</booleanValue></value>
        </inputParameters>
        <inputParameters>
            <name>selectedOutputs</name>
            <value><stringValue>GET_AVAILABILITY</stringValue></value>
        </inputParameters>
        <nameSegment>checkAvailabilityForRouting</nameSegment>
        <outputParameters>
            <assignToReference>onlineAgentsCount</assignToReference>
            <name>onlineAgentsCount</name>
        </outputParameters>
        <versionString>2.0.0</versionString>
    </actionCalls>
    <actionCalls>
        <name>Route_to_Queue</name>
        <label>Route to Queue</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <actionName>routeWork</actionName>
        <actionType>routeWork</actionType>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>recordId</name>
            <value><elementReference>recordId</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelLabel</name>
            <value><stringValue>{SERVICE_CHANNEL_LABEL}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelDevName</name>
            <value><stringValue>{SERVICE_CHANNEL_DEV_NAME}</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>routingType</name>
            <value><stringValue>QueueBased</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>serviceChannelId</name>
            <value>
                <setupReference>{SERVICE_CHANNEL_DEV_NAME}</setupReference>
                <setupReferenceType>ServiceChannel</setupReferenceType>
            </value>
        </inputParameters>
        <inputParameters>
            <name>queueId</name>
            <value><elementReference>Lookup_Queue_by_Name.Id</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>isQueueVariable</name>
            <value><booleanValue>true</booleanValue></value>
        </inputParameters>
        <nameSegment>routeWork</nameSegment>
        <versionString>2.0.0</versionString>
    </actionCalls>
    <apiVersion>67.0</apiVersion>
    <areMetricsLoggedToDataCloud>false</areMetricsLoggedToDataCloud>
    <decisions>
        <name>Are_Reps_Available</name>
        <label>Are Reps Available?</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <defaultConnectorLabel>No</defaultConnectorLabel>
        <rules>
            <name>Reps_Available</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>onlineAgentsCount</leftValueReference>
                <operator>GreaterThan</operator>
                <rightValue><numberValue>0.0</numberValue></rightValue>
            </conditions>
            <connector><targetReference>Route_to_Queue</targetReference></connector>
            <label>Yes</label>
        </rules>
    </decisions>
    <environments>Default</environments>
    <interviewLabel>{FLOW_DEVELOPER_NAME} {!$Flow.CurrentDateTime}</interviewLabel>
    <label>{FLOW_LABEL}</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value>
    </processMetadataValues>
    <processMetadataValues>
        <name>OriginBuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processType>RoutingFlow</processType>
    <recordLookups>
        <name>Lookup_Queue_by_Name</name>
        <label>Lookup Queue by Name</label>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Check_Availability</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>DeveloperName</field>
            <operator>EqualTo</operator>
            <value><stringValue>{QUEUE_DEVELOPER_NAME}</stringValue></value>
        </filters>
        <filters>
            <field>Type</field>
            <operator>EqualTo</operator>
            <value><stringValue>Queue</stringValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>Group</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <start>
        <locationX>0</locationX>
        <locationY>0</locationY>
        <connector><targetReference>Lookup_Queue_by_Name</targetReference></connector>
    </start>
    <status>Active</status>
    <variables>
        <name>onlineAgentsCount</name>
        <dataType>Number</dataType>
        <isCollection>false</isCollection>
        <isInput>false</isInput>
        <isOutput>false</isOutput>
        <scale>0</scale>
    </variables>
    <variables>
        <name>recordId</name>
        <dataType>String</dataType>
        <isCollection>false</isCollection>
        <isInput>true</isInput>
        <isOutput>false</isOutput>
    </variables>
</Flow>
```

### Deploy and verify

```bash
sf project deploy start -m "Flow:{FLOW_DEVELOPER_NAME}" --target-org $ORG
sf data query --target-org $ORG --json \
  --query "SELECT ApiName, ActiveVersionId FROM FlowDefinitionView WHERE ApiName='{FLOW_DEVELOPER_NAME}'"
```

`ActiveVersionId` must be non-null. Capture `{FLOW_DEVELOPER_NAME}` for use in the agent's connection block (`outbound_route_name: "flow://{FLOW_DEVELOPER_NAME}"`).

## Common failures (outbound)

| Symptom | Cause |
|---|---|
| `ActiveVersionId` is null after deploy | Flow saved as inactive draft — check XML for validation errors |
| Escalation goes nowhere / agent hangs | Connection block uses wrong key (`messaging:` instead of `customer_web_client:` for EmbeddedMessaging, etc.) — see `agent-wiring.md` |
| No agents available — queue not receiving work | Queue lacks a `QueueSobject` for the correct SobjectType — recheck Phase 1 |
