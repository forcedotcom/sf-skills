# Deriving Widget schema.json From a Lightning Type

When the orchestrator passes a `lightningTypeSchema` (with `path` and `apexClassFqn`), the widget bundle's `schema.json` is derived from the Apex class the Lightning Type references — not invented. The Lightning Type root points at the **outer Apex class** (`@apexClassType/<namespace>__<ClassName>`); that outer class's `@AuraEnabled` fields define the payload shape. Inner classes appear either as a **singular field** (e.g. `InnerClass field` on the outer class) or as a **list-element type** (e.g. `List<InnerClass>` on the outer class). In either case, the widget schema references the nested type by its own inner-class FQN (`@apexClassType/<namespace>__<OuterClass>$<InnerClass>`) — see step 4 below. This file documents the derivation rule.

> **Scope:** This guide covers Apex-backed Lightning Types only. The orchestrator (`platform-lightning-type-widget-coordinate`) only routes Apex-backed types into this skill. Object/JSON-based Lightning Types (Lightning Type root `lightning:type: "lightning__objectType"` with primitive `properties`) are out of scope here.

---

## Guidance

- The widget aligns to the Lightning Type's shape — it grounds on the `@AuraEnabled` fields of the Apex class the type references.
- The widget MUST NOT introduce properties the Apex class does not expose.
- **Default to including every `@AuraEnabled` field.** Omission is the exception, not the rule. Before dropping any field, confirm with the user — print the field, its Apex type, and the omission rationale (e.g. "audit timestamp, not user-facing"), and ASK before continuing. Silent omission is a hard violation; the orchestrator's P1.1 gate flags it.
- Fields that are typically safe to propose for omission *with user confirmation*: audit timestamps (`createdDate`, `lastModifiedDate`), system IDs that duplicate a primary key, and internal flags. **Domain-meaningful fields — including `List<InnerClass>` collections — are NEVER omitted silently.**

---

## Deriving from an Apex-backed Lightning Type

The Lightning Type root is minimal and points at the **outer Apex class**:

```json
{
  "title": "<TypeName>",
  "lightning:type": "@apexClassType/<namespace>__<ClassName>"
}
```

The widget cannot mirror this directly — the widget root is a plain `type: "object"` whose `properties.attributes` wrapper carries `lightning:type: "lightning__objectType"` and the actual field map. Derive the widget shape from the Apex class's `@AuraEnabled` fields:

1. Read the Apex class file (path provided by the orchestrator's Phase 4 output, or located via `<pkgDir>/classes/<ClassName>.cls`). The `apexClassFqn` from the orchestrator names the outer class.
2. **Enumerate every `@AuraEnabled` field on the outer class AND every field on each inner class referenced by a `List<Inner>` field or a singular inner-class field.** Default disposition is **include**. If you propose to drop any field, ASK the user first and record the rationale in the build plan's `Properties omitted:` section. Do not silently drop.
3. For each retained field, map the Apex type to the matching `lightning:type`:

   | Apex type | `lightning:type` (in widget schema) |
   |---|---|
   | `String`, `Id` | `lightning__textType` |
   | `Decimal`, `Double`, `Integer`, `Long` | `lightning__numberType` |
   | `Boolean` | `lightning__booleanType` |
   | `Date`, `Datetime` | `lightning__dateTimeType` |
   | `List<Primitive>` (e.g. `List<String>`) | `lightning__listType`, with `items.lightning:type` set to the matching primitive `lightning:type` from this table (e.g. `items.lightning:type: "lightning__textType"` for `List<String>`). |
   | `List<InnerClass>` | `lightning__listType`, with `items.lightning:type` set to the inner Apex class reference (see step 4). The widget body MUST also iterate this list with `forEach`/`forItem` and bind every `@AuraEnabled` field on `InnerClass` via `{!$item.<innerField>}`. See `references/widget-meta-directives.md`. |
   | `InnerClass` (singular field) | `lightning:type` set directly to the inner Apex class reference (see step 4). Bind its fields via `{!$attrs.<outerField>.<innerField>}`. |

4. Build the widget `schema.json`. **Every `@AuraEnabled` field on the outer class** that survived step 2 MUST appear as an entry under `properties.attributes.properties`.

   For any field whose type is an inner Apex class — whether a singular field or a `List<InnerClass>` — the property (or, for a list, its `items`) MUST reference the inner Apex class type directly, using the same `@apexClassType/<namespace>__<OuterClass>$<InnerClass>` form as the Lightning Type root, with `<InnerClass>` naming the nested class as declared inside the outer class. Do not redeclare the inner class's fields inline:

   ```json
   "<listFieldName>": {
     "title": "<List Field Label>",
     "description": "<short description>",
     "lightning:type": "lightning__listType",
     "items": {
       "lightning:type": "@apexClassType/<namespace>__<OuterClass>$<InnerClass>"
     }
   },
   "<singularInnerFieldName>": {
     "title": "<Field Label>",
     "description": "<short description>",
     "lightning:type": "@apexClassType/<namespace>__<OuterClass>$<InnerClass>"
   }
   ```

   This is the only case where a widget schema property carries an `@apexClassType/...` reference instead of a primitive `lightning:type` — it lets the runtime resolve the inner class's own `@AuraEnabled` fields without the widget schema duplicating them. For a list, inner-class fields are reached in the widget body via the `forEach`/`forItem` loop variable (`{!$item.<innerField>}`); for a singular field, via `{!$attrs.<outerField>.<innerField>}` — neither case gets a separate nested `properties` entry in the schema.

   ```json
   {
     "title": "<WidgetDisplayName>",
     "description": "<one line about what the widget renders>",
     "type": "object",
     "properties": {
       "attributes": {
         "lightning:type": "lightning__objectType",
         "properties": {
           "<textFieldName>":     { "title": "<Text Field Label>",      "lightning:type": "lightning__textType" },
           "<numberFieldName>":   { "title": "<Number Field Label>",    "lightning:type": "lightning__numberType" },
           "<dateTimeFieldName>": { "title": "<Date/Time Field Label>", "lightning:type": "lightning__dateTimeType" },
           "<listFieldName>":     { "title": "<List Field Label>",      "lightning:type": "lightning__listType", "items": { "lightning:type": "<primitive lightning:type, or an inner-class @apexClassType/... reference>" } }
         }
       }
     }
   }
   ```

---

## Reachability check

Before authoring the widget body, confirm every property you plan to bind via `{!$attrs.X}` exists in the derived widget `schema.json`. The orchestrator's P0.4 gate enforces this; the leaf skill must self-check first to avoid round-trips.

---

## Out of scope

- Renaming Apex class fields for display. The widget schema must use the same names as the Apex class. Display labels are carried in `title` only.
- Synthesizing properties not present on the resolved payload class. This includes computed/derived fields and any field the Apex class does not currently expose. **`platform-widget-generate` MUST NOT edit `.cls` files.** If the widget body needs a field that is missing (for example, a `lightning__booleanType` to drive `meta.if`), STOP and surface the gap to the orchestrator — name the missing field, its expected type, and why the widget needs it. The orchestrator decides whether to amend the Apex class (via `platform-apex-generate`) or revise the widget plan.
