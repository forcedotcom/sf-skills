# Apex AST Node Reference

PMD 7.x Apex AST node types and their attributes. Use `sf code-analyzer ast-dump --file <file.cls>` to see the actual tree for your code.

## Node Hierarchy (Common Structure)

```text
ApexFile
├── UserClass / UserInterface / UserTrigger / UserEnum
│   ├── FormalComment (Javadoc)
│   ├── ModifierNode (public, private, static, etc.)
│   ├── Field (class-level variables)
│   │   └── VariableDeclaration
│   └── Method
│       ├── ModifierNode
│       ├── Parameter
│       └── BlockStatement
│           ├── VariableDeclarationStatements
│           ├── ExpressionStatement
│           │   └── MethodCallExpression
│           ├── IfElseBlockStatement
│           │   └── IfBlockStatement
│           ├── ForEachStatement / ForLoopStatement / WhileLoopStatement
│           ├── TryCatchFinallyBlockStatement
│           │   ├── BlockStatement (try body)
│           │   ├── CatchBlockStatement
│           │   └── BlockStatement (finally body)
│           ├── DmlInsertStatement / DmlUpdateStatement / DmlDeleteStatement
│           ├── ReturnStatement
│           └── ThrowStatement
```

## ModifierNode Attributes

Every class, method, field, and parameter has a `ModifierNode` with these boolean attributes:

| Attribute | Meaning |
|-----------|---------|
| `Public` | public access |
| `Private` | private access |
| `Protected` | protected access |
| `Global` | global access |
| `Static` | static member |
| `Final` | final/const |
| `Abstract` | abstract method/class |
| `Virtual` | virtual method/class |
| `Override` | overrides parent method |
| `Test` | @IsTest annotated |
| `TestOrTestSetup` | @IsTest or @TestSetup |
| `WebService` | webservice method |
| `WithSharing` | with sharing class |
| `WithoutSharing` | without sharing class |
| `InheritedSharing` | inherited sharing class |
| `Transient` | transient field |
| `Modifiers` | Bitmask integer of all modifiers |

⚠️ **PMD 7 Boolean Attribute Comparison:**

In PMD 7, these boolean attributes are **always present** on the node — they are never absent. This means:
- ✅ `@WithSharing = false()` — correct (XPath boolean function)
- ✅ `@WithSharing = true()` — correct
- ❌ `@WithSharing = 'false'` — WRONG (string comparison, won't match)
- ❌ `not(@WithSharing)` — WRONG (attribute always exists, so this is always false)
- ❌ `@WithSharing` (as existence check) — WRONG (always true, attribute always present)

Use the XPath `true()`/`false()` functions for boolean comparisons:
```xpath
<!-- Classes without sharing declaration -->
//UserClass[ModifierNode[@WithSharing = false() and @WithoutSharing = false() and @InheritedSharing = false()]]

<!-- Abstract classes -->
//UserClass[ModifierNode[@Abstract = true()]]
```

## MethodCallExpression Attributes

| Attribute | Example | Notes |
|-----------|---------|-------|
| `FullMethodName` | `'System.debug'`, `'Database.query'` | Most reliable for matching |
| `MethodName` | `'debug'`, `'query'` | Just the method part |
| `InputParametersSize` | `'1'`, `'0'` | Number of arguments |

## LiteralExpression Attributes

| Attribute | Values | Notes |
|-----------|--------|-------|
| `LiteralType` | `STRING`, `INTEGER`, `DECIMAL`, `DOUBLE`, `LONG`, `BOOLEAN` | Type of literal |
| `Image` | The literal value | For strings, excludes quotes |
| `String` | `'true'` / `'false'` | Boolean shorthand |
| `Null` | `'true'` / `'false'` | Is it a null literal |

## SoqlExpression Attributes

| Attribute | Example | Notes |
|-----------|---------|-------|
| `Query` | `'SELECT Id FROM Account WHERE Name = :name'` | Original SOQL as written |
| `CanonicalQuery` | `'SELECT Id FROM Account WHERE Name = :tmpVar1'` | Normalized (bind vars replaced) |

## Annotation Node

```xml
<Annotation Image="IsTest">
  <AnnotationParameter Name="testFor" Value="'ApexClass:MyService'" />
</Annotation>
```

Use: `//Annotation[@Image='IsTest']` to find test annotations.

## DML Nodes

| Statement | Node | Notes |
|-----------|------|-------|
| `insert x;` | `DmlInsertStatement` | |
| `update x;` | `DmlUpdateStatement` | |
| `delete x;` | `DmlDeleteStatement` | |
| `upsert x;` | `DmlUpsertStatement` | |
| `undelete x;` | `DmlUndeleteStatement` | |
| `Database.insert(x)` | `MethodCallExpression[@FullMethodName='Database.insert']` | Method-form DML |

## Tips for Reading AST Dumps

1. **`Image` attribute** = the actual source name (variable name, class name, method name)
2. **`DefiningType` attribute** = which class this node belongs to (present on every node)
3. **`RealLoc='true'`** = this node has a real source position (not compiler-generated)
4. **`RealLoc='false'`** = compiler-generated node (e.g., implicit modifiers, empty references)
5. **`EmptyReferenceExpression`** = placeholder for unqualified variable access (ignore these)
6. **`Type` attribute on VariableDeclaration** = the declared type (e.g., `'Account'`, `'List<Contact>'`)
