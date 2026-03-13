# Common FlexiPage Deployment Errors

## "Invalid field reference"
**Cause:** Used `ObjectName.Field` instead of `Record.Field`
**Fix:** Change to `Record.{FieldApiName}`

**Example:**
```xml
<!-- Wrong -->
<fieldItem>Account.Name</fieldItem>

<!-- Correct -->
<fieldItem>Record.Name</fieldItem>
```

## "Element fieldInstance is duplicated"
**Cause:** Multiple fieldInstances in one itemInstances wrapper
**Fix:** Each fieldInstance needs its own `<itemInstances>` wrapper

**Example:**
```xml
<!-- Wrong -->
<itemInstances>
    <fieldInstance>
        <fieldItem>Record.Name</fieldItem>
    </fieldInstance>
    <fieldInstance>
        <fieldItem>Record.Phone</fieldItem>
    </fieldInstance>
</itemInstances>

<!-- Correct -->
<itemInstances>
    <fieldInstance>
        <fieldItem>Record.Name</fieldItem>
    </fieldInstance>
</itemInstances>
<itemInstances>
    <fieldInstance>
        <fieldItem>Record.Phone</fieldItem>
    </fieldInstance>
</itemInstances>
```

## "Missing fieldInstanceProperties"
**Cause:** No uiBehavior specified
**Fix:** Add `fieldInstanceProperties` with `uiBehavior`

**Example:**
```xml
<!-- Wrong -->
<fieldInstance>
    <fieldItem>Record.Name</fieldItem>
    <identifier>RecordNameField</identifier>
</fieldInstance>

<!-- Correct -->
<fieldInstance>
    <fieldInstanceProperties>
        <name>uiBehavior</name>
        <value>none</value>
    </fieldInstanceProperties>
    <fieldItem>Record.Name</fieldItem>
    <identifier>RecordNameField</identifier>
</fieldInstance>
```

## "Unused Facet"
**Cause:** Facet defined but not referenced by any component
**Fix:** Remove Facet or reference it in a component property

**Example:**
```xml
<!-- Component must reference the facet -->
<componentInstanceProperties>
    <name>body</name>
    <value>detailTabContent</value>
</componentInstanceProperties>

<!-- And the facet must exist -->
<flexiPageRegions>
    <name>detailTabContent</name>
    <type>Facet</type>
</flexiPageRegions>
```

## "XML parsing error"
**Cause:** Unencoded HTML/XML in property values
**Fix:** Manually encode `<`, `>`, `&`, `"`, `'` in all `<value>` tags

**Encoding order (important!):**
1. `&` → `&amp;` (FIRST! Encode this before others)
2. `<` → `&lt;`
3. `>` → `&gt;`
4. `"` → `&quot;`
5. `'` → `&apos;`

**Example:**
```xml
<!-- Wrong -->
<value><b>Important</b> text & notes</value>

<!-- Correct -->
<value>&lt;b&gt;Important&lt;/b&gt; text &amp; notes</value>
```

## "Cannot create component with namespace"
**Cause:** Invalid page name (don't use `__c` suffix in page names)
**Fix:** Use "Volunteer_Record_Page" not "Volunteer__c_Record_Page"

**Example:**
```bash
# Wrong
sf template generate flexipage --name Volunteer__c_Record_Page

# Correct
sf template generate flexipage --name Volunteer_Record_Page
```

## "Region specifies mode that parent doesn't support"
**Cause:** Added `<mode>` tag to region
**Fix:** Remove `<mode>` tags - they're not needed for standard regions

**Example:**
```xml
<!-- Wrong -->
<flexiPageRegions>
    <name>header</name>
    <type>Region</type>
    <mode>Replace</mode>
</flexiPageRegions>

<!-- Correct -->
<flexiPageRegions>
    <name>header</name>
    <type>Region</type>
</flexiPageRegions>
```
