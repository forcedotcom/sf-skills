# Trigger Actions Framework (TAF) Guide

## Overview

The Trigger Actions Framework provides a metadata-driven approach to trigger management, enabling:
- One trigger per object
- Ordered execution of actions
- Bypass mechanisms (global, transaction, permission-based)
- Support for both Apex and Flow actions

## Installation

Install from: https://github.com/mitchspano/trigger-actions-framework

## Basic Setup

### 1. Create the Trigger

One trigger per object, delegating all logic to the framework:

```apex
trigger AccountTrigger on Account (
    before insert, after insert,
    before update, after update,
    before delete, after delete,
    after undelete
) {
    new MetadataTriggerHandler().run();
}
```

### 2. Enable the Object

Create an `sObject_Trigger_Setting__mdt` record:
- Label: Account Trigger Setting
- Object API Name: Account
- Bypass Execution: unchecked

### 3. Create Action Classes

Each action class handles one specific behavior:

```apex
public class TA_Account_SetDefaults implements TriggerAction.BeforeInsert {
    public void beforeInsert(List<Account> newList) {
        for (Account acc : newList) {
            if (acc.Industry == null) {
                acc.Industry = 'Other';
            }
        }
    }
}
```

### 4. Register the Action

Create a `Trigger_Action__mdt` record:
- Object: Account
- Apex Class Name: TA_Account_SetDefaults
- Order: 1
- Before Insert: checked

---

## Action Interfaces

### Before Triggers

```apex
// Before Insert
public class MyAction implements TriggerAction.BeforeInsert {
    public void beforeInsert(List<SObject> newList) { }
}

// Before Update
public class MyAction implements TriggerAction.BeforeUpdate {
    public void beforeUpdate(List<SObject> newList, List<SObject> oldList) { }
}

// Before Delete
public class MyAction implements TriggerAction.BeforeDelete {
    public void beforeDelete(List<SObject> oldList) { }
}
```

### After Triggers

```apex
// After Insert
public class MyAction implements TriggerAction.AfterInsert {
    public void afterInsert(List<SObject> newList) { }
}

// After Update
public class MyAction implements TriggerAction.AfterUpdate {
    public void afterUpdate(List<SObject> newList, List<SObject> oldList) { }
}

// After Delete
public class MyAction implements TriggerAction.AfterDelete {
    public void afterDelete(List<SObject> oldList) { }
}

// After Undelete
public class MyAction implements TriggerAction.AfterUndelete {
    public void afterUndelete(List<SObject> newList) { }
}
```

---

## Common Patterns

### Setting Default Values (Before Insert)

```apex
public class TA_Account_SetDefaults implements TriggerAction.BeforeInsert {
    public void beforeInsert(List<Account> newList) {
        for (Account acc : newList) {
            acc.Industry = acc.Industry ?? 'Other';
            acc.NumberOfEmployees = acc.NumberOfEmployees ?? 0;
        }
    }
}
```

### Validation (Before Insert/Update)

```apex
public class TA_Account_ValidateData implements TriggerAction.BeforeInsert, TriggerAction.BeforeUpdate {

    public void beforeInsert(List<Account> newList) {
        validate(newList);
    }

    public void beforeUpdate(List<Account> newList, List<Account> oldList) {
        validate(newList);
    }

    private void validate(List<Account> accounts) {
        for (Account acc : accounts) {
            if (acc.AnnualRevenue != null && acc.AnnualRevenue < 0) {
                acc.AnnualRevenue.addError('Annual Revenue cannot be negative');
            }
        }
    }
}
```

### Related Record Updates (After Insert/Update)

```apex
public class TA_Account_UpdateContacts implements TriggerAction.AfterUpdate {

    public void afterUpdate(List<Account> newList, List<Account> oldList) {
        Map<Id, Account> oldMap = new Map<Id, Account>(oldList);
        Set<Id> changedAccountIds = new Set<Id>();

        for (Account acc : newList) {
            Account oldAcc = oldMap.get(acc.Id);
            if (acc.BillingCity != oldAcc.BillingCity) {
                changedAccountIds.add(acc.Id);
            }
        }

        if (!changedAccountIds.isEmpty()) {
            updateContactAddresses(changedAccountIds);
        }
    }

    private void updateContactAddresses(Set<Id> accountIds) {
        List<Contact> contacts = [
            SELECT Id, AccountId, MailingCity
            FROM Contact
            WHERE AccountId IN :accountIds
            WITH USER_MODE
        ];

        Map<Id, Account> accounts = new Map<Id, Account>([
            SELECT Id, BillingCity
            FROM Account
            WHERE Id IN :accountIds
            WITH USER_MODE
        ]);

        for (Contact con : contacts) {
            con.MailingCity = accounts.get(con.AccountId).BillingCity;
        }

        update contacts;
    }
}
```

### Async Processing (After Insert/Update)

```apex
public class TA_Account_ProcessAsync implements TriggerAction.AfterInsert {

    public void afterInsert(List<Account> newList) {
        Set<Id> accountIds = new Map<Id, Account>(newList).keySet();
        System.enqueueJob(new AccountProcessingQueueable(accountIds));
    }
}
```

---

## Bypass Mechanisms

### Global Bypass (Metadata)

In `sObject_Trigger_Setting__mdt`:
- Set `Bypass_Execution__c = true` to disable all triggers for object

### Transaction Bypass (Apex)

```apex
// Bypass specific object
TriggerBase.bypass(Account.SObjectType);

// Bypass specific action
MetadataTriggerHandler.bypass('TA_Account_SetDefaults');

// Clear bypasses
TriggerBase.clearAllBypasses();
MetadataTriggerHandler.clearAllBypasses();
```

### Permission-Based Bypass

In `Trigger_Action__mdt`:
- `Bypass_Permission__c`: Users with this permission skip the action
- `Required_Permission__c`: Only users with this permission run the action

### Custom Permissions as Preferred Bypass (Recommended)

Custom Permissions provide a scalable, declarative bypass mechanism — preferred over hardcoded profile/role names.

```apex
public class TA_Account_SetDefaults implements TriggerAction.BeforeInsert {
    public void beforeInsert(List<Account> newList) {
        // Check Custom Permission — preferred over hardcoded profile names
        if (FeatureManagement.checkPermission('Bypass_Triggers')) {
            return;
        }
        for (Account acc : newList) {
            acc.Industry = acc.Industry ?? 'Other';
        }
    }
}
```

> **Why Custom Permissions > hardcoded profile names**: Custom Permissions can be assigned via Permission Sets (stackable, user-specific), don't break when profiles are renamed, and work across all automation types (Apex, Flow, Validation Rules).

---

## Recursion Prevention

### Field-Value Comparison (Recommended)

The official recommendation for recursion prevention is to compare old vs new field values, processing only records where the relevant field actually changed. This is more precise than static boolean flags.

```apex
public class TA_Account_SyncExternal implements TriggerAction.AfterUpdate {

    public void afterUpdate(List<Account> newList, List<Account> oldList) {
        Map<Id, Account> oldMap = new Map<Id, Account>(oldList);
        List<Account> toProcess = new List<Account>();

        for (Account acc : newList) {
            Account oldAcc = oldMap.get(acc.Id);
            // Only process if the field we care about actually changed
            if (acc.Status__c != oldAcc.Status__c) {
                toProcess.add(acc);
            }
        }

        if (!toProcess.isEmpty()) {
            processAccounts(toProcess);
        }
    }
}
```

> **Why field-value comparison > static boolean flags**: Static booleans (`hasRun = true`) prevent ALL re-entry, even legitimate re-entry from different field changes. Field-value comparison only skips records where the triggering field didn't change.

### Using TriggerBase (TAF-Specific)

TAF provides built-in recursion tracking via `idToNumberOfTimesSeenAfterUpdate`. Use this when you need to limit execution count per record regardless of which fields changed:

```apex
public class TA_Account_PreventRecursion implements TriggerAction.AfterUpdate {

    public void afterUpdate(List<Account> newList, List<Account> oldList) {
        List<Account> toProcess = new List<Account>();

        for (Account acc : newList) {
            // Check if already processed in this transaction
            if (!TriggerBase.idToNumberOfTimesSeenAfterUpdate.get(acc.Id).equals(1)) {
                continue;
            }
            toProcess.add(acc);
        }

        if (!toProcess.isEmpty()) {
            processAccounts(toProcess);
        }
    }
}
```

---

## Flow Actions

### Setup

1. Create an Autolaunched Flow
2. Add variables:
   - `record` (Input, Record type)
   - `recordPrior` (Input, Record type, for Update triggers)

3. Create `Trigger_Action__mdt`:
   - Apex Class Name: `TriggerActionFlow`
   - Flow Name: `Your_Flow_API_Name`

### Entry Criteria

Define formula criteria to control when the flow executes:
```
{!record.Status__c} = 'Submitted' && {!recordPrior.Status__c} != 'Submitted'
```

---

## Testing

### Test Action Classes

```apex
@isTest
private class TA_Account_SetDefaultsTest {

    @isTest
    static void testBeforeInsert() {
        Account acc = new Account(Name = 'Test');

        Test.startTest();
        insert acc;
        Test.stopTest();

        Account result = [SELECT Industry FROM Account WHERE Id = :acc.Id];
        Assert.areEqual('Other', result.Industry, 'Default industry should be set');
    }

    @isTest
    static void testBulkInsert() {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < 251; i++) {
            accounts.add(new Account(Name = 'Test ' + i));
        }

        Test.startTest();
        insert accounts;
        Test.stopTest();

        List<Account> results = [SELECT Industry FROM Account WHERE Id IN :accounts];
        for (Account acc : results) {
            Assert.areEqual('Other', acc.Industry);
        }
    }
}
```

### Test with Bypass

```apex
@isTest
static void testWithBypass() {
    // Bypass the action
    MetadataTriggerHandler.bypass('TA_Account_SetDefaults');

    Account acc = new Account(Name = 'Test');
    insert acc;

    Account result = [SELECT Industry FROM Account WHERE Id = :acc.Id];
    Assert.isNull(result.Industry, 'Industry should not be set when bypassed');

    // Clear bypass for other tests
    MetadataTriggerHandler.clearBypass('TA_Account_SetDefaults');
}
```

---

## Naming Convention

```
TA_[ObjectName]_[ActionDescription]

Examples:
- TA_Account_SetDefaults
- TA_Account_ValidateData
- TA_Contact_UpdateAccountRollup
- TA_Opportunity_SendNotification
```

---

## Execution Order

Actions execute in the order defined by the `Order__c` field in `Trigger_Action__mdt`.

Recommended ordering:
1. Validation (10-20)
2. Default values (30-40)
3. Field calculations (50-60)
4. Related record queries (70-80)
5. Related record updates (90-100)
6. Async/external calls (110+)
