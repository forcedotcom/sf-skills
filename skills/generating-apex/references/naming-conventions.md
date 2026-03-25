# Apex Naming Conventions

For the class naming table (Service, Selector, Domain, Batch, Queueable, Schedulable, DTO, Trigger Action, etc.), see the **Naming Conventions** section in [SKILL.md](../SKILL.md).

This file covers **method, variable, collection, and constant** naming in detail.

---

## Methods

### Format: camelCase, Start with Verb

| Purpose | Convention | Example |
|---------|------------|---------|
| Get data | `get[Noun]` | `getAccounts()` |
| Set data | `set[Noun]` | `setAccountStatus()` |
| Check condition | `is[Adjective]` / `has[Noun]` | `isActive()`, `hasPermission()` |
| Action | `[verb][Noun]` | `processOrders()`, `validateData()` |
| Calculate | `calculate[Noun]` | `calculateTotal()` |
| Create | `create[Noun]` | `createAccount()` |
| Update | `update[Noun]` | `updateStatus()` |
| Delete | `delete[Noun]` | `deleteRecords()` |

```apex
// Good
public Account getAccount(Id accountId) { }
public void processRecords(List<Record__c> records) { }
public Boolean isEligible(Account acc) { }
public Decimal calculateTotalRevenue(List<Opportunity> opps) { }

// Boolean methods read as assertions
public Boolean hasActiveSubscription() { }
public Boolean canModifyRecord() { }
```

---

## Variables

### Format: camelCase, Descriptive

| Type | Convention | Example |
|------|------------|---------|
| Local variable | descriptive noun | `account`, `totalAmount` |
| Loop iterator | single letter (temp) | `i`, `j`, `k` |
| Boolean | `is[Adjective]` / `has[Noun]` | `isValid`, `hasError` |
| Collection | plural noun | `accounts`, `contactList` |
| Map | `[value]By[key]` | `accountsById`, `contactsByEmail` |
| Set | `[noun]Set` or `[noun]Ids` | `accountIds`, `processedIdSet` |

### Anti-Patterns to Avoid

```apex
// BAD: Abbreviations
String acct;      // What is this?
List<Task> tks;   // Unclear
SObject rec;      // Too generic

// GOOD: Descriptive names
String accountName;
List<Task> openTasks;
Account parentAccount;
```

### Collection Naming

```apex
// Lists - plural noun
List<Account> accounts;
List<Contact> relatedContacts;

// Sets - noun + Ids or noun + Set
Set<Id> accountIds;
Set<String> processedEmailSet;

// Maps - value + By + key description
Map<Id, Account> accountsById;
Map<String, List<Contact>> contactsByEmail;
Map<Id, Map<String, Decimal>> metricsByAccountByType;
```

---

## Constants

### Format: UPPER_SNAKE_CASE

```apex
public class Constants {
    public static final String STATUS_ACTIVE = 'Active';
    public static final String STATUS_INACTIVE = 'Inactive';
    public static final Integer MAX_RETRY_COUNT = 3;
    public static final Decimal TAX_RATE = 0.08;
}
```

---

## Custom Objects & Fields

### Format: Title_Case_With_Underscores

```apex
// Objects
Account_Score__c
Order_Line_Item__c

// Fields
Account_Status__c
Total_Revenue__c
Is_Primary__c

// Reference in code (use API names)
account.Account_Status__c = 'Active';
```


