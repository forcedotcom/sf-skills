# Example: Pasted tool-output source

A complete walkthrough of the flow when the payload source is a pasted MCP tool-output JSON sample and no Apex class is available (`source = sample`).

## The prompt

> Here's what my MCP tool returns. Build a widget for it.
>
> ```json
> {
>   "actionName": "GetOrderStatus",
>   "isSuccess": true,
>   "outputValues": {
>     "orderId": "80100000ABC",
>     "orderNumber": "ORD-4471",
>     "status": "Shipped",
>     "itemCount": 3,
>     "orderTotal": 249.95,
>     "expedited": true
>   }
> }
> ```

## Phase 1 — Input selection

- Source: `sample` (the prompt pastes a tool-output envelope; no Apex class referenced).
- Tool API name: `getOrderStatus` (from `actionName`).

## Phase 2 — Payload discovery

Read `references/mcp-tool-output-discovery.md`, then parse the `outputValues` object. Infer each `lightning:type` from the JSON value:

| Field | JSON value | Inferred CLT `lightning:type` |
|---|---|---|
| orderId | `"80100000ABC"` (string) | `lightning__textType` |
| orderNumber | `"ORD-4471"` (string) | `lightning__textType` |
| status | `"Shipped"` (string) | `lightning__textType` |
| itemCount | `3` (integer) | `lightning__integerType` |
| orderTotal | `249.95` (fractional) | `lightning__numberType` |
| expedited | `true` (boolean) | `lightning__booleanType` |

Envelope keys confirmed against the sample: `actionName`, `isSuccess`, `outputValues`. **No extra nesting** — `outputValues.<field>` is flat, so bindings will be `{!$attrs.outputValues.<field>}`.

> If the sample had nested the payload one level deeper (e.g. `outputValues.data.orderId`), the response CLT would model that `data` object and every renderer binding would be `{!$attrs.outputValues.data.<field>}`. Call this out in the plan.

`payloadFields` = the 6 rows above.

## Phase 3 — Build plan (abridged)

```text
MCP Tool Widget Build Plan: getOrderStatusWidget

PLAN: Render the GetOrderStatus MCP tool output as an order-status card.

TOOL / SOURCE:
  Tool API name: getOrderStatus
  Payload source: pasted tool-output sample

LIGHTNING TYPES:
  Response CLT:  getOrderStatusResponse   (6 payload properties)
  Envelope CLT: getOrderStatus
    Renderer (default, bundle root): .../lightningTypes/getOrderStatus/renderer.json
    Envelope: actionName (text), isSuccess (boolean), outputValues (c__getOrderStatusResponse)

WIDGET: getOrderStatusWidget
  Renderer binding: each attribute → {!$attrs.outputValues.<field>}
  Properties omitted: none

GENERATION ORDER: response CLT → widget → envelope CLT
```

Proceed unless the next reply pushes back.

## Phase 4 — Generation order

1. Response CLT `getOrderStatusResponse` — `lightning__objectType`, 6 properties (numerics: `itemCount` → `lightning__integerType` in the CLT but `lightning__numberType` in the widget schema; `orderTotal` → `lightning__numberType` in both).
2. Envelope CLT `getOrderStatus` — `actionName`, `isSuccess`, `outputValues` → `c__getOrderStatusResponse`.
3. Widget `getOrderStatusWidget` — flat schema over the 6 payload fields; body binds `{!$attrs.orderNumber}` etc.
4. Default renderer at `lightningTypes/getOrderStatus/renderer.json` — `definition: @widget/c/getOrderStatusWidget`, each attribute `{!$attrs.outputValues.<field>}`.

## Phase 5 — Validation

- `clt-reference-integrity`: envelope `outputValues` → `c__getOrderStatusResponse`, response CLT exists, no `$schema`/`items` → **pass**.
- `renderer-wires-widget`: bundle-root renderer present, definition `@widget/c/getOrderStatusWidget`, all 6 bindings nested under `outputValues` → **pass**.
- `field-trace`: source is a sample, so INVOCABLE_FIELDS = `outputValues` keys; INVENTED empty, OMITTED empty → **pass**.
