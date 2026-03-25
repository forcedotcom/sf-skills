# Agentic Test-Fix Loop Implementation

## How It Works

When the agentic loop is enabled, the test-fix loop will:

1. **Run tests** and capture results
2. **Parse failures** to identify error type and location
3. **Read source files** (test class + class under test)
4. **Analyze root cause** using the failure analysis decision tree
5. **Generate fix** by invoking the generating-apex skill
6. **Re-run failing test** to verify fix
7. **Iterate** until passing or max attempts (3)

## Example Agentic Flow

```
User: "Run tests for AccountService with auto-fix enabled"

Claude:
1. sf apex run test --class-names AccountServiceTest --code-coverage --result-format json
2. Parse results: 1 failure - testBulkInsert line 45 NullPointerException
3. Read AccountServiceTest.cls (line 45 context)
4. Read AccountService.cls (trace the null reference)
5. Identify: Missing null check in AccountService.processAccounts()
6. generating-apex: Add null safety to AccountService.processAccounts()
7. Deploy fix
8. Re-run: sf apex run test --tests AccountServiceTest.testBulkInsert
9. ✅ Passing! Report success.
```

## Failure Analysis Decision Tree

| Error Type | Root Cause | Auto-Fix Strategy |
|------------|------------|-------------------|
| `System.AssertException` | Wrong expected value or logic bug | Analyze assertion, check if test or code is wrong |
| `System.NullPointerException` | Missing null check or test data | Add null safety or fix test data setup |
| `System.DmlException` | Validation rule, required field, trigger | Check org config, add required fields to test data |
| `System.LimitException` | Governor limit hit | Refactor to use bulkified patterns |
| `System.QueryException` | No rows returned | Add test data or adjust query |
| `System.TypeException` | Type mismatch | Fix type casting or data format |

## Auto-Fix Command

When the root cause is in production code, delegate to the `generating-apex` skill:

```
Fix failing test [TestClassName].[methodName] - Error: [error message]
```
