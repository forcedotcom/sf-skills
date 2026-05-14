<!-- Parent: building-sf-integrations/SKILL.md -->
# Change Data Capture (CDC) Guide

## Overview

Change Data Capture publishes change events for Salesforce records, enabling near real-time data synchronization with external systems.

## How CDC Works

```
┌─────────────────────────────────────────────────────────────────┐
│  CHANGE DATA CAPTURE FLOW                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Record Created/Updated/Deleted in Salesforce                │
│     ↓                                                           │
│  2. Salesforce generates Change Event                           │
│     ↓                                                           │
│  3. Event published to {{Object}}ChangeEvent channel            │
│     ↓                                                           │
│  4. Apex Trigger or External Subscriber receives event          │
│     ↓                                                           │
│  5. Process event (sync, audit, notify)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## CDC vs Platform Events

| Feature | CDC | Platform Events |
|---------|-----|-----------------|
| Trigger | Automatic on DML | Manual publish |
| Schema | Predefined (object fields) | Custom defined |
| Use Case | Data sync/replication | Custom messaging |
| Control | Limited | Full control |

## Enabling CDC

### Via Setup

1. Go to **Setup → Integrations → Change Data Capture**
2. Select objects to enable
3. Save

### Supported Objects

- Most Standard objects (Account, Contact, Opportunity, etc.)
- Custom objects
- Some system objects (User, Group, etc.)

## Event Channel Names

| Object Type | Channel Name |
|-------------|--------------|
| Standard | `AccountChangeEvent`, `ContactChangeEvent` |
| Custom | `My_Object__ChangeEvent` (append ChangeEvent) |

## Change Event Structure

### ChangeEventHeader

```apex
EventBus.ChangeEventHeader header = event.ChangeEventHeader;

// Available methods
header.getChangeType();       // CREATE, UPDATE, DELETE, UNDELETE
header.getChangedFields();    // List of changed field API names
header.getRecordIds();        // Affected record IDs
header.getEntityName();       // Object API name
header.getCommitNumber();     // Transaction sequence
header.getCommitTimestamp();  // When change occurred
header.getTransactionKey();   // Unique transaction ID
```

### Change Types

| Type | Description | Event Contains |
|------|-------------|----------------|
| CREATE | New record | All field values |
| UPDATE | Record modified | Changed field values only |
| DELETE | Record deleted | Record IDs only |
| UNDELETE | Restored from bin | All field values |
| GAP_* | Events missed | Affected record IDs |
| GAP_OVERFLOW | Too many changes | Entity name |

### Field Values

- **Changed fields**: Contain new values
- **Unchanged fields**: Null
- Use `getChangedFields()` to know what changed

## Subscribing to CDC

### Apex Trigger

```apex
trigger AccountCDC on AccountChangeEvent (after insert) {
    for (AccountChangeEvent event : Trigger.new) {
        EventBus.ChangeEventHeader header = event.ChangeEventHeader;

        String changeType = header.getChangeType();
        List<String> changedFields = header.getChangedFields();
        List<String> recordIds = header.getRecordIds();

        switch on changeType {
            when 'CREATE' {
                // Handle new records
            }
            when 'UPDATE' {
                // Handle updates
            }
            when 'DELETE' {
                // Handle deletions
            }
        }
    }

    // Set checkpoint
    EventBus.TriggerContext.currentContext().setResumeCheckpoint(
        Trigger.new[Trigger.new.size()-1].ReplayId
    );
}
```

### External (CometD)

```
Channel: /data/AccountChangeEvent
```

## Handling Specific Changes

### Filter by Changed Fields

```apex
// Only process if important fields changed
Set<String> importantFields = new Set<String>{'Status__c', 'Amount__c'};
List<String> changedFields = header.getChangedFields();

Boolean relevant = false;
for (String field : changedFields) {
    if (importantFields.contains(field)) {
        relevant = true;
        break;
    }
}

if (!relevant) return;
```

### Get New Values

```apex
// Access field values from event (UPDATE: only changed fields have values)
if (changedFields.contains('Status__c')) {
    String newStatus = event.Status__c;
    // Process status change
}
```

## Gap Events

Gap events indicate missed events:

### Types

| Event | Meaning | Action |
|-------|---------|--------|
| GAP_CREATE | Missed creates | Query and sync records |
| GAP_UPDATE | Missed updates | Query current state |
| GAP_DELETE | Missed deletes | Reconcile with source |
| GAP_UNDELETE | Missed restores | Query and sync |
| GAP_OVERFLOW | Too many changes | Full sync required |

### Handling Gaps

```apex
when 'GAP_CREATE', 'GAP_UPDATE', 'GAP_DELETE', 'GAP_UNDELETE' {
    // Query current state and sync
    List<Account> records = [
        SELECT Id, Name, Status__c
        FROM Account
        WHERE Id IN :header.getRecordIds()
    ];
    syncToExternalSystem(records);
}
when 'GAP_OVERFLOW' {
    // Trigger full sync batch job
    Database.executeBatch(new FullSyncBatch());
}
```

## Replay and Durability

### Retention

CDC events retained for **3 days** (72 hours).

### Replay ID

Each event has unique ReplayId for tracking:

```apex
String replayId = event.ReplayId;
```

### Resume Checkpoint

Critical for durability:

```apex
// Always set checkpoint at end of trigger
EventBus.TriggerContext.currentContext().setResumeCheckpoint(lastReplayId);
```

If trigger fails after checkpoint, processing resumes from that point.

## External Sync Pattern

```apex
public class AccountCDCHandler {

    public static void syncToExternal(AccountChangeEvent event) {
        EventBus.ChangeEventHeader header = event.ChangeEventHeader;

        Map<String, Object> payload = new Map<String, Object>{
            'recordIds' => header.getRecordIds(),
            'operation' => header.getChangeType(),
            'timestamp' => header.getCommitTimestamp(),
            'changedFields' => header.getChangedFields()
        };

        // Add field values for CREATE/UPDATE
        if (header.getChangeType() != 'DELETE') {
            payload.put('name', event.Name);
            payload.put('accountNumber', event.AccountNumber);
            // Add relevant fields
        }

        // Queue async callout
        System.enqueueJob(new ExternalSyncJob(payload));
    }
}
```

## Best Practices

### DO

1. **Set resume checkpoint** in every trigger
2. **Filter by relevant fields** to reduce noise
3. **Handle all change types** including GAPs
4. **Process idempotently** (events may replay)
5. **Use async** for external callouts
6. **Log changes** for debugging

### DON'T

1. **Don't throw exceptions** - catch and log
2. **Don't ignore GAP events** - they indicate data loss
3. **Don't assume single record** - batch DML creates multi-record events
4. **Don't block on external calls** - use Queueable

## Monitoring

### Event Delivery

Check for failures in:
- Setup → Platform Events → Monitor
- Debug logs for triggers

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Missing events | No CDC enabled | Enable in Setup |
| Duplicate processing | No idempotency | Check transactionKey |
| GAP events | Processing too slow | Optimize trigger, scale out |
| Timeout | Heavy processing | Move to async |

## Limits

| Limit | Value |
|-------|-------|
| Objects per org | 100 |
| Events per 15 minutes | Varies by edition |
| Event retention | 3 days (72 hours) |
| Replay window | 3 days |
