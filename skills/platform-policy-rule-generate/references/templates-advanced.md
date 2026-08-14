# Advanced Templates — Multi-Condition, Hierarchy, Unauthorable

Each template is a verified shape from a passing test fixture. Copy, then change names/values.

---

## Multi-Condition with Custom Conjunction (AND/OR mix)

Source: `conjunctionExpressionSteelthread`

```xml
<unlessPolicyRuleDefinitionClauseConjunction>
    <conditions>
        <clause>UNLESS</clause>
        <operator>CONTAINS_ANY</operator>
        <resourcePath>TAG</resourcePath>
    </conditions>
    <conditions>
        <clause>UNLESS</clause>
        <operator>CONTAINS_NONE</operator>
        <resourcePath>TAG</resourcePath>
    </conditions>
    <conjunctionExpression>(AND 1 2)</conjunctionExpression>
</unlessPolicyRuleDefinitionClauseConjunction>
```

> Note: `<unlessPolicyRuleDefinitionClauseConjunction>` blocks are **not UI-editable** — silently dropped on first save. Prefer WHEN + negated operator for UI-compatible policies.

---

## Hierarchy Traversal

Source: `conditionWithHierarchy`

```xml
<conditions>
    <clause>WHEN</clause>
    <operator>HIERARCHICALLY_BELOW</operator>
    <resourcePath>RECORDFIELD</resourcePath>
    <valueDomain>testDMO__dlm:name__c</valueDomain>
    <policyRuleValueSet>
        <valueReference>testHierarchyRLS</valueReference>
        <valueReferenceType>HIERARCHY</valueReferenceType>
    </policyRuleValueSet>
</conditions>
```

> Not UI-editable (`HIERARCHICALLY_BELOW` and `valueReferenceType=HIERARCHY` are not in the UI dropdowns).

---

## IDENTIFIED_RECORD — Not Authorable via MDAPI

`IDENTIFIED_RECORD` policies cannot be authored as XML. The required `RuleContextPath.SESSION_CONSUMER_ID` is not in `RuleContextPathType`.

To author one: implement it as a runtime `RuleProvider` in the consuming service, not via MDAPI XML.

**Do not** synthesize a placeholder XML using `<contextPath>SESSION_CONSUMER_ID</contextPath>` — the value is not in `RuleContextPathType` and the deploy will fail.
