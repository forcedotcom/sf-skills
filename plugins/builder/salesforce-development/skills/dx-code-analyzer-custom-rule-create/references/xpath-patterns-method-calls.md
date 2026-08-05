# XPath Patterns for Method Calls and Annotations

[← Back to XPath Patterns Index](xpath-patterns.md)

## Method Call Patterns

### Ban System.debug (non-test classes)

```xpath
//MethodCallExpression[@FullMethodName='System.debug']
  [not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

**AST evidence:** `MethodCallExpression` has `@FullMethodName='System.debug'`. Test classes have `ModifierNode[@Test = true()]`.

**Catches:** `System.debug('anything');` in production classes
**Does NOT catch (correct):** Same call inside `@IsTest` classes

### Ban Database.query (dynamic SOQL — SOQL injection risk)

```xpath
//MethodCallExpression[@FullMethodName='Database.query']
```

**AST evidence:** `MethodCallExpression[@FullMethodName='Database.query']` (line 118 of verified AST)

To exclude test classes:
```xpath
//MethodCallExpression[@FullMethodName='Database.query']
  [not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

### Ban Test.isRunningTest() in production code

```xpath
//MethodCallExpression[@FullMethodName='Test.isRunningTest']
  [not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

### Ban specific method calls (generic pattern)

```xpath
//MethodCallExpression[@FullMethodName='ClassName.methodName']
```

Common examples:
- `@FullMethodName='System.debug'`
- `@FullMethodName='Database.query'`
- `@FullMethodName='Test.isRunningTest'`
- `@FullMethodName='UserInfo.getUserId'`
- `@FullMethodName='Limits.getQueries'`

---

## Annotation Patterns

### @AuraEnabled without cacheable=true

```xpath
//Method/ModifierNode/Annotation[@Name='AuraEnabled'
  and not(AnnotationParameter[@Name='cacheable' and @Value='true'])]
```

**AST evidence:** `Annotation[@Name='AuraEnabled']` with child `AnnotationParameter[@Name='cacheable'][@Value='true']`

**Catches:** `@AuraEnabled public static ...` (no cacheable)
**Does NOT catch (correct):** `@AuraEnabled(cacheable=true) public static ...`

### @future methods (recommend Queueable instead)

```xpath
//Method/ModifierNode/Annotation[@Name='Future']
```

**AST evidence:** Annotation `@Name='Future'` (note: PMD normalizes `@future` → `Future` in the Name attribute, but `@RawName='future'`)

### @SuppressWarnings usage (audit/ban)

```xpath
//Annotation[@Name='SuppressWarnings']
```

**AST evidence:** `Annotation[@Name='SuppressWarnings']` with `AnnotationParameter[@Name='value'][@Value='PMD.RuleName']`

To flag specific suppressions:
```xpath
//Annotation[@Name='SuppressWarnings']/AnnotationParameter[contains(@Value, 'ApexCRUDViolation')]
```

### @IsTest without testFor parameter

From GitHub issue #2008:
```xpath
//UserClass/ModifierNode/Annotation[
  @Name='IsTest'
  and not(AnnotationParameter[@Name='testFor'])
]
```

### @IsTest class without System.runAs

```xpath
//UserClass[ModifierNode[@Test = true()]]
  /Method[ModifierNode[@Test = true()]]
  /BlockStatement[not(.//RunAsBlockStatement)]
```

**AST evidence:** `RunAsBlockStatement` is the node for `System.runAs(...) { }` blocks.
