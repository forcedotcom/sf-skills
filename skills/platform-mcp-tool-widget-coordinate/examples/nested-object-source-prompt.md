# Example: Nested-object payload field (Apex-class-typed response field)

A complete walkthrough of the flow when one `@InvocableVariable` field on the response class is
itself **another Apex class**, not a primitive (`source = apex`, nested-object branch). This is the
second, additive payload shape alongside the flat-primitive shape in `apex-invocable-source-prompt.md`
— read `references/mcp-tool-output-discovery.md` ("Nested-object payload fields") and
`references/two-clt-modeling.md` ("Nested-object payload fields (a second, additive case)") first.

## The prompt

> I have an MCP server tool backed by the `GetFlightDetailsAction` Apex invocable action. Build a
> widget that renders its output as a flight details card.

## Phase 1 — Input selection

- Source: `apex` (the prompt names an Apex Invocable class; no org describe needed for this walkthrough).
- Tool API name: `getFlightDetails` (from the class name `GetFlightDetailsAction`, stripping the
  trailing `Action` suffix and lower-camelCasing — see the naming convention in
  `references/two-clt-modeling.md`).

## Phase 2 — Payload discovery

Read `references/mcp-tool-output-discovery.md`, then locate `.../classes/GetFlightDetailsAction.cls`.

The invocable method:

```apex
@InvocableMethod(label='Get Flight Details' description='Returns flight details based on input ID, Origin, and Destination')
public static List<FlightDetailsResponse> getFlightDetails(List<FlightDetailsRequest> requests) { ... }

public class FlightDetailsResponse {
    @InvocableVariable(label='Flight Details')
    public SearchFlightsAction.Flight flightInfo;
}
```

- Response class = `FlightDetailsResponse` (the `List<...>` element type) → **payload source**.
- Request class = `FlightDetailsRequest` → excluded (tool input).
- The single `@InvocableVariable` field, `flightInfo`, is declared `SearchFlightsAction.Flight` —
  **another Apex class**, not `String`/`Integer`/etc. This is the nested-object branch: it does not
  go in the primitive Apex→CLT mapping table.

Enumerate the referenced class (`SearchFlightsAction.Flight`) for its own `@InvocableVariable`
leaf fields — these become the widget's flat properties:

```apex
public class Flight {
    @InvocableVariable public String flightId;
    @InvocableVariable public String origin;
    @InvocableVariable public String destination;
    @InvocableVariable public String departureTime;
    @InvocableVariable public String arrivalTime;
    @InvocableVariable public Long price;
}
```

| Leaf field | Apex type | CLT / widget `lightning:type` |
|---|---|---|
| flightId | String | `lightning__textType` |
| origin | String | `lightning__textType` |
| destination | String | `lightning__textType` |
| departureTime | String | `lightning__textType` |
| arrivalTime | String | `lightning__textType` |
| price | Long | `lightning__numberType` (widget uses `lightning__numberType` for all numerics; the response CLT would use `lightning__integerType` if this leaf were typed directly on the response CLT — but it isn't, since it's flattened through `@apexClassType`, see below) |

`payloadFields` (top-level) = 1 field: `flightInfo`, typed as an Apex class → nested-object branch.
`payloadFields` (flattened, for the widget) = the 6 leaf rows above.

## Phase 3 — Build plan (abridged)

```text
MCP Tool Widget Build Plan: getFlightDetailsWidget

PLAN: Render the GetFlightDetails MCP tool output as a flight-details card.

TOOL / SOURCE:
  Tool API name: getFlightDetails
  Payload source: Apex Invocable class GetFlightDetailsAction
  Response class FQN: GetFlightDetailsAction.FlightDetailsResponse

LIGHTNING TYPES:
  Response CLT:  getFlightDetailsResponse
    Properties: flightInfo → "@apexClassType/c__SearchFlightsAction$Flight"   # nested-object field, NOT {"type":"object"}
  Envelope CLT: getFlightDetails
    Renderer (default, bundle root): .../lightningTypes/getFlightDetails/renderer.json
    Envelope: actionName (text), isSuccess (boolean), outputValues (c__getFlightDetailsResponse)

WIDGET: getFlightDetailsWidget
  Schema: flattened to flightInfo's 6 leaf fields (flightId, origin, destination, departureTime, arrivalTime, price)
  Renderer binding: each attribute → {!$attrs.outputValues.flightInfo.<leaf>}   # two levels deep, not one
  Properties omitted: none

GENERATION ORDER: response CLT → widget → envelope CLT
```

Proceed unless the next reply pushes back.

## Phase 4 — Generation order

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
       "flightInfo": {
         "title": "Flight Info",
         "lightning:type": "@apexClassType/c__SearchFlightsAction$Flight"
       }
     }
   }
   ```

2. **Widget** `getFlightDetailsWidget` — flat schema over the 6 leaf fields (not the single
   `flightInfo` field); body binds `{!$attrs.flightId}`, `{!$attrs.origin}`, etc.

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
   `definition: @widget/c/getFlightDetailsWidget`, each attribute bound two levels deep through the
   nested object:

   ```json
   {
     "renderer": {
       "componentOverrides": {
         "$": {
           "definition": "@widget/c/getFlightDetailsWidget",
           "attributes": {
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

## Phase 5 — Validation

- `clt-reference-integrity`: envelope `outputValues` → `c__getFlightDetailsResponse`,
  response CLT exists, `flightInfo` uses `@apexClassType/c__SearchFlightsAction$Flight` (not a
  bare `{"type":"object"}` and not an inlined `lightning__objectType`), no `$schema`/`items` →
  **pass**.
- `renderer-wires-widget`: bundle-root renderer present, definition `@widget/c/getFlightDetailsWidget`,
  every widget property bound two levels deep as `{!$attrs.outputValues.flightInfo.<property>}` (not
  one level, which would bind to an unresolvable object) → **pass**.
- `field-trace`: INVOCABLE_FIELDS (top-level, per the gate's literal definition) = `flightInfo` —
  a single nested-object field, not a primitive. Because it resolves to `@apexClassType/...` (see
  `clt-reference-integrity` above), it expands to its referenced class's own leaf fields before
  comparing against the widget: `flightId, origin, destination, departureTime, arrivalTime, price`.
  Widget properties match this expanded leaf set exactly; INVENTED empty; OMITTED empty → **pass**.

## Notes

- **Why not a single-level CLT.** Typing `flightInfo` as `{"type":"object"}` on the response CLT
  produces an opaque blob with no leaf fields — not renderable, and rejected by intent even where the
  CLT metaschema would technically accept a generic object. The `@apexClassType/<ns>__<OuterClass>$<InnerClass>`
  reference is what actually deploys (verified against a hand-fixed, successfully deployed bundle).
- **This is additive, not a replacement.** A response class with only primitive `@InvocableVariable`
  fields (the `AccountSummary`/`GetOrderStatus` examples) still uses the flat mapping tables
  unchanged. Check each field independently — a response class can mix primitive and Apex-class-typed
  fields.
- **`List<ApexClass>` fields** (e.g. `SearchFlightsAction.FlightSearchResponse.availableFlights`, a
  `List<Flight>`) are out of scope for this beta single-response flow — surface them in the build
  plan the same way a `maxOccurs > 1` scalar is surfaced, rather than emitting a schema for them.
