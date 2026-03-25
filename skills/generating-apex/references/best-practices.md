# Apex Best Practices — Supplementary Patterns

Patterns not covered in the main SKILL.md rules or other reference files.
For bulkification, security, error handling, and async patterns, see the dedicated reference files.
For code smells and refactoring strategies, see [anti-patterns.md](anti-patterns.md).

## 1. Platform Cache

### When to Use
- Frequently accessed, rarely changed data
- Expensive calculations
- Cross-transaction data sharing

### Implementation
```apex
// Check cache first
Account acc = (Account)Cache.Org.get('local.AccountCache.' + accountId);
if (acc == null) {
    acc = [SELECT Id, Name FROM Account WHERE Id = :accountId];
    Cache.Org.put('local.AccountCache.' + accountId, acc, 3600);  // 1 hour TTL
}
return acc;
```

### Always Handle Cache Misses
```apex
// Cache can be evicted at any time
Object cachedValue = Cache.Org.get(key);
if (cachedValue == null) {
    // Rebuild from source
}
```

---

## 2. Static Variables for Transaction Caching

### Prevent Duplicate Queries
```apex
public class AccountService {
    private static Map<Id, Account> accountCache;

    public static Account getAccount(Id accountId) {
        if (accountCache == null) {
            accountCache = new Map<Id, Account>();
        }

        if (!accountCache.containsKey(accountId)) {
            accountCache.put(accountId, [SELECT Id, Name FROM Account WHERE Id = :accountId]);
        }

        return accountCache.get(accountId);
    }
}
```

### Recursion Prevention
```apex
public class TriggerHelper {
    private static Set<Id> processedIds = new Set<Id>();

    public static Boolean hasProcessed(Id recordId) {
        if (processedIds.contains(recordId)) {
            return true;
        }
        processedIds.add(recordId);
        return false;
    }
}
```

---

<a id="10-guard-clauses--fail-fast"></a>

## 3. Guard Clauses & Fail-Fast

> 💡 *Principles inspired by "Clean Apex Code" by Pablo Gonzalez.
> [Purchase the book](https://link.springer.com/book/10.1007/979-8-8688-1411-2) for complete coverage.*

### The Problem

Deeply nested validation leads to hard-to-read code where business logic is buried.

### Anti-Pattern
```apex
// BAD: Deep nesting obscures business logic
public void processAccountUpdate(Account oldAccount, Account newAccount) {
    if (newAccount != null) {
        if (oldAccount != null) {
            if (newAccount.Id != null) {
                if (hasFieldChanged(oldAccount, newAccount)) {
                    if (UserInfo.getUserType() == 'Standard') {
                        // Actual business logic buried 5 levels deep
                        performSync(newAccount);
                        sendNotification(newAccount);
                    }
                }
            }
        }
    }
}
```

### Best Practice: Guard Clauses
```apex
// GOOD: Guard clauses at the top, exit early
public void processAccountUpdate(Account oldAccount, Account newAccount) {
    // Guard clauses - validate preconditions and exit fast
    if (newAccount == null) return;
    if (oldAccount == null) return;
    if (newAccount.Id == null) return;
    if (!hasFieldChanged(oldAccount, newAccount)) return;
    if (UserInfo.getUserType() != 'Standard') return;

    // Main logic is now at the top level, clearly visible
    performSync(newAccount);
    sendNotification(newAccount);
}
```

### Parameter Validation with Exceptions

For public APIs, throw exceptions for invalid input:

```apex
public Database.LeadConvertResult convertLead(Id leadId, Id accountId) {
    // Guard clauses with exceptions for public API
    if (leadId == null) {
        throw new IllegalArgumentException('Lead ID cannot be null');
    }

    if (leadId.getSObjectType() != Lead.SObjectType) {
        throw new IllegalArgumentException('Expected Lead ID, received: ' + leadId.getSObjectType());
    }

    Lead leadRecord = queryLead(leadId);

    if (leadRecord == null) {
        throw new IllegalArgumentException('Lead not found: ' + leadId);
    }

    if (leadRecord.IsConverted) {
        throw new IllegalArgumentException('Lead is already converted: ' + leadId);
    }

    // Main conversion logic
    return performConversion(leadRecord, accountId);
}
```

### When to Use Each Pattern

| Scenario | Pattern | Example |
|----------|---------|---------|
| Private/internal methods | `return` early | `if (list == null) return;` |
| Public API | `throw Exception` | `throw new IllegalArgumentException(...)` |
| Trigger handlers | `return` for skip | `if (records.isEmpty()) return;` |
| Validation service | `addError()` | `record.addError('...')` |

---

## 4. Comment Best Practices

> 💡 *Principles inspired by "Clean Apex Code" by Pablo Gonzalez.
> [Purchase the book](https://link.springer.com/book/10.1007/979-8-8688-1411-2) for complete coverage.*

### Core Principle

Comments should explain **"why"**, not **"what"**. The code itself should communicate the "what".

### When Comments Add Value

```apex
// GOOD: Explains business decision
// Salesforce processes triggers in batches of 200. We use 201 to ensure
// our code handles batch boundaries correctly during validation.
private static final Integer BULK_TEST_SIZE = 201;

// GOOD: Documents platform limitation
// Safe navigation (?.) doesn't work in formulas - must use IF(ISBLANK())
// See Known Issue W-12345678

// GOOD: References external documentation
// Algorithm based on RFC 7519 (JSON Web Token specification)
// See: https://tools.ietf.org/html/rfc7519#section-4.1

// GOOD: Explains non-obvious optimization
// SOQL query in a loop replaced with map-based lookup — O(1) per record.
Account acc = accountsByExternalId.get(record.ExternalId__c);
```

### Comment Anti-Patterns

```apex
// BAD: Restates what code clearly shows
Integer count = 0;  // Initialize count to zero

// BAD: Version history belongs in Git
// Modified by John on 2024-01-15 to add validation
// Modified by Jane on 2024-02-20 to fix bug

// BAD: Commented-out code (delete it!)
// if (account.Type == 'Partner') {
//     processPartner(account);
// }

// BAD: TODO without owner or ticket
// TODO: fix this later

// GOOD: TODO with context
// TODO(JIRA-1234): Refactor to use Platform Events after Spring '26 release
```

### Self-Documenting Code

Instead of comments, make code self-explanatory:

```apex
// BAD: Needs comment to explain
if (acc.AnnualRevenue > 1000000 && acc.Type == 'Enterprise' && acc.Industry == 'Technology') {
    // Process strategic tech accounts
}

// GOOD: Code explains itself
Boolean isStrategicTechAccount =
    acc.AnnualRevenue > 1000000 &&
    acc.Type == 'Enterprise' &&
    acc.Industry == 'Technology';

if (isStrategicTechAccount) {
    processStrategicAccount(acc);
}
```
