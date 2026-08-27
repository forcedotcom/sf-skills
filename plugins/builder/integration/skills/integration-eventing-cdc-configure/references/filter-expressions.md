# Filter Expression Reference

The `<filterExpression>` body is a SOQL-WHERE-clause-body — predicate only, no `WHERE` keyword. The platform supports a subset of SOQL grammar for CDC filters; this reference documents what the dry-run deploy verifies.

## Operators by field type

| Field type | Supported operators | Notes |
|---|---|---|
| Text | `=`, `!=`, `IN`, `NOT IN`, `LIKE` | `LIKE` accepts `%` wildcard. Quote string literals with single quotes. |
| Number / Currency / Percent | `=`, `!=`, `<`, `<=`, `>`, `>=` | Numeric literals unquoted. |
| Boolean (Checkbox) | `=`, `!=` | Use `true` / `false` literal — no quotes. |
| Date | `=`, `!=` | Named literals (`TODAY`, `THIS_WEEK`, `LAST_N_DAYS:7`) and ISO date strings work. |
| DateTime | `=`, `!=` only | **Range operators (`>`, `<`) are rejected** — "Only equality operators are supported for this field type or value". |
| Reference (lookup ID) | `=`, `!=`, `IN`, `NOT IN` | Use the 18-character ID in single quotes: `OwnerId = '005000000000000AAA'`. |
| Picklist | `=`, `!=`, `IN`, `NOT IN` | Quote the value as a string. |

## Compound expressions

`AND`, `OR`, and parentheses all work. There's no documented limit on nesting depth.

```text
(Industry = 'Technology' OR Industry = 'Finance') AND AnnualRevenue > 0 AND Phone != null
```

## Null checks

```text
Phone = null
Phone != null
```

`null` is a literal — no quotes.

`ISBLANK()` and `ISNULL()` are **not** valid filter operators — they parse-fail with "unexpected token". They work in formulas but not in CDC filter expressions. Use `Field = null` / `Field != null` instead.

## Functions

`LOWER(Name) = 'acme'` deploys successfully. Other SOQL functions probably work, but only `LOWER` has been verified in this skill's dataset. Test before relying on `UPPER`, `CONVERTCURRENCY`, etc.

## What the filter cannot do

| Pattern | Deploy error |
|---|---|
| `WHERE Industry = 'Tech'` | "filter expression has syntax errors: unexpected token: 'WHERE'" — drop the keyword. |
| `IsDeleted = false` | "The IsDeleted field in the filter expression is invalid." Soft-deleted records still emit ChangeEvent; you cannot filter them out via this mechanism. |
| `Owner.Username = 'foo@bar.com'` | "The Owner.Username field in the filter expression is invalid." Relationship traversal works in `<enrichedFields>` rejection messages but NOT in filter expressions either — single-hop only. |
| `LastModifiedDate > LAST_N_DAYS:30` | "Only equality operators are supported for this field type or value." DateTime is equality-only; for "recent changes" semantics, use `LastModifiedDate = LAST_N_DAYS:N` (which compares to the *day*, not the timestamp). |

## Field-to-field comparison: not supported

The right-hand side of a comparison must be a **literal**. Field references are rejected.

| Wrong | Deploy error |
|---|---|
| `BillingCity = ShippingCity` | "syntax errors: unexpected token: 'ShippingCity'" |
| `NumberOfEmployees > AnnualRevenue` | "unexpected token: 'AnnualRevenue'" |

If the user wants "records where two fields differ," that logic must live downstream of the change event consumer, not in the filter.

## Composite (compound) fields like Address: dotted-component is the only valid form

Counterintuitively, the opposite rule applies for composite fields like `BillingAddress` vs. relationship traversals like `Owner.Name`. Compound fields **require** dot-notation; flat component names are rejected.

| Pattern | Result |
|---|---|
| `BillingAddress.City = 'San Francisco'` | ✓ deploys — required form for compound fields |
| `BillingAddress = null` | ✗ "Compound field BillingAddress has to be used with a component field in a filter expression" |
| `BillingCity = 'San Francisco'` (flat component) | ✗ "The BillingCity field in the filter expression is invalid" |
| `BillingState`, `BillingPostalCode`, `BillingCountry`, `BillingLatitude` (flat) | ✗ all rejected as invalid |

So, for the same `BillingAddress` field, the accepted form differs by location:

| Location | `BillingAddress` (compound) | `BillingAddress.City` (dotted) | `BillingCity` (flat component) |
|---|---|---|---|
| `<filterExpression>` | ✗ "has to be used with a component field" | ✓ deploys (required form) | ✗ "field is invalid" |
| `<enrichedFields>` | ✓ deploys | ✗ "isn't valid" (dots never allowed) | ✗ "isn't valid" (components not exposed at this layer) |

Rules per location:

- **Filter expression**: address components are reachable only via dotted form on the compound (`BillingAddress.City`). Both the compound itself (no component) and the flat component name are rejected.
- **Enrichment field**: takes a top-level field API name only. The compound `BillingAddress` is a top-level field and works; dotted forms are never valid here regardless of whether the dot would be a compound-component select or a relationship traversal; flat components like `BillingCity` are not top-level enrichable fields and are rejected.
- **Relationship traversal** (`Owner.Name`, `Parent.Industry`) is rejected in both locations.

The mental model: compound fields are a single physical column with sub-components; relationships are joins. The filter parser supports dotted access into compound sub-components but never into joins. The enrichment list takes top-level field names only and never accepts dots; the platform handles compound-vs-component decomposition itself when emitting the change event payload.

## What's NOT yet verified

- Aggregate functions or subqueries — almost certainly unsupported.
- Operators on Long Text, Rich Text, Encrypted, Geolocation field types.
- Filter on a custom field that doesn't exist (deploy-time error vs runtime).
- Custom-object-specific picklist with locale-sensitive values.

If the user requests one of these and the deploy succeeds — update this file. If it fails — capture the error here.
