# Deriving Widget schema.json From a Lightning Type

When the orchestrator passes a `lightningTypeSchema` (with `path` and `apexClassFqn`), the widget bundle's `schema.json` is derived from the Apex class the Lightning Type references — not invented. The Lightning Type root points at the **outer Apex class** (`@apexClassType/<namespace>__<ClassName>`); that outer class's `@AuraEnabled` fields define the payload shape. Inner classes appear only as nested list-element types (e.g. `List<OpenOpportunity>` on the outer class) and are referenced by their `List<...>` fields, not by a separate FQN. This file documents the derivation rule.

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
2. **Enumerate every `@AuraEnabled` field on the outer class AND every field on each inner class referenced by a `List<Inner>` field.** Default disposition is **include**. If you propose to drop any field, ASK the user first and record the rationale in the build plan's `Properties omitted:` section. Do not silently drop.
3. For each retained field, map the Apex type to the matching `lightning:type`:

   | Apex type | `lightning:type` (in widget schema) |
   |---|---|
   | `String`, `Id` | `lightning__textType` |
   | `Decimal`, `Double`, `Integer`, `Long` | `lightning__numberType` |
   | `Boolean` | `lightning__booleanType` |
   | `Date`, `Datetime` | `lightning__dateTimeType` |
   | `List<Primitive>` (e.g. `List<String>`) | `lightning__listType` |
   | `List<InnerClass>` | `lightning__listType` — and the widget body MUST iterate this list with `forEach`/`forItem` and bind every `@AuraEnabled` field on `InnerClass` via `{!$item.<innerField>}`. See `references/widget-meta-directives.md`. |

4. Build the widget `schema.json`. **Every `@AuraEnabled` field on the outer class** that survived step 2 MUST appear as an entry under `properties.attributes.properties`. Inner-class fields are NOT separate entries — they are accessed via the loop variable inside `forEach`, so they do not need their own entry in the widget schema.

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
           "<listFieldName>":     { "title": "<List Field Label>",      "lightning:type": "lightning__listType" }
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
