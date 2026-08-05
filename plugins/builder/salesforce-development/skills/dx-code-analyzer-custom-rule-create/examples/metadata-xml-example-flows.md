# Metadata XML Examples: Flows

[← Back to Metadata XML Examples Index](metadata-xml-examples.md)

## Example 5: Require Flow Auto-Layout

**Problem:** Flows should use Auto-Layout canvas for consistency and maintainability.

**Target file:** `*.flow-meta.xml`

**Sample violating metadata:**
```xml
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>58.0</apiVersion>
    <label>My Flow</label>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>FREE_FORM_CANVAS</stringValue></value>
    </processMetadataValues>
</Flow>
```

**XPath (PMD 7 — flags FREE_FORM_CANVAS):**
```xpath
//*[@Text='FREE_FORM_CANVAS']/../..
  [local-name()='value']
  [ancestor::*[local-name()='processMetadataValues'][.//*[@Text='CanvasMode']]]
```

**How it works:** Finds text nodes with "FREE_FORM_CANVAS", navigates up to the `<value>` element, then confirms it's inside a `processMetadataValues` block that also contains "CanvasMode".

**PMD ruleset:**
```xml
<rule name="FlowMustUseAutoLayout"
      language="xml"
      message="Flows must use AUTO_LAYOUT_CANVAS mode"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Enforces auto-layout canvas mode on all flows for consistency</description>
    <priority>3</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[@Text='FREE_FORM_CANVAS']/../..
  [local-name()='value']
  [ancestor::*[local-name()='processMetadataValues'][.//*[@Text='CanvasMode']]]
]]></value>
        </property>
    </properties>
</rule>
```

---

## Example 6: Flow Missing Fault Handler

**Problem:** Flow actions without fault connectors can fail silently.

**Target file:** `*.flow-meta.xml`

**Sample violating metadata:**
```xml
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <recordCreates>
        <name>Create_Account</name>
        <object>Account</object>
        <connector>
            <targetReference>Next_Step</targetReference>
        </connector>
        <!-- No <faultConnector> element! -->
    </recordCreates>
</Flow>
```

**XPath:**
```xpath
//*[local-name()='Flow']/*[
  local-name()='recordCreates' or local-name()='recordUpdates'
  or local-name()='recordDeletes' or local-name()='recordLookups'
][
  not(*[local-name()='faultConnector'])
]
```

**PMD ruleset:**
```xml
<rule name="FlowActionRequiresFaultHandler"
      language="xml"
      message="Flow DML/query actions must have a fault connector for error handling"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Ensures all data operations in flows have fault paths</description>
    <priority>2</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[local-name()='Flow']/*[
  local-name()='recordCreates' or local-name()='recordUpdates'
  or local-name()='recordDeletes' or local-name()='recordLookups'
][
  not(*[local-name()='faultConnector'])
]
]]></value>
        </property>
    </properties>
</rule>
```
