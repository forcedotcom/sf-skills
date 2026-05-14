# retrieving-datacloud

Query and search workflows for Salesforce Data Cloud.

## Use this skill for

- quick SQL counts
- paginated SQL (`sqlv2`)
- async query lifecycles
- table describe
- vector search
- hybrid search with optional prefilter
- search index inspection and lifecycle work

## Example requests

```text
"Run a Data Cloud SQL query against unified profiles"
"Describe this Data Cloud table before I write SQL"
"Help me troubleshoot vector search in Data Cloud"
"Run a hybrid search with a prefilter in Data Cloud"
"Create and inspect a search index"
```

## Common commands

```bash
sf data360 query sql -o myorg --sql 'SELECT COUNT(*) FROM "ssot__Individual__dlm"' 2>/dev/null
sf data360 query describe -o myorg --table ssot__Individual__dlm 2>/dev/null
sf data360 search-index list -o myorg 2>/dev/null
sf data360 query vector -o myorg --index Knowledge_Index --query "reset password" --limit 5 2>/dev/null
sf data360 query hybrid -o myorg --index Knowledge_Index --query "reset password" --limit 5 2>/dev/null
```

## Example payloads

- [examples/search-indexes/vector-knowledge.json](examples/search-indexes/vector-knowledge.json)
- [examples/search-indexes/hybrid-structured.json](examples/search-indexes/hybrid-structured.json)

## References

- [SKILL.md](SKILL.md)
- [../orchestrating-datacloud/assets/definitions/search-index.template.json](../orchestrating-datacloud/assets/definitions/search-index.template.json)
- [CREDITS.md](CREDITS.md)
