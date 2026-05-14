<!-- Parent: querying-soql/SKILL.md -->

# Query Optimization & Governor Limits

## Indexing Strategy

**Indexed Fields** (Always Selective):
- Id, Name, OwnerId, CreatedDate, LastModifiedDate, RecordTypeId
- External ID fields, Master-Detail relationship fields
- Lookup fields (when unique)

**Standard Indexed Fields by Object**:
- Account: AccountNumber, Site
- Contact: Email
- Lead: Email
- Case: CaseNumber

## Selectivity Rules

```
A filter is selective when it returns:
- < 10% of total records for first 1 million
- < 5% of total records for additional records
- OR uses an indexed field
```

## Optimization Patterns

```sql
-- ❌ NON-SELECTIVE (scans all records)
SELECT Id FROM Lead WHERE Status = 'Open'

-- ✅ SELECTIVE (uses index + selective filter)
SELECT Id FROM Lead
WHERE Status = 'Open'
AND CreatedDate = LAST_N_DAYS:30
LIMIT 10000

-- ❌ LEADING WILDCARD (can't use index)
SELECT Id FROM Account WHERE Name LIKE '%corp'

-- ✅ TRAILING WILDCARD (uses index)
SELECT Id FROM Account WHERE Name LIKE 'Acme%'
```

## Query Plan Analysis

```bash
# Get query plan
sf data query \
  --query "SELECT Id FROM Account WHERE Name = 'Test'" \
  --target-org my-org \
  --use-tooling-api \
  --plan
```

**Plan Output Interpretation**:
- `Cardinality`: Estimated rows returned
- `Cost`: Relative query cost (lower is better)
- `Fields`: Index fields used
- `LeadingOperationType`: How the query starts (Index vs TableScan)

---

## Governor Limits

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| Total SOQL Queries | 100 | 200 |
| Records Retrieved | 50,000 | 50,000 |
| Query Rows (queryMore) | 2,000 | 2,000 |
| Query Locator Rows | 10 million | 10 million |

### Efficient Patterns

```sql
-- ❌ Query all, filter in Apex
SELECT Id, Name FROM Account
-- Then filter 50,000 records in Apex

-- ✅ Filter in SOQL
SELECT Id, Name FROM Account
WHERE Industry = 'Technology' AND IsActive__c = true
LIMIT 1000

-- ❌ Multiple queries in loop
for (Contact c : contacts) {
    Account a = [SELECT Name FROM Account WHERE Id = :c.AccountId];
}

-- ✅ Single query with Map
Map<Id, Account> accounts = new Map<Id, Account>(
    [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
);
```

## SOQL FOR Loops

```apex
// For large datasets - doesn't load all into heap
for (Account acc : [SELECT Id, Name FROM Account WHERE Industry = 'Technology']) {
    // Process one record at a time
    // Governor: Uses queryMore internally (200 at a time)
}

// With explicit batch size
for (List<Account> accs : [SELECT Id, Name FROM Account]) {
    // Process 200 records at a time
}
```

## Security Patterns

### WITH SECURITY_ENFORCED

```sql
-- Throws exception if user lacks FLS
SELECT Id, Name, Phone
FROM Account
WITH SECURITY_ENFORCED
```

### WITH USER_MODE / SYSTEM_MODE

```sql
-- Respects sharing rules (default in Apex)
SELECT Id, Name FROM Account WITH USER_MODE

-- Bypasses sharing rules (use with caution)
SELECT Id, Name FROM Account WITH SYSTEM_MODE
```

### In Apex: stripInaccessible

```apex
// Strip inaccessible fields instead of throwing
SObjectAccessDecision decision = Security.stripInaccessible(
    AccessType.READABLE,
    [SELECT Id, Name, SecretField__c FROM Account]
);
List<Account> safeAccounts = decision.getRecords();
```
