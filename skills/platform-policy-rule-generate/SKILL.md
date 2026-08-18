---
name: platform-policy-rule-generate
description: "Use this skill when authoring PolicyRuleDefinition and PolicyRuleDefinitionSet metadata XML for Salesforce Data Cloud governance policies, or when editing *.policyRuleDefinition / *.policyRuleDefinitionSet files. Covers the category decision tree, full schema for all policy variants (ACCESS, GOVERNANCE, RECORD, TRANSFORM), UI-compatibility rules for the Data Governance Policy Builder, output hygiene for user-facing agent responses, and validation guardrails. Do NOT use this skill for UserAccessPolicy, AccessPolicy, SharingRules, PermissionSet, or any other access-control metadata type — those have their own types and live outside the PolicyRuleDefinition schema."
metadata:
  version: "1.0"
  domains: ["Platform", "Data 360"]
  minApiVersion: "64.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Authoring Policy Rule Definitions

**Gating:** requires the `EnforceOMatic` and `PolicyRuleMDAPI` org permissions. 
**Min API version:** 64.0 (66.0 for conditions using `PolicyJsonExpression`).

This skill covers the **on-disk metadata XML format** for authoring policies. Use it whenever a task asks to write a `*.policyRuleDefinition` or `*.policyRuleDefinitionSet` file, or ship a metadata package containing them. The runtime side (RuleProvider, hooks) is out of scope.

---

> **Eval coverage:** This skill is exercised by the team's ADK eval framework, not by `tests/evals/` under the skill directory. Five datasets covering the ACCESS / GOVERNANCE / RECORD / TRANSFORM variants live in `packages/adk-eval/eval/domains/platform-policy-rule-generate/datasets/`.

## 1. Package Layout

A deployable package always contains:

```text
<fixture>/
  package.xml
  policyRuleDefinitionSets/<setName>.policyRuleDefinitionSet
  policyRuleDefinitions/<ruleName>.policyRuleDefinition
```

`package.xml` template (use `<version>[ftest]</version>` for ftests, `64.0` or higher for real orgs):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Rule0</members>
        <name>PolicyRuleDefinition</name>
    </types>
    <types>
        <members>Set1</members>
        <name>PolicyRuleDefinitionSet</name>
    </types>
    <version>64.0</version>
</Package>
```

---

## 2. PolicyRuleDefinitionSet Schema

```xml
<PolicyRuleDefinitionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Set1</label>
    <description>Optional free text</description>
    <replicated>false</replicated>             <!-- MinAppVersion 260 -->
    <builderCompatible>true</builderCompatible> <!-- MinAppVersion 262, author-settable -->
    <!-- builderValidated: server-managed — do not set in authored XML -->
</PolicyRuleDefinitionSet>
```

| Element | Req | Notes |
|---------|-----|-------|
| `<label>` | yes | Master label. File basename (devName) is the MDAPI identifier, not the label. |
| `<description>` | no | Free text. |
| `<replicated>` | no | `true` triggers placeholder transformation across companion orgs. Omit for null/false. |
| `<builderCompatible>` | no | `true` = rules audited per §7 checklist. `false` = API-only. Omit = unaudited. Informational only — no deploy/runtime effect. |
| `<builderValidated>` | no | **Server-managed. Never set in authored XML.** Server overwrites on validation. |

---

## 3. PolicyRuleDefinition — Core Fields

| Element | Req | Notes |
|---------|-----|-------|
| `<label>` | yes | MasterLabel. |
| `<category>` | yes | See §4. Drives `resourceScopeType` and whether `policyRuleResourceDomains`/`resourceTransform` are required. **Does NOT constrain `effect` outside of TRANSFORM.** |
| `<effect>` | yes | `Permit`, `Forbid`, or `Transform`. The only category-coupling enforced by core: `effect=Transform ↔ category=TRANSFORM_POLICY_RULE_DEFINITION` (bidirectional). All other categories accept Permit and Forbid freely. |
| `<action>` | yes (≥1) | `Read`, `TupleRead`, `Create`, etc. Multiple elements OR-combine. |
| `<policyRuleDefinitionSetName>` | yes | Developer name of parent set. |
| `<principalScopeType>` | yes | Always `ANY`. |
| `<resourceScopeType>` | yes | `ANY`, `FIELD`, `RECORD`, `DATASPACE`, or `SPAN`. Must match category (§4). |
| `<principalAuthenticationLevel>` | no | `INTERNAL`, `AUTHENTICATED`, `UNIDENTIFIED`, `IDENTIFIED`. |
| `<ruleConsumer>` | no | `ALL`, `DATACLOUD`, `MULESOFT`, `TABLEAU`, `CORE`. |
| `<policyRuleResourceDomains>` | no | Required for RECORD (RLS) and FIELD-scope TRANSFORM rules only. Forbidden on ACCESS/GOVERNANCE. |
| `<resourceTransform>` | no | Required (and only valid) when `category=TRANSFORM`. |
| `<whenPolicyRuleDefinitionClauseConjunction>` | no | WHEN conditions. |
| `<unlessPolicyRuleDefinitionClauseConjunction>` | no | UNLESS conditions. Not UI-editable — prefer WHEN + negated operator. |

---

## 4. Category Decision Tree

**Category names a domain (where in the platform's enforcement layers the rule applies). Effect names the action (allow / deny / transform). They are independent except for TRANSFORM.**

The **only** Category × Effect rule the platform validates:

- `effect=Transform` ⇔ `category=TRANSFORM_POLICY_RULE_DEFINITION` (bidirectional; mismatched throws `INVALIDFORCATEGORY`).
- All other categories (`ACCESS`, `GOVERNANCE`, `RECORD`, `IDENTIFIED_RECORD`) accept either `Permit` or `Forbid`.

> **Note on the platform's auto-fill default:** When `<category>` is omitted from authored XML, the server fills it in from `effect`: `Permit→ACCESS`, `Forbid→GOVERNANCE`, `Transform→TRANSFORM`. **This is a default-fill, not a validation.** If you author an explicit category that contradicts this default, it is accepted and persisted as-is.

### Picking the category

```text
What kind of policy?
│
├── OLS/FLS allow/deny on tagged or classified resources
│     category = ACCESS_POLICY_RULE_DEFINITION (allow/deny attestation in the access plane)
│              | GOVERNANCE_POLICY_RULE_DEFINITION (governance-audited)
│     effect = Permit | Forbid (chosen independently from category)
│     resourceScopeType = ANY | FIELD | DATASPACE
│     NO <policyRuleResourceDomains>
│     condition: resourcePath=TAG|CLASSIFICATION CONTAINS_ANY <ref>
│     For "objects AND all their fields" → action=TupleRead + OR-of-ENTITYTYPE clause (§7)
│     Note: "Block access to Foo object" → tag Foo with <yourTag>, write rule on tag
│        Do NOT use <resourceDomain>Foo</resourceDomain> — forbidden for ACCESS/GOVERNANCE
│
├── Row-level filter on a DMO/DLO
│     category = RECORD_POLICY_RULE_DEFINITION
│     effect = Permit | Forbid
│     resourceScopeType = RECORD
│     <policyRuleResourceDomains> = the DMO/DLO API name  ← entity targeting allowed here
│
├── Identified-Guest record access
│     NOT authorable via MDAPI — SESSION_CONSUMER_ID is not in RuleContextPathType
│        Must be implemented as a runtime RuleProvider.
│
└── Field masking
      category = TRANSFORM_POLICY_RULE_DEFINITION   ← required by RuleBuilder validator
      effect = Transform                            ← required by RuleBuilder validator
      resourceScopeType = FIELD (structured) or SPAN (unstructured)
      <policyRuleResourceDomains> = the DMO whose field is masked
      <resourceTransform> required (e.g. NULL_RESOURCE_TRANSFORM, LAST_N_CHARS_RESOURCE_TRANSFORM)
```

### ACCESS vs GOVERNANCE — how to choose

Both legally accept Permit and Forbid. Pick by *which enforcement layer should record/audit the rule* and **what the prompt literally asks for**:

| Use case | Pick | Reason |
|---|---|---|
| The prompt names "ACCESS policy rule" / "access rule" / "OLS/FLS" explicitly | `ACCESS_POLICY_RULE_DEFINITION` | Matches the prompt's vocabulary; sits in the data-access enforcement layer. |
| The prompt names "governance" / "audit" / "policy framework" / data-residency or compliance language | `GOVERNANCE_POLICY_RULE_DEFINITION` | Matches the prompt's vocabulary; rules surface in governance reporting. |
| Prompt is ambiguous and only describes allow/deny semantics | Default to `ACCESS` for Permit, `GOVERNANCE` for Forbid (mirrors the platform's auto-fill default; safe and deployable, but **not required**) |

> **Important — honor the explicit category in the prompt.** If the prompt says "ACCESS policy rule that denies …" or "GOVERNANCE policy rule that permits …", emit exactly that category. Do not silently swap to the auto-fill default just because effect is Forbid (or Permit). The platform accepts both. The agent must not override the user's stated intent.

**Scope × category compatibility** — any combination outside this matrix throws `INVALIDFORCATEGORY`:

|            | `ACCESS` | `GOVERNANCE` | `TRANSFORM` | `RECORD` |
|------------|:--------:|:------------:|:-----------:|:--------:|
| `ANY`      | Yes | Yes | No  | No  |
| `DATASPACE`| Yes | Yes | No  | No  |
| `FIELD`    | Yes | Yes | Yes | No  |
| `RECORD`   | No  | No  | No  | Yes |
| `SPAN`     | No  | No  | Yes | No  |

---

## 5. Condition Patterns (Quick Reference)

Every `<conditions>` block needs **all four**: `<clause>`, `<operator>`, one path element, and the value.

| Goal | path element | operator | value |
|------|-------------|----------|-------|
| Resource has tag | `<resourcePath>TAG</resourcePath>` | `CONTAINS_ANY` | `<valueReferenceType>CUSTOM_TAG` \| `STANDARD_TAG</valueReferenceType>` |
| Resource has classification | `<resourcePath>CLASSIFICATION</resourcePath>` | `CONTAINS_ANY` | `CUSTOM_CLASSIFICATION` \| `STANDARD_CLASSIFICATION` |
| Principal has permission | `<principalPath>ASSIGNED_PERMISSIONS_PATH</principalPath>` | `CONTAINS_ANY` \| `CONTAINS_NONE` | `<valueReferenceType>CUSTOM_PERMISSION</valueReferenceType>` |
| Session in dataspace | `<contextPath>SESSION_DATASPACE</contextPath>` | `CONTAINS_ANY` | `<valueReferenceType>DATASPACE</valueReferenceType>` |
| Record field = user attribute | `<resourcePath>RECORDFIELD</resourcePath>` + `<valueDomain>Schema:field</valueDomain>` | `EQUALS` | `<valuePrincipalPath>USER_ID` \| `ORGANIZATION_ID` \| `USER_ROLE_ID</valuePrincipalPath>` |
| Entity type check | `<resourcePath>ENTITYTYPE</resourcePath>` | `IS` | `<valueString>{"t":"Text","v":"FIELD"}</valueString>` |

`<conjunctionExpression>` is 1-indexed prefix notation: `1`, `(AND 1 2)`, `(OR 1 2)`, `(AND (OR 1 2) (AND 3))`. A bare top-level index like `1` is valid for **deploy** but **crashes the Data Governance Policy Builder UI** — see §7 if UI editability matters.

For full path enums (`RulePrincipalPathType`, `RuleResourcePathType`, `RuleContextPathType`), operators, and JSON expressions (PROJECTION / ARGLIST / SOQLTARGETLISTEXPR), see [`references/policy-schema-full.md`](references/policy-schema-full.md). 
For copy-paste templates for all policy variants, see [`references/templates.md`](references/templates.md).

---

## 6. Validation Guardrails

1. Every `<conditions>` needs an `<operator>`. Missing operator → reject.
2. Every `<conditions>` needs at least one path element (`<resourcePath>`, `<principalPath>`, `<contextPath>`, or `<valueDomain>`).
3. `<contextPath>` is exclusively `SESSION_DATASPACE`. Never put a resource path value there.
4. Scope × category must be in the §4 matrix. Common offenders: ACCESS/GOVERNANCE + RECORD scope; RECORD + ANY/FIELD scope; TRANSFORM + ANY/RECORD scope. (Effect is independent of category except for TRANSFORM — see §4.)
5. `<resourceTransform>` and `effect=Transform` are coupled. Transform effect needs a resourceTransform. Permit/Forbid must not have one.
6. `<policyRuleResourceDomains>` is **required** for RECORD (RLS) and FIELD-scope TRANSFORM; **forbidden** on ACCESS/GOVERNANCE.
7. `<conjunctionExpression>` indices must match actual `<conditions>` count. Off-by-one → reject.
8. `<clause>` inside `<conditions>` must match the wrapper (`WHEN` inside `<when…>`, `UNLESS` inside `<unless…>`).
9. JSON literals in `<valueString>` must escape `"` to `&quot;`. Wrong escaping silently corrupts the literal.
10. Reference targets (`<valueReference>`, `<resourceDomain>`) must exist in the target org at deploy time.
11. `SCALAR_ATTRIBUTE` / `PLURAL_ATTRIBUTE` are not in `RulePrincipalPathType` — not in MDAPI contract. Use a runtime RuleProvider for those shapes.
12. `IDENTIFIED_RECORD` is not authorable via MDAPI — `SESSION_CONSUMER_ID` not in `RuleContextPathType`.
13. Standard tag/classification dev names are fully-qualified dotted paths (e.g. `DataGovernanceTags.ExternalData.Visibility.Public`). Retrieve an existing rule to get the exact string before authoring.
14. Min API versions: `PolicyRuleDefinition` = 64.0; `PolicyJsonExpression` conditions = 66.0; `<replicated>` = 260+; `<builderCompatible>` / `<builderValidated>` = 262+.

> **Note on `<conjunctionExpression>` shape:** A bare top-level index (e.g. `<conjunctionExpression>1</conjunctionExpression>`) deploys cleanly — the server-side parser accepts bare tokens at the top level. It is **not** a deploy-time validation error. It does, however, crash the Data Governance Policy Builder UI on load — see §7.

---

## 7. UI Compatibility — Core Rules

The Data Governance Policy Builder edits a **strict subset** of the MDAPI. Default goal: produce UI-compatible policies. Always confirm with the operator before producing API-only XML.

**Hard blockers** — any of these make the policy uneditable (and several crash the builder on load):

- **Missing OR-of-ENTITYTYPE clause on ACCESS/GOVERNANCE rules** → hard crash: `Cannot use 'in' operator to search for 'Permit' in undefined`. Required even when paired with `TupleRead` (where it's functionally redundant at runtime). Must include `IS` conditions for `{"t":"Text","v":"OBJECT"}` and `{"t":"Text","v":"FIELD"}`.
- **Bare top-level condition index** in `<conjunctionExpression>` (e.g. `1`, or `(AND (OR 1 2) 3)`) → crash on builder load in `buildCriteria`. Deploy is unaffected, but the policy is uneditable in the UI. Always wrap: `(AND 1)` for a single condition; `(AND (OR 1 2) (AND 3))` instead of `(AND (OR 1 2) 3)`.
- `category = ACCESS_POLICY_RULE_DEFINITION` + `effect = Forbid` → the **Data Governance Policy Builder UI** (not MDAPI) collapses it to GOVERNANCE on save; round-trip via the builder will rewrite the category. MDAPI deploy is unaffected — the original ACCESS+Forbid combination is valid and deploys without modification. If your goal is UI round-trippability, prefer GOVERNANCE for Forbid; if the source of truth is MDAPI, ACCESS+Forbid is fine.
- Any `<unlessPolicyRuleDefinitionClauseConjunction>` block → silently dropped on first UI save.
- More than one `<action>` → only the first is kept.
- `ruleConsumer` ≠ `DATACLOUD` → UI hardcodes DATACLOUD on save.
- Top-level `(OR 1 2)` conjunction → triggers `// ERROR: Unsupported rule!` path, rule silently dropped.

**UI-compatible "unless" rewrite:**

| Author intent | UI-compatible shape |
|---|---|
| `unless principal has permission X` | `WHEN ASSIGNED_PERMISSIONS_PATH CONTAINS_NONE X` |
| `unless resource has tag X` | `WHEN TAG CONTAINS_NONE X` |
| `unless record field = value` | `WHEN RECORDFIELD NOT_EQUALS value` |

For the full UI-compatibility checklist, round-trip rules, and operator support matrix, see [`references/ui-compatibility.md`](references/ui-compatibility.md).

---

## 8. Authoring Workflow

1. **Start from the closest template** in [`references/templates.md`](references/templates.md) — modify from there, don't start blank.
2. **Pick category first** (§4). Category fixes effect, resourceScopeType, and whether policyRuleResourceDomains/resourceTransform are required.
3. **Lay out the bare rule**: top-level fields only, no conditions. Match the category template in [`references/templates.md`](references/templates.md).
4. **Add conditions one at a time**, each with all four anchors: `<clause>`, `<operator>`, one path element, and the value.
5. **Update `<conjunctionExpression>`** — 1-indexed prefix notation. Bare top-level index (e.g. `1`) deploys but breaks the UI; wrap as `(AND 1)` if UI editability matters (§7).
6. **Run the UI-compatibility check** (§7 / [`references/ui-compatibility.md`](references/ui-compatibility.md)). If any item trips, attempt the "unless" rewrite first; if not possible, get explicit operator confirmation before continuing.
7. **Update `package.xml`** — list each `<members>` for both types.
8. **Set `<builderCompatible>`** on the set to `true` if §7 checklist passes; `false` if intentionally API-only.
9. **Sanity-check against §6 (guardrails)** before considering done.
10. **Validate with dry-run** before any non-dry deploy to a persistent org. Surface errors using the error reference in [`references/deploy-errors.md`](references/deploy-errors.md).

**Three-layer correctness check** before done:
- **Runtime enforcement** — does the rule enforce what's intended? (action choice, condition shape)
- **MDAPI deploy validity** — does it deploy? (§6 guardrails, scope×category, tag dev names, org perms)
- **UI editability** — can the builder render and re-save it? (§7 checklist, OR-of-ENTITYTYPE requirement)

---

## 9. Output Hygiene — What the Agent Must NOT Say to the User

The agent's user-facing chat response accompanies every generated file. Customers should never see internal engine or implementation details.

- **Do NOT name the internal evaluation engine** in user-facing text — including but not limited to `Cedar`, `policy engine`, `AuthZ engine`, `evaluation engine`, `Rego`, `OPA`, or similar. The customer-facing surface is *Data Governance*, *Policy Builder*, *Data Cloud Governance* — use those terms only.
- **Do NOT emit trailing "How it works at runtime" narratives** that describe evaluation flow, principal-resource matching semantics, or engine-internal condition ordering. The generated file is the artifact; a one-line summary of what deployed is enough. If the user explicitly asks how enforcement works, describe it in product terms (e.g. "Data Governance denies the read when …"), never in engine terms.
- **Do NOT name internal packages, source directories, Java class names, method names, or line-number references** in user-facing text. Internal implementation identifiers are not customer-facing; refer to platform behavior in product terms only ("the server validates …", "Data Governance rejects …").
- **Do NOT explain auto-fill / default-fill / fallback semantics** unless the user asks. Ship the rule; surface constraints only when they affect what the user has to do next (e.g. "the DMO tag must exist before deploy").

If the user needs more context, they'll ask — respond then, in product language.

---

## Reference Docs

| Detail | File |
|--------|------|
| Full path enums, operators, value sets, JSON expressions (PROJECTION / ARGLIST / SOQLTARGETLISTEXPR) | [`references/policy-schema-full.md`](references/policy-schema-full.md) |
| Copy-paste templates — index at [`references/templates.md`](references/templates.md); per-variant: [`templates-access.md`](references/templates-access.md), [`templates-record.md`](references/templates-record.md), [`templates-transform.md`](references/templates-transform.md), [`templates-advanced.md`](references/templates-advanced.md) |
| Full UI-compatibility checklist, round-trip rules, operator/path support matrix | [`references/ui-compatibility.md`](references/ui-compatibility.md) |
