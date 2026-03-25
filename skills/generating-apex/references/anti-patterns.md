# Apex Anti-Patterns

Code smells, performance anti-patterns, and refactoring strategies.

For critical anti-patterns (SOQL/DML in loops, missing sharing, hardcoded IDs, empty catches, SOQL injection), see the **SKILL.md "Never Generate These"** table.
For security anti-patterns, see [security-guide.md](security-guide.md).
For Apex testing guidance, use `generating-apex-test` skill.
For bulkification anti-patterns, see [bulkification-guide.md](bulkification-guide.md).

---

## Table of Contents

1. [Code Review Red Flags](#code-review-red-flags)
2. [Performance Anti-Patterns](#performance-anti-patterns)
3. [Code Smell Catalog](#code-smell-catalog)
4. [Refactoring Decision Guide](#refactoring-decision-guide)
5. [When NOT to Refactor](#when-not-to-refactor)
6. [Detection Tools](#detection-tools)

---

## Code Review Red Flags

These patterns indicate poor code quality and should be refactored.

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| **SOQL without WHERE or LIMIT** | Returns all records, slow | Always add `WHERE` clause or `LIMIT` |
| **Multiple triggers on object** | Unpredictable execution order | Single trigger + Trigger Actions Framework |
| **Generic `Exception` only** | Masks specific errors | Catch specific exceptions first |
| **No trigger bypass flag** | Can't disable for data loads | Add Custom Setting bypass |
| **`System.debug()` in main code paths** | Performance impact from concatenating variables, even when logs are disabled | Use logging framework with levels |
| **Unnecessary `isEmpty()` before DML** | Wastes CPU | Remove - DML handles empty lists |
| **`!= false` comparisons** | Confusing double negative | Use `== true` or just the boolean |
| **God Class** | Single class does everything | Split into Service/Selector/Domain |
| **Magic Numbers** | Hardcoded values like `if (score > 75)` | Use named constants |

---

### SOQL Without WHERE or LIMIT

**❌ BAD:**
```apex
List<Account> accounts = [SELECT Id FROM Account];
// Returns ALL accounts - could be millions!
```

**✅ GOOD:**
```apex
// Option 1: Filter
List<Account> accounts = [SELECT Id FROM Account WHERE Industry = 'Technology'];

// Option 2: Limit
List<Account> accounts = [SELECT Id FROM Account ORDER BY CreatedDate DESC LIMIT 200];

// Option 3: Both
List<Account> accounts = [SELECT Id FROM Account WHERE CreatedDate = THIS_YEAR LIMIT 1000];
```

---

### Multiple Triggers on Same Object

**❌ BAD:**
```apex
// AccountTrigger1.trigger
trigger AccountTrigger1 on Account (before insert) {
    // Some logic
}

// AccountTrigger2.trigger
trigger AccountTrigger2 on Account (before insert) {
    // More logic - which runs first?
}
```

**✅ GOOD:**
```apex
// Single trigger + TAF
trigger AccountTrigger on Account (before insert, after insert, before update, after update) {
    new MetadataTriggerHandler().run();
}

// Separate action classes
public class TA_Account_SetDefaults implements TriggerAction.BeforeInsert { }
public class TA_Account_Validate implements TriggerAction.BeforeInsert { }
```

---

### Generic Exception Only

**❌ BAD:**
```apex
try {
    insert accounts;
} catch (Exception e) {
    // Catches EVERYTHING - too broad
}
```

**✅ GOOD:**
```apex
try {
    insert accounts;
} catch (DmlException e) {
    // Handle DML errors specifically
    System.debug('DML failed: ' + e.getDmlMessage(0));
} catch (Exception e) {
    // Catch unexpected errors
    System.debug('Unexpected error: ' + e.getMessage());
    throw e;
}
```

---

### Unnecessary isEmpty() Before DML

**❌ BAD:**
```apex
if (!accounts.isEmpty()) {
    update accounts;
}
// Wastes CPU checking - DML already handles empty lists
```

**✅ GOOD:**
```apex
update accounts;  // No-op if empty, no error thrown
```

---

### Double Negative Comparisons

**❌ BAD:**
```apex
if (acc.IsActive__c != false) {
    // Confusing logic
}
```

**✅ GOOD:**
```apex
if (acc.IsActive__c == true) {
    // Clear intent
}

// Or even better
if (acc.IsActive__c) {
    // Most concise
}
```

---

<a id="performance-anti-patterns"></a>

## Performance Anti-Patterns

### 1. Nested Loops with SOQL

**❌ BAD:**
```apex
for (Account acc : accounts) {
    for (Contact con : [SELECT Id FROM Contact WHERE AccountId = :acc.Id]) {
        // Nested SOQL - quadratic complexity!
    }
}
```

**✅ GOOD:**
```apex
Map<Id, Account> accountsWithContacts = new Map<Id, Account>([
    SELECT Id, (SELECT Id FROM Contacts)
    FROM Account
    WHERE Id IN :accountIds
]);

for (Account acc : accountsWithContacts.values()) {
    for (Contact con : acc.Contacts) {
        // No SOQL in loop
    }
}
```

---

### 2. Querying in Constructor

**❌ BAD:**
```apex
public class AccountService {
    private List<Account> accounts;

    public AccountService() {
        accounts = [SELECT Id FROM Account];  // Runs on EVERY instantiation
    }
}
```

**✅ GOOD:**
```apex
public class AccountService {
    private List<Account> accounts;

    public AccountService(List<Account> accounts) {
        this.accounts = accounts;  // Inject dependencies
    }

    // Or lazy load only when needed
    private List<Account> getAccounts() {
        if (accounts == null) {
            accounts = [SELECT Id FROM Account LIMIT 200];
        }
        return accounts;
    }
}
```

---

### 3. Excessive CPU Time

**❌ BAD:**
```apex
for (Account acc : accounts) {
    for (Integer i = 0; i < 10000; i++) {
        String hash = EncodingUtil.convertToHex(Crypto.generateDigest('SHA256', Blob.valueOf(acc.Name + i)));
        // Expensive crypto in nested loop
    }
}
```

**✅ GOOD:**
```apex
// Move expensive operations outside loops
String baseHash = EncodingUtil.convertToHex(Crypto.generateDigest('SHA256', Blob.valueOf('base')));

for (Account acc : accounts) {
    acc.Hash__c = baseHash;  // Reuse computed value
}
```

---

### 4. Inefficient Collections

**❌ BAD:**
```apex
List<Id> uniqueIds = new List<Id>();
for (Id accountId : allIds) {
    if (!uniqueIds.contains(accountId)) {  // O(n) lookup in List
        uniqueIds.add(accountId);
    }
}
```

**✅ GOOD:**
```apex
Set<Id> uniqueIds = new Set<Id>(allIds);  // O(1) deduplication
```

---

## Code Smell Catalog

Based on "Clean Apex Code" by Pablo Gonzalez and clean code principles.

### Long Methods

#### The Smell

Methods exceeding 20-30 lines, doing too much, hard to verify in isolation.

#### Signs

- Method name is vague (`processData`, `handleStuff`)
- Multiple levels of nesting
- Many local variables
- Comments separating "sections" of work

#### Before

```apex
public void processOpportunity(Opportunity opp) {
    // Validate opportunity
    if (opp == null) {
        throw new IllegalArgumentException('Opportunity cannot be null');
    }
    if (opp.AccountId == null) {
        throw new IllegalArgumentException('Account is required');
    }
    if (opp.Amount == null || opp.Amount <= 0) {
        throw new IllegalArgumentException('Valid amount required');
    }

    // Calculate discount
    Account acc = [SELECT Type, AnnualRevenue FROM Account WHERE Id = :opp.AccountId];
    Decimal discountRate = 0;
    if (acc.Type == 'Enterprise') {
        if (acc.AnnualRevenue > 1000000) {
            discountRate = 0.20;
        } else {
            discountRate = 0.15;
        }
    } else if (acc.Type == 'Partner') {
        discountRate = 0.10;
    }
    opp.Discount__c = opp.Amount * discountRate;

    // Assign to team
    if (opp.Amount > 100000) {
        opp.OwnerId = getEnterpriseTeamQueue();
    } else if (opp.Amount > 25000) {
        opp.OwnerId = getMidMarketQueue();
    }

    // Send notifications
    if (discountRate > 0.15) {
        sendApprovalRequest(opp);
    }
    if (opp.Amount > 500000) {
        notifyExecutiveTeam(opp);
    }

    update opp;
}
```

#### After

```apex
public void processOpportunity(Opportunity opp) {
    validateOpportunity(opp);

    Account account = getAccountForOpportunity(opp);
    applyDiscount(opp, account);
    assignToAppropriateTeam(opp);
    sendRequiredNotifications(opp);

    update opp;
}

private void validateOpportunity(Opportunity opp) {
    if (opp == null) {
        throw new IllegalArgumentException('Opportunity cannot be null');
    }
    if (opp.AccountId == null) {
        throw new IllegalArgumentException('Account is required');
    }
    if (opp.Amount == null || opp.Amount <= 0) {
        throw new IllegalArgumentException('Valid amount required');
    }
}

private Account getAccountForOpportunity(Opportunity opp) {
    return [SELECT Type, AnnualRevenue FROM Account WHERE Id = :opp.AccountId];
}

private void applyDiscount(Opportunity opp, Account account) {
    Decimal discountRate = DiscountRules.calculateRate(account);
    opp.Discount__c = opp.Amount * discountRate;
}

private void assignToAppropriateTeam(Opportunity opp) {
    opp.OwnerId = TeamAssignment.getQueueForAmount(opp.Amount);
}

private void sendRequiredNotifications(Opportunity opp) {
    NotificationService.sendIfRequired(opp);
}
```

#### When to Extract

Extract a method when:
- The code block can be understood independently
- It doesn't require knowledge of the caller's implementation
- It serves a purpose beyond the immediate use case
- You find yourself writing a comment to explain what a section does

**Refactoring**: Extract Method - split into smaller methods with single responsibilities.

---

### Mixed Abstraction Levels

See [design-patterns.md — Abstraction Level Management](design-patterns.md#abstraction-level-management) for the full pattern with architecture diagram and guidelines.

---

### Boolean Parameter Proliferation

#### The Smell

Methods with multiple boolean parameters that control behavior.

#### Signs

- Method calls like `process(acc, true, false, true)`
- Hard to remember which boolean does what
- Many if/else branches based on parameters

#### Before

```apex
public void createCase(
    String subject,
    String description,
    Id accountId,
    Boolean sendEmail,
    Boolean highPriority,
    Boolean assignToQueue,
    String origin
) {
    Case c = new Case(Subject = subject, Description = description);
    if (highPriority) {
        c.Priority = 'High';
    }
    if (assignToQueue) {
        c.OwnerId = getDefaultQueue();
    }
    // ... more conditionals
}

// Caller - which boolean is which?
createCase('Issue', 'Desc', accId, true, false, true, 'Web');
```

#### After: Options Object Pattern

```apex
public class CaseOptions {
    public Boolean sendEmail = false;
    public Boolean highPriority = false;
    public Boolean assignToQueue = true;
    public String origin = 'Web';

    public CaseOptions withEmail() {
        this.sendEmail = true;
        return this;
    }

    public CaseOptions withHighPriority() {
        this.highPriority = true;
        return this;
    }

    public CaseOptions withOrigin(String origin) {
        this.origin = origin;
        return this;
    }
}

public Case createCase(String subject, String description, Id accountId, CaseOptions options) {
    Case c = new Case(
        Subject = subject,
        Description = description,
        AccountId = accountId,
        Priority = options.highPriority ? 'High' : 'Medium',
        Origin = options.origin
    );

    if (options.assignToQueue) {
        c.OwnerId = getDefaultQueue();
    }

    insert c;

    if (options.sendEmail) {
        sendCaseConfirmation(c);
    }

    return c;
}

// Clear, self-documenting caller
Case newCase = createCase(
    'Login Issue',
    'Cannot access account',
    accountId,
    new CaseOptions()
        .withEmail()
        .withHighPriority()
        .withOrigin('Phone')
);
```

---

### Magic Numbers and Strings

#### The Smell

Hardcoded values scattered throughout code without explanation.

#### Signs

- Numbers like `5`, `100`, `1000000` without context
- String literals like `'Enterprise'`, `'Active'`
- Same value repeated in multiple places

#### Before

```apex
if (account.AnnualRevenue > 1000000) {
    if (retryCount < 5) {
        if (account.Type == 'Enterprise') {
            // process
        }
    }
}

// Elsewhere in code
if (customer.Revenue__c > 1000000) { }  // Same threshold, different field
```

#### After

```apex
public class AccountConstants {
    public static final Decimal HIGH_VALUE_THRESHOLD = 1000000;
    public static final Integer MAX_RETRY_ATTEMPTS = 5;
    public static final String TYPE_ENTERPRISE = 'Enterprise';
    public static final String TYPE_PARTNER = 'Partner';
    public static final String STATUS_ACTIVE = 'Active';
}

// Usage
if (account.AnnualRevenue > AccountConstants.HIGH_VALUE_THRESHOLD) {
    if (retryCount < AccountConstants.MAX_RETRY_ATTEMPTS) {
        if (account.Type == AccountConstants.TYPE_ENTERPRISE) {
            // process
        }
    }
}
```

#### Benefits

- Single source of truth
- Self-documenting code
- Easy to change values globally
- Prevents typos in string literals

---

### Complex Conditionals

#### The Smell

Long, nested boolean expressions that are hard to understand.

#### Signs

- Multiple `&&` and `||` in one expression
- Negations of negations
- Conditions spanning multiple lines without names

#### Before

```apex
if (account.Type == 'Enterprise' &&
    account.AnnualRevenue > 1000000 &&
    account.NumberOfEmployees > 500 &&
    (account.Industry == 'Technology' || account.Industry == 'Finance') &&
    account.BillingCountry == 'United States' &&
    account.Rating == 'Hot') {
    // 50 lines of logic
}
```

#### Step 1: Named Boolean Variables

_Improves readability by naming each condition, but the logic still sits inline — the reader must parse it even if they don't care about the details._

```apex
Boolean isEnterpriseCustomer = account.Type == 'Enterprise';
Boolean isHighValue = account.AnnualRevenue > 1000000;
Boolean isLargeCompany = account.NumberOfEmployees > 500;
Boolean isTargetIndustry = account.Industry == 'Technology' ||
                           account.Industry == 'Finance';
Boolean isDomestic = account.BillingCountry == 'United States';
Boolean isHotLead = account.Rating == 'Hot';

Boolean isStrategicAccount = isEnterpriseCustomer &&
                              isHighValue &&
                              isLargeCompany &&
                              isTargetIndustry &&
                              isDomestic &&
                              isHotLead;

if (isStrategicAccount) {
    processStrategicAccount(account);
}
```

#### Step 2: Extract Method (Recommended)

_Move the decision behind a single descriptive method name. Callers see **what** is being checked; only maintainers who open the method see **how**._

```apex
// In the same class — no new file needed
private Boolean isStrategicAccount(Account account) {
    Boolean isEnterpriseCustomer = account.Type == 'Enterprise';
    Boolean isHighValue = account.AnnualRevenue > 1000000;
    Boolean isLargeCompany = account.NumberOfEmployees > 500;
    Boolean isTargetIndustry = account.Industry == 'Technology' ||
                               account.Industry == 'Finance';
    Boolean isDomestic = account.BillingCountry == 'United States';
    Boolean isHotLead = account.Rating == 'Hot';

    return isEnterpriseCustomer && isHighValue && isLargeCompany &&
           isTargetIndustry && isDomestic && isHotLead;
}

// Clean call site — one line, self-documenting
if (isStrategicAccount(account)) {
    processStrategicAccount(account);
}
```

#### Step 3: Domain Rules Class

_Best for rules reused across triggers, batch jobs, and flows._

```apex
// Reusable business rules
public class AccountRules {
    public static Boolean isStrategicAccount(Account account) {
        return isEnterpriseCustomer(account) &&
               isHighValue(account) &&
               isInTargetMarket(account);
    }

    public static Boolean isEnterpriseCustomer(Account account) {
        return account.Type == 'Enterprise' &&
               account.NumberOfEmployees > 500;
    }

    public static Boolean isHighValue(Account account) {
        return account.AnnualRevenue != null &&
               account.AnnualRevenue > 1000000;
    }

    public static Boolean isInTargetMarket(Account account) {
        Set<String> targetIndustries = new Set<String>{'Technology', 'Finance'};
        return targetIndustries.contains(account.Industry) &&
               account.BillingCountry == 'United States';
    }
}

// Clean usage
if (AccountRules.isStrategicAccount(account)) {
    processStrategicAccount(account);
}
```

---

### Large Class (God Class)

**Smell**: Class exceeds 500 lines or has 20+ methods.

**❌ BAD:**
```apex
public class AccountService {
    // 50 methods mixing concerns:
    public static void createAccount() { }
    public static void updateAccount() { }
    public static void validateAccount() { }
    public static void calculateScore() { }
    public static void sendEmail() { }
    public static void generateReport() { }
    // ... 44 more methods
}
```

**✅ GOOD:**
```apex
// Split by responsibility
public class AccountService { }         // Business logic
public class AccountValidator { }       // Validation
public class AccountScoreCalculator { } // Scoring
public class AccountEmailService { }    // Notifications
public class AccountReportGenerator { } // Reporting
```

**Refactoring**: Extract Class - split into multiple classes by concern.

---

### Long Parameter List

**Smell**: Method has 5+ parameters.

**❌ BAD:**
```apex
public static void createAccount(
    String name,
    String industry,
    Decimal revenue,
    String phone,
    String email,
    String website,
    Id ownerId
) { }
```

**✅ GOOD:**
```apex
public class AccountRequest {
    public String name;
    public String industry;
    public Decimal revenue;
    public String phone;
    public String email;
    public String website;
    public Id ownerId;
}

public static void createAccount(AccountRequest request) { }
```

---

### Feature Envy

**Smell**: Method uses more methods/fields from another class than its own.

**❌ BAD:**
```apex
public class OrderService {
    public static Decimal calculateDiscount(Order__c order) {
        Account acc = [SELECT Id, Tier__c FROM Account WHERE Id = :order.Account__c];
        if (acc.Tier__c == 'Gold') {
            return order.Amount__c * 0.2;
        } else if (acc.Tier__c == 'Silver') {
            return order.Amount__c * 0.1;
        }
        return 0;
    }
}
```

**✅ GOOD:**
```apex
public class AccountDomain {
    public static Decimal getDiscountRate(Account acc) {
        if (acc.Tier__c == 'Gold') return 0.2;
        if (acc.Tier__c == 'Silver') return 0.1;
        return 0;
    }
}

public class OrderService {
    public static Decimal calculateDiscount(Order__c order) {
        Account acc = [SELECT Id, Tier__c FROM Account WHERE Id = :order.Account__c];
        return order.Amount__c * AccountDomain.getDiscountRate(acc);
    }
}
```

**Refactoring**: Extract to Domain class — move discount logic to the class that owns Account behavior.

---

### Primitive Obsession

**Smell**: Using primitives instead of small objects to represent concepts.

**❌ BAD:**
```apex
public static void sendEmail(String address, String subject, String body) {
    // Validates email format inline
    if (!address.contains('@')) throw new InvalidEmailException();
}
```

**✅ GOOD:**
```apex
public class EmailAddress {
    private String value;

    public EmailAddress(String address) {
        if (!address.contains('@')) {
            throw new InvalidEmailException('Invalid email format');
        }
        this.value = address;
    }

    public String getValue() {
        return value;
    }
}

public static void sendEmail(EmailAddress address, String subject, String body) {
    // Email is already validated
}
```

---

## Refactoring Decision Guide

| Smell | Quick Fix | Proper Fix |
|-------|-----------|------------|
| Long method | Extract method | Separate concerns into classes |
| Mixed abstraction | Extract low-level to methods | Create abstraction layers |
| Boolean parameters | Options object | Strategy pattern |
| Magic numbers | Named constants | Configuration class |
| Complex conditionals | Named booleans | Domain class |
| Duplicate code | Extract method | Selector/Service pattern |
| Deep nesting | Guard clauses | Command pattern |
| God class | Split methods | Proper architecture |

---

## When NOT to Refactor

- **Working code under deadline**: Don't refactor what you don't have time to validate
- **No quality checks exist**: Establish validation/quality checks first, then refactor
- **Code is being deprecated**: Don't polish what's being removed
- **Premature abstraction**: Wait until you have 3 concrete examples before abstracting

---

## Detection Tools

**How to find anti-patterns:**

| Tool | What It Finds |
|------|---------------|
| **Salesforce Code Analyzer** | SOQL/DML in loops, security issues |
| **PMD (via VS Code)** | Code quality, complexity, unused code |
| **Developer Console** | Debug logs |
| **Grep/Search** | Hardcoded IDs, empty catches, magic numbers |

**VS Code Command:**
```bash
sf code-analyzer run --workspace force-app/main/default/classes --view table
```

**Example output:**
```
Severity  File                    Line  Rule                     Message
────────────────────────────────────────────────────────────────────────────
3         AccountService.cls      45    ApexSOQLInjection        SOQL injection risk
2         AccountTrigger.trigger  12    ApexCRUDViolation        Missing FLS check
```

---

## Refactoring Checklist

See [code-review-checklist.md](code-review-checklist.md) for the consolidated review checklist covering bulkification, security, architecture, and clean code.
