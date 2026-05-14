<!-- Parent: querying-soql/SKILL.md -->
# Selector Patterns: Query Abstraction in Vanilla Apex

This guide teaches query abstraction patterns using pure Apex — no external libraries required. These patterns improve testability, maintainability, and security compliance.

---

## Why Use a Selector Layer?

### The Problem

Without abstraction, SOQL queries are scattered everywhere:

```apex
// In TriggerHandler.cls
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :accountIds];

// In BatchJob.cls (duplicate!)
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :ids];

// In ServiceClass.cls (slightly different fields!)
List<Account> accounts = [SELECT Id, Name, Industry FROM Account WHERE Id IN :accountIds];
```

**Problems**:
1. **Duplication**: Same query logic repeated
2. **Inconsistency**: Different fields queried in different places
3. **Fragility**: Field deletion breaks multiple classes
4. **Testability**: Must create real records to test
5. **Security**: FLS/sharing often forgotten

### The Solution

Centralize queries in Selector classes:

```apex
// Single source of truth
public class AccountSelector {
    public static List<Account> byIds(Set<Id> accountIds) {
        return [
            SELECT Id, Name, Industry
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ];
    }
}

// Usage everywhere
List<Account> accounts = AccountSelector.byIds(accountIds);
```

---

## Pattern 1: Basic Selector Class

The simplest approach - a class with static query methods.

```apex
/**
 * AccountSelector - Centralized queries for Account object
 */
public inherited sharing class AccountSelector {

    // ═══════════════════════════════════════════════════════════════════
    // FIELD SETS (centralized field lists)
    // ═══════════════════════════════════════════════════════════════════

    private static final List<SObjectField> STANDARD_FIELDS = new List<SObjectField>{
        Account.Id,
        Account.Name,
        Account.Industry,
        Account.AnnualRevenue,
        Account.OwnerId
    };

    // ═══════════════════════════════════════════════════════════════════
    // QUERY METHODS
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Query accounts by their IDs
     */
    public static List<Account> byIds(Set<Id> accountIds) {
        if (accountIds == null || accountIds.isEmpty()) {
            return new List<Account>();
        }
        return [
            SELECT Id, Name, Industry, AnnualRevenue, OwnerId
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ];
    }

    /**
     * Query accounts by Owner
     */
    public static List<Account> byOwnerId(Id ownerId) {
        return [
            SELECT Id, Name, Industry, AnnualRevenue, OwnerId
            FROM Account
            WHERE OwnerId = :ownerId
            WITH SECURITY_ENFORCED
            LIMIT 1000
        ];
    }

    /**
     * Query accounts with their contacts
     */
    public static List<Account> withContactsByIds(Set<Id> accountIds) {
        return [
            SELECT Id, Name,
                   (SELECT Id, FirstName, LastName, Email
                    FROM Contacts
                    WHERE IsActive__c = true
                    LIMIT 50)
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ];
    }
}
```

**Usage**:
```apex
// Clean, readable, testable
List<Account> accounts = AccountSelector.byIds(accountIdSet);
List<Account> myAccounts = AccountSelector.byOwnerId(UserInfo.getUserId());
```

---

## Pattern 2: Selector with Sharing Modes

Control sharing rules at the selector level.

```apex
/**
 * ContactSelector with sharing mode control
 */
public class ContactSelector {

    // ═══════════════════════════════════════════════════════════════════
    // USER MODE (respects sharing rules - default)
    // ═══════════════════════════════════════════════════════════════════

    public inherited sharing class UserMode {
        public static List<Contact> byAccountIds(Set<Id> accountIds) {
            return [
                SELECT Id, FirstName, LastName, Email, AccountId
                FROM Contact
                WHERE AccountId IN :accountIds
                WITH USER_MODE
            ];
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // SYSTEM MODE (bypasses sharing - use carefully!)
    // ═══════════════════════════════════════════════════════════════════

    public without sharing class SystemMode {
        public static List<Contact> byAccountIds(Set<Id> accountIds) {
            return [
                SELECT Id, FirstName, LastName, Email, AccountId
                FROM Contact
                WHERE AccountId IN :accountIds
                WITH SYSTEM_MODE
            ];
        }
    }
}

// Usage
List<Contact> visibleContacts = ContactSelector.UserMode.byAccountIds(ids);
List<Contact> allContacts = ContactSelector.SystemMode.byAccountIds(ids);
```

---

## Pattern 3: Mockable Selector (for Unit Tests)

Enable query mocking without database calls.

```apex
/**
 * OpportunitySelector with mocking support
 */
public inherited sharing class OpportunitySelector {

    // Test-visible mock data
    @TestVisible
    private static List<Opportunity> mockData;

    /**
     * Query opportunities by Account IDs
     * Returns mock data in tests if set
     */
    public static List<Opportunity> byAccountIds(Set<Id> accountIds) {
        if (Test.isRunningTest() && mockData != null) {
            return mockData;
        }
        return [
            SELECT Id, Name, StageName, Amount, CloseDate, AccountId
            FROM Opportunity
            WHERE AccountId IN :accountIds
            WITH SECURITY_ENFORCED
        ];
    }

    /**
     * Set mock data for testing
     */
    @TestVisible
    private static void setMockData(List<Opportunity> opportunities) {
        mockData = opportunities;
    }
}
```

**Test Usage**:
```apex
@IsTest
private class OpportunitySelectorTest {
    @IsTest
    static void testByAccountIds_returnsMockData() {
        // Arrange - no database records needed!
        List<Opportunity> mockOpps = new List<Opportunity>{
            new Opportunity(Name = 'Test Opp', StageName = 'Prospecting', Amount = 1000)
        };
        OpportunitySelector.setMockData(mockOpps);

        // Act
        List<Opportunity> result = OpportunitySelector.byAccountIds(new Set<Id>());

        // Assert
        System.assertEquals(1, result.size());
        System.assertEquals('Test Opp', result[0].Name);
    }
}
```

---

## Pattern 4: Query Builder (Dynamic SOQL)

For complex, dynamic queries that vary at runtime.

```apex
/**
 * Dynamic query builder for flexible SOQL construction
 */
public inherited sharing class QueryBuilder {

    private String objectName;
    private Set<String> fields = new Set<String>();
    private List<String> conditions = new List<String>();
    private Map<String, Object> bindings = new Map<String, Object>();
    private String orderByClause;
    private Integer limitCount;

    /**
     * Constructor
     */
    public QueryBuilder(String objectName) {
        this.objectName = objectName;
    }

    /**
     * Add fields to select
     */
    public QueryBuilder selectFields(List<String> fieldList) {
        fields.addAll(fieldList);
        return this;
    }

    /**
     * Add fields using SObjectField tokens (type-safe!)
     */
    public QueryBuilder selectFields(List<SObjectField> fieldTokens) {
        for (SObjectField token : fieldTokens) {
            fields.add(String.valueOf(token));
        }
        return this;
    }

    /**
     * Add WHERE condition with binding
     */
    public QueryBuilder whereEquals(String field, Object value) {
        String bindName = 'bind' + bindings.size();
        conditions.add(field + ' = :' + bindName);
        bindings.put(bindName, value);
        return this;
    }

    /**
     * Add WHERE IN condition
     */
    public QueryBuilder whereIn(String field, Set<Id> ids) {
        String bindName = 'bind' + bindings.size();
        conditions.add(field + ' IN :' + bindName);
        bindings.put(bindName, ids);
        return this;
    }

    /**
     * Add ORDER BY
     */
    public QueryBuilder orderBy(String field, Boolean ascending) {
        orderByClause = field + (ascending ? ' ASC' : ' DESC');
        return this;
    }

    /**
     * Add LIMIT
     */
    public QueryBuilder setLimit(Integer count) {
        limitCount = count;
        return this;
    }

    /**
     * Build and execute the query
     */
    public List<SObject> execute() {
        String query = buildQuery();
        return Database.queryWithBinds(query, bindings, AccessLevel.USER_MODE);
    }

    /**
     * Build query string (for debugging)
     */
    public String buildQuery() {
        List<String> parts = new List<String>();

        // SELECT
        if (fields.isEmpty()) {
            fields.add('Id');
        }
        parts.add('SELECT ' + String.join(new List<String>(fields), ', '));

        // FROM
        parts.add('FROM ' + objectName);

        // WHERE
        if (!conditions.isEmpty()) {
            parts.add('WHERE ' + String.join(conditions, ' AND '));
        }

        // ORDER BY
        if (orderByClause != null) {
            parts.add('ORDER BY ' + orderByClause);
        }

        // LIMIT
        if (limitCount != null) {
            parts.add('LIMIT ' + limitCount);
        }

        return String.join(parts, ' ');
    }
}
```

**Usage**:
```apex
// Fluent API for dynamic queries
List<SObject> results = new QueryBuilder('Account')
    .selectFields(new List<SObjectField>{Account.Id, Account.Name, Account.Industry})
    .whereEquals('Industry', 'Technology')
    .whereIn('Id', accountIds)
    .orderBy('Name', true)
    .setLimit(100)
    .execute();

// Debug the generated query
System.debug(new QueryBuilder('Account').selectFields(...).buildQuery());
// "SELECT Id, Name, Industry FROM Account WHERE Industry = :bind0 AND Id IN :bind1 ORDER BY Name ASC LIMIT 100"
```

---

## Pattern 5: Bulkified Query Pattern

The Map-based lookup pattern for bulk operations.

```apex
/**
 * BulkQueryHelper - Reusable bulk query patterns
 */
public inherited sharing class BulkQueryHelper {

    /**
     * Get Accounts by ID as a Map (O(1) lookup)
     */
    public static Map<Id, Account> getAccountMapByIds(Set<Id> accountIds) {
        return new Map<Id, Account>([
            SELECT Id, Name, Industry
            FROM Account
            WHERE Id IN :accountIds
            WITH SECURITY_ENFORCED
        ]);
    }

    /**
     * Get Contacts grouped by AccountId
     */
    public static Map<Id, List<Contact>> getContactsByAccountId(Set<Id> accountIds) {
        Map<Id, List<Contact>> contactsByAccount = new Map<Id, List<Contact>>();

        for (Contact c : [
            SELECT Id, FirstName, LastName, Email, AccountId
            FROM Contact
            WHERE AccountId IN :accountIds
            WITH SECURITY_ENFORCED
        ]) {
            if (!contactsByAccount.containsKey(c.AccountId)) {
                contactsByAccount.put(c.AccountId, new List<Contact>());
            }
            contactsByAccount.get(c.AccountId).add(c);
        }

        return contactsByAccount;
    }
}
```

**Usage in Trigger**:
```apex
// ❌ WRONG: Query per record
for (Opportunity opp : Trigger.new) {
    Account a = [SELECT Name FROM Account WHERE Id = :opp.AccountId];
}

// ✅ CORRECT: Bulk query with Map lookup
Set<Id> accountIds = new Set<Id>();
for (Opportunity opp : Trigger.new) {
    accountIds.add(opp.AccountId);
}

Map<Id, Account> accountMap = BulkQueryHelper.getAccountMapByIds(accountIds);

for (Opportunity opp : Trigger.new) {
    Account a = accountMap.get(opp.AccountId);
    if (a != null) {
        // Use account data
    }
}
```

---

## Best Practices Summary

| Practice | Benefit |
|----------|---------|
| Centralize in Selector classes | One place to update field lists |
| Use `WITH SECURITY_ENFORCED` | Automatic FLS enforcement |
| Return empty List, not null | Prevents NullPointerException |
| Use `inherited sharing` | Respects caller's sharing context |
| Make fields list a constant | Easy to update across queries |
| Add null/empty checks | Prevent unnecessary queries |
| Support mocking in tests | Faster tests, no database dependencies |

---

## When to Use Each Pattern

| Scenario | Pattern |
|----------|---------|
| Simple, static queries | Pattern 1: Basic Selector |
| Need sharing mode control | Pattern 2: Sharing Modes |
| Heavy unit testing | Pattern 3: Mockable Selector |
| Dynamic filters at runtime | Pattern 4: Query Builder |
| Trigger/batch bulk operations | Pattern 5: Bulkified Query |
