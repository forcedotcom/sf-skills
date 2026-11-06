# Policy Shapes

Choose the shape before constructing conditions. Do not mix top-level fields between shapes.

## Every renderable rule needs at least one resource condition

A DC Data Governance UI-renderable rule MUST carry **at least one resource condition** — a `<conditions>` whose left operand is resource-side (`resourcePath` = `ENTITYTYPE`, `TAG`, `CLASSIFICATION`, `RECORDFIELD`, `EXPRESSION`, or `DATASPACE`). Principal conditions (`ASSIGNED_PERMISSIONS_PATH`, `SCALAR_ATTRIBUTE`) are **optional**. A rule with **zero `<conditions>`**, or with only principal conditions and no resource condition, is **not deployable and not renderable** — do not author it.

Per shape, the mandatory resource condition is:

- **OLS** — the `(OR OBJECT FIELD)` entity-type group.
- **FLS / Masking** — the `FIELD` entity-type condition.
- **RLS** — a `RECORDFIELD` comparison or an `EXPRESSION` (`EXISTS` join) row criterion. `policyRuleResourceDomains` scopes the rule to the object but is **not** a condition and does not satisfy this requirement. "Read the whole object, no row filter" therefore has no resource condition and is **not** a renderable RLS policy — obtain a row criterion, or route object-wide read to the permission-set path (`platform-dataspace-access-configure`).

## Selecting the shape (deterministic — do not ask the user)

Route from the request signal. Only ask when there is genuinely no signal (see SKILL.md routing for the policy-vs-permission-set case) — do not turn a clear signal into a clarifying question. The single human checkpoint is the preview-and-confirm before the create/update dispatch, not a mid-flow shape question.

| Request signal | Shape |
|---|---|
| Grant or deny **read of a specific named object's data** (a DMO/DLO/CIO named or clearly implied) | **RLS** — `RECORD_POLICY_RULE_DEFINITION`, `resourceScopeType=RECORD`, `policyRuleResourceDomains` = that object, **plus a row criterion** |
| **Hide or deny a specific field** | **FLS** — `Forbid` / `Read` / `FIELD` |
| **Mask or transform a field's value** | **Masking** — `TRANSFORM_POLICY_RULE_DEFINITION` |
| Object access gated by **tag / classification across the tenant** (no single named object) | **OLS** — `TupleRead` + tag/classification conditions |

Naming a specific object is the decisive RLS signal: `policyRuleResourceDomains` scopes a RECORD rule to that object. An OLS `TupleRead` rule does **not** scope to a named object — see the OLS warning below.

| Shape | Category | Effect | Action | Scope | Required entity-type group |
|---|---|---|---|---|---|
| OLS Permit | `GOVERNANCE_POLICY_RULE_DEFINITION` | `Permit` | `TupleRead` | `ANY` | `(OR OBJECT FIELD)` |
| FLS deny | `GOVERNANCE_POLICY_RULE_DEFINITION` | `Forbid` | `Read` | `ANY` | `FIELD` only |
| Masking | `TRANSFORM_POLICY_RULE_DEFINITION` | `Transform` | `Read` | `FIELD` | `FIELD` only |
| RLS | `RECORD_POLICY_RULE_DEFINITION` | `Permit` | `Read` | `RECORD` | Exact resource DMO |

## OLS

Start with two conditions in this exact order: entity type `OBJECT`, entity type `FIELD`. Group them as `(OR 1 2)`, and always combine that group under a top-level `AND` — never leave `(OR 1 2)` bare at the top level (see `ui-compatibility.md` / `conjunction-expression.md`). Add principal and resource condition groups afterward.

> **An OLS rule applies tenant-wide unless a resource condition narrows it.** The entity-type conditions (`ENTITYTYPE IS OBJECT` / `IS FIELD`) match *every* object and field in the org — they satisfy the mandatory-resource-condition rule but are **not** a scoping mechanism. Without a `TAG` / `CLASSIFICATION` / `DATASPACE` gate, an OLS Permit is an allow-all. `policyRuleResourceDomains` does **not** confine a GOVERNANCE rule — it is a RECORD (RLS) scoping mechanism only. To grant read access scoped to one named object, use **RLS**, not OLS.

## FLS

The validated FLS example uses `Forbid`. Condition 1 is entity type `FIELD`; it has no `OBJECT` condition. Add requested principal conditions and tag/classification resource conditions after it. Construct the conjunction from the requested semantics rather than copying the example's grouping blindly. This evidence does not establish whether a Permit FLS variant is valid.

### Deny unless

Request: "block field F for everyone unless they have custom permission P" (or "only people with P can see it"). The UI-renderable shape is `Forbid` + `Read` + `FIELD`, with the exemption written as a negated principal condition in the `WHEN` conjunction. Do not emit `<unlessPolicyRuleDefinitionClauseConjunction>` or `<clause>UNLESS</clause>`: the Data Governance UI nulls it on save and cannot open the policy.

```xml
<whenPolicyRuleDefinitionClauseConjunction>
    <conditions>   <!-- 1: entity type -->
        <clause>WHEN</clause><operator>IS</operator>
        <policyRuleValueSet><valueText>FIELD</valueText></policyRuleValueSet>
        <resourcePath>ENTITYTYPE</resourcePath>
    </conditions>
    <conditions>   <!-- 2: the field's tag -->
        <clause>WHEN</clause><operator>CONTAINS_ANY</operator>
        <policyRuleValueSet>
            <valueReference>{RESOLVED_TAG}</valueReference>
            <valueReferenceType>STANDARD_TAG</valueReferenceType>
        </policyRuleValueSet>
        <resourcePath>TAG</resourcePath>
    </conditions>
    <conditions>   <!-- 3: user.permission != P -->
        <clause>WHEN</clause><operator>CONTAINS_NONE</operator>
        <policyRuleValueSet>
            <valueReference>{RESOLVED_CUSTOM_PERMISSION}</valueReference>
            <valueReferenceType>CUSTOM_PERMISSION</valueReferenceType>
        </policyRuleValueSet>
        <principalPath>ASSIGNED_PERMISSIONS_PATH</principalPath>
    </conditions>
    <conjunctionExpression>(AND 1 (AND 2) (AND 3))</conjunctionExpression>
</whenPolicyRuleDefinitionClauseConjunction>
```

Check before deploy: no `UNLESS` anywhere, the permission condition uses `CONTAINS_NONE` (not `CONTAINS_ANY`), and the permission is a resolved developer name. If the user instead asks to deny the permission *holders*, that is `CONTAINS_ANY` and a different request; ask rather than rewriting. The category is `GOVERNANCE_POLICY_RULE_DEFINITION` for this DATACLOUD FLS/OLS shape, as in `examples/FieldReadDeny/`.

## Masking

Use category `TRANSFORM_POLICY_RULE_DEFINITION`, effect `Transform`, action `Read`, and resource scope `FIELD`. Set `resourceTransform` to the requested transform. Condition 1 is entity type `FIELD`. Do not add an `OBJECT` condition.

For the retrieved `LAST_N_CHARS_RESOURCE_TRANSFORM`, add one top-level `resourceExpression`:

```xml
<resourceExpression>
    <transformExpression>
        <argument>
            <type>STRING</type>
            <value>12</value>
        </argument>
    </transformExpression>
    <type>ARGLIST</type>
    <version>1</version>
</resourceExpression>
```

The retrieved example uses one `STRING` argument even though its value is numeric text. Copy a retrieved shape for the selected transform; do not infer argument type or count.

## RLS

Use category `RECORD_POLICY_RULE_DEFINITION`, effect `Permit`, action `Read`, and resource scope `RECORD`. Add one `policyRuleResourceDomains` block containing the exact target DMO API name. These are MDAPI persistence-validated shapes; runtime row-filter behavior requires separate positive and negative data-access tests.

Every RLS rule needs **at least one resource (row) condition** — a `RECORDFIELD` comparison or an `EXISTS`/`EXPRESSION` join (see "Every renderable rule needs at least one resource condition" above). A `RECORD` rule with zero conditions is not deployable/renderable; `policyRuleResourceDomains` scopes the rule but is not a condition.

The retrieved direct-comparison evidence uses `resourcePath=RECORDFIELD`, a `valueDomain` in `DMO_API_NAME:FIELD_API_NAME` form, a version-1 `SOQLTARGETLISTEXPR`, and `valuePrincipalPath=SCALAR_ATTRIBUTE`. This is the confirmed normal-author-mode shape for a record-field-to-principal-attribute comparison; generate it directly, resolving the exact DMO, field, and principal attribute in the target org.

For an `EXISTS` join, use `resourcePath=EXPRESSION`, a version-1 `PROJECTION`, one or more nested `policyRuleDefinitionCondition` elements, and a `whereClauseConjunction` that indexes those nested conditions independently of the top-level rule conditions. Use the complete semantic `ExistsJoinRLS` example; do not invent joins or relationship direction.
