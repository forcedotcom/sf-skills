<!-- Parent: querying-soql/SKILL.md -->
# SOQL Anti-Patterns: What to Avoid

A catalog of common SOQL mistakes and their solutions. Avoiding these patterns will help you stay within governor limits, improve query performance, and write more maintainable code.

---

## Anti-Pattern #1: SOQL Inside Loops

**The Problem**: Executing queries inside a loop quickly exhausts the 100 SOQL query limit.

```apex
// ❌ ANTI-PATTERN: Query per record
for (Contact c : Trigger.new) {
    Account a = [SELECT Name FROM Account WHERE Id = :c.AccountId];
    c.Account_Name__c = a.Name;
}
// 200 contacts = 200 queries = LIMIT EXCEEDED
```

**The Solution**: Query once, use a Map for lookups.

```apex
// ✅ CORRECT: Single query with Map lookup
Set<Id> accountIds = new Set<Id>();
for (Contact c : Trigger.new) {
    accountIds.add(c.AccountId);
}

Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
);

for (Contact c : Trigger.new) {
    Account a = accountMap.get(c.AccountId);
    if (a != null) {
        c.Account_Name__c = a.Name;
    }
}
// 200 contacts = 1 query = SAFE
```

**Key Insight**: Collect IDs first, query once with `IN` clause, then use Map for O(1) lookups.

---

## Anti-Pattern #2: Non-Selective WHERE Clauses

**The Problem**: Queries on non-indexed fields cause full table scans, which fail on large objects (100k+ records).

```apex
// ❌ ANTI-PATTERN: Non-selective filter
SELECT Id FROM Lead WHERE Status = 'Open'
// Status is not indexed - scans ALL Lead records
```

**The Solution**: Add an indexed field to make the query selective.

```apex
// ✅ CORRECT: Add indexed field filter
SELECT Id FROM Lead
WHERE Status = 'Open'
AND CreatedDate = LAST_N_DAYS:30
// CreatedDate is indexed - uses index

// ✅ ALTERNATIVE: Use OwnerId (indexed)
SELECT Id FROM Lead
WHERE Status = 'Open'
AND OwnerId = :UserInfo.getUserId()
```

**Indexed Fields** (Always use these in WHERE):
- `Id`, `Name`, `OwnerId`, `CreatedDate`, `LastModifiedDate`
- `RecordTypeId`, External ID fields, Master-Detail fields
- Standard indexed fields: `Account.AccountNumber`, `Contact.Email`, `Case.CaseNumber`

---

## Anti-Pattern #3: Leading Wildcards

**The Problem**: `LIKE '%value'` cannot use indexes and scans all records.

```apex
// ❌ ANTI-PATTERN: Leading wildcard
SELECT Id FROM Account WHERE Name LIKE '%Corporation'
// Cannot use index - full table scan
```

**The Solution**: Use trailing wildcards or exact matches.

```apex
// ✅ CORRECT: Trailing wildcard (uses index)
SELECT Id FROM Account WHERE Name LIKE 'Acme%'

// ✅ CORRECT: Exact match
SELECT Id FROM Account WHERE Name = 'Acme Corporation'

// ✅ CORRECT: Contains check (if absolutely necessary)
// Do the filtering in Apex after a selective query
List<Account> allAccounts = [
    SELECT Id, Name FROM Account
    WHERE CreatedDate = THIS_YEAR
];
List<Account> filtered = new List<Account>();
for (Account a : allAccounts) {
    if (a.Name.contains('Corporation')) {
        filtered.add(a);
    }
}
```

---

## Anti-Pattern #4: Negative Operators

**The Problem**: `!=`, `NOT IN`, `NOT LIKE` often prevent index usage.

```apex
// ❌ ANTI-PATTERN: Negative operators
SELECT Id FROM Opportunity WHERE StageName != 'Closed Lost'
SELECT Id FROM Contact WHERE AccountId NOT IN :excludedIds
```

**The Solution**: Query for what you want, not what you don't want.

```apex
// ✅ CORRECT: Positive filter with specific values
SELECT Id FROM Opportunity
WHERE StageName IN ('Prospecting', 'Qualification', 'Proposal', 'Negotiation')

// ✅ CORRECT: Use a formula field for complex exclusions
// Create IsExcluded__c formula, then:
SELECT Id FROM Contact WHERE IsExcluded__c = false
```

---

## Anti-Pattern #5: Querying for NULL

**The Problem**: `WHERE Field = null` is non-selective and scans all records.

```apex
// ❌ ANTI-PATTERN: Null check in WHERE
SELECT Id FROM Contact WHERE Email = null
// Non-selective - scans all contacts
```

**The Solution**: Combine with selective filters or redesign data model.

```apex
// ✅ CORRECT: Add selective filter
SELECT Id FROM Contact
WHERE Email = null
AND CreatedDate = LAST_N_DAYS:30

// ✅ BETTER: Use a checkbox field
// Create HasEmail__c formula checkbox
SELECT Id FROM Contact WHERE HasEmail__c = false
```

---

## Anti-Pattern #6: SELECT * (All Fields)

**The Problem**: Querying all fields wastes resources and can hit heap limits.

```apex
// ❌ ANTI-PATTERN: Selecting everything
SELECT FIELDS(ALL) FROM Account LIMIT 200
// Loads ALL fields into memory

// ❌ ANTI-PATTERN: Listing every field manually
SELECT Id, Name, Description, BillingStreet, BillingCity,
       BillingState, BillingPostalCode, BillingCountry, ...
FROM Account
```

**The Solution**: Query only the fields you need.

```apex
// ✅ CORRECT: Minimal field selection
SELECT Id, Name, Industry FROM Account

// ✅ FOR DISPLAY: Just display fields
SELECT Id, Name FROM Account

// ✅ FOR PROCESSING: Just processing fields
SELECT Id, Status__c, ProcessedDate__c FROM Account
```

---

## Anti-Pattern #7: No LIMIT on Queries

**The Problem**: Unbounded queries can return 50,000 records and consume heap memory.

```apex
// ❌ ANTI-PATTERN: No limit
SELECT Id, Name FROM Account
// Could return 50,000 records!

// ❌ ANTI-PATTERN: Excessive limit
SELECT Id, Name FROM Account LIMIT 50000
```

**The Solution**: Use appropriate limits for your use case.

```apex
// ✅ CORRECT: Reasonable limit for UI display
SELECT Id, Name FROM Account LIMIT 200

// ✅ CORRECT: Pagination
SELECT Id, Name FROM Account
ORDER BY Name
LIMIT 50 OFFSET 0

// ✅ CORRECT: Single record lookup
SELECT Id, Name FROM Account WHERE Name = 'Acme' LIMIT 1

// ✅ CORRECT: Existence check
SELECT Id FROM Account WHERE Name = 'Acme' LIMIT 1
// In Apex: if (!results.isEmpty()) { /* exists */ }
```

---

## Anti-Pattern #8: Deep Relationship Traversal

**The Problem**: Deep nesting (>3 levels) hurts performance and readability.

```apex
// ❌ ANTI-PATTERN: Deep traversal
SELECT Id,
       Account.Owner.Manager.Department.Name
FROM Contact
// 4 levels deep - hard to maintain, performance hit
```

**The Solution**: Flatten queries or use multiple queries.

```apex
// ✅ CORRECT: Flatten to 1-2 levels
SELECT Id, Account.Name, Account.OwnerId FROM Contact

// Then query Owner separately if needed
Map<Id, User> owners = new Map<Id, User>(
    [SELECT Id, ManagerId FROM User WHERE Id IN :ownerIds]
);
```

---

## Anti-Pattern #9: Unfiltered Subqueries

**The Problem**: Child subqueries without filters can return massive datasets.

```apex
// ❌ ANTI-PATTERN: Unfiltered subquery
SELECT Id,
       (SELECT Id FROM Contacts),
       (SELECT Id FROM Opportunities)
FROM Account
// Could return thousands of child records per account
```

**The Solution**: Always filter and limit subqueries.

```apex
// ✅ CORRECT: Filtered and limited subqueries
SELECT Id,
       (SELECT Id, Name FROM Contacts
        WHERE IsActive__c = true
        LIMIT 5),
       (SELECT Id, Name FROM Opportunities
        WHERE StageName != 'Closed Lost'
        LIMIT 5)
FROM Account
WHERE Industry = 'Technology'
```

---

## Anti-Pattern #10: Formula Fields in WHERE

**The Problem**: Formula fields are not indexed and require full table scans.

```apex
// ❌ ANTI-PATTERN: Filter on formula field
SELECT Id FROM Opportunity
WHERE Days_Since_Created__c > 30
// Formula field - cannot use index
```

**The Solution**: Use the underlying indexed field.

```apex
// ✅ CORRECT: Use base field
SELECT Id FROM Opportunity
WHERE CreatedDate < LAST_N_DAYS:30

// ✅ ALTERNATIVE: Store computed value in regular field
// Use workflow/flow to update a Number field
SELECT Id FROM Opportunity
WHERE Days_Open__c > 30
```

---

## Quick Reference: Selectivity Rules

```
A filter is SELECTIVE when:
├── Uses an indexed field, AND
├── Returns < 10% of first million records, OR
├── Returns < 5% of records beyond first million
└── Absolute max: 333,333 records (1M / 3)
```

**Always Indexed Fields**:
- `Id`, `Name`, `OwnerId`, `CreatedDate`, `LastModifiedDate`
- `RecordTypeId`, External ID fields, Master-Detail relationship fields

**Request Custom Index**: Contact Salesforce Support with:
- Object name and field API name
- Sample SOQL query
- Cardinality (unique values count)
- Business justification

---

## Testing Checklist

Before deploying SOQL to production:

1. [ ] Run Query Plan tool (Developer Console or CLI)
2. [ ] Verify `LeadingOperationType` is "Index" not "TableScan"
3. [ ] Test with 200+ records in trigger context
4. [ ] Verify query count stays under 100 per transaction
5. [ ] Check heap usage for large result sets

```bash
# CLI Query Plan
sf data query \
  --query "SELECT Id FROM Account WHERE Name = 'Test'" \
  --target-org my-org \
  --use-tooling-api \
  --plan
```
