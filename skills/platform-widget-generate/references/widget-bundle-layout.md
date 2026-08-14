# WidgetBundle Layout

The widget skill writes three files into one directory under the project's package directory.

---

## Folder layout

```text
<pkgDir>/uiWidgets/<widgetName>/
  <widgetName>.json                     # widget envelope + UEM body
  schema.json                           # JSON Schema
  <widgetName>.uiwidget-meta.xml        # UiWidgetBundle registration
```

`<widgetName>` is `camelCase` and matches the directory name and both `<widgetName>.json` / `<widgetName>.uiwidget-meta.xml` filenames exactly.

---

## Resolving `<pkgDir>`

`<pkgDir>` resolves to `<packageDirectories[].path>/main/default` — the SFDX source-format default, where `<packageDirectories[].path>` is the `default: true` entry in `sfdx-project.json` (or the first entry if none is marked default).

---

## `<widgetName>.json` — Widget envelope + UEM body

The envelope has exactly two top-level keys — `type` and `contentBody`. The UEM tree lives at `contentBody.widgetBody`. Display metadata (label / description) lives in `<widgetName>.uiwidget-meta.xml`, not in the envelope.

```json
{
  "type": "lightning__agentforceWidget",
  "contentBody": {
    "widgetBody": {
      "definition": "tile/widget",
      "children": [
        /* every block — root and non-root — carries "definition", optional "attributes", optional "meta", optional "children". No "type" key on any node. */
      ]
    }
  }
}
```

Envelope keys:

- `type` — always `"lightning__agentforceWidget"`.
- `contentBody.widgetBody` — the root UEM node; this is `tile/widget`. It carries `definition` and `children` only — no `type` key on the root, no `type` key on any child.

Tree composition (everything inside `widgetBody.children`) is owned by `SKILL.md` *Composition*. No node — root or non-root — carries a `type` key.

---

## `schema.json` — Input contract

JSON Schema describing what data the widget accepts at runtime. Fields are wrapped one level deep under `properties.attributes`.

**Required root keys:**

- `title` (string) — display name
- `type` (string) — must equal `"object"`
- `properties.attributes` (object) — must carry `lightning:type: "lightning__objectType"` and a nested `properties` map whose leaves each carry `lightning:type`

**Optional root keys:**

- `description` (string)

**Each leaf under `properties.attributes.properties` MUST have `lightning:type`.** Optional per-leaf: `title`, `description`. **A `lightning__listType` leaf MUST also carry `items.lightning:type`** — set to the matching primitive `lightning:type` for a list of primitives, or to an `@apexClassType/...` reference for a list of Apex objects (see `references/schema-from-lightning-type.md`).

Example:

```json
{
  "title": "Order Summary Widget",
  "description": "Displays an order's id, customer, total, and tags.",
  "type": "object",
  "properties": {
    "attributes": {
      "lightning:type": "lightning__objectType",
      "properties": {
        "orderId":  { "title": "Order ID", "description": "Stable identifier shown in the header.",      "lightning:type": "lightning__textType" },
        "customer": { "title": "Customer", "description": "Display name of the customer on the order.", "lightning:type": "lightning__textType" },
        "total":    { "title": "Total",    "description": "Order total in the order's currency.",       "lightning:type": "lightning__numberType" },
        "tags":     { "title": "Tags",     "description": "Labels attached to the order.",               "lightning:type": "lightning__listType", "items": { "lightning:type": "lightning__textType" } }
      }
    }
  }
}
```

`{!$attrs.X}` in the body resolves to `properties.attributes.properties.X` in the schema.

---

## `<widgetName>.uiwidget-meta.xml` — Registration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<UiWidgetBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <masterLabel><Human display label></masterLabel>
    <description><One-line description of what the widget renders></description>
    <widgetType>JSON</widgetType>
</UiWidgetBundle>
```

Elements:

- `<masterLabel>` — required. Human-readable label shown in the runtime UI. Prefer title-case (e.g. `Account Summary Card`) — not the `camelCase` `<widgetName>`.
- `<description>` — required. One-line description of what the widget renders. Populates the display metadata previously carried in the envelope.
- `<widgetType>` — required. Only the `JSON` variant is supported. The `FUNCTION` variant is out of scope.

---

## Validation reminders

- Every `{!$attrs.X}` in `<widgetName>.json` MUST resolve to a property under `schema.json` `properties.attributes.properties` (or to a `forItem` loop variable defined upstream).
- `<widgetName>.uiwidget-meta.xml` MUST parse as well-formed XML, have root element `<UiWidgetBundle>`, and carry non-empty `<masterLabel>`, `<description>`, and `<widgetType>JSON</widgetType>` elements.
- The three files MUST be co-located in the same `<widgetName>/` directory under `uiWidgets/`.
