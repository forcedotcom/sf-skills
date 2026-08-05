# Identifiers, Regions, and Container Facets

## Generating Unique Identifiers

**Before generating ANY new identifier or facet name, read the existing XML and extract all `<identifier>` and `<name>` values first.**

**Identifier Generation Algorithm**:
```text
1. Extract ALL existing <identifier> AND <name> values from XML
2. Generate base name: {namespace}_{componentType}_{context}
   Examples: "lst_relatedList_contacts", "flexipage_richText_header"
3. Find first available number:
   - Try "{base}_1"
   - If exists, try "{base}_2", "{base}_3", etc.
   - Use first available
```

**Examples**:
- First related list: `lst_relatedList_contacts`
- Second related list: `lst_relatedList_contacts_2`
- First rich text: `flexipage_richText_header`
- Second rich text: `flexipage_richText_header_2`
- Field section: `flexipage_fieldSection`

**Facet Naming - Two Patterns**:

1. **Named facets** (for major content areas):
   - `detailTabContent` (detail tab content)
   - `maintabs` (main tab container)
   - `sidebartabs` (sidebar tab container)
   - Use when facet represents meaningful content area

2. **UUID facets** (for internal structure):
   - Format: `Facet-{8hex}-{4hex}-{4hex}-{4hex}-{12hex}`
   - Example: `Facet-66d5a4b3-bf14-4665-ba75-1ceaa71b2cde`
   - Use for field section columns, nested containers, anonymous slots

**When adding components to existing files:**
- Check if target facet name already exists
- If exists: Add new `<itemInstances>` to that existing region (see xml_rules.md section 5 for details)
- If doesn't exist: Create new region with unique name

---

## Region Selection

**Parse regions from file** - don't hardcode names. Templates vary:
- `flexipage:recordHomeTemplateDesktop` → `header`, `main`, `sidebar`
- `runtime_service_fieldservice:...` → `header`, `main`, `footer`
- Others may have different region names

**Default placement**: End of target region (after last `<itemInstances>`)

**Insertion pattern**:
```xml
<flexiPageRegions>
   <name>main</name>  <!-- or whatever region name exists -->
   <type>Region</type>
   <itemInstances><!-- Existing component 1 --></itemInstances>
   <itemInstances><!-- Existing component 2 --></itemInstances>
   <itemInstances>
      <!-- INSERT NEW COMPONENT HERE -->
   </itemInstances>
</flexiPageRegions>
```

---

## Container Components with Facets

Components like tabs, accordions, and field sections require a **3-layer facet pattern**. There is NO single "tabs" component — you must use `flexipage:tabset` + `flexipage:tab` + content facets.

**The 3-layer tab pattern:**

```xml
<!-- LAYER 1: Content facets — one per tab's body -->
<flexiPageRegions>
    <itemInstances>
        <componentInstance>
            <componentName>force:detailPanel</componentName>
            <identifier>force_detailPanel1</identifier>
        </componentInstance>
    </itemInstances>
    <name>detailTabContent</name>
    <type>Facet</type>
</flexiPageRegions>

<flexiPageRegions>
    <itemInstances>
        <componentInstance>
            <componentInstanceProperties>
                <name>relatedListComponentOverride</name>
                <value>NONE</value>
            </componentInstanceProperties>
            <componentName>force:relatedListContainer</componentName>
            <identifier>force_relatedListContainer1</identifier>
        </componentInstance>
    </itemInstances>
    <name>relatedTabContent</name>
    <type>Facet</type>
</flexiPageRegions>

<!-- LAYER 2: Tab definitions facet — each flexipage:tab points to a content facet via "body" -->
<flexiPageRegions>
    <itemInstances>
        <componentInstance>
            <componentInstanceProperties>
                <name>active</name>
                <value>true</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>body</name>
                <value>detailTabContent</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>title</name>
                <value>Standard.Tab.detail</value>
            </componentInstanceProperties>
            <componentName>flexipage:tab</componentName>
            <identifier>flexipage_tab1</identifier>
        </componentInstance>
    </itemInstances>
    <itemInstances>
        <componentInstance>
            <componentInstanceProperties>
                <name>active</name>
                <value>false</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>body</name>
                <value>relatedTabContent</value>
            </componentInstanceProperties>
            <componentInstanceProperties>
                <name>title</name>
                <value>Standard.Tab.relatedLists</value>
            </componentInstanceProperties>
            <componentName>flexipage:tab</componentName>
            <identifier>flexipage_tab2</identifier>
        </componentInstance>
    </itemInstances>
    <name>maintabs</name>
    <type>Facet</type>
</flexiPageRegions>

<!-- LAYER 3: Tabset in the template region — references the tabs facet -->
<flexiPageRegions>
    <itemInstances>
        <componentInstance>
            <componentInstanceProperties>
                <name>tabs</name>
                <value>maintabs</value>
            </componentInstanceProperties>
            <componentName>flexipage:tabset</componentName>
            <identifier>flexipage_tabset1</identifier>
        </componentInstance>
    </itemInstances>
    <name>main</name>
    <type>Region</type>
</flexiPageRegions>
```

**Critical rules:**
- Facet regions are **siblings** of template regions (same level), NEVER nested inside them
- Each `flexipage:tab` has `body` pointing to a content facet name, `title` for the label, and `active` (true/false)
- The `flexipage:tabset` has a single `tabs` property pointing to the tabs facet name
- Standard tab titles: `Standard.Tab.detail`, `Standard.Tab.relatedLists`, `Standard.Tab.activity`, `Standard.Tab.news`
- The component is `flexipage:tabset` — NOT `flexipage:tabs`, `flexipage:tabset2`, or `lightning:tabset`
