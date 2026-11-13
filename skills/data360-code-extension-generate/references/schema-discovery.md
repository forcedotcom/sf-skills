# Discovering Source and Target Schemas

Commands for SKILL.md Phase 2. Use the first option that's available and tell the user which one you used. **If the Data 360 MCP server is connected, you must use it**; don't switch to the `sf api` fallback just because it has a ready-made command.

## 1. Data 360 MCP server (default)

Use the MCP check from SKILL.md Phase 0b. If Phase 0b didn't run in this session (for example the user asked straight for a code change), do that check now, before the first lookup.

- **Fields:** call `payload_examples` for `d360_dlo_get`, then `execute` it with the DLO name. One call per DLO.
- If `d360_dlo_get` isn't found, call `search` with "get DLO schema fields". Pass only the query; the server rejects `limit`.
- **Sample data:** `execute` `d360_query_sql` with `SELECT <field1>, <field2> FROM <INPUT_DLO> LIMIT 20`.

Tool details: [mcp-integration.md](mcp-integration.md).

## 2. Fallback only: `sf api`

Use this only when the MCP server isn't connected or its call failed, and say which. Use the `API_VERSION` printed by `check_env.sh`. These commands don't need `<PY_ENV>`.

### DLO fields

```bash
sf api request rest "/services/data/v<API_VERSION>/ssot/data-lake-objects/<DLO_NAME>" --target-org <ORG_ALIAS> 2>/dev/null \
  | jq '.dataLakeObjects[0] | {name, fields: [.fields[] | {name, dataType}]}'
```

The response wraps the object in an array: `{"dataLakeObjects": [{"name", "label", "fields": [{"name", "label", "dataType"}], ...}]}`. Read it with `.dataLakeObjects[0]`; a top-level `.fields` is null. Run one call per DLO, and compare `dataType` for fields you join or compare (for example, a Number key joined to a Text key needs a cast).

### Sample input data

Look at the input data before you write join or filter logic, especially self-joins and root conditions (null vs `0`). Parse with `jq`, not `python3 -c`: agent hosts treat inline interpreters like `eval` and ask for approval.

```bash
sf api request rest "/services/data/v<API_VERSION>/ssot/query-sql" --method POST --target-org <ORG_ALIAS> --body - <<'EOF' 2>/dev/null \
  | jq -c '.data[]'
{"sql": "SELECT <field1>, <field2> FROM <INPUT_DLO> LIMIT 20"}
EOF
```

## 3. UI

Data Cloud → **Data Lake Objects**, then open the object and check the field API names.

## Lowercase column names

Code extensions support only lowercase column names. The SDK lowercases every column it reads (`read_dlo` returns `kq_id__c`, not `KQ_id__c`), and writes accept only lowercase names, so a target field whose API name has a capital letter can't be written. Write only the target's own lowercase fields, computed ones included, end the code with an explicit `select()` of them, and refer to them by their lowercase names. Don't pass every source column through.
