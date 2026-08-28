# Sa11y Accessibility Test Instructions

## Environment Detection

Choose the approach based on your environment:

- **Core Build Environment** — contains a `WORKSPACE` file, uses Bazel build system.
- **Standalone Environment** — no `WORKSPACE` file, uses npm/yarn scripts.

If this is not a Salesforce core build environment, do not mention anything about the core build environment.

---

## Core Build Environment (Bazel)

When working within a Salesforce core build environment, use Bazel commands.

### Base Command Structure

```bash
{coreRootPath}/tools/bazel test [TARGET] --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

**Replacements:**

- `{coreRootPath}` — your actual core root directory path
- `{moduleName}` — module name (e.g. `ui-content-authoring-components`)
- `{relativePath}` — test file path **without** `.test.js` extension

### Testing Approaches

#### 1. Single File Testing

```bash
{coreRootPath}/tools/bazel test //{moduleName}:{relativePath} --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

Example:

```bash
./core/tools/bazel test //ui-content-authoring-components:modules/es_block_builder/blockBuilder/__tests__/blockBuilder --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

**Use when:** testing a specific component with a known test file path.

#### 2. Module Testing

```bash
{coreRootPath}/tools/bazel test //{moduleName}:sa11y_jest_test --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

Example:

```bash
./core/tools/bazel test //ui-content-authoring-components:sa11y_jest_test --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

**Use when:** testing an entire module or when unsure which specific component to target.

#### 3. Multiple Modules

```bash
{coreRootPath}/tools/bazel test //{module1}:sa11y_jest_test //{module2}:sa11y_jest_test --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

**Use when:** integration testing across module boundaries.

#### 4. Wildcard Testing

```bash
{coreRootPath}/tools/bazel test //{moduleName}:sa11y_jest_test --test_arg=--testMatch="**/{modulePath}/**" --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

**Use when:** filtering multiple components within a module by pattern.

---

## Standalone Environment (Direct Jest)

No `SA11Y_*` environment variables are needed here — `@sa11y/jest` is wired into
the project's Jest setup, so the accessibility assertions run automatically.

```bash
# Run all accessibility tests (match by the *.accessibility.test.js convention)
npm test -- --testMatch="**/*.accessibility.test.js"

# Re-run a single test file — use the filename/path as given in the prompt
# (a bare filename when the file is "in this directory")
npm test -- myComponent.accessibility.test.js
```

### Jest Configuration

Ensure Jest includes Sa11y setup:

```javascript
// jest.config.js
module.exports = {
  setupFilesAfterEnv: ['<rootDir>/test/setup/sa11y-setup.js'],
  testEnvironment: 'jsdom',
};
```

### Sa11y Setup File

```javascript
// test/setup/sa11y-setup.js
import { configure } from '@sa11y/jest';

configure({
  rules: ['wcag2a', 'wcag2aa', 'wcag2aaa'],
});
```

---

## Path Discovery (Core Build Environment)

```bash
# Find all test files in a module
find {coreRootPath}/ui-content-authoring-components -name "*.test.js" -type f

# Explore module structure
ls {coreRootPath}/ui-content-authoring-components/modules/

# Use Bazel to list test targets
{coreRootPath}/tools/bazel query "tests(//ui-content-authoring-components:*)"
```

### Path Construction

- **Module Name** — use directly (e.g. `ui-content-authoring-components`)
- **Component Path** — `modules/{componentDir}/{componentName}/__tests__/`
- **Test File** — remove `.test.js` extension

---

## Optional Arguments

### Bazel Options

| Option           | Command                                                                                                                           | Purpose                    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| Update Snapshots | `--test_arg="--updateSnapshot"`                                                                                                   | Update test snapshots      |
| Disable Cache    | `--cache_test_results=no`                                                                                                         | Disable Bazel test caching |
| Save HTML Files  | `--test_env=SA11Y_ENABLE_RENDERED_DOM_SAVE=1 --test_env=SA11Y_RENDERED_DOM_SAVE_PATH=sfdc-test/unit/javascript/htdocs/sa11y/jest` | Save HTML for analysis     |

**Note:** Use `sfdc-test/unit/javascript/htdocs/sa11y/jest` as the save path to avoid EPERM permission issues.

**Complete example with HTML saving:**

```bash
./core/tools/bazel test //ui-content-authoring-components:modules/es_block_builder/blockBuilder/__tests__/blockBuilder \
  --test_output=streamed \
  --test_env=SA11Y_AUTO=1 \
  --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1 \
  --test_env=SA11Y_ENABLE_RENDERED_DOM_SAVE=1 \
  --test_env=SA11Y_RENDERED_DOM_SAVE_PATH=sfdc-test/unit/javascript/htdocs/sa11y/jest
```

### Jest Options

```bash
# Update snapshots
npm test -- --testMatch="**/*.accessibility.test.js" --updateSnapshot

# Run in watch mode
npm test -- --testMatch="**/*.accessibility.test.js" --watch

# Run with verbose output
npm test -- --testMatch="**/*.accessibility.test.js" --verbose
```

---

## Expected Exit Codes

### Bazel

- **0** — all tests passed
- **3** — build succeeded, some tests failed
- **1** — build or command failed

### Jest

- **0** — all tests passed
- **1** — some tests failed or error occurred

---

## Troubleshooting

### Bazel

- Verify `WORKSPACE` file exists
- Check Bazel version compatibility
- Ensure test targets are properly defined
- Verify repository-specific Bazel binary path

### Jest

- Verify Jest configuration
- Check test file naming conventions
- Ensure Sa11y dependencies are installed
- Verify jsdom environment setup
