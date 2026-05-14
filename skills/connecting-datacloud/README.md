# connecting-datacloud

Connection and connector workflows for Salesforce Data Cloud.

## Use this skill for

- listing available connector types
- inspecting configured connections
- testing a connection
- browsing source objects, databases, fields, and uploaded schemas
- preparing connector JSON for Snowflake, SharePoint Unstructured, and Ingestion API sources
- preparing for stream creation

## Key reminders

- `connection list` requires `--connector-type`
- `connection test` may need `--connector-type` for non-Salesforce name resolution
- use `connection schema-upsert` after creating an Ingestion API connector
- start with inspection before mutation
- use `2>/dev/null` to suppress linked-plugin warning noise
- some connector types can be created by API while downstream stream creation still requires UI flow

## Example requests

```text
"Show me which Data Cloud connections already exist in this org"
"Test my Snowflake Data Cloud connection"
"What source objects are available on this Salesforce connector?"
"Help me create an Ingestion API connector and upload its schema"
"Set up a SharePoint Unstructured connection for document ingestion"
```

## Common commands

```bash
sf data360 connection connector-list -o myorg 2>/dev/null
sf data360 connection list -o myorg --connector-type SalesforceDotCom 2>/dev/null
sf data360 connection get -o myorg --name SalesforceDotCom_Home 2>/dev/null
sf data360 connection test -o myorg --name Snowflake_Demo --connector-type SNOWFLAKE 2>/dev/null
sf data360 connection schema-get -o myorg --name <connector-id> 2>/dev/null
sf data360 connection create -o myorg -f examples/connections/heroku-postgres.json 2>/dev/null
sf data360 connection schema-upsert -o myorg --name <connector-id> -f examples/connections/ingest-api-schema.json 2>/dev/null
```

## Example payloads

- [examples/connections/heroku-postgres.json](examples/connections/heroku-postgres.json)
- [examples/connections/redshift.json](examples/connections/redshift.json)
- [examples/connections/sharepoint-unstructured.json](examples/connections/sharepoint-unstructured.json)
- [examples/connections/snowflake-connection.json](examples/connections/snowflake-connection.json)
- [examples/connections/ingest-api-connection.json](examples/connections/ingest-api-connection.json)
- [examples/connections/ingest-api-schema.json](examples/connections/ingest-api-schema.json)

## References

- [SKILL.md](SKILL.md)
- [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md)
- [../orchestrating-datacloud/UPSTREAM.md](../orchestrating-datacloud/UPSTREAM.md)
- [CREDITS.md](CREDITS.md)
