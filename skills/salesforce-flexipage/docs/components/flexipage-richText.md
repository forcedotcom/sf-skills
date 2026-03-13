# Rich Text Component

**Component name:** `flexipage:richText`

**Use for:** Displaying HTML-formatted rich text content with support for text formatting, headings, lists, tables, images, links, forms, and multimedia elements. Preserves styling and layout. Escape all special characters in the default text.

**Location:** Can be used in any region on any page type (Home, Record, App, Community pages).

**Structure:** Single-level component (no facets):
1. Component instance (flexipage:richText) with direct properties

**XML Structure Example:**
```xml
<itemInstances>
   <componentInstance>
      <componentInstanceProperties>
         <name>decorate</name>
         <value>true</value>
      </componentInstanceProperties>
      <componentName>flexipage:richText</componentName>
      <identifier>flexipage_richText</identifier>
   </componentInstance>
</itemInstances>
```

**Identifier Pattern:** `flexipage_richText` or `flexipage_richText_{sequence}`
