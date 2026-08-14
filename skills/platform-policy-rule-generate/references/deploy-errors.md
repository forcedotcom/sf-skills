# Deploy Error Reference

When `sf project deploy start` fails, it prints a per-component status table. Below are the most common error families for `PolicyRuleDefinition` / `PolicyRuleDefinitionSet` metadata.

For verbose output when scripting:
```bash
sf project deploy start --target-org <alias> --source-dir … --json --verbose \
  | jq '.result.details.componentFailures'
```

---

## Error Table

| Error fragment | Likely cause | Fix |
|---|---|---|
| `Not available for deploy for this organization` | Org has `EnforceOMatic` perm (entities visible) but lacks `PolicyRuleMDAPI` org perm | Internal license/feature provisioning — surface to the operator. Both `EnforceOMatic` AND `PolicyRuleMDAPI` are required (see §11.1 of policy.md). |
| `Cannot find … PolicyRuleDefinition` (older orgs) | Org missing `EnforceOMatic` entirely, or API version too low | Confirm both `EnforceOMatic` and `PolicyRuleMDAPI` perms; ensure `<version>` ≥ 64.0 in package.xml |
| `INVALIDFORCATEGORY` / `Resource scope … not valid for category …` | Scope × category mismatch (e.g., ACCESS/GOVERNANCE + RECORD scope, or TRANSFORM + ANY scope) | Match scope to category per the §4 matrix in SKILL.md. For OLS/FLS on tagged objects: use `ANY`/`FIELD` scope + tag/classification condition — **not** `<resourceDomain>`. |
| `Identified record category should use record field …` | Attempted to author an `IDENTIFIED_RECORD` policy with a non-`RECORDFIELD` resource path | Do not author `IDENTIFIED_RECORD` via MDAPI — use a runtime `RuleProvider` instead. |
| `Invalid resource domain - <name>` | `<resourceDomain>` references an entity that doesn't exist in the target org | Pre-deploy the DMO/entity, or remove the rule until the target is available. Namespaced DMOs (e.g. `ssot__Account__dlm`) need the namespace prefix in the XML. |
| `An unexpected error occurred. Please include this ErrorId… (-116061062)` (opaque gack on RLS deploy) | RLS rule references a `<valueDomain>` DMO field that exists in metadata but is **not mapped** in the target org's data streams. Server-side NPE instead of a clean validation error. | Verify each `<valueDomain>` field is mapped in Setup → Data Cloud → Data Explorer. Build the rule in the UI first — the UI surfaces field-mapping issues with usable errors where MDAPI doesn't. |
| `Metadata API received improper input. … Load of metadata from db failed for metadata of type:PolicyRuleDefinition and file name:<name>` (on **retrieve**) | UI-saved RLS rules can fail to round-trip back through MDAPI retrieve in some org states | No clean fix. Use the UI as source of truth for that rule, or hand-author from a known-deployable RLS template. |
| `Use the principal … with external record category.` | `EXTERNAL_RECORD` rule used a non-`IS_AUTHENTICATED`/`IS_INTERNAL` `principalPath` | Switch principal path or change category |
| `Unsupported … contextPath` | Used a context path outside `RuleContextPathType.SESSION_DATASPACE` | Not authorable via MDAPI XML — use a runtime `RuleProvider` |

---

## OrgPerm Gating

Two org permissions are **both** required for MDAPI authoring:

| Permission | Gate | Effect if missing |
|---|---|---|
| `EnforceOMatic` | `@WsdlGuard` master switch | Entities not visible in UI/Tooling API at all |
| `PolicyRuleMDAPI` | `orgCanUsePolicyRuleMDAPI` WSDL layer | Deploy fails with `Not available for deploy for this organization` |

`EnforcOMaticMDAPI` is a separate **packaging** gate (`isMdAPIAllowedInternal`) — only required for packaging/change sets, not for DX CLI deploys. After PR #98647 (merged 2026-06-08) the predicate is `DBContext.get().isDoingPackageInstall()`, so DX CLI deploys work with just the two perms above.

---

## Dry-Run First

Always validate before deploying to a long-lived org:

```bash
sf project deploy start \
  --target-org <alias> \
  --source-dir force-app/main/default \
  --dry-run \
  --wait 10
```

A `--dry-run` failure runs the full server-side validation (including the `IDENTIFIED_RECORD` constraint) without persisting. This catches all of the errors in the table above before they affect a real org.
