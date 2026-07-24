# Widget Rendition Pattern for CLT renderer.json

## Overview

When a Custom Lightning Type needs to render through a Widget bundle (authored by `platform-widget-generate`), the `renderer.json` uses a flat widget-reference pattern. The renderer points at the widget by developer name and maps each CLT schema property to the widget's attribute contract.

> **For full widget generation** (Apex → Lightning Type → Widget pipeline), use the `platform-lightning-type-widget-coordinate` orchestrator. This file documents only the renderer.json wiring pattern for CLTs that reference an existing widget.

## renderer.json Shape

```json
{
  "renderer": {
    "componentOverrides": {
      "$": {
        "definition": "@widget/c/<widgetDeveloperName>",
        "attributes": {
          "<widgetAttrKey>": "{!$attrs.<schemaPropertyName>}"
        }
      }
    }
  }
}
```

- `<widgetDeveloperName>` matches the widget bundle directory name under `uiWidgets/`.
- `<widgetAttrKey>` is a property under the widget's `schema.json` `properties.attributes.properties`.
- `<schemaPropertyName>` is a property on the Custom Lightning Type's schema.
- One attribute mapping per widget property — the set of attributes must match the widget's schema contract.

## Attribute Binding

Use `{!$attrs.<name>}` syntax in attribute values. `<name>` must match a property defined in the CLT's own `schema.json`. At runtime the renderer resolves these bindings and passes the live data to the widget.

## Constraints

- Do NOT duplicate the widget UEM body inside `renderer.json` — the widget bundle owns its own UEM tree.
- The widget bundle (`<pkgDir>/uiWidgets/<widgetDeveloperName>/`) must exist and be deployed before the Lightning Type that references it.
- Every attribute key in the renderer must resolve to a property in the widget's `schema.json` `properties.attributes.properties`.
- Write the renderer to `lightningTypes/<TypeName>/lightningDesktopGenAi/renderer.json` (or the correct target subfolder for the product surface).
