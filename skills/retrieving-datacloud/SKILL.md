---
name: retrieving-datacloud
description: "Salesforce Data Cloud Retrieve phase. Use this skill when the user runs Data Cloud SQL, async queries, vector search, search-index workflows, or metadata introspection for Data Cloud objects. TRIGGER when: user runs Data Cloud SQL, describe, async queries, vector search, search-index workflows, or metadata introspection for Data Cloud objects. DO NOT TRIGGER when: the task is standard CRM SOQL (use querying-soql), segment creation or calculated insight design (use segmenting-datacloud), or STDM/session tracing/parquet analysis (use observing-agentforce)."
license: MIT
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# retrieving-datacloud: Data Cloud Retrieve Phase

Use this skill when the user needs **query, search, and metadata introspection** for Data Cloud: sync SQL, paginated SQL, async query workflows, table describe, vector search, hybrid search, or search index operations.

## When This Skill Owns the Task

Use `retrieving-datacloud` when the work involves:
- `sf data360 query *`
- `sf data360 search-index *`
- `sf data360 metadata *`
- `sf data360 profile *` or `sf data360 insight *` inspection
- understanding Data Cloud SQL results or query shape

Delegate elsewhere when the user is:
- writing standard CRM SOQL only → [querying-soql](../querying-soql/SKILL.md)
- designing segment or calculated insight assets → [segmenting-datacloud](../segmenting-datacloud/SKILL.md)
- analyzing STDM/session tracing/parquet telemetry → [observing-agentforce](../observing-agentforce/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- whether the user needs quick count, medium result set, large export, schema inspection, or semantic search
- table/index name if known
- whether the task is read-only SQL or search-index lifecycle management

---

## Core Operating Rules

- Treat Data Cloud SQL as its own query language, not SOQL.
- Run the shared readiness classifier before relying on query/search surfaces: `node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase retrieve --json`.
- Use describe before guessing columns.
- Prefer `sqlv2` or async query flows for larger result sets.
- Use vector search or hybrid search only when the search index lifecycle is healthy.
- Keep STDM/parquet/session-tracing workflows out of this skill family.

---

## Recommended Workflow

### 1. Classify readiness for retrieve work
```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase retrieve --json
# optional query-plane probe, only with a real table name
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase retrieve --describe-table MyDMO__dlm --json
```

### 2. Choose the smallest correct query shape
```bash
sf data360 query sql -o <org> --sql 'SELECT COUNT(*) FROM "ssot__Individual__dlm"' 2>/dev/null
sf data360 query sqlv2 -o <org> --sql 'SELECT * FROM "ssot__Individual__dlm"' 2>/dev/null
sf data360 query async-create -o <org> --sql 'SELECT * FROM "ssot__Individual__dlm"' 2>/dev/null
```

### 3. Use describe before guessing fields
```bash
sf data360 query describe -o <org> --table ssot__Individual__dlm 2>/dev/null
```

### 4. Use vector or hybrid search only when an index exists
```bash
sf data360 search-index list -o <org> 2>/dev/null
sf data360 query vector -o <org> --index Knowledge_Index --query "reset password" --limit 5 2>/dev/null
sf data360 query hybrid -o <org> --index Knowledge_Index --query "reset password" --limit 5 2>/dev/null
sf data360 query hybrid -o <org> --index Insurance_Index --query "weather damage coverage" --prefilter "Type_of_Insurance__c='Home'" --limit 10 2>/dev/null
```

### 5. Reuse curated search-index examples when creating indexes
Use the phase-owned examples instead of inventing JSON from scratch:
- `examples/search-indexes/vector-knowledge.json`
- `examples/search-indexes/hybrid-structured.json`

---

## High-Signal Gotchas

- Data Cloud SQL is not SOQL.
- Table names should be double-quoted in SQL.
- `sqlv2` is better than ad hoc OFFSET paging for medium result sets.
- async query is preferable for large results.
- search-index operations and vector/hybrid queries depend on the index lifecycle being healthy.
- Hybrid search can use `--prefilter`, but only on fields configured as prefilter-capable when the search index was created.
- HNSW index parameters are typically read-only on create; leave `userValues: []` unless the platform explicitly documents otherwise.
- `query describe` is not a universal tenant probe; only run it with a known DMO or DLO table after broader readiness has been confirmed.

---

## Output Format

```text
Retrieve task: <sql / sqlv2 / async / describe / vector / search-index>
Target org: <alias>
Target object: <table or index>
Commands: <key commands run>
Verification: <query rows / schema / status>
Next step: <segment / harmonize / follow-up>
```

---

## References

- [README.md](README.md)
- [examples/search-indexes/vector-knowledge.json](examples/search-indexes/vector-knowledge.json)
- [examples/search-indexes/hybrid-structured.json](examples/search-indexes/hybrid-structured.json)
- [../orchestrating-datacloud/assets/definitions/search-index.template.json](../orchestrating-datacloud/assets/definitions/search-index.template.json)
- [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md)
- [../orchestrating-datacloud/references/feature-readiness.md](../orchestrating-datacloud/references/feature-readiness.md)
