<!-- Parent: deploying-metadata/SKILL.md -->
# Trigger Deployment Safety Guide

## Overview

This guide covers deployment considerations for triggers, focusing on cascade failures, atomicity patterns, and async decoupling strategies.

---

## 1. Understanding Cascade Failures

### What Are Cascade Failures?

When an exception in one trigger causes rollback of operations from preceding triggers in the chain.

```
Account Insert → AccountTrigger → ContactTrigger → OpportunityTrigger
                     ✓               ✓                 ✗ (Exception)

                 All three operations ROLL BACK
```

### Default Behavior

- Uncaught exceptions in triggers cause rollback of **all** operations in the transaction
- This includes operations from other triggers that fired successfully
- This behavior may or may not be desired depending on business requirements

### When Cascade Failure is DESIRED

- All operations represent ONE atomic business process
- Example: Order with line items must be complete or not exist
- Same business unit/persona owns all the data

```apex
// DESIRED cascade: Order and OrderItems must both succeed
trigger OrderTrigger on Order__c (after insert) {
    // If this fails, we WANT the Order insert to roll back
    List<OrderItem__c> items = createDefaultLineItems(Trigger.new);
    insert items;  // Exception here rolls back Order insert - GOOD
}
```

### When Cascade Failure is PROBLEMATIC

- Operations represent INDEPENDENT business processes
- Example: Creating account + syncing to external CRM
- Different business units own different parts of the process

```apex
// PROBLEMATIC cascade: CRM sync failure shouldn't prevent Account creation
trigger AccountTrigger on Account (after insert) {
    // If CRM sync fails, Account creation also fails - BAD
    CRMService.syncNewAccounts(Trigger.new);  // Exception here rolls back Account
}
```

---

## 2. Atomicity Patterns

### Explicit Savepoints

Use `Database.setSavepoint()` for explicit transaction control within a single process.

```apex
/**
 * Demonstrates explicit atomicity control for cross-object operations
 */
public class AccountOwnership {

    /**
     * Reassigns all related records when account owner changes.
     * This is an ATOMIC operation - all changes succeed or all roll back.
     */
    public static void reassignRelatedRecords(
        List<Account> accountsWithNewOwner,
        Map<Id, Account> oldAccountsById
    ) {
        // Create savepoint for atomic operation
        Savepoint sp = Database.setSavepoint();

        try {
            Map<Id, Id> newOwnerByAccountId = buildOwnerMap(accountsWithNewOwner);

            // Step 1: Reassign opportunities
            reassignOpportunities(newOwnerByAccountId);

            // Step 2: Reassign cases
            reassignCases(newOwnerByAccountId);

            // Step 3: Create transition tasks
            createOwnerTransitionTasks(accountsWithNewOwner, oldAccountsById);

        } catch (Exception e) {
            // Rollback ALL changes if ANY step fails
            Database.rollback(sp);

            // Log the failure for investigation
            ErrorLogger.log('AccountOwnership.reassignRelatedRecords', e);

            // Re-throw to inform the caller
            throw new AccountOwnershipException(
                'Failed to reassign related records: ' + e.getMessage()
            );
        }
    }
}
```

### When to Use Savepoints

| Scenario | Use Savepoint? | Reason |
|----------|---------------|--------|
| Multi-object update in same trigger | Yes | Ensures consistency |
| Order + OrderItems creation | Yes | Business atomicity required |
| Account + CRM sync | No | Use async decoupling instead |
| Validation that spans objects | Yes | All-or-nothing validation |

---

## 3. Async Decoupling Patterns

### The Problem

After-trigger logic that represents an independent business process can cause cascade failures.

### Solution: Queueable Jobs

```apex
/**
 * Queueable job for processing that should not block the main transaction
 */
public class AccountSyncQueueable implements Queueable, Database.AllowsCallouts {

    private Set<Id> accountIds;
    private TriggerOperation operationType;

    public AccountSyncQueueable(Set<Id> accountIds, TriggerOperation operationType) {
        this.accountIds = accountIds;
        this.operationType = operationType;
    }

    public void execute(QueueableContext context) {
        try {
            List<Account> accounts = [
                SELECT Id, Name, Website, Industry, BillingAddress
                FROM Account
                WHERE Id IN :accountIds
            ];

            switch on operationType {
                when AFTER_INSERT {
                    ExternalCRM.createAccounts(accounts);
                }
                when AFTER_UPDATE {
                    ExternalCRM.updateAccounts(accounts);
                }
                when AFTER_DELETE {
                    ExternalCRM.deleteAccounts(accountIds);
                }
            }

        } catch (Exception e) {
            // Log error but don't fail - this is independent of main transaction
            ErrorLogger.log('AccountSyncQueueable', e, accountIds);
        }
    }
}
```

### Usage in Trigger Handler

```apex
public void afterInsert(List<Account> newAccounts, Map<Id, Account> newAccountsById) {
    // Synchronous operations that SHOULD block
    AccountNotifications.notifySalesTeam(newAccounts);

    // Async operations that should NOT block main transaction
    if (canEnqueueJob()) {
        System.enqueueJob(new AccountSyncQueueable(
            newAccountsById.keySet(),
            TriggerOperation.AFTER_INSERT
        ));
    }
}

private Boolean canEnqueueJob() {
    return !System.isBatch() &&
           !System.isFuture() &&
           Limits.getQueueableJobs() < Limits.getLimitQueueableJobs();
}
```

### Platform Events for Maximum Decoupling

```apex
// Publisher (in trigger)
EventBus.publish(new Account_Changed__e(
    Account_Id__c = account.Id,
    Change_Type__c = 'INSERT'
));

// Subscriber (separate trigger on platform event)
trigger AccountChangedSubscriber on Account_Changed__e (after insert) {
    // Process events - failures here don't affect original transaction
    List<Id> accountIds = new List<Id>();
    for (Account_Changed__e event : Trigger.new) {
        accountIds.add(event.Account_Id__c);
    }
    // Sync to external system
}
```

### Decoupling Decision Matrix

| Business Process | Same User Persona? | Failure Impact | Recommendation |
|-----------------|-------------------|----------------|----------------|
| Order + Line Items | Yes | Must be atomic | Synchronous + Savepoint |
| Account + Audit Log | Yes | Can retry | Queueable |
| Account + External CRM | No | Independent | Platform Event |
| Contact + Marketing Cloud | No | Independent | Platform Event |
| Record + Email Notification | Yes | Non-critical | @future |

---

## 4. Pre-Deployment Checklist

### Trigger Cascade Analysis

Before deploying triggers, analyze the cascade impact:

```
CHECKLIST:
□ List all triggers that fire on the same transaction
□ Identify which operations are atomic (same business process)
□ Identify which operations are independent (different processes)
□ Verify exception handling in each trigger
□ Check for recursive trigger prevention
□ Review async job usage and limits
```

### Questions to Answer

1. **What triggers will fire together?**
   - Map the full trigger chain for each DML operation
   - Include triggers on related objects (parent-child)

2. **What happens if each trigger fails?**
   - Which operations will roll back?
   - Is that the desired behavior?

3. **Are there external system calls?**
   - Should they be async?
   - What happens if they fail?

4. **What about governor limits?**
   - How many DML statements in the chain?
   - How many SOQL queries?
   - Can bulk operations stay within limits?

---

## 5. Testing Cascade Scenarios

### Test Cascade Success

```apex
@IsTest
static void testTriggerChain_AllSucceed() {
    Test.startTest();
    Account acc = new Account(Name = 'Test');
    insert acc;  // Should fire AccountTrigger, create child records, etc.
    Test.stopTest();

    // Verify all expected records were created
    Assert.areEqual(1, [SELECT COUNT() FROM Contact WHERE AccountId = :acc.Id]);
    Assert.areEqual(1, [SELECT COUNT() FROM Task WHERE WhatId = :acc.Id]);
}
```

### Test Cascade Failure (Expected Rollback)

```apex
@IsTest
static void testTriggerChain_ChildFailure_RollsBack() {
    // Configure scenario that will cause child trigger to fail
    Test.startTest();
    try {
        Account acc = new Account(Name = 'Trigger Failure Test');
        insert acc;
        Assert.fail('Expected DmlException');
    } catch (DmlException e) {
        // Expected - verify Account was NOT created
        Assert.areEqual(0, [SELECT COUNT() FROM Account WHERE Name = 'Trigger Failure Test']);
    }
    Test.stopTest();
}
```

### Test Async Decoupling

```apex
@IsTest
static void testAccountInsert_CRMSyncAsync_DoesNotBlock() {
    // Even if CRM sync would fail, Account should be created
    Test.startTest();
    Account acc = new Account(Name = 'Async Test');
    insert acc;
    Test.stopTest();

    // Account should exist regardless of async job outcome
    Assert.areEqual(1, [SELECT COUNT() FROM Account WHERE Name = 'Async Test']);

    // Verify async job was enqueued
    Assert.areEqual(1, [SELECT COUNT() FROM AsyncApexJob WHERE JobType = 'Queueable']);
}
```

---

## 6. Deployment Commands for Trigger Safety

### Validate Before Deploying

```bash
# Always validate triggers before deploying
sf project deploy start --dry-run \
    --source-dir force-app/main/default/triggers \
    --source-dir force-app/main/default/classes \
    --test-level RunLocalTests \
    --target-org alias
```

### Deploy with Test Coverage

```bash
# Deploy triggers with their test classes
sf project deploy start \
    --source-dir force-app/main/default/triggers \
    --source-dir force-app/main/default/classes \
    --test-level RunSpecifiedTests \
    --tests AccountTriggerTest,ContactTriggerTest \
    --target-org alias
```

### Verify Trigger Order

After deployment, verify trigger execution order if you have multiple triggers on the same object:

```bash
# Query trigger execution order (via Debug Logs)
sf apex tail log --target-org alias

# Or check in Setup: Object Manager → [Object] → Triggers
```

---

## Summary

| Pattern | Use Case | Trade-off |
|---------|----------|-----------|
| **Default (Cascade)** | Atomic business processes | Simple but all-or-nothing |
| **Savepoint** | Controlled rollback within handler | More code, explicit control |
| **Queueable** | Independent async processes | Decoupled but async limits |
| **Platform Event** | Maximum decoupling | More infrastructure |
| **@future** | Simple fire-and-forget | Limited parameters |

### Key Principles

1. **Make atomicity decisions explicit** - Don't rely on default behavior accidentally
2. **Decouple independent processes** - Use async for cross-domain operations
3. **Test cascade scenarios** - Verify both success and failure paths
4. **Document trigger chains** - Future maintainers need to understand dependencies
5. **Validate before deploying** - Use `--dry-run` to catch issues early
