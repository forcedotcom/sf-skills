---
name: analyzing-test-failures
description: "Parses a DevOps Center test-failure or Code Analyzer violation payload and explains it in plain language — failure category, offending file/class/method/line, rule violated, and fix direction — then gives prioritized test-improvement suggestions (distinguishing test-code from production-code fixes). Pure reasoning: no system calls or code authoring. TRIGGER when: a test run failed and the user wants root cause; a quality gate failure needs explaining; Code Analyzer violations need translating to plain language; the user shares a failure payload and asks how to address it; tests keep failing and the user wants suggestions; or the user wants to close coverage gaps, strengthen assertions, or fix flaky/weak tests. DO NOT TRIGGER when: the user wants fix code written (use platform-apex-generate) or new test classes authored (use platform-apex-test-generate)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
---

# analyzing-test-failures

**Type:** Pure reasoning — no system calls, no code authoring.

**What it does:** Parses a test failure or Code Analyzer violation payload and produces a plain-language explanation, then follows up with concrete, prioritized improvement suggestions per failed test — including whether each fix belongs in the test or in production code. Never exposes raw JSON, stack traces, or API error bodies to the user.

---

## Prerequisites

If you need to fetch the failure payload yourself rather than receiving it, load `checking-devops-prerequisites` first, then use `polling-test-results` to obtain the execution result. If the payload is already in context, no prerequisites are needed — this is pure reasoning.

---

## Inputs

- JSON failure payload provided by the `polling-test-results` skill, or pasted directly into context from a test run or Code Analyzer execution. Specifically required per failed test:
  - Test method name
  - Failure message (the assertion error or exception text)
  - Failure category (assertion failure, unhandled exception, timeout, compile error)

---

## Empty-org / no-data case

If the payload contains no failures or violations, report that clearly (e.g. "No failures found in the provided execution results.") and stop. Do NOT fabricate failures, violations, or improvement suggestions when none are present.

---

## Reasoning steps

1. Determine the failure category:

   | Category | Description |
   |---|---|
   | **Assertion failure** | A test assertion failed (expected vs actual mismatch) |
   | **Exception** | An unhandled exception was thrown |
   | **Code Analyzer violation** | A static analysis rule was violated (e.g. `ApexCRUDViolation`, `ApexSharingViolations`) |
   | **Timeout** | Test exceeded execution time limit |
   | **Compile error** | Class failed to compile |

2. For each failure, extract and translate to plain language:
   - Offending file and class name
   - Method name
   - Line number
   - What rule or assertion was violated, in plain language
   - Suggested fix direction (without writing code)

3. Group failures by category if more than one.

---

## Output format

```text
Test failure summary:

<N> failure(s) found:

1. [<Category>] `<ClassName>.cls` — `<methodName>()` at line <N>
   What happened: <plain-language description>
   Rule violated: <ruleName or assertion description>
   Fix direction: <plain-language suggestion>

2. [<Category>] `<ClassName2>.cls` — `<methodName2>()` at line <N>
   ...
```

---

## Code Analyzer violations

For violations, always include:
- The rule name translated to plain English (e.g. "ApexCRUDViolation" → "A SOQL query was made without checking object-level permissions first")
- The exact line number
- The fix direction (e.g. "Add a `Schema.sObjectType.Account.isAccessible()` check before the query")

---

## Plain-language rule

Never paste raw stack traces, JSON payloads, or internal Salesforce error codes into the output. Always translate to file name, method, line, and plain description.

---

## Suggesting improvements

Invoke this section **after test execution completes with failures**, not on static source code. The failure message is the primary signal — it describes what the test expected vs. what actually happened, which directly informs what the test needs to handle better.

### 1 — Read each failure message

For each failed test in the execution result, extract:
- Test method name
- Failure message (the assertion error or exception message)
- Failure category (assertion failure, unhandled exception, timeout, compile error)

### 2 — Infer what the test is not handling

Reason over the failure message to identify the root cause pattern:

| Failure pattern | Improvement suggestion |
|---|---|
| `NullPointerException` | The test is not handling null input — add a null check or a test setup that ensures the data exists |
| `Assertion failed: expected X but was Y` | The expected value in the assertion is wrong or the test data setup does not produce the right state |
| `List has no rows for assignment` | The test is querying for data that doesn't exist — test setup is incomplete |
| `System.LimitException: Too many SOQL queries` | The test is hitting governor limits — the code under test or test setup is making too many queries |
| `Insufficient access rights on cross-reference id` | The test user lacks the required permissions — the test needs to run as a user with appropriate profile/permission set |
| `DML currently not allowed` | The test is performing DML inside a method called from a context that doesn't allow it |
| Code Analyzer violation message | The production code violates a specific rule — the test exposed it but the fix is in the production code, not the test |

### 3 — Produce actionable suggestions

For each failure, describe in plain language:
- What the failure reveals about what the test is not handling
- What specifically should be added or changed to make the test robust
- Whether the fix is in the **test** (assertion, setup, permissions) or in the **production code** (the test is correct but the code under test is broken)

Do not rewrite the test. Only describe what needs to change and why.

### Output format for improvements

```text
Test improvement suggestions based on execution results:

`<testMethodName>()` — [Assertion Failure / Exception / etc.]
Failure: "<failure message>"
What this reveals: <plain-language explanation>
Suggestion: <specific, actionable recommendation>
Fix location: Test | Production code

`<testMethodName2>()` — [NullPointerException]
Failure: "Attempt to de-reference a null object"
What this reveals: The test is calling the method without setting up the required input data
Suggestion: Add test data setup for <object/field> before calling the method
Fix location: Test

Overall: <N> improvement(s) across <M> failed test(s).
```

### Test fix vs. production-code fix

Suggestions flagged as **Fix location: Production code** indicate a code defect exposed by the test — the test logic itself is sound. These should not block suite promotion on the grounds of test quality; they should be tracked separately as production defects.

Suggestions flagged as **Fix location: Test** indicate the test needs to be hardened — missing setup, wrong assertions, inadequate coverage of edge cases (null inputs, bulk record volumes, mixed permission contexts, governor-limit boundaries).

---

## Related skills

- **`polling-test-results`** — obtains the failure payload that feeds into this skill.
- **`creating-fix-work-item`** — use to create a tracked fix item from the analysis output or to track an approved improvement suggestion as a work item once the user decides to act on it.
