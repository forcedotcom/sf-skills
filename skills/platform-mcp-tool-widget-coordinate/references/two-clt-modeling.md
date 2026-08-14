# Two-CLT Modeling for an MCP Tool Output

A custom MCP server tool backed by an Apex Invocable Action returns the platform's **invocable-action result envelope**. The real payload the tool consumer cares about lives under `outputValues`; the surrounding fields (`errors`, `sortOrder`, `version`, …) are envelope metadata and are not modeled — the envelope CLT declares only `actionName`, `isSuccess`, `outputValues`.

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

> **Response CLT properties are 1:1 with the describe outputs — never an invented wrapper.** The response CLT's top-level property names equal the describe's `outputs[].name` set (for `apex`/`sample`, the response class's `@InvocableVariable` field names). A describe with **N sibling outputs** → **N flat properties** (the `GetAccountSummary` example above; `GetLeadsList` → `leadCount`, `leads`, `message`, `status`); a describe with **one output** → **one property named after it** (`GetShipmentDetails` → `shipmentDetailsResponse`, `GetFlightDetails` → `flightInfo`). Do **not** collapse several sibling outputs into one lone property such as `leadsListResponse` — that key appears in no describe output and is unresolvable under `action` (the response-class name is never in `outputs[]`). A single-property response CLT is correct only when the describe itself returns a single output. This is enforced by `clt-reference-integrity` check 5 (`PROP_GROUNDING`).

### Nested-object and list payload fields (a second, additive case)

The example above covers a **flat** payload — every `@InvocableVariable` field is a primitive. Some invocable responses instead have a field whose type is **itself an Apex class** — either a single object (e.g. `GetFlightDetailsAction.FlightDetailsResponse.flightInfo`, typed `SearchFlightsAction.Flight`) or a **list** of them (e.g. the `GetShipmentDetails` wrapper's `shipmentDetailsResponse.statusUpdates`, typed `List<StatusUpdateResponse>`). All three shapes — flat, single-object, list-of-objects — are in scope; pick the branch per field. In every case:

- **Never** type the property as a bare `{"type":"object"}` (opaque, unrenderable, and not what deploys) and **never** inline it as a nested `lightning__objectType` (rejected by the CLT metaschema, same as the envelope↔response relationship below).

#### Single nested object

- **Do** type it as `"@apexClassType/<ns>__<OuterClass>$<InnerClass>"` — e.g. `"lightning:type": "@apexClassType/c__SearchFlightsAction$Flight"` — exactly the Apex-backed-CLT convention `platform-custom-lightning-type-generate` already documents for `@apexClassType/namespace__ClassName$InnerClass`.
- The **widget** and **renderer** then flatten through it — see the nested-binding note at the end of the "Default renderer" section below, and the full walkthroughs in `examples/nested-object-single-source-prompt.md` (single object) and `examples/nested-object-list-source-prompt.md` (lists).

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

#### List of nested objects

A `List<ApexClass>` field (an Actions-API output with `apexClass` set and `maxOccurs > 1`, or an `@InvocableVariable List<Inner>` in source) is **in scope** — a real, renderable, boundary-crossing field. It is NOT out of scope for the beta: the `content[]` single-response limit governs how many tool *results* render (one), not list *fields* inside that one result. Render it as a collection; never drop it silently.

> **A list is bindable in whichever position the describe returns it — never reshape the Apex to move it.** Two positions occur, and both bind directly: (a) a **top-level list output** — the describe returns the list as its own output entry (`apexClass` set, `maxOccurs > 1`, e.g. a flat `GetLeadsList` whose `leads` output is `maxOccurs: 2000`); the response CLT types that property **directly** as `@apexClassType/c__<Outer>$<ElementClass>` and the renderer binds it at two segments, `{!$attrs.outputValues.<listField>}`. (b) a **list inside a single wrapper object** — the describe returns ONE output (`apexClass`, `maxOccurs: 1`, e.g. `GetShipmentDetails` → `shipmentDetailsResponse`) whose class *contains* the list (`statusUpdates`); the renderer binds it at three segments, `{!$attrs.outputValues.<wrapper>.<listField>}`. See "Top-level list vs list-inside-wrapper" below. In neither case does the CLT declare a `lightning__listType`/`items` — the list-typed property is always a plain `@apexClassType/...` reference.

The rule is that **a list-typed CLT property is always a plain `@apexClassType/...` reference — the object-based response CLT never declares the list as a `lightning__listType` property itself.** The `@apexClassType` describe layer resolves the list and its element type; the list surfaces as a `lightning__listType` in the *widget* schema, not the CLT. Which class the reference names, and how deep the renderer binds, depend on the list's **position in the describe** (see "Top-level list vs list-inside-wrapper" below). Concretely:

- **Response CLT:** the list-typed property is a plain `@apexClassType` reference (never a `lightning__listType`, never `items`). For a **top-level list output** (flat `GetLeadsList` → `leads`, `maxOccurs: 2000`) the property names the **element** class directly — `leads → @apexClassType/c__GetLeadsList$LeadSummary` — and the CLT carries that property itself. For a **list inside a wrapper** (`GetShipmentDetails` → `shipmentDetailsResponse`) the CLT carries the **wrapper** property — `shipmentDetailsResponse → @apexClassType/c__GetShipmentDetails$GetShipmentDetailsResponse` — and the `List<StatusUpdateResponse>` lives inside that class (discovered by reading it, not from the describe). Either way the CLT gets **no** `lightning__listType` property.
- **Renderer:** bind the list at the depth its position dictates (NOT `.<leaf>` in either case): `{!$attrs.outputValues.<listField>}` (two segments) for a **top-level list output** (e.g. `{!$attrs.outputValues.leads}`), or `{!$attrs.outputValues.<objectField>.<listField>}` (three segments) for a **list inside a wrapper** (e.g. `{!$attrs.outputValues.shipmentDetailsResponse.statusUpdates}`). This bridges the envelope to the widget's flat `{!$attrs.<listField>}`.

How the widget bundle surfaces the list (its `lightning__listType` + `items` schema property) and iterates the items is authored and validated by `platform-widget-generate` — not by this skill.

Deployed response CLT (the list is NOT here — it rides inside the `@apexClassType` object):

```json
{
  "title": "Get Shipment Details Response",
  "description": "Payload fields returned by the GetShipmentDetails invocable action",
  "type": "object",
  "lightning:type": "lightning__objectType",
  "lightning:tags": ["mcp"],
  "unevaluatedProperties": false,
  "properties": {
    "shipmentDetailsResponse": {
      "title": "Shipment Details Response",
      "lightning:type": "@apexClassType/c__GetShipmentDetails$GetShipmentDetailsResponse"
    }
  }
}
```

Deployed renderer binding (list bound one level through the object; the widget iterates the items):

```json
{ "statusUpdates": "{!$attrs.outputValues.shipmentDetailsResponse.statusUpdates}" }
```

The widget schema property for the list (`lightning__listType` + `items`) and the widget body that iterates it are authored by `platform-widget-generate`.

#### Top-level list vs list-inside-wrapper (which position the describe returns the list in)

**The describe is the source of truth, and the list is renderable in whichever position it returns — never touch the Apex to move it.** Two positions occur in practice. They differ ONLY in renderer binding depth:

| Position | Actions describe `outputs` | Response CLT list property | Renderer binding |
|---|---|---|---|
| **Top-level list output** (e.g. flat `GetLeadsList`) | The list is its **own** output entry — `apexClass` set, `maxOccurs > 1` (e.g. `leads` → `apexClass: GetLeadsList$LeadSummary`, `maxOccurs: 2000`), beside sibling scalars | `leads` → `@apexClassType/c__GetLeadsList$LeadSummary` (the **element** class) | **Two segments:** `{!$attrs.outputValues.leads}` |
| **List inside a wrapper** (e.g. `GetShipmentDetails`) | ONE output — `shipmentDetailsResponse` · `apexClass` set · `maxOccurs: 1`; the list is a field **inside** that class (`statusUpdates`), which the describe does NOT surface | `shipmentDetailsResponse` → `@apexClassType/c__GetShipmentDetails$GetShipmentDetailsResponse` (the **wrapper** class; the list is discovered by reading it) | **Three segments:** `{!$attrs.outputValues.shipmentDetailsResponse.statusUpdates}` |

**A top-level `@apexClassType` list binds directly.** A response CLT that types a top-level list property directly as `@apexClassType/c__<Outer>$<ElementClass>`, with an envelope whose renderer binds `{!$attrs.outputValues.<listField>}` (two segments, no wrapper hop), is a valid, deployable shape. There is no need for — and the skill must not perform — any Apex reshaping (no wrapper class, no `List<Wrapper>` return-type change) to render a top-level list. The Apex is never modified by this skill.

**Typing facts:**
- A response CLT list property **must** be a plain `@apexClassType/c__<Outer>$<ElementClass>` reference. Typing it as `lightning__listType` with an `items` element type is **rejected** by the CLT metaschema (*"You can't add the items property … because the `unevaluatedProperties` keyword value is set to false"*). `items`/`lightning__listType` belong to the **widget** schema only.
- The binding depth is dictated purely by the list's position in the describe (two segments for a top-level output, three for a list inside a wrapper) — not by any transform you apply.

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
- Include only the envelope scalars the widget or the platform needs (`actionName`, `isSuccess`, and `outputValues` only). Add `message` etc. only when rendered. `outputValues` is the load-bearing field the renderer bridges through; the widget renders the payload under it, never the envelope metadata (`actionName`/`isSuccess`).

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

**Nested-object response fields bind one level deeper.** When a response field is itself a single Apex-class reference (the `flightInfo` case above), the widget flattens to that class's own leaf fields, and the renderer binding goes two levels deep: `{!$attrs.outputValues.flightInfo.flightId}`, `{!$attrs.outputValues.flightInfo.origin}`, etc. — `outputValues.<objectField>.<leaf>`, not `outputValues.<objectField>` alone (which would bind the widget to an unresolvable object, not a renderable leaf).

**List-of-object response fields bind the list, not the leaves — at a depth set by the list's position.** A `List<ApexClass>` returned as a **top-level output** (flat `GetLeadsList` → `leads`) binds at two segments — `{!$attrs.outputValues.leads}`. A `List<ApexClass>` that lives **inside a wrapper object** (`GetShipmentDetails` → `shipmentDetailsResponse.statusUpdates`) binds at three — `{!$attrs.outputValues.shipmentDetailsResponse.statusUpdates}`. Do NOT append `.<leaf>` to the list binding in the renderer — there is no single leaf to bind at the list level; the widget (authored by `platform-widget-generate`) iterates the list and renders each item's leaves. The renderer binding depth is set by the describe position.

> **The list binding must still go through the renderer's `outputValues` path.** A common failure is a widget that iterates the list correctly but whose *renderer* binds the list flat — `"leads": "{!$attrs.leads}"` instead of `"leads": "{!$attrs.outputValues.<wrapper>.leads}"`. The flat renderer binding resolves against the envelope root, where the payload does not live, so the widget renders "No data available" even though the widget body is correct. Every list is wired through the `outputValues` bridge.

> **A renderer attribute CAN bind a top-level `@apexClassType` list directly.** The bindable right-hand paths are: a primitive (`outputValues.<field>`), a **top-level `@apexClassType` list** (`outputValues.<listField>`, e.g. `outputValues.leads` — two segments), or a leaf/list reached *through* one `@apexClassType` wrapper (`outputValues.<wrapper>.<leaf>` / `outputValues.<wrapper>.<listField>` — three segments). There is no "top-level `@apexClassType` list is unbindable" constraint, and the skill must never reshape the Apex to a wrapper to render a top-level list. Bind at the depth the describe's position dictates and leave the Apex untouched.

## Why two CLTs and not one

The platform binds the tool's output rendition to the CLT whose shape matches the **tool output schema** — that is the envelope, not the response. So the renderer (and thus the widget assignment) must live in the envelope CLT. But the widget wants a flat attribute contract, so the renderer flattens the nesting via `outputValues.`. The response CLT exists purely to *type* the `outputValues` node so those nested paths resolve. Inlining the response fields as a nested `lightning__objectType` inside the envelope is rejected by the CLT metaschema — hence a separate, referenced response CLT.

## The widget schema is generic, not CLT-derived

The widget schema is a standalone contract: `properties.attributes.properties` built from the **response field list** (name + primitive `lightning:type`), nothing more. It happens to share the field set with the response CLT for this flow, but it is not typed against the CLT, does not carry `unevaluatedProperties`, and would look identical if the same field list arrived from any other source `platform-widget-generate` supports. The widget schema and body know nothing about the envelope. The widget binds `{!$attrs.accountName}` (flat); only the renderer knows the field actually lives at `outputValues.accountName`. This keeps the widget reusable and lets `platform-widget-generate` author it exactly as it would for any flat response.
