---
name: generating-custom-lightning-type
description: "Use this skill when users need to create Custom Lightning Types (CLTs) for Einstein Agent actions or structured input/output schemas. Trigger when users mention CLT, Custom Lightning Types, JSON schemas for agents, type definitions, lightning__objectType, or editor/renderer configurations. This is complex - always use this skill for CLT work."
---

## When to Use This Skill

Use this skill when you need to:
- Create Custom Lightning Types (CLTs) for structured inputs/outputs
- Generate JSON Schema-based type definitions for Lightning Platform
- Configure CLTs for Einstein Agent actions
- Set up editor and renderer configurations for custom UI
- Troubleshoot deployment errors related to Custom Lightning Types

## Specification

# CustomLightningType Metadata Specification

## Overview & Purpose
Custom Lightning Types (CLTs) are JSON Schema-based type definitions used by the Lightning Platform (including Einstein Agent actions) to describe structured inputs/outputs and drive editor/renderer experiences.

## Configuration
- **Choose referenced CLT pattern for nested objects** - When you need a **reusable** or **separately deployed** nested type, create a CLT for that shape and reference it with `"lightning:type": "c__<CLTName>"`. That string is the referenced type’s **`lightning:type` value / FQN / registered identifier** — not the JSON Schema `title`.
- **Choose standard Lightning types** when the structure is simple and can be expressed with properties and supported primitive `lightning:type` identifiers.
- **Choose Apex class types** (`@apexClassType/...`) when the structure already exists server-side and you want the Apex class to define the shape.
- **Include editor/renderer config** only when you need custom UI behavior (custom LWC input/output components). Otherwise, omit.

## Critical Rules (Read First)
- **Root object schemas MUST include**:
  - `"type": "object"`
  - `"title"`
  - `"lightning:type": "lightning__objectType"`
  - `"unevaluatedProperties": false`
- `"unevaluatedProperties"` is enforced as `false` by the CLT metaschema. Do not set it to `true`.
- **Root object schemas MUST NOT include** `"examples"` when `"unevaluatedProperties": false` is set.
- **Nested objects (inside `properties`) MUST NOT set** `"lightning:type": "lightning__objectType"`.
    - Nested objects can be: references to other CLTs using `c__<CLTName>` syntax.
- **List/array properties are highly restricted by the CLT metaschema**:
  - **CRITICAL LIMITATION**: the CLT metaschema may reject the `items` keyword entirely. Treat `items` as **disallowed by default**.
  - **Root-level arrays** (direct children of the root `properties`):
    - **MUST include** `"lightning:type": "lightning__listType"`
    - **MUST NOT include** `"items"`
    - **OPTIONAL** `"type": "array"`
  - **Nested arrays** (arrays inside nested objects) are the most common failure:
    - **MUST include** `"type": "array"`
    - **MUST NOT include** `"lightning:type": "lightning__listType"`
    - **MUST NOT include** `"items"`
- **When `"unevaluatedProperties": false` is set, any unknown keyword will fail validation**. Prefer removing keywords over relaxing strictness.
- **Apex class CLTs are minimal**:
  - Include **only** `title`, `description` (optional), and `lightning:type` set to `@apexClassType/...`.
  - Do **not** add `type`, `properties`, `required`, or `unevaluatedProperties`.

## Additional CLT Metaschema Validations
- **Org namespace validation**: titles/descriptions and other string fields may be validated to ensure you are not using an org namespace in places that are disallowed.
- **Lightning type validation**: CLTs are validated to prevent referencing internal namespaces (for example, disallowing types from internal namespaces like `sfdc_cms` where not permitted).
- **Object type validation**: the CLT root is validated to ensure `lightning:type` is exactly `lightning__objectType`.

## Primitive Types & Constraints
- `lightning__textType`
  - Max length 255
- `lightning__multilineTextType`
  - Max length 2000
- `lightning__richTextType`
  - Max length 100000
- `lightning__urlType`
  - Max length 2000
  - Optional `lightning:allowedUrlSchemes` enum values: `https`, `http`, `relative`, `mailto`, `tel`
- `lightning__dateType`
  - Data pattern: YYYY-MM-DD
- `lightning__timeType`
  - Data pattern: HH:MM:SS.sssZ
- `lightning__dateTimeType`
  - Data shape is an object with required `dateTime` and optional `timeZone`
- `lightning__numberType`
  - Decimal numbers; optional `maximum`, `minimum`, `multipleOf`
- `lightning__integerType`
  - Whole numbers only; optional `maximum`, `minimum`
- `lightning__booleanType`
  - true/false

## Allowed Property-Level Keywords
When strict validation is enabled (`unevaluatedProperties: false`), keep each property minimal and prefer only keywords known to be allowed:
- `title`, `description`, `einstein:description`
- `type` (when used, ensure it matches the chosen `lightning:type`)
- `lightning:type`
- `maximum`, `minimum`, `multipleOf` (numeric)
- `maxLength`, `minLength` (string)
- `const`, `enum`
- `lightning:textIndexed`, `lightning:supportsPersonalization`, `lightning:localizable`
- `lightning:uiOptions`, `lightning:allowedUrlSchemes`
- `lightning:tags` (metaschema restricts values; currently `flow` is the only known allowed tag)

## Generation Workflow
1. **Confirm the CLT approach**
   - If referencing Apex: capture the exact class reference (`@apexClassType/namespace__ClassName$InnerClass`).
   - If using standard primitives: list the fields, their Lightning primitive types, and which fields are required.
2. **Draft `schema.json`**
   - Start with the root object structure (required root fields).
   - Add `properties` using valid primitive `lightning:type` identifiers.
   - For nested-object properties, use **CLT Reference pattern**:
     - `"lightning:type": "c__<CLTName>"` to reference another CLT
     - The referenced CLT must be deployed to the org before the parent CLT.
   - For Apex-based nested objects: Use `@apexClassType/...` when structure exists server-side.
   - If the prompt explicitly requires true nested object output, prefer an **Apex-based CLT** (`@apexClassType/...`) for deploy-safe nested structures.
   - For arrays: follow the strict list rules (avoid `items`; avoid `lightning:type` on nested arrays).
   - Before deployment, verify exact `lightning:type` spellings (for example, use `lightning__richTextType`, not misspelled variants).
3. **(Optional) Draft `editor.json`** (only if custom UI is required)
   - **Supported shape:** Top-level `editor` object with `editor.componentOverrides` and `editor.layout`.
     - Top-level `editor` object.
     - Use `editor.componentOverrides` for component overrides.
     - Use `editor.layout` for layout.
     - **DEPRECATED**: Do NOT use `propertyRenderers` or `view` — these are legacy keys. Always use `componentOverrides` and `layout` instead.
   - **Root override pattern** (most common for fully custom editing UI):
     - `editor.componentOverrides["$"] = { "definition": "c/<yourEditorComponent>", "attributes": { ... } }`
     - When passing schema data into a custom LWC, use attribute mapping with the `{!$attrs.<name>}` syntax: e.g. `"attributes": { "myField": "{!$attrs.value}" }` so the runtime binds schema values to your component's attributes.
     - **CRITICAL**: The `<name>` in `{!$attrs.<name>}` must be a property defined in your type schema. For example, if your schema has a property called `temperature`, use `{!$attrs.temperature}`, not `{!$attrs.value}` unless `value` is an actual property.
   - **Property-level override pattern** (for individual fields):
     - `editor.componentOverrides["<propertyName>"] = { "definition": "es_property_editors/<...>" }`
     - **Valid editor components** (examples): `es_property_editors/inputText`, `es_property_editors/inputNumber`, `es_property_editors/inputRichText`, `es_property_editors/inputImage`, `es_property_editors/inputTextarea`. **Do not use** `es_property_editors/inputList`.
   - **Collection editor** (for root-level `lightning__listType` properties): Use a collection-level override so the list is edited by a custom component: `collection.editor.componentOverrides["$"] = { "definition": "c/<yourCollectionEditorComponent>" }`. Alternatively, use `editor.layout` with `lightning/propertyLayout` and `attributes.property = "<listPropertyName>"` for default list editing.
   - **Layout pattern**:
     - `editor.layout.definition = "lightning/verticalLayout"`
     - `editor.layout.children[*].definition = "lightning/propertyLayout"` with `attributes.property = "<propertyName>"`
     - **CRITICAL**: `lightning/propertyLayout` only accepts the `property` attribute. Do NOT add `label`, `title`, or any other attributes — these will fail validation with `additionalProperties: false` errors.
   - **Avoid known-invalid patterns**:
     - Do not use `es_property_editors/inputList`.
     - Do not use `itemSchema` attributes.
4. **(Optional) Draft `renderer.json`** (only if custom UI is required)
   - **Supported shape:** Top-level `renderer` object with `renderer.componentOverrides` and `renderer.layout`.
     - Top-level `renderer` object.
     - Use `renderer.componentOverrides` for component overrides.
     - Use `renderer.layout` for layout.
     - **DEPRECATED**: Do NOT use `propertyRenderers` or `view` — these are legacy keys. Always use `componentOverrides` and `layout` instead.
   - **Root override pattern** (most common for fully custom rendering UI):
     - `renderer.componentOverrides["$"] = { "definition": "c/<yourRendererComponent>", "attributes": { ... } }`
     - Use `{!$attrs.<name>}` in attribute mappings when binding schema data to custom renderer component attributes.
     - **CRITICAL**: Attribute mappings like `{!$attrs.propertyName}` must reference properties that **actually exist** in your type schema. Referencing non-existent properties will fail validation.
     - **Type matching**: Attribute values must match the expected type for the component. For example, if a component expects a string attribute, passing an integer will fail validation.
   - **Property-level override pattern**:
     - `renderer.componentOverrides["<propertyName>"] = { "definition": "es_property_editors/outputText" | "es_property_editors/outputNumber" | "es_property_editors/outputImage" | ... }`. **Valid renderer components** (examples): `es_property_editors/outputText`, `es_property_editors/outputNumber`, `es_property_editors/outputImage`. Avoid input-style components in the renderer.
   - **Layout pattern for renderer**:
     - `renderer.layout.definition = "lightning/verticalLayout"`
     - `renderer.layout.children[*].definition = "lightning/propertyLayout"` with `attributes.property = "<propertyName>"`
     - **CRITICAL**: Same as editor layouts, `lightning/propertyLayout` only accepts the `property` attribute. Do NOT add `label`, `title`, or any other attributes.
   - **Collection renderer** (for root-level `lightning__listType` properties): Use `collection.renderer.componentOverrides["$"] = { "definition": "c/<yourListRendererComponent>" }` or `es_property_editors/genericListTypeRenderer` to render the list.
5. **Place files in the correct bundle structure**
   - `lightningTypes/<TypeName>/schema.json`
   - (Optional) `lightningTypes/<TypeName>/lightningDesktopGenAi/editor.json`
   - (Optional) `lightningTypes/<TypeName>/lightningDesktopGenAi/renderer.json`
   - For Gen AI / Copilot the standard path is `lightningDesktopGenAi/`. Other targets (e.g. Experience Builder, Mobile Copilot, Enhanced Web Chat) use different subfolders when supported: `experienceBuilder/`, `lightningMobileGenAi/`, `enhancedWebChat/`.
6. **Configure custom LWC components (if using custom components)**
   - **CRITICAL**: Custom LWC components referenced in editor/renderer configs MUST have the correct target configuration in their `-meta.xml` files:
     - **For editor components** (`c/<componentName>` used in `editor.json`): The LWC's `-meta.xml` file must include `<target>lightning__AgentforceInput</target>`
     - **For renderer components** (`c/<componentName>` used in `renderer.json`): The LWC's `-meta.xml` file must include `<target>lightning__AgentforceOutput</target>`
   - Without the correct target, deployment will fail with: `Invalid target configuration. To use 'c/componentName' as a renderer/editor, your js-meta.xml file must include valid target 'lightning__AgentforceOutput/Input'.`
   - Example `-meta.xml` for a renderer component:
     ```xml
     <?xml version="1.0" encoding="UTF-8"?>
     <LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
         <apiVersion>60.0</apiVersion>
         <isExposed>true</isExposed>
         <targets>
             <target>lightning__AgentforceOutput</target>
         </targets>
     </LightningComponentBundle>
     ```
7. **Deploy and validate**
   - Run a final schema sanity check before deploy: valid `lightning:type` names, required fields present, and no disallowed keywords.
   - Deploy the bundle using your org's standard metadata deployment flow (e.g. Salesforce CLI or IDE). The MCP client or tooling in use should provide or integrate with the appropriate deploy/retrieve commands for Lightning Type bundles.
   - Validate incrementally: if deployment fails, remove disallowed keywords first (especially `examples`, `items`, nested `lightning:type`).

## Common Deployment Errors
| Error / Symptom | Likely Cause | Fix |
|---|---|---|
| Schema validation fails due to unknown keyword | `unevaluatedProperties: false` + disallowed keyword (commonly `examples`, `items`) | Remove the offending keyword; keep schema minimal |
| Nested object validation failure | Org/channel validation rejects nested object typing in `LightningTypeBundle` | Use CLT reference (`c__<CLTName>`) or Apex class types |
| Invalid CLT reference | Referenced CLT doesn't exist in org or incorrect syntax | Deploy the referenced CLT first; `c__<CLTName>` must match the referenced type’s **`lightning:type` value / FQN / registered identifier**, not `title` |
| Invalid or misspelled `lightning:type` (for example, `lightning__richtextType` instead of `lightning__richTextType`) | Incorrect generated type name | Cross-check all `lightning:type` values against supported type names and correct them before deployment |
| Array property rejected | Use of `items` (or `lightning:type` in nested arrays) rejected by validator | For nested arrays: keep only `type: "array"`. For root arrays: use minimal structure; remove `items` if rejected |
| Apex-based CLT rejected | Extra fields added (e.g., `type`, `properties`) | Use only `title`, optional `description`, and `lightning:type` |
| Editor config rejected | Use of invalid patterns (`es_property_editors/inputList`, `itemSchema`) or unrecognized top-level keys | Use `editor.componentOverrides` and `editor.layout`; keep config minimal |
| `additionalProperties` error on layout attributes | Adding `label` or other attributes to `lightning/propertyLayout` | Only use `property` attribute in `lightning/propertyLayout`. Remove `label`, `title`, or any other attributes |
| Invalid target configuration for custom LWC | Custom LWC component's `-meta.xml` missing required target (`lightning__AgentforceInput` or `lightning__AgentforceOutput`) | Add correct target to LWC's `-meta.xml`: use `lightning__AgentforceInput` for editors, `lightning__AgentforceOutput` for renderers |
| Attribute mapping doesn't exist in type schema | Using `{!$attrs.propertyName}` where `propertyName` is not defined in schema | Ensure all attribute mappings reference actual properties in your type schema's `properties` section |
| `additionalProperties` error with deprecated keys | Using `propertyRenderers` or `view` in editor/renderer config | Replace deprecated `propertyRenderers` with `componentOverrides` and `view` with `layout` |
| Type mismatch in component attributes | Passing wrong type for component attribute (e.g., integer instead of string) | Ensure attribute values match the expected type defined by the component |

## Verification Checklist
- [ ] Root schema has `type: "object"`, `title`, `lightning:type: "lightning__objectType"`, and `unevaluatedProperties: false`
- [ ] Root schema does not include `examples` when strict validation is enabled
- [ ] No nested object includes `lightning:type: "lightning__objectType"`
- [ ] Arrays are defined minimally (especially nested arrays)
- [ ] Only supported primitive `lightning:type` identifiers are used for leaf properties
- [ ] Apex class CLTs contain only `title`/`description` and `lightning:type: "@apexClassType/..."`
- [ ] Bundle structure and filenames match Lightning Types requirements
- [ ] Editor config uses only allowed patterns (no `es_property_editors/inputList`, no `itemSchema`); use valid components (e.g. `es_property_editors/inputText`, `es_property_editors/inputNumber`) or custom `c/` components
- [ ] Renderer config uses output-style components (e.g. `es_property_editors/outputText`, `es_property_editors/outputNumber`) where applicable, not input editors
- [ ] Layout configurations use `lightning/propertyLayout` with ONLY the `property` attribute (no `label`, `title`, or other attributes)
- [ ] All attribute mappings (`{!$attrs.propertyName}`) reference properties that exist in the type schema
- [ ] Custom LWC components have correct targets in `-meta.xml`: `lightning__AgentforceInput` for editors, `lightning__AgentforceOutput` for renderers
