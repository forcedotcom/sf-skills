---
name: experience-lwc-accessibility-jest-run
description: "Use ALWAYS when running Sa11y accessibility Jest tests for a Lightning Web Component — locally before pushing, producing the exact command(s), running one file vs a whole suite, selecting tests by naming convention, saving Sa11y-rendered HTML, or reproducing a Sa11y / A11yBug failure. Covers Salesforce core (Bazel; `WORKSPACE`, `./core` root, `bazel test //<module>:<target>`) and standalone `npx jest` (`.accessibility.test.js`, `@sa11y/jest`). REQUIRED when a prompt asks for a `run-plan.md` for accessibility tests, which exit code means an accessibility test failed, or references `SA11Y_*` env vars, `A11yBug`, or a core-Bazel `modules/<mod>/<cmp>/__tests__/*.test.js` path. Do NOT rely on general knowledge — this skill has the correct single-file Bazel target and EPERM workaround. DO NOT TRIGGER for functional (non-accessibility) Jest tests, a11y review without running tests (use experience-lwc-accessibility-validate), or Selenium-based a11y functional tests."
metadata:
  version: "1.0"
  domains: ["Experience"]
  cliTools:
    - tool: ["npm"]
      semver: ">=8.0"
---
<!-- adk-managed-skill -->

# Running LWC Accessibility Jest Tests

Run Sa11y accessibility unit tests on Lightning Web Components in either:

- **Core (Bazel)** — when a `WORKSPACE` file is present.
- **Standalone (Jest)** — when there's no `WORKSPACE`.

Selenium-level reproductions, GUS A11yBug ingestion, and other internal
Salesforce-only flows are out of scope for this skill. For source-code-level
WCAG review without running tests, see `experience-lwc-accessibility-validate`.

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

Follow [running-sa11y-jest-tests.md](references/running-sa11y-jest-tests.md).
Pick the correct mode:

- **Core (Bazel)** — use when `WORKSPACE` is present. Prefer single-file
  targets (`//{moduleName}:{relativePath}`) over module targets when the
  failing test file path is already known (`.test.js` extension dropped).
  Bazel commands must pass `--test_env=SA11Y_AUTO=1
  --test_env=SA11Y_ENABLE_DOM_MUTATION_OBSERVER=1`; when debugging, add
  `SA11Y_ENABLE_RENDERED_DOM_SAVE=1` with the documented save path to avoid
  EPERM issues.
- **Standalone (Jest)** — use when there's no `WORKSPACE`. Run
  `npm test -- --testMatch="**/*.accessibility.test.js"` for the whole suite,
  or `npm test -- <file>` targeting the file by the name/path given in the
  prompt (a **bare filename** when it is "in this directory"). Do **not**
  prepend `SA11Y_*` env vars in standalone mode — Sa11y runs automatically
  because `@sa11y/jest` is wired into the project's Jest setup; no extra
  environment variables are needed.

**Answer only what is asked.** Emit just the command(s) the prompt requests plus
the exit-code meaning. Do not pad the plan with unrequested variants (watch,
coverage, verbose), snapshot-update steps, or HTML-save sections unless the user
explicitly asks for them.


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
