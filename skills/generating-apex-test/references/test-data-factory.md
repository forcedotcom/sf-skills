# TestDataFactory Patterns

## Overview

TestDataFactory is a centralized utility class for creating test records with sensible defaults. It ensures consistent test data across all test classes and reduces duplication.

See [assets/test-data-factory.cls](../assets/test-data-factory.cls) for the full template.

## API Convention

Every object has two methods:

| Method | Returns | DML |
|--------|---------|-----|
| `createObjects(count)` | `List<SObject>` (not inserted) | None |
| `createAndInsertObjects(count)` | `List<SObject>` (inserted) | Yes |

This gives callers flexibility to modify records before insert when needed.

```apex
// Create without insert (modify fields first)
List<Account> accounts = TestDataFactory.createAccounts(251);
accounts[0].Industry = 'Healthcare';
insert accounts;

// Create and insert in one call
List<Account> accounts = TestDataFactory.createAndInsertAccounts(251);
```

## Field Override Pattern

Allow callers to override default values:

```apex
public static Account createAccount(Map<String, Object> fieldOverrides) {
    Account acc = new Account(
        Name = 'Test Account',
        Industry = 'Technology'
    );

    for (String fieldName : fieldOverrides.keySet()) {
        acc.put(fieldName, fieldOverrides.get(fieldName));
    }

    return acc;
}

// Usage:
Account acc = TestDataFactory.createAccount(new Map<String, Object>{
    'Name' => 'Custom Name',
    'Industry' => 'Healthcare'
});
insert acc;
```

## Handling Required Fields and Validation Rules

```apex
public static Account createAccountWithRequiredFields() {
    return new Account(
        Name = 'Test Account',
        External_Id__c = 'EXT-' + String.valueOf(DateTime.now().getTime()),
        Phone = '555-123-4567',
        Website = 'https://example.com'
    );
}
```

## Record Type Support

```apex
public static Account createAccountByRecordType(String recordTypeName) {
    Id recordTypeId = Schema.SObjectType.Account
        .getRecordTypeInfosByDeveloperName()
        .get(recordTypeName)
        .getRecordTypeId();

    return new Account(
        Name = 'Test Account',
        RecordTypeId = recordTypeId
    );
}
```

## Avoiding Duplicate Rule Violations

Active Duplicate Rules in the org can reject bulk inserts with `DUPLICATES_DETECTED` when test records match each other or existing org data on fields like Name, Email, Phone, or Company. This is the most common cause of `system.DmlException: Insert failed. First exception on row 200; first error: DUPLICATES_DETECTED`.

### Strategy 1 — Generate Unique Field Values (Preferred)

Ensure every field that participates in a matching rule has a unique value per record. Append the loop index to **all** matchable fields, not just Name:

```apex
public static List<Lead> createLeads(Integer count) {
    List<Lead> leads = new List<Lead>();
    for (Integer i = 0; i < count; i++) {
        leads.add(new Lead(
            FirstName = 'Test' + i,
            LastName = 'Lead' + i,
            Company = 'TestCompany' + i,
            Email = 'testlead' + i + '@example.com',
            Phone = '555-000-' + String.valueOf(i).leftPad(4, '0')
        ));
    }
    return leads;
}

public static List<Contact> createContacts(Integer count, Id accountId) {
    List<Contact> contacts = new List<Contact>();
    for (Integer i = 0; i < count; i++) {
        contacts.add(new Contact(
            FirstName = 'Test' + i,
            LastName = 'Contact' + i,
            AccountId = accountId,
            Email = 'testcontact' + i + '@example.com',
            Phone = '555-100-' + String.valueOf(i).leftPad(4, '0')
        ));
    }
    return contacts;
}
```

### Strategy 2 — Bypass Duplicate Rules with DuplicateRuleHeader

When unique values alone are not sufficient (e.g., matching rules use fuzzy logic, or the test deliberately creates similar records), bypass duplicate detection at insert time:

```apex
public static List<SObject> insertWithDuplicateRuleBypass(List<SObject> records) {
    Database.DMLOptions dmlOptions = new Database.DMLOptions();
    dmlOptions.DuplicateRuleHeader.allowSave = true;
    List<Database.SaveResult> results = Database.insert(records, dmlOptions);
    for (Database.SaveResult sr : results) {
        if (!sr.isSuccess()) {
            System.debug(LoggingLevel.ERROR, 'Insert failed: ' + sr.getErrors());
        }
    }
    return records;
}
```

Usage in `@TestSetup`:

```apex
@TestSetup
static void setupTestData() {
    List<Lead> leads = TestDataFactory.createLeads(251);
    TestDataFactory.insertWithDuplicateRuleBypass(leads);
}
```

### When to Use Each Strategy

| Strategy | Use when |
|----------|----------|
| Unique field values | Default approach — catches most standard matching rules |
| DuplicateRuleHeader bypass | Fuzzy matching rules, or test specifically validates duplicate-adjacent data |
| Both combined | Maximum safety for orgs with aggressive duplicate rules |

## Best Practices

1. **Separate create from insert** -- use `create` + `createAndInsert` method pairs for flexibility
2. **Use unique identifiers** -- include index or timestamp in Name/Email fields to avoid duplicates across all matchable fields (Name, Email, Phone, Company, etc.)
3. **Set all required fields** -- include all fields required by validation rules
4. **Return the created records** -- enables chaining and further manipulation
5. **Create bulk methods first** -- single record methods should call bulk methods with count=1
6. **Anticipate Duplicate Rules** -- always assume the target org may have active Duplicate Rules; generate unique values for every field that could participate in matching
