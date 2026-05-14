<!-- Parent: querying-soql/SKILL.md -->

# SOQL Syntax Reference

## Basic Query Structure

```sql
SELECT field1, field2, ...
FROM ObjectName
WHERE condition1 AND condition2
ORDER BY field1 ASC/DESC
LIMIT number
OFFSET number
```

### Field Selection

```sql
-- Specific fields (recommended)
SELECT Id, Name, Industry FROM Account

-- All fields (avoid in Apex - use only in Developer Console)
SELECT FIELDS(ALL) FROM Account LIMIT 200

-- Standard fields only
SELECT FIELDS(STANDARD) FROM Account
```

### WHERE Clause Operators

| Operator | Example | Notes |
|----------|---------|-------|
| `=` | `Name = 'Acme'` | Exact match |
| `!=` | `Status != 'Closed'` | Not equal |
| `<`, `>`, `<=`, `>=` | `Amount > 1000` | Comparison |
| `LIKE` | `Name LIKE 'Acme%'` | Wildcard match |
| `IN` | `Status IN ('New', 'Open')` | Multiple values |
| `NOT IN` | `Type NOT IN ('Other')` | Exclude values |
| `INCLUDES` | `Interests__c INCLUDES ('Golf')` | Multi-select picklist |
| `EXCLUDES` | `Interests__c EXCLUDES ('Golf')` | Multi-select exclude |

### Date Literals

| Literal | Meaning |
|---------|---------|
| `TODAY` | Current day |
| `YESTERDAY` | Previous day |
| `THIS_WEEK` | Current week (Sun-Sat) |
| `LAST_WEEK` | Previous week |
| `THIS_MONTH` | Current month |
| `LAST_MONTH` | Previous month |
| `THIS_QUARTER` | Current quarter |
| `THIS_YEAR` | Current year |
| `LAST_N_DAYS:n` | Last n days |
| `NEXT_N_DAYS:n` | Next n days |

```sql
-- Created in last 30 days
SELECT Id FROM Account WHERE CreatedDate = LAST_N_DAYS:30

-- Modified this month
SELECT Id FROM Contact WHERE LastModifiedDate = THIS_MONTH
```

---

## Relationship Queries

### Child-to-Parent (Dot Notation)

```sql
-- Access parent fields
SELECT Id, Name, Account.Name, Account.Industry
FROM Contact
WHERE Account.AnnualRevenue > 1000000

-- Up to 5 levels
SELECT Id, Contact.Account.Owner.Manager.Name
FROM Case
```

### Parent-to-Child (Subquery)

```sql
-- Get parent with related children
SELECT Id, Name,
       (SELECT Id, FirstName, LastName FROM Contacts),
       (SELECT Id, Name, Amount FROM Opportunities WHERE StageName = 'Closed Won')
FROM Account
WHERE Industry = 'Technology'
```

### Standard Relationship Names

| Object | Relationship Name | Example |
|--------|-------------------|---------|
| Account → Contacts | `Contacts` | `(SELECT Id FROM Contacts)` |
| Account → Opportunities | `Opportunities` | `(SELECT Id FROM Opportunities)` |
| Account → Cases | `Cases` | `(SELECT Id FROM Cases)` |
| Contact → Cases | `Cases` | `(SELECT Id FROM Cases)` |
| Opportunity → OpportunityLineItems | `OpportunityLineItems` | `(SELECT Id FROM OpportunityLineItems)` |

### Custom Object Relationships

```sql
-- Custom relationship: add __r suffix
SELECT Id, Name, Custom_Object__r.Name
FROM Another_Object__c

-- Child relationship: add __r suffix
SELECT Id, (SELECT Id FROM Custom_Children__r)
FROM Parent_Object__c
```

---

## Aggregate Queries

### Basic Aggregates

```sql
-- Count all records
SELECT COUNT() FROM Account

-- Count with alias
SELECT COUNT(Id) cnt FROM Account

-- Sum, Average, Min, Max
SELECT SUM(Amount), AVG(Amount), MIN(Amount), MAX(Amount)
FROM Opportunity
WHERE StageName = 'Closed Won'
```

### GROUP BY

```sql
-- Count by field
SELECT Industry, COUNT(Id)
FROM Account
GROUP BY Industry

-- Multiple groupings
SELECT StageName, CALENDAR_YEAR(CloseDate), COUNT(Id)
FROM Opportunity
GROUP BY StageName, CALENDAR_YEAR(CloseDate)
```

### HAVING Clause

```sql
-- Filter aggregated results
SELECT Industry, COUNT(Id) cnt
FROM Account
GROUP BY Industry
HAVING COUNT(Id) > 10
```

### GROUP BY ROLLUP

```sql
-- Subtotals
SELECT LeadSource, Rating, COUNT(Id)
FROM Lead
GROUP BY ROLLUP(LeadSource, Rating)
```

---

## Advanced Features

### Polymorphic Relationships (What)

```sql
-- Query polymorphic fields
SELECT Id, What.Name, What.Type
FROM Task
WHERE What.Type IN ('Account', 'Opportunity')

-- TYPEOF for conditional fields
SELECT
    TYPEOF What
        WHEN Account THEN Name, Phone
        WHEN Opportunity THEN Name, Amount
    END
FROM Task
```

### Semi-Joins and Anti-Joins

```sql
-- Semi-join: Records that HAVE related records
SELECT Id, Name FROM Account
WHERE Id IN (SELECT AccountId FROM Contact)

-- Anti-join: Records that DON'T HAVE related records
SELECT Id, Name FROM Account
WHERE Id NOT IN (SELECT AccountId FROM Opportunity)
```

### Format and Currency

```sql
-- Format currency/date in results
SELECT FORMAT(Amount), FORMAT(CloseDate) FROM Opportunity

-- Convert to user's currency
SELECT Id, convertCurrency(Amount) FROM Opportunity
```
