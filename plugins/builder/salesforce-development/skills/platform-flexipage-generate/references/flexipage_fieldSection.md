# flexipage:fieldSection — Field Section

## Purpose

Displays fields in a column layout under a labeled section heading.

## Supported Page Types

- RecordPage (`main` region or detail tab facets)

## Structure

Three-level nesting:
1. Template Region (Region type) — contains the fieldSection component
2. Column Facets (Facet type) — contains `flexipage:column` components pointing to field facets
3. Field Facets (Facet type) — contains `fieldInstance` elements for each column

**Critical:** The `columns` property value must match the `<name>` of the facet where the `flexipage:column` components are defined. It is *not* a number.

## Property Table

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| columns | String (Facet ref) | Yes | — | Reference to the Facet containing `flexipage:column` components |
| label | String | Yes | — | Section heading displayed to users |
| horizontalAlignment | Boolean | No | false | Align fields horizontally within columns |

## Property Inference Rules

| User Intent | Inferred Properties |
|-------------|-------------------|
| "add a field section with {fields}" | Split fields evenly across 2 columns |
| "section labeled {name}" | `label` = `{name}` |

## XML Example

```xml
<!-- Field facet for first column -->
<flexiPageRegions>
   <itemInstances>
      <fieldInstance>
            <fieldInstanceProperties>
               <name>uiBehavior</name>
               <value>required</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Field0</fieldItem>
            <identifier>RecordColumn1Field0</identifier>
      </fieldInstance>
   </itemInstances>
   <itemInstances>
      <fieldInstance>
            <fieldInstanceProperties>
               <name>uiBehavior</name>
               <value>none</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Field1</fieldItem>
            <identifier>RecordColumn1Field1</identifier>
      </fieldInstance>
   </itemInstances>
   <name>Facet-FieldSection-Column1</name>
   <type>Facet</type>
</flexiPageRegions>

<!-- Field facet for second column -->
<flexiPageRegions>
   <itemInstances>
      <fieldInstance>
            <fieldInstanceProperties>
               <name>uiBehavior</name>
               <value>none</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Field2</fieldItem>
            <identifier>RecordColumn2Field0</identifier>
      </fieldInstance>
   </itemInstances>
   <itemInstances>
      <fieldInstance>
            <fieldInstanceProperties>
               <name>uiBehavior</name>
               <value>none</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Type</fieldItem>
            <identifier>RecordColumn2Field1</identifier>
      </fieldInstance>
   </itemInstances>
   <name>Facet-FieldSection-Column2</name>
   <type>Facet</type>
</flexiPageRegions>

<!-- Columns facet -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
            <componentInstanceProperties>
               <name>body</name>
               <value>Facet-FieldSection-Column1</value>
            </componentInstanceProperties>
            <componentName>flexipage:column</componentName>
            <identifier>flexipage_column1</identifier>
      </componentInstance>
   </itemInstances>
   <itemInstances>
      <componentInstance>
            <componentInstanceProperties>
               <name>body</name>
               <value>Facet-FieldSection-Column2</value>
            </componentInstanceProperties>
            <componentName>flexipage:column</componentName>
            <identifier>flexipage_column2</identifier>
      </componentInstance>
   </itemInstances>
   <name>Facet-FieldSection-Columns</name>
   <type>Facet</type>
</flexiPageRegions>

<!-- Template region with fieldSection component -->
<flexiPageRegions>
   <itemInstances>
      <componentInstance>
            <componentInstanceProperties>
               <name>columns</name>
               <value>Facet-FieldSection-Columns</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
               <name>horizontalAlignment</name>
               <value>false</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
               <name>label</name>
               <value>Information</value>
            </componentInstanceProperties>
            <componentName>flexipage:fieldSection</componentName>
            <identifier>flexipage_fieldSection</identifier>
      </componentInstance>
   </itemInstances>
   <name>main</name>
   <type>Region</type>
</flexiPageRegions>
```

## uiBehavior Attribute

Every `fieldInstance` requires a `uiBehavior` property that controls field editability on the page.

| Value | Meaning | When to use |
|-------|---------|-------------|
| `none` | Field respects standard editability settings (default) | Standard fields — uses object/layout-level permissions |
| `required` | Field is required — must be filled before save | Fields that must have a value for the record to be valid |
| `readonly` | Field is read-only — displayed but not editable | Formula fields, system fields, or fields locked by business rules |

**Inference rules:**
- Default to `none` unless the user specifies otherwise
- If user says "required" or "mandatory" → use `required`
- If user says "read-only", "display only", or "locked" → use `readonly`
- Formula fields and auto-number fields should always be `readonly`

## Edge Cases

- `columns` property is a Facet name, not a count — common mistake
- Split fields roughly evenly across columns
- Identifiers: `flexipage_fieldSection`, `flexipage_fieldSection2`; columns: `flexipage_column1`, `flexipage_column2`
- Second fieldSection on same page: all facet names and identifiers must be unique
