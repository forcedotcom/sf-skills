<!-- Parent: generating-lwc-components/SKILL.md -->
# Salesforce CLI Commands for LWC Development

## Quick Reference

| Task | Command |
|------|---------|
| Create component | `sf template generate lightning component --name myComp --type lwc` |
| Create FlexiPage | `sf template generate flexipage --name MyPage --template DefaultAppPage` |
| Run all tests | `sf force lightning lwc test run` |
| Preview a component locally | `sf lightning dev component --target-org my-sandbox` |
| Preview an app locally | `sf lightning dev app --target-org my-sandbox` |
| Preview an Experience Cloud site locally | `sf lightning dev site --target-org my-sandbox` |
| Deploy component | `sf project deploy start --source-dir force-app/.../lwc/myComp` |
| Create message channel | Manual XML: `force-app/.../messageChannels/MyChannel.messageChannel-meta.xml` |

---

## Component Generation

### Create New LWC

```bash
# Basic component
sf template generate lightning component \
  --name accountList \
  --type lwc \
  --output-dir force-app/main/default/lwc

# Creates:
# force-app/main/default/lwc/accountList/
# ├── accountList.js
# ├── accountList.html
# └── accountList.js-meta.xml
```

### Generate with Jest Test

```bash
# The test file must be created manually in __tests__ folder
mkdir -p force-app/main/default/lwc/accountList/__tests__
touch force-app/main/default/lwc/accountList/__tests__/accountList.test.js
```

---

## Testing

### Run All Jest Tests

```bash
sf force lightning lwc test run
```

### Run Specific Test File

```bash
sf force lightning lwc test run \
  --spec force-app/main/default/lwc/accountList/__tests__/accountList.test.js
```

### Watch Mode (Development)

```bash
# Re-runs tests when files change
sf force lightning lwc test run --watch
```

### Coverage Report

```bash
# Generate HTML coverage report
sf force lightning lwc test run --coverage
# Report at: coverage/lcov-report/index.html
```

### Debug Tests

```bash
# Run with Node debugger
sf force lightning lwc test run --debug

# Then in Chrome: chrome://inspect
```

### Update Snapshots

```bash
sf force lightning lwc test run --update-snapshot
```

---

## Linting

### Run ESLint

> **Note**: `sf lightning lint` does not exist. Use `npx eslint` directly or `sf code-analyzer run`.

```bash
# Lint LWC files with ESLint (requires @salesforce/eslint-config-lwc)
npx eslint force-app/main/default/lwc

# Lint specific component
npx eslint force-app/main/default/lwc/accountList

# Auto-fix issues
npx eslint force-app/main/default/lwc --fix

# Or use Code Analyzer (includes ESLint + PMD + RetireJS)
sf code-analyzer run --workspace force-app/main/default/lwc
```

---

## Deployment

### Deploy Single Component

```bash
sf project deploy start \
  --source-dir force-app/main/default/lwc/accountList \
  --target-org my-sandbox
```

### Deploy Multiple Components

```bash
sf project deploy start \
  --source-dir force-app/main/default/lwc/accountList \
  --source-dir force-app/main/default/lwc/accountForm \
  --target-org my-sandbox
```

### Deploy with Related Apex

```bash
sf project deploy start \
  --source-dir force-app/main/default/lwc/accountList \
  --source-dir force-app/main/default/classes/AccountController.cls \
  --target-org my-sandbox
```

### Validate Without Deploying

```bash
sf project deploy start \
  --source-dir force-app/main/default/lwc \
  --target-org my-sandbox \
  --dry-run
```

---

## Retrieval

### Retrieve Component from Org

```bash
sf project retrieve start \
  --metadata LightningComponentBundle:accountList \
  --target-org my-sandbox \
  --output-dir force-app/main/default
```

### Retrieve All LWC

```bash
sf project retrieve start \
  --metadata LightningComponentBundle \
  --target-org my-sandbox
```

---

## Local Development

### Preview Components Locally

> **Note**: `sf lightning dev-server` was deprecated. In current SF CLI releases, Local Dev commands are installed just-in-time on first use via the Local Dev plugin.

```bash
# Preview an LWC component in isolation
sf lightning dev component --name myComp --target-org my-sandbox

# Launch component preview and choose the component interactively
sf lightning dev component --target-org my-sandbox

# Preview a Lightning Experience app locally
sf lightning dev app --target-org my-sandbox

# Preview an Experience Cloud site locally
sf lightning dev site --name "Partner Central" --target-org my-sandbox
```

These commands start long-running local preview sessions with hot reload. Use `sf project deploy start` for changes that Local Dev can't reflect automatically.

---

## Message Channels

### Create Message Channel

> **Note**: There is no `sf lightning generate messageChannel` command. Message Channels are created as metadata XML files manually.

```bash
# Create the directory if it doesn't exist
mkdir -p force-app/main/default/messageChannels

# Create the XML file manually:
# force-app/main/default/messageChannels/RecordSelected.messageChannel-meta.xml
```

### Deploy Message Channel

```bash
sf project deploy start \
  --metadata LightningMessageChannel:RecordSelected__c \
  --target-org my-sandbox
```

---

## Debugging

### Open Component in Browser

```bash
# Open Lightning App Builder
sf org open --target-org my-sandbox --path /lightning/setup/FlexiPageList/home
```

### View Debug Logs

```bash
# Tail logs while testing
sf apex tail log --target-org my-sandbox --color
```

### Check Deployment Errors

```bash
# If deployment fails, check status
sf project deploy report --job-id <job-id>
```

---

## Package Development

### Create Unlocked Package

```bash
# Create package
sf package create \
  --name "My LWC Package" \
  --package-type Unlocked \
  --path force-app

# Create version
sf package version create \
  --package "My LWC Package" \
  --installation-key test1234 \
  --wait 10
```

---

## Jest Configuration

### Setup Jest (if not already configured)

```bash
# Install Jest dependencies
npm install @salesforce/sfdx-lwc-jest --save-dev

# Add to package.json scripts
{
  "scripts": {
    "test:unit": "sfdx-lwc-jest",
    "test:unit:watch": "sfdx-lwc-jest --watch",
    "test:unit:debug": "sfdx-lwc-jest --debug",
    "test:unit:coverage": "sfdx-lwc-jest --coverage"
  }
}
```

### Jest Config (jest.config.js)

```javascript
const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    roots: ['<rootDir>/force-app'],
    modulePathIgnorePatterns: ['<rootDir>/.localdevserver'],
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
        '<rootDir>/.sfdx/',
        '<rootDir>/.agents/',
        '<rootDir>/.cursor/',
        '<rootDir>/.claude/',
        '<rootDir>/.pi/'
    ],
    testTimeout: 10000
};
```

If you copy example tests from `generating-lwc-components/assets/`, rename the `.example` file after placing it in your component's `__tests__` folder.

---

## Useful Patterns

### Deploy and Test Flow

```bash
# 1. Run local tests
sf force lightning lwc test run

# 2. Deploy to sandbox
sf project deploy start \
  --source-dir force-app/main/default/lwc/myComponent \
  --target-org my-sandbox

# 3. Open org to test
sf org open --target-org my-sandbox
```

### CI/CD Pipeline Pattern

```bash
#!/bin/bash

# Lint
npx eslint ./force-app/main/default/lwc || exit 1

# Test
sf force lightning lwc test run --coverage || exit 1

# Validate deployment
sf project deploy start \
  --source-dir force-app/main/default/lwc \
  --target-org ci-sandbox \
  --dry-run \
  --json || exit 1

# Deploy if validation passes
sf project deploy start \
  --source-dir force-app/main/default/lwc \
  --target-org ci-sandbox \
  --json
```

### Watch and Auto-Deploy

```bash
# Using nodemon or similar
npx nodemon \
  --watch "force-app/main/default/lwc/**/*" \
  --exec "sf project deploy start --source-dir force-app/main/default/lwc --target-org my-sandbox"
```

---

## Troubleshooting

### Component Not Visible in App Builder

1. Check `isExposed` is `true` in meta.xml
2. Check `targets` include the desired location
3. Verify deployment was successful

```bash
# Re-deploy with verbose output
sf project deploy start \
  --source-dir force-app/main/default/lwc/myComponent \
  --target-org my-sandbox \
  --verbose
```

### Jest Tests Not Finding Component

If Jest reports errors from `.agents/`, `.cursor/`, `.claude/`, or `.pi/`, it is discovering files outside your real Salesforce source tree. Scope Jest to `force-app` and ignore agent folders.

```bash
# Clear Jest cache
npx jest --clearCache

# Re-run tests
sf force lightning lwc test run
```

### Wire Service Not Working

1. Verify `cacheable=true` on Apex method
2. Check reactive parameter has `$` prefix
3. Verify Apex method is accessible

```bash
# Test Apex method directly
sf apex run --target-org my-sandbox <<< "System.debug(MyController.getRecords());"
```

### Deployment Conflicts

```bash
# Check what's different
sf project retrieve start \
  --metadata LightningComponentBundle:myComponent \
  --target-org my-sandbox \
  --output-dir temp-retrieve

# Compare and resolve
diff -r force-app/main/default/lwc/myComponent temp-retrieve/force-app/.../myComponent
```

---

## Static Analysis (Code Analyzer v5)

### Salesforce Code Analyzer

Code Analyzer v5 (`@salesforce/plugin-code-analyzer`) validates LWC files for SLDS 2 compliance, accessibility, and security.

```bash
# Install Code Analyzer v5 plugin
sf plugins install @salesforce/plugin-code-analyzer

# Run scan on LWC components
sf code-analyzer run \
  --workspace force-app/main/default/lwc \
  --output-file lwc-scan-results.html

# Run with specific rules
sf code-analyzer run \
  --workspace force-app/main/default/lwc \
  --rule-selector "Category:Best Practices,Security"
```

> **Migration from sfdx-scanner**: v5 uses `--workspace` instead of `--target`, `--output-file` instead of `--outfile` (format inferred from extension), `--view` for table/detail display, and `--rule-selector` instead of `--engine`/`--category`.

### SLDS 2 Compliance Checks

```bash
# Check for hardcoded colors (breaks dark mode)
rg -n '#[0-9A-Fa-f]{3,8}' force-app/main/default/lwc/**/*.css

# Find deprecated SLDS 1 tokens
rg -n '\-\-lwc\-' force-app/main/default/lwc/**/*.css

# Find missing alternative-text on icons
rg -n '<lightning-icon' force-app/main/default/lwc/**/*.html | \
  rg -v 'alternative-text'

# Check for !important overrides
rg -n '!important' force-app/main/default/lwc/**/*.css
```

### Dark Mode Validation

```bash
# Find all hardcoded colors that may break dark mode
rg -n 'rgb\(|rgba\(|#[0-9A-Fa-f]{3,8}' \
  force-app/main/default/lwc/**/*.css \
  --glob '!**/node_modules/**'

# Verify CSS variables usage (SLDS 2 global hooks)
rg -n '\-\-slds-g-color' force-app/main/default/lwc/**/*.css
```

---

## GraphQL Debugging

### GraphQL Wire Service

```bash
# View GraphQL queries in debug mode (enable in Setup → Debug Logs)
sf apex tail log --target-org my-sandbox --color
# Note: Debug levels are configured via TraceFlag records in Setup, not CLI flags

# Test GraphQL query via Anonymous Apex (for syntax validation)
sf apex run --target-org my-sandbox <<'EOF'
// GraphQL syntax can't be tested directly in Apex
// But you can verify field access:
System.debug([SELECT Id, Name FROM Account LIMIT 1]);
EOF
```

### GraphQL Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| "Field not found" | FLS restriction | Check user has read access |
| "Object not supported" | GraphQL scope | Not all objects support GraphQL |
| Cursor pagination fails | Invalid cursor | Use exact cursor from `pageInfo.endCursor` |
| Null data | Query error | Check `errors` array in wire result |

### Monitor GraphQL Performance

```bash
# Open Developer Console for network inspection
sf org open --target-org my-sandbox \
  --path /lightning/setup/ApexDebugLogDetail/home

# View Event Monitoring logs (if enabled)
sf data query \
  --query "SELECT EventType, LogDate FROM EventLogFile WHERE EventType='LightningPageView' ORDER BY LogDate DESC LIMIT 5" \
  --target-org my-sandbox
```

---

## Workspace API (Console Apps)

### Console Detection

```bash
# Check if an app is a Console app
sf data query \
  --query "SELECT DeveloperName, NavType FROM AppDefinition WHERE NavType='Console'" \
  --target-org my-sandbox

# List all Lightning Apps
sf data query \
  --query "SELECT DeveloperName, NavType, Label FROM AppDefinition ORDER BY Label" \
  --target-org my-sandbox
```

### Console App Testing

```bash
# Open Service Console
sf org open --target-org my-sandbox \
  --path /lightning/app/standard__ServiceConsole

# Open Sales Console
sf org open --target-org my-sandbox \
  --path /lightning/app/standard__SalesConsole

# Open custom console app
sf org open --target-org my-sandbox \
  --path /lightning/app/c__MyConsoleApp
```
