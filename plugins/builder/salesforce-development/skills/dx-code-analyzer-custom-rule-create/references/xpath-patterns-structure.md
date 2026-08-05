# XPath Patterns for Code Structure, Tests, and Naming

[← Back to XPath Patterns Index](xpath-patterns.md)

## Code Structure Patterns

### DML without try-catch

```xpath
//DmlInsertStatement[not(ancestor::TryCatchFinallyBlockStatement)]
|
//DmlUpdateStatement[not(ancestor::TryCatchFinallyBlockStatement)]
|
//DmlDeleteStatement[not(ancestor::TryCatchFinallyBlockStatement)]
|
//DmlUpsertStatement[not(ancestor::TryCatchFinallyBlockStatement)]
```

**AST evidence:** DML nodes sit inside `TryCatchFinallyBlockStatement` when wrapped in try-catch.

To exclude test classes:
```xpath
//DmlInsertStatement[
  not(ancestor::TryCatchFinallyBlockStatement)
  and not(ancestor::UserClass[ModifierNode[@Test = true()]])
]
```

### Empty catch blocks (swallowed exceptions)

```xpath
//CatchBlockStatement[BlockStatement[not(*)]]
```

**AST evidence:** `CatchBlockStatement` contains a `BlockStatement`. Empty body = `BlockStatement` with no children.

### Nested if statements (max depth 3)

```xpath
//IfBlockStatement[
  ancestor::IfBlockStatement[
    ancestor::IfBlockStatement[
      ancestor::IfBlockStatement
    ]
  ]
]
```

### Methods with too many parameters

```xpath
//Method[@Arity >= 5 and @Constructor = false()]
```

**AST evidence:** `Method[@Arity]` gives parameter count directly.

### Logic in trigger (should delegate to handler)

For trigger files (UserTrigger node):
```xpath
//UserTrigger/BlockStatement//DmlInsertStatement
|
//UserTrigger/BlockStatement//DmlUpdateStatement
|
//UserTrigger/BlockStatement//SoqlExpression
|
//UserTrigger/BlockStatement//MethodCallExpression[@FullMethodName='Database.query']
```

---

## Test Quality Patterns

### Test method without assertions

```xpath
//Method[ModifierNode[@Test = true()]]
  /BlockStatement[
    not(.//MethodCallExpression[
      contains(@FullMethodName, 'System.assert')
      or contains(@FullMethodName, 'Assert.')
    ])
  ]
```

**Catches:** Test methods with no `System.assert*` or `Assert.*` calls anywhere in their body.

### Test method without System.runAs

```xpath
//Method[ModifierNode[@Test = true()]]
  /BlockStatement[not(.//RunAsBlockStatement)]
```

**AST evidence:** `System.runAs(user) { ... }` becomes `RunAsBlockStatement` in the AST.

### Test using seeAllData=true

```xpath
//Annotation[@Name='IsTest']/AnnotationParameter[@Name='seeAllData' and @Value='true']
```

---

## Naming Convention Patterns

### Class name doesn't match file (non-test)

This is better enforced by the built-in rule, but the XPath pattern for a specific convention:
```xpath
//UserClass[@Nested = false() and not(starts-with(@Image, 'Test')) and not(ends-with(@Image, 'Test'))]
```

### Method naming (non-standard)

```xpath
//Method[
  @Constructor = false()
  and not(ModifierNode[@Test = true()])
  and not(starts-with(@Image, 'get'))
  and not(starts-with(@Image, 'set'))
  and not(starts-with(@Image, 'is'))
  and matches(@Image, '^[A-Z]')
]
```

**Catches:** Methods starting with uppercase in non-test code (Apex convention is camelCase).
