# Apex Security Guide

Comprehensive guide to Apex security including CRUD/FLS enforcement, sharing rules, and SOQL injection prevention.

---

## Table of Contents

1. [CRUD and FLS (Field-Level Security)](#crud-and-fls-field-level-security)
2. [Sharing and Record Access](#sharing-and-record-access)
3. [SOQL Injection Prevention](#soql-injection-prevention)
4. [Security Checklist](#security-checklist)

---

<a id="crud-and-fls-field-level-security"></a>

## CRUD and FLS (Field-Level Security)

### API 62.0: WITH USER_MODE

**Modern approach (API 62.0+)**: Use `WITH USER_MODE` in SOQL to enforce CRUD and FLS automatically.

```apex
// ✅ GOOD: Respects user permissions
List<Account> accounts = [
    SELECT Id, Name, Industry, AnnualRevenue
    FROM Account
    WHERE Industry = 'Technology'
    WITH USER_MODE
];
```

**DML with USER_MODE**: Use `AccessLevel.USER_MODE` for Database methods to enforce CRUD/FLS on insert, update, and delete:

```apex
// ✅ GOOD: Enforces CRUD/FLS on DML operations
Database.insert(records, AccessLevel.USER_MODE);
Database.update(records, AccessLevel.USER_MODE);
Database.delete(records, AccessLevel.USER_MODE);
```

**What USER_MODE does**:
- Enforces object-level CRUD (Create, Read, Update, Delete)
- Enforces field-level security (FLS)
- Throws `System.QueryException` if user lacks access (for SOQL)
- Throws `System.DmlException` if user lacks access (for DML)
- Respects user's sharing rules (when combined with `with sharing`)

**When to use SYSTEM_MODE**:
```apex
// Only use SYSTEM_MODE when you explicitly NEED to bypass security
List<Account> accounts = [
    SELECT Id, Name, Sensitive_Field__c
    FROM Account
    WITH SYSTEM_MODE  // ⚠️ Use with caution!
];
```

**Use cases for SYSTEM_MODE**:
- Background jobs that must process all records regardless of user
- System integrations
- Administrative cleanup scripts

**ALWAYS document why SYSTEM_MODE is needed:**
```apex
// JUSTIFICATION: This batch job processes all accounts for regulatory reporting,
// regardless of user's access level. Approved by Security Team on 2025-01-01.
```

---

### Legacy Approach: Security.stripInaccessible()

**For pre-62.0 compatibility** or when you need to filter fields dynamically:

```apex
// Query all fields
List<Account> accounts = [SELECT Id, Name, Industry, AnnualRevenue FROM Account];

// Strip inaccessible fields
SObjectAccessDecision decision = Security.stripInaccessible(
    AccessType.READABLE,
    accounts
);

// Use stripped records
List<Account> accessibleAccounts = decision.getRecords();

// Check which fields were removed
Set<String> removedFields = decision.getRemovedFields().get('Account');
if (removedFields != null && !removedFields.isEmpty()) {
    System.debug('User lacks access to fields: ' + removedFields);
}
```

**Access Types**:
- `READABLE` - Read access (for queries)
- `CREATABLE` - Create access (before insert)
- `UPDATABLE` - Update access (before update)
- `UPSERTABLE` - Upsert access

**Example: Pre-DML Check**
```apex
public static void createAccounts(List<Account> accounts) {
    // Check if user can create these fields
    SObjectAccessDecision decision = Security.stripInaccessible(
        AccessType.CREATABLE,
        accounts
    );

    if (!decision.getRemovedFields().isEmpty()) {
        throw new SecurityException('User lacks permission to create some fields');
    }

    insert decision.getRecords();
}
```

---

### Manual CRUD/FLS Checks (Verbose but Explicit)

```apex
// Check object-level CRUD
if (!Schema.sObjectType.Account.isAccessible()) {
    throw new SecurityException('User cannot read Accounts');
}

if (!Schema.sObjectType.Account.isCreateable()) {
    throw new SecurityException('User cannot create Accounts');
}

// Check field-level security
if (!Schema.sObjectType.Account.fields.Industry.isAccessible()) {
    throw new SecurityException('User cannot read Industry field');
}

if (!Schema.sObjectType.Account.fields.Industry.isUpdateable()) {
    throw new SecurityException('User cannot update Industry field');
}
```

**When to use**: Legacy codebases, specific error messaging, or when you need fine-grained control.

---

## Sharing and Record Access

### Sharing Keywords

| Keyword | Behavior | When to Use |
|---------|----------|-------------|
| `with sharing` | Enforces record-level sharing | Default for user-facing code |
| `without sharing` | Bypasses record-level sharing | System operations, integrations |
| `inherited sharing` | Inherits from calling class | Utility classes, shared libraries |

**Default Rule**: If no keyword specified, class runs in `without sharing` mode (pre-API 40 behavior).

**ALWAYS specify a sharing keyword** - implicit behavior is confusing.

---

### with sharing (Recommended Default)

```apex
public with sharing class AccountService {

    public static List<Account> getAccountsForUser() {
        // User only sees Accounts they have access to via sharing rules
        return [SELECT Id, Name FROM Account WITH USER_MODE];
    }

    public static void updateAccount(Account acc) {
        // Throws exception if user lacks access
        update acc;
    }
}
```

**Use cases**:
- User-facing controllers (LWC, Aura, Visualforce)
- Service classes handling user requests
- Trigger actions that respect user context

---

### without sharing (Use Sparingly)

```apex
public without sharing class AdminService {

    // JUSTIFICATION: This method is only called by system administrators
    // to perform global updates. Access controlled by Custom Permission.
    public static void globalAccountUpdate() {
        List<Account> allAccounts = [SELECT Id, Name FROM Account];
        // Process ALL accounts, ignoring sharing
    }
}
```

**Use cases**:
- Background jobs
- System integrations
- Administrative operations

**Security Note**: Always add access control checks when using `without sharing`:
```apex
public without sharing class AdminService {

    public static void globalUpdate() {
        // Check permission before executing
        if (!FeatureManagement.checkPermission('Admin_Global_Update')) {
            throw new SecurityException('Requires Admin_Global_Update permission');
        }

        // Now safe to proceed with without sharing logic
    }
}
```

---

### inherited sharing (Best for Utilities)

```apex
public inherited sharing class StringUtils {

    // Inherits sharing from calling class
    public static String sanitize(String input) {
        return String.escapeSingleQuotes(input);
    }
}

// Called from "with sharing" class → runs with sharing
// Called from "without sharing" class → runs without sharing
```

**Use cases**:
- Utility classes
- Helper methods
- Shared libraries that don't directly query records

---

### Mixing Sharing Contexts

```apex
public with sharing class UserFacingService {

    public static void processAccount(Id accountId) {
        // This runs WITH sharing
        Account acc = [SELECT Id, Name FROM Account WHERE Id = :accountId];

        // Call a without sharing method for specific operation
        SystemOperations.performGlobalCheck(acc);
    }
}

public without sharing class SystemOperations {

    public static void performGlobalCheck(Account acc) {
        // This runs WITHOUT sharing
        // Can access records the original user couldn't see
    }
}
```

**Pattern**: Start with `with sharing`, only escalate to `without sharing` when needed.

---

## SOQL Injection Prevention

### The Problem

**NEVER concatenate user input into SOQL strings:**

```apex
// ❌ VULNERABLE to SOQL injection
public static List<Account> searchAccounts(String userInput) {
    String query = 'SELECT Id, Name FROM Account WHERE Name = \'' + userInput + '\'';
    return Database.query(query);
}

// Attack: userInput = "test' OR '1'='1"
// Results in: SELECT Id, Name FROM Account WHERE Name = 'test' OR '1'='1'
// Returns ALL accounts!
```

---

### Solution 1: Bind Variables (Recommended)

```apex
// ✅ SAFE: Use bind variables
public static List<Account> searchAccounts(String userInput) {
    return [SELECT Id, Name FROM Account WHERE Name = :userInput WITH USER_MODE];
}

// Even with malicious input, it's treated as a literal string
```

**Why it works**: Salesforce treats `:userInput` as a value, not executable SOQL.

---

### Solution 2: String.escapeSingleQuotes()

**When dynamic SOQL is unavoidable** (rare cases):

```apex
// ✅ SAFE: Escape user input
public static List<Account> dynamicSearch(String userInput) {
    String sanitized = String.escapeSingleQuotes(userInput);
    String query = 'SELECT Id, Name FROM Account WHERE Name = \'' + sanitized + '\'';
    return Database.query(query);
}
```

**What it does**: Escapes single quotes (`'` → `\'`) to prevent breaking out of string literals.

**Still prefer bind variables** - escapeSingleQuotes is a backup.

---

### Solution 3: Allowlist Validation

**For field names, operators, or other dynamic query parts:**

```apex
public static List<Account> sortedAccounts(String sortField) {
    // ✅ SAFE: Validate against allowlist
    Set<String> allowedFields = new Set<String>{'Name', 'Industry', 'AnnualRevenue'};

    if (!allowedFields.contains(sortField)) {
        throw new IllegalArgumentException('Invalid sort field');
    }

    String query = 'SELECT Id, Name, Industry FROM Account ORDER BY ' + sortField;
    return Database.query(query);
}
```

**Use case**: Dynamic ORDER BY, dynamic field selection (but NOT WHERE clause values).

---

### Dynamic SOQL Best Practices

**Pattern: Safe Dynamic Query Builder**
```apex
public class SafeQueryBuilder {

    private static final Set<String> ALLOWED_FIELDS = new Set<String>{
        'Id', 'Name', 'Industry', 'AnnualRevenue'
    };

    private static final Set<String> ALLOWED_OPERATORS = new Set<String>{
        '=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN'
    };

    public static List<Account> query(
        String field,
        String operator,
        String value
    ) {
        // Validate field
        if (!ALLOWED_FIELDS.contains(field)) {
            throw new IllegalArgumentException('Invalid field: ' + field);
        }

        // Validate operator
        if (!ALLOWED_OPERATORS.contains(operator)) {
            throw new IllegalArgumentException('Invalid operator: ' + operator);
        }

        // Use bind variable for value
        String query = 'SELECT Id, Name FROM Account WHERE ' + field + ' ' + operator + ' :value WITH USER_MODE';
        return Database.query(query);
    }
}
```

---

## Security Checklist

Use this checklist when generating or reviewing Apex code:

### CRUD/FLS

- [ ] All SOQL queries use `WITH USER_MODE` (or `Security.stripInaccessible()` for pre-62.0)
- [ ] DML operations check `isCreateable()`, `isUpdateable()`, `isDeletable()` OR use `WITH USER_MODE`
- [ ] Custom fields have Permission Sets/Profiles granting FLS
- [ ] System operations using `WITH SYSTEM_MODE` are documented with justification

### Sharing

- [ ] All classes have explicit sharing keyword (`with sharing`, `without sharing`, or `inherited sharing`)
- [ ] User-facing classes use `with sharing`
- [ ] `without sharing` classes have documented justification
- [ ] `without sharing` classes include Custom Permission checks

### SOQL Injection

- [ ] No string concatenation in WHERE clauses with user input
- [ ] All user input uses bind variables (`:variableName`)
- [ ] Dynamic SOQL uses allowlist validation for field names/operators
- [ ] `String.escapeSingleQuotes()` used if concatenation is unavoidable

### General Security

- [ ] No hardcoded credentials or API keys (use Named Credentials)
- [ ] No hardcoded Record IDs (use Custom Metadata or queries)
- [ ] Sensitive data (SSN, PII) is encrypted at rest (Platform Encryption)
- [ ] External callouts use Named Credentials, not plain URLs
- [ ] Error messages don't leak sensitive information

---

## Advanced Security Patterns

### Custom Permissions

**Check user has specific permission before dangerous operations:**

```apex
public without sharing class DataDeletionService {

    public static void deleteAllTestData() {
        // Check Custom Permission
        if (!FeatureManagement.checkPermission('Delete_Test_Data')) {
            throw new SecurityException('Requires Delete_Test_Data permission');
        }

        // Safe to proceed
        delete [SELECT Id FROM Account WHERE Name LIKE 'TEST%'];
    }
}
```

**Create Custom Permission**: Setup → Custom Permissions → New

---

### Secure Remote Actions (@AuraEnabled)

```apex
public with sharing class AccountController {

    @AuraEnabled(cacheable=true)
    public static List<Account> getAccounts() {
        // Runs with sharing + user mode = secure
        return [SELECT Id, Name FROM Account WITH USER_MODE LIMIT 50];
    }

    @AuraEnabled
    public static void updateAccount(Account acc) {
        // Verify user can update
        if (!Schema.sObjectType.Account.isUpdateable()) {
            throw new AuraHandledException('No update permission');
        }

        update acc;
    }
}
```

**Security Notes**:
- Always use `with sharing` for `@AuraEnabled` methods
- Use `WITH USER_MODE` in SOQL
- Validate DML permissions before operations
- Use `AuraHandledException` for friendly error messages

---

### Platform Events Security

```apex
public with sharing class EventPublisher {

    public static void publishEvent(String message) {
        // Check if user can create Platform Events
        if (!Schema.sObjectType.MyEvent__e.isCreateable()) {
            throw new SecurityException('Cannot publish events');
        }

        MyEvent__e event = new MyEvent__e(
            Message__c = message
        );

        EventBus.publish(event);
    }
}
```

---

### Custom Settings for Bypass Flags

Enable admins to disable automation without code changes:

```apex
public class TriggerConfig {
    private static Trigger_Settings__c settings;

    public static Boolean isDisabled(String triggerName) {
        if (settings == null) {
            settings = Trigger_Settings__c.getInstance();
        }

        return settings?.Disable_All_Triggers__c == true ||
               (Boolean)settings.get('Disable_' + triggerName + '__c') == true;
    }
}

// Usage in trigger action
if (TriggerConfig.isDisabled('Account')) {
    return;
}
```

---

## Common Security Vulnerabilities

| Vulnerability | Example | Fix |
|---------------|---------|-----|
| **SOQL Injection** | `'WHERE Name = \'' + input + '\''` | Use bind variable `:input` |
| **XSS (Cross-Site Scripting)** | Returning unsanitized HTML | Use `HTMLENCODE()` in VF or LWC escaping |
| **Insecure Direct Object Reference** | Accepting record ID from user without checking access | Query with `WITH USER_MODE`, verify in `with sharing` |
| **Hardcoded Credentials** | `String apiKey = 'abc123';` | Use Named Credentials |
| **Missing FLS** | Directly querying fields without checking | Use `WITH USER_MODE` |
| **Overly Permissive Sharing** | `without sharing` everywhere | Use `with sharing` by default |

**Back to Main**: [SKILL.md](../SKILL.md)
