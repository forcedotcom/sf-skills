---
name: platform-mcp-tool-widget-coordinate
description: "Orchestrate object-based Lightning Type + HXL widget generation to render the output of a custom MCP server tool backed by an Apex Invocable Action. TRIGGER only when the prompt EXPLICITLY involves rendering an MCP tool result: user says 'MCP server', 'MCP tool', 'custom MCP server', references a tool 'output schema' / 'tool output' / 'outputValues' envelope, names an 'invocable action' backing an MCP tool, or asks to build a widget or rich UI rendition for the output of an Apex-invocable-backed MCP tool. DO NOT TRIGGER when: customizing an Apex-backed agent action output (use platform-lightning-type-widget-coordinate), authoring only a Custom Lightning Type (use platform-custom-lightning-type-generate), authoring only an Apex class (use platform-apex-generate), or building a standalone widget with no Lightning Type or MCP tool involved (use platform-widget-generate)."
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-custom-lightning-type-generate"
    - "platform-lightning-type-widget-coordinate"
    - "platform-widget-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Rendering a Custom MCP Tool Output With a Widget

Coordinate **two object-based Custom Lightning Types (CLTs)** and an **HXL widget** to render the output of a custom MCP server tool whose implementation is an Apex `@InvocableMethod`. This skill never authors content directly — it loads and invokes leaf skills in dependency order, gates progress on user approval, and runs validation gates before reporting completion.

## Scope

Custom MCP server tools backed by an Apex Invocable Action only. The MCP tool returns the platform's **invocable-action result envelope** — an object with `actionName`, `isSuccess`, and an `outputValues` node that carries the tool's real payload. To render this envelope with a widget, model it as **two object-based CLTs** (`lightning__objectType`) of equal standing — the only reason there are two is that one must reference the other by name (a CLT cannot reference itself), so they need distinct deployed names. Name and describe each by what it actually models — never by an invented role-label pair like "Payload CLT"/"Envelope CLT" or "Inner CLT"/"Outer CLT":

- The CLT that mimics the tool-result envelope, named `<toolApiName>`. Its `outputValues` property is typed to the other CLT via `c__<responseCLT>`.
- The CLT that is the exact shape of the Invocable Action's **response** (`@InvocableVariable` fields on the `@InvocableMethod` response class), named `<toolApiName>Response` — "Response" here is not an invented role word, it's the same word the Apex source already uses for that class (e.g. `GetAccountSummaryResponse`).

The widget grounds on the **response fields** (flat), and the **default `renderer.json` in the envelope CLT** bridges the envelope nesting to the flat widget via `{!$attrs.outputValues.<field>}`.

**Out of scope, route elsewhere:**

- Customizing an **Apex-backed agent action** output (Apex-backed CLT `@apexClassType/...`, single CLT, surface-specific renderer) → `platform-lightning-type-widget-coordinate`.
- A standalone widget with no MCP tool / Lightning Type → `platform-widget-generate`.
- Authoring only a CLT or only an Apex class → `platform-custom-lightning-type-generate` / `platform-apex-generate`.

> **Beta cardinality:** the invocable-action result is a bulk array (`content[]`). For the beta release this skill models and renders a **single response** — the first element of `content[]`. The CLT envelope models one result object, not the `content[]` wrapper.

---

## How this differs from `platform-lightning-type-widget-coordinate`

| Dimension | agent-action flow (`...lightning-type-widget-coordinate`) | this MCP-tool flow |
|---|---|---|
| CLT kind | Apex-backed (`@apexClassType/...`) | Object-based (`lightning__objectType`) |
| Number of CLTs | one | **two** (envelope + response) |
| Field source | `@AuraEnabled` | **`@InvocableVariable`** on the response class |
| Renderer location | `lightningTypes/<T>/lightningDesktopGenAi/renderer.json` (surface-specific) | `lightningTypes/<toolCLT>/renderer.json` (**default, parallel to `schema.json`**) |
| Renderer binding | flat `{!$attrs.<field>}` | **nested `{!$attrs.outputValues.<field>}`** |

---

## Phase Graph

| Phase | Purpose | Output |
|---|---|---|
| 1 — Input selection | Determine the payload source: an **invocable action API name** (preferred), an Apex Invocable class, or a pasted tool-output JSON sample. | `source` (`action` \| `apex` \| `sample`), tool API name |
| 2 — Payload discovery | Describe the invocable action via the Actions REST API and read its typed `outputs` (or parse the response class from source, or `outputValues` from the sample). | `payloadFields` (name + `lightning:type`) |
| 3 — Build plan | Print the plan in full; proceed unless the next reply explicitly pushes back. | printed plan |
| 4 — Generation | Load and invoke leaf skills: response CLT → envelope CLT → widget → inline default renderer in the envelope CLT. | files written |
| 5 — Validation | Run hard gates (block) and warn gates (advisory). | gate report |
| 6 — Summary | Files, validations, deploy order, preview readiness. | summary |

**Per-phase pattern:** load the skill fresh → execute its workflow → verify outputs → checkpoint before the next phase. Even if you remember a leaf skill's content, skills evolve — always load fresh.

---

## Phase 1 — Input selection

Determine where the payload shape comes from. Prefer the sources top-to-bottom:

| Source | Trigger | Phase 2 action |
|---|---|---|
| `action` | Prompt gives an **invocable action API name** — directly, or via an Apex class name that resolves to one — AND an authenticated org is available. **Preferred.** | Describe the action via the Actions REST API and read its typed `outputs`. |
| `sample` | No reachable org (or the describe 404s), but a pasted tool-output JSON sample is available. | Parse the `outputValues` object from the sample. |
| `apex` | Only the Apex **class** is available (no action name resolvable, no reachable org, no sample) — fallback only, may be stale relative to what's deployed. | Resolve the response class and enumerate `@InvocableVariable` fields. |

Capture the **tool API name** (used to name all artifacts — see the naming convention below).

**Source priority:** live/authoritative schema sources beat parsing a local class, which beats a pasted example. In order:
1. **`action`** if an action API name and an authenticated org are available. The Actions REST API describe is the same schema the platform itself exposes, so it needs no request/helper filtering and gives real field types.
2. **`sample`** if a runtime JSON sample is pasted (runtime response — explicit and current).
3. **`apex`** if an Apex class exists locally AND none of the above apply (fallback only — may be stale relative to what's actually deployed behind the action).

If none are available, STOP and ask the user for an action name, a class, a sample, or a schema.

---

## Phase 2 — Payload discovery

FIRST Read `references/mcp-tool-output-discovery.md` (REQUIRED — do NOT run Phase 2 from this summary alone), then execute the procedure for the chosen source. Reminders:

**For `action` (preferred):** describe the action with the Actions REST API and read its `outputs`:

- Resolve the action API name (for Apex actions this is the **class name** declaring `@InvocableMethod`, not the method label).
- `sf api request rest '/services/data/v<APIVER>/actions/custom/apex/<ActionApiName>' -o <org>`.
- Use the `outputs` array only (each entry `{ name, label, type, maxOccurs }`). **Ignore `inputs`** — that is the tool input (request wrapper). A field with `maxOccurs > 1` is a list — surface it in the plan (beta renders a single response).
- Map the Actions API `type` → CLT `lightning:type` (see the discovery reference's table; `STRING`/`ID`/`REFERENCE`/… → `lightning__textType`, `INTEGER`/`LONG` → `lightning__integerType`, `DOUBLE`/`DECIMAL`/`CURRENCY`/`PERCENT` → `lightning__numberType`, `BOOLEAN` → `lightning__booleanType`, `DATE`/`DATETIME` → date types). Match case-insensitively.
- An entry with **`"type": null` and an `"apexClass": "<OuterClass>$<InnerClass>"` key** instead of a primitive `type` is a nested-object field, not a describe gap — see "Nested-object payload fields" below. The describe never exposes that class's own leaf fields, so retrieving/reading the named Apex class to enumerate them is the expected next step, not a fallback away from `action`.
- If the describe 404s, fall back to `sample` (a pasted tool-output JSON) if one is available, else `apex` (parse the class from source, if locally available).

**For `apex` (fallback):**

- Locate the class (`<pkgDir>/classes/<ClassName>.cls`; retrieve `ApexClass:<ClassName>` if absent).
- Identify the **response class** — the element type of the `@InvocableMethod` return `List<...>` (e.g. `List<GetAccountSummaryResponse>` → `GetAccountSummaryResponse`).
- Enumerate its `@InvocableVariable` fields. **Exclude** the request class (the `@InvocableMethod` parameter type) and any `private` helper classes — those are not part of the tool's externally visible output schema.
- Map Apex → CLT `lightning:type`: `String`/`Id` → `lightning__textType`, `Integer` → `lightning__integerType`, `Decimal`/`Double` → `lightning__numberType`, `Boolean` → `lightning__booleanType`, `Date` → `lightning__dateType`, `Datetime` → `lightning__dateTimeType`.
- **A field whose type is itself an Apex class** (e.g. `flightInfo : SearchFlightsAction.Flight`) is a second, additive case alongside the flat-primitive mapping above — see "Nested-object payload fields" below. This applies to every source (`action`, `apex`, `sample`), not just `apex`.

**For `sample` (fallback):** parse the `outputValues` object; infer each field's `lightning:type` from its JSON value (string → `lightning__textType`, integer → `lightning__integerType`, fractional number → `lightning__numberType`, boolean → `lightning__booleanType`).

**Nested-object payload fields (applies to every source above):** when a response/output field's type is not a primitive but another Apex class (object), do NOT model it as `{"type":"object"}` or an inlined `lightning__objectType` — both produce an opaque, unrenderable blob and neither deploys. Instead:
- Type the response CLT property as `"@apexClassType/<ns>__<OuterClass>$<InnerClass>"` (e.g. `"@apexClassType/c__SearchFlightsAction$Flight"`), matching the Apex-backed-CLT convention `platform-custom-lightning-type-generate` already documents.
- Enumerate the referenced Apex class's own `@InvocableVariable`/public fields as the leaf set; the widget schema flattens to those leaves (never the object field itself).
- The renderer binds one level deeper: `{!$attrs.outputValues.<objectField>.<leaf>}` (e.g. `{!$attrs.outputValues.flightInfo.flightId}`), not `{!$attrs.outputValues.<objectField>}`.
- A field typed `List<ApexClass>` is out of scope for the beta single-response flow — surface it in the build plan like a `maxOccurs > 1` scalar, do not emit a schema for it.
- See `references/two-clt-modeling.md` ("Nested-object payload fields") and `examples/nested-object-source-prompt.md` for the full walkthrough.

Capture `payloadFields` — the ordered list of `{ name, title, lightning:type }` that defines the response CLT and the widget schema. Record which source produced it in the build plan.

> Staleness: do NOT maintain a cross-session cache. Read the local project fresh and re-retrieve from the org per session.

---

## Phase 3 — Build plan + approval gate

Print a build plan using the template in `references/build-plan-format.md`. The plan must list:

- A one-line developer-facing summary (the `PLAN:` line).
- The tool API name and the response class FQN (or "from pasted sample").
- The two CLT names (envelope + payload) and the widget name, with absolute paths.
- The envelope fields the envelope CLT will carry, and the response fields the response CLT + widget will carry.
- `Properties omitted:` — any response fields intentionally dropped, with rationale. **`actionName` and `isSuccess` are envelope fields and never appear here or on the widget** — they belong to the envelope CLT only. Any payload-side operational/status field (`isSuccess`, `errorMessage`, `status`, `message`, and similar) that the response happens to carry is omitted from the widget by default and MUST be listed here with a one-line rationale — the widget renders `outputValues` data fields only.
- The validations that will run after generation.

**Print the plan in full, then proceed unless the user's next reply explicitly pushes back.** Explicit pushback = `no`, `stop`, `wait`, `change X`, `use Y instead`, or an equivalent rejection / revision request. Explicit approval is welcome but NOT required — silence, an unrelated follow-up, or the natural continuation of a single-turn eval all count as implicit approval. The invariant is the plan being visible in the transcript. If pushback arrives, revise and re-print before moving on.

---

## Phase 4 — Generation

Load and invoke leaf skills in this order. For each: load the skill, execute its workflow against the Phase 3 spec, verify the outputs, checkpoint before the next.

1. **Response CLT** — load `platform-custom-lightning-type-generate`. Author an object-based CLT `<responseCLT>` (convention: `<toolApiName>Response`) whose `properties` are the `payloadFields` from Phase 2 (1:1 with the response `@InvocableVariable` fields). Root is `lightning__objectType`, with root-level `"lightning:tags": ["mcp"]`.

2. **Envelope CLT** — load `platform-custom-lightning-type-generate`. Author an object-based CLT `<toolCLT>` (convention: `<toolApiName>`, the envelope), also with root-level `"lightning:tags": ["mcp"]`, and:
   - `actionName` → `lightning__textType`
   - `isSuccess` → `lightning__booleanType`
   - `outputValues` → **`c__<responseCLT>`** (the referenced-CLT pattern; the response CLT must be deployed before the envelope CLT)
   - Add `message` / other envelope scalars only if the widget needs to render them.

3. **Widget** — load `platform-widget-generate`. Author a **flat** widget whose `schema.json` properties are the `payloadFields` (name + primitive type) — a standalone widget contract, not derived from or coupled to any Lightning Type. It renders **only `outputValues` data fields**: never `actionName`/`isSuccess` (envelope-only), and never a response-side operational/status field declared in `Properties omitted:`. The widget body binds each field via `{!$attrs.<field>}` — the widget is envelope-agnostic and never references `outputValues` itself.

4. **Default renderer (authored inline in the ENVELOPE CLT — never optional).** FIRST Read `platform-custom-lightning-type-generate/references/widget-rendition.md` (REQUIRED — do NOT author from memory or copy an existing sample, which may use a deprecated shape). Then author `<pkgDir>/lightningTypes/<toolCLT>/renderer.json` — the **default renderer, at the bundle root, parallel to `schema.json`** (NOT under `lightningDesktopGenAi/`). Shape:

   ```json
   {
     "renderer": {
       "componentOverrides": {
         "$": {
           "definition": "@widget/c/<widgetName>",
           "attributes": {
             "<payloadField>": "{!$attrs.outputValues.<payloadField>}"
           }
         }
       }
     }
   }
   ```

   The renderer maps **every widget schema property** to the matching payload field nested under the envelope's `outputValues` node via `{!$attrs.outputValues.<payloadField>}`. This nested binding is the crux of this flow — it bridges the envelope CLT to the flat widget. Do **NOT** duplicate the widget body inside `renderer.json`.

**Existing-renderer handling:** if `renderer.json` already exists at the target path, read it first. If it references the same widget with the same bindings, leave it. If it references a different widget or a custom-LWC root override (`c/<component>`), STOP and surface the conflict before overwriting.

---

## Phase 5 — Validation gates

Read `references/validation-gates.md` and **run every gate**. Widget-bundle-internal checks (schema parse, root keys, leaf types, `{!$attrs.X}` resolution, `.uiwidget-meta.xml` well-formedness) are owned by `platform-widget-generate` and run in its own self-validation.

**Hard — block on failure:**

1. `clt-reference-integrity` — the envelope CLT's `outputValues` property has `lightning:type === "c__<responseCLT>"`, the response CLT exists at `<pkgDir>/lightningTypes/<responseCLT>/schema.json`, both parse as JSON, and neither carries `$schema` or (nested) `items`.
2. `renderer-wires-widget` — `<pkgDir>/lightningTypes/<toolCLT>/renderer.json` exists (at the bundle root, **not** `lightningDesktopGenAi/`), parses, wires the widget via `componentOverrides["$"].definition === "@widget/c/<widgetName>"`, and binds every widget schema property as **`{!$attrs.outputValues.<property>}`** (nested path). Bidirectional: missing or extra bindings both fail.

**Warn — advisory:**

1. `field-trace` — RUN the trace in `references/validation-gates.md`: grep `@InvocableVariable` from the **response** class, `jq` the widget schema property keys, print both lists, classify INVENTED vs OMITTED. Invented widget fields fail; silent omissions (a response field absent from the widget AND absent from the Phase 3 `Properties omitted:` plan) warn.

Report each gate result by name in Phase 6 (`pass`, `fail (<reason>)`, `warn (<reason>)`, `not run`). Do **not** summarize as "all passed". This skill produces metadata only — it does not deploy; deployment is the caller's responsibility.

---

## Phase 6 — Summary

```text
MCP Tool Widget Build Complete: <widgetName>

FILES GENERATED:
  Response CLT:
    <pkgDir>/lightningTypes/<responseCLT>/schema.json
  Envelope CLT:
    <pkgDir>/lightningTypes/<toolCLT>/schema.json
    <pkgDir>/lightningTypes/<toolCLT>/renderer.json          # default renderer — wires the widget
  Widget bundle:
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json
    <pkgDir>/uiWidgets/<widgetName>/schema.json
    <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml

VALIDATIONS:
  widget self-validation (platform-widget-generate gates): <pass | fail — see sub-skill report>
  clt-reference-integrity (envelope.outputValues → c__<responseCLT>): <pass | fail (<reason>)>
  renderer-wires-widget (nested {!$attrs.outputValues.X} bindings): <pass | fail (<reason>)>
  field-trace (INVENTED + OMITTED lists printed): <pass | warn (<reason>) | fail (invented: <list>)>
```

---

## Hard Rules (always apply)

1. **Plan-first, then proceed.** Print the full Phase 3 build plan before writing any file. Explicit rejection or a change request → stop and revise; otherwise continue. The invariant is the plan being visible in the transcript, not an interactive human approval — this holds in manual chat, agent-to-agent flows, and single-turn evals.
2. **Two object-based CLTs, never one.** The envelope and the payload are separate CLTs. The envelope's `outputValues` is typed via `c__<responseCLT>`, never inlined as a nested `lightning__objectType`. Both CLTs carry root-level `"lightning:tags": ["mcp"]` (see `platform-custom-lightning-type-generate/assets/primitive-types-and-constraints.md`).
3. **Renderer lives in the ENVELOPE CLT, at the bundle root.** `lightningTypes/<toolCLT>/renderer.json` — the default renderer, parallel to `schema.json`. Never `lightningDesktopGenAi/renderer.json` (that is the agent-action flow's surface-specific path), never in the response CLT.
4. **Renderer bindings are nested.** Every widget attribute maps to `{!$attrs.outputValues.<field>}`, not `{!$attrs.<field>}`. The widget schema stays flat; the renderer does the bridging.
5. **Widget grounds on the payload, not the envelope, and renders `outputValues` data fields only.** The widget schema properties are the payload fields. The widget never references `actionName` or `isSuccess` — those are envelope-only. A payload field that is itself operational/status (`isSuccess`, `errorMessage`, `status`, `message`, and similar) is omitted from the widget by default and declared in `Properties omitted:`.
6. **Field source is `@InvocableVariable` on the response class.** Enumerate the response class only. Exclude the request class and private helper classes.
7. **No invented fields, no silent omissions.** The widget schema (and the response CLT) must be a subset of the response `@InvocableVariable` fields. Omission requires the field to appear in the Phase 3 `Properties omitted:` section with an approved rationale. `field-trace` prints both lists.
8. **Single response for beta.** Model one result object, not the `content[]` bulk wrapper.
9. **Always load the leaf skill** before generation. Do not author from memory.
10. **Run gates, do not describe them.** Reporting `pass` without executing a gate is a hard violation; report `not run` instead.
11. **No shell metacharacters that trigger the Vibes safe-shell filter.** In every `Bash` tool call emitted by this orchestrator and by any leaf skill it invokes, do NOT use command substitution (`$(…)` or backticks), process substitution (`<(…)`, `>(…)`), brace expansion (`{a,b,c}` or `{1..N}`), or `eval` / `exec`. These force manual approval even under Bypass mode and stall the eval. Run separate commands (`mkdir -p a && mkdir -p b`), print each intermediate value with its own command and reason about the result, and use plain shell variables (`X=literal`) or here-strings when a value must be reused.
12. **Resolve `action` schema from the Actions REST API describe, never from raw HTTP to the MCP endpoint or from credential extraction.** Use `sf api request rest` against the org's Actions REST API (which uses the existing `sf` org auth). Never read `a4d_mcp_settings.json` or any MCP settings file, never extract an org access token, never `curl` an MCP server endpoint directly — that requires credentials the session doesn't have and targets a URL the runtime doesn't actually expose that way.
13. **Never invoke an MCP tool to discover its output shape.** Describing the payload must never execute the underlying action. Resolve the schema via the Actions REST API describe of the backing action — never by calling the tool with sample/guessed input to observe a response. If no action name is resolvable, ask the user for a pasted `sample` instead of invoking anything.
14. **A response field typed as another Apex class is never a bare `{"type":"object"}`.** Type it `@apexClassType/<ns>__<OuterClass>$<InnerClass>` in the response CLT, flatten to its leaf fields in the widget, and bind the renderer two levels deep (`{!$attrs.outputValues.<objectField>.<leaf>}`). This is additive to the flat-primitive case (Hard Rule 5), not a replacement for it — see `references/two-clt-modeling.md`.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-tool-output-discovery.md` | Phase 2 — the three sources (`action` describe via Actions REST API; pasted `sample`; `apex` class parse), field enumeration, and type mapping. |
| `references/two-clt-modeling.md` | Phase 4 — how the envelope + response CLTs and the nested renderer binding fit together, with the naming convention and nested-object payload handling. |
| `references/build-plan-format.md` | Phase 3 — plan template the model fills before proceeding. |
| `references/validation-gates.md` | Phase 5 — full hard / warn gate table with RUN procedures. |
| `examples/action-name-source-prompt.md` | Phase 3 — a complete walkthrough starting from an invocable action API name (preferred source). |
| `examples/apex-invocable-source-prompt.md` | Phase 3 — a complete walkthrough starting from an Apex Invocable class (fallback). |
| `examples/pasted-tool-output-prompt.md` | Phase 3 — a complete walkthrough starting from a pasted tool-output sample (fallback). |
| `examples/nested-object-source-prompt.md` | Phase 3 — a complete walkthrough where a payload field is itself an Apex-class reference, not a primitive. |
