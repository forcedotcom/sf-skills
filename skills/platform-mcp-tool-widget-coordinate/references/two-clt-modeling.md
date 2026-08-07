# Two-CLT Modeling for an MCP Tool Output

A custom MCP server tool backed by an Apex Invocable Action returns the platform's **invocable-action result envelope**. The real payload the tool consumer cares about lives under `outputValues`; the surrounding fields (`actionName`, `isSuccess`, `errors`, `sortOrder`, `version`, …) are envelope metadata.

To render this with an HXL widget we model it as **two object-based CLTs** and wire them with a renderer that bridges the nesting. Both are ordinary CLTs of equal standing — nothing in the platform or the metaschema distinguishes an "envelope type" from a "response type." The only reason two files exist is that one CLT (the envelope) must reference the other (the response) by name via `c__<name>`, and a CLT cannot reference itself — so the two need distinct deployed names, nothing more. Don't invent a role-label pair for the two CLTs themselves ("Payload CLT"/"Envelope CLT", "Outer CLT"/"Inner CLT") — name and describe each by what it actually models (see below), and in prose refer to them by that same identifier: "the `<toolApiName>` envelope" / "the `<toolApiName>Response`". ("Payload" and "response" remain fine as ordinary words for the data itself — e.g. "response fields", "the payload the tool consumer cares about" — the rule is about not naming or labeling the *CLTs* by an invented role.)

## Naming convention

| Artifact | Convention | Example |
|---|---|---|
| Envelope CLT | `<toolApiName>` | `getFlightDetails` |
| Response CLT | `<toolApiName>Response` | `getFlightDetailsResponse` |
| Widget | `<toolApiName>Widget` | `getFlightDetailsWidget` |

- `<toolApiName>` is derived **deterministically from the Apex class / Invocable Action name**, not the label: lower-camelCase the class name and strip a trailing `Action`, `Test`, or `WidgetAction` suffix if present.
  - `AccountSummaryWidgetAction` → `accountSummary`
  - `GetFlightDetailsAction` → `getFlightDetails`
  - `GetAccountSummaryTest` → `getAccountSummary`
  - Only when no class/action name is available at all (e.g. a bare `sample` with no `actionName` resolvable to a class) fall back to camelCasing the tool/action **label** (e.g. `Get Account Summary` → `accountSummary`).
- Both CLT names are derived from the **same single `<toolApiName>`** — there is no separate naming decision to make per artifact, and no free-standing role word (no "Result", "OutputValues", "Payload", "Envelope", and no `_CLT` suffix either — a Lightning Type is identified by living under `lightningTypes/`, not by a suffix on its name). `Response` is not a role label; it is literally what the class is (the Invocable Action's declared `List<...Response>` return-element type) — the same word the Apex source itself already uses (e.g. `GetAccountSummaryResponse`, `FlightDetailsResponse`).
- The envelope CLT is *structurally* generic but **cannot be a single shared CLT** — its `outputValues` must be typed to a tool-specific response CLT via `c__<responseCLT>`. One envelope CLT per tool.

> **Naming convention supersedes the earlier hand-verified prototype.** Two bundles were manually fixed and successfully deployed during development using an older `<toolApiName>Result` / `<toolApiName>OutputValues` naming pair — that proved the *structural* pattern (two object-based CLTs, `@apexClassType` for nested fields, two-level renderer bindings) deploys correctly. The naming convention above replaces those two suffixes; every other structural rule in this file (root keys, `unevaluatedProperties`, the `c__` reference, nested-object typing, renderer bindings) is unchanged and still matches what was verified.

## Response CLT

Object-based CLT whose `properties` are exactly the response `@InvocableVariable` fields (1:1). Root `lightning:type` is `lightning__objectType`. `platform-custom-lightning-type-generate` injects and enforces `"unevaluatedProperties": false` on every object-based CLT (its metaschema rejects a CLT without it) — this orchestrator does not fight that, it matches it in every example and every generated file. Give both CLTs a real, tool-specific `description` (never `""`) — it is what a consumer sees when picking a referenced CLT. Both CLTs also carry a root-level `"lightning:tags": ["mcp"]` — it marks the type as MCP-tool-generated per `platform-custom-lightning-type-generate/assets/primitive-types-and-constraints.md`.

```json
{
  "title": "Get Account Summary Response",
  "description": "Response fields from the GetAccountSummaryTest invocable-action (GetAccountSummaryResponse)",
  "type": "object",
  "lightning:type": "lightning__objectType",
  "lightning:tags": ["mcp"],
  "unevaluatedProperties": false,
  "properties": {
    "accountName":    { "title": "accountName",    "lightning:type": "lightning__textType" },
    "accountIndustry":{ "title": "accountIndustry","lightning:type": "lightning__textType" },
    "contactCount":   { "title": "contactCount",   "lightning:type": "lightning__integerType" },
    "totalOpportunityAmount": { "title": "totalOpportunityAmount", "lightning:type": "lightning__numberType" }
  }
}
```

### Nested-object payload fields (a second, additive case)

The example above covers a **flat** payload — every `@InvocableVariable` field is a primitive. Some invocable responses instead have a field whose type is **itself an Apex class** (e.g. `GetFlightDetailsAction.FlightDetailsResponse.flightInfo`, typed `SearchFlightsAction.Flight`). Both shapes are in scope; pick the branch per field:

- **Never** type that property as a bare `{"type":"object"}` (opaque, unrenderable, and not what deploys) and **never** inline it as a nested `lightning__objectType` (rejected by the CLT metaschema, same as the envelope↔response relationship below).
- **Do** type it as `"@apexClassType/<ns>__<OuterClass>$<InnerClass>"` — e.g. `"lightning:type": "@apexClassType/c__SearchFlightsAction$Flight"` — exactly the Apex-backed-CLT convention `platform-custom-lightning-type-generate` already documents for `@apexClassType/namespace__ClassName$InnerClass`.
- The **widget** and **renderer** then flatten through it — see the nested-binding note at the end of the "Default renderer" section below, and the full walkthrough in `examples/nested-object-source-prompt.md`.
- A field typed `List<ApexClass>` (a list of nested objects) is out of scope for the beta single-response flow — surface it in the build plan rather than emitting a schema for it, the same way a `maxOccurs > 1` scalar is surfaced.

```json
{
  "title": "Get Flight Details Response",
  "description": "Response fields from the GetFlightDetailsAction invocable-action (FlightDetailsResponse)",
  "type": "object",
  "lightning:type": "lightning__objectType",
  "lightning:tags": ["mcp"],
  "unevaluatedProperties": false,
  "properties": {
    "flightInfo": {
      "title": "Flight Info",
      "lightning:type": "@apexClassType/c__SearchFlightsAction$Flight"
    }
  }
}
```

## Envelope CLT

Object-based CLT that mimics the tool-result envelope. `outputValues` is typed to the response CLT via the referenced-CLT pattern `c__<responseCLT>` — **not** inlined as a nested `lightning__objectType` (nested object typing is rejected by the CLT metaschema; see `platform-custom-lightning-type-generate`).

```json
{
  "title": "Get Account Summary",
  "description": "Invocable-action result envelope for the GetAccountSummaryTest MCP tool",
  "type": "object",
  "lightning:type": "lightning__objectType",
  "lightning:tags": ["mcp"],
  "unevaluatedProperties": false,
  "properties": {
    "actionName":   { "title": "actionName",   "lightning:type": "lightning__textType" },
    "isSuccess":    { "title": "isSuccess",     "lightning:type": "lightning__booleanType" },
    "outputValues": { "title": "outputValues",  "lightning:type": "c__getAccountSummaryResponse" }
  }
}
```

- The `c__<responseCLT>` string is the referenced type's **registered identifier / FQN**, not its `title`. It must match the response CLT's deployed name.
- The response CLT must be deployed **before** the envelope CLT.
- Include only the envelope scalars the widget or the platform needs (`actionName`, `isSuccess`, and `outputValues` at minimum). Add `message` etc. only when rendered.

## Default renderer (in the ENVELOPE CLT)

The renderer is the **default `renderer.json` at the envelope CLT bundle root**, parallel to `schema.json` — NOT under `lightningDesktopGenAi/`. It assigns the widget and bridges the envelope nesting to the flat widget schema.

```json
{
  "renderer": {
    "componentOverrides": {
      "$": {
        "definition": "@widget/c/accountSummaryWidget",
        "attributes": {
          "accountName":    "{!$attrs.outputValues.accountName}",
          "accountIndustry":"{!$attrs.outputValues.accountIndustry}",
          "contactCount":   "{!$attrs.outputValues.contactCount}",
          "totalOpportunityAmount": "{!$attrs.outputValues.totalOpportunityAmount}"
        }
      }
    }
  }
}
```

**The binding path is the crux:** each widget attribute (left, flat) maps to the response field nested under the envelope's `outputValues` node (right) via `{!$attrs.outputValues.<field>}`. Because the envelope CLT's `outputValues` is typed to the response CLT, the runtime can resolve `outputValues.<field>` against the response CLT's `properties`.

**Nested-object response fields bind one level deeper.** When a response field is itself an Apex-class reference (the `flightInfo` case above), the widget flattens to that class's own leaf fields, and the renderer binding goes two levels deep: `{!$attrs.outputValues.flightInfo.flightId}`, `{!$attrs.outputValues.flightInfo.origin}`, etc. — `outputValues.<objectField>.<leaf>`, not `outputValues.<objectField>` alone (which would bind the widget to an unresolvable object, not a renderable leaf).

## Why two CLTs and not one

The platform binds the tool's output rendition to the CLT whose shape matches the **tool output schema** — that is the envelope, not the response. So the renderer (and thus the widget assignment) must live in the envelope CLT. But the widget wants a flat attribute contract, so the renderer flattens the nesting via `outputValues.`. The response CLT exists purely to *type* the `outputValues` node so those nested paths resolve. Inlining the response fields as a nested `lightning__objectType` inside the envelope is rejected by the CLT metaschema — hence a separate, referenced response CLT.

## The widget schema is generic, not CLT-derived

The widget schema is a standalone contract: `properties.attributes.properties` built from the **response field list** (name + primitive `lightning:type`), nothing more. It happens to share the field set with the response CLT for this flow, but it is not typed against the CLT, does not carry `unevaluatedProperties`, and would look identical if the same field list arrived from any other source `platform-widget-generate` supports. The widget schema and body know nothing about the envelope. The widget binds `{!$attrs.accountName}` (flat); only the renderer knows the field actually lives at `outputValues.accountName`. This keeps the widget reusable and lets `platform-widget-generate` author it exactly as it would for any flat response.
