<!-- Parent: building-sf-integrations/SKILL.md -->
# Event-Driven Architecture Guide

> **Source**: Salesforce Architect Decision Guides — Event-Driven Architecture, Async Processing
> **Related**: [event-patterns.md](./event-patterns.md) | [callout-patterns.md](./callout-patterns.md)

---

## Overview

Event-Driven Architecture (EDA) decouples producers from consumers, enabling scalable, resilient integrations. Salesforce supports multiple event mechanisms — choosing the right one depends on volume, latency, and consumer location.

---

## 5 Core EDA Patterns

### Pattern Comparison Matrix

| Pattern | Description | Salesforce Implementation | Best For |
|---------|-------------|--------------------------|----------|
| **Pub/Sub** | Publisher emits, multiple subscribers consume | Platform Events + Pub/Sub API | Multi-consumer notifications, cross-system sync |
| **Fanout** | One event → multiple independent consumers | Platform Events + multiple subscribers | Parallel processing, diverse downstream systems |
| **Passed Messages** | Event carries data payload for consumer processing | Platform Events with rich fields | External systems needing full context in message |
| **Streaming** | Continuous data feed for real-time consumers | CDC + Pub/Sub API | Data replication, real-time dashboards |
| **Queueing** | Ordered, guaranteed-delivery message processing | Platform Events (High-Volume) with checkpoints | Sequential processing, backpressure handling |

### When to Use Each

**Pub/Sub**: Default choice for most event-driven integrations. Works for both internal (Apex triggers) and external (Pub/Sub API) consumers.

**Fanout**: When a single business event (e.g., "Order Placed") needs to notify billing, shipping, analytics, and notifications simultaneously.

**Passed Messages**: When the consumer needs all context in the event itself (no callback to Salesforce). Keep payloads lean — 1 MB limit.

**Streaming**: For data replication to warehouses or lakes. CDC + Pub/Sub API replaces legacy Streaming API.

**Queueing**: When processing order matters and you need backpressure handling. Use High-Volume Platform Events with resume checkpoints.

---

## Pub/Sub API (Recommended External Subscription)

The Pub/Sub API is the **recommended mechanism for external consumers** subscribing to Platform Events and CDC events. It replaces the legacy Streaming API (CometD).

### Key Characteristics

| Feature | Pub/Sub API | Legacy Streaming API (Deprecated) |
|---------|-------------|----------------------------------|
| **Protocol** | gRPC | CometD (long-polling) |
| **Authentication** | OAuth 2.0 | Session-based |
| **Event Types** | Platform Events, CDC, Custom Channels | PushTopic, Generic Events, Platform Events |
| **Performance** | High throughput, binary protocol | Limited by long-polling overhead |
| **Status** | **Current — use for all new development** | Deprecated — no new investments |

### Subscription Modes

- **Subscribe**: Stream events from a given replay ID forward
- **PublishStream**: Bi-directional — publish events via gRPC (no Apex needed)
- **ManagedSubscribe**: Salesforce manages replay state (simplest for external consumers)

### External Consumer Architecture

```
Salesforce Org
  └── Platform Event / CDC Event
        └── Pub/Sub API (gRPC endpoint)
              └── External Consumer (Java, Python, Node.js, Go)
                    ├── Process event
                    ├── Commit replay ID
                    └── Handle failures with retry
```

### LWC Subscription (Internal)

For Lightning Web Components subscribing to Platform Events, use **empApi**:

```javascript
import { subscribe, unsubscribe, onError } from 'lightning/empApi';

const channelName = '/event/Order_Status__e';
let subscription = {};

connectedCallback() {
    subscribe(channelName, -1, (response) => {
        console.log('Event received:', JSON.stringify(response));
        this.handleEvent(response.data.payload);
    }).then((sub) => {
        subscription = sub;
    });

    onError((error) => {
        console.error('empApi error:', JSON.stringify(error));
    });
}

disconnectedCallback() {
    unsubscribe(subscription);
}
```

---

## Event Relays to AWS EventBridge

Salesforce Event Relays forward Platform Events to AWS EventBridge, enabling cloud-native event processing.

### Architecture

```
Salesforce Platform Event
  └── Event Relay Definition (Metadata)
        └── AWS EventBridge Partner Event Source
              ├── AWS Lambda
              ├── AWS SQS
              ├── AWS Step Functions
              └── Any EventBridge target
```

### When to Use

- AWS-native architecture needing Salesforce events
- Complex event processing requiring AWS services (Step Functions, SQS, SNS)
- Fan-out to multiple AWS consumers from a single Salesforce event
- Event archival in AWS S3 or data lakes

### Limitations

- One-way only (Salesforce → AWS)
- Adds latency (~seconds) compared to direct Pub/Sub API
- Requires AWS account configuration and IAM setup
- Platform Event limits still apply on the Salesforce side

---

## Apache Kafka on Heroku

For organizations needing long-retention, high-throughput event streaming beyond Platform Event limits.

### Comparison with Platform Events

| Feature | Platform Events | Kafka on Heroku |
|---------|----------------|-----------------|
| **Retention** | 24h (HV) / 72h (SV) | 1-6 weeks (configurable) |
| **Throughput** | Millions/day (HV) | Millions/second |
| **Consumer groups** | Limited | Unlimited |
| **Replay** | ReplayId-based | Offset-based, topic-level |
| **Cost** | Included / Platform Event add-on | Heroku Kafka add-on |

### When to Choose Kafka

- Retention > 72 hours required
- Need multiple independent consumer groups
- Event throughput exceeds Platform Event limits
- Existing Kafka ecosystem in organization
- Need topic partitioning for ordered processing

### Integration Pattern

```
Salesforce → Platform Event → Apex/Flow subscriber → Heroku Kafka producer
                                                        └── Consumer Group A (analytics)
                                                        └── Consumer Group B (data lake)
                                                        └── Consumer Group C (external CRM)
```

---

## When NOT to Use Events

Events are not always the right choice. Prefer synchronous patterns when:

| Scenario | Why Not Events | Better Alternative |
|----------|---------------|-------------------|
| **Need synchronous response** | Events are async — no return value | REST callout with Named Credential |
| **Infrequent data changes** | Event infrastructure overhead not justified | Scheduled batch sync |
| **Target system lacks event support** | Consumer can't subscribe to events | Outbound Messages or REST callout |
| **Simple record sync** | Over-engineering for basic needs | Salesforce Connect / External Objects |
| **Data volume < 100 records/day** | Platform Event overhead unnecessary | Scheduled Flow with REST callout |

---

## High-Volume Outbound Pattern

For scenarios requiring high-volume data push to external systems:

> **Do NOT use async Apex directly for high-volume outbound.** Apex async limits (250K daily Queueable, 250K daily @future) are shared across all org operations. Consuming them for outbound sync starves other automation.

### Recommended Pattern: Middleware + Platform Events

```
Salesforce Record Change
  └── After-Save Flow / Trigger
        └── Publish Platform Event (lightweight payload)
              └── External Middleware (MuleSoft, Pub/Sub API consumer)
                    ├── Enrich data (callback to Salesforce REST API if needed)
                    ├── Transform to target format
                    ├── Deliver to target system with retry logic
                    └── Report status back via Platform Event or REST callback
```

### Benefits

- **No Apex async limit consumption** — events don't count against daily limits
- **Middleware handles retries** — exponential backoff, dead letter queues
- **Scalable** — middleware scales independently of Salesforce
- **Observable** — middleware provides logging, monitoring, alerting

---

## Monitoring Event-Driven Systems

### AsyncApexJob Monitoring

Query job status for async Apex that processes events:

```apex
List<AsyncApexJob> jobs = [
    SELECT Id, JobType, Status, NumberOfErrors, MethodName, CreatedDate
    FROM AsyncApexJob
    WHERE CreatedDate = TODAY
    AND Status IN ('Failed', 'Aborted')
    ORDER BY CreatedDate DESC
    LIMIT 50
];
```

> **Polling limit**: AsyncApexJob queries are subject to SOQL limits. Max polling frequency: every 5 minutes.

### Platform Event Metrics

- **Setup → Platform Events → Usage**: View publish/subscribe counts
- **EventBusSubscriber**: Query for subscriber status and position
- **Proactive Monitoring**: Set up Flow or Apex to alert on failed event processing

```apex
// Check subscriber lag
List<EventBusSubscriber> subs = [
    SELECT Name, Position, Retries, LastError, Status
    FROM EventBusSubscriber
    WHERE Topic = 'Order_Status__e'
];
```

### Key Metrics to Monitor

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Failed events | `EventBusSubscriber.Retries` | > 3 consecutive retries |
| Subscriber lag | `EventBusSubscriber.Position` vs latest ReplayId | Lag > 1000 events |
| Async job failures | `AsyncApexJob.NumberOfErrors` | Any failure |
| Event publish errors | `Database.SaveResult` in publisher | Any failure |
| Daily event usage | Setup → Company Information → Platform Event Usage | > 80% of allocation |

---

## Summary: EDA Decision Tree

```
Need real-time data sync?
  ├── YES → Is consumer external?
  │    ├── YES → Pub/Sub API + Platform Events (or CDC for record changes)
  │    └── NO → Platform Event trigger subscriber (or empApi for LWC)
  └── NO → Is volume high (>10K records/day)?
       ├── YES → Middleware + Platform Events (high-volume outbound pattern)
       └── NO → Scheduled batch sync (simplest, most maintainable)
```
