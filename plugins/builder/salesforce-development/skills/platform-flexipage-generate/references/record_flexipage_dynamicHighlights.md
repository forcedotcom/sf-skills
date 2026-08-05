# record_flexipage:dynamicHighlights — Dynamic Highlights Panel

## Purpose

Displays the record highlights panel at the top of a record page with a primary identifying field, secondary summary fields, and configurable actions. Replaces the older static `force:highlightsPanel`.

## Supported Page Types

- RecordPage only (always in `header` region)

## Property Table

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| primaryField | String (Facet ref) | Yes | — | Reference to a Facet containing the primary field (typically Record.Name) |
| secondaryFields | String (Facet ref) | No | — | Reference to a Facet containing secondary highlight fields |
| actionNames | valueList | No | — | Actions in the highlights panel: `Edit`, `Delete`, `ChangeOwnerOne`, `Share`, `RecordShareHierarchy` |
| numVisibleActions | Integer | No | 3 | Number of actions shown before overflow menu |

## Structural Pattern

This component uses an **indirect Facet reference** pattern. The `primaryField` and `secondaryFields` properties point to Facet regions that contain `fieldInstance` elements — they are NOT direct field API names.

**Required supporting structure:**
1. A Facet region for `primaryField` containing one `fieldInstance` (the identifying field)
2. A Facet region for `secondaryFields` containing multiple `fieldInstance` elements (summary fields)

## Property Inference Rules

| User Intent | Inferred Properties |
|-------------|-------------------|
| "highlights with {fields}" | Create secondaryFields facet with those fields as fieldInstances |
| "show actions: Edit, Delete" | `actionNames` = valueList with `Edit`, `Delete` |
| "show {N} actions" | `numVisibleActions` = `{N}` |

**Field selection:** Primary = `Record.Name` (or object's identifying field). Secondary = 4-6 useful fields (max 12). Prefer CLI `--secondary-fields` values if available.

## XML Example

```xml
<!-- Component in header region -->
<flexiPageRegions>
    <itemInstances>
        <componentInstance>
            <componentInstanceProperties>
                <name>actionNames</name>
                <valueList>
                    <valueListItems>
                        <value>Edit</value>
                    </valueListItems>
                    <valueListItems>
                        <value>Delete</value>
                    </valueListItems>
                    <valueListItems>
                        <value>ChangeOwnerOne</value>
                    </valueListItems>
                </valueList>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>numVisibleActions</name>
                <value>3</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>primaryField</name>
                <value>Facet-primary-field-001</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>secondaryFields</name>
                <value>Facet-secondary-fields-001</value>
            </componentInstanceProperties>
            <componentName>record_flexipage:dynamicHighlights</componentName>
            <identifier>record_flexipage_dynamicHighlights</identifier>
        </componentInstance>
    </itemInstances>
    <name>header</name>
    <type>Region</type>
</flexiPageRegions>

<!-- Primary field Facet -->
<flexiPageRegions>
    <itemInstances>
        <fieldInstance>
            <fieldInstanceProperties>
                <name>uiBehavior</name>
                <value>none</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Name</fieldItem>
            <identifier>RecordNameField</identifier>
        </fieldInstance>
    </itemInstances>
    <name>Facet-primary-field-001</name>
    <type>Facet</type>
</flexiPageRegions>

<!-- Secondary fields Facet (same structure as primary, multiple fieldInstances) -->
<flexiPageRegions>
    <itemInstances>
        <fieldInstance>
            <fieldInstanceProperties>
                <name>uiBehavior</name>
                <value>none</value>
            </fieldInstanceProperties>
            <fieldItem>Record.Phone</fieldItem>
            <identifier>RecordPhoneField</identifier>
        </fieldInstance>
    </itemInstances>
    <name>Facet-secondary-fields-001</name>
    <type>Facet</type>
</flexiPageRegions>
```

## Edge Cases

- Only ONE per page — never multiple instances
- Always in `header` region — never in `main` or sidebar
- Facet names must be unique UUIDs or descriptive names
- Primary field `uiBehavior` is `none`; secondary fields also use `none`
- If CLI already generated highlights, modify existing — do not add a duplicate
- Identifier is always `record_flexipage_dynamicHighlights` (singular, never numbered)
