# Apex Troubleshooting Guide

Comprehensive guide to debugging Apex code, LSP validation, dependency management, and common deployment issues.

---

## Table of Contents

1. [LSP-Based Validation (Auto-Fix Loop)](#lsp-based-validation-auto-fix-loop)
2. [Cross-Skill Dependency Checklist](#cross-skill-dependency-checklist)
3. [Common Deployment Errors](#common-deployment-errors)
4. [Debug Logs and Monitoring](#debug-logs-and-monitoring)
5. [Governor Limit Debugging](#governor-limit-debugging)
6. [Test Failures](#test-failures)

---

<a id="lsp-based-validation-auto-fix-loop"></a>

## LSP-Based Validation (Auto-Fix Loop)

The sf-apex skill includes Language Server Protocol (LSP) integration for real-time syntax validation. This enables Claude to automatically detect and fix Apex syntax errors during code authoring.

### How It Works

1. **PostToolUse Hook**: After every Write/Edit operation on `.cls` or `.trigger` files, the LSP hook validates syntax
2. **Apex Language Server**: Uses Salesforce's official `apex-jorje-lsp.jar` (from VS Code extension)
3. **Auto-Fix Loop**: If errors are found, Claude receives diagnostics and auto-fixes them (max 3 attempts)
4. **Two-Layer Validation**:
   - **LSP Validation**: Fast syntax checking (~500ms)
   - **150-Point Validation**: Semantic analysis for best practices

---

### Prerequisites

For LSP validation to work, users must have:

| Requirement | How to Install |
|-------------|----------------|
| **VS Code Salesforce Extension Pack** | VS Code → Extensions → "Salesforce Extension Pack" |
| **Java 11+ (Adoptium recommended)** | https://adoptium.net/temurin/releases/ |

**Verify Installation:**
```bash
# Check VS Code extensions
code --list-extensions | grep salesforce

# Check Java version
java -version
# Should output: openjdk version "11.x.x" or higher
```

---

### Validation Flow

```
User writes Apex code → Write/Edit tool executes
                              ↓
                    ┌─────────────────────────┐
                    │   LSP Validation (fast) │
                    │   Syntax errors only    │
                    └─────────────────────────┘
                              ↓
                    ┌─────────────────────────┐
                    │  150-Point Validation   │
                    │  Semantic best practices│
                    └─────────────────────────┘
                              ↓
                    Claude sees any errors and auto-fixes
```

---

### Sample LSP Error Output

```
============================================================
🔍 APEX LSP VALIDATION RESULTS
   File: force-app/main/default/classes/MyClass.cls
   Attempt: 1/3
============================================================

Found 1 error(s), 0 warning(s)

ISSUES TO FIX:
----------------------------------------
❌ [ERROR] line 4: Missing ';' at 'System.debug' (source: apex)

ACTION REQUIRED:
Please fix the Apex syntax errors above and try again.
(Attempt 1/3)
============================================================
```

---

### Common LSP Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Missing ';' at ... | Statement not terminated | Add semicolon at end of line |
| Unexpected token ... | Syntax error | Check brackets, quotes, keywords |
| Unknown type ... | Class/type not found | Ensure class exists, check spelling |
| Method does not exist ... | Method call on wrong type | Verify method name and signature |
| Variable not found ... | Undeclared variable | Declare variable before use |

**Example Auto-Fix Loop:**

**Attempt 1 (ERROR):**
```apex
public class MyClass {
    public void doSomething() {
        System.debug('Hello')  // Missing semicolon
    }
}
```

**LSP Output:**
```
❌ [ERROR] line 3: Missing ';' at '}'
```

**Attempt 2 (SUCCESS):**
```apex
public class MyClass {
    public void doSomething() {
        System.debug('Hello');  // Fixed!
    }
}
```

**LSP Output:**
```
✅ VALIDATION PASSED
```

---

### Manual LSP Validation

**Run LSP validation manually from VS Code:**

1. Open Apex class in VS Code
2. View → Problems panel (`Cmd+Shift+M` / `Ctrl+Shift+M`)
3. See syntax errors highlighted in real-time

**Run from CLI (if available):**
```bash
# Apex compilation happens automatically during deploy (no standalone compile command)
sf project deploy start --metadata ApexClass:MyClass --target-org <alias> --dry-run --json
```

---

<a id="cross-skill-dependency-checklist"></a>

## Cross-Skill Dependency Checklist

**Before deploying Apex code, verify these prerequisites:**

| Prerequisite | Check Command | Required For |
|--------------|---------------|--------------|
| **TAF Package** | `sf package installed list --target-org alias` | TAF trigger pattern |
| **Custom Fields** | `sf sobject describe --sobject Lead --target-org alias` | Field references in code |
| **Permission Sets** | `sf org list metadata --metadata-type PermissionSet` | FLS for custom fields |
| **Trigger_Action__mdt** | Check Setup → Custom Metadata Types | TAF trigger execution |
| **Named Credentials** | Check Setup → Named Credentials | External callouts |
| **Custom Settings** | Check Setup → Custom Settings | Bypass flags, configuration |

---

### Common Deployment Order

```
1. sf-metadata: Create custom fields
   └─> sf schema generate field --object Lead --label "Score" (then edit XML for Number(3,0))

2. sf-metadata: Create Permission Sets
   └─> Grant FLS on custom fields

3. sf-deploy: Deploy fields + Permission Sets
   └─> sf project deploy start --metadata-dir force-app/main/default/objects

4. sf-apex: Deploy Apex classes/triggers
   └─> sf project deploy start --metadata-dir force-app/main/default/classes

5. sf-data: Create test data
   └─> sf data create record --sobject Account --values "Name='Test'"
```

---

### Verifying Prerequisites

**Check TAF Package:**
```bash
sf package installed list --target-org myorg --json
```

**Output:**
```json
{
  "result": [
    {
      "Id": "04t...",
      "SubscriberPackageName": "Trigger Actions Framework",
      "SubscriberPackageVersionNumber": "1.2.0"
    }
  ]
}
```

**If not installed:**
```bash
sf package install --package 04tKZ000000gUEFYA2 --target-org myorg --wait 10
```

---

**Check Custom Metadata Records:**
```bash
sf data query --query "SELECT DeveloperName, Object__c, Apex_Class_Name__c FROM Trigger_Action__mdt" --target-org myorg
```

**Expected Output:**
```
DeveloperName          Object__c  Apex_Class_Name__c
─────────────────────────────────────────────────────
TA_Account_SetDefaults  Account    TA_Account_SetDefaults
TA_Lead_CalculateScore  Lead       TA_Lead_CalculateScore
```

**If missing, create via sf-metadata skill.**

---

## Common Deployment Errors

### Error: "Field does not exist"

**Cause**: Apex references a custom field that doesn't exist in target org.

**Example:**
```
Error: Field Account.Custom_Field__c does not exist
```

**Fix:**
1. Verify field exists:
   ```bash
   sf sobject describe --sobject Account --target-org myorg | grep Custom_Field__c
   ```

2. Deploy field first:
   ```bash
   sf project deploy start --metadata CustomField:Account.Custom_Field__c --target-org myorg
   ```

3. Then deploy Apex

---

### Error: "Invalid type: TriggerAction"

**Cause**: TAF package not installed in target org.

**Example:**
```
Error: Invalid type: TriggerAction.BeforeInsert
```

**Fix:**
```bash
# Install TAF package
sf package install --package 04tKZ000000gUEFYA2 --target-org myorg --wait 10

# Verify
sf package installed list --target-org myorg
```

---

### Error: "Insufficient access rights"

**Cause**: Deploy user lacks permissions.

**Example:**
```
Error: Insufficient access rights on object id
```

**Fix:**
1. Verify user has "Modify All Data" or is System Administrator
2. Or add specific permissions to user's profile:
   ```bash
   sf org assign permset --name "Deploy_Permissions" --target-org myorg
   ```

---

### Error: "Test coverage less than 75%"

**Cause**: Production deployment requires 75% test coverage.

**Example:**
```
Error: Average test coverage across all Apex Classes and Triggers is 68%, at least 75% required
```

**Fix:**
1. Identify uncovered classes:
   ```bash
   sf apex run test --code-coverage --result-format human --target-org myorg
   ```

2. Add missing test classes

3. Ensure tests have assertions:
   ```apex
   Assert.areEqual(expected, actual, 'Message');
   ```

---

### Error: "FIELD_CUSTOM_VALIDATION_EXCEPTION"

**Cause**: Apex code violates validation rule.

**Example:**
```
Error: FIELD_CUSTOM_VALIDATION_EXCEPTION: Annual Revenue must be greater than 0
```

**Fix:**
1. Check validation rules:
   ```bash
   sf data query --query "SELECT ValidationName, ErrorDisplayField, ErrorMessage FROM ValidationRule WHERE EntityDefinition.QualifiedApiName = 'Account'" --target-org myorg
   ```

2. Update Apex to satisfy validation logic:
   ```apex
   acc.AnnualRevenue = 1000000;  // Ensure > 0
   ```

---

## Debug Logs and Monitoring

### Enable Debug Logs

**Via Setup:**
1. Setup → Debug Logs
2. Click "New"
3. Select User
4. Set expiration (max 24 hours)
5. Set log levels:
   - Apex Code: `DEBUG`
   - Database: `INFO`
   - Workflow: `INFO`

**Via CLI:**
```bash
# Create trace flag
sf data create record --sobject TraceFlag --values "StartDate=2025-01-01T00:00:00Z EndDate=2025-01-02T00:00:00Z LogType=USER_DEBUG TracedEntityId=<USER_ID> DebugLevelId=<DEBUG_LEVEL_ID>" --target-org myorg

# Tail logs in real-time
sf apex tail log --target-org myorg
```

---

### Reading Debug Logs

**Structure:**
```
HH:MM:SS.SSS|EXECUTION_STARTED
HH:MM:SS.SSS|CODE_UNIT_STARTED|AccountService
HH:MM:SS.SSS|USER_DEBUG|[3]|DEBUG|Processing account: Test
HH:MM:SS.SSS|SOQL_EXECUTE_BEGIN|[5]|SELECT Id FROM Account
HH:MM:SS.SSS|SOQL_EXECUTE_END|[5]|Rows:10
HH:MM:SS.SSS|DML_BEGIN|[8]|Op:Update|Type:Account|Rows:10
HH:MM:SS.SSS|DML_END|[8]
HH:MM:SS.SSS|LIMIT_USAGE_FOR_NS|(default)|SOQL:1/100|DML:1/150
HH:MM:SS.SSS|EXECUTION_FINISHED
```

**Key Events:**
- `USER_DEBUG`: Your `System.debug()` statements
- `SOQL_EXECUTE_*`: SOQL queries
- `DML_BEGIN/END`: DML operations
- `LIMIT_USAGE_FOR_NS`: Governor limit consumption

---

### Strategic Debug Statements

```apex
public static void processAccounts(List<Account> accounts) {
    System.debug(LoggingLevel.INFO, '=== START processAccounts ===');
    System.debug(LoggingLevel.INFO, 'Input size: ' + accounts.size());

    // Log limits BEFORE expensive operation
    System.debug('SOQL before: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());

    List<Contact> contacts = [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds];

    // Log limits AFTER
    System.debug('SOQL after: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
    System.debug('Contacts retrieved: ' + contacts.size());

    System.debug(LoggingLevel.INFO, '=== END processAccounts ===');
}
```

---

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `ERROR` | Critical failures | `System.debug(LoggingLevel.ERROR, 'DML failed: ' + e.getMessage())` |
| `WARN` | Potential issues | `System.debug(LoggingLevel.WARN, 'No contacts found for account')` |
| `INFO` | Key milestones | `System.debug(LoggingLevel.INFO, 'Processing 251 accounts')` |
| `DEBUG` | Detailed traces | `System.debug(LoggingLevel.DEBUG, 'Variable value: ' + var)` |
| `FINE`/`FINER`/`FINEST` | Very detailed | Rarely used |

---

## Governor Limit Debugging

### Monitoring Limits in Code

```apex
public static void expensiveOperation() {
    System.debug('=== LIMIT CHECK ===');
    System.debug('SOQL Queries: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
    System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
    System.debug('DML Rows: ' + Limits.getDmlRows() + '/' + Limits.getLimitDmlRows());
    System.debug('CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
    System.debug('Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
}
```

---

### Common Limit Exceptions

**SOQL Limit (100 queries):**
```
System.LimitException: Too many SOQL queries: 101
```

**Fix**: Query BEFORE loops, use Maps for lookups.

**DML Limit (150 statements):**
```
System.LimitException: Too many DML statements: 151
```

**Fix**: Collect records in List, DML AFTER loop.

**CPU Time Limit (10 seconds):**
```
System.LimitException: Maximum CPU time exceeded
```

**Fix**: Optimize loops, move expensive operations to async, reduce complexity.

**Heap Size Limit (6 MB):**
```
System.LimitException: Apex heap size too large
```

**Fix**: Process in batches, clear collections when done, avoid storing large objects in memory.

---

### Using Limits Class for Alerts

```apex
public static void monitoredOperation() {
    // Warn if approaching 80% of limit
    Integer queriesUsed = Limits.getQueries();
    Integer queriesLimit = Limits.getLimitQueries();

    if (queriesUsed > queriesLimit * 0.8) {
        System.debug(LoggingLevel.WARN, 'Approaching SOQL limit: ' + queriesUsed + '/' + queriesLimit);
    }

    // Expensive operation
    List<Account> accounts = [SELECT Id FROM Account];
}
```

---

## Test Failures

### Common Test Failure Patterns

**Pattern 1: No assertions**
```apex
@IsTest
static void testCreateAccount() {
    Account acc = new Account(Name = 'Test');
    insert acc;
    // PASSES even if logic is broken!
}
```

**Fix**: Add assertions
```apex
@IsTest
static void testCreateAccount() {
    Account acc = new Account(Name = 'Test', Industry = 'Tech');
    insert acc;

    Account inserted = [SELECT Id, Industry FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Tech', inserted.Industry, 'Industry should be set');
}
```

---

**Pattern 2: Order dependency**
```apex
@IsTest
static void test1() {
    insert new Account(Name = 'Shared');
}

@IsTest
static void test2() {
    // Assumes test1 ran first - BRITTLE!
    Account acc = [SELECT Id FROM Account WHERE Name = 'Shared'];
}
```

**Fix**: Use @TestSetup or create data in each test
```apex
@TestSetup
static void setup() {
    insert new Account(Name = 'Shared');
}

@IsTest
static void test2() {
    Account acc = [SELECT Id FROM Account WHERE Name = 'Shared'];  // Safe
}
```

---

**Pattern 3: Insufficient permissions**
```apex
@IsTest
static void testRestrictedUser() {
    User u = TestDataFactory.createStandardUser();

    System.runAs(u) {
        // Fails if user lacks permission
        insert new Account(Name = 'Test');
    }
}
```

**Fix**: Grant necessary permissions
```apex
@TestSetup
static void setup() {
    User u = TestDataFactory.createStandardUser();
    insert new PermissionSetAssignment(
        AssigneeId = u.Id,
        PermissionSetId = [SELECT Id FROM PermissionSet WHERE Name = 'Account_Create'].Id
    );
}
```

---

### Running Tests

**VS Code:**
1. Open test class
2. Click "Run Test" above `@IsTest` method
3. View results in Output panel

**CLI:**
```bash
# Run specific test class
sf apex run test --tests AccountServiceTest --result-format human --code-coverage --target-org myorg

# Run all tests
sf apex run test --test-level RunLocalTests --result-format human --code-coverage --target-org myorg

# Run tests and generate coverage report
sf apex run test --test-level RunLocalTests --code-coverage --result-format json --output-dir test-results --target-org myorg
```

**Output:**
```
Test Summary
════════════
Outcome              Passed
Tests Ran            12
Pass Rate            100%
Fail Rate            0%
Skip Rate            0%
Test Run Coverage    92%
Org Wide Coverage    85%
Test Execution Time  1234 ms

Coverage Warnings
═════════════════
AccountService.cls  Line 45 not covered by tests
```

---

## Debugging Strategies

### 1. Binary Search for Errors

When unsure where error occurs, add debug statements at midpoints:

```apex
public static void complexOperation() {
    System.debug('START');

    // Part 1
    List<Account> accounts = [SELECT Id FROM Account];
    System.debug('CHECKPOINT 1: Retrieved ' + accounts.size() + ' accounts');

    // Part 2
    for (Account acc : accounts) {
        acc.Industry = 'Tech';
    }
    System.debug('CHECKPOINT 2: Updated accounts');

    // Part 3
    update accounts;
    System.debug('CHECKPOINT 3: DML complete');

    System.debug('END');
}
```

Run and check logs to see which checkpoint fails.

---

### 2. Isolate in Anonymous Apex

**Execute in Developer Console:**
```apex
Account acc = new Account(Name = 'Debug Test', Industry = 'Tech');
insert acc;

System.debug('Account ID: ' + acc.Id);
System.debug('Industry: ' + acc.Industry);
```

Open Execute Anonymous Window (`Ctrl+E`), paste code, check logs.

---

### 3. Unit Test in Isolation

**Create minimal test case:**
```apex
@IsTest
static void debugIssue() {
    Account acc = new Account(Name = 'Test', AnnualRevenue = null);

    Test.startTest();
    AccountService.calculateScore(acc);  // Isolated method
    Test.stopTest();

    System.debug('Score: ' + acc.Score__c);
}
```

Easier to debug than full integration test.

---

## Reference

**Full Documentation**: See `references/` folder for comprehensive guides:
- `best-practices.md` - Debugging best practices
- `testing-patterns.md` - Test troubleshooting
- `code-review-checklist.md` - Quality checklist

**Back to Main**: [SKILL.md](../SKILL.md)
