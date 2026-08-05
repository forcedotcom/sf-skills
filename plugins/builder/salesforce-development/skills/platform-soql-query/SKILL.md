---
name: platform-soql-query
description: "SOQL query generation, optimization, and analysis with 100-point scoring. Use this skill when the user needs SOQL/SOSL authoring or optimization: natural-language-to-query generation, relationship queries, aggregates, query-plan analysis, and performance or safety improvements for Salesforce queries. TRIGGER when: user writes, optimizes, or debugs SOQL/SOSL queries, touches .soql files, or asks about relationship queries, aggregates, or query performance. DO NOT TRIGGER when: bulk data operations (use platform-data-manage), Apex DML logic (use platform-apex-generate), or report/dashboard queries."
allowed-tools: |
  Bash Read Write
  mcp__plugin_salesforce-development_salesforce-lsp__validate_soql
  mcp__plugin_salesforce-development_salesforce-lsp__complete_soql
  mcp__plugin_salesforce-development_salesforce-lsp__check_soql_selectivity
  mcp__plugin_salesforce-development_salesforce-lsp__extract_soql_from_apex
  mcp__plugin_salesforce-development_salesforce-lsp__refresh_org_schema
metadata:
  version: "1.1"
  relatedSkills:
    - "experience-lwc-generate"
    - "platform-apex-generate"
    - "platform-apex-logs-debug"
    - "platform-apex-test-run"
    - "platform-data-manage"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  mcpTools:
    salesforce-lsp:
      tools:
        - validate_soql
        - complete_soql
        - check_soql_selectivity
        - extract_soql_from_apex
        - refresh_org_schema
      semver: ">=0.1.0"
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

While drafting, call `mcp__plugin_salesforce-development_salesforce-lsp__complete_soql` with the partial query to get schema-aware completion of object, field, and relationship names against the connected org — this avoids guessing API names that then fail validation. On error envelope or unavailable (`{error: <code>}` / tool not registered), skip completion and rely on the syntax reference in `references/soql-syntax-reference.md`.

When the query already lives inside an Apex class (optimizing or debugging embedded SOQL rather than authoring new), call `mcp__plugin_salesforce-development_salesforce-lsp__extract_soql_from_apex` with the `.cls` file to pull the SOQL strings out before analyzing them, so you optimize the exact query the class runs.

### 2. Choose the right query shape
| Need | Default pattern |
|---|---|
| parent data from child | child-to-parent traversal |
| child rows from parent | subquery |
| counts / rollups | aggregate query |
| records with / without related rows | semi-join / anti-join |
| text search across objects | SOSL |

### 3. Validate with LSP tools (REQUIRED)

**REQUIRED:** Before running a SOQL query against the org or recommending it for production use:

1. **Call `mcp__plugin_salesforce-development_salesforce-lsp__validate_soql`** with the query string to check syntax and catch parse errors before execution.
   - On success (`{ok: true}`), proceed. **A clean parse is not a clean query.** `validate_soql` is parser-only — it accepts objects, fields, and relationships that do not exist in the target org. A successful parse means the syntax is well-formed, NOT that the identifiers resolve.
   - **Fail closed on an uncertain result.** If the call timed out, was retried, or its result is otherwise uncertain, do NOT treat it as a successful validation — fall back to step 2 and record `validate_soql=unavailable: timeout`.
   - On error envelope (`{error: <code>}`), record `validate_soql=unavailable: <code>` and fall back to step 2.
   - On unavailable (tool not registered), record `validate_soql=unavailable: lsp_not_present` and fall back to step 2.

2. **Verify identifiers against org schema (REQUIRED, even when the parse succeeds).** Confirm every object, field, and relationship in the query actually exists in the target org before recommending it — a well-formed parse over a nonexistent field must not be reported as valid.
   - **Authoritative check — describe or a bounded probe. Do NOT execute the user's full query to verify schema** (it may be unbounded and retrieve large result sets). Instead:
     - **Preferred:** `sf sobject describe --sobject <Object> --target-org <org>` for each object in the query, and confirm every referenced field/relationship appears in the describe output. This resolves identifiers with no rows retrieved.
     - **Alternative:** a bounded org-backed probe — the same query rewritten with `LIMIT 0` (or the object's key with `LIMIT 1`) via `sf data query --query "<bounded-query>" --json --target-org <org>`. `LIMIT 0` validates every identifier server-side while returning no rows; a bad object or field surfaces as an `INVALID_TYPE` / `INVALID_FIELD` error.
   - `mcp__plugin_salesforce-development_salesforce-lsp__complete_soql` may be used to resolve names while drafting, but completion returns candidates at a cursor position — not a validation result for every identifier — and can return `{ok: true, hint: "no_org_connected"}` with placeholder schema. **Completion output is NOT sufficient schema verification:** if `complete_soql` returns `no_org_connected` or does not resolve every identifier, fall back to the describe or bounded-probe check above.
   - **NEVER** report a query as valid because the validation check didn't run or only parsed — always confirm identifiers against the org schema first.

3. **For production queries**, also call `mcp__plugin_salesforce-development_salesforce-lsp__check_soql_selectivity` to analyze selectivity heuristics before recommending the query for high-volume or scheduled use.
   - On error envelope or unavailable, record `check_soql_selectivity=unavailable: <code>` and note selectivity was not verified.

4. **After deploying schema changes**, if a field or object reference fails validation immediately after deployment, call `mcp__plugin_salesforce-development_salesforce-lsp__refresh_org_schema` to invalidate the cached org describe, then re-validate before assuming a code error.

See the `platform-lsp-integrate` skill for the complete LSP Call/Fallback Contract and error code reference.

### 4. Optimize for selectivity and safety
Check:
- indexed / selective filters
- no unnecessary fields
- no avoidable wildcard or scan-heavy patterns
- security enforcement expectations

### 5. Validate execution path if needed
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

```text
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
