# Example: Invocable action name source (preferred)

A complete walkthrough when the user gives only the **invocable action API name** and the action is deployed to a reachable org (`source = action`). No `.cls` parsing — the Actions REST API describes the typed outputs directly.

## The prompt

> My custom MCP server has a GetAccountSummary tool backed by the `GetAccountSummaryTest` invocable action in my org. Build a widget that renders its output as a rich account card.

## Phase 1 — Input selection

- Source: `action` (prompt gives an action API name; an authenticated org is available).
- Tool API name: `getAccountSummary` (camelCase of the tool / action label).
- Action API name: `GetAccountSummaryTest` (the Apex class declaring `@InvocableMethod`).

## Phase 2 — Payload discovery

Read `references/mcp-tool-output-discovery.md`, then describe the action:

```bash
sf api request rest '/services/data/v63.0/actions/custom/apex/GetAccountSummaryTest' -o myOrg
```

Read the `outputs` array (ignore `inputs` — that is `accountId`, the tool input). Map each `type`:

| output `name` | Actions API `type` | CLT `lightning:type` |
|---|---|---|
| status | STRING | `lightning__textType` |
| message | STRING | `lightning__textType` |
| accountId | ID | `lightning__textType` |
| accountName | STRING | `lightning__textType` |
| accountDescription | STRING | `lightning__textType` |
| accountIndustry | STRING | `lightning__textType` |
| accountPhone | STRING | `lightning__textType` |
| accountWebsite | STRING | `lightning__textType` |
| contactCount | INTEGER | `lightning__integerType` |
| opportunityCount | INTEGER | `lightning__integerType` |
| largestOpportunityId | ID | `lightning__textType` |
| largestOpportunityName | STRING | `lightning__textType` |
| largestOpportunityAmount | DOUBLE | `lightning__numberType` |
| totalOpportunityAmount | DOUBLE | `lightning__numberType` |

`payloadFields` = the 14 rows above — identical to what the `apex` source would enumerate, but resolved from the live org without parsing source or filtering the request/helper classes.

> If any output had `maxOccurs > 1`, it would be a list — render it as a collection (`lightning__listType` + `items` element type in the widget schema, iterated with `forEach`), never drop it. See `references/mcp-tool-output-discovery.md` ("Nested-object and list payload fields").

## Phase 3 — Build plan (abridged)

```text
MCP Tool Widget Build Plan: getAccountSummaryWidget

PLAN: Render the GetAccountSummary MCP tool output as an account-summary card.

TOOL / SOURCE:
  Tool API name: getAccountSummary
  Payload source: action: Actions REST describe of GetAccountSummaryTest

LIGHTNING TYPES:
  Response CLT:  getAccountSummaryResponse
  Envelope CLT: getAccountSummary
    Renderer (default, bundle root): .../lightningTypes/getAccountSummary/renderer.json
    Envelope: actionName (text), isSuccess (boolean), outputValues (c__getAccountSummaryResponse)

WIDGET: getAccountSummaryWidget
  Renderer binding: each attribute → {!$attrs.outputValues.<field>}

GENERATION ORDER: response CLT → widget → envelope CLT
```

Proceed unless the next reply pushes back.

## Phases 4–5

Generation and validation are identical to the `apex` walkthrough (`apex-invocable-source-prompt.md`), since both produce the same `payloadFields`. In `field-trace`, `INVOCABLE_FIELDS` comes from `jq -r '.outputs[].name'` on the describe rather than a `grep` of the `.cls`.
