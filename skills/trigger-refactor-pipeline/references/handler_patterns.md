# Trigger Handler Patterns Reference

This guide covers common patterns for refactoring Salesforce triggers into handler classes with bulk-safe operations.

## Pattern 1: Simple Handler Class

**Best for**: Triggers with 1-3 contexts and straightforward logic.

### Structure

```apex
public class OpportunityTriggerHandler {
    
    public void beforeInsert(List<Opportunity> newRecords) {
        validateClosedWonAmount(newRecords);
    }
    
    public void beforeUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap) {
        updateDescriptionOnStageChange(newRecords, oldMap);
    }
    
    public void afterUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap) {
        createTasksForClosedWon(newRecords, oldMap);
    }
    
    // Private helper methods below
    private void validateClosedWonAmount(List<Opportunity> opportunities) {
        for (Opportunity opp : opportunities) {
            if (opp.StageName == 'Closed Won' && 
                (opp.Amount == null || opp.Amount < 1000)) {
                opp.addError('Closed Won opportunities must have Amount ≥ 1000.');
            }
        }
    }
    
    private void updateDescriptionOnStageChange(
        List<Opportunity> newRecords, 
        Map<Id, Opportunity> oldMap
    ) {
        for (Opportunity opp : newRecords) {
            Opportunity oldOpp = oldMap.get(opp.Id);
            if (opp.StageName != oldOpp.StageName) {
                opp.Description = 'Stage changed from ' + 
                    oldOpp.StageName + ' to ' + opp.StageName;
            }
        }
    }
    
    private void createTasksForClosedWon(
        List<Opportunity> newRecords, 
        Map<Id, Opportunity> oldMap
    ) {
        List<Task> tasksToInsert = new List<Task>();
        
        for (Opportunity opp : newRecords) {
            Opportunity oldOpp = oldMap.get(opp.Id);
            
            // Check if stage changed to Closed Won
            if (opp.StageName == 'Closed Won' && 
                oldOpp.StageName != 'Closed Won') {
                
                tasksToInsert.add(new Task(
                    WhatId = opp.Id,
                    OwnerId = opp.OwnerId,
                    Subject = 'Send thank-you',
                    Status = 'Not Started',
                    Priority = 'Normal',
                    ActivityDate = Date.today()
                ));
            }
        }
        
        // Bulk DML outside loop
        if (!tasksToInsert.isEmpty()) {
            insert tasksToInsert;
        }
    }
}
```

### Trigger Delegation

```apex
trigger OpportunityTrigger on Opportunity (
    before insert, before update, after update
) {
    OpportunityTriggerHandler handler = new OpportunityTriggerHandler();
    
    if (Trigger.isBefore) {
        if (Trigger.isInsert) {
            handler.beforeInsert(Trigger.new);
        } else if (Trigger.isUpdate) {
            handler.beforeUpdate(Trigger.new, Trigger.oldMap);
        }
    }
    
    if (Trigger.isAfter && Trigger.isUpdate) {
        handler.afterUpdate(Trigger.new, Trigger.oldMap);
    }
}
```

## Pattern 2: Handler with Database Methods

**Best for**: When you need granular error handling and partial success.

### Key Features

- Uses `Database.insert()` instead of `insert` for partial saves
- Returns `Database.SaveResult` for error handling
- Logs errors without stopping execution

### Example

```apex
private void createTasksForClosedWon(
    List<Opportunity> newRecords, 
    Map<Id, Opportunity> oldMap
) {
    List<Task> tasksToInsert = new List<Task>();
    
    for (Opportunity opp : newRecords) {
        Opportunity oldOpp = oldMap.get(opp.Id);
        
        if (opp.StageName == 'Closed Won' && 
            oldOpp.StageName != 'Closed Won') {
            
            tasksToInsert.add(new Task(
                WhatId = opp.Id,
                OwnerId = opp.OwnerId,
                Subject = 'Send thank-you',
                Status = 'Not Started',
                Priority = 'Normal',
                ActivityDate = Date.today()
            ));
        }
    }
    
    if (!tasksToInsert.isEmpty()) {
        Database.SaveResult[] results = Database.insert(tasksToInsert, false);
        
        // Log errors without stopping execution
        for (Integer i = 0; i < results.size(); i++) {
            if (!results[i].isSuccess()) {
                System.debug('Failed to create task: ' + results[i].getErrors());
            }
        }
    }
}
```

## Pattern 3: Handler with Maps for Lookups

**Best for**: When you need to query related records for processing.

### Key Features

- Pre-queries related records using Sets
- Uses Maps for O(1) lookups instead of nested loops
- Avoids SOQL in loops

### Example

```apex
private void enrichOpportunitiesWithAccountData(List<Opportunity> opportunities) {
    // Collect Account IDs
    Set<Id> accountIds = new Set<Id>();
    for (Opportunity opp : opportunities) {
        if (opp.AccountId != null) {
            accountIds.add(opp.AccountId);
        }
    }
    
    // Single SOQL query outside loop
    Map<Id, Account> accountMap = new Map<Id, Account>([
        SELECT Id, Name, Industry, AnnualRevenue
        FROM Account
        WHERE Id IN :accountIds
    ]);
    
    // Use Map for O(1) lookup
    for (Opportunity opp : opportunities) {
        if (opp.AccountId != null && accountMap.containsKey(opp.AccountId)) {
            Account acc = accountMap.get(opp.AccountId);
            // Process with account data
            opp.Description = 'Account Industry: ' + acc.Industry;
        }
    }
}
```

## Pattern 4: Unified Handler Framework

**Best for**: Complex triggers with many contexts and cross-cutting concerns.

### Structure

```apex
public abstract class TriggerHandler {
    
    protected Boolean isBefore;
    protected Boolean isAfter;
    protected Boolean isInsert;
    protected Boolean isUpdate;
    protected Boolean isDelete;
    protected Boolean isUndelete;
    
    public void run() {
        isBefore = Trigger.isBefore;
        isAfter = Trigger.isAfter;
        isInsert = Trigger.isInsert;
        isUpdate = Trigger.isUpdate;
        isDelete = Trigger.isDelete;
        isUndelete = Trigger.isUndelete;
        
        if (isBefore) {
            if (isInsert) beforeInsert();
            if (isUpdate) beforeUpdate();
            if (isDelete) beforeDelete();
        }
        
        if (isAfter) {
            if (isInsert) afterInsert();
            if (isUpdate) afterUpdate();
            if (isDelete) afterDelete();
            if (isUndelete) afterUndelete();
        }
    }
    
    protected virtual void beforeInsert() {}
    protected virtual void beforeUpdate() {}
    protected virtual void beforeDelete() {}
    protected virtual void afterInsert() {}
    protected virtual void afterUpdate() {}
    protected virtual void afterDelete() {}
    protected virtual void afterUndelete() {}
}
```

### Concrete Handler

```apex
public class OpportunityTriggerHandler extends TriggerHandler {
    
    private List<Opportunity> newRecords;
    private List<Opportunity> oldRecords;
    private Map<Id, Opportunity> newMap;
    private Map<Id, Opportunity> oldMap;
    
    public OpportunityTriggerHandler() {
        this.newRecords = (List<Opportunity>) Trigger.new;
        this.oldRecords = (List<Opportunity>) Trigger.old;
        this.newMap = (Map<Id, Opportunity>) Trigger.newMap;
        this.oldMap = (Map<Id, Opportunity>) Trigger.oldMap;
    }
    
    protected override void beforeInsert() {
        validateClosedWonAmount();
    }
    
    protected override void beforeUpdate() {
        updateDescriptionOnStageChange();
    }
    
    protected override void afterUpdate() {
        createTasksForClosedWon();
    }
    
    // Private helper methods omitted for brevity
}
```

### Trigger Delegation

```apex
trigger OpportunityTrigger on Opportunity (
    before insert, before update, after update
) {
    new OpportunityTriggerHandler().run();
}
```

## Best Practices

### 1. Bulkification

Always process records in collections:

```apex
// ✓ Good: Collect DML outside loop
List<Task> tasksToInsert = new List<Task>();
for (Opportunity opp : opportunities) {
    tasksToInsert.add(new Task(...));
}
if (!tasksToInsert.isEmpty()) {
    insert tasksToInsert;
}

// ✗ Bad: DML inside loop
for (Opportunity opp : opportunities) {
    insert new Task(...);  // SOQL/DML in loop!
}
```

### 2. Defensive Null Checks

```apex
// ✓ Good: Check for null before accessing
if (opp.AccountId != null && accountMap.containsKey(opp.AccountId)) {
    Account acc = accountMap.get(opp.AccountId);
    // Safe to use acc
}

// ✗ Bad: Assumes data exists
Account acc = accountMap.get(opp.AccountId);
String industry = acc.Industry;  // NullPointerException risk
```

### 3. Clear Method Names

```apex
// ✓ Good: Descriptive, verb-noun pattern
private void validateClosedWonAmount(List<Opportunity> opportunities)
private void createTasksForClosedWon(List<Opportunity> opportunities)

// ✗ Bad: Vague or unclear
private void validate(List<Opportunity> opportunities)
private void doStuff(List<Opportunity> opportunities)
```

### 4. Single Responsibility

Each handler method should do one thing:

```apex
// ✓ Good: Separate concerns
private void validateClosedWonAmount(List<Opportunity> opportunities)
private void validateRequiredFields(List<Opportunity> opportunities)
private void calculateDiscounts(List<Opportunity> opportunities)

// ✗ Bad: One method does everything
private void processOpportunities(List<Opportunity> opportunities)
```

### 5. Test Boundaries

Structure code to make testing easier:

```apex
// ✓ Good: Public method for testing, private for implementation
@TestVisible
private void createTasksForClosedWon(
    List<Opportunity> newRecords,
    Map<Id, Opportunity> oldMap
) {
    // Implementation
}
```

## Deployment Order

When deploying refactored triggers:

1. Deploy handler class(es) first
2. Update trigger to use handler
3. Deploy test class
4. Run all tests before production deployment
5. Monitor debug logs for 24-48 hours after production deployment

## Rollback Strategy

Keep the old trigger code commented out or in version control:

```apex
trigger OpportunityTrigger on Opportunity (...) {
    // New handler approach
    new OpportunityTriggerHandler().run();
    
    /* OLD CODE - REMOVE AFTER 1 WEEK IF NO ISSUES
    if (Trigger.isBefore && Trigger.isInsert) {
        for (Opportunity o : Trigger.new) {
            // old logic
        }
    }
    */
}
```

## Common Pitfalls

### Pitfall 1: Recursive Triggers

**Problem**: Handler calls DML which triggers the same trigger again.

**Solution**: Use static flag to prevent recursion:

```apex
public class OpportunityTriggerHandler {
    private static Boolean isExecuting = false;
    
    public void beforeUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap) {
        if (isExecuting) return;
        
        isExecuting = true;
        try {
            // Your logic here
        } finally {
            isExecuting = false;
        }
    }
}
```

### Pitfall 2: Mixed Context Logic

**Problem**: Before-context logic mixed with after-context logic.

**Solution**: Keep context methods separate and focused:

```apex
// ✓ Good: Separate methods per context
public void beforeUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap)
public void afterUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap)

// ✗ Bad: Mixed logic in one method
public void handleUpdate(List<Opportunity> newRecords, Map<Id, Opportunity> oldMap)
```

### Pitfall 3: Over-Engineering

**Problem**: Using complex framework for simple triggers.

**Solution**: Choose the right pattern for your complexity:
- 1-3 contexts with simple logic → Simple Handler (Pattern 1)
- 3-5 contexts with moderate complexity → Handler with Database Methods (Pattern 2)
- 5+ contexts with cross-cutting concerns → Unified Framework (Pattern 4)

## Additional Resources

- [Apex Developer Guide: Trigger and Bulk Request Best Practices](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_triggers_bulk_requests.htm)
- [Apex Enterprise Patterns](https://github.com/apex-enterprise-patterns)
- [Trigger Framework Comparison](https://github.com/kevinohara80/sfdc-trigger-framework)
