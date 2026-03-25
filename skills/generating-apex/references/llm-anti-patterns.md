# LLM-Specific Anti-Patterns in Apex

This guide documents systematic errors that LLMs (including Claude) commonly make when generating Salesforce Apex code. These patterns are critical to validate in generated code.

> **Source**: [LLM Mistakes in Apex & LWC - Salesforce Diaries](https://salesforcediaries.com/2026/01/16/llm-mistakes-in-apex-lwc-salesforce-code-generation-rules/)

---

## Table of Contents

1. [Non-Existent Methods](#1-non-existent-methods)
2. [Java Types Instead of Apex Types](#2-java-types-instead-of-apex-types)
3. [Map Access Without Null Safety](#3-map-access-without-null-safety)
4. [Missing SOQL Fields](#4-missing-soql-fields)
5. [Recursive Trigger Loops](#5-recursive-trigger-loops)
6. [Invalid InvocableVariable Types](#6-invalid-invocablevariable-types)
7. [Missing @JsonAccess Annotations](#7-missing-jsonaccess-annotations)
8. [Null Pointer from Missing Checks](#8-null-pointer-from-missing-checks)
9. [Incorrect DateTime Methods](#9-incorrect-datetime-methods)
10. [Collection Initialization Patterns](#10-collection-initialization-patterns)

---

<a id="1-non-existent-methods"></a>

## 1. Non-Existent Methods

LLMs often hallucinate methods that don't exist in Apex, borrowing syntax from Java or other languages.

### Common Hallucinated Methods

| Hallucinated Method | What LLM Expected | Correct Apex Alternative |
|---------------------|-------------------|--------------------------|
| `Datetime.addMilliseconds()` | Add milliseconds | `Datetime.addSeconds(ms/1000)` |
| `String.isEmpty(str)` | Static empty check | `String.isBlank(str)` |
| `List.stream()` | Java streams | Use `for` loops |
| `Map.getOrDefault()` | Default value | `map.get(key) ?? defaultValue` |
| `String.format()` | String formatting | `String.format()` exists but with different syntax |
| `Object.equals()` | Equality check | Use `==` or custom method |
| `List.sort(comparator)` | Custom sorting | Implement `Comparable` interface |
| `String.join(list)` | Join with delimiter | `String.join(list, delimiter)` |

### ❌ BAD: Hallucinated Datetime Method

```apex
// LLM generates this - DOES NOT EXIST
Datetime future = Datetime.now().addMilliseconds(500);
```

### ✅ GOOD: Correct Apex Pattern

```apex
// Apex has no millisecond precision - use seconds
Datetime future = Datetime.now().addSeconds(1);

// For sub-second timing, use System.currentTimeMillis()
Long startMs = System.currentTimeMillis();
// ... operation ...
Long elapsedMs = System.currentTimeMillis() - startMs;
```

### ❌ BAD: Java Stream Syntax

```apex
// LLM generates this - Java streams don't exist in Apex
List<String> names = accounts.stream()
    .map(a -> a.Name)
    .collect(Collectors.toList());
```

### ✅ GOOD: Apex Loop Pattern

```apex
// Use traditional loops in Apex
List<String> names = new List<String>();
for (Account a : accounts) {
    names.add(a.Name);
}
```

---

## 2. Java Types Instead of Apex Types

LLMs trained on Java code often use Java collection types that don't exist in Apex.

### Java Types to Avoid

| Java Type | Apex Equivalent |
|-----------|-----------------|
| `ArrayList<T>` | `List<T>` |
| `HashMap<K,V>` | `Map<K,V>` |
| `HashSet<T>` | `Set<T>` |
| `StringBuffer` | `String` (immutable) or `List<String>` + `String.join()` |
| `StringBuilder` | `String` (immutable) or `List<String>` + `String.join()` |
| `LinkedList<T>` | `List<T>` |
| `TreeMap<K,V>` | `Map<K,V>` (no ordering guarantee) |
| `Vector<T>` | `List<T>` |
| `Hashtable<K,V>` | `Map<K,V>` |

### ❌ BAD: Java Collection Types

```apex
// LLM generates these - COMPILE ERROR
ArrayList<Account> accounts = new ArrayList<Account>();
HashMap<Id, Contact> contactMap = new HashMap<Id, Contact>();
StringBuilder sb = new StringBuilder();
```

### ✅ GOOD: Apex Native Types

```apex
// Apex uses these types
List<Account> accounts = new List<Account>();
Map<Id, Contact> contactMap = new Map<Id, Contact>();

// For string concatenation
String result = '';
for (String s : parts) {
    result += s;  // OK for small strings
}

// For large string building
List<String> parts = new List<String>();
parts.add('Part 1');
parts.add('Part 2');
String result = String.join(parts, '');
```

### Detection Rule

```
REGEX: \b(ArrayList|HashMap|HashSet|StringBuffer|StringBuilder|LinkedList|TreeMap|Vector|Hashtable)\s*<
SEVERITY: CRITICAL
MESSAGE: Java type "{match}" does not exist in Apex. Use Apex native collections.
```

---

## 3. Map Access Without Null Safety

LLMs often use `Map.get()` without checking if the key exists, causing null pointer exceptions.

### ❌ BAD: Unsafe Map Access

```apex
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

for (Contact c : contacts) {
    // DANGER: If AccountId not in map, .Name throws NPE
    String accountName = accountMap.get(c.AccountId).Name;
}
```

### ✅ GOOD: Safe Map Access (Option 1 - containsKey)

```apex
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

for (Contact c : contacts) {
    if (accountMap.containsKey(c.AccountId)) {
        String accountName = accountMap.get(c.AccountId).Name;
    }
}
```

### ✅ GOOD: Safe Map Access (Option 2 - Null Check)

```apex
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

for (Contact c : contacts) {
    Account acc = accountMap.get(c.AccountId);
    if (acc != null) {
        String accountName = acc.Name;
    }
}
```

### ✅ GOOD: Safe Map Access (Option 3 - Safe Navigation)

```apex
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

for (Contact c : contacts) {
    // Safe navigation operator (?.) - returns null if key not found
    String accountName = accountMap.get(c.AccountId)?.Name;
    if (accountName != null) {
        // Process
    }
}
```

### ✅ GOOD: Safe Map Access (Option 4 - Null Coalescing)

```apex
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

for (Contact c : contacts) {
    // Null coalescing operator (??) for default values
    String accountName = accountMap.get(c.AccountId)?.Name ?? 'Unknown';
}
```

---

## 4. Missing SOQL Fields

LLMs often query fields but then access different fields not in the SELECT clause.

### ❌ BAD: Accessing Unqueried Fields

```apex
// Only querying Id and Name
List<Account> accounts = [SELECT Id, Name FROM Account];

for (Account acc : accounts) {
    // RUNTIME ERROR: Industry was not queried!
    if (acc.Industry == 'Technology') {
        acc.Description = 'Tech company';  // Description also not queried!
    }
}
```

### ✅ GOOD: Query All Accessed Fields

```apex
// Query all fields that will be accessed
List<Account> accounts = [SELECT Id, Name, Industry, Description FROM Account];

for (Account acc : accounts) {
    if (acc.Industry == 'Technology') {
        acc.Description = 'Tech company';
    }
}
```

### ❌ BAD: Missing Relationship Fields

```apex
// Missing Account.Name in query
List<Contact> contacts = [SELECT Id, Name, AccountId FROM Contact];

for (Contact c : contacts) {
    // RUNTIME ERROR: Account.Name not queried
    System.debug('Account: ' + c.Account.Name);
}
```

### ✅ GOOD: Include Relationship Fields

```apex
// Include relationship fields using dot notation
List<Contact> contacts = [SELECT Id, Name, AccountId, Account.Name FROM Contact];

for (Contact c : contacts) {
    System.debug('Account: ' + c.Account.Name);  // Works!
}
```

### Validation Checklist

Before running code, verify:
1. All fields accessed in `if` statements are queried
2. All fields accessed in assignments are queried
3. All relationship fields (e.g., `Account.Name`) are in SELECT
4. Parent relationship uses `.` notation in query (e.g., `Contact.Account.Name`)

---

## 5. Recursive Trigger Loops

LLMs often forget to add recursion prevention in triggers, causing infinite loops.

### ❌ BAD: No Recursion Prevention

```apex
// Trigger that updates related records
trigger AccountTrigger on Account (after update) {
    List<Contact> contactsToUpdate = new List<Contact>();

    for (Account acc : Trigger.new) {
        // This update might trigger another trigger, which might update Account...
        for (Contact c : [SELECT Id FROM Contact WHERE AccountId = :acc.Id]) {
            c.MailingCity = acc.BillingCity;
            contactsToUpdate.add(c);
        }
    }

    update contactsToUpdate;  // Could cause recursion!
}
```

### ✅ GOOD: Static Flag Pattern

```apex
// TriggerHelper.cls
public class TriggerHelper {
    private static Boolean isFirstRun = true;

    public static Boolean isFirstRun() {
        if (isFirstRun) {
            isFirstRun = false;
            return true;
        }
        return false;
    }

    public static void reset() {
        isFirstRun = true;
    }
}

// AccountTrigger.trigger
trigger AccountTrigger on Account (after update) {
    if (!TriggerHelper.isFirstRun()) {
        return;  // Skip on recursive calls
    }

    // ... trigger logic ...
}
```

### ✅ BETTER: Set-Based Recursion Control

```apex
// TriggerRecursionHandler.cls
public class TriggerRecursionHandler {
    private static Set<Id> processedIds = new Set<Id>();

    public static Boolean hasProcessed(Id recordId) {
        return processedIds.contains(recordId);
    }

    public static void markProcessed(Id recordId) {
        processedIds.add(recordId);
    }

    public static void markProcessed(Set<Id> recordIds) {
        processedIds.addAll(recordIds);
    }
}

// In trigger handler
for (Account acc : Trigger.new) {
    if (TriggerRecursionHandler.hasProcessed(acc.Id)) {
        continue;
    }
    TriggerRecursionHandler.markProcessed(acc.Id);
    // Process record...
}
```

### ✅ BEST: Trigger Actions Framework

```apex
// Use TAF for built-in recursion control via metadata
// See: references/trigger-actions-framework.md
```

---

## 6. Invalid InvocableVariable Types

LLMs often use unsupported types in `@InvocableVariable` annotations for Flow/Process Builder integration.

### Supported InvocableVariable Types

| Category | Supported Types |
|----------|----------------|
| **Primitives** | `Boolean`, `Date`, `DateTime`, `Decimal`, `Double`, `Id`, `Integer`, `Long`, `String`, `Time` |
| **Collections** | `List<T>` where T is a supported type |
| **sObjects** | Any standard or custom sObject |
| **Apex-Defined** | Classes with `@InvocableVariable` on fields |

### Unsupported Types

| Type | Why Unsupported | Alternative |
|------|----------------|-------------|
| `Map<K,V>` | Not serializable to Flow | Use List of wrapper class |
| `Set<T>` | Not serializable to Flow | Use `List<T>` |
| `Object` | Too generic | Use specific type |
| `Blob` | Not serializable | Use `String` (Base64) |
| Custom classes without `@InvocableVariable` | Not marked for Flow | Add annotations |

### ❌ BAD: Unsupported InvocableVariable Types

```apex
public class FlowInput {
    @InvocableVariable
    public Map<String, String> options;  // NOT SUPPORTED!

    @InvocableVariable
    public Set<Id> recordIds;  // NOT SUPPORTED!

    @InvocableVariable
    public Blob fileContent;  // NOT SUPPORTED!
}
```

### ✅ GOOD: Supported Types with Wrapper Pattern

```apex
public class FlowInput {
    @InvocableVariable(label='Record IDs' description='Comma-separated IDs')
    public List<Id> recordIds;  // List is supported

    @InvocableVariable(label='Options JSON' description='JSON string of options')
    public String optionsJson;  // Serialize Map to JSON string

    @InvocableVariable(label='File Content' description='Base64 encoded content')
    public String fileContentBase64;  // Base64 encode Blob
}

// In your method, deserialize as needed
public static void process(List<FlowInput> inputs) {
    for (FlowInput input : inputs) {
        Map<String, String> options = (Map<String, String>)JSON.deserialize(
            input.optionsJson,
            Map<String, String>.class
        );

        Blob fileContent = EncodingUtil.base64Decode(input.fileContentBase64);
    }
}
```

---

## 7. Missing @JsonAccess Annotations

When using `JSON.serialize()` / `JSON.deserialize()` with inner classes or non-public classes, LLMs forget the `@JsonAccess` annotation required since API version 49.0.

### ❌ BAD: Missing JsonAccess

```apex
public class AccountService {
    // Inner class without @JsonAccess - JSON.serialize() fails silently
    private class AccountWrapper {
        public String name;
        public String industry;
    }

    public static String getAccountsJson() {
        List<AccountWrapper> wrappers = new List<AccountWrapper>();
        // ... populate ...
        return JSON.serialize(wrappers);  // Returns "[]" or throws error!
    }
}
```

### ✅ GOOD: With JsonAccess Annotation

```apex
public class AccountService {
    @JsonAccess(serializable='always' deserializable='always')
    private class AccountWrapper {
        public String name;
        public String industry;
    }

    public static String getAccountsJson() {
        List<AccountWrapper> wrappers = new List<AccountWrapper>();
        // ... populate ...
        return JSON.serialize(wrappers);  // Works correctly!
    }
}
```

### When @JsonAccess is Required

| Class Type | Needs @JsonAccess? |
|------------|-------------------|
| Public top-level class | No |
| Private inner class | **Yes** |
| Protected inner class | **Yes** |
| Public inner class | No (but recommended for clarity) |
| Class used only internally | No (unless serialized) |

---

## 8. Null Pointer from Missing Checks

LLMs often chain method calls without null safety, leading to null pointer exceptions.

### ❌ BAD: Chained Calls Without Null Checks

```apex
// Any of these could be null!
String city = [SELECT Id, Account.BillingAddress FROM Contact LIMIT 1]
    .Account
    .BillingAddress
    .getCity();
```

### ✅ GOOD: Safe Navigation Operator

```apex
// Use ?. for safe navigation
Contact c = [SELECT Id, Account.BillingCity FROM Contact LIMIT 1];
String city = c?.Account?.BillingCity;

// With default value
String city = c?.Account?.BillingCity ?? 'Unknown';
```

### ✅ GOOD: Explicit Null Checks

```apex
Contact c = [SELECT Id, Account.BillingCity FROM Contact LIMIT 1];

String city = 'Unknown';
if (c != null && c.Account != null && c.Account.BillingCity != null) {
    city = c.Account.BillingCity;
}
```

---

## 9. Incorrect DateTime Methods

LLMs confuse Date and DateTime methods, which have different APIs.

### Date vs DateTime Method Confusion

| Operation | Date Method | DateTime Method |
|-----------|-------------|-----------------|
| Add days | `addDays(n)` | `addDays(n)` |
| Add months | `addMonths(n)` | `addMonths(n)` |
| Add years | `addYears(n)` | N/A (use `addMonths(n*12)`) |
| Add hours | N/A | `addHours(n)` |
| Add minutes | N/A | `addMinutes(n)` |
| Add seconds | N/A | `addSeconds(n)` |
| Get day | `day()` | `day()` |
| Get month | `month()` | `month()` |
| Get year | `year()` | `year()` |
| Get hour | N/A | `hour()` |
| Get minute | N/A | `minute()` |
| Today | `Date.today()` | N/A |
| Now | N/A | `DateTime.now()` |

### ❌ BAD: Mixing Date/DateTime Methods

```apex
// Date doesn't have addHours!
Date d = Date.today();
Date future = d.addHours(5);  // COMPILE ERROR

// DateTime doesn't have a static today()!
DateTime now = DateTime.today();  // COMPILE ERROR
```

### ✅ GOOD: Correct Method Usage

```apex
// For Date operations
Date d = Date.today();
Date future = d.addDays(5);

// For DateTime operations
DateTime now = DateTime.now();
DateTime future = now.addHours(5);

// Converting between Date and DateTime
Date d = Date.today();
DateTime dt = DateTime.newInstance(d, Time.newInstance(0, 0, 0, 0));

DateTime dt = DateTime.now();
Date d = dt.date();
```

---

## 10. Collection Initialization Patterns

LLMs sometimes use incorrect patterns for initializing collections from SOQL or other collections.

### ❌ BAD: Incorrect Map Initialization

```apex
// This doesn't work - can't construct Map from SOQL directly with fields
Map<Id, String> nameMap = new Map<Id, String>(
    [SELECT Id, Name FROM Account]
);  // COMPILE ERROR - wrong constructor
```

### ✅ GOOD: Correct Map Initialization

```apex
// Map<Id, SObject> works directly with SOQL
Map<Id, Account> accountMap = new Map<Id, Account>(
    [SELECT Id, Name FROM Account]
);

// For Map<Id, SpecificField>, use a loop
Map<Id, String> nameMap = new Map<Id, String>();
for (Account acc : [SELECT Id, Name FROM Account]) {
    nameMap.put(acc.Id, acc.Name);
}
```

### ❌ BAD: List to Set Conversion

```apex
// Can't directly convert List to Set in constructor
List<Id> idList = new List<Id>{'001...', '001...'};
Set<Id> idSet = new Set<Id>(idList);  // Actually this DOES work in Apex!
```

### ✅ GOOD: Collection Conversions

```apex
// List to Set - this works!
List<Id> idList = new List<Id>{'001...', '001...'};
Set<Id> idSet = new Set<Id>(idList);

// Set to List
Set<Id> idSet = new Set<Id>{'001...', '001...'};
List<Id> idList = new List<Id>(idSet);

// Map keys to Set
Map<Id, Account> accountMap = new Map<Id, Account>([SELECT Id FROM Account]);
Set<Id> accountIds = accountMap.keySet();

// Map values to List
List<Account> accounts = accountMap.values();
```

---

## Quick Reference: LLM Validation Checklist

Before accepting LLM-generated Apex code, verify:

### Methods & Types
- [ ] No Java collection types (ArrayList, HashMap, etc.)
- [ ] No hallucinated methods (addMilliseconds, stream(), etc.)
- [ ] Correct Date vs DateTime methods

### Null Safety
- [ ] Map.get() has null check or uses containsKey()
- [ ] Chained method calls use safe navigation (?.)
- [ ] SOQL results checked before accessing

### SOQL
- [ ] All accessed fields are in SELECT clause
- [ ] Relationship fields use dot notation in query
- [ ] Parent records accessed safely

### Flow Integration
- [ ] InvocableVariable uses supported types
- [ ] No Map/Set in @InvocableVariable
- [ ] @JsonAccess on inner classes if serialized

### Triggers
- [ ] Recursion prevention mechanism in place
- [ ] Static flag or processed ID tracking

---

## Detection Script

Add this validation to your CI/CD pipeline:

```python
# detect_llm_patterns.py
import re

JAVA_TYPES = [
    r'\bArrayList\s*<',
    r'\bHashMap\s*<',
    r'\bHashSet\s*<',
    r'\bStringBuffer\b',
    r'\bStringBuilder\b',
    r'\bLinkedList\s*<',
    r'\bTreeMap\s*<',
]

HALLUCINATED_METHODS = [
    r'\.addMilliseconds\s*\(',
    r'\.stream\s*\(\)',
    r'\.getOrDefault\s*\(',
    r'DateTime\.today\s*\(\)',
]

def validate_apex(content):
    issues = []

    for pattern in JAVA_TYPES:
        if re.search(pattern, content):
            issues.append(f"Java type detected: {pattern}")

    for pattern in HALLUCINATED_METHODS:
        if re.search(pattern, content):
            issues.append(f"Non-existent method: {pattern}")

    return issues
```

---

## Reference

- **Existing Anti-Patterns**: See `references/anti-patterns.md` for traditional Apex anti-patterns
- **Best Practices**: See `references/best-practices.md` for correct patterns
- **Source**: [Salesforce Diaries - LLM Mistakes](https://salesforcediaries.com/2026/01/16/llm-mistakes-in-apex-lwc-salesforce-code-generation-rules/)
