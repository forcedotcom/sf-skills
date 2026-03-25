# Performance Optimization for Apex Tests

Fast tests enable faster development. When test suites run quickly, developers refactor confidently. This guide covers techniques to dramatically reduce test execution time.

> **Source**: [James Simone - Writing Performant Apex Tests](https://www.jamessimone.net/blog/joys-of-apex/writing-performant-apex-tests/)

---

## Why Test Speed Matters

| Test Suite Duration | Impact |
|---------------------|--------|
| **< 5 minutes** | Developers run frequently, catch issues early |
| **5-30 minutes** | Developers run occasionally, issues slip through |
| **30+ minutes** | Developers avoid running, tests become stale |
| **Hours** | CI/CD bottleneck, blocked deployments |

The goal: **Sub-second unit tests**, with integration tests taking seconds, not minutes.

---

## Technique 1: Mock DML Operations

Database operations are the #1 cause of slow tests.

### The Numbers

| Operation | 10,000 Records | Notes |
|-----------|----------------|-------|
| Actual insert | ~50 seconds | Database round-trips |
| DML mocking | <1 second | In-memory only |
| **Improvement** | **~35x faster** | |

### Implementation

See `assets/dml-mock.cls` and `references/mocking-patterns.md` for complete implementation.

```apex
// ❌ SLOW: Actual database insert
List<Account> accounts = TestDataFactory.createAccounts(1000);
insert accounts;  // ~5 seconds

// ✅ FAST: Mock DML
DMLMock.reset();
AccountService service = new AccountService(new DMLMock());
service.createAccounts(accounts);  // <0.1 seconds
Assert.areEqual(1000, DMLMock.InsertedRecords.size());
```

---

## Technique 2: Mock SOQL Queries

Query execution adds overhead, especially with large result sets.

```apex
// ❌ SLOW: Actual query requiring test data setup
@TestSetup
static void setup() {
    List<Account> accounts = new List<Account>();
    for (Integer i = 0; i < 1000; i++) {
        accounts.add(new Account(Name = 'Test ' + i));
    }
    insert accounts;  // Slow
}

// ✅ FAST: Mock query results
AccountSelector.setMockResults(new List<Account>{
    new Account(Name = 'Mock 1'),
    new Account(Name = 'Mock 2')
});
List<Account> results = AccountSelector.getActiveAccounts();  // Instant
```

---

## Technique 3: Minimize @TestSetup

`@TestSetup` runs before every test method. Large setups compound execution time.

```apex
// ❌ SLOW: Heavy @TestSetup
@TestSetup
static void setup() {
    List<Account> accounts = TestDataFactory.createAccounts(100);
    insert accounts;
    List<Contact> contacts = TestDataFactory.createContacts(500, accounts);
    insert contacts;
    List<Opportunity> opps = TestDataFactory.createOpportunities(200, accounts);
    insert opps;
    // Total: 800 DML operations, runs before EACH test method
}

// ✅ FAST: Minimal @TestSetup, mock what you can
@TestSetup
static void setup() {
    // Only create what MUST exist in database
    Account parentAccount = new Account(Name = 'Required Parent');
    insert parentAccount;
}
```

---

## Technique 4: Choose Efficient Loop Constructs

Loop performance varies significantly with large iterations.

### Benchmark Results (10,000 iterations)

| Loop Type | Duration | Notes |
|-----------|----------|-------|
| While loop | ~0.4s | Fastest |
| Cached iterator | ~0.8s | Good alternative |
| For loop (index) | ~1.4s | Acceptable |
| Enhanced for loop | ~2.4s | Convenient but slower |
| Uncached iterator | CPU limit | Avoid |

### Recommendation

```apex
// ✅ PREFERRED: While loop for large iterations
Iterator<Account> iter = accounts.iterator();
while (iter.hasNext()) {
    Account acc = iter.next();
    // process
}

// ✅ ACCEPTABLE: Standard for loop
for (Integer i = 0; i < accounts.size(); i++) {
    Account acc = accounts[i];
    // process
}

// ⚠️ CONVENIENT BUT SLOWER: Enhanced for
for (Account acc : accounts) {
    // process
}
```

---

## Technique 5: Batch Test Data Creation

Creating records one-by-one is slow. Batch operations are faster.

```apex
// ❌ SLOW: One-by-one creation
for (Integer i = 0; i < 200; i++) {
    Account acc = new Account(Name = 'Test ' + i);
    insert acc;  // 200 DML statements!
}

// ✅ FAST: Batch creation
List<Account> accounts = new List<Account>();
for (Integer i = 0; i < 200; i++) {
    accounts.add(new Account(Name = 'Test ' + i));
}
insert accounts;  // 1 DML statement
```

---

## Technique 6: Avoid SOSL in Tests

SOSL searches return empty results in tests unless configured.

```apex
// ❌ PROBLEM: SOSL returns nothing in tests by default
List<List<SObject>> results = [FIND 'test' IN ALL FIELDS RETURNING Account];
// results[0] is EMPTY even with matching records!

// ✅ SOLUTION: Use Test.setFixedSearchResults()
@IsTest
static void testSearch() {
    Account acc = new Account(Name = 'Searchable');
    insert acc;

    // Configure what SOSL will return
    Test.setFixedSearchResults(new List<Id>{ acc.Id });

    Test.startTest();
    List<List<SObject>> results = [FIND 'test' IN ALL FIELDS RETURNING Account];
    Test.stopTest();

    Assert.areEqual(1, results[0].size(), 'Should find configured record');
}
```

---

## Technique 7: Strategic Test Method Scoping

Run only the tests you need during development.

```bash
# ❌ SLOW: Run all tests (minutes to hours)
sf apex run test --test-level RunLocalTests --target-org sandbox

# ✅ FAST: Run single test class
sf apex run test --class-names MyClassTest --target-org sandbox

# ✅ FASTER: Run single test method
sf apex run test --tests MyClassTest.testSpecificMethod --target-org sandbox
```

---

## Technique 8: Async Test Execution

Use async mode for large test suites to avoid blocking.

```bash
# Start tests asynchronously
sf apex run test --class-names MyClassTest --wait 0 --target-org sandbox
# Returns test run ID: 707xx0000000000

# Check status later
sf apex get test --test-run-id 707xx0000000000 --target-org sandbox
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| DML in loops | N operations instead of 1 | Bulk DML outside loops |
| Large @TestSetup | Runs before every test | Minimize or mock |
| No mocking | Full database round-trips | Mock DML, queries, callouts |
| SeeAllData=true | Depends on org data | Create test data |
| Deep nested loops | O(n²) or worse | Flatten with Maps |
| String concatenation in loops | New string objects each iteration | Use List and join |

---

## Optimization Checklist

Before committing tests, verify:

- [ ] DML operations are mocked where possible
- [ ] @TestSetup is minimal
- [ ] No SOQL/DML inside loops
- [ ] Uses bulk patterns (200+ records)
- [ ] Individual test methods run in <1 second
- [ ] Full test class runs in <10 seconds

---

## Performance Testing Your Tests

```apex
@IsTest
static void testPerformance() {
    Long startTime = System.currentTimeMillis();

    // Your test code here

    Long duration = System.currentTimeMillis() - startTime;
    System.debug('Test duration: ' + duration + 'ms');

    // Assert performance constraint
    Assert.isTrue(duration < 1000, 'Test should complete in <1 second, took: ' + duration + 'ms');
}
```
