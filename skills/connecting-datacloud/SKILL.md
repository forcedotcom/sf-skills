---
name: connecting-datacloud
description: "Salesforce Data Cloud Connect phase. Use this skill when the user manages Data Cloud connections, connectors, or sets up a new source system. TRIGGER when: user manages Data Cloud connections, connectors, connector metadata, tests a connection, browses source objects or databases, or sets up a new source system. DO NOT TRIGGER when: the task is about data streams or DLOs (use preparing-datacloud), DMOs or identity resolution (use harmonizing-datacloud), retrieval/search (use retrieving-datacloud), or STDM telemetry (use observing-agentforce)."
license: MIT
compatibility: "Requires the sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# connecting-datacloud: Data Cloud Connect Phase

Use this skill when the user needs **source connection work**: connector discovery, connection metadata, connection testing, source-object browsing, connector schema inspection, or connector-specific setup payloads for external sources.

## When This Skill Owns the Task

Use `connecting-datacloud` when the work involves:
- `sf data360 connection *`
- connector catalog inspection
- connection creation, update, test, or delete
- browsing source objects, fields, databases, or schemas
- identifying connector types already in use
- preparing connector definitions for Snowflake, SharePoint Unstructured, or Ingestion API sources

Delegate elsewhere when the user is:
- creating data streams or DLOs → [preparing-datacloud](../preparing-datacloud/SKILL.md)
- creating DMOs, mappings, IR rulesets, or data graphs → [harmonizing-datacloud](../harmonizing-datacloud/SKILL.md)
- writing Data Cloud SQL or search-index workflows → [retrieving-datacloud](../retrieving-datacloud/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- connector type or source system
- whether the user wants inspection only or live mutation
- connection name or ID if one already exists
- whether credentials are already configured outside the CLI
- whether the user also expects stream creation right after connection setup
- whether the source is a database, an unstructured document source, or an Ingestion API feed

---

## Core Operating Rules

- Verify the plugin runtime first; see [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md).
- Run the shared readiness classifier before mutating connections: `node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase connect --json`.
- Prefer read-only discovery before connection creation.
- Suppress linked-plugin warning noise with `2>/dev/null` for standard usage.
- Remember that `connection list` requires `--connector-type`.
- For `connection test`, pass `--connector-type` when resolving a non-Salesforce connection by name.
- Discover existing connector types from streams first when the org is unfamiliar.
- Use curated example payloads before inventing connector-specific credentials or parameters.
- For connector types outside the curated examples, inspect a known-good UI-created connection via REST before building JSON.
- Do not promise API-based stream creation for every connector type just because connection creation succeeds.

---

## Recommended Workflow

### 1. Classify readiness for connect work
```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase connect --json
```

### 2. Discover connector types
```bash
sf data360 connection connector-list -o <org> 2>/dev/null
sf data360 data-stream list -o <org> 2>/dev/null
```

### 3. Inspect connections by type
```bash
sf data360 connection list -o <org> --connector-type SalesforceDotCom 2>/dev/null
sf data360 connection list -o <org> --connector-type REDSHIFT 2>/dev/null
sf data360 connection list -o <org> --connector-type SNOWFLAKE 2>/dev/null
```

### 4. Inspect a specific connection or uploaded schema
```bash
sf data360 connection get -o <org> --name <connection> 2>/dev/null
sf data360 connection objects -o <org> --name <connection> 2>/dev/null
sf data360 connection fields -o <org> --name <connection> 2>/dev/null
sf data360 connection schema-get -o <org> --name <connection-id> 2>/dev/null
```

### 5. Test or create only after discovery
```bash
sf data360 connection test -o <org> --name <connection> --connector-type <type> 2>/dev/null
sf data360 connection create -o <org> -f connection.json 2>/dev/null
```

### 6. Start from curated example payloads for external connectors
Use the phase-owned examples before inventing a payload from scratch:
- `examples/connections/heroku-postgres.json`
- `examples/connections/redshift.json`
- `examples/connections/sharepoint-unstructured.json`
- `examples/connections/snowflake-connection.json`
- `examples/connections/ingest-api-connection.json`
- `examples/connections/ingest-api-schema.json`

Typical Ingestion API setup flow:
```bash
sf data360 connection create -o <org> -f examples/connections/ingest-api-connection.json 2>/dev/null
sf data360 connection schema-upsert -o <org> --name <connector-id> -f examples/connections/ingest-api-schema.json 2>/dev/null
sf data360 connection schema-get -o <org> --name <connector-id> 2>/dev/null
```

### 7. Discover payload fields for unknown connector types
Create one in the UI, then inspect it directly:
```bash
sf api request rest "/services/data/v66.0/ssot/connections/<id>" -o <org>
```

---

## High-Signal Gotchas

- `connection list` has no true global "list all" mode; query by connector type.
- The connector catalog name and connection connector type are not always the same label.
- `connection test` may need `--connector-type` for name resolution when the source is not a default Salesforce connector.
- An empty connection list usually means "enabled but not configured yet", not "feature disabled".
- Heroku Postgres, Redshift, Snowflake, SharePoint Unstructured, and Ingestion API all use different credential and parameter shapes; reuse the curated examples instead of guessing.
- SharePoint Unstructured uses `clientId`, `clientSecret`, and `tokenEndpoint` in the `credentials` array and does not require a `parameters` array.
- Snowflake uses key-pair auth and can often be created through the API, but downstream stream creation can still remain UI-only.
- Ingestion API connector setup is incomplete until `connection schema-upsert` has uploaded the object schema.
- Some external connector credential setup still depends on UI-side configuration or external-system permissions.

---

## Output Format

```text
Connect task: <inspect / create / test / update>
Connector type: <SalesforceDotCom / REDSHIFT / SNOWFLAKE / SPUnstructuredDocument / IngestApi / ...>
Target org: <alias>
Commands: <key commands run>
Verification: <passed / partial / blocked>
Next step: <prepare phase or connector follow-up>
```

---

## References

- [README.md](README.md)
- [examples/connections/heroku-postgres.json](examples/connections/heroku-postgres.json)
- [examples/connections/redshift.json](examples/connections/redshift.json)
- [examples/connections/sharepoint-unstructured.json](examples/connections/sharepoint-unstructured.json)
- [examples/connections/snowflake-connection.json](examples/connections/snowflake-connection.json)
- [examples/connections/ingest-api-connection.json](examples/connections/ingest-api-connection.json)
- [examples/connections/ingest-api-schema.json](examples/connections/ingest-api-schema.json)
- [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md)
- [../orchestrating-datacloud/references/feature-readiness.md](../orchestrating-datacloud/references/feature-readiness.md)
- [../orchestrating-datacloud/UPSTREAM.md](../orchestrating-datacloud/UPSTREAM.md)
