# Failure Categories & Improvement Mapping

## Inputs required per failed test

- Test method name
- Failure message (the assertion error or exception text)
- Failure category (assertion failure, unhandled exception, timeout, compile error)

## Category table

| Category | Description |
|---|---|
| **Assertion failure** | A test assertion failed (expected vs actual mismatch) |
| **Exception** | An unhandled exception was thrown |
| **Code Analyzer violation** | A static analysis rule was violated (e.g. `ApexCRUDViolation`, `ApexSharingViolations`) |
| **Timeout** | Test exceeded execution time limit |
| **Compile error** | Class failed to compile |

## Per-failure extraction (Part 1)

For each failure, extract and translate to plain language:
- Offending file and class name
- Method name
- Line number
- What rule or assertion was violated, in plain language
- Suggested fix direction (without writing code)

Group failures by category if more than one.

## Failure-pattern → improvement suggestion (Part 2)

Reason over the failure message to identify the root-cause pattern:

| Failure pattern | Improvement suggestion |
|---|---|
| `NullPointerException` | The test is not handling null input — add a null check or a test setup that ensures the data exists |
| `Assertion failed: expected X but was Y` | The expected value in the assertion is wrong or the test data setup does not produce the right state |
| `List has no rows for assignment` | The test is querying for data that doesn't exist — test setup is incomplete |
| `System.LimitException: Too many SOQL queries` | The test is hitting governor limits — the code under test or test setup is making too many queries |
| `Insufficient access rights on cross-reference id` | The test user lacks permissions — run as a user with the appropriate profile/permission set |
| `DML currently not allowed` | The test is performing DML inside a method called from a context that doesn't allow it |
| Code Analyzer violation message | The production code violates a specific rule — the test exposed it, but the fix is in production code, not the test |

## Producing actionable suggestions

For each failure describe, in plain language:
- What the failure reveals about what the test is not handling
- What specifically should be added or changed to make the test robust
- Whether the fix is in the **test** (assertion, setup, permissions) or in **production code** (test is correct, code under test is broken)

Do not rewrite the test — only describe what needs to change and why.

## Test fix vs. production-code fix

- **Fix location: Production code** — a code defect exposed by a sound test. Should NOT block suite promotion on test-quality grounds; track separately as a production defect.
- **Fix location: Test** — the test needs hardening: missing setup, wrong assertions, inadequate coverage of edge cases (null inputs, bulk record volumes, mixed permission contexts, governor-limit boundaries).

## Output formats

**Part 1 — failure summary:**

```text
Test failure summary:

<N> failure(s) found:

1. [<Category>] `<ClassName>.cls` — `<methodName>()` at line <N>
   What happened: <plain-language description>
   Rule violated: <ruleName or assertion description>
   Fix direction: <plain-language suggestion>
```

**Part 2 — improvement suggestions:**

```text
Test improvement suggestions based on execution results:

`<testMethodName>()` — [Assertion Failure / Exception / etc.]
Failure: "<failure message>"
What this reveals: <plain-language explanation>
Suggestion: <specific, actionable recommendation>
Fix location: Test | Production code

Overall: <N> improvement(s) across <M> failed test(s).
```
