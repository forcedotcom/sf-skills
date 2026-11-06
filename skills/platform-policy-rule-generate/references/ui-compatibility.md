# UI Compatibility — Data Governance Policy Builder

The Data Governance Policy Builder edits a **strict subset** of the MDAPI. Anything outside that subset must be maintained through the MDAPI package path for the policy's lifetime — admins cannot open it in the builder without silent data loss or a hard crash.

> **Default goal**: produce policies that can eventually be validated in Policy Builder. Author `<builderCompatible>true</builderCompatible>` on the set by default; omit it (or author `false`) only when the user explicitly asks for a policy that is not builder-compatible. `<builderValidated>` is server-managed — never author it. Authoring `builderCompatible=true` declares intent; only an actual Policy Builder open/save/retrieve comparison can establish UI compatibility for a specific shape, so keep the checklist below satisfied.

> **Evidence boundary:** MDAPI dry-run, deploy, and retrieve prove metadata validity and persistence. They do not prove that Policy Builder can open and save the policy without normalization or loss. A retrieved set's `<builderCompatible>` and `<builderValidated>` values are persisted-shape evidence only.

> **ACCESS distinction:** An OR-of-ENTITYTYPE discriminator prevents the builder crash for object-level ACCESS-shaped rules, but ACCESS categories still do not round-trip as ACCESS; the builder rewrites them to GOVERNANCE. Treat explicitly requested ACCESS output as API-only and record that status in the description or an XML comment and author `<builderCompatible>false</builderCompatible>` on the parent set (the policy is not authored with builder-renderable intent).

---

## What the UI Can Render

**Categories** : `GOVERNANCE_POLICY_RULE_DEFINITION`, `RECORD_POLICY_RULE_DEFINITION`, `TRANSFORM_POLICY_RULE_DEFINITION` 
**Categories NOT handled** : `ACCESS_POLICY_RULE_DEFINITION` (UI forces to GOVERNANCE on save), `IDENTIFIED_RECORD_POLICY_RULE_DEFINITION`

**Effects** : `Permit`, `Forbid` (UI label "Deny"), `Transform`

**Actions** : `Read`, `TupleRead` — two real choices for OLS/FLS rules.
- `Read`: evaluates conditions against the resource itself
- `TupleRead`: cascade rewriter — expands object-level condition to also cover `resource.object.*` for fields. Use when the intent is "objects matching X AND all their fields"
- Multiple `<action>` entries: only the first is kept on save

**`<ruleConsumer>`** : only `DATACLOUD` (hardcoded on save) 
**`<principalScopeType>`** : only `ANY` (hardcoded on save) 
**`<resourceScopeType>`** : `ANY`, `RECORD`, `FIELD`, `DATASPACE`, `SPAN` 
**`<principalAuthenticationLevel>`** : `INTERNAL`, `AUTHENTICATED`, `UNIDENTIFIED`. `IDENTIFIED` not exposed. 
**`<replicated>`** : read but NOT editable. Once `true`, UI forces read-only mode. 
**`<transformPrecedence>`** : not exposed; non-zero values dropped.

---

## Conditions — Supported Shapes

**Top-level conjunction**: only `<whenPolicyRuleDefinitionClauseConjunction>`. The UI forces `<unlessPolicyRuleDefinitionClauseConjunction>` to `null` on save.

**Conjunction expression**: the UI builds one top-level `(AND …)` from typed sections dispatched by path type. Conditions are not combined as one undifferentiated list. Put all conditions for the same UI section into that section's local group, then combine the non-empty section groups under the top-level `AND`. A pure flat `(OR 1 2)` at the top level triggers `// ERROR: Unsupported rule!` — rule silently dropped. `OR` only round-trips inside a single section's group.

**Path types per UI section:**

| UI Section | Recognized path |
|------------|-----------------|
| Users (Permission) | `principalPath = ASSIGNED_PERMISSIONS_PATH` |
| Resource entity-type | `resourcePath = ENTITYTYPE` with `IS` operator |
| Data space | `resourcePath = DATASPACE` or `contextPath = SESSION_DATASPACE` |
| Tag / Classification | `resourcePath = TAG` or `CLASSIFICATION` |
| RLS rule criteria | `resourcePath = RECORDFIELD` or `EXPRESSION` |

Any other path type → condition silently ignored when UI rebuilds the rule.

**Required grouping examples**:

- Two classifications that are alternatives belong in one Tag / Classification group: `(OR 1 2)`.
- A permission condition belongs in the Users / Permission group: `(AND 3)`.
- The complete policy expression combines those section groups: `(AND (OR 1 2) (AND 3))`.
- If the policy also has object/field entity discriminators, add a separate Entity Type group, for example `(AND (OR 1 2) (AND 3) (OR 4 5))`.
- A record-field or join condition belongs in the RLS rule criteria group; it must not be placed directly beside a classification condition at the top level.

The exact condition numbers depend on final document order. The invariant is section-local grouping followed by a top-level `AND`, not the example numbers.

**Operators per path**:
- Tag/Classification: `CONTAINS_ANY`, `CONTAINS_NONE`. (`CONTAINS_ALL` exists in schema but not offered in dropdowns)
- Permission: `CONTAINS_ANY` (Permit) / `CONTAINS_NONE` (Forbid/Transform)
- RLS `RECORDFIELD`: `EQUALS`, `NOT_EQUALS`, `LIKE`, `LESS_THAN(_OR_EQUALS)`, `GREATER_THAN(_OR_EQUAL)`, `HIERARCHICALLY_ABOVE` (DLO/DMO only). **Not editable**: `HIERARCHICALLY_BELOW`, `IN`, `CONTAINS_ALL`
- RLS join (`EXPRESSION`): `EXISTS` only

**`<policyRuleValueSet>` reference types** : `CUSTOM_TAG`, `STANDARD_TAG`, `CUSTOM_CLASSIFICATION`, `STANDARD_CLASSIFICATION`, `CUSTOM_PERMISSION`. **Not editable**: `HIERARCHY`, `DATASPACE`.

---

## Implicit Defaults Injected by the UI on Save

When the UI saves, it auto-injects these — if your hand-authored XML omits them or uses different values, the first UI save rewrites them:

| Field | UI default |
|-------|-----------|
| `principalAuthenticationLevel` | `INTERNAL` |
| `principalScopeType` | `ANY` |
| `ruleConsumer` | `DATACLOUD` |
| `unlessPolicyRuleDefinitionClauseConjunction` | `null` (always) |
| `actions` | only first action kept |
| `policyRuleResourceDomains` | only first `<resourceDomain>` kept |

`policyRuleResourceDomains` scopes a **RECORD (RLS)** rule to the named object; it does **not** confine a `GOVERNANCE` (OLS) rule, whose entity-type conditions match every object, and it is **not** a condition — every renderable rule still needs at least one resource `<conditions>`. To scope read access to one named object, author RLS with a row criterion — see `policy-shapes.md` shape-selection.

---

## The Non-Round-Trip Checklist

The policy will **not** round-trip through the UI without data loss or silent failure if **any** of the following is true:

- [ ] **No resource-side condition present** — zero `<conditions>`, or only principal conditions (`ASSIGNED_PERMISSIONS_PATH` / `SCALAR_ATTRIBUTE`) and no resource condition (`ENTITYTYPE` / `TAG` / `CLASSIFICATION` / `RECORDFIELD` / `EXPRESSION` / `DATASPACE`). Every renderable rule needs ≥1 resource condition; `policyRuleResourceDomains` does not count. Not deployable/renderable — see `policy-shapes.md`.
- [ ] `category` is `ACCESS_POLICY_RULE_DEFINITION` or `IDENTIFIED_RECORD_POLICY_RULE_DEFINITION`
- [ ] `ruleConsumer` ≠ `DATACLOUD`
- [ ] More than one `<action>`, or action is not `Read` / `TupleRead`
- [ ] **No top-level `resourcePath=ENTITYTYPE` discriminator group** for ACCESS/GOVERNANCE rules — this causes a **hard crash** (`Cannot use 'in' operator to search for 'Permit' in undefined`), not a graceful degradation. OLS uses an `(OR OBJECT FIELD)` group; FLS uses `FIELD` only. A `TupleRead` OLS rule without its OR group still deploys and works at runtime — the crash is UI-only.
- [ ] **Bare top-level condition index** in `<conjunctionExpression>` for a tag/classification, permission, record-field or dataspace condition (e.g. `3` instead of `(AND 3)`) — causes crash in `buildCriteria` (`param.params.map(...)` = `undefined.map()`). Only a solitary `ENTITYTYPE IS FIELD` condition (FLS/Transform) may stay bare, as in `examples/FieldReadDeny`.
- [ ] More than one `<resourceDomain>`
- [ ] An `<unlessPolicyRuleDefinitionClauseConjunction>` block present
- [ ] Any `<conditions>` uses `<clause>UNLESS</clause>`
- [ ] `<conjunctionExpression>` uses top-level `OR` (e.g. `(OR 1 2)`)
- [ ] `<principalPath>` other than `ASSIGNED_PERMISSIONS_PATH` or `SCALAR_ATTRIBUTE` (paired with a `SOQLTARGETLISTEXPR` `principalExpression`) — other values such as raw user ID may appear only inside SOQL `${User.X}` substitutions
- [ ] `<resourcePath>` other than `TAG`, `CLASSIFICATION`, `DATASPACE`, `RECORDFIELD`, `EXPRESSION`, `ENTITYTYPE`
- [ ] `<valuePrincipalPath>` is not one of `USER_ID`, `USER_ROLE_ID`, `ORGANIZATION_ID`, `SCALAR_ATTRIBUTE`, `PLURAL_ATTRIBUTE` (with `${User.X}` expression)
- [ ] `<contextPath>` other than `SESSION_DATASPACE`
- [ ] Operator is `HIERARCHICALLY_BELOW`, `IN`, or `CONTAINS_ALL`
- [ ] `<valueReferenceType>` is `HIERARCHY` or `DATASPACE`
- [ ] Entity-type conditions do not use the MDAPI-authorable `<valueText>OBJECT</valueText>` / `<valueText>FIELD</valueText>` form, or the persisted UI JSON representation is assumed to be authorable without a target-org dry-run
- [ ] `<resourceTransform>` not in the masking-category mapped set
- [ ] `<resourceExpression>` ARGLIST has multiple arguments
- [ ] `<replicated>true</replicated>` in an org with replication frozen

If none of the above is true, the policy is a candidate for UI validation. It is not proven UI-compatible until Policy Builder opens and saves it and a subsequent MDAPI retrieval shows no semantic loss.

> **Important**: The UI shows NO banner when it drops unsupported pieces on save (`// ERROR: Unsupported rule!` comment, no surfaced message). Operator-confirmation is the only line of defense.

---

## Operator-Confirmation Protocol

Whenever a request would produce a UI-incompatible policy:

1. **Try to make it UI-compatible first.** Mechanical rewrites:
 - `unless` → `when` with negated operator:
 | Intent | UI-compatible rewrite |
 |--------|----------------------|
 | `unless principal has permission X` | `WHEN ASSIGNED_PERMISSIONS_PATH CONTAINS_NONE X` |
 | `unless resource has tag X` | `WHEN TAG CONTAINS_NONE X` |
 | `unless record field = value` | `WHEN RECORDFIELD NOT_EQUALS value` |
 - Top-level `OR` between two tags → nest inside a tag/classification section group
 - Multiple `<action>` → reject the request or generate separate one-rule policy sets; one policy set in this skill contains exactly one rule

2. **If a UI-compatible rewrite is not possible**, tell the operator:
 - Which traits make it incompatible (cite items from the checklist above)
 - That the Data Governance Policy Builder will silently drop unsupported pieces on save with no warning
   - That maintenance must happen through the MDAPI package path for the policy's lifetime

3. **Wait for explicit confirmation.** Do not write the file until confirmed.

4. **On confirmation**, add an in-source marker to `<description>` (or a comment above the rule): `# API-only: not editable in Data Governance Policy Builder. Reasons: <bullets>`. Author `<builderCompatible>false</builderCompatible>` on the parent set; never author `builderValidated` (server-managed).

---

## UI-Compatibility Matrix for Templates

| Template | UI-compatible? | Notes |
|----------|----------------|-------|
| Bare permit, no conditions | Partial | Single `<action>Read</action>` only; `ruleConsumer=DATACLOUD`. UI maps ACCESS → Governance on load. |
| GOVERNANCE / RECORD / TRANSFORM tag, classification, or permission gate | Candidate; requires Policy Builder validation | `CONTAINS_ANY` / `CONTAINS_NONE` only. Tag refs must resolve in org. Explicit ACCESS-category variants are API-only because the builder rewrites ACCESS to GOVERNANCE. |
| Basic RLS (RECORDFIELD = user attribute) | UI-compatible (per DG UI source) | `SCALAR_ATTRIBUTE` is confirmed deployable; UI-compatible per DG UI source (this is how the builder itself authors the condition), not by a per-shape round-trip. |
| TupleRead with OR-of-ENTITYTYPE | Candidate; requires Policy Builder validation | Persistence-validated OLS/FLS shape. |
| IDENTIFIED_RECORD | Not MDAPI-authorable | Must be a runtime RuleProvider. |
| RLS via PROJECTION join | Requires UI validation | API 69.0 MDAPI persistence is validated for one `EXISTS`/PROJECTION shape; Policy Builder open/save is not. |
| Scalar SOQL principal | UI-compatible (per DG UI source) | `SCALAR_ATTRIBUTE`/`SOQLTARGETLISTEXPR` is confirmed deployable; UI-compatible per DG UI source (this is how the builder itself authors the condition), not by a per-shape round-trip. |
| Plural SOQL principal | Unvalidated | No retrieved and round-trip-tested example is included. |
| TRANSFORM with permission + classification | Candidate; requires Policy Builder validation | Use masking-category-mapped transforms only. |
| `(AND 1 2)` multi-condition | Candidate; requires Policy Builder validation | Each section must use a supported UI bucket. |
| Top-level `(OR 1 2)` | No | Triggers unsupported-rule path; silently dropped. |
| Hierarchy traversal | No | `HIERARCHICALLY_BELOW` and `HIERARCHY` not in UI dropdowns. Always API-only. |
