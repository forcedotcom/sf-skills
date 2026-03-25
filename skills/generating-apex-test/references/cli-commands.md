# Salesforce CLI Test Commands Reference

## Quick Reference

| Task | Command |
|------|---------|
| Run single test class | `sf apex run test --class-names MyTest` |
| Run all local tests | `sf apex run test --test-level RunLocalTests` |
| Run with coverage | `sf apex run test --class-names MyTest --code-coverage` |
| Get JSON output | `sf apex run test --class-names MyTest --result-format json` |
| Run specific methods | `sf apex run test --tests MyTest.method1 --tests MyTest.method2` |

## Test Execution

### Run Single Test Class

```bash
sf apex run test \
  --class-names AccountServiceTest \
  --target-org my-sandbox \
  --code-coverage \
  --result-format human
```

### Run Multiple Test Classes

```bash
sf apex run test \
  --class-names AccountServiceTest \
  --class-names ContactServiceTest \
  --class-names LeadServiceTest \
  --target-org my-sandbox \
  --code-coverage
```

### Run Specific Test Methods

```bash
sf apex run test \
  --tests AccountServiceTest.testCreate \
  --tests AccountServiceTest.testUpdate \
  --target-org my-sandbox
```

### Run All Local Tests

```bash
sf apex run test \
  --test-level RunLocalTests \
  --target-org my-sandbox \
  --code-coverage \
  --output-dir test-results
```

### Run Test Suite

```bash
sf apex run test \
  --suite-names RegressionSuite \
  --target-org my-sandbox \
  --code-coverage
```

## Test Levels

| Level | Description |
|-------|-------------|
| `RunSpecifiedTests` | Only specified tests (default when using --class-names) |
| `RunLocalTests` | All tests except managed packages |
| `RunAllTestsInOrg` | All tests including managed packages |

## Output Formats

### Human Readable (Default)

```bash
sf apex run test --class-names MyTest --result-format human
```

### JSON (For Parsing)

```bash
sf apex run test --class-names MyTest --result-format json
```

### JUnit XML (For CI/CD)

```bash
sf apex run test --class-names MyTest --result-format junit
```

### TAP (Test Anything Protocol)

```bash
sf apex run test --class-names MyTest --result-format tap
```

## Code Coverage

### Basic Coverage

```bash
sf apex run test \
  --class-names MyTest \
  --code-coverage \
  --target-org my-sandbox
```

### Detailed Line-by-Line Coverage

```bash
sf apex run test \
  --class-names MyTest \
  --code-coverage \
  --detailed-coverage \
  --target-org my-sandbox
```

### Save Results to Directory

```bash
sf apex run test \
  --class-names MyTest \
  --code-coverage \
  --output-dir ./test-results \
  --target-org my-sandbox
```

Output files:
- `test-run-id.json` - Test results
- `test-run-id-codecoverage.json` - Coverage data

## Async Test Execution

### Run Tests Asynchronously

```bash
sf apex run test \
  --test-level RunLocalTests \
  --target-org my-sandbox \
  --async
```

Returns a test run ID for checking status later.

### Check Async Test Status

```bash
sf apex get test \
  --test-run-id 707xx0000000000AAA \
  --target-org my-sandbox
```

### Wait for Test Completion

```bash
sf apex run test \
  --test-level RunLocalTests \
  --target-org my-sandbox \
  --wait 10  # Wait up to 10 minutes
```

## Debug Logs During Tests

### Enable Debug Logs

```bash
# List current log levels
sf apex list log --target-org my-sandbox

# Tail logs in real-time
sf apex tail log --target-org my-sandbox --color
```

### Get Specific Log

```bash
sf apex get log \
  --log-id 07Lxx0000000000AAA \
  --target-org my-sandbox
```

## Useful Flags

| Flag | Description |
|------|-------------|
| `--code-coverage` | Include coverage in results |
| `--detailed-coverage` | Line-by-line coverage (slower) |
| `--result-format` | Output format (human, json, junit, tap) |
| `--output-dir` | Save results to directory |
| `--synchronous` | Wait for completion (default) |
| `--wait` | Max minutes to wait |
| `--async` | Return immediately with run ID |
| `--verbose` | Show additional details |
| `--concise` | Suppress passing test details (show only failures) |
| `--poll-interval <seconds>` | Customize polling interval (v2.116.6+) |

## Common Patterns

### Full Test Run with Coverage Report

```bash
sf apex run test \
  --test-level RunLocalTests \
  --code-coverage \
  --result-format json \
  --output-dir ./test-results \
  --target-org my-sandbox \
  --wait 30
```

### Quick Validation (Single Test)

```bash
sf apex run test \
  --tests AccountServiceTest.testCreate \
  --target-org my-sandbox
```

### CI/CD Pipeline Pattern

```bash
# Run tests with JUnit output for CI tools
sf apex run test \
  --test-level RunLocalTests \
  --result-format junit \
  --output-dir ./test-results \
  --code-coverage \
  --target-org ci-sandbox \
  --wait 60

# Check exit code
if [ $? -ne 0 ]; then
  echo "Tests failed!"
  exit 1
fi
```

### Coverage Validation

```bash
# Run tests and check minimum coverage
sf apex run test \
  --test-level RunLocalTests \
  --code-coverage \
  --result-format json \
  --output-dir ./test-results \
  --target-org my-sandbox

# Parse coverage from JSON (requires jq)
coverage=$(jq '.result.summary.orgWideCoverage' ./test-results/*.json | tr -d '"' | tr -d '%')
if [ "$coverage" -lt 75 ]; then
  echo "Coverage $coverage% is below 75% threshold!"
  exit 1
fi
```

## Troubleshooting

### Test Timeout

```bash
# Increase wait time for long-running tests
sf apex run test \
  --test-level RunAllTestsInOrg \
  --wait 120 \
  --target-org my-sandbox
```

### No Test Results

Check if tests exist:
```bash
sf data query --query "SELECT Id, Name FROM ApexClass WHERE Name LIKE '%Test%'" --target-org my-sandbox
```

### Permission Errors

Ensure user has "Author Apex" permission and API access.

### Async Test Not Completing

Check system status:
```bash
sf apex get test \
  --test-run-id 707xx0000000000AAA \
  --target-org my-sandbox
```
