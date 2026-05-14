<!-- Parent: handling-sf-data/SKILL.md -->
# SOQL Relationship Query Guide

Complete reference for querying related records in Salesforce.

## Relationship Types

### 1. Parent-to-Child (Subquery)
Returns parent records with nested child records.

```sql
SELECT Id, Name,
    (SELECT Id, FirstName, LastName FROM Contacts)
FROM Account
WHERE Industry = 'Technology'
```

**Key Points:**
- Maximum 20 subqueries per query
- Use relationship name (plural): `Contacts`, `Opportunities`, `Cases`
- For custom objects: `Child_Object__r`

### 2. Child-to-Parent (Dot Notation)
Access parent fields from child record.

```sql
SELECT Id, Name,
    Account.Name,
    Account.Industry,
    Account.Owner.Name
FROM Contact
WHERE Account.Type = 'Customer'
```

**Key Points:**
- Maximum 5 levels deep
- Standard: `Account.Name`
- Custom: `Parent__r.Name`

### 3. Polymorphic (TYPEOF)
Handle fields that reference multiple object types.

```sql
SELECT Id, Subject,
    TYPEOF Who
        WHEN Contact THEN FirstName, LastName
        WHEN Lead THEN Company
    END,
    TYPEOF What
        WHEN Account THEN Name, Industry
        WHEN Opportunity THEN Amount
    END
FROM Task
```

**Common Polymorphic Fields:**
- `WhoId` → Contact, Lead
- `WhatId` → Account, Opportunity, Case, etc.
- `OwnerId` → User, Queue

## Relationship Names

| Child Object | Parent Field | Relationship Name |
|--------------|--------------|-------------------|
| Contact | AccountId | Account.Contacts |
| Opportunity | AccountId | Account.Opportunities |
| Case | AccountId | Account.Cases |
| Task | WhatId | Account.Tasks |
| Contact | ReportsToId | Contact.ReportsTo |

## Limits

| Limit | Value |
|-------|-------|
| Child-to-Parent depth | 5 levels |
| Subqueries per query | 20 |
| Rows per subquery | 200 (without LIMIT) |

## Best Practices

1. **Use indexed fields** in WHERE clauses
2. **Add LIMIT** to subqueries
3. **Filter early** - push conditions into subqueries
4. **Avoid N+1** - use relationship queries instead of loops
