# Validation Gates

The orchestrator runs only **cross-skill validations** — checks that span the two CLTs, the widget, and the renderer. Widget-bundle-internal checks (schema parses, root keys, leaf types, `{!$attrs.X}` resolution, `.uiwidget-meta.xml` well-formedness, `<UiWidgetBundle>` root, widget-type) are owned by `platform-widget-generate` and run in its own self-validation.

Run every gate below. If a hard gate fails, fix and re-run before reporting success. Warn gates are advisory.

**Shell note:** run each command verbatim and reason about its printed output. Do NOT capture into shell variables with `$(…)`, do NOT use process substitution `<(…)`, do NOT use brace expansion. Vibes' safe-shell filter blocks those patterns and prompts for manual approval even in Bypass mode. See Hard Rule 11 in the SKILL.md.

---

## Hard — block on failure

### 1. `clt-reference-integrity`

Confirms the envelope→response typing the renderer depends on.

1. **Both CLTs parse:**

   ```bash
   jq . <pkgDir>/lightningTypes/<responseCLT>/schema.json > /dev/null && echo "RESPONSE_PARSE: ok" || echo "RESPONSE_PARSE: FAIL"
   ```

   ```bash
   jq . <pkgDir>/lightningTypes/<toolCLT>/schema.json > /dev/null && echo "ENVELOPE_PARSE: ok" || echo "ENVELOPE_PARSE: FAIL"
   ```

2. **Envelope `outputValues` references the response CLT.** Print the value and compare in reasoning:

   ```bash
   jq -r '.properties.outputValues["lightning:type"]' <pkgDir>/lightningTypes/<toolCLT>/schema.json
   ```

   Expected: `c__<responseCLT>`. Match → `REFERENCE: ok`; else `REFERENCE: FAIL (got <actual>, expected c__<responseCLT>)`.

3. **Neither CLT carries a forbidden keyword.** Print any hits (empty output = clean):

   ```bash
   jq 'paths | select(.[-1] == "$schema" or .[-1] == "items")' <pkgDir>/lightningTypes/<responseCLT>/schema.json
   ```

   ```bash
   jq 'paths | select(.[-1] == "$schema" or .[-1] == "items")' <pkgDir>/lightningTypes/<toolCLT>/schema.json
   ```

   Any output → `KEYWORDS: FAIL (<path>)`; empty → `KEYWORDS: ok`.

4. **Nested-object response fields (if any) use `@apexClassType`, never a bare object or a CLT-level list.** For every response CLT property that is not a primitive leaf, print its `lightning:type`:

   ```bash
   jq -r '.properties | to_entries[] | select(.value["lightning:type"] == null or (.value["lightning:type"] | test("^lightning__(text|integer|number|boolean|date|dateTime)Type$") | not)) | "\(.key): \(.value["lightning:type"])"' <pkgDir>/lightningTypes/<responseCLT>/schema.json
   ```

   Every printed entry must be a single nested object typed `@apexClassType/<ns>__<OuterClass>$<InnerClass>`. Two FAILs:
   - A bare `{"type":"object"}` (no `lightning:type`, or a `lightning:type` of `lightning__objectType` inlined on a *property* rather than the CLT root) → `NESTED_TYPE: FAIL (<key>: <actual>)`.
   - A `lightning__listType` on a **response CLT** property → `NESTED_TYPE: FAIL (<key>: lists ride inside an @apexClassType object; the CLT must not carry a lightning__listType — see references/two-clt-modeling.md "List of nested objects")`. Lists surface in the widget schema, not the CLT.

   All entries are `@apexClassType/...` or no such properties exist → `NESTED_TYPE: ok`.

5. **Response CLT property names trace to describe outputs (no invented wrapper).** The response CLT's top-level property names MUST equal the describe's `outputs[].name` set (for `apex`/`sample`, the response class's `@InvocableVariable` field names — the same set the describe surfaces). Print both:

   ```bash
   echo "OUTPUTS:"
   sf api request rest '/services/data/v<APIVER>/actions/custom/apex/<ActionApiName>' -o <org> | jq -r '.outputs[].name' | sort -u
   echo "RESPONSE_CLT_PROPS:"
   jq -r '.properties | keys[]' <pkgDir>/lightningTypes/<responseCLT>/schema.json | sort -u
   ```

   A describe with **N sibling outputs** must yield **N flat properties** with matching names; a describe with **one output** yields **one property named after it** (`shipmentDetailsResponse`, `flightInfo`). A single property whose name is **not** among the describe outputs (e.g. `leadsListResponse` against a `leadCount`/`leads`/`message`/`status` describe) is an **invented wrapper** — it collapses N siblings into one key the describe never returns and is unresolvable under `action`. Any response CLT property name absent from the describe outputs → `PROP_GROUNDING: FAIL (<prop> not a describe output — model each sibling output as its own flat property; never collapse into an invented wrapper)`. All property names present in the outputs set → `PROP_GROUNDING: ok`.

**Result:** all ok → `pass`. Otherwise `fail (<first failing check>)`.

**Failure → fix:** the renderer's `{!$attrs.outputValues.<field>}` paths cannot resolve unless `outputValues` is typed to the response CLT. Fix the envelope CLT's `outputValues.lightning:type` to `c__<responseCLT>`, ensure the response CLT exists, and remove any `$schema` / `items` keywords.

---

### 2. `renderer-wires-widget`

Confirms the envelope CLT's default renderer assigns the widget and binds every widget property through the nested `outputValues` path.

1. **File exists at the bundle root and parses** (NOT `lightningDesktopGenAi/`):

   ```bash
   jq . <pkgDir>/lightningTypes/<toolCLT>/renderer.json > /dev/null && echo "PARSE: ok" || echo "PARSE: FAIL"
   ```

2. **Definition points at this widget:**

   ```bash
   jq -r '.renderer.componentOverrides["$"].definition' <pkgDir>/lightningTypes/<toolCLT>/renderer.json
   ```

   Expected: `@widget/c/<widgetName>`. Match → `DEFINITION: ok`; else `DEFINITION: FAIL (got <actual>)`.

3. **Attribute keys cover every widget schema property.** Print both lists; compare in reasoning:

   ```bash
   echo "SCHEMA_KEYS (expected):"
   jq -r '.properties.attributes.properties | keys[]' <pkgDir>/uiWidgets/<widgetName>/schema.json | sort -u
   ```

   ```bash
   echo "RENDERER_KEYS (actual):"
   jq -r '.renderer.componentOverrides["$"].attributes | keys[]' <pkgDir>/lightningTypes/<toolCLT>/renderer.json | sort -u
   ```

   Same set → `ATTRIBUTES: ok`. Keys in SCHEMA not in RENDERER → `ATTRIBUTES: FAIL (missing: <list>)`. Keys in RENDERER not in SCHEMA → `ATTRIBUTES: FAIL (extra: <list>)`.

4. **Each binding uses the nested `outputValues` path.** Dump the map and inspect each entry:

   ```bash
   jq '.renderer.componentOverrides["$"].attributes' <pkgDir>/lightningTypes/<toolCLT>/renderer.json
   ```

   For every key `K`, the value MUST equal `{!$attrs.outputValues.K}` exactly (nested path, matching key, no whitespace) — **unless** `K` is a leaf of a nested-object response field (per the response CLT's `@apexClassType` properties, see `clt-reference-integrity` check 4), in which case it MUST equal `{!$attrs.outputValues.<objectField>.K}` (three segments: `outputValues`, the object field, the leaf). All match their expected form → `BINDINGS: ok`. A flat `{!$attrs.K}` (missing `outputValues.`) or a one-level binding for a nested-object leaf (missing the `<objectField>.` segment) is a FAIL — these are the most common mistakes in this flow. Report `BINDINGS: FAIL (<key>: got <value>, expected <expected>)`.

**Result classification:**
- All checks pass → `pass`
- File missing / at wrong path / invalid JSON → `fail (renderer.json missing, mislocated, or invalid — must be at lightningTypes/<toolCLT>/renderer.json)`
- Definition mismatch → `fail (definition does not point at widget: got <actual>)`
- Coverage mismatch → `fail (missing bindings: <list>)` or `fail (extra bindings: <list>)`
- Flat or malformed binding → `fail (binding for <key> is not nested under outputValues: <actual>)`

**Failure → fix:** without correct nested wiring the widget either ships dead (no definition) or renders empty (flat bindings resolve against the envelope root, where the payload fields do not exist). Author the renderer per `references/two-clt-modeling.md`.

---

### 3. `nested-list-coverage`

Confirms every **nested-object** and **list** payload field discovered in Phase 2 is actually rendered — never dropped. The failure mode it guards against: a `List<...>` field declared "out of scope" and silently omitted, leaving the widget with only a scalar KPI. A nested-object or list field is **domain data** and MUST be rendered.

> **A top-level list output is directly renderable — never reshape the Apex.** When the describe surfaces the list itself as an output (`apexClass` set + `maxOccurs > 1`, e.g. `GetLeadsList` → `leads`), the response CLT types it directly as `@apexClassType/c__<Outer>$<ElementClass>` and the renderer binds it at **two segments** `{!$attrs.outputValues.<listField>}` — no wrapper class, no Apex change. A list *inside* a wrapper object (the describe returns one `maxOccurs: 1` `apexClass` output and the list is a field the describe does not surface) binds at **three segments** `{!$attrs.outputValues.<wrapperField>.<listField>}` after reading the inner class to find the list field. Covering the field means binding it at the depth its describe position dictates — the skill must **never** normalize the action to a wrapper or drop the field.

> **Key it off discovery, not the artifacts.** A field the skill silently dropped will be absent from BOTH the CLT and the widget — so this gate must compare against the Phase 2 discovery output (the Actions REST `outputs` with `apexClass`, or the response class's `@InvocableVariable` fields, or the sample's object/array values), NOT against what the generated files happen to contain. Recall from Phase 2: a list in a response CLT is always a plain `@apexClassType/...` reference — the CLT never carries a `lightning__listType` property (the list-ness lives in the *widget* schema). Do not look for a `lightning__listType` in the CLT.

1. **List the nested-object and list fields DISCOVERED in Phase 2** (from the source, not the generated CLT). For `action`, these are `outputs[]` entries with an `apexClass` key (`maxOccurs: 1` → single object; `maxOccurs > 1` → list of objects). For `apex`, they are top-level `@InvocableVariable` fields whose type is an Apex class or `List<ApexClass>`, plus fields on any nested/referenced class the payload references — those inner fields are enumerated by the class's **public / `@AuraEnabled`** members, not `@InvocableVariable` (an inner class's list/object fields are `@AuraEnabled`, never surfaced in the describe). For `sample`, they are properties whose value is an object or an array of objects. Print the list with each field's kind (single-object vs list) and, for lists, the inner class name.

   Empty (payload is all primitives) → `COVERAGE: ok (no nested/list fields)`.

2. **For each single nested-object field** (`@apexClassType/...` in the CLT): confirm its inner class's leaf fields appear as widget schema properties (the flatten rule), and each is bound `{!$attrs.outputValues.<objectField>.<leaf>}` in the renderer. A nested-object field whose leaves are absent from the widget schema → `COVERAGE: FAIL (<objectField> flattened leaves missing from widget)`.

3. **For each list field.** The list is a plain `@apexClassType/...` reference in the CLT — either a top-level list output typed directly as `c__<Outer>$<ElementClass>`, or a field inside a wrapper `@apexClassType` object (verify the corresponding CLT property exists). Two cross-skill checks — how the widget schema/body surfaces and iterates the list is owned and validated by `platform-widget-generate`, not re-specified here:
   - **Rendered by the delegate.** Confirm the list field is present as a property in the widget schema handed off to / produced by `platform-widget-generate` (a list property, not dropped). A discovered list field absent from the widget entirely → `COVERAGE: FAIL (<listField> is a List<ApexClass> but the widget does not render it — never declare a list "out of scope")`.
   - **Bound in the renderer at the correct depth.** The envelope renderer binds the list at the depth its describe position dictates: **two segments** `{!$attrs.outputValues.<listField>}` for a top-level list output, or **three segments** `{!$attrs.outputValues.<wrapperField>.<listField>}` for a list inside a wrapper object (never `.<leaf>`). A missing or wrong-depth binding → `COVERAGE: FAIL (<listField> not bound at correct depth in renderer)`.

4. **No drop.** A discovered nested/list field is never absent. "Beta single-response flow" / "out of scope" / "list rendering not supported" are NOT valid rationales — the skill renders lists. If a discovered nested/list field is absent → **FAIL**.

**Result:** all discovered nested/list fields rendered → `pass`. Otherwise `fail (<first failing field + reason>)`.

**Failure → fix:** render the field per `references/two-clt-modeling.md` ("Nested-object and list payload fields") — do not drop it. If the list-element typing is uncertain, resolve it through `platform-custom-lightning-type-generate` and `platform-widget-generate`; do not fall back to omission.

---

## Warn — advisory

### `field-trace`

Enforces: no invented widget fields (subset rule) and no silent omission of response fields.

`INVOCABLE_FIELDS` and `WIDGET_PROPS` are labels in the printed output, NOT shell variables. Do NOT assign with `$(…)`.

1. **Extract the authoritative payload field names**, using the same source chosen in Phase 2:

   **`action` source (preferred)** — read the Actions REST API `outputs` (already excludes inputs/helpers):

   ```bash
   echo "INVOCABLE_FIELDS:"
   sf api request rest '/services/data/v<APIVER>/actions/custom/apex/<ActionApiName>' -o <org> \
     | jq -r '.outputs[].name' | sort -u
   ```

   **`apex` source** — grep the response class (scope to the response class block only; exclude the request class and private helpers):

   ```bash
   echo "INVOCABLE_FIELDS:"
   grep -A1 '@InvocableVariable' <pkgDir>/classes/<ClassName>.cls \
     | grep -oE '(public|global)\s+[A-Za-z0-9_<>,\s]+\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;' \
     | sed -E 's/.*\s([a-zA-Z_][a-zA-Z0-9_]*)\s*;/\1/' \
     | sort -u
   ```

   If grep misses multi-line annotations, read the `.cls` with the Read tool and list fields manually. For the `sample` source, use the `outputValues` keys instead.

   **Nested-object fields (per `references/mcp-tool-output-discovery.md` "Nested-object and list payload fields") expand before comparison.** A field resolved to `@apexClassType/<ns>__<OuterClass>$<InnerClass>` (single object) is not itself compared against `WIDGET_PROPS` — the widget flattens to that class's own leaf fields, never the object field. Replace that field name in `INVOCABLE_FIELDS` with its referenced class's leaf field names — enumerated by the inner class's **public / `@AuraEnabled`** members, not `@InvocableVariable` (SKILL.md Hard Rule 6; grepping an inner class for `@InvocableVariable` yields zero leaves, so the trace would spuriously pass against an empty widget) — before running the diff in step 3. Note the substitution in the printed output, e.g. `INVOCABLE_FIELDS (expanded): flightInfo → flightId, origin, destination, departureTime, arrivalTime, price`. A **list** field (`List<ApexClass>`), by contrast, is NOT flattened away — it remains a single `WIDGET_PROPS` key (the `lightning__listType` widget property), so keep the list field name in `INVOCABLE_FIELDS` as-is; its per-item leaves are `{!$item.<leaf>}` bindings inside the widget body, not top-level widget schema keys. (Whether a list is actually rendered is enforced by the hard `nested-list-coverage` gate, not here.)

2. **Extract widget schema property keys:**

   ```bash
   echo "WIDGET_PROPS:"
   jq -r '.properties.attributes.properties | keys[]' <pkgDir>/uiWidgets/<widgetName>/schema.json | sort -u
   ```

3. **PRINT both lists** in the gate report (not just an assertion):

   ```text
   INVOCABLE_FIELDS: accountName, accountIndustry, contactCount, status, ...
   WIDGET_PROPS:     accountName, accountIndustry, contactCount, ...
   INVENTED (widget − invocable): <empty>
   OMITTED  (invocable − widget): status, ...
   ```

4. **Result classification:**
   - `INVENTED` non-empty → **fail** (subset rule violated). `fail (invented: <list>)`.
   - `OMITTED` non-empty → **warn** (a response data field absent from the widget). `warn (omitted: <list>)`, surface before the summary.
   - Both empty → **pass**.

**Reporting `pass` without printing the two lists is a hard violation — report `not run` instead.**

---

## Direction of the subset rule

The widget `schema.json` and the response CLT `properties` are a **subset** of the fields the tool exposes — the top-level response class's `@InvocableVariable` outputs, plus (when a field resolves to `@apexClassType/...`) the referenced inner class's public/`@AuraEnabled` leaves.

- **No invented fields (hard via `field-trace`).** The widget must not introduce properties the response class does not expose.
- **Omissions surface as a warning.** A response data field absent from the widget is reported by `field-trace` as a warning, not silently accepted.

---

## Reporting

Phase 6 must list each gate's result by name: `pass`, `fail (<reason>)`, `warn (<reason>)`, or `not run`. Do not summarize as "all passed".
