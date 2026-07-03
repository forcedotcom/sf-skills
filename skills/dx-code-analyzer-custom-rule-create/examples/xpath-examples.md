# XPath Rule Examples

Real-world custom PMD/XPath rules for Apex, derived from community requests and common enforcement needs.

## Example 1: Ban System.debug in Production Code

**Problem:** Debug statements clutter logs and expose sensitive data.

**Sample violating code:**
```apex
public class MyService {
    public void doWork() {
        System.debug('Sensitive: ' + record.SSN__c);
    }
}
```

**AST nodes (from ast-dump):**
```xml
<MethodCallExpression FullMethodName='System.debug' InputParametersSize='1' ...>
```

**XPath:**
```xpath
//MethodCallExpression[@FullMethodName='System.debug']
  [not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

**PMD ruleset:**
```xml
<rule name="NoSystemDebugInProduction" language="apex"
      message="System.debug statements are not allowed in production code"
      class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">
    <priority>3</priority>
    <properties>
        <property name="xpath">
            <value>//MethodCallExpression[@FullMethodName='System.debug'][not(ancestor::UserClass[ModifierNode[@Test = true()]])]</value>
        </property>
    </properties>
</rule>
```

---

## Example 2: SOQL Query Inside a Loop

**Problem:** Governor limit risk — N+1 queries.

**Sample violating code:**
```apex
public class AccountProcessor {
    public void process(List<Account> accounts) {
        for (Account acc : accounts) {
            List<Contact> contacts = [SELECT Id FROM Contact WHERE AccountId = :acc.Id];
        }
    }
}
```

**AST nodes:**
```xml
<ForEachStatement>
    ...
    <BlockStatement>
        <VariableDeclarationStatements>
            <VariableDeclaration>
                <SoqlExpression Query='SELECT Id FROM Contact...' />
```

**XPath:**
```xpath
//ForEachStatement/BlockStatement//SoqlExpression
|
//ForLoopStatement/BlockStatement//SoqlExpression
|
//WhileLoopStatement/BlockStatement//SoqlExpression
```

> ⚠️ **Why `/BlockStatement//`?** ForEachStatement has the iterable SOQL as a direct child alongside BlockStatement. Without scoping to `/BlockStatement//`, the XPath also matches `for (Contact c : [SELECT...])` — a valid Apex idiom that is NOT a governor limit risk.

---

## Example 3: Enforce @IsTest(testFor) Annotation

**Problem:** Test classes should specify which class they test for traceability.
(GitHub issue #2008 — real community request)

**Sample violating code:**
```apex
@IsTest
public class MyServiceTest {
    // Missing testFor parameter
}
```

**AST nodes:**
```xml
<UserClass Image='MyServiceTest'>
    <ModifierNode Test='true'>
        <Annotation Image='IsTest'>
            <!-- No AnnotationParameter with Name='testFor' -->
        </Annotation>
    </ModifierNode>
```

**XPath:**
```xpath
/ApexFile/UserClass/ModifierNode/Annotation[
  @Image='IsTest'
  and count(AnnotationParameter[@Name='testFor']) = 0
]
```

---

## Example 4: DML Operations Without Try-Catch

**Problem:** Unhandled DML exceptions cause runtime failures.
(GitHub issue #738 — user requested "detect missing try-catch")

**Sample violating code:**
```apex
public class AccountService {
    public void createAccount(String name) {
        Account acc = new Account(Name = name);
        insert acc;  // No try-catch!
    }
}
```

**AST nodes:**
```xml
<DmlInsertStatement>
    <VariableExpression Image='acc' />
</DmlInsertStatement>
<!-- No TryCatchFinallyBlockStatement ancestor -->
```

**XPath:**
```xpath
//DmlInsertStatement[not(ancestor::TryCatchFinallyBlockStatement)]
|
//DmlUpdateStatement[not(ancestor::TryCatchFinallyBlockStatement)]
|
//DmlDeleteStatement[not(ancestor::TryCatchFinallyBlockStatement)]
```

---

## Example 5: Nested If Statements (Max Depth 3)

**Problem:** Deep nesting reduces readability and maintainability.

**Sample violating code:**
```apex
public class ComplexLogic {
    public void process(Integer a, Integer b, Integer c, Integer d) {
        if (a > 0) {
            if (b > 0) {
                if (c > 0) {
                    if (d > 0) {  // 4th level — violation!
                        doWork();
                    }
                }
            }
        }
    }
}
```

**XPath (flags depth 4+):**
```xpath
//IfBlockStatement[
  ancestor::IfBlockStatement[
    ancestor::IfBlockStatement[
      ancestor::IfBlockStatement
    ]
  ]
]
```

---

## Example 6: Class Without Explicit Sharing Declaration

**Problem:** Classes without sharing default to "without sharing" — security risk.

**Sample violating code:**
```apex
public class UnsafeService {  // No "with sharing" or "without sharing"
    public List<Account> getAccounts() {
        return [SELECT Id FROM Account];
    }
}
```

**AST nodes:**
```xml
<UserClass Image='UnsafeService'>
    <ModifierNode WithSharing='false' WithoutSharing='false' InheritedSharing='false' ...>
```

**XPath:**
```xpath
//UserClass[
  ModifierNode[
    @WithSharing = false()
    and @WithoutSharing = false()
    and @InheritedSharing = false()
  ]
  and not(ModifierNode[@Test = true()])
]
```

---

## How to Create These

For each example above, the creation process was:

1. Write the sample violating code (5-10 lines)
2. Run: `sf code-analyzer ast-dump --file sample.cls`
3. Find the relevant node in the XML output
4. Write XPath using the exact node names and attributes
5. Create the ruleset XML using the template
6. Validate: `sf code-analyzer rules --rule-selector pmd:RuleName`
7. Test: `sf code-analyzer run --rule-selector pmd:RuleName --target sample.cls`
