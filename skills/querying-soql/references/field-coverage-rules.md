<!-- Parent: querying-soql/SKILL.md -->
# SOQL Field Coverage Rules

This guide documents field coverage validation rules for SOQL queries — ensuring that all fields accessed in Apex code are actually queried. This is a common source of runtime errors, especially in AI-assisted code generation.

---

## Table of Contents

1. [The Field Coverage Problem](#the-field-coverage-problem)
2. [Direct Field Access](#direct-field-access)
3. [Relationship Field Access](#relationship-field-access)
4. [Dynamic Field Access](#dynamic-field-access)
5. [Aggregate Queries](#aggregate-queries)
6. [Subquery Fields](#subquery-fields)
7. [Validation Patterns](#validation-patterns)

---

## The Field Coverage Problem

When you query an sObject, only the fields in the SELECT clause are populated. Accessing any other field results in a runtime error:

```
System.SObjectException: SObject row was retrieved via SOQL without querying the requested field: Account.Industry
```

This error is particularly common in LLM-generated code because the LLM may:
1. Query some fields but access others in subsequent code
2. Forget to include relationship fields (e.g., `Account.Name` on Contact)
3. Access fields in conditional logic that weren't anticipated in the query

---

## Direct Field Access

### Rule: Every field accessed must be in the SELECT clause

### ❌ BAD: Accessing Unqueried Fields

```apex
// Query only includes Id and Name
List<Account> accounts = [SELECT Id, Name FROM Account];

for (Account acc : accounts) {
    // RUNTIME ERROR: Industry was not queried
    if (acc.Industry == 'Technology') {
        // RUNTIME ERROR: Description was not queried
        acc.Description = 'Tech company';
    }

    // RUNTIME ERROR: AnnualRevenue was not queried
    Decimal revenue = acc.AnnualRevenue;
}
```

### ✅ GOOD: Query All Accessed Fields

```apex
// Query ALL fields that will be accessed
List<Account> accounts = [
    SELECT Id, Name, Industry, Description, AnnualRevenue
    FROM Account
];

for (Account acc : accounts) {
    if (acc.Industry == 'Technology') {
        acc.Description = 'Tech company';  // OK - queried
    }
    Decimal revenue = acc.AnnualRevenue;  // OK - queried
}
```

### Field Access Locations to Check

Fields can be accessed in many places—ensure coverage for all:

| Access Location | Example | Must Query |
|-----------------|---------|------------|
| Conditional (`if`) | `if (acc.Industry == 'Tech')` | `Industry` |
| Assignment | `acc.Description = 'Text'` | `Description` |
| Variable assignment | `String name = acc.Name` | `Name` |
| Method argument | `sendEmail(acc.Email__c)` | `Email__c` |
| Collection key | `map.put(acc.Name, acc)` | `Name` |
| String interpolation | `'Hello ' + acc.Name` | `Name` |
| SOQL bind | `[SELECT Id FROM Contact WHERE AccountId = :acc.Id]` | `Id` (usually included) |

---

## Relationship Field Access

### Rule: Parent relationship fields require dot notation in SELECT

### ❌ BAD: Missing Relationship Fields

```apex
// Contact query without Account relationship fields
List<Contact> contacts = [SELECT Id, Name, AccountId FROM Contact];

for (Contact c : contacts) {
    // RUNTIME ERROR: Account.Name was not queried
    String accountName = c.Account.Name;

    // RUNTIME ERROR: Account.Industry was not queried
    if (c.Account.Industry == 'Technology') {
        // ...
    }
}
```

### ✅ GOOD: Include Relationship Fields

```apex
// Use dot notation to include parent fields
List<Contact> contacts = [
    SELECT Id, Name, AccountId,
           Account.Name,           // Parent field
           Account.Industry,       // Parent field
           Account.Owner.Name      // Grandparent field (up to 5 levels)
    FROM Contact
];

for (Contact c : contacts) {
    String accountName = c.Account.Name;  // OK - queried

    if (c.Account.Industry == 'Technology') {  // OK - queried
        String ownerName = c.Account.Owner.Name;  // OK - queried
    }
}
```

### Relationship Traversal Limits

| Direction | Limit | Example |
|-----------|-------|---------|
| Parent (lookup/master-detail) | 5 levels | `Contact.Account.Owner.Manager.Name` |
| Child (subquery) | 1 level | `Account -> Contacts` (cannot nest subqueries) |

### ❌ BAD: Assuming Relationship is Populated

```apex
List<Contact> contacts = [SELECT Id, AccountId FROM Contact];

for (Contact c : contacts) {
    // AccountId is queried, but Account object is NOT populated
    // This will throw: Account.Name not queried
    if (c.Account != null) {
        String name = c.Account.Name;  // ERROR!
    }
}
```

### ✅ GOOD: Query Relationship or Use Separate Query

```apex
// Option 1: Include relationship field
List<Contact> contacts = [SELECT Id, AccountId, Account.Name FROM Contact];

for (Contact c : contacts) {
    if (c.Account != null) {
        String name = c.Account.Name;  // OK
    }
}

// Option 2: Separate query using collected IDs
List<Contact> contacts = [SELECT Id, AccountId FROM Contact];
Set<Id> accountIds = new Set<Id>();
for (Contact c : contacts) {
    if (c.AccountId != null) {
        accountIds.add(c.AccountId);
    }
}

Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
);

for (Contact c : contacts) {
    Account acc = accountMap.get(c.AccountId);
    if (acc != null) {
        String name = acc.Name;  // OK
    }
}
```

---

## Dynamic Field Access

### Rule: Dynamic field access (using `get()`) also requires queried fields

### ❌ BAD: Dynamic Access to Unqueried Field

```apex
List<Account> accounts = [SELECT Id, Name FROM Account];
String fieldName = 'Industry';  // Dynamic field name

for (Account acc : accounts) {
    // RUNTIME ERROR: Industry was not queried
    Object value = acc.get(fieldName);
}
```

### ✅ GOOD: Query Fields Used Dynamically

```apex
// If you know which fields will be accessed dynamically, query them
List<Account> accounts = [SELECT Id, Name, Industry FROM Account];
String fieldName = 'Industry';

for (Account acc : accounts) {
    Object value = acc.get(fieldName);  // OK - Industry is queried
}
```

### ✅ GOOD: Build Dynamic Query

```apex
// For truly dynamic scenarios, build the query dynamically
Set<String> fieldsToQuery = new Set<String>{'Id', 'Name'};
fieldsToQuery.addAll(dynamicFieldList);  // Add dynamic fields

String query = 'SELECT ' + String.join(new List<String>(fieldsToQuery), ', ') +
               ' FROM Account WHERE Id IN :accountIds';

List<Account> accounts = Database.query(query);
```

---

## Aggregate Queries

### Rule: Aggregate queries return `AggregateResult`, not sObjects

### ❌ BAD: Treating Aggregate as sObject

```apex
// This returns AggregateResult, not Account
List<Account> accounts = [
    SELECT Industry, COUNT(Id) cnt
    FROM Account
    GROUP BY Industry
];  // COMPILE ERROR - wrong type

// Even with correct type, can't access normal fields
AggregateResult[] results = [
    SELECT Industry, COUNT(Id) cnt
    FROM Account
    GROUP BY Industry
];

for (AggregateResult ar : results) {
    // Cannot access like sObject fields
    String industry = ar.Industry;  // COMPILE ERROR
}
```

### ✅ GOOD: Use get() for Aggregate Results

```apex
AggregateResult[] results = [
    SELECT Industry, COUNT(Id) cnt, SUM(AnnualRevenue) totalRevenue
    FROM Account
    GROUP BY Industry
];

for (AggregateResult ar : results) {
    // Use get() with field alias
    String industry = (String) ar.get('Industry');
    Integer count = (Integer) ar.get('cnt');
    Decimal totalRevenue = (Decimal) ar.get('totalRevenue');

    System.debug(industry + ': ' + count + ' accounts, $' + totalRevenue);
}
```

### Aggregate Field Aliases

| Function | Default Alias | Example |
|----------|---------------|---------|
| `COUNT(Field)` | `expr0`, `expr1`, etc. | Use explicit alias: `COUNT(Id) cnt` |
| `SUM(Field)` | `expr0`, `expr1`, etc. | Use explicit alias: `SUM(Amount) total` |
| `AVG(Field)` | `expr0`, `expr1`, etc. | Use explicit alias: `AVG(Age) avgAge` |
| `MIN(Field)` | `expr0`, `expr1`, etc. | Use explicit alias: `MIN(CreatedDate) earliest` |
| `MAX(Field)` | `expr0`, `expr1`, etc. | Use explicit alias: `MAX(Amount) largest` |
| `GROUP BY Field` | Field API name | Access with field name: `ar.get('Industry')` |

---

## Subquery Fields

### Rule: Child relationship subqueries create nested lists

### ❌ BAD: Accessing Subquery Fields Incorrectly

```apex
// Query with contact subquery
List<Account> accounts = [
    SELECT Id, Name,
           (SELECT Id, Name FROM Contacts)
    FROM Account
];

for (Account acc : accounts) {
    // ERROR: Contacts is a List, not a single Contact
    String contactName = acc.Contacts.Name;

    // ERROR: Cannot access unqueried field from subquery
    for (Contact c : acc.Contacts) {
        String email = c.Email;  // Email not in subquery SELECT!
    }
}
```

### ✅ GOOD: Proper Subquery Field Access

```apex
// Query all needed fields in subquery
List<Account> accounts = [
    SELECT Id, Name,
           (SELECT Id, Name, Email, Phone FROM Contacts)
    FROM Account
];

for (Account acc : accounts) {
    // Contacts is a List<Contact>
    List<Contact> contacts = acc.Contacts;

    if (contacts != null && !contacts.isEmpty()) {
        for (Contact c : contacts) {
            String name = c.Name;    // OK - in subquery SELECT
            String email = c.Email;  // OK - in subquery SELECT
            String phone = c.Phone;  // OK - in subquery SELECT
        }
    }
}
```

### Subquery Null Safety

```apex
List<Account> accounts = [
    SELECT Id, (SELECT Id FROM Contacts)
    FROM Account
];

for (Account acc : accounts) {
    // Subquery result can be null if no child records
    if (acc.Contacts != null) {
        for (Contact c : acc.Contacts) {
            // Process contact
        }
    }

    // Or use null-safe size check
    Integer contactCount = acc.Contacts?.size() ?? 0;
}
```

---

## Validation Patterns

### Pattern 1: Field-to-Query Mapping

Create a systematic approach to track field usage:

```apex
public class AccountProcessor {
    // Document required fields at the top
    private static final Set<String> REQUIRED_FIELDS = new Set<String>{
        'Id', 'Name', 'Industry', 'Description', 'AnnualRevenue',
        'OwnerId', 'Owner.Name', 'Owner.Email'
    };

    // Single method for consistent querying
    public static List<Account> queryAccounts(Set<Id> accountIds) {
        return [
            SELECT Id, Name, Industry, Description, AnnualRevenue,
                   OwnerId, Owner.Name, Owner.Email
            FROM Account
            WHERE Id IN :accountIds
        ];
    }

    public static void processAccounts(List<Account> accounts) {
        for (Account acc : accounts) {
            // All fields in REQUIRED_FIELDS are safe to access
            if (acc.Industry == 'Technology') {
                acc.Description = 'Tech: ' + acc.Name;
            }
        }
    }
}
```

### Pattern 2: Selector Layer

Use a selector pattern to centralize query field management:

```apex
public class AccountSelector {

    // Default fields for most operations
    private static final List<String> DEFAULT_FIELDS = new List<String>{
        'Id', 'Name', 'Industry', 'Type', 'OwnerId'
    };

    // Extended fields for detailed views
    private static final List<String> DETAIL_FIELDS = new List<String>{
        'Id', 'Name', 'Industry', 'Type', 'OwnerId',
        'Description', 'AnnualRevenue', 'NumberOfEmployees',
        'BillingCity', 'BillingState', 'BillingCountry',
        'Owner.Name', 'Owner.Email'
    };

    public List<Account> selectById(Set<Id> ids) {
        return selectByIdWithFields(ids, DEFAULT_FIELDS);
    }

    public List<Account> selectByIdDetailed(Set<Id> ids) {
        return selectByIdWithFields(ids, DETAIL_FIELDS);
    }

    private List<Account> selectByIdWithFields(Set<Id> ids, List<String> fields) {
        String query = 'SELECT ' + String.join(fields, ', ') +
                       ' FROM Account WHERE Id IN :ids';
        return Database.query(query);
    }
}
```

### Pattern 3: Field Validation Helper

```apex
public class SObjectFieldValidator {

    /**
     * Check if a field was queried on an sObject
     * @param obj The sObject to check
     * @param fieldName The API name of the field
     * @return true if the field is populated (was queried)
     */
    public static Boolean isFieldPopulated(SObject obj, String fieldName) {
        try {
            obj.get(fieldName);
            return true;
        } catch (SObjectException e) {
            return false;
        }
    }

    /**
     * Get field value with default if not queried
     * @param obj The sObject
     * @param fieldName The field API name
     * @param defaultValue Value to return if field not queried
     * @return The field value or default
     */
    public static Object getFieldOrDefault(SObject obj, String fieldName, Object defaultValue) {
        try {
            Object value = obj.get(fieldName);
            return value != null ? value : defaultValue;
        } catch (SObjectException e) {
            return defaultValue;
        }
    }
}
```

---

## Quick Reference: Field Coverage Checklist

Before running code that processes SOQL results:

### Direct Fields
- [ ] All fields in `if` conditions are queried
- [ ] All fields on left side of assignments are queried
- [ ] All fields passed to methods are queried
- [ ] All fields used in map keys/values are queried

### Relationship Fields
- [ ] Parent fields use dot notation (e.g., `Account.Name`)
- [ ] Parent object null checks before field access
- [ ] Relationship traversal doesn't exceed 5 levels

### Subqueries
- [ ] Child records accessed as List, not single record
- [ ] Subquery SELECT includes all accessed child fields
- [ ] Null check before iterating subquery results

### Dynamic Access
- [ ] Fields accessed via `get(fieldName)` are queried
- [ ] Dynamic queries include all needed fields

---

## Common LLM Mistakes Summary

| Mistake | Example | Fix |
|---------|---------|-----|
| Query subset, use superset | Query `Id, Name`, use `Industry` | Add `Industry` to SELECT |
| Forget relationship field | Use `c.Account.Name` without querying | Add `Account.Name` to SELECT |
| Assume AccountId = Account | Query `AccountId`, access `Account.Name` | Query `Account.Name` explicitly |
| Wrong subquery access | `acc.Contacts.Email` | `for (Contact c : acc.Contacts) { c.Email }` |
| Missing subquery field | Subquery `SELECT Id`, use `Email` | Add `Email` to subquery SELECT |

---

## Reference

- **SOQL Anti-Patterns**: See `references/anti-patterns.md` for general SOQL mistakes
- **Selector Patterns**: See `references/selector-patterns.md` for query organization
