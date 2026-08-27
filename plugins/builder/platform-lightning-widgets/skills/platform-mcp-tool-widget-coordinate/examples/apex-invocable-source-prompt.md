# Example: Apex Invocable source

A complete walkthrough of the flow when the payload source is an Apex `@InvocableMethod` class that already exists in the project (`source = apex`). This is the fallback source — when the action is deployed to a reachable org, prefer `action` (describe it by name via the Actions REST API; see `action-name-source-prompt.md`). Use `apex` when no org is reachable or the describe 404s.

## The prompt

> I have an MCP server tool backed by the `GetAccountSummaryTest` Apex invocable action. Build a widget that renders its output so the account summary shows up as a rich card.

## Phase 1 — Input selection

- Source: `apex` (the prompt names an Apex Invocable class).
- Tool API name: `getAccountSummary` (from the class / invocable label `Get Account Summary`).

## Phase 2 — Payload discovery

Read `references/mcp-tool-output-discovery.md`, then locate `.../classes/GetAccountSummaryTest.cls`.

The invocable method:

```apex
@InvocableMethod(label='Get Account Summary')
global static List<GetAccountSummaryResponse> getAccountSummary(
    List<GetAccountSummaryRequest> requests
) { ... }
```

- Response class = `GetAccountSummaryResponse` (the `List<...>` element type) → **payload source**.
- Request class = `GetAccountSummaryRequest` → excluded (tool input).
- `private class OpportunityMetrics` → excluded (internal helper, not part of the invocable schema).

Enumerate `@InvocableVariable` fields on `GetAccountSummaryResponse` and map to CLT types:

| Field | Apex type | CLT `lightning:type` |
|---|---|---|
| status | String | `lightning__textType` |
| message | String | `lightning__textType` |
| accountId | Id | `lightning__textType` |
| accountName | String | `lightning__textType` |
| accountDescription | String | `lightning__textType` |
| accountIndustry | String | `lightning__textType` |
| accountPhone | String | `lightning__textType` |
| accountWebsite | String | `lightning__textType` |
| contactCount | Integer | `lightning__integerType` |
| opportunityCount | Integer | `lightning__integerType` |
| largestOpportunityId | Id | `lightning__textType` |
| largestOpportunityName | String | `lightning__textType` |
| largestOpportunityAmount | Decimal | `lightning__numberType` |
| totalOpportunityAmount | Decimal | `lightning__numberType` |

`payloadFields` = the 14 rows above.

## Phase 3 — Build plan (abridged)

```text
MCP Tool Widget Build Plan: getAccountSummaryWidget

PLAN: Render the GetAccountSummary MCP tool output as an account-summary card.

TOOL / SOURCE:
  Tool API name: getAccountSummary
  Payload source: Apex Invocable class GetAccountSummaryTest
  Response class FQN: GetAccountSummaryTest.GetAccountSummaryResponse

LIGHTNING TYPES:
  Response CLT:  getAccountSummaryResponse   (14 payload properties)
  Envelope CLT: getAccountSummary
    Renderer (default, bundle root): .../lightningTypes/getAccountSummary/renderer.json
    Envelope: actionName (text), isSuccess (boolean), outputValues (c__getAccountSummaryResponse)

WIDGET: getAccountSummaryWidget
  Renderer binding: each attribute → {!$attrs.outputValues.<field>}

GENERATION ORDER: response CLT → widget → envelope CLT
```

Proceed unless the next reply pushes back.

## Phase 4 — Generation order

1. Response CLT `getAccountSummaryResponse` — `lightning__objectType`, all 14 `payloadFields` (1:1 with the response class's `@InvocableVariable` fields — the response CLT always models the complete response, including `status`/`message`).
2. Envelope CLT `getAccountSummary` — `actionName`, `isSuccess`, `outputValues` → `c__getAccountSummaryResponse`.
3. Widget `getAccountSummaryWidget` — flat schema over all 14 payload fields; body binds `{!$attrs.accountName}` etc.
4. Default renderer at `lightningTypes/getAccountSummary/renderer.json` — `definition: @widget/c/getAccountSummaryWidget`, each attribute `{!$attrs.outputValues.<field>}`.

## Phase 5 — Validation

- `clt-reference-integrity`: envelope `outputValues` → `c__getAccountSummaryResponse`, response CLT exists, no `$schema`/`items` → **pass**.
- `renderer-wires-widget`: bundle-root renderer present, definition `@widget/c/getAccountSummaryWidget`, every widget prop bound as `{!$attrs.outputValues.<prop>}` → **pass**.
- `field-trace`: INVENTED empty; OMITTED empty (all 14 fields rendered) → **pass**.
