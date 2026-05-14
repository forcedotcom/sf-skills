# preparing-datacloud

Ingestion and lake-preparation workflows for Salesforce Data Cloud.

## Use this skill for

- data streams
- Data Lake Objects (DLOs)
- data transforms
- Document AI setup and extraction
- unstructured ingestion and re-scan workflows
- deciding how a source dataset should enter Data Cloud
- classifying a dataset as `Profile`, `Engagement`, or `Other`
- using the Ingestion API send-data example after connector setup

## Example requests

```text
"Create a Data Cloud stream from Contact"
"Inspect the DLO created by this stream"
"Help me create a transform for ingested data"
"Re-run this SharePoint document stream so it picks up new files"
"Show me how to send records to Data Cloud through the Ingestion API"
```

## Common commands

```bash
sf data360 data-stream list -o myorg 2>/dev/null
sf data360 data-stream create-from-object -o myorg --object Contact --connection SalesforceDotCom_Home 2>/dev/null
sf data360 data-stream run -o myorg --name Contact_Home 2>/dev/null
sf data360 dlo get -o myorg --name Contact_Home__dll 2>/dev/null
sf data360 transform list -o myorg 2>/dev/null
sf data360 connection run-existing -o myorg --name <connection-id> 2>/dev/null
```

## Key reminders

- confirm whether a dataset should be treated as `Profile`, `Engagement`, or `Other` before creating the stream
- `data-stream run` is the preferred re-scan path for unstructured document ingestion
- `connection run-existing` is a connection-level rerun and is not a full substitute for stream refresh
- some external database and Ingestion API stream-creation flows still require UI setup
- initial unstructured DLO setup can be richer in the UI than in a minimal CLI payload
- use the local [examples/ingestion-api/](examples/ingestion-api/) folder for the send-data flow

## References

- [SKILL.md](SKILL.md)
- [examples/ingestion-api/README.md](examples/ingestion-api/README.md)
- [../orchestrating-datacloud/assets/definitions/data-stream.template.json](../orchestrating-datacloud/assets/definitions/data-stream.template.json)
- [CREDITS.md](CREDITS.md)
