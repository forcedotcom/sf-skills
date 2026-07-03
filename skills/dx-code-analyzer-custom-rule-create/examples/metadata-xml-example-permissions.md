# Metadata XML Examples: Permissions

[← Back to Metadata XML Examples Index](metadata-xml-examples.md)

## Example 1: Flag ModifyAllData / ViewAllData Permissions

**Problem:** Permission sets granting ModifyAllData or ViewAllData are a security risk.

**Target file:** `*.permissionset-meta.xml`

**Sample violating metadata:**
```xml
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Power User</label>
    <userPermissions>
        <enabled>true</enabled>
        <name>ModifyAllData</name>
    </userPermissions>
</PermissionSet>
```

**XPath (PMD 7):**
```xpath
//*[@Text='ModifyAllData' or @Text='ViewAllData']/../..
  [local-name()='userPermissions']
  [.//*[@Text='true']]
```

**How it works:**
1. `//*[@Text='ModifyAllData' or @Text='ViewAllData']` — find text node with dangerous permission name
2. `/../..` — navigate up: text node → `<name>` element → `<userPermissions>` parent
3. `[local-name()='userPermissions']` — confirm we're at the right element
4. `[.//*[@Text='true']]` — check that a descendant text node contains "true" (the `<enabled>` value)

**PMD ruleset:**
```xml
<rule name="NoDangerousPermissions"
      language="xml"
      message="Permission set grants ModifyAllData or ViewAllData — use specific object permissions instead"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Flags permission sets that grant ModifyAllData or ViewAllData</description>
    <priority>1</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[@Text='ModifyAllData' or @Text='ViewAllData']/../..
  [local-name()='userPermissions']
  [.//*[@Text='true']]
]]></value>
        </property>
    </properties>
</rule>
```

---

## Example 4: No Field Permissions in Profiles

**Problem:** Field permissions should be managed via Permission Sets, not Profiles.

**Target file:** `*.profile-meta.xml`

**Sample violating metadata:**
```xml
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <fieldPermissions>
        <editable>true</editable>
        <field>Account.Revenue__c</field>
        <readable>true</readable>
    </fieldPermissions>
</Profile>
```

**XPath:**
```xpath
//*[local-name()='Profile']/*[local-name()='fieldPermissions']
```

**PMD ruleset:**
```xml
<rule name="NoFieldPermissionsInProfile"
      language="xml"
      message="Field permissions should be in Permission Sets, not Profiles"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <description>Profiles should not contain field-level security — use Permission Sets</description>
    <priority>2</priority>
    <properties>
        <property name="xpath">
            <value><![CDATA[
//*[local-name()='Profile']/*[local-name()='fieldPermissions']
]]></value>
        </property>
    </properties>
</rule>
```
