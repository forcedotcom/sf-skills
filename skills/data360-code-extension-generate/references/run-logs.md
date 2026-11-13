# Reading a Deployed Run's Logs (`DataCustomCodeLogs__dll`)

Everything the deployed code prints or logs, including uncaught exceptions and tracebacks, is written to the system DLO **`DataCustomCodeLogs__dll`**, one row per message. Check it after every run (SKILL.md Phase 7), whether the run succeeded or failed.

| Field | Meaning |
|---|---|
| `DataCustomCodeName__c` | Name of the code extension (the deploy `--name`). Filter on this |
| `ExecutionId__c` | One value per run. All rows of a run share it |
| `Timestamp__c` | When the message was written. The newest rows are the latest run |
| `Message__c` | The printed or logged text, or the exception |

## Latest run

This returns every message from the **latest run** of `<name>`, in order. When the Data 360 MCP server is available, send the same SQL with its `d360_query_sql` tool first; use this command as the fallback:

```bash
sf api request rest "/services/data/v<API_VERSION>/ssot/query-sql" --method POST --target-org <ORG_ALIAS> --body - <<'EOF' \
  | jq -r '"rows: \(.returnedRows)", (.data[] | "\(.[0])  \(.[2])")'
{"sql": "SELECT Timestamp__c, ExecutionId__c, Message__c FROM DataCustomCodeLogs__dll WHERE DataCustomCodeName__c = '<name>' AND ExecutionId__c = (SELECT ExecutionId__c FROM DataCustomCodeLogs__dll WHERE DataCustomCodeName__c = '<name>' ORDER BY Timestamp__c DESC LIMIT 1) ORDER BY Timestamp__c"}
EOF
```

`--body -` reads the JSON request from the quoted heredoc, so the command needs no `$(…)`. Keep `<name>` free of `"` and `'`.

## Reading the rows

- Confirm the run is the one you just started: the newest `Timestamp__c` should be after you clicked Run Now. Log rows can take a few minutes to appear. If there are none, or only an older run's rows, wait and query again.
- Look in `Message__c` for `Traceback`, `Error` or `Exception` lines. They give the failing line in `entrypoint.py`.
- To see the last few runs at a glance, send this SQL the same way: `SELECT ExecutionId__c, MIN(Timestamp__c), MAX(Timestamp__c), COUNT(*) FROM DataCustomCodeLogs__dll WHERE DataCustomCodeName__c = '<name>' GROUP BY ExecutionId__c ORDER BY 2 DESC LIMIT 5`.
- In the UI, use **Data Explorer**: choose `DataCustomCodeLogs__dll` and filter on `DataCustomCodeName__c`.
- Add `print()` or `logging` calls to the code to trace a deployed run, then redeploy. Local `run` prints to the terminal instead.
