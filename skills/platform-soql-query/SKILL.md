---
name: platform-soql-query
description: "SOQL query generation, optimization, and analysis with 100-point scoring. Use this skill when the user needs SOQL/SOSL authoring or optimization: natural-language-to-query generation, relationship queries, aggregates, query-plan analysis, and performance or safety improvements for Salesforce queries. TRIGGER when: user writes, optimizes, or debugs SOQL/SOSL queries, touches .soql files, or asks about relationship queries, aggregates, or query performance. DO NOT TRIGGER when: bulk data operations (use platform-data-manage), Apex DML logic (use platform-apex-generate), or report/dashboard queries."
metadata:
  version: "1.1"
---

# platform-soql-query: Salesforce SOQL Query Expert

Use this skill when the user needs **SOQL/SOSL authoring or optimization**: natural-language-to-query generation, relationship queries, aggregates, query-plan analysis, and performance/safety improvements for Salesforce queries.

## When This Skill Owns the Task

Use `platform-soql-query` when the work involves:
- `.soql` files
- query generation from natural language
- relationship queries and aggregate queries
- query optimization and selectivity analysis
- SOQL/SOSL syntax and governor-aware design

Delegate elsewhere when the user is:
- performing bulk data operations → [platform-data-manage](../platform-data-manage/SKILL.md)
- embedding query logic inside broader Apex implementation → [platform-apex-generate](../platform-apex-generate/SKILL.md)
- debugging via logs rather than query shape → [platform-apex-logs-debug](../platform-apex-logs-debug/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target object(s)
- fields needed
- filter criteria
- sort / limit requirements
- whether the query is for display, automation, reporting-like analysis, or Apex usage
- whether performance / selectivity is already a concern

---

## Recommended Workflow

### 1. Generate the simplest correct query
Prefer:
- only needed fields
- clear WHERE criteria
- reasonable LIMIT when appropriate
- relationship depth only as deep as necessary

### 2. Choose the right query shape
| Need | Default pattern |
|---|---|
| parent data from child | child-to-parent traversal |
| child rows from parent | subquery |
| counts / rollups | aggregate query |
| records with / without related rows | semi-join / anti-join |
| text search across objects | SOSL |

### 3. Optimize for selectivity and safety
Check:
- indexed / selective filters
- no unnecessary fields
- no avoidable wildcard or scan-heavy patterns
- security enforcement expectations

### 4. Validate execution path if needed
If the user wants runtime verification, hand off execution to:
- [platform-data-manage](../platform-data-manage/SKILL.md)

---

## High-Signal Rules

- never use `SELECT *` style thinking; query only required fields
- do not query inside loops in Apex contexts
- prefer filtering in SOQL rather than post-filtering in Apex
- use aggregates for counts and grouped summaries instead of loading unnecessary records
- evaluate wildcard usage carefully; leading wildcards often defeat indexes
- account for security mode / field access requirements when queries move into Apex

---

## Output Format

When finishing, report in this order:
1. **Query purpose**
2. **Final SOQL/SOSL**
3. **Why this shape was chosen**
4. **Optimization or security notes**
5. **Execution suggestion if needed**

Suggested shape — use `references/soql-syntax-reference.md` for exact syntax:

```
Query goal: <summary>
Query: <soql or sosl>
Design: <relationship / aggregate / filter choices>
Notes: <selectivity, limits, security, governor awareness>
Next step: <run in platform-data-manage or embed in Apex>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| run the query against an org | [platform-data-manage](../platform-data-manage/SKILL.md) | execution and export |
| embed the query in services/selectors | [platform-apex-generate](../platform-apex-generate/SKILL.md) | implementation context |
| analyze slow-query symptoms from logs | [platform-apex-logs-debug](../platform-apex-logs-debug/SKILL.md) | runtime evidence |
| wire query-backed UI | [experience-lwc-generate](../experience-lwc-generate/SKILL.md) | frontend integration |

---

## Score Guide

| Score | Meaning |
|---|---|
| 90+ | production-optimized query |
| 80–89 | good query with minor improvements possible |
| 70–79 | functional but performance concerns remain |
| < 70 | needs revision before production use |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/soql-syntax-reference.md` | Syntax, operators, date literals, relationship query patterns |
| `references/query-optimization.md` | Selectivity rules, indexing strategy, governor limits, security patterns |
| `references/soql-reference.md` | Quick reference — operators, date functions, aggregate functions, WITH clauses |
| `references/anti-patterns.md` | Common SOQL mistakes and their fixes — read before finalizing any query |
| `references/selector-patterns.md` | Apex selector layer patterns — read when embedding queries in Apex classes |
| `references/field-coverage-rules.md` | Field coverage validation — read when generating SOQL used inside Apex code |
| `references/cli-commands.md` | sf CLI query execution, bulk export, query plan commands |
| `assets/basic-queries.soql` | Starter query examples for common objects |
| `assets/relationship-queries.soql` | Parent-to-child and child-to-parent relationship query patterns |
| `assets/aggregate-queries.soql` | COUNT, SUM, GROUP BY, ROLLUP query patterns |
| `assets/optimization-patterns.soql` | Selective filter and index-aware query patterns |
| `assets/bulkified-query-pattern.cls` | Apex Map-based bulk query pattern for trigger contexts |
| `assets/selector-class.cls` | Full selector class implementation template |
| `scripts/post-tool-validate.py` | Post-write hook — runs static SOQL validation and live query plan analysis after `.soql` file edits |
