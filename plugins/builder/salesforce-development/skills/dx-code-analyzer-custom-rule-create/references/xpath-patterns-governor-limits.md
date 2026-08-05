# XPath Patterns for Governor Limits

[← Back to XPath Patterns Index](xpath-patterns.md)

## Governor Limit Patterns

### SOQL inside loops

⚠️ **Must scope to `/BlockStatement//`** — ForEachStatement has the iterable SOQL as a direct child alongside BlockStatement. Without this, `for (Contact c : [SELECT...])` is a false positive.

**ForEachStatement child structure (from ast-dump):**
```text
ForEachStatement
├── VariableDeclarationStatements   ← loop variable declaration
├── VariableExpression              ← loop variable reference
├── BlockStatement                  ← LOOP BODY — only match here
└── SoqlExpression (or VariableExpression)  ← ITERABLE — do NOT flag
```

```xpath
//ForEachStatement/BlockStatement//SoqlExpression
|
//ForLoopStatement/BlockStatement//SoqlExpression
|
//WhileLoopStatement/BlockStatement//SoqlExpression
```

**Catches:** `for (Id accId : ids) { Account acc = [SELECT ...]; }` (SOQL in body)
**Does NOT catch (correct):** `for (Contact c : [SELECT Id FROM Contact]) { ... }` (SOQL as iterable)

### DML inside loops

Same principle — scope to BlockStatement:

```xpath
//ForEachStatement/BlockStatement//DmlInsertStatement
|
//ForEachStatement/BlockStatement//DmlUpdateStatement
|
//ForEachStatement/BlockStatement//DmlDeleteStatement
|
//ForEachStatement/BlockStatement//DmlUpsertStatement
|
//ForLoopStatement/BlockStatement//DmlInsertStatement
|
//ForLoopStatement/BlockStatement//DmlUpdateStatement
|
//ForLoopStatement/BlockStatement//DmlDeleteStatement
|
//ForLoopStatement/BlockStatement//DmlUpsertStatement
|
//WhileLoopStatement/BlockStatement//DmlInsertStatement
|
//WhileLoopStatement/BlockStatement//DmlUpdateStatement
|
//WhileLoopStatement/BlockStatement//DmlDeleteStatement
|
//WhileLoopStatement/BlockStatement//DmlUpsertStatement
```

**Shorter variant** (ForEach only, most common):
```xpath
//ForEachStatement/BlockStatement//DmlInsertStatement
| //ForEachStatement/BlockStatement//DmlUpdateStatement
| //ForEachStatement/BlockStatement//DmlDeleteStatement
| //ForEachStatement/BlockStatement//DmlUpsertStatement
```

### Database methods inside loops

```xpath
//ForEachStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.query']
|
//ForEachStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.insert']
|
//ForEachStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.update']
|
//ForEachStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.delete']
|
//ForLoopStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.query']
|
//WhileLoopStatement/BlockStatement//MethodCallExpression[@FullMethodName='Database.query']
```
