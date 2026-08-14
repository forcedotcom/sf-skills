# Example: single nested-object payload field, discovered from the IA describe

A complete walkthrough for the case where an Invocable Action output is itself **another Apex class** —
a **single nested object** (`maxOccurs: 1`). **The Invocable Action (IA) describe is the source of
truth**; the Apex class is read only to enumerate the referenced class's own leaf fields. This is the
second, additive payload shape alongside the flat-primitive shape in `apex-invocable-source-prompt.md` —
read `references/mcp-tool-output-discovery.md` ("Nested-object and list payload fields") and
`references/two-clt-modeling.md` ("Nested-object and list payload fields") first. The **list** shapes
(top-level list, list-inside-wrapper) are in the companion example `nested-object-list-source-prompt.md`.

> **The skill never modifies the Apex.** The describe's `apexClass` + `maxOccurs` tell you the shape;
> reading the referenced class is a read-only enumeration step, not a reshape.

---

## Single nested object (`maxOccurs: 1`)

### The prompt

> I have an MCP server tool backed by the `GetFlightDetailsAction` Apex invocable action. Build a
> widget that renders its output as a flight details card.

### Phase 1 — Input selection

- Source: `action` — the prompt names an Apex Invocable, so describe it through the Actions REST API
  (`/services/data/v<APIVER>/actions/custom/apex/GetFlightDetailsAction`). This is the source of truth
  for the output shape; the `.cls` is read later only to enumerate the referenced class's leaves.
- Tool API name: `getFlightDetails` (from the class name `GetFlightDetailsAction`, stripping the
  trailing `Action` suffix and lower-camelCasing — see the naming convention in
  `references/two-clt-modeling.md`).

### Phase 2 — Payload discovery (from the describe)

The Actions describe returns a scalar sibling alongside the single nested-object output:

```jsonc
// GET /services/data/v67.0/actions/custom/apex/GetFlightDetailsAction  →  .outputs[]
[
  { "name": "searchStatus", "type": "STRING", "maxOccurs": 1 },
  { "name": "flightInfo", "type": null, "apexClass": "SearchFlightsAction$Flight", "maxOccurs": 1 }
]
```

- `searchStatus` is a **flat primitive** (`STRING`) → `lightning__textType`, bound two segments deep. Flat scalars and a single nested object coexist in one response; handle each per its own branch.
- `flightInfo`: `type: null` + `apexClass` set + `maxOccurs: 1` = a **single nested object** (not a describe gap, not a list).
- The nested output's own leaf fields are **not** in the describe. Read the named class
  (`SearchFlightsAction.Flight`) and enumerate its **public / `@AuraEnabled`** members — an
  inner/referenced class is not gated by `@InvocableVariable` (that gates only the top-level response
  class). These become the widget's flat leaf properties. **Never ignore any property.**

```apex
public class Flight {
    @InvocableVariable public String flightId;
    @InvocableVariable public String origin;
    @InvocableVariable public String destination;
    @InvocableVariable public String departureTime;
    @InvocableVariable public String arrivalTime;
    @InvocableVariable public Long   price;
}
```

| Leaf field | Apex type | widget `lightning:type` |
|---|---|---|
| flightId | String | `lightning__textType` |
| origin | String | `lightning__textType` |
| destination | String | `lightning__textType` |
| departureTime | String | `lightning__textType` |
| arrivalTime | String | `lightning__textType` |
| price | Long | `lightning__numberType` |

`payloadFields` (from describe) = 2 fields: `searchStatus` (flat `STRING`) + `flightInfo` (Apex-class-typed → nested-object branch).
`payloadFields` (flattened, for the widget) = `searchStatus` + the 6 leaf rows above (7 total).

### Phase 3 — Build plan (abridged)

```text
MCP Tool Widget Build Plan: getFlightDetailsWidget

PLAN: Render the GetFlightDetails MCP tool output as a flight-details card.

TOOL / SOURCE:
  Tool API name: getFlightDetails
  Payload source: Actions describe of Apex Invocable GetFlightDetailsAction
  Outputs: searchStatus (STRING, maxOccurs 1 → flat scalar) + flightInfo (apexClass SearchFlightsAction$Flight, maxOccurs 1 → single nested object)

LIGHTNING TYPES:
  Response CLT:  getFlightDetailsResponse
    Properties: searchStatus → "lightning__textType"; flightInfo → "@apexClassType/c__SearchFlightsAction$Flight"   # nested-object field, NOT {"type":"object"}
  Envelope CLT: getFlightDetails
    Renderer (default, bundle root): .../lightningTypes/getFlightDetails/renderer.json
    Envelope: actionName (text), isSuccess (boolean), outputValues (c__getFlightDetailsResponse)

WIDGET: getFlightDetailsWidget
  Schema: searchStatus (flat scalar) + flightInfo's 6 leaf fields (flightId, origin, destination, departureTime, arrivalTime, price)
  Renderer binding: searchStatus → {!$attrs.outputValues.searchStatus} (two segments); each flightInfo leaf → {!$attrs.outputValues.flightInfo.<leaf>} (three segments)

GENERATION ORDER: response CLT → widget → envelope CLT
```

Proceed unless the next reply pushes back.

### Phase 4 — Generation order

1. **Response CLT** `getFlightDetailsResponse`:

   ```json
   {
     "title": "Get Flight Details Response",
     "description": "Response fields from the GetFlightDetailsAction invocable-action (FlightDetailsResponse)",
     "type": "object",
     "lightning:type": "lightning__objectType",
     "lightning:tags": ["mcp"],
     "unevaluatedProperties": false,
     "properties": {
       "searchStatus": {
         "title": "Search Status",
         "lightning:type": "lightning__textType"
       },
       "flightInfo": {
         "title": "Flight Info",
         "lightning:type": "@apexClassType/c__SearchFlightsAction$Flight"
       }
     }
   }
   ```

2. **Widget** `getFlightDetailsWidget` — flat schema over `searchStatus` + the 6 leaf fields (not the
   single `flightInfo` field); body binds `{!$attrs.searchStatus}`, `{!$attrs.flightId}`,
   `{!$attrs.origin}`, etc.

3. **Envelope CLT** `getFlightDetails`:

   ```json
   {
     "title": "Get Flight Details",
     "description": "Invocable-action result envelope for the GetFlightDetailsAction MCP tool",
     "type": "object",
     "lightning:type": "lightning__objectType",
     "lightning:tags": ["mcp"],
     "unevaluatedProperties": false,
     "properties": {
       "actionName": { "title": "Action Name", "lightning:type": "lightning__textType" },
       "isSuccess":  { "title": "Is Success",  "lightning:type": "lightning__booleanType" },
       "outputValues": { "title": "Output Values", "lightning:type": "c__getFlightDetailsResponse" }
     }
   }
   ```

4. **Default renderer** at `lightningTypes/getFlightDetails/renderer.json` —
   `definition: @widget/c/getFlightDetailsWidget`, each attribute bound three segments deep through
   the nested object:

   ```json
   {
     "renderer": {
       "componentOverrides": {
         "$": {
           "definition": "@widget/c/getFlightDetailsWidget",
           "attributes": {
             "searchStatus":  "{!$attrs.outputValues.searchStatus}",
             "flightId":      "{!$attrs.outputValues.flightInfo.flightId}",
             "origin":        "{!$attrs.outputValues.flightInfo.origin}",
             "destination":   "{!$attrs.outputValues.flightInfo.destination}",
             "departureTime": "{!$attrs.outputValues.flightInfo.departureTime}",
             "arrivalTime":   "{!$attrs.outputValues.flightInfo.arrivalTime}",
             "price":         "{!$attrs.outputValues.flightInfo.price}"
           }
         }
       }
     }
   }
   ```

### Phase 5 — Validation

- `clt-reference-integrity`: envelope `outputValues` → `c__getFlightDetailsResponse`, response CLT
  exists, `searchStatus` is a primitive `lightning__textType`, `flightInfo` uses
  `@apexClassType/c__SearchFlightsAction$Flight` (not a bare `{"type":"object"}`, not an inlined
  `lightning__objectType`), no `$schema`/`items` → **pass**. PROP_GROUNDING: both trace to describe outputs → **ok**.
- `renderer-wires-widget`: bundle-root renderer present, definition `@widget/c/getFlightDetailsWidget`,
  `searchStatus` bound two segments, every `flightInfo` leaf bound three segments as
  `{!$attrs.outputValues.flightInfo.<property>}` (not two, which would bind to an unresolvable object) → **pass**.
- `field-trace`: `searchStatus` (primitive) compares directly; `flightInfo` resolves to
  `@apexClassType/...` and expands to its class's leaves before comparing. INVOCABLE_FIELDS (expanded)
  = `searchStatus, flightId, origin, destination, departureTime, arrivalTime, price`. Widget properties
  match exactly; INVENTED empty; OMITTED empty → **pass**.

---

## Notes

- **Why not a single-level opaque object.** Typing an Apex-class-typed field as `{"type":"object"}`
  produces an opaque blob with no leaf fields — not renderable. The
  `@apexClassType/<ns>__<OuterClass>$<InnerClass>` reference is what actually deploys.
- **This is additive, not a replacement.** A response of all primitives still uses the flat mapping
  tables unchanged. Check each field independently — outputs can mix primitive and Apex-class-typed fields.
- **List shapes are separate.** A top-level list output or a list nested inside a wrapper is covered in
  `nested-object-list-source-prompt.md`.
