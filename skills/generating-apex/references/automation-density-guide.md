# Automation Density Guide

> **Source**: Salesforce Architect Decision Guides — Record-Triggered Automation
> **Related**: [trigger-actions-framework.md](./trigger-actions-framework.md)

---

## Automation Density Framework

**Automation density** = the number of automations (triggers, flows, processes) firing on a single object. Higher density increases governor limit risk and debugging complexity.

| Density | Triggers + Flows on Object | Recommended Tool | Rationale |
|---------|---------------------------|-----------------|-----------|
| **Low** (0-2) | Few automations, simple logic | **Flow** (Record-Triggered) | Declarative, admin-maintainable, faster to build |
| **Medium** (3-5) | Multiple automations, some complexity | **Hybrid** (Flow + Invocable Apex) | Flow orchestrates, Apex handles complex logic |
| **High** (6+) | Many automations, complex interdependencies | **Apex** (TAF or single trigger) | Full control over execution order and governor limits |

### Key Decision Factors

- **Team skill mix**: More admins → favor Flow. More developers → favor Apex.
- **Change frequency**: Frequently changing business rules → Flow (no deploy cycle for admins)
- **Quality assurance requirements**: Apex has mature validation options. Flow validation is improving but less granular.
- **Debug complexity**: Multiple flows on one object are hard to debug. Apex has better stack traces.

---

## One Entry Point Per Object

> **Rule**: Each object should have ONE primary entry point for record-triggered automation.

Multiple triggers and record-triggered flows on the same object create:
- **Unpredictable execution order** between triggers and flows
- **Governor limit stacking** across independent automations
- **Debugging nightmares** when logic conflicts

### Implementation Patterns

**Pure Flow (Low Density)**:
- Single Record-Triggered Flow per object per timing (Before Save / After Save)
- Use Subflows for modularity within that single flow

**Pure Apex (High Density)**:
- Single trigger per object → TAF MetadataTriggerHandler
- All logic in ordered Trigger Action classes

**Hybrid (Medium Density)**:
- Record-Triggered Flow as entry point
- Complex logic delegated to `@InvocableMethod` Apex

### Coexistence Management

When an org has BOTH Flow and Apex triggers on the same object (common in brownfield orgs):

1. **Audit first**: Use **Flow Trigger Explorer** (Setup → Process Automation → Flow Trigger Explorer) to see all automations per object
2. **Document execution order**: Flows before triggers? After? Both?
3. **Consolidate incrementally**: Don't refactor everything at once
4. **Validate together**: A change in one automation can break another

```
⚠️ Salesforce Execution Order (simplified):
   Before Flows → Before Triggers → Validation Rules →
   After Triggers → After Flows → Assignment Rules → Workflow Rules →
   Escalation Rules → Entitlement Rules → Record-Triggered Flows (After Save)
```

---

## Hybrid Pattern: Flow + Invocable Apex

The hybrid pattern uses Flow as the orchestrator and Apex for complex operations.

### When to Use

- Business rules change frequently (Flow) but implementation is complex (Apex)
- Admins need to control WHEN logic runs; developers control WHAT it does
- You need Apex capabilities (complex queries, callouts, governor limit management) inside a Flow

### Architecture

```
Record-Triggered Flow (After Save)
  ├── Decision: Check entry conditions
  ├── Action: Call @InvocableMethod (Apex)
  │     └── Complex business logic, callouts, multi-object DML
  └── Fault Path: Error handler
```

### Critical Limitation

> **`@InvocableMethod` calls from Flow execute in after-save context only.** You cannot call Invocable Apex from a Before-Save Flow. Before-Save flows are limited to field updates on the triggering record.

```apex
public with sharing class ProcessOrderInvocable {

    @InvocableMethod(label='Process Order' category='Orders')
    public static List<Response> execute(List<Request> requests) {
        List<Response> responses = new List<Response>();
        for (Request req : requests) {
            Response res = new Response();
            try {
                // Complex logic here
                res.isSuccess = true;
            } catch (Exception e) {
                res.isSuccess = false;
                res.errorMessage = e.getMessage();
            }
            responses.add(res);
        }
        return responses;
    }

    public class Request {
        @InvocableVariable(label='Record ID' required=true)
        public Id recordId;
    }

    public class Response {
        @InvocableVariable(label='Success')
        public Boolean isSuccess;
        @InvocableVariable(label='Error Message')
        public String errorMessage;
    }
}
```

---

## CDC as Async Pattern from Triggers

Change Data Capture provides a built-in async mechanism for trigger-like behavior with failure isolation.

### When to Use CDC Instead of After-Save Triggers

| Factor | After-Save Trigger/Flow | CDC Subscriber |
|--------|------------------------|----------------|
| **Timing** | Same transaction | Async (separate transaction) |
| **Failure impact** | Rolls back triggering DML | Isolated — triggering DML succeeds |
| **Replay** | None | 72-hour replay window |
| **Governor limits** | Shared with triggering transaction | Separate transaction limits |
| **Use case** | Critical same-transaction logic | External sync, audit, non-critical updates |

### Pattern

1. Enable CDC on the object (Setup → Integrations → Change Data Capture)
2. Create CDC subscriber trigger on `{Object}ChangeEvent`
3. Process changes asynchronously with full replay capability

```apex
trigger AccountCDCSubscriber on AccountChangeEvent (after insert) {
    for (AccountChangeEvent event : Trigger.new) {
        String changeType = event.ChangeEventHeader.getChangeType();
        if (changeType == 'UPDATE') {
            List<String> changedFields = event.ChangeEventHeader.getChangedFields();
            if (changedFields.contains('Status__c')) {
                // Queue external sync — isolated from original transaction
                System.enqueueJob(new ExternalSyncQueueable(
                    event.ChangeEventHeader.getRecordIds()[0]
                ));
            }
        }
    }
}
```

---

## Scheduled Alternative Pattern

For non-time-critical automation, use a scheduled approach instead of trigger-based automation.

### Pattern: Set Status → Scheduled Job Processes

1. **Trigger/Flow**: Set a status field (e.g., `Processing_Status__c = 'Pending'`)
2. **Scheduled Flow or Batch**: Periodically queries pending records and processes them

### Benefits

- **Decouples** trigger execution from heavy processing
- **Batches** multiple records for efficient governor limit usage
- **Retryable** — failed records stay in pending status
- **Observable** — query `Processing_Status__c` for pipeline visibility

### Preference: Scheduled Flow over Apex Schedulable

| Factor | Scheduled Flow | Apex Schedulable |
|--------|---------------|-----------------|
| **Deployment** | Deployable metadata, packageable | Requires code deployment |
| **Admin maintenance** | Admins can modify schedule and logic | Developer-only |
| **Job limit** | No hard limit | 100 scheduled jobs max |
| **Best for** | Simple-to-medium scheduled tasks | Complex processing needing Batch Apex |

> **Recommendation**: Use Scheduled Flow for most scheduled automation. Use Apex `Schedulable` only when you need Batch Apex chaining or complex Apex-only logic.

---

## Flow Trigger Explorer

**Location**: Setup → Process Automation → Flow Trigger Explorer

This tool shows all automations (Flows, Process Builder, Workflow Rules) that fire on a given object, in execution order.

### Use Cases

- **Pre-development**: Check what already exists before adding automation
- **Debugging**: Understand why a record update produces unexpected results
- **Consolidation planning**: Identify redundant or conflicting automations
- **Impact analysis**: Before deactivating an automation, see what else runs alongside it

### Recommended Practice

Before creating any new Record-Triggered Flow or Trigger Action, check Flow Trigger Explorer to understand the existing automation landscape for that object.

---

## Summary: Decision Checklist

1. **Check density**: How many automations already exist on this object?
2. **Choose tool**: Low → Flow, Medium → Hybrid, High → Apex
3. **One entry point**: Don't add a second trigger or record-triggered flow if one exists
4. **Check coexistence**: Use Flow Trigger Explorer to see the full picture
5. **Consider CDC**: For external sync or non-critical async processing
6. **Consider scheduled**: For non-time-critical batch processing
