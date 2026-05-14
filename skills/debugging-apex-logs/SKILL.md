---
name: debugging-apex-logs
description: "Salesforce debug log analysis and troubleshooting with 100-point scoring. TRIGGER when: user analyzes debug logs, hits governor limits, reads stack traces, or touches .log files from Salesforce orgs. DO NOT TRIGGER when: running Apex tests (use running-apex-tests), generating or fixing Apex code (use generating-apex), or Agentforce session tracing (use observing-agentforce)."
license: LICENSE.txt has complete terms
metadata:
  version: "1.1"
---

# debugging-apex-logs: Salesforce Debug Log Analysis & Troubleshooting

Use this skill when the user needs **root-cause analysis from debug logs**: governor-limit diagnosis, stack-trace interpretation, slow-query investigation, heap / CPU pressure analysis, or a reproduction-to-fix loop based on log evidence.

## When This Skill Owns the Task

Use `debugging-apex-logs` when the work involves:
- `.log` files from Salesforce
- stack traces and exception analysis
- governor limits
- SOQL / DML / CPU / heap troubleshooting
- query-plan or performance evidence extracted from logs

Delegate elsewhere when the user is:
- running or repairing Apex tests → [running-apex-tests](../running-apex-tests/SKILL.md)
- generating or implementing the code fix → [generating-apex](../generating-apex/SKILL.md)
- debugging Agentforce session traces / parquet telemetry → [observing-agentforce](../observing-agentforce/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- org alias
- failing transaction / user flow / test name
- approximate timestamp or transaction window
- user / record / request ID if known
- whether the goal is diagnosis only or diagnosis + fix loop

---

## Recommended Workflow

### 1. Retrieve logs

Use the commands in [references/cli-commands.md](references/cli-commands.md) to list, download, or stream logs for the target org.

### 2. Analyze in this order
1. entry point and transaction type
2. exceptions / fatal errors
3. governor limits
4. repeated SOQL / DML patterns
5. CPU / heap hotspots
6. callout timing and external failures

### 3. Classify severity
- **Critical** — runtime failure, hard limit, corruption risk
- **Warning** — near-limit, non-selective query, slow path
- **Info** — optimization opportunity or hygiene issue

### 4. Recommend the smallest correct fix
Prefer fixes that are:
- root-cause oriented
- bulk-safe
- testable
- easy to verify with a rerun

Expanded workflow: [references/analysis-playbook.md](references/analysis-playbook.md)

---

## High-Signal Issue Patterns

| Issue | Primary signal | Default fix direction |
|---|---|---|
| SOQL in loop | repeating `SOQL_EXECUTE_BEGIN` in a repeated call path | query once, use maps / grouped collections |
| DML in loop | repeated `DML_BEGIN` patterns | collect rows, bulk DML once |
| Non-selective query | high rows scanned / poor selectivity | add indexed filters, reduce scope |
| CPU pressure | CPU usage approaching sync limit | reduce algorithmic complexity, cache, async where valid |
| Heap pressure | heap usage approaching sync limit | stream with SOQL for-loops, reduce in-memory data |
| Null pointer / fatal error | `EXCEPTION_THROWN` / `FATAL_ERROR` | guard null assumptions, fix empty-query handling |

Expanded examples: [references/common-issues.md](references/common-issues.md)

---

## Output Format

When finishing analysis, report in this order:

1. **What failed**
2. **Where it failed** (class / method / line / transaction stage)
3. **Why it failed** (root cause, not just symptom)
4. **How severe it is**
5. **Recommended fix**
6. **Verification step**

Suggested shape:

```text
Issue: <summary>
Location: <class / line / transaction>
Root cause: <explanation>
Severity: Critical | Warning | Info
Fix: <specific action>
Verify: <test or rerun step>
```

---

## Rules / Constraints

| Rule | Rationale |
|------|-----------|
| Always base fix recommendations on log evidence | Avoid speculative diagnosis — root cause must be traceable in the log |
| Report all six output fields for every issue found | Ensures actionable, complete findings for each problem |
| Classify every finding as Critical, Warning, or Info | Helps the user prioritize which issues to address first |
| Delegate code generation to `generating-apex` | This skill diagnoses; it does not rewrite Apex code |
| Delegate test execution to `running-apex-tests` | This skill does not run or repair test classes |
| Never assume limits are safe without reading `LIMIT_USAGE` events | Limits may be consumed by earlier operations not visible in the failure point |

---

## Gotchas

| Pitfall | Resolution |
|---------|------------|
| Log truncated at 2 MB | Reduce debug levels (e.g., `ApexCode: INFO`, `ApexProfiling: FINE`) and re-capture |
| Same issue appears as both SOQL and CPU problem | Fix SOQL-in-loop first — it typically drives the CPU spike as a secondary effect |
| No logs appear after trace flag is set | Verify the trace flag `ExpirationDate` is in the future and the correct user is traced |
| Async context changes limit values | CPU limit is 60,000 ms async vs 10,000 ms sync — check transaction type before flagging limits |
| Stack trace points to framework line, not user code | Walk up the call stack past trigger handlers to find the originating user code |

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Implement Apex fix | [generating-apex](../generating-apex/SKILL.md) | code change generation / review |
| Reproduce via tests | [running-apex-tests](../running-apex-tests/SKILL.md) | test execution and coverage loop |
| Deploy fix | [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) | deployment orchestration |
| Create debugging data | [handling-sf-data](../handling-sf-data/SKILL.md) | targeted seed / repro data |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/analysis-playbook.md` | Start here — expanded step-by-step workflow for any debugging session |
| `references/common-issues.md` | Quick lookup for SOQL in loop, DML in loop, CPU/heap pressure, null pointer patterns |
| `references/cli-commands.md` | SF CLI commands for retrieving, streaming, and managing debug logs |
| `references/debug-log-reference.md` | Full event type catalog, log levels, and governor limit reference values |
| `references/log-analysis-tools.md` | Tool guide: Apex Log Analyzer, Developer Console, CLI grep patterns |
| `references/benchmarking-guide.md` | Performance benchmarking techniques, benchmark data, and anti-patterns |
| `references/scoring-rubric.md` | 100-point scoring rubric for evaluating analysis quality |
| `assets/benchmarking-template.cls` | Copy-paste Anonymous Apex template for running performance benchmarks |
| `assets/cpu-heap-optimization.cls` | Apex patterns for reducing CPU time and heap allocation |
| `assets/dml-in-loop-fix.cls` | Before/after example for resolving DML-in-loop violations |
| `assets/soql-in-loop-fix.cls` | Before/after example for resolving SOQL-in-loop violations |
| `assets/null-pointer-fix.cls` | Patterns for guarding against null pointer exceptions |

---

## Score Guide

| Score | Meaning |
|---|---|
| 90+ | Expert analysis with strong fix guidance |
| 80–89 | Good analysis with minor gaps |
| 70–79 | Acceptable but may miss secondary issues |
| 60–69 | Partial diagnosis only |
| < 60 | Incomplete analysis |
