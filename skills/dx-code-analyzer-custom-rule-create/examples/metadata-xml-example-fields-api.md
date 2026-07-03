# Metadata XML Examples: Fields and API Version

[← Back to Metadata XML Examples Index](metadata-xml-examples.md)

## Example 2: Require Description on Custom Fields

**Problem:** Custom fields without descriptions make orgs hard to maintain.

**Target file:** `*.field-meta.xml`

**Sample violating metadata:**
```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Revenue__c</fullName>
    <label>Revenue</label>
    <type>Currency</type>
    <!-- No <description> element! -->
</CustomField>
```

**XPath (PMD 7):**
```xpath
//*[local-name()='CustomField'][not(*[local-name()='description']) or *[local-name()='description'][not(@Text)]]
```

**How it works:** Matches `CustomField` elements that either lack a `<description>` child entirely, or have one with no text content (`@Text` absent means empty).

**PMD ruleset:**
```xml
<rule name="FieldRequiresDescription"
      language="xml"
      message="Custom field must have a non-empty description"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Enforces that all custom fields have a description for documentation</description>
    <priority>3</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[local-name()='CustomField'][not(*[local-name()='description']) or *[local-name()='description'][not(@Text)]]
]]></value>
        </property>
    </properties>
</rule>
```

---

## Example 3: Enforce Minimum API Version

**Problem:** Metadata using API versions older than 60.0 should be updated.

**Target file:** Any `*-meta.xml` with `<apiVersion>`

**Sample violating metadata:**
```xml
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>52.0</apiVersion>
    <status>Active</status>
</ApexClass>
```

**XPath (PMD 7):**
```xpath
//*[local-name()='apiVersion']/*[number(@Text) < 60]
```

**How it works:** Finds `<apiVersion>` elements, then navigates to their child text node with `/*`. The `@Text` attribute on the text node holds the value (e.g., "52.0"). `number(@Text)` converts it to a float, and flags if < 60.

⚠️ **Key insight:** `@Text` lives on CHILD text nodes, not on elements. You must use `/*` to reach the text node — putting `[@Text]` directly on the element (after `local-name()='apiVersion'`) returns 0 matches.

**PMD ruleset:**
```xml
<rule name="MinimumApiVersion"
      language="xml"
      message="API version must be 60.0 or higher — update this metadata"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Enforces minimum API version of 60.0 across all metadata</description>
    <priority>3</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[local-name()='apiVersion']/*[number(@Text) < 60]
]]></value>
        </property>
    </properties>
</rule>
```
