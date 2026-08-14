---
name: platform-mcp-tool-widget-coordinate
description: "Orchestrate object-based Lightning Type + HXL widget generation to render the output of a custom MCP server tool backed by an Apex Invocable Action. TRIGGER only when the prompt EXPLICITLY involves rendering an MCP tool result: user says 'MCP server', 'MCP tool', 'custom MCP server', references a tool 'output schema' / 'tool output' / 'outputValues' envelope, names an 'invocable action' backing an MCP tool, or asks to build a widget or rich UI rendition for the output of an Apex-invocable-backed MCP tool. DO NOT TRIGGER when: customizing an Apex-backed agent action output (use platform-lightning-type-widget-coordinate), authoring only a Custom Lightning Type (use platform-custom-lightning-type-generate), authoring only an Apex class (use platform-apex-generate), or building a standalone widget with no Lightning Type or MCP tool involved (use platform-widget-generate)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
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

**Ownership boundary** — this skill owns only:

1. the **MCP-tool use case** — resolving the tool's output shape and orchestrating the leaf skills in the right order; and
2. the **envelope CLT's default `renderer.json`** — the one artifact it authors inline, bridging the envelope to the widget.

The **CLTs** are authored by `platform-custom-lightning-type-generate`, and **all widget metadata** (schema + body + `.uiwidget-meta.xml`) is authored and validated by `platform-widget-generate`. This skill never writes widget metadata and never modifies the Apex class — it supplies each leaf skill its inputs and wires the result together.

## Scope

Custom MCP server tools backed by an Apex Invocable Action only. The MCP tool returns the platform's **invocable-action result envelope** — an object with `actionName`, `isSuccess`, and an `outputValues` node that carries the tool's real payload. To render this envelope with a widget, model it as **two object-based CLTs** (`lightning__objectType`) of equal standing — the only reason there are two is that one must reference the other by name (a CLT cannot reference itself), so they need distinct deployed names. Name and describe each by what it actually models — never by an invented role-label pair like "Payload CLT"/"Envelope CLT" or "Inner CLT"/"Outer CLT":

- The CLT that mimics the tool-result envelope, named `<toolApiName>`. Its `outputValues` property is typed to the other CLT via `c__<responseCLT>` (the CLT-reference prefix — see the namespace note below).
- The CLT that is the exact shape of the Invocable Action's **response** (`@InvocableVariable` fields on the `@InvocableMethod` response class), named `<toolApiName>Response` — "Response" is not an invented role word; it is the word the Apex source itself uses for that class.

The widget grounds on the **response fields** (flat), and the **default `renderer.json` in the envelope CLT** bridges the envelope nesting to the flat widget via `{!$attrs.outputValues.<field>}`.

> **Namespace prefix provenance (`c__` / `@apexClassType/<ns>__…`):** the Actions REST describe returns bare, unprefixed class names (`Outer$Inner`) and no namespace — the prefix is the *org's CLT namespace*, added by this skill. It is `c__` in a namespace-less org (the common case, used literally throughout this doc) or the package namespace `<ns>__` in a packaged org (read from the class's `NamespacePrefix`; default to `c` only when the org has none). Every `c__` below is this prefix.

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
| Field source | `@AuraEnabled` | **`@InvocableVariable`** on the top-level response class (referenced inner classes: public/`@AuraEnabled` — see Hard Rule 6) |
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

FIRST Read `references/mcp-tool-output-discovery.md` (REQUIRED — do NOT run Phase 2 from this summary alone), then execute the procedure for the chosen source. The reference is authoritative for the full per-source procedures, the field-type mapping tables, and the nested/list handling; the pointers below are only a map to it:

- **`action` (preferred):** describe via `sf api request rest '/services/data/v<APIVER>/actions/custom/apex/<ActionApiName>' -o <org>`; use the `outputs` array only (**ignore `inputs`** — the request wrapper); map each `type` → CLT `lightning:type` case-insensitively. An entry with `"type": null` and an `"apexClass": "<Outer>$<Inner>"` key is an Apex-class-typed field (not a describe gap): `maxOccurs: 1` → single nested object, `maxOccurs > 1` → top-level list. If the describe 404s, fall back to `sample` then `apex`.
- **`apex` (fallback):** locate the class, identify the response class (the `@InvocableMethod` return `List<...>` element type), enumerate its `@InvocableVariable` fields (**exclude** the request class and `private` helpers), map Apex type → CLT type.
- **`sample` (fallback):** parse the `outputValues` object; infer each field's `lightning:type` from its JSON value.

**Nested-object and list fields (every source, additive to the flat-primitive case):** a field typed as another Apex class — a single object (`maxOccurs: 1`), a top-level list (`maxOccurs > 1`), or a list *inside* a wrapper object (the describe returns one `maxOccurs: 1` `apexClass` output and hides the interior list) — is **in scope** and is **never** modeled as a bare `{"type":"object"}` or an inlined `lightning__objectType`. Type it `@apexClassType/c__<Outer>$<Inner>` in the response CLT (never a CLT-level `lightning__listType`/`items`), enumerate a referenced/inner class by its **public / `@AuraEnabled`** members (Hard Rule 6), and recurse when a leaf is itself a class. The CLT typing and renderer binding depth per shape live in `references/mcp-tool-output-discovery.md` and `references/two-clt-modeling.md` ("Top-level list vs list-inside-wrapper") — also Hard Rules 4, 6, 14 — and the `examples/nested-object-*-source-prompt.md` walkthroughs.

Capture `payloadFields` — the ordered list of `{ name, title, lightning:type }` that defines the response CLT and the widget schema. Record which source produced it in the build plan.

> Staleness: do NOT maintain a cross-session cache. Read the local project fresh and re-retrieve from the org per session.

---

## Phase 3 — Build plan + approval gate

Print a build plan using the template in `references/build-plan-format.md`. The plan must list:

- A one-line developer-facing summary (the `PLAN:` line).
- The tool API name and the response class FQN (or "from pasted sample").
- The two CLT names (envelope + payload) and the widget name, with absolute paths.
- **The envelope CLT carries exactly `actionName` (text), `isSuccess` (boolean), and `outputValues`** (typed `c__<responseCLT>`, the load-bearing field the renderer bridges through) — `actionName`/`isSuccess` are envelope-only and never appear on the widget (Hard Rule 5) — plus the response fields the response CLT + widget will carry.
- The validations that will run after generation.

**Print the plan in full, then proceed unless the user's next reply explicitly pushes back.** Explicit pushback = `no`, `stop`, `wait`, `change X`, `use Y instead`, or an equivalent rejection / revision request. Explicit approval is welcome but NOT required — silence, an unrelated follow-up, or the natural continuation of a single-turn eval all count as implicit approval. The invariant is the plan being visible in the transcript. If pushback arrives, revise and re-print before moving on.

---

## Phase 4 — Generation

Load and invoke leaf skills in this order. For each: load the skill, execute its workflow against the Phase 3 spec, verify the outputs, checkpoint before the next.

1. **Response CLT** — load `platform-custom-lightning-type-generate`. Author an object-based CLT `<responseCLT>` (convention: `<toolApiName>Response`) whose `properties` are the `payloadFields` from Phase 2. Root is `lightning__objectType`, with root-level `"lightning:tags": ["mcp"]`.
   - **The response CLT's top-level properties are 1:1 with the describe's `outputs[]` names** (or, for `apex`/`sample`, the response class's `@InvocableVariable` fields — the same set the describe would surface). A describe with **N sibling outputs** → **N flat properties**; a describe with **one output** → **one property named after that output**. A single-property CLT is correct only when the describe itself returns a single output.
   - **Never collapse multiple sibling outputs into one invented wrapper property.** Naming a lone property to hold several outputs invents a key that is **in no describe output** and is unresolvable under the `action` source — the response-class name never appears in `outputs[]`. Each response CLT property name must trace to a describe output name (see `field-trace` / `clt-reference-integrity`).
   - A top-level list output is typed **directly** to its element class (`@apexClassType/c__<Outer>$<ElementClass>`), not wrapped — see "List of nested objects" above.

2. **Envelope CLT** — load `platform-custom-lightning-type-generate`. Author an object-based CLT `<toolCLT>` (convention: `<toolApiName>`, the envelope), also with root-level `"lightning:tags": ["mcp"]`, and:
   - `actionName` → `lightning__textType`
   - `isSuccess` → `lightning__booleanType`
   - `outputValues` → **`c__<responseCLT>`** (the referenced-CLT pattern; the response CLT must be deployed before the envelope CLT)

3. **Widget** — load `platform-widget-generate`. Author a **flat** widget whose `schema.json` properties are the `payloadFields` (name + primitive type) — a standalone widget contract, not derived from or coupled to any Lightning Type. It renders **only `outputValues` data fields**: never `actionName`/`isSuccess` (envelope-only). The widget body binds each field via `{!$attrs.<field>}` — the widget is envelope-agnostic and never references `outputValues` itself.

4. **Default renderer (authored inline in the ENVELOPE CLT — never optional).** FIRST Read `platform-custom-lightning-type-generate/references/widget-rendition.md` (REQUIRED — do NOT author from memory or copy an existing sample, which may use a deprecated shape). Then author `<pkgDir>/lightningTypes/<toolCLT>/renderer.json` — the **default renderer, at the bundle root, parallel to `schema.json`** (NOT under `lightningDesktopGenAi/`). Its `renderer.componentOverrides["$"]` sets `definition` to `@widget/c/<widgetName>` and maps **every widget schema property** to the matching payload field nested under the envelope's `outputValues` node via `{!$attrs.outputValues.<payloadField>}` — the nested binding that bridges the envelope CLT to the flat widget. Do **NOT** duplicate the widget body inside `renderer.json`. The worked JSON is in `references/two-clt-modeling.md`.

**Existing-renderer handling:** if `renderer.json` already exists at the target path, read it first. If it references the same widget with the same bindings, leave it. If it references a different widget or a custom-LWC root override (`c/<component>`), STOP and surface the conflict before overwriting.

---

## Phase 5 — Validation gates

Read `references/validation-gates.md` (REQUIRED — it holds the RUN procedure and exact pass/fail predicates for each gate) and **run every gate**. Widget-bundle-internal checks (schema parse, root keys, leaf types, `{!$attrs.X}` resolution, `.uiwidget-meta.xml` well-formedness) are owned by `platform-widget-generate` and run in its own self-validation.

**Hard — block on failure:**

1. `clt-reference-integrity` — envelope `outputValues` typed `c__<responseCLT>`, the response CLT exists and both parse, no `$schema`/`items`, every non-primitive response property an `@apexClassType/...` reference (never a bare object or CLT-level `lightning__listType`).
2. `renderer-wires-widget` — the bundle-root `renderer.json` wires `@widget/c/<widgetName>` and binds every widget property under `outputValues` at the depth the describe dictates (two segments for a top-level primitive or list output, three for a leaf/list inside a wrapper object). Bidirectional: missing or extra bindings both fail.
3. `nested-list-coverage` — every nested-object and list field discovered in Phase 2 is rendered by the widget and bound at the correct depth. "Out of scope" / "beta single-response" are NOT valid drop rationales.

**Warn — advisory:**

1. `field-trace` — RUN the trace in `references/validation-gates.md`: enumerate response fields, `jq` the widget schema keys, classify INVENTED vs OMITTED. Invented widget fields fail; an omitted response data field warns.

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
  clt-reference-integrity (envelope.outputValues → c__<responseCLT>; nested → @apexClassType): <pass | fail (<reason>)>
  renderer-wires-widget (nested {!$attrs.outputValues.X} bindings): <pass | fail (<reason>)>
  nested-list-coverage (every discovered nested/list field rendered): <pass | fail (<reason>)>
  field-trace (INVENTED + OMITTED lists printed): <pass | warn (<reason>) | fail (invented: <list>)>
```

---

## Hard Rules (always apply)

1. **Plan-first, then proceed.** Print the full Phase 3 build plan before writing any file. Explicit rejection or a change request → stop and revise; otherwise continue. The invariant is the plan being visible in the transcript, not an interactive human approval — this holds in manual chat, agent-to-agent flows, and single-turn evals.
2. **Two object-based CLTs, never one.** The envelope and the payload are separate CLTs. The envelope's `outputValues` is typed via `c__<responseCLT>`, never inlined as a nested `lightning__objectType`. Both CLTs carry root-level `"lightning:tags": ["mcp"]` (see `platform-custom-lightning-type-generate/assets/primitive-types-and-constraints.md`).
3. **Renderer lives in the ENVELOPE CLT, at the bundle root.** `lightningTypes/<toolCLT>/renderer.json` — the default renderer, parallel to `schema.json`. Never `lightningDesktopGenAi/renderer.json` (that is the agent-action flow's surface-specific path), never in the response CLT.
4. **Renderer bindings are nested.** Every widget attribute maps to `{!$attrs.outputValues.<field>}`, not `{!$attrs.<field>}`. The widget schema stays flat; the renderer does the bridging.
5. **Widget grounds on the payload, not the envelope.** The widget schema properties are the payload (`outputValues`) fields. The widget never references `actionName` or `isSuccess` — those are envelope-only fields on the envelope CLT.
6. **Field source depends on class role.** The **top-level response class** is gated by `@InvocableVariable` — the describe surfaces exactly those fields, so a top-level field carrying only `@AuraEnabled` (or no annotation) is correctly *not* an output; enumerate the top-level response class by `@InvocableVariable` and exclude the request class and private helper classes. An **inner/referenced class** reached via `@apexClassType/<ns>__<Outer>$<Inner>` is enumerated by its **public / `@AuraEnabled`** members instead — its leaves are never in the describe and `@InvocableVariable` is not used there, so grepping it for `@InvocableVariable` yields zero leaves (empty CLT + widget).
7. **No invented fields.** The widget schema (and the response CLT) must be a subset of the fields the tool actually exposes — top-level `@InvocableVariable` outputs plus the public/`@AuraEnabled` leaves of any referenced inner class — never a property no class exposes. `field-trace` prints both lists.
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
| `references/mcp-tool-output-discovery.md` | Phase 2 — the three sources, field enumeration, and type mapping. |
| `references/two-clt-modeling.md` | Phase 4 — envelope + response CLTs, the nested renderer binding, naming convention, and nested-object handling. |
| `references/build-plan-format.md` | Phase 3 — plan template. |
| `references/validation-gates.md` | Phase 5 — full hard / warn gate table with RUN procedures. |
| `examples/action-name-source-prompt.md` | Phase 3 — walkthrough from an invocable action API name (preferred). |
| `examples/apex-invocable-source-prompt.md` | Phase 3 — walkthrough from an Apex Invocable class (fallback). |
| `examples/pasted-tool-output-prompt.md` | Phase 3 — walkthrough from a pasted tool-output sample (fallback). |
| `examples/nested-object-single-source-prompt.md` | Phase 3 — single Apex-class-reference payload field. |
| `examples/nested-object-list-source-prompt.md` | Phase 3 — top-level list and list-inside-wrapper. |
