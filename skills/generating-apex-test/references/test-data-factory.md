# TestDataFactory Patterns

## Overview

TestDataFactory is a centralized utility class for creating test records with sensible defaults. It ensures consistent test data across all test classes and reduces duplication.

## Base Template

```apex
@isTest
public class TestDataFactory {
    
    // ============ ACCOUNTS ============
    
    public static List<Account> createAccounts(Integer count, Boolean doInsert) {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            accounts.add(new Account(
                Name = 'Test Account ' + i,
                BillingStreet = '123 Test St',
                BillingCity = 'San Francisco',
                BillingState = 'CA',
                BillingPostalCode = '94105',
                BillingCountry = 'USA',
                Industry = 'Technology',
                Type = 'Customer'
            ));
        }
        if (doInsert) insert accounts;
        return accounts;
    }
    
    public static Account createAccount(Boolean doInsert) {
        return createAccounts(1, doInsert)[0];
    }
    
    // ============ CONTACTS ============
    
    public static List<Contact> createContacts(List<Account> accounts, Integer countPerAccount, Boolean doInsert) {
        List<Contact> contacts = new List<Contact>();
        Integer index = 0;
        for (Account acc : accounts) {
            for (Integer i = 0; i < countPerAccount; i++) {
                contacts.add(new Contact(
                    FirstName = 'Test',
                    LastName = 'Contact ' + index,
                    Email = 'test.contact' + index + '@example.com',
                    Phone = '555-000-' + String.valueOf(index).leftPad(4, '0'),
                    AccountId = acc.Id
                ));
                index++;
            }
        }
        if (doInsert) insert contacts;
        return contacts;
    }
    
    // ============ OPPORTUNITIES ============
    
    public static List<Opportunity> createOpportunities(List<Account> accounts, Integer countPerAccount, Boolean doInsert) {
        List<Opportunity> opps = new List<Opportunity>();
        Integer index = 0;
        for (Account acc : accounts) {
            for (Integer i = 0; i < countPerAccount; i++) {
                opps.add(new Opportunity(
                    Name = 'Test Opportunity ' + index,
                    AccountId = acc.Id,
                    StageName = 'Prospecting',
                    CloseDate = Date.today().addDays(30),
                    Amount = 10000 + (index * 1000)
                ));
                index++;
            }
        }
        if (doInsert) insert opps;
        return opps;
    }
    
    // ============ USERS ============
    
    public static User createUser(String profileName, Boolean doInsert) {
        Profile p = [SELECT Id FROM Profile WHERE Name = :profileName LIMIT 1];
        String uniqueKey = String.valueOf(DateTime.now().getTime());
        
        User u = new User(
            FirstName = 'Test',
            LastName = 'User ' + uniqueKey,
            Email = 'testuser' + uniqueKey + '@example.com',
            Username = 'testuser' + uniqueKey + '@example.com.test',
            Alias = 'tuser',
            TimeZoneSidKey = 'America/Los_Angeles',
            LocaleSidKey = 'en_US',
            EmailEncodingKey = 'UTF-8',
            LanguageLocaleKey = 'en_US',
            ProfileId = p.Id
        );
        if (doInsert) insert u;
        return u;
    }
    
    // ============ CUSTOM OBJECTS ============
    
    // Add methods for your custom objects following the same pattern:
    // public static List<MyObject__c> createMyObjects(Integer count, Boolean doInsert) { ... }
}
```

## Field Override Pattern

Allow callers to override default values:

```apex
public static Account createAccount(Map<String, Object> fieldOverrides, Boolean doInsert) {
    Account acc = new Account(
        Name = 'Test Account',
        Industry = 'Technology'
    );
    
    // Apply overrides
    for (String fieldName : fieldOverrides.keySet()) {
        acc.put(fieldName, fieldOverrides.get(fieldName));
    }
    
    if (doInsert) insert acc;
    return acc;
}

// Usage:
Account acc = TestDataFactory.createAccount(new Map<String, Object>{
    'Name' => 'Custom Name',
    'Industry' => 'Healthcare'
}, true);
```

## Handling Required Fields and Validation Rules

```apex
public static Account createAccountWithRequiredFields(Boolean doInsert) {
    Account acc = new Account(
        Name = 'Test Account',
        // Required custom fields
        External_Id__c = 'EXT-' + String.valueOf(DateTime.now().getTime()),
        // Fields required by validation rules
        Phone = '555-123-4567',
        Website = 'https://example.com'
    );
    if (doInsert) insert acc;
    return acc;
}
```

## Record Type Support

```apex
public static Account createAccountByRecordType(String recordTypeName, Boolean doInsert) {
    Id recordTypeId = Schema.SObjectType.Account
        .getRecordTypeInfosByDeveloperName()
        .get(recordTypeName)
        .getRecordTypeId();
    
    Account acc = new Account(
        Name = 'Test Account',
        RecordTypeId = recordTypeId
    );
    if (doInsert) insert acc;
    return acc;
}
```

## Best Practices

1. **Always include doInsert parameter** - Allows flexibility for tests that need to modify records before insert
2. **Use unique identifiers** - Include index or timestamp in Name/Email fields to avoid duplicates
3. **Set all required fields** - Include all fields required by validation rules
4. **Return the created records** - Enables chaining and further manipulation
5. **Create bulk methods first** - Single record methods should call bulk methods with count=1
