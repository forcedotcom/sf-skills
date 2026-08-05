# XPath Patterns for Security

[← Back to XPath Patterns Index](xpath-patterns.md)

## Security Patterns

### Class without sharing declaration

```xpath
//UserClass[
  @Nested = false()
  and ModifierNode[@WithSharing = false() and @WithoutSharing = false() and @InheritedSharing = false()]
]
```

**AST evidence:** `ModifierNode` has `@WithSharing`, `@WithoutSharing`, `@InheritedSharing` — all `false()` means no sharing keyword declared (implicit without sharing).

Added `@Nested = false()` to exclude inner classes (which inherit from parent).

> ⚠️ **PMD 7 boolean attributes:** `@WithSharing`, `@WithoutSharing`, `@InheritedSharing`, and `@Nested` are boolean-typed in PMD 7 — string comparison (`='false'`) errors with "Cannot compare xs:boolean to xs:string". Always use `= false()` / `= true()`. See [xpath-patterns.md](xpath-patterns.md) for the full list.

### SOQL without WITH USER_MODE or SECURITY_ENFORCED

```xpath
//SoqlExpression[
  not(contains(@CanonicalQuery, 'WITH USER_MODE'))
  and not(contains(@CanonicalQuery, 'WITH SECURITY_ENFORCED'))
]
[not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

**AST evidence:** `SoqlExpression[@CanonicalQuery]` contains the full normalized query text.

### Hardcoded Salesforce IDs (structural — string literals 15-18 chars)

```xpath
//LiteralExpression[
  @LiteralType='STRING'
  and string-length(@Image) >= 15
  and string-length(@Image) <= 18
]
[not(ancestor::UserClass[ModifierNode[@Test = true()]])]
```

**Note:** `matches()` function may not be available in all PMD XPath versions. The string-length check catches most cases. For precision, use Regex engine instead.
