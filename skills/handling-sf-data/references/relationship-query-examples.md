<!-- Parent: handling-sf-data/SKILL.md -->
# Relationship Query Examples

Comprehensive SOQL relationship patterns for complex data retrieval.

## Parent-to-Child Queries (Subqueries)

### Basic Subquery
```sql
SELECT Id, Name,
    (SELECT Id, FirstName, LastName, Email FROM Contacts)
FROM Account
WHERE Industry = 'Technology'
```

```bash
sf data query \
  --query "SELECT Id, Name, (SELECT Id, FirstName, LastName FROM Contacts) FROM Account WHERE Industry = 'Technology' LIMIT 5" \
  --target-org dev \
  --json
```

### Multiple Subqueries
```sql
SELECT Id, Name,
    (SELECT Id, Name, Title FROM Contacts),
    (SELECT Id, Name, Amount, StageName FROM Opportunities),
    (SELECT Id, CaseNumber, Subject FROM Cases)
FROM Account
WHERE Id = '001XXXXXXXXXXXX'
```

### Filtered Subquery
```sql
SELECT Id, Name,
    (SELECT Id, Name, Amount
     FROM Opportunities
     WHERE StageName = 'Closed Won'
     ORDER BY Amount DESC
     LIMIT 5)
FROM Account
WHERE AnnualRevenue > 1000000
```

## Child-to-Parent Queries (Dot Notation)

### Basic Relationship
```sql
SELECT Id, FirstName, LastName,
       Account.Name, Account.Industry
FROM Contact
WHERE Account.Industry = 'Technology'
```

```bash
sf data query \
  --query "SELECT Id, FirstName, LastName, Account.Name, Account.Industry FROM Contact WHERE Account.Industry = 'Technology' LIMIT 10" \
  --target-org dev
```

### Multi-Level Traversal
```sql
SELECT Id, Name, Amount,
       Account.Name,
       Account.Owner.Name,
       Account.Owner.Profile.Name
FROM Opportunity
WHERE Account.Industry = 'Finance'
```

### Custom Object Relationships
```sql
-- __r suffix for custom relationships
SELECT Id, Name,
       Custom_Parent__r.Name,
       Custom_Parent__r.Custom_Field__c
FROM Custom_Child__c
```

## Polymorphic Relationships (TYPEOF)

### Task Who/What Fields
```sql
SELECT Id, Subject, Status,
    TYPEOF Who
        WHEN Contact THEN FirstName, LastName, Email
        WHEN Lead THEN FirstName, LastName, Company
    END,
    TYPEOF What
        WHEN Account THEN Name, Industry
        WHEN Opportunity THEN Name, Amount, StageName
    END
FROM Task
WHERE Status = 'Open'
```

```bash
sf data query \
  --query "SELECT Id, Subject, TYPEOF Who WHEN Contact THEN FirstName, LastName WHEN Lead THEN FirstName, LastName END FROM Task WHERE Status = 'Open' LIMIT 5" \
  --target-org dev \
  --json
```

### Event Relationships
```sql
SELECT Id, Subject, StartDateTime,
    TYPEOF Who
        WHEN Contact THEN FirstName, LastName, Account.Name
        WHEN Lead THEN Name, Company
    END
FROM Event
WHERE StartDateTime >= TODAY
```

## Aggregate Queries

### Basic Aggregation
```sql
SELECT Industry, COUNT(Id) total, SUM(AnnualRevenue) revenue
FROM Account
GROUP BY Industry
HAVING COUNT(Id) > 10
ORDER BY SUM(AnnualRevenue) DESC
```

```bash
sf data query \
  --query "SELECT Industry, COUNT(Id) total, SUM(AnnualRevenue) revenue FROM Account GROUP BY Industry HAVING COUNT(Id) > 5" \
  --target-org dev
```

### Rollup by Date
```sql
SELECT CALENDAR_MONTH(CloseDate) month,
       SUM(Amount) total,
       COUNT(Id) deals
FROM Opportunity
WHERE CloseDate = THIS_YEAR
AND StageName = 'Closed Won'
GROUP BY CALENDAR_MONTH(CloseDate)
ORDER BY CALENDAR_MONTH(CloseDate)
```

### Aggregate with Relationships
```sql
SELECT Account.Industry,
       COUNT(Id) opportunities,
       SUM(Amount) pipeline
FROM Opportunity
WHERE StageName NOT IN ('Closed Won', 'Closed Lost')
GROUP BY Account.Industry
```

## Semi-Joins and Anti-Joins

### Semi-Join (Records WITH Related)
```sql
-- Accounts that HAVE Opportunities
SELECT Id, Name
FROM Account
WHERE Id IN (
    SELECT AccountId FROM Opportunity WHERE Amount > 100000
)
```

### Anti-Join (Records WITHOUT Related)
```sql
-- Accounts WITHOUT Contacts
SELECT Id, Name
FROM Account
WHERE Id NOT IN (
    SELECT AccountId FROM Contact WHERE AccountId != null
)
```

### Complex Semi-Join
```sql
-- Contacts at Accounts with large deals
SELECT Id, FirstName, LastName
FROM Contact
WHERE AccountId IN (
    SELECT AccountId
    FROM Opportunity
    WHERE Amount > 500000
    AND StageName = 'Closed Won'
)
```

## Date Functions and Filters

### Date Literals
```sql
SELECT Id, Name, CreatedDate
FROM Account
WHERE CreatedDate = THIS_WEEK
-- Also: TODAY, YESTERDAY, THIS_MONTH, LAST_MONTH, THIS_YEAR, LAST_N_DAYS:7
```

### Date Functions in SELECT
```sql
SELECT DAY_IN_MONTH(CreatedDate) day,
       WEEK_IN_YEAR(CreatedDate) week,
       CALENDAR_YEAR(CreatedDate) year,
       COUNT(Id) count
FROM Lead
GROUP BY DAY_IN_MONTH(CreatedDate),
         WEEK_IN_YEAR(CreatedDate),
         CALENDAR_YEAR(CreatedDate)
```

## Query Optimization Tips

### Use Indexed Fields
```sql
-- GOOD: Query on indexed fields (Id, Name, CreatedDate, SystemModstamp)
SELECT Id, Name FROM Account WHERE Name LIKE 'Acme%'

-- BAD: Query on non-indexed custom field (full table scan)
SELECT Id, Name FROM Account WHERE Custom_Unindexed__c = 'value'
```

### Limit Records Retrieved
```sql
-- Always use LIMIT for exploration
SELECT Id, Name FROM Account LIMIT 100

-- Use OFFSET for pagination
SELECT Id, Name FROM Account LIMIT 100 OFFSET 200
```

### Select Only Needed Fields
```sql
-- GOOD: Only needed fields
SELECT Id, Name, Industry FROM Account

-- BAD: Selecting all fields
SELECT Id, Name, Industry, Description, BillingStreet, BillingCity,
       BillingState, BillingPostalCode, BillingCountry, ...
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid relationship` | Wrong relationship name | Check `__r` suffix for custom |
| `MALFORMED_QUERY` | Syntax error | Validate SOQL syntax |
| `SELECT too complex` | Too many levels | Max 5 levels of relationships |
| `Subquery limit` | >20 subqueries | Reduce number of child queries |
| `Non-selective query` | No indexed filter | Add indexed field to WHERE |
