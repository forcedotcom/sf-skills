# R3 Node Schema

Verified node shapes for Spring '26 / API v66 orgs.

## load

`mode` valid values: `SYNCED` (default — replicates data before processing), `DIRECT` (queries live, no replication lag but higher API cost), `AUTO` (platform chooses).

```json
{
  "action": "load",
  "sources": [],
  "parameters": {
    "dataset": {
      "type": "connectedDataset",
      "label": "Opportunity",
      "connectionName": "SFDC_LOCAL",
      "sourceObjectName": "Opportunity"
    },
    "fields": ["Id", "AccountId", "StageName", "CloseDate", "Amount"],
    "mode": "SYNCED",
    "preserveCurrencyFields": [],
    "sampleDetails": { "type": "TopN", "sortBy": [] }
  }
}
```

## filter
```json
{
  "action": "filter",
  "sources": ["LOAD_OPPORTUNITY"],
  "parameters": {
    "filterExpressions": [
      { "field": "StageName", "operator": "EQUAL", "operands": ["Closed Won"], "type": "TEXT" }
    ]
  }
}
```

## join
```json
{
  "action": "join",
  "sources": ["FILTER_CLOSED_WON", "LOAD_ACCOUNT"],
  "parameters": {
    "joinType": "LOOKUP",
    "leftKeys": ["AccountId"],
    "rightKeys": ["Id"],
    "rightQualifier": "Account"
  }
}
```
Do NOT pass `rightSelectedFields` — it is rejected. After a LOOKUP join, right-side fields are addressable as `<rightQualifier>.<FieldName>` (e.g. `Account.Name`).

**Join keys must be the same type.** `leftKeys` and `rightKeys` are paired by position. Joining an ID to an ID (`Opportunity.AccountId` → `Account.Id`) works. Joining an ID to a TEXT Name, or a NUMBER Amount to a TEXT code, fails at run time with a type-mismatch on the join keys. Do not stringify IDs to "make the types match" — pick the real lookup field.

## formula
```json
{
  "action": "formula",
  "sources": ["JOIN_ACCOUNT"],
  "parameters": {
    "expressionType": "SQL",
    "fields": [
      {
        "name": "TotalAmount",
        "label": "Total Amount",
        "type": "NUMBER",
        "formulaExpression": "Amount"
      }
    ]
  }
}
```

### Critical formula rules

- **`expressionType` must be `"SQL"`** — `"FORMULA"` silently drops the `type` field, defaulting output to TEXT.
- **`type` must be `"NUMBER"`** for numeric output — `"NUMERIC"`, `"DECIMAL"`, `"INTEGER"` etc. normalize to TEXT at write time, causing runtime: *"formula generates decimal(35,17) but output type is TEXT"*.
- Valid `type` values: `"NUMBER"`, `"TEXT"`, `"DATE"`, `"DATETIME"`.
- Do NOT include `precision` or `scale` — they trigger *"Unrecognized field 'scale'"*.
- **Numeric outputs become measures, not dimensions.** SAQL `group q by 'CloseYear'` fails with errorCode 119 if CloseYear is NUMBER. Use `date_format` with `type: "TEXT"` for groupable date dimensions.
- **One field per formula node — hard UI constraint.** REST API accepts multiple fields and the recipe compiles/runs fine, but the Recipe Designer breaks with *"Can't Load the Recipe — A node can only define one field."* Always chain separate single-field formula nodes:
  ```json
  "COMPUTE_YEAR":  { "action": "formula", "sources": ["JOIN_ACCOUNT"],   "parameters": { "expressionType": "SQL", "fields": [{ "name": "CloseYear",  "type": "TEXT", "formulaExpression": "date_format(CloseDate, 'yyyy')" }] } },
  "COMPUTE_MONTH": { "action": "formula", "sources": ["COMPUTE_YEAR"],    "parameters": { "expressionType": "SQL", "fields": [{ "name": "CloseMonth", "type": "TEXT", "formulaExpression": "date_format(CloseDate, 'MM/yyyy')" }] } }
  ```
- **`date_format` patterns**: `'yyyy'` → `"2032"` (TEXT, groupable) ✓ | `'MM/yyyy'` → `"03/2032"` (TEXT, groupable) ✓ | `'MMM yyyy'` → silently produces numeric month integer ✗
- `lpad()`, `string()`, and bare `concat()` with string-converted date parts are NOT available in Wave recipe SQL — use `date_format`.
- **`coalesce()` is not reliable in recipe SQL.** Null/blank TEXT dimensions use a `case` expression, one field per node:
  ```sql
  case when (Account.Industry is null or Account.Industry = '') then 'Unknown' else Account.Industry end
  ```
- **Conditional buckets** also use `case` (not `IFF` / `IF`). Example deal-size TEXT dimension:
  ```sql
  case when Amount >= 100000 then 'Large' when Amount >= 50000 then 'Medium' else 'Small' end
  ```
- **Quarter as TEXT**: there is no proven `'QQ'` / `'Q'` `date_format` pattern. Derive it from the month string:
  ```sql
  case when date_format(CloseDate, 'MM') <= '03' then 'Q1' when date_format(CloseDate, 'MM') <= '06' then 'Q2' when date_format(CloseDate, 'MM') <= '09' then 'Q3' else 'Q4' end
  ```
- **Changing formula field `type` requires DELETE + re-POST** — `PATCH ?format=R3` may not update the runtime compiled artifact; multipart PATCH destroys compiled state entirely.

## extractGrains (EXTRACT0)
```json
{
  "action": "extractGrains",
  "sources": ["COMPUTE_CLOSE_MONTH"],
  "parameters": { "grainExtractions": [] }
}
```
Always insert EXTRACT0 between the last formula node and aggregate. The aggregate must list `EXTRACT0` in its `sources`, not the last formula node directly.

## aggregate
```json
{
  "action": "aggregate",
  "sources": ["EXTRACT0"],
  "parameters": {
    "aggregations": [
      { "name": "TotalRevenue", "label": "Total Revenue", "action": "SUM", "source": "TotalAmount" }
    ],
    "groupings": ["AccountId", "Account.Name", "CloseYear", "CloseMonth"],
    "nodeType": "STANDARD",
    "pivots": []
  }
}
```
Every column in `groupings` must physically exist on the upstream node's output. Wave does NOT auto-derive `<Date>_Year` / `<Date>_Month` in mid-pipeline — derive them via formula nodes.

## save
```json
{
  "action": "save",
  "sources": ["AGGREGATE_BY_ACCOUNT_MONTH"],
  "parameters": {
    "dataset": {
      "type": "analyticsDataset",
      "label": "DTS_OpportunityRev",
      "name": "DTS_OpportunityRev",
      "folderName": "OpportunityInsights"
    },
    "fields": [],
    "measuresToCurrencies": []
  }
}
```

## Common errors → fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Recipe in `New` status, `targetDataflowId` null | Multipart upload instead of `?format=R3` JSON | Re-create with `POST /wave/recipes?format=R3` |
| `500 "tableModelInfo is null"` | Multipart PATCH destroyed compiled state | DELETE recipe and re-POST via R3 JSON body |
| `400 "Recipe Definition JSON is missing"` | Sent multipart while using `?format=R3` | Use plain `application/json` with `recipeDefinition` embedded |
| Formula type mismatch at runtime | Wrong `type` (e.g. `"TEXT"`) on numeric formula | Use `type: "NUMBER"` and `expressionType: "SQL"` |
| Aggregate: `Can't find field _Year` | Auto-derived helpers don't exist mid-pipeline | Add formula node: `date_format(CloseDate, 'yyyy')` |
| `400 errorCode 276` on POST | Recipe name already exists | Use `PATCH /wave/recipes/{id}?format=R3` instead |
| `400 Id not found: 05v...` on dataflowjobs | Passed recipe id instead of `targetDataflowId` | Use the `02K...` id |
| Recipe opens with "Can't Load the Recipe" | Formula node has multiple fields | Split into chained single-field formula nodes |

## Common wrong variants

The API silently rejects incorrect field names, function expressions, and structural keys. Use the values in the Correct column verbatim.

| Node type | Correct usage / field name | Common wrong variant |
|-----------|-------------------|----------------------|
| load | `parameters.dataset.type: "connectedDataset"` | `connection: "LocalSalesforce"` |
| load | `parameters.dataset.connectionName: "SFDC_LOCAL"` | `connection` key at top level |
| load | `parameters.dataset.sourceObjectName: "Opportunity"` | `object` key |
| filter | `parameters.filterExpressions[].operator: "EQUAL"` | `predicate.expression` |
| filter | `parameters.filterExpressions[].operands: ["Closed Won"]` | `value` key |
| join | `parameters.joinType: "LOOKUP"` | `"Left"`, `"INNER"` |
| join | `parameters.leftKeys: ["AccountId"]` | `leftKey` (singular) |
| join | `parameters.rightKeys: ["Id"]` | `rightKey` (singular) |
| join | `parameters.rightQualifier: "Account"` | `rightPrefix` |
| formula | `action: "formula"` | `"computeExpression"`, `"augmentColumns"`, `"transform"` |
| formula | `parameters.fields[].formulaExpression` | `formula`, `expression` |
| formula | `parameters.fields` (array key) | `"columns"` |
| formula | field names unquoted: `date_format(CloseDate, 'yyyy')` | backtick-quoted: `` date_format(`CloseDate`, 'yyyy') `` |
| formula | `parameters.fields[].type: "TEXT"` | `dataType` |
| formula | `date_format(CloseDate, 'yyyy')` | `TO_CHAR(CloseDate, 'YYYY')` |
| extractGrains | `parameters.grainExtractions: []` | `grainFields: [...]` |
| aggregate | `parameters.aggregations[].action: "SUM"` | `operation` |
| aggregate | `parameters.aggregations[].source: "Amount"` | `field` |
| aggregate | `parameters.groupings: [...]` | `groupBy` |
| aggregate | `parameters.nodeType: "STANDARD"` | absent |
| aggregate | `parameters.pivots: []` | absent |
| save | `parameters.dataset.folderName: "AppName"` | `app`, `folder` |
| save | `parameters.fields: []` | absent |
| save | `parameters.measuresToCurrencies: []` | absent |
| ui connectors | `{ "source": "A", "target": "B" }` | `{ "from": "A", "to": "B" }` |
| ui containers | `"graph": { ... }` | `"children": { ... }` |
