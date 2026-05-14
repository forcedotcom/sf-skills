<!-- Parent: generating-lwc-components/SKILL.md -->
# Async Notification Patterns in LWC

This guide covers real-time notification patterns for Lightning Web Components using Platform Events, Change Data Capture, and the Emp API.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ASYNC NOTIFICATION ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐        Platform Events        ┌──────────────┐       │
│   │    Apex      │ ─────────────────────────────▶│     LWC      │       │
│   │  Queueable   │    /event/My_Event__e         │  empApi      │       │
│   └──────────────┘                               └──────────────┘       │
│                                                                          │
│   ┌──────────────┐        Change Data Capture    ┌──────────────┐       │
│   │    DML       │ ─────────────────────────────▶│     LWC      │       │
│   │  Operation   │    /data/AccountChangeEvent   │  empApi      │       │
│   └──────────────┘                               └──────────────┘       │
│                                                                          │
│   Use Cases:                                                             │
│   • Queueable/Batch job completion notification                          │
│   • Real-time record updates across users                                │
│   • External system webhook processing notification                      │
│   • Background AI generation completion                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Emp API Basics

The `lightning/empApi` module enables LWC to subscribe to Streaming API channels.

### Import and Setup

```javascript
import { LightningElement } from 'lwc';
import { subscribe, unsubscribe, onError, setDebugFlag } from 'lightning/empApi';

export default class NotificationListener extends LightningElement {
    subscription = null;
    channelName = '/event/Job_Complete__e';

    connectedCallback() {
        // Enable debug logging (development only)
        setDebugFlag(true);

        // Register global error handler
        this.registerErrorListener();

        // Subscribe to channel
        this.handleSubscribe();
    }

    disconnectedCallback() {
        // CRITICAL: Always unsubscribe to prevent memory leaks
        this.handleUnsubscribe();
    }
}
```

### Subscribe to Platform Events

```javascript
async handleSubscribe() {
    // Callback invoked when event received
    const messageCallback = (response) => {
        console.log('Event received:', JSON.stringify(response));
        this.handleEvent(response.data.payload);
    };

    try {
        // Subscribe and store reference
        this.subscription = await subscribe(
            this.channelName,
            -1,  // -1 = all new events, -2 = replay last 24h
            messageCallback
        );
        console.log('Subscribed to:', JSON.stringify(this.subscription));
    } catch (error) {
        console.error('Subscribe error:', error);
    }
}

handleUnsubscribe() {
    if (this.subscription) {
        unsubscribe(this.subscription, (response) => {
            console.log('Unsubscribed:', JSON.stringify(response));
        });
    }
}

registerErrorListener() {
    onError((error) => {
        console.error('Streaming API error:', JSON.stringify(error));
        // Attempt reconnection after delay
        setTimeout(() => this.handleSubscribe(), 5000);
    });
}
```

---

## Pattern 1: Queueable Job Completion

Notify users when async Apex processing completes.

### Platform Event Definition

```xml
<!-- force-app/main/default/objects/Job_Complete__e/Job_Complete__e.object-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>StandardVolume</eventType>
    <label>Job Complete</label>
    <pluralLabel>Job Complete Events</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>
    <fields>
        <fullName>Job_Id__c</fullName>
        <label>Job ID</label>
        <type>Text</type>
        <length>50</length>
    </fields>
    <fields>
        <fullName>User_Id__c</fullName>
        <label>User ID</label>
        <type>Text</type>
        <length>18</length>
    </fields>
    <fields>
        <fullName>Status__c</fullName>
        <label>Status</label>
        <type>Text</type>
        <length>20</length>
    </fields>
    <fields>
        <fullName>Message__c</fullName>
        <label>Message</label>
        <type>TextArea</type>
    </fields>
    <fields>
        <fullName>Record_Id__c</fullName>
        <label>Record ID</label>
        <type>Text</type>
        <length>18</length>
    </fields>
</CustomObject>
```

### Apex Queueable with Event Publishing

```apex
public class AIGenerationQueueable implements Queueable, Database.AllowsCallouts {

    private Id recordId;
    private Id userId;

    public AIGenerationQueueable(Id recordId, Id userId) {
        this.recordId = recordId;
        this.userId = userId;
    }

    public void execute(QueueableContext context) {
        String status;
        String message;

        try {
            // Perform async work (AI generation, callout, etc.)
            performGeneration();
            status = 'SUCCESS';
            message = 'AI content generated successfully';
        } catch (Exception e) {
            status = 'ERROR';
            message = e.getMessage();
        }

        // Publish completion event
        publishCompletionEvent(status, message);
    }

    private void publishCompletionEvent(String status, String message) {
        Job_Complete__e event = new Job_Complete__e();
        event.Job_Id__c = 'AI_GEN_' + recordId;
        event.User_Id__c = userId;
        event.Status__c = status;
        event.Message__c = message;
        event.Record_Id__c = recordId;

        Database.SaveResult result = EventBus.publish(event);
        if (!result.isSuccess()) {
            System.debug('Event publish failed: ' + result.getErrors());
        }
    }

    private void performGeneration() {
        // AI generation logic...
    }
}
```

### LWC Listener Component

```javascript
// jobCompletionListener.js
import { LightningElement, api } from 'lwc';
import { subscribe, unsubscribe, onError } from 'lightning/empApi';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { refreshApex } from '@salesforce/apex';
import userId from '@salesforce/user/Id';

export default class JobCompletionListener extends LightningElement {
    @api recordId;

    subscription = null;
    channelName = '/event/Job_Complete__e';

    // Reference to wired data for refresh
    wiredResult;

    connectedCallback() {
        this.registerErrorListener();
        this.subscribeToChannel();
    }

    disconnectedCallback() {
        this.unsubscribeFromChannel();
    }

    async subscribeToChannel() {
        if (this.subscription) return;

        try {
            this.subscription = await subscribe(
                this.channelName,
                -1,
                (message) => this.handleMessage(message)
            );
        } catch (error) {
            console.error('Subscription error:', error);
        }
    }

    unsubscribeFromChannel() {
        if (this.subscription) {
            unsubscribe(this.subscription);
            this.subscription = null;
        }
    }

    handleMessage(message) {
        const payload = message.data.payload;

        // Filter: Only process events for current user and record
        if (payload.User_Id__c !== userId) return;
        if (payload.Record_Id__c !== this.recordId) return;

        // Show toast notification
        const variant = payload.Status__c === 'SUCCESS' ? 'success' : 'error';
        this.dispatchEvent(new ShowToastEvent({
            title: payload.Status__c === 'SUCCESS' ? 'Complete' : 'Error',
            message: payload.Message__c,
            variant: variant
        }));

        // Refresh data if successful
        if (payload.Status__c === 'SUCCESS' && this.wiredResult) {
            refreshApex(this.wiredResult);
        }

        // Dispatch custom event for parent components
        this.dispatchEvent(new CustomEvent('jobcomplete', {
            detail: {
                jobId: payload.Job_Id__c,
                status: payload.Status__c,
                message: payload.Message__c
            }
        }));
    }

    registerErrorListener() {
        onError((error) => {
            console.error('EmpApi error:', JSON.stringify(error));
            // Reconnect after delay
            this.subscription = null;
            setTimeout(() => this.subscribeToChannel(), 3000);
        });
    }
}
```

---

## Pattern 2: Real-Time Record Updates (CDC)

Use Change Data Capture to sync UI when records change.

### Enable CDC for Object

1. Setup → Integrations → Change Data Capture
2. Select objects to track
3. Deploy (or enable via metadata)

### CDC Channel Names

| Object Type | Channel Pattern |
|-------------|-----------------|
| Standard Object | `/data/AccountChangeEvent` |
| Custom Object | `/data/My_Object__ChangeEvent` |

### LWC CDC Listener

```javascript
// recordChangeListener.js
import { LightningElement, api, wire } from 'lwc';
import { subscribe, unsubscribe, onError } from 'lightning/empApi';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import { refreshApex } from '@salesforce/apex';

const FIELDS = ['Account.Name', 'Account.Industry', 'Account.AnnualRevenue'];

export default class RecordChangeListener extends LightningElement {
    @api recordId;

    subscription = null;
    channelName = '/data/AccountChangeEvent';

    @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
    wiredRecord;

    get accountName() {
        return getFieldValue(this.wiredRecord.data, 'Account.Name');
    }

    connectedCallback() {
        this.registerErrorListener();
        this.subscribeToChanges();
    }

    disconnectedCallback() {
        if (this.subscription) {
            unsubscribe(this.subscription);
        }
    }

    async subscribeToChanges() {
        try {
            this.subscription = await subscribe(
                this.channelName,
                -1,
                (message) => this.handleChange(message)
            );
        } catch (error) {
            console.error('CDC subscription error:', error);
        }
    }

    handleChange(message) {
        const payload = message.data.payload;
        const changeType = payload.ChangeEventHeader.changeType;
        const recordIds = payload.ChangeEventHeader.recordIds;

        // Only process changes for our record
        if (!recordIds.includes(this.recordId)) return;

        console.log(`Record ${changeType}:`, payload);

        // Refresh the wire
        if (this.wiredRecord) {
            refreshApex(this.wiredRecord);
        }

        // Notify parent
        this.dispatchEvent(new CustomEvent('recordchange', {
            detail: {
                changeType,
                changedFields: payload.ChangeEventHeader.changedFields,
                payload
            }
        }));
    }

    registerErrorListener() {
        onError((error) => {
            console.error('CDC error:', error);
            this.subscription = null;
            setTimeout(() => this.subscribeToChanges(), 5000);
        });
    }
}
```

### CDC Payload Structure

```javascript
{
    "data": {
        "schema": "...",
        "payload": {
            "ChangeEventHeader": {
                "entityName": "Account",
                "recordIds": ["001xx000003ABCDE"],
                "changeType": "UPDATE",  // CREATE, UPDATE, DELETE, UNDELETE
                "changedFields": ["Name", "Industry"],
                "changeOrigin": "com/salesforce/api/soap/58.0",
                "transactionKey": "...",
                "sequenceNumber": 1,
                "commitTimestamp": 1705612800000,
                "commitUser": "005xx000001AAAAA",
                "commitNumber": 123456789
            },
            // Changed field values
            "Name": "Updated Account Name",
            "Industry": "Technology"
        }
    }
}
```

---

## Pattern 3: Multi-User Collaboration

Notify all users viewing the same record.

```javascript
// collaborativeEditor.js
import { LightningElement, api } from 'lwc';
import { subscribe, unsubscribe, onError } from 'lightning/empApi';
import userId from '@salesforce/user/Id';

export default class CollaborativeEditor extends LightningElement {
    @api recordId;

    subscription = null;
    channelName = '/event/Edit_Activity__e';
    activeEditors = [];

    connectedCallback() {
        this.registerErrorListener();
        this.subscribeToActivity();
        this.announcePresence();
    }

    disconnectedCallback() {
        this.announceExit();
        this.unsubscribe();
    }

    async subscribeToActivity() {
        this.subscription = await subscribe(
            this.channelName,
            -1,
            (message) => this.handleActivity(message)
        );
    }

    handleActivity(message) {
        const { Record_Id__c, User_Id__c, User_Name__c, Action__c } = message.data.payload;

        // Ignore our own events, only track this record
        if (User_Id__c === userId || Record_Id__c !== this.recordId) return;

        if (Action__c === 'JOINED') {
            this.addEditor(User_Id__c, User_Name__c);
        } else if (Action__c === 'LEFT') {
            this.removeEditor(User_Id__c);
        } else if (Action__c === 'EDITING') {
            this.showEditingIndicator(User_Name__c, message.data.payload.Field__c);
        }
    }

    addEditor(userId, userName) {
        if (!this.activeEditors.find(e => e.id === userId)) {
            this.activeEditors = [...this.activeEditors, { id: userId, name: userName }];
        }
    }

    removeEditor(userId) {
        this.activeEditors = this.activeEditors.filter(e => e.id !== userId);
    }

    // Call Apex to publish presence event
    announcePresence() {
        // publishEditActivity({ recordId: this.recordId, action: 'JOINED' });
    }

    announceExit() {
        // publishEditActivity({ recordId: this.recordId, action: 'LEFT' });
    }

    unsubscribe() {
        if (this.subscription) {
            unsubscribe(this.subscription);
        }
    }

    registerErrorListener() {
        onError((error) => {
            console.error('Collaboration error:', error);
        });
    }
}
```

---

## Pattern 4: Polling Fallback

When empApi isn't available (Communities, some mobile contexts), use polling.

```javascript
// pollingFallback.js
import { LightningElement, api } from 'lwc';
import checkJobStatus from '@salesforce/apex/JobStatusController.checkJobStatus';

export default class PollingFallback extends LightningElement {
    @api jobId;

    pollingInterval = null;
    pollFrequencyMs = 3000;
    maxAttempts = 60;
    attemptCount = 0;

    connectedCallback() {
        this.startPolling();
    }

    disconnectedCallback() {
        this.stopPolling();
    }

    startPolling() {
        this.pollingInterval = setInterval(() => {
            this.checkStatus();
        }, this.pollFrequencyMs);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    async checkStatus() {
        this.attemptCount++;

        if (this.attemptCount >= this.maxAttempts) {
            this.stopPolling();
            this.handleTimeout();
            return;
        }

        try {
            const result = await checkJobStatus({ jobId: this.jobId });

            if (result.status === 'COMPLETE' || result.status === 'ERROR') {
                this.stopPolling();
                this.handleCompletion(result);
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }

    handleCompletion(result) {
        this.dispatchEvent(new CustomEvent('complete', { detail: result }));
    }

    handleTimeout() {
        this.dispatchEvent(new CustomEvent('timeout'));
    }
}
```

---

## Replay Options

| Replay ID | Behavior |
|-----------|----------|
| `-1` | Only new events (after subscription) |
| `-2` | All stored events (last 24 hours) + new |
| Specific ID | Events after that replay ID |

### Storing Replay Position

```javascript
// For durable subscriptions, store last processed replay ID
handleMessage(message) {
    const replayId = message.data.event.replayId;

    // Process message...

    // Store replay ID for recovery
    this.lastReplayId = replayId;
    localStorage.setItem('myapp_replay_id', replayId);
}

connectedCallback() {
    // Recover from stored position
    const storedReplayId = localStorage.getItem('myapp_replay_id');
    const replayFrom = storedReplayId ? parseInt(storedReplayId, 10) : -1;

    this.subscribeFromReplayId(replayFrom);
}
```

---

## Best Practices

### DO ✅

| Practice | Reason |
|----------|--------|
| Always unsubscribe in `disconnectedCallback` | Prevents memory leaks |
| Filter events by user/record ID | Reduces unnecessary processing |
| Register error handler | Enables reconnection on failure |
| Use `refreshApex` after events | Keeps wire data in sync |
| Set reasonable replay ID | `-1` for real-time, `-2` for recovery |

### DON'T ❌

| Anti-Pattern | Problem |
|--------------|---------|
| Subscribe without unsubscribing | Memory leak, duplicate handlers |
| Process all events without filtering | Performance impact |
| Ignore error handler | Silent failures, no reconnection |
| Mutate wire data directly | Breaks reactivity |
| Use CDC for high-frequency updates | Rate limits, performance |

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No events received | Subscription failed silently | Check error handler, verify channel name |
| Duplicate processing | Component re-mounted | Track subscription state, dedupe by replay ID |
| Events delayed | High server load | Normal behavior, events are async |
| "Handshake denied" | Missing permissions | Verify Streaming API access in profile |
| Events stop after time | Session expired | Handle error event, resubscribe |

---

## Cross-Skill References

| Topic | Resource |
|-------|----------|
| Platform Event definition | [building-sf-integrations/references/platform-events-guide.md](../../building-sf-integrations/references/platform-events-guide.md) |
| Publishing from Apex | [sf-apex/references/best-practices.md](../../sf-apex/references/best-practices.md) |
| State management | [state-management.md](state-management.md) |
| Agentforce Models API | [sf-ai-agentforce/references/models-api.md](../../sf-ai-agentforce/references/models-api.md) |
