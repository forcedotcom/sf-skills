# Metadata XML Rule Examples

Real-world custom PMD rules targeting Salesforce metadata XML files for org governance.

⚠️ **PMD 7 Note:** All examples use `@Text` for text content matching. The `text()` function does NOT work in PMD 7's XML language. See `references/metadata-xml-rules.md` for full details.

## Example Index

| # | Example | File |
|---|---------|------|
| 1 | Flag ModifyAllData / ViewAllData Permissions | [metadata-xml-example-permissions.md](metadata-xml-example-permissions.md) |
| 2 | Require Description on Custom Fields | [metadata-xml-example-fields-api.md](metadata-xml-example-fields-api.md) |
| 3 | Enforce Minimum API Version | [metadata-xml-example-fields-api.md](metadata-xml-example-fields-api.md) |
| 4 | No Field Permissions in Profiles | [metadata-xml-example-permissions.md](metadata-xml-example-permissions.md) |
| 5 | Require Flow Auto-Layout | [metadata-xml-example-flows.md](metadata-xml-example-flows.md) |
| 6 | Flow Missing Fault Handler | [metadata-xml-example-flows.md](metadata-xml-example-flows.md) |

---

## How to Create These

1. Run `sf code-analyzer ast-dump --file your-file.xml --language xml` to see the DOM structure. If ast-dump fails, read the raw XML file directly — the file content IS the AST.
2. Write XPath using `local-name()` for element matching and `@Text` for text content (NOT `text()`)
3. Navigate from text nodes to parent elements using `../..`
4. Scope to the correct metadata type by checking the root element or using `ancestor::`
5. Configure `file_extensions: { xml: [".xml"] }` in `code-analyzer.yml` (just `.xml` covers all compound metadata extensions)
6. Add the rule to a ruleset XML file with `language="xml"`
7. Reference the ruleset in `code-analyzer.yml` under `engines.pmd.custom_rulesets`
8. Validate: `sf code-analyzer rules --rule-selector pmd:RuleName`
9. Test positive + negative: run against both a violating and clean metadata file

## Complete Multi-Rule Ruleset Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ruleset name="MetadataGovernance"
    xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">

    <description>Org governance rules for Salesforce metadata</description>

    <rule name="NoDangerousPermissions" language="xml"
          message="Permission set grants ModifyAllData or ViewAllData"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
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

    <rule name="FieldRequiresDescription" language="xml"
          message="Custom field must have a non-empty description"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
        <priority>3</priority>
        <properties>
            <property name="xpath">
                <value><![CDATA[
//*[local-name()='CustomField'][not(*[local-name()='description']) or *[local-name()='description'][not(@Text)]]
]]></value>
            </property>
        </properties>
    </rule>

    <rule name="MinimumApiVersion" language="xml"
          message="API version must be 60.0 or higher"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
        <priority>3</priority>
        <properties>
            <property name="xpath">
                <value><![CDATA[
//*[local-name()='apiVersion']/*[number(@Text) < 60]
]]></value>
            </property>
        </properties>
    </rule>
</ruleset>
```
