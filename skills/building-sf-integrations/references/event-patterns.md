<!-- Parent: building-sf-integrations/SKILL.md -->
# Event-Driven Integration Patterns

This document provides detailed implementation patterns for Platform Events and Change Data Capture (CDC) in Salesforce integrations.

> **Parent Document**: [building-sf-integrations/SKILL.md](../SKILL.md)
> **Related**: [callout-patterns.md](./callout-patterns.md)

---

## Table of Contents

- [Platform Events](#platform-events)
  - [Platform Event Definition](#platform-event-definition)
  - [Event Publisher](#event-publisher)
  - [Event Subscriber Trigger](#event-subscriber-trigger)
  - [High-Volume vs Standard-Volume Events](#high-volume-vs-standard-volume-events)
- [Change Data Capture (CDC)](#change-data-capture-cdc)
  - [CDC Enablement](#cdc-enablement)
  - [CDC Subscriber Trigger](#cdc-subscriber-trigger)
  - [CDC Handler Service](#cdc-handler-service)
  - [Field-Specific Change Detection](#field-specific-change-detection)

---

## Platform Events

Platform Events enable asynchronous, event-driven communication between applications. They provide a publish-subscribe model where publishers fire events and subscribers listen for them.

### Platform Event Definition

**Use Case**: Asynchronous, event-driven communication

**Template**: `assets/platform-events/platform-event-definition.object-meta.xml`

#### Standard Volume Event

Best for moderate event volumes (~2,000 events/hour):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>StandardVolume</eventType>
    <label>{{EventLabel}}</label>
    <pluralLabel>{{EventPluralLabel}}</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>

    <fields>
        <fullName>{{FieldName}}__c</fullName>
        <label>{{FieldLabel}}</label>
        <type>Text</type>
        <length>255</length>
    </fields>

    <fields>
        <fullName>RecordId__c</fullName>
        <label>Record ID</label>
        <type>Text</type>
        <length>18</length>
        <description>Salesforce record ID related to this event</description>
    </fields>

    <fields>
        <fullName>Timestamp__c</fullName>
        <label>Timestamp</label>
        <type>DateTime</type>
        <description>When the event was triggered</description>
    </fields>
</CustomObject>
```

#### High-Volume Event

Best for millions of events per day:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>HighVolume</eventType>
    <label>{{EventLabel}}</label>
    <pluralLabel>{{EventPluralLabel}}</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>

    <fields>
        <fullName>{{FieldName}}__c</fullName>
        <label>{{FieldLabel}}</label>
        <type>Text</type>
        <length>255</length>
    </fields>
</CustomObject>
```

#### Key Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| **eventType** | `StandardVolume`, `HighVolume` | Event throughput capacity |
| **publishBehavior** | `PublishAfterCommit`, `PublishImmediately` | When events are published |
| **deploymentStatus** | `Deployed`, `InDevelopment` | Deployment status |

**PublishBehavior Details**:
- `PublishAfterCommit`: Event published only if transaction commits (recommended)
- `PublishImmediately`: Event published immediately, even if transaction rolls back

---

### Event Publisher

**Template**: `assets/platform-events/event-publisher.cls`

#### Bulk Event Publisher

```apex
public with sharing class {{EventName}}Publisher {

    public static void publishEvents(List<{{EventName}}__e> events) {
        if (events == null || events.isEmpty()) {
            return;
        }

        List<Database.SaveResult> results = EventBus.publish(events);

        for (Integer i = 0; i < results.size(); i++) {
            Database.SaveResult sr = results[i];
            if (!sr.isSuccess()) {
                for (Database.Error err : sr.getErrors()) {
                    System.debug(LoggingLevel.ERROR,
                        'Event publish error: ' + err.getStatusCode() + ' - ' + err.getMessage());
                }
            }
        }
    }

    public static void publishSingleEvent(Map<String, Object> eventData) {
        {{EventName}}__e event = new {{EventName}}__e();

        // Map fields from eventData
        event.{{FieldName}}__c = (String) eventData.get('{{fieldKey}}');
        event.RecordId__c = (String) eventData.get('recordId');
        event.Timestamp__c = DateTime.now();

        Database.SaveResult sr = EventBus.publish(event);
        if (!sr.isSuccess()) {
            throw new EventPublishException('Failed to publish event: ' + sr.getErrors());
        }
    }

    public class EventPublishException extends Exception {}
}
```

#### Usage Examples

**Single Event**:
```apex
Map<String, Object> eventData = new Map<String, Object>{
    'recordId' => '001xx000003DXXXAAA',
    'status' => 'Completed',
    'amount' => 1000.00
};
OrderStatusPublisher.publishSingleEvent(eventData);
```

**Bulk Events**:
```apex
List<Order_Status__e> events = new List<Order_Status__e>();

for (Order order : orders) {
    Order_Status__e event = new Order_Status__e();
    event.RecordId__c = order.Id;
    event.Status__c = order.Status;
    event.Timestamp__c = DateTime.now();
    events.add(event);
}

OrderStatusPublisher.publishEvents(events);
```

#### Best Practices for Publishing

1. **Batch Events**: Publish up to 2,000 events per transaction (governor limit)
2. **Error Handling**: Always check `Database.SaveResult` for failures
3. **Transaction Context**: Use `PublishAfterCommit` to ensure events only fire on successful transactions
4. **Field Population**: Populate all required fields before publishing
5. **Logging**: Log failed event publishes for debugging

---

### Event Subscriber Trigger

**Template**: `assets/platform-events/event-subscriber-trigger.trigger`

#### Standard Volume Subscriber

```apex
trigger {{EventName}}Subscriber on {{EventName}}__e (after insert) {
    // Get replay ID for resumption
    String lastReplayId = '';

    for ({{EventName}}__e event : Trigger.new) {
        // Store replay ID for potential resume
        lastReplayId = event.ReplayId;

        try {
            // Process event
            {{EventName}}Handler.processEvent(event);
        } catch (Exception e) {
            // Log error but don't throw - allow other events to process
            System.debug(LoggingLevel.ERROR,
                'Event processing error: ' + e.getMessage() +
                ' ReplayId: ' + event.ReplayId);
        }
    }
}
```

#### High-Volume Subscriber (with Resume Checkpoint)

```apex
trigger {{EventName}}Subscriber on {{EventName}}__e (after insert) {
    String lastReplayId = '';

    for ({{EventName}}__e event : Trigger.new) {
        lastReplayId = event.ReplayId;

        try {
            {{EventName}}Handler.processEvent(event);
        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR,
                'Event processing error: ' + e.getMessage() +
                ' ReplayId: ' + event.ReplayId);
        }
    }

    // Set resume checkpoint for high-volume events
    // Allows resuming from this point if subscriber fails
    EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
}
```

#### Event Handler Class

```apex
public with sharing class {{EventName}}Handler {

    public static void processEvent({{EventName}}__e event) {
        // Extract event data
        String recordId = event.RecordId__c;
        String status = event.Status__c;
        DateTime timestamp = event.Timestamp__c;

        System.debug('Processing event - RecordId: ' + recordId +
                     ', Status: ' + status +
                     ', ReplayId: ' + event.ReplayId);

        // Business logic
        updateRelatedRecords(recordId, status);
        syncToExternalSystem(recordId, status);
    }

    private static void updateRelatedRecords(String recordId, String status) {
        // Update related records based on event
        List<Task> tasks = [
            SELECT Id, Status
            FROM Task
            WHERE WhatId = :recordId
            WITH USER_MODE
        ];

        for (Task t : tasks) {
            t.Status = status;
        }

        update as user tasks;
    }

    private static void syncToExternalSystem(String recordId, String status) {
        // Queue async callout
        Map<String, Object> payload = new Map<String, Object>{
            'recordId' => recordId,
            'status' => status
        };
        System.enqueueJob(new ExternalSyncQueueable(payload));
    }
}
```

---

<a id="high-volume-vs-standard-volume-events"></a>

### High-Volume vs Standard-Volume Events

| Feature | Standard-Volume | High-Volume |
|---------|----------------|-------------|
| **Throughput** | ~2,000 events/hour | Millions/day |
| **Delivery** | Exactly-once | At-least-once (may deliver duplicates) |
| **Retention** | 3 days (72 hours) | 24 hours |
| **Replay** | ReplayId from last 3 days | ReplayId from last 24 hours |
| **Use Case** | Low-volume integrations, workflows | IoT, real-time analytics, high-traffic |
| **Cost** | Included in platform | Additional licensing |

#### When to Use High-Volume Events

- **IoT Data**: Sensor data, device telemetry
- **Real-Time Analytics**: Clickstream, user behavior tracking
- **High-Traffic Systems**: E-commerce order processing, stock updates
- **Event Sourcing**: Append-only event logs

#### When to Use Standard-Volume Events

- **Business Workflows**: Order status updates, approval processes
- **Integration Events**: Sync to external CRM, ERP systems
- **Notifications**: Email triggers, Slack notifications
- **Audit Trails**: Record-level change notifications

---

## Change Data Capture (CDC)

Change Data Capture publishes change events whenever records are created, updated, deleted, or undeleted in Salesforce. CDC events are published automatically—no custom code needed.

### CDC Enablement

#### Enable via Setup UI

1. Navigate to **Setup** → **Integrations** → **Change Data Capture**
2. Select objects to enable (Standard or Custom)
3. Save

#### Enable via Metadata API

**File**: `force-app/main/default/changeDataCaptures/AccountChangeEvent.cdc-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ChangeDataCapture xmlns="http://soap.sforce.com/2006/04/metadata">
    <entityName>Account</entityName>
    <isEnabled>true</isEnabled>
</ChangeDataCapture>
```

#### Channel Naming Convention

CDC channels follow the pattern: `{{ObjectAPIName}}ChangeEvent`

**Examples**:
- `AccountChangeEvent` (Standard object)
- `Order__ChangeEvent` (Custom object)
- `OpportunityChangeEvent`
- `Contact_Request__ChangeEvent`

---

### CDC Subscriber Trigger

**Template**: `assets/cdc/cdc-subscriber-trigger.trigger`

#### Basic CDC Subscriber

```apex
trigger {{ObjectName}}CDCSubscriber on {{ObjectName}}ChangeEvent (after insert) {

    for ({{ObjectName}}ChangeEvent event : Trigger.new) {
        // Get change event header
        EventBus.ChangeEventHeader header = event.ChangeEventHeader;

        String changeType = header.getChangeType();
        List<String> changedFields = header.getChangedFields();
        String recordId = header.getRecordIds()[0]; // First record ID

        System.debug('CDC Event - Type: ' + changeType +
                     ', RecordId: ' + recordId +
                     ', Changed Fields: ' + changedFields);

        // Route based on change type
        switch on changeType {
            when 'CREATE' {
                // Handle new record
                {{ObjectName}}CDCHandler.handleCreate(event);
            }
            when 'UPDATE' {
                // Handle update
                {{ObjectName}}CDCHandler.handleUpdate(event, changedFields);
            }
            when 'DELETE' {
                // Handle delete
                {{ObjectName}}CDCHandler.handleDelete(recordId);
            }
            when 'UNDELETE' {
                // Handle undelete
                {{ObjectName}}CDCHandler.handleUndelete(event);
            }
        }
    }
}
```

#### ChangeEventHeader Fields

| Field | Type | Description |
|-------|------|-------------|
| `getChangeType()` | String | CREATE, UPDATE, DELETE, UNDELETE |
| `getRecordIds()` | List<String> | Record IDs affected (usually 1, up to 5 for related changes) |
| `getChangedFields()` | List<String> | Field API names that changed (UPDATE only) |
| `getCommitTimestamp()` | Long | Transaction commit timestamp |
| `getCommitUser()` | String | User ID who made the change |
| `getCommitNumber()` | Long | Monotonically increasing commit number |
| `getEntityName()` | String | Object API name |

---

### CDC Handler Service

**Template**: `assets/cdc/cdc-handler.cls`

```apex
public with sharing class {{ObjectName}}CDCHandler {

    public static void handleCreate({{ObjectName}}ChangeEvent event) {
        // Sync to external system on create
        Map<String, Object> payload = buildPayload(event);
        System.enqueueJob(new ExternalSystemSyncQueueable(payload, 'CREATE'));
    }

    public static void handleUpdate({{ObjectName}}ChangeEvent event, List<String> changedFields) {
        // Only sync if relevant fields changed
        Set<String> fieldsToWatch = new Set<String>{'Name', 'Status__c', 'Amount__c'};

        Boolean relevantChange = false;
        for (String field : changedFields) {
            if (fieldsToWatch.contains(field)) {
                relevantChange = true;
                break;
            }
        }

        if (relevantChange) {
            Map<String, Object> payload = buildPayload(event);
            payload.put('changedFields', changedFields);
            System.enqueueJob(new ExternalSystemSyncQueueable(payload, 'UPDATE'));
        }
    }

    public static void handleDelete(String recordId) {
        Map<String, Object> payload = new Map<String, Object>{'recordId' => recordId};
        System.enqueueJob(new ExternalSystemSyncQueueable(payload, 'DELETE'));
    }

    public static void handleUndelete({{ObjectName}}ChangeEvent event) {
        handleCreate(event); // Treat undelete like create
    }

    private static Map<String, Object> buildPayload({{ObjectName}}ChangeEvent event) {
        return new Map<String, Object>{
            'recordId' => event.ChangeEventHeader.getRecordIds()[0],
            'commitTimestamp' => event.ChangeEventHeader.getCommitTimestamp(),
            'commitUser' => event.ChangeEventHeader.getCommitUser(),
            // Add event field values
            'name' => event.Name,
            'status' => event.Status__c
            // Add more fields
        };
    }
}
```

---

<a id="field-specific-change-detection"></a>

### Field-Specific Change Detection

#### Filtering by Changed Fields

```apex
public static void handleUpdate(AccountChangeEvent event, List<String> changedFields) {
    // Only process if billing address changed
    Set<String> billingFields = new Set<String>{
        'BillingStreet',
        'BillingCity',
        'BillingState',
        'BillingPostalCode',
        'BillingCountry'
    };

    Boolean billingChanged = false;
    for (String field : changedFields) {
        if (billingFields.contains(field)) {
            billingChanged = true;
            break;
        }
    }

    if (billingChanged) {
        updateShippingPartner(event);
    }
}
```

#### Multi-Field Change Logic

```apex
public static void handleUpdate(OpportunityChangeEvent event, List<String> changedFields) {
    Set<String> changedFieldSet = new Set<String>(changedFields);

    // Check if stage AND amount both changed
    if (changedFieldSet.contains('StageName') && changedFieldSet.contains('Amount')) {
        // Alert sales ops about significant deal change
        sendAlert('Deal stage and amount changed', event);
    }

    // Check if close date moved backward
    if (changedFieldSet.contains('CloseDate')) {
        checkCloseDateRegression(event);
    }
}
```

---

## CDC vs Platform Events: When to Use Which

| Use Case | Platform Events | Change Data Capture |
|----------|----------------|---------------------|
| **Custom business events** | **Preferred** | Not applicable |
| **Record change notifications** | Requires custom trigger | **Automatic** (no code) |
| **External system sync** | Both work | **CDC** (lower maintenance) |
| **Custom event fields** | Fully customizable | Limited to object fields |
| **Event filtering** | Filter in publisher code | Filter in subscriber code |
| **Performance overhead** | Manual event creation | Automatic (minimal overhead) |

### Decision Matrix

```
┌───────────────────────────────────────────────────────────────────────┐
│  WHEN TO USE PLATFORM EVENTS vs CHANGE DATA CAPTURE                   │
├───────────────────────────────────────────────────────────────────────┤
│  Use PLATFORM EVENTS when:                                            │
│  • Custom business event (not tied to record changes)                 │
│  • Event needs custom fields not on object                            │
│  • Need to batch/aggregate data before publishing                     │
│  • Publishing from external system to Salesforce                      │
│  • Complex event logic (multi-object aggregation)                     │
│                                                                        │
│  Use CHANGE DATA CAPTURE when:                                        │
│  • Syncing record changes to external system                          │
│  • Audit trail of all record modifications                            │
│  • Real-time replication to data warehouse                            │
│  • Event sourcing from Salesforce objects                             │
│  • Zero-code event publishing required                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Advanced Patterns

### Combining CDC with Callouts

```apex
public with sharing class AccountCDCHandler {

    public static void handleUpdate(AccountChangeEvent event, List<String> changedFields) {
        // Extract data
        String recordId = event.ChangeEventHeader.getRecordIds()[0];
        String accountName = event.Name;

        // Queue async callout to external CRM
        Map<String, Object> payload = new Map<String, Object>{
            'salesforceId' => recordId,
            'name' => accountName,
            'changedFields' => changedFields,
            'timestamp' => event.ChangeEventHeader.getCommitTimestamp()
        };

        System.enqueueJob(new CRMSyncQueueable(payload));
    }
}
```

### Event Replay with Stored ReplayId

```apex
public with sharing class EventReplayService {

    @future(callout=true)
    public static void replayFromLastCheckpoint(String eventChannel) {
        // Get last stored replay ID
        Event_Checkpoint__c checkpoint = [
            SELECT ReplayId__c
            FROM Event_Checkpoint__c
            WHERE Channel__c = :eventChannel
            LIMIT 1
        ];

        if (checkpoint != null) {
            // Use stored replay ID to resume from last successful event
            // Note: Replay is typically done via API/streaming API, not Apex
            System.debug('Last replay ID: ' + checkpoint.ReplayId__c);
        }
    }

    public static void storeCheckpoint(String channel, String replayId) {
        Event_Checkpoint__c checkpoint = new Event_Checkpoint__c(
            Channel__c = channel,
            ReplayId__c = replayId,
            Last_Updated__c = DateTime.now()
        );
        upsert checkpoint Channel__c;
    }
}
```

### Error Handling with Dead Letter Queue

```apex
trigger OrderEventSubscriber on Order_Status__e (after insert) {
    for (Order_Status__e event : Trigger.new) {
        try {
            OrderEventHandler.processEvent(event);
        } catch (Exception e) {
            // Log to dead letter queue for manual review
            Event_Error_Log__c errorLog = new Event_Error_Log__c(
                Event_Type__c = 'Order_Status__e',
                Replay_Id__c = event.ReplayId,
                Error_Message__c = e.getMessage(),
                Event_Payload__c = JSON.serialize(event),
                Occurred_At__c = DateTime.now()
            );
            insert as user errorLog;
        }
    }
}
```

---

## Best Practices

### Platform Events

1. **Batch Publishing**: Publish events in batches (up to 2,000 per transaction)
2. **Idempotent Subscribers**: Design subscribers to handle duplicate events (especially for high-volume)
3. **ReplayId Tracking**: Store ReplayIds for resume capability
4. **Error Isolation**: Catch exceptions in subscriber loops to process remaining events
5. **Resume Checkpoints**: Use `setResumeCheckpoint()` for high-volume events

### Change Data Capture

1. **Field Filtering**: Only process relevant field changes to reduce processing overhead
2. **Async Processing**: Use Queueable/Future for callouts or long-running operations
3. **ChangeType Routing**: Use switch statements for different change types
4. **RecordIds Array**: Handle multiple RecordIds (CDC can batch related changes)
5. **Commit Metadata**: Use `getCommitTimestamp()` and `getCommitUser()` for audit trails

---

## Governor Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Platform Events published/transaction | 2,000 | Both Standard and High-Volume |
| Platform Event delivery | Asynchronous | Delivered to subscribers after commit |
| CDC events/hour (per object) | 250,000 | Auto-throttled if exceeded |
| Event message size | 1 MB | Total size of all fields |
| Event retention (Standard) | 3 days | ReplayId available for 72 hours |
| Event retention (High-Volume) | 24 hours | ReplayId available for 24 hours |

---

## Testing Event-Driven Integrations

### Platform Event Test

```apex
@isTest
private class OrderEventTest {

    @isTest
    static void testEventPublish() {
        Test.startTest();

        Order_Status__e event = new Order_Status__e(
            RecordId__c = '006xx000000XXXAAA',
            Status__c = 'Completed'
        );
        Database.SaveResult sr = EventBus.publish(event);

        Test.stopTest();

        System.assert(sr.isSuccess(), 'Event should publish successfully');
    }

    @isTest
    static void testEventSubscriber() {
        // Subscriber triggers execute synchronously in tests
        Test.startTest();

        Order_Status__e event = new Order_Status__e(
            RecordId__c = '006xx000000XXXAAA',
            Status__c = 'Completed'
        );
        EventBus.publish(event);

        Test.stopTest();

        // Verify subscriber logic executed
        // (check that handler updated related records)
    }
}
```

### CDC Test

```apex
@isTest
private class AccountCDCTest {

    @isTest
    static void testAccountUpdate() {
        Account acc = new Account(Name = 'Test Account');
        insert acc;

        Test.startTest();

        acc.BillingCity = 'San Francisco';
        update acc;

        Test.stopTest();

        // CDC events don't fire in test context
        // Must test handler methods directly
        AccountChangeEvent mockEvent = new AccountChangeEvent();
        // Note: Can't instantiate ChangeEvent in Apex
        // Test handler logic with mock data instead
    }
}
```

---

## Pub/Sub API (Recommended for External Consumers)

The Pub/Sub API is the **recommended mechanism** for external systems subscribing to Platform Events and CDC events. It replaces the legacy Streaming API (CometD).

### Why Pub/Sub API

| Feature | Pub/Sub API | Legacy Streaming API |
|---------|-------------|---------------------|
| **Protocol** | gRPC (binary, high performance) | CometD (long-polling, HTTP overhead) |
| **Authentication** | OAuth 2.0 | Session-based |
| **Event Types** | Platform Events, CDC, Custom Channels | PushTopic, Generic Events |
| **Status** | **Current** | **Deprecated — no new investments** |

### Subscription Modes

- **Subscribe**: Stream events from a given replay ID forward
- **PublishStream**: Bi-directional — publish events via gRPC
- **ManagedSubscribe**: Salesforce manages replay state (simplest)

### LWC Internal Subscription

For Lightning Web Components, use the `empApi` module:

```javascript
import { subscribe, unsubscribe, onError } from 'lightning/empApi';

connectedCallback() {
    subscribe('/event/Order_Status__e', -1, (response) => {
        this.handleEvent(response.data.payload);
    }).then((sub) => { this.subscription = sub; });
}

disconnectedCallback() {
    unsubscribe(this.subscription);
}
```

> **Note**: `empApi` uses CometD internally but is the supported LWC API. For external consumers, always use the gRPC-based Pub/Sub API.

---

## Platform Event Anti-Patterns

### 1. Publishing from Trigger on Same Event Object → Infinite Loop

```apex
// ❌ WRONG: Trigger on Order_Status__e publishes Order_Status__e
trigger OrderStatusSubscriber on Order_Status__e (after insert) {
    for (Order_Status__e event : Trigger.new) {
        // This creates an infinite loop!
        EventBus.publish(new Order_Status__e(Status__c = 'Processed'));
    }
}
```

**Fix**: Never publish the same event type from its own subscriber trigger. Use a different event type or update a record instead.

### 2. PublishImmediately When Data Integrity Matters

```apex
// ❌ WRONG: Event fires even if the transaction rolls back
Order_Status__e event = new Order_Status__e();
event.Status__c = 'Completed';
// publishBehavior = PublishImmediately in event definition
EventBus.publish(event);

// If subsequent DML fails, the event was already published
// External system thinks order is "Completed" but it's not
```

**Fix**: Use `PublishAfterCommit` (the default) when the event represents a state change that depends on the transaction succeeding.

### 3. Using Platform Events for Synchronous-Style Flow Orchestration

```
// ❌ WRONG: Using events to simulate synchronous request/response
Flow A → Publish "Request" Event → Subscriber triggers Flow B → Publish "Response" Event → ???
```

**Fix**: Platform Events are asynchronous and unordered. For synchronous orchestration, use Subflows, @InvocableMethod, or direct Apex calls. Events are for decoupled, fire-and-forget communication.

### 4. Oversized Event Payloads

> **1 MB message size limit.** Balance payload size — smaller = faster delivery, larger = fewer API calls. Include record IDs and essential context; let consumers query Salesforce for full records if needed.

---

## Related Resources

- [Callout Patterns](./callout-patterns.md) - REST and SOAP callout implementations
- [Event-Driven Architecture Guide](./event-driven-architecture-guide.md) - EDA patterns, Pub/Sub API deep dive, monitoring
- [Main Skill Documentation](../SKILL.md) - building-sf-integrations overview
- [Platform Event Templates](../assets/platform-events/) - Event definitions and triggers
- [CDC Templates](../assets/cdc/) - Change Data Capture triggers
