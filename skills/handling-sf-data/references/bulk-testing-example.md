<!-- Parent: handling-sf-data/SKILL.md -->
# Bulk Testing Example

Testing Apex triggers and flows with bulk data operations.

## Scenario

Test an Account trigger that:
- Fires on insert with 200+ records
- Updates a custom field based on Industry
- Creates a related Task for high-value accounts

## Why 201 Records?

Salesforce processes triggers in batches of 200. Testing with 201+ records ensures:
- Trigger handles batch boundaries
- No governor limit violations in loops
- SOQL/DML operations are bulkified

## Method 1: Anonymous Apex Factory

### Create Test Data
```apex
// Create 251 Accounts to test trigger bulkification
List<Account> accounts = new List<Account>();

List<String> industries = new List<String>{
    'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail'
};

for (Integer i = 0; i < 251; i++) {
    accounts.add(new Account(
        Name = 'BulkTest Account ' + i,
        Industry = industries[Math.mod(i, industries.size())],
        AnnualRevenue = Math.round(Math.random() * 10000000)
    ));
}

// Single DML - triggers fire in batches of 200
insert accounts;

System.debug('Created ' + accounts.size() + ' accounts');
System.debug('SOQL Queries Used: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
```

Save as `bulk-test-accounts.apex` and run:
```bash
sf apex run --file bulk-test-accounts.apex --target-org dev
```

## Method 2: CSV Bulk Import

### Create CSV File
```csv
Name,Industry,AnnualRevenue
BulkTest Account 1,Technology,1000000
BulkTest Account 2,Healthcare,2000000
BulkTest Account 3,Finance,5000000
... (251 rows)
```

### Import via sf CLI
```bash
sf data import bulk \
  --file accounts-bulk.csv \
  --sobject Account \
  --target-org dev \
  --wait 30
```

## Method 3: JSON Tree Import

For hierarchical test data with relationships:

```json
{
  "records": [
    {
      "attributes": {"type": "Account", "referenceId": "AccountRef1"},
      "Name": "BulkTest Parent 1",
      "Industry": "Technology",
      "Contacts": {
        "records": [
          {
            "attributes": {"type": "Contact"},
            "FirstName": "Test",
            "LastName": "Contact 1"
          }
        ]
      }
    }
  ]
}
```

```bash
sf data import tree \
  --files bulk-hierarchy.json \
  --target-org dev
```

## Verify Trigger Executed Correctly

### Check Trigger Results
```bash
sf data query \
  --query "SELECT Id, Name, Industry, Custom_Field__c FROM Account WHERE Name LIKE 'BulkTest%' LIMIT 10" \
  --target-org dev \
  --json
```

### Check Related Tasks Created
```bash
sf data query \
  --query "SELECT Id, Subject, WhatId, What.Name FROM Task WHERE What.Name LIKE 'BulkTest%'" \
  --target-org dev
```

### Count Records
```bash
sf data query \
  --query "SELECT COUNT(Id) total FROM Account WHERE Name LIKE 'BulkTest%'" \
  --target-org dev
```

## Test Bulk Update

```apex
// Update all test records - triggers fire again
List<Account> accounts = [
    SELECT Id, Name, Industry
    FROM Account
    WHERE Name LIKE 'BulkTest%'
];

for (Account acc : accounts) {
    acc.Description = 'Bulk updated on ' + DateTime.now();
}

update accounts;

System.debug('Updated ' + accounts.size() + ' accounts');
```

## Test Bulk Delete

```apex
// Delete in reverse order (children first)
List<Task> tasks = [SELECT Id FROM Task WHERE What.Name LIKE 'BulkTest%'];
delete tasks;

List<Contact> contacts = [SELECT Id FROM Contact WHERE Account.Name LIKE 'BulkTest%'];
delete contacts;

List<Account> accounts = [SELECT Id FROM Account WHERE Name LIKE 'BulkTest%'];
delete accounts;

System.debug('Cleanup complete');
```

## Governor Limits Monitoring

```apex
// Add to your test script to monitor limits
System.debug('=== GOVERNOR LIMITS ===');
System.debug('SOQL: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
System.debug('DML Rows: ' + Limits.getDmlRows() + '/' + Limits.getLimitDmlRows());
System.debug('CPU Time: ' + Limits.getCpuTime() + 'ms/' + Limits.getLimitCpuTime() + 'ms');
System.debug('Heap: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
```

## Validation Score

```
Score: 128/130 ⭐⭐⭐⭐⭐ Excellent
├─ Query Efficiency: 25/25 (bulk queries)
├─ Bulk Safety: 25/25 (251 records, limits monitored)
├─ Data Integrity: 20/20 (valid field values)
├─ Security & FLS: 20/20 (no sensitive data)
├─ Test Patterns: 15/15 (201+ records, variations)
├─ Cleanup & Isolation: 13/15 (cleanup script provided)
└─ Documentation: 10/10 (fully documented)
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `SOQL 101` | Query in loop | Use Map or Set for bulk queries |
| `DML 151` | DML in loop | Collect records, single DML |
| `CPU timeout` | Complex logic | Optimize loops, async processing |
| `Too many records` | >10,000 DML rows | Use Bulk API or Batch Apex |
