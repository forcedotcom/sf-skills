# UI Component Handling

**Use when** adding/configuring components to be used in Experience site.

## Component Insertion

Insert custom Lightning Web Components (LWC) into views.

### What is a Custom Component?

Any LWC in `c` namespace (e.g., `c:heroBanner`). Distinct from OOTB components (e.g., `community_builder:htmlEditor`).

### Prerequisites for Custom LWC

**js-meta.xml Requirements**:

- `<isExposed>true</isExposed>`
- Targets: `lightningCommunity__Page`, `lightningCommunity__Default`

**Property Type Constraints (MANDATORY GATE)**:

1. **Supported**: String, Integer, Boolean, Color, Picklist
2. **Unsupported**: Any other type → **STOP immediately**
   - Do NOT delete, comment, or auto-correct
   - Advise user to set up Custom Property Editor (CPE) or Custom Property Type
3. **Type Mismatch**: `type="Number"` → change to `type="Integer"` in js-meta.xml

**Do not proceed** until LWC files are compliant or user advised on CPE/CPT.

### Placement Hierarchy

**NEVER** place components directly in top-level regions. Must nest inside `community_layout:section` → column region.

```
community_layout:sldsFlexibleLayout (root)
└── region (content/header/footer)
    └── community_layout:section
        └── region (column: col1/col2)
            └── component(s)
```

### Column Width & Layout

**12-unit grid**: Column widths sum to 12 per section.

**Width Formats**:

- Grid units: 8 + 4
- Percentages: 66% + 33% → 8 + 4; 50% + 50% → 6 + 6
- Ratios: 2:1 → 8 + 4; 1:1 → 6 + 6; equal thirds → 4 + 4 + 4

**Layout Rules**:

- One section = one horizontal row
- Multiple rows = multiple sections (siblings)
- Multiple components in column = vertical stack

**Set width in** `sectionConfig` (JSON string attribute on section component).

### sectionConfig Structure

**Top-level** (when parsed):

- `UUID`: Section ID (matches section component's `id`)
- `columns`: Array of column definitions

**Each column**:

- `UUID`: Column ID (matches column region's `id`)
- `columnKey`: Column identifier (e.g., `col1`, `col2`) - matches column region's `name`
- `columnName`: Display name (e.g., "Column 1")
- `columnWidth`: String from `"1"` to `"12"` (must sum to 12)
- `seedComponents`: Array or `null` (typically `[]` or `null`)

**Example** (serialized as JSON string in `sectionConfig` attribute):

```json
{
  "UUID": "295e6a8b-fd94-485b-af9d-7ccf5b3048ee",
  "columns": [
    {
      "UUID": "7e1f7e33-5ba8-4fef-8494-6ea3e90b22a0",
      "columnKey": "col1",
      "columnName": "Column 1",
      "columnWidth": "12",
      "seedComponents": null
    }
  ]
}
```

### Named Region Creation
In order to create a component with drag-n-droppable region/slot that can be used in Experience Builder sites and persist across views, there are multiple steps needed.

Page layout components should add the lightningCommunity__Page_Layout target in js-meta.xml.
Theme layout components should add the lightningCommunity__Theme_Layout target in js-meta.xml.
Add lightningCommunity__Page as a target for page layouts and any component with slots that is not explicitly defined as a theme layout.

The js file in LWC need to declare named slots:
```js
/**
 * @slot header
 * @slot footer
 */
export default class YourComponentName extends LightningElement {}
```

Do not add any other comments in the declaration comment block. The named @slot annotations must be the last comments
in the block before the class declaration.

In html, named slots are needed. <slot name="header"> and <slot name="footer"> in the above example.

For theme layout component, a <slot> with no name is the main content region, a slot with name is a sticky region that doesn't change from page to page that uses the same theme layout component.

No need to declare target config properties for the slots/regions.
See the example below for adding a component with named slots into a view.

### Component Structure

```json
{
  "id": "[UNIQUE_UUID]",
  "type": "component",
  "definition": "[NAMESPACE]:[COMPONENT_NAME]",
  "attributes": {
    "[ATTRIBUTE_NAME]": "[ATTRIBUTE_VALUE]"
  }
}
```

**Field Definitions**:

- `id`: Unique UUID (see `handle-component-and-region-ids.md`)
- `type`: Always `"component"`
- `definition`:
  - Custom LWC: `c:[componentName]` (e.g., `c:heroBanner`)
  - OOTB: `[namespace]:[componentName]` (e.g., `community_builder:richTextEditor`)
- `attributes`: Component properties
  - **Omit if no attributes** (don't include empty object)
  - Custom LWC: Only `@api` properties in `targetConfigs` (with `lightningCommunity__Default` target)
  - OOTB: Only exposed schema properties

### Complete Examples

**Example 1: Overall structure**
Correct nesting: `content` region → section → column region → components

```json
{
  "type": "region",
  "name": "content",
  "children": [
    {
      "attributes": {
        "sectionConfig": "{\"UUID\":\"295e6a8b-fd94-485b-af9d-7ccf5b3048ee\",\"columns\":[{\"UUID\":\"7e1f7e33-5ba8-4fef-8494-6ea3e90b22a0\",\"columnName\":\"Column 1\",\"columnKey\":\"col1\",\"columnWidth\":\"12\",\"seedComponents\":null}]}"
      },
      "children": [
        {
          "children": [
            {
              "definition": "c:testComponent",
              "id": "2ae498bd-2871-487d-8fb1-b186376cee3b",
              "type": "component"
            },
            {
              "id": "7c7d3b6a-1e2f-4a33-9c1e-8b2a6d5f4e3b",
              "type": "component",
              "definition": "c:helloWorld",
              "attributes": {
                "title": "Hello"
              }
            }
          ],
          "id": "7e1f7e33-5ba8-4fef-8494-6ea3e90b22a0",
          "name": "col1",
          "title": "Column 1",
          "type": "region"
        }
      ],
      "definition": "community_layout:section",
      "id": "295e6a8b-fd94-485b-af9d-7ccf5b3048ee",
      "type": "component"
    }
  ]
}
```

**CRITICAL**: Follow UUID generation process (`handle-component-and-region-ids.md`) when inserting components.

**Example 2: Representing slots**
If a component with slots (i.e. @slot annotation) is inserted, slots must appear as named regions.
In this example the component threeColumn has 3 slots, named left, center, and right.
```json
{
    "attributes" : { },
    "children" : [ {
    "id" : "4c6148c7-c07e-4245-ae50-ac07891046f2",
    "name" : "left",
    "title" : "left",
    "type" : "region"
    }, {
    "id" : "f362e789-7f09-40b4-a59f-03f76ea73401",
    "name" : "center",
    "title" : "center",
    "type" : "region"
    }, {
    "id" : "2678ddd4-a1a4-41c4-bf5a-1a3e55891eb2",
    "name" : "right",
    "title" : "right",
    "type" : "region"
    } ],
    "definition" : "c:threeColumn",
    "id" : "b9e517c5-90ac-49e9-91b7-3730512c95a3",
    "type" : "component"
}
