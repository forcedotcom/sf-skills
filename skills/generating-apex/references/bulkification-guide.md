# Apex Bulkification Guide

Comprehensive guide to writing bulk-safe Apex code, understanding governor limits, and optimizing collection handling.

---

## Table of Contents

1. [Governor Limits Overview](#governor-limits-overview)
2. [The Golden Rules](#the-golden-rules)
3. [Common Bulkification Patterns](#common-bulkification-patterns)
4. [Collection Handling Best Practices](#collection-handling-best-practices)
5. [Monitoring and Debugging](#monitoring-and-debugging)

---

## Governor Limits Overview

Salesforce enforces per-transaction limits to ensure multi-tenant platform stability.

### Critical Limits (Synchronous Context)

| Resource | Limit | Notes |
|----------|-------|-------|
| **SOQL Queries** | 100 | Includes parent-child queries |
| **SOQL Query Rows** | 50,000 | Total rows retrieved |
| **DML Statements** | 150 | insert, update, delete, undelete operations |
| **DML Rows** | 10,000 | Total records per transaction |
| **CPU Time** | 10,000ms | Actual CPU time (not wall clock) |
| **Heap Size** | 6 MB | Memory used by variables |
| **Callouts** | 100 | HTTP requests |
| **Callout Time** | 120 seconds | Total time for all callouts |

### Asynchronous Limits (Future, Batch, Queueable)

| Resource | Limit | Notes |
|----------|-------|-------|
| **SOQL Queries** | 200 | Double synchronous |
| **SOQL Query Rows** | 50,000 | Same as sync |
| **DML Statements** | 150 | Same as sync |
| **DML Rows** | 10,000 | Same as sync |
| **CPU Time** | 60,000ms | 6x synchronous |
| **Heap Size** | 12 MB | 2x synchronous |

**Key Insight**: Async has more SOQL queries and CPU time, but DML limits are the same.

---

## The Golden Rules

> The hard rules (no SOQL in loops, no DML in loops, collection-first design) are defined in SKILL.md § **Bulkification & Governor Limits** and § **Never Generate These**. This section provides the implementation patterns for each rule.

### Pattern: Collect → Query → Map → Loop

Replace per-record SOQL with a single bulk query and a Map lookup:

```apex
Set<Id> accountIds = new Set<Id>();
for (Account acc : accounts) {
    accountIds.add(acc.Id);
}

Map<Id, List<Contact>> contactsByAccountId = new Map<Id, List<Contact>>();
for (Contact con : [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds]) {
    if (!contactsByAccountId.containsKey(con.AccountId)) {
        contactsByAccountId.put(con.AccountId, new List<Contact>());
    }
    contactsByAccountId.get(con.AccountId).add(con);
}

for (Account acc : accounts) {
    List<Contact> contacts = contactsByAccountId.get(acc.Id) ?? new List<Contact>();
    // Process contacts
}
```

### Pattern: Modify in Loop → DML After Loop

Collect changes in a List, then perform a single DML statement:

```apex
List<Account> toUpdate = new List<Account>();
for (Account acc : accounts) {
    if (acc.Industry != 'Technology') {
        toUpdate.add(new Account(Id = acc.Id, Industry = 'Technology'));
    }
}
update toUpdate;
```

### Pattern: Relationship Subqueries

Fetch parent and child records in a single SOQL:

```apex
Map<Id, Account> accountsWithRelated = new Map<Id, Account>([
    SELECT Id, Name,
           (SELECT Id FROM Contacts),
           (SELECT Id FROM Opportunities)
    FROM Account
    WHERE Id IN :accountIds
]);
```

---

## Common Bulkification Patterns

### Pattern 1: Map-Based Lookup

**Use Case**: Need to lookup related records for each item in a loop.

```apex
public static void updateAccountIndustry(List<Contact> contacts) {
    // Step 1: Collect Account IDs
    Set<Id> accountIds = new Set<Id>();
    for (Contact con : contacts) {
        if (con.AccountId != null) {
            accountIds.add(con.AccountId);
        }
    }

    // Step 2: Query Accounts into Map
    Map<Id, Account> accountMap = new Map<Id, Account>([
        SELECT Id, Industry
        FROM Account
        WHERE Id IN :accountIds
    ]);

    // Step 3: Loop and lookup
    for (Contact con : contacts) {
        Account acc = accountMap.get(con.AccountId);
        if (acc != null) {
            con.Description = 'Account Industry: ' + acc.Industry;
        }
    }

    update contacts;
}
```

**Key**: `Map<Id, SObject>` constructor automatically creates map from query results.

---

### Pattern 2: Grouping Related Records

**Use Case**: Process child records grouped by parent.

```apex
public static void processContactsByAccount(List<Contact> contacts) {
    // Group contacts by AccountId
    Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();

    for (Contact con : contacts) {
        if (!contactsByAccount.containsKey(con.AccountId)) {
            contactsByAccount.put(con.AccountId, new List<Contact>());
        }
        contactsByAccount.get(con.AccountId).add(con);
    }

    // Process each group
    for (Id accountId : contactsByAccount.keySet()) {
        List<Contact> accountContacts = contactsByAccount.get(accountId);
        System.debug('Account ' + accountId + ' has ' + accountContacts.size() + ' contacts');
        // Process accountContacts
    }
}
```

**Alternative using Null Coalescing (API 59+):**
```apex
for (Contact con : contacts) {
    List<Contact> existing = contactsByAccount.get(con.AccountId);
    if (existing == null) {
        existing = new List<Contact>();
        contactsByAccount.put(con.AccountId, existing);
    }
    existing.add(con);
}
```

---

### Pattern 3: Aggregate Queries for Rollups

**Use Case**: Calculate rollup values (count, sum, avg) on related records.

```apex
public static void updateAccountContactCounts(Set<Id> accountIds) {
    // Query aggregate data
    Map<Id, Integer> contactCountsByAccount = new Map<Id, Integer>();

    for (AggregateResult ar : [
        SELECT AccountId, COUNT(Id) contactCount
        FROM Contact
        WHERE AccountId IN :accountIds
        GROUP BY AccountId
    ]) {
        Id accountId = (Id) ar.get('AccountId');
        Integer count = (Integer) ar.get('contactCount');
        contactCountsByAccount.put(accountId, count);
    }

    // Update accounts
    List<Account> accountsToUpdate = new List<Account>();
    for (Id accountId : accountIds) {
        Integer count = contactCountsByAccount.get(accountId) ?? 0;
        accountsToUpdate.add(new Account(
            Id = accountId,
            Number_of_Contacts__c = count
        ));
    }

    update accountsToUpdate;
}
```

**Why use aggregates**: More efficient than querying all records and counting in Apex.

---

### Pattern 4: Bulk Upsert with External ID

**Use Case**: Upserting records from external system.

```apex
public static void syncAccountsFromExternal(List<ExternalAccount> externalAccounts) {
    List<Account> accountsToUpsert = new List<Account>();

    for (ExternalAccount ext : externalAccounts) {
        accountsToUpsert.add(new Account(
            External_ID__c = ext.externalId,  // External ID field
            Name = ext.name,
            Industry = ext.industry
        ));
    }

    // Upsert by External ID field
    Database.upsert(accountsToUpsert, Account.External_ID__c, false);
}
```

**Key**: `Database.upsert()` with External ID field automatically matches and updates existing records.

---

### Pattern 5: Conditional DML (Only Update Changed Records)

**Use Case**: Avoid unnecessary DML on unchanged records.

```apex
public static void updateAccountsIfChanged(List<Account> accounts, Map<Id, Account> oldMap) {
    List<Account> accountsToUpdate = new List<Account>();

    for (Account newAcc : accounts) {
        Account oldAcc = oldMap.get(newAcc.Id);

        // Only update if specific fields changed
        if (newAcc.Industry != oldAcc.Industry || newAcc.Rating != oldAcc.Rating) {
            accountsToUpdate.add(newAcc);
        }
    }

    if (!accountsToUpdate.isEmpty()) {
        update accountsToUpdate;
    }
}
```

**Benefit**: Reduces DML statements and CPU time.

---

## Collection Handling Best Practices

### Use the Right Collection Type

| Collection | When to Use | Key Features |
|------------|-------------|--------------|
| **List<T>** | Ordered data, duplicates allowed | Index access, iteration |
| **Set<T>** | Unique values, fast lookups | No duplicates, O(1) contains() |
| **Map<K,V>** | Key-value pairs, fast lookups | O(1) get(), unique keys |

**Example: Deduplication**
```apex
// ❌ BAD - O(n²) complexity
List<Id> uniqueIds = new List<Id>();
for (Id accountId : allAccountIds) {
    if (!uniqueIds.contains(accountId)) {  // Linear search!
        uniqueIds.add(accountId);
    }
}

// ✅ GOOD - O(n) complexity
Set<Id> uniqueIdsSet = new Set<Id>(allAccountIds);  // Automatic deduplication
```

---

### List Operations

**Creating Lists:**
```apex
// Empty list
List<Account> accounts = new List<Account>();

// From SOQL
List<Account> accounts = [SELECT Id FROM Account];

// From Set
Set<Id> idSet = new Set<Id>{acc1.Id, acc2.Id};
List<Id> idList = new List<Id>(idSet);
```

**Adding Elements:**
```apex
accounts.add(newAccount);           // Add single
accounts.addAll(moreAccounts);      // Add list
```

### Set Operations

**Union, Intersection, Difference:**
```apex
Set<Id> set1 = new Set<Id>{id1, id2, id3};
Set<Id> set2 = new Set<Id>{id2, id3, id4};

// Union (all unique values)
Set<Id> union = set1.clone();
union.addAll(set2);  // {id1, id2, id3, id4}

// Intersection (common values)
Set<Id> intersection = set1.clone();
intersection.retainAll(set2);  // {id2, id3}

// Difference (in set1 but not set2)
Set<Id> difference = set1.clone();
difference.removeAll(set2);  // {id1}
```

**Checking Membership:**
```apex
if (accountIds.contains(acc.Id)) {
    // Fast O(1) lookup
}
```

**⚠️ API 62.0 Breaking Change:**
Cannot modify Set while iterating - throws `System.FinalException`.

```apex
// ❌ FAILS in API 62.0+
Set<Id> ids = new Set<Id>{id1, id2, id3};
for (Id currentId : ids) {
    ids.add(newId);  // FinalException!
}

// ✅ GOOD - Collect changes, apply after loop
Set<Id> ids = new Set<Id>{id1, id2, id3};
Set<Id> toAdd = new Set<Id>();

for (Id currentId : ids) {
    toAdd.add(newId);
}

ids.addAll(toAdd);
```

---

### Map Operations

**Creating Maps:**
```apex
// Empty map
Map<Id, Account> accountMap = new Map<Id, Account>();

// From List (uses SObject Id as key)
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

// Manual insertion
Map<String, Integer> scoreMap = new Map<String, Integer>();
scoreMap.put('Alice', 95);
scoreMap.put('Bob', 87);
```

**Safe Access with Null Coalescing:**
```apex
// Old way
Integer score = scoreMap.get('Charlie');
if (score == null) {
    score = 0;
}

// Modern way (API 59+)
Integer score = scoreMap.get('Charlie') ?? 0;
```

**Iterating Maps:**
```apex
// Iterate keys
for (Id accountId : accountMap.keySet()) {
    Account acc = accountMap.get(accountId);
}

// Iterate values
for (Account acc : accountMap.values()) {
    System.debug(acc.Name);
}

// Iterate entries (best for both key + value)
for (Id accountId : accountMap.keySet()) {
    Account acc = accountMap.get(accountId);
    System.debug('Account ' + accountId + ': ' + acc.Name);
}
```

---

## Monitoring and Debugging

### Using Limits Class

**Check current consumption:**
```apex
System.debug('SOQL Queries: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
System.debug('CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
System.debug('Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
```

**Strategic placement:**
```apex
public static void expensiveOperation() {
    System.debug('=== BEFORE OPERATION ===');
    logLimits();

    // Expensive code
    List<Account> accounts = [SELECT Id FROM Account];

    System.debug('=== AFTER OPERATION ===');
    logLimits();
}

private static void logLimits() {
    System.debug('SOQL: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
    System.debug('DML: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
}
```

---

### Debug Logs Best Practices

**Use log levels strategically:**
```apex
System.debug(LoggingLevel.ERROR, 'Critical failure: ' + errorMsg);
System.debug(LoggingLevel.WARN, 'Warning: potential issue');
System.debug(LoggingLevel.INFO, 'Processing ' + accounts.size() + ' accounts');
System.debug(LoggingLevel.DEBUG, 'Variable value: ' + variable);
System.debug(LoggingLevel.FINE, 'Detailed trace info');
```

**Filter in Setup → Debug Logs:**
- Apex Code: DEBUG
- Database: INFO
- Workflow: INFO
- Validation: INFO

**Avoid excessive debug statements** - they consume heap and CPU.

---

### Query Plan Analysis

**Check query selectivity:**
```apex
// Use EXPLAIN in Developer Console or Workbench
// Or query plan API (requires REST call)
```

**Indicators of bad queries:**
- TableScan (full table scan)
- Cardinality mismatch (estimated vs actual rows)
- Missing indexes on WHERE clause fields

---

For Apex testing patterns (including bulk scenarios), use `generating-apex-test` skill.

## Advanced Optimization Techniques

### Lazy Loading Pattern

**Defer expensive operations until needed:**
```apex
public class AccountProcessor {

    private Map<Id, List<Contact>> contactsCache;

    public List<Contact> getContactsForAccount(Id accountId) {
        // Lazy load - only query when first accessed
        if (contactsCache == null) {
            loadAllContacts();
        }

        return contactsCache.get(accountId) ?? new List<Contact>();
    }

    private void loadAllContacts() {
        contactsCache = new Map<Id, List<Contact>>();

        for (Contact con : [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds]) {
            if (!contactsCache.containsKey(con.AccountId)) {
                contactsCache.put(con.AccountId, new List<Contact>());
            }
            contactsCache.get(con.AccountId).add(con);
        }
    }
}
```

---

### Platform Cache for Expensive Queries

**Cache frequently accessed data:**
```apex
public class CachedMetadataService {

    private static final String CACHE_PARTITION = 'local.MetadataCache';

    public static List<Config__c> getConfigurations() {
        // Try cache first
        List<Config__c> cached = (List<Config__c>) Cache.Org.get(CACHE_PARTITION + '.configs');

        if (cached != null) {
            return cached;
        }

        // Cache miss - query and store
        List<Config__c> configs = [SELECT Id, Name, Value__c FROM Config__c];
        Cache.Org.put(CACHE_PARTITION + '.configs', configs, 3600); // 1 hour TTL

        return configs;
    }
}
```

---

**Back to Main**: [SKILL.md](../SKILL.md)
