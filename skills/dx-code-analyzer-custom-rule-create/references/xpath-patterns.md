# XPath Patterns for Apex Custom Rules

Pre-validated PMD XPath patterns for Salesforce Apex code. Every pattern below has been verified against actual `sf code-analyzer ast-dump` output. Use these directly — but still run `ast-dump` on YOUR code to confirm node names haven't changed in newer PMD versions.

## XPath Syntax Quick Reference

| Syntax | Meaning |
|--------|---------|
| `//Node` | Find Node anywhere in tree |
| `//Node[@attr='value']` | Node with specific string attribute value |
| `//Node[@attr = true()]` | Node with boolean attribute = true (**PMD 7 requirement**) |
| `//Parent//Child` | Child anywhere inside Parent (any descendant) |
| `//Parent/Child` | **Direct child only** — use this to avoid false positives |
| `//Node[not(...)]` | Node where condition is NOT true |
| `//Node[ancestor::Other]` | Node that has Other as an ancestor |
| `//Node[.//Other]` | Node that contains Other somewhere inside |
| `@Image` | The name/text of the node |
| `@FullMethodName` | Full qualified method name (e.g., 'System.debug') |
| `@LiteralType` | Type of literal: STRING, INTEGER, BOOLEAN, TRUE, FALSE, NULL |

### PMD 7 Boolean Attributes — MUST use `true()` / `false()`

In PMD 7, many node attributes are **boolean typed**, not strings — even though `ast-dump` renders them as `Nested='false'` or `Test='true'` in the XML output. String attributes (`@FullMethodName`, `@Name`, `@Image`, `@LiteralType`, etc.) are safe to copy from the AST dump as-is. But **attributes whose values are `true` or `false` in the dump are boolean-typed** — comparing them with string literals (`@Nested='false'`) causes the error: "Cannot compare xs:boolean to xs:string".

Known boolean attributes by node:

| Node | Boolean Attributes |
|------|--------------------|
| `ModifierNode` | `@Test`, `@Public`, `@Private`, `@Protected`, `@Static`, `@Abstract`, `@Final`, `@Global`, `@WithSharing`, `@WithoutSharing`, `@InheritedSharing` |
| `UserClass` | `@Nested` |
| `Method` | `@Constructor` |

| WRONG | CORRECT |
|-------|---------|
| `UserClass[@Nested='false']` | `UserClass[@Nested = false()]` |
| `UserClass[@Nested='true']` | `UserClass[@Nested = true()]` |
| `ModifierNode[@Test='true']` | `ModifierNode[@Test = true()]` |
| `ModifierNode[@Static='false']` | `ModifierNode[@Static = false()]` |
| `Method[@Constructor = false()]` | `Method[@Constructor = false()]` |

`true()` and `false()` are XPath boolean functions. If you see an attribute that looks boolean in the AST dump, assume it is typed as boolean and use `true()`/`false()`.

---

### `/` vs `//` — The Most Common Source of False Positives

| XPath | Meaning | Risk |
|-------|---------|------|
| `//ForEachStatement//SoqlExpression` | SOQL anywhere inside ForEachStatement | ❌ Matches iterable position too |
| `//ForEachStatement/BlockStatement//SoqlExpression` | SOQL inside loop **body** only | ✅ Correct |

**Rule of thumb:** When matching inside a structural node (loop, if, try), always scope to `/BlockStatement//` to target the body, not sibling children like iterables or conditions.

---

## Pattern Categories (By Topic)

For detailed patterns in each category, see the dedicated files below:

| Category | File | Contents |
|----------|------|----------|
| Governor Limits | [xpath-patterns-governor-limits.md](xpath-patterns-governor-limits.md) | SOQL/DML in loops, Database methods in loops |
| Method Calls & Annotations | [xpath-patterns-method-calls.md](xpath-patterns-method-calls.md) | Ban specific methods, @AuraEnabled, @future, @IsTest, @SuppressWarnings patterns |
| Security | [xpath-patterns-security.md](xpath-patterns-security.md) | Sharing declarations, SOQL security modes, hardcoded IDs |
| Code Structure, Tests & Naming | [xpath-patterns-structure.md](xpath-patterns-structure.md) | DML error handling, empty catches, test assertions, naming conventions |

---

## Key Apex AST Node Names

| Apex Construct | AST Node | Key Attributes |
|---|---|---|
| Class | `UserClass` | `Image`, `SuperClassName`, `InterfaceNames`, `Nested` |
| Interface | `UserInterface` | `Image`, `SuperInterfaceName` |
| Method | `Method` | `Image`, `Arity`, `ReturnType`, `Constructor` |
| Trigger | `UserTrigger` | `Image`, `TargetName` |
| SOQL query | `SoqlExpression` | `Query`, `CanonicalQuery` |
| DML insert | `DmlInsertStatement` | |
| DML update | `DmlUpdateStatement` | |
| DML delete | `DmlDeleteStatement` | |
| DML upsert | `DmlUpsertStatement` | |
| Method call | `MethodCallExpression` | `FullMethodName`, `MethodName`, `InputParametersSize` |
| For-each loop | `ForEachStatement` | children: VariableDeclarationStatements, VariableExpression, **BlockStatement** (body), iterable |
| For loop | `ForLoopStatement` | children: init, condition, update, **BlockStatement** (body) |
| While loop | `WhileLoopStatement` | children: condition, **BlockStatement** (body) |
| If/else | `IfElseBlockStatement` > `IfBlockStatement` | `ElseStatement` |
| Try-catch | `TryCatchFinallyBlockStatement` | |
| Catch block | `CatchBlockStatement` | `ExceptionType`, `VariableName` |
| RunAs | `RunAsBlockStatement` | |
| String literal | `LiteralExpression` | `@LiteralType='STRING'`, `@Image` (value without quotes) |
| Integer literal | `LiteralExpression` | `@LiteralType='INTEGER'`, `@Image` |
| Boolean true | `LiteralExpression` | `@LiteralType='TRUE'` |
| Boolean false | `LiteralExpression` | `@LiteralType='FALSE'` |
| Null | `LiteralExpression` | `@LiteralType='NULL'` |
| Variable | `VariableExpression` | `@Image` (name) |
| Assignment | `AssignmentExpression` | `@Op` (=, +=, etc.) |
| Binary expression | `BinaryExpression` | `@Op` (+, -, *, /) |
| Boolean expression | `BooleanExpression` | `@Op` (>, <, ==, !=, >=, <=) |
| New object | `NewKeyValueObjectExpression` | `@Type` |
| New object (no-arg) | `NewObjectExpression` | `@Type` |
| Return | `ReturnStatement` | |
| Annotation | `Annotation` | `@Name` (IsTest, AuraEnabled, Future, SuppressWarnings) |
| Annotation param | `AnnotationParameter` | `@Name`, `@Value` |
| Modifier | `ModifierNode` | `Public`, `Private`, `Static`, `Test`, `WithSharing`, `Global`, etc. |
| Parameter | `Parameter` | `@Image` (name), `@Type` |
| New list | `NewListInitExpression` | |
| New map | `NewMapInitExpression` | |

---

## XPath Best Practices

1. **ALWAYS run `ast-dump` first** — never guess node names, even for patterns listed here
2. **Use `/BlockStatement//` for loop/if body** — avoids matching iterables, conditions, etc.
3. **Use `@FullMethodName`** for method calls — not `@Image` or `@MethodName` alone
4. **Exclude test classes** with `[not(ancestor::UserClass[ModifierNode[@Test = true()]])]`
5. **Test with BOTH positive AND negative cases** — ensure no false positives
6. **Prefer `//Node` over absolute paths** — code structure varies
7. **Use `ancestor::` / `not(ancestor::)`** for structural exclusions (try-catch, test class)
8. **Keep XPath simple** — complex expressions are fragile and hard to maintain

## Common False Positive Traps

| Pattern | Trap | Fix |
|---------|------|-----|
| SOQL in loop | `//ForEachStatement//SoqlExpression` matches iterable | Use `/BlockStatement//` |
| DML in loop | Same as above | Use `/BlockStatement//` |
| Ban method in all code | Flags test code too | Add `[not(ancestor::UserClass[ModifierNode[@Test = true()]])]` |
| Empty block detection | Matches intentional empty constructors | Add `[@Constructor = false()]` or exclude specific patterns |
| No sharing declaration | Flags inner classes (which inherit) | Add `[@Nested = false()]` |
| String literal length check | Matches test data strings | Exclude test classes |
