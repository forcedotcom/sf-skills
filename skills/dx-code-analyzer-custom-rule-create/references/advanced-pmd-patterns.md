# Advanced PMD Patterns

Multi-rule rulesets, overriding built-in rules, exclusion patterns, Java-based rules, and sharing rules across projects.

## Multiple Rules in One Ruleset File

A single ruleset XML can contain any number of rules. This is the recommended approach for teams maintaining a shared rule set:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ruleset name="TeamStandards"
    xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">

    <description>Team coding standards</description>

    <!-- Rule 1: Custom XPath rule -->
    <rule name="NoSystemDebug" language="apex"
          message="Remove System.debug before merging"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
        <priority>3</priority>
        <properties>
            <property name="xpath">
                <value><![CDATA[
//MethodCallExpression[@FullMethodName='System.debug']
  [not(ancestor::UserClass[ModifierNode[@Test = true()]])]
]]></value>
            </property>
        </properties>
    </rule>

    <!-- Rule 2: Another custom XPath rule -->
    <rule name="SoqlInLoop" language="apex"
          message="SOQL query inside a loop — move query before the loop"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
        <priority>2</priority>
        <properties>
            <property name="xpath">
                <value><![CDATA[
//ForEachStatement//SoqlExpression | //ForLoopStatement//SoqlExpression | //WhileLoopStatement//SoqlExpression
]]></value>
            </property>
        </properties>
    </rule>

    <!-- Rule 3: XML metadata rule in the same file -->
    <rule name="MinApiVersion" language="xml"
          message="Update API version to 60.0+"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
        <priority>3</priority>
        <properties>
            <property name="xpath">
                <value><![CDATA[
//*[local-name()='apiVersion'][number(substring-before(text(), '.')) < 60]
]]></value>
            </property>
        </properties>
    </rule>
</ruleset>
```

Rules with different `language` values (apex, xml, visualforce, etc.) can coexist in one ruleset. PMD applies each rule only to files matching its language.

## Overriding Built-in PMD Rules

Override severity, priority, or configurable properties on PMD's built-in rules without writing new ones:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ruleset name="CustomizedBuiltins"
    xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">

    <description>Customized built-in rule thresholds</description>

    <!-- Lower the complexity threshold from default 25 to 10 -->
    <rule ref="category/apex/design.xml/CyclomaticComplexity">
        <priority>2</priority>
        <properties>
            <property name="classReportLevel" value="40" />
            <property name="methodReportLevel" value="10" />
        </properties>
    </rule>

    <!-- Change excessive parameter count from default 4 to 3 -->
    <rule ref="category/apex/design.xml/ExcessiveParameterList">
        <properties>
            <property name="minimum" value="3" />
        </properties>
    </rule>

    <!-- Make debug statement rule high-severity instead of moderate -->
    <rule ref="category/apex/bestpractices.xml/DebugsShouldUseLoggingLevel">
        <priority>2</priority>
        <properties>
            <property name="strictMode" value="true" />
        </properties>
    </rule>

    <!-- Include an entire category with one exclusion -->
    <rule ref="category/apex/security.xml">
        <exclude name="ApexSuggestUsingNamedCred" />
    </rule>
</ruleset>
```

**Configuration:**
```yaml
# code-analyzer.yml
engines:
  pmd:
    custom_rulesets:
      - "custom-rules/customized-builtins.xml"
```

### How rule ref works

| Pattern | Effect |
|---------|--------|
| `<rule ref="category/apex/design.xml/CyclomaticComplexity">` | Override one specific rule |
| `<rule ref="category/apex/security.xml">` | Include entire category |
| `<rule ref="..."><exclude name="RuleName"/></rule>` | Include category minus specific rules |
| Nested `<priority>` | Override severity (1=Critical, 2=High, 3=Moderate, 4=Low, 5=Info) |
| Nested `<properties>` | Override configurable thresholds/options |

### Common built-in rules to customize

| Rule | Useful Properties |
|------|-------------------|
| `CyclomaticComplexity` | `classReportLevel` (default: 40), `methodReportLevel` (default: 25) |
| `ExcessiveParameterList` | `minimum` (default: 4) |
| `ExcessiveClassLength` | `minimum` (default: 1000) |
| `TooManyFields` | `maxfields` (default: 15) |
| `NcssMethodCount` | `minimum` (default: 60) |
| `DebugsShouldUseLoggingLevel` | `strictMode` (default: false) |
| `ApexUnitTestClassShouldHaveAsserts` | (no properties — exclude if unwanted) |

## Exclusion Patterns

Three mechanisms for excluding files and rules:

### 1. File exclusions in `code-analyzer.yml`

Exclude entire directories or file patterns from all engines:

```yaml
# code-analyzer.yml
ignores:
  files:
    - "**/node_modules/**"
    - "**/fflib_*"
    - "**/*Test*.cls"
    - "**/generated/**"
```

Supports glob patterns: `*`, `**`, `?`, `[...]`, `{...}`

### 2. Rule exclusions in PMD rulesets

Exclude specific rules when including an entire category:

```xml
<rule ref="category/apex/bestpractices.xml">
    <exclude name="ApexUnitTestClassShouldHaveAsserts" />
    <exclude name="ApexAssertionsShouldIncludeMessage" />
</rule>
```

### 3. Exclude patterns in PMD rulesets

Exclude files at the PMD level (applies only to rules in that ruleset):

```xml
<ruleset name="MyRules" ...>
    <exclude-pattern>.*/fflib_.*</exclude-pattern>
    <exclude-pattern>.*/test/.*</exclude-pattern>

    <rule name="..." ...>
        ...
    </rule>
</ruleset>
```

### 4. Disabling individual rules via config

Disable any rule without editing rulesets:

```yaml
# code-analyzer.yml
rules:
  pmd:
    ApexUnitTestClassShouldHaveAsserts:
      disabled: true
    CyclomaticComplexity:
      severity: "Low"    # Downgrade instead of disable
```

## Java-Based Custom Rules (Advanced)

For rules that need logic beyond XPath (complex data flow, cross-file analysis), write Java PMD rules:

1. **Create a Java class** extending `net.sourceforge.pmd.lang.apex.rule.AbstractApexRule`
2. **Compile into a JAR** file
3. **Reference in config:**

```yaml
# code-analyzer.yml
engines:
  pmd:
    java_classpath_entries:
      - "custom-rules/my-rules.jar"      # JAR with compiled rule classes
      - "custom-rules/lib/"              # Folder of JARs (all JARs inside loaded)
    custom_rulesets:
      - "category/myteam/rules.xml"      # Ruleset inside the JAR (classpath resource)
```

The JAR's ruleset XML references the Java class:
```xml
<rule name="AvoidFutureAnnotation" language="apex"
      message="Use Queueable instead of @Future"
      class="com.myteam.pmd.rules.AvoidFutureRule">
    <priority>3</priority>
</rule>
```

**Requirements:**
- Java 11+ for compilation
- PMD 7.x API (use `net.sourceforge.pmd.lang.rule.xpath.XPathRule` for XPath, or extend `AbstractApexRule` for visitor-pattern Java rules)

## Sharing Rules Across Projects

### Approach 1: Relative paths with shared config

If projects share a parent directory or monorepo:
```yaml
# code-analyzer.yml
engines:
  pmd:
    custom_rulesets:
      - "../shared-rules/team-standards.xml"    # Relative to config_root
```

`config_root` is the directory containing `code-analyzer.yml`. All relative paths resolve from there.

### Approach 2: JAR-based distribution

Package rules into a JAR and distribute via artifact repository:

1. Build a JAR containing your ruleset XML at a classpath resource path (e.g., `category/myteam/standards.xml`)
2. Place the JAR in each project's `custom-rules/` directory (or download in CI)
3. Reference in config:

```yaml
engines:
  pmd:
    java_classpath_entries:
      - "custom-rules/myteam-rules-1.0.jar"
    custom_rulesets:
      - "category/myteam/standards.xml"    # Resource inside the JAR
```

### Approach 3: Git submodule or symlink

For simpler setups, share the ruleset XML via git submodule:
```bash
git submodule add https://github.com/myteam/pmd-rules.git custom-rules/shared
```

```yaml
engines:
  pmd:
    custom_rulesets:
      - "custom-rules/shared/team-standards.xml"
```

### CI/CD Integration

All approaches work in CI because paths are relative to `config_root`. Example GitHub Actions step:

```yaml
- name: Run Code Analyzer
  run: |
    sf code-analyzer run --rule-selector "pmd:2,regex:2" --target force-app/
```

No absolute paths needed — the config file handles resolution.
