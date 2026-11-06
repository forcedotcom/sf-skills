---
name: platform-policy-rule-generate
description: "THE skill for creating a Data Cloud / Data Governance access policy — authors and deploys a PolicyRuleDefinitionSet + PolicyRuleDefinition pair (CRUD) covering OLS, FLS, RLS, masking/transform, and tag/classification-based access for the DATACLOUD or ALL consumer. TRIGGER when the user wants to create/write/author a Data Cloud or Data Governance policy, access policy, or policy rule, or to grant access to a Data Cloud object THROUGH A POLICY — a Data Cloud policy-create request routes here, not to the tag/classification surface. Resolves every reference via Data 360 MCP. SCOPE: Data Cloud policies only (not Security Center, DSAR, or User Access Policies). DO NOT TRIGGER to create tags/classifications, or to grant object/dataspace access via a PERMISSION SET / RBAC grant (use platform-dataspace-access-configure). For a vague object-access ask, surface both skills and ASK the permission-set way vs the policy way; if unsure the object is Data Cloud, ask which first."
metadata:
  relatedSkills:
    - "platform-dataspace-access-configure"
  version: "2.0"
  domains: ["Platform", "Data 360"]
  minApiVersion: "66.0"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
  mcpTools:
    data360:
      tools: ["execute", "payload_examples", "search"]
      semver: ">=1.0.0"
    headless-360:
      tools: ["discover", "describe", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
---

# Generate Policy Rule Metadata

This skill generates H360 policy metadata for the explicit `DATACLOUD` or `ALL` consumer. OLS, FLS, RLS, and Transform are shared policy shapes; `DATACLOUD` additionally requires the Data Governance Policy Builder contract. `ALL` uses the general metadata/runtime contract and does not inherit DG UI restrictions.

## When to use this skill (routing)

This is the single entry point for **creating a Data Cloud / Data Governance access policy** (a `PolicyRuleDefinitionSet` + `PolicyRuleDefinition` pair). Any request to *create / write / author a policy, an access policy, a data governance policy, a Data Cloud policy, or a policy rule* (OLS / FLS / RLS / masking / tag- or classification-based object access) **whose target is Data Cloud** routes here — **do not** hand a Data Cloud policy-create request to the Data Governance tag/classification surface; that surface owns tags and classifications, not policy authoring.

**Scope today: Data Cloud policies only.** This skill covers Data Cloud / Data Governance access policies. It does **not** yet cover core administrative policies, CMDB policies, or other non-Data-Cloud policy types (those are a planned future extension), and it is **not** the route for Security Center security policies, DSAR policies, or User Access Policies — leave those to their own core surfaces. If a policy-create request does not name Data Cloud and it is unclear whether the target object is a Data Cloud object, **ask which object first** (or whether it is Data Cloud) before routing here; core access-control surfaces (e.g. `scoped-access`) surfacing for a non-Data-Cloud request is legitimate.

Two adjacent skills, and how this one relates:

- **Data Governance tags / classifications** (create a tag, create/assign a classification, list governance tags): that is a *different* surface (`data360` Data Governance). This skill only *consumes* already-existing tags/classifications as policy references — it does not create them.
- **`platform-dataspace-access-configure`** — the **permission-set / RBAC** way to grant object or dataspace access (PermissionSet `dataspaceScopes` + the Object Access Grants Connect API). Data-space access grants go there.

**Object access can be granted two ways — infer from context, ask only when vague.** For a Data Cloud / Data Governance object-access request, read the framing before acting:

- The user is **driving from a permission set** (mentions a permission set, RBAC, or an object grant on a permset) → this is an **object access grant** → route to `platform-dataspace-access-configure`, no need to ask.
- The user **frames it as a policy** (says policy, access policy, policy rule, OLS/FLS/RLS, tag/classification-based) → **create the policy here**, no need to ask.
- The request is **genuinely vague** — "grant object access to X" with no mechanism and no clue → **ASK** whether they want the **permission-set way** (`platform-dataspace-access-configure`) or the **access-policy way** (this skill). If it is also unclear whether the object is Data Cloud, ask which object first.

"Access to a **data space**" is the permission-set path — route it to `platform-dataspace-access-configure`.

H360 policy **create / read / update** run over the headless-360 MCP `/headless/metadata` MD-CRUD path via `dispatch`: `discover`/`describe` the operation, then `dispatch` a POST create / PUT update of the generated XML and `dispatch_readonly` GET it back to verify. See `references/headless-transport.md` for the exact request/response shapes. There is **no `sf`/MDAPI fallback** — if the headless-360 MCP session is unavailable, or the type/op is not yet on the MD-CRUD allowlist (`400 UNSUPPORTED_OPERATION`), or the org lacks feature provisioning (`400 FIELD_INTEGRITY_EXCEPTION`), surface that gap to the operator rather than routing around it. This skill covers **create, read, update, and delete (CRUD)**. **Delete does NOT run over `/headless/metadata`** — Core has no real metadata delete (a metadata DELETE 405s, and the interim delete is a no-op 200 that removes nothing), so a policy is deleted over the Data 360 MCP **Data Governance Access Policy** surface (`d360_data_governance_access_policy_delete`), which removes the Access Policy and every embedded rule by developer name. See the "Deleting a Policy" section below. Use the Data 360 MCP tools to resolve exact org references before writing XML — `search`/`payload_examples`/`execute` against read-only lookup operations (tag, classification, dataspace, and every resource object: custom/derived DMO via `d360_dmo_list`/`d360_dmo_get`, standard DMO via `d360_data_model_objects_list`/`d360_data_model_object_get`, DLO via `d360_dlo_list`/`d360_dlo_get`, calculated insight object via `d360_ci_list`/`d360_ci_get`). Only when no Data 360 MCP session is reachable, resolve a custom `__dlm` DMO's fields by a read-only headless-360 `dispatch_readonly` sObject describe as a last resort (it can miss `__dlm` objects — see `references/reference-resolution.md`). Author **creates and updates only** over `/headless/metadata` MD-CRUD — never via a Data 360 MCP `_create`/`_update` operation; the Data 360 MCP mutation surface is used only for **delete** (`access_policy_delete`, whole-policy) and, to remove a single rule while keeping the policy, `access_policy_rule_replace`. All tag/classification/dataspace/DMO/DLO/CIO lookups stay read-only. Never resolve a reference through an `sf` CLI command.

## Deterministic Workflow

1. Require `consumer`: accept only `DATACLOUD` or `ALL`; do not infer or default it.
2. Select the operating mode. Use normal author mode unless the request explicitly says to recreate a named retrieved evidence package exactly. In explicit evidence-recreation mode, the named API 69.0 example is authoritative: preserve its condition order, exact conjunctions, persisted `SCALAR_ATTRIBUTE`/`SOQLTARGETLISTEXPR` operands, and evidence values, while omitting `builderValidated` and keeping the evidence set's `builderCompatible` as retrieved. Exact recreation takes precedence over normal authoring rewrites and target-org re-resolution. It proves only evidence fidelity, not current-org authorability, runtime enforcement, or Policy Builder validation.
3. Identify the policy set developer name and rule developer name.
4. Choose the shared policy shape, category, effect, action, and resource scope **deterministically from the request signal** — do not ask the user "is this OLS/RLS/FLS?" when the signal is clear (read of a specific named object → RLS; hide a field → FLS; mask a field value → Transform; tag/classification tenant-wide → OLS). See `references/policy-shapes.md#selecting-the-shape-deterministic--do-not-ask-the-user`. Every renderable rule MUST carry **at least one resource condition** (principal conditions are optional; a zero-conditions or principal-only rule is not deployable/renderable) — if the shape has no valid resource condition (e.g. object-wide read with no row filter), obtain a resource condition or route object-wide read to the permission-set path (`platform-dataspace-access-configure`) rather than authoring an unrenderable rule.
5. In normal author mode, resolve every tag, classification, custom permission, DMO/DLO, field, resource domain, join field, and principal field in the target org through MCP — never through an `sf` CLI command. Resolve tags, classifications, dataspaces, and every resource object's schema and fields through the Data 360 MCP read-only lookup operations from `references/reference-resolution.md#data-360-mcp-lookup-operations`. Resource objects are not only DMOs — resolve custom/derived DMOs (the `__dlm` suffix that most `resourceDomains` entries target) via `d360_dmo_list`/`d360_dmo_get` (family `DataModelObject`), standard/canonical DMOs via `d360_data_model_objects_list`/`d360_data_model_object_get` (family `DataModelObjectCatalog`), raw ingested DLOs via `d360_dlo_list`/`d360_dlo_get`, and calculated insight objects (CIOs) via `d360_ci_list`/`d360_ci_get`. `d360_dmo_get` returns the DMO with all field definitions; pass `includeFields:"true"` to `d360_dmo_list`. Only when no Data 360 MCP session is reachable, resolve a custom `__dlm` DMO's field API names with a read-only headless-360 `dispatch_readonly` sObject describe as a last resort — it can miss `__dlm` objects that are absent from the sObjects surface, so prefer `d360_dmo_get` whenever Data 360 MCP is available. For custom permissions and ID-valued principal comparisons (e.g. `ProfileId`), for which no Data 360 MCP lookup exists, resolve read-only through `dispatch_readonly` (a SOQL `/query` or metadata read). The MCP path addresses the org implicitly and `/headless/metadata` resolves the API version server-side, so no `ORG_ID`/`ORG_API_VERSION` resolution is needed; evidence-recreation fixtures retain the `{API_VERSION}` placeholder for the eval harness. User-provided values may be developer names, fully qualified names, labels, or partial descriptions: resolve each to the exact target-org developer/API name before generating XML. A Data 360 MCP lookup result's `id` is not the value to persist unless the field itself is ID-valued (e.g. `ProfileId`). For STANDARD_TAG/STANDARD_CLASSIFICATION `<valueReference>` values, construct the dotted path per `references/reference-resolution.md#constructing-valuereference-for-standard_tag--standard_classification` — it is not a single-field copy from the lookup record. For other `<valueDomain>`/`<select>` values, take the resolved developer/API name from the same record. When a label or description matches a reference, retain the resolved developer/API name in the metadata and do not emit the label unless the schema explicitly requires a label. Never invent reference names, infer a developer name from a label, or reuse evidence-package values.
6. Construct the shared policy model from `references/condition-model.md`; reject `PLACEHOLDER` because it is internal-only.
7. In normal author mode, if `consumer=DATACLOUD`, apply `references/consumer-datacloud-ui.md`: build a typed custom-conjunction plan for the API/UI projection, serialize it as nested MDAPI `conjunctionExpression` `AND`/`OR` groups, enforce one action and one resource domain, reject plural principal attributes, and validate directional scalar/RLS capabilities. If `consumer=ALL`, apply only `references/consumer-all.md` and base validation; make no UI-renderability claim. In evidence-recreation mode, preserve the named example's exact conjunction instead of recompiling it.
8. Number conditions only after grouping is complete, validate complete conjunction coverage (every top-level operand is a group, except a lone FLS/Transform `ENTITYTYPE IS FIELD` index — a lone permission or tag condition is still wrapped, e.g. FLS `(AND 1 (OR 2 3 4) (AND 5))`), then render XML. For evidence recreation, retain the evidence condition order and validate its existing numbering without rewriting it.
9. Author the set XML and the definition XML as two components. Author `<builderCompatible>true</builderCompatible>` on the set by default; omit it (or author `false`) only when the user explicitly asks for a non-builder-compatible policy. **ACCESS exception:** when the user explicitly requests the ACCESS category and the operator confirms API-only output (the `references/ui-compatibility.md` path), author `<builderCompatible>false</builderCompatible>` and keep the `# API-only:` marker in the description. Never author `builderValidated`. The MD-CRUD path takes each component's XML directly as `xmlRep` (see step 10) — no `package.xml`/manifest or `ORG_API_VERSION` interpolation is required. Eval fixtures retain the `{API_VERSION}` placeholder for the harness.
10. **Preview and confirm before writing.** The deterministic routing means no mid-flow clarifying questions; the single human checkpoint is here. Show the operator the resolved shape, target object/references, and the concrete rule (conditions + effect) and get an explicit go-ahead before the create/update dispatch. Then verify via the transport: flatten the generated `.policyRuleDefinitionSet`/`.policyRuleDefinition` XML to a single-line string (a defensive default — a properly-escaped multi-line `xmlRep` also persists, but single-line sidesteps any client that mangles newlines), `dispatch` a POST create (PUT for an update) to `/headless/metadata` for the set and then the rule, and `dispatch_readonly` GET each back to confirm a 2xx response. See `references/headless-transport.md` for the exact request/response shapes, the `xmlRep` newline guidance, and the transient-retry note. **UI-renderable-contract check:** the set read-back must carry the authored `<builderCompatible>true</builderCompatible>` (or `false` when the user opted out) and a server-set `<builderValidated>` — do not assert a specific `builderValidated` value (observed `true` alongside an authored `builderCompatible=true`; `false` when the flag was not authored). If `builderCompatible` reads back `false` although `true` was authored, the server normalized it: report that to the operator rather than retrying. `builderValidated` remains server-managed; never author it.

## Deleting a Policy

Delete a policy over the Data 360 MCP **Data Governance Access Policy** surface, **not** `/headless/metadata` — Core has no real metadata delete (a metadata DELETE 405s or no-ops), so it never belongs on that transport. A `PolicyRuleDefinitionSet` authored by this skill surfaces there as an **Access Policy** addressable by its developer name. Sets authored with the default `builderCompatible: true` appear in a plain `access_policy_list`; sets that were authored with the opt-out (or normalized to `false`) need `includeIncompatible: true` to show up. Either way, `access_policy_get` and `access_policy_delete` work by name regardless of builder-compatibility.

`d360_data_governance_access_policy_delete` takes a single `name` (the set's developer name) and is a **whole-policy delete**: one call removes the Access Policy **and every embedded rule** (its `PolicyRuleDefinition` members). There is therefore **no leaf-before-parent ordering** and **no discrete single-rule delete** — to drop one rule while keeping the policy, re-author the surviving rule set via `d360_data_governance_access_policy_rule_replace` instead. Confirm the delete by reading the policy back with `d360_data_governance_access_policy_get` by name: a not-found result (or the policy being absent from an `includeIncompatible` list) is the success signal. There is **no `sf` CLI fallback**.

## Validated Policy Shapes

For an object-level security policy with tags/classifications and principal conditions, begin with `references/examples/TaggedObjectAccess/`. Select the conjunction contract from the explicit consumer: `DATACLOUD` requires the UI custom-conjunction form; `ALL` uses the general form.

The real example has:

- One `PolicyRuleDefinitionSet`: `TaggedObjectAccess`.
- One `PolicyRuleDefinition`: `TaggedObjectAccess_Rule_1`.
- `GOVERNANCE_POLICY_RULE_DEFINITION`.
- `Permit` and `TupleRead`.
- `ANY` resource scope.
- Two entity-type conditions, one principal-permission condition, one principal-expression condition, and two tag conditions.
- A grouped conjunction expression: `(AND (OR 1 2) (AND 3 4) (AND 5 6))`.

For the validated field-level security deny shape, use `references/examples/FieldReadDeny/`: `GOVERNANCE_POLICY_RULE_DEFINITION`, `Forbid`, `Read`, and one entity-type discriminator whose right operand is `FIELD`. This example validates the deny shape; it does not establish that every other FLS shape is invalid.

**"Deny X unless the user has permission P" is authored as `!=`, never as `UNLESS`.** The Data Governance UI has no UNLESS section: it forces `unlessPolicyRuleDefinitionClauseConjunction` to null on save, so a policy that uses it deploys but will not open in Policy Builder. Cedar's `unless` is the natural reading of the request, so do not copy it. Keep the effect `Forbid` and express the exemption as a principal condition inside `whenPolicyRuleDefinitionClauseConjunction`: `principalPath=ASSIGNED_PERMISSIONS_PATH`, `operator=CONTAINS_NONE`, `valueReferenceType=CUSTOM_PERMISSION` (the UI's "user.permission != P"). Number it as its own `(AND n)` group. The same rewrite applies to `unless` on a tag (`TAG CONTAINS_NONE`) and on a record field (`RECORDFIELD NOT_EQUALS`). Worked shape: `references/policy-shapes.md`, section "Deny unless".

For the validated field-masking shape, use `references/examples/LastCharactersFieldMasking/`: `TRANSFORM_POLICY_RULE_DEFINITION`, `Transform`, `Read`, `FIELD` scope, an explicit `resourceTransform`, and one entity-type discriminator whose right operand is `FIELD`. The retrieved `LAST_N_CHARS_RESOURCE_TRANSFORM` uses a top-level `resourceExpression` of type `ARGLIST`; do not generalize its argument shape to other transforms.

For the validated row-level security shapes, use `references/examples/PrincipalFieldMatchRLS/` for direct record-field comparisons and `references/examples/ExistsJoinRLS/` for an `EXISTS` join block. Both use `RECORD_POLICY_RULE_DEFINITION`, `Permit`, `Read`, `RECORD` scope, and an exact target DMO in `policyRuleResourceDomains`. Resolve every DMO and field in the target org before authoring.

Dataspace-scoped OLS is parked and unsupported because the UI-retrieved references did not pass MDAPI validation in the source org. Do not construct it until a separately validated real-org shape is available.

## Required References

- `references/condition-model.md`: how to construct a condition as left operand, operator, and right operand.
- `references/condition-templates.md`: copyable condition shapes.
- `references/resource-expression.md`: resource-side projections, joins, aliases, and predicates.
- `references/policy-shapes.md`: deterministic OLS, FLS, and masking top-level fields.
- `references/principal-expression.md`: principal-side `SOQLTARGETLISTEXPR` expressions.
- `references/conjunction-expression.md`: one-indexed boolean grouping.
- `references/reference-resolution.md`: exact target-org reference resolution.
- `references/headless-transport.md`: the `dispatch`/`dispatch_readonly` `/headless/metadata` request/response shapes (the sole transport; no CLI fallback).
- `references/consumer-datacloud-ui.md`: Data Governance UI grouping, cardinality, scalar attributes, and RLS field capabilities.
- `references/consumer-all.md`: general `ALL` consumer contract.
- `references/runtime-context.md`: `MIN_API_VERSION`, `ORG_API_VERSION`, and evidence-version handling.
- `references/conjunction-compiler.md`: deterministic bucket, index, and custom-conjunction construction.
- `references/examples/TaggedObjectAccess/`: semantic OLS evidence package.
- `references/examples/FieldReadDeny/`: semantic FLS deny evidence package.
- `references/examples/LastCharactersFieldMasking/`: semantic field-masking evidence package.
- `references/examples/PrincipalFieldMatchRLS/`: semantic direct-comparison RLS evidence package.
- `references/examples/ExistsJoinRLS/`: semantic projection-join RLS evidence package.

The semantic examples are derived from retrieved server output and retain source-org-specific values. All five examples carry `<builderCompatible>true</builderCompatible>` on the set; `builderCompatible` is authored (step 9) and `builderValidated` is never authored. They prove persisted metadata shapes, not Policy Builder open/save compatibility or a public MDAPI enum contract. Treat them as evidence, not directly deployable templates. Do not copy persisted `builderValidated` values, IDs, references, or undocumented enum values into authored packages; resolve every org-specific value again, change component identities and requested policy values, and validate the result in the target org.

## Package Contract

```text
<policy>/
  package.xml
  policyRuleDefinitionSets/<setName>.policyRuleDefinitionSet
  policyRuleDefinitions/<ruleName>.policyRuleDefinition
```

The rule must contain `<policyRuleDefinitionSetName>` equal to the set filename without its extension. The package must list both metadata types.

Both the set and the rule take a human-readable `<label>`. The set's `<label>` conventionally matches its developer name (`TaggedObjectAccess`'s set uses `<label>TaggedObjectAccess</label>`); the rule's `<label>` conventionally identifies its position within the set (`TaggedObjectAccess_Rule_1` uses `<label>Rule 1</label>`). This is a plain descriptive label, distinct from the reference-resolution rule against emitting a *resolved-reference* label (see `references/reference-resolution.md`): never substitute a tag/classification/permission's display label for its resolved developer/API name, but the set's and rule's own `<label>` are always fine to author.

The MD-CRUD path sends each component's XML as `xmlRep` and resolves the API version server-side, so no `package.xml`/manifest `<version>` and no `ORG_API_VERSION` interpolation are required. The `package.xml` shown above and the `<version>{API_VERSION}</version>` placeholder are retained only for the eval fixtures and as the logical component set. Historical evidence versions are provenance only. Never modify the caller's `sfdx-project.json` to set an operation-specific version.

Author `<builderCompatible>true</builderCompatible>` on every `PolicyRuleDefinitionSet` unless the user explicitly asks for a policy that is not builder-compatible (then omit it, or author `false`). For an explicitly requested ACCESS policy with operator-confirmed API-only output, author `false` and keep the `# API-only:` marker in the description. Never author `builderValidated`; it is server-managed and set by an actual Policy Builder validation.
