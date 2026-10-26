# TestDataFactory Patterns

For the base class template, see [assets/test-data-factory-template.cls](../assets/test-data-factory-template.cls).

## Design Rules

1. **Always accept a `doInsert` flag** — lets callers modify records before insert
2. **Append loop index to all fields that participate in matching rules** — prevents `DUPLICATES_DETECTED` errors from active Duplicate Rules
3. **Single-record methods delegate to bulk** — e.g., `createAccount(doInsert)` calls `createAccounts(1, doInsert)[0]`
4. **Return created records** — enables chaining and further manipulation
5. **Set all required fields** — include fields enforced by validation rules, not just schema-required fields

## Field Override Pattern

Allow callers to override default values without creating new factory methods:

```apex
public static Account createAccount(Map<String, Object> fieldOverrides, Boolean doInsert) {
    Account acc = new Account(
        Name = 'Test Account',
        Industry = 'Technology'
    );
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

## Handling Duplicate Rules

When unique field values alone are not sufficient, use `Database.insert()` with a `DuplicateRuleHeader`:

```apex
public static List<Account> createAccountsAllowDuplicates(Integer count, Boolean doInsert) {
    List<Account> accounts = new List<Account>();
    for (Integer i = 0; i < count; i++) {
        accounts.add(new Account(
            Name = 'Test Account ' + i,
            Phone = '555-000-' + String.valueOf(i).leftPad(4, '0')
        ));
    }
    if (doInsert) {
        Database.DMLOptions dml = new Database.DMLOptions();
        dml.DuplicateRuleHeader.allowSave = true;
        Database.insert(accounts, dml);
    }
    return accounts;
}
```

## Setup Objects (Users and Roles)

`UserRole`, `User`, and `PermissionSetAssignment` are setup objects. Inserting one and then inserting an Account or a custom object in the same test method fails with `MIXED_DML_OPERATION`, at any API version. The sharing and portal-owner tests that seed a role hit this on the first run.

Insert the role and the user first, then run the record DML inside `System.runAs(thatUser)`. Give each test method its own `UserRole.DeveloperName`; two methods in one class that insert the same role collide.

```apex
@IsTest
static void portalOwner_sharesAccountWithRole() {
    UserRole role = new UserRole(Name = 'Portal Owner', DeveloperName = 'PortalOwner_sharesAccount');
    insert role;
    User owner = TestDataFactory.createUser(new Map<String, Object>{ 'UserRoleId' => role.Id }, true);

    System.runAs(owner) {
        Account acc = TestDataFactory.createAccount(true);   // record DML runs here, not alongside the role insert
        Test.startTest();
        // ... code under test
        Test.stopTest();
    }
}
```

See [Mixed DML Operations in Test Methods](https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_dml_non_mix_sobjects_test_methods.htm).
