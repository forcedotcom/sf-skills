---
name: experience-lwc-accessibility-jest-run
description: "Use ALWAYS when running Sa11y accessibility Jest tests for an LWC — locally before pushing, producing the command(s), running one file vs a suite, selecting tests by naming convention, saving Sa11y-rendered HTML, or reproducing a Sa11y/A11yBug failure. Covers core (Bazel; `bazel test //<module>:<target>`) and standalone `npx jest` (`.accessibility.test.js`, `@sa11y/jest`). REQUIRED for a `run-plan.md`, a failing a11y test's exit code, or `SA11Y_*`/`A11yBug`/core-Bazel test paths. DO NOT TRIGGER for functional Jest tests, a11y review without running tests (use experience-accessibility-validate), or Selenium-based a11y tests."
metadata:
  version: "1.0"
  domains: ["Experience"]
  relatedSkills:
    - "experience-accessibility-validate"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=8.0"
---
<!-- a11y-expert-managed-skill -->

# Accessibility Unit Testing

Run Sa11y accessibility unit tests on Lightning Web Components in either:

- **Core (Bazel)** — when a `WORKSPACE` file is present.
- **Standalone (Jest)** — when there's no `WORKSPACE`.

Selenium-level reproductions, GUS A11yBug ingestion, and other internal
Salesforce-only flows are out of scope for this skill. For source-code-level
WCAG review without running tests, see `experience-accessibility-validate`.

## When to Use This Skill

- User wants to run accessibility unit tests (Sa11y Jest) locally before
  pushing a fix.
- User has a known failing test file path (e.g. from an A11yBug's
  `Test_Names__c`) and wants to target it directly.
- User is iterating on an accessibility fix and needs the fastest
  pass/fail signal.

## Prerequisites

- For Bazel Jest tests: a Salesforce core build environment (a `WORKSPACE`
  file is present).
- For standalone Jest tests: `@sa11y/jest` installed and configured.


## Workflow

Choose the approach based on the environment. If this is not a Salesforce core
build environment, do not mention the Core workflow.

For Core workspaces, discover an active `salesforce-core-dev` installation from
this host's plugin/skill inventory and declared installation metadata. Read its
component-testing guidance from that installation root; do not hard-code plugin
cache paths or assume a cached version is active. Use supported guidance for
Core workspace setup and test discovery. Core Dev has no dedicated Jest runner:
retain the direct Bazel commands below and **both** accessibility flags. If Core
Dev is unavailable, use the same direct Bazel workflow. Standalone Jest does not
require Core Dev.

### Core (Bazel)

Use this mode when a `WORKSPACE` file is present. Run from the Core workspace
root. The base command is:

```bash
"{coreRootPath}/tools/bazel" test [TARGET] --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

Replace `{coreRootPath}` with the Core repository root, `{moduleName}` with the
module name, and `{relativePath}` with the test file path without the `.test.js`
extension.

To discover targets and paths:

```bash
find {coreRootPath}/{moduleName} -name "*.test.js" -type f
"{coreRootPath}/tools/bazel" query "tests(//{moduleName}:*)"
```

Component tests typically live under
`modules/{componentDir}/{componentName}/__tests__/`.

Prefer a single-file target when the failing test path is known:

```bash
"{coreRootPath}/tools/bazel" test //{moduleName}:{relativePath} --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

Run all Sa11y Jest tests in a module when a specific test is not known:

```bash
"{coreRootPath}/tools/bazel" test //{moduleName}:sa11y_jest_test --test_output=streamed --test_env=SA11Y_AUTO=1 --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1
```

Multiple module targets can be passed to the same command. To filter tests
within a module, add `--test_arg=--testMatch="**/{modulePath}/**"`.

Useful options:

- Update snapshots: `--test_arg="--updateSnapshot"`
- Disable cached test results: `--cache_test_results=no`
- Save rendered HTML:
  `--test_env=SA11Y_ENABLE_RENDERED_DOM_SAVE=1 --test_env=SA11Y_RENDERED_DOM_SAVE_PATH=sfdc-test/unit/javascript/htdocs/sa11y/jest`

Use `sfdc-test/unit/javascript/htdocs/sa11y/jest` as the rendered DOM save path
to avoid EPERM errors.

### Standalone (Jest)

Use this mode when no `WORKSPACE` file is present. Run all accessibility tests:

Do **not** prepend `SA11Y_*` environment variables in standalone mode;
`@sa11y/jest` is activated through the project's Jest setup.

```bash
npm test -- --testMatch="**/*.accessibility.test.js"
```

Or target a specific file:

```bash
npm test -- src/components/MyComponent/__tests__/MyComponent.accessibility.test.js
```

Use the filename or path supplied by the user. When the named test is in the
current directory, keep a bare filename bare instead of inventing a path.

Other useful options are `--coverage`, `--updateSnapshot`, `--watch`, and
`--verbose`. To target a named test, use
`npm test -- --testNamePattern="MyComponent accessibility"`.

Ensure Jest uses a `jsdom` environment and loads the project's `@sa11y/jest`
setup file. Copy or adapt the bundled `assets/jest.config.js` template into
the project's Jest configuration, and copy `assets/sa11y-jest-setup.js` to
`test/setup/sa11y-setup.js`. If the project already has a Jest configuration,
merge the relevant settings instead of overwriting unrelated configuration.

The `SA11Y_*` variables shown above are for Core/Bazel only; the Bazel commands
already include them.

## Response Scope

Answer only what the user asked. Emit the requested command or commands plus
the relevant exit-code meaning. Do not add watch, coverage, snapshot-update,
HTML-save, or other variants unless the user requests them.

## Expected Exit Codes

- Bazel: `0` means all tests passed, `3` means tests failed, and `1` means the
  build or command failed.
- Jest: `0` means all tests passed and `1` means tests failed or an error
  occurred.


## Verification Checklist

- [ ] Sa11y Jest run completed with a clear pass/fail signal (exit 0 or 3
      for Bazel; exit 0 or 1 for Jest).
- [ ] If snapshots were intentionally updated, the new snapshots are
      committed alongside the fix.


## Troubleshooting

- **Bazel test "not found"** — the target path is off. Remember to drop the
  `.test.js` extension in `{relativePath}`.
- **HTML saving fails with EPERM** — use the prescribed save path
  `sfdc-test/unit/javascript/htdocs/sa11y/jest`.
- **Standalone tests do not run** — verify the test naming pattern, Jest
  configuration, `@sa11y/jest` dependency, and `jsdom` environment.
