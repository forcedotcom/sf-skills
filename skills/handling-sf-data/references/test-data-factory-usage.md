<!-- Parent: handling-sf-data/SKILL.md -->
# Test Data Factory Usage

How to use and customize the test data factory templates.

## Basic Factory Pattern

### Account Factory
```apex
public class TestDataFactory_Account {

    // Basic creation - inserted
    public static List<Account> create(Integer count) {
        return create(count, true);
    }

    // Control insertion
    public static List<Account> create(Integer count, Boolean doInsert) {
        List<Account> records = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            records.add(new Account(
                Name = 'Test Account ' + i,
                Industry = 'Technology'
            ));
        }
        if (doInsert) {
            insert records;
        }
        return records;
    }
}
```

### Usage Examples

```apex
// Create 10 accounts (inserted)
List<Account> accounts = TestDataFactory_Account.create(10);

// Create 10 accounts (not inserted - for customization)
List<Account> accounts = TestDataFactory_Account.create(10, false);
accounts[0].AnnualRevenue = 1000000;
accounts[1].Rating = 'Hot';
insert accounts;
```

## Factory with Variations

### Industry Variations
```apex
public static List<Account> createWithVariedIndustries(Integer count) {
    List<Account> records = new List<Account>();
    List<String> industries = new List<String>{
        'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail'
    };

    for (Integer i = 0; i < count; i++) {
        records.add(new Account(
            Name = 'Test Account ' + i,
            Industry = industries[Math.mod(i, industries.size())]
        ));
    }
    insert records;
    return records;
}
```

### Revenue Tiers
```apex
public static List<Account> createWithRevenueTiers(Integer count) {
    List<Account> records = new List<Account>();
    List<Decimal> tiers = new List<Decimal>{
        100000, 500000, 1000000, 5000000, 10000000
    };

    for (Integer i = 0; i < count; i++) {
        records.add(new Account(
            Name = 'Test Account ' + i,
            AnnualRevenue = tiers[Math.mod(i, tiers.size())]
        ));
    }
    insert records;
    return records;
}
```

## Factory with Relationships

### Contact Factory with Account
```apex
public class TestDataFactory_Contact {

    // Create contacts for existing accounts
    public static List<Contact> createForAccounts(Set<Id> accountIds, Integer perAccount) {
        List<Contact> contacts = new List<Contact>();
        Integer i = 0;

        for (Id accId : accountIds) {
            for (Integer j = 0; j < perAccount; j++) {
                contacts.add(new Contact(
                    FirstName = 'Test',
                    LastName = 'Contact ' + i,
                    AccountId = accId,
                    Email = 'test' + i + '@example.com'
                ));
                i++;
            }
        }
        insert contacts;
        return contacts;
    }
}
```

### Usage
```apex
// Create 10 accounts with 3 contacts each
List<Account> accounts = TestDataFactory_Account.create(10);
Set<Id> accountIds = new Map<Id, Account>(accounts).keySet();
List<Contact> contacts = TestDataFactory_Contact.createForAccounts(accountIds, 3);
// Total: 10 accounts + 30 contacts
```

## Hierarchy Factory

### Complete Hierarchy in One Call
```apex
public class TestDataFactory_Hierarchy {

    public class HierarchyResult {
        public List<Account> accounts;
        public List<Contact> contacts;
        public List<Opportunity> opportunities;
    }

    public static HierarchyResult create(
        Integer accountCount,
        Integer contactsPerAccount,
        Integer oppsPerAccount
    ) {
        HierarchyResult result = new HierarchyResult();

        // Create accounts
        result.accounts = TestDataFactory_Account.create(accountCount);
        Set<Id> accountIds = new Map<Id, Account>(result.accounts).keySet();

        // Create contacts
        result.contacts = TestDataFactory_Contact.createForAccounts(
            accountIds, contactsPerAccount
        );

        // Create opportunities
        result.opportunities = TestDataFactory_Opportunity.createForAccounts(
            accountIds, oppsPerAccount
        );

        return result;
    }
}
```

### Usage
```apex
// Create complete test hierarchy
HierarchyResult data = TestDataFactory_Hierarchy.create(
    10,  // accounts
    3,   // contacts per account
    2    // opportunities per account
);
// Total: 10 accounts + 30 contacts + 20 opportunities

System.debug('Accounts: ' + data.accounts.size());
System.debug('Contacts: ' + data.contacts.size());
System.debug('Opportunities: ' + data.opportunities.size());
```

## Edge Case Factories

### Boundary Values
```apex
public static Account createWithMinValues() {
    return new Account(
        Name = 'A'  // Minimum name length
    );
}

public static Account createWithMaxValues() {
    return new Account(
        Name = 'X'.repeat(255),  // Maximum name length
        Description = 'Y'.repeat(32000)  // Maximum description
    );
}
```

### Special Characters
```apex
public static Account createWithSpecialCharacters() {
    return new Account(
        Name = 'Test & "Special" <Characters> \'Quotes\''
    );
}
```

### Null/Empty Values
```apex
public static List<Account> createWithNullableFields(Integer count) {
    List<Account> records = new List<Account>();
    for (Integer i = 0; i < count; i++) {
        Account acc = new Account(Name = 'Test ' + i);
        // Leave optional fields null
        // acc.Industry = null;
        // acc.AnnualRevenue = null;
        records.add(acc);
    }
    insert records;
    return records;
}
```

## Using Factories for Testing

### Trigger Test Example
```apex
@isTest
public class AccountTriggerTest {

    @isTest
    static void testBulkInsert() {
        // Setup - 201 records to test batch boundaries
        Test.startTest();
        List<Account> accounts = TestDataFactory_Account.create(201);
        Test.stopTest();

        // Verify trigger logic executed
        List<Account> results = [
            SELECT Id, Custom_Field__c
            FROM Account
            WHERE Id IN :accounts
        ];

        for (Account acc : results) {
            System.assertNotEquals(null, acc.Custom_Field__c,
                'Trigger should have set Custom_Field__c');
        }
    }

    @isTest
    static void testWithRelatedRecords() {
        // Setup hierarchy
        HierarchyResult data = TestDataFactory_Hierarchy.create(5, 2, 1);

        Test.startTest();
        // Test logic that involves relationships
        MyClass.processAccountsWithContacts(data.accounts);
        Test.stopTest();

        // Verify results
    }
}
```

### Flow Test Example
```apex
@isTest
static void testRecordTriggeredFlow() {
    // Create data that matches flow entry criteria
    List<Account> accounts = TestDataFactory_Account.create(10, false);
    for (Account acc : accounts) {
        acc.Industry = 'Technology';  // Matches flow filter
        acc.AnnualRevenue = 1000000;  // Triggers flow action
    }

    Test.startTest();
    insert accounts;  // Flow fires on insert
    Test.stopTest();

    // Verify flow results
    List<Task> tasks = [SELECT Id FROM Task WHERE WhatId IN :accounts];
    System.assertEquals(10, tasks.size(), 'Flow should create task for each account');
}
```

## Best Practices

1. **Always return inserted records** - Caller may need IDs
2. **Provide doInsert parameter** - Allow customization before insert
3. **Use bulk patterns** - Single DML for multiple records
4. **Handle required fields** - Prevent validation errors
5. **Use unique values** - Avoid duplicate rule violations
6. **Track IDs for cleanup** - Enable proper test isolation
