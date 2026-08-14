# Policy Schema — Full Element Reference

---

## Path Enums

> **Surface principle.** The MDAPI surface is a narrower set of `*Type` enums (`RulePrincipalPathType`, `RuleResourcePathType`, `RuleContextPathType`) than what the runtime honors at evaluation time. Values that appear at runtime but are not in the MDAPI `*Type` enums are **not authorable via MDAPI** — use a runtime RuleProvider for those.

### `<principalPath>` / `<valuePrincipalPath>` — `RulePrincipalPathType` (6 values)

| Value | Meaning |
|-------|---------|
| `IS_AUTHENTICATED_USER_PATH` | Boolean "is principal an authenticated user" |
| `ASSIGNED_PERMISSIONS_PATH` | Principal's assigned permissions (pair with `valueReferenceType=CUSTOM_PERMISSION`) |
| `USER_ID` | Principal user ID |
| `ORGANIZATION_ID` | Principal org ID |
| `USER_ROLE_ID` | Principal role ID |
| `RBAC_TAGS` | Principal RBAC tags |

Outside contract (not in `RulePrincipalPathType`): `IS_INTERNAL`, `CONTACT_ID`, `SCALAR_ATTRIBUTE`, `PLURAL_ATTRIBUTE`, `PLACEHOLDER`. Use a runtime RuleProvider for these.

### `<resourcePath>` / `<valueResourcePath>` — `RuleResourcePathType` (16 values)

| Value | Meaning |
|-------|---------|
| `NAMESPACE` | Resource namespace |
| `ENTITY` | Entity (object) reference |
| `FIELD` | Field reference |
| `ENTITYTYPE` | Entity type — pair with `IS` operator and `{"t":"Text","v":"FIELD"}` literal |
| `ENTITYKIND` | Entity kind bits |
| `FIELDKIND` | Field kind bits |
| `DATASPACE` | Resource dataspace |
| `TAG` | Custom or standard tag |
| `OBJECT_TAG` | Object-level tag |
| `CLASSIFICATION` | Custom or standard classification |
| `IMPLICITTAG` | Implicit tag |
| `RECORDFIELD` | Field of the record being evaluated (RLS) — pair with `<valueDomain>Schema:field</valueDomain>` |
| `OBJECT_CLASSIFICATION` | Object-level classification |
| `EXPRESSION` | Compound expression — pair with `<resourceExpression>` PROJECTION |
| `OBJECT_DATASPACE` | Object-level dataspace |
| `RECORDFIELDTYPE` | Type of a record field |

### `<contextPath>` / `<valueContextPath>` — `RuleContextPathType` (1 value)

| Value | Use case |
|-------|----------|
| `SESSION_DATASPACE` | Session-scoped dataspace check |

Outside contract: `SESSION_CONSUMER_ID`, `CONTEXT_AGENT_ID`, `CONTEXT_AGENT_VERSION_ID` (IDENTIFIED_RECORD / agentic — runtime RuleProvider only).

> `SCALAR_ATTRIBUTE` / `PLURAL_ATTRIBUTE` in `<valuePrincipalPath>` are outside `RulePrincipalPathType` — not authorable via MDAPI for new work.

---

## `<operator>` — `RuleDefinitionOperatorType`

| Operator | Use with |
|----------|----------|
| `EQUALS` / `NOT_EQUALS` | Scalar equality |
| `GREATER_THAN`, `LESS_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN_OR_EQUALS` | Numeric / date |
| `IN` | Scalar IN set |
| `LIKE` | String pattern |
| `CONTAINS_ANY` | Set has at least one of |
| `CONTAINS_ALL` | Set has all of |
| `CONTAINS_NONE` | Set has none of |
| `IS` | Type / kind check (pair with `ENTITYTYPE` + `{"t":"Text","v":"FIELD"}` literal) |
| `EXISTS` | RLS join exists (pair with `resourcePath=EXPRESSION` + PROJECTION) |
| `HIERARCHICALLY_ABOVE` / `HIERARCHICALLY_BELOW` | Hierarchy traversal — pair with `valueReferenceType=HIERARCHY` |

---

## `<conditions>` — Full Schema

| Element | Notes |
|---------|-------|
| `<clause>` | `WHEN` or `UNLESS` — match the wrapper |
| `<operator>` | Always required |
| `<resourcePath>` | What about the resource to inspect |
| `<principalPath>` | What about the principal to inspect |
| `<contextPath>` | Context attribute (SESSION_DATASPACE only) |
| `<valueDomain>` | `Schema:field` — for RECORDFIELD comparisons |
| `<resourceAlias>` | Used in PROJECTION join expressions |
| `<valueBit>` | Entity/field-kind bits |
| `<valuePrincipalPath>` | Path the value comes from |
| `<valueResourcePath>` | Path the value comes from |
| `<valueContextPath>` | Path the value comes from |
| `<policyRuleValueSet>` | Literal or named-reference values (see below) |
| `<resourceExpression>` | `PolicyJsonExpression` type=PROJECTION (RLS join) |
| `<principalExpression>` | `PolicyJsonExpression` type=SOQLTARGETLISTEXPR (SOQL principal) |
| `<whereClauseConjunction>` | Sub-expression for nested conditions |
| `<policyRuleDefinitionCondition>` | Nested children — used with `whereClauseConjunction` |

---

## `<policyRuleValueSet>`

Three fields (all optional at schema level, but a non-empty value set needs at least one):

### Literal values — `<valueString>`

For typed literals, embed JSON (escape `"` to `&quot;`):
```xml
<valueString>{&quot;t&quot;:&quot;Text&quot;,&quot;v&quot;:&quot;FIELD&quot;}</valueString>
<valueString>{&quot;t&quot;:&quot;Boolean&quot;,&quot;v&quot;:true}</valueString>
<valueString>{&quot;t&quot;:&quot;Number&quot;,&quot;v&quot;:42}</valueString>
```

For plain string equality:
```xml
<valueString>Toxico</valueString>
```

### Named references — `<valueReference>` + `<valueReferenceType>`

| `valueReferenceType` | Refers to | Typical path pairing |
|----------------------|-----------|----------------------|
| `CUSTOM_TAG` | Custom tag by devName | `resourcePath=TAG` |
| `STANDARD_TAG` | Standard tag — **fully qualified** (e.g. `DataGovernanceTags.ExternalData.Visibility.Public`) | `resourcePath=TAG` |
| `CUSTOM_CLASSIFICATION` | Custom classification | `resourcePath=CLASSIFICATION` |
| `STANDARD_CLASSIFICATION` | Standard classification — **fully qualified** (e.g. `DataGovernanceClassifications.DataCategorization.FieldUsage.Active`) | `resourcePath=CLASSIFICATION` |
| `HIERARCHY` | Hierarchy definition | `operator=HIERARCHICALLY_BELOW/ABOVE`, `resourcePath=RECORDFIELD` |
| `CUSTOM_PERMISSION` | Custom permission | `principalPath=ASSIGNED_PERMISSIONS_PATH` |
| `DATASPACE` | Dataspace | `resourcePath=DATASPACE` or `contextPath=SESSION_DATASPACE` |

> **Tag/classification dev names are NOT free-form.** The deploy-time validator checks `<valueReference>` against the org's taxonomy. To find the exact string: `sf project retrieve start --target-org <alias> --metadata "PolicyRuleDefinition:<existing-rule-name>"` and copy `<valueReference>` verbatim.

Multiple `<policyRuleValueSet>` siblings inside one condition are OR-combined.

---

## JSON Expressions (min API 66.0)

`<type>` must match the location:

| Location | Required `type` |
|----------|-----------------|
| Top-level `<resourceExpression>` (TRANSFORM rule arg list) | `ARGLIST` |
| `<conditions>` `<resourceExpression>` (RLS join) | `PROJECTION` |
| `<conditions>` `<principalExpression>` (SOQL principal) | `SOQLTARGETLISTEXPR` |

### ARGLIST — Transform argument list

```xml
<resourceExpression>
    <type>ARGLIST</type>
    <version>1</version>
    <transformExpression>
        <argument>
            <type>NUMBER</type>
            <value>4</value>
        </argument>
    </transformExpression>
</resourceExpression>
```

`TransformExpressionArgumentType` = `STRING` or `NUMBER`. Use when `<resourceTransform>` takes parameters (e.g. `LAST_N_CHARS_RESOURCE_TRANSFORM` needs N).

### PROJECTION — RLS join

Used inside `<conditions>` with `resourcePath=EXPRESSION` and `operator=EXISTS`:

```xml
<resourceExpression>
    <type>PROJECTION</type>
    <version>1</version>
    <projection>
        <join>
            <schema>testDMO__dlm</schema>
            <alias>test 1</alias>
            <predicate>
                <comparator>EQUALS</comparator>
                <attribute>testDMO__dlm:name__c</attribute>
                <on>
                    <resourceAlias>resource</resourceAlias>
                    <schema>testDMO__dlm</schema>
                    <field>age__c</field>
                </on>
            </predicate>
        </join>
    </projection>
</resourceExpression>
```

### SOQLTARGETLISTEXPR — Principal SOQL target

Scalar:
```xml
<principalExpression>
    <type>SOQLTARGETLISTEXPR</type>
    <version>1</version>
    <soqlTarget>
        <select>age__c</select>
    </soqlTarget>
</principalExpression>
```

Plural (use a set operator: `CONTAINS_ANY` / `CONTAINS_NONE` / `CONTAINS_ALL`):
```xml
<principalExpression>
    <type>SOQLTARGETLISTEXPR</type>
    <version>1</version>
    <soqlTarget>
        <plural>true</plural>
        <relationship>pluralAttributes__r</relationship>
        <select>name__c</select>
    </soqlTarget>
</principalExpression>
```

> `SCALAR_ATTRIBUTE` / `PLURAL_ATTRIBUTE` principal expressions are outside MDAPI contract. Fixture-only.

---

## `<resourceTransform>` Enum (TRANSFORM rules only)

| Value | Effect |
|-------|--------|
| `NULL_RESOURCE_TRANSFORM` | Replace with NULL |
| `EMPTY_STRING_RESOURCE_TRANSFORM` | Replace with `""` |
| `LAST_N_CHARS_RESOURCE_TRANSFORM` | Keep last N chars (N via ARGLIST) |
| `FIRST_N_CHARS_RESOURCE_TRANSFORM` | Keep first N chars (N via ARGLIST) |
| `ALL_BUT_LAST_N_CHARS_RESOURCE_TRANSFORM` | Mask last N |
| `ALL_BUT_FIRST_N_CHARS_RESOURCE_TRANSFORM` | Mask first N |
| `CLOSEST_ORDER_OF_MAGNITUDE_RESOURCE_TRANSFORM` | Round to nearest power of 10 |
| `TRUNCATE_DATE_RESOURCE_TRANSFORM` | Truncate date precision |
| `ROUND_RESOURCE_TRANSFORM` | Round number |
| `REPLACE_ALL_CHARS_RESOURCE_TRANSFORM` | Replace each char |

Pure transforms (NULL, EMPTY_STRING) need no `<resourceExpression>`. Parameterized transforms (FIRST_N, LAST_N, ROUND, REPLACE_ALL_CHARS, TRUNCATE_DATE) take args via ARGLIST.
