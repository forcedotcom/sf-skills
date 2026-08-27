---
name: dx-devops-test-failures-analyze
description: "Analyzes DevOps Center test failures and Code Analyzer violations in plain language — failure category, offending file/class/method/line, rule violated, fix direction, and prioritized improvement suggestions (test-code vs production-code) — then optionally creates a tracked fix WorkItem on explicit request. Analysis is pure reasoning; work-item creation is a confirmation-gated write. Use this skill to explain failures or improvement suggestions, translate Code Analyzer violations, or track a fix as a work item. TRIGGER when: a run failed and the user wants root cause; a quality gate failure needs explaining; violations need translating; the user shares a failure payload and asks how to address it; wants to strengthen tests; or wants to create a fix work item, log a remediation, or assign a failure. DO NOT TRIGGER when: the user wants fix code written (use platform-apex-generate) or new test classes authored (use platform-apex-test-generate)."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "67.0"
  relatedSkills:
    - "dx-devops-test-suite-assignments-configure"
    - "dx-devops-test-suite-run"
    - "platform-apex-generate"
    - "platform-apex-test-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.67.0"
---

# Analyze DevOps Center Test Failures

Parses a test failure or Code Analyzer violation payload, explains it in plain language, produces prioritized improvement suggestions, and — only on explicit user request — creates a tracked fix work item. Parts 1–2 are pure reasoning (no writes); Part 3 is an optional, confirmation-gated write.

**Never expose raw JSON, stack traces, or internal Salesforce error codes to the user.** Always translate to file name, method, line, and plain description.

---

## Prerequisites

- **Parts 1–2 (analysis):** If the failure payload is already in context, no prerequisites are needed — this is pure reasoning. If you must fetch the payload yourself, run prerequisites (`references/prerequisite-checks.md`, Prereqs 1–4) and obtain the execution result via `dx-devops-test-suite-run` (its polling step).
- **Part 3 (work item):** Run Prerequisites 1–4. You also need a `DevopsProjectId` to file under and an `OwnerId` (assignee). See `references/work-item-creation.md`.

---

## Part 1 — Classify and explain each failure

Determine the failure category, then for each failure extract and translate to plain language: offending file/class, method, line number, the rule or assertion violated, and a fix direction (without writing code). Group failures by category if more than one.

| Category | Description |
|---|---|
| Assertion failure | A test assertion failed (expected vs actual mismatch) |
| Exception | An unhandled exception was thrown |
| Code Analyzer violation | A static-analysis rule was violated (e.g. `ApexCRUDViolation`) |
| Timeout | Test exceeded execution time limit |
| Compile error | Class failed to compile |

**Output format:**

```text
Test failure summary:

<N> failure(s) found:

1. [<Category>] `<ClassName>.cls` — `<methodName>()` at line <N>
   What happened: <plain-language description>
   Rule violated: <ruleName or assertion description>
   Fix direction: <plain-language suggestion>
```

Full category/pattern tables and Code Analyzer rule translations: `references/failure-categories.md` and `references/code-analyzer-violations.md`.

**Empty / no-data case:** If the payload contains no failures or violations, report that clearly (e.g. "No failures found in the provided execution results.") and stop. Do NOT fabricate failures or suggestions.

---

## Part 2 — Improvement suggestions

Run this **after execution completes with failures**, not on static source. For each failed test, reason over the failure message (the primary signal) to identify what the test is not handling, then produce a specific, actionable suggestion and a **fix location** (Test vs Production code). The full failure-pattern → suggestion mapping is in `references/failure-categories.md`.

```text
Test improvement suggestions based on execution results:

`<testMethodName>()` — [Assertion Failure / Exception / etc.]
Failure: "<failure message>"
What this reveals: <plain-language explanation>
Suggestion: <specific, actionable recommendation>
Fix location: Test | Production code

Overall: <N> improvement(s) across <M> failed test(s).
```

Do not rewrite the test — only describe what needs to change and why. **Fix location: Production code** indicates a code defect exposed by a sound test (track separately, not a test-quality blocker). **Fix location: Test** indicates the test needs hardening (setup, assertions, edge cases).

---

## Part 3 — Create a fix work item (optional, on request only)

Trigger only when the user wants to create a fix work item, log a remediation, or assign a failure to a developer. This is a **write** operation with a mandatory confirmation gate. Follow `references/work-item-creation.md` for inputs, the subject/assignee/project confirmation gate, the `sf data create record --sobject WorkItem` call, and error handling.

> Use `WorkItem` (no namespace) — `DevopsWorkItem` is not a supported sObject in this org version.

If no `DevopsProject` exists in the org, report that the work item cannot be created until a project is set up — do NOT fabricate a project or proceed.

---

## Related skills

- **`dx-devops-test-suite-run`** — produces the failure payload (via its polling step) that feeds this skill.
- **`dx-devops-test-suite-assignments-configure`** — assign/strengthen the suites whose tests are failing.
- **`platform-apex-generate` / `platform-apex-test-generate`** — to actually write fix code or new test classes (out of scope here).
