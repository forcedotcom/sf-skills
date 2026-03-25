# Flow-LWC-Apex Triangle: Apex Perspective

The **Triangle Architecture** is a foundational Salesforce pattern where Flow, LWC, and Apex work together. This guide focuses on the **Apex role** in this architecture.

---

## Architecture Overview

```
                         ┌─────────────────────────────────────┐
                         │              FLOW                   │
                         │         (Orchestrator)              │
                         └───────────────┬─────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              │ screens                  │ actionCalls              │
              │ <componentInstance>      │ actionType="apex"        │
              │                          │                          │
              ▼                          ▼                          ▲
┌─────────────────────────┐    ┌─────────────────────────┐         │
│          LWC            │    │         APEX            │         │
│     (UI Component)      │───▶│   (Business Logic)      │─────────┘
│                         │    │                         │
│ • Rich UI/UX            │    │ • @InvocableMethod  ◀── YOU ARE HERE
│ • User Interaction      │    │ • @AuraEnabled          │
│                         │    │ • Complex Logic         │
│                         │    │ • DML Operations        │
│                         │    │ • Integration           │
└─────────────────────────┘    └─────────────────────────┘
              │                          ▲
              │      @AuraEnabled        │
              │      wire / imperative   │
              └──────────────────────────┘
```

---

## Apex's Role in the Triangle

| Communication Path | Apex Annotation | Direction |
|-------------------|-----------------|-----------|
| Flow → Apex | `@InvocableMethod` | Request/Response |
| Apex → Flow | `@InvocableVariable` | Return values |
| LWC → Apex | `@AuraEnabled` | Async call |
| Apex → LWC | Return value | Response |

---

## Pattern 1: @InvocableMethod for Flow

**Use Case**: Complex business logic, DML, or external integrations called from Flow.

For the full @InvocableMethod pattern — Request/Response wrappers, bulkification, error handling, and supported types — see [flow-integration.md](flow-integration.md).

Key points from the Apex perspective in the triangle:
- Flow calls Apex via `actionCalls` with `actionType="apex"`
- Always use `List<Request>` → `List<Response>` (bulk-safe)
- Return errors in Response fields — throwing exceptions triggers Flow's Fault path
- Use `WITH USER_MODE` in SOQL for automatic CRUD/FLS enforcement

---

## Pattern 2: @AuraEnabled for LWC

**Use Case**: LWC needs data or operations beyond Flow context.

```
┌─────────┐     @wire         ┌─────────┐
│   LWC   │ ────────────────▶ │  APEX   │
│         │    imperative     │@Aura    │
│         │ ◀──────────────── │Enabled  │
│         │   Promise/data    │         │
└─────────┘                   └─────────┘
```

### Apex Controller

```apex
public with sharing class RecordController {

    @AuraEnabled(cacheable=true)
    public static List<Record__c> getRecords(Id parentId) {
        return [
            SELECT Id, Name, Status__c
            FROM Record__c
            WHERE Parent__c = :parentId
            WITH USER_MODE
        ];
    }

    @AuraEnabled
    public static Map<String, Object> processRecord(Id recordId) {
        // Process logic (DML operations)
        return new Map<String, Object>{
            'isSuccess' => true,
            'recordId' => recordId
        };
    }
}
```

### Key Differences

| Annotation | Cacheable | Use For |
|------------|-----------|---------|
| `@AuraEnabled(cacheable=true)` | Yes | Read-only queries (SOQL) |
| `@AuraEnabled` | No | DML operations, mutations |

---

## Testing Triangle Components

For testing `@InvocableMethod` classes, see [flow-integration.md — Testing Invocable Methods](flow-integration.md#testing-invocable-methods).


## Deployment Order

When deploying integrated triangle solutions:

```
1. APEX CLASSES         ← Deploy FIRST
   └── @InvocableMethod classes
   └── @AuraEnabled controllers

2. LWC COMPONENTS
   └── Depend on Apex controllers

3. FLOWS
   └── Reference deployed Apex classes
   └── Reference deployed LWC components
```

---

## Common Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Non-bulkified Invocable | Fails for multi-record Flows | Use `List<Request>` → `List<Response>` |
| Missing faultConnector handling | Exceptions crash Flow | Return error in Response, add fault path |
| Cacheable method with DML | Runtime error | Remove `cacheable=true` for mutations |
| Mixing concerns | Hard to validate | Separate controller (LWC) from service (Flow) classes |

---

## Decision Matrix

| Scenario | Use @InvocableMethod | Use @AuraEnabled |
|----------|---------------------|------------------|
| Called from Flow | ✅ | ❌ |
| Called from LWC | ❌ | ✅ |
| Needs bulkification | ✅ (always bulk) | Optional |
| Read-only query | Either | ✅ (cacheable) |
| DML operations | ✅ | ✅ |
| External callout | ✅ | ✅ |

---

## Related Documentation

| Topic | Location |
|-------|----------|
| Flow integration guide | [flow-integration.md](flow-integration.md) |
| Automation density | [automation-density-guide.md](automation-density-guide.md) |
