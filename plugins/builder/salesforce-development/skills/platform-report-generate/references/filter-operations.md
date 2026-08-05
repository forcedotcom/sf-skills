# Filter Operations Reference

The `<operation>` element in a `<filter>` block determines how the field value is compared. Use these values exactly as shown.

## Text & Picklist Operations

| Operation | Description | `<value>` Required | Example |
|-----------|-------------|-------------------|---------|
| `equals` | Exact match (case-insensitive for text) | Yes | `<value>Closed Won</value>` |
| `notEqual` | Does not equal | Yes | `<value>Closed Lost</value>` |
| `contains` | Contains substring | Yes | `<value>Enterprise</value>` |
| `notContain` | Does not contain substring | Yes | `<value>Test</value>` |
| `startsWith` | Starts with prefix | Yes | `<value>Acme</value>` |

## Numeric & Currency Operations

| Operation | Description | `<value>` Required | Example |
|-----------|-------------|-------------------|---------|
| `equals` | Equal to | Yes | `<value>100000</value>` |
| `notEqual` | Not equal to | Yes | `<value>0</value>` |
| `lessThan` | Less than | Yes | `<value>50000</value>` |
| `greaterThan` | Greater than | Yes | `<value>100000</value>` |
| `lessOrEqual` | Less than or equal to | Yes | `<value>50000</value>` |
| `greaterOrEqual` | Greater than or equal to | Yes | `<value>100000</value>` |

## Multi-Select Picklist Operations

| Operation | Description | `<value>` Required | Example |
|-----------|-------------|-------------------|---------|
| `includes` | Includes any of the specified values | Yes | `<value>Web;Phone</value>` (semicolon-separated) |
| `excludes` | Excludes all of the specified values | Yes | `<value>Other;Unknown</value>` |

## Blank / Null Operations

| Operation | Description | `<value>` Required | Example |
|-----------|-------------|-------------------|---------|
| `isBlank` | Field is null or empty | No | (no `<value>` element needed) |
| `notBlank` | Field is not null and not empty | No | (no `<value>` element needed) |

```xml
<filter>
    <field>ACCOUNT_NAME</field>
    <operation>notBlank</operation>
</filter>
```

## Geolocation Operations

| Operation | Description | `<value>` Required | Example |
|-----------|-------------|-------------------|---------|
| `within` | Within specified distance | Yes | `<value>DISTANCE(BillingAddress, GEOLOCATION(37.7749,-122.4194), 'mi') < 50</value>` |

## Multiple Values in a Single Filter

For `equals` and `notEqual` operations on picklist fields, separate multiple values with commas:
```xml
<filter>
    <field>STAGE_NAME</field>
    <operation>notEqual</operation>
    <value>Closed Won,Closed Lost</value>
</filter>
```

## Filter Logic

Use `<filterLogic>` to combine filters with AND/OR/NOT logic. Filters are numbered starting from 1 in the order they appear in the XML.

```xml
<filter>
    <field>STAGE_NAME</field>
    <operation>equals</operation>
    <value>Prospecting</value>
</filter>
<filter>
    <field>AMOUNT</field>
    <operation>greaterThan</operation>
    <value>10000</value>
</filter>
<filter>
    <field>LEAD_SOURCE</field>
    <operation>equals</operation>
    <value>Web</value>
</filter>
<filterLogic>1 AND (2 OR 3)</filterLogic>
```

**Rules:**
- Every filter must be referenced in the logic expression
- Parentheses control evaluation order
- Supported operators: `AND`, `OR`, `NOT`
- Maximum 20 filters per report
- Without `<filterLogic>`, all filters are combined with AND
