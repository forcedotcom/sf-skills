<!-- Parent: querying-soql/SKILL.md -->
# SOQL Quick Reference

## Query Structure

```sql
SELECT fields
FROM object
[WHERE conditions]
[WITH filter]
[GROUP BY fields]
[HAVING conditions]
[ORDER BY fields [ASC|DESC] [NULLS FIRST|LAST]]
[LIMIT number]
[OFFSET number]
[FOR UPDATE]
```

---

## Operators

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equal | `Name = 'Acme'` |
| `!=` | Not equal | `Status != 'Closed'` |
| `<` | Less than | `Amount < 1000` |
| `<=` | Less than or equal | `Amount <= 1000` |
| `>` | Greater than | `Amount > 1000` |
| `>=` | Greater than or equal | `Amount >= 1000` |
| `LIKE` | Pattern match | `Name LIKE 'Acme%'` |
| `IN` | In list | `Status IN ('New', 'Open')` |
| `NOT IN` | Not in list | `Type NOT IN ('Other')` |
| `INCLUDES` | Multi-select contains | `Skills__c INCLUDES ('Java')` |
| `EXCLUDES` | Multi-select excludes | `Skills__c EXCLUDES ('Java')` |

### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `AND` | Both conditions | `A = 1 AND B = 2` |
| `OR` | Either condition | `A = 1 OR B = 2` |
| `NOT` | Negate condition | `NOT (A = 1)` |

### LIKE Patterns

| Pattern | Matches |
|---------|---------|
| `'Acme%'` | Starts with "Acme" |
| `'%Corp'` | Ends with "Corp" |
| `'%test%'` | Contains "test" |
| `'A_me'` | "A" + any char + "me" |

---

## Date Literals

### Relative Dates

| Literal | Description |
|---------|-------------|
| `TODAY` | Current day |
| `YESTERDAY` | Previous day |
| `TOMORROW` | Next day |
| `THIS_WEEK` | Current week (Sun-Sat) |
| `LAST_WEEK` | Previous week |
| `NEXT_WEEK` | Next week |
| `THIS_MONTH` | Current month |
| `LAST_MONTH` | Previous month |
| `NEXT_MONTH` | Next month |
| `THIS_QUARTER` | Current quarter |
| `LAST_QUARTER` | Previous quarter |
| `NEXT_QUARTER` | Next quarter |
| `THIS_YEAR` | Current year |
| `LAST_YEAR` | Previous year |
| `NEXT_YEAR` | Next year |
| `THIS_FISCAL_QUARTER` | Current fiscal quarter |
| `THIS_FISCAL_YEAR` | Current fiscal year |

### N Days/Weeks/Months/Years

| Literal | Description |
|---------|-------------|
| `LAST_N_DAYS:n` | Last n days |
| `NEXT_N_DAYS:n` | Next n days |
| `LAST_N_WEEKS:n` | Last n weeks |
| `NEXT_N_WEEKS:n` | Next n weeks |
| `LAST_N_MONTHS:n` | Last n months |
| `NEXT_N_MONTHS:n` | Next n months |
| `LAST_N_QUARTERS:n` | Last n quarters |
| `NEXT_N_QUARTERS:n` | Next n quarters |
| `LAST_N_YEARS:n` | Last n years |
| `NEXT_N_YEARS:n` | Next n years |

### Specific Dates

```sql
-- Date only
WHERE CloseDate = 2024-12-31

-- DateTime
WHERE CreatedDate >= 2024-01-01T00:00:00Z
```

---

## Aggregate Functions

| Function | Description | Example |
|----------|-------------|---------|
| `COUNT()` | Count all rows | `SELECT COUNT() FROM Account` |
| `COUNT(field)` | Count non-null values | `SELECT COUNT(Email) FROM Contact` |
| `COUNT_DISTINCT(field)` | Count unique values | `SELECT COUNT_DISTINCT(Industry) FROM Account` |
| `SUM(field)` | Sum of values | `SELECT SUM(Amount) FROM Opportunity` |
| `AVG(field)` | Average of values | `SELECT AVG(Amount) FROM Opportunity` |
| `MIN(field)` | Minimum value | `SELECT MIN(Amount) FROM Opportunity` |
| `MAX(field)` | Maximum value | `SELECT MAX(Amount) FROM Opportunity` |

---

## Date Functions

| Function | Returns | Example |
|----------|---------|---------|
| `CALENDAR_YEAR(date)` | Year (e.g., 2024) | `SELECT CALENDAR_YEAR(CloseDate) FROM Opportunity` |
| `CALENDAR_QUARTER(date)` | Quarter (1-4) | `SELECT CALENDAR_QUARTER(CloseDate) FROM Opportunity` |
| `CALENDAR_MONTH(date)` | Month (1-12) | `SELECT CALENDAR_MONTH(CloseDate) FROM Opportunity` |
| `DAY_IN_MONTH(date)` | Day (1-31) | `SELECT DAY_IN_MONTH(CreatedDate) FROM Account` |
| `DAY_IN_WEEK(date)` | Day (1=Sun, 7=Sat) | `SELECT DAY_IN_WEEK(CreatedDate) FROM Account` |
| `DAY_IN_YEAR(date)` | Day (1-366) | `SELECT DAY_IN_YEAR(CreatedDate) FROM Account` |
| `WEEK_IN_MONTH(date)` | Week (1-5) | `SELECT WEEK_IN_MONTH(CreatedDate) FROM Account` |
| `WEEK_IN_YEAR(date)` | Week (1-53) | `SELECT WEEK_IN_YEAR(CreatedDate) FROM Account` |
| `HOUR_IN_DAY(date)` | Hour (0-23) | `SELECT HOUR_IN_DAY(CreatedDate) FROM Account` |
| `FISCAL_YEAR(date)` | Fiscal year | `SELECT FISCAL_YEAR(CloseDate) FROM Opportunity` |
| `FISCAL_QUARTER(date)` | Fiscal quarter | `SELECT FISCAL_QUARTER(CloseDate) FROM Opportunity` |
| `FISCAL_MONTH(date)` | Fiscal month | `SELECT FISCAL_MONTH(CloseDate) FROM Opportunity` |

---

## Relationship Queries

### Child-to-Parent (Dot Notation)

```sql
-- Standard objects
SELECT Contact.Name, Contact.Account.Name FROM Contact

-- Custom objects (use __r)
SELECT Child__c.Name, Child__c.Parent__r.Name FROM Child__c
```

### Parent-to-Child (Subquery)

```sql
-- Standard objects
SELECT Id, (SELECT Id FROM Contacts) FROM Account

-- Custom objects (use __r)
SELECT Id, (SELECT Id FROM Children__r) FROM Parent__c
```

---

## WITH Clauses

| Clause | Description |
|--------|-------------|
| `WITH SECURITY_ENFORCED` | Enforce FLS (throws exception if no access) |
| `WITH USER_MODE` | Respect sharing and FLS |
| `WITH SYSTEM_MODE` | Bypass sharing rules |

---

## Governor Limits

| Limit | Synchronous | Asynchronous |
|-------|-------------|--------------|
| Total SOQL Queries | 100 | 200 |
| Records Retrieved | 50,000 | 50,000 |
| QueryLocator Rows | 10,000,000 | 10,000,000 |
| OFFSET Maximum | 2,000 | 2,000 |
| Subqueries | 20 | 20 |
| Relationship Depth | 5 levels | 5 levels |

---

## Index Usage

### Always Indexed

- `Id`
- `Name`
- `OwnerId`
- `CreatedDate`
- `LastModifiedDate`
- `RecordTypeId`
- External ID fields
- Master-Detail fields

### Selective Query Rules

- Query is selective if WHERE returns < 10% of first 1M records
- Or uses an indexed field with < 1M matching records
- Non-selective queries on large tables fail

---

## CLI Commands

```bash
# Basic query
sf data query --query "SELECT Id, Name FROM Account LIMIT 10" --target-org my-org

# JSON output
sf data query --query "SELECT Id, Name FROM Account" --target-org my-org --json

# CSV output
sf data query --query "SELECT Id, Name FROM Account" --result-format csv --target-org my-org

# Bulk export (for large results, > 2,000 records)
sf data export bulk --query "SELECT Id, Name FROM Account" --target-org my-org --output-file accounts.csv

# Query plan (uses REST API explain endpoint)
sf api request rest "/query/?explain=SELECT+Id+FROM+Account+WHERE+Name='Test'" --target-org my-org --json
```
