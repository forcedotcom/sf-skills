# running-apex-tests

Comprehensive Salesforce testing skill with test execution, code coverage analysis, and agentic test-fix loops. Run tests, analyze coverage, and automatically fix failing tests.

## Features

- **Test Execution**: Run Apex tests via sf CLI with coverage analysis
- **Coverage Analysis**: Parse reports, identify untested code paths
- **Failure Analysis**: Parse failures, identify root causes, suggest fixes
- **Agentic Test-Fix Loop**: Automatically fix failing tests and re-run
- **120-Point Scoring**: Validation across 6 categories
- **Bulk Testing**: Validate with 251+ records for governor limits

## Quick Start

### 1. Invoke the skill

```
Skill: running-apex-tests
Request: "Run all tests and show coverage report for org dev"
```

### 2. Common operations

| Operation | Example Request |
|-----------|-----------------|
| Run class | "Run AccountServiceTest in org dev" |
| Run all | "Run all local tests with coverage" |
| Coverage report | "Show code coverage for AccountService" |
| Fix loop | "Run tests and fix failures automatically" |
| Generate tests | "Create tests for AccountService class" |

## Key Commands

```bash
# Run single test class
sf apex run test --class-names MyClassTest --code-coverage --result-format json --target-org [alias]

# Run all local tests
sf apex run test --test-level RunLocalTests --code-coverage --result-format json --target-org [alias]

# Run specific methods
sf apex run test --tests MyClassTest.testMethod1 --target-org [alias]

# Run with output directory
sf apex run test --class-names MyClassTest --output-dir test-results --target-org [alias]
```

## Scoring System (120 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Coverage | 25 | Overall and per-class coverage |
| Assertions | 25 | Meaningful assertions, edge cases |
| Bulk Testing | 20 | 251+ records, governor limits |
| Data Isolation | 20 | @TestSetup, test data factories |
| Negative Tests | 15 | Error paths, exceptions |
| Documentation | 15 | Test descriptions, clear naming |

## Test Thresholds

| Level | Coverage | Purpose |
|-------|----------|---------|
| Production | 75% minimum | Required for deployment |
| Recommended | 90%+ | Best practice target |
| Critical paths | 100% | Business-critical code |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| sf-apex | Fix failing Apex code |
| debugging-apex-logs | Analyze test failures with debug logs |
| handling-sf-data | Generate 251+ bulk test records |
| deploying-sf-metadata | Validate before deployment |

## Agentic Test-Fix Loop

When enabled, the skill will:
1. Run tests and capture failures
2. Analyze error messages and stack traces
3. Generate fixes for common issues
4. Apply fixes and re-run tests
5. Repeat until all tests pass or max iterations reached

## Documentation

- [Testing Best Practices](references/testing-best-practices.md)

## Requirements

- sf CLI v2
- Target Salesforce org
- Test classes in org or local project

## License

MIT License. See LICENSE file.
