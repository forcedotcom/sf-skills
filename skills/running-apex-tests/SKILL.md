---
name: running-apex-tests
description: "Apex test execution, coverage analysis, and test-fix loops with 120-point scoring. Use when the user needs to run Apex tests, check code coverage, fix failing tests, or work with *Test.cls / *_Test.cls files. TRIGGER when: user runs Apex tests, checks code coverage, fixes failing tests, or touches *Test.cls / *_Test.cls files. DO NOT TRIGGER when: writing Apex production code (use generating-apex), Agentforce agent testing (use sf-ai-agentforce-testing), or Jest/LWC tests (use generating-lwc-components)."
license: LICENSE.txt has complete terms
metadata:
  version: "1.1"
---

# running-apex-tests: Salesforce Test Execution & Coverage Analysis

Use this skill when the user needs **Apex test execution and failure analysis**: running tests, checking coverage, interpreting failures, improving coverage, and managing a disciplined test-fix loop for Salesforce code.

## When This Skill Owns the Task

Use `running-apex-tests` when the work involves:
- `sf apex run test` workflows
- Apex unit-test failures
- code coverage analysis
- identifying uncovered lines and missing test scenarios
- structured test-fix loops for Apex code

Delegate elsewhere when the user is:
- writing or refactoring production Apex → `generating-apex` skill
- testing Agentforce agents → `sf-ai-agentforce-testing` skill
- testing LWC with Jest → [generating-lwc-components](../generating-lwc-components/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- desired test scope: single class, specific methods, suite, or local tests
- coverage threshold expectation
- whether the user wants diagnosis only or a test-fix loop
- whether related test data factories already exist

---

## Recommended Workflow

### 1. Discover test scope
Identify:
- existing test classes
- target production classes
- test data factories / setup helpers

### 2. Run the smallest useful test set first
Start narrow when debugging a failure; widen only after the fix is stable.

### 3. Analyze results
Focus on:
- failing methods
- exception types and stack traces
- uncovered lines / weak coverage areas
- whether failures indicate bad test data, brittle assertions, or broken production logic

### 4. Run a disciplined fix loop
When the issue is code or test quality:
- delegate code fixes to `generating-apex` skill when needed
- add or improve tests
- rerun focused tests before broader regression

### 5. Improve coverage intentionally
Cover:
- positive path
- negative / exception path
- bulk path (251+ records where appropriate)
- callout or async path when relevant

---

## High-Signal Rules

| Rule | Rationale |
|------|-----------|
| Default to `SeeAllData=false` | Ensures test isolation; prevents reliance on org-specific data |
| Every test must assert meaningful outcomes | Tests with no assertions prove nothing and give false confidence |
| Test bulk behavior with 251+ records | Triggers process in batches of 200; 251 records crosses the boundary |
| Use factories / `@TestSetup` when they improve clarity | Consistent data creation in one place; rolled back between test methods |
| Pair `Test.startTest()` with `Test.stopTest()` for async | Ensures async operations (queueable, future) complete before assertions |
| Do not hide flaky org dependencies inside tests | Prevents intermittent failures tied to org state |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Test passes locally but fails in CI org | Check for `SeeAllData=true` or undeclared dependencies on org-specific records |
| Coverage drops unexpectedly after refactor | Run focused class-level tests first, then widen to `RunLocalTests` to confirm |
| "Uncommitted work pending" error in callout test | DML and HTTP callouts cannot be mixed in the same test context without `Test.startTest()` wrapping |
| Mock not taking effect in test | Ensure `Test.setMock()` is called before the code that makes the callout |
| `@TestSetup` data missing in test method | `@TestSetup` data is committed per test method — re-query it; do not store in static variables |

---

## Output Format

When finishing, report in this order:
1. **What tests were run**
2. **Pass/fail summary**
3. **Coverage result**
4. **Root-cause findings**
5. **Fix or next-run recommendation**

Suggested shape:

```text
Test run: <scope>
Org: <alias>
Result: <passed / partial / failed>
Coverage: <percent / key classes>
Issues: <highest-signal failures>
Next step: <fix class, add test, rerun scope, or widen regression>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|------|-------------|--------|
| Fix production code or author test classes | `generating-apex` skill | Code generation and repair |
| Create bulk / edge-case test data | [handling-sf-data](../handling-sf-data/SKILL.md) | Realistic test datasets |
| Deploy updated tests to org | [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) | Deployment workflows |
| Inspect detailed runtime logs | [debugging-apex-logs](../debugging-apex-logs/SKILL.md) | Deeper failure analysis |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cli-commands.md` | All `sf apex run test` command flags, output formats, async execution, and coverage commands |
| `references/test-patterns.md` | Test class templates — basic, bulk (251+), mock callout, and data factory patterns |
| `references/testing-best-practices.md` | Core testing principles — AAA pattern, naming conventions, bulk, negative, and mock strategies |
| `references/test-fix-loop.md` | Agentic test-fix loop implementation and failure analysis decision tree |
| `references/mocking-patterns.md` | HttpCalloutMock, DML mocking, StubProvider, and selector mocking patterns |
| `references/performance-optimization.md` | Techniques to reduce test execution time — DML mocking, SOQL mocking, loop optimizations |
| `assets/basic-test.cls` | Template: standard test class with `@TestSetup`, positive / negative / bulk / edge-case methods |
| `assets/bulk-test.cls` | Template: bulk test with 251+ records that crosses the 200-record trigger batch boundary |
| `assets/mock-callout-test.cls` | Template: HTTP callout mock using `HttpCalloutMock` |
| `assets/test-data-factory.cls` | Template: reusable `TestDataFactory` with create and insert helpers |
| `assets/dml-mock.cls` | Template: `IDML` interface + `DMLMock` implementation for database-free unit tests |
| `assets/stub-provider-example.cls` | Template: `StubProvider`-based dependency injection stub |
| `hooks/scripts/parse-test-results.py` | Post-tool hook — parses `sf apex run test` JSON output and formats failures for the auto-fix loop |

---

## Score Guide

| Score | Meaning |
|---|---|
| 108+ | strong production-grade test confidence |
| 96–107 | good test suite with minor gaps |
| 84–95 | acceptable but strengthen coverage / assertions |
| < 84 | below standard; revise before relying on it |
