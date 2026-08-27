# Validation Gates

The orchestrator runs only **cross-skill validations** — checks that span two skills' outputs or compare against state captured in earlier phases. Widget-bundle-internal checks (schema parses, root keys, leaf types, attribute bindings resolve, `.uiwidget-meta.xml` well-formed, `<UiWidgetBundle>` root, widget-type) are owned by `platform-widget-generate` and run as part of its own self-validation step.

Run every gate below. If a hard-failure gate fails, fix and re-run before reporting success. Warn-level gates are advisory — failures emit warnings but do not block.

---

## Hard — block on failure

| Name | Gate | Failure → fix |
|---|---|---|
| `lightning-type-unchanged` | **`existing-lightning-type-with-widget` only** — the Lightning Type `schema.json` SHA-256 captured in Phase 2 matches the on-disk SHA at end of Phase 4. | The orchestrator (or a sub-skill) silently edited the Lightning Type. Restore the Lightning Type from `git diff` and re-author the widget against the unchanged Lightning Type. |
| `renderer-wires-widget` | **Both paths** — RUN the check below and PRINT the result. **Reporting `pass` without running the commands is a hard violation — report `not run` instead.** | The Lightning Type does not point at this widget — the widget bundle ships dead and is unreachable from any consumer that resolves through the CLT. Author or update `renderer.json` per the widget-rendition pattern in `platform-custom-lightning-type-generate/references/widget-rendition.md`. If a different widget is already wired, surface the conflict instead of silently overwriting. |

### `renderer-wires-widget` — RUN procedure

Run each command below **verbatim**. Observe each command's output in the tool result and reason about it — do NOT capture into shell variables with `$(…)`, do NOT use process substitution `<(…)`, do NOT use brace expansion. Vibes' safe-shell filter blocks those patterns and prompts for manual approval even in Bypass mode. See "Hard Rules — shell commands" in the orchestrator SKILL.md.

1. **Verify file exists and parses as JSON:**

   ```bash
   jq . <pkgDir>/lightningTypes/<TypeName>/renderer.json > /dev/null && echo "PARSE: ok" || echo "PARSE: FAIL"
   ```

2. **Verify definition points at this widget.** Print the actual value and compare it to the expected one in your reasoning:

   ```bash
   jq -r '.renderer.componentOverrides["$"].definition' <pkgDir>/lightningTypes/<TypeName>/renderer.json
   ```

   Expected output: `@widget/c/<widgetName>`. If output equals expected → `DEFINITION: ok`; otherwise `DEFINITION: FAIL (got <actual>, expected @widget/c/<widgetName>)`.

3. **Verify attribute bindings cover every widget schema property.** Print both key lists with separate commands; compare them in your reasoning (do NOT `diff` with process substitution):

   ```bash
   echo "SCHEMA_KEYS (expected):"
   jq -r '.properties.attributes.properties | keys[]' <pkgDir>/uiWidgets/<widgetName>/schema.json | sort -u
   ```

   ```bash
   echo "RENDERER_KEYS (actual):"
   jq -r '.renderer.componentOverrides["$"].attributes | keys[]' <pkgDir>/lightningTypes/<TypeName>/renderer.json | sort -u
   ```

   Classify: same set → `ATTRIBUTES: ok`. Keys in `SCHEMA_KEYS` not in `RENDERER_KEYS` → `ATTRIBUTES: FAIL (missing: <list>)`. Keys in `RENDERER_KEYS` not in `SCHEMA_KEYS` → `ATTRIBUTES: FAIL (extra: <list>)`.

4. **Verify each attribute value is a well-formed binding.** Dump the attributes map and inspect each entry in your reasoning:

   ```bash
   jq '.renderer.componentOverrides["$"].attributes' <pkgDir>/lightningTypes/<TypeName>/renderer.json
   ```

   For every key `K`, the value must match `{!$attrs.K}` exactly (same key name, no whitespace). All match → `BINDINGS: ok`. Otherwise `BINDINGS: FAIL (<key>: got <value>, expected {!$attrs.<key>})` for each offender.

5. **Result classification:**
   - All checks pass → `pass`
   - File missing or does not parse → `fail (renderer.json missing or invalid JSON)`
   - Definition mismatch → `fail (definition does not point at widget: got <actual>)`
   - Attribute coverage mismatch → `fail (missing bindings: <list>)` or `fail (extra bindings: <list>)`
   - Binding format invalid → `fail (malformed binding for <key>: <actual>)`

---

## Warn — advisory

| Name | Gate | Warning meaning |
|---|---|---|
| `field-trace` | **Both paths** — RUN the trace below and PRINT both lists explicitly. | See "`field-trace` — RUN procedure" below. **Reporting `pass` without printing the two lists side by side is a hard violation — report `not run` instead.** |
| `deploy-check` | **`new-lightning-type-with-widget` only** — RUN `sf project deploy --check-only --source-dir <pkgDir>/classes/<ClassName>.cls,<pkgDir>/lightningTypes/<TypeName>` and report the result. | Apex / Custom Lightning Type references are unresolved when validated against the org. Common cause: the FQN in the Custom Lightning Type does not match the actual Apex class. **Reporting `pass` without running this command is a hard violation. Reporting `not run` is only valid if the source files do not exist in the local project — "not yet deployed" is not a valid reason; `--check-only` submits the source as part of the call.** |

### `field-trace` — RUN procedure

The gate enforces two things: no invented widget fields (subset rule), and no silent omission of `@AuraEnabled` fields (omission must be in the build plan's `Properties omitted:` and approved at Phase 3).

**`APEX_FIELDS` and `WIDGET_PROPS` are labels in the printed output, NOT shell variables. Do NOT assign either with `APEX_FIELDS=$(grep …)` or `WIDGET_PROPS=$(jq …)` — Vibes' safe-shell filter blocks `$(…)` and stalls the eval on manual approval. Run each command bare and reason about the output.**

1. **Resolve the payload class from the Apex class FQN**, then extract `@AuraEnabled` field names from the payload class **and from every inner class referenced by it** — both singular nested objects (e.g. `Address address`) and `List<InnerClass>` collections. Split the FQN on `$`: no `$` → the outer class is the payload; with `$` (e.g. `c__OrderResponses$CreateResult`) → the named inner class is the payload and the outer class's own `@AuraEnabled` fields are NOT part of the trace.

   Read the outer `.cls` file at `<pkgDir>/classes/<ClassName>.cls`; when the payload is the outer class, grep the whole file; when the payload is an inner class, scope the grep to that inner class's block.

   ```bash
   # Outer-class payload — print the field names. Do NOT wrap in $().
   echo "APEX_FIELDS:"
   grep -B0 -A2 '@AuraEnabled' <pkgDir>/classes/<ClassName>.cls \
     | grep -oE '(public|global)\s+[A-Za-z0-9_<>,\s]+\s+[a-zA-Z_][a-zA-Z0-9_]*\s*;' \
     | sed -E 's/.*\s([a-zA-Z_][a-zA-Z0-9_]*)\s*;/\1/' \
     | sort -u
   ```

   For an inner-class payload, read the .cls file, locate the named inner class's block (`class <InnerClass> {…}`), and run the field enumeration scoped to that block only. Identify further inner classes the payload class declares (singular `InnerClass <field>;` and `List<InnerClass> <field>;`) — typically siblings inside the same outer file — and repeat against each. Combine the printed sets in your reasoning under the label `APEX_FIELDS`. If grep returns nothing, fall back to reading the .cls file with the Read tool and listing fields manually — but do NOT skip the comparison.

2. Extract widget schema property keys, expanding nested inner-Apex-class-reference properties (`lightning:type: "@apexClassType/...$Inner"`, and any remaining `lightning__objectType`) to their inner-field dot paths:

   ```bash
   echo "WIDGET_PROPS:"
   jq -r '.properties.attributes.properties | keys[]' <pkgDir>/uiWidgets/<widgetName>/schema.json | sort -u
   ```

   For any property whose `lightning:type` is an inner-Apex-class reference (`@apexClassType/...$Inner`) or `lightning__objectType`, also include the dot-notation bindings actually referenced in the widget body (e.g. `address.city`) — you can see these by reading the widget JSON directly with the Read tool. For any property whose `lightning:type` is `lightning__listType`, also include the `{!$item.<innerField>}` references inside the `forEach`. Combine in your reasoning under the label `WIDGET_PROPS`.

3. PRINT both lists in the gate report (not just an assertion) — as plain text you author from the two command outputs above, NOT via a shell expression:

   ```text
   APEX_FIELDS:  cartId, currencyIsoCode, items.itemId, items.qty, itemCount, ...
   WIDGET_PROPS: cartId, currencyIsoCode, itemCount, ...
   INVENTED  (widget − apex): <empty>
   OMITTED   (apex − widget): items.*
   ```

4. Result classification:
   - `INVENTED` non-empty → **fail** (subset rule violated). Report `fail (invented: <list>)`.
   - `OMITTED` non-empty AND every omitted field appears in the Phase 3 build plan's `Properties omitted:` section → **pass** (auditable omission).
   - `OMITTED` non-empty AND any omitted field is NOT in `Properties omitted:` → **warn** (silent omission). Report `warn (silent omission: <list>)` and surface to the user before the final summary.
   - Both empty → **pass**.

---

## Direction of subset rule

The widget `schema.json` (plus the dot-notation paths it binds through nested inner-Apex-class-reference (`@apexClassType/...$Inner`) or `lightning__objectType` properties, and the `{!$item.X}` references inside `lightning__listType` loops) is a **subset** of the Apex class's `@AuraEnabled` fields (outer class plus every referenced inner class). The orchestrator enforces both directions, asymmetrically:

- **No invented fields (hard).** Widget MUST NOT introduce properties or inner-field paths the Apex classes do not expose. A non-empty INVENTED set fails `field-trace`.
- **No silent omissions (warn).** Widget MAY omit Apex fields, but every omission MUST appear in the Phase 3 build plan's `Properties omitted:` section with a rationale. Omissions not in the plan are silent and warn at `field-trace` (OMITTED list flagged). The leaf skill must surface the proposed omissions to the user before authoring (`platform-widget-generate/references/schema-from-lightning-type.md`). Inner-class fields (whether reached as singular nested objects or via `List<InnerClass>`) are NEVER silently omitted.

---

## Reporting

Phase 6 must list each gate's result by name: `pass`, `fail (<reason>)`, `warn (<reason>)`, or `not run`. Do not summarize ("all passed") — list each gate explicitly so the reviewer can spot a silent skip.
