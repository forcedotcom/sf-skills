# MCP Invocation Reference — Multi-Campus Hierarchy

`headless-360` is the default transport (see Mechanism in `SKILL.md` for the health-probe and fallback
sequence). When it's healthy, every operation below dispatches through it via four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pull the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, queryParams?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, queryParams?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v68.0/...`), `method`, optional `body`, and optional `queryParams` (camelCase — the
tool rejects `query_params`, and a SOQL string must go in `queryParams.q`, never appended inline to
the URL as `?q=`). The server signs the request with the JWT bound to the current MCP session and
forwards it to the org — the skill never handles a credential, org id, or alias.

**A `discover` miss does NOT mean the route is absent.** The standard `/sobjects/...` and `/query`
REST routes this skill uses are not always ranked first (or indexed) in the discovery corpus —
`describe` on the canonical operation still returns the schema, and `dispatch*` on the exact path
still works. Only if the GET/POST/PATCH/DELETE itself returns 404 should you treat the route as
unavailable on this org.

## Response envelope

`dispatch*` returns the REST response singly wrapped:

```json
{ "status_code": 200, "body": { "totalSize": 1, "records": [ { "Id": "001..." } ] } }
```

Read the relevant field from `body`. Status codes: `200` read success; `201` record created; `400`
bad body or a business-rule rejection — read `body[0].errorCode`; `403` access/feature gap; `404` the
endpoint/impl is not present on this org.

## Calls used by this skill

**Step 3.5 — resolve Account RecordType**
```text
mcp__headless-360__dispatch_readonly({"url": "/services/data/v68.0/sobjects/Account/describe", "method": "GET"})
```

**Step 5 — load current hierarchy**
```text
mcp__headless-360__dispatch_readonly({"url": "/services/data/v68.0/sobjects/Account/[Account Id]/ChildAccounts", "method": "GET"})
```
Fallback if `ChildAccounts` is unavailable:
```text
mcp__headless-360__dispatch_readonly({
  "url": "/services/data/v68.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id, Name, ParentId FROM Account WHERE ParentId = '[Account Id]'" }
})
```

**Step 7 — create / rename / move / delete Account**
```text
mcp__headless-360__dispatch({
  "url": "/services/data/v68.0/sobjects/Account",
  "method": "POST",
  "body": { "Name": "[Node name]", "RecordTypeId": "[recordTypeId]", "ParentId": "[Parent Account Id]" }
})
mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/Account/[Account Id]", "method": "PATCH", "body": {"Name": "[new name]"}})
mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/Account/[Account Id]", "method": "PATCH", "body": {"ParentId": "[new parent Account Id]"}})
mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/Account/[Account Id]", "method": "DELETE"})
```

**Step 8 — create BusinessProfile**
```text
mcp__headless-360__dispatch({"url": "/services/data/v68.0/sobjects/BusinessProfile", "method": "POST", "body": {"AccountId": "[Account ID]"}})
```

**Step 9 — cold verification**
```text
mcp__headless-360__dispatch_readonly({"url": "/services/data/v68.0/sobjects/Account/[Account Id]", "method": "GET"})
```
