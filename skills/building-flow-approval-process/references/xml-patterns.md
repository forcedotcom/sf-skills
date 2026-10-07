# XML Patterns — Flow Approval Process

Complete XML reference for all components of a Flow Approval Process.

---

## Orchestration — Required Input Variables

```xml
<variables>
    <name>recordId</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>
<variables>
    <name>submitter</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>
<variables>
    <name>submissionComments</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>
<variables>
    <name>firstApprover</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>
```

---

## WebLink — Only Valid Trigger

```xml
<WebLink>
    <fullName>LaunchApproval</fullName>
    <availability>online</availability>
    <displayType>button</displayType>
    <linkType>url</linkType>
    <openType>replace</openType>
    <protected>false</protected>
    <url>/flow/MyOrchestration?recordId={!Object__c.Id}&amp;submitter={!$User.Id}&amp;retURL=/{!Object__c.Id}</url>
</WebLink>
```

Add to the page layout as `actionType: CustomButton`.

**Do not include** `hasMenubar`, `hasScrollbars`, `height`, `position`, `isResizable` — these are forbidden with `openType: replace` and cause deployment failures.

---

## Background Step

Calls an AutoLaunched flow. Use for calculations, evaluations, and status updates.

```xml
<stageSteps>
    <name>CalcLevel</name>
    <actionName>MyAutoLaunchedFlow</actionName>
    <actionType>stepBackground</actionType>
    <stepSubtype>BackgroundStep</stepSubtype>
    <inputParameters>
        <name>recordId</name>
        <value>
            <elementReference>recordId</elementReference>
        </value>
    </inputParameters>
    <outputConfigParams>
        <name>approvalLevel</name>
        <!-- Must match the output variable name in the called flow -->
        <value xsi:nil="true"/>
    </outputConfigParams>
    <requiresAsyncProcessing>false</requiresAsyncProcessing>
    <runAsUser>false</runAsUser>
    <shouldLock>false</shouldLock>
    <label>Calculate Level</label>
</stageSteps>
```

**Input constraints:** only variable references (`<elementReference>`) or string literals (`<stringValue>1</stringValue>`) are valid. Expressions and merge fields are not supported.

---

## Approval Step

Calls a Screen Flow for the approver UI.

```xml
<stageSteps>
    <name>Approval_N1</name>
    <actionName>Review_Approval_Screen_Flow</actionName>
    <actionType>stepApproval</actionType>
    <stepSubtype>ApprovalStep</stepSubtype>
    <assignees>
        <assignee>
            <stringValue>MyQueueDeveloperName</stringValue>
        </assignee>
        <assigneeType>Queue</assigneeType>
        <!-- Valid values: Queue | User | Group -->
    </assignees>
    <outputConfigParams>
        <name>approvalDecision</name>
        <value xsi:nil="true"/>
    </outputConfigParams>
    <requiresAsyncProcessing>true</requiresAsyncProcessing>
    <runAsUser>true</runAsUser>
    <shouldLock>true</shouldLock>
    <label>Approval Level 1</label>
</stageSteps>
```

---

## Decision Element — Routing After Background Step

Reference Background Step outputs using the `Outputs.` prefix:

```xml
<decisions>
    <name>RouteByLevel</name>
    <label>Route by Approval Level</label>
    <rules>
        <name>Level1</name>
        <conditionLogic>and</conditionLogic>
        <conditions>
            <leftValueReference>CalcLevel.Outputs.approvalLevel</leftValueReference>
            <operator>EqualTo</operator>
            <rightValue>
                <stringValue>1</stringValue>
            </rightValue>
        </conditions>
        <connector>
            <targetReference>Stage_N1</targetReference>
        </connector>
        <label>Level 1</label>
    </rules>
</decisions>
```

Decision after an Approval Step — check the `approvalDecision` output:

```xml
<leftValueReference>Approval_N1.Outputs.approvalDecision</leftValueReference>
<!-- Valid values: "Approve" or "Reject" — case-sensitive -->
```

---

## Screen Flow — Required Variables

The approver Screen Flow must expose these variables with the exact names shown.

```xml
<!-- Inputs -->
<variables>
    <name>approvalInformation</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>
<variables>
    <name>recordId</name>
    <dataType>String</dataType>
    <isInput>true</isInput>
</variables>

<!-- Outputs — exact names required by the orchestration -->
<variables>
    <name>approvalDecision</name>
    <dataType>String</dataType>
    <isOutput>true</isOutput>
    <value>
        <elementReference>ApprovalRadioButtons</elementReference>
    </value>
</variables>
<!-- Radio button choices must produce exactly "Approve" or "Reject" -->

<variables>
    <name>approvalComments</name>
    <dataType>String</dataType>
    <isOutput>true</isOutput>
</variables>
```

Add a `faultConnector` on every `recordLookups` element leading to a screen that displays `{!$Flow.FaultMessage}`.

---

## Orchestrated Stage — Full Structure

```xml
<orchestratedStages>
    <name>Stage_N1</name>
    <label>Stage Level 1</label>
    <exitConditionLogic>and</exitConditionLogic>
    <stageSteps>
        <!-- Approval Step first -->
        <name>Approval_N1</name>
        <actionName>Review_Approval_Screen_Flow</actionName>
        <actionType>stepApproval</actionType>
        <stepSubtype>ApprovalStep</stepSubtype>
        <assignees>
            <assignee><stringValue>MyQueue</stringValue></assignee>
            <assigneeType>Queue</assigneeType>
        </assignees>
        <outputConfigParams>
            <name>approvalDecision</name>
            <value xsi:nil="true"/>
        </outputConfigParams>
        <requiresAsyncProcessing>true</requiresAsyncProcessing>
        <runAsUser>true</runAsUser>
        <shouldLock>true</shouldLock>
        <label>Approval N1</label>
    </stageSteps>
    <stageSteps>
        <!-- Background Step for status update, runs after approval -->
        <name>UpdateStatus_N1</name>
        <actionName>UpdateApprovalStatusFlow</actionName>
        <actionType>stepBackground</actionType>
        <stepSubtype>BackgroundStep</stepSubtype>
        <inputParameters>
            <name>recordId</name>
            <value><elementReference>recordId</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>status</name>
            <value><stringValue>PendingN2</stringValue></value>
        </inputParameters>
        <requiresAsyncProcessing>false</requiresAsyncProcessing>
        <runAsUser>false</runAsUser>
        <shouldLock>false</shouldLock>
        <label>Update Status N1</label>
    </stageSteps>
    <connector>
        <targetReference>RouteAfterN1</targetReference>
    </connector>
</orchestratedStages>
```
