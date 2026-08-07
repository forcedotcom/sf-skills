---
name: platform-widget-generate
description: "Use this skill to author a complete HXL WidgetBundle (UEM body + schema.json + -meta.xml). TRIGGER when: user asks for a widget, mosaic, fragment, card, or rich UI surface for any subject, domain, feature, or entity noun; the prompt names only an entity or data shape without invoking Lightning Types, CLTs, or Apex-backed types. DO NOT TRIGGER when: the prompt explicitly says 'Lightning Type', 'CLT', 'Custom Lightning Type', 'Apex-backed type', or references '@apexClassType/...' (use platform-lightning-type-widget-coordinate); authoring a custom-LWC renderer for a Custom Lightning Type (use platform-custom-lightning-type-generate); or editing only an LWC component."
metadata:
  version: "1.1"
  minApiVersion: "68.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-custom-lightning-type-generate"
    - "platform-lightning-type-widget-coordinate"
  mcpTools:
    metadata-experts:
      tools: ["execute_metadata_action"]
      semver: ">=1.0.0"
---

# Generating a Widget Bundle

Author a complete WidgetBundle: a UEM tree (`tile/widget`), a JSON Schema describing the widget's input contract, and the `.uiwidget-meta.xml` that registers the bundle.

## When to Use This Skill

Use when the user asks for a widget, mosaic, fragment, or card-style rich UI surface. Do not use this skill for custom-LWC renderers or for `renderer.json` files inside a Custom Lightning Type bundle — those belong to `platform-custom-lightning-type-generate`.

## Inputs

- **`widgetName`** (required) — `camelCase` identifier; becomes the directory name under `uiWidgets/`.
- A **shape** — what data the widget renders. The widget cannot be generated without it. The shape arrives one of two ways, in priority order:
  1. **`lightningTypeSchema`** — `{ path, apexClassFqn }` for an existing Apex-backed Lightning Type. The FQN takes one of two forms: outer-class (`<namespace>__<ClassName>`) where the outer class is the payload, or inner-class (`<namespace>__<ClassName>$<InnerClass>`) where the named inner class is the payload. Passed in by the `platform-lightning-type-widget-coordinate` orchestrator. When present, derive per `references/schema-from-lightning-type.md`.
  2. **Extracted from the user's prompt** — when no `lightningTypeSchema` is passed, infer the shape directly from what the user wrote: a pasted JSON payload, an enumerated field list ("id as string, total as number"), or descriptive prose. The output is the same ordered list of `{ name, type, required }` either way.

If neither source yields a shape, STOP and ask the user before proceeding.

## Output

Three files in `<pkgDir>/uiWidgets/<widgetName>/`:

| File | Content |
|---|---|
| `<widgetName>.json` | Widget envelope — `{ "type": "lightning__agentforceWidget", "contentBody": { "widgetBody": { UEM tree rooted at tile/widget } } }` |
| `schema.json` | JSON Schema — root has `type: "object"` + `properties.attributes` wrapper carrying `lightning:type: "lightning__objectType"` and the field `properties` |
| `<widgetName>.uiwidget-meta.xml` | `<UiWidgetBundle>` element with `<masterLabel>`, `<description>`, and `<widgetType>JSON</widgetType>` |

See `references/widget-bundle-layout.md` for the `<pkgDir>` resolution procedure and the exact `<widgetName>.uiwidget-meta.xml` shape.

---

## Composition

A widget body is a UEM tree of blocks nested under `contentBody.widgetBody`. The root node is `tile/widget`. Every node — root and non-root — has the same shape: no `type` key; just `definition`, optional `attributes`, optional `meta`, and optional `children`. Block shape:

```ts
interface Block {
  definition: string  // {namespace}/{blockName} — root is "tile/widget"
  attributes?: Record<string, any>
  meta?: { // see references/widget-meta-directives.md
    forEach?: string
    forItem?: string
    if?: string
  }
  children?: Block[]
}
```

The first child of `tile/widget.children` SHOULD be a single `tile/column` (or a single `tile/card`). All widget content typically goes inside that first child for predictable vertical structure across surfaces.

---

## Available Metadata Actions

### discoverUiComponents

**Purpose:** Discover the palette of blocks available for composition.

**Required parameters:** `actionName: "discoverUiComponents"`, `metadataType: "FRAGMENT"`, `parameters.pageType: "FRAGMENT"`. Optional: `searchQuery` to filter by name/description.

**Returns:** list of `{ definition, description, label, attributes? }`.

### getUiComponentSchemas

**Purpose:** Fetch JSON schemas (property types, required vs optional, validation) for selected blocks.

**Required parameters:** `actionName: "getUiComponentSchemas"`, `metadataType: "FRAGMENT"`, `parameters.pageType: "FRAGMENT"`, `parameters.componentDefinitions: ["namespace/definition", ...]`. Optional: `includeKnowledge` (default `true`).

**Returns:** `componentSchemas[]` — success entries carry the JSON schema, failure entries carry an error message. Partial failures are supported.

> Never pass `tile/widget` to `getUiComponentSchemas` — it is a fixed wrapper, not a queryable component.

---

## Attribute Binding

- Bind a block property to runtime data with `{!$attrs.<attrName>}`. `<attrName>` MUST match a property name in `schema.json`.
- Inside a `forEach`, reference the loop variable instead — e.g. `"text": "{!$item.name}"`. See `references/widget-meta-directives.md`.

---

## Layout Best Practices

These conventions cover widget *structure* — how blocks are grouped and stacked.

| Primitive | Purpose | When to use |
|---|---|---|
| `tile/column` | Vertical stack of children | Root wrapper, and any group of blocks that should stack |
| `tile/row` | Horizontal stack of children | Two or more blocks that belong on the same line |
| `tile/card` | Visually-boxed group | A bounded section that should read as one unit |
| `tile/spacer` | Whitespace between blocks | When extra space is needed between content groups |

- **Sectioning:** Separate major content groups with a fresh `tile/card`-bounded section. Do not nest cards inside cards.
- **Nesting:** Prefer flat layouts. Only nest a `tile/column` inside a `tile/row` (or vice versa) when the visual orientation actually changes for that subgroup.
- **Authoritative palette:** the table above lists *typical* layout primitives. Always confirm a block exists by inspecting `discoverUiComponents` output — do not assume a block name from this table without seeing it in the discovery response.

---

## Styling Best Practices

Widgets express *intent*, not pixels. Each surface provides a default look and feel; brand/theme overrides apply automatically.

- **Style semantically.** Use `variant`, `size`, and other enum-typed attributes (`primary`, `destructive`, `success`, `warning`). Do not pin literal colors or pixel values.
- **One primary action per visible group.** At most one `tile/button` with `variant: primary`. Use `secondary`, `outline`, or `ghost` for additional actions.
- **One `h1` per widget.** Use `h2`/`h3` for sub-section headings, `body` for prose, `caption` for helper text.
- **Use semantic state variants on state-bearing blocks** (`tile/alert`, `tile/badge`, `tile/callout`, `tile/chip`).
- **Accept schema defaults for `gap`, `padding`, `size`** unless there is a specific reason to override.
- **Don't pin `width`, `height`, `maxWidth`** unless a content constraint requires it. For long text, use `truncate: true`.
- **Use the Lucide icon set.** Pass the Lucide name (`"check"`, `"alert-circle"`); other icon libraries are not supported.

---

## Workflow

1. **Resolve the widget spec** — an ordered list of `{ name, type, required }`. Source depends on which input was provided (see *Inputs*):
   - If `lightningTypeSchema` was passed by the orchestrator → derive per `references/schema-from-lightning-type.md`.
   - Otherwise → infer the list directly from the user prompt (pasted JSON payload, enumerated field list, or descriptive prose).

2. **Discover blocks (REQUIRED — do NOT skip).** Call the `discoverUiComponents` metadata action via `execute_metadata_action`. Use property types from the widget spec to seed `searchQuery` (text → `"text"`, number → `"number"`). **If `discoverUiComponents` returns `success: false`, an error, or an empty list, STOP and surface the error verbatim — do not improvise block names from memory, prior runs, or training data. Re-run discover with a different `searchQuery` only if the failure is search-query-specific.**

3. **Select blocks.** Choose one block per widget-spec property, plus structural primitives from *Layout Best Practices*.

4. **Get block schemas (REQUIRED — do NOT skip).** Call the `getUiComponentSchemas` metadata action via `execute_metadata_action` for the selected blocks. Review property metadata. **If `componentSchemas` returns all-failure or empty, STOP and surface the error — do not improvise from existing widgets in the project.**

5. **Build the UEM tree (example reads REQUIRED — do NOT skip).** First, identify which patterns match the widget spec and read each matching example file from this skill's own `examples/` directory (`<skill-root>/examples/`):

   | Pattern in the spec | Example to read |
   |---|---|
   | Single object (no iteration) | `<skill-root>/examples/single-object.json` |
   | Any list iteration (root-level array, nested list, or list embedded in a single-object widget) | `<skill-root>/examples/list-with-foreach.json` |
   | Conditional rendering (`if` bound to a boolean) | `<skill-root>/examples/conditional.json` |

   A spec may match multiple patterns (e.g. a list of items where some items render conditionally reads both `list-with-foreach.json` and `conditional.json`). **Read every matching example, and only those — do not skip the read because the pattern feels familiar.**

   Then:
   - Map each widget-spec property to a block property; preserve spec order.
   - **Decide root iteration:** single object → properties directly under root `tile/column`. Collection → wrap repeating block in `forEach`/`forItem`. See `references/widget-meta-directives.md`.
   - Bind values with `{!$attrs.X}` (or `{!$item.X}` inside `forEach`).
   - For conditional blocks, add `"if"` on `meta` — only when the schema has a matching `lightning__booleanType` property.

6. **Author `schema.json`.** Build the JSON Schema from the widget spec. Fields live one level deep under an `attributes` wrapper:

   ```json
   {
     "title": "<Widget Display Name>",
     "description": "<one line about what the widget shows>",
     "type": "object",
     "properties": {
       "attributes": {
         "lightning:type": "lightning__objectType",
         "properties": {
           "<propertyName>": {
             "title": "<label>",
             "description": "<short description>",
             "lightning:type": "<lightning__textType | lightning__numberType | ...>"
           }
         }
       }
     }
   }
   ```

   **Required root keys:** `title`, `type: "object"`, `properties.attributes` (with `lightning:type: "lightning__objectType"` and a nested `properties` map). See `references/schema-from-lightning-type.md` for full primitive type guidance.

7. **Author `<widgetName>.uiwidget-meta.xml`.** See `references/widget-bundle-layout.md` for the exact shape.

8. **Resolve `<pkgDir>` and write the bundle.** Follow the procedure in `references/widget-bundle-layout.md` (`## Resolving <pkgDir>`). A widget bundle is a **three-file set** — all three files must be written in the same step; a bundle with fewer than three files is incomplete and will not deploy.

   ```text
   <pkgDir>/uiWidgets/<widgetName>/<widgetName>.json               # widget envelope — UEM tree (primary artifact)
   <pkgDir>/uiWidgets/<widgetName>/schema.json                     # attribute contract for the envelope
   <pkgDir>/uiWidgets/<widgetName>/<widgetName>.uiwidget-meta.xml  # UiWidgetBundle registration
   ```

   Each file has a distinct role:
   - `<widgetName>.json` — the widget envelope with the `tile/widget` UEM tree. This is the primary artifact; `schema.json` is its companion contract, not a substitute.
   - `schema.json` — the JSON Schema for the attributes referenced by `{!$attrs.X}` bindings in the envelope.
   - `<widgetName>.uiwidget-meta.xml` — the `UiWidgetBundle` element that registers the bundle for source tracking and deployment.

   Write all three before proceeding to self-validation.

9. **Self-validate.** Before reporting, confirm each check below and report each result individually (`pass` or `fail (<reason>)`). Do **not** summarize as a single "all passed" line — list every check so a reviewer can spot a silent skip.
    - **`schema-parses`** — `<pkgDir>/uiWidgets/<widgetName>/schema.json` parses as JSON.
    - **`schema-root-keys`** — root has `title` (string), `type: "object"`, and `properties.attributes` (object) — where `properties.attributes` carries `lightning:type: "lightning__objectType"` and a nested `properties` map. No `unevaluatedProperties: false`.
    - **`schema-leaf-types`** — every leaf under `properties.attributes.properties` carries a `lightning:type`. Singular nested inner-class fields appear as `lightning__objectType`; the nested shape is not redeclared.
    - **`bindings-resolve`** — every `{!$attrs.X}` (or `{!$attrs.<outerField>.<innerField>}` for nested objects) in `<widgetName>.json` resolves to a property under `schema.json` `properties.attributes.properties`, and every `{!$item.X}` resolves to a `forItem` loop variable defined upstream.
    - **`body-envelope`** — `<widgetName>.json` root has `type: "lightning__agentforceWidget"` and a `contentBody` object whose `widgetBody` carries the UEM tree rooted at `tile/widget`. No node in the tree — root or non-root — carries a `type` key.
    - **`metaxml-wellformed`** — `<widgetName>.uiwidget-meta.xml` parses as well-formed XML.
    - **`metaxml-elements`** — `<widgetName>.uiwidget-meta.xml` has root `<UiWidgetBundle>` and contains `<masterLabel>` (non-empty), `<description>` (non-empty), and `<widgetType>JSON</widgetType>`.
    - **`files-present`** — all three files exist at the resolved `<pkgDir>/uiWidgets/<widgetName>/` path.

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| Block definitions follow `{namespace}/{blockName}` and must match `discoverUiComponents` output | Runtime resolves blocks by exact definition string |
| Never pass `tile/widget` to `getUiComponentSchemas` | It is a fixed wrapper, not a queryable component |
| Always supply `parameters` (with required keys) when calling `execute_metadata_action` | Missing parameters cause hard failure, not partial result |
| Every `{!$attrs.X}` in the body resolves to a property in the widget `schema.json` | No invented fields |
| No `$(…)`, backticks, `<(…)`, brace expansion `{a,b,c}`, or `eval`/`exec` in any Bash tool call | Vibes' safe-shell filter forces manual approval on these patterns even in Bypass mode. Emit separate commands (`mkdir -p a && mkdir -p b`) or print each value with its own command and reason about the output — do not capture into a shell variable |

---

## Gotchas

| Issue | Resolution |
|---|---|
| `getUiComponentSchemas` returns a partial-failure entry | Pick a different block from `discoverUiComponents`; do not silently continue without a schema |
| Body references `{!$attrs.foo}` but `foo` is not under `schema.json` `properties.attributes.properties` | Add `foo` to `schema.json` `properties.attributes.properties` OR remove the body reference |
| Output written outside `<pkgDir>/uiWidgets/<widgetName>/` | `<pkgDir>` = `<packageDirectories[].path>/main/default` (see `references/widget-bundle-layout.md`). Dropping the `main/default/` segment is the common cause of widgets landing at `force-app/uiWidgets/...` instead of `force-app/main/default/uiWidgets/...` |
| `if` bound to a non-boolean | Use `if` only when the schema has a `lightning__booleanType` property |

---

## Reference File Index

| File | When to read |
|---|---|
| `references/widget-meta-directives.md` | For `forEach` / `forItem` (iteration) and `if` (conditional rendering), including nested loops |
| `references/schema-from-lightning-type.md` | When `lightningTypeSchema` is provided; how to derive the widget `schema.json` from an Apex-backed Lightning Type |
| `references/widget-bundle-layout.md` | Folder layout, `-meta.xml` shape, `<pkgDir>` resolution rules |
| `examples/single-object.json` | Single-object pattern (root binding via `{!$attrs.X}`, no iteration) |
| `examples/list-with-foreach.json` | Any list-iteration case — root-level collections, nested lists, and lists embedded inside a single-object widget (e.g. iterating a `List<InnerClass>` inside an outer Apex payload) |
| `examples/conditional.json` | Conditional pattern (`if` on `meta`, including `if` + `forEach` together) |
