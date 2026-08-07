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

4. **Nested-object response fields (if any) use `@apexClassType`, never a bare object.** For every response CLT property that is not a primitive leaf, print its `lightning:type`:

   ```bash
   jq -r '.properties | to_entries[] | select(.value["lightning:type"] == null or (.value["lightning:type"] | test("^lightning__") | not)) | "\(.key): \(.value["lightning:type"])"' <pkgDir>/lightningTypes/<responseCLT>/schema.json
   ```

   Every printed entry must match `@apexClassType/<ns>__<OuterClass>$<InnerClass>`. A bare `{"type":"object"}` (no `lightning:type`, or a `lightning:type` of `lightning__objectType` inlined on a *property* rather than the CLT root) → `NESTED_TYPE: FAIL (<key>: <actual>)`. All match or no such properties exist → `NESTED_TYPE: ok`.

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

   **Nested-object fields (per `references/mcp-tool-output-discovery.md` "Nested-object payload fields") expand before comparison.** A field resolved to `@apexClassType/<ns>__<OuterClass>$<InnerClass>` is not itself compared against `WIDGET_PROPS` — the widget flattens to that class's own leaf fields, never the object field. Replace that field name in `INVOCABLE_FIELDS` with its referenced class's leaf field names (its own `@InvocableVariable`/public members) before running the diff in step 3. Note the substitution in the printed output, e.g. `INVOCABLE_FIELDS (expanded): flightInfo → flightId, origin, destination, departureTime, arrivalTime, price`.

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
   - `OMITTED` non-empty AND every omitted field is in the Phase 3 `Properties omitted:` → **pass**.
   - `OMITTED` non-empty AND any omitted field is NOT in `Properties omitted:` → **warn** (silent omission). `warn (silent omission: <list>)`, surface before the summary.
   - Both empty → **pass**.

**Reporting `pass` without printing the two lists is a hard violation — report `not run` instead.**

---

## Direction of the subset rule

The widget `schema.json` and the response CLT `properties` are a **subset** of the response `@InvocableVariable` fields.

- **No invented fields (hard via `field-trace`).** The widget must not introduce properties the response class does not expose.
- **No silent omissions (warn).** The widget MAY omit response fields, but every omission must appear in the Phase 3 `Properties omitted:` section with a rationale.

---

## Reporting

Phase 6 must list each gate's result by name: `pass`, `fail (<reason>)`, `warn (<reason>)`, or `not run`. Do not summarize as "all passed".
