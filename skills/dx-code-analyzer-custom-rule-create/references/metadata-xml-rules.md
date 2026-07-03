# Metadata XML Rules (PMD with language="xml")

Write PMD XPath rules that target Salesforce metadata XML files (`.field-meta.xml`, `.permissionset-meta.xml`, `.profile-meta.xml`, `.flow-meta.xml`, etc.) to enforce org governance.

## How It Works

PMD's `language="xml"` mode parses any XML file into a DOM-like AST. You write XPath expressions against element/attribute names in the XML structure — same mechanism as Apex rules, but the AST is the XML DOM.

## Critical: PMD 7 XML XPath Rules

### Rule 1: Namespace — use `local-name()`

Salesforce metadata files declare a namespace:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>My_Field__c</fullName>
    ...
</CustomField>
```

This namespace **breaks standard XPath** because `//fullName` won't match — PMD sees it as `//metadata:fullName` internally.

**Solution:** Use `local-name()` to match element names regardless of namespace:

```xpath
//*[local-name()='CustomField']/*[local-name()='fullName']
```

**This applies to ALL Salesforce metadata XPath rules.** Never use bare element names without `local-name()`.

### Rule 2: Text content — use `@Text` (NOT `text()`)

⚠️ **PMD 7's XML language does NOT support `text()` for value comparison.** The `text()` function returns 0 matches regardless of content. This is a PMD 7 change from PMD 6.

**Use the `@Text` attribute instead:**

```xpath
// ❌ WRONG — does not work in PMD 7:
//*[local-name()='name'][text()='ModifyAllData']

// ✅ CORRECT — use @Text attribute:
//*[@Text='ModifyAllData']
```

### Rule 3: Navigation — text nodes require `../..`

In PMD 7 XML, `@Text` matches TEXT NODES (child nodes of elements), not the elements themselves. To navigate from a matched text node to its parent element hierarchy:

```xpath
// @Text='ModifyAllData' matches the TEXT NODE inside <name>ModifyAllData</name>
// To get the <name> element: go up one level
//*[@Text='ModifyAllData']/..

// To get the <userPermissions> parent: go up two levels
//*[@Text='ModifyAllData']/../..

// To check a sibling's text value from the parent:
//*[@Text='ModifyAllData']/../..[.//*[@Text='true']]
```

### Complete Pattern for Checking Parent + Sibling Text Values

The canonical PMD 7 pattern for "find element X that contains child with text A AND child with text B":

```xpath
//*[@Text='TargetValue']/../..
  [local-name()='ParentElement']
  [.//*[@Text='ConditionValue']]
```

Example — find `userPermissions` where name=ModifyAllData AND enabled=true:
```xpath
//*[@Text='ModifyAllData']/../..
  [local-name()='userPermissions']
  [.//*[@Text='true']]
```

## AST Dump for Metadata Files

Dump the AST to see the exact XML structure:
```bash
sf code-analyzer ast-dump --file force-app/main/default/objects/Account/fields/MyField__c.field-meta.xml --language xml
```

The output shows the DOM tree — element nodes, text nodes, and attributes. Use this to confirm element names before writing XPath.

## Ruleset XML Template for Metadata Rules

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ruleset name="MetadataGovernanceRules"
    xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">

    <description>Custom rules for Salesforce metadata governance</description>

    <rule name="MyMetadataRule"
          language="xml"
          message="Violation message here"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">

        <description>What this rule enforces</description>
        <priority>3</priority>

        <properties>
            <property name="xpath">
                <value><![CDATA[
//*[local-name()='YourElement'][your-condition]
]]></value>
            </property>
        </properties>
    </rule>
</ruleset>
```

## Configuration

```yaml
# code-analyzer.yml
engines:
  pmd:
    custom_rulesets:
      - "custom-rules/metadata-governance.xml"
    file_extensions:
      xml: [".xml"]
```

⚠️ **IMPORTANT:** PMD's XML language only scans `.xml` files by default. You MUST add `file_extensions: { xml: [".xml"] }` under `engines.pmd` in your config. This single entry covers ALL Salesforce metadata compound extensions (`.permissionset-meta.xml`, `.field-meta.xml`, `.flow-meta.xml`, etc.) because the system reads the final `.xml` portion of the filename.

⚠️ **Do NOT add compound extensions** like `.permissionset-meta.xml` to the list — Code Analyzer's validator only accepts single-segment extensions matching `/^[.][a-zA-Z0-9]+$/` and will reject them with a config error.

## Common Metadata File Structures

### Custom Field (`.field-meta.xml`)
```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Revenue__c</fullName>
    <label>Revenue</label>
    <type>Currency</type>
    <required>false</required>
    <description>Annual revenue</description>
</CustomField>
```

### Permission Set (`.permissionset-meta.xml`)
```xml
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Admin Access</label>
    <userPermissions>
        <enabled>true</enabled>
        <name>ModifyAllData</name>
    </userPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Account.Revenue__c</field>
        <readable>true</readable>
    </fieldPermissions>
</PermissionSet>
```

### Profile (`.profile-meta.xml`)
```xml
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <userPermissions>
        <enabled>true</enabled>
        <name>ViewSetup</name>
    </userPermissions>
    <fieldPermissions>
        <editable>true</editable>
        <field>Account.SSN__c</field>
    </fieldPermissions>
</Profile>
```

### Flow (`.flow-meta.xml`)
```xml
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>58.0</apiVersion>
    <label>My Flow</label>
    <processType>AutoLaunchedFlow</processType>
    <status>Active</status>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value>
    </processMetadataValues>
    <recordCreates>
        <name>Create_Account</name>
        <object>Account</object>
    </recordCreates>
    <loops>
        <name>Loop_Records</name>
        <collectionReference>Get_Records</collectionReference>
    </loops>
</Flow>
```

## XPath Patterns for Metadata (PMD 7)

All patterns below use `@Text` for text content matching (NOT `text()` which is broken in PMD 7).

### Require description on Custom Fields

**Missing description entirely:**
```xpath
//*[local-name()='CustomField'][not(*[local-name()='description'])]
```

**Missing OR empty description (catches `<description></description>` too):**
```xpath
//*[local-name()='CustomField'][not(*[local-name()='description']) or *[local-name()='description'][not(.//*[@Text])]]
```
Note: `.//*[@Text]` checks for any descendant text node with content. Do NOT put `[not(@Text)]` directly on the `<description>` element — `@Text` only exists on child text nodes, not on elements themselves. Putting it on the element always evaluates to true (false positive).

### Flag ModifyAllData / ViewAllData in Permission Sets
```xpath
//*[@Text='ModifyAllData' or @Text='ViewAllData']/../..
  [local-name()='userPermissions']
  [.//*[@Text='true']]
```

### Enforce minimum API version (60.0+)
```xpath
//*[local-name()='apiVersion']/*[number(@Text) < 60]
```
Note: `/*` navigates to the **child text node** where `@Text` lives. Do NOT put `@Text` directly on the element — it won't match because `@Text` only exists on text nodes (children), not on elements themselves.

### Flag field permissions in Profiles (should be in Perm Sets)
```xpath
//*[local-name()='Profile']/*[local-name()='fieldPermissions']
```
(No text matching needed — structural only.)

### Flag dangerous permissions (ModifyAllData only, enabled)
```xpath
//*[@Text='ModifyAllData']/../..
  [local-name()='userPermissions']
  [.//*[@Text='true']]
```

### Flag DML (recordCreates/recordUpdates/recordDeletes) inside Flow loops
```xpath
//*[local-name()='loops'][
  following-sibling::*[local-name()='recordCreates' or local-name()='recordUpdates' or local-name()='recordDeletes']
]
```
(No text matching needed — structural only.)

## Targeting Specific File Types

PMD only scans `.xml` files by default. You must add `.xml` to the config. This single extension covers ALL Salesforce compound metadata extensions (`.permissionset-meta.xml`, `.field-meta.xml`, etc.) because `path.extname()` returns `.xml` from these filenames.

```yaml
# code-analyzer.yml
engines:
  pmd:
    file_extensions:
      xml: [".xml"]
```

⚠️ Do NOT add compound extensions — the validator rejects anything that doesn't match `/^[.][a-zA-Z0-9]+$/`.

Additionally, scope your XPath to the correct root element to avoid false positives across file types:

```xpath
//*[@Text='ModifyAllData']/../..[local-name()='userPermissions']
  [ancestor::*[local-name()='PermissionSet']]
```

This ensures the rule only fires on permission set files, not on profile or other metadata files.

## Gotchas

| Issue | Resolution |
|-------|------------|
| XPath matches nothing | Three causes: (1) Forgot `local-name()`. (2) Used `text()` — broken in PMD 7, use `@Text`. (3) File extension not in `file_extensions.xml` config. |
| Rule fires on wrong metadata type | Add root element scope: `[ancestor::*[local-name()='PermissionSet']]` |
| Can't match text content | **Use `@Text` attribute** (NOT `text()`). Example: `//*[@Text='ModifyAllData']` |
| `@Text` matches but parent navigation fails | `@Text` matches TEXT NODES. Go up with `../..`: text→element→parent. |
| Number comparison fails | `@Text` lives on the **child text node**, NOT on the element. Use: `//*[local-name()='element']/*[number(@Text) < N]` — the `/*` navigates to the text node. Do NOT put `[@Text]` predicate directly on the element (returns 0 matches). |
| Too many violations on large orgs | Scope with `file_extensions` in PMD config or add `ignores.files` patterns |
| Rule doesn't fire on metadata files | Add `file_extensions: { xml: [".xml"] }` under `engines.pmd` — this covers all compound extensions. Do NOT add `.permissionset-meta.xml` etc. (validator rejects them). |
| ast-dump fails with "XmlEncoding" error | Known issue. Read the raw XML file — the file content IS the DOM structure |
| ast-dump shows different structure | XML AST is the literal DOM — what you see in the file is what you get |
