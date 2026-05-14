<!-- Parent: building-sf-integrations/SKILL.md -->
# Platform Events Guide

## Overview

Platform Events enable event-driven architecture in Salesforce. They provide a scalable, asynchronous messaging system for real-time integrations.

## Event Types

### Standard Volume

- Up to ~2,000 events per hour
- Included in all Salesforce editions
- Standard delivery guarantees

### High Volume

- Millions of events per day
- At-least-once delivery
- 24-hour retention for replay
- May require additional entitlement

## When to Use Platform Events

| Scenario | Platform Events | Other Options |
|----------|-----------------|---------------|
| Real-time notifications | ✅ Best choice | - |
| Decoupled integrations | ✅ Best choice | - |
| High-volume streaming | ✅ High Volume | Change Data Capture |
| Simple record sync | Consider | Change Data Capture |
| External system notifications | ✅ Best choice | - |
| Internal process triggers | ✅ Good choice | Process Builder, Flow |

## Creating Platform Events

### Via Metadata (Recommended)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>HighVolume</eventType>
    <label>Order Update Event</label>
    <pluralLabel>Order Update Events</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>
    <fields>
        <fullName>Order_Id__c</fullName>
        <label>Order ID</label>
        <type>Text</type>
        <length>18</length>
    </fields>
    <fields>
        <fullName>Status__c</fullName>
        <label>Status</label>
        <type>Text</type>
        <length>50</length>
    </fields>
</CustomObject>
```

### File Location

```
force-app/main/default/objects/Order_Update_Event__e/Order_Update_Event__e.object-meta.xml
```

## Publishing Events

### From Apex

```apex
// Single event
Order_Update_Event__e event = new Order_Update_Event__e();
event.Order_Id__c = orderId;
event.Status__c = 'Shipped';

Database.SaveResult result = EventBus.publish(event);
if (result.isSuccess()) {
    System.debug('Event published: ' + result.getId());
}

// Multiple events
List<Order_Update_Event__e> events = new List<Order_Update_Event__e>();
// ... populate events
List<Database.SaveResult> results = EventBus.publish(events);
```

### From Flow

1. Create Record element
2. Select Platform Event object
3. Map field values

### From Process Builder

1. Add Immediate Action
2. Select "Create a Record"
3. Choose Platform Event

## Subscribing to Events

### Apex Trigger

```apex
trigger OrderUpdateSubscriber on Order_Update_Event__e (after insert) {
    for (Order_Update_Event__e event : Trigger.new) {
        System.debug('Order ' + event.Order_Id__c + ' is now ' + event.Status__c);
        // Process event
    }

    // Set checkpoint for durability
    EventBus.TriggerContext.currentContext().setResumeCheckpoint(
        Trigger.new[Trigger.new.size() - 1].ReplayId
    );
}
```

### Flow (Record-Triggered)

1. Create Platform Event-Triggered Flow
2. Select Platform Event object
3. Build logic with event data

### External (CometD)

External systems can subscribe using CometD streaming:

```
/event/Order_Update_Event__e
```

## Publish Behavior

### PublishAfterCommit (Default)

- Event published after transaction commits
- If transaction rolls back, event NOT published
- **Recommended for most cases**

### PublishImmediately

- Event published immediately
- Event still published even if transaction rolls back
- Use when external system must be notified regardless of outcome

## Durability & Replay

### Replay ID

Each event has a unique `ReplayId` for tracking and replay:

```apex
String replayId = event.ReplayId;
```

### Resume Checkpoint

Set checkpoint to ensure durability:

```apex
// In trigger
EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
```

If trigger fails after checkpoint, processing resumes from that point.

### Retention

- High Volume events: 24 hours
- Standard Volume: 24 hours

## Best Practices

### Publishing

1. **Batch events** when publishing multiple
2. **Check SaveResults** for publish failures
3. **Use meaningful correlation IDs** for tracking
4. **Include timestamp** for ordering
5. **Keep payloads small** - use IDs, not full records

### Subscribing

1. **Always set resume checkpoint** in triggers
2. **Don't throw exceptions** - catch and log errors
3. **Process idempotently** - events may replay
4. **Keep processing lightweight** - queue heavy work
5. **Handle duplicates** using correlation ID

### Design

1. **Event granularity** - not too fine, not too coarse
2. **Include enough context** but not entire records
3. **Version your events** if schema evolves
4. **Document event contracts** for consumers

## Error Handling

### Publish Errors

```apex
List<Database.SaveResult> results = EventBus.publish(events);
for (Integer i = 0; i < results.size(); i++) {
    if (!results[i].isSuccess()) {
        for (Database.Error err : results[i].getErrors()) {
            System.debug('Publish failed: ' + err.getMessage());
        }
    }
}
```

### Subscriber Errors

```apex
trigger MySubscriber on My_Event__e (after insert) {
    for (My_Event__e event : Trigger.new) {
        try {
            processEvent(event);
        } catch (Exception e) {
            // Log error, don't throw
            System.debug('Error processing ' + event.ReplayId + ': ' + e.getMessage());
            // Create error log record
        }
    }

    // Still set checkpoint even if some failed
    EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
}
```

## Monitoring

### Setup → Platform Events

- View event definitions
- Check usage metrics
- Monitor delivery status

### Event Delivery Failures

Check for:
- Unhandled exceptions in triggers
- Apex CPU timeout
- Governor limit errors

### Event Publishing

Query `EventBusSubscriber` for subscription health:

```apex
SELECT Id, Position, ExternalId, Name, Status, Tip
FROM EventBusSubscriber
WHERE Topic = 'Order_Update_Event__e'
```

## Limits

| Limit | Standard Volume | High Volume |
|-------|-----------------|-------------|
| Events per hour | ~2,000 | Millions |
| Retention | 24 hours | 24 hours |
| Max event size | 1 MB | 1 MB |
| Fields per event | 100 | 100 |

## External Integration

### Subscribe from External System

Use CometD client to connect to Streaming API:

```
Endpoint: /cometd/62.0
Channel: /event/Order_Update_Event__e
```

### Publish from External System

Use REST API:

```http
POST /services/data/v66.0/sobjects/Order_Update_Event__e
Content-Type: application/json

{
    "Order_Id__c": "001xx000003NGSFAA4",
    "Status__c": "Shipped"
}
```
