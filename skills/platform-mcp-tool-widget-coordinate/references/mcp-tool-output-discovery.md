# MCP Tool Output Discovery

Phase 2 resolves the payload shape that defines the response CLT and the widget schema. There are three sources, in order of preference: an invocable action API name (`action`), a pasted tool-output sample (`sample`), or an Apex Invocable class (`apex`).

---

| Source | Use when | Authority |
|---|---|---|
| `action` | An **invocable action API name** is known — directly, or from a class name that resolves to one. **Preferred.** | The org's Actions REST API describes the action's typed outputs directly — it already excludes the request wrapper and private helpers. |
| `sample` | The describe 404s or no org is reachable, but a pasted tool-output JSON is available. | Infers types from example values. |
| `apex` | Only the Apex **class** name is known, and no org and no sample are available — fallback only, may be stale relative to what's deployed. | Parses `@InvocableVariable` fields from source. |

Prefer `action` whenever an action name (directly given, or derived from a class name that resolves to a single invocable action) and an authenticated org are available — it is the same schema the platform itself exposes, so it needs no request/helper filtering and gives real field types. Fall back to `sample`, then `apex`.

---

## `action` — resolve from the invocable action name (preferred)

The Salesforce **Actions REST API** describes any custom Apex invocable action, including its output variables and their types. This is authoritative: the `outputs` it returns are exactly the `@InvocableVariable` fields on the response class — the request wrapper and private helper classes never appear.

### 1. Confirm the action API name

For an Apex invocable action the action API name is the **Apex class name** that declares the `@InvocableMethod` (e.g. `GetAccountSummaryTest`), not the method label. If the user gave a label ("Get Account Summary") resolve it to the class name — the class name is what the endpoint path uses.

### 2. Describe the action

```bash
sf api request rest '/services/data/v63.0/actions/custom/apex/<ActionApiName>' -o <org>
```

`<ActionApiName>` is the Apex class name. Use the org's API version (`v63.0` here — match `sourceApiVersion` in `sfdx-project.json` or the org's max). If the org alias is the default, `-o <org>` may be omitted. (`sf api request rest ...` is the form used elsewhere in this repo; `sf org api request rest ...` is an equivalent alias.)

To list all custom Apex actions first (when the exact name is unknown) — the action names are under `.actions[].name`:

```bash
sf api request rest '/services/data/v63.0/actions/custom/apex' -o <org> | jq -r '.actions[].name'
```

If the describe returns 404 / `NOT_FOUND`, the action is not deployed or is not exposed as a custom Apex action — fall back to `sample` (a pasted tool-output JSON) if one is available, else `apex` (parse the class), and surface the miss.

### 3. Read the `outputs` array

The describe response has an `outputs` array. Each entry describes one payload field:

```json
{
  "outputs": [
    { "name": "accountName",  "label": "Account Name",  "type": "STRING",  "maxOccurs": 1 },
    { "name": "contactCount", "label": "Contact Count", "type": "INTEGER", "maxOccurs": 1 },
    { "name": "totalOpportunityAmount", "label": "Total Opportunity Amount", "type": "DOUBLE", "maxOccurs": 1 }
  ],
  "inputs": [ { "name": "accountId", "type": "ID", "required": true } ]
}
```

- **Use `outputs` only.** `inputs` is the tool input (the request wrapper) — exclude it, exactly as `apex` excludes the request class.
- `name` → the CLT/widget property key. `label` → the property `title`.
- A field with `maxOccurs > 1` is a **collection** (list). For the beta, surface it to the user in the build plan — the widget renders a single response, and list payloads need a nested item CLT (out of scope for the default flow).
- An entry with **`"type": null` and an `"apexClass"` key instead** (e.g. `{ "name": "flightInfo", "type": null, "apexClass": "SearchFlightsAction$Flight", "maxOccurs": 1 }`) is **not missing data to default to text** — it is the describe's encoding for a field typed as another Apex class. `$` separates the outer class from the inner class, matching the `@apexClassType/<ns>__<OuterClass>$<InnerClass>` convention used elsewhere in this skill. This is the same case as a `List<ApexClass>`/nested-object field from the other two sources — see "Nested-object payload fields" below; the Actions REST API describe never exposes that class's own leaf fields, so retrieving/reading the Apex class named in `apexClass` (via `apex` §1/§3) is the correct next step, not a fallback away from `action`.

Extract the field list with `jq` (do NOT wrap in `$()`):

```bash
sf api request rest '/services/data/v63.0/actions/custom/apex/<ActionApiName>' -o <org> \
  | jq -r '.outputs[] | "\(.name)\t\(.type)"'
```

### 4. Map Actions-API `type` → CLT `lightning:type`

| Actions API `type` | CLT `lightning:type` |
|---|---|
| `STRING`, `TEXTAREA`, `PICKLIST`, `ID`, `REFERENCE`, `EMAIL`, `PHONE`, `URL` | `lightning__textType` |
| `INTEGER`, `INT`, `LONG` | `lightning__integerType` |
| `DOUBLE`, `DECIMAL`, `CURRENCY`, `PERCENT` | `lightning__numberType` |
| `BOOLEAN` | `lightning__booleanType` |
| `DATE` | `lightning__dateType` |
| `DATETIME` | `lightning__dateTimeType` |

Casing varies by API version (some return `Int`/`Double`, some `INTEGER`/`DOUBLE`) — match case-insensitively. An unrecognized `type` defaults to `lightning__textType`; note the assumption in the build plan.

> **Widget schema vs CLT schema type vocabulary** (applies to every source). The response CLT uses `lightning__integerType` for integers. The widget `schema.json` (per `platform-widget-generate`) has no integer type — all numerics are `lightning__numberType`. So integer fields are `lightning__integerType` in the *response CLT* but `lightning__numberType` in the *widget* schema. Do not copy CLT leaf types verbatim into the widget schema. Renderer bindings are strings and type-agnostic.

---

## `sample` — parse from a pasted tool-output JSON (fallback)

Use when the action describe 404s or no org is reachable, but a pasted tool-output sample is available.

Given a pasted envelope sample, read the `outputValues` object and infer each field's type from its value:

| JSON value | CLT `lightning:type` |
|---|---|
| string | `lightning__textType` |
| integer (no fraction) | `lightning__integerType` |
| number (fractional) | `lightning__numberType` |
| boolean | `lightning__booleanType` |

Confirm the envelope keys (`actionName`, `isSuccess`, `outputValues`) against the sample. If the sample nests the payload further (e.g. `outputValues.data.<field>`), the response CLT and the renderer bindings must reflect that extra level (`{!$attrs.outputValues.data.<field>}`) — surface this in the build plan, because it changes every binding.

---

## `apex` — parse the Invocable class (fallback)

Use when no org is reachable and no sample is available, but the `.cls` is in the project.

### 1. Locate the class

Search the local project first: `<pkgDir>/classes/<ClassName>.cls` where `<pkgDir>` = `<packageDirectories[].path>/main/default`. If absent, retrieve from the org:

```bash
sf project retrieve start --metadata ApexClass:<ClassName>
```

If it exists nowhere, STOP and surface — the payload shape cannot be enumerated.

### 2. Identify the response class

The Invocable method is annotated `@InvocableMethod` and returns `List<ResponseType>`. The **response class** is that element type.

```apex
@InvocableMethod(label='Get Account Summary')
global static List<GetAccountSummaryResponse> getAccountSummary(
    List<GetAccountSummaryRequest> requests
) { ... }
```

- Response class = `GetAccountSummaryResponse` (the `List<...>` element type). **This is the payload source.**
- Request class = `GetAccountSummaryRequest` (the parameter element type). **Excluded** — it is the tool input, not output.
- Private helper classes (e.g. `private class OpportunityMetrics`) are **excluded** — not part of the invocable's externally visible schema. The Apex author signals this with `private`; respect it.

### 3. Enumerate `@InvocableVariable` fields

Read the response class block and list every field annotated `@InvocableVariable`. These become the response CLT `properties` and the widget schema properties (1:1).

```bash
# Print the response class field declarations. Do NOT wrap in $().
echo "INVOCABLE_FIELDS:"
grep -A1 '@InvocableVariable' <pkgDir>/classes/<ClassName>.cls \
  | grep -oE '(public|global)\s+[A-Za-z0-9_<>,\s]+\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;' \
  | sed -E 's/.*\s([a-zA-Z_][a-zA-Z0-9_]*)\s*;/\1/' \
  | sort -u
```

If the grep misses multi-line annotations, read the `.cls` with the Read tool and list fields manually — but do not skip enumeration. Scope the enumeration to the **response class block only**; do not pick up `@InvocableVariable` fields from the request class.

### 4. Map Apex → CLT `lightning:type`

| Apex type | CLT `lightning:type` |
|---|---|
| `String`, `Id` | `lightning__textType` |
| `Integer`, `Long` | `lightning__integerType` |
| `Decimal`, `Double` | `lightning__numberType` |
| `Boolean` | `lightning__booleanType` |
| `Date` | `lightning__dateType` |
| `Datetime` | `lightning__dateTimeType` |

---

## Nested-object payload fields (applies to every source above)

The mapping tables above (Actions-API `type`, Apex type, JSON value/schema `type`) cover **primitive** fields. A field can also be typed as **another Apex class** instead of a primitive — e.g. `GetFlightDetailsAction.FlightDetailsResponse.flightInfo`, typed `SearchFlightsAction.Flight`. This is a second, additive branch — check every payload field against it, regardless of which of the three sources produced the field list:

- **Actions API**: an output entry with `"type": null` and an `"apexClass": "<OuterClass>$<InnerClass>"` key, rather than a primitive `STRING`/`INTEGER`/etc. `type` (see step 3 above).
- **`apex`**: an `@InvocableVariable` field whose declared type is not `String`/`Id`/`Integer`/`Long`/`Decimal`/`Double`/`Boolean`/`Date`/`Datetime` but another Apex class.
- **`sample`**: a property whose JSON value/schema `type` is `"object"` (not a primitive).

**Never** model such a field as `{"type":"object"}` (opaque, unrenderable) or inline it as a nested `lightning__objectType` (rejected by the CLT metaschema — same rule as the envelope↔response relationship). Instead:

1. Type the response CLT property as `"@apexClassType/<ns>__<OuterClass>$<InnerClass>"` (e.g. `"@apexClassType/c__SearchFlightsAction$Flight"`) — the same convention `platform-custom-lightning-type-generate` documents for Apex-backed CLTs.
2. Enumerate the referenced Apex class's own fields (its own `@InvocableVariable`/public members) — these become the widget's leaf properties. The object field itself never appears on the widget.
3. Bind the renderer one level deeper: `{!$attrs.outputValues.<objectField>.<leaf>}` (e.g. `{!$attrs.outputValues.flightInfo.flightId}`), not `{!$attrs.outputValues.<objectField>}`.
4. A field typed `List<ApexClass>` (a list of nested objects, not a single one) is out of scope for the beta single-response flow — surface it in the build plan like a `maxOccurs > 1` scalar rather than emitting a schema for it.

See `references/two-clt-modeling.md` ("Nested-object payload fields") for the worked JSON, and `examples/nested-object-source-prompt.md` for the full end-to-end walkthrough.

## Output of Phase 2

`payloadFields` — an ordered list of `{ name, title, lightning:type }` describing the response payload (primitive fields), plus any nested-object fields resolved to `@apexClassType/...` per above. This drives:

- the **response CLT** `properties` (CLT type vocabulary, `lightning__integerType` allowed, `@apexClassType/...` for nested-object fields),
- the **widget schema** `properties.attributes.properties` (widget type vocabulary, numerics → `lightning__numberType`; nested-object fields flattened to their leaf properties),
- the **renderer** attribute bindings (`{!$attrs.outputValues.<name>}` for primitives, `{!$attrs.outputValues.<objectField>.<leaf>}` for nested-object leaves).

Whichever source produced the fields, record it in the build plan so the reviewer knows whether the schema came from the live org (`action`), source (`apex`), or an example (`sample`).
